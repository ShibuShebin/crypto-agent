"""
arbitrage.py

Compares the live price of the same asset across multiple exchanges and
flags spreads worth investigating after a rough fee estimate.

Note: this checks SPOT ticker spreads only. Real arbitrage execution also
needs to account for withdrawal/transfer time, network fees, and
transfer limits between exchanges — those aren't included here since they
vary a lot by exchange and asset. Treat flagged opportunities as leads to
verify manually, not auto-executable trades.
"""
from config import ARBITRAGE_MIN_SPREAD_PCT, ASSUMED_ROUND_TRIP_FEE_PCT
from data_fetcher import fetch_tickers_all_exchanges


def find_arbitrage_opportunities(exchanges: list[str], symbols: list[str]) -> list[dict]:
    opportunities = []

    for symbol in symbols:
        tickers = fetch_tickers_all_exchanges(exchanges, symbol)
        valid = [t for t in tickers if t.get("bid") and t.get("ask")]
        if len(valid) < 2:
            continue

        # Find cheapest place to buy (lowest ask) and priciest place to sell (highest bid)
        buy_at = min(valid, key=lambda t: t["ask"])
        sell_at = max(valid, key=lambda t: t["bid"])

        if buy_at["exchange"] == sell_at["exchange"]:
            continue

        spread_pct = ((sell_at["bid"] - buy_at["ask"]) / buy_at["ask"]) * 100
        net_spread_pct = spread_pct - ASSUMED_ROUND_TRIP_FEE_PCT

        if net_spread_pct >= ARBITRAGE_MIN_SPREAD_PCT:
            opportunities.append({
                "symbol": symbol,
                "buy_exchange": buy_at["exchange"],
                "buy_price": buy_at["ask"],
                "sell_exchange": sell_at["exchange"],
                "sell_price": sell_at["bid"],
                "gross_spread_pct": round(spread_pct, 3),
                "est_net_spread_pct": round(net_spread_pct, 3),
                "note": "Excludes withdrawal/network fees and transfer time — verify before acting.",
            })

    return sorted(opportunities, key=lambda o: o["est_net_spread_pct"], reverse=True)
