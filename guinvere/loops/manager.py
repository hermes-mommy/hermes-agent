"""Loop Manager — orchestrates autonomous SDLC loop instances.

Creates, drives, and monitors loops through the 7-phase SDLC cycle.
Each loop runs as an asyncio.Task, monitored by LoopGuardian.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import select, update

from guinvere.loops.cost import LoopCostTracker
from guinvere.loops.evidence import EvidencePipeline
from guinvere.loops.guardian import LoopGuardian
from guinvere.loops.phases import PHASE_REGISTRY, create_phase_handler, get_phase_handler
from guinvere.loops.state_machine import (
    PHASE_NAMES,
    LoopPhase,
    LoopStateMachine,
    LoopStatus,
)
from guinvere.memory.db import get_async_session
from guinvere.memory.models import LoopInstances

logger = structlog.get_logger()

# Phases to execute in order (excludes COMPLETE terminal).
_EXECUTION_PHASES = [
    LoopPhase.RESEARCH,
    LoopPhase.PLAN_AND_DELEGATE,
    LoopPhase.DELEGATE,
    LoopPhase.EXECUTE,
    LoopPhase.VALIDATE_AND_AUDIT,
    LoopPhase.UPDATE_DOCUMENTS,
    LoopPhase.SETUP_EVIDENCE,
]


class LoopManager:
    """Orchestrates autonomous SDLC loop instances."""

    def __init__(self, llm_router: Any | None = None) -> None:
        self.active_loops: dict[str, LoopStateMachine] = {}
        self.guardian = LoopGuardian()
        self.evidence_pipelines: dict[str, EvidencePipeline] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._llm_router = llm_router

        # RG-006: Per-loop cost tracking (fail-soft on Redis error)
        try:
            self.cost_tracker = LoopCostTracker()
        except Exception as cost_err:
            logger.warning("loop_cost_tracker_init_failed", error=str(cost_err))
            self.cost_tracker = None

        logger.info(
            "loop_manager.initialized",
            llm_router_attached=llm_router is not None,
        )

    async def start_loop(
        self, task: str, goal: str, priority: str = "normal"
    ) -> str:
        """Create a new loop, register with guardian, and run through 7 phases.

        Args:
            task: The task description for the loop.
            goal: The goal the loop should achieve.
            priority: Priority level (informational, used for scheduling).

        Returns:
            The generated loop_id (UUID).
        """
        loop_id = uuid.uuid4().hex[:12]
        state = LoopStateMachine(loop_id=loop_id, task=task, goal=goal)

        self.active_loops[loop_id] = state
        self.evidence_pipelines[loop_id] = EvidencePipeline(loop_id)

        # Start the loop as a background asyncio.Task.
        loop_task = asyncio.create_task(
            self._run_loop(loop_id, task, goal),
            name=f"loop-{loop_id}",
        )
        self._tasks[loop_id] = loop_task

        # Register with guardian, passing cancel_callback for immediate kill.
        self.guardian.register_loop(
            loop_id, state, cancel_callback=loop_task.cancel,
        )

        state.set_status(LoopStatus.RUNNING)

        logger.info(
            "loop_manager.loop_started",
            loop_id=loop_id,
            task=task,
            goal=goal,
            priority=priority,
        )

        # F-04: Persist loop start to PostgreSQL (fail-soft — loop runs regardless).
        await self._db_persist_loop_start(loop_id, state)

        return loop_id

    async def stop_loop(self, loop_id: str) -> dict[str, Any]:
        """Gracefully stop an active loop.

        Args:
            loop_id: The loop to stop.

        Returns:
            Final state dict of the loop, or error info if not found.
        """
        state = self.active_loops.get(loop_id)
        if state is None:
            logger.warning("loop_manager.stop_unknown_loop", loop_id=loop_id)
            return {"error": f"Loop {loop_id} not found."}

        if state.is_terminal():
            logger.info(
                "loop_manager.stop_already_terminal",
                loop_id=loop_id,
                status=state.status.value,
            )
            return state.to_dict()

        # Cancel the asyncio task.
        task = self._tasks.get(loop_id)
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        state.cancel()
        self.guardian.unregister_loop(loop_id)

        # F-04: Persist cancelled status to PostgreSQL (fail-soft).
        await self._db_update_loop_status(loop_id, state)

        logger.info("loop_manager.loop_stopped", loop_id=loop_id)
        return state.to_dict()

    async def get_loop_status(self, loop_id: str) -> dict[str, Any] | None:
        """Return current state dict for a loop.

        Args:
            loop_id: The loop to query.

        Returns:
            State dict or None if loop_id not found.
        """
        state = self.active_loops.get(loop_id)
        if state is None:
            return None
        return state.to_dict()

    async def list_loops(self) -> list[dict[str, Any]]:
        """Return status of all active loops."""
        return [state.to_dict() for state in self.active_loops.values()]

    async def cancel_all_loops(self, reason: str = "hard_stop") -> int:
        """Cancel all active loops immediately.

        Called by the HARD STOP protocol to halt all running autonomous loops.

        Args:
            reason: Human-readable reason logged per-loop cancellation.

        Returns:
            Number of loops that were cancelled.
        """
        loop_ids = list(self._tasks.keys())
        cancelled = 0
        for loop_id in loop_ids:
            task = self._tasks.get(loop_id)
            if task is not None and not task.done():
                task.cancel()
                cancelled += 1
            state = self.active_loops.get(loop_id)
            if state is not None and not state.is_terminal():
                state.cancel()
            self.guardian.unregister_loop(loop_id)

        logger.warning(
            "loop_manager.cancel_all_loops",
            reason=reason,
            cancelled=cancelled,
            total=len(loop_ids),
        )
        return cancelled

    async def _run_loop(self, loop_id: str, task: str, goal: str) -> None:
        """Internal: drive a loop through all 7 phases using PHASE_REGISTRY.

        Each phase:
        1. Gets the handler from PHASE_REGISTRY.
        2. Executes the handler to produce artifact content.
        3. Writes the artifact via EvidencePipeline.
        4. Advances the state machine.
        5. Sends a guardian heartbeat.

        On error: calls state.fail(reason), logs, and stops the loop.
        """
        state = self.active_loops[loop_id]
        pipeline = self.evidence_pipelines[loop_id]

        try:
            for phase in _EXECUTION_PHASES:
                # Check if loop was cancelled/stopped externally.
                if state.is_terminal():
                    logger.info(
                        "loop_manager.loop_terminal_before_phase",
                        loop_id=loop_id,
                        phase=PHASE_NAMES[phase],
                        status=state.status.value,
                    )
                    return

                logger.info(
                    "loop_manager.phase_start",
                    loop_id=loop_id,
                    phase=PHASE_NAMES[phase],
                    phase_value=phase.value,
                )

                handler = create_phase_handler(
                    phase,
                    llm_router=self._llm_router,
                    cost_tracker=self.cost_tracker,
                )
                artifact_content = await handler.execute(loop_id, task, goal)

                # Persist artifact through evidence pipeline.
                await pipeline.collect_phase_artifact(phase, artifact_content)

                # Record artifact in state machine.
                state.record_artifact(phase, PHASE_NAMES[phase])

                # Advance state machine to next phase.
                state.advance()

                # Guardian heartbeat + phase advance record.
                self.guardian.heartbeat(loop_id)
                self.guardian.record_phase_advance(loop_id)

                # RG-006: Record phase cost from handler metadata.
                # Phase handlers return str content. Token usage is captured
                # in handler._last_metadata when LLM router is attached.
                if self.cost_tracker is not None:
                    try:
                        # PhaseArtifact metadata contains token_usage dict when LLM was called.
                        phase_metadata = getattr(handler, "_last_metadata", None)
                        if phase_metadata is not None:
                            token_meta = phase_metadata.get("token_usage", {})
                            if token_meta:
                                self.cost_tracker.record_loop_cost(
                                    loop_id=loop_id,
                                    model=token_meta.get("model", "unknown"),
                                    input_tokens=token_meta.get("input_tokens", 0),
                                    output_tokens=token_meta.get("output_tokens", 0),
                                    cost_per_1k_input=token_meta.get("cost_per_1k_input", 0.0),
                                    cost_per_1k_output=token_meta.get("cost_per_1k_output", 0.0),
                                )
                    except Exception as cost_err:
                        logger.warning(
                            "loop_cost_record_failed",
                            loop_id=loop_id,
                            error=str(cost_err),
                        )

                logger.info(
                    "loop_manager.phase_complete",
                    loop_id=loop_id,
                    phase=PHASE_NAMES[phase],
                )

            # All 7 phases done — generate final evidence report.
            await pipeline.generate_final_report(state)

            logger.info(
                "loop_manager.loop_completed",
                loop_id=loop_id,
                task=task,
            )

            # F-04: Persist COMPLETE status to PostgreSQL (fail-soft).
            await self._db_update_loop_status(loop_id, state)

        except asyncio.CancelledError:
            logger.info("loop_manager.loop_cancelled", loop_id=loop_id)
            raise
        except Exception as exc:
            reason = f"{type(exc).__name__}: {exc}"
            logger.exception(
                "loop_manager.loop_failed",
                loop_id=loop_id,
                phase=PHASE_NAMES[state.current_phase],
                error=reason,
            )
            state.fail(reason)

            # Attempt to generate partial evidence report.
            try:
                await pipeline.generate_final_report(state)
            except Exception as report_exc:
                logger.exception(
                    "loop_manager.final_report_failed",
                    loop_id=loop_id,
                    error=str(report_exc),
                )

            # F-04: Persist FAILED status to PostgreSQL (fail-soft).
            await self._db_update_loop_status(loop_id, state)

        finally:
            self.guardian.unregister_loop(loop_id)

    # ── F-04: PostgreSQL persistence helpers (fail-soft) ─────────────────

    async def _db_persist_loop_start(
        self, loop_id: str, state: LoopStateMachine
    ) -> None:
        """Insert a new row into projects.loop_instances on loop creation.

        Wrapped in try/except — if DB is unavailable the loop keeps running
        and only a warning is logged (graceful degradation, F-04).
        """
        try:
            async with get_async_session() as session:
                record = LoopInstances(
                    loop_phase=PHASE_NAMES[state.current_phase],
                    status=state.status.value,
                    started_at=state.created_at,
                    goal=state.goal,
                    error_count=state.error_count,
                    retry_count=state.retry_count,
                    result_summary={
                        "loop_id": loop_id,
                        "task": state.task,
                    },
                )
                session.add(record)
        except Exception as db_err:
            logger.warning(
                "loop_manager.db_persist_start_failed",
                loop_id=loop_id,
                error=str(db_err),
            )

    async def resume_pending_loops(self) -> int:
        """Resume loops from database that were running or paused.

        Queries projects.loop_instances for rows with status 'running' or 'paused'.
        Re-creates state machine and restarts as asyncio.Task for each.

        Returns:
            Number of loops resumed.
        """
        resumed_count = 0
        try:
            async with get_async_session() as session:
                from sqlalchemy import select

                result = await session.execute(
                    select(LoopInstances).where(
                        LoopInstances.status.in_(['running', 'paused'])
                    )
                )
                pending_loops = result.scalars().all()

                for record in pending_loops:
                    loop_id = record.result_summary["loop_id"]
                    task = record.result_summary.get("task", "")
                    goal = record.goal or ""

                    # Re-create state machine
                    state = LoopStateMachine(
                        loop_id=loop_id,
                        task=task,
                        goal=goal,
                    )

                    self.active_loops[loop_id] = state
                    self.evidence_pipelines[loop_id] = EvidencePipeline(loop_id)

                    # Start as asyncio.Task
                    loop_task = asyncio.create_task(
                        self._run_loop(loop_id, task, goal),
                        name=f"loop-{loop_id}",
                    )
                    self._tasks[loop_id] = loop_task

                    # Register with guardian
                    self.guardian.register_loop(
                        loop_id, state, cancel_callback=loop_task.cancel,
                    )

                    # Update status to RUNNING
                    state.set_status(LoopStatus.RUNNING)

                    # Persist updated status
                    await self._db_update_loop_status(loop_id, state)

                    resumed_count += 1
                    logger.info(
                        "loop_manager.loop_resumed",
                        loop_id=loop_id,
                        task=task,
                    )

                logger.info(
                    "loop_manager.resume_pending_loops_complete",
                    resumed_count=resumed_count,
                    total=len(pending_loops),
                )
                return resumed_count
        except Exception as db_err:
            logger.warning(
                "loop_manager.resume_pending_loops_failed",
                error=str(db_err),
            )
            return 0

    async def _db_update_loop_status(
        self, loop_id: str, state: LoopStateMachine
    ) -> None:
        """Update the loop_instances row that matches loop_id in result_summary.

        Wrapped in try/except — if DB is unavailable the loop keeps running
        and only a warning is logged (graceful degradation, F-04).
        """
        try:
            now = datetime.now(timezone.utc)
            is_terminal = state.is_terminal()
            async with get_async_session() as session:
                await session.execute(
                    update(LoopInstances)
                    .where(
                        LoopInstances.result_summary["loop_id"].as_string()
                        == loop_id
                    )
                    .values(
                        status=state.status.value,
                        loop_phase=PHASE_NAMES[state.current_phase],
                        error_count=state.error_count,
                        retry_count=state.retry_count,
                        updated_at=now,
                        completed_at=now if is_terminal else None,
                    )
                )
        except Exception as db_err:
            logger.warning(
                "loop_manager.db_update_status_failed",
                loop_id=loop_id,
                error=str(db_err),
            )


async def main() -> None:
    """Entry point for running the loop manager as a standalone service."""
    manager = LoopManager()

    # Start guardian monitoring in the background.
    guardian_task = asyncio.create_task(
        manager.guardian.monitor(),
        name="guardian-monitor",
    )

    logger.info("loop_manager.service_started")

    try:
        # Keep the service running until interrupted.
        await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("loop_manager.service_stopping")
    finally:
        # Graceful shutdown.
        await manager.guardian.stop()
        guardian_task.cancel()
        try:
            await guardian_task
        except asyncio.CancelledError:
            pass

        # Cancel all active loop tasks.
        for loop_id, task in manager._tasks.items():
            if not task.done():
                task.cancel()

        logger.info("loop_manager.service_stopped")


if __name__ == "__main__":
    asyncio.run(main())
