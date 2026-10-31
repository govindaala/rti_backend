# रिपॉजिटरी पथ: rti_backend/tests/test_admin_dashboard.py
"""Public dashboard और privileged source API की सुरक्षा जाँच."""

from dataclasses import replace

from fastapi.testclient import TestClient

from app.api.routes import admin as admin_routes
from app.main import app

client = TestClient(app)


def test_dashboard_is_public_and_returns_only_aggregate_counts(monkeypatch) -> None:
    monkeypatch.setattr(
        admin_routes,
        "settings",
        replace(admin_routes.settings, database_url=None),
    )
    response = client.get("/api/v1/admin/dashboard")
    assert response.status_code == 200
    assert response.json()["database"] == "not_configured"


def test_source_submission_requires_admin_token(monkeypatch) -> None:
    monkeypatch.setattr(
        admin_routes,
        "settings",
        replace(admin_routes.settings, admin_api_token="test-secret"),
    )
    response = client.post("/api/v1/admin/sources", json={"url": "https://cic.gov.in/"})
    assert response.status_code == 401


def test_source_submission_rejects_non_official_domain(monkeypatch) -> None:
    monkeypatch.setattr(
        admin_routes,
        "settings",
        replace(admin_routes.settings, admin_api_token="test-secret"),
    )
    response = client.post(
        "/api/v1/admin/sources",
        headers={"X-Admin-Token": "test-secret"},
        json={"url": "https://example.com/"},
    )
    assert response.status_code == 422


def test_document_verification_requires_admin_token(monkeypatch) -> None:
    """मानव verification endpoint privileged token के बिना उपलब्ध न हो."""
    monkeypatch.setattr(
        admin_routes,
        "settings",
        replace(admin_routes.settings, admin_api_token="test-secret"),
    )
    response = client.post(
        "/api/v1/admin/documents/00000000-0000-0000-0000-000000000001/verify",
        json={
            "review_note": "मूल आदेश और वर्तमान स्थिति की समीक्षा की गई है।",
            "confirm_reviewed": True,
        },
    )
    assert response.status_code == 401
