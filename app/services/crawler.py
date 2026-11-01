# रिपॉजिटरी पथ: rti_backend/app/services/crawler.py
"""सरकारी स्रोतों से सीमित, robots-aware दस्तावेज़ discovery और extraction."""

import hashlib
import io
import re
import xml.etree.ElementTree as ET
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx
from pypdf import PdfReader

from app.services.source_registry import is_official_source_url

USER_AGENT = "RTI-ResearchBot/0.2 (+respectful public legal research)"
LEGAL_PATH_HINTS = (
    "judgment", "judgements", "judgement", "decision", "decisions", "order", "orders",
    "decision", "case", "court", "circular", "notification", "gazette",
    "act", "rules", "regulation", "tribunal", "commission", "cause-list",
)


def extract_html_text(html: str) -> str:
    """HTML से script/style हटाकर whitespace-normalized plain text निकालें."""
    cleaned = re.sub(r"(?is)<script[^>]*>.*?</script\s*>", " ", html)
    cleaned = re.sub(r"(?is)<style[^>]*>.*?</style\s*>", " ", cleaned)
    cleaned = re.sub(r"(?is)<noscript[^>]*>.*?</noscript\s*>", " ", cleaned)
    without_tags = re.sub(r"(?s)<[^>]+>", " ", cleaned)
    return unescape(re.sub(r"\s+", " ", without_tags)).strip()


class _LinkParser(HTMLParser):
    """HTML anchor href collect करें; script text को link नहीं मानें."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._active_href: str | None = None
        self._active_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            self._active_href = dict(attrs).get("href")
            self._active_text = []

    def handle_data(self, data: str) -> None:
        if self._active_href:
            self._active_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._active_href:
            self.links.append((self._active_href, " ".join(self._active_text)))
            self._active_href = None
            self._active_text = []


def discover_legal_links(html: str, base_url: str, limit: int = 25) -> list[str]:
    """उसी official host के PDF और स्पष्ट legal-path links लौटाएँ."""
    parser = _LinkParser()
    parser.feed(html)
    base = urlsplit(base_url)
    seen: set[str] = set()
    results: list[str] = []
    for href, anchor_text in parser.links:
        candidate = urljoin(base_url, href).split("#", 1)[0]
        parsed = urlsplit(candidate)
        if parsed.scheme != "https" or not parsed.hostname:
            continue
        if not is_official_source_url(candidate):
            continue
        path = f"{parsed.path} {parsed.query}".lower()
        searchable = f"{path} {anchor_text}".lower()
        is_pdf = path.endswith(".pdf")
        is_legal_page = any(hint in searchable for hint in LEGAL_PATH_HINTS)
        is_pagination = (
            "page=" in parsed.query.lower()
            or "paged=" in parsed.query.lower()
            or bool(re.search(r"/page/\d+/?$", parsed.path.lower()))
            or bool(re.search(r"\b(next|older|अगला|अगले)\b", searchable))
        )
        if not (is_pdf or is_legal_page or is_pagination):
            continue
        normalized = candidate.rstrip("/")
        if normalized == base_url.rstrip("/") or normalized in seen:
            continue
        seen.add(normalized)
        results.append(normalized)
        if len(results) >= limit:
            break
    return results



def discover_sitemap_links(
    base_url: str, timeout_seconds: int = 20, max_urls: int = 100, max_sitemaps: int = 5
) -> list[str]:
    """Robots-compliant sitemap discovery across allowlisted official government hosts."""
    safe_base = _safe_url(base_url)
    if not _robots_allows(safe_base, timeout_seconds):
        return []
    parsed = urlsplit(safe_base)
    candidates = [f"{parsed.scheme}://{parsed.netloc}/sitemap.xml", f"{parsed.scheme}://{parsed.netloc}/sitemap_index.xml"]
    visited: set[str] = set()
    discovered: list[str] = []
    headers = {"User-Agent": USER_AGENT, "Accept": "application/xml,text/xml,*/*"}
    with httpx.Client(timeout=timeout_seconds, follow_redirects=False, headers=headers) as client:
        while candidates and len(visited) < max_sitemaps and len(discovered) < max_urls:
            sitemap_url = candidates.pop(0)
            if sitemap_url in visited or not is_official_source_url(sitemap_url):
                continue
            visited.add(sitemap_url)
            try:
                response = client.get(sitemap_url)
                if response.status_code != 200 or len(response.content) > 2_000_000:
                    continue
                root = ET.fromstring(response.content)
            except (httpx.HTTPError, ET.ParseError, ValueError):
                continue
            for node in root.iter():
                if node.tag.rsplit("}", 1)[-1].lower() != "loc" or not node.text:
                    continue
                loc = node.text.strip()
                if urlsplit(loc).scheme != "https" or not is_official_source_url(loc):
                    continue
                if loc.lower().endswith(".xml") and len(visited) + len(candidates) < max_sitemaps:
                    candidates.append(loc)
                elif loc not in discovered:
                    discovered.append(loc)
                    if len(discovered) >= max_urls:
                        break
    return discovered


def classify_document_type(url: str, title: str, text: str = "") -> str:
    """URL/title hints से document type का preliminary label दें."""
    sample = f"{url} {title} {text[:1000]}".lower()
    if "judgment" in sample or "judgement" in sample or "निर्णय" in sample:
        return "judgment"
    if "order" in sample or "आदेश" in sample:
        return "order"
    if "circular" in sample or "परिपत्र" in sample:
        return "circular"
    if "notification" in sample or "gazette" in sample or "अधिसूचना" in sample:
        return "notification"
    if any(term in sample for term in (" act ", "/act", " rules ", "/rules", "regulation")):
        return "other"
    return "unknown"


def _safe_url(url: str) -> str:
    """केवल HTTPS allowlisted hostname और सामान्य web ports स्वीकार करें."""
    parsed = urlsplit(url)
    if not is_official_source_url(url):
        raise ValueError("URL is outside the official HTTPS source allowlist")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("URL credentials and custom ports are not allowed")
    return url


def _robots_allows(url: str, timeout_seconds: int) -> bool:
    """robots.txt का पालन करें; policy fetch विफल हो तो सुरक्षित रूप से रुकें."""
    parsed = urlsplit(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        # robots.txt को भी सीमित आकार में पढ़ें; policy fetch विफल हो तो fail closed.
        body = bytearray()
        with httpx.Client(
            timeout=min(timeout_seconds, 8),
            follow_redirects=False,
            headers={"User-Agent": USER_AGENT},
        ) as client, client.stream("GET", robots_url) as response:
            if response.status_code in (404, 410):
                return True
            if response.status_code != 200:
                return False
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > 256_000:
                    return False
        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(bytes(body).decode("utf-8", errors="replace").splitlines())
        return parser.can_fetch(USER_AGENT, url)
    except httpx.HTTPError:
        return False


def fetch_document(
    url: str,
    timeout_seconds: int = 20,
    max_bytes: int = 12_000_000,
) -> dict:
    """Robots policy के बाद redirect रहित सीमित fetch और SHA-256 extraction."""
    safe_url = _safe_url(url)
    if not _robots_allows(safe_url, timeout_seconds):
        raise PermissionError("Robots policy disallows crawling or could not be verified")

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
        pages = len(reader.pages)
        if pages > 500:
            raise ValueError("PDF exceeds the 500-page extraction limit")
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        kind = "pdf"
        title = (reader.metadata.title if reader.metadata else None) or safe_url.rsplit("/", 1)[-1]
    else:
        decoded = raw.decode("utf-8", errors="replace")
        title_match = re.search(r"(?is)<title[^>]*>(.*?)</title\s*>", decoded)
        title = extract_html_text(title_match.group(1)) if title_match else safe_url
        text = extract_html_text(decoded)
        pages = None
        kind = "html"

    return {
        "final_url": safe_url,
        "content_type": content_type,
        "document_type": kind,
        "title": title[:500],
        "text": text[:2_000_000],
        "html": raw.decode("utf-8", errors="replace") if kind == "html" else None,
        "page_count": pages,
        "content_sha256": hashlib.sha256(raw).hexdigest(),
    }
