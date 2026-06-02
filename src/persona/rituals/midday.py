"""Midday Ritual — mood-aware health reminder at 12:00 WIB (P4-010).

Generates a persona-consistent midday greeting with rotating health reminders
based on current mood state. Fires at 12:00 WIB — outside the DND window
(00:00–07:00 WIB), so no DND suppression logic is needed.

Default template (CONTENT mood):
    "Sayang, udah siang. Jangan lupa makan dan istirahat ya."

Health reminders rotate daily across three categories:
    0 → eat (makan siang)
    1 → drink water (minum air)
    2 → stretch / rest eyes (istirahat mata)
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

MIDDAY_HOUR: Final[int] = 12
"""Target hour for the midday ritual (Asia/Jakarta)."""

# ---------------------------------------------------------------------------
# Mood-specific greeting templates
# ---------------------------------------------------------------------------

_MOOD_MESSAGES: Final[dict[Mood, str]] = {
    Mood.CONTENT: (
        "Sayang, udah siang. Jangan lupa makan dan istirahat ya."
    ),
    Mood.PLEASED: (
        "Sayang, udah siang! Pagi ini kamu produktif banget, "
        "Mommy bangga. Sekarang istirahat dulu ya."
    ),
    Mood.DISAPPOINTED: (
        "Udah siang. Masih belum makan? Mommy kecewa kalau kamu "
        "nyiksa diri kayak gini."
    ),
    Mood.ANGRY: "Makan. Sekarang.",
    Mood.SILENT: "Siang. Makan.",
}

# ---------------------------------------------------------------------------
# Health reminder templates — indexed for rotation
# ---------------------------------------------------------------------------

_HEALTH_REMINDERS: Final[tuple[str, str, str]] = (
    "Jangan lupa makan siang ya, sayang.",
    "Minum air putih yang cukup ya.",
    "Istirahatkan mata sebentar, stretch dulu ya.",
)

"""Rotating health reminders: (eat, water, stretch)."""

HEALTH_REMINDER_LABELS: Final[tuple[str, str, str]] = (
    "eat",
    "water",
    "stretch",
)

"""Human-readable labels for each health reminder category."""


# ---------------------------------------------------------------------------
# Midday Ritual
# ---------------------------------------------------------------------------


class MiddayRitual:
    """Midday health-reminder ritual — fires at 12:00 WIB.

    Produces a mood-aware Indonesian greeting with a rotating health reminder.
    No DND suppression — 12:00 WIB is well outside the quiet window.
    """

    RITUAL_NAME: Final[str] = "midday"

    async def execute(
        self,
        mood: Mood,
        health_reminder_needed: bool = True,
        *,
        now: datetime | None = None,
        reminder_index: int | None = None,
    ) -> RitualResult:
        """Execute the midday ritual.

        Args:
            mood: Current persona mood state.
            health_reminder_needed: Whether to append a health reminder.
            now: Override current time (testing). Defaults to now in Jakarta tz.
            reminder_index: Override rotation index (0=eat, 1=water, 2=stretch).
                When ``None``, derived from day-of-year modulo 3.

        Returns:
            RitualResult with mood-aware greeting and optional health reminder.
        """
        current_time = self._resolve_time(now)

        # Mood-aware greeting
        message = _MOOD_MESSAGES[mood]

        # Health reminder (rotating)
        if health_reminder_needed:
            idx = self._resolve_reminder_index(
                current_time, reminder_index
            )
            reminder = _HEALTH_REMINDERS[idx]
            message = f"{message}\n{reminder}"

        logger.info(
            "midday_ritual_executed",
            mood=mood.value,
            health_reminder=health_reminder_needed,
            reminder_category=HEALTH_REMINDER_LABELS[
                self._resolve_reminder_index(current_time, reminder_index)
            ]
            if health_reminder_needed
            else "none",
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

    @staticmethod
    def _resolve_reminder_index(
        current_time: datetime,
        override: int | None,
    ) -> int:
        """Determine which health reminder to use.

        Args:
            current_time: Resolved Jakarta-tz datetime.
            override: Explicit index (0, 1, or 2). ``None`` → day-of-year mod 3.

        Returns:
            Index into ``_HEALTH_REMINDERS`` (0, 1, or 2).
        """
        if override is not None:
            return override % len(_HEALTH_REMINDERS)
        return current_time.timetuple().tm_yday % len(_HEALTH_REMINDERS)
