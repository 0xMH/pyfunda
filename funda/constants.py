"""Constants used by the Funda client."""

from funda.models import ConstructionPeriod, Fingerprint


API_BASE = "https://listing-detail-page.funda.io/api/v4/listing/object/nl"
API_LISTING = f"{API_BASE}/{{listing_id}}"
API_LISTING_TINY = f"{API_BASE}/tinyId/{{tiny_id}}"
API_SEARCH = "https://listing-search-wonen.funda.io/_msearch/template"
API_LOCATION_AUTOCOMPLETE = (
    "https://listing-search-wonen.funda.io/geo-wonen-alias-prod/_search/template"
)
API_WALTER = "https://api.walterliving.com/hunter/lookup"
API_CONTACTS = (
    "https://contacts-flows-bff.funda.io/api/v1/contacts-flows/"
    "listings/{listing_id}/contact-block"
)
API_CONTACT_FORM = (
    "https://contacts-bff.funda.io/api/v4/contact/"
    "listings/{listing_id}/contact-form"
)
API_LISTING_SUMMARY = "https://listing-detail-summary.funda.io/api/v1/listing/nl/{global_id}"
API_SIMILAR = "https://local-listings.funda.io/api/v1/similarlistings"
API_MARKET_INSIGHTS = (
    "https://marketinsights.funda.io/v2/localinsights/"
    "preview/{city}/{neighbourhood}"
)
API_BROKER_INFO = (
    "https://brokerpresentation-office-pages-bff.funda.io/api/v3.0/"
    "office-page/Wonen/{broker_id}/nl"
)
API_BROKER_LISTINGS = f"{API_BROKER_INFO}/listings"
API_BROKER_REVIEWS = (
    "https://reviews-office-pages-bff.funda.io/api/v1/"
    "office-page/{broker_id}/reviews/nl"
)

SEARCH_INDEX = "listings-wonen-searcher-alias-prod"
SEARCH_TEMPLATE_ID = "search_result_20260227"
LOCATION_AUTOCOMPLETE_TEMPLATE_ID = "searchbox_20250805"
LOCATION_AUTOCOMPLETE_AREA_TYPES = (
    "country",
    "city",
    "province",
    "region",
    "municipality",
    "street",
    "postal_code",
    "neighborhood",
    "wijk",
)

PAGE_SIZE = 15
VALID_RADII = (1, 2, 5, 10, 15, 30, 50)
VALID_OFFERING_TYPES = ("buy", "rent")
VALID_AVAILABILITY = ("available", "negotiations", "unavailable", "sold")
RETRY_STATUS_CODES = {403, 429, 503}

SORT_OPTIONS = {
    "newest": ("publish_date_utc", "desc"),
    "oldest": ("publish_date_utc", "asc"),
    "price_asc": ("price.selling_price", "asc"),
    "price_desc": ("price.selling_price", "desc"),
    "area_asc": ("floor_area", "asc"),
    "area_desc": ("floor_area", "desc"),
    "plot_desc": ("plot_area", "desc"),
    "city": ("address.city", "asc"),
    "postcode": ("address.postal_code", "asc"),
}

CONSTRUCTION_PERIODS: tuple[ConstructionPeriod, ...] = (
    ConstructionPeriod("before_1906", "before 1906", 0, 1905),
    ConstructionPeriod("from_1906_to_1930", "1906-1930", 1906, 1930),
    ConstructionPeriod("from_1931_to_1944", "1931-1944", 1931, 1944),
    ConstructionPeriod("from_1945_to_1959", "1945-1959", 1945, 1959),
    ConstructionPeriod("from_1960_to_1970", "1960-1970", 1960, 1970),
    ConstructionPeriod("from_1971_to_1980", "1971-1980", 1971, 1980),
    ConstructionPeriod("from_1981_to_1990", "1981-1990", 1981, 1990),
    ConstructionPeriod("from_1991_to_2000", "1991-2000", 1991, 2000),
    ConstructionPeriod("from_2001_to_2010", "2001-2010", 2001, 2010),
    ConstructionPeriod("from_2011_to_2020", "2011-2020", 2011, 2020),
    ConstructionPeriod("after_2020", "after 2020", 2021, 9999),
)

FUNDA_JA3 = (
    "771,4867-4865-4866-52393-52392-49195-49199-49196-49200-49161-49171-"
    "49162-49172-156-157-47-53,0-23-65281-10-11-35-13-51-45-43,29-23-24,0"
)
FUNDA_JA3_EXT21 = (
    "771,4867-4865-4866-52393-52392-49195-49199-49196-49200-49161-49171-"
    "49162-49172-156-157-47-53,0-23-65281-10-11-35-13-51-45-43-21,29-23-24,0"
)

FINGERPRINT_POOL: tuple[Fingerprint, ...] = (
    Fingerprint("tls_ja3", ja3=FUNDA_JA3),
    Fingerprint("tls_ja3", ja3=FUNDA_JA3_EXT21),
    Fingerprint("curl_impersonate", target="safari15_5"),
    Fingerprint("curl_impersonate", target="safari15_3"),
    Fingerprint("tls_client", identifier="okhttp4_android_13"),
    Fingerprint("tls_client", identifier="chrome_120"),
)

DEFAULT_MAX_RETRIES = len(FINGERPRINT_POOL) - 1
