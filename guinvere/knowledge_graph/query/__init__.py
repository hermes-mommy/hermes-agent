"""KG query submodule — subgraph traversal, PPR scoring, RRF fusion, and recall assembly.

This package contains the **query / recall** surface of the Knowledge
Graph module.  It is the bridge between the graph storage layer
(``memory.kg_*`` tables) and the existing memory recall pipeline
(``guinvere.memory.read_pipeline``).

Public surface
--------------

Engine — :mod:`guinvere.knowledge_graph.query.engine`
    :class:`KGQueryEngine` — RCTE-based graph traversal, path finding,
    neighborhood queries, and ILIKE entity search.  The single
    entry point for every "give me the graph around X" question.

Personalized PageRank — :mod:`guinvere.knowledge_graph.query.ppr`
    :class:`PersonalizedPageRank` — in-process power iteration
    scoring over the active edge set.

RRF fusion — :mod:`guinvere.knowledge_graph.query.rrf_fusion`
    :class:`KGRRFFusion` — integrates the KG as the **4th signal**
    in the existing recall RRF fusion (Faiz-locked weight 0.20).
    Non-breaking: when the KG contributes no signal, the existing
    results pass through unchanged.

Token budget — :mod:`guinvere.knowledge_graph.query.token_budget`
    :class:`KGTokenBudgetManager` — formats the KG subgraph into a
    linearized context string that fits the **1000-token ceiling**.
    Trims from the bottom when the budget is hit.

Recall context assembly — :mod:`guinvere.knowledge_graph.query.context`
    :class:`RecallContextAssembler` — orchestrates the full
    pipeline (search → PPR → traverse → fuse → format → budget) and
    returns a :class:`RecallContext` ready for prompt injection.

Sister modules: :mod:`guinvere.knowledge_graph.repository`,
:mod:`guinvere.knowledge_graph.consent`, :mod:`guinvere.knowledge_graph.types`.
"""
from __future__ import annotations

# Eager re-exports — every collaborator in the recall pipeline is
# imported at package load time so the orchestrator (Wave 3+) can
# resolve everything from a single import.
from guinvere.knowledge_graph.query.context import (
    RecallContext,
    RecallContextAssembler,
)
from guinvere.knowledge_graph.query.engine import (
    DEFAULT_MAX_RESULTS,
    EntityMatch,
    EntityNeighborhood,
    GraphPath,
    GraphTraversalResult,
    KGQueryEngine,
    MAX_NEIGHBORHOOD_RADIUS,
    MAX_PATH_HOPS,
    MAX_SEARCH_LIMIT,
)
from guinvere.knowledge_graph.query.ppr import PPRResult, PersonalizedPageRank
from guinvere.knowledge_graph.query.rrf_fusion import (
    DEFAULT_GRAPH_TOP_K,
    FTS_WEIGHT,
    GraphFusionResult,
    KG_WEIGHT,
    KGRRFFusion,
    K,
    MAX_GRAPH_TOP_K,
    RECENCY_WEIGHT,
    VECTOR_WEIGHT,
)
from guinvere.knowledge_graph.query.token_budget import (
    CHARS_PER_TOKEN,
    DEFAULT_FOOTER,
    DEFAULT_HEADER,
    FormattedContext,
    KGTokenBudgetManager,
    MAX_KG_TOKENS,
)

__all__ = [
    # Engine
    "KGQueryEngine",
    "GraphTraversalResult",
    "GraphPath",
    "EntityNeighborhood",
    "EntityMatch",
    "DEFAULT_MAX_RESULTS",
    "MAX_PATH_HOPS",
    "MAX_NEIGHBORHOOD_RADIUS",
    "MAX_SEARCH_LIMIT",
    # PPR
    "PPRResult",
    "PersonalizedPageRank",
    # RRF fusion
    "KGRRFFusion",
    "GraphFusionResult",
    "KG_WEIGHT",
    "VECTOR_WEIGHT",
    "FTS_WEIGHT",
    "RECENCY_WEIGHT",
    "K",
    "DEFAULT_GRAPH_TOP_K",
    "MAX_GRAPH_TOP_K",
    # Token budget
    "KGTokenBudgetManager",
    "FormattedContext",
    "MAX_KG_TOKENS",
    "CHARS_PER_TOKEN",
    "DEFAULT_HEADER",
    "DEFAULT_FOOTER",
    # Recall context assembly
    "RecallContext",
    "RecallContextAssembler",
]
