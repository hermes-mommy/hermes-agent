-- =============================================================================
-- P3-004: PostgreSQL Mirror — RLS + RBAC
-- =============================================================================
-- Purpose: Create hermes_memory_bridge role with SELECT-ONLY access to memory
--          schema tables, RLS policies enforcing classification ceiling (max
--          CONFIDENTIAL) and surveillance isolation.
--
-- Execution:
--   export HERMES_MEMORY_BRIDGE_PASSWORD='<sops-decrypted-password>'
--   psql -h 127.0.0.1 -p 5433 -U guinevere_core -d guinevere -f this_file.sql
--
-- Password: loaded from $HERMES_MEMORY_BRIDGE_PASSWORD at runtime.
-- NEVER hardcode a password in this file — use \getenv.
--
-- Author: Guinevere (P3-004 Migration)
-- Date: 2026-06-05
-- ADR: ADR-035 (Hermes reads via replication/mirror role, NEVER writes)
-- VPS-verified: Table owner = guinevere_core (NOT guinevere as planner v1.5 assumed)
-- =============================================================================

-- Load password from environment (fail loudly if unset)
\getenv v_password HERMES_MEMORY_BRIDGE_PASSWORD
\set ON_ERROR_STOP on

-- Check if role already exists (stored as psql var)
SELECT EXISTS(SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'hermes_memory_bridge') AS bridge_role_exists \gset

BEGIN;

-- =============================================================================
-- §1: Create hermes_memory_bridge role
-- =============================================================================
-- NOINHERIT: When granted to another role, privileges do NOT cascade automatically.
-- This is correct for a mirror/bridge role — Hermes connects directly AS the role.
-- Password: loaded from $HERMES_MEMORY_BRIDGE_PASSWORD env var at runtime.
-- ⚠️  STORE the actual password in a SOPS-encrypted secrets file only.

\if :bridge_role_exists
\else
    CREATE ROLE hermes_memory_bridge
        WITH LOGIN
        NOSUPERUSER
        NOCREATEDB
        NOCREATEROLE
        NOINHERIT
        PASSWORD :'v_password'
        CONNECTION LIMIT 5;
\endif

-- =============================================================================
-- §2: Grant schema usage
-- =============================================================================
GRANT USAGE ON SCHEMA memory TO hermes_memory_bridge;

-- =============================================================================
-- §3: Grant SELECT on specific memory tables only
-- =============================================================================
-- 8 tables confirmed on VPS (2026-06-05):
--   episodes, semantic_facts, emotional_events, faiz_profile,
--   faiz_predictions, inner_journal, knowledge_graph, procedural_skills

GRANT SELECT ON memory.episodes          TO hermes_memory_bridge;
GRANT SELECT ON memory.semantic_facts    TO hermes_memory_bridge;
GRANT SELECT ON memory.emotional_events  TO hermes_memory_bridge;
GRANT SELECT ON memory.faiz_profile      TO hermes_memory_bridge;
GRANT SELECT ON memory.faiz_predictions  TO hermes_memory_bridge;
GRANT SELECT ON memory.inner_journal     TO hermes_memory_bridge;
GRANT SELECT ON memory.knowledge_graph   TO hermes_memory_bridge;
GRANT SELECT ON memory.procedural_skills TO hermes_memory_bridge;

-- =============================================================================
-- §4: Explicitly REVOKE all write permissions
-- =============================================================================
-- Safety net: if any future table gets default GRANT, this ensures no writes.
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA memory
    FROM hermes_memory_bridge;

-- =============================================================================
-- §5: Default privileges for future tables in memory schema
-- =============================================================================
-- VPS-verified: Table owner is guinevere_core (NOT guinevere).
-- Altering default privileges for guinevere_core ensures any future tables
-- created by guinevere_core in memory schema automatically grant SELECT to
-- hermes_memory_bridge.

ALTER DEFAULT PRIVILEGES FOR ROLE guinevere_core IN SCHEMA memory
    GRANT SELECT ON TABLES TO hermes_memory_bridge;

-- =============================================================================
-- §6: Row-Level Security — Classification Ceiling
-- =============================================================================
-- Classification hierarchy: Public < Internal < Restricted < Confidential < Critical
-- Policy: hermes_memory_bridge can see rows up to Confidential.
--          Rows with classification = 'Critical' are FILTERED OUT.

-- §6.1: memory.episodes
ALTER TABLE memory.episodes ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'memory'
          AND tablename = 'episodes'
          AND policyname = 'hermes_classification_ceiling'
    ) THEN
        CREATE POLICY hermes_classification_ceiling ON memory.episodes
            FOR SELECT TO hermes_memory_bridge
            USING (classification != 'Critical');
    END IF;
END $$;

-- §6.2: memory.semantic_facts
ALTER TABLE memory.semantic_facts ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'memory'
          AND tablename = 'semantic_facts'
          AND policyname = 'hermes_classification_ceiling'
    ) THEN
        CREATE POLICY hermes_classification_ceiling ON memory.semantic_facts
            FOR SELECT TO hermes_memory_bridge
            USING (classification != 'Critical');
    END IF;
END $$;

-- §6.3: memory.emotional_events
ALTER TABLE memory.emotional_events ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'memory'
          AND tablename = 'emotional_events'
          AND policyname = 'hermes_classification_ceiling'
    ) THEN
        CREATE POLICY hermes_classification_ceiling ON memory.emotional_events
            FOR SELECT TO hermes_memory_bridge
            USING (classification != 'Critical');
    END IF;
END $$;

-- §6.4: memory.faiz_profile
ALTER TABLE memory.faiz_profile ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'memory'
          AND tablename = 'faiz_profile'
          AND policyname = 'hermes_classification_ceiling'
    ) THEN
        CREATE POLICY hermes_classification_ceiling ON memory.faiz_profile
            FOR SELECT TO hermes_memory_bridge
            USING (classification != 'Critical');
    END IF;
END $$;

-- §6.5: memory.faiz_predictions
ALTER TABLE memory.faiz_predictions ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'memory'
          AND tablename = 'faiz_predictions'
          AND policyname = 'hermes_classification_ceiling'
    ) THEN
        CREATE POLICY hermes_classification_ceiling ON memory.faiz_predictions
            FOR SELECT TO hermes_memory_bridge
            USING (classification != 'Critical');
    END IF;
END $$;

-- §6.6: memory.inner_journal
ALTER TABLE memory.inner_journal ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'memory'
          AND tablename = 'inner_journal'
          AND policyname = 'hermes_classification_ceiling'
    ) THEN
        CREATE POLICY hermes_classification_ceiling ON memory.inner_journal
            FOR SELECT TO hermes_memory_bridge
            USING (classification != 'Critical');
    END IF;
END $$;

-- §6.7: memory.knowledge_graph
ALTER TABLE memory.knowledge_graph ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'memory'
          AND tablename = 'knowledge_graph'
          AND policyname = 'hermes_classification_ceiling'
    ) THEN
        CREATE POLICY hermes_classification_ceiling ON memory.knowledge_graph
            FOR SELECT TO hermes_memory_bridge
            USING (classification != 'Critical');
    END IF;
END $$;

-- §6.8: memory.procedural_skills
ALTER TABLE memory.procedural_skills ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'memory'
          AND tablename = 'procedural_skills'
          AND policyname = 'hermes_classification_ceiling'
    ) THEN
        CREATE POLICY hermes_classification_ceiling ON memory.procedural_skills
            FOR SELECT TO hermes_memory_bridge
            USING (classification != 'Critical');
    END IF;
END $$;

-- =============================================================================
-- §7: Surveillance Isolation
-- =============================================================================
-- Explicitly revoke ALL privileges on surveillance, security, and audit schemas.
-- ADR-035: Hermes must NEVER access surveillance data.

REVOKE ALL ON ALL TABLES IN SCHEMA surveillance FROM hermes_memory_bridge;
REVOKE ALL ON ALL TABLES IN SCHEMA security     FROM hermes_memory_bridge;
REVOKE ALL ON ALL TABLES IN SCHEMA audit        FROM hermes_memory_bridge;

-- Ensure no schema-level access to restricted schemas
REVOKE ALL ON SCHEMA surveillance FROM hermes_memory_bridge;
REVOKE ALL ON SCHEMA security     FROM hermes_memory_bridge;
REVOKE ALL ON SCHEMA audit        FROM hermes_memory_bridge;

-- =============================================================================
-- §8: Verification Queries (run after migration)
-- =============================================================================
-- These queries should be executed manually after migration to verify success.

-- V-1: Confirm role exists
--   SELECT rolname, rolcanlogin, rolsuper, rolinherit
--   FROM pg_roles WHERE rolname = 'hermes_memory_bridge';
--   Expected: 1 row, canlogin=true, super=false, inherit=false

-- V-2: Confirm SELECT privileges on all memory tables
--   SELECT tablename, has_table_privilege('hermes_memory_bridge', 'memory.' || tablename, 'SELECT')
--   FROM pg_tables WHERE schemaname = 'memory' ORDER BY tablename;
--   Expected: all true

-- V-3: Confirm NO INSERT privileges
--   SELECT tablename, has_table_privilege('hermes_memory_bridge', 'memory.' || tablename, 'INSERT')
--   FROM pg_tables WHERE schemaname = 'memory' ORDER BY tablename;
--   Expected: all false

-- V-4: Confirm NO UPDATE/DELETE/TRUNCATE privileges
--   SELECT tablename,
--     has_table_privilege('hermes_memory_bridge', 'memory.' || tablename, 'UPDATE') AS can_update,
--     has_table_privilege('hermes_memory_bridge', 'memory.' || tablename, 'DELETE') AS can_delete,
--     has_table_privilege('hermes_memory_bridge', 'memory.' || tablename, 'TRUNCATE') AS can_truncate
--   FROM pg_tables WHERE schemaname = 'memory' ORDER BY tablename;
--   Expected: all false

-- V-5: Confirm RLS policies exist
--   SELECT tablename, policyname, cmd, qual
--   FROM pg_policies WHERE schemaname = 'memory' ORDER BY tablename;
--   Expected: 8 rows, all 'hermes_classification_ceiling', SELECT, classification != 'Critical'

-- V-6: Test RLS enforcement (Critical classification filtered)
--   SET ROLE hermes_memory_bridge;
--   SELECT COUNT(*) FROM memory.episodes WHERE classification = 'Critical';
--   Expected: 0 (rows filtered by RLS)
--   RESET ROLE;

-- V-7: Confirm NO access to surveillance schema
--   SELECT has_schema_privilege('hermes_memory_bridge', 'surveillance', 'USAGE');
--   Expected: false

-- V-8: Confirm NO access to security/audit schemas
--   SELECT has_schema_privilege('hermes_memory_bridge', 'security', 'USAGE');
--   SELECT has_schema_privilege('hermes_memory_bridge', 'audit', 'USAGE');
--   Expected: false, false

-- =============================================================================
COMMIT;

-- =============================================================================
-- §9: Rollback Instructions
-- =============================================================================
-- To rollback this migration:
--   BEGIN;
--   DROP OWNED BY hermes_memory_bridge;
--   DROP ROLE IF EXISTS hermes_memory_bridge;
--   COMMIT;
--
-- Note: RLS policies on tables will be dropped automatically when the role is
-- dropped. ALTER DEFAULT PRIVILEGES changes are permanent for the role and
-- must be manually removed if needed:
--   ALTER DEFAULT PRIVILEGES FOR ROLE guinevere_core IN SCHEMA memory
--     REVOKE SELECT ON TABLES FROM hermes_memory_bridge;
--
-- RLS remains ENABLED on tables but without policies targeting hermes_memory_bridge
-- they have no effect. To disable RLS on all memory tables:
--   ALTER TABLE memory.episodes DISABLE ROW LEVEL SECURITY;
--   (repeat for each table)

-- =============================================================================
-- §10: Footer
-- =============================================================================
-- | Field | Value |
-- |---|---|
-- | Migration ID | P3-004 |
-- | Date | 2026-06-05 |
-- | Author | Guinevere |
-- | VPS | 100.94.104.22 (Tailscale) |
-- | PostgreSQL | 16.14 in Docker guinevere-postgres:5433 |
-- | Database | guinevere |
-- | Table Owner | guinevere_core (verified via VPS) |
-- | Target Role | hermes_memory_bridge |
-- | Classification Ceiling | Max CONFIDENTIAL (Critical excluded) |
-- | Surveillance Isolation | REVOKE ALL on surveillance, security, audit |
-- | Write Prevention | Explicit REVOKE INSERT/UPDATE/DELETE/TRUNCATE |
-- | Password Storage | MUST encrypt via SOPS+age before production use |
-- | ADR Reference | ADR-035: Hermes NEVER writes to PG, reads via bridge role |