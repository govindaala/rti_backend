# Repository path: rti_backend/app/services/legal_decision_analyzer.py
"""Conservative local/extractive analysis of court text; never substitutes for legal review."""
from __future__ import annotations

import re
from typing import Any

RTI_ACT_HINTS = (
    "right to information act",
    "rti act",
    "सूचना का अधिकार अधिनियम",
    "सूचना का अधिकार अधिनियम, 2005",
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


def _clean_excerpt(value: str, limit: int = 700) -> str:
    return re.sub(r"\s+", " ", value).strip()[:limit]


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in SENTENCE_SPLIT.split(text) if len(part.strip()) >= 35]


def _explicit_rti_sections(text: str) -> list[str]:
    """Only keep section citations with nearby explicit RTI Act context."""
    found: list[str] = []
    lower = text.lower()
    for match in SECTION_PATTERN.finditer(text):
        start, end = max(0, match.start() - 140), min(len(text), match.end() + 180)
        context = lower[start:end]
        if any(hint in context for hint in RTI_ACT_HINTS):
            section = re.sub(r"\s+", "", match.group(1))
            normalized = f"धारा {section}"
            if normalized not in found:
                found.append(normalized)
    return found[:20]


def analyze_decision_text(text: str | None, source_url: str) -> dict[str, Any]:
    """Return traceable excerpts and explicitly cited RTI sections, not invented legal conclusions."""
    content = (text or "").strip()
    if not content:
        return {
            "analysis_status": "text_unavailable",
            "analysis_method": "rule_based_extractive_v1",
            "learned_summary": None,
            "legal_issue": None,
            "holding": None,
            "cited_sections": [],
            "key_paragraphs": [],
            "analyzed": False,
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
    # Later operative paragraphs are more likely to contain the disposition.
    holding = holding_sentences[-1] if holding_sentences else None
    sections = _explicit_rti_sections(content)

    key_paragraphs: list[dict[str, str]] = []
    if issue:
        key_paragraphs.append({
            "label": "संभावित कानूनी मुद्दे का मूल पाठ",
            "excerpt": _clean_excerpt(issue),
            "source_url": source_url,
        })
    for sentence in holding_sentences[-3:]:
        excerpt = _clean_excerpt(sentence)
        if not any(item["excerpt"] == excerpt for item in key_paragraphs):
            key_paragraphs.append({
                "label": "आदेश/निष्कर्ष का संभावित मूल अंश",
                "excerpt": excerpt,
                "source_url": source_url,
            })
    if sections:
        key_paragraphs.append({
            "label": "RTI Act का स्पष्ट संदर्भ",
            "excerpt": "पाठ के निकटवर्ती संदर्भ में स्पष्ट रूप से मिले: " + ", ".join(sections),
            "source_url": source_url,
        })

    parts = [
        "यह स्थानीय नियम-आधारित प्रारंभिक निष्कर्ष है; यह जनरेटिव AI या कानूनी सत्यापन नहीं है।"
    ]
    if sections:
        parts.append("RTI Act की स्पष्ट संदर्भित धाराएँ: " + ", ".join(sections) + ".")
    else:
        parts.append("उपलब्ध पाठ में RTI Act के साथ स्पष्ट रूप से जुड़ी धारा की पुष्टि नहीं हुई।")
    if issue:
        parts.append("संभावित मुद्दे का उद्धरण: " + _clean_excerpt(issue, 260))
    if holding:
        parts.append("आदेश/निष्कर्ष का संभावित उद्धरण: " + _clean_excerpt(holding, 260))
    if not issue and not holding:
        parts.append("पाठ में पहचाने जाने योग्य मुद्दा/आदेश संकेत नहीं मिले; मूल दस्तावेज़ पढ़कर जाँच आवश्यक है.")

    return {
        "analysis_status": "human_review_required",
        "analysis_method": "rule_based_extractive_v1",
        "learned_summary": " ".join(parts),
        "legal_issue": _clean_excerpt(issue) if issue else None,
        "holding": _clean_excerpt(holding) if holding else None,
        "cited_sections": sections,
        "key_paragraphs": key_paragraphs[:6],
        "analyzed": True,
    }
