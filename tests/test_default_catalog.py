# रिपॉजिटरी पथ: rti_backend/tests/test_default_catalog.py
"""CIC-first स्रोत सूची के परीक्षण."""

from app.services.default_catalog import DEFAULT_SOURCE_CATALOG, RELATED_LAW_DISCOVERY, catalog_urls


def test_default_catalog_contains_only_cic_first_phase_sources():
    urls = catalog_urls()
    assert set(urls) == {
        "https://cic.gov.in/",
        "https://cic.gov.in/decision",
        "https://cic.gov.in/rti_act",
    }
    assert len(DEFAULT_SOURCE_CATALOG) == 3


def test_related_law_catalog_links_to_primary_sources():
    assert any("indiacode.nic.in" in item["url"] for item in RELATED_LAW_DISCOVERY)
    assert any("egazette.gov.in" in item["url"] for item in RELATED_LAW_DISCOVERY)
    assert all(item["name"] and item["url"].startswith("https://") for item in RELATED_LAW_DISCOVERY)


def test_catalog_urls_are_unique():
    urls = catalog_urls()
    assert len(urls) == len(set(urls))
