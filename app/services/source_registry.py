# रिपॉजिटरी पथ: rti_backend/app/services/source_registry.py
"""कानूनी स्रोतों के domain की प्रारंभिक विश्वसनीयता जाँच."""

from urllib.parse import urlsplit

# केवल स्पष्ट रूप से पहचाने गए सरकारी/न्यायिक डोमेन को आधिकारिक चिह्नित करें।
# यह सूची संपूर्ण नहीं है; नए स्रोत Admin समीक्षा के बाद जोड़े जाएँ।
OFFICIAL_DOMAIN_SUFFIXES = (
    "gov.in",
    "nic.in",
    "indiacode.nic.in",
    "sci.gov.in",
    "cic.gov.in",
    "ecourts.gov.in",
)


def is_official_source_url(url: str) -> bool:
    """URL का hostname सरकारी/न्यायिक allowlist में है या नहीं जाँचें."""
    hostname = (urlsplit(url).hostname or "").lower().rstrip(".")
    if not hostname:
        return False

    # suffix match में मूल domain या उसका वास्तविक subdomain ही स्वीकारें।
    return any(
        hostname == suffix or hostname.endswith(f".{suffix}")
        for suffix in OFFICIAL_DOMAIN_SUFFIXES
    )


def source_review_label(url: str) -> str:
    """डोमेन जाँच को अंतिम कानूनी सत्यापन न मानते हुए review label दें."""
    if is_official_source_url(url):
        return "official_domain_unverified_content"
    return "external_source_requires_review"
