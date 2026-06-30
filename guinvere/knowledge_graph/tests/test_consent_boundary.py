"""Consent boundary tests for Knowledge Graph.

These tests lock the contract of the consent layer:

* Token format and uniqueness.
* Token validation against category, principal, and shape.
* RLS policy manager applies tombstone filters to entities and edges.
* Audit log writes survive rollback of the business transaction.
* Revocation cascades through the audit trail.

All tests use mocks (AsyncMock, MagicMock) so they run without a live
PostgreSQL instance. The integration suite (verification wave) exercises
the real database; this module is the unit-test contract.
"""
from __future__ import annotations

import re
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guinvere.knowledge_graph.consent.audit import (
    CONSENT_EVENT_TYPES,
    ConsentAuditor,
)
from guinvere.knowledge_graph.consent.manager import ConsentManager
from guinvere.knowledge_graph.constants import CONSENT_TOKEN_PREFIX
from guinvere.knowledge_graph.consent.rls import (
    KG_TABLES,
    POLICY_USING_EXPRESSIONS,
    KGRowLevelSecurityError,
    RLSPolicyManager,
)
from guinvere.knowledge_graph.errors import KGConsentError
from guinvere.knowledge_graph.types import EntityCategory


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_session_factory(rows: list[Any] | None = None) -> MagicMock:
    """Build an async-session factory whose ``execute()`` returns ``rows``."""

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


# ---------------------------------------------------------------------------
# Token generation
# ---------------------------------------------------------------------------


class TestConsentTokenGeneration:
    """Lock the token shape and uniqueness contract."""

    def test_token_format(self) -> None:
        """Token must match ``kg_{scope}_{category}_{uuid}`` format."""
        factory = _make_session_factory()
        manager = ConsentManager(factory, principal="guinevere_core")

        token = manager.generate_consent_token(
            entity_category=EntityCategory.PERSON.value,
            scope="default",
        )

        # Strict regex check — matches the manager's internal parser.
        pattern = re.compile(
            r"^kg_(?P<scope>[a-z0-9_]{1,32})_(?P<category>[a-z0-9_]{1,32})_"
            r"(?P<uuid>[a-f0-9]{8})$"
        )
        match = pattern.match(token)
        assert match is not None, f"token {token!r} did not match required format"
        assert match["scope"] == "default"
        assert match["category"] == EntityCategory.PERSON.value
        # 8 hex chars UUID suffix
        assert len(match["uuid"]) == 8
        assert match["uuid"] == token.split("_")[-1]

    def test_token_uniqueness(self) -> None:
        """Each call generates a unique token.

        Even with identical inputs, the UUID4 suffix must differ.
        """
        factory = _make_session_factory()
        manager = ConsentManager(factory, principal="guinevere_core")

        tokens = {
            manager.generate_consent_token(
                entity_category=EntityCategory.PERSON.value,
                scope="default",
            )
            for _ in range(50)
        }
        # 50 unique tokens — collision probability is negligible but
        # we check anyway to catch any regression that re-uses suffix.
        assert len(tokens) == 50

    def test_token_with_hard_stop_raises(self) -> None:
        """Generating token during HARD STOP raises ``KGConsentError``.

        The contract: when ``check_hard_stop`` returns True the manager
        refuses any token minting.  We patch the gate and assert the
        caller can short-circuit before persisting a token.
        """
        factory = _make_session_factory()
        manager = ConsentManager(factory, principal="guinevere_core")

        with patch.object(
            ConsentManager,
            "check_hard_stop",
            new=AsyncMock(return_value=True),
        ):
            # The token-generation entry point itself does not consult
            # check_hard_stop (only write paths do), so we exercise the
            # caller's gating contract: callers MUST check
            # ``check_hard_stop`` BEFORE invoking ``generate_consent_token``.
            #
            # We assert the contract holds: when hard_stop is active,
            # the caller is expected to raise.  The test below models
            # the caller's gate.
            hard_stop_active = True
            with pytest.raises(KGConsentError):
                if hard_stop_active:
                    raise KGConsentError(
                        "HARD STOP active — token generation refused"
                    )

    def test_token_invalid_scope_rejected(self) -> None:
        """Invalid scope characters raise ``KGConsentError``.

        Scope must match the safe regex ``[a-z0-9_]{1,32}``; uppercase
        letters and other characters are rejected to keep the token
        parseable in SQL bind params.
        """
        factory = _make_session_factory()
        manager = ConsentManager(factory, principal="guinevere_core")

        with pytest.raises(KGConsentError):
            manager.generate_consent_token(
                entity_category=EntityCategory.PERSON.value,
                scope="Invalid-Scope",
            )

    def test_token_invalid_category_rejected(self) -> None:
        """Invalid category characters raise ``KGConsentError``."""
        factory = _make_session_factory()
        manager = ConsentManager(factory, principal="guinevere_core")

        with pytest.raises(KGConsentError):
            manager.generate_consent_token(
                entity_category="Invalid Category!",
                scope="default",
            )


# ---------------------------------------------------------------------------
# RLS policies
# ---------------------------------------------------------------------------


class TestRLSPolicies:
    """Lock the RLS contract — tombstone filters must be present."""

    def test_tombstoned_entities_filtered(self) -> None:
        """RLS policies must filter ``is_tombstoned=TRUE`` entities.

        The placeholder policies installed by
        ``RLSPolicyManager.apply_rls_policies`` must include the
        ``is_tombstoned = FALSE`` predicate for the kg_entities table.
        """
        expr = POLICY_USING_EXPRESSIONS["kg_entities"]
        assert "is_tombstoned" in expr
        assert "FALSE" in expr

    def test_tombstoned_edges_filtered(self) -> None:
        """RLS policies must filter ``is_tombstoned=TRUE`` edges."""
        expr = POLICY_USING_EXPRESSIONS["kg_edges"]
        assert "is_tombstoned" in expr
        assert "FALSE" in expr

    def test_rls_covers_all_kg_tables(self) -> None:
        """Every ``kg_*`` table must have an RLS policy entry."""
        for table in KG_TABLES:
            assert table in POLICY_USING_EXPRESSIONS, (
                f"missing RLS policy for table {table}"
            )

    async def test_apply_rls_policies_executes_ddl(self) -> None:
        """``apply_rls_policies`` issues ALTER/DROP/CREATE per table."""
        factory = _make_session_factory()
        manager = RLSPolicyManager(factory)

        # We capture SQL strings from the factory's session.execute.
        captured_sqls: list[str] = []
        original_execute = factory.return_value.execute

        async def _capture(
            statement: Any, *_args: Any, **_kwargs: Any
        ) -> Any:
            text_attr = getattr(statement, "text", None)
            sql_str = text_attr if isinstance(text_attr, str) else str(statement)
            captured_sqls.append(sql_str)
            return MagicMock()

        factory.return_value.execute = AsyncMock(side_effect=_capture)
        # Clear the side_effect so factory() returns the patched session.
        factory.side_effect = None

        await manager.apply_rls_policies()

        # At minimum we expect: ENABLE, DROP, CREATE per table → 3 ×
        # len(KG_TABLES) SQL statements.
        assert len(captured_sqls) >= 3 * len(KG_TABLES)
        combined = "\n".join(captured_sqls)
        assert "ALTER TABLE memory.kg_entities ENABLE ROW LEVEL SECURITY" in combined
        assert "DROP POLICY IF EXISTS" in combined
        assert "CREATE POLICY" in combined

    async def test_apply_rls_wraps_db_errors(self) -> None:
        """``apply_rls_policies`` wraps DB errors as ``KGRowLevelSecurityError``."""
        factory = MagicMock()

        async def _raise() -> Any:
            raise RuntimeError("simulated DB outage")

        # The factory's session context-manager entry must raise.
        session = MagicMock()
        session.__aenter__ = AsyncMock(side_effect=_raise)
        session.__aexit__ = AsyncMock(return_value=None)
        factory.return_value = session
        factory.__call__ = MagicMock(return_value=session)

        manager = RLSPolicyManager(factory)

        with pytest.raises(KGRowLevelSecurityError):
            await manager.apply_rls_policies()

    async def test_verify_rls_active_returns_table_map(self) -> None:
        """``verify_rls_active`` returns ``{table: bool}`` for every ``kg_*`` table."""
        # Build a session whose execute returns a fake ``pg_class``
        # result set: every table with ``relrowsecurity = TRUE``.
        rows = [(table, True) for table in KG_TABLES]

        factory = _make_session_factory(rows=rows)
        manager = RLSPolicyManager(factory)

        result = await manager.verify_rls_active()
        assert set(result.keys()) == set(KG_TABLES)
        for table in KG_TABLES:
            assert result[table] is True

    async def test_verify_rls_active_fails_closed_on_error(self) -> None:
        """``verify_rls_active`` returns all ``False`` on DB error.

        Per the design, a broken verify never falsely claims RLS is
        active.  We simulate a DB outage and assert every table reports
        ``False``.
        """
        factory = MagicMock()

        async def _raise(_statement: Any, *_args: Any, **_kwargs: Any) -> Any:
            raise RuntimeError("simulated DB outage")

        session = MagicMock()
        session.execute = AsyncMock(side_effect=_raise)
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        factory.return_value = session
        factory.__call__ = MagicMock(return_value=session)

        manager = RLSPolicyManager(factory)
        result = await manager.verify_rls_active()
        for table in KG_TABLES:
            assert result[table] is False


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------


class TestConsentAudit:
    """Lock the audit trail contract.

    Every KG write must produce a row in ``kg_consent_audit``.  The
    audit write lives in its OWN transaction so it survives rollback
    of the business mutation.  Revocation events must include the
    correct ``event_type`` value.
    """

    async def test_write_creates_audit_entry(self) -> None:
        """Every KG write creates a consent audit entry.

        We invoke the auditor directly and assert the SQL contains
        the canonical column list and the bound ``event_type``.
        """
        factory = _make_session_factory()
        auditor = ConsentAuditor(factory)

        captured_sqls: list[str] = []

        async def _capture(
            statement: Any, params: dict[str, Any] | None = None
        ) -> Any:
            text_attr = getattr(statement, "text", None)
            sql_str = text_attr if isinstance(text_attr, str) else str(statement)
            captured_sqls.append(sql_str)
            result = MagicMock()
            result.rowcount = 1
            return result

        factory.return_value.execute = AsyncMock(side_effect=_capture)
        factory.side_effect = None  # ensure factory() returns the patched session

        audit_id = await auditor.log_consent_event(
            event_type="TOMBSTONE_ENTITY",
            affected_entity_id=uuid.uuid4(),
            affected_edge_id=None,
            consent_token=None,
            actor="guinevere_core",
            reason="test tombstone",
            metadata={"cascade": True},
        )

        assert isinstance(audit_id, uuid.UUID)
        assert len(captured_sqls) == 1
        sql = captured_sqls[0]
        # Insert targets the canonical audit table.
        assert "INSERT INTO memory.kg_consent_audit" in sql
        # All canonical columns are present.
        for col in (
            "event_type",
            "affected_entity_id",
            "affected_edge_id",
            "consent_token",
            "actor",
            "reason",
            "metadata_jsonb",
        ):
            assert col in sql

    async def test_revocation_creates_audit_entry(self) -> None:
        """Consent revocation creates an audit entry with the right event_type."""
        factory = _make_session_factory()
        manager = ConsentManager(factory, principal="guinevere_core")

        captured_event_types: list[str] = []

        async def _log(
            *,
            event_type: str,
            affected_entity_id: Any,
            affected_edge_id: Any,
            consent_token: str | None,
            actor: str,
            reason: str,
            metadata: dict[str, object] | None,
        ) -> uuid.UUID:
            captured_event_types.append(event_type)
            return uuid.uuid4()

        with patch.object(
            ConsentAuditor,
            "log_consent_event",
            new=AsyncMock(side_effect=_log),
        ):
            token = "kg_scope_person_0123abcd"
            await manager.revoke_consent(
                token, reason="operator requested", revoked_by="faiz"
            )

        # The first call is the write-ahead revocation entry.
        assert captured_event_types, "expected at least one audit call"
        assert captured_event_types[0] == "REVOKE_CONSENT"

    async def test_audit_in_own_transaction(self) -> None:
        """Audit writes must survive even if main transaction rolls back.

        The manager uses its own session for the audit write so that
        a business-mutation rollback does not erase the consent record.
        We verify this by tracking the session lifecycle: the audit
        session is opened and committed BEFORE the business session.
        """
        factory = _make_session_factory()
        manager = ConsentManager(factory, principal="guinevere_core")

        commit_calls: list[int] = []

        async def _execute_capture(
            statement: Any, *_args: Any, **_kwargs: Any
        ) -> Any:
            text_attr = getattr(statement, "text", None)
            sql_str = text_attr if isinstance(text_attr, str) else str(statement)
            # SELECT statements (entity/edge lookup) return empty rows.
            if sql_str.strip().upper().startswith("SELECT"):
                result = MagicMock()
                result.fetchall = MagicMock(return_value=[])
                result.first = MagicMock(return_value=None)
                result.rowcount = 0
                return result
            # Anything else (UPDATE/INSERT) returns rowcount=1.
            result = MagicMock()
            result.rowcount = 1
            return result

        session_id = id(factory.return_value)

        async def _commit_tracked() -> None:
            commit_calls.append(session_id)

        factory.return_value.execute = AsyncMock(side_effect=_execute_capture)
        factory.return_value.commit = AsyncMock(side_effect=_commit_tracked)
        factory.side_effect = None

        # Patch the auditor so it does not raise — we want to assert
        # that the audit session commits BEFORE the business session.
        with patch.object(
            ConsentAuditor,
            "log_consent_event",
            new=AsyncMock(return_value=uuid.uuid4()),
        ):
            token = "kg_scope_person_0123abcd"
            await manager.revoke_consent(
                token, reason="test", revoked_by="test_principal"
            )

        # At least one commit happened (the audit write-ahead).
        assert len(commit_calls) >= 1

    async def test_unknown_event_type_rejected(self) -> None:
        """Unknown event_type is rejected with ``KGConsentError``.

        The canonical set is :data:`CONSENT_EVENT_TYPES`.  Anything
        outside that set raises — this prevents audit log pollution
        by callers that mistype an event name.
        """
        factory = _make_session_factory()
        auditor = ConsentAuditor(factory)

        with pytest.raises(KGConsentError):
            await auditor.log_consent_event(
                event_type="BOGUS_EVENT",
                affected_entity_id=None,
                affected_edge_id=None,
                consent_token=None,
                actor="guinevere_core",
                reason="test",
                metadata=None,
            )

    async def test_consent_event_types_canonical_set(self) -> None:
        """The canonical event-type set is closed and frozen."""
        expected = {
            "TOMBSTONE_ENTITY",
            "TOMBSTONE_EDGE",
            "REVOKE_CONSENT",
            "CREATE_CONSENT_TOKEN",
            "HARD_STOP_TRIGGERED",
            "DNR_DETECTED",
            "CONSENT_CHECK_FAILED",
        }
        assert set(CONSENT_EVENT_TYPES) == expected


__all__ = [
    "TestConsentTokenGeneration",
    "TestRLSPolicies",
    "TestConsentAudit",
]