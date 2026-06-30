"""P13 X Auto Poster — PostgreSQL-backed FIFO queue manager."""

from __future__ import annotations

import json
import structlog
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from .config import get_xposter_settings
from .db import DatabaseManager
from .exceptions import DatabaseConnectionError, DatabaseQueryError, QueueError, QueueFullError
from .metrics import record_post, set_queue_depth

_logger = structlog.get_logger(__name__)

VALID_STATES = frozenset(
    {"pending", "scheduled", "in_progress", "completed", "failed", "held", "cancelled"}
)
VALID_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending": frozenset({"scheduled", "in_progress", "held", "cancelled"}),
    "scheduled": frozenset({"in_progress", "held", "cancelled"}),
    "in_progress": frozenset({"completed", "failed"}),
    "failed": frozenset({"pending", "held", "cancelled"}),
    "held": frozenset({"pending", "cancelled"}),
    "completed": frozenset(),
    "cancelled": frozenset(),
}


class QueueManager:
    """Manages the PostgreSQL-backed posting queue (p13_posts table)."""

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db
        self._settings = get_xposter_settings()

    async def enqueue(
        self,
        media_path: str,
        media_type: str,
        caption: str | None = None,
        priority: int = 4,
        metadata: dict[str, Any] | None = None,
    ) -> UUID:
        """Add post to queue. Returns post_id.

        Raises QueueError on failure.
        """
        post_id = uuid4()
        query = """
            INSERT INTO p13_posts (id, media_path, media_type, caption, state, priority, metadata)
            VALUES ($1, $2, $3, $4, 'pending', $5, $6)
            RETURNING id
        """
        try:
            row = await self._db.fetchrow(
                query,
                post_id,
                media_path,
                media_type,
                caption,
                priority,
                json.dumps(metadata or {}),
            )
            if row is None:
                raise QueueError("INSERT returned no row")
            _logger.info(
                "x_poster.queue.enqueued",
                post_id=str(post_id),
                media_type=media_type,
                priority=priority,
            )
            record_post("queued")
            await self._refresh_depth("pending")
            return post_id
        except DatabaseQueryError as exc:
            raise QueueError(f"Failed to enqueue post {post_id}: {exc.message}") from exc

    async def dequeue_next(self) -> dict[str, Any] | None:
        """Fetch next pending post (ORDER BY priority ASC, created_at ASC).

        Atomically transitions state from 'pending' to 'in_progress'.
        Returns dict or None if queue is empty.
        """
        query = """
            UPDATE p13_posts
            SET state = 'in_progress', updated_at = NOW()
            WHERE id = (
                SELECT id FROM p13_posts
                WHERE state = 'pending'
                ORDER BY priority ASC, created_at ASC
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            )
            RETURNING id, media_path, media_type, caption, priority,
                      metadata, attempt_count, max_attempts, scheduled_slot
        """
        try:
            row = await self._db.fetchrow(query)
            if row is None:
                return None
            _logger.info(
                "x_poster.queue.dequeued",
                post_id=str(row["id"]),
                priority=row["priority"],
            )
            await self._refresh_depth("pending")
            await self._refresh_depth("in_progress")
            return row
        except DatabaseQueryError as exc:
            _logger.error("x_poster.queue.dequeue_failed", error=exc.message)
            return None

    async def update_state(
        self,
        post_id: UUID,
        state: str,
        last_error: str | None = None,
        post_url: str | None = None,
    ) -> None:
        """Update post state. Validates state transitions.

        Raises QueueError if transition is invalid.
        Raises DatabaseQueryError if DB operation fails.
        """
        if state not in VALID_STATES:
            raise QueueError(f"Invalid state: {state}")

        # Get current state to validate transition
        current = await self._get_state(post_id)
        if current is None:
            raise QueueError(f"Post {post_id} not found")

        allowed = VALID_TRANSITIONS.get(current, frozenset())
        if state not in allowed and state != current:
            raise QueueError(
                f"Invalid transition from '{current}' to '{state}' for post {post_id}"
            )

        query = """
            UPDATE p13_posts
            SET state = $2, last_error = $3, post_url = $4, updated_at = NOW()
            WHERE id = $1
        """
        extra: dict[str, Any] = {}
        if state == "completed":
            extra["posted_at"] = datetime.now(timezone.utc)
            extra["state"] = state
            extra_query = """
                UPDATE p13_posts
                SET state = $2, last_error = $3, post_url = $4,
                    updated_at = NOW(), posted_at = NOW()
                WHERE id = $1
            """
            await self._db.execute(extra_query, post_id, state, last_error, post_url)
        else:
            await self._db.execute(query, post_id, state, last_error, post_url)

        _logger.info(
            "x_poster.queue.state_changed",
            post_id=str(post_id),
            from_state=current,
            to_state=state,
        )

        # Record metrics
        if state in ("completed", "failed", "cancelled"):
            record_post(state)
        await self._refresh_depth(state)
        if current in ("pending", "in_progress", "scheduled"):
            await self._refresh_depth(current)

    async def increment_attempts(self, post_id: UUID, max_attempts: int = 3) -> bool:
        """Increment attempt_count. Return True if still under max_attempts.

        If exceeded, state is set to 'failed'.
        """
        query = """
            UPDATE p13_posts
            SET attempt_count = attempt_count + 1, updated_at = NOW()
            WHERE id = $1
            RETURNING attempt_count
        """
        row = await self._db.fetchrow(query, post_id)
        if row is None:
            return False

        count = row["attempt_count"]
        _logger.info(
            "x_poster.queue.attempt_incremented",
            post_id=str(post_id),
            attempt=count,
            max_attempts=max_attempts,
        )

        if count >= max_attempts:
            await self.update_state(post_id, "failed", last_error="Max attempts exceeded")
            return False
        return True

    async def hold(self, post_id: UUID) -> None:
        """Set state to 'held'."""
        await self.update_state(post_id, "held")

    async def resume(self, post_id: UUID) -> None:
        """Set state back to 'pending'."""
        await self.update_state(post_id, "pending")

    async def cancel(self, post_id: UUID) -> None:
        """Set state to 'cancelled'."""
        await self.update_state(post_id, "cancelled")

    async def get_queue_depth(self, state: str = "pending") -> int:
        """Return count of posts in given state."""
        query = "SELECT COUNT(*) AS cnt FROM p13_posts WHERE state = $1"
        row = await self._db.fetchrow(query, state)
        if row is None:
            return 0
        return int(row["cnt"])

    async def list_posts(
        self, state: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        """List posts by state, ordered by priority ASC then created_at ASC."""
        if state:
            query = """
                SELECT id, media_path, media_type, caption, state, priority,
                       scheduled_slot, attempt_count, max_attempts, last_error,
                       created_at, updated_at, posted_at, post_url, metadata
                FROM p13_posts
                WHERE state = $1
                ORDER BY priority ASC, created_at ASC
                LIMIT $2
            """
            return await self._db.fetch(query, state, limit)
        query = """
            SELECT id, media_path, media_type, caption, state, priority,
                   scheduled_slot, attempt_count, max_attempts, last_error,
                   created_at, updated_at, posted_at, post_url, metadata
            FROM p13_posts
            ORDER BY priority ASC, created_at ASC
            LIMIT $1
        """
        return await self._db.fetch(query, limit)

    async def get_post(self, post_id: UUID) -> dict[str, Any] | None:
        """Fetch single post by ID."""
        query = """
            SELECT id, media_path, media_type, caption, state, priority,
                   scheduled_slot, attempt_count, max_attempts, last_error,
                   created_at, updated_at, posted_at, post_url, metadata
            FROM p13_posts WHERE id = $1
        """
        return await self._db.fetchrow(query, post_id)

    # --- Private helpers ---

    async def _get_state(self, post_id: UUID) -> str | None:
        """Get current state for a post."""
        query = "SELECT state FROM p13_posts WHERE id = $1"
        row = await self._db.fetchrow(query, post_id)
        if row is None:
            return None
        return row["state"]

    async def _refresh_depth(self, state: str) -> None:
        """Refresh queue depth metric for given state."""
        count = await self.get_queue_depth(state)
        set_queue_depth(state, count)
