"""P4-002: Mood State Persistence Layer — deterministic unit tests.

Tests cover:
- get_current_mood returns MoodState or None
- set_current_mood upserts correctly (insert + update paths)
- record_mood_transition inserts history entry
- get_mood_history returns limited, ordered results
- get_mood_streak / update_mood_streak
- Error handling: DB errors wrapped in MoodPersistenceError subclasses

All tests use FakeAsyncSession — no real DB connection.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pytest

from src.persona.mood_persistence import (
    MoodHistoryRecord,
    MoodPersistenceError,
    MoodPersistenceQueryError,
    MoodPersistenceWriteError,
    MoodRepository,
    MoodState,
)


# ---------------------------------------------------------------------------
# Fake DB infrastructure
# ---------------------------------------------------------------------------

UTC = timezone.utc
NOW = datetime(2026, 6, 2, 12, 0, 0, tzinfo=UTC)


@dataclass
class FakePersonaState:
    """Mimics PersonaState ORM model for testing."""

    state_key: str
    state_value: dict[str, Any]
    updated_at: datetime = field(default_factory=lambda: NOW)
    updated_by: str = "test"
    id: Any = None


@dataclass
class FakeMoodHistory:
    """Mimics MoodHistory ORM model for testing."""

    mood: str
    intensity: int | None = 5
    trigger: str | None = None
    duration_minutes: int | None = None
    recorded_at: datetime = field(default_factory=lambda: NOW)
    id: Any = None


class FakeScalars:
    """Wraps a list of rows to provide ``.all()`` like SQLAlchemy scalars."""

    def __init__(self, rows: Sequence[Any]) -> None:
        self._rows = list(rows)

    def all(self) -> list[Any]:
        return self._rows


class FakeResult:
    """Mimics SQLAlchemy ``Result`` object."""

    def __init__(self, rows: Sequence[Any]) -> None:
        self._rows = list(rows)

    def scalar_one_or_none(self) -> Any | None:
        return self._rows[0] if self._rows else None

    def scalars(self) -> FakeScalars:
        return FakeScalars(self._rows)


class FakeAsyncSession:
    """Deterministic fake of ``AsyncSession`` for unit tests.

    ``results`` is a list of row-lists; each ``execute()`` call pops the
    next result set in order.  Added objects and commit/rollback calls
    are tracked for assertion.
    """

    def __init__(self, results: list[list[Any]] | None = None) -> None:
        self._results: list[list[Any]] = results if results is not None else []
        self._call_index: int = 0
        self.added: list[Any] = []
        self.committed: int = 0
        self.rolled_back: int = 0

    async def execute(self, stmt: Any) -> FakeResult:
        if self._call_index >= len(self._results):
            return FakeResult([])
        rows = self._results[self._call_index]
        self._call_index += 1
        return FakeResult(rows)

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.committed += 1

    async def rollback(self) -> None:
        self.rolled_back += 1


class FailingAsyncSession:
    """Fake session that raises on execute/commit to simulate DB errors."""

    def __init__(self, fail_on: str = "execute") -> None:
        self._fail_on = fail_on
        self.added: list[Any] = []
        self.committed: int = 0
        self.rolled_back: int = 0

    async def execute(self, stmt: Any) -> FakeResult:
        if self._fail_on == "execute":
            raise RuntimeError("simulated DB failure on execute")
        return FakeResult([])

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        if self._fail_on == "commit":
            raise RuntimeError("simulated DB failure on commit")
        self.committed += 1

    async def rollback(self) -> None:
        self.rolled_back += 1


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def repo_empty() -> MoodRepository:
    """Repository with no existing rows."""
    session = FakeAsyncSession(results=[[]])
    return MoodRepository(session)  # type: ignore[arg-type]


@pytest.fixture
def repo_with_mood() -> MoodRepository:
    """Repository with an existing current_mood row."""
    state = FakePersonaState(
        state_key="current_mood",
        state_value={"mood": "Content", "intensity": 7},
        updated_at=NOW,
        updated_by="persona_engine",
    )
    session = FakeAsyncSession(results=[[state]])
    return MoodRepository(session)  # type: ignore[arg-type]


@pytest.fixture
def repo_with_history() -> MoodRepository:
    """Repository with multiple mood history entries."""
    entries = [
        FakeMoodHistory(
            mood="Pleased",
            intensity=8,
            trigger="Content -> Pleased: good news",
            recorded_at=NOW,
        ),
        FakeMoodHistory(
            mood="Content",
            intensity=5,
            trigger=None,
            duration_minutes=30,
            recorded_at=NOW,
        ),
        FakeMoodHistory(
            mood="Disappointed",
            intensity=3,
            trigger="Content -> Disappointed: minor issue",
            recorded_at=NOW,
        ),
    ]
    session = FakeAsyncSession(results=[entries])
    return MoodRepository(session)  # type: ignore[arg-type]


@pytest.fixture
def repo_with_streak() -> MoodRepository:
    """Repository with an existing mood_streak row."""
    state = FakePersonaState(
        state_key="mood_streak",
        state_value={"streak": 5},
        updated_at=NOW,
        updated_by="persona_engine",
    )
    session = FakeAsyncSession(results=[[state]])
    return MoodRepository(session)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tests: get_current_mood
# ---------------------------------------------------------------------------


class TestGetCurrentMood:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_row(self, repo_empty: MoodRepository) -> None:
        result = await repo_empty.get_current_mood()
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_mood_state(self, repo_with_mood: MoodRepository) -> None:
        result = await repo_with_mood.get_current_mood()
        assert result is not None
        assert isinstance(result, MoodState)
        assert result.mood == "Content"
        assert result.intensity == 7
        assert result.updated_at == NOW
        assert result.updated_by == "persona_engine"

    @pytest.mark.asyncio
    async def test_returns_frozen_dataclass(self, repo_with_mood: MoodRepository) -> None:
        result = await repo_with_mood.get_current_mood()
        assert result is not None
        with pytest.raises(AttributeError):
            result.mood = "Other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Tests: set_current_mood
# ---------------------------------------------------------------------------


class TestSetCurrentMood:
    @pytest.mark.asyncio
    async def test_insert_when_no_existing_row(self) -> None:
        """When no current_mood row exists, a new PersonaState is added."""
        session = FakeAsyncSession(results=[[]])
        repo = MoodRepository(session)  # type: ignore[arg-type]

        await repo.set_current_mood("Pleased", intensity=8, updated_by="test_agent")

        assert len(session.added) == 1
        added = session.added[0]
        assert added.state_key == "current_mood"
        assert added.state_value == {"mood": "Pleased", "intensity": 8}
        assert added.updated_by == "test_agent"
        assert session.committed == 1

    @pytest.mark.asyncio
    async def test_update_when_existing_row(self) -> None:
        """When current_mood row exists, it is updated in-place."""
        existing = FakePersonaState(
            state_key="current_mood",
            state_value={"mood": "Content", "intensity": 5},
            updated_at=NOW,
            updated_by="persona_engine",
        )
        session = FakeAsyncSession(results=[[existing]])
        repo = MoodRepository(session)  # type: ignore[arg-type]

        await repo.set_current_mood("Disappointed", intensity=3)

        # No new object added — existing one mutated
        assert len(session.added) == 0
        assert existing.state_value == {"mood": "Disappointed", "intensity": 3}
        assert existing.updated_by == "persona_engine"
        assert session.committed == 1

    @pytest.mark.asyncio
    async def test_default_intensity_and_updated_by(self) -> None:
        session = FakeAsyncSession(results=[[]])
        repo = MoodRepository(session)  # type: ignore[arg-type]

        await repo.set_current_mood("Content")

        added = session.added[0]
        assert added.state_value == {"mood": "Content", "intensity": 5}
        assert added.updated_by == "persona_engine"


# ---------------------------------------------------------------------------
# Tests: record_mood_transition
# ---------------------------------------------------------------------------


class TestRecordMoodTransition:
    @pytest.mark.asyncio
    async def test_inserts_history_entry(self) -> None:
        session = FakeAsyncSession(results=[])
        repo = MoodRepository(session)  # type: ignore[arg-type]

        await repo.record_mood_transition(
            from_mood="Content",
            to_mood="Pleased",
            reason="good news",
            intensity=8,
        )

        assert len(session.added) == 1
        entry = session.added[0]
        assert entry.mood == "Pleased"
        assert entry.intensity == 8
        assert "Content -> Pleased" in entry.trigger
        assert "good news" in entry.trigger
        assert entry.duration_minutes is None
        assert session.committed == 1

    @pytest.mark.asyncio
    async def test_default_intensity(self) -> None:
        session = FakeAsyncSession(results=[])
        repo = MoodRepository(session)  # type: ignore[arg-type]

        await repo.record_mood_transition(
            from_mood="Content",
            to_mood="Disappointed",
            reason="minor issue",
        )

        entry = session.added[0]
        assert entry.intensity == 5


# ---------------------------------------------------------------------------
# Tests: get_mood_history
# ---------------------------------------------------------------------------


class TestGetMoodHistory:
    @pytest.mark.asyncio
    async def test_returns_history_records(
        self, repo_with_history: MoodRepository
    ) -> None:
        records = await repo_with_history.get_mood_history(limit=10)

        assert len(records) == 3
        assert all(isinstance(r, MoodHistoryRecord) for r in records)

        assert records[0].mood == "Pleased"
        assert records[0].intensity == 8
        assert records[0].trigger == "Content -> Pleased: good news"

        assert records[1].mood == "Content"
        assert records[1].trigger is None
        assert records[1].duration_minutes == 30

        assert records[2].mood == "Disappointed"
        assert records[2].intensity == 3

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_history(self) -> None:
        session = FakeAsyncSession(results=[[]])
        repo = MoodRepository(session)  # type: ignore[arg-type]

        records = await repo.get_mood_history()
        assert records == []

    @pytest.mark.asyncio
    async def test_frozen_dataclass(self, repo_with_history: MoodRepository) -> None:
        records = await repo_with_history.get_mood_history(limit=1)
        assert len(records) > 0
        with pytest.raises(AttributeError):
            records[0].mood = "Other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Tests: get_mood_streak / update_mood_streak
# ---------------------------------------------------------------------------


class TestMoodStreak:
    @pytest.mark.asyncio
    async def test_get_streak_returns_zero_when_no_row(self) -> None:
        session = FakeAsyncSession(results=[[]])
        repo = MoodRepository(session)  # type: ignore[arg-type]

        streak = await repo.get_mood_streak()
        assert streak == 0

    @pytest.mark.asyncio
    async def test_get_streak_returns_value(
        self, repo_with_streak: MoodRepository
    ) -> None:
        streak = await repo_with_streak.get_mood_streak()
        assert streak == 5

    @pytest.mark.asyncio
    async def test_update_streak_insert_when_no_row(self) -> None:
        session = FakeAsyncSession(results=[[]])
        repo = MoodRepository(session)  # type: ignore[arg-type]

        await repo.update_mood_streak(3)

        assert len(session.added) == 1
        added = session.added[0]
        assert added.state_key == "mood_streak"
        assert added.state_value == {"streak": 3}
        assert added.updated_by == "persona_engine"
        assert session.committed == 1

    @pytest.mark.asyncio
    async def test_update_streak_modifies_existing(self) -> None:
        existing = FakePersonaState(
            state_key="mood_streak",
            state_value={"streak": 5},
            updated_at=NOW,
            updated_by="persona_engine",
        )
        session = FakeAsyncSession(results=[[existing]])
        repo = MoodRepository(session)  # type: ignore[arg-type]

        await repo.update_mood_streak(10)

        assert len(session.added) == 0
        assert existing.state_value == {"streak": 10}
        assert session.committed == 1


# ---------------------------------------------------------------------------
# Tests: Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_get_current_mood_wraps_db_error(self) -> None:
        session = FailingAsyncSession(fail_on="execute")
        repo = MoodRepository(session)  # type: ignore[arg-type]

        with pytest.raises(MoodPersistenceQueryError) as exc_info:
            await repo.get_current_mood()

        assert isinstance(exc_info.value, MoodPersistenceError)
        assert exc_info.value.__cause__ is not None

    @pytest.mark.asyncio
    async def test_set_current_mood_wraps_db_error(self) -> None:
        session = FailingAsyncSession(fail_on="execute")
        repo = MoodRepository(session)  # type: ignore[arg-type]

        with pytest.raises(MoodPersistenceWriteError) as exc_info:
            await repo.set_current_mood("Content")

        assert isinstance(exc_info.value, MoodPersistenceError)
        assert exc_info.value.__cause__ is not None

    @pytest.mark.asyncio
    async def test_set_current_mood_wraps_commit_error(self) -> None:
        """If execute succeeds but commit fails, error is wrapped."""
        session = FailingAsyncSession(fail_on="commit")
        repo = MoodRepository(session)  # type: ignore[arg-type]

        with pytest.raises(MoodPersistenceWriteError):
            await repo.set_current_mood("Content")

        # rollback should have been called
        assert session.rolled_back == 1

    @pytest.mark.asyncio
    async def test_record_mood_transition_wraps_error(self) -> None:
        session = FailingAsyncSession(fail_on="commit")
        repo = MoodRepository(session)  # type: ignore[arg-type]

        with pytest.raises(MoodPersistenceWriteError) as exc_info:
            await repo.record_mood_transition("Content", "Pleased", "test")

        assert isinstance(exc_info.value, MoodPersistenceError)

    @pytest.mark.asyncio
    async def test_get_mood_history_wraps_db_error(self) -> None:
        session = FailingAsyncSession(fail_on="execute")
        repo = MoodRepository(session)  # type: ignore[arg-type]

        with pytest.raises(MoodPersistenceQueryError):
            await repo.get_mood_history()

    @pytest.mark.asyncio
    async def test_get_mood_streak_wraps_db_error(self) -> None:
        session = FailingAsyncSession(fail_on="execute")
        repo = MoodRepository(session)  # type: ignore[arg-type]

        with pytest.raises(MoodPersistenceQueryError):
            await repo.get_mood_streak()

    @pytest.mark.asyncio
    async def test_update_mood_streak_wraps_db_error(self) -> None:
        session = FailingAsyncSession(fail_on="execute")
        repo = MoodRepository(session)  # type: ignore[arg-type]

        with pytest.raises(MoodPersistenceWriteError):
            await repo.update_mood_streak(5)

    @pytest.mark.asyncio
    async def test_error_hierarchy(self) -> None:
        """Verify exception class hierarchy."""
        assert issubclass(MoodPersistenceQueryError, MoodPersistenceError)
        assert issubclass(MoodPersistenceWriteError, MoodPersistenceError)
        assert issubclass(MoodPersistenceError, Exception)


# ---------------------------------------------------------------------------
# Tests: Return type contracts
# ---------------------------------------------------------------------------


class TestReturnTypeContracts:
    @pytest.mark.asyncio
    async def test_mood_state_fields(self) -> None:
        state = MoodState(
            mood="Content",
            intensity=5,
            updated_at=NOW,
            updated_by="test",
        )
        assert state.mood == "Content"
        assert state.intensity == 5
        assert state.updated_at == NOW
        assert state.updated_by == "test"

    @pytest.mark.asyncio
    async def test_mood_history_record_fields(self) -> None:
        record = MoodHistoryRecord(
            mood="Pleased",
            intensity=8,
            trigger="test trigger",
            duration_minutes=15,
            recorded_at=NOW,
        )
        assert record.mood == "Pleased"
        assert record.intensity == 8
        assert record.trigger == "test trigger"
        assert record.duration_minutes == 15
        assert record.recorded_at == NOW

    @pytest.mark.asyncio
    async def test_mood_history_record_nullable_fields(self) -> None:
        record = MoodHistoryRecord(
            mood="Content",
            intensity=5,
            trigger=None,
            duration_minutes=None,
            recorded_at=NOW,
        )
        assert record.trigger is None
        assert record.duration_minutes is None
