"""
scripts/generate_static.py

Runs ONE full scan cycle (see pipeline.py for the full flow) and writes the
results as static JSON into docs/data/. Meant to be run on a schedule by
GitHub Actions, with docs/ served as a static site via GitHub Pages.

Run manually:  python scripts/generate_static.py
"""
import asyncio
import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
logging.basicConfig(level=logging.INFO)

from pipeline import run_full_scan

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "data")


async def main():
    result = await run_full_scan()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(os.path.join(OUTPUT_DIR, "signals.json"), "w") as f:
        json.dump({
            "last_updated": result["last_updated"],
            "signals": result["signals"],
            "errors": result["errors"],
        }, f, indent=2)

    with open(os.path.join(OUTPUT_DIR, "high_confidence.json"), "w") as f:
        json.dump({
            "last_updated": result["last_updated"],
            "signals": result["high_confidence_signals"],
        }, f, indent=2)

    with open(os.path.join(OUTPUT_DIR, "arbitrage.json"), "w") as f:
        json.dump({
            "last_updated": result["last_updated"],
            "opportunities": result["arbitrage"],
        }, f, indent=2)

    with open(os.path.join(OUTPUT_DIR, "new_listings.json"), "w") as f:
        json.dump({
            "last_updated": result["last_updated"],
            "new_listings": result["new_listings"],
        }, f, indent=2)

    with open(os.path.join(OUTPUT_DIR, "whale_alerts.json"), "w") as f:
        json.dump({
            "last_updated": result["last_updated"],
            "alerts": result["whale_alerts"],
        }, f, indent=2)

    print(
        f"Wrote {len(result['signals'])} signals "
        f"({len(result['high_confidence_signals'])} high-confidence), "
        f"{len(result['arbitrage'])} arbitrage opportunities, "
        f"{len(result['whale_alerts'])} whale alerts."
    )


if __name__ == "__main__":
    asyncio.run(main())
