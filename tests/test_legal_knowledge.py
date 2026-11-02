# Repository path: rti_backend/tests/test_legal_knowledge.py
"""Human-reviewed legal principle memory API tests."""

from fastapi.testclient import TestClient

from app.main import app
from app.api.routes import legal_knowledge

client = TestClient(app)


def _principle_payload():
    return {
        "document_id": "b0b1b2b3-b4b5-46b7-88b9-b0c1d2e3f456",
        "issue": "क्या निजी सूचना के प्रकटीकरण पर धारा 8(1)(j) लागू होती है?",
        "principle_type": "ratio_decidendi",
        "principle_text": "व्यक्तिगत सूचना के प्रकटीकरण पर वैधानिक अपवाद और व्यापक लोकहित का परीक्षण आवश्यक है।",
        "scope": "RTI Act के तहत व्यक्तिगत सूचना के अनुरोध",
        "conditions": ["सूचना व्यक्तिगत प्रकृति की हो"],
        "exceptions": ["बड़ा लोकहित प्रकटीकरण को उचित ठहरा सकता है"],
        "applicant_arguments_accepted": ["लोकहित का ठोस आधार"],
        "applicant_arguments_rejected": [],
        "pio_arguments_accepted": ["निजता पर वास्तविक प्रभाव"],
        "pio_arguments_rejected": [],
        "outcome": "काल्पनिक उदाहरण; वास्तविक आदेश से सत्यापन आवश्यक",
        "pinpoint_citations": [{"pinpoint": "पैरा 12", "supporting_note": "इस पैरा में वैधानिक कसौटी का सार है"}],
    }


def test_create_principle_requires_admin_and_keeps_it_pending(monkeypatch):
    monkeypatch.setattr(legal_knowledge, "require_admin", lambda *_args, **_kwargs: {"sub": "admin"})
    monkeypatch.setattr(
        legal_knowledge, "create_pending_principle",
        lambda payload: {"principle_id": "p-1", "legal_status": "pending_review", "source_url": "https://cic.gov.in/order"},
    )
    response = client.post("/api/v1/knowledge/principles", json=_principle_payload())
    assert response.status_code == 200
    assert response.json()["legal_status"] == "pending_review"
    assert "अभी उपयोगकर्ता उत्तरों में लागू नहीं" in response.json()["message"]


def test_review_requires_explicit_confirmation_and_note(monkeypatch):
    monkeypatch.setattr(legal_knowledge, "require_admin", lambda *_args, **_kwargs: {"sub": "reviewer"})
    response = client.post(
        "/api/v1/knowledge/principles/00000000-0000-4000-8000-000000000001/review",
        json={"legal_status": "verified_current", "reviewer_note": "यह छोटा नोट है", "confirm_reviewed": True},
    )
    assert response.status_code == 422


def test_review_requires_verified_later_decision_for_overruled_status():
    response = client.post(
        "/api/v1/knowledge/principles/00000000-0000-4000-8000-000000000001/review",
        json={
            "legal_status": "overruled",
            "reviewer_note": "बाद के निर्णय ने इस सिद्धांत को स्पष्ट रूप से पलट दिया है।",
            "confirm_reviewed": True,
        },
    )
    assert response.status_code == 422


def test_verified_principles_are_added_to_application_response(monkeypatch):
    from app.models.research import LegalApplicationRequest
    from app.services import research

    monkeypatch.setattr(research, "search_verified_documents", lambda *_args: [])
    monkeypatch.setattr(
        research, "search_verified_principles",
        lambda *_args: [{
            "principle_id": "p-verified", "document_id": "doc-1",
            "source_title": "CIC order", "source_url": "https://cic.gov.in/order",
            "authority": "CIC", "decision_date": None,
            "issue": "व्यक्तिगत सूचना", "principle_type": "ratio_decidendi",
            "principle_text": "प्रकटीकरण से पहले वैधानिक अपवाद की जाँच आवश्यक है।",
            "scope": None, "conditions": [], "exceptions": [],
            "applicant_arguments_accepted": [], "applicant_arguments_rejected": [],
            "pio_arguments_accepted": [], "pio_arguments_rejected": [],
            "outcome": None, "pinpoint_citations": [{"pinpoint": "पैरा 12", "supporting_note": "कसौटी"}],
            "legal_status": "verified_current", "subsequent_treatment": [],
        }],
    )
    response = research.apply_verified_legal_knowledge(
        LegalApplicationRequest(question="व्यक्तिगत सूचना के प्रकटीकरण का नियम क्या है?", role="neutral")
    )
    assert response.verified_principles[0].principle_id == "p-verified"
    assert response.verified_principles[0].legal_status == "verified_current"
    assert response.verified_principles[0].application_signal == "potentially_relevant_review_facts"
    assert "व्यक्तिगत" in response.verified_principles[0].matched_terms
    assert any("शर्तों और अपवादों" in item for item in response.verified_principles[0].application_trace)
