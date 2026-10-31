# रिपॉजिटरी पथ: rti_backend/tests/test_admin_dashboard.py
"""Public dashboard और privileged source API की सुरक्षा जाँच."""

from dataclasses import replace

from fastapi.testclient import TestClient

from app.api.routes import admin as admin_routes
from app.main import app

client = TestClient(app)


def test_dashboard_handles_unavailable_database(monkeypatch) -> None:
    monkeypatch.setattr(
        admin_routes,
        "settings",
        replace(admin_routes.settings, database_url="postgresql://invalid"),
    )
    monkeypatch.setattr(
        admin_routes,
        "get_connection",
        lambda: (_ for _ in ()).throw(RuntimeError("not configured")),
    )
    response = client.get("/api/v1/admin/dashboard")
    assert response.status_code == 200
    assert response.json()["database"] == "unavailable"


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
