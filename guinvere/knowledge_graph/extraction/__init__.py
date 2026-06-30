"""KG extraction submodule — NER / RE pipeline (P16-007, Wave 2).

Public surface
--------------

The submodule exposes the two Wave 2 extractor classes plus the
pattern table they share:

* :class:`EntityExtractor`  — rule-based NER (L1 + L2 only).  Maps
  surface forms in ``SemanticFact.subject`` and ``.object_val`` to
  one of the closed :class:`EntityCategory` values and returns a
  list of :class:`ExtractedEntity` instances.

* :class:`RelationExtractor`  — rule-based RE (L1 + L2 only).  Takes
  a :class:`SemanticFact` plus an :class:`EntityExtractor` and
  returns a list of :class:`ExtractedRelation` instances.

* :data:`~src.knowledge_graph.extraction.patterns.ENTITY_PATTERNS`
  and :data:`~src.knowledge_graph.extraction.patterns.PREDICATE_MAP`
  are re-exported for ergonomic access at the package level.

Layering / future work
----------------------

* L1 = hand-curated regex / gazetteer (this module).
* L2 = exact + fuzzy alias / canonical-key match (delegated to
  :class:`src.knowledge_graph.resolution.resolver.EntityResolver`,
  which is injected but not invoked at extraction time).
* L3 (embedding similarity) is **deferred to P17+** — see the
  no-embeddings research at
  ``evidence/p16-kg/research-entity-resolution-no-embeddings.md``.

Sister modules: :mod:`src.knowledge_graph.resolution`,
:mod:`src.knowledge_graph.ingestion`.
"""
from __future__ import annotations

# Re-export the core public surface so callers can do::
#
#     from guinvere.knowledge_graph.extraction import (
#         EntityExtractor,
#         RelationExtractor,
#         ENTITY_PATTERNS,
#         PREDICATE_MAP,
#     )
from guinvere.knowledge_graph.extraction.entity_extractor import (
    EntityExtractor,
    EntityType,
)
from guinvere.knowledge_graph.extraction.patterns import (
    DEFAULT_FACT_CONFIDENCE,
    DOCUMENT_PATTERNS,
    EMOTION_PATTERNS,
    ENTITY_PATTERNS,
    EVENT_PATTERNS,
    GEO_PATTERNS,
    NAME_PATTERNS,
    ORG_PATTERNS,
    PATTERN_CONFIDENCE,
    PREDICATE_MAP,
    PROJECT_PATTERNS,
    RELATIONSHIP_PATTERNS,
    SURVEILLANCE_PATTERNS,
    SYSTEM_COMPONENT_PATTERNS,
    TECH_PATTERNS,
    CONCEPT_PATTERNS,
)
from guinvere.knowledge_graph.extraction.relation_extractor import (
    RelationExtractor,
)
from guinvere.knowledge_graph.types import (
    EntityCategory,
    ExtractedEntity,
    ExtractedRelation,
    RelationType,
    SemanticFact,
)

__all__ = [
    # Public classes
    "EntityExtractor",
    "RelationExtractor",
    # Re-exported types (so callers can import them from the submodule)
    "EntityCategory",
    "EntityType",
    "ExtractedEntity",
    "ExtractedRelation",
    "RelationType",
    "SemanticFact",
    # Re-exported pattern tables (for tests / observability)
    "ENTITY_PATTERNS",
    "PREDICATE_MAP",
    "PATTERN_CONFIDENCE",
    "DEFAULT_FACT_CONFIDENCE",
    # Per-category pattern families
    "NAME_PATTERNS",
    "GEO_PATTERNS",
    "TECH_PATTERNS",
    "ORG_PATTERNS",
    "PROJECT_PATTERNS",
    "EVENT_PATTERNS",
    "DOCUMENT_PATTERNS",
    "CONCEPT_PATTERNS",
    "EMOTION_PATTERNS",
    "RELATIONSHIP_PATTERNS",
    "SURVEILLANCE_PATTERNS",
    "SYSTEM_COMPONENT_PATTERNS",
]
