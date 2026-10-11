# ML pipeline

The clause-**type** classifier lives here. The risk **rubric** does not — it is
rule-based and lives in `backend/app/services/risk/`. Keeping them apart is the
architectural invariant described in `PLAN.md` §1, and the reason every risk
flag can be explained without interpreting model internals.

## Layout

```
ml/
├── scripts/
│   ├── prepare_cuad.py    CUAD span annotations → multi-label clause dataset
│   ├── train.py           fine-tune, write checkpoint + threshold table
│   ├── evaluate.py        macro/per-class F1 on CUAD test and Indian eval set
│   └── export.py          checkpoint → ONNX for CPU inference
├── configs/
│   ├── distilbert.yaml    served model
│   ├── legalbert.yaml     comparison run
│   └── label_mapping.yaml CUAD's 41 categories → the 20 classes
├── data/
│   ├── raw/               CUAD download + Indian templates  (gitignored)
│   └── processed/         converted dataset                 (gitignored)
├── eval/
│   └── indian_eval_set.jsonl   150–200 hand-labelled Indian clauses
└── MODEL_CARD.md          provenance, metrics, limitations (SRS §6)
```

`data/` is gitignored: CUAD is large and redistributing it is unnecessary when
it is publicly downloadable, and some Indian source documents have per-source
licence terms recorded in the model card.

## Order of work (Phase 3)

1. **`prepare_cuad.py` first, and audit its output before training anything.**
   CUAD ships as SQuAD-format span extraction, so conversion to multi-label
   classification involves real judgement calls (IoU threshold, negative
   sampling, boilerplate removal). Hand-check 50 converted clauses. If the
   mapping is wrong, every metric downstream is meaningless and you will not
   find out from the loss curve.
2. **Import the production segmenter, do not reimplement it.**
   `prepare_cuad.py` must call `backend/app/services/segmentation/`. A separate
   training-time segmenter is the classic train/serve skew bug: the model learns
   on text shaped one way and is served text shaped another, and accuracy
   degrades silently.
3. **Split by contract, not by clause.** Clauses within a contract share
   drafting style and vocabulary; a clause-level split leaks and inflates every
   number.
4. Train DistilBERT, then Legal-BERT on identical splits.
5. Fit per-class thresholds on validation (TBD-2 floor: 0.45).
6. Evaluate on both CUAD test **and** `eval/indian_eval_set.jsonl`, and report
   both. The gap is the interesting result.
7. Fill in `MODEL_CARD.md` as you go, not afterwards.

## Reporting

Report **macro-F1 and per-class precision/recall/F1**. Do not report accuracy:
with 20 imbalanced labels it is dominated by true negatives and will look
impressive while meaning nothing.

## Environment

The ML dependencies (`torch`, `transformers`, `onnxruntime`) are deliberately
absent from `backend/requirements.txt` until Phase 3, so that Phase 0–2 images
stay small and fast to build. Training runs on Google Colab (free T4 is
sufficient for ~3 epochs); only inference runs in the backend container.
