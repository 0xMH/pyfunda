#!/usr/bin/env python3
"""Export Funda search results to CSV or Excel.

Usage:
    # Export to CSV
    uv run examples/export_to_csv.py --location amsterdam --output listings.csv

    # Export to Excel
    uv run examples/export_to_csv.py --location amsterdam --output listings.xlsx

    # With filters
    uv run examples/export_to_csv.py -l amsterdam --max-price 600000 --min-area 60 -o results.csv

    # Multiple pages
    uv run examples/export_to_csv.py -l amsterdam --pages 3 -o all_listings.csv
"""

import argparse
import csv
from pathlib import Path

from funda import Funda

COLUMNS = [
    "title",
    "city",
    "postcode",
    "price",
    "living_area",
    "plot_area",
    "bedrooms",
    "rooms",
    "energy_label",
    "construction_year",
    "object_type",
    "house_type",
    "url",
    "latitude",
    "longitude",
]


def export_csv(listings: list[dict], output: Path) -> None:
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for listing in listings:
            row = {col: listing.get(col, "") for col in COLUMNS}
            writer.writerow(row)


def export_excel(listings: list[dict], output: Path) -> None:
    try:
        import openpyxl
    except ImportError:
        print("Excel export requires openpyxl: uv pip install openpyxl")
        raise SystemExit(1)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Funda Listings"

    # Header
    ws.append(COLUMNS)

    # Data
    for listing in listings:
        row = [listing.get(col, "") for col in COLUMNS]
        ws.append(row)

    # Auto-width columns
    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 50)

    wb.save(output)


def main():
    parser = argparse.ArgumentParser(description="Export Funda listings to CSV/Excel")
    parser.add_argument("--location", "-l", required=True, help="City or area")
    parser.add_argument("--output", "-o", required=True, help="Output file (.csv or .xlsx)")
    parser.add_argument("--max-price", type=int, help="Maximum price")
    parser.add_argument("--min-price", type=int, help="Minimum price")
    parser.add_argument("--min-area", type=int, help="Minimum living area (m²)")
    parser.add_argument("--offering", choices=["buy", "rent"], default="buy")
    parser.add_argument("--pages", type=int, default=1, help="Number of pages to fetch")
    args = parser.parse_args()

    output = Path(args.output)
    if output.suffix not in (".csv", ".xlsx"):
        print("Output must be .csv or .xlsx")
        raise SystemExit(1)

    all_listings = []

    with Funda() as f:
        for page in range(args.pages):
            print(f"Fetching page {page + 1}...")
            results = f.search_listing(
                location=args.location,
                offering_type=args.offering,
                price_min=args.min_price,
                price_max=args.max_price,
                area_min=args.min_area,
                page=page,
            )
            if not results:
                break
            all_listings.extend([r.to_dict() for r in results])

    if not all_listings:
        print("No listings found")
        raise SystemExit(1)

    print(f"Exporting {len(all_listings)} listings...")

    if output.suffix == ".csv":
        export_csv(all_listings, output)
    else:
        export_excel(all_listings, output)

    print(f"Saved to {output}")


if __name__ == "__main__":
    main()
