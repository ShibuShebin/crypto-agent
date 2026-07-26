"""
indicators.py

Computes standard technical indicators on an OHLCV DataFrame using the `ta` library.
"""
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator, ADXIndicator
from ta.volatility import BollingerBands


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Adds indicator columns to a copy of the OHLCV dataframe and returns it."""
    df = df.copy()

    df["rsi"] = RSIIndicator(close=df["close"], window=14).rsi()

    macd = MACD(close=df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["macd_diff"] = macd.macd_diff()

    df["ema20"] = EMAIndicator(close=df["close"], window=20).ema_indicator()
    df["ema50"] = EMAIndicator(close=df["close"], window=50).ema_indicator()

    bb = BollingerBands(close=df["close"], window=20, window_dev=2)
    df["bb_high"] = bb.bollinger_hband()
    df["bb_low"] = bb.bollinger_lband()
    df["bb_pct"] = bb.bollinger_pband()  # 0 = at lower band, 1 = at upper band

    adx = ADXIndicator(high=df["high"], low=df["low"], close=df["close"], window=14)
    df["adx"] = adx.adx()  # trend strength (not direction); >25 = trending market

    # Volume spike: current volume vs 20-period rolling average
    df["vol_avg20"] = df["volume"].rolling(20).mean()
    df["vol_ratio"] = df["volume"] / df["vol_avg20"]

    return df


def latest_snapshot(df: pd.DataFrame) -> dict:
    """Returns the most recent row of indicators as a plain dict, handling NaNs."""
    row = df.iloc[-1]
    return {k: (None if pd.isna(v) else round(float(v), 4) if isinstance(v, (int, float)) else v)
            for k, v in row.items()}
