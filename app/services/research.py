# रिपॉजिटरी पथ: rti_backend/app/services/research.py
"""कानूनी शोध सेवा; unverified crawler output कभी evidence नहीं बनता."""

from app.models.research import LegalResearchQuery, LegalResearchResponse
from app.repositories.legal_knowledge import search_verified_documents

RESEARCH_NOTE = (
    "परिणाम केवल मानव-सत्यापित corpus से हैं। उद्धृत निर्णय की वर्तमान वैधता, "
    "बाद के निर्णयों और लागू कानून की जाँच किए बिना इसे अंतिम कानूनी राय न मानें।"
)


def run_legal_research(query: LegalResearchQuery) -> LegalResearchResponse:
    """सत्यापित स्रोत खोजें और प्रत्येक परिणाम का स्रोत/हैश बनाए रखें."""
    records = search_verified_documents(query.query.strip(), query.limit)
    return LegalResearchResponse(
        query=query.query.strip(),
        results=records,
        result_count=len(records),
        note=RESEARCH_NOTE,
    )
