"""Loop de-duplication filter for autonomous task discovery.

Provides a content-hash based duplicate detector with optional PostgreSQL
persistence backed by the existing ``agents.task_queue`` table.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class _DedupRecord:
    """In-memory duplicate record with timestamp."""

    item_id: str
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class DeduplicationFilter:
    """Detect and record content hashes to avoid duplicate backlog items.

    Parameters
    ----------
    session_factory:
        Optional callable returning an async context manager that yields a
        SQLAlchemy ``AsyncSession``. When provided, dedup entries are persisted
        in ``agents.task_queue`` so they survive restarts.
    agent_id:
        Optional agent identifier required when persisting to
        ``agents.task_queue`` (the table has a non-nullable ``agent_id`` FK).
        If omitted, persistence is disabled even when ``session_factory`` is
        supplied.
    """

    def __init__(
        self,
        session_factory: Callable[[], AbstractAsyncContextManager[AsyncSession]]
        | None = None,
        *,
        agent_id: str | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._agent_id = agent_id
        self._records: dict[str, _DedupRecord] = {}

    # ------------------------------------------------------------------
    # Hash computation
    # ------------------------------------------------------------------

    @staticmethod
    def compute_hash(title: str, description: str, source: str) -> str:
        """Return a SHA-256 hash of ``title|description|source``.

        Normalises inputs by stripping whitespace before hashing.
        """
        payload = f"{title.strip()}|{description.strip()}|{source.strip()}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # Duplicate detection
    # ------------------------------------------------------------------

    async def is_duplicate(self, content_hash: str) -> bool:
        """Return ``True`` if *content_hash* is known in active records.

        Checks the in-memory cache first, then the optional PostgreSQL store.
        """
        if content_hash in self._records:
            return True

        if self._session_factory is None or self._agent_id is None:
            return False

        sql = text(
            """
            SELECT 1
            FROM agents.task_queue
            WHERE task_payload ->> 'content_hash' = :content_hash
              AND status = 'dedup'
            LIMIT 1
            """
        )
        try:
            async with self._session_factory() as session:
                result = await session.execute(sql, {"content_hash": content_hash})
                row = result.fetchone()
                return row is not None
        except SQLAlchemyError as exc:
            logger.warning("dedup_db_check_failed", exc_info=exc)
            return False

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    async def record(self, content_hash: str, item_id: str) -> None:
        """Record *content_hash* so future duplicates can be detected."""
        self._records[content_hash] = _DedupRecord(item_id=item_id)

        if self._session_factory is None or self._agent_id is None:
            return

        try:
            agent_uuid = uuid.UUID(self._agent_id)
        except ValueError as exc:
            raise ValueError(
                f"agent_id must be a valid UUID: {self._agent_id}"
            ) from exc

        sql = text(
            """
            INSERT INTO agents.task_queue (
                agent_id, task_payload, priority, status
            ) VALUES (
                :agent_id, :task_payload, :priority, 'dedup'
            )
            ON CONFLICT DO NOTHING
            """
        )
        params = {
            "agent_id": agent_uuid,
            "task_payload": {
                "content_hash": content_hash,
                "item_id": item_id,
            },
            "priority": 0,
        }
        try:
            async with self._session_factory() as session:
                await session.execute(sql, params)
                await session.commit()
        except SQLAlchemyError as exc:
            logger.warning("dedup_db_record_failed", exc_info=exc)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def cleanup(self, max_age_hours: int = 48) -> int:
        """Remove dedup entries older than *max_age_hours*.

        Returns the number of in-memory and database entries removed.
        """
        cutoff = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
        cutoff_dt = datetime.fromtimestamp(cutoff, tz=timezone.utc)

        removed = 0
        stale = [
            content_hash
            for content_hash, record in self._records.items()
            if record.recorded_at.timestamp() < cutoff
        ]
        for content_hash in stale:
            del self._records[content_hash]
            removed += 1

        if self._session_factory is not None and self._agent_id is not None:
            sql = text(
                """
                DELETE FROM agents.task_queue
                WHERE status = 'dedup'
                  AND created_at < :cutoff
                """
            )
            try:
                async with self._session_factory() as session:
                    result = await session.execute(sql, {"cutoff": cutoff_dt})
                    await session.commit()
                    if result.rowcount:
                        removed += result.rowcount
            except SQLAlchemyError as exc:
                logger.warning("dedup_db_cleanup_failed", exc_info=exc)

        return removed


__all__ = ["DeduplicationFilter"]
