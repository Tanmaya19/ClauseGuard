"""Guards against the migration drifting from the ORM models.

The failure this prevents is a quiet one: you add a column to models.py,
forget the migration, and everything works locally because your development
database was created from metadata rather than from the migration chain.
Deployment then fails on a column that does not exist.

So: migrate a scratch database from zero, then compare it against
``Base.metadata`` table by table and column by column.
"""

import uuid

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.core.config import get_settings
from app.db import models  # noqa: F401  — registers the tables on Base.metadata
from app.db.base import Base

pytestmark = pytest.mark.db


@pytest.fixture(scope="module")
def migrated_database(db_required: None) -> str:
    """Create a throwaway database, run `alembic upgrade head` into it, drop it."""
    settings = get_settings()
    scratch_name = f"cg_test_{uuid.uuid4().hex[:12]}"

    admin = create_engine(settings.sqlalchemy_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{scratch_name}"'))

    scratch_url = settings.sqlalchemy_url.rsplit("/", 1)[0] + f"/{scratch_name}"

    config = Config("alembic.ini")
    config.set_main_option("script_location", "app/db/migrations")
    config.set_main_option("sqlalchemy.url", scratch_url)

    try:
        command.upgrade(config, "head")
        yield scratch_url
    finally:
        with admin.connect() as conn:
            conn.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :name"
                ),
                {"name": scratch_name},
            )
            conn.execute(text(f'DROP DATABASE IF EXISTS "{scratch_name}"'))
        admin.dispose()


def test_migration_creates_every_model_table(migrated_database: str) -> None:
    engine = create_engine(migrated_database)
    try:
        migrated_tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    expected = set(Base.metadata.tables)
    missing = expected - migrated_tables
    assert not missing, f"tables defined in models.py but absent from migrations: {sorted(missing)}"


def test_migration_creates_every_model_column(migrated_database: str) -> None:
    engine = create_engine(migrated_database)
    try:
        inspector = inspect(engine)
        drift: list[str] = []

        for table_name, table in Base.metadata.tables.items():
            migrated_columns = {c["name"] for c in inspector.get_columns(table_name)}
            for column in table.columns:
                if column.name not in migrated_columns:
                    drift.append(f"{table_name}.{column.name}")
    finally:
        engine.dispose()

    assert not drift, f"columns defined in models.py but absent from migrations: {sorted(drift)}"


def test_downgrade_to_base_removes_the_schema(migrated_database: str) -> None:
    """A migration that cannot be reversed is a migration you cannot test twice."""
    config = Config("alembic.ini")
    config.set_main_option("script_location", "app/db/migrations")
    config.set_main_option("sqlalchemy.url", migrated_database)

    command.downgrade(config, "base")

    engine = create_engine(migrated_database)
    try:
        remaining = set(inspect(engine).get_table_names()) - {"alembic_version"}
    finally:
        engine.dispose()

    assert not remaining, f"downgrade left tables behind: {sorted(remaining)}"

    command.upgrade(config, "head")  # restore for any later test in the module
