#!/usr/bin/env python3
"""Alert on new Funda listings matching your search criteria.

Usage:
    uv run examples/new_listings_alert.py --location amsterdam --max-price 500000
    uv run examples/new_listings_alert.py --location amsterdam --notify
    uv run examples/new_listings_alert.py --location amsterdam --webhook "https://..."
"""

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from curl_cffi import requests

from funda import Funda, Listing


SEEN_FILE = Path("seen_listings.json")


def load_seen() -> set[str]:
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return set()


def save_seen(seen: set[str]) -> None:
    SEEN_FILE.write_text(json.dumps(sorted(seen), indent=2))


def notify_macos(title: str, message: str) -> None:
    subprocess.run(
        ["osascript", "-e", f'display notification "{message}" with title "{title}"'],
        check=False,
    )


def notify_webhook(webhook_url: str, listings: list[dict[str, Any]]) -> None:
    content = "\n".join(
        f"**{item['title']}** ({item['city']}) - {item['price']}\n{item['url']}"
        for item in listings
    )
    requests.post(webhook_url, json={"content": content}, timeout=10)


def listing_key(listing: Listing) -> str | None:
    if listing.global_id is not None:
        return str(listing.global_id)
    return listing.id


def alert_payload(listing: Listing) -> dict[str, Any]:
    price = listing.price.amount
    return {
        "title": listing.title,
        "city": listing.city,
        "price": f"EUR {price:,}" if price else "price unknown",
        "url": listing.url,
        "area": listing.living_area,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Alert on new Funda listings")
    parser.add_argument("--location", "-l", required=True, help="City or area")
    parser.add_argument("--max-price", type=int, help="Maximum price")
    parser.add_argument("--min-price", type=int, help="Minimum price")
    parser.add_argument("--min-area", type=int, help="Minimum living area")
    parser.add_argument("--category", choices=["buy", "rent"], default="buy")
    parser.add_argument("--notify", action="store_true", help="Send macOS notification")
    parser.add_argument("--webhook", help="Webhook URL for notifications")
    args = parser.parse_args()

    seen = load_seen()
    new_listings: list[dict[str, Any]] = []

    with Funda() as client:
        results = client.search(
            args.location,
            category=args.category,
            min_price=args.min_price,
            max_price=args.max_price,
            min_area=args.min_area,
            sort="newest",
        )

    for listing in results:
        key = listing_key(listing)
        if key and key not in seen:
            seen.add(key)
            new_listings.append(alert_payload(listing))

    save_seen(seen)
    if not new_listings:
        print(f"[{datetime.now():%H:%M}] No new listings")
        return

    print(f"[{datetime.now():%H:%M}] Found {len(new_listings)} new listing(s):\n")
    for item in new_listings:
        area = f", {item['area']}m2" if item.get("area") else ""
        print(f"  {item['title']} ({item['city']}{area})")
        print(f"  {item['price']}")
        print(f"  {item['url']}\n")

    if args.notify:
        notify_macos("New Funda Listings", f"{len(new_listings)} new listing(s) in {args.location}")
    if args.webhook:
        notify_webhook(args.webhook, new_listings)


if __name__ == "__main__":
    main()
