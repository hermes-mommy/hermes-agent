"""Custom exception hierarchy for the wearable health pipeline."""

from __future__ import annotations


class WearableError(Exception):
    """Base exception for all wearable pipeline errors."""

    metric: str | None

    def __init__(self, message: str, metric: str | None = None) -> None:
        self.metric = metric
        super().__init__(message)


class AuthError(WearableError):
    """Raised when Mi Fitness Cloud authentication fails."""

    def __init__(self, message: str, metric: str | None = None) -> None:
        super().__init__(message, metric)


class RateLimitError(WearableError):
    """Raised when Mi Fitness Cloud rate limits are exceeded."""

    def __init__(self, message: str, metric: str | None = None) -> None:
        super().__init__(message, metric)


class CaptchaRequiredError(WearableError):
    """Raised when Xiaomi requires captcha or device verification."""

    def __init__(self, message: str, metric: str | None = None) -> None:
        super().__init__(message, metric)


class EndpointDriftError(WearableError):
    """Raised when the Mi Fitness Cloud API endpoint changes."""

    def __init__(self, message: str, metric: str | None = None) -> None:
        super().__init__(message, metric)


class DeviceUntrustedError(WearableError):
    """Raised when Xiaomi rejects an untrusted device fingerprint."""

    def __init__(self, message: str, metric: str | None = None) -> None:
        super().__init__(message, metric)


class CircuitBreakerOpenError(WearableError):
    """Raised when the sync circuit breaker is open."""

    def __init__(self, message: str, metric: str | None = None) -> None:
        super().__init__(message, metric)


class ConsentDeniedError(WearableError):
    """Raised when wearable health consent has not been granted."""

    def __init__(self, message: str, metric: str | None = None) -> None:
        super().__init__(message, metric)


class MetricUnavailableError(WearableError):
    """Raised when a requested metric is unavailable for the device."""

    def __init__(self, message: str, metric: str | None = None) -> None:
        super().__init__(message, metric)


class GadgetbridgeFileNotFoundError(WearableError):
    """Raised when the Gadgetbridge SQLite export file is not found."""

    def __init__(self, message: str, metric: str | None = None) -> None:
        super().__init__(message, metric)


class SQLiteParseError(WearableError):
    """Raised when the Gadgetbridge SQLite file cannot be parsed."""

    def __init__(self, message: str, metric: str | None = None) -> None:
        super().__init__(message, metric)


class GadgetbridgeSchemaMismatchError(WearableError):
    """Raised when Gadgetbridge table schema is incompatible with known patterns."""

    def __init__(self, message: str, metric: str | None = None) -> None:
        super().__init__(message, metric)


class GadgetbridgeEmptyExportError(WearableError):
    """Raised when the Gadgetbridge export contains no recognized tables."""

    def __init__(self, message: str, metric: str | None = None) -> None:
        super().__init__(message, metric)


class HealthConnectFileNotFoundError(WearableError):
    """Health Connect JSON export file not found at configured path."""
    pass


class HealthConnectParseError(WearableError):
    """Failed to parse Health Connect JSON export."""
    pass


class HealthConnectSDKError(WearableError):
    """Health Connect SDK unavailable or misconfigured."""
    pass


class HealthConnectPermissionError(WearableError):
    """Required Health Connect permissions not granted."""
    pass
