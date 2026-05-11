# Development

## Local Setup

```bash
uv sync
uv run python -m unittest discover -s tests -v
```

The test suite uses the Python standard library `unittest` module. No pytest
dependency is required.

## Test Layout

| File | Scope |
| --- | --- |
| `tests/test_client.py` | Client routing, id parsing, JSON handling |
| `tests/test_search.py` | Search payload construction and validation |
| `tests/test_autocomplete.py` | Location autocomplete payloads and parser behavior |
| `tests/test_models.py` | Dataclass model behavior |
| `tests/test_enrichment_parser.py` | Auxiliary endpoint parser normalization |
| `tests/test_transport_parallel.py` | Retry rotation, headers, parallel runner |
| `tests/test_live.py` | Gated live Funda smoke tests |

Fast local tests:

```bash
uv run python -m unittest discover -s tests
```

Live tests:

```bash
PYFUNDA_LIVE=1 uv run python -m unittest tests.test_live -v
```

Live tests verify listing, search, parallel fetching, and enrichment endpoints.
They intentionally stay narrow. Do not add broad city sweeps or large parallel
batches to the default live checks.

## Verification Checklist

Before committing production changes:

```bash
uv run python -m py_compile funda/*.py examples/*.py tests/*.py
uv run python -m unittest discover -s tests -v
PYFUNDA_LIVE=1 uv run python -m unittest tests.test_live -v
```

For docs and notebooks:

```bash
uv run python -m json.tool examples/analysis.ipynb >/dev/null
uv run python examples/full_api_walkthrough.py
```

## Design Rules

- Public API methods should be short, direct, and named like Python methods:
  `listing`, `search`, `price_history`, `broker_info`.
- Private implementation details stay underscore-prefixed.
- Prefer typed dataclasses for stable user-facing models.
- Preserve raw response data on models with a `raw` field.
- Use parser modules for payload normalization; do not parse API payloads in
  `Funda` methods.
- Use `_get_json()` for simple GET endpoints with repeated status handling.
- Keep network tests opt-in with `PYFUNDA_LIVE=1`.

## Transport Notes

The transport chooses a fingerprint lazily, caches the last working fingerprint
class-wide, and rotates on retryable statuses (`403`, `429`, `503`). It does not
preflight a separate test URL before real requests.

Batch APIs use a reusable private `_ParallelRunner`. Single listing and single
search calls remain sequential.
