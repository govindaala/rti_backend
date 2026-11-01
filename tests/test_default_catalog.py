from app.services.default_catalog import DEFAULT_SOURCE_CATALOG, RELATED_LAW_DISCOVERY, catalog_urls


def test_default_catalog_has_central_rti_sources_and_all_india_directories():
    urls = catalog_urls()
    assert "https://cic.gov.in/rti_act" in urls
    assert "https://www.cic.gov.in/links-to-state-information-commissions" in urls
    assert "https://ecommitteesci.gov.in/high-courts/" in urls
    assert "https://www.sci.gov.in/" in urls
    assert len(DEFAULT_SOURCE_CATALOG) >= 8


def test_related_law_catalog_links_to_primary_sources():
    assert any("indiacode.nic.in" in item["url"] for item in RELATED_LAW_DISCOVERY)
    assert any("egazette.gov.in" in item["url"] for item in RELATED_LAW_DISCOVERY)
    assert all(item["name"] and item["url"].startswith("https://") for item in RELATED_LAW_DISCOVERY)


def test_catalog_urls_are_unique():
    urls = catalog_urls()
    assert len(urls) == len(set(urls))
