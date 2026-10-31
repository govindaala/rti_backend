# रिपॉजिटरी पथ: rti_backend/app/api/routes/legal_cases.py
"""कानूनी रिकॉर्ड की संरचना और स्रोतों की प्रारंभिक जाँच के API."""

from fastapi import APIRouter

from app.models.legal_case import LegalCase
from app.services.source_registry import source_review_label

router = APIRouter(prefix="/legal-cases", tags=["कानूनी निर्णय"])


@router.post("/validate", summary="कानूनी केस रिकॉर्ड की जाँच")
def validate_legal_case(case: LegalCase) -> dict:
    """रिकॉर्ड को validate करें; यह endpoint अभी database में save नहीं करता."""
    citations = [
        {
            "citation_id": citation.citation_id,
            "source_title": citation.source_title,
            "pinpoint": citation.pinpoint,
            "verified": citation.verified,
            "review_label": source_review_label(str(citation.source_url)),
        }
        for citation in case.citations
    ]

    # किसी डोमेन का सरकारी होना उस पेज की सामग्री को सत्यापित नहीं करता।
    warnings = [
        "यह केवल संरचनात्मक और domain-स्तर की जाँच है; निर्णय का पाठ, पैरा और "
        "कानूनी स्थिति मानव/प्रमाणित समीक्षा से सत्यापित करना आवश्यक है।"
    ]
    if any(not citation["verified"] for citation in citations):
        warnings.append("एक या अधिक citations अभी सामग्री-स्तर पर सत्यापित नहीं हैं।")

    return {
        "valid": True,
        "stored": False,
        "case_id": case.case_id,
        "verification_status": case.verification_status.value,
        "issue_count": len(case.issues),
        "citations": citations,
        "warnings": warnings,
    }
