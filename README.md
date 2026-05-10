# pyfunda

[![PyPI version](https://img.shields.io/pypi/v/pyfunda)](https://pypi.org/project/pyfunda/)
[![Python versions](https://img.shields.io/pypi/pyversions/pyfunda)](https://pypi.org/project/pyfunda/)
[![License](https://img.shields.io/pypi/l/pyfunda)](https://github.com/0xMH/pyfunda/blob/main/LICENSE)

The only working real Python API for Funda ([funda.nl](https://www.funda.nl)) -- the Netherlands' largest real estate platform.

> If you find this useful, consider giving it a star -- it helps others discover the project.

[![Star History Chart](https://api.star-history.com/svg?repos=0xMH/pyfunda&type=Date)](https://star-history.com/#0xMH/pyfunda&Date)

## Why I'm open-sourcing this?

After pyfunda, I got messages asking why I'd give this away when aggregators will just take it and sell it. They're right, every week there's a new "revolutionary AI-powered housing finder" charging EUR40/month or a EUR250 "success fee." They all pull from the same one or two sources and wrap it in a fancy UI completely built with AI.

That's exactly why I'm open-sourcing it.

These services are selling air to people who are looking for any kind of hope. The data is public. The APIs aren't hard to figure out. You shouldn't have to pay someone to refresh a webpage for you. Funda could kill this entire market overnight by offering a public API. They don't, so here we are.

Here's the code, do it yourself. Send my library link to any AI service you use and ask it to build whatever tool you think will make your life easier while searching for your next home.

With pyfunda, I've already done all the heavy lifting for you.

## Why pyfunda?

**Because it simply works.**

Funda has no public developer API. If you want Dutch real estate data programmatically, your options are limited:

| Library | Approach | Limitations |
|---------|----------|-------------|
| [whchien/funda-scraper](https://github.com/whchien/funda-scraper) | HTML scraping | Listing dates blocked since Q4 2023 (requires login). Breaks when Funda changes frontend. |
| [khpeek/funda-scraper](https://github.com/khpeek/funda-scraper) | Scrapy | Last updated 2016. No longer maintained. |
| [joostboon/Funda-Scraper](https://github.com/joostboon/Funda-Scraper) | Selenium | Requires manual CAPTCHA solving. Slow browser automation. |
| **Official API** | Broker API | Only available to registered brokers. Not accessible to regular developers. |

**pyfunda takes a different approach:** it uses Funda's app-facing JSON APIs instead of scraping browser HTML.

- Pure Python, no browser or Selenium needed
- No manual CAPTCHA solving
- Typed Python objects for listings, prices, media, brokers, coordinates, and history
- Search, listing detail, enrichment, broker, price-history, polling, and parallel batch workflows
- Raw Funda payloads are still available when you need fields that pyfunda does not model yet

## Installation

```bash
pip install pyfunda
```

For local development:

```bash
uv sync
uv run python -m unittest discover -s tests
```

## Quick Start

```python
from funda import Funda

with Funda() as client:
    # Get a listing by global id, tiny id, or Funda URL
    listing = client.listing(43117443)
    print(listing.title, listing.city, listing.price.amount)

    # Search listings
    results = client.search("amsterdam", max_price=500000)
    for item in results:
        print(item.title, item.price.amount, item.url)
```

## How It Works

This library uses Funda's undocumented app-facing APIs, which provide clean JSON responses unlike the website that embeds data in Nuxt.js/JavaScript bundles.

### Discovery Process

The original API was reverse engineered by intercepting and analyzing HTTPS traffic from the official Funda Android app:

1. Configured an Android device to route traffic through an intercepting proxy
2. Used the Funda app normally - browsing listings, searching, opening shared URLs
3. Identified the `*.funda.io` API infrastructure separate from the `www.funda.nl` website
4. Analyzed request/response patterns to understand the query format and available filters
5. Discovered how the app resolves URL-based IDs (`tinyId`) to internal IDs (`globalId`)

### API Architecture

The app-facing APIs live across several `*.funda.io` services:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `listing-detail-page.funda.io/api/v4/listing/object/nl/{globalId}` | GET | Fetch listing by internal ID |
| `listing-detail-page.funda.io/api/v4/listing/object/nl/tinyId/{tinyId}` | GET | Fetch listing by URL ID |
| `listing-search-wonen.funda.io/_msearch/template` | POST | Search listings |
| `listing-detail-summary.funda.io/api/v1/listing/nl/{globalId}` | GET | Fetch lightweight listing summary |
| `contacts-flows-bff.funda.io/.../contact-block` | GET | Fetch realtor contact block |
| `contacts-bff.funda.io/.../contact-form` | GET | Fetch contact-form availability |
| `local-listings.funda.io/api/v1/similarlistings` | GET | Fetch similar and recently sold listing IDs |
| `marketinsights.funda.io/v2/localinsights/preview/...` | GET | Fetch neighbourhood market insights |
| `brokerpresentation-office-pages-bff.funda.io/.../office-page/...` | GET | Fetch broker profile and listings |
| `reviews-office-pages-bff.funda.io/.../reviews/nl` | GET | Fetch broker review aggregates |
| `api.walterliving.com/hunter/lookup` | POST | Fetch price history data |

The request transport, headers, retry profiles, and TLS fingerprint rotation are internal implementation details. Normal users only construct `Funda()` and call the public methods below.

### ID System

Funda uses two ID systems:

- **globalId**: Internal numeric ID, used by the listing-detail API
- **tinyId**: Public-facing ID, appears in URLs like `funda.nl/detail/koop/amsterdam/.../{tinyId}/`

The `tinyId` endpoint allows fetching any listing directly from a Funda URL without first knowing the internal ID.

### Search API

Search uses Elasticsearch's [Multi Search Template API](https://www.elastic.co/guide/en/elasticsearch/reference/current/multi-search-template.html) with NDJSON format:

```json
{"index":"listings-wonen-searcher-alias-prod"}
{"id":"search_result_20250805","params":{...}}
```

Search results are paginated with 15 listings per page.

**Search parameters pyfunda models:**

| pyfunda filter | Funda parameter | Example |
|----------------|-----------------|---------|
| `location` | `selected_area` | `["amsterdam"]` |
| `radius_km` | `radius_search` | `{"id": "1012ab-0", "path": "area_with_radius.10"}` |
| `category` | `offering_type` / `availability` | `"buy"`, `"rent"`, or `"sold"` |
| `min_price`, `max_price` | `price.selling_price` or `price.rent_price` | `{"from": 200000, "to": 500000}` |
| `min_area`, `max_area` | `floor_area` | `{"from": 50, "to": 150}` |
| `min_plot`, `max_plot` | `plot_area` | `{"from": 100, "to": 500}` |
| `min_rooms`, `max_rooms` | `rooms` | `{"from": 3}` |
| `min_bedrooms`, `max_bedrooms` | `bedrooms` | `{"from": 2}` |
| `object_type` | `object_type` | `["house", "apartment"]` |
| `energy_label` | `energy_label` | `["A", "A+"]` |
| `construction_type` | `construction_type` | `"existing"` |
| `min_construction_year`, `max_construction_year` | `construction_period` | `from_1991_to_2000` |
| `sort` | `sort` | `{"field": "publish_date_utc", "order": "desc"}` |
| `page` | `page.from` | `0`, `15`, `30`... |

**Valid radius values:** 1, 2, 5, 10, 15, 30, 50 km. Other values are mapped to the nearest indexed radius because those are the only radius buckets Funda exposes.

### Response Data

Listing responses include:

- **Identifiers** - globalId, tinyId
- **AddressDetails** - title, city, postcode, province, neighbourhood, house number
- **Price** - numeric and formatted prices, sale/rent metadata, auction flag
- **FastView** - bedrooms, living area, plot area, energy label
- **Media** - photos, floorplans, videos, 360 photos, virtual tours, brochure URL
- **KenmerkSections** - detailed property characteristics
- **Coordinates** - latitude/longitude
- **ObjectInsights** - view and save counts
- **Advertising.TargetingOptions** - boolean features, construction year, room counts
- **Share** - shareable URL
- **GoogleMapsObjectUrl** - direct Google Maps link
- **PublicationDate** - when the listing was published
- **Tracking.Values.brokers** - broker ID and association

pyfunda models the common stable fields as dataclasses and keeps the full original payload on `listing.raw`.

## API Reference

### Funda

Main entry point for the API.

```python
from funda import Funda

client = Funda(timeout=30, max_retries=5, retry_backoff=0.1)
```

Use the client as a context manager when possible:

```python
with Funda() as client:
    listing = client.listing(43117443)
```

### `listing(listing_id)`

Get a single listing by global ID, tiny ID, or Funda URL.

```python
listing = client.listing(43117443)
listing = client.listing("https://www.funda.nl/detail/koop/city/house-name/43117443/")
```

Raises `ListingNotFound` for missing listings and `FundaRequestError` for transport rejection or unexpected HTTP status.

### `listings(listing_ids, workers=8)`

Fetch many listings concurrently. Output order matches input order.

```python
details = client.listings([43117443, 43333315], workers=4)
for listing in details:
    print(listing.title)
```

Use `listing()` for one listing and `listings()` for batches.

### `search(location=None, **filters)`

Fetch one search page.

```python
results = client.search(
    "amsterdam",
    category="buy",          # buy, rent, sold
    min_price=200000,
    max_price=500000,
    min_area=50,
    max_area=150,
    min_plot=100,
    max_plot=500,
    min_bedrooms=2,
    object_type=["house", "apartment"],
    energy_label=["A", "A+"],
    construction_type="existing",
    sort="newest",
    page=0,
)
```

**Radius search** - search within a radius from a postcode or city:

```python
results = client.search(
    "1012AB",
    radius_km=10,
    max_price=750000,
)
```

**Multiple locations:**

```python
results = client.search(["amsterdam", "rotterdam", "utrecht"])
```

**Sort options:**

| Sort Value | Description |
|------------|-------------|
| `newest` | Most recently published first |
| `oldest` | Oldest listings first |
| `price_asc` | Lowest price first |
| `price_desc` | Highest price first |
| `area_asc` | Smallest living area first |
| `area_desc` | Largest living area first |
| `plot_desc` | Largest plot area first |
| `city` | Alphabetically by city |
| `postcode` | Alphabetically by postcode |

### `iter_search(location=None, start_page=0, max_pages=None, workers=1, **filters)`

Iterate across search pages. Set `workers > 1` with `max_pages` for concurrent page fetching.

```python
for listing in client.iter_search("utrecht", max_pages=5, workers=3):
    print(listing.title)
```

### `latest_listing_id()`

Get the highest listing ID currently visible in Funda's search index.

```python
latest = client.latest_listing_id()
```

### `new_listings(since_id, max_consecutive_404s=20)`

Generator that polls for new listings by incrementing global IDs.

```python
for listing in client.new_listings(since_id=latest):
    print("New:", listing.title, listing.url)
```

This bypasses search and queries the detail API directly, catching listings that may not be indexed yet.

### `price_history(listing)`

Get historical price data for a listing, including previous asking prices, WOZ tax assessments, and sale history.

```python
listing = client.listing(43032486)
history = client.price_history(listing)

for change in history.changes:
    print(change.date, change.human_price, change.status)
```

**Returns:** `PriceHistory` with `changes`, where each `PriceChange` contains:

| Field | Description |
|-------|-------------|
| `price` | Numeric price |
| `human_price` | Formatted price, for example `EUR435.000` |
| `date` | Human readable date |
| `timestamp` | ISO timestamp |
| `source` | Data source, such as `Funda` or `WOZ` |
| `status` | `asking_price`, `sold`, or `woz` |

> **Note:** This fetches data from the Walter Living API. It is only called when explicitly requested.

### Enrichment methods

These methods are lazy and only make extra requests when called. They accept a `Listing`, numeric ID, or Funda URL unless noted otherwise.

| Method | Purpose |
|--------|---------|
| `contact_info(listing)` | Realtor/makelaar agency name, phone, office ID, association, and contact metadata |
| `contact_form(listing)` | Contact-form availability, office, weekdays, and times of day |
| `listing_summary(listing)` | Lightweight listing summary without the full detail payload |
| `similar_listings(listing)` | Recently listed and recently sold global IDs near a listing |
| `market_insights(city, neighbourhood=None)` | Neighbourhood demographics and asking price per m2; also accepts a `Listing` |
| `broker_info(broker)` | Broker profile: phone, email, website, address, services, certificates |
| `broker_listings(broker)` | Listings handled by a broker, tagged by status |
| `broker_reviews(broker)` | Review aggregate scores and recent review examples |

```python
contact = client.contact_info(listing)
form = client.contact_form(listing)
summary = client.listing_summary(listing)
similar = client.similar_listings(listing)
insights = client.market_insights(listing)
broker = client.broker_info(listing)
handled = client.broker_listings(listing)
reviews = client.broker_reviews(listing)
```

## Listing Objects

`Listing` is an immutable dataclass with nested value objects. Prefer attributes over dict indexing.

**Basic info:**

```python
listing.title
listing.city
listing.postcode
listing.address.province
listing.address.neighbourhood
listing.address.municipality
listing.address.house_number
listing.address.house_number_suffix
```

**Price & status:**

```python
listing.price.amount
listing.price.formatted
listing.price.condition
listing.price.is_auction
listing.status
listing.offering_type
```

**Property details:**

```python
listing.property_details.object_type
listing.property_details.house_type
listing.property_details.construction_type
listing.property_details.construction_year
listing.bedrooms
listing.rooms_count
listing.living_area
listing.plot_area
listing.energy_label
listing.description
```

**Dates:**

```python
listing.publication_date
listing.characteristic("Aangeboden sinds")
listing.characteristic("Aanvaarding")
```

**Location:**

```python
listing.location.coordinates
listing.location.latitude
listing.location.longitude
listing.location.google_maps_url
```

**Media:**

```python
listing.media.photo_urls
listing.media.photo_count
listing.media.floorplans
listing.media.videos
listing.media.photos_360
listing.media.virtual_tours
listing.media.brochure_url
```

**Property features:**

```python
features = listing.property_details.features
features["has_garden"]
features["has_balcony"]
features["has_roof_terrace"]
features["has_solar_panels"]
features["has_heat_pump"]
features["has_parking_on_site"]
features["has_parking_enclosed"]
features["is_energy_efficient"]
features["is_monument"]
features["is_fixer_upper"]
```

**Stats & metadata:**

```python
listing.insights.views if listing.insights else None
listing.insights.saves if listing.insights else None
listing.highlight
listing.global_id
listing.tiny_id
listing.url
listing.urls.share
listing.broker
listing.characteristics
listing.sales_history
listing.raw
```

**Serialization:**

```python
data = listing.to_dict()
raw_data = listing.to_dict(include_raw=True)
```

## Examples

### Find apartments in Amsterdam under EUR400k

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

### Get detailed listing information

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

### Search rentals in multiple cities

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

### Find energy-efficient homes with a garden

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

### Download listing photos

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

### Search by radius from postcode

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

### Poll for new listings

Funda's search index can lag behind the actual database. Use `new_listings()` to find listings that search may not show yet:

```python
from funda import Funda

with Funda() as client:
    latest_id = client.latest_listing_id()

    for listing in client.new_listings(since_id=latest_id):
        print(f"New: {listing.title}, {listing.city}")
        print(f"     {listing.url}")
```

The generator stops after 20 consecutive 404s by default. Change this with `max_consecutive_404s`.

### Get price history for a listing

```python
from funda import Funda

with Funda() as client:
    listing = client.listing(43032486)
    history = client.price_history(listing)

    print(f"Price history for {listing.title}:")
    for change in history.changes:
        print(f"  {change.date}: {change.human_price} ({change.status})")

    funda_prices = [change for change in history.changes if change.source == "Funda" and change.price]
    if len(funda_prices) >= 2:
        newest, oldest = funda_prices[0].price, funda_prices[-1].price
        change_pct = ((newest - oldest) / oldest) * 100
        print(f"Price change: {change_pct:+.1f}%")
```

### Broker due diligence

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

### Parallel batch details

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

## Tests

Fast local tests:

```bash
uv run python -m unittest discover -s tests
```

Live Funda smoke tests:

```bash
PYFUNDA_LIVE=1 uv run python -m unittest tests.test_live -v
```

Live tests verify listing, search, parallel fetching, and enrichment endpoints.

## More Documentation

- [API reference](docs/API.md)
- [Development and testing](docs/DEVELOPMENT.md)

## Disclaimer

This is an unofficial library and is not affiliated with, authorized, maintained, sponsored, or endorsed by Funda or any of its affiliates. Use at your own risk.

This library only accesses publicly available listing data through Funda's undocumented internal APIs. Using this library may violate Funda's Terms of Service. The authors are not responsible for any consequences of using this software.

This project is intended for personal use, research, and educational purposes only.

- The APIs are undocumented and may change or break at any time without notice.
- Please use this library responsibly and avoid excessive requests that could burden Funda's infrastructure.
- Data may be subject to copyright and usage restrictions. Ensure your use complies with applicable laws.

## License

AGPL-3.0
