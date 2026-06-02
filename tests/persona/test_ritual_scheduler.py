"""P4-008: Daily ritual scheduler — deterministic unit tests.

Tests cover:
- RITUALS config has exactly 5 entries with correct hour/minute values.
- setup() creates AsyncIOScheduler with 5 registered cron jobs.
- is_dnd() returns True for 00:00–06:59 WIB, False for 07:00–23:59 WIB.
- execute_ritual respects DND (returns skipped result during DND).
- execute_ritual fires correctly outside DND via mocked callback.
- get_scheduled_jobs returns 5 job info dicts.
- start/stop lifecycle.
- RitualConfig is frozen (immutable).

All tests use synthetic data — no real cron fires, no Discord, no network.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from typing import Final
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.persona.ritual_scheduler import (
    DND_END_HOUR,
    DND_START_HOUR,
    RITUALS,
    RitualConfig,
    RitualExecutionError,
    RitualResult,
    RitualScheduler,
    RitualSchedulerError,
    TZ_JAKARTA,
    _RITUAL_MAP,
)

TZ: Final[ZoneInfo] = ZoneInfo(TZ_JAKARTA)

# ---------------------------------------------------------------------------
# Expected ritual definitions
# ---------------------------------------------------------------------------

EXPECTED_RITUALS: Final[list[dict[str, object]]] = [
    {"name": "morning", "hour": 7, "minute": 0, "mood_aware": True, "dnd_bypass": False},
    {"name": "midday", "hour": 12, "minute": 0, "mood_aware": True, "dnd_bypass": False},
    {"name": "afternoon", "hour": 17, "minute": 0, "mood_aware": True, "dnd_bypass": False},
    {"name": "evening", "hour": 21, "minute": 0, "mood_aware": True, "dnd_bypass": False},
    {"name": "midnight", "hour": 0, "minute": 0, "mood_aware": False, "dnd_bypass": False},
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def scheduler() -> RitualScheduler:
    """Create a fresh RitualScheduler (not yet started)."""
    return RitualScheduler()


@pytest.fixture
def configured_scheduler(scheduler: RitualScheduler) -> RitualScheduler:
    """Create a RitualScheduler with setup() called but not started."""
    scheduler.setup()
    return scheduler


@pytest.fixture
def mock_callback() -> AsyncMock:
    """AsyncMock that returns a successful RitualResult for any ritual name."""

    async def _callback(name: str) -> RitualResult:
        return RitualResult(
            name=name,
            executed_at=datetime.now(TZ),
            message=f"Mock message for {name}",
            success=True,
        )

    return AsyncMock(side_effect=_callback)


@pytest.fixture
def scheduler_with_callback(
    scheduler: RitualScheduler,
    mock_callback: AsyncMock,
) -> RitualScheduler:
    """Create a RitualScheduler with a mocked callback."""
    scheduler.setup(callback=mock_callback)
    return scheduler


# ---------------------------------------------------------------------------
# Tests — RITUALS configuration
# ---------------------------------------------------------------------------


class TestRitualsConfig:
    """Verify the static RITUALS configuration."""

    def test_rituals_count(self) -> None:
        """RITUALS must contain exactly 5 entries."""
        assert len(RITUALS) == 5

    def test_ritual_names(self) -> None:
        """Ritual names match expected set."""
        names = {r.name for r in RITUALS}
        assert names == {"morning", "midday", "afternoon", "evening", "midnight"}

    @pytest.mark.parametrize(
        ("expected",),
        [(e,) for e in EXPECTED_RITUALS],
        ids=[e["name"] for e in EXPECTED_RITUALS],  # type: ignore[misc]
    )
    def test_ritual_hour_minute(self, expected: dict[str, object]) -> None:
        """Each ritual has the correct hour and minute."""
        ritual = _RITUAL_MAP[expected["name"]]  # type: ignore[index]
        assert ritual.hour == expected["hour"]
        assert ritual.minute == expected["minute"]

    @pytest.mark.parametrize(
        ("expected",),
        [(e,) for e in EXPECTED_RITUALS],
        ids=[e["name"] for e in EXPECTED_RITUALS],  # type: ignore[misc]
    )
    def test_ritual_flags(self, expected: dict[str, object]) -> None:
        """Each ritual has correct mood_aware and dnd_bypass flags."""
        ritual = _RITUAL_MAP[expected["name"]]  # type: ignore[index]
        assert ritual.mood_aware == expected["mood_aware"]
        assert ritual.dnd_bypass == expected["dnd_bypass"]

    def test_ritual_config_frozen(self) -> None:
        """RitualConfig is frozen — attribute assignment raises FrozenInstanceError."""
        config = RITUALS[0]
        with pytest.raises(FrozenInstanceError):
            config.name = "changed"  # type: ignore[misc]

    def test_ritual_result_frozen(self) -> None:
        """RitualResult is frozen — attribute assignment raises FrozenInstanceError."""
        result = RitualResult(
            name="test",
            executed_at=datetime.now(TZ),
            message="msg",
            success=True,
        )
        with pytest.raises(FrozenInstanceError):
            result.success = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Tests — setup()
# ---------------------------------------------------------------------------


class TestSetup:
    """Verify scheduler setup behaviour."""

    def test_setup_returns_asyncio_scheduler(self, scheduler: RitualScheduler) -> None:
        """setup() returns an AsyncIOScheduler instance."""
        result = scheduler.setup()
        assert isinstance(result, AsyncIOScheduler)

    def test_setup_registers_five_jobs(self, configured_scheduler: RitualScheduler) -> None:
        """setup() registers exactly 5 cron jobs."""
        assert configured_scheduler.scheduler is not None
        jobs = configured_scheduler.scheduler.get_jobs()
        assert len(jobs) == 5

    def test_setup_job_ids(self, configured_scheduler: RitualScheduler) -> None:
        """Each registered job has the expected ``ritual_<name>`` id."""
        assert configured_scheduler.scheduler is not None
        job_ids = {job.id for job in configured_scheduler.scheduler.get_jobs()}
        expected_ids = {f"ritual_{r.name}" for r in RITUALS}
        assert job_ids == expected_ids

    @pytest.mark.asyncio
    async def test_setup_duplicate_raises(
        self, configured_scheduler: RitualScheduler
    ) -> None:
        """Calling setup() on a running scheduler raises RitualSchedulerError."""
        # Start it so .running is True
        configured_scheduler.scheduler.start()  # type: ignore[union-attr]
        try:
            with pytest.raises(RitualSchedulerError, match="already running"):
                configured_scheduler.setup()
        finally:
            configured_scheduler.scheduler.shutdown(wait=False)  # type: ignore[union-attr]
            await asyncio.sleep(0)  # let event loop process shutdown


# ---------------------------------------------------------------------------
# Tests — is_dnd()
# ---------------------------------------------------------------------------


class TestIsDnd:
    """Verify DND window detection."""

    @pytest.mark.parametrize(
        "hour",
        [0, 1, 2, 3, 4, 5, 6],
        ids=[f"hour_{h:02d}" for h in range(7)],
    )
    def test_dnd_true(self, scheduler: RitualScheduler, hour: int) -> None:
        """is_dnd() returns True for hours 00–06 WIB."""
        now = datetime(2026, 6, 2, hour, 30, 0, tzinfo=TZ)
        assert scheduler.is_dnd(now) is True

    @pytest.mark.parametrize(
        "hour",
        [7, 8, 10, 12, 17, 21, 23],
        ids=[f"hour_{h:02d}" for h in [7, 8, 10, 12, 17, 21, 23]],
    )
    def test_dnd_false(self, scheduler: RitualScheduler, hour: int) -> None:
        """is_dnd() returns False for hours 07–23 WIB."""
        now = datetime(2026, 6, 2, hour, 0, 0, tzinfo=TZ)
        assert scheduler.is_dnd(now) is False

    def test_dnd_boundary_start(self, scheduler: RitualScheduler) -> None:
        """Midnight (00:00) is inside DND."""
        now = datetime(2026, 6, 2, 0, 0, 0, tzinfo=TZ)
        assert scheduler.is_dnd(now) is True

    def test_dnd_boundary_end(self, scheduler: RitualScheduler) -> None:
        """07:00 WIB is outside DND (end is exclusive)."""
        now = datetime(2026, 6, 2, 7, 0, 0, tzinfo=TZ)
        assert scheduler.is_dnd(now) is False

    def test_dnd_utc_conversion(self, scheduler: RitualScheduler) -> None:
        """is_dnd() correctly converts UTC-aware datetime to WIB."""
        # 23:00 UTC = 06:00 WIB (next day) → inside DND
        utc_time = datetime(2026, 6, 1, 23, 0, 0, tzinfo=timezone.utc)
        assert scheduler.is_dnd(utc_time) is True

        # 00:00 UTC = 07:00 WIB → outside DND
        utc_time_outside = datetime(2026, 6, 2, 0, 0, 0, tzinfo=timezone.utc)
        assert scheduler.is_dnd(utc_time_outside) is False


# ---------------------------------------------------------------------------
# Tests — execute_ritual()
# ---------------------------------------------------------------------------


class TestExecuteRitual:
    """Verify ritual execution logic."""

    @pytest.mark.asyncio
    async def test_execute_outside_dnd(
        self,
        scheduler_with_callback: RitualScheduler,
        mock_callback: AsyncMock,
    ) -> None:
        """Ritual fires via callback when outside DND window."""
        # Patch is_dnd to always return False (simulate daytime)
        scheduler_with_callback.is_dnd = lambda now=None: False  # type: ignore[assignment]

        result = await scheduler_with_callback.execute_ritual("morning")
        assert result.success is True
        assert result.name == "morning"
        assert result.error is None
        mock_callback.assert_called_once_with("morning")

    @pytest.mark.asyncio
    async def test_execute_during_dnd_skipped(
        self,
        scheduler_with_callback: RitualScheduler,
        mock_callback: AsyncMock,
    ) -> None:
        """Ritual is skipped during DND (callback not invoked)."""
        # Patch is_dnd to always return True (simulate nighttime)
        scheduler_with_callback.is_dnd = lambda now=None: True  # type: ignore[assignment]

        result = await scheduler_with_callback.execute_ritual("morning")
        assert result.success is False
        assert result.error is not None
        assert "DND" in result.error
        mock_callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_unknown_ritual(
        self,
        scheduler_with_callback: RitualScheduler,
    ) -> None:
        """Unknown ritual name raises RitualExecutionError."""
        with pytest.raises(RitualExecutionError, match="Unknown ritual"):
            await scheduler_with_callback.execute_ritual("nonexistent")

    @pytest.mark.asyncio
    async def test_execute_default_callback(
        self,
        configured_scheduler: RitualScheduler,
    ) -> None:
        """Without explicit callback, default handler returns success."""
        configured_scheduler.is_dnd = lambda now=None: False  # type: ignore[assignment]

        result = await configured_scheduler.execute_ritual("evening")
        assert result.success is True
        assert result.name == "evening"
        assert result.message == RITUALS[3].default_message  # evening is index 3

    @pytest.mark.asyncio
    async def test_execute_callback_error(
        self,
        scheduler: RitualScheduler,
    ) -> None:
        """When callback raises, result has success=False with error message."""
        failing_callback: AsyncMock = AsyncMock(side_effect=RuntimeError("boom"))
        scheduler.setup(callback=failing_callback)
        scheduler.is_dnd = lambda now=None: False  # type: ignore[assignment]

        result = await scheduler.execute_ritual("midday")
        assert result.success is False
        assert result.error is not None
        assert "boom" in result.error

    @pytest.mark.asyncio
    async def test_get_last_result(
        self,
        scheduler_with_callback: RitualScheduler,
    ) -> None:
        """get_last_result returns the most recent execution result."""
        scheduler_with_callback.is_dnd = lambda now=None: False  # type: ignore[assignment]

        assert scheduler_with_callback.get_last_result("morning") is None

        await scheduler_with_callback.execute_ritual("morning")
        last = scheduler_with_callback.get_last_result("morning")
        assert last is not None
        assert last.name == "morning"
        assert last.success is True


# ---------------------------------------------------------------------------
# Tests — get_scheduled_jobs()
# ---------------------------------------------------------------------------


class TestGetScheduledJobs:
    """Verify job introspection."""

    def test_returns_five_jobs(self, configured_scheduler: RitualScheduler) -> None:
        """get_scheduled_jobs returns exactly 5 job dicts."""
        jobs = configured_scheduler.get_scheduled_jobs()
        assert len(jobs) == 5

    def test_job_dict_keys(self, configured_scheduler: RitualScheduler) -> None:
        """Each job dict has the expected keys."""
        jobs = configured_scheduler.get_scheduled_jobs()
        for job in jobs:
            assert "id" in job
            assert "name" in job
            assert "trigger" in job
            assert "next_run_time" in job

    def test_unconfigured_returns_empty(self, scheduler: RitualScheduler) -> None:
        """get_scheduled_jobs on unconfigured scheduler returns empty list."""
        assert scheduler.get_scheduled_jobs() == []


# ---------------------------------------------------------------------------
# Tests — start / stop lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    """Verify scheduler start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_without_setup_raises(self, scheduler: RitualScheduler) -> None:
        """start() without setup() raises RitualSchedulerError."""
        with pytest.raises(RitualSchedulerError, match="not initialised"):
            await scheduler.start()

    @pytest.mark.asyncio
    async def test_start_stop(self, configured_scheduler: RitualScheduler) -> None:
        """Scheduler starts and stops cleanly."""
        await configured_scheduler.start()
        assert configured_scheduler.scheduler is not None
        assert configured_scheduler.scheduler.running is True

        await configured_scheduler.stop()
        assert configured_scheduler.scheduler.running is False

    @pytest.mark.asyncio
    async def test_stop_without_start(self, configured_scheduler: RitualScheduler) -> None:
        """stop() on a non-running scheduler does not raise."""
        # Scheduler configured but never started — stop should be safe
        await configured_scheduler.stop()

    @pytest.mark.asyncio
    async def test_stop_unconfigured(self, scheduler: RitualScheduler) -> None:
        """stop() on unconfigured scheduler does not raise."""
        await scheduler.stop()
