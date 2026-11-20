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
        "matched_terms": ["delay", "penalty", "section"],
        "application_signal": "fact_comparison_confirmed",
        "fact_comparison": {"verification_status": "human_verified",
                            "material_fact_matches": ["delay and statutory penalty issue"],
                            "pinpoint_citations": [{"paragraph": "7"}]},
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



def test_legacy_crawler_key_paragraphs_remain_usable_as_review_candidates():
    evidence = [{
        "document_id": "d5",
        "title": "Older CIC order",
        "canonical_url": "https://cic.gov.in/order/5",
        "key_paragraphs": [
            {
                "label": "मुद्दे की पहचान हेतु छोटा स्रोत-अंश",
                "excerpt": "Whether the requested record should be disclosed.",
                "source_url": "https://cic.gov.in/order/5",
            },
            {
                "label": "आदेश-संकेत की जाँच हेतु छोटा स्रोत-अंश",
                "excerpt": "Accordingly, the appeal is dismissed.",
                "source_url": "https://cic.gov.in/order/5",
            },
        ],
    }]
    result = build_legal_answer("record disclosure", "general", [], evidence, [])
    assert len(result["candidate_case_positions"]) == 1
    position = result["candidate_case_positions"][0]
    assert position["issue_candidates"][0]["excerpt"].startswith("Whether")
    assert position["operative_order_candidates"][0]["review_status"] == "human_review_required"


def test_evidence_citations_expose_page_and_paragraph_as_review_candidates():
    evidence = [{
        "document_id": "d6",
        "title": "Paged CIC order",
        "canonical_url": "https://cic.gov.in/order/6.pdf",
        "decision_candidates": [
            {
                "kind": "applicant_argument_candidate",
                "excerpt": "The appellant submitted that the record was not supplied.",
                "paragraph_reference": "पैरा 5",
                "page_reference": "PDF पृष्ठ 2",
                "source_url": "https://cic.gov.in/order/6.pdf",
                "review_status": "human_review_required",
            }
        ],
    }]
    result = build_legal_answer("record not supplied", "general", [], evidence, [])
    citation = result["citations"][0]

    assert citation["pinpoint"] == []
    assert citation["pinpoint_candidates"] == [{
        "source_url": "https://cic.gov.in/order/6.pdf",
        "review_status": "human_review_required",
        "kind": "applicant_argument_candidate",
        "paragraph_reference": "पैरा 5",
        "page_reference": "PDF पृष्ठ 2",
        "excerpt": "The appellant submitted that the record was not supplied.",
    }]


def test_duplicate_decision_citation_preserves_verified_and_candidate_pinpoints_separately():
    evidence = [{
        "document_id": "d7",
        "title": "CIC order",
        "canonical_url": "https://cic.gov.in/order/7.pdf",
        "decision_candidates": [{
            "kind": "finding_candidate",
            "excerpt": "The Commission observed that the search was incomplete.",
            "paragraph_reference": "पैरा 11",
            "page_reference": "PDF पृष्ठ 4",
            "source_url": "https://cic.gov.in/order/7.pdf",
            "review_status": "human_review_required",
        }],
    }]
    principle = {
        "document_id": "d7",
        "source_title": "CIC order",
        "source_url": "https://cic.gov.in/order/7.pdf",
        "authority": "CIC",
        "decision_date": "2025-04-01",
        "pinpoint_citations": [{"paragraph": "10"}],
        "legal_status": "verified_current",
        "principle_type": "ratio_decidendi",
        "matched_terms": ["search", "duty", "record"],
        "application_signal": "fact_comparison_confirmed",
        "fact_comparison": {"verification_status": "human_verified",
                            "material_fact_matches": ["search duty issue"],
                            "pinpoint_citations": [{"paragraph": "10"}]},
    }
    result = build_legal_answer("search duty", "general", [], evidence, [principle])

    assert len(result["citations"]) == 1
    citation = result["citations"][0]
    assert citation["pinpoint"] == [{"paragraph": "10"}]
    assert citation["pinpoint_candidates"][0]["paragraph_reference"] == "पैरा 11"
    assert citation["pinpoint_candidates"][0]["review_status"] == "human_review_required"




def test_current_ratio_produces_conclusion_first_answer_with_scope_and_source():
    principle = {
        "document_id": "d8",
        "source_title": "Verified CIC decision",
        "source_url": "https://cic.gov.in/order/8",
        "authority": "CIC",
        "principle_text": "A public authority must disclose an existing record unless a statutory exemption applies.",
        "scope": "Applies to records held by or under the control of the public authority.",
        "pinpoint_citations": [{"paragraph": "4"}],
        "conditions": ["The record must exist or be under the authority's control."],
        "exceptions": ["A valid exemption under section 8 may apply."],
        "legal_status": "verified_current",
        "principle_type": "ratio_decidendi",
        "matched_terms": ["record", "authority", "disclosure"],
        "application_signal": "fact_comparison_confirmed",
        "fact_comparison": {"verification_status": "human_verified",
                            "material_fact_matches": ["existing record held by public authority"],
                            "pinpoint_citations": [{"paragraph": "4"}]},
    }
    result = build_legal_answer("Can I obtain the record?", "general", [], [], [principle])

    assert result["direct_answer"].startswith("सीधा जवाब:")
    assert principle["principle_text"] in result["direct_answer"]
    assert principle["scope"] in result["direct_answer"]
    assert principle["conditions"][0] in result["direct_answer"]
    assert principle["exceptions"][0] in result["direct_answer"]
    assert principle["source_title"] in result["direct_answer"]


def test_related_evidence_without_current_ratio_gives_explicit_non_conclusion():
    result = build_legal_answer(
        "Can I obtain the record?", "general", [],
        [{"document_id": "d9", "title": "Related decision",
          "canonical_url": "https://cic.gov.in/order/9"}],
        [],
    )

    assert result["direct_answer"].startswith("सीधा जवाब:")
    assert "निश्चित निष्कर्ष नहीं" in result["direct_answer"]
    assert "शब्द-समानता" in result["direct_answer"]


def test_verified_current_ratio_without_principle_text_does_not_invent_conclusion():
    principle = {
        "document_id": "d10",
        "source_title": "Incomplete ratio record",
        "source_url": "https://cic.gov.in/order/10",
        "legal_status": "verified_current",
        "principle_type": "ratio_decidendi",
        "matched_terms": ["issue", "principle", "scope"],
        "application_signal": "fact_comparison_confirmed",
        "pinpoint_citations": [{"paragraph": "2"}],
        "fact_comparison": {"verification_status": "human_verified",
                            "material_fact_matches": ["reviewed material fact match"],
                            "pinpoint_citations": [{"paragraph": "2"}]},
    }
    result = build_legal_answer("question", "general", [], [], [principle])

    assert result["answer_status"] == "source_based_draft"
    assert result["direct_answer"].startswith("सीधा जवाब:")
    assert "निष्कर्ष देना अभी सुरक्षित नहीं" in result["direct_answer"]



def test_verified_ratio_without_question_level_match_is_not_applied():
    principle = {
        "document_id": "d11",
        "source_title": "Verified but unrelated decision",
        "source_url": "https://cic.gov.in/order/11",
        "principle_text": "A different legal issue has a specific statutory test.",
        "legal_status": "verified_current",
        "principle_type": "ratio_decidendi",
        "matched_terms": [],
        "application_signal": "needs_fact_comparison",
    }

    result = build_legal_answer("Question about an unrelated issue", "general", [], [], [principle])

    assert result["answer_status"] == "evidence_found_no_verified_ratio"
    assert result["direct_answer"].startswith("सीधा जवाब:")
    assert principle["principle_text"] not in result["direct_answer"]
    assert result["legal_basis"] == []


def test_two_keyword_overlap_is_not_enough_to_apply_verified_ratio():
    principle = {
        "document_id": "d12",
        "source_title": "Weakly matched decision",
        "source_url": "https://cic.gov.in/order/12",
        "principle_text": "The rule concerns disclosure of a record.",
        "legal_status": "verified_current",
        "principle_type": "ratio_decidendi",
        "matched_terms": ["record", "disclosure"],
        "application_signal": "limited_keyword_overlap",
    }

    result = build_legal_answer("Question about record disclosure", "general", [], [], [principle])

    assert result["answer_status"] == "evidence_found_no_verified_ratio"
    assert result["legal_basis"] == []
    assert "पर्याप्त मुद्दा-स्तरीय संबंध स्थापित नहीं हुआ" in result["direct_answer"]



def test_three_keyword_overlap_without_reviewed_fact_comparison_is_not_applied():
    principle = {
        "document_id": "d13",
        "source_title": "Keyword-overlap only",
        "source_url": "https://cic.gov.in/order/13",
        "principle_text": "The disclosure rule depends on whether the authority holds the record.",
        "legal_status": "verified_current",
        "principle_type": "ratio_decidendi",
        "matched_terms": ["record", "authority", "disclosure"],
        "application_signal": "potentially_relevant_review_facts",
        "pinpoint_citations": [{"paragraph": "9"}],
    }

    result = build_legal_answer("Question about record disclosure", "general", [], [], [principle])

    assert result["answer_status"] == "evidence_found_no_verified_ratio"
    assert result["legal_basis"] == []
    assert principle["principle_text"] not in result["direct_answer"]



def test_next_step_is_one_question_specific_action_for_verified_ratio():
    principle = {
        "document_id": "d14",
        "source_title": "CIC order",
        "source_url": "https://cic.gov.in/order/14",
        "authority": "CIC",
        "issue": "विलंब",
        "principle_text": "लिखित कारणों की जाँच आवश्यक है।",
        "pinpoint_citations": [{"paragraph": "7"}],
        "legal_status": "verified_current",
        "principle_type": "ratio_decidendi",
        "application_signal": "fact_comparison_confirmed",
        "fact_comparison": {
            "verification_status": "human_verified",
            "material_fact_matches": ["आवेदन और उत्तर की तारीख का मुद्दा"],
            "pinpoint_citations": [{"paragraph": "7"}],
        },
    }
    result = build_legal_answer(
        "PIO ने देर से उत्तर दिया", "delay_or_deadline", ["delay_and_time_limit"],
        [], [principle],
    )

    assert len(result["next_steps"]) == 1
    assert "CIC order" in result["next_steps"][0]
    assert "पैरा 7" in result["next_steps"][0]
    assert "तभी" in result["next_steps"][0]


def test_candidate_next_step_is_one_source_verification_action():
    candidate = {
        "document_id": "candidate-14",
        "title": "CIC candidate order",
        "canonical_url": "https://cic.gov.in/order/14.pdf",
        "verification_status": "machine_extracted_candidate",
        "decision_candidates": [{
            "kind": "finding_candidate",
            "excerpt": "The Commission observes that the record search was incomplete.",
            "page_reference": "PDF पृष्ठ 4",
            "source_url": "https://cic.gov.in/order/14.pdf",
            "review_status": "human_review_required",
        }],
    }
    result = build_legal_answer(
        "रिकॉर्ड खोज अधूरी थी", "record_availability", ["record_search_and_non_availability"],
        [], [], candidate_evidence=[candidate],
    )

    assert len(result["next_steps"]) == 1
    assert "CIC candidate order" in result["next_steps"][0]
    assert "PDF पृष्ठ 4" in result["next_steps"][0]
    assert "machine-extracted candidate" in result["next_steps"][0]
    assert "verified precedent" in result["next_steps"][0]


def test_no_source_returns_only_the_first_decisive_fact_gap_as_next_action():
    result = build_legal_answer(
        "PIO ने समय पर जवाब नहीं दिया; अब क्या करूँ?",
        "delay_or_deadline", ["delay_and_time_limit"], [], [],
    )

    assert len(result["next_steps"]) == 1
    assert "PIO को किस तारीख को मिला" in result["next_steps"][0]
    assert "माँगी गई सूचना का सटीक विवरण" not in result["next_steps"][0]
