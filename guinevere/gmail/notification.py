"""Email notification dispatcher for Discord webhooks.

Sends rich Discord embed notifications for important emails via webhook POST.
Rate-limited to configurable notifications per sliding hour.
Quiet hours silently suppress all notifications.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog

from guinevere.gmail.categories import EmailCategory
from guinevere.gmail.envelope import GmailMessageEnvelope
from guinevere.gmail.metrics import record_notification_sent

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CATEGORY_COLORS: dict[EmailCategory, int] = {
    EmailCategory.FINANCIAL: 0xFFD700,  # GOLD
    EmailCategory.CLIENT_WORK: 0x3498DB,  # BLUE
    EmailCategory.BILLING_INVOICE: 0xF39C12,  # ORANGE
    EmailCategory.IMPORTANT: 0x2ECC71,  # GREEN
    EmailCategory.SPAM_PHISHING: 0xE74C3C,  # RED
    EmailCategory.NEWSLETTER: 0x95A5A6,  # GRAY
    EmailCategory.PROMOTION: 0x9B59B6,  # PURPLE
    EmailCategory.TRANSACTIONAL: 0x1ABC9C,  # TEAL
}

DEFAULT_COLOR = 0x95A5A6

IMPORTANCE_THRESHOLD = 5
RATE_LIMIT_WINDOW = 3600  # 1 hour in seconds
RATE_LIMIT_MAX = 10

NOTIFIABLE_CATEGORIES: frozenset[EmailCategory] = frozenset({
    EmailCategory.CLIENT_WORK,
    EmailCategory.FINANCIAL,
    EmailCategory.BILLING_INVOICE,
    EmailCategory.IMPORTANT,
})

SUPPORTED_ACTIONS = ("Draft Reply", "Mark Read", "Ignore")


# ---------------------------------------------------------------------------
# Notifier
# ---------------------------------------------------------------------------


class EmailNotifier:
    """Sends rich Discord embed notifications for important emails.

    Parameters
    ----------
    webhook_url:
        Discord webhook URL to POST notifications to.
    channel_id:
        Optional Discord channel/thread ID override for the webhook.
    rate_limit:
        Maximum notifications per sliding hour (default 10).
    quiet_start:
        Hour (0‑23) when quiet hours begin (default 22).
    quiet_end:
        Hour (0‑23) when quiet hours end (default 7).
    importance_threshold:
        Minimum importance score to trigger notification (default 5).
    http_client:
        Optional shared ``httpx.AsyncClient``. A private one is created if
        omitted.
    """

    def __init__(
        self,
        webhook_url: str,
        channel_id: int | None = None,
        rate_limit: int = RATE_LIMIT_MAX,
        quiet_start: int = 22,
        quiet_end: int = 7,
        importance_threshold: int = IMPORTANCE_THRESHOLD,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._webhook_url: str = webhook_url
        self._channel_id: int | None = channel_id
        self._rate_limit: int = rate_limit
        self._quiet_start: int = quiet_start
        self._quiet_end: int = quiet_end
        self._importance_threshold: int = importance_threshold
        self._http_client: httpx.AsyncClient = http_client or httpx.AsyncClient(timeout=30.0)

        # Sliding-window rate-limit state
        self._lock: asyncio.Lock = asyncio.Lock()
        self._timestamps: list[float] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def notify_important(self, envelope: GmailMessageEnvelope) -> bool:
        """Send a Discord notification if *envelope* meets the threshold.

        Returns ``True`` if a notification was dispatched, ``False`` if it
        was skipped (quiet hours, rate-limited, or below threshold).
        """
        if not await self._should_notify(envelope):
            return False

        embed = await self._build_embed(envelope)
        success = await self._send_webhook(embed)

        if success:
            category = envelope.classify()
            _ = record_notification_sent(category.value)
            logger.info(
                "notification_sent",
                message_id=envelope.message_id,
                thread_id=envelope.thread_id,
                category=category.value,
            )
        return success

    # ------------------------------------------------------------------
    # Decision helpers
    # ------------------------------------------------------------------

    async def _should_notify(self, envelope: GmailMessageEnvelope) -> bool:
        """Run the full notification gate.

        Order: quiet hours → threshold check (no cost) → rate limit (cost).
        """
        if self._in_quiet_hours():
            logger.debug("quiet_hours_skip", message_id=envelope.message_id)
            return False

        if not self._meets_threshold(envelope):
            return False

        if not await self._check_rate_limit():
            logger.debug("rate_limit_skip", message_id=envelope.message_id)
            return False

        return True

    def _meets_threshold(self, envelope: GmailMessageEnvelope) -> bool:
        """Pure predicate — does *not* consume a rate-limit slot.

        Returns ``True`` if the envelope passes the importance score or
        belongs to a notifiable category.  Category is derived via
        ``envelope.classify()``.
        """
        category = envelope.classify()

        # High-importance markers (non-empty list) are a proxy for the
        # numeric importance threshold.
        if (
            envelope.importance_markers is not None
            and len(envelope.importance_markers) >= self._importance_threshold
        ):
            return True

        if category in NOTIFIABLE_CATEGORIES:
            return True

        return False

    def _in_quiet_hours(self) -> bool:
        """Check whether *now* falls inside the configured quiet window.

        Supports windows that span midnight (e.g. 22:00‑07:00).
        """
        now = datetime.now()
        current = now.hour * 60 + now.minute
        start = self._quiet_start * 60
        end = self._quiet_end * 60

        if self._quiet_start > self._quiet_end:
            # Spans midnight — e.g. 22:00 → 07:00
            return current >= start or current < end
        return start <= current < end

    async def _check_rate_limit(self) -> bool:
        """Sliding-window rate limiter.

        Thread-safe via ``asyncio.Lock``.  The current timestamp is recorded
        atomically with the check so that a ``True`` return always consumes
        one slot.
        """
        async with self._lock:
            now = time.time()
            cutoff = now - RATE_LIMIT_WINDOW

            # Prune expired timestamps
            self._timestamps[:] = [t for t in self._timestamps if t > cutoff]

            if len(self._timestamps) >= self._rate_limit:
                return False

            self._timestamps.append(now)
            return True

    # ------------------------------------------------------------------
    # Embed building & dispatch
    # ------------------------------------------------------------------

    async def _build_embed(self, envelope: GmailMessageEnvelope) -> dict[str, Any]:
        """Construct a Discord embed payload for *envelope*."""
        category = envelope.classify()
        color = CATEGORY_COLORS.get(category, DEFAULT_COLOR)

        # Truncate subject to Discord's 256‑character embed-title limit
        title = (envelope.subject or "(no subject)")[:256]

        importance_str = str(len(envelope.importance_markers)) if envelope.importance_markers else "—"

        fields: list[dict[str, Any]] = [
            {"name": "From", "value": (envelope.sender or "unknown")[:1024], "inline": True},
            {"name": "Category", "value": category.value[:1024], "inline": True},
            {"name": "Importance", "value": importance_str, "inline": True},
        ]

        if envelope.snippet:
            fields.append({"name": "Preview", "value": envelope.snippet[:1024], "inline": False})

        # Text-only action hints — actual button handling lives in
        # ``guinevere/discord_ux.py`` / ``guinevere/draft/``.
        actions_str = " · ".join(f"`{a}`" for a in SUPPORTED_ACTIONS)
        fields.append({"name": "Actions", "value": actions_str, "inline": False})

        embed: dict[str, Any] = {
            "title": title,
            "color": color,
            "fields": fields,
            "footer": {"text": "Gmail"},
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }

        return embed

    async def _send_webhook(self, embed: dict[str, Any]) -> bool:
        """POST the embed payload to the Discord webhook URL.

        Returns ``True`` on success.  Failures are logged as warnings and
        return ``False`` — they never propagate.
        """
        payload: dict[str, Any] = {"embeds": [embed]}

        if self._channel_id is not None:
            payload["channel_id"] = str(self._channel_id)

        try:
            response = await self._http_client.post(self._webhook_url, json=payload)
            _ = response.raise_for_status()
            return True
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "webhook_http_error",
                status_code=exc.response.status_code,
                body=exc.response.text[:500],
            )
            return False
        except httpx.RequestError as exc:
            logger.warning("webhook_request_failed", error=str(exc))
            return False
        except Exception:
            logger.warning("webhook_unexpected_error", exc_info=True)
            return False
