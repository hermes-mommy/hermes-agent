"""Smoke test for P16-007 NER/RE Extractor Module.

Run with:  python -m src.knowledge_graph.tests.smoke_extraction
or:        python smoke_extraction.py
"""
from __future__ import annotations

import sys
import uuid

from guinvere.knowledge_graph.extraction import (
    EntityCategory,
    EntityExtractor,
    ExtractedEntity,
    ExtractedRelation,
    RelationExtractor,
    RelationType,
    SemanticFact,
)


class _MockResolver:
    """Stub for EntityResolver — the L1+L2 path does not invoke it."""


class _MockFact:
    """Minimal stand-in for a ``memory.semantic_facts`` row.

    Satisfies the :class:`SemanticFact` Protocol structurally.
    """

    def __init__(
        self,
        subject: str,
        predicate: str,
        object_val: str,
        confidence: float | None = 0.9,
    ) -> None:
        self.id = uuid.uuid4()
        self.subject = subject
        self.predicate = predicate
        self.object_val = object_val
        self.fact_type = "semantic"
        self.confidence = confidence
        self.source_episode = None


def _summarise_entity(entity: ExtractedEntity) -> str:
    return f"{entity.text!r}:{entity.entity_type.name}@{entity.confidence:.2f}"


def _summarise_relation(relation: ExtractedRelation) -> str:
    return (
        f"{relation.relation_type.name} "
        f"({relation.predicate!r}) "
        f"conf={relation.confidence:.2f}"
    )


def main() -> int:
    ee = EntityExtractor(_MockResolver())
    re_ = RelationExtractor(ee)

    print("== Test 1: Faiz works_at OpenAI ==")
    fact = _MockFact("Faiz", "works_at", "OpenAI")
    entities = ee.extract_entities(fact)
    relations = re_.extract_relations(fact)
    for e in entities:
        print(f"  entity: {_summarise_entity(e)}")
    for r in relations:
        print(f"  relation: {_summarise_relation(r)}")
    assert len(entities) == 2
    assert entities[0].entity_type == EntityCategory.PERSON
    assert entities[1].entity_type == EntityCategory.ORGANIZATION
    assert len(relations) == 1
    assert relations[0].relation_type == RelationType.WORKS_AT

    print("\n== Test 2: Guinevere uses PostgreSQL 16 ==")
    fact = _MockFact("Guinevere", "uses", "PostgreSQL 16")
    entities = ee.extract_entities(fact)
    relations = re_.extract_relations(fact)
    for e in entities:
        print(f"  entity: {_summarise_entity(e)}")
    for r in relations:
        print(f"  relation: {_summarise_relation(r)}")
    assert entities[0].entity_type == EntityCategory.PROJECT
    assert entities[1].entity_type == EntityCategory.TECHNOLOGY
    assert relations[0].relation_type == RelationType.USES

    print("\n== Test 3: Faiz lives_in Jakarta ==")
    fact = _MockFact("Faiz", "lives_in", "Jakarta")
    entities = ee.extract_entities(fact)
    relations = re_.extract_relations(fact)
    for e in entities:
        print(f"  entity: {_summarise_entity(e)}")
    for r in relations:
        print(f"  relation: {_summarise_relation(r)}")
    assert entities[1].entity_type == EntityCategory.LOCATION
    assert relations[0].relation_type == RelationType.LOCATED_IN

    print("\n== Test 4: Faiz works_at Google Inc. ==")
    fact = _MockFact("Faiz", "works_at", "Google Inc.")
    entities = ee.extract_entities(fact)
    for e in entities:
        print(f"  entity: {_summarise_entity(e)}")
    assert entities[1].entity_type == EntityCategory.ORGANIZATION

    print("\n== Test 5: classify_entity_type direct calls ==")
    cases = [
        ("Faiz", EntityCategory.PERSON),
        ("OpenAI", EntityCategory.ORGANIZATION),
        ("Jakarta", EntityCategory.LOCATION),
        ("PostgreSQL 16", EntityCategory.TECHNOLOGY),
        ("Hermes Agent", EntityCategory.PROJECT),
        ("Guinevere", EntityCategory.PROJECT),
        ("joy", EntityCategory.EMOTION),
        ("friend", EntityCategory.RELATIONSHIP),
        ("Dr. Smith", EntityCategory.PERSON),
        ("Microsoft Corporation", EntityCategory.ORGANIZATION),
    ]
    for text, expected in cases:
        got = ee.classify_entity_type(text)
        marker = "OK" if got == expected else "FAIL"
        print(f"  [{marker}] {text!r:35s} -> {got.name:15s} (expected {expected.name})")
        assert got == expected, f"Expected {expected.name} for {text!r}, got {got.name}"

    print("\n== Test 6: classify_relation direct calls (type-aware fallback) ==")
    cases = [
        (EntityCategory.PERSON, "unknown_pred", EntityCategory.ORGANIZATION, RelationType.WORKS_AT),
        (EntityCategory.PERSON, "unknown_pred", EntityCategory.LOCATION, RelationType.LOCATED_IN),
        (EntityCategory.PERSON, "unknown_pred", EntityCategory.PERSON, RelationType.KNOWS),
        (EntityCategory.PERSON, "unknown_pred", EntityCategory.TECHNOLOGY, RelationType.USES),
        (EntityCategory.LOCATION, "unknown_pred", EntityCategory.LOCATION, RelationType.LOCATED_IN),
    ]
    for st, p, ot, expected in cases:
        got = re_.classify_relation(st, p, ot)
        marker = "OK" if got == expected else "FAIL"
        print(f"  [{marker}] ({st.name}, {p!r}, {ot.name}) -> {got.name}")
        assert got == expected

    print("\n== Test 7: compute_confidence ==")
    cases = [
        (_MockFact("a", "b", "c", confidence=None), 0.5),
        (_MockFact("a", "b", "c", confidence=0.95), 0.95),
        (_MockFact("a", "b", "c", confidence=-0.5), 0.0),
        (_MockFact("a", "b", "c", confidence=1.5), 1.0),
    ]
    for fact, expected in cases:
        got = re_.compute_confidence(fact)
        marker = "OK" if abs(got - expected) < 1e-9 else "FAIL"
        print(f"  [{marker}] conf={fact.confidence} -> {got} (expected {expected})")
        assert abs(got - expected) < 1e-9

    print("\n== Test 8: PREDICATE_MAP longest-key-wins ==")
    # `works_at` is longer than `works`, so a predicate containing both
    # must map to WORKS_AT, not RELATED_TO.
    fact = _MockFact("Faiz", "currently_works_at", "OpenAI")
    relations = re_.extract_relations(fact)
    assert relations[0].relation_type == RelationType.WORKS_AT
    print(f"  [OK] currently_works_at -> {relations[0].relation_type.name}")

    print("\n== Test 9: empty slot ==")
    fact = _MockFact("Faiz", "works_at", "")
    entities = ee.extract_entities(fact)
    relations = re_.extract_relations(fact)
    print(f"  entities: {len(entities)} (expected 1)")
    print(f"  relations: {len(relations)} (expected 0)")
    assert len(entities) == 1
    assert len(relations) == 0

    print("\n== Test 10: dataclass validation ==")
    # Empty text must raise.
    try:
        ExtractedEntity(
            text="",
            entity_type=EntityCategory.PERSON,
            confidence=0.9,
            source_fact_id=uuid.uuid4(),
        )
        print("  [FAIL] empty text was accepted")
        return 1
    except ValueError as exc:
        print(f"  [OK] empty text rejected: {exc}")
    # Out-of-range confidence must raise.
    try:
        ExtractedEntity(
            text="Faiz",
            entity_type=EntityCategory.PERSON,
            confidence=1.5,
            source_fact_id=uuid.uuid4(),
        )
        print("  [FAIL] confidence > 1.0 was accepted")
        return 1
    except ValueError as exc:
        print(f"  [OK] confidence > 1.0 rejected: {exc}")

    print("\nALL_TESTS_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
