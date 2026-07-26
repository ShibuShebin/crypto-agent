"""
new_listings.py

"New Listings Watch" -- flags coins the FIRST TIME they appear in a scan.

Honest note on scope: there is no reliable free API for pre-listing airdrop
tracking (the sites that list airdrops don't offer public APIs). What this
does instead, using only data we already have for free: it remembers every
symbol we've ever seen on each exchange (persisted in docs/data/known_symbols.json,
committed by the GitHub Action each run) and flags any symbol that's new since
last time. A coin newly tradable on an exchange is often airdrop/TGE-linked,
so this is a reasonable proxy -- just not a literal "airdrop calendar."
"""
import json
import os

KNOWN_SYMBOLS_PATH = os.path.join(os.path.dirname(__file__), "docs", "data", "known_symbols.json")


def load_known_symbols() -> dict:
    """Returns {exchange_id: [symbols...]} seen in all prior runs."""
    try:
        with open(KNOWN_SYMBOLS_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_known_symbols(known: dict):
    os.makedirs(os.path.dirname(KNOWN_SYMBOLS_PATH), exist_ok=True)
    with open(KNOWN_SYMBOLS_PATH, "w") as f:
        json.dump(known, f, indent=2)


def detect_new_listings(exchange_id: str, current_symbols: list[str], known: dict) -> list[str]:
    """
    Returns symbols in current_symbols not present in known[exchange_id].
    Mutates `known` in place to include the new symbols (caller should save_known_symbols after).

    On the very first run ever for an exchange (no baseline yet), nothing is
    flagged -- otherwise every coin would falsely show up as "new" on day one.
    """
    is_first_run_for_exchange = exchange_id not in known
    seen = set(known.get(exchange_id, []))

    new_ones = [] if is_first_run_for_exchange else [s for s in current_symbols if s not in seen]

    updated = seen.union(current_symbols)
    known[exchange_id] = sorted(updated)

    return new_ones
