# Signal Desk — Crypto Signal, Arbitrage & Whale-Activity Agent

A signal-only trading assistant. It does **not** place trades — it screens every
coin listed on Binance, Coinbase, and Kraken, and shows you:

- **High-confidence signals** — LONG/SHORT calls at 75%+ confidence, with an
  ATR-based reference stop-loss/take-profit
- **Arbitrage watch** — live cross-exchange price spreads, covering every coin
- **New Listings Watch** — coins newly seen in a scan (often airdrop/TGE-linked)
- **Whale Activity Watch** — large public on-chain transfers of major ETH tokens
- **AI rationale** for each high-confidence call (via a free NVIDIA-hosted LLM)

Everything here is decision support, not financial advice. Confidence % reflects
how strongly the technical indicators agree with each other — not a backtested
win rate. Read the "Honest limitations" section below before relying on any of it.

## How the scan works (two tiers, to stay within free rate limits)

Binance alone lists 2,000+ trading pairs. Running full technical analysis on
every coin, every 30 minutes, would hit exchange rate limits hard and risk
getting your IP temporarily blocked. So the scan works in two tiers:

1. **Tier 1 — bulk screen**: one API call per exchange fetches *every* listed
   coin's price, 24h change, and volume at once. Cheap and fast, covers 100%
   of the coin universe. Arbitrage and new-listings detection run entirely off
   this data — free, no extra calls.
2. **Tier 2 — full analysis**: only the top N coins by 24h volume per exchange
   (`TOP_N_PER_EXCHANGE` in `config.py`, default 150) get the expensive
   per-symbol work — RSI, MACD, EMA, Bollinger, ADX, ATR, and the signal score.

If you want deeper coverage, raise `TOP_N_PER_EXCHANGE` — just watch for rate
limit errors in the Action logs if you push it too high.

## Project structure

```
config.py           -> all tunable settings (coin count, thresholds, API keys, etc.)
data_fetcher.py      -> ccxt wrapper: bulk tickers (Tier 1) + OHLCV candles (Tier 2)
coin_scanner.py       -> turns a bulk ticker scan into a top-N-by-volume shortlist
indicators.py         -> RSI, MACD, EMA20/50, Bollinger %B, ADX, ATR, volume ratio
signal_engine.py      -> weighted rule-based scorer -> LONG/SHORT/NEUTRAL + confidence %
risk_levels.py        -> ATR-based reference stop-loss/take-profit (not personalized advice)
arbitrage.py          -> cross-exchange spread scan, using only Tier 1 data (all coins, free)
new_listings.py        -> flags coins seen for the first time (persisted history)
whale_watch.py         -> large ERC-20 transfer alerts via Etherscan (ETH tokens only)
ai_narrator.py         -> sends high-confidence signals to NVIDIA NIM for a rationale
pipeline.py            -> orchestrates all of the above into one scan cycle
scripts/generate_static.py -> runs the pipeline once, writes JSON for GitHub Pages
main.py                -> optional live FastAPI server (e.g. for Render), same pipeline
docs/                  -> static dashboard + data, served by GitHub Pages
static/                -> live-server dashboard variant (points at /api instead of JSON files)
```

## Run it locally

```bash
pip install -r requirements.txt
cp .env.example .env    # fill in whichever optional keys you want (see below)
python scripts/generate_static.py    # runs one scan, writes docs/data/*.json
```

Then open `docs/index.html` directly in a browser to see the results, or run the
live server instead: `uvicorn main:app --reload --port 8000` → http://localhost:8000

## Optional keys (the app works without all of these — just with fewer features)

| Key | What it's for | Get it free at |
|---|---|---|
| `NVIDIA_NIM_API_KEY` | AI-written rationale for each high-confidence signal | build.nvidia.com |
| `ETHERSCAN_API_KEY` | Whale-activity watch (Ethereum tokens) | etherscan.io/apis |
| `BINANCE_API_KEY` / `_SECRET` | Higher rate limits when scanning many symbols | binance.com (create with **read-only**, no trading/withdrawal permissions) |

Same pattern for `COINBASE_API_KEY`/`_SECRET` and `KRAKEN_API_KEY`/`_SECRET` if you want those too.

**On exchange API keys specifically:** create them with market-data/read-only
permissions only. Never enable withdrawals. This project does not execute
trades — there's no code path that would use trading permissions even if you
granted them, but there's no reason to grant them either.

## Deploy for free

### Option A: GitHub Pages + Actions (recommended)

A scheduled GitHub Action runs the scan every 30 minutes and commits the
results as JSON into `docs/data/`. GitHub Pages serves `docs/` as a static
site — no live backend running at all.

1. Push this project to a GitHub repo (public = unlimited free Action minutes)
2. Add secrets: repo → **Settings → Secrets and variables → Actions** → add
   whichever of `NVIDIA_NIM_API_KEY`, `ETHERSCAN_API_KEY`, `BINANCE_API_KEY`,
   `BINANCE_API_SECRET` you want (all optional)
3. Enable Pages: **Settings → Pages** → Source: **Deploy from a branch**,
   Branch: **main**, Folder: **/docs** → Save
4. Run it once manually: **Actions** tab → **Refresh signals** → **Run workflow**
5. Visit `https://<your-username>.github.io/<your-repo>/`

Given the larger scan size, one run may take several minutes (a `timeout-minutes: 25`
safeguard is set in the workflow). It'll keep refreshing itself every 30 minutes
after that, for free, indefinitely.

### Option B: Render (for a live, always-computing server)

Uses `main.py` + `static/` instead of `docs/`. Push to GitHub, then on
render.com → **New → Blueprint** → point at your repo (uses `render.yaml`),
add your secrets in the dashboard, deploy. Free tier sleeps after inactivity
(~30-60s wake-up on the next request) — fine for personal checking, not for
split-second reactions.

## Honest limitations (please read before trusting any of this)

- **Confidence % is indicator agreement, not a win-rate probability.** A 90%
  reading means RSI/MACD/EMA/Bollinger/volume all point the same way strongly
  — it is not a backtested statistic about how often that setup made money.
  If you want real probabilities, the next step is training a classifier on
  historical outcomes — ask if you'd like help building that.
- **Stop-loss/take-profit are volatility-based reference points (ATR), not
  personalized advice.** They don't know your account size or risk tolerance —
  you decide how much capital that stop distance represents, and size any
  position/leverage accordingly.
- **"New Listings Watch" is not a pre-listing airdrop calendar.** There's no
  reliable free API for that. This flags coins the first time they appear in
  a scan (i.e. already tradable) — useful, but after the fact, not before.
- **"Whale Activity Watch" is not insider-trading detection.** It flags large
  public transfers of a few major Ethereum tokens. It cannot see intent, and
  most large transfers are routine (exchange rebalancing, custodial moves,
  etc.), not a signal of anything. Also: Ethereum-only, not BSC/Solana/other chains.
- **Arbitrage spreads exclude withdrawal fees, network transfer time, and
  transfer limits** between exchanges — a flagged spread is a lead to check
  manually, not something to auto-execute.
- **No auto-execution.** Everything here is signal-only, by design. If you
  ever want to add real order execution, that's a substantial, higher-risk
  addition — happy to help scope it carefully if/when you want that.

## Customize

- **Scan depth** → `TOP_N_PER_EXCHANGE` in `config.py`
- **Confidence bar** → `HIGH_CONFIDENCE_THRESHOLD` in `config.py`
- **Stop-loss/take-profit distance** → `ATR_STOP_MULTIPLIER` / `ATR_TARGET_MULTIPLIER`
- **Signal weights** → `WEIGHTS` dict in `signal_engine.py`
- **Whale alert threshold / tracked tokens** → `WHALE_ALERT_MIN_USD` / `WHALE_WATCH_TOKENS` in `config.py`
- **Known exchange wallets** (improves whale-alert labels) → `KNOWN_EXCHANGE_WALLETS`
  in `config.py`. Left empty on purpose — look up real, current, labeled
  addresses yourself at etherscan.io/accounts/label/exchange, don't guess.

## Suggested next steps

- Backtest the signal logic against historical data before trusting it
- Add Telegram/Discord push alerts when a high-confidence signal appears
- Train a real classifier on historical outcomes for genuine win-probability estimates
