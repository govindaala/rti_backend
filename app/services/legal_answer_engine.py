"""Source-grounded, deterministic answer assembly for RTI research.

This module does not invent holdings or decide disputed facts. It composes a
structured draft only from verified documents and reviewed current ratio records.
"""
from __future__ import annotations

from typing import Any


def build_legal_answer(
    question: str,
    intent: str,
    topics: list[str],
    evidence: list[dict[str, Any]],
    principles: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build an auditable answer draft with explicit evidence and fact gaps."""
    current = [
        item for item in principles
        if item.get("legal_status") == "verified_current"
        and item.get("principle_type") == "ratio_decidendi"
    ]
    citations: list[dict[str, Any]] = []
    legal_basis: list[dict[str, Any]] = []
    positions: list[dict[str, Any]] = []
    conditions: list[str] = []
    exceptions: list[str] = []

    for item in current:
        citation = {
            "title": item.get("source_title") or "Verified decision",
            "authority": item.get("authority"),
            "decision_date": item.get("decision_date"),
            "url": item.get("source_url"),
            "pinpoint": item.get("pinpoint_citations") or [],
            "document_id": item.get("document_id"),
        }
        citations.append(citation)
        legal_basis.append({
            "issue": item.get("issue"),
            "principle": item.get("principle_text"),
            "scope": item.get("scope"),
            "source": citation,
        })
        positions.append({
            "issue": item.get("issue"),
            "applicant_arguments_accepted": item.get("applicant_arguments_accepted") or [],
            "applicant_arguments_rejected": item.get("applicant_arguments_rejected") or [],
            "pio_arguments_accepted": item.get("pio_arguments_accepted") or [],
            "pio_arguments_rejected": item.get("pio_arguments_rejected") or [],
            "outcome": item.get("outcome"),
            "source": citation,
        })
        conditions.extend(str(value) for value in (item.get("conditions") or []) if value)
        exceptions.extend(str(value) for value in (item.get("exceptions") or []) if value)

    for item in evidence:
        citations.append({
            "title": item.get("title"),
            "authority": item.get("authority"),
            "decision_date": item.get("decision_date"),
            "url": item.get("canonical_url"),
            "pinpoint": [],
            "document_id": item.get("document_id"),
        })

    citations = _dedupe_citations(citations)
    if current:
        status = "source_based_draft"
        direct_answer = (
            "उपलब्ध मानव-सत्यापित वर्तमान ratio records के आधार पर नीचे प्रारंभिक "
            "कानूनी स्थिति दी गई है। इसे अपने तथ्यों और उद्धृत निर्णय के मूल अनुच्छेद "
            "से मिलाकर ही अंतिम निष्कर्ष मानें।"
        )
    elif evidence:
        status = "evidence_found_no_verified_ratio"
        direct_answer = (
            "संबंधित सत्यापित निर्णय मिले हैं, लेकिन इस प्रश्न पर वर्तमान स्थिति "
            "के रूप में मानव-सत्यापित ratio record नहीं मिला। इसलिए अभी निश्चित "
            "कानूनी निष्कर्ष देना उचित नहीं है।"
        )
    else:
        status = "insufficient_verified_material"
        direct_answer = (
            "इस प्रश्न के लिए उपलब्ध सत्यापित corpus में पर्याप्त संबंधित सामग्री "
            "नहीं मिली। कोई कानूनी निष्कर्ष अनुमान से नहीं बनाया गया है।"
        )

    fact_gaps = [
        "RTI आवेदन की तारीख, PIO को प्राप्ति की तारीख और उत्तर/अस्वीकृति की तारीख।",
        "PIO के आदेश में उद्धृत धारा, कारण और उपलब्ध संलग्नक।",
        "माँगी गई सूचना का सटीक विवरण तथा रिकॉर्ड किस लोक प्राधिकरण के पास है।",
        "प्रथम अपील/द्वितीय अपील की तारीख और अब तक के आदेश, यदि कोई हों।",
    ]
    next_steps = [
        "मूल RTI आवेदन, डाक/ऑनलाइन प्राप्ति प्रमाण और PIO का पूरा उत्तर साथ रखें।",
        "प्रत्येक लागू शर्त और अपवाद को अपने वास्तविक तथ्यों से अलग-अलग मिलाएँ।",
        "नीचे दिए स्रोत लिंक खोलकर मूल निर्णय, संबंधित अनुच्छेद और बाद के निर्णय जाँचें।",
    ]
    if not current:
        next_steps.insert(
            0,
            "संबंधित निर्णयों की मानव समीक्षा कर सही ratio, परिणाम और pinpoint paragraph "
            "दर्ज होने तक इस उत्तर को शोध-संकेत मात्र मानें।",
        )

    return {
        "answer_status": status,
        "direct_answer": direct_answer,
        "legal_basis": legal_basis,
        "case_positions": positions,
        "conditions_to_check": _dedupe_strings(conditions),
        "exceptions_to_check": _dedupe_strings(exceptions),
        "fact_gaps": fact_gaps,
        "next_steps": next_steps,
        "citations": citations,
        "disclaimer": (
            "यह नियम-आधारित शोध-मसौदा है, वकील की राय या न्यायिक निर्णय नहीं। "
            "प्रासंगिकता/शब्द-समानता किसी फैसले की बाध्यकारी प्रकृति सिद्ध नहीं करती। "
            "वर्तमान अधिनियम, नियम, बाद के निर्णय, अपील/स्थगन और मूल अनुच्छेद जाँचें।"
        ),
        "question_intent": intent,
        "identified_topics": topics,
    }


def _dedupe_strings(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value.strip()))


def _dedupe_citations(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    result = []
    for value in values:
        key = (str(value.get("document_id") or ""), str(value.get("url") or ""))
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result
