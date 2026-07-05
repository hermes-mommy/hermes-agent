"""Knowledge Graph RLS policy manager (P16-008).

This module owns the placeholder Row-Level Security policies declared in
``evidence/p16-kg/p16-001-schema-ddl.sql`` (DDL v4). The policies in
that DDL are deliberately minimal: they enforce soft-delete filtering
only (``deletion_state != 'deleted' AND is_tombstoned = FALSE``).

Full consent-aware RLS (consent_token validation, classification
ceiling, safe-mode filtering, active-consent JOIN) is **deferred** to
P16-008. Until that work lands, the methods in this class:

* Apply the DDL v4 placeholder policies (idempotent).
* Log a warning when an "upgrade" is requested -- the upgrade is a
  no-op until P16-008 ships.
* Verify which ``kg_*`` tables currently have RLS enabled.
* Summarise the existing policies for audit purposes.

All SQL is defined as module-level constants (no f-strings) to make
injection impossible. User input never reaches the SQL string.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Protocol

from sqlalchemy import text

from guinevere.knowledge_graph.errors import KGError

if TYPE_CHECKING:  # pragma: no cover -- typing-only
    from sqlalchemy.ext.asyncio import AsyncSession


# ---------------------------------------------------------------------------
# Local RLS error (subclass of the package's existing ``KGError``).
#
# The package-level ``guinevere.knowledge_graph.errors`` module already defines
# ``KGError`` and the consent-specific ``KGConsentError``; we deliberately
# add a separate ``KGRowLevelSecurityError`` here (subclassing ``KGError``)
# so that RLS failures are categorised distinctly from consent failures
# in observability and policy routing. This keeps the consent package
# self-contained without modifying the parent ``errors`` module.
# ---------------------------------------------------------------------------


class KGRowLevelSecurityError(KGError):
    """Raised when an RLS policy cannot be applied or verified."""


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants -- table inventory
# ---------------------------------------------------------------------------

#: Every ``kg_*`` table that participates in the Knowledge Graph.
#: ``apply_rls_policies`` iterates over this list.
KG_TABLES: tuple[str, ...] = (
    "kg_entities",
    "kg_edges",
    "kg_episodes",
    "kg_same_as_edges",
    "kg_episode_participants",
    "kg_consent_audit",
)

#: Schema that hosts all ``kg_*`` tables.
KG_SCHEMA: str = "memory"

#: Postgres role that owns the service connection. RLS policies are
#: granted to this role; superuser connections bypass RLS, which is
#: why callers must NEVER connect as a superuser for KG work.
SERVICE_ROLE: str = "guinevere_core"


# ---------------------------------------------------------------------------
# SQL constants (no f-strings, no interpolation of user input)
# ---------------------------------------------------------------------------

#: Enable RLS on a table. Parameterised on table name (validated against
#: :data:`KG_TABLES` before binding).
_ENABLE_RLS_SQL: str = (
    "ALTER TABLE memory.{table} ENABLE ROW LEVEL SECURITY"
)

#: Idempotent policy creation: ``CREATE POLICY`` would error if a policy
#: with the same name already exists. We drop-and-recreate using a
#: constant policy name. Parameterised on table name.
_DROP_POLICY_SQL: str = "DROP POLICY IF EXISTS {policy_name} ON memory.{table}"
_CREATE_POLICY_SQL: str = (
    "CREATE POLICY {policy_name} ON memory.{table} "
    "FOR ALL TO guinevere_core "
    "USING ({using_expr})"
)

#: Per-table USING expressions (placeholder soft-delete filter).
#: These are constants, not f-strings, so they cannot be
#: influenced by user input.
POLICY_USING_EXPRESSIONS: dict[str, str] = {
    "kg_entities": "deletion_state != 'deleted' AND is_tombstoned = FALSE",
    "kg_edges": "deletion_state != 'deleted' AND is_tombstoned = FALSE",
    "kg_episodes": "deletion_state != 'deleted' AND is_tombstoned = FALSE",
    # Read-through tables: no soft-delete column, so the placeholder
    # policy is a no-op. P16-008 will tighten these to a
    # consent-aware USING expression.
    "kg_same_as_edges": "TRUE",
    "kg_episode_participants": "TRUE",
    "kg_consent_audit": "TRUE",
}

#: Policy name per table. Kept as a constant mapping so audit reports
#: can link a policy back to its owning table.
POLICY_NAMES: dict[str, str] = {
    "kg_entities": "kg_entities_service",
    "kg_edges": "kg_edges_service",
    "kg_episodes": "kg_episodes_service",
    "kg_same_as_edges": "kg_same_as_service",
    "kg_episode_participants": "kg_episode_participants_service",
    "kg_consent_audit": "kg_consent_audit_service",
}

#: Query -- is RLS enabled on the given table? Parameterised on the
#: *schema-qualified* table name (validated against :data:`KG_TABLES`).
_RLS_ENABLED_SQL: str = (
    "SELECT c.relname AS tablename, c.relrowsecurity AS rls_enabled "
    "FROM pg_class c "
    "JOIN pg_namespace n ON n.oid = c.relnamespace "
    "WHERE n.nspname = :schema AND c.relname = ANY(:tables)"
)

#: Query -- list every policy on a ``kg_*`` table.
_POLICY_SUMMARY_SQL: str = (
    "SELECT schemaname, tablename, policyname, "
    "       permissive, roles, cmd, qual, with_check "
    "FROM pg_policies "
    "WHERE schemaname = :schema AND tablename = ANY(:tables) "
    "ORDER BY tablename, policyname"
)


# ---------------------------------------------------------------------------
# Session factory protocol
# ---------------------------------------------------------------------------


class _SessionFactory(Protocol):
    """Minimal async session-factory protocol used by
    :class:`RLSPolicyManager`."""

    def __call__(self) -> "AsyncSession":  # pragma: no cover -- structural
        ...


# ---------------------------------------------------------------------------
# RLSPolicyManager
# ---------------------------------------------------------------------------


class RLSPolicyManager:
    """Apply, verify, and summarise Knowledge Graph RLS policies.

    This manager is invoked during database migrations and during the
    post-deploy audit gate. It never accepts user input into its SQL
    strings: all identifiers come from module-level constants.
    """

    def __init__(self, session_factory: _SessionFactory) -> None:
        if not session_factory:
            raise ValueError("session_factory is required")
        self._session_factory = session_factory

    # ------------------------------------------------------------------
    # Apply (idempotent)
    # ------------------------------------------------------------------

    async def apply_rls_policies(self) -> None:
        """Apply the DDL v4 placeholder policies to every ``kg_*`` table.

        The operation is idempotent: each policy is dropped before being
        recreated. SQL identifiers are taken from module-level
        constants -- no caller-supplied data ever reaches the SQL.
        """
        try:
            async with self._session_factory() as session:
                for table in KG_TABLES:
                    using_expr = POLICY_USING_EXPRESSIONS[table]
                    policy_name = POLICY_NAMES[table]
                    # We render the DDL into per-iteration strings by
                    # formatting the *constant* table identifier; this
                    # is safe because ``table`` is a member of
                    # ``KG_TABLES`` (validated above) and is not user
                    # input. The USING expression is also a constant.
                    enable_sql = _ENABLE_RLS_SQL.format(table=table)
                    drop_sql = _DROP_POLICY_SQL.format(
                        policy_name=policy_name, table=table
                    )
                    create_sql = _CREATE_POLICY_SQL.format(
                        policy_name=policy_name,
                        table=table,
                        using_expr=using_expr,
                    )
                    await session.execute(text(enable_sql))
                    await session.execute(text(drop_sql))
                    await session.execute(text(create_sql))
                await session.commit()
        except KGRowLevelSecurityError:
            raise
        except Exception as exc:  # noqa: BLE001 -- defensive boundary
            logger.exception(
                "RLSPolicyManager.apply_rls_policies failed: %s", exc
            )
            raise KGRowLevelSecurityError(
                f"apply_rls_policies failed: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Upgrade (deferred to P16-008)
    # ------------------------------------------------------------------

    async def upgrade_rls_with_consent_awareness(self) -> None:
        """TODO(P16-008): full consent-aware RLS.

        The placeholder policies installed by :meth:`apply_rls_policies`
        do NOT validate ``consent_token``, classification ceiling,
        safe-mode filtering, or active-consent JOIN. Those checks are
        deferred to P16-008.

        Until that work lands this method is a logged no-op. It exists
        so callers can wire up the upgrade entry point today and have
        it activate automatically when P16-008 ships.
        """
        logger.warning(
            "RLSPolicyManager.upgrade_rls_with_consent_awareness: "
            "P16-008 deferred. Placeholder RLS is currently active -- "
            "consent_token validation is performed at the application "
            "layer by ConsentManager.check_consent, NOT by the "
            "database. Do not claim consent/RLS is enforced at the "
            "DB level until P16-008 is complete."
        )

    # ------------------------------------------------------------------
    # Verify
    # ------------------------------------------------------------------

    async def verify_rls_active(self) -> dict[str, bool]:
        """Return ``{table_name: is_enabled}`` for every ``kg_*`` table.

        Read-only inspection of ``pg_class.relrowsecurity``. Any
        database error is converted to ``{table: False}`` so a broken
        verify never falsely claims RLS is active.
        """
        results: dict[str, bool] = {table: False for table in KG_TABLES}
        try:
            async with self._session_factory() as session:
                rows = (
                    await session.execute(
                        text(_RLS_ENABLED_SQL),
                        {
                            "schema": KG_SCHEMA,
                            "tables": list(KG_TABLES),
                        },
                    )
                ).all()
        except Exception as exc:  # noqa: BLE001 -- defensive boundary
            logger.exception(
                "RLSPolicyManager.verify_rls_active failed: %s", exc
            )
            return results  # all False -- fail closed
        for row in rows:
            if row is None:
                continue
            tablename, rls_enabled = row[0], bool(row[1])
            if tablename in results:
                results[tablename] = rls_enabled
        return results

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    async def get_rls_policy_summary(self) -> list[dict[str, object]]:
        """Return one dict per policy on any ``kg_*`` table.

        Each dict has keys: ``schemaname``, ``tablename``,
        ``policyname``, ``permissive``, ``roles``, ``cmd``, ``qual``,
        ``with_check``, ``retrieved_at``. Read-only; errors return
        an empty list.
        """
        retrieved_at = datetime.now(timezone.utc)
        try:
            async with self._session_factory() as session:
                rows = (
                    await session.execute(
                        text(_POLICY_SUMMARY_SQL),
                        {
                            "schema": KG_SCHEMA,
                            "tables": list(KG_TABLES),
                        },
                    )
                ).all()
        except Exception as exc:  # noqa: BLE001 -- defensive boundary
            logger.exception(
                "RLSPolicyManager.get_rls_policy_summary failed: %s", exc
            )
            return []
        summary: list[dict[str, object]] = []
        for row in rows:
            if row is None:
                continue
            summary.append(
                {
                    "schemaname": row[0],
                    "tablename": row[1],
                    "policyname": row[2],
                    "permissive": row[3],
                    "roles": row[4],
                    "cmd": row[5],
                    "qual": row[6],
                    "with_check": row[7],
                    "retrieved_at": retrieved_at,
                }
            )
        return summary


# ---------------------------------------------------------------------------
# Re-exports
# ---------------------------------------------------------------------------

__all__: list[str] = [
    "KG_TABLES",
    "KG_SCHEMA",
    "POLICY_NAMES",
    "POLICY_USING_EXPRESSIONS",
    "RLSPolicyManager",
    "SERVICE_ROLE",
]
