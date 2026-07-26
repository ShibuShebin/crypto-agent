"""
data_fetcher.py

Wraps ccxt to pull OHLCV candles and live tickers from multiple exchanges.
Uses only PUBLIC endpoints — no API keys needed for market data, so this
works out of the box for signal generation and arbitrage scanning.
"""
import ccxt
import pandas as pd
import logging

logger = logging.getLogger("data_fetcher")

# Some exchanges quote in USD instead of USDT for the same asset.
# Map a "canonical" symbol to what each exchange actually calls it.
SYMBOL_OVERRIDES = {
    "coinbase": {"BTC/USDT": "BTC/USD", "ETH/USDT": "ETH/USD", "SOL/USDT": "SOL/USD"},
    "kraken": {"BTC/USDT": "BTC/USD", "ETH/USDT": "ETH/USD", "SOL/USDT": "SOL/USD"},
}

_exchange_cache = {}


def get_exchange(exchange_id: str):
    """Return a cached ccxt exchange instance."""
    if exchange_id not in _exchange_cache:
        exchange_class = getattr(ccxt, exchange_id)
        _exchange_cache[exchange_id] = exchange_class({"enableRateLimit": True})
    return _exchange_cache[exchange_id]


def resolve_symbol(exchange_id: str, symbol: str) -> str:
    return SYMBOL_OVERRIDES.get(exchange_id, {}).get(symbol, symbol)


def fetch_ohlcv(exchange_id: str, symbol: str, timeframe: str, limit: int) -> pd.DataFrame | None:
    """Fetch OHLCV candles for a symbol from one exchange. Returns None on failure."""
    try:
        ex = get_exchange(exchange_id)
        real_symbol = resolve_symbol(exchange_id, symbol)
        raw = ex.fetch_ohlcv(real_symbol, timeframe=timeframe, limit=limit)
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
        real_symbol = resolve_symbol(exchange_id, symbol)
        ticker = ex.fetch_ticker(real_symbol)
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
    """Fetch the same symbol's ticker across every configured exchange."""
    results = []
    for ex_id in exchanges:
        t = fetch_ticker(ex_id, symbol)
        if t:
            results.append(t)
    return results
