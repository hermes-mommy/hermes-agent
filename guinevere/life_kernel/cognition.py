"""Background cognition system for Guinevere's Living Autonomy Kernel (LK-007).

This module provides the ``BackgroundCognition`` class — six independent,
asynchronous observer loops that continuously feed observations into the
life-mind graph state.  All writes are serialized through an ``asyncio.Queue``
to avoid concurrent ``graph.ainvoke`` collisions.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from datetime import datetime
from typing import Any

import structlog

from guinevere.life_kernel.state import Priority

logger = structlog.get_logger(__name__)


class BackgroundCognition:
    """Six asynchronous observer loops for the living autonomy kernel.

    Each loop runs as an independent ``asyncio.Task`` and writes observations
    to the compiled life-mind graph via a shared ``asyncio.Queue``.  The queue
    guarantees that only one ``graph.ainvoke`` call touches the graph state at
    a time.

    Attributes:
        graph: Compiled LangGraph StateGraph for the life-mind kernel.
        graph_config: Runtime configuration used for ``graph.ainvoke``.
            Expected to contain ``thread_id`` either directly or under
            ``configurable``.
        hermes_brain: Optional Hermes brain bridge used only by critic/curiosity
            loops in later milestones.  **Never called by placeholder logic.**
    """

    def __init__(
        self,
        graph: Any,
        graph_config: dict[str, Any],
        hermes_brain: Any | None = None,
        sensor_registry: Any | None = None,
        project_id: str | None = None,
    ) -> None:
        """Initialize the background cognition service.

        Args:
            graph: Compiled LangGraph StateGraph for the life-mind kernel.
            graph_config: Dict with ``thread_id`` (e.g. ``{"thread_id": "abc"}``
                or ``{"configurable": {"thread_id": "abc"}}``).
            hermes_brain: Optional Hermes brain bridge (placeholder only).
            sensor_registry: Optional sensor registry for real sensor polling.
                SensorRegistry is optional; when absent, observer produces
                placeholder observations. Real sensors wired in LK-011.
            project_id: Optional project namespace. Logged only; the caller
                supplies a per-project graph/config when running in multi-project
                mode.
        """
        self.graph = graph
        self.graph_config = graph_config
        self.hermes_brain = hermes_brain
        self.sensor_registry = sensor_registry
        self.project_id = project_id

        self._tasks: set[asyncio.Task[Any]] = set()
        self._write_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._write_task: asyncio.Task[Any] | None = None
        self._stop_event = asyncio.Event()

        # Loop intervals in seconds.
        self._loop_intervals: dict[str, float] = {
            "observer": 10.0,
            "memory": 300.0,
            "critic": 300.0,
            "curiosity": 3600.0,
            "self_improvement": 3600.0,
            "guardian": 10.0,
        }

        # Mapping of public loop methods to their interval keys.
        self._loops: dict[str, Callable[[], Coroutine[Any, Any, None]]] = {
            "observer": self.observer,
            "memory": self.memory,
            "critic": self.critic,
            "curiosity": self.curiosity,
            "self_improvement": self.self_improvement,
            "guardian": self.guardian,
        }

    @property
    def running(self) -> bool:
        """Return True if at least one background loop task is active."""
        return any(not task.done() for task in self._tasks)

    async def start(self) -> None:
        """Start all six background loops and the graph write worker.

        Launches independent asyncio tasks for observer, memory, critic,
        curiosity, self_improvement, and guardian loops, plus a single
        worker task that drains the write queue.
        """
        logger.info("background_cognition_starting", project_id=self.project_id)
        self._stop_event.clear()

        self._write_task = asyncio.create_task(self._write_loop())

        for loop_name, coro in self._loops.items():
            task = asyncio.create_task(self._run_loop(loop_name, coro))
            self._tasks.add(task)
            logger.debug(
                "background_loop_started",
                loop=loop_name,
                interval=self._loop_intervals[loop_name],
                project_id=self.project_id,
            )

        logger.info(
            "background_cognition_started",
            loop_count=len(self._tasks),
            project_id=self.project_id,
        )

    async def stop(self) -> None:
        """Cancel all background loops and the graph write worker.

        Sets the stop event, cancels every running loop, and waits briefly for
        graceful shutdown.  In-flight observations are best-effort drained.
        """
        logger.info(
            "background_cognition_stopping",
            task_count=len(self._tasks),
            project_id=self.project_id,
        )
        self._stop_event.set()

        for task in self._tasks:
            task.cancel()

        tasks_to_await = list(self._tasks)
        self._tasks.clear()

        if self._write_task is not None:
            self._write_task.cancel()
            tasks_to_await.append(self._write_task)
            self._write_task = None

        if tasks_to_await:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks_to_await, return_exceptions=True),
                    timeout=5.0,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "background_cognition_stop_timeout",
                    pending_count=len(tasks_to_await),
                    project_id=self.project_id,
                )

        logger.info("background_cognition_stopped", project_id=self.project_id)

    async def _run_loop(
        self,
        loop_name: str,
        coro: Callable[[], Coroutine[Any, Any, None]],
    ) -> None:
        """Generic runner for a single background loop.

        Executes the loop coroutine, catches non-fatal errors, and sleeps for
        the configured interval until ``stop()`` is called.

        Args:
            loop_name: Human-readable loop name used for logging.
            coro: Coroutine function to execute each iteration.
        """
        interval = self._loop_intervals[loop_name]

        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=interval,
                )
            except asyncio.TimeoutError:
                pass

            if self._stop_event.is_set():
                break

            try:
                await coro()
            except asyncio.CancelledError:
                logger.debug("loop_cancelled", loop=loop_name, project_id=self.project_id)
                raise
            except Exception as exc:
                logger.error(
                    "background_loop_error",
                    loop=loop_name,
                    error=str(exc),
                    project_id=self.project_id,
                    exc_info=True,
                )

    async def _write_loop(self) -> None:
        """Drain the write queue and invoke ``graph.ainvoke`` serially.

        This worker is the only task that writes to the graph, ensuring all
        observations are serialized through ``asyncio.Queue``.
        """
        while not self._stop_event.is_set():
            try:
                observation = await asyncio.wait_for(
                    self._write_queue.get(),
                    timeout=0.5,
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                logger.debug("write_loop_cancelled", project_id=self.project_id)
                raise

            try:
                await self._invoke_graph_write(observation)
            except Exception as exc:
                logger.error(
                    "graph_write_error",
                    loop=observation.get("loop"),
                    error=str(exc),
                    project_id=self.project_id,
                    exc_info=True,
                )

    async def _invoke_graph_write(self, observation: dict[str, Any]) -> None:
        """Write a single observation to the graph state.

        Normalizes ``graph_config`` to the LangGraph ``configurable`` shape and
        invokes ``graph.ainvoke`` with the observation wrapped in a list.

        Args:
            observation: Observation dict to append to graph state.

        Raises:
            AttributeError: If ``graph`` is None or does not expose ``ainvoke``.
        """
        if self.graph is None:
            logger.warning("graph_not_available_skip_write", project_id=self.project_id)
            return

        config = self.graph_config or {}
        if "configurable" not in config:
            config = {"configurable": config}
        config["recursion_limit"] = 25

        await self.graph.ainvoke(
            {"observations": [observation]},
            config,
        )

    async def _write_to_graph(self, observation: dict[str, Any]) -> None:
        """Enqueue an observation for serialized graph writing.

        Args:
            observation: Observation dict produced by a background loop.
        """
        await self._write_queue.put(observation)
        logger.debug(
            "observation_queued",
            source=observation.get("source"),
            loop=observation.get("loop"),
            priority=str(observation.get("priority")),
            project_id=self.project_id,
        )

    def _make_observation(
        self,
        loop: str,
        content: str,
        priority: Priority,
    ) -> dict[str, Any]:
        """Build a standardized observation dict.

        Args:
            loop: Loop name (observer, memory, critic, etc.).
            content: Human-readable observation content.
            priority: Autonomy priority level.

        Returns:
            Observation dict matching the required schema.
        """
        source = "observer" if loop == "observer" else "cognition"
        observation: dict[str, Any] = {
            "source": source,
            "loop": loop,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "priority": priority,
        }
        if self.project_id is not None:
            observation["project_id"] = self.project_id
        return observation

    # ── Public loop methods ─────────────────────────────────────────────────

    async def observer(self) -> None:
        """Poll sensors every 10 seconds.

        If a :class:`SensorRegistry` was provided, this method calls
        ``sense_all()`` and writes every returned observation to the graph.
        Otherwise it writes a single placeholder observation.  SensorRegistry
        is optional; when absent, observer produces placeholder observations.
        Real sensors wired in LK-011.
        """
        logger.debug("observer_tick", project_id=self.project_id)

        if self.sensor_registry is not None:
            observations = await self.sensor_registry.sense_all()
            for observation in observations:
                await self._write_to_graph(
                    {
                        "source": "observer",
                        "loop": "observer",
                        "content": str(observation),
                        "timestamp": datetime.now().isoformat(),
                        "priority": Priority.KEEP_ALIVE,
                    }
                )
            return

        observation = self._make_observation(
            loop="observer",
            content="Sensor poll placeholder — no real sensors wired (LK-010/LK-011).",
            priority=Priority.KEEP_ALIVE,
        )
        await self._write_to_graph(observation)

    async def memory(self) -> None:
        """Scan recent observations for memory patterns every 5 minutes (placeholder).

        Writes a placeholder memory observation.  Real P18 memory recall
        integration is planned for a later milestone.
        """
        logger.debug("memory_tick", project_id=self.project_id)
        observation = self._make_observation(
            loop="memory",
            content="Memory pattern scan placeholder — waiting for P18 memory recall integration.",
            priority=Priority.IMPROVE_AUTONOMY,
        )
        await self._write_to_graph(observation)

    async def critic(self) -> None:
        """Analyze recent actions for errors/anomalies every 5 minutes (placeholder).

        The optional ``hermes_brain`` is **never called** by placeholder logic.
        Real anomaly detection via Hermes arrives in LK-014.
        """
        logger.debug("critic_tick", project_id=self.project_id)
        if self.hermes_brain is not None:
            logger.debug("critic_hermes_available_placeholder_only", project_id=self.project_id)

        observation = self._make_observation(
            loop="critic",
            content="Critic analysis placeholder — recent actions scanned for anomalies.",
            priority=Priority.PROTECT_SECRETS,
        )
        await self._write_to_graph(observation)

    async def curiosity(self) -> None:
        """Generate exploration questions every hour (placeholder).

        The optional ``hermes_brain`` is **never called** by placeholder logic.
        Real Hermes-driven curiosity arrives in LK-014.
        """
        logger.debug("curiosity_tick", project_id=self.project_id)
        if self.hermes_brain is not None:
            logger.debug("curiosity_hermes_available_placeholder_only", project_id=self.project_id)

        observation = self._make_observation(
            loop="curiosity",
            content="Curiosity question placeholder — self-directed learning (Hermes unused).",
            priority=Priority.EXPLORE_RESEARCH,
        )
        await self._write_to_graph(observation)

    async def self_improvement(self) -> None:
        """Evaluate SDLC loop efficiency every hour (placeholder).

        Writes a placeholder self-improvement candidate.  Real SDLC efficiency
        analysis and LK-015 integration are planned.
        """
        logger.debug("self_improvement_tick", project_id=self.project_id)
        observation = self._make_observation(
            loop="self_improvement",
            content="Self-improvement evaluation placeholder — SDLC loop efficiency scan.",
            priority=Priority.ENGINEERING,
        )
        await self._write_to_graph(observation)

    async def guardian(self) -> None:
        """Check safety boundaries every 10 seconds (placeholder).

        Checks are placeholders for LK-016.  Real guardian will validate:
        HARD STOP safety, consent boundaries, and secret leakage.
        """
        logger.debug("guardian_tick", project_id=self.project_id)
        observation = self._make_observation(
            loop="guardian",
            content=(
                "Guardian safety boundary check placeholder — "
                "HARD_STOP/consent/secrets (LK-016)."
            ),
            priority=Priority.HARD_STOP_SAFETY,
        )
        await self._write_to_graph(observation)


class ProjectAwareCognitionRegistry:
    """Registry that manages up to ``N`` concurrent ``BackgroundCognition`` instances.

    When the ``feature:projects:enabled`` flag is OFF, the registry holds a
    single legacy instance keyed by ``None`` and behaves exactly like the
    pre-P19 single-project runtime.  When the flag is ON, active projects are
    mapped to individual ``BackgroundCognition`` instances with a bounded
    concurrency cap (default 3).  Idle/paused projects do not receive
    cognition cycles, but pausing one project does NOT affect others.

    The registry never alters the global HARD STOP path.
    """

    def __init__(self, max_active: int = 3) -> None:
        self._instances: dict[str | None, BackgroundCognition] = {}
        self._max_active = max_active
        self._flag_key = "feature:projects:enabled"

    def _is_flag_on(self, redis_client: Any) -> bool:
        try:
            raw = redis_client.get(self._flag_key)
        except Exception:
                logger.debug("project_flag_read_failed_defaulting_off", exc_info=True)
                return False
        if raw is None:
            return False
        decoded = raw.decode() if isinstance(raw, bytes) else str(raw)
        return decoded.strip().lower() in ("true", "1", "yes")

    async def get_or_create(
        self,
        redis_client: Any,
        project_id: str | None,
        *,
        graph_factory: Callable[[str | None], BackgroundCognition],
    ) -> BackgroundCognition | None:
        """Return the cognition instance for a project, creating it on demand.

        Args:
            redis_client: A Redis client (sync or async) used to read the
                ``feature:projects:enabled`` flag.  Fail-safe: any read error
                returns the legacy single instance.
            project_id: Project namespace to resolve.
            graph_factory: Callable that builds a ``BackgroundCognition`` for
                the given project_id.

        Returns:
            A ``BackgroundCognition`` instance, or ``None`` if the concurrency
            cap would be exceeded.
        """
        if not self._is_flag_on(redis_client):
            if None not in self._instances:
                self._instances[None] = graph_factory(None)
            return self._instances[None]

        if project_id in self._instances:
            return self._instances[project_id]

        if len(self._instances) >= self._max_active:
            logger.warning(
                "cognition_registry_capacity_reached",
                requested_project=project_id,
                active_count=len(self._instances),
                max_active=self._max_active,
            )
            return None

        instance = graph_factory(project_id)
        self._instances[project_id] = instance
        logger.info(
            "project_cognition_instance_created",
            project_id=project_id,
            active_count=len(self._instances),
            max_active=self._max_active,
        )
        return instance

    async def pause_project(self, project_id: str) -> bool:
        """Pause cognition for a single project without affecting others.

        Returns True if an running instance was paused.
        """
        instance = self._instances.get(project_id)
        if instance is None:
            return False
        await instance.stop()
        if project_id in self._instances:
            del self._instances[project_id]
        logger.info("project_cognition_paused", project_id=project_id)
        return True

    async def stop_all(self) -> None:
        """Stop all managed cognition instances."""
        for instance in list(self._instances.values()):
            await instance.stop()
        self._instances.clear()
