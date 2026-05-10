"""Exception types raised by pyfunda."""


class FundaError(Exception):
    """Base exception for pyfunda errors."""


class FingerprintError(FundaError):
    """Raised when no configured TLS fingerprint can reach Funda."""


class FundaRequestError(FundaError, RuntimeError):
    """Raised when Funda rejects or fails an HTTP request."""


class ListingNotFound(FundaError, LookupError):
    """Raised when a listing cannot be found."""


class SearchError(FundaError, RuntimeError):
    """Raised when the Funda search endpoint rejects a query."""


class PriceHistoryError(FundaError, LookupError):
    """Raised when price history cannot be fetched for a listing."""
