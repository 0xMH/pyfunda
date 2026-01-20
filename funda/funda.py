"""Main Funda API class."""

import re
import time
from typing import Any

from curl_cffi import requests

from funda.listing import Listing


# API endpoints
API_BASE = "https://listing-detail-page.funda.io/api/v4/listing/object/nl"
API_LISTING = f"{API_BASE}/{{listing_id}}"
API_LISTING_TINY = f"{API_BASE}/tinyId/{{tiny_id}}"
API_SEARCH = "https://listing-search-wonen.funda.io/_msearch/template"

# Headers for mobile API
HEADERS = {
    "user-agent": "Dart/3.9 (dart:io)",
    "x-funda-app-platform": "android",
    "content-type": "application/json",
}

SEARCH_HEADERS = {
    "user-agent": "Dart/3.9 (dart:io)",
    "content-type": "application/json",
    "accept": "application/json",
    "referer": "https://www.funda.nl/",
}


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
        self._session: requests.Session | None = None

    @property
    def session(self) -> requests.Session:
        """Lazily create HTTP session."""
        if self._session is None:
            self._session = requests.Session(impersonate="chrome")
            self._session.headers.update(HEADERS)
        return self._session

    def close(self) -> None:
        """Close the HTTP session."""
        if self._session:
            self._session.close()
            self._session = None

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

        response = self.session.get(url, timeout=self.timeout)

        # If tinyId fails, try as globalId
        if response.status_code == 404 and len(listing_id_str) >= 8:
            url = API_LISTING.format(listing_id=listing_id_str)
            response = self.session.get(url, timeout=self.timeout)

        if response.status_code != 200:
            raise LookupError(f"Listing {listing_id} not found")

        data = response.json()
        return self._parse_listing(data)

    def search_listing(
        self,
        location: str | list[str] | None = None,
        offering_type: str = "buy",
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
            >>> f.search_listing('1012AB', radius_km=30, price_max=1250000, energy_label=['A', 'A+'])
        """
        import json

        # Normalize location to list
        locations = None
        if location:
            locations = [location] if isinstance(location, str) else list(location)

        # Build search params
        params: dict[str, Any] = {
            "availability": ["available", "negotiations"],
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
            response = self.session.post(
                API_SEARCH,
                headers=SEARCH_HEADERS,
                data=query,
                timeout=self.timeout,
            )
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
                response = self.session.get(url, timeout=self.timeout)

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

            except requests.RequestException:
                consecutive_404s += 1

            current_id += 1

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
