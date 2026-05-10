"""Shared parser helpers for Funda response payloads."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


_ID_IN_URL = re.compile(r"/(\d{7,9})/?(?:\?|$|#)")


def mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def first(value: Any) -> Any:
    return value[0] if isinstance(value, list) and value else value


def coalesce(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None


def as_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def parse_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    cleaned = str(value).strip().replace(".", "").replace(" ", "")
    return int(cleaned) if cleaned.isdigit() else None


def parse_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    normalized = str(value).strip().casefold()
    if normalized in {"true", "1", "yes", "ja"}:
        return True
    if normalized in {"false", "0", "no", "nee"}:
        return False
    return None


def parse_area(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return int(value)
    cleaned = (
        str(value)
        .replace("m²", "")
        .replace("m³", "")
        .replace(".", "")
        .replace(",", "")
        .strip()
    )
    return int(cleaned) if cleaned.isdigit() else None


def parse_rooms(value: Any) -> int | None:
    if value is None:
        return None
    match = re.search(r"\d+", str(value))
    return int(match.group(0)) if match else None


def tiny_id_from_url(url: Any) -> str | None:
    if not isinstance(url, str):
        return None
    match = _ID_IN_URL.search(url)
    return match.group(1) if match else None


def normalize_offering_type(value: Any) -> str | None:
    if isinstance(value, list):
        value = first(value)
    if value is None:
        return None
    normalized = str(value).casefold()
    if normalized in {"sale", "buy", "koop"}:
        return "buy"
    if normalized in {"rental", "rent", "huur"}:
        return "rent"
    return str(value)


def normalize_object_type(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).casefold()
    if normalized in {"house", "huis"}:
        return "house"
    if normalized in {"apartment", "appartement"}:
        return "apartment"
    return str(value)


def normalize_construction_type(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).casefold()
    if normalized in {"existingconstruction", "resale", "bestaande bouw"}:
        return "existing"
    if normalized in {"newconstruction", "newly_built", "nieuwbouw"}:
        return "new"
    return str(value)


def normalize_status(value: Any, offering_type: Any = None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().casefold()
    if normalized in {"", "none"}:
        return None
    if normalized in {"beschikbaar", "available"}:
        return "available"
    if normalized in {"onder bod", "negotiations"}:
        return "negotiations"
    if normalized in {"verkocht", "sold", "unavailable"}:
        return "rented" if normalize_offering_type(offering_type) == "rent" else "sold"
    if normalized in {"verhuurd", "rented"}:
        return "rented"
    return str(value)


def search_title(address: Mapping[str, Any]) -> str | None:
    street = address.get("street_name") or ""
    number = as_str(address.get("house_number")) or ""
    suffix = address.get("house_number_suffix") or ""
    title = f"{street} {number}".strip()
    if number and suffix:
        return f"{title}-{suffix}"
    return f"{title} {suffix}".strip() or None


def fallback_url(
    address: Mapping[str, Any],
    listing_id: str | None,
    offering_type: str | None,
) -> str | None:
    if not listing_id:
        return None
    city_slug = slug(address.get("City"))
    title_slug = slug(address.get("Title"))
    offering = "huur" if offering_type == "rent" else "koop"
    return f"https://www.funda.nl/detail/{offering}/{city_slug}/{title_slug}/{listing_id}/"


def media_url(template: Any, media_id: str | None) -> str | None:
    if not template or not media_id:
        return None
    return str(template).replace("{id}", media_id)


def slug(value: Any) -> str:
    return str(value or "").lower().replace(" ", "-")
