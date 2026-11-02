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


import re

from app.models.research import (
    AppliedLegalEvidence,
    LegalApplicationRequest,
    LegalApplicationResponse,
)

_TOKEN_PATTERN = re.compile(r"[\\w\\u0900-\\u097F]{2,}", re.UNICODE)
_STOP_WORDS = {
    "और", "तथा", "क्या", "किस", "किसी", "कैसे", "कब", "है", "हैं", "था",
    "थी", "थे", "को", "की", "का", "के", "से", "पर", "में", "लिए", "द्वारा",
    "this", "that", "with", "from", "have", "has", "what", "when", "where",
    "which", "who", "does", "shall", "will", "would", "could", "should",
}


def _terms(value: str) -> set[str]:
    """Hindi/English legal query के meaningful lexical terms निकालें."""
    return {
        token.lower()
        for token in _TOKEN_PATTERN.findall(value)
        if token.lower() not in _STOP_WORDS
    }


def apply_verified_legal_knowledge(
    request: LegalApplicationRequest,
) -> LegalApplicationResponse:
    """Verified decisions को नए प्रश्न से मिलाएँ; कोई unverified holding न गढ़ें."""
    query_terms = _terms(request.question)
    records = search_verified_documents(request.question, request.limit)
    evidence = []
    for record in records:
        searchable = " ".join(
            str(record.get(key) or "")
            for key in ("title", "learned_summary", "legal_issue", "holding")
        ) + " " + " ".join(record.get("cited_sections") or [])
        matched = sorted(query_terms & _terms(searchable))
        # Ranking is a transparent lexical overlap indicator, not an AI confidence.
        ratio = len(matched) / max(1, len(query_terms))
        if ratio >= 0.35:
            label = "strong_keyword_overlap"
        elif ratio >= 0.15:
            label = "partial_keyword_overlap"
        else:
            label = "retrieved_for_review"
        evidence.append(AppliedLegalEvidence(
            document_id=record["document_id"],
            title=record.get("title") or record["canonical_url"],
            canonical_url=record["canonical_url"],
            authority=record.get("authority"),
            decision_date=record.get("decision_date"),
            legal_issue=record.get("legal_issue"),
            holding=record.get("holding"),
            cited_sections=record.get("cited_sections") or [],
            content_sha256=record.get("content_sha256"),
            matched_terms=matched,
            relevance_label=label,
        ))

    common_checks = [
        "पहले निर्णय का पूरा operative order और संबंधित pinpoint paragraph पढ़ें।",
        "यह जाँचें कि उद्धृत सिद्धांत बाद के उच्चतर/समन्वय पीठ के निर्णय से बदला, सीमित या पलटा तो नहीं गया।",
        "निर्णय के तथ्य, पक्षकार, मंच और लागू वैधानिक प्रावधान वर्तमान प्रश्न से मिलाएँ।",
        "केवल समान धारा दिखने से दोनों मामलों को समान न मानें; अपवाद, proviso और तथ्यात्मक अंतर जाँचें।",
        "हर निष्कर्ष को उसके आधिकारिक स्रोत URL और पैराग्राफ से जोड़ें।",
    ]
    role_checks = {
        "applicant": [
            "माँगी गई सूचना और रिकॉर्ड के अस्तित्व/नियंत्रण को स्पष्ट करें।",
            "PIO द्वारा बताए गए प्रत्येक अपवाद के आवश्यक तत्व और प्रमाण की जाँच करें।",
            "जहाँ संभव हो, severability/आंशिक प्रकटीकरण और वैधानिक अपील उपाय जाँचें।",
        ],
        "pio": [
            "लागू अपवाद के प्रत्येक वैधानिक तत्व और उसके तथ्यात्मक आधार की जाँच करें।",
            "धारा 10 के तहत पृथक्करण/आंशिक प्रकटीकरण की संभावना जाँचें।",
            "समय-सीमा, तीसरे पक्ष की प्रक्रिया और कारणयुक्त आदेश की आवश्यकताएँ जाँचें।",
        ],
        "neutral": [
            "दोनों पक्षों के तर्क, रिकॉर्ड और वैधानिक burden को अलग-अलग जाँचें।",
            "विवादित तथ्य और अनुपलब्ध साक्ष्य को स्पष्ट रूप से चिह्नित करें।",
        ],
    }
    return LegalApplicationResponse(
        question=request.question,
        role=request.role,
        evidence=evidence,
        common_legal_checks=common_checks,
        role_specific_checks=role_checks[request.role],
        limitations=[
            "यह नियम-आधारित retrieval और keyword overlap है; generative AI/LLM reasoning नहीं।",
            "प्रासंगिकता label confidence score या binding precedent का निष्कर्ष नहीं है।",
            "केवल मानव-सत्यापित corpus के परिणाम शामिल हैं; खाली corpus पर कोई निर्णय लागू नहीं किया जा सकता।",
            "अंतिम कानूनी निष्कर्ष से पहले वर्तमान कानून, बाद के निर्णय, stay/appeal और मूल paragraph सत्यापित करें।",
        ],
    )
