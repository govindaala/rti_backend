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
    candidate_evidence: list[dict[str, Any]] | None = None,
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
    candidate_evidence = candidate_evidence or []
    candidate_case_positions = (
        _candidate_case_positions(evidence)
        + _candidate_case_positions(candidate_evidence)
    )
    candidate_citations: list[dict[str, Any]] = []
    for item in candidate_evidence:
        citation = {
            "title": item.get("title") or item.get("canonical_url"),
            "authority": item.get("authority"),
            "decision_date": item.get("decision_date"),
            "url": item.get("canonical_url"),
            "document_id": item.get("document_id"),
            "verification_status": "machine_extracted_candidate",
            "analysis_status": item.get("analysis_status"),
            "analysis_method": item.get("analysis_method"),
            "extraction_status": item.get("extraction_status"),
        }
        pinpoint_candidates = _candidate_pinpoint_references(item)
        if pinpoint_candidates:
            citation["pinpoint_candidates"] = pinpoint_candidates
        candidate_citations.append(citation)

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
        citation = {
            "title": item.get("title"),
            "authority": item.get("authority"),
            "decision_date": item.get("decision_date"),
            "url": item.get("canonical_url"),
            "pinpoint": [],
            "document_id": item.get("document_id"),
        }
        pinpoint_candidates = _candidate_pinpoint_references(item)
        if pinpoint_candidates:
            citation["pinpoint_candidates"] = pinpoint_candidates
        citations.append(citation)

    citations = _dedupe_citations(citations)
    if current:
        status = "source_based_draft"
        direct_answer = _build_direct_answer(current)
    elif evidence:
        status = "evidence_found_no_verified_ratio"
        direct_answer = (
            "सीधा जवाब: अभी उपलब्ध सामग्री से इस प्रश्न पर लागू कानूनी नियम का "
            "निश्चित निष्कर्ष नहीं निकाला जा सकता। संबंधित निर्णय मिले हैं, लेकिन "
            "उनमें से किसी का वर्तमान ratio इस प्रश्न पर सत्यापित रूप से स्थापित नहीं है। "
            "इसलिए केवल शब्द-समानता के आधार पर अधिकार, उल्लंघन या राहत घोषित नहीं की जा रही।"
        )
    else:
        status = "insufficient_verified_material"
        direct_answer = (
            "सीधा जवाब: उपलब्ध सत्यापित कानूनी ज्ञान-संग्रह में इस प्रश्न का उत्तर "
            "देने योग्य स्रोत नहीं मिला। इसका अर्थ यह नहीं कि आपका दावा गलत है; "
            "अभी इस इंजन के पास निष्कर्ष सिद्ध करने के लिए पर्याप्त सत्यापित सामग्री नहीं है।"
        )

    fact_gaps = _question_specific_fact_gaps(intent, topics)
    next_steps = [
        "मूल RTI आवेदन, डाक/ऑनलाइन प्राप्ति प्रमाण और PIO का पूरा उत्तर साथ रखें।",
        "प्रत्येक लागू शर्त और अपवाद को अपने वास्तविक तथ्यों से अलग-अलग मिलाएँ।",
        "नीचे दिए स्रोत लिंक खोलकर मूल निर्णय, संबंधित अनुच्छेद और बाद के निर्णय जाँचें।",
    ]
    if not current and candidate_evidence:
        next_steps.insert(
            0,
            "मशीन-निकाले candidate अंशों को मूल निर्णय से मिलाकर पक्षों के तर्क, "
            "न्यायालय/आयोग की finding और operative order अलग पहचानें; candidate को "
            "अपने-आप ratio या binding precedent न मानें।",
        )

    return {
        "answer_status": status,
        "direct_answer": direct_answer,
        "legal_basis": legal_basis,
        "case_positions": positions,
        "candidate_case_positions": candidate_case_positions,
        "candidate_citations": _dedupe_citations(candidate_citations),
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




def _build_direct_answer(principles: list[dict[str, Any]]) -> str:
    """Render a conclusion only from current, verified ratio records."""
    usable = [
        item for item in principles
        if item.get("legal_status") == "verified_current"
        and item.get("principle_type") == "ratio_decidendi"
        and str(item.get("principle_text") or "").strip()
    ]
    if not usable:
        return (
            "सीधा जवाब: सत्यापित वर्तमान ratio का रिकॉर्ड मिला है, लेकिन उसमें "
            "उद्धृत करने योग्य सिद्धांत-पाठ उपलब्ध नहीं है। इसलिए कानूनी निष्कर्ष "
            "देना अभी सुरक्षित नहीं है।"
        )

    primary = usable[0]
    principle = str(primary["principle_text"]).strip()
    source = str(primary.get("source_title") or primary.get("authority") or "सत्यापित निर्णय")
    scope = str(primary.get("scope") or "").strip()
    conditions = [str(value).strip() for value in (primary.get("conditions") or []) if str(value).strip()]
    exceptions = [str(value).strip() for value in (primary.get("exceptions") or []) if str(value).strip()]

    parts = ["सीधा जवाब: उपलब्ध मानव-सत्यापित वर्तमान ratio के अनुसार, " + principle]
    if scope:
        parts.append("इस सिद्धांत का दर्ज दायरा: " + scope)
    if conditions:
        parts.append("इसका प्रयोग इन शर्तों के अधीन है: " + "；".join(conditions[:3]))
    if exceptions:
        parts.append("दर्ज अपवाद/सीमाएँ: " + "；".join(exceptions[:3]))
    parts.append(
        "यह निष्कर्ष " + source + " के सत्यापित ratio record पर आधारित है; "
        "प्रश्न के तथ्यों से उसका मिलान अलग से आवश्यक है।"
    )
    if len(usable) > 1:
        parts.append(
            f"अतिरिक्त {len(usable) - 1} सत्यापित ratio record भी उपलब्ध हैं; "
            "उनके संभावित भिन्न/पूरक प्रभाव को साथ में पढ़ना होगा।"
        )
    return " ".join(parts)[:2400]


def _candidate_kind_and_review_status(item: dict[str, Any]) -> tuple[str | None, str | None]:
    """Keep legacy label handling identical across candidate display and citation paths."""
    kind = item.get("kind")
    review_status = item.get("review_status")
    if not kind:
        legacy_label = str(item.get("label") or "")
        if "मुद्दे" in legacy_label:
            kind = "issue_candidate"
        elif "आदेश" in legacy_label:
            kind = "operative_order_candidate"
        elif "धारा" in legacy_label:
            kind = "section_reference_candidate"
        if kind:
            review_status = "human_review_required"
    return kind, review_status


def _candidate_pinpoint_references(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Expose extracted para/page locations separately from verified legal pinpoints."""
    candidates = document.get("decision_candidates") or document.get("key_paragraphs") or []
    references: list[dict[str, Any]] = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        kind, review_status = _candidate_kind_and_review_status(item)
        if review_status != "human_review_required":
            continue
        paragraph = item.get("paragraph_reference")
        page = item.get("page_reference")
        if not paragraph and not page:
            continue
        reference: dict[str, Any] = {
            "source_url": item.get("source_url") or document.get("canonical_url"),
            "review_status": "human_review_required",
        }
        if kind:
            reference["kind"] = kind
        if paragraph:
            reference["paragraph_reference"] = paragraph
        if page:
            reference["page_reference"] = page
        if item.get("excerpt"):
            reference["excerpt"] = item["excerpt"]
        if item.get("label"):
            reference["label"] = item["label"]
        references.append(reference)
    return _merge_unique_dicts(references)


def _candidate_case_positions(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Expose short extracted party/finding/order passages as review candidates only."""
    labels = {
        "applicant_argument_candidate": "applicant_argument_candidates",
        "pio_argument_candidate": "pio_argument_candidates",
        "finding_candidate": "court_or_commission_finding_candidates",
        "outcome_candidate": "outcome_candidates",
        "operative_order_candidate": "operative_order_candidates",
        "issue_candidate": "issue_candidates",
        "section_reference_candidate": "section_reference_candidates",
    }
    results = []
    for document in evidence:
        candidates = document.get("decision_candidates") or document.get("key_paragraphs") or []
        grouped: dict[str, list[dict[str, Any]]] = {name: [] for name in labels.values()}
        for item in candidates:
            if not isinstance(item, dict):
                continue
            kind, review_status = _candidate_kind_and_review_status(item)
            if review_status != "human_review_required":
                continue
            target = labels.get(kind)
            if not target:
                continue
            grouped[target].append({
                "excerpt": item.get("excerpt"),
                "paragraph_reference": item.get("paragraph_reference"),
                "page_reference": item.get("page_reference"),
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


def _merge_unique_dicts(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, dict):
            continue
        key = repr(sorted((str(name), repr(item)) for name, item in value.items()))
        if key in seen:
            continue
        seen.add(key)
        merged.append(value)
    return merged


def _dedupe_citations(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    result: list[dict[str, Any]] = []
    for value in values:
        key = (str(value.get("document_id") or ""), str(value.get("url") or ""))
        existing = by_key.get(key)
        if existing is None:
            existing = dict(value)
            existing["pinpoint"] = _merge_unique_dicts(existing.get("pinpoint") or [])
            if existing.get("pinpoint_candidates"):
                existing["pinpoint_candidates"] = _merge_unique_dicts(
                    existing["pinpoint_candidates"]
                )
            by_key[key] = existing
            result.append(existing)
            continue

        # One decision may support a verified principle and also have review-only
        # extracted snippets. Preserve both without merging candidate refs into
        # the verified pinpoint list.
        existing["pinpoint"] = _merge_unique_dicts(
            (existing.get("pinpoint") or []) + (value.get("pinpoint") or [])
        )
        candidate_refs = (
            (existing.get("pinpoint_candidates") or [])
            + (value.get("pinpoint_candidates") or [])
        )
        if candidate_refs:
            existing["pinpoint_candidates"] = _merge_unique_dicts(candidate_refs)
        for field in ("title", "authority", "decision_date", "url"):
            if not existing.get(field) and value.get(field):
                existing[field] = value[field]
    return result
