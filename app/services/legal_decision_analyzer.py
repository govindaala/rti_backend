# Repository path: rti_backend/app/services/legal_decision_analyzer.py
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
SECTION_PATTERN = re.compile(
    r"(?i)\b(?:section|sec\.?|s\.?|धारा)\s*"
    r"(\d{1,2}(?:\s*\(\s*[a-zA-Z0-9]+\s*\))*)"
)
SENTENCE_SPLIT = re.compile(r"(?<=[.!?।])\s+|\n+")


def _clean_excerpt(value: str, limit: int = 280) -> str:
    """Return a short traceable fragment; never use an entire article as a summary."""
    return re.sub(r"\s+", " ", value).strip()[:limit]


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in SENTENCE_SPLIT.split(text) if len(part.strip()) >= 35]


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


def analyze_decision_text(text: str | None, source_url: str) -> dict[str, Any]:
    """Build a compact review record; do not claim this is AI training or a verified holding."""
    content = (text or "").strip()
    if not content:
        return {
            "analysis_status": "text_unavailable",
            "analysis_method": "rule_based_structured_v2",
            "learned_summary": None, "legal_issue": None, "holding": None,
            "cited_sections": [], "key_paragraphs": [], "analyzed": False,
        }

    sentences = _sentences(content)
    issue = next(
        (sentence for sentence in sentences if any(hint in sentence.lower() for hint in ISSUE_HINTS)),
        None,
    )
    holding_sentences = [
        sentence for sentence in sentences
        if any(hint in sentence.lower() for hint in HOLDING_HINTS)
    ]
    holding = holding_sentences[-1] if holding_sentences else None
    sections = _explicit_rti_sections(content)

    # Short, attributable fragments are retained separately for reviewer verification.
    key_paragraphs: list[dict[str, str]] = []
    if issue:
        key_paragraphs.append({
            "label": "मुद्दे की पहचान हेतु छोटा स्रोत-अंश",
            "excerpt": _clean_excerpt(issue, 220), "source_url": source_url,
        })
    for sentence in holding_sentences[-2:]:
        excerpt = _clean_excerpt(sentence, 220)
        if not any(item["excerpt"] == excerpt for item in key_paragraphs):
            key_paragraphs.append({
                "label": "आदेश-संकेत की जाँच हेतु छोटा स्रोत-अंश",
                "excerpt": excerpt, "source_url": source_url,
            })
    if sections:
        key_paragraphs.append({
            "label": "RTI Act धारा-संदर्भ",
            "excerpt": "पाठ में RTI Act के संदर्भ में पहचानी गई धाराएँ: " + ", ".join(sections),
            "source_url": source_url,
        })

    # This is a new metadata-style synopsis, not a reproduction of source sentences.
    parts = ["प्रारंभिक संरचित रिकॉर्ड; मानव समीक्षा आवश्यक।"]
    parts.append(
        "RTI Act के स्पष्ट संदर्भ: " + ", ".join(sections) + "."
        if sections else "RTI Act की किसी धारा का स्पष्ट संदर्भ नियमों से पुष्ट नहीं हुआ।"
    )
    parts.append("मुद्दा-संकेत: " + ("मिला" if issue else "नहीं मिला") + ".")
    parts.append("आदेश/निष्कर्ष-संकेत: " + ("मिला" if holding else "नहीं मिला") + ".")
    parts.append("यह सत्यापित कानूनी सिद्धांत, पक्ष की जीत, या वर्तमान वैधता का निष्कर्ष नहीं है।")
    parts.append("मूल स्रोत: " + source_url)

    return {
        "analysis_status": "human_review_required",
        "analysis_method": "rule_based_structured_v2",
        "learned_summary": " ".join(parts)[:1800],
        "legal_issue": _clean_excerpt(issue, 280) if issue else None,
        "holding": _clean_excerpt(holding, 280) if holding else None,
        "cited_sections": sections, "key_paragraphs": key_paragraphs[:5],
        "analyzed": True,
    }
