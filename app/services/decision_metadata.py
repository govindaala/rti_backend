# Repository path: rti_backend/app/services/decision_metadata.py
"""Conservative metadata extraction; candidates are not legally verified."""
from __future__ import annotations
import re
from datetime import date
from urllib.parse import urlsplit

_MONTHS = {name: number for number, names in enumerate([
    (), ("jan", "january"), ("feb", "february"), ("mar", "march"), ("apr", "april"),
    ("may",), ("jun", "june"), ("jul", "july"), ("aug", "august"),
    ("sep", "sept", "september"), ("oct", "october"), ("nov", "november"),
    ("dec", "december")
]) if number for name in names}

def _parse_date(value: str) -> date | None:
    match = re.search(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b", value)
    if match:
        try: return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError: return None
    match = re.search(r"\b(\d{1,2})[./-](\d{1,2})[./-](20\d{2})\b", value)
    if match:
        try: return date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
        except ValueError: return None
    for pattern, month_group, day_group, year_group in (
        (r"\b(\d{1,2})\s+([A-Za-z]{3,9}),?\s+(20\d{2})\b", 2, 1, 3),
        (r"\b([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(20\d{2})\b", 1, 2, 3),
    ):
        match = re.search(pattern, value)
        if match:
            month = _MONTHS.get(match.group(month_group).lower())
            if month:
                try: return date(int(match.group(year_group)), month, int(match.group(day_group)))
                except ValueError: return None
    return None

def extract_decision_metadata(url: str, title: str | None, text: str | None) -> dict:
    """Extract likely court/date/case number from the title and document header only."""
    host = (urlsplit(url).hostname or "").lower()
    title_text, body = title or "", text or ""
    lower = f"{host} {title_text} {body[:1200]}".lower()
    court = None
    if "cic.gov.in" in host or "central information commission" in lower:
        court = "Central Information Commission (CIC)"
    elif "sci.gov.in" in host or "supreme court of india" in lower:
        court = "Supreme Court of India"
    elif "mphc.gov.in" in host or "madhya pradesh high court" in lower:
        court = "Madhya Pradesh High Court"
    elif "high court" in lower or re.search(r"\bhc\b", host):
        court = "High Court (name requires verification)"
    elif "state information commission" in lower or re.search(r"\bsic\b", host):
        court = "State Information Commission (name requires verification)"
    decision_date = _parse_date(title_text)
    if decision_date is None:
        decision_date = _parse_date("\n".join(body.splitlines()[:18])[:1800])
    pattern = (r"\b(?:W\.P\.?|WP|Writ Petition|Civil Appeal|Criminal Appeal|S\.L\.P\.?|"
               r"Special Leave Petition|Appeal|Complaint|Second Appeal|File No\.?|Case No\.?)"
               r"\s*(?:No\.?\s*)?([A-Z0-9./() -]{2,70}?)(?=\s+(?:of|dated|decided|\bvs?\b|versus)|[,;\n]|$)")
    match = re.search(pattern, f"{title_text}\n{body[:5000]}", re.IGNORECASE)
    case_number = re.sub(r"\s+", " ", match.group(1)).strip(" .,-") if match else None
    if case_number and not 2 <= len(case_number) <= 70: case_number = None
    return {"court_name": court, "decision_date": decision_date, "case_number": case_number}
