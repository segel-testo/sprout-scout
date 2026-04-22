import hashlib

import httpx

from services.adapters import foodora, generic, lieferando, pdf
from services.cache import get_namespaced, set_namespaced
from services.fallback import no_menu_payload


SCAN_TIMEOUT = 20
USER_AGENT = "Mozilla/5.0 (compatible; SproutScoutBot/0.1; +https://sprout-scout.example)"


async def scan_restaurant(restaurant_id: str, website: str, restaurant: dict | None = None) -> dict:
    cache_key = _cache_key(restaurant_id, website)
    cached = get_namespaced("scan", cache_key)
    if cached is not None:
        return cached

    result = await _scan_uncached(restaurant_id, website, restaurant)
    set_namespaced("scan", cache_key, result)
    return result


async def _scan_uncached(restaurant_id: str, website: str, restaurant: dict | None) -> dict:
    if not website:
        return no_menu_payload(restaurant_id, restaurant)

    headers = {"User-Agent": USER_AGENT, "Accept-Language": "de,en;q=0.8"}
    async with httpx.AsyncClient(timeout=SCAN_TIMEOUT, follow_redirects=True, headers=headers) as client:
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

    try:
        response = await client.get(website)
        response.raise_for_status()
    except Exception:
        return [], None
    html = response.text

    delivery_link: dict | None = None
    if (link := foodora.find_foodora_link(html)):
        delivery_link = _delivery_link("foodora", link)
    elif (link := lieferando.find_lieferando_link(html)):
        delivery_link = _delivery_link("lieferando", link)

    if (dishes := await pdf.scan(html, website, client)):
        return dishes, delivery_link
    if (dishes := await generic.scan(html, website, client)):
        return dishes, delivery_link
    return [], delivery_link


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
