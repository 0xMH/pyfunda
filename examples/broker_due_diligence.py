#!/usr/bin/env python3
"""Inspect a broker's profile, reviews, and recent listings.

Usage:
    uv run examples/broker_due_diligence.py 16122
    uv run examples/broker_due_diligence.py --from-listing 43117443
"""

import argparse

from funda import Funda, Listing


def broker_source(client: Funda, broker_id: str | None, listing_id: str | None) -> Listing | str:
    if listing_id:
        return client.listing(listing_id)
    if broker_id:
        return broker_id
    raise ValueError("Pass a broker id or --from-listing")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect a broker profile")
    parser.add_argument("broker_id", nargs="?", help="Broker id")
    parser.add_argument("--from-listing", help="Resolve broker from this listing id or URL")
    args = parser.parse_args()

    with Funda() as client:
        broker = broker_source(client, args.broker_id, args.from_listing)
        info = client.broker_info(broker)
        reviews = client.broker_reviews(broker)
        listings = client.broker_listings(broker)

    active = [item for item in listings if item.get("status") == "for_sale"]
    sold = [item for item in listings if item.get("status") == "sold"]

    print(info["name"])
    print("-" * len(info["name"]))
    print(f"Broker id: {info['broker_id']}")
    print(f"Phone:     {info.get('phone') or '-'}")
    print(f"Email:     {info.get('email') or '-'}")
    print(f"Website:   {info.get('website') or '-'}")
    print(f"Reviews:   {reviews.get('average')} average across {reviews.get('number_of_reviews')} reviews")
    print(f"Listings:  {len(active)} active, {len(sold)} sold, {len(listings)} total")
    print()

    print("Recent handled listings:")
    for item in listings[:10]:
        price = f"EUR {item['price']:,}" if item.get("price") else "-"
        print(f"- {item.get('status'):<8} {price:>12}  {item.get('title')} ({item.get('city')})")


if __name__ == "__main__":
    main()
