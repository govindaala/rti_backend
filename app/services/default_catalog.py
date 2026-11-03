# रिपॉजिटरी पथ: rti_backend/app/services/default_catalog.py
"""Default official-source catalogue for Indian RTI legal research.

URLs are seed/discovery entry points, not guarantees that every decision is publicly
available or crawlable. Review domain ownership and robots/terms before crawling.
"""
from __future__ import annotations

# पहले चरण में केवल CIC के आधिकारिक स्रोत queue catalogue में उपलब्ध रखें।
DEFAULT_SOURCE_CATALOG: tuple[dict[str, str], ...] = (
    {"name": "Central Information Commission — Decisions", "category": "information_commission", "jurisdiction": "central", "url": "https://cic.gov.in/"},
    {"name": "Central Information Commission — Decision search landing page (10 September 2016 split)", "category": "information_commission_decisions", "jurisdiction": "central", "url": "https://cic.gov.in/decision"},
    {"name": "RTI Act and Rules — CIC", "category": "legislation", "jurisdiction": "central", "url": "https://cic.gov.in/rti_act"},
)

# आगे के चरणों के कानून-संदर्भ; ये CIC crawl queue का हिस्सा नहीं हैं।
RELATED_LAW_DISCOVERY: tuple[dict[str, str], ...] = (
    {"name": "Right to Information Act, 2005", "url": "https://www.indiacode.nic.in/"},
    {"name": "RTI Rules, 2012 and 2019", "url": "https://cic.gov.in/rti_act"},
    {"name": "Digital Personal Data Protection Act, 2023 (potentially relevant; check current commencement and amendments)", "url": "https://www.indiacode.nic.in/"},
    {"name": "Official Gazette of India — notifications and amendments", "url": "https://egazette.gov.in/"},
    {"name": "India Code — central acts, rules and amendments", "url": "https://www.indiacode.nic.in/"},
)


def catalog_urls() -> tuple[str, ...]:
    """Return unique CIC-only seed URLs for the first ingestion phase."""
    return tuple(dict.fromkeys(item["url"] for item in DEFAULT_SOURCE_CATALOG))
