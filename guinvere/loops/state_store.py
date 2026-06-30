"""PostgreSQL-backed loop state persistence.

Survives VPS restart by storing loop state in ``projects.loop_instances``
rather than keeping it only in memory.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class LoopStatus(str, Enum):
    """Lifecycle status of a loop instance."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class LoopState:
    """Immutable snapshot of a loop instance.

    Fields stored partly in ``projects.loop_instances`` columns and partly in
    the ``result_summary`` JSONB blob.
    """

    loop_id: str
    task: str
    goal: str = ""
    principal: str = ""
    priority: str = ""
    trigger_source: str = ""
    phase: int = 1
    phase_artifacts: dict[str, str] = field(default_factory=dict)
    status: LoopStatus = LoopStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    checkpoint_data: dict = field(default_factory=dict)
    retry_count: int = 0
    error_message: Optional[str] = None
    parent_loop_id: Optional[str] = None

    def __post_init__(self) -> None:
        if not 1 <= self.phase <= 7:
            raise ValueError(f"phase must be between 1 and 7, got {self.phase}")


class LoopStateStore:
    """Persist and retrieve loop state from ``projects.loop_instances``.

    The store uses an raw-SQL approach against the existing table so it can
    read and write the checkpoint columns without modifying
    ``guinvere/memory/models.py``.
    """

    def __init__(
        self,
        session_factory: Callable[[], AbstractAsyncContextManager[AsyncSession]],
    ) -> None:
        self._session_factory = session_factory

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def create(self, state: LoopState) -> LoopState:
        """INSERT a new loop state and return the persisted record."""
        summary = self._state_to_summary(state)
        insert_sql = text(
            """
            INSERT INTO projects.loop_instances (
                status,
                started_at,
                loop_phase,
                goal,
                retry_count,
                result_summary,
                checkpoint_data,
                phase,
                phase_artifacts,
                parent_loop_id,
                error_message
            ) VALUES (
                :status,
                :started_at,
                :loop_phase,
                :goal,
                :retry_count,
                :result_summary,
                :checkpoint_data,
                :phase,
                :phase_artifacts,
                :parent_loop_id,
                :error_message
            )
            RETURNING id
            """
        )
        params: dict[str, Any] = {
            "status": state.status.value,
            "started_at": state.created_at,
            "loop_phase": f"phase_{state.phase}",
            "goal": state.goal,
            "retry_count": state.retry_count,
            "result_summary": summary,
            "checkpoint_data": state.checkpoint_data,
            "phase": state.phase,
            "phase_artifacts": state.phase_artifacts,
            "parent_loop_id": state.parent_loop_id,
            "error_message": state.error_message,
        }

        async with self._session_factory() as session:
            await session.execute(insert_sql, params)
            await session.commit()
            return await self._fetch_by_loop_id(session, state.loop_id)

    async def get(self, loop_id: str) -> LoopState | None:
        """SELECT a loop state by its loop_id."""
        async with self._session_factory() as session:
            return await self._fetch_by_loop_id(session, loop_id)

    async def update(self, loop_id: str, **fields: object) -> LoopState:
        """UPDATE specific fields of a loop and return the updated state."""
        summary_fields = {"task", "goal", "principal", "priority", "trigger_source", "loop_id"}
        db_fields = {
            "status",
            "phase",
            "phase_artifacts",
            "checkpoint_data",
            "retry_count",
            "error_message",
            "parent_loop_id",
        }

        async with self._session_factory() as session:
            row = await self._fetch_row(session, loop_id)
            if row is None:
                raise ValueError(f"Loop {loop_id} not found")

            summary: dict[str, Any] = dict(row.get("result_summary") or {})
            current: dict[str, Any] = {
                "status": row["status"],
                "phase": row.get("phase") or 1,
                "phase_artifacts": row.get("phase_artifacts") or {},
                "checkpoint_data": row.get("checkpoint_data") or {},
                "retry_count": row.get("retry_count") or 0,
                "error_message": row.get("error_message"),
                "parent_loop_id": row.get("parent_loop_id"),
                "goal": row.get("goal"),
            }

            for key, value in fields.items():
                if key in summary_fields:
                    if key == "goal":
                        current["goal"] = value
                    summary[key] = value
                elif key in db_fields:
                    current[key] = value
                else:
                    raise ValueError(f"Unsupported update field: {key}")

            status_value = current["status"]
            if isinstance(status_value, LoopStatus):
                status_value = status_value.value

            update_sql = text(
                """
                UPDATE projects.loop_instances
                SET status = :status,
                    phase = :phase,
                    phase_artifacts = :phase_artifacts,
                    checkpoint_data = :checkpoint_data,
                    retry_count = :retry_count,
                    error_message = :error_message,
                    parent_loop_id = :parent_loop_id,
                    goal = :goal,
                    result_summary = :result_summary
                WHERE result_summary ->> 'loop_id' = :loop_id
                """
            )
            await session.execute(
                update_sql,
                {
                    "status": status_value,
                    "phase": current["phase"],
                    "phase_artifacts": current["phase_artifacts"],
                    "checkpoint_data": current["checkpoint_data"],
                    "retry_count": current["retry_count"],
                    "error_message": current["error_message"],
                    "parent_loop_id": current["parent_loop_id"],
                    "goal": current["goal"],
                    "result_summary": summary,
                    "loop_id": loop_id,
                },
            )
            await session.commit()
            return await self._fetch_by_loop_id(session, loop_id)

    async def delete(self, loop_id: str) -> bool:
        """DELETE a loop state by loop_id."""
        sql = text(
            """
            DELETE FROM projects.loop_instances
            WHERE result_summary ->> 'loop_id' = :loop_id
            """
        )
        async with self._session_factory() as session:
            result = await session.execute(sql, {"loop_id": loop_id})
            await session.commit()
            return result.rowcount is not None and result.rowcount > 0

    async def list_by_status(self, status: str, limit: int = 100) -> list[LoopState]:
        """List loop states filtered by status."""
        sql = text(
            """
            SELECT id, status, started_at, completed_at, loop_phase, goal,
                   retry_count, result_summary, checkpoint_data, phase,
                   phase_artifacts, parent_loop_id, error_message
            FROM projects.loop_instances
            WHERE status = :status
            LIMIT :limit
            """
        )
        async with self._session_factory() as session:
            result = await session.execute(sql, {"status": status, "limit": limit})
            rows = result.mappings().all()
            return [self._row_to_state(row) for row in rows]

    async def save_checkpoint(self, loop_id: str, phase: int, data: dict) -> None:
        """Persist a phase checkpoint for the given loop."""
        sql = text(
            """
            UPDATE projects.loop_instances
            SET phase = :phase,
                checkpoint_data = :data
            WHERE result_summary ->> 'loop_id' = :loop_id
            """
        )
        async with self._session_factory() as session:
            result = await session.execute(
                sql, {"phase": phase, "data": data, "loop_id": loop_id}
            )
            await session.commit()
            if result.rowcount == 0:
                raise ValueError(f"Loop {loop_id} not found")

    async def load_checkpoint(self, loop_id: str) -> tuple[int, dict] | None:
        """Load the latest checkpoint for a loop."""
        sql = text(
            """
            SELECT phase, checkpoint_data
            FROM projects.loop_instances
            WHERE result_summary ->> 'loop_id' = :loop_id
            """
        )
        async with self._session_factory() as session:
            result = await session.execute(sql, {"loop_id": loop_id})
            row = result.mappings().first()
            if row is None:
                return None
            return int(row["phase"]), dict(row["checkpoint_data"] or {})

    async def mark_completed(self, loop_id: str, result_summary: str) -> None:
        """Mark a loop as completed and store the summary."""
        async with self._session_factory() as session:
            row = await self._fetch_row(session, loop_id)
            if row is None:
                raise ValueError(f"Loop {loop_id} not found")

            summary: dict[str, Any] = dict(row.get("result_summary") or {})
            summary["summary"] = result_summary

            update_sql = text(
                """
                UPDATE projects.loop_instances
                SET status = 'completed',
                    result_summary = :result_summary,
                    completed_at = now()
                WHERE result_summary ->> 'loop_id' = :loop_id
                """
            )
            await session.execute(
                update_sql,
                {"result_summary": summary, "loop_id": loop_id},
            )
            await session.commit()

    async def mark_failed(self, loop_id: str, error: str) -> None:
        """Mark a loop as failed and record the error message."""
        sql = text(
            """
            UPDATE projects.loop_instances
            SET status = 'failed',
                error_message = :error
            WHERE result_summary ->> 'loop_id' = :loop_id
            """
        )
        async with self._session_factory() as session:
            result = await session.execute(sql, {"error": error, "loop_id": loop_id})
            await session.commit()
            if result.rowcount == 0:
                raise ValueError(f"Loop {loop_id} not found")

    async def resume_interrupted(self) -> list[LoopState]:
        """Return all loops that were running when the process crashed."""
        sql = text(
            """
            SELECT id, status, started_at, completed_at, loop_phase, goal,
                   retry_count, result_summary, checkpoint_data, phase,
                   phase_artifacts, parent_loop_id, error_message
            FROM projects.loop_instances
            WHERE status = 'running'
            """
        )
        async with self._session_factory() as session:
            result = await session.execute(sql)
            rows = result.mappings().all()
            return [self._row_to_state(row) for row in rows]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _state_to_summary(state: LoopState) -> dict[str, Any]:
        return {
            "loop_id": state.loop_id,
            "task": state.task,
            "goal": state.goal,
            "principal": state.principal,
            "priority": state.priority,
            "trigger_source": state.trigger_source,
        }

    async def _fetch_by_loop_id(
        self, session: AsyncSession, loop_id: str
    ) -> LoopState | None:
        row = await self._fetch_row(session, loop_id)
        if row is None:
            return None
        return self._row_to_state(row)

    async def _fetch_row(self, session: AsyncSession, loop_id: str) -> Any | None:
        sql = text(
            """
            SELECT id, status, started_at, completed_at, loop_phase, goal,
                   retry_count, result_summary, checkpoint_data, phase,
                   phase_artifacts, parent_loop_id, error_message
            FROM projects.loop_instances
            WHERE result_summary ->> 'loop_id' = :loop_id
            """
        )
        result = await session.execute(sql, {"loop_id": loop_id})
        return result.mappings().first()

    @staticmethod
    def _row_to_state(row: Any) -> LoopState:
        summary: dict[str, Any] = dict(row.get("result_summary") or {})
        status_value = row["status"]
        try:
            status = LoopStatus(status_value)
        except ValueError as exc:
            raise ValueError(f"Unsupported loop status in DB: {status_value}") from exc

        return LoopState(
            loop_id=summary.get("loop_id", ""),
            task=summary.get("task", ""),
            goal=summary.get("goal", row.get("goal") or ""),
            principal=summary.get("principal", ""),
            priority=summary.get("priority", ""),
            trigger_source=summary.get("trigger_source", ""),
            phase=int(row.get("phase") or 1),
            phase_artifacts=dict(row.get("phase_artifacts") or {}),
            status=status,
            created_at=row["started_at"],
            updated_at=row["completed_at"] or row["started_at"],
            checkpoint_data=dict(row.get("checkpoint_data") or {}),
            retry_count=int(row.get("retry_count") or 0),
            error_message=row.get("error_message"),
            parent_loop_id=row.get("parent_loop_id"),
        )


__all__ = [
    "LoopStateStore",
    "LoopState",
    "LoopStatus",
]
