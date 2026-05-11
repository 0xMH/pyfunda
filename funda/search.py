"""Search payload construction."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from typing import Any

from funda.constants import (
    CONSTRUCTION_PERIODS,
    PAGE_SIZE,
    SEARCH_INDEX,
    SEARCH_TEMPLATE_ID,
    SORT_OPTIONS,
    VALID_AVAILABILITY,
    VALID_RADII,
)
from funda.models import JsonDict


_TextValues = str | Sequence[str] | None
_VALID_CATEGORIES = {"buy", "rent", "sold"}

_RANGE_FILTERS = {
    "price": ("min_price", "max_price"),
    "area": ("min_area", "max_area"),
    "plot": ("min_plot", "max_plot"),
    "rooms": ("min_rooms", "max_rooms"),
    "bedrooms": ("min_bedrooms", "max_bedrooms"),
    "construction_year": ("min_construction_year", "max_construction_year"),
}

_VALUE_FILTERS = {
    "category",
    "status",
    "object_type",
    "energy_label",
    "construction_type",
    "radius_km",
    "sort",
    "page",
}


@dataclass(frozen=True, slots=True)
class _Bounds:
    minimum: int | None = None
    maximum: int | None = None

    def __post_init__(self) -> None:
        if (
            self.minimum is not None
            and self.maximum is not None
            and self.minimum > self.maximum
        ):
            raise ValueError("minimum must be <= maximum")

    def __bool__(self) -> bool:
        return self.minimum is not None or self.maximum is not None

    def to_params(self) -> dict[str, int]:
        params: dict[str, int] = {}
        if self.minimum is not None:
            params["from"] = self.minimum
        if self.maximum is not None:
            params["to"] = self.maximum
        return params

    def add_to(self, params: JsonDict, key: str) -> None:
        if self:
            params[key] = self.to_params()


@dataclass(frozen=True, slots=True)
class _ConstructionYearBounds(_Bounds):
    def to_period_keys(self) -> list[str]:
        return [
            period.key
            for period in CONSTRUCTION_PERIODS
            if period.overlaps(self.minimum, self.maximum)
        ]


@dataclass(frozen=True, slots=True)
class _Search:
    location: _TextValues = None
    category: str = "buy"
    status: _TextValues = None
    price: _Bounds = field(default_factory=_Bounds)
    area: _Bounds = field(default_factory=_Bounds)
    plot: _Bounds = field(default_factory=_Bounds)
    rooms: _Bounds = field(default_factory=_Bounds)
    bedrooms: _Bounds = field(default_factory=_Bounds)
    object_type: _TextValues = None
    energy_label: _TextValues = None
    construction_type: _TextValues = None
    construction_year: _ConstructionYearBounds = field(
        default_factory=_ConstructionYearBounds
    )
    radius_km: int | None = None
    sort: str | None = None
    page: int = 0

    @classmethod
    def from_filters(cls, location: _TextValues = None, **filters: Any) -> "_Search":
        values = {name: filters.pop(name, None) for name in _VALUE_FILTERS}
        values["category"] = str(values["category"] or "buy").lower()
        values["page"] = values["page"] or 0

        bounds: dict[str, _Bounds] = {}
        for field_name, (min_name, max_name) in _RANGE_FILTERS.items():
            bounds_type = (
                _ConstructionYearBounds if field_name == "construction_year" else _Bounds
            )
            bounds[field_name] = bounds_type(
                filters.pop(min_name, None),
                filters.pop(max_name, None),
            )

        if filters:
            names = ", ".join(sorted(filters))
            raise TypeError(f"unknown search filter(s): {names}")

        return cls(location=location, **values, **bounds)

    def with_page(self, page: int) -> "_Search":
        return replace(self, page=page)

    def to_payload(self) -> str:
        params = self.to_params()
        index_line = json.dumps({"index": SEARCH_INDEX})
        query_line = json.dumps({"id": SEARCH_TEMPLATE_ID, "params": params})
        return f"{index_line}\n{query_line}\n"

    @property
    def offering(self) -> str:
        return "rent" if self.category == "rent" else "buy"

    @property
    def availability(self) -> _TextValues:
        return "sold" if self.category == "sold" else self.status

    def to_params(self) -> JsonDict:
        self._validate()
        locations = self._text_values(self.location)

        params: JsonDict = {
            "availability": self._availability_values(),
            "type": ["single"],
            "zoning": ["residential"],
            "object_type": self._text_values(self.object_type)
            or ["house", "apartment"],
            "publication_date": {"no_preference": True},
            "offering_type": self.offering,
            "page": {"from": self.page * PAGE_SIZE},
            "sort": self._sort_params(),
        }

        self._add_location(params, locations)
        self._add_bounds(params)
        self._add_optional_values(params)
        return params

    def _validate(self) -> None:
        if self.page < 0:
            raise ValueError("page must be >= 0")
        if self.category not in _VALID_CATEGORIES:
            raise ValueError("category must be 'buy', 'rent', or 'sold'")

        if self.category == "sold" and self._text_values(self.status) not in (
            None,
            ["sold"],
        ):
            raise ValueError("category='sold' cannot be combined with status")

        status = self._status_values(self.availability)
        invalid_status = sorted(set(status) - set(VALID_AVAILABILITY))
        if invalid_status:
            raise ValueError(f"invalid status values: {invalid_status}")

        locations = self._text_values(self.location)
        if self.radius_km is not None and (not locations or len(locations) != 1):
            raise ValueError("radius_km requires exactly one location")

    def _add_location(self, params: JsonDict, locations: list[str] | None) -> None:
        if locations and self.radius_km is not None:
            params["radius_search"] = self._radius_params(locations[0])
        elif locations:
            params["selected_area"] = [location.lower() for location in locations]

    def _add_bounds(self, params: JsonDict) -> None:
        self.area.add_to(params, "floor_area")
        self.plot.add_to(params, "plot_area")
        self.rooms.add_to(params, "rooms")
        self.bedrooms.add_to(params, "bedrooms")

        if self.price:
            price_key = "selling_price" if self.offering == "buy" else "rent_price"
            params["price"] = {price_key: self.price.to_params()}

        if self.construction_year:
            periods = self.construction_year.to_period_keys()
            if periods:
                params["construction_period"] = periods

    def _add_optional_values(self, params: JsonDict) -> None:
        energy_label = self._text_values(self.energy_label)
        if energy_label:
            params["energy_label"] = energy_label

        construction_type = self._text_values(self.construction_type)
        if construction_type:
            params["construction_type"] = construction_type

    def _availability_values(self) -> list[str]:
        return [
            "unavailable" if value == "sold" else value
            for value in self._status_values(self.availability)
        ]

    def _sort_params(self) -> JsonDict:
        if not self.sort:
            return {"field": None, "order": None}
        if self.sort not in SORT_OPTIONS:
            raise ValueError(f"invalid sort value: {self.sort!r}")
        field, order = SORT_OPTIONS[self.sort]
        return {"field": field, "order": order}

    def _radius_params(self, location: str) -> JsonDict:
        if self.radius_km is None:
            raise ValueError("radius_km is required")

        radius = min(
            VALID_RADII,
            key=lambda valid_radius: abs(valid_radius - self.radius_km),
        )
        return {
            "index": "geo-wonen-alias-prod",
            "id": location.lower().replace(" ", "-") + "-0",
            "path": f"area_with_radius.{radius}",
        }

    @staticmethod
    def _status_values(status: _TextValues) -> list[str]:
        if status is None:
            return ["available", "negotiations"]
        return _Search._text_values(status) or []

    @staticmethod
    def _text_values(value: _TextValues) -> list[str] | None:
        if value is None:
            return None
        if isinstance(value, str):
            return [value]
        return list(value)
