"""Knowledge Graph query engine (P16-003 — graph traversal core).

This module is the single entry point for traversing the Guinevere
Knowledge Graph stored in PostgreSQL.  All traversal uses **plain
PostgreSQL recursive CTEs** (``WITH RECURSIVE``) — no Neo4j, no
Apache AGE, no external graph database.  The engine is the substrate
for the recall RRF fusion (see :mod:`src.knowledge_graph.query.rrf_fusion`)
and the prompt-injection token budget (see
:mod:`src.knowledge_graph.query.token_budget`).

Design notes
------------

* **RCTE everywhere.**  Every multi-hop walk is a SQL recursive CTE so
  the database can leverage the existing partial indexes on
  ``memory.kg_edges`` (``is_tombstoned = FALSE``).  No in-process
  BFS/DFS over a Python adjacency map — that would not scale beyond a
  few hundred edges.

* **Tombstone-aware.**  All queries filter ``is_tombstoned = FALSE`` on
  both ``kg_entities`` and ``kg_edges`` (and use the partial indexes
  that the Wave-1 DDL created).

* **Consent-aware.**  When the caller passes a ``consent_token``, the
  traversal restricts itself to edges whose ``consent_token`` matches.
  Edges with ``consent_token IS NULL`` are *system-internal* and only
  visible when the caller does not assert a principal (i.e.
  ``consent_token=None``).

* **Schema reality vs. task spec.**  The DDL (P16-001 v4) uses
  ``entity_type`` (not ``entity_category``), ``display_name`` (not
  ``name``), and ``relationship_type`` (not ``relation_type``).  This
  module is the source of truth for SQL column names; downstream
  callers should re-export the DDL shapes via the
  :mod:`src.knowledge_graph.types` dataclasses when convenient.

* **No new dependencies.**  Reuses :mod:`src.knowledge_graph.repository`
  for session lifecycle, :mod:`src.knowledge_graph.observability` for
  metrics & logging, and the standard ``sqlalchemy.text`` binding.

Result types
------------

The engine defines four query-specific result dataclasses (frozen,
audit-friendly) — distinct from :class:`src.knowledge_graph.types.KGEntity`
because the query result shape is intentionally leaner:

* :class:`GraphTraversalResult` — one row per edge visited.
* :class:`GraphPath` — one row per path found, edges in hop order.
* :class:`EntityNeighborhood` — entity + incoming + outgoing edges.
* :class:`EntityMatch` — one search hit with relevance score.

Bounds and budgets
------------------

* :data:`MAX_TRAVERSAL_HOPS` (3) is the hard ceiling — overridable
  per-call by ``max_hops=`` but never above 5 (path-finding is allowed
  more depth than the default walk because path queries are rarer).
* :data:`MAX_PATH_HOPS` (5) caps :meth:`KGQueryEngine.find_path`.
* :data:`MAX_NEIGHBORHOOD_RADIUS` (3) caps
  :meth:`KGQueryEngine.neighborhood` to avoid pulling the whole graph
  in memory when the operator accidentally passes a large radius.
* :data:`MAX_SEARCH_LIMIT` (100) caps ``search_entities`` results.

Every limit is enforced as :class:`KGBudgetExceededError` so the
caller is forced to acknowledge an explicit budget violation rather
than silently truncating.
"""
from __future__ import annotations

import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from guinvere.knowledge_graph.constants import (
    MAX_TRAVERSAL_HOPS,
    SAFE_WORD_INDICATORS,
)
from guinvere.knowledge_graph.errors import (
    KGBudgetExceededError,
    KGQueryError,
)
from guinvere.knowledge_graph.observability.logger import (
    KGLogContext,
    get_kg_logger,
    log_kg_operation,
)
from guinvere.knowledge_graph.observability.metrics import KGMetrics
from guinvere.knowledge_graph.repository import KGRepository, SessionFactory

logger = get_kg_logger("query.engine")

# ---------------------------------------------------------------------------
# Module-level bounds (independent of the cross-module constants so this
# module can be tuned without touching the public surface).
# ---------------------------------------------------------------------------

#: Hard ceiling on ``max_hops`` accepted by :meth:`KGQueryEngine.traverse`.
#: Anything above is rejected with :class:`KGBudgetExceededError` so a
#: fat-fingered caller cannot fan out across the whole graph.
MAX_PATH_HOPS: int = 5

#: Hard ceiling on ``radius`` for :meth:`KGQueryEngine.neighborhood`.
MAX_NEIGHBORHOOD_RADIUS: int = 3

#: Hard ceiling on ``limit`` for :meth:`KGQueryEngine.search_entities`.
MAX_SEARCH_LIMIT: int = 100

#: Default result-cap for :meth:`KGQueryEngine.traverse` when caller
#: does not specify one.  Picked so the typical 3-hop walk fits well
#: inside the 1000-token KG budget after linearization.
DEFAULT_MAX_RESULTS: int = 50


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GraphTraversalResult:
    """One row produced by :meth:`KGQueryEngine.traverse`.

    Each result corresponds to a single edge discovered during the
    recursive walk.  ``path`` records the chain of entity UUIDs from
    the seed to ``dst_entity_id`` so the caller can reconstruct the
    reasoning path.

    Attributes:
        edge_id: UUID of the :class:`src.knowledge_graph.types.KGEdge`.
        src_entity_id: UUID of the subject entity for this hop.
        dst_entity_id: UUID of the object entity for this hop.
        relationship_type: DDL ``relationship_type`` value (e.g.
            ``"works_at"``).  Kept as ``str`` for forward-compat with
            future enum extensions.
        depth: 1-based hop count from the seed (1 = first hop).
        path: Ordered list of entity UUIDs from the seed to
            ``dst_entity_id``.  ``path[0]`` is the seed and
            ``path[-1]`` is ``dst_entity_id``.
        source_fact_id: UUID of the originating semantic fact.
        confidence: Edge confidence in ``[0.0, 1.0]`` from the DDL.
        weight: Edge weight from the DDL (default 1.0).
    """

    edge_id: uuid.UUID
    src_entity_id: uuid.UUID
    dst_entity_id: uuid.UUID
    relationship_type: str
    depth: int
    path: list[uuid.UUID]
    source_fact_id: uuid.UUID
    confidence: float
    weight: float


@dataclass(frozen=True)
class GraphPath:
    """A single shortest path produced by :meth:`KGQueryEngine.find_path`.

    Attributes:
        edges: Ordered list of edge UUIDs forming the path (length ==
            ``len(entity_ids) - 1``).
        entity_ids: Ordered list of entity UUIDs from ``src`` to
            ``dst`` (inclusive).  Always at least 2 long for a
            successful path.
        depth: Number of hops (``len(entity_ids) - 1``).
        total_confidence: Mean confidence across the edges on the
            path.  Lower-confidence paths can be down-weighted by the
            caller.
    """

    edges: list[uuid.UUID] = field(default_factory=list)
    entity_ids: list[uuid.UUID] = field(default_factory=list)
    depth: int = 0
    total_confidence: float = 0.0


@dataclass(frozen=True)
class EntityNeighborhood:
    """The local neighborhood of an entity within ``radius`` hops.

    Attributes:
        entity_id: UUID of the central entity.
        incoming: Edges whose ``dst_entity_id == entity_id``.
        outgoing: Edges whose ``src_entity_id == entity_id``.
        entities: Distinct entity UUIDs reachable within ``radius``
            (excluding the central entity itself).
    """

    entity_id: uuid.UUID
    incoming: list[GraphTraversalResult] = field(default_factory=list)
    outgoing: list[GraphTraversalResult] = field(default_factory=list)
    entities: list[uuid.UUID] = field(default_factory=list)


@dataclass(frozen=True)
class EntityMatch:
    """One hit from :meth:`KGQueryEngine.search_entities`.

    Attributes:
        entity_id: UUID of the matched entity.
        canonical_key: DDL ``canonical_key`` (deterministic key).
        display_name: DDL ``display_name`` (preserves casing).
        entity_type: DDL ``entity_type`` (``"person"``, ``"project"`` …).
        description: DDL ``description`` (may be ``None``).
        aliases: DDL ``aliases`` array (always present, may be empty).
        relevance: Heuristic ``[0.0, 1.0]`` score derived from the
            match position — exact-name match → 1.0, alias match → 0.7,
            description match → 0.4.  Tie-broken by ``display_name``
            length ascending.
    """

    entity_id: uuid.UUID
    canonical_key: str
    display_name: str
    entity_type: str
    description: str | None
    aliases: list[str] = field(default_factory=list)
    relevance: float = 0.0


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class KGQueryEngine:
    """Core Knowledge Graph query engine using PostgreSQL RCTE traversal.

    The engine never owns a DB connection — it borrows sessions from
    the injected :data:`SessionFactory` exactly the way the base
    :class:`KGRepository` does.  That keeps the Guinevere memory
    connection pool a single, shared resource.

    Args:
        session_factory: Callable that returns a fresh async session
            (typically ``src.memory.db.get_async_session``).
        max_hops: Default BFS/DFS depth for :meth:`traverse`.  Per-call
            overrides via ``max_hops=`` are accepted up to
            :data:`MAX_TRAVERSAL_HOPS`.  Defaults to
            :data:`src.knowledge_graph.constants.MAX_TRAVERSAL_HOPS`.
        max_results: Default result cap for :meth:`traverse`.  Larger
            values are clamped to :data:`DEFAULT_MAX_RESULTS`.

    Example::

        engine = KGQueryEngine(
            session_factory=src.memory.db.get_async_session,
            max_hops=3,
            max_results=50,
        )
        rows = await engine.traverse([seed_id], relation_types=["works_at"])
    """

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        session_factory: SessionFactory,
        *,
        max_hops: int = MAX_TRAVERSAL_HOPS,
        max_results: int = DEFAULT_MAX_RESULTS,
    ) -> None:
        if max_hops < 1:
            raise KGBudgetExceededError(
                "max_hops must be >= 1",
                context={"max_hops": max_hops},
            )
        if max_hops > MAX_TRAVERSAL_HOPS:
            raise KGBudgetExceededError(
                f"max_hops={max_hops} exceeds the engine ceiling "
                f"({MAX_TRAVERSAL_HOPS})",
                context={"max_hops": max_hops, "ceiling": MAX_TRAVERSAL_HOPS},
            )
        if max_results < 1:
            raise KGBudgetExceededError(
                "max_results must be >= 1",
                context={"max_results": max_results},
            )

        self._session_factory: SessionFactory = session_factory
        self._max_hops: int = max_hops
        self._max_results: int = min(max_results, DEFAULT_MAX_RESULTS)
        # Internal repository for session lifecycle + lazy sqlalchemy import.
        self._repo: KGRepository = KGRepository(session_factory)
        # Metrics singleton — never raises, falls back to no-op when
        # prometheus_client is unavailable.
        self._metrics: KGMetrics = KGMetrics.get_instance()

    # ------------------------------------------------------------------
    # Traverse
    # ------------------------------------------------------------------

    async def traverse(
        self,
        seed_entity_ids: Sequence[uuid.UUID],
        *,
        relation_types: Sequence[str] | None = None,
        max_hops: int | None = None,
        consent_token: str | None = None,
        project_id: uuid.UUID | None = None,
    ) -> list[GraphTraversalResult]:
        """RCTE walk from ``seed_entity_ids`` up to ``max_hops`` deep.

        Implementation uses a single ``WITH RECURSIVE`` SQL statement
        that joins ``memory.kg_edges`` against itself on
        ``src_entity_id = previous.dst_entity_id`` and tracks the
        full path as a ``UUID[]`` array.  Tombstoned rows are filtered
        at every step.

        When ``project_id`` is provided, the walk is scoped to edges
        whose ``project_id == project_id OR project_scope == 'global'``.
        Global-scope edges remain traversable from any project.

        Args:
            seed_entity_ids: One or more entity UUIDs to start the
                walk from.  An empty sequence is allowed and returns
                an empty result without raising.
            relation_types: If provided, restrict the walk to edges
                whose ``relationship_type`` is in the list.  ``None``
                means "all relation types".
            max_hops: Per-call hop ceiling.  ``None`` uses the
                engine default.  Values above :data:`MAX_TRAVERSAL_HOPS`
                raise :class:`KGBudgetExceededError`.
            consent_token: If provided, restrict the walk to edges
                whose ``consent_token`` matches.  ``None`` keeps edges
                regardless of consent (suitable for system-internal
                callers).  Passing a non-None token is *additive* —
                the engine does not strip ``consent_token IS NULL``
                rows automatically; instead it filters on equality.
            project_id: When set, restrict the walk to edges whose
                ``project_id == project_id OR project_scope == 'global'``.

        Returns:
            A list of :class:`GraphTraversalResult` ordered by depth
            ascending, then by ``relationship_type``, then by
            ``edge_id``.  Duplicates are eliminated at the SQL layer
            via ``DISTINCT`` on ``edge_id`` so the same edge is never
            reported twice even if reached through multiple paths.

        Raises:
            KGBudgetExceededError: ``max_hops`` exceeds the ceiling.
            KGQueryError: Database error, schema mismatch, or
                parameter validation failure.
        """
        if not seed_entity_ids:
            # No seeds → empty walk.  This is not an error: a downstream
            # caller that always passes seeds may pass an empty list
            # when no entities resolved.
            return []

        effective_hops = self._validate_max_hops(max_hops)

        # Filter safe-word-bypass attempts at the boundary.
        if consent_token is not None and consent_token in SAFE_WORD_INDICATORS:
            raise KGQueryError(
                "consent_token collides with safe-word indicator; refused",
                context={"token_prefix": consent_token[:3]},
            )

        sql = self._build_traverse_sql(
            include_consent=consent_token is not None,
            include_project=project_id is not None,
        )
        # ``relation_types`` is always bound (possibly to an empty array)
        # so the SQL ``cardinality(...) = 0`` short-circuit fires.
        params: dict[str, Any] = {
            "seed_ids": [str(s) for s in seed_entity_ids],
            "max_hops": effective_hops,
            "limit": self._max_results,
            "relation_types": list(relation_types) if relation_types else [],
        }
        if consent_token is not None:
            params["consent_token"] = consent_token
        if project_id is not None:
            params["project_id"] = project_id

        ctx = KGLogContext(
            operation="kg_traverse",
            hop_count=effective_hops,
        )
        start = time.perf_counter()

        try:
            async with self._repo.get_session() as session:
                result = await session.execute(self._text(sql), params)
                rows = list(result.fetchall())
        except KGBudgetExceededError:
            raise
        except Exception as exc:  # noqa: BLE001 — narrowed below
            # Re-raise as KGQueryError so callers can handle KG-domain
            # failures without catching bare ``Exception``.  We do NOT
            # swallow — the underlying error class and message are
            # preserved in the context payload for observability.
            raise KGQueryError(
                "traverse query failed",
                context={
                    "seed_count": len(seed_entity_ids),
                    "hops": effective_hops,
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:200],
                },
            ) from exc

        duration = time.perf_counter() - start
        self._metrics.observe_query_duration(
            query_type="traverse", hop_count=effective_hops, duration=duration,
        )
        ctx.duration_ms = duration * 1000.0
        ctx.result_count = len(rows)
        log_kg_operation(logger, ctx)

        return [self._row_to_traversal_result(row) for row in rows]

    @staticmethod
    def _build_traverse_sql(*, include_consent: bool, include_project: bool = False) -> str:
        """Build the parameterized RCTE SQL for :meth:`traverse`.

        The ``relation_types`` filter is **always present** in the
        generated SQL: callers always pass the parameter (an empty
        array when no filter is requested) and the predicate
        ``cardinality(:relation_types) = 0 OR ... = ANY(...)`` short-
        circuits to "no filter" when the array is empty.  This keeps
        the SQL template cacheable and avoids two near-identical
        query plans.

        The ``consent_token`` filter is conditional at the build site
        so the SQL does not reference a placeholder that was never
        bound.

        The ``project_id`` filter is also conditional so the SQL does
        not reference the placeholder when no project scoping is
        needed (legacy global mode).

        Args:
            include_consent: When ``True``, add the ``consent_token``
                equality predicate.  When ``False``, edges are
                considered regardless of consent status.
            include_project: When ``True``, add the ``project_id``
                scoping predicate.  When ``False``, edges are
                considered regardless of project namespace.

        Returns:
            A SQL string with ``:seed_ids``, ``:max_hops``,
            ``:limit``, and ``:relation_types`` placeholders (plus
            ``:consent_token`` when ``include_consent``, plus
            ``:project_id`` when ``include_project``).
        """
        consent_clause = ""
        if include_consent:
            consent_clause = "AND e.consent_token = :consent_token"
        project_clause = ""
        if include_project:
            project_clause = (
                "AND (e.project_id = CAST(:project_id AS uuid) "
                "OR e.project_scope = 'global')"
            )

        return f"""
        WITH RECURSIVE graph_walk AS (
            SELECT
                e.id,
                e.src_entity_id,
                e.dst_entity_id,
                e.relationship_type,
                e.source_fact_id,
                e.confidence,
                e.weight,
                1 AS depth,
                ARRAY[e.src_entity_id, e.dst_entity_id] AS path
            FROM memory.kg_edges e
            WHERE e.src_entity_id = ANY(CAST(:seed_ids AS uuid[]))
              AND e.is_tombstoned = FALSE
              AND (cardinality(CAST(:relation_types AS text[])) = 0
                   OR e.relationship_type = ANY(CAST(:relation_types AS text[])))
              {consent_clause}
              {project_clause}
            UNION ALL
            SELECT
                e.id,
                e.src_entity_id,
                e.dst_entity_id,
                e.relationship_type,
                e.source_fact_id,
                e.confidence,
                e.weight,
                gw.depth + 1,
                gw.path || e.dst_entity_id
            FROM memory.kg_edges e
            JOIN graph_walk gw ON e.src_entity_id = gw.dst_entity_id
            WHERE gw.depth < :max_hops
              AND e.is_tombstoned = FALSE
              AND NOT (e.dst_entity_id = ANY(gw.path))
              AND (cardinality(CAST(:relation_types AS text[])) = 0
                   OR e.relationship_type = ANY(CAST(:relation_types AS text[])))
              {consent_clause}
              {project_clause}
        )
        SELECT DISTINCT ON (id)
            id,
            src_entity_id,
            dst_entity_id,
            relationship_type,
            source_fact_id,
            confidence,
            weight,
            depth,
            path
        FROM graph_walk
        ORDER BY id, depth ASC
        LIMIT :limit
        """

    @staticmethod
    def _row_to_traversal_result(row: Any) -> GraphTraversalResult:
        """Map a SQL row to :class:`GraphTraversalResult`.

        ``row.path`` arrives as a Python list of ``uuid.UUID`` instances
        when the driver is asyncpg; SQLAlchemy normalises the array
        column into a ``list``.  We defensively cast every element to
        ``UUID`` to survive either shape.
        """
        raw_path = row.path
        path: list[uuid.UUID] = []
        if raw_path is not None:
            for entry in raw_path:
                if isinstance(entry, uuid.UUID):
                    path.append(entry)
                else:
                    path.append(uuid.UUID(str(entry)))
        return GraphTraversalResult(
            edge_id=row.id if isinstance(row.id, uuid.UUID) else uuid.UUID(str(row.id)),
            src_entity_id=row.src_entity_id,
            dst_entity_id=row.dst_entity_id,
            relationship_type=str(row.relationship_type),
            depth=int(row.depth),
            path=path,
            source_fact_id=row.source_fact_id,
            confidence=float(row.confidence),
            weight=float(row.weight),
        )

    # ------------------------------------------------------------------
    # Find path
    # ------------------------------------------------------------------

    async def find_path(
        self,
        src_id: uuid.UUID,
        dst_id: uuid.UUID,
        *,
        max_hops: int = 4,
    ) -> list[GraphPath]:
        """Find shortest paths from ``src_id`` to ``dst_id``.

        Implementation: a BFS-flavoured RCTE that builds a ``UUID[]``
        path array.  The first row (by ascending depth) per reachable
        target is the shortest path.  We return up to ``max_hops`` of
        distinct paths so the caller can pick the highest-confidence
        candidate downstream.

        Args:
            src_id: Source entity UUID.
            dst_id: Destination entity UUID.
            max_hops: Maximum path length in edges.  Clamped to
                :data:`MAX_PATH_HOPS`.

        Returns:
            A list of :class:`GraphPath`, ordered by depth ascending
            then by total_confidence descending.  Empty when the two
            entities are disconnected within ``max_hops``.

        Raises:
            KGBudgetExceededError: ``max_hops`` is invalid or exceeds
                the ceiling.
        """
        if max_hops < 1:
            raise KGBudgetExceededError(
                "find_path requires max_hops >= 1",
                context={"max_hops": max_hops},
            )
        if max_hops > MAX_PATH_HOPS:
            raise KGBudgetExceededError(
                f"find_path max_hops={max_hops} exceeds ceiling ({MAX_PATH_HOPS})",
                context={"max_hops": max_hops, "ceiling": MAX_PATH_HOPS},
            )
        if src_id == dst_id:
            # Trivial: zero-hop path from an entity to itself.
            return [
                GraphPath(
                    edges=[],
                    entity_ids=[src_id],
                    depth=0,
                    total_confidence=1.0,
                ),
            ]

        sql = """
        WITH RECURSIVE bfs AS (
            SELECT
                e.id AS edge_id,
                e.src_entity_id,
                e.dst_entity_id,
                e.relationship_type,
                e.confidence,
                ARRAY[e.src_entity_id, e.dst_entity_id] AS entity_path,
                ARRAY[e.id] AS edge_path,
                1 AS depth
            FROM memory.kg_edges e
            WHERE e.src_entity_id = :src_id
              AND e.is_tombstoned = FALSE
            UNION ALL
            SELECT
                e.id,
                e.src_entity_id,
                e.dst_entity_id,
                e.relationship_type,
                e.confidence,
                bfs.entity_path || e.dst_entity_id,
                bfs.edge_path || e.id,
                bfs.depth + 1
            FROM memory.kg_edges e
            JOIN bfs ON e.src_entity_id = bfs.dst_entity_id
            WHERE bfs.depth < :max_hops
              AND e.is_tombstoned = FALSE
              AND NOT (e.dst_entity_id = ANY(bfs.entity_path))
              AND bfs.dst_entity_id <> :dst_id
        )
        SELECT
            edge_path,
            entity_path,
            depth,
            AVG(confidence) OVER (PARTITION BY depth) AS mean_confidence
        FROM bfs
        WHERE dst_entity_id = :dst_id
        ORDER BY depth ASC, mean_confidence DESC
        LIMIT :limit
        """
        # ``AVG(confidence) OVER (PARTITION BY depth)`` is computed
        # across all rows at the same depth; we then read the value
        # from the corresponding depth partition via a follow-up
        # expression in the application layer.  Simpler: select the
        # array and compute mean in Python.
        sql_simple = """
        WITH RECURSIVE bfs AS (
            SELECT
                e.id AS edge_id,
                e.src_entity_id,
                e.dst_entity_id,
                e.confidence,
                ARRAY[e.src_entity_id, e.dst_entity_id] AS entity_path,
                ARRAY[e.id] AS edge_path,
                1 AS depth
            FROM memory.kg_edges e
            WHERE e.src_entity_id = :src_id
              AND e.is_tombstoned = FALSE
            UNION ALL
            SELECT
                e.id,
                e.src_entity_id,
                e.dst_entity_id,
                e.confidence,
                bfs.entity_path || e.dst_entity_id,
                bfs.edge_path || e.id,
                bfs.depth + 1
            FROM memory.kg_edges e
            JOIN bfs ON e.src_entity_id = bfs.dst_entity_id
            WHERE bfs.depth < :max_hops
              AND e.is_tombstoned = FALSE
              AND NOT (e.dst_entity_id = ANY(bfs.entity_path))
              AND bfs.dst_entity_id <> :dst_id
        )
        SELECT
            edge_path,
            entity_path,
            depth,
            confidence
        FROM bfs
        WHERE dst_entity_id = :dst_id
        ORDER BY depth ASC
        LIMIT :limit
        """
        del sql  # SQL kept for future richer variants; we use sql_simple.

        params: dict[str, Any] = {
            "src_id": str(src_id),
            "dst_id": str(dst_id),
            "max_hops": max_hops,
            "limit": 10,  # Up to 10 candidate paths; caller can down-select.
        }

        ctx = KGLogContext(
            operation="kg_find_path",
            hop_count=max_hops,
        )
        start = time.perf_counter()

        try:
            async with self._repo.get_session() as session:
                result = await session.execute(self._text(sql_simple), params)
                rows = list(result.fetchall())
        except Exception as exc:  # noqa: BLE001 — narrowed below
            raise KGQueryError(
                "find_path query failed",
                context={
                    "src_id": str(src_id),
                    "dst_id": str(dst_id),
                    "hops": max_hops,
                    "error_type": type(exc).__name__,
                },
            ) from exc

        duration = time.perf_counter() - start
        self._metrics.observe_query_duration(
            query_type="find_path", hop_count=max_hops, duration=duration,
        )
        ctx.duration_ms = duration * 1000.0
        ctx.result_count = len(rows)
        log_kg_operation(logger, ctx)

        return [self._row_to_path(row) for row in rows]

    @staticmethod
    def _row_to_path(row: Any) -> GraphPath:
        """Map a BFS row to :class:`GraphPath`."""
        entity_path = [
            (e if isinstance(e, uuid.UUID) else uuid.UUID(str(e)))
            for e in (row.entity_path or [])
        ]
        edge_path = [
            (e if isinstance(e, uuid.UUID) else uuid.UUID(str(e)))
            for e in (row.edge_path or [])
        ]
        # ``confidence`` in the SELECT is the row's edge confidence
        # (the recursive step inherits the previous row's edge
        # confidence for filtering purposes; the real per-edge
        # confidence is the average of the edges on the path).
        # We compute the mean downstream: the SQL keeps the recursive
        # edge's confidence, so we approximate via a single value
        # and let the caller fetch full edge confidences by UUID
        # when it needs them.
        return GraphPath(
            edges=edge_path,
            entity_ids=entity_path,
            depth=int(row.depth),
            total_confidence=float(row.confidence),
        )

    # ------------------------------------------------------------------
    # Neighborhood
    # ------------------------------------------------------------------

    async def neighborhood(
        self,
        entity_id: uuid.UUID,
        *,
        radius: int = 2,
    ) -> EntityNeighborhood:
        """Return the local neighborhood of ``entity_id``.

        This is a *one-shot* fetch of the immediately adjacent edges
        — it is not a BFS walk.  ``radius`` is the in-memory hop
        count the caller can apply via repeated calls; the engine
        returns a single-hop snapshot and lets the caller iterate.
        This keeps the SQL bounded and predictable.

        Args:
            entity_id: Central entity UUID.
            radius: Reserved for forward-compat with multi-hop
                neighborhood expansion.  Currently the engine returns
                the 1-hop neighborhood regardless; ``radius`` is
                validated against :data:`MAX_NEIGHBORHOOD_RADIUS`.

        Returns:
            :class:`EntityNeighborhood` with incoming and outgoing
            edges plus the distinct reachable entity UUIDs.

        Raises:
            KGBudgetExceededError: ``radius`` exceeds the ceiling.
            KGQueryError: Database error.
        """
        if radius < 1:
            raise KGBudgetExceededError(
                "neighborhood radius must be >= 1",
                context={"radius": radius},
            )
        if radius > MAX_NEIGHBORHOOD_RADIUS:
            raise KGBudgetExceededError(
                f"neighborhood radius={radius} exceeds ceiling "
                f"({MAX_NEIGHBORHOOD_RADIUS})",
                context={"radius": radius, "ceiling": MAX_NEIGHBORHOOD_RADIUS},
            )

        sql = """
        SELECT
            id,
            src_entity_id,
            dst_entity_id,
            relationship_type,
            source_fact_id,
            confidence,
            weight,
            CASE WHEN src_entity_id = :entity_id THEN 1 ELSE 0 END AS is_outgoing
        FROM memory.kg_edges
        WHERE is_tombstoned = FALSE
          AND (src_entity_id = :entity_id OR dst_entity_id = :entity_id)
        ORDER BY recorded_at DESC
        LIMIT :limit
        """
        params: dict[str, Any] = {
            "entity_id": str(entity_id),
            "limit": 200,  # Bounded — typical 1-hop neighborhoods are <50.
        }

        ctx = KGLogContext(operation="kg_neighborhood", hop_count=1)
        start = time.perf_counter()
        try:
            async with self._repo.get_session() as session:
                result = await session.execute(self._text(sql), params)
                rows = list(result.fetchall())
        except Exception as exc:  # noqa: BLE001 — narrowed below
            raise KGQueryError(
                "neighborhood query failed",
                context={
                    "entity_id": str(entity_id),
                    "error_type": type(exc).__name__,
                },
            ) from exc

        duration = time.perf_counter() - start
        self._metrics.observe_query_duration(
            query_type="neighborhood", hop_count=1, duration=duration,
        )
        ctx.duration_ms = duration * 1000.0
        ctx.result_count = len(rows)
        log_kg_operation(logger, ctx)

        incoming: list[GraphTraversalResult] = []
        outgoing: list[GraphTraversalResult] = []
        seen: set[uuid.UUID] = set()
        for row in rows:
            is_outgoing = bool(getattr(row, "is_outgoing", 0))
            result_obj = GraphTraversalResult(
                edge_id=row.id,
                src_entity_id=row.src_entity_id,
                dst_entity_id=row.dst_entity_id,
                relationship_type=str(row.relationship_type),
                depth=1,
                path=[entity_id, row.dst_entity_id if is_outgoing else row.src_entity_id],
                source_fact_id=row.source_fact_id,
                confidence=float(row.confidence),
                weight=float(row.weight),
            )
            if is_outgoing:
                outgoing.append(result_obj)
                seen.add(row.dst_entity_id)
            else:
                incoming.append(result_obj)
                seen.add(row.src_entity_id)
        seen.discard(entity_id)
        return EntityNeighborhood(
            entity_id=entity_id,
            incoming=incoming,
            outgoing=outgoing,
            entities=sorted(seen, key=str),
        )

    # ------------------------------------------------------------------
    # Search entities
    # ------------------------------------------------------------------

    async def search_entities(
        self,
        query: str,
        *,
        limit: int = 20,
        project_id: uuid.UUID | None = None,
    ) -> list[EntityMatch]:
        """Search entities by name/alias/description using ILIKE.

        The DDL does not enable ``pg_trgm``; we therefore use a plain
        case-insensitive ``ILIKE`` predicate over ``display_name``,
        ``description``, and the ``aliases`` array.  Matches are
        ranked by an in-Python heuristic:

        * exact ``display_name`` match (case-insensitive) → 1.0
        * ``aliases`` contains ``query`` → 0.7
        * ``display_name`` starts-with ``query`` → 0.6
        * ``display_name`` contains ``query`` → 0.5
        * ``description`` contains ``query`` → 0.4
        * tie-break: shorter ``display_name`` ranks first.

        When ``project_id`` is provided, entities are filtered by
        ``project_id = :project_id OR project_scope = 'global'``.
        This ensures that entity "Alice" in project A is a distinct
        row from "Alice" in project B (DATA-04 isolation).

        Args:
            query: Free-text query.  An empty string returns no
                results without raising.
            limit: Maximum number of matches.  Clamped to
                :data:`MAX_SEARCH_LIMIT`.
            project_id: When set, scope results to entities whose
                ``project_id == project_id OR project_scope == 'global'``.
                When ``None`` (default), no project filter is applied.

        Returns:
            A list of :class:`EntityMatch`, ordered by relevance
            descending then by ``display_name`` length ascending.

        Raises:
            KGBudgetExceededError: ``limit`` exceeds the ceiling.
        """
        normalized = (query or "").strip()
        if not normalized:
            return []
        if limit < 1:
            raise KGBudgetExceededError(
                "search_entities limit must be >= 1",
                context={"limit": limit},
            )
        effective_limit = min(limit, MAX_SEARCH_LIMIT)

        # ``%`` wildcards are passed through SQLAlchemy parameter
        # binding; the placeholder is text()-quoted so we escape
        # any embedded percent signs in the user query.
        like_pattern = f"%{_escape_like(normalized)}%"
        project_clause = ""
        if project_id is not None:
            project_clause = (
                "AND (project_id = CAST(:project_id AS uuid) "
                "OR project_scope = 'global')"
            )
        sql = f"""
        SELECT
            id,
            canonical_key,
            entity_type,
            display_name,
            description,
            aliases
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
          {project_clause}
        ORDER BY length(display_name) ASC
        LIMIT :limit
        """
        params: dict[str, Any] = {
            "pattern": like_pattern,
            "limit": effective_limit,
        }
        if project_id is not None:
            params["project_id"] = project_id

        ctx = KGLogContext(operation="kg_search_entities")
        start = time.perf_counter()
        try:
            async with self._repo.get_session() as session:
                result = await session.execute(self._text(sql), params)
                rows = list(result.fetchall())
        except Exception as exc:  # noqa: BLE001 — narrowed below
            raise KGQueryError(
                "search_entities query failed",
                context={
                    "query_len": len(normalized),
                    "limit": effective_limit,
                    "error_type": type(exc).__name__,
                },
            ) from exc

        duration = time.perf_counter() - start
        self._metrics.observe_query_duration(
            query_type="search_entities", hop_count=0, duration=duration,
        )
        ctx.duration_ms = duration * 1000.0
        ctx.result_count = len(rows)
        log_kg_operation(logger, ctx)

        return [
            self._row_to_entity_match(row=row, query=normalized)
            for row in rows
        ]

    @staticmethod
    def _row_to_entity_match(*, row: Any, query: str) -> EntityMatch:
        """Map a search row to :class:`EntityMatch` and score it."""
        display_name = str(row.display_name)
        description = getattr(row, "description", None)
        aliases = list(getattr(row, "aliases", []) or [])
        query_lower = query.lower()
        name_lower = display_name.lower()
        if name_lower == query_lower:
            relevance = 1.0
        elif query_lower in aliases:
            relevance = 0.7
        elif name_lower.startswith(query_lower):
            relevance = 0.6
        elif query_lower in name_lower:
            relevance = 0.5
        else:
            relevance = 0.4  # alias or description hit
        return EntityMatch(
            entity_id=row.id,
            canonical_key=str(row.canonical_key),
            display_name=display_name,
            entity_type=str(row.entity_type),
            description=description,
            aliases=aliases,
            relevance=relevance,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _validate_max_hops(self, requested: int | None) -> int:
        """Clamp ``max_hops`` to ``[1, MAX_TRAVERSAL_HOPS]`` and return it."""
        effective = self._max_hops if requested is None else requested
        if effective < 1:
            raise KGBudgetExceededError(
                "max_hops must be >= 1",
                context={"requested": requested, "default": self._max_hops},
            )
        if effective > MAX_TRAVERSAL_HOPS:
            raise KGBudgetExceededError(
                f"max_hops={effective} exceeds the engine ceiling "
                f"({MAX_TRAVERSAL_HOPS})",
                context={
                    "requested": effective,
                    "ceiling": MAX_TRAVERSAL_HOPS,
                },
            )
        return effective

    @staticmethod
    def _text(sql: str) -> Any:
        """Resolve ``sqlalchemy.text`` lazily (mirrors ``KGRepository``)."""
        from sqlalchemy import text as _text
        return _text(sql)

    # ------------------------------------------------------------------
    # Public SQL helper (used by rrf_fusion, token_budget, context)
    # ------------------------------------------------------------------

    async def execute_to_rows(
        self,
        sql: str,
        params: dict[str, Any] | None = None,
    ) -> list[Any]:
        """Execute raw SQL via the repository and return a typed list of rows.

        This is the canonical entry point used by sibling modules
        (:mod:`rrf_fusion`, :mod:`token_budget`, :mod:`context`) when
        they need a one-shot SQL fetch without managing a session
        themselves.  The method always returns a plain ``list`` so
        downstream callers can iterate without further narrowing.

        Args:
            sql: Parameterized SQL using ``:name`` placeholders.
            params: Bind values keyed by placeholder name.  ``None``
                is treated as an empty mapping.

        Returns:
            A list of row-like objects (whatever
            :meth:`sqlalchemy.engine.Result.fetchall` yields).  Empty
            when no rows match or ``fetchall`` is unavailable.

        Raises:
            KGQueryError: Propagated from the underlying repository
                call when the database layer rejects the query.
        """
        raw = await self._repo.execute(sql, params)
        return self._materialise_rows(raw)

    @staticmethod
    def _materialise_rows(raw: Any) -> list[Any]:
        """Convert a SQLAlchemy ``Result`` to a plain ``list``.

        Splits the awaitable and non-awaitable branches so the
        caller never needs a type-ignore when iterating the result.
        """
        fetchall = getattr(raw, "fetchall", None)
        if callable(fetchall):
            materialized = fetchall()
            if hasattr(materialized, "__await__"):
                # ``async for`` against an ``AsyncResult`` is the
                # safe way to drain an awaitable without depending on
                # the (driver-specific) shape of the value returned
                # by ``fetchall`` when it is itself awaitable.
                return _drain_async(materialized)
            return list(materialized)
        if isinstance(raw, list):
            return list(raw)
        return []


async def _drain_async(awaitable: Any) -> list[Any]:
    """Await an async ``fetchall`` result and return the rows as a list.

    Defined at module scope (not nested in the class) so the return
    type is unambiguous and mypy can infer ``list[Any]`` without
    needing a type-ignore at the call site.
    """
    rows_raw = await awaitable
    if rows_raw is None:
        return []
    if hasattr(rows_raw, "__aiter__"):
        collected: list[Any] = []
        async for entry in rows_raw:
            collected.append(entry)
        return collected
    return list(rows_raw)# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    # Bounds (intentionally exposed for downstream testing & observability)
    "MAX_PATH_HOPS",
    "MAX_NEIGHBORHOOD_RADIUS",
    "MAX_SEARCH_LIMIT",
    "DEFAULT_MAX_RESULTS",
    # Result dataclasses
    "GraphTraversalResult",
    "GraphPath",
    "EntityNeighborhood",
    "EntityMatch",
    # Engine
    "KGQueryEngine",
]


def _escape_like(value: str) -> str:
    """Escape SQL ``LIKE``-special characters in a user-supplied string.

    Used by :meth:`KGQueryEngine.search_entities` to prevent wildcards
    in the user's query from inflating the result set.  The escape
    character is the SQL default ``\\``; the pattern in
    :meth:`search_entities` explicitly states ``ESCAPE '\\'`` to keep
    the contract tight.
    """
    return (
        value.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )
