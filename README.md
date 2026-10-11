# ClauseGuard

AI-powered contract clause classification and risk triage for Indian MSMEs.

Upload a vendor, supply, NDA or service contract; get a clause-by-clause
breakdown that classifies each provision by legal type, flags the risky ones
against a documented fairness rubric, and explains in plain language why each
flag was raised.

The goal is **triage, not legal advice**: cheaply identify which 2–3 clauses in
a 20-clause contract deserve a paid legal opinion.

> ClauseGuard is an educational triage tool. It does not provide legal advice.
> High-stakes contracts should be reviewed by a licensed professional.
> *(SRS §2.5, §5.2, §5.5)*

**Software Engineering project — Tanmaya Gupta, 24BPS1042, VIT Chennai.**
Requirements: `24BPS1042.pdf` (SRS v1.0) plus `docs/SRS_v1.1_addendum.md`.
Build plan: `PLAN.md`.

---

## The one design decision that matters

> **Clause-type classification is learned. Risk scoring is not.**

Clause typing is a fine-tuned transformer over 20 multi-label classes. Risk
scoring is a rule engine over a versioned, human-readable YAML rubric. Every
risk label traces to a named rule with a documented criterion, and every report
records which rubric version produced it — so a report stays explainable even
after the rubric changes.

That separation delivers the Explainability requirement in SRS §5.4, and it is
the invariant to preserve when changing this codebase. The published rubric is
`docs/RUBRIC.md` (generated from the YAML; CI fails if it drifts).

---

## Quick start

```bash
cp .env.example .env            # optional; defaults work for local development
docker compose up -d --build
```

Over HTTPS instead (self-signed, for local TLS testing):

```bash
bash scripts/generate_dev_certs.sh certs
docker compose -f docker-compose.yml -f docker-compose.tls.yml up -d --build
# https://localhost — accept the browser warning
```

- **App:** <http://localhost:5173>
- **API docs:** <http://localhost:8000/docs>
- **Health:** <http://localhost:8000/api/v1/health>
- PostgreSQL on host port **5433** (not 5432, to avoid clashing with other
  local Postgres instances; override with `POSTGRES_HOST_PORT`)

Migrations run automatically on container start. Register an account in the UI
and upload a contract.

No sample contract to hand? The test fixtures generate one:

```bash
cd backend
python -c "
import sys; sys.path.insert(0, '.')
from tests.fixtures import make_pdf
open('sample-contract.pdf','wb').write(make_pdf())
"
```

It is a synthetic Indian supply agreement seeded with 15 specific risks, so the
report has plenty to show.

## Running the tests

The schema uses PostgreSQL-specific types (`UUID`, `JSONB`, native enums), so
the tests need a real server rather than SQLite.

```bash
docker compose up -d db

cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Linux/macOS: .venv/bin/python

REQUIRE_DB=1 .venv/Scripts/python -m pytest -v
.venv/Scripts/python -m ruff check .
```

Database tests **skip** when no server is reachable, so `pytest` still passes on
a bare checkout. `REQUIRE_DB=1` turns that skip into a failure — CI sets it so a
green build cannot hide skipped tests.

Frontend:

```bash
cd frontend
npm install
npm run build        # runs `tsc -b` first, so type errors fail the build
npm run dev          # dev server on :5173, proxying /api to :8000
```

## Useful commands

```bash
# Regenerate docs/RUBRIC.md after editing the rubric YAML
python backend/scripts/generate_rubric_docs.py

# Measure pipeline latency against the TBD-3 budget (30s for ~50 clauses)
python backend/scripts/measure_latency.py --clauses 50 --runs 5

# Load-test concurrent analysis against the TBD-4 capacity
python backend/scripts/load_test.py --concurrency 10

# Rebuild the Indian evaluation set from reviewable source
python ml/eval/build_eval_set.py

# Migrations
cd backend
.venv/Scripts/python -m alembic upgrade head
.venv/Scripts/python -m alembic revision --autogenerate -m "describe the change"
```

## Training the classifier

The app runs today on a keyword baseline, so the pipeline is complete and
testable without a trained model (ADR 0003). To train the real one:

```bash
pip install -r ml/requirements.txt

# 1. Download CUADv1.json from https://github.com/TheAtticusProject/cuad
#    into ml/data/raw/
python ml/scripts/prepare_cuad.py --audit 50

# 2. READ ml/data/processed/audit_sample.txt AND CHECK 50 CLAUSES BY HAND.
#    This is a gate, not a formality — a bad span-to-clause mapping is
#    invisible in the loss curve and makes every downstream metric meaningless.

python ml/scripts/train.py --config ml/configs/distilbert.yaml
python ml/scripts/evaluate.py --checkpoint ml/artifacts/distilbert
```

Then serve it:

```bash
CLAUSEGUARD_MODEL_DIR=/path/to/ml/artifacts/distilbert
```

Nothing else changes — no code edit, no migration. The `model_version` recorded
on every prediction and report switches from `baseline-keyword-v1` to the
trained checkpoint's version, so results can never be confused.

See `ml/README.md` for the order of work and the traps.

## Repository layout

```
backend/
  app/
    api/v1/        auth, contracts, reports, health
    core/          config, security (bcrypt + JWT)
    db/            models, migrations
    services/
      extraction/      PDF (PyMuPDF) / DOCX (python-docx) / plain text
      segmentation/    numbering -> heading -> paragraph cascade
      classification/  taxonomy, transformer + keyword baseline
      risk/            rubric loader, engine, detector primitives, rubrics/*.yaml
      reporting/       PDF export (reportlab)
    pipeline.py    stage orchestration and persistence
  scripts/         rubric doc generator, latency measurement
  tests/           119 tests
ml/
  scripts/         prepare_cuad, train, evaluate
  configs/         model configs, CUAD label mapping
  eval/            Indian evaluation set
  MODEL_CARD.md    provenance, metrics, limitations
frontend/src/      React + TypeScript SPA (5 screens)
docs/
  RUBRIC.md             generated — every rule and criterion
  TRACEABILITY.md       REQ -> module -> test, with deliberate gaps named
  USER_GUIDE.md         end-user guide, glossary, FAQ (SRS 2.6)
  SRS_v1.1_addendum.md  all 7 Appendix C TBDs resolved
  ADRs/                 design decisions and their trade-offs
PLAN.md            phased build plan
```

## Status

All nine phases of `PLAN.md` are implemented, and the classifier has been
trained and evaluated on the real CUAD dataset.

> **The trained model is not the served one.** It scores macro-F1 0.566 on CUAD
> and 0.302 on Indian contracts, but types only 7 of 16 fixture clauses against
> the keyword baseline's 15 - because seven of the twenty classes have zero CUAD
> training support and cannot be predicted at all. The baseline remains the
> default. Full reasoning and remediation order in `ml/MODEL_CARD.md`.

| Phase | | |
|---|---|---|
| 0 | Foundation: schema, migrations, health, CI, Docker | ✅ |
| 1 | Upload and text extraction | ✅ |
| 2 | Clause segmentation | ✅ |
| 3 | Classifier: taxonomy, interface, baseline, trained + evaluated | ✅ (baseline served — see note) |
| 4 | Risk rubric engine (21 clause rules + 4 contract rules) | ✅ |
| 5 | Auth and per-user scoping | ✅ |
| 6 | Frontend (5 screens) | ✅ |
| 7 | PDF report export | ✅ |
| 8 | NFR hardening, latency + load measurement, TLS, user docs | ✅ |
| 9 | Containerised deployment, traceability, ADRs | ✅ |

`docs/TRACEABILITY.md` has requirement-by-requirement status and a section
naming every deliberate gap.

### Measured, not assumed

- **Latency (TBD-3):** **2.78 s** worst case for 51 clauses with the trained
  DistilBERT (2.627 s of it classification), against a 30 s budget - better than
  10x headroom. 0.2 s with the keyword baseline.
- **Classification accuracy:** CUAD test macro-F1 **0.566** over the 13 classes
  with test support (micro-F1 0.564); Indian evaluation set **0.302**. The
  like-for-like domain gap is **0.264** - performance roughly halves on the
  domain the product serves.
- **Concurrency (TBD-4):** 10 simultaneous analyses — twice the stated
  capacity — none rejected, all completed, identical results, 8.46× speedup.
  `python backend/scripts/load_test.py --concurrency 10`
- **TLS (§5.3):** TLSv1.3 / AES-256-GCM, HTTP→HTTPS redirect, HSTS and CSP
  verified against the running stack. See `docs/DEPLOYMENT.md`.
- **Tests:** 119 passing, including the full analysis path through nginx.
- **Cross-format agreement:** the same contract as PDF and as DOCX segments
  into identical clauses.
- **CUAD conversion:** real dataset converted — 490 of 510 contracts, 20k
  clauses. Label noise measured at ~23% after three rounds of audit-driven
  correction; see the audit record in `ml/MODEL_CARD.md`.

## Stack

FastAPI · PostgreSQL 16 · SQLAlchemy 2 · Alembic · PyMuPDF · python-docx ·
pysbd · PyTorch / Hugging Face Transformers · reportlab · React · TypeScript ·
Tailwind · Vite · nginx · Docker

Design decisions and their trade-offs are recorded in `docs/ADRs/`.
