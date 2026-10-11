"""ORM models for the ClauseGuard schema (PLAN.md section 3).

Design notes worth knowing before editing:

* UUID primary keys throughout. Sequential integers would let any logged-in
  user enumerate other accounts' contract IDs, which SRS 5.3 forbids.
* ``clause_predictions`` holds one row per (clause, label) pair rather than a
  label column on the clause, because REQ-3.2 requires multi-label output.
  Zero rows for a clause is the storage form of "Uncategorized" (REQ-3.4).
* ``rubric_version`` is denormalised onto findings, risk and reports. That
  duplication is deliberate: SRS 5.5 requires a historical report to stay
  explainable against the rubric version that produced it, even after the
  rubric changes.
* Risk lives in its own ``clause_risk`` table rather than a column on
  ``clauses`` so that the learned layer (clauses, predictions) and the rule
  layer (findings, risk) can be recomputed independently — the decoupling
  SRS 5.4 and section 6 call for.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


# --------------------------------------------------------------------------
# Enumerations
# --------------------------------------------------------------------------
class ContractStatus(str, enum.Enum):
    """Pipeline stages. The Processing Screen (SRS 3.1) polls this value, so
    the stage names are user-facing and must stay aligned with the UI copy."""

    UPLOADED = "uploaded"
    EXTRACTING = "extracting"
    SEGMENTING = "segmenting"
    CLASSIFYING = "classifying"
    SCORING = "scoring"
    COMPLETE = "complete"
    FAILED = "failed"


class SegmentationMethod(str, enum.Enum):
    """Which strategy produced a clause — recorded so segmentation quality can
    be audited per method (REQ-2.1, REQ-2.3)."""

    NUMBERING = "numbering"
    HEADING = "heading"
    PARAGRAPH = "paragraph"


class RiskLevel(str, enum.Enum):
    """REQ-4.1 three-tier scale, plus the graceful-degradation value that
    SRS 5.4 Reliability requires instead of failing a whole report."""

    SAFE = "safe"
    CAUTION = "caution"
    HIGH_RISK = "high_risk"
    UNASSESSABLE = "unassessable"


class FindingSeverity(str, enum.Enum):
    """Severity a single rubric rule can contribute. Rules never fire "safe" —
    safe is the absence of findings."""

    CAUTION = "caution"
    HIGH = "high"


# --------------------------------------------------------------------------
# Tables
# --------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    contracts: Mapped[list[Contract]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Contract(Base):
    """An uploaded document and the state of its analysis."""

    __tablename__ = "contracts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    mime: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)

    # REQ-1.5: the extracted text is kept so a report can be rebuilt without
    # re-parsing the original file.
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[ContractStatus] = mapped_column(
        Enum(
            ContractStatus,
            name="contract_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        default=ContractStatus.UPLOADED,
        nullable=False,
        index=True,
    )
    # Human-readable detail for the processing screen, e.g. "clause 12 of 48".
    status_detail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Stable machine code for failures, e.g. "no_extractable_text" (REQ-1.4).
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="contracts")
    clauses: Mapped[list[Clause]] = relationship(
        back_populates="contract", cascade="all, delete-orphan", order_by="Clause.ordinal"
    )
    report: Mapped[Report | None] = relationship(
        back_populates="contract", cascade="all, delete-orphan", uselist=False
    )

    # Names here are bare: the "ck_%(table_name)s_" prefix comes from the
    # naming convention in db/base.py, so prefixing again would double it.
    __table_args__ = (CheckConstraint("size_bytes > 0", name="size_positive"),)


class Clause(Base):
    """One segmented provision, holding its position in the source document."""

    __tablename__ = "clauses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contracts.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # REQ-2.2: original order is part of the data, not an accident of row order.
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    heading: Mapped[str | None] = mapped_column(String(512), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    # Offsets into Contract.raw_text, so the UI can highlight the source span.
    char_start: Mapped[int] = mapped_column(Integer, nullable=False)
    char_end: Mapped[int] = mapped_column(Integer, nullable=False)

    segmentation_method: Mapped[SegmentationMethod] = mapped_column(
        Enum(
            SegmentationMethod,
            name="segmentation_method",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    # REQ-2.4: surfaced for manual review rather than silently misclassified.
    needs_manual_review: Mapped[bool] = mapped_column(default=False, nullable=False)

    contract: Mapped[Contract] = relationship(back_populates="clauses")
    predictions: Mapped[list[ClausePrediction]] = relationship(
        back_populates="clause", cascade="all, delete-orphan"
    )
    findings: Mapped[list[RiskFinding]] = relationship(
        back_populates="clause", cascade="all, delete-orphan"
    )
    risk: Mapped[ClauseRisk | None] = relationship(
        back_populates="clause", cascade="all, delete-orphan", uselist=False
    )

    __table_args__ = (
        UniqueConstraint("contract_id", "ordinal", name="uq_clauses_contract_ordinal"),
        CheckConstraint("char_end >= char_start", name="span_ordered"),
    )


class ClausePrediction(Base):
    """One predicted clause type for one clause (REQ-3.1 to REQ-3.3)."""

    __tablename__ = "clause_predictions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clause_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clauses.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Taxonomy key from ml/ labels, e.g. "limitation_of_liability".
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    # Which trained artefact produced this, so results stay reproducible.
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)

    clause: Mapped[Clause] = relationship(back_populates="predictions")

    __table_args__ = (
        UniqueConstraint("clause_id", "label", "model_version", name="uq_prediction_unique_label"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_is_a_probability"),
    )


class RubricVersion(Base):
    """Registry of risk rubrics. The SHA-256 of the YAML makes an edit to a
    published rubric detectable rather than silent (SRS 5.5)."""

    __tablename__ = "rubric_versions"

    version: Mapped[str] = mapped_column(String(32), primary_key=True)
    yaml_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    activated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class RiskFinding(Base):
    """One rubric rule that fired on one clause, with the reason shown to the
    user. REQ-4.3 requires the explanation; REQ-4.2 requires the rule id."""

    __tablename__ = "risk_findings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clause_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clauses.id", ondelete="CASCADE"), index=True, nullable=False
    )

    rule_id: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[FindingSeverity] = mapped_column(
        Enum(
            FindingSeverity,
            name="finding_severity",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    rubric_version: Mapped[str] = mapped_column(
        ForeignKey("rubric_versions.version"), nullable=False
    )

    clause: Mapped[Clause] = relationship(back_populates="findings")

    __table_args__ = (
        UniqueConstraint("clause_id", "rule_id", "rubric_version", name="uq_finding_unique_rule"),
    )


class ClauseRisk(Base):
    """The composed risk level for a clause: the highest severity among its
    findings, or ``unassessable`` when the rule layer could not run."""

    __tablename__ = "clause_risk"

    clause_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clauses.id", ondelete="CASCADE"), primary_key=True
    )
    level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, name="risk_level", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        index=True,
    )
    rubric_version: Mapped[str] = mapped_column(
        ForeignKey("rubric_versions.version"), nullable=False
    )

    clause: Mapped[Clause] = relationship(back_populates="risk")


class Report(Base):
    """Generated summary for a contract (REQ-5.1, REQ-5.4).

    ``summary_json`` holds the precomputed counts the report header shows, so
    re-opening a past report (REQ-6.4) is a single row read rather than a
    re-aggregation over every clause.
    """

    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contracts.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    rubric_version: Mapped[str] = mapped_column(
        ForeignKey("rubric_versions.version"), nullable=False
    )
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    summary_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    contract: Mapped[Contract] = relationship(back_populates="report")
