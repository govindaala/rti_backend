"""Default official-source catalogue for Indian RTI legal research.

URLs are seed/discovery entry points, not guarantees that every decision is publicly
available or crawlable. Review domain ownership and robots/terms before crawling.
"""
from __future__ import annotations

DEFAULT_SOURCE_CATALOG: tuple[dict[str, str], ...] = (
    {"name": "Central Information Commission — Decisions", "category": "information_commission", "jurisdiction": "central", "url": "https://cic.gov.in/"},
    {"name": "Central Information Commission — State Commission directory", "category": "directory", "jurisdiction": "central", "url": "https://www.cic.gov.in/links-to-state-information-commissions"},
    {"name": "Department of Personnel and Training — RTI portal", "category": "law_and_guidance", "jurisdiction": "central", "url": "https://rti.dopt.gov.in/"},
    {"name": "India Code — RTI Act, 2005", "category": "legislation", "jurisdiction": "central", "url": "https://www.indiacode.nic.in/"},
    {"name": "Supreme Court of India", "category": "court", "jurisdiction": "supreme_court", "url": "https://www.sci.gov.in/"},
    {"name": "Supreme Court e-Committee — High Court directory", "category": "directory", "jurisdiction": "all_high_courts", "url": "https://ecommitteesci.gov.in/high-courts/"},
    {"name": "Madhya Pradesh High Court", "category": "court", "jurisdiction": "madhya_pradesh", "url": "https://mphc.gov.in/"},
    {"name": "RTI Act and Rules — CIC", "category": "legislation", "jurisdiction": "central", "url": "https://cic.gov.in/rti_act"},
    {"name": "State Information Commissions — official CIC directory", "category": "information_commission_directory", "jurisdiction": "states_and_union_territories", "url": "https://www.cic.gov.in/links-to-state-information-commissions"},
)

# Official catalogue pages are preferred to stale hard-coded lists of every court URL.
# The linked directory is the discovery source for the current High Court roster.
RELATED_LAW_DISCOVERY: tuple[dict[str, str], ...] = (
    {"name": "Right to Information Act, 2005", "url": "https://www.indiacode.nic.in/"},
    {"name": "RTI Rules, 2012 and 2019", "url": "https://cic.gov.in/rti_act"},
    {"name": "Digital Personal Data Protection Act, 2023 (potentially relevant; check current commencement and amendments)", "url": "https://www.indiacode.nic.in/"},
    {"name": "Official Gazette of India — notifications and amendments", "url": "https://egazette.gov.in/"},
    {"name": "India Code — central acts, rules and amendments", "url": "https://www.indiacode.nic.in/"},
)

def catalog_urls() -> tuple[str, ...]:
    """Return unique seed URLs suitable for an operator-reviewed initial import."""
    return tuple(dict.fromkeys(item["url"] for item in DEFAULT_SOURCE_CATALOG))
