"""Daily ritual scheduler — 5 rituals at specific WIB times.

P4-008: Ritual scheduler setup using APScheduler 3.x AsyncIOScheduler.
Fires 5 persona rituals at fixed Asia/Jakarta (WIB, UTC+7) times:
morning (07:00), midday (12:00), afternoon (17:00), evening (21:00),
midnight (00:00).

DND window: 00:00–07:00 WIB — rituals during this window are skipped
unless ``dnd_bypass=True`` (reserved for D3/D4 emergencies only).

.. deprecated:: Phase 5
    This module is **deprecated** in favour of Hermes cron (``~/.hermes/crontab.yaml``)
    and PersonaPlugin (``src/hermes/plugins/persona_plugin.py``).  APScheduler is
    removed from the active production path.  The module remains importable for
    backward compatibility during migration.  Scheduled removal: Phase 7.
"""

from __future__ import annotations

import importlib
import warnings

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Final
from zoneinfo import ZoneInfo

import asyncio

import structlog

warnings.warn(
    "ritual_scheduler.py is deprecated in Phase 5. "
    "Use Hermes cron (~/.hermes/crontab.yaml) and PersonaPlugin instead. "
    "Scheduled removal: Phase 7.",
    DeprecationWarning,
    stacklevel=2,
)

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Timezone constant
# ---------------------------------------------------------------------------

TZ_JAKARTA: Final[str] = "Asia/Jakarta"
"""IANA timezone identifier for Western Indonesia Time (WIB, UTC+7)."""

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class RitualSchedulerError(Exception):
    """Base exception for ritual scheduler errors."""


class RitualExecutionError(RitualSchedulerError):
    """Raised when a ritual execution fails."""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RitualConfig:
    """Configuration for a single daily ritual.

    Attributes:
        name: Unique ritual identifier (e.g. ``"morning"``).
        hour: Hour component in Asia/Jakarta (0–23).
        minute: Minute component (0–59).
        default_message: Persona message delivered when the ritual fires.
        mood_aware: If ``True``, message adapts to current mood state.
        dnd_bypass: If ``True``, bypasses DND (only D3/D4 emergencies).
    """

    name: str
    hour: int
    minute: int
    default_message: str
    mood_aware: bool = False
    dnd_bypass: bool = False


@dataclass(frozen=True)
class RitualResult:
    """Result of a single ritual execution.

    Attributes:
        name: Ritual identifier that was executed.
        executed_at: Timestamp of execution (timezone-aware, Asia/Jakarta).
        message: The message that was (or would be) delivered.
        success: Whether the ritual completed without error.
        error: Error description if ``success`` is ``False``, else ``None``.
    """

    name: str
    executed_at: datetime
    message: str
    success: bool
    error: str | None = None


# ---------------------------------------------------------------------------
# Ritual definitions — all times in Asia/Jakarta (WIB, UTC+7)
# ---------------------------------------------------------------------------

RITUALS: Final[list[RitualConfig]] = [
    RitualConfig(
        name="morning",
        hour=7,
        minute=0,
        default_message="Selamat pagi, Darling. Mommy sudah siap nemenin hari kamu.",
        mood_aware=True,
    ),
    RitualConfig(
        name="midday",
        hour=12,
        minute=0,
        default_message="Sayang, udah siang. Jangan lupa makan dan istirahat ya.",
        mood_aware=True,
    ),
    RitualConfig(
        name="afternoon",
        hour=17,
        minute=0,
        default_message="Sore, Darling. Gimana hari ini? Cerita sama Mommy.",
        mood_aware=True,
    ),
    RitualConfig(
        name="evening",
        hour=21,
        minute=0,
        default_message="Malam, sayang. Waktunya wind-down. Mommy di sini.",
        mood_aware=True,
    ),
    RitualConfig(
        name="midnight",
        hour=0,
        minute=0,
        default_message="Self-evaluation complete. Silent mode until morning.",
        mood_aware=False,
    ),
]

# ---------------------------------------------------------------------------
# DND (Do-Not-Disturb) window
# ---------------------------------------------------------------------------

DND_START_HOUR: Final[int] = 0
"""DND window start hour (inclusive), Asia/Jakarta."""

DND_END_HOUR: Final[int] = 7
"""DND window end hour (exclusive), Asia/Jakarta."""


# ---------------------------------------------------------------------------
# Ritual name → config lookup
# ---------------------------------------------------------------------------

_RITUAL_MAP: Final[dict[str, RitualConfig]] = {r.name: r for r in RITUALS}


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


class RitualScheduler:
    """Manages daily persona rituals using APScheduler 3.x AsyncIOScheduler.

    Usage::

        scheduler = RitualScheduler()
        scheduler.setup(callback=my_ritual_handler)
        await scheduler.start()
        # ... application runs ...
        await scheduler.stop()
    """

    def __init__(self, timezone: str = TZ_JAKARTA) -> None:
        self.timezone: str = timezone
        # Runtime type is AsyncIOScheduler | None; typed as object to avoid
        # module-level import dependency on APScheduler (lazy-imported).
        self.scheduler: object | None = None
        self._callback: Callable[[str], Awaitable[RitualResult]] | None = None
        self._last_results: dict[str, RitualResult] = {}
        self._tz: ZoneInfo = ZoneInfo(timezone)

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _get_scheduler_running(self) -> bool:
        """Check whether the stored scheduler is running (attribute guard).

        Uses ``getattr`` to avoid type-level dependency on AsyncIOScheduler.
        """
        if self.scheduler is None:
            return False
        return bool(getattr(self.scheduler, "running", False))

    def setup(
        self,
        callback: Callable[[str], Awaitable[RitualResult]] | None = None,
    ) -> object:
        """Create and configure APScheduler with all 5 ritual cron jobs.

        .. deprecated:: Phase 5
            APScheduler removed from active production path. This method
            lazy-imports ``apscheduler`` at call time.

        Args:
            callback: Async callable invoked when a ritual fires. Receives
                the ritual name as its sole argument and must return a
                ``RitualResult``. If ``None``, the built-in
                :meth:`execute_ritual` is used.

        Returns:
            The configured (but not yet started) ``AsyncIOScheduler``.

        Raises:
            RitualSchedulerError: If called when a scheduler is already active.
        """
        # Dynamic import — apscheduler not required at module load time.
        # Uses importlib so static analysis (basedpyright) never sees the path.
        aps_mod = importlib.import_module("apscheduler.schedulers.asyncio")
        AsyncIOScheduler = aps_mod.AsyncIOScheduler
        cron_mod = importlib.import_module("apscheduler.triggers.cron")
        CronTrigger = cron_mod.CronTrigger

        if self._get_scheduler_running():
            msg = "Scheduler already running; call stop() before re-setup."
            raise RitualSchedulerError(msg)

        self._callback = callback
        sched = AsyncIOScheduler(timezone=self.timezone)

        for ritual in RITUALS:
            job_id = f"ritual_{ritual.name}"
            trigger = CronTrigger(
                hour=ritual.hour,
                minute=ritual.minute,
                timezone=self.timezone,
            )
            sched.add_job(
                self._job_wrapper,
                trigger=trigger,
                id=job_id,
                name=f"{ritual.name.capitalize()} Ritual",
                args=[ritual.name],
                replace_existing=True,
            )
            logger.info(
                "ritual_job_registered",
                ritual=ritual.name,
                hour=ritual.hour,
                minute=ritual.minute,
                job_id=job_id,
            )

        self.scheduler = sched
        return sched

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the scheduler.

        Raises:
            RitualSchedulerError: If :meth:`setup` has not been called.
        """
        if self.scheduler is None:
            msg = "Scheduler not initialised; call setup() first."
            raise RitualSchedulerError(msg)
        start_method = getattr(self.scheduler, "start", None)
        if start_method is not None:
            start_method()
        logger.info("ritual_scheduler_started", timezone=self.timezone)

    async def stop(self) -> None:
        """Shutdown the scheduler gracefully.

        APScheduler 3.x ``AsyncIOScheduler.shutdown()`` schedules the actual
        shutdown via ``call_soon_threadsafe`` on the event loop. We yield
        control briefly to let the event loop process it.
        """
        running = self._get_scheduler_running()
        if running:
            shutdown = getattr(self.scheduler, "shutdown", None)
            if shutdown is not None:
                shutdown(wait=False)
            # Yield to event loop so @run_in_event_loop decorator executes
            await asyncio.sleep(0)
            logger.info("ritual_scheduler_stopped")

    # ------------------------------------------------------------------
    # DND
    # ------------------------------------------------------------------

    def is_dnd(self, now: datetime | None = None) -> bool:
        """Check if *now* falls within the DND window (00:00–07:00 WIB).

        Args:
            now: The datetime to evaluate. Defaults to the current time in
                the scheduler's timezone. Both naive and aware datetimes are
                accepted; naive datetimes are treated as already in the
                scheduler's timezone.

        Returns:
            ``True`` when the hour is in ``[DND_START_HOUR, DND_END_HOUR)``.
        """
        if now is None:
            now = datetime.now(self._tz)
        elif now.tzinfo is not None:
            now = now.astimezone(self._tz)

        return DND_START_HOUR <= now.hour < DND_END_HOUR

    # ------------------------------------------------------------------
    # Job introspection
    # ------------------------------------------------------------------

    def get_scheduled_jobs(self) -> list[dict[str, object]]:
        """Return metadata dicts for all scheduled ritual jobs.

        Each dict contains ``id``, ``name``, ``trigger``, and ``next_run_time``.
        ``next_run_time`` is ``None`` when the scheduler has not been started
        (jobs are pending).
        """
        if self.scheduler is None:
            return []

        get_jobs = getattr(self.scheduler, "get_jobs", None)
        if get_jobs is None:
            return []

        jobs: list[dict[str, object]] = []
        for job in get_jobs():
            jobs.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "trigger": str(job.trigger),
                    "next_run_time": getattr(job, "next_run_time", None),
                }
            )
        return jobs

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute_ritual(self, ritual_name: str) -> RitualResult:
        """Execute a single ritual by name.

        Respects DND: if the current time is within the DND window and the
        ritual does not have ``dnd_bypass=True``, returns a skipped result
        rather than firing the callback.

        Args:
            ritual_name: One of the five registered ritual names.

        Returns:
            A :class:`RitualResult` describing the outcome.

        Raises:
            RitualExecutionError: If *ritual_name* is not registered.
        """
        config = _RITUAL_MAP.get(ritual_name)
        if config is None:
            msg = f"Unknown ritual: {ritual_name!r}. Known: {list(_RITUAL_MAP)}"
            raise RitualExecutionError(msg)

        now = datetime.now(self._tz)

        # DND gate
        if self.is_dnd(now) and not config.dnd_bypass:
            logger.info("ritual_skipped_dnd", ritual=ritual_name, hour=now.hour)
            result = RitualResult(
                name=ritual_name,
                executed_at=now,
                message=config.default_message,
                success=False,
                error="Skipped: DND window active (00:00–07:00 WIB).",
            )
            self._last_results[ritual_name] = result
            return result

        # Execute via callback or default
        try:
            if self._callback is not None:
                result = await self._callback(ritual_name)
            else:
                result = await self._default_execute(ritual_name)
        except RitualSchedulerError:
            raise
        except Exception as exc:
            logger.error(
                "ritual_execution_failed",
                ritual=ritual_name,
                error=str(exc),
            )
            result = RitualResult(
                name=ritual_name,
                executed_at=now,
                message=config.default_message,
                success=False,
                error=f"Execution failed: {exc}",
            )

        self._last_results[ritual_name] = result
        logger.info("ritual_executed", ritual=ritual_name, success=result.success)
        return result

    def get_last_result(self, ritual_name: str) -> RitualResult | None:
        """Get the last execution result for *ritual_name*, or ``None``."""
        return self._last_results.get(ritual_name)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _default_execute(self, ritual_name: str) -> RitualResult:
        """Default ritual execution — logs and returns a success result."""
        config = _RITUAL_MAP[ritual_name]
        now = datetime.now(self._tz)
        logger.info(
            "ritual_default_execute",
            ritual=ritual_name,
            message=config.default_message,
        )
        return RitualResult(
            name=ritual_name,
            executed_at=now,
            message=config.default_message,
            success=True,
        )

    async def _job_wrapper(self, ritual_name: str) -> None:
        """APScheduler job wrapper — calls :meth:`execute_ritual`."""
        try:
            await self.execute_ritual(ritual_name)
        except RitualSchedulerError:
            logger.error("ritual_job_error", ritual=ritual_name)
