import httpx

OVERPASS_URL = "https://overpass-api.de/api/interpreter"


FOOD_AMENITIES = ["restaurant", "cafe", "fast_food", "pub", "bar", "biergarten", "food_court", "ice_cream"]


async def fetch_restaurants(zip_code: str) -> list[dict]:
    amenity_regex = "|".join(FOOD_AMENITIES)
    query = f"""
    [out:json][timeout:25];
    area["ISO3166-1"="AT"]["admin_level"="2"]->.country;
    nwr["amenity"~"^({amenity_regex})$"]["addr:postcode"="{zip_code}"](area.country);
    out body;
    """
    headers = {
        "User-Agent": "SproutScout/0.1 (https://github.com/valroeck/sprout-scout)",
        "Accept": "application/json",
    }
    async with httpx.AsyncClient(timeout=30, headers=headers) as client:
        response = await client.post(OVERPASS_URL, data={"data": query})
        response.raise_for_status()
        data = response.json()

    restaurants = []
    for element in data.get("elements", []):
        tags = element.get("tags", {})
        restaurants.append({
            "id": str(element["id"]),
            "osm_type": element.get("type", "node"),
            "name": tags.get("name", "Unknown"),
            "amenity": tags.get("amenity"),
            "address": _build_address(tags),
            "website": tags.get("website") or tags.get("contact:website", ""),
            "phone": tags.get("phone") or tags.get("contact:phone", ""),
            "osm_diet_vegan": tags.get("diet:vegan") or None,
        })

    return restaurants


def _build_address(tags: dict) -> str:
    parts = [
        tags.get("addr:street", ""),
        tags.get("addr:housenumber", ""),
        tags.get("addr:postcode", ""),
        tags.get("addr:city", ""),
    ]
    return " ".join(p for p in parts if p)
