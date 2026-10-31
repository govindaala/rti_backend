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
