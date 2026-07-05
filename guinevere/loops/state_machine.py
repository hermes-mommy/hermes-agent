"""7-phase SDLC loop state machine per ADR-011.

Canonical phases (exactly 7 + COMPLETE terminal):
1. Research
2. Plan & Delegate
3. Delegate
4. Execute
5. Validate & Audit
6. Update Documents
7. Setup Evidence
8. COMPLETE (terminal)
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum, IntEnum


import structlog

logger = structlog.get_logger()


class LoopPhase(IntEnum):
    """Ordered phases of the autonomous SDLC loop."""

    RESEARCH = 1
    PLAN_AND_DELEGATE = 2
    DELEGATE = 3
    EXECUTE = 4
    VALIDATE_AND_AUDIT = 5
    UPDATE_DOCUMENTS = 6
    SETUP_EVIDENCE = 7
    COMPLETE = 8


PHASE_NAMES: dict[LoopPhase, str] = {
    LoopPhase.RESEARCH: "Research",
    LoopPhase.PLAN_AND_DELEGATE: "Plan & Delegate",
    LoopPhase.DELEGATE: "Delegate",
    LoopPhase.EXECUTE: "Execute",
    LoopPhase.VALIDATE_AND_AUDIT: "Validate & Audit",
    LoopPhase.UPDATE_DOCUMENTS: "Update Documents",
    LoopPhase.SETUP_EVIDENCE: "Setup Evidence",
    LoopPhase.COMPLETE: "Complete",
}


class LoopStatus(str, Enum):
    """Lifecycle status of a loop instance."""

    INIT = "init"
    RUNNING = "running"
    PAUSED = "paused"
    BLOCKED = "blocked"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


_TERMINAL_STATUSES = frozenset({LoopStatus.COMPLETE, LoopStatus.FAILED, LoopStatus.CANCELLED})


class LoopStateMachine:
    """Drives a single loop instance through the 7-phase SDLC cycle.

    Each transition is logged via structlog with the loop_id for traceability.
    """

    def __init__(self, loop_id: str, task: str, goal: str = "") -> None:
        self.loop_id = loop_id
        self.task = task
        self.goal = goal
        self.current_phase: LoopPhase = LoopPhase.RESEARCH
        self.status: LoopStatus = LoopStatus.INIT
        self.artifacts: dict[LoopPhase, str] = {}
        self.created_at: datetime = datetime.now(timezone.utc)
        self.error_count: int = 0
        self.retry_count: int = 0

        logger.info(
            "loop_state_machine.created",
            loop_id=self.loop_id,
            task=self.task,
            goal=self.goal,
            initial_phase=PHASE_NAMES[self.current_phase],
        )

    # ── Phase transitions ────────────────────────────────────────────

    def advance(self) -> LoopPhase:
        """Advance to the next phase. Returns the new current phase.

        Raises ValueError if the loop is already COMPLETE.
        """
        if self.current_phase == LoopPhase.COMPLETE:
            logger.warning(
                "loop_state_machine.advance_blocked",
                loop_id=self.loop_id,
                reason="already_complete",
            )
            raise ValueError(
                f"Loop {self.loop_id} is already COMPLETE; cannot advance further."
            )

        old_phase = self.current_phase
        self.current_phase = LoopPhase(self.current_phase.value + 1)

        logger.info(
            "loop_state_machine.phase_advanced",
            loop_id=self.loop_id,
            from_phase=PHASE_NAMES[old_phase],
            to_phase=PHASE_NAMES[self.current_phase],
            phase_value=self.current_phase.value,
        )

        if self.current_phase == LoopPhase.COMPLETE:
            self.set_status(LoopStatus.COMPLETE)

        return self.current_phase

    # ── Status transitions ───────────────────────────────────────────

    def set_status(self, status: LoopStatus) -> None:
        """Transition the loop status with logging."""
        old_status = self.status
        self.status = status

        logger.info(
            "loop_state_machine.status_changed",
            loop_id=self.loop_id,
            from_status=old_status.value,
            to_status=status.value,
        )

    def pause(self) -> None:
        """Pause the loop."""
        if self.is_terminal():
            logger.warning(
                "loop_state_machine.pause_blocked",
                loop_id=self.loop_id,
                reason=f"status_is_{self.status.value}",
            )
            raise ValueError(
                f"Cannot pause loop {self.loop_id}: status is {self.status.value}."
            )
        self.set_status(LoopStatus.PAUSED)

    def resume(self) -> None:
        """Resume a paused or blocked loop."""
        if self.status not in {LoopStatus.PAUSED, LoopStatus.BLOCKED}:
            logger.warning(
                "loop_state_machine.resume_blocked",
                loop_id=self.loop_id,
                reason=f"status_is_{self.status.value}",
            )
            msg = f"Cannot resume loop {self.loop_id}: status is {self.status.value}. Only PAUSED or BLOCKED loops can be resumed."
            raise ValueError(msg)
        self.set_status(LoopStatus.RUNNING)

    def fail(self, reason: str) -> None:
        """Mark the loop as failed with a reason."""
        self.error_count += 1
        logger.error(
            "loop_state_machine.failed",
            loop_id=self.loop_id,
            phase=PHASE_NAMES[self.current_phase],
            reason=reason,
            error_count=self.error_count,
        )
        self.set_status(LoopStatus.FAILED)

    def cancel(self) -> None:
        """Cancel the loop."""
        logger.warning(
            "loop_state_machine.cancelled",
            loop_id=self.loop_id,
            phase=PHASE_NAMES[self.current_phase],
        )
        self.set_status(LoopStatus.CANCELLED)

    # ── Queries ──────────────────────────────────────────────────────

    def is_complete(self) -> bool:
        """Check whether the loop has reached the COMPLETE phase."""
        return self.current_phase == LoopPhase.COMPLETE

    def is_terminal(self) -> bool:
        """Check whether the loop is in a terminal status."""
        return self.status in _TERMINAL_STATUSES

    # ── Artifact management ──────────────────────────────────────────

    def record_artifact(self, phase: LoopPhase, artifact_path: str) -> None:
        """Record an artifact path produced during a phase."""
        self.artifacts[phase] = artifact_path
        logger.info(
            "loop_state_machine.artifact_recorded",
            loop_id=self.loop_id,
            phase=PHASE_NAMES[phase],
            artifact_path=artifact_path,
        )

    def get_artifact(self, phase: LoopPhase) -> str | None:
        """Retrieve the artifact path for a phase, or None if absent."""
        return self.artifacts.get(phase)

    # ── Serialisation ────────────────────────────────────────────────

    def to_dict(self) -> dict[str, str | int | dict[str, str]]:
        """Serialize state for API response."""
        return {
            "loop_id": self.loop_id,
            "task": self.task,
            "goal": self.goal,
            "current_phase": self.current_phase.value,
            "current_phase_name": PHASE_NAMES[self.current_phase],
            "status": self.status.value,
            "artifacts": {
                PHASE_NAMES[phase]: path for phase, path in self.artifacts.items()
            },
            "created_at": self.created_at.isoformat(),
            "error_count": self.error_count,
            "retry_count": self.retry_count,
        }
