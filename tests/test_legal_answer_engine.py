"""Tests for source-grounded legal answer assembly."""
from app.services.legal_answer_engine import build_legal_answer


def test_answer_uses_only_verified_current_ratio_and_keeps_citations():
    principle = {
        "principle_id": "p1",
        "document_id": "d1",
        "source_title": "CIC order",
        "source_url": "https://cic.gov.in/order/1",
        "authority": "CIC",
        "issue": "RTI delay",
        "principle_text": "Penalty requires statutory conditions to be established.",
        "scope": "Section 20",
        "conditions": ["reasonable opportunity of hearing"],
        "exceptions": [],
        "applicant_arguments_accepted": ["delay"],
        "applicant_arguments_rejected": [],
        "pio_arguments_accepted": [],
        "pio_arguments_rejected": ["no explanation"],
        "outcome": "Applicant partly succeeded",
        "pinpoint_citations": [{"paragraph": "7"}],
        "legal_status": "verified_current",
        "principle_type": "ratio_decidendi",
    }
    result = build_legal_answer(
        "PIO delay penalty?", "penalty_or_accountability", ["penalty"],
        [], [principle],
    )
    assert result["answer_status"] == "source_based_draft"
    assert result["legal_basis"][0]["principle"] == principle["principle_text"]
    assert result["conditions_to_check"] == ["reasonable opportunity of hearing"]
    assert result["citations"][0]["url"] == principle["source_url"]
    assert result["case_positions"][0]["outcome"] == "Applicant partly succeeded"


def test_answer_never_promotes_unreviewed_or_unverified_principle():
    principle = {
        "document_id": "d2",
        "source_title": "Pending",
        "source_url": "https://example.test/pending",
        "issue": "delay",
        "principle_text": "unreviewed text",
        "legal_status": "pending_review",
        "principle_type": "ratio_decidendi",
    }
    result = build_legal_answer("question", "general", [], [], [principle])
    assert result["answer_status"] == "insufficient_verified_material"
    assert result["legal_basis"] == []
    assert result["case_positions"] == []


def test_related_documents_without_verified_ratio_are_not_a_final_answer():
    evidence = [{
        "document_id": "d3", "title": "Related order",
        "canonical_url": "https://cic.gov.in/order/3", "authority": "CIC",
    }]
    result = build_legal_answer("question", "general", [], evidence, [])
    assert result["answer_status"] == "evidence_found_no_verified_ratio"
    assert "निश्चित" in result["direct_answer"]
    assert result["citations"][0]["url"] == evidence[0]["canonical_url"]



def test_fact_gaps_are_specific_to_privacy_and_penalty_topics():
    privacy = build_legal_answer(
        "personal data", "disclosure_or_exemption",
        ["personal_information_privacy"], [], [],
    )
    penalty = build_legal_answer(
        "delay penalty", "penalty_or_accountability",
        ["delay_and_time_limit", "penalty_and_disciplinary_action"], [], [],
    )
    assert any("किस व्यक्ति" in item for item in privacy["fact_gaps"])
    assert any("लोकहित" in item for item in privacy["fact_gaps"])
    assert any("सुनवाई" in item for item in penalty["fact_gaps"])
    assert any("PIO को" in item for item in penalty["fact_gaps"])
    assert not any("तीसरे पक्ष" in item for item in privacy["fact_gaps"])



def test_extracted_party_positions_remain_review_candidates_not_verified_ratio():
    evidence = [{
        "document_id": "d4",
        "title": "CIC order",
        "canonical_url": "https://cic.gov.in/order/4",
        "authority": "CIC",
        "decision_candidates": [
            {
                "kind": "applicant_argument_candidate",
                "excerpt": "The appellant submitted that the reply was delayed.",
                "paragraph_reference": "पैरा 5",
                "source_url": "https://cic.gov.in/order/4",
                "review_status": "human_review_required",
            },
            {
                "kind": "pio_argument_candidate",
                "excerpt": "The CPIO submitted that the delay was explained.",
                "paragraph_reference": "पैरा 6",
                "source_url": "https://cic.gov.in/order/4",
                "review_status": "human_review_required",
            },
        ],
    }]
    result = build_legal_answer("PIO delay", "delay_or_deadline", [], evidence, [])
    assert result["case_positions"] == []
    assert len(result["candidate_case_positions"]) == 1
    position = result["candidate_case_positions"][0]
    assert position["applicant_argument_candidates"][0]["paragraph_reference"] == "पैरा 5"
    assert position["pio_argument_candidates"][0]["paragraph_reference"] == "पैरा 6"
    assert "मानव समीक्षा" in position["note"]
