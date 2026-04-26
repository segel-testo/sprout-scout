# Sprout Scout

Find vegan dishes at local restaurants — search by zip code, we scan the menus.

---

## Status

| Area | Status |
|------|--------|
| Project scaffold | done |
| Backend (FastAPI) | done |
| Frontend (Angular) | done |
| Overpass API integration (cafe + restaurant + fast_food + pub + bar + biergarten + food_court + ice_cream) | done |
| Adapter-based scanner (generic + PDF + one-hop menu-link crawl) | done |
| Vegan extractor (negation, legend tables, German + English) | done |
| Delivery-platform link-out (foodora / mjam / lieferando) | done |
| No-menu fallback (Google Maps + OSM links, `diet:vegan` hint) | done |
| File-based cache (restaurant list + scan results, 1 week) | done |
| SSE bulk-scan endpoint | done |
| Angular UI (single auto-scan flow) | done |
| Integration test against 5 real-world URLs | done |
| Deploy frontend (Vercel) | next |
| Deploy backend (Render) | next |

---

## How it works

1. User enters a 4-digit Austrian zip code.
2. Backend queries OpenStreetMap via Overpass for all food-serving venues in that zip — `restaurant`, `cafe`, `fast_food`, `pub`, `bar`, `biergarten`, `food_court`, `ice_cream`.
3. For each website, the **scanner orchestrator** tries adapters in order and stops on the first hit:
   - **Foodora / mjam / lieferando** URLs → link out to the delivery platform (scraping these requires a headless browser; out of scope, so we surface the link instead).
   - **PDF adapter** → finds PDFs via `<a>`, `<iframe>`, `<object>`, `<embed>`, PDF.js viewer URLs, or `content-type: application/pdf`.
   - **Generic HTML adapter** → text extraction on the page.
   - **One-hop menu-link crawl** *(fallback when both adapters return empty on the homepage)* — follows up to 4 same-host links whose path or text matches `menu|menü|menue|speisekarte|karte|produkte|gerichte|essen|food|drinks|getränke`, runs both adapters on each.
4. All extracted text runs through the **vegan extractor**: German + English keyword matching with negation detection, two-pass legend parsing (e.g. `V = vegan` → `V` on a dish line), and "on request" downgrading.
5. If nothing is found, a **no-menu fallback** payload is returned with links to the restaurant website, Google Maps, OSM, and the `diet:vegan` tag if present.
6. Results are cached (1-week TTL, file-based) so repeat searches are near-instant.

---

## Tech Stack

| Layer | Choice |
|-------|--------|
| Frontend | Angular 21 |
| Backend | Python 3.13 + FastAPI |
| Restaurant data | OpenStreetMap / Overpass API |
| PDF parsing | `pdfplumber` |
| Web scraping | `BeautifulSoup` + `httpx` |
| Streaming | Server-Sent Events (FastAPI `StreamingResponse`) |
| Caching | File-based (`backend/.cache/`, 1 week TTL) |
| Hosting (FE) | Vercel |
| Hosting (BE) | Render |

---

## Project Structure

```
sprout-scout/
├── plan.md                            # Full implementation plan
├── url-collection.txt                 # Example URLs used for integration tests
├── backend/
│   ├── main.py                        # FastAPI entry
│   ├── requirements.txt
│   ├── routers/
│   │   └── restaurants.py             # REST + SSE endpoints
│   ├── services/
│   │   ├── overpass.py                # Restaurants by zip code
│   │   ├── scanner.py                 # Orchestrator: picks adapter, dedupes, caches
│   │   ├── extractor.py               # Vegan keyword matching (negation, legends)
│   │   ├── fallback.py                # No-menu payload + delivery_link shape
│   │   ├── cache.py                   # File-based cache (namespaced)
│   │   └── adapters/
│   │       ├── generic.py             # Plain HTML text extraction
│   │       ├── pdf.py                 # All PDF embedding methods
│   │       ├── foodora.py             # Detect + link out (mjam, foodora.at/.com)
│   │       └── lieferando.py          # Detect + link out (lieferando.at/.de, takeaway.com)
│   └── tests/
│       └── scan_examples.py           # Integration test against 5 real URLs
└── frontend/
    └── src/app/
        ├── components/
        │   ├── search/                # Zip input + SSE subscription
        │   └── restaurant-card/       # Name, badge, address, phone, amenity tag, primary link
        └── services/
            └── restaurant.ts          # REST + SSE client
```

---

## API Endpoints

### `GET /api/restaurants?zip_code=1010&country=AT`
Returns a list of restaurants from OpenStreetMap. Cached for 1 week.

### `GET /api/restaurants/{id}/vegan?website=...&name=...&address=...&osm_type=...&osm_diet_vegan=...`
Scans one restaurant's menu. Returns either:

```jsonc
// dishes found
{
  "restaurant_id": "123",
  "no_menu": false,
  "dishes": [{ "name": "...", "confidence": 0.9, "matched_keywords": ["vegan"], "source": "..." }],
  "delivery_link": null
}
```

```jsonc
// delivery-platform link-out
{
  "restaurant_id": "123",
  "no_menu": true,
  "dishes": [],
  "delivery_link": { "platform": "foodora", "url": "https://...", "label": "View menu on foodora" },
  "fallback_links": [...],
  "osm_diet_vegan": null
}
```

```jsonc
// no menu online
{
  "restaurant_id": "123",
  "no_menu": true,
  "dishes": [],
  "delivery_link": null,
  "fallback_links": [
    { "label": "Restaurant website", "url": "..." },
    { "label": "Search on Google Maps", "url": "..." },
    { "label": "View on OpenStreetMap", "url": "..." }
  ],
  "osm_diet_vegan": "yes"   // or "only" / "limited" / null
}
```

### `GET /api/restaurants/scan?zip_code=1010&country=AT`  *(Server-Sent Events)*

Streams scan results for every restaurant in the zip, capped at 30 to keep scan time bounded.

Events emitted:

- `start` — `{ total, total_available, capped }`
- `restaurant` — `{ restaurant, scan }` (only when `scan.dishes` is non-empty)
- `progress` — `{ scanned, total }` after every scan finishes
- `error` — `{ restaurant_id, reason }` on scan failure
- `done` — `{ scanned, total }` when the batch is finished

Concurrency: up to 8 scans in flight, 25s timeout per scan, cancels cleanly on client disconnect.

### `GET /health`
Health check.

---

## Frontend UX

Single auto-scan flow: the search bar opens the SSE endpoint immediately, shows a spinner + `Scanning X / 30` counter, and reveals restaurants progressively as their scans come back positive. Zero-dish results are filtered out server-side. Empty-state message if nothing is found.

Each restaurant card shows: name, "Vegan options found" badge, address, phone, an amenity tag in the top-right corner (Restaurant / Café / Pub / …), and a single primary-link button in the bottom-right. The button picks the best target available: delivery platform link → website → Google Maps search.

---

## Running Locally

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn main:app --reload
# API at http://localhost:8000
```

### Frontend
```bash
cd frontend
npm install
ng serve
# App at http://localhost:4200
```

### Integration test (regression check for the 5 example URLs)
```bash
cd backend
venv/Scripts/python -m tests.scan_examples
```

Expected output: Zen → delivery link, Akakiko → dishes, Pizzeria Ofenbarung + Mister Beans → no_menu fallback, Bruder & Schwester → dishes from the PDF menu.

---

## Next Steps

- [ ] Deploy backend to Render (verify SSE works through Render's proxy; set `X-Accel-Buffering: no` is already emitted)
- [ ] Deploy frontend to Vercel
- [ ] Browser smoke test of the toggle UX (click through both modes, verify empty-state + delivery-link buttons)

---

## Design Decisions

- **Country restriction.** Austria only (4-digit zip, AT filter in Overpass).
- **Discovery scope.** Overpass matches eight food-serving amenities (`restaurant`, `cafe`, `fast_food`, `pub`, `bar`, `biergarten`, `food_court`, `ice_cream`). Many small venues — including pure cafés that serve full lunch menus — are not tagged `restaurant`, so a `restaurant`-only filter under-covers a typical zip noticeably.
- **Delivery platforms.** Foodora/mjam and Lieferando load menus via XHR behind auth — unreachable to anonymous `httpx`. Rather than add a headless browser, we detect their URLs (direct or linked from the homepage) and surface a "View menu on foodora →" button instead.
- **Vegan detection.** Keyword-based (kept intentionally simple); `vegetarisch` is *not* a match since it's not vegan. Negation tokens (`kein`, `ohne`, `leider`, `no`, `without`) suppress matches. Two-pass legend parsing picks up symbol markers like `V = vegan` even when the legend lives elsewhere on the page. "Vegan on request" gets a 0.3 confidence instead of a full match.
- **One-hop crawl, not a full crawler.** When the homepage yields nothing, the scanner follows up to 4 same-host links whose path/text matches obvious menu words and runs both adapters on each. Anything deeper (JS-rendered menus, interactive menu builders) is out of scope — no headless browser.
- **PDF embedding.** Supports `<a href>`, `<iframe>`, `<object>`, `<embed>`, content-type sniffing for extension-less URLs, and PDF.js viewer query-param unwrapping.
- **Caching.** File-based JSON in `backend/.cache/`, 1-week TTL. Restaurant lists cached by zip; scan results cached by `{restaurant_id}_{sha1(website)[:10]}` so the same URL doesn't re-scan on every search.
- **SSE over WebSockets.** One-way stream, plain HTTP, browser-native `EventSource`. No extra dependency needed — FastAPI's `StreamingResponse` emits the `event:` / `data:` frames directly.
- **No login required.** Public tool.
