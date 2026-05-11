# Architecture Notes

These notes describe the Funda-facing API concepts that pyfunda wraps. Normal
users should start with [API.md](API.md); this page is useful when you need to
understand identifiers, payloads, and response shape.

## ID System

Funda uses two ID systems:

- **globalId**: Internal numeric ID, used by the listing-detail API
- **tinyId**: Public-facing ID, appears in URLs like `funda.nl/detail/koop/amsterdam/.../{tinyId}/`

The `tinyId` endpoint allows fetching any listing directly from a Funda URL
without first knowing the internal ID.

## Search API

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

**Valid radius values:** 1, 2, 5, 10, 15, 30, 50 km. Other values are mapped
to the nearest indexed radius because those are the only radius buckets Funda
exposes.

## Autocomplete API

Autocomplete uses Funda's geo search-box template endpoint:

```http
POST https://listing-search-wonen.funda.io/geo-wonen-alias-prod/_search/template
```

pyfunda sends the `searchbox_20250805` template with `value`, `size`,
`timeout`, `area_types`, `exclude`, and sort settings. Suggestions return Funda
geo IDs such as `amsterdam/wijk-slotermeer-west-0`; those IDs can be passed
directly to `Funda.search(location=...)`.

Broad search-box area types include streets. For vague user input like
`"amsterdam west"`, area-focused types such as `city`, `municipality`,
`neighborhood`, and `wijk` usually produce better location suggestions.

## Response Data

Listing responses include:

- Identifiers: globalId, tinyId
- AddressDetails: title, city, postcode, province, neighbourhood, house number
- Price: numeric and formatted prices, sale/rent metadata, auction flag
- FastView: bedrooms, living area, plot area, energy label
- Media: photos, floorplans, videos, 360 photos, virtual tours, brochure URL
- KenmerkSections: detailed property characteristics
- Coordinates: latitude/longitude
- ObjectInsights: view and save counts
- Advertising.TargetingOptions: boolean features, construction year, room counts
- Share: shareable URL
- GoogleMapsObjectUrl: direct Google Maps link
- PublicationDate: when the listing was published
- Tracking.Values.brokers: broker ID and association

pyfunda models the common stable fields as dataclasses and keeps the full
original payload on `listing.raw`.
