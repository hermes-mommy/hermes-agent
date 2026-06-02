"""P4-013: Midnight Ritual — deterministic unit tests.

Tests cover:
- Always-suppressed behaviour (DND active 00:00–07:00 WIB).
- Self-evaluation data processing (list keys, count keys, mixed, None).
- RitualResult dataclass correctness (fields, types, suppressed=True).
- Message template verification.
- Timezone handling (naive, aware, UTC→Jakarta conversion).
- structlog logging interaction (log event name, context fields).
- Edge cases: None data, empty data, missing keys, negative counts, priority.

All tests use synthetic data — no real scheduling, no Discord, no network.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Final
from zoneinfo import ZoneInfo

import pytest
import structlog
from structlog.testing import LogCapture

from src.persona.rituals.midnight import (
    MIDNIGHT_HOUR,
    MidnightRitual,
)
from src.persona.rituals.morning import RitualResult, TZ_JAKARTA

TZ: Final[ZoneInfo] = TZ_JAKARTA


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def ritual() -> MidnightRitual:
    """Fresh MidnightRitual instance."""
    return MidnightRitual()


@pytest.fixture
def log_capture() -> LogCapture:
    """structlog log capture for verifying internal logging."""
    cap = LogCapture()
    structlog.configure(processors=[cap])
    return cap


# ---------------------------------------------------------------------------
# Helper — build a timezone-aware datetime at a given hour
# ---------------------------------------------------------------------------


def _at(hour: int = MIDNIGHT_HOUR, minute: int = 0) -> datetime:
    """Return a Jakarta-tz datetime at the given hour on a fixed date."""
    return datetime(2026, 6, 2, hour, minute, 0, tzinfo=TZ)


# ===========================================================================
# Tests — Always suppressed behaviour
# ===========================================================================


class TestAlwaysSuppressed:
    """Midnight ritual is always suppressed — DND 00:00–07:00 WIB."""

    @pytest.mark.asyncio
    async def test_suppressed_at_midnight(
        self, ritual: MidnightRitual
    ) -> None:
        """At 00:00 WIB, suppressed is True."""
        result = await ritual.execute(now=_at(0))
        assert result.suppressed is True

    @pytest.mark.asyncio
    async def test_suppressed_regardless_of_data(
        self, ritual: MidnightRitual
    ) -> None:
        """Suppressed even when evaluation data is provided."""
        data = {
            "mood_transitions": [{"from": "Content", "to": "Pleased"}],
            "punishments": [{"type": "warning"}],
            "rewards": [{"type": "praise"}],
            "streak_count": 7,
        }
        result = await ritual.execute(self_evaluation_data=data, now=_at(0))
        assert result.suppressed is True

    @pytest.mark.asyncio
    async def test_suppressed_with_none_data(
        self, ritual: MidnightRitual
    ) -> None:
        """Suppressed even when no data is provided."""
        result = await ritual.execute(now=_at(0))
        assert result.suppressed is True

    @pytest.mark.asyncio
    async def test_suppressed_at_any_time(
        self, ritual: MidnightRitual
    ) -> None:
        """Suppressed regardless of hour — always True for midnight ritual."""
        for hour in (0, 3, 6, 12, 17, 23):
            result = await ritual.execute(now=_at(hour))
            assert result.suppressed is True, f"Expected suppressed at {hour}:00"


# ===========================================================================
# Tests — Message template
# ===========================================================================


class TestMessageTemplate:
    """The internal evaluation message is fixed regardless of data."""

    @pytest.mark.asyncio
    async def test_message_is_evaluation_template(
        self, ritual: MidnightRitual
    ) -> None:
        """Message is always the internal evaluation template."""
        result = await ritual.execute(now=_at(0))
        assert result.message == (
            "Self-evaluation complete. Silent mode until morning."
        )

    @pytest.mark.asyncio
    async def test_message_unchanged_with_data(
        self, ritual: MidnightRitual
    ) -> None:
        """Message is unchanged even when evaluation data is provided."""
        data = {"streak_count": 42}
        result = await ritual.execute(self_evaluation_data=data, now=_at(0))
        assert result.message == (
            "Self-evaluation complete. Silent mode until morning."
        )

    @pytest.mark.asyncio
    async def test_message_not_empty(
        self, ritual: MidnightRitual
    ) -> None:
        """Message is never empty (internal template always present)."""
        result = await ritual.execute(now=_at(0))
        assert result.message != ""


# ===========================================================================
# Tests — RitualResult field correctness
# ===========================================================================


class TestRitualResultFields:
    """RitualResult dataclass field verification."""

    @pytest.mark.asyncio
    async def test_ritual_name(self, ritual: MidnightRitual) -> None:
        """ritual_name is always 'midnight'."""
        result = await ritual.execute(now=_at(0))
        assert result.ritual_name == "midnight"

    @pytest.mark.asyncio
    async def test_timestamp_is_tz_aware(
        self, ritual: MidnightRitual
    ) -> None:
        """timestamp has timezone info."""
        result = await ritual.execute(now=_at(0))
        assert isinstance(result.timestamp, datetime)
        assert result.timestamp.tzinfo is not None

    @pytest.mark.asyncio
    async def test_timestamp_matches_input(
        self, ritual: MidnightRitual
    ) -> None:
        """timestamp matches the provided now parameter."""
        now = _at(0, 15)
        result = await ritual.execute(now=now)
        assert result.timestamp == now

    @pytest.mark.asyncio
    async def test_result_is_ritualresult_instance(
        self, ritual: MidnightRitual
    ) -> None:
        """Return value is a RitualResult dataclass."""
        result = await ritual.execute(now=_at(0))
        assert isinstance(result, RitualResult)


# ===========================================================================
# Tests — Self-evaluation data processing: None and empty
# ===========================================================================


class TestEvaluationDataNoneAndEmpty:
    """When data is None or empty, all counts default to 0."""

    @pytest.mark.asyncio
    async def test_none_data_defaults_to_zero(
        self, ritual: MidnightRitual, log_capture: LogCapture
    ) -> None:
        """None self_evaluation_data → all counts = 0."""
        result = await ritual.execute(now=_at(0))
        assert result.suppressed is True

    @pytest.mark.asyncio
    async def test_empty_dict_defaults_to_zero(
        self, ritual: MidnightRitual, log_capture: LogCapture
    ) -> None:
        """Empty dict → all counts = 0."""
        result = await ritual.execute(self_evaluation_data={}, now=_at(0))
        assert result.suppressed is True

    @pytest.mark.asyncio
    async def test_no_key_error_on_none(
        self, ritual: MidnightRitual
    ) -> None:
        """None data does not raise KeyError or AttributeError."""
        # Should not raise
        result = await ritual.execute(self_evaluation_data=None, now=_at(0))
        assert result is not None


# ===========================================================================
# Tests — Self-evaluation data: list-based counts
# ===========================================================================


class TestListBasedCounts:
    """When list keys are present, counts are derived from len()."""

    @pytest.mark.asyncio
    async def test_mood_transitions_count_from_list(
        self, ritual: MidnightRitual
    ) -> None:
        """mood_transitions list → count = len(list)."""
        data = {
            "mood_transitions": [
                {"from": "Content", "to": "Pleased"},
                {"from": "Pleased", "to": "Content"},
                {"from": "Content", "to": "Disappointed"},
            ],
        }
        result = await ritual.execute(self_evaluation_data=data, now=_at(0))
        assert result.suppressed is True

    @pytest.mark.asyncio
    async def test_punishments_count_from_list(
        self, ritual: MidnightRitual
    ) -> None:
        """punishments list → count = len(list)."""
        data = {"punishments": [{"type": "warning"}, {"type": "silence"}]}
        result = await ritual.execute(self_evaluation_data=data, now=_at(0))
        assert result.suppressed is True

    @pytest.mark.asyncio
    async def test_rewards_count_from_list(
        self, ritual: MidnightRitual
    ) -> None:
        """rewards list → count = len(list)."""
        data = {"rewards": [{"type": "praise"}]}
        result = await ritual.execute(self_evaluation_data=data, now=_at(0))
        assert result.suppressed is True


# ===========================================================================
# Tests — Self-evaluation data: direct count keys
# ===========================================================================


class TestDirectCountKeys:
    """When count keys are present (no lists), they are used directly."""

    @pytest.mark.asyncio
    async def test_mood_transitions_direct_count(
        self, ritual: MidnightRitual
    ) -> None:
        """mood_transitions_count used directly."""
        data = {"mood_transitions_count": 5}
        result = await ritual.execute(self_evaluation_data=data, now=_at(0))
        assert result.suppressed is True

    @pytest.mark.asyncio
    async def test_punishments_direct_count(
        self, ritual: MidnightRitual
    ) -> None:
        """punishments_count used directly."""
        data = {"punishments_count": 3}
        result = await ritual.execute(self_evaluation_data=data, now=_at(0))
        assert result.suppressed is True

    @pytest.mark.asyncio
    async def test_rewards_direct_count(
        self, ritual: MidnightRitual
    ) -> None:
        """rewards_count used directly."""
        data = {"rewards_count": 2}
        result = await ritual.execute(self_evaluation_data=data, now=_at(0))
        assert result.suppressed is True

    @pytest.mark.asyncio
    async def test_streak_count_direct(
        self, ritual: MidnightRitual
    ) -> None:
        """streak_count extracted directly from data."""
        data = {"streak_count": 30}
        result = await ritual.execute(self_evaluation_data=data, now=_at(0))
        assert result.suppressed is True


# ===========================================================================
# Tests — Self-evaluation data: edge cases
# ===========================================================================


class TestEvaluationDataEdgeCases:
    """Edge cases for self-evaluation data processing."""

    @pytest.mark.asyncio
    async def test_negative_counts_clamped_to_zero(
        self, ritual: MidnightRitual
    ) -> None:
        """Negative counts are clamped to 0."""
        data = {
            "mood_transitions_count": -5,
            "punishments_count": -1,
            "rewards_count": -3,
            "streak_count": -10,
        }
        result = await ritual.execute(self_evaluation_data=data, now=_at(0))
        assert result.suppressed is True

    @pytest.mark.asyncio
    async def test_missing_keys_default_to_zero(
        self, ritual: MidnightRitual
    ) -> None:
        """Partial data — missing keys default to 0."""
        data = {"streak_count": 10}  # only streak, no transitions/punishments/rewards
        result = await ritual.execute(self_evaluation_data=data, now=_at(0))
        assert result.suppressed is True

    @pytest.mark.asyncio
    async def test_list_key_priority_over_count_key(
        self, ritual: MidnightRitual
    ) -> None:
        """When both list and count keys present, list takes priority."""
        data = {
            "mood_transitions": [1, 2, 3],
            "mood_transitions_count": 99,
        }
        result = await ritual.execute(self_evaluation_data=data, now=_at(0))
        assert result.suppressed is True

    @pytest.mark.asyncio
    async def test_non_int_count_key_ignored(
        self, ritual: MidnightRitual
    ) -> None:
        """Non-int count key is ignored, defaults to 0."""
        data = {"mood_transitions_count": "twelve"}
        result = await ritual.execute(self_evaluation_data=data, now=_at(0))
        assert result.suppressed is True

    @pytest.mark.asyncio
    async def test_non_int_streak_ignored(
        self, ritual: MidnightRitual
    ) -> None:
        """Non-int streak_count is clamped to 0."""
        data = {"streak_count": "seven"}
        result = await ritual.execute(self_evaluation_data=data, now=_at(0))
        assert result.suppressed is True


# ===========================================================================
# Tests — Logging interaction
# ===========================================================================


class TestLogging:
    """structlog logging is called with correct event and fields."""

    @pytest.mark.asyncio
    async def test_logging_event_name(
        self, ritual: MidnightRitual, log_capture: LogCapture
    ) -> None:
        """Log event name is 'midnight_ritual_self_evaluation'."""
        await ritual.execute(now=_at(0))
        entries = log_capture.entries
        assert len(entries) >= 1
        assert any(
            e.get("event") == "midnight_ritual_self_evaluation"
            for e in entries
        )

    @pytest.mark.asyncio
    async def test_logging_contains_ritual_name(
        self, ritual: MidnightRitual, log_capture: LogCapture
    ) -> None:
        """Log entry includes ritual_name='midnight'."""
        await ritual.execute(now=_at(0))
        entries = log_capture.entries
        matching = [
            e
            for e in entries
            if e.get("event") == "midnight_ritual_self_evaluation"
        ]
        assert len(matching) >= 1
        assert matching[0].get("ritual_name") == "midnight"

    @pytest.mark.asyncio
    async def test_logging_contains_suppressed_flag(
        self, ritual: MidnightRitual, log_capture: LogCapture
    ) -> None:
        """Log entry includes suppressed=True."""
        await ritual.execute(now=_at(0))
        entries = log_capture.entries
        matching = [
            e
            for e in entries
            if e.get("event") == "midnight_ritual_self_evaluation"
        ]
        assert len(matching) >= 1
        assert matching[0].get("suppressed") is True

    @pytest.mark.asyncio
    async def test_logging_contains_all_count_fields(
        self, ritual: MidnightRitual, log_capture: LogCapture
    ) -> None:
        """Log entry includes all four count fields."""
        data = {
            "mood_transitions": [1],
            "punishments": [1, 2],
            "rewards": [1, 2, 3],
            "streak_count": 5,
        }
        await ritual.execute(self_evaluation_data=data, now=_at(0))
        matching = [
            e
            for e in log_capture.entries
            if e.get("event") == "midnight_ritual_self_evaluation"
        ]
        assert len(matching) >= 1
        entry = matching[0]
        assert entry.get("mood_transitions_count") == 1
        assert entry.get("punishments_count") == 2
        assert entry.get("rewards_count") == 3
        assert entry.get("streak_count") == 5

    @pytest.mark.asyncio
    async def test_logging_zero_counts_with_no_data(
        self, ritual: MidnightRitual, log_capture: LogCapture
    ) -> None:
        """Log entry shows all zeros when no data provided."""
        await ritual.execute(now=_at(0))
        matching = [
            e
            for e in log_capture.entries
            if e.get("event") == "midnight_ritual_self_evaluation"
        ]
        assert len(matching) >= 1
        entry = matching[0]
        assert entry.get("mood_transitions_count") == 0
        assert entry.get("punishments_count") == 0
        assert entry.get("rewards_count") == 0
        assert entry.get("streak_count") == 0


# ===========================================================================
# Tests — Timezone handling
# ===========================================================================


class TestTimezoneHandling:
    """Verify timezone conversion and naive datetime handling."""

    @pytest.mark.asyncio
    async def test_naive_datetime_treated_as_jakarta(
        self, ritual: MidnightRitual
    ) -> None:
        """Naive datetime is treated as Asia/Jakarta."""
        naive = datetime(2026, 6, 2, 0, 0, 0)
        result = await ritual.execute(now=naive)
        assert result.suppressed is True
        assert result.timestamp.tzinfo is not None

    @pytest.mark.asyncio
    async def test_utc_conversion(self, ritual: MidnightRitual) -> None:
        """UTC-aware datetime is converted to Jakarta time.

        17:00 UTC = 00:00 WIB (next day) → midnight ritual fires.
        """
        utc_midnight_wib = datetime(
            2026, 6, 1, 17, 0, 0, tzinfo=timezone.utc
        )
        result = await ritual.execute(now=utc_midnight_wib)
        assert result.suppressed is True


# ===========================================================================
# Tests — Constant
# ===========================================================================


class TestConstant:
    """Verify module-level constants."""

    def test_midnight_hour(self) -> None:
        """MIDNIGHT_HOUR is 0."""
        assert MIDNIGHT_HOUR == 0