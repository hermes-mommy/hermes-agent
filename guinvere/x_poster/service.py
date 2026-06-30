from __future__ import annotations

"""P13 X Poster — Main service wiring and lifecycle."""

import asyncio
from collections import Counter
from datetime import date
from typing import Any
from uuid import UUID

import structlog

from .caption_generator import CaptionGenerator
from .circuit_breaker import CircuitBreaker
from .cleanup import CleanupService
from .config import XPosterSettings, get_xposter_settings
from .db import DatabaseManager
from .metrics import (
    set_queue_depth,
    set_schedule_total,
    set_schedule_used,
    set_session_health,
    start_metrics_server,
)
from .moderator import ContentModerator, ModerationResult
from .notification import NotificationService
from .poster import XPoster
from .queue_manager import QueueManager
from .retry_engine import RetryEngine
from .schedule_manager import ScheduleManager
from .storage import StorageManager
from .x_api_client import XApiClient
from .summary import DailySummaryGenerator
from .timeout_handler import TimeoutConfig, TimeoutHandler

logger = structlog.get_logger("x_poster.service")


def _range_to_interval(range_param: str) -> str:
    if range_param == "1mo":
        return "1 month"
    if range_param == "6mo":
        return "6 months"
    if range_param == "all":
        return "100 years"
    return "3 months"


def _empty_totals() -> dict[str, int]:
    return {"impressions": 0, "likes": 0, "replies": 0, "retweets": 0, "quotes": 0, "bookmarks": 0}


_STATUS_STATES: tuple[str, ...] = (
    "pending",
    "scheduled",
    "in_progress",
    "completed",
    "failed",
    "held",
    "cancelled",
)

_CIRCUIT_STATE_TO_METRIC: dict[str, int] = {
    "closed": 0,
    "open": 1,
    "half_open": 2,
}


class XPosterService:
    """Main X Poster service — wires all components and manages lifecycle."""

    _settings: XPosterSettings
    _db: DatabaseManager | None
    _storage: StorageManager | None
    _queue: QueueManager | None
    _schedule: ScheduleManager | None
    _bridge: Any | None
    _caption: CaptionGenerator | None
    _moderator: ContentModerator | None
    _x_api: XApiClient | None
    _poster: XPoster | None
    _circuit_breaker: CircuitBreaker | None
    _retry_engine: RetryEngine | None
    _timeout_handler: TimeoutHandler | None
    _notifications: NotificationService | None
    _summary: DailySummaryGenerator | None
    _cleanup: CleanupService | None
    _running: bool
    _worker_task: asyncio.Task[None] | None
    _loop: asyncio.AbstractEventLoop | None
    _status_snapshot: dict[str, Any]

    def __init__(self, settings: XPosterSettings | None = None, bridge: Any | None = None) -> None:
        self._settings = settings or get_xposter_settings()
        self._bridge = bridge
        self._db = None
        self._storage = None
        self._queue = None
        self._schedule = None
        self._caption = None
        self._moderator = None
        self._x_api = None
        self._poster = None
        self._circuit_breaker = None
        self._retry_engine = None
        self._timeout_handler = None
        self._notifications = None
        self._summary = None
        self._cleanup = None
        self._running = False
        self._worker_task = None
        self._engagement_task: asyncio.Task[None] | None = None
        self._loop = None
        self._status_snapshot = {
            "running": False,
            "queue_depth": {state: 0 for state in _STATUS_STATES},
            "session_health": "unknown",
            "next_slot": None,
            "metrics_port": self._settings.metrics_port,
            "health_port": self._settings.health_port,
            "circuit_breaker": "closed",
        }
        logger.info("x_poster.service_initialized")

    async def start(self) -> None:
        """Start the full X Poster service."""
        logger.info("x_poster.service_starting")
        self._loop = asyncio.get_running_loop()

        self._db = DatabaseManager()
        await self._db.initialize()

        self._storage = StorageManager(self._settings.media_root)
        self._queue = QueueManager(self._db)
        self._schedule = ScheduleManager(self._db)
        await self._initialize_schedule_window()

        self._caption = CaptionGenerator(self._bridge, self._settings)
        self._moderator = ContentModerator(self._bridge, self._settings)
        self._x_api = XApiClient(self._settings)
        await self._x_api.connect()
        api_health = await self._x_api.check_health()
        set_session_health(api_health["authenticated"])

        self._poster = XPoster(self._x_api, self._queue, self._db)

        self._circuit_breaker = CircuitBreaker(self._db, component="x_api")
        await self._circuit_breaker.initialize()
        self._retry_engine = RetryEngine(self._queue, self._schedule)
        self._timeout_handler = TimeoutHandler(
            TimeoutConfig(
                x_api_connect=30.0,
                x_api_upload=120.0,
                x_api_post=60.0,
                caption_generation=30.0,
                moderation_check=15.0,
                db_operation=10.0,
            )
        )
        self._notifications = NotificationService()
        self._summary = DailySummaryGenerator(self._db, self._settings)
        self._cleanup = CleanupService(self._db, self._storage, self._settings)

        await self._summary.start()
        await self._cleanup.start()
        start_metrics_server(self._settings.health_host, self._settings.metrics_port)

        self._running = True
        self._status_snapshot["running"] = True
        self._worker_task = asyncio.create_task(self._worker_loop(), name="x-poster-worker")
        # Engagement polling via X API — DISABLED per Faiz request (2026-06-25)
        # self._engagement_task = asyncio.create_task(self._engagement_poll_loop(), name="x-poster-engagement")
        self._engagement_task = None
        await self._refresh_metrics()
        logger.info("x_poster.service_started")

    async def stop(self) -> None:
        """Stop the X Poster service gracefully."""
        self._running = False
        self._status_snapshot["running"] = False

        if self._engagement_task is not None:
            self._engagement_task.cancel()
            try:
                await self._engagement_task
            except asyncio.CancelledError:
                pass
            self._engagement_task = None

        if self._worker_task is not None:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None

        if self._summary is not None:
            await self._summary.stop()
        if self._cleanup is not None:
            await self._cleanup.stop()
        if self._x_api is not None:
            await self._x_api.disconnect()
        if self._db is not None:
            await self._db.close()
        logger.info("x_poster.service_stopped")

    async def _initialize_schedule_window(self) -> None:
        assert self._schedule is not None
        today = self._schedule._now_wib().date()
        rapid_test = getattr(self._settings, "rapid_test_mode", False)
        look_ahead_days = 1 if rapid_test else getattr(self._settings, "schedule_look_ahead_days", 365)
        for offset in range(0, look_ahead_days):
            target = today.fromordinal(today.toordinal() + offset)
            await self._schedule.initialize_schedule(target)
        logger.info("x_poster.schedule.window_initialized", days=look_ahead_days, rapid_test=rapid_test)

    async def _worker_loop(self) -> None:
        """Main scheduler worker loop."""
        assert self._queue is not None
        assert self._schedule is not None
        assert self._caption is not None
        assert self._moderator is not None
        assert self._poster is not None
        assert self._retry_engine is not None
        assert self._notifications is not None
        assert self._circuit_breaker is not None
        assert self._timeout_handler is not None

        while self._running:
            try:
            # Watchdog ping (systemd Type=notify) - disabled for Type=exec compatibility
                await self._refresh_metrics()
                due_slot = await self._schedule.get_next_due_slot()
                if due_slot is None:
                    await asyncio.sleep(15)
                    continue

                slot_time, slot_date = due_slot
                slot_posts = await self._schedule.get_slot_posts(slot_time, slot_date)
                if not slot_posts:
                    await self._schedule.mark_slot_executed(slot_time, slot_date)
                    await asyncio.sleep(2)
                    continue

                # Group posts into batches of 4 for multi-media tweets
                batch_size = 4
                for i in range(0, len(slot_posts), batch_size):
                    if not self._running:
                        break
                    batch = slot_posts[i:i + batch_size]
                    await self._process_scheduled_post_batch(batch, slot_time, slot_date)

                await self._schedule.mark_slot_executed(slot_time, slot_date)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("x_poster.worker_loop_error", error=str(exc))
                await asyncio.sleep(10)

    async def _process_scheduled_post_batch(
        self,
        batch: list[dict[str, Any]],
        slot_time: Any,
        slot_date: date,
    ) -> None:
        """Process a batch of posts (up to 4) as a single multi-media tweet."""
        import json
        assert self._queue is not None
        assert self._schedule is not None
        assert self._poster is not None
        assert self._retry_engine is not None
        assert self._notifications is not None
        assert self._circuit_breaker is not None

        allowed = await self._circuit_breaker.allow_request()
        if not allowed:
            logger.warning("x_poster.circuit_open_skip_batch", batch_size=len(batch))
            return

        post_ids = [post["id"] for post in batch]
        
        # Extract media paths - each post may have multiple paths in metadata
        all_media_paths = []
        for post in batch:
            media_path = str(post.get("media_path") or "")
            if media_path:
                all_media_paths.append((post["id"], media_path))
            
            # Check for additional media_paths in metadata
            metadata_raw = post.get("metadata")
            if metadata_raw:
                try:
                    metadata = json.loads(metadata_raw) if isinstance(metadata_raw, str) else metadata_raw
                    extra_paths = metadata.get("media_paths", [])
                    for path in extra_paths:
                        if path and path != media_path:
                            all_media_paths.append((post["id"], path))
                except (json.JSONDecodeError, TypeError):
                    pass

        if not all_media_paths:
            logger.warning("x_poster.batch_no_media", post_ids=[str(pid) for pid in post_ids])
            return

        slot_dt = self._schedule._now_wib().replace(
            year=slot_date.year,
            month=slot_date.month,
            day=slot_date.day,
            hour=slot_time.hour,
            minute=slot_time.minute,
            second=0,
            microsecond=0,
        )

        try:
            result = await self._poster.execute_post_batch(all_media_paths, None)

            if result.success:
                for post_id in post_ids:
                    await self._notifications.notify_post_success(
                        str(post_id),
                        "",
                        result.duration_seconds,
                        slot_dt,
                    )
                await self._circuit_breaker.record_success()
                return

            for post_id in post_ids:
                retry_state = await self._retry_engine.handle_failure(
                    post_id,
                    Exception(result.error or "batch post failed"),
                )
                await self._notifications.notify_post_failure(
                    str(post_id),
                    result.error or "batch post failed",
                    1,
                    retry_state,
                )
            await self._circuit_breaker.record_failure()
        except Exception as exc:
            logger.exception("x_poster.process_batch_error", post_ids=[str(pid) for pid in post_ids], error=str(exc))
            for post_id in post_ids:
                retry_state = await self._retry_engine.handle_failure(post_id, exc)
                await self._notifications.notify_post_failure(
                    str(post_id),
                    str(exc),
                    1,
                    retry_state,
                )
            await self._circuit_breaker.record_failure()

    async def _process_scheduled_post(
        self,
        post_id: UUID,
        post: dict[str, Any],
        slot_time: Any,
        slot_date: date,
    ) -> None:
        assert self._queue is not None
        assert self._schedule is not None
        assert self._caption is not None
        assert self._moderator is not None
        assert self._poster is not None
        assert self._retry_engine is not None
        assert self._notifications is not None
        assert self._circuit_breaker is not None
        assert self._timeout_handler is not None

        allowed = await self._circuit_breaker.allow_request()
        if not allowed:
            logger.warning("x_poster.circuit_open_skip", post_id=str(post_id))
            return

        media_path = str(post.get("media_path") or "")
        media_type = str(post.get("media_type") or "photo")
        caption = str(post.get("caption") or "").strip()
        slot_dt = self._schedule._now_wib().replace(
            year=slot_date.year,
            month=slot_date.month,
            day=slot_date.day,
            hour=slot_time.hour,
            minute=slot_time.minute,
            second=0,
            microsecond=0,
        )

        try:
            await self._queue.update_state(post_id, "in_progress")

            moderation = await self._timeout_handler.timeout_moderation(
                self._moderator.moderate_caption(post_id, caption)
            )
            if not moderation.safe:
                await self._queue.update_state(post_id, "failed", last_error=f"Moderation: {moderation.reason}")
                await self._notifications.notify_post_failure(
                    str(post_id),
                    moderation.reason,
                    self._extract_attempts(post),
                    "failed",
                )
                await self._circuit_breaker.record_failure()
                return

            result = await self._poster.execute_post(
                post_id,
                caption,
                [media_path] if media_path else [],
            )

            if result.success:
                await self._notifications.notify_post_success(
                    str(post_id),
                    caption,
                    result.duration_seconds,
                    slot_dt,
                )
                await self._circuit_breaker.record_success()
                return

            retry_state = await self._retry_engine.handle_failure(
                post_id,
                Exception(result.error or "post failed"),
            )
            await self._notifications.notify_post_failure(
                str(post_id),
                result.error or "post failed",
                self._extract_attempts(post) + 1,
                retry_state,
            )
            await self._circuit_breaker.record_failure()
        except Exception as exc:
            logger.exception("x_poster.process_post_error", post_id=str(post_id), error=str(exc))
            retry_state = await self._retry_engine.handle_failure(post_id, exc)
            await self._notifications.notify_post_failure(
                str(post_id),
                str(exc),
                self._extract_attempts(post) + 1,
                retry_state,
            )
            await self._circuit_breaker.record_failure()

    async def _persist_caption(self, post_id: UUID, caption: str) -> str:
        assert self._db is not None
        return await self._db.execute(
            "UPDATE p13_posts SET caption = $2, updated_at = NOW() WHERE id = $1",
            post_id,
            caption,
        )

    async def _refresh_metrics(self) -> None:
        """Refresh queue depth and schedule metrics."""
        assert self._queue is not None
        assert self._schedule is not None
        assert self._x_api is not None
        assert self._circuit_breaker is not None

        counts = Counter()
        for state in _STATUS_STATES:
            counts[state] = await self._queue.get_queue_depth(state)
            set_queue_depth(state, counts[state])

        set_schedule_total(len(self._settings.schedule_slots))
        used = await self._schedule.get_slots_used_today()
        set_schedule_used(used)
        api_health = await self._x_api.check_health()
        session_healthy = api_health["authenticated"]
        set_session_health(session_healthy)

        circuit_state = (await self._circuit_breaker.get_state()).value
        self._status_snapshot = {
            "running": self._running,
            "queue_depth": {state: counts[state] for state in _STATUS_STATES},
            "session_health": "ok" if session_healthy else "expired",
            "next_slot": self._format_next_slot(await self._schedule.get_next_upcoming_slot()),
            "metrics_port": self._settings.metrics_port,
            "health_port": self._settings.health_port,
            "circuit_breaker": circuit_state,
        }

    def get_status_summary(self) -> dict[str, Any]:
        """Return service status for health API."""
        return dict(self._status_snapshot)

    def get_engagement_summary(self, range_param: str = "3mo") -> dict[str, Any]:
        """Return engagement summary for health API (sync)."""
        if self._loop is None:
            return {"ok": False, "error": "service not running", "totals": _empty_totals(), "top_post": None, "posts_tracked": 0, "range": range_param}
        try:
            return self._run_sync(self._get_engagement_summary_async(range_param))
        except Exception as exc:
            logger.warning("x_poster.engagement_summary_sync_failed", error=str(exc))
            return {"ok": False, "error": str(exc), "totals": _empty_totals(), "top_post": None, "posts_tracked": 0, "range": range_param}

    async def _engagement_poll_loop(self) -> None:
        """Poll full-account engagement metrics daily at 00:00 WIB."""
        assert self._x_api is not None
        assert self._db is not None

        # Get authenticated user ID once
        me = await self._x_api.get_me()
        user_id = me.get("id", "")
        if not user_id:
            logger.warning("x_poster.engagement_loop_no_user_id")
            user_id = "1676214373919109122"  # fallback from known config

        while self._running:
            try:
                await self._poll_full_account_engagement(user_id)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("x_poster.engagement_poll_error", error=str(exc))

            # Sleep 15s until next check for 00:00 WIB
            for _ in range(int(24 * 3600 / 15)):
                if not self._running:
                    return
                await asyncio.sleep(15)
                # Check if it's 00:00 WIB (UTC+7 = 17:00 UTC)
                now_utc = asyncio.get_event_loop().time()
                import datetime as _dt
                now_wib = _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=7)))
                if now_wib.hour == 0 and now_wib.minute < 15:
                    break

    async def _poll_full_account_engagement(self, user_id: str) -> None:
        """Fetch all account tweets + engagement, aggregate into daily stats."""
        assert self._db is not None
        assert self._x_api is not None

        logger.info("x_poster.engagement.full_account_poll_starting", user_id=user_id)

        # Step 1: Fetch all recent tweets from the account
        tweets = await self._x_api.get_user_tweets(user_id, max_results=100)
        if not tweets:
            logger.warning("x_poster.engagement.no_tweets_returned")
            return

        # Step 2: Upsert each tweet into p13_account_tweets
        today_wib = asyncio.get_event_loop().time()
        import datetime as _dt
        today = _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=7))).date()

        for t in tweets:
            if not self._running:
                return
            try:
                # Parse created_at from ISO string to datetime
                created_str = t.get("created_at", "")
                created_dt = None
                if created_str:
                    try:
                        created_dt = _dt.datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                    except (ValueError, AttributeError):
                        created_dt = None

                await self._db.execute(
                    """
                    INSERT INTO p13_account_tweets
                        (tweet_id, text, created_at, impressions, likes, replies,
                         retweets, quotes, bookmarks, fetched_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), NOW())
                    ON CONFLICT (tweet_id) DO UPDATE SET
                        impressions = EXCLUDED.impressions,
                        likes = EXCLUDED.likes,
                        replies = EXCLUDED.replies,
                        retweets = EXCLUDED.retweets,
                        quotes = EXCLUDED.quotes,
                        bookmarks = EXCLUDED.bookmarks,
                        fetched_at = NOW(),
                        updated_at = NOW()
                    """,
                    t["tweet_id"],
                    t.get("text", ""),
                    created_dt,
                    int(t.get("impressions", 0)),
                    int(t.get("likes", 0)),
                    int(t.get("replies", 0)),
                    int(t.get("retweets", 0)),
                    int(t.get("quotes", 0)),
                    int(t.get("bookmarks", 0)),
                )
            except Exception as exc:
                logger.warning("x_poster.engagement.upsert_failed", tweet_id=t.get("tweet_id"), error=str(exc))

        # Step 3: Aggregate daily engagement from all account tweets
        for days_ago in range(90):  # Last 90 days
            day = today - _dt.timedelta(days=days_ago)
            day_start = _dt.datetime.combine(day, _dt.time.min).replace(
                tzinfo=_dt.timezone(_dt.timedelta(hours=7))
            )
            day_end = day_start + _dt.timedelta(days=1)

            row = await self._db.fetchrow(
                """
                SELECT
                    COALESCE(SUM(impressions), 0)::bigint AS impressions,
                    COALESCE(SUM(likes), 0)::bigint AS likes,
                    COALESCE(SUM(replies), 0)::bigint AS replies,
                    COALESCE(SUM(retweets), 0)::bigint AS retweets,
                    COALESCE(SUM(quotes), 0)::bigint AS quotes,
                    COALESCE(SUM(bookmarks), 0)::bigint AS bookmarks,
                    COUNT(*)::integer AS tweet_count
                FROM p13_account_tweets
                WHERE created_at >= $1 AND created_at < $2
                """,
                day_start,
                day_end,
            )

            if row and int(row["tweet_count"] or 0) > 0:
                try:
                    await self._db.execute(
                        """
                        INSERT INTO p13_daily_engagement
                            (date, impressions, likes, replies, retweets, quotes,
                             bookmarks, tweet_count, fetched_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
                        ON CONFLICT (date) DO UPDATE SET
                            impressions = EXCLUDED.impressions,
                            likes = EXCLUDED.likes,
                            replies = EXCLUDED.replies,
                            retweets = EXCLUDED.retweets,
                            quotes = EXCLUDED.quotes,
                            bookmarks = EXCLUDED.bookmarks,
                            tweet_count = EXCLUDED.tweet_count,
                            fetched_at = NOW()
                        """,
                        day,
                        int(row["impressions"]),
                        int(row["likes"]),
                        int(row["replies"]),
                        int(row["retweets"]),
                        int(row["quotes"]),
                        int(row["bookmarks"]),
                        int(row["tweet_count"]),
                    )
                except Exception as exc:
                    logger.warning("x_poster.engagement.daily_aggregate_failed", date=str(day), error=str(exc))

        logger.info("x_poster.engagement.full_account_poll_completed", tweets_fetched=len(tweets))

    async def _get_engagement_summary_async(self, range_param: str) -> dict[str, Any]:
        if self._db is None:
            return {"ok": False, "error": "db not initialized", "totals": _empty_totals(), "top_post": None, "posts_tracked": 0, "range": range_param, "daily": []}
        interval = _range_to_interval(range_param)

        # Totals from p13_daily_engagement (authoritative)
        totals = await self._db.fetchrow(
            f"""
            SELECT
                COALESCE(SUM(impressions),0)::bigint AS impressions,
                COALESCE(SUM(likes),0)::bigint AS likes,
                COALESCE(SUM(replies),0)::bigint AS replies,
                COALESCE(SUM(retweets),0)::bigint AS retweets,
                COALESCE(SUM(quotes),0)::bigint AS quotes,
                COALESCE(SUM(bookmarks),0)::bigint AS bookmarks,
                COALESCE(SUM(tweet_count),0)::bigint AS posts_tracked
            FROM p13_daily_engagement
            WHERE date >= CURRENT_DATE - INTERVAL '{interval}'
            """
        )

        # Daily chart: last 30 days
        daily_rows = await self._db.fetch(
            """
            SELECT date, impressions, likes, replies, retweets, quotes, bookmarks, tweet_count
            FROM p13_daily_engagement
            WHERE date >= CURRENT_DATE - INTERVAL '30 days'
            ORDER BY date ASC
            """
        )
        daily_chart = [
            {
                "date": str(row["date"]),
                "impressions": int(row["impressions"]),
                "likes": int(row["likes"]),
                "replies": int(row["replies"]),
                "retweets": int(row["retweets"]),
                "quotes": int(row["quotes"]),
                "bookmarks": int(row["bookmarks"]),
                "tweet_count": int(row["tweet_count"]),
            }
            for row in daily_rows
        ]

        # Top post from account tweets
        top = await self._db.fetchrow(
            """
            SELECT tweet_id, impressions, likes
            FROM p13_account_tweets
            ORDER BY impressions DESC
            LIMIT 1
            """
        )

        return {
            "ok": True,
            "range": range_param,
            "totals": {
                "impressions": int(totals["impressions"]) if totals else 0,
                "likes": int(totals["likes"]) if totals else 0,
                "replies": int(totals["replies"]) if totals else 0,
                "retweets": int(totals["retweets"]) if totals else 0,
                "quotes": int(totals["quotes"]) if totals else 0,
                "bookmarks": int(totals["bookmarks"]) if totals else 0,
            },
            "posts_tracked": int(totals["posts_tracked"]) if totals else 0,
            "top_post": {"tweet_id": top["tweet_id"], "impressions": int(top["impressions"]), "likes": int(top["likes"])} if top else None,
            "daily": daily_chart,
        }

    def list_posts(self, state: str, limit: int) -> list[dict[str, Any]]:
        """Sync API adapter for health server."""
        return self._run_sync(self._list_posts_async(state, limit))

    async def _list_posts_async(self, state: str, limit: int) -> list[dict[str, Any]]:
        assert self._queue is not None
        rows = await self._queue.list_posts(state=state, limit=limit)
        return [self._serialize_post(row) for row in rows]

    def execute_post_action(self, action: str, post_id: str) -> dict[str, Any]:
        """Sync API adapter for post actions."""
        return self._run_sync(self._execute_post_action_async(action, post_id))

    async def _execute_post_action_async(self, action: str, post_id: str) -> dict[str, Any]:
        assert self._queue is not None
        post_uuid = UUID(post_id)

        if action == "cancel":
            await self._queue.cancel(post_uuid)
            new_state = "cancelled"
        elif action == "hold":
            await self._queue.hold(post_uuid)
            new_state = "held"
        elif action == "resume":
            await self._queue.resume(post_uuid)
            new_state = "pending"
        else:
            raise ValueError(f"Unsupported post action: {action}")

        await self._refresh_metrics()
        return {"action": action, "post_id": post_id, "new_state": new_state}

    def retry_all_failed(self) -> int:
        """Sync API adapter for retry failed."""
        return self._run_sync(self._retry_all_failed_async())

    async def _retry_all_failed_async(self) -> int:
        assert self._queue is not None
        assert self._retry_engine is not None

        failed_rows = await self._queue.list_posts(state="failed", limit=100)
        retried = 0
        for row in failed_rows:
            try:
                result = await self._retry_engine.handle_failure(
                    row["id"],
                    Exception(str(row.get("last_error") or "manual retry")),
                )
                if result == "retried":
                    retried += 1
            except Exception as exc:
                logger.warning("x_poster.retry_failed_single_error", post_id=str(row["id"]), error=str(exc))
        await self._refresh_metrics()
        return retried

    def execute_dry_run(self, post_id: str) -> str:
        """Sync API adapter for dry run."""
        return self._run_sync(self._execute_dry_run_async(post_id))

    async def _execute_dry_run_async(self, post_id: str) -> str:
        assert self._queue is not None
        post = await self._queue.get_post(UUID(post_id))
        if not post:
            raise ValueError(f"Post not found: {post_id}")
        media_type = str(post.get("media_type") or "photo")
        media_path = str(post.get("media_path") or "")
        caption = str(post.get("caption") or "").strip()
        if not caption and self._caption is not None:
            caption = await self._caption.generate_caption(post["id"], media_type, media_path)
        return f"dry-run ok: media_type={media_type}, caption={caption[:120]}"

    def enqueue_post(
        self,
        filename: str,
        file_data: bytes,
        content_type: str,
        author_id: str,
        message_id: str,
        caption_hint: str,
    ) -> dict[str, Any]:
        """Sync API adapter for upload handler (single file)."""
        return self._run_sync(
            self._enqueue_post_async(
                filename=filename,
                file_data=file_data,
                content_type=content_type,
                author_id=author_id,
                message_id=message_id,
                caption_hint=caption_hint,
            )
        )

    def enqueue_post_batch(
        self,
        files_data: list[dict[str, Any]],
        author_id: str,
        message_id: str,
        caption_hint: str,
    ) -> dict[str, Any]:
        """Sync API adapter for batch upload handler (multiple files, 1 post)."""
        return self._run_sync(
            self._enqueue_post_batch_async(
                files_data=files_data,
                author_id=author_id,
                message_id=message_id,
                caption_hint=caption_hint,
            )
        )

    def post_now(
        self,
        filename: str,
        file_data: bytes,
        content_type: str,
        author_id: str,
        caption_hint: str,
    ) -> dict[str, Any]:
        """Sync API adapter for immediate post (bypasses queue/schedule)."""
        return self._run_sync(
            self._post_now_async(
                filename=filename,
                file_data=file_data,
                content_type=content_type,
                author_id=author_id,
                caption_hint=caption_hint,
            )
        )

    def post_now_batch(
        self,
        files_data: list[dict[str, Any]],
        author_id: str,
        caption_hint: str,
    ) -> dict[str, Any]:
        """Sync API adapter for immediate batch post (bypasses queue/schedule)."""
        return self._run_sync(
            self._post_now_batch_async(
                files_data=files_data,
                author_id=author_id,
                caption_hint=caption_hint,
            )
        )

    async def _enqueue_post_async(
        self,
        filename: str,
        file_data: bytes,
        content_type: str,
        author_id: str,
        message_id: str,
        caption_hint: str,
    ) -> dict[str, Any]:
        assert self._db is not None
        assert self._storage is not None
        assert self._queue is not None
        assert self._schedule is not None
        assert self._notifications is not None

        media_type = self._resolve_media_type(content_type)
        post_id = await self._queue.enqueue(
            media_path="",
            media_type=media_type,
            caption=caption_hint or None,
            metadata={
                "author_id": author_id,
                "message_id": message_id,
                "original_filename": filename,
                "content_type": content_type,
            },
        )
        saved_path = await asyncio.to_thread(
            self._storage.save_media,
            str(post_id),
            filename,
            file_data,
            "pending",
        )
        _ = await self._db.execute(
            "UPDATE p13_posts SET media_path = $2, updated_at = NOW() WHERE id = $1",
            post_id,
            str(saved_path),
        )
        scheduled_slot = await self._schedule.assign_next_slot(post_id)
        await self._notifications.notify_queue_entry(
            str(post_id),
            str(saved_path),
            media_type,
            scheduled_slot,
        )
        await self._refresh_metrics()
        return {
            "post_id": str(post_id),
            "queue_position": await self._queue.get_queue_depth("scheduled"),
            "estimated_slot": scheduled_slot.isoformat(),
            "filename": filename,
            "content_type": content_type,
            "author_id": author_id,
            "message_id": message_id,
            "caption_hint": caption_hint,
            "size_bytes": len(file_data),
        }

    async def _enqueue_post_batch_async(
        self,
        files_data: list[dict[str, Any]],
        author_id: str,
        message_id: str,
        caption_hint: str,
    ) -> dict[str, Any]:
        """Enqueue multiple media files as a single post (1 tweet with up to 4 media)."""
        assert self._db is not None
        assert self._storage is not None
        assert self._queue is not None
        assert self._schedule is not None
        assert self._notifications is not None

        if not files_data:
            raise ValueError("No files provided")

        # Use first file's content_type for the post
        first_file = files_data[0]
        media_type = self._resolve_media_type(first_file.get("content_type", ""))
        
        # Create post with empty media_path initially
        post_id = await self._queue.enqueue(
            media_path="",
            media_type=media_type,
            caption=caption_hint or None,
            metadata={
                "author_id": author_id,
                "message_id": message_id,
                "original_filename": first_file.get("filename", ""),
                "content_type": first_file.get("content_type", ""),
                "media_count": len(files_data),
            },
        )

        # Save all media files and collect paths
        saved_paths = []
        for file_info in files_data:
            filename = file_info.get("filename", "")
            file_data = file_info.get("data", b"")
            saved_path = await asyncio.to_thread(
                self._storage.save_media,
                str(post_id),
                filename,
                file_data,
                "pending",
            )
            saved_paths.append(str(saved_path))

        # Store all media paths as JSON array in metadata
        import json
        media_paths_json = json.dumps(saved_paths)
        _ = await self._db.execute(
            """UPDATE p13_posts 
               SET media_path = $2, metadata = metadata || $3::jsonb, updated_at = NOW() 
               WHERE id = $1""",
            post_id,
            saved_paths[0],  # Primary path for backward compatibility
            json.dumps({"media_paths": saved_paths}),
        )

        scheduled_slot = await self._schedule.assign_next_slot(post_id)
        await self._notifications.notify_queue_entry(
            str(post_id),
            saved_paths[0],
            media_type,
            scheduled_slot,
        )
        await self._refresh_metrics()
        
        total_size = sum(len(f.get("data", b"")) for f in files_data)
        return {
            "post_id": str(post_id),
            "queue_position": await self._queue.get_queue_depth("scheduled"),
            "estimated_slot": scheduled_slot.isoformat(),
            "filename": first_file.get("filename", ""),
            "content_type": first_file.get("content_type", ""),
            "author_id": author_id,
            "message_id": message_id,
            "caption_hint": caption_hint,
            "size_bytes": total_size,
            "media_count": len(files_data),
        }

    async def _post_now_async(
        self,
        filename: str,
        file_data: bytes,
        content_type: str,
        author_id: str,
        caption_hint: str,
    ) -> dict[str, Any]:
        """Immediate post pipeline — bypasses queue and schedule entirely.

        1. Save media to disk / create DB row (state=in_progress)
        2. Generate caption if empty
        3. Moderate caption
        4. Execute post via Twikit API
        5. Notify success/failure
        6. Return result
        """
        assert self._db is not None
        assert self._storage is not None
        assert self._queue is not None
        assert self._caption is not None
        assert self._moderator is not None
        assert self._poster is not None
        assert self._circuit_breaker is not None
        assert self._notifications is not None
        assert self._timeout_handler is not None

        media_type = self._resolve_media_type(content_type)

        # Step 1 — Create DB row + save file
        post_id = await self._queue.enqueue(
            media_path="",
            media_type=media_type,
            caption=caption_hint or None,
            metadata={
                "author_id": author_id,
                "original_filename": filename,
                "content_type": content_type,
                "immediate": True,
            },
        )
        await self._queue.update_state(post_id, "in_progress")

        saved_path = await asyncio.to_thread(
            self._storage.save_media,
            str(post_id),
            filename,
            file_data,
            "pending",
        )
        _ = await self._db.execute(
            "UPDATE p13_posts SET media_path = $2, updated_at = NOW() WHERE id = $1",
            post_id,
            str(saved_path),
        )

        # Step 2 — Caption (skip generation if empty, media-only posts)
        caption = caption_hint.strip() if caption_hint else ""

        # Step 3 — Moderate
        try:
            moderation = await self._timeout_handler.timeout_moderation(
                self._moderator.moderate_caption(post_id, caption)
            )
        except Exception as exc:
            moderation = ModerationResult(safe=False, reason=str(exc))

        if not moderation.safe:
            await self._queue.update_state(post_id, "failed", last_error=f"Moderation: {moderation.reason}")
            await self._circuit_breaker.record_failure()
            return {
                "ok": False,
                "post_id": str(post_id),
                "error": f"Moderation failed: {moderation.reason}",
                "state": "failed",
            }

        # Step 4 — Execute post
        result = await self._poster.execute_post(
            post_id,
            caption,
            [str(saved_path)],
        )

        # Step 5 — Notify
        if result.success:
            await self._circuit_breaker.record_success()
            await self._queue.update_state(post_id, "completed")
            return {
                "ok": True,
                "post_id": str(post_id),
                "post_url": result.post_url,
                "duration_seconds": result.duration_seconds,
                "caption": caption,
                "media_type": media_type,
                "filename": filename,
            }
        else:
            await self._circuit_breaker.record_failure()
            await self._queue.update_state(post_id, "failed", last_error=result.error)
            return {
                "ok": False,
                "post_id": str(post_id),
                "error": result.error,
                "state": "failed",
            }

    async def _post_now_batch_async(
        self,
        files_data: list[dict[str, Any]],
        author_id: str,
        caption_hint: str,
    ) -> dict[str, Any]:
        """Immediate batch post pipeline — bypasses queue and schedule entirely.

        1. Save all media files to disk / create DB row (state=in_progress)
        2. Moderate caption
        3. Execute post with all media files via X API
        4. Notify success/failure
        5. Return result
        """
        import json
        assert self._db is not None
        assert self._storage is not None
        assert self._queue is not None
        assert self._caption is not None
        assert self._moderator is not None
        assert self._poster is not None
        assert self._circuit_breaker is not None
        assert self._notifications is not None
        assert self._timeout_handler is not None

        if not files_data:
            raise ValueError("No files provided")

        first_file = files_data[0]
        media_type = self._resolve_media_type(first_file.get("content_type", ""))
        filename = first_file.get("filename", "")

        # Step 1 — Create DB row + save all files
        post_id = await self._queue.enqueue(
            media_path="",
            media_type=media_type,
            caption=caption_hint or None,
            metadata={
                "author_id": author_id,
                "original_filename": filename,
                "content_type": first_file.get("content_type", ""),
                "immediate": True,
                "media_count": len(files_data),
            },
        )
        await self._queue.update_state(post_id, "in_progress")

        # Save all media files
        saved_paths = []
        for file_info in files_data:
            file_filename = file_info.get("filename", "")
            file_data = file_info.get("data", b"")
            saved_path = await asyncio.to_thread(
                self._storage.save_media,
                str(post_id),
                file_filename,
                file_data,
                "pending",
            )
            saved_paths.append(str(saved_path))

        # Store all media paths in metadata
        _ = await self._db.execute(
            """UPDATE p13_posts 
               SET media_path = $2, metadata = metadata || $3::jsonb, updated_at = NOW() 
               WHERE id = $1""",
            post_id,
            saved_paths[0],
            json.dumps({"media_paths": saved_paths}),
        )

        # Step 2 — Caption (skip generation if empty, media-only posts)
        caption = caption_hint.strip() if caption_hint else ""

        # Step 3 — Moderate
        try:
            moderation = await self._timeout_handler.timeout_moderation(
                self._moderator.moderate_caption(post_id, caption)
            )
        except Exception as exc:
            moderation = ModerationResult(safe=False, reason=str(exc))

        if not moderation.safe:
            await self._queue.update_state(post_id, "failed", last_error=f"Moderation: {moderation.reason}")
            await self._circuit_breaker.record_failure()
            return {
                "ok": False,
                "post_id": str(post_id),
                "error": f"Moderation failed: {moderation.reason}",
                "state": "failed",
            }

        # Step 4 — Execute post with all media files
        media_paths_with_ids = [(post_id, path) for path in saved_paths]
        result = await self._poster.execute_post_batch(media_paths_with_ids, caption)

        # Step 5 — Notify
        if result.success:
            await self._circuit_breaker.record_success()
            await self._queue.update_state(post_id, "completed")
            return {
                "ok": True,
                "post_id": str(post_id),
                "post_url": result.post_url,
                "duration_seconds": result.duration_seconds,
                "caption": caption,
                "media_type": media_type,
                "filename": filename,
                "media_count": len(files_data),
            }
        else:
            await self._circuit_breaker.record_failure()
            await self._queue.update_state(post_id, "failed", last_error=result.error)
            return {
                "ok": False,
                "post_id": str(post_id),
                "error": result.error,
                "state": "failed",
            }

    def _run_sync(self, coro: Any) -> Any:
        if self._loop is None:
            raise RuntimeError("XPosterService event loop not initialized")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=360)

    def _extract_attempts(self, post: dict[str, Any]) -> int:
        raw = post.get("attempt_count")
        return int(raw) if raw is not None else 0

    def _format_next_slot(self, due_slot: tuple[Any, date] | None) -> str | None:
        if due_slot is None:
            return None
        slot_time, slot_date = due_slot
        return f"{slot_date.isoformat()} {slot_time.strftime('%H:%M')}"

    def _resolve_media_type(self, content_type: str) -> str:
        if content_type.startswith("video/"):
            return "video"
        return "photo"

    def _serialize_post(self, row: dict[str, Any]) -> dict[str, Any]:
        serialized: dict[str, Any] = {}
        for key, value in row.items():
            if isinstance(value, UUID):
                serialized[key] = str(value)
            elif hasattr(value, "isoformat"):
                serialized[key] = value.isoformat()
            else:
                serialized[key] = value
        return serialized


__all__ = ["XPosterService"]
