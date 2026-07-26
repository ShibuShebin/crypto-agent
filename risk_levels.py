"""
risk_levels.py

Computes REFERENCE stop-loss / take-profit levels from recent volatility (ATR),
plus a plain risk/reward ratio. This is standard technical-analysis math, not
personalized financial advice -- it does not recommend a leverage amount or
position size, since that depends on your own account size and risk tolerance.

How to use the numbers: decide how much of your capital you're willing to lose
if the stop is hit, then size your position (and any leverage) so that the
distance from entry to stop equals that dollar amount. This tool gives you the
distance; you decide the amount.
"""
import config


def compute_risk_levels(direction: str, price: float, atr: float | None) -> dict | None:
    """
    direction: "LONG" or "SHORT" (returns None for NEUTRAL -- no directional trade to size)
    price: current price
    atr: Average True Range (volatility measure) from indicators.py
    """
    if direction not in ("LONG", "SHORT") or atr is None or price is None or atr <= 0:
        return None

    stop_distance = atr * config.ATR_STOP_MULTIPLIER
    target_distance = atr * config.ATR_TARGET_MULTIPLIER

    if direction == "LONG":
        stop_loss = price - stop_distance
        take_profit = price + target_distance
    else:  # SHORT
        stop_loss = price + stop_distance
        take_profit = price - target_distance

    risk_pct = (stop_distance / price) * 100
    reward_pct = (target_distance / price) * 100
    reward_risk_ratio = round(target_distance / stop_distance, 2) if stop_distance else None

    return {
        "stop_loss": round(stop_loss, 6),
        "take_profit": round(take_profit, 6),
        "stop_distance_pct": round(risk_pct, 2),
        "target_distance_pct": round(reward_pct, 2),
        "reward_risk_ratio": reward_risk_ratio,
        "note": (
            "Reference levels from recent volatility (ATR), not personalized advice. "
            "Size any position/leverage so the stop distance matches what you're willing to risk."
        ),
    }
