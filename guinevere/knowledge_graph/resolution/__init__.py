"""Guinevere P16 Knowledge Graph — entity resolution module.

Layered entity deduplication following the research pattern
(research-reports/p16-kg-patterns.md §3, evidence/p16-kg/research-entity-resolution-no-embeddings.md):

- L1: Exact canonical_key match (SHA-256 over Unicode-normalized name+category)
- L1b: Alias-array exact match (GIN-indexed)
- L2: Fuzzy match via rapidfuzz.WRatio (with difflib.SequenceMatcher fallback
  when rapidfuzz is unavailable)
- L3: Embedding similarity — DEFERRED to P17+ (9Router has no embedding model;
  sentence-transformers explicitly forbidden by operator)

Public API (per the task contract):
    EntityResolver        — high-level orchestrator
    generate_canonical_key — L1 hash generator
    fuzzy_match_entities  — L2 candidate scanner

The module never hard-deletes.  All merges go through ``is_tombstoned = TRUE``
and every merge action is recorded in ``memory.kg_consent_audit``.
"""

from __future__ import annotations

from guinevere.knowledge_graph.resolution.canonical import (
    CANONICAL_KEY_PREFIX,
    CATEGORY_DEFAULT,
    HONORIFIC_PREFIXES,
    NAME_NORMALIZE_PATTERN,
    WHITESPACE_PATTERN,
    generate_canonical_key,
    normalize_entity_name,
)
from guinevere.knowledge_graph.resolution.fuzzy import (
    DEFAULT_FUZZY_LIMIT,
    DEFAULT_FUZZY_THRESHOLD,
    FUZZY_BACKEND_DIFFLIB,
    FUZZY_BACKEND_RAPIDFUZZ,
    FuzzyMatchResult,
    fuzzy_match_entities,
)
from guinevere.knowledge_graph.resolution.resolver import (
    DEFAULT_DEDUP_THRESHOLD,
    EntityResolver,
)

__all__ = [
    # Public resolution API (per the task contract — these three are required)
    "EntityResolver",
    "generate_canonical_key",
    "fuzzy_match_entities",
    # Supporting public types / constants
    "CANONICAL_KEY_PREFIX",
    "CATEGORY_DEFAULT",
    "HONORIFIC_PREFIXES",
    "NAME_NORMALIZE_PATTERN",
    "WHITESPACE_PATTERN",
    "DEFAULT_FUZZY_LIMIT",
    "DEFAULT_FUZZY_THRESHOLD",
    "DEFAULT_DEDUP_THRESHOLD",
    "FUZZY_BACKEND_RAPIDFUZZ",
    "FUZZY_BACKEND_DIFFLIB",
    "FuzzyMatchResult",
    "normalize_entity_name",
]
