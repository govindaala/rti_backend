# Repository path: rti_backend/tests/test_legal_decision_analyzer.py
from app.services.legal_decision_analyzer import analyze_decision_text

def test_only_explicitly_linked_rti_sections_are_extracted():
    text = ("The Right to Information Act, 2005 applies. Section 8(1)(j) of the RTI Act "
            "was considered. Whether personal information can be disclosed is the question "
            "before the Commission. Accordingly, the appeal is dismissed.")
    result = analyze_decision_text(text, "https://cic.gov.in/orders/example")
    assert result["analysis_status"] == "human_review_required"
    assert result["analysis_method"] == "rule_based_extractive_v1"
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
