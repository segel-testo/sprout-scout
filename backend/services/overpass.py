import httpx

OVERPASS_URL = "https://overpass-api.de/api/interpreter"


async def fetch_restaurants(zip_code: str) -> list[dict]:
    query = f"""
    [out:json][timeout:25];
    area["ISO3166-1"="AT"]["admin_level"="2"]->.country;
    nwr["amenity"="restaurant"]["addr:postcode"="{zip_code}"](area.country);
    out body;
    """
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(OVERPASS_URL, data={"data": query})
        response.raise_for_status()
        data = response.json()

    restaurants = []
    for element in data.get("elements", []):
        tags = element.get("tags", {})
        restaurants.append({
            "id": str(element["id"]),
            "name": tags.get("name", "Unknown"),
            "address": _build_address(tags),
            "website": tags.get("website") or tags.get("contact:website", ""),
            "phone": tags.get("phone") or tags.get("contact:phone", ""),
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
