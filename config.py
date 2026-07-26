import os
from dotenv import load_dotenv

load_dotenv()

# --- Exchanges to pull data from (must be supported by ccxt) ---
EXCHANGES = ["binance", "coinbase", "kraken"]

# --- Optional read-only API keys, per exchange (NOT required for public market data,
# but some exchanges give higher rate limits to authenticated requests, which matters
# when scanning hundreds of symbols). Create keys with "read only" / market-data-only
# permissions -- NEVER enable withdrawals, and NEVER enable trading unless you have
# specifically decided to build order execution (this project does not do that).
EXCHANGE_API_KEYS = {
    "binance": {"apiKey": os.getenv("BINANCE_API_KEY", ""), "secret": os.getenv("BINANCE_API_SECRET", "")},
    "coinbase": {"apiKey": os.getenv("COINBASE_API_KEY", ""), "secret": os.getenv("COINBASE_API_SECRET", "")},
    "kraken": {"apiKey": os.getenv("KRAKEN_API_KEY", ""), "secret": os.getenv("KRAKEN_API_SECRET", "")},
}

# --- Quote currency to filter each exchange's coin universe by ---
QUOTE_CURRENCY = {
    "binance": "USDT",
    "coinbase": "USD",
    "kraken": "USD",
}

# --- Two-tier scanning ---
# Tier 1: one bulk ticker call per exchange screens EVERY listed coin (cheap, fast).
# Tier 2: only the top N by 24h quote volume get the full indicator/signal treatment.
# Raise TOP_N_PER_EXCHANGE if you want deeper coverage, but each unit costs one
# extra OHLCV request per refresh cycle -- watch exchange rate limits.
TOP_N_PER_EXCHANGE = 150

# --- Only surface LONG/SHORT calls at or above this confidence in the "High Confidence" feed ---
HIGH_CONFIDENCE_THRESHOLD = 75.0

# --- Candle timeframe used for indicator calculations ---
TIMEFRAME = "1h"
CANDLE_LIMIT = 200  # number of past candles to fetch per request

# --- Arbitrage settings ---
ARBITRAGE_MIN_SPREAD_PCT = 0.5   # only flag spreads above this % (after rough fee estimate)
ASSUMED_ROUND_TRIP_FEE_PCT = 0.2  # rough taker fee both legs combined; adjust per exchange

# --- Risk levels (ATR-based reference stop-loss / take-profit) ---
ATR_STOP_MULTIPLIER = 1.5   # stop-loss distance = ATR * this
ATR_TARGET_MULTIPLIER = 3.0  # take-profit distance = ATR * this (2:1 reward:risk by default)

# --- Airdrop / new-listing watch (via CoinGecko's free public API, no key needed) ---
ENABLE_AIRDROP_WATCH = True
AIRDROP_LOOKBACK_COINS = 40  # how many "recently added" coins to check for tradeable pairs

# --- Whale activity watch (Ethereum-based tokens only, via Etherscan's free API) ---
# This tracks large ERC-20 transfers to/from known exchange wallets as a PROXY for
# unusual activity. It is NOT insider-trading detection -- it cannot see intent or
# non-public information, only large public on-chain movements.
ENABLE_WHALE_WATCH = True
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "")  # free at etherscan.io/apis
WHALE_ALERT_MIN_USD = 1_000_000  # minimum transfer size (approx USD) to flag
WHALE_WATCH_TOKENS = {
    # symbol: ERC-20 contract address (these four are long-standing, widely-documented
    # mainnet contracts -- double check on etherscan.io before trusting for anything critical)
    "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    "USDC": "0xA0b86991c6218b36C1D19D4a2e9Eb0cE3606eB48",
    "WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
    "LINK": "0x514910771AF9Ca656af840dff83E8264EcF986CA",
}
# Known exchange deposit/hot wallets to watch transfers in/out of. Left EMPTY on
# purpose -- do not fabricate addresses here. Look up real, current, labeled
# exchange wallets yourself at https://etherscan.io/accounts/label/exchange
# (pick a label like "binance" or "coinbase") and paste verified addresses in,
# e.g. "0xABC...": "Binance". Whale alerts only cover wallets you add here.
KNOWN_EXCHANGE_WALLETS = {
    # "0xPasteAVerifiedAddressHere": "Binance",
}

# --- Refresh interval for the live-server scheduler (main.py / Render). Not used by
# the GitHub Actions static generator, which runs on the workflow's own cron schedule. ---
REFRESH_INTERVAL_SECONDS = 300  # 5 minutes; raise this if you hit rate limits

# --- NVIDIA NIM (build.nvidia.com) for AI-generated rationale ---
# Get a free API key at https://build.nvidia.com  (top right -> Get API Key)
NVIDIA_NIM_API_KEY = os.getenv("NVIDIA_NIM_API_KEY", "")
NVIDIA_NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_NIM_MODEL = os.getenv("NVIDIA_NIM_MODEL", "meta/llama-3.3-70b-instruct")

