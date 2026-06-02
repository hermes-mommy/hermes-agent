"""P4-010: Midday Ritual — deterministic unit tests.

Tests cover:
- All 5 mood variants produce correct greeting text.
- Health reminder integration (enabled, disabled).
- Health reminder rotation (eat, water, stretch cycle).
- Reminder index override and modulo wrapping.
- RitualResult dataclass correctness (fields, types).
- Timezone handling (naive, aware, UTC→Jakarta conversion).
- Never-suppressed behaviour (12:00 WIB is outside DND).

All tests use synthetic data — no real scheduling, no Discord, no network.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Final
from zoneinfo import ZoneInfo

import pytest

from src.persona.mood_engine import Mood
from src.persona.rituals.midday import (
    HEALTH_REMINDER_LABELS,
    MIDDAY_HOUR,
    MiddayRitual,
    RitualResult,
    TZ_JAKARTA,
    _HEALTH_REMINDERS,
    _MOOD_MESSAGES,
)

TZ: Final[ZoneInfo] = TZ_JAKARTA


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def ritual() -> MiddayRitual:
    """Fresh MiddayRitual instance."""
    return MiddayRitual()


# ---------------------------------------------------------------------------
# Helper — build a timezone-aware datetime at a given hour
# ---------------------------------------------------------------------------


def _at(hour: int = MIDDAY_HOUR, minute: int = 0) -> datetime:
    """Return a Jakarta-tz datetime at noon on a fixed date (2026-06-02).

    June 2, 2026 = day 153 → 153 % 3 == 0 → default reminder index is 0 (eat).
    """
    return datetime(2026, 6, 2, hour, minute, 0, tzinfo=TZ)


# ===========================================================================
# Tests — Mood variant messages
# ===========================================================================


class TestMoodVariants:
    """Each mood produces the correct greeting text."""

    @pytest.mark.asyncio
    async def test_content_message(self, ritual: MiddayRitual) -> None:
        """CONTENT mood → standard caring reminder."""
        result = await ritual.execute(Mood.CONTENT, health_reminder_needed=False)
        assert result.message == (
            "Sayang, udah siang. Jangan lupa makan dan istirahat ya."
        )

    @pytest.mark.asyncio
    async def test_content_default_template(
        self, ritual: MiddayRitual
    ) -> None:
        """CONTENT matches the documented default template."""
        result = await ritual.execute(Mood.CONTENT, health_reminder_needed=False)
        assert "udah siang" in result.message
        assert "jangan lupa makan" in result.message.lower()

    @pytest.mark.asyncio
    async def test_pleased_message(self, ritual: MiddayRitual) -> None:
        """PLEASED mood → adds praise for morning productivity."""
        result = await ritual.execute(Mood.PLEASED, health_reminder_needed=False)
        assert "produktif" in result.message.lower()
        assert "bangga" in result.message.lower()

    @pytest.mark.asyncio
    async def test_pleased_exact(self, ritual: MiddayRitual) -> None:
        """PLEASED mood exact text."""
        result = await ritual.execute(Mood.PLEASED, health_reminder_needed=False)
        assert result.message == (
            "Sayang, udah siang! Pagi ini kamu produktif banget, "
            "Mommy bangga. Sekarang istirahat dulu ya."
        )

    @pytest.mark.asyncio
    async def test_disappointed_message(self, ritual: MiddayRitual) -> None:
        """DISAPPOINTED mood → guilt-tinged reminder."""
        result = await ritual.execute(
            Mood.DISAPPOINTED, health_reminder_needed=False
        )
        assert "belum makan" in result.message.lower()
        assert "kecewa" in result.message.lower()

    @pytest.mark.asyncio
    async def test_angry_message(self, ritual: MiddayRitual) -> None:
        """ANGRY mood → curt command."""
        result = await ritual.execute(Mood.ANGRY, health_reminder_needed=False)
        assert result.message == "Makan. Sekarang."

    @pytest.mark.asyncio
    async def test_silent_message(self, ritual: MiddayRitual) -> None:
        """SILENT mood → minimal two-word response."""
        result = await ritual.execute(Mood.SILENT, health_reminder_needed=False)
        assert result.message == "Siang. Makan."


# ===========================================================================
# Tests — Health reminder integration
# ===========================================================================


class TestHealthReminders:
    """Health reminders appended or omitted based on flag."""

    @pytest.mark.asyncio
    async def test_reminder_appended(self, ritual: MiddayRitual) -> None:
        """health_reminder_needed=True appends a reminder line."""
        result = await ritual.execute(
            Mood.CONTENT, health_reminder_needed=True, reminder_index=0
        )
        lines = result.message.split("\n")
        assert len(lines) == 2
        assert lines[1] == _HEALTH_REMINDERS[0]

    @pytest.mark.asyncio
    async def test_reminder_omitted(self, ritual: MiddayRitual) -> None:
        """health_reminder_needed=False → no reminder line."""
        result = await ritual.execute(
            Mood.CONTENT, health_reminder_needed=False
        )
        assert "\n" not in result.message

    @pytest.mark.asyncio
    async def test_reminder_default_true(self, ritual: MiddayRitual) -> None:
        """Default health_reminder_needed is True."""
        result = await ritual.execute(Mood.CONTENT)
        assert "\n" in result.message


# ===========================================================================
# Tests — Health reminder rotation
# ===========================================================================


class TestHealthReminderRotation:
    """Rotating reminders: eat (0), water (1), stretch (2)."""

    @pytest.mark.asyncio
    async def test_reminder_eat(self, ritual: MiddayRitual) -> None:
        """Index 0 → eat reminder."""
        result = await ritual.execute(
            Mood.CONTENT, reminder_index=0
        )
        assert "makan siang" in result.message.lower()

    @pytest.mark.asyncio
    async def test_reminder_water(self, ritual: MiddayRitual) -> None:
        """Index 1 → drink water reminder."""
        result = await ritual.execute(
            Mood.CONTENT, reminder_index=1
        )
        assert "minum air" in result.message.lower()

    @pytest.mark.asyncio
    async def test_reminder_stretch(self, ritual: MiddayRitual) -> None:
        """Index 2 → stretch / rest eyes reminder."""
        result = await ritual.execute(
            Mood.CONTENT, reminder_index=2
        )
        assert "stretch" in result.message.lower()
        assert "mata" in result.message.lower()

    @pytest.mark.asyncio
    async def test_reminder_day_rotation(self, ritual: MiddayRitual) -> None:
        """Default rotation uses day-of-year modulo 3.

        2026-06-02 = day 153, 153 % 3 == 0 → eat.
        """
        result = await ritual.execute(Mood.CONTENT, now=_at())
        # Day 153 % 3 = 0 → eat
        assert "makan siang" in result.message.lower()

    @pytest.mark.asyncio
    async def test_reminder_override_takes_precedence(
        self, ritual: MiddayRitual
    ) -> None:
        """Explicit reminder_index overrides day-of-year rotation."""
        # Day 153 % 3 = 0 (eat), but override to 2 (stretch)
        result = await ritual.execute(
            Mood.CONTENT, now=_at(), reminder_index=2
        )
        assert "stretch" in result.message.lower()

    @pytest.mark.asyncio
    async def test_reminder_index_wraps(self, ritual: MiddayRitual) -> None:
        """Index modulo wraps correctly (e.g. 5 → 5%3=2 → stretch)."""
        result = await ritual.execute(
            Mood.CONTENT, reminder_index=5
        )
        # 5 % 3 = 2 → stretch
        assert "stretch" in result.message.lower()

    @pytest.mark.asyncio
    async def test_all_reminders_distinct(self, ritual: MiddayRitual) -> None:
        """All 3 health reminders are unique strings."""
        reminders = set()
        for idx in range(3):
            result = await ritual.execute(
                Mood.CONTENT, reminder_index=idx
            )
            # Extract the reminder line
            reminder_line = result.message.split("\n")[1]
            reminders.add(reminder_line)
        assert len(reminders) == 3


# ===========================================================================
# Tests — RitualResult dataclass
# ===========================================================================


class TestRitualResult:
    """RitualResult correctness for midday ritual."""

    @pytest.mark.asyncio
    async def test_ritual_name(self, ritual: MiddayRitual) -> None:
        """ritual_name is always 'midday'."""
        result = await ritual.execute(Mood.CONTENT)
        assert result.ritual_name == "midday"

    @pytest.mark.asyncio
    async def test_never_suppressed(self, ritual: MiddayRitual) -> None:
        """Midday ritual is never suppressed (12:00 WIB is outside DND)."""
        for mood in Mood:
            result = await ritual.execute(mood, health_reminder_needed=False)
            assert result.suppressed is False

    @pytest.mark.asyncio
    async def test_timestamp_set(self, ritual: MiddayRitual) -> None:
        """timestamp is a datetime with timezone info."""
        now = _at()
        result = await ritual.execute(Mood.CONTENT, now=now)
        assert isinstance(result.timestamp, datetime)
        assert result.timestamp.tzinfo is not None

    @pytest.mark.asyncio
    async def test_timestamp_matches_input(self, ritual: MiddayRitual) -> None:
        """timestamp matches the provided now parameter."""
        now = _at(12, 30)
        result = await ritual.execute(Mood.CONTENT, now=now)
        assert result.timestamp == now


# ===========================================================================
# Tests — Timezone handling
# ===========================================================================


class TestTimezoneHandling:
    """Verify timezone conversion and naive datetime handling."""

    @pytest.mark.asyncio
    async def test_naive_datetime_treated_as_jakarta(
        self, ritual: MiddayRitual
    ) -> None:
        """Naive datetime is treated as Asia/Jakarta."""
        naive = datetime(2026, 6, 2, 12, 0, 0)
        result = await ritual.execute(Mood.CONTENT, now=naive)
        assert result.suppressed is False
        assert result.timestamp.tzinfo is not None

    @pytest.mark.asyncio
    async def test_utc_conversion(self, ritual: MiddayRitual) -> None:
        """UTC-aware datetime is converted to Jakarta time.

        05:00 UTC = 12:00 WIB → valid midday timestamp.
        """
        utc_noon_wib = datetime(2026, 6, 2, 5, 0, 0, tzinfo=timezone.utc)
        result = await ritual.execute(Mood.CONTENT, now=utc_noon_wib)
        assert result.suppressed is False
        assert result.timestamp.hour == 12


# ===========================================================================
# Tests — All moods produce distinct messages
# ===========================================================================


class TestAllMoodsDistinct:
    """Verify all mood variants are distinguishable."""

    @pytest.mark.asyncio
    async def test_all_moods_distinct(self, ritual: MiddayRitual) -> None:
        """All 5 moods produce unique base message strings."""
        messages = set()
        for mood in Mood:
            base_msg = _MOOD_MESSAGES[mood]
            messages.add(base_msg)
        assert len(messages) == len(Mood)

    @pytest.mark.asyncio
    async def test_mood_message_matches_template(
        self, ritual: MiddayRitual
    ) -> None:
        """Each mood's output starts with its template text."""
        for mood in Mood:
            result = await ritual.execute(
                mood, health_reminder_needed=False
            )
            assert result.message == _MOOD_MESSAGES[mood]


# ===========================================================================
# Tests — Edge cases
# ===========================================================================


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_angry_with_reminder(self, ritual: MiddayRitual) -> None:
        """ANGRY mood + reminder: curt message + reminder appended."""
        result = await ritual.execute(
            Mood.ANGRY, health_reminder_needed=True, reminder_index=0
        )
        lines = result.message.split("\n")
        assert lines[0] == "Makan. Sekarang."
        assert lines[1] == _HEALTH_REMINDERS[0]

    @pytest.mark.asyncio
    async def test_silent_with_reminder(self, ritual: MiddayRitual) -> None:
        """SILENT mood + reminder: minimal message + reminder appended."""
        result = await ritual.execute(
            Mood.SILENT, health_reminder_needed=True, reminder_index=1
        )
        lines = result.message.split("\n")
        assert lines[0] == "Siang. Makan."
        assert "minum air" in lines[1].lower()

    @pytest.mark.asyncio
    async def test_health_reminder_labels_match_reminders(
        self,
    ) -> None:
        """HEALTH_REMINDER_LABELS and _HEALTH_REMINDERS have same length."""
        assert len(HEALTH_REMINDER_LABELS) == len(_HEALTH_REMINDERS)

    @pytest.mark.asyncio
    async def test_midday_hour_constant(self) -> None:
        """MIDDAY_HOUR is 12."""
        assert MIDDAY_HOUR == 12
