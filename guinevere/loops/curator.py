"""Curator Loop — idle-time background maintenance tasks.

Runs during system idle periods (>2h inactivity by default) to perform
maintenance: skill review, memory consolidation triggers, documentation
sync checks, and cleanup of old artifacts.

Inspired by Hermes Agent's curator loop pattern.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass(frozen=True)
class CuratorTask:
    """A single maintenance task for the curator to execute.

    Attributes:
        task_type: One of "skill_review", "memory_check", "doc_sync", "cleanup".
        description: Human-readable description of what this task does.
        priority: 1 = highest priority, 10 = lowest.
        metadata: Arbitrary key-value data for task-specific configuration.
    """

    task_type: str
    description: str
    priority: int  # 1 = highest, 10 = lowest
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CuratorResult:
    """Outcome of executing a single CuratorTask.

    Attributes:
        task: The task that was executed.
        completed: Whether the task completed successfully.
        result_text: Human-readable result summary.
        duration_s: Wall-clock seconds the task took to run.
    """

    task: CuratorTask
    completed: bool
    result_text: str
    duration_s: float


class CuratorLoop:
    """Background curator — runs maintenance during idle periods.

    Monitors activity via :meth:`mark_activity`. When the idle threshold
    is exceeded, spawns maintenance tasks:

    - Skill library review (check for stale / unused skills)
    - Memory consolidation triggers (notify P18 decay sweep)
    - Documentation sync checks (verify evidence paths exist)
    - Cleanup (old loop artifacts, temp files)

    Constructor injection:

    - ``llm_router``: LLMRouter instance (``None`` = skip LLM-based tasks)
    - ``idle_threshold_s``: seconds of inactivity before curator activates
      (default 7200 = 2 hours)
    """

    def __init__(
        self,
        llm_router: Any | None = None,
        idle_threshold_s: float = 7200.0,
    ) -> None:
        self._llm_router = llm_router
        self._idle_threshold_s = idle_threshold_s
        self._last_activity: float = time.monotonic()
        self._task: asyncio.Task | None = None
        self._running: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def mark_activity(self) -> None:
        """Reset idle timer.

        Call this on every user interaction or loop start so the curator
        only runs during genuine idle periods.
        """
        self._last_activity = time.monotonic()

    def is_idle(self) -> bool:
        """Check whether the idle threshold has been exceeded."""
        return (time.monotonic() - self._last_activity) >= self._idle_threshold_s

    async def start(self) -> None:
        """Start the background curator task."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._curator_loop())
        logger.info("curator.started", idle_threshold_s=self._idle_threshold_s)

    async def stop(self) -> None:
        """Cancel the running curator task and wait for it to finish."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._running = False
        logger.info("curator.stopped")

    def is_running(self) -> bool:
        """Return whether the curator loop is currently active."""
        return self._running

    # ------------------------------------------------------------------
    # Internal loop
    # ------------------------------------------------------------------

    async def _curator_loop(self) -> None:
        """Wait for idle, then run maintenance tasks.

        The loop checks every 60 seconds for idle detection. Once idle,
        it runs all generated maintenance tasks in priority order. If
        activity resumes mid-batch, remaining tasks are aborted. After
        a full batch it sleeps 5 minutes before the next check.
        """
        try:
            while self._running:
                # Check idle
                if not self.is_idle():
                    await asyncio.sleep(60)
                    continue

                # Idle detected — run maintenance batch
                logger.info(
                    "curator.idle_detected",
                    idle_s=time.monotonic() - self._last_activity,
                )

                tasks = self._generate_maintenance_tasks()
                for task in sorted(tasks, key=lambda t: t.priority):
                    if not self.is_idle():
                        # Activity resumed — abort remaining tasks
                        logger.info(
                            "curator.activity_resumed",
                            remaining=len(tasks),
                        )
                        break
                    result = await self._run_curator_task(task)
                    logger.info(
                        "curator.task_complete",
                        task_type=task.task_type,
                        completed=result.completed,
                        duration_s=round(result.duration_s, 2),
                    )

                # After maintenance, wait before next check cycle
                await asyncio.sleep(300)  # 5 minutes

        except asyncio.CancelledError:
            logger.info("curator.cancelled")
            raise

    # ------------------------------------------------------------------
    # Task generation
    # ------------------------------------------------------------------

    def _generate_maintenance_tasks(self) -> list[CuratorTask]:
        """Generate the list of maintenance tasks for the current idle batch."""
        tasks: list[CuratorTask] = []

        # Skill review (priority 1 — highest)
        tasks.append(
            CuratorTask(
                task_type="skill_review",
                description="Review skill library for stale or unused skills",
                priority=1,
            )
        )

        # Memory check (priority 2)
        tasks.append(
            CuratorTask(
                task_type="memory_check",
                description="Check memory consolidation status and trigger decay sweep if needed",
                priority=2,
            )
        )

        # Doc sync (priority 3)
        tasks.append(
            CuratorTask(
                task_type="doc_sync",
                description="Verify evidence paths exist for recent loops",
                priority=3,
            )
        )

        # Cleanup (priority 5)
        tasks.append(
            CuratorTask(
                task_type="cleanup",
                description="Clean up old loop artifacts and temp files",
                priority=5,
            )
        )

        return tasks

    # ------------------------------------------------------------------
    # Single task execution
    # ------------------------------------------------------------------

    async def _run_curator_task(self, task: CuratorTask) -> CuratorResult:
        """Execute a single curator task and return its result."""
        start = time.monotonic()

        try:
            # Route to task-specific handler
            if task.task_type == "skill_review":
                result_text = await self._task_skill_review()
            elif task.task_type == "memory_check":
                result_text = await self._task_memory_check()
            elif task.task_type == "doc_sync":
                result_text = await self._task_doc_sync()
            elif task.task_type == "cleanup":
                result_text = await self._task_cleanup()
            else:
                result_text = f"Unknown task type: {task.task_type}"
                return CuratorResult(
                    task=task,
                    completed=False,
                    result_text=result_text,
                    duration_s=time.monotonic() - start,
                )

            return CuratorResult(
                task=task,
                completed=True,
                result_text=result_text,
                duration_s=time.monotonic() - start,
            )

        except Exception as err:
            logger.warning(
                "curator.task_failed",
                task_type=task.task_type,
                error=str(err),
            )
            return CuratorResult(
                task=task,
                completed=False,
                result_text=f"Error: {err}",
                duration_s=time.monotonic() - start,
            )

    # ------------------------------------------------------------------
    # Task handlers  (placeholders — real integration in later phases)
    # ------------------------------------------------------------------

    async def _task_skill_review(self) -> str:
        """Review skill library for stale / unused skills.

        Placeholder for P5-015 skill library integration.
        """
        # Future: query ProceduralSkills table, check last_used, flag stale skills
        return "Skill review: no skill library integrated yet (P5-015 pending)"

    async def _task_memory_check(self) -> str:
        """Check memory consolidation status.

        Placeholder for P18 integration.
        """
        # Future: check if P18 decay sweep ran recently, trigger if overdue
        return "Memory check: P18 decay sweep integration pending"

    async def _task_doc_sync(self) -> str:
        """Verify evidence paths exist for recent loops.

        Placeholder for evidence pipeline integration.
        """
        # Future: query LoopInstances, check evidence paths exist
        return "Doc sync: evidence path verification pending"

    async def _task_cleanup(self) -> str:
        """Clean up old loop artifacts and temp files.

        Placeholder for artifact retention policy.
        """
        # Future: delete loop artifacts older than retention_days
        return "Cleanup: artifact retention policy pending"


def create_curator(llm_router: Any | None = None) -> CuratorLoop:
    """Factory: create a :class:`CuratorLoop` with optional LLM router injection.

    Args:
        llm_router: An optional LLM router instance. Pass ``None`` (the
            default) to skip LLM-based tasks.

    Returns:
        A new ``CuratorLoop`` instance ready to be started.
    """
    return CuratorLoop(llm_router=llm_router)
