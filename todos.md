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

## 5. zuminderhof.at — image-only PDF fallback

**Rule:** OCR runs *only* when normal text extraction returns empty/whitespace. If extraction yields text but no vegan keyword matches, no OCR.

- `backend/services/adapters/pdf.py` — after `pdfplumber.extract_text()`, check whether the result is empty (or below a small whitespace threshold, e.g. <20 non-whitespace chars across all pages).
- If empty → fall through to OCR path: rasterize each page with `pdf2image` (or `pdfplumber`'s page images), run `pytesseract.image_to_string`, concatenate.
- New deps: `pytesseract`, `pdf2image`. System deps: Tesseract binary, Poppler (for pdf2image). Document in `backend/requirements.txt` and a "System dependencies" section in README.
- Add a per-PDF timeout cap on the OCR path (e.g. 15s) so a 50-page scanned menu doesn't blow the 25s scan timeout for the whole restaurant.
- Verify against `zuminderhof.at`: download the PDF, confirm `extract_text()` returns empty, confirm OCR finds "vegan".

## ✅ 6. kennys.at — DONE

Root cause: menu lives one click deep at `/produkte/` (and sub-pages); homepage's only "vegan" mentions are inside image filenames, which BeautifulSoup strips during text extraction.

- `services/adapters/generic.py`: added `find_menu_links()` — same-host `<a>` candidates whose path or link text matches `menu|menü|menue|speisekarte|karte|produkte|gerichte|essen|food|drinks|getränke`, capped at 4.
- `services/scanner.py`: `_dispatch` now uses the post-redirect URL as the base (`response.url`), and falls through to `_crawl_menu_links` only when both pdf and generic scans on the homepage return empty. Each candidate is run through both adapters.
- Verified: `https://kennys.at/` now yields 8 vegan dishes via `/produkte/` and sub-pages. Same fix also rescues `bruderundschwester.com` from #4 (homepage → `/speisekarte` PDF → 7 dishes).

## 7. Cleanup pass (last)

After 4–6 land:
- Search for unreferenced functions/components/imports across `backend/` and `frontend/src/`.
- Specifically check whether `GET /api/restaurants/{id}/vegan` still has callers (Angular service, tests). If not, delete the route + its handler. **Note: as of step 1, the FE no longer calls it — only the integration test path may still use it.**
- Look for duplicated extraction/normalization logic between `extractor.py` and the adapters.
- Run the integration test again as a final regression check.

---

## Suggested order

1. ~~Investigate #4 and #6~~ — done.
2. #5 OCR path (backend, isolated).
3. #7 cleanup.

## Out of scope (confirmed)

- Headless browser for foodora/lieferando/kennys.
- OCR on non-PDF image menus.
- Countries other than Austria.
