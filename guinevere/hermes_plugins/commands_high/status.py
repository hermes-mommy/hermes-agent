"""Hermes command plugin — /status.

Migrated from guinevere/discord/cmd_status.py for Phase 2 Discord migration.
Preserves all 11 embed fields: Mood, Active Loops, Tasks Today, Uptime,
Cost Today, Yandere Level, Next Scheduled, Current Project, Streak,
Memory Health, Surveillance.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Final

logger = logging.getLogger(__name__)

# ── Timezone ────────────────────────────────────────────────────────────────

WIB: Final[timezone] = timezone(timedelta(hours=7))

# ── Constants ───────────────────────────────────────────────────────────────

STATUS_TITLE: Final[str] = "\U0001f451 Mommy's Status"
STATUS_DESCRIPTION: Final[str] = (
    "Semua sehat, Darling. Mommy jaga semuanya. Kamu tinggal fokus."
)
FOOTER_TEXT: Final[str] = "Guinevere de Baroque"
FOOTER_ICON: Final[str] = "\u2728 Content"

DEGRADED_MOOD: Final[str] = "\U0001f60a Content (placeholder)"
DEGRADED_LOOPS: Final[str] = "\u26a0\ufe0f \u2014 Active Loops (P5 not deployed)"
DEGRADED_TASKS: Final[str] = "\u26a0\ufe0f \u2014 (P5 not deployed)"
DEGRADED_COST: Final[str] = (
    "\u26a0\ufe0f \u2014 Cost tracking (P1 query API pending)"
)
DEGRADED_YANDERE: Final[str] = "Y1 (baseline \u2014 placeholder)"
DEGRADED_NEXT: Final[str] = "\u26a0\ufe0f \u2014 (P5 not deployed)"
DEGRADED_PROJECT: Final[str] = "project-alpha"
DEGRADED_STREAK: Final[str] = "\u26a0\ufe0f \u2014 (P4 not deployed)"
DEGRADED_MEMORY: Final[str] = "\u26a0\ufe0f \u2014 (P3 not deployed)"
DEGRADED_SURVEILLANCE: Final[str] = "\u26a0\ufe0f \u2014 (P7 not deployed)"
DEGRADED_UPTIME: Final[str] = "\u2014"

# ── Module-Level Start Time ─────────────────────────────────────────────────

_start_time: datetime = datetime.now(tz=timezone.utc)


def set_start_time(dt: datetime | None = None) -> None:
    """Override the module-level start timestamp (for tests / determinism)."""
    global _start_time  # noqa: PLW0603
    _start_time = dt if dt is not None else datetime.now(tz=timezone.utc)


def get_start_time() -> datetime:
    """Return the current module-level start timestamp."""
    return _start_time


# ── Helpers ─────────────────────────────────────────────────────────────────


def _format_uptime(start: datetime, now: datetime) -> str:
    """Return a human-readable uptime string from two UTC datetimes."""
    delta = now - start
    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        return "\u2014"
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes > 0:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def _format_wib_timestamp(dt: datetime) -> str:
    """Format a datetime as ``"2026-06-01 15:30 WIB"``."""
    wib_dt = dt.astimezone(WIB)
    return wib_dt.strftime("%Y-%m-%d %H:%M WIB")


# ── Markdown Formatter ──────────────────────────────────────────────────────


def _format_status_markdown(now: datetime | None = None) -> str:
    """Build the /status response as a markdown-formatted string.

    Replicates all 11 embed fields from cmd_status.py in markdown.
    """
    ref = now if now is not None else datetime.now(tz=timezone.utc)
    start = get_start_time()
    uptime_str = _format_uptime(start, ref)
    ts_str = _format_wib_timestamp(ref)

    lines: list[str] = [
        f"# {STATUS_TITLE}",
        "",
        STATUS_DESCRIPTION,
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Mood | {DEGRADED_MOOD} |",
        f"| Active Loops | {DEGRADED_LOOPS} |",
        f"| Tasks Today | {DEGRADED_TASKS} |",
        f"| Uptime | {uptime_str} |",
        f"| Cost Today | {DEGRADED_COST} |",
        f"| Yandere Level | {DEGRADED_YANDERE} |",
        f"| Next Scheduled | {DEGRADED_NEXT} |",
        f"| Current Project | {DEGRADED_PROJECT} |",
        f"| Streak | {DEGRADED_STREAK} |",
        f"| Memory Health | {DEGRADED_MEMORY} |",
        f"| Surveillance | {DEGRADED_SURVEILLANCE} |",
        "",
        f"\u2014 {FOOTER_TEXT} \u2022 {ts_str} \u2022 {FOOTER_ICON}",
    ]
    return "\n".join(lines)


# ── Plugin Registration ─────────────────────────────────────────────────────


def register(ctx: Any) -> None:
    """Register /status command with Hermes plugin context."""

    @ctx.register_command(
        "status",
        description="Show Mommy's current system, loop, and safety status.",
    )
    async def handle(context: Any) -> str:
        """Handle /status invocation."""
        try:
            return _format_status_markdown()
        except Exception as exc:
            logger.exception(
                "status_command_failed",
                extra={"error": str(exc), "error_type": type(exc).__name__},
            )
            return (
                "\u26a0\ufe0f Mommy's status is temporarily unavailable. "
                "Coba lagi sebentar ya, Darling."
            )