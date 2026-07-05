"""Knowledge Graph Personalized PageRank (PPR) — P16-003 graph scoring.

PPR computes a *relevance score* for every entity reachable from a
seed set, given the structure of the KG.  It is the standard way to
rank graph nodes against a personalised teleport distribution: the
random walker mostly follows edges (probability ``damping``) and
occasionally teleports back to the seeds (probability
``1 - damping``).

Why PPR for recall fusion
-------------------------

A simple BFS over the KG would surface every node within N hops
without distinguishing between nodes that are *strongly* connected to
the seed and nodes that are merely *near*.  PPR captures strength of
connection: a node that is connected to many high-scoring nodes
inherits some of their score, and the seed itself remains the highest-
scoring node by construction.

The output scores feed directly into the KG-aware RRF fusion module
(see :mod:`guinevere.knowledge_graph.query.rrf_fusion`) — the PPR rank
becomes the ``graph_rank`` signal in the recall formula.

Implementation
--------------

PPR is computed **in-process via power iteration** over an adjacency
map loaded from PostgreSQL with a single ``SELECT`` query.  This
deliberate choice:

* avoids database round-trips per iteration (would be prohibitively
  slow),
* keeps the hot loop in native Python (fast enough for the M0-M2
  graph sizes of < 100 k entities / < 500 k edges),
* uses a sparse ``dict[UUID, list[UUID]]`` adjacency because the KG
  is sparse — most nodes have a small out-degree.

Dead-end (dangling-node) handling follows the Page et al. (1999)
convention: when the walker visits a node with no outgoing edges,
its mass is *not* lost — it is redistributed across the
personalisation vector.  Without this fix, dead ends artificially
drain probability mass and starve the rest of the graph.

Tombstoned nodes and edges are excluded at the SQL stage so the
in-process graph is already filtered.

Numerical safety
----------------

All scores are stored as plain ``float`` (Python ``double``).  At the
end of each iteration we compute the L1 delta against the previous
vector; if it drops below ``tolerance`` we early-exit.  The
implementation also caps the iteration count via
``max_iterations`` so a poorly-converging graph (e.g. disconnected
seeds) cannot run forever.

Result type
-----------

:class:`PPRResult` is a frozen dataclass carrying the entity UUID,
display name, taxonomy type, raw PPR score, and 1-based rank.
Entity name/type are fetched in a single follow-up ``SELECT`` after
the power iteration converges — this keeps the hot loop free of DB
round-trips.
"""
from __future__ import annotations

import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from guinevere.knowledge_graph.errors import KGQueryError
from guinevere.knowledge_graph.observability.logger import (
    KGLogContext,
    get_kg_logger,
    log_kg_operation,
)
from guinevere.knowledge_graph.observability.metrics import KGMetrics
from guinevere.knowledge_graph.repository import KGRepository, SessionFactory

logger = get_kg_logger("query.ppr")

# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PPRResult:
    """One entity's PPR score.

    Attributes:
        entity_id: UUID of the entity whose score is reported.
        entity_name: Human-readable display name from
            ``memory.kg_entities.display_name`` (DDL column).  Used by
            the context assembler to render SPO triples for prompt
            injection — the caller never has to re-fetch.
        entity_type: Taxonomy classification string from
            ``memory.kg_entities.entity_type`` (e.g. ``"person"``,
            ``"project"``).  Used as the predicate context for the
            SPO triple linearisation.
        score: PPR score in ``[0.0, 1.0]`` *after* normalisation
            across the reachable subgraph.  Scores sum to ``1.0``
            over the result set (the personalisation vector sums
            to ``1.0`` and PPR preserves L1 mass).
        rank: 1-based rank within the returned top-k (1 = highest).
            The rank is what :class:`KGRRFFusion` consumes when
            computing the per-fact RRF contribution.
    """

    entity_id: uuid.UUID
    entity_name: str
    entity_type: str
    score: float
    rank: int


# ---------------------------------------------------------------------------
# Personalized PageRank
# ---------------------------------------------------------------------------


class PersonalizedPageRank:
    """PPR scoring for KG entities given a seed set.

    Args:
        session_factory: Callable that returns a fresh async session
            (typically ``guinevere.memory.db.get_async_session``).  Required
            — the PPR scorer must reach the KG edges table.
        damping: Probability of *following an edge* at each step.
            Higher damping → walks are longer → scores spread
            further.  Defaults to the literature standard of 0.85.
        max_iterations: Hard ceiling on power iterations.  Typical
            convergence is in < 20 iterations; the ceiling guards
            against pathological graphs.
        tolerance: L1 early-exit threshold.  When
            ``||p_{t+1} - p_t||_1 < tolerance`` we stop and return.

    Example::

        ppr = PersonalizedPageRank(
            session_factory=guinevere.memory.db.get_async_session,
            damping=0.85,
        )
        top = await ppr.compute(seed_entity_ids=[seed], top_k=50)
    """

    def __init__(
        self,
        session_factory: SessionFactory,
        *,
        damping: float = 0.85,
        max_iterations: int = 20,
        tolerance: float = 1e-6,
    ) -> None:
        if not 0.0 < damping < 1.0:
            raise ValueError(
                f"damping must be in (0.0, 1.0); got {damping}",
            )
        if max_iterations < 1:
            raise ValueError(
                f"max_iterations must be >= 1; got {max_iterations}",
            )
        if tolerance <= 0.0:
            raise ValueError(
                f"tolerance must be > 0.0; got {tolerance}",
            )

        self._damping: float = damping
        self._max_iterations: int = max_iterations
        self._tolerance: float = tolerance
        self._repo: KGRepository = KGRepository(session_factory)
        self._metrics: KGMetrics = KGMetrics.get_instance()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def compute(
        self,
        seed_entity_ids: Sequence[uuid.UUID],
        *,
        top_k: int = 50,
        project_id: uuid.UUID | None = None,
    ) -> list[PPRResult]:
        """Compute PPR scores for entities reachable from ``seed_entity_ids``.

        Steps:

        1. Load the active (non-tombstoned) edge set into an
           in-process adjacency map (single SQL ``SELECT``).
        2. Build the personalisation vector ``v`` —
           ``v[s] = 1 / |seeds|`` for each seed, ``v[i] = 0``
           otherwise.
        3. Initialise the score vector ``p = v``.
        4. Iterate ``p_{t+1} = damping * M^T * p_t + (1 - damping) * v``,
           redistributing dangling-node mass through ``v`` after each
           step (Page et al. convention).
        5. Early-exit when ``||p_{t+1} - p_t||_1 < tolerance``.
        6. Fetch display names + taxonomy types for the top-``k``
           entities in a single follow-up ``SELECT``.
        7. Return the top-``k`` :class:`PPRResult` rows.

        When ``project_id`` is provided, the adjacency is scoped to
        edges whose ``project_id == project_id OR project_scope == 'global'``.
        This prevents PPR from walking across project boundaries
        (DATA-04 isolation).

        Args:
            seed_entity_ids: One or more seed entity UUIDs.  An
                empty sequence returns an empty list (PPR is undefined
                without at least one teleport target).
            top_k: Maximum number of :class:`PPRResult` rows to
                return.  Capped at 200 — callers needing more should
                fetch the full vector and slice downstream.
            project_id: When set, scope the adjacency load to edges
                in the given project namespace.

        Returns:
            A list of :class:`PPRResult` ordered by score descending,
            then by ``entity_id`` ascending (deterministic tie-break).

        Raises:
            KGQueryError: Database error during adjacency load.
            ValueError: ``seed_entity_ids`` is empty, ``top_k`` < 1,
                or ``top_k`` exceeds the safety ceiling.
        """
        if not seed_entity_ids:
            return []
        if top_k < 1:
            raise ValueError(f"top_k must be >= 1; got {top_k}")
        effective_top_k = min(top_k, 200)

        seed_set: set[uuid.UUID] = {uuid.UUID(str(s)) for s in seed_entity_ids}

        ctx = KGLogContext(operation="kg_ppr_compute")
        start = time.perf_counter()

        try:
            adjacency, out_degree = await self._load_adjacency(
                project_id=project_id,
            )
        except Exception as exc:  # noqa: BLE001 — narrowed below
            raise KGQueryError(
                "PPR adjacency load failed",
                context={
                    "seed_count": len(seed_set),
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:200],
                },
            ) from exc

        p, iterations = self._power_iterate(
            adjacency=adjacency,
            out_degree=out_degree,
            seed_set=seed_set,
        )

        top_nodes = self._top_nodes(p=p, top_k=effective_top_k)
        if not top_nodes:
            duration = time.perf_counter() - start
            self._metrics.observe_query_duration(
                query_type="ppr_compute",
                hop_count=iterations,
                duration=duration,
            )
            ctx.duration_ms = duration * 1000.0
            ctx.result_count = 0
            ctx.hop_count = iterations
            log_kg_operation(logger, ctx)
            return []

        try:
            entity_meta = await self._load_entity_metadata([n for n, _ in top_nodes])
        except Exception as exc:  # noqa: BLE001 — narrowed below
            raise KGQueryError(
                "PPR entity metadata lookup failed",
                context={
                    "entity_count": len(top_nodes),
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:200],
                },
            ) from exc

        results = self._build_results(
            top_nodes=top_nodes,
            entity_meta=entity_meta,
        )

        duration = time.perf_counter() - start
        self._metrics.observe_query_duration(
            query_type="ppr_compute",
            hop_count=iterations,
            duration=duration,
        )
        ctx.duration_ms = duration * 1000.0
        ctx.result_count = len(results)
        ctx.hop_count = iterations
        log_kg_operation(logger, ctx)

        return results

    async def compute_from_query(
        self,
        query_text: str,
        *,
        top_k: int = 50,
    ) -> list[PPRResult]:
        """PPR from entities matched by ``query_text``.

        Implementation:

        1. Use :meth:`KGQueryEngine.search_entities` style ILIKE scan
           (inlined here so this class stays free of an engine
           dependency) to get the top matching entities (default
           cap = 10).
        2. Use those entities as seeds for :meth:`compute`.
        3. Return the PPR-ranked list.

        Args:
            query_text: Free-text query — typically the same query
                the recall pipeline is fusing over.
            top_k: Forwarded to :meth:`compute`.

        Returns:
            A list of :class:`PPRResult`.  Empty when the query
            resolves to no entities (which is not an error).

        Raises:
            KGQueryError: When the underlying search fails.
        """
        if not (query_text or "").strip():
            return []
        seeds = await self._search_seed_entities(query_text, limit=10)
        if not seeds:
            return []
        return await self.compute(seeds, top_k=top_k)

    # ------------------------------------------------------------------
    # Internal: adjacency load
    # ------------------------------------------------------------------

    async def _load_adjacency(
        self,
        *,
        project_id: uuid.UUID | None = None,
    ) -> tuple[dict[uuid.UUID, list[uuid.UUID]], dict[uuid.UUID, int]]:
        """Load the active edge set into an adjacency map.

        When ``project_id`` is provided, only edges whose
        ``project_id == project_id OR project_scope == 'global'``
        are included.  This prevents PPR from walking across project
        boundaries (DATA-04 isolation).

        Loads the *full* active (non-tombstoned) edge set within the
        requested scope.  For the M0-M2 scope (< 100 k entities) this
        is bounded; for P17+ the load would page by 2-hop neighbourhood
        around the seeds.

        Args:
            project_id: When set, scope the adjacency to edges in the
                given project namespace.  ``None`` (default) = no
                project filter (legacy global behavior).

        Returns:
            A tuple ``(adjacency, out_degree)`` where:

            * ``adjacency[u]`` is the list of v such that ``u → v``
              is an active, non-tombstoned edge.
            * ``out_degree[u]`` is ``len(adjacency.get(u, []))``.
              Dangling nodes (no outgoing edges) are still inserted
              with ``out_degree=0`` so the iteration can redistribute
              their mass correctly.
        """
        project_clause = ""
        if project_id is not None:
            project_clause = (
                "AND (project_id = CAST(:project_id AS uuid) "
                "OR project_scope = 'global')"
            )
        sql = f"""
        SELECT DISTINCT ON (src_entity_id, dst_entity_id)
            src_entity_id,
            dst_entity_id
        FROM memory.kg_edges
        WHERE is_tombstoned = FALSE
              {project_clause}
        ORDER BY src_entity_id, dst_entity_id, recorded_at DESC
        """
        adjacency: dict[uuid.UUID, list[uuid.UUID]] = {}
        out_degree: dict[uuid.UUID, int] = {}
        params: dict[str, object] = {}
        if project_id is not None:
            params["project_id"] = project_id
        async with self._repo.get_session() as session:
            from sqlalchemy import text as _sa_text
            result = await session.execute(_sa_text(sql), params)
            rows = list(result.fetchall())
        for row in rows:
            src = row.src_entity_id
            dst = row.dst_entity_id
            if isinstance(src, str):
                src = uuid.UUID(src)
            if isinstance(dst, str):
                dst = uuid.UUID(dst)
            adjacency.setdefault(src, []).append(dst)
            out_degree[src] = out_degree.get(src, 0) + 1
            out_degree.setdefault(dst, out_degree.get(dst, 0))
        return adjacency, out_degree

    # ------------------------------------------------------------------
    # Internal: entity metadata + search
    # ------------------------------------------------------------------

    async def _load_entity_metadata(
        self,
        entity_ids: Sequence[uuid.UUID],
    ) -> dict[uuid.UUID, tuple[str, str]]:
        """Fetch ``(display_name, entity_type)`` for ``entity_ids``.

        Returns:
            ``{entity_id: (display_name, entity_type)}`` — missing
            entities simply do not appear in the mapping (the caller
            falls back to ``"<unknown>"`` / ``"unknown"``).
        """
        if not entity_ids:
            return {}
        sql = """
        SELECT id, display_name, entity_type
        FROM memory.kg_entities
        WHERE is_tombstoned = FALSE
          AND id = ANY(CAST(:entity_ids AS uuid[]))
        """
        params: dict[str, object] = {
            "entity_ids": [str(e) for e in entity_ids],
        }
        out: dict[uuid.UUID, tuple[str, str]] = {}
        async with self._repo.get_session() as session:
            from sqlalchemy import text as _sa_text
            result = await session.execute(_sa_text(sql), params)
            rows = list(result.fetchall())
        for row in rows:
            raw_id = row.id
            if isinstance(raw_id, str):
                raw_id = uuid.UUID(raw_id)
            out[raw_id] = (str(row.display_name), str(row.entity_type))
        return out

    async def _search_seed_entities(
        self,
        query_text: str,
        *,
        limit: int = 10,
    ) -> list[uuid.UUID]:
        """Resolve ``query_text`` into seed entity UUIDs.

        Mirrors the heuristic used by :meth:`KGQueryEngine.search_entities`
        so :meth:`compute_from_query` does not need an engine
        dependency.  ILIKE pattern is escaped with ``\\`` — the same
        convention :class:`KGQueryEngine` uses.
        """
        normalized = (query_text or "").strip()
        if not normalized:
            return []
        like_pattern = f"%{_escape_like(normalized)}%"
        sql = """
        SELECT id
        FROM memory.kg_entities
        WHERE is_tombstoned = FALSE
          AND (
                display_name ILIKE :pattern ESCAPE '\\'
             OR EXISTS (
                  SELECT 1 FROM unnest(aliases) AS a
                  WHERE a ILIKE :pattern ESCAPE '\\'
             )
             OR description ILIKE :pattern ESCAPE '\\'
          )
        ORDER BY length(display_name) ASC
        LIMIT :limit
        """
        params: dict[str, object] = {"pattern": like_pattern, "limit": limit}
        ids: list[uuid.UUID] = []
        async with self._repo.get_session() as session:
            from sqlalchemy import text as _sa_text
            result = await session.execute(_sa_text(sql), params)
            rows = list(result.fetchall())
        for row in rows:
            raw = row.id
            if isinstance(raw, str):
                raw = uuid.UUID(raw)
            ids.append(raw)
        return ids

    # ------------------------------------------------------------------
    # Internal: power iteration
    # ------------------------------------------------------------------

    def _power_iterate(
        self,
        *,
        adjacency: dict[uuid.UUID, list[uuid.UUID]],
        out_degree: dict[uuid.UUID, int],
        seed_set: set[uuid.UUID],
    ) -> tuple[dict[uuid.UUID, float], int]:
        """Run power iteration until convergence or ceiling.

        Args:
            adjacency: Outgoing adjacency from :meth:`_load_adjacency`.
            out_degree: Out-degree of every node in ``adjacency``.
            seed_set: Seed UUIDs.

        Returns:
            ``(scores, iterations)`` where ``scores`` is the converged
            PPR vector and ``iterations`` is the count actually used.
        """
        all_nodes: set[uuid.UUID] = set(adjacency.keys()) | set(out_degree.keys())
        if not all_nodes:
            return {}, 0

        # Personalisation vector: uniform over seeds, zero elsewhere.
        seed_count = len(seed_set)
        teleport: dict[uuid.UUID, float] = {
            node: (1.0 / seed_count if node in seed_set else 0.0)
            for node in all_nodes
        }
        # Initialise the score vector to the personalisation vector.
        scores: dict[uuid.UUID, float] = dict(teleport)

        # Power iteration.
        damping = self._damping
        one_minus_damping = 1.0 - damping
        iterations_used = 0
        for iteration in range(1, self._max_iterations + 1):
            iterations_used = iteration
            new_scores: dict[uuid.UUID, float] = {}
            dangling_mass = 0.0
            # First pass: compute the random-walk contribution and
            # accumulate dangling mass (sum of scores at nodes with
            # out_degree 0).
            for node in all_nodes:
                old_score = scores.get(node, 0.0)
                degree = out_degree.get(node, 0)
                if degree == 0:
                    dangling_mass += old_score
                else:
                    share = old_score / degree
                    neighbours = adjacency.get(node, ())
                    for nbr in neighbours:
                        new_scores[nbr] = new_scores.get(nbr, 0.0) + share
            # Apply damping and re-inject dangling mass via teleport.
            for node in all_nodes:
                random_walk = damping * new_scores.get(node, 0.0)
                teleport_part = one_minus_damping * teleport.get(node, 0.0)
                # Dangling mass flows entirely through teleport: at
                # each step the walker would restart from a seed.
                dangling_part = damping * dangling_mass * teleport.get(node, 0.0)
                new_scores[node] = random_walk + teleport_part + dangling_part
            # L1 delta for convergence check.
            delta = 0.0
            for node in all_nodes:
                delta += abs(new_scores.get(node, 0.0) - scores.get(node, 0.0))
            scores = new_scores
            if delta < self._tolerance:
                break
        return scores, iterations_used

    # ------------------------------------------------------------------
    # Internal: top-k extraction + result assembly
    # ------------------------------------------------------------------

    @staticmethod
    def _top_nodes(
        *,
        p: dict[uuid.UUID, float],
        top_k: int,
    ) -> list[tuple[uuid.UUID, float]]:
        """Return ``[(entity_id, score), ...]`` for the top-``k`` nodes.

        Drops zero-score nodes so the follow-up metadata lookup is
        bounded.  Sort is by score descending then entity_id ascending
        for deterministic tie-breaks.
        """
        scored = [(node, score) for node, score in p.items() if score > 0.0]
        scored.sort(key=lambda pair: (-pair[1], str(pair[0])))
        return scored[:top_k]

    @staticmethod
    def _build_results(
        *,
        top_nodes: list[tuple[uuid.UUID, float]],
        entity_meta: dict[uuid.UUID, tuple[str, str]],
    ) -> list[PPRResult]:
        """Assemble :class:`PPRResult` rows from scores + metadata.

        Entities missing from ``entity_meta`` (tombstoned between
        PPR iteration and the lookup, or simply not in the table)
        fall back to ``"<unknown>"`` for the name and ``"unknown"``
        for the type — they are still scored so the downstream
        fusion can decide what to do with them.
        """
        results: list[PPRResult] = []
        for rank_idx, (node, score) in enumerate(top_nodes, start=1):
            name, etype = entity_meta.get(node, ("<unknown>", "unknown"))
            results.append(
                PPRResult(
                    entity_id=node,
                    entity_name=name,
                    entity_type=etype,
                    score=float(score),
                    rank=rank_idx,
                ),
            )
        return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _escape_like(value: str) -> str:
    """Escape SQL ``LIKE``-special characters in a user-supplied string.

    Mirrors the helper in :mod:`guinevere.knowledge_graph.query.engine` —
    keeps the wildcards the user types from inflating the result set.
    """
    return (
        value.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "PPRResult",
    "PersonalizedPageRank",
]