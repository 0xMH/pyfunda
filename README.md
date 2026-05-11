# pyfunda

[![PyPI version](https://img.shields.io/pypi/v/pyfunda)](https://pypi.org/project/pyfunda/)
[![Python versions](https://img.shields.io/pypi/pyversions/pyfunda)](https://pypi.org/project/pyfunda/)
[![License](https://img.shields.io/pypi/l/pyfunda)](https://github.com/0xMH/pyfunda/blob/main/LICENSE)

**pyfunda** is a Python API wrapper for [Funda.nl](https://www.funda.nl), the Netherlands' largest Dutch real estate platform. It talks to Funda's reverse engineered mobile JSON API, so you get clean typed objects for listings, prices, media, brokers, and price history without HTML scraping, Selenium, a headless browser, or CAPTCHA solving.

Funda has no public developer API. pyfunda is the only working opensource Python client that hits Funda's app facing `*.funda.io` endpoints directly, the same ones the official Android app uses.

Use pyfunda as a Funda API client or Funda Python SDK to fetch Dutch property listings, run search queries by city and price, pull listing detail and media, get broker info and reviews, read price history, and stream new listings. If you have been looking for a working fundascraper alternative or a Netherlands housing API, this is the only Python wrapper hitting the same `*.funda.io` endpoints the Funda Android app uses.

> If you find this useful, consider giving it a star, it helps others discover the project.

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
| `listing-search-wonen.funda.io/geo-wonen-alias-prod/_search/template` | POST | Autocomplete location/search-box text |
| `listing-detail-summary.funda.io/api/v1/listing/nl/{globalId}` | GET | Fetch lightweight listing summary |
| `contacts-flows-bff.funda.io/.../contact-block` | GET | Fetch realtor contact block |
| `contacts-bff.funda.io/.../contact-form` | GET | Fetch contact-form availability |
| `local-listings.funda.io/api/v1/similarlistings` | GET | Fetch similar and recently sold listing IDs |
| `marketinsights.funda.io/v2/localinsights/preview/...` | GET | Fetch neighbourhood market insights |
| `brokerpresentation-office-pages-bff.funda.io/.../office-page/...` | GET | Fetch broker profile and listings |
| `reviews-office-pages-bff.funda.io/.../reviews/nl` | GET | Fetch broker review aggregates |
| `api.walterliving.com/hunter/lookup` | POST | Fetch price history data |

The request transport, headers, retry profiles, and TLS fingerprint rotation are internal implementation details. Normal users only construct `Funda()` and call the public methods below.

## Documentation

- [Start here](docs/README.md)
- [API reference](docs/API.md)
- [Architecture notes](docs/ARCHITECTURE.md)
- [Examples](docs/EXAMPLES.md)
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
