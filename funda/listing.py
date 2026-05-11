"""Typed value objects returned by the public Funda client."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import asdict, dataclass, field
from typing import Any, Literal


ListingSource = Literal["detail", "search", "summary"]
JsonDict = dict[str, Any]


class DictValue:
    """Small mixin for exporting nested dataclasses."""

    def to_dict(self, *, include_raw: bool = False) -> JsonDict:
        data = asdict(self)
        if not include_raw:
            self._drop_raw(data)
        return data

    @staticmethod
    def _drop_raw(value: Any) -> None:
        if isinstance(value, dict):
            value.pop("raw", None)
            for child in value.values():
                DictValue._drop_raw(child)
        elif isinstance(value, list | tuple):
            for child in value:
                DictValue._drop_raw(child)


@dataclass(frozen=True, slots=True)
class Address(DictValue):
    title: str | None = None
    subtitle: str | None = None
    street_name: str | None = None
    house_number: str | None = None
    house_number_suffix: str | None = None
    postcode: str | None = None
    city: str | None = None
    municipality: str | None = None
    neighbourhood: str | None = None
    neighbourhood_identifier: str | None = None
    province: str | None = None
    country: str | None = None
    is_international: bool | None = None
    is_bag_address: bool | None = None
    identifiers: tuple[str, ...] = ()
    raw: JsonDict = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class GeoLocation(DictValue):
    latitude: float | None = None
    longitude: float | None = None
    google_maps_url: str | None = None
    raw: JsonDict = field(default_factory=dict, repr=False, compare=False)

    @property
    def coordinates(self) -> tuple[float, float] | None:
        if self.latitude is None or self.longitude is None:
            return None
        return self.latitude, self.longitude


@dataclass(frozen=True, slots=True)
class LocationArea(DictValue):
    name: str | None = None
    geo_identifier: str | None = None
    area_type: str | None = None
    raw: JsonDict = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class LocationSuggestion(DictValue):
    id: str | None = None
    name: str | None = None
    geo_identifier: str | None = None
    area_type: str | None = None
    parent: LocationArea | None = None
    parent_areas: tuple[LocationArea, ...] = ()
    synonyms: tuple[str, ...] = ()
    location: GeoLocation = field(default_factory=GeoLocation)
    score: float | None = None
    raw: JsonDict = field(default_factory=dict, repr=False, compare=False)

    @property
    def label(self) -> str | None:
        if not self.name:
            return None
        if self.parent and self.parent.name and self.parent.name != self.name:
            return f"{self.name}, {self.parent.name}"
        return self.name


@dataclass(frozen=True, slots=True)
class Urls(DictValue):
    full: str | None = None
    path: str | None = None
    share: str | None = None
    raw: JsonDict = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class Price(DictValue):
    amount: int | None = None
    formatted: str | None = None
    offering_type: str | None = None
    condition: str | None = None
    price_type: str | None = None
    range_min: int | None = None
    range_max: int | None = None
    is_auction: bool = False
    raw: JsonDict = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class Areas(DictValue):
    living: int | None = None
    plot: int | None = None
    other_indoor: int | None = None
    building_bound_outdoor: int | None = None
    external_storage: int | None = None
    volume: int | None = None
    living_formatted: str | None = None
    plot_formatted: str | None = None
    living_range_min: int | None = None
    living_range_max: int | None = None
    plot_range_min: int | None = None
    plot_range_max: int | None = None
    raw: JsonDict = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class Rooms(DictValue):
    total: int | None = None
    bedrooms: int | None = None
    bathrooms_description: str | None = None
    floors_description: str | None = None
    located_on: str | None = None
    raw: JsonDict = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class PropertyDetails(DictValue):
    object_type: str | None = None
    construction_type: str | None = None
    construction_year: int | None = None
    building_type: str | None = None
    house_type: str | None = None
    energy_label: str | None = None
    status: str | None = None
    raw_object_type: str | None = None
    raw_construction_type: str | None = None
    raw_offering_type: str | None = None
    raw_status: str | None = None
    features: JsonDict = field(default_factory=dict)
    raw: JsonDict = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class Broker(DictValue):
    id: str | None = None
    office_id: str | None = None
    name: str | None = None
    association: str | None = None
    relative_url: str | None = None
    logo_id: str | None = None
    is_primary: bool | None = None
    raw: JsonDict = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class MediaItem(DictValue):
    id: str | None = None
    display_name: str | None = None
    url: str | None = None
    thumbnail_url: str | None = None
    embed_url: str | None = None
    raw: JsonDict = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class Media(DictValue):
    photos: tuple[MediaItem, ...] = ()
    floorplans: tuple[MediaItem, ...] = ()
    photos_360: tuple[MediaItem, ...] = ()
    videos: tuple[MediaItem, ...] = ()
    virtual_tours: tuple[MediaItem, ...] = ()
    brochure_url: str | None = None
    layout: JsonDict = field(default_factory=dict)
    available_types: tuple[str, ...] = ()
    raw: JsonDict = field(default_factory=dict, repr=False, compare=False)

    @property
    def photo_count(self) -> int:
        return len(self.photos)

    @property
    def photo_ids(self) -> tuple[str, ...]:
        return tuple(item.id for item in self.photos if item.id)

    @property
    def photo_urls(self) -> tuple[str, ...]:
        return tuple(item.url for item in self.photos if item.url)


@dataclass(frozen=True, slots=True)
class Label(DictValue):
    text: str | None = None
    type: str | None = None
    raw: JsonDict = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class Characteristic(DictValue):
    section: str | None = None
    id: str | None = None
    label: str | None = None
    value: Any = None
    label_style: str | None = None
    children: tuple["Characteristic", ...] = ()
    raw: JsonDict = field(default_factory=dict, repr=False, compare=False)

    def walk(self) -> Iterator["Characteristic"]:
        yield self
        for child in self.children:
            yield from child.walk()


@dataclass(frozen=True, slots=True)
class CharacteristicSection(DictValue):
    title: str | None = None
    items: tuple[Characteristic, ...] = ()
    raw: JsonDict = field(default_factory=dict, repr=False, compare=False)

    def get(self, label: str, default: Any = None) -> Any:
        needle = label.casefold()
        for root in self.items:
            for item in root.walk():
                if item.label and item.label.casefold() == needle:
                    return item.value
        return default


@dataclass(frozen=True, slots=True)
class SalesHistory(DictValue):
    title: str | None = None
    rows: tuple[Characteristic, ...] = ()
    raw: JsonDict = field(default_factory=dict, repr=False, compare=False)

    @property
    def summary(self) -> JsonDict:
        return {row.label: row.value for row in self.rows if row.label}

    @property
    def sale_date(self) -> Any:
        return self.summary.get("Verkoopdatum")

    @property
    def time_on_market(self) -> Any:
        return self.summary.get("Looptijd")


@dataclass(frozen=True, slots=True)
class Project(DictValue):
    global_id: int | None = None
    tiny_id: str | None = None
    title: str | None = None
    city: str | None = None
    type: str | None = None
    status: str | None = None
    url: str | None = None
    price: Price | None = None
    address: Address | None = None
    raw: JsonDict = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class Insights(DictValue):
    views: int | None = None
    saves: int | None = None
    raw: JsonDict = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class Listing(DictValue):
    listing_id: str | None = None
    source: ListingSource = "detail"
    global_id: int | None = None
    tiny_id: str | None = None
    offering_type: str | None = None
    address: Address = field(default_factory=Address)
    price: Price = field(default_factory=Price)
    areas: Areas = field(default_factory=Areas)
    rooms: Rooms = field(default_factory=Rooms)
    property_details: PropertyDetails = field(default_factory=PropertyDetails)
    location: GeoLocation = field(default_factory=GeoLocation)
    urls: Urls = field(default_factory=Urls)
    media: Media = field(default_factory=Media)
    brokers: tuple[Broker, ...] = ()
    labels: tuple[Label, ...] = ()
    description: str | None = None
    description_title: str | None = None
    highlight: str | None = None
    publication_date: str | None = None
    characteristics: tuple[CharacteristicSection, ...] = ()
    sales_history: SalesHistory | None = None
    parent_project: Project | None = None
    insights: Insights | None = None
    raw: JsonDict = field(default_factory=dict, repr=False, compare=False)

    def __repr__(self) -> str:
        return f"Listing(id={self.id!r}, title={self.title!r}, city={self.city!r})"

    @property
    def id(self) -> str | None:
        if self.tiny_id is not None:
            return self.tiny_id
        if self.global_id is not None:
            return str(self.global_id)
        return self.listing_id

    @property
    def title(self) -> str | None:
        return self.address.title

    @property
    def city(self) -> str | None:
        return self.address.city

    @property
    def postcode(self) -> str | None:
        return self.address.postcode

    @property
    def url(self) -> str | None:
        return self.urls.full

    @property
    def detail_url(self) -> str | None:
        return self.urls.path

    @property
    def broker(self) -> Broker | None:
        return self.brokers[0] if self.brokers else None

    @property
    def living_area(self) -> int | None:
        return self.areas.living

    @property
    def plot_area(self) -> int | None:
        return self.areas.plot

    @property
    def rooms_count(self) -> int | None:
        return self.rooms.total

    @property
    def bedrooms(self) -> int | None:
        return self.rooms.bedrooms

    @property
    def energy_label(self) -> str | None:
        return self.property_details.energy_label

    @property
    def status(self) -> str | None:
        return self.property_details.status

    def characteristic(self, label: str, default: Any = None) -> Any:
        missing = object()
        for section in self.characteristics:
            value = section.get(label, missing)
            if value is not missing:
                return value
        return default


@dataclass(frozen=True, slots=True)
class PriceChange(DictValue):
    price: int | None = None
    human_price: str | None = None
    badge_text: str | None = None
    source: str | None = None
    status: str | None = None
    date: str | None = None
    timestamp: str | None = None
    raw: JsonDict = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class PriceHistory(DictValue):
    status: str | None = None
    url: str | None = None
    report_token: str | None = None
    report_slug: str | None = None
    report_url: str | None = None
    changes: tuple[PriceChange, ...] = ()
    trigger_popup: bool | None = None
    listing_count: int | None = None
    raw: JsonDict = field(default_factory=dict, repr=False, compare=False)
