"""Main Funda API class."""

import random
import re
import time
from typing import Any

from curl_cffi import requests
import tls_client

from funda.listing import Listing


# API endpoints
API_BASE = "https://listing-detail-page.funda.io/api/v4/listing/object/nl"
API_LISTING = f"{API_BASE}/{{listing_id}}"
API_LISTING_TINY = f"{API_BASE}/tinyId/{{tiny_id}}"
API_SEARCH = "https://listing-search-wonen.funda.io/_msearch/template"
API_WALTER = "https://api.walterliving.com/hunter/lookup"

# Funda mobile app JA3 fingerprints (captured from real Dart/Flutter app traffic)
# JA3 without extension 21 - from favourites.funda.io
# JA3 hash: 9225d95490794840d9d5f1f94d339285
FUNDA_JA3 = "771,4867-4865-4866-52393-52392-49195-49199-49196-49200-49161-49171-49162-49172-156-157-47-53,0-23-65281-10-11-35-13-51-45-43,29-23-24,0"

# JA3 with extension 21 (padding) - from cdn-settings.segment.com
# JA3 hash: 4bf8cdd8919b07d35ca824c20efb3537
FUNDA_JA3_EXT21 = "771,4867-4865-4866-52393-52392-49195-49199-49196-49200-49161-49171-49162-49172-156-157-47-53,0-23-65281-10-11-35-13-51-45-43-21,29-23-24,0"

# Fingerprint pool - tried in order until one works
# Types: "tls_ja3", "curl_impersonate", "tls_client"
FINGERPRINT_POOL = [
    # tls_client with exact Funda app JA3 fingerprints
    {"type": "tls_ja3", "ja3": FUNDA_JA3},
    {"type": "tls_ja3", "ja3": FUNDA_JA3_EXT21},
    # curl_cffi impersonate fallback - Safari works best with Funda headers
    {"type": "curl_impersonate", "target": "safari15_5"},
    {"type": "curl_impersonate", "target": "safari15_3"},
    # tls_client preset profiles as final fallback
    {"type": "tls_client", "identifier": "okhttp4_android_13"},
    {"type": "tls_client", "identifier": "chrome_120"},
]

# Test endpoint to verify fingerprint works
TEST_URL = f"{API_BASE}/tinyId/43117443"



def _make_headers(for_search: bool = False) -> list[tuple[str, str]]:
    """Generate headers matching the Funda Android app exactly.

    Header order and values are captured from real Funda app traffic.
    """
    trace_id = str(random.randint(10**18, 10**19))
    parent_id = hex(random.randint(10**15, 10**16))[2:]
    tid = hex(int(time.time()))[2:] + "00000000"

    # Base headers in exact order from app traffic
    headers = [
        ("user-agent", "Dart/3.9 (dart:io)"),
        ("x-datadog-sampling-priority", "0"),
        ("x-datadog-origin", "rum"),
        ("tracestate", f"dd=s:0;o:rum;p:{parent_id}"),
        ("accept-encoding", "gzip"),
        ("x-datadog-parent-id", trace_id),
    ]

    if for_search:
        # Search endpoint: content-type, referer, accept, then traceparent
        headers.extend([
            ("content-type", "application/json"),
            ("referer", "https://www.funda.nl/"),
            ("accept", "application/json"),
        ])
    else:
        # Listing endpoint: x-funda-app-platform, content-type, then traceparent
        headers.extend([
            ("x-funda-app-platform", "android"),
            ("content-type", "application/json"),
        ])

    # traceparent is always last
    headers.append(("traceparent", f"00-{tid}{trace_id[:16]}-{parent_id}-00"))

    return headers


def _parse_area(value: str | None) -> int | None:
    """Parse area string like '200 m²' or '2.960 m²' to integer."""
    if not value:  # handles None and ''
        return None
    if isinstance(value, (int, float)):
        return int(value)
    # Remove ' m²' suffix and '.' thousand separator (Dutch locale)
    cleaned = value.replace(' m²', '').replace('.', '')
    return int(cleaned) if cleaned.isdigit() else None


class Funda:
    """Main interface to Funda API.

    Example:
        >>> from funda import Funda
        >>> f = Funda()
        >>> listing = f.get_listing(43117443)
        >>> print(listing['title'], listing['city'])
        Reehorst 13 Luttenberg
        >>> results = f.search_listing('amsterdam', price_max=500000)
        >>> for r in results[:3]:
        ...     print(r['title'], r['price'])
    """

    TINYID_PATTERN = re.compile(r"/(\d{7,9})/?(?:\?|$|#)")

    def __init__(self, timeout: int = 30):
        """Initialize Funda API client.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self._curl_session: requests.Session | None = None
        self._tls_session: tls_client.Session | None = None
        self._fingerprint: dict | None = None

    def _make_headers_dict(self, for_search: bool = False) -> dict[str, str]:
        """Generate headers as dict for tls_client.

        Header order and values match the real Funda Android app exactly.
        """
        trace_id = str(random.randint(10**18, 10**19))
        parent_id = hex(random.randint(10**15, 10**16))[2:]
        tid = hex(int(time.time()))[2:] + "00000000"

        # Build headers in exact order from app traffic
        # Python 3.7+ dicts preserve insertion order
        headers = {
            "user-agent": "Dart/3.9 (dart:io)",
            "x-datadog-sampling-priority": "0",
            "x-datadog-origin": "rum",
            "tracestate": f"dd=s:0;o:rum;p:{parent_id}",
            "accept-encoding": "gzip",
            "x-datadog-parent-id": trace_id,
        }

        if for_search:
            # Search endpoint: content-type, referer, accept, then traceparent
            headers["content-type"] = "application/json"
            headers["referer"] = "https://www.funda.nl/"
            headers["accept"] = "application/json"
        else:
            # Listing endpoint: x-funda-app-platform, content-type, then traceparent
            headers["x-funda-app-platform"] = "android"
            headers["content-type"] = "application/json"

        # traceparent is always last
        headers["traceparent"] = f"00-{tid}{trace_id[:16]}-{parent_id}-00"

        return headers

    def _test_fingerprint(self, fingerprint: dict) -> bool:
        """Test if a fingerprint works against Funda API."""
        try:
            fp_type = fingerprint["type"]
            if fp_type == "tls_ja3":
                # tls_client with custom JA3 - primary method for Funda app fingerprint
                session = tls_client.Session(ja3_string=fingerprint["ja3"], random_tls_extension_order=False)
                headers = self._make_headers_dict()
                response = session.get(TEST_URL, headers=headers, timeout_seconds=5)
            elif fp_type == "curl_ja3":
                session = requests.Session()
                headers = _make_headers()
                response = session.get(TEST_URL, headers=headers, ja3=fingerprint["ja3"], timeout=5)
                session.close()
            elif fp_type == "curl_impersonate":
                session = requests.Session(impersonate=fingerprint["target"])
                headers = _make_headers()
                response = session.get(TEST_URL, headers=headers, timeout=5)
                session.close()
            elif fp_type == "tls_client":
                session = tls_client.Session(client_identifier=fingerprint["identifier"], random_tls_extension_order=False)
                headers = self._make_headers_dict()
                response = session.get(TEST_URL, headers=headers, timeout_seconds=5)
            else:
                return False
            return response.status_code == 200
        except Exception:
            return False

    def _find_working_fingerprint(self) -> dict:
        """Find a working fingerprint from the pool."""
        for fp in FINGERPRINT_POOL:
            if self._test_fingerprint(fp):
                return fp
        raise RuntimeError("No working fingerprint found. Funda may have updated their bot detection.")

    def _ensure_session(self) -> None:
        """Ensure a working session is created."""
        if self._fingerprint is None:
            self._fingerprint = self._find_working_fingerprint()

        fp_type = self._fingerprint["type"]
        if fp_type == "tls_ja3":
            # tls_client with custom JA3 - exact Funda app fingerprint
            if self._tls_session is None:
                self._tls_session = tls_client.Session(
                    ja3_string=self._fingerprint["ja3"],
                    random_tls_extension_order=False
                )
        elif fp_type == "curl_ja3":
            if self._curl_session is None:
                self._curl_session = requests.Session()
        elif fp_type == "curl_impersonate":
            if self._curl_session is None:
                self._curl_session = requests.Session(impersonate=self._fingerprint["target"])
        elif fp_type == "tls_client":
            if self._tls_session is None:
                self._tls_session = tls_client.Session(
                    client_identifier=self._fingerprint["identifier"],
                    random_tls_extension_order=False
                )

    def _get(self, url: str, headers_list: list[tuple[str, str]]) -> Any:
        """Make GET request using the active session."""
        self._ensure_session()
        fp_type = self._fingerprint["type"]

        if fp_type in ("tls_ja3", "tls_client"):
            headers = self._make_headers_dict()
            return self._tls_session.get(url, headers=headers, timeout_seconds=self.timeout)
        elif fp_type == "curl_ja3":
            return self._curl_session.get(url, headers=headers_list, ja3=self._fingerprint["ja3"], timeout=self.timeout)
        else:
            return self._curl_session.get(url, headers=headers_list, timeout=self.timeout)

    def _post(self, url: str, headers_list: list[tuple[str, str]], data: str = None, json_data: dict = None, for_search: bool = False) -> Any:
        """Make POST request using the active session."""
        self._ensure_session()
        fp_type = self._fingerprint["type"]

        if fp_type in ("tls_ja3", "tls_client"):
            headers = self._make_headers_dict(for_search=for_search)
            if json_data:
                return self._tls_session.post(url, headers=headers, json=json_data, timeout_seconds=self.timeout)
            return self._tls_session.post(url, headers=headers, data=data, timeout_seconds=self.timeout)
        elif fp_type == "curl_ja3":
            if json_data:
                return self._curl_session.post(url, headers=headers_list, json=json_data, ja3=self._fingerprint["ja3"], timeout=self.timeout)
            return self._curl_session.post(url, headers=headers_list, data=data, ja3=self._fingerprint["ja3"], timeout=self.timeout)
        else:
            if json_data:
                return self._curl_session.post(url, headers=headers_list, json=json_data, timeout=self.timeout)
            return self._curl_session.post(url, headers=headers_list, data=data, timeout=self.timeout)

    def close(self) -> None:
        """Close the HTTP session."""
        if self._curl_session:
            self._curl_session.close()
            self._curl_session = None
        self._tls_session = None

    def __enter__(self) -> "Funda":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    # -------------------------------------------------------------------------
    # Listing methods
    # -------------------------------------------------------------------------

    def get_listing(self, listing_id: int | str) -> Listing:
        """Get a listing by ID or URL.

        Args:
            listing_id: Numeric ID (globalId or tinyId) or full URL

        Returns:
            Listing object with property data

        Example:
            >>> f.get_listing(43117443)
            >>> f.get_listing('https://www.funda.nl/detail/koop/city/house-123/43117443/')
        """
        # If it's a URL, extract tinyId
        if isinstance(listing_id, str) and 'funda.nl' in listing_id:
            match = self.TINYID_PATTERN.search(listing_id)
            if not match:
                raise ValueError(f"Could not extract listing ID from URL: {listing_id}")
            listing_id = match.group(1)

        # Try tinyId endpoint first (8-9 digits), then globalId (7 digits)
        listing_id_str = str(listing_id)
        if len(listing_id_str) >= 8:
            url = API_LISTING_TINY.format(tiny_id=listing_id_str)
        else:
            url = API_LISTING.format(listing_id=listing_id_str)

        headers = _make_headers()
        response = self._get(url, headers)

        # If tinyId fails, try as globalId
        if response.status_code == 404 and len(listing_id_str) >= 8:
            url = API_LISTING.format(listing_id=listing_id_str)
            headers = _make_headers()
            response = self._get(url, headers)

        if response.status_code != 200:
            raise LookupError(f"Listing {listing_id} not found")

        data = response.json()
        return self._parse_listing(data)

    def search_listing(
        self,
        location: str | list[str] | None = None,
        offering_type: str = "buy",
        availability: str | list[str] | None = None,
        price_min: int | None = None,
        price_max: int | None = None,
        area_min: int | None = None,
        area_max: int | None = None,
        plot_min: int | None = None,
        plot_max: int | None = None,
        object_type: list[str] | None = None,
        energy_label: list[str] | None = None,
        radius_km: int | None = None,
        sort: str | None = None,
        page: int = 0,
    ) -> list[Listing]:
        """Search for listings.

        Args:
            location: City/area name(s) or postcode to search in
            offering_type: "buy" or "rent"
            availability: Filter by status - "available", "negotiations", "sold",
                or a list combining them. Default: ["available", "negotiations"]
            price_min: Minimum price
            price_max: Maximum price
            area_min: Minimum living area in m²
            area_max: Maximum living area in m²
            plot_min: Minimum plot area in m²
            plot_max: Maximum plot area in m²
            object_type: Property types (e.g. ["house", "apartment"])
            energy_label: Energy labels (e.g. ["A", "A+", "A++"])
            radius_km: Search radius in km (use with single location/postcode)
            sort: Sort order - "newest", "oldest", "price_asc", "price_desc",
                  "area_asc", "area_desc", "plot_desc", "city", "postcode", or None
            page: Page number (0-indexed, 15 results per page)

        Returns:
            List of Listing objects (max 15 per page)

        Example:
            >>> f.search_listing('amsterdam', price_max=500000)
            >>> f.search_listing('amsterdam', availability='sold')  # sold listings
            >>> f.search_listing('1012AB', radius_km=30, price_max=1250000, energy_label=['A', 'A+'])
        """
        import json

        # Normalize location to list
        locations = None
        if location:
            locations = [location] if isinstance(location, str) else list(location)

        # Normalize availability - map user-friendly "sold" to API's "unavailable"
        if availability is None:
            avail_list = ["available", "negotiations"]
        elif isinstance(availability, str):
            avail_list = [availability]
        else:
            avail_list = list(availability)
        # Map "sold" to "unavailable" (API terminology)
        avail_list = ["unavailable" if v == "sold" else v for v in avail_list]

        # Build search params
        params: dict[str, Any] = {
            "availability": avail_list,
            "type": ["single"],
            "zoning": ["residential"],
            "object_type": object_type or ["house", "apartment"],
            "publication_date": {"no_preference": True},
            "offering_type": offering_type,
            "page": {"from": page * 15},
        }

        # Sort
        sort_map = {
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
        if sort and sort in sort_map:
            field, order = sort_map[sort]
            params["sort"] = {"field": field, "order": order}
        else:
            params["sort"] = {"field": None, "order": None}

        # Location - either radius search or selected_area
        if locations and radius_km and len(locations) == 1:
            # Radius search from postcode or city
            # Valid radius values in the geo index
            valid_radii = [1, 2, 5, 10, 15, 30, 50]
            actual_radius = min(valid_radii, key=lambda x: abs(x - radius_km))
            loc_id = locations[0].lower().replace(" ", "-") + "-0"
            params["radius_search"] = {
                "index": "geo-wonen-alias-prod",
                "id": loc_id,
                "path": f"area_with_radius.{actual_radius}",
            }
        elif locations:
            params["selected_area"] = locations

        # Price filter - format depends on offering type
        if price_min is not None or price_max is not None:
            price_key = "selling_price" if offering_type == "buy" else "rent_price"
            price_filter: dict[str, Any] = {}
            if price_min:
                price_filter["from"] = price_min
            if price_max:
                price_filter["to"] = price_max
            params["price"] = {price_key: price_filter}

        # Living area filter
        if area_min is not None or area_max is not None:
            floor_filter: dict[str, Any] = {}
            if area_min:
                floor_filter["from"] = area_min
            if area_max:
                floor_filter["to"] = area_max
            params["floor_area"] = floor_filter

        # Plot area filter
        if plot_min is not None or plot_max is not None:
            plot_filter: dict[str, Any] = {}
            if plot_min:
                plot_filter["from"] = plot_min
            if plot_max:
                plot_filter["to"] = plot_max
            params["plot_area"] = plot_filter

        # Energy label filter
        if energy_label:
            params["energy_label"] = energy_label

        # Build NDJSON query
        index_line = json.dumps({"index": "listings-wonen-searcher-alias-prod"})
        query_line = json.dumps({"id": "search_result_20250805", "params": params})
        query = f"{index_line}\n{query_line}\n"

        # Retry on intermittent 400 errors from API
        for attempt in range(3):
            headers = _make_headers(for_search=True)
            response = self._post(API_SEARCH, headers, data=query, for_search=True)
            if response.status_code == 200:
                break
            if response.status_code == 400 and attempt < 2:
                time.sleep(0.1 * (attempt + 1))
                continue
            raise RuntimeError(f"Search failed (status {response.status_code})")

        data = response.json()
        return self._parse_search_results(data)

    # -------------------------------------------------------------------------
    # Parsing methods
    # -------------------------------------------------------------------------

    def _parse_listing(self, data: dict) -> Listing:
        """Parse API response into Listing object."""
        identifiers = data.get("Identifiers", {})
        address = data.get("AddressDetails", {})
        price_data = data.get("Price", {})
        coords = data.get("Coordinates", {})
        media = data.get("Media", {})
        fast_view = data.get("FastView", {})
        ads = data.get("Advertising", {}).get("TargetingOptions", {})

        # Build listing data
        listing_data = {
            "global_id": identifiers.get("GlobalId"),
            "tiny_id": identifiers.get("TinyId"),
            "title": address.get("Title"),
            "city": address.get("City"),
            "postcode": address.get("PostCode"),
            "province": address.get("Province"),
            "neighbourhood": address.get("NeighborhoodName"),
            "house_number": address.get("HouseNumber"),
            "house_number_ext": address.get("HouseNumberExtension"),
            "municipality": ads.get("gemeente"),
            "price": price_data.get("NumericSellingPrice") or price_data.get("NumericRentalPrice"),
            "price_formatted": price_data.get("SellingPrice") or price_data.get("RentalPrice"),
            "offering_type": data.get("OfferingType"),
            "object_type": data.get("ObjectType"),
            "construction_type": data.get("ConstructionType"),
            "status": "sold" if data.get("IsSoldOrRented") else "available",
            "energy_label": fast_view.get("EnergyLabel"),
            "living_area": int(ads["woonoppervlakte"]) if ads.get("woonoppervlakte", "").isdigit() else _parse_area(fast_view.get("LivingArea")),
            "living_area_formatted": fast_view.get("LivingArea"),
            "plot_area": int(ads["perceeloppervlakte"]) if ads.get("perceeloppervlakte", "").isdigit() else _parse_area(fast_view.get("PlotArea")),
            "plot_area_formatted": fast_view.get("PlotArea"),
            "bedrooms": fast_view.get("NumberOfBedrooms"),
            "rooms": int(ads["aantalkamers"]) if ads.get("aantalkamers") else None,
            "construction_year": int(ads["bouwjaar"]) if ads.get("bouwjaar") and ads["bouwjaar"].isdigit() else None,
            "description": data.get("ListingDescription", {}).get("Description"),
            "highlight": data.get("Promo", {}).get("Blikvanger", {}).get("Text"),
            "publication_date": data.get("PublicationDate"),
            # Booleans
            "has_garden": ads.get("tuin") == "true",
            "has_balcony": ads.get("balkon") == "true",
            "has_solar_panels": ads.get("zonnepanelen") == "true",
            "has_heat_pump": ads.get("warmtepomp") == "true",
            "has_roof_terrace": ads.get("dakterras") == "true",
            "has_parking_on_site": ads.get("parkeergelegenheidopeigenterrein") == "true",
            "has_parking_enclosed": ads.get("parkeergelegenheidopafgeslotenterrein") == "true",
            "open_house": ads.get("openhuis") == "true",
            "is_auction": price_data.get("IsAuction", False),
            "is_energy_efficient": ads.get("energiezuinig") == "true",
            "is_monument": ads.get("monumentalestatus") == "true",
            "is_fixer_upper": ads.get("kluswoning") == "true",
            "house_type": ads.get("soortwoning"),
            # URLs
            "google_maps_url": data.get("GoogleMapsObjectUrl"),
            "share_url": data.get("Share", {}).get("Url"),
            "brochure_url": media.get("Brochure", {}).get("CdnUrl"),
        }

        # Coordinates
        if coords.get("Latitude") and coords.get("Longitude"):
            listing_data["latitude"] = float(coords["Latitude"])
            listing_data["longitude"] = float(coords["Longitude"])
            listing_data["coordinates"] = (listing_data["latitude"], listing_data["longitude"])

        # Photos - IDs and full URLs
        photos_data = media.get("Photos", {})
        photo_base = photos_data.get("MediaBaseUrl", "").replace("{id}", "{}")
        photo_items = photos_data.get("Items", [])
        listing_data["photos"] = [p.get("Id") for p in photo_items if p.get("Id")]
        listing_data["photo_urls"] = [photo_base.format(p["Id"]) for p in photo_items if p.get("Id")] if photo_base else []
        listing_data["photo_count"] = len(listing_data["photos"])

        # Floorplans
        floorplans_data = media.get("LegacyFloorPlan", {})
        floorplan_base = floorplans_data.get("ThumbnailBaseUrl", "").replace("{id}", "{}")
        floorplan_items = floorplans_data.get("Items", [])
        listing_data["floorplans"] = [f.get("Id") for f in floorplan_items if f.get("Id")]
        listing_data["floorplan_urls"] = [
            floorplan_base.format(f["ThumbnailId"])
            for f in floorplan_items if f.get("ThumbnailId")
        ] if floorplan_base else []

        # Videos
        videos_data = media.get("Videos", {})
        video_base = videos_data.get("MediaBaseUrl", "").replace("{id}", "{}")
        video_items = videos_data.get("Items", [])
        listing_data["videos"] = [v.get("Id") for v in video_items if v.get("Id")]
        listing_data["video_urls"] = [video_base.format(v["Id"]) for v in video_items if v.get("Id")] if video_base else []

        # 360 Photos
        photos360_data = media.get("LegacyPhotos360", {})
        photos360_base = photos360_data.get("ThumbnailBaseUrl", "").replace("{id}", "{}")
        photos360_items = photos360_data.get("Items", [])
        listing_data["photos_360"] = [
            {"name": p.get("DisplayName"), "id": p.get("Id"), "url": photos360_base.format(p["Id"]) if photos360_base else None}
            for p in photos360_items if p.get("Id")
        ]

        # URL
        city_slug = address.get("City", "").lower().replace(" ", "-")
        title_slug = address.get("Title", "").lower().replace(" ", "-")
        tiny_id = identifiers.get("TinyId")
        offering = "koop" if data.get("OfferingType") == "Sale" else "huur"
        listing_data["url"] = f"https://www.funda.nl/detail/{offering}/{city_slug}/{title_slug}/{tiny_id}/"

        # Characteristics
        characteristics = {}
        for section in data.get("KenmerkSections", []):
            for item in section.get("KenmerkenList", []):
                if item.get("Label") and item.get("Value"):
                    characteristics[item["Label"]] = item["Value"]
        listing_data["characteristics"] = characteristics

        # Extract specific fields from characteristics
        listing_data["offered_since"] = characteristics.get("Aangeboden sinds")
        listing_data["acceptance"] = characteristics.get("Aanvaarding")
        listing_data["price_per_m2"] = characteristics.get("Vraagprijs per m²")

        # Broker
        tracking = data.get("Tracking", {}).get("Values", {})
        brokers = tracking.get("brokers", [])
        if brokers:
            listing_data["broker_id"] = brokers[0].get("broker_id")
            listing_data["broker_association"] = brokers[0].get("broker_association")

        # Insights
        insights = data.get("ObjectInsights", {})
        if insights:
            listing_data["views"] = insights.get("Views")
            listing_data["saves"] = insights.get("Saves")

        return Listing(
            listing_id=identifiers.get("TinyId") or identifiers.get("GlobalId"),
            data=listing_data
        )

    def get_latest_id(self) -> int:
        """Get the latest listing ID from ES search.

        Useful as a starting point for poll_new_listings if you don't
        have a saved ID.

        Returns:
            The highest global_id currently in the search index.
        """
        results = self.search_listing(offering_type="buy", sort="newest", page=0)
        if not results:
            raise RuntimeError("Could not fetch latest listings from search")
        return max(int(r["global_id"]) for r in results)

    def poll_new_listings(
        self,
        since_id: int,
        max_consecutive_404s: int = 20,
        offering_type: str | None = None,
    ):
        """Poll for new listings by incrementing IDs.

        Generator that yields listings by directly querying the detail API,
        bypassing ES search. This catches listings that ES hasn't indexed yet.

        Args:
            since_id: Start polling from this ID + 1.
            max_consecutive_404s: Stop after this many consecutive 404s (default 20).
            offering_type: Filter by "buy" or "rent" (default: return all).

        Yields:
            Listing objects as they are found.

        Example:
            >>> f = Funda()
            >>> for listing in f.poll_new_listings(since_id=7852306):
            ...     print(listing['title'], listing['city'])
            ...     save_to_db(listing)  # process immediately
        """
        consecutive_404s = 0
        current_id = since_id + 1

        while consecutive_404s < max_consecutive_404s:
            url = API_LISTING.format(listing_id=current_id)
            try:
                headers = _make_headers()
                response = self._get(url, headers)

                if response.status_code == 200:
                    consecutive_404s = 0
                    data = response.json()

                    # Filter by offering type if specified
                    if offering_type:
                        listing_offering = data.get("OfferingType", "")
                        expected = "Sale" if offering_type == "buy" else "Rental"
                        if listing_offering != expected:
                            current_id += 1
                            continue

                    yield self._parse_listing(data)
                else:
                    consecutive_404s += 1

            except requests.errors.RequestsError:
                consecutive_404s += 1

            current_id += 1

    def get_price_history(self, listing: Listing | str) -> list[dict]:
        """Get historical price data for a listing.

        Fetches price history from Walter Living API, including:
        - Previous asking prices
        - WOZ tax assessments
        - Previous sales

        Args:
            listing: A Listing object or Funda URL string

        Returns:
            List of price changes, each containing:
            - price: Numeric price
            - human_price: Formatted price (e.g., "€400.000")
            - date: Human readable date
            - timestamp: ISO timestamp
            - source: "Funda" or "WOZ"
            - status: "asking_price", "sold", or "woz"

        Example:
            >>> listing = f.get_listing(89666837)
            >>> history = f.get_price_history(listing)
            >>> for change in history:
            ...     print(change['date'], change['human_price'], change['status'])
            15 jan, 2026 €400.000 asking_price
            1 jan, 2025 €376.000 woz
            8 mrt, 2023 €325.000 asking_price
        """
        # Extract data from Listing or fetch if URL provided
        if isinstance(listing, str):
            listing = self.get_listing(listing)

        url = listing.get("url")
        address = listing.get("title")
        postcode = listing.get("postcode")

        if not all([url, address, postcode]):
            raise ValueError("Listing must have url, title (address), and postcode")

        payload = {
            "url": url,
            "address": address,
            "zipcode": postcode,
        }

        walter_headers = [
            ("Accept", "application/json"),
            ("Content-Type", "application/json"),
        ]
        response = self._post(API_WALTER, walter_headers, json_data=payload)

        if response.status_code != 200:
            raise LookupError(f"Could not fetch price history (status {response.status_code})")

        data = response.json()
        if data.get("status") != "ok":
            raise LookupError("Price history not available for this listing")

        # Translate Dutch status to English
        status_map = {
            "Vraagprijs": "asking_price",
            "Verkocht": "sold",
            "WOZ": "woz",
        }

        changes = data.get("changes", [])
        for change in changes:
            if "status" in change:
                change["status"] = status_map.get(change["status"], change["status"])

        return changes

    def _parse_search_results(self, data: dict) -> list[Listing]:
        """Parse search API response into list of Listings."""
        listings = []
        responses = data.get("responses", [])

        if not responses:
            return listings

        hits = responses[0].get("hits", {}).get("hits", [])

        for hit in hits:
            source = hit.get("_source", {})
            address = source.get("address", {})

            # Price
            price_data = source.get("price", {})
            if isinstance(price_data, dict):
                price = price_data.get("selling_price", [None])[0]
                if not price:
                    price = price_data.get("rent_price", [None])[0] if price_data.get("rent_price") else None
            else:
                price = price_data

            listing_data = {
                "global_id": int(hit.get("_id", 0)),
                "title": f"{address.get('street_name', '')} {address.get('house_number', '')}".strip(),
                "city": address.get("city"),
                "postcode": address.get("postal_code"),
                "province": address.get("province"),
                "neighbourhood": address.get("neighbourhood"),
                "price": price,
                "living_area": source.get("floor_area", [None])[0] if source.get("floor_area") else None,
                "plot_area": source.get("plot_area_range", {}).get("gte"),
                "bedrooms": source.get("number_of_bedrooms"),
                "energy_label": source.get("energy_label"),
                "object_type": source.get("object_type"),
                "construction_type": source.get("construction_type"),
                "photos": source.get("thumbnail_id", [])[:5],
            }

            listings.append(Listing(
                listing_id=hit.get("_id"),
                data=listing_data
            ))

        return listings


# Convenience alias
FundaAPI = Funda
