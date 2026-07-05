"""KG token budget manager — P16-003 prompt injection formatting.

This module formats the graph-derived evidence (entities, edges, PPR
scores) into a string that fits inside the KG's slice of the system
prompt.  It enforces the Faiz-locked **1000-token ceiling** for the
KG portion of any single recall response.

Why a hard 1000-token ceiling
------------------------------

* The recall pipeline has its own overall budget (4 000 tokens per
  cycle, see :data:`guinevere.memory.read_pipeline.DEFAULT_TOKEN_BUDGET`).
  KG cannot eat more than a quarter of that without starving the
  vector / FTS / recency signals — every other channel needs room.
* Linearized triples are noisier than curated memory; without a
  ceiling the model would have to choose between fidelity and
  breadth.

Token estimation
----------------

:func:`KGTokenBudgetManager.estimate_tokens` is intentionally
identical to :func:`guinevere.memory.read_pipeline.estimate_tokens`
(``len(text) // CHARS_PER_TOKEN`` with ``CHARS_PER_TOKEN = 4``).
We re-declare the constant here so this module does not import
from ``guinevere.memory.read_pipeline`` — keeping the KG package free of
upstream coupling.

Linearization format
--------------------

The output is a single human-readable string:

* Direct entity mentions first (one per line, ranked by PPR score).
* Then 1-hop relations, then 2-hop, etc.
* Each edge becomes ``"<src> → <relation> → <dst>"``.
* Edges and entities separated by newlines for legibility.

The string is trimmed **from the bottom** when it would exceed the
budget.  Trimming is performed at line boundaries so the LLM never
sees a half-line artefact.

Hard guarantees
---------------

* Never raises on oversize input — it returns what fits.
* Always returns a string (never ``None``), even when there is
  nothing to format — returns an empty string in that case.
* Logs every truncation event with the line count and token
  delta so capacity planning has data.
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from guinevere.knowledge_graph.constants import KG_TOKEN_BUDGET_MAX
from guinevere.knowledge_graph.errors import KGBudgetExceededError, KGQueryError
from guinevere.knowledge_graph.observability.logger import (
    KGLogContext,
    get_kg_logger,
    log_kg_operation,
)
from guinevere.knowledge_graph.observability.metrics import KGMetrics
from guinevere.knowledge_graph.query.engine import (
    GraphTraversalResult,
    KGQueryEngine,
)
from guinevere.knowledge_graph.query.ppr import PPRResult

logger = get_kg_logger("query.token_budget")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Hard ceiling on tokens consumed by the KG context in a single
#: recall response.  Mirrors :data:`guinevere.knowledge_graph.constants.KG_TOKEN_BUDGET_MAX`
#: (Faiz-locked per PRD v2.2 P16).
MAX_KG_TOKENS: int = KG_TOKEN_BUDGET_MAX

#: Characters-per-token used by :meth:`estimate_tokens`.  Matches
#: :data:`guinevere.memory.read_pipeline.CHARS_PER_TOKEN` so estimates are
#: comparable across the recall pipeline.
CHARS_PER_TOKEN: int = 4

#: Default header line used by :meth:`build_injection_block`.
DEFAULT_HEADER: str = "[KNOWLEDGE GRAPH CONTEXT]"

#: Default footer line used by :meth:`build_injection_block`.
DEFAULT_FOOTER: str = "[END KNOWLEDGE GRAPH CONTEXT]"


# ---------------------------------------------------------------------------
# Result metadata
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FormattedContext:
    """Diagnostic bundle for a :meth:`format_graph_context` call.

    Attributes:
        text: The final linearized graph context (may be empty).
        tokens_used: Estimated token count of ``text``.
        triples_included: Number of triples that made it into the
            output (entities + edges, whichever applies).
        triples_dropped: Number of triples skipped because of the
            token budget.  ``0`` when nothing was dropped.
        truncated: ``True`` when the budget forced a trim.
    """

    text: str
    tokens_used: int
    triples_included: int
    triples_dropped: int
    truncated: bool


# ---------------------------------------------------------------------------
# Token budget manager
# ---------------------------------------------------------------------------


class KGTokenBudgetManager:
    """Manages KG context injection within the 1000-token budget.

    The manager is **stateless**: every method is a pure function of
    its inputs plus a database round-trip for entity-name lookup.
    Construct it once at app start and share across coroutines.

    Args:
        query_engine: A :class:`KGQueryEngine` — used to resolve
            entity UUIDs to display names when ``format_graph_context``
            needs them.  When ``None`` is passed, the manager can
            still operate but entity names are rendered as their
            truncated UUID (fallback for offline / unit-test mode).
        max_tokens: Optional override of the per-call budget.  When
            ``None``, :data:`MAX_KG_TOKENS` (1000) applies.  Values
            above :data:`MAX_KG_TOKENS` raise :class:`KGBudgetExceededError`
            so a misconfigured caller cannot silently violate the
            Faiz-locked ceiling.

    Example::

        engine = KGQueryEngine(session_factory)
        budget = KGTokenBudgetManager(query_engine=engine)
        ctx_text = budget.format_graph_context(traversal_results, ppr_results)
        block = budget.build_injection_block(ctx_text)
    """

    def __init__(
        self,
        query_engine: KGQueryEngine | None = None,
        *,
        max_tokens: int | None = None,
    ) -> None:
        if max_tokens is not None:
            if max_tokens < 1:
                raise KGBudgetExceededError(
                    "max_tokens must be >= 1",
                    context={"max_tokens": max_tokens},
                )
            if max_tokens > MAX_KG_TOKENS:
                # Strict Faiz-locked ceiling — surface, do not silently clamp.
                raise KGBudgetExceededError(
                    f"max_tokens={max_tokens} exceeds the KG ceiling "
                    f"({MAX_KG_TOKENS})",
                    context={
                        "max_tokens": max_tokens,
                        "ceiling": MAX_KG_TOKENS,
                    },
                )
        self._max_tokens: int = max_tokens if max_tokens is not None else MAX_KG_TOKENS
        self._query_engine: KGQueryEngine | None = query_engine
        self._metrics: KGMetrics = KGMetrics.get_instance()

    # ------------------------------------------------------------------
    # Token estimation
    # ------------------------------------------------------------------

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Approximate token count of ``text``.

        Mirrors :func:`guinevere.memory.read_pipeline.estimate_tokens`
        (``len(text) // CHARS_PER_TOKEN``) so KG and recall budgets
        use the same estimator and stay comparable.

        Args:
            text: The string to estimate.  Empty strings return 0.

        Returns:
            Estimated token count, always >= 0.
        """
        if not text:
            return 0
        return len(text) // CHARS_PER_TOKEN

    # ------------------------------------------------------------------
    # Context formatting
    # ------------------------------------------------------------------

    async def format_graph_context(
        self,
        traversal_results: Sequence[GraphTraversalResult],
        ppr_results: Sequence[PPRResult] | None = None,
        *,
        max_tokens: int | None = None,
    ) -> str:
        """Format graph results as an injectable context string.

        Priority order (from highest to lowest):

        1. Direct entity mentions — sorted by PPR score descending.
        2. 1-hop relations from seeds (depth == 1).
        3. 2-hop relations (depth == 2).
        4. Deeper hops (depth == 3+) — included only when budget
           permits.

        Each line is either an entity mention (``"<name> (PPR: 0.85)"``)
        or an edge (``"<src> → <relation> → <dst>"``).  Lines are
        separated by ``"\\n"`` for readability.

        Trimming is greedy from the bottom: each candidate line is
        appended only if doing so keeps the running total under the
        budget; otherwise it is dropped.

        Args:
            traversal_results: Edges from
                :meth:`KGQueryEngine.traverse`.  May be empty.
            ppr_results: PPR-ranked entities from
                :meth:`PersonalizedPageRank.compute`.  Optional.
            max_tokens: Per-call budget override.  ``None`` uses the
                instance default.  Clamped to :data:`MAX_KG_TOKENS`.

        Returns:
            A linearized string ready for injection.  Empty string
            when there is nothing to format.
        """
        effective_budget = self._resolve_budget(max_tokens)
        if effective_budget < 1:
            return ""

        log_ctx = KGLogContext(operation="kg_format_graph_context")
        start_time = _now_monotonic()

        # Resolve entity names.  We dedupe upfront to keep the SQL
        # bounded; traversal and PPR may share many UUIDs.
        needed_ids: set[uuid.UUID] = set()
        for tr in traversal_results:
            needed_ids.add(tr.src_entity_id)
            needed_ids.add(tr.dst_entity_id)
        if ppr_results:
            for pr in ppr_results:
                needed_ids.add(pr.entity_id)

        name_lookup: dict[uuid.UUID, str]
        if needed_ids:
            name_lookup = await self._resolve_entity_names(needed_ids)
        else:
            name_lookup = {}

        # Build candidate lines in priority order.
        candidate_lines: list[str] = []

        # 1. PPR-ranked entity mentions.
        if ppr_results:
            sorted_ppr = sorted(
                ppr_results,
                key=lambda r: (-r.score, str(r.entity_id)),
            )
            for pr in sorted_ppr:
                name = name_lookup.get(pr.entity_id, _short_uuid(pr.entity_id))
                candidate_lines.append(f"{name} (PPR: {pr.score:.3f})")

        # 2-N. Group edges by depth; emit depth-1 first, then deeper.
        edges_by_depth: dict[int, list[GraphTraversalResult]] = {}
        for tr in traversal_results:
            edges_by_depth.setdefault(tr.depth, []).append(tr)

        for depth in sorted(edges_by_depth.keys()):
            group = edges_by_depth[depth]
            # Within a depth group, edges from higher-PPR sources
            # come first.  PPR results may not be present; in that
            # case we fall back to edge confidence desc.
            score_lookup = (
                {pr.entity_id: pr.score for pr in (ppr_results or [])}
            )
            group_sorted = sorted(
                group,
                key=lambda e: (
                    -float(score_lookup.get(e.src_entity_id, 0.0)),
                    -float(e.confidence),
                    str(e.edge_id),
                ),
            )
            for edge in group_sorted:
                src_name = name_lookup.get(
                    edge.src_entity_id, _short_uuid(edge.src_entity_id),
                )
                dst_name = name_lookup.get(
                    edge.dst_entity_id, _short_uuid(edge.dst_entity_id),
                )
                relation = edge.relationship_type.replace("_", " ")
                candidate_lines.append(
                    f"{src_name} → {relation} → {dst_name}",
                )

        # Trim from the bottom to fit the budget.
        accepted: list[str] = []
        running = 0
        for line in candidate_lines:
            line_cost = self.estimate_tokens(line) + 1  # +1 for the newline
            if running + line_cost > effective_budget:
                break
            accepted.append(line)
            running += line_cost

        final_text = "\n".join(accepted)
        truncated = len(accepted) < len(candidate_lines)

        # Observability: log + record metrics.
        if truncated:
            elapsed_ms = (_now_monotonic() - start_time) * 1000.0
            log_ctx.duration_ms = elapsed_ms
            log_ctx.result_count = len(accepted)
            log_ctx.error = (
                f"trimmed {len(candidate_lines) - len(accepted)} lines "
                f"to fit budget={effective_budget}"
            )
            log_kg_operation(logger, log_ctx)
            self._metrics.observe_token_budget(
                utilization_ratio=running / effective_budget,
            )

        return final_text

    def format_graph_context_sync(
        self,
        traversal_results: Sequence[GraphTraversalResult],
        ppr_results: Sequence[PPRResult] | None = None,
        *,
        max_tokens: int | None = None,
        name_lookup: dict[uuid.UUID, str] | None = None,
    ) -> FormattedContext:
        """Synchronous variant that accepts a pre-resolved name lookup.

        Use this when the caller has already done a name resolution
        pass (e.g. inside :class:`RecallContextAssembler`) and wants
        to avoid a second database round-trip.

        Args:
            traversal_results: Edges from traversal.
            ppr_results: PPR-ranked entities (optional).
            max_tokens: Budget override; ``None`` uses the default.
            name_lookup: Pre-built ``{uuid: display_name}`` mapping.
                When ``None``, names fall back to truncated UUIDs.

        Returns:
            :class:`FormattedContext` carrying the formatted text,
            token usage, and truncation metadata.
        """
        effective_budget = self._resolve_budget(max_tokens)
        names = name_lookup or {}

        candidates: list[str] = []
        if ppr_results:
            sorted_ppr = sorted(
                ppr_results,
                key=lambda r: (-r.score, str(r.entity_id)),
            )
            for pr in sorted_ppr:
                display = names.get(pr.entity_id, _short_uuid(pr.entity_id))
                candidates.append(f"{display} (PPR: {pr.score:.3f})")

        edges_by_depth: dict[int, list[GraphTraversalResult]] = {}
        for tr in traversal_results:
            edges_by_depth.setdefault(tr.depth, []).append(tr)
        score_lookup = (
            {pr.entity_id: pr.score for pr in (ppr_results or [])}
        )
        for depth in sorted(edges_by_depth.keys()):
            group = sorted(
                edges_by_depth[depth],
                key=lambda e: (
                    -float(score_lookup.get(e.src_entity_id, 0.0)),
                    -float(e.confidence),
                    str(e.edge_id),
                ),
            )
            for edge in group:
                src = names.get(edge.src_entity_id, _short_uuid(edge.src_entity_id))
                dst = names.get(edge.dst_entity_id, _short_uuid(edge.dst_entity_id))
                relation = edge.relationship_type.replace("_", " ")
                candidates.append(f"{src} → {relation} → {dst}")

        accepted: list[str] = []
        running = 0
        for line in candidates:
            cost = self.estimate_tokens(line) + 1
            if running + cost > effective_budget:
                break
            accepted.append(line)
            running += cost

        final_text = "\n".join(accepted)
        truncated = len(accepted) < len(candidates)
        return FormattedContext(
            text=final_text,
            tokens_used=self.estimate_tokens(final_text),
            triples_included=len(accepted),
            triples_dropped=len(candidates) - len(accepted),
            truncated=truncated,
        )

    # ------------------------------------------------------------------
    # Injection block
    # ------------------------------------------------------------------

    def build_injection_block(
        self,
        graph_context: str,
        *,
        header: str = DEFAULT_HEADER,
        footer: str = DEFAULT_FOOTER,
    ) -> str:
        """Wrap ``graph_context`` in a labelled block for system prompt.

        The block looks like::

            [KNOWLEDGE GRAPH CONTEXT]
            Faiz → works on → Guinevere
            Guinevere → uses → PostgreSQL
            [END KNOWLEDGE GRAPH CONTEXT]

        An empty ``graph_context`` returns an empty string (no
        pointless header) — this keeps the system prompt clean
        when the KG contributed nothing.

        Args:
            graph_context: The linearized context from
                :meth:`format_graph_context`.  May be empty.
            header: Opening line.  Override for custom labels.
            footer: Closing line.  Override for custom labels.

        Returns:
            The wrapped block, or ``""`` when ``graph_context`` is
            empty.
        """
        body = (graph_context or "").strip()
        if not body:
            return ""
        return f"{header}\n{body}\n{footer}"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _resolve_entity_names(
        self,
        entity_ids: set[uuid.UUID],
    ) -> dict[uuid.UUID, str]:
        """Look up display names for ``entity_ids`` via the query engine.

        Returns an empty dict when no query engine is wired (e.g.
        in unit tests); the caller falls back to truncated UUIDs.

        Args:
            entity_ids: Set of UUIDs to resolve.

        Returns:
            ``{uuid: display_name}`` for entities that exist and are
            not tombstoned.  Missing UUIDs are simply absent from
            the returned dict.
        """
        if not entity_ids or self._query_engine is None:
            return {}
        try:
            rows = await self._query_engine.execute_to_rows(
                _ENTITY_NAME_SQL,
                {"ids": [str(e) for e in entity_ids]},
            )
        except Exception as exc:  # noqa: BLE001 — narrowed below
            raise KGQueryError(
                "entity-name lookup for context formatting failed",
                context={
                    "entity_count": len(entity_ids),
                    "error_type": type(exc).__name__,
                },
            ) from exc
        out: dict[uuid.UUID, str] = {}
        for row in rows:
            ent_id = getattr(row, "id", None)
            name = getattr(row, "display_name", None)
            if ent_id is None or name is None:
                continue
            if isinstance(ent_id, uuid.UUID):
                out[ent_id] = str(name)
            else:
                out[uuid.UUID(str(ent_id))] = str(name)
        return out

    def _resolve_budget(self, requested: int | None) -> int:
        """Resolve the effective per-call budget, honouring the ceiling."""
        effective = self._max_tokens if requested is None else requested
        if effective < 1:
            return 0
        return min(effective, MAX_KG_TOKENS)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


_ENTITY_NAME_SQL = """
SELECT id, display_name
FROM memory.kg_entities
WHERE is_tombstoned = FALSE
  AND id = ANY(CAST(:ids AS uuid[]))
"""


def _now_monotonic() -> float:
    """Wall-clock-independent monotonic time in seconds (float)."""
    import time
    return time.perf_counter()


def _short_uuid(value: uuid.UUID) -> str:
    """Render ``value`` as a short, opaque but readable fallback label.

    Used only when no name resolution is available (offline mode
    or unit tests).  Returns the first 8 hex characters — enough
    for disambiguation, not enough to leak sensitive IDs in logs.
    """
    return f"<{str(value)[:8]}>"


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    # Constants
    "MAX_KG_TOKENS",
    "CHARS_PER_TOKEN",
    "DEFAULT_HEADER",
    "DEFAULT_FOOTER",
    # Diagnostic dataclass
    "FormattedContext",
    # Main class
    "KGTokenBudgetManager",
]
