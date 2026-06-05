"""Notify handler — redacted webhook notifications for WRITE_NOTIFY operations.

Posts asynchronous (fire-and-forget) notifications to a configured webhook
URL.  Sensitive-looking values in the payload are redacted before sending.
If the webhook is not configured or the request fails, the failure is logged
but does **not** block the tool invocation (notification is best-effort).
"""

from __future__ import annotations

import os
import re
from typing import Protocol, cast

import httpx
import structlog

class Logger(Protocol):
    def info(self, event: str, **kwargs: object) -> None: ...
    def debug(self, event: str, **kwargs: object) -> None: ...
    def warning(self, event: str, **kwargs: object) -> None: ...


logger = cast(Logger, structlog.get_logger(__name__))

# Regex patterns for values that should be redacted in notification payloads.
# Matches common secret-like substrings (API keys, tokens, webhooks, passwords).
_REDACT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)(sk-[A-Za-z0-9_-]{20,})"),
    re.compile(r"(?i)(ghp_[A-Za-z0-9_]{36,})"),
    re.compile(r"(?i)(gho_[A-Za-z0-9_]{36,})"),
    re.compile(r"(?i)(discord(app)?\.com/api/webhooks/[\w-]+/[\w-]+)"),
    re.compile(r"(?i)(github\.com/[^/\s]+/[^/\s]+/settings/secrets)"),
    re.compile(r"(?i)(redis://[^@\s]+@[^/\s]+)"),
    re.compile(r"(?i)(postgresql?://[^@\s]+:[^@\s]+@[^/\s]+)"),
    re.compile(r"(?i)(mongodb(?:\+srv)?://[^@\s]+:[^@\s]+@[^/\s]+)"),
    re.compile(r"(?i)(-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)"),
    re.compile(r"(?i)(\b[A-Za-z0-9+/]{40,}={0,2}\b)"),  # base64-like blobs
]

_REDACTED_PLACEHOLDER = "[REDACTED]"


def redact_payload(text: str) -> str:
    """Replace secret-like substrings in *text* with ``[REDACTED]``.

    Args:
        text: The raw payload string.

    Returns:
        The string with sensitive patterns replaced.
    """
    for pattern in _REDACT_PATTERNS:
        text = pattern.sub(_REDACTED_PLACEHOLDER, text)
    return text


class NotifyHandler:
    """Fire-and-forget webhook notifier with payload redaction.

    Args:
        webhook_url: Optional explicit webhook URL.  Falls back to the
            ``DISCORD_APPROVAL_WEBHOOK`` environment variable.
    """

    def __init__(self, webhook_url: str | None = None) -> None:
        self._webhook_url: str | None = webhook_url

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send(
        self,
        canonical_tool: str,
        operation: str,
        level: str = "write_notify",
        details: str = "",
    ) -> None:
        """Send a redacted notification (fire-and-forget).

        Spawns an HTTP POST in a background task if a running event loop
        exists.  If no event loop is running (e.g. during synchronous
        tests), the notification is logged but skipped.

        Args:
            canonical_tool: Canonical tool name.
            operation: The operation that was executed.
            level: Auth level label for the notification.
            details: Optional extra detail string (will be redacted).
        """
        import asyncio

        try:
            _ = asyncio.get_running_loop()
        except RuntimeError:
            # No running event loop — log and skip the async call.
            logger.info(
                "auth_overlay_notify_skipped_no_loop",
                tool=canonical_tool,
                operation=operation,
            )
            return

        _ = asyncio.create_task(
            self._send_async(canonical_tool, operation, level, details)
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_webhook_url(self) -> str | None:
        """Return the configured webhook URL or ``None``."""
        if self._webhook_url is not None:
            return self._webhook_url
        return os.environ.get("DISCORD_APPROVAL_WEBHOOK")

    async def _send_async(
        self,
        canonical_tool: str,
        operation: str,
        level: str,
        details: str,
    ) -> None:
        """Perform the actual async HTTP POST to the webhook."""
        url = self._resolve_webhook_url()
        if url is None:
            logger.debug(
                "auth_overlay_webhook_not_configured",
                tool=canonical_tool,
                operation=operation,
            )
            return

        safe_details = redact_payload(details) if details else ""
        payload: dict[str, str] = {
            "content": (
                f"[Auth Overlay] **{canonical_tool}/{operation}** "
                f"— level: `{level}`\n{safe_details}"
            ),
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                _ = resp.raise_for_status()
            logger.info(
                "auth_overlay_notification_sent",
                tool=canonical_tool,
                operation=operation,
            )
        except Exception:
            logger.warning(
                "auth_overlay_notification_failed",
                tool=canonical_tool,
                operation=operation,
                exc_info=True,
            )
