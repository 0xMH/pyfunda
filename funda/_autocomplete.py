"""Internal autocomplete payload construction."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from funda.constants import (
    LOCATION_AUTOCOMPLETE_AREA_TYPES,
    LOCATION_AUTOCOMPLETE_TEMPLATE_ID,
)
from funda.models import JsonDict


@dataclass(frozen=True, slots=True)
class LocationAutocomplete:
    value: str
    timeout: str = "3s"
    size: int = 10
    use_sort: bool = False
    sort: Sequence[Any] = ()
    exclude: Sequence[str] = ()
    area_types: Sequence[str] = LOCATION_AUTOCOMPLETE_AREA_TYPES

    def to_payload(self) -> JsonDict:
        self._validate()
        return {
            "id": LOCATION_AUTOCOMPLETE_TEMPLATE_ID,
            "params": {
                "value": self.value.strip(),
                "timeout": self.timeout,
                "size": self.size,
                "use_sort": self.use_sort,
                "sort": list(self.sort),
                "exclude": list(self.exclude),
                "area_types": list(self.area_types),
            },
        }

    def _validate(self) -> None:
        if not self.value.strip():
            raise ValueError("value must not be empty")
        if not self.timeout:
            raise ValueError("timeout must not be empty")
        if self.size < 1:
            raise ValueError("size must be >= 1")
