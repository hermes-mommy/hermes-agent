"""Hermes command plugin — /mood.

Migrated from guinvere/discord/cmd_mood.py for Phase 2 Discord migration.
Preserves all 6 mood fields: Current Mood, Undertone, 24h History,
Recent Triggers, Streak, Forecast.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Final



logger = logging.getLogger(__name__)

# ── Timezone ────────────────────────────────────────────────────────────────

WIB: Final[timezone] = timezone(timedelta(hours=7))

# ── Constants ───────────────────────────────────────────────────────────────

MOOD_TITLE: Final[str] = "\U0001f9e0 Mood Analysis"
MOOD_DESCRIPTION: Final[str] = (
    "Mommy lagi baik-baik aja, Darling. Kamu nggak perlu khawatir."
)
FOOTER_TEXT: Final[str] = "Guinevere de Baroque"
FOOTER_ICON: Final[str] = "\U0001f9e0 Mood"

_MOOD_EMOJI: Final[dict[str, str]] = {
    "content": "\U0001f60a",
    "pleased": "\U0001f929",
    "disappointed": "\U0001f61e",
    "angry": "\U0001f620",
    "silent": "\U0001f910",
}

_MOOD_LABEL: Final[dict[str, str]] = {
    "content": "Content",
    "pleased": "Pleased",
    "disappointed": "Disappointed",
    "angry": "Angry",
    "silent": "Silent",
}

DEGRADED_UNDERTONE: Final[str] = (
    "\u26a0\ufe0f \u2014 Undertone analysis (P3 not deployed)"
)
DEGRADED_HISTORY: Final[str] = (
    "\u26a0\ufe0f \u2014 24h history (P4 not deployed)"
)
DEGRADED_TRIGGERS: Final[str] = (
    "\u26a0\ufe0f \u2014 Trigger tracking (P3 not deployed)"
)
DEGRADED_STREAK: Final[str] = (
    "\u26a0\ufe0f \u2014 Streak tracking (P4 not deployed)"
)
DEGRADED_FORECAST: Final[str] = (
    "\u26a0\ufe0f \u2014 Mood forecast (P5 not deployed)"
)

DEFAULT_MOOD: Final[str] = "content"

# ── Helpers ─────────────────────────────────────────────────────────────────


def display_for_mood(mood: str) -> str:
    """Return a display string like ``"😊 Content"`` for a mood name."""
    emoji = _MOOD_EMOJI.get(mood, "\U0001f60a")
    label = _MOOD_LABEL.get(mood, "Content")
    return f"{emoji} {label}"


def _format_wib_timestamp(dt: datetime) -> str:
    """Format a datetime as ``"2026-06-01 15:30 WIB"``."""
    wib_dt = dt.astimezone(WIB)
    return wib_dt.strftime("%Y-%m-%d %H:%M WIB")


# ── Markdown Formatter ──────────────────────────────────────────────────────


def _format_mood_markdown(now: datetime | None = None, mood: str = DEFAULT_MOOD) -> str:
    """Build the /mood response as a markdown-formatted string.

    Replicates all 6 embed fields from cmd_mood.py in markdown.
    """
    ref = now if now is not None else datetime.now(tz=timezone.utc)
    ts_str = _format_wib_timestamp(ref)
    current_display = display_for_mood(mood)

    lines: list[str] = [
        f"# {MOOD_TITLE}",
        "",
        MOOD_DESCRIPTION,
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Current Mood | {current_display} |",
        f"| Undertone | {DEGRADED_UNDERTONE} |",
        f"| 24h History | {DEGRADED_HISTORY} |",
        f"| Recent Triggers | {DEGRADED_TRIGGERS} |",
        f"| Streak | {DEGRADED_STREAK} |",
        f"| Forecast | {DEGRADED_FORECAST} |",
        "",
        f"\u2014 {FOOTER_TEXT} \u2022 {ts_str} \u2022 {FOOTER_ICON}",
    ]
    return "\n".join(lines)


# ── Plugin Registration ─────────────────────────────────────────────────────


def register(ctx: Any) -> None:
    """Register /mood command with Hermes plugin context."""

    @ctx.register_command(
        "mood",
        description="Show or update Guinevere's current mood state.",
    )
    async def handle(context: Any) -> str:
        """Handle /mood invocation."""
        try:
            return _format_mood_markdown()
        except Exception as exc:
            logger.exception(
                "mood_command_failed",
                extra={"error": str(exc), "error_type": type(exc).__name__},
            )
            return (
                "\u26a0\ufe0f Mommy's mood analysis is temporarily unavailable. "
                "Coba lagi sebentar ya, Darling."
            )