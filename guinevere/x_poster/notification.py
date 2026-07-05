"""P13 X Auto Poster — Discord webhook notifications for queue events."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone

import httpx
import structlog

from .config import XPosterSettings, get_xposter_settings

_logger = structlog.get_logger(__name__)

# Color constants
COLOR_GREEN = 0x2ECC71  # Success
COLOR_RED = 0xE74C3C    # Failure
COLOR_BLUE = 0x3498DB   # Queue entry
COLOR_ORANGE = 0xF39C12 # Warning/Held


class NotificationService:
    """Sends Discord webhook notifications for X poster events."""

    _settings: XPosterSettings
    _webhook_url: str
    _dashboard_channel: str

    def __init__(self) -> None:
        self._settings = get_xposter_settings()
        self._webhook_url = self._settings.notification_webhook_url
        self._dashboard_channel = self._settings.discord_dashboard_channel_id

    async def notify_queue_entry(
        self,
        post_id: str,
        media_path: str,
        media_type: str,
        scheduled_slot: datetime | None,
    ) -> None:
        """Notify when a new post is queued."""
        embed = {
            "title": "New Post Queued",
            "color": COLOR_BLUE,
            "fields": [
                {"name": "Post ID", "value": post_id, "inline": True},
                {"name": "Media Type", "value": media_type, "inline": True},
                {"name": "Media", "value": media_path, "inline": False},
                {
                    "name": "Scheduled Slot",
                    "value": scheduled_slot.strftime("%Y-%m-%d %H:%M WIB") if scheduled_slot else "Pending",
                    "inline": False,
                },
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await self._send_embed(embed)

    async def notify_post_success(
        self,
        post_id: str,
        caption: str,
        duration_seconds: float,
        slot_time: datetime | None,
    ) -> None:
        """Notify when a post is successfully published."""
        embed = {
            "title": "Post Published",
            "color": COLOR_GREEN,
            "fields": [
                {"name": "Post ID", "value": post_id, "inline": True},
                {"name": "Caption", "value": caption[:100], "inline": False},
                {"name": "Duration", "value": f"{duration_seconds:.1f}s", "inline": True},
                {
                    "name": "Slot",
                    "value": slot_time.strftime("%H:%M WIB") if slot_time else "N/A",
                    "inline": True,
                },
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await self._send_embed(embed)

    async def notify_post_failure(
        self,
        post_id: str,
        error: str,
        attempts: int,
        next_action: str,
    ) -> None:
        """Notify when a post fails."""
        embed = {
            "title": "Post Failed",
            "color": COLOR_RED,
            "fields": [
                {"name": "Post ID", "value": post_id, "inline": True},
                {"name": "Error", "value": error[:500], "inline": False},
                {"name": "Attempts", "value": str(attempts), "inline": True},
                {"name": "Next Action", "value": next_action, "inline": True},
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await self._send_embed(embed)

    async def notify_session_expired(self) -> None:
        """Notify when the X session has expired."""
        embed = {
            "title": "Session Expired",
            "color": COLOR_ORANGE,
            "description": "X session cookies have expired. All pending posts are held. Please re-authenticate via noVNC.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await self._send_embed(embed)

    async def notify_daily_summary(
        self,
        total_posts: int,
        successful: int,
        failed: int,
        held: int,
        pending: int,
    ) -> None:
        """Send daily summary to dashboard channel."""
        embed = {
            "title": "Daily Summary",
            "color": COLOR_BLUE,
            "fields": [
                {"name": "Total", "value": str(total_posts), "inline": True},
                {"name": "Successful", "value": str(successful), "inline": True},
                {"name": "Failed", "value": str(failed), "inline": True},
                {"name": "Held", "value": str(held), "inline": True},
                {"name": "Pending", "value": str(pending), "inline": True},
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await self._send_embed(embed)

    async def _send_embed(self, embed: Mapping[str, object]) -> None:
        """Send an embed to the configured Discord webhook."""
        embed_title = embed.get("title")
        if not self._webhook_url:
            _logger.debug("notification.no_webhook_configured", embed_title=embed_title)
            return

        payload = {"embeds": [embed]}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self._webhook_url, json=payload)
                _ = response.raise_for_status()
                _logger.info(
                    "notification.sent",
                    embed_title=embed_title,
                    status_code=response.status_code,
                )
        except httpx.HTTPError as e:
            _logger.error(
                "notification.send_failed",
                embed_title=embed_title,
                error=str(e),
            )
