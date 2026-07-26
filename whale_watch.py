"""
whale_watch.py

Flags large ERC-20 token transfers as a PROXY for "unusual activity."

Important honesty note: this is NOT insider-trading detection. It has no
way to see intent, non-public information, or who is behind a wallet unless
that wallet is independently labeled (e.g. a known exchange address you've
added to config.KNOWN_EXCHANGE_WALLETS). It only surfaces large, entirely
public on-chain transfers -- which sometimes precede price moves, but often
don't mean anything at all (internal exchange rebalancing, custodial
transfers, etc. are common and benign).

Uses Etherscan's free API (register for a free key at etherscan.io/apis).
Covers Ethereum-mainnet ERC-20 tokens only -- not BSC, Solana, or other chains.
"""
import logging
import httpx
import config

logger = logging.getLogger("whale_watch")

ETHERSCAN_BASE = "https://api.etherscan.io/api"


def _approx_price_usd(symbol: str, reference_prices: dict) -> float | None:
    if symbol in ("USDT", "USDC"):
        return 1.0
    return reference_prices.get(symbol)


async def get_whale_alerts(reference_prices: dict) -> list[dict]:
    """
    reference_prices: {"WBTC": <approx usd price>, "LINK": <approx usd price>, ...}
    used to convert raw token amounts into approximate USD for the $ threshold.
    """
    if not config.ENABLE_WHALE_WATCH:
        return []
    if not config.ETHERSCAN_API_KEY:
        logger.info("Whale watch skipped: no ETHERSCAN_API_KEY configured.")
        return []

    alerts = []
    async with httpx.AsyncClient(timeout=20.0) as client:
        for symbol, contract in config.WHALE_WATCH_TOKENS.items():
            try:
                resp = await client.get(ETHERSCAN_BASE, params={
                    "module": "account",
                    "action": "tokentx",
                    "contractaddress": contract,
                    "page": 1,
                    "offset": 25,
                    "sort": "desc",
                    "apikey": config.ETHERSCAN_API_KEY,
                })
                resp.raise_for_status()
                data = resp.json()
                if data.get("status") != "1":
                    continue

                price = _approx_price_usd(symbol, reference_prices)
                for tx in data.get("result", []):
                    try:
                        decimals = int(tx.get("tokenDecimal", 18))
                        raw_value = int(tx["value"])
                        amount = raw_value / (10 ** decimals)
                    except (KeyError, ValueError):
                        continue

                    if price is None:
                        continue  # can't estimate USD value, skip rather than guess
                    usd_value = amount * price
                    if usd_value < config.WHALE_ALERT_MIN_USD:
                        continue

                    from_label = config.KNOWN_EXCHANGE_WALLETS.get(tx.get("from", "").lower())
                    to_label = config.KNOWN_EXCHANGE_WALLETS.get(tx.get("to", "").lower())

                    alerts.append({
                        "token": symbol,
                        "amount": round(amount, 4),
                        "approx_usd": round(usd_value, 0),
                        "from": from_label or (tx.get("from", "")[:10] + "…"),
                        "to": to_label or (tx.get("to", "")[:10] + "…"),
                        "tx_hash": tx.get("hash"),
                        "note": "Large public on-chain transfer -- not confirmed insider activity.",
                    })
            except Exception as e:
                logger.warning(f"Whale watch failed for {symbol}: {e}")

    alerts.sort(key=lambda a: a["approx_usd"], reverse=True)
    return alerts[:25]
