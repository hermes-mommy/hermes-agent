"""P16-002: APScheduler cron registration for the KG ingestion pipeline.

Schedules the daily :class:`BatchProcessor` run at 03:30
``Asia/Bangkok`` (ICT, no DST) — exactly 30 minutes after the daily
episodic-to-semantic consolidation job (which fires at 03:00 ICT in
``guinvere.memory.consolidation``).  The 30-minute buffer ensures all new
``semantic_facts`` rows produced by overnight consolidation are
committed and visible to the ingestion query.

Design notes:

* Mirrors ``guinvere.memory.consolidation.register_consolidation_job`` so the
  two jobs are configured with the same knobs (``misfire_grace_time``,
  ``replace_existing``).
* The scheduler is duck-typed via :class:`SchedulerProtocol` — keeps this
  module free of an APScheduler import so unit tests can register the
  job against a fake scheduler without pulling in the APScheduler runtime.
* Failure policy is "log + re-raise" — same as consolidation.  APScheduler
  captures the exception and surfaces it through its own logger; an
  empty catch would mask real outages (per AGENTS.md BLOCKING rule).
* The job runs against :class:`BatchProcessor.process_unprocessed_facts`,
  NOT :meth:`KGIngestionPipeline.ingest_from_consolidation`, because the
  cron job must also drain any backlog from previous runs that crashed
  mid-flight.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Protocol, cast

from guinvere.knowledge_graph.ingestion.batch_processor import (
    BacklogSnapshot,
    BatchProcessor,
)
from guinvere.knowledge_graph.ingestion.pipeline import (
    BatchIngestionResult,
    KGIngestionPipeline,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants — mirror of guinvere.memory.consolidation
# ---------------------------------------------------------------------------

KG_INGESTION_JOB_ID: str = "daily_kg_ingestion"
"""APScheduler job identifier for the daily KG ingestion job."""

KG_INGESTION_DEFAULT_HOUR: int = 3
"""Scheduled hour (03:xx ICT) for daily KG ingestion."""

KG_INGESTION_DEFAULT_MINUTE: int = 30
"""Scheduled minute (03:30 ICT) for daily KG ingestion."""

KG_INGESTION_DEFAULT_TIMEZONE: str = "Asia/Bangkok"
"""Timezone string for the cron trigger.

Matches ``guinvere.memory.consolidation.TZ_BANGKOK`` — ICT has no DST."""

KG_INGESTION_DEFAULT_BACKLOG_LIMIT: int = 10_000
"""Per-run cap on the number of facts the cron job will process.

Keeps the longest-running pass bounded; the next cron tick picks up
where this one stopped."""

KG_INGESTION_DEFAULT_BATCH_SIZE: int = 100
"""Per-transaction batch size for the cron job.

Mirrors :data:`KGConfig.kg_batch_size` (Pydantic default)."""


# ---------------------------------------------------------------------------
# Protocol — matches guinvere.memory.consolidation.SchedulerProtocol
# ---------------------------------------------------------------------------


class SchedulerProtocol(Protocol):
    """Minimal scheduler interface used by APScheduler registration.

    Mirrors :class:`guinvere.memory.consolidation.SchedulerProtocol` so the
    same fake / mock scheduler implementation works for both the
    consolidation and the KG-ingestion registration helpers.
    """

    def add_job(
        self,
        func: object,
        *,
        trigger: str,
        id: str,
        kwargs: dict[str, object],
        name: str,
        replace_existing: bool,
        misfire_grace_time: int,
        hour: int,
        minute: int,
        timezone: str,
    ) -> object:
        ...


class _SessionFactory(Protocol):
    """Minimal async session-factory protocol."""

    def __call__(self) -> object:  # pragma: no cover -- structural
        ...


# ---------------------------------------------------------------------------
# Session-factory adapter — the APScheduler signature requires a callable
# whose first parameter is ``session_factory``.  ``guinvere.knowledge_graph``
# uses a session-factory protocol, so we type-narrow at the boundary.
# ---------------------------------------------------------------------------


def _coerce_session_factory(
    session_factory: _SessionFactory,
) -> Callable[[], object]:
    """Type-erasure boundary so the APScheduler kwarg matches the job signature.

    APScheduler calls the job function with the kwargs registered here
    verbatim — the typed ``_SessionFactory`` protocol is a guidance
    tool, not a runtime check.  We use :func:`typing.cast` (which is a
    type-checker-only annotation, not a runtime conversion) so the
    return type stays honest without resorting to ``# type: ignore``.
    """
    return cast(Callable[[], object], session_factory)


# ---------------------------------------------------------------------------
# Public API — registration helper
# ---------------------------------------------------------------------------


def register_kg_ingestion_job(
    scheduler: SchedulerProtocol,
    session_factory: _SessionFactory,
    pipeline: KGIngestionPipeline,
    *,
    hour: int = KG_INGESTION_DEFAULT_HOUR,
    minute: int = KG_INGESTION_DEFAULT_MINUTE,
    timezone: str = KG_INGESTION_DEFAULT_TIMEZONE,
    backlog_limit: int = KG_INGESTION_DEFAULT_BACKLOG_LIMIT,
    batch_size: int = KG_INGESTION_DEFAULT_BATCH_SIZE,
) -> object:
    """Register the daily KG ingestion job on an APScheduler v3 scheduler.

    Mirrors :func:`guinvere.memory.consolidation.register_consolidation_job` so
    the two cron jobs are configured identically (``misfire_grace_time``,
    ``replace_existing``).  The job fires at ``hour:minute`` in the
    supplied timezone — defaults to ``03:30 Asia/Bangkok`` so it runs 30
    minutes after consolidation completes.

    Parameters
    ----------
    scheduler:
        An active APScheduler v3 ``AsyncIOScheduler`` instance (or any
        object satisfying :class:`SchedulerProtocol`).
    session_factory:
        Callable returning an async SQLAlchemy session.  Passed as a
        keyword argument to the job function.  ``None`` is allowed for
        graceful no-op behaviour when no DB sessionmaker is configured.
    pipeline:
        The :class:`KGIngestionPipeline` instance to use.  Held by the
        job callback via the closure-free APScheduler kwargs.
    hour:
        Scheduled hour (``0-23``) for the daily run.  Default ``3``
        matches :data:`KGConfig.kg_cron_hour`.
    minute:
        Scheduled minute (``0-59``).  Default ``30`` matches
        :data:`KGConfig.kg_cron_minute`.
    timezone:
        IANA timezone string for the cron trigger.  Default
        ``"Asia/Bangkok"`` — ICT has no DST.
    backlog_limit:
        Maximum number of facts the cron job will drain per run.
        Default ``10_000``.
    batch_size:
        Per-transaction batch size used by the underlying
        :class:`BatchProcessor`.  Default ``100`` matches
        :data:`KGConfig.kg_batch_size`.

    Returns
    -------
    object
        The :class:`apscheduler.job.Job` instance returned by
        ``scheduler.add_job`` — exposed for tests / observability.

    Raises
    ------
    ValueError
        If ``hour`` is not in ``[0, 23]`` or ``minute`` is not in
        ``[0, 59]`` or ``backlog_limit`` / ``batch_size`` are < 1.
    """
    if scheduler is None:
        raise ValueError("scheduler is required")
    if session_factory is None:
        raise ValueError("session_factory is required")
    if pipeline is None:
        raise ValueError("pipeline is required")
    if not (0 <= int(hour) <= 23):
        raise ValueError(f"hour must be in [0, 23]; got {hour!r}")
    if not (0 <= int(minute) <= 59):
        raise ValueError(f"minute must be in [0, 59]; got {minute!r}")
    if backlog_limit < 1:
        raise ValueError(f"backlog_limit must be >= 1; got {backlog_limit!r}")
    if batch_size < 1:
        raise ValueError(f"batch_size must be >= 1; got {batch_size!r}")
    if not timezone or not timezone.strip():
        raise ValueError("timezone must be a non-empty IANA string")

    coerced_factory = _coerce_session_factory(session_factory)

    job = scheduler.add_job(
        _run_ingestion_job,
        trigger="cron",
        id=KG_INGESTION_JOB_ID,
        kwargs={
            "session_factory": coerced_factory,
            "pipeline": pipeline,
            "backlog_limit": int(backlog_limit),
            "batch_size": int(batch_size),
        },
        name="Daily Knowledge Graph Ingestion",
        replace_existing=True,
        misfire_grace_time=3600,
        hour=int(hour),
        minute=int(minute),
        timezone=timezone,
    )

    logger.info(
        "kg_ingestion_job_registered",
        extra={
            "job_id": KG_INGESTION_JOB_ID,
            "trigger": "cron",
            "hour": int(hour),
            "minute": int(minute),
            "timezone": timezone,
            "backlog_limit": int(backlog_limit),
            "batch_size": int(batch_size),
        },
    )
    return job


# ---------------------------------------------------------------------------
# Job callback
# ---------------------------------------------------------------------------


async def _run_ingestion_job(
    session_factory: Callable[[], object] | None = None,
    pipeline: KGIngestionPipeline | None = None,
    *,
    backlog_limit: int = KG_INGESTION_DEFAULT_BACKLOG_LIMIT,
    batch_size: int = KG_INGESTION_DEFAULT_BATCH_SIZE,
) -> BatchIngestionResult:
    """APScheduler job entry point for the daily KG ingestion run.

    Wraps :meth:`BatchProcessor.process_unprocessed_facts` with
    metadata-only logging and structured failure handling.  On any
    unexpected exception the error is logged and re-raised so
    APScheduler's own retry / alert machinery can act — never an empty
    catch (per AGENTS.md BLOCKING rule).

    Parameters
    ----------
    session_factory:
        Callable returning an async SQLAlchemy session.  When ``None``
        (e.g. no DB sessionmaker configured), logs a warning and
        returns an empty :class:`BatchIngestionResult`.
    pipeline:
        The :class:`KGIngestionPipeline` instance to use.  ``None``
        triggers the same graceful-skip path as a missing session
        factory.
    backlog_limit:
        Cap on the number of facts processed in this run.  Forwarded
        to :meth:`BatchProcessor.process_unprocessed_facts`.
    batch_size:
        Per-transaction batch size.  Forwarded to
        :meth:`BatchProcessor.process_unprocessed_facts`.

    Returns
    -------
    BatchIngestionResult
        Summary from the run — counts of facts, entities, edges,
        errors, and the per-fact outcome list.  Empty result is
        returned when no session factory is configured.

    Raises
    ------
    Exception
        Re-raised after logging error metadata so APScheduler's own
        retry / alert machinery can act.
    """
    try:
        logger.info(
            "kg_ingestion_job_started",
            extra={
                "job_id": KG_INGESTION_JOB_ID,
                "backlog_limit": int(backlog_limit),
                "batch_size": int(batch_size),
            },
        )

        if session_factory is None or pipeline is None:
            logger.warning(
                "kg_ingestion_job_no_dependencies",
                extra={
                    "job_id": KG_INGESTION_JOB_ID,
                    "has_session_factory": session_factory is not None,
                    "has_pipeline": pipeline is not None,
                    "detail": "Missing dependencies; skipping ingestion",
                },
            )
            return BatchIngestionResult(total_facts=0, per_fact=[])

        processor = BatchProcessor(pipeline, batch_size=int(batch_size))
        async with session_factory() as session:
            snapshot: BacklogSnapshot = await processor.snapshot_backlog(session)
            logger.info(
                "kg_ingestion_backlog_snapshot",
                extra={
                    "job_id": KG_INGESTION_JOB_ID,
                    "candidate_count": snapshot.candidate_count,
                },
            )
            if snapshot.candidate_count == 0:
                logger.info(
                    "kg_ingestion_job_completed_empty",
                    extra={"job_id": KG_INGESTION_JOB_ID},
                )
                return BatchIngestionResult(total_facts=0, per_fact=[])
            result = await processor.process_unprocessed_facts(
                session, limit=int(backlog_limit)
            )

        logger.info(
            "kg_ingestion_job_completed",
            extra={
                "job_id": KG_INGESTION_JOB_ID,
                "total_facts": result.total_facts,
                "total_entities_created": result.total_entities_created,
                "total_entities_resolved": result.total_entities_resolved,
                "total_edges_created": result.total_edges_created,
                "total_edges_skipped_duplicate": result.total_edges_skipped_duplicate,
                "total_errors": result.total_errors,
            },
        )
        return result

    except (RuntimeError, ValueError, TypeError, OSError, AttributeError):
        logger.error(
            "kg_ingestion_job_failed",
            extra={"job_id": KG_INGESTION_JOB_ID},
            exc_info=True,
        )
        raise