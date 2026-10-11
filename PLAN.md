# ClauseGuard — Implementation Plan

**Project:** ClauseGuard: AI-Powered Contract Risk Analyzer for Indian MSMEs
**Author:** Tanmaya Gupta (24BPS1042), VIT Chennai
**Source of truth:** `24BPS1042.pdf` (SRS v1.0, 15/07/2026)
**Plan date:** 2026-10-02

---

## 0. Decisions taken before planning

| Decision | Choice | Why |
|---|---|---|
| Classifier backbone | Fine-tune **DistilBERT** first; Legal-BERT as a swap-in experiment | CPU inference is an SRS constraint (§2.4). DistilBERT is ~2x faster and fits the latency budget; Legal-BERT is trained as a comparison row in the results table, satisfying §2.5 while keeping the demo responsive. |
| Scope weight | **All six System Features** (§4.1–4.6), full-stack | The rubric rewards requirements traceability. A half-built feature set reads worse than a complete one with a modest model. |
| Appendix C TBDs | **Resolved with concrete values** (see §7) | Unresolved TBDs block testable acceptance criteria. |

---

## 1. What makes this project defensible

The SRS already contains the strongest idea in the project, and the build must not blur it:

> **Clause-type classification is learned. Risk scoring is NOT.**

Clause typing is an ML problem (REQ-3.1–3.4). Risk scoring is a **rule engine over a versioned, human-readable rubric** (REQ-4.2, REQ-4.4, §5.5). This separation is what delivers the Explainability quality attribute (§5.4) and is the single most important architectural invariant in the codebase. Every risk label traces to a named rule in a YAML file, and every report records which rubric version produced it.

The second defensible idea: the risk engine does **absence detection**, not just keyword matching. Knowing a clause is a *Termination for Cause* clause is what lets the engine notice that it contains no cure period. That dependency — classification feeding the rubric — is why the two layers are decoupled but ordered.

---

## 2. Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│ React SPA (Vite + TS)                                            │
│  Upload · Processing · Report · Dashboard · Export               │
└───────────────────────────┬──────────────────────────────────────┘
                            │ HTTPS / JSON / JWT
┌───────────────────────────▼──────────────────────────────────────┐
│ FastAPI                                                          │
│  /auth  /contracts  /contracts/{id}/status  /reports  /health    │
└───┬──────────────────────────────────────────────────────┬───────┘
    │ background job (one per upload)                      │
    ▼                                                      ▼
┌─────────────────────────────────────────────┐     ┌───────────────┐
│ PIPELINE (each stage independently testable)│     │ PostgreSQL 14+│
│ 1 extract   PyMuPDF / python-docx           │◄───►│ users         │
│ 2 segment   regex + heading + pysbd         │     │ contracts     │
│ 3 classify  DistilBERT multi-label (CPU)    │     │ clauses       │
│ 4 score     rubric engine ← rubrics/v1.0.yml│     │ predictions   │
│ 5 report    WeasyPrint → PDF                │     │ risk_findings │
└─────────────────────────────────────────────┘     │ reports       │
                                                    │ rubric_vers   │
                                                    └───────────────┘
```

Each pipeline stage is a pure function `(input, config) -> output` with no HTTP or DB awareness. The orchestrator owns persistence. This is what makes stage 3 and stage 4 swappable (§5.4 Maintainability, §6 Reuse objective).

### Repository layout

```
clauseguard/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/            config, security (JWT, bcrypt), logging
│   │   ├── api/v1/          auth.py contracts.py reports.py health.py
│   │   ├── db/              models.py session.py  + alembic/
│   │   ├── schemas/         pydantic request/response models
│   │   ├── services/
│   │   │   ├── extraction/      pdf.py docx.py  (raises EmptyTextError)
│   │   │   ├── segmentation/    segmenter.py rules.py
│   │   │   ├── classification/  model.py labels.py  (lazy singleton)
│   │   │   ├── risk/            engine.py loader.py detectors/ rubrics/v1.0.yaml
│   │   │   └── reporting/       pdf_renderer.py templates/
│   │   └── pipeline.py      orchestrator + status transitions
│   └── tests/               unit per stage + api integration
├── ml/
│   ├── scripts/             prepare_cuad.py train.py evaluate.py export.py
│   ├── data/                raw/ processed/   (gitignored)
│   ├── configs/             distilbert.yaml legalbert.yaml
│   ├── eval/                indian_eval_set.jsonl  (hand-labelled)
│   └── MODEL_CARD.md        provenance + label mapping  (§6 Data requirement)
├── frontend/src/            pages/ components/ api/ hooks/
├── docs/
│   ├── SRS_v1.1.md          TBDs resolved
│   ├── TRACEABILITY.md      REQ-x.y → module → test
│   ├── RUBRIC.md            every rule, criterion, citation
│   └── ERD.png  wireframes/  ADRs/
├── docker-compose.yml       api · db · frontend
└── README.md
```

---

## 3. Data model

```
users(id, email UNIQUE, password_hash, created_at)

contracts(id, user_id→users, filename, mime, size_bytes, storage_path,
          raw_text, status, status_detail, error_code, uploaded_at, processed_at)

clauses(id, contract_id→contracts, ordinal, heading, text, char_start, char_end,
        segmentation_method, needs_manual_review)          -- REQ-2.2, REQ-2.4

clause_predictions(id, clause_id→clauses, label, confidence, model_version)
        -- multi-label: N rows per clause; zero rows ⇒ "Uncategorized"  REQ-3.2/3.4

risk_findings(id, clause_id→clauses, rule_id, severity, explanation, rubric_version)
                                                           -- REQ-4.2/4.3

clause_risk(clause_id PK, level, rubric_version)  -- max severity, or 'unassessable'

reports(id, contract_id, rubric_version, model_version, summary_json, generated_at)

rubric_versions(version PK, yaml_sha256, activated_at, notes)   -- §5.5 auditability
```

`status` enum: `uploaded → extracting → segmenting → classifying → scoring → complete | failed`. The Processing Screen (§3.1) polls this; the enum *is* the "live extraction, segmentation, ML computation states" the SRS asks for.

`rubric_version` denormalised onto findings and reports is deliberate: it is how a historical report stays explainable against the rubric that produced it (§5.5), even after the rubric evolves.

---

## 4. The ML layer

### 4.1 CUAD is not a classification dataset — it must be converted

CUAD ships as SQuAD-style **span extraction** over 510 contracts and 41 categories ("highlight the text answering: does this contract contain an indemnity clause?"). Converting it to multi-label clause classification is real work and is the piece most likely to be underestimated:

1. Parse each contract's annotated spans; map each span to its CUAD category.
2. Segment every contract with **the same segmenter used at inference time** — train/serve skew here silently destroys accuracy.
3. A clause gets label *L* if an *L*-span overlaps it past an IoU threshold (start at 0.5, tune).
4. Clauses with no overlapping span become negatives — but only after discarding boilerplate (signature blocks, schedules, tables of contents), which otherwise floods the negative class.
5. Split **by contract, never by clause** — clauses from one contract leak heavily.
6. Record every mapping decision in `ml/MODEL_CARD.md` (§6 Data requirement).

### 4.2 Label taxonomy: 41 CUAD categories → 20 MSME-relevant classes

CUAD's 41 categories are M&A-flavoured (`Rofr/Rofo/Rofn`, `Joint IP Ownership`, `Volume Restriction`) and brutally imbalanced. Collapse and localise to 20 classes, which lands inside the SRS's 15–20 budget (§2.5):

| # | Class | Collapsed from CUAD / origin |
|---|---|---|
| 1 | Parties & Definitions | Parties, Document Name |
| 2 | Term & Effective Date | Agreement Date, Effective Date, Expiration Date |
| 3 | Renewal & Auto-Renewal | Renewal Term, Notice Period To Terminate Renewal |
| 4 | Termination for Convenience | Termination For Convenience |
| 5 | Termination for Cause & Cure | *(Indian templates — thin in CUAD)* |
| 6 | Payment Terms & Pricing | Price Restrictions, Minimum Commitment, Revenue/Profit Sharing |
| 7 | **Late Payment, Interest & GST** | **Indian addition** — MSMED Act §15 |
| 8 | Indemnity | Insurance-adjacent + Indian templates |
| 9 | Limitation of Liability | Cap On Liability, Uncapped Liability |
| 10 | Warranties & Representations | Warranty Duration |
| 11 | Confidentiality | *(Indian templates + NDA corpus)* |
| 12 | IP Ownership & Licence | IP Ownership Assignment, License Grant, Joint IP Ownership |
| 13 | Exclusivity & Non-Compete | Exclusivity, Non-Compete, No-Solicit (both) |
| 14 | Assignment & Change of Control | Anti-Assignment, Change Of Control |
| 15 | Governing Law & Jurisdiction | Governing Law |
| 16 | **Dispute Resolution & Arbitration** | **Indian addition** — Arbitration & Conciliation Act 1996 |
| 17 | Force Majeure | *(Indian templates)* |
| 18 | Audit, Inspection & Compliance | Audit Rights |
| 19 | Insurance | Insurance |
| 20 | Notices & Miscellaneous | Notice |

Classes 5, 7, 11, 16 and 17 are thin or absent in CUAD — they are exactly why the domain-adaptation corpus (§2.7) is a hard dependency rather than a nice-to-have.

### 4.3 Training

- `DistilBertForSequenceClassification`, `problem_type="multi_label_classification"`, 20 sigmoid heads, BCEWithLogits.
- `max_length=256` with sliding-window + max-pool over windows for long clauses — contract clauses routinely exceed 512 tokens.
- Class-weighted or focal loss; imbalance is severe (Governing Law appears in nearly every contract, Joint IP in a handful).
- Thresholds tuned **per class** on validation for best F1, not a single global 0.5.
- Report **macro-F1 and per-class P/R/F1**, not accuracy. Accuracy on a 20-label imbalanced multi-label task is meaningless and an evaluator will say so.
- Two runs for the results table: DistilBERT vs Legal-BERT, identical data and splits.
- Google Colab free T4 is sufficient; ~3 epochs over ~25–40k clause instances fits well inside a session limit.
- Export to ONNX + `onnxruntime` for CPU inference — but measure first. If plain PyTorch CPU already hits the latency budget, skip ONNX as unnecessary complexity.

### 4.4 Honest evaluation on the actual target domain

CUAD test-set F1 measures performance on US M&A contracts. The product targets Indian MSME vendor agreements. So: hand-label **150–200 clauses** from Indian templates as `ml/eval/indian_eval_set.jsonl` and report metrics on **both** sets. The gap between them is a genuine finding and a far stronger results section than one inflated number.

---

## 5. The risk rubric engine

A versioned YAML file, loaded at startup, hash-recorded in `rubric_versions`. Shape:

```yaml
version: "1.0"
rules:
  - id: uncapped_liability
    applies_to: [limitation_of_liability, indemnity]
    severity: high
    detect:
      absent_any: ["shall not exceed", "limited to", "aggregate liability",
                   "maximum liability", "capped at"]
    explanation: >
      This clause makes you responsible for losses with no upper limit. If
      something goes wrong, your exposure could exceed the entire value of
      this contract. Ask for liability to be capped — commonly at the total
      fees paid in the preceding 12 months.
    criterion: "Absence of a monetary cap on liability exposure."

  - id: payment_term_over_45_days
    applies_to: [payment_terms, late_payment_interest_gst]
    severity: caution
    detect:
      numeric_days_gt: 45
    explanation: >
      Payment is due more than 45 days after invoice. Under the MSMED Act,
      2006, a buyer must pay a registered micro or small enterprise within
      45 days. A longer term written into the contract does not remove that
      statutory right.
    criterion: "MSMED Act, 2006 §15 — 45-day statutory payment ceiling."

  - id: auto_renew_without_notice_window
    applies_to: [renewal_auto_renewal]
    severity: high
    detect:
      absent_pattern: "\\d+\\s*(days?|months?)"
    explanation: >
      This contract renews itself automatically and does not state how much
      notice you must give to stop it. You could be locked into another full
      term without meaning to.
    criterion: "Auto-renewal lacking a specified opt-out notice window."
```

**Detector primitives** (`services/risk/detectors/`): `present_any`, `absent_any`, `absent_pattern`, `numeric_days_gt`, `numeric_days_lt`, `one_sided_obligation`, `foreign_jurisdiction`, `unbounded_duration`. Composable, each unit-tested against fixture clauses.

**Asymmetry detection** (`one_sided_obligation`) is the most interesting detector. Resolve party roles once per contract from the Parties clause (supplier / vendor / service-provider vs customer / client / buyer), then check which role is the grammatical subject of the obligation verb. If only the user's likely side bears the duty and there is no reciprocal sentence, fire. Ship a conservative keyword version first; upgrade to a spaCy dependency-parse version only if time allows — the rubric's rule-level isolation means that upgrade touches one file.

**Target rubric: ~18–22 rules.** Opening set: uncapped liability · one-sided indemnity · unilateral termination · no cure period · auto-renew without notice · payment term >45 days · no late-payment interest · unilateral price variation · foreign governing law · foreign arbitration seat · perpetual or unbounded confidentiality · broad assignment of pre-existing IP · exclusivity without volume commitment · post-term non-compete · anti-assignment binding one side only · no force majeure clause present · unlimited audit rights · liquidated damages without reciprocity.

**Composition:** clause risk = highest severity among fired rules. Zero fired rules with a confident type ⇒ Safe. Classifier returned `Uncategorized`, or the engine raised ⇒ `Unable to assess` (§5.4 Reliability — never fail the whole report).

Every rule's `criterion` and `explanation` is dumped into `docs/RUBRIC.md` by a script, so the documentation cannot drift from the code.

---

## 6. Build phases

Ten weeks, each phase ending in something demonstrable. Phases 2 and 3 run in parallel — the ML track is the long-lead item and should start as early as possible.

| Phase | Weeks | Deliverable | Satisfies |
|---|---|---|---|
| **0 · Foundation** | 1 | Repo, docker-compose (api+db), Alembic migrations, `/health`, CI running pytest, SRS v1.1 with TBDs closed | §2.4, App. C |
| **1 · Ingest** | 1–2 | Upload endpoint, PDF/DOCX extraction, size and type validation, empty-text rejection, file storage, status machine | REQ-1.1–1.5 |
| **2 · Segmentation** | 2–3 | Numbering / heading / paragraph cascade + pysbd, stable clause IDs, ambiguity flagging, fixture test suite | REQ-2.1–2.4 |
| **3 · ML** (parallel, start wk 2) | 2–6 | `prepare_cuad.py`, taxonomy mapping, trained DistilBERT, Legal-BERT comparison, per-class thresholds, Indian eval set, MODEL_CARD | REQ-3.1–3.4, §6 |
| **4 · Risk engine** | 4–6 | Rubric YAML v1.0 with ~20 rules, detector primitives, engine, `docs/RUBRIC.md` generator, graceful degradation | REQ-4.1–4.4, §5.4 |
| **5 · Auth & persistence** | 5–6 | Register / login, bcrypt, JWT, per-user data scoping, contract deletion | REQ-6.1–6.2, §5.3 |
| **6 · Frontend** | 6–8 | All five screens, polling processing view, colour-coded report, expandable explanation panels, dashboard with history and trend | §3.1, REQ-5.1/5.2/5.4, REQ-6.3/6.4 |
| **7 · Report export** | 8 | WeasyPrint PDF matching the web report, summary header, disclaimer on every page | REQ-5.3, §5.2 |
| **8 · NFR hardening** | 8–9 | Latency measured against budget, concurrency test, HTTPS/TLS config, tooltips / user guide / glossary / FAQ, traceability matrix | §5.1–5.5, §2.6 |
| **9 · Deliverables** | 9–10 | Deployment, README, ERD, wireframes, demo script, results tables, viva prep | — |

**Critical path:** the CUAD conversion in §4.1, steps 1–2. If the span-to-clause mapping produces garbage labels, everything downstream is built on sand. Validate it in week 2 by eyeballing 50 mapped clauses by hand before training anything.

---

## 7. Appendix C — TBDs resolved

| # | Item | Value | Justification |
|---|---|---|---|
| 1 | Max upload size | **10 MB** | A 20-page text-extractable contract is under 2 MB. 10 MB absorbs image-heavy and badly-exported files while bounding per-request server memory. Enforced client-side *and* server-side. |
| 2 | Min confidence threshold | **0.45 global floor, per-class thresholds tuned on validation** | A single global threshold on a 20-label imbalanced multi-label task sacrifices rare-class recall. Both the floor and the per-class table live in the model card; below the floor ⇒ `Uncategorized` (REQ-3.4). |
| 3 | Target processing time | **p95 ≤ 30 s** for ≤20 pages / ≤50 clauses on 2 vCPU | Budget: extraction ~2 s, segmentation <1 s, DistilBERT over 50 × 256-token clauses batched on CPU ~6–10 s, rubric <1 s. ~15 s expected; 30 s stated for headroom. Measured in Phase 8, not assumed. |
| 4 | Concurrent uploads | **5** | One container, 2 Uvicorn workers, bounded job queue of depth 5; requests beyond that queue rather than drop. Sized for the academic demo load in §2.4. |
| 5 | Indian template sources | GeM General Terms & Conditions; model forms under the Indian Contract Act, 1872; MSME Samadhaan / MSMED Act, 2006 reference material; publicly filed material contracts from BSE/NSE disclosures; publicly available law-firm template repositories; plus synthetic Indian vendor / NDA / service agreements, each manually reviewed before inclusion. Target 150–200 hand-labelled clauses. | Provenance and licence recorded per source in the model card. No scraping of paywalled or licence-restricted material. |
| 6 | Wireframes / style guide | Separate design doc at `docs/wireframes/`. Five screens: Upload, Processing, Report, Dashboard, Auth. Low-fidelity Figma; Tailwind + shadcn/ui for implementation. | Keeps the SRS a requirements document rather than a design document. |
| 7 | OCR support | **Out of scope for V1.0.** Detect-and-reject only, per REQ-1.4. | §2.7 already assumes text-extractable input. Listed as future work; adding Tesseract would introduce an accuracy-degradation path the rubric layer cannot account for. |

---

## 8. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| CUAD span-to-clause mapping yields noisy labels | Fatal to the ML story | Manual audit of 50 mapped clauses in week 2, before training. Tune the IoU threshold against that audit. |
| Train/serve segmenter skew | Silent accuracy collapse | One segmenter module, imported by both `prepare_cuad.py` and the API. Enforced by a test. |
| Indian-domain classes absent from CUAD (5, 7, 11, 16, 17) | Weak predictions on the most MSME-relevant clauses | Domain corpus started in week 2, not week 6. Report per-class F1 so the weakness is visible and discussed rather than hidden. |
| Over-engineering the asymmetry detector | Burns the frontend's time budget | Keyword version in Phase 4; dependency-parse upgrade only if Phase 6 lands early. |
| CPU latency misses the 30 s budget | NFR failure | Measure in Phase 3 as soon as a model exists. Escape hatches: ONNX export, shorter `max_length`, batch tuning. |
| Scope creep into OCR or multilingual | Timeline loss | Both explicitly closed in §7. |

---

## 9. Next step

Scaffold Phase 0: repo structure, `docker-compose.yml`, Alembic baseline migration for the §3 schema, `/health`, pytest + CI, and `docs/SRS_v1.1.md` carrying the §7 resolutions.
