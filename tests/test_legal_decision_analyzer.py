# Repository path: rti_backend/tests/test_legal_decision_analyzer.py
from app.services.legal_decision_analyzer import analyze_decision_text

def test_only_explicitly_linked_rti_sections_are_extracted():
    text = ("The Right to Information Act, 2005 applies. Section 8(1)(j) of the RTI Act "
            "was considered. Whether personal information can be disclosed is the question "
            "before the Commission. Accordingly, the appeal is dismissed.")
    result = analyze_decision_text(text, "https://cic.gov.in/orders/example")
    assert result["analysis_status"] == "human_review_required"
    assert result["analysis_method"] == "rule_based_structured_v3"
    assert "धारा 8(1)(j)" in result["cited_sections"]
    assert result["legal_issue"]
    assert result["holding"]
    assert all(item["source_url"] == "https://cic.gov.in/orders/example" for item in result["key_paragraphs"])

def test_does_not_invent_conclusions_for_empty_text():
    result = analyze_decision_text("  ", "https://cic.gov.in/orders/example")
    assert result["analysis_status"] == "text_unavailable"
    assert result["learned_summary"] is None
    assert result["cited_sections"] == []

def test_unrelated_section_is_not_mislabelled_as_rti_act():
    result = analyze_decision_text("Section 302 IPC was discussed. The appeal is dismissed.", "https://sci.gov.in/")
    assert result["cited_sections"] == []



def test_extracts_party_arguments_findings_and_order_as_review_candidates():
    text = (
        "Para 7: The appellant submitted that the requested record was not supplied. "
        "Para 8: The CPIO submitted that the record was not available. "
        "The Commission observed that the reply did not explain the search. "
        "Accordingly, the appeal is allowed."
    )
    result = analyze_decision_text(text, "https://cic.gov.in/orders/example")
    candidates = result["key_paragraphs"]
    kinds = {item["kind"] for item in candidates}

    assert "applicant_argument_candidate" in kinds
    assert "pio_argument_candidate" in kinds
    assert "finding_candidate" in kinds
    assert "outcome_candidate" in kinds
    assert "operative_order_candidate" in kinds
    applicant = next(x for x in candidates if x["kind"] == "applicant_argument_candidate")
    assert applicant["paragraph_reference"] == "पैरा 7"
    assert applicant["review_status"] == "human_review_required"
    assert applicant["source_url"] == "https://cic.gov.in/orders/example"
    assert "ratio_decidendi" not in applicant


def test_hindi_party_arguments_are_not_silently_promoted_to_holdings():
    text = (
        "अपीलकर्ता ने तर्क दिया कि मांगी गई सूचना उपलब्ध नहीं कराई गई थी। "
        "लोक सूचना अधिकारी ने कहा कि रिकॉर्ड कार्यालय में उपलब्ध नहीं है। "
        "आयोग ने पाया कि खोज का विवरण आदेश में दर्ज नहीं है।"
    )
    result = analyze_decision_text(text, "https://cic.gov.in/orders/hindi")
    kinds = [item["kind"] for item in result["key_paragraphs"]]
    assert "applicant_argument_candidate" in kinds
    assert "pio_argument_candidate" in kinds
    assert "finding_candidate" in kinds
    assert result["analysis_status"] == "human_review_required"
