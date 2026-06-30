"""Async SQLAlchemy session factory for Guinevere PostgreSQL database.

Connection: postgresql+asyncpg://guinevere_core@localhost:5433/guinevere
Schema: persona (PunishmentLog, RewardLog, PersonaState, DriftLog, MoodHistory)

Usage::

    async with get_async_session() as session:
        session.add(SomeModel(...))
        await session.commit()

The engine and session factory are created lazily on first call to
``get_async_engine()`` or ``get_async_session()``.  Callers must NOT
commit/rollback the session themselves when using the context manager —
``get_async_session()`` commits on clean exit and rolls back on exception.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# ---------------------------------------------------------------------------
# Database URL
# ---------------------------------------------------------------------------

_DEFAULT_DB_URL = (
    "postgresql+asyncpg://guinevere_core@localhost:5433/guinevere"
)


def _db_url() -> str:
    """Return the database URL from env or default."""
    return os.environ.get("GUINEVERE_DB_URL", _DEFAULT_DB_URL)


# ---------------------------------------------------------------------------
# Lazy engine singleton
# ---------------------------------------------------------------------------

_engine: AsyncEngine | None = None


def get_async_engine() -> AsyncEngine:
    """Return (or create) the shared async SQLAlchemy engine."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            _db_url(),
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            echo=False,
        )
    return _engine


# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

_session_factory: async_sessionmaker[AsyncSession] | None = None


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return (or create) the shared async session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_async_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autobegin=True,
        )
    return _session_factory


# ---------------------------------------------------------------------------
# Public context manager
# ---------------------------------------------------------------------------


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an ``AsyncSession``, commit on success, rollback on error.

    Example::

        async with get_async_session() as session:
            session.add(PunishmentLog(...))
            # commit happens automatically on context exit

    Raises:
        Any exception from the database layer — callers should wrap in
        try/except if they want graceful degradation.
    """
    factory = _get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


__all__ = [
    "get_async_engine",
    "get_async_session",
    "write_yandere_state",
]


async def write_yandere_state(
    yandere_level: int,
    baseline: int,
    effective_level: int,
    *,
    session_override=None,
) -> bool:
    """Persist yandere state to ``persona.persona_state`` (JSONB).

    Uses the key ``yandere_state``.  If a ``session_override`` is provided,
    the caller manages commit/rollback.  Otherwise a new session is created
    via :func:`get_async_session`.

    Returns ``True`` on success, ``False`` on any error (fire-and-forget
    semantics — the caller is never blocked).
    """
    import json
    from datetime import datetime, timezone

    try:
        from guinvere.memory.models import PersonaState

        state_value = {
            "yandere_level": yandere_level,
            "baseline": baseline,
            "effective_level": effective_level,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        if session_override is not None:
            # Check if row exists; update or insert.
            from sqlalchemy import select as _select
            stmt = _select(PersonaState).where(PersonaState.state_key == "yandere_state")
            result = await session_override.execute(stmt)
            row = result.scalars().first()
            if row is not None:
                row.state_value = state_value
                row.updated_at = datetime.now(timezone.utc)
                row.updated_by = "yandere_engine"
            else:
                session_override.add(
                    PersonaState(
                        state_key="yandere_state",
                        state_value=state_value,
                        updated_by="yandere_engine",
                    )
                )
            await session_override.flush()
            return True
        else:
            async with get_async_session() as session:
                from sqlalchemy import select as _select2
                stmt = _select2(PersonaState).where(PersonaState.state_key == "yandere_state")
                result = await session.execute(stmt)
                row = result.scalars().first()
                if row is not None:
                    row.state_value = state_value
                    row.updated_at = datetime.now(timezone.utc)
                    row.updated_by = "yandere_engine"
                else:
                    session.add(
                        PersonaState(
                            state_key="yandere_state",
                            state_value=state_value,
                            updated_by="yandere_engine",
                        )
                    )
                await session.commit()
                return True
    except Exception:
        return False
