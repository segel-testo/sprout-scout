# Sprout Scout — Startup

Resume here after a break.

## Project

- **Location:** `C:\Vali\coding\sprout-scout`
- **GitHub:** https://github.com/segel-testo/sprout-scout

## First message to Claude

> Get familiar with the project at `C:\Vali\coding\sprout-scout` (GitHub: https://github.com/segel-testo/sprout-scout). Read `README.md`, `prompt.md`, and `todos.md` — in that order — then summarize the current state and what's pending.

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
