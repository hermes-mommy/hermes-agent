"""Streak tracking — consecutive days without punishment.

Tracks Faiz's streak of days without triggering any punishment level
(L1–L5).  The streak persists across safe_mode activations and distress
events; only an explicit punishment application resets it to zero.

Milestone thresholds:
  7 days   → week
  14 days  → fortnight
  30 days  → month
  90 days  → quarter
  365 days → year

The streak count is displayed in the /mood command output.  The 30-day
milestone is stored in faiz_profile per PersonaDoc v3.0.

Optional persistence uses the existing PersonaState table via an async
SQLAlchemy session.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Final

import structlog

from src.memory.models import PersonaState

logger = structlog.get_logger()

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class StreakError(Exception):
    """Base exception for streak tracking errors."""


class StreakPersistenceError(StreakError):
    """Raised when streak persistence operations fail."""


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MILESTONE_THRESHOLDS: Final[list[int]] = [7, 14, 30, 90, 365]
"""Ordered milestone thresholds in days."""

MILESTONE_LABELS: Final[dict[int, str]] = {
    7: "week",
    14: "fortnight",
    30: "month",
    90: "quarter",
    365: "year",
}
"""Human-readable labels for each milestone threshold."""

STREAK_STATE_KEY: Final[str] = "streak_count"
"""PersonaState.state_key used for streak persistence."""


def _safe_int(value: object, default: int = 0) -> int:
    """Convert an arbitrary JSON value to int, returning *default* on failure."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


# ---------------------------------------------------------------------------
# StreakTracker
# ---------------------------------------------------------------------------


@dataclass
class StreakTracker:
    """Tracks consecutive days without punishment.

    The streak increments daily when no punishment (L1–L5) is applied.
    It persists across safe_mode / distress events — only punishment
    resets it.

    Usage::

        tracker = StreakTracker()
        tracker.increment()        # +1 day
        tracker.get_count()        # 1
        tracker.get_milestone()    # None (below 7)
        tracker.get_display_text() # "Streak: 1 day (6 days to week milestone)"
        tracker.reset()            # punishment applied → back to 0
    """

    _count: int = field(default=0, repr=False)
    _last_increment: datetime | None = field(default=None, repr=False)
    _highest_milestone_reached: int = field(default=0, repr=False)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def increment(self) -> int:
        """Increment the streak count by one day.

        Returns:
            The new streak count after incrementing.
        """
        self._count += 1
        self._last_increment = datetime.now(timezone.utc)
        logger.info("streak_incremented", count=self._count)

        milestone = self.get_milestone()
        if milestone is not None and milestone > self._highest_milestone_reached:
            self._highest_milestone_reached = milestone
            logger.info(
                "streak_milestone_reached",
                milestone=milestone,
                label=MILESTONE_LABELS.get(milestone, "unknown"),
            )

        return self._count

    def reset(self) -> int:
        """Reset the streak to zero.

        Called when any punishment (L1–L5) is applied.  Returns the
        previous count before reset so callers can log or reward it.

        Returns:
            The streak count that was active before the reset.
        """
        previous = self._count
        self._count = 0
        self._last_increment = None
        self._highest_milestone_reached = 0
        logger.info("streak_reset", previous_count=previous)
        return previous

    def get_count(self) -> int:
        """Return the current streak count in days."""
        return self._count

    def get_milestone(self) -> int | None:
        """Return the highest milestone threshold reached, or *None*.

        Returns *None* when the streak is below the lowest threshold (7).
        """
        reached: int | None = None
        for threshold in MILESTONE_THRESHOLDS:
            if self._count >= threshold:
                reached = threshold
        return reached

    def is_milestone_reached(self, threshold: int) -> bool:
        """Check whether a specific milestone threshold has been reached.

        Args:
            threshold: One of the valid milestone thresholds
                       (7, 14, 30, 90, or 365).

        Raises:
            StreakError: If *threshold* is not a valid milestone value.
        """
        if threshold not in MILESTONE_LABELS:
            raise StreakError(
                f"Invalid milestone threshold {threshold}. "
                f"Valid thresholds: {sorted(MILESTONE_LABELS.keys())}"
            )
        return self._count >= threshold

    def get_display_text(self) -> str:
        """Return human-readable streak info for the /mood command.

        Examples::

            "Streak: 0 days — no streak active."
            "Streak: 3 days (4 days to week milestone)"
            "Streak: 7 days (week milestone reached!)"
            "Streak: 45 days (month milestone reached!)"
            "Streak: 400 days (year milestone reached!)"
        """
        if self._count == 0:
            return "Streak: 0 days — no streak active."

        milestone = self.get_milestone()
        if milestone is not None:
            label = MILESTONE_LABELS[milestone]
            return f"Streak: {self._count} days ({label} milestone reached!)"

        # Below all milestones — show progress toward the next one
        next_threshold: int | None = None
        for t in MILESTONE_THRESHOLDS:
            if self._count < t:
                next_threshold = t
                break

        if next_threshold is not None:
            remaining = next_threshold - self._count
            next_label = MILESTONE_LABELS[next_threshold]
            day_word = "day" if self._count == 1 else "days"
            return (
                f"Streak: {self._count} {day_word} "
                f"({remaining} days to {next_label} milestone)"
            )

        return f"Streak: {self._count} days"

    # ------------------------------------------------------------------
    # Optional async persistence via PersonaState
    # ------------------------------------------------------------------

    async def save(self, session: AsyncSession, updated_by: str = "streak_tracker") -> None:
        """Persist the current streak state to the PersonaState table.

        Uses an upsert pattern: if a row with ``state_key = 'streak_count'``
        exists it is updated; otherwise a new row is inserted.

        Args:
            session: An active async SQLAlchemy session.
            updated_by: Identifier recorded in the ``updated_by`` column.

        Raises:
            StreakPersistenceError: On any database failure.
        """
        from sqlalchemy import select

        state_value: dict[str, object] = {
            "count": self._count,
            "last_updated": (
                self._last_increment.isoformat()
                if self._last_increment is not None
                else None
            ),
            "highest_milestone": self._highest_milestone_reached,
        }

        try:
            # Attempt to find existing row
            stmt = select(PersonaState).where(
                PersonaState.state_key == STREAK_STATE_KEY
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing is not None:
                existing.state_value = state_value
                existing.updated_by = updated_by
                existing.updated_at = datetime.now(timezone.utc)
            else:
                import uuid as _uuid

                new_row = PersonaState(
                    id=_uuid.uuid4(),
                    state_key=STREAK_STATE_KEY,
                    state_value=state_value,
                    updated_by=updated_by,
                )
                session.add(new_row)

            await session.flush()
            logger.info("streak_saved", count=self._count)
        except StreakPersistenceError:
            raise
        except Exception as exc:
            raise StreakPersistenceError(
                f"Failed to persist streak state: {exc}"
            ) from exc

    async def load(self, session: AsyncSession) -> None:
        """Load streak state from the PersonaState table.

        If no record exists the streak remains at its current value
        (default 0).  Partial or corrupted data resets the streak.

        Args:
            session: An active async SQLAlchemy session.

        Raises:
            StreakPersistenceError: On any database failure.
        """
        from sqlalchemy import select

        try:
            stmt = select(PersonaState).where(
                PersonaState.state_key == STREAK_STATE_KEY
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()

            if row is None:
                logger.info("streak_load_no_record")
                return

            value = row.state_value
            if isinstance(value, dict) and "count" in value:
                raw_count: object = value["count"]
                loaded_count: int = _safe_int(raw_count)
                self._count = max(loaded_count, 0)
                raw_milestone: object = value.get("highest_milestone", 0)
                self._highest_milestone_reached = _safe_int(raw_milestone)
                last_updated_raw = value.get("last_updated")
                if isinstance(last_updated_raw, str):
                    self._last_increment = datetime.fromisoformat(
                        last_updated_raw
                    )
                else:
                    self._last_increment = None
                logger.info("streak_loaded", count=self._count)
            else:
                logger.warning("streak_load_corrupted", resetting=True)
                self._count = 0
                self._highest_milestone_reached = 0
                self._last_increment = None
        except StreakPersistenceError:
            raise
        except Exception as exc:
            raise StreakPersistenceError(
                f"Failed to load streak state: {exc}"
            ) from exc
