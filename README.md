# Sprout Scout

Find vegan dishes at local restaurants — search by zip code, we scan the menus.

---

## Plan

### Phase 1 — Location Input
- Angular SPA with zip code input + country selector (Austria only initially)
- Validate 4-digit Austrian postal codes
- Submit triggers restaurant lookup

### Phase 2 — Restaurant Discovery
- Query **OpenStreetMap Overpass API** for restaurants in the given zip code area
- Display restaurant cards (name, address, website, map link)
- Click a restaurant card to see its vegan dishes

### Phase 3 — Vegan Menu Search
For each restaurant, scan for vegan dishes via:

1. **PDF menu scan** — fetch and parse linked PDF menus
2. **Homepage scrape** — scrape menu pages from the restaurant's website
3. **Keyword matching** — German + English vegan keywords
   - EN: `vegan`, `plant-based`, `dairy-free`, `no meat`, ...
   - DE: `vegan`, `pflanzlich`, `ohne Fleisch`, `laktosefrei`, ...
4. **Confidence score** — rate each dish (e.g. 85% vegan) based on matched signals

### Phase 4 — Results Display
- Restaurant cards as primary view
- Click a card → expand to show found vegan dishes with confidence scores
- Source shown per dish (PDF or website)

### Phase 5 — Caching
- Cache results per zip code for **1 week**
- Fresh scan if cache is expired or missing

---

## Tech Stack

| Layer        | Choice                          |
|--------------|----------------------------------|
| Frontend     | Angular                          |
| Backend      | Python + FastAPI                 |
| Restaurant data | OpenStreetMap / Overpass API  |
| PDF parsing  | `pdfplumber`                     |
| Web scraping | `BeautifulSoup` + `httpx`        |
| Caching      | File-based or Redis              |
| Hosting (FE) | Vercel                           |
| Hosting (BE) | Render                           |

---

## Access
- Public tool, no login required

---

## Next Steps

- [ ] Set up GitHub repo (`sprout-scout`)
- [ ] Scaffold Angular frontend
- [ ] Scaffold FastAPI backend
- [ ] Implement zip code input + Austria validation
- [ ] Integrate Overpass API for restaurant lookup
- [ ] Build PDF parser + keyword/confidence matcher
- [ ] Build website scraper + keyword/confidence matcher
- [ ] Wire up frontend to backend
- [ ] Deploy to Vercel + Render
