"""Conservative structured extraction for RTI legal research; human review remains mandatory."""
from __future__ import annotations

import re
from typing import Any

RTI_ACT_HINTS = (
    "right to information act", "rti act",
    "सूचना का अधिकार अधिनियम", "सूचना का अधिकार अधिनियम, 2005",
)
ISSUE_HINTS = (
    "whether", "question before", "issue for consideration", "the issue is",
    "grievance", "appellant", "applicant", "information sought", "सूचना मांगी",
    "अपीलकर्ता", "आवेदक", "सूचना उपलब्ध", "प्रथम अपील", "द्वितीय अपील",
)
HOLDING_HINTS = (
    "held that", "it is held", "we hold", "appeal is allowed", "appeal is dismissed",
    "appeal stands dismissed", "appeal stands allowed", "is hereby directed",
    "we direct", "accordingly", "therefore", "ordered that", "the commission directs",
    "आदेश दिया जाता", "अपील खारिज", "अपील स्वीकार", "निर्देशित किया जाता",
    "निर्णय लिया", "तदनुसार",
)
APPLICANT_ARGUMENT_HINTS = (
    "appellant submitted", "applicant submitted", "appellant contended",
    "applicant contended", "appellant argued", "applicant argued",
    "on behalf of the appellant", "on behalf of applicant",
    "अपीलकर्ता ने तर्क", "आवेदक ने तर्क", "अपीलकर्ता की ओर से",
    "आवेदक की ओर से", "अपीलकर्ता ने कहा", "आवेदक ने कहा",
)
PIO_ARGUMENT_HINTS = (
    "cpio submitted", "pio submitted", "respondent submitted",
    "respondent contended", "respondent argued", "public information officer submitted",
    "on behalf of the respondent", "लोक सूचना अधिकारी ने कहा",
    "जन सूचना अधिकारी ने कहा", "प्रतिवादी ने तर्क", "लोक सूचना अधिकारी की ओर से",
)
FINDING_HINTS = (
    "the commission observes", "commission observed", "the commission finds",
    "we find that", "we are of the view", "it is observed that",
    "it is clear from the record", "the record reveals", "we hold that",
    "आयोग ने पाया", "आयोग का मत", "हम पाते हैं", "यह पाया जाता है",
    "अभिलेख से स्पष्ट", "आयोग का निष्कर्ष",
)
OUTCOME_HINTS = (
    "appeal is allowed", "appeal stands allowed", "appeal is dismissed",
    "appeal stands dismissed", "appeal is partly allowed", "partly allowed",
    "matter is remanded", "case is remanded", "complaint is disposed",
    "appeal is disposed", "appeal is withdrawn", "आंशिक रूप से स्वीकार",
    "अपील स्वीकार", "अपील खारिज", "मामला वापस भेजा जाता",
    "शिकायत निराकृत", "अपील निराकृत",
)
SECTION_PATTERN = re.compile(
    r"(?i)\b(?:section|sec\.?|s\.?|धारा)\s*"
    r"(\d{1,2}(?:\s*\(\s*[a-zA-Z0-9]+\s*\))*)"
)
PARAGRAPH_PATTERN = re.compile(
    r"(?i)\b(?:para(?:graph)?|पैरा)\s*[.:#-]?\s*(\d+[a-z]?)\b"
)
SENTENCE_SPLIT = re.compile(r"(?<=[.!?।])\s+|\n+")


def _clean_excerpt(value: str, limit: int = 280) -> str:
    """Return a short traceable fragment; never use an entire article as a summary."""
    return re.sub(r"\s+", " ", value).strip()[:limit]


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in SENTENCE_SPLIT.split(text) if len(part.strip()) >= 35]


def _sentences_with_pages(text: str) -> list[tuple[str, int | None]]:
    """PDF form-feed boundaries से physical page index जोड़ें; बिना marker page न गढ़ें."""
    if "\f" not in text:
        return [(sentence, None) for sentence in _sentences(text)]
    located: list[tuple[str, int | None]] = []
    for page_number, page_text in enumerate(text.split("\f"), start=1):
        located.extend((sentence, page_number) for sentence in _sentences(page_text))
    return located


def _explicit_rti_sections(text: str) -> list[str]:
    """Only keep section citations with nearby explicit RTI Act context."""
    found: list[str] = []
    lower = text.lower()
    for match in SECTION_PATTERN.finditer(text):
        start, end = max(0, match.start() - 140), min(len(text), match.end() + 180)
        if any(hint in lower[start:end] for hint in RTI_ACT_HINTS):
            normalized = "धारा " + re.sub(r"\s+", "", match.group(1))
            if normalized not in found:
                found.append(normalized)
    return found[:20]


def _paragraph_reference(sentence: str) -> str | None:
    """Return only an explicit paragraph marker; never infer a page/paragraph number."""
    match = PARAGRAPH_PATTERN.search(sentence)
    return f"पैरा {match.group(1)}" if match else None


def _candidate(
    kind: str, label: str, sentence: str, source_url: str,
    page_number: int | None = None,
) -> dict[str, Any]:
    item = {
        "kind": kind,
        "label": label,
        "excerpt": _clean_excerpt(sentence, 220),
        "source_url": source_url,
        "review_status": "human_review_required",
    }
    paragraph = _paragraph_reference(sentence)
    if paragraph:
        item["paragraph_reference"] = paragraph
    if page_number is not None:
        item["page_reference"] = f"PDF पृष्ठ {page_number}"
    return item


def analyze_decision_text(text: str | None, source_url: str) -> dict[str, Any]:
    """Extract review candidates, not legal holdings or verified precedent."""
    content = (text or "").strip()
    if not content:
        return {
            "analysis_status": "text_unavailable",
            "analysis_method": "rule_based_structured_v3",
            "learned_summary": None, "legal_issue": None, "holding": None,
            "cited_sections": [], "key_paragraphs": [], "analyzed": False,
        }

    located_sentences = _sentences_with_pages(content)
    sentences = [sentence for sentence, _page in located_sentences]
    issue_entry = next(
        ((sentence, page) for sentence, page in located_sentences
         if any(hint in sentence.lower() for hint in ISSUE_HINTS)),
        None,
    )
    issue = issue_entry[0] if issue_entry else None
    holding_entries = [
        (sentence, page) for sentence, page in located_sentences
        if any(hint in sentence.lower() for hint in HOLDING_HINTS)
    ]
    holding = holding_entries[-1][0] if holding_entries else None
    sections = _explicit_rti_sections(content)

    # Each category is a searchable review candidate, never a verified legal conclusion.
    candidates: list[dict[str, str]] = []
    if issue_entry:
        candidates.append(_candidate(
            "issue_candidate", "विवादित मुद्दे का संभावित स्रोत-अंश",
            issue_entry[0], source_url, issue_entry[1],
        ))

    for sentence, page_number in located_sentences:
        lower = sentence.lower()
        if any(hint in lower for hint in APPLICANT_ARGUMENT_HINTS):
            candidates.append(_candidate(
                "applicant_argument_candidate", "आवेदक/अपीलकर्ता के तर्क का संभावित अंश",
                sentence, source_url, page_number,
            ))
        if any(hint in lower for hint in PIO_ARGUMENT_HINTS):
            candidates.append(_candidate(
                "pio_argument_candidate", "PIO/प्रतिवादी के तर्क का संभावित अंश",
                sentence, source_url, page_number,
            ))
        if any(hint in lower for hint in FINDING_HINTS):
            candidates.append(_candidate(
                "finding_candidate", "आयोग/न्यायालय की टिप्पणी का संभावित अंश",
                sentence, source_url, page_number,
            ))
        if any(hint in lower for hint in OUTCOME_HINTS):
            candidates.append(_candidate(
                "outcome_candidate", "परिणाम-संकेत; operative order से मिलान आवश्यक",
                sentence, source_url, page_number,
            ))

    for sentence, page_number in holding_entries[-3:]:
        if not any(
            item["excerpt"] == _clean_excerpt(sentence, 220)
            and item["kind"] == "operative_order_candidate"
            for item in candidates
        ):
            candidates.append(_candidate(
                "operative_order_candidate",
                "अंतिम आदेश/निर्देश का संभावित अंश; मानव पुष्टि आवश्यक",
                sentence, source_url, page_number,
            ))

    if sections:
        candidates.append({
            "kind": "section_reference_candidate",
            "label": "RTI Act धारा-संदर्भ; मूल पाठ से सत्यापन आवश्यक",
            "excerpt": "पाठ में RTI Act के संदर्भ में पहचानी गई धाराएँ: " + ", ".join(sections),
            "source_url": source_url,
            "review_status": "human_review_required",
        })

    # Preserve first occurrence while limiting JSONB growth for large decisions.
    unique: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in candidates:
        key = (item["kind"], item["excerpt"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    unique = unique[:16]

    applicant_count = sum(x["kind"] == "applicant_argument_candidate" for x in unique)
    pio_count = sum(x["kind"] == "pio_argument_candidate" for x in unique)
    finding_count = sum(x["kind"] == "finding_candidate" for x in unique)
    outcome_count = sum(x["kind"] == "outcome_candidate" for x in unique)
    parts = ["प्रारंभिक संरचित रिकॉर्ड; मानव समीक्षा आवश्यक।"]
    parts.append(
        "RTI Act के स्पष्ट संदर्भ: " + ", ".join(sections) + "."
        if sections else "RTI Act की किसी धारा का स्पष्ट संदर्भ नियमों से पुष्ट नहीं हुआ।"
    )
    parts.append("मुद्दा-संकेत: " + ("मिला" if issue else "नहीं मिला") + ".")
    parts.append(
        f"पक्ष-तर्क संकेत: आवेदक/अपीलकर्ता {applicant_count}, PIO/प्रतिवादी {pio_count}."
    )
    parts.append(
        f"न्यायिक टिप्पणी संकेत: {finding_count}; परिणाम संकेत: {outcome_count}."
    )
    parts.append(
        "ये केवल खोज/समीक्षा उम्मीदवार हैं; ratio decidendi, पक्ष की जीत, "
        "operative order या वर्तमान वैधता का सत्यापित निष्कर्ष नहीं हैं।"
    )
    parts.append("मूल स्रोत: " + source_url)

    return {
        "analysis_status": "human_review_required",
        "analysis_method": "rule_based_structured_v3",
        "learned_summary": " ".join(parts)[:1800],
        "legal_issue": _clean_excerpt(issue, 280) if issue else None,
        "holding": _clean_excerpt(holding, 280) if holding else None,
        "cited_sections": sections,
        "key_paragraphs": unique,
        "analyzed": True,
    }
