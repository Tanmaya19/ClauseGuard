"""Risk rubric tests (REQ-4.1 to REQ-4.4, SRS 5.4, 5.5).

Several of these are regression tests for defects found while building the
rubric; each says which, because the failure modes are subtle and a future
edit could easily reintroduce them.
"""

from __future__ import annotations

import pytest

from app.db.models import FindingSeverity, RiskLevel
from app.services.classification import LABEL_KEYS, UNCATEGORIZED, get_classifier
from app.services.extraction import extract
from app.services.risk import RubricError, assess_clause, assess_contract, get_rubric
from app.services.risk.detectors import (
    PRIMITIVES,
    RiskContext,
    foreign_jurisdiction,
    notice_period_absent,
    notice_period_gt,
    numeric_days_gt,
    one_sided_obligation,
    one_sided_right,
    unbounded_duration,
)
from app.services.risk.loader import load_rubric
from app.services.segmentation import segment
from tests.fixtures import EXPECTED_CONTRACT_RISKS, EXPECTED_RISKS, make_pdf


# --- Rubric integrity ----------------------------------------------------
def test_rubric_loads_and_is_hashed() -> None:
    rubric = get_rubric()

    assert rubric.version == "1.0"
    assert len(rubric.sha256) == 64  # SRS 5.5: edits must be detectable
    assert rubric.rule_count >= 20


def test_every_rule_documents_a_criterion_and_an_explanation() -> None:
    """REQ-4.2 forbids an unexplained score; REQ-4.3 requires plain language."""
    for rule in get_rubric().rules:
        assert rule.criterion, f"{rule.id} has no criterion"
        assert len(rule.explanation) > 80, f"{rule.id} explanation is too terse"


def test_explanations_avoid_legal_jargon() -> None:
    """SRS 5.4 Usability: the audience has no legal training."""
    banned = [
        "inter alia", "mutatis mutandis", "prima facie", "ipso facto",
        "pari passu", "ab initio", "ultra vires",
    ]
    for rule in get_rubric().rules:
        lowered = rule.explanation.lower()
        for phrase in banned:
            assert phrase not in lowered, f"{rule.id} uses {phrase!r}"


def test_rules_only_reference_known_clause_types() -> None:
    for rule in get_rubric().rules:
        for label in rule.applies_to:
            assert label == "*" or label in LABEL_KEYS, f"{rule.id}: {label}"


def test_rules_only_reference_known_detectors() -> None:
    for rule in get_rubric().rules:
        for primitive, _ in rule.detect:
            assert primitive in PRIMITIVES, f"{rule.id}: {primitive}"


def test_unknown_clause_type_is_a_load_error(tmp_path) -> None:
    """A typo must fail loudly: a rule that can never fire is invisible."""
    import app.services.risk.loader as loader_module

    bad = tmp_path / "v9.9.yaml"
    bad.write_text(
        'version: "9.9"\nrules:\n'
        "  - id: broken\n    applies_to: [not_a_real_type]\n"
        "    severity: high\n    criterion: x\n    explanation: y\n"
        "    detect:\n      present_any: [foo]\n",
        encoding="utf-8",
    )

    original = loader_module.RUBRIC_DIR
    loader_module.RUBRIC_DIR = tmp_path
    try:
        with pytest.raises(RubricError, match="unknown clause type"):
            load_rubric("9.9")
    finally:
        loader_module.RUBRIC_DIR = original


def test_unknown_detector_is_a_load_error(tmp_path) -> None:
    import app.services.risk.loader as loader_module

    bad = tmp_path / "v9.8.yaml"
    bad.write_text(
        'version: "9.8"\nrules:\n'
        "  - id: broken\n    applies_to: [indemnity]\n"
        "    severity: high\n    criterion: x\n    explanation: y\n"
        "    detect:\n      no_such_detector: true\n",
        encoding="utf-8",
    )

    original = loader_module.RUBRIC_DIR
    loader_module.RUBRIC_DIR = tmp_path
    try:
        with pytest.raises(RubricError, match="unknown detector"):
            load_rubric("9.8")
    finally:
        loader_module.RUBRIC_DIR = original


# --- Detector primitives -------------------------------------------------
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("payable within 45 days of invoice", False),
        ("payable within 60 days of invoice", True),
        # Regression: the figure follows the word, in brackets. The original
        # regex expected digits first and missed this entirely.
        ("payable within ninety (90) days", True),
        ("payable within thirty (30) days", False),
        # Spelled out with no digits at all.
        ("a period of twenty-four months", True),
        ("Net 30", False),
        ("Net 90", True),
        # Regression: a four-digit year is not a duration.
        ("under the Indian Contract Act, 1872", False),
    ],
)
def test_day_counting_handles_how_contracts_actually_write_periods(
    text: str, expected: bool
) -> None:
    assert numeric_days_gt(RiskContext(text=text), 45) is expected


@pytest.mark.parametrize(
    ("text", "absent"),
    [
        ("terminable on 30 days' prior written notice", False),
        ("upon notice period of ninety (90) days", False),
        ("may terminate at any time without assigning any reason", True),
        # Regression: the figure here is the renewal TERM, in a different
        # sentence from the notice requirement. A loose proximity window read
        # it as a 360-day notice period and suppressed the correct finding.
        (
            "shall renew for successive periods of twelve months at the end of the "
            "initial term. The Agreement shall be deemed renewed unless written "
            "notice is given.",
            True,
        ),
    ],
)
def test_notice_period_detection_is_anchored_to_notice_language(
    text: str, absent: bool
) -> None:
    assert notice_period_absent(RiskContext(text=text)) is absent


def test_notice_period_threshold() -> None:
    assert notice_period_gt(RiskContext(text="on 120 days' notice"), 90)
    assert not notice_period_gt(RiskContext(text="on 30 days' notice"), 90)


def test_one_sided_obligation_detects_asymmetry() -> None:
    one_way = "The Supplier shall indemnify the Customer against all claims."
    mutual = "Each party shall indemnify the other against all claims."

    assert one_sided_obligation(RiskContext(text=one_way))
    assert not one_sided_obligation(RiskContext(text=mutual))


def test_one_sided_right_detects_permissions_not_duties() -> None:
    """Regression: a termination right reads "the Customer **may** terminate".
    Matching only obligation verbs (shall/must) missed it completely."""
    text = "The Customer may terminate this Agreement at any time without cause."

    assert one_sided_right(RiskContext(text=text))
    assert not one_sided_obligation(RiskContext(text=text))


def test_mutual_language_suppresses_asymmetry_flags() -> None:
    text = "Either party may terminate this Agreement on 30 days' notice."
    assert not one_sided_right(RiskContext(text=text))


def test_foreign_jurisdiction() -> None:
    assert foreign_jurisdiction(RiskContext(text="the courts at Singapore"))
    assert not foreign_jurisdiction(RiskContext(text="the courts at Mumbai, India"))
    # A clause naming both is not unambiguously foreign.
    assert not foreign_jurisdiction(
        RiskContext(text="arbitration in London or Mumbai, India")
    )


def test_unbounded_duration() -> None:
    assert unbounded_duration(RiskContext(text="shall continue in perpetuity"))
    assert not unbounded_duration(RiskContext(text="shall continue for three years"))


# --- Composition ---------------------------------------------------------
def test_high_severity_dominates_composition() -> None:
    """REQ-4.1: one serious problem makes the clause serious."""
    assessment = assess_clause(
        "The Supplier shall be liable for all direct and indirect losses.",
        frozenset({"limitation_of_liability"}),
    )

    assert assessment.level is RiskLevel.HIGH_RISK
    assert any(f.severity is FindingSeverity.HIGH for f in assessment.findings)


def test_clause_with_no_findings_is_safe() -> None:
    assessment = assess_clause(
        "Any notice under this Agreement shall be in writing and sent by "
        "registered post to the address set out above.",
        frozenset({"notices_misc"}),
    )

    assert assessment.level is RiskLevel.SAFE
    assert assessment.findings == ()


def test_unclassified_clause_is_unassessable_not_safe() -> None:
    """SRS 5.2: reporting an unjudged clause as safe is a false reassurance."""
    assert assess_clause("Some text.", frozenset()).level is RiskLevel.UNASSESSABLE
    assert (
        assess_clause("Some text.", frozenset({UNCATEGORIZED})).level
        is RiskLevel.UNASSESSABLE
    )


def test_a_failing_detector_does_not_fail_the_report(monkeypatch) -> None:
    """SRS 5.4 Reliability: degrade gracefully, never take down the report."""
    def explode(ctx, arg):  # noqa: ANN001, ANN202
        raise RuntimeError("detector is broken")

    monkeypatch.setitem(PRIMITIVES, "absent_any", explode)

    assessment = assess_clause(
        "The Supplier shall be liable for all losses.",
        frozenset({"limitation_of_liability"}),
    )

    # uncapped_liability uses absent_any and cannot fire, but the clause is
    # still assessed rather than raising.
    assert assessment.level in {RiskLevel.SAFE, RiskLevel.CAUTION, RiskLevel.HIGH_RISK}
    assert "uncapped_liability" not in {f.rule_id for f in assessment.findings}


# --- End to end against the fixture -------------------------------------
def test_fixture_contract_triggers_every_expected_rule() -> None:
    document = extract(make_pdf(), "c.pdf")
    segments = segment(document)
    predictions = get_classifier().classify([s.text for s in segments])
    labelled = [
        (s.text, frozenset(p.label for p in preds))
        for s, preds in zip(segments, predictions, strict=True)
    ]

    assessment = assess_contract(labelled, contract_text=document.text)

    fired: dict[str, set[str]] = {}
    for segment_, findings in zip(segments, assessment.clause_findings, strict=True):
        fired[segment_.heading or ""] = {f.rule_id for f in findings}

    for heading, expected in EXPECTED_RISKS.items():
        number = heading.split(".")[0]
        actual = next(
            (v for k, v in fired.items() if k.startswith(f"{number} ")), set()
        )
        assert expected <= actual, f"{heading}: missing {sorted(expected - actual)}"

    contract_rules = {f.rule_id for f in assessment.contract_findings}
    assert EXPECTED_CONTRACT_RISKS <= contract_rules


def test_no_exclusivity_false_positive_on_tax_or_forum_language() -> None:
    """Regression: the cue "exclusive" matched "exclusive of GST" and
    "exclusive jurisdiction", flagging two unrelated clauses as exclusivity."""
    classifier = get_classifier()

    for text in (
        "All prices are exclusive of GST, which shall be charged at the applicable rate.",
        "The courts at Mumbai shall have exclusive jurisdiction over any dispute.",
    ):
        labels = {p.label for p in classifier.classify([text])[0]}
        assert "exclusivity_noncompete" not in labels, text


def test_msmed_rule_cites_the_statute() -> None:
    """SRS 6 requires Indian relevance; the citation is the evidence of it."""
    rule = next(r for r in get_rubric().rules if r.id == "payment_term_over_45_days")

    assert "MSMED" in rule.criterion
    assert "45" in rule.explanation
