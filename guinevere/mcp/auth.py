"""MCP Auth — Authorization decorator with 4 approval levels.

Provides the ``AuthLevel`` enum and ``require_approval`` decorator for
gating MCP tool invocations through Discord-based approval workflows.

Levels:
    READ_AUTO — execute immediately, no side effects.
    WRITE_NOTIFY — execute then fire Discord notification (non-blocking).
    DESTRUCTIVE_APPROVAL — notify Discord, wait for approval (5-min timeout).
    FORBIDDEN — raise immediately, never execute.
"""

from __future__ import annotations

import asyncio
import enum
import os
from functools import wraps
from typing import Any, Callable, Protocol, cast

import httpx
import structlog

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Pending-approval state (resolved by external Discord callback)
# ---------------------------------------------------------------------------

_pending_approvals: dict[str, asyncio.Event] = {}
_approval_results: dict[str, bool] = {}

# Default timeout in seconds for DESTRUCTIVE_APPROVAL (5 minutes).
_APPROVAL_TIMEOUT_SECONDS: float = 300.0


# ---------------------------------------------------------------------------
# Auth level enum
# ---------------------------------------------------------------------------


class AuthLevel(enum.Enum):
    """Authorization levels for MCP tool operations."""

    READ_AUTO = "read_auto"
    WRITE_NOTIFY = "write_notify"
    DESTRUCTIVE_APPROVAL = "destructive_approval"
    FORBIDDEN = "forbidden"


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class ForbiddenOperationError(Exception):
    """Raised when a FORBIDDEN operation is attempted or approval is denied."""


class _AuthGatedFunction(Protocol):
    """Protocol for an auth-gated callable exposing decorator metadata."""

    _auth_level: AuthLevel
    _auth_tool_name: str

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        ...


# ---------------------------------------------------------------------------
# Discord webhook helpers
# ---------------------------------------------------------------------------


def _get_webhook_url() -> str | None:
    """Return the Discord webhook URL from environment, or *None*."""
    return os.environ.get("DISCORD_WEBHOOK_URL")


async def _send_discord_notification(
    tool_name: str,
    level: AuthLevel,
    details: str = "",
) -> None:
    """Post a non-blocking notification to the Discord webhook.

    Silently logs errors rather than propagating them so that
    notification failures do not break the tool invocation flow.
    """
    url = _get_webhook_url()
    if url is None:
        logger.warning("discord_webhook_not_configured", tool_name=tool_name, level=level.value)
        return

    payload: dict[str, str] = {
        "content": (
            f"[MCP Auth] **{tool_name}** — level: `{level.value}`\n{details}"
        ),
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        logger.info("discord_notification_sent", tool_name=tool_name, level=level.value)
    except httpx.HTTPError as exc:
        logger.error(
            "discord_notification_failed",
            tool_name=tool_name,
            level=level.value,
            error=str(exc),
        )


async def _wait_for_approval(tool_name: str, timeout: float) -> bool:
    """Block until an external caller resolves approval for *tool_name*.

    Returns ``True`` if approved, ``False`` if denied or timed out.
    """
    event = asyncio.Event()
    _pending_approvals[tool_name] = event

    logger.info("awaiting_approval", tool_name=tool_name, timeout_seconds=timeout)

    try:
        await asyncio.wait_for(event.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning("approval_timed_out", tool_name=tool_name, timeout_seconds=timeout)
        _pending_approvals.pop(tool_name, None)
        return False

    approved = _approval_results.pop(tool_name, False)
    _pending_approvals.pop(tool_name, None)
    logger.info("approval_resolved", tool_name=tool_name, approved=approved)
    return approved


def approve(tool_name: str) -> None:
    """Signal that *tool_name* has been approved (called externally)."""
    _approval_results[tool_name] = True
    event = _pending_approvals.get(tool_name)
    if event is not None:
        event.set()


def deny(tool_name: str) -> None:
    """Signal that *tool_name* has been denied (called externally)."""
    _approval_results[tool_name] = False
    event = _pending_approvals.get(tool_name)
    if event is not None:
        event.set()


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------

def require_approval(
    level: AuthLevel, tool_name: str = ""
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator that gates a tool function through the auth workflow.

    Args:
        level: The authorization level to enforce.
        tool_name: Human-readable name for logging.  Defaults to the
            decorated function's ``__name__``.

    Returns:
        A decorator that wraps the target function with auth logic.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        name = tool_name or getattr(func, "__name__", "unknown")

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger.info(
                "auth_check",
                tool_name=name,
                level=level.value,
            )

            # RG-008: Validate declared level against AUTH_MATRIX (warn-only)
            try:
                from guinevere.mcp.auth_matrix import get_auth_level

                matrix_level = get_auth_level(name, "*")
                if matrix_level != level:
                    logger.warning(
                        "auth_matrix_mismatch",
                        tool_name=name,
                        declared_level=level.value,
                        matrix_level=matrix_level.value,
                    )
            except KeyError:
                logger.warning("auth_matrix_tool_missing", tool_name=name)
            except Exception as matrix_err:
                logger.warning(
                    "auth_matrix_check_failed",
                    tool_name=name,
                    error=str(matrix_err),
                )

            if level is AuthLevel.FORBIDDEN:
                logger.warning("auth_forbidden", tool_name=name)
                raise ForbiddenOperationError(
                    f"Operation '{name}' is forbidden."
                )

            if level is AuthLevel.READ_AUTO:
                logger.debug("auth_read_auto_pass", tool_name=name)
                return await func(*args, **kwargs)

            if level is AuthLevel.WRITE_NOTIFY:
                result = await func(*args, **kwargs)
                # Fire-and-forget notification — do not block on it.
                asyncio.create_task(
                    _send_discord_notification(
                        tool_name=name,
                        level=level,
                        details="Executed by MCP gateway.",
                    )
                )
                logger.info("auth_write_notify_done", tool_name=name)
                return result

            # DESTRUCTIVE_APPROVAL
            await _send_discord_notification(
                tool_name=name,
                level=level,
                details="Awaiting operator approval...",
            )
            approved = await _wait_for_approval(
                name,
                timeout=_APPROVAL_TIMEOUT_SECONDS,
            )
            if not approved:
                logger.warning("auth_denied", tool_name=name)
                raise ForbiddenOperationError(
                    f"Operation '{name}' was denied or timed out."
                )
            logger.info("auth_approved_executing", tool_name=name)
            return await func(*args, **kwargs)

        # Expose the auth level for introspection (auditors, tests).
        typed_wrapper = cast(_AuthGatedFunction, wrapper)
        typed_wrapper._auth_level = level
        typed_wrapper._auth_tool_name = name
        return typed_wrapper

    return decorator
