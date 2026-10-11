#!/usr/bin/env python
"""Fine-tune a multi-label clause-type classifier (REQ-3.1 to REQ-3.3).

Writes a checkpoint the backend can load directly: the model, the tokenizer,
``thresholds.json`` (per-class thresholds fitted on validation, TBD-2) and a
``VERSION`` marker that is recorded on every prediction.

Usage
-----
    pip install -r ml/requirements.txt
    python ml/scripts/prepare_cuad.py          # and audit its output first
    python ml/scripts/train.py --config ml/configs/distilbert.yaml

On a free Colab T4, three epochs over ~30k clauses takes well under an hour.
Point the backend at the result with:

    CLAUSEGUARD_MODEL_DIR=/path/to/ml/artifacts/distilbert
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
import yaml
from sklearn.metrics import f1_score, precision_recall_fscore_support
from torch.utils.data import Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
    set_seed,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.services.classification.labels import LABEL_KEYS, thin_classes  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("train")

PROCESSED = REPO_ROOT / "ml" / "data" / "processed"


@dataclass
class Config:
    model_name: str = "distilbert-base-uncased"
    output_dir: str = "ml/artifacts/distilbert"
    version: str = "distilbert-cuad-v1"
    max_length: int = 256
    epochs: float = 3.0
    batch_size: int = 16
    learning_rate: float = 3e-5
    weight_decay: float = 0.01
    warmup_ratio: float = 0.1
    seed: int = 20241042
    # Caps the positive class weight. Without a ceiling, a class with three
    # examples gets a weight in the thousands and dominates the gradient.
    max_class_weight: float = 20.0

    @classmethod
    def load(cls, path: Path | None) -> Config:
        if path is None:
            return cls()
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        unknown = set(data) - {f for f in cls.__dataclass_fields__}
        if unknown:
            raise SystemExit(f"{path.name}: unknown keys {sorted(unknown)}")
        return cls(**data)


class ClauseDataset(Dataset):
    def __init__(self, rows: list[dict], tokenizer, max_length: int) -> None:
        self.rows = rows
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.index = {key: i for i, key in enumerate(LABEL_KEYS)}

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, i: int) -> dict:
        row = self.rows[i]
        encoded = self.tokenizer(
            row["text"], truncation=True, max_length=self.max_length, padding="max_length"
        )
        targets = np.zeros(len(LABEL_KEYS), dtype=np.float32)
        for label in row["labels"]:
            targets[self.index[label]] = 1.0

        item = {k: torch.tensor(v) for k, v in encoded.items()}
        item["labels"] = torch.tensor(targets)
        return item


class WeightedTrainer(Trainer):
    """Trainer with per-class positive weighting.

    Support ranges from thousands of clauses (Governing Law) to a handful
    (Joint IP), and unweighted BCE on that distribution simply predicts the
    majority negative for every rare class.
    """

    def __init__(self, *args, class_weights: torch.Tensor | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.class_weights = class_weights

    def compute_loss(
        self, model, inputs, return_outputs=False, **kwargs
    ):  # noqa: ANN001, ANN201
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        weights = (
            self.class_weights.to(outputs.logits.device)
            if self.class_weights is not None
            else None
        )
        loss = torch.nn.BCEWithLogitsLoss(pos_weight=weights)(
            outputs.logits, labels
        )
        return (loss, outputs) if return_outputs else loss


def read_split(name: str, limit: int | None = None) -> list[dict]:
    """Read a split, optionally truncated.

    ``limit`` exists for smoke-testing: a full CPU run is ~an hour, and
    discovering a crash in the evaluation step at the end of it is an
    expensive way to find a typo.
    """
    path = PROCESSED / f"{name}.jsonl"
    if not path.is_file():
        raise SystemExit(f"{path} missing — run ml/scripts/prepare_cuad.py first")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    return rows[:limit] if limit else rows


def positive_weights(rows: list[dict], ceiling: float) -> torch.Tensor:
    counts = np.zeros(len(LABEL_KEYS))
    index = {key: i for i, key in enumerate(LABEL_KEYS)}
    for row in rows:
        for label in row["labels"]:
            counts[index[label]] += 1

    total = len(rows)
    # Standard positive weighting: negatives / positives, clamped.
    weights = np.where(counts > 0, (total - counts) / np.maximum(counts, 1), 1.0)
    return torch.tensor(np.clip(weights, 1.0, ceiling), dtype=torch.float32)


def fit_thresholds(probabilities: np.ndarray, targets: np.ndarray) -> dict[str, float]:
    """Per-class threshold maximising F1 on validation (TBD-2).

    A single global 0.5 sacrifices recall on rare classes, which are exactly
    the Indian-relevant ones. The global floor from settings still applies at
    serve time; this table only ever raises a threshold above it.
    """
    thresholds: dict[str, float] = {}
    grid = np.arange(0.05, 0.96, 0.05)

    for i, key in enumerate(LABEL_KEYS):
        if targets[:, i].sum() == 0:
            # No validation examples: leave it at the conservative default
            # rather than fitting noise.
            thresholds[key] = 0.5
            continue

        best_threshold, best_f1 = 0.5, -1.0
        for threshold in grid:
            predicted = (probabilities[:, i] >= threshold).astype(int)
            score = f1_score(targets[:, i], predicted, zero_division=0)
            if score > best_f1:
                best_threshold, best_f1 = float(threshold), float(score)
        thresholds[key] = round(best_threshold, 2)

    return thresholds


def evaluate(
    probabilities: np.ndarray, targets: np.ndarray, thresholds: dict[str, float]
) -> dict:
    predicted = np.zeros_like(probabilities, dtype=int)
    for i, key in enumerate(LABEL_KEYS):
        predicted[:, i] = (probabilities[:, i] >= thresholds[key]).astype(int)

    precision, recall, f1, support = precision_recall_fscore_support(
        targets, predicted, average=None, zero_division=0
    )

    per_class = {
        key: {
            "precision": round(float(precision[i]), 4),
            "recall": round(float(recall[i]), 4),
            "f1": round(float(f1[i]), 4),
            "support": int(support[i]),
            "thin_in_cuad": key in thin_classes(),
        }
        for i, key in enumerate(LABEL_KEYS)
    }

    return {
        # Macro-F1, not accuracy: with 20 imbalanced labels, accuracy is
        # dominated by true negatives and would overstate performance.
        "macro_f1": round(float(f1_score(targets, predicted, average="macro", zero_division=0)), 4),
        "micro_f1": round(float(f1_score(targets, predicted, average="micro", zero_division=0)), 4),
        "per_class": per_class,
    }


def predict(trainer: Trainer, dataset: ClauseDataset) -> tuple[np.ndarray, np.ndarray]:
    output = trainer.predict(dataset)
    probabilities = torch.sigmoid(torch.tensor(output.predictions)).numpy()
    return probabilities, output.label_ids


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Truncate every split to N rows. For smoke-testing the script.",
    )
    args = parser.parse_args()

    config = Config.load(args.config)
    set_seed(config.seed)

    train_rows = read_split("train", args.limit)
    validation_rows = read_split("validation", args.limit)
    test_rows = read_split("test", args.limit)

    tokenizer = AutoTokenizer.from_pretrained(config.model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        config.model_name,
        num_labels=len(LABEL_KEYS),
        problem_type="multi_label_classification",
        # Written into config.json, so the backend reads label order from the
        # checkpoint rather than assuming it matches LABEL_KEYS positionally.
        id2label=dict(enumerate(LABEL_KEYS)),
        label2id={key: i for i, key in enumerate(LABEL_KEYS)},
    )

    output_dir = REPO_ROOT / config.output_dir
    arguments = TrainingArguments(
        output_dir=str(output_dir / "_checkpoints"),
        num_train_epochs=config.epochs,
        per_device_train_batch_size=config.batch_size,
        per_device_eval_batch_size=config.batch_size * 2,
        learning_rate=config.learning_rate,
        weight_decay=config.weight_decay,
        warmup_ratio=config.warmup_ratio,
        logging_steps=100,
        # No intermediate checkpoints: each one is a 268 MB copy of the model,
        # and the final save below is the only artefact anything consumes.
        save_strategy="no",
        seed=config.seed,
        report_to=[],
        # Pinned memory only helps when copying to a GPU. On CPU it allocates
        # page-locked buffers for nothing and warns on every dataloader
        # construction.
        dataloader_pin_memory=torch.cuda.is_available(),
    )

    trainer = WeightedTrainer(
        model=model,
        args=arguments,
        train_dataset=ClauseDataset(train_rows, tokenizer, config.max_length),
        class_weights=positive_weights(train_rows, config.max_class_weight),
    )

    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(
        "Training %s on %d clauses (%d labels), device=%s",
        config.model_name,
        len(train_rows),
        len(LABEL_KEYS),
        device,
    )
    if device == "cpu":
        logger.warning(
            "No CUDA device available — training on CPU. This is slower but "
            "produces an identical checkpoint."
        )
    trainer.train()

    logger.info("Fitting per-class thresholds on validation")
    validation_set = ClauseDataset(validation_rows, tokenizer, config.max_length)
    validation_probabilities, validation_targets = predict(trainer, validation_set)
    thresholds = fit_thresholds(validation_probabilities, validation_targets)

    logger.info("Evaluating on the held-out test split")
    test_set = ClauseDataset(test_rows, tokenizer, config.max_length)
    test_probabilities, test_targets = predict(trainer, test_set)
    metrics = evaluate(test_probabilities, test_targets, thresholds)

    output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    (output_dir / "thresholds.json").write_text(json.dumps(thresholds, indent=2), encoding="utf-8")
    (output_dir / "VERSION").write_text(config.version, encoding="utf-8")
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    logger.info("")
    logger.info("macro-F1 %.4f | micro-F1 %.4f", metrics["macro_f1"], metrics["micro_f1"])
    logger.info("%-28s %6s %6s %6s %7s", "class", "P", "R", "F1", "support")
    for key, row in metrics["per_class"].items():
        marker = " (thin)" if row["thin_in_cuad"] else ""
        logger.info(
            "%-28s %6.3f %6.3f %6.3f %7d%s",
            key,
            row["precision"],
            row["recall"],
            row["f1"],
            row["support"],
            marker,
        )

    logger.info("")
    logger.info("Saved to %s", output_dir)
    logger.info("Serve it with CLAUSEGUARD_MODEL_DIR=%s", output_dir)
    logger.info("NEXT: run evaluate.py against ml/eval/indian_eval_set.jsonl and")
    logger.info("copy both tables into ml/MODEL_CARD.md.")


if __name__ == "__main__":
    main()
