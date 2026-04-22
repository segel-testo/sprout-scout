# Plan: Reading Menus from Restaurant Websites

> **Addendum — what actually shipped (2026-04)**
>
> This document is the original plan. Most of it was built as designed; see the main [README](./README.md) for the current state of the system. One part deviated materially:
>
> - **Phases 3 & 4 (Foodora / Lieferando adapters).** The plan called for parsing Foodora's `__NEXT_DATA__` JSON and Lieferando's `cw-api.takeaway.com` endpoint. In practice: Foodora/mjam pages don't SSR the menu (it loads via XHR post-render), and both platforms return 403 to anonymous `httpx` clients — the XHR endpoints require browser-set cookies / tokens. The "Bot protection" risk listed at the bottom of this plan is what we actually hit.
> - **What we shipped instead: option 2, link-out.** When the scanner detects a Foodora/mjam/Lieferando URL (direct or linked from the homepage), it returns a `delivery_link` payload and the frontend renders a "View menu on foodora →" button. No menu text is extracted for those cases. A headless-browser path (playwright) remains possible but is not implemented.
>
> Everything else in this plan (extractor hardening, PDF handling, no-menu fallback, orchestrator, SSE bulk scan, toggle, integration test) shipped as described.

---

## Goal

Improve `backend/services/scanner.py` so it can find vegan dishes across the very different ways restaurants expose their menus. Use the 5 example URLs in `url-collection.txt` as representative cases.

## The 5 cases and how we'll handle each

| # | URL | Menu location | Strategy |
|---|-----|---------------|----------|
| 1 | zen-restaurant.at | Behind foodora ("Online bestellen") | **Foodora adapter** |
| 2 | akakiko.at | On site, keywords present | **Generic HTML scan** (already mostly works) |
| 3 | pizzeria-ofenbarung (resmio) | No menu online | **No-menu fallback** |
| 4 | misterbeans.at | No menu online | **No-menu fallback** |
| 5 | bruderundschwester.com/speisekarte | PDF embedded on page | **Hardened PDF handling** |

## Architecture change

Today `scanner.py` has a single generic path. Replace with an adapter pattern so each source type has its own module:

```
backend/services/
├── scanner.py              # Orchestrator: pick adapter, aggregate results
├── extractor.py            # Shared keyword matching (vegan detection)
└── adapters/
    ├── __init__.py
    ├── generic.py          # Plain HTML + keyword scan (current logic)
    ├── pdf.py              # All PDF embedding methods
    ├── foodora.py          # Foodora JSON menu
    └── lieferando.py       # Lieferando JSON menu
```

Orchestrator order — **stop on first adapter that returns ≥1 dish**, don't run all of them (cheaper, and Phase 7 amplifies every extra request by ~30 restaurants):

1. Is the URL a foodora / lieferando URL? → that adapter. Done.
2. Otherwise fetch the homepage once.
3. Does the homepage link to foodora / lieferando? → delivery adapter. If it returns dishes, done.
4. Does the page embed or link a PDF? → PDF adapter. If it returns dishes, done.
5. Otherwise → generic HTML adapter.
6. Dedupe the result.
7. If total dishes = 0 → return no-menu fallback payload (see Phase 5).

---

## Phase 1 — Extractor hardening (keyword-based, decision 3a)

Move keyword logic out of `scanner.py` into `extractor.py` and improve it:

- **Negation detection.** Skip matches when preceded by "kein", "keine", "ohne", "no", "not", "without", "leider nicht", etc. within the same sentence.
- **Legend tables (two-pass).** First pass: scan the whole document for legend entries like `V = vegan`, `★ vegan`, `(v) vegan`, `ⓥ vegan`, building a symbol → label map. Second pass: scan dish lines for those symbols and treat a match as a vegan hit. Needs two passes because the legend can appear before, after, or alongside the dishes — one-line matching won't catch it.
- **"On request" detection.** Phrases like "auf Anfrage vegan", "vegan available", "vegan option" → lower confidence (0.3 instead of 0.6+), not full match.
- **Better line boundaries.** HTML text collapsed with `separator=" "` produces run-on lines. Split on `.`, `•`, `|`, and common menu separators too.
- **German wordlist tune-up.** Add "veganes Gericht", "rein pflanzlich", "100% vegan", "vg", drop "vegetarisch" (not the same as vegan — currently a false positive source).

Confidence formula stays similar: base 0.4, +0.2 per distinct keyword, capped at 1.0. Legend-matched dishes start at 0.9 (explicit marker).

## Phase 2 — PDF handling (decision 4)

Current scanner only finds PDFs linked via `<a href="...pdf">`. Expand to all embedding methods:

- `<a href>` where URL ends in `.pdf` (current)
- `<a href>` where URL has no extension but the HEAD response returns `application/pdf` (some PDFs are served from `/menu` or `?download=1`)
- `<iframe src="...pdf">`
- `<object data="...pdf">`
- `<embed src="...pdf">`
- Links containing known PDF viewer patterns (e.g. resmio / PDF.js viewer URLs with `?file=...pdf`)

Also fix the existing relative-URL bug: use `urllib.parse.urljoin` instead of string concatenation.

**Verification needed before implementing:** URL #2 (akakiko.at/lieferservice`#veggie`) uses a fragment. Fragments don't travel over HTTP, so the server returns the unfiltered page. Worth fetching once and checking whether the unfiltered HTML contains the full menu, or whether the `#veggie` tab is JS-populated (which `httpx` won't see). If it's JS-populated we'd need a playwright fallback for this specific case, or accept reduced coverage.

Expected outcome for URL #5 (bruderundschwester): PDF is found and parsed regardless of how it's embedded.

## Phase 3 — Foodora adapter (decision 1c)

- **Detection.** URL host is `foodora.at` or `foodora.com`, OR homepage contains a link to one.
- **Extraction.** Foodora runs on Next.js — every page ships a `<script id="__NEXT_DATA__">` with the full menu as JSON. Parse that rather than scraping DOM.
- **Parsing.** Walk `menuCategories[].products[]`. Each product has `name`, `description`, and sometimes `dietary` / `tags` with explicit `vegan` flag.
- **Vegan detection.** First check explicit tags. If none, run Phase 1 extractor on `description`.
- **Request hygiene.** Realistic User-Agent header; one request per restaurant; rely on the 1-week cache.

Expected outcome for URL #1 (zen): foodora link is followed, dishes come back with high confidence.

## Phase 4 — Lieferando adapter

Same shape as foodora, different internals. Lieferando exposes a JSON API at `https://cw-api.takeaway.com/api/v33/restaurant?slug={slug}` (seen via their frontend). Parse `menu.categories[].products[]`. Same vegan-detection flow: tags first, extractor second.

If their API starts requiring auth or Cloudflare blocks us, fall back to parsing the embedded JSON on the HTML page (same pattern as foodora's `__NEXT_DATA__`). Out of scope for this plan: headless browser (playwright) for heavy bot protection.

## Phase 5 — No-menu fallback (decision 2: no Google API)

When orchestrator finishes with zero dishes, don't return an empty list. Return a structured payload the frontend can render as a helpful card:

```json
{
  "restaurant_id": "...",
  "dishes": [],
  "no_menu": true,
  "fallback_links": [
    {"label": "Restaurant website", "url": "https://..."},
    {"label": "Search on Google Maps", "url": "https://www.google.com/maps/search/?api=1&query=..."},
    {"label": "View on OpenStreetMap", "url": "https://www.openstreetmap.org/..."}
  ],
  "osm_diet_vegan": "yes"   // one of "yes" | "only" | "limited" | null
}
```

Also surface the OSM `diet:vegan` tag (`yes` / `only` / `limited`) if Overpass returned it — currently ignored. This is a free, honest signal for restaurants without a menu online.

Expected outcome for URLs #3 and #4: user sees "No menu found online — check these sources" with working links, instead of a silent empty list.

Frontend change needed: `restaurant-card` component renders the no-menu state. Small scope — new conditional block.

## Phase 6 — Orchestrator rewrite

`scanner.py` becomes a thin dispatcher that tries adapters in order and stops on the first one that returns dishes:

```python
async def scan_restaurant(restaurant_id, website, osm_tags):
    if is_foodora(website):
        dishes = await foodora.scan(website)
    elif is_lieferando(website):
        dishes = await lieferando.scan(website)
    else:
        page = await fetch(website)
        dishes = []
        if (link := find_foodora_link(page)):    dishes = await foodora.scan(link)
        if not dishes and (link := find_lieferando_link(page)):
                                                  dishes = await lieferando.scan(link)
        if not dishes:                            dishes = await pdf.scan(page, base=website)
        if not dishes:                            dishes = await generic.scan(page, base=website)

    dishes = dedupe(dishes)
    if not dishes:
        return no_menu_fallback(restaurant_id, website, osm_tags)
    return {"restaurant_id": restaurant_id, "dishes": dishes}
```

Dedupe within one restaurant by normalized dish name (lowercase, stripped) to avoid duplicates when a menu appears in multiple places.

**Scan-result caching.** Wrap `scan_restaurant` in the same file-based cache used for Overpass (1-week TTL, key = restaurant id + website URL). Without this, Phase 7's bulk scan re-hits every external site on every search. If `cache.py` today only handles Overpass, extend it to accept a generic `(namespace, key) → value` interface.

---

## Phase 7 — Bulk scan on search + streaming results

Current flow is lazy: user picks a restaurant, then the scanner runs. Change it so scanning kicks off immediately after Overpass returns the restaurant list, and the frontend reveals results progressively.

**Flow:**

1. User submits zip code.
2. Backend calls Overpass → returns the restaurant list (capped at 30 — see below).
3. Frontend shows a loading spinner and scan counter (e.g. "Scanning 14 restaurants...").
4. Backend fans out scans for all restaurants in parallel (e.g. `asyncio.gather` with a concurrency cap of ~5–10 to avoid hammering external sites).
5. As each scan finishes **with at least one vegan dish**, the restaurant appears in the list. Restaurants with zero dishes are **hidden entirely** in auto-scan mode (the no-menu fallback payload is only rendered in on-demand mode — auto-scan is a filter).
6. When all scans complete and the visible list is still empty → show "No vegan dishes found in this area. Try a different zip code."

**Restaurant cap.** Overpass can return 50+ results for busy urban zips. Cap the bulk scan at 30 restaurants and show "Showing first 30 of N — refine your search" when trimmed. Keeps total scan time bounded and avoids rate-limiting.

**Backend change.** Add a streaming endpoint so results arrive as they finish, not all at once:

- `GET /api/restaurants/scan?zip_code=1010&country=AT` — Server-Sent Events (SSE) stream.
- Events:
  - `restaurant` — payload = restaurant + dishes. Emitted only on positive hits.
  - `progress` — payload = `{scanned, total}`. Emitted after every scan completes, whether the scan returned dishes, zero dishes, or failed. Keeps the counter honest.
  - `error` — payload = `{restaurant_id, reason}`. Emitted on scan failure (timeout, HTTP error, parse error). Frontend can count or display these separately.
  - `done` — emitted once when `scanned == total`. Frontend stops the spinner here.

SSE chosen over WebSockets: one-way, works over plain HTTP, supported natively by browsers via `EventSource`. FastAPI has `sse-starlette` for this.

**Frontend change.** `search` component subscribes to the SSE stream:
- On `restaurant` event → append to visible list, render via `restaurant-card`.
- On `progress` event → update counter.
- On `error` event → increment failure counter (optional display: "3 sites couldn't be checked").
- On `done` event → stop spinner. If list empty, show "no vegan restaurants found" message.

**Cancellation.** If the user submits a new zip code while a stream is still open, the frontend must close the active `EventSource` before opening a new one. Backend-side, handle `asyncio.CancelledError` on client disconnect so in-flight scans stop cleanly rather than running to completion for a client that's gone.

**Why this matters.** With ~10–30 restaurants per zip code and scans taking 2–15 seconds each, a blocking "scan everything then return" request would feel broken. Streaming gives the user the first positive result in ~2s and keeps the page lively. The 1-week cache means a second search of the same zip code is near-instant.

**Mode toggle (auto-scan vs on-demand).** Put a toggle in the search bar that switches between two behaviors:

- **On-demand** (default): Overpass returns, all restaurants show immediately as plain cards, no scanning happens until the user clicks a card to expand it — then `GET /api/restaurants/{id}/vegan` fires for that one. This matches the original behavior and avoids bulk-scanning random hosts on a first visit.
- **Auto-scan**: backend streams dishes via SSE, only vegan-positive restaurants appear. Good for "where can I eat vegan near me?" once the user trusts the tool enough to opt in.

Both modes coexist — the existing per-restaurant endpoint stays, the new SSE endpoint is added alongside it. The frontend picks which one to call based on the toggle. UI-wise: a simple two-state switch labeled something like "Show all, scan on click / Auto-scan all", persisted to `localStorage` so the user's preference sticks across sessions.

Rationale for on-demand default: auto-scan kicks off 8 concurrent requests to small-business websites on the first pageload, before any cache is warm. On-demand is politer and faster to first paint; users who want filtering can flip the toggle and have it remembered.

**When each mode is useful.**
- Auto-scan is better when the user just wants "where can I eat vegan near me?" — results are filtered and ranked for them.
- On-demand is better when the user wants to browse all restaurants (maybe they're checking a specific place they already know), or when they're on a slow connection and don't want 30 parallel scans kicked off automatically.

**Concurrency / politeness.**
- Cap at ~8 concurrent scans (per backend worker) so we don't get rate-limited by foodora/lieferando/random restaurant hosts.
- Per-host concurrency limit of 1 (don't hit foodora.at with 8 parallel requests).
- Per-scan timeout of 20s — if a restaurant is slow/broken, move on rather than blocking the whole batch.

**Risk.** Bulk scanning amplifies any politeness issue with external hosts. The cache + concurrency caps are the main mitigation. Also: SSE connections held open through some proxies/CDNs can be a deploy headache — worth verifying on Render before shipping.

Expected outcome: user searches "1010" → spinner + counter → vegan restaurants pop in one by one within a few seconds → final count or empty-state message.

## Validation

Acceptance test: run scanner against each of the 5 URLs, expect:

| URL | Expected result |
|-----|-----------------|
| zen-restaurant.at | ≥1 vegan dish via foodora adapter |
| akakiko.at | ≥1 vegan dish via generic adapter |
| pizzeria-ofenbarung | `no_menu: true` with 3 fallback links |
| misterbeans.at | `no_menu: true` with 3 fallback links |
| bruderundschwester.com | ≥1 vegan dish via PDF adapter |

Add a small integration test script `backend/tests/scan_examples.py` that hits all five and prints a summary. Useful for regression checks when an adapter breaks.

## Risks / known limitations

- **Adapter rot.** Foodora and Lieferando will change their internal JSON shape occasionally. Expect to update each adapter ~1–2× per year.
- **Bot protection.** If either platform adds Cloudflare challenges, the JSON approach breaks and we'd need playwright (out of scope).
- **Keyword approach ceiling.** Dishes not explicitly labeled (e.g. "Falafel wrap") won't be detected. Decision 3a accepts this. Mitigation: legend handling (Phase 1) catches most cases since menus typically mark vegan items with a symbol.
- **Foodora/Lieferando ToS.** Using their undocumented JSON is technically against their terms. Risk is low for a small public tool but worth knowing.
- **Dedupe is strict-match.** "Falafel Wrap" and "Falafel Wrap mit Hummus" from two sources won't merge. Acceptable for now; revisit with fuzzy matching if duplication becomes noisy in practice.

## Rough order of work

1. Phase 1 (extractor) + Phase 2 (PDF) — handles URLs #2 and #5, low risk
2. Phase 5 (fallback) + Phase 6 (orchestrator skeleton) — handles #3 and #4, needs frontend tweak
3. Phase 3 (foodora) — handles #1
4. Phase 4 (lieferando) — bonus coverage, not needed for the 5 examples but important in practice
5. Phase 7 (bulk scan + SSE streaming) — changes search UX; do after adapters are solid so each scan is worth surfacing
