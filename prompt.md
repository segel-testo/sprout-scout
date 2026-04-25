# Continuation prompt — Sprout Scout

Paste this verbatim at the start of a new session.

---

You are continuing work on **Sprout Scout** at `C:\Vali\coding\sprout-scout`. It's an Austria-only web app that finds vegan dishes at restaurants via 4-digit zip code (Angular 21 frontend + FastAPI backend + OpenStreetMap/Overpass for restaurant data + an adapter pipeline that scans menu pages and PDFs).

## Read these first, in this order

1. `README.md` — full architecture, API contract, design decisions. Authoritative.
2. `todos.md` — the live work plan. Items 1–3 are done; 4–7 are pending. **Read this even if you think you remember the state — it's the source of truth.**
3. `plan.md` (if present) — older full implementation plan, mostly historical now.

Skim, don't memorize. The code is the truth.

## What's done as of last session

- Frontend simplified to a single auto-scan flow. Toggle removed, on-demand mode gone.
- Restaurant card is now flat: name, "Vegan options found" badge, address, phone, one primary-link button (foodora link → website → Google Maps fallback).
- `services/restaurant.ts` pruned: only `scanStream` remains; `getRestaurants` and `getVeganDishes` are gone, plus unused types.
- Backend untouched. The SSE route still filters zero-dish restaurants out before emitting.

## What's pending (from `todos.md`)

- **#4** — `bruderundschwester.com/speisekarte` not appearing in the UI even though the integration test asserts dishes from it. **Investigate first**: run `backend/tests/scan_examples.py`, see whether it's a backend regression or a discovery-layer mismatch (Overpass `website` field vs the URL the test uses).
- **#5** — `zuminderhof.at` likely serves an image-only PDF. Add OCR (`pytesseract` + `pdf2image` + Tesseract + Poppler) **only as a fallback** when `pdfplumber.extract_text()` returns empty/near-empty. If extraction works but no vegan keyword matches, do NOT OCR.
- **#6** — `kennys.at` menu not picked up. **Investigate first**: curl the homepage, find out whether the menu is one click deep, JS-rendered, or just a matcher gap on "KENNY'S VEGAN". Pick the narrowest fix. Headless browser is OUT of scope.
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

Open `todos.md`, pick #4 or #6 (cheapest — both start with "investigate"), and run the integration test to see current backend behavior. That single command informs both items.

```bash
cd backend && venv/Scripts/python -m tests.scan_examples
```

If the user gave you a specific instruction in their message, that overrides this suggestion.
