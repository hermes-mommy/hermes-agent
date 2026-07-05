"""Typed exception hierarchy for the Gmail module.

Every exception in this module inherits from ``GmailError`` so callers can
catch the base class for any Gmail-related failure or drill into specific
subclasses for structured error handling.

Hierarchy::

    GmailError
    ├── GmailAuthError
    │   ├── TokenExpiredError
    │   ├── TokenRefreshError
    │   ├── ScopeViolationError
    │   └── CredentialsNotFoundError
    ├── GmailAPIError
    │   ├── QuotaExceededError
    │   ├── MessageNotFoundError
    │   ├── ThreadNotFoundError
    │   ├── HistoryExpiredError
    │   └── RateLimitError
    ├── GmailSyncError
    │   ├── SyncStateCorruptedError
    │   └── BackfillInterruptedError
    ├── GmailSecurityError
    │   ├── InjectionDetectedError
    │   ├── SecretDetectedError
    │   └── PIIDetectedError
    ├── GmailDraftError
    │   ├── DraftCreationError
    │   ├── DraftSendError
    │   ├── DraftExpiredError
    │   └── PersonaLeakError
    ├── GmailConsentError
    │   ├── ConsentNotGrantedError
    │   └── ConsentRevokedError
    └── GmailPubSubError
        ├── WatchRenewalError
        └── StreamingPullError
"""

from __future__ import annotations

__all__ = [
    "GmailError",
    "GmailAuthError",
    "TokenExpiredError",
    "TokenRefreshError",
    "ScopeViolationError",
    "CredentialsNotFoundError",
    "GmailAPIError",
    "QuotaExceededError",
    "MessageNotFoundError",
    "ThreadNotFoundError",
    "HistoryExpiredError",
    "RateLimitError",
    "GmailSyncError",
    "SyncStateCorruptedError",
    "BackfillInterruptedError",
    "GmailSecurityError",
    "InjectionDetectedError",
    "SecretDetectedError",
    "PIIDetectedError",
    "GmailDraftError",
    "DraftCreationError",
    "DraftSendError",
    "DraftExpiredError",
    "PersonaLeakError",
    "GmailConsentError",
    "ConsentNotGrantedError",
    "ConsentRevokedError",
    "GmailPubSubError",
    "WatchRenewalError",
    "StreamingPullError",
]


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class GmailError(Exception):
    """Base exception for all Gmail module errors."""


# ---------------------------------------------------------------------------
# Auth errors
# ---------------------------------------------------------------------------


class GmailAuthError(GmailError):
    """Raised when Gmail authentication or authorization fails."""


class TokenExpiredError(GmailAuthError):
    """OAuth2 access token has expired and is no longer usable."""

    def __init__(self, expires_at: str) -> None:
        self.expires_at: str = expires_at
        super().__init__(f"Access token expired at {expires_at}")


class TokenRefreshError(GmailAuthError):
    """Refresh-token exchange with Google OAuth2 endpoint failed."""

    def __init__(self, reason: str) -> None:
        self.reason: str = reason
        super().__init__(f"Token refresh failed: {reason}")


class ScopeViolationError(GmailAuthError):
    """Requested Gmail scope is not granted in the current credentials."""

    def __init__(
        self, required_scope: str, available_scopes: list[str]
    ) -> None:
        self.required_scope: str = required_scope
        self.available_scopes: list[str] = available_scopes
        scopes_repr = ", ".join(available_scopes)
        super().__init__(
            f"Required scope '{required_scope}' not in"
            + f" available scopes [{scopes_repr}]"
        )


class CredentialsNotFoundError(GmailAuthError):
    """No OAuth2 credentials file or JSON could be located."""

    def __init__(self, searched_paths: list[str]) -> None:
        self.searched_paths: list[str] = searched_paths
        paths_repr = ", ".join(searched_paths)
        super().__init__(
            f"Credentials not found in any of: [{paths_repr}]"
        )


# ---------------------------------------------------------------------------
# API errors
# ---------------------------------------------------------------------------


class GmailAPIError(GmailError):
    """Raised when a Gmail REST API call fails."""


class QuotaExceededError(GmailAPIError):
    """Gmail API daily or per-user quota has been exhausted."""

    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds: int = retry_after_seconds
        super().__init__(f"Quota exceeded; retry after {retry_after_seconds}s")


class MessageNotFoundError(GmailAPIError):
    """The requested Gmail message does not exist or is inaccessible."""

    def __init__(self, message_id: str) -> None:
        self.message_id: str = message_id
        super().__init__(f"Message not found: {message_id}")


class ThreadNotFoundError(GmailAPIError):
    """The requested Gmail thread does not exist or is inaccessible."""

    def __init__(self, thread_id: str) -> None:
        self.thread_id: str = thread_id
        super().__init__(f"Thread not found: {thread_id}")


class HistoryExpiredError(GmailAPIError):
    """Gmail history token has expired; a full sync is required."""

    def __init__(self, history_id: str) -> None:
        self.history_id: str = history_id
        super().__init__(
            f"History expired for id {history_id}; full sync required"
        )


class RateLimitError(GmailAPIError):
    """Gmail API rate limit (per-second) has been hit."""

    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds: int = retry_after_seconds
        super().__init__(
            f"Rate limited; retry after {retry_after_seconds}s"
        )


# ---------------------------------------------------------------------------
# Sync errors
# ---------------------------------------------------------------------------


class GmailSyncError(GmailError):
    """Raised when incremental or full sync state is invalid."""


class SyncStateCorruptedError(GmailSyncError):
    """Persisted sync cursor/page-token is missing or unreadable."""

    def __init__(self, detail: str) -> None:
        self.detail: str = detail
        super().__init__(f"Sync state corrupted: {detail}")


class BackfillInterruptedError(GmailSyncError):
    """Historical backfill was interrupted before completion."""

    def __init__(
        self, processed_count: int, remaining_estimate: int
    ) -> None:
        self.processed_count: int = processed_count
        self.remaining_estimate: int = remaining_estimate
        super().__init__(
            f"Backfill interrupted after {processed_count} messages; "
            + f"~{remaining_estimate} remaining"
        )


# ---------------------------------------------------------------------------
# Security errors
# ---------------------------------------------------------------------------


class GmailSecurityError(GmailError):
    """Raised when a content-safety check flags a message or draft."""


class InjectionDetectedError(GmailSecurityError):
    """Prompt-injection or command-injection pattern found in content."""

    def __init__(self, injection_type: str, pattern: str) -> None:
        self.injection_type: str = injection_type
        self.pattern: str = pattern
        super().__init__(
            f"Injection detected (type={injection_type}): {pattern}"
        )


class SecretDetectedError(GmailSecurityError):
    """A secret or credential was found in message or draft content."""

    def __init__(self, secret_types: list[str]) -> None:
        self.secret_types: list[str] = secret_types
        types_repr = ", ".join(secret_types)
        super().__init__(f"Secret(s) detected in content: [{types_repr}]")


class PIIDetectedError(GmailSecurityError):
    """Personally-identifiable information detected in content."""

    def __init__(self, pii_types: list[str]) -> None:
        self.pii_types: list[str] = pii_types
        types_repr = ", ".join(pii_types)
        super().__init__(f"PII detected in content: [{types_repr}]")


# ---------------------------------------------------------------------------
# Draft errors
# ---------------------------------------------------------------------------


class GmailDraftError(GmailError):
    """Raised when a draft lifecycle operation fails."""


class DraftCreationError(GmailDraftError):
    """The Gmail draft could not be created via the API."""

    def __init__(self, reason: str) -> None:
        self.reason: str = reason
        super().__init__(f"Draft creation failed: {reason}")


class DraftSendError(GmailDraftError):
    """A draft could not be sent."""

    def __init__(self, draft_id: str, reason: str) -> None:
        self.draft_id: str = draft_id
        self.reason: str = reason
        super().__init__(f"Failed to send draft {draft_id}: {reason}")


class DraftExpiredError(GmailDraftError):
    """The draft has exceeded its maximum age and was purged."""

    def __init__(self, draft_id: str) -> None:
        self.draft_id: str = draft_id
        super().__init__(f"Draft expired and was purged: {draft_id}")


class PersonaLeakError(GmailDraftError):
    """Draft contains persona-internal patterns that must not be sent."""

    def __init__(self, leaked_patterns: list[str]) -> None:
        self.leaked_patterns: list[str] = leaked_patterns
        patterns_repr = ", ".join(leaked_patterns)
        super().__init__(
            f"Persona leak detected in draft: [{patterns_repr}]"
        )


# ---------------------------------------------------------------------------
# Consent errors
# ---------------------------------------------------------------------------


class GmailConsentError(GmailError):
    """Raised when a consent gate blocks a Gmail operation."""


class ConsentNotGrantedError(GmailConsentError):
    """Operator has not granted consent for the requested Gmail action."""

    def __init__(self, action: str) -> None:
        self.action: str = action
        super().__init__(f"Consent not granted for Gmail action: {action}")


class ConsentRevokedError(GmailConsentError):
    """Previously-granted consent for Gmail access has been revoked."""

    def __init__(self, revoked_at: str) -> None:
        self.revoked_at: str = revoked_at
        super().__init__(f"Gmail consent was revoked at {revoked_at}")


# ---------------------------------------------------------------------------
# Pub/Sub errors
# ---------------------------------------------------------------------------


class GmailPubSubError(GmailError):
    """Raised when a Gmail push-notification operation fails."""


class WatchRenewalError(GmailPubSubError):
    """Renewing the Gmail watch on a topic or mailbox failed."""

    def __init__(self, reason: str) -> None:
        self.reason: str = reason
        super().__init__(f"Watch renewal failed: {reason}")


class StreamingPullError(GmailPubSubError):
    """Cloud Pub/Sub streaming-pull subscription encountered an error."""

    def __init__(self, reason: str) -> None:
        self.reason: str = reason
        super().__init__(f"Streaming pull error: {reason}")
