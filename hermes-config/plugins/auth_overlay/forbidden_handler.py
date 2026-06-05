"""Forbidden handler — FORBIDDEN auth level response.

Returns a consistent ``block`` action dict for FORBIDDEN-level operations
and logs the attempt at warning severity.
"""

from __future__ import annotations

from typing import Protocol, cast

import structlog


class Logger(Protocol):
    """Subset of structlog logger methods used by this module."""

    def warning(self, event: str, **kwargs: object) -> None: ...


logger = cast(Logger, structlog.get_logger(__name__))


def handle_forbidden(
    canonical_tool: str,
    operation: str,
    raw_tool_name: str | None = None,
) -> dict[str, str]:
    """Return a fail-closed block response for a FORBIDDEN operation.

    Args:
        canonical_tool: Normalised canonical tool name.
        operation: The attempted operation.
        raw_tool_name: Original Hermes tool name (for logging).

    Returns:
        ``{"action": "block", "reason": "...", "message": "..."}``
    """
    logger.warning(
        "auth_overlay_forbidden",
        tool=canonical_tool,
        operation=operation,
        raw_tool_name=raw_tool_name,
    )
    return {
        "action": "block",
        "reason": f"AUTH_FORBIDDEN:{canonical_tool}:{operation}",
        "message": (
            f"Operation '{operation}' on tool '{canonical_tool}' "
            f"is forbidden by the auth matrix."
        ),
    }
