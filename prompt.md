# Continuation prompt — Sprout Scout

Paste this verbatim at the start of a new session.

---

You are continuing work on **Sprout Scout** at `C:\Vali\coding\sprout-scout`. It's an Austria-only web app that finds vegan dishes at restaurants via 4-digit zip code (Angular 21 frontend + FastAPI backend + OpenStreetMap/Overpass for restaurant data + an adapter pipeline that scans menu pages and PDFs).

## Read these first, in this order

1. `README.md` — full architecture, API contract, design decisions. Authoritative.
2. `todos.md` — the live work plan. Items 1–4, 6, 8, 9, 11, 12, 13, 14, 15, 16 are done; 5 and 10 are pending. **Pre-launch security hardening: #15 (SSRF) and #16 (delete unused vegan route) landed; #17–#20 are still open. Pre-launch legal must-do: #21 Impressum + #22 OSM attribution + #23 privacy notice — these block any public launch under Austrian law / GDPR / ODbL.** Read this even if you think you remember the state — it's the source of truth.

Skim, don't memorize. The code is the truth.

## What's done as of last session

- Discovery widened: Overpass query now matches eight food-serving amenities (`restaurant|cafe|fast_food|pub|bar|biergarten|food_court|ice_cream`) instead of just `restaurant`. The `amenity` field is propagated through SSE to the FE.
- One-hop menu-link crawl added to scanner: when both pdf and generic adapters yield empty on the homepage, follows up to 4 same-host links matching `menu|menü|menue|speisekarte|karte|produkte|gerichte|essen|food|drinks|getränke` and runs both adapters on each. Resolved #6 (kennys → 8 dishes via `/produkte/`) and rounded out #4 (bruder homepage → `/speisekarte` PDF → 7 dishes).
- **#11 radius search ("Near me") landed.** Segmented control above the search row, radius pills 500m / 1km / 2km. Backend hard-clips to Austria via Overpass `area["ISO3166-1"="AT"]`. Two endpoints: `GET /api/restaurants-by-radius` and SSE `GET /api/restaurants/scan-by-radius`. Streaming/keepalive/cancellation logic shared via `_stream_scan`.
- **#12 soft-natural UI redesign.** Dropped the yellow-chartreuse brand accent in favor of soft leaf greens (`--leaf`, `--leaf-d`); replaced editorial offset block shadows with a rounded paper panel + soft drop shadow; bumped form controls to 54px with bordered fields; segmented tabs and real selectable radius pills; CTA scaled up. Typography unified — Albert Sans for every interactive control (inputs, dropdown options, tabs, radius pills, CTA, link buttons), Fraunces display reserved for editorial accents only. Custom `field-select` component replaces the native `<select>` (smart up/down flip, follows trigger on scroll). Result rows became standalone gap-separated cards (paper bg, sage border, soft drop shadow) — `Nº 01` numbering removed.
- **#13 pagination.** Results paginate at 10/page with smart ellipsis past 7 pages; smooth-scrolls back to top of results on page change.
- **#14 stop control.** During an in-flight scan the green "Begin scan" CTA flips to a rust "Stop" button. Click → `streamSub.unsubscribe()` → `EventSource.close()` → backend's existing `request.is_disconnected()` polling cancels remaining scan tasks. Already-found results stay rendered.
- **Overpass resilience.** `services/overpass._run_query` retries up to 3 attempts with 1s/2s backoff on 429/502/503/504 and `httpx.RequestError`. Persistent failures convert to `HTTPException(503)` at the router. Frontend `EventSource` distinguishes connection-failed-before-any-event from end-of-stream so a backend 503 surfaces as an inline error rather than an indefinite spinner.
- **Loading spinner.** Replaces the trailing arrow on the CTA during locate / scan; `@keyframes cta-spin` lives in global `styles.scss` (component-scoped keyframes were intermittently not applied), with a `prefers-reduced-motion` override so essential feedback always rotates.
- **Z-index fix for dropdown over results.** `.control` and `.results-section` both use `animation: rise … both`, which permanently holds `transform: translateY(0)` and creates sibling stacking contexts at z-auto — `.results-section` was painting over the dropdown because it's later in DOM. Fix: explicit `z-index: 2` on `.control`. Field-select `:host` also has `z-index: 50` as belt-and-suspenders.
- **#15 SSRF hardening landed.** New `services/safe_fetch.py` resolves every outbound URL via `getaddrinfo` and rejects `is_private | is_loopback | is_link_local | is_reserved | is_multicast | is_unspecified` addresses, with manual redirect walking and per-hop revalidation. Wired into `scanner.py` (initial fetch, menu-link crawl) and `adapters/pdf.py` (HEAD + GET for every PDF candidate). `httpx.AsyncClient` switched to `follow_redirects=False`. End-to-end-verified: `scan_restaurant` returns no-menu fallback for metadata IPs, loopback, and RFC1918 addresses. Integration test (`tests.scan_examples`) still passes for the five real-world URLs.
- **#16 unused `/api/restaurants/{id}/vegan` route deleted.** Zero FE callers. Routes left: list, list-by-radius, scan, scan-by-radius, health.

## What's pending (from `todos.md`)

- **#21 Impressum** — Austrian *E-Commerce-Gesetz § 5 (1)* requires every publicly accessible site served from / targeting Austrian users to display name + address + email. Applies to non-commercial hobby sites too. Static page or footer modal.
- **#22 OSM attribution** — ODbL § 4.3 requires "© OpenStreetMap contributors" with a link to <https://www.openstreetmap.org/copyright> wherever Overpass data is surfaced. Currently nowhere.
- **#23 privacy notice** — GDPR Art. 13. Static page covering: search terms / IP / geolocation, retention, processors (Scaleway, Codeberg, Google Fonts, counter.dev if kept), data subject rights, contact.
- **#17** — move frontend `apiUrl` (`services/restaurant.ts:35`) into Angular `environments/` files; required for the Codeberg Pages deploy to point at the production API.
- **#18** — restrict `CORSMiddleware` `allow_origins` to the deployed Codeberg/custom domain + localhost.
- **#19** — replace cache-key sanitizer in `services/cache.py` with a SHA-256 hash so future cache keys can't path-traverse.
- **#20** — add SRI hash to (or remove) the `cdn.counter.dev` script in `index.html`; add a CSP header.
- **#5** — `zuminderhof.at` likely serves an image-only PDF. Add OCR (`pytesseract` + `pdf2image` + Tesseract + Poppler) **only as a fallback** when `pdfplumber.extract_text()` returns empty/near-empty. If extraction works but no vegan keyword matches, do NOT OCR.
- **#10** — cleanup pass. Folds in the unused `RestaurantCard.index` input.

## Hard constraints — don't cross these without asking

- **No headless browser** (Playwright/Selenium). User explicitly punted on this for foodora/lieferando, and it stays punted for kennys.
- **Austria only.** 4-digit zip, AT in Overpass. Don't generalize.
- **OCR is fallback-only.** Never run on PDFs that already yield text.
- **Investigate before implementing** when the task description is "find out why X" — don't pre-build a fix for a hypothesis.

## Working style this user prefers

- Terse. No trailing summaries restating the diff.
- Ask before adding deps, changing scope, or doing destructive git operations. Use `AskUserQuestion` when there's a real fork (especially for #5/#6).
- Default to no comments and no docstrings unless the *why* is non-obvious.
- Confirm with a build (`ng build --configuration development` for FE; `python -m tests.scan_examples` for BE) before reporting work done.
- The user runs Windows + bash. Use forward slashes in paths and Unix shell syntax.
- Don't auto-commit. The user commits manually.

## Suggested first move

**Legal first**: #21 Impressum, #22 OSM attribution, #23 privacy notice — these are the actual launch blockers under Austrian law / GDPR / ODbL. Then #17 (environment-based `apiUrl`, otherwise the production build calls `localhost:8000` and the site is dead in production), #18 (CORS lockdown), #19 (cache-key SHA-256), #20 (counter.dev SRI + CSP). After legal + deploy work lands, pick up #5 (OCR fallback) and #10 (cleanup, including the unused `RestaurantCard.index` input).

**Note (2026-05-10):** all the items above are now done **and the site is live**. Frontend on Codeberg Pages serving <https://sprout-scout.at/>; backend on Scaleway Serverless Containers (`fr-par`, scale-to-zero, S3-backed cache) at <https://api.sprout-scout.at/>. DNS landed via easyname after switching from the initial registrar. Smoke test (zip + radius + legal modals + OSM attribution) passed end-to-end. See `startup.md` for the live state and the README *Backend → Scaleway Serverless Containers* section for the deploy walkthrough.

**Note (2026-05-13):** post-launch round of fixes shipped — see `todos.md` *Post-launch fixes*. (1) #24 stuck-SSE bug: `pdfplumber.open(...)` was a synchronous CPU-bound call inside an async coroutine, blocking the event loop and freezing the SSE stream whenever the last batch of 8 scans hit a slow/large PDF. Now wrapped in `asyncio.to_thread` plus a 10 MB PDF size cap; per-scan timeout dropped 25 → 20 s. (2) #25 visual: removed the trailing `↗` arrow from the Begin scan / Stop CTA. (3) www cert is now valid (was briefly 421 at flip time). Active future work: v2.1 OCR fallback (see todos.md) — still only worth it once a second image-only PDF surfaces.

```bash
cd backend && venv/Scripts/python -m tests.scan_examples
```

If the user gave you a specific instruction in their message, that overrides this suggestion.
