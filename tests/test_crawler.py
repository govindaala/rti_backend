# रिपॉजिटरी पथ: rti_backend/tests/test_crawler.py
"""Crawler URL policy और redirect सुरक्षा के परीक्षण."""

import pytest

from app.services.crawler import _safe_url, extract_html_text


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


def test_html_extraction_removes_scripts_styles_and_normalizes_whitespace() -> None:
    """Extracted legal text must not contain scripts, styles, or HTML tags."""
    result = extract_html_text(
        "<html><style>.hidden { display:none }</style>"
        "<body><h1>RTI Act</h1><script>alert('x')</script>"
        "<p>Section   6(1)   provides information.</p></body></html>"
    )
    assert result == "RTI Act Section 6(1) provides information."
    assert "alert" not in result
    assert "display:none" not in result
