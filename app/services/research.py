# रिपॉजिटरी पथ: rti_backend/app/services/research.py
"""कानूनी शोध सेवा; unverified crawler output कभी evidence नहीं बनता."""


from app.models.research import (
    AppliedLegalEvidence,
    LegalApplicationRequest,
    LegalApplicationResponse,
    LegalResearchQuery,
    LegalResearchResponse,
)
from app.repositories.legal_knowledge import search_verified_documents
from app.repositories.legal_principles import search_verified_principles
from app.services.legal_intelligence import (
    TOKEN_RE,
    STOP_WORDS,
    merge_ranked_documents,
    understand_question,
)

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


def _terms(value: str) -> set[str]:
    """Hindi/English legal text के meaningful lexical terms निकालें."""
    return {
        token.lower()
        for token in TOKEN_RE.findall(value)
        if token.lower() not in STOP_WORDS
    }


def apply_verified_legal_knowledge(
    request: LegalApplicationRequest,
) -> LegalApplicationResponse:
    """Verified decisions को नए प्रश्न से मिलाएँ; कोई unverified holding न गढ़ें."""
    plan = understand_question(request.question)
    # दो स्वतंत्र offline retrieval passes: user के मूल शब्द और पहचाने गए कानूनी concepts.
    candidates = []
    for query in plan.search_queries:
        candidates.extend(search_verified_documents(query, min(request.limit * 2, 30)))
    ranked_records = merge_ranked_documents(candidates, plan, request.limit)
    evidence = []
    for record in ranked_records:
        raw = record
        score = raw.pop("_intelligence_score")
        matched = raw.pop("_matched_terms")
        coverage = len(matched) / max(1.0, len(plan.key_terms))
        if coverage >= 0.30:
            label = "strong_concept_match"
        elif coverage >= 0.12:
            label = "moderate_concept_match"
        else:
            label = "possible_related_result"
        evidence.append(AppliedLegalEvidence(
            document_id=raw["document_id"],
            title=raw.get("title") or raw["canonical_url"],
            canonical_url=raw["canonical_url"],
            authority=raw.get("authority"),
            decision_date=raw.get("decision_date"),
            legal_issue=raw.get("legal_issue"),
            holding=raw.get("holding"),
            cited_sections=raw.get("cited_sections") or [],
            content_sha256=raw.get("content_sha256"),
            matched_terms=matched,
            relevance_label=label,
            relevance_score=score,
        ))

    # हर प्रश्न के intent के अनुसार guidance बदलती है; fixed five-point template हटाया गया.
    common_checks = []

    role_checks = {
        "applicant": [
            "आवेदक द्वारा माँगी गई सूचना और रिकॉर्ड के अस्तित्व/नियंत्रण को स्पष्ट करें।",
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
    query_terms = set(plan.key_terms)
    principle_query = " OR ".join(plan.key_terms[:20]) or request.question
    principle_records = search_verified_principles(principle_query, min(request.limit, 8))
    traced_principles = []
    for principle in principle_records:
        searchable_principle = " ".join(
            str(principle.get(key) or "")
            for key in ("issue", "principle_text", "scope")
        )
        matched = sorted(query_terms & _terms(searchable_principle))
        condition_terms = _terms(" ".join(principle.get("conditions") or []))
        exception_terms = _terms(" ".join(principle.get("exceptions") or []))
        trace = [
            "सिद्धांत का प्रकार ratio_decidendi और स्थिति verified_current है; फिर भी वर्तमान कानून की अलग जाँच आवश्यक है।",
            "मिले हुए प्रश्न-संबंधी शब्द: " + (", ".join(matched) if matched else "कोई स्पष्ट शब्द-समानता नहीं"),
            "सभी शर्तों और अपवादों को मामले के तथ्यों से अलग-अलग मिलाना आवश्यक है।",
        ]
        if condition_terms & query_terms:
            trace.append("प्रश्न और दर्ज शर्तों में कुछ शब्द समान हैं; यह शर्त पूरी होने का प्रमाण नहीं है।")
        if exception_terms & query_terms:
            trace.append("प्रश्न और दर्ज अपवादों में कुछ शब्द समान हैं; अपवाद लागू होने का निष्कर्ष नहीं है।")
        if len(matched) >= 3:
            signal = "potentially_relevant_review_facts"
        elif matched:
            signal = "limited_keyword_overlap"
        else:
            signal = "needs_fact_comparison"
        traced_principles.append({
            **principle,
            "matched_terms": matched,
            "application_signal": signal,
            "application_trace": trace,
        })

    return LegalApplicationResponse(
        question=request.question,
        role=request.role,
        question_intent=plan.intent,
        identified_topics=list(plan.topics),
        answer_guidance=list(plan.guidance),
        evidence=evidence,
        verified_principles=traced_principles,
        result_count=len(evidence),
        common_legal_checks=common_checks,
        role_specific_checks=role_checks[request.role],
        limitations=[
            "यह offline Python intelligence है: Hindi-English intent पहचान, कानूनी concept expansion और explainable field-weighted ranking; यह paid LLM या generative legal opinion नहीं है।",
            "प्रासंगिकता label confidence score या binding precedent का निष्कर्ष नहीं है।",
            "केवल मानव-सत्यापित corpus के परिणाम शामिल हैं; खाली corpus पर कोई निर्णय लागू नहीं किया जा सकता।",
            "अंतिम कानूनी निष्कर्ष से पहले वर्तमान कानून, बाद के निर्णय, stay/appeal और मूल paragraph सत्यापित करें।",
        ],
    )
