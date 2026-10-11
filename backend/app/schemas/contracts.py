"""Contract and report schemas (REQ-5.1 to REQ-5.4, REQ-6.3, REQ-6.4)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.db.models import ContractStatus, FindingSeverity, RiskLevel, SegmentationMethod

# Shown on every report and every export (SRS 5.2, 5.5). Served from the API
# rather than hard-coded in the frontend so the wording cannot drift between
# the web view and the PDF.
DISCLAIMER = (
    "ClauseGuard is an automated triage tool, not a lawyer. It highlights clauses "
    "that are commonly one-sided so you can decide what deserves professional "
    "review. It can miss things and it can flag things that are fine in context. "
    "Do not rely on it alone for a contract that matters — have a licensed "
    "professional review anything significant before you sign."
)


class UploadResponse(BaseModel):
    """202 response: analysis has been queued, not completed."""

    contract_id: uuid.UUID
    filename: str
    status: ContractStatus
    poll_url: str


class StatusResponse(BaseModel):
    contract_id: uuid.UUID
    status: ContractStatus
    status_detail: str | None = None
    error_code: str | None = None
    error_message: str | None = Field(
        default=None, description="Plain-language explanation, safe to show the user."
    )
    progress: int = Field(description="Rough percentage, for the processing screen.")


class PredictionOut(BaseModel):
    label: str
    display: str
    confidence: float


class FindingOut(BaseModel):
    rule_id: str
    severity: FindingSeverity
    explanation: str


class ClauseOut(BaseModel):
    id: uuid.UUID
    ordinal: int
    heading: str | None
    text: str
    risk: RiskLevel
    predictions: list[PredictionOut]
    findings: list[FindingOut]
    needs_manual_review: bool
    segmentation_method: SegmentationMethod


class ContractSummary(BaseModel):
    """Row in the dashboard history list (REQ-6.3)."""

    id: uuid.UUID
    filename: str
    status: ContractStatus
    uploaded_at: datetime
    processed_at: datetime | None
    clause_count: int | None = None
    high_risk_count: int | None = None
    caution_count: int | None = None


class ReportResponse(BaseModel):
    contract_id: uuid.UUID
    filename: str
    uploaded_at: datetime
    generated_at: datetime
    rubric_version: str
    model_version: str
    summary: dict[str, Any]
    clauses: list[ClauseOut]
    disclaimer: str = DISCLAIMER


class ClauseTypeOut(BaseModel):
    key: str
    display: str
    description: str


class DashboardResponse(BaseModel):
    total_contracts: int
    total_clauses: int
    risk_totals: dict[str, int]
    # "contracts reviewed over time" (SRS 2.2), as (date, count) pairs.
    reviewed_over_time: list[dict[str, Any]]
    recent: list[ContractSummary]
