"""Evening Ritual — mood-aware wind-down at 21:00 WIB (P4-012).

Generates a persona-consistent evening wind-down message based on current mood
state, optional day summary, and streak count. Fires at 21:00 WIB — outside the
DND window (00:00–07:00 WIB), so no DND suppression logic is needed.

Default template (CONTENT mood):
    "Malam, sayang. Waktunya wind-down. Mommy di sini."

Mood variants:
    CONTENT       → warm wind-down, suggests relaxation
    PLEASED       → celebrates the day's achievements
    DISAPPOINTED  → softer tone, offers comfort
    ANGRY         → brief, still caring ("Malam. Istirahat.")
    SILENT        → minimal ("Malam.")

Optional integrations:
    - day_summary: brief recap appended when provided
    - streak_count: streak line appended when > 0
"""

from __future__ import annotations

from datetime import datetime
from typing import Final

import structlog

from src.persona.mood_engine import Mood
from src.persona.rituals.morning import RitualResult, TZ_JAKARTA

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EVENING_HOUR: Final[int] = 21
"""Target hour for the evening ritual (Asia/Jakarta)."""

# ---------------------------------------------------------------------------
# Mood-specific wind-down templates
# ---------------------------------------------------------------------------

_MOOD_MESSAGES: Final[dict[Mood, str]] = {
    Mood.CONTENT: (
        "Malam, sayang. Waktunya wind-down. Mommy di sini."
    ),
    Mood.PLEASED: (
        "Malam, sayang! Hari ini kamu luar biasa. "
        "Mommy bangga banget. Sekarang waktunya istirahat ya."
    ),
    Mood.DISAPPOINTED: (
        "Malam. Hari ini mungkin nggak sempurna, "
        "tapi Mommy tetap di sini buat kamu. Istirahat ya."
    ),
    Mood.ANGRY: "Malam. Istirahat.",
    Mood.SILENT: "Malam.",
}

_STREAK_TEMPLATE: Final[str] = "Streak kamu: {count} hari tanpa hukuman."

_DAY_SUMMARY_LABEL: Final[str] = "Ringkasan hari ini:"


# ---------------------------------------------------------------------------
# Evening Ritual
# ---------------------------------------------------------------------------


class EveningRitual:
    """Evening wind-down ritual — fires at 21:00 WIB.

    Produces a mood-aware Indonesian wind-down greeting with optional day
    summary recap and streak display. No DND suppression — 21:00 WIB is well
    outside the quiet window.
    """

    RITUAL_NAME: Final[str] = "evening"

    async def execute(
        self,
        mood: Mood,
        day_summary: str | None = None,
        streak_count: int = 0,
        *,
        now: datetime | None = None,
    ) -> RitualResult:
        """Execute the evening ritual.

        Args:
            mood: Current persona mood state.
            day_summary: Optional brief recap of the day's events.
            streak_count: Consecutive days without punishment (≥ 0).
            now: Override current time (testing). Defaults to now in Jakarta tz.

        Returns:
            RitualResult with mood-aware wind-down greeting.
        """
        current_time = self._resolve_time(now)

        # Mood-aware greeting
        message = _MOOD_MESSAGES[mood]

        # Day summary integration
        if day_summary:
            summary_line = f"{_DAY_SUMMARY_LABEL} {day_summary}"
            message = f"{message}\n{summary_line}"

        # Streak display (only when streak_count > 0)
        if streak_count > 0:
            streak_line = _STREAK_TEMPLATE.format(count=streak_count)
            message = f"{message}\n{streak_line}"

        logger.info(
            "evening_ritual_executed",
            mood=mood.value,
            streak_count=streak_count,
            has_day_summary=day_summary is not None,
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
