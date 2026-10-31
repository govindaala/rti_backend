# रिपॉजिटरी पथ: rti_backend/tests/test_legal_cases_api.py
"""कानूनी केस API के validation और source-domain परीक्षण."""

from fastapi.testclient import TestClient

from app.main import app
from app.services.source_registry import is_official_source_url

client = TestClient(app)


def case_payload() -> dict:
    """API परीक्षण के लिए न्यूनतम काल्पनिक केस payload."""
    return {
        "case_id": "API-TEST-001",
        "forum": "High Court",
        "case_title": "काल्पनिक परीक्षण निर्णय",
        "issues": [
            {
                "issue": "क्या रिकॉर्ड का प्रकटीकरण आवश्यक है?",
                "citation_ids": ["C1"],
            }
        ],
        "citations": [
            {
                "citation_id": "C1",
                "source_title": "सरकारी स्रोत का परीक्षण",
                "source_url": "https://cic.gov.in/example",
                "pinpoint": "पैरा 5",
                "summary": "काल्पनिक परीक्षण संदर्भ",
                "verified": False,
            }
        ],
    }


def test_validate_endpoint_returns_structured_result_without_saving() -> None:
    """API वैध रिकॉर्ड लौटाए और साफ बताए कि अभी save नहीं हुआ."""
    response = client.post("/api/v1/legal-cases/validate", json=case_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    assert body["stored"] is False
    assert body["case_id"] == "API-TEST-001"
    assert body["issue_count"] == 1
    assert body["citations"][0]["review_label"] == "official_domain_unverified_content"
    assert any("सत्यापित" in warning for warning in body["warnings"])


def test_validate_endpoint_rejects_missing_citation_reference() -> None:
    """किसी issue का citation रिकॉर्ड में न हो तो API 422 लौटाए."""
    payload = case_payload()
    payload["issues"][0]["citation_ids"] = ["NOT-FOUND"]

    response = client.post("/api/v1/legal-cases/validate", json=payload)

    assert response.status_code == 422


def test_official_domain_detection_rejects_lookalike_hosts() -> None:
    """सरकारी domain जैसा दिखने वाला बाहरी hostname स्वीकार न हो."""
    assert is_official_source_url("https://cic.gov.in/decision") is True
    assert is_official_source_url("https://records.cic.gov.in/decision") is True
    assert is_official_source_url("https://cic.gov.in.attacker.example/") is False
    assert is_official_source_url("https://fakegov.in/") is False
    assert is_official_source_url("https://example.com/") is False
    assert is_official_source_url("http://cic.gov.in/decision") is False
    assert is_official_source_url("javascript://cic.gov.in/") is False
