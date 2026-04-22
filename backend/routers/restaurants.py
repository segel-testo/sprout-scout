import asyncio
import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from services.cache import get_cached, set_cached
from services.overpass import fetch_restaurants
from services.scanner import scan_restaurant

router = APIRouter()

SCAN_CONCURRENCY = 8
SCAN_PER_RESTAURANT_TIMEOUT = 25
SCAN_RESTAURANT_CAP = 30


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


@router.get("/restaurants/scan")
async def scan_zip(zip_code: str, request: Request, country: str = "AT"):
    if country != "AT":
        raise HTTPException(status_code=400, detail="Only Austria (AT) is supported currently.")
    if not zip_code.isdigit() or len(zip_code) != 4:
        raise HTTPException(status_code=400, detail="Austrian zip codes must be 4 digits.")

    cache_key = f"{country}_{zip_code}"
    cached = get_cached(cache_key)
    if cached:
        restaurants = cached["restaurants"]
    else:
        restaurants = await fetch_restaurants(zip_code)
        set_cached(cache_key, {"zip_code": zip_code, "country": country, "restaurants": restaurants})

    total_available = len(restaurants)
    batch = restaurants[:SCAN_RESTAURANT_CAP]
    total = len(batch)

    async def event_stream():
        yield _sse("start", {"total": total, "total_available": total_available, "capped": total_available > total})

        if total == 0:
            yield _sse("done", {"scanned": 0, "total": 0})
            return

        semaphore = asyncio.Semaphore(SCAN_CONCURRENCY)

        async def scan_one(r):
            async with semaphore:
                try:
                    return ("ok", r, await asyncio.wait_for(
                        scan_restaurant(r["id"], r.get("website", ""), r),
                        timeout=SCAN_PER_RESTAURANT_TIMEOUT,
                    ))
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    return ("error", r, str(e))

        tasks = [asyncio.create_task(scan_one(r)) for r in batch]
        scanned = 0
        try:
            for task in asyncio.as_completed(tasks):
                if await request.is_disconnected():
                    break
                kind, r, payload = await task
                scanned += 1
                if kind == "ok" and payload.get("dishes"):
                    yield _sse("restaurant", {"restaurant": r, "scan": payload})
                elif kind == "error":
                    yield _sse("error", {"restaurant_id": r["id"], "reason": payload})
                yield _sse("progress", {"scanned": scanned, "total": total})
            yield _sse("done", {"scanned": scanned, "total": total})
        finally:
            for t in tasks:
                if not t.done():
                    t.cancel()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.get("/restaurants/{restaurant_id}/vegan")
async def get_vegan_dishes(
    restaurant_id: str,
    website: str = "",
    name: str = "",
    address: str = "",
    osm_type: str = "node",
    osm_diet_vegan: str | None = None,
):
    restaurant = {
        "name": name,
        "address": address,
        "website": website,
        "osm_type": osm_type,
        "osm_diet_vegan": osm_diet_vegan,
    }
    return await scan_restaurant(restaurant_id, website, restaurant)
