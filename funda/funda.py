"""Public Funda client."""

import re
import time
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, ClassVar, TypeVar
from urllib.parse import quote, urlencode

from funda._parallel import _ParallelRunner
from funda._transport import _FundaTransport
from funda.constants import (
    API_LOCATION_AUTOCOMPLETE,
    API_BROKER_INFO,
    API_BROKER_LISTINGS,
    API_BROKER_REVIEWS,
    API_CONTACT_FORM,
    API_CONTACTS,
    API_LISTING,
    API_LISTING_SUMMARY,
    API_LISTING_TINY,
    API_MARKET_INSIGHTS,
    API_SEARCH,
    API_SIMILAR,
    API_WALTER,
    DEFAULT_MAX_RETRIES,
    LOCATION_AUTOCOMPLETE_AREA_TYPES,
    PAGE_SIZE,
)
from funda.exceptions import FundaRequestError, ListingNotFound, PriceHistoryError, SearchError
from funda._autocomplete import LocationAutocomplete
from funda.listing import Listing, LocationSuggestion, PriceHistory
from funda.models import JsonDict
from funda.parsing import (
    parse_broker_info,
    parse_broker_listings,
    parse_broker_reviews,
    parse_contact_form,
    parse_contact_info,
    parse_listing,
    parse_listing_summary,
    parse_location_suggestions,
    parse_market_insights,
    parse_price_history,
    parse_search_results,
    parse_similar_listings,
)
from funda.search import _Search


_TextValues = str | Sequence[str] | None
_ListingInput = Listing | int | str
_BrokerInput = Listing | int | str
_Item = TypeVar("_Item")
_Result = TypeVar("_Result")


@dataclass(slots=True)
class Funda:
    """Main interface to Funda listings."""

    LISTING_ID_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"(?<!\d)(\d{7,9})(?!\d)")

    timeout: int = 30
    max_retries: int = DEFAULT_MAX_RETRIES
    retry_backoff: float = 0.1

    _transport: _FundaTransport = field(init=False, repr=False)
    _parallel_runner: _ParallelRunner["Funda"] | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self._transport = _FundaTransport(
            timeout=self.timeout,
            max_retries=self.max_retries,
            retry_backoff=self.retry_backoff,
        )

    def close(self) -> None:
        if self._parallel_runner is not None:
            self._parallel_runner.close()
            self._parallel_runner = None
        self._transport.close()

    def __enter__(self) -> "Funda":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def listing(self, listing_id: int | str) -> Listing:
        listing_id_str = self._listing_id_from_input(listing_id)
        last_status = None

        for url in self._listing_urls(listing_id_str):
            response = self._transport.get(url)
            last_status = response.status_code
            if response.status_code == 200:
                return parse_listing(response.json())
            if response.status_code != 404:
                raise FundaRequestError(
                    f"Listing {listing_id_str} request failed "
                    f"(status {response.status_code})"
                )

        raise ListingNotFound(f"Listing {listing_id_str} not found (status {last_status})")

    def listings(self, listing_ids: Iterable[int | str], *, workers: int = 8) -> list[Listing]:
        return self._parallel(
            lambda client, listing_id: client.listing(listing_id),
            listing_ids,
            workers=workers,
        )

    def search(
        self,
        location: _TextValues = None,
        **filters,
    ) -> list[Listing]:
        return self._search_results(_Search.from_filters(location, **filters))

    def autocomplete(
        self,
        value: str,
        *,
        size: int = 10,
        timeout: str = "3s",
        area_types: Sequence[str] | None = None,
        exclude: Sequence[str] | None = None,
        use_sort: bool = False,
        sort: Sequence[Any] | None = None,
    ) -> list[LocationSuggestion]:
        """Suggest Funda location identifiers for search-box text."""
        autocomplete = LocationAutocomplete(
            value=value,
            size=size,
            timeout=timeout,
            area_types=area_types or LOCATION_AUTOCOMPLETE_AREA_TYPES,
            exclude=exclude or (),
            use_sort=use_sort,
            sort=sort or (),
        )
        return parse_location_suggestions(self._autocomplete(autocomplete))

    def iter_search(
        self,
        location: _TextValues = None,
        *,
        start_page: int = 0,
        max_pages: int | None = None,
        workers: int = 1,
        **filters,
    ) -> Iterator[Listing]:
        if start_page < 0:
            raise ValueError("start_page must be >= 0")
        if max_pages is not None and max_pages < 0:
            raise ValueError("max_pages must be >= 0")
        if workers < 1:
            raise ValueError("workers must be >= 1")
        if "page" in filters:
            raise ValueError("iter_search manages pages; use start_page instead of page")
        if workers > 1 and max_pages is None:
            raise ValueError("parallel iter_search requires max_pages")

        search = _Search.from_filters(location, **filters)
        if workers > 1:
            searches = [
                search.with_page(page)
                for page in range(start_page, start_page + (max_pages or 0))
            ]
            for listings in self._parallel(
                lambda client, page_search: client._search_results(page_search),
                searches,
                workers=workers,
            ):
                if not listings:
                    break
                yield from listings
                if len(listings) < PAGE_SIZE:
                    break
            return

        page = start_page
        fetched_pages = 0
        while max_pages is None or fetched_pages < max_pages:
            listings = self._search_results(search.with_page(page))
            if not listings:
                break
            yield from listings
            fetched_pages += 1
            if len(listings) < PAGE_SIZE:
                break
            page += 1

    def latest_listing_id(self) -> int:
        listings = self.search(sort="newest")
        if not listings:
            raise SearchError("Could not fetch latest listings from search")
        global_ids = [listing.global_id for listing in listings if listing.global_id is not None]
        if not global_ids:
            raise SearchError("Search results did not include listing IDs")
        return max(global_ids)

    def new_listings(
        self,
        since_id: int,
        max_consecutive_404s: int = 20,
    ) -> Iterator[Listing]:
        if max_consecutive_404s < 1:
            raise ValueError("max_consecutive_404s must be >= 1")

        consecutive_404s = 0
        current_id = since_id + 1
        while consecutive_404s < max_consecutive_404s:
            response = self._transport.get(API_LISTING.format(listing_id=current_id))
            if response.status_code == 200:
                consecutive_404s = 0
                yield parse_listing(response.json())
            elif response.status_code == 404:
                consecutive_404s += 1
            else:
                raise FundaRequestError(
                    f"Listing {current_id} request failed "
                    f"(status {response.status_code})"
                )

            current_id += 1

    def price_history(self, listing: Listing | str) -> PriceHistory:
        if isinstance(listing, str):
            listing = self.listing(listing)

        if not listing.url or not listing.title or not listing.postcode:
            raise PriceHistoryError("Listing must have url, title, and postcode")

        payload = {
            "url": listing.url,
            "address": listing.title,
            "zipcode": listing.postcode,
        }
        response = self._transport.post(API_WALTER, profile="walter", json_data=payload)
        if response.status_code != 200:
            raise PriceHistoryError(
                f"Could not fetch price history (status {response.status_code})"
            )
        data = response.json()
        if data.get("status") != "ok":
            raise PriceHistoryError("Price history not available for this listing")
        return parse_price_history(data)

    def contact_info(self, listing: _ListingInput) -> JsonDict:
        """Get realtor contact info for a listing."""
        global_id = self._resolve_global_id(listing)
        data = self._get_json(
            API_CONTACTS.format(listing_id=global_id),
            error="Could not fetch contact info",
            missing={
                204: f"Listing {global_id} has no contact info",
                404: f"Listing {global_id} not found",
            },
        )
        return parse_contact_info(data)

    def contact_form(self, listing: _ListingInput) -> JsonDict:
        """Get contact-form availability for a listing."""
        global_id = self._resolve_global_id(listing)
        data = self._get_json(
            API_CONTACT_FORM.format(listing_id=global_id),
            error="Could not fetch contact form",
            missing={
                204: f"Listing {global_id} has no contact form",
                404: f"Listing {global_id} not found",
            },
        )
        if not data:
            raise LookupError(f"No contact form entries for listing {global_id}")
        return parse_contact_form(data)

    def listing_summary(self, listing: _ListingInput) -> Listing:
        """Get a lightweight listing summary without the full detail payload."""
        global_id = self._resolve_global_id(listing)
        data = self._get_json(
            API_LISTING_SUMMARY.format(global_id=global_id),
            error="Could not fetch listing summary",
            missing={404: f"Listing summary {global_id} not found"},
        )
        return parse_listing_summary(data)

    def similar_listings(self, listing: _ListingInput) -> JsonDict:
        """Get recently listed and recently sold globalIds near a listing."""
        global_id = self._resolve_global_id(listing)
        data = self._get_json(
            f"{API_SIMILAR}?{urlencode({'globalId': global_id})}",
            error="Could not fetch similar listings",
        )
        return parse_similar_listings(data)

    def market_insights(
        self,
        city: str | Listing,
        neighbourhood: str | None = None,
    ) -> JsonDict:
        """Get local market insight data for a city and neighbourhood."""
        city_name, neighbourhood_name = self._market_location(city, neighbourhood)
        city_slug = self._market_slug(city_name)
        neighbourhood_slug = self._market_slug(neighbourhood_name)
        data = self._get_json(
            API_MARKET_INSIGHTS.format(city=city_slug, neighbourhood=neighbourhood_slug),
            error="Could not fetch market insights",
            missing={
                204: f"No market insights for {city_slug}/{neighbourhood_slug}",
                404: f"No market insights for {city_slug}/{neighbourhood_slug}",
            },
        )
        return parse_market_insights(data)

    def broker_info(self, broker: _BrokerInput) -> JsonDict:
        """Get a broker or agency profile."""
        broker_id = self._resolve_broker_id(broker)
        data = self._get_json(
            API_BROKER_INFO.format(broker_id=broker_id),
            error="Could not fetch broker info",
            missing={
                204: f"Broker {broker_id} not found",
                404: f"Broker {broker_id} not found",
            },
        )
        return parse_broker_info(data)

    def broker_listings(self, broker: _BrokerInput) -> list[JsonDict]:
        """Get listings handled by a broker, tagged by status."""
        broker_id = self._resolve_broker_id(broker)
        data = self._get_json(
            API_BROKER_LISTINGS.format(broker_id=broker_id),
            error="Could not fetch broker listings",
            missing={
                204: f"Broker {broker_id} has no listings",
                404: f"Broker {broker_id} not found",
            },
        )
        return parse_broker_listings(data)

    def broker_reviews(self, broker: _BrokerInput) -> JsonDict:
        """Get review aggregates and recent review examples for a broker."""
        broker_id = self._resolve_broker_id(broker)
        data = self._get_json(
            API_BROKER_REVIEWS.format(broker_id=broker_id),
            error="Could not fetch broker reviews",
            missing={
                204: f"Broker {broker_id} has no reviews",
                404: f"Broker {broker_id} not found",
            },
        )
        return parse_broker_reviews(data)

    def _get_json(
        self,
        url: str,
        *,
        error: str,
        missing: Mapping[int, str] | None = None,
    ) -> Any:
        response = self._transport.get(url)
        if response.status_code == 200:
            return response.json()
        if missing and response.status_code in missing:
            raise LookupError(missing[response.status_code])
        raise FundaRequestError(f"{error} (status {response.status_code})")

    def _resolve_global_id(self, listing: _ListingInput) -> int:
        if isinstance(listing, Listing):
            if listing.global_id is not None:
                return listing.global_id
            listing_id = listing.id
            if listing_id is None:
                raise ValueError("Listing has no global_id")
        else:
            listing_id = self._listing_id_from_input(listing)

        if len(str(listing_id)) >= 8:
            global_id = self.listing(listing_id).global_id
            if global_id is None:
                raise ValueError(f"Could not resolve tinyId {listing_id}")
            return global_id
        return int(listing_id)

    def _resolve_broker_id(self, broker: _BrokerInput) -> int:
        if isinstance(broker, Listing):
            primary = broker.broker
            broker_id = (primary.id or primary.office_id) if primary else None
            if not broker_id:
                raise ValueError("Listing has no broker_id")
            return int(broker_id)

        broker_id = str(broker).strip()
        if not broker_id.isdigit():
            raise ValueError(f"Unrecognized broker identifier: {broker!r}")
        return int(broker_id)

    def _market_location(
        self,
        city: str | Listing,
        neighbourhood: str | None,
    ) -> tuple[str, str]:
        if isinstance(city, Listing):
            city_name = city.city or ""
            neighbourhood_name = city.address.neighbourhood or ""
            if not city_name or not neighbourhood_name:
                raise ValueError("Listing must have city and neighbourhood for market insights")
            return city_name, neighbourhood_name

        city_name = city.strip()
        neighbourhood_name = neighbourhood.strip() if neighbourhood else ""
        if not city_name or not neighbourhood_name:
            raise ValueError("city and neighbourhood are required")
        return city_name, neighbourhood_name

    @staticmethod
    def _market_slug(value: str) -> str:
        return quote("-".join(value.strip().lower().split()), safe="-")

    def _search(self, search: _Search) -> JsonDict:
        payload = search.to_payload()
        for attempt in range(3):
            response = self._transport.post(API_SEARCH, profile="search", data=payload)
            if response.status_code == 200:
                return response.json()
            if response.status_code == 400 and attempt < 2:
                time.sleep(0.1 * (attempt + 1))
                continue

            detail = getattr(response, "text", "")[:200]
            suffix = f": {detail}" if detail else ""
            raise SearchError(f"Search failed (status {response.status_code}){suffix}")

        raise SearchError("Search failed without a response")

    def _autocomplete(self, autocomplete: LocationAutocomplete) -> JsonDict:
        payload = autocomplete.to_payload()
        for attempt in range(3):
            response = self._transport.post(
                API_LOCATION_AUTOCOMPLETE,
                profile="search",
                json_data=payload,
            )
            if response.status_code == 200:
                return response.json()
            if response.status_code == 400 and attempt < 2:
                time.sleep(0.1 * (attempt + 1))
                continue

            detail = getattr(response, "text", "")[:200]
            suffix = f": {detail}" if detail else ""
            raise SearchError(
                f"Location autocomplete failed (status {response.status_code}){suffix}"
            )

        raise SearchError("Location autocomplete failed without a response")

    def _search_results(self, search: _Search) -> list[Listing]:
        return parse_search_results(self._search(search))

    def _parallel(
        self,
        func: Callable[["Funda", _Item], _Result],
        items: Iterable[_Item],
        *,
        workers: int,
    ) -> list[_Result]:
        if workers < 1:
            raise ValueError("workers must be >= 1")

        items = list(items)
        if not items:
            return []
        if workers == 1 or len(items) == 1:
            return [func(self, item) for item in items]

        if self._parallel_runner is None:
            self._parallel_runner = _ParallelRunner(self._parallel_client, lambda c: c.close())
        return self._parallel_runner.map(func, items, workers=min(workers, len(items)))

    def _parallel_client(self) -> "Funda":
        return type(self)(
            timeout=self.timeout,
            max_retries=self.max_retries,
            retry_backoff=self.retry_backoff,
        )

    def _listing_id_from_input(self, listing_id: int | str) -> str:
        if isinstance(listing_id, str) and "funda.nl" in listing_id:
            path = listing_id.split("?", 1)[0].split("#", 1)[0]
            matches = self.LISTING_ID_PATTERN.findall(path)
            if not matches:
                raise ValueError(f"Could not extract listing ID from URL: {listing_id}")
            return matches[-1]

        listing_id_str = str(listing_id).strip()
        if not listing_id_str:
            raise ValueError("listing_id must not be empty")
        if not self.LISTING_ID_PATTERN.fullmatch(listing_id_str):
            raise ValueError("listing_id must be a 7-9 digit ID or a Funda URL")
        return listing_id_str

    def _listing_urls(self, listing_id: str) -> tuple[str, ...]:
        global_url = API_LISTING.format(listing_id=listing_id)
        if len(listing_id) >= 8:
            return API_LISTING_TINY.format(tiny_id=listing_id), global_url
        return (global_url,)
