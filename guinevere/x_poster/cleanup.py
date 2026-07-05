"""Cleanup service — auto-deletes old posted and failed media.

Runs daily at 04:00 WIB.  Deletes filesystem artifacts via
``StorageManager.delete_media()`` and removes/archives stale rows from
``p13_posts``.

- Completed posts older than ``posted_retention_days`` → state='archived'
- Failed posts older than ``failed_retention_days`` → DELETE row
"""

from __future__ import annotations

from uuid import UUID

import structlog

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo

from .config import XPosterSettings
from .db import DatabaseManager
from .storage import StorageManager

logger = structlog.get_logger(__name__)


class CleanupService:
    """Periodic cleanup of old post media and database rows."""

    _db: DatabaseManager
    _storage: StorageManager
    _settings: XPosterSettings
    _tz: ZoneInfo

    def __init__(
        self,
        db: DatabaseManager,
        storage: StorageManager,
        settings: XPosterSettings,
    ) -> None:
        self._db = db
        self._storage = storage
        self._settings = settings
        self._scheduler: AsyncIOScheduler | None = None
        self._tz = ZoneInfo(settings.schedule_timezone)

    async def start(self) -> None:
        """Start the daily cleanup scheduler (04:00 WIB)."""
        self._scheduler = AsyncIOScheduler(timezone=self._tz)
        trigger = CronTrigger(hour=4, minute=0, timezone=self._tz)
        _ = self._scheduler.add_job(
            self.run_cleanup,
            trigger=trigger,
            id="x_poster_cleanup",
            name="X Poster Daily Cleanup",
            replace_existing=True,
        )
        self._scheduler.start()
        logger.info(
            "x_poster.cleanup_started",
            posted_retention_days=self._settings.posted_retention_days,
            failed_retention_days=self._settings.failed_retention_days,
            timezone=self._settings.schedule_timezone,
        )

    async def stop(self) -> None:
        """Shutdown the cleanup scheduler."""
        if self._scheduler is not None:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None
            logger.info("x_poster.cleanup_stopped")

    async def run_cleanup(self) -> None:
        """Execute the daily cleanup cycle."""
        logger.info("x_poster.cleanup_cycle_start")
        archived = 0
        deleted = 0
        errors = 0

        # ── Phase 1: Archive old completed posts ──────────────────────
        try:
            archived = await self._archive_old_completed()
        except Exception:
            logger.exception("x_poster.cleanup_archive_error")
            errors += 1

        # ── Phase 2: Delete old failed posts ─────────────────────────
        try:
            deleted = await self._delete_old_failed()
        except Exception:
            logger.exception("x_poster.cleanup_delete_error")
            errors += 1

        logger.info(
            "x_poster.cleanup_completed",
            archived=archived,
            deleted=deleted,
            errors=errors,
        )

    async def _archive_old_completed(self) -> int:
        """Archive completed posts older than posted_retention_days."""
        retention = self._settings.posted_retention_days
        rows = await self._db.fetch(
            """
            SELECT id, media_path, state
            FROM p13_posts
            WHERE state = 'completed'
              AND posted_at < NOW() - make_interval(days => $1)
            ORDER BY posted_at ASC
            LIMIT 500
            """,
            retention,
        )

        archived = 0
        for row in rows:
            post_id: UUID = row["id"]
            filename: str = row["media_path"] or ""
            state: str = row["state"]
            try:
                _ = self._storage.delete_media(str(post_id), filename, state)
                _ = await self._db.execute(
                    "UPDATE p13_posts SET state = 'archived' WHERE id = $1",
                    post_id,
                )
                archived += 1
            except Exception:
                logger.warning(
                    "x_poster.cleanup_archive_single_error",
                    post_id=str(post_id),
                )

        if archived:
            logger.info("x_poster.cleanup_archived", count=archived)
        return archived

    async def _delete_old_failed(self) -> int:
        """Delete failed posts older than failed_retention_days."""
        retention = self._settings.failed_retention_days
        rows = await self._db.fetch(
            """
            SELECT id, media_path, state
            FROM p13_posts
            WHERE state = 'failed'
              AND created_at < NOW() - make_interval(days => $1)
            ORDER BY created_at ASC
            LIMIT 500
            """,
            retention,
        )

        deleted = 0
        for row in rows:
            post_id: UUID = row["id"]
            filename: str = row["media_path"] or ""
            state: str = row["state"]
            try:
                _ = self._storage.delete_media(str(post_id), filename, state)
                _ = await self._db.execute(
                    "DELETE FROM p13_posts WHERE id = $1",
                    post_id,
                )
                deleted += 1
            except Exception:
                logger.warning(
                    "x_poster.cleanup_delete_single_error",
                    post_id=str(post_id),
                )

        if deleted:
            logger.info("x_poster.cleanup_deleted", count=deleted)
        return deleted


__all__ = ["CleanupService"]
