"""p24_consent_ref_nullable -- Make consent_ref nullable for hermes_runtime events (ADR-066).

ADR-066: consent_ref is nullable when event_source='hermes_runtime'.
dev_workflow events MUST retain NOT NULL on consent_ref.
This migration adds an event_source column and a CHECK constraint to
5 society event-store tables, IF those tables exist.

Defensive (D2, no live PG): uses inspect + try/except so it won't fail
on databases that don't have these tables yet.

Revision ID: p24_consent_ref_nullable
Revises: p22_002_revoke_truncate_audit
Create Date: 2026-06-29
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

# revision identifiers, used by Alembic.
revision: str = "p24_consent_ref_nullable"
down_revision: Union[str, Sequence[str], None] = "p22_002_revoke_truncate_audit"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EVENT_TABLES = [
    "society_event_memory",
    "society_event_decision",
    "society_event_action",
    "society_event_drift",
    "society_event_publication",
]


def _table_exists(conn, table_name: str) -> bool:
    """Return True if *table_name* exists in the public schema."""
    insp = sa_inspect(conn)
    return table_name in insp.get_table_names(schema="public")


def _col_exists(conn, table_name: str, col_name: str) -> bool:
    """Return True if *col_name* exists on *table_name*."""
    insp = sa_inspect(conn)
    return any(c["name"] == col_name for c in insp.get_columns(table_name, schema="public"))


def upgrade() -> None:
    """Add event_source column and relax consent_ref for hermes_runtime."""
    conn = op.get_bind()

    for tbl in EVENT_TABLES:
        if not _table_exists(conn, tbl):
            # Table doesn't exist yet (D2 local-only). Skip.
            continue

        # 1. Add event_source column (default 'dev_workflow' for existing rows)
        if not _col_exists(conn, tbl, "event_source"):
            op.add_column(
                tbl,
                sa.Column(
                    "event_source",
                    sa.String(32),
                    nullable=False,
                    server_default="dev_workflow",
                ),
            )

        # 2. Make consent_ref nullable
        op.alter_column(
            tbl,
            "consent_ref",
            existing_type=sa.String(256),
            nullable=True,
        )

        # 3. Add CHECK: dev_workflow rows MUST have consent_ref NOT NULL
        constraint_name = f"ck_{tbl}_consent_ref_not_null_dev_workflow"
        op.execute(
            f"ALTER TABLE {tbl} ADD CONSTRAINT {constraint_name} "
            f"CHECK (event_source <> 'dev_workflow' OR consent_ref IS NOT NULL)"
        )


def downgrade() -> None:
    """Remove event_source column and re-enforce NOT NULL on consent_ref."""
    conn = op.get_bind()

    for tbl in EVENT_TABLES:
        if not _table_exists(conn, tbl):
            continue

        constraint_name = f"ck_{tbl}_consent_ref_not_null_dev_workflow"
        op.execute(f"ALTER TABLE {tbl} DROP CONSTRAINT IF EXISTS {constraint_name}")

        # Re-enforce NOT NULL (only safe if all rows are dev_workflow with non-null)
        op.alter_column(
            tbl,
            "consent_ref",
            existing_type=sa.String(256),
            nullable=False,
        )

        if _col_exists(conn, tbl, "event_source"):
            op.drop_column(tbl, "event_source")
