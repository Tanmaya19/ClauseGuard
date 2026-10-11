"""Rubric loading and validation (REQ-4.4, SRS 5.5).

The rubric is data, not code: it is loaded from YAML at startup, hashed, and
registered in the ``rubric_versions`` table. Validation happens at load time
and is strict — a rule naming an unknown clause type or an unknown detector is
a startup failure, not a rule that silently never fires.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.db.models import FindingSeverity
from app.services.classification.labels import LABEL_KEYS
from app.services.risk.detectors import PRIMITIVES

logger = logging.getLogger(__name__)

RUBRIC_DIR = Path(__file__).parent / "rubrics"

WILDCARD = "*"


class RubricError(Exception):
    """The rubric file is missing, malformed, or internally inconsistent."""


@dataclass(frozen=True, slots=True)
class Rule:
    id: str
    applies_to: frozenset[str]
    severity: FindingSeverity
    criterion: str
    explanation: str
    detect: tuple[tuple[str, object], ...]

    def matches_labels(self, labels: frozenset[str]) -> bool:
        return WILDCARD in self.applies_to or bool(self.applies_to & labels)


@dataclass(frozen=True, slots=True)
class ContractRule:
    """A rule about an entire clause type being absent from the contract."""

    id: str
    missing_clause_type: str
    severity: FindingSeverity
    criterion: str
    explanation: str


@dataclass(frozen=True, slots=True)
class Rubric:
    version: str
    sha256: str
    notes: str
    rules: tuple[Rule, ...]
    contract_rules: tuple[ContractRule, ...]

    @property
    def rule_count(self) -> int:
        return len(self.rules) + len(self.contract_rules)


def _normalise_text(value: object, field: str, rule_id: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RubricError(f"rule {rule_id!r}: {field} must be a non-empty string")
    return " ".join(value.split())


def _parse_severity(value: object, rule_id: str) -> FindingSeverity:
    try:
        return FindingSeverity(str(value))
    except ValueError as exc:
        allowed = [s.value for s in FindingSeverity]
        raise RubricError(f"rule {rule_id!r}: severity must be one of {allowed}") from exc


def _parse_rule(raw: dict) -> Rule:
    rule_id = raw.get("id")
    if not isinstance(rule_id, str) or not rule_id:
        raise RubricError(f"every rule needs a string id; got {raw!r}")

    applies_raw = raw.get("applies_to") or []
    if not isinstance(applies_raw, list) or not applies_raw:
        raise RubricError(f"rule {rule_id!r}: applies_to must be a non-empty list")

    applies_to = set()
    for label in applies_raw:
        if label == WILDCARD:
            applies_to.add(WILDCARD)
            continue
        if label not in LABEL_KEYS:
            # Fail loudly: a typo here would produce a rule that can never
            # fire, and a rule that never fires is invisible in testing.
            raise RubricError(
                f"rule {rule_id!r}: applies_to references unknown clause type {label!r}"
            )
        applies_to.add(label)

    detect_raw = raw.get("detect")
    if not isinstance(detect_raw, dict) or not detect_raw:
        raise RubricError(f"rule {rule_id!r}: detect must be a non-empty mapping")

    for primitive in detect_raw:
        if primitive not in PRIMITIVES:
            raise RubricError(
                f"rule {rule_id!r}: unknown detector {primitive!r}; "
                f"available: {sorted(PRIMITIVES)}"
            )

    return Rule(
        id=rule_id,
        applies_to=frozenset(applies_to),
        severity=_parse_severity(raw.get("severity"), rule_id),
        criterion=_normalise_text(raw.get("criterion"), "criterion", rule_id),
        explanation=_normalise_text(raw.get("explanation"), "explanation", rule_id),
        detect=tuple(sorted(detect_raw.items(), key=lambda kv: kv[0])),
    )


def _parse_contract_rule(raw: dict) -> ContractRule:
    rule_id = raw.get("id")
    if not isinstance(rule_id, str) or not rule_id:
        raise RubricError(f"every contract rule needs a string id; got {raw!r}")

    missing = raw.get("missing_clause_type")
    if missing not in LABEL_KEYS:
        raise RubricError(
            f"contract rule {rule_id!r}: missing_clause_type {missing!r} is not a clause type"
        )

    return ContractRule(
        id=rule_id,
        missing_clause_type=str(missing),
        severity=_parse_severity(raw.get("severity"), rule_id),
        criterion=_normalise_text(raw.get("criterion"), "criterion", rule_id),
        explanation=_normalise_text(raw.get("explanation"), "explanation", rule_id),
    )


def load_rubric(version: str | None = None) -> Rubric:
    """Load and validate a rubric by version string."""
    import yaml

    version = version or "1.0"
    path = RUBRIC_DIR / f"v{version}.yaml"
    if not path.is_file():
        available = sorted(p.stem for p in RUBRIC_DIR.glob("v*.yaml"))
        raise RubricError(f"no rubric for version {version!r}; available: {available}")

    raw_bytes = path.read_bytes()
    sha256 = hashlib.sha256(raw_bytes).hexdigest()

    try:
        data = yaml.safe_load(raw_bytes.decode("utf-8"))
    except yaml.YAMLError as exc:
        raise RubricError(f"{path.name} is not valid YAML: {exc}") from exc

    if not isinstance(data, dict):
        raise RubricError(f"{path.name} must contain a mapping at the top level")

    declared = str(data.get("version", ""))
    if declared != version:
        # A mismatch here means reports would be stamped with a version that
        # does not describe the rules that actually ran.
        raise RubricError(
            f"{path.name} declares version {declared!r} but was loaded as {version!r}"
        )

    rules = tuple(_parse_rule(r) for r in data.get("rules") or [])
    contract_rules = tuple(_parse_contract_rule(r) for r in data.get("contract_rules") or [])

    if not rules:
        raise RubricError(f"{path.name} defines no clause rules")

    ids = [r.id for r in rules] + [r.id for r in contract_rules]
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        raise RubricError(f"{path.name} has duplicate rule ids: {sorted(duplicates)}")

    rubric = Rubric(
        version=version,
        sha256=sha256,
        notes=" ".join(str(data.get("notes", "")).split()),
        rules=rules,
        contract_rules=contract_rules,
    )
    logger.info(
        "Loaded rubric v%s (%d rules, sha256 %s)",
        rubric.version,
        rubric.rule_count,
        rubric.sha256[:12],
    )
    return rubric


@lru_cache(maxsize=4)
def get_rubric(version: str | None = None) -> Rubric:
    """Cached loader. Parsing and validating on every request is wasteful."""
    return load_rubric(version)
