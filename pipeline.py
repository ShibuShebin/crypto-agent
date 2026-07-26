"""
pipeline.py

The full scan pipeline, shared by both:
  - scripts/generate_static.py (GitHub Actions -> static JSON for Pages)
  - main.py (optional live FastAPI server, e.g. on Render)

Flow per refresh cycle:
  1. TIER 1: one bulk ticker call per exchange screens EVERY listed coin (cheap)
  2. Arbitrage + new-listings detection run off that same Tier 1 data -- free,
     no extra API calls, and covers the whole coin universe
  3. TIER 2: only the top-N-by-volume shortlist per exchange gets the full
     indicator/signal/risk-level treatment (the expensive per-symbol work)
  4. AI rationale (NVIDIA NIM) is only generated for signals that clear the
     high-confidence threshold, to stay within free LLM rate limits
"""
import logging
from datetime import datetime, timezone

import config
from data_fetcher import fetch_all_tickers_bulk, fetch_ohlcv, fetch_ticker
from coin_scanner import get_shortlist
from indicators import compute_indicators, latest_snapshot
from signal_engine import generate_signal
from risk_levels import compute_risk_levels
from arbitrage import find_arbitrage_opportunities
from ai_narrator import explain_signal
from new_listings import load_known_symbols, save_known_symbols, detect_new_listings
from whale_watch import get_whale_alerts

logger = logging.getLogger("pipeline")


async def run_full_scan() -> dict:
    errors = []

    # ---- Tier 1: bulk-screen every listed coin on every exchange ----
    bulk_tickers = {}
    for exchange_id in config.EXCHANGES:
        tickers = fetch_all_tickers_bulk(exchange_id)
        if not tickers:
            errors.append(f"Bulk ticker scan failed: {exchange_id}")
        bulk_tickers[exchange_id] = tickers

    # ---- Arbitrage + new listings: free, derived from Tier 1 data only ----
    arbitrage_opportunities = find_arbitrage_opportunities(bulk_tickers)

    known_symbols = load_known_symbols()
    new_listings_found = {}
    for exchange_id, tickers in bulk_tickers.items():
        quote = config.QUOTE_CURRENCY.get(exchange_id, "USDT")
        current_symbols = [s for s in tickers.keys() if s.endswith(f"/{quote}")]
        new_syms = detect_new_listings(exchange_id, current_symbols, known_symbols)
        if new_syms:
            new_listings_found[exchange_id] = new_syms
    save_known_symbols(known_symbols)

    # ---- Tier 2: full indicator/signal engine on the top-N shortlist per exchange ----
    all_signals = []
    high_confidence_signals = []

    for exchange_id in config.EXCHANGES:
        shortlist = get_shortlist(exchange_id, tickers=bulk_tickers.get(exchange_id))
        for candidate in shortlist:
            symbol = candidate["symbol"]
            df = fetch_ohlcv(exchange_id, symbol, config.TIMEFRAME, config.CANDLE_LIMIT)
            if df is None or len(df) < 50:
                continue

            df = compute_indicators(df)
            snapshot = latest_snapshot(df)
            signal = generate_signal(snapshot)
            risk = compute_risk_levels(signal["direction"], snapshot.get("close"), snapshot.get("atr"))

            entry = {
                "symbol": symbol,
                "exchange": exchange_id,
                "price": snapshot.get("close"),
                "signal": signal,
                "risk_levels": risk,
                "indicators": snapshot,
                "rationale": None,  # filled in below only for high-confidence entries
            }
            all_signals.append(entry)

            is_actionable = signal["direction"] in ("LONG", "SHORT")
            if is_actionable and signal["confidence_pct"] >= config.HIGH_CONFIDENCE_THRESHOLD:
                high_confidence_signals.append(entry)

    # AI rationale only for the high-confidence shortlist (keeps NVIDIA NIM calls low)
    for entry in high_confidence_signals:
        entry["rationale"] = await explain_signal(entry["symbol"], entry["signal"], entry["indicators"])

    # ---- Whale watch: needs a couple of reference prices to estimate USD values ----
    reference_prices = {}
    btc_ticker = fetch_ticker("binance", "BTC/USDT")
    if btc_ticker and btc_ticker.get("last"):
        reference_prices["WBTC"] = btc_ticker["last"]
    link_ticker = fetch_ticker("binance", "LINK/USDT")
    if link_ticker and link_ticker.get("last"):
        reference_prices["LINK"] = link_ticker["last"]

    whale_alerts = await get_whale_alerts(reference_prices)

    logger.info(
        f"Scan complete: {len(all_signals)} signals scanned, "
        f"{len(high_confidence_signals)} high-confidence, "
        f"{len(arbitrage_opportunities)} arbitrage opportunities, "
        f"{sum(len(v) for v in new_listings_found.values())} new listings, "
        f"{len(whale_alerts)} whale alerts"
    )

    return {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "signals": all_signals,
        "high_confidence_signals": high_confidence_signals,
        "arbitrage": arbitrage_opportunities,
        "new_listings": new_listings_found,
        "whale_alerts": whale_alerts,
        "errors": errors,
    }
