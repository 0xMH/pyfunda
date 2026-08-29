"""Decode the server-rendered Nuxt search payload used by funda.nl."""

import json
import math
from html.parser import HTMLParser
from typing import Any


class NuxtPayloadError(RuntimeError):
    """Raised when the Funda Nuxt search payload cannot be decoded."""


class _NuxtDataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_script = False
        self._is_nuxt_data = False
        self._parts: list[str] = []
        self.payload: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "script":
            return
        attributes = dict(attrs)
        self._in_script = True
        self._is_nuxt_data = attributes.get("id") == "__NUXT_DATA__"
        self._parts = []

    def handle_data(self, data: str) -> None:
        if self._in_script and self._is_nuxt_data:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "script" or not self._in_script:
            return
        if self._is_nuxt_data:
            self.payload = "".join(self._parts)
        self._in_script = False
        self._is_nuxt_data = False
        self._parts = []


def _decode_nuxt_values(values: list[Any]) -> Any:
    """Resolve Nuxt/devalue references into regular Python values."""
    memo: dict[int, Any] = {}
    sentinels = {
        -1: None,
        -2: None,
        -3: math.nan,
        -4: math.inf,
        -5: -math.inf,
        -6: -0.0,
    }
    wrappers = {"Reactive", "ShallowReactive", "Ref", "EmptyRef"}

    def decode(index: int) -> Any:
        if index < 0:
            return sentinels.get(index)
        if index >= len(values):
            raise NuxtPayloadError(f"Nuxt payload reference {index} is out of range")
        if index in memo:
            return memo[index]

        value = values[index]
        if isinstance(value, list):
            tag = value[0] if value and isinstance(value[0], str) else None
            if tag in wrappers:
                if len(value) < 2 or not isinstance(value[1], int):
                    raise NuxtPayloadError(f"Malformed Nuxt {tag} value")
                result = decode(value[1])
                memo[index] = result
                return result
            if tag == "Set":
                result: set[Any] = set()
                memo[index] = result
                for item in value[1:]:
                    result.add(decode(item) if isinstance(item, int) else item)
                return result
            if tag == "Map":
                result_map: dict[Any, Any] = {}
                memo[index] = result_map
                entries = value[1:]
                for offset in range(0, len(entries) - 1, 2):
                    key = entries[offset]
                    item = entries[offset + 1]
                    decoded_key = decode(key) if isinstance(key, int) else key
                    decoded_item = decode(item) if isinstance(item, int) else item
                    result_map[decoded_key] = decoded_item
                return result_map
            if tag == "Date" and len(value) > 1:
                item = value[1]
                result = decode(item) if isinstance(item, int) else item
                memo[index] = result
                return result
            if tag == "BigInt" and len(value) > 1:
                item = value[1]
                result = int(decode(item) if isinstance(item, int) else item)
                memo[index] = result
                return result

            result_list: list[Any] = []
            memo[index] = result_list
            result_list.extend(
                decode(item) if isinstance(item, int) else item for item in value
            )
            return result_list

        if isinstance(value, dict):
            result_dict: dict[str, Any] = {}
            memo[index] = result_dict
            for key, item in value.items():
                result_dict[key] = decode(item) if isinstance(item, int) else item
            return result_dict

        memo[index] = value
        return value

    return decode(0)


def extract_search_state(page: str) -> dict[str, Any]:
    """Return the Pinia search state embedded in a Funda search page."""
    parser = _NuxtDataParser()
    parser.feed(page)
    if not parser.payload:
        raise NuxtPayloadError("Funda search page contains no __NUXT_DATA__ payload")

    try:
        values = json.loads(parser.payload)
    except json.JSONDecodeError as exc:
        raise NuxtPayloadError("Funda search page contains invalid Nuxt JSON") from exc
    if not isinstance(values, list):
        raise NuxtPayloadError("Funda Nuxt payload is not a reference array")

    root = _decode_nuxt_values(values)
    try:
        search = root["pinia"]["search"]
    except (KeyError, TypeError) as exc:
        raise NuxtPayloadError("Funda Nuxt payload contains no search state") from exc

    required = {"criteria", "listings", "totalListingsCount"}
    if not isinstance(search, dict) or not required.issubset(search):
        raise NuxtPayloadError("Funda Nuxt search state has an unexpected shape")
    if not isinstance(search["listings"], list):
        raise NuxtPayloadError("Funda Nuxt listings value is not a list")
    return search
