import os
from dotenv import load_dotenv

load_dotenv()

# --- Exchanges to pull data from (must be supported by ccxt) ---
EXCHANGES = ["binance", "coinbase", "kraken"]

# --- Trading pairs to watch ---
SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

# Note: Coinbase and Kraken use USD spot pairs, not USDT for some assets.
# The data layer normalizes this — see data_fetcher.SYMBOL_MAP if you add pairs.

# --- Candle timeframe used for indicator calculations ---
TIMEFRAME = "1h"
CANDLE_LIMIT = 200  # number of past candles to fetch per request

# --- Arbitrage settings ---
ARBITRAGE_MIN_SPREAD_PCT = 0.5   # only flag spreads above this % (after rough fee estimate)
ASSUMED_ROUND_TRIP_FEE_PCT = 0.2  # rough taker fee both legs combined; adjust per exchange

# --- Refresh interval for the background scheduler (seconds) ---
REFRESH_INTERVAL_SECONDS = 300  # 5 minutes; raise this if you hit rate limits

# --- NVIDIA NIM (build.nvidia.com) for AI-generated rationale ---
# Get a free API key at https://build.nvidia.com  (top right -> Get API Key)
NVIDIA_NIM_API_KEY = os.getenv("NVIDIA_NIM_API_KEY", "")
NVIDIA_NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_NIM_MODEL = os.getenv("NVIDIA_NIM_MODEL", "meta/llama-3.3-70b-instruct")
