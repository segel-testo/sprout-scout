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
| Radius search (`Near me` mode, 500m / 1km / 2km, AT-clipped) | done |
| Soft-natural UI redesign + custom dropdown + paginated results | done |
| Stop control (abort in-flight scan, keep partial results) | done |
| Overpass retry-with-backoff + clean 503 on persistent failure | done |
| SSRF hardening (private-IP block + manual redirect walk) | done |
| Deploy frontend (Codeberg Pages) | live at https://sprout-scout.at/ |
| Deploy backend (Scaleway Serverless Containers, fr-par) | live at https://api.sprout-scout.at/ |

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
| Hosting (FE) | Codeberg Pages (Berlin, DE) |
| Hosting (BE) | Scaleway Serverless Containers (fr-par, scale-to-zero, EU sovereign) |
| Cache backend (prod) | Scaleway Object Storage (S3-compatible) |

---

## Project Structure

```
sprout-scout/
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
│   │   ├── safe_fetch.py              # SSRF-safe wrapper for outbound HTTP (private-IP block, manual redirect walk)
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

### `GET /api/restaurants?zip_code=1010&country=AT&amenity=cafe`
Returns a list of restaurants from OpenStreetMap. Cached for 1 week. Optional `amenity` filters to one of `restaurant|cafe|fast_food|pub|bar|biergarten|food_court|ice_cream`; the cache stores the full set, so switching the filter doesn't trigger another Overpass call.

### `GET /api/restaurants-by-radius?lat=48.21&lon=16.37&radius=500&amenity=cafe`
Same shape as `/api/restaurants` but searches a circular area around `lat,lon`. `radius` is meters, must be one of `500 | 1000 | 2000`. Hard-clipped to Austria via the Overpass `area["ISO3166-1"="AT"]` filter — cross-border hits are dropped at the source, not post-filtered. Cache key rounds coordinates to 3 decimals (~75–110m at AT latitude), so repeat taps from the same spot share a cache hit.

### `GET /api/restaurants/scan?zip_code=1010&country=AT&amenity=cafe`  *(Server-Sent Events)*

Streams scan results for every restaurant in the zip. A defensive ceiling of 500 keeps a runaway query from spinning forever, but no realistic Austrian zip hits it. Optional `amenity` narrows the batch before the ceiling is applied — fewer scans = fewer outbound HTTP calls.

### `GET /api/restaurants/scan-by-radius?lat=48.21&lon=16.37&radius=500&amenity=cafe`  *(Server-Sent Events)*

Same SSE event shape as `/api/restaurants/scan`, but the batch is sourced from the radius endpoint above. Same ceiling, same keepalive, same `amenity` filter behavior.

Events emitted:

- `start` — `{ total, total_available, capped }`
- `restaurant` — `{ restaurant, scan }` (only when `scan.dishes` is non-empty)
- `progress` — `{ scanned, total }` after every scan finishes
- `error` — `{ restaurant_id, reason }` on scan failure
- `done` — `{ scanned, total }` when the batch is finished

Concurrency: up to 8 scans in flight, 25s timeout per scan, cancels cleanly on client disconnect. Emits a `:keepalive` SSE comment every 15s of idle so proxies don't drop long-running streams.

### `GET /health`
Health check.

---

## Frontend UX

Two search modes via a segmented control above the input row:

- **By zip** (default) — 4-digit Austrian zip + amenity filter.
- **Near me** — three radius pills (500m / 1km / 2km, default 500m) + amenity filter. The Search button itself triggers geolocation on every press: while in flight the button label is `Locating…` with an inline spinner, then flips to `Searching…` once the scan starts. `getCurrentPosition` runs with `maximumAge: 60000`, so a fresh fix from the last minute is reused instantly without a real GPS poll. On denial or unsupported browser, the UI snaps back to zip mode and shows an inline message.

After either mode finishes, the search bar opens the SSE endpoint immediately, shows a `Scanning X / total` counter, and reveals restaurants progressively as their scans come back positive. Zero-dish results are filtered out server-side. If a radius scan finishes empty, an inline "Try 1 km" / "Try 2 km" button bumps the radius and re-runs.

The CTA flips role while a scan is running — the green "Begin scan" button becomes a rust-colored "Stop" button (with the trailing arrow swapped for a rotating spinner). Clicking it closes the SSE connection, the backend cleanly cancels in-flight scans, and any restaurants found so far stay on screen.

Result cards are standalone paper surfaces with sage borders and a soft drop shadow, separated by gaps. Each card shows: name, "Vegan options found" badge, address, phone, an amenity tag in the top-right corner (Restaurant / Café / Pub / …), and a single primary-link button on the bottom-right that picks the best target available — delivery platform link → website → Google Maps search.

When more than 10 restaurants come back, the results paginate at 10/page with a numbered control (smart ellipsis kicks in past 7 pages); switching pages smooth-scrolls back to the top of the results section.

The amenity filter uses a custom dropdown component (`field-select`) instead of a native `<select>` — it flips upward when the trigger is too close to the viewport bottom, and follows the trigger if you scroll while open.

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

- [x] Frontend deployed to Codeberg Pages (`pages` branch live; serving <https://sprout-scout.at/>)
- [x] DNS for `sprout-scout.at` (easyname; apex A/AAAA + apex TXT for Codeberg owner-lookup, `www` CNAME to project-site target, `api` CNAME to Scaleway container)
- [x] Backend deployed to Scaleway Serverless Containers (`fr-par`); cache writes verified against Scaleway Object Storage; `api.sprout-scout.at` answering with Let's Encrypt cert
- [x] Browser smoke test against the live origin (zip search, "Near me", Impressum + Privacy modals, OSM attribution)

---

## Deployment

### Frontend → Codeberg Pages

[Codeberg Pages](https://docs.codeberg.org/codeberg-pages/) serves static
content from a `pages` branch (or a repo named `pages`).

#### One-time setup (do this once before the first deploy)

**1. Codeberg account + repo.**
- Sign up at <https://codeberg.org>.
- Create a new public repo, e.g. `sprout-scout`. Source code stays on
  GitHub; Codeberg only needs the built artefact.

**2. SSH key for push access.**
- Generate or reuse an SSH keypair (`ssh-keygen -t ed25519` if you don't
  have one). On Windows, `~/.ssh/id_ed25519.pub` lives at
  `C:\Users\<you>\.ssh\id_ed25519.pub`.
- In Codeberg: *avatar → Settings → SSH / GPG Keys → Add Key*. Paste the
  contents of the `.pub` file.
- Test: `ssh -T git@codeberg.org` should reply *"Hi `<your-user>`!"*.

**3. Bake `.domains` into every build.** In the served output, Codeberg
looks for a plain-text file named `.domains` listing the custom domains
you want it to serve. The first line is the canonical hostname; others
redirect to it. Put it in `frontend/public/.domains` so the Angular
build copies it into `dist/frontend/browser/` automatically:
```
sprout-scout.at
www.sprout-scout.at
```

**4. DNS records** at your registrar for `sprout-scout.at`. Codeberg
identifies the owner of a custom domain by following the CNAME / TXT
record back to the user/repo's pages URL — get any of these wrong and
the pages-server returns `424 Failed Dependency` *"could not obtain
repo owner from custom domain"*.

| Subdomain | Type | Value | Why |
|-----------|------|-------|-----|
| *(empty)* | `A` | Codeberg's published IPv4 (currently `217.197.84.141`, [check docs](https://docs.codeberg.org/codeberg-pages/using-custom-domain/)) | Apex traffic |
| *(empty)* | `AAAA` | Codeberg's published IPv6 (currently `2a0a:4580:103f:c0de::2`) | Apex IPv6 |
| *(empty)* | `TXT` | `sprout-scout.<your-user>.codeberg.page` | Required for apex — pages-server can't follow a CNAME from the apex (DNS forbids it) so it reads this TXT to figure out which user/repo serves the apex |
| `www` | `CNAME` | `sprout-scout.<your-user>.codeberg.page.` | Project-site format. **Not** `<your-user>.codeberg.page` — that's the personal-site format and pages-server won't resolve owner for project repos |

The `sprout-scout.<your-user>.codeberg.page` form is `[[branch.]repo.]user.codeberg.page` — Codeberg auto-discovers the `pages` branch, so the branch prefix isn't needed.

**5. Set the deploy remote** (used by the deploy script):
```powershell
$env:CODEBERG_REMOTE = "git@codeberg.org:<your-user>/sprout-scout.git"
```
Persist across sessions with `[Environment]::SetEnvironmentVariable(
'CODEBERG_REMOTE', '...', 'User')` if you want.

#### Deploy

```powershell
cd frontend
.\scripts\deploy-codeberg.ps1
```

The script runs `ng build --configuration production` and force-pushes
`dist/frontend/browser/` to the `pages` branch of your Codeberg repo.
Codeberg auto-provisions a Let's Encrypt certificate once DNS resolves
to its servers.

The site is then live at `https://www.sprout-scout.at/` (custom domain)
and at `https://<your-user>.codeberg.page/sprout-scout/` (default URL).

### Backend → Scaleway Serverless Containers

[Scaleway](https://scaleway.com) is a French sovereign cloud with a
real recurring free tier for serverless containers (400 000 GB-s memory
+ 200 000 vCPU-s per month). Region `fr-par` (Paris) keeps everything
in EU jurisdiction. **Scale-to-zero** after 15 min of idle keeps the
bill at €0 for hobby-traffic; the cost is a 1–3s cold start on the
first request after an idle period.

The image is built in CI and pushed to Scaleway Container Registry; the
serverless container pulls from there. The file cache is replaced by an
S3-compatible cache on Scaleway Object Storage so cached scans survive
across cold starts.

#### One-time setup

**1. Scaleway account + region.**
- Sign up at <https://console.scaleway.com>. A payment method is
  required even for the free tier (Scaleway uses it for KYC; they don't
  charge unless you exceed the free pool).
- Top-bar region selector: `fr-par`.

**2. Object Storage bucket** (*Storage → Object Storage*):
- Create a private **Standard Multi-AZ** bucket named `sprout-scout-cache`
  in `fr-par`. Versioning + Object Lock off.
- Generate an API key from *avatar → IAM → API keys* (bearer = yourself).
  Save the **Access key ID** and **Secret key** — secret is shown once.

**3. Container Registry namespace** (*Containers → Container Registry*):
- Create namespace `sprout-scout` in `fr-par`, **Private**.
- Registry URL becomes `rg.fr-par.scw.cloud/sprout-scout`. The CI
  workflow (`.github/workflows/build-backend.yml`) is hardcoded to
  push there.

**4. CI build secret** (GitHub repo settings → *Secrets and variables → Actions*):

| Secret | Value |
|--------|-------|
| `SCW_SECRET_KEY` | the Scaleway secret key from step 2 |

Every push to `main` that touches `backend/` triggers
`docker build` + push to the registry — ~3 min total.

**5. Serverless Container** (*Serverless → Containers*):
- Create namespace `sprout-scout` in `fr-par`.
- Deploy a container from `rg.fr-par.scw.cloud/sprout-scout/sprout-scout-api:latest`.

| Setting | Value |
|---------|-------|
| Container name | `sprout-scout-api` |
| Port | `8000` |
| Memory | `256 MB` |
| vCPU | `100 mvCPU` |
| Min scale | `0` (scale-to-zero — keeps it free) |
| Max scale | `5` |
| Request timeout | `300` s |
| Sandbox | `v2` (faster cold starts) |
| Privacy | **Public** |

**6. Environment variables on the container:**

| Variable | Value | Type |
|----------|-------|------|
| `ALLOWED_ORIGINS` | `https://www.sprout-scout.at,https://sprout-scout.at,https://heislsheimen.codeberg.page` | normal |
| `CACHE_S3_BUCKET` | `sprout-scout-cache` | normal |
| `CACHE_S3_ACCESS_KEY` | Scaleway access key ID (`SCW…`) | normal |
| `CACHE_S3_SECRET_KEY` | Scaleway secret key | **Secret** ✅ |

The `CACHE_S3_*` variables flip `backend/services/cache.py` from its
default file backend to the S3 backend. Endpoint defaults to
`https://s3.fr-par.scw.cloud` and region to `fr-par`; both can be
overridden via `CACHE_S3_ENDPOINT` / `CACHE_S3_REGION`.

The Codeberg default URL stays in `ALLOWED_ORIGINS` so you can
smoke-test the live frontend before DNS flips. Drop it after launch.

**7. Custom domain.**
- *Container → Custom domains* → add `api.sprout-scout.at`.
- At the registrar, add `CNAME api → <container-host>.functions.fnc.fr-par.scw.cloud`
  (exact host shown in the container detail page).
- Scaleway auto-provisions a Let's Encrypt cert once DNS resolves.

#### Notes for this project

- **SSE streams.** Scaleway supports HTTP/1.1 + HTTP/2 with chunked
  transfer encoding. The 300 s request timeout is well above the
  worst-case SSE scan duration (Vienna 1010 caps around 2–3 min). The
  `X-Accel-Buffering: no` header the backend already emits covers any
  edge proxy that might otherwise buffer SSE frames.
- **Cache backend.** `services/cache.py` auto-detects: if all three
  `CACHE_S3_BUCKET` / `CACHE_S3_ACCESS_KEY` / `CACHE_S3_SECRET_KEY` are
  set, it writes JSON blobs to Object Storage; otherwise it falls back
  to local file I/O for dev. Same public API (`get_cached`,
  `set_cached`, `get_namespaced`, `set_namespaced`) either way. Object
  Storage requests are free; storage is ~€0.002/GB/month after the
  90-day trial — for the project's <100 MB cache, effectively €0
  forever.
- **Cold start budget.** A 1–3 s pause hits the first user of each
  ~15-min-idle window. With ~3–4 sessions/day at 100 users/month, that
  cold start is amortised across the rest of the session, and the
  cache (now persistent across cold starts) absorbs subsequent loads.
- **If the API URL changes**, edit
  `frontend/src/environments/environment.production.ts` and redeploy
  the frontend.

---

## Design Decisions

- **Country restriction.** Austria only (4-digit zip, AT filter in Overpass).
- **Discovery scope.** Overpass matches eight food-serving amenities (`restaurant`, `cafe`, `fast_food`, `pub`, `bar`, `biergarten`, `food_court`, `ice_cream`). Many small venues — including pure cafés that serve full lunch menus — are not tagged `restaurant`, so a `restaurant`-only filter under-covers a typical zip noticeably.
- **Delivery platforms.** Foodora/mjam and Lieferando load menus via XHR behind auth — unreachable to anonymous `httpx`. Rather than add a headless browser, we detect their URLs (direct or linked from the homepage) and surface a "View menu on foodora →" button instead.
- **Vegan detection.** Keyword-based (kept intentionally simple); `vegetarisch` is *not* a match since it's not vegan. Negation tokens (`kein`, `ohne`, `leider`, `no`, `without`) suppress matches. Two-pass legend parsing picks up symbol markers like `V = vegan` even when the legend lives elsewhere on the page. "Vegan on request" gets a 0.3 confidence instead of a full match.
- **One-hop crawl, not a full crawler.** When the homepage yields nothing, the scanner follows up to 4 same-host links whose path/text matches obvious menu words and runs both adapters on each. Anything deeper (JS-rendered menus, interactive menu builders) is out of scope — no headless browser.
- **PDF embedding.** Supports `<a href>`, `<iframe>`, `<object>`, `<embed>`, content-type sniffing for extension-less URLs, and PDF.js viewer query-param unwrapping.
- **Caching.** File-based JSON in `backend/.cache/`, 1-week TTL. Restaurant lists cached by zip; radius lists cached by `AT_radius_{round(lat,3)}_{round(lon,3)}_{radius}` (a ~100m grid so nearby taps share); scan results cached by `{restaurant_id}_{sha1(website)[:10]}` so the same URL doesn't re-scan on every search.
- **SSE over WebSockets.** One-way stream, plain HTTP, browser-native `EventSource`. No extra dependency needed — FastAPI's `StreamingResponse` emits the `event:` / `data:` frames directly.
- **Overpass resilience.** Public Overpass API regularly returns 504 / 502 / 429 under load. `_run_query` retries up to 3 attempts with 1s/2s backoff on those statuses and on `httpx.RequestError`; persistent failures convert to `HTTPException(503)` at the router so the frontend can show a friendly "directory temporarily unavailable" message instead of a 500 stack trace. The `EventSource` client also distinguishes connection-failed-before-any-event from a normal end-of-stream so a backend 503 surfaces as an inline error rather than an indefinite spinner.
- **Stop control.** Abort is purely a frontend-driven `EventSource.close()` — the backend's `_stream_scan` already polled `request.is_disconnected()` for keepalive purposes, so the same path cancels pending scan tasks cleanly when the user hits Stop. Already-found results stay rendered.
- **SSRF guard on outbound fetches.** OSM is publicly editable, so any `website` tag is attacker-controllable. `services/safe_fetch.py` is the chokepoint for every outbound HTTP request the scanner makes: it requires `http`/`https`, rejects URLs whose host (literal IP or DNS-resolved address) falls into `is_private | is_loopback | is_link_local | is_reserved | is_multicast | is_unspecified`, and walks redirects manually so each `Location` hop is re-validated. Cloud-metadata endpoints (`169.254.169.254`), loopback, and RFC1918 ranges are unreachable from the scanner. `httpx.AsyncClient` is configured with `follow_redirects=False` to enforce this — the auto-follow path would have bypassed validation.
- **No login required.** Public tool.
- **Data attribution.** Restaurant directory data comes from OpenStreetMap via the Overpass API and is licensed under the [Open Database License (ODbL 1.0)](https://opendatacommons.org/licenses/odbl/). Per § 4.3 of the license, the UI footer carries the required "© OpenStreetMap contributors" attribution with a link to <https://www.openstreetmap.org/copyright>.
