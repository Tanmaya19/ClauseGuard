"""Risk scoring engine (REQ-4.1 to REQ-4.4).

Evaluates each clause against the rules whose ``applies_to`` matches the
clause's predicted types, then composes a risk level from the findings:

    any HIGH finding      -> HIGH_RISK
    any CAUTION finding   -> CAUTION
    no findings, typed    -> SAFE
    untyped or errored    -> UNASSESSABLE

``UNASSESSABLE`` is load-bearing, not a cop-out. SRS 5.4 requires the pipeline
to degrade gracefully: if the rule layer cannot judge a clause, the clause and
its predicted type are still shown, marked as not assessed, rather than failing
the whole report.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.db.models import FindingSeverity, RiskLevel
from app.services.classification.labels import UNCATEGORIZED
from app.services.risk.detectors import PRIMITIVES, RiskContext
from app.services.risk.loader import ContractRule, Rubric, Rule, get_rubric

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Finding:
    rule_id: str
    severity: FindingSeverity
    explanation: str
    criterion: str


@dataclass(frozen=True, slots=True)
class ClauseAssessment:
    level: RiskLevel
    findings: tuple[Finding, ...]


@dataclass(frozen=True, slots=True)
class ContractAssessment:
    clause_levels: tuple[RiskLevel, ...]
    clause_findings: tuple[tuple[Finding, ...], ...]
    contract_findings: tuple[Finding, ...]
    rubric_version: str

    @property
    def counts(self) -> dict[str, int]:
        tally = {level.value: 0 for level in RiskLevel}
        for level in self.clause_levels:
            tally[level.value] += 1
        return tally


def _evaluate_rule(rule: Rule, ctx: RiskContext) -> bool:
    """A rule fires when every primitive in its ``detect`` block is satisfied.

    The conjunction is deliberate: it is what lets a rule express "this clause
    talks about auto-renewal AND states no notice period", which is the shape
    almost every absence-based criterion takes.
    """
    for primitive_name, argument in rule.detect:
        predicate = PRIMITIVES[primitive_name]
        try:
            if not predicate(ctx, argument):  # type: ignore[arg-type]
                return False
        except Exception:
            # One malformed rule must not take down the clause, let alone the
            # report. Log it with the rule id so it is fixable, treat it as
            # not firing.
            logger.exception("Detector %s failed in rule %s", primitive_name, rule.id)
            return False
    return True


def assess_clause(
    text: str,
    labels: frozenset[str],
    *,
    contract_text: str = "",
    rubric: Rubric | None = None,
) -> ClauseAssessment:
    """Score one clause. Never raises — see SRS 5.4 Reliability."""
    rubric = rubric or get_rubric()

    # An unclassified clause cannot be judged: nearly every criterion depends
    # on knowing what kind of clause it is. Saying so is more honest than
    # applying liability rules to a notices clause.
    if not labels or labels == {UNCATEGORIZED}:
        return ClauseAssessment(level=RiskLevel.UNASSESSABLE, findings=())

    try:
        ctx = RiskContext(text=text, labels=labels, contract_text=contract_text)
        findings = tuple(
            Finding(
                rule_id=rule.id,
                severity=rule.severity,
                explanation=rule.explanation,
                criterion=rule.criterion,
            )
            for rule in rubric.rules
            if rule.matches_labels(labels) and _evaluate_rule(rule, ctx)
        )
    except Exception:
        logger.exception("Risk assessment failed for a clause; marking unassessable")
        return ClauseAssessment(level=RiskLevel.UNASSESSABLE, findings=())

    return ClauseAssessment(level=_compose(findings), findings=findings)


def _compose(findings: tuple[Finding, ...]) -> RiskLevel:
    if any(f.severity is FindingSeverity.HIGH for f in findings):
        return RiskLevel.HIGH_RISK
    if findings:
        return RiskLevel.CAUTION
    return RiskLevel.SAFE


def _evaluate_contract_rule(
    rule: ContractRule, present_labels: set[str]
) -> Finding | None:
    if rule.missing_clause_type in present_labels:
        return None
    return Finding(
        rule_id=rule.id,
        severity=rule.severity,
        explanation=rule.explanation,
        criterion=rule.criterion,
    )


def assess_contract(
    clauses: list[tuple[str, frozenset[str]]],
    *,
    contract_text: str = "",
    rubric_version: str | None = None,
) -> ContractAssessment:
    """Score every clause, then apply the contract-level absence checks.

    Contract-level findings have no clause to attach to, so they are returned
    separately and stored in ``Report.summary_json`` rather than
    ``risk_findings``.
    """
    rubric = get_rubric(rubric_version)

    levels: list[RiskLevel] = []
    per_clause: list[tuple[Finding, ...]] = []
    present: set[str] = set()

    for text, labels in clauses:
        assessment = assess_clause(
            text, labels, contract_text=contract_text, rubric=rubric
        )
        levels.append(assessment.level)
        per_clause.append(assessment.findings)
        present.update(labels)

    contract_findings = tuple(
        finding
        for rule in rubric.contract_rules
        if (finding := _evaluate_contract_rule(rule, present)) is not None
    )

    return ContractAssessment(
        clause_levels=tuple(levels),
        clause_findings=tuple(per_clause),
        contract_findings=contract_findings,
        rubric_version=rubric.version,
    )
