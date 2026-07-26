"""
arbitrage.py

Compares the live price of every common asset across exchanges using the
SAME bulk ticker data already fetched for coin scanning -- no extra API
calls needed, so this now covers the entire coin universe for free instead
of just a handful of hardcoded symbols.

Note: this checks SPOT ticker spreads only. Real arbitrage execution also
needs to account for withdrawal/transfer time, network fees, and transfer
limits between exchanges -- those aren't included here since they vary a
lot by exchange and asset. Treat flagged opportunities as leads to verify
manually, not auto-executable trades.
"""
from collections import defaultdict
import config


def find_arbitrage_opportunities(bulk_tickers: dict[str, dict]) -> list[dict]:
    """
    bulk_tickers: {exchange_id: {symbol: ccxt_ticker_dict}}  (from fetch_all_tickers_bulk)
    Returns opportunities sorted by estimated net spread, highest first.
    """
    # Map each base asset (e.g. "BTC") to {exchange_id: {bid, ask}}, using each
    # exchange's configured quote currency (USDT on Binance, USD on Coinbase/Kraken).
    base_map = defaultdict(dict)

    for exchange_id, tickers in bulk_tickers.items():
        quote = config.QUOTE_CURRENCY.get(exchange_id, "USDT")
        for symbol, t in tickers.items():
            if not symbol.endswith(f"/{quote}"):
                continue
            base = symbol.split("/")[0]
            bid = t.get("bid") or t.get("last")
            ask = t.get("ask") or t.get("last")
            if bid is None or ask is None:
                continue
            base_map[base][exchange_id] = {"bid": bid, "ask": ask, "symbol": symbol}

    opportunities = []
    for base, per_exchange in base_map.items():
        if len(per_exchange) < 2:
            continue  # need at least 2 exchanges to compare

        buy_ex_id, buy_data = min(per_exchange.items(), key=lambda kv: kv[1]["ask"])
        sell_ex_id, sell_data = max(per_exchange.items(), key=lambda kv: kv[1]["bid"])

        if buy_ex_id == sell_ex_id:
            continue

        spread_pct = ((sell_data["bid"] - buy_data["ask"]) / buy_data["ask"]) * 100
        net_spread_pct = spread_pct - config.ASSUMED_ROUND_TRIP_FEE_PCT

        if net_spread_pct >= config.ARBITRAGE_MIN_SPREAD_PCT:
            opportunities.append({
                "asset": base,
                "buy_exchange": buy_ex_id,
                "buy_symbol": buy_data["symbol"],
                "buy_price": buy_data["ask"],
                "sell_exchange": sell_ex_id,
                "sell_symbol": sell_data["symbol"],
                "sell_price": sell_data["bid"],
                "gross_spread_pct": round(spread_pct, 3),
                "est_net_spread_pct": round(net_spread_pct, 3),
                "note": "Excludes withdrawal/network fees and transfer time -- verify before acting.",
            })

    return sorted(opportunities, key=lambda o: o["est_net_spread_pct"], reverse=True)
