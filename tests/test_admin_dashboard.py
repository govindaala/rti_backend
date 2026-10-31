# रिपॉजिटरी पथ: rti_backend/tests/test_admin_dashboard.py
"""Admin login/session, dashboard authorization, and privileged API security tests."""

from dataclasses import replace

from fastapi.testclient import TestClient

from app.api.routes import admin as admin_routes
from app.main import app

client = TestClient(app, base_url="https://testserver")


def configured_admin(monkeypatch):
    client.cookies.clear()
    monkeypatch.setattr(
        admin_routes,
        "settings",
        replace(
            admin_routes.settings,
            admin_id="root",
            admin_pass="test-password",
            admin_session_secret="x" * 48,
            database_url=None,
        ),
    )


def test_admin_dashboard_requires_login() -> None:
    response = client.get("/api/v1/admin/dashboard")
    assert response.status_code == 401


def test_admin_login_creates_http_only_secure_session(monkeypatch) -> None:
    configured_admin(monkeypatch)
    response = client.post(
        "/api/v1/admin/auth/login",
        json={"admin_id": "root", "admin_pass": "test-password"},
    )
    assert response.status_code == 200
    cookie = response.cookies.get("rti_admin_session")
    assert cookie
    assert "httponly" in response.headers["set-cookie"].lower()
    assert "secure" in response.headers["set-cookie"].lower()
    assert response.json()["csrf_token"]


def test_wrong_admin_credentials_are_rejected(monkeypatch) -> None:
    configured_admin(monkeypatch)
    response = client.post(
        "/api/v1/admin/auth/login",
        json={"admin_id": "root", "admin_pass": "wrong"},
    )
    assert response.status_code == 401


def test_authenticated_dashboard_works_without_database(monkeypatch) -> None:
    configured_admin(monkeypatch)
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"admin_id": "root", "admin_pass": "test-password"},
    )
    response = client.get("/api/v1/admin/dashboard")
    assert login.status_code == 200
    assert response.status_code == 200
    assert response.json()["database"] == "not_configured"


def test_source_submission_requires_session_and_csrf(monkeypatch) -> None:
    configured_admin(monkeypatch)
    response = client.post("/api/v1/admin/sources", json={"url": "https://cic.gov.in/"})
    assert response.status_code == 401


def test_source_submission_rejects_non_official_domain_after_login(monkeypatch) -> None:
    configured_admin(monkeypatch)
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"admin_id": "root", "admin_pass": "test-password"},
    )
    response = client.post(
        "/api/v1/admin/sources",
        headers={"X-CSRF-Token": login.json()["csrf_token"]},
        json={"url": "https://example.com/"},
    )
    assert response.status_code == 422


def test_document_verification_requires_authenticated_session(monkeypatch) -> None:
    configured_admin(monkeypatch)
    response = client.post(
        "/api/v1/admin/documents/00000000-0000-0000-0000-000000000001/verify",
        json={
            "review_note": "मूल आदेश और वर्तमान स्थिति की समीक्षा की गई है।",
            "confirm_reviewed": True,
        },
    )
    assert response.status_code == 401
