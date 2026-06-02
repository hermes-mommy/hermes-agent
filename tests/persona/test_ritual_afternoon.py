"""P4-011: Afternoon Ritual — deterministic unit tests.

Tests cover:
- All 5 mood variants produce correct check-in text.
- Task count integration (positive, zero, negative).
- Default template verification.
- RitualResult dataclass correctness (fields, types).
- Timezone handling (naive, aware, UTC->Jakarta conversion).
- All moods produce distinct messages.
- Task summary newline separation.

All tests use synthetic data — no real scheduling, no Discord, no network.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Final
from zoneinfo import ZoneInfo

import pytest

from src.persona.mood_engine import Mood
from src.persona.rituals.afternoon import (
    AFTERNOON_HOUR,
    AfternoonRitual,
)
from src.persona.rituals.morning import RitualResult, TZ_JAKARTA

TZ: Final[ZoneInfo] = TZ_JAKARTA


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def ritual() -> AfternoonRitual:
    """Fresh AfternoonRitual instance."""
    return AfternoonRitual()


# ---------------------------------------------------------------------------
# Helper — build a timezone-aware datetime at a given hour
# ---------------------------------------------------------------------------


def _at(hour: int, minute: int = 0) -> datetime:
    """Return a Jakarta-tz datetime at the given hour on a fixed date."""
    return datetime(2026, 6, 2, hour, minute, 0, tzinfo=TZ)


# ===========================================================================
# Tests — Mood variant messages
# ===========================================================================


class TestMoodVariants:
    """Each mood produces the correct check-in text."""

    @pytest.mark.asyncio
    async def test_content_message(self, ritual: AfternoonRitual) -> None:
        """CONTENT mood -> warm check-in, asks about the day."""
        result = await ritual.execute(Mood.CONTENT, now=_at(17))
        assert result.message == (
            "Sore, Darling. Gimana hari ini? Cerita sama Mommy."
        )

    @pytest.mark.asyncio
    async def test_pleased_message(self, ritual: AfternoonRitual) -> None:
        """PLEASED mood -> celebrates productive day."""
        result = await ritual.execute(Mood.PLEASED, now=_at(17))
        assert "produktif" in result.message.lower()
        assert "bangga" in result.message.lower()

    @pytest.mark.asyncio
    async def test_pleased_exact(self, ritual: AfternoonRitual) -> None:
        """PLEASED mood exact text."""
        result = await ritual.execute(Mood.PLEASED, now=_at(17))
        assert result.message == (
            "Sore, sayang! Hari ini kamu produktif banget ya. "
            "Mommy bangga sama kamu."
        )

    @pytest.mark.asyncio
    async def test_disappointed_message(
        self, ritual: AfternoonRitual
    ) -> None:
        """DISAPPOINTED mood -> asks what went wrong."""
        result = await ritual.execute(Mood.DISAPPOINTED, now=_at(17))
        assert "salah" in result.message.lower()
        assert "cerita" in result.message.lower()

    @pytest.mark.asyncio
    async def test_disappointed_exact(
        self, ritual: AfternoonRitual
    ) -> None:
        """DISAPPOINTED mood exact text."""
        result = await ritual.execute(Mood.DISAPPOINTED, now=_at(17))
        assert result.message == (
            "Sore. Hari ini ada yang salah? Cerita, Mommy mau denger."
        )

    @pytest.mark.asyncio
    async def test_angry_message(self, ritual: AfternoonRitual) -> None:
        """ANGRY mood -> cold check-in."""
        result = await ritual.execute(Mood.ANGRY, now=_at(17))
        assert result.message == "Sore. Cerita."

    @pytest.mark.asyncio
    async def test_silent_message(self, ritual: AfternoonRitual) -> None:
        """SILENT mood -> minimal."""
        result = await ritual.execute(Mood.SILENT, now=_at(17))
        assert result.message == "Sore."


# ===========================================================================
# Tests — Task count integration
# ===========================================================================


class TestTaskCount:
    """Task summary appended when task_count_today > 0."""

    @pytest.mark.asyncio
    async def test_task_count_appended(
        self, ritual: AfternoonRitual
    ) -> None:
        """Positive task count adds task summary to message."""
        result = await ritual.execute(Mood.CONTENT, task_count_today=5, now=_at(17))
        assert "5 tugas" in result.message
        assert "effort" in result.message.lower()

    @pytest.mark.asyncio
    async def test_task_count_zero_omitted(
        self, ritual: AfternoonRitual
    ) -> None:
        """Zero task count -> no task summary."""
        result = await ritual.execute(Mood.CONTENT, task_count_today=0, now=_at(17))
        assert "tugas" not in result.message

    @pytest.mark.asyncio
    async def test_task_count_default_omitted(
        self, ritual: AfternoonRitual
    ) -> None:
        """Default task_count_today (0) -> no task summary."""
        result = await ritual.execute(Mood.CONTENT, now=_at(17))
        assert "tugas" not in result.message

    @pytest.mark.asyncio
    async def test_task_count_negative_omitted(
        self, ritual: AfternoonRitual
    ) -> None:
        """Negative task count treated as no tasks."""
        result = await ritual.execute(Mood.CONTENT, task_count_today=-1, now=_at(17))
        assert "tugas" not in result.message

    @pytest.mark.asyncio
    async def test_task_count_large_number(
        self, ritual: AfternoonRitual
    ) -> None:
        """Large task count renders correctly."""
        result = await ritual.execute(
            Mood.PLEASED, task_count_today=42, now=_at(17)
        )
        assert "42 tugas" in result.message

    @pytest.mark.asyncio
    async def test_task_summary_newline_separated(
        self, ritual: AfternoonRitual
    ) -> None:
        """Task summary is on a new line after the greeting."""
        result = await ritual.execute(
            Mood.CONTENT, task_count_today=3, now=_at(17)
        )
        lines = result.message.split("\n")
        assert len(lines) == 2
        assert lines[0].startswith("Sore")
        assert "tugas" in lines[1]


# ===========================================================================
# Tests — RitualResult correctness
# ===========================================================================


class TestRitualResultFields:
    """RitualResult correctness for afternoon ritual."""

    @pytest.mark.asyncio
    async def test_ritual_name(self, ritual: AfternoonRitual) -> None:
        """ritual_name is always 'afternoon'."""
        result = await ritual.execute(Mood.CONTENT, now=_at(17))
        assert result.ritual_name == "afternoon"

    @pytest.mark.asyncio
    async def test_not_suppressed(self, ritual: AfternoonRitual) -> None:
        """Afternoon ritual is never suppressed (outside DND)."""
        result = await ritual.execute(Mood.CONTENT, now=_at(17))
        assert result.suppressed is False

    @pytest.mark.asyncio
    async def test_timestamp_set(self, ritual: AfternoonRitual) -> None:
        """timestamp is a datetime with timezone info."""
        now = _at(17)
        result = await ritual.execute(Mood.CONTENT, now=now)
        assert isinstance(result.timestamp, datetime)
        assert result.timestamp.tzinfo is not None

    @pytest.mark.asyncio
    async def test_timestamp_matches_input(
        self, ritual: AfternoonRitual
    ) -> None:
        """timestamp matches the provided now parameter."""
        now = _at(17, 30)
        result = await ritual.execute(Mood.CONTENT, now=now)
        assert result.timestamp == now

    @pytest.mark.asyncio
    async def test_message_not_empty(
        self, ritual: AfternoonRitual
    ) -> None:
        """All mood variants produce non-empty messages."""
        for mood in Mood:
            result = await ritual.execute(mood, now=_at(17))
            assert result.message != ""


# ===========================================================================
# Tests — Timezone handling
# ===========================================================================


class TestTimezoneHandling:
    """Verify timezone conversion and naive datetime handling."""

    @pytest.mark.asyncio
    async def test_naive_datetime_treated_as_jakarta(
        self, ritual: AfternoonRitual
    ) -> None:
        """Naive datetime is treated as Asia/Jakarta."""
        naive = datetime(2026, 6, 2, 17, 0, 0)
        result = await ritual.execute(Mood.CONTENT, now=naive)
        assert result.suppressed is False
        assert result.timestamp.tzinfo is not None

    @pytest.mark.asyncio
    async def test_utc_conversion(self, ritual: AfternoonRitual) -> None:
        """UTC-aware datetime is converted to Jakarta time.

        10:00 UTC = 17:00 WIB -> fires normally.
        """
        utc_5pm_wib = datetime(2026, 6, 2, 10, 0, 0, tzinfo=timezone.utc)
        result = await ritual.execute(Mood.CONTENT, now=utc_5pm_wib)
        assert result.suppressed is False


# ===========================================================================
# Tests — All moods produce distinct messages
# ===========================================================================


class TestDistinctMessages:
    """All mood variants produce unique message strings."""

    @pytest.mark.asyncio
    async def test_all_moods_distinct(self, ritual: AfternoonRitual) -> None:
        """All 5 moods produce unique check-in strings."""
        messages = set()
        for mood in Mood:
            result = await ritual.execute(mood, now=_at(17))
            messages.add(result.message)
        assert len(messages) == len(Mood)


# ===========================================================================
# Tests — Default template verification
# ===========================================================================


class TestDefaultTemplate:
    """Verify the documented default template."""

    @pytest.mark.asyncio
    async def test_default_content_template(
        self, ritual: AfternoonRitual
    ) -> None:
        """Default template matches documented CONTENT check-in."""
        result = await ritual.execute(Mood.CONTENT, now=_at(17))
        assert result.message == (
            "Sore, Darling. Gimana hari ini? Cerita sama Mommy."
        )


# ===========================================================================
# Tests — Task count with different moods
# ===========================================================================


class TestTaskCountWithMoods:
    """Task summary works correctly across all mood variants."""

    @pytest.mark.asyncio
    async def test_angry_with_tasks(self, ritual: AfternoonRitual) -> None:
        """ANGRY mood still includes task summary when tasks exist."""
        result = await ritual.execute(Mood.ANGRY, task_count_today=3, now=_at(17))
        assert "Sore. Cerita." in result.message
        assert "3 tugas" in result.message

    @pytest.mark.asyncio
    async def test_silent_with_tasks(self, ritual: AfternoonRitual) -> None:
        """SILENT mood still includes task summary when tasks exist."""
        result = await ritual.execute(Mood.SILENT, task_count_today=1, now=_at(17))
        assert result.message.startswith("Sore.")
        assert "1 tugas" in result.message

    @pytest.mark.asyncio
    async def test_task_count_one(self, ritual: AfternoonRitual) -> None:
        """Single task count renders correctly."""
        result = await ritual.execute(
            Mood.CONTENT, task_count_today=1, now=_at(17)
        )
        assert "1 tugas" in result.message


# ===========================================================================
# Tests — Constant
# ===========================================================================


class TestConstant:
    """Verify module-level constants."""

    def test_afternoon_hour(self) -> None:
        """AFTERNOON_HOUR is 17."""
        assert AFTERNOON_HOUR == 17
