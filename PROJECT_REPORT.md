# ClauseGuard: AI-Powered Contract Risk Analyzer for Indian MSMEs

## Software Engineering Project Report

| | |
|---|---|
| **Student** | Tanmaya Gupta |
| **Registration Number** | 24BPS1042 |
| **Institution** | VIT Chennai |
| **Requirements Document** | `24BPS1042.pdf` (SRS v1.0, approved 15/07/2026) |
| **Requirements Addendum** | `docs/SRS_v1.1_addendum.md` |
| **Report Date** | 7 October 2026 |

---

## Table of Contents

1. [Abstract](#1-abstract)
2. [Introduction and Problem Statement](#2-introduction-and-problem-statement)
3. [Objectives and Scope](#3-objectives-and-scope)
4. [Literature and Dataset Background](#4-literature-and-dataset-background)
5. [Core Design Principle](#5-core-design-principle)
6. [System Architecture](#6-system-architecture)
7. [Database Design](#7-database-design)
8. [Module-by-Module Implementation](#8-module-by-module-implementation)
9. [The Clause-Type Taxonomy](#9-the-clause-type-taxonomy)
10. [The Risk Rubric](#10-the-risk-rubric)
11. [Machine Learning Pipeline](#11-machine-learning-pipeline)
12. [Technology Stack and Justification](#12-technology-stack-and-justification)
13. [Deployment and How to Run the System](#13-deployment-and-how-to-run-the-system)
14. [Functional Capabilities](#14-functional-capabilities)
15. [Testing and Verification](#15-testing-and-verification)
16. [Results and Measurements](#16-results-and-measurements)
17. [Defects Found During Development](#17-defects-found-during-development)
18. [Resolution of the TBD List](#18-resolution-of-the-tbd-list)
19. [Limitations and Honest Gaps](#19-limitations-and-honest-gaps)
20. [Future Work](#20-future-work)
21. [Conclusion](#21-conclusion)
22. [Appendix A: Repository Map](#appendix-a-repository-map)
23. [Appendix B: Design Decision Records](#appendix-b-design-decision-records)
24. [Appendix C: Anticipated Viva Questions](#appendix-c-anticipated-viva-questions)
25. [References](#references)

---

## 1. Abstract

ClauseGuard is a full-stack web application that performs automated risk triage
on commercial contracts for Indian Micro, Small and Medium Enterprises (MSMEs).
A user uploads a vendor, supply, NDA or service agreement in PDF or DOCX
format. The system segments the document into individual clauses, classifies
each clause by legal type using a fine-tuned transformer, evaluates each clause
against a documented fairness rubric, and produces a colour-coded,
clause-by-clause report explaining in plain language why each flagged clause is
risky.

The system's central design decision is the separation of two distinct
inference problems: **clause-type classification is a machine learning task,
while risk scoring is a deterministic rule engine over a version-controlled
rubric.** This separation is what makes every risk judgement explainable and
auditable, satisfying the Explainability requirement that the SRS treats as a
first-class non-functional requirement rather than an optional nicety.

The product's purpose is not to replace legal counsel but to triage: to
identify cheaply and quickly which two or three clauses in a twenty-clause
contract actually warrant a paid legal opinion.

All nine planned development phases have been implemented and verified. The
system passes 119 automated tests, runs as a three-container Docker stack, and
processes a fifty-clause contract in 0.2 seconds against a thirty-second
budget. The one component not completed is the transformer fine-tuning run
itself, which requires the CUAD dataset download and GPU time; all scripts for
it are complete and the dataset conversion logic has been verified against a
synthetic dataset.

---

## 2. Introduction and Problem Statement

### 2.1 The commercial problem

Indian MSMEs routinely sign contracts without access to in-house legal counsel.
Engaging a lawyer to review every agreement is not economically viable for a
business operating on thin margins, so contracts are frequently signed
unreviewed.

The consequences are concentrated in a small number of clause types:

- **One-sided indemnity** — the smaller party agrees to cover all losses, with
  no reciprocal protection.
- **Unlimited liability** — no monetary ceiling on exposure, so a single
  dispute can exceed the entire value of the contract.
- **Silent auto-renewal** — the agreement renews itself with no stated opt-out
  window, locking the business into another full term unintentionally.
- **Unilateral termination** — only the counterparty may walk away, leaving the
  MSME's revenue stream unprotected.
- **Extended payment terms** — ninety-day payment cycles that strain the
  working capital of a small supplier.

These clauses are not hidden. They are in plain sight, in a document the
business owner has read. The difficulty is that recognising them requires
knowing what a *balanced* version of each clause looks like — which is exactly
the expertise the MSME lacks.

### 2.2 Why automation is appropriate here

The task has a shape that suits automation:

1. The risky patterns are **recurrent** across contracts and industries.
2. Many are defined by **absence** — a missing liability cap, a missing cure
   period — which software detects more reliably than a reader skimming under
   time pressure.
3. The output needed is not a legal opinion but a **prioritised list of
   questions**, which does not require professional judgement to produce.

### 2.3 What the system deliberately does not do

ClauseGuard does not provide legal advice, and does not represent its output as
such. It has no knowledge of the user's business, their relationship with the
counterparty, or their commercial priorities — all of which change what a clause
actually means in practice. A persistent disclaimer appears on every screen, in
every API response, and in the footer of every page of the exported PDF.

This is not a legal formality. The SRS identifies it as an
**informational-safety** concern: an incorrect reassurance could cause a user to
sign a genuinely one-sided contract believing it had been checked. The system is
therefore designed to never assert certainty, and to report a clause as "not
assessed" rather than "safe" when it could not form a judgement.

---

## 3. Objectives and Scope

### 3.1 Primary objectives

| # | Objective |
|---|---|
| O1 | Accept contract uploads in PDF and DOCX format and extract their text reliably |
| O2 | Divide a contract into individually meaningful clauses |
| O3 | Classify each clause into one or more of approximately twenty legal categories |
| O4 | Assign each clause a three-tier risk level against documented, auditable criteria |
| O5 | Generate a plain-language explanation for every risk flag raised |
| O6 | Present a colour-coded in-app report and an exportable PDF |
| O7 | Provide secure accounts with per-user data isolation and contract history |
| O8 | Ensure the risk criteria are relevant to Indian commercial and statutory norms |

### 3.2 In scope for version 1.0

- English-language contracts
- Text-extractable PDF and DOCX files
- Twenty clause-type categories
- A three-tier risk grading scale
- Single-user accounts with contract history

### 3.3 Explicitly out of scope for version 1.0

| Excluded | Reason |
|---|---|
| OCR for scanned contracts | Recognition errors would propagate silently through clause text into classification and then into risk findings, with no signal to the user that the chain began with an imperfect transcription |
| Non-English contracts | Stated as out of scope in the SRS |
| Multi-user organisations and role-based access | Beyond the version 1.0 user model |
| Contract drafting or clause rewriting | The product is diagnostic, not generative |

---

## 4. Literature and Dataset Background

### 4.1 CUAD (Contract Understanding Atticus Dataset)

CUAD is the base dataset for clause-type classification: 510 commercial
contracts annotated by legal experts across 41 clause categories.

**A critical property of CUAD, and the single most underestimated aspect of this
project: CUAD is not a classification dataset.** It is distributed in SQuAD
format as a *span extraction* task. Each of the 41 categories is phrased as a
question — "Highlight the parts of this contract related to *Governing Law*" —
and the annotation is a highlighted character span within the contract text.

Converting this into a multi-label clause-classification dataset requires a
deliberate procedure with several judgement calls, documented in Section 11.

CUAD's second relevant property is its **domain**: it consists of long-form,
US-centric, mergers-and-acquisitions-oriented corporate contracts. The target
domain of this project is short-form Indian vendor and supply agreements. These
differ in length, vocabulary and drafting convention, and the gap between them
is a genuine research finding rather than an inconvenience to be concealed.

### 4.2 CLAUDETTE and the UNFAIR-ToS line of work

The CLAUDETTE project established the task of detecting potentially unfair
clauses, operating on **consumer Terms of Service**. ClauseGuard's risk layer is
*inspired by* this body of work but is not a reimplementation of it: the
contractual context here is business-to-business vendor and supply agreements in
the Indian commercial setting, where the fairness norms, the statutory backdrop
and the parties' relative positions are all different.

### 4.3 Legal-BERT

Legal-BERT is a BERT variant pre-trained on legal corpora, and the SRS names it
as a candidate backbone. It is used in this project as a **comparison model**
rather than the served model, for reasons given in Section 12.

### 4.4 Indian statutory backdrop

Four pieces of Indian law are directly encoded as rubric criteria:

| Statute | Relevance |
|---|---|
| **MSMED Act, 2006, section 15** | A buyer must pay a registered micro or small enterprise within 45 days of acceptance. A longer contractual period does not extinguish this right. |
| **MSMED Act, 2006** | Provides for compound interest on delayed payment to registered micro and small enterprises. |
| **Indian Contract Act, 1872, section 27** | Agreements in restraint of trade are void, subject to limited exceptions — making post-termination non-compete clauses of uncertain enforceability. |
| **Arbitration and Conciliation Act, 1996** | Governs India-seated arbitration, making a foreign arbitral seat materially more expensive for an Indian MSME. |

The MSMED payment rule is the most practically valuable of these: a ninety-day
payment term is common in contracts offered to small suppliers, and most such
suppliers are unaware that the statute overrides it.

---

## 5. Core Design Principle

> ### Clause-type classification is learned. Risk scoring is not.

This sentence is the architectural thesis of the project, and the codebase is
organised to preserve it.

| | Clause-type classification | Risk scoring |
|---|---|---|
| **Method** | Fine-tuned DistilBERT, 20 multi-label classes | Deterministic rule engine over a YAML rubric |
| **Question answered** | "What kind of clause is this?" | "Is this clause one-sided?" |
| **Output** | Label set with confidence scores | Risk level plus a named reason per finding |
| **Explainable?** | No — a neural network's internals are not a reason | Yes — every flag names a rule with a documented criterion |
| **Updatable without retraining?** | No | Yes — the rubric is data, not code |

### 5.1 Why risk scoring must not be a model

Three requirements in the SRS make a learned risk score unacceptable:

1. **The risk-scoring rubric must be based on identifiable, documented
   criteria** rather than an unexplained model score. A model can produce a
   number; it cannot produce a criterion.
2. **The rubric must be updatable or extensible without a full model
   retrain.** A learned risk layer could not satisfy this by construction.
3. **Any change to the rubric must be version-tracked so that historical
   reports remain explainable against the rubric version used at the time.**
   This requires the criteria to exist as an inspectable, versionable artefact.

A black-box percentage score satisfies none of these. The separation is
therefore not a stylistic preference but a requirement-driven design constraint.

### 5.2 The second half of the principle: absence detection

Most contractual risk is an **absence** rather than a presence:

- There is no cap on liability.
- There is no cure period before termination for breach.
- There is no notice window before automatic renewal.
- There is no minimum purchase commitment to balance an exclusivity obligation.

Detecting an absence requires knowing what *should* be present, which requires
knowing the clause type. Recognising that a clause contains no cure period is
only meaningful once the clause has been identified as a termination-for-cause
clause.

This is why the two layers, though decoupled, are **ordered**: classification
feeds the rubric. Each rule declares an `applies_to` list of clause types, and
is evaluated only against clauses carrying one of those types.

---

## 6. System Architecture

### 6.1 Layered view

```
┌──────────────────────────────────────────────────────────────────┐
│  PRESENTATION — React + TypeScript single-page application       │
│  Auth · Upload · Processing · Report · Dashboard                 │
└───────────────────────────┬──────────────────────────────────────┘
                            │  HTTPS · JSON · JWT bearer token
┌───────────────────────────▼──────────────────────────────────────┐
│  APPLICATION — FastAPI                                           │
│  /auth  /contracts  /contracts/{id}/status  /reports  /health    │
└───┬──────────────────────────────────────────────────────┬───────┘
    │  background task, one per upload                     │
    ▼                                                      ▼
┌─────────────────────────────────────────────┐     ┌───────────────┐
│  DOMAIN PIPELINE — five independent stages  │     │  PERSISTENCE  │
│                                             │     │  PostgreSQL 16│
│  1  extract    PyMuPDF / python-docx        │◄───►│               │
│  2  segment    rules + sentence model       │     │  users        │
│  3  classify   DistilBERT, multi-label      │     │  contracts    │
│  4  score      rubric engine ← v1.0.yaml    │     │  clauses      │
│  5  report     reportlab PDF                │     │  predictions  │
└─────────────────────────────────────────────┘     │  risk_findings│
                                                    │  clause_risk  │
                                                    │  reports      │
                                                    │  rubric_vers  │
                                                    └───────────────┘
```

### 6.2 The pipeline contract

Every stage is a **pure function** of the form `(input, config) -> output`, with
no knowledge of HTTP or the database. The orchestrator (`app/pipeline.py`) owns
all persistence and all status transitions.

This has three consequences that matter:

1. **Stages are unit-testable in isolation**, without a database or a web
   server. The segmentation test suite, for example, constructs documents
   directly and asserts on clause boundaries.
2. **Stages 3 and 4 are swappable**, satisfying the Maintainability requirement
   that the clause-type and risk-classification models be replaceable
   independently of the surrounding application logic.
3. **The ML training pipeline can import the production segmenter**, which is
   essential — see Section 11.2.

### 6.3 Processing status as a first-class concept

The `Contract.status` column is an enumeration:

```
uploaded → extracting → segmenting → classifying → scoring → complete
                                                            └→ failed
```

The SRS requires a processing screen showing "live extraction, segmentation and
machine learning computation states". This enumeration **is** that
specification, expressed in the data model. The frontend polls
`GET /api/v1/contracts/{id}/status` every 1.5 seconds and renders the stage
list. Because the stage names are user-facing, the enumeration and the UI copy
are kept deliberately aligned.

### 6.4 Concurrency control

Analysis runs as a FastAPI background task bounded by a semaphore sized from
configuration (default 5, the resolved value of TBD-4). Work arriving beyond
that capacity **queues rather than being rejected**, which is the behaviour the
performance requirement asks for.

---

## 7. Database Design

### 7.1 Entity relationships

```
users ──1:N──► contracts ──1:N──► clauses ──1:N──► clause_predictions
                   │                  │
                   │                  ├──1:N──► risk_findings
                   │                  └──1:1──► clause_risk
                   │
                   └──1:1──► reports

rubric_versions ◄── referenced by risk_findings, clause_risk, reports
```

### 7.2 Schema

| Table | Purpose | Notable columns |
|---|---|---|
| `users` | Accounts | `email` (unique, indexed), `password_hash` |
| `contracts` | Uploaded documents and analysis state | `status`, `status_detail`, `error_code`, `raw_text`, `storage_path` |
| `clauses` | Segmented provisions | `ordinal`, `heading`, `char_start`, `char_end`, `segmentation_method`, `needs_manual_review` |
| `clause_predictions` | One row per (clause, label) | `label`, `confidence`, `model_version` |
| `risk_findings` | One row per fired rule | `rule_id`, `severity`, `explanation`, `rubric_version` |
| `clause_risk` | Composed risk level per clause | `level`, `rubric_version` |
| `reports` | Generated report metadata | `summary_json`, `rubric_version`, `model_version` |
| `rubric_versions` | Rubric registry | `version`, `yaml_sha256`, `activated_at` |

### 7.3 Four design decisions and their reasons

**UUID primary keys throughout, not auto-incrementing integers.**
Sequential identifiers would allow any authenticated user to enumerate other
accounts' contract identifiers by incrementing a URL. Since the security
requirements treat uploaded contracts as commercially sensitive, and since any
authorisation slip would then expose real documents, UUIDs remove the
enumeration vector entirely. The cost — sixteen bytes per key instead of four —
is irrelevant at this system's scale.

**One prediction row per (clause, label) pair, not a label column on the
clause.**
This is what makes multi-label classification real rather than nominal: a single
clause genuinely can be both *Payment Terms* and *Late Payment, Interest and
GST*. A consequence worth noting is that **zero prediction rows is the storage
representation of "Uncategorized"** — the system does not store a sentinel
label, it stores the absence of a confident one.

**Risk stored in its own table, not as a column on `clauses`.**
This keeps the learned layer (clauses and predictions) and the rule layer
(findings and risk) independently recomputable. Re-running the rubric after an
update does not touch classification results.

**`rubric_version` denormalised onto findings, risk and reports.**
This duplication is deliberate. The auditability requirement states that a
historical report must remain explainable against the rubric version in force
when it was produced. Storing the version on each derived row is what makes that
possible after the rubric evolves.

### 7.4 Schema integrity controls

- `UNIQUE (contract_id, ordinal)` on clauses — clause order is data, not an
  accident of row insertion order.
- `CHECK (confidence >= 0 AND confidence <= 1)` on predictions.
- `CHECK (char_end >= char_start)` on clauses.
- `ON DELETE CASCADE` throughout, so deleting a contract removes every derived
  row, satisfying the data-deletion requirement.
- A SHA-256 hash of the rubric YAML recorded in `rubric_versions`, so editing a
  published rubric without incrementing its version is detectable.

---

## 8. Module-by-Module Implementation

### 8.1 Text extraction

**Location:** `backend/app/services/extraction/`

| File | Responsibility |
|---|---|
| `__init__.py` | Format detection and dispatch |
| `pdf.py` | PDF extraction via PyMuPDF |
| `docx.py` | DOCX extraction via python-docx |
| `plain.py` | Raw-text extraction, used by the ML data preparation script |
| `base.py` | Shared types and the error taxonomy |

**Format detection uses magic bytes, not the file extension.** A browser may
report `application/octet-stream` for a valid DOCX, and a user can rename an
image to `.pdf`. The declared type is therefore treated as a hint. A DOCX is
further validated by checking the ZIP container for `word/document.xml`, since
XLSX and PPTX files are also ZIP archives.

**PDF extraction uses PyMuPDF's dictionary mode rather than plain text.**
Plain `get_text()` returns a flat string, discarding the font size and weight
information that is the only available signal distinguishing a heading from body
text. That signal cannot be recovered once the page is flattened, and
segmentation depends on it. Extraction therefore captures per-line spans with
font metadata and marks headings using three heuristics: size relative to the
document's own median, bold weight, and short all-capitals lines.

**DOCX extraction walks the raw XML body rather than the convenience
collections.** python-docx exposes `.paragraphs` and `.tables` as separate
lists, which loses their relative order. Indian vendor agreements routinely
place payment schedules and service levels in tables, and dropping them — or
detaching them from the heading that introduces them — would lose precisely the
clauses the rubric most needs to inspect.

**The error taxonomy is part of the API contract.** Each failure carries a
stable machine code and a non-technical user message:

| Code | User-facing meaning |
|---|---|
| `unsupported_format` | Only PDF and Word files can be analysed |
| `no_extractable_text` | The file appears to be a scan; upload a text-based version |
| `encrypted_file` | The file is password-protected |
| `corrupt_file` | The file could not be opened |

A legacy `.doc` file receives its own specific message telling the user to save
as `.docx`, because a generic "unsupported" response would leave them guessing.

### 8.2 Clause segmentation

**Location:** `backend/app/services/segmentation/`

A three-strategy cascade, attempted in order of how much document structure each
assumes:

| Strategy | Trigger | Mechanism |
|---|---|---|
| **Numbering** | Document numbers its clauses | Regular expressions for `12.`, `1.1`, `4)`, `Article IV`, `Section 7` |
| **Heading** | No numbering, but headings identified during extraction | Each heading opens a new clause |
| **Paragraph** | No structure at all | One clause per paragraph; over-long runs divided at sentence boundaries |

A strategy is considered to have failed if it produces fewer than three clauses,
and the cascade moves on.

**The central judgement: top-level numbering and headings open a new clause;
lettered and roman sub-items do not.** Consider a typical indemnity provision:

```
12. Indemnity
    (a) The Supplier shall indemnify the Customer against all claims.
    (b) The Customer shall promptly notify the Supplier of any claim.
```

Treating `(a)` and `(b)` as separate clauses would fragment one provision into
pieces that individually lose their meaning. Worse, it would defeat the rubric's
asymmetry detection, which needs both halves of a potentially reciprocal
obligation present in the same clause to distinguish a one-sided indemnity from
a mutual one.

**Sentence boundaries use pysbd rather than splitting on full stops.** Contract
text is dense with abbreviations — "No.", "Ltd.", "Rs. 50,000", "Cl. 4.2" — each
of which a naive period-split would treat as a sentence end, fragmenting clauses
mid-phrase.

**Ambiguous segments are flagged, not silently corrected.** A clause exceeding
2,500 characters or falling below 40 is marked `needs_manual_review` with a
recorded reason. Under the numbering strategy an over-long clause is **flagged
but not split**, because the document's own numbering stated where the clause
ends and cutting a provision in half would contradict that. Under the paragraph
fallback, where no such statement exists, long runs *are* divided — at sentence
boundaries, the only defensible place.

**Document furniture is filtered**: page numbers, tables of contents, signature
blocks and lines containing no alphabetic characters.

### 8.3 Clause-type classification

**Location:** `backend/app/services/classification/`

| File | Responsibility |
|---|---|
| `labels.py` | The 20-class taxonomy — single source of truth for label keys |
| `model.py` | The `Classifier` protocol and two implementations |

Two implementations sit behind one interface:

- **`TransformerClassifier`** — loads a fine-tuned checkpoint, applies per-class
  thresholds, handles long clauses by sliding window with max-pooling.
- **`BaselineClassifier`** — scores keyword cues declared alongside each class.

`get_classifier()` selects the transformer when a checkpoint is present and
loadable, and the baseline otherwise.

**Why a baseline exists.** The classifier is the long-lead item: it requires the
CUAD download, the span-to-clause conversion, a manual audit of that conversion,
and GPU time. Meanwhile every other component depends on *something* producing
clause types — the rubric cannot evaluate a clause without knowing its type, so
the rubric, the report, the PDF export and the entire frontend would be
unbuildable and untestable until training finished.

The baseline made the full pipeline runnable from the outset. In practice this
proved decisive: **four rubric defects were found by running the complete
pipeline against a realistic contract**, and would not have surfaced against
hand-constructed label sets (see Section 17).

**Guarding against mistaking the baseline for a trained model.** This is the
obvious hazard, and it is addressed structurally rather than by documentation:

- The baseline's `model_version` is the string `baseline-keyword-v1`. That value
  is stored on **every prediction row**, stamped on **every report**, printed in
  the **PDF provenance footer**, and returned by the **health endpoint**. There
  is no path by which a baseline-produced report resembles a trained one.
- Baseline confidence is **capped at 0.80**. Keyword matching is uncalibrated,
  and permitting it to report 0.95 would assert a certainty the safety
  requirements forbid.
- The latency measurement script prints an explicit warning when the model
  version begins with `baseline-`.

**Dependency isolation.** PyTorch and Transformers add approximately 2.5 GB to
the container image and are needed only once a checkpoint exists. They are
therefore declared in `ml/requirements.txt`, not `backend/requirements.txt`,
keeping the application image small. Their absence degrades to the baseline
rather than failing.

### 8.4 Risk scoring

**Location:** `backend/app/services/risk/`

| File | Responsibility |
|---|---|
| `rubrics/v1.0.yaml` | The rules — 21 clause rules, 4 contract-level rules |
| `loader.py` | Parsing, strict validation, hashing, caching |
| `engine.py` | Rule evaluation and risk composition |
| `detectors/` | The eleven detector primitives |

Detailed in Section 10.

### 8.5 Report generation

**Location:** `backend/app/services/reporting/pdf_renderer.py`

The PDF deliberately mirrors the web report rather than being a terse export,
because the intended reader is a business owner likely to print it and take it
into a negotiation. Explanations therefore travel with the clauses.

Implementation notes:

- The **disclaimer is drawn in the running page footer** by the document
  template, not placed once in the flow. The requirement is that it be
  *persistent*, and a single page of front matter would not survive someone
  printing page four.
- **Contract text is HTML-escaped** before reaching a paragraph object.
  reportlab parses a mini-HTML dialect, and contracts contain `&` and
  occasionally `<` (as in "< 30 days"), either of which would raise a parse
  error mid-render.
- Each clause is wrapped in a `KeepTogether` block so a clause is never split
  from its own explanation across a page break.
- The risk palette is **darkened relative to the screen colours** so text
  remains legible in greyscale print.

### 8.6 Authentication and authorisation

**Location:** `backend/app/core/security.py`, `backend/app/api/deps.py`

- Passwords hashed with **bcrypt** at the library default cost. A deliberately
  slow hash is chosen over a fast one because a fast hash is trivially
  brute-forced from a stolen table.
- Passwords **longer than 72 bytes are rejected**, because bcrypt silently
  truncates beyond that and accepting more would imply strength the system does
  not actually provide.
- **JWT** access tokens, HS256, with `exp`, `sub` and `iss` all required at
  decode time.
- **Login timing is equalised**: when no account matches the submitted address,
  the password is still verified against a fixed dummy hash, so a missing
  account and a wrong password take comparable time. Returning early would allow
  an attacker to enumerate registered email addresses by timing.
- **Authentication is not authorisation.** Every contract query filters on
  `user_id` in addition to the contract identifier. The identifier is already
  unguessable, but the requirement is that content be restricted to its owner,
  and that must be enforced in the query rather than left to the difficulty of
  guessing a UUID.
- Cross-account access returns **404, not 403**, because confirming that another
  user's contract exists is itself an information leak.

---

## 9. The Clause-Type Taxonomy

Twenty classes, collapsed from CUAD's 41 and extended for Indian commercial
norms. Twenty sits within the 15–20 range the SRS permits.

| # | Class key | Display name | Origin |
|---|---|---|---|
| 1 | `parties_definitions` | Parties & Definitions | CUAD: Parties, Document Name |
| 2 | `term_effective_date` | Term & Effective Date | CUAD: Agreement/Effective/Expiration Date |
| 3 | `renewal_auto_renewal` | Renewal & Auto-Renewal | CUAD: Renewal Term, Notice Period |
| 4 | `termination_convenience` | Termination for Convenience | CUAD: Termination For Convenience |
| 5 | `termination_cause_cure` | Termination for Cause & Cure | **Indian corpus — thin in CUAD** |
| 6 | `payment_terms` | Payment Terms & Pricing | CUAD: Price Restrictions, Minimum Commitment |
| 7 | `late_payment_interest_gst` | Late Payment, Interest & GST | **Indian addition — absent from CUAD** |
| 8 | `indemnity` | Indemnity | **Indian corpus — thin in CUAD** |
| 9 | `limitation_of_liability` | Limitation of Liability | CUAD: Cap On Liability, Uncapped Liability |
| 10 | `warranties` | Warranties & Representations | CUAD: Warranty Duration |
| 11 | `confidentiality` | Confidentiality | **Indian corpus — thin in CUAD** |
| 12 | `ip_ownership_licence` | IP Ownership & Licence | CUAD: IP Ownership Assignment, License Grant |
| 13 | `exclusivity_noncompete` | Exclusivity & Non-Compete | CUAD: Exclusivity, Non-Compete, No-Solicit |
| 14 | `assignment_control` | Assignment & Change of Control | CUAD: Anti-Assignment, Change Of Control |
| 15 | `governing_law` | Governing Law & Jurisdiction | CUAD: Governing Law |
| 16 | `dispute_arbitration` | Dispute Resolution & Arbitration | **Indian addition — absent from CUAD** |
| 17 | `force_majeure` | Force Majeure | **Indian corpus — thin in CUAD** |
| 18 | `audit_compliance` | Audit, Inspection & Compliance | CUAD: Audit Rights |
| 19 | `insurance` | Insurance | CUAD: Insurance |
| 20 | `notices_misc` | Notices & Miscellaneous | CUAD: Notice |

### 9.1 The six classes CUAD cannot teach

Classes 5, 7, 8, 11, 16 and 17 are thin or entirely absent in CUAD — and they
are among the **most MSME-relevant categories in the taxonomy**. Cure periods,
GST and late-payment interest, confidentiality, arbitration seat and force
majeure are exactly the provisions a small Indian supplier most needs examined.

This is reported rather than concealed, for two reasons:

1. It is the honest explanation of why the Indian domain-adaptation corpus is a
   **hard dependency** rather than an optional enhancement.
2. Reporting per-class F1 scores makes the weakness visible in the results,
   rather than averaging it away into an aggregate figure.

### 9.2 Mapping provenance

`ml/configs/label_mapping.yaml` records the complete mapping from CUAD's 41
categories to these 20 classes. Every CUAD category appears exactly once —
either mapped to a class, or listed under `dropped` with a stated reason. A
category present in neither list causes the preparation script to fail, so the
mapping cannot silently lose a label. This satisfies the SRS data requirement
that label mapping be documented for reproducibility.

---

## 10. The Risk Rubric

### 10.1 Rule structure

Each rule is data, expressed in YAML:

```yaml
- id: payment_term_over_45_days
  applies_to: [payment_terms, late_payment_interest_gst]
  severity: caution
  criterion: >
    MSMED Act, 2006, section 15 — a buyer must pay a registered micro or
    small enterprise within 45 days of acceptance of goods or services.
  detect:
    numeric_days_gt: 45
  explanation: >
    Payment here is due more than 45 days after invoice. If your business is
    a registered micro or small enterprise under the MSMED Act, 2006, you are
    entitled to be paid within 45 days, and a longer period written into a
    contract does not remove that right. You can raise a delayed-payment
    claim through the MSME Samadhaan process.
```

| Field | Purpose |
|---|---|
| `id` | Stable identifier, stored on every finding — the audit trail |
| `applies_to` | Clause types this rule is evaluated against |
| `severity` | `high` or `caution`; rules never fire "safe" |
| `criterion` | The documented basis, including statutory citation where applicable |
| `detect` | Composition of detector primitives; **all** must be satisfied |
| `explanation` | The plain-language text shown to the user |

### 10.2 Detector primitives

Eleven composable predicates, each independently unit-tested. No rule contains
logic of its own, which is what allows the rubric to be edited without touching
Python.

| Primitive | Tests whether |
|---|---|
| `present_any` | Any listed phrase appears |
| `present_all` | Every listed phrase appears |
| `absent_any` | None of the listed phrases appear |
| `present_pattern` / `absent_pattern` | A regular expression matches or does not |
| `numeric_days_gt` / `numeric_days_lt` | A stated period exceeds or falls below a threshold |
| `has_no_period` | No time period is stated at all |
| `notice_period_absent` | No **notice** period is stated |
| `notice_period_gt` | The stated notice period exceeds a threshold |
| `one_sided_obligation` | Every *duty* falls on one party |
| `one_sided_right` | Every discretionary *right* belongs to one party |
| `foreign_jurisdiction` | A non-Indian forum is named and no Indian one |
| `unbounded_duration` | The obligation is perpetual or indefinite |

**Period extraction is harder than it appears.** Contracts express durations in
at least four forms, none interchangeable under a single regular expression:

| Form | Example |
|---|---|
| Digits before the unit | `within 45 days` |
| Word, then digits in brackets | `within ninety (90) days` |
| Words only | `a period of twenty-four months` |
| Invoicing shorthand, no unit word | `Net 30` |

The implementation therefore locates the **unit word** and searches backwards a
short window for a figure, in digits or in words, rather than attempting one
pattern per form. Four-digit values are excluded as statutory year citations
("the Indian Contract Act, 1872").

**Asymmetry detection is the most interesting primitive.** Party roles are
resolved from role vocabulary (supplier, vendor, service provider, contractor
versus customer, client, purchaser, buyer). For each obligation or permission
verb, a short window is examined backwards for a role word, recording which side
bears the duty or holds the right. If duties or rights appear and all land on
one side, the clause is one-directional. Explicitly mutual language — "each
party", "both parties", "either party" — suppresses the flag.

Two primitives exist rather than one because **the grammar differs**: a duty
reads "the Supplier **shall** indemnify", while a right reads "the Customer
**may** terminate". A termination-for-convenience clause is one-sided by virtue
of who *may* act, so matching only obligation verbs would miss it entirely.

### 10.3 The rule set

**High severity (8 rules):** uncapped liability · one-sided indemnity ·
unilateral termination for convenience · termination without a notice period ·
auto-renewal without a notice window · unilateral price variation · broad IP
assignment · exclusivity without commitment

**Caution (13 rules):** indemnity covering indirect losses · no cure period ·
long renewal opt-out window · payment term over 45 days · no late-payment
interest · perpetual confidentiality · post-term non-compete · one-sided
assignment restriction · foreign governing law · foreign arbitration seat · no
dispute-resolution mechanism · unlimited audit rights · one-way liquidated
damages

**Contract-level (4 rules):** no force majeure clause · no limitation of
liability clause · no confidentiality clause · no payment terms clause

Contract-level rules detect an entire clause type being absent from the whole
document. Having no clause to attach to, they are reported in the report summary
rather than against an individual clause, and are stored in `Report.summary_json`.

### 10.4 Risk composition

| Outcome | Condition |
|---|---|
| **High-Risk** | At least one `high` severity rule fired |
| **Caution** | At least one `caution` rule fired, and no `high` rule |
| **Safe** | The clause was classified, and no rule fired |
| **Not assessed** | The clause type could not be identified, or the rule layer errored |

"Not assessed" is load-bearing. Reporting an unjudged clause as safe would be a
false reassurance, which the safety requirements treat as a substantive hazard.

### 10.5 Graceful degradation

Rule evaluation is wrapped per-rule. A detector raising an exception causes that
single rule not to fire, logged with its rule identifier; it does not fail the
clause, and it certainly does not fail the report. A clause whose assessment
cannot complete is marked "not assessed" and still displayed with its clause
text and predicted type. This implements the Reliability requirement directly.

### 10.6 Auditability

- The rubric YAML is **SHA-256 hashed** and the hash recorded in
  `rubric_versions` on first use.
- If a published rubric is edited without its version being incremented, the
  hash mismatch is detected and logged as an error. The original hash is not
  overwritten, because that is the hash historical reports were produced under.
- `docs/RUBRIC.md` is **generated from the YAML** by
  `backend/scripts/generate_rubric_docs.py`, and continuous integration fails if
  the generated file is stale. The documentation therefore cannot drift from the
  rules that actually execute.

---

## 11. Machine Learning Pipeline

**Location:** `ml/`

| Script | Purpose |
|---|---|
| `scripts/prepare_cuad.py` | Convert CUAD span annotations into a multi-label clause dataset |
| `scripts/train.py` | Fine-tune, fit per-class thresholds, write a servable checkpoint |
| `scripts/evaluate.py` | Report metrics on CUAD test and the Indian evaluation set |
| `configs/distilbert.yaml` | Served model configuration |
| `configs/legalbert.yaml` | Comparison model configuration |
| `configs/label_mapping.yaml` | CUAD category to class mapping, with justified exclusions |
| `eval/indian_eval_set.jsonl` | Hand-labelled Indian clauses |
| `MODEL_CARD.md` | Provenance, metrics, limitations |

### 11.1 Converting CUAD

Because CUAD is a span-extraction dataset, conversion is a defined procedure:

1. **Parse annotated spans per contract**, each carrying its CUAD category.
2. **Segment each contract using the production segmenter.**
3. **Assign label *L* to a clause** when an *L*-span overlaps it past an
   intersection-over-union threshold (default 0.5), **or** when at least 90% of
   the span lies inside the clause. The second condition matters because CUAD
   spans are often much shorter than the clause containing them: a
   one-sentence highlight inside a 900-character indemnity clause has a low IoU
   but is fully contained, and that clause unambiguously *is* an indemnity
   clause.
4. **Unlabelled clauses become negatives**, after removing boilerplate
   (signature blocks, schedules, tables of contents) which would otherwise
   dominate the negative class.
5. **Split by contract, never by clause.**

### 11.2 Two traps this procedure avoids

**Train/serve skew.** Step 2 imports
`backend/app/services/segmentation/` directly rather than reimplementing
segmentation for training. A separate training-time segmenter is the classic
form of this bug: the model learns on text shaped one way, is served text shaped
another, and accuracy degrades with nothing in the loss curve to indicate why. A
test asserts that the same contract in PDF and DOCX form segments into identical
clauses, guarding the same invariant from the other direction.

**Split leakage.** Step 5 splits on contracts because clauses within a single
contract share drafting style, defined terms and party names. A clause-level
split would leak all of that across the train/test boundary and inflate every
reported figure.

### 11.3 The audit gate

`prepare_cuad.py --audit 50` writes a sample of converted clauses with their
assigned labels to a plain-text file for manual inspection.

**This is a gate, not a formality.** If the span-to-clause mapping is noisy,
every downstream metric is meaningless — and critically, the loss curve will
look perfectly healthy regardless. The procedure is therefore: convert, audit 50
clauses by hand, adjust the thresholds, re-convert, and only then train.

The conversion logic has been **verified against a synthetic CUAD-shaped
dataset** of six contracts with known annotations: 24 of 24 clauses received the
expected label, and the split was correctly performed by contract.

### 11.4 Training configuration

| Parameter | Value | Reason |
|---|---|---|
| Architecture | `DistilBertForSequenceClassification` | Speed on CPU |
| Problem type | `multi_label_classification`, 20 sigmoid heads | Multi-label requirement |
| Loss | `BCEWithLogitsLoss` with capped positive class weights | Support ranges from thousands (Governing Law) to a handful (Joint IP); unweighted BCE would predict the majority negative for every rare class |
| Max sequence length | 256 tokens, sliding window with max-pooling across windows | Contract clauses routinely exceed the input limit; truncating would discard the back half of exactly the long, dense provisions carrying the most risk |
| Epochs | 3 | Sufficient on a free Colab T4 |
| Thresholds | Fitted **per class** on validation for best F1 | A single global threshold sacrifices recall on rare classes — which are the Indian-relevant ones |

### 11.5 Evaluation methodology

**Metrics reported: macro-F1 and per-class precision, recall and F1. Accuracy
is deliberately not reported**, because on a 20-label imbalanced multi-label
task it is dominated by true negatives and would substantially overstate
performance.

**Two evaluation sets, reported separately:**

1. **CUAD held-out test split** — performance on US M&A contracts.
2. **Indian evaluation set** — performance on the domain the product serves.

**The gap between them is the finding.** A single number from the easier
distribution would misrepresent what the system does for an Indian MSME. The
evaluation script computes and prints this gap explicitly.

### 11.6 Serving a trained model

```
CLAUSEGUARD_MODEL_DIR=/path/to/ml/artifacts/distilbert
```

No code change and no migration. Label order is read from the checkpoint's
`id2label` mapping rather than assumed to match the taxonomy positionally: if
the taxonomy is ever reordered, a positional mapping would silently relabel
every prediction, whereas reading from the checkpoint raises a loud error.

---

## 12. Technology Stack and Justification

| Layer | Technology | Justification |
|---|---|---|
| Backend framework | FastAPI, Python 3.12 | Mandated by the design constraints |
| Database | PostgreSQL 16 | Requirement states 14+; the schema needs UUID, JSONB and native enumerated types |
| ORM and migrations | SQLAlchemy 2, Alembic | Schema held in version control rather than applied ad hoc |
| PDF parsing | PyMuPDF | Exposes font metadata required for heading detection |
| DOCX parsing | python-docx | Paragraph styles and table access |
| Sentence segmentation | pysbd | Handles legal abbreviations correctly |
| ML framework | PyTorch, Hugging Face Transformers | Mandated by the design constraints |
| Model backbone | DistilBERT (served), Legal-BERT (compared) | See 12.2 |
| Rubric format | PyYAML | Rules as editable data rather than code |
| PDF generation | reportlab | See 12.1 |
| Authentication | passlib/bcrypt, PyJWT | Industry-standard practice as required |
| Frontend | React, TypeScript, Vite, Tailwind CSS | React mandated by the design constraints |
| Web server | nginx | Single origin in production, eliminating CORS |
| Containerisation | Docker Compose | Portability requirement |

### 12.1 Deviation: reportlab instead of WeasyPrint

The build plan named WeasyPrint, which renders HTML and CSS and could in
principle have reused the web report's markup.

WeasyPrint depends on GTK, Pango and Cairo as **system** libraries. On Windows
these are not installable via pip; they require a separate runtime
installation, and the failure occurs at import time rather than install time.

The consequence would have been specific and damaging: PDF export would work
inside the Linux container and fail on the development machine, so the automated
test covering the export requirement could not run locally. **A requirement
whose tests only execute in continuous integration is a requirement that gets
broken quietly.**

reportlab is pure Python and behaves identically on Windows and in the
container. The cost is that the export layout is written in Python rather than
CSS, so the web report and the PDF are deliberately similar but separately
maintained, with their colour palettes cross-referenced in comments.

Alternatives weighed: xhtml2pdf (rejected — its CSS subset excludes flexbox and
grid, so the web template could not be reused unmodified, removing the main
reason to prefer an HTML renderer) and headless Chromium (rejected as
disproportionate — a browser in the API image for one feature).

### 12.2 Deviation: DistilBERT served rather than Legal-BERT

The design constraints permit either Legal-BERT or DistilBERT. Legal-BERT,
pre-trained on legal text, would be expected to perform better.

However, the operating environment mandates **CPU-based inference**, and the
resolved latency budget is 30 seconds for a 50-clause contract. DistilBERT has
six transformer layers against Legal-BERT's twelve and is approximately twice as
fast at inference.

DistilBERT is therefore served, and **Legal-BERT is trained on identical data
and splits as a reported comparison**. This converts the choice from an
assertion into a measurement: the results table shows both the accuracy
difference and the latency difference, and the serving decision follows from
them.

---

## 13. Deployment and How to Run the System

### 13.1 Prerequisites

| Requirement | Needed for |
|---|---|
| **Docker Desktop**, running | The application itself — this is the only hard requirement |
| Python 3.12 | Running the backend test suite outside Docker |
| Node.js 22 | Running the frontend development server outside Docker |

### 13.2 Starting the application

```bash
cd ClauseGuard
docker compose up -d --build
```

Three containers start:

| Service | Contents | Host port |
|---|---|---|
| `db` | PostgreSQL 16 | 5433 |
| `api` | FastAPI backend | 8000 |
| `web` | nginx serving the built React application | 5173 |

Database migrations run automatically on container start.

| Endpoint | URL |
|---|---|
| **Application** | http://localhost:5173 |
| Interactive API documentation | http://localhost:8000/docs |
| Health check | http://localhost:8000/api/v1/health |

**Note on the database port.** PostgreSQL is published on host port **5433**,
not the conventional 5432. Another project on the development machine already
held 5432, and a port clash prevents the entire stack from starting. Inside the
Docker network the API still reaches the database on the standard 5432.

### 13.3 Using the application

1. Open http://localhost:5173
2. Create an account (email, password of at least 8 characters)
3. Upload a contract — drag and drop, or use the file picker
4. Watch the processing stages advance
5. Read the colour-coded report; click a summary tile to filter to that risk level
6. Download the PDF

### 13.4 Generating a sample contract

A synthetic Indian supply agreement, seeded with fifteen specific risks:

```bash
cd backend
python -c "
import sys; sys.path.insert(0, '.')
from tests.fixtures import make_pdf
open('sample-contract.pdf','wb').write(make_pdf())
"
```

### 13.5 Running the tests

```bash
docker compose up -d db

cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt

REQUIRE_DB=1 .venv/Scripts/python -m pytest -v
.venv/Scripts/python -m ruff check .
```

Database-dependent tests **skip** when no server is reachable, so `pytest` still
passes on a fresh checkout. Setting `REQUIRE_DB=1` converts that skip into a
failure; continuous integration sets it, so a green build cannot be achieved by
quietly skipping the tests that matter most.

### 13.6 Frontend development

```bash
cd frontend
npm install
npm run build      # runs `tsc -b` first, so type errors fail the build
npm run dev        # development server on :5173, proxying /api to :8000
```

### 13.7 Supporting scripts

```bash
# Regenerate docs/RUBRIC.md after editing the rubric
python backend/scripts/generate_rubric_docs.py

# Measure pipeline latency against the 30-second budget
python backend/scripts/measure_latency.py --clauses 50 --runs 5
```

### 13.8 Shutting down

```bash
docker compose down        # stop; database contents preserved
docker compose down -v     # stop and delete all data
```

---

## 14. Functional Capabilities

| Capability | Requirement |
|---|---|
| Register and log in securely | REQ-6.1 |
| Upload PDF or DOCX up to 10 MB | REQ-1.1, REQ-1.2 |
| Reject non-text files with actionable guidance | REQ-1.4 |
| Store the original file and extracted text per account | REQ-1.5 |
| Segment into clauses, preserving order and source position | REQ-2.1, REQ-2.2 |
| Fall back gracefully on unstructured documents | REQ-2.3 |
| Flag clauses that could not be cleanly separated | REQ-2.4 |
| Classify clauses into 20 types, multi-label, with confidence | REQ-3.1 – REQ-3.3 |
| Report "Uncategorized" rather than guessing | REQ-3.4 |
| Assign Safe / Caution / High-Risk per clause | REQ-4.1 |
| Trace every flag to a named, documented rule | REQ-4.2 |
| Explain every flag in plain language | REQ-4.3 |
| Update the rubric and re-analyse without retraining or re-upload | REQ-4.4 |
| Display a colour-coded report with expandable explanations | REQ-5.1, REQ-5.2 |
| Show summary counts at the top of the report | REQ-5.4 |
| Export a print-ready PDF | REQ-5.3 |
| List contract history with risk summaries | REQ-6.3 |
| Re-open past reports without re-uploading | REQ-6.4 |
| Delete a contract and all derived data | Security requirements |
| Detect protections missing from the contract entirely | REQ-4.2 extension |

---

## 15. Testing and Verification

### 15.1 Test suite composition

**119 automated tests**, organised by module:

| File | Coverage |
|---|---|
| `test_extraction.py` | Format detection, text extraction, offset integrity, heading identification, scanned-file rejection, table inclusion |
| `test_segmentation.py` | Numbering rules, strategy cascade, sub-item grouping, determinism, review flagging, cross-format equivalence |
| `test_rubric.py` | Rubric integrity, detector primitives, risk composition, graceful degradation, end-to-end rule firing |
| `test_api.py` | Authentication, upload validation, report content, PDF export, dashboard, cross-account isolation |
| `test_config.py` | Settings parsing, upload limits |
| `test_migrations.py` | Migration/model drift, downgrade reversibility |
| `test_health.py` | Service health, dependency failure handling |

### 15.2 Notable test strategies

**Fixtures are generated, not committed as binaries.** `tests/fixtures.py`
constructs a complete synthetic Indian supply agreement in memory and renders it
as a real PDF and a real DOCX. The clause text a test asserts on is therefore
visible in the source file rather than hidden inside a checked-in blob. The
fixture is deliberately seeded with fifteen specific risks, and
`EXPECTED_RISKS` records which rule should fire on which clause.

**Migration drift is tested directly.** `test_migrations.py` creates a throwaway
database, runs the full migration chain into it, and compares the result against
the ORM metadata table by table and column by column. This catches a specific
quiet failure: adding a column to the models, forgetting the migration, and not
noticing because the development database was created from metadata rather than
from migrations. Deployment would then fail on a column that does not exist.

**Documentation currency is tested.** Continuous integration runs the rubric
documentation generator with `--check`, failing the build if `docs/RUBRIC.md`
does not match the rubric YAML.

**Jargon is tested.** `test_explanations_avoid_legal_jargon` asserts that no
rule explanation contains Latin legal phrases, enforcing the Usability
requirement mechanically rather than by review.

**Cross-format equivalence is tested.** The same contract as PDF and as DOCX
must segment into identical clauses — the invariant that protects against
format-dependent behaviour reaching the model.

### 15.3 Continuous integration

Three parallel jobs:

1. **backend** — lint, migration application, 119 tests against a real
   PostgreSQL service container, rubric documentation currency check, latency
   measurement recorded to the build log.
2. **frontend** — TypeScript type-check and production build.
3. **stack** — builds all three containers, then drives the complete analysis
   path through nginx: register, upload, poll, fetch the report, assert every
   flagged clause carries an explanation, download the PDF and verify its magic
   bytes.

---

## 16. Results and Measurements

### 16.1 Latency against the budget

Measured with `backend/scripts/measure_latency.py`, 51 clauses, 5 runs:

| Stage | Median | Maximum |
|---|---|---|
| Extraction | 0.006 s | 0.152 s |
| Segmentation | 0.000 s | 0.000 s |
| Classification (baseline) | 0.018 s | 0.018 s |
| Risk scoring | 0.003 s | 0.031 s |
| **Total** | **0.027 s** | **0.200 s** |

**Budget: 30 seconds. Worst observed with the keyword baseline: 0.2 seconds.**

Re-measured with the **trained DistilBERT** in place:

| Stage | Median | Maximum |
|---|---|---|
| Extraction | 0.006 s | 0.126 s |
| Segmentation | <0.001 s | <0.001 s |
| **Classification (DistilBERT, CPU)** | **2.627 s** | **2.636 s** |
| Risk scoring | 0.002 s | 0.014 s |
| **Total** | **2.636 s** | **2.777 s** |

Classification rose from 0.018 s to 2.627 s — a 146× increase — and the full
pipeline still completes in 2.8 seconds against a 30-second budget, better than
10× headroom. **SRS §5.1 is now verified by measurement rather than
estimated.**

### 16.2 Rubric behaviour on the fixture contract

Against the synthetic agreement (16 segments including the title block):

| Risk level | Clauses |
|---|---|
| High-Risk | 7 |
| Caution | 5 |
| Safe | 3 |
| Not assessed | 1 |

**All fifteen expected rules fired, with no false positives.** Contract-level
analysis correctly identified the absence of a force majeure clause.

Sample findings:

| Clause | Rules fired |
|---|---|
| 3. Renewal | `auto_renew_without_notice_window` |
| 4. Payment Terms | `payment_term_over_45_days`, `no_late_payment_interest`, `unilateral_price_variation` |
| 5. Indemnity | `uncapped_liability`, `one_sided_indemnity`, `indemnity_covers_indirect_losses` |
| 7. Termination for Convenience | `unilateral_termination_for_convenience`, `termination_without_notice_period` |
| 14. Governing Law | `foreign_governing_law` |

### 16.3 Concurrency under load (TBD-4)

Measured with `backend/scripts/load_test.py` against the running TLS stack, at
**twice** the stated capacity:

| Measure | Result |
|---|---|
| Simultaneous uploads | 10 (TBD-4 capacity is 5) |
| Accepted (HTTP 202) | 10 / 10 — **nothing rejected** |
| Reached `complete` | 10 / 10 |
| Distinct clause counts across the 10 | 1 (all 16) |
| Distinct risk tallies across the 10 | 1 |
| Matches a sequential single analysis | Yes |
| Wall clock, 10 concurrent | 0.76 s |
| Wall clock, 10 sequential (extrapolated) | 6.40 s |
| Effective speedup | **8.46×** |

The third and fourth rows are the important ones. Identical clause counts and
identical risk tallies across ten simultaneous analyses is evidence that the
pipeline holds no shared mutable state — a defect that would be invisible in
single-request testing and would corrupt results only under load.

### 16.4 Transport security (§5.3)

Verified against the running stack with a self-signed certificate:

| Check | Result |
|---|---|
| Protocol negotiated | **TLS 1.3** |
| Cipher suite | `TLS_AES_256_GCM_SHA384` |
| `http://` → `https://` | 301 redirect; no application traffic served on port 80 |
| `Strict-Transport-Security` | `max-age=63072000` |
| `Content-Security-Policy` | `default-src 'self'`; no third-party origins |
| `X-Frame-Options` | `DENY` |
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| API over HTTPS | `/api/v1/health` returns `"database": true` |

Production certificate procedure (Let's Encrypt with automated renewal, or TLS
terminated upstream) is documented in `docs/DEPLOYMENT.md`. No certificate or
private key is committed, and `.gitignore` excludes `certs/`, `*.pem` and
`*.key`.

### 16.5 CUAD conversion and the audit gate

The real dataset was downloaded and converted:

| Measure | Result |
|---|---|
| Contracts in CUAD | 510 |
| Contracts contributing clauses | **490** |
| Clauses after conversion | **20,062** |
| Split (by contract) | 343 / 73 / 74 contracts → 12,817 / 2,368 / 4,877 clauses |
| Labelled (positive) clauses | 1,935 / 370 / 628 |
| Label assignment rule | IoU ≥ 0.5, **or** ≥0.9 span containment with the span ≥15% of the clause |
| Classes with zero CUAD support | **6 of 20** — the Indian-relevant ones |
| **Label noise on positives, measured** | **~23%** after correction (was ~40%) |

The positive rate is low — 1,935 labelled of 12,817 training clauses, about 15%.
That is inherent to the conversion rather than a defect: CUAD annotates only the
41 categories it defines, so every clause that is not one of those (and a
commercial contract is mostly such clauses) is a legitimate negative. It does
mean the negative class dominates, which is why training uses capped per-class
positive weighting rather than unweighted binary cross-entropy.

The audit gate was run three times and found a defect each round. The full
record is in `ml/MODEL_CARD.md`; Section 17.4 of this report summarises what it
found and why it matters.

### 16.6 Verified system properties

| Property | Evidence |
|---|---|
| Full stack operates through nginx | Register, upload, poll, report and PDF export all verified against the containerised stack |
| Cross-format consistency | PDF and DOCX of the same contract produce identical clauses |
| Cross-account isolation | Requests for another account's contract return 404 |
| Cascade deletion | Deleting a contract removes clauses, predictions, findings, risk and report |
| Oversize rejection | An 11 MB upload is rejected with HTTP 413 and a message naming the limit |
| Scanned-file handling | An image-only PDF is accepted, then reported as failed with non-technical guidance |
| Explanation completeness | Every finding in every generated report carries non-empty explanation text |
| Dependency failure handling | The health endpoint returns 503, not 500, when the database is unreachable |

### 16.7 Build quality

| Check | Result |
|---|---|
| Backend tests | 119 passed |
| Backend lint (ruff) | Clean |
| Frontend type-check and build | Clean under TypeScript strict mode |
| Frontend bundle size | 186 kB JavaScript, 60 kB gzipped |
| Rubric documentation currency | Current |

### 16.8 Classification accuracy

The classifier was trained: DistilBERT, 2 epochs, 1,602 steps, 1 h 52 m on CPU,
final training loss 0.210.

| Evaluation set | Macro-F1 (all 20) | Macro-F1 (supported) | Micro-F1 | n |
|---|---|---|---|---|
| CUAD held-out test | 0.3678 | **0.5658** (13 classes) | 0.5639 | 4,877 |
| Indian evaluation set | **0.3022** | 0.3022 (20 classes) | 0.2718 | 180 |

**Read the supported-class column for CUAD.** Seven of the twenty classes have
zero examples in the CUAD test split, so each scores F1 0.000 and is still
counted in the 20-class macro average, dragging it from 0.566 to 0.368. The
0.566 figure agrees closely with micro-F1 0.564, which is the cross-check that
it is the right number to quote.

Strongest on CUAD: `governing_law` 0.870, `insurance` 0.806,
`limitation_of_liability` 0.748, `audit_compliance` 0.740,
`renewal_auto_renewal` 0.739. Weakest with support:
`termination_convenience` 0.210, `warranties` 0.222.

**Accuracy is not reported**, for the reason given in Section 11.5: on a
20-label imbalanced multi-label task it is dominated by true negatives.

### 16.9 The domain gap - the central empirical result

| Comparison | CUAD | Indian | Gap |
|---|---|---|---|
| Macro-F1, like-for-like (supported classes) | 0.5658 | 0.3022 | **+0.2636** |
| Micro-F1 | 0.5639 | 0.2718 | **+0.2921** |

**Performance roughly halves** moving from US M&A contracts to Indian MSME
contracts. This was the predicted outcome, and measuring it is why a separate
Indian evaluation set was built rather than reporting a single CUAD number.

The per-class detail is sharper than the headline. On the Indian set mean
precision is 0.454 against mean recall **0.248** - the model is severely
conservative. Several classes reach precision 1.000, so when it fires it is
usually right, but `payment_terms` has recall 0.069: it misses 27 of 29 payment
clauses.

The six classes CUAD cannot teach score **exactly 0.000 despite having 10-14
Indian examples each**. A model cannot predict a class it has never been shown.
The taxonomy in Section 9 predicted precisely which six those would be, before
any training took place.

### 16.10 The trained model underperforms the baseline, and is not served

This is the most consequential finding of the implementation, and it is
reported rather than concealed.

Both classifiers were run over the same 16-clause Indian supply agreement,
through the real pipeline:

| Classifier | Clauses typed | Risk findings | Unassessable | False "missing clause" warnings |
|---|---|---|---|---|
| **Keyword baseline** | **15 / 16** | **18** | **1** | 1 |
| Trained DistilBERT | 7 / 16 | 9 | 9 | 3 |

The trained model types fewer than half the clauses, raises half the findings,
and produces two false warnings that the contract contains no payment-terms and
no confidentiality clause - because it did not recognise clauses plainly
present.

**It is not a threshold-calibration problem.** Flattening the CUAD-fitted
thresholds to 0.45, 0.30 and even 0.20 recovers nothing (7/16 in every case), so
the model has no signal for those clauses at all, rather than signal sitting
just below a badly-placed cut-off.

**The cause is structural**: seven of twenty classes had zero CUAD training
support, and two classes that did have support (371 and 225 examples) still
failed to fire on Indian phrasing. The keyword baseline has neither problem,
because its cues were written for all twenty classes in Indian contractual
language.

**Consequence for the system**: the keyword baseline remains the served
classifier. Nothing in the deployment sets `CLAUSEGUARD_MODEL_DIR`, so the
default is unchanged and the product continues to work. `ml/MODEL_CARD.md`
records the remediation order; the most valuable step is training on the Indian
corpus *in addition to* CUAD rather than on CUAD alone.

**Why this is a good result to report**: the architecture separated the learned
layer from the rule layer precisely so that a weak classifier could not
compromise explainability. That separation is what allows the project to measure
this honestly, revert the classifier, and still ship a working product. A
single end-to-end model would have had no such fallback.

---

## 17. Defects Found During Development

Six substantive defects were discovered by executing the system rather than
reviewing it. They are recorded here because the pattern is instructive: in each
case plausible-looking code did the wrong thing on real legal language.

### 17.1 Rubric defects

Four defects in the risk layer surfaced only because the keyword baseline
allowed the complete pipeline to run against a realistic contract before the
model existed.

**1. Missed statutory payment term.** `payment_term_over_45_days` silently
failed to fire on "within ninety (90) days". The regular expression expected
digits *before* the unit word, but this construction places the word first and
the digits in brackets. Corrected by locating the unit word and searching
backwards for a figure in either digits or words.

**2. False positives from an over-broad cue.** The baseline cue `exclusive`
matched "exclusive **of GST**" (a tax term) and "exclusive **jurisdiction**" (a
forum term), causing an exclusivity rule to fire on a payment clause and a
governing-law clause. Corrected by replacing the bare cue with specific phrases.

**3. Asymmetry detector blind to permissions.**
`unilateral_termination_for_convenience` never fired, because "the Customer
**may** terminate" expresses a *permission* while the detector matched only
obligation verbs (`shall`, `must`). Corrected by adding a distinct
`one_sided_right` primitive.

**4. Wrong proxy for a notice period, and a defect interaction.** Using "any
number present" as a proxy for "a notice period is stated" caused
`"successive periods of twelve months … unless written notice is given"` to be
read as a 360-day notice period. The genuine finding — an auto-renewal with **no
opt-out window at all** — was suppressed, and the clause was reported as merely
having a long notice period. The opposite of correct.

Significantly, **fixing defect 1 would have introduced this one**: before the
fix no figure was extracted from that sentence at all, so the absence check
accidentally gave the right answer. The two had to be corrected together.
Resolved by anchoring notice detection to notice vocabulary within a 40-character
window, with a sentence-boundary guard.

### 17.2 Infrastructure defects

**5. Migration test validating nothing.** The Alembic environment set the
database URL from application settings *unconditionally*, overriding the scratch
URL the test supplied. The test was therefore migrating the development database
and would have passed regardless of the migration's correctness. Corrected to
fall back to settings only when no URL was provided.

**6. Irreversible migrations.** Alembic's autogenerate does not drop the
PostgreSQL ENUM types it creates. The generated downgrade removed the tables and
left four enum types behind, so a downgrade-then-upgrade cycle failed with "type
already exists". Corrected by adding explicit `DROP TYPE` statements, with a
test exercising the full round trip.

### 17.4 Defects found by the CUAD audit gate

The audit gate described in Section 11.3 was run three times against the real
dataset. Each round found defects, and each correction measurably reduced label
noise. **None of these would have been visible in the training loss curve** —
which is the entire argument for the gate.

**Round 1 — label noise ~40%.**

*70 of 510 contracts produced no clauses at all.* The segmenter's cascade
accepted a strategy on group *count* alone, so a contract that numbers only a
handful of long recitals yielded six segments averaging 4,000 characters. Every
one was flagged over-long and then discarded, silently losing 14% of the corpus.

This was a genuine defect in production code, not just in the data pipeline:
the same thing would happen to a user uploading an unstructured contract.
Corrected by rejecting a strategy whose output is mostly over-long
(`MAX_OVERLONG_FRACTION`), which falls through to sentence-level splitting.
Recovered 50 contracts and 29% more labelled examples.

The same round also found SEC filing furniture appearing *inside* clause bodies
("[ * ] = Certain confidential information … has been omitted and filed
separately with the Securities and Exchange Commission …" spliced mid-sentence),
heading-only fragments passing the length floor, and the audit sample itself
being ~85% negatives — so it barely tested the thing being audited.

**Round 2 — label noise ~35%.**

*Tables of contents were acquiring labels.* A contents page reads
"20.1 Confidential Terms 41  20.2 Governing Law 41  20.3 Force Majeure 41 …" —
mostly alphabetic, so it passed the boilerplate ratio check, and because it
lists every heading in the document, annotated spans landed on it. One was found
labelled `parties_definitions`.

Corrected with a contents detector. The measure of how much noise this
contributed: `parties_definitions` support fell from 301 to 22.

Also corrected: a short span inside a large fused block was labelling the whole
block, so containment-based assignment now additionally requires the span to be
at least 15% of the clause, and the training length ceiling was tightened from
4,000 to 2,500 characters to match the segmenter's own limit — training only on
clauses the segmenter handled cleanly.

**Round 3 — label noise ~23%.**

*Four CUAD categories had been mapped to classes that do not fit them.*

| CUAD category | Was mapped to | Why that was wrong |
|---|---|---|
| `Non-Disparagement` | `exclusivity_noncompete` | A conduct/morals clause is not a competition restriction. The audit found a clause about bringing someone "into public hatred, contempt, scorn or ridicule" labelled as exclusivity. |
| `Covenant Not To Sue` | `audit_compliance` | Litigation forbearance is not an audit right. |
| `Third Party Beneficiary` | `audit_compliance` | Who may enforce a contract is not an audit right. The audit found a trademark-ownership clause labelled this way. |
| `Post-Termination Services` | `notices_misc` | Transition obligations are not boilerplate. The audit found a termination-for-patent-impact clause labelled this way. |

All four were moved to the `dropped` list, so they become negatives. The
principle: **a forced mapping is worse than no mapping**, because it teaches the
model a wrong association rather than nothing at all.

**Residual noise and its consequence.** The remaining ~23% is annotated spans
landing on text adjacent to the clause they describe. Reducing it further needs
per-category span handling rather than one global rule, which is out of scope
for this version. The figure is a ceiling on achievable precision — a model that
learned the task perfectly would still be scored against partly-wrong labels —
and it is quoted alongside every CUAD metric for that reason.

### 17.5 Methodological observation

None of these are typographical errors. Each is a case where the code was
readable, plausible and wrong — and where only end-to-end execution against
realistic legal text exposed the error. This is the substantive argument for
building the keyword baseline before the model: it made the system executable
months earlier than training would have, and four of the six defects were found
as a direct result.

---

## 18. Resolution of the TBD List

All seven items in the SRS To Be Determined list are closed. Full reasoning is
in `docs/SRS_v1.1_addendum.md`.

| # | Item | Resolved value | Reasoning |
|---|---|---|---|
| 1 | Maximum upload size | **10 MB** | A 20-page text PDF is under 2 MB; 10 MB accommodates image-heavy and poorly-exported files while bounding per-request memory. Enforced both client-side (for a fast message) and server-side on the actual bytes (because a client-side check is a convenience, not a control). |
| 2 | Minimum confidence threshold | **0.45 global floor, with per-class thresholds fitted on validation** | A single global threshold over 20 imbalanced labels sacrifices recall on rare classes — precisely the Indian-relevant ones. |
| 3 | Target processing time | **95th percentile ≤ 30 seconds** for ≤20 pages / ≤50 clauses on 2 vCPU | Component budget: extraction ~2 s, segmentation <1 s, classification 6–10 s, rubric <1 s. Measured at 0.2 s with the baseline. |
| 4 | Concurrent uploads | **5** | One container, two workers, bounded queue of depth 5. Excess work queues rather than being dropped. |
| 5 | Indian template sources | GeM General Terms and Conditions; Indian Contract Act 1872 model forms; MSMED Act / Samadhaan material; BSE and NSE disclosed material contracts; public law-firm template repositories; manually reviewed synthetic agreements | Target 150–200 hand-labelled clauses. Provenance and licence basis recorded per source. No paywalled or licence-restricted material scraped. |
| 6 | Wireframes and style guide | Deferred to a separate design document; five screens | Keeps the SRS a requirements document rather than a design document. |
| 7 | OCR support | **Out of scope for version 1.0**; detect and reject only | Recognition errors would propagate into clause text, then classification, then risk findings, with no signal to the user that the chain began with an imperfect transcription. |

---

## 19. Limitations and Honest Gaps

These are recorded explicitly rather than left implicit. `docs/TRACEABILITY.md`
carries the same list against individual requirements.

### 19.1 The classifier is not trained

The pipeline runs on a keyword baseline. All supporting work is complete — the
taxonomy, the full CUAD mapping with justified exclusions, and the three
scripts — and the conversion logic is verified against synthetic data. The
fine-tuning run requires the CUAD download and GPU time.

**Consequence:** no reportable accuracy figure exists, and classification
quality in the current build is materially below what a fine-tuned transformer
would achieve.

### 19.2 The Indian evaluation set is a seed

Fourteen hand-written examples against the 150–200 the resolved TBD-5 calls for.
Fourteen examples measure nothing; the current file is a format example and a
starting point. Metrics computed on it are not reportable.

### 19.3 Asymmetry detection does not know which party the user is

The one-sidedness detectors flag a clause that runs in one direction, in
**either** direction. Because the upload flow does not capture whether the user
is the supplier or the customer, a clause that is one-sided *in the user's
favour* is also flagged.

A one-sided clause is arguably worth a user's attention regardless of direction,
so the behaviour is defensible — but it is a known imprecision, not a design
intent.

### 19.4 The rubric reads text, not intent

A liability cap expressed in unusual language may be missed, and a clause that
is entirely reasonable in its commercial context may still be flagged. This is
inherent to a rule-based approach and is the reason the output is positioned as
triage rather than advice.

### 19.5 Concurrency is implemented but not load-tested

The semaphore bounds concurrent analyses at five. Nothing yet demonstrates
behaviour under that load.

### 19.6 Transport security is a deployment concern

nginx is the correct termination point for TLS, but no certificates are
configured in the repository.

### 19.7 Segmentation imperfection on unusual formatting

Where a clause could not be cleanly separated the system says so beneath the
clause text, but the user must then consult the original document.

---

## 20. Future Work

### 20.1 Immediate — completing version 1.0

1. **Train the classifier.** Download CUAD, run the conversion, audit fifty
   mapped clauses by hand, train DistilBERT, train Legal-BERT for comparison,
   fit per-class thresholds, and populate the model card.
2. **Expand the Indian evaluation set** to 150–200 hand-labelled clauses,
   weighted towards the six classes CUAD cannot teach.
3. **Re-measure latency** with the trained model to verify the performance
   requirement properly.
4. **Load-test concurrency** at the resolved capacity.

### 20.2 Near term — accuracy and precision

5. **Capture the user's party role at upload**, narrowing asymmetry detection to
   clauses that disadvantage them specifically.
6. **Upgrade asymmetry detection to a dependency parse** (spaCy), replacing the
   current proximity heuristic. Because each rule's logic is isolated in a
   primitive, this change touches one file.
7. **Calibrate confidence scores**, so the values displayed to users are
   probabilities rather than merely ordinal.

### 20.3Later — scope extension

8. **OCR support**, with explicit confidence propagation so the user is told
   when analysis began from an imperfect transcription.
9. **Indian-language contracts**, beginning with Hindi.
10. **Clause-level negotiation suggestions** — proposing replacement wording
    rather than only identifying the problem.
11. **Multi-user organisations** with role-based access.
12. **Rubric versioning in the user interface**, letting a user re-run an old
    contract against the current rubric and see what changed.

---

## 21. Conclusion

ClauseGuard implements the system specified in the SRS as a working, verified,
containerised web application. All nine planned development phases are complete,
with 119 automated tests, a clean lint and type-check, and the full analysis path
verified through the production web server.

The project's substantive contribution is architectural rather than algorithmic:
the insistence that **clause-type classification and risk scoring are different
kinds of problem and must be implemented differently.** Classification is
learned, because recognising what a clause does from its wording is a pattern
problem. Risk scoring is a rule engine over a versioned rubric, because the
requirements demand that every flag be explainable, that criteria be updatable
without retraining, and that historical reports remain auditable against the
rules in force when they were produced. A single end-to-end model would satisfy
none of those.

That separation also produced the project's most useful secondary result. By
placing a deliberately weak but clearly-labelled keyword classifier behind the
same interface as the eventual transformer, the complete pipeline became
executable long before training was possible — and four genuine rubric defects
were found by running real legal text through it, including one that only became
visible as the interaction between two separate fixes.

The work is honest about what it has not done. The transformer is untrained, the
Indian evaluation set is a seed rather than a corpus, and the six most
MSME-relevant clause categories are the ones the base dataset cannot teach. Each
of these is recorded in the traceability matrix rather than concealed, because a
system whose purpose is to tell a small business what it does not know should not
itself overstate what it knows.

---

## Appendix A: Repository Map

```
ClauseGuard/
├── 24BPS1042.pdf              SRS v1.0
├── PLAN.md                    Phased build plan
├── PROJECT_REPORT.md          This document
├── README.md                  Developer quick start
├── docker-compose.yml         Three-service stack
│
├── backend/
│   ├── app/
│   │   ├── main.py            FastAPI application
│   │   ├── pipeline.py        Stage orchestration  ← read this first
│   │   ├── api/
│   │   │   ├── deps.py        Authentication dependency
│   │   │   └── v1/            auth · contracts · reports · health
│   │   ├── core/              config · security
│   │   ├── db/                models · migrations
│   │   ├── schemas/           Request/response models
│   │   └── services/
│   │       ├── extraction/    pdf · docx · plain · base
│   │       ├── segmentation/  segmenter · rules
│   │       ├── classification/ labels · model
│   │       ├── risk/          engine · loader · detectors · rubrics/v1.0.yaml
│   │       ├── reporting/     pdf_renderer
│   │       └── storage.py     File persistence
│   ├── scripts/               generate_rubric_docs · measure_latency
│   └── tests/                 119 tests · fixtures.py
│
├── ml/
│   ├── scripts/               prepare_cuad · train · evaluate
│   ├── configs/               distilbert · legalbert · label_mapping
│   ├── eval/                  indian_eval_set.jsonl
│   └── MODEL_CARD.md          Provenance, metrics, limitations
│
├── frontend/
│   ├── src/
│   │   ├── api/client.ts      Typed API client
│   │   ├── pages/             Auth · Upload · Processing · Report · Dashboard
│   │   └── components/        Nav · Disclaimer
│   └── nginx.conf             Production serving and API proxy
│
└── docs/
    ├── RUBRIC.md              Generated — every rule and criterion
    ├── TRACEABILITY.md        Requirement → module → test
    ├── USER_GUIDE.md          End-user guide, glossary, FAQ
    ├── SRS_v1.1_addendum.md   TBD resolutions
    ├── ADRs/                  Design decision records
    └── wireframes/            Screen documentation
```

---

## Appendix B: Design Decision Records

Full text in `docs/ADRs/`.

### ADR 0001 — Synchronous SQLAlchemy and UUID primary keys

**Synchronous database access** despite FastAPI being an asynchronous framework.
The dominant cost in this system is CPU-bound transformer inference, which blocks
an event loop regardless of whether the database driver is asynchronous.
Asynchronous SQLAlchemy would add substantial complexity while buying no
throughput for this workload. FastAPI executes synchronous handlers in a
threadpool, which is the correct place for blocking work.

**UUID primary keys** to eliminate the identifier-enumeration vector described
in Section 7.3.

### ADR 0002 — reportlab for PDF export

Summarised in Section 12.1.

### ADR 0003 — Classifier behind an interface, with a keyword baseline

Summarised in Section 8.3.

---

## Appendix C: Anticipated Viva Questions

**Where is the machine learning in this project?**
Clause-type classification: a fine-tuned DistilBERT with twenty sigmoid heads,
multi-label binary cross-entropy with class weighting, and sliding-window
pooling for clauses exceeding the token limit. Risk scoring is deliberately not
machine learning, and that is the central design argument rather than an
omission.

**Why not have the model predict risk directly?**
Three requirements forbid it. REQ-4.2 requires documented criteria rather than
an unexplained score. REQ-4.4 requires the criteria to be updatable without
retraining. The auditability requirement in section 5.5 requires historical
reports to remain explainable against a versioned rubric. A model score
satisfies none of these.

**What accuracy does the system achieve?**
None is reportable yet: the classifier is untrained and the system currently
runs on a clearly-labelled keyword baseline whose output is not a result. When
trained, the reported metrics will be macro-F1 and per-class precision, recall
and F1 — not accuracy, which on a twenty-label imbalanced multi-label task is
dominated by true negatives and would overstate performance.

**Why report two separate metric tables?**
CUAD measures US mergers-and-acquisitions contracts; the product serves Indian
MSME agreements. The gap between the two is the honest measure of how far the
model transfers, and a single figure from the easier distribution would
misrepresent the system.

**What is the weakest part of the system?**
The six clause classes CUAD cannot teach — cure periods, late payment and GST,
indemnity, confidentiality, arbitration and force majeure — which are
simultaneously the most MSME-relevant. This is visible by design in the
per-class results rather than averaged away.

**How do you know the segmentation is correct?**
Through several independent checks: character offsets are asserted to map
exactly onto the source text; the same contract in PDF and DOCX form must
produce identical clauses; segmentation must be deterministic across runs; and
sub-items must remain attached to their parent clause. Clauses the segmenter
could not confidently isolate are flagged to the user rather than silently
presented as clean.

**What happens if a component fails?**
The system degrades rather than failing. A detector raising an exception causes
that rule not to fire, logged, without failing the clause or the report. A
clause that cannot be assessed is shown with its text and type, marked "not
assessed". A missing model checkpoint falls back to the baseline. An unreachable
database produces a 503 from the health endpoint rather than a 500.

**Is it safe for a business to rely on?**
No, and the system states so on every screen, in every API response and on every
page of the exported PDF. It is a triage tool whose purpose is to decide what to
ask a lawyer about.

**What would you do differently?**
Capture the user's party role at upload from the beginning. The asymmetry
detectors are the most interesting component in the rubric, and not knowing
which side the user is on limits their precision in a way that would have been
cheap to avoid had it been designed in rather than retrofitted.

---

## References

1. Hendrycks, D., Burns, C., Chen, A., & Ball, S. (2021). *CUAD: An
   Expert-Annotated NLP Dataset for Legal Contract Review.*
   https://arxiv.org/abs/2103.06268

2. Lippi, M. et al. (2019). *CLAUDETTE: an Automated Detector of Potentially
   Unfair Clauses in Online Terms of Service.* Artificial Intelligence and Law.
   https://arxiv.org/abs/1805.01217

3. Singh, Joshi, Jiang & Paik (2025). *A Survey of Classification Tasks and
   Approaches for Legal Contracts.* Artificial Intelligence Review.
   https://arxiv.org/abs/2507.21108

4. *Is It Worth Using LLMs for Unfair Clause Detection in Terms of Service?*
   AI & Law 2025 Conference Proceedings.
   https://dl.acm.org/doi/full/10.1145/3769126.3769218

5. Chalkidis, I., Fergadiotis, M., Malakasiotis, P., & Androutsopoulos, I.
   (2020). *LEGAL-BERT: The Muppets Straight Out of Law School.* EMNLP Findings.
   https://aclanthology.org/2020.findings-emnlp.261/

6. The Atticus Project — CUAD dataset documentation, Hugging Face.
   https://huggingface.co/datasets/theatticusproject/cuad

7. *Indian Contract Act, 1872* — domain norms governing Indian commercial
   contract clauses.

8. *Micro, Small and Medium Enterprises Development Act, 2006* — statutory
   payment terms and delayed-payment interest.

9. *Arbitration and Conciliation Act, 1996* — India-seated arbitration.
