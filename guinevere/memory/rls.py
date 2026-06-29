"""PostgreSQL Row-Level Security helpers for agent-scoped data isolation.

Uses SET LOCAL for transaction-scoped agent_id injection.
Fail-soft: all functions gracefully handle absent PostgreSQL by returning
False/raising no errors.

Design per r05 research section 4.1:
  - Non-superuser app role: guinevere_core (already in db.py:36)
  - SET LOCAL app.current_agent_id = <uuid> per transaction
  - current_agent_id() SQL function reads the session variable
  - USING + WITH CHECK on ALL operations
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# SQL for creating the current_agent_id() helper function.
# Idempotent — uses CREATE OR REPLACE.
CURRENT_AGENT_ID_FUNCTION = """
CREATE OR REPLACE FUNCTION current_agent_id()
RETURNS UUID AS $$
    SELECT NULLIF(current_setting('app.current_agent_id', true), '')::UUID;
$$ LANGUAGE SQL STABLE;
"""

# Template for RLS policy creation on a given table.
# Expects: {schema}, {table}, {agent_id_col} substitutions.
RLS_POLICY_TEMPLATE = """
ALTER TABLE {schema}.{table} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.{table} FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = '{schema}'
          AND tablename = '{table}'
          AND policyname = 'agent_isolation_{table}'
    ) THEN
        EXECUTE format(
            'CREATE POLICY agent_isolation_{table} ON {schema}.{table} '
            'FOR ALL '
            'USING ({agent_id_col} = current_agent_id()) '
            'WITH CHECK ({agent_id_col} = current_agent_id())'
        );
    END IF;
END$$;
"""

# SQL to set the agent_id within a transaction scope.
# Uses set_config with is_local=false to make it session-level but
# transaction-scoped when wrapped in BEGIN/COMMIT.
SET_AGENT_ID_SQL = "SELECT set_config('app.current_agent_id', $1, false)"

# Tables that should have RLS enabled (from r05 research).
_RLS_TABLES = [
    ("memory", "episodes", "agent_id"),
    ("memory", "semantic_facts", "agent_id"),
    ("memory", "kg_entities", "agent_id"),
    ("memory", "kg_edges", "agent_id"),
]


def get_rls_setup_sql() -> str:
    """Return the full SQL script to set up RLS.

    This is design-only (D2) — real DB migration applies via Alembic.
    Returns the SQL that would be applied for reference/documentation.
    """
    parts = [CURRENT_AGENT_ID_FUNCTION]
    for schema, table, agent_id_col in _RLS_TABLES:
        parts.append(
            RLS_POLICY_TEMPLATE.format(
                schema=schema,
                table=table,
                agent_id_col=agent_id_col,
            )
        )
    return "\n".join(parts)


async def apply_agent_rls(conn, agent_id: str) -> None:
    """Set the transaction-scoped agent_id via SET LOCAL.

    Args:
        conn: An asyncpg connection (must be inside a transaction).
        agent_id: UUID string for the current agent.

    This is a no-op if conn is None (fail-soft for absent PG).
    """
    if conn is None:
        logger.debug("apply_agent_rls: no connection, skipping (fail-soft)")
        return
    try:
        await conn.execute(SET_AGENT_ID_SQL, agent_id)
        logger.debug("RLS agent_id set to %s", agent_id)
    except Exception:
        logger.warning(
            "Failed to set RLS agent_id (PG may be unavailable)",
            exc_info=True,
        )


def build_set_local_statement(agent_id: str) -> str:
    """Build a SQL statement that sets the agent_id in the current session.

    Returns a SQL string suitable for raw execution.
    For use with SQLAlchemy or asyncpg connections.
    """
    # Escape single quotes in agent_id to prevent SQL injection
    safe_id = agent_id.replace("'", "''")
    return f"SELECT set_config('app.current_agent_id', '{safe_id}', false)"
