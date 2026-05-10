#!/usr/bin/env python3
"""Exercise the main pyfunda API surface in one small run.

The example keeps live traffic intentionally small while demonstrating:

- listing detail lookup
- one-page search
- parallel detail fetching
- paged search iteration
- price history
- enrichment endpoints
- serialization with dataclasses

Usage:
    uv run examples/full_api_walkthrough.py
    uv run examples/full_api_walkthrough.py --listing 43117443 --location amsterdam
"""

import argparse
from collections.abc import Iterable
from typing import Any

from funda import Funda, FundaError, Listing


def compact(value: Any, keys: Iterable[str]) -> dict[str, Any]:
    return {key: value.get(key) for key in keys}


def describe_listing(listing: Listing) -> None:
    print("Listing")
    print("-------")
    print(f"id:        {listing.id}")
    print(f"global_id: {listing.global_id}")
    print(f"title:     {listing.title}")
    print(f"city:      {listing.city}")
    print(f"price:     {listing.price.formatted or listing.price.amount}")
    print(f"area:      {listing.living_area} m2")
    print(f"bedrooms:  {listing.bedrooms}")
    print(f"energy:    {listing.energy_label}")
    print(f"url:       {listing.url}")
    print()


def show_search(client: Funda, location: str) -> list[Listing]:
    results = client.search(location, max_price=500000, sort="newest")
    print(f"Search: {len(results)} listings in {location!r} under 500000")
    for item in results[:5]:
        price = item.price.amount
        price_text = f"EUR {price:,}" if price else "price unknown"
        print(f"- {item.title} ({item.city}) - {price_text}")
    print()
    return results


def show_parallel_details(client: Funda, results: list[Listing]) -> None:
    ids = [item.global_id for item in results[:4] if item.global_id]
    details = client.listings(ids, workers=4)
    print(f"Parallel details: {[item.global_id for item in details]}")
    print()


def show_iter_search(client: Funda, location: str) -> None:
    listings = list(client.iter_search(location, max_price=500000, max_pages=2, workers=2))
    print(f"Parallel paged search: {len(listings)} listings across 2 pages")
    print()


def show_price_history(client: Funda, listing: Listing) -> None:
    try:
        history = client.price_history(listing)
    except FundaError as exc:
        print(f"Price history unavailable: {exc}")
        print()
        return

    print(f"Price history: {len(history.changes)} changes")
    for change in history.changes[:5]:
        print(f"- {change.date}: {change.human_price} ({change.status})")
    print()


def show_enrichment(client: Funda, listing: Listing) -> None:
    print("Enrichment")
    print("----------")

    calls = [
        ("contact_info", lambda: client.contact_info(listing), ("broker_id", "name", "phone")),
        ("contact_form", lambda: client.contact_form(listing), ("office_id", "days", "times_of_day")),
        ("similar_listings", lambda: client.similar_listings(listing), ("recently_listed", "recently_sold")),
        (
            "market_insights",
            lambda: client.market_insights(listing),
            ("city", "neighbourhood", "avg_asking_price_per_m2"),
        ),
        ("broker_info", lambda: client.broker_info(listing), ("broker_id", "name", "phone")),
        ("broker_reviews", lambda: client.broker_reviews(listing), ("average", "number_of_reviews")),
    ]

    summary = client.listing_summary(listing)
    print(f"listing_summary: {summary.title} ({summary.global_id})")

    broker_listings = client.broker_listings(listing)
    print(f"broker_listings: {len(broker_listings)} rows")

    for name, call, keys in calls:
        try:
            value = call()
        except LookupError as exc:
            print(f"{name}: unavailable ({exc})")
            continue
        print(f"{name}: {compact(value, keys)}")
    print()


def show_serialization(listing: Listing) -> None:
    data = listing.to_dict()
    print("Serialized keys:", ", ".join(sorted(data)[:8]), "...")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a small pyfunda API walkthrough")
    parser.add_argument("--listing", default="43117443", help="Listing ID or Funda URL")
    parser.add_argument("--location", default="amsterdam", help="Search location")
    args = parser.parse_args()

    with Funda(timeout=30) as client:
        listing = client.listing(args.listing)
        describe_listing(listing)

        results = show_search(client, args.location)
        show_parallel_details(client, results)
        show_iter_search(client, args.location)
        show_price_history(client, listing)
        show_enrichment(client, listing)
        show_serialization(listing)


if __name__ == "__main__":
    main()
