"""Parser for Funda location autocomplete payloads."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from funda._parse_helpers import as_str, mapping, parse_float
from funda.listing import GeoLocation, LocationArea, LocationSuggestion


def parse_location_suggestions(data: Mapping[str, Any]) -> list[LocationSuggestion]:
    hits = mapping(data.get("hits")).get("hits") or []
    return [_hit(hit) for hit in hits if isinstance(hit, Mapping)]


def _hit(hit: Mapping[str, Any]) -> LocationSuggestion:
    source = mapping(hit.get("_source"))
    parent_areas = source.get("parent_areas")
    synonyms = source.get("synonyms")
    parent_area_values = parent_areas if isinstance(parent_areas, list) else []
    synonym_values = synonyms if isinstance(synonyms, list) else []
    return LocationSuggestion(
        id=as_str(source.get("id") or hit.get("_id")),
        name=as_str(source.get("name")),
        geo_identifier=as_str(source.get("geo_identifier")),
        area_type=as_str(source.get("area_type")),
        parent=_area(source.get("parent")),
        parent_areas=tuple(
            area
            for area in (_area(value) for value in parent_area_values)
            if area is not None
        ),
        synonyms=tuple(
            str(value) for value in synonym_values if value is not None
        ),
        location=_location(source.get("centroid")),
        score=parse_float(hit.get("_score")),
        raw=dict(hit),
    )


def _area(value: Any) -> LocationArea | None:
    area = mapping(value)
    if not area:
        return None
    return LocationArea(
        name=as_str(area.get("name")),
        geo_identifier=as_str(area.get("geo_identifier")),
        area_type=as_str(area.get("area_type")),
        raw=dict(area),
    )


def _location(value: Any) -> GeoLocation:
    if not isinstance(value, str):
        return GeoLocation(raw={"centroid": value} if value is not None else {})

    latitude, _, longitude = value.partition(",")
    return GeoLocation(
        latitude=parse_float(latitude),
        longitude=parse_float(longitude),
        raw={"centroid": value},
    )
