# Repository path: rti_backend/tests/test_legal_application.py
"""Verified legal knowledge application tests."""

from app.models.research import LegalApplicationRequest
from app.services import research


def test_application_uses_only_verified_search_and_returns_traceable_evidence(monkeypatch):
    captured = {}

    def fake_search(query: str, limit: int = 10):
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
    result = research.apply_verified_legal_knowledge(LegalApplicationRequest(
        question="क्या धारा 8(1)(j) व्यक्तिगत सूचना देने से रोकती है?",
        role="applicant",
        limit=5,
    ))

    assert captured["limit"] == 5
    assert " OR " in captured["query"]
    assert result.result_count == 1
    assert result.evidence[0].document_id == "verified-1"
    assert result.evidence[0].canonical_url.startswith("https://cic.gov.in/")
    assert "व्यक्तिगत" in result.evidence[0].matched_terms
    assert result.evidence[0].relevance_label in {
        "strong_keyword_overlap", "partial_keyword_overlap", "retrieved_for_review"
    }
    assert any("केवल मानव-सत्यापित" in item for item in result.limitations)
    assert any("आवेदक" in item for item in result.role_specific_checks)


def test_application_neutral_role_does_not_return_unverified_material(monkeypatch):
    def fake_search(_query: str, _limit: int = 10):
        # Repository contract supplies verified rows only; no crawler/pending rows.
        return []

    monkeypatch.setattr(research, "search_verified_documents", fake_search)
    result = research.apply_verified_legal_knowledge(LegalApplicationRequest(
        question="सूचना की प्रमाणित प्रति देने का नियम क्या है?",
        role="neutral",
    ))

    assert result.evidence == []
    assert result.result_count == 0
    assert result.role_specific_checks
