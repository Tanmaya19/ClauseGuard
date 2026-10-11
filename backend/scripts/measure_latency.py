#!/usr/bin/env python
"""Measure end-to-end pipeline latency against the TBD-3 budget (Phase 8).

SRS 5.1 states a processing-time requirement; PLAN.md section 7 resolved it to
p95 <= 30 s for a contract of up to 20 pages / 50 clauses. That figure was a
budget, not a measurement — this script turns it into one.

Each stage is timed separately, so if the budget is ever missed it is clear
which stage to attack rather than guessing.

    python backend/scripts/measure_latency.py
    python backend/scripts/measure_latency.py --clauses 50 --runs 7
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services.classification import get_classifier  # noqa: E402
from app.services.extraction import extract  # noqa: E402
from app.services.risk import assess_contract  # noqa: E402
from app.services.segmentation import segment  # noqa: E402
from tests.fixtures import RISKY_AGREEMENT, make_pdf  # noqa: E402

BUDGET_SECONDS = 30.0


def build_contract(target_clauses: int) -> bytes:
    """Repeat the fixture until it has roughly the target clause count."""
    clauses: list[tuple[str, str]] = []

    while len(clauses) < target_clauses:
        for heading, body in RISKY_AGREEMENT:
            title = heading.split(". ", 1)[-1]
            clauses.append((f"{len(clauses) + 1}. {title}", body))
            if len(clauses) >= target_clauses:
                break

    return make_pdf(clauses)


def measure(data: bytes, runs: int) -> dict:
    stages: dict[str, list[float]] = {
        "extract": [],
        "segment": [],
        "classify": [],
        "score": [],
        "total": [],
    }
    clause_count = 0
    classifier = get_classifier()

    for _ in range(runs):
        start_total = time.perf_counter()

        t = time.perf_counter()
        document = extract(data, "contract.pdf")
        stages["extract"].append(time.perf_counter() - t)

        t = time.perf_counter()
        segments = segment(document)
        stages["segment"].append(time.perf_counter() - t)
        clause_count = len(segments)

        t = time.perf_counter()
        predictions = classifier.classify([s.text for s in segments])
        stages["classify"].append(time.perf_counter() - t)

        t = time.perf_counter()
        labelled = [
            (s.text, frozenset(p.label for p in preds))
            for s, preds in zip(segments, predictions, strict=True)
        ]
        assess_contract(labelled, contract_text=document.text)
        stages["score"].append(time.perf_counter() - t)

        stages["total"].append(time.perf_counter() - start_total)

    def summarise(values: list[float]) -> dict:
        ordered = sorted(values)
        # With a handful of runs, the max is the honest stand-in for p95.
        return {"median": round(statistics.median(ordered), 3), "max": round(ordered[-1], 3)}

    return {
        "clauses": clause_count,
        "runs": runs,
        "model_version": classifier.model_version,
        "stages": {name: summarise(values) for name, values in stages.items()},
        "budget_seconds": BUDGET_SECONDS,
        "within_budget": max(stages["total"]) <= BUDGET_SECONDS,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clauses", type=int, default=50)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args()

    data = build_contract(args.clauses)
    print(f"Contract: {len(data) / 1024:.0f} KB PDF, targeting {args.clauses} clauses")

    results = measure(data, args.runs)

    print(f"Model: {results['model_version']}")
    print(f"Clauses segmented: {results['clauses']}")
    print(f"Runs: {results['runs']}")
    print()
    print(f"{'stage':<12} {'median':>9} {'max':>9}")
    print("-" * 32)
    for name, values in results["stages"].items():
        print(f"{name:<12} {values['median']:>8.3f}s {values['max']:>8.3f}s")
    print()

    total = results["stages"]["total"]
    verdict = "WITHIN BUDGET" if results["within_budget"] else "OVER BUDGET"
    print(f"TBD-3 budget: {BUDGET_SECONDS:.0f}s for ~50 clauses -> {verdict}")
    print(f"  worst observed total: {total['max']:.3f}s")

    if results["model_version"].startswith("baseline-"):
        print()
        print(
            "NOTE: measured with the keyword baseline, not a trained transformer.\n"
            "      Classification is the stage that grows once a checkpoint is in\n"
            "      place — budget roughly 6-10s for 50 clauses on 2 vCPU. Re-run\n"
            "      this after training before treating the result as verification\n"
            "      of SRS 5.1."
        )

    if args.json:
        args.json.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"\nWrote {args.json}")


if __name__ == "__main__":
    main()
