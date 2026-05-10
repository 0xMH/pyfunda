#!/usr/bin/env python3
"""Fetch historical price data for a Funda listing.

Usage:
    uv run examples/price_history.py 43032486
    uv run examples/price_history.py "https://www.funda.nl/detail/koop/..."
"""

import argparse

from funda import Funda, PriceChange


def source_label(change: PriceChange) -> str:
    labels = {
        "asking_price": "Asking price",
        "sold": "Sold",
        "woz": "WOZ",
    }
    return labels.get(change.status or "", change.status or "unknown")


def main() -> None:
    parser = argparse.ArgumentParser(description="Get historical price data for a listing")
    parser.add_argument("listing", help="Listing ID or Funda URL")
    args = parser.parse_args()

    with Funda() as client:
        listing = client.listing(args.listing)
        history = client.price_history(listing)

    print(f"\n{listing.title}, {listing.city}")
    print(f"Current price: {listing.price.formatted}")
    print(f"URL: {listing.url}")

    if not history.changes:
        print("\nNo price history available.")
        return

    print(f"\nPrice History ({len(history.changes)} records):")
    print("-" * 55)
    print(f"{'Date':<18} {'Price':<14} {'Type'}")
    print("-" * 55)

    for change in history.changes:
        print(f"{change.date or 'Unknown':<18} {change.human_price or 'N/A':<14} {source_label(change)}")

    funda_prices = [change.price for change in history.changes if change.source == "Funda" and change.price]
    if len(funda_prices) >= 2:
        newest, oldest = funda_prices[0], funda_prices[-1]
        print(f"\nFunda price change: {((newest - oldest) / oldest) * 100:+.1f}%")


if __name__ == "__main__":
    main()
