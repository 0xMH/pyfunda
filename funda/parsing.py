"""Public parser entry points used by the Funda client."""

from funda._detail_parser import parse_listing
from funda._autocomplete_parser import parse_location_suggestions
from funda._enrichment_parser import (
    parse_broker_info,
    parse_broker_listings,
    parse_broker_reviews,
    parse_contact_form,
    parse_contact_info,
    parse_listing_summary,
    parse_market_insights,
    parse_similar_listings,
)
from funda._price_history_parser import parse_price_history
from funda._search_parser import parse_search_results

__all__ = [
    "parse_broker_info",
    "parse_broker_listings",
    "parse_broker_reviews",
    "parse_contact_form",
    "parse_contact_info",
    "parse_listing",
    "parse_listing_summary",
    "parse_location_suggestions",
    "parse_market_insights",
    "parse_price_history",
    "parse_search_results",
    "parse_similar_listings",
]
