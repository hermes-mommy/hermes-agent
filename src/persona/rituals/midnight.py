"""Midnight Ritual — internal self-evaluation at 00:00 WIB (P4-013).

Performs a silent self-evaluation of the day's activity: mood transitions,
punishments, rewards, and streak status. This ritual is **never** sent to
Discord — it is internal-only and produces structured log data via structlog.

DND window (00:00–07:00 WIB) is active at midnight, so the ritual is always
suppressed from external output. Evaluation data is logged regardless.

Message template (internal log only):
    "Self-evaluation complete. Silent mode until morning."
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Final

import structlog

from src.persona.rituals.morning import RitualResult, TZ_JAKARTA

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MIDNIGHT_HOUR: Final[int] = 0
"""Target hour for the midnight ritual (Asia/Jakarta)."""

_EVALUATION_MESSAGE: Final[str] = (
    "Self-evaluation complete. Silent mode until morning."
)
"""Internal-only evaluation message (never sent to Discord)."""


# ---------------------------------------------------------------------------
# Self-evaluation data extraction helpers
# ---------------------------------------------------------------------------


def _extract_count(data: dict[str, Any], list_key: str, count_key: str) -> int:
    """Extract a count from self-evaluation data.

    Checks *list_key* first (uses ``len()``), then *count_key*, then 0.

    Args:
        data: The self-evaluation data dictionary.
        list_key: Key that may hold a list (counted via ``len``).
        count_key: Key that may hold a direct integer count.

    Returns:
        Non-negative integer count.
    """
    value = data.get(list_key)
    if isinstance(value, (list, tuple)):
        return len(value)

    value = data.get(count_key)
    if isinstance(value, int):
        return max(value, 0)

    return 0


# ---------------------------------------------------------------------------
# Midnight Ritual
# ---------------------------------------------------------------------------


class MidnightRitual:
    """Midnight self-evaluation ritual — fires at 00:00 WIB.

    Performs internal-only self-evaluation of the day's activity.
    Always suppressed (DND 00:00–07:00 WIB) — evaluation data is logged
    via structlog but never delivered to Discord.
    """

    RITUAL_NAME: Final[str] = "midnight"

    async def execute(
        self,
        self_evaluation_data: dict[str, Any] | None = None,
        *,
        now: datetime | None = None,
    ) -> RitualResult:
        """Execute the midnight self-evaluation ritual.

        Args:
            self_evaluation_data: Optional dictionary containing today's
                activity data. Recognised keys:

                - ``mood_transitions`` (list): list of mood transition events.
                - ``mood_transitions_count`` (int): direct count fallback.
                - ``punishments`` (list): list of punishment events.
                - ``punishments_count`` (int): direct count fallback.
                - ``rewards`` (list): list of reward events.
                - ``rewards_count`` (int): direct count fallback.
                - ``streak_count`` (int): current streak days (≥ 0).

                When ``None``, all counts default to 0.

            now: Override current time (testing). Defaults to now in Jakarta tz.

        Returns:
            RitualResult with ``suppressed=True`` (DND active at midnight).
            The ``message`` field contains the internal evaluation template
            for logging; it must **not** be delivered to Discord.
        """
        current_time = self._resolve_time(now)
        eval_data = self_evaluation_data or {}

        # Extract evaluation counts
        mood_transitions_count = _extract_count(
            eval_data, "mood_transitions", "mood_transitions_count"
        )
        punishments_count = _extract_count(
            eval_data, "punishments", "punishments_count"
        )
        rewards_count = _extract_count(
            eval_data, "rewards", "rewards_count"
        )
        streak_count = eval_data.get("streak_count", 0)
        if not isinstance(streak_count, int):
            streak_count = 0
        streak_count = max(streak_count, 0)

        # Log evaluation summary (internal only)
        logger.info(
            "midnight_ritual_self_evaluation",
            ritual_name=self.RITUAL_NAME,
            mood_transitions_count=mood_transitions_count,
            punishments_count=punishments_count,
            rewards_count=rewards_count,
            streak_count=streak_count,
            suppressed=True,
            hour=current_time.hour,
        )

        return RitualResult(
            message=_EVALUATION_MESSAGE,
            suppressed=True,
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
