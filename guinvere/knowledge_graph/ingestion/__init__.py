"""KG ingestion submodule — batched write pipeline for entities and edges.

P16-002 (Wave 3) — orchestrator that turns consolidated ``semantic_facts``
into ``kg_entities`` and ``kg_edges`` rows, with batched backpressure and
a 03:30 ICT daily cron registration.

Public surface
--------------

* :class:`KGIngestionPipeline` — orchestrator.  Holds the five
  collaborators (entity extractor, entity resolver, relation extractor,
  consent manager, metrics singleton) and runs the per-fact ingestion
  flow.
* :class:`BatchProcessor` — wraps the pipeline with two operational
  primitives the cron job needs: ``process_unprocessed_facts`` (drains
  the LEFT-JOIN backlog) and ``process_facts_since`` (manual backfill
  from a timestamp).  Both support ``dry_run``.
* :func:`register_kg_ingestion_job` — APScheduler v3 cron registration at
  03:30 ``Asia/Bangkok``, 30 minutes after the daily consolidation
  job completes (see ``guinvere.memory.consolidation.register_consolidation_job``).

* :class:`KGBackfillEngine` (P16-004) — historical backfill of
  ``memory.semantic_facts`` into the KG.  Idempotent, checkpointable,
  soft-delete-only rollback.  See
  :mod:`guinvere.knowledge_graph.ingestion.backfill`.
* :class:`KGBackfillValidator` (P16-010) — read-only validation
  suite for the backfill output.  Entity coverage, edge integrity,
  orphan detection, duplicate triage, consent compliance, and
  tombstone consistency.  See
  :mod:`guinvere.knowledge_graph.ingestion.backfill_validator`.

Result types
------------

* :class:`IngestionResult` — per-fact outcome (counts + errors + fact id).
* :class:`BatchIngestionResult` — aggregate outcome (totals + per-fact list).
* :class:`BacklogSnapshot` — read-only summary of the ingestion backlog
  (returned by ``BatchProcessor.snapshot_backlog``).
* :class:`BackfillResult` / :class:`BackfillStatus` / :class:`RollbackResult`
  — backfill engine outcomes.
* :class:`ValidationReport` / :class:`CheckResult` / :class:`CoverageMetrics`
  — validator outcomes.

Sister modules: :mod:`guinvere.knowledge_graph.resolution`,
:mod:`guinvere.knowledge_graph.consent`, :mod:`guinvere.knowledge_graph.extraction`.

Safety / consent notes (per AGENTS.md BLOCKING rules and
PersonaSafetyPolicy):

* The pipeline never opens a write transaction in ``dry_run`` mode.
* Ingestion is the **cron path only** — the chat hot path stays
  out of the batch writer entirely.  This avoids blocking the request
  loop on bulk ``kg_entities`` / ``kg_edges`` INSERTs.
* All exceptions are caught at the per-fact boundary and surfaced via
  :attr:`IngestionResult.errors` — no empty catches, no silent failures.
* No type suppression: every SQL bind, every dataclass field, every
  return value is statically typed.
* The backfill engine never hard-deletes: ``rollback_backfill`` uses
  ``is_tombstoned = TRUE`` exclusively.  Idempotency is enforced at
  the SQL layer via ``ON CONFLICT DO NOTHING`` against the DDL
  UNIQUE constraints.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Pipeline (orchestrator + result dataclasses)
# ---------------------------------------------------------------------------

from guinvere.knowledge_graph.ingestion.batch_processor import (
    BacklogSnapshot,
    BatchProcessor,
)
from guinvere.knowledge_graph.ingestion.cron import (
    KG_INGESTION_DEFAULT_BACKLOG_LIMIT,
    KG_INGESTION_DEFAULT_BATCH_SIZE,
    KG_INGESTION_DEFAULT_HOUR,
    KG_INGESTION_DEFAULT_MINUTE,
    KG_INGESTION_DEFAULT_TIMEZONE,
    KG_INGESTION_JOB_ID,
    register_kg_ingestion_job,
)
from guinvere.knowledge_graph.ingestion.pipeline import (
    DEFAULT_CLASSIFICATION,
    DEFAULT_CONSENT_SCOPE,
    BatchIngestionResult,
    IngestionResult,
    KG_EDGES_TABLE,
    KG_ENTITIES_TABLE,
    KGIngestionPipeline,
    SOURCE_LABEL,
)

# ---------------------------------------------------------------------------
# Backfill (P16-004) and Backfill Validator (P16-010)
# ---------------------------------------------------------------------------

from guinvere.knowledge_graph.ingestion.backfill import (
    BACKFILL_CONSENT_SCOPE,
    BACKFILL_SOURCE_TAG,
    DEFAULT_BATCH_SIZE,
    DEFAULT_CHECKPOINT_INTERVAL,
    DEFAULT_CHECKPOINT_PATH,
    MAX_BATCH_SIZE,
    BackfillCheckpoint,
    BackfillResult,
    BackfillStatus,
    KGBackfillEngine,
    RollbackResult,
)
from guinvere.knowledge_graph.ingestion.backfill_validator import (
    MAX_DUPLICATE_SAMPLES,
    MAX_ISSUES_PER_CHECK,
    SEVERITY_CRITICAL,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    CheckResult,
    CoverageMetrics,
    KGBackfillValidator,
    ValidationReport,
)

__all__ = [
    # Orchestrator + result dataclasses
    "KGIngestionPipeline",
    "IngestionResult",
    "BatchIngestionResult",
    # Batch processor
    "BatchProcessor",
    "BacklogSnapshot",
    # Cron registration
    "register_kg_ingestion_job",
    # Constants
    "KG_INGESTION_JOB_ID",
    "KG_INGESTION_DEFAULT_HOUR",
    "KG_INGESTION_DEFAULT_MINUTE",
    "KG_INGESTION_DEFAULT_TIMEZONE",
    "KG_INGESTION_DEFAULT_BACKLOG_LIMIT",
    "KG_INGESTION_DEFAULT_BATCH_SIZE",
    # SQL table references
    "KG_ENTITIES_TABLE",
    "KG_EDGES_TABLE",
    # Defaults
    "DEFAULT_CONSENT_SCOPE",
    "DEFAULT_CLASSIFICATION",
    "SOURCE_LABEL",
    # Backfill (P16-004)
    "KGBackfillEngine",
    "BackfillResult",
    "BackfillStatus",
    "RollbackResult",
    "BackfillCheckpoint",
    "BACKFILL_SOURCE_TAG",
    "BACKFILL_CONSENT_SCOPE",
    "DEFAULT_CHECKPOINT_PATH",
    "MAX_BATCH_SIZE",
    # Validator (P16-010)
    "KGBackfillValidator",
    "CheckResult",
    "CoverageMetrics",
    "ValidationReport",
    "SEVERITY_CRITICAL",
    "SEVERITY_WARNING",
    "SEVERITY_INFO",
    "MAX_ISSUES_PER_CHECK",
    "MAX_DUPLICATE_SAMPLES",
]