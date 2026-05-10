# pyfunda

Python client for Funda.nl real estate data.

pyfunda talks to Funda's app-facing JSON endpoints and returns typed Python
objects instead of browser-scraped HTML. It is designed for scripts, analysis,
alerts, exports, and lightweight enrichment workflows.

## Install

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
    listing = client.listing(43117443)
    print(listing.title, listing.city, listing.price.amount)

    results = client.search("amsterdam", max_price=500000)
    for item in results:
        print(item.title, item.price.amount, item.url)
```

## Core API

### `listing(listing_id)`

Fetch a single listing by global id, tiny id, or Funda URL.

```python
listing = client.listing(43117443)
listing = client.listing("https://www.funda.nl/detail/koop/amsterdam/house/43117443/")
```

### `listings(listing_ids, workers=8)`

Fetch multiple listings concurrently. Order is preserved.

```python
details = client.listings([43117443, 43333315], workers=4)
```

### `search(location=None, **filters)`

Fetch one search page.

```python
results = client.search(
    "amsterdam",
    category="buy",          # buy, rent, sold
    min_price=200000,
    max_price=500000,
    min_area=50,
    min_bedrooms=2,
    object_type="apartment",
    sort="newest",
)
```

### `iter_search(location=None, max_pages=None, workers=1, **filters)`

Iterate across search pages. Set `workers > 1` with `max_pages` for concurrent
page fetching.

```python
for listing in client.iter_search("utrecht", max_pages=5, workers=3):
    print(listing.title)
```

### Search Filters

Supported filters:

| Filter | Description |
| --- | --- |
| `category` | `buy`, `rent`, or `sold` |
| `status` | Availability values such as `available` or `negotiations` |
| `min_price`, `max_price` | Sale or rent price bounds |
| `min_area`, `max_area` | Living area bounds |
| `min_plot`, `max_plot` | Plot area bounds |
| `min_rooms`, `max_rooms` | Total room bounds |
| `min_bedrooms`, `max_bedrooms` | Bedroom bounds |
| `object_type` | `house`, `apartment`, or a sequence |
| `energy_label` | Energy label or sequence |
| `construction_type` | Construction type |
| `min_construction_year`, `max_construction_year` | Construction year bounds |
| `radius_km` | Radius search around exactly one location |
| `sort` | `newest`, `oldest`, `price_asc`, `price_desc`, `area_asc`, `area_desc`, `plot_desc`, `city`, `postcode` |
| `page` | Page number for `search`; use `start_page` for `iter_search` |

## Listing Objects

`Listing` is an immutable dataclass with nested value objects.

```python
listing.title
listing.city
listing.postcode
listing.price.amount
listing.price.formatted
listing.living_area
listing.plot_area
listing.bedrooms
listing.rooms_count
listing.energy_label
listing.status
listing.location.coordinates
listing.media.photo_urls
listing.broker
listing.sales_history
listing.raw
```

Use `to_dict()` when you need serialization:

```python
data = listing.to_dict()
raw_data = listing.to_dict(include_raw=True)
```

## Enrichment API

These methods are lazy and only make extra requests when called.

```python
contact = client.contact_info(listing)
form = client.contact_form(listing)
summary = client.listing_summary(listing)
similar = client.similar_listings(listing)
insights = client.market_insights(listing)
broker = client.broker_info(listing)
broker_listings = client.broker_listings(listing)
reviews = client.broker_reviews(listing)
```

## Price History

```python
history = client.price_history(listing)
for change in history.changes:
    print(change.date, change.human_price, change.status)
```

## New Listing Polling

```python
latest_id = client.latest_listing_id()

for listing in client.new_listings(since_id=latest_id):
    print(listing.title, listing.url)
```

## Performance

Single requests are intentionally sequential:

```python
client.listing(43117443)
client.search("amsterdam")
```

Batch workflows can use parallel fetching:

```python
client.listings(ids, workers=4)
list(client.iter_search("amsterdam", max_pages=4, workers=4))
```

The client keeps a reusable per-thread worker pool for repeated batch calls and
caches the last working TLS fingerprint internally.

## Examples

Runnable examples live in `examples/`:

| File | Purpose |
| --- | --- |
| `full_api_walkthrough.py` | Small end-to-end walkthrough of the public API |
| `batch_details.py` | Parallel detail fetching for known ids |
| `broker_due_diligence.py` | Broker profile, reviews, and handled listings |
| `enrichment_export.py` | Export a listing plus enrichment data to JSON |
| `neighborhood_market_snapshot.py` | Compare search sample with local market insights |
| `similar_sales_comp.py` | Build comparable-sales rows from similar sold listings |
| `search_sold.py` | Search sold listings and print summary stats |
| `export_to_csv.py` | Export search results to CSV or XLSX |
| `new_listings_alert.py` | Alert on new listings matching a search |
| `poll_new_listings.py` | Poll by incrementing listing ids |
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

Live tests intentionally stay small: they verify listing, search, parallel
fetching, and enrichment endpoints without sweeping large result sets.

## More Documentation

- [API reference](docs/API.md)
- [Development and testing](docs/DEVELOPMENT.md)
