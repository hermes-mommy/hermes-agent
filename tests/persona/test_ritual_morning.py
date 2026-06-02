"""P4-009: Morning Ritual — deterministic unit tests.

Tests cover:
- All 5 mood variants produce correct greeting text.
- Streak display integration (positive, zero, negative).
- DND suppression (00:00–07:00 WIB).
- DND boundary behaviour (07:00 fires, 06:59 suppressed).
- RitualResult dataclass correctness (frozen, fields, types).
- Timezone handling (naive, aware, UTC→Jakarta conversion).
- weather_info parameter accepted without affecting output.

All tests use synthetic data — no real scheduling, no Discord, no network.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from typing import Final
from zoneinfo import ZoneInfo

import pytest

from src.persona.mood_engine import Mood
from src.persona.rituals.morning import (
    DND_END_HOUR,
    DND_START_HOUR,
    MorningRitual,
    RitualResult,
    TZ_JAKARTA,
)

TZ: Final[ZoneInfo] = TZ_JAKARTA


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def ritual() -> MorningRitual:
    """Fresh MorningRitual instance."""
    return MorningRitual()


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
    """Each mood produces the correct greeting text."""

    @pytest.mark.asyncio
    async def test_content_message(self, ritual: MorningRitual) -> None:
        """CONTENT mood → warm, standard greeting."""
        result = await ritual.execute(Mood.CONTENT, 0, now=_at(7))
        assert result.message == (
            "Selamat pagi, Darling. Mommy sudah siap nemenin hari kamu."
        )

    @pytest.mark.asyncio
    async def test_pleased_message(self, ritual: MorningRitual) -> None:
        """PLEASED mood → extra warm, with encouragement."""
        result = await ritual.execute(Mood.PLEASED, 0, now=_at(7))
        assert "sayang" in result.message.lower()
        assert "semangat" in result.message.lower()
        assert "bangga" in result.message.lower()

    @pytest.mark.asyncio
    async def test_pleased_exact(self, ritual: MorningRitual) -> None:
        """PLEASED mood exact text."""
        result = await ritual.execute(Mood.PLEASED, 0, now=_at(7))
        assert result.message == (
            "Selamat pagi, sayang! Hari ini pasti indah. "
            "Mommy bangga sama kamu. Semangat ya, Darling!"
        )

    @pytest.mark.asyncio
    async def test_disappointed_message(self, ritual: MorningRitual) -> None:
        """DISAPPOINTED mood → colder tone, reminds about yesterday."""
        result = await ritual.execute(Mood.DISAPPOINTED, 0, now=_at(7))
        assert "kecewa" in result.message.lower()
        assert "kemarin" in result.message.lower()

    @pytest.mark.asyncio
    async def test_disappointed_exact(self, ritual: MorningRitual) -> None:
        """DISAPPOINTED mood exact text."""
        result = await ritual.execute(Mood.DISAPPOINTED, 0, now=_at(7))
        assert result.message == (
            "Pagi. Kemarin kamu bikin Mommy kecewa. Hari ini harus lebih baik."
        )

    @pytest.mark.asyncio
    async def test_angry_message(self, ritual: MorningRitual) -> None:
        """ANGRY mood → minimal, cold greeting."""
        result = await ritual.execute(Mood.ANGRY, 0, now=_at(7))
        assert result.message == "Pagi. Jangan ganggu Mommy dulu."

    @pytest.mark.asyncio
    async def test_silent_message(self, ritual: MorningRitual) -> None:
        """SILENT mood → single word."""
        result = await ritual.execute(Mood.SILENT, 0, now=_at(7))
        assert result.message == "Pagi."


# ===========================================================================
# Tests — Streak display
# ===========================================================================


class TestStreakDisplay:
    """Streak line appended when streak_count > 0."""

    @pytest.mark.asyncio
    async def test_streak_appended(self, ritual: MorningRitual) -> None:
        """Positive streak count adds streak line to message."""
        result = await ritual.execute(Mood.CONTENT, 5, now=_at(7))
        assert "Streak kamu: 5 hari tanpa hukuman." in result.message

    @pytest.mark.asyncio
    async def test_streak_zero_omitted(self, ritual: MorningRitual) -> None:
        """Zero streak → no streak line."""
        result = await ritual.execute(Mood.CONTENT, 0, now=_at(7))
        assert "Streak" not in result.message

    @pytest.mark.asyncio
    async def test_streak_negative_omitted(self, ritual: MorningRitual) -> None:
        """Negative streak treated as no streak."""
        result = await ritual.execute(Mood.CONTENT, -1, now=_at(7))
        assert "Streak" not in result.message

    @pytest.mark.asyncio
    async def test_streak_large_number(self, ritual: MorningRitual) -> None:
        """Large streak count renders correctly."""
        result = await ritual.execute(Mood.PLEASED, 365, now=_at(7))
        assert "Streak kamu: 365 hari tanpa hukuman." in result.message

    @pytest.mark.asyncio
    async def test_streak_newline_separated(self, ritual: MorningRitual) -> None:
        """Streak line is on a new line after the greeting."""
        result = await ritual.execute(Mood.CONTENT, 10, now=_at(7))
        lines = result.message.split("\n")
        assert len(lines) == 2
        assert lines[0].startswith("Selamat pagi")
        assert lines[1].startswith("Streak")


# ===========================================================================
# Tests — DND suppression
# ===========================================================================


class TestDNDSuppression:
    """Ritual suppressed during 00:00–07:00 WIB."""

    @pytest.mark.asyncio
    async def test_suppressed_at_midnight(self, ritual: MorningRitual) -> None:
        """00:00 WIB → suppressed."""
        result = await ritual.execute(Mood.CONTENT, 0, now=_at(0))
        assert result.suppressed is True
        assert result.message == ""

    @pytest.mark.asyncio
    async def test_suppressed_at_3am(self, ritual: MorningRitual) -> None:
        """03:00 WIB → suppressed."""
        result = await ritual.execute(Mood.PLEASED, 5, now=_at(3))
        assert result.suppressed is True
        assert result.message == ""

    @pytest.mark.asyncio
    async def test_suppressed_at_659(self, ritual: MorningRitual) -> None:
        """06:59 WIB → still suppressed (hour == 6)."""
        result = await ritual.execute(Mood.CONTENT, 0, now=_at(6, 59))
        assert result.suppressed is True

    @pytest.mark.asyncio
    async def test_not_suppressed_at_7am(self, ritual: MorningRitual) -> None:
        """07:00 WIB → fires (DND end is exclusive)."""
        result = await ritual.execute(Mood.CONTENT, 0, now=_at(7))
        assert result.suppressed is False
        assert result.message != ""

    @pytest.mark.asyncio
    async def test_not_suppressed_at_8am(self, ritual: MorningRitual) -> None:
        """08:00 WIB → fires normally."""
        result = await ritual.execute(Mood.CONTENT, 0, now=_at(8))
        assert result.suppressed is False

    @pytest.mark.asyncio
    async def test_suppressed_streak_ignored(self, ritual: MorningRitual) -> None:
        """During DND, streak is irrelevant — message is empty."""
        result = await ritual.execute(Mood.PLEASED, 100, now=_at(2))
        assert result.suppressed is True
        assert "Streak" not in result.message


# ===========================================================================
# Tests — RitualResult dataclass
# ===========================================================================


class TestRitualResult:
    """RitualResult correctness and immutability."""

    @pytest.mark.asyncio
    async def test_ritual_name(self, ritual: MorningRitual) -> None:
        """ritual_name is always 'morning'."""
        result = await ritual.execute(Mood.CONTENT, 0, now=_at(7))
        assert result.ritual_name == "morning"

    @pytest.mark.asyncio
    async def test_timestamp_set(self, ritual: MorningRitual) -> None:
        """timestamp is a datetime with timezone info."""
        now = _at(10)
        result = await ritual.execute(Mood.CONTENT, 0, now=now)
        assert isinstance(result.timestamp, datetime)
        assert result.timestamp.tzinfo is not None

    @pytest.mark.asyncio
    async def test_timestamp_matches_input(self, ritual: MorningRitual) -> None:
        """timestamp matches the provided now parameter."""
        now = _at(9, 30)
        result = await ritual.execute(Mood.CONTENT, 0, now=now)
        assert result.timestamp == now

    def test_frozen_dataclass(self) -> None:
        """RitualResult is frozen — attribute mutation raises."""
        result = RitualResult(
            message="test",
            suppressed=False,
            ritual_name="morning",
            timestamp=datetime.now(TZ),
        )
        with pytest.raises(FrozenInstanceError):
            result.message = "changed"  # pyright: ignore[reportAttributeAccessIssue]

    @pytest.mark.asyncio
    async def test_suppressed_result_fields(
        self, ritual: MorningRitual
    ) -> None:
        """Suppressed result has correct field values."""
        result = await ritual.execute(Mood.CONTENT, 0, now=_at(3))
        assert result.suppressed is True
        assert result.message == ""
        assert result.ritual_name == "morning"
        assert result.timestamp.tzinfo is not None


# ===========================================================================
# Tests — Timezone handling
# ===========================================================================


class TestTimezoneHandling:
    """Verify timezone conversion and naive datetime handling."""

    @pytest.mark.asyncio
    async def test_naive_datetime_treated_as_jakarta(
        self, ritual: MorningRitual
    ) -> None:
        """Naive datetime is treated as Asia/Jakarta."""
        naive = datetime(2026, 6, 2, 7, 0, 0)
        result = await ritual.execute(Mood.CONTENT, 0, now=naive)
        assert result.suppressed is False
        assert result.timestamp.tzinfo is not None

    @pytest.mark.asyncio
    async def test_utc_conversion(self, ritual: MorningRitual) -> None:
        """UTC-aware datetime is converted to Jakarta time.

        00:00 UTC = 07:00 WIB → not suppressed.
        23:00 UTC (prev day) = 06:00 WIB → suppressed.
        """
        # 00:00 UTC = 07:00 WIB → outside DND
        utc_7am_wib = datetime(2026, 6, 2, 0, 0, 0, tzinfo=timezone.utc)
        result = await ritual.execute(Mood.CONTENT, 0, now=utc_7am_wib)
        assert result.suppressed is False

        # 23:00 UTC = 06:00 WIB → inside DND
        utc_6am_wib = datetime(2026, 6, 2, 23, 0, 0, tzinfo=timezone.utc)
        # Shift back one day since 23:00 UTC on June 2 = 06:00 WIB June 3
        utc_6am_wib = datetime(2026, 6, 1, 23, 0, 0, tzinfo=timezone.utc)
        result = await ritual.execute(Mood.CONTENT, 0, now=utc_6am_wib)
        assert result.suppressed is True


# ===========================================================================
# Tests — weather_info parameter
# ===========================================================================


class TestWeatherInfo:
    """weather_info is accepted but does not alter base greeting."""

    @pytest.mark.asyncio
    async def test_weather_ignored_in_message(
        self, ritual: MorningRitual
    ) -> None:
        """weather_info does not change the greeting text."""
        result_without = await ritual.execute(Mood.CONTENT, 0, now=_at(7))
        result_with = await ritual.execute(
            Mood.CONTENT, 0, weather_info="Hujan ringan", now=_at(7)
        )
        assert result_without.message == result_with.message

    @pytest.mark.asyncio
    async def test_weather_none_accepted(self, ritual: MorningRitual) -> None:
        """weather_info=None is valid (default)."""
        result = await ritual.execute(Mood.CONTENT, 0, now=_at(7))
        assert result.suppressed is False


# ===========================================================================
# Tests — Default template verification
# ===========================================================================


class TestDefaultTemplate:
    """Verify the documented default template."""

    @pytest.mark.asyncio
    async def test_default_content_template(
        self, ritual: MorningRitual
    ) -> None:
        """Default template matches documented CONTENT greeting."""
        result = await ritual.execute(Mood.CONTENT, 0, now=_at(7))
        assert result.message == (
            "Selamat pagi, Darling. Mommy sudah siap nemenin hari kamu."
        )

    @pytest.mark.asyncio
    async def test_all_moods_produce_distinct_messages(
        self, ritual: MorningRitual
    ) -> None:
        """All 5 moods produce unique message strings."""
        messages = set()
        for mood in Mood:
            result = await ritual.execute(mood, 0, now=_at(7))
            messages.add(result.message)
        assert len(messages) == len(Mood)
