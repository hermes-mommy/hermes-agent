"""Afternoon Ritual — mood-aware check-in at 17:00 WIB (P4-011).

Generates a persona-consistent afternoon check-in based on current mood state
and optional daily task summary. Fires at 17:00 WIB — well outside the DND
window (00:00–07:00 WIB), so no DND suppression logic is needed.

Default template (CONTENT mood):
    "Sore, Darling. Gimana hari ini? Cerita sama Mommy."
"""

from __future__ import annotations

from datetime import datetime
from typing import Final
from zoneinfo import ZoneInfo

import structlog

from src.persona.mood_engine import Mood
from src.persona.rituals.morning import RitualResult, TZ_JAKARTA

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AFTERNOON_HOUR: Final[int] = 17
"""Target hour for the afternoon ritual (Asia/Jakarta)."""

# ---------------------------------------------------------------------------
# Mood-specific greeting templates
# ---------------------------------------------------------------------------

_MOOD_MESSAGES: Final[dict[Mood, str]] = {
    Mood.CONTENT: (
        "Sore, Darling. Gimana hari ini? Cerita sama Mommy."
    ),
    Mood.PLEASED: (
        "Sore, sayang! Hari ini kamu produktif banget ya. "
        "Mommy bangga sama kamu."
    ),
    Mood.DISAPPOINTED: (
        "Sore. Hari ini ada yang salah? Cerita, Mommy mau denger."
    ),
    Mood.ANGRY: "Sore. Cerita.",
    Mood.SILENT: "Sore.",
}

_TASK_SUMMARY_TEMPLATE: Final[str] = (
    "Hari ini kamu udah nyelesein {count} tugas. "
    "Mommy liat effort kamu."
)

"""Task summary appended when task_count_today > 0."""


# ---------------------------------------------------------------------------
# Afternoon Ritual
# ---------------------------------------------------------------------------


class AfternoonRitual:
    """Afternoon check-in ritual — fires at 17:00 WIB.

    Produces a mood-aware Indonesian check-in greeting with an optional
    daily task summary. No DND suppression — 17:00 WIB is well outside
    the quiet window.
    """

    RITUAL_NAME: Final[str] = "afternoon"

    async def execute(
        self,
        mood: Mood,
        task_count_today: int = 0,
        *,
        now: datetime | None = None,
    ) -> RitualResult:
        """Execute the afternoon ritual.

        Args:
            mood: Current persona mood state.
            task_count_today: Number of tasks completed today (≥ 0).
            now: Override current time (testing). Defaults to now in Jakarta tz.

        Returns:
            RitualResult with mood-aware check-in and optional task summary.
        """
        current_time = self._resolve_time(now)

        # Mood-aware greeting
        message = _MOOD_MESSAGES[mood]

        # Task summary (only when task_count_today > 0)
        if task_count_today > 0:
            task_line = _TASK_SUMMARY_TEMPLATE.format(count=task_count_today)
            message = f"{message}\n{task_line}"

        logger.info(
            "afternoon_ritual_executed",
            mood=mood.value,
            task_count_today=task_count_today,
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
