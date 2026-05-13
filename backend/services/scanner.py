import hashlib

import httpx
from bs4 import BeautifulSoup

from services.adapters import foodora, generic, lieferando, pdf
from services.cache import aget_namespaced, aset_namespaced
from services.fallback import no_menu_payload
from services.safe_fetch import safe_get


SCAN_TIMEOUT = 20
USER_AGENT = "Mozilla/5.0 (compatible; SproutScoutBot/0.1; +https://sprout-scout.example)"
CLIENT_HEADERS = {"User-Agent": USER_AGENT, "Accept-Language": "de,en;q=0.8"}
CLIENT_LIMITS = httpx.Limits(max_connections=32, max_keepalive_connections=16)


def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=SCAN_TIMEOUT,
        follow_redirects=False,
        headers=CLIENT_HEADERS,
        limits=CLIENT_LIMITS,
    )


async def scan_restaurant(
    restaurant_id: str,
    website: str,
    restaurant: dict | None = None,
    client: httpx.AsyncClient | None = None,
) -> dict:
    cache_key = _cache_key(restaurant_id, website)
    cached = await aget_namespaced("scan", cache_key)
    if cached is not None:
        return cached

    result = await _scan_uncached(restaurant_id, website, restaurant, client)
    await aset_namespaced("scan", cache_key, result)
    return result


async def _scan_uncached(
    restaurant_id: str,
    website: str,
    restaurant: dict | None,
    client: httpx.AsyncClient | None = None,
) -> dict:
    if not website:
        return no_menu_payload(restaurant_id, restaurant)

    if client is None:
        async with make_client() as owned:
            dishes, delivery_link = await _dispatch(website, owned)
    else:
        dishes, delivery_link = await _dispatch(website, client)

    if dishes:
        return {
            "restaurant_id": restaurant_id,
            "dishes": _dedupe(dishes),
            "no_menu": False,
            "delivery_link": delivery_link,
        }

    return no_menu_payload(restaurant_id, restaurant, delivery_link=delivery_link)


async def _dispatch(website: str, client: httpx.AsyncClient) -> tuple[list[dict], dict | None]:
    if foodora.is_foodora_url(website):
        return [], _delivery_link("foodora", website)
    if lieferando.is_lieferando_url(website):
        return [], _delivery_link("lieferando", website)

    response = await safe_get(client, website)
    if response is None or response.status_code >= 400:
        return [], None
    soup, text = _parse(response.text)
    final_url = str(response.url)

    delivery_link: dict | None = None
    if (link := foodora.find_foodora_link(soup)):
        delivery_link = _delivery_link("foodora", link)
    elif (link := lieferando.find_lieferando_link(soup)):
        delivery_link = _delivery_link("lieferando", link)

    if (dishes := await pdf.scan(soup, final_url, client)):
        return dishes, delivery_link
    if (dishes := await generic.scan(text, final_url)):
        return dishes, delivery_link
    if (dishes := await _crawl_menu_links(soup, final_url, client)):
        return dishes, delivery_link
    return [], delivery_link


async def _crawl_menu_links(soup: BeautifulSoup, base_url: str, client: httpx.AsyncClient) -> list[dict]:
    dishes: list[dict] = []
    for link in generic.find_menu_links(soup, base_url):
        response = await safe_get(client, link)
        if response is None or response.status_code >= 400:
            continue
        sub_soup, sub_text = _parse(response.text)
        dishes += await pdf.scan(sub_soup, link, client)
        dishes += await generic.scan(sub_text, link)
    return dishes


def _parse(html: str) -> tuple[BeautifulSoup, str]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup, soup.get_text(separator="\n")


def _delivery_link(platform: str, url: str) -> dict:
    labels = {"foodora": "View menu on foodora", "lieferando": "View menu on Lieferando"}
    return {"platform": platform, "url": url, "label": labels.get(platform, f"View menu on {platform}")}


def _dedupe(dishes: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for d in dishes:
        key = d["name"].strip().lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(d)
    return out


def _cache_key(restaurant_id: str, website: str) -> str:
    digest = hashlib.sha1(website.encode("utf-8")).hexdigest()[:10] if website else "nourl"
    return f"{restaurant_id}_{digest}"
