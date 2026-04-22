from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


def is_foodora_url(url: str) -> bool:
    if not url:
        return False
    host = urlparse(url).hostname or ""
    return host.endswith("foodora.at") or host.endswith("foodora.com") or host.endswith("mjam.net")


def find_foodora_link(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        if is_foodora_url(a["href"]):
            return a["href"]
    return None


async def scan(url: str, client: httpx.AsyncClient) -> list[dict]:
    # Foodora/mjam SSR HTML does not contain the menu — it loads via XHR after
    # page load. The relevant API requires geo coords + auth headers and returns
    # 403 to anonymous httpx clients. A working adapter needs either playwright
    # (out of scope) or reverse-engineered API auth. Stub returns empty so the
    # orchestrator falls through; the URL is preserved so the frontend can link
    # the user out to foodora directly.
    return []
