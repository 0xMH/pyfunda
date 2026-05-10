#!/usr/bin/env python3
"""Track price changes for Funda listings.

Usage:
    uv run examples/price_tracker.py
    uv run examples/price_tracker.py --add 43117443
    uv run examples/price_tracker.py --add "https://www.funda.nl/detail/koop/..."
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from funda import Funda, FundaError, Listing


HISTORY_FILE = Path("price_history.json")


def load_history() -> dict[str, Any]:
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text())
    return {"listings": {}}


def save_history(history: dict[str, Any]) -> None:
    HISTORY_FILE.write_text(json.dumps(history, indent=2))


def price(listing: Listing) -> int | None:
    return listing.price.amount


def listing_key(listing: Listing) -> str:
    if listing.global_id is not None:
        return str(listing.global_id)
    if listing.id is not None:
        return listing.id
    raise ValueError("Listing has no usable id")


def track_listing(client: Funda, listing_id: str | int, history: dict[str, Any]) -> dict[str, Any] | None:
    try:
        listing = client.listing(listing_id)
    except (FundaError, ValueError) as exc:
        print(f"  Error fetching {listing_id}: {exc}")
        return None

    current_price = price(listing)
    if current_price is None:
        print(f"  Skipping {listing.id}: no price in payload")
        return None

    key = listing_key(listing)
    now = datetime.now().isoformat()
    stored = history["listings"].setdefault(
        key,
        {
            "title": listing.title,
            "city": listing.city,
            "url": listing.url,
            "price_history": [],
        },
    )

    if not stored["price_history"]:
        stored["price_history"].append({"price": current_price, "date": now})
        print(f"  + Added: {listing.title} - EUR {current_price:,}")
        return None

    last_price = stored["price_history"][-1]["price"]
    if current_price == last_price:
        return None

    change = current_price - last_price
    change_pct = (change / last_price) * 100 if last_price else 0
    stored["price_history"].append({"price": current_price, "date": now})
    return {
        "title": stored["title"],
        "city": stored["city"],
        "url": stored["url"],
        "old_price": last_price,
        "new_price": current_price,
        "change": change,
        "change_pct": change_pct,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Track Funda listing prices")
    parser.add_argument("--add", help="Add a listing ID or URL to track")
    args = parser.parse_args()

    history = load_history()
    with Funda() as client:
        if args.add:
            track_listing(client, args.add, history)
            save_history(history)
            return

        if not history["listings"]:
            print("No listings to track. Add one with --add <id-or-url>.")
            return

        print(f"Checking {len(history['listings'])} listings...\n")
        changes = [
            change
            for listing_id in list(history["listings"])
            if (change := track_listing(client, listing_id, history))
        ]

    save_history(history)
    if not changes:
        print("\nNo price changes detected.")
        return

    print("\nPrice changes detected:")
    print("-" * 50)
    for change in changes:
        direction = "dropped" if change["change"] < 0 else "increased"
        print(f"{change['title']} ({change['city']})")
        print(f"  Price {direction}: EUR {change['old_price']:,} -> EUR {change['new_price']:,}")
        print(f"  Change: EUR {change['change']:+,} ({change['change_pct']:+.1f}%)")
        print(f"  {change['url']}")


if __name__ == "__main__":
    main()
