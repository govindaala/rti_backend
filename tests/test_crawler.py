# रिपॉजिटरी पथ: rti_backend/tests/test_crawler.py
"""Crawler URL policy और redirect सुरक्षा के परीक्षण."""

import pytest

from app.services.crawler import (
    _safe_url,
    classify_document_type,
    discover_legal_links,
    extraction_status_for_text,
    extract_html_text,
)


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


def test_discover_legal_links_accepts_official_hosts_and_pagination_but_rejects_untrusted_hosts() -> None:
    """Legal PDFs and judgment paths are discovered; off-domain links are excluded."""
    html = (
        '<a href="/judgments/2024/abc.pdf">PDF</a>'
        '<a href="/orders/123">Order</a>'
        '<a href="https://example.com/judgment.pdf">External</a>'
        '<a href="javascript:alert(1)">Bad</a>'
        '<a href="/download?id=7">Judgment No. 7</a>'
        '<a href="https://dsscic.nic.in/rti-request/view-pdf-data/123">Official hosted PDF</a>'
        '<a href="?page=2">Next page</a>'
        '<a href="/about">Unrelated</a>'
    )
    links = discover_legal_links(html, "https://cic.gov.in/", limit=10)
    assert links == [
        "https://cic.gov.in/judgments/2024/abc.pdf",
        "https://cic.gov.in/orders/123",
        "https://cic.gov.in/download?id=7",
        "https://dsscic.nic.in/rti-request/view-pdf-data/123",
        "https://cic.gov.in/?page=2",
    ]


def test_document_type_is_only_a_preliminary_metadata_label() -> None:
    """URL/title classifier identifies common document types without verification."""
    assert classify_document_type("https://x.gov.in/judgments/1.pdf", "Case") == "judgment"
    assert classify_document_type("https://x.gov.in/files/2.pdf", "Office Order") == "order"
    assert classify_document_type("https://x.gov.in/files/3.pdf", "New PDF") == "unknown"



def test_scanned_pdf_is_marked_for_ocr_instead_of_successful_extraction() -> None:
    assert extraction_status_for_text("  \\n ", "application/pdf") == (True, "needs_ocr")


def test_text_pdf_does_not_require_ocr() -> None:
    assert extraction_status_for_text("Section 6 RTI Act", "application/pdf") == (
        False,
        "extracted",
    )


def test_empty_html_is_not_mislabelled_as_ocr_candidate() -> None:
    assert extraction_status_for_text("", "text/html") == (False, "empty_text")
