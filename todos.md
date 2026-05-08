# Sprout Scout — Todo Plan

## ✅ 1. Remove "show all, scan on click" mode — DONE

- `search.ts`: removed `Mode` type, `mode` signal, `toggleMode`, `loadMode`, `runOnDemand`, `scanDone`. Search now always opens the SSE stream.
- `search.html`: removed `.mode-row` (toggle button + hint).
- `search.scss`: removed `.mode-row`, `.mode-toggle`, `.mode-hint` styles.
- `services/restaurant.ts`: removed `getRestaurants` and `getVeganDishes` (no callers left). Removed `HttpClient` import. Backend `GET /api/restaurants/{id}/vegan` route still exists — flagged for removal in step 7 if no other consumer surfaces.

## ✅ 2 + 3. Simplify the restaurant card — DONE

- Card now shows: **name, "Vegan options found" badge, address, phone, single primary-link button**.
- Dropped from card: dish list, confidence scores, matched keywords, source URL, fallback-links block, OSM `diet:vegan` hint, expand/collapse chevron, on-demand scan path.
- Primary link priority: `delivery_link.url` (e.g. foodora) → `restaurant.website` → Google Maps search built from name + address.
- Phone row hidden when empty (Overpass returns `phone` from `phone` or `contact:phone`).
- `services/restaurant.ts`: pruned `VeganDish` and `FallbackLink` interfaces; `ScanResult` reduced to `{ restaurant_id, delivery_link? }` since nothing else is consumed by the UI.
- `RestaurantCard` simplified to a presentational component with no scanning logic.

Build passes (`ng build --configuration development`).

---

## ✅ 4. Bruderundschwester not appearing — DONE

Root cause: tagged `amenity=cafe` in OSM, but the Overpass query only matched `amenity=restaurant`. Discovery was filtering it out before the scanner ever saw it.

- `services/overpass.py`: query now matches `restaurant|cafe|fast_food|pub|bar|biergarten|food_court|ice_cream` via a regex on `amenity`. Also propagates the `amenity` field on each restaurant payload.
- Verified: postcode 2340 went from 29 to 57 results; Bruder und Schwester (`node/1925290287`) now comes back with `website=http://www.bruderundschwester.com`.
- The homepage doesn't contain vegan keywords directly, but the one-hop crawl from #6 follows `/speisekarte` and the PDF adapter pulls 7 vegan dishes.

## 5. zuminderhof.at — image-only PDF fallback

**Rule:** OCR runs *only* when normal text extraction returns empty/whitespace. If extraction yields text but no vegan keyword matches, no OCR.

- `backend/services/adapters/pdf.py` — after `pdfplumber.extract_text()`, check whether the result is empty (or below a small whitespace threshold, e.g. <20 non-whitespace chars across all pages).
- If empty → fall through to OCR path: rasterize each page with `pdf2image` (or `pdfplumber`'s page images), run `pytesseract.image_to_string`, concatenate.
- New deps: `pytesseract`, `pdf2image`. System deps: Tesseract binary, Poppler (for pdf2image). Document in `backend/requirements.txt` and a "System dependencies" section in README.
- Add a per-PDF timeout cap on the OCR path (e.g. 15s) so a 50-page scanned menu doesn't blow the 25s scan timeout for the whole restaurant.
- Verify against `zuminderhof.at`: download the PDF, confirm `extract_text()` returns empty, confirm OCR finds "vegan".

## ✅ 6. kennys.at — DONE

Root cause: menu lives one click deep at `/produkte/` (and sub-pages); homepage's only "vegan" mentions are inside image filenames, which BeautifulSoup strips during text extraction.

- `services/adapters/generic.py`: added `find_menu_links()` — same-host `<a>` candidates whose path or link text matches `menu|menü|menue|speisekarte|karte|produkte|gerichte|essen|food|drinks|getränke`, capped at 4.
- `services/scanner.py`: `_dispatch` now uses the post-redirect URL as the base (`response.url`), and falls through to `_crawl_menu_links` only when both pdf and generic scans on the homepage return empty. Each candidate is run through both adapters.
- Verified: `https://kennys.at/` now yields 8 vegan dishes via `/produkte/` and sub-pages. Same fix also rescues `bruderundschwester.com` from #4 (homepage → `/speisekarte` PDF → 7 dishes).

## ✅ 8. Lift the 30-restaurant scan cap — DONE

Full-zip scan now in effect. Defensive ceiling of 500 (no realistic Austrian zip approaches this); for zips above that the existing `capped` flag still surfaces correctly in the `start` event.

- `routers/restaurants.py`: `SCAN_RESTAURANT_CAP` raised to 500. New `SSE_KEEPALIVE_INTERVAL = 15`.
- Replaced the `asyncio.as_completed` consumer with `asyncio.wait(timeout=SSE_KEEPALIVE_INTERVAL, return_when=FIRST_COMPLETED)` in a loop. When 15s elapse with no scan completing, the stream emits `:keepalive\n\n` (an SSE comment — browsers ignore, but proxies see traffic and don't drop the connection). Disconnect check still runs every iteration. Cleanup cancels remaining `pending` tasks on exit.
- `components/search/search.html`: when `p.total > 50` and not capped, shows a "large area — this may take a few minutes" hint next to the spinner so the user expects a multi-minute scan.
- README: SSE section updated (ceiling + keepalive note).

Build passes (`ng build --configuration development`). Backend module imports cleanly with the new constants.

## ✅ 9. Amenity filter dropdown — DONE

Native `<select>` (no Material dep). Backend-side filtering, so fewer scans / fewer outbound HTTP calls when an amenity is selected.

- `services/overpass.py`: `FOOD_AMENITIES` constant unchanged (the Overpass query still pulls all eight in one call so the cache stays useful across filter switches).
- `routers/restaurants.py`: extracted `_validate_query`, `_load_restaurants`, `_filter_by_amenity` helpers. Both `GET /api/restaurants` and `GET /api/restaurants/scan` accept `amenity=<value>` (validated against `FOOD_AMENITIES`, 400 on unknown). Cache key stays zip-only — switching the dropdown is a cache hit + cheap in-memory filter, so no extra Overpass calls.
- `services/restaurant.ts`: `scanStream(zip, amenity?)` builds the URL with `URLSearchParams`.
- `components/search/search.ts`: `AMENITY_OPTIONS` const + `selectedAmenity` field passed to the stream.
- `components/search/search.html` + `search.scss`: native `<select class="amenity-select">` between zip input and country select; styled the enabled variant.

Build passes (`ng build --configuration development`).

## ✅ 12. Soft-natural UI redesign — DONE

Reframed the editorial-magazine look into a calmer "field guide" aesthetic. Controls became more obviously interactive; brand accent shifted from yellow-chartreuse to soft leaf-green.

- `styles.scss`: brand accent vars repurposed — `--chartreuse` (#E8F564 yellow → #C8E0BA soft leaf), `--chartreuse-d` (#C8D844 → #9FBE89). New `--leaf`, `--leaf-d` aliases. New soft-shadow tokens (`--shadow-soft`, `--shadow-medium`, `--shadow-cta`, `--shadow-cta-h`). Global `@keyframes cta-spin` lives here so it's not subject to component-scoped CSS quirks; `prefers-reduced-motion` block carries an explicit override for `.cta-spinner` so essential feedback keeps rotating.
- `search.scss`: control surface became a rounded paper panel (1px sage border, 14px radius, soft drop shadow). Tabs are a pill-shaped segmented control. Form controls are 54px with bordered fields, focus snaps the border to moss + a 4px sage-soft halo (no more yellow ring). Radius pills are real selectable buttons (forest fill + sage rings/unit on active). CTA is 54px with weight 600 sans label, soft drop shadow that deepens on hover, and an `is-stop` variant that paints rust during an in-flight scan.
- `field-select.{ts,html,scss}`: new custom dropdown component — sage-bordered trigger that matches the field style, rounded paper panel with soft shadow. Open-direction is computed from the trigger's `getBoundingClientRect` (flips upward when there's ≤336px below and more space above). `:host` is permanently `z-index: 50` so the panel always paints over later siblings.
- `restaurant-card.{html,scss}`: `Nº 01` prefix removed. Cards became standalone surfaces — paper bg, 1px sage border, 12px radius, soft drop shadow, 14px gap between cards. Hover lifts 1px and darkens the border.
- Typography unified — every interactive control uses Albert Sans (weight 500 default, 600 active/selected). Fraunces display is reserved for hero, results count, scan progress numerals, restaurant card name, and the small italic accents in scan caption / error notice / footer / brand wordmark. `Nº 01 · The Field Guide` eyebrow + `Vol. I · Vienna · AT` brand-meta nav both removed.
- Loading spinner replaces the trailing arrow on the CTA during locate / scan (zip + radius forms).

## ✅ 13. Paginated results — DONE

Page size 10 (only paginates when more results come in). `currentPage` signal + `pagedItems` / `totalPages` / `pageNumbers` computed signals in `search.ts`. Smart ellipsis kicks in past 7 pages: `[1, …, current-1, current, current+1, …, total]`. New search resets the page to 1 inside `startStream`. `setPage` smooth-scrolls back to the top of the results section. Styles live in `search.scss` (`.pagination`, `.page-btn`, `.page-arrow`, `.page-ellipsis`) — sage-bordered paper buttons, forest-fill on active, hairline divider above.

## ✅ 14. Stop control + Overpass resilience — DONE

Stop is purely frontend: `Search.stop()` calls `streamSub.unsubscribe()`, which triggers the `EventSource.close()` teardown in `RestaurantService.streamFrom`. Backend's existing `request.is_disconnected()` polling in `_stream_scan` then cancels in-flight scan tasks via the `finally` block. Already-found results stay visible. CTA flips to rust `is-stop` variant during `loading()`; locating remains disabled-with-spinner because `getCurrentPosition` has no clean abort.

Overpass resilience:
- `services/overpass.py`: `_run_query` retries up to 3 attempts with 1s/2s backoff on `429 | 502 | 503 | 504` and `httpx.RequestError`. Permanent 4xx (excluding 429) raises immediately.
- `routers/restaurants.py`: `_load_restaurants` and `_load_restaurants_by_radius` wrap the `fetch_*` calls in `try/except (httpx.HTTPStatusError, httpx.RequestError)` and convert to `HTTPException(503, "The restaurant directory is temporarily unavailable. Please try again in a moment.")`.
- `services/restaurant.ts` `streamFrom`: tracks whether any SSE event was received. If `EventSource` reaches `CLOSED` without any data (i.e. the initial GET failed with non-2xx), calls `subscriber.error()` instead of silently completing. Previously the spinner spun forever on a 500/503.
- `search.ts`: error handler message updated to "Could not start the search. The directory service is temporarily unavailable — please try again in a moment."

## ✅ 11. Radius search ("Near me" mode) — DONE

Two-mode search via segmented control: existing `By zip` plus new `Near me` (500m / 1km / 2km, default 500m). Backend hard-clips to Austria via the Overpass `area["ISO3166-1"="AT"]` filter; cross-border hits are dropped at the source.

- `services/overpass.py`: extracted `_run_query`. New `fetch_restaurants_by_radius(lat, lon, radius_m)` using `(around:R,lat,lon)(area.country)` against the same eight food amenities.
- `routers/restaurants.py`: new `_validate_radius_query` and `_load_restaurants_by_radius` (cache key `AT_radius_{round(lat,3)}_{round(lon,3)}_{radius}` ≈ 100m grid). Two new endpoints: `GET /api/restaurants-by-radius` and `GET /api/restaurants/scan-by-radius`. Refactored streaming/keepalive/cancellation logic into `_stream_scan` reused by both SSE endpoints.
- `services/restaurant.ts`: extracted `streamFrom(url)` helper. New `scanStreamByRadius(lat, lon, radius, amenity?)`.
- `components/search/search.ts`: `mode`, `radius`, `coords`, `geoStatus` signals. `searchByRadius()` is async and calls `getFreshCoords()` (Promise wrapper around `getCurrentPosition`, `maximumAge: 60000`) on every press — denial or unavailable → snap to zip + inline error. No standalone refresh/locate button; the Search button is the single entry point. `tryLargerRadius()` powers the empty-state suggestion.
- `components/search/search.html` + `.scss`: segmented control (`By zip` / `Near me`), radius pill group, "Try N km" suggest button on empty radius result. While locating, the Search button shows an inline white spinner (`.spinner-on-dark`) + `Locating…` label.

Build passes (`ng build --configuration development`). Backend module imports cleanly.

---

## 🔒 Pre-launch security hardening

Audit done 2026-05-08 against the deployed-but-unreleased state of `main`. Items are ordered by severity. **#15 is a launch blocker** — public, anonymous SSRF into Render's metadata endpoint and internal services.

## ✅ 15. Block SSRF in the scanner — DONE

New helper `backend/services/safe_fetch.py` validates every outbound URL before fetching:

- `is_safe_url(url)` rejects non-http(s) schemes, missing hosts, IP-literal URLs that resolve to private space, and DNS hostnames whose `getaddrinfo` returns *any* address that is `is_private | is_loopback | is_link_local | is_reserved | is_multicast | is_unspecified` (or unparseable).
- `safe_get` / `safe_head` walk redirects manually (`MAX_REDIRECTS = 5`) and re-validate each `Location` hop before the next request.

Wired into:
- `services/scanner.py`: `httpx.AsyncClient` switched to `follow_redirects=False`. Initial homepage fetch and every menu-link crawl candidate go through `safe_get`.
- `services/adapters/pdf.py`: `_fetch_pdf` uses `safe_head` + `safe_get` for every PDF candidate, including ones unwrapped from `?file=`/`?url=`/`?src=` viewer params.

End-to-end verified — `scan_restaurant` returns the no-menu fallback with no fetch issued for `http://169.254.169.254/...`, `http://127.0.0.1/...`, `http://10.0.0.1/...`. Integration test (`tests.scan_examples`) still produces the five expected outcomes (Zen → delivery link, Akakiko → 2 dishes, Ofenbarung + MisterBeans → no_menu, Bruder → 7 dishes from PDF).

Residual risk: DNS-rebinding window between `_resolve_safe` and the actual `client.get` is open. Mitigation would be IP-literal pinning with explicit `Host` header — deferred since the current attack model (OSM-edited URLs, attacker-controlled redirects) is fully covered by the resolve-then-fetch check.

## ✅ 16. Delete `GET /api/restaurants/{id}/vegan` — DONE

`git grep` confirmed zero callers. Removed the `@router.get("/restaurants/{restaurant_id}/vegan")` handler in `backend/routers/restaurants.py`. The `scan_restaurant` import stays — still used by `_stream_scan` and `tests.scan_examples`.

Routes after the change: `/api/restaurants`, `/api/restaurants-by-radius`, `/api/restaurants/scan`, `/api/restaurants/scan-by-radius`, `/health`. The unused `RestaurantCard.index` input still pending — folded into #10 cleanup.

## 17. Move frontend `apiUrl` into Angular environment files — MEDIUM

**File:** `frontend/src/app/services/restaurant.ts:35`

**Problem.** `private apiUrl = 'http://localhost:8000/api';` is hardcoded into the production bundle. Once shipped to Vercel, every browser tries `http://localhost:8000` for API calls — the site is broken with the "directory temporarily unavailable" error. Mild data-leak risk too: if a user happens to run any service on port 8000, the request body and headers reach that service.

**Fix.** Standard Angular pattern.
- Create `frontend/src/environments/environment.ts` (`apiUrl: 'http://localhost:8000/api'`) and `environment.production.ts` (`apiUrl: 'https://<render-app>.onrender.com/api'`).
- Configure `fileReplacements` in `angular.json` for the `production` configuration.
- Replace the hardcoded literal with `import { environment } from '../../environments/environment'; … this.apiUrl = environment.apiUrl;`.

## 18. Tighten CORS — MEDIUM

**File:** `backend/main.py:8-13`

**Problem.** `allow_origins=["*"]`, `allow_methods=["*"]`, `allow_headers=["*"]`. Currently safe (no auth, no cookies, `allow_credentials=False` by default) but a footgun if auth or cookies are ever added. Easier to lock down now while it's a one-line change.

**Fix.**
```python
allow_origins=[
    "https://<your-vercel-domain>",
    "http://localhost:4200",  # dev
],
allow_methods=["GET"],  # the API only serves GET
allow_headers=["*"],
```

## 19. Replace cache-key sanitization with a hash — LOW

**File:** `backend/services/cache.py:11-13`

**Problem.** `_cache_path` only replaces `/` and `:`. It does not strip `..`, backslash, null bytes, or absolute-path indicators. Currently safe because every caller passes already-validated input (`AT` country, 4-digit zip, integer radii, SHA-1 hex digests), so no traversal is reachable. But the sanitizer is the wrong defense — any future cache key built from less-validated input (an `amenity` value, a freeform search term) could write outside `.cache/`.

**Fix.** Make the sanitizer collision-proof regardless of input:
```python
import hashlib

def _cache_path(key: str) -> Path:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{digest}.json"
```
Cache keys remain deterministic per input string; traversal becomes impossible by construction.

## 21. Impressum — HIGH (Austrian law)

**Why.** Austria's *E-Commerce-Gesetz § 5 (1)* requires every publicly accessible website served from Austria or targeting Austrian users to display an Impressum: full name, postal address, email, and — if applicable — business registration / VAT number. **This applies to non-commercial hobby sites too.** Missing one can earn a warning letter from a *Wettbewerbsverein* with cost recovery in the hundreds of EUR.

**Fix.** Static page or modal at `/impressum`. Minimum content:
- Name (Vor- und Nachname)
- Postal address
- Email
- *(if applicable)* Firmenbuchnummer / UID-Nummer

Link to it from the footer next to the existing "A field guide to vegan menus" line. Could be a dedicated `app-impressum` route or a small static page in `frontend/public/impressum.html`.

## 22. OSM attribution footer — HIGH (ODbL license)

**Why.** Overpass returns data licensed under the Open Database License (ODbL 1.0). Section 4.3 of the license requires attribution: *"© OpenStreetMap contributors"* with a link to <https://www.openstreetmap.org/copyright> wherever the data is made publicly available. Currently nowhere in the UI or the README.

**Fix.** Add to `app.html` footer:

```html
<p class="foot-attrib">
  Restaurant data © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a>.
</p>
```

Style it small, sage-toned, sits below the existing "tended in Vienna" line. Also mention in the README "Tech Stack" / "Design Decisions" section.

## 23. Privacy notice — HIGH (GDPR Art. 13)

**Why.** The app processes personal data even without accounts:
- **IP address** — uvicorn access log records it (personal data under GDPR).
- **Geolocation coordinates** — radius mode sends lat/lon to the backend.
- **Search terms / zip codes** — in URL query strings, get logged.
- **Cache** — extracted dish text from third-party sites stored 1 week (`backend/.cache/`).

Browser permission gates the geolocation data (counts as consent), but a written notice naming everything collected and the hosts as data processors is required by Art. 13.

**Fix.** Static page or modal at `/privacy`. Minimum content:
- What's collected: search terms, IP (logged ~30 days by Render), geolocation (only when user clicks "Near me", never stored)
- Purpose: serve the search; no advertising, no profiling
- Retention: server logs (host's default), 1-week file cache for scan results
- Third-party processors: Render (backend host), Vercel (frontend host), Google Fonts (CSS), counter.dev (analytics — *if kept; see #20*)
- Data subject rights (access, deletion, complaint to DSB)
- Contact email (same as Impressum)
- *Inline note in radius mode UI*: "Your location is sent to find nearby restaurants. We don't store it."

Link from the footer next to Impressum.

## 20. Lock down third-party assets — LOW

**File:** `frontend/src/index.html:18`

**Problem.** `<script src="https://cdn.counter.dev/script.js" data-id="YOUR-COUNTER-DEV-ID" …>` — no Subresource Integrity hash, and the `data-id` is still the placeholder string from the install snippet (so the analytics is loading-but-not-tracking). Without SRI, a `cdn.counter.dev` compromise becomes supply-chain XSS in your users' browsers.

**Fix.** Either:
- Replace the placeholder with the real counter.dev ID and add `integrity="sha384-…" crossorigin="anonymous"` (pin to the current published bundle hash), or
- Remove the script entirely until analytics is actually wanted.

While you're in `index.html`, also add a Content-Security-Policy — either as a `<meta http-equiv="Content-Security-Policy">` tag or via Vercel's `vercel.json` `headers` config. A starting policy: `default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; script-src 'self' https://cdn.counter.dev; connect-src 'self' https://<render-domain>;`.

---

## 10. Cleanup pass (last)

- Search for unreferenced functions/components/imports across `backend/` and `frontend/src/`.
- Specifically check whether `GET /api/restaurants/{id}/vegan` still has callers (Angular service, tests). If not, delete the route + its handler. **Note: as of step 1, the FE no longer calls it — only the integration test path may still use it.**
- The `index` input on `RestaurantCard` is unused since the `Nº 01` prefix was removed in step 12 — candidate for deletion (and the corresponding `prefix` getter / template usages, if any are still around).
- Look for duplicated extraction/normalization logic between `extractor.py` and the adapters.
- Run the integration test again as a final regression check.

---

## Suggested order

1. ~~Investigate #4 and #6~~ — done.
2. ~~#9 amenity filter dropdown~~ — done.
3. ~~#8 lift the 30-restaurant cap~~ — done.
4. ~~#11 radius search~~ — done.
5. ~~#12 UI redesign~~ — done.
6. ~~#13 pagination~~ — done.
7. ~~#14 stop control + Overpass resilience~~ — done.
8. ~~#15 + #16 SSRF hardening~~ — done.
9. **#21 Impressum + #22 OSM attribution + #23 privacy notice** — Austrian/EU legal must-do before any public launch.
10. #17 environment-based `apiUrl` — required for Vercel deploy to work.
11. #18 CORS lockdown.
12. #19 cache-key hash + #20 third-party script SRI / CSP.
13. #5 OCR path (backend, isolated) — still pending.
14. #10 cleanup (folds in unused `RestaurantCard.index`).
15. Deploy: backend → Render, frontend → Vercel.

## Out of scope (confirmed)

- Headless browser for foodora/lieferando/kennys.
- OCR on non-PDF image menus.
- Countries other than Austria.
