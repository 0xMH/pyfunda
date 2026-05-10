#!/usr/bin/env python3
"""Rank a house's construction year against the local for-sale stock.

For each Funda construction-period bucket, this sweeps active for-sale listings
in a city, tags every hit with its wijk, and builds a wijk x period
distribution. Given a subject listing URL or ID, it reports where the subject
falls in its wijk's age distribution and city-wide.

Defaults to Almere; pass --location to use a different city.

Usage:
    # Print the wijk x period distribution for Almere
    uv run examples/almere_age_rank.py

    # Rank a specific listing within its wijk and city
    uv run examples/almere_age_rank.py --listing https://www.funda.nl/detail/koop/almere/huis-andantestraat-5/43332850/

    # By Funda URL ID
    uv run examples/almere_age_rank.py --listing 43332850
"""

import argparse
import re
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Iterable

from funda import CONSTRUCTION_PERIODS, ConstructionPeriod, Funda, Listing

DEFAULT_REQUEST_DELAY_S = 1.0
PAGE_SIZE = 15


def parse_listing_arg(arg: str) -> int:
    """Accept a Funda URL or a bare listing ID."""
    match = re.search(r"/(\d{7,9})(?:/|\?|#|$)", arg)
    if match:
        return int(match.group(1))
    return int(arg)


def period_for_year(year: int) -> ConstructionPeriod | None:
    """Return the construction period for a year."""
    for period in CONSTRUCTION_PERIODS:
        if period.year_min <= year <= period.year_max:
            return period
    return None


def period_labels() -> list[str]:
    return [period.label for period in CONSTRUCTION_PERIODS]


def period_search_kwargs(period: ConstructionPeriod) -> dict[str, int]:
    """Convert a construction period into search filter kwargs."""
    kwargs: dict[str, int] = {}
    if period.year_min > 0:
        kwargs["min_construction_year"] = period.year_min
    if period.year_max < 9999:
        kwargs["max_construction_year"] = period.year_max
    return kwargs


def search_period_pages(
    f: Funda,
    location: str,
    period: ConstructionPeriod,
    *,
    delay_s: float,
    max_pages: int | None,
) -> Iterable[list[Listing]]:
    """Yield pages of active listings for one construction period."""
    page = 0
    while max_pages is None or page < max_pages:
        if delay_s > 0:
            time.sleep(delay_s)
        results = f.search(
            location=location,
            page=page,
            **period_search_kwargs(period),
        )
        if not results:
            break
        yield results
        if len(results) < PAGE_SIZE:
            break
        page += 1


def sweep_population(
    f: Funda,
    location: str,
    *,
    delay_s: float,
    max_pages: int | None,
) -> dict[str, Counter[str]]:
    """Sweep active for-sale listings filtered by each construction bucket."""
    counts: dict[str, Counter[str]] = defaultdict(Counter)

    for period in CONSTRUCTION_PERIODS:
        period_total = 0
        for results in search_period_pages(f, location, period, delay_s=delay_s, max_pages=max_pages):
            for listing in results:
                wijk = listing.address.neighbourhood or "(unknown)"
                counts[wijk][period.label] += 1
                period_total += 1
        sys.stderr.write(f"  {period.label}: {period_total} listings\n")

    return dict(counts)


def listing_ids(listing: Listing) -> set[str]:
    return {
        str(value)
        for value in (listing.global_id, listing.tiny_id, listing.id)
        if value is not None
    }


def print_distribution_table(counts: dict[str, Counter[str]]) -> None:
    labels = period_labels()
    wijken = sorted(counts, key=lambda wijk: -sum(counts[wijk].values()))

    name_w = max(len("wijk"), max((len(wijk) for wijk in wijken), default=0))
    col_w = 9
    header = f"{'wijk'.ljust(name_w)}  " + "  ".join(label.rjust(col_w) for label in labels)
    header += f"  {'total'.rjust(7)}"
    print(header)
    print("-" * len(header))

    for wijk in wijken:
        total = sum(counts[wijk].values())
        row = f"{wijk.ljust(name_w)}  "
        row += "  ".join(str(counts[wijk].get(label, 0)).rjust(col_w) for label in labels)
        row += f"  {str(total).rjust(7)}"
        print(row)

    totals = Counter()
    for counter in counts.values():
        totals.update(counter)
    grand = sum(totals.values())

    print("-" * len(header))
    foot = f"{'total'.ljust(name_w)}  " + "  ".join(str(totals.get(label, 0)).rjust(col_w) for label in labels)
    foot += f"  {str(grand).rjust(7)}"
    print(foot)


def describe_rank(counter: Counter[str], subject_year: int, subject_label: str, label: str) -> None:
    labels = period_labels()
    total = sum(counter.values())
    if total == 0:
        print(f"  Within {label}: no active listings found.")
        return

    idx = labels.index(subject_label)
    older = sum(counter[p] for p in labels[:idx])
    same = counter[subject_label]
    newer = sum(counter[p] for p in labels[idx + 1:])
    side = "older" if older < newer else "newer" if newer < older else "middle"

    print(f"  Within {label} ({total} active listings):")
    print(f"    {100 * older / total:5.1f}% older than the subject bucket")
    print(f"    {100 * same / total:5.1f}% in the subject bucket ({subject_label})")
    print(f"    {100 * newer / total:5.1f}% newer than the subject bucket")
    print(f"    -> built {subject_year} sits on the {side} side of this stock")


def find_subject_wijk_from_search(
    f: Funda,
    location: str,
    subject_ids: set[str],
    *,
    max_pages: int | None,
) -> str | None:
    """Resolve wijk from search results when the detail endpoint only has buurt."""
    probe_max_pages = max_pages if max_pages is not None else 20
    for listing in f.iter_search(location, max_pages=probe_max_pages):
        if str(listing.global_id) in subject_ids or str(listing.id) in subject_ids:
            return listing.address.neighbourhood
    return None


def rank_subject(
    counts: dict[str, Counter[str]],
    subject_year: int,
    subject_label: str,
    subject_wijk: str | None,
) -> None:
    city_counter = Counter()
    for counter in counts.values():
        city_counter.update(counter)

    print()
    print(f"Subject: built {subject_year}, bucket = {subject_label}")
    print()

    if subject_wijk and subject_wijk in counts:
        describe_rank(counts[subject_wijk], subject_year, subject_label, f"wijk {subject_wijk}")
        print()
    elif subject_wijk:
        print(f"  Wijk {subject_wijk!r} was not present in the swept active stock.")
        print()
    else:
        print("  Could not resolve the subject wijk from detail or search results.")
        print()

    describe_rank(city_counter, subject_year, subject_label, "city")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--location", default="almere", help="City to sweep (default: almere)")
    parser.add_argument("--listing", help="Funda URL or listing ID of the subject")
    parser.add_argument("--no-table", action="store_true", help="Skip the wijk x period table")
    parser.add_argument("--delay", type=float, default=DEFAULT_REQUEST_DELAY_S, help="Delay between search pages")
    parser.add_argument("--max-pages", type=int, help="Limit pages per construction bucket")
    args = parser.parse_args()

    with Funda() as f:
        subject = None
        subject_wijk = None
        subject_ids: set[str] = set()
        if args.listing:
            subject_id = parse_listing_arg(args.listing)
            sys.stderr.write(f"Fetching subject listing {subject_id}...\n")
            subject = f.listing(subject_id)
            if not subject.property_details.construction_year:
                print(
                    f"Could not read construction_year from listing {subject_id}.",
                    file=sys.stderr,
                )
                sys.exit(1)
            subject_ids = listing_ids(subject)
            subject_wijk = subject.address.neighbourhood

        sys.stderr.write(f"Sweeping {args.location} listings by construction period...\n")
        counts = sweep_population(f, args.location, delay_s=args.delay, max_pages=args.max_pages)
        if subject is not None and (not subject_wijk or subject_wijk not in counts):
            subject_wijk = (
                find_subject_wijk_from_search(
                    f,
                    args.location,
                    subject_ids,
                    max_pages=args.max_pages,
                )
                or subject_wijk
            )

    if not args.no_table:
        print_distribution_table(counts)

    if subject is not None:
        subject_year = subject.property_details.construction_year
        period = period_for_year(subject_year)
        if period is None:
            print(f"Year {subject_year} did not map to any construction period.", file=sys.stderr)
            sys.exit(1)
        rank_subject(counts, subject_year, period.label, subject_wijk)


if __name__ == "__main__":
    main()
