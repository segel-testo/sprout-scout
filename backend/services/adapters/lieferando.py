from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


def is_lieferando_url(url: str) -> bool:
    if not url:
        return False
    host = urlparse(url).hostname or ""
    return host.endswith("lieferando.at") or host.endswith("lieferando.de") or host.endswith("takeaway.com")


def find_lieferando_link(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        if is_lieferando_url(a["href"]):
            return a["href"]
    return None


async def scan(url: str, client: httpx.AsyncClient) -> list[dict]:
    # Lieferando is behind Cloudflare/Akamai — anonymous GETs return 403. The
    # cw-api.takeaway.com JSON endpoint requires session cookies set by the
    # browser. Same constraint as foodora: needs playwright or reverse-
    # engineered auth. Stub returns empty; URL is preserved for frontend linkout.
    return []
