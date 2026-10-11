# ADR 0001 — Synchronous SQLAlchemy and UUID primary keys

**Status:** Accepted
**Date:** 2026-10-02
**Phase:** 0

## Context

SRS §3.3 describes FastAPI as an "asynchronous backend REST API framework",
which invites the assumption that the database layer should also be async
(`asyncpg` + `AsyncSession`). Separately, the schema in PLAN.md §3 needed a
primary-key strategy, and SRS §5.3 requires that uploaded contract content be
reachable only by the account that owns it.

## Decision

1. Use **synchronous** SQLAlchemy with `psycopg` (v3), and define route handlers
   with `def` rather than `async def` where they touch the database or the model.
2. Use **UUID** primary keys for every table rather than auto-incrementing
   integers.

## Rationale

### On synchronous database access

The dominant cost in this system is not database I/O — it is CPU-bound
transformer inference over up to 50 clauses (PLAN.md §7, TBD-3). A CPU-bound
call blocks the event loop whether or not the database driver is async, so async
SQLAlchemy would add real complexity (greenlet-based session handling, async
fixtures, two sets of idioms) while buying no throughput for this workload.

FastAPI runs a `def` handler in its threadpool, which is the correct place for
blocking work. The HTTP layer remains async; only the handler body is
synchronous. If a later phase introduces genuinely I/O-bound fan-out, the
decision can be revisited per router without a rewrite.

### On UUID keys

Sequential integer keys would make contract identifiers guessable. A logged-in
user who owns `/contracts/41` could probe `/contracts/42` and learn that
another account's contract exists, and any authorisation slip would expose it
outright. UUIDs remove the enumeration vector entirely, which matters here
because SRS §5.3 treats uploaded contracts as commercially sensitive.

The cost is 16 bytes per key instead of 4, and slightly worse index locality.
At the scale this system targets (TBD-4: five concurrent analyses) that cost is
irrelevant.

## Consequences

- Tests require a real PostgreSQL instance; SQLite cannot host `UUID`, `JSONB`
  or native enums. `tests/conftest.py` skips database tests when none is
  reachable, and CI sets `REQUIRE_DB=1` so the skip cannot hide a failure.
- Model inference in Phase 3 must stay inside threadpool-executed `def`
  handlers, or it will stall the event loop.
- Contract IDs are not human-readable, so log lines should carry the filename
  alongside the ID for debuggability.
