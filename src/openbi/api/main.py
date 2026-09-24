"""OpenBI — FastAPI application entry point.

Run:
    uvicorn openbi.api.main:app --reload --port 8000

Docs:
    http://localhost:8000/docs
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from openbi.api.routes import customers, forecasts, sales

app = FastAPI(
    title="OpenBI API",
    description="Programmatic access to OpenBI metrics, segments, and forecasts.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sales.router)
app.include_router(customers.router)
app.include_router(forecasts.router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "OK"}


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    return {
        "service": "OpenBI API",
        "docs": "/docs",
        "endpoints": "/kpis /customers /forecasts",
    }
