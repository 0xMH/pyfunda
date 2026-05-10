#!/usr/bin/env python3
"""Poll for new listings by incrementing IDs."""

import json
from pathlib import Path

from funda import Funda, Listing


STATE_FILE = Path("last_seen_id.json")


def load_last_id() -> int | None:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text()).get("last_id")
    return None


def save_last_id(last_id: int) -> None:
    STATE_FILE.write_text(json.dumps({"last_id": last_id}, indent=2))


def listing_id(listing: Listing) -> int | None:
    return listing.global_id


def main() -> None:
    with Funda() as client:
        last_id = load_last_id()
        if last_id is None:
            last_id = client.latest_listing_id()
            print(f"First run, starting from latest search ID: {last_id}")
            save_last_id(last_id)
            return

        max_id = last_id
        count = 0
        for listing in client.new_listings(since_id=last_id):
            count += 1
            if listing_id(listing) is not None:
                max_id = max(max_id, listing_id(listing))

            price = listing.price.amount
            price_text = f"EUR {price:,}" if price else "price unknown"
            print(f"New: {listing.title}, {listing.city}")
            print(f"     {price_text} - {listing.living_area or '?'} m2")
            print(f"     {listing.url}")
            print()

    save_last_id(max_id)
    print(f"Found {count} new listings. Saved last ID: {max_id}" if count else "No new listings found.")


if __name__ == "__main__":
    main()
