import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import restaurants

app = FastAPI(title="Sprout Scout API")

# Comma-separated list of origins allowed to call the API.
# Dev default is the Angular dev server; production sets this via env var
# on Render to e.g. "https://www.sprout-scout.at,https://sprout-scout.at".
_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:4200")
ALLOWED_ORIGINS = [o.strip() for o in _origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(restaurants.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
