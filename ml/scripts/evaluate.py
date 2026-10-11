#!/usr/bin/env python
"""Evaluate a trained checkpoint on CUAD test and the Indian eval set.

Reports both, side by side. CUAD test measures performance on US M&A
contracts; the Indian set measures the domain the product actually serves. The
**gap between them is the finding** — a single number from the easier
distribution would overstate what this system does for an Indian MSME.

Also measures CPU inference latency against the TBD-3 budget (30 s p95 for 50
clauses), so SRS 5.1 is verified by measurement rather than assumed.

Usage
-----
    python ml/scripts/evaluate.py --checkpoint ml/artifacts/distilbert
"""

from __future__ import annotations

import argparse
import json
import logging
import statistics
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.services.classification.labels import LABEL_KEYS, thin_classes  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("evaluate")

PROCESSED = REPO_ROOT / "ml" / "data" / "processed"
INDIAN_EVAL = REPO_ROOT / "ml" / "eval" / "indian_eval_set.jsonl"

LATENCY_BUDGET_SECONDS = 30.0
LATENCY_CLAUSE_COUNT = 50


def read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def score(rows: list[dict], checkpoint: Path) -> dict:
    import numpy as np
    import torch
    from sklearn.metrics import f1_score, precision_recall_fscore_support
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(str(checkpoint))
    model = AutoModelForSequenceClassification.from_pretrained(str(checkpoint))
    model.eval()

    thresholds_path = checkpoint / "thresholds.json"
    thresholds = (
        json.loads(thresholds_path.read_text(encoding="utf-8"))
        if thresholds_path.is_file()
        else dict.fromkeys(LABEL_KEYS, 0.5)
    )

    # Label order from the checkpoint, not from LABEL_KEYS: if the taxonomy is
    # reordered after training, positional mapping silently relabels.
    id2label = model.config.id2label
    order = [id2label[i] for i in sorted(id2label)]

    index = {key: i for i, key in enumerate(order)}
    targets = np.zeros((len(rows), len(order)), dtype=int)
    probabilities = np.zeros((len(rows), len(order)), dtype=float)

    batch = 16
    for start in range(0, len(rows), batch):
        chunk = rows[start : start + batch]
        encoded = tokenizer(
            [r["text"] for r in chunk],
            truncation=True,
            max_length=256,
            padding=True,
            return_tensors="pt",
        )
        with torch.no_grad():
            logits = model(**encoded).logits
        probabilities[start : start + len(chunk)] = torch.sigmoid(logits).numpy()

        for offset, row in enumerate(chunk):
            for label in row["labels"]:
                if label in index:
                    targets[start + offset, index[label]] = 1

    predicted = np.zeros_like(targets)
    for i, key in enumerate(order):
        predicted[:, i] = (probabilities[:, i] >= thresholds.get(key, 0.5)).astype(int)

    precision, recall, f1, support = precision_recall_fscore_support(
        targets, predicted, average=None, zero_division=0
    )

    return {
        "n": len(rows),
        "macro_f1": round(float(f1_score(targets, predicted, average="macro", zero_division=0)), 4),
        "micro_f1": round(float(f1_score(targets, predicted, average="micro", zero_division=0)), 4),
        "per_class": {
            key: {
                "precision": round(float(precision[i]), 4),
                "recall": round(float(recall[i]), 4),
                "f1": round(float(f1[i]), 4),
                "support": int(support[i]),
            }
            for i, key in enumerate(order)
        },
    }


def measure_latency(checkpoint: Path, rows: list[dict], repeats: int = 5) -> dict:
    """Time the classifier over a realistic 50-clause contract on CPU."""
    import torch

    torch.set_num_threads(2)  # match the 2-vCPU target in TBD-3

    from app.services.classification.model import TransformerClassifier

    classifier = TransformerClassifier(checkpoint)
    texts = [r["text"] for r in rows[:LATENCY_CLAUSE_COUNT]]
    if len(texts) < LATENCY_CLAUSE_COUNT:
        texts = (texts * (LATENCY_CLAUSE_COUNT // max(len(texts), 1) + 1))[
            :LATENCY_CLAUSE_COUNT
        ]

    classifier.classify(texts[:4])  # warm up; first call pays lazy init

    timings: list[float] = []
    for _ in range(repeats):
        start = time.perf_counter()
        classifier.classify(texts)
        timings.append(time.perf_counter() - start)

    return {
        "clauses": len(texts),
        "runs": repeats,
        "median_seconds": round(statistics.median(timings), 2),
        "max_seconds": round(max(timings), 2),
        "budget_seconds": LATENCY_BUDGET_SECONDS,
        "within_budget": max(timings) <= LATENCY_BUDGET_SECONDS,
    }


def print_table(name: str, metrics: dict) -> None:
    logger.info("")
    logger.info("=== %s (n=%d) ===", name, metrics["n"])
    logger.info("macro-F1 %.4f | micro-F1 %.4f", metrics["macro_f1"], metrics["micro_f1"])
    logger.info("%-28s %6s %6s %6s %7s", "class", "P", "R", "F1", "support")
    for key, row in metrics["per_class"].items():
        marker = " (thin)" if key in thin_classes() else ""
        logger.info(
            "%-28s %6.3f %6.3f %6.3f %7d%s",
            key,
            row["precision"],
            row["recall"],
            row["f1"],
            row["support"],
            marker,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--skip-latency", action="store_true")
    args = parser.parse_args()

    checkpoint = (
        args.checkpoint if args.checkpoint.is_absolute() else REPO_ROOT / args.checkpoint
    )
    if not (checkpoint / "config.json").is_file():
        raise SystemExit(f"no checkpoint at {checkpoint} — run train.py first")

    results: dict[str, dict] = {}

    cuad_test = read_jsonl(PROCESSED / "test.jsonl")
    if cuad_test:
        results["cuad_test"] = score(cuad_test, checkpoint)
        print_table("CUAD held-out test", results["cuad_test"])
    else:
        logger.warning("No CUAD test split; run prepare_cuad.py")

    indian = read_jsonl(INDIAN_EVAL)
    if indian:
        results["indian_eval"] = score(indian, checkpoint)
        print_table("Indian evaluation set", results["indian_eval"])
    else:
        logger.warning(
            "No Indian eval set at %s. Hand-label 150-200 clauses from the TBD-5 "
            "sources; without it you cannot report performance on the domain the "
            "product actually serves.",
            INDIAN_EVAL,
        )

    if "cuad_test" in results and "indian_eval" in results:
        gap = results["cuad_test"]["macro_f1"] - results["indian_eval"]["macro_f1"]
        logger.info("")
        logger.info("=== domain gap ===")
        logger.info(
            "CUAD macro-F1 %.4f - Indian macro-F1 %.4f = %+.4f",
            results["cuad_test"]["macro_f1"],
            results["indian_eval"]["macro_f1"],
            -gap if gap < 0 else gap,
        )
        logger.info(
            "Discuss this gap in the report. It is the honest measure of how far "
            "a US-trained model transfers to Indian MSME contracts."
        )

    if not args.skip_latency and (cuad_test or indian):
        latency = measure_latency(checkpoint, cuad_test or indian)
        results["latency"] = latency
        logger.info("")
        logger.info("=== latency (TBD-3) ===")
        logger.info(
            "%d clauses on 2 threads: median %.2fs, max %.2fs (budget %.0fs) -> %s",
            latency["clauses"],
            latency["median_seconds"],
            latency["max_seconds"],
            latency["budget_seconds"],
            "WITHIN BUDGET" if latency["within_budget"] else "OVER BUDGET",
        )

    out = checkpoint / "evaluation.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    logger.info("")
    logger.info("Wrote %s — copy both tables into ml/MODEL_CARD.md", out)


if __name__ == "__main__":
    main()
