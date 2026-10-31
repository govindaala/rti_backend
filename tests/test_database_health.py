# रिपॉजिटरी पथ: rti_backend/tests/test_database_health.py
"""Tests for safe PostgreSQL readiness reporting."""

from fastapi.testclient import TestClient

from app.api.routes import database as database_routes
from app.main import app

client = TestClient(app)


def test_database_health_reports_connected(monkeypatch) -> None:
    monkeypatch.setattr(
        database_routes,
        "database_health",
        lambda: {"status": "connected", "database": "postgresql"},
    )

    response = client.get("/api/v1/health/database")

    assert response.status_code == 200
    assert response.json() == {"status": "connected", "database": "postgresql"}


def test_database_health_does_not_expose_connection_details(monkeypatch) -> None:
    monkeypatch.setattr(
        database_routes,
        "database_health",
        lambda: {"status": "unavailable", "database": "postgresql"},
    )

    response = client.get("/api/v1/health/database")

    assert response.status_code == 200
    assert "password" not in response.text.lower()
    assert "supabase.co" not in response.text.lower()
