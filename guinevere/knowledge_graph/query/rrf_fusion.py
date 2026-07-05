"""KG-aware Reciprocal Rank Fusion (RRF) — P16-003 4th RRF signal.

This module plugs the Knowledge Graph into the existing
``guinevere.memory.read_pipeline`` recall fusion as a **4th signal**.
The existing pipeline fuses three signals per
:func:`guinevere.memory.read_pipeline.compute_rrf_score`:

* vector cosine similarity (weight 0.50)
* full-text search relevance (weight 0.50)
* recency decay (applied as a multiplicative boost, max +10%)

We add the KG signal **on top** without touching the read pipeline —
the integration is additive and non-breaking.  The pipeline keeps
producing the same scores; the caller (recall orchestrator) asks
this module for a 4th-rank contribution per result and adds it to
``combined_score``.

Faiz-locked weights
-------------------

The weights below are not configurable from the call site — they
are pinned by PRD v2.2 P16 spec and must remain stable across
deployments.  Promoting them to configuration requires a documented
PRD/ADR change.

============  =====
Signal        Weight
============  =====
vector        0.50
fts           0.50
recency       0.25 (boost, not rank)
kg            0.20
============  =====

All four weights use the standard RRF formula
``weight / (K + rank)`` with ``K = 60`` (the
:data:`guinevere.knowledge_graph.constants.RRF_K` value).

Algorithm
---------

:meth:`KGRRFFusion.compute_graph_scores` produces a
``{fact_id: graph_score}`` mapping where:

* ``fact_id`` is a :class:`uuid.UUID` from
  ``memory.kg_edges.source_fact_id`` — every edge has a non-NULL
  source fact.
* ``graph_score`` is a ``[0.0, 1.0]`` PPR score mapped from the
  entity that owns the edge.

:meth:`KGRRFFusion.fuse_with_existing` then walks the existing
recall results, looks up each result's ``id`` (string UUID) in the
graph-scores mapping, and — on a hit — adds the KG RRF contribution
to ``combined_score``.

**Non-breaking contract**: if ``graph_scores`` is empty (the graph
contributed no signal), :meth:`fuse_with_existing` returns the
``existing_results`` list unchanged.  This guarantees the recall
pipeline continues to function when the KG is empty or unreachable.

Lazy integration
----------------

The actual call site that wires this module into the recall loop
will land in Wave 3+ and will live inside
``guinevere.memory.read_pipeline``.  Per the task contract we do NOT
modify that file in this task — only the additive signal lives
here, ready to be consumed.
"""
from __future__ import annotations

import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from guinevere.knowledge_graph.constants import KG_RRF_WEIGHT, RRF_K
from guinevere.knowledge_graph.errors import KGQueryError
from guinevere.knowledge_graph.observability.logger import (
    KGLogContext,
    get_kg_logger,
    log_kg_operation,
)
from guinevere.knowledge_graph.observability.metrics import KGMetrics
from guinevere.knowledge_graph.query.engine import KGQueryEngine
from guinevere.knowledge_graph.query.ppr import PPRResult, PersonalizedPageRank

logger = get_kg_logger("query.rrf_fusion")


# ---------------------------------------------------------------------------
# Weights and constants (Faiz-locked — do not change without PRD/ADR)
# ---------------------------------------------------------------------------


#: KG RRF weight (Faiz-locked per PRD v2.2 P16).
KG_WEIGHT: float = KG_RRF_WEIGHT

#: Vector similarity RRF weight (mirrors ``read_pipeline.VECTOR_WEIGHT``).
VECTOR_WEIGHT: float = 0.50

#: Full-text-search RRF weight (mirrors ``read_pipeline.FTS_WEIGHT``).
FTS_WEIGHT: float = 0.50

#: Recency RRF weight (mirrors ``read_pipeline.RECENCY_MAX_BOOST``).
RECENCY_WEIGHT: float = 0.25

#: RRF damping constant.  Mirrors ``read_pipeline.RRF_K``.
K: int = RRF_K

#: Default cap on the top-``k`` graph entities we materialise into
#: the fact-id mapping.  60 matches the typical recall limit and
#: avoids blowing up the result dictionary for empty graphs.
DEFAULT_GRAPH_TOP_K: int = 60

#: Hard ceiling on the mapping size — guards against pathological
#: graphs with millions of edges.
MAX_GRAPH_TOP_K: int = 500


# ---------------------------------------------------------------------------
# Optional dataclass for callers that want structured access to the
# fusion metadata (not required by the contract but useful in tests).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GraphFusionResult:
    """Diagnostic bundle produced by :meth:`KGRRFFusion.compute_graph_scores`.

    Attributes:
        fact_scores: ``{fact_id: graph_score}`` mapping — the value
            :meth:`fuse_with_existing` consumes.
        ppr_results: Raw :class:`PPRResult` rows that produced the
            mapping (useful for audit / debugging).
        seed_entity_ids: Seeds actually used.  Empty when the PPR
            path was skipped because ``seed_entity_ids`` resolved to
            no entities (search-driven path returned no hits).
        query_text: The original query when search-driven seeding
            was used; ``None`` when seeds were passed directly.
    """

    fact_scores: dict[uuid.UUID, float]
    ppr_results: list[PPRResult]
    seed_entity_ids: list[uuid.UUID]
    query_text: str | None


# ---------------------------------------------------------------------------
# KGRRFFusion
# ---------------------------------------------------------------------------


class KGRRFFusion:
    """Integrates KG signals into the existing recall RRF fusion.

    The fusion is **strictly additive** — the existing recall scores
    produced by ``guinevere.memory.read_pipeline.compute_rrf_score`` are
    preserved verbatim; this module only computes the *additional*
    KG contribution per result.

    Args:
        query_engine: A :class:`KGQueryEngine` (P16-003 traversal).
        ppr: A :class:`PersonalizedPageRank` (P16-003 scoring).

    Example::

        engine = KGQueryEngine(session_factory)
        ppr = PersonalizedPageRank(query_engine=engine)
        rrf = KGRRFFusion(query_engine=engine, ppr=ppr)
        graph_scores = await rrf.compute_graph_scores(
            "Guinevere Faiz PostgreSQL",
        )
        fused = rrf.fuse_with_existing(existing_results, graph_scores)
    """

    def __init__(
        self,
        query_engine: KGQueryEngine,
        ppr: PersonalizedPageRank,
    ) -> None:
        self._query_engine: KGQueryEngine = query_engine
        self._ppr: PersonalizedPageRank = ppr
        self._metrics: KGMetrics = KGMetrics.get_instance()

    # ------------------------------------------------------------------
    # Graph-score computation
    # ------------------------------------------------------------------

    async def compute_graph_scores(
        self,
        query_text: str,
        *,
        seed_entity_ids: Sequence[uuid.UUID] | None = None,
        top_k: int = DEFAULT_GRAPH_TOP_K,
        project_id: uuid.UUID | None = None,
    ) -> dict[uuid.UUID, float]:
        """Compute graph-based relevance scores for the recall fusion.

        Steps:

        1. Resolve seed entities — either the caller's
           ``seed_entity_ids`` (when provided) or the top hits from
           :meth:`KGQueryEngine.search_entities` over ``query_text``.
        2. Run :meth:`PersonalizedPageRank.compute` from the seeds.
        3. For each PPR-ranked entity, fetch the active
           ``kg_edges.source_fact_id`` values that touch the entity
           (single SQL ``SELECT``).
        4. Map each fact to the entity's PPR score.
        5. Return the ``{fact_id: graph_score}`` dict, dropping
           entries with score 0.0.

        When ``project_id`` is provided, seed resolution and PPR are
        scoped to entities whose ``project_id == project_id OR
        project_scope == 'global'``.

        Args:
            query_text: Original query — used only for logging /
                audit.  Does not affect the math when
                ``seed_entity_ids`` is supplied.
            seed_entity_ids: Optional explicit seeds.  When
                ``None``, the engine seeds from entity search.
            top_k: Cap on PPR top-k.  Clamped to
                :data:`MAX_GRAPH_TOP_K`.
            project_id: When set, scope seed resolution to the given
                project namespace.

        Returns:
            ``{fact_id: graph_score}`` mapping.  Empty when the KG
            contributed no signal (no seeds, empty graph, or PPR
            converges to a degenerate distribution).

        Raises:
            KGQueryError: Database error during seed resolution,
                PPR computation, or fact lookup.
        """
        effective_top_k = max(1, min(top_k, MAX_GRAPH_TOP_K))

        ctx = KGLogContext(operation="kg_rrf_compute_graph_scores")
        start = time.perf_counter()

        # Step 1 — resolve seeds.
        seeds: list[uuid.UUID] = []
        if seed_entity_ids:
            seeds = [uuid.UUID(str(s)) for s in seed_entity_ids]
        else:
            try:
                matches = await self._query_engine.search_entities(
                    query_text, limit=10,
                    project_id=project_id,
                )
            except Exception as exc:  # noqa: BLE001 — narrowed below
                raise KGQueryError(
                    "seed resolution via search_entities failed",
                    context={
                        "query_len": len(query_text or ""),
                        "error_type": type(exc).__name__,
                    },
                ) from exc
            seeds = [m.entity_id for m in matches]

        if not seeds:
            duration = time.perf_counter() - start
            self._metrics.observe_query_duration(
                query_type="rrf_graph_scores", hop_count=0, duration=duration,
            )
            ctx.duration_ms = duration * 1000.0
            ctx.result_count = 0
            log_kg_operation(logger, ctx)
            return {}

        # Step 2 — PPR from seeds.
        ppr_results: list[PPRResult]
        try:
            ppr_results = await self._ppr.compute(
                seeds, top_k=effective_top_k, project_id=project_id,
            )
        except Exception as exc:  # noqa: BLE001 — narrowed below
            raise KGQueryError(
                "PPR compute failed inside graph-score fusion",
                context={
                    "seed_count": len(seeds),
                    "top_k": effective_top_k,
                    "error_type": type(exc).__name__,
                },
            ) from exc

        if not ppr_results:
            duration = time.perf_counter() - start
            self._metrics.observe_query_duration(
                query_type="rrf_graph_scores", hop_count=0, duration=duration,
            )
            ctx.duration_ms = duration * 1000.0
            ctx.result_count = 0
            log_kg_operation(logger, ctx)
            return {}

        # Step 3 — collect entity UUIDs and fetch source_fact_id values.
        entity_ids = [r.entity_id for r in ppr_results]
        entity_to_score: dict[uuid.UUID, float] = {
            r.entity_id: r.score for r in ppr_results
        }
        try:
            fact_to_entities = await self._fetch_facts_for_entities(entity_ids)
        except Exception as exc:  # noqa: BLE001 — narrowed below
            raise KGQueryError(
                "fact lookup for PPR entities failed",
                context={
                    "entity_count": len(entity_ids),
                    "error_type": type(exc).__name__,
                },
            ) from exc

        # Step 4 — fold per-entity scores onto fact_ids.
        # When a fact is touched by multiple entities, we keep the
        # *maximum* score so the strongest connected entity wins.
        fact_scores: dict[uuid.UUID, float] = {}
        for fact_id, ent_ids in fact_to_entities.items():
            best = 0.0
            for ent_id in ent_ids:
                candidate = entity_to_score.get(ent_id, 0.0)
                if candidate > best:
                    best = candidate
            if best > 0.0:
                fact_scores[fact_id] = best

        duration = time.perf_counter() - start
        self._metrics.observe_query_duration(
            query_type="rrf_graph_scores", hop_count=len(ppr_results), duration=duration,
        )
        self._metrics.record_rrf_signal("graph")
        ctx.duration_ms = duration * 1000.0
        ctx.result_count = len(fact_scores)
        log_kg_operation(logger, ctx)

        return fact_scores

    async def _fetch_facts_for_entities(
        self,
        entity_ids: Sequence[uuid.UUID],
    ) -> dict[uuid.UUID, list[uuid.UUID]]:
        """Return ``{fact_id: [entity_id, ...]}`` for edges touching any entity.

        Filters ``is_tombstoned = FALSE`` so soft-deleted edges never
        contribute to the recall fusion.
        """
        if not entity_ids:
            return {}
        # Reach back into the query engine's session factory — the
        # repository pattern is the only DB gateway.
        repo = self._query_engine._repo  # noqa: SLF001 — internal contract
        sql = """
        SELECT DISTINCT ON (source_fact_id, src_entity_id, dst_entity_id)
            source_fact_id,
            src_entity_id,
            dst_entity_id
        FROM memory.kg_edges
        WHERE is_tombstoned = FALSE
          AND (src_entity_id = ANY(CAST(:entity_ids AS uuid[]))
               OR dst_entity_id = ANY(CAST(:entity_ids AS uuid[])))
        ORDER BY source_fact_id, src_entity_id, dst_entity_id
        """
        params: dict[str, Any] = {
            "entity_ids": [str(e) for e in entity_ids],
        }
        out: dict[uuid.UUID, list[uuid.UUID]] = {}
        async with repo.get_session() as session:
            from sqlalchemy import text as _sa_text
            result = await session.execute(_sa_text(sql), params)
            rows = list(result.fetchall())
        for row in rows:
            fact_id = row.source_fact_id
            src = row.src_entity_id
            dst = row.dst_entity_id
            out.setdefault(fact_id, [])
            if src in entity_ids and src not in out[fact_id]:
                out[fact_id].append(src)
            if dst in entity_ids and dst not in out[fact_id]:
                out[fact_id].append(dst)
        return out

    # ------------------------------------------------------------------
    # Fusion
    # ------------------------------------------------------------------

    def fuse_with_existing(
        self,
        existing_results: list[dict[str, Any]],
        graph_scores: dict[uuid.UUID, float],
    ) -> list[dict[str, Any]]:
        """Add KG as the 4th RRF signal to existing recall results.

        Each result in ``existing_results`` is a dict matching the
        shape produced by :func:`guinevere.memory.read_pipeline.recall_memories`
        (keys: ``id``, ``safe_content``, ``classification``,
        ``importance``, ``created_at``, ``combined_score``,
        ``is_summarized``).  The ``id`` is the string form of a UUID.

        For every result whose ``id`` parses as a UUID and is found
        in ``graph_scores``, this method:

        1. Computes the entity's rank in the sorted graph_scores
           (``1`` = highest score).
        2. Adds the KG RRF contribution ``KG_WEIGHT / (K + rank)`` to
           the result's ``combined_score``.
        3. Records ``kg_rank`` and ``kg_score`` on the result dict
           (audit-friendly) so downstream logging can show the
           graph contribution.

        **Non-breaking:** when ``graph_scores`` is empty, the input
        list is returned unchanged (no copy, no mutation).  This
        keeps the recall pipeline functional when the KG is empty
        or offline.

        Args:
            existing_results: Output of the existing recall pipeline.
                Must be a list; ``None`` is treated as empty.
            graph_scores: Output of :meth:`compute_graph_scores`.

        Returns:
            The same list (sorted by ``combined_score`` descending) —
            either the original (when ``graph_scores`` is empty) or
            a new list with KG-augmented scores.
        """
        if not existing_results:
            return existing_results
        if not graph_scores:
            # Non-breaking: nothing to add.
            return existing_results

        # Build the rank map: 1-based, sorted by score desc.
        ordered_facts = sorted(
            graph_scores.items(),
            key=lambda pair: (-pair[1], str(pair[0])),
        )
        fact_to_rank: dict[uuid.UUID, int] = {
            fact_id: rank for rank, (fact_id, _) in enumerate(ordered_facts, start=1)
        }

        # Mutate a shallow copy so the caller's list reference is
        # unchanged but the dicts inside are new (audit-safety).
        augmented: list[dict[str, Any]] = []
        for row in existing_results:
            new_row = dict(row)
            raw_id = row.get("id")
            graph_rank: int | None = None
            graph_score: float | None = None
            if isinstance(raw_id, str):
                try:
                    parsed = uuid.UUID(raw_id)
                except ValueError:
                    parsed = None
                if parsed is not None and parsed in fact_to_rank:
                    graph_rank = fact_to_rank[parsed]
                    graph_score = graph_scores[parsed]
            if graph_rank is not None and graph_score is not None:
                kg_contribution = self.compute_rrf_rank(
                    rank=graph_rank, weight=KG_WEIGHT, k=K,
                )
                current = float(row.get("combined_score", 0.0) or 0.0)
                new_row["combined_score"] = current + kg_contribution
                new_row["kg_rank"] = graph_rank
                new_row["kg_score"] = graph_score
                new_row["kg_contribution"] = kg_contribution
            else:
                # KG did not contribute — record zero-rank for transparency.
                new_row["kg_rank"] = None
                new_row["kg_score"] = None
                new_row["kg_contribution"] = 0.0
            augmented.append(new_row)

        augmented.sort(
            key=lambda r: float(r.get("combined_score", 0.0) or 0.0),
            reverse=True,
        )
        return augmented

    # ------------------------------------------------------------------
    # Static RRF helpers
    # ------------------------------------------------------------------

    @staticmethod
    def compute_rrf_rank(rank: int, weight: float, k: int = K) -> float:
        """Single RRF rank component: ``weight / (k + rank)``.

        Args:
            rank: 1-based rank (1 = highest).  Values < 1 are
                clamped to 1 to avoid dividing by ``k + 0``.
            weight: Signal weight.  Must be ``>= 0``; weights above
                1.0 are accepted but will skew the fusion.
            k: Damping constant.  Defaults to :data:`K` (60).

        Returns:
            The RRF contribution ``weight / (k + rank)``.

        Raises:
            ValueError: ``weight`` is negative.
        """
        if weight < 0:
            raise ValueError(f"weight must be >= 0; got {weight}")
        safe_rank = max(1, int(rank))
        return float(weight) / float(int(k) + safe_rank)


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    # Faiz-locked weights (mirrored from PRD v2.2 P16)
    "KG_WEIGHT",
    "VECTOR_WEIGHT",
    "FTS_WEIGHT",
    "RECENCY_WEIGHT",
    "K",
    "DEFAULT_GRAPH_TOP_K",
    "MAX_GRAPH_TOP_K",
    # Diagnostic dataclass
    "GraphFusionResult",
    # Main class
    "KGRRFFusion",
]
