"""Loop Manager — orchestrates autonomous SDLC loop instances.

Creates, drives, and monitors loops through the 7-phase SDLC cycle.
Each loop runs as an asyncio.Task, monitored by LoopGuardian.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import structlog

from src.loops.evidence import EvidencePipeline
from src.loops.guardian import LoopGuardian
from src.loops.phases import PHASE_REGISTRY, get_phase_handler
from src.loops.state_machine import (
    PHASE_NAMES,
    LoopPhase,
    LoopStateMachine,
    LoopStatus,
)

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

    def __init__(self) -> None:
        self.active_loops: dict[str, LoopStateMachine] = {}
        self.guardian = LoopGuardian()
        self.evidence_pipelines: dict[str, EvidencePipeline] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}

        logger.info("loop_manager.initialized")

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

                handler = get_phase_handler(phase)
                artifact_content = await handler(loop_id, task, goal)

                # Persist artifact through evidence pipeline.
                await pipeline.collect_phase_artifact(phase, artifact_content)

                # Record artifact in state machine.
                state.record_artifact(phase, PHASE_NAMES[phase])

                # Advance state machine to next phase.
                state.advance()

                # Guardian heartbeat + phase advance record.
                self.guardian.heartbeat(loop_id)
                self.guardian.record_phase_advance(loop_id)

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
        finally:
            self.guardian.unregister_loop(loop_id)


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
