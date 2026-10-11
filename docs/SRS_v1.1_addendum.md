# SRS v1.1 — Addendum to v1.0

**Base document:** `24BPS1042.pdf`, ClauseGuard SRS v1.0, approved 15/07/2026
**Addendum date:** 2026-10-02
**Author:** Tanmaya Gupta (24BPS1042)

This addendum records changes to SRS v1.0 made during Phase 0 of
implementation. Its sole substantive purpose is to **close every item in
Appendix C (To Be Determined List)**. Section numbering follows v1.0.

Nothing in v1.0 is withdrawn. Where a value is specified here, it replaces the
corresponding `[TBD-n]` placeholder in v1.0.

---

## A. Appendix C resolutions

### TBD-1 — Maximum accepted file size for upload
**Affects:** REQ-1.2
**Resolved value: 10 MB (10,485,760 bytes).**

A 20-page text-extractable contract is typically under 2 MB. A 10 MB ceiling
accommodates image-heavy and poorly-exported documents while bounding
per-request server memory. Enforced twice: client-side before transfer, for a
fast error message, and server-side against `Content-Length`, because a
client-side check is a convenience and not a control.

REQ-1.2 now reads: *The system shall reject files exceeding 10 MB with a clear,
non-technical error message.*

### TBD-2 — Minimum confidence threshold
**Affects:** REQ-3.4
**Resolved value: 0.45 global floor, with per-class thresholds tuned on the
validation split.**

A single global threshold over a 20-label, heavily imbalanced multi-label task
trades away recall on rare classes. The system therefore applies a per-class
threshold table produced during training, with 0.45 as the floor below which no
label is emitted regardless of class. Both the floor and the fitted table are
recorded in `ml/MODEL_CARD.md` so that any report can be reproduced.

A clause with no label above its class threshold is labelled `Uncategorized`
and surfaced as such, per REQ-3.4.

### TBD-3 — Target processing time
**Affects:** §5.1
**Resolved value: 95th-percentile end-to-end processing ≤ 30 seconds** for a
contract of up to 20 pages / 50 clauses, on 2 vCPU with no GPU.

Component budget:

| Stage | Expected |
|---|---|
| Text extraction (PyMuPDF / python-docx) | ~2 s |
| Segmentation | < 1 s |
| Clause classification, 50 clauses batched at 256 tokens, DistilBERT on CPU | 6–10 s |
| Rubric evaluation | < 1 s |
| Report assembly | < 1 s |

Expected total is ~15 s; 30 s is stated to leave headroom for cold model load
and contention. This figure is to be **measured in Phase 8**, not assumed, and
revised in v1.2 if measurement contradicts it.

### TBD-4 — Target number of concurrent uploads
**Affects:** §5.1
**Resolved value: 5 simultaneous analyses.**

One API container with 2 Uvicorn workers and a bounded job queue of depth 5.
Requests arriving beyond that are queued rather than rejected, and the
Processing Screen reports a queued state. This is sized for the demonstration
and evaluation load described in §2.4, not for production multi-tenancy.

### TBD-5 — Exact final list of Indian templates
**Affects:** §2.7
**Resolved:** the domain-adaptation corpus draws on

1. Government e-Marketplace (GeM) General Terms and Conditions.
2. Model contract forms published under the Indian Contract Act, 1872.
3. MSME Samadhaan and MSMED Act, 2006 reference material, for payment-term and
   interest provisions.
4. Material contracts in public company disclosures filed with BSE / NSE.
5. Publicly available law-firm and industry-body template repositories.
6. Synthetic Indian vendor, NDA and service agreements, each manually reviewed
   before inclusion.

Target size: **150–200 hand-labelled clauses**, used as a held-out evaluation
set reported separately from CUAD metrics. Provenance and licence are recorded
per source in `ml/MODEL_CARD.md`. No paywalled or licence-restricted material
is scraped.

### TBD-6 — Detailed UI wireframes / style guide
**Affects:** §3.1
**Resolved:** deferred to a separate design document at `docs/wireframes/`,
referenced but not reproduced here, so that the SRS remains a requirements
document. Five screens are in scope for V1.0: Upload, Processing, Report,
Dashboard, Authentication. Low-fidelity wireframes in Figma; implementation
uses Tailwind CSS with shadcn/ui components.

### TBD-7 — OCR support inclusion
**Affects:** §2.7, REQ-1.4
**Resolved: out of scope for V1.0.** The system detects an image-only PDF and
rejects it with the guidance REQ-1.4 already specifies; it does not attempt
optical character recognition.

§2.7 already assumes text-extractable input. Adding OCR would introduce a
silent accuracy-degradation path — recognition errors would propagate into
clause text, then into classification, then into risk findings, with no signal
to the user that the chain started from an imperfect transcription. Listed as
future work.

---

## B. Consequential changes

### §2.4 Operating Environment
PostgreSQL 16 is used in place of the stated minimum of 14+. The requirement
said "14+"; this records which version is actually deployed and tested.

Python 3.12 is used for the backend runtime, within the stated "3.10+".

### §2.5 Design and Implementation Constraints
The constraint names Legal-BERT **or** DistilBERT. The implementation fine-tunes
**DistilBERT as the primary served model**, with Legal-BERT trained under
identical data and splits as a reported comparison. Rationale: §2.4 mandates
CPU-based inference, and DistilBERT is roughly twice as fast, which is what
makes the TBD-3 latency budget achievable. The comparison is reported so the
choice is evidenced rather than asserted.

### §4.3 Clause-Type Classification
The taxonomy is fixed at **20 classes**, within the 15–20 range §2.5 permits.
Five of them — Termination for Cause & Cure, Late Payment / Interest / GST,
Confidentiality, Dispute Resolution & Arbitration, and Force Majeure — are thin
or absent in CUAD and depend on the TBD-5 corpus. Per-class F1 is reported for
all 20 so that weakness on these is visible rather than hidden in an aggregate.

### §5.1 Performance Requirements
Both placeholders are now numeric (TBD-3, TBD-4) and therefore testable.
Phase 8 adds the measurement that verifies them.

---

## C. Still open

Nothing from Appendix C remains open. The following are **deliberately deferred
beyond V1.0** and are not defects in this specification:

- OCR for scanned contracts (TBD-7).
- Internationalisation / non-English contracts (§6, already out of scope in v1.0).
- Admin tooling for the Admin/Operator user class in §2.3 beyond direct
  database access.
