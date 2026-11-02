# रिपॉजिटरी पथ: rti_backend/tests/test_research.py
"""Verified legal research endpoint tests."""

from fastapi.testclient import TestClient

from app.main import app
from app.services import research

client = TestClient(app)


def test_research_returns_only_verified_corpus_results(monkeypatch) -> None:
    """Repository boundary पर returned rows verified corpus से ही आते हैं."""
    def fake_search(query: str, limit: int = 10) -> list[dict]:
        assert query == "सूचना"
        assert limit == 5
        return [
            {
                "document_id": "doc-1",
                "title": "सत्यापित आदेश",
                "canonical_url": "https://cic.gov.in/order/1",
                "authority": "CIC",
                "decision_date": None,
                "document_type": "order",
                "excerpt": "सूचना का अधिकार",
                "content_sha256": "a" * 64,
            }
        ]

    monkeypatch.setattr(research, "search_verified_documents", fake_search)
    response = client.post(
        "/api/v1/research/search",
        json={"query": "सूचना", "limit": 5},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["result_count"] == 1
    assert body["results"][0]["verification_status"] == "verified"
    assert body["results"][0]["canonical_url"] == "https://cic.gov.in/order/1"


def test_research_rejects_short_query() -> None:
    """बहुत छोटा search query स्वीकार न हो."""
    response = client.post("/api/v1/research/search", json={"query": "a"})
    assert response.status_code == 422


def test_legal_application_uses_verified_evidence_and_returns_traceable_sources(monkeypatch) -> None:
    captured = {}

    def fake_search(query: str, limit: int = 10) -> list[dict]:
        captured["query"] = query
        captured["limit"] = limit
        return [{
            "document_id": "verified-1",
            "title": "CIC सूचना आदेश",
            "canonical_url": "https://cic.gov.in/orders/verified-1",
            "authority": "CIC",
            "decision_date": None,
            "legal_issue": "व्यक्तिगत सूचना के प्रकटीकरण का प्रश्न",
            "holding": "धारा 8(1)(j) के तहत परीक्षण आवश्यक है",
            "cited_sections": ["धारा 8(1)(j)"],
            "content_sha256": "b" * 64,
            "verification_status": "verified",
        }]

    monkeypatch.setattr(research, "search_verified_documents", fake_search)
    response = client.post(
        "/api/v1/research/apply",
        json={
            "question": "क्या धारा 8(1)(j) व्यक्तिगत सूचना देने से रोकती है?",
            "role": "applicant",
            "limit": 5,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert captured["limit"] == 5
    assert " OR " in captured["query"]
    assert body["result_count"] == 1
    assert body["evidence"][0]["document_id"] == "verified-1"
    assert body["evidence"][0]["canonical_url"] == "https://cic.gov.in/orders/verified-1"
    assert "व्यक्तिगत" in body["evidence"][0]["matched_terms"]
    assert any("केवल मानव-सत्यापित" in item for item in body["limitations"])
    assert any("आवेदक" in item for item in body["role_specific_checks"])


def test_legal_application_neutral_role_returns_empty_when_verified_corpus_is_empty(monkeypatch) -> None:
    monkeypatch.setattr(research, "search_verified_documents", lambda _query, _limit=10: [])
    response = client.post(
        "/api/v1/research/apply",
        json={"question": "सूचना की प्रमाणित प्रति देने का नियम क्या है?", "role": "neutral"},
    )
    assert response.status_code == 200
    assert response.json()["evidence"] == []
    assert response.json()["result_count"] == 0
