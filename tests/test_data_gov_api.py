# रिपॉजिटरी पथ: rti_backend/tests/test_data_gov_api.py
"""data.gov.in API credentials remain request-time secrets, not stored source URLs."""

import pytest

from app.services import crawler


def test_data_gov_api_url_adds_key_and_json_options_without_mutating_source(monkeypatch):
    monkeypatch.setattr(crawler, "settings", type("Settings", (), {
        "data_gov_api_key": "test-secret-key",
        "data_gov_api_page_limit": 250,
    })())
    source_url = "https://api.data.gov.in/resource/12345678-abcd-1234-abcd-123456789abc"

    request_url = crawler.build_data_gov_request_url(source_url)

    assert "test-secret-key" not in source_url
    assert "api-key=test-secret-key" in request_url
    assert "format=json" in request_url
    assert "limit=250" in request_url
    assert "test-secret-key" not in source_url


def test_data_gov_api_url_requires_server_side_key(monkeypatch):
    monkeypatch.setattr(crawler, "settings", type("Settings", (), {
        "data_gov_api_key": None,
        "data_gov_api_page_limit": 100,
    })())

    with pytest.raises(ValueError, match="DATA_GOV_API_KEY"):
        crawler.build_data_gov_request_url("https://api.data.gov.in/resource/12345678-abcd")


def test_non_data_gov_urls_are_not_modified(monkeypatch):
    monkeypatch.setattr(crawler, "settings", type("Settings", (), {
        "data_gov_api_key": None,
        "data_gov_api_page_limit": 100,
    })())
    url = "https://cic.gov.in/rti_act"

    assert crawler.build_data_gov_request_url(url) == url
