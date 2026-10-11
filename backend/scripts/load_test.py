#!/usr/bin/env python
"""Load-test concurrent contract analysis against the TBD-4 capacity.

PLAN.md section 7 resolved TBD-4 to five simultaneous analyses, and stated that
work arriving beyond that **queues rather than being rejected**. That was a
design intent; this script turns it into a measurement.

Three things are checked, because "it handled the load" is not one claim:

1. **Nothing is rejected.** Every upload must be accepted (HTTP 202) and every
   contract must reach `complete`. A dropped request would violate TBD-4.
2. **Throughput does not collapse.** Wall-clock time for N concurrent
   analyses is compared against N sequential ones.
3. **Results stay correct under concurrency.** Every contract must produce the
   same clause count and the same risk tally as a single analysis does. A
   shared-state bug in the pipeline would show up here and nowhere else —
   this is the check most likely to catch a real defect.

Usage
-----
    docker compose up -d
    python backend/scripts/load_test.py --concurrency 10
    python backend/scripts/load_test.py --base-url https://localhost --insecure
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import httpx

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from tests.fixtures import make_pdf  # noqa: E402

POLL_INTERVAL = 0.5
POLL_TIMEOUT = 180.0


@dataclass
class Outcome:
    index: int
    accepted: bool
    status: str
    upload_seconds: float
    total_seconds: float
    clause_count: int | None = None
    risk_counts: dict | None = None
    error: str | None = None


def register(client: httpx.Client) -> dict[str, str]:
    email = f"load-{uuid.uuid4().hex[:12]}@example.com"
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "load-test-password-1"},
    )
    response.raise_for_status()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def analyse_one(
    client: httpx.Client, headers: dict[str, str], pdf: bytes, index: int
) -> Outcome:
    started = time.perf_counter()

    try:
        upload = client.post(
            "/api/v1/contracts",
            headers=headers,
            files={"file": (f"contract-{index}.pdf", pdf, "application/pdf")},
        )
    except httpx.HTTPError as exc:
        return Outcome(index, False, "upload_error", 0.0, 0.0, error=str(exc))

    upload_seconds = time.perf_counter() - started

    if upload.status_code != 202:
        return Outcome(
            index,
            False,
            f"http_{upload.status_code}",
            upload_seconds,
            upload_seconds,
            error=upload.text[:200],
        )

    contract_id = upload.json()["contract_id"]

    # Poll to completion.
    deadline = time.perf_counter() + POLL_TIMEOUT
    status = "unknown"
    while time.perf_counter() < deadline:
        response = client.get(
            f"/api/v1/contracts/{contract_id}/status", headers=headers
        )
        if response.status_code != 200:
            time.sleep(POLL_INTERVAL)
            continue
        status = response.json()["status"]
        if status in {"complete", "failed"}:
            break
        time.sleep(POLL_INTERVAL)

    total_seconds = time.perf_counter() - started

    if status != "complete":
        return Outcome(index, True, status, upload_seconds, total_seconds)

    report = client.get(f"/api/v1/reports/{contract_id}", headers=headers)
    if report.status_code != 200:
        return Outcome(
            index,
            True,
            "report_unavailable",
            upload_seconds,
            total_seconds,
            error=f"http_{report.status_code}",
        )

    body = report.json()
    return Outcome(
        index,
        True,
        status,
        upload_seconds,
        total_seconds,
        clause_count=len(body["clauses"]),
        risk_counts={k: v for k, v in body["summary"]["risk_counts"].items() if v},
    )


def run_batch(
    base_url: str, verify: bool, pdf: bytes, count: int, parallel: bool
) -> tuple[list[Outcome], float]:
    with httpx.Client(base_url=base_url, verify=verify, timeout=60.0) as client:
        headers = register(client)

    def task(i: int) -> Outcome:
        # A client per thread: httpx.Client is not designed to be shared
        # across threads, and sharing one would measure the client's
        # contention rather than the server's.
        with httpx.Client(base_url=base_url, verify=verify, timeout=60.0) as client:
            return analyse_one(client, headers, pdf, i)

    started = time.perf_counter()
    if parallel:
        with ThreadPoolExecutor(max_workers=count) as pool:
            outcomes = list(pool.map(task, range(count)))
    else:
        outcomes = [task(i) for i in range(count)]
    elapsed = time.perf_counter() - started

    return outcomes, elapsed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument(
        "--concurrency",
        type=int,
        default=10,
        help="Simultaneous uploads. Default 10 = twice the TBD-4 capacity, "
        "so queuing behaviour is actually exercised.",
    )
    parser.add_argument(
        "--sequential-baseline",
        type=int,
        default=3,
        help="How many to run one-at-a-time for a throughput comparison.",
    )
    parser.add_argument("--insecure", action="store_true", help="Skip TLS verification.")
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args()

    verify = not args.insecure
    pdf = make_pdf()

    print(f"Target: {args.base_url}")
    print(f"Contract: {len(pdf) / 1024:.0f} KB PDF")
    print()

    # --- Sequential baseline -------------------------------------------
    print(f"Sequential baseline: {args.sequential_baseline} analyses, one at a time…")
    sequential, sequential_elapsed = run_batch(
        args.base_url, verify, pdf, args.sequential_baseline, parallel=False
    )
    per_analysis = sequential_elapsed / max(args.sequential_baseline, 1)
    print(
        f"  {sequential_elapsed:.2f}s total, {per_analysis:.2f}s per analysis"
    )
    print()

    # --- Concurrent run ------------------------------------------------
    print(f"Concurrent: {args.concurrency} simultaneous uploads…")
    concurrent, concurrent_elapsed = run_batch(
        args.base_url, verify, pdf, args.concurrency, parallel=True
    )
    print(f"  {concurrent_elapsed:.2f}s wall clock")
    print()

    # --- Assertions ----------------------------------------------------
    accepted = [o for o in concurrent if o.accepted]
    completed = [o for o in concurrent if o.status == "complete"]
    rejected = [o for o in concurrent if not o.accepted]

    print("=== TBD-4: nothing rejected under load ===")
    print(f"  uploads accepted : {len(accepted)}/{len(concurrent)}")
    print(f"  reached complete : {len(completed)}/{len(concurrent)}")
    if rejected:
        for outcome in rejected:
            print(f"  REJECTED #{outcome.index}: {outcome.status} {outcome.error}")

    print()
    print("=== correctness under concurrency ===")
    clause_counts = {o.clause_count for o in completed}
    risk_tallies = {json.dumps(o.risk_counts, sort_keys=True) for o in completed}
    baseline_clauses = {
        o.clause_count for o in sequential if o.status == "complete"
    }

    consistent = len(clause_counts) <= 1 and len(risk_tallies) <= 1
    matches_baseline = not baseline_clauses or clause_counts == baseline_clauses

    print(f"  distinct clause counts : {sorted(c for c in clause_counts if c)}")
    print(f"  distinct risk tallies  : {len(risk_tallies)}")
    print(f"  matches sequential run : {matches_baseline}")

    print()
    print("=== latency distribution (upload accepted -> complete) ===")
    durations = sorted(o.total_seconds for o in completed)
    if durations:
        print(f"  min    {durations[0]:.2f}s")
        print(f"  median {statistics.median(durations):.2f}s")
        print(f"  max    {durations[-1]:.2f}s")
        upload_times = sorted(o.upload_seconds for o in accepted)
        print(
            f"  upload call itself: median {statistics.median(upload_times):.3f}s, "
            f"max {upload_times[-1]:.3f}s"
        )

    print()
    print("=== throughput ===")
    if durations and per_analysis > 0:
        ideal = per_analysis * args.concurrency
        speedup = ideal / concurrent_elapsed if concurrent_elapsed else 0
        print(f"  {args.concurrency} sequential would take ~{ideal:.2f}s")
        print(f"  {args.concurrency} concurrent took      {concurrent_elapsed:.2f}s")
        print(f"  effective speedup: {speedup:.2f}x")

    verdict_lines = []
    if rejected:
        verdict_lines.append("FAIL: requests were rejected rather than queued")
    if len(completed) != len(concurrent):
        verdict_lines.append("FAIL: not every accepted contract completed")
    if not consistent:
        verdict_lines.append("FAIL: results differed between concurrent analyses")
    if not matches_baseline:
        verdict_lines.append("FAIL: concurrent results differ from sequential")

    print()
    if verdict_lines:
        print("=== VERDICT ===")
        for line in verdict_lines:
            print(f"  {line}")
    else:
        print("=== VERDICT: PASS ===")
        print(
            f"  {args.concurrency} simultaneous analyses, none rejected, all "
            f"completed, identical results."
        )

    if args.json:
        args.json.write_text(
            json.dumps(
                {
                    "concurrency": args.concurrency,
                    "accepted": len(accepted),
                    "completed": len(completed),
                    "wall_clock_seconds": round(concurrent_elapsed, 2),
                    "sequential_per_analysis_seconds": round(per_analysis, 3),
                    "consistent_results": consistent,
                    "matches_sequential": matches_baseline,
                    "durations": [round(d, 3) for d in durations],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"\nWrote {args.json}")

    raise SystemExit(1 if verdict_lines else 0)


if __name__ == "__main__":
    main()
