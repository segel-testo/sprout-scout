# Sprout Scout — Startup

Resume here after a break.

## Project

- **Source repo (GitHub):** https://github.com/segel-testo/sprout-scout
- **Deploy repo (Codeberg):** https://codeberg.org/heislsheimen/sprout-scout
- **Local path:** `C:\Vali\coding\sprout-scout`

## Where we stopped (2026-05-09)

All v1 hardening shipped — legal pages, env-driven `apiUrl`, CORS lockdown, SHA-256 cache keys, real counter.dev ID, dead-code cleanup. **Latest commit on `main`: `62e7870`.**

Frontend successfully deployed to Codeberg Pages once: `pages` branch on `codeberg.org/heislsheimen/sprout-scout` is live. Codeberg returns `307 → https://www.sprout-scout.at/` (correct behavior — `.domains` is in the build), confirming the bundle is up.

**Backend host pivoted again (2026-05-09):** Briefly attempted Northflank, but their "free Sandbox" turned out to meter compute on top of the structural slot (~$5.40/month at smallest size), so it isn't actually free. Pivoted to **Scaleway Serverless Containers** (`fr-par`) with **scale-to-zero** + cache backed by **Scaleway Object Storage**. Bill: €0/month within the recurring monthly free tier. Trade-off: 1–3s cold start on the first request after a 15-min idle window (acceptable for hobby traffic). Full reasoning + walkthrough in README *Backend → Scaleway Serverless Containers*.

**Backend is live.** Image built via GitHub Actions (`.github/workflows/build-backend.yml`) and pushed to `rg.fr-par.scw.cloud/sprout-scout/sprout-scout-api:latest`. Container is deployed and answering on `https://<host>.functions.fnc.fr-par.scw.cloud`. Cache writes verified end-to-end against Object Storage bucket `sprout-scout-cache`.

**What's blocking the live site:**
1. **DNS** for `sprout-scout.at` — domain bought but no provider confirmation / panel access yet. When available, add three records:
   - `CNAME www → heislsheimen.codeberg.page` (frontend)
   - `A`/`AAAA` for the apex → Codeberg's published IPs (frontend)
   - `CNAME api → <container-host>.functions.fnc.fr-par.scw.cloud` (backend)
2. **Custom domain link in Scaleway** — once DNS resolves, add `api.sprout-scout.at` to the container's custom domains panel; Scaleway auto-provisions a Let's Encrypt cert.

## First message to Claude (resume)

> Resume sprout-scout. Read `startup.md`, `todos.md`, and the *Deployment* section of `README.md`. Summarize: what's the latest deploy state, what's still blocked on DNS, what's the next concrete step?

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
