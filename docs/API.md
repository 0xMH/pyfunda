# API Reference

This is the public pyfunda API as of the current redesign. Private modules and
underscore-prefixed classes are implementation details.

## Client

```python
from funda import Funda

client = Funda(timeout=30, max_retries=5, retry_backoff=0.1)
```

Use the client as a context manager when possible:

```python
with Funda() as client:
    listing = client.listing(43117443)
```

### `Funda.listing(listing_id)`

Returns a `Listing`.

`listing_id` may be:

- a global id
- a tiny id
- a Funda detail URL
- an older Funda slug URL containing a 7-9 digit id

Raises:

- `ListingNotFound` for `404`
- `FundaRequestError` for transport rejection or unexpected HTTP status
- `ValueError` for invalid ids or URLs

### `Funda.listings(listing_ids, workers=8)`

Fetches details for many listing ids concurrently and returns `list[Listing]`.
The output order matches the input order.

Use this for batches. For one listing, use `listing()`.

### `Funda.search(location=None, **filters)`

Fetches one search page and returns `list[Listing]`.

Common filters:

```python
client.search(
    "amsterdam",
    category="buy",
    min_price=200000,
    max_price=500000,
    min_area=50,
    max_area=120,
    min_plot=100,
    max_plot=500,
    min_rooms=3,
    max_rooms=6,
    min_bedrooms=2,
    max_bedrooms=4,
    object_type=["house", "apartment"],
    energy_label=["A", "A+"],
    construction_type="existing",
    min_construction_year=1990,
    max_construction_year=2020,
    radius_km=10,
    sort="newest",
    page=0,
)
```

Valid categories are `buy`, `rent`, and `sold`.

### `Funda.iter_search(location=None, start_page=0, max_pages=None, workers=1, **filters)`

Iterates search pages until an empty or short page is returned, or until
`max_pages` is reached.

Parallel page fetching requires `max_pages`:

```python
list(client.iter_search("amsterdam", max_pages=4, workers=4))
```

### `Funda.latest_listing_id()`

Returns the highest listing global id visible in the search index.

### `Funda.new_listings(since_id, max_consecutive_404s=20)`

Yields details for newly discoverable global ids after `since_id`.

### `Funda.price_history(listing)`

Returns `PriceHistory` for a `Listing` or Funda URL.

### Enrichment Methods

These methods return extra data from auxiliary Funda endpoints:

| Method | Return |
| --- | --- |
| `contact_info(listing)` | `dict` with primary broker/contact fields |
| `contact_form(listing)` | `dict` with contact form availability |
| `listing_summary(listing)` | lightweight `Listing` |
| `similar_listings(listing)` | `dict` with recently listed/sold global ids |
| `market_insights(city, neighbourhood=None)` | `dict` with local market fields |
| `broker_info(broker)` | `dict` with broker profile fields |
| `broker_listings(broker)` | `list[dict]` of broker listings |
| `broker_reviews(broker)` | `dict` with aggregate and recent reviews |

`listing` arguments accept a `Listing`, a global id, a tiny id, or a Funda URL.
`broker` arguments accept a `Listing` with broker data or a broker id.

## Models

### `Listing`

`Listing` is frozen and slot-based. Prefer attributes over dict indexing.

Important fields:

```python
listing.id
listing.global_id
listing.tiny_id
listing.source
listing.offering_type
listing.address
listing.price
listing.areas
listing.rooms
listing.property_details
listing.location
listing.urls
listing.media
listing.brokers
listing.labels
listing.description
listing.characteristics
listing.sales_history
listing.parent_project
listing.insights
listing.raw
```

Convenience properties:

```python
listing.title
listing.city
listing.postcode
listing.url
listing.detail_url
listing.broker
listing.living_area
listing.plot_area
listing.rooms_count
listing.bedrooms
listing.energy_label
listing.status
```

Use:

```python
listing.characteristic("Bouwjaar")
listing.to_dict()
listing.to_dict(include_raw=True)
```

### Nested Value Objects

The main nested dataclasses are:

- `Address`
- `Price`
- `Areas`
- `Rooms`
- `PropertyDetails`
- `GeoLocation`
- `Urls`
- `Media`
- `MediaItem`
- `Broker`
- `SalesHistory`
- `Project`
- `Insights`
- `PriceHistory`
- `PriceChange`

Each supports `to_dict(include_raw=False)`.

## Exceptions

```python
from funda import (
    FundaError,
    FundaRequestError,
    FingerprintError,
    ListingNotFound,
    PriceHistoryError,
    SearchError,
)
```

Use `FundaError` to catch any pyfunda-specific error.
