# pyfunda

[![PyPI version](https://img.shields.io/pypi/v/pyfunda)](https://pypi.org/project/pyfunda/)
[![Python versions](https://img.shields.io/pypi/pyversions/pyfunda)](https://pypi.org/project/pyfunda/)
[![License](https://img.shields.io/pypi/l/pyfunda)](https://github.com/0xMH/pyfunda/blob/main/LICENSE)

The only working real Python API for Funda ([funda.nl](https://www.funda.nl)) — the Netherlands' largest real estate platform.

> If you find this useful, consider giving it a star — it helps others discover the project.

[![Star History Chart](https://api.star-history.com/svg?repos=0xMH/pyfunda&type=Date)](https://star-history.com/#0xMH/pyfunda&Date)

## Why I'm open-sourcing this?

After pyfunda, I got messages asking why I'd give this away when aggregators will just take it and sell it. They're right, every week there's a new "revolutionary AI-powered housing finder" charging €40/month or a €250 "success fee.". They all pull from the same one or two sources and wrap it in a fancy UI completely built with AI.

That's exactly why I'm open-sourcing it.

These services are selling air to people who are looking for any kind of hope. The data is public. The APIs aren't hard to figure out. You shouldn't have to pay someone to refresh a webpage for you. Funda could kill this entire market overnight by offering a public API. They don't, so here we are.

Here's the code, do it yourself. Send my library link to any AI service you use and ask it to build whatever tool you think will make your life easier while searching for your next home.

With pyfunda, I've already done all the heavy lifting for you.

## Why pyfunda?

**Because it simply works.**

Funda has no public API. If you want Dutch real estate data programmatically, your options are limited:

| Library | Approach | Limitations |
|---------|----------|-------------|
| [whchien/funda-scraper](https://github.com/whchien/funda-scraper) | HTML scraping | Listing dates blocked since Q4 2023 (requires login). Breaks when Funda changes frontend. |
| [khpeek/funda-scraper](https://github.com/khpeek/funda-scraper) | Scrapy | Last updated 2016. No longer maintained. |
| [joostboon/Funda-Scraper](https://github.com/joostboon/Funda-Scraper) | Selenium | Requires manual CAPTCHA solving. Slow browser automation. |
| **Official API** | — | Only available to registered brokers. Not accessible to developers. |

**pyfunda takes a different approach:** it uses Funda's internal mobile app API, reverse-engineered from the official Android app.

- Pure Python, no browser or Selenium needed
- No CAPTCHAs or anti-bot blocks
- 70+ fields including photos, floorplans, coordinates, and listing dates
- Stable mobile API that doesn't break when the website changes

## Installation

```bash
pip install pyfunda
```

## Quick Start

```python
from funda import Funda

f = Funda()

# Get a listing by ID
listing = f.get_listing(43117443)
print(listing['title'], listing['city'])
# Reehorst 13 Luttenberg

# Get a listing by URL
listing = f.get_listing('https://www.funda.nl/detail/koop/amsterdam/appartement-123/43117443/')

# Search listings
results = f.search_listing('amsterdam', price_max=500000)
for r in results:
    print(r['title'], r['price'])
```

## How It Works

This library uses Funda's undocumented mobile app API, which provides clean JSON responses unlike the website that embeds data in Nuxt.js/JavaScript bundles.

### Discovery Process

The API was reverse engineered by intercepting and analyzing HTTPS traffic from the official Funda Android app:

1. Configured an Android device to route traffic through an intercepting proxy
2. Used the Funda app normally - browsing listings, searching, opening shared URLs
3. Identified the `*.funda.io` API infrastructure separate from the `www.funda.nl` website
4. Analyzed request/response patterns to understand the query format and available filters
5. Discovered how the app resolves URL-based IDs (`tinyId`) to internal IDs (`globalId`)

### API Architecture

The mobile app communicates with a separate API at `*.funda.io`:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `listing-detail-page.funda.io/api/v4/listing/object/nl/{globalId}` | GET | Fetch listing by internal ID |
| `listing-detail-page.funda.io/api/v4/listing/object/nl/tinyId/{tinyId}` | GET | Fetch listing by URL ID |
| `listing-search-wonen.funda.io/_msearch/template` | POST | Search listings |

### ID System

Funda uses two ID systems:
- **globalId**: Internal numeric ID (7 digits), used in the database
- **tinyId**: Public-facing ID (8-9 digits), appears in URLs like `funda.nl/detail/koop/amsterdam/.../{tinyId}/`

The `tinyId` endpoint was key - it allows fetching any listing directly from a Funda URL without needing to know the internal ID.

### Search API

Search uses Elasticsearch's [Multi Search Template API](https://www.elastic.co/guide/en/elasticsearch/reference/current/multi-search-template.html) with NDJSON format:

```
{"index":"listings-wonen-searcher-alias-prod"}
{"id":"search_result_20250805","params":{...}}
```

**Search parameters:**

| Parameter | Description | Example |
|-----------|-------------|---------|
| `selected_area` | Location filter | `["amsterdam"]` |
| `radius_search` | Radius from location | `{"index": "geo-wonen-alias-prod", "id": "1012AB-0", "path": "area_with_radius.10"}` |
| `offering_type` | Buy or rent | `"buy"` or `"rent"` |
| `price.selling_price` | Price range (buy) | `{"from": 200000, "to": 500000}` |
| `price.rent_price` | Price range (rent) | `{"from": 500, "to": 2000}` |
| `object_type` | Property types | `["house", "apartment"]` |
| `floor_area` | Living area m² | `{"from": 50, "to": 150}` |
| `plot_area` | Plot area m² | `{"from": 100, "to": 500}` |
| `energy_label` | Energy labels | `["A", "A+", "A++"]` |
| `sort` | Sort order | `{"field": "publish_date_utc", "order": "desc"}` |
| `page.from` | Pagination offset | `0`, `15`, `30`... |

Results are paginated with 15 listings per page.

**Valid radius values:** 1, 2, 5, 10, 15, 30, 50 km (other values are not indexed).

### Required Headers

```
User-Agent: Dart/3.9 (dart:io)
X-Funda-App-Platform: android
Content-Type: application/json
```

### Response Data

Listing responses include:
- **Identifiers** - globalId, tinyId
- **AddressDetails** - title, city, postcode, province, neighbourhood, house number
- **Price** - numeric and formatted prices (selling or rental), auction flag
- **FastView** - bedrooms, living area, plot area, energy label
- **Media** - photos, floorplans, videos, 360° photos, brochure URL (all with CDN base URLs)
- **KenmerkSections** - detailed property characteristics (70+ fields)
- **Coordinates** - latitude/longitude
- **ObjectInsights** - view and save counts
- **Advertising.TargetingOptions** - boolean features (garden, balcony, solar panels, heat pump, parking, etc.), construction year, room counts
- **Share** - shareable URL
- **GoogleMapsObjectUrl** - direct Google Maps link
- **PublicationDate** - when the listing was published
- **Tracking.Values.brokers** - broker ID and association

## API Reference

### Funda

Main entry point for the API.

```python
from funda import Funda

f = Funda(timeout=30)
```

#### get_listing(listing_id)

Get a single listing by ID or URL.

```python
# By numeric ID (tinyId or globalId)
listing = f.get_listing(43117443)

# By URL
listing = f.get_listing('https://www.funda.nl/detail/koop/city/house-name/43117443/')
```

#### search_listing(location, ...)

Search for listings with filters.

```python
results = f.search_listing(
    location='amsterdam',           # City or area name
    offering_type='buy',            # 'buy' or 'rent'
    price_min=200000,               # Minimum price
    price_max=500000,               # Maximum price
    area_min=50,                    # Minimum living area (m²)
    area_max=150,                   # Maximum living area (m²)
    plot_min=100,                   # Minimum plot area (m²)
    plot_max=500,                   # Maximum plot area (m²)
    object_type=['house'],          # Property types (default: house, apartment)
    energy_label=['A', 'A+'],       # Energy labels to filter
    sort='newest',                  # Sort order (see below)
    page=0,                         # Page number (15 results per page)
)
```

**Radius search** - search within a radius from a postcode or city:

```python
results = f.search_listing(
    location='1012AB',              # Postcode or city
    radius_km=10,                   # Search radius in km
    price_max=750000,
)
```

> **Note:** Valid radius values are 1, 2, 5, 10, 15, 30, and 50 km. Other values are automatically mapped to the nearest valid radius.

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

**Multiple locations:**

```python
results = f.search_listing(['amsterdam', 'rotterdam', 'utrecht'])
```

#### get_latest_id()

Get the highest listing ID currently in Funda's search index.

```python
latest = f.get_latest_id()  # e.g., 7852306
```

#### poll_new_listings(since_id, ...)

Generator that polls for new listings by incrementing IDs.

```python
for listing in f.poll_new_listings(
    since_id=7852306,           # Start from this ID + 1
    max_consecutive_404s=20,    # Stop after N consecutive 404s
    offering_type='buy',        # Filter: 'buy' or 'rent' (optional)
):
    print(listing['title'])
```

This bypasses ES search and queries the detail API directly, catching listings that haven't been indexed yet.

#### get_price_history(listing)

Get historical price data for a listing, including previous asking prices, WOZ tax assessments, and sale history.

```python
listing = f.get_listing(43032486)
history = f.get_price_history(listing)

for change in history:
    print(change['date'], change['human_price'], change['status'])
# 22 okt, 2025    €435.000     asking_price
# 1 jan, 2025     €472.000     woz
# 19 aug, 2019    €300.000     asking_price
```

**Returns:** List of price changes, each containing:

| Field | Description |
|-------|-------------|
| `price` | Numeric price |
| `human_price` | Formatted price (e.g., "€435.000") |
| `date` | Human readable date |
| `timestamp` | ISO timestamp |
| `source` | "Funda" or "WOZ" |
| `status` | `asking_price`, `sold`, or `woz` |

> **Note:** This fetches data from the Walter Living API. Only called when explicitly requested (lazy-loaded).

#### get_contact_info(listing)

Get the realtor/makelaar agency name and phone number for a listing. Accepts a `Listing`, a numeric id (globalId or tinyId), or a Funda URL.

```python
listing = f.get_listing(43333315)
contact = f.get_contact_info(listing)

print(contact['name'], contact['phone'])
# Scheffer Makelaardij B.V. 020-2470322
```

**Returns:** A dict with the primary broker hoisted to the top level:

| Field | Description |
|-------|-------------|
| `name` | Agency display name |
| `phone` | Agency phone number |
| `broker_id` | Numeric office id |
| `association` | Trade association code (e.g. `VN`) |
| `is_contacting_enabled` | Whether the in-app contact form is enabled |
| `listing_id` / `tiny_id` / `listing_status` | Listing meta |
| `brokers` | Full list of brokers (for the rare multi-agency case) |

Raises `LookupError` if the listing has no contact info exposed.

#### get_contact_form(listing)

Get the agency's contact-form availability (which weekdays and times-of-day they accept inquiries through the in-app form).

```python
form = f.get_contact_form(43333315)
print(form['days'], form['times_of_day'])
# ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'] ['Morning', 'Afternoon']
```

**Returns:** Dict with `office_id`, `office_name`, `days`, `times_of_day`, `is_contacting_enabled`, `is_viewing_planner_enabled`, plus the raw `offices` list.

#### get_listing_summary(listing)

Lightweight version of `get_listing` (no descriptions, photos, kenmerken). Faster and smaller, useful for batch enrichment.

```python
summary = f.get_listing_summary(7985628)
print(summary['title'], summary['price'], summary['energy_label'])
# Semarangstraat 13 650000 C
```

**Returns:** A `Listing` object with summary fields (`title`, `price`, `living_area`, `plot_area`, `bedrooms`, `energy_label`, `broker_name`, `url`, `thumbnail_url`, …).

#### get_similar_listings(listing)

Get globalIds of similar / recently-sold listings near a given listing. Returns IDs only; combine with `get_listing_summary` or `get_listing` to materialize them.

```python
sim = f.get_similar_listings(7988952)
for gid in sim['recently_sold']:
    print(f.get_listing_summary(gid)['title'])
```

**Returns:** Dict with `recently_listed` and `recently_sold`, each a list of integer globalIds.

#### get_market_insights(city, neighbourhood)

Neighbourhood demographics and average asking €/m² for a (city, neighbourhood) pair. Accepts a `Listing` directly to use its city/neighbourhood automatically.

```python
mi = f.get_market_insights('Amsterdam', 'Twiske-West')
# {'city': 'Amsterdam', 'neighbourhood': 'Twiske-West',
#  'inhabitants': 2510, 'families_with_children_pct': 43.96,
#  'avg_asking_price_per_m2': 5975}

# Or pass a Listing
listing = f.get_listing(43333315)
mi = f.get_market_insights(listing)
```

**Returns:** Dict with `city`, `neighbourhood`, `inhabitants`, `families_with_children_pct`, `avg_asking_price_per_m2`. Raises `LookupError` for unknown neighbourhoods (HTTP 204).

#### get_broker_info(broker)

Get the agency's profile page: phone, email, website, postal address, affiliation (NVM/VBO/…), description, certificates, languages, services. Accepts a numeric `broker_id` or a `Listing` (uses its `broker_id` automatically).

```python
info = f.get_broker_info(24716)
print(info['name'], info['phone'], info['email'])
# Simone Dijkman Makelaardij 075 7725155 info@simonedijkman.nl

# Or chain from a listing
listing = f.get_listing(43333315)
info = f.get_broker_info(listing)
```

#### get_broker_listings(broker)

Every listing the agency has handled, tagged by status. Useful for analyzing an agency's deal history (sold dates, prices, neighbourhoods).

```python
listings = f.get_broker_listings(24716)
sold = [l for l in listings if l['status'] == 'sold']
for_sale = [l for l in listings if l['status'] == 'for_sale']
print(f"{len(sold)} sold, {len(for_sale)} active")
```

**Returns:** Flat list of dicts. Each entry has `status` (`sold`, `for_sale`, `purchased`), `listing_id`, `tiny_id`, `title`, `street`, `house_number`, `postcode`, `city`, `latitude`, `longitude`, `price`, `price_formatted`, `price_condition`, `publication_date`, `transaction_date`, `image_url`, `detail_url`.

#### get_broker_reviews(broker)

Customer reviews and aggregate scores per agency. The API returns only a representative sample of recent reviews — `number_of_reviews` is the true total.

```python
r = f.get_broker_reviews(24716)
print(f"{r['average']}/10 over {r['number_of_reviews']} reviews")
for review in r['reviews']:
    print(review['date'], review['average'], review['text'][:60])
```

**Returns:** Dict with `average` (float), `number_of_reviews`, `selectivity_percentage`, a single `highlight` review, and a `reviews` list. Each review has subscores (`expertise`, `local_market_knowledge`, `price_and_quality`, `service_and_guidance`, `average`), `transaction_type`, `text`, and `date`.

### Listing

Listing objects support dict-like access with convenient aliases.

**Basic info:**

```python
listing['title']            # Property title/address
listing['city']             # City name
listing['postcode']         # Postal code
listing['province']         # Province
listing['neighbourhood']    # Neighbourhood name
listing['municipality']     # Municipality (gemeente)
listing['house_number']     # House number
listing['house_number_ext'] # House number extension (e.g., "A", "II")
```

**Price & Status:**

```python
listing['price']            # Numeric price
listing['price_formatted']  # Formatted price string (e.g., "€ 450.000 k.k.")
listing['price_per_m2']     # Price per m² (from characteristics)
listing['status']           # "available" or "sold"
listing['offering_type']    # "Sale" or "Rent"
```

**Property details:**

```python
listing['object_type']      # House, Apartment, etc.
listing['house_type']       # Type of house (e.g., "Tussenwoning")
listing['construction_type'] # New or existing construction
listing['construction_year'] # Year built
listing['bedrooms']         # Number of bedrooms
listing['rooms']            # Total number of rooms
listing['living_area']      # Living area in m²
listing['plot_area']        # Plot area in m²
listing['energy_label']     # Energy label (A, B, C, etc.)
listing['description']      # Full description text
```

**Dates:**

```python
listing['publication_date'] # When listed on Funda
listing['offered_since']    # "Offered since" date (from characteristics)
listing['acceptance']       # Acceptance terms (e.g., "In overleg")
```

**Location:**

```python
listing['coordinates']      # (lat, lng) tuple
listing['latitude']         # Latitude
listing['longitude']        # Longitude
listing['google_maps_url']  # Direct Google Maps link
```

**Media:**

```python
listing['photos']           # List of photo IDs
listing['photo_urls']       # List of full CDN URLs for photos
listing['photo_count']      # Number of photos
listing['floorplans']       # List of floorplan IDs
listing['floorplan_urls']   # List of full CDN URLs for floorplans
listing['videos']           # List of video IDs
listing['video_urls']       # List of video URLs
listing['photos_360']       # List of 360° photo dicts with name, id, url
listing['brochure_url']     # PDF brochure URL (if available)
```

**Property features (booleans):**

```python
listing['has_garden']           # Has garden
listing['has_balcony']          # Has balcony
listing['has_roof_terrace']     # Has roof terrace
listing['has_solar_panels']     # Has solar panels
listing['has_heat_pump']        # Has heat pump
listing['has_parking_on_site']  # Parking on property
listing['has_parking_enclosed'] # Enclosed parking
listing['is_energy_efficient']  # Energy efficient property
listing['is_monument']          # Listed/protected building
listing['is_fixer_upper']       # Fixer-upper (kluswoning)
listing['is_auction']           # Sold via auction
listing['open_house']           # Has open house scheduled
```

**Stats & metadata:**

```python
listing['views']            # Number of views on Funda
listing['saves']            # Number of times saved
listing['highlight']        # Highlight text (blikvanger)
listing['global_id']        # Internal Funda ID
listing['tiny_id']          # Public ID (used in URLs)
listing['url']              # Full Funda URL
listing['share_url']        # Shareable URL
listing['broker_id']        # Broker ID
listing['broker_association'] # Broker association (e.g., "NVM")
listing['characteristics']  # Dict of all detailed characteristics
```

**Key aliases** - these all work:

| Alias | Canonical Key |
|-------|---------------|
| `name`, `address` | `title` |
| `location`, `locality` | `city` |
| `area`, `size` | `living_area` |
| `type`, `property_type` | `object_type` |
| `images`, `pictures`, `media` | `photos` |
| `agent`, `realtor`, `makelaar` | `broker` |
| `zip`, `zipcode`, `postal_code` | `postcode` |

#### Methods

```python
listing.summary()       # Text summary of the listing
listing.to_dict()       # Convert to plain dictionary
listing.keys()          # List available keys
listing.get('key')      # Get with default (like dict.get)
listing.getID()         # Get listing ID
```

## Examples

### Find apartments in Amsterdam under €400k

```python
from funda import Funda

f = Funda()
results = f.search_listing('amsterdam', price_max=400000)

for listing in results:
    print(f"{listing['title']}")
    print(f"  Price: €{listing['price']:,}")
    print(f"  Area: {listing.get('living_area', 'N/A')}")
    print(f"  Bedrooms: {listing.get('bedrooms', 'N/A')}")
    print()
```

### Get detailed listing information

```python
from funda import Funda

f = Funda()
listing = f.get_listing(43117443)

print(listing.summary())

# Access all characteristics
for key, value in listing['characteristics'].items():
    print(f"{key}: {value}")
```

### Search rentals in multiple cities

```python
from funda import Funda

f = Funda()
results = f.search_listing(
    location=['amsterdam', 'rotterdam', 'den-haag'],
    offering_type='rent',
    price_max=2000,
)

print(f"Found {len(results)} rentals")
```

### Find energy-efficient homes with a garden

```python
from funda import Funda

f = Funda()
listing = f.get_listing(43117443)

# Check property features
if listing['has_garden'] and listing.get('has_solar_panels'):
    print("Energy efficient with garden!")

if listing['is_energy_efficient']:
    print(f"Energy label: {listing['energy_label']}")
```

### Download listing photos

```python
from funda import Funda
import requests

f = Funda()
listing = f.get_listing(43117443)

# Photo URLs are ready to use
for i, url in enumerate(listing['photo_urls'][:5]):
    response = requests.get(url)
    with open(f"photo_{i}.jpg", "wb") as file:
        file.write(response.content)

# Also available: floorplan_urls, video_urls
```

### Search by radius from postcode

```python
from funda import Funda

f = Funda()
results = f.search_listing(
    location='1012AB',
    radius_km=15,
    price_max=600000,
    energy_label=['A', 'A+', 'A++'],
    sort='newest',
)

for r in results:
    print(f"{r['title']} - €{r['price']:,}")
```

### Poll for new listings (bypass ES lag)

Funda's search index can lag behind the actual database by hours. Use `poll_new_listings` to find listings that search doesn't show yet:

```python
from funda import Funda

f = Funda()

# Get starting point from search (one-time)
latest_id = f.get_latest_id()  # e.g., 7852306

# Poll for new listings by incrementing IDs
for listing in f.poll_new_listings(since_id=latest_id):
    print(f"New: {listing['title']}, {listing['city']}")
    print(f"     {listing['url']}")

# Filter by type
for listing in f.poll_new_listings(since_id=latest_id, offering_type="buy"):
    print(f"New sale: {listing['title']}")
```

The generator stops after 20 consecutive 404s (configurable via `max_consecutive_404s`).

### Get price history for a listing

```python
from funda import Funda

f = Funda()
listing = f.get_listing(43032486)

# Fetch historical prices (WOZ assessments, previous asking prices, sales)
history = f.get_price_history(listing)

print(f"Price history for {listing['title']}:")
for change in history:
    print(f"  {change['date']}: {change['human_price']} ({change['status']})")

# Calculate price change over time
funda_prices = [c for c in history if c['source'] == 'Funda']
if len(funda_prices) >= 2:
    newest, oldest = funda_prices[0]['price'], funda_prices[-1]['price']
    change_pct = ((newest - oldest) / oldest) * 100
    print(f"\nPrice change: {change_pct:+.1f}%")
```

## Disclaimer

This is an unofficial library and is not affiliated with, authorized, maintained, sponsored, or endorsed by Funda or any of its affiliates. Use at your own risk.

This library only accesses publicly available listing data through Funda's undocumented internal API. Using this library may violate Funda's Terms of Service. The authors are not responsible for any consequences of using this software.

This project is intended for personal use, research, and educational purposes only.

- The API is undocumented and may change or break at any time without notice.
- Please use this library responsibly and avoid excessive requests that could burden Funda's infrastructure.
- Scraped data may be subject to copyright and usage restrictions. Ensure your use complies with applicable laws.

## License

AGPL-3.0
