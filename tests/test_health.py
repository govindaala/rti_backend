# रिपॉजिटरी पथ: rti_backend/tests/test_health.py
"""मुख्य API endpoints के शुरुआती परीक्षण."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint_returns_api_information() -> None:
    """मूल endpoint API की पहचान लौटाए."""
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["message"] == "RTI Intelligence Platform Backend"


def test_health_endpoint_returns_ok() -> None:
    """हेल्थ endpoint सेवा की स्थिति ok बताए."""
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "service" in response.json()
