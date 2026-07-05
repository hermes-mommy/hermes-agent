"""Daily summary generator — posts stats to #x-dashboard Discord channel.

Runs daily at 23:00 WIB.  Queries today's stats, tomorrow's queue, and
formats a rich Discord embed posted via webhook.
"""

from __future__ import annotations

import httpx
import structlog

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo

from .config import XPosterSettings
from .db import DatabaseManager

logger = structlog.get_logger(__name__)

_INFO_BLUE: int = 0x3498DB
_TIMEOUT: float = 15.0


class DailySummaryGenerator:
    """Periodic daily summary generator for X Poster."""

    _db: DatabaseManager
    _settings: XPosterSettings
    _tz: ZoneInfo

    def __init__(self, db: DatabaseManager, settings: XPosterSettings) -> None:
        self._db = db
        self._settings = settings
        self._scheduler: AsyncIOScheduler | None = None
        self._tz = ZoneInfo(settings.schedule_timezone)

    async def start(self) -> None:
        """Start the daily summary scheduler (23:00 WIB)."""
        self._scheduler = AsyncIOScheduler(timezone=self._tz)
        trigger = CronTrigger(hour=23, minute=0, timezone=self._tz)
        _ = self._scheduler.add_job(
            self.generate_daily_summary,
            trigger=trigger,
            id="x_poster_daily_summary",
            name="X Poster Daily Summary",
            replace_existing=True,
        )
        self._scheduler.start()
        logger.info("x_poster.summary_started", timezone=self._settings.schedule_timezone)

    async def stop(self) -> None:
        """Shutdown the summary scheduler."""
        if self._scheduler is not None:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None
            logger.info("x_poster.summary_stopped")

    async def generate_daily_summary(self) -> None:
        """Execute the daily summary generation and webhook post."""
        logger.info("x_poster.summary_generating")

        # 1. Query today's stats from p13_daily_stats
        stats_row = await self._db.fetchrow(
            """
            SELECT posts_sent, posts_failed, queue_depth
            FROM p13_daily_stats
            WHERE stat_date = CURRENT_DATE
            """,
        )
        posts_sent = stats_row["posts_sent"] if stats_row else 0
        posts_failed = stats_row["posts_failed"] if stats_row else 0
        queue_depth = stats_row["queue_depth"] if stats_row else 0

        # 2. Query tomorrow's scheduled slots
        tomorrow_slots = await self._db.fetch(
            """
            SELECT slot_time, slot_date
            FROM p13_schedule
            WHERE slot_date = CURRENT_DATE + INTERVAL '1 day'
            ORDER BY slot_time ASC
            """,
        )
        slots_str = "\n".join([f"• {row['slot_time'].strftime('%H:%M')} WIB" for row in tomorrow_slots]) or "None"

        # 3. Format embed
        embed = {
            "title": "📊 X Poster Daily Summary",
            "color": _INFO_BLUE,
            "fields": [
                {"name": "Today's Stats", "value": f"✅ Sent: {posts_sent}\n❌ Failed: {posts_failed}\n⏳ Queue Depth: {queue_depth}", "inline": True},
                {"name": "Tomorrow's Schedule", "value": slots_str, "inline": False},
            ],
            "timestamp": None,  # Will be set by Discord if needed, or we can add it
        }

        # 4. POST to webhook
        webhook_url = self._settings.notification_webhook_url
        if not webhook_url:
            logger.warning("x_poster.summary_no_webhook", message="notification_webhook_url not configured")
            return

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.post(webhook_url, json={"embeds": [embed]})
                _ = response.raise_for_status()
                logger.info(
                    "x_poster.daily_summary_sent",
                    posts_sent=posts_sent,
                    posts_failed=posts_failed,
                    queue_depth=queue_depth,
                )
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "x_poster.summary_webhook_http_error",
                status=exc.response.status_code,
                body=exc.response.text[:300],
            )
        except httpx.RequestError as exc:
            logger.warning(
                "x_poster.summary_webhook_request_error",
                error=str(exc),
            )
        except Exception:
            logger.exception("x_poster.summary_webhook_unexpected_error")


__all__ = ["DailySummaryGenerator"]