"""
Funda - Python API for Funda.nl real estate listings.

Example usage:
    >>> from funda import Funda
    >>> f = Funda()
    >>> listing = f.listing(43117443)
    >>> print(listing.title, listing.price.amount)
    Reehorst 13 695000

    >>> results = f.search('amsterdam', max_price=500000)
    >>> for listing in results[:3]:
    ...     print(listing.title, listing.city)
"""

from importlib.metadata import version

from funda.constants import CONSTRUCTION_PERIODS
from funda.exceptions import (
    FingerprintError,
    FundaError,
    FundaRequestError,
    ListingNotFound,
    PriceHistoryError,
    SearchError,
)
from funda.funda import Funda
from funda.listing import (
    Address,
    Areas,
    Broker,
    Characteristic,
    CharacteristicSection,
    GeoLocation,
    Insights,
    Label,
    Listing,
    Media,
    MediaItem,
    Price,
    PriceChange,
    PriceHistory,
    Project,
    PropertyDetails,
    Rooms,
    SalesHistory,
    Urls,
)
from funda.models import ConstructionPeriod, Fingerprint

__version__ = version("pyfunda")
__all__ = [
    "CONSTRUCTION_PERIODS",
    "Address",
    "Areas",
    "Broker",
    "Characteristic",
    "CharacteristicSection",
    "ConstructionPeriod",
    "Fingerprint",
    "FingerprintError",
    "Funda",
    "FundaError",
    "FundaRequestError",
    "GeoLocation",
    "Insights",
    "Label",
    "Listing",
    "ListingNotFound",
    "Media",
    "MediaItem",
    "Price",
    "PriceChange",
    "PriceHistory",
    "PriceHistoryError",
    "Project",
    "PropertyDetails",
    "Rooms",
    "SalesHistory",
    "SearchError",
    "Urls",
    "__version__",
]
