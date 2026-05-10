#!/usr/bin/env python3
"""Export Funda search results to CSV or Excel.

Usage:
    uv run examples/export_to_csv.py --location amsterdam --output listings.csv
    uv run examples/export_to_csv.py -l amsterdam --max-price 600000 --min-area 60 -o results.csv
    uv run examples/export_to_csv.py -l amsterdam --pages 3 -o all_listings.xlsx
"""

import argparse
import csv
from pathlib import Path
from typing import Any

from funda import Funda, Listing


COLUMNS = [
    "id",
    "global_id",
    "tiny_id",
    "title",
    "city",
    "postcode",
    "price",
    "price_formatted",
    "living_area",
    "plot_area",
    "bedrooms",
    "rooms",
    "energy_label",
    "construction_year",
    "object_type",
    "url",
    "latitude",
    "longitude",
]


def row(listing: Listing) -> dict[str, Any]:
    return {
        "id": listing.id,
        "global_id": listing.global_id,
        "tiny_id": listing.tiny_id,
        "title": listing.title,
        "city": listing.city,
        "postcode": listing.postcode,
        "price": listing.price.amount,
        "price_formatted": listing.price.formatted,
        "living_area": listing.living_area,
        "plot_area": listing.plot_area,
        "bedrooms": listing.bedrooms,
        "rooms": listing.rooms_count,
        "energy_label": listing.energy_label,
        "construction_year": listing.property_details.construction_year,
        "object_type": listing.property_details.object_type,
        "url": listing.url,
        "latitude": listing.location.latitude,
        "longitude": listing.location.longitude,
    }


def export_csv(rows: list[dict[str, Any]], output: Path) -> None:
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def export_excel(rows: list[dict[str, Any]], output: Path) -> None:
    try:
        import openpyxl
    except ImportError as exc:
        raise SystemExit("Excel export requires openpyxl: uv pip install openpyxl") from exc

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Funda Listings"
    sheet.append(COLUMNS)
    for item in rows:
        sheet.append([item.get(column, "") for column in COLUMNS])
    for column in sheet.columns:
        max_len = max(len(str(cell.value or "")) for cell in column)
        sheet.column_dimensions[column[0].column_letter].width = min(max_len + 2, 50)
    workbook.save(output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Funda listings to CSV or Excel")
    parser.add_argument("--location", "-l", required=True, help="City or area")
    parser.add_argument("--output", "-o", required=True, help="Output file (.csv or .xlsx)")
    parser.add_argument("--max-price", type=int, help="Maximum price")
    parser.add_argument("--min-price", type=int, help="Minimum price")
    parser.add_argument("--min-area", type=int, help="Minimum living area")
    parser.add_argument("--category", choices=["buy", "rent", "sold"], default="buy")
    parser.add_argument("--pages", type=int, default=1, help="Number of pages to fetch")
    args = parser.parse_args()

    output = Path(args.output)
    if output.suffix not in {".csv", ".xlsx"}:
        raise SystemExit("Output must be .csv or .xlsx")

    with Funda() as client:
        listings = list(
            client.iter_search(
                args.location,
                category=args.category,
                min_price=args.min_price,
                max_price=args.max_price,
                min_area=args.min_area,
                max_pages=args.pages,
            )
        )

    if not listings:
        raise SystemExit("No listings found")

    rows = [row(listing) for listing in listings]
    if output.suffix == ".csv":
        export_csv(rows, output)
    else:
        export_excel(rows, output)
    print(f"Saved {len(rows)} listings to {output}")


if __name__ == "__main__":
    main()
