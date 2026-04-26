import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from services.extractor import extract_vegan_dishes


MENU_LINK_PATTERN = re.compile(
    r"(menu|menü|menue|speisekarte|karte|produkte|gerichte|essen|food|drinks|getränke|getraenke)",
    re.IGNORECASE,
)
MAX_CRAWL_LINKS = 4


async def scan(html: str, base_url: str, client: httpx.AsyncClient) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    return extract_vegan_dishes(text, source=base_url)


def find_menu_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    base_host = urlparse(base_url).netloc
    base_norm = base_url.split("#")[0].rstrip("/")
    seen: set[str] = set()
    candidates: list[str] = []
    for a in soup.find_all("a"):
        href = a.get("href")
        if not href:
            continue
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in ("http", "https") or parsed.netloc != base_host:
            continue
        norm = absolute.split("#")[0]
        if norm.rstrip("/") == base_norm:
            continue
        link_text = a.get_text(" ", strip=True)
        if not MENU_LINK_PATTERN.search(f"{parsed.path} {link_text}"):
            continue
        if norm in seen:
            continue
        seen.add(norm)
        candidates.append(norm)
        if len(candidates) >= MAX_CRAWL_LINKS:
            break
    return candidates
