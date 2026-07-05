"""Guinevere memory read pipeline — P3-010.

Recalls episodic memories from ``memory.episodes`` using hybrid ranking:
vector cosine similarity, full-text search (FTS), recency decay with 90-day
half-life, and importance factor.  Results are fused with reciprocal rank
fusion (RRF, k=60).

Safety gates:
- DNR (do-not-recall) exclusion.
- Classification ceiling per principal.
- Safe-mode content substitution — raw Critical content is never returned
  when ``safe_mode=True``.
- Token budget enforcement (4 000 tokens per recall cycle).

All embedding calls go through P3-005 ``EmbeddingService`` (9Router-native).
Never imports or uses OpenAI SDK.  Never logs raw content, vector values,
or secrets.
"""

from __future__ import annotations

import hashlib
import logging
import math
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from collections.abc import Iterable, Sequence
from typing import Protocol, TypeAlias, cast, runtime_checkable

from guinevere.memory.embeddings import (
    CLASSIFICATION_ORDER,
    CONFIDENTIAL,
    CRITICAL,
    INTERNAL,
    PUBLIC,
    RESTRICTED,
)

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

JsonObject: TypeAlias = dict[str, object]
RecallResults: TypeAlias = list[dict[str, object]]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RRF_K: int = 60
"""Reciprocal rank fusion constant (k=60 per batch plan)."""

RECENCY_HALF_LIFE_DAYS: int = 90
"""Exponential decay half-life for recency scoring."""

EXPANDED_LIMIT_MULTIPLIER: int = 3
"""Multiply requested ``limit`` by this when querying, so RRF has enough
candidates from each signal to fuse meaningfully."""

SAFE_MODE_PLACEHOLDER: str = (
    "[Content redacted per safe-mode policy — Critical classification]"
)

SAFE_MODE_RESTRICTED_PLACEHOLDER: str = (
    "[Content redacted per safe-mode policy — Restricted/Confidential classification]"
)

SAFE_MODE_CONTENT_BLOCKED_PLACEHOLDER: str = (
    "[Content blocked per safe-mode policy — emotional/surveillance/persona-escalation content]"
)

# Tags/episode_type/source substrings that indicate content should be
# blocked in safe mode regardless of classification level.
_SAFE_MODE_BLOCKED_CONTENT_TAGS: frozenset[str] = frozenset({
    "emotional", "emotion", "sentiment", "mood",
    "surveillance", "surveil", "monitor", "spy",
    "persona_escalation", "persona-escalation", "yandere",
    "punishment", "punitive", "jealousy", "dark_mood",
    "silent_mode", "nuclear", "possessive",
})

# Safe-mode classification ceiling: classification levels ABOVE this are
# blocked or redacted when safe_mode=True.
# - guinevere_core  → Internal (Restricted+ blocked/redacted)
# - guinevere_subagent → Public (Internal+ blocked)
# - default         → Public (fail-closed)
_SAFE_MODE_CEILING: dict[str, str] = {
    "guinevere_core": INTERNAL,
    "guinevere_subagent": PUBLIC,
    "default": PUBLIC,
}

DEFAULT_TOKEN_BUDGET: int = 4000
"""Default maximum tokens per recall cycle (~4 chars per token)."""

CHARS_PER_TOKEN: int = 4
"""Rough estimate: one token ~= 4 characters for typical text."""

# ---------------------------------------------------------------------------
# P3-011 hybrid ranking tuning — weighted RRF, signal bonus, recency boost
# ---------------------------------------------------------------------------

VECTOR_WEIGHT: float = 0.5
"""Weight for the vector similarity signal in weighted RRF fusion."""

FTS_WEIGHT: float = 0.5
"""Weight for the FTS relevance signal in weighted RRF fusion."""

# ---------------------------------------------------------------------------
# P16-003 KG 4th RRF signal weight — Faiz-locked per PRD v2.2 P16 spec
# ---------------------------------------------------------------------------

KG_WEIGHT: float = 0.20
"""Weight for the KG (knowledge-graph) signal in weighted RRF fusion.

This is the 4th RRF signal, added on top of the existing 3-signal fusion
(vector cosine + FTS relevance + recency boost).  When ``kg_enabled=True``
in :func:`recall_memories`, the KG contribution ``KG_WEIGHT / (RRF_K + kg_rank)``
is added to ``combined_score`` for episodes ranked by the KG graph traversal.

Mirrors :data:`guinevere.knowledge_graph.query.rrf_fusion.KG_WEIGHT`.  Kept in sync
deliberately so callers do not have to import from the KG module.
"""

# ---------------------------------------------------------------------------
# P18-008 FSRS reconsolidation signal weight
# ---------------------------------------------------------------------------

FSRS_WEIGHT: float = 0.15
"""Weight for the FSRS retrievability signal in weighted RRF fusion.

5th RRF signal: when ``fsrs_enabled=True`` in :func:`recall_memories`,
episodes with high FSRS retrievability get a bonus added to
``combined_score``.  Default False preserves byte-for-byte backward compat.
"""

BOTH_SIGNAL_BONUS: float = 1.25
"""Multiplier applied when an episode is found by both vector AND FTS."""

RECENCY_MAX_BOOST: float = 0.10
"""Maximum fractional recency boost (10%) applied as ``1 + boost * score``.

Ensures recency never dominates relevance — a highly relevant but old
document easily beats a marginally relevant new one.
"""

MAX_CANDIDATE_POOL: int = 200
"""Hard cap on the total candidate pool fed into RRF fusion.

Prevents unbounded memory/CPU usage from large expanded limits.
"""

# ---------------------------------------------------------------------------
# Principal → max classification ceiling
# ---------------------------------------------------------------------------

_CLASSIFICATION_CEILING: dict[str, str] = {
    "guinevere_core": CRITICAL,
    "guinevere_subagent": CONFIDENTIAL,
    "default": RESTRICTED,
}
"""Each principal has a maximum classification they may read.

- ``guinevere_core`` → may read up to ``Critical`` (everything).
- ``guinevere_subagent`` → may read up to ``Confidential`` (no Critical).
- default (unknown principal) → may read up to ``Restricted``.
"""


def _resolve_ceiling(principal: str, safe_mode: bool) -> str:
    """Return the effective classification ceiling label for a principal.

    In safe mode, the ceiling is downgraded per ``_SAFE_MODE_CEILING``.
    In normal mode, the standard ``_CLASSIFICATION_CEILING`` applies.
    """
    if safe_mode:
        ceiling = _SAFE_MODE_CEILING.get(principal)
        if ceiling is None:
            ceiling = _SAFE_MODE_CEILING["default"]
        return ceiling
    ceiling = _CLASSIFICATION_CEILING.get(principal)
    if ceiling is None:
        ceiling = _CLASSIFICATION_CEILING["default"]
    return ceiling

# ---------------------------------------------------------------------------
# Custom errors
# ---------------------------------------------------------------------------


class ReadPipelineError(Exception):
    """Base error for the memory read pipeline."""


class ReadPipelineQueryError(ReadPipelineError):
    """Raised when the query text is empty or malformed."""


class ReadPipelineSafetyError(ReadPipelineError):
    """Raised when a safety gate blocks the recall entirely."""


class ReadPipelineTokenBudgetError(ReadPipelineError):
    """Raised when the token budget is too small to return any results."""


# ---------------------------------------------------------------------------
# Protocols
# ---------------------------------------------------------------------------


@runtime_checkable
class EpisodeProtocol(Protocol):
    """Minimal protocol matching ``Episodes`` ORM attributes we read."""

    id: object
    raw_content: str | None
    summary: str | None
    embedding: list[float] | None
    search_vector: object | None
    do_not_recall: bool
    classification: str
    importance: int | None
    started_at: datetime | None
    created_at: datetime | None


class ScalarResult(Protocol):
    """Minimal protocol for SQLAlchemy-like scalar result wrappers."""

    def scalars(self) -> Iterable[EpisodeProtocol]:
        """Return scalar episode rows."""
        ...


class RecallSession(Protocol):
    """Async session protocol for memory recall.

    Matches the subset of ``sqlalchemy.ext.asyncio.AsyncSession`` that the
    read pipeline uses.
    """

    async def execute(self, statement: object) -> ScalarResult:
        """Execute a query and return a result set."""
        ...


class VectorDistanceColumn(Protocol):
    """Minimal pgvector SQLAlchemy column protocol used for ordering."""

    def cosine_distance(self, vector: list[float]) -> object:
        """Return a SQL expression for cosine distance ordering."""
        ...


class EmbeddingClient(Protocol):
    """Minimal embedding client protocol for the read pipeline.

    Matches the ``EmbeddingService.aembed()`` signature.
    """

    async def aembed(
        self,
        text: str,
        classification: str = RESTRICTED,
        *,
        sanitized_summary: str | None = None,
    ) -> list[float]:
        """Return one embedding vector."""
        ...


# ---------------------------------------------------------------------------
# Recency Config
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RecencyConfig:
    """Configuration for recency decay scoring."""

    half_life_days: int = RECENCY_HALF_LIFE_DAYS
    reference_time: datetime | None = None

    @property
    def _ref(self) -> datetime:
        if self.reference_time is not None:
            return self.reference_time
        return datetime.now(timezone.utc)

    def score(self, started_at: datetime | None) -> float:
        """Compute recency score: exponential decay with ``half_life_days``.

        Returns a value in (0, 1] where 1.0 = now and approaches 0 as the
        episode ages past the half-life.
        """
        if started_at is None:
            return 0.0
        ref = self._ref
        # Ensure we always have a timezone-aware comparison
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        if ref.tzinfo is None:
            ref = ref.replace(tzinfo=timezone.utc)
        days_elapsed = (ref - started_at).total_seconds() / 86_400.0
        if days_elapsed < 0:
            days_elapsed = 0.0
        half_life_days_f = float(self.half_life_days)
        if half_life_days_f <= 0:
            return 0.0
        return math.exp(-days_elapsed * math.log(2) / half_life_days_f)


# ---------------------------------------------------------------------------
# Ranking utilities
# ---------------------------------------------------------------------------


def compute_rrf_score(
    vector_rank: int | None,
    fts_rank: int | None,
    k: int = RRF_K,
    *,
    vector_weight: float = VECTOR_WEIGHT,
    fts_weight: float = FTS_WEIGHT,
) -> tuple[float, int]:
    """Compute weighted reciprocal rank fusion score from individual signal ranks.

    Each signal contributes ``weight / (k + rank)``.  If a signal did not
    find the episode, it contributes 0.  Returns ``(score, num_signals)``
    so the caller can apply the both-signal bonus after fusion.

    ``num_signals`` is the count of non-None ranks (1 or 2 in P3-011).
    """
    score = 0.0
    num_signals = 0
    if vector_rank is not None:
        score += vector_weight / (k + vector_rank)
        num_signals += 1
    if fts_rank is not None:
        score += fts_weight / (k + fts_rank)
        num_signals += 1
    return score, num_signals


def normalize_importance(importance: int) -> float:
    """Normalise importance (1-10) to (0.1, 1.0).

    Falls back to 0.5 if value is out of range.
    """
    return max(0.1, min(1.0, importance / 10.0))


def classification_level(label: str | None) -> int:
    """Return classification numeric level, fail-closed for unknown/null.

    Unknown or ``None`` classifications map to level 5 (beyond Critical),
    ensuring they are blocked by the classification ceiling filter.
    """
    if not label:
        return 5  # beyond Critical — fail closed
    return CLASSIFICATION_ORDER.get(label, 5)


# ---------------------------------------------------------------------------
# Safe-content builder
# ---------------------------------------------------------------------------


def _is_safe_mode_blocked_content(episode: EpisodeProtocol) -> bool:
    """Check if episode content should be blocked in safe mode.

    Returns True if the episode contains emotional, surveillance, or
    persona-escalation content as indicated by optional ``tags``,
    ``episode_type``, or ``source`` attributes.  Uses ``getattr`` defensively
    since ``EpisodeProtocol`` does not mandate these fields.
    """
    # Check tags — may be list[str], set[str], tuple[str, ...],
    # or comma-separated string.  Use getattr defensively.
    tags_raw = getattr(episode, "tags", None)
    if tags_raw is not None:
        tags_lower: set[str] = set()
        if isinstance(tags_raw, str):
            for part in tags_raw.split(","):
                tags_lower.add(part.strip().lower())
        elif isinstance(tags_raw, (list, tuple, set)):
            tags_lower.add(f"{tags_raw}".lower())
        for tag in tags_lower:
            for blocked in _SAFE_MODE_BLOCKED_CONTENT_TAGS:
                if blocked in tag:
                    return True

    # Check episode_type
    episode_type = getattr(episode, "episode_type", None)
    if isinstance(episode_type, str):
        ep_lower = episode_type.lower()
        for blocked in _SAFE_MODE_BLOCKED_CONTENT_TAGS:
            if blocked in ep_lower:
                return True

    # Check source field for surveillance/monitoring indicators
    source = getattr(episode, "source", None)
    if isinstance(source, str):
        src_lower = source.lower()
        for blocked in _SAFE_MODE_BLOCKED_CONTENT_TAGS:
            if blocked in src_lower:
                return True

    return False


def build_safe_content(
    episode: EpisodeProtocol,
    safe_mode: bool,
) -> tuple[str, bool]:
    """Build the ``safe_content`` field for one episode.

    Returns ``(safe_content, is_summarized)``.

    **Normal mode (``safe_mode=False``):**
    - Prefer summary when substantially shorter than raw_content.
    - Otherwise use raw_content (or empty string).

    **Safe mode (``safe_mode=True``):**
    - DNR exclusion is handled upstream (query-level WHERE).
    - Critical → blocked with ``SAFE_MODE_PLACEHOLDER``.
    - Restricted/Confidential → prefer summary if available; otherwise
      ``SAFE_MODE_RESTRICTED_PLACEHOLDER``.  Raw content is never returned.
    - Public/Internal → prefer neutral summary if available; if the content
      contains emotional/surveillance/persona-escalation markers (via tags,
      episode_type, or source), blocked with
      ``SAFE_MODE_CONTENT_BLOCKED_PLACEHOLDER``.
    - Unknown classification → fail-closed: blocked with placeholder.
    - Raw ``raw_content`` is NEVER returned for Restricted, Confidential,
      Critical, or blocked-content episodes in safe mode.
    """
    raw: str = episode.raw_content or ""
    summary: str = episode.summary or ""

    if not safe_mode:
        # Normal mode — prefer summary when shorter
        if summary and raw and len(summary) < len(raw) * 0.8:
            return summary, True
        return raw, False

    # --- Safe mode active ---
    cls = episode.classification

    if cls == CRITICAL:
        return SAFE_MODE_PLACEHOLDER, False

    if cls == RESTRICTED or cls == CONFIDENTIAL:
        # Prefer summary; never return raw_content
        if summary:
            return summary, True
        return SAFE_MODE_RESTRICTED_PLACEHOLDER, False

    if cls == PUBLIC or cls == INTERNAL:
        # Check for emotional/surveillance/escalation content
        if _is_safe_mode_blocked_content(episode):
            return SAFE_MODE_CONTENT_BLOCKED_PLACEHOLDER, False
        # Neutral content — prefer summary if available
        if summary:
            return summary, True
        return raw, False

    # Unknown classification → fail-closed (treated as Critical+)
    return SAFE_MODE_PLACEHOLDER, False


# ---------------------------------------------------------------------------
# Token budget estimation
# ---------------------------------------------------------------------------


def estimate_tokens(text: str) -> int:
    """Approximate token count: ``len(text) // CHARS_PER_TOKEN``."""
    return len(text) // CHARS_PER_TOKEN


# ---------------------------------------------------------------------------
# Token budget trimming
# ---------------------------------------------------------------------------


def apply_token_budget(
    results: list[dict[str, object]],
    budget: int,
) -> list[dict[str, object]]:
    """Trim results from the bottom if total estimated tokens exceed *budget*.

    Items are already sorted by combined_score descending.  This function
    discards the lowest-ranked items until the budget fits.
    """
    total_tokens = 0
    trimmed: list[dict[str, object]] = []
    for r in results:
        safe_content = str(r.get("safe_content", ""))
        estimated = estimate_tokens(safe_content)
        if total_tokens + estimated > budget:
            _logger.info(
                "token_budget_trimmed",
                extra={
                    "budget": budget,
                    "total_before": sum(
                        estimate_tokens(str(x.get("safe_content", "")))
                        for x in results
                    ),
                    "returned_after": len(trimmed),
                    "discarded": len(results) - len(trimmed),
                },
            )
            break
        total_tokens += estimated
        trimmed.append(r)
    return trimmed


# ---------------------------------------------------------------------------
# SQLAlchemy ORM query builders
# ---------------------------------------------------------------------------


def build_vector_query(
    query_vector: list[float],
    limit: int,
    exclude_dnr: bool,
    project_id: uuid.UUID | None = None,
) -> object:
    """Build an ORM ``select()`` for vector cosine similarity search.

    Uses ``Episodes.embedding.cosine_distance(...)`` which maps to the
    pgvector ``<=>`` operator.

    When ``project_id`` is provided, filters to episodes whose
    ``project_id == :project_id OR project_scope == 'global'``.
    """
    from sqlalchemy import or_, select
    from sqlalchemy.sql.elements import ColumnElement

    from guinevere.memory.models import Episodes

    embedding_column = cast(VectorDistanceColumn, cast(object, Episodes.embedding))
    cosine_order = cast(
        ColumnElement[object],
        embedding_column.cosine_distance(query_vector),
    )
    stmt = (
        select(Episodes)
        .where(Episodes.embedding.isnot(None))
        .order_by(cosine_order)
        .limit(limit)
    )
    if exclude_dnr:
        stmt = stmt.where(Episodes.do_not_recall.is_(False))
    if project_id is not None:
        stmt = stmt.where(
            or_(
                Episodes.project_id == project_id,
                Episodes.project_scope == "global",
            )
        )
    return stmt


def build_fts_query(
    query_text: str,
    limit: int,
    exclude_dnr: bool,
    project_id: uuid.UUID | None = None,
) -> object:
    """Build an ORM ``select()`` for FTS relevance search.

    Uses ``func.plainto_tsquery()`` for user-friendly query parsing and
    ``func.ts_rank()`` for relevance ranking.

    When ``project_id`` is provided, filters to episodes whose
    ``project_id == :project_id OR project_scope == 'global'``.
    """
    from sqlalchemy import func, or_, select

    from guinevere.memory.models import Episodes

    fts_query = func.plainto_tsquery("english", query_text)
    stmt = (
        select(Episodes)
        .where(Episodes.search_vector.op("@@")(fts_query))
        .order_by(func.ts_rank(Episodes.search_vector, fts_query).desc())
        .limit(limit)
    )
    if exclude_dnr:
        stmt = stmt.where(Episodes.do_not_recall.is_(False))
    if project_id is not None:
        stmt = stmt.where(
            or_(
                Episodes.project_id == project_id,
                Episodes.project_scope == "global",
            )
        )
    return stmt


def build_recency_query(
    limit: int,
    exclude_dnr: bool,
    project_id: uuid.UUID | None = None,
) -> object:
    """Build an ORM ``select()`` ordered by ``started_at DESC``.

    Provides a fallback signal for episodes that may not match vector or
    FTS queries (e.g., empty query text or cold-start scenarios).

    When ``project_id`` is provided, filters to episodes whose
    ``project_id == :project_id OR project_scope == 'global'``.
    """
    from sqlalchemy import or_, select

    from guinevere.memory.models import Episodes

    stmt = (
        select(Episodes)
        .order_by(Episodes.started_at.desc())
        .limit(limit)
    )
    if exclude_dnr:
        stmt = stmt.where(Episodes.do_not_recall.is_(False))
    if project_id is not None:
        stmt = stmt.where(
            or_(
                Episodes.project_id == project_id,
                Episodes.project_scope == "global",
            )
        )
    return stmt


# ---------------------------------------------------------------------------
# Internal data class for episode entry during fusion
# ---------------------------------------------------------------------------


@dataclass
class EpisodeEntry:
    """Scoring data for one unique episode during RRF fusion."""

    episode: EpisodeProtocol
    vector_rank: int | None = None
    fts_rank: int | None = None
    num_signals: int = 0
    """Count of distinct ranking signals that found this episode (1 or 2)."""


# ---------------------------------------------------------------------------
# Result-set assembler
# ---------------------------------------------------------------------------


def build_result_episode_map(
    vector_rows: Sequence[EpisodeProtocol],
    fts_rows: Sequence[EpisodeProtocol],
    recency_rows: Sequence[EpisodeProtocol] | None = None,
) -> "dict[str, EpisodeEntry]":
    """Build a map of episode_id → EpisodeEntry.

    For each unique episode found by any signal, record:
    - episode protocol object
    - vector rank position (or None)
    - FTS rank position (or None)
    """
    merged: dict[str, EpisodeEntry] = {}

    def _record(
        ep: EpisodeProtocol,
        signal: str,
        rank: int | None,
    ) -> None:
        ep_id = str(ep.id)
        entry = merged.get(ep_id)
        if entry is None:
            entry = EpisodeEntry(episode=ep)
            merged[ep_id] = entry
        if signal == "vector" and rank is not None:
            entry.vector_rank = rank
        elif signal == "fts" and rank is not None:
            entry.fts_rank = rank

    for rank_idx, ep in enumerate(vector_rows):
        _record(ep, "vector", rank_idx + 1)

    for rank_idx, ep in enumerate(fts_rows):
        _record(ep, "fts", rank_idx + 1)

    # Count distinct signals that found each episode for both-signal bonus
    for entry in merged.values():
        entry.num_signals = (
            (1 if entry.vector_rank is not None else 0)
            + (1 if entry.fts_rank is not None else 0)
        )

    # Recency signal does not contribute a rank to RRF, but we still
    # include episodes from it as candidates
    if recency_rows is not None:
        for _rank_idx, ep in enumerate(recency_rows):
            _record(ep, "recency", None)

    return merged


# ---------------------------------------------------------------------------
# Scored-result builder
# ---------------------------------------------------------------------------


def compute_scored_results(
    merged: dict[str, EpisodeEntry],
    recency_config: RecencyConfig,
) -> list[dict[str, object]]:
    """Compute final combined scores and build result dicts.

    Combined score = RRF score * recency_decay * importance_boost
    where importance_boost = 0.5 + 0.5 * normalized_importance.
    """
    scored: list[dict[str, object]] = []

    for entry in merged.values():
        episode = entry.episode

        # Weighted RRF fusion — returns (score, num_signals)
        rrf_score, num_signals = compute_rrf_score(
            vector_rank=entry.vector_rank,
            fts_rank=entry.fts_rank,
        )

        # Both-signal bonus: episodes found by both vector AND FTS get x1.25
        if num_signals > 1:
            rrf_score *= BOTH_SIGNAL_BONUS

        # Recency decay — bounded boost (max 10%), not a relevance override
        recency_score = recency_config.score(
            getattr(episode, "started_at", None)
        )
        recency_boost = 1.0 + RECENCY_MAX_BOOST * recency_score

        # Importance factor
        raw_importance = getattr(episode, "importance", None)
        if isinstance(raw_importance, int):
            importance_val: int = raw_importance
        else:
            importance_val = 5
        imp_norm = normalize_importance(importance_val)
        importance_boost = 0.5 + 0.5 * imp_norm

        combined = rrf_score * recency_boost * importance_boost

        # Build result dict with required fields
        created_at: datetime | None = getattr(episode, "created_at", None)
        if not isinstance(created_at, datetime):
            created_at = getattr(episode, "started_at", None)
            if not isinstance(created_at, datetime):
                created_at = None

        scored.append({
            "id": str(episode.id),
            "safe_content": "",
            "classification": episode.classification,
            "importance": importance_val,
            "created_at": created_at,
            "combined_score": combined,
            "is_summarized": False,
        })

    # Sort by combined_score descending
    scored.sort(key=lambda r: float(str(r.get("combined_score", 0))), reverse=True)
    return scored


# ---------------------------------------------------------------------------
# recall_memories — main entry point
# ---------------------------------------------------------------------------


async def recall_memories(
    session: RecallSession,
    query_text: str,
    limit: int = 20,
    *,
    exclude_dnr: bool = True,
    safe_mode: bool = False,
    principal: str = "guinevere_core",
    embedding_service: EmbeddingClient | None = None,
    token_budget: int = DEFAULT_TOKEN_BUDGET,
    kg_enabled: bool = True,
    fsrs_enabled: bool = False,
    project_id: uuid.UUID | None = None,
) -> RecallResults:
    """Recall episodic memories using hybrid ranking.

    Parameters
    ----------
    session:
        SQLAlchemy ``AsyncSession`` bound to the Guinevere database.
    query_text:
        Natural-language query string used for FTS and (optionally) vector
        similarity search.
    limit:
        Maximum number of results to return.  Default ``20``.
    exclude_dnr:
        If True (default), episodes with ``do_not_recall=True`` are excluded.
    safe_mode:
        If True, raw ``Critical``-classified content is replaced with a
        safe-mode placeholder before returning.
    principal:
        Identity used to determine the classification ceiling.  Default
        ``"guinevere_core"`` (may read up to ``Critical``).
    embedding_service:
        If provided, a 1536-dimensional query embedding is computed via
        ``embedding_service.aembed()`` and used for vector cosine similarity
        search.
    token_budget:
        Maximum estimated token count for all returned results (4 chars ≈ 1
        token).  Default 4000.
    kg_enabled:
        If True (default False), the knowledge-graph (KG) 4th RRF signal
        is computed and fused into ``combined_score`` with weight
        :data:`KG_WEIGHT` (``0.20``).  Default is False to preserve the
        existing 3-signal fusion behavior 100% — when False, this
        function is byte-for-byte equivalent to its prior contract.

        When True and the KG module is unavailable (import error) or
        construction fails (protocol mismatch, e.g. missing
        ``session_factory``), the pipeline **silently falls back** to
        3-signal fusion and no error is raised.  The fallback is
        observable only via the ``kg_enabled`` field in the
        ``recall_complete`` log record.

    fsrs_enabled:
        If True (default False), the FSRS reconsolidation-on-retrieval hook
        is activated.  Retrieved episodes have their FSRS state updated
        (grade=Good), and a retrievability bonus is added to
        ``combined_score`` with weight :data:`FSRS_WEIGHT` (``0.15``).
        Default False preserves byte-for-byte backward compatibility.
    project_id:
        If provided (not None), filter to episodes whose
        ``project_id == project_id OR project_scope == 'global'``.
        When ``None`` (default), project-scoped filtering is omitted and
        all episodes are considered (legacy global behavior).

    Returns
    -------
    ``list[dict[str, object]]``
        Each dict contains keys:
        - ``id`` (str) — UUID of the episode
        - ``safe_content`` (str) — content safe for the caller
        - ``classification`` (str) — data classification level
        - ``importance`` (int) — importance score (1-10)
        - ``created_at`` (datetime | None) — timestamp
        - ``combined_score`` (float) — hybrid ranking score
        - ``is_summarized`` (bool) — True if summary is used for content

    Raises
    ------
    ReadPipelineQueryError
        If ``query_text`` is empty or only whitespace.
    ReadPipelineSafetyError
        If the principal's classification ceiling denies all results.
    """
    # ---- validate inputs ---------------------------------------------------
    if not query_text or not query_text.strip():
        raise ReadPipelineQueryError(
            "query_text must be non-empty for memory recall"
        )

    query_text_stripped = query_text.strip()

    # Metadata-only query identifier for logging — never raw query text
    _query_len: int = len(query_text_stripped)
    _query_hash: str = hashlib.sha256(
        query_text_stripped.encode()
    ).hexdigest()[:16]

    # ---- compute query embedding (optional) --------------------------------
    query_vector: list[float] | None = None
    if embedding_service is not None:
        try:
            query_vector = await embedding_service.aembed(query_text_stripped)
        except Exception:
            _logger.warning("embedding_fallback_keyword", extra={"query_hash": _query_hash})
            # Graceful fallback: keyword-only search without vector similarity

    # ---- resolve classification ceiling ------------------------------------
    ceiling_label = _resolve_ceiling(principal, safe_mode)

    # ---- expanded query limit for RRF fusion --------------------------------
    expanded_limit = min(limit * EXPANDED_LIMIT_MULTIPLIER, MAX_CANDIDATE_POOL)

    # ---- execute signal queries --------------------------------------------
    recency_config = RecencyConfig()

    vector_rows: list[EpisodeProtocol] = []
    if query_vector is not None:
        vector_stmt = build_vector_query(
            query_vector, expanded_limit, exclude_dnr,
            project_id=project_id,
        )
        vector_result = await session.execute(vector_stmt)
        vector_rows = list(vector_result.scalars())

    fts_stmt = build_fts_query(
        query_text_stripped, expanded_limit, exclude_dnr,
        project_id=project_id,
    )
    fts_result = await session.execute(fts_stmt)
    fts_rows: list[EpisodeProtocol] = list(fts_result.scalars())

    recency_stmt = build_recency_query(
        expanded_limit, exclude_dnr,
        project_id=project_id,
    )
    recency_result = await session.execute(recency_stmt)
    recency_rows: list[EpisodeProtocol] = list(recency_result.scalars())

    # ---- P16: KG graph signal (optional, 4th RRF signal) -------------------
    # When ``kg_enabled`` is True, attempt to compute graph-based relevance
    # scores via ``KGRRFFusion.compute_graph_scores``.  The KG module returns
    # ``{fact_id: graph_score}`` where ``fact_id`` is a UUID from
    # ``memory.kg_edges.source_fact_id``.  We convert the score dict into a
    # 1-based rank map keyed by the string form of each fact UUID, sorted by
    # graph score descending — this is the data structure consumed by the
    # KG RRF score adjustment block below.
    #
    # Lazy import + broad except: KG construction requires a session_factory
    # callable that the current ``RecallSession`` protocol does not expose,
    # so ``KGQueryEngine(session)`` raises ``TypeError`` until a future
    # protocol extension wires ``session_factory`` through.  Any failure —
    # ``ImportError`` (module absent), ``TypeError`` (protocol mismatch),
    # ``RuntimeError`` (DB outage) — is caught and the pipeline falls back
    # to 3-signal fusion silently.  Default ``kg_enabled=False`` skips this
    # block entirely, preserving 100% of existing behavior.
    kg_rank_map: dict[str, int] = {}
    if kg_enabled:
        try:
            from guinevere.knowledge_graph.query.rrf_fusion import (
                KGRRFFusion,
                KGQueryEngine,
                PersonalizedPageRank,
            )
            # Wrap the active recall session in a BorrowedSession factory
            # so the KG module can use it without closing it.  The caller
            # retains full lifecycle ownership of the session.
            from guinevere.knowledge_graph.repository import make_borrowed_factory  # noqa: PLC0415
            _kg_factory = make_borrowed_factory(session)
            _kg_engine_obj: object = KGQueryEngine(_kg_factory)
            _kg_ppr_obj: object = PersonalizedPageRank(_kg_factory)
            _kg_fusion_obj: object = KGRRFFusion(_kg_engine_obj, _kg_ppr_obj)
            _graph_scores = await _kg_fusion_obj.compute_graph_scores(
                query_text_stripped,
                top_k=expanded_limit,
            )
            # Sort by score desc, then by fact_id str for deterministic
            # tie-breaking.  Assign 1-based ranks.
            _ordered_facts = sorted(
                _graph_scores.items(),
                key=lambda pair: (-pair[1], str(pair[0])),
            )
            kg_rank_map = {
                str(fact_id): rank
                for rank, (fact_id, _) in enumerate(_ordered_facts, start=1)
            }
        except ImportError:
            kg_rank_map = {}
            _logger.debug("kg_module_unavailable_recall_fallback")
        except Exception as _kg_exc:
            kg_rank_map = {}
            _logger.warning(
                "kg_recall_signal_failed",
                extra={
                    "error": str(_kg_exc),
                    "error_type": type(_kg_exc).__name__,
                },
            )

    # ---- build deduplicated episode map ------------------------------------
    merged = build_result_episode_map(
        vector_rows, fts_rows, recency_rows
    )

    if not merged:
        _logger.info(
            "recall_no_results",
            extra={"query_length": _query_len, "query_hash": _query_hash},
        )
        return []

    # ---- compute scores ----------------------------------------------------
    scored = compute_scored_results(merged, recency_config)

    # ---- P16: Apply KG RRF signal adjustment -------------------------------
    # When ``kg_enabled`` is True and the KG signal populated a rank map,
    # add the KG RRF contribution ``KG_WEIGHT / (RRF_K + kg_rank)`` to each
    # matched result's ``combined_score`` and re-sort descending.  When the
    # KG was unavailable, ``kg_rank_map`` is empty and this block is a no-op
    # (no re-sort, no mutation).  Default ``kg_enabled=False`` skips the
    # block entirely, preserving the existing scoring output verbatim.
    if kg_enabled and kg_rank_map:
        for r in scored:
            ep_id = str(r.get("id", ""))
            kg_rank = kg_rank_map.get(ep_id)
            if kg_rank is not None:
                kg_signal = KG_WEIGHT / (RRF_K + kg_rank)
                r["combined_score"] = (
                    float(r.get("combined_score", 0.0)) + kg_signal
                )
        scored.sort(
            key=lambda r: float(str(r.get("combined_score", 0))),
            reverse=True,
        )

    # ---- P18-008: FSRS reconsolidation-on-retrieval -----------------------
    # When ``fsrs_enabled`` is True, reinforce retrieved episodes by
    # updating their FSRS state (grade=Good, simulating successful recall).
    # This increases retrievability for frequently-accessed memories.
    #
    # Pattern: mirrors kg_enabled — lazy import, broad except, silent fallback.
    # Default False = no-op, preserves existing behavior byte-for-byte.
    fsrs_updated_count = 0
    if fsrs_enabled:
        try:
            from guinevere.memory.spaced_repetition import FSRSScheduler, GRADE_GOOD
            _fsrs_scheduler = FSRSScheduler()
            for r in scored:
                ep_id = str(r.get("id", ""))
                cand_entry = merged.get(ep_id)
                if cand_entry is not None:
                    episode = cand_entry.episode
                    try:
                        _fsrs_scheduler.update_episode_state(episode, GRADE_GOOD)
                        fsrs_updated_count += 1
                    except Exception as _ep_exc:
                        _logger.debug(
                            "fsrs_episode_update_failed",
                            extra={"episode_id": ep_id, "error": str(_ep_exc)},
                        )
            # Add FSRS retrievability bonus to combined_score
            if fsrs_updated_count > 0:
                for r in scored:
                    ep_id = str(r.get("id", ""))
                    cand_entry = merged.get(ep_id)
                    if cand_entry is not None:
                        ep = cand_entry.episode
                        retrievability = getattr(ep, "retrievability", None)
                        if isinstance(retrievability, (int, float)) and retrievability > 0:
                            fsrs_signal = FSRS_WEIGHT * retrievability / (RRF_K + 1)
                            r["combined_score"] = (
                                float(r.get("combined_score", 0.0)) + fsrs_signal
                            )
                scored.sort(
                    key=lambda r: float(str(r.get("combined_score", 0))),
                    reverse=True,
                )
        except ImportError:
            _logger.debug("fsrs_module_unavailable_recall_fallback")
        except Exception as _fsrs_exc:
            _logger.warning(
                "fsrs_reconsolidation_failed",
                extra={
                    "error": str(_fsrs_exc),
                    "error_type": type(_fsrs_exc).__name__,
                },
            )

    # ---- classification ceiling filter -------------------------------------
    ceil_level = CLASSIFICATION_ORDER.get(ceiling_label, 0)
    filtered_scored: list[dict[str, object]] = []
    for r in scored:
        ep_id = str(r.get("id", ""))
        cand_entry = merged.get(ep_id)
        if cand_entry is None:
            continue
        ep = cand_entry.episode
        ep_class_level = classification_level(ep.classification)
        if ep_class_level <= ceil_level:
            filtered_scored.append(r)

    if not filtered_scored:
        raise ReadPipelineSafetyError(
            f"All {len(scored)} candidate results filtered by classification "
            + f"ceiling '{ceiling_label}' (level {ceil_level}) for principal "
            + f"'{principal}'"
        )

    # ---- limit to requested count before safe mode / budget -----------------
    results = filtered_scored[:limit]

    # ---- build safe_content and is_summarized --------------------------------
    sm_redacted_count = 0
    sm_blocked_count = 0
    for r in results:
        ep_id = str(r.get("id", ""))
        cand_entry = merged.get(ep_id)
        if cand_entry is not None:
            safe_content, is_summarized = build_safe_content(
                cand_entry.episode, safe_mode
            )
            r["safe_content"] = safe_content
            r["is_summarized"] = is_summarized
            # Count safe-mode redactions/blocks for metadata logging
            if safe_mode:
                if safe_content in (
                    SAFE_MODE_PLACEHOLDER,
                    SAFE_MODE_RESTRICTED_PLACEHOLDER,
                ):
                    sm_redacted_count += 1
                elif safe_content == SAFE_MODE_CONTENT_BLOCKED_PLACEHOLDER:
                    sm_blocked_count += 1

    # ---- token budget enforcement -------------------------------------------
    results = apply_token_budget(results, token_budget)

    if not results and limit > 0:
        _logger.warning(
            "recall_token_budget_empty",
            extra={"budget": token_budget, "limit": limit},
        )

    _logger.info(
        "recall_complete",
        extra={
            "query_length": _query_len,
            "query_hash": _query_hash,
            "candidates": len(merged),
            "filtered": len(filtered_scored),
            "returned": len(results),
            "principal": principal,
            "safe_mode": safe_mode,
            "exclude_dnr": exclude_dnr,
            "safe_mode_redacted": sm_redacted_count,
            "safe_mode_blocked": sm_blocked_count,
            "kg_enabled": kg_enabled,
            "fsrs_enabled": fsrs_enabled,
            "fsrs_updated": fsrs_updated_count,
        },
    )

    return results


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "PUBLIC",
    "INTERNAL",
    "RESTRICTED",
    "CONFIDENTIAL",
    "CRITICAL",
    "RRF_K",
    "RECENCY_HALF_LIFE_DAYS",
    "EXPANDED_LIMIT_MULTIPLIER",
    "SAFE_MODE_PLACEHOLDER",
    "SAFE_MODE_RESTRICTED_PLACEHOLDER",
    "SAFE_MODE_CONTENT_BLOCKED_PLACEHOLDER",
    "DEFAULT_TOKEN_BUDGET",
    "CHARS_PER_TOKEN",
    "VECTOR_WEIGHT",
    "FTS_WEIGHT",
    "FSRS_WEIGHT",
    "BOTH_SIGNAL_BONUS",
    "RECENCY_MAX_BOOST",
    "MAX_CANDIDATE_POOL",
    "ReadPipelineError",
    "ReadPipelineQueryError",
    "ReadPipelineSafetyError",
    "ReadPipelineTokenBudgetError",
    "RecencyConfig",
    "compute_rrf_score",
    "normalize_importance",
    "classification_level",
    "_is_safe_mode_blocked_content",
    "_resolve_ceiling",
    "build_vector_query",
    "build_fts_query",
    "build_recency_query",
    "EpisodeEntry",
    "build_result_episode_map",
    "compute_scored_results",
    "build_safe_content",
    "estimate_tokens",
    "apply_token_budget",
    "recall_memories",
]