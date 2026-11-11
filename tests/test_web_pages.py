# रिपॉजिटरी पथ: rti_backend/tests/test_web_pages.py
"""एक ही FastAPI सेवा से user और secure admin UI serve होने की जाँच."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_user_interface_is_served() -> None:
    """यूजर UI response सफल होना चाहिए."""
    response = client.get("/app")
    assert response.status_code == 200
    assert "RTI साथी" in response.text
    assert 'id="language"' in response.text


def test_admin_interface_shows_secure_login_and_protected_source_form() -> None:
    """Admin UI secure login दिखाए; dashboard और source form login से पहले छिपे हों."""
    response = client.get("/admin")
    assert response.status_code == 200
    assert "कानूनी शोध नियंत्रण कक्ष" in response.text
    assert 'id="login-form"' in response.text
    assert 'id="admin-id"' in response.text
    assert 'id="admin-pass"' in response.text
    assert 'id="admin-content" hidden' in response.text
    assert 'id="source-form"' in response.text
    assert 'id="login-panel" class="panel" hidden' in response.text
    assert "स्रोत स्वीकृत करें" in response.text
    # पुराना bearer-token form हट चुका है; अब signed session + CSRF इस्तेमाल होता है.
    assert 'id="admin-token"' not in response.text


def test_frontend_assets_are_served() -> None:
    """CSS और JavaScript assets backend से उपलब्ध हों."""
    css = client.get("/assets/styles.css")
    script = client.get("/assets/app.js")
    assert css.status_code == 200
    assert "font-family" in css.text
    assert script.status_code == 200
    assert "translations" in script.text


def test_admin_javascript_contains_human_document_review_action() -> None:
    """Admin UI में review_required दस्तावेज़ के लिए human review control हो."""
    response = client.get("/assets/admin.js")
    assert response.status_code == 200
    assert "समीक्षा के बाद Verify" in response.text
    assert "confirm_reviewed" in response.text


def test_applicant_workspace_renders_conclusion_first_legal_answer() -> None:
    """Applicant UI निष्कर्ष पहले दिखाए और candidate sources को verified से अलग रखे."""
    page = client.get("/app")
    script = client.get("/assets/app.js")

    assert page.status_code == 200
    assert 'id="analysis-result"' in page.text
    assert 'id="analysis-answer"' in page.text
    assert 'id="analysis-checklist"' not in page.text
    assert 'type="submit" data-i18n="submitQuestion"' in page.text
    assert 'type="submit" disabled' not in page.text
    assert script.status_code == 200
    assert "/api/v1/research/apply" in script.text
    assert "/api/v1/analysis/checklist" not in script.text
    assert "renderLegalAnswer" in script.text
    assert "result.direct_answer" in script.text
    assert "result.candidate_evidence" in script.text
    assert "result.verified_principles" in script.text
    assert "result.common_legal_checks" not in script.text
    assert "मशीन-निकाले स्रोत" in script.text


def test_applicant_checklist_api_returns_rule_based_checks() -> None:
    """User-facing checklist endpoint usable है और AI legal opinion का दावा नहीं करता."""
    response = client.post(
        "/api/v1/analysis/checklist",
        json={
            "role": "applicant",
            "facts": "PIO ने RTI आवेदन का जवाब नहीं दिया है और समय-सीमा बीत चुकी है।",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["role"] == "applicant"
    assert len(payload["checklist"]) == 5
    assert "AI model inference" in payload["notice"]
