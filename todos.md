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

## 4. Bruderundschwester not appearing — investigate

Integration test currently asserts dishes from `bruderundschwester.com/speisekarte`. Two hypotheses:

1. **Test still passes** → backend finds dishes, frontend drops them. Likely cause: name/address mismatch between OSM and the website's domain, so the SSE stream never reaches this restaurant in zip 1010 (or wherever it lives). Check whether it appears in the Overpass result for its zip at all.
2. **Test fails** → PDF extractor regression. Re-run `python -m tests.scan_examples`, inspect.

Steps:
- Run the integration test, capture output.
- If pass: query Overpass for the actual zip, confirm the restaurant is in the response, confirm its `website` field matches the URL the scanner can hit.
- If fail: bisect — does `pdf.py` find the PDF? Does `pdfplumber` extract text? Does `extractor.py` match "vegan"? Fix the broken stage.

## 5. zuminderhof.at — image-only PDF fallback

**Rule:** OCR runs *only* when normal text extraction returns empty/whitespace. If extraction yields text but no vegan keyword matches, no OCR.

- `backend/services/adapters/pdf.py` — after `pdfplumber.extract_text()`, check whether the result is empty (or below a small whitespace threshold, e.g. <20 non-whitespace chars across all pages).
- If empty → fall through to OCR path: rasterize each page with `pdf2image` (or `pdfplumber`'s page images), run `pytesseract.image_to_string`, concatenate.
- New deps: `pytesseract`, `pdf2image`. System deps: Tesseract binary, Poppler (for pdf2image). Document in `backend/requirements.txt` and a "System dependencies" section in README.
- Add a per-PDF timeout cap on the OCR path (e.g. 15s) so a 50-page scanned menu doesn't blow the 25s scan timeout for the whole restaurant.
- Verify against `zuminderhof.at`: download the PDF, confirm `extract_text()` returns empty, confirm OCR finds "vegan".

## 6. kennys.at — investigate first

Curl the homepage, locate how the menu is reached. Three plausible outcomes:

- **Static link the scanner missed** (e.g., menu page linked from a non-`<a>` element, or one click deeper than the generic adapter follows). Fix: extend generic adapter to follow obvious "menu" / "speisekarte" links one level.
- **Same-origin XHR / JS-rendered**. Decision needed at that point — most likely: document as known limitation and add to the no_menu fallback path. Headless browser stays out.
- **The menu IS reachable but extractor misses "KENNY'S VEGAN"** because of formatting (all-caps, apostrophe, line break splitting "VEGAN" from context). Tune the matcher.

Don't pre-build any of this — investigate, then pick the narrowest fix.

## 7. Cleanup pass (last)

After 4–6 land:
- Search for unreferenced functions/components/imports across `backend/` and `frontend/src/`.
- Specifically check whether `GET /api/restaurants/{id}/vegan` still has callers (Angular service, tests). If not, delete the route + its handler. **Note: as of step 1, the FE no longer calls it — only the integration test path may still use it.**
- Look for duplicated extraction/normalization logic between `extractor.py` and the adapters.
- Run the integration test again as a final regression check.

---

## Suggested order

1. Investigate #4 and #6 (cheap, results may shrink other steps).
2. #5 OCR path (backend, isolated).
3. #7 cleanup.

## Out of scope (confirmed)

- Headless browser for foodora/lieferando/kennys.
- OCR on non-PDF image menus.
- Countries other than Austria.
