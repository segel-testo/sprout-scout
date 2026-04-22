# Sprout Scout

Find vegan dishes at local restaurants — search by zip code, we scan the menus.

---

## Status

| Area | Status |
|------|--------|
| Project scaffold | done |
| Backend (FastAPI) | done |
| Frontend (Angular) | done |
| Overpass API integration | done |
| Adapter-based scanner (generic + PDF) | done |
| Vegan extractor (negation, legend tables, German + English) | done |
| Delivery-platform link-out (foodora / mjam / lieferando) | done |
| No-menu fallback (Google Maps + OSM links, `diet:vegan` hint) | done |
| File-based cache (restaurant list + scan results, 1 week) | done |
| SSE bulk-scan endpoint | done |
| Angular UI with on-demand / auto-scan toggle | done |
| Integration test against 5 real-world URLs | done |
| Deploy frontend (Vercel) | next |
| Deploy backend (Render) | next |

---

## How it works

1. User enters a 4-digit Austrian zip code.
2. Backend queries OpenStreetMap via Overpass for all restaurants in that zip.
3. For each restaurant website, the **scanner orchestrator** tries adapters in order and stops on the first hit:
   - **Foodora / mjam / lieferando** URLs → link out to the delivery platform (scraping these requires a headless browser; out of scope, so we surface the link instead).
   - **PDF adapter** → finds PDFs via `<a>`, `<iframe>`, `<object>`, `<embed>`, PDF.js viewer URLs, or `content-type: application/pdf`.
   - **Generic HTML adapter** → text extraction on the page.
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
        │   ├── search/                # Zip input, mode toggle, SSE subscription
        │   └── restaurant-card/       # Dishes, delivery link, fallback links
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

Two modes, toggleable in the search bar, persisted to `localStorage`:

- **Show all, scan on click** *(default)* — fast to first paint. Lists every restaurant; the card fetches its own scan on expand.
- **Auto-scan all** — hits the SSE endpoint, shows a spinner + `Scanning X / 30` counter, and reveals restaurants progressively as their scans come back positive. Hides zero-dish results entirely. If nothing is found, shows an empty-state message.

Restaurant cards handle three states:

- Dishes found → rendered with per-dish confidence score.
- Menu lives on a delivery platform → `View menu on foodora →` button.
- No menu online → fallback-links block (website / Google Maps / OSM) and, if present, the OSM `diet:vegan` hint ("fully vegan restaurant" / "has vegan options" / "limited vegan options").

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
- **Delivery platforms.** Foodora/mjam and Lieferando load menus via XHR behind auth — unreachable to anonymous `httpx`. Rather than add a headless browser, we detect their URLs (direct or linked from the homepage) and surface a "View menu on foodora →" button instead.
- **Vegan detection.** Keyword-based (kept intentionally simple); `vegetarisch` is *not* a match since it's not vegan. Negation tokens (`kein`, `ohne`, `leider`, `no`, `without`) suppress matches. Two-pass legend parsing picks up symbol markers like `V = vegan` even when the legend lives elsewhere on the page. "Vegan on request" gets a 0.3 confidence instead of a full match.
- **PDF embedding.** Supports `<a href>`, `<iframe>`, `<object>`, `<embed>`, content-type sniffing for extension-less URLs, and PDF.js viewer query-param unwrapping.
- **Caching.** File-based JSON in `backend/.cache/`, 1-week TTL. Restaurant lists cached by zip; scan results cached by `{restaurant_id}_{sha1(website)[:10]}` so the same URL doesn't re-scan on every search.
- **SSE over WebSockets.** One-way stream, plain HTTP, browser-native `EventSource`. No extra dependency needed — FastAPI's `StreamingResponse` emits the `event:` / `data:` frames directly.
- **Auto-scan default = off.** First-time visitors shouldn't kick off 8 concurrent requests to random small-business websites before any cache is warm. Users opt into auto-scan via the toggle, and their choice is remembered.
- **No login required.** Public tool.
