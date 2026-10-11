"""Report retrieval and PDF export (REQ-5.1 to REQ-5.4, REQ-6.4)."""

from __future__ import annotations

import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.api.v1.contracts import load_clauses, owned_contract
from app.db.models import Clause, Contract, ContractStatus, Report, RiskLevel, User
from app.db.session import get_db
from app.schemas.contracts import (
    DISCLAIMER,
    ClauseOut,
    ClauseTypeOut,
    FindingOut,
    PredictionOut,
    ReportResponse,
)
from app.services.classification import CLAUSE_TYPES, display_name
from app.services.reporting import render_report_pdf

router = APIRouter(tags=["reports"])


@router.get("/clause-types", response_model=list[ClauseTypeOut])
def clause_types() -> list[ClauseTypeOut]:
    """The taxonomy, so the frontend never hard-codes label names."""
    return [
        ClauseTypeOut(key=c.key, display=c.display, description=c.description)
        for c in CLAUSE_TYPES
    ]


def _build(db: Session, contract: Contract) -> ReportResponse:
    report = db.scalar(select(Report).where(Report.contract_id == contract.id))
    if report is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This contract has no report yet. Check its status first.",
        )

    clauses = load_clauses(db, contract.id)

    return ReportResponse(
        contract_id=contract.id,
        filename=contract.filename,
        uploaded_at=contract.uploaded_at,
        generated_at=report.generated_at,
        rubric_version=report.rubric_version,
        model_version=report.model_version,
        summary=report.summary_json,
        clauses=[_clause_out(c) for c in clauses],
        disclaimer=DISCLAIMER,
    )


def _clause_out(clause: Clause) -> ClauseOut:
    return ClauseOut(
        id=clause.id,
        ordinal=clause.ordinal,
        heading=clause.heading,
        text=clause.text,
        # A clause with no risk row has not been scored; reporting it as
        # "safe" would be a false reassurance (SRS 5.2, 5.4).
        risk=clause.risk.level if clause.risk else RiskLevel.UNASSESSABLE,
        predictions=[
            PredictionOut(
                label=p.label, display=display_name(p.label), confidence=p.confidence
            )
            for p in sorted(clause.predictions, key=lambda p: p.confidence, reverse=True)
        ],
        findings=[
            FindingOut(rule_id=f.rule_id, severity=f.severity, explanation=f.explanation)
            for f in clause.findings
        ],
        needs_manual_review=clause.needs_manual_review,
        segmentation_method=clause.segmentation_method,
    )


@router.get("/reports/{contract_id}", response_model=ReportResponse)
def get_report(
    contract_id: uuid.UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> ReportResponse:
    """Full clause-by-clause report (REQ-5.1). Re-openable at any time (REQ-6.4)."""
    contract = owned_contract(db, contract_id, user)

    if contract.status is ContractStatus.FAILED:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "This contract could not be analysed."
        )
    if contract.status is not ContractStatus.COMPLETE:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "This contract is still being analysed."
        )

    return _build(db, contract)


@router.get(
    "/reports/{contract_id}/pdf",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
def export_pdf(
    contract_id: uuid.UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Download the report as a print-ready PDF (REQ-5.3)."""
    contract = owned_contract(db, contract_id, user)
    if contract.status is not ContractStatus.COMPLETE:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "This contract is still being analysed."
        )

    report = _build(db, contract)
    pdf = render_report_pdf(report)

    stem = (contract.filename.rsplit(".", 1)[0] or "contract")[:80]
    filename = f"ClauseGuard - {stem}.pdf"

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            # Both forms: filename* carries the UTF-8 original for modern
            # browsers, filename is the ASCII fallback for older ones.
            "Content-Disposition": (
                f'attachment; filename="report.pdf"; '
                f"filename*=UTF-8''{quote(filename)}"
            )
        },
    )
