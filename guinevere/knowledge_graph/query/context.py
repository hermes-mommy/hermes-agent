"""Recall context assembler — P16-003 end-to-end pipeline.

This module ties the four preceding modules together into the
single pipeline that the recall orchestrator (Wave 3+) will call.

Pipeline
--------

:meth:`RecallContextAssembler.assemble` performs, in order:

1. **Seed resolution** — :meth:`KGQueryEngine.search_entities` to
   map the user query into KG seed entities (unless the caller
   supplies ``seed_entity_ids`` directly).
2. **PPR scoring** — :meth:`PersonalizedPageRank.compute` to rank
   every reachable entity by graph proximity to the seeds.
3. **Traversal** — :meth:`KGQueryEngine.traverse` for the subgraph
   within ``max_hops`` of the seeds.
4. **Graph-score mapping** —
   :meth:`KGRRFFusion.compute_graph_scores` to convert PPR ranks
   into ``{fact_id: graph_score}`` for the RRF formula.
5. **RRF fusion** — :meth:`KGRRFFusion.fuse_with_existing` to add
   the 4th KG signal to the existing recall results.
6. **Token-bounded formatting** —
   :meth:`KGTokenBudgetManager.format_graph_context` to linearize
   the subgraph into a string that fits the KG's 1000-token slice.
7. **Result packaging** — return a :class:`RecallContext` carrying
   every intermediate artefact for audit and downstream
   integration.

Failure semantics
-----------------

The assembler follows the **non-breaking** contract inherited from
:meth:`KGRRFFusion.fuse_with_existing`: when the KG contributes no
signal (empty graph, no seeds, or PPR converges to a degenerate
distribution), the assembler returns a :class:`RecallContext` with
``enhanced_results`` equal to the input list and
``graph_signal_active=False`.  Callers can therefore always rely on
``RecallContext.enhanced_results`` being a valid (possibly
unchanged) list.

``KGError`` and its subclasses propagate; the assembler does not
swallow safety/consent violations.  Non-KG exceptions (DB outages
etc.) are wrapped in :class:`KGQueryError` with structured context.

Naming
------

The dataclass defined here is named :class:`RecallContext`.  It is
the *query-package* :class:`RecallContext` — distinct from
:class:`guinevere.knowledge_graph.types.RecallContext` (the
``types.RecallContext`` is a leaner bundle of entities / edges /
triples that ingestion uses).  Both can coexist; callers should
import from the most specific module (``query.context`` vs.
``types``).
"""
from __future__ import annotations

import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from guinevere.knowledge_graph.constants import KG_TOKEN_BUDGET_MAX, MAX_TRAVERSAL_HOPS
from guinevere.knowledge_graph.errors import KGQueryError
from guinevere.knowledge_graph.observability.logger import (
    KGLogContext,
    get_kg_logger,
    log_kg_operation,
)
from guinevere.knowledge_graph.observability.metrics import KGMetrics
from guinevere.knowledge_graph.query.engine import (
    EntityMatch,
    GraphTraversalResult,
    KGQueryEngine,
)
from guinevere.knowledge_graph.query.ppr import PPRResult, PersonalizedPageRank
from guinevere.knowledge_graph.query.rrf_fusion import KGRRFFusion
from guinevere.knowledge_graph.query.token_budget import (
    KGTokenBudgetManager,
    FormattedContext,
)

logger = get_kg_logger("query.context")


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class RecallContext:
    """Complete recall context including KG augmentation.

    The :class:`RecallContext` is a *mutable* dataclass (not frozen)
    because the assembler fills its fields progressively as the
    pipeline runs.  Callers that need an immutable copy should
    :func:`dataclasses.replace` the result before sharing it.

    Attributes:
        enhanced_results: Original recall results with the 4th KG
            RRF signal added.  When the KG contributed nothing,
            this is the input list unchanged (per the non-breaking
            contract).
        graph_context: Linearized KG context, trimmed to the
            per-call budget.  May be empty when the KG contributed
            nothing or after trimming dropped every line.
        seed_entities: Entities matched by :meth:`search_entities`
            in step 1 of the pipeline.  Stored as
            ``EntityMatch``-shaped dicts (``entity_id``,
            ``display_name``, ``entity_type``, ``relevance``) so
            the data is JSON-serialisable for audit logs.
        traversal_depth: Actual number of hops walked in step 3.
            ``0`` when no traversal was performed.
        ppr_scores: ``{entity_id_str: score}`` — the entity-level
            PPR scores produced in step 2.  Keys are stringified
            UUIDs for JSON safety.
        token_usage: Estimated tokens consumed by ``graph_context``
            (uses the same estimator as the recall pipeline).
        graph_signal_active: ``True`` when the KG contributed at
            least one ranked entity *or* one fused RRF signal.
            Downstream code can short-circuit on ``False``.
    """

    enhanced_results: list[dict[str, Any]] = field(default_factory=list)
    graph_context: str = ""
    seed_entities: list[dict[str, Any]] = field(default_factory=list)
    traversal_depth: int = 0
    ppr_scores: dict[str, float] = field(default_factory=dict)
    token_usage: int = 0
    graph_signal_active: bool = False


# ---------------------------------------------------------------------------
# Assembler
# ---------------------------------------------------------------------------


class RecallContextAssembler:
    """Assembles a full :class:`RecallContext` for prompt injection.

    Args:
        query_engine: A :class:`KGQueryEngine` instance.
        ppr: A :class:`PersonalizedPageRank` instance.
        rrf_fusion: A :class:`KGRRFFusion` instance.
        token_budget: A :class:`KGTokenBudgetManager` instance.

    All four collaborators must be supplied because the assembler
    treats them as a coordinated pipeline — partial wiring would
    produce silently degraded recall.  The constructor refuses to
    accept ``None`` for any collaborator.

    Example::

        engine = KGQueryEngine(session_factory)
        ppr = PersonalizedPageRank(query_engine=engine)
        rrf = KGRRFFusion(query_engine=engine, ppr=ppr)
        budget = KGTokenBudgetManager(query_engine=engine)
        assembler = RecallContextAssembler(engine, ppr, rrf, budget)

        ctx = await assembler.assemble(
            query_text="Apa itu Guinevere?",
            existing_recall_results=existing,
        )
        # ctx.enhanced_results, ctx.graph_context ready for prompt.
    """

    def __init__(
        self,
        query_engine: KGQueryEngine,
        ppr: PersonalizedPageRank,
        rrf_fusion: KGRRFFusion,
        token_budget: KGTokenBudgetManager,
    ) -> None:
        if query_engine is None:
            raise ValueError("query_engine is required")
        if ppr is None:
            raise ValueError("ppr is required")
        if rrf_fusion is None:
            raise ValueError("rrf_fusion is required")
        if token_budget is None:
            raise ValueError("token_budget is required")
        self._query_engine: KGQueryEngine = query_engine
        self._ppr: PersonalizedPageRank = ppr
        self._rrf: KGRRFFusion = rrf_fusion
        self._budget: KGTokenBudgetManager = token_budget
        self._metrics: KGMetrics = KGMetrics.get_instance()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def assemble(
        self,
        query_text: str,
        existing_recall_results: list[dict[str, Any]],
        *,
        seed_entity_ids: Sequence[uuid.UUID] | None = None,
        token_budget: int = KG_TOKEN_BUDGET_MAX,
        traversal_max_hops: int = MAX_TRAVERSAL_HOPS,
        project_id: uuid.UUID | None = None,
    ) -> RecallContext:
        """Run the full KG recall pipeline.

        When ``project_id`` is provided, all KG operations
        (seed resolution, PPR scoring, traversal, fusion) are
        scoped to entities/edges whose ``project_id == project_id``
        or ``project_scope == 'global'``.

        Args:
            query_text: User/operator query.  Used for seed
                resolution when ``seed_entity_ids`` is ``None`` and
                for log context.
            existing_recall_results: Output of the existing recall
                pipeline (vector + FTS + recency).  Required — the
                assembler returns these results augmented with the
                KG signal (or unchanged when the KG contributes
                nothing).
            seed_entity_ids: Optional explicit seed entities.  When
                ``None``, the assembler derives seeds from
                :meth:`KGQueryEngine.search_entities`.
            token_budget: Per-call KG budget.  Defaults to
                :data:`guinevere.knowledge_graph.constants.KG_TOKEN_BUDGET_MAX`
                (1000).  The :class:`KGTokenBudgetManager` enforces
                the ceiling.
            traversal_max_hops: BFS depth for the
                :meth:`KGQueryEngine.traverse` call.  Defaults to
                :data:`guinevere.knowledge_graph.constants.MAX_TRAVERSAL_HOPS`
                (3).
            project_id: When set, scope all KG operations to the
                given project namespace.  ``None`` (default) = no
                project filtering (legacy global behavior).

        Returns:
            A fully-populated :class:`RecallContext` ready for
            prompt injection.

        Raises:
            KGQueryError: Wraps non-KG exceptions (DB outages etc.)
                with structured context for observability.  Pure
                KG errors propagate as their original subclass.
        """
        log_ctx = KGLogContext(operation="kg_recall_assemble")
        start_time = time.perf_counter()

        # Pre-flight: defensive copy so we never mutate the caller's list.
        existing_list = list(existing_recall_results or [])
        out = RecallContext(enhanced_results=existing_list)

        try:
            await self._run_pipeline(
                out=out,
                query_text=query_text,
                seed_entity_ids=seed_entity_ids,
                token_budget=token_budget,
                traversal_max_hops=traversal_max_hops,
                project_id=project_id,
            )
        except KGQueryError:
            # Already typed — propagate with audit trail intact.
            raise
        except Exception as exc:  # noqa: BLE001 — narrowed below
            raise KGQueryError(
                "RecallContext assembly failed",
                context={
                    "query_len": len(query_text or ""),
                    "existing_results": len(existing_list),
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:200],
                },
            ) from exc

        elapsed = time.perf_counter() - start_time
        self._metrics.observe_query_duration(
            query_type="assemble",
            hop_count=out.traversal_depth,
            duration=elapsed,
        )
        log_ctx.duration_ms = elapsed * 1000.0
        log_ctx.result_count = len(out.enhanced_results)
        log_kg_operation(logger, log_ctx)

        return out

    # ------------------------------------------------------------------
    # Pipeline steps
    # ------------------------------------------------------------------

    async def _run_pipeline(
        self,
        *,
        out: RecallContext,
        query_text: str,
        seed_entity_ids: Sequence[uuid.UUID] | None,
        token_budget: int,
        traversal_max_hops: int,
        project_id: uuid.UUID | None = None,
    ) -> None:
        """Internal: run the seven-step pipeline, mutating ``out``."""
        # Step 1 — seed resolution.
        seed_matches: list[EntityMatch]
        if seed_entity_ids:
            seed_matches = await self._resolve_explicit_seeds(seed_entity_ids)
        else:
            seed_matches = await self._query_engine.search_entities(
                query_text, limit=10,
                project_id=project_id,
            )
        out.seed_entities = [self._match_to_dict(m) for m in seed_matches]
        seeds: list[uuid.UUID] = [m.entity_id for m in seed_matches]

        # If no seeds resolve, we still produce a valid (no-signal) context.
        if not seeds:
            # Defer to the rrf fusion which already short-circuits on empty seeds.
            out.enhanced_results = self._rrf.fuse_with_existing(
                existing_results=out.enhanced_results,
                graph_scores={},
            )
            # ``graph_context`` stays empty; ``graph_signal_active`` stays False.
            return

        # Step 2 — PPR scoring.
        ppr_results: list[PPRResult] = await self._ppr.compute(
            seeds, top_k=50, project_id=project_id,
        )
        out.ppr_scores = {
            str(pr.entity_id): float(pr.score) for pr in ppr_results
        }

        # Step 3 — traversal from the seeds.
        traversal: list[GraphTraversalResult] = await self._query_engine.traverse(
            seeds,
            max_hops=traversal_max_hops,
            project_id=project_id,
        )
        out.traversal_depth = self._max_depth(traversal)

        # Step 4 — graph scores (fact-level mapping).
        graph_scores = await self._rrf.compute_graph_scores(
            query_text,
            seed_entity_ids=seeds,
            project_id=project_id,
        )

        # Step 5 — RRF fusion.
        out.enhanced_results = self._rrf.fuse_with_existing(
            existing_results=out.enhanced_results,
            graph_scores=graph_scores,
        )

        # Step 6 — token-bounded formatting.
        formatted: FormattedContext = self._budget.format_graph_context_sync(
            traversal_results=traversal,
            ppr_results=ppr_results,
            max_tokens=token_budget,
        )
        out.graph_context = formatted.text
        out.token_usage = formatted.tokens_used

        # Step 7 — determine graph_signal_active.
        # The KG contributed if either:
        #   - PPR produced at least one non-zero score, OR
        #   - The RRF fusion added a non-zero kg_contribution to any row.
        ppr_signal = any(score > 0.0 for score in out.ppr_scores.values())
        rrf_signal = any(
            float(row.get("kg_contribution", 0.0) or 0.0) > 0.0
            for row in out.enhanced_results
        )
        out.graph_signal_active = bool(ppr_signal or rrf_signal)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _resolve_explicit_seeds(
        self,
        seed_entity_ids: Sequence[uuid.UUID],
    ) -> list[EntityMatch]:
        """Convert explicit UUID seeds into :class:`EntityMatch` records.

        Performs a single SQL ``SELECT`` to fetch the matching
        entity rows.  UUIDs not found in the table are silently
        dropped — the caller can detect this by inspecting the
        returned list length.

        Args:
            seed_entity_ids: Caller-supplied seed UUIDs.

        Returns:
            A list of :class:`EntityMatch` (one per found entity).
        """
        ids = [uuid.UUID(str(s)) for s in seed_entity_ids]
        if not ids:
            return []
        sql = """
        SELECT id, canonical_key, entity_type, display_name, description, aliases
        FROM memory.kg_entities
        WHERE is_tombstoned = FALSE
          AND id = ANY(CAST(:ids AS uuid[]))
        """
        rows = await self._query_engine.execute_to_rows(
            sql, {"ids": [str(i) for i in ids]},
        )
        matches: list[EntityMatch] = []
        for row in rows:
            ent_id = getattr(row, "id", None)
            if not isinstance(ent_id, uuid.UUID):
                ent_id = uuid.UUID(str(ent_id))
            matches.append(
                EntityMatch(
                    entity_id=ent_id,
                    canonical_key=str(getattr(row, "canonical_key", "")),
                    display_name=str(getattr(row, "display_name", "")),
                    entity_type=str(getattr(row, "entity_type", "concept")),
                    description=getattr(row, "description", None),
                    aliases=list(getattr(row, "aliases", []) or []),
                    relevance=1.0,  # Explicit seeds score full marks.
                ),
            )
        return matches

    @staticmethod
    def _match_to_dict(match: EntityMatch) -> dict[str, Any]:
        """Render an :class:`EntityMatch` as a JSON-safe dict for audit."""
        return {
            "entity_id": str(match.entity_id),
            "display_name": match.display_name,
            "entity_type": match.entity_type,
            "canonical_key": match.canonical_key,
            "relevance": float(match.relevance),
        }

    @staticmethod
    def _max_depth(traversal: Sequence[GraphTraversalResult]) -> int:
        """Return the largest ``depth`` observed in ``traversal``.

        ``0`` when ``traversal`` is empty.
        """
        if not traversal:
            return 0
        return max(tr.depth for tr in traversal)


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "RecallContext",
    "RecallContextAssembler",
]
