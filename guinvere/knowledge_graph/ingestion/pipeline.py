"""P16-002: Knowledge Graph ingestion pipeline (Wave 3).

This module implements the **post-consolidation ingestion hook** that
converts ``memory.semantic_facts`` rows produced by
:func:`guinvere.memory.consolidation.consolidate_episodes_to_facts` into
``memory.kg_entities`` and ``memory.kg_edges`` rows.

The pipeline orchestrates five collaborators that are injected at
construction time:

* :class:`guinvere.knowledge_graph.extraction.entity_extractor.EntityExtractor`
  — L1+L2 NER over the subject / object slots of a fact.
* :class:`guinvere.knowledge_graph.resolution.resolver.EntityResolver`
  — L1 → L1b → L2 deduplication of extracted entities against the live KG.
* :class:`guinvere.knowledge_graph.extraction.relation_extractor.RelationExtractor`
  — L1+L2 predicate → :class:`RelationType` mapping.
* :class:`guinvere.knowledge_graph.consent.manager.ConsentManager`
  — issuance of consent tokens attached to every new edge.
* :class:`guinvere.knowledge_graph.observability.metrics.KGMetrics`
  — Prometheus counters / histograms for observability.

Flow per fact (see :meth:`KGIngestionPipeline._ingest_fact_in_session`):

    1. Extract entities from ``fact.subject`` and ``fact.object_val``.
    2. Resolve each entity — reuse existing canonical ID or create a new
       ``kg_entities`` row (idempotent via ``ON CONFLICT (canonical_key) DO
       UPDATE SET updated_at = kg_entities.updated_at RETURNING id``).
    3. Extract relations from the typed entities + source predicate.
    4. Mint a fresh consent token via the :class:`ConsentManager`.
    5. Insert each edge into ``kg_edges`` with
       ``ON CONFLICT (src_entity_id, dst_entity_id, relationship_type,
        source_fact_id) DO NOTHING`` — the DDL UNIQUE constraint enforces
       idempotency so re-ingesting the same fact is a safe no-op.
    6. Record Prometheus metrics.

Safety / consent notes (per AGENTS.md BLOCKING rules and
PersonaSafetyPolicy):

* The pipeline **never** touches ``memory.episodes`` for safe-word checks
  — that gate is owned by the consent manager / extraction layer.  Hard
  stop propagation is the responsibility of the caller (the cron job).
* Ingestion runs in the cron path, NEVER in the request hot path —
  bulk writes are bounded by ``BatchProcessor`` backpressure.
* No type suppression: every parameter, every return value, every SQL
  bind is statically typed.
* No empty catches: every exception is logged with full context and
  the per-fact error list captures it so the batch continues.
"""
from __future__ import annotations

import logging
import uuid
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol, cast

from sqlalchemy import text as _sa_text

from guinvere.knowledge_graph.consent.manager import ConsentManager
from guinvere.knowledge_graph.errors import KGIngestionError
from guinvere.knowledge_graph.extraction.entity_extractor import EntityExtractor
from guinvere.knowledge_graph.extraction.relation_extractor import RelationExtractor
from guinvere.knowledge_graph.observability.metrics import KGMetrics
from guinvere.knowledge_graph.resolution.canonical import (
    AsyncSessionProtocol,
    generate_canonical_key,
)
from guinvere.knowledge_graph.resolution.resolver import EntityResolver
from guinvere.knowledge_graph.types import (
    EntityCategory,
    ExtractedEntity,
    ExtractedRelation,
    RelationType,
    SemanticFact,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

UTC = timezone.utc

KG_ENTITIES_TABLE: str = "memory.kg_entities"
"""Fully-qualified ``kg_entities`` table — upsert target."""

KG_EDGES_TABLE: str = "memory.kg_edges"
"""Fully-qualified ``kg_edges`` table — insert target."""

DEFAULT_CONSENT_SCOPE: str = "kg_ingestion"
"""Default scope string for ``ConsentManager.generate_consent_token``.

Kept short and lowercase so it satisfies :data:`ConsentManager._SAFE_SCOPE_RE`
(``^[a-z0-9_]{1,32}$``).  Length = 13 chars."""

DEFAULT_CLASSIFICATION: str = "Restricted"
"""Classification applied to entities / edges created by the pipeline.

Mirrors the ``ClassificationMetaMixin`` server default and the consolidation
contract — see ``guinvere.memory.models``."""

SOURCE_LABEL: str = "kg_ingestion"
"""Value stored in ``kg_entities.first_seen_source`` for new entities.

Audit-friendly string that survives table scans; matches the
``DEFAULT_CONSENT_SCOPE`` token but kept as a separate constant so it can
evolve independently."""


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IngestionResult:
    """Outcome of :meth:`KGIngestionPipeline.ingest_fact`.

    Attributes:
        entities_created: Number of brand-new ``kg_entities`` rows inserted
            during this fact's ingestion.  Zero when every mention resolved
            to an existing canonical entity.
        entities_resolved: Number of mentions that collapsed onto a
            pre-existing entity (L1 / L1b / L2 hit).
        edges_created: Number of new ``kg_edges`` rows inserted.  Always
            ``<= 1`` for the L1+L2 path because each fact produces at most
            one relation.
        edges_skipped_duplicate: Number of edge INSERTs that hit the
            DDL UNIQUE constraint and were silently ignored (re-ingest).
        fact_id: UUID of the source ``memory.semantic_facts`` row.
        errors: Per-fact error messages.  Empty on success.
    """

    entities_created: int = 0
    entities_resolved: int = 0
    edges_created: int = 0
    edges_skipped_duplicate: int = 0
    fact_id: uuid.UUID | None = None
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class BatchIngestionResult:
    """Aggregate outcome of a batch ingestion call.

    Attributes:
        total_facts: Number of facts that were attempted.
        total_entities_created: Sum of ``IngestionResult.entities_created``.
        total_entities_resolved: Sum of ``IngestionResult.entities_resolved``.
        total_edges_created: Sum of ``IngestionResult.edges_created``.
        total_edges_skipped_duplicate: Sum of
            ``IngestionResult.edges_skipped_duplicate``.
        total_errors: Count of per-fact errors across the batch.
        per_fact: Per-fact outcomes — order matches the input list.
    """

    total_facts: int = 0
    total_entities_created: int = 0
    total_entities_resolved: int = 0
    total_edges_created: int = 0
    total_edges_skipped_duplicate: int = 0
    total_errors: int = 0
    per_fact: list[IngestionResult] = field(default_factory=list)


# ---------------------------------------------------------------------------
# SQL statements
# ---------------------------------------------------------------------------

# Idempotent entity upsert.  ``ON CONFLICT (canonical_key) DO UPDATE SET
# updated_at = kg_entities.updated_at`` is a deliberate no-op — it forces
# Postgres to return the row via ``RETURNING id`` whether the row was new
# (INSERT path) or pre-existing (UPDATE path with no side effects).
_ENTITY_UPSERT_SQL: str = (
    "INSERT INTO memory.kg_entities ("
    "id, canonical_key, entity_type, display_name, aliases, "
    "first_seen_source, first_seen_at, classification, deletion_state, "
    "created_at, updated_at"
    ") VALUES ("
    ":id, :canonical_key, :entity_type, :display_name, :aliases, "
    ":first_seen_source, NOW(), :classification, 'active', "
    "NOW(), NOW()"
    ") "
    "ON CONFLICT (canonical_key) DO UPDATE "
    "SET updated_at = memory.kg_entities.updated_at "
    "RETURNING id, (xmax = 0) AS was_inserted"
)


# Edge INSERT — idempotent via the DDL UNIQUE constraint
# (src_entity_id, dst_entity_id, relationship_type, source_fact_id).
# ``ON CONFLICT DO NOTHING`` + ``RETURNING id`` lets us detect duplicates
# from the rowcount (RETURNING is empty on conflict).
_EDGE_INSERT_SQL: str = (
    "INSERT INTO memory.kg_edges ("
    "id, src_entity_id, dst_entity_id, relationship_type, confidence, "
    "weight, context_sentence, source_fact_id, kg_episode_id, "
    "source_id, consent_token, consent_scope, extractor_model, review_status, "
    "valid_from, valid_to, recorded_at, is_tombstoned, attributes"
    ") VALUES ("
    ":id, :src_entity_id, :dst_entity_id, :relationship_type, :confidence, "
    ":weight, :context_sentence, :source_fact_id, :kg_episode_id, "
    ":source_id, :consent_token, :consent_scope, :extractor_model, :review_status, "
    "NOW(), NULL, NOW(), FALSE, CAST(:attributes AS JSONB)"
    ") "
    "ON CONFLICT (src_entity_id, dst_entity_id, relationship_type, source_fact_id) "
    "DO NOTHING "
    "RETURNING id"
)


# ---------------------------------------------------------------------------
# Protocols — kept narrow so test fakes can satisfy them with no DB driver.
# ---------------------------------------------------------------------------


class _SessionFactory(Protocol):
    """Minimal async session-factory protocol used by the pipeline.

    Mirrors :class:`guinvere.knowledge_graph.consent.manager._SessionFactory` so
    the same factory implementation can be shared across the KG module.
    The factory must return an :class:`AsyncSessionProtocol`-compatible
    object usable as ``async with factory() as session: ...``.
    """

    def __call__(self) -> AsyncSessionProtocol:  # pragma: no cover -- structural
        ...


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bind_params(statement: object, params: dict[str, object]) -> object:
    """Bind named parameters to a SQL string.

    Same idiom as
    :func:`guinvere.knowledge_graph.resolution.canonical._bind_params` — kept
    local so this module does not need to import a private helper from a
    sibling module (which would couple them at the import level).
    """
    bind = getattr(statement, "bindparams", None)
    if callable(bind):
        return bind(**params)
    return statement


def _coerce_uuid(value: object, *, context: str) -> uuid.UUID:
    """Best-effort UUID coercion.  Raises :class:`KGIngestionError` on failure.

    Centralises the error message so every call site has a consistent
    ``context`` field for audit logs.
    """
    if isinstance(value, uuid.UUID):
        return value
    if isinstance(value, str) and value:
        try:
            return uuid.UUID(value)
        except (TypeError, ValueError) as exc:
            raise KGIngestionError(
                f"could not coerce UUID from {context}",
                context={"got_type": type(value).__name__, "got_value": repr(value)},
            ) from exc
    raise KGIngestionError(
        f"missing or non-UUID value for {context}",
        context={"got_type": type(value).__name__, "got_value": repr(value)},
    )


def _row_first_uuid(row: object, field_name: str = "id") -> uuid.UUID | None:
    """Extract a UUID from the first column of a SQLAlchemy result row.

    Returns ``None`` for an empty row (e.g. ON CONFLICT DO NOTHING).
    """
    if row is None:
        return None
    mapping = getattr(row, "_mapping", None)
    raw: object
    if mapping is not None:
        try:
            raw = mapping[field_name]
        except (KeyError, TypeError, ValueError):
            raw = row[0] if len(row) > 0 else None
    else:
        raw = getattr(row, field_name, None)
        if raw is None and len(getattr(row, "__iter__", lambda: ()))() if callable(getattr(row, "__iter__", None)) else False:
            try:
                raw = row[0]
            except (IndexError, TypeError):
                raw = None
    if raw is None:
        return None
    if isinstance(raw, uuid.UUID):
        return raw
    if isinstance(raw, str) and raw:
        try:
            return uuid.UUID(raw)
        except (TypeError, ValueError):
            return None
    return None


def _row_first_bool(row: object, field_name: str) -> bool:
    """Extract a boolean from a SQLAlchemy result row.

    Used for the ``(xmax = 0) AS was_inserted`` column returned by the
    entity upsert — ``xmax = 0`` is the canonical Postgres trick to
    distinguish a freshly-inserted row from a pre-existing one.
    """
    if row is None:
        return False
    mapping = getattr(row, "_mapping", None)
    raw: object
    if mapping is not None:
        try:
            raw = mapping[field_name]
        except (KeyError, TypeError, ValueError):
            raw = None
    else:
        raw = getattr(row, field_name, None)
    return bool(raw)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


class KGIngestionPipeline:
    """Orchestrates KG entity+edge creation from semantic facts.

    The pipeline is constructed once with all six collaborators and reused
    across facts.  It is safe to share across asyncio tasks as long as the
    underlying session factory is safe (no global state is held).

    The class is **not** thread-safe for concurrent ``ingest_fact`` calls
    on the same instance (sessions are per-call but the ``metrics``
    singleton is shared and prometheus_client is internally locked).
    """

    def __init__(
        self,
        session_factory: Callable[[], AsyncSessionProtocol],
        entity_extractor: EntityExtractor,
        entity_resolver: EntityResolver,
        relation_extractor: RelationExtractor,
        consent_manager: ConsentManager,
        metrics: KGMetrics,
        *,
        consent_scope: str = DEFAULT_CONSENT_SCOPE,
        classification: str = DEFAULT_CLASSIFICATION,
    ) -> None:
        if session_factory is None:
            raise ValueError("session_factory is required")
        if entity_extractor is None:
            raise ValueError("entity_extractor is required")
        if entity_resolver is None:
            raise ValueError("entity_resolver is required")
        if relation_extractor is None:
            raise ValueError("relation_extractor is required")
        if consent_manager is None:
            raise ValueError("consent_manager is required")
        if metrics is None:
            raise ValueError("metrics is required")
        if not consent_scope or not consent_scope.strip():
            raise ValueError("consent_scope must be a non-empty string")
        if not classification or not classification.strip():
            raise ValueError("classification must be a non-empty string")

        self._session_factory: Callable[[], AsyncSessionProtocol] = session_factory
        self._entity_extractor: EntityExtractor = entity_extractor
        self._entity_resolver: EntityResolver = entity_resolver
        self._relation_extractor: RelationExtractor = relation_extractor
        self._consent_manager: ConsentManager = consent_manager
        self._metrics: KGMetrics = metrics
        self._consent_scope: str = consent_scope.strip()
        self._classification: str = classification.strip()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def ingest_fact(self, fact: SemanticFact) -> IngestionResult:
        """Process a single semantic fact into KG entities + edges.

        Opens a fresh session via :attr:`session_factory`, runs the
        ingestion flow, commits, and returns the per-fact outcome.

        Partial failures are captured in :attr:`IngestionResult.errors`
        and the pipeline never raises for per-fact errors — the caller
        can choose to retry or surface the error list.

        The function does raise :class:`KGIngestionError` when the
        source fact itself is structurally invalid (missing UUID, etc.).
        """
        fact_id = _coerce_uuid(getattr(fact, "id", None), context="fact.id")
        started = datetime.now(UTC)
        try:
            async with self._session_factory() as session:
                result = await self._ingest_fact_in_session(fact, session)
                await session.commit()
        except KGIngestionError:
            raise
        except Exception as exc:  # noqa: BLE001 -- defensive boundary
            logger.exception(
                "kg_ingest_fatal",
                extra={"fact_id": str(fact_id), "error": repr(exc)},
            )
            return IngestionResult(
                fact_id=fact_id,
                errors=[f"fatal:{type(exc).__name__}:{exc}"],
            )
        finally:
            elapsed = (datetime.now(UTC) - started).total_seconds()
            self._metrics.observe_ingestion_duration("fact", max(elapsed, 0.0))
        return result

    async def ingest_batch(
        self,
        facts: Sequence[SemanticFact],
        *,
        batch_size: int = 100,
    ) -> BatchIngestionResult:
        """Process multiple facts in batch.

        Each fact is processed independently inside one transaction per
        ``batch_size`` chunk.  A failure on one fact is logged and captured
        in the per-fact :class:`IngestionResult.errors` list — the rest of
        the batch continues.  This mirrors the resilience policy in
        ``guinvere.memory.consolidation.consolidate_episodes_to_facts`` (DNR /
        safe-word skips are isolated; the job never short-circuits on a
        single bad row).

        Parameters
        ----------
        facts:
            Facts to ingest.  Order is preserved in ``per_fact``.
        batch_size:
            Maximum facts per database transaction.  Smaller batches keep
            transactions short at the cost of more round-trips; larger
            batches amortise commit cost.  Default ``100`` matches
            :data:`KGConfig.kg_batch_size`.
        """
        if not facts:
            return BatchIngestionResult(total_facts=0, per_fact=[])
        if batch_size < 1:
            raise ValueError(f"batch_size must be >= 1; got {batch_size}")

        started = datetime.now(UTC)
        per_fact: list[IngestionResult] = []
        total_entities_created = 0
        total_entities_resolved = 0
        total_edges_created = 0
        total_edges_skipped = 0
        total_errors = 0

        for chunk_start in range(0, len(facts), batch_size):
            chunk = list(facts[chunk_start : chunk_start + batch_size])
            try:
                async with self._session_factory() as session:
                    for fact in chunk:
                        fact_id = _coerce_uuid(
                            getattr(fact, "id", None), context="fact.id"
                        )
                        try:
                            result = await self._ingest_fact_in_session(fact, session)
                        except KGIngestionError as exc:
                            logger.warning(
                                "kg_ingest_fact_skipped",
                                extra={
                                    "fact_id": str(fact_id),
                                    "error": exc.message,
                                },
                            )
                            result = IngestionResult(
                                fact_id=fact_id,
                                errors=[f"skipped:{exc.message}"],
                            )
                        except Exception as exc:  # noqa: BLE001 -- per-fact isolation
                            logger.exception(
                                "kg_ingest_fact_error",
                                extra={
                                    "fact_id": str(fact_id),
                                    "error": repr(exc),
                                },
                            )
                            result = IngestionResult(
                                fact_id=fact_id,
                                errors=[f"error:{type(exc).__name__}:{exc}"],
                            )
                        per_fact.append(result)
                        total_entities_created += result.entities_created
                        total_entities_resolved += result.entities_resolved
                        total_edges_created += result.edges_created
                        total_edges_skipped += result.edges_skipped_duplicate
                        total_errors += len(result.errors)
                    await session.commit()
            except Exception as exc:  # noqa: BLE001 -- chunk-level isolation
                logger.exception(
                    "kg_ingest_chunk_failed",
                    extra={
                        "chunk_start": chunk_start,
                        "chunk_size": len(chunk),
                        "error": repr(exc),
                    },
                )
                # Whole chunk failed — synthesize error results so the
                # caller still gets a per-fact list of the right length.
                for fact in chunk:
                    fact_id = _coerce_uuid(
                        getattr(fact, "id", None), context="fact.id"
                    )
                    per_fact.append(
                        IngestionResult(
                            fact_id=fact_id,
                            errors=[f"chunk_fatal:{type(exc).__name__}:{exc}"],
                        )
                    )
                    total_errors += 1

        elapsed = (datetime.now(UTC) - started).total_seconds()
        self._metrics.observe_ingestion_duration("batch", max(elapsed, 0.0))
        return BatchIngestionResult(
            total_facts=len(facts),
            total_entities_created=total_entities_created,
            total_entities_resolved=total_entities_resolved,
            total_edges_created=total_edges_created,
            total_edges_skipped_duplicate=total_edges_skipped,
            total_errors=total_errors,
            per_fact=per_fact,
        )

    async def ingest_from_consolidation(
        self,
        consolidation_result: object,
        session: AsyncSessionProtocol,
    ) -> BatchIngestionResult:
        """Post-consolidation hook: ingest all newly created ``semantic_facts``.

        Looks up the :class:`memory.models.SemanticFacts` rows referenced by
        ``consolidation_result.facts_created`` inside the supplied
        *session* (which is expected to share the consolidation
        transaction so uncommitted additions are visible), then runs the
        standard per-fact ingestion flow against the same session.

        This function does **not** commit *session* — the caller owns the
        outer transaction.  Per-fact failures are isolated (logged +
        captured in the per-fact error list); a single bad fact never
        aborts the consolidation transaction.

        Parameters
        ----------
        consolidation_result:
            The :class:`guinvere.memory.consolidation.ConsolidationResult`
            returned by ``consolidate_episodes_to_facts``.  Treated as an
            opaque object that exposes a ``facts_created`` list of dicts
            with keys ``subject``, ``predicate``, ``object_val``, and
            ``source_episode``.
        session:
            An open async DB session.  Used both for the lookup query
            (so the consolidation's pending rows are visible) and for the
            ingestion INSERTs.
        """
        facts_to_ingest: list[SemanticFacts] = await self._lookup_facts_from_consolidation(
            consolidation_result, session
        )
        started = datetime.now(UTC)
        per_fact: list[IngestionResult] = []
        total_entities_created = 0
        total_entities_resolved = 0
        total_edges_created = 0
        total_edges_skipped = 0
        total_errors = 0

        for fact in facts_to_ingest:
            fact_id = _coerce_uuid(getattr(fact, "id", None), context="fact.id")
            try:
                result = await self._ingest_fact_in_session(fact, session)
            except KGIngestionError as exc:
                logger.warning(
                    "kg_ingest_consolidation_skipped",
                    extra={"fact_id": str(fact_id), "error": exc.message},
                )
                result = IngestionResult(
                    fact_id=fact_id,
                    errors=[f"skipped:{exc.message}"],
                )
            except Exception as exc:  # noqa: BLE001 -- per-fact isolation
                logger.exception(
                    "kg_ingest_consolidation_error",
                    extra={"fact_id": str(fact_id), "error": repr(exc)},
                )
                result = IngestionResult(
                    fact_id=fact_id,
                    errors=[f"error:{type(exc).__name__}:{exc}"],
                )
            per_fact.append(result)
            total_entities_created += result.entities_created
            total_entities_resolved += result.entities_resolved
            total_edges_created += result.edges_created
            total_edges_skipped += result.edges_skipped_duplicate
            total_errors += len(result.errors)

        elapsed = (datetime.now(UTC) - started).total_seconds()
        self._metrics.observe_ingestion_duration("consolidation", max(elapsed, 0.0))
        return BatchIngestionResult(
            total_facts=len(facts_to_ingest),
            total_entities_created=total_entities_created,
            total_entities_resolved=total_entities_resolved,
            total_edges_created=total_edges_created,
            total_edges_skipped_duplicate=total_edges_skipped,
            total_errors=total_errors,
            per_fact=per_fact,
        )

    # ------------------------------------------------------------------
    # Internal primitives
    # ------------------------------------------------------------------

    async def _ingest_fact_in_session(
        self,
        fact: SemanticFact,
        session: AsyncSessionProtocol,
    ) -> IngestionResult:
        """Run the full ingestion flow for a single fact.

        Public callers should use :meth:`ingest_fact` or
        :meth:`ingest_batch`; this method assumes the caller owns the
        transaction (no commit).  All collaborators run against the
        supplied *session* — except the resolver, which keeps its own
        read-only session via the resolver's :attr:`session_factory`.
        """
        fact_id = _coerce_uuid(getattr(fact, "id", None), context="fact.id")

        # Step 1: extract entities from the fact's two text slots.
        extracted_entities: list[ExtractedEntity] = self._safe_extract_entities(fact)
        if len(extracted_entities) < 2:
            # Either subject or object is empty / non-extractable — the
            # relation extractor will also return [], so we short-circuit.
            logger.info(
                "kg_ingest_no_entities",
                extra={"fact_id": str(fact_id)},
            )
            return IngestionResult(fact_id=fact_id)

        # Step 2: resolve each entity (existing or new).  This step also
        # INSERTs new rows — kept in the same session as the edge INSERT
        # so the entire fact lands atomically.
        resolved_pairs: list[tuple[ExtractedEntity, uuid.UUID, bool]] = []
        entities_created = 0
        entities_resolved = 0
        for extracted in extracted_entities:
            entity_id, was_created = await self._resolve_or_create_entity(
                extracted=extracted,
                session=session,
            )
            resolved_pairs.append((extracted, entity_id, was_created))
            if was_created:
                entities_created += 1
            else:
                entities_resolved += 1
            self._metrics.record_extraction(
                entity_category=extracted.entity_type.value,
                relation_type="-",
                status="ok" if not was_created else "created",
            )

        # Step 3: extract relations from the typed entity pair.
        extracted_relations: list[ExtractedRelation] = self._safe_extract_relations(fact)
        if not extracted_relations:
            logger.info(
                "kg_ingest_no_relations",
                extra={"fact_id": str(fact_id)},
            )
            return IngestionResult(
                entities_created=entities_created,
                entities_resolved=entities_resolved,
                fact_id=fact_id,
            )

        # Step 4 + 5: mint consent token and write each edge.
        edges_created = 0
        edges_skipped = 0
        for relation in extracted_relations:
            try:
                inserted = await self._write_edge(
                    fact=fact,
                    relation=relation,
                    resolved_pairs=resolved_pairs,
                    session=session,
                )
            except KGIngestionError:
                raise
            except Exception as exc:  # noqa: BLE001 -- per-edge isolation
                logger.exception(
                    "kg_ingest_edge_failed",
                    extra={
                        "fact_id": str(fact_id),
                        "relation_type": relation.relation_type.value,
                        "error": repr(exc),
                    },
                )
                # Per-edge failure is isolated: log + skip, keep going.
                edges_skipped += 1
                continue
            if inserted:
                edges_created += 1
            else:
                edges_skipped += 1
            self._metrics.record_extraction(
                entity_category=relation.subject.entity_type.value,
                relation_type=relation.relation_type.value,
                status="ok" if inserted else "skipped",
            )

        return IngestionResult(
            entities_created=entities_created,
            entities_resolved=entities_resolved,
            edges_created=edges_created,
            edges_skipped_duplicate=edges_skipped,
            fact_id=fact_id,
        )

    def _safe_extract_entities(self, fact: SemanticFact) -> list[ExtractedEntity]:
        """Run the entity extractor, swallowing exceptions to a ``[]`` result.

        The extractor can raise :class:`KGExtractionError` on a malformed
        fact — we want to log and continue, never crash the batch.
        """
        try:
            return list(self._entity_extractor.extract_entities(fact))
        except Exception as exc:  # noqa: BLE001 -- defensive boundary
            fact_id = getattr(fact, "id", None)
            logger.warning(
                "kg_extract_entities_failed",
                extra={"fact_id": str(fact_id), "error": repr(exc)},
            )
            return []

    def _safe_extract_relations(self, fact: SemanticFact) -> list[ExtractedRelation]:
        """Run the relation extractor with the same defensive boundary."""
        try:
            return list(self._relation_extractor.extract_relations(fact))
        except Exception as exc:  # noqa: BLE001 -- defensive boundary
            fact_id = getattr(fact, "id", None)
            logger.warning(
                "kg_extract_relations_failed",
                extra={"fact_id": str(fact_id), "error": repr(exc)},
            )
            return []

    async def _resolve_or_create_entity(
        self,
        *,
        extracted: ExtractedEntity,
        session: AsyncSessionProtocol,
    ) -> tuple[uuid.UUID, bool]:
        """Return ``(entity_id, was_created)`` for one extracted entity.

        The resolver is consulted first (``L1 → L1b → L2``).  If it
        returns a live match, the entity ID is reused and ``was_created``
        is ``False``.  If the resolver returns ``method='none'``, a brand
        new row is upserted into ``kg_entities`` and ``was_created`` is
        ``True``.  The upsert is idempotent — a concurrent insert that
        wins the race is detected via the ``(xmax = 0) AS was_inserted``
        column and we degrade ``was_created`` to ``False``.
        """
        name = extracted.text
        category_value = extracted.entity_type.value

        # Resolver handles its own session internally — read-only, safe.
        resolution = await self._entity_resolver.resolve_entity(name, category_value)
        if resolution.canonical_entity is not None:
            entity_id = _coerce_uuid(
                resolution.canonical_entity.get("id"),
                context=f"resolver.canonical_entity.id for {name!r}",
            )
            self._metrics.record_resolution(resolution.method, "hit")
            return entity_id, False

        # No live match — upsert.  Even if a concurrent worker inserts the
        # same canonical_key first, the ``ON CONFLICT DO UPDATE`` no-op
        # path returns the existing row's id.
        canonical_key = generate_canonical_key(name, category_value)
        new_id = uuid.uuid4()
        params: dict[str, object] = {
            "id": new_id,
            "canonical_key": canonical_key,
            "entity_type": category_value,
            "display_name": name,
            "aliases": [name],
            "first_seen_source": SOURCE_LABEL,
            "classification": self._classification,
        }
        stmt = _sa_text(_ENTITY_UPSERT_SQL)
        bound = _bind_params(stmt, params)
        exec_result = await session.execute(bound)
        row = exec_result.first()
        entity_id = _row_first_uuid(row, field_name="id")
        was_inserted = _row_first_bool(row, field_name="was_inserted")
        if entity_id is None:
            # Defensive: should never happen with DO UPDATE no-op, but a
            # misbehaving driver could still surface this.  Surface a
            # structured error rather than a NoneType later.
            raise KGIngestionError(
                "entity upsert returned no id",
                context={
                    "name": name,
                    "category": category_value,
                    "canonical_key": canonical_key,
                },
            )
        self._metrics.record_resolution("none", "hit" if was_inserted else "miss")
        return entity_id, was_inserted

    async def _write_edge(
        self,
        *,
        fact: SemanticFact,
        relation: ExtractedRelation,
        resolved_pairs: list[tuple[ExtractedEntity, uuid.UUID, bool]],
        session: AsyncSessionProtocol,
    ) -> bool:
        """Insert one edge into ``kg_edges``.

        Returns ``True`` when the edge was newly inserted and ``False``
        when the UNIQUE constraint skipped a duplicate.  Raises
        :class:`KGIngestionError` for structural errors (missing UUIDs).
        """
        src_id = self._lookup_entity_id(relation.subject, resolved_pairs)
        dst_id = self._lookup_entity_id(relation.object_entity, resolved_pairs)
        if src_id is None or dst_id is None:
            raise KGIngestionError(
                "edge insert: unresolved entity id",
                context={
                    "subject_text": relation.subject.text,
                    "object_text": relation.object_entity.text,
                    "src_resolved": src_id is not None,
                    "dst_resolved": dst_id is not None,
                },
            )
        if src_id == dst_id:
            # Self-loop on a single canonical entity — never insert.
            # This can happen when subject and object slots share a
            # mention after resolution (e.g. "Faiz works_at Faiz Corp"
            # where "Faiz" is already known).
            logger.info(
                "kg_ingest_self_loop_skipped",
                extra={
                    "fact_id": str(getattr(fact, "id", None)),
                    "entity_id": str(src_id),
                },
            )
            return False

        fact_id = _coerce_uuid(getattr(fact, "id", None), context="fact.id")
        consent_token = self._consent_manager.generate_consent_token(
            entity_category=relation.subject.entity_type.value,
            scope=self._consent_scope,
        )

        params: dict[str, object] = {
            "id": uuid.uuid4(),
            "src_entity_id": src_id,
            "dst_entity_id": dst_id,
            "relationship_type": relation.relation_type.value,
            "confidence": float(relation.confidence),
            "weight": 1.0,
            "context_sentence": getattr(fact, "safe_content", None) or None,
            "source_fact_id": fact_id,
            "kg_episode_id": None,  # episode reification deferred to M3+; edges link via source_fact_id
            "source_id": f"consolidation:{fact_id}",
            "consent_token": consent_token,
            "consent_scope": self._consent_scope,
            "extractor_model": "rule-based-p16",
            "review_status": "auto_accepted",
            "attributes": "{}",
        }
        stmt = _sa_text(_EDGE_INSERT_SQL)
        bound = _bind_params(stmt, params)
        exec_result = await session.execute(bound)
        row = exec_result.first()
        return row is not None

    @staticmethod
    def _lookup_entity_id(
        extracted: ExtractedEntity,
        resolved_pairs: Iterable[tuple[ExtractedEntity, uuid.UUID, bool]],
    ) -> uuid.UUID | None:
        """Find the resolved UUID for an :class:`ExtractedEntity`.

        Matches by text + entity_type — same surface form + same category
        guarantees the same canonical entity, so a single equality check
        is sufficient and avoids relying on object identity (which would
        break across ``dataclasses.replace`` boundaries).
        """
        target_text = extracted.text
        target_type = extracted.entity_type
        for other, entity_id, _created in resolved_pairs:
            if other.text == target_text and other.entity_type == target_type:
                return entity_id
        return None

    async def _lookup_facts_from_consolidation(
        self,
        consolidation_result: object,
        session: AsyncSessionProtocol,
    ) -> list[SemanticFacts]:
        """Map :class:`ConsolidationResult.facts_created` dicts to ORM rows.

        Consolidation emits a list of dicts (``subject``, ``predicate``,
        ``object_val``, ``source_episode``, ``classification``) without the
        row's UUID or confidence.  This helper re-queries
        ``memory.semantic_facts`` to recover the full row so the ingestion
        INSERTs can set their ``source_fact_id`` FK and respect
        ``fact_type`` / ``confidence`` if the relation extractor ever
        branches on them.
        """
        from guinvere.memory.models import SemanticFacts  # local import — avoid heavy ORM at module top

        facts_created_obj = getattr(consolidation_result, "facts_created", None)
        if not facts_created_obj:
            return []

        # Build a (subject, predicate, object_val, source_episode) index.
        keys: set[tuple[str, str, str, str]] = set()
        for fd in facts_created_obj:
            if not isinstance(fd, dict):
                continue
            subject = str(fd.get("subject", ""))
            predicate = str(fd.get("predicate", ""))
            object_val = str(fd.get("object_val", ""))
            source_episode = str(fd.get("source_episode", ""))
            if subject and predicate and object_val and source_episode:
                keys.add((subject, predicate, object_val, source_episode))
        if not keys:
            return []

        # Query the live (in-session) semantic_facts for matching rows
        # using SQLAlchemy ORM — raw SQL + .scalars() returns scalar values,
        # not ORM instances, so downstream getattr() calls would fail.
        from sqlalchemy import select, and_, or_

        or_clauses = []
        for subject, predicate, object_val, source_episode in keys:
            or_clauses.append(
                and_(
                    SemanticFacts.subject == subject,
                    SemanticFacts.predicate == predicate,
                    SemanticFacts.object_val == object_val,
                    SemanticFacts.source_episode == source_episode,
                )
            )
        stmt = select(SemanticFacts).where(or_(*or_clauses))
        exec_result = await session.execute(stmt)
        rows = list(exec_result.scalars().all())
        # Return in the order the consolidation_result declared them so
        # the per_fact list is stable.
        order_index = {key: idx for idx, key in enumerate(keys)}

        def _row_key(row: object) -> tuple[str, str, str, str]:
            return (
                str(getattr(row, "subject", "")),
                str(getattr(row, "predicate", "")),
                str(getattr(row, "object_val", "")),
                str(getattr(row, "source_episode", "")),
            )

        rows_sorted = sorted(
            rows,
            key=lambda r: order_index.get(_row_key(r), len(order_index)),
        )
        # ``exec_result.scalars().all()`` is typed as ``Sequence[Row]`` at
        # the SQLAlchemy boundary.  We trust the SELECT above to return
        # ``SemanticFacts`` rows, so cast the list at the static-type
        # layer — never a ``# type: ignore``.
        return cast(list[SemanticFacts], rows_sorted)

    # ------------------------------------------------------------------
    # Read-only accessors
    # ------------------------------------------------------------------

    @property
    def session_factory(self) -> Callable[[], AsyncSessionProtocol]:
        """Return the injected session factory (read-only)."""
        return self._session_factory

    @property
    def entity_extractor(self) -> EntityExtractor:
        """Return the injected entity extractor (read-only)."""
        return self._entity_extractor

    @property
    def entity_resolver(self) -> EntityResolver:
        """Return the injected entity resolver (read-only)."""
        return self._entity_resolver

    @property
    def relation_extractor(self) -> RelationExtractor:
        """Return the injected relation extractor (read-only)."""
        return self._relation_extractor

    @property
    def consent_manager(self) -> ConsentManager:
        """Return the injected consent manager (read-only)."""
        return self._consent_manager

    @property
    def metrics(self) -> KGMetrics:
        """Return the injected metrics singleton (read-only)."""
        return self._metrics


# ---------------------------------------------------------------------------
# Public re-exports
# ---------------------------------------------------------------------------

__all__ = [
    "BatchIngestionResult",
    "DEFAULT_CLASSIFICATION",
    "DEFAULT_CONSENT_SCOPE",
    "IngestionResult",
    "KG_EDGES_TABLE",
    "KG_ENTITIES_TABLE",
    "KGIngestionPipeline",
    "SOURCE_LABEL",
    # Re-exported for tests / downstream callers that want the SQL
    # constants without reaching into the module globals.
    "_EDGE_INSERT_SQL",
    "_ENTITY_UPSERT_SQL",
]