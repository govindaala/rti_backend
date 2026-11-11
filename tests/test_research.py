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
    monkeypatch.setattr(research, "search_candidate_documents", lambda *_args: [])
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
            "decision_candidates": [
                {
                    "kind": "applicant_argument_candidate",
                    "label": "applicant argument candidate",
                    "excerpt": "The appellant submitted that the record was not supplied.",
                    "source_url": "https://cic.gov.in/orders/verified-1",
                    "paragraph_reference": "पैरा 7",
                    "review_status": "human_review_required",
                },
                {
                    "kind": "pio_argument_candidate",
                    "label": "PIO argument candidate",
                    "excerpt": "The CPIO submitted that the record was not available.",
                    "source_url": "https://cic.gov.in/orders/verified-1",
                    "paragraph_reference": "पैरा 8",
                    "review_status": "human_review_required",
                },
                {
                    "kind": "outcome_candidate",
                    "label": "outcome candidate",
                    "excerpt": "Accordingly, the appeal is dismissed.",
                    "source_url": "https://cic.gov.in/orders/verified-1",
                    "review_status": "human_review_required",
                },
            ],
            "verification_status": "verified",
        }]

    monkeypatch.setattr(research, "search_verified_documents", fake_search)
    monkeypatch.setattr(research, "search_candidate_documents", lambda *_args: [])
    monkeypatch.setattr(research, "search_verified_principles", lambda *_args: [])
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
    assert len(body["evidence"][0]["decision_candidates"]) == 3
    assert body["candidate_case_positions"][0]["source_url"] == "https://cic.gov.in/orders/verified-1"
    assert body["candidate_case_positions"][0]["applicant_argument_candidates"][0]["paragraph_reference"] == "पैरा 7"
    assert body["candidate_case_positions"][0]["pio_argument_candidates"][0]["paragraph_reference"] == "पैरा 8"
    assert body["candidate_case_positions"][0]["outcome_candidates"]
    assert "व्यक्तिगत" in body["evidence"][0]["matched_terms"]
    assert any("केवल मानव-सत्यापित" in item for item in body["limitations"])
    assert any("आवेदक" in item for item in body["role_specific_checks"])


def test_legal_application_neutral_role_returns_empty_when_verified_corpus_is_empty(monkeypatch) -> None:
    monkeypatch.setattr(research, "search_verified_documents", lambda _query, _limit=10: [])
    monkeypatch.setattr(research, "search_candidate_documents", lambda _query, _limit=10: [])
    monkeypatch.setattr(research, "search_verified_principles", lambda *_args: [])
    response = client.post(
        "/api/v1/research/apply",
        json={"question": "सूचना की प्रमाणित प्रति देने का नियम क्या है?", "role": "neutral"},
    )
    assert response.status_code == 200
    assert response.json()["evidence"] == []
    assert response.json()["result_count"] == 0



def test_legal_intelligence_understands_hindi_question_and_expands_terms():
    from app.services.legal_intelligence import understand_question

    plan = understand_question("PIO ne RTI ka jawab der se diya, kya us par jurmana lag sakta hai?")
    assert plan.intent == "penalty_or_accountability"
    assert "penalty_and_disciplinary_action" in plan.topics
    assert len(plan.search_queries) == 2
    assert "जुर्माना" in plan.key_terms


def test_legal_intelligence_ranks_issue_and_holding_above_generic_excerpt():
    from app.services.legal_intelligence import merge_ranked_documents, understand_question

    plan = understand_question("क्या व्यक्तिगत सूचना धारा 8(1)(j) में रोकी जा सकती है?")
    relevant = {
        "document_id": "a", "title": "CIC privacy decision",
        "legal_issue": "व्यक्तिगत सूचना और निजता", "holding": "धारा 8(1)(j) का परीक्षण",
        "learned_summary": "privacy exemption", "cited_sections": ["8(1)(j)"],
        "excerpt": "verified decision", "verification_status": "verified",
    }
    generic = {
        "document_id": "b", "title": "General RTI order", "legal_issue": "सामान्य प्रक्रिया",
        "holding": "सामान्य आदेश", "learned_summary": "", "cited_sections": [],
        "excerpt": "व्यक्तिगत सूचना का उल्लेख", "verification_status": "verified",
    }
    results = merge_ranked_documents([generic, relevant], plan, 5)
    assert results[0]["document_id"] == "a"
    assert results[0]["_intelligence_score"] > results[1]["_intelligence_score"]


def test_legal_intelligence_excludes_unverified_records():
    from app.services.legal_intelligence import merge_ranked_documents, understand_question

    plan = understand_question("धारा 20 का जुर्माना")
    record = {"document_id": "unverified", "title": "धारा 20 जुर्माना",
              "verification_status": "pending", "canonical_url": "https://example.test"}
    assert merge_ranked_documents([record], plan, 5) == []



def test_machine_extracted_candidates_are_retrieved_separately_from_verified_results(monkeypatch) -> None:
    candidate = {
        "document_id": "candidate-1",
        "title": "CIC machine-extracted order",
        "canonical_url": "https://cic.gov.in/orders/candidate-1",
        "authority": "CIC",
        "decision_date": None,
        "document_type": "order",
        "excerpt": "धारा 8 के तहत सूचना रोकने का संभावित अंश",
        "legal_issue": "धारा 8 की छूट",
        "holding": None,
        "cited_sections": ["धारा 8"],
        "content_sha256": "c" * 64,
        "analysis_status": "human_review_required",
        "analysis_method": "rule_based_structured_v3",
        "extraction_status": "extracted",
        "verification_status": "machine_extracted_candidate",
        "decision_candidates": [{
            "kind": "finding_candidate",
            "label": "आयोग की finding का संभावित अंश",
            "excerpt": "The Commission observes that the exemption must be justified.",
            "source_url": "https://cic.gov.in/orders/candidate-1",
            "paragraph_reference": "पैरा 9",
            "review_status": "human_review_required",
        }],
    }
    monkeypatch.setattr(research, "search_verified_documents", lambda *_args: [])
    monkeypatch.setattr(research, "search_candidate_documents", lambda *_args: [candidate])
    monkeypatch.setattr(research, "search_verified_principles", lambda *_args: [])

    search_response = client.post(
        "/api/v1/research/search",
        json={"query": "धारा 8", "limit": 5},
    )
    assert search_response.status_code == 200
    search_body = search_response.json()
    assert search_body["results"] == []
    assert search_body["result_count"] == 0
    assert search_body["candidate_result_count"] == 1
    assert search_body["candidate_results"][0]["verification_status"] == "machine_extracted_candidate"

    apply_response = client.post(
        "/api/v1/research/apply",
        json={"question": "क्या धारा 8 के तहत सूचना रोकी जा सकती है?", "role": "neutral"},
    )
    assert apply_response.status_code == 200
    body = apply_response.json()
    assert body["evidence"] == []
    assert body["verified_principles"] == []
    assert body["citations"] == []
    assert body["candidate_result_count"] == 1
    assert body["candidate_evidence"][0]["verification_status"] == "machine_extracted_candidate"
    assert body["candidate_citations"][0]["verification_status"] == "machine_extracted_candidate"
    assert body["candidate_case_positions"][0]["finding_candidates"][0]["paragraph_reference"] == "पैरा 9"
    assert body["direct_answer"].startswith("सीधा जवाब:")
