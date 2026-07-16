"""HTTP transport and fingerprint rotation for Funda."""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, ClassVar
from urllib.parse import urlsplit

from curl_cffi import requests
import tls_client
from tls_client.exceptions import TLSClientExeption  # upstream typo, do not "fix"

from funda.constants import DEFAULT_MAX_RETRIES, FINGERPRINT_POOL, RETRY_STATUS_CODES
from funda.exceptions import FingerprintError, FundaRequestError
from funda.headers import make_headers
from funda.models import Fingerprint, HttpMethod, JsonDict, RequestProfile


@dataclass(slots=True)
class _FundaTransport:
    _cached_fingerprint_index: ClassVar[int | None] = None
    _fingerprint_cache_lock: ClassVar[Any] = Lock()
    _request_pacing_lock: ClassVar[Any] = Lock()
    _last_request_at: ClassVar[dict[str, float]] = {}

    timeout: int = 30
    max_retries: int = DEFAULT_MAX_RETRIES
    retry_backoff: float = 0.5
    min_request_interval: float = 0.5
    retry_statuses: set[int] | None = None

    _curl_session: requests.Session | None = field(default=None, init=False, repr=False)
    _tls_session: tls_client.Session | None = field(default=None, init=False, repr=False)
    _fingerprint: Fingerprint | None = field(default=None, init=False, repr=False)
    _fingerprint_index: int | None = field(default=None, init=False, repr=False)
    _fingerprint_proven: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if self.retry_backoff < 0:
            raise ValueError("retry_backoff must be >= 0")
        if self.min_request_interval < 0:
            raise ValueError("min_request_interval must be >= 0")
        if self.retry_statuses is None:
            self.retry_statuses = set(RETRY_STATUS_CODES)
        else:
            self.retry_statuses = set(self.retry_statuses)

    @property
    def session(self) -> Any:
        self._ensure_session()
        return self._session

    @property
    def _session(self) -> Any:
        return self._curl_session or self._tls_session

    def close(self) -> None:
        self._close_sessions()

    def __enter__(self) -> "_FundaTransport":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def _headers_dict(self, profile: RequestProfile = "listing") -> dict[str, str]:
        return dict(make_headers(profile))

    def _select_fingerprint(
        self, start_index: int | None = None
    ) -> tuple[int, Fingerprint, bool]:
        if start_index is None:
            with type(self)._fingerprint_cache_lock:
                cached_index = type(self)._cached_fingerprint_index
                if cached_index is not None:
                    return cached_index, FINGERPRINT_POOL[cached_index], True
            start_index = 0

        index = start_index % len(FINGERPRINT_POOL)
        return index, FINGERPRINT_POOL[index], False

    def _remember_fingerprint(self) -> None:
        if self._fingerprint_index is None:
            return
        self._fingerprint_proven = True
        with type(self)._fingerprint_cache_lock:
            type(self)._cached_fingerprint_index = self._fingerprint_index

    def _ensure_session(self, fingerprint_start_index: int | None = None) -> None:
        if self._fingerprint is None:
            index, fingerprint, selected_proven = self._select_fingerprint(
                fingerprint_start_index
            )
            self._fingerprint_index = index
            self._fingerprint = fingerprint
            self._fingerprint_proven = self._fingerprint_proven or selected_proven

        fingerprint = self._fingerprint
        if fingerprint.kind == "tls_ja3" and self._tls_session is None:
            self._tls_session = tls_client.Session(
                ja3_string=fingerprint.ja3,
                random_tls_extension_order=False,
            )
        elif fingerprint.kind == "curl_ja3" and self._curl_session is None:
            self._curl_session = requests.Session()
        elif fingerprint.kind == "curl_impersonate" and self._curl_session is None:
            self._curl_session = requests.Session(impersonate=fingerprint.target)
        elif fingerprint.kind == "tls_client" and self._tls_session is None:
            self._tls_session = tls_client.Session(
                client_identifier=fingerprint.identifier,
                random_tls_extension_order=False,
            )

    def _close_sessions(self) -> None:
        for session in (self._curl_session, self._tls_session):
            close = getattr(session, "close", None)
            if callable(close):
                close()
        self._curl_session = None
        self._tls_session = None

    def _reset_transport(self, *, rotate: bool = False) -> int | None:
        current_index = self._fingerprint_index
        self._close_sessions()
        self._fingerprint = None
        self._fingerprint_index = None
        if current_index is None:
            self._fingerprint_proven = False
            return None
        if rotate:
            self._fingerprint_proven = False
            with type(self)._fingerprint_cache_lock:
                if type(self)._cached_fingerprint_index == current_index:
                    type(self)._cached_fingerprint_index = None
            return (current_index + 1) % len(FINGERPRINT_POOL)
        return current_index

    def get(self, url: str, *, profile: RequestProfile = "listing") -> Any:
        return self.request("GET", url, profile=profile)

    def post(
        self,
        url: str,
        *,
        profile: RequestProfile = "listing",
        data: str | None = None,
        json_data: JsonDict | None = None,
    ) -> Any:
        return self.request("POST", url, profile=profile, data=data, json_data=json_data)

    def request(
        self,
        method: HttpMethod,
        url: str,
        *,
        profile: RequestProfile = "listing",
        data: str | None = None,
        json_data: JsonDict | None = None,
    ) -> Any:
        fingerprint_start_index: int | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self._send_once(
                    method,
                    url,
                    profile=profile,
                    data=data,
                    json_data=json_data,
                    fingerprint_start_index=fingerprint_start_index,
                )
            except (requests.errors.RequestsError, TLSClientExeption):
                if attempt >= self.max_retries:
                    raise
                fingerprint_start_index = self._reset_transport(
                    rotate=not self._fingerprint_proven
                )
                self._sleep_backoff(attempt)
                continue

            if response.status_code not in self.retry_statuses:
                self._remember_fingerprint()
                return response
            if attempt >= self.max_retries:
                detail = self._rejection_detail(response)
                raise FundaRequestError(
                    f"Funda rejected {method} {url} after {attempt + 1} attempts "
                    f"(status {response.status_code}){detail}"
                )

            rotate = response.status_code == 403 and not self._fingerprint_proven
            fingerprint_start_index = self._reset_transport(rotate=rotate)
            self._sleep_backoff(attempt, status_code=response.status_code)

        raise AssertionError("unreachable: retry loop must return or raise")

    def _sleep_backoff(self, attempt: int, *, status_code: int | None = None) -> None:
        if self.retry_backoff <= 0:
            return
        multiplier = 2**attempt if status_code in (403, 429) else attempt + 1
        time.sleep(self.retry_backoff * multiplier)

    @staticmethod
    def _rejection_detail(response: Any) -> str:
        headers = getattr(response, "headers", {})
        server = headers.get("server", headers.get("Server", ""))
        text = getattr(response, "text", "")
        if "AkamaiGHost" in server or "Access Denied" in text[:500]:
            return (
                ": Akamai denied the request; this is usually an IP-based rate or "
                "reputation block, not a search payload error. Stop requests and retry "
                "after a cooldown or from a different network"
            )
        return ""

    def _pace_request(self, url: str) -> None:
        if self.min_request_interval <= 0:
            return

        hostname = urlsplit(url).hostname or ""
        pacing_key = "funda.io" if hostname.endswith(".funda.io") else hostname
        with type(self)._request_pacing_lock:
            now = time.monotonic()
            last_request_at = type(self)._last_request_at.get(pacing_key)
            if last_request_at is not None:
                delay = self.min_request_interval - (now - last_request_at)
                if delay > 0:
                    time.sleep(delay)
                    now = time.monotonic()
            type(self)._last_request_at[pacing_key] = now

    def _send_once(
        self,
        method: HttpMethod,
        url: str,
        *,
        profile: RequestProfile = "listing",
        data: str | None = None,
        json_data: JsonDict | None = None,
        fingerprint_start_index: int | None = None,
    ) -> Any:
        self._pace_request(url)
        self._ensure_session(fingerprint_start_index=fingerprint_start_index)
        fingerprint = self._fingerprint
        if fingerprint is None:
            raise FingerprintError("No active Funda fingerprint")

        send, kwargs = self._sender(method, fingerprint, profile=profile)
        if method == "POST":
            if json_data is None:
                kwargs["data"] = data
            else:
                kwargs["json"] = json_data

        return send(url, **kwargs)

    def _sender(
        self,
        method: HttpMethod,
        fingerprint: Fingerprint,
        *,
        profile: RequestProfile,
    ) -> tuple[Callable[..., Any], JsonDict]:
        headers = make_headers(profile)
        if fingerprint.kind in ("tls_ja3", "tls_client"):
            if self._tls_session is None:
                raise FingerprintError("TLS session was not initialized")
            send = self._tls_session.get if method == "GET" else self._tls_session.post
            return send, {"headers": dict(headers), "timeout_seconds": self.timeout}

        if self._curl_session is None:
            raise FingerprintError("curl_cffi session was not initialized")

        send = self._curl_session.get if method == "GET" else self._curl_session.post
        kwargs: JsonDict = {"headers": headers, "timeout": self.timeout}
        if fingerprint.kind == "curl_ja3":
            kwargs["ja3"] = fingerprint.ja3
        return send, kwargs
