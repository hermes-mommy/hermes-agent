"""Knowledge Graph module constants.

Pure value module — no internal imports.  All defaults live here so they
can be referenced by ``types``, ``config``, and downstream modules without
creating circular dependencies.

Conventions follow ``src.memory.read_pipeline`` (``RRF_K = 60``) and
``src.memory.consolidation`` (``SAFE_WORD_INDICATORS`` frozenset).
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Reciprocal Rank Fusion
# ---------------------------------------------------------------------------

RRF_K: int = 60
"""RRF damping constant.  Matches ``src.memory.read_pipeline.RRF_K``."""

KG_RRF_WEIGHT: float = 0.20
"""Default KG weight when fusing KG subgraph evidence with vector/recency
channels in the memory read pipeline.  Per PRD v2.2 P16 spec."""


# ---------------------------------------------------------------------------
# Token budget & traversal depth
# ---------------------------------------------------------------------------

KG_TOKEN_BUDGET_MAX: int = 1000
"""Maximum tokens a KG-derived ``RecallContext`` may contribute to a single
recall response.  Aligns with PRD v2.2 P16 budget ceiling."""

MAX_TRAVERSAL_HOPS: int = 3
"""Maximum BFS/DFS hop depth during subgraph retrieval.  Per P16 spec."""


# ---------------------------------------------------------------------------
# Consent
# ---------------------------------------------------------------------------

CONSENT_TOKEN_PREFIX: str = "kg_"
"""Prefix for all consent tokens issued by the KG module (audit-friendly)."""


# ---------------------------------------------------------------------------
# Default taxonomy (POLE+O + Guinevere extensions)
# ---------------------------------------------------------------------------

DEFAULT_ENTITY_TYPES: list[str] = [
    "person",
    "organization",
    "location",
    "event",
    "concept",
    "technology",
    "project",
    "relationship",
    "emotion",
    "memory_theme",
    "consent_scope",
    "communication_channel",
]
"""Default entity categories.

Mirrors the :class:`EntityCategory` enum in :mod:`src.knowledge_graph.types`.
Defined here as a plain ``list[str]`` so this module stays import-free and
``config.py`` can wire it into Pydantic without a circular import.
"""


DEFAULT_RELATION_TYPES: list[str] = [
    "knows",
    "works_at",
    "located_in",
    "participates_in",
    "related_to",
    "uses",
    "created_by",
    "has_attribute",
    "feels_about",
    "remembers",
    "consents_to",
    "communicates_via",
    "supervises",
    "collaborates_with",
    "preferences",
]
"""Default relation types.

Mirrors the :class:`RelationType` enum in :mod:`src.knowledge_graph.types`.
"""


# ---------------------------------------------------------------------------
# Safe-word & distress indicators
# ---------------------------------------------------------------------------

SAFE_WORD_INDICATORS: frozenset[str] = frozenset({
    "safe_word",
    "hard_stop",
    "crisis",
    "formal_hold",
    "distress",
})
"""Tags / episode_type / title / summary values that mark a record as
off-limits for KG extraction, resolution, and recall.  Mirrors
``src.memory.consolidation.SAFE_WORD_INDICATORS`` — Guinevere persona
boundary; do not weaken without safety review."""


__all__ = [
    "RRF_K",
    "KG_RRF_WEIGHT",
    "KG_TOKEN_BUDGET_MAX",
    "MAX_TRAVERSAL_HOPS",
    "CONSENT_TOKEN_PREFIX",
    "DEFAULT_ENTITY_TYPES",
    "DEFAULT_RELATION_TYPES",
    "SAFE_WORD_INDICATORS",
]
