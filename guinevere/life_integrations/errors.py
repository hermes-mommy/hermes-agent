"""P22 integration error types.

Typed exceptions for integration failures. No bare except/empty catch
(AGENTS.md §5 Error Handling Bypass).
"""

from __future__ import annotations


class IntegrationError(Exception):
    """Base exception for all P22 integration errors."""


class ConfigurationMissingError(IntegrationError):
    """Raised when required configuration/credentials are missing.

    Integrations must report CONFIG_MISSING status, not fake success.
    """


class ConsentDeniedError(IntegrationError):
    """Raised when consent is revoked or not granted for an action."""


class HardStopBlockedError(IntegrationError):
    """Raised when HARD STOP blocks an action."""


class PermissionDeniedError(IntegrationError):
    """Raised when an action's permission tier is L4_FORBIDDEN."""


class ActionNotSupportedError(IntegrationError):
    """Raised when an adapter does not support the requested action."""


class RateLimitExceededError(IntegrationError):
    """Raised when an integration's rate limit is exceeded."""

    def __init__(self, provider: str, retry_after: int | None = None) -> None:
        self.provider = provider
        self.retry_after = retry_after
        msg = f"rate limit exceeded for {provider}"
        if retry_after:
            msg += f" (retry after {retry_after}s)"
        super().__init__(msg)


class AuthenticationError(IntegrationError):
    """Raised when authentication fails (invalid token, expired OAuth)."""


class ProviderError(IntegrationError):
    """Raised when a provider returns an error response."""

    def __init__(self, provider: str, status: int, message: str) -> None:
        self.provider = provider
        self.status = status
        self.message = message
        super().__init__(f"{provider} error {status}: {message}")


class PreDeleteSnapshotError(IntegrationError):
    """Raised when a pre-delete snapshot cannot be created.

    Destructive operations must abort if snapshot fails (no silent delete).
    """


class ChainVerificationError(IntegrationError):
    """Raised when audit chain verification fails (tamper detected)."""
