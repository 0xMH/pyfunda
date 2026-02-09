#!/usr/bin/env python3
"""Search for sold listings on Funda.

Find recently sold properties in a given location to analyze
market prices and trends.

Usage:
    uv run examples/search_sold.py amsterdam
    uv run examples/search_sold.py rotterdam --max-price 500000
    uv run examples/search_sold.py utrecht --pages 3
"""

import argparse

from funda import Funda


def main():
    parser = argparse.ArgumentParser(description="Search for sold listings")
    parser.add_argument("location", help="City or area to search in")
    parser.add_argument("--min-price", type=int, help="Minimum price")
    parser.add_argument("--max-price", type=int, help="Maximum price")
    parser.add_argument("--pages", type=int, default=1, help="Number of pages (15 results each)")
    args = parser.parse_args()

    with Funda() as f:
        print(f"Searching for sold listings in {args.location}...")
        print()

        all_listings = []
        for page in range(args.pages):
            results = f.search_listing(
                location=args.location,
                availability="sold",
                price_min=args.min_price,
                price_max=args.max_price,
                sort="newest",
                page=page,
            )
            all_listings.extend(results)

            if len(results) < 15:
                break

        if not all_listings:
            print("No sold listings found.")
            return

        print(f"Found {len(all_listings)} sold listings:")
        print("-" * 70)
        print(f"{'Address':<35} {'City':<15} {'Price':>12} {'m²':>6}")
        print("-" * 70)

        total_price = 0
        total_area = 0
        count_with_area = 0

        for listing in all_listings:
            title = listing["title"][:34]
            city = (listing["city"] or "")[:14]
            price = listing["price"]
            area = listing["living_area"]

            price_str = f"€{price:,}" if price else "N/A"
            area_str = str(area) if area else "-"

            print(f"{title:<35} {city:<15} {price_str:>12} {area_str:>6}")

            if price:
                total_price += price
            if area:
                total_area += area
                count_with_area += 1

        print("-" * 70)

        # Summary statistics
        if all_listings:
            avg_price = total_price // len(all_listings)
            print(f"\nAverage sold price: €{avg_price:,}")

            if count_with_area > 0:
                avg_area = total_area // count_with_area
                avg_price_m2 = total_price // total_area
                print(f"Average living area: {avg_area} m²")
                print(f"Average price per m²: €{avg_price_m2:,}")


if __name__ == "__main__":
    main()
