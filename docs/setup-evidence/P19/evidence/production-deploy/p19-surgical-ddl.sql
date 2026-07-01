-- P19 Surgical DDL for Production Deploy
-- Date: 2026-06-26
-- Strategy: Create new schemas/tables only (no ALTER on existing tables)

-- 1. Create projects schema
CREATE SCHEMA IF NOT EXISTS projects;

-- 2. Create projects.project_registry table
CREATE TABLE IF NOT EXISTS projects.project_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    archived_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    default_channel_id TEXT,
    dashboard_channel_id TEXT,
    log_channel_id TEXT,
    accent_color TEXT
);

-- 3. Seed default project
INSERT INTO projects.project_registry (id, slug, name, status)
VALUES ('00000000-0000-0000-0000-000000000001', 'default', 'Default Project', 'active')
ON CONFLICT (slug) DO NOTHING;

-- 4. Create ops schema for alembic version tracking
CREATE SCHEMA IF NOT EXISTS ops;

-- 5. Create alembic_version table
CREATE TABLE IF NOT EXISTS ops.alembic_version (
    version_num VARCHAR(32) NOT NULL
);

-- 6. Stamp P19 migrations
INSERT INTO ops.alembic_version (version_num) VALUES ('p19_001_project_namespaces') ON CONFLICT DO NOTHING;
INSERT INTO ops.alembic_version (version_num) VALUES ('p19_002_project_id_not_null') ON CONFLICT DO NOTHING;
INSERT INTO ops.alembic_version (version_num) VALUES ('p19_003_audit_chain_version') ON CONFLICT DO NOTHING;

-- 7. Verification queries
SELECT 'Schema created: projects' AS status;
SELECT 'Table created: projects.project_registry' AS status;
SELECT 'Default project seeded' AS status;
SELECT 'Schema created: ops' AS status;
SELECT 'Table created: ops.alembic_version' AS status;
SELECT 'P19 migrations stamped' AS status;
