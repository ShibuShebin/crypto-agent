"""
signal_engine.py

Turns a snapshot of technical indicators into a directional call
(LONG / SHORT / NEUTRAL) plus a confidence percentage.

This is a transparent, rule-based weighted scorer — not a black box.
Each factor contributes a score in [-1, +1], weights are applied, and the
sum is squashed into a 0-100% confidence via a logistic curve. It is meant
as a decision-support signal, not a guarantee — always treat it as one
input among several, and backtest before relying on it.
"""
import math


WEIGHTS = {
    "rsi": 0.25,
    "macd": 0.25,
    "ema_trend": 0.20,
    "bollinger": 0.15,
    "volume": 0.15,
}


def _score_rsi(rsi: float | None) -> float:
    if rsi is None:
        return 0.0
    if rsi <= 30:
        return 1.0   # oversold -> bullish
    if rsi >= 70:
        return -1.0  # overbought -> bearish
    # linear taper between 30-50 (mild bullish) and 50-70 (mild bearish)
    return (50 - rsi) / 20


def _score_macd(macd_diff: float | None) -> float:
    if macd_diff is None:
        return 0.0
    return max(-1.0, min(1.0, macd_diff * 5))  # scaled; MACD diff is usually small


def _score_ema_trend(ema20: float | None, ema50: float | None) -> float:
    if ema20 is None or ema50 is None or ema50 == 0:
        return 0.0
    pct_diff = (ema20 - ema50) / ema50
    return max(-1.0, min(1.0, pct_diff * 20))


def _score_bollinger(bb_pct: float | None) -> float:
    if bb_pct is None:
        return 0.0
    if bb_pct <= 0.1:
        return 1.0   # near lower band -> bullish reversion
    if bb_pct >= 0.9:
        return -1.0  # near upper band -> bearish reversion
    return (0.5 - bb_pct) * 2


def _score_volume(vol_ratio: float | None, directional_bias: float) -> float:
    """Volume doesn't have its own direction — it confirms/amplifies the existing bias."""
    if vol_ratio is None or vol_ratio < 1.2:
        return 0.0
    strength = min(1.0, (vol_ratio - 1.2) / 1.5)
    return strength * (1 if directional_bias > 0 else -1 if directional_bias < 0 else 0)


def generate_signal(snapshot: dict) -> dict:
    """
    snapshot: dict of latest indicator values from indicators.latest_snapshot()
    Returns: {direction, confidence_pct, score, breakdown, trend_strength}
    """
    rsi_s = _score_rsi(snapshot.get("rsi"))
    macd_s = _score_macd(snapshot.get("macd_diff"))
    ema_s = _score_ema_trend(snapshot.get("ema20"), snapshot.get("ema50"))
    bb_s = _score_bollinger(snapshot.get("bb_pct"))

    pre_volume_bias = rsi_s * WEIGHTS["rsi"] + macd_s * WEIGHTS["macd"] + ema_s * WEIGHTS["ema_trend"] + bb_s * WEIGHTS["bollinger"]
    vol_s = _score_volume(snapshot.get("vol_ratio"), pre_volume_bias)

    raw_score = (
        rsi_s * WEIGHTS["rsi"]
        + macd_s * WEIGHTS["macd"]
        + ema_s * WEIGHTS["ema_trend"]
        + bb_s * WEIGHTS["bollinger"]
        + vol_s * WEIGHTS["volume"]
    )

    # ADX tells us whether we're in a trending or choppy market. In choppy
    # markets (ADX < 20) we pull confidence toward neutral since directional
    # signals are less reliable.
    adx = snapshot.get("adx")
    trend_strength = "trending" if (adx or 0) >= 25 else ("choppy" if (adx or 0) < 20 else "moderate")
    adx_dampener = 1.0 if trend_strength == "trending" else (0.6 if trend_strength == "choppy" else 0.85)
    raw_score *= adx_dampener

    NEUTRAL_THRESHOLD = 0.08

    if raw_score > NEUTRAL_THRESHOLD:
        direction = "LONG"
        # Squash to 0-100 confidence using a logistic curve centered on |score|
        confidence_pct = round(100 / (1 + math.exp(-6 * abs(raw_score))), 1)
    elif raw_score < -NEUTRAL_THRESHOLD:
        direction = "SHORT"
        confidence_pct = round(100 / (1 + math.exp(-6 * abs(raw_score))), 1)
    else:
        direction = "NEUTRAL"
        # Confidence in "neutral" is highest when raw_score sits right at 0,
        # and decays toward 0 as it approaches the directional threshold.
        confidence_pct = round(100 * (1 - min(1.0, abs(raw_score) / NEUTRAL_THRESHOLD)), 1)

    return {
        "direction": direction,
        "confidence_pct": confidence_pct,
        "raw_score": round(raw_score, 4),
        "trend_strength": trend_strength,
        "breakdown": {
            "rsi_score": round(rsi_s, 3),
            "macd_score": round(macd_s, 3),
            "ema_trend_score": round(ema_s, 3),
            "bollinger_score": round(bb_s, 3),
            "volume_score": round(vol_s, 3),
            "adx": adx,
        },
    }
