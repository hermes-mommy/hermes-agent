"""MCP Time Tools — Timezone conversions and scheduling utilities.

Provides timezone-aware time operations using Python's stdlib ``zoneinfo``
for IANA timezone support.  Default timezone is Asia/Jakarta (WIB, UTC+7).

All functions are READ_AUTO — no side effects, no operator approval needed.
"""

from __future__ import annotations

import calendar
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo, available_timezones

import structlog

from guinvere.mcp.auth import AuthLevel, require_approval

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_TZ: str = "Asia/Jakarta"
_DEFAULT_FORMAT: str = "%Y-%m-%d %H:%M:%S"
_DATETIME_FMT: str = "%Y-%m-%d %H:%M:%S"
_DATE_FMT: str = "%Y-%m-%d"

_SECONDS_PER_MINUTE: int = 60
_SECONDS_PER_HOUR: int = 3600
_SECONDS_PER_DAY: int = 86400


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_tz(tz_name: str) -> ZoneInfo:
    """Resolve a timezone name to ``ZoneInfo``, raising ``ValueError`` if invalid."""
    valid_zones = available_timezones()
    if tz_name not in valid_zones:
        raise ValueError(
            f"Invalid timezone '{tz_name}'. "
            f"Use a valid IANA timezone (e.g. 'Asia/Jakarta', 'UTC', 'America/New_York')."
        )
    return ZoneInfo(tz_name)


def _parse_datetime(time_str: str) -> datetime:
    """Parse a naive datetime string in ``YYYY-MM-DD HH:MM:SS`` format."""
    try:
        return datetime.strptime(time_str, _DATETIME_FMT)
    except ValueError as exc:
        raise ValueError(
            f"Invalid datetime format '{time_str}'. "
            f"Expected format: YYYY-MM-DD HH:MM:SS"
        ) from exc


def _parse_date(date_str: str) -> datetime:
    """Parse a date string in ``YYYY-MM-DD`` format."""
    try:
        return datetime.strptime(date_str, _DATE_FMT)
    except ValueError as exc:
        raise ValueError(
            f"Invalid date format '{date_str}'. Expected format: YYYY-MM-DD"
        ) from exc


def _humanise_delta(total_seconds: int) -> str:
    """Convert a signed seconds delta into a human-readable relative string."""
    abs_seconds = abs(total_seconds)

    if abs_seconds < _SECONDS_PER_MINUTE:
        value, unit = abs_seconds, "second"
    elif abs_seconds < _SECONDS_PER_HOUR:
        value, unit = abs_seconds // _SECONDS_PER_MINUTE, "minute"
    elif abs_seconds < _SECONDS_PER_DAY:
        value, unit = abs_seconds // _SECONDS_PER_HOUR, "hour"
    else:
        value, unit = abs_seconds // _SECONDS_PER_DAY, "day"

    plural = "s" if value != 1 else ""
    if total_seconds >= 0:
        return f"{value} {unit}{plural} ago"
    return f"in {value} {unit}{plural}"


# ---------------------------------------------------------------------------
# Public async functions
# ---------------------------------------------------------------------------


@require_approval(AuthLevel.READ_AUTO, tool_name="time_current_time")
async def current_time(
    tz_name: str = _DEFAULT_TZ,
    fmt: str = _DEFAULT_FORMAT,
) -> str:
    """Get current date and time in the specified IANA timezone.

    Args:
        tz_name: IANA timezone name (default ``Asia/Jakarta``).
        fmt: ``strftime`` format string (default ``%Y-%m-%d %H:%M:%S``).

    Returns:
        Formatted datetime string.
    """
    tz = _resolve_tz(tz_name)
    now = datetime.now(tz)
    logger.debug("current_time", timezone=tz_name)
    return now.strftime(fmt)


@require_approval(AuthLevel.READ_AUTO, tool_name="time_convert_time")
async def convert_time(
    source_tz: str,
    target_tz: str,
    time_str: str,
) -> str:
    """Convert a datetime string from one IANA timezone to another.

    Args:
        source_tz: Source IANA timezone name.
        target_tz: Target IANA timezone name.
        time_str: Datetime string in ``YYYY-MM-DD HH:MM:SS`` format.

    Returns:
        Converted datetime string in the same format.
    """
    src = _resolve_tz(source_tz)
    tgt = _resolve_tz(target_tz)
    dt = _parse_datetime(time_str).replace(tzinfo=src)
    converted = dt.astimezone(tgt)
    logger.debug("convert_time", source=source_tz, target=target_tz)
    return converted.strftime(_DATETIME_FMT)


@require_approval(AuthLevel.READ_AUTO, tool_name="time_days_in_month")
async def days_in_month(date: str | None = None) -> int:
    """Return the number of days in the month for the given date.

    Args:
        date: Date string in ``YYYY-MM-DD`` format.
            Defaults to the current UTC date when *None*.

    Returns:
        Number of days in that month.
    """
    if date is None:
        now = datetime.now(timezone.utc)
        year, month = now.year, now.month
    else:
        dt = _parse_date(date)
        year, month = dt.year, dt.month
    logger.debug("days_in_month", date=date)
    return calendar.monthrange(year, month)[1]


@require_approval(AuthLevel.READ_AUTO, tool_name="time_relative_time")
async def relative_time(time: str) -> str:
    """Return a human-readable relative time string compared to *now* (UTC).

    Args:
        time: Datetime string in ``YYYY-MM-DD HH:MM:SS`` format (UTC).

    Returns:
        Relative string such as ``"3 hours ago"`` or ``"in 2 days"``.
    """
    dt = _parse_datetime(time).replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    delta_seconds = int((now - dt).total_seconds())
    result = _humanise_delta(delta_seconds)
    logger.debug("relative_time", time=time, result=result)
    return result


@require_approval(AuthLevel.READ_AUTO, tool_name="time_get_timestamp")
async def get_timestamp(time: str) -> int:
    """Return the Unix timestamp (seconds since epoch) for a UTC datetime.

    Args:
        time: Datetime string in ``YYYY-MM-DD HH:MM:SS`` format (UTC).

    Returns:
        Unix timestamp as an integer.
    """
    dt = _parse_datetime(time).replace(tzinfo=timezone.utc)
    logger.debug("get_timestamp", time=time)
    return int(dt.timestamp())


@require_approval(AuthLevel.READ_AUTO, tool_name="time_get_week_year")
async def get_week_year(date: str | None = None) -> dict[str, int]:
    """Return week number, ISO week number, and year for a date.

    Args:
        date: Date string in ``YYYY-MM-DD`` format.
            Defaults to the current UTC date when *None*.

    Returns:
        Dictionary with keys ``week``, ``isoWeek``, and ``year``.
    """
    if date is None:
        dt = datetime.now(timezone.utc).date()
    else:
        dt = _parse_date(date).date()

    iso_cal = dt.isocalendar()
    week = int(dt.strftime("%W"))
    logger.debug("get_week_year", date=date)
    return {
        "week": week,
        "isoWeek": iso_cal[1],
        "year": iso_cal[0],
    }


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


def register_tools(mcp: FastMCP) -> None:
    """Register all time-related tools with the FastMCP server."""
    mcp.tool(name="time_current_time")(current_time)
    mcp.tool(name="time_convert_time")(convert_time)
    mcp.tool(name="time_days_in_month")(days_in_month)
    mcp.tool(name="time_relative_time")(relative_time)
    mcp.tool(name="time_get_timestamp")(get_timestamp)
    mcp.tool(name="time_get_week_year")(get_week_year)
