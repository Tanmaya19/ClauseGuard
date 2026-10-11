# ADR 0003 — Classifier behind an interface, with a keyword baseline

**Status:** Accepted
**Date:** 2026-10-07
**Phase:** 3

## Context

The clause-type classifier is the long-lead item in this project: it needs the
CUAD download, the span-to-clause conversion, a manual audit of that
conversion, and GPU time to fine-tune. Meanwhile every other phase depends on
*something* producing clause types — the risk rubric cannot evaluate a clause
until it knows what kind of clause it is, so the rubric, the report, the PDF
export and the frontend would all be unbuildable and untestable until training
finished.

Two further constraints:

- `torch` and `transformers` add roughly 2.5 GB to the backend image. Carrying
  that before a checkpoint exists makes every build slow for no benefit.
- SRS 5.4 requires the classification pipeline to degrade gracefully, and
  SRS 5.4 Maintainability requires the models to be swappable independently of
  the surrounding application.

## Decision

Define a `Classifier` protocol — `classify(texts) -> list[list[Prediction]]`
plus a `model_version` string — and provide two implementations:

1. **`TransformerClassifier`**, loading a fine-tuned checkpoint from
   `CLAUSEGUARD_MODEL_DIR`, with per-class thresholds from `thresholds.json`.
2. **`BaselineClassifier`**, scoring keyword cues declared alongside each class
   in `labels.py`.

`get_classifier()` selects the transformer when a checkpoint is present and
loadable, and the baseline otherwise. `torch` and `transformers` stay out of
`backend/requirements.txt` and live in `ml/requirements.txt`.

## Why a baseline rather than failing closed

A system that returns 500 until the model is trained cannot be developed
against. The baseline makes the entire pipeline runnable and testable from
Phase 3 onward, and it is what allowed the rubric's defects to be found against
real end-to-end output rather than hand-constructed label sets — four rubric
bugs surfaced that way.

It also satisfies SRS 5.4: a missing or corrupt checkpoint degrades to weaker
predictions rather than taking down the report.

## Guarding against mistaking the baseline for a trained model

This is the obvious hazard, and it is addressed structurally rather than by
documentation alone:

- The baseline's `model_version` is `baseline-keyword-v1`. That string is
  stored on **every prediction row**, stamped on **every report**, printed in
  the **PDF footer provenance line**, and returned by **`/api/v1/health`**.
  There is no path by which a baseline-produced report looks like a trained one.
- Baseline confidence is capped at **0.80** (`BASELINE_CONFIDENCE_CEILING`).
  Keyword matching is uncalibrated, and letting it emit 0.95 would assert a
  certainty SRS 5.2 forbids.
- `measure_latency.py` prints an explicit warning when the model version starts
  with `baseline-`, so a latency result cannot be mistaken for verification of
  SRS 5.1.

## Consequences

- Reported accuracy with the baseline is **not** a result. `ml/MODEL_CARD.md`
  stays the place where real metrics go, and they require the trained model.
- Label order is read from the checkpoint's `id2label`, not from `LABEL_KEYS`
  positionally. If the taxonomy is ever reordered, a positional mapping would
  silently relabel every prediction; reading from the checkpoint turns that
  into a loud `ValueError` instead.
- The baseline's cues live beside the class definitions in `labels.py`, so a
  new clause type gets both its taxonomy entry and its fallback behaviour in
  one place.
- Serving a trained model means installing `ml/requirements.txt` into the
  backend environment and setting `CLAUSEGUARD_MODEL_DIR`. Nothing else
  changes — no code edit, no schema change.
