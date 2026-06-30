"""Restart recovery infrastructure for autonomous loops.

This module lets a loop resume from its last checkpoint after a process
restart, skipping phases that were already completed before the crash.
"""

from __future__ import annotations

import asyncio
import enum
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("guinevere.loops.recovery")


class PhaseCheckpoint(enum.Enum):
    """Status of a single phase checkpoint."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class Checkpoint:
    """Immutable snapshot of a loop checkpoint.

    Attributes:
        loop_id: Identifier of the loop this checkpoint belongs to.
        phase: The phase number (1-7) this checkpoint records.
        task_hash: SHA-256 of ``task:goal`` used for idempotency checks.
        completed_at: Timestamp when the checkpoint was recorded.
        artifact_summary: Brief summary of what was produced in this phase.
        metadata: Extensible metadata for extra recovery context.
    """

    loop_id: str
    phase: int
    task_hash: str
    completed_at: datetime
    artifact_summary: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Serialize this checkpoint to a JSON-friendly dictionary."""
        return {
            "loop_id": self.loop_id,
            "phase": self.phase,
            "task_hash": self.task_hash,
            "completed_at": self.completed_at.isoformat(),
            "artifact_summary": self.artifact_summary,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Checkpoint":
        """Reconstruct a :class:`Checkpoint` from a dictionary."""
        completed_at = data.get("completed_at")
        if isinstance(completed_at, str):
            completed_at = datetime.fromisoformat(completed_at)
        else:
            completed_at = datetime.now(timezone.utc)

        return cls(
            loop_id=data["loop_id"],
            phase=data["phase"],
            task_hash=data["task_hash"],
            completed_at=completed_at,
            artifact_summary=data.get("artifact_summary", ""),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(frozen=True)
class RecoveryResult:
    """Result of analysing how a loop should resume after a restart."""

    resume_from_phase: int
    skipped_phases: list[int]
    checkpoint: Checkpoint | None
    can_resume: bool
    reason: str


class RecoveryManager:
    """Manages loop checkpoints for restart recovery.

    Uses PostgreSQL via :class:`~src.loops.state_store.LoopStateStore` to
    persist checkpoints. On restart, reads the last checkpoint and determines
    which phases to skip.
    """

    def __init__(self, state_store: Any = None) -> None:
        """Create a new recovery manager.

        Args:
            state_store: A ``LoopStateStore`` instance. If ``None``, the
                manager operates in-memory only and checkpoints will not
                survive process restarts.
        """
        self._state_store: Any = state_store
        self._memory: dict[str, Checkpoint] = {}
        self._lock = asyncio.Lock()
        if state_store is None:
            logger.warning(
                "RecoveryManager operating in-memory only, checkpoints will be lost on restart"
            )

    @staticmethod
    def compute_task_hash(task: str, goal: str) -> str:
        """Return the SHA-256 hash of ``task:goal`` for idempotency checks."""
        payload = f"{task}:{goal}".encode()
        return hashlib.sha256(payload).hexdigest()

    async def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Persist checkpoint to PostgreSQL (or in-memory fallback)."""
        if self._state_store is not None:
            data = checkpoint.to_dict()
            try:
                await self._state_store.save_checkpoint(
                    checkpoint.loop_id, checkpoint.phase, data
                )
            except Exception as exc:
                logger.exception(
                    "Failed to persist checkpoint for loop %s", checkpoint.loop_id
                )
                raise RuntimeError(
                    f"Could not save checkpoint for loop {checkpoint.loop_id}"
                ) from exc
        else:
            async with self._lock:
                self._memory[checkpoint.loop_id] = checkpoint

    async def load_checkpoint(self, loop_id: str) -> Checkpoint | None:
        """Load last checkpoint for a loop."""
        if self._state_store is not None:
            raw = await self._state_store.load_checkpoint(loop_id)
            if raw is None:
                return None
            phase, data = raw
            if not isinstance(data, dict):
                return None
            try:
                return Checkpoint.from_dict(data)
            except Exception as exc:
                logger.exception("Failed to decode checkpoint for loop %s", loop_id)
                raise RuntimeError(
                    f"Could not decode checkpoint for loop {loop_id}"
                ) from exc
        async with self._lock:
            return self._memory.get(loop_id)

    async def get_recovery_plan(
        self, loop_id: str, current_phase: int = 1
    ) -> RecoveryResult:
        """Determine which phases to skip and which to execute.

        Returns:
            A :class:`RecoveryResult` with the first phase to execute, the
            phases that can be skipped, the latest checkpoint, whether the
            loop can resume, and a human-readable explanation.
        """
        checkpoint = await self.load_checkpoint(loop_id)
        current_hash = await self._current_task_hash(loop_id)

        if checkpoint is None:
            return RecoveryResult(
                resume_from_phase=current_phase,
                skipped_phases=[],
                checkpoint=None,
                can_resume=True,
                reason="No prior checkpoint found; starting fresh.",
            )

        if current_hash is not None and checkpoint.task_hash != current_hash:
            return RecoveryResult(
                resume_from_phase=current_phase,
                skipped_phases=[],
                checkpoint=checkpoint,
                can_resume=False,
                reason="Task hash mismatch; the stored checkpoint belongs to a different task.",
            )

        phase_statuses = self._phase_statuses(checkpoint)
        skipped = sorted(
            phase
            for phase, status in phase_statuses.items()
            if status in (PhaseCheckpoint.COMPLETED, PhaseCheckpoint.SKIPPED)
        )

        # Determine the first phase that has not been completed or skipped.
        resume_from = current_phase
        for phase in range(current_phase, 8):
            if phase not in skipped:
                resume_from = phase
                break
        else:
            resume_from = 8

        if skipped:
            reason = (
                f"Resuming from phase {resume_from}; "
                f"completed/skipped phases: {skipped}."
            )
        else:
            reason = f"Resuming from phase {resume_from}; no completed phases recorded."

        return RecoveryResult(
            resume_from_phase=resume_from,
            skipped_phases=skipped,
            checkpoint=checkpoint,
            can_resume=True,
            reason=reason,
        )

    async def mark_phase(
        self,
        loop_id: str,
        phase: int,
        status: PhaseCheckpoint,
        artifact_summary: str = "",
    ) -> None:
        """Mark a phase as in-progress/completed/failed."""
        now = datetime.now(timezone.utc)
        existing = await self.load_checkpoint(loop_id)

        metadata: dict[str, Any] = {}
        phase_statuses: dict[str, str] = {}
        if existing is not None:
            metadata = dict(existing.metadata)
            phase_statuses = dict(metadata.get("phase_statuses") or {})

        phase_statuses[str(phase)] = status.value
        metadata["phase_statuses"] = phase_statuses

        if artifact_summary:
            phase_artifacts = dict(metadata.get("phase_artifacts") or {})
            phase_artifacts[str(phase)] = artifact_summary
            metadata["phase_artifacts"] = phase_artifacts

        task_hash = existing.task_hash if existing else (await self._current_task_hash(loop_id) or "")

        checkpoint = Checkpoint(
            loop_id=loop_id,
            phase=phase,
            task_hash=task_hash,
            completed_at=now,
            artifact_summary=artifact_summary,
            metadata=metadata,
        )
        await self.save_checkpoint(checkpoint)

    async def cleanup(self, loop_id: str) -> None:
        """Remove all checkpoints for a completed loop."""
        if self._state_store is not None and hasattr(self._state_store, "delete"):
            try:
                await self._state_store.delete(loop_id)
            except Exception as exc:
                logger.exception("Failed to cleanup checkpoints for loop %s", loop_id)
                raise RuntimeError(
                    f"Could not cleanup checkpoints for loop {loop_id}"
                ) from exc
        async with self._lock:
            self._memory.pop(loop_id, None)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _current_task_hash(self, loop_id: str) -> str | None:
        """Load the current loop's task hash from the persistent state store."""
        if self._state_store is None:
            return None
        if not hasattr(self._state_store, "get"):
            return None

        try:
            state = await self._state_store.get(loop_id)
        except Exception as exc:
            logger.exception("Failed to load loop state for idempotency check")
            return None

        if state is None:
            return None
        return self.compute_task_hash(state.task, state.goal)

    @staticmethod
    def _phase_statuses(checkpoint: Checkpoint) -> dict[int, PhaseCheckpoint]:
        """Return a mapping of phase numbers to phase status for a checkpoint."""
        statuses: dict[int, PhaseCheckpoint] = {}
        raw = checkpoint.metadata.get("phase_statuses")

        # If no per-phase status metadata exists, treat the checkpoint's phase
        # as the last completed phase for backwards compatibility.
        if not raw:
            for phase in range(1, checkpoint.phase + 1):
                statuses[phase] = PhaseCheckpoint.COMPLETED
            return statuses

        if isinstance(raw, dict):
            for phase_str, status_value in raw.items():
                try:
                    phase = int(phase_str)
                except ValueError:
                    continue
                try:
                    statuses[phase] = PhaseCheckpoint(status_value)
                except ValueError:
                    continue

        return statuses
