import io
import re
from urllib.parse import urljoin, urlparse, parse_qs, unquote

import httpx
import pdfplumber
from bs4 import BeautifulSoup

from services.extractor import extract_vegan_dishes


PDF_VIEWER_PARAMS = ("file", "url", "src")


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
            dishes += _scan_pdf_bytes(content, source=pdf_url)
    return dishes


async def scan_url(url: str, client: httpx.AsyncClient) -> list[dict]:
    try:
        content = await _fetch_pdf(url, client)
    except Exception:
        return []
    if not content:
        return []
    return _scan_pdf_bytes(content, source=url)


async def _fetch_pdf(url: str, client: httpx.AsyncClient) -> bytes | None:
    if not _looks_like_pdf_url(url):
        try:
            head = await client.head(url)
            content_type = head.headers.get("content-type", "").lower()
            if "pdf" not in content_type:
                return None
        except Exception:
            return None
    response = await client.get(url)
    response.raise_for_status()
    if "pdf" not in response.headers.get("content-type", "").lower() and not _looks_like_pdf_url(url):
        return None
    return response.content


def _scan_pdf_bytes(content: bytes, source: str) -> list[dict]:
    dishes: list[dict] = []
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            full_text = "\n".join((page.extract_text() or "") for page in pdf.pages)
    except Exception:
        return []
    return extract_vegan_dishes(full_text, source=source)
