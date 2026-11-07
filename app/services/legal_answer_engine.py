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
    candidate_case_positions = _candidate_case_positions(evidence)

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

    fact_gaps = _question_specific_fact_gaps(intent, topics)
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
        "candidate_case_positions": candidate_case_positions,
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
    }



def _candidate_case_positions(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Expose short extracted party/finding/order passages as review candidates only."""
    labels = {
        "applicant_argument_candidate": "applicant_argument_candidates",
        "pio_argument_candidate": "pio_argument_candidates",
        "finding_candidate": "court_or_commission_finding_candidates",
        "outcome_candidate": "outcome_candidates",
        "operative_order_candidate": "operative_order_candidates",
        "issue_candidate": "issue_candidates",
    }
    results = []
    for document in evidence:
        candidates = document.get("decision_candidates") or document.get("key_paragraphs") or []
        grouped: dict[str, list[dict[str, Any]]] = {name: [] for name in labels.values()}
        for item in candidates:
            if not isinstance(item, dict) or item.get("review_status") != "human_review_required":
                continue
            target = labels.get(item.get("kind"))
            if not target:
                continue
            grouped[target].append({
                "excerpt": item.get("excerpt"),
                "paragraph_reference": item.get("paragraph_reference"),
                "label": item.get("label"),
                "source_url": item.get("source_url") or document.get("canonical_url"),
                "review_status": "human_review_required",
            })
        if not any(grouped.values()):
            continue
        results.append({
            "document_id": document.get("document_id"),
            "source_title": document.get("title") or document.get("canonical_url"),
            "source_url": document.get("canonical_url"),
            "authority": document.get("authority"),
            "decision_date": document.get("decision_date"),
            **grouped,
            "note": (
                "ये rule-based निकाले गए छोटे स्रोत-अंश हैं। पक्ष की स्थिति, "
                "अंतिम आदेश और ratio/obiter का निर्धारण मूल निर्णय पढ़कर मानव समीक्षा से करें।"
            ),
        })
    return results


def _question_specific_fact_gaps(intent: str, topics: list[str]) -> list[str]:
    """Ask only for facts that materially affect the identified RTI issue."""
    gaps = [
        "माँगी गई सूचना का सटीक विवरण और संबंधित लोक प्राधिकरण/शाखा।",
    ]
    topic_gaps = {
        "delay_and_time_limit": [
            "RTI आवेदन PIO को किस तारीख को मिला; कोई transfer या अतिरिक्त शुल्क सूचना कब भेजी गई?",
            "PIO का उत्तर/अस्वीकृति कब मिला, या आज तक उत्तर नहीं मिला?",
        ],
        "penalty_and_disciplinary_action": [
            "देरी/गलत सूचना के लिए PIO ने क्या लिखित कारण दिया और क्या सुनवाई का अवसर मिला?",
            "क्या सूचना न मिलने से कोई वास्तविक नुकसान/हानि हुई; उसका दस्तावेजी प्रमाण क्या है?",
        ],
        "personal_information_privacy": [
            "सूचना किस व्यक्ति से संबंधित है और आवेदक का उस व्यक्ति/रिकॉर्ड से क्या संबंध है?",
            "कौन-सा बड़ा लोकहित बताया जा रहा है और उसका समर्थन करने वाले दस्तावेज़ क्या हैं?",
        ],
        "third_party_information": [
            "PIO ने तीसरे पक्ष को नोटिस दिया था या नहीं; नोटिस/आपत्ति की तारीखें क्या हैं?",
            "तीसरे पक्ष की सहमति/आपत्ति और PIO का कारणयुक्त निर्णय उपलब्ध है?",
        ],
        "disclosure_and_exemptions": [
            "PIO ने किस सटीक उपधारा में छूट लगाई और आदेश में क्या कारण लिखे?",
            "क्या सूचना का कोई हिस्सा अलग करके दिया जा सकता है; लोकहित का आधार क्या है?",
        ],
        "inspection_and_copies": [
            "किस रिकॉर्ड/फाइल/रजिस्टर का निरीक्षण या प्रमाणित प्रति चाहिए और अनुमानित अवधि/पृष्ठ कितने हैं?",
            "निरीक्षण/कॉपी के लिए तारीख दी गई थी या शुल्क माँगा गया था; उसकी रसीद/गणना उपलब्ध है?",
        ],
        "fees_and_cost": [
            "कितना शुल्क, किस नियम/गणना से माँगा गया और सूचना किस तारीख को दी गई?",
            "क्या आवेदक BPL श्रेणी में है और वैध प्रमाण आवेदन के साथ दिया गया था?",
        ],
        "record_search_and_non_availability": [
            "PIO ने रिकॉर्ड अनुपलब्ध बताया, नष्ट बताया या दूसरे प्राधिकरण को transfer किया?",
            "रिकॉर्ड retention/destruction register, search note या transfer पत्र उपलब्ध है?",
        ],
        "first_appeal": [
            "प्रथम अपील किस तारीख को दाखिल हुई और FAA ने कब आदेश दिया/नहीं दिया?",
            "अपील में कौन-सी राहत माँगी गई और सुनवाई/आदेश की प्रति उपलब्ध है?",
        ],
        "second_appeal_and_cic": [
            "FAA का आदेश कब मिला, या प्रथम अपील पर 45 दिन में निर्णय नहीं हुआ?",
            "द्वितीय अपील दाखिल करने की तारीख, विलंब का कारण और संलग्न आदेश क्या हैं?",
        ],
        "complaint": [
            "शिकायत का आधार धारा 18 के किस उपखंड से जुड़ा है और कौन-सा साक्ष्य उपलब्ध है?",
            "क्या पहले धारा 19 की अपील की गई; यदि नहीं, तो शिकायत में माँगी गई राहत क्या है?",
        ],
        "life_and_liberty": [
            "जीवन या स्वतंत्रता पर तात्कालिक खतरे का ठोस तथ्य और दस्तावेजी प्रमाण क्या है?",
            "PIO को आवेदन मिलने की तारीख/समय और 48 घंटे की समय-सीमा का रिकॉर्ड क्या है?",
        ],
        "public_interest": [
            "कौन-सा विशिष्ट व्यापक लोकहित है और उससे प्रभावित जनता/समूह का प्रमाण क्या है?",
            "निजता/गोपनीयता के संभावित नुकसान की तुलना में लोकहित कैसे अधिक है?",
        ],
        "severability_and_partial_disclosure": [
            "कौन-से हिस्से छूट के दायरे में बताए गए और शेष रिकॉर्ड अलग करके दिया जा सकता है?",
            "PIO ने धारा 10 के तहत पृथक्करण पर कोई कारणयुक्त निर्णय दिया?",
        ],
    }
    for topic in topics:
        gaps.extend(topic_gaps.get(topic, []))
    if intent in {"appeal_or_remedy", "delay_or_deadline", "penalty_or_accountability"}:
        gaps.append("प्रथम अपील/द्वितीय अपील की तारीखें, FAA/CIC आदेश और उनकी प्राप्ति का प्रमाण, यदि उपलब्ध हों।")
    return list(dict.fromkeys(gaps))


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
