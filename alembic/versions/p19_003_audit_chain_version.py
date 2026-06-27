"""audit_chain_version -- P19-010 hash chain versioning field.

Adds chain_version SMALLINT column to audit.audit_trail.

Semantics:
  chain_version = 1  (default, legacy): rows created before P19.
    Canonical payload does NOT include project_id.
    Hash is computed with the original algorithm.

  chain_version = 2  (P19+): rows created after P19-010 deployment.
    Canonical payload MAY include project_id (NULL = global).
    Hash includes chain_version in the canonical input.

Existing rows are backfilled to chain_version=1 (no hash recomputation).
New rows written by AuditWriter use chain_version=2.

Revision ID: p19_003_audit_chain_version
Revises: p19_002_project_id_not_null
Create Date: 2026-06-26
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "p19_003_audit_chain_version"
down_revision: Union[str, Sequence[str], None] = "p19_002_project_id_not_null"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add chain_version column to audit.audit_trail.

    - Column: SMALLINT NOT NULL DEFAULT 1
    - Backfill: all existing rows get chain_version=1 (legacy)
    - New P19+ rows (written by AuditWriter) will use chain_version=2
    - Index: (chain_version) for version-scoped verification queries
    """
    # 1. Add column with DEFAULT 1 (backfills existing rows atomically)
    op.execute(
        "ALTER TABLE audit.audit_trail "
        "ADD COLUMN IF NOT EXISTS chain_version SMALLINT NOT NULL DEFAULT 1"
    )

    # 2. Btree index for version-scoped verification queries
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_trail_chain_version "
        "ON audit.audit_trail (chain_version)"
    )


def downgrade() -> None:
    """Remove chain_version column and its index."""
    op.execute("DROP INDEX IF EXISTS audit.ix_audit_trail_chain_version")
    op.execute("ALTER TABLE audit.audit_trail DROP COLUMN IF EXISTS chain_version")
