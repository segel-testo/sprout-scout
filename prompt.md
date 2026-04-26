# Continuation prompt — Sprout Scout

Paste this verbatim at the start of a new session.

---

You are continuing work on **Sprout Scout** at `C:\Vali\coding\sprout-scout`. It's an Austria-only web app that finds vegan dishes at restaurants via 4-digit zip code (Angular 21 frontend + FastAPI backend + OpenStreetMap/Overpass for restaurant data + an adapter pipeline that scans menu pages and PDFs).

## Read these first, in this order

1. `README.md` — full architecture, API contract, design decisions. Authoritative.
2. `todos.md` — the live work plan. Items 1–4 and 6 are done; 5 and 7 are pending. **Read this even if you think you remember the state — it's the source of truth.**
3. `plan.md` (if present) — older full implementation plan, mostly historical now.

Skim, don't memorize. The code is the truth.

## What's done as of last session

- Discovery widened: Overpass query now matches eight food-serving amenities (`restaurant|cafe|fast_food|pub|bar|biergarten|food_court|ice_cream`) instead of just `restaurant`. Was the root cause for #4 — Bruder und Schwester is `amenity=cafe`. The `amenity` field is now propagated through SSE to the FE.
- One-hop menu-link crawl added to scanner: when both pdf and generic adapters yield empty on the homepage, follows up to 4 same-host links matching `menu|menü|menue|speisekarte|karte|produkte|gerichte|essen|food|drinks|getränke` and runs both adapters on each. Also fixed the base URL to use the post-redirect `response.url` so subdomain redirects (e.g. `kennys.at` → `www.kennys.at`) don't break same-host filtering. Resolved #6 (kennys → 8 dishes via `/produkte/`) and rounded out #4 (bruder homepage → `/speisekarte` PDF → 7 dishes).
- Restaurant card now shows an amenity tag (Restaurant / Café / Pub / …) absolutely positioned in the top-right corner, matching the card's 20px padding. Primary-link button moved to bottom-right (`align-items: flex-end`) so it doesn't collide with the tag.

## What's pending (from `todos.md`)

- **#5** — `zuminderhof.at` likely serves an image-only PDF. Add OCR (`pytesseract` + `pdf2image` + Tesseract + Poppler) **only as a fallback** when `pdfplumber.extract_text()` returns empty/near-empty. If extraction works but no vegan keyword matches, do NOT OCR.
- **#7** — cleanup pass. Includes deciding whether to delete `GET /api/restaurants/{id}/vegan` (no FE callers since step 1).

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

Open `todos.md`, pick #5 (OCR fallback) or #7 (cleanup). For #5, start by downloading `zuminderhof.at`'s PDF and confirming `pdfplumber.extract_text()` actually returns empty before adding any deps. For #7, grep for callers of `GET /api/restaurants/{id}/vegan` and the `getVeganDishes` shape in the FE.

```bash
cd backend && venv/Scripts/python -m tests.scan_examples
```

If the user gave you a specific instruction in their message, that overrides this suggestion.
