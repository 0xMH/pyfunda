"""Parser for Walter Living price-history payloads."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from funda._parse_helpers import mapping, parse_int
from funda.listing import PriceChange, PriceHistory


def parse_price_history(data: Mapping[str, Any]) -> PriceHistory:
    report = mapping(data.get("report"))
    return PriceHistory(
        status=data.get("status"),
        url=data.get("url"),
        report_token=report.get("token"),
        report_slug=report.get("slug"),
        report_url=report.get("url"),
        changes=tuple(
            _change(change)
            for change in data.get("changes", [])
            if isinstance(change, Mapping)
        ),
        trigger_popup=data.get("trigger_popup"),
        listing_count=parse_int(data.get("listing_count")),
        raw=dict(data),
    )


def _change(change: Mapping[str, Any]) -> PriceChange:
    status_map = {
        "Vraagprijs": "asking_price",
        "Verkocht": "sold",
        "WOZ": "woz",
    }
    status = change.get("status")
    return PriceChange(
        price=parse_int(change.get("price")),
        human_price=change.get("human_price"),
        badge_text=change.get("badge_text"),
        source=change.get("source"),
        status=status_map.get(status, status),
        date=change.get("date"),
        timestamp=change.get("timestamp"),
        raw=dict(change),
    )
