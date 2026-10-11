"""API tests: auth, upload, report, export, isolation.

These need a database, so they are marked ``db`` and skip without one.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from tests.fixtures import make_docx, make_image_only_pdf, make_legacy_doc, make_pdf

pytestmark = pytest.mark.db


@pytest.fixture
def account(client: TestClient, db_required: None) -> dict[str, str]:
    """A registered user, returned as an auth header."""
    email = f"user-{uuid.uuid4().hex[:10]}@example.com"
    response = client.post(
        "/api/v1/auth/register", json={"email": email, "password": "a-good-password-1"}
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def analysed(client: TestClient, account: dict[str, str]) -> str:
    """A contract uploaded and analysed to completion.

    TestClient runs BackgroundTasks synchronously, so analysis has finished by
    the time upload returns.
    """
    response = client.post(
        "/api/v1/contracts",
        headers=account,
        files={"file": ("supply.pdf", make_pdf(), "application/pdf")},
    )
    assert response.status_code == 202, response.text
    contract_id = response.json()["contract_id"]

    status = client.get(f"/api/v1/contracts/{contract_id}/status", headers=account).json()
    assert status["status"] == "complete", status
    return contract_id


# --- Auth (REQ-6.1) ------------------------------------------------------
def test_register_then_login(client: TestClient, db_required: None) -> None:
    email = f"user-{uuid.uuid4().hex[:10]}@example.com"

    assert client.post(
        "/api/v1/auth/register", json={"email": email, "password": "a-good-password-1"}
    ).status_code == 201

    login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "a-good-password-1"}
    )
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"


def test_duplicate_registration_is_rejected(client: TestClient, db_required: None) -> None:
    email = f"user-{uuid.uuid4().hex[:10]}@example.com"
    body = {"email": email, "password": "a-good-password-1"}

    assert client.post("/api/v1/auth/register", json=body).status_code == 201
    assert client.post("/api/v1/auth/register", json=body).status_code == 409


def test_email_is_matched_case_insensitively(client: TestClient, db_required: None) -> None:
    email = f"MixedCase-{uuid.uuid4().hex[:8]}@Example.com"
    client.post("/api/v1/auth/register", json={"email": email, "password": "pass-word-123"})

    assert client.post(
        "/api/v1/auth/login", json={"email": email.lower(), "password": "pass-word-123"}
    ).status_code == 200


def test_wrong_password_and_unknown_user_are_indistinguishable(
    client: TestClient, db_required: None
) -> None:
    """Different messages would let an attacker enumerate registered emails."""
    email = f"user-{uuid.uuid4().hex[:10]}@example.com"
    client.post("/api/v1/auth/register", json={"email": email, "password": "a-good-password-1"})

    wrong = client.post("/api/v1/auth/login", json={"email": email, "password": "nope-nope-1"})
    missing = client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "nope-nope-1"}
    )

    assert wrong.status_code == missing.status_code == 401
    assert wrong.json()["detail"] == missing.json()["detail"]


def test_short_password_is_rejected(client: TestClient, db_required: None) -> None:
    response = client.post(
        "/api/v1/auth/register", json={"email": "x@example.com", "password": "short"}
    )
    assert response.status_code == 422


def test_password_beyond_bcrypt_limit_is_rejected(
    client: TestClient, db_required: None
) -> None:
    """bcrypt truncates at 72 bytes; accepting more implies strength we do
    not actually get."""
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "y@example.com", "password": "a" * 80},
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "header",
    [None, {"Authorization": "Bearer not-a-token"}, {"Authorization": "Basic abc"}],
)
def test_protected_routes_require_a_valid_token(
    client: TestClient, db_required: None, header
) -> None:
    response = client.get("/api/v1/contracts", headers=header)
    assert response.status_code == 401


# --- Upload (REQ-1.1, REQ-1.2) ------------------------------------------
def test_upload_queues_analysis(client: TestClient, account: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/contracts",
        headers=account,
        files={"file": ("supply.docx", make_docx(), "application/octet-stream")},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["poll_url"].endswith("/status")


def test_oversize_upload_is_rejected_with_the_limit_in_the_message(
    client: TestClient, account: dict[str, str]
) -> None:
    """REQ-1.2. Checked against real bytes, not the Content-Length header."""
    oversized = b"%PDF-" + b"0" * (11 * 1024 * 1024)

    response = client.post(
        "/api/v1/contracts",
        headers=account,
        files={"file": ("big.pdf", oversized, "application/pdf")},
    )

    assert response.status_code == 413
    assert "10 MB" in response.json()["detail"]


def test_legacy_doc_is_rejected_synchronously(
    client: TestClient, account: dict[str, str]
) -> None:
    response = client.post(
        "/api/v1/contracts",
        headers=account,
        files={"file": ("old.doc", make_legacy_doc(), "application/msword")},
    )

    assert response.status_code == 415
    assert ".docx" in response.json()["detail"]


def test_empty_file_is_rejected(client: TestClient, account: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/contracts",
        headers=account,
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400


def test_scanned_pdf_fails_with_plain_language(
    client: TestClient, account: dict[str, str]
) -> None:
    """REQ-1.4: accepted, then reported as unreadable with usable guidance."""
    response = client.post(
        "/api/v1/contracts",
        headers=account,
        files={"file": ("scan.pdf", make_image_only_pdf(), "application/pdf")},
    )
    contract_id = response.json()["contract_id"]

    status = client.get(f"/api/v1/contracts/{contract_id}/status", headers=account).json()

    assert status["status"] == "failed"
    assert status["error_code"] == "no_extractable_text"
    assert "scan" in status["error_message"].lower()


# --- Report (REQ-5.1 to REQ-5.4) ----------------------------------------
def test_report_contains_clauses_types_risks_and_explanations(
    client: TestClient, account: dict[str, str], analysed: str
) -> None:
    body = client.get(f"/api/v1/reports/{analysed}", headers=account).json()

    assert body["summary"]["clause_count"] == len(body["clauses"])
    assert body["rubric_version"] == "1.0"
    assert body["disclaimer"]  # SRS 5.2

    high_risk = [c for c in body["clauses"] if c["risk"] == "high_risk"]
    assert high_risk, "fixture should produce high-risk clauses"

    for clause in high_risk:
        assert clause["findings"], "REQ-4.3: every flag needs an explanation"
        for finding in clause["findings"]:
            assert finding["explanation"]
            assert finding["rule_id"]  # REQ-4.2: traceable to a named rule


def test_report_summary_counts_match_the_clauses(
    client: TestClient, account: dict[str, str], analysed: str
) -> None:
    body = client.get(f"/api/v1/reports/{analysed}", headers=account).json()

    counted: dict[str, int] = {}
    for clause in body["clauses"]:
        counted[clause["risk"]] = counted.get(clause["risk"], 0) + 1

    stored = {k: v for k, v in body["summary"]["risk_counts"].items() if v}
    assert stored == counted


def test_predictions_carry_confidence_and_display_names(
    client: TestClient, account: dict[str, str], analysed: str
) -> None:
    """REQ-3.3, and SRS 5.2's requirement never to assert certainty."""
    body = client.get(f"/api/v1/reports/{analysed}", headers=account).json()

    typed = [c for c in body["clauses"] if c["predictions"]]
    assert typed
    for clause in typed:
        for prediction in clause["predictions"]:
            assert 0.0 <= prediction["confidence"] <= 1.0
            assert prediction["display"]


def test_report_is_unavailable_until_analysis_completes(
    client: TestClient, account: dict[str, str]
) -> None:
    response = client.post(
        "/api/v1/contracts",
        headers=account,
        files={"file": ("scan.pdf", make_image_only_pdf(), "application/pdf")},
    )
    contract_id = response.json()["contract_id"]

    assert client.get(f"/api/v1/reports/{contract_id}", headers=account).status_code == 409


def test_pdf_export(client: TestClient, account: dict[str, str], analysed: str) -> None:
    """REQ-5.3."""
    response = client.get(f"/api/v1/reports/{analysed}/pdf", headers=account)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")
    assert len(response.content) > 5000
    assert "attachment" in response.headers["content-disposition"]


def test_reanalysis_reuses_the_stored_file(
    client: TestClient, account: dict[str, str], analysed: str
) -> None:
    """REQ-4.4 and REQ-6.4: a rubric change must not require re-upload."""
    before = client.get(f"/api/v1/reports/{analysed}", headers=account).json()

    assert client.post(
        f"/api/v1/contracts/{analysed}/reanalyse", headers=account
    ).status_code == 200

    after = client.get(f"/api/v1/reports/{analysed}", headers=account).json()

    assert len(after["clauses"]) == len(before["clauses"])
    assert after["summary"]["risk_counts"] == before["summary"]["risk_counts"]


# --- History and dashboard (REQ-6.3) ------------------------------------
def test_history_lists_contracts_with_risk_summary(
    client: TestClient, account: dict[str, str], analysed: str
) -> None:
    rows = client.get("/api/v1/contracts", headers=account).json()

    row = next(r for r in rows if r["id"] == analysed)
    assert row["status"] == "complete"
    assert row["high_risk_count"] is not None
    assert row["clause_count"]


def test_dashboard_aggregates(
    client: TestClient, account: dict[str, str], analysed: str
) -> None:
    body = client.get("/api/v1/contracts/dashboard/overview", headers=account).json()

    assert body["total_contracts"] >= 1
    assert body["total_clauses"] >= 1
    assert body["reviewed_over_time"]


def test_clause_types_endpoint_returns_the_taxonomy(client: TestClient) -> None:
    body = client.get("/api/v1/clause-types").json()

    assert len(body) == 20  # SRS 2.5 permits 15-20
    assert all(t["key"] and t["display"] and t["description"] for t in body)


# --- Isolation (SRS 5.3) -------------------------------------------------
def test_another_account_cannot_reach_a_contract(
    client: TestClient, account: dict[str, str], analysed: str, db_required: None
) -> None:
    other = client.post(
        "/api/v1/auth/register",
        json={"email": f"other-{uuid.uuid4().hex[:8]}@example.com", "password": "other-pass-1"},
    ).json()
    headers = {"Authorization": f"Bearer {other['access_token']}"}

    # 404 not 403: confirming existence would itself leak information.
    assert client.get(f"/api/v1/reports/{analysed}", headers=headers).status_code == 404
    assert client.get(f"/api/v1/contracts/{analysed}/status", headers=headers).status_code == 404
    assert client.delete(f"/api/v1/contracts/{analysed}", headers=headers).status_code == 404
    assert client.get(f"/api/v1/reports/{analysed}/pdf", headers=headers).status_code == 404


def test_deletion_removes_the_contract_and_its_report(
    client: TestClient, account: dict[str, str], analysed: str
) -> None:
    """SRS 5.3: account-level deletion of uploaded contracts on request."""
    assert client.delete(f"/api/v1/contracts/{analysed}", headers=account).status_code == 204

    assert client.get(f"/api/v1/reports/{analysed}", headers=account).status_code == 404
    assert client.get(f"/api/v1/contracts/{analysed}/status", headers=account).status_code == 404


def test_history_is_scoped_to_the_account(
    client: TestClient, account: dict[str, str], analysed: str, db_required: None
) -> None:
    other = client.post(
        "/api/v1/auth/register",
        json={"email": f"other-{uuid.uuid4().hex[:8]}@example.com", "password": "other-pass-1"},
    ).json()
    headers = {"Authorization": f"Bearer {other['access_token']}"}

    assert client.get("/api/v1/contracts", headers=headers).json() == []
