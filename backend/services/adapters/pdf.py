import asyncio
import io
import re
from urllib.parse import urljoin, urlparse, parse_qs, unquote

import httpx
import pdfplumber
from bs4 import BeautifulSoup

from services.extractor import extract_vegan_dishes
from services.safe_fetch import safe_get, safe_head


PDF_VIEWER_PARAMS = ("file", "url", "src")
MAX_PDF_BYTES = 10 * 1024 * 1024


def collect_pdf_urls(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    candidates: list[str] = []

    for tag, attr in (("a", "href"), ("iframe", "src"), ("object", "data"), ("embed", "src")):
        for el in soup.find_all(tag):
            value = el.get(attr)
            if not value:
                continue
            absolute = urljoin(base_url, value)
            if _looks_like_pdf_url(absolute):
                candidates.append(absolute)
                continue
            extracted = _extract_pdf_from_viewer(absolute)
            if extracted:
                candidates.append(extracted)

    seen = set()
    deduped = []
    for url in candidates:
        if url not in seen:
            seen.add(url)
            deduped.append(url)
    return deduped


def _looks_like_pdf_url(url: str) -> bool:
    path = urlparse(url).path.lower()
    return path.endswith(".pdf")


def _extract_pdf_from_viewer(url: str) -> str | None:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    for key in PDF_VIEWER_PARAMS:
        if key in qs:
            candidate = unquote(qs[key][0])
            if ".pdf" in candidate.lower():
                return urljoin(url, candidate)
    return None


async def scan(html: str, base_url: str, client: httpx.AsyncClient) -> list[dict]:
    dishes: list[dict] = []
    for pdf_url in collect_pdf_urls(html, base_url):
        try:
            content = await _fetch_pdf(pdf_url, client)
        except Exception:
            continue
        if content:
            dishes += await asyncio.to_thread(_scan_pdf_bytes, content, pdf_url)
    return dishes


async def scan_url(url: str, client: httpx.AsyncClient) -> list[dict]:
    try:
        content = await _fetch_pdf(url, client)
    except Exception:
        return []
    if not content:
        return []
    return await asyncio.to_thread(_scan_pdf_bytes, content, url)


async def _fetch_pdf(url: str, client: httpx.AsyncClient) -> bytes | None:
    if not _looks_like_pdf_url(url):
        head = await safe_head(client, url)
        if head is None:
            return None
        content_type = head.headers.get("content-type", "").lower()
        if "pdf" not in content_type:
            return None
        if _content_length_over_cap(head):
            return None
    response = await safe_get(client, url)
    if response is None or response.status_code >= 400:
        return None
    if "pdf" not in response.headers.get("content-type", "").lower() and not _looks_like_pdf_url(url):
        return None
    if len(response.content) > MAX_PDF_BYTES:
        return None
    return response.content


def _content_length_over_cap(response: httpx.Response) -> bool:
    raw = response.headers.get("content-length")
    if not raw:
        return False
    try:
        return int(raw) > MAX_PDF_BYTES
    except ValueError:
        return False


def _scan_pdf_bytes(content: bytes, source: str) -> list[dict]:
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            full_text = "\n".join((page.extract_text() or "") for page in pdf.pages)
    except Exception:
        return []
    return extract_vegan_dishes(full_text, source=source)
