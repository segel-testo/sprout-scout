# Sprout Scout

Find vegan dishes at local restaurants — search by zip code, we scan the menus.

---

## Status

| Area | Status |
|------|--------|
| Project scaffold | done |
| Backend (FastAPI) | done |
| Frontend (Angular) | scaffolded |
| Overpass API integration | done |
| PDF + web scanner | done |
| File-based cache (1 week) | done |
| Angular UI | next |
| Deploy frontend (Vercel) | todo |
| Deploy backend (Render) | todo |

---

## Tech Stack

| Layer | Choice |
|-------|--------|
| Frontend | Angular 21 |
| Backend | Python 3.13 + FastAPI |
| Restaurant data | OpenStreetMap / Overpass API |
| PDF parsing | `pdfplumber` |
| Web scraping | `BeautifulSoup` + `httpx` |
| Caching | File-based (`.cache/`, 1 week TTL) |
| Hosting (FE) | Vercel |
| Hosting (BE) | Render |

---

## Project Structure

```
sprout-scout/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── requirements.txt
│   ├── routers/
│   │   └── restaurants.py       # GET /api/restaurants, GET /api/restaurants/{id}/vegan
│   └── services/
│       ├── overpass.py          # Fetch restaurants by zip code via Overpass API
│       ├── scanner.py           # Scan websites + PDFs for vegan dishes with confidence score
│       └── cache.py             # File-based cache with 1-week TTL
└── frontend/
    └── src/
        └── app/                 # Angular app (UI to be built)
```

---

## API Endpoints

### `GET /api/restaurants?zip_code=1010&country=AT`
Returns list of restaurants in the given Austrian zip code.

### `GET /api/restaurants/{id}/vegan?website=https://...`
Scans the restaurant's website/PDF menus and returns vegan dishes with confidence scores.

### `GET /health`
Health check.

---

## Running Locally

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn main:app --reload
# API available at http://localhost:8000
```

### Frontend
```bash
cd frontend
npm install
ng serve
# App available at http://localhost:4200
```

---

## Next Steps

- [ ] Build Angular UI
  - [ ] Zip code input form (4-digit, Austria only)
  - [ ] Restaurant card list
  - [ ] Click card to show vegan dishes with confidence scores
- [ ] Deploy backend to Render
- [ ] Deploy frontend to Vercel

---

## Design Decisions

- **Country restriction:** Austria only for now (4-digit zip codes, AT filter in Overpass query)
- **Vegan detection:** Keyword matching in German + English, confidence score 40-100% based on number of matched keywords
- **Cache:** File-based JSON cache in `backend/.cache/`, keyed by zip code, expires after 1 week
- **No login required:** Public tool, anyone can use it
