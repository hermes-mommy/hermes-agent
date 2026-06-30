"""P13 X Auto Poster — Custom exception hierarchy."""

from typing import Any


class XPosterError(Exception):
    """Base exception for all P13 X Auto Poster errors."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context = context or {}


# --- Queue & Schedule ---
class QueueError(XPosterError):
    """Base queue-related error."""


class QueueFullError(QueueError):
    """Queue has reached maximum capacity."""


class ScheduleSlotUnavailableError(XPosterError):
    """No schedule slots available for assignment."""


class ScheduleOverflowError(XPosterError):
    """Queue overflowed beyond schedule capacity."""


# --- Database ---
class DatabaseError(XPosterError):
    """Base database-related error."""


class DatabaseConnectionError(DatabaseError):
    """Failed to establish database connection or pool."""


class DatabaseQueryError(DatabaseError):
    """Database query execution failed."""


# --- X API / Twikit ---
class XApiError(XPosterError):
    """Base X API error."""


class XApiConnectionError(XApiError):
    """X API network or client connection failed."""


class XApiAuthError(XApiError):
    """X API authentication failed."""


class XApiRateLimitError(XApiError):
    """X API request was rate limited."""


class XApiPostError(XApiError):
    """X API post creation or media upload failed."""


# --- Session & Auth ---
class SessionError(XPosterError):
    """Base session-related error."""


class SessionExpiredError(SessionError):
    """X session cookies have expired."""


# --- Moderation & Caption ---
class ModerationError(XPosterError):
    """Content moderation check failed or blocked."""


class CaptionGenerationError(XPosterError):
    """Base caption generation error."""


class CaptionTooLongError(CaptionGenerationError):
    """Generated caption exceeds maximum allowed length."""


class CaptionEmptyError(CaptionGenerationError):
    """Generated caption is empty or whitespace-only."""
