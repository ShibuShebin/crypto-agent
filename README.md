# Signal Desk — Crypto Signal & Arbitrage Agent

A signal-only trading assistant. It does **not** place trades — it watches
Binance, Coinbase, and Kraken, computes technical indicators, and shows you:

- **Directional signals** — LONG / SHORT / NEUTRAL per symbol, with a confidence %
- **Plain-English rationale** for each signal (via a free NVIDIA-hosted LLM)
- **Arbitrage watch** — live cross-exchange price spreads worth a manual look

Everything here is decision support, not financial advice. Treat confidence
percentages as "how strongly the indicators agree with each other," not a
probability of profit — backtest before trusting it with real money.

## How it works

```
data_fetcher.py   -> pulls OHLCV candles + live tickers via ccxt (public endpoints, no API key needed)
indicators.py     -> RSI, MACD, EMA20/50, Bollinger %B, ADX, volume ratio
signal_engine.py  -> weighted rule-based scorer -> LONG/SHORT/NEUTRAL + confidence %
arbitrage.py      -> compares tickers across exchanges, flags spreads after est. fees
ai_narrator.py    -> sends the computed numbers to NVIDIA NIM to write a rationale
main.py           -> FastAPI app: background refresh loop + /api endpoints + dashboard
static/index.html -> the dashboard UI
```

The signal engine is fully rule-based and transparent — you can read exactly
why each call was made in `signal_engine.py`. The LLM is only used to narrate
the numbers in English; it never changes the direction or confidence.

## Run it locally

```bash
pip install -r requirements.txt
cp .env.example .env    # add your free NVIDIA NIM key (optional but recommended)
uvicorn main:app --reload --port 8000
```

Open http://localhost:8000

## Get a free NVIDIA NIM key (optional)

1. Go to https://build.nvidia.com
2. Sign in, click your profile icon → **Get API Key**
3. Paste it into `.env` as `NVIDIA_NIM_API_KEY`

This is free for prototyping (rate-limited, not for production traffic —
see notes below). Without a key, the app still works fully — you just get a
template-based rationale instead of an LLM-written one.

## Deploy for free

There are two ways to host this, depending on whether you need a live server
or just a periodically-refreshed dashboard. For signal suggestions (not
live execution), **GitHub Pages + Actions is the better default** — it's
free forever, has no cold starts, and needs no server to keep alive.

### Option A: GitHub Pages + Actions (recommended)

A scheduled GitHub Action recomputes signals every 30 minutes and commits
the results as JSON into `docs/data/`. GitHub Pages serves `docs/` as a
static site that reads those files — no live backend running at all.

1. **Push this project to a new GitHub repo** (public repo = unlimited free Action minutes; private repos get 2,000 free minutes/month, plenty for this schedule).
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<your-repo>.git
   git push -u origin main
   ```

2. **Add your NVIDIA NIM key as a repo secret** (optional but recommended):
   Repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**
   Name: `NVIDIA_NIM_API_KEY`, value: your key from build.nvidia.com

3. **Enable GitHub Pages**:
   Repo → **Settings** → **Pages** → under "Build and deployment", set
   **Source: Deploy from a branch**, **Branch: main**, **Folder: /docs** → Save.
   GitHub gives you a URL like `https://<your-username>.github.io/<your-repo>/`.

4. **Run the workflow once manually** so you don't have to wait 30 minutes:
   Repo → **Actions** tab → **Refresh signals** workflow → **Run workflow**.
   After it finishes (~1-2 min), refresh your Pages URL — you should see live signals.

From then on, it refreshes itself every 30 minutes automatically. Adjust the
schedule by editing the `cron` line in `.github/workflows/refresh.yml`.

**Limitation:** this is a "snapshot" view, not real-time — good for
checking signals a few times a day, not for split-second arbitrage
execution (see Option B for that).

### Option B: Render (for a live, always-computing server)
1. Push this folder to a GitHub repo
2. On [render.com](https://render.com) → New → Blueprint → point at your repo (uses the included `render.yaml`)
3. Add your `NVIDIA_NIM_API_KEY` in the Render dashboard's environment variables
4. Deploy — you get a free `https://your-app.onrender.com` URL

Note: Render's free web services spin down after inactivity and take ~30-60s
to wake on the next request. Fine for a personal dashboard you check
periodically; not fine if you need it always-on and instantly responsive.
This runs `main.py`/`static/` (the live FastAPI app) — separate from the
`docs/` folder used by Option A.

**Other live-server alternatives**
- **Railway** — similar free trial credits, simple GitHub deploy, no sleep-on-idle during trial
- **Fly.io** — free allowance covers one small always-on VM, good if you want no cold starts
- **Oracle Cloud Free Tier** — permanently free small VM (not a trial), most generous long-term option but more setup (you manage the server yourself)

## Customize

- **Add symbols/exchanges** → edit `SYMBOLS` and `EXCHANGES` in `config.py`. Any exchange ccxt supports (100+) works.
- **Change refresh rate** → `REFRESH_INTERVAL_SECONDS` in `config.py`. Keep this reasonable — hammering exchange public endpoints too fast can get you rate-limited or temporarily banned.
- **Adjust signal weights** → `WEIGHTS` dict in `signal_engine.py`.
- **Arbitrage sensitivity** → `ARBITRAGE_MIN_SPREAD_PCT` / `ASSUMED_ROUND_TRIP_FEE_PCT` in `config.py`.

## Known limitations / honest caveats

- **Rule-based, not ML-trained.** Confidence % reflects indicator agreement, not a backtested win probability. If you want real probabilities, the natural next step is training a classifier (e.g. logistic regression or gradient boosting) on historical outcomes — happy to help build that next.
- **Arbitrage spreads exclude withdrawal fees, network transfer time, and transfer limits** between exchanges — a flagged spread is a lead to check manually, not something to auto-execute.
- **Public REST polling, not websockets.** Fine for signals on hourly candles; too slow for high-frequency arbitrage execution.
- **Single-instance in-memory cache.** Fine for personal use; if you scale to multiple server instances you'll want to move the cache to Redis or a small database.

## Suggested next steps

- Add a backtesting script to validate the signal logic against historical data before trusting it
- Add Telegram/Discord alerts when a high-confidence signal or arbitrage opportunity appears
- Add a news/sentiment feed (e.g. CryptoPanic API) as an extra factor in the signal score
