# रिपॉजिटरी पथ: rti_backend/tests/test_web_pages.py
"""एक ही FastAPI सेवा से user और admin UI serve होने की जाँच."""

from app.main import app
from fastapi.testclient import TestClient


client = TestClient(app)


def test_user_interface_is_served() -> None:
    """यूजर UI का HTML response सफल होना चाहिए."""
    response = client.get("/app")

    assert response.status_code == 200
    assert "RTI साथी" in response.text
    assert 'id="language"' in response.text


def test_admin_interface_is_served_with_security_warning() -> None:
    """Admin UI अपनी अधूरी authentication स्थिति स्पष्ट करे."""
    response = client.get("/admin")

    assert response.status_code == 200
    assert "Admin Panel" in response.text
    assert "UI skeleton" in response.text


def test_frontend_assets_are_served() -> None:
    """CSS और JavaScript assets backend से उपलब्ध हों."""
    css = client.get("/assets/styles.css")
    script = client.get("/assets/app.js")

    assert css.status_code == 200
    assert "font-family" in css.text
    assert script.status_code == 200
    assert "translations" in script.text
