# Sprout Scout — Startup

Resume here after a break.

## Project

- **Source repo (GitHub):** https://github.com/segel-testo/sprout-scout
- **Deploy repo (Codeberg):** https://codeberg.org/heislsheimen/sprout-scout
- **Local path:** `C:\Vali\coding\sprout-scout`

## Where we stopped (2026-05-13)

**The site is live at <https://sprout-scout.at/>.** Backend at <https://api.sprout-scout.at/> (Scaleway, fr-par, scale-to-zero with S3-backed cache). Frontend on Codeberg Pages. `www.sprout-scout.at` cert is now provisioned and 307-redirects to the apex cleanly.

DNS landed via easyname (domain switched from the initial registrar). Records: apex `A 217.197.84.141` + `AAAA 2a0a:4580:103f:c0de::2` (Codeberg), apex `TXT sprout-scout.heislsheimen.codeberg.page` (Codeberg's apex owner-lookup — without it pages-server returns 424 *"could not obtain repo owner from custom domain"*), `www CNAME sprout-scout.heislsheimen.codeberg.page` (project-site format, **not** `heislsheimen.codeberg.page`), `api CNAME sproutscout6ac23ac7-sprout-scout-api.functions.fnc.fr-par.scw.cloud` + custom domain added on the container so Scaleway auto-provisioned a Let's Encrypt cert.

`.domains` order is `sprout-scout.at` then `www.sprout-scout.at`. Apex is canonical (default URL 307-redirects there). Smoke test passed: zip search, "Near me" radius, Impressum + Privacy modals, OSM attribution.

**Latest fixes (2026-05-13):**
- Stuck SSE scan resolved (#24). `pdfplumber` parsing was blocking the event loop synchronously, freezing the SSE stream when a slow/large PDF hit the final batch (e.g. `1200`). Now wrapped in `asyncio.to_thread` + a 10 MB PDF size cap. Per-scan timeout dropped 25 → 20 s.
- Removed the trailing `↗` arrow from the Begin scan / Stop CTA in both zip and radius modes (#25).

## First message to Claude (resume)

> Resume sprout-scout. Read `startup.md`, `todos.md`, and the *Deployment* section of `README.md`. Anything in the v2 backlog still worth picking up?

## Run it locally

Open two terminals at `C:\Vali\coding\sprout-scout`.

**Backend** → http://localhost:8000
```powershell
cd backend; venv\Scripts\python -m uvicorn main:app --reload
```

**Frontend** → http://localhost:4200
```powershell
cd frontend; npx ng serve
```

## Regression check

```powershell
cd backend; venv\Scripts\python -m tests.scan_examples
```

Expected: Zen → delivery link, Akakiko → dishes, Pizzeria Ofenbarung + Mister Beans → no_menu fallback, Bruder & Schwester → dishes from PDF.
