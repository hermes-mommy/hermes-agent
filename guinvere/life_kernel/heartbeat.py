"""Heartbeat service for Guinevere's Living Autonomy Kernel.

This module provides the autonomous clock that drives the kernel's 24/7 cycles.
The heartbeat manages 6 configurable intervals for liveness, health checks,
awareness refresh, decision heartbeat, deep scans, and reflection.

Heartbeat intervals from P5+P20 Architecture Benchmark:
- 1s: Liveness check + HARD STOP detection
- 10s: Graph health check (stuck detection, node timeout)
- 30s: Awareness refresh (read sensors, update world model)
- 60s: 60s heartbeat decision (trigger graph.ainvoke for OBSERVE→DECIDE cycle) + dashboard update
- 5m: Deep scan (check domain mind states, anomaly detection)
- 1h: Reflection + memory consolidation + self-improvement evaluation
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from enum import StrEnum
from typing import Any, Optional

import structlog
import redis.asyncio as aioredis
from redis.exceptions import RedisError

from guinvere.life_kernel.state import LifeMindPhase

logger = structlog.get_logger(__name__)

_LIFECYCLE_LOG_THROTTLE_SECONDS = 300  # at most one lifecycle log line per 5 min


class HeartbeatInterval(StrEnum):
    """Heartbeat interval types with their durations.

    These intervals form the autonomous clock that drives the living kernel's cycles.
    Each interval has a specific purpose and executes at its designated timing.
    """

    L1S = "1s"
    L10S = "10s"
    L30S = "30s"
    L60S = "60s"
    L5M = "5m"
    L1H = "1h"


class HeartbeatService:
    """Heartbeat service for autonomous cycle management.

    This service manages 6 configurable heartbeat loops that drive the living kernel's
    24/7 autonomous behavior. Each interval runs in its own asyncio task and performs
    specific health checks, awareness updates, decision triggers, and self-reflection.

    The heartbeat is the AUTONOMOUS CLOCK — when Faiz is silent, heartbeat continues.
    Graph idle → heartbeat triggers self-directed task.

    Attributes:
        graph: Compiled LangGraph StateGraph for autonomous execution.
        redis_client: Redis client for HARD STOP flag and hot state.
        checkpointer: LangGraph checkpointer for state persistence.
        _tasks: Set of running asyncio tasks.
        _last_heartbeats: Dict tracking last execution time for each interval type.
    """

    def __init__(
        self,
        graph: Any,
        redis_client: aioredis.Redis,
        checkpointer: Any | None = None,
        discord_publisher: Any | None = None,
        hermes_brain: Any | None = None,
        log_channel: Any | None = None,
        dashboard_channel_id: Any | None = None,
        project_id: Optional[str] = None,
    ):
        """Initialize heartbeat service.

        Args:
            graph: Compiled LangGraph StateGraph for autonomous execution.
            redis_client: Redis client for HARD STOP flag (key: life_kernel:hard_stop).
            checkpointer: LangGraph checkpointer for state persistence (optional).
            discord_publisher: Optional ``DashboardWriter`` for the Discord
                dashboard (edit-not-spam). When ``None`` the dashboard is
                skipped — the kernel runs headless (tests, no-token envs).
            hermes_brain: Optional ``HermesBrain`` for LLM-driven autonomy.
                Reserved for the graph builder; the heartbeat itself does not
                call the brain directly.
            log_channel: Optional ``LogChannel`` for append-only lifecycle
                events. When ``None`` lifecycle logging is skipped.
            dashboard_channel_id: Optional channel id snowflake, used only to
                record which channel the dashboard targets (diagnostics).
            project_id: Optional project namespace for multi-project context
                (P19).  When set AND ``feature:projects:enabled`` is ON,
                thread_id is scoped to ``"heartbeat-{project_id}"``.  When
                None (default), legacy ``"heartbeat"`` thread_id is used.
        """
        self.graph = graph
        self.redis_client = redis_client
        self.checkpointer = checkpointer
        self._discord_publisher = discord_publisher
        self._hermes_brain = hermes_brain
        self._log_channel = log_channel
        self._dashboard_channel_id = dashboard_channel_id
        self.project_id = project_id
        # Guards so we log a lifecycle milestone at most once per boot and
        # never spam the log channel with repeated identical events.
        self._hard_stop_announced = False
        self._recovery_announced = False
        self._last_log_line: str | None = None
        self._last_lifecycle_log_ts: float = 0.0

        self._tasks: set[asyncio.Task] = set()
        self._last_heartbeats: dict[HeartbeatInterval, float] = {}
        self._heartbeat_counts: dict[HeartbeatInterval, int] = {
            interval: 0 for interval in HeartbeatInterval
        }

        # Heartbeat intervals in seconds (from architecture benchmark)
        self._heartbeat_intervals = {
            HeartbeatInterval.L1S: 1,
            HeartbeatInterval.L10S: 10,
            HeartbeatInterval.L30S: 30,
            HeartbeatInterval.L60S: 60,
            HeartbeatInterval.L5M: 300,
            HeartbeatInterval.L1H: 3600,
        }

    async def _resolve_thread_id(self, project_id: str | None = None) -> str:
        """Resolve the thread_id based on the feature:projects:enabled flag.

        When the flag is ON and a project_id is present, returns
        ``f"heartbeat-{project_id}"``.  In all other cases (flag OFF,
        flag absent, Redis unreachable, or project_id is None) returns
        the legacy ``"heartbeat"``.

        This is FAIL-SAFE by design: any flag-read failure defaults to
        OFF so the heartbeat never crashes and P20 semantics are
        preserved when the flag is absent.

        Args:
            project_id: Optional project context identifier.

        Returns:
            The resolved thread_id string.
        """
        _FEATURE_FLAG_KEY = "feature:projects:enabled"
        try:
            raw = await self.redis_client.get(_FEATURE_FLAG_KEY)
        except RedisError:
            logger.warning(
                "projects_flag_redis_unreachable",
                _error="redis_unreachable_falling_back_to_legacy",
            )
            return "heartbeat"

        # Decode the Redis value and check for a semantically-on signal.
        # Only explicit truthy values ("true", "1", "yes") count as ON.
        # Everything else (None, "false", "0", "no", "") defaults to OFF
        # so that a random accidental write never changes thread_id.
        if raw is not None:
            decoded = raw.decode() if isinstance(raw, bytes) else str(raw)
            flag_on = decoded.strip().lower() in ("true", "1", "yes")
        else:
            flag_on = False

        if flag_on and project_id:
            return f"heartbeat-{project_id}"

        return "heartbeat"

    async def start(self) -> None:
        """Start all heartbeat loops as asyncio tasks.

        Creates an asyncio task for each interval type and starts them immediately.
        Returns immediately after starting all tasks.

        Logs:
            - DEBUG: Each heartbeat starts
        """
        logger.debug("heartbeat_service_starting")

        for interval_type in HeartbeatInterval:
            task = asyncio.create_task(self._heartbeat_loop(interval_type))
            self._tasks.add(task)
            logger.debug(
                "heartbeat_loop_started",
                interval_type=interval_type.value,
                duration=self._heartbeat_intervals[interval_type],
            )

        logger.info("heartbeat_service_started", interval_count=len(self._tasks))

    async def stop(self) -> None:
        """Stop all heartbeat loops.

        Cancels all running tasks and waits for them to complete gracefully.
        Clears the tasks set. Prevents self-deadlock when called from within
        a heartbeat task (e.g. HARD STOP detection in _heartbeat_1s).

        Logs:
            - DEBUG: Each task cancelled
            - INFO: Service stopped
        """
        logger.debug("heartbeat_service_stopping", task_count=len(self._tasks))

        # Identify the calling task to exclude from gather (prevents self-deadlock
        # when stop() is called from within a heartbeat — e.g. HARD STOP in _heartbeat_1s)
        current = asyncio.current_task()

        # Cancel all tasks
        for task in self._tasks:
            task.cancel()

        # Wait for all tasks EXCEPT the current caller to complete
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

    async def _heartbeat_loop(self, interval_type: HeartbeatInterval) -> None:
        """Heartbeat loop for a specific interval type.

        This is the main loop for each interval type. It sleeps for the duration
        and executes the corresponding heartbeat handler. Continues indefinitely
        until the service is stopped.

        Args:
            interval_type: The interval type to execute.

        Logs:
            - DEBUG: Each heartbeat execution
            - ERROR: Heartbeat errors (logged but don't crash service)
        """
        duration = self._heartbeat_intervals[interval_type]

        logger.debug("heartbeat_loop_started", interval_type=interval_type.value)

        while True:
            try:
                # Execute heartbeat
                start_time = time.perf_counter()

                if interval_type == HeartbeatInterval.L1S:
                    await self._heartbeat_1s()
                elif interval_type == HeartbeatInterval.L10S:
                    await self._heartbeat_10s()
                elif interval_type == HeartbeatInterval.L30S:
                    await self._heartbeat_30s()
                elif interval_type == HeartbeatInterval.L60S:
                    await self._heartbeat_60s()
                elif interval_type == HeartbeatInterval.L5M:
                    await self._heartbeat_5m()
                elif interval_type == HeartbeatInterval.L1H:
                    await self._heartbeat_1h()
                else:
                    logger.error("unknown_interval_type", interval_type=interval_type.value)
                    continue

                # Calculate and log latency
                elapsed = time.perf_counter() - start_time
                logger.debug(
                    "heartbeat_completed",
                    interval_type=interval_type.value,
                    latency_ms=elapsed * 1000,
                )

                # Record last heartbeat time and increment count
                self._last_heartbeats[interval_type] = time.time()
                self._heartbeat_counts[interval_type] += 1

            except asyncio.CancelledError:
                logger.debug("heartbeat_loop_cancelled", interval_type=interval_type.value)
                raise
            except Exception as e:
                logger.error(
                    "heartbeat_loop_error",
                    interval_type=interval_type.value,
                    error=str(e),
                    exc_info=True,
                )
                # Continue loop on error - don't crash the service

            # Sleep for duration
            try:
                await asyncio.sleep(duration)
            except asyncio.CancelledError:
                logger.debug("heartbeat_loop_sleep_cancelled", interval_type=interval_type.value)
                raise

    async def _heartbeat_1s(self) -> None:
        """Liveness heartbeat with HARD STOP detection AND recovery.

        This is the SAFETY heartbeat — checks EVERY second for the live HARD
        STOP flag in Redis. The *live* Redis flag is the single source of
        truth; stale checkpoint state (``hard_stop_requested=True`` persisted
        in the LangGraph checkpoint) is recovered by clearing it when the
        Redis flag is absent. This fixes the stuck-HARD-STOP bug where the
        kernel spun to END ~195k times with no live signal.

        On live HARD STOP: sets the flag in checkpoint state, publishes a
        HARD STOP dashboard update (bypassing the checksum-skip so it is
        visible immediately), writes a lifecycle log line, then stops the
        heartbeat service.

        MUST NOT block — every network call is wrapped in try/except so a
        Discord or Redis outage does not delay the safety check.
        """
        try:
            hard_stop_key = "life_kernel:hard_stop"
            try:
                hard_stop_value = await self.redis_client.get(hard_stop_key)
            except Exception as redis_err:  # noqa: BLE001
                # If Redis is unreachable we must NOT assume the flag is
                # absent (fail-closed on safety). Do not clear state.
                logger.error("hard_stop_redis_unreachable", error_type=type(redis_err).__name__)
                return

            live_hard_stop = bool(hard_stop_value)

            if live_hard_stop:
                if not self._hard_stop_announced:
                    logger.warning(
                        "hard_stop_detected_live",
                        hard_stop_value=(
                            hard_stop_value.decode()
                            if isinstance(hard_stop_value, bytes)
                            else str(hard_stop_value)
                        ),
                    )
                    self._hard_stop_announced = True
                    self._recovery_announced = False

                if self.graph:
                    try:
                        _t = await self._resolve_thread_id(self.project_id)
                        await self.graph.ainvoke(
                            {"hard_stop_requested": True, "is_active": False, "project_id": self.project_id},
                            config={
                                "configurable": {"thread_id": _t},
                                "recursion_limit": 25,
                            },
                        )
                        logger.info("hard_stop_requested_set_in_state")
                    except Exception as e:  # noqa: BLE001
                        logger.error("hard_stop_set_failed", error=str(e), exc_info=True)

                # Publish HARD STOP to Discord BEFORE stopping (best-effort,
                # never blocks stop). Fail-soft — dashboard/log writes may fail.
                try:
                    if self._discord_publisher is not None:
                        state = await self._safe_aget_state()
                        if state is not None:
                            await self._discord_publisher.publish_hard_stop(state)
                    if self._log_channel is not None:
                        await self._log_channel.write("[HARD_STOP] Kernel halted by operator")
                except Exception as pub_err:  # noqa: BLE001
                    logger.warning("hard_stop_discord_publish_failed", error_type=type(pub_err).__name__)

                await self.stop()
                logger.info("heartbeat_stopped_due_to_hard_stop")
                return

            # No live flag. Recover if checkpoint state is stale (stuck
            # hard_stop_requested=True with no live Redis signal).
            try:
                state = await self._safe_aget_state()
            except Exception:  # noqa: BLE001
                state = None
            stale = bool(state and state.get("hard_stop_requested", False))

            if stale:
                logger.warning("hard_stop_recovery_clearing_stale_state")
                try:
                    if self.graph:
                        _t = await self._resolve_thread_id(self.project_id)
                        await self.graph.ainvoke(
                            {"hard_stop_requested": False, "is_active": True, "project_id": self.project_id},
                            config={
                                "configurable": {"thread_id": _t},
                                "recursion_limit": 25,
                            },
                        )
                    self._recovery_announced = True
                    self._hard_stop_announced = False
                    if self._log_channel is not None:
                        await self._log_channel.write("[RECOVERY] HARD STOP cleared, kernel active")
                except Exception as e:  # noqa: BLE001
                    logger.error("hard_stop_recovery_clear_failed", error=str(e), exc_info=True)
                return

            # Normal liveness: DEBUG level to avoid spam.
            logger.debug("heartbeat_liveness_check", timestamp=datetime.now().isoformat())

        except Exception as e:  # noqa: BLE001
            logger.error("heartbeat_1s_error", error=str(e), exc_info=True)

    async def _safe_aget_state(self) -> dict[str, Any] | None:
        """Return the graph state dict, or None if unavailable. Fail-soft."""
        if self.graph is None:
            return None
        try:
            _t = await self._resolve_thread_id(self.project_id)
            state = await self.graph.aget_state(
                config={"configurable": {"thread_id": _t}},
            )
        except Exception:  # noqa: BLE001
            return None
        if state is None:
            return None
        return getattr(state, "values", None) or {}

    async def _heartbeat_10s(self) -> None:
        """Graph health check heartbeat.

        Checks if the graph has been stuck (same phase > 30s without transition).
        Logs graph health and can trigger alerts if stuck.

        Placeholder for future stuck detection logic.

        Logs:
            - DEBUG: Graph health check
            - WARNING: Graph stuck detected (future)
        """
        try:
            logger.debug("heartbeat_10s_graph_health_check")

            # Placeholder: Check if graph has been stuck
            # Future: Track phase transitions and detect prolonged idle/busy states

            # Log current state (if available)
            if self.graph:
                # Future: Query graph state for health metrics
                pass

        except Exception as e:
            logger.error("heartbeat_10s_error", error=str(e), exc_info=True)
            # Continue on error - don't crash the service

    async def _heartbeat_30s(self) -> None:
        """Awareness refresh heartbeat.

        Refreshes awareness from sensors (wired in LK-011).
        Reads sensor data and updates the world model.

        Placeholder for future sensor integration.

        Logs:
            - DEBUG: Awareness refresh
        """
        try:
            logger.debug("heartbeat_30s_awareness_refresh")

            # Placeholder: Refresh awareness from sensors
            # Future: Call sensor adapters to read sensor data and update world model

        except Exception as e:
            logger.error("heartbeat_30s_error", error=str(e), exc_info=True)
            # Continue on error - don't crash the service

    async def _heartbeat_60s(self) -> None:
        """Decision heartbeat.

        Invokes the graph to trigger the OBSERVE→DECIDE cycle when the graph is
        in IDLE or OBSERVE phase. This is the decision heartbeat — creates new tasks
        when no work exists (autonomy principle: V-003 silence is not a blocker).

        Skips invocation when graph is busy (ACT or REFLECT phase) to avoid
        interrupting active work.

        Logs:
            - DEBUG: Decision heartbeat
            - INFO: Graph invoked
            - INFO: Graph skipped (busy phase or IDLE gate)
        """
        try:
            logger.debug("heartbeat_60s_decision")

            if not self.graph:
                logger.warning("no_graph_available")
                return

            # Query graph state to check current phase
            try:
                _t = await self._resolve_thread_id(self.project_id)
                state = await self.graph.aget_state(
                    config={"configurable": {"thread_id": _t}},
                )
                if state and state.values:
                    current_phase = state.values.get("current_phase", LifeMindPhase.IDLE)
                    if current_phase in (LifeMindPhase.ACT, LifeMindPhase.REFLECT):
                        logger.info(
                            "heartbeat_60s_skipped_busy",
                            current_phase=current_phase.value,
                        )
                        return
            except Exception:
                # Graph may not have a checkpointer — proceed with invoke
                logger.debug("heartbeat_60s_no_checkpointer")

            # Invoke graph with decision signal
            try:
                _t = await self._resolve_thread_id(self.project_id)
                result = await self.graph.ainvoke(
                    {"decision": "continue", "is_active": True, "project_id": self.project_id},
                    config={
                        "configurable": {"thread_id": _t},
                        "recursion_limit": 25,
                    },
                )
                # PRIVACY (cleanup blocker #2): never log the raw graph result
                # — it contains recalled_memories (P18 content, possibly
                # Critical-classified), journal_entries (reflective reasoning),
                # and observations. Logging it verbatim leaks personal/intimate
                # data into structlog (and the Discord log channel via the
                # lifecycle line). Log a SANITIZED SUMMARY only: counts and
                # the decision/next-action labels (which are display-only and
                # already sanitised by DashboardRenderer before publishing).
                _summary = {
                    "phase": result.get("current_phase"),
                    "decision": result.get("decision"),
                    "last_autonomous_decision": result.get("last_autonomous_decision"),
                    "cycle_count": result.get("cycle_count"),
                    "act_count": result.get("act_count"),
                    "n_goals": len(result.get("goals", []) or []),
                    "n_commitments": len(result.get("commitments", []) or []),
                    "n_concerns": len(result.get("concerns", []) or []),
                    "n_observations": len(result.get("observations", []) or []),
                    "n_recalled_memories": len(result.get("recalled_memories", []) or []),
                    "n_recalled_concepts": len(result.get("recalled_concepts", []) or []),
                    "n_journal_entries": len(result.get("journal_entries", []) or []),
                    "world_model_status": result.get("world_model_status"),
                    "hard_stop_requested": result.get("hard_stop_requested"),
                }
                logger.info("graph_invoked_decision_heartbeat", **_summary)
            except Exception as e:
                logger.error("graph_invoke_failed", error=str(e), exc_info=True)

            # Publish the dashboard (edit-not-spam) + a throttled lifecycle
            # log line. Both are fail-soft: a Discord outage never blocks the
            # heartbeat, and the lifecycle log is throttled to one line per 5
            # minutes so the log channel reads as a calm narrative, not spam.
            try:
                state = await self._safe_aget_state()
                if state is not None:
                    if self._discord_publisher is not None:
                        await self._discord_publisher.update_dashboard(state)
                    await self._log_lifecycle_milestone(state)
            except Exception as pub_err:  # noqa: BLE001
                logger.warning(
                    "dashboard_publish_failed",
                    error_type=type(pub_err).__name__,
                    error_message=str(pub_err)[:400],
                )

        except Exception as e:
            logger.error("heartbeat_60s_error", error=str(e), exc_info=True)
            # Continue on error - don't crash the service

    async def _log_lifecycle_milestone(self, state: dict[str, Any]) -> None:
        """Write a throttled, meaningful lifecycle log line.

        Summarizes the observe/decide/act/idle cycle in one compact line so the
        log channel shows Guinevere's autonomous behavior without spam. The
        line is deduped: an identical summary suppresses the next write, and
        even distinct summaries are capped at one per 5 minutes.
        """
        if self._log_channel is None:
            return
        phase = state.get("current_phase", "idle")
        acts = state.get("act_count", 0)
        cycles = state.get("cycle_count", 0)
        decision = state.get("last_autonomous_decision", "—")
        next_action = state.get("next_planned_action", "—")
        hard_stop = state.get("hard_stop_requested", False)
        focus = state.get("current_focus", "—")
        world_model = state.get("world_model_status", "—")
        n_mem = len(state.get("recalled_memories", []) or [])
        n_kg = len(state.get("recalled_concepts", []) or [])
        # T12: include a one-sentence autonomous-intent narrative so the log
        # channel reads as Guinevere's living behaviour, not raw counters.
        intent = next_action if next_action and next_action != "—" else decision
        line = (
            f"[cycle {cycles}] phase={phase} focus={focus} acts={acts} "
            f"decision={decision} intent=\"{intent}\" "
            f"recall=mem:{n_mem}/kg:{n_kg} world_model={world_model} "
            f"hard_stop={hard_stop}"
        )
        # DUX-01 fix: Discord rejects plain-text messages over 2000 chars.
        # Long intent/focus values could push this line past the limit, so
        # cap it well below 2000 (1900 leaves headroom for any wrapper).
        _DISCORD_LOG_MAX = 1900
        if len(line) > _DISCORD_LOG_MAX:
            line = line[: _DISCORD_LOG_MAX - 3] + "..."
        now = time.time()
        # Throttle: skip if the line is identical to the last one we wrote, OR
        # if we wrote any line less than _LIFECYCLE_LOG_THROTTLE_SECONDS ago.
        # Use a dedicated timestamp (not the 1s heartbeat's), so a busy 1s
        # heartbeat never starves the lifecycle log.
        last_t = self._last_lifecycle_log_ts
        if line == self._last_log_line or (now - last_t) < _LIFECYCLE_LOG_THROTTLE_SECONDS:
            # Still update the dashboard (above); only skip the noisy log line.
            return
        self._last_log_line = line
        self._last_lifecycle_log_ts = now
        try:
            await self._log_channel.write(line)
        except Exception as exc:  # noqa: BLE001 — fail-soft
            logger.warning("lifecycle_log_write_failed", error_type=type(exc).__name__)

    async def _heartbeat_5m(self) -> None:
        """Deep scan heartbeat.

        Performs deep scan of domain minds for anomalies and health checks.
        Checks domain mind states and identifies potential issues.

        Placeholder for future domain mind scanning.

        Logs:
            - DEBUG: Deep scan heartbeat
        """
        try:
            logger.debug("heartbeat_5m_deep_scan")

            # Placeholder: Deep scan domain minds
            # Future: Query domain mind states and check for anomalies

        except Exception as e:
            logger.error("heartbeat_5m_error", error=str(e), exc_info=True)
            # Continue on error - don't crash the service

    async def _heartbeat_1h(self) -> None:
        """Reflection heartbeat.

        Performs reflection, memory consolidation, and self-improvement evaluation.
        Reviews kernel performance, consolidates memory, and identifies areas for
        self-improvement.

        Placeholder for future reflection logic.

        Logs:
            - DEBUG: Reflection heartbeat
        """
        try:
            logger.debug("heartbeat_1h_reflection")

            # AC-LIFE-009: evaluate self-improvement candidates from the
            # current kernel state. ReflectionEvaluator inspects metrics
            # (errors, efficiency, idle, queue) and proposes skill/prompt/
            # planner/code improvement candidates. Candidates are display-
            # only records — promotion requires regression tests + audit
            # (LK-015), never auto-applied here. Fail-soft: any failure
            # logs a warning and the heartbeat continues.
            try:
                state = await self._safe_aget_state()
            except Exception:  # noqa: BLE001
                state = None

            if state is not None:
                try:
                    from guinvere.life_kernel.self_improve import (
                        ImprovementTracker,
                        ReflectionEvaluator,
                    )

                    # ReflectionEvaluator requires the compiled graph + config
                    # (RUN-01/DOC-02 fix: it was instantiated with no args,
                    # raising TypeError every hour and silently breaking
                    # AC-LIFE-009). Pass the heartbeat's graph + thread config.
                    _t = await self._resolve_thread_id(self.project_id)
                    graph_config = {
                        "configurable": {"thread_id": _t},
                        "recursion_limit": 25,
                    }
                    evaluator = ReflectionEvaluator(
                        graph=self.graph,
                        graph_config=graph_config,
                        hermes_brain=self._hermes_brain,
                    )
                    tracker = ImprovementTracker()
                    # evaluate() is sync (in-memory heuristics) — run it off
                    # the event loop so a future heavier implementation cannot
                    # block the 1h heartbeat (RUN-02).
                    candidates = await asyncio.to_thread(evaluator.evaluate, state)
                    for candidate in candidates:
                        tracker.propose(candidate)
                    # ImprovementCandidate exposes `.category` (a
                    # CandidateCategory enum), not `candidate_type` (AUTO-06
                    # fix — the old getattr logged '?' for every candidate).
                    categories = [
                        str(getattr(c, "category", "?")) for c in candidates
                    ]
                    logger.info(
                        "heartbeat_1h_self_improvement",
                        candidates_generated=len(candidates),
                        candidate_categories=categories,
                    )
                    if candidates and self._log_channel is not None:
                        # Log a calm narrative line so the improvement
                        # candidates are visible without spam.
                        try:
                            await self._log_channel.write(
                                f"[reflection] generated {len(candidates)} self-improvement "
                                f"candidate(s): {categories}"
                            )
                        except Exception:  # noqa: BLE001 — fail-soft
                            pass
                except Exception as si_err:  # noqa: BLE001 — fail-soft
                    logger.warning(
                        "heartbeat_1h_self_improvement_failed",
                        error_type=type(si_err).__name__,
                    )

        except Exception as e:
            logger.error("heartbeat_1h_error", error=str(e), exc_info=True)
            # Continue on error - don't crash the service

    def get_last_heartbeat_time(self, interval_type: HeartbeatInterval) -> float | None:
        """Get the last execution time for an interval type.

        Args:
            interval_type: The interval type to query.

        Returns:
            Last execution timestamp or None if not executed yet.
        """
        return self._last_heartbeats.get(interval_type)