# रिपॉजिटरी पथ: rti_backend/tests/test_legal_case.py
"""कानूनी रिकॉर्ड की संरचना और स्रोत-सत्यापन नियमों के परीक्षण."""

import pytest
from pydantic import ValidationError

from app.models.legal_case import LegalCase, VerificationStatus
from app.services.legal_analysis import AnalysisRole, build_analysis_instructions


def sample_case() -> dict:
    """परीक्षण के लिए एक न्यूनतम, काल्पनिक रिकॉर्ड बनाएँ."""
    return {
        "case_id": "TEST-001",
        "forum": "High Court",
        "case_title": "परीक्षण हेतु काल्पनिक निर्णय",
        "issues": [
            {
                "issue": "क्या संबंधित रिकॉर्ड पर RTI अपवाद लागू होता है?",
                "applicant_arguments_accepted": ["रिकॉर्ड का कुछ भाग सार्वजनिक है"],
                "pio_arguments_rejected": ["बिना कारण पूरा रिकॉर्ड रोकना"],
                "legal_principles": ["हर मुद्दे का अलग परीक्षण आवश्यक है"],
                "citation_ids": ["CIT-1"],
            }
        ],
        "citations": [
            {
                "citation_id": "CIT-1",
                "source_title": "परीक्षण स्रोत",
                "source_url": "https://example.com/decision",
                "pinpoint": "पैरा 10",
                "summary": "परीक्षण के लिए काल्पनिक संदर्भ",
                "verified": False,
            }
        ],
    }


def test_case_preserves_both_sides_issue_findings() -> None:
    """एक ही मुद्दे में दोनों पक्षों के स्वीकार/अस्वीकार तर्क रखे जा सकें."""
    case = LegalCase.model_validate(sample_case())

    assert case.issues[0].applicant_arguments_accepted
    assert case.issues[0].pio_arguments_rejected


def test_unknown_citation_reference_is_rejected() -> None:
    """रिकॉर्ड में मौजूद न होने वाला citation ID स्वीकार न हो."""
    data = sample_case()
    data["issues"][0]["citation_ids"] = ["MISSING"]

    with pytest.raises(ValidationError):
        LegalCase.model_validate(data)


def test_issue_without_citation_is_rejected() -> None:
    """हर कानूनी मुद्दे के साथ कम-से-कम एक source reference अनिवार्य हो."""
    data = sample_case()
    data["issues"][0]["citation_ids"] = []

    with pytest.raises(ValidationError):
        LegalCase.model_validate(data)


def test_duplicate_citation_id_is_rejected() -> None:
    """एक ही केस में citation IDs अद्वितीय होने चाहिए."""
    data = sample_case()
    data["citations"].append(dict(data["citations"][0]))

    with pytest.raises(ValidationError):
        LegalCase.model_validate(data)


def test_verified_case_requires_every_referenced_source_verified() -> None:
    """verified केस के हर issue में प्रयुक्त सभी citations verified हों."""
    data = sample_case()
    data["verification_status"] = VerificationStatus.VERIFIED.value
    data["citations"][0]["verified"] = False

    with pytest.raises(ValidationError):
        LegalCase.model_validate(data)

    data["citations"][0]["verified"] = True
    assert LegalCase.model_validate(data).verification_status == VerificationStatus.VERIFIED


def test_role_guidance_is_distinct_but_has_shared_rules() -> None:
    """दोनों भूमिकाओं को अलग निर्देश और समान निष्पक्षता नियम मिलें."""
    applicant = build_analysis_instructions(AnalysisRole.APPLICANT)
    pio = build_analysis_instructions(AnalysisRole.PIO)

    assert "आवेदक" in applicant
    assert "PIO" in pio
    assert "आविष्कार न करें" in applicant
    assert "आविष्कार न करें" in pio
    assert applicant != pio
