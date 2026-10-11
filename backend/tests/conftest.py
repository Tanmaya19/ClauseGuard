"""Shared test fixtures.

PostgreSQL-specific column types (UUID, JSONB) and native enums mean these
tests cannot run on SQLite. Rather than distort the schema to suit a test
backend, database tests are skipped when no server is reachable — so ``pytest``
still passes on a bare checkout.

To stop CI from going green on skipped tests, set ``REQUIRE_DB=1``; the skip
then becomes a failure.
"""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.main import app


def _database_reachable() -> bool:
    try:
        probe = create_engine(get_settings().sqlalchemy_url, pool_pre_ping=True)
        with probe.connect() as conn:
            conn.execute(text("SELECT 1"))
        probe.dispose()
        return True
    except SQLAlchemyError:
        return False


DB_AVAILABLE = _database_reachable()
REQUIRE_DB = os.getenv("REQUIRE_DB") == "1"


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="session")
def db_required() -> None:
    """Depend on this from any test that needs a live database."""
    if not DB_AVAILABLE:
        if REQUIRE_DB:
            pytest.fail(
                "REQUIRE_DB=1 but no database is reachable at "
                f"{get_settings().sqlalchemy_url.rsplit('@', 1)[-1]}"
            )
        pytest.skip("no PostgreSQL reachable; start it with `docker compose up -d db`")
