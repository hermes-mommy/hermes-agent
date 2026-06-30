"""Mood State Persistence Layer — Repository for mood CRUD operations (P4-002).

Manages mood state persistence using existing persona schema tables
(PersonaState, MoodHistory). All DB errors are wrapped in
MoodPersistenceError subclasses — no bare exceptions leak.

This module works with raw mood strings only; it does NOT depend on
mood_engine.py (P4-001).

PersonaPlugin Integration:
    ``MoodRepository`` exposes plugin-queryable state via:
    - :meth:`get_session` — expose the underlying AsyncSession for plugin reuse
    - ``get_current_mood()``, ``get_mood_streak()`` — async queries
    - ``set_current_mood()``, ``record_mood_transition()`` — async mutations
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from guinvere.memory.models import MoodHistory, PersonaState

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# State key constants
# ---------------------------------------------------------------------------
_CURRENT_MOOD_KEY: str = "current_mood"
_MOOD_STREAK_KEY: str = "mood_streak"


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------


class MoodPersistenceError(Exception):
    """Base exception for all mood persistence failures."""


class MoodPersistenceQueryError(MoodPersistenceError):
    """Raised when a read/query operation fails."""


class MoodPersistenceWriteError(MoodPersistenceError):
    """Raised when a write/insert/update operation fails."""


# ---------------------------------------------------------------------------
# Return-type dataclasses (frozen / immutable)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MoodState:
    """Snapshot of the current mood state."""

    mood: str
    intensity: int
    updated_at: datetime
    updated_by: str


@dataclass(frozen=True)
class MoodHistoryRecord:
    """A single mood history entry."""

    mood: str
    intensity: int
    trigger: str | None
    duration_minutes: int | None
    recorded_at: datetime


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------


class MoodRepository:
    """Manages mood state persistence using persona schema tables."""

    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    # ---- session accessor (PersonaPlugin hook) -------------------------

    def get_session(self) -> AsyncSession:
        """Return the underlying AsyncSession.

        Enables PersonaPlugin to reuse the same database session for
        transactional consistency across multiple mood operations.
        """
        return self._session

    # ---- current mood -------------------------------------------------

    async def get_current_mood(self) -> MoodState | None:
        """Get current mood from persona.persona_state where state_key='current_mood'.

        Returns ``None`` when no row exists yet.
        """
        try:
            stmt = select(PersonaState).where(
                PersonaState.state_key == _CURRENT_MOOD_KEY,
            )
            result = await self._session.execute(stmt)
            row: PersonaState | None = result.scalar_one_or_none()
        except MoodPersistenceError:
            raise
        except Exception as exc:
            logger.error(
                "mood_persistence.get_current_mood.failed",
                error=str(exc),
            )
            raise MoodPersistenceQueryError(
                "Failed to query current mood state"
            ) from exc

        if row is None:
            return None

        state_value: dict[str, object] = row.state_value
        raw_mood: object = state_value.get("mood", "")
        raw_intensity: object = state_value.get("intensity", 5)
        return MoodState(
            mood=str(raw_mood) if raw_mood is not None else "",
            intensity=raw_intensity if isinstance(raw_intensity, int) else 5,
            updated_at=row.updated_at or datetime.now(timezone.utc),
            updated_by=row.updated_by,
        )

    async def set_current_mood(
        self,
        mood: str,
        intensity: int = 5,
        updated_by: str = "persona_engine",
    ) -> None:
        """Upsert current mood in persona_state table.

        If a row with ``state_key='current_mood'`` exists, its ``state_value``
        and ``updated_by`` are updated.  Otherwise a new row is inserted via
        ``merge()``.
        """
        try:
            stmt = select(PersonaState).where(
                PersonaState.state_key == _CURRENT_MOOD_KEY,
            )
            result = await self._session.execute(stmt)
            existing: PersonaState | None = result.scalar_one_or_none()

            now = datetime.now(timezone.utc)

            if existing is not None:
                existing.state_value = {
                    "mood": mood,
                    "intensity": intensity,
                }
                existing.updated_by = updated_by
                existing.updated_at = now
            else:
                new_state = PersonaState(
                    state_key=_CURRENT_MOOD_KEY,
                    state_value={"mood": mood, "intensity": intensity},
                    updated_at=now,
                    updated_by=updated_by,
                )
                self._session.add(new_state)

            await self._session.commit()
        except MoodPersistenceError:
            raise
        except Exception as exc:
            await self._safe_rollback()
            logger.error(
                "mood_persistence.set_current_mood.failed",
                error=str(exc),
                mood=mood,
            )
            raise MoodPersistenceWriteError(
                f"Failed to set current mood to '{mood}'"
            ) from exc

    # ---- mood history -------------------------------------------------

    async def record_mood_transition(
        self,
        from_mood: str,
        to_mood: str,
        reason: str,
        intensity: int = 5,
    ) -> None:
        """Insert into persona.mood_history table."""
        try:
            entry = MoodHistory(
                mood=to_mood,
                intensity=intensity,
                trigger=f"{from_mood} -> {to_mood}: {reason}",
                duration_minutes=None,
                recorded_at=datetime.now(timezone.utc),
            )
            self._session.add(entry)
            await self._session.commit()
        except MoodPersistenceError:
            raise
        except Exception as exc:
            await self._safe_rollback()
            logger.error(
                "mood_persistence.record_mood_transition.failed",
                error=str(exc),
                from_mood=from_mood,
                to_mood=to_mood,
            )
            raise MoodPersistenceWriteError(
                f"Failed to record mood transition from '{from_mood}' to '{to_mood}'"
            ) from exc

    async def get_mood_history(self, limit: int = 20) -> list[MoodHistoryRecord]:
        """Get recent mood history entries ordered by recorded_at DESC."""
        try:
            stmt = (
                select(MoodHistory)
                .order_by(MoodHistory.recorded_at.desc())
                .limit(limit)
            )
            result = await self._session.execute(stmt)
            rows: list[MoodHistory] = list(result.scalars().all())
        except MoodPersistenceError:
            raise
        except Exception as exc:
            logger.error(
                "mood_persistence.get_mood_history.failed",
                error=str(exc),
            )
            raise MoodPersistenceQueryError(
                "Failed to query mood history"
            ) from exc

        return [
            MoodHistoryRecord(
                mood=row.mood,
                intensity=row.intensity if row.intensity is not None else 5,
                trigger=row.trigger,
                duration_minutes=row.duration_minutes,
                recorded_at=row.recorded_at,
            )
            for row in rows
        ]

    # ---- mood streak --------------------------------------------------

    async def get_mood_streak(self) -> int:
        """Get current streak from persona_state where state_key='mood_streak'.

        Returns ``0`` when no streak row exists.
        """
        try:
            stmt = select(PersonaState).where(
                PersonaState.state_key == _MOOD_STREAK_KEY,
            )
            result = await self._session.execute(stmt)
            row: PersonaState | None = result.scalar_one_or_none()
        except MoodPersistenceError:
            raise
        except Exception as exc:
            logger.error(
                "mood_persistence.get_mood_streak.failed",
                error=str(exc),
            )
            raise MoodPersistenceQueryError(
                "Failed to query mood streak"
            ) from exc

        if row is None:
            return 0

        state_value: dict[str, object] = row.state_value
        raw_streak: object = state_value.get("streak", 0)
        return raw_streak if isinstance(raw_streak, int) else 0

    async def update_mood_streak(self, streak: int) -> None:
        """Update mood streak in persona_state (upsert)."""
        try:
            stmt = select(PersonaState).where(
                PersonaState.state_key == _MOOD_STREAK_KEY,
            )
            result = await self._session.execute(stmt)
            existing: PersonaState | None = result.scalar_one_or_none()

            now = datetime.now(timezone.utc)

            if existing is not None:
                existing.state_value = {"streak": streak}
                existing.updated_at = now
                existing.updated_by = "persona_engine"
            else:
                new_state = PersonaState(
                    state_key=_MOOD_STREAK_KEY,
                    state_value={"streak": streak},
                    updated_at=now,
                    updated_by="persona_engine",
                )
                self._session.add(new_state)

            await self._session.commit()
        except MoodPersistenceError:
            raise
        except Exception as exc:
            await self._safe_rollback()
            logger.error(
                "mood_persistence.update_mood_streak.failed",
                error=str(exc),
                streak=streak,
            )
            raise MoodPersistenceWriteError(
                f"Failed to update mood streak to {streak}"
            ) from exc

    # ---- internal helpers ---------------------------------------------

    async def _safe_rollback(self) -> None:
        """Rollback the session, swallowing secondary errors."""
        try:
            await self._session.rollback()
        except Exception:
            logger.warning("mood_persistence.rollback.failed")
