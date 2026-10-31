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


def test_admin_interface_shows_live_metrics_and_token_protected_source_form() -> None:
    """Admin dashboard public metrics दिखाए और source intake के लिए token माँगे."""
    response = client.get("/admin")
    assert response.status_code == 200
    assert "कानूनी शोध नियंत्रण कक्ष" in response.text
    assert 'id="source-form"' in response.text
    assert 'id="admin-token"' in response.text
    assert "स्रोत स्वीकृत करें" in response.text


def test_frontend_assets_are_served() -> None:
    """CSS और JavaScript assets backend से उपलब्ध हों."""
    css = client.get("/assets/styles.css")
    script = client.get("/assets/app.js")
    assert css.status_code == 200
    assert "font-family" in css.text
    assert script.status_code == 200
    assert "translations" in script.text
