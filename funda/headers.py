"""Request headers for Funda API calls."""

import random
import time

from funda.models import HeaderList, RequestProfile


def make_headers(profile: RequestProfile = "listing") -> HeaderList:
    """Generate the headers required by an internal request profile."""
    if profile == "walter":
        return [
            ("Accept", "application/json"),
            ("Content-Type", "application/json"),
        ]

    trace_id = str(random.randrange(10**18, 10**19))
    parent_id = hex(random.randrange(10**15, 10**16))[2:]
    tid = hex(int(time.time()))[2:] + "00000000"

    headers = [
        ("user-agent", "Dart/3.11 (dart:io)"),
        ("x-datadog-sampling-priority", "0"),
        ("x-datadog-origin", "rum"),
        ("tracestate", f"dd=s:0;o:rum;p:{parent_id}"),
        ("accept-encoding", "gzip"),
        ("x-datadog-parent-id", trace_id),
    ]

    if profile == "search":
        headers.extend(
            [
                ("content-type", "application/json"),
                ("referer", "https://www.funda.nl/"),
                ("accept", "application/json"),
            ]
        )
    elif profile == "listing":
        headers.extend(
            [
                ("x-funda-app-platform", "android"),
                ("x-funda-app-version", "7.14.11"),
                ("content-type", "application/json"),
            ]
        )
    else:
        raise ValueError(f"unknown request profile: {profile!r}")

    headers.append(("traceparent", f"00-{tid}{trace_id[:16]}-{parent_id}-00"))
    return headers
