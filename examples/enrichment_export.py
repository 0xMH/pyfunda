#!/usr/bin/env python3
"""Export listing details plus enrichment data to JSON.

Useful when building a local dataset with contact, market, and broker context.

Usage:
    uv run examples/enrichment_export.py 43117443 --output listing_enriched.json
"""

import argparse
import json
from pathlib import Path
from typing import Any

from funda import Funda, Listing


def safe_call(default: Any, func):
    try:
        return func()
    except LookupError:
        return default


def payload(client: Funda, listing: Listing) -> dict[str, Any]:
    return {
        "listing": listing.to_dict(),
        "summary": safe_call(None, lambda: client.listing_summary(listing).to_dict()),
        "contact_info": safe_call(None, lambda: client.contact_info(listing)),
        "contact_form": safe_call(None, lambda: client.contact_form(listing)),
        "similar_listings": safe_call({}, lambda: client.similar_listings(listing)),
        "market_insights": safe_call(None, lambda: client.market_insights(listing)),
        "broker_info": safe_call(None, lambda: client.broker_info(listing)),
        "broker_reviews": safe_call(None, lambda: client.broker_reviews(listing)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Export enriched listing data")
    parser.add_argument("listing", help="Listing id or Funda URL")
    parser.add_argument("--output", "-o", default="listing_enriched.json", help="Output JSON path")
    args = parser.parse_args()

    with Funda() as client:
        listing = client.listing(args.listing)
        data = payload(client, listing)

    output = Path(args.output)
    output.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"Saved enriched payload for {listing.title} to {output}")


if __name__ == "__main__":
    main()
