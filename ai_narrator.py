"""
ai_narrator.py

Calls NVIDIA NIM's free hosted LLM API (build.nvidia.com) to turn the
computed signal + indicator numbers into a short plain-English rationale.

This is a NICE-TO-HAVE layer on top of the (already complete) rule-based
signal engine — the actual trading logic never depends on the LLM. If the
API key is missing or the call fails, we fall back to a template summary
so the rest of the app keeps working.

Get a free key at https://build.nvidia.com -> click your profile -> "Get API Key"
Set it as the NVIDIA_NIM_API_KEY environment variable.
"""
import httpx
import logging
from config import NVIDIA_NIM_API_KEY, NVIDIA_NIM_BASE_URL, NVIDIA_NIM_MODEL

logger = logging.getLogger("ai_narrator")


def _fallback_summary(symbol: str, signal: dict) -> str:
    d = signal["direction"]
    c = signal["confidence_pct"]
    trend = signal["trend_strength"]
    return (
        f"{symbol}: rule-based engine reads {d} at {c}% confidence in a {trend} market "
        f"(RSI/MACD/EMA/Bollinger/volume composite score {signal['raw_score']})."
    )


async def explain_signal(symbol: str, signal: dict, snapshot: dict) -> str:
    if not NVIDIA_NIM_API_KEY:
        return _fallback_summary(symbol, signal) + " [Set NVIDIA_NIM_API_KEY for an AI-written explanation.]"

    prompt = f"""You are a crypto market analyst assistant. Given this computed technical
signal, write a tight 2-3 sentence plain-English rationale for a trader. Be specific about
which indicators are driving the call. Do not give financial advice or tell the user to
trade — just explain what the data shows. Do not exceed 60 words.

Symbol: {symbol}
Direction: {signal['direction']}
Confidence: {signal['confidence_pct']}%
Market condition: {signal['trend_strength']}
RSI: {snapshot.get('rsi')}
MACD histogram: {snapshot.get('macd_diff')}
EMA20 vs EMA50: {snapshot.get('ema20')} vs {snapshot.get('ema50')}
Bollinger %B: {snapshot.get('bb_pct')}
Volume vs 20-period avg (ratio): {snapshot.get('vol_ratio')}
ADX: {snapshot.get('adx')}
"""

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"{NVIDIA_NIM_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {NVIDIA_NIM_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": NVIDIA_NIM_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.4,
                    "max_tokens": 150,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning(f"NVIDIA NIM call failed: {e}")
        return _fallback_summary(symbol, signal) + " [AI explanation unavailable this cycle.]"
