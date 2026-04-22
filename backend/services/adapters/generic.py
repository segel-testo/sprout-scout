import httpx
from bs4 import BeautifulSoup

from services.extractor import extract_vegan_dishes


async def scan(html: str, base_url: str, client: httpx.AsyncClient) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    return extract_vegan_dishes(text, source=base_url)
