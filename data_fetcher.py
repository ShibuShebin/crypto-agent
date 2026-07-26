"""
data_fetcher.py

Wraps ccxt to pull OHLCV candles and live tickers from multiple exchanges.
Uses PUBLIC market data endpoints by default -- no API keys needed. Optional
read-only API keys (see config.EXCHANGE_API_KEYS) can be supplied for higher
rate limits on some exchanges when scanning many symbols.
"""
import ccxt
import pandas as pd
import logging
import config

logger = logging.getLogger("data_fetcher")

_exchange_cache = {}


def get_exchange(exchange_id: str):
    """Return a cached ccxt exchange instance, authenticated if keys are configured."""
    if exchange_id not in _exchange_cache:
        exchange_class = getattr(ccxt, exchange_id)
        creds = config.EXCHANGE_API_KEYS.get(exchange_id, {})
        opts = {"enableRateLimit": True}
        if creds.get("apiKey") and creds.get("secret"):
            opts.update({"apiKey": creds["apiKey"], "secret": creds["secret"]})
        _exchange_cache[exchange_id] = exchange_class(opts)
    return _exchange_cache[exchange_id]


def fetch_all_tickers_bulk(exchange_id: str) -> dict:
    """
    Tier 1 scan: ONE API call fetches every listed ticker on the exchange
    (price, 24h change, quote volume). This is what lets us screen the whole
    coin universe cheaply instead of hitting rate limits.
    Returns {} on failure.
    """
    try:
        ex = get_exchange(exchange_id)
        return ex.fetch_tickers()
    except Exception as e:
        logger.warning(f"Bulk ticker fetch failed [{exchange_id}]: {e}")
        return {}


def fetch_ohlcv(exchange_id: str, symbol: str, timeframe: str, limit: int) -> pd.DataFrame | None:
    """Fetch OHLCV candles for a symbol from one exchange. Returns None on failure."""
    try:
        ex = get_exchange(exchange_id)
        raw = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        return df
    except Exception as e:
        logger.warning(f"OHLCV fetch failed [{exchange_id} {symbol}]: {e}")
        return None


def fetch_ticker(exchange_id: str, symbol: str) -> dict | None:
    """Fetch a live ticker (bid/ask/last) for one symbol from one exchange."""
    try:
        ex = get_exchange(exchange_id)
        ticker = ex.fetch_ticker(symbol)
        return {
            "exchange": exchange_id,
            "symbol": symbol,
            "bid": ticker.get("bid"),
            "ask": ticker.get("ask"),
            "last": ticker.get("last"),
            "timestamp": ticker.get("datetime"),
        }
    except Exception as e:
        logger.warning(f"Ticker fetch failed [{exchange_id} {symbol}]: {e}")
        return None


def fetch_tickers_all_exchanges(exchanges: list[str], symbol: str) -> list[dict]:
    """Fetch the same symbol's ticker across every configured exchange (for arbitrage)."""
    results = []
    for ex_id in exchanges:
        t = fetch_ticker(ex_id, symbol)
        if t:
            results.append(t)
    return results
