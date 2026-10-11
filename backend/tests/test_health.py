"""Smoke tests for the health endpoint — the Phase 0 baseline.

If these fail, nothing else in the system is worth debugging yet.
"""

from fastapi.testclient import TestClient


def test_root_advertises_entry_points(client: TestClient) -> None:
    body = client.get("/").json()
    assert body["service"] == "ClauseGuard"
    assert body["health"] == "/api/v1/health"


def test_openapi_schema_builds(client: TestClient) -> None:
    """Catches malformed response models and duplicate route definitions,
    neither of which surface until the schema is generated."""
    schema = client.get("/openapi.json")
    assert schema.status_code == 200
    assert "/api/v1/health" in schema.json()["paths"]


def test_health_reports_ok_when_database_is_up(client: TestClient, db_required: None) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] is True
    # Proves the deployed instance reports what it is serving (SRS 5.5).
    assert body["rubric_version"]
    assert body["model_version"]


def test_health_degrades_rather_than_crashes_without_a_database(client: TestClient) -> None:
    """SRS 5.4 Reliability: a dependency failure must be reported, not raised.

    The dependency is overridden with a session whose queries fail, so this
    runs identically with or without a real database present.
    """
    from sqlalchemy.exc import OperationalError

    from app.db.session import get_db

    class BrokenSession:
        def execute(self, *_args: object, **_kwargs: object) -> None:
            raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    app = client.app
    app.dependency_overrides[get_db] = lambda: BrokenSession()
    try:
        response = client.get("/api/v1/health")
        assert response.status_code == 503
        assert response.json()["status"] == "degraded"
        assert response.json()["database"] is False
    finally:
        app.dependency_overrides.clear()
