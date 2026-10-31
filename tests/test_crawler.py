# रिपॉजिटरी पथ: rti_backend/tests/test_crawler.py
"""Crawler URL policy और redirect सुरक्षा के परीक्षण."""

import pytest

from app.services.crawler import _safe_url


def test_crawler_accepts_official_https_url() -> None:
    assert _safe_url("https://cic.gov.in/") == "https://cic.gov.in/"


@pytest.mark.parametrize(
    "url",
    [
        "http://cic.gov.in/",
        "https://cic.gov.in.attacker.example/",
        "https://user:pass@cic.gov.in/",
        "https://cic.gov.in:8443/",
    ],
)
def test_crawler_rejects_unsafe_urls(url: str) -> None:
    with pytest.raises(ValueError):
        _safe_url(url)
