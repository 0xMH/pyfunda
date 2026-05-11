# API Guide

This guide explains pyfunda's public API from the user-facing concepts up to
the method reference. You do not need prior knowledge of Funda's internal APIs
to use this library.

Private modules and underscore-prefixed classes are implementation details.

## Core Concepts

### Client

`Funda()` is the client. It owns the network connection settings and exposes
methods such as `search()`, `listing()`, and `autocomplete()`.

Use it as a context manager when possible:

```python
from funda import Funda

with Funda() as client:
    listings = client.search("amsterdam")
```

The `with` block closes network resources automatically when your code leaves
the block.

### Listing

A `Listing` is the Python object pyfunda returns for a home. It has convenient
attributes such as:

```python
listing.title
listing.city
listing.price.amount
listing.living_area
listing.url
```

Most nested data is also modeled as Python objects. For example,
`listing.price.amount` reads the numeric price, while `listing.address.city`
reads the city from the address object.

### Raw Data

pyfunda models stable fields as dataclasses. The original Funda payload is
still available on `listing.raw`.

Use `.raw` when you need a field that pyfunda does not expose as a first-class
attribute yet.

### Listing IDs

Funda has two listing IDs. You usually do not need to know which one you have:
`client.listing(...)` accepts global IDs, tiny IDs, and Funda URLs.

- `globalId`: Funda's internal listing ID
- `tinyId`: the public ID that appears in many Funda URLs

These all work:

```python
client.listing(43117443)
client.listing("7762080")
client.listing("https://www.funda.nl/detail/koop/amsterdam/example/43117443/")
```

### Search Versus Autocomplete

`search()` returns homes.

```python
listings = client.search("amsterdam")
```

`autocomplete()` returns locations that can be used by `search()`. It is useful
when a user types vague text such as `amsterdam west`.

```python
suggestions = client.autocomplete(
    "amsterdam west",
    area_types=["city", "municipality", "neighborhood", "wijk"],
)

selected_location = suggestions[0]
listings = client.search(selected_location.id)
```

Autocomplete does not return houses. It returns `LocationSuggestion` objects.
Use `suggestion.label` for display text and `suggestion.id` as the search
location.

## Common Workflows

| Goal | Use |
| --- | --- |
| I have a Funda URL or ID and want one listing | `client.listing(url_or_id)` |
| I want homes in a city | `client.search("amsterdam")` |
| I want homes near a postcode | `client.search("1012AB", radius_km=10)` |
| I have vague location text from a user | `client.autocomplete(...)`, then `client.search(suggestion.id)` |
| I want more than one page of search results | `client.iter_search(...)` |
| I want contact, broker, market, or similar-listing data | enrichment methods such as `broker_info()` or `similar_listings()` |
| I want the original Funda JSON | `listing.raw` or `listing.to_dict(include_raw=True)` |

## Method Reference

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

Radius search works from a postcode or city:

```python
client.search("1012AB", radius_km=10, max_price=750000)
```

Multiple locations are accepted:

```python
client.search(["amsterdam", "rotterdam", "utrecht"])
```

Search filters:

| pyfunda filter | Funda parameter | Example |
| --- | --- | --- |
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

Valid radius values are 1, 2, 5, 10, 15, 30, and 50 km. Other values are
mapped to the nearest indexed radius.

Sort options:

| Sort Value | Description |
| --- | --- |
| `newest` | Most recently published first |
| `oldest` | Oldest listings first |
| `price_asc` | Lowest price first |
| `price_desc` | Highest price first |
| `area_asc` | Smallest living area first |
| `area_desc` | Largest living area first |
| `plot_desc` | Largest plot area first |
| `city` | Alphabetically by city |
| `postcode` | Alphabetically by postcode |

### `Funda.iter_search(location=None, start_page=0, max_pages=None, workers=1, **filters)`

Iterates search pages until an empty or short page is returned, or until
`max_pages` is reached.

Parallel page fetching requires `max_pages`:

```python
list(client.iter_search("amsterdam", max_pages=4, workers=4))
```

### `Funda.autocomplete(value, size=10, timeout="3s", area_types=None, exclude=None, use_sort=False, sort=None)`

Returns `list[LocationSuggestion]` from Funda's geo search-box endpoint.
Each suggestion's `id` can be passed to `search(location=...)`.

```python
suggestions = client.autocomplete(
    "amsterdam west",
    area_types=["city", "municipality", "neighborhood", "wijk"],
)
listings = client.search(suggestions[0].id)
```

The default `area_types` mirror Funda's broad search box and include streets.
For vague area text, pass area-focused types to avoid street results dominating.

### `Funda.latest_listing_id()`

Returns the highest listing global id visible in the search index.

### `Funda.new_listings(since_id, max_consecutive_404s=20)`

Yields details for newly discoverable global ids after `since_id`.

### `Funda.price_history(listing)`

Returns `PriceHistory` for a `Listing` or Funda URL.

This fetches historical price data for a listing, including previous asking
prices, WOZ tax assessments, and sale history. It calls the Walter Living API
only when explicitly requested.

`PriceHistory.changes` contains `PriceChange` objects:

| Field | Description |
| --- | --- |
| `price` | Numeric price |
| `human_price` | Formatted price, for example `EUR435.000` |
| `date` | Human readable date |
| `timestamp` | ISO timestamp |
| `source` | Data source, such as `Funda` or `WOZ` |
| `status` | `asking_price`, `sold`, or `woz` |

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

Examples:

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

Common grouped fields:

Basic info:

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

Price and status:

```python
listing.price.amount
listing.price.formatted
listing.price.condition
listing.price.is_auction
listing.status
listing.offering_type
```

Property details:

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

Dates:

```python
listing.publication_date
listing.characteristic("Aangeboden sinds")
listing.characteristic("Aanvaarding")
```

Location:

```python
listing.location.coordinates
listing.location.latitude
listing.location.longitude
listing.location.google_maps_url
```

Media:

```python
listing.media.photo_urls
listing.media.photo_count
listing.media.floorplans
listing.media.videos
listing.media.photos_360
listing.media.virtual_tours
listing.media.brochure_url
```

Property features:

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

Stats and metadata:

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

### `LocationSuggestion`

Returned by `Funda.autocomplete()`.

Important fields:

```python
suggestion.id              # Funda selected_area id, usable in search()
suggestion.label           # display label, e.g. "Slotermeer-West, Amsterdam"
suggestion.name
suggestion.area_type
suggestion.geo_identifier
suggestion.parent
suggestion.parent_areas
suggestion.synonyms
suggestion.location.latitude
suggestion.location.longitude
suggestion.score
suggestion.raw
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
