# Repository path: rti_backend/app/services/legal_intelligence.py
"""Offline, explainable Hindi/English RTI question understanding and retrieval planning.

No paid API, external model, or generated legal conclusion is used. The engine
classifies intent, expands common legal concepts, runs verified-corpus searches,
and ranks source-backed evidence transparently.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

TOKEN_RE = re.compile(r"[\w\u0900-\u097F]{2,}", re.UNICODE)
SECTION_RE = re.compile(r"(?:धारा|dhara|section|sec\.?|s\.?)[\s-]*(\d+[A-Za-z]?(?:\([0-9A-Za-z]+\))*)", re.IGNORECASE)
STOP_WORDS = {
    "और", "तथा", "क्या", "किस", "किसी", "कैसे", "कब", "है", "हैं", "था",
    "थी", "थे", "को", "की", "का", "के", "से", "पर", "में", "लिए", "द्वारा",
    "मुझे", "मेरा", "मेरी", "बताएं", "बताओ", "करें", "करना", "चाहिए", "होता",
    "this", "that", "with", "from", "have", "has", "what", "when", "where",
    "which", "who", "does", "shall", "will", "would", "could", "should",
    "the", "is", "are", "was", "were", "for", "and", "or", "to", "of", "in",
}
# Each concept is a small bilingual vocabulary, not a claim about legal equivalence.
CONCEPTS: dict[str, tuple[str, ...]] = {
    "personal_information_privacy": ("निजी", "व्यक्तिगत", "निजता", "niji", "vyaktigat", "nijta", "privacy", "personal", "private", "8(1)(j)"),
    "third_party_information": ("तीसरा पक्ष", "तृतीय पक्ष", "third party", "third-party", "धारा 11", "section 11"),
    "delay_and_time_limit": ("देरी", "विलंब", "deri", "vilamb", "samay seema", "समय सीमा", "समय-सीमा", "late", "delay", "time limit", "30 दिन", "48 घंटे"),
    "first_appeal": ("प्रथम अपील", "पहली अपील", "pratham apil", "pehli appeal", "first appeal", "faa", "धारा 19(1)", "section 19(1)"),
    "second_appeal_and_cic": ("द्वितीय अपील", "दूसरी अपील", "second appeal", "cic", "केंद्रीय सूचना आयोग", "धारा 19(3)"),
    "complaint": ("शिकायत", "complaint", "धारा 18", "section 18"),
    "penalty_and_disciplinary_action": ("जुर्माना", "दंड", "jurmana", "dand", "penalty", "fine", "धारा 20", "section 20"),
    "inspection_and_copies": ("निरीक्षण", "अवलोकन", "nirikshan", "pramanit prati", "प्रमाणित प्रति", "प्रतिलिपि", "pratilipi", "inspection", "certified copy", "copy"),
    "fees_and_cost": ("शुल्क", "फीस", "shulk", "fees", "atirikt shulk", "अतिरिक्त शुल्क", "fee", "charges", "cost"),
    "disclosure_and_exemptions": ("सूचना देना", "soochna", "suchna", "jaankari", "जानकारी", "प्रकटीकरण", "अस्वीकृति", "छूट", "rok", "mana", "exemption", "disclosure", "denial", "धारा 8", "dhara 8", "section 8", "धारा 9", "dhara 9", "section 9"),
    "record_search_and_non_availability": ("रिकॉर्ड नहीं", "अभिलेख उपलब्ध", "रिकॉर्ड उपलब्ध", "record not available", "not held", "missing record", "सूचना अस्तित्व में नहीं"),
    "severability_and_partial_disclosure": ("आंशिक", "पृथक्करण", "हटाकर", "severability", "partial disclosure", "धारा 10", "section 10"),
    "life_and_liberty": ("जीवन और स्वतंत्रता", "जीवन एवं स्वतंत्रता", "life and liberty", "48 घंटे"),
    "public_interest": ("लोकहित", "जनहित", "बड़ा लोकहित", "public interest", "larger public interest"),
}

INTENT_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("penalty_or_accountability", ("जुर्माना", "दंड", "jurmana", "dand", "penalty", "fine", "धारा 20", "dhara 20", "section 20")),
    ("appeal_or_remedy", ("अपील", "शिकायत", "apil", "shikayat", "appeal", "complaint", "faa")),
    ("delay_or_deadline", ("देरी", "विलंब", "deri", "vilamb", "कितने दिन", "समय सीमा", "samay seema", "late", "delay", "deadline", "time limit")),
    ("disclosure_or_exemption", ("सूचना देने", "सूचना रोक", "अस्वीकृति", "छूट", "प्रकटीकरण", "disclosure", "denial", "exemption", "8(1)")),
    ("inspection_or_copy", ("निरीक्षण", "प्रमाणित प्रति", "प्रतिलिपि", "inspection", "certified copy")),
    ("fee_or_payment", ("शुल्क", "फीस", "fee", "charges", "payment")),
    ("record_availability", ("रिकॉर्ड", "अभिलेख", "उपलब्ध नहीं", "नष्ट", "record", "not held", "missing")),
)

@dataclass(frozen=True)
class QuestionPlan:
    intent: str
    topics: tuple[str, ...]
    search_queries: tuple[str, ...]
    key_terms: tuple[str, ...]
    guidance: tuple[str, ...]


def _norm(text: str) -> str:
    return " ".join(text.lower().split())


def _contains_phrase(text: str, phrase: str) -> bool:
    return _norm(phrase) in _norm(text)


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text) if t.lower() not in STOP_WORDS]


def understand_question(question: str) -> QuestionPlan:
    """Infer a narrow RTI intent and produce two compact bilingual retrieval passes."""
    text = _norm(question)
    topics = [name for name, phrases in CONCEPTS.items() if any(_contains_phrase(text, p) for p in phrases)]
    intent = "general_rti_question"
    for candidate, phrases in INTENT_RULES:
        if any(_contains_phrase(text, phrase) for phrase in phrases):
            intent = candidate
            break

    raw_terms = list(dict.fromkeys(_tokens(question)))
    section_terms = [match.group(1) for match in SECTION_RE.finditer(question)]
    for section in section_terms:
        raw_terms.extend([section, f"धारा {section}", f"section {section}"])
    expanded: list[str] = []
    for topic in topics:
        phrases = CONCEPTS[topic]
        # Select only short, high-signal phrases; avoid flooding PostgreSQL tsquery.
        for phrase in phrases[:5]:
            expanded.extend(_tokens(phrase))
    key_terms = list(dict.fromkeys(raw_terms + expanded))[:24]

    base_query = " OR ".join(raw_terms[:12])
    concept_query = " OR ".join(list(dict.fromkeys(expanded + section_terms))[:16])
    queries = tuple(q for q in dict.fromkeys((base_query, concept_query)) if q)

    guidance_map = {
        "penalty_or_accountability": ("जाँचें कि PIO की देरी/अस्वीकृति किस वैधानिक कर्तव्य से जुड़ी है।", "धारा 20 के प्रत्येक आवश्यक तत्व, कारण और सुनवाई के अवसर को अलग जाँचें।"),
        "appeal_or_remedy": ("पहले सही उपाय—धारा 18 की शिकायत या धारा 19 की अपील—को प्रश्न के तथ्यों से मिलाएँ।", "समय-सीमा, सक्षम प्राधिकारी, मांगी गई राहत और रिकॉर्ड संलग्नक जाँचें।"),
        "delay_or_deadline": ("आवेदन प्राप्ति, transfer, अतिरिक्त शुल्क सूचना और उत्तर की तारीखों की timeline बनाएँ।", "लागू वैधानिक अवधि और किसी विशेष 48 घंटे वाले प्रावधान की शर्तें अलग जाँचें।"),
        "disclosure_or_exemption": ("PIO द्वारा उद्धृत प्रत्येक exemption की पूरी कसौटी और तथ्यात्मक आधार जाँचें।", "धारा 10 के पृथक्करण और लोकहित के तर्क को अलग-अलग परखें।"),
        "inspection_or_copy": ("माँगी गई राहत—निरीक्षण, प्रमाणित प्रति या नमूना—को मूल आवेदन से मिलाएँ।", "अभिलेख का अस्तित्व, custody और लागू शुल्क नियम जाँचें।"),
        "fee_or_payment": ("शुल्क की गणना, लागू नियम, गरीबी रेखा छूट और देरी के प्रभाव की जाँच करें।", "माँगी गई सूचना की मात्रा और अतिरिक्त शुल्क सूचना की तारीख मिलाएँ।"),
        "record_availability": ("रिकॉर्ड किस लोक प्राधिकरण/शाखा के नियंत्रण में होना चाहिए, यह पहचानें।", "रिकॉर्ड खोज, retention/destruction और transfer के दस्तावेजी प्रमाण जाँचें।"),
        "general_rti_question": ("प्रश्न में मांगी गई सूचना, संबंधित लोक प्राधिकरण और विवादित कार्रवाई पहचानें।", "संबंधित धारा, निर्णय के तथ्य और उपलब्ध राहत का मिलान करें।"),
    }
    return QuestionPlan(intent, tuple(topics), queries, tuple(key_terms), guidance_map[intent])


def rank_document(record: dict, plan: QuestionPlan) -> tuple[float, list[str]]:
    """Field-weighted, explainable lexical score; never represented as legal certainty."""
    weights = {
        "title": 5.0, "legal_issue": 4.0, "holding": 4.0,
        "learned_summary": 3.0, "cited_sections": 4.0, "excerpt": 1.0,
    }
    query_terms = set(plan.key_terms)
    matched: set[str] = set()
    score = 0.0
    for field, weight in weights.items():
        value = record.get(field) or ""
        if isinstance(value, (list, tuple)):
            value = " ".join(str(v) for v in value)
        field_terms = set(_tokens(str(value)))
        overlap = query_terms & field_terms
        if overlap:
            matched.update(overlap)
            score += weight * min(1.0, len(overlap) / max(1, min(4, len(query_terms))))
    if not matched:
        return 0.0, []
    coverage = len(matched) / max(1, len(query_terms))
    return round(score + coverage * 5.0, 3), sorted(matched)


def merge_ranked_documents(records: list[dict], plan: QuestionPlan, limit: int) -> list[dict]:
    """Deduplicate search passes and rank the union, preserving only verified rows."""
    unique: dict[str, dict] = {}
    for record in records:
        if record.get("verification_status", "verified") != "verified":
            continue
        key = str(record.get("document_id") or record.get("canonical_url") or "")
        if not key:
            continue
        previous = unique.get(key)
        if previous is None or len(str(record.get("excerpt") or "")) > len(str(previous.get("excerpt") or "")):
            unique[key] = record
    ranked = []
    for record in unique.values():
        score, matched = rank_document(record, plan)
        if score <= 0:
            continue
        ranked.append((score, matched, record))
    ranked.sort(key=lambda item: (item[0], item[2].get("decision_date") or ""), reverse=True)
    output = []
    for score, matched, record in ranked[:limit]:
        output.append({**record, "_intelligence_score": score, "_matched_terms": matched})
    return output
