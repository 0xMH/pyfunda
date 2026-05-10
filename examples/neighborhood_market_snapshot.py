#!/usr/bin/env python3
"""Compare search results with Funda local market insights.

Usage:
    uv run examples/neighborhood_market_snapshot.py Amsterdam "Twiske-West"
    uv run examples/neighborhood_market_snapshot.py --from-listing 43117443
"""

import argparse
from statistics import median

from funda import Funda, Listing


def location_from_args(
    client: Funda,
    city: str | None,
    neighbourhood: str | None,
    listing_id: str | None,
) -> tuple[str, str]:
    if listing_id:
        listing = client.listing(listing_id)
        if not listing.city or not listing.address.neighbourhood:
            raise SystemExit("Listing has no city/neighbourhood data")
        return listing.city, listing.address.neighbourhood
    if not city or not neighbourhood:
        raise SystemExit("Pass city and neighbourhood, or use --from-listing")
    return city, neighbourhood


def price_per_m2(listing: Listing) -> float | None:
    if not listing.price.amount or not listing.living_area:
        return None
    return listing.price.amount / listing.living_area


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a small neighbourhood market snapshot")
    parser.add_argument("city", nargs="?", help="City")
    parser.add_argument("neighbourhood", nargs="?", help="Neighbourhood")
    parser.add_argument("--from-listing", help="Use city/neighbourhood from a listing")
    parser.add_argument("--pages", type=int, default=2, help="Search pages to sample")
    args = parser.parse_args()

    with Funda() as client:
        city, neighbourhood = location_from_args(client, args.city, args.neighbourhood, args.from_listing)
        insights = client.market_insights(city, neighbourhood)
        listings = list(client.iter_search(city, max_pages=args.pages))

    values = [value for listing in listings if (value := price_per_m2(listing))]
    prices = [listing.price.amount for listing in listings if listing.price.amount]

    print(f"{city} / {neighbourhood}")
    print("-" * (len(city) + len(neighbourhood) + 3))
    print(f"Inhabitants:          {insights.get('inhabitants')}")
    print(f"Funda avg asking/m2:  EUR {insights.get('avg_asking_price_per_m2'):,}")
    if values:
        print(f"Sample median/m2:     EUR {median(values):,.0f}")
    if prices:
        print(f"Sample median price:  EUR {median(prices):,.0f}")
    print(f"Sample listings:      {len(listings)}")


if __name__ == "__main__":
    main()
