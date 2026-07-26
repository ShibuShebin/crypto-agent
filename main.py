"""
main.py

Optional LIVE server (e.g. for Render) running the same pipeline as the
GitHub Pages generator, refreshed on an in-process schedule instead of a
GitHub Actions cron job.

Run locally:   uvicorn main:app --reload --port 8000
Then open:     http://localhost:8000
"""
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
from pipeline import run_full_scan

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

app = FastAPI(title="Crypto Signal Agent")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# In-memory cache, refreshed by the background job.
CACHE = {
    "last_updated": None,
    "signals": [],
    "high_confidence_signals": [],
    "arbitrage": [],
    "new_listings": {},
    "whale_alerts": [],
    "errors": [],
}

scheduler = AsyncIOScheduler()


async def refresh():
    result = await run_full_scan()
    CACHE.update(result)


@app.on_event("startup")
async def startup():
    await refresh()  # populate cache immediately so the dashboard isn't empty on first load
    scheduler.add_job(refresh, "interval", seconds=config.REFRESH_INTERVAL_SECONDS)
    scheduler.start()


@app.get("/api/signals")
async def get_signals():
    return {"last_updated": CACHE["last_updated"], "signals": CACHE["signals"], "errors": CACHE["errors"]}


@app.get("/api/high-confidence")
async def get_high_confidence():
    return {"last_updated": CACHE["last_updated"], "signals": CACHE["high_confidence_signals"]}


@app.get("/api/arbitrage")
async def get_arbitrage():
    return {"last_updated": CACHE["last_updated"], "opportunities": CACHE["arbitrage"]}


@app.get("/api/new-listings")
async def get_new_listings():
    return {"last_updated": CACHE["last_updated"], "new_listings": CACHE["new_listings"]}


@app.get("/api/whale-alerts")
async def get_whale_alerts():
    return {"last_updated": CACHE["last_updated"], "alerts": CACHE["whale_alerts"]}


@app.get("/api/refresh")
async def force_refresh():
    """Manually trigger a refresh (useful for testing; be mindful of exchange rate limits)."""
    await refresh()
    return {"status": "refreshed", "last_updated": CACHE["last_updated"]}


@app.get("/health")
async def health():
    return {"status": "ok"}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
