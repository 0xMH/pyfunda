#!/usr/bin/env python3
"""Fetch many listing details efficiently.

Use this when search results are too lightweight and you need full listing
payloads for a known set of ids.

Usage:
    uv run examples/batch_details.py 43117443 43333315
    uv run examples/batch_details.py --workers 6 43117443 43333315 43826303
"""

import argparse

from funda import Funda, Listing


def print_table(listings: list[Listing]) -> None:
    print(f"{'ID':<10} {'City':<16} {'Price':>14} {'Area':>6}  Title")
    print("-" * 80)
    for listing in listings:
        price = listing.price.amount
        price_text = f"EUR {price:,}" if price else "-"
        area = str(listing.living_area or "-")
        print(f"{listing.id or '-':<10} {(listing.city or '-')[:16]:<16} {price_text:>14} {area:>6}  {listing.title}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch listing details in parallel")
    parser.add_argument("listing_ids", nargs="+", help="Listing ids or Funda URLs")
    parser.add_argument("--workers", type=int, default=4, help="Parallel workers")
    args = parser.parse_args()

    with Funda() as client:
        listings = client.listings(args.listing_ids, workers=args.workers)

    print_table(listings)


if __name__ == "__main__":
    main()
