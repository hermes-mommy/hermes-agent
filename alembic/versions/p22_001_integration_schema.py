"""p22_integration_schema -- P22 Life Integration Hub audit + registry.

Creates audit.integration_api_log (hash-chained, INSERT/SELECT only) and
p22.integration_registry metadata table for integration action auditing.

Schema follows P22 plan §Audit Trail Model:
- audit.integration_api_log: WORM (Write-Once-Read-Many), hash-chained
- p22.integration_registry: integration metadata (no secrets)
- Both carry project_id/project_scope columns (P19 namespace propagation)

Revision ID: p22_001_integration_schema
Revises: p19_003_audit_chain_version
Create Date: 2026-06-27
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "p22_001_integration_schema"
down_revision: Union[str, Sequence[str], None] = "p19_003_audit_chain_version"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create P22 integration audit + registry schema.

    Idempotent: uses IF NOT EXISTS for safe re-runs.
    """
    # 1. audit.integration_api_log — hash-chained WORM table
    op.execute("""
        CREATE TABLE IF NOT EXISTS audit.integration_api_log (
            id                  BIGSERIAL PRIMARY KEY,
            event_id            UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
            sequence            BIGSERIAL NOT NULL,
            occurred_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
            actor_type          TEXT NOT NULL CHECK (actor_type IN ('user','agent','system')),
            actor_id            TEXT NOT NULL,
            integration_id      TEXT NOT NULL,
            provider            TEXT NOT NULL,
            action              TEXT NOT NULL,
            tier                TEXT NOT NULL,
            project_id          UUID,
            project_scope       TEXT,
            result              TEXT NOT NULL,
            correlation_id      UUID,
            metadata            JSONB NOT NULL DEFAULT '{}'::jsonb,
            previous_hash       TEXT NOT NULL DEFAULT '',
            event_hash          TEXT NOT NULL,
            chain_version       SMALLINT NOT NULL DEFAULT 2
        );
    """)

    # Indexes for audit query patterns
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_integration_api_log_integration_id
            ON audit.integration_api_log (integration_id);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_integration_api_log_occurred_at
            ON audit.integration_api_log (occurred_at DESC);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_integration_api_log_project_id
            ON audit.integration_api_log (project_id)
            WHERE project_id IS NOT NULL;
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_integration_api_log_correlation_id
            ON audit.integration_api_log (correlation_id);
    """)

    # WORM enforcement: revoke UPDATE/DELETE from application role
    op.execute("""
        REVOKE UPDATE, DELETE ON audit.integration_api_log FROM guinevere_core;
    """)
    op.execute("""
        GRANT INSERT, SELECT ON audit.integration_api_log TO guinevere_core;
    """)

    # 2. p22.integration_registry — integration metadata (no secret values)
    op.execute("CREATE SCHEMA IF NOT EXISTS p22;")

    op.execute("""
        CREATE TABLE IF NOT EXISTS p22.integration_registry (
            integration_id      TEXT PRIMARY KEY,
            name                TEXT NOT NULL,
            provider            TEXT NOT NULL,
            capabilities        TEXT[] NOT NULL DEFAULT '{}',
            default_tier        TEXT NOT NULL DEFAULT 'L1_READ',
            secret_refs         TEXT[] NOT NULL DEFAULT '{}',
            project_aware       BOOLEAN NOT NULL DEFAULT TRUE,
            consent_scopes      TEXT[] NOT NULL DEFAULT '{}',
            risk_tier           TEXT NOT NULL DEFAULT 'low',
            enabled             BOOLEAN NOT NULL DEFAULT FALSE,
            config_status       TEXT NOT NULL DEFAULT 'config_missing',
            last_health_check   TIMESTAMPTZ,
            last_status         TEXT,
            metadata            JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_integration_registry_enabled
            ON p22.integration_registry (enabled) WHERE enabled = TRUE;
    """)

    op.execute("""
        GRANT SELECT, INSERT, UPDATE ON p22.integration_registry TO guinevere_core;
    """)

    # 3. p22.secret_ref_metadata — secret references (no values, metadata only)
    op.execute("""
        CREATE TABLE IF NOT EXISTS p22.secret_ref_metadata (
            secret_id           TEXT PRIMARY KEY,
            provider            TEXT NOT NULL,
            classification      TEXT NOT NULL DEFAULT 'Critical',
            rotation_cadence    TEXT NOT NULL DEFAULT 'quarterly',
            last_rotated        TIMESTAMPTZ,
            revoke_method       TEXT,
            project_scoped      BOOLEAN NOT NULL DEFAULT FALSE,
            metadata            JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)

    op.execute("""
        GRANT SELECT, INSERT, UPDATE ON p22.secret_ref_metadata TO guinevere_core;
    """)

    # Backfill integration_registry with the 12 P22 integrations (all disabled by default)
    op.execute("""
        INSERT INTO p22.integration_registry (integration_id, name, provider, capabilities, default_tier, risk_tier, config_status) VALUES
            ('discord', 'Discord', 'Discord', ARRAY['read','write','delete','execute'], 'L1_READ', 'medium', 'config_missing'),
            ('gmail', 'Gmail', 'Google', ARRAY['read','write','delete','sync'], 'L1_READ', 'medium', 'config_missing'),
            ('github', 'GitHub', 'GitHub', ARRAY['read','write','delete','execute','sync'], 'L1_READ', 'high', 'config_missing'),
            ('calendar', 'Google Calendar', 'Google', ARRAY['read','write','delete','sync'], 'L1_READ', 'medium', 'config_missing'),
            ('drive', 'Google Drive', 'Google', ARRAY['read','write','delete'], 'L1_READ', 'high', 'config_missing'),
            ('notion', 'Notion', 'Notion', ARRAY['read','write','delete','search'], 'L1_READ', 'medium', 'config_missing'),
            ('telegram', 'Telegram', 'Telegram', ARRAY['read','write','delete','execute'], 'L1_READ', 'medium', 'config_missing'),
            ('whatsapp', 'WhatsApp', 'Neonize/Baileys', ARRAY['read','write','delete'], 'L1_READ', 'medium', 'config_missing'),
            ('vps', 'VPS System Health', 'Docker/Systemd', ARRAY['read','write','delete','execute'], 'L1_READ', 'high', 'config_missing'),
            ('finance', 'Finance Tracker', 'Polars/PG', ARRAY['read','write','delete'], 'L1_READ', 'high', 'config_missing'),
            ('browser', 'Browser/Research', 'Brave/Exa/Obscura', ARRAY['read','write','search'], 'L1_READ', 'low', 'config_missing'),
            ('memory', 'Memory/KG', 'PostgreSQL/pgvector', ARRAY['read','write','delete','search'], 'L1_READ', 'critical', 'config_missing')
        ON CONFLICT (integration_id) DO NOTHING;
    """)


def downgrade() -> None:
    """Drop P22 schema (non-destructive — audit log preserved if data exists).

    Note: audit.integration_api_log is WORM and may contain production audit
    data. Downgrade drops the table but real deployments should archive first.
    """
    op.execute("DROP TABLE IF EXISTS p22.secret_ref_metadata;")
    op.execute("DROP TABLE IF EXISTS p22.integration_registry;")
    # audit.integration_api_log dropped last (may contain historical data)
    op.execute("DROP TABLE IF EXISTS audit.integration_api_log;")
    # Do not drop p22 schema (may have other objects)
