"""Settings parsing.

The CORS case is a regression test. pydantic-settings JSON-decodes complex
field types directly from the environment, so declaring cors_origins as
list[str] made the container crash on startup with a comma-separated
CORS_ORIGINS — a failure that only appeared under Docker, where the variable
is actually set.
"""

import pytest

from app.core.config import Settings


def test_cors_origins_splits_a_comma_separated_environment_value() -> None:
    settings = Settings(cors_origins="http://localhost:5173, http://localhost:3000")
    assert settings.cors_origin_list == ["http://localhost:5173", "http://localhost:3000"]


def test_cors_origins_tolerates_trailing_separators() -> None:
    settings = Settings(cors_origins="http://localhost:5173,,")
    assert settings.cors_origin_list == ["http://localhost:5173"]


def test_database_url_overrides_the_assembled_parts() -> None:
    explicit = "postgresql+psycopg://u:p@elsewhere:5432/other"
    assert Settings(database_url=explicit).sqlalchemy_url == explicit


def test_sqlalchemy_url_is_assembled_when_database_url_is_blank() -> None:
    settings = Settings(
        database_url=None,
        postgres_user="cg",
        postgres_password="pw",
        postgres_host="localhost",
        postgres_port=5433,
        postgres_db="clauseguard",
    )
    assert settings.sqlalchemy_url == "postgresql+psycopg://cg:pw@localhost:5433/clauseguard"


@pytest.mark.parametrize(("mb", "expected"), [(1, 1048576), (10, 10485760)])
def test_upload_cap_converts_to_bytes(mb: int, expected: int) -> None:
    """TBD-1 is stated in MB but enforced in bytes against Content-Length."""
    assert Settings(max_upload_mb=mb).max_upload_bytes == expected
