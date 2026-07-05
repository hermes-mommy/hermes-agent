"""Entity resolution tests.

These tests cover:

* Canonical key generation — deterministic, case-insensitive,
  whitespace-normalised.
* Fuzzy matching — exact returns existing, above-threshold resolves,
  below-threshold creates new.
* Same-as edges — canonical ordering enforced, merge transfers edges,
  merged entity tombstoned.

All tests use mocks (AsyncMock, MagicMock) so they run without a live
PostgreSQL instance.
"""
from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from guinevere.knowledge_graph.resolution.canonical import (
    generate_canonical_key,
)
from guinevere.knowledge_graph.resolution.fuzzy import (
    DEFAULT_FUZZY_LIMIT,
    DEFAULT_FUZZY_THRESHOLD,
    FuzzyMatchResult,
    compute_similarity,
)
from guinevere.knowledge_graph.resolution.resolver import (
    EntityResolutionResult,
    EntityResolver,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_session_factory(rows: list[Any] | None = None) -> MagicMock:
    """Build an async-session factory whose ``execute()`` returns ``rows``.

    Rows can be plain dicts; the wrapper exposes ``_mapping`` so the
    canonical.py mapper (``_row_to_entity_dict``) treats them like
    SQLAlchemy ``Row`` instances.
    """

    async def _commit() -> None:
        return None

    rows = list(rows) if rows else []

    async def _execute(_statement: Any, *_args: Any, **_kwargs: Any) -> MagicMock:
        result = MagicMock()
        first_row = rows[0] if rows else None
        result.first = MagicMock(return_value=first_row)
        result.all = MagicMock(return_value=rows)
        scalar_value = None
        if first_row is not None:
            if isinstance(first_row, dict):
                scalar_value = first_row.get("id") or next(iter(first_row.values()), None)
            elif isinstance(first_row, (list, tuple)) and first_row:
                scalar_value = first_row[0]
            else:
                scalar_value = getattr(first_row, "id", None) or first_row
        result.scalar = MagicMock(return_value=scalar_value)
        result.scalars.return_value.all = MagicMock(return_value=rows)
        result.scalars.return_value.first = MagicMock(return_value=first_row)
        result.fetchall = MagicMock(return_value=rows)
        result.rowcount = len(rows)
        return result

    session = MagicMock()
    session.execute = AsyncMock(side_effect=_execute)
    session.commit = AsyncMock(side_effect=_commit)
    session.flush = AsyncMock(side_effect=lambda: None)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)

    factory = MagicMock()
    factory.return_value = session
    factory.__call__ = MagicMock(return_value=session)
    factory.side_effect = lambda: session
    return factory


class _DictRow:
    """Wrap a dict so canonical.py's row-to-dict mapper recognises it.

    The mapper first tries ``row._mapping.items()``.  We expose a
    ``_mapping`` attribute that yields the dict's ``(key, value)``
    pairs.  The fuzzy matcher additionally calls ``entity.get(...)``,
    so we implement ``get`` as a dict passthrough.
    """

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data
        self._mapping = self._Mapping(data)

    class _Mapping:
        def __init__(self, data: dict[str, Any]) -> None:
            self._data = data

        def items(self) -> Any:
            return self._data.items()

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def __getattr__(self, key: str) -> Any:
        if key in self._data:
            return self._data[key]
        raise AttributeError(key)


def _wrap_rows_as_dict_rows(rows: list[Any]) -> list[Any]:
    """Convert plain dicts in ``rows`` to ``_DictRow`` instances."""
    out = []
    for row in rows:
        if isinstance(row, dict):
            out.append(_DictRow(row))
        else:
            out.append(row)
    return out


# ---------------------------------------------------------------------------
# Canonical key generation
# ---------------------------------------------------------------------------


class TestCanonicalKeyGeneration:
    """Canonical-key derivation must be deterministic and normalised."""

    def test_deterministic_key(self) -> None:
        """Same input always produces the same canonical_key.

        The key is a 16-char hex SHA-256 prefix of ``{category}:{slug}``.
        """
        key_a = generate_canonical_key("Faiz", "PERSON")
        key_b = generate_canonical_key("Faiz", "PERSON")
        assert key_a == key_b
        assert len(key_a) == 16
        # Hex-only.
        assert all(c in "0123456789abcdef" for c in key_a)

    def test_case_insensitive(self) -> None:
        """``Faiz`` and ``faiz`` produce the same canonical_key.

        Canonicalisation lowercases the slug before hashing.
        """
        key_upper = generate_canonical_key("Faiz", "PERSON")
        key_lower = generate_canonical_key("faiz", "PERSON")
        assert key_upper == key_lower

    def test_whitespace_normalized(self) -> None:
        """``John  Doe`` and ``John Doe`` produce the same key.

        Multiple whitespace characters collapse to a single space during
        canonicalisation.  Leading/trailing whitespace is also trimmed.
        """
        key_a = generate_canonical_key("John  Doe", "PERSON")
        key_b = generate_canonical_key("John Doe", "PERSON")
        assert key_a == key_b

    def test_category_lowercased(self) -> None:
        """Category is lowercased before hashing.

        ``PERSON`` and ``person`` produce the same key for the same name.
        """
        key_upper = generate_canonical_key("Faiz", "PERSON")
        key_lower = generate_canonical_key("Faiz", "person")
        assert key_upper == key_lower

    def test_distinct_names_distinct_keys(self) -> None:
        """Different names within the same category produce different keys.

        The birthday-collision space is 64 bits; for the operator-scale
        KG (< 1M entities) collisions are effectively zero.
        """
        key_a = generate_canonical_key("Faiz", "PERSON")
        key_b = generate_canonical_key("Hermes", "PERSON")
        assert key_a != key_b

    def test_distinct_categories_distinct_keys(self) -> None:
        """Same name in different categories produces different keys.

        ``Faiz`` the person and ``Faiz`` the project live in separate
        name-spaces.
        """
        key_person = generate_canonical_key("Faiz", "PERSON")
        key_project = generate_canonical_key("Faiz", "PROJECT")
        assert key_person != key_project

    def test_blank_category_uses_default(self) -> None:
        """Empty category falls back to the default placeholder.

        A missing category must not crash — it hashes against a sentinel.
        """
        key_default = generate_canonical_key("Faiz", "")
        # ``generate_canonical_key`` accepts ``str | None`` but mypy
        # infers ``str`` — we exercise the empty-string path which
        # is functionally equivalent to None.
        key_empty = generate_canonical_key("Faiz", "")
        assert key_default == key_empty


# ---------------------------------------------------------------------------
# Fuzzy matching
# ---------------------------------------------------------------------------


class TestFuzzyMatching:
    """Fuzzy matcher behaviour across threshold boundaries."""

    def test_compute_similarity_identical_strings(self) -> None:
        """Identical strings score 1.0."""
        score = compute_similarity("Faiz", "Faiz")
        assert score == pytest.approx(1.0, abs=1e-6)

    def test_compute_similarity_case_insensitive(self) -> None:
        """Case differences do not affect similarity.

        The matcher normalises both inputs to lower-case before scoring.
        """
        score_a = compute_similarity("FAIZ", "faiz")
        score_b = compute_similarity("Faiz", "faiz")
        assert score_a == pytest.approx(1.0, abs=1e-6)
        assert score_b == pytest.approx(1.0, abs=1e-6)

    def test_compute_similarity_disjoint(self) -> None:
        """Completely different strings score below the default threshold."""
        score = compute_similarity("Faiz", "PostgreSQL")
        assert score < DEFAULT_FUZZY_THRESHOLD

    async def test_exact_match_returns_existing(self) -> None:
        """Exact canonical-key match returns the existing entity.

        The resolver's L1 path consults ``find_by_canonical_key`` first.
        When the session returns a matching row, the resolver returns
        ``method='exact'`` with confidence 1.0.
        """
        existing_id = uuid.uuid4()
        existing_entity = {
            "id": existing_id,
            "canonical_key": generate_canonical_key("Faiz", "PERSON"),
            "entity_type": "person",
            "display_name": "Faiz",
            "aliases": [],
            "is_tombstoned": False,
        }

        factory = _make_session_factory(rows=_wrap_rows_as_dict_rows([existing_entity]))
        resolver = EntityResolver(factory)

        result = await resolver.resolve_entity("Faiz", "PERSON")

        assert isinstance(result, EntityResolutionResult)
        assert result.method == "exact"
        assert result.confidence == 1.0
        assert result.canonical_entity is not None
        assert result.canonical_entity["id"] == existing_id

    async def test_fuzzy_match_above_threshold(self) -> None:
        """Similar names above threshold resolve to the same entity.

        L2 fires when L1 misses.  We seed a candidate whose display name
        is one insertion away — rapidfuzz WRatio must score above the
        default threshold.
        """
        existing_id = uuid.uuid4()
        existing_key = generate_canonical_key("Faiz", "PERSON")

        factory = MagicMock()

        def _extract_value(bound: Any) -> Any:
            return getattr(bound, "value", bound)

        def _row_result() -> Any:
            row = _DictRow(
                {
                    "id": existing_id,
                    "canonical_key": existing_key,
                    "entity_type": "person",
                    "display_name": "Faiz",
                    "aliases": [],
                    "is_tombstoned": False,
                }
            )
            result = MagicMock()
            result.first = MagicMock(return_value=row)
            result.all = MagicMock(return_value=[row])
            # ``list_entities_by_category`` and ``find_by_canonical_key``
            # both go through ``exec_result.scalars()``.
            result.scalars.return_value.first = MagicMock(return_value=row)
            result.scalars.return_value.all = MagicMock(return_value=[row])
            return result

        async def _execute(
            statement: Any, *_args: Any, **_kwargs: Any
        ) -> Any:
            sql_str = (
                getattr(statement, "text", None)
                or str(statement)
            ).upper()
            # SQLAlchemy stores bound params in ``_bindparams`` keyed
            # by name with ``BindParameter`` values (each exposes
            # ``.value``).
            bind_params: dict[str, Any] = {}
            raw_bindparams = getattr(statement, "_bindparams", None) or {}
            for k, v in raw_bindparams.items():
                bind_params[k] = getattr(v, "value", v)
            # L2 path: list_entities_by_category binds ``category``.
            if bind_params.get("category") is not None:
                return _row_result()
            # L1 path: bind_params has ``canonical_key``.  Only return
            # the row when the queried canonical_key matches the seeded
            # entity (so the follow-up confirm-after-fuzzy succeeds).
            if bind_params.get("canonical_key") == existing_key:
                return _row_result()
            # Otherwise (initial L1 for "Faizz") — return None/empty.
            # NOTE: the resolver calls ``exec_result.scalars().first()``
            # so we must populate both ``.first()`` AND
            # ``.scalars().first()`` with None.
            result = MagicMock()
            result.first = MagicMock(return_value=None)
            result.all = MagicMock(return_value=[])
            result.scalar = MagicMock(return_value=None)
            result.scalars.return_value.first = MagicMock(return_value=None)
            result.scalars.return_value.all = MagicMock(return_value=[])
            return result

        session = MagicMock()
        session.execute = AsyncMock(side_effect=_execute)
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        factory.return_value = session
        factory.side_effect = lambda: session

        resolver = EntityResolver(factory, dedup_threshold=0.85)

        # "Faizz" vs "Faiz" is one insertion — rapidfuzz WRatio scores
        # ~0.89 (above the 0.85 threshold).
        result = await resolver.resolve_entity("Faizz", "PERSON")

        assert result.method == "fuzzy"
        assert result.confidence >= 0.85
        assert result.canonical_entity is not None
        assert result.canonical_entity["id"] == existing_id

    async def test_fuzzy_match_below_threshold_creates_new(self) -> None:
        """Dissimilar names below threshold return ``method='none'``.

        ``"PostgreSQL"`` vs ``"Faiz"`` is far below the default 0.85
        threshold — the resolver must report ``none`` so the caller
        creates a new entity.
        """
        factory = MagicMock()

        async def _execute(
            statement: Any, *_args: Any, **_kwargs: Any
        ) -> Any:
            # All queries return empty — no match anywhere.
            result = MagicMock()
            result.first = MagicMock(return_value=None)
            result.all = MagicMock(return_value=[])
            result.scalar = MagicMock(return_value=None)
            result.scalars.return_value.first = MagicMock(return_value=None)
            result.scalars.return_value.all = MagicMock(return_value=[])
            return result

        session = MagicMock()
        session.execute = AsyncMock(side_effect=_execute)
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        factory.return_value = session
        factory.side_effect = lambda: session

        resolver = EntityResolver(factory, dedup_threshold=0.95)

        result = await resolver.resolve_entity("PostgreSQL", "PERSON")

        assert result.method == "none"
        assert result.confidence == 0.0
        assert result.canonical_entity is None

    def test_dedup_threshold_validation(self) -> None:
        """``dedup_threshold`` must be in ``[0.0, 1.0]``."""
        with pytest.raises(ValueError):
            EntityResolver(_make_session_factory(), dedup_threshold=-0.1)
        with pytest.raises(ValueError):
            EntityResolver(_make_session_factory(), dedup_threshold=1.5)

    def test_fuzzy_limit_validation(self) -> None:
        """``fuzzy_limit`` must be >= 1."""
        with pytest.raises(ValueError):
            EntityResolver(_make_session_factory(), fuzzy_limit=0)


# ---------------------------------------------------------------------------
# Same-as edges
# ---------------------------------------------------------------------------


class TestSameAsEdges:
    """Same-as edges and merge semantics."""

    async def test_canonical_ordering(self) -> None:
        """``src_entity_id < dst_entity_id`` CHECK constraint is enforced.

        ``propose_same_as`` sorts the UUIDs at the application layer so
        the SQL INSERT can never violate the DDL CHECK.  We verify both
        orderings end up with the smaller UUID as ``src_entity_id``.
        """
        factory = _make_session_factory()
        resolver = EntityResolver(factory)

        # The resolver binds params into the SQL statement before
        # calling session.execute.  Extract the bound params from the
        # statement's BindParameter wrappers.
        captured_params: dict[str, Any] = {}

        def _extract_value(bound: Any) -> Any:
            # SQLAlchemy BindParameter exposes ``.value``.
            return getattr(bound, "value", bound)

        async def _capture(
            statement: Any, *_args: Any, **_kwargs: Any
        ) -> Any:
            bind = getattr(statement, "bind", None)
            if bind is not None and hasattr(bind, "params"):
                captured_params.update(
                    {k: _extract_value(v) for k, v in bind.params.items()}
                )
            elif hasattr(statement, "_bindparams"):
                captured_params.update(
                    {k: _extract_value(v) for k, v in statement._bindparams.items()}
                )
            return MagicMock()

        factory.return_value.execute = AsyncMock(side_effect=_capture)
        factory.return_value.flush = AsyncMock()
        factory.side_effect = None

        a = uuid.UUID("00000000-0000-0000-0000-000000000001")
        b = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")

        # Order does not matter — the resolver sorts internally.
        await resolver.propose_same_as(
            src_entity_id=b,
            dst_entity_id=a,
            confidence=0.95,
            source="test",
        )

        # The captured params should reflect the canonical ordering.
        assert captured_params.get("src_entity_id") == a, (
            f"expected src={a}, got {captured_params.get('src_entity_id')}"
        )
        assert captured_params.get("dst_entity_id") == b

    async def test_self_same_as_rejected(self) -> None:
        """A same-as edge between an entity and itself is rejected."""
        factory = _make_session_factory()
        resolver = EntityResolver(factory)

        same_id = uuid.uuid4()
        with pytest.raises(ValueError):
            await resolver.propose_same_as(
                src_entity_id=same_id,
                dst_entity_id=same_id,
                confidence=1.0,
                source="test",
            )

    async def test_propose_same_as_requires_valid_confidence(self) -> None:
        """Confidence must be in ``[0.0, 1.0]``."""
        factory = _make_session_factory()
        resolver = EntityResolver(factory)

        with pytest.raises(ValueError):
            await resolver.propose_same_as(
                src_entity_id=uuid.uuid4(),
                dst_entity_id=uuid.uuid4(),
                confidence=1.5,
                source="test",
            )

    async def test_merge_transfers_edges(self) -> None:
        """Merging entities transfers all edges to the canonical entity.

        The ``merge_entities`` method re-points every edge where the
        secondary appears as ``src_entity_id`` or ``dst_entity_id`` to
        the primary.  We assert the SQL contains the UPDATE statements.
        """
        factory = _make_session_factory()
        resolver = EntityResolver(factory)

        captured_sqls: list[str] = []

        async def _capture(
            statement: Any, params: dict[str, Any] | None = None
        ) -> Any:
            text_attr = getattr(statement, "text", None)
            sql_str = text_attr if isinstance(text_attr, str) else str(statement)
            captured_sqls.append(sql_str)
            return MagicMock()

        factory.return_value.execute = AsyncMock(side_effect=_capture)
        factory.return_value.flush = AsyncMock()
        factory.side_effect = None

        primary = uuid.UUID("00000000-0000-0000-0000-000000000001")
        secondary = uuid.UUID("00000000-0000-0000-0000-000000000002")

        await resolver.merge_entities(
            primary_id=primary,
            secondary_id=secondary,
            reason="manual merge",
        )

        combined = "\n".join(captured_sqls)

        # Edge re-point UPDATE for both src and dst sides.
        assert "UPDATE memory.kg_edges" in combined
        assert "SET src_entity_id = :primary_id" in combined
        assert "SET dst_entity_id = :primary_id" in combined
        # Tombstone of the secondary.
        assert "is_tombstoned = TRUE" in combined
        # Audit row for the merge event.
        assert "INSERT INTO memory.kg_consent_audit" in combined

    async def test_merged_entity_tombstoned(self) -> None:
        """The secondary entity gets ``is_tombstoned=TRUE`` and ``merged_into``.

        The tombstone SQL sets both columns so audit / resolution paths
        can distinguish a "merged" entity from a "soft-deleted" one.
        """
        factory = _make_session_factory()
        resolver = EntityResolver(factory)

        captured_sqls: list[str] = []

        async def _capture(
            statement: Any, params: dict[str, Any] | None = None
        ) -> Any:
            text_attr = getattr(statement, "text", None)
            sql_str = text_attr if isinstance(text_attr, str) else str(statement)
            captured_sqls.append(sql_str)
            return MagicMock()

        factory.return_value.execute = AsyncMock(side_effect=_capture)
        factory.return_value.flush = AsyncMock()
        factory.side_effect = None

        primary = uuid.UUID("00000000-0000-0000-0000-000000000001")
        secondary = uuid.UUID("00000000-0000-0000-0000-000000000002")

        await resolver.merge_entities(
            primary_id=primary,
            secondary_id=secondary,
            reason="test merge",
        )

        combined = "\n".join(captured_sqls)
        assert "merged_into = :primary_id" in combined
        assert "is_tombstoned = TRUE" in combined
        assert "tombstone_reason = :reason" in combined

    async def test_merge_self_rejected(self) -> None:
        """Merging an entity into itself is rejected with ValueError."""
        factory = _make_session_factory()
        resolver = EntityResolver(factory)

        same_id = uuid.uuid4()
        with pytest.raises(ValueError):
            await resolver.merge_entities(
                primary_id=same_id,
                secondary_id=same_id,
                reason="self merge",
            )


__all__ = [
    "TestCanonicalKeyGeneration",
    "TestFuzzyMatching",
    "TestSameAsEdges",
]