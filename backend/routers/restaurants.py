from fastapi import APIRouter, HTTPException
from services.overpass import fetch_restaurants
from services.scanner import scan_restaurant
from services.cache import get_cached, set_cached

router = APIRouter()


@router.get("/restaurants")
async def get_restaurants(zip_code: str, country: str = "AT"):
    if country != "AT":
        raise HTTPException(status_code=400, detail="Only Austria (AT) is supported currently.")
    if not zip_code.isdigit() or len(zip_code) != 4:
        raise HTTPException(status_code=400, detail="Austrian zip codes must be 4 digits.")

    cache_key = f"{country}_{zip_code}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    restaurants = await fetch_restaurants(zip_code)
    result = {"zip_code": zip_code, "country": country, "restaurants": restaurants}
    set_cached(cache_key, result)
    return result


@router.get("/restaurants/{restaurant_id}/vegan")
async def get_vegan_dishes(restaurant_id: str, website: str = ""):
    cache_key = f"vegan_{restaurant_id}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    dishes = await scan_restaurant(restaurant_id, website)
    set_cached(cache_key, dishes)
    return dishes
