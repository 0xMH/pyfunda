# Examples

These snippets show common pyfunda workflows. Runnable versions live in
`examples/`.

## Find Apartments In Amsterdam Under EUR400k

```python
from funda import Funda

with Funda() as client:
    results = client.search(
        "amsterdam",
        max_price=400000,
        object_type="apartment",
        sort="newest",
    )

    for listing in results:
        print(listing.title)
        print(f"  Price: {listing.price.formatted or listing.price.amount}")
        print(f"  Area: {listing.living_area or 'N/A'} m2")
        print(f"  Bedrooms: {listing.bedrooms or 'N/A'}")
```

## Autocomplete Then Search

Use autocomplete when user input is vague. For text like `"amsterdam west"`,
limit area types to avoid street-name matches ranking first.

```python
from funda import Funda

with Funda() as client:
    suggestions = client.autocomplete(
        "amsterdam west",
        area_types=["city", "municipality", "neighborhood", "wijk"],
    )

    for suggestion in suggestions:
        print(suggestion.label, suggestion.id, suggestion.area_type)

    listings = client.search(suggestions[0].id, max_price=500000)
    for listing in listings:
        print(listing.title, listing.price.formatted)
```

## Get Detailed Listing Information

```python
from funda import Funda

with Funda() as client:
    listing = client.listing(43117443)

    print(listing)
    print(listing.description)

    for section in listing.characteristics:
        print(section.title)
        for item in section.items:
            print(f"  {item.label}: {item.value}")
```

## Search Rentals In Multiple Cities

```python
from funda import Funda

with Funda() as client:
    results = client.search(
        ["amsterdam", "rotterdam", "den-haag"],
        category="rent",
        max_price=2000,
    )

    print(f"Found {len(results)} rentals")
```

## Find Energy-Efficient Homes With A Garden

```python
from funda import Funda

with Funda() as client:
    listing = client.listing(43117443)
    features = listing.property_details.features

    if features.get("has_garden") and features.get("has_solar_panels"):
        print("Energy efficient with garden")

    if features.get("is_energy_efficient"):
        print(f"Energy label: {listing.energy_label}")
```

## Download Listing Photos

```python
from pathlib import Path

import requests
from funda import Funda

with Funda() as client:
    listing = client.listing(43117443)

for index, url in enumerate(listing.media.photo_urls[:5]):
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    Path(f"photo_{index}.jpg").write_bytes(response.content)
```

## Search By Radius From Postcode

```python
from funda import Funda

with Funda() as client:
    results = client.search(
        "1012AB",
        radius_km=15,
        max_price=600000,
        energy_label=["A", "A+", "A++"],
        sort="newest",
    )

    for listing in results:
        print(listing.title, listing.price.formatted)
```

## Poll For New Listings

Funda's search index can lag behind the actual database. Use `new_listings()`
to find listings that search may not show yet:

```python
from funda import Funda

with Funda() as client:
    latest_id = client.latest_listing_id()

    for listing in client.new_listings(since_id=latest_id):
        print(f"New: {listing.title}, {listing.city}")
        print(f"     {listing.url}")
```

The generator stops after 20 consecutive 404s by default. Change this with
`max_consecutive_404s`.

## Get Price History For A Listing

```python
from funda import Funda

with Funda() as client:
    listing = client.listing(43032486)
    history = client.price_history(listing)

    print(f"Price history for {listing.title}:")
    for change in history.changes:
        print(f"  {change.date}: {change.human_price} ({change.status})")

    funda_prices = [
        change
        for change in history.changes
        if change.source == "Funda" and change.price
    ]
    if len(funda_prices) >= 2:
        newest, oldest = funda_prices[0].price, funda_prices[-1].price
        change_pct = ((newest - oldest) / oldest) * 100
        print(f"Price change: {change_pct:+.1f}%")
```

## Broker Due Diligence

```python
from funda import Funda

with Funda() as client:
    listing = client.listing(43333315)
    broker = client.broker_info(listing)
    reviews = client.broker_reviews(listing)
    handled = client.broker_listings(listing)

    print(broker["name"], broker.get("phone"), broker.get("email"))
    print(f"{reviews.get('average')}/10 over {reviews.get('number_of_reviews')} reviews")
    print(f"{len(handled)} handled listings")
```

## Parallel Batch Details

```python
from funda import Funda

ids = [43117443, 43333315]

with Funda() as client:
    listings = client.listings(ids, workers=4)

for listing in listings:
    print(listing.title, listing.city)
```

## Runnable Examples

Runnable examples live in `examples/`:

| File | Purpose |
| --- | --- |
| `full_api_walkthrough.py` | Small end-to-end walkthrough of the public API |
| `batch_details.py` | Parallel detail fetching for known IDs |
| `broker_due_diligence.py` | Broker profile, reviews, and handled listings |
| `enrichment_export.py` | Export a listing plus enrichment data to JSON |
| `neighborhood_market_snapshot.py` | Compare search sample with local market insights |
| `similar_sales_comp.py` | Build comparable-sales rows from similar sold listings |
| `search_sold.py` | Search sold listings and print summary stats |
| `export_to_csv.py` | Export search results to CSV or XLSX |
| `new_listings_alert.py` | Alert on new listings matching a search |
| `poll_new_listings.py` | Poll by incrementing listing IDs |
| `price_history.py` | Print historical price changes |
| `price_tracker.py` | Persist and track listing price changes |
| `almere_age_rank.py` | Compare construction year distribution |
| `analysis.ipynb` | Pandas analysis notebook |
