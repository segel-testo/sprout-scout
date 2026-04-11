from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import restaurants

app = FastAPI(title="Sprout Scout API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(restaurants.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
