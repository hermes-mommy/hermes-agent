"""Knowledge Graph domain types.

Pure value module — defines enums and dataclasses that all downstream
P16 submodules (``extraction``, ``resolution``, ``query``, ``ingestion``,
``consent``, ``eval``, ``observability``) import.  No I/O, no DB, no
external service calls.

Conventions:
- ``str``-based enums so :class:`.EntityCategory` and :class:`.RelationType`
  serialize cleanly to PostgreSQL ``text`` columns.
- All dataclasses use ``field(default_factory=...)`` for mutable defaults.
- ``JsonObject`` is ``dict[str, object]`` (never ``Any``) for audit safety.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Protocol, TypeAlias

if TYPE_CHECKING:
    # Imported only for type checkers — runtime code uses the Protocol so the
    # KG module stays free of heavy ORM imports.  See ``SemanticFact``.
    from guinvere.memory.models import SemanticFacts as _SemanticFactsORM  # noqa: F401

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

# Compatibility alias — earlier P16 specs and the Wave 2 task contract
# referred to the entity taxonomy as ``EntityType``; the canonical enum below
# is named ``EntityCategory`` to match the PRD v2.2 P16 spec.  Both names
# resolve to the same enum so callers can use whichever they prefer.
EntityType: TypeAlias = "EntityCategory"
"""Alias for :class:`EntityCategory`.

Kept so that code written against the Wave 2 task contract (``EntityType``)
and code aligned with the PRD v2.2 P16 vocabulary (``EntityCategory``) both
type-check without an extra import.  See :class:`EntityCategory`.
"""

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

JsonObject: TypeAlias = dict[str, object]
"""Audit-safe JSON payload — string keys, ``object`` values.

Use this for ``metadata`` / ``properties`` fields.  Never use bare
``dict`` (rejected by strict mypy) and never use ``Any`` (audit-unfriendly).
"""

EmbeddingVector: TypeAlias = list[float]
"""Dense embedding vector.  Length is provider-specific (e.g. 1024 for the
memory module's default embedding model)."""

ResolutionMethod: TypeAlias = str
"""One of ``"exact"``, ``"fuzzy"``, or ``"llm"`` — see
:class:`EntityResolutionResult.method` for the contract."""


def _utcnow() -> datetime:
    """Return a timezone-aware UTC ``datetime``.  Local helper to avoid
    importing the same idiom in every dataclass default factory."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class EntityCategory(str, Enum):
    """Closed taxonomy of KG entity categories.

    Combines the standard POLE+O scheme (Person, Organization, Location,
    Event) with Guinevere-specific extensions for the companion domain
    (consent, emotion, memory themes, communication channels, documents,
    surveillance contexts, and system components).

    ``str``-based so values round-trip cleanly through PostgreSQL ``text``.

    .. note::

        Wave 2 (P16-007) extended the taxonomy with ``DOCUMENT``,
        ``SURVEILLANCE_CONTEXT``, and ``SYSTEM_COMPONENT`` so the
        rule-based extractor can surface the operator's documents,
        surveillance channels, and Guinevere system components
        directly.  The Wave 1 closed-taxonomy DDL was designed to
        accept arbitrary new ``entity_type`` strings, so the extension
        is additive and does not require a schema migration.
    """

    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    EVENT = "event"
    CONCEPT = "concept"
    TECHNOLOGY = "technology"
    PROJECT = "project"
    RELATIONSHIP = "relationship"
    EMOTION = "emotion"
    MEMORY_THEME = "memory_theme"
    CONSENT_SCOPE = "consent_scope"
    COMMUNICATION_CHANNEL = "communication_channel"
    # Wave 2 (P16-007) additions
    DOCUMENT = "document"
    SURVEILLANCE_CONTEXT = "surveillance_context"
    SYSTEM_COMPONENT = "system_component"


class RelationType(str, Enum):
    """Closed taxonomy of KG relation types.

    Covers social (``KNOWS``, ``COLLABORATES_WITH``), organizational
    (``WORKS_AT``, ``SUPERVISES``), spatial (``LOCATED_IN``), preference
    (``PREFERENCES``, ``FEELS_ABOUT``), provenance (``CREATED_BY``,
    ``USES``), and the Guinevere-specific consent / memory relations
    (``CONSENTS_TO``, ``REMEMBERS``, ``COMMUNICATES_VIA``).
    """

    KNOWS = "knows"
    WORKS_AT = "works_at"
    LOCATED_IN = "located_in"
    PARTICIPATES_IN = "participates_in"
    RELATED_TO = "related_to"
    USES = "uses"
    CREATED_BY = "created_by"
    HAS_ATTRIBUTE = "has_attribute"
    FEELS_ABOUT = "feels_about"
    REMEMBERS = "remembers"
    CONSENTS_TO = "consents_to"
    COMMUNICATES_VIA = "communicates_via"
    SUPERVISES = "supervises"
    COLLABORATES_WITH = "collaborates_with"
    PREFERENCES = "preferences"


class EdgeStatus(str, Enum):
    """Lifecycle state of a :class:`KGEdge`.

    Soft-delete is preferred: ``TOMBSTONED`` keeps the row for audit but
    excludes it from query results.  ``MERGED`` indicates the edge was
    consolidated into another during entity resolution.  ``PENDING_REVIEW``
    is set when the extraction confidence is below the configured floor
    and human review is required.
    """

    ACTIVE = "active"
    TOMBSTONED = "tombstoned"
    MERGED = "merged"
    PENDING_REVIEW = "pending_review"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KGEntity:
    """A node in the Knowledge Graph.

    Attributes:
        id: Stable UUID assigned at first persistence.
        canonical_key: Deterministic normalized form of the entity name
            (lowercase, NFKC, collapsed whitespace).  Used for upsert
            collision detection in the resolution stage.
        name: Display name (preserves original casing and punctuation).
        category: Closed-taxonomy classification — see :class:`EntityCategory`.
        aliases: Alternative surface forms observed in source text.  The
            canonical name is implicit; do not duplicate it here.
        embedding: Optional dense vector for semantic similarity.  ``None``
            for entities not yet embedded (e.g. fresh CRUD rows).
        metadata: Audit-safe JSON payload — see :data:`JsonObject`.
        created_at: UTC timestamp of first persistence.
        updated_at: UTC timestamp of the last modification.
        is_tombstoned: Soft-delete flag.  Tombstoned entities are excluded
            from default query results but kept for audit.
    """

    id: uuid.UUID
    canonical_key: str
    name: str
    category: EntityCategory
    aliases: list[str] = field(default_factory=list)
    embedding: EmbeddingVector | None = None
    metadata: JsonObject = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    is_tombstoned: bool = False


@dataclass(frozen=True)
class KGEdge:
    """A directed edge in the Knowledge Graph (relation).

    Attributes:
        id: Stable UUID assigned at first persistence.
        src_entity_id: UUID of the subject :class:`KGEntity`.
        dst_entity_id: UUID of the object :class:`KGEntity`.
        relation_type: Closed-taxonomy relation — see :class:`RelationType`.
        confidence: Extraction confidence in ``[0.0, 1.0]``.
        consent_token: Opaque token authorizing this edge for the
            requesting principal.  ``None`` only for system-internal edges
            (e.g. entity-resolution bookkeeping).  Required for any edge
            that surfaces user-derived personal data.
        source_fact_id: UUID of the originating fact in
            ``memory.semantic_facts`` (P3-015 consolidation output).
        kg_episode_id: Optional UUID of the KG-episode provenance row in
            ``memory.kg_episodes`` (when the fact was processed by the
            KG extraction pipeline).
        valid_from: UTC timestamp marking the start of temporal validity.
        valid_to: UTC timestamp marking the end of temporal validity,
            or ``None`` if the edge is still considered valid.
        recorded_at: UTC timestamp when the edge row was written.
        is_tombstoned: Soft-delete flag.
        metadata: Audit-safe JSON payload.
    """

    id: uuid.UUID
    src_entity_id: uuid.UUID
    dst_entity_id: uuid.UUID
    relation_type: RelationType
    confidence: float
    consent_token: str | None
    source_fact_id: uuid.UUID
    kg_episode_id: uuid.UUID | None
    valid_from: datetime
    valid_to: datetime | None
    recorded_at: datetime
    is_tombstoned: bool = False
    metadata: JsonObject = field(default_factory=dict)


@dataclass(frozen=True)
class KGTriple:
    """A raw extracted (subject, predicate, object) triple from source text.

    Used as the intermediate representation between NER/RE and the
    resolution/ingestion stages.  Triples are NOT persisted directly —
    after resolution they become :class:`KGEntity` and :class:`KGEdge` rows.
    """

    subject: str
    predicate: str
    object: str
    confidence: float
    source_text: str
    source_episode_id: uuid.UUID | None = None


@dataclass(frozen=True)
class RecallContext:
    """Bundle of KG-derived evidence for a single recall response.

    Produced by the query stage and consumed by the memory read pipeline
    for RRF fusion (weight = :data:`KG_RRF_WEIGHT`).

    Attributes:
        entities: :class:`KGEntity` rows surfaced by the traversal.
        edges: :class:`KGEdge` rows surfaced by the traversal.
        triples: Pre-formatted stringified triples (one per line) ready
            for prompt injection.  Must fit within ``token_count`` budget.
        token_count: Estimated token cost of the full context.  Enforced
            against :data:`KG_TOKEN_BUDGET_MAX`.
        query: The original user/operator query that produced this context.
        hop_count: Number of BFS/DFS hops actually performed (``<=``
            :data:`MAX_TRAVERSAL_HOPS`).
    """

    entities: list[KGEntity] = field(default_factory=list)
    edges: list[KGEdge] = field(default_factory=list)
    triples: list[str] = field(default_factory=list)
    token_count: int = 0
    query: str = ""
    hop_count: int = 0


@dataclass(frozen=True)
class EntityResolutionResult:
    """Outcome of the entity-resolution stage for a single mention.

    Attributes:
        canonical_entity: The resolved :class:`KGEntity` (existing or
            newly created).  Never ``None`` — resolution must always
            produce a canonical node.
        matched_aliases: Surface forms that were collapsed into this
            canonical entity during this resolution call.
        confidence: Match confidence in ``[0.0, 1.0]``.  Below
            :data:`kg_dedup_threshold` the match is rejected and a new
            entity is created.
        method: One of ``"exact"``, ``"fuzzy"``, or ``"llm"`` —
            indicates which resolver path produced the match.
    """

    canonical_entity: KGEntity
    matched_aliases: list[str] = field(default_factory=list)
    confidence: float = 1.0
    method: ResolutionMethod = "exact"


# ---------------------------------------------------------------------------
# Extraction layer types (P16-007 — NER/RE Extractor Module, Wave 2)
# ---------------------------------------------------------------------------


class SemanticFact(Protocol):
    """Structural type for a semantic fact consumed by the extraction layer.

    The Wave 2 extraction pipeline operates on instances of
    ``memory.semantic_facts`` (P3-015 consolidation output) but the KG module
    does not want to import the SQLAlchemy ORM at runtime.  This ``Protocol``
    captures the attribute contract — any object exposing the listed
    attributes is accepted by :class:`src.knowledge_graph.extraction.
    EntityExtractor` and :class:`src.knowledge_graph.extraction.
    RelationExtractor`.

    Attributes are read-only from the extractor's perspective; the extractor
    never mutates the source fact.
    """

    id: uuid.UUID
    """Stable UUID of the fact in ``memory.semantic_facts``."""

    subject: str
    """Subject slot of the (s, p, o) triple.  Free text, not yet typed."""

    predicate: str
    """Predicate slot.  Free text, used as the primary relation-classification
    signal.  Lower-cased and trimmed before lookup in ``PREDICATE_MAP``."""

    object_val: str
    """Object slot of the (s, p, o) triple.  Free text, not yet typed."""

    fact_type: str
    """Coarse fact category from the consolidation layer (e.g. ``"episodic"``,
    ``"semantic"``, ``"preference"``).  Reserved for future routing; the
    current L1+L2 rule-based extractor does not branch on this attribute."""

    confidence: float | None
    """Extraction confidence in ``[0.0, 1.0]``.  ``None`` is coerced to a
    neutral ``0.5`` floor by :meth:`RelationExtractor.compute_confidence`."""

    source_episode: uuid.UUID | None
    """Optional UUID of the originating ``memory.episodes`` row.  Carried
    through the KG provenance chain but not used by the L1+L2 extractor."""


@dataclass(frozen=True)
class ExtractedEntity:
    """A single entity mention extracted from a semantic fact.

    Produced by :class:`src.knowledge_graph.extraction.EntityExtractor`.
    Frozen so it can safely cross asyncio / queue boundaries during the
    P16 ingestion pipeline (Wave 3) and be hashed for set-membership tests
    inside the resolver without copying.

    Attributes:
        text: The original surface form as it appeared in the source fact
            (subject or object_val).  Preserves casing/punctuation for
            display; canonical form lives in the resolver.
        entity_type: Closed-taxonomy classification — see :class:`EntityCategory`.
        confidence: Extraction confidence in ``[0.0, 1.0]``.  Combines the
            pattern strength with the source fact's confidence (see
            :meth:`EntityExtractor._confidence_for`).
        source_fact_id: UUID of the originating semantic fact.  Used by
            downstream stages (resolution, ingestion) to maintain
            provenance.
        span: Optional ``(start, end)`` character offsets into the source
            text.  ``None`` when the extractor treats the entire input
            string as a single entity (the L1+L2 fast-path behaviour).
    """

    text: str
    entity_type: EntityType
    confidence: float
    source_fact_id: uuid.UUID
    span: tuple[int, int] | None = None

    def __post_init__(self) -> None:
        # Defensive validation — frozen dataclasses run ``__post_init__`` once
        # at construction.  Centralising the check here keeps every call site
        # honest without sprinkling ``if not 0.0 <= x <= 1.0`` everywhere.
        if not self.text:
            raise ValueError("ExtractedEntity.text must be non-empty")
        if not (0.0 <= float(self.confidence) <= 1.0):
            raise ValueError(
                f"ExtractedEntity.confidence must be in [0.0, 1.0]; "
                f"got {self.confidence!r}"
            )
        if self.span is not None:
            start, end = self.span
            if start < 0 or end < start:
                raise ValueError(
                    f"ExtractedEntity.span must be a non-negative range with "
                    f"start <= end; got {self.span!r}"
                )


@dataclass(frozen=True)
class ExtractedRelation:
    """A typed relation extracted from a semantic fact.

    Produced by :class:`src.knowledge_graph.extraction.RelationExtractor`.
    Wraps a subject and object :class:`ExtractedEntity` together with the
    classified :class:`RelationType` and a confidence score.

    Attributes:
        subject: The head (s) of the relation.  Always present.
        predicate: The raw predicate string from the source fact.  Preserved
            verbatim (not lower-cased) so the LLM-extraction stage in P17+
            can inspect the original verb phrase.
        object_entity: The tail (o) of the relation.  Always present.
        relation_type: Closed-taxonomy relation — see :class:`RelationType`.
        confidence: Relation-level confidence in ``[0.0, 1.0]``.  Equal to
            the source fact's confidence floor (the L1+L2 stage does not
            combine subject/object confidences — that is P17+ territory).
        source_fact_id: UUID of the originating semantic fact.
    """

    subject: ExtractedEntity
    predicate: str
    object_entity: ExtractedEntity
    relation_type: RelationType
    confidence: float
    source_fact_id: uuid.UUID

    def __post_init__(self) -> None:
        if not self.predicate:
            raise ValueError("ExtractedRelation.predicate must be non-empty")
        if not (0.0 <= float(self.confidence) <= 1.0):
            raise ValueError(
                f"ExtractedRelation.confidence must be in [0.0, 1.0]; "
                f"got {self.confidence!r}"
            )


__all__ = [
    # Type aliases
    "JsonObject",
    "EmbeddingVector",
    "ResolutionMethod",
    "EntityType",
    # Enums
    "EntityCategory",
    "RelationType",
    "EdgeStatus",
    # Dataclasses
    "KGEntity",
    "KGEdge",
    "KGTriple",
    "RecallContext",
    "EntityResolutionResult",
    # Extraction layer (P16-007)
    "SemanticFact",
    "ExtractedEntity",
    "ExtractedRelation",
]
