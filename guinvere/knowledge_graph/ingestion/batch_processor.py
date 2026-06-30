"""P16-002: Batch processor for unprocessed semantic facts.

Sister module to :mod:`src.knowledge_graph.ingestion.pipeline`.  The
:class:`BatchProcessor` wraps a :class:`KGIngestionPipeline` and adds two
operational primitives the cron job needs:

* :meth:`BatchProcessor.process_unprocessed_facts` — find every
  ``memory.semantic_facts`` row that has **no** corresponding
  ``memory.kg_edges`` row (LEFT JOIN) and ingest it.
* :meth:`BatchProcessor.process_facts_since` — ingest every fact created
  after a given timestamp (used by ad-hoc backfill jobs and operator
  manual triggers).

Both methods support a ``dry_run`` flag that runs the lookup query and
returns a populated :class:`BatchIngestionResult` populated with zeros
for the counters — letting the operator preview the backlog before
committing a real run.

Safety / consent notes (per AGENTS.md BLOCKING rules and
PersonaSafetyPolicy):

* The processor never opens a write transaction in dry-run mode.
* Per-fact failures are isolated (logged + captured in the per-fact
  error list) — one bad row never aborts the batch.
* No type suppression, no empty catches.
* The processor is **read-heavy**: the unprocessed-facts query is the
  only blocking call.  Backpressure is bounded by ``batch_size`` and
  ``limit``.
"""
from __future__ import annotations

import logging
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol

from sqlalchemy import select as _sa_select, text as _sa_text, not_
from sqlalchemy import column as _sa_column, literal_column
from sqlalchemy.orm import aliased

from guinvere.knowledge_graph.errors import KGIngestionError
from guinvere.knowledge_graph.ingestion.pipeline import (
    BatchIngestionResult,
    IngestionResult,
    KGIngestionPipeline,
)
from guinvere.knowledge_graph.resolution.canonical import AsyncSessionProtocol
from guinvere.memory.models import SemanticFacts

logger = logging.getLogger(__name__)


UTC = timezone.utc


# ---------------------------------------------------------------------------
# Protocols
# ---------------------------------------------------------------------------


class _SessionFactory(Protocol):
    """Minimal async session-factory protocol — mirror of the pipeline's."""

    def __call__(self) -> AsyncSessionProtocol:  # pragma: no cover -- structural
        ...


# ---------------------------------------------------------------------------
# SQL statements
# ---------------------------------------------------------------------------

# Facts with no edges — the "backlog" of ingestion candidates.
# Uses LEFT JOIN to detect the absence of an edge for a given fact.
_UNPROCESSED_FACTS_SQL: str = (
    "SELECT sf.id, sf.subject, sf.predicate, sf.object_val, sf.fact_type, "
    "       sf.confidence, sf.source, sf.source_episode, sf.last_verified, "
    "       sf.verified_count, sf.contradicts_ids, sf.is_conflict, "
    "       sf.conflict_resolved, sf.guinevere_note, sf.embedding, sf.tags, "
    "       sf.version, sf.classification, sf.purpose, sf.retention_class, "
    "       sf.retention_until, sf.access_policy, sf.encryption_profile, "
    "       sf.deletion_state, sf.key_id, sf.key_version, "
    "       sf.created_at, sf.updated_at "
    "FROM memory.semantic_facts sf "
    "LEFT JOIN memory.kg_edges e ON e.source_fact_id = sf.id "
    "WHERE e.id IS NULL "
    "  AND (sf.deletion_state IS NULL OR sf.deletion_state != 'deleted') "
    "ORDER BY sf.created_at ASC "
    "LIMIT :lim"
)


# Facts created at-or-after a given timestamp (manual backfill / re-run).
_FACTS_SINCE_SQL: str = (
    "SELECT id, subject, predicate, object_val, fact_type, "
    "       confidence, source, source_episode, last_verified, "
    "       verified_count, contradicts_ids, is_conflict, "
    "       conflict_resolved, guinevere_note, embedding, tags, "
    "       version, classification, purpose, retention_class, "
    "       retention_until, access_policy, encryption_profile, "
    "       deletion_state, key_id, key_version, "
    "       created_at, updated_at "
    "FROM memory.semantic_facts "
    "WHERE created_at >= :since "
    "  AND (deletion_state IS NULL OR deletion_state != 'deleted') "
    "ORDER BY created_at ASC"
)


# Aggregate count for dry-run reporting.
_COUNT_UNPROCESSED_SQL: str = (
    "SELECT COUNT(*) AS n "
    "FROM memory.semantic_facts sf "
    "LEFT JOIN memory.kg_edges e ON e.source_fact_id = sf.id "
    "WHERE e.id IS NULL "
    "  AND (sf.deletion_state IS NULL OR sf.deletion_state != 'deleted')"
)


_COUNT_SINCE_SQL: str = (
    "SELECT COUNT(*) AS n "
    "FROM memory.semantic_facts "
    "WHERE created_at >= :since "
    "  AND (deletion_state IS NULL OR deletion_state != 'deleted')"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bind_params(statement: object, params: dict[str, object]) -> object:
    """Bind named parameters to a SQL string.

    Same idiom as :func:`src.knowledge_graph.ingestion.pipeline._bind_params`
    — kept local to avoid coupling the two modules at the import level.
    """
    bind = getattr(statement, "bindparams", None)
    if callable(bind):
        return bind(**params)
    return statement


def _coerce_uuid(value: object, *, context: str) -> uuid.UUID:
    """Best-effort UUID coercion with structured :class:`KGIngestionError`."""
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


def _extract_int(row: object, attr: str = "n", *, default: int = 0) -> int:
    """Extract an integer from a SQLAlchemy result row, with a safe default."""
    if row is None:
        return default
    mapping = getattr(row, "_mapping", None)
    raw: object
    if mapping is not None:
        try:
            raw = mapping[attr]
        except (KeyError, TypeError, ValueError):
            raw = getattr(row, attr, default)
    else:
        raw = getattr(row, attr, default)
    if isinstance(raw, bool):
        return int(raw)
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        try:
            return int(raw)
        except ValueError:
            return default
    return default


# ---------------------------------------------------------------------------
# BatchProcessor
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BacklogSnapshot:
    """Read-only summary of the ingestion backlog at a point in time.

    Returned by the dry-run previews.  Cheap to compute (single
    ``COUNT(*)``) and useful for ops dashboards.
    """

    candidate_count: int
    oldest_created_at: datetime | None
    query_label: str


class BatchProcessor:
    """Process semantic facts in configurable batches with backpressure.

    The processor is a thin wrapper over :class:`KGIngestionPipeline`
    that adds the two batch-scan primitives the cron job needs.  It
    holds no DB state of its own — every method takes a session and
    returns structured counts.

    Concurrency
    -----------
    The ``max_concurrent`` knob is currently advisory (not used to
    spawn sub-tasks) because the underlying pipeline runs each fact in
    its own transaction and is already I/O-bound on Postgres.  It is
    retained as a parameter so future revisions can switch to
    ``asyncio.gather`` with a ``Semaphore(max_concurrent)`` without
    changing the call sites.

    The processor is safe to share across asyncio tasks as long as the
    underlying pipeline / session factory is safe.
    """

    def __init__(
        self,
        pipeline: KGIngestionPipeline,
        *,
        batch_size: int = 100,
        max_concurrent: int = 5,
    ) -> None:
        if pipeline is None:
            raise ValueError("pipeline is required")
        if batch_size < 1:
            raise ValueError(f"batch_size must be >= 1; got {batch_size}")
        if max_concurrent < 1:
            raise ValueError(f"max_concurrent must be >= 1; got {max_concurrent}")
        self._pipeline: KGIngestionPipeline = pipeline
        self._batch_size: int = batch_size
        self._max_concurrent: int = max_concurrent

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def process_unprocessed_facts(
        self,
        session: AsyncSessionProtocol,
        *,
        limit: int = 10_000,
        dry_run: bool = False,
    ) -> BatchIngestionResult:
        """Find every fact without an edge and ingest it.

        The lookup query is::

            SELECT sf.*
              FROM memory.semantic_facts sf
              LEFT JOIN memory.kg_edges e ON e.source_fact_id = sf.id
             WHERE e.id IS NULL
               AND (sf.deletion_state IS NULL OR sf.deletion_state != 'deleted')
             ORDER BY sf.created_at ASC
             LIMIT :limit

        Parameters
        ----------
        session:
            An open async DB session.  Used for both the lookup query
            and (when ``dry_run=False``) the ingestion flow that
            delegates to the pipeline.
        limit:
            Cap on the number of facts to process in a single call.
            Default ``10_000`` — bounds the longest-running cron pass.
        dry_run:
            When ``True``, run the lookup query, count the backlog,
            and return a zero-filled :class:`BatchIngestionResult`.
            No INSERTs are issued.
        """
        if session is None:
            raise KGIngestionError("process_unprocessed_facts: session is required")
        if limit < 1:
            raise ValueError(f"limit must be >= 1; got {limit}")

        if dry_run:
            count_stmt = _sa_text(_COUNT_UNPROCESSED_SQL)
            bound_count = _bind_params(count_stmt, {})
            exec_result = await session.execute(bound_count)
            row = exec_result.first()
            return BatchIngestionResult(
                total_facts=_extract_int(row),
                per_fact=[],
            )

        started = datetime.now(UTC)
        facts = await self._fetch_unprocessed_facts(session, limit=limit)
        if not facts:
            return BatchIngestionResult(total_facts=0, per_fact=[])

        batch_result = await self._pipeline.ingest_batch(facts, batch_size=self._batch_size)
        elapsed = (datetime.now(UTC) - started).total_seconds()
        logger.info(
            "kg_batch_unprocessed_completed",
            extra={
                "candidate_count": len(facts),
                "ingested_count": batch_result.total_facts,
                "edges_created": batch_result.total_edges_created,
                "errors": batch_result.total_errors,
                "elapsed_seconds": elapsed,
            },
        )
        return batch_result

    async def process_facts_since(
        self,
        session: AsyncSessionProtocol,
        *,
        since: datetime,
        dry_run: bool = False,
    ) -> BatchIngestionResult:
        """Process every fact created at-or-after *since*.

        Used by manual backfill jobs and operator-initiated reruns.

        Parameters
        ----------
        session:
            An open async DB session.
        since:
            Lower bound (inclusive) for ``semantic_facts.created_at``.
            Naive datetimes are interpreted as UTC.
        dry_run:
            When ``True``, run the lookup query, count the backlog,
            and return a zero-filled :class:`BatchIngestionResult`.
        """
        if session is None:
            raise KGIngestionError("process_facts_since: session is required")
        if since is None:
            raise KGIngestionError("process_facts_since: since is required")

        since_utc = _normalise_to_utc(since)

        if dry_run:
            stmt = _sa_text(_COUNT_SINCE_SQL)
            bound = _bind_params(stmt, {"since": since_utc})
            exec_result = await session.execute(bound)
            row = exec_result.first()
            return BatchIngestionResult(
                total_facts=_extract_int(row),
                per_fact=[],
            )

        started = datetime.now(UTC)
        facts = await self._fetch_facts_since(session, since=since_utc)
        if not facts:
            return BatchIngestionResult(total_facts=0, per_fact=[])

        batch_result = await self._pipeline.ingest_batch(facts, batch_size=self._batch_size)
        elapsed = (datetime.now(UTC) - started).total_seconds()
        logger.info(
            "kg_batch_since_completed",
            extra={
                "since": since_utc.isoformat(),
                "candidate_count": len(facts),
                "ingested_count": batch_result.total_facts,
                "edges_created": batch_result.total_edges_created,
                "errors": batch_result.total_errors,
                "elapsed_seconds": elapsed,
            },
        )
        return batch_result

    async def snapshot_backlog(
        self,
        session: AsyncSessionProtocol,
        *,
        since: datetime | None = None,
    ) -> BacklogSnapshot:
        """Read-only preview of the ingestion backlog.

        Parameters
        ----------
        session:
            An open async DB session.
        since:
            When provided, counts facts created at-or-after *since*
            instead of the unprocessed-facts backlog.
        """
        if session is None:
            raise KGIngestionError("snapshot_backlog: session is required")
        if since is None:
            stmt = _sa_text(_COUNT_UNPROCESSED_SQL)
            bound = _bind_params(stmt, {})
            label = "unprocessed"
        else:
            since_utc = _normalise_to_utc(since)
            stmt = _sa_text(_COUNT_SINCE_SQL)
            bound = _bind_params(stmt, {"since": since_utc})
            label = f"since:{since_utc.isoformat()}"
        exec_result = await session.execute(bound)
        row = exec_result.first()
        return BacklogSnapshot(
            candidate_count=_extract_int(row),
            oldest_created_at=None,
            query_label=label,
        )

    # ------------------------------------------------------------------
    # Read-only accessors
    # ------------------------------------------------------------------

    @property
    def pipeline(self) -> KGIngestionPipeline:
        """Return the wrapped pipeline (read-only)."""
        return self._pipeline

    @property
    def batch_size(self) -> int:
        """Return the configured batch size."""
        return self._batch_size

    @property
    def max_concurrent(self) -> int:
        """Return the configured max-concurrent advisory knob."""
        return self._max_concurrent

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _fetch_unprocessed_facts(
        self,
        session: AsyncSessionProtocol,
        *,
        limit: int,
    ) -> Sequence[object]:
        """Fetch up to ``limit`` facts that have no corresponding edge.

        Uses ORM ``select(SemanticFacts)`` with a NOT EXISTS subquery
        against ``kg_edges`` so results are proper ORM model instances
        with attribute access (``fact.id``, ``fact.subject``, etc.).
        """
        not_exists = _sa_text(
            "NOT EXISTS (SELECT 1 FROM memory.kg_edges e "
            "WHERE e.source_fact_id = memory.semantic_facts.id)"
        )
        stmt = (
            _sa_select(SemanticFacts)
            .where(not_exists)
            .where(
                (SemanticFacts.deletion_state == None)  # noqa: E711
                | (SemanticFacts.deletion_state != "deleted")
            )
            .order_by(SemanticFacts.created_at.asc())
            .limit(int(limit))
        )
        exec_result = await session.execute(stmt)
        return list(exec_result.scalars().all())

    async def _fetch_facts_since(
        self,
        session: AsyncSessionProtocol,
        *,
        since: datetime,
    ) -> Sequence[object]:
        """Fetch every fact whose ``created_at`` is at-or-after *since*.

        Returns ORM model instances in chronological order.
        """
        stmt = (
            _sa_select(SemanticFacts)
            .where(SemanticFacts.created_at >= since)
            .where(
                (SemanticFacts.deletion_state == None)  # noqa: E711
                | (SemanticFacts.deletion_state != "deleted")
            )
            .order_by(SemanticFacts.created_at.asc())
        )
        exec_result = await session.execute(stmt)
        return list(exec_result.scalars().all())


def _normalise_to_utc(value: datetime) -> datetime:
    """Coerce a ``datetime`` into a timezone-aware UTC ``datetime``.

    Naive inputs are tagged with UTC; aware inputs are converted to UTC.
    Used by every entry-point that accepts a ``since`` argument so the
    SQL bind parameter is always tz-aware (Postgres TIMESTAMPTZ rejects
    naive datetimes with a warning).
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


# ---------------------------------------------------------------------------
# Public re-exports
# ---------------------------------------------------------------------------

__all__ = [
    "BatchProcessor",
    "BacklogSnapshot",
]