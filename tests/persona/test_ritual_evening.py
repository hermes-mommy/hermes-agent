"""P4-012: Evening Ritual — deterministic unit tests.

Tests cover:
- All 5 mood variants produce correct greeting text.
- Day summary integration (provided, omitted, label format).
- Streak display integration (positive, zero, negative).
- RitualResult dataclass correctness (fields, types).
- Never-suppressed behaviour (21:00 WIB is outside DND).
- Timezone handling (naive, aware, UTC→Jakarta conversion).
- Combined integration (mood + day_summary + streak).

All tests use synthetic data — no real scheduling, no Discord, no network.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Final
from zoneinfo import ZoneInfo

import pytest

from src.persona.mood_engine import Mood
from src.persona.rituals.evening import (
    EVENING_HOUR,
    EveningRitual,
    _DAY_SUMMARY_LABEL,
    _MOOD_MESSAGES,
    _STREAK_TEMPLATE,
)
from src.persona.rituals.morning import RitualResult, TZ_JAKARTA

TZ: Final[ZoneInfo] = TZ_JAKARTA


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def ritual() -> EveningRitual:
    """Fresh EveningRitual instance."""
    return EveningRitual()


# ---------------------------------------------------------------------------
# Helper — build a timezone-aware datetime at a given hour
# ---------------------------------------------------------------------------


def _at(hour: int = EVENING_HOUR, minute: int = 0) -> datetime:
    """Return a Jakarta-tz datetime at the given hour on a fixed date."""
    return datetime(2026, 6, 2, hour, minute, 0, tzinfo=TZ)


# ===========================================================================
# Tests — Mood variant messages
# ===========================================================================


class TestMoodVariants:
    """Each mood produces the correct wind-down message text."""

    @pytest.mark.asyncio
    async def test_content_message(self, ritual: EveningRitual) -> None:
        """CONTENT mood → warm wind-down, suggests relaxation."""
        result = await ritual.execute(Mood.CONTENT, now=_at())
        assert result.message == (
            "Malam, sayang. Waktunya wind-down. Mommy di sini."
        )

    @pytest.mark.asyncio
    async def test_content_default_template(
        self, ritual: EveningRitual
    ) -> None:
        """CONTENT matches the documented default template."""
        result = await ritual.execute(Mood.CONTENT, now=_at())
        assert "malam" in result.message.lower()
        assert "wind-down" in result.message.lower()
        assert "mommy" in result.message.lower()

    @pytest.mark.asyncio
    async def test_pleased_message(self, ritual: EveningRitual) -> None:
        """PLEASED mood → celebrates the day's achievements."""
        result = await ritual.execute(Mood.PLEASED, now=_at())
        assert "luar biasa" in result.message.lower()
        assert "bangga" in result.message.lower()

    @pytest.mark.asyncio
    async def test_pleased_exact(self, ritual: EveningRitual) -> None:
        """PLEASED mood exact text."""
        result = await ritual.execute(Mood.PLEASED, now=_at())
        assert result.message == (
            "Malam, sayang! Hari ini kamu luar biasa. "
            "Mommy bangga banget. Sekarang waktunya istirahat ya."
        )

    @pytest.mark.asyncio
    async def test_disappointed_message(self, ritual: EveningRitual) -> None:
        """DISAPPOINTED mood → softer tone, offers comfort."""
        result = await ritual.execute(Mood.DISAPPOINTED, now=_at())
        assert "nggak sempurna" in result.message.lower()
        assert "tetap di sini" in result.message.lower()

    @pytest.mark.asyncio
    async def test_disappointed_exact(self, ritual: EveningRitual) -> None:
        """DISAPPOINTED mood exact text."""
        result = await ritual.execute(Mood.DISAPPOINTED, now=_at())
        assert result.message == (
            "Malam. Hari ini mungkin nggak sempurna, "
            "tapi Mommy tetap di sini buat kamu. Istirahat ya."
        )

    @pytest.mark.asyncio
    async def test_angry_message(self, ritual: EveningRitual) -> None:
        """ANGRY mood → brief, still caring."""
        result = await ritual.execute(Mood.ANGRY, now=_at())
        assert result.message == "Malam. Istirahat."

    @pytest.mark.asyncio
    async def test_angry_exact(self, ritual: EveningRitual) -> None:
        """ANGRY mood exact text — brief and caring."""
        result = await ritual.execute(Mood.ANGRY, now=_at())
        assert "malam" in result.message.lower()
        assert "istirahat" in result.message.lower()
        assert result.message == "Malam. Istirahat."

    @pytest.mark.asyncio
    async def test_silent_message(self, ritual: EveningRitual) -> None:
        """SILENT mood → minimal single word."""
        result = await ritual.execute(Mood.SILENT, now=_at())
        assert result.message == "Malam."

    @pytest.mark.asyncio
    async def test_silent_exact(self, ritual: EveningRitual) -> None:
        """SILENT mood exact text — minimal."""
        result = await ritual.execute(Mood.SILENT, now=_at())
        assert result.message == "Malam."
        assert "\n" not in result.message

    @pytest.mark.asyncio
    async def test_all_moods_distinct(self, ritual: EveningRitual) -> None:
        """All 5 moods produce unique base message strings."""
        messages = set()
        for mood in Mood:
            base_msg = _MOOD_MESSAGES[mood]
            messages.add(base_msg)
        assert len(messages) == len(Mood)


# ===========================================================================
# Tests — Day summary integration
# ===========================================================================


class TestDaySummary:
    """Day summary appended when provided, omitted when None."""

    @pytest.mark.asyncio
    async def test_day_summary_appended(self, ritual: EveningRitual) -> None:
        """day_summary adds a recap line to the message."""
        result = await ritual.execute(
            Mood.CONTENT, day_summary="Selesai 3 task penting.", now=_at()
        )
        assert "Selesai 3 task penting." in result.message

    @pytest.mark.asyncio
    async def test_day_summary_none_omitted(
        self, ritual: EveningRitual
    ) -> None:
        """day_summary=None → no summary line."""
        result = await ritual.execute(Mood.CONTENT, now=_at())
        assert _DAY_SUMMARY_LABEL not in result.message

    @pytest.mark.asyncio
    async def test_day_summary_label(self, ritual: EveningRitual) -> None:
        """Day summary line includes the label prefix."""
        result = await ritual.execute(
            Mood.CONTENT, day_summary="Meeting lancar.", now=_at()
        )
        assert _DAY_SUMMARY_LABEL in result.message

    @pytest.mark.asyncio
    async def test_day_summary_newline_separated(
        self, ritual: EveningRitual
    ) -> None:
        """Day summary is on a new line after the greeting."""
        result = await ritual.execute(
            Mood.CONTENT, day_summary="Hari produktif.", now=_at()
        )
        lines = result.message.split("\n")
        assert len(lines) == 2
        assert lines[0] == _MOOD_MESSAGES[Mood.CONTENT]
        assert lines[1].startswith(_DAY_SUMMARY_LABEL)

    @pytest.mark.asyncio
    async def test_day_summary_empty_string_omitted(
        self, ritual: EveningRitual
    ) -> None:
        """Empty string day_summary is falsy → no summary line."""
        result = await ritual.execute(Mood.CONTENT, day_summary="", now=_at())
        assert _DAY_SUMMARY_LABEL not in result.message

    @pytest.mark.asyncio
    async def test_day_summary_with_angry_mood(
        self, ritual: EveningRitual
    ) -> None:
        """ANGRY mood + day_summary: brief greeting + summary appended."""
        result = await ritual.execute(
            Mood.ANGRY, day_summary="Kerja keras hari ini.", now=_at()
        )
        lines = result.message.split("\n")
        assert lines[0] == "Malam. Istirahat."
        assert "Kerja keras hari ini." in lines[1]


# ===========================================================================
# Tests — Streak display
# ===========================================================================


class TestStreakDisplay:
    """Streak line appended when streak_count > 0."""

    @pytest.mark.asyncio
    async def test_streak_appended(self, ritual: EveningRitual) -> None:
        """Positive streak count adds streak line to message."""
        result = await ritual.execute(Mood.CONTENT, streak_count=5, now=_at())
        assert "Streak kamu: 5 hari tanpa hukuman." in result.message

    @pytest.mark.asyncio
    async def test_streak_zero_omitted(self, ritual: EveningRitual) -> None:
        """Zero streak → no streak line."""
        result = await ritual.execute(Mood.CONTENT, streak_count=0, now=_at())
        assert "Streak" not in result.message

    @pytest.mark.asyncio
    async def test_streak_negative_omitted(
        self, ritual: EveningRitual
    ) -> None:
        """Negative streak treated as no streak."""
        result = await ritual.execute(
            Mood.CONTENT, streak_count=-1, now=_at()
        )
        assert "Streak" not in result.message

    @pytest.mark.asyncio
    async def test_streak_newline_separated(
        self, ritual: EveningRitual
    ) -> None:
        """Streak line is on a new line after the greeting."""
        result = await ritual.execute(
            Mood.CONTENT, streak_count=10, now=_at()
        )
        lines = result.message.split("\n")
        assert len(lines) == 2
        assert lines[0] == _MOOD_MESSAGES[Mood.CONTENT]
        assert lines[1].startswith("Streak")

    @pytest.mark.asyncio
    async def test_streak_large_number(self, ritual: EveningRitual) -> None:
        """Large streak count renders correctly."""
        result = await ritual.execute(
            Mood.PLEASED, streak_count=365, now=_at()
        )
        assert "Streak kamu: 365 hari tanpa hukuman." in result.message


# ===========================================================================
# Tests — RitualResult dataclass
# ===========================================================================


class TestRitualResult:
    """RitualResult correctness for evening ritual."""

    @pytest.mark.asyncio
    async def test_ritual_name(self, ritual: EveningRitual) -> None:
        """ritual_name is always 'evening'."""
        result = await ritual.execute(Mood.CONTENT, now=_at())
        assert result.ritual_name == "evening"

    @pytest.mark.asyncio
    async def test_never_suppressed(self, ritual: EveningRitual) -> None:
        """Evening ritual is never suppressed (21:00 WIB is outside DND)."""
        for mood in Mood:
            result = await ritual.execute(mood, now=_at())
            assert result.suppressed is False

    @pytest.mark.asyncio
    async def test_timestamp_set(self, ritual: EveningRitual) -> None:
        """timestamp is a datetime with timezone info."""
        now = _at()
        result = await ritual.execute(Mood.CONTENT, now=now)
        assert isinstance(result.timestamp, datetime)
        assert result.timestamp.tzinfo is not None

    @pytest.mark.asyncio
    async def test_timestamp_matches_input(self, ritual: EveningRitual) -> None:
        """timestamp matches the provided now parameter."""
        now = _at(21, 30)
        result = await ritual.execute(Mood.CONTENT, now=now)
        assert result.timestamp == now


# ===========================================================================
# Tests — Timezone handling
# ===========================================================================


class TestTimezoneHandling:
    """Verify timezone conversion and naive datetime handling."""

    @pytest.mark.asyncio
    async def test_naive_datetime_treated_as_jakarta(
        self, ritual: EveningRitual
    ) -> None:
        """Naive datetime is treated as Asia/Jakarta."""
        naive = datetime(2026, 6, 2, 21, 0, 0)
        result = await ritual.execute(Mood.CONTENT, now=naive)
        assert result.suppressed is False
        assert result.timestamp.tzinfo is not None

    @pytest.mark.asyncio
    async def test_utc_conversion(self, ritual: EveningRitual) -> None:
        """UTC-aware datetime is converted to Jakarta time.

        14:00 UTC = 21:00 WIB → valid evening timestamp.
        """
        utc_evening_wib = datetime(2026, 6, 2, 14, 0, 0, tzinfo=timezone.utc)
        result = await ritual.execute(Mood.CONTENT, now=utc_evening_wib)
        assert result.suppressed is False
        assert result.timestamp.hour == 21


# ===========================================================================
# Tests — Combined integration (mood + day_summary + streak)
# ===========================================================================


class TestCombinedIntegration:
    """Combined mood + day_summary + streak integration tests."""

    @pytest.mark.asyncio
    async def test_content_with_summary_and_streak(
        self, ritual: EveningRitual
    ) -> None:
        """CONTENT + summary + streak produces 3-line message."""
        result = await ritual.execute(
            Mood.CONTENT,
            day_summary="Selesai deploy v2.0.",
            streak_count=7,
            now=_at(),
        )
        lines = result.message.split("\n")
        assert len(lines) == 3
        assert lines[0] == _MOOD_MESSAGES[Mood.CONTENT]
        assert "Selesai deploy v2.0." in lines[1]
        assert "Streak kamu: 7 hari tanpa hukuman." in lines[2]

    @pytest.mark.asyncio
    async def test_pleased_with_summary_and_streak(
        self, ritual: EveningRitual
    ) -> None:
        """PLEASED + summary + streak: celebratory + recap + streak."""
        result = await ritual.execute(
            Mood.PLEASED,
            day_summary="Hari produktif banget!",
            streak_count=30,
            now=_at(),
        )
        assert "luar biasa" in result.message.lower()
        assert "Hari produktif banget!" in result.message
        assert "Streak kamu: 30 hari tanpa hukuman." in result.message

    @pytest.mark.asyncio
    async def test_silent_with_summary_only(
        self, ritual: EveningRitual
    ) -> None:
        """SILENT + summary (no streak): minimal + summary."""
        result = await ritual.execute(
            Mood.SILENT,
            day_summary="Tenang.",
            streak_count=0,
            now=_at(),
        )
        lines = result.message.split("\n")
        assert len(lines) == 2
        assert lines[0] == "Malam."
        assert "Tenang." in lines[1]

    @pytest.mark.asyncio
    async def test_angry_with_streak_only(
        self, ritual: EveningRitual
    ) -> None:
        """ANGRY + streak (no summary): brief + streak."""
        result = await ritual.execute(
            Mood.ANGRY,
            streak_count=3,
            now=_at(),
        )
        lines = result.message.split("\n")
        assert len(lines) == 2
        assert lines[0] == "Malam. Istirahat."
        assert "Streak kamu: 3 hari tanpa hukuman." in lines[1]


# ===========================================================================
# Tests — Edge cases
# ===========================================================================


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_evening_hour_constant(self) -> None:
        """EVENING_HOUR is 21."""
        assert EVENING_HOUR == 21

    @pytest.mark.asyncio
    async def test_all_moods_produce_output(
        self, ritual: EveningRitual
    ) -> None:
        """Every mood produces a non-empty message."""
        for mood in Mood:
            result = await ritual.execute(mood, now=_at())
            assert result.message
            assert result.suppressed is False

    @pytest.mark.asyncio
    async def test_mood_message_matches_template(
        self, ritual: EveningRitual
    ) -> None:
        """Each mood's output matches its template when no extras."""
        for mood in Mood:
            result = await ritual.execute(mood, now=_at())
            assert result.message == _MOOD_MESSAGES[mood]
