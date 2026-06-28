"""p22_002_revoke_truncate_audit -- Complete the WORM contract on the audit table.

The p22_001 migration revoked UPDATE and DELETE from the application role
(guinevere_core) but did NOT revoke TRUNCATE. A table owner (or any role with
TRUNCATE grant) could wipe the audit log via TRUNCATE, bypassing the
UPDATE/DELETE WORM restriction. This migration explicitly revokes TRUNCATE
to close that gap (brutal-audit finding F13 -- HIGH).

WORM contract after this migration:
- INSERT, SELECT: granted to guinevere_core (audit writing + reading)
- UPDATE, DELETE, TRUNCATE: revoked from guinevere_core (immutable + non-truncatable)
For high-integrity deployments, consider transferring table ownership to a
separate ``guinevere_audit_owner`` role that cannot be assumed by the app.

Idempotent: REVOKE is safe to re-run.

Revision ID: p22_002_revoke_truncate_audit
Revises: p22_001_integration_schema
Create Date: 2026-06-28
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "p22_002_revoke_truncate_audit"
down_revision: Union[str, Sequence[str], None] = "p22_001_integration_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Revoke TRUNCATE on audit.integration_api_log to complete WORM enforcement."""
    # REVOKE TRUNCATE from the application role (guinevere_core) and from PUBLIC
    # (belt-and-braces against any implicit grant). Idempotent: REVOKE is safe
    # to re-run. We do NOT revoke INSERT/SELECT (those are required for audit
    # writing + reading).
    op.execute(
        "REVOKE TRUNCATE ON audit.integration_api_log FROM guinevere_core;"
    )
    op.execute(
        "REVOKE TRUNCATE ON audit.integration_api_log FROM PUBLIC;"
    )


def downgrade() -> None:
    """No-op downgrade.

    This migration is a security-hardening REVOKE. Downgrade does NOT re-grant
    TRUNCATE (if you truly need it, grant it manually with explicit operator
    approval). Re-granting a table-wipe capability silently would be unsafe.
    """
    pass
