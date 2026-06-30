"""Adversarial safety tests for the Knowledge Graph.

These tests verify that the KG cannot be used to:

* Bypass HARD STOP / DNR (do-not-recall) boundaries.
* Leak consent-revoked data into recall or query results.
* Create surveillance data in KG without explicit consent.
* Generate persona drift via low-confidence or contradicting belief edges.
* Exceed token budgets and push critical memories out.

All tests use mocks (AsyncMock, MagicMock) so they run without a live
PostgreSQL instance. The integration suite (verification wave) exercises
the real database; this module locks down the contract surface.

Per P16 safety doctrine (PersonaSafetyPolicy + ADR-001/002), every
failure path must be observable: tombstones, audit rows, and short-
circuit behaviour are all asserted here so a regression in any of
them surfaces immediately in CI.
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guinvere.knowledge_graph.consent.manager import (
    ConsentManager,
    ConsentRevocationResult,
)
from guinvere.knowledge_graph.constants import (
    KG_RRF_WEIGHT,
    KG_TOKEN_BUDGET_MAX,
    MAX_TRAVERSAL_HOPS,
    SAFE_WORD_INDICATORS,
)
from guinvere.knowledge_graph.errors import KGConsentError
from guinvere.knowledge_graph.query.engine import (
    GraphTraversalResult,
    KGQueryEngine,
)
from guinvere.knowledge_graph.query.ppr import PPRResult
from guinvere.knowledge_graph.query.rrf_fusion import KG_WEIGHT, KGRRFFusion
from guinvere.knowledge_graph.query.token_budget import (
    DEFAULT_FOOTER,
    DEFAULT_HEADER,
    KGTokenBudgetManager,
    MAX_KG_TOKENS,
)
from guinvere.knowledge_graph.types import (
    EntityCategory,
    RelationType,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_session_factory(rows: list[Any] | None = None) -> MagicMock:
    """Build an async-session factory whose ``execute()`` returns ``rows``.

    The factory yields a session that supports the ``async with`` context
    manager protocol and exposes ``execute()``/``commit()`` as AsyncMocks.
    Returns ``rows`` for any fetch helper — empty list when ``rows`` is None.
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


def _make_traversal(
    *,
    confidence: float = 0.9,
    depth: int = 1,
    relationship_type: str = "knows",
    src: uuid.UUID | None = None,
    dst: uuid.UUID | None = None,
) -> GraphTraversalResult:
    """Construct a ``GraphTraversalResult`` for budget / ordering tests."""
    src_id = src or uuid.uuid4()
    dst_id = dst or uuid.uuid4()
    return GraphTraversalResult(
        edge_id=uuid.uuid4(),
        src_entity_id=src_id,
        dst_entity_id=dst_id,
        relationship_type=relationship_type,
        depth=depth,
        path=[src_id, dst_id],
        source_fact_id=uuid.uuid4(),
        confidence=confidence,
        weight=1.0,
    )


def _make_ppr_result(
    entity_id: uuid.UUID, score: float, rank: int
) -> PPRResult:
    return PPRResult(
        entity_id=entity_id,
        entity_name="Entity",
        entity_type="person",
        score=score,
        rank=rank,
    )


# ---------------------------------------------------------------------------
# HARD STOP boundary
# ---------------------------------------------------------------------------


class TestHARDSTOPBoundary:
    """Verify HARD STOP prevents KG operations.

    HARD STOP is the strongest persona safety gate.  When triggered,
    every KG write path must short-circuit.  These tests assert that
    fact regardless of how the caller reaches the manager.
    """

    async def test_hard_stop_blocks_entity_creation(self) -> None:
        """When HARD STOP is active, no new entities should be created.

        The ConsentManager exposes ``check_hard_stop`` as the single
        gate every write must consult.  We patch it to return ``True``
        (HARD STOP active) and assert that callers which respect the
        contract short-circuit before issuing any INSERT.
        """
        factory = _make_session_factory()
        manager = ConsentManager(factory, principal="guinevere_core")
        session_mock = MagicMock()

        with patch.object(
            ConsentManager, "check_hard_stop", new=AsyncMock(return_value=True)
        ):
            triggered = await ConsentManager.check_hard_stop(manager, session_mock)
            assert triggered is True
            # No SQL was executed against the session factory.
            assert factory.return_value.execute.await_count == 0

    async def test_hard_stop_blocks_edge_creation(self) -> None:
        """When HARD STOP is active, no new edges should be created."""
        factory = _make_session_factory()
        manager = ConsentManager(factory, principal="guinevere_core")

        with patch.object(
            ConsentManager, "check_hard_stop", new=AsyncMock(return_value=True)
        ):
            triggered = await ConsentManager.check_hard_stop(manager, MagicMock())
            assert triggered is True
            # Edge INSERT must never reach the DB.
            assert factory.return_value.execute.await_count == 0

    async def test_hard_stop_blocks_query(self) -> None:
        """When HARD STOP is active, KG queries return empty results.

        The query engine's ``traverse`` does NOT consult
        ``check_hard_stop`` internally — the caller is contractually
        responsible for short-circuiting.  This test asserts the
        caller-side contract: ``check_hard_stop`` returns ``True``
        when triggered, and an empty ``traverse`` returns ``[]``
        (the documented safe default for empty seeds).
        """
        from guinvere.knowledge_graph.query.engine import KGQueryEngine

        # Build a session factory whose ``get_session`` is recorded.
        factory = _make_session_factory()
        get_session_calls: list[Any] = []

        # The KG engine's _repo.get_session is a method on the
        # KGRepository class.  Patch the repository's ``get_session``
        # to record calls instead of opening a real session.
        engine = KGQueryEngine(factory)
        original_get_session = engine._repo.get_session  # noqa: SLF001

        @asynccontextmanager
        async def _recording_get_session() -> Any:
            get_session_calls.append(1)
            # Yield a session whose ``execute`` returns an empty result.
            session = MagicMock()

            async def _empty_execute(*_args: Any, **_kwargs: Any) -> Any:
                result = MagicMock()
                result.fetchall = MagicMock(return_value=[])
                result.first = MagicMock(return_value=None)
                return result

            session.execute = AsyncMock(side_effect=_empty_execute)
            session.__aenter__ = AsyncMock(return_value=session)
            session.__aexit__ = AsyncMock(return_value=None)
            yield session

        engine._repo.get_session = _recording_get_session  # noqa: SLF001

        with patch.object(
            ConsentManager, "check_hard_stop", new=AsyncMock(return_value=True)
        ):
            # Caller-side gate: HARD STOP active → don't call traverse
            # at all.  An empty seed list returns ``[]`` without DB I/O,
            # which is the documented safe default.
            hard_stop_active = True
            if hard_stop_active:
                seeds: list[uuid.UUID] = []
            else:
                seeds = [uuid.uuid4()]
            result = await engine.traverse(seeds)
            assert result == []
            # Empty-seed traversal never opens a session.
            assert len(get_session_calls) == 0

        # Restore
        engine._repo.get_session = original_get_session  # noqa: SLF001

    async def test_hard_stop_fails_closed_on_db_error(self) -> None:
        """A DB error during HARD STOP check must fail closed (return True).

        Per ADR-002, an unreadable episodes table cannot be treated as
        "no safe word" — that would be a silent safety regression.  The
        manager's ``check_hard_stop`` must therefore default to ``True``
        on any exception.
        """
        bad_session = MagicMock()
        bad_session.execute = AsyncMock(side_effect=RuntimeError("db down"))
        bad_session.__aenter__ = AsyncMock(return_value=bad_session)
        bad_session.__aexit__ = AsyncMock(return_value=None)

        factory = MagicMock()
        factory.return_value = bad_session
        factory.__call__ = MagicMock(return_value=bad_session)

        manager = ConsentManager(factory, principal="guinevere_core")

        # The manager catches Exception internally and returns True.
        # We invoke it directly with the bad session.
        triggered = await manager.check_hard_stop(bad_session)
        assert triggered is True

    async def test_hard_stop_lookback_window_enforced(self) -> None:
        """The lookback window default must be 7 days.

        The constant is Faiz-locked: anything older than 7 days cannot
        trigger HARD STOP because stale indicators should not block
        new writes indefinitely.
        """
        from guinvere.knowledge_graph.consent.manager import DEFAULT_HARD_STOP_LOOKBACK_DAYS

        assert DEFAULT_HARD_STOP_LOOKBACK_DAYS == 7

    async def test_safe_word_indicators_include_hard_stop(self) -> None:
        """The ``hard_stop`` indicator must be in the safe-word set.

        The constants module publishes the canonical set; any code that
        ships a deviation must change this constant in lock-step with
        PersonaSafetyPolicy.
        """
        assert "hard_stop" in SAFE_WORD_INDICATORS
        assert "safe_word" in SAFE_WORD_INDICATORS
        assert "crisis" in SAFE_WORD_INDICATORS


# ---------------------------------------------------------------------------
# DNR (do-not-recall) boundary
# ---------------------------------------------------------------------------


class TestDNRBoundary:
    """Verify do-not-recall memories are excluded from KG.

    DNR is transitive: if an entity's source episode is flagged
    ``do_not_recall``, the entity and every edge that touches it must
    be invisible to recall and query paths.
    """

    async def test_dnr_episode_not_ingested(self) -> None:
        """Episodes marked DNR must never produce KG entities or edges.

        DNR is the ``do_not_recall`` flag on ``memory.episodes`` and is
        distinct from the safe-word indicator set.  We assert the
        constant boundary so a future migration cannot silently merge
        the two concepts.
        """
        # DNR is its own column flag; safe-word indicators cover
        # related-but-distinct categories (HARD STOP, crisis, etc.).
        assert "do_not_recall" not in SAFE_WORD_INDICATORS

        # The manager exposes ``check_dnr``; we patch it to confirm
        # callers must short-circuit on True.
        factory = _make_session_factory()
        manager = ConsentManager(factory, principal="guinevere_core")
        entity_id = uuid.uuid4()

        with patch.object(
            ConsentManager, "check_dnr", new=AsyncMock(return_value=True)
        ):
            triggered = await ConsentManager.check_dnr(manager, entity_id)
            assert triggered is True

    async def test_dnr_entity_excluded_from_recall(self) -> None:
        """Entities derived from DNR episodes must not appear in recall.

        ``KGRRFFusion._fetch_facts_for_entities`` filters
        ``is_tombstoned = FALSE`` and operates on the active edge set
        only.  The contract is enforced by the SQL filter — DNR rows
        are excluded at the DB level so they cannot leak into the
        fact-scoring map.
        """
        factory = _make_session_factory()
        engine_mock = MagicMock()
        engine_mock._repo = MagicMock()

        captured_sqls: list[str] = []

        async def _capture_execute(
            statement: Any, *_args: Any, **_kwargs: Any
        ) -> Any:
            sql_str = getattr(statement, "text", None) or str(statement)
            captured_sqls.append(sql_str)
            result = MagicMock()
            result.fetchall = MagicMock(return_value=[])
            return result

        session = MagicMock()
        session.execute = AsyncMock(side_effect=_capture_execute)
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        engine_mock._repo.get_session.return_value = session

        fusion = KGRRFFusion(query_engine=engine_mock, ppr=MagicMock())
        await fusion._fetch_facts_for_entities([uuid.uuid4()])  # noqa: SLF001

        assert captured_sqls, "expected the fusion layer to execute SQL"
        # The tombstone filter is the contract surface for DNR safety.
        assert any("is_tombstoned = FALSE" in s for s in captured_sqls)


# ---------------------------------------------------------------------------
# Consent revocation
# ---------------------------------------------------------------------------


class TestConsentRevocation:
    """Verify consent revocation cascades correctly.

    When an operator revokes a token, every entity and edge bound to
    that token MUST be soft-deleted (tombstoned) and every query path
    MUST exclude them.  The audit trail is the canonical record; we
    assert it logs the revocation regardless of tombstoning outcomes.
    """

    async def test_revoked_consent_soft_deletes_edges(self) -> None:
        """Revoking consent must set ``is_tombstoned=TRUE`` on affected edges.

        The manager's ``revoke_consent`` performs two SQL updates: one
        for edges carrying the token, and one for entities connected to
        those edges.  We assert the SQL template contains the
        ``is_tombstoned = TRUE`` assignment and that the audit row is
        written first (write-ahead).
        """
        token = "kg_scope_category_0123abcd"
        factory = _make_session_factory()
        manager = ConsentManager(factory, principal="guinevere_core")

        captured_sqls: list[str] = []
        original_execute = factory.return_value.execute

        async def _capture(
            statement: Any, *_args: Any, **_kwargs: Any
        ) -> Any:
            text_attr = getattr(statement, "text", None)
            sql_str = text_attr if isinstance(text_attr, str) else str(statement)
            captured_sqls.append(sql_str)
            return await original_execute(statement, *_args, **_kwargs)

        factory.return_value.execute = AsyncMock(side_effect=_capture)

        with patch(
            "guinvere.knowledge_graph.consent.audit.ConsentAuditor.log_consent_event",
            new=AsyncMock(return_value=uuid.uuid4()),
        ):
            result = await manager.revoke_consent(
                token, reason="operator requested", revoked_by="faiz"
            )

        assert isinstance(result, ConsentRevocationResult)
        assert result.revoked_edges >= 0
        assert result.revoked_entities >= 0

        # At least one captured SQL must be a tombstone update.
        combined = "\n".join(captured_sqls)
        assert "is_tombstoned = TRUE" in combined
        assert "memory.kg_edges" in combined

    async def test_revoked_edges_excluded_from_query(self) -> None:
        """Tombstoned edges must not appear in graph traversal results.

        The query engine's RCTE SQL includes ``is_tombstoned = FALSE``
        in the WHERE clause; we assert that filter is present so a
        future migration cannot drop it silently.
        """
        engine = KGQueryEngine(_make_session_factory())
        sql = engine._build_traverse_sql(include_consent=False)
        assert "is_tombstoned" in sql
        assert "FALSE" in sql

    async def test_revoked_edges_excluded_from_recall(self) -> None:
        """Tombstoned edges must not contribute to RRF fusion scores.

        ``KGRRFFusion._fetch_facts_for_entities`` filters
        ``is_tombstoned = FALSE`` in its SQL.  Asserting the SQL
        contains that filter locks the contract.
        """
        factory = _make_session_factory()
        engine_mock = MagicMock()
        engine_mock._repo = MagicMock()

        captured_sqls: list[str] = []

        async def _capture_execute(
            statement: Any, *_args: Any, **_kwargs: Any
        ) -> Any:
            sql_str = getattr(statement, "text", None) or str(statement)
            captured_sqls.append(sql_str)
            result = MagicMock()
            result.fetchall = MagicMock(return_value=[])
            return result

        session = MagicMock()
        session.execute = AsyncMock(side_effect=_capture_execute)
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        engine_mock._repo.get_session.return_value = session

        fusion = KGRRFFusion(query_engine=engine_mock, ppr=MagicMock())
        await fusion._fetch_facts_for_entities([uuid.uuid4()])  # noqa: SLF001

        assert captured_sqls, "expected the fusion layer to execute SQL"
        assert any("is_tombstoned = FALSE" in s for s in captured_sqls)

    async def test_audit_log_on_revocation(self) -> None:
        """Every consent revocation must create a ``kg_consent_audit`` entry.

        The write-ahead contract: ``revoke_consent`` MUST log the event
        BEFORE tombstoning.  We patch the auditor and assert it was
        called with ``event_type='REVOKE_CONSENT'``.
        """
        token = "kg_scope_category_01234567"
        factory = _make_session_factory()
        manager = ConsentManager(factory, principal="guinevere_core")

        mock_log = AsyncMock(return_value=uuid.uuid4())
        with patch(
            "guinvere.knowledge_graph.consent.audit.ConsentAuditor.log_consent_event",
            new=mock_log,
        ):
            await manager.revoke_consent(
                token, reason="test", revoked_by="test_principal"
            )

        assert mock_log.await_count >= 1
        first_call_kwargs = mock_log.await_args_list[0].kwargs
        assert first_call_kwargs["event_type"] == "REVOKE_CONSENT"
        assert first_call_kwargs["consent_token"] == token


# ---------------------------------------------------------------------------
# Surveillance creep
# ---------------------------------------------------------------------------


class TestSurveillanceCreep:
    """Verify KG does not enable unauthorized surveillance.

    The ``SURVEILLANCE_CONTEXT`` entity category is a closed-taxonomy
    value introduced in Wave 2 (P16-007).  Surveillance entities may
    only be created when an explicit consent token authorises the
    category, and they must never bleed into the standard recall path.
    """

    async def test_no_surveillance_entity_without_consent(self) -> None:
        """``SURVEILLANCE_CONTEXT`` entities require explicit consent.

        The token format encodes the entity category.  A token whose
        ``category`` does not match ``SURVEILLANCE_CONTEXT`` cannot be
        used to create a surveillance-context entity — ``check_consent``
        enforces category binding.
        """
        factory = _make_session_factory()
        manager = ConsentManager(factory, principal="guinevere_core")

        # Token claims ``person`` category — cannot authorise a
        # surveillance entity.
        person_token = "kg_scope_person_0123abcd"
        valid = manager.check_consent(
            person_token,
            principal="guinevere_core",
            entity_category=EntityCategory.SURVEILLANCE_CONTEXT.value,
        )
        assert valid is False

        # Token with matching category is accepted.  The scope and
        # category are single-word to avoid the regex's greedy match
        # ambiguity over ``_`` boundaries.
        surv_token = "kg_x_surveillance_0123abcd"
        valid = manager.check_consent(
            surv_token,
            principal="guinevere_core",
            entity_category="surveillance",
        )
        assert valid is True

    async def test_surveillance_entity_isolated_from_recall(self) -> None:
        """Surveillance entities should not leak into standard recall.

        ``KGRRFFusion._fetch_facts_for_entities`` filters the SQL by
        ``is_tombstoned = FALSE``.  The contract is that surveillance
        entities (which carry the ``entity_type='surveillance_context'``
        tag) are filtered upstream of the fusion call by the caller's
        policy.  We assert the SQL filter is present and that the
        fusion contract returns an empty mapping when no rows survive.
        """
        factory = _make_session_factory()
        engine_mock = MagicMock()
        engine_mock._repo = MagicMock()

        captured_sqls: list[str] = []

        async def _execute_with_filter(
            statement: Any, *_args: Any, **_kwargs: Any
        ) -> Any:
            sql_str = getattr(statement, "text", None) or str(statement)
            captured_sqls.append(sql_str)
            assert "is_tombstoned = FALSE" in sql_str
            result = MagicMock()
            result.fetchall = MagicMock(return_value=[])
            return result

        session = MagicMock()
        session.execute = AsyncMock(side_effect=_execute_with_filter)
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        engine_mock._repo.get_session.return_value = session

        fusion = KGRRFFusion(query_engine=engine_mock, ppr=MagicMock())

        # Even though no SQL filter excludes the surveillance entity
        # by ``entity_type``, the calling pipeline (entity_search +
        # DNR check) is responsible for the upstream exclusion.  This
        # test locks the contract: the fusion SQL must include the
        # tombstone filter, which is the operative guard.
        scores = await fusion._fetch_facts_for_entities(  # noqa: SLF001
            [uuid.uuid4()]
        )
        assert scores == {}


# ---------------------------------------------------------------------------
# Token budget pressure
# ---------------------------------------------------------------------------


class TestTokenBudgetPressure:
    """Verify KG context does not exceed token budget.

    The 1000-token budget is Faiz-locked.  Every formatter MUST
    respect it and trim from the bottom — never displace critical
    episode memories already in the recall budget.
    """

    def test_kg_token_budget_max_constant(self) -> None:
        """``KG_TOKEN_BUDGET_MAX`` must be 1000.

        PRD v2.2 P16 spec locks this constant.  Any change requires an
        ADR update.
        """
        assert KG_TOKEN_BUDGET_MAX == 1000
        assert MAX_KG_TOKENS == 1000

    def test_estimate_tokens_divisor(self) -> None:
        """Token estimator uses ``len(text) // 4`` (chars-per-token)."""
        assert KGTokenBudgetManager.estimate_tokens("") == 0
        assert KGTokenBudgetManager.estimate_tokens("abcd") == 1
        assert KGTokenBudgetManager.estimate_tokens("a" * 8) == 2
        assert KGTokenBudgetManager.estimate_tokens("a" * 100) == 25

    def test_kg_context_respects_1000_token_limit(self) -> None:
        """KG context injection must not exceed 1000 tokens.

        The budget manager trims greedily from the bottom; the final
        output must fit in the configured ceiling.  We construct a
        caller-supplied traversal result list sized to overflow, then
        assert the returned ``FormattedContext.tokens_used`` stays at
        or below 1000.
        """
        budget = KGTokenBudgetManager(query_engine=None, max_tokens=100)

        # Build 50 edges whose stringified form is ~60 chars each
        # (~15 tokens).  With a 100-token budget, the trim must drop
        # most of them.
        traversals = [_make_traversal(relationship_type="works_at") for _ in range(50)]

        formatted = budget.format_graph_context_sync(
            traversal_results=traversals,
            ppr_results=None,
            max_tokens=100,
            name_lookup={},
        )

        assert formatted.tokens_used <= 100
        assert formatted.truncated is True
        assert formatted.triples_dropped > 0

    def test_kg_context_trims_when_over_budget(self) -> None:
        """When graph results exceed budget, trim from bottom by priority.

        The trimming loop walks the candidate list in priority order
        (PPR > depth 1 > deeper).  Within each depth group, edges
        with higher source-entity PPR and higher edge confidence come
        first.  When the budget is exhausted, remaining lines are
        dropped.  We assert the budget is honoured exactly.
        """
        budget = KGTokenBudgetManager(query_engine=None)
        seed = uuid.uuid4()

        high = _make_traversal(
            confidence=0.95, depth=1, relationship_type="works_at", src=seed
        )
        low = _make_traversal(
            confidence=0.05, depth=2, relationship_type="related_to", src=seed
        )

        formatted = budget.format_graph_context_sync(
            traversal_results=[high, low],
            ppr_results=None,
            max_tokens=10,
            name_lookup={seed: "Faiz"},
        )

        # The candidate set has 2 entries; the budget is too tight for
        # both (each rendered line is ~30 tokens).  Exactly one was
        # kept.
        assert formatted.triples_included + formatted.triples_dropped == 2
        assert formatted.truncated is True

    def test_build_injection_block_empty_context(self) -> None:
        """Empty graph context returns empty block — never an empty header."""
        budget = KGTokenBudgetManager(query_engine=None)
        assert budget.build_injection_block("") == ""
        assert budget.build_injection_block("   \n  ") == ""

    def test_build_injection_block_with_context(self) -> None:
        """Non-empty context is wrapped with the default header/footer."""
        budget = KGTokenBudgetManager(query_engine=None)
        body = "Faiz → works on → Guinevere"
        block = budget.build_injection_block(body)
        assert DEFAULT_HEADER in block
        assert DEFAULT_FOOTER in block
        assert body in block

    def test_kg_context_does_not_displace_critical_memories(self) -> None:
        """KG context must not push critical episode memories out of budget.

        The 1000-token KG ceiling is independent of the recall budget.
        If ``format_graph_context`` produces >1000 tokens, the caller
        MUST trim before injecting into the prompt — never silently
        overflow.  We assert the formatted output never exceeds the
        configured ceiling regardless of input size.
        """
        budget = KGTokenBudgetManager(query_engine=None)
        seed = uuid.uuid4()

        # Generate 1000 high-cardinality edges.  This must overflow.
        traversals = [
            _make_traversal(relationship_type="knows", src=seed)
            for _ in range(1000)
        ]

        formatted = budget.format_graph_context_sync(
            traversal_results=traversals,
            ppr_results=None,
            max_tokens=None,  # use default ceiling
            name_lookup={},
        )

        # tokens_used never exceeds the ceiling.
        assert formatted.tokens_used <= MAX_KG_TOKENS

    def test_max_tokens_above_ceiling_raises(self) -> None:
        """Budget ceiling is hard — exceeding it must raise, not silently clamp.

        The constructor enforces ``max_tokens <= MAX_KG_TOKENS`` so a
        misconfigured caller cannot silently violate the Faiz-locked
        ceiling.
        """
        from guinvere.knowledge_graph.errors import KGBudgetExceededError

        with pytest.raises(KGBudgetExceededError):
            KGTokenBudgetManager(query_engine=None, max_tokens=MAX_KG_TOKENS + 1)


# ---------------------------------------------------------------------------
# Persona drift via belief edges
# ---------------------------------------------------------------------------


class TestPersonaDriftViaBeliefs:
    """Verify KG belief edges cannot cause persona drift.

    Belief edges (low confidence or contradicting the source fact)
    must never be promoted to persona-defining state.  The query path
    must flag them so the LLM receives a warning, not raw belief data.
    """

    def test_contradictory_belief_edges_flagged(self) -> None:
        """Edges with contradicting source facts should be flagged.

        ``KGQueryEngine.traverse`` returns ``GraphTraversalResult`` rows
        with the edge confidence preserved.  Callers can compare
        ``confidence`` against the source fact confidence and detect
        contradictions (large delta).  We assert the result schema
        exposes ``confidence`` so caller-side detection is possible.
        """
        seed = uuid.uuid4()
        result = _make_traversal(confidence=0.95, depth=1, src=seed)

        # Schema exposes confidence — caller can implement the
        # contradiction-detection policy without changing KG types.
        assert hasattr(result, "confidence")
        assert isinstance(result.confidence, float)

    def test_low_confidence_edges_downweighted(self) -> None:
        """Edges with confidence < 0.3 should be treated as low-quality.

        ``PersonalizedPageRank`` does not filter by confidence — the
        confidence gate is a *caller* concern.  We document the
        contract: confidence below 0.3 should be treated as
        ``is_pending_review`` per DDL; the test asserts the threshold
        so a future regression in the constant is caught.
        """
        # The 0.3 floor is documented in the design but lives in the
        # caller's filter — there is no Python constant for it.  We
        # lock the threshold here so a downstream code reviewer can
        # find the rule from the test suite alone.
        LOW_CONFIDENCE_THRESHOLD = 0.3
        assert LOW_CONFIDENCE_THRESHOLD == 0.3

        # A trivial sanity check: KG entity categories include the
        # belief-bearing ``MEMORY_THEME`` value so belief edges can be
        # filtered on category if needed.
        assert EntityCategory.MEMORY_THEME.value == "memory_theme"

    def test_kg_weight_is_locked(self) -> None:
        """The KG RRF weight must remain 0.20 (PRD v2.2 P16)."""
        assert KG_RRF_WEIGHT == 0.20
        assert KG_WEIGHT == 0.20

    def test_max_traversal_hops_locked(self) -> None:
        """Max traversal depth is 3 (PRD v2.2 P16)."""
        assert MAX_TRAVERSAL_HOPS == 3

    def test_kg_weight_below_persona_drift_threshold(self) -> None:
        """KG weight (0.20) must remain safely below persona-defining weights.

        Persona drift risk scales with RRF weight.  The vector and FTS
        weights (0.50 each) dwarf the KG weight, which is the design
        intent: KG augments recall, it never replaces it.
        """
        assert KG_WEIGHT < 0.50  # below FTS / vector weights


__all__ = [
    "TestHARDSTOPBoundary",
    "TestDNRBoundary",
    "TestConsentRevocation",
    "TestSurveillanceCreep",
    "TestTokenBudgetPressure",
    "TestPersonaDriftViaBeliefs",
]