#!/usr/bin/env python3
"""Search sold listings and print simple market statistics.

Usage:
    uv run examples/search_sold.py amsterdam
    uv run examples/search_sold.py rotterdam --max-price 500000
    uv run examples/search_sold.py utrecht --pages 3
"""

import argparse

from funda import Funda, Listing


def price(listing: Listing) -> int | None:
    return listing.price.amount


def main() -> None:
    parser = argparse.ArgumentParser(description="Search sold Funda listings")
    parser.add_argument("location", help="City or area to search in")
    parser.add_argument("--min-price", type=int, help="Minimum price")
    parser.add_argument("--max-price", type=int, help="Maximum price")
    parser.add_argument("--pages", type=int, default=1, help="Number of pages to fetch")
    args = parser.parse_args()

    with Funda() as client:
        listings = list(
            client.iter_search(
                args.location,
                category="sold",
                min_price=args.min_price,
                max_price=args.max_price,
                sort="newest",
                max_pages=args.pages,
            )
        )

    if not listings:
        print("No sold listings found.")
        return

    print(f"Found {len(listings)} sold listings:")
    print("-" * 70)
    print(f"{'Address':<35} {'City':<15} {'Price':>12} {'m2':>6}")
    print("-" * 70)

    prices = [value for listing in listings if (value := price(listing))]
    areas = [listing.living_area for listing in listings if listing.living_area]

    for listing in listings:
        price_text = f"EUR {price(listing):,}" if price(listing) else "N/A"
        area_text = str(listing.living_area) if listing.living_area else "-"
        title = (listing.title or "")[:34]
        city = (listing.city or "")[:14]
        print(f"{title:<35} {city:<15} {price_text:>12} {area_text:>6}")

    print("-" * 70)
    if prices:
        print(f"\nAverage sold price: EUR {sum(prices) // len(prices):,}")
    if areas:
        print(f"Average living area: {sum(areas) // len(areas)} m2")
    if prices and areas:
        print(f"Average price per m2: EUR {sum(prices) // sum(areas):,}")


if __name__ == "__main__":
    main()
