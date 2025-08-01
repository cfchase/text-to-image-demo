"""KServe-specific exceptions."""


class KServeError(Exception):
    """Base exception for KServe operations."""

    pass


class KServeConnectionError(KServeError):
    """Failed to connect to KServe endpoint."""

    pass


class KServeTimeoutError(KServeError):
    """KServe request timed out."""

    pass


class KServeModelNotReadyError(KServeError):
    """KServe model is not ready to serve requests."""

    pass


class KServeInvalidResponseError(KServeError):
    """KServe returned an invalid response."""

    pass


class KServeRateLimitError(KServeError):
    """KServe rate limit exceeded."""

    pass


class KServeInferenceError(KServeError):
    """KServe inference request failed."""

    def __init__(self, message: str, error_code: str = None, details: str = None):
        """
        Initialize inference error.

        Args:
            message: Error message
            error_code: Optional error code from KServe
            details: Optional detailed error information
        """
        super().__init__(message)
        self.error_code = error_code
        self.details = details


class KServeValidationError(KServeError):
    """KServe request validation failed."""

    pass