# रिपॉजिटरी पथ: rti_backend/tests/test_web_pages.py
"""एक ही FastAPI सेवा से user और read-only admin UI serve होने की जाँच."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_user_interface_is_served() -> None:
    """यूजर UI response सफल होना चाहिए."""
    response = client.get("/app")
    assert response.status_code == 200
    assert "RTI साथी" in response.text
    assert 'id="language"' in response.text


def test_admin_interface_is_public_read_only_dashboard() -> None:
    """Admin dashboard बिना login दिखे और write access का दावा न करे."""
    response = client.get("/admin")
    assert response.status_code == 200
    assert "Operations Dashboard" in response.text
    assert "READ ONLY" in response.text
    assert "कोई पासवर्ड आवश्यक नहीं" in response.text


def test_frontend_assets_are_served() -> None:
    """CSS और JavaScript assets backend से उपलब्ध हों."""
    css = client.get("/assets/styles.css")
    script = client.get("/assets/app.js")
    assert css.status_code == 200
    assert "font-family" in css.text
    assert script.status_code == 200
    assert "translations" in script.text
