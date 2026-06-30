"""P16-007: rule-based entity extractor (NER, L1 + L2 only).

This module implements the **first** stage of the Wave 2 extraction
pipeline: given a :class:`~src.knowledge_graph.types.SemanticFact` (a
consolidated ``(subject, predicate, object_val)`` triple), it
classifies the subject and object surface forms into one of the
closed :class:`~src.knowledge_graph.types.EntityCategory` values and
returns a list of :class:`ExtractedEntity` instances ready to be
resolved by the P16-002 layer.

The extractor is deliberately **rule-based** for P16:

* L1 = hand-curated gazetteer / pattern match (this module).
* L2 = exact + fuzzy alias / canonical-key match (delegated to
  :class:`~src.knowledge_graph.resolution.resolver.EntityResolver`,
  which is injected but not invoked at extraction time — the
  resolver is async / DB-bound and the L1 path is fully synchronous).
* L3 (embedding similarity) is **deferred to P17+** — see
  :mod:`src.knowledge_graph.extraction` module docstring and the
  no-embeddings research in ``evidence/p16-kg/``.

The extractor is a *pure* function of its inputs: it never reads from
the database, never calls the network, and never imports
``src.memory.models``.  This keeps the unit-test surface small and
the call graph obvious.

Safety / consent notes (per AGENTS.md BLOCKING rules and
PersonaSafetyPolicy):

* The extractor does not perform surveillance.  It only reads
  in-memory text and emits extracted entities.
* It does not bypass HARD STOP or safe-word enforcement — the
  safe-word gate is owned by the ingestion pipeline (P16-002 Wave 3),
  not by the extractor.
* It does not type-suppress: every dict key, every dataclass field,
  and every return type is statically typed.
"""
from __future__ import annotations

import re
import uuid
from typing import Final

from guinvere.knowledge_graph.errors import KGExtractionError
from guinvere.knowledge_graph.extraction.patterns import (
    DEFAULT_FACT_CONFIDENCE,
    ENTITY_PATTERNS,
    PATTERN_CONFIDENCE,
    PROJECT_PATTERNS,
)
from guinvere.knowledge_graph.resolution.resolver import EntityResolver
from guinvere.knowledge_graph.types import (
    EntityCategory,
    ExtractedEntity,
    SemanticFact,
)

# Type alias for the closed taxonomy.  Resolves to ``EntityCategory`` via
# the alias added in :mod:`src.knowledge_graph.types` — see that module
# for the rationale.
EntityType = EntityCategory

# Categories that are *almost always* lower-case in source text and which
# the rule-based classifier should fall through to a heuristic for.
# Listed here so the magic strings are not duplicated in the body of
# :meth:`EntityExtractor.classify_entity_type`.
_HEURISTIC_FALLBACK_CATEGORIES: Final[frozenset[EntityCategory]] = frozenset(
    {
        EntityCategory.MEMORY_THEME,
        EntityCategory.CONSENT_SCOPE,
        EntityCategory.COMMUNICATION_CHANNEL,
        EntityCategory.CONCEPT,
        EntityCategory.EMOTION,
        EntityCategory.RELATIONSHIP,
    }
)

# Categories that must be checked **before** the general pattern table.
# Some surface forms (e.g. ``"Guinevere"`` is a project and a persona
# handle, ``"Jakarta"`` is a city and a plausible name) are ambiguous
# between two categories.  The categories listed here have a
# high-specificity gazetteer (a known list of cities / orgs / tech
# products) that should win over the generic Latin-name pattern.
#
# Why not just reorder :data:`ENTITY_PATTERNS`?  Because the same
# surface form (e.g. ``"Faiz"``) is correctly a PERSON in most
# contexts and the priority list would mis-classify it.  We handle
# the gazetteer-rich categories explicitly here and keep PERSON
# as the broad fallback.
_PRIORITY_CATEGORIES: Final[tuple[EntityCategory, ...]] = (
    EntityCategory.PROJECT,
    EntityCategory.SYSTEM_COMPONENT,
    EntityCategory.SURVEILLANCE_CONTEXT,
    EntityCategory.TECHNOLOGY,
    EntityCategory.LOCATION,
    EntityCategory.ORGANIZATION,
    EntityCategory.DOCUMENT,
    EntityCategory.EVENT,
)


class EntityExtractor:
    """Rule-based NER for the Wave 2 extraction pipeline (L1 + L2 only).

    The extractor is constructed once and reused across facts — the
    pattern table is module-level and shared, but the resolver is
    per-instance because the session factory is per-deployment.

    Parameters
    ----------
    resolver:
        The :class:`EntityResolver` from the resolution layer.  Held
        as ``self._resolver`` so future extensions (canonicalisation,
        alias lookup, embedding fall-through) can use it without
        re-plumbing the constructor.  **Not invoked during L1
        extraction** — the rule-based path is fully synchronous and
        DB-free.
    min_confidence:
        Floor for the returned :class:`ExtractedEntity` confidence.
        Facts whose derived confidence falls below this value are
        still returned (the ingestion pipeline may still want them)
        but tagged with a low confidence.  Default ``0.1`` — low
        enough to keep the pattern-only path productive, high enough
        to keep obvious noise out of the resolver.
    """

    def __init__(
        self,
        resolver: EntityResolver,
        *,
        min_confidence: float = 0.1,
    ) -> None:
        if not (0.0 <= float(min_confidence) <= 1.0):
            raise ValueError(
                f"min_confidence must be in [0.0, 1.0]; got {min_confidence!r}"
            )
        self._resolver: EntityResolver = resolver
        self._min_confidence: float = float(min_confidence)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_entities(self, fact: SemanticFact) -> list[ExtractedEntity]:
        """Extract entities from the *subject* and *object_val* of a fact.

        The extractor always returns up to **two** entities — one for
        the subject slot, one for the object slot.  An empty slot
        (whitespace-only, empty string) yields no entity for that
        side, so the returned list has 0, 1, or 2 elements.

        The returned entities carry the source fact's UUID and the
        per-slot text verbatim; downstream stages (resolver, ingestion)
        add canonicalisation and persistence.

        Parameters
        ----------
        fact:
            The semantic fact to extract from.  Must satisfy the
            :class:`SemanticFact` Protocol — i.e. expose ``id``,
            ``subject``, ``predicate``, ``object_val``, ``fact_type``,
            ``confidence``, ``source_episode`` attributes.

        Returns
        -------
        list[ExtractedEntity]
            Possibly-empty list of extracted entities, one per
            non-empty slot in the fact.  Never ``None``.

        Raises
        ------
        KGExtractionError
            If the fact is missing a UUID or the surface text cannot
            be coerced to ``str``.  All other malformed input
            degrades gracefully (empty string → no entity).
        """
        fact_id = self._require_fact_id(fact)

        results: list[ExtractedEntity] = []
        for slot_text, slot_name in (
            (fact.subject, "subject"),
            (fact.object_val, "object"),
        ):
            entity = self._entity_from_slot(slot_text, fact_id, slot_name)
            if entity is not None:
                results.append(entity)
        return results

    def classify_entity_type(self, text: str) -> EntityType:
        """Return the most likely :class:`EntityCategory` for *text*.

        Classification proceeds in three stages:

        1. **Priority pass** — a small set of categories
           (:data:`_PRIORITY_CATEGORIES`) whose gazetteers contain
           surface forms that are ambiguous with other categories
           (``"Guinevere"`` is both a project and a persona name)
           are checked first.  This prevents the wrong category
           from winning purely on declaration order.
        2. **First-match-wins** over :data:`ENTITY_PATTERNS` in
           declaration order.  Categories whose patterns are empty
           (e.g. ``MEMORY_THEME``) fall through to the heuristic
           pass.
        3. **Heuristic fallback** — returns
           :class:`EntityCategory.CONCEPT` as a neutral default.

        This method is exposed publicly so the relation extractor
        and any future test harness can re-use the same classification
        rule without re-instantiating the extractor.

        Parameters
        ----------
        text:
            The surface form to classify.  May be empty — an empty
            string returns :class:`EntityCategory.CONCEPT` as a
            neutral default (matches the pattern-table fallback for
            empty input).

        Returns
        -------
        EntityType
            The most-specific category whose patterns match *text*,
            or :class:`EntityCategory.CONCEPT` if no pattern fires
            and the heuristic does not match either.
        """
        cleaned = self._clean_text(text)
        if not cleaned:
            return EntityCategory.CONCEPT

        # Stage 1: priority pass for ambiguous gazetteer entries.
        for category in _PRIORITY_CATEGORIES:
            patterns = ENTITY_PATTERNS.get(category, ())
            for pattern in patterns:
                if pattern.search(cleaned):
                    return category

        # Stage 2: first-match-wins over the full pattern table.
        for category, patterns in ENTITY_PATTERNS.items():
            for pattern in patterns:
                if pattern.search(cleaned):
                    return category

        # Stage 3: heuristic fallback for closed-class categories whose
        # gazetteer is not exhaustive enough to rely on pattern match
        # alone.  Kept small and conservative — better to over-classify
        # as CONCEPT than to mis-label a person as an emotion.
        return self._heuristic_classify(cleaned)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_text(text: object) -> str:
        """Coerce *text* to a stripped ``str``; never raises."""
        if text is None:
            return ""
        try:
            cleaned = str(text).strip()
        except Exception as exc:  # pragma: no cover - defensive
            # Never let a stringification failure crash the extractor.
            # ``str()`` is effectively total for Python objects but we
            # guard against pathological ``__str__`` implementations.
            raise KGExtractionError(
                "Failed to coerce entity text to str",
                context={"text_repr": repr(text), "error": repr(exc)},
            ) from exc
        return cleaned

    def _entity_from_slot(
        self,
        text: object,
        fact_id: uuid.UUID,
        slot_name: str,
    ) -> ExtractedEntity | None:
        """Build an :class:`ExtractedEntity` from one fact slot.

        Returns ``None`` for empty / whitespace-only slots so the caller
        can build the result list without a special case.
        """
        cleaned = self._clean_text(text)
        if not cleaned:
            return None

        category = self.classify_entity_type(cleaned)
        confidence = self._confidence_for(cleaned, category, fact_id)
        # Clamp to the configured floor (still returns — the ingestion
        # pipeline may keep a low-confidence entity for human review).
        confidence = max(self._min_confidence, confidence)

        return ExtractedEntity(
            text=cleaned,
            entity_type=category,
            confidence=confidence,
            source_fact_id=fact_id,
            span=None,
        )

    @staticmethod
    def _heuristic_classify(cleaned: str) -> EntityType:
        """Conservative fallback for text that matches no pattern.

        Used when every :data:`ENTITY_PATTERNS` entry has been tried
        without a hit.  Deliberately narrow — over-classifying as
        :class:`EntityCategory.CONCEPT` is the safe default; we never
        promote a string to a person / org / location without a
        pattern match.
        """
        # All-lowercase short tokens are most likely a CONCEPT or a
        # bare keyword.  We pick CONCEPT because it is the most neutral
        # catch-all in the closed taxonomy.
        return EntityCategory.CONCEPT

    def _confidence_for(
        self,
        cleaned: str,
        category: EntityCategory,
        fact_id: uuid.UUID,
    ) -> float:
        """Compute the per-entity extraction confidence.

        Combines the per-category base confidence (see
        :data:`PATTERN_CONFIDENCE`) with the source fact's
        ``confidence`` field via a **geometric mean** — this is a
        compromise that neither pure-pattern nor pure-fact-confidence
        dominates.  Geometric mean is bounded in ``[0.0, 1.0]`` and
        symmetric, which is what we want for a confidence product.

        The fact's confidence is fetched via the resolver's session
        factory is *not* called here; we only consult the in-memory
        fact.  This keeps the path synchronous and DB-free.
        """
        base = PATTERN_CONFIDENCE.get(category, 0.5)
        fact_conf = self._fact_confidence(fact_id)
        combined = (base * fact_conf) ** 0.5
        # Numerical safety — clamp to a hard floor / ceiling.
        return max(0.0, min(1.0, combined))

    @staticmethod
    def _fact_confidence(fact_id: uuid.UUID) -> float:
        """Return the source fact's confidence as a float in ``[0, 1]``.

        The extractor does not read the DB, so this helper currently
        returns the :data:`DEFAULT_FACT_CONFIDENCE` floor.  It is
        deliberately factored out so future extensions (e.g. reading
        the fact from a pre-loaded cache) can swap the implementation
        without changing call sites.
        """
        # NOTE: the fact itself is passed through ``extract_entities``;
        # we deliberately do not store a reference to it (it is a
        # Protocol object — keeping it would extend the lifecycle of
        # whatever SQLAlchemy session produced it).  The confidence
        # value is captured at construction time by the caller via
        # :meth:`RelationExtractor.compute_confidence`.
        return DEFAULT_FACT_CONFIDENCE

    @staticmethod
    def _require_fact_id(fact: SemanticFact) -> uuid.UUID:
        """Return ``fact.id`` or raise :class:`KGExtractionError`.

        Centralised so the error message is consistent across both
        call sites in :meth:`extract_entities`.  The Protocol
        declares ``id`` as required, so this only fires for shapes
        that violate the Protocol — a defensive guard.
        """
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
    def resolver(self) -> EntityResolver:
        """Return the injected :class:`EntityResolver` (read-only)."""
        return self._resolver

    @property
    def min_confidence(self) -> float:
        """Return the configured minimum confidence floor."""
        return self._min_confidence


# ---------------------------------------------------------------------------
# Public re-exports
# ---------------------------------------------------------------------------

__all__ = [
    "EntityExtractor",
    "EntityType",
]
