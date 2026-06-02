"""Tests for MCP Time Tools — timezone conversions and scheduling utilities."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure project root is on sys.path for ``from src.*`` imports.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.mcp.tools.time_tools import (  # noqa: E402
    _humanise_delta,
    _parse_date,
    _parse_datetime,
    _resolve_tz,
    convert_time,
    current_time,
    days_in_month,
    get_timestamp,
    get_week_year,
    relative_time,
)

# Fixed "now" for deterministic relative-time tests.
_MOCK_NOW = datetime(2026, 6, 3, 12, 0, 0, tzinfo=timezone.utc)


# ============================================================================
# TestResolveTz
# ============================================================================


class TestResolveTz:
    """Timezone resolution — valid IANA names pass, invalid names raise."""

    def test_valid_utc(self) -> None:
        tz = _resolve_tz("UTC")
        assert str(tz) == "UTC"

    def test_valid_jakarta(self) -> None:
        tz = _resolve_tz("Asia/Jakarta")
        assert str(tz) == "Asia/Jakarta"

    def test_valid_new_york(self) -> None:
        tz = _resolve_tz("America/New_York")
        assert str(tz) == "America/New_York"

    def test_invalid_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Invalid timezone"):
            _resolve_tz("Not/A/Timezone")

    def test_empty_string_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Invalid timezone"):
            _resolve_tz("")


# ============================================================================
# TestParseDatetime
# ============================================================================


class TestParseDatetime:
    """Datetime string parsing — valid format and error cases."""

    def test_valid_datetime(self) -> None:
        dt = _parse_datetime("2026-05-31 12:00:00")
        assert dt == datetime(2026, 5, 31, 12, 0, 0)

    def test_midnight(self) -> None:
        dt = _parse_datetime("2026-01-01 00:00:00")
        assert dt == datetime(2026, 1, 1, 0, 0, 0)

    def test_invalid_format_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid datetime format"):
            _parse_datetime("31/05/2026 12:00")

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid datetime format"):
            _parse_datetime("")


# ============================================================================
# TestParseDate
# ============================================================================


class TestParseDate:
    """Date string parsing — YYYY-MM-DD format."""

    def test_valid_date(self) -> None:
        dt = _parse_date("2026-02-15")
        assert dt == datetime(2026, 2, 15)

    def test_leap_day(self) -> None:
        dt = _parse_date("2024-02-29")
        assert dt == datetime(2024, 2, 29)

    def test_invalid_format_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid date format"):
            _parse_date("15-02-2026")


# ============================================================================
# TestCurrentTime
# ============================================================================


class TestCurrentTime:
    """Get current time in various timezones."""

    @pytest.mark.asyncio
    async def test_default_jakarta(self) -> None:
        result = await current_time()
        # Should return a non-empty string in default format
        assert len(result) == 19  # "YYYY-MM-DD HH:MM:SS"
        # Should parse back successfully
        datetime.strptime(result, "%Y-%m-%d %H:%M:%S")

    @pytest.mark.asyncio
    async def test_utc(self) -> None:
        result = await current_time(tz_name="UTC")
        assert len(result) == 19

    @pytest.mark.asyncio
    async def test_custom_format(self) -> None:
        result = await current_time(fmt="%Y/%m/%d")
        assert len(result) == 10  # "YYYY/MM/DD"

    @pytest.mark.asyncio
    async def test_invalid_timezone_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid timezone"):
            await current_time(tz_name="Fake/Zone")


# ============================================================================
# TestConvertTime
# ============================================================================


class TestConvertTime:
    """Timezone conversion — WIB = UTC+7 is the canonical test."""

    @pytest.mark.asyncio
    async def test_utc_to_jakarta(self) -> None:
        """UTC 12:00 → WIB 19:00 (UTC+7)."""
        result = await convert_time("UTC", "Asia/Jakarta", "2026-05-31 12:00:00")
        assert result == "2026-05-31 19:00:00"

    @pytest.mark.asyncio
    async def test_jakarta_to_utc(self) -> None:
        """WIB 00:00 → UTC 17:00 previous day."""
        result = await convert_time("Asia/Jakarta", "UTC", "2026-06-01 00:00:00")
        assert result == "2026-05-31 17:00:00"

    @pytest.mark.asyncio
    async def test_same_timezone(self) -> None:
        result = await convert_time("UTC", "UTC", "2026-05-31 12:00:00")
        assert result == "2026-05-31 12:00:00"

    @pytest.mark.asyncio
    async def test_tokyo_to_jakarta(self) -> None:
        """JST (UTC+9) 12:00 → WIB (UTC+7) 10:00."""
        result = await convert_time("Asia/Tokyo", "Asia/Jakarta", "2026-05-31 12:00:00")
        assert result == "2026-05-31 10:00:00"

    @pytest.mark.asyncio
    async def test_dst_transition_new_york(self) -> None:
        """DST edge case — EST vs EDT offset changes."""
        # January: EST (UTC-5) → UTC 17:00
        result_winter = await convert_time(
            "America/New_York", "UTC", "2026-01-15 12:00:00"
        )
        assert result_winter == "2026-01-15 17:00:00"

        # July: EDT (UTC-4) → UTC 16:00
        result_summer = await convert_time(
            "America/New_York", "UTC", "2026-07-15 12:00:00"
        )
        assert result_summer == "2026-07-15 16:00:00"

    @pytest.mark.asyncio
    async def test_invalid_source_tz_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid timezone"):
            await convert_time("Bad/Zone", "UTC", "2026-05-31 12:00:00")

    @pytest.mark.asyncio
    async def test_invalid_target_tz_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid timezone"):
            await convert_time("UTC", "Bad/Zone", "2026-05-31 12:00:00")

    @pytest.mark.asyncio
    async def test_invalid_time_format_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid datetime format"):
            await convert_time("UTC", "Asia/Jakarta", "not-a-date")


# ============================================================================
# TestDaysInMonth
# ============================================================================


class TestDaysInMonth:
    """Days-in-month calculation — regular and leap years."""

    @pytest.mark.asyncio
    async def test_february_non_leap(self) -> None:
        assert await days_in_month("2026-02-15") == 28

    @pytest.mark.asyncio
    async def test_february_leap_year(self) -> None:
        assert await days_in_month("2024-02-15") == 29

    @pytest.mark.asyncio
    async def test_january(self) -> None:
        assert await days_in_month("2026-01-01") == 31

    @pytest.mark.asyncio
    async def test_april(self) -> None:
        assert await days_in_month("2026-04-10") == 30

    @pytest.mark.asyncio
    async def test_december(self) -> None:
        assert await days_in_month("2026-12-25") == 31

    @pytest.mark.asyncio
    async def test_default_current_month(self) -> None:
        result = await days_in_month()
        assert 28 <= result <= 31

    @pytest.mark.asyncio
    async def test_invalid_date_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid date format"):
            await days_in_month("not-a-date")


# ============================================================================
# TestRelativeTime
# ============================================================================


class TestRelativeTime:
    """Human-readable relative time — mocked 'now' for determinism."""

    # Save reference to real datetime before any patching.
    _real_dt = datetime

    def _patch_now(self):
        """Return a context manager that mocks datetime.now while keeping strptime real."""
        p = patch("src.mcp.tools.time_tools.datetime")
        return p

    @pytest.mark.asyncio
    async def test_seconds_ago(self) -> None:
        with self._patch_now() as mock_dt:
            mock_dt.now.return_value = _MOCK_NOW
            mock_dt.strptime.side_effect = self._real_dt.strptime
            result = await relative_time("2026-06-03 11:59:30")
        assert result == "30 seconds ago"

    @pytest.mark.asyncio
    async def test_minutes_ago(self) -> None:
        with self._patch_now() as mock_dt:
            mock_dt.now.return_value = _MOCK_NOW
            mock_dt.strptime.side_effect = self._real_dt.strptime
            result = await relative_time("2026-06-03 11:45:00")
        assert result == "15 minutes ago"

    @pytest.mark.asyncio
    async def test_hours_ago(self) -> None:
        with self._patch_now() as mock_dt:
            mock_dt.now.return_value = _MOCK_NOW
            mock_dt.strptime.side_effect = self._real_dt.strptime
            result = await relative_time("2026-06-03 09:00:00")
        assert result == "3 hours ago"

    @pytest.mark.asyncio
    async def test_days_ago(self) -> None:
        with self._patch_now() as mock_dt:
            mock_dt.now.return_value = _MOCK_NOW
            mock_dt.strptime.side_effect = self._real_dt.strptime
            result = await relative_time("2026-06-01 12:00:00")
        assert result == "2 days ago"

    @pytest.mark.asyncio
    async def test_future_time(self) -> None:
        with self._patch_now() as mock_dt:
            mock_dt.now.return_value = _MOCK_NOW
            mock_dt.strptime.side_effect = self._real_dt.strptime
            result = await relative_time("2026-06-03 15:00:00")
        assert result == "in 3 hours"

    @pytest.mark.asyncio
    async def test_one_hour_ago_singular(self) -> None:
        with self._patch_now() as mock_dt:
            mock_dt.now.return_value = _MOCK_NOW
            mock_dt.strptime.side_effect = self._real_dt.strptime
            result = await relative_time("2026-06-03 11:00:00")
        assert result == "1 hour ago"


# ============================================================================
# TestGetTimestamp
# ============================================================================


class TestGetTimestamp:
    """Unix timestamp conversion."""

    @pytest.mark.asyncio
    async def test_epoch_zero(self) -> None:
        result = await get_timestamp("1970-01-01 00:00:00")
        assert result == 0

    @pytest.mark.asyncio
    async def test_known_timestamp(self) -> None:
        # 2026-01-01 00:00:00 UTC = 1767225600
        result = await get_timestamp("2026-01-01 00:00:00")
        assert result == 1767225600

    @pytest.mark.asyncio
    async def test_returns_integer(self) -> None:
        result = await get_timestamp("2026-06-03 12:00:00")
        assert isinstance(result, int)

    @pytest.mark.asyncio
    async def test_invalid_format_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid datetime format"):
            await get_timestamp("invalid")


# ============================================================================
# TestGetWeekYear
# ============================================================================


class TestGetWeekYear:
    """Week and ISO-week calculation."""

    @pytest.mark.asyncio
    async def test_known_date(self) -> None:
        result = await get_week_year("2026-01-05")
        assert result["year"] == 2026
        assert result["isoWeek"] == 2
        assert "week" in result

    @pytest.mark.asyncio
    async def test_iso_week_boundary(self) -> None:
        # 2025-12-29 is ISO week 1 of 2026
        result = await get_week_year("2025-12-29")
        assert result["isoWeek"] == 1
        assert result["year"] == 2026

    @pytest.mark.asyncio
    async def test_default_current_date(self) -> None:
        result = await get_week_year()
        assert "week" in result
        assert "isoWeek" in result
        assert "year" in result

    @pytest.mark.asyncio
    async def test_invalid_date_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid date format"):
            await get_week_year("not-a-date")

    @pytest.mark.asyncio
    async def test_return_types(self) -> None:
        result = await get_week_year("2026-06-03")
        assert isinstance(result["week"], int)
        assert isinstance(result["isoWeek"], int)
        assert isinstance(result["year"], int)


# ============================================================================
# TestHumaniseDelta
# ============================================================================


class TestHumaniseDelta:
    """Delta seconds → human-readable string."""

    def test_zero_seconds(self) -> None:
        assert _humanise_delta(0) == "0 seconds ago"

    def test_one_second(self) -> None:
        assert _humanise_delta(1) == "1 second ago"

    def test_one_minute(self) -> None:
        assert _humanise_delta(60) == "1 minute ago"

    def test_plural_minutes(self) -> None:
        assert _humanise_delta(120) == "2 minutes ago"

    def test_one_hour(self) -> None:
        assert _humanise_delta(3600) == "1 hour ago"

    def test_one_day(self) -> None:
        assert _humanise_delta(86400) == "1 day ago"

    def test_future(self) -> None:
        assert _humanise_delta(-7200) == "in 2 hours"
