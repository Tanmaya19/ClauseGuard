#!/usr/bin/env python
"""Generate docs/RUBRIC.md from the rubric YAML.

SRS 5.5 requires risk-scoring criteria to be documented and auditable. Writing
that document by hand would let it drift from the rules that actually run, so
it is generated instead, and CI checks it is current.

    python backend/scripts/generate_rubric_docs.py          # write
    python backend/scripts/generate_rubric_docs.py --check   # fail if stale
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.services.classification.labels import display_name  # noqa: E402
from app.services.risk import get_rubric  # noqa: E402

OUTPUT = REPO_ROOT / "docs" / "RUBRIC.md"

SEVERITY_LABEL = {"high": "High-Risk", "caution": "Caution"}


def render() -> str:
    rubric = get_rubric()

    lines = [
        "# Risk rubric",
        "",
        "> **Generated file — do not edit.**",
        "> Produced from `backend/app/services/risk/rubrics/v"
        f"{rubric.version}.yaml` by",
        "> `backend/scripts/generate_rubric_docs.py`. Edit the YAML and re-run it.",
        "",
        f"**Version {rubric.version}** · SHA-256 `{rubric.sha256}`",
        "",
        "Every risk flag ClauseGuard raises comes from one of the rules below.",
        "There is no model score anywhere in risk assessment: a clause is flagged",
        "because a named, documented criterion matched its text (REQ-4.2), and the",
        "explanation shown to the user is the one recorded here (REQ-4.3).",
        "",
        "The rubric is data, not code — it can be extended without retraining",
        "anything (REQ-4.4). Each report records the rubric version that produced",
        "it, so a historical report stays explainable after the rubric changes",
        "(SRS 5.5).",
        "",
        "## How a clause gets its risk level",
        "",
        "| Outcome | When |",
        "|---|---|",
        "| **High-Risk** | At least one `high` severity rule fired |",
        "| **Caution** | At least one `caution` rule fired, and no `high` rule |",
        "| **Safe** | The clause was classified, and no rule fired |",
        "| **Not assessed** | The clause type could not be identified, or the rule layer errored |",
        "",
        "*Not assessed* is deliberate. Reporting an unjudged clause as safe would",
        "be a false reassurance, which SRS 5.2 treats as an informational-safety",
        "concern rather than a cosmetic one.",
        "",
        f"## Clause rules ({len(rubric.rules)})",
        "",
    ]

    by_severity = {"high": [], "caution": []}
    for rule in rubric.rules:
        by_severity[rule.severity.value].append(rule)

    for severity in ("high", "caution"):
        rules = by_severity[severity]
        if not rules:
            continue
        lines += [f"### {SEVERITY_LABEL[severity]} ({len(rules)})", ""]
        for rule in sorted(rules, key=lambda r: r.id):
            applies = ", ".join(
                "any clause type" if label == "*" else display_name(label)
                for label in sorted(rule.applies_to)
            )
            detectors = ", ".join(f"`{name}`" for name, _ in rule.detect)
            lines += [
                f"#### `{rule.id}`",
                "",
                f"**Applies to:** {applies}",
                "",
                f"**Criterion:** {rule.criterion}",
                "",
                f"**Detectors:** {detectors}",
                "",
                "**Shown to the user:**",
                "",
                f"> {rule.explanation}",
                "",
            ]

    if rubric.contract_rules:
        lines += [
            f"## Contract-level rules ({len(rubric.contract_rules)})",
            "",
            "These check for an entire clause type being *absent* from the",
            "contract. They have no clause to attach to, so they appear in the",
            "report summary rather than against an individual clause.",
            "",
        ]
        for rule in sorted(rubric.contract_rules, key=lambda r: r.id):
            lines += [
                f"#### `{rule.id}`",
                "",
                f"**Fires when the contract has no:** {display_name(rule.missing_clause_type)}",
                "",
                f"**Severity:** {SEVERITY_LABEL[rule.severity.value]}",
                "",
                f"**Criterion:** {rule.criterion}",
                "",
                "**Shown to the user:**",
                "",
                f"> {rule.explanation}",
                "",
            ]

    lines += [
        "## Statutory references",
        "",
        "Rules that cite Indian law, satisfying the SRS section 6 requirement that",
        "categories be reviewed for relevance to Indian commercial norms rather",
        "than inherited wholesale from US-centric CUAD:",
        "",
        "| Rule | Statute |",
        "|---|---|",
        "| `payment_term_over_45_days` | MSMED Act, 2006, s.15 — 45-day payment"
        " ceiling for registered micro and small enterprises |",
        "| `no_late_payment_interest` | MSMED Act, 2006 — statutory compound"
        " interest on delayed payment |",
        "| `post_term_noncompete` | Indian Contract Act, 1872, s.27 —"
        " agreements in restraint of trade |",
        "| `foreign_arbitration_seat` | Arbitration and Conciliation Act, 1996"
        " — India-seated arbitration |",
        "",
        "## Known limitations",
        "",
        "- **Asymmetry detection does not know which side you are.** The",
        "  `one_sided_obligation` and `one_sided_right` detectors flag a clause that",
        "  runs one way, in either direction. Until the upload flow captures whether",
        "  the user is the supplier or the customer, a clause that is one-sided *in",
        "  the user's favour* is flagged too.",
        "- **The rubric reads text, not intent.** A liability cap expressed in an",
        "  unusual form may be missed, and a clause that is fine in its commercial",
        "  context may still be flagged. This is why the output is triage and not",
        "  advice.",
        "- **Detection is English-only**, matching the V1.0 scope in SRS section 6.",
        "",
    ]

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Exit non-zero if the file is out of date."
    )
    args = parser.parse_args()

    rendered = render()

    if args.check:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.is_file() else ""
        if current != rendered:
            print(
                f"{OUTPUT.relative_to(REPO_ROOT)} is out of date — "
                "run backend/scripts/generate_rubric_docs.py",
                file=sys.stderr,
            )
            raise SystemExit(1)
        print(f"{OUTPUT.relative_to(REPO_ROOT)} is current")
        return

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
