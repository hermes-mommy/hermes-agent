-- P8-003: PostgreSQL role for prometheus postgres_exporter
-- Creates a minimal-privilege role for metrics collection
-- Run as superuser: psql -h 127.0.0.1 -p 5433 -U postgres -d guinevere -f postgres_exporter_role.sql
--
-- SECURITY: Password must be replaced with SOPS-decrypted value before execution.
-- Never commit the actual password. Use: sops -d monitoring/.env.enc | grep PG_EXPORTER_PASSWORD

-- Create the exporter role (idempotent)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'postgres_exporter') THEN
        CREATE ROLE postgres_exporter WITH LOGIN PASSWORD 'CHANGE_ME_VIA_SOPS';
        RAISE NOTICE 'Created role: postgres_exporter';
    ELSE
        RAISE NOTICE 'Role postgres_exporter already exists, skipping creation';
    END IF;
END
$$;

-- Grant pg_monitor: provides read access to all statistics views
-- This is the minimum required role for postgres_exporter metrics collection
-- Includes: pg_stat_activity, pg_stat_database, pg_stat_all_tables, pg_stat_user_tables, etc.
GRANT pg_monitor TO postgres_exporter;

-- Grant connect to guinevere database
GRANT CONNECT ON DATABASE guinevere TO postgres_exporter;

-- Verify the role was created correctly
SELECT rolname, rolsuper, rolcreaterole, rolcreatedb, rolcanlogin
FROM pg_roles
WHERE rolname = 'postgres_exporter';
