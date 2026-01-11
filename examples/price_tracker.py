#!/usr/bin/env python3
"""Track price changes for Funda listings.

Monitors a list of listings and alerts when prices change.
Stores history in a JSON file for persistence.

Usage:
    uv run examples/price_tracker.py

    # Or add listings to track:
    uv run examples/price_tracker.py --add 43117443
    uv run examples/price_tracker.py --add "https://www.funda.nl/detail/koop/..."
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from funda import Funda

HISTORY_FILE = Path("price_history.json")


def load_history() -> dict:
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text())
    return {"listings": {}}


def save_history(history: dict) -> None:
    HISTORY_FILE.write_text(json.dumps(history, indent=2))


def track_listing(funda: Funda, listing_id: str | int, history: dict) -> dict | None:
    """Fetch listing and check for price changes. Returns change info if changed."""
    try:
        listing = funda.get_listing(listing_id)
    except Exception as e:
        print(f"  Error fetching {listing_id}: {e}")
        return None

    lid = str(listing["global_id"])
    current_price = listing["price"]
    now = datetime.now().isoformat()

    if lid not in history["listings"]:
        # New listing
        history["listings"][lid] = {
            "title": listing["title"],
            "city": listing["city"],
            "url": listing["url"],
            "price_history": [{"price": current_price, "date": now}],
        }
        print(f"  + Added: {listing['title']} - €{current_price:,}")
        return None

    stored = history["listings"][lid]
    last_price = stored["price_history"][-1]["price"]

    if current_price != last_price:
        change = current_price - last_price
        pct = (change / last_price) * 100
        stored["price_history"].append({"price": current_price, "date": now})

        return {
            "title": stored["title"],
            "city": stored["city"],
            "url": stored["url"],
            "old_price": last_price,
            "new_price": current_price,
            "change": change,
            "change_pct": pct,
        }

    return None


def main():
    parser = argparse.ArgumentParser(description="Track Funda listing prices")
    parser.add_argument("--add", help="Add a listing ID or URL to track")
    args = parser.parse_args()

    history = load_history()

    with Funda() as f:
        if args.add:
            # Add new listing to track
            track_listing(f, args.add, history)
            save_history(history)
            return

        if not history["listings"]:
            print("No listings to track. Add some with --add <id>")
            print("Example: uv run examples/price_tracker.py --add 43117443")
            return

        # Check all tracked listings
        print(f"Checking {len(history['listings'])} listings...\n")
        changes = []

        for lid in list(history["listings"].keys()):
            change = track_listing(f, lid, history)
            if change:
                changes.append(change)

        save_history(history)

        if changes:
            print("\nPrice changes detected:")
            print("-" * 50)
            for c in changes:
                direction = "dropped" if c["change"] < 0 else "increased"
                print(f"{c['title']} ({c['city']})")
                print(f"  Price {direction}: €{c['old_price']:,} -> €{c['new_price']:,}")
                print(f"  Change: €{c['change']:+,} ({c['change_pct']:+.1f}%)")
                print(f"  {c['url']}")
                print()
        else:
            print("\nNo price changes detected.")


if __name__ == "__main__":
    main()
