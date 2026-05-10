#!/usr/bin/env python3
"""Build a simple comparable-sales table for a subject listing.

Usage:
    uv run examples/similar_sales_comp.py 43117443
"""

import argparse

from funda import Funda, Listing


def row(listing: Listing) -> tuple[str, str, str, str, str]:
    price = f"EUR {listing.price.amount:,}" if listing.price.amount else "-"
    area = f"{listing.living_area} m2" if listing.living_area else "-"
    return (
        listing.id or "-",
        listing.title or "-",
        listing.city or "-",
        price,
        area,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Show similar recently sold listings")
    parser.add_argument("listing", help="Subject listing id or Funda URL")
    parser.add_argument("--workers", type=int, default=4, help="Parallel detail workers")
    args = parser.parse_args()

    with Funda() as client:
        subject = client.listing(args.listing)
        similar = client.similar_listings(subject)
        sold_ids = similar.get("recently_sold", [])
        sold = client.listings(sold_ids, workers=args.workers) if sold_ids else []

    print(f"Subject: {subject.title} ({subject.city})")
    print(f"Price:   {subject.price.formatted or subject.price.amount}")
    print()
    print(f"{'ID':<10} {'Title':<35} {'City':<16} {'Price':>14} {'Area':>8}")
    print("-" * 90)
    for item in sold:
        item_id, title, city, price, area = row(item)
        print(f"{item_id:<10} {title[:35]:<35} {city[:16]:<16} {price:>14} {area:>8}")


if __name__ == "__main__":
    main()
