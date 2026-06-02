"""P4-007: Streak Tracking — comprehensive tests.

Tests cover:
- increment(): basic, multiple, return value, last_increment tracking
- reset(): basic, return value, state clearing
- get_count(): initial, after operations
- get_milestone(): below all, at each threshold, between thresholds, above all
- is_milestone_reached(): valid thresholds, invalid threshold raises
- get_display_text(): all display states
- Constants: MILESTONE_THRESHOLDS, MILESTONE_LABELS, STREAK_STATE_KEY
- Error hierarchy: StreakError, StreakPersistenceError
- Async persistence: save() and load() with mock sessions
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pytest

from persona.streak_tracker import (
    MILESTONE_LABELS,
    MILESTONE_THRESHOLDS,
    STREAK_STATE_KEY,
    StreakError,
    StreakPersistenceError,
    StreakTracker,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

UTC = timezone.utc
NOW = datetime(2026, 6, 2, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Fake DB infrastructure for async persistence tests
# ---------------------------------------------------------------------------


@dataclass
class FakePersonaState:
    """Mimics PersonaState ORM model for testing."""

    state_key: str
    state_value: dict[str, Any]
    updated_at: datetime = field(default_factory=lambda: NOW)
    updated_by: str = "test"
    id: Any = None


class FakeResult:
    """Mimics SQLAlchemy Result object."""

    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def scalar_one_or_none(self) -> Any | None:
        return self._rows[0] if self._rows else None


class FakeAsyncSession:
    """Deterministic fake AsyncSession for streak persistence tests."""

    def __init__(self, result_rows: list[Any] | None = None) -> None:
        self._result = FakeResult(result_rows or [])
        self.added: list[Any] = []
        self.flushed: int = 0

    async def execute(self, stmt: Any) -> FakeResult:
        return self._result

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        self.flushed += 1


class FailingAsyncSession:
    """Fake session that raises to simulate DB errors."""

    def __init__(self, fail_on: str = "execute") -> None:
        self._fail_on = fail_on
        self.added: list[Any] = []
        self.flushed: int = 0

    async def execute(self, stmt: Any) -> FakeResult:
        if self._fail_on == "execute":
            raise RuntimeError("simulated DB failure")
        return FakeResult([])

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        if self._fail_on == "flush":
            raise RuntimeError("simulated flush failure")
        self.flushed += 1


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tracker() -> StreakTracker:
    """Return a fresh StreakTracker with zero count."""
    return StreakTracker()


# ---------------------------------------------------------------------------
# Tests: increment
# ---------------------------------------------------------------------------


class TestIncrement:
    """Tests for StreakTracker.increment()."""

    def test_returns_one_on_first_increment(self, tracker: StreakTracker) -> None:
        result = tracker.increment()
        assert result == 1

    def test_returns_two_on_second_increment(self, tracker: StreakTracker) -> None:
        tracker.increment()
        result = tracker.increment()
        assert result == 2

    def test_increments_count_by_one(self, tracker: StreakTracker) -> None:
        tracker.increment()
        tracker.increment()
        tracker.increment()
        assert tracker.get_count() == 3

    def test_sets_last_increment_timestamp(self, tracker: StreakTracker) -> None:
        tracker.increment()
        assert tracker._last_increment is not None
        assert tracker._last_increment.tzinfo is not None

    def test_logs_milestone_on_threshold(self, tracker: StreakTracker) -> None:
        """Reaching a milestone threshold should not raise."""
        for _ in range(7):
            tracker.increment()
        assert tracker.get_count() == 7
        assert tracker._highest_milestone_reached == 7


# ---------------------------------------------------------------------------
# Tests: reset
# ---------------------------------------------------------------------------


class TestReset:
    """Tests for StreakTracker.reset()."""

    def test_returns_previous_count(self, tracker: StreakTracker) -> None:
        tracker.increment()
        tracker.increment()
        tracker.increment()
        previous = tracker.reset()
        assert previous == 3

    def test_sets_count_to_zero(self, tracker: StreakTracker) -> None:
        tracker.increment()
        tracker.increment()
        tracker.reset()
        assert tracker.get_count() == 0

    def test_clears_last_increment(self, tracker: StreakTracker) -> None:
        tracker.increment()
        tracker.reset()
        assert tracker._last_increment is None

    def test_clears_highest_milestone(self, tracker: StreakTracker) -> None:
        for _ in range(7):
            tracker.increment()
        assert tracker._highest_milestone_reached == 7
        tracker.reset()
        assert tracker._highest_milestone_reached == 0

    def test_reset_from_zero_returns_zero(self, tracker: StreakTracker) -> None:
        previous = tracker.reset()
        assert previous == 0


# ---------------------------------------------------------------------------
# Tests: get_count
# ---------------------------------------------------------------------------


class TestGetCount:
    """Tests for StreakTracker.get_count()."""

    def test_initial_count_is_zero(self, tracker: StreakTracker) -> None:
        assert tracker.get_count() == 0

    def test_count_after_increments(self, tracker: StreakTracker) -> None:
        for _ in range(10):
            tracker.increment()
        assert tracker.get_count() == 10

    def test_count_after_reset(self, tracker: StreakTracker) -> None:
        for _ in range(5):
            tracker.increment()
        tracker.reset()
        assert tracker.get_count() == 0

    def test_count_resumes_after_reset(self, tracker: StreakTracker) -> None:
        for _ in range(5):
            tracker.increment()
        tracker.reset()
        tracker.increment()
        tracker.increment()
        assert tracker.get_count() == 2


# ---------------------------------------------------------------------------
# Tests: get_milestone
# ---------------------------------------------------------------------------


class TestGetMilestone:
    """Tests for StreakTracker.get_milestone()."""

    def test_none_when_below_all_thresholds(self, tracker: StreakTracker) -> None:
        for _ in range(6):
            tracker.increment()
        assert tracker.get_milestone() is None

    def test_week_at_seven(self, tracker: StreakTracker) -> None:
        for _ in range(7):
            tracker.increment()
        assert tracker.get_milestone() == 7

    def test_fortnight_at_fourteen(self, tracker: StreakTracker) -> None:
        for _ in range(14):
            tracker.increment()
        assert tracker.get_milestone() == 14

    def test_month_at_thirty(self, tracker: StreakTracker) -> None:
        for _ in range(30):
            tracker.increment()
        assert tracker.get_milestone() == 30

    def test_quarter_at_ninety(self, tracker: StreakTracker) -> None:
        for _ in range(90):
            tracker.increment()
        assert tracker.get_milestone() == 90

    def test_year_at_365(self, tracker: StreakTracker) -> None:
        for _ in range(365):
            tracker.increment()
        assert tracker.get_milestone() == 365

    def test_between_milestones_returns_lower(self, tracker: StreakTracker) -> None:
        """20 days is between fortnight (14) and month (30) → returns 14."""
        for _ in range(20):
            tracker.increment()
        assert tracker.get_milestone() == 14

    def test_above_all_returns_year(self, tracker: StreakTracker) -> None:
        for _ in range(400):
            tracker.increment()
        assert tracker.get_milestone() == 365

    def test_none_at_zero(self, tracker: StreakTracker) -> None:
        assert tracker.get_milestone() is None


# ---------------------------------------------------------------------------
# Tests: is_milestone_reached
# ---------------------------------------------------------------------------


class TestIsMilestoneReached:
    """Tests for StreakTracker.is_milestone_reached()."""

    def test_week_not_reached_below_7(self, tracker: StreakTracker) -> None:
        for _ in range(6):
            tracker.increment()
        assert tracker.is_milestone_reached(7) is False

    def test_week_reached_at_7(self, tracker: StreakTracker) -> None:
        for _ in range(7):
            tracker.increment()
        assert tracker.is_milestone_reached(7) is True

    def test_week_reached_above_7(self, tracker: StreakTracker) -> None:
        for _ in range(10):
            tracker.increment()
        assert tracker.is_milestone_reached(7) is True

    def test_month_not_reached_at_29(self, tracker: StreakTracker) -> None:
        for _ in range(29):
            tracker.increment()
        assert tracker.is_milestone_reached(30) is False

    def test_invalid_threshold_raises(self, tracker: StreakTracker) -> None:
        with pytest.raises(StreakError, match="Invalid milestone threshold"):
            tracker.is_milestone_reached(5)

    def test_invalid_threshold_zero_raises(self, tracker: StreakTracker) -> None:
        with pytest.raises(StreakError, match="Invalid milestone threshold"):
            tracker.is_milestone_reached(0)

    def test_invalid_threshold_negative_raises(self, tracker: StreakTracker) -> None:
        with pytest.raises(StreakError, match="Invalid milestone threshold"):
            tracker.is_milestone_reached(-1)

    def test_all_valid_thresholds_accepted(self, tracker: StreakTracker) -> None:
        """All defined thresholds should be accepted without raising."""
        for threshold in MILESTONE_THRESHOLDS:
            result = tracker.is_milestone_reached(threshold)
            assert result is False  # count is 0, so none reached


# ---------------------------------------------------------------------------
# Tests: get_display_text
# ---------------------------------------------------------------------------


class TestGetDisplayText:
    """Tests for StreakTracker.get_display_text()."""

    def test_zero_days(self, tracker: StreakTracker) -> None:
        text = tracker.get_display_text()
        assert text == "Streak: 0 days — no streak active."

    def test_one_day_singular(self, tracker: StreakTracker) -> None:
        tracker.increment()
        text = tracker.get_display_text()
        assert "1 day" in text
        assert "6 days to week milestone" in text

    def test_three_days(self, tracker: StreakTracker) -> None:
        for _ in range(3):
            tracker.increment()
        text = tracker.get_display_text()
        assert "3 days" in text
        assert "4 days to week milestone" in text

    def test_at_week_milestone(self, tracker: StreakTracker) -> None:
        for _ in range(7):
            tracker.increment()
        text = tracker.get_display_text()
        assert "7 days" in text
        assert "week milestone reached!" in text

    def test_between_week_and_fortnight(self, tracker: StreakTracker) -> None:
        for _ in range(10):
            tracker.increment()
        text = tracker.get_display_text()
        assert "10 days" in text
        assert "week milestone reached!" in text

    def test_at_fortnight_milestone(self, tracker: StreakTracker) -> None:
        for _ in range(14):
            tracker.increment()
        text = tracker.get_display_text()
        assert "14 days" in text
        assert "fortnight milestone reached!" in text

    def test_at_month_milestone(self, tracker: StreakTracker) -> None:
        for _ in range(30):
            tracker.increment()
        text = tracker.get_display_text()
        assert "30 days" in text
        assert "month milestone reached!" in text

    def test_at_quarter_milestone(self, tracker: StreakTracker) -> None:
        for _ in range(90):
            tracker.increment()
        text = tracker.get_display_text()
        assert "90 days" in text
        assert "quarter milestone reached!" in text

    def test_at_year_milestone(self, tracker: StreakTracker) -> None:
        for _ in range(365):
            tracker.increment()
        text = tracker.get_display_text()
        assert "365 days" in text
        assert "year milestone reached!" in text

    def test_above_all_milestones(self, tracker: StreakTracker) -> None:
        for _ in range(400):
            tracker.increment()
        text = tracker.get_display_text()
        assert "400 days" in text
        assert "year milestone reached!" in text

    def test_after_reset_shows_zero(self, tracker: StreakTracker) -> None:
        for _ in range(10):
            tracker.increment()
        tracker.reset()
        text = tracker.get_display_text()
        assert text == "Streak: 0 days — no streak active."


# ---------------------------------------------------------------------------
# Tests: Constants
# ---------------------------------------------------------------------------


class TestConstants:
    """Tests for module-level constants."""

    def test_milestone_threshold_values(self) -> None:
        assert MILESTONE_THRESHOLDS == [7, 14, 30, 90, 365]

    def test_milestone_labels_keys_match_thresholds(self) -> None:
        assert set(MILESTONE_LABELS.keys()) == set(MILESTONE_THRESHOLDS)

    def test_milestone_label_values(self) -> None:
        assert MILESTONE_LABELS[7] == "week"
        assert MILESTONE_LABELS[14] == "fortnight"
        assert MILESTONE_LABELS[30] == "month"
        assert MILESTONE_LABELS[90] == "quarter"
        assert MILESTONE_LABELS[365] == "year"

    def test_streak_state_key(self) -> None:
        assert STREAK_STATE_KEY == "streak_count"


# ---------------------------------------------------------------------------
# Tests: Error hierarchy
# ---------------------------------------------------------------------------


class TestErrorHierarchy:
    """Tests for exception class hierarchy."""

    def test_streak_error_is_exception(self) -> None:
        assert issubclass(StreakError, Exception)

    def test_persistence_error_is_streak_error(self) -> None:
        assert issubclass(StreakPersistenceError, StreakError)

    def test_persistence_error_is_exception(self) -> None:
        assert issubclass(StreakPersistenceError, Exception)

    def test_streak_error_message(self) -> None:
        err = StreakError("test message")
        assert str(err) == "test message"

    def test_persistence_error_cause(self) -> None:
        cause = RuntimeError("db down")
        err = StreakPersistenceError("failed")
        err.__cause__ = cause
        assert err.__cause__ is cause


# ---------------------------------------------------------------------------
# Tests: Async persistence — save
# ---------------------------------------------------------------------------


class TestSave:
    """Tests for StreakTracker.save() async persistence."""

    @pytest.mark.asyncio
    async def test_save_inserts_when_no_existing_row(self) -> None:
        """When no streak_count row exists, a new row is added."""
        session = FakeAsyncSession(result_rows=[])
        tracker = StreakTracker()
        tracker.increment()

        await tracker.save(session)  # type: ignore[arg-type]

        assert len(session.added) == 1
        added = session.added[0]
        assert added.state_key == STREAK_STATE_KEY
        assert added.state_value["count"] == 1
        assert added.updated_by == "streak_tracker"
        assert session.flushed == 1

    @pytest.mark.asyncio
    async def test_save_updates_existing_row(self) -> None:
        """When streak_count row exists, it is updated in-place."""
        existing = FakePersonaState(
            state_key="streak_count",
            state_value={"count": 3, "last_updated": None, "highest_milestone": 0},
            updated_at=NOW,
            updated_by="streak_tracker",
        )
        session = FakeAsyncSession(result_rows=[existing])
        tracker = StreakTracker()
        tracker.increment()

        await tracker.save(session, updated_by="test_agent")  # type: ignore[arg-type]

        assert len(session.added) == 0
        assert existing.state_value["count"] == 1
        assert existing.updated_by == "test_agent"
        assert session.flushed == 1

    @pytest.mark.asyncio
    async def test_save_wraps_db_error(self) -> None:
        """DB errors during save are wrapped in StreakPersistenceError."""
        session = FailingAsyncSession(fail_on="execute")
        tracker = StreakTracker()

        with pytest.raises(StreakPersistenceError, match="Failed to persist"):
            await tracker.save(session)  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_save_wraps_flush_error(self) -> None:
        """Flush errors during save are wrapped in StreakPersistenceError."""
        session = FailingAsyncSession(fail_on="flush")
        tracker = StreakTracker()

        with pytest.raises(StreakPersistenceError, match="Failed to persist"):
            await tracker.save(session)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tests: Async persistence — load
# ---------------------------------------------------------------------------


class TestLoad:
    """Tests for StreakTracker.load() async persistence."""

    @pytest.mark.asyncio
    async def test_load_no_record_keeps_default(self) -> None:
        """When no record exists, streak remains at default (0)."""
        session = FakeAsyncSession(result_rows=[])
        tracker = StreakTracker()

        await tracker.load(session)  # type: ignore[arg-type]

        assert tracker.get_count() == 0

    @pytest.mark.asyncio
    async def test_load_restores_count(self) -> None:
        """Existing record restores the streak count."""
        row = FakePersonaState(
            state_key="streak_count",
            state_value={
                "count": 42,
                "last_updated": "2026-06-01T12:00:00+00:00",
                "highest_milestone": 30,
            },
        )
        session = FakeAsyncSession(result_rows=[row])
        tracker = StreakTracker()

        await tracker.load(session)  # type: ignore[arg-type]

        assert tracker.get_count() == 42
        assert tracker._highest_milestone_reached == 30
        assert tracker._last_increment is not None

    @pytest.mark.asyncio
    async def test_load_corrupted_data_resets(self) -> None:
        """Corrupted state_value resets streak to zero."""
        row = FakePersonaState(
            state_key="streak_count",
            state_value={"invalid_key": "no_count_here"},
        )
        session = FakeAsyncSession(result_rows=[row])
        tracker = StreakTracker()

        await tracker.load(session)  # type: ignore[arg-type]

        assert tracker.get_count() == 0

    @pytest.mark.asyncio
    async def test_load_negative_count_clamps_to_zero(self) -> None:
        """Negative stored count is clamped to zero."""
        row = FakePersonaState(
            state_key="streak_count",
            state_value={"count": -5, "last_updated": None, "highest_milestone": 0},
        )
        session = FakeAsyncSession(result_rows=[row])
        tracker = StreakTracker()

        await tracker.load(session)  # type: ignore[arg-type]

        assert tracker.get_count() == 0

    @pytest.mark.asyncio
    async def test_load_wraps_db_error(self) -> None:
        """DB errors during load are wrapped in StreakPersistenceError."""
        session = FailingAsyncSession(fail_on="execute")
        tracker = StreakTracker()

        with pytest.raises(StreakPersistenceError, match="Failed to load"):
            await tracker.load(session)  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_load_with_null_last_updated(self) -> None:
        """Null last_updated is handled gracefully."""
        row = FakePersonaState(
            state_key="streak_count",
            state_value={
                "count": 10,
                "last_updated": None,
                "highest_milestone": 7,
            },
        )
        session = FakeAsyncSession(result_rows=[row])
        tracker = StreakTracker()

        await tracker.load(session)  # type: ignore[arg-type]

        assert tracker.get_count() == 10
        assert tracker._last_increment is None
        assert tracker._highest_milestone_reached == 7


# ---------------------------------------------------------------------------
# Tests: Integration — full lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    """Integration tests for the streak tracker lifecycle."""

    def test_increment_to_milestone_then_reset(self) -> None:
        """Full lifecycle: build streak → hit milestone → punishment reset."""
        tracker = StreakTracker()

        # Build to 14 days
        for _ in range(14):
            tracker.increment()
        assert tracker.get_count() == 14
        assert tracker.get_milestone() == 14
        assert tracker.is_milestone_reached(7) is True
        assert tracker.is_milestone_reached(14) is True
        assert tracker.is_milestone_reached(30) is False
        assert "fortnight milestone reached!" in tracker.get_display_text()

        # Punishment resets
        previous = tracker.reset()
        assert previous == 14
        assert tracker.get_count() == 0
        assert tracker.get_milestone() is None
        assert "no streak active" in tracker.get_display_text()

        # Rebuild
        tracker.increment()
        assert tracker.get_count() == 1
        assert "6 days to week milestone" in tracker.get_display_text()

    def test_streak_persists_across_mood_changes(self) -> None:
        """Streak is NOT affected by mood changes (only punishment resets)."""
        tracker = StreakTracker()
        for _ in range(5):
            tracker.increment()

        # Simulate safe_mode/distress — streak should persist
        # (no method exists to reset for mood; only reset() does it)
        assert tracker.get_count() == 5

    def test_multiple_resets_and_rebuilds(self) -> None:
        """Multiple punishment-reset-rebuild cycles work correctly."""
        tracker = StreakTracker()

        for cycle in range(3):
            days = 3 + cycle * 2
            for _ in range(days):
                tracker.increment()
            assert tracker.get_count() == days
            previous = tracker.reset()
            assert previous == days
            assert tracker.get_count() == 0
