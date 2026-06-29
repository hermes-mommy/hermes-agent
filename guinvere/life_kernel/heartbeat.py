"""Heartbeat service for Guinevere's Life Kernel.

Six-interval autonomous clock driving 24/7 cycles:
  1s   — liveness check
  10s  — world-model health
  30s  — sensor poll / awareness refresh
  60s  — decision trigger + dashboard update
  5m   — deep scan (anomaly detection)
  1h   — reflection + memory consolidation

P20 invariants preserved:
  - asyncio.Queue graph-write serialization (invariant #4)
  - edit-not-spam dashboard pattern (invariant #6)
  - fail-soft Discord — never blocks on Discord errors (invariant #3)
  - autonomous 24/7 runtime (invariant #7)

P20 HARD STOP removed (M2 paradigm shift) — no Redis hard-stop flag.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# --- Heartbeat interval enumeration -----------------------------------------

class HeartbeatInterval(StrEnum):
    """Six heartbeat cadences from P5+P20 architecture benchmark."""

    L1S = "1s"
    L10S = "10s"
    L30S = "30s"
    L60S = "60s"
    L5M = "5m"
    L1H = "1h"


_INTERVAL_SECONDS: dict[HeartbeatInterval, int] = {
    HeartbeatInterval.L1S: 1,
    HeartbeatInterval.L10S: 10,
    HeartbeatInterval.L30S: 30,
    HeartbeatInterval.L60S: 60,
    HeartbeatInterval.L5M: 300,
    HeartbeatInterval.L1H: 3600,
}

# Throttle for lifecycle log lines — at most one per 5 minutes.
_LIFECYCLE_LOG_THROTTLE_S = 300
_DISCORD_MSG_MAX = 1900


# --- Heartbeat service ------------------------------------------------------

class HeartbeatService:
    """Six-interval autonomous clock for the Life Kernel.

    Each interval runs as a separate ``asyncio.Task``.  Graph writes are
    serialized through an ``asyncio.Queue`` so that concurrent intervals
    never corrupt graph state.

    Args:
        world_model: Object with an async ``health()`` method.
        sensor_registry: Object with an async ``sense_all()`` method.
        dashboard_writer: Optional object with an async
            ``update_dashboard(state: dict)`` method.  When ``None``
            the dashboard is skipped (headless mode / tests).
        log_channel: Optional async callable ``write(text)`` for
            append-only lifecycle events.
        on_decision: Optional async callable invoked on the 60s cycle
            to trigger an observe-decide cycle.
    """

    def __init__(
        self,
        world_model: Any | None = None,
        sensor_registry: Any | None = None,
        dashboard_writer: Any | None = None,
        log_channel: Any | None = None,
        on_decision: Any | None = None,
    ) -> None:
        self._world_model = world_model
        self._sensor_registry = sensor_registry
        self._dashboard_writer = dashboard_writer
        self._log_channel = log_channel
        self._on_decision = on_decision

        # Public intervals map (exposed for tests/verification).
        self.intervals: dict[str, int] = {
            iv.value: secs for iv, secs in _INTERVAL_SECONDS.items()
        }

        # Internal state.
        self._tasks: set[asyncio.Task] = set()
        self._last_heartbeats: dict[HeartbeatInterval, float] = {}
        self._heartbeat_counts: dict[HeartbeatInterval, int] = {
            iv: 0 for iv in HeartbeatInterval
        }

        # asyncio.Queue for graph write serialization (P20 invariant #4).
        self._graph_write_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

        # Dashboard state (edit-not-spam, P20 invariant #6).
        self._last_dashboard_state: dict[str, Any] = {}
        self._last_dashboard_checksum: str | None = None

        # Lifecycle log throttle state.
        self._last_log_line: str | None = None
        self._last_lifecycle_log_ts: float = 0.0

    # --- lifecycle -----------------------------------------------------------

    async def start(self) -> None:
        """Start all six heartbeat loops as asyncio tasks."""
        logger.debug("heartbeat_service_starting")

        # Start the graph-write consumer.
        task = asyncio.create_task(self._graph_write_consumer())
        self._tasks.add(task)

        for interval in HeartbeatInterval:
            task = asyncio.create_task(self._heartbeat_loop(interval))
            self._tasks.add(task)
            logger.debug(
                "heartbeat_loop_started",
                interval=interval.value,
                seconds=_INTERVAL_SECONDS[interval],
            )

        logger.info("heartbeat_service_started", interval_count=len(self._tasks))

    async def stop(self) -> None:
        """Cancel all heartbeat loops and drain the graph-write queue."""
        logger.debug("heartbeat_service_stopping", task_count=len(self._tasks))

        current = asyncio.current_task()
        for task in self._tasks:
            task.cancel()

        tasks_to_await = [t for t in self._tasks if t is not current]
        if tasks_to_await:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks_to_await, return_exceptions=True),
                    timeout=5.0,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "heartbeat_tasks_timeout", task_count=len(tasks_to_await)
                )

        self._tasks.clear()
        logger.info("heartbeat_service_stopped")

    # --- graph write serialization (P20 invariant #4) -------------------------

    async def enqueue_graph_write(self, payload: dict[str, Any]) -> None:
        """Enqueue a graph write for serialized consumption."""
        await self._graph_write_queue.put(payload)

    async def _graph_write_consumer(self) -> None:
        """Consume graph-write requests one at a time (serialized)."""
        while True:
            try:
                payload = await self._graph_write_queue.get()
                # In production this would call graph.ainvoke(payload).
                # Here we just log the serialization point.
                logger.debug("graph_write_consumed", payload_keys=list(payload.keys()))
                self._graph_write_queue.task_done()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error(
                    "graph_write_consumer_error",
                    error_type=type(exc).__name__,
                )

    # --- interval dispatch ---------------------------------------------------

    async def _heartbeat_loop(self, interval: HeartbeatInterval) -> None:
        """Dispatch loop for a single heartbeat interval."""
        duration = _INTERVAL_SECONDS[interval]

        while True:
            try:
                start = time.perf_counter()

                if interval == HeartbeatInterval.L1S:
                    await self._heartbeat_1s()
                elif interval == HeartbeatInterval.L10S:
                    await self._heartbeat_10s()
                elif interval == HeartbeatInterval.L30S:
                    await self._heartbeat_30s()
                elif interval == HeartbeatInterval.L60S:
                    await self._heartbeat_60s()
                elif interval == HeartbeatInterval.L5M:
                    await self._heartbeat_5m()
                elif interval == HeartbeatInterval.L1H:
                    await self._heartbeat_1h()

                elapsed_ms = (time.perf_counter() - start) * 1000
                logger.debug(
                    "heartbeat_completed",
                    interval=interval.value,
                    latency_ms=elapsed_ms,
                )
                self._last_heartbeats[interval] = time.time()
                self._heartbeat_counts[interval] += 1

            except asyncio.CancelledError:
                logger.debug("heartbeat_loop_cancelled", interval=interval.value)
                raise
            except Exception as exc:
                logger.error(
                    "heartbeat_loop_error",
                    interval=interval.value,
                    error_type=type(exc).__name__,
                )

            try:
                await asyncio.sleep(duration)
            except asyncio.CancelledError:
                raise

    # --- 1s: liveness check --------------------------------------------------

    async def _heartbeat_1s(self) -> None:
        """Liveness check — confirms the kernel is alive.

        P20 HARD STOP detection removed (M2 paradigm shift).
        This interval is now a simple liveness ping; downstream
        subsystems can hook into it if needed.
        """
        logger.debug("heartbeat_1s_liveness", timestamp=datetime.now(timezone.utc).isoformat())

    # --- 10s: world model health ---------------------------------------------

    async def _heartbeat_10s(self) -> None:
        """Check world-model health (fail-soft)."""
        try:
            if self._world_model is not None:
                healthy = await self._world_model.health()
                logger.debug("heartbeat_10s_world_model", healthy=healthy)
            else:
                logger.debug("heartbeat_10s_world_model_none")
        except Exception as exc:
            logger.error("heartbeat_10s_error", error_type=type(exc).__name__)

    # --- 30s: sensor poll / awareness refresh --------------------------------

    async def _heartbeat_30s(self) -> None:
        """Poll sensors via SensorRegistry and enqueue observations."""
        try:
            if self._sensor_registry is None:
                logger.debug("heartbeat_30s_no_sensors")
                return

            observations = await self._sensor_registry.sense_all()
            if observations:
                await self.enqueue_graph_write(
                    {"type": "observations", "data": observations}
                )
                logger.info(
                    "heartbeat_30s_observations",
                    count=len(observations),
                )
            else:
                logger.debug("heartbeat_30s_no_observations")
        except Exception as exc:
            logger.error("heartbeat_30s_error", error_type=type(exc).__name__)

    # --- 60s: decision trigger + dashboard -----------------------------------

    async def _heartbeat_60s(self) -> None:
        """Trigger observe-decide cycle + update dashboard (edit-not-spam)."""
        try:
            # Trigger decision cycle.
            if self._on_decision is not None:
                try:
                    result = await self._on_decision()
                    logger.info(
                        "heartbeat_60s_decision",
                        result_keys=list(result.keys()) if isinstance(result, dict) else None,
                    )
                except Exception as exc:
                    logger.error(
                        "heartbeat_60s_decision_error",
                        error_type=type(exc).__name__,
                    )

            # Dashboard update (edit-not-spam, P20 invariant #6).
            await self._update_dashboard()

            # Lifecycle log (throttled).
            await self._log_lifecycle()

        except Exception as exc:
            logger.error("heartbeat_60s_error", error_type=type(exc).__name__)

    # --- 5m: deep scan -------------------------------------------------------

    async def _heartbeat_5m(self) -> None:
        """Deep scan — anomaly detection across subsystems."""
        try:
            logger.debug("heartbeat_5m_deep_scan")
            if self._world_model is not None:
                healthy = await self._world_model.health()
                if not healthy:
                    logger.warning("heartbeat_5m_world_model_unhealthy")
        except Exception as exc:
            logger.error("heartbeat_5m_error", error_type=type(exc).__name__)

    # --- 1h: reflection + consolidation --------------------------------------

    async def _heartbeat_1h(self) -> None:
        """Reflection — memory consolidation + self-improvement evaluation."""
        try:
            logger.debug("heartbeat_1h_reflection")
            # Consolidation hook: enqueue a graph write for reflection.
            await self.enqueue_graph_write({"type": "reflection", "trigger": "1h"})
        except Exception as exc:
            logger.error("heartbeat_1h_error", error_type=type(exc).__name__)

    # --- dashboard (edit-not-spam, P20 invariant #6) -------------------------

    async def _update_dashboard(self) -> None:
        """Update the dashboard message in place (edit-not-spam).

        Computes a checksum of the state; skips the Discord round-trip
        entirely when the state is unchanged.  Fail-soft: never blocks
        on Discord errors (P20 invariant #3).
        """
        if self._dashboard_writer is None:
            return

        state = self._build_state_snapshot()
        checksum = _state_checksum(state)
        if checksum == self._last_dashboard_checksum:
            return

        try:
            await self._dashboard_writer.update_dashboard(state)
            self._last_dashboard_checksum = checksum
            self._last_dashboard_state = state
            logger.debug("dashboard_updated")
        except Exception as exc:
            logger.warning(
                "dashboard_update_failed",
                error_type=type(exc).__name__,
            )

    def _build_state_snapshot(self) -> dict[str, Any]:
        """Build a sanitized state snapshot for the dashboard.

        The snapshot intentionally excludes the timestamp so that the
        checksum only changes when *meaningful* state changes (counts,
        queue size) change.  This powers the edit-not-spam dedup.
        """
        return {
            "heartbeat_counts": {
                iv.value: self._heartbeat_counts[iv] for iv in HeartbeatInterval
            },
            "graph_queue_size": self._graph_write_queue.qsize(),
        }

    # --- lifecycle log (throttled) -------------------------------------------

    async def _log_lifecycle(self) -> None:
        """Write a throttled lifecycle log line (at most once per 5 min)."""
        if self._log_channel is None:
            return

        now = time.time()
        if (now - self._last_lifecycle_log_ts) < _LIFECYCLE_LOG_THROTTLE_S:
            return

        line = (
            f"[heartbeat] t={datetime.now(timezone.utc).isoformat()} "
            f"counts={self._heartbeat_counts[HeartbeatInterval.L60S]}"
        )
        if line == self._last_log_line:
            return

        if len(line) > _DISCORD_MSG_MAX:
            line = line[: _DISCORD_MSG_MAX - 3] + "..."

        self._last_log_line = line
        self._last_lifecycle_log_ts = now
        try:
            await self._log_channel.write(line)
        except Exception as exc:
            logger.warning("lifecycle_log_write_failed", error_type=type(exc).__name__)

    # --- accessors -----------------------------------------------------------

    def get_last_heartbeat_time(self, interval: HeartbeatInterval) -> float | None:
        """Return the last execution timestamp for *interval*, or ``None``."""
        return self._last_heartbeats.get(interval)


# --- helpers -----------------------------------------------------------------

def _state_checksum(state: dict[str, Any]) -> str:
    """Stable checksum of a state dict (edit-not-spam dedup)."""
    serialized = json.dumps(state, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()[:16]
