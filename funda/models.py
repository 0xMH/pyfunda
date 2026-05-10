"""Small value objects and shared type aliases for pyfunda."""

from dataclasses import dataclass
from typing import Any, Literal


HeaderList = list[tuple[str, str]]
HttpMethod = Literal["GET", "POST"]
JsonDict = dict[str, Any]
FingerprintKind = Literal["tls_ja3", "curl_ja3", "curl_impersonate", "tls_client"]
RequestProfile = Literal["listing", "search", "walter"]


@dataclass(frozen=True, slots=True)
class ConstructionPeriod:
    key: str
    label: str
    year_min: int
    year_max: int


@dataclass(frozen=True, slots=True)
class Fingerprint:
    kind: FingerprintKind
    ja3: str | None = None
    target: str | None = None
    identifier: str | None = None
