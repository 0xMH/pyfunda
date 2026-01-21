#!/usr/bin/env python3
"""Fetch historical price data for a Funda listing.

Shows previous asking prices, WOZ tax assessments, and sale history
using the Walter Living API.

Usage:
    uv run examples/price_history.py 89666837
    uv run examples/price_history.py "https://www.funda.nl/detail/koop/..."
"""

import argparse
import sys

from funda import Funda


def main():
    parser = argparse.ArgumentParser(description="Get historical price data for a listing")
    parser.add_argument("listing", help="Listing ID or Funda URL")
    args = parser.parse_args()

    with Funda() as f:
        # Get listing details
        print("Fetching listing...")
        try:
            listing = f.get_listing(args.listing)
        except LookupError as e:
            print(f"Error: {e}")
            sys.exit(1)

        print(f"\n{listing['title']}, {listing['city']}")
        print(f"Current price: {listing['price_formatted']}")
        print(f"URL: {listing['url']}")

        # Get price history
        print("\nFetching price history...")
        try:
            history = f.get_price_history(listing)
        except LookupError as e:
            print(f"Error: {e}")
            sys.exit(1)

        if not history:
            print("No price history available.")
            return

        print(f"\nPrice History ({len(history)} records):")
        print("-" * 55)
        print(f"{'Date':<18} {'Price':<14} {'Type'}")
        print("-" * 55)

        for change in history:
            date = change.get("date", "Unknown")
            price = change.get("human_price", "N/A")
            status = change.get("status", "unknown")

            # Format status for display
            status_labels = {
                "asking_price": "Asking price",
                "sold": "Sold",
                "woz": "WOZ (tax assessment)",
            }
            type_str = status_labels.get(status, status)

            print(f"{date:<18} {price:<14} {type_str}")

        # Show price trends
        funda_prices = [c for c in history if c.get("source") == "Funda"]
        if len(funda_prices) >= 2:
            newest = funda_prices[0].get("price", 0)
            oldest = funda_prices[-1].get("price", 0)
            if oldest > 0:
                change = ((newest - oldest) / oldest) * 100
                print(f"\nFunda price change: {change:+.1f}% (from €{oldest:,} to €{newest:,})")


if __name__ == "__main__":
    main()
