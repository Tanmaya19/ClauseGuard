"""Contract upload, status, history and deletion.

Every query here filters on ``user_id`` as well as the contract id. The id is
a UUID and therefore unguessable, but SRS 5.3 requires that contract content be
restricted to its owner, and that has to be enforced in the query rather than
left to the difficulty of guessing an identifier.
"""

from __future__ import annotations

import logging
import uuid
from collections import Counter

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import current_user
from app.core.config import get_settings
from app.db.models import (
    Clause,
    ClauseRisk,
    Contract,
    ContractStatus,
    Report,
    RiskLevel,
    User,
)
from app.db.session import get_db
from app.pipeline import analyse
from app.schemas.contracts import (
    ContractSummary,
    DashboardResponse,
    StatusResponse,
    UploadResponse,
)
from app.services import storage
from app.services.extraction import ExtractionError, detect_format

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/contracts", tags=["contracts"])

# Rough progress per stage, for the processing screen's progress bar.
_PROGRESS = {
    ContractStatus.UPLOADED: 5,
    ContractStatus.EXTRACTING: 20,
    ContractStatus.SEGMENTING: 40,
    ContractStatus.CLASSIFYING: 65,
    ContractStatus.SCORING: 85,
    ContractStatus.COMPLETE: 100,
    ContractStatus.FAILED: 100,
}

# Mapped to user-facing copy here rather than in the frontend so the API is
# self-describing and the two cannot drift.
_ERROR_MESSAGES = {
    "no_extractable_text": (
        "This file appears to be a scan or a photo of a contract, so there is no text "
        "we can read. Please upload a text-based PDF or Word version."
    ),
    "unsupported_format": "Only PDF and Word (.docx) files can be analysed.",
    "encrypted_file": "This file is password-protected. Remove the password and try again.",
    "corrupt_file": "This file could not be opened. It may be damaged or incomplete.",
    "internal_error": (
        "Something went wrong while analysing this contract. Please try uploading it again."
    ),
}


@router.post(
    "", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED
)
def upload(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> UploadResponse:
    """Accept a contract and queue it for analysis (REQ-1.1, REQ-1.2, REQ-1.5)."""
    settings = get_settings()

    data = file.file.read()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The uploaded file is empty.")

    # REQ-1.2. Enforced on the actual bytes, not on the Content-Length header,
    # which a client controls and can understate.
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"This file is larger than the {settings.max_upload_mb} MB limit. "
            "Please upload a smaller file.",
        )

    # REQ-1.1, checked synchronously so an unusable file is rejected with a
    # clear message instead of becoming a failed background job.
    try:
        fmt = detect_format(data, file.filename)
    except ExtractionError as exc:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, exc.user_message) from exc

    contract = Contract(
        user_id=user.id,
        filename=(file.filename or "contract")[:512],
        mime=file.content_type or f"application/{fmt}",
        size_bytes=len(data),
        storage_path="",  # set below, once the id exists
        status=ContractStatus.UPLOADED,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)

    contract.storage_path = storage.save(user.id, contract.id, fmt, data)
    db.commit()

    background.add_task(analyse, contract.id)

    return UploadResponse(
        contract_id=contract.id,
        filename=contract.filename,
        status=contract.status,
        poll_url=f"/api/v1/contracts/{contract.id}/status",
    )


def _owned(db: Session, contract_id: uuid.UUID, user: User) -> Contract:
    contract = db.scalar(
        select(Contract).where(Contract.id == contract_id, Contract.user_id == user.id)
    )
    if contract is None:
        # 404 rather than 403: confirming that someone else's contract exists
        # would itself leak information.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contract not found.")
    return contract


@router.get("/{contract_id}/status", response_model=StatusResponse)
def analysis_status(
    contract_id: uuid.UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> StatusResponse:
    contract = _owned(db, contract_id, user)
    return StatusResponse(
        contract_id=contract.id,
        status=contract.status,
        status_detail=contract.status_detail,
        error_code=contract.error_code,
        error_message=_ERROR_MESSAGES.get(contract.error_code or ""),
        progress=_PROGRESS.get(contract.status, 0),
    )


@router.get("", response_model=list[ContractSummary])
def history(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    limit: int = 50,
) -> list[ContractSummary]:
    """Dashboard history list (REQ-6.3)."""
    contracts = db.scalars(
        select(Contract)
        .where(Contract.user_id == user.id)
        .order_by(Contract.uploaded_at.desc())
        .limit(min(limit, 200))
    ).all()

    return [_summarise(db, c) for c in contracts]


def _summarise(db: Session, contract: Contract) -> ContractSummary:
    summary = ContractSummary(
        id=contract.id,
        filename=contract.filename,
        status=contract.status,
        uploaded_at=contract.uploaded_at,
        processed_at=contract.processed_at,
    )

    if contract.status is not ContractStatus.COMPLETE:
        return summary

    report = db.scalar(select(Report).where(Report.contract_id == contract.id))
    if report is not None:
        counts = report.summary_json.get("risk_counts", {})
        summary.clause_count = report.summary_json.get("clause_count")
        summary.high_risk_count = counts.get(RiskLevel.HIGH_RISK.value, 0)
        summary.caution_count = counts.get(RiskLevel.CAUTION.value, 0)

    return summary


@router.get("/dashboard/overview", response_model=DashboardResponse)
def dashboard(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    """Aggregates for the dashboard view (SRS 2.2, REQ-6.3)."""
    total_contracts = (
        db.scalar(select(func.count(Contract.id)).where(Contract.user_id == user.id)) or 0
    )

    risk_rows = db.execute(
        select(ClauseRisk.level, func.count(ClauseRisk.clause_id))
        .join(Clause, Clause.id == ClauseRisk.clause_id)
        .join(Contract, Contract.id == Clause.contract_id)
        .where(Contract.user_id == user.id)
        .group_by(ClauseRisk.level)
    ).all()
    risk_totals = {level.value: 0 for level in RiskLevel}
    for level, count in risk_rows:
        risk_totals[level.value if hasattr(level, "value") else str(level)] = count

    # Grouped in the database rather than in Python: the history list can grow
    # unbounded and pulling every row back to count them would not scale.
    over_time = db.execute(
        select(
            func.date(Contract.uploaded_at).label("day"),
            func.count(Contract.id),
        )
        .where(Contract.user_id == user.id)
        .group_by(func.date(Contract.uploaded_at))
        .order_by(func.date(Contract.uploaded_at))
    ).all()

    recent = db.scalars(
        select(Contract)
        .where(Contract.user_id == user.id)
        .order_by(Contract.uploaded_at.desc())
        .limit(5)
    ).all()

    return DashboardResponse(
        total_contracts=total_contracts,
        total_clauses=sum(risk_totals.values()),
        risk_totals=risk_totals,
        reviewed_over_time=[{"date": str(day), "count": count} for day, count in over_time],
        recent=[_summarise(db, c) for c in recent],
    )


@router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contract(
    contract_id: uuid.UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Delete a contract and everything derived from it (SRS 5.3)."""
    contract = _owned(db, contract_id, user)
    path = contract.storage_path

    db.delete(contract)  # cascades to clauses, predictions, findings, risk, report
    db.commit()

    if path:
        storage.delete(path)

    logger.info("Deleted contract %s for user %s", contract_id, user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{contract_id}/reanalyse", response_model=UploadResponse)
def reanalyse(
    contract_id: uuid.UUID,
    background: BackgroundTasks,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> UploadResponse:
    """Re-run the pipeline, e.g. after the rubric or the model changes.

    Supports REQ-4.4: a rubric update should be applicable without retraining,
    and without the user having to upload the file again.
    """
    contract = _owned(db, contract_id, user)

    if contract.status in {
        ContractStatus.EXTRACTING,
        ContractStatus.SEGMENTING,
        ContractStatus.CLASSIFYING,
        ContractStatus.SCORING,
    }:
        raise HTTPException(status.HTTP_409_CONFLICT, "This contract is already being analysed.")

    contract.status = ContractStatus.UPLOADED
    contract.error_code = None
    contract.status_detail = None
    db.commit()

    background.add_task(analyse, contract.id)

    return UploadResponse(
        contract_id=contract.id,
        filename=contract.filename,
        status=contract.status,
        poll_url=f"/api/v1/contracts/{contract.id}/status",
    )


# Imported late to avoid a circular import at module load: reports needs the
# ownership helper defined above.
def owned_contract(db: Session, contract_id: uuid.UUID, user: User) -> Contract:
    return _owned(db, contract_id, user)


def clause_counter(db: Session, contract_id: uuid.UUID) -> Counter[str]:
    """Risk tally for one contract, used by the report and the PDF export."""
    rows = db.execute(
        select(ClauseRisk.level, func.count(ClauseRisk.clause_id))
        .join(Clause, Clause.id == ClauseRisk.clause_id)
        .where(Clause.contract_id == contract_id)
        .group_by(ClauseRisk.level)
    ).all()
    return Counter({str(getattr(level, "value", level)): count for level, count in rows})


def load_clauses(db: Session, contract_id: uuid.UUID) -> list[Clause]:
    """Clauses with predictions, findings and risk eagerly loaded.

    ``selectinload`` rather than lazy access: a 50-clause report would
    otherwise issue 150+ queries, which on its own could threaten the TBD-3
    latency budget.
    """
    return list(
        db.scalars(
            select(Clause)
            .where(Clause.contract_id == contract_id)
            .order_by(Clause.ordinal)
            .options(
                selectinload(Clause.predictions),
                selectinload(Clause.findings),
                selectinload(Clause.risk),
            )
        ).all()
    )
