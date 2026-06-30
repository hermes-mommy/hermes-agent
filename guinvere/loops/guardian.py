"""Loop Guardian — watchdog for autonomous SDLC loops.

Monitors active loops for heartbeat liveness, progress stalls,
and resource issues per ADR-011 / AgentLoopSpec v2.0.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, Optional

import structlog

if TYPE_CHECKING:
    from guinvere.core.services.hard_stop_handler import HardStopHandler

logger = structlog.get_logger()


class LoopGuardian:
    """Watchdog that monitors all registered autonomous loops.

    Checks heartbeat liveness every ``HEARTBEAT_INTERVAL`` seconds,
    kills loops that have not advanced a phase within ``PROGRESS_TIMEOUT``
    seconds, and performs periodic resource checks every ``RESOURCE_CHECK``
    seconds.
    """

    HEARTBEAT_INTERVAL: int = 30  # seconds between heartbeat checks
    PROGRESS_TIMEOUT: int = 300  # 5 minutes without phase advance
    RESOURCE_CHECK: int = 60  # seconds between resource checks

    def __init__(self) -> None:
        self.active_loops: dict[str, dict[str, Any]] = {}
        self._running: bool = False
        self._monitor_task: asyncio.Task[None] | None = None
        self._hard_stop_handler: Optional[HardStopHandler] = None
        logger.info("loop_guardian_initialized",
                     heartbeat_interval=self.HEARTBEAT_INTERVAL,
                     progress_timeout=self.PROGRESS_TIMEOUT,
                     resource_check=self.RESOURCE_CHECK)

    def set_hard_stop_handler(self, handler: HardStopHandler) -> None:
        """Wire a HardStopHandler so the guardian cancels all loops on HARD STOP.

        Args:
            handler: The application-level HardStopHandler instance.
        """
        self._hard_stop_handler = handler
        logger.info("loop_guardian.hard_stop_handler_wired")

    @property
    def is_hard_stop_active(self) -> bool:
        """Check if HARD STOP is active.

        Returns:
            True if HardStopHandler is wired and in SAFE state.
        """
        if self._hard_stop_handler is None:
            return False
        return self._hard_stop_handler.is_safe

    @property
    def is_safe(self) -> bool:
        """Deprecated alias for is_hard_stop_active.

        .. deprecated:: 2.1
            Use :meth:`is_hard_stop_active` instead.

        Returns:
            True if HardStopHandler is wired and in SAFE state.
        """
        logger.warning(
            "loop_guardian.is_safe_deprecated",
            alternative="is_hard_stop_active",
        )
        return self.is_hard_stop_active

    def register_loop(
        self,
        loop_id: str,
        state_machine: object,
        cancel_callback: Optional[Callable[[], None]] = None,
    ) -> None:
        """Register a loop for monitoring.

        Args:
            loop_id: Unique identifier for the loop.
            state_machine: The LoopStateMachine instance to monitor.
            cancel_callback: Optional callback to cancel the loop's asyncio.Task.
        """
        now = datetime.now(timezone.utc)
        self.active_loops[loop_id] = {
            "state_machine": state_machine,
            "cancel_callback": cancel_callback,
            "registered_at": now,
            "last_heartbeat": now,
            "last_phase_advance": now,
            "last_resource_check": now,
        }
        logger.info("loop_registered", loop_id=loop_id)

    def unregister_loop(self, loop_id: str) -> None:
        """Remove a loop from monitoring.

        Args:
            loop_id: The loop to unregister.
        """
        removed = self.active_loops.pop(loop_id, None)
        if removed is not None:
            logger.info("loop_unregistered", loop_id=loop_id)
        else:
            logger.warning("loop_unregister_not_found", loop_id=loop_id)

    def heartbeat(self, loop_id: str) -> None:
        """Update the last heartbeat timestamp for a loop.

        Args:
            loop_id: The loop sending the heartbeat.
        """
        loop_data = self.active_loops.get(loop_id)
        if loop_data is None:
            logger.warning("heartbeat_unknown_loop", loop_id=loop_id)
            return
        loop_data["last_heartbeat"] = datetime.now(timezone.utc)
        logger.debug("heartbeat_received", loop_id=loop_id)

    def record_phase_advance(self, loop_id: str) -> None:
        """Record that a loop has advanced to a new phase.

        Args:
            loop_id: The loop that advanced.
        """
        loop_data = self.active_loops.get(loop_id)
        if loop_data is None:
            logger.warning("phase_advance_unknown_loop", loop_id=loop_id)
            return
        loop_data["last_phase_advance"] = datetime.now(timezone.utc)
        logger.info("phase_advance_recorded", loop_id=loop_id)

    async def kill_loop(self, loop_id: str, reason: str) -> None:
        """Kill a stalled loop: update state machine, cancel task, unregister."""
        data = self.active_loops.get(loop_id)
        if data is None:
            logger.warning("guardian.kill_loop_not_found", loop_id=loop_id)
            return

        # Update state machine to FAILED
        state_machine = data.get("state_machine")
        if state_machine is not None:
            try:
                state_machine.fail(reason)
            except Exception as exc:
                logger.exception("guardian.state_fail_failed", loop_id=loop_id)

        # Cancel the asyncio task via callback
        cancel_cb = data.get("cancel_callback")
        if cancel_cb is not None:
            try:
                cancel_cb()
            except Exception as exc:
                logger.exception("guardian.cancel_callback_failed", loop_id=loop_id)

        logger.warning("loop_killed", loop_id=loop_id, reason=reason)
        self.unregister_loop(loop_id)

    async def monitor(self) -> None:
        """Main monitoring loop — checks all active loops periodically.

        Runs until ``stop()`` is called.  Checks heartbeat liveness,
        progress timeout, and resource health on each tick.

        If a HardStopHandler is wired (via ``set_hard_stop_handler``), the
        guardian also checks ``is_hard_stop_active`` on every tick and cancels all active
        loops immediately when HARD STOP is active.
        """
        self._running = True
        logger.info("guardian_monitor_started")
        while self._running:
            try:
                # F-05: Check HardStopHandler — cancel all loops when HARD STOP active
                if (
                    self._hard_stop_handler is not None
                    and self._hard_stop_handler.is_safe
                    and self.active_loops
                ):
                    loop_ids = list(self.active_loops.keys())
                    logger.warning(
                        "guardian.hard_stop_active_cancelling_loops",
                        loop_count=len(loop_ids),
                    )
                    for loop_id in loop_ids:
                        try:
                            await self.kill_loop(loop_id, "hard_stop_protocol")
                        except asyncio.CancelledError:
                            raise
                        except Exception as exc:
                            logger.exception(
                                "guardian.hard_stop_kill_failed", loop_id=loop_id, exc_info=True
                            )

                now = datetime.now(timezone.utc)
                stale_loops: list[tuple[str, str]] = []

                for loop_id, data in list(self.active_loops.items()):
                    # Heartbeat check
                    heartbeat_age = (now - data["last_heartbeat"]).total_seconds()
                    if heartbeat_age > self.HEARTBEAT_INTERVAL * 3:
                        stale_loops.append(
                            (loop_id, f"heartbeat_lost ({heartbeat_age:.0f}s)")
                        )
                        continue

                    # Progress timeout check
                    progress_age = (now - data["last_phase_advance"]).total_seconds()
                    if progress_age > self.PROGRESS_TIMEOUT:
                        stale_loops.append(
                            (loop_id, f"progress_stalled ({progress_age:.0f}s)")
                        )
                        continue

                    # Resource check (periodic)
                    resource_age = (now - data["last_resource_check"]).total_seconds()
                    if resource_age >= self.RESOURCE_CHECK:
                        data["last_resource_check"] = now
                        logger.debug("resource_check", loop_id=loop_id)

                for loop_id, reason in stale_loops:
                    try:
                        await self.kill_loop(loop_id, reason)
                    except asyncio.CancelledError:
                        raise
                    except Exception as exc:
                        logger.exception("guardian.kill_failed", loop_id=loop_id, exc_info=True)

            except Exception as exc:
                logger.exception(
                    "guardian.monitor_error",
                    error="unexpected error in monitoring loop",
                    exc_info=True
                )

            await asyncio.sleep(self.HEARTBEAT_INTERVAL)

        logger.info("guardian_monitor_stopped")

    async def stop(self) -> None:
        """Stop the monitoring loop gracefully."""
        logger.info("guardian_stopping")
        self._running = False
        if self._monitor_task is not None and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("guardian_stopped")
