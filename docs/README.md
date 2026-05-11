# pyfunda Documentation

pyfunda is a Python library for reading public Funda listing data without
scraping HTML pages or running a browser.

If you are new to this project, read this page first. It explains what each
documentation file is for and which one to open for a specific task.

## What You Can Do

With pyfunda you can:

- Fetch one listing by Funda URL or listing ID
- Search for listings in a city, neighbourhood, postcode, or radius
- Resolve vague location text like `amsterdam west` into Funda location IDs
- Iterate through multiple search pages
- Fetch extra data such as broker info, contact forms, similar listings, market insights, and price history
- Work with Python dataclasses instead of raw JSON dictionaries
- Access the original Funda response through `.raw` when pyfunda does not model a field yet

## What To Read First

Start with [API.md](API.md) if you want to use the library. It explains the
main objects, common workflows, and every public method.

Open [EXAMPLES.md](EXAMPLES.md) when you want copyable examples for searches,
autocomplete, price history, photos, brokers, and batch fetching.

Open [ARCHITECTURE.md](ARCHITECTURE.md) when you want to understand how Funda's
internal APIs, IDs, search templates, and response payloads work.

Open [DEVELOPMENT.md](DEVELOPMENT.md) when you want to run tests, contribute
code, or understand the development workflow.

## First Working Example

```python
from funda import Funda

with Funda() as client:
    listings = client.search("amsterdam", max_price=500000)

    for listing in listings:
        print(listing.title, listing.price.amount, listing.url)
```

`client.search(...)` returns a list of `Listing` objects. A `Listing` is a
Python object with fields like `title`, `city`, `price`, `living_area`, and
`url`.

## When Location Text Is Vague

For simple places, pass the location directly:

```python
client.search("amsterdam")
```

For vague text such as `amsterdam west`, use autocomplete first:

```python
suggestions = client.autocomplete(
    "amsterdam west",
    area_types=["city", "municipality", "neighborhood", "wijk"],
)

selected_location = suggestions[0]
listings = client.search(selected_location.id)
```

Autocomplete returns locations, not houses. Search returns houses.
