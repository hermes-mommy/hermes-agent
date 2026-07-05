"""P3-015: Daily episodic-to-semantic memory consolidation.

Uses APScheduler v3 cron scheduling to run daily at 03:00
Asia/Bangkok (ICT, no DST).

Design principles:
- Idempotent: safe to re-run via deterministic content key and existence check.
- DNR-safe: ``do_not_recall`` episodes are always excluded.
- Safe-word aware: skips records tagged/typed as ``safe_word``, ``hard_stop``,
  ``crisis``, ``formal_hold``, or ``distress``.
- Classification-preserving: uses highest (most restrictive) classification
  among source episode and fact candidates (Public < Internal < Restricted <
  Confidential < Critical).
- Provenance: every created semantic fact stores ``source_episode``.
- Non-destructive pruning: default mode is ``archive`` (metadata-only); hard
  delete requires explicit configuration.
- No empty catches: job errors log metadata and re-raise.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol, TypedDict, final

from sqlalchemy import select

from guinevere.memory.embeddings import (
    CLASSIFICATION_ORDER,
    CRITICAL,
    RESTRICTED,
)
from guinevere.memory.models import Episodes, SemanticFacts
from guinevere.projects.registry import ProjectRegistry

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

UTC = timezone.utc
TZ_BANGKOK = "Asia/Bangkok"

CONSOLIDATION_JOB_ID = "daily_consolidation"
"""APScheduler job identifier for the daily consolidation job."""

CONSOLIDATION_HOUR = 3
"""Scheduled hour (03:00 ICT) for daily consolidation."""

CONSOLIDATION_MINUTE = 0
"""Scheduled minute."""

# P18-002: 6-hourly FSRS decay sweep.
DECAY_SWEEP_JOB_ID = "decay_sweep"
"""APScheduler job identifier for the 6-hourly FSRS decay sweep."""

DECAY_SWEEP_HOUR = 0
"""Anchor hour (00:00 ICT) for the decay sweep cron."""

DECAY_SWEEP_MINUTE = 0
"""Scheduled minute for the decay sweep."""

DECAY_SWEEP_INTERVAL_HOURS = 6
"""Interval between decay sweeps (hours).  6h matches the biologically-motivated
multi-period architecture benchmarked in
``research-reports/p18-consolidation-forgetting-benchmark.md``."""

# P18-002: Active forgetting threshold.
ACTIVE_FORGETTING_THRESHOLD = 0.1
"""Episodes with retrievability below this are candidates for active forgetting.
The 0.1 threshold matches the Mem0 default search threshold and the
benchmarked Ebbinghaus near-zero retention floor."""

ACTIVE_FORGETTING_GRACE_DAYS = 90
"""Minimum age (days) before an episode becomes eligible for active forgetting.
90 days protects recently-distilled facts from being pruned prematurely."""

ACTIVE_FORGETTING_IMPORTANCE_FLOOR = 8
"""Episodes with importance >= this value are protected from active forgetting.
High-importance memories (importance 8-10) represent critical context for Faiz
and should never be auto-archived regardless of retrievability."""

ACTIVE_FORGETTING_DEFAULT_MODE = "archive"
"""Default active-forgetting action — metadata-only ``deletion_state='archived'``,
mirrors :data:`RetentionConfig.mode='archive'` default."""

SAFE_WORD_INDICATORS: frozenset[str] = frozenset({
    "safe_word",
    "hard_stop",
    "crisis",
    "formal_hold",
    "distress",
})
"""Tags/episode_type/title/summary values that identify records to skip."""

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# TypedDict for fact-candidate dictionaries
# ---------------------------------------------------------------------------


class FactData(TypedDict, total=False):
    """Structured fact candidate extracted from an episode."""

    subject: str
    predicate: str
    object_val: str
    fact_type: str
    classification: str
    tags: list[str]
    confidence: float


# ---------------------------------------------------------------------------
# Protocols for execute result typing
# ---------------------------------------------------------------------------


class _ScalarResult(Protocol):
    """Minimal protocol for ``Result.scalars()``."""

    def all(self) -> list[object]:
        ...


class _ExecResult(Protocol):
    """Minimal protocol for ``session.execute()`` return."""

    def scalars(self) -> _ScalarResult:
        ...


class SchedulerProtocol(Protocol):
    """Minimal scheduler interface used by APScheduler registration."""

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


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@final
class ConsolidationResult:
    """Typed result from ``consolidate_episodes_to_facts``."""

    consolidated: int
    skipped_dnr: int
    skipped_safe_word: int
    skipped_exists: int
    facts_created: list[dict[str, str]]

    def __init__(
        self,
        consolidated: int = 0,
        skipped_dnr: int = 0,
        skipped_safe_word: int = 0,
        skipped_exists: int = 0,
        facts_created: list[dict[str, str]] | None = None,
    ) -> None:
        self.consolidated = consolidated
        self.skipped_dnr = skipped_dnr
        self.skipped_safe_word = skipped_safe_word
        self.skipped_exists = skipped_exists
        self.facts_created = facts_created or []


@final
class PruneResult:
    """Typed result from ``prune_stale_facts``."""

    pruned: int
    dry_run: int
    mode: str

    def __init__(
        self,
        pruned: int = 0,
        dry_run: int = 0,
        mode: str = "archive",
    ) -> None:
        self.pruned = pruned
        self.dry_run = dry_run
        self.mode = mode


# ---------------------------------------------------------------------------
# Session protocol
# ---------------------------------------------------------------------------


class AsyncSessionProtocol(Protocol):
    """Minimal async database session interface for consolidation.

    Covers the subset of SQLAlchemy ``AsyncSession`` used by this module.
    """

    async def execute(self, statement: object) -> _ExecResult:
        ...

    def add(self, obj: object) -> None:
        ...

    async def delete(self, obj: object) -> None:
        ...

    async def __aenter__(self) -> AsyncSessionProtocol:
        ...

    async def __aexit__(self, *args: object) -> None:
        ...


# ---------------------------------------------------------------------------
# Retention configuration
# ---------------------------------------------------------------------------


@dataclass
class RetentionConfig:
    """Configurable retention policy for semantic fact pruning.

    Default mode is ``archive`` (metadata-only update to ``deletion_state``).
    ``dry_run=True`` logs what would be pruned without making any changes.
    ``delete`` mode requires explicit opt-in and is not default.
    """

    min_retention_score: float = 0.05
    """Minimum retention/confidence score threshold (0.0-1.0)."""

    max_age_days: int = 365
    """Maximum age in days before a fact is eligible for pruning."""

    max_semantic_count: int = 10_000
    """Soft cap on total semantic facts before pruning triggers."""

    mode: str = "archive"
    """Pruning action: ``dry_run``, ``archive``, ``soft_delete``, or ``delete``."""

    protected_categories: list[str] = field(
        default_factory=lambda: ["strategy", "preference"]
    )
    """Tags/categories that are never pruned."""

    protected_importance_floor: float = 0.7
    """Never prune facts with confidence >= this threshold."""

    dry_run: bool = False
    """When True, log pruning candidates without applying any changes."""


# ---------------------------------------------------------------------------
# Core consolidation logic
# ---------------------------------------------------------------------------


async def consolidate_episodes_to_facts(
    session: AsyncSessionProtocol,
    *,
    watermark: datetime | None = None,
    now: datetime | None = None,
    kg_ingestion_enabled: bool = True,
    fsrs_enabled: bool = True,
) -> ConsolidationResult:
    """Idempotent episodic-to-semantic consolidation.

    Reads unconsolidated episodes (created after *watermark*), filters by DNR/
    safe-word rules, extracts semantic fact candidates, and upserts deduplicated
    ``SemanticFacts`` rows with provenance and highest classification.

    Parameters
    ----------
    session:
        An async SQLAlchemy session (or fake test session).
    watermark:
        Only process episodes with ``created_at`` after this timestamp.
        ``None`` means process all eligible episodes.
    now:
        Explicit "now" timestamp (for deterministic testing).  Defaults to
        ``datetime.now(UTC)``.
    kg_ingestion_enabled:
        When ``True`` (default), newly created facts are handed off to the
        post-consolidation KG ingestion hook after the upsert loop completes.
        Set to ``False`` to skip the hook (e.g. in tests or when the KG
        module is unavailable).  The hook uses a lazy import and swallows
        every error — consolidation itself never fails because of the KG
        layer.
    fsrs_enabled:
        When ``True`` (default), each consolidated episode receives a
        ``grade=Good`` FSRS review after the fact-creation loop so that its
        next-review timestamp lands in the future.  Lazy-imported from
        ``guinevere.memory.spaced_repetition``; if the optional ``fsrs`` library
        is missing, the call is silently skipped.

    Returns
    -------
    ConsolidationResult
        Summary with ``consolidated``, ``skipped_dnr``, ``skipped_safe_word``,
        ``skipped_exists``, and ``facts_created``.
    """
    if now is None:
        now = datetime.now(UTC)

    # Build query — select eligible episodes (non-DNR, after watermark)
    stmt = select(Episodes).where(Episodes.do_not_recall.is_(False))  # noqa: E712
    if watermark is not None:
        stmt = stmt.where(Episodes.created_at > watermark)

    exec_result = await session.execute(stmt)
    episodes = list(exec_result.scalars().all())

    consolidated = 0
    skipped_dnr = 0
    skipped_safe_word = 0
    skipped_exists = 0
    facts_created: list[dict[str, str]] = []
    consolidated_episodes: list[object] = []
    """Episodes that produced at least one fact candidate - used by the
    post-loop FSRS review hook (P18-002)."""

    for ep in episodes:
        # Defensive DNR skip (primary filter already excludes, but double-check)
        if getattr(ep, "do_not_recall", False):
            skipped_dnr += 1
            continue

        # Skip safe-word / crisis / formal-hold records
        if is_safe_word_record(ep):
            skipped_safe_word += 1
            continue

        # Extract fact candidates
        candidates = _extract_facts_from_episode(ep)
        if not candidates:
            continue

        # Episode metadata extracted via getattr (polymorphic: real ORM or FakeEpisode)
        _ep_id: object = getattr(ep, "id", None) or uuid.uuid4()
        _ep_cls_raw: object = getattr(ep, "classification", None)
        _ep_cls: str | None = str(_ep_cls_raw) if isinstance(_ep_cls_raw, str) else None

        # P19: Extract project_id and project_scope from source episode.
        # Falls back to the default project for legacy episodes with NULL project_id.
        _ep_project_id_raw: object = getattr(ep, "project_id", None)
        _ep_project_id: uuid.UUID | None = (
            _ep_project_id_raw if isinstance(_ep_project_id_raw, uuid.UUID)
            else ProjectRegistry.DEFAULT_PROJECT_ID
        )
        _ep_project_scope_raw: object = getattr(ep, "project_scope", None)
        _ep_project_scope: str = (
            str(_ep_project_scope_raw) if isinstance(_ep_project_scope_raw, str)
            else "project"
        )

        # Track this episode for the post-loop FSRS review (P18-002).
        consolidated_episodes.append(ep)

        for fd in candidates:
            _subj = fd.get("subject", "")
            _pred = fd.get("predicate", "")
            _obj = fd.get("object_val", "")

            content_key = make_content_key(
                subject=str(_subj),
                predicate=str(_pred),
                object_val=str(_obj),
                source_episode=uuid.UUID(str(_ep_id)) if isinstance(_ep_id, uuid.UUID) else uuid.uuid4(),
            )
            if await _fact_exists_by_key(session, content_key):
                skipped_exists += 1
                continue

            _fd_cls_raw = fd.get("classification")
            _fd_cls: str | None = str(_fd_cls_raw) if isinstance(_fd_cls_raw, str) else None
            fd_classification = fd.get("classification")
            highest_cls = highest_classification(_ep_cls, fd_classification)
            source_episode_id = _ep_id if isinstance(_ep_id, uuid.UUID) else uuid.uuid4()
            fact_type = fd.get("fact_type", "episodic_summary")
            confidence = fd.get("confidence", 0.5)
            fact_tags = fd.get("tags")

            fact = SemanticFacts(
                subject=str(_subj),
                predicate=str(_pred),
                object_val=str(_obj),
                fact_type=fact_type,
                confidence=confidence,
                source="consolidation",
                source_episode=source_episode_id,
                classification=highest_cls,
                tags=fact_tags,
                project_id=_ep_project_id,
                project_scope=_ep_project_scope,
            )
            session.add(fact)
            facts_created.append({
                "subject": str(_subj),
                "predicate": str(_pred),
                "object_val": str(_obj),
                "source_episode": str(source_episode_id),
                "classification": highest_cls,
            })

            consolidated += 1

    # ---- P18-002: Post-consolidation FSRS review (non-breaking) ----
    if fsrs_enabled and consolidated_episodes:
        try:
            from guinevere.memory.spaced_repetition import FSRSScheduler  # noqa: PLC0415
            from guinevere.memory.spaced_repetition import GRADE_GOOD  # noqa: PLC0415

            _fsrs_scheduler = FSRSScheduler()
            _fsrs_updated = 0
            _fsrs_failed = 0
            for _fsrs_ep in consolidated_episodes:
                try:
                    _fsrs_scheduler.update_episode_state(
                        _fsrs_ep,
                        grade=GRADE_GOOD,
                        now=now,
                    )
                    _fsrs_updated += 1
                except Exception as _fsrs_ep_exc:
                    _fsrs_failed += 1
                    logger.debug(
                        "fsrs_episode_update_failed",
                        extra={
                            "error": str(_fsrs_ep_exc),
                            "error_type": type(_fsrs_ep_exc).__name__,
                        },
                    )
            logger.info(
                "fsrs_post_consolidation_review",
                extra={
                    "episodes_updated": _fsrs_updated,
                    "episodes_failed": _fsrs_failed,
                    "fsrs_available": _fsrs_scheduler.available,
                },
            )
        except ImportError:
            logger.debug("fsrs_module_unavailable_skipping_post_consolidation")
        except Exception as _fsrs_exc:
            logger.warning(
                "fsrs_post_consolidation_failed",
                extra={
                    "error": str(_fsrs_exc),
                    "error_type": type(_fsrs_exc).__name__,
                    "episodes_attempted": len(consolidated_episodes),
                },
            )

    # ---- P16: Post-consolidation KG ingestion (non-breaking) ----
    if kg_ingestion_enabled and facts_created:
        try:
            from guinevere.knowledge_graph.repository import make_borrowed_factory  # noqa: PLC0415
            from guinevere.knowledge_graph.resolution.resolver import EntityResolver  # noqa: PLC0415
            from guinevere.knowledge_graph.extraction.entity_extractor import EntityExtractor  # noqa: PLC0415
            from guinevere.knowledge_graph.extraction.relation_extractor import RelationExtractor  # noqa: PLC0415
            from guinevere.knowledge_graph.consent.manager import ConsentManager  # noqa: PLC0415
            from guinevere.knowledge_graph.observability.metrics import KGMetrics  # noqa: PLC0415
            from guinevere.knowledge_graph.ingestion.pipeline import KGIngestionPipeline  # noqa: PLC0415

            _kg_factory = make_borrowed_factory(session)
            _kg_resolver = EntityResolver(_kg_factory)
            _kg_extractor = EntityExtractor(_kg_resolver)
            _kg_rel_extractor = RelationExtractor(_kg_extractor)
            _kg_consent = ConsentManager(_kg_factory)
            _kg_metrics = KGMetrics()
            kg_pipeline = KGIngestionPipeline(
                session_factory=_kg_factory,
                entity_extractor=_kg_extractor,
                entity_resolver=_kg_resolver,
                relation_extractor=_kg_rel_extractor,
                consent_manager=_kg_consent,
                metrics=_kg_metrics,
            )
            kg_count = await kg_pipeline.ingest_from_consolidation(facts_created)
            if kg_count > 0:
                logger.info("kg_post_consolidation_ingestion", extra={"facts_ingested": kg_count})
        except ImportError:
            logger.debug("kg_module_unavailable_skipping_post_consolidation")
        except Exception as _kg_exc:
            logger.warning(
                "kg_post_consolidation_failed",
                extra={"error": str(_kg_exc), "facts_attempted": len(facts_created)},
            )

    return ConsolidationResult(
        consolidated=consolidated,
        skipped_dnr=skipped_dnr,
        skipped_safe_word=skipped_safe_word,
        skipped_exists=skipped_exists,
        facts_created=facts_created,
    )


# ---------------------------------------------------------------------------
# Helpers — safe-word detection, fact extraction, classification, idempotency
# ---------------------------------------------------------------------------


def is_safe_word_record(ep: object) -> bool:
    """Return True if *ep* is a safe-word/crisis/formal-hold record.

    Checks ``tags``, ``episode_type``, ``title``, ``summary``, and ``source``
    for any of the ``SAFE_WORD_INDICATORS``.

    For ``summary`` and ``title`` (free-text fields), uses substring matching
    so that e.g. "distress signal received" matches indicator "distress".
    For ``tags``, ``episode_type``, and ``source`` (controlled values), uses
    exact token or string matching.
    """
    # Tags (list[str], tuple[str], str with comma-sep, or set[str]) — exact token
    tags_raw = getattr(ep, "tags", None)
    if tags_raw is not None:
        tags_iter: list[str] = []
        if isinstance(tags_raw, str):
            tags_iter = [t.strip().lower() for t in tags_raw.split(",")]
        elif isinstance(tags_raw, (list, tuple, set)):
            tags_text = f"{tags_raw}".lower()
            if any(indicator in tags_text for indicator in SAFE_WORD_INDICATORS):
                return True
        for tag in tags_iter:
            if tag in SAFE_WORD_INDICATORS:
                return True

    # Episode type — exact match
    ep_type = getattr(ep, "episode_type", None)
    if isinstance(ep_type, str) and ep_type.lower() in SAFE_WORD_INDICATORS:
        return True

    # Source — exact match
    source = getattr(ep, "source", None)
    if isinstance(source, str) and source.lower() in SAFE_WORD_INDICATORS:
        return True

    # Title — substring match (free-text field)
    title = getattr(ep, "title", None)
    if isinstance(title, str):
        title_lower = title.lower()
        for indicator in SAFE_WORD_INDICATORS:
            if indicator in title_lower:
                return True

    # Summary — substring match (free-text field)
    summary = getattr(ep, "summary", None)
    if isinstance(summary, str):
        summary_lower = summary.lower()
        for indicator in SAFE_WORD_INDICATORS:
            if indicator in summary_lower:
                return True

    return False


def _extract_facts_from_episode(ep: object) -> list[FactData]:
    """Extract semantic fact candidates from an episode.

    Produces:
    1. A primary ``summarizes`` fact from ``title`` + ``summary``.
    2. An ``insight_*`` fact for each key in ``key_insights``.
    3. A minimal fallback fact if neither title/summary/insights exist.
    """
    facts: list[FactData] = []

    title_raw = getattr(ep, "title", None)
    title = title_raw if isinstance(title_raw, str) else ""
    summary = getattr(ep, "summary", None)
    key_insights_raw = getattr(ep, "key_insights", None)
    key_insights: dict[str, str] = {}
    if isinstance(key_insights_raw, dict):
        key_insights_text = f"{key_insights_raw}"
        key_insights["summary"] = key_insights_text
    tags_raw = getattr(ep, "tags", None)
    ep_classification_raw = getattr(ep, "classification", RESTRICTED)
    ep_classification = (
        ep_classification_raw if isinstance(ep_classification_raw, str) else RESTRICTED
    )

    # Clean tags to list[str]
    if isinstance(tags_raw, str):
        tags_list = [tag_item.strip() for tag_item in tags_raw.split(",") if tag_item.strip()]
    elif isinstance(tags_raw, (list, tuple)):
        tags_list = [f"{tags_raw}"]
    else:
        tags_list = []

    # Primary summary fact
    summary_text = summary if isinstance(summary, str) else ""
    if title or summary_text:
        facts.append({
            "subject": title or f"episode_{getattr(ep, 'id', 'unknown')}",
            "predicate": "summarizes",
            "object_val": summary_text,
            "fact_type": "episodic_summary",
            "classification": ep_classification,
            "tags": tags_list,
            "confidence": 0.7,
        })

    # Key-insight facts
    for insight_key, insight_value in key_insights.items():
        if insight_key and insight_value.strip():
            facts.append({
                "subject": title or f"episode_{getattr(ep, 'id', 'unknown')}",
                "predicate": f"insight_{insight_key}",
                "object_val": insight_value,
                "fact_type": "key_insight",
                "classification": ep_classification,
                "tags": tags_list,
                "confidence": 0.6,
            })

    # Fallback if nothing else produced
    if not facts:
        ep_type = getattr(ep, "episode_type", "unknown")
        facts.append({
            "subject": title or f"episode_{getattr(ep, 'id', 'unknown')}",
            "predicate": "occurred",
            "object_val": ep_type,
            "fact_type": "episodic_summary",
            "classification": ep_classification,
            "tags": tags_list,
            "confidence": 0.5,
        })

    return facts


def make_content_key(
    subject: str,
    predicate: str,
    object_val: str,
    source_episode: uuid.UUID,
) -> str:
    """Create a deterministic SHA-256 key for fact deduplication.

    Combines ``subject | predicate | object_val | source_episode`` into a
    content-addressable hash.
    """
    raw = f"{subject}|{predicate}|{object_val}|{source_episode}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def _fact_exists_by_key(session: AsyncSessionProtocol, content_key: str) -> bool:
    """Return True if a semantic fact with the given content key exists.

    Iterates existing facts and compares their content keys.  This is an
    in-memory check suitable for app-layer and test usage.  A production
    deployment could add a ``content_hash`` column with a unique constraint
    for O(1) lookup.
    """
    stmt = select(SemanticFacts)
    exec_result = await session.execute(stmt)
    existing_facts = list(exec_result.scalars().all())
    for fact in existing_facts:
        fact_key = make_content_key(
            subject=str(getattr(fact, "subject", "")),
            predicate=str(getattr(fact, "predicate", "")),
            object_val=str(getattr(fact, "object_val", "")),
            source_episode=getattr(fact, "source_episode", None) or uuid.uuid4(),
        )
        if fact_key == content_key:
            return True
    return False


def highest_classification(*labels: str | None) -> str:
    """Return the highest (most restrictive) classification among labels.

    Order: Public(0) < Internal(1) < Restricted(2) < Confidential(3) <
    Critical(4).  ``None`` or unknown labels fail-closed as Critical.

    If no labels are provided, returns ``Restricted`` (the model default).
    """
    max_level = -1
    max_label: str = RESTRICTED
    for label in labels:
        if label is None:
            level = 5  # Unknown → fail-closed Critical+
        else:
            level = CLASSIFICATION_ORDER.get(label, 5)
        if level > max_level:
            max_level = level
            if label in CLASSIFICATION_ORDER:
                max_label = label
            else:
                max_label = CRITICAL  # Unknown label → Critical
    return max_label


# ---------------------------------------------------------------------------
# Stale pruning
# ---------------------------------------------------------------------------


async def prune_stale_facts(
    session: AsyncSessionProtocol,
    config: RetentionConfig | None = None,
) -> PruneResult:
    """Prune stale semantic facts based on configurable policy.

    Default behaviour (``mode="archive"``, ``dry_run=False``) transitions
    matching facts to ``deletion_state="archived"`` — a metadata-only change
    that preserves the row.  Hard delete requires explicit ``mode="delete"``.

    Parameters
    ----------
    session:
        An async SQLAlchemy session (or fake test session).
    config:
        Retention policy.  Defaults to ``RetentionConfig()``.

    Returns
    -------
    PruneResult
        Summary with ``pruned``, ``dry_run``, and ``mode``.
    """
    if config is None:
        config = RetentionConfig()

    stmt = select(SemanticFacts)
    exec_result = await session.execute(stmt)
    all_facts = list(exec_result.scalars().all())

    now = datetime.now(UTC)
    candidates: list[object] = []

    for fact in all_facts:
        # Skip protected categories
        fact_tags_raw = getattr(fact, "tags", None)
        if isinstance(fact_tags_raw, (list, tuple)):
            fact_tags_text = f"{fact_tags_raw}"
            if any(category in fact_tags_text for category in config.protected_categories):
                continue
        elif isinstance(fact_tags_raw, str):
            if any(cat in fact_tags_raw for cat in config.protected_categories):
                continue

        # Skip high-importance (confidence) facts
        confidence = getattr(fact, "confidence", None)
        if isinstance(confidence, (int, float)) and confidence >= config.protected_importance_floor:
            continue

        # Check age
        created_at = getattr(fact, "created_at", None)
        if isinstance(created_at, datetime):
            age_days = (now - created_at).days
            if age_days < config.max_age_days:
                continue

        candidates.append(fact)

    if config.dry_run:
        logger.info("dry_run_prune_candidates=%d", len(candidates))
        return PruneResult(pruned=0, dry_run=len(candidates), mode="dry_run")

    if config.mode == "delete":
        for fact in candidates:
            await session.delete(fact)
        logger.info("hard_deleted_facts=%d", len(candidates))
        return PruneResult(pruned=len(candidates), mode="delete")

    if config.mode == "soft_delete":
        for fact in candidates:
            setattr(fact, "deletion_state", "deleted")
        logger.info("soft_deleted_facts=%d", len(candidates))
        return PruneResult(pruned=len(candidates), mode="soft_delete")

    # Default: archive (metadata-only)
    for fact in candidates:
        setattr(fact, "deletion_state", "archived")
    logger.info("archived_facts=%d", len(candidates))
    return PruneResult(pruned=len(candidates), mode="archive")


# ---------------------------------------------------------------------------
# APScheduler v3 job wrapper
# ---------------------------------------------------------------------------


async def daily_consolidation_job(
    session_factory: Callable[[], AsyncSessionProtocol] | None = None,
) -> ConsolidationResult:
    """APScheduler job entry point for daily consolidation.

    Wraps ``consolidate_episodes_to_facts`` with metadata-only logging.
    Re-raises any exception after logging (no empty catch).

    Parameters
    ----------
    session_factory:
        Callable returning an async SQLAlchemy session.  When ``None``
        (e.g. no DB sessionmaker configured), logs a warning and returns early.

    Returns
    -------
    ConsolidationResult
        Summary (see ``consolidate_episodes_to_facts``).

    Raises
    ------
    Exception
        Re-raised after logging error metadata.
    """
    try:
        logger.info("consolidation_job_started", extra={"job_id": CONSOLIDATION_JOB_ID})

        if session_factory is None:
            logger.warning(
                "consolidation_job_no_session_factory",
                extra={
                    "job_id": CONSOLIDATION_JOB_ID,
                    "detail": "No session factory available; skipping consolidation",
                },
            )
            return ConsolidationResult()

        async with session_factory() as session:
            result = await consolidate_episodes_to_facts(session)

        logger.info(
            "consolidation_job_completed",
            extra={
                "job_id": CONSOLIDATION_JOB_ID,
                "consolidated": result.consolidated,
                "skipped_dnr": result.skipped_dnr,
                "skipped_safe_word": result.skipped_safe_word,
                "skipped_exists": result.skipped_exists,
            },
        )
        return result

    except (RuntimeError, ValueError, TypeError, OSError, AttributeError):
        logger.error(
            "consolidation_job_failed",
            extra={"job_id": CONSOLIDATION_JOB_ID},
            exc_info=True,
        )
        raise


# ---------------------------------------------------------------------------
# Registration helper
# ---------------------------------------------------------------------------


async def register_consolidation_job(
    scheduler: SchedulerProtocol,
    session_factory: Callable[[], AsyncSessionProtocol] | None = None,
) -> None:
    """Register the daily consolidation job on an APScheduler v3 scheduler.

    The job is registered with:
    - ID: ``daily_consolidation``
    - Trigger: ``CronTrigger(hour=3, minute=0, timezone='Asia/Bangkok')``
    - ``replace_existing=True`` (safe for re-registration)
    - ``misfire_grace_time=3600`` (1 hour)

    Parameters
    ----------
    scheduler:
        An active APScheduler v3 ``AsyncIOScheduler`` instance.
    session_factory:
        Optional async session factory.  Passed as a keyword argument to the
        job function.  May be ``None`` when no DB sessionmaker is available
        (the job will log a warning and skip work).
    """
    trigger = "cron"

    _ = scheduler.add_job(
        daily_consolidation_job,
        trigger=trigger,
        id=CONSOLIDATION_JOB_ID,
        kwargs={"session_factory": session_factory},
        name="Daily Episodic-to-Semantic Consolidation",
        replace_existing=True,
        misfire_grace_time=3600,
        hour=CONSOLIDATION_HOUR,
        minute=CONSOLIDATION_MINUTE,
        timezone=TZ_BANGKOK,
    )

    logger.info(
        "consolidation_job_registered",
        extra={
            "job_id": CONSOLIDATION_JOB_ID,
            "trigger": str(trigger),
            "timezone": TZ_BANGKOK,
        },
    )


# ---------------------------------------------------------------------------
# P18-002: 6-hourly FSRS decay sweep + active forgetting
# ---------------------------------------------------------------------------


@final
class DecaySweepResult:
    """Typed result from :func:`decay_sweep_job`."""

    episodes_reviewed: int
    episodes_archived: int
    errors: int

    def __init__(
        self,
        episodes_reviewed: int = 0,
        episodes_archived: int = 0,
        errors: int = 0,
    ) -> None:
        self.episodes_reviewed = episodes_reviewed
        self.episodes_archived = episodes_archived
        self.errors = errors

    def to_dict(self) -> dict[str, int]:
        return {
            "episodes_reviewed": self.episodes_reviewed,
            "episodes_archived": self.episodes_archived,
            "errors": self.errors,
        }


async def decay_sweep_job(
    session_factory: Callable[[], AsyncSessionProtocol] | None = None,
    fsrs_enabled: bool = True,
) -> DecaySweepResult:
    """APScheduler job: 6-hourly FSRS decay sweep + active forgetting.

    Behaviour:

    1. Lazy-import :class:`FSRSScheduler` (no-op if ``fsrs`` is missing).
    2. Query all non-DNR episodes that have ``next_review_at <= now``
       (or never reviewed) - these are due for re-evaluation.
    3. Run an FSRS review (``grade=Good`` for never-reviewed or due
       episodes) and persist the new state via
       :meth:`FSRSScheduler.update_episode_state`.
    4. For episodes older than :data:`ACTIVE_FORGETTING_GRACE_DAYS`
       whose predicted retrievability is below
       :data:`ACTIVE_FORGETTING_THRESHOLD`, mark them
       ``deletion_state='archived'`` (metadata-only; never hard delete).

    The sweep is **non-breaking**: if FSRS or the DB session is
    unavailable, the job logs a warning and returns an empty result.

    Parameters
    ----------
    session_factory:
        Callable returning an async SQLAlchemy session.  ``None`` means
        the job skips work (and logs a warning).
    fsrs_enabled:
        When ``False``, the sweep skips the FSRS review step and only
        runs the active-forgetting archive pass.

    Returns
    -------
    DecaySweepResult
        Counts of episodes reviewed, archived, and any per-episode errors.
    """
    result = DecaySweepResult()

    if session_factory is None:
        logger.warning(
            "decay_sweep_no_session_factory",
            extra={"job_id": DECAY_SWEEP_JOB_ID, "detail": "No session factory; skipping sweep"},
        )
        return result

    now = datetime.now(UTC)

    scheduler_obj: Any = None
    if fsrs_enabled:
        try:
            from guinevere.memory.spaced_repetition import FSRSScheduler  # noqa: PLC0415
            from guinevere.memory.spaced_repetition import GRADE_GOOD  # noqa: PLC0415

            scheduler_obj = FSRSScheduler()
            _ = GRADE_GOOD  # type-guard: constant import check
        except ImportError:
            logger.debug("fsrs_module_unavailable_decay_sweep_no_op")
            scheduler_obj = None
        except Exception as _fsrs_init_exc:
            logger.warning(
                "fsrs_decay_sweep_init_failed",
                extra={"error": str(_fsrs_init_exc), "error_type": type(_fsrs_init_exc).__name__},
            )
            scheduler_obj = None

    try:
        async with session_factory() as session:
            stmt = select(Episodes).where(Episodes.do_not_recall.is_(False))  # noqa: E712
            exec_result = await session.execute(stmt)
            all_episodes = list(exec_result.scalars().all())

            for ep in all_episodes:
                next_review_at = getattr(ep, "next_review_at", None)
                fsrs_state = getattr(ep, "fsrs_state", None)
                due_for_review = bool(
                    next_review_at is None
                    or (isinstance(next_review_at, datetime) and next_review_at <= now)
                    or not fsrs_state
                )

                # P18-002: FSRS review pass.
                if fsrs_enabled and scheduler_obj is not None and due_for_review:
                    try:
                        scheduler_obj.update_episode_state(ep, grade=GRADE_GOOD, now=now)
                        result.episodes_reviewed += 1
                    except Exception as _ep_exc:
                        result.errors += 1
                        logger.debug(
                            "fsrs_decay_review_failed",
                            extra={
                                "error": str(_ep_exc),
                                "error_type": type(_ep_exc).__name__,
                            },
                        )

                # P18-002: Active forgetting pass.
                try:
                    retrievability = getattr(ep, "retrievability", None)
                    created_at = getattr(ep, "created_at", None) or getattr(
                        ep, "started_at", None
                    )
                    age_days: int | None = None
                    if isinstance(created_at, datetime):
                        age_days = max(0, (now - created_at).days)

                    ep_importance = getattr(ep, "importance", None)
                    if (
                        isinstance(retrievability, (int, float))
                        and retrievability < ACTIVE_FORGETTING_THRESHOLD
                        and age_days is not None
                        and age_days > ACTIVE_FORGETTING_GRACE_DAYS
                        and (ep_importance is None or ep_importance < ACTIVE_FORGETTING_IMPORTANCE_FLOOR)
                    ):
                        if ACTIVE_FORGETTING_DEFAULT_MODE == "archive":
                            setattr(ep, "deletion_state", "archived")
                            result.episodes_archived += 1
                        else:
                            # Future modes ('soft_delete', 'delete') reserved.
                            logger.debug(
                                "active_forgetting_mode_unhandled",
                                extra={"mode": ACTIVE_FORGETTING_DEFAULT_MODE},
                            )
                except Exception as _archive_exc:
                    result.errors += 1
                    logger.debug(
                        "active_forgetting_check_failed",
                        extra={
                            "error": str(_archive_exc),
                            "error_type": type(_archive_exc).__name__,
                        },
                    )

        logger.info(
            "decay_sweep_job_completed",
            extra={
                "job_id": DECAY_SWEEP_JOB_ID,
                "episodes_reviewed": result.episodes_reviewed,
                "episodes_archived": result.episodes_archived,
                "errors": result.errors,
                "fsrs_enabled": fsrs_enabled,
                "fsrs_available": getattr(scheduler_obj, "available", False),
            },
        )
        return result

    except (RuntimeError, ValueError, TypeError, OSError, AttributeError):
        logger.error(
            "decay_sweep_job_failed",
            extra={"job_id": DECAY_SWEEP_JOB_ID},
            exc_info=True,
        )
        raise


# ---------------------------------------------------------------------------
# P18-002: Decay sweep APScheduler registration
# ---------------------------------------------------------------------------


async def register_decay_job(
    scheduler: SchedulerProtocol,
    session_factory: Callable[[], AsyncSessionProtocol] | None = None,
) -> None:
    """Register the 6-hourly decay sweep on an APScheduler v3 scheduler.

    Trigger: ``interval`` with ``hours=6``, anchored at the start of each
    6-hour block.  This is *additional* to the daily 03:00 ICT consolidation
    cron - the daily consolidation continues to run unchanged.

    Parameters
    ----------
    scheduler:
        An active APScheduler v3 ``AsyncIOScheduler`` instance.
    session_factory:
        Optional async session factory.  ``None`` means the job will log
        a warning and skip work when it fires.
    """
    trigger = "interval"

    _ = scheduler.add_job(
        decay_sweep_job,
        trigger=trigger,
        id=DECAY_SWEEP_JOB_ID,
        kwargs={"session_factory": session_factory},
        name="P18 FSRS Decay Sweep + Active Forgetting",
        replace_existing=True,
        misfire_grace_time=1800,
        hours=DECAY_SWEEP_INTERVAL_HOURS,
        minute=DECAY_SWEEP_MINUTE,
    )

    logger.info(
        "decay_sweep_job_registered",
        extra={
            "job_id": DECAY_SWEEP_JOB_ID,
            "trigger": str(trigger),
            "interval_hours": DECAY_SWEEP_INTERVAL_HOURS,
        },
    )
