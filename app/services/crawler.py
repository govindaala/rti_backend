# रिपॉजिटरी पथ: rti_backend/app/services/crawler.py
"""सीमित और allowlist-आधारित सरकारी स्रोत fetch तथा text extraction."""

import hashlib
import io
import re
from html import unescape
from urllib.parse import urlsplit

import httpx
from pypdf import PdfReader

from app.services.source_registry import is_official_source_url

USER_AGENT = "RTI-ResearchBot/0.1 (+respectful public legal research)"


def extract_html_text(html: str) -> str:
    """HTML से script/style हटाकर whitespace-normalized plain text निकालें."""
    cleaned = re.sub(r"(?is)<script[^>]*>.*?</script\s*>", " ", html)
    cleaned = re.sub(r"(?is)<style[^>]*>.*?</style\s*>", " ", cleaned)
    cleaned = re.sub(r"(?is)<noscript[^>]*>.*?</noscript\s*>", " ", cleaned)
    without_tags = re.sub(r"(?s)<[^>]+>", " ", cleaned)
    return unescape(re.sub(r"\s+", " ", without_tags)).strip()


def _safe_url(url: str) -> str:
    """केवल HTTPS allowlisted hostname और सामान्य web ports स्वीकार करें."""
    parsed = urlsplit(url)
    if not is_official_source_url(url):
        raise ValueError("URL is outside the official HTTPS source allowlist")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("URL credentials and custom ports are not allowed")
    return url


def fetch_document(
    url: str,
    timeout_seconds: int = 20,
    max_bytes: int = 12_000_000,
) -> dict:
    """Redirect follow किए बिना सीमित bytes fetch करें; redirect को अलग review चाहिए."""
    safe_url = _safe_url(url)
    with (
        httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=False,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/pdf"},
        ) as client,
        client.stream("GET", safe_url) as response,
    ):
        if response.status_code in (301, 302, 303, 307, 308):
            raise ValueError("Redirect requires manual source review")
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").split(";")[0].lower()
        if content_type not in ("application/pdf", "text/html", "application/xhtml+xml"):
            raise ValueError("Unsupported content type")
        body = bytearray()
        for chunk in response.iter_bytes():
            body.extend(chunk)
            if len(body) > max_bytes:
                raise ValueError("Document exceeds configured size limit")

    raw = bytes(body)
    if content_type == "application/pdf":
        reader = PdfReader(io.BytesIO(raw), strict=False)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        pages = len(reader.pages)
        kind = "pdf"
    else:
        text = extract_html_text(raw.decode("utf-8", errors="replace"))
        pages = None
        kind = "html"

    return {
        "final_url": safe_url,
        "content_type": content_type,
        "document_type": kind,
        "text": text[:2_000_000],
        "page_count": pages,
        "content_sha256": hashlib.sha256(raw).hexdigest(),
    }
