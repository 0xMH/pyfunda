#!/usr/bin/env python3
"""Alert on new Funda listings matching your search criteria.

Monitors a search and notifies when new listings appear.
Can send notifications via terminal, macOS notifications, or webhook.

Usage:
    uv run examples/new_listings_alert.py --location amsterdam --max-price 500000

    # With desktop notifications (macOS):
    uv run examples/new_listings_alert.py --location amsterdam --notify

    # With webhook (Discord, Slack, etc.):
    uv run examples/new_listings_alert.py --location amsterdam --webhook "https://..."
"""

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path

import requests

from funda import Funda

SEEN_FILE = Path("seen_listings.json")


def load_seen() -> set:
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return set()


def save_seen(seen: set) -> None:
    SEEN_FILE.write_text(json.dumps(list(seen)))


def notify_macos(title: str, message: str) -> None:
    """Send macOS notification."""
    subprocess.run([
        "osascript", "-e",
        f'display notification "{message}" with title "{title}"'
    ], check=False)


def notify_webhook(webhook_url: str, listings: list) -> None:
    """Send listings to a webhook (Discord/Slack compatible)."""
    content = "\n".join([
        f"**{l['title']}** ({l['city']}) - €{l['price']:,}\n{l['url']}"
        for l in listings
    ])
    requests.post(webhook_url, json={"content": content}, timeout=10)


def main():
    parser = argparse.ArgumentParser(description="Alert on new Funda listings")
    parser.add_argument("--location", "-l", required=True, help="City or area")
    parser.add_argument("--max-price", type=int, help="Maximum price")
    parser.add_argument("--min-price", type=int, help="Minimum price")
    parser.add_argument("--min-area", type=int, help="Minimum living area (m²)")
    parser.add_argument("--offering", choices=["buy", "rent"], default="buy")
    parser.add_argument("--notify", action="store_true", help="Send macOS notification")
    parser.add_argument("--webhook", help="Webhook URL for notifications")
    args = parser.parse_args()

    seen = load_seen()
    new_listings = []

    with Funda() as f:
        results = f.search_listing(
            location=args.location,
            offering_type=args.offering,
            price_min=args.min_price,
            price_max=args.max_price,
            area_min=args.min_area,
            sort="newest",
        )

        for listing in results:
            lid = str(listing["global_id"])
            if lid not in seen:
                seen.add(lid)
                new_listings.append({
                    "title": listing["title"],
                    "city": listing["city"],
                    "price": listing["price"],
                    "url": f"https://www.funda.nl/detail/{listing['global_id']}/",
                    "area": listing.get("living_area"),
                })

    save_seen(seen)

    if not new_listings:
        print(f"[{datetime.now():%H:%M}] No new listings")
        return

    print(f"[{datetime.now():%H:%M}] Found {len(new_listings)} new listing(s):\n")
    for l in new_listings:
        area = f", {l['area']}m²" if l.get("area") else ""
        print(f"  {l['title']} ({l['city']}{area})")
        print(f"  €{l['price']:,}")
        print(f"  {l['url']}\n")

    if args.notify:
        notify_macos(
            "New Funda Listings",
            f"{len(new_listings)} new listing(s) in {args.location}"
        )

    if args.webhook:
        notify_webhook(args.webhook, new_listings)


if __name__ == "__main__":
    main()
