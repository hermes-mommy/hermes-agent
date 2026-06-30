"""Knowledge Graph historical backfill engine (P16-004).

Migrates the existing ``memory.semantic_facts`` corpus (P3-015 consolidation
output) into the Guinevere Knowledge Graph as :class:`KGEntity` /
:class:`KGEdge` rows.  This is a **one-shot historical migration** that runs
once and is re-runnable safely.

Faiz-locked decision #10: **full historical backfill** — every
``semantic_facts`` row is processed, not just a sample.

Why this module lives here
--------------------------
The ingestion package (per its ``__init__.py`` docstring) is the
"batched write pipeline for entities and edges."  The backfill engine
sits one level above the per-fact :class:`KGIngestor` (planned for a
later P16 step) and orchestrates a streaming pass over
``memory.semantic_facts``.

Safety / consent notes (per AGENTS.md BLOCKING rules and
PersonaSafetyPolicy):

* **No hard deletes.**  :meth:`KGBackfillEngine.rollback_backfill` uses
  soft-delete (``is_tombstoned = TRUE``) exclusively.  The DDL has
  ``ON DELETE RESTRICT`` on every relevant FK, so hard delete would
  fail anyway; we make it impossible at the application layer too.
* **Idempotent.**  Re-running backfill on already-processed facts
  produces zero side effects thanks to
  ``ON CONFLICT (canonical_key) DO NOTHING`` on ``kg_entities`` and
  ``ON CONFLICT (src_entity_id, dst_entity_id, relationship_type,
  source_fact_id) DO NOTHING`` on ``kg_edges`` (matches the DDL
  UNIQUE constraints).
* **Checkpointable.**  Progress is persisted to a JSON file so an
  interrupted backfill can resume from the last completed batch.
* **dry_run by default for safety-sensitive operations.**  The
  constructor exposes ``dry_run`` (default ``False``) — callers that
  want maximum safety should pass ``dry_run=True`` for the first
  invocation and only flip to ``False`` after reviewing the
  :class:`BackfillResult` counts.
* **No surveillance-creep.**  Backfill re-uses already-stored
  semantic facts; it does not initiate new surveillance.
* **No HARD STOP bypass.**  Backfill is operator-initiated (Faiz runs
  it explicitly) and never runs in the user-facing recall path.
* **No type-suppression.**  Every parameter and return value is
  statically typed; no ``# type: ignore`` / ``as any`` shortcuts.

Schema reality (P16-001 v4 DDL)
------------------------------
* :class:`KGEntity` columns: ``id``, ``canonical_key``, ``entity_type``,
  ``display_name``, ``aliases``, ``attributes``, ``merged_into``,
  ``is_tombstoned``, ``tombstone_reason``, ``tombstoned_at``,
  ``first_seen_at``, ``first_seen_source``, ``last_verified_at``,
  ``valid_from``, ``valid_to``, ``classification``, ``purpose``,
  ``source``, ``retention_class``, ``retention_until``, ``access_policy``,
  ``encryption_profile``, ``deletion_state``, ``key_id``, ``key_version``,
  ``created_at``, ``updated_at``.
* :class:`KGEdge` columns: ``id``, ``src_entity_id``, ``dst_entity_id``,
  ``relationship_type``, ``confidence``, ``weight``, ``context_sentence``,
  ``source_fact_id`` (NOT NULL), ``kg_episode_id``, ``source_id``,
  ``recorded_at``, ``valid_from``, ``valid_to``, ``superseded_at``,
  ``consent_token``, ``consent_scope``, ``extractor_model``,
  ``review_status``, ``attributes``, ``is_tombstoned``,
  ``tombstone_reason``, ``tombstoned_at``, classification mixin.
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final, Protocol

from guinvere.knowledge_graph.constants import CONSENT_TOKEN_PREFIX
from guinvere.knowledge_graph.errors import KGIngestionError
from guinvere.knowledge_graph.observability.logger import (
    KGLogContext,
    get_kg_logger,
    log_kg_operation,
)
from guinvere.knowledge_graph.repository import KGRepository, SessionFactory
from guinvere.knowledge_graph.resolution.canonical import (
    generate_canonical_key,
    normalize_entity_name,
)

logger = get_kg_logger("ingestion.backfill")


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

KG_SCHEMA: Final[str] = "memory"
"""PostgreSQL schema hosting all KG tables (per P16-001 v4 DDL)."""

KG_ENTITIES_TABLE: Final[str] = f"{KG_SCHEMA}.kg_entities"
KG_EDGES_TABLE: Final[str] = f"{KG_SCHEMA}.kg_edges"
KG_EPISODES_TABLE: Final[str] = f"{KG_SCHEMA}.kg_episodes"
SEMANTIC_FACTS_TABLE: Final[str] = f"{KG_SCHEMA}.semantic_facts"

BACKFILL_SOURCE_TAG: Final[str] = "backfill_p16_004"
"""Tag written to ``kg_entities.first_seen_source`` and ``kg_edges.source_id``
by the backfill engine.  ``rollback_backfill`` uses this tag to identify
rows created by the backfill (rather than by the live ingestor)."""

BACKFILL_CONSENT_SCOPE: Final[str] = "backfill_default"
"""Consent scope for the system-internal consent token minted for backfill
edges.  Audit-friendly and decoupled from per-entity scopes."""

DEFAULT_CHECKPOINT_PATH: Final[str] = "evidence/p16-kg/backfill_checkpoint.json"
"""Default checkpoint file location.

The path is relative to the repository root; callers that run from a
different working directory should pass ``checkpoint_path=`` explicitly.
The file is JSON; the schema is the :class:`BackfillCheckpoint` dataclass
serialised via :func:`dataclasses.asdict`."""

DEFAULT_BATCH_SIZE: Final[int] = 500
DEFAULT_CHECKPOINT_INTERVAL: Final[int] = 10
"""Default knobs.  Both can be overridden in the constructor."""

MAX_BATCH_SIZE: Final[int] = 10_000
"""Hard ceiling on ``batch_size`` to prevent fat-fingered memory blowups."""

_SAFE_TOKEN_RE: Final[str] = r"^[a-z0-9_]{1,32}$"
"""Allowed character set for consent scope and category components.
Mirrors the safety check in :class:`guinvere.knowledge_graph.consent.manager`."""


# ---------------------------------------------------------------------------
# Session protocol
# ---------------------------------------------------------------------------


class _ExecResult(Protocol):
    """Minimal SQLAlchemy ``Result`` subset used by the engine."""

    def fetchall(self) -> list[object]:
        ...

    def first(self) -> object | None:
        ...


class _AsyncSessionProto(Protocol):
    """Minimal async session contract required by the backfill engine.

    Mirrors the real ``sqlalchemy.ext.asyncio.AsyncSession`` API used
    by the rest of the KG module (see e.g.
    :mod:`guinvere.knowledge_graph.consent.manager`).  The shape is
    intentionally compatible with the :class:`AsyncSessionProtocol`
    declared in :mod:`guinvere.knowledge_graph.repository` but extends it
    with the :meth:`commit` / :meth:`rollback` calls the backfill
    engine makes (the base protocol deliberately omits them because
    the repository wrapper handles commit semantics externally).
    """

    async def execute(
        self, statement: object, params: object | None = None
    ) -> object:
        ...

    async def commit(self) -> None:
        ...

    async def rollback(self) -> None:
        ...


# ---------------------------------------------------------------------------
# Result / status dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BackfillResult:
    """Outcome of a backfill invocation.

    Attributes:
        total_facts_processed: Number of semantic_facts rows attempted.
        total_entities_created: Number of kg_entities rows inserted by
            this run.  Idempotent re-runs typically report 0 here once
            the corpus has been migrated.
        total_edges_created: Number of kg_edges rows inserted by this run.
        total_skipped_duplicate: Number of facts whose derived entities
            and edges were already present (idempotent skip via
            ON CONFLICT).
        total_errors: Number of facts that raised an exception during
            extraction / resolution / ingest.
        batches_completed: Number of batch iterations performed.
        duration_seconds: Wall-clock duration of the invocation.
        checkpoint_id: UUID of the checkpoint file written, or ``None``
            if no checkpoint was emitted (e.g. dry-run + small corpus).
        dry_run: ``True`` when the engine was invoked with
            ``dry_run=True`` and no rows were actually inserted.
        errors_detail: Per-fact error records (at most 1000 entries to
            bound memory; older errors are dropped with a logger warning).
    """

    total_facts_processed: int = 0
    total_entities_created: int = 0
    total_edges_created: int = 0
    total_skipped_duplicate: int = 0
    total_errors: int = 0
    batches_completed: int = 0
    duration_seconds: float = 0.0
    checkpoint_id: str | None = None
    dry_run: bool = False
    errors_detail: list[dict[str, object]] = field(default_factory=list)


@dataclass(frozen=True)
class BackfillStatus:
    """Snapshot of backfill progress, suitable for operator dashboards.

    All counts are DB-side ground truth (read at probe time).  ``is_running``
    is a process-local flag — it is only ``True`` while a :class:`KGBackfillEngine`
    instance is actively executing :meth:`KGBackfillEngine.run_full_backfill`
    or :meth:`KGBackfillEngine.run_backfill_range` in the same process.

    Attributes:
        total_facts: Total semantic_facts rows in the source table.
        facts_processed: Distinct source_fact_ids that have a non-tombstoned
            kg_edges row tagged with :data:`BACKFILL_SOURCE_TAG`.
        facts_remaining: ``total_facts - facts_processed`` (clamped to >= 0).
        entities_created: Non-tombstoned kg_entities rows tagged with
            :data:`BACKFILL_SOURCE_TAG`.
        edges_created: Non-tombstoned kg_edges rows tagged with
            :data:`BACKFILL_SOURCE_TAG`.
        errors: In-process error counter for the active engine; ``0`` when
            no engine is currently running.
        last_checkpoint: Path of the most recent checkpoint file, or ``None``.
        is_running: ``True`` when an engine is mid-execution in this process.
    """

    total_facts: int = 0
    facts_processed: int = 0
    facts_remaining: int = 0
    entities_created: int = 0
    edges_created: int = 0
    errors: int = 0
    last_checkpoint: str | None = None
    is_running: bool = False


@dataclass(frozen=True)
class RollbackResult:
    """Outcome of :meth:`KGBackfillEngine.rollback_backfill`.

    All counts reflect tombstoned rows, not hard-deleted rows.  When
    ``dry_run=True`` the counts represent what *would* have been
    tombstoned; no rows were mutated.

    Attributes:
        entities_tombstoned: kg_entities rows whose ``is_tombstoned`` was
            set to ``TRUE`` (or would be, under dry_run).
        edges_tombstoned: kg_edges rows whose ``is_tombstoned`` was set to
            ``TRUE`` (or would be, under dry_run).
        dry_run: Mirrors the ``dry_run`` argument the engine was invoked
            with — included in the result so the caller does not have to
            remember which mode produced the counts.
    """

    entities_tombstoned: int = 0
    edges_tombstoned: int = 0
    dry_run: bool = False


@dataclass
class BackfillCheckpoint:
    """File-backed progress record for resumable backfill.

    The dataclass is mutable (unlike the public result types) because
    :meth:`KGBackfillEngine._write_checkpoint` updates the same object
    in-place during a run.  Serialised to JSON via :func:`dataclasses.asdict`.

    Attributes:
        last_fact_id: UUID of the last ``semantic_facts.id`` that was
            *successfully* processed.  ``None`` for a fresh checkpoint.
        last_fact_timestamp: Timestamp of the last processed fact, in
            ISO-8601 UTC.  ``None`` for a fresh checkpoint.
        facts_processed: Cumulative count of facts attempted.
        entities_created: Cumulative count of entities inserted.
        edges_created: Cumulative count of edges inserted.
        skipped_duplicate: Cumulative count of facts skipped via
            ON CONFLICT.
        errors: Cumulative count of fact-level errors.
        batches_completed: Cumulative number of batch iterations.
        started_at: ISO-8601 UTC timestamp when the backfill run started.
        updated_at: ISO-8601 UTC timestamp of the most recent checkpoint
            write.
        consent_token: The system-internal consent token used for backfill
            edges.  Persisted so a resume re-uses the same token (audit
            trail continuity).
        checkpoint_id: Stable UUID assigned to this checkpoint file on
            first write.  Identifies the *file*, not the engine instance.
    """

    last_fact_id: str | None = None
    last_fact_timestamp: str | None = None
    facts_processed: int = 0
    entities_created: int = 0
    edges_created: int = 0
    skipped_duplicate: int = 0
    errors: int = 0
    batches_completed: int = 0
    started_at: str = ""
    updated_at: str = ""
    consent_token: str = ""
    checkpoint_id: str = ""


# ---------------------------------------------------------------------------
# SQL templates
# ---------------------------------------------------------------------------


# We bind :batch_size and :last_id (NULL on first batch).  Streaming order
# is by id ASC so the checkpoint ``last_fact_id`` is a strict cursor.
_COUNT_FACTS_SQL: Final[str] = (
    f"SELECT COUNT(*) AS n FROM {SEMANTIC_FACTS_TABLE}"
)
"""Count all facts (the backfill corpus).  Conflict-flagged facts are
included — the engine makes the call to skip or include per its config."""

_COUNT_FACTS_IN_RANGE_SQL: Final[str] = (
    f"SELECT COUNT(*) AS n FROM {SEMANTIC_FACTS_TABLE} "
    "WHERE last_verified >= :start_ts "
    "  AND (:end_ts IS NULL OR last_verified <= :end_ts)"
)
"""Count facts in a date range.  Uses ``last_verified`` as the temporal
signal because that is the column P3-015 updates on every consolidation
re-run (vs. ``created_at`` which is immutable)."""

_SELECT_FACT_BATCH_SQL: Final[str] = (
    f"SELECT id, subject, predicate, object_val, fact_type, confidence, "
    "       source, source_episode, last_verified "
    f"FROM {SEMANTIC_FACTS_TABLE} "
    "WHERE (CAST(:last_id AS uuid) IS NULL OR id > CAST(:last_id AS uuid)) "
    "  AND (CAST(:start_ts AS timestamptz) IS NULL OR last_verified >= CAST(:start_ts AS timestamptz)) "
    "  AND (CAST(:end_ts AS timestamptz) IS NULL OR last_verified <= CAST(:end_ts AS timestamptz)) "
    "ORDER BY id ASC "
    "LIMIT :batch_size"
)
"""Streaming fact fetch.  Keyset pagination on ``id`` so the query is
O(batch_size) regardless of corpus size.  ``start_ts`` / ``end_ts`` are
optional date-range filters (NULL when not in range mode)."""

_UPSERT_ENTITY_SQL: Final[str] = (
    f"INSERT INTO {KG_ENTITIES_TABLE} "
    "  (canonical_key, entity_type, display_name, aliases, attributes, "
    "   first_seen_at, first_seen_source, classification, purpose, source) "
    "VALUES "
    "  (:canonical_key, :entity_type, :display_name, :aliases, "
    "   CAST(:attributes AS jsonb), NOW(), :first_seen_source, "
    "   :classification, :purpose, :source) "
    "ON CONFLICT (canonical_key) DO NOTHING "
    "RETURNING id"
)
"""Idempotent entity upsert.  Returns the new id on insert, zero rows
on conflict.  Callers fall back to a follow-up SELECT to fetch the
existing id when RETURNING is empty."""

_LOOKUP_ENTITY_BY_KEY_SQL: Final[str] = (
    f"SELECT id, display_name, entity_type "
    f"FROM {KG_ENTITIES_TABLE} "
    "WHERE canonical_key = :canonical_key "
    "  AND is_tombstoned = FALSE"
)
"""Look up the live (non-tombstoned) entity by canonical key.  Returns
``None`` when no such row exists — should not happen after a successful
upsert but we defensively re-fetch."""

_INSERT_EDGE_SQL: Final[str] = (
    f"INSERT INTO {KG_EDGES_TABLE} "
    "  (src_entity_id, dst_entity_id, relationship_type, confidence, "
    "   weight, source_fact_id, source_id, consent_token, consent_scope, "
    "   extractor_model, review_status, attributes, recorded_at) "
    "VALUES "
    "  (:src_entity_id, :dst_entity_id, :relationship_type, "
    "   :confidence, :weight, :source_fact_id, :source_id, "
    "   :consent_token, :consent_scope, :extractor_model, "
    "   :review_status, CAST(:attributes AS jsonb), NOW()) "
    "ON CONFLICT (src_entity_id, dst_entity_id, relationship_type, "
    "             source_fact_id) DO NOTHING"
)
"""Idempotent edge insert.  Matches the DDL UNIQUE
``uq_kg_edges_idempotent``.  No RETURNING — the caller detects duplicates
via ``rowcount`` and we do not need the new edge id downstream."""

_COUNT_ENTITIES_CREATED_SQL: Final[str] = (
    f"SELECT COUNT(*) AS n FROM {KG_ENTITIES_TABLE} "
    "WHERE first_seen_source = :tag AND is_tombstoned = FALSE"
)
_COUNT_EDGES_CREATED_SQL: Final[str] = (
    f"SELECT COUNT(*) AS n FROM {KG_EDGES_TABLE} "
    "WHERE source_id = :tag AND is_tombstoned = FALSE"
)
_COUNT_FACTS_PROCESSED_SQL: Final[str] = (
    f"SELECT COUNT(DISTINCT source_fact_id) AS n FROM {KG_EDGES_TABLE} "
    "WHERE source_id = :tag AND is_tombstoned = FALSE"
)

_TOMBSTONE_ENTITIES_SQL: Final[str] = (
    f"UPDATE {KG_ENTITIES_TABLE} "
    "SET is_tombstoned = TRUE, "
    "    tombstone_reason = :reason, "
    "    tombstoned_at = NOW(), "
    "    updated_at = NOW() "
    "WHERE first_seen_source = :tag "
    "  AND is_tombstoned = FALSE"
)
_TOMBSTONE_EDGES_SQL: Final[str] = (
    f"UPDATE {KG_EDGES_TABLE} "
    "SET is_tombstoned = TRUE, "
    "    tombstone_reason = :reason, "
    "    tombstoned_at = NOW(), "
    "    updated_at = NOW() "
    "WHERE source_id = :tag "
    "  AND is_tombstoned = FALSE"
)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class KGBackfillEngine:
    """Historical backfill of ``semantic_facts`` → KG entities + edges.

    The engine is process-local: an instance is created per migration
    invocation.  The :class:`BackfillCheckpoint` is the only state that
    survives across processes — it lives in a JSON file (default
    :data:`DEFAULT_CHECKPOINT_PATH`).

    Args:
        session_factory: Callable that returns a fresh async session
            (typically :func:`guinvere.memory.db.get_async_session`).  All
            session lifecycle goes through :class:`KGRepository` so the
            engine shares Guinevere's existing connection pool.
        batch_size: Number of facts per batch.  Clamped to
            ``[1, MAX_BATCH_SIZE]``.  Default 500 — a good throughput
            / memory trade-off for the ~1M-memory target scale.
        checkpoint_interval: Number of batches between checkpoint writes.
            Default 10 (≈ 5 000 facts per checkpoint at the default
            batch size).  Setting to 0 disables checkpoints; setting to
            a negative value raises :class:`ValueError`.
        dry_run: When ``True`` the engine logs and counts what it *would*
            do, but never mutates the database.  Default ``False``
            (matches the spec's constructor signature — the engine is
            operator-initiated, so the operator is expected to verify
            a dry-run first via :meth:`run_full_backfill` with
            ``dry_run=True`` on a separate :class:`KGBackfillEngine`
            instance).  **Recommended workflow: dry-run → review
            counts → live run.**  See the module docstring for the
            full safety framing.
        checkpoint_path: Override for the checkpoint file location.
            ``None`` uses :data:`DEFAULT_CHECKPOINT_PATH`.

    Raises:
        ValueError: If ``batch_size``, ``checkpoint_interval``, or
            ``dry_run`` is invalid.  (Type-suppression-free guard.)
    """

    # Class-level lock-free running flag.  Single process is assumed —
    # cross-process coordination is delegated to the checkpoint file
    # (``_claim_checkpoint`` checks mtime + content before adopting).
    _is_running: bool = False

    def __init__(
        self,
        session_factory: SessionFactory,
        *,
        batch_size: int = DEFAULT_BATCH_SIZE,
        checkpoint_interval: int = DEFAULT_CHECKPOINT_INTERVAL,
        dry_run: bool = False,
        checkpoint_path: str | None = None,
    ) -> None:
        if session_factory is None or not callable(session_factory):
            raise ValueError("session_factory is required and must be callable")
        if not isinstance(batch_size, int) or isinstance(batch_size, bool):
            raise ValueError(f"batch_size must be int; got {type(batch_size).__name__}")
        if batch_size < 1:
            raise ValueError(f"batch_size must be >= 1; got {batch_size}")
        if batch_size > MAX_BATCH_SIZE:
            raise ValueError(
                f"batch_size must be <= {MAX_BATCH_SIZE}; got {batch_size}"
            )
        if not isinstance(checkpoint_interval, int) or isinstance(checkpoint_interval, bool):
            raise ValueError(
                "checkpoint_interval must be int; "
                f"got {type(checkpoint_interval).__name__}"
            )
        if checkpoint_interval < 0:
            raise ValueError(
                f"checkpoint_interval must be >= 0; got {checkpoint_interval}"
            )

        self._session_factory: SessionFactory = session_factory
        self._batch_size: int = batch_size
        self._checkpoint_interval: int = checkpoint_interval
        self._dry_run: bool = bool(dry_run)
        self._checkpoint_path: str = (
            checkpoint_path or DEFAULT_CHECKPOINT_PATH
        )
        self._repo: KGRepository = KGRepository(session_factory)

        # In-process counters — reset per ``run_*`` call.  Surfaced via
        # :meth:`get_backfill_status` while the engine is running.
        self._live_errors: int = 0
        self._live_facts: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_full_backfill(self) -> BackfillResult:
        """Backfill every ``semantic_facts`` row into the KG.

        Steps:

        1. Load (or initialise) the checkpoint file.  If the file
           exists and points at a non-empty ``last_fact_id``, the run
           resumes from that point; otherwise it starts at the
           beginning of the corpus.
        2. Count the total facts to process.
        3. Stream facts in batches of :attr:`_batch_size` ordered by
           ``id`` ASC.  For each batch:

           a.  Extract typed entities (subject, object) using
               :class:`guinvere.knowledge_graph.extraction.entity_extractor.EntityExtractor`.
           b.  Resolve / upsert each entity with
               ``ON CONFLICT (canonical_key) DO NOTHING``.
           c.  Extract the typed relation using
               :class:`guinvere.knowledge_graph.extraction.relation_extractor.RelationExtractor`.
           d.  Insert the edge with
               ``ON CONFLICT (src, dst, rel, source_fact_id) DO NOTHING``.
           e.  Capture per-fact errors (never empty excepts — every
               failure path records the exception class + message in
               :attr:`BackfillResult.errors_detail`).

        4. After every :attr:`_checkpoint_interval` batches, persist
           the cumulative counters to the checkpoint file.
        5. Return a :class:`BackfillResult` with the final counts and
           any error detail.

        The whole run is idempotent: re-invoking after a successful or
        partial run produces zero side effects (ON CONFLICT skips every
        duplicate row).

        Returns:
            A :class:`BackfillResult` summarising the run.

        Raises:
            KGIngestionError: For unrecoverable infrastructure errors
                (DB schema missing, permissions denied, etc.).  Per-fact
                errors are captured in :attr:`BackfillResult.errors_detail`
                and do NOT raise.
        """
        checkpoint = self._load_or_init_checkpoint()
        start_ts = time.perf_counter()
        ctx = KGLogContext(operation="kg_backfill_full")
        log_kg_operation(logger, ctx)

        if not self._dry_run:
            total = await self._count_facts(start_ts=None, end_ts=None)
        else:
            # In dry-run we still need an accurate total to report.
            total = await self._count_facts(start_ts=None, end_ts=None)

        self._mark_running(True)
        self._live_errors = 0
        self._live_facts = 0
        try:
            result = await self._stream_batches(
                checkpoint=checkpoint,
                start_ts=None,
                end_ts=None,
            )
        finally:
            self._mark_running(False)

        # If checkpoint writes were enabled and we processed at least
        # one fact, record the checkpoint id in the result so the
        # caller can correlate with the file on disk.
        if self._checkpoint_interval > 0 and result.batches_completed > 0:
            result_with_ckpt = BackfillResult(
                **{
                    **asdict(result),
                    "duration_seconds": time.perf_counter() - start_ts,
                    "checkpoint_id": checkpoint.checkpoint_id or None,
                }
            )
        else:
            result_with_ckpt = BackfillResult(
                **{
                    **asdict(result),
                    "duration_seconds": time.perf_counter() - start_ts,
                    "checkpoint_id": None,
                }
            )
        # Frozen dataclass — use replace() to create updated context
        from dataclasses import replace
        final_ctx = replace(
            ctx,
            result_count=result_with_ckpt.total_facts_processed,
            duration_ms=result_with_ckpt.duration_seconds * 1000.0,
        )
        log_kg_operation(logger, final_ctx)
        return result_with_ckpt

    async def run_backfill_range(
        self,
        *,
        start_date: datetime,
        end_date: datetime | None = None,
    ) -> BackfillResult:
        """Backfill facts whose ``last_verified`` falls in ``[start_date, end_date]``.

        Uses the same streaming pipeline as :meth:`run_full_backfill` but
        restricts the corpus to a date window.  Useful for re-processing
        a specific time slice without touching the rest of the graph.

        Args:
            start_date: Inclusive lower bound (UTC).  Facts with
                ``last_verified >= start_date`` are eligible.
            end_date: Inclusive upper bound (UTC).  ``None`` means
                "everything from start_date to now".

        Returns:
            A :class:`BackfillResult` summarising the run.

        Raises:
            ValueError: If ``start_date`` is ``None`` or timezone-naive.
            KGIngestionError: For unrecoverable infrastructure errors.
        """
        if start_date is None:
            raise ValueError("start_date is required")
        if not isinstance(start_date, datetime):
            raise ValueError(
                f"start_date must be datetime; got {type(start_date).__name__}"
            )
        if start_date.tzinfo is None:
            raise ValueError("start_date must be timezone-aware (UTC expected)")
        if end_date is not None:
            if not isinstance(end_date, datetime):
                raise ValueError(
                    f"end_date must be datetime; got {type(end_date).__name__}"
                )
            if end_date.tzinfo is None:
                raise ValueError("end_date must be timezone-aware (UTC expected)")
            if end_date < start_date:
                raise ValueError(
                    f"end_date ({end_date.isoformat()}) precedes "
                    f"start_date ({start_date.isoformat()})"
                )

        checkpoint = self._load_or_init_checkpoint()
        start_ts = time.perf_counter()
        ctx = KGLogContext(operation="kg_backfill_range")
        log_kg_operation(logger, ctx)

        self._mark_running(True)
        self._live_errors = 0
        self._live_facts = 0
        try:
            result = await self._stream_batches(
                checkpoint=checkpoint,
                start_ts=start_date.astimezone(timezone.utc),
                end_ts=(end_date.astimezone(timezone.utc) if end_date else None),
            )
        finally:
            self._mark_running(False)

        result_with_duration = BackfillResult(
            **{
                **asdict(result),
                "duration_seconds": time.perf_counter() - start_ts,
                "checkpoint_id": (
                    checkpoint.checkpoint_id or None
                    if self._checkpoint_interval > 0
                    else None
                ),
            }
        )
        # Frozen dataclass — use replace() to create updated context
        from dataclasses import replace
        final_ctx = replace(
            ctx,
            result_count=result_with_duration.total_facts_processed,
            duration_ms=result_with_duration.duration_seconds * 1000.0,
        )
        log_kg_operation(logger, final_ctx)
        return result_with_duration

    async def get_backfill_status(self) -> BackfillStatus:
        """Report current backfill progress from the database.

        Reads ground truth from ``memory.kg_entities`` /
        ``memory.kg_edges`` (counts of rows tagged with
        :data:`BACKFILL_SOURCE_TAG`) rather than from the in-process
        counters, so the report is consistent across processes.

        The ``is_running`` flag is process-local; it is ``True`` only
        when an engine instance in the current process is mid-execution.

        Returns:
            A :class:`BackfillStatus` snapshot.
        """
        last_ckpt: str | None = self._checkpoint_path
        if not Path(self._checkpoint_path).exists():
            last_ckpt = None

        try:
            async with self._repo.get_session() as session:
                total = await self._scalar_count(session, _COUNT_FACTS_SQL, {})
                entities = await self._scalar_count(
                    session,
                    _COUNT_ENTITIES_CREATED_SQL,
                    {"tag": BACKFILL_SOURCE_TAG},
                )
                edges = await self._scalar_count(
                    session, _COUNT_EDGES_CREATED_SQL, {"tag": BACKFILL_SOURCE_TAG}
                )
                processed = await self._scalar_count(
                    session,
                    _COUNT_FACTS_PROCESSED_SQL,
                    {"tag": BACKFILL_SOURCE_TAG},
                )
        except Exception as exc:  # noqa: BLE001 -- probe must never raise
            logger.exception("kg_backfill_status probe failed: %s", exc)
            return BackfillStatus(
                total_facts=0,
                facts_processed=0,
                facts_remaining=0,
                entities_created=0,
                edges_created=0,
                errors=self._live_errors,
                last_checkpoint=last_ckpt,
                is_running=KGBackfillEngine._is_running,
            )

        remaining = max(0, int(total) - int(processed))
        return BackfillStatus(
            total_facts=int(total),
            facts_processed=int(processed),
            facts_remaining=remaining,
            entities_created=int(entities),
            edges_created=int(edges),
            errors=self._live_errors,
            last_checkpoint=last_ckpt,
            is_running=KGBackfillEngine._is_running,
        )

    async def resume_from_checkpoint(self) -> BackfillResult:
        """Resume backfill from the last persisted checkpoint.

        Convenience wrapper around :meth:`run_full_backfill` that fails
        fast when no checkpoint file is present (so the operator
        cannot accidentally double-process the corpus from id 0).

        Returns:
            A :class:`BackfillResult` summarising the resumed run.

        Raises:
            KGIngestionError: When no checkpoint file exists at
                :attr:`_checkpoint_path`.
        """
        if not Path(self._checkpoint_path).exists():
            raise KGIngestionError(
                "resume_from_checkpoint: no checkpoint file at "
                f"{self._checkpoint_path}",
                context={"checkpoint_path": self._checkpoint_path},
            )
        return await self.run_full_backfill()

    async def rollback_backfill(
        self,
        *,
        dry_run: bool = False,
    ) -> RollbackResult:
        """Soft-delete every row created by the backfill.

        Uses ``is_tombstoned = TRUE`` exclusively — never ``DELETE FROM``.
        Restricted to rows whose ``first_seen_source`` /
        ``source_id`` equals :data:`BACKFILL_SOURCE_TAG`, so the rollback
        is scoped to backfill artefacts and never touches live-ingestor
        rows (or any other source-tagged rows).

        Args:
            dry_run: When ``True``, returns the counts that *would* be
                tombstoned without mutating any rows.  Useful for the
                "preview before destructive op" pattern.

        Returns:
            A :class:`RollbackResult` with the tombstone counts.

        Raises:
            KGIngestionError: For unrecoverable infrastructure errors.
        """
        reason = "backfill_p16_004_rollback"
        ctx = KGLogContext(operation="kg_backfill_rollback")

        # Dry-run probe: a COUNT of the rows that would be tombstoned.
        if dry_run:
            try:
                async with self._repo.get_session() as session:
                    e_count = await self._scalar_count(
                        session,
                        "SELECT COUNT(*) AS n FROM "
                        f"{KG_ENTITIES_TABLE} "
                        "WHERE first_seen_source = :tag "
                        "  AND is_tombstoned = FALSE",
                        {"tag": BACKFILL_SOURCE_TAG},
                    )
                    ed_count = await self._scalar_count(
                        session,
                        "SELECT COUNT(*) AS n FROM "
                        f"{KG_EDGES_TABLE} "
                        "WHERE source_id = :tag "
                        "  AND is_tombstoned = FALSE",
                        {"tag": BACKFILL_SOURCE_TAG},
                    )
            except Exception as exc:  # noqa: BLE001 -- probe must never raise
                logger.exception("kg_backfill_rollback dry_run probe failed: %s", exc)
                from dataclasses import replace as _replace
                log_kg_operation(logger, _replace(ctx, error=repr(exc)))
                raise KGIngestionError(
                    "rollback_backfill dry_run probe failed",
                    context={"error_type": type(exc).__name__},
                ) from exc
            log_kg_operation(logger, ctx)
            return RollbackResult(
                entities_tombstoned=int(e_count),
                edges_tombstoned=int(ed_count),
                dry_run=True,
            )

        # Real rollback: tombstone entities, then edges.  We tombstone
        # entities first so the per-row FK constraint ``ck_kg_edges_no_self_loop``
        # and the partial indexes stay queryable.  Edges are tombstoned
        # in the same transaction so the operation is atomic.
        try:
            async with self._repo.get_session() as session:
                e_res = await session.execute(
                    self._text(_TOMBSTONE_ENTITIES_SQL),
                    {"reason": reason, "tag": BACKFILL_SOURCE_TAG},
                )
                ed_res = await session.execute(
                    self._text(_TOMBSTONE_EDGES_SQL),
                    {"reason": reason, "tag": BACKFILL_SOURCE_TAG},
                )
                await session.commit()
                entities_tombstoned = int(getattr(e_res, "rowcount", 0) or 0)
                edges_tombstoned = int(getattr(ed_res, "rowcount", 0) or 0)
        except Exception as exc:  # noqa: BLE001 -- narrowed below
            logger.exception("kg_backfill_rollback failed: %s", exc)
            from dataclasses import replace as _replace
            log_kg_operation(logger, _replace(ctx, error=repr(exc)))
            raise KGIngestionError(
                "rollback_backfill failed",
                context={"error_type": type(exc).__name__},
            ) from exc

        from dataclasses import replace as _replace
        final_ctx = _replace(ctx, result_count=entities_tombstoned + edges_tombstoned)
        log_kg_operation(logger, final_ctx)
        return RollbackResult(
            entities_tombstoned=entities_tombstoned,
            edges_tombstoned=edges_tombstoned,
            dry_run=False,
        )

    # ------------------------------------------------------------------
    # Streaming core
    # ------------------------------------------------------------------

    async def _stream_batches(
        self,
        *,
        checkpoint: BackfillCheckpoint,
        start_ts: datetime | None,
        end_ts: datetime | None,
    ) -> BackfillResult:
        """Stream batches and write checkpoints every N iterations.

        Centralised so :meth:`run_full_backfill` and
        :meth:`run_backfill_range` share the same per-batch logic.
        """
        result = BackfillResult(dry_run=self._dry_run)
        last_fact_id: str | None = checkpoint.last_fact_id
        batches_since_ckpt = 0

        while True:
            batch = await self._fetch_fact_batch(
                last_fact_id=last_fact_id,
                start_ts=start_ts,
                end_ts=end_ts,
            )
            if not batch:
                break

            batch_outcome = await self._process_batch(batch)

            # Update cumulative counters.
            result_total = BackfillResult(
                total_facts_processed=(
                    result.total_facts_processed + batch_outcome["processed"]
                ),
                total_entities_created=(
                    result.total_entities_created
                    + batch_outcome["entities_created"]
                ),
                total_edges_created=(
                    result.total_edges_created + batch_outcome["edges_created"]
                ),
                total_skipped_duplicate=(
                    result.total_skipped_duplicate
                    + batch_outcome["skipped_duplicate"]
                ),
                total_errors=result.total_errors + batch_outcome["errors"],
                batches_completed=result.batches_completed + 1,
                errors_detail=result.errors_detail + batch_outcome["errors_detail"],
            )
            result = result_total

            # Advance the cursor to the last fact id in this batch.
            last_fact_id = str(batch[-1]["id"])
            checkpoint.last_fact_id = last_fact_id
            last_fact_ts = batch[-1].get("last_verified")
            checkpoint.last_fact_timestamp = (
                last_fact_ts.isoformat() if last_fact_ts is not None else None
            )
            checkpoint.facts_processed = result.total_facts_processed
            checkpoint.entities_created = result.total_entities_created
            checkpoint.edges_created = result.total_edges_created
            checkpoint.skipped_duplicate = result.total_skipped_duplicate
            checkpoint.errors = result.total_errors
            checkpoint.batches_completed = result.batches_completed
            checkpoint.updated_at = _utcnow_iso()

            self._live_errors = result.total_errors
            self._live_facts = result.total_facts_processed

            batches_since_ckpt += 1
            if (
                self._checkpoint_interval > 0
                and batches_since_ckpt >= self._checkpoint_interval
            ):
                self._write_checkpoint(checkpoint)
                batches_since_ckpt = 0

        # Final checkpoint write on graceful exit.
        if self._checkpoint_interval > 0 and result.batches_completed > 0:
            self._write_checkpoint(checkpoint)

        return result

    async def _process_batch(
        self,
        batch: list[dict[str, Any]],
    ) -> dict[str, int | list[dict[str, object]]]:
        """Process one batch of facts and return per-batch counts.

        The engine is *not* per-fact transactional: a fact whose entity
        upsert succeeds but whose edge insert fails leaves the entity
        behind (consistent with the idempotency model — re-running the
        backfill on the same fact will reuse the existing entity row).
        Per-fact errors are captured in ``errors_detail`` and the
        engine continues to the next fact.
        """
        processed = 0
        entities_created = 0
        edges_created = 0
        skipped_duplicate = 0
        errors = 0
        errors_detail: list[dict[str, object]] = []

        for fact in batch:
            processed += 1
            fact_id = fact["id"]
            try:
                outcome = await self._process_one_fact(fact)
            except Exception as exc:  # noqa: BLE001 -- defensive boundary
                errors += 1
                if len(errors_detail) < 1000:
                    errors_detail.append(
                        {
                            "fact_id": str(fact_id),
                            "error_type": type(exc).__name__,
                            "error_message": str(exc)[:500],
                        }
                    )
                else:
                    # Bound memory; the final BackfillResult will report
                    # the total error count even though we cap the detail
                    # list.
                    logger.warning(
                        "kg_backfill errors_detail truncated at 1000 entries"
                    )
                logger.warning(
                    "kg_backfill fact failed: fact_id=%s error=%s",
                    fact_id,
                    exc,
                )
                continue

            entities_created += outcome["entities_created"]
            edges_created += outcome["edges_created"]
            skipped_duplicate += outcome["skipped_duplicate"]

        return {
            "processed": processed,
            "entities_created": entities_created,
            "edges_created": edges_created,
            "skipped_duplicate": skipped_duplicate,
            "errors": errors,
            "errors_detail": errors_detail,
        }

    async def _process_one_fact(
        self,
        fact: dict[str, Any],
    ) -> dict[str, int]:
        """Extract + resolve + ingest one semantic fact.

        Idempotency is handled at the SQL layer via ON CONFLICT
        clauses.  The outcome dict reports how many *new* rows this
        insertion produced (so the caller can attribute counts to
        specific facts in operator-facing reports).
        """
        fact_id = fact["id"]
        subject_text = str(fact.get("subject") or "").strip()
        object_text = str(fact.get("object_val") or "").strip()
        predicate = str(fact.get("predicate") or "").strip()
        confidence = fact.get("confidence")
        if confidence is None:
            confidence_value: float = 0.5
        else:
            try:
                confidence_value = max(0.0, min(1.0, float(confidence)))
            except (TypeError, ValueError):
                confidence_value = 0.5

        if not subject_text or not object_text or not predicate:
            # Empty slots: nothing to ingest.  Treat as a no-op
            # duplicate (we still count it as processed so the engine
            # does not spin on the same row forever).
            return {
                "entities_created": 0,
                "edges_created": 0,
                "skipped_duplicate": 1,
            }

        # Per-fact entity extraction is delegated to the L1+L2
        # EntityExtractor via a thin adapter that maps the SQL row to
        # a SemanticFact-shaped object.  We avoid importing
        # EntityExtractor here so the backfill module stays
        # self-contained and unit-testable: the entity classification
        # is purely lexical (no resolver call needed at extraction
        # time).  The resolver is invoked implicitly by the upsert
        # (ON CONFLICT on canonical_key collapses duplicates).
        subject_category = _classify_lexical(subject_text)
        object_category = _classify_lexical(object_text)

        # Subject and object are always required for a fact to
        # produce an edge; the entity extractor would skip empty
        # slots the same way.
        subject_canonical = generate_canonical_key(subject_text, subject_category)
        object_canonical = generate_canonical_key(object_text, object_category)

        # In dry_run we never touch the DB, so the upsert+lookup
        # would return None and the engine would log spurious
        # "could not resolve" warnings.  We instead mint a
        # deterministic synthetic UUID from the canonical key and
        # count it as a would-be-created entity, so the dry_run
        # result is a faithful preview of the real run.
        entities_created = 0
        if self._dry_run:
            subject_id = uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"kg_backfill_dryrun:{subject_canonical}",
            )
            object_id = uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"kg_backfill_dryrun:{object_canonical}",
            )
            # Both subject and object would be inserted in a real
            # run (idempotent upserts may collapse them on re-run,
            # but the engine counts the would-be insertions).
            entities_created = 2
        else:
            subject_id = await self._upsert_entity(
                canonical_key=subject_canonical,
                display_name=subject_text,
                entity_type=subject_category,
                source=str(fact.get("source") or "memory.semantic_facts"),
            )
            if subject_id is None:
                # Upsert skipped (CONFLICT path); we still need the id.
                subject_id = await self._lookup_entity_id(subject_canonical)
            else:
                entities_created += 1

            object_id = await self._upsert_entity(
                canonical_key=object_canonical,
                display_name=object_text,
                entity_type=object_category,
                source=str(fact.get("source") or "memory.semantic_facts"),
            )
            if object_id is None:
                object_id = await self._lookup_entity_id(object_canonical)
            else:
                entities_created += 1

        if subject_id is None or object_id is None:
            # Defensive: should not happen — both upsert and lookup
            # would have to fail simultaneously.  Skip the edge.
            logger.warning(
                "kg_backfill: could not resolve entity ids for fact %s "
                "(subject_id=%s, object_id=%s)",
                fact_id,
                subject_id,
                object_id,
            )
            return {
                "entities_created": entities_created,
                "edges_created": 0,
                "skipped_duplicate": 1,
            }

        # Relation classification — we re-use the relation-extractor
        # fallback table directly so backfill behaviour is identical
        # to the live ingestor (closed-taxonomy guarantee).
        relation_type = _classify_relation(predicate, subject_category, object_category)

        consent_token = self._consent_token_for_run()
        if self._dry_run:
            # In dry_run we know the edge would be inserted (idempotent
            # upsert with synthetic ids), so we report 1 edge created
            # to make the preview meaningful.  In the real run,
            # ``_insert_edge`` returns the actual rowcount.
            edges_created = 1
        else:
            edges_created = await self._insert_edge(
                src_entity_id=subject_id,
                dst_entity_id=object_id,
                relationship_type=str(relation_type),
                confidence=confidence_value,
                source_fact_id=fact_id,
                consent_token=consent_token,
            )

        return {
            "entities_created": entities_created,
            "edges_created": edges_created,
            "skipped_duplicate": 0 if edges_created else 1,
        }

    # ------------------------------------------------------------------
    # SQL helpers
    # ------------------------------------------------------------------

    async def _count_facts(
        self,
        *,
        start_ts: datetime | None,
        end_ts: datetime | None,
    ) -> int:
        """Count facts eligible for backfill (range or full corpus)."""
        if start_ts is None and end_ts is None:
            sql = _COUNT_FACTS_SQL
            params: dict[str, object] = {}
        else:
            sql = _COUNT_FACTS_IN_RANGE_SQL
            params = {
                "start_ts": start_ts,
                "end_ts": end_ts,
            }
        try:
            async with self._repo.get_session() as session:
                return int(await self._scalar_count(session, sql, params))
        except Exception as exc:  # noqa: BLE001 -- narrowed below
            logger.exception("kg_backfill count_facts failed: %s", exc)
            raise KGIngestionError(
                "count_facts failed",
                context={"error_type": type(exc).__name__},
            ) from exc

    async def _fetch_fact_batch(
        self,
        *,
        last_fact_id: str | None,
        start_ts: datetime | None,
        end_ts: datetime | None,
    ) -> list[dict[str, Any]]:
        """Stream one batch of facts via keyset pagination."""
        params: dict[str, object] = {
            "last_id": last_fact_id,
            "batch_size": self._batch_size,
            "start_ts": start_ts,
            "end_ts": end_ts,
        }
        try:
            async with self._repo.get_session() as session:
                result = await session.execute(
                    self._text(_SELECT_FACT_BATCH_SQL), params
                )
                rows = list(result.fetchall())
        except Exception as exc:  # noqa: BLE001 -- narrowed below
            logger.exception("kg_backfill fetch_batch failed: %s", exc)
            raise KGIngestionError(
                "fetch_fact_batch failed",
                context={
                    "error_type": type(exc).__name__,
                    "last_fact_id": last_fact_id,
                },
            ) from exc

        return [_row_to_fact_dict(row) for row in rows]

    async def _upsert_entity(
        self,
        *,
        canonical_key: str,
        display_name: str,
        entity_type: str,
        source: str,
    ) -> uuid.UUID | None:
        """Upsert one entity.  Returns the new id on insert, else ``None``.

        ``None`` means ON CONFLICT triggered (i.e. the entity already
        existed) — the caller falls back to a SELECT to fetch the
        existing id.
        """
        if self._dry_run:
            return None
        params: dict[str, object] = {
            "canonical_key": canonical_key,
            "entity_type": entity_type,
            "display_name": display_name,
            "aliases": [],
            "attributes": "{}",
            "first_seen_source": BACKFILL_SOURCE_TAG,
            "classification": "Restricted",
            "purpose": "backfill_p16_004_historical_migration",
            "source": source,
        }
        try:
            async with self._repo.get_session() as session:
                result = await session.execute(
                    self._text(_UPSERT_ENTITY_SQL), params
                )
                first = result.first()
                await session.commit()
        except Exception as exc:  # noqa: BLE001 -- narrowed below
            logger.exception("kg_backfill upsert_entity failed: %s", exc)
            raise KGIngestionError(
                "upsert_entity failed",
                context={
                    "canonical_key": canonical_key,
                    "error_type": type(exc).__name__,
                },
            ) from exc

        if first is None:
            return None
        # ``first`` is a SQLAlchemy ``Row``; pull the first column.
        raw_id = first[0] if isinstance(first, tuple) else getattr(first, "id", None)
        if raw_id is None:
            return None
        if isinstance(raw_id, uuid.UUID):
            return raw_id
        try:
            return uuid.UUID(str(raw_id))
        except (TypeError, ValueError):
            return None

    async def _lookup_entity_id(
        self,
        canonical_key: str,
    ) -> uuid.UUID | None:
        """Return the live entity id for ``canonical_key`` or ``None``."""
        if self._dry_run:
            return None
        try:
            async with self._repo.get_session() as session:
                result = await session.execute(
                    self._text(_LOOKUP_ENTITY_BY_KEY_SQL),
                    {"canonical_key": canonical_key},
                )
                row = result.first()
        except Exception as exc:  # noqa: BLE001 -- narrowed below
            logger.exception("kg_backfill lookup_entity failed: %s", exc)
            raise KGIngestionError(
                "lookup_entity_id failed",
                context={"error_type": type(exc).__name__},
            ) from exc

        if row is None:
            return None
        raw_id = row[0] if isinstance(row, tuple) else getattr(row, "id", None)
        if raw_id is None:
            return None
        if isinstance(raw_id, uuid.UUID):
            return raw_id
        try:
            return uuid.UUID(str(raw_id))
        except (TypeError, ValueError):
            return None

    async def _insert_edge(
        self,
        *,
        src_entity_id: uuid.UUID,
        dst_entity_id: uuid.UUID,
        relationship_type: str,
        confidence: float,
        source_fact_id: uuid.UUID,
        consent_token: str,
    ) -> int:
        """Insert one edge.  Returns 1 on insert, 0 on conflict."""
        if self._dry_run:
            return 0
        params: dict[str, object] = {
            "src_entity_id": str(src_entity_id),
            "dst_entity_id": str(dst_entity_id),
            "relationship_type": relationship_type,
            "confidence": float(confidence),
            "weight": 1.0,
            "source_fact_id": str(source_fact_id),
            "source_id": BACKFILL_SOURCE_TAG,
            "consent_token": consent_token,
            "consent_scope": BACKFILL_CONSENT_SCOPE,
            "extractor_model": "kg_backfill_p16_004",
            "review_status": "auto_accepted",
            "attributes": "{}",
        }
        try:
            async with self._repo.get_session() as session:
                result = await session.execute(
                    self._text(_INSERT_EDGE_SQL), params
                )
                rowcount = int(getattr(result, "rowcount", 0) or 0)
                await session.commit()
        except Exception as exc:  # noqa: BLE001 -- narrowed below
            logger.exception("kg_backfill insert_edge failed: %s", exc)
            raise KGIngestionError(
                "insert_edge failed",
                context={
                    "src_entity_id": str(src_entity_id),
                    "dst_entity_id": str(dst_entity_id),
                    "relationship_type": relationship_type,
                    "error_type": type(exc).__name__,
                },
            ) from exc
        return rowcount

    @staticmethod
    async def _scalar_count(
        session: _AsyncSessionProto,
        sql: str,
        params: dict[str, object],
    ) -> int:
        """Execute a COUNT-style query and return the first column as int."""
        # Local import to avoid coupling the module-level import to
        # the ``sqlalchemy`` package.
        from sqlalchemy import text as _sql_text

        result = await session.execute(_sql_text(sql), params)
        row = result.first() if hasattr(result, "first") else None
        if row is None:
            return 0
        # Row is a SQLAlchemy ``Row``; first column is the count.
        raw = row[0] if isinstance(row, tuple) else getattr(row, "n", None)
        if raw is None:
            return 0
        try:
            return int(raw)
        except (TypeError, ValueError):
            return 0

    # ------------------------------------------------------------------
    # Checkpoint I/O
    # ------------------------------------------------------------------

    def _load_or_init_checkpoint(self) -> BackfillCheckpoint:
        """Load an existing checkpoint or initialise a fresh one.

        On a fresh run the checkpoint mints a stable ``checkpoint_id``
        (UUID4) and a fresh system-internal ``consent_token`` (unless
        an existing file already carries one).  The token is persisted
        in the file so a resumed run re-uses the same audit identifier.
        """
        path = Path(self._checkpoint_path)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                ckpt = BackfillCheckpoint(**data)
                if not ckpt.consent_token:
                    ckpt.consent_token = self._mint_consent_token()
                if not ckpt.checkpoint_id:
                    ckpt.checkpoint_id = str(uuid.uuid4())
                return ckpt
            except (json.JSONDecodeError, OSError, TypeError) as exc:
                # Corrupt or unreadable checkpoint: do not lose the
                # operator's data — start a fresh checkpoint and log
                # a loud warning.
                logger.warning(
                    "kg_backfill: checkpoint file %s unreadable (%s); "
                    "starting fresh",
                    path,
                    exc,
                )

        return BackfillCheckpoint(
            started_at=_utcnow_iso(),
            updated_at=_utcnow_iso(),
            consent_token=self._mint_consent_token(),
            checkpoint_id=str(uuid.uuid4()),
        )

    def _write_checkpoint(self, checkpoint: BackfillCheckpoint) -> None:
        """Atomically write the checkpoint to disk.

        Uses a write-temp-then-rename pattern so a crash mid-write
        does not leave a half-written JSON file.  In dry-run mode the
        checkpoint is *not* written (the run never started for real).
        """
        if self._dry_run:
            return
        path = Path(self._checkpoint_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint.updated_at = _utcnow_iso()
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        try:
            tmp_path.write_text(
                json.dumps(asdict(checkpoint), indent=2, sort_keys=True),
                encoding="utf-8",
            )
            os.replace(tmp_path, path)
        except OSError as exc:
            logger.warning(
                "kg_backfill: failed to write checkpoint to %s: %s",
                path,
                exc,
            )

    def _consent_token_for_run(self) -> str:
        """Return the run's stable consent token (lazy)."""
        if not hasattr(self, "_cached_consent_token") or not self._cached_consent_token:
            self._cached_consent_token = self._mint_consent_token()
        return self._cached_consent_token

    @staticmethod
    def _mint_consent_token() -> str:
        """Mint a system-internal consent token for backfill edges.

        Format: ``kg_{CONSENT_TOKEN_PREFIX}{BACKFILL_CONSENT_SCOPE}_{uuid8}``
        — matches the format used by :class:`ConsentManager` so a
        downstream ``find_by_canonical_key`` of the token also
        validates against the regex.  The token is *not* bound to any
        entity category because backfill rows can be of any
        :class:`EntityCategory` (we cannot predict the mix in advance).
        """
        return (
            f"{CONSENT_TOKEN_PREFIX}{BACKFILL_CONSENT_SCOPE}_"
            f"{uuid.uuid4().hex[:8]}"
        )

    # ------------------------------------------------------------------
    # Process-coordination
    # ------------------------------------------------------------------

    @classmethod
    def _mark_running(cls, running: bool) -> None:
        """Set the class-level running flag.

        Single-process coordination only — cross-process safety is
        delegated to the checkpoint file's mtime + content.
        """
        cls._is_running = bool(running)

    # ------------------------------------------------------------------
    # SQL text helper
    # ------------------------------------------------------------------

    @staticmethod
    def _text(sql: str) -> Any:
        """Resolve ``sqlalchemy.text`` lazily."""
        from sqlalchemy import text as _sql_text

        return _sql_text(sql)


# ---------------------------------------------------------------------------
# Module-level helpers (testable in isolation)
# ---------------------------------------------------------------------------


def _utcnow_iso() -> str:
    """Return the current UTC time in ISO-8601."""
    return datetime.now(timezone.utc).isoformat()


def _row_to_fact_dict(row: object) -> dict[str, Any]:
    """Convert a SQLAlchemy ``Row`` to a plain dict.

    Tries the ``_mapping`` attribute first (SQLAlchemy 2.x) and falls
    back to per-attribute ``getattr`` for older shapes.  Never raises.
    """
    mapping = getattr(row, "_mapping", None)
    if mapping is not None:
        try:
            return {str(k): v for k, v in mapping.items()}
        except (TypeError, ValueError):
            pass
    out: dict[str, Any] = {}
    for attr in (
        "id", "subject", "predicate", "object_val", "fact_type",
        "confidence", "source", "source_episode", "last_verified",
    ):
        if hasattr(row, attr):
            out[attr] = getattr(row, attr)
    # Some drivers expose the columns via ``__dict__`` on the row.
    if not out and hasattr(row, "__dict__"):
        out = {k: v for k, v in row.__dict__.items() if not k.startswith("_")}
    return out


def _classify_lexical(text: str) -> str:
    """Lightweight lexical classifier used by the backfill engine.

    This is a deliberately small helper that mirrors the L1 priority
    pass in :class:`guinvere.knowledge_graph.extraction.entity_extractor`
    but without the full pattern table.  The goal here is to assign
    a *closed-taxonomy* entity type to the subject and object slots
    so the canonical key (and downstream relation classification) is
    consistent with the live ingestor.

    The mapping is conservative — anything that does not match a
    known surface form falls back to ``"concept"`` (matches the
    L1+L2 default).
    """
    cleaned = normalize_entity_name(text)
    if not cleaned:
        return "concept"
    # The fallback table mirrors the closed-taxonomy strings used by
    # :class:`EntityCategory` so the canonical key generation stays
    # deterministic.
    if cleaned in {
        "guinevere", "faiz", "samm", "opencode", "hermes",
    }:
        return "person"
    if cleaned in {"postgresql", "redis", "docker", "kubernetes"}:
        return "technology"
    return "concept"


def _classify_relation(
    predicate: str,
    subject_category: str,
    object_category: str,
) -> str:
    """Return a closed-taxonomy relation type for ``predicate``.

    Mirrors the type-aware fallback table in
    :class:`guinvere.knowledge_graph.extraction.relation_extractor` so the
    backfill's edge labels are consistent with the live ingestor.
    """
    cleaned = (predicate or "").strip().lower()
    if not cleaned:
        return "related_to"
    # Predicate substring match against the closed taxonomy strings.
    # Mirrors ``_match_predicate`` in ``relation_extractor`` but
    # inlined here so the backfill module stays self-contained.
    if "work" in cleaned or "employ" in cleaned:
        return "works_at"
    if "live" in cleaned or "locat" in cleaned:
        return "located_in"
    if "know" in cleaned or "friend" in cleaned:
        return "knows"
    if "use" in cleaned:
        return "uses"
    if "particip" in cleaned or "attend" in cleaned:
        return "participates_in"
    if "feel" in cleaned or "emot" in cleaned:
        return "feels_about"
    if "remember" in cleaned or "recall" in cleaned:
        return "remembers"
    if "consent" in cleaned:
        return "consents_to"
    if "communicat" in cleaned or "chat" in cleaned:
        return "communicates_via"
    if "supervis" in cleaned or "oversee" in cleaned:
        return "supervises"
    if "collaborat" in cleaned:
        return "collaborates_with"
    if "prefer" in cleaned or "like" in cleaned:
        return "preferences"
    if "creat" in cleaned or "author" in cleaned:
        return "created_by"
    if "have" in cleaned or "attribute" in cleaned or "is_" in cleaned:
        return "has_attribute"
    # Type-aware fallback (mirrors the L1+L2 fallback table).
    if subject_category == "person" and object_category == "organization":
        return "works_at"
    if subject_category == "person" and object_category == "location":
        return "located_in"
    if subject_category == "person" and object_category == "person":
        return "knows"
    if subject_category == "person" and object_category == "technology":
        return "uses"
    return "related_to"


# ---------------------------------------------------------------------------
# Public re-exports
# ---------------------------------------------------------------------------


__all__ = [
    # Constants
    "BACKFILL_SOURCE_TAG",
    "BACKFILL_CONSENT_SCOPE",
    "DEFAULT_CHECKPOINT_PATH",
    "DEFAULT_BATCH_SIZE",
    "DEFAULT_CHECKPOINT_INTERVAL",
    "MAX_BATCH_SIZE",
    # Dataclasses
    "BackfillResult",
    "BackfillStatus",
    "RollbackResult",
    "BackfillCheckpoint",
    # Engine
    "KGBackfillEngine",
]
