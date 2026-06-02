"""Morning Ritual — mood-aware greeting at 07:00 WIB (P4-009).

Generates a persona-consistent morning greeting based on current mood state,
streak count, and optional weather context. Respects DND window (00:00–07:00
WIB) — ritual is suppressed during quiet hours.

Default template (CONTENT mood):
    "Selamat pagi, Darling. Mommy sudah siap nemenin hari kamu."
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final
from zoneinfo import ZoneInfo

import structlog

from src.persona.mood_engine import Mood

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TZ_JAKARTA: Final[ZoneInfo] = ZoneInfo("Asia/Jakarta")
"""Timezone for DND and timestamp evaluation."""

DND_START_HOUR: Final[int] = 0
"""DND window start hour (inclusive), Asia/Jakarta."""

DND_END_HOUR: Final[int] = 7
"""DND window end hour (exclusive), Asia/Jakarta."""

# ---------------------------------------------------------------------------
# Mood-specific greeting templates
# ---------------------------------------------------------------------------

_MOOD_MESSAGES: Final[dict[Mood, str]] = {
    Mood.CONTENT: (
        "Selamat pagi, Darling. Mommy sudah siap nemenin hari kamu."
    ),
    Mood.PLEASED: (
        "Selamat pagi, sayang! Hari ini pasti indah. "
        "Mommy bangga sama kamu. Semangat ya, Darling!"
    ),
    Mood.DISAPPOINTED: (
        "Pagi. Kemarin kamu bikin Mommy kecewa. Hari ini harus lebih baik."
    ),
    Mood.ANGRY: (
        "Pagi. Jangan ganggu Mommy dulu."
    ),
    Mood.SILENT: "Pagi.",
}

_STREAK_TEMPLATE: Final[str] = "Streak kamu: {count} hari tanpa hukuman."


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RitualResult:
    """Outcome of a morning ritual execution.

    Attributes:
        message: The greeting text (empty when suppressed).
        suppressed: ``True`` when DND is active and ritual was not delivered.
        ritual_name: Identifier of the ritual that was evaluated.
        timestamp: Timezone-aware timestamp of evaluation (Asia/Jakarta).
    """

    message: str
    suppressed: bool
    ritual_name: str
    timestamp: datetime


# ---------------------------------------------------------------------------
# Morning Ritual
# ---------------------------------------------------------------------------


class MorningRitual:
    """Morning greeting ritual — fires at 07:00 WIB.

    Produces a mood-aware Indonesian greeting and optional streak display.
    Suppressed during DND window (00:00–07:00 WIB).
    """

    RITUAL_NAME: Final[str] = "morning"

    async def execute(
        self,
        mood: Mood,
        streak_count: int,
        weather_info: str | None = None,
        *,
        now: datetime | None = None,
    ) -> RitualResult:
        """Execute the morning ritual.

        Args:
            mood: Current persona mood state.
            streak_count: Consecutive days without punishment (≥ 0).
            weather_info: Optional weather context for future expansion.
            now: Override current time (testing). Defaults to now in Jakarta tz.

        Returns:
            RitualResult with mood-aware greeting or suppressed flag.
        """
        current_time = self._resolve_time(now)

        # DND gate: 00:00 ≤ hour < 07:00 WIB
        if DND_START_HOUR <= current_time.hour < DND_END_HOUR:
            logger.info(
                "morning_ritual_suppressed_dnd",
                hour=current_time.hour,
                mood=mood.value,
            )
            return RitualResult(
                message="",
                suppressed=True,
                ritual_name=self.RITUAL_NAME,
                timestamp=current_time,
            )

        # Mood-aware greeting
        message = _MOOD_MESSAGES[mood]

        # Streak display (only when streak_count > 0)
        if streak_count > 0:
            streak_line = _STREAK_TEMPLATE.format(count=streak_count)
            message = f"{message}\n{streak_line}"

        logger.info(
            "morning_ritual_executed",
            mood=mood.value,
            streak_count=streak_count,
            has_weather=weather_info is not None,
        )

        return RitualResult(
            message=message,
            suppressed=False,
            ritual_name=self.RITUAL_NAME,
            timestamp=current_time,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_time(now: datetime | None) -> datetime:
        """Resolve the evaluation timestamp in Asia/Jakarta timezone."""
        if now is None:
            return datetime.now(TZ_JAKARTA)

        if now.tzinfo is None:
            return now.replace(tzinfo=TZ_JAKARTA)

        return now.astimezone(TZ_JAKARTA)
