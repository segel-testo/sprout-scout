from urllib.parse import quote_plus


def no_menu_payload(
    restaurant_id: str,
    restaurant: dict | None,
    delivery_link: dict | None = None,
) -> dict:
    name = (restaurant or {}).get("name", "")
    address = (restaurant or {}).get("address", "")
    website = (restaurant or {}).get("website") or ""
    osm_type = (restaurant or {}).get("osm_type", "node")
    osm_diet_vegan = (restaurant or {}).get("osm_diet_vegan")

    query = quote_plus(" ".join(p for p in (name, address) if p) or restaurant_id)
    maps_url = f"https://www.google.com/maps/search/?api=1&query={query}"
    osm_url = f"https://www.openstreetmap.org/{osm_type}/{restaurant_id}"

    links = []
    if website:
        links.append({"label": "Restaurant website", "url": website})
    links.append({"label": "Search on Google Maps", "url": maps_url})
    links.append({"label": "View on OpenStreetMap", "url": osm_url})

    return {
        "restaurant_id": restaurant_id,
        "dishes": [],
        "no_menu": True,
        "fallback_links": links,
        "osm_diet_vegan": osm_diet_vegan,
        "delivery_link": delivery_link,
    }
