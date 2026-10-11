"""Analysis pipeline orchestration.

Stages run in order, each advancing ``Contract.status`` so the Processing
Screen (SRS 3.1) can report progress by polling. The orchestrator owns all
persistence; the stage services themselves are pure functions with no database
or HTTP awareness, which is what makes them unit-testable and swappable
(SRS 5.4 Maintainability).

Concurrency is bounded by a semaphore sized from ``max_concurrent_analyses``
(TBD-4 = 5). Work beyond that **queues** rather than being rejected, which is
what SRS 5.1 asks for.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import (
    Clause,
    ClausePrediction,
    ClauseRisk,
    Contract,
    ContractStatus,
    Report,
    RiskFinding,
    RubricVersion,
)
from app.db.session import SessionLocal
from app.services import storage
from app.services.classification import UNCATEGORIZED, display_name, get_classifier
from app.services.extraction import ExtractionError, extract
from app.services.risk import assess_contract, get_rubric
from app.services.segmentation import segment

logger = logging.getLogger(__name__)

_settings = get_settings()
_slots = threading.BoundedSemaphore(_settings.max_concurrent_analyses)


def _set_status(
    db: Session,
    contract: Contract,
    status: ContractStatus,
    detail: str | None = None,
) -> None:
    contract.status = status
    contract.status_detail = detail
    db.commit()


def ensure_rubric_registered(db: Session, version: str | None = None) -> str:
    """Record the active rubric's hash so reports stay auditable (SRS 5.5).

    If a rubric file is edited in place without bumping its version, the hash
    changes and this notices. The stored row is not overwritten — the original
    hash is what historical reports were produced under.
    """
    rubric = get_rubric(version)
    row = db.get(RubricVersion, rubric.version)

    if row is None:
        db.add(
            RubricVersion(
                version=rubric.version,
                yaml_sha256=rubric.sha256,
                notes=rubric.notes[:2000] or None,
            )
        )
        db.commit()
    elif row.yaml_sha256 != rubric.sha256:
        logger.error(
            "Rubric v%s on disk (sha %s) differs from the registered hash (%s). "
            "Historical reports were produced under the registered version; bump "
            "the rubric version instead of editing a published one.",
            rubric.version,
            rubric.sha256[:12],
            row.yaml_sha256[:12],
        )

    return rubric.version


def analyse(contract_id: uuid.UUID) -> None:
    """Run the full pipeline for one contract. Safe to call from a worker thread.

    Never raises: a failure is recorded on the contract as ``failed`` with an
    ``error_code``, because the caller is a background task with nowhere to
    propagate an exception to.
    """
    with _slots:
        started = time.perf_counter()
        db = SessionLocal()
        try:
            contract = db.get(Contract, contract_id)
            if contract is None:
                logger.error("Contract %s vanished before analysis", contract_id)
                return
            _run(db, contract)
            logger.info(
                "Analysed contract %s in %.2fs", contract_id, time.perf_counter() - started
            )
        except ExtractionError as exc:
            _fail(db, contract_id, exc.error_code, str(exc))
        except Exception as exc:  # noqa: BLE001 — background task boundary
            logger.exception("Pipeline failed for %s", contract_id)
            _fail(db, contract_id, "internal_error", str(exc))
        finally:
            db.close()


def _fail(db: Session, contract_id: uuid.UUID, code: str, detail: str) -> None:
    try:
        db.rollback()
        contract = db.get(Contract, contract_id)
        if contract is None:
            return
        contract.status = ContractStatus.FAILED
        contract.error_code = code
        contract.status_detail = detail[:255]
        db.commit()
    except Exception:
        logger.exception("Could not record failure for %s", contract_id)


def _run(db: Session, contract: Contract) -> None:
    rubric_version = ensure_rubric_registered(db)

    # --- 1. Extract ----------------------------------------------------
    _set_status(db, contract, ContractStatus.EXTRACTING, "Reading the document")
    document = extract(storage.read(contract.storage_path), contract.filename)
    contract.raw_text = document.text
    db.commit()

    # --- 2. Segment ----------------------------------------------------
    _set_status(db, contract, ContractStatus.SEGMENTING, "Splitting into clauses")
    segments = segment(document)
    if not segments:
        raise ValueError("segmentation produced no clauses")

    # Re-analysis of the same contract must not accumulate duplicate rows.
    _clear_previous(db, contract.id)

    clauses = [
        Clause(
            contract_id=contract.id,
            ordinal=s.ordinal,
            heading=s.heading,
            text=s.text,
            char_start=s.char_start,
            char_end=s.char_end,
            segmentation_method=s.method,
            needs_manual_review=s.needs_manual_review,
        )
        for s in segments
    ]
    db.add_all(clauses)
    db.commit()
    for clause in clauses:
        db.refresh(clause)

    # --- 3. Classify ---------------------------------------------------
    _set_status(
        db, contract, ContractStatus.CLASSIFYING, f"Identifying {len(clauses)} clause types"
    )
    classifier = get_classifier()
    predictions = classifier.classify([c.text for c in clauses])

    db.add_all(
        [
            ClausePrediction(
                clause_id=clause.id,
                label=prediction.label,
                confidence=prediction.confidence,
                model_version=classifier.model_version,
            )
            for clause, clause_predictions in zip(clauses, predictions, strict=True)
            for prediction in clause_predictions
        ]
    )
    db.commit()

    # --- 4. Score ------------------------------------------------------
    _set_status(db, contract, ContractStatus.SCORING, "Checking clauses against the rubric")
    labelled = [
        (clause.text, frozenset(p.label for p in preds))
        for clause, preds in zip(clauses, predictions, strict=True)
    ]
    assessment = assess_contract(
        labelled, contract_text=document.text, rubric_version=rubric_version
    )

    for clause, level, findings in zip(
        clauses, assessment.clause_levels, assessment.clause_findings, strict=True
    ):
        db.add(
            ClauseRisk(clause_id=clause.id, level=level, rubric_version=rubric_version)
        )
        db.add_all(
            [
                RiskFinding(
                    clause_id=clause.id,
                    rule_id=finding.rule_id,
                    severity=finding.severity,
                    explanation=finding.explanation,
                    rubric_version=rubric_version,
                )
                for finding in findings
            ]
        )
    db.commit()

    # --- 5. Report -----------------------------------------------------
    db.add(
        Report(
            contract_id=contract.id,
            rubric_version=rubric_version,
            model_version=classifier.model_version,
            summary_json=_summary(clauses, predictions, assessment),
        )
    )
    contract.processed_at = datetime.now(UTC)
    _set_status(db, contract, ContractStatus.COMPLETE, None)


def _clear_previous(db: Session, contract_id: uuid.UUID) -> None:
    existing = db.scalars(select(Clause).where(Clause.contract_id == contract_id)).all()
    for clause in existing:
        db.delete(clause)  # cascades to predictions, findings and risk
    report = db.scalar(select(Report).where(Report.contract_id == contract_id))
    if report is not None:
        db.delete(report)
    db.commit()


def _summary(clauses: list[Clause], predictions: list, assessment) -> dict:
    """Precomputed report header (REQ-5.4) and contract-level findings.

    Stored rather than recomputed so re-opening a past report (REQ-6.4) is one
    row read instead of an aggregation over every clause.
    """
    counts = assessment.counts
    type_tally: dict[str, int] = {}
    for clause_predictions in predictions:
        for prediction in clause_predictions:
            type_tally[prediction.label] = type_tally.get(prediction.label, 0) + 1

    return {
        "clause_count": len(clauses),
        "risk_counts": counts,
        "needs_review_count": sum(1 for c in clauses if c.needs_manual_review),
        "uncategorized_count": sum(1 for p in predictions if not p),
        "clause_type_counts": type_tally,
        "clause_type_labels": {k: display_name(k) for k in type_tally},
        "contract_findings": [
            {
                "rule_id": f.rule_id,
                "severity": f.severity.value,
                "explanation": f.explanation,
                "criterion": f.criterion,
            }
            for f in assessment.contract_findings
        ],
        "uncategorized_label": UNCATEGORIZED,
    }
