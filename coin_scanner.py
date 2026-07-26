"""
coin_scanner.py

Tier 1 of the scanning pipeline: screens EVERY coin listed on an exchange
using a single bulk ticker call, then narrows down to the top N by 24h quote
volume for the full indicator/signal treatment (Tier 2, done elsewhere).

This is what makes "scan all coins" practical on free infrastructure --
one cheap bulk call covers the whole universe; only a shortlist gets the
expensive per-symbol OHLCV + indicator work.
"""
import logging
import config
from data_fetcher import fetch_all_tickers_bulk

logger = logging.getLogger("coin_scanner")


def get_shortlist(exchange_id: str, tickers: dict | None = None, top_n: int | None = None) -> list[dict]:
    """
    Returns the top N symbols on this exchange by 24h quote volume, filtered to
    the configured quote currency (e.g. only USDT pairs on Binance).

    Pass in an already-fetched `tickers` dict (from fetch_all_tickers_bulk) to
    avoid making a duplicate bulk API call if the caller already has one.

    Each item: {symbol, last, percentage, quote_volume}
    """
    top_n = top_n or config.TOP_N_PER_EXCHANGE
    quote = config.QUOTE_CURRENCY.get(exchange_id, "USDT")

    if tickers is None:
        tickers = fetch_all_tickers_bulk(exchange_id)
    if not tickers:
        return []

    candidates = []
    for symbol, t in tickers.items():
        if not symbol.endswith(f"/{quote}"):
            continue
        quote_volume = t.get("quoteVolume")
        last = t.get("last")
        if quote_volume is None or last is None:
            continue
        candidates.append({
            "symbol": symbol,
            "last": last,
            "percentage": t.get("percentage"),
            "quote_volume": quote_volume,
        })

    candidates.sort(key=lambda c: c["quote_volume"], reverse=True)
    shortlist = candidates[:top_n]
    logger.info(f"{exchange_id}: screened {len(candidates)} {quote}-quoted coins, shortlisted top {len(shortlist)}")
    return shortlist
