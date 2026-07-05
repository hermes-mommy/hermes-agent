"""P16-007: rule-based relation extractor (RE, L1 + L2 only).

Sister module to :mod:`guinevere.knowledge_graph.extraction.entity_extractor`.
This module takes a :class:`~guinevere.knowledge_graph.types.SemanticFact`,
asks the :class:`EntityExtractor` for the typed entities in the
subject and object slots, and emits a list of
:class:`ExtractedRelation` instances ready to be persisted as
:class:`~guinevere.knowledge_graph.types.KGEdge` rows by the P16-002
ingestion pipeline.

The relation classification is driven by the source fact's
**predicate** — the consolidation layer (P3-015) already produces a
verb phrase that captures the relationship.  We do not re-derive
the predicate from raw text; we map it through
:data:`~guinevere.knowledge_graph.extraction.patterns.PREDICATE_MAP` to one
of the closed :class:`~guinevere.knowledge_graph.types.RelationType` values.

Type-aware refinement lives in
:meth:`RelationExtractor.classify_relation`: when the
``PREDICATE_MAP`` does not match (e.g. a foreign-language predicate
or a verb the gazetteer has not seen), the entity-type pair provides
a secondary signal — e.g. ``(PERSON, ORGANIZATION)`` defaults to
:attr:`RelationType.WORKS_AT`, ``(PERSON, LOCATION)`` defaults to
:attr:`RelationType.LOCATED_IN`, etc.

Safety / consent notes (per AGENTS.md BLOCKING rules and
PersonaSafetyPolicy):

* The relation extractor never persists data.  It only emits
  :class:`ExtractedRelation` instances in memory.
* It does not bypass HARD STOP or safe-word enforcement.
* It does not type-suppress.
"""
from __future__ import annotations

import uuid
from typing import Final

from guinevere.knowledge_graph.errors import KGExtractionError
from guinevere.knowledge_graph.extraction.entity_extractor import EntityExtractor
from guinevere.knowledge_graph.extraction.patterns import (
    DEFAULT_FACT_CONFIDENCE,
    PREDICATE_MAP,
)
from guinevere.knowledge_graph.types import (
    EntityCategory,
    EntityType,
    ExtractedEntity,
    ExtractedRelation,
    RelationType,
    SemanticFact,
)


# ---------------------------------------------------------------------------
# Type-aware fallback map
# ---------------------------------------------------------------------------

# When ``PREDICATE_MAP`` does not match the predicate, this table is
# consulted with ``(subject_category, object_category)`` as the key.
# The chosen relation type is a conservative default — the ingestion
# pipeline can downgrade it to ``RELATED_TO`` if the operator reviews
# the row and disagrees.
_TYPE_AWARE_FALLBACK: Final[dict[tuple[EntityCategory, EntityCategory], RelationType]] = {
    # People at companies → WORKS_AT
    (EntityCategory.PERSON, EntityCategory.ORGANIZATION): RelationType.WORKS_AT,
    # People in places → LOCATED_IN
    (EntityCategory.PERSON, EntityCategory.LOCATION): RelationType.LOCATED_IN,
    # People with people → KNOWS
    (EntityCategory.PERSON, EntityCategory.PERSON): RelationType.KNOWS,
    # People using tools → USES
    (EntityCategory.PERSON, EntityCategory.TECHNOLOGY): RelationType.USES,
    # People participating in events → PARTICIPATES_IN
    (EntityCategory.PERSON, EntityCategory.EVENT): RelationType.PARTICIPATES_IN,
    # People working on projects → PARTICIPATES_IN (project ≈ event-ish)
    (EntityCategory.PERSON, EntityCategory.PROJECT): RelationType.PARTICIPATES_IN,
    # People reading documents → RELATED_TO (no exact match in taxonomy)
    (EntityCategory.PERSON, EntityCategory.DOCUMENT): RelationType.RELATED_TO,
    # People feeling emotions → FEELS_ABOUT
    (EntityCategory.PERSON, EntityCategory.EMOTION): RelationType.FEELS_ABOUT,
    # People in relationships → KNOWS (closest social relation)
    (EntityCategory.PERSON, EntityCategory.RELATIONSHIP): RelationType.KNOWS,
    # People interacting with surveillance contexts → RELATED_TO
    (
        EntityCategory.PERSON,
        EntityCategory.SURVEILLANCE_CONTEXT,
    ): RelationType.RELATED_TO,
    # People using system components → USES
    (
        EntityCategory.PERSON,
        EntityCategory.SYSTEM_COMPONENT,
    ): RelationType.USES,
    # Orgs at locations → LOCATED_IN
    (EntityCategory.ORGANIZATION, EntityCategory.LOCATION): RelationType.LOCATED_IN,
    # Orgs created by people → CREATED_BY (reverse — fall back to RELATED_TO
    # because the closed taxonomy has no inverse-CREATED_BY).
    (EntityCategory.ORGANIZATION, EntityCategory.PERSON): RelationType.RELATED_TO,
    # Orgs using tools → USES
    (EntityCategory.ORGANIZATION, EntityCategory.TECHNOLOGY): RelationType.USES,
    # Orgs participating in events → PARTICIPATES_IN
    (EntityCategory.ORGANIZATION, EntityCategory.EVENT): RelationType.PARTICIPATES_IN,
    # Orgs on projects → PARTICIPATES_IN
    (EntityCategory.ORGANIZATION, EntityCategory.PROJECT): RelationType.PARTICIPATES_IN,
    # Tech used by tech → USES
    (EntityCategory.TECHNOLOGY, EntityCategory.TECHNOLOGY): RelationType.USES,
    # Tech powering projects → USES
    (EntityCategory.TECHNOLOGY, EntityCategory.PROJECT): RelationType.USES,
    # Locations inside locations → LOCATED_IN
    (EntityCategory.LOCATION, EntityCategory.LOCATION): RelationType.LOCATED_IN,
    # Projects using tech → USES
    (EntityCategory.PROJECT, EntityCategory.TECHNOLOGY): RelationType.USES,
    # Projects on locations → LOCATED_IN
    (EntityCategory.PROJECT, EntityCategory.LOCATION): RelationType.LOCATED_IN,
    # Documents about anything → RELATED_TO
    (EntityCategory.DOCUMENT, EntityCategory.PROJECT): RelationType.RELATED_TO,
    (EntityCategory.DOCUMENT, EntityCategory.PERSON): RelationType.RELATED_TO,
    (EntityCategory.DOCUMENT, EntityCategory.ORGANIZATION): RelationType.RELATED_TO,
}
"""Subject/object type-pair → default :class:`RelationType` fallback.

Used only when :data:`PREDICATE_MAP` does not match the source fact's
predicate.  Every entry is a conservative guess that the operator
can correct during ingestion review.

The dict is keyed on ``(subject_category, object_category)`` so the
directionality of the relation is preserved — the same pair reversed
may map to a different default (e.g. ``(PERSON, ORG)`` → ``WORKS_AT``
but ``(ORG, PERSON)`` → ``RELATED_TO`` because the closed taxonomy
has no inverse-``WORKS_AT``).
"""


# Floor for the relation confidence.  When the source fact carries
# ``confidence=None`` we use this value, matching the SQL DDL default
# for ``memory.semantic_facts.confidence``.
_FLOOR_CONFIDENCE: Final[float] = DEFAULT_FACT_CONFIDENCE


class RelationExtractor:
    """Rule-based relation classifier for the Wave 2 extraction pipeline.

    The relation extractor is constructed with an
    :class:`EntityExtractor` and reuses it for type classification of
    the subject / object slots.  This keeps the L1 path synchronous
    and side-effect-free.

    Parameters
    ----------
    entity_extractor:
        The :class:`EntityExtractor` instance to use for type
        classification.  Must be already constructed with a valid
        :class:`EntityResolver`.
    """

    def __init__(self, entity_extractor: EntityExtractor) -> None:
        if not isinstance(entity_extractor, EntityExtractor):
            raise TypeError(
                "RelationExtractor requires an EntityExtractor instance; "
                f"got {type(entity_extractor).__name__}"
            )
        self._entity_extractor: EntityExtractor = entity_extractor

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_relations(
        self, fact: SemanticFact
    ) -> list[ExtractedRelation]:
        """Extract typed relations from a semantic fact.

        For a given fact the extractor returns a list with **up to
        one** :class:`ExtractedRelation` per ``(subject, object)``
        pair.  In the L1+L2 path the subject and object slots are
        treated as single entity mentions (no nested NER), so the
        list has length 0 or 1.

        Parameters
        ----------
        fact:
            The semantic fact to extract from.  See
            :class:`SemanticFact` for the attribute contract.

        Returns
        -------
        list[ExtractedRelation]
            Possibly-empty list of extracted relations.  Length 0 if
            either the subject or the object slot is empty.

        Raises
        ------
        KGExtractionError
            If the fact is missing a UUID or any required attribute.
        """
        fact_id = self._require_fact_id(fact)

        entities = self._entity_extractor.extract_entities(fact)
        if len(entities) < 2:
            # Either the subject or the object slot is empty / non-extractable.
            return []

        subject_entity, object_entity = entities[0], entities[1]
        relation_type = self.classify_relation(
            subject_entity.entity_type,
            fact.predicate,
            object_entity.entity_type,
        )
        confidence = self.compute_confidence(fact)

        return [
            ExtractedRelation(
                subject=subject_entity,
                predicate=str(fact.predicate),
                object_entity=object_entity,
                relation_type=relation_type,
                confidence=confidence,
                source_fact_id=fact_id,
            )
        ]

    def classify_relation(
        self,
        subject_type: EntityType,
        predicate: str,
        object_type: EntityType,
    ) -> RelationType:
        """Map a (subject_type, predicate, object_type) triple to a
        :class:`RelationType`.

        The classification proceeds in three stages:

        1. **Substring match against** :data:`PREDICATE_MAP` — the
           longest matching key wins, so ``"works_at"`` beats
           ``"works"``.  This handles the common case (English
           verbs produced by the consolidation layer).
        2. **Type-aware fallback** — when the predicate did not
           match, consult :data:`_TYPE_AWARE_FALLBACK` keyed on
           ``(subject_type, object_type)``.
        3. **Universal fallback** — :attr:`RelationType.RELATED_TO`
           if neither of the above produced a result.

        The method is pure — no I/O, no DB, no logging.

        Parameters
        ----------
        subject_type:
            The classified type of the subject entity.
        predicate:
            The raw predicate string from the source fact.  Will be
            lower-cased and stripped before lookup.
        object_type:
            The classified type of the object entity.

        Returns
        -------
        RelationType
            Always a closed-taxon relation — never ``None``.
        """
        # Stage 1: predicate substring match (longest-key-wins).
        rel_type = _match_predicate(predicate)
        if rel_type is not None:
            return rel_type

        # Stage 2: type-aware fallback.
        rel_type = _TYPE_AWARE_FALLBACK.get(
            (subject_type, object_type)
        )
        if rel_type is not None:
            return rel_type

        # Stage 3: universal fallback.
        return RelationType.RELATED_TO

    def compute_confidence(self, fact: SemanticFact) -> float:
        """Return the source fact's confidence as a float in ``[0, 1]``.

        The relation-level confidence equals the source fact's
        ``confidence`` field (clamped to ``[0.0, 1.0]``).  When the
        field is ``None`` we use :data:`DEFAULT_FACT_CONFIDENCE`.

        We deliberately do **not** combine this with the subject
        and object entity confidences — that is P17+ territory.  The
        L1+L2 path keeps the relation confidence traceable to the
        source fact so the operator can audit a single number.

        Parameters
        ----------
        fact:
            The semantic fact.  The ``confidence`` attribute is read
            but not mutated.

        Returns
        -------
        float
            Confidence in ``[0.0, 1.0]``.
        """
        raw = getattr(fact, "confidence", None)
        if raw is None:
            return _FLOOR_CONFIDENCE
        try:
            value = float(raw)
        except (TypeError, ValueError) as exc:
            raise KGExtractionError(
                "SemanticFact.confidence must be coercible to float",
                context={"got_type": type(raw).__name__, "got_value": repr(raw)},
            ) from exc
        if value < 0.0:
            return 0.0
        if value > 1.0:
            return 1.0
        return value

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _require_fact_id(fact: SemanticFact) -> uuid.UUID:
        """Return ``fact.id`` or raise :class:`KGExtractionError`."""
        fact_id = getattr(fact, "id", None)
        if not isinstance(fact_id, uuid.UUID):
            raise KGExtractionError(
                "SemanticFact.id must be a UUID",
                context={
                    "got_type": type(fact_id).__name__,
                    "got_value": repr(fact_id),
                },
            )
        return fact_id

    # ------------------------------------------------------------------
    # Read-only accessors (handy for tests / observability)
    # ------------------------------------------------------------------

    @property
    def entity_extractor(self) -> EntityExtractor:
        """Return the injected :class:`EntityExtractor` (read-only)."""
        return self._entity_extractor


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _match_predicate(predicate: object) -> RelationType | None:
    """Return the longest-key match from :data:`PREDICATE_MAP` or ``None``.

    Matching is case-insensitive and whitespace-tolerant.  The
    predicate is lower-cased and stripped once, then every
    ``PREDICATE_MAP`` key is checked for substring containment in
    the cleaned predicate.

    The longest key wins, so ``"works_at"`` (length 8) beats
    ``"works"`` (length 5) when both could match.  This is the
    standard longest-substring-match idiom — see the unit tests
    in :mod:`guinevere.knowledge_graph.tests`.

    Parameters
    ----------
    predicate:
        The raw predicate value.  ``None`` and non-string values
        are coerced via ``str()`` and stripped.

    Returns
    -------
    RelationType | None
        The matched relation type, or ``None`` if no key matches.
    """
    if predicate is None:
        return None
    try:
        cleaned = str(predicate).strip().lower()
    except (TypeError, AttributeError):
        # ``str()`` itself is total for Python objects, but a pathological
        # ``__str__`` or one that returns a non-string can still raise
        # ``TypeError`` / ``AttributeError`` on the chained ``.strip()``.
        # We treat both as "no match" — the relation will fall through to
        # the type-aware fallback.  Never let a stringification failure
        # crash the extractor.
        return None
    if not cleaned:
        return None

    best_key: str | None = None
    best_type: RelationType | None = None
    for key, rel_type in PREDICATE_MAP.items():
        # ``key in cleaned`` is the contract: the gazetteer key is a
        # substring of the predicate.  This catches prefixes
        # (``"works_at_home"`` → ``"works_at"``) and infixes
        # (``"currently_works_at"`` → ``"works_at"``).
        if key in cleaned:
            if best_key is None or len(key) > len(best_key):
                best_key = key
                best_type = rel_type
    return best_type


# ---------------------------------------------------------------------------
# Public re-exports
# ---------------------------------------------------------------------------

__all__ = [
    "RelationExtractor",
    # Internal helpers exposed for unit tests
    "_match_predicate",
    "_TYPE_AWARE_FALLBACK",
]
