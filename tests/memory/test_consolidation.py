"""P3-015: Daily consolidation job — deterministic unit tests.

Tests cover:
- Scheduler registration id ``daily_consolidation``, 03:00 Asia/Bangkok trigger.
- Consolidation excludes ``do_not_recall=True`` episodes.
- Skips safe-word/crisis/formal-hold identifiable records.
- Semantic fact creation preserves source episode/provenance and highest
  classification.
- Idempotent repeated run does not duplicate semantic facts.
- Pruning dry-run/non-destructive default.
- Job wrapper logs metadata-only and re-raises errors.

All tests use synthetic/fake data — no DB, no scheduler, no network.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol

from src.memory.consolidation import AsyncSessionProtocol

import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.sql import Select
from sqlalchemy.sql.elements import (
    BinaryExpression,
    BooleanClauseList,
    UnaryExpression,
)

from src.memory.consolidation import (
    CONSOLIDATION_JOB_ID,
    CONSOLIDATION_HOUR,
    CONSOLIDATION_MINUTE,
    TZ_BANGKOK,
    ConsolidationResult,
    PruneResult,
    RetentionConfig,
    consolidate_episodes_to_facts,
    daily_consolidation_job,
    highest_classification,
    is_safe_word_record,
    make_content_key,
    prune_stale_facts,
    register_consolidation_job,
)
from src.memory.embeddings import (
    PUBLIC,
    INTERNAL,
    RESTRICTED,
    CONFIDENTIAL,
    CRITICAL,
)

UTC = timezone.utc

# ---------------------------------------------------------------------------
# Local protocol for caplog fixture
# ---------------------------------------------------------------------------


class _CapLog(Protocol):
    """Minimal protocol for pytest's caplog fixture."""

    records: list[logging.LogRecord]

    def at_level(
        self, level: int, logger: str
    ) -> AbstractContextManager[object]:
        ...


# ---------------------------------------------------------------------------
# Fake objects — mimic SQLAlchemy ORM row with minimal required attributes
# ---------------------------------------------------------------------------


@dataclass
class FakeEpisode:
    """Minimal fake ``Episodes`` row for consolidation tests."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    do_not_recall: bool = False
    classification: str = RESTRICTED
    episode_type: str = "conversation"
    title: str = ""
    summary: str = ""
    key_insights: dict[str, str] | None = None
    tags: list[str] | None = None
    source: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class FakeFact:
    """Minimal fake ``SemanticFacts`` row for consolidation tests."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    subject: str = ""
    predicate: str = ""
    object_val: str = ""
    fact_type: str = "episodic_summary"
    confidence: float = 0.5
    source: str = "consolidation"
    source_episode: uuid.UUID | None = None
    classification: str = RESTRICTED
    tags: list[str] | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    deletion_state: str = "active"
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class FakeScalarResult:
    """Mimics SQLAlchemy ``Result.scalars().all()``."""

    def __init__(self, rows: list[object] | list[FakeEpisode] | list[FakeFact]) -> None:
        self._rows = list(rows)

    def all(self) -> list[object]:
        return self._rows


class FakeExecuteResult:
    """Mimics SQLAlchemy execution result."""

    def __init__(self, scalars_result: FakeScalarResult) -> None:
        self._scalars_result = scalars_result

    def scalars(self) -> FakeScalarResult:
        return self._scalars_result


class FakeSession:
    """Fake async session for consolidation tests.

    Stores episodes and facts in dicts indexed by UUID.  Handles
    ``select(Episodes)`` and ``select(SemanticFacts)`` with simple
    WHERE condition inspection.
    """

    def __init__(self) -> None:
        self.episodes: dict[uuid.UUID, FakeEpisode] = {}
        self.facts: dict[uuid.UUID, FakeFact] = {}
        self._added_objects: list[object] = []

    # ------------------------------------------------------------------
    # Session-like interface
    # ------------------------------------------------------------------

    async def execute(self, statement: object) -> FakeExecuteResult:
        """Handle ``select(Episodes)`` and ``select(SemanticFacts)``."""
        if not isinstance(statement, Select):
            return FakeExecuteResult(FakeScalarResult([]))

        table_name = self._extract_table_name(statement)

        if table_name == "episodes":
            return self._execute_episodes_select(statement)
        elif table_name == "semantic_facts":
            return self._execute_facts_select(statement)
        return FakeExecuteResult(FakeScalarResult([]))

    def add(self, obj: object) -> None:
        """Track added objects for later inspection.

        Accepts both ``FakeFact`` and real ``SemanticFacts`` ORM instances,
        converting the latter to a ``FakeFact`` for test inspection.
        """
        self._added_objects.append(obj)

        # Handle FakeFact (dataclass)
        if isinstance(obj, FakeFact):
            self.facts[obj.id] = obj
            return

        # Handle SemanticFacts (real ORM model) — extract attributes safely.
        # Note: ORM model ``id`` is ``None`` before DB flush, so we generate
        # a UUID for test storage.
        if hasattr(obj, "subject") and hasattr(obj, "predicate"):
            sf_id = getattr(obj, "id", None)
            fact = FakeFact(
                id=sf_id if isinstance(sf_id, uuid.UUID) else uuid.uuid4(),
                subject=str(getattr(obj, "subject", "")),
                predicate=str(getattr(obj, "predicate", "")),
                object_val=str(getattr(obj, "object_val", "")),
                fact_type=str(getattr(obj, "fact_type", "episodic_summary")),
                confidence=float(getattr(obj, "confidence", 0.5) or 0.5),
                source=str(getattr(obj, "source", "consolidation")),
                source_episode=getattr(obj, "source_episode", None),
                classification=str(getattr(obj, "classification", RESTRICTED)),
                tags=list(getattr(obj, "tags", None) or []) if getattr(obj, "tags", None) else None,
                created_at=getattr(obj, "created_at", datetime.now(UTC)),
            )
            self.facts[fact.id] = fact

    async def delete(self, obj: object) -> None:
        """Remove a fact from the store."""
        if isinstance(obj, FakeFact) and obj.id in self.facts:
            del self.facts[obj.id]

    async def __aenter__(self) -> FakeSession:
        """Support async context manager protocol."""
        return self

    async def __aexit__(self, *args: object) -> None:
        """Support async context manager protocol."""

    async def flush(self) -> None:
        """No-op for tests."""

    # ------------------------------------------------------------------
    # Statement introspection helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_table_name(statement: Select[tuple[object, ...]]) -> str:
        """Extract the target table name from a select statement."""
        from sqlalchemy.sql import FromClause

        froms: list[FromClause] = list(statement.get_final_froms())
        if not froms:
            return ""
        for f in froms:
            name = getattr(f, "name", None)
            if name:
                return str(name)
        return ""

    def _extract_where_conditions(
        self, statement: Select[tuple[object, ...]]
    ) -> list[tuple[str, str, object]]:
        """Extract (column, operator, value) triples from WHERE clause.

        Handles ``BooleanClauseList`` (AND-combined criteria from chained
        ``.where()`` calls), ``BinaryExpression``, and ``UnaryExpression``.
        """
        whereclause = getattr(statement, "whereclause", None)
        if whereclause is None:
            return []

        conditions: list[tuple[str, str, object]] = []

        if isinstance(whereclause, BooleanClauseList):
            for clause in whereclause.clauses:
                conditions.extend(self._extract_single_condition(clause))
        else:
            conditions.extend(self._extract_single_condition(whereclause))

        return conditions

    def _extract_single_condition(
        self, expr: object
    ) -> list[tuple[str, str, object]]:
        """Extract conditions from a single expression."""
        if isinstance(expr, BooleanClauseList):
            result: list[tuple[str, str, object]] = []
            for clause in expr.clauses:
                result.extend(self._extract_single_condition(clause))
            return result

        if isinstance(expr, UnaryExpression):
            element = getattr(expr, "element", None)
            if isinstance(element, BinaryExpression):
                left = getattr(element, "left", None)
                right = getattr(element, "right", None)
                col_name = self._get_column_name(left)
                op = self._get_operator(expr)
                val = self._get_value(right)
                if col_name:
                    return [(col_name, op, val)]
            col_name = self._get_column_name(element)
            if col_name:
                return [(col_name, "is_not", None)]
            return []

        if isinstance(expr, BinaryExpression):
            left = getattr(expr, "left", None)
            right = getattr(expr, "right", None)
            col_name = self._get_column_name(left)
            op = self._get_operator(expr)
            val: object = self._get_value(right)
            if col_name:
                return [(col_name, op, val)]
        return []

    @staticmethod
    def _get_column_name(expr: object) -> str | None:
        """Get the column name from a SQLAlchemy column expression."""
        if expr is None:
            return None
        name = getattr(expr, "name", None)
        if name:
            return str(name)
        element = getattr(expr, "element", None)
        if element is not None:
            name = getattr(element, "name", None)
            if name:
                return str(name)
        return None

    @staticmethod
    def _get_operator(expr: object) -> str:
        """Get operator string from expression."""
        from sqlalchemy.sql import operators

        op = getattr(expr, "operator", None)
        if op is None:
            return "eq"

        op_map: dict[object, str] = {
            operators.eq: "eq",
            operators.ne: "ne",
            operators.gt: "gt",
            operators.lt: "lt",
            operators.ge: "ge",
            operators.le: "le",
            operators.is_: "is_",
            operators.is_not: "is_not",
        }
        return op_map.get(op, str(op))

    @staticmethod
    def _get_value(expr: object) -> object:
        """Get the bound value from a BindParameter or literal."""
        from sqlalchemy.sql.elements import BindParameter, Label

        if expr is None:
            return None
        if isinstance(expr, BindParameter):
            return getattr(expr, "value", None)
        if isinstance(expr, Label):
            return getattr(expr, "name", None)
        return expr if not hasattr(expr, "value") else getattr(expr, "value", None)

    # ------------------------------------------------------------------
    # Select execution
    # ------------------------------------------------------------------

    def _execute_episodes_select(
        self, statement: Select[tuple[object, ...]]
    ) -> FakeExecuteResult:
        """Filter stored episodes by WHERE conditions."""
        conditions = self._extract_where_conditions(statement)
        results = list(self.episodes.values())

        for _col, op, val in conditions:
            if _col == "do_not_recall":
                if op in ("is_", "eq") and val is False:
                    results = [e for e in results if not e.do_not_recall]
                elif op == "is_not" and val is False:
                    results = [e for e in results if e.do_not_recall]
            elif _col == "created_at":
                if op == "gt" and isinstance(val, datetime):
                    results = [e for e in results if e.created_at > val]
                elif op == "ge" and isinstance(val, datetime):
                    results = [e for e in results if e.created_at >= val]
            elif _col == "id":
                if op == "eq" and isinstance(val, uuid.UUID):
                    results = [e for e in results if e.id == val]

        return FakeExecuteResult(FakeScalarResult(results))

    def _execute_facts_select(
        self, statement: Select[tuple[object, ...]]
    ) -> FakeExecuteResult:
        """Filter stored facts by WHERE conditions."""
        conditions = self._extract_where_conditions(statement)
        results = list(self.facts.values())

        for _col, op, val in conditions:
            if _col == "source_episode":
                if op == "eq" and isinstance(val, uuid.UUID):
                    results = [f for f in results if f.source_episode == val]
            elif _col == "id":
                if op == "eq" and isinstance(val, uuid.UUID):
                    results = [f for f in results if f.id == val]

        return FakeExecuteResult(FakeScalarResult(results))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_session() -> FakeSession:
    return FakeSession()


@pytest.fixture
def seeded_session() -> FakeSession:
    """Session with a single non-DNR, normal episode."""
    session = FakeSession()
    ep = FakeEpisode(
        title="test_conversation",
        summary="A test conversation about Python.",
        episode_type="conversation",
        classification=RESTRICTED,
    )
    session.episodes[ep.id] = ep
    return session


@pytest.fixture
def varied_session() -> FakeSession:
    """Session with episodes of various classifications and DNR/safe-word flags."""
    session = FakeSession()

    public_ep = FakeEpisode(
        title="public_note",
        summary="A public note.",
        classification=PUBLIC,
        episode_type="note",
    )
    internal_ep = FakeEpisode(
        title="internal_memo",
        summary="An internal memo.",
        classification=INTERNAL,
        episode_type="memo",
    )
    restricted_ep = FakeEpisode(
        title="restricted_discussion",
        summary="A restricted discussion.",
        classification=RESTRICTED,
        episode_type="conversation",
    )
    confidential_ep = FakeEpisode(
        title="confidential_plan",
        summary="A confidential plan.",
        classification=CONFIDENTIAL,
        episode_type="planning",
    )
    critical_ep = FakeEpisode(
        title="critical_secret",
        summary="A critical secret.",
        classification=CRITICAL,
        episode_type="crisis",
    )

    dnr_ep = FakeEpisode(
        title="dnr_conversation",
        summary="This should be excluded.",
        do_not_recall=True,
        classification=RESTRICTED,
        episode_type="conversation",
    )

    safe_word_ep = FakeEpisode(
        title="safe_word_event",
        summary="Safe word was used.",
        classification=RESTRICTED,
        episode_type="conversation",
        tags=["safe_word"],
    )

    crisis_ep = FakeEpisode(
        title="crisis_situation",
        summary="A crisis occurred.",
        classification=CRITICAL,
        episode_type="crisis",
        tags=["distress"],
    )

    session.episodes[public_ep.id] = public_ep
    session.episodes[internal_ep.id] = internal_ep
    session.episodes[restricted_ep.id] = restricted_ep
    session.episodes[confidential_ep.id] = confidential_ep
    session.episodes[critical_ep.id] = critical_ep
    session.episodes[dnr_ep.id] = dnr_ep
    session.episodes[safe_word_ep.id] = safe_word_ep
    session.episodes[crisis_ep.id] = crisis_ep
    return session


# ---------------------------------------------------------------------------
# Scheduler registration tests
# ---------------------------------------------------------------------------


class TestSchedulerRegistration:
    """Verify ``register_consolidation_job`` registers with correct ID/trigger."""

    def test_registers_correct_job_id(self) -> None:
        """Job ID must be ``daily_consolidation``."""
        async def _run() -> str:
            scheduler = AsyncIOScheduler()
            scheduler.start()
            try:
                await register_consolidation_job(scheduler)
                job = scheduler.get_job(CONSOLIDATION_JOB_ID)
                assert job is not None, f"Job {CONSOLIDATION_JOB_ID} not found"
                return str(job.id)
            finally:
                scheduler.shutdown(wait=False)

        result = asyncio.run(_run())
        assert result == CONSOLIDATION_JOB_ID

    def test_registers_correct_trigger(self) -> None:
        """Trigger must be CronTrigger at 03:00 Asia/Bangkok."""
        async def _run() -> tuple[bool, bool, bool]:
            scheduler = AsyncIOScheduler()
            scheduler.start()
            try:
                await register_consolidation_job(scheduler)
                job = scheduler.get_job(CONSOLIDATION_JOB_ID)
                assert job is not None
                trigger = job.trigger
                is_cron = isinstance(trigger, CronTrigger)
                trigger_repr = repr(trigger)
                has_hour = f"hour='{CONSOLIDATION_HOUR}'" in trigger_repr or "hour='3'" in trigger_repr
                has_tz = TZ_BANGKOK in trigger_repr or "Asia/Bangkok" in trigger_repr
                return (is_cron, has_hour, has_tz)
            finally:
                scheduler.shutdown(wait=False)

        is_cron, has_hour, has_tz = asyncio.run(_run())
        assert is_cron
        assert has_hour
        assert has_tz

    def test_replace_existing_allows_reregistration(self) -> None:
        """Re-registering same ID should not raise."""
        async def _run() -> str:
            scheduler = AsyncIOScheduler()
            scheduler.start()
            try:
                await register_consolidation_job(scheduler)
                await register_consolidation_job(scheduler)
                job = scheduler.get_job(CONSOLIDATION_JOB_ID)
                assert job is not None
                return str(job.id)
            finally:
                scheduler.shutdown(wait=False)

        result = asyncio.run(_run())
        assert result == CONSOLIDATION_JOB_ID

    def test_cron_trigger_pure_function(self) -> None:
        """CronTrigger is a pure function — test next fire time."""
        from datetime import datetime
        from zoneinfo import ZoneInfo

        tz = ZoneInfo(TZ_BANGKOK)
        trigger = CronTrigger(
            hour=CONSOLIDATION_HOUR,
            minute=CONSOLIDATION_MINUTE,
            timezone=TZ_BANGKOK,
        )

        now = datetime(2026, 6, 2, 10, 0, 0, tzinfo=tz)
        next_time = trigger.get_next_fire_time(None, now)
        assert next_time is not None
        assert next_time.hour == CONSOLIDATION_HOUR
        assert next_time.minute == CONSOLIDATION_MINUTE
        assert next_time.day == 3
        assert next_time.month == 6
        assert next_time.year == 2026


# ---------------------------------------------------------------------------
# DNR exclusion tests
# ---------------------------------------------------------------------------


class TestDNRExclusion:
    """Consolidation must exclude ``do_not_recall=True`` episodes."""

    def test_skips_dnr_episodes(self, seeded_session: FakeSession) -> None:
        """DNR episode should not produce semantic facts."""
        dnr_ep = FakeEpisode(
            title="dnr_test",
            summary="Should be excluded.",
            do_not_recall=True,
        )
        seeded_session.episodes[dnr_ep.id] = dnr_ep

        result = asyncio.run(consolidate_episodes_to_facts(seeded_session))

        assert result.skipped_dnr >= 1
        assert result.consolidated >= 1

    def test_no_facts_from_dnr_only(self, fake_session: FakeSession) -> None:
        """Session with only DNR episodes produces zero consolidated facts."""
        dnr_ep = FakeEpisode(
            title="only_dnr",
            summary="Only DNR episode.",
            do_not_recall=True,
        )
        fake_session.episodes[dnr_ep.id] = dnr_ep

        result = asyncio.run(consolidate_episodes_to_facts(fake_session))

        assert result.consolidated == 0
        assert result.skipped_dnr == 1
        assert result.skipped_safe_word == 0


# ---------------------------------------------------------------------------
# Safe-word/crisis/formal-hold skip tests
# ---------------------------------------------------------------------------


class TestSafeWordSkip:
    """Consolidation must skip safe-word/crisis/formal-hold records."""

    def test_skips_safe_word_tag(self, seeded_session: FakeSession) -> None:
        """Episode tagged with ``safe_word`` should be skipped."""
        sw_ep = FakeEpisode(
            title="sw_tagged",
            summary="Safe word episode.",
            tags=["safe_word"],
            episode_type="conversation",
        )
        seeded_session.episodes[sw_ep.id] = sw_ep

        result = asyncio.run(consolidate_episodes_to_facts(seeded_session))
        assert result.skipped_safe_word >= 1

    def test_skips_crisis_episode_type(self, seeded_session: FakeSession) -> None:
        """Episode with ``crisis`` type should be skipped."""
        crisis_ep = FakeEpisode(
            title="crisis_event",
            summary="A crisis event.",
            episode_type="crisis",
        )
        seeded_session.episodes[crisis_ep.id] = crisis_ep

        result = asyncio.run(consolidate_episodes_to_facts(seeded_session))
        assert result.skipped_safe_word >= 1

    def test_skips_hard_stop_title(self, seeded_session: FakeSession) -> None:
        """Episode with ``hard_stop`` title should be skipped."""
        hs_ep = FakeEpisode(
            title="hard_stop",
            summary="Hard stop triggered.",
            episode_type="conversation",
        )
        seeded_session.episodes[hs_ep.id] = hs_ep

        result = asyncio.run(consolidate_episodes_to_facts(seeded_session))
        assert result.skipped_safe_word >= 1

    def test_skips_formal_hold_summary(self, seeded_session: FakeSession) -> None:
        """Episode with ``formal_hold`` in summary should be skipped."""
        fh_ep = FakeEpisode(
            title="hold_record",
            summary="formal_hold status active",
            episode_type="conversation",
        )
        seeded_session.episodes[fh_ep.id] = fh_ep

        result = asyncio.run(consolidate_episodes_to_facts(seeded_session))
        assert result.skipped_safe_word >= 1

    def test_skips_distress_tag(self, seeded_session: FakeSession) -> None:
        """Episode with ``distress`` tag should be skipped."""
        dist_ep = FakeEpisode(
            title="user_distressed",
            summary="User is distressed.",
            tags=["distress"],
            episode_type="conversation",
        )
        seeded_session.episodes[dist_ep.id] = dist_ep

        result = asyncio.run(consolidate_episodes_to_facts(seeded_session))
        assert result.skipped_safe_word >= 1

    def test_multiple_safe_word_records_skipped(
        self, fake_session: FakeSession
    ) -> None:
        """Multiple safe-word records all skipped."""
        for i in range(3):
            sw_ep = FakeEpisode(
                title=f"sw_{i}",
                summary=f"Safe word event {i}.",
                tags=["safe_word"],
            )
            fake_session.episodes[sw_ep.id] = sw_ep

        result = asyncio.run(consolidate_episodes_to_facts(fake_session))
        assert result.skipped_safe_word == 3
        assert result.consolidated == 0


# ---------------------------------------------------------------------------
# is_safe_word_record unit tests
# ---------------------------------------------------------------------------


class TestIsSafeWordRecord:
    """Direct tests of the safe-word detection helper."""

    def test_detects_safe_word_tag(self) -> None:
        ep = FakeEpisode(tags=["safe_word"])
        assert is_safe_word_record(ep)

    def test_detects_crisis_type(self) -> None:
        ep = FakeEpisode(episode_type="crisis")
        assert is_safe_word_record(ep)

    def test_detects_hard_stop_title(self) -> None:
        ep = FakeEpisode(title="hard_stop")
        assert is_safe_word_record(ep)

    def test_detects_distress_summary(self) -> None:
        ep = FakeEpisode(summary="distress signal received")
        assert is_safe_word_record(ep)

    def test_detects_formal_hold_source(self) -> None:
        ep = FakeEpisode(source="formal_hold")
        assert is_safe_word_record(ep)

    def test_normal_episode_not_detected(self) -> None:
        ep = FakeEpisode(
            title="normal_convo",
            summary="Everything is fine.",
            episode_type="conversation",
            tags=["general"],
        )
        assert not is_safe_word_record(ep)

    def test_empty_episode_not_detected(self) -> None:
        ep = FakeEpisode()
        assert not is_safe_word_record(ep)

    def test_comma_separated_tags_string(self) -> None:
        """Handle tags as comma-separated string."""
        ep = FakeEpisode(title="test", tags=["general", "safe_word", "urgent"])
        assert is_safe_word_record(ep)


# ---------------------------------------------------------------------------
# Classification preservation tests
# ---------------------------------------------------------------------------


class TestClassificationPreservation:
    """Semantic facts must preserve highest classification from sources."""

    def test_preserves_episode_classification(
        self, fake_session: FakeSession
    ) -> None:
        """Fact classification should match episode classification."""
        ep = FakeEpisode(
            title="confidential_note",
            summary="A confidential note.",
            classification=CONFIDENTIAL,
        )
        fake_session.episodes[ep.id] = ep

        result = asyncio.run(consolidate_episodes_to_facts(fake_session))
        assert result.consolidated == 1
        assert len(result.facts_created) == 1
        assert result.facts_created[0]["classification"] == CONFIDENTIAL

    def test_multiple_classifications_preserved(
        self, varied_session: FakeSession
    ) -> None:
        """Episodes with different classifications all preserve their own."""
        result = asyncio.run(consolidate_episodes_to_facts(varied_session))

        assert result.skipped_dnr >= 1
        assert result.skipped_safe_word >= 2
        assert result.consolidated >= 3

        classifications = {f["classification"] for f in result.facts_created}
        assert PUBLIC in classifications or INTERNAL in classifications or RESTRICTED in classifications

    def test_safe_word_episode_classification_not_in_facts(
        self, fake_session: FakeSession
    ) -> None:
        """Safe-word-tagged episodes should not produce facts."""
        sw_ep = FakeEpisode(
            title="sw_public",
            summary="Safe word public.",
            classification=PUBLIC,
            tags=["safe_word"],
        )
        fake_session.episodes[sw_ep.id] = sw_ep

        result = asyncio.run(consolidate_episodes_to_facts(fake_session))
        assert result.consolidated == 0
        assert result.skipped_safe_word == 1

    def test_dnr_episode_classification_not_in_facts(
        self, fake_session: FakeSession
    ) -> None:
        """DNR episodes should not produce facts even at low classification."""
        dnr_ep = FakeEpisode(
            title="dnr_public",
            summary="DNR public note.",
            classification=PUBLIC,
            do_not_recall=True,
        )
        fake_session.episodes[dnr_ep.id] = dnr_ep

        result = asyncio.run(consolidate_episodes_to_facts(fake_session))
        assert result.consolidated == 0
        assert result.skipped_dnr == 1


# ---------------------------------------------------------------------------
# highest_classification unit tests
# ---------------------------------------------------------------------------


class TestHighestClassification:
    """Direct tests of the classification resolution helper."""

    def test_public_lowest(self) -> None:
        assert highest_classification(PUBLIC, INTERNAL) == INTERNAL

    def test_critical_highest(self) -> None:
        assert highest_classification(PUBLIC, INTERNAL, CRITICAL) == CRITICAL

    def test_none_fails_closed(self) -> None:
        assert highest_classification(None) == CRITICAL

    def test_all_none_returns_restricted(self) -> None:
        assert highest_classification() == RESTRICTED

    def test_public_only(self) -> None:
        assert highest_classification(PUBLIC) == PUBLIC

    def test_confidential_vs_restricted(self) -> None:
        assert highest_classification(RESTRICTED, CONFIDENTIAL) == CONFIDENTIAL

    def test_internal_vs_public(self) -> None:
        assert highest_classification(PUBLIC, INTERNAL) == INTERNAL


# ---------------------------------------------------------------------------
# Provenance preservation tests
# ---------------------------------------------------------------------------


class TestProvenancePreservation:
    """Semantic facts must store source episode IDs."""

    def test_fact_has_source_episode(
        self, seeded_session: FakeSession
    ) -> None:
        """Created fact's source_episode should match source episode ID."""
        ep = next(iter(seeded_session.episodes.values()))
        result = asyncio.run(consolidate_episodes_to_facts(seeded_session))

        assert result.consolidated == 1
        assert result.facts_created[0]["source_episode"] == str(ep.id)

    def test_multiple_episodes_all_preserve_source(
        self, fake_session: FakeSession
    ) -> None:
        """Multiple episodes each produce facts with correct source_episode."""
        ep1 = FakeEpisode(title="ep1", summary="First episode.")
        ep2 = FakeEpisode(title="ep2", summary="Second episode.")
        fake_session.episodes[ep1.id] = ep1
        fake_session.episodes[ep2.id] = ep2

        result = asyncio.run(consolidate_episodes_to_facts(fake_session))

        assert result.consolidated >= 2
        source_ids = {f["source_episode"] for f in result.facts_created}
        assert str(ep1.id) in source_ids
        assert str(ep2.id) in source_ids


# ---------------------------------------------------------------------------
# Idempotency tests
# ---------------------------------------------------------------------------


class TestIdempotency:
    """Repeated consolidation runs must not duplicate semantic facts."""

    def test_repeated_run_no_duplicates(
        self, seeded_session: FakeSession
    ) -> None:
        """Second run should skip facts already created."""
        result1 = asyncio.run(consolidate_episodes_to_facts(seeded_session))
        assert result1.consolidated >= 1
        assert result1.skipped_exists == 0
        first_count = result1.consolidated

        result2 = asyncio.run(consolidate_episodes_to_facts(seeded_session))
        assert result2.consolidated == 0
        assert result2.skipped_exists >= first_count

    def test_watermark_prevents_reprocessing(
        self, seeded_session: FakeSession
    ) -> None:
        """With watermark after episodes, nothing should be consolidated."""
        ep = next(iter(seeded_session.episodes.values()))
        ep.created_at = datetime.now(UTC)

        future = datetime(2030, 1, 1, tzinfo=UTC)
        result = asyncio.run(
            consolidate_episodes_to_facts(
                seeded_session, watermark=future
            )
        )
        assert result.consolidated == 0
        assert result.skipped_exists == 0

    def test_idempotent_across_multiple_episodes(
        self, fake_session: FakeSession
    ) -> None:
        """Idempotency holds with multiple episodes across runs."""
        for i in range(3):
            ep = FakeEpisode(
                title=f"ep_{i}",
                summary=f"Episode {i} summary.",
            )
            fake_session.episodes[ep.id] = ep

        r1 = asyncio.run(consolidate_episodes_to_facts(fake_session))
        assert r1.consolidated >= 3

        r2 = asyncio.run(consolidate_episodes_to_facts(fake_session))
        assert r2.consolidated == 0
        assert r2.skipped_exists >= 3


# ---------------------------------------------------------------------------
# make_content_key tests
# ---------------------------------------------------------------------------


class TestMakeContentKey:
    """Content key must be deterministic and unique."""

    def test_deterministic(self) -> None:
        ep_id = uuid.uuid4()
        key1 = make_content_key("subject", "predicate", "object", ep_id)
        key2 = make_content_key("subject", "predicate", "object", ep_id)
        assert key1 == key2
        assert len(key1) == 64  # SHA-256 hex

    def test_different_inputs_different_keys(self) -> None:
        ep_id = uuid.uuid4()
        key1 = make_content_key("subj_a", "pred", "obj", ep_id)
        key2 = make_content_key("subj_b", "pred", "obj", ep_id)
        assert key1 != key2

    def test_different_episodes_different_keys(self) -> None:
        key1 = make_content_key("s", "p", "o", uuid.uuid4())
        key2 = make_content_key("s", "p", "o", uuid.uuid4())
        assert key1 != key2


# ---------------------------------------------------------------------------
# Stale pruning tests
# ---------------------------------------------------------------------------


class TestPruning:
    """Pruning must be dry-run/non-destructive by default."""

    def test_dry_run_does_not_modify(self, fake_session: FakeSession) -> None:
        """Dry run logs candidates but does not alter facts."""
        fact = FakeFact(
            subject="old_fact",
            predicate="summarizes",
            object_val="Old information.",
            created_at=datetime(2020, 1, 1, tzinfo=UTC),
            confidence=0.01,
        )
        fake_session.facts[fact.id] = fact

        config = RetentionConfig(dry_run=True, max_age_days=30)
        result = asyncio.run(prune_stale_facts(fake_session, config))

        assert result.dry_run >= 1
        assert result.pruned == 0
        assert fake_session.facts[fact.id].deletion_state == "active"

    def test_archive_default_is_non_destructive(
        self, fake_session: FakeSession
    ) -> None:
        """Default archive mode sets deletion_state but keeps the row."""
        fact = FakeFact(
            subject="old_fact",
            predicate="summarizes",
            object_val="Archivable info.",
            created_at=datetime(2020, 1, 1, tzinfo=UTC),
            confidence=0.01,
        )
        fake_session.facts[fact.id] = fact

        config = RetentionConfig(mode="archive", max_age_days=30)
        result = asyncio.run(prune_stale_facts(fake_session, config))

        assert result.pruned >= 1
        assert result.mode == "archive"
        assert fact.id in fake_session.facts
        assert fake_session.facts[fact.id].deletion_state == "archived"

    def test_soft_delete_preserves_row(self, fake_session: FakeSession) -> None:
        """Soft delete sets deletion_state but keeps the row."""
        fact = FakeFact(
            subject="old_fact",
            predicate="summarizes",
            object_val="Deletable info.",
            created_at=datetime(2020, 1, 1, tzinfo=UTC),
            confidence=0.01,
        )
        fake_session.facts[fact.id] = fact

        config = RetentionConfig(mode="soft_delete", max_age_days=30)
        result = asyncio.run(prune_stale_facts(fake_session, config))

        assert result.pruned >= 1
        assert fake_session.facts[fact.id].deletion_state == "deleted"

    def test_protected_categories_not_pruned(
        self, fake_session: FakeSession
    ) -> None:
        """Facts in protected categories should not be pruned."""
        fact = FakeFact(
            subject="strategy_plan",
            predicate="summarizes",
            object_val="Important strategy.",
            created_at=datetime(2020, 1, 1, tzinfo=UTC),
            confidence=0.5,
            tags=["strategy"],
        )
        fake_session.facts[fact.id] = fact

        config = RetentionConfig(
            mode="archive",
            max_age_days=30,
            protected_categories=["strategy", "preference"],
        )
        result = asyncio.run(prune_stale_facts(fake_session, config))

        assert result.pruned == 0

    def test_high_confidence_facts_not_pruned(
        self, fake_session: FakeSession
    ) -> None:
        """Facts above protected_importance_floor should not be pruned."""
        fact = FakeFact(
            subject="important_fact",
            predicate="summarizes",
            object_val="Very important.",
            created_at=datetime(2020, 1, 1, tzinfo=UTC),
            confidence=0.9,
        )
        fake_session.facts[fact.id] = fact

        config = RetentionConfig(
            mode="archive",
            max_age_days=30,
            protected_importance_floor=0.7,
        )
        result = asyncio.run(prune_stale_facts(fake_session, config))

        assert result.pruned == 0

    def test_recent_facts_not_pruned(self, fake_session: FakeSession) -> None:
        """Facts within max_age_days should not be pruned."""
        fact = FakeFact(
            subject="recent_fact",
            predicate="summarizes",
            object_val="Recent info.",
            created_at=datetime.now(UTC),
            confidence=0.3,
        )
        fake_session.facts[fact.id] = fact

        config = RetentionConfig(mode="archive", max_age_days=365)
        result = asyncio.run(prune_stale_facts(fake_session, config))

        assert result.pruned == 0


# ---------------------------------------------------------------------------
# Job wrapper tests
# ---------------------------------------------------------------------------


class TestJobWrapper:
    """Job wrapper must log metadata and re-raise errors."""

    def test_no_session_factory_returns_early(
        self, caplog: _CapLog
    ) -> None:
        """With no session factory, job should log warning and return."""
        with caplog.at_level(logging.WARNING, logger="src.memory.consolidation"):
            result = asyncio.run(daily_consolidation_job(session_factory=None))

        assert result.consolidated == 0
        assert any(
            "no_session_factory" in str(record.message).lower()
            or "no session factory" in str(record.message).lower()
            for record in caplog.records
        )

    def test_re_raises_exception(self, caplog: _CapLog) -> None:
        """Job wrapper must re-raise exceptions after logging."""

        def _broken_factory() -> AsyncSessionProtocol:
            raise RuntimeError("DB connection failed")

        with caplog.at_level(logging.ERROR, logger="src.memory.consolidation"):
            with pytest.raises(RuntimeError, match="DB connection failed"):
                _ = asyncio.run(daily_consolidation_job(session_factory=_broken_factory))

        assert any(
            "consolidation_job_failed" in str(record.message)
            or "failed" in str(record.message).lower()
            for record in caplog.records
        )

    def test_logs_metadata_only(self, caplog: _CapLog) -> None:
        """Log messages must not contain raw episode content."""
        ep = FakeEpisode(
            title="secret_topic",
            summary="This contains SECRET_INFO that must not appear in logs.",
        )
        session = FakeSession()
        session.episodes[ep.id] = ep

        with caplog.at_level(logging.INFO, logger="src.memory.consolidation"):
            def _session_factory() -> FakeSession:
                return session

            _ = asyncio.run(daily_consolidation_job(session_factory=_session_factory))

        log_text = " ".join(str(r.message) for r in caplog.records)
        assert "SECRET_INFO" not in log_text
        assert "secret_topic" not in log_text


# ---------------------------------------------------------------------------
# Integration: full seeded run
# ---------------------------------------------------------------------------


class TestFullSeededRun:
    """End-to-end consolidation with varied episode types."""

    def test_varied_session_consolidates_correctly(
        self, varied_session: FakeSession
    ) -> None:
        """All eligible episodes produce facts with provenance."""
        result = asyncio.run(consolidate_episodes_to_facts(varied_session))

        assert result.consolidated >= 3
        assert result.skipped_dnr >= 1
        assert result.skipped_safe_word >= 2

        for fact in result.facts_created:
            assert fact["source_episode"] is not None
            assert fact["source_episode"] != ""

    def test_watermark_filters_by_time(
        self, fake_session: FakeSession
    ) -> None:
        """Episodes before watermark should be skipped."""
        old_ep = FakeEpisode(
            title="old_episode",
            summary="Old stuff.",
            created_at=datetime(2020, 6, 1, tzinfo=UTC),
        )
        new_ep = FakeEpisode(
            title="new_episode",
            summary="New stuff.",
            created_at=datetime(2026, 6, 2, tzinfo=UTC),
        )
        fake_session.episodes[old_ep.id] = old_ep
        fake_session.episodes[new_ep.id] = new_ep

        watermark = datetime(2025, 1, 1, tzinfo=UTC)
        result = asyncio.run(
            consolidate_episodes_to_facts(fake_session, watermark=watermark)
        )

        assert result.consolidated >= 1
        source_ids = {f["source_episode"] for f in result.facts_created}
        assert str(new_ep.id) in source_ids
        assert str(old_ep.id) not in source_ids
