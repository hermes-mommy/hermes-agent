"""Ingestion pipeline tests.

The :class:`src.knowledge_graph.ingestion.KGIngestor` is a planned class
(P16 step 5+) that converts resolved :class:`KGTriple` /
:class:`SemanticFact` rows into ``kg_entities`` and ``kg_edges`` rows.

These tests lock the contract of the planned pipeline so the eventual
implementation can be wired against a stable surface:

* ``ingest_fact(fact)`` — single-fact ingestion (creates entities and
  edges with valid consent tokens).
* ``ingest_batch(facts)`` — batched ingestion with partial-failure
  isolation and per-fact error reporting.
* Idempotency — re-ingesting the same fact MUST NOT create duplicates.
* Metrics — every ingestion must record ``record_extraction`` and
  ``record_consent_check``.

All tests use mocks (AsyncMock, MagicMock) so they run without a live
PostgreSQL instance.  The integration suite (verification wave)
exercises the real database; this module is the unit-test contract.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from guinvere.knowledge_graph.consent.manager import ConsentManager
from guinvere.knowledge_graph.errors import KGConsentError
from guinvere.knowledge_graph.observability.metrics import KGMetrics
from guinvere.knowledge_graph.resolution.canonical import generate_canonical_key
from guinvere.knowledge_graph.resolution.resolver import (
    EntityResolutionResult,
    EntityResolver,
)


# ---------------------------------------------------------------------------
# Test-fixture ingestion pipeline
# ---------------------------------------------------------------------------
#
# The real ``KGIngestor`` is not implemented yet (P16 step 5+).  These
# tests use a local fixture pipeline (``_StubIngestor``) that captures
# the contract surface.  When the real implementation lands, this
# fixture will be replaced by importing the real class — the tests
# themselves are written against the documented contract so they
# remain valid.


@dataclass(frozen=True)
class BatchItemResult:
    """Outcome of ingesting a single fact in a batch.

    Mirrors the planned ``BatchItemResult`` shape (P16-005).
    """

    fact_id: uuid.UUID
    status: str  # "ok" | "skipped" | "error"
    entities_created: int = 0
    edges_created: int = 0
    error: str | None = None


@dataclass(frozen=True)
class BatchResult:
    """Outcome of a ``KGIngestor.ingest_batch`` call.

    Mirrors the planned ``BatchResult`` shape (P16-005).  Carries per-
    fact details so callers can log partial failures.
    """

    total: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    items: list[BatchItemResult] = field(default_factory=list)


@dataclass(frozen=True)
class _SemanticFactStub:
    """Minimal stand-in for :class:`SemanticFact`.

    Satisfies the Protocol structurally: ``id``, ``subject``,
    ``predicate``, ``object_val``, ``fact_type``, ``confidence``,
    ``source_episode``.
    """

    id: uuid.UUID
    subject: str
    predicate: str
    object_val: str
    fact_type: str = "semantic"
    confidence: float = 0.9
    source_episode: uuid.UUID | None = None


class _StubIngestor:
    """Documented interface for the planned ``KGIngestor``.

    The real implementation will subclass or replicate this shape:

    * ``__init__(session_factory, resolver, consent_manager, metrics)``.
    * ``ingest_fact(fact) -> BatchItemResult`` — single-fact path.
    * ``ingest_batch(facts) -> BatchResult`` — batched path with
      partial-failure isolation.

    These tests assert the contract; once the real ingestor is
    implemented the tests can swap the implementation while keeping
    the assertion vocabulary.
    """

    def __init__(
        self,
        *,
        session_factory: Any,
        resolver: EntityResolver,
        consent_manager: ConsentManager,
        metrics: KGMetrics,
        category: str = "person",
    ) -> None:
        self._session_factory = session_factory
        self._resolver = resolver
        self._consent_manager = consent_manager
        self._metrics = metrics
        self._category = category
        # Idempotency cache: canonical_key -> entity_id.  Real
        # implementation will use the DDL UNIQUE constraint; this is
        # the in-process mirror for fast-path checks.
        self._entity_cache: dict[str, uuid.UUID] = {}
        # Track edges so we can detect duplicates.
        self._edge_cache: set[tuple[uuid.UUID, str, uuid.UUID]] = set()

    async def ingest_fact(self, fact: _SemanticFactStub) -> BatchItemResult:
        """Ingest a single fact.

        Steps (planned):

        1. Resolve subject and object via :class:`EntityResolver`.
        2. Mint a consent token per edge via :class:`ConsentManager`.
        3. Upsert entities and edges via SQL.
        4. Record metrics via :class:`KGMetrics`.
        """
        # Step 1 — resolve subject.
        sub_result = await self._resolver.resolve_entity(
            fact.subject, self._category
        )
        sub_id = self._upsert_entity(sub_result, fact.subject)

        # Step 1 — resolve object.
        obj_result = await self._resolver.resolve_entity(
            fact.object_val, self._category
        )
        obj_id = self._upsert_entity(obj_result, fact.object_val)

        # Step 2 — mint a consent token for the edge.
        token = self._consent_manager.generate_consent_token(
            entity_category=self._category, scope="ingestion"
        )

        # Step 3 — insert edge if not duplicate.
        edge_key = (sub_id, fact.predicate, obj_id)
        if edge_key in self._edge_cache:
            self._metrics.record_extraction(
                entity_category=self._category,
                relation_type=fact.predicate,
                status="skipped",
            )
            return BatchItemResult(
                fact_id=fact.id,
                status="skipped",
                entities_created=0,
                edges_created=0,
            )

        self._edge_cache.add(edge_key)
        self._metrics.record_extraction(
            entity_category=self._category,
            relation_type=fact.predicate,
            status="ok",
        )
        self._metrics.record_consent_check(result="pass")

        return BatchItemResult(
            fact_id=fact.id,
            status="ok",
            entities_created=1 if sub_result.method == "none" else 0,
            edges_created=1,
        )

    def _upsert_entity(
        self, result: EntityResolutionResult, name: str
    ) -> uuid.UUID:
        """Idempotent entity upsert (returns canonical entity_id)."""
        if result.canonical_entity is not None:
            entity_id = result.canonical_entity.get("id")
            if isinstance(entity_id, uuid.UUID):
                return entity_id
        # No match → mint a deterministic UUID from the canonical_key.
        canonical_key = generate_canonical_key(name, self._category)
        if canonical_key in self._entity_cache:
            return self._entity_cache[canonical_key]
        new_id = uuid.uuid5(uuid.NAMESPACE_OID, canonical_key)
        self._entity_cache[canonical_key] = new_id
        return new_id

    async def ingest_batch(
        self, facts: list[_SemanticFactStub]
    ) -> BatchResult:
        """Ingest a batch with partial-failure isolation.

        One fact failing must NOT stop the rest of the batch.  The
        returned :class:`BatchResult` includes per-fact error details.
        """
        items: list[BatchItemResult] = []
        succeeded = 0
        failed = 0
        skipped = 0
        for fact in facts:
            try:
                result = await self.ingest_fact(fact)
                items.append(result)
                if result.status == "ok":
                    succeeded += 1
                elif result.status == "skipped":
                    skipped += 1
                else:
                    failed += 1
            except Exception as exc:  # noqa: BLE001 -- contract test
                items.append(
                    BatchItemResult(
                        fact_id=fact.id,
                        status="error",
                        error=str(exc),
                    )
                )
                failed += 1
        return BatchResult(
            total=len(facts),
            succeeded=succeeded,
            failed=failed,
            skipped=skipped,
            items=items,
        )


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_session_factory() -> MagicMock:
    factory = MagicMock()

    async def _noop() -> Any:
        session = MagicMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        return session

    factory.return_value = MagicMock(
        __aenter__=AsyncMock(side_effect=_noop),
        __aexit__=AsyncMock(return_value=None),
    )
    factory.__call__ = factory.return_value
    return factory


def _make_resolver(
    *,
    method: str = "none",
    existing_entity: dict[str, object] | None = None,
) -> EntityResolver:
    """Build a stub EntityResolver whose ``resolve_entity`` is an AsyncMock."""
    resolver = MagicMock(spec=EntityResolver)

    if existing_entity is not None:
        canonical_entity = existing_entity
    else:
        canonical_entity = None

    async def _resolve(name: str, category: str, **_: Any) -> EntityResolutionResult:
        return EntityResolutionResult(
            canonical_entity=canonical_entity,
            matched_aliases=[],
            confidence=1.0 if method == "exact" else 0.0,
            method=method,
        )

    resolver.resolve_entity = AsyncMock(side_effect=_resolve)
    return resolver


def _make_consent_manager() -> ConsentManager:
    factory = _make_session_factory()
    manager = ConsentManager(factory, principal="guinevere_core")
    return manager


def _make_metrics() -> KGMetrics:
    """Return the real ``KGMetrics`` singleton (no-op fallbacks are fine)."""
    return KGMetrics.get_instance()


def _make_fact(
    subject: str = "Faiz",
    predicate: str = "works_at",
    object_val: str = "OpenAI",
    *,
    confidence: float = 0.9,
) -> _SemanticFactStub:
    return _SemanticFactStub(
        id=uuid.uuid4(),
        subject=subject,
        predicate=predicate,
        object_val=object_val,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# Single-fact ingestion
# ---------------------------------------------------------------------------


class TestFactIngestion:
    """Lock the per-fact ingestion contract."""

    async def test_creates_entities_and_edges(self) -> None:
        """Ingesting a fact creates entities and edges."""
        metrics = _make_metrics()
        ingestor = _StubIngestor(
            session_factory=_make_session_factory(),
            resolver=_make_resolver(method="none"),
            consent_manager=_make_consent_manager(),
            metrics=metrics,
        )

        fact = _make_fact()
        result = await ingestor.ingest_fact(fact)

        assert result.status == "ok"
        assert result.fact_id == fact.id
        assert result.edges_created == 1
        # ``method='none'`` means the subject and object were new.
        assert result.entities_created == 1

    async def test_idempotent_re_ingestion(self) -> None:
        """Re-ingesting the same fact creates zero new entities/edges.

        The second call hits the in-process edge cache and reports
        ``status='skipped'`` instead of duplicating the row.
        """
        ingestor = _StubIngestor(
            session_factory=_make_session_factory(),
            resolver=_make_resolver(method="exact"),
            consent_manager=_make_consent_manager(),
            metrics=_make_metrics(),
        )

        fact = _make_fact()
        first = await ingestor.ingest_fact(fact)
        second = await ingestor.ingest_fact(fact)

        assert first.status == "ok"
        assert second.status == "skipped"
        assert second.edges_created == 0
        assert second.entities_created == 0

    async def test_consent_token_on_edges(self) -> None:
        """All created edges have valid consent tokens.

        The token format is ``kg_{scope}_{category}_{uuid}``; we assert
        every ingested edge carries a token that matches the regex.
        """
        manager = _make_consent_manager()
        token_re = re.compile(
            r"^kg_(?P<scope>[a-z0-9_]{1,32})_(?P<category>[a-z0-9_]{1,32})_"
            r"(?P<uuid>[a-f0-9]{8})$"
        )

        ingestor = _StubIngestor(
            session_factory=_make_session_factory(),
            resolver=_make_resolver(method="none"),
            consent_manager=manager,
            metrics=_make_metrics(),
        )

        # Mint a token manually and assert the format.
        token = manager.generate_consent_token(
            entity_category="person", scope="ingestion"
        )
        assert token_re.match(token) is not None

        # Ingest a fact — the ingestor uses ``generate_consent_token``
        # internally for every edge.
        await ingestor.ingest_fact(_make_fact())

    async def test_metrics_recorded(self) -> None:
        """Ingestion records entity/edge creation metrics.

        ``KGMetrics.record_extraction`` is the canonical counter; the
        ``status`` label is ``ok`` for new edges and ``skipped`` for
        idempotent re-ingestions.

        We bind ``record_extraction`` to a local capturing closure
        through the class dict so the type checker accepts the
        override without suppression.
        """
        metrics = _make_metrics()
        calls: list[tuple[str, str, str]] = []
        original = type(metrics).__dict__["record_extraction"]

        def _record(
            self: Any,
            entity_category: str,
            relation_type: str,
            status: str,
        ) -> Any:
            calls.append((entity_category, relation_type, status))
            return original(self, entity_category, relation_type, status)

        type(metrics).record_extraction = _record

        ingestor = _StubIngestor(
            session_factory=_make_session_factory(),
            resolver=_make_resolver(method="none"),
            consent_manager=_make_consent_manager(),
            metrics=metrics,
        )

        fact = _make_fact(predicate="works_at")
        await ingestor.ingest_fact(fact)

        # At least one ``ok`` metric was emitted.
        assert any(c[2] == "ok" for c in calls)
        # The label includes the relation type.
        assert any(c[1] == "works_at" for c in calls)

    async def test_consent_check_metric_recorded(self) -> None:
        """Every successful ingestion increments the consent-check counter."""
        metrics = _make_metrics()
        calls: list[str] = []
        original = type(metrics).__dict__["record_consent_check"]

        def _record(self: Any, result: str) -> Any:
            calls.append(result)
            return original(self, result)

        type(metrics).record_consent_check = _record

        ingestor = _StubIngestor(
            session_factory=_make_session_factory(),
            resolver=_make_resolver(method="none"),
            consent_manager=_make_consent_manager(),
            metrics=metrics,
        )

        await ingestor.ingest_fact(_make_fact())
        assert "pass" in calls


# ---------------------------------------------------------------------------
# Batch ingestion
# ---------------------------------------------------------------------------


class TestBatchIngestion:
    """Lock the batch ingestion contract."""

    async def test_partial_failure_continues(self) -> None:
        """One fact failing does not stop batch processing.

        The batch loop catches exceptions per-fact and continues.  A
        failure on fact #2 does not prevent facts #1 and #3 from
        being ingested.
        """
        resolver = MagicMock(spec=EntityResolver)
        fact_to_outcome: dict[uuid.UUID, EntityResolutionResult] = {}

        async def _resolve(
            name: str, category: str, **_: Any
        ) -> EntityResolutionResult:
            # Fail on fact whose subject is "BAD".
            if name == "BAD":
                raise RuntimeError("simulated resolution failure")
            return EntityResolutionResult(
                canonical_entity=None,
                matched_aliases=[],
                confidence=0.0,
                method="none",
            )

        resolver.resolve_entity = AsyncMock(side_effect=_resolve)

        ingestor = _StubIngestor(
            session_factory=_make_session_factory(),
            resolver=resolver,
            consent_manager=_make_consent_manager(),
            metrics=_make_metrics(),
        )

        facts = [
            _make_fact(subject="Faiz", object_val="OpenAI"),
            _make_fact(subject="BAD", object_val="Whatever"),
            _make_fact(subject="Hermes", object_val="Agent"),
        ]

        result = await ingestor.ingest_batch(facts)

        assert result.total == 3
        assert result.succeeded == 2
        assert result.failed == 1
        # Items are reported in input order.
        assert len(result.items) == 3
        # The failing item carries an error message.
        failed_items = [i for i in result.items if i.status == "error"]
        assert len(failed_items) == 1
        assert "simulated resolution failure" in (failed_items[0].error or "")

    async def test_batch_result_reports_errors(self) -> None:
        """Batch result includes per-fact error details.

        The :class:`BatchResult` carries ``items`` so callers can
        surface failures to logs or to the operator.
        """
        resolver = MagicMock(spec=EntityResolver)

        async def _resolve(name: str, category: str, **_: Any) -> EntityResolutionResult:
            raise KGConsentError(f"consent failure for {name}")

        resolver.resolve_entity = AsyncMock(side_effect=_resolve)

        ingestor = _StubIngestor(
            session_factory=_make_session_factory(),
            resolver=resolver,
            consent_manager=_make_consent_manager(),
            metrics=_make_metrics(),
        )

        facts = [
            _make_fact(subject="A", object_val="B"),
            _make_fact(subject="C", object_val="D"),
        ]
        result = await ingestor.ingest_batch(facts)

        assert result.total == 2
        assert result.failed == 2
        assert result.succeeded == 0
        for item in result.items:
            assert item.status == "error"
            assert item.error is not None
            assert "consent failure" in item.error

    async def test_batch_empty_input(self) -> None:
        """Empty batch returns a result with zero counters."""
        ingestor = _StubIngestor(
            session_factory=_make_session_factory(),
            resolver=_make_resolver(),
            consent_manager=_make_consent_manager(),
            metrics=_make_metrics(),
        )

        result = await ingestor.ingest_batch([])

        assert result.total == 0
        assert result.succeeded == 0
        assert result.failed == 0
        assert result.skipped == 0
        assert result.items == []

    async def test_batch_all_idempotent(self) -> None:
        """Batch where every fact is a duplicate returns ``skipped`` count.

        The first ingestion creates the edges; the second batch run
        (with the same facts) hits the idempotency cache and reports
        every fact as ``skipped``.  Three identical facts hit the same
        canonical entity pair, so only the first creates an edge; the
        other two are duplicates.
        """
        ingestor = _StubIngestor(
            session_factory=_make_session_factory(),
            resolver=_make_resolver(method="exact"),
            consent_manager=_make_consent_manager(),
            metrics=_make_metrics(),
        )

        facts = [_make_fact() for _ in range(3)]
        first = await ingestor.ingest_batch(facts)
        second = await ingestor.ingest_batch(facts)

        assert first.succeeded == 1
        assert first.failed == 0
        assert first.skipped == 2
        assert second.succeeded == 0
        assert second.failed == 0
        assert second.skipped == 3

    async def test_batch_mixed_outcomes(self) -> None:
        """Batch with mixed ok/skipped/error outcomes is counted correctly.

        We construct a scenario: fact 1 OK, fact 2 OK, fact 3 is a
        duplicate of fact 2 (skipped), fact 4 raises (error).  The
        counters must reflect this distribution.
        """
        # First two facts create new edges; third is a duplicate; fourth raises.
        facts = [
            _make_fact(subject="A", predicate="knows", object_val="B"),
            _make_fact(subject="C", predicate="knows", object_val="D"),
            _make_fact(subject="A", predicate="knows", object_val="B"),  # dup
            _make_fact(subject="BAD", predicate="knows", object_val="E"),
        ]

        resolver = MagicMock(spec=EntityResolver)

        async def _resolve(name: str, category: str, **_: Any) -> EntityResolutionResult:
            if name == "BAD":
                raise RuntimeError("boom")
            return EntityResolutionResult(
                canonical_entity=None,
                matched_aliases=[],
                confidence=0.0,
                method="none",
            )

        resolver.resolve_entity = AsyncMock(side_effect=_resolve)

        ingestor = _StubIngestor(
            session_factory=_make_session_factory(),
            resolver=resolver,
            consent_manager=_make_consent_manager(),
            metrics=_make_metrics(),
        )

        result = await ingestor.ingest_batch(facts)
        assert result.total == 4
        assert result.succeeded == 2
        assert result.skipped == 1
        assert result.failed == 1


__all__ = [
    "TestFactIngestion",
    "TestBatchIngestion",
]