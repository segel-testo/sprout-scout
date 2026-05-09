# Sprout Scout — Startup

Resume here after a break.

## Project

- **Source repo (GitHub):** https://github.com/segel-testo/sprout-scout
- **Deploy repo (Codeberg):** https://codeberg.org/heislsheimen/sprout-scout
- **Local path:** `C:\Vali\coding\sprout-scout`

## Where we stopped (2026-05-09)

All v1 hardening shipped — legal pages, env-driven `apiUrl`, CORS lockdown, SHA-256 cache keys, real counter.dev ID, dead-code cleanup. **Latest commit on `main`: `62e7870`.**

Frontend successfully deployed to Codeberg Pages once: `pages` branch on `codeberg.org/heislsheimen/sprout-scout` is live. Codeberg returns `307 → https://www.sprout-scout.at/` (correct behavior — `.domains` is in the build), confirming the bundle is up.

**Backend host decision changed (2026-05-09):** moved off Render in favor of **Northflank** (free Sandbox tier, EU region, **always-on** — no idle sleep). Reasoning captured in `todos.md` step 14. Render's free tier sleeps after 15 min idle; Scaleway/Clever Cloud were also evaluated but Scaleway's ephemeral filesystem breaks our file cache and Clever Cloud has no free tier.

**What's blocking the live site:**
1. **DNS** for `sprout-scout.at` — domain bought but no provider confirmation / panel access yet. Once available, add `CNAME www → heislsheimen.codeberg.page` and `A`/`AAAA` for the apex pointing at Codeberg's published IPs.
2. **Backend deploy** — Northflank service not yet created. Pick an EU region, deploy from `backend/` via Python buildpack with start command `uvicorn main:app --host 0.0.0.0 --port $PORT`. Set `ALLOWED_ORIGINS=https://www.sprout-scout.at,https://sprout-scout.at` under env vars; add `api.sprout-scout.at` as a custom domain; CNAME `api` → `<service>.code.run` at the DNS provider. Full walkthrough in README *Backend → Northflank*.

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
