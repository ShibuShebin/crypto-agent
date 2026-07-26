"""
scripts/generate_static.py

Runs ONE refresh cycle (fetch data -> compute signals -> scan arbitrage ->
write JSON) and saves the results into docs/data/. Meant to be run on a
schedule by GitHub Actions, with docs/ served as a static site via GitHub
Pages. No live server needed.

Run manually:  python scripts/generate_static.py
"""
import asyncio
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config
from data_fetcher import fetch_ohlcv
from indicators import compute_indicators, latest_snapshot
from signal_engine import generate_signal
from arbitrage import find_arbitrage_opportunities
from ai_narrator import explain_signal

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "data")


async def main():
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

    try:
        opportunities = find_arbitrage_opportunities(config.EXCHANGES, config.SYMBOLS)
    except Exception as e:
        opportunities = []
        errors.append(f"Arbitrage scan failed: {e}")

    now = datetime.now(timezone.utc).isoformat()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(os.path.join(OUTPUT_DIR, "signals.json"), "w") as f:
        json.dump({"last_updated": now, "signals": results, "errors": errors}, f, indent=2)

    with open(os.path.join(OUTPUT_DIR, "arbitrage.json"), "w") as f:
        json.dump({"last_updated": now, "opportunities": opportunities}, f, indent=2)

    print(f"Wrote {len(results)} signals and {len(opportunities)} arbitrage opportunities ({len(errors)} errors).")


if __name__ == "__main__":
    asyncio.run(main())
