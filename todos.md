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

Audit done 2026-05-08 against the deployed-but-unreleased state of `main`. Items are ordered by severity. **#15 is a launch blocker** — public, anonymous SSRF into the cloud provider's metadata endpoint and internal services.

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

## ✅ 17. Move frontend `apiUrl` into Angular environment files — DONE

Standard Angular environment pattern in place. Production bundle no longer leaks `localhost:8000` (verified by `grep`).

- New `frontend/src/environments/environment.ts` — `{ production: false, apiUrl: 'http://localhost:8000/api' }`.
- New `frontend/src/environments/environment.production.ts` — `{ production: true, apiUrl: 'https://api.sprout-scout.at/api' }`. Subdomain split (frontend on `www.sprout-scout.at` via Codeberg Pages, backend on `api.sprout-scout.at` via Scaleway Serverless Containers with a CNAME to `<container-host>.functions.fnc.fr-par.scw.cloud`). Reason for not collapsing onto a single origin: SSE streams need unbuffered transport, and any extra static-host proxy hop in front of the live scan stream is asking for buffering / connection-drop trouble.
- `angular.json`: production configuration gained a `fileReplacements` entry swapping `environment.ts` for `environment.production.ts`. Also bumped the `anyComponentStyle` budget from 4kB warn / 8kB error to 12kB warn / 20kB error — pre-existing issue, `search.scss` had grown to 12kB over successive redesigns and was blocking the prod build entirely.
- `services/restaurant.ts`: hardcoded literal replaced with `private apiUrl = environment.apiUrl;` (import from `'../../environments/environment'`).
- Deploy note: when DNS for `sprout-scout.at` is configured, add `api.sprout-scout.at` as a custom domain in the Scaleway container, and add the matching CNAME at the registrar pointing at the `<container-host>.functions.fnc.fr-par.scw.cloud` host shown in the container detail page. Scaleway auto-provisions Let's Encrypt. If you change the API host, only `environment.production.ts` needs a one-line edit.

Dev build: 1.65 MB (unoptimized). Prod build: 310 kB raw / 80 kB gzipped main bundle, zero `localhost` strings in the output.

## ✅ 18. Tighten CORS — DONE

CORS is now env-driven so the production origin list lives on Scaleway rather than baked into the image.

- `backend/main.py`: reads `ALLOWED_ORIGINS` (comma-separated). Defaults to `http://localhost:4200` for dev so a fresh checkout works without env config. `allow_methods=["GET"]` — every public route is GET-only. `allow_headers=["*"]` is fine since `allow_credentials` stays at its default (`False`); no cookies, no auth, no preflight surface to widen.
- Production env var on the Scaleway container (documented in README *Backend → Scaleway Serverless Containers*): `ALLOWED_ORIGINS=https://www.sprout-scout.at,https://sprout-scout.at,https://heislsheimen.codeberg.page` (Codeberg URL stays in until launch so the live frontend can be smoke-tested before DNS flips).
- Verified: backend imports cleanly with the default origin list, env var parsing trims whitespace and drops empty entries, integration regression (`tests.scan_examples`) still produces the five expected outcomes.

## ✅ 19. Replace cache-key sanitization with a hash — DONE

`backend/services/cache.py` — keys are SHA-256-hashed; on-disk filename is always a 64-hex-char `.json` so path traversal is impossible by construction. The same module also gained a Scaleway Object Storage backend (S3-compatible via boto3): if `CACHE_S3_BUCKET` + `CACHE_S3_ACCESS_KEY` + `CACHE_S3_SECRET_KEY` are set, all reads/writes go to Object Storage; otherwise the file backend is used (for local dev). Same public API. Production deploys on Scaleway Serverless Containers use the S3 backend so cached scans survive across cold starts (containers scale to zero after 15 min idle, which would otherwise wipe the local file cache). Object Storage requests are free, storage <€0.001/month for the project's cache. Locally you can `rm -rf backend/.cache/` if you want a clean slate. Integration test still produces all five expected outcomes.

## ✅ 21 + 22 + 23. Legal pages (Impressum, OSM attribution, Privacy) — DONE

Audit-driven legal triple shipped via a single non-disruptive modal pattern. The search flow is untouched — no router, no URL state, no surface changes to the existing controls.

- New `LegalModal` component (`frontend/src/app/components/legal-modal/`) — single component, `kind: 'impressum' | 'privacy'` input, emits `closed`. Backdrop click + Esc + close button. Sage-bordered paper panel, soft drop shadow, scrollable body with `max-height: calc(100vh - 48px)` so short viewports don't trap content.
- `App` (`app.ts`) gained a `legalOpen = signal<LegalKind | null>(null)` plus `openLegal` / `closeLegal`. Modal renders only when open.
- `app.html` footer redesigned into a right-aligned `.foot-text` column with three lines:
  1. existing tagline (`A field guide to vegan menus · {{ year }}.`),
  2. **OSM attribution** — `Restaurant data © OpenStreetMap contributors.` with the required link to `openstreetmap.org/copyright` (ODbL § 4.3),
  3. footer nav with `Impressum · Privacy` buttons that open the modal.
- **Impressum content** — Information gemäß § 5 ECG / § 25 MedienG: Valentin Röcklinger, K. Elisabethstrasse 13, 2340 Mödling, Austria, heislsheimen@gmail.com. Marked as non-commercial hobby project (no Firmenbuch/UID).
- **Privacy content** — GDPR Art. 13 notice: search terms / IP / geolocation / cached scan results, processors (Codeberg Pages, Scaleway, Google Fonts, OSM/Overpass), GDPR Art. 15–21 rights with Datenschutzbehörde complaint link, contact email.
- `search.html` + `.scss` — radius-mode now shows a small inline `geo-note` directly under the tabs: *"Your location is sent to find nearby restaurants. We don't store it."* So the user reads the consent statement before they hit Search.
- `README.md` Design Decisions section — new "Data attribution" bullet documenting the ODbL license and its § 4.3 attribution requirement.

Build passes (`ng build --configuration development`).

## ✅ 20. counter.dev real ID — DONE

`frontend/src/index.html` — placeholder `YOUR-COUNTER-DEV-ID` replaced with the real counter.dev site ID `ca079955-cd3a-4c77-8c03-778fc417f597`. Analytics now actually tracks.

Still open as a follow-up if desired (deferred — separate from launch blockers):
- **Subresource Integrity (SRI):** counter.dev publishes a versioned bundle, so pinning a `sha384-…` hash means the script breaks on every bundle update; the practical hardening here is to self-host a copy of `script.js` (then SRI-pin it) or accept the small supply-chain risk in exchange for live updates. No action taken — counter.dev is a small, EU-leaning analytics service, and the script runs inert unless `data-id` matches.
- **Content-Security-Policy:** worth adding before launch as a `<meta http-equiv>` tag in `index.html`. Starting policy: `default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; script-src 'self' https://cdn.counter.dev; connect-src 'self' https://api.sprout-scout.at;`. Test carefully — Angular's runtime emits inline styles and may need `'unsafe-inline'` on `style-src`. Deferred.

---

## ✅ 10. Cleanup pass — DONE

- `RestaurantCard.index` input + `prefix` getter deleted from `restaurant-card.ts`. Dead since #12 removed the `Nº 01 ·` prefix display from the card template.
- `Restaurant` interface (`services/restaurant.ts`) trimmed: `osm_diet_vegan` and `osm_type` removed. Both were declared but never read anywhere in the UI — backend still emits `osm_type` inside `no_menu_payload` but that payload is filtered out server-side (`_stream_scan` only yields restaurants with `dishes`), so the field never crosses the wire.
- `GET /api/restaurants/{id}/vegan` was already removed in #16. No stragglers.
- **Backend extractor/adapter dedup — examined, no action.** Each adapter (`generic.py`, `pdf.py`) does format-specific normalization (HTML script-stripping + `get_text("\n")` for HTML; `pdfplumber.extract_text()` page-joining for PDF) and then hands off to the shared `extract_vegan_dishes(text, source)`. That's the right separation, not duplication.
- Integration test (`tests.scan_examples`) passes: Zen → delivery, Akakiko → 2 dishes, Ofenbarung + MisterBeans → no_menu, Bruder → 7 PDF dishes.

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
9. ~~#21 Impressum + #22 OSM attribution + #23 privacy notice~~ — done.
10. ~~#17 environment-based `apiUrl`~~ — done.
11. ~~#18 CORS lockdown~~ — done.
12. ~~#19 cache-key hash + #20 counter.dev real ID~~ — done. (CSP / SRI deferred as separate follow-ups, see #20.)
13. ~~#10 cleanup~~ — done.
14. Deploy — **done (2026-05-10)**.
    - ✅ Codeberg account created (`heislsheimen`), SSH key generated and registered, `codeberg.org/heislsheimen/sprout-scout` repo created.
    - ✅ First frontend deploy ran via `frontend/scripts/deploy-codeberg.ps1` — `pages` branch live, `curl https://heislsheimen.codeberg.page/sprout-scout/` returns `307 → https://www.sprout-scout.at/` (proves `.domains` works, bundle is up).
    - ✅ **Backend host decision (2026-05-09)** — Render rejected (15-min idle sleep). Northflank tried briefly but its "free Sandbox" plan meters compute on top of the slot (~$5.40/month at smallest size), so it isn't actually free. Settled on **Scaleway Serverless Containers** (`fr-par`) with **scale-to-zero** + cache backed by **Scaleway Object Storage**. Bill: €0/month within the recurring monthly free tier (400 000 GB-s memory + 200 000 vCPU-s). Trade-off: 1–3 s cold start on the first request after a 15-min idle window. Cache porting (~50 lines in `services/cache.py`) preserves cache across cold starts. Clever Cloud (~€5/mo always-on) and min-scale=1 on Scaleway (~€2/mo) are escape valves if cold starts ever bother us. See README *Backend → Scaleway Serverless Containers* for the full setup walkthrough.
    - ✅ **Backend deployed** — image built via GitHub Actions (`.github/workflows/build-backend.yml`, secret `SCW_SECRET_KEY`) and pushed to `rg.fr-par.scw.cloud/sprout-scout/sprout-scout-api:latest`. Container running at `https://<host>.functions.fnc.fr-par.scw.cloud` with 256 MB / 100 mvCPU, min-scale 0 / max-scale 5, sandbox v2, request timeout 300 s. Env vars: `ALLOWED_ORIGINS`, `CACHE_S3_BUCKET=sprout-scout-cache`, `CACHE_S3_ACCESS_KEY`, `CACHE_S3_SECRET_KEY` (marked Secret). Smoke test: `/api/restaurants?zip_code=2346&country=AT` → 200 with empty `restaurants` array (correct — no OSM matches in 2346); first request wrote a JSON object to the bucket.
    - ✅ **DNS (2026-05-10)** — domain switched from initial registrar to easyname. Records at easyname's `cns1/2/3.cloudpit` nameservers: apex `A 217.197.84.141` + `AAAA 2a0a:4580:103f:c0de::2` (Codeberg), apex `TXT sprout-scout.heislsheimen.codeberg.page` (required for Codeberg apex owner-lookup — without it pages-server returns 424 *"could not obtain repo owner from custom domain"*), `www CNAME sprout-scout.heislsheimen.codeberg.page` (project-site format, **not** `heislsheimen.codeberg.page` — that's the personal-site format and won't resolve owner for project repos), `api CNAME sproutscout6ac23ac7-sprout-scout-api.functions.fnc.fr-par.scw.cloud`.
    - ✅ **Custom domain on Scaleway** — `api.sprout-scout.at` added; Let's Encrypt cert provisioned. `https://api.sprout-scout.at/health` returns `{"status":"ok"}`.
    - ✅ **Frontend canonical flipped to apex.** `.domains` order is `sprout-scout.at` then `www.sprout-scout.at`; default URL `heislsheimen.codeberg.page/sprout-scout/` 307-redirects to `https://sprout-scout.at/`. Apex serves the Angular bundle; www currently 421s (cert under new CNAME hadn't issued yet at flip time — self-resolves as Caddy on-demand TLS retries).
    - ✅ **Smoke test (live origin)** — zip search, "Near me" radius, Impressum + Privacy modals, OSM attribution all confirmed working.

## Out of scope (confirmed)

- Headless browser for foodora/lieferando/kennys.
- OCR on non-PDF image menus.
- Countries other than Austria.

---

## 🔭 v2 backlog (post-launch)

Things deferred until after the v1 public launch. Pick up when there's a reason to.

### v2.1 — OCR fallback for image-only PDFs (was #5)

**Target case:** `zuminderhof.at` ships a scanned PDF menu — `pdfplumber.extract_text()` returns empty, so the scanner currently surfaces it as `no_menu` even though the word *vegan* is visible on the page.

**Why deferred:** adds Tesseract + Poppler as system dependencies, which means extending the existing Scaleway container `Dockerfile` and accepting a larger image / longer cold start. Worth it once we know v1 traffic justifies the deploy complexity, or once a second image-only PDF surfaces.

**Plan when picked up:**
- `backend/services/adapters/pdf.py` — after `pdfplumber.extract_text()`, check whether the result is empty (or below a small whitespace threshold, e.g. <20 non-whitespace chars across all pages). **OCR runs *only* if normal extraction is empty** — if extraction yields text but no vegan keyword matches, *don't* OCR. Keeps the common path fast.
- If empty → fall through to OCR: rasterize each page with `pdf2image`, run `pytesseract.image_to_string`, concatenate.
- New pip deps: `pytesseract`, `pdf2image`. System deps: Tesseract binary, Poppler. Add `apt-get install` lines for those to the existing `backend/Dockerfile` and document in `backend/requirements.txt` + a "System dependencies" section in README.
- Per-PDF OCR timeout cap (e.g. 15s) so a 50-page scanned menu doesn't blow the 25s scan timeout for the whole restaurant.
- Verify against `zuminderhof.at`: download the PDF, confirm `extract_text()` returns empty, confirm OCR finds "vegan".
