"""Kanban-style backlog with priority queue and aging.

The ``Backlog`` keeps discovered task signals in memory and can optionally
persist state through the existing ``LoopStateStore`` infrastructure.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Literal

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from guinvere.loops.dedup import DeduplicationFilter
from guinvere.loops.state_store import LoopStateStore

if TYPE_CHECKING:
    from guinvere.loops.discovery import TaskSignal

logger = logging.getLogger(__name__)


BacklogStatus = Literal["pending", "claimed", "completed", "cancelled"]


@dataclass(frozen=True)
class BacklogItem:
    """Immutable entry in the discovery backlog."""

    item_id: str
    signal: "TaskSignal"
    priority_score: float
    created_at: datetime
    status: BacklogStatus
    claimed_by: str | None
    claim_count: int
    last_scored_at: datetime


class Backlog:
    """Priority backlog with aging for autonomous task discovery.

    Parameters
    ----------
    state_store:
        Optional ``LoopStateStore`` used for PostgreSQL persistence.  The
        backlog falls back to in-memory storage when the store is omitted.
    session_factory:
        Optional raw SQLAlchemy session factory.  When supplied together with
        ``agent_id``, backlog entries are mirrored to ``agents.task_queue``.
    agent_id:
        Agent identifier required for DB mirroring.
    """

    def __init__(
        self,
        state_store: LoopStateStore | None = None,
        session_factory: Callable[[], AbstractAsyncContextManager[object]]
        | None = None,
        *,
        agent_id: str | None = None,
    ) -> None:
        self._state_store = state_store
        self._session_factory = session_factory
        self._agent_id = agent_id
        self._items: dict[str, BacklogItem] = {}
        self._base_scores: dict[str, float] = {}
        self._hashes: set[str] = set()

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    @staticmethod
    def _score_signal(signal: "TaskSignal") -> float:
        """Compute the base priority score for a signal using WSJF.

        Uses the formula::

            (urgency + value + feasibility) * (1 / (1 + cost))

        Metadata keys ``urgency``, ``value``, ``feasibility``, and ``cost``
        override defaults.  ``signal.priority_hint`` supplies the default urgency.
        """
        metadata = signal.metadata or {}
        urgency = float(metadata.get("urgency", signal.priority_hint))
        value = float(metadata.get("value", 0.5))
        feasibility = float(metadata.get("feasibility", 0.5))
        cost = max(float(metadata.get("cost", 1.0)), 0.0)

        if not (0.0 <= urgency <= 1.0):
            urgency = max(0.0, min(urgency, 1.0))
        if not (0.0 <= value <= 1.0):
            value = max(0.0, min(value, 1.0))
        if not (0.0 <= feasibility <= 1.0):
            feasibility = max(0.0, min(feasibility, 1.0))

        base_score = (urgency + value + feasibility) * (1.0 / (1.0 + cost))
        return round(min(max(base_score, 0.0), 1.0), 6)

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    async def add(self, signal: "TaskSignal") -> BacklogItem | None:
        """Add *signal* to the backlog if it is not a duplicate.

        Auto-scores the signal and returns the created ``BacklogItem``.
        Returns ``None`` when the signal is a duplicate.
        """
        content_hash = DeduplicationFilter.compute_hash(
            signal.title, signal.description, signal.source
        )
        if content_hash in self._hashes:
            return None

        now = datetime.now(timezone.utc)
        base_score = self._score_signal(signal)
        item_id = str(uuid.uuid4())
        item = BacklogItem(
            item_id=item_id,
            signal=signal,
            priority_score=base_score,
            created_at=now,
            status="pending",
            claimed_by=None,
            claim_count=0,
            last_scored_at=now,
        )

        self._items[item_id] = item
        self._base_scores[item_id] = base_score
        self._hashes.add(content_hash)

        if self._session_factory is not None and self._agent_id is not None:
            await self._mirror_to_db(item)

        return item

    async def claim(self, loop_id: str) -> BacklogItem | None:
        """Return the highest-priority pending item and mark it as claimed."""
        candidates = [
            item
            for item in self._items.values()
            if item.status == "pending"
        ]
        if not candidates:
            return None

        candidates.sort(
            key=lambda item: (item.priority_score, -item.created_at.timestamp()),
            reverse=True,
        )
        chosen = candidates[0]
        updated = BacklogItem(
            item_id=chosen.item_id,
            signal=chosen.signal,
            priority_score=chosen.priority_score,
            created_at=chosen.created_at,
            status="claimed",
            claimed_by=loop_id,
            claim_count=chosen.claim_count + 1,
            last_scored_at=chosen.last_scored_at,
        )
        self._items[chosen.item_id] = updated
        return updated

    async def complete(self, item_id: str, result_summary: str) -> None:
        """Mark the item as completed and record the summary."""
        item = self._items.get(item_id)
        if item is None:
            return
        logger.info("backlog_item_completed", item_id=item_id, summary=result_summary)
        updated = BacklogItem(
            item_id=item.item_id,
            signal=item.signal,
            priority_score=item.priority_score,
            created_at=item.created_at,
            status="completed",
            claimed_by=item.claimed_by,
            claim_count=item.claim_count,
            last_scored_at=item.last_scored_at,
        )
        self._items[item_id] = updated

    async def cancel(self, item_id: str, reason: str) -> None:
        """Mark the item as cancelled and log the reason."""
        item = self._items.get(item_id)
        if item is None:
            return
        logger.info("backlog_item_cancelled", item_id=item_id, reason=reason)
        updated = BacklogItem(
            item_id=item.item_id,
            signal=item.signal,
            priority_score=item.priority_score,
            created_at=item.created_at,
            status="cancelled",
            claimed_by=item.claimed_by,
            claim_count=item.claim_count,
            last_scored_at=item.last_scored_at,
        )
        self._items[item_id] = updated

    async def get_pending(self, limit: int = 20) -> list[BacklogItem]:
        """Return pending items sorted by priority (highest first)."""
        pending = [item for item in self._items.values() if item.status == "pending"]
        pending.sort(
            key=lambda item: (item.priority_score, -item.created_at.timestamp()),
            reverse=True,
        )
        return pending[:limit]

    async def get_by_id(self, item_id: str) -> BacklogItem | None:
        """Return the backlog item with the given identifier."""
        return self._items.get(item_id)

    async def apply_aging(self) -> int:
        """Recalculate priority scores with aging.

        Returns the number of pending/claimed items aged.
        """
        now = datetime.now(timezone.utc)
        updated_items: list[BacklogItem] = []
        count = 0

        for item in self._items.values():
            if item.status not in {"pending", "claimed"}:
                continue
            base_score = self._base_scores.get(item.item_id, item.priority_score)
            aging_hours = (now - item.created_at).total_seconds() / 3600.0
            adjusted = base_score * (1.0 + aging_hours * 0.01)
            updated = BacklogItem(
                item_id=item.item_id,
                signal=item.signal,
                priority_score=round(min(adjusted, 1.0), 6),
                created_at=item.created_at,
                status=item.status,
                claimed_by=item.claimed_by,
                claim_count=item.claim_count,
                last_scored_at=now,
            )
            updated_items.append(updated)
            self._base_scores[item.item_id] = base_score
            count += 1

        for updated in updated_items:
            self._items[updated.item_id] = updated

        return count

    async def size(self, status: str | None = None) -> int:
        """Return the number of items, optionally filtered by status."""
        if status is None:
            return len(self._items)
        return sum(1 for item in self._items.values() if item.status == status)

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    async def _mirror_to_db(self, item: BacklogItem) -> None:
        """Mirror a newly created backlog item to ``agents.task_queue``."""
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
                :agent_id, :task_payload, :priority, 'pending'
            )
            """
        )
        params = {
            "agent_id": agent_uuid,
            "task_payload": {
                "item_id": item.item_id,
                "title": item.signal.title,
                "source": item.signal.source,
                "status": item.status,
            },
            "priority": int(item.priority_score * 10),
        }
        try:
            async with self._session_factory() as session:
                await session.execute(sql, params)
                await session.commit()
        except SQLAlchemyError as exc:
            logger.warning("backlog_mirror_db_failed", exc_info=exc)


__all__ = ["Backlog", "BacklogItem"]
