"""Clause-type classification (REQ-3.1 to REQ-3.4).

Two implementations behind one interface:

* ``TransformerClassifier`` — the fine-tuned DistilBERT from ``ml/``. Used when
  a checkpoint is present and torch/transformers are installed.
* ``BaselineClassifier`` — keyword cues from ``labels.py``. Used otherwise.

The baseline exists so the pipeline is end-to-end runnable before Phase 3
training completes, and so a missing checkpoint degrades to a weaker
prediction instead of a 500 (SRS 5.4 Reliability). It is **not** a substitute
for the trained model: its ``model_version`` begins with ``baseline-`` and that
string is stored on every prediction and stamped on every report, so no result
can be mistaken for a trained one.

torch and transformers are intentionally **not** in
``backend/requirements.txt``. They add ~2.5 GB to the image, and the backend
needs them only once a checkpoint exists. See ``ml/requirements.txt``.
"""

from __future__ import annotations

import logging
import math
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.core.config import get_settings
from app.services.classification.labels import CLAUSE_TYPES, LABEL_KEYS

logger = logging.getLogger(__name__)

BASELINE_VERSION = "baseline-keyword-v1"

# Highest confidence the baseline will ever report. Keyword matching is not
# calibrated, and letting it emit 0.95 would misrepresent a heuristic as a
# trained prediction — SRS 5.2 forbids asserting certainty.
BASELINE_CONFIDENCE_CEILING = 0.80


@dataclass(frozen=True, slots=True)
class Prediction:
    label: str
    confidence: float


class Classifier(Protocol):
    model_version: str

    def classify(self, texts: list[str]) -> list[list[Prediction]]:
        """Return predictions per input, already threshold-filtered and sorted."""
        ...


# --------------------------------------------------------------------------
# Baseline
# --------------------------------------------------------------------------
class BaselineClassifier:
    """Keyword-cue scoring. Deterministic, dependency-free, modest accuracy."""

    model_version = BASELINE_VERSION

    def __init__(self, threshold: float | None = None) -> None:
        self._threshold = (
            threshold if threshold is not None else get_settings().min_confidence_threshold
        )
        # Compile once: whole-phrase matching with word boundaries, so "audit"
        # does not fire on "auditorium" and "gst" not on "gstreamer".
        self._patterns: dict[str, list[re.Pattern[str]]] = {
            c.key: [re.compile(rf"\b{re.escape(cue)}\b", re.IGNORECASE) for cue in c.baseline_cues]
            for c in CLAUSE_TYPES
        }

    def classify(self, texts: list[str]) -> list[list[Prediction]]:
        return [self._classify_one(t) for t in texts]

    def _classify_one(self, text: str) -> list[Prediction]:
        scores: dict[str, float] = {}

        for key, patterns in self._patterns.items():
            hits = sum(1 for p in patterns if p.search(text))
            if not hits:
                continue
            # Diminishing returns: the second cue is strong evidence, the
            # fifth adds little. Saturates below the ceiling.
            score = BASELINE_CONFIDENCE_CEILING * (1 - math.exp(-0.9 * hits))
            scores[key] = round(score, 4)

        predictions = [
            Prediction(label=k, confidence=v) for k, v in scores.items() if v >= self._threshold
        ]
        # REQ-3.2 is multi-label, but a keyword heuristic over 20 classes fires
        # too broadly to be useful unfiltered. Keep the strongest few.
        predictions.sort(key=lambda p: p.confidence, reverse=True)
        return predictions[:3]


# --------------------------------------------------------------------------
# Transformer
# --------------------------------------------------------------------------
class TransformerClassifier:
    """Fine-tuned DistilBERT with per-class thresholds (TBD-2).

    Long clauses are handled by a sliding window with max-pooling across
    windows: contract clauses routinely exceed the 256-token input, and
    truncating would discard the back half of exactly the long, dense
    provisions that carry the most risk.
    """

    def __init__(self, checkpoint: Path) -> None:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self._torch = torch
        self._tokenizer = AutoTokenizer.from_pretrained(str(checkpoint))
        self._model = AutoModelForSequenceClassification.from_pretrained(str(checkpoint))
        self._model.eval()

        self.model_version = _read_version(checkpoint)
        self._thresholds = _read_thresholds(checkpoint)
        self._floor = get_settings().min_confidence_threshold

        # Label order must come from the checkpoint, not from LABEL_KEYS: if
        # the taxonomy is reordered after training, positional mapping would
        # silently relabel every prediction.
        config_labels = getattr(self._model.config, "id2label", None) or {}
        self._labels = [config_labels[i] for i in sorted(config_labels)] or list(LABEL_KEYS)

        unknown = set(self._labels) - set(LABEL_KEYS)
        if unknown:
            raise ValueError(f"checkpoint emits labels not in the taxonomy: {sorted(unknown)}")

    _MAX_TOKENS = 256
    _STRIDE = 192
    _BATCH = 16

    def classify(self, texts: list[str]) -> list[list[Prediction]]:
        results: list[list[Prediction]] = []
        for i in range(0, len(texts), self._BATCH):
            results.extend(self._classify_batch(texts[i : i + self._BATCH]))
        return results

    def _classify_batch(self, texts: list[str]) -> list[list[Prediction]]:
        torch = self._torch
        out: list[list[Prediction]] = []

        for text in texts:
            encoded = self._tokenizer(
                text,
                truncation=True,
                max_length=self._MAX_TOKENS,
                stride=self._STRIDE,
                return_overflowing_tokens=True,
                return_tensors="pt",
                padding="max_length",
            )
            inputs = {
                k: v for k, v in encoded.items() if k in {"input_ids", "attention_mask"}
            }

            with torch.no_grad():
                logits = self._model(**inputs).logits

            # Max-pool across windows: a clause belongs to a class if *any*
            # part of it does.
            probabilities = torch.sigmoid(logits).max(dim=0).values.tolist()
            out.append(self._to_predictions(probabilities))

        return out

    def _to_predictions(self, probabilities: list[float]) -> list[Prediction]:
        predictions: list[Prediction] = []
        for label, probability in zip(self._labels, probabilities, strict=False):
            threshold = max(self._thresholds.get(label, self._floor), self._floor)
            if probability >= threshold:
                predictions.append(Prediction(label=label, confidence=round(probability, 4)))
        predictions.sort(key=lambda p: p.confidence, reverse=True)
        return predictions


def _read_version(checkpoint: Path) -> str:
    marker = checkpoint / "VERSION"
    if marker.is_file():
        return marker.read_text(encoding="utf-8").strip()[:64] or checkpoint.name
    return checkpoint.name


def _read_thresholds(checkpoint: Path) -> dict[str, float]:
    """Per-class thresholds fitted on validation, written by ml/scripts/train.py."""
    import json

    path = checkpoint / "thresholds.json"
    if not path.is_file():
        logger.warning("No thresholds.json in %s; using the global floor only", checkpoint)
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {str(k): float(v) for k, v in data.items()}
    except (ValueError, TypeError):
        logger.exception("thresholds.json is malformed; using the global floor only")
        return {}


# --------------------------------------------------------------------------
# Selection
# --------------------------------------------------------------------------
def _checkpoint_path() -> Path:
    return Path(os.getenv("CLAUSEGUARD_MODEL_DIR", "models/clause-classifier"))


@lru_cache(maxsize=1)
def get_classifier() -> Classifier:
    """Load the best available classifier once per process.

    Cached because model load is seconds, not milliseconds, and the TBD-3
    latency budget cannot absorb it per request.
    """
    checkpoint = _checkpoint_path()

    if checkpoint.is_dir() and (checkpoint / "config.json").is_file():
        try:
            classifier = TransformerClassifier(checkpoint)
            logger.info("Loaded trained classifier %s", classifier.model_version)
            return classifier
        except ImportError:
            logger.warning(
                "Checkpoint at %s but torch/transformers are not installed; "
                "falling back to the keyword baseline. Install ml/requirements.txt.",
                checkpoint,
            )
        except Exception:
            logger.exception("Checkpoint at %s could not be loaded; using baseline", checkpoint)
    else:
        logger.info("No checkpoint at %s; using the keyword baseline", checkpoint)

    return BaselineClassifier()
