"""
main.py

FastAPI app that:
  1. Runs a background scheduler that periodically refreshes signals & arbitrage data
  2. Serves that cached data over a small JSON API
  3. Serves a static dashboard (static/index.html)

Run locally:   uvicorn main:app --reload --port 8000
Then open:     http://localhost:8000
"""
import asyncio
import logging
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
from data_fetcher import fetch_ohlcv
from indicators import compute_indicators, latest_snapshot
from signal_engine import generate_signal
from arbitrage import find_arbitrage_opportunities
from ai_narrator import explain_signal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

app = FastAPI(title="Crypto Signal Agent")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# In-memory cache — refreshed by the background job. Simple and good enough
# for a single-instance free-tier deployment; swap for Redis/DB if you scale out.
CACHE = {
    "signals": [],
    "arbitrage": [],
    "last_updated": None,
    "errors": [],
}


async def refresh_signals():
    """Pull fresh candles for every configured symbol/exchange and recompute signals."""
    results = []
    errors = []

    for symbol in config.SYMBOLS:
        for exchange_id in config.EXCHANGES:
            df = fetch_ohlcv(exchange_id, symbol, config.TIMEFRAME, config.CANDLE_LIMIT)
            if df is None or len(df) < 50:
                errors.append(f"Insufficient data: {exchange_id} {symbol}")
                continue

            df = compute_indicators(df)
            snapshot = latest_snapshot(df)
            signal = generate_signal(snapshot)
            rationale = await explain_signal(symbol, signal, snapshot)

            results.append({
                "symbol": symbol,
                "exchange": exchange_id,
                "price": snapshot.get("close"),
                "signal": signal,
                "rationale": rationale,
                "indicators": snapshot,
            })

    CACHE["signals"] = results
    CACHE["errors"] = errors
    CACHE["last_updated"] = datetime.now(timezone.utc).isoformat()
    logger.info(f"Refreshed {len(results)} signals ({len(errors)} errors)")


async def refresh_arbitrage():
    try:
        opps = find_arbitrage_opportunities(config.EXCHANGES, config.SYMBOLS)
        CACHE["arbitrage"] = opps
        logger.info(f"Found {len(opps)} arbitrage opportunities")
    except Exception as e:
        logger.warning(f"Arbitrage refresh failed: {e}")


async def refresh_all():
    await refresh_signals()
    await refresh_arbitrage()


scheduler = AsyncIOScheduler()


@app.on_event("startup")
async def startup():
    await refresh_all()  # populate cache immediately so the dashboard isn't empty on first load
    scheduler.add_job(refresh_all, "interval", seconds=config.REFRESH_INTERVAL_SECONDS)
    scheduler.start()


@app.get("/api/signals")
async def get_signals():
    return {"last_updated": CACHE["last_updated"], "signals": CACHE["signals"], "errors": CACHE["errors"]}


@app.get("/api/arbitrage")
async def get_arbitrage():
    return {"last_updated": CACHE["last_updated"], "opportunities": CACHE["arbitrage"]}


@app.get("/api/refresh")
async def force_refresh():
    """Manually trigger a refresh (useful for testing; be mindful of exchange rate limits)."""
    await refresh_all()
    return {"status": "refreshed", "last_updated": CACHE["last_updated"]}


@app.get("/health")
async def health():
    return {"status": "ok"}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
