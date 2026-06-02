# PostgreSQL 16 Least-Privilege User/Role Best Practices

> **Research report** for Guinevere multi-service AI companion system PostgreSQL 16 setup.
> Covers: ALTER DEFAULT PRIVILEGES, GRANT vs REVOKE PUBLIC, connection privileges, NOLOGIN/INHERIT patterns, password generation, schema/user ordering, and per-service least privilege patterns.
>
> **Date**: 2026-05-31 · **PostgreSQL version**: 16.14 (current stable)

---

## Table of Contents

1. [ALTER DEFAULT PRIVILEGES — Deep Dive](#1-alter-default-privileges--deep-dive)
2. [GRANT vs REVOKE PUBLIC — Production Lockdown Pattern](#2-grant-vs-revoke-public--production-lockdown-pattern)
3. [Connection Privilege Handling](#3-connection-privilege-handling)
4. [NOLOGIN Roles + INHERIT — Group Role Pattern](#4-nologin-roles--inherit--group-role-pattern)
5. [Password Generation for scram-sha-256](#5-password-generation-for-scram-sha-256)
6. [Schema Creation Ordering](#6-schema-creation-ordering)
7. [Least Privilege Patterns per Service Role](#7-least-privilege-patterns-per-service-role)
8. [Complete Execution Order](#8-complete-execution-order)
9. [Key Traps and Pitfalls](#9-key-traps-and-pitfalls)
10. [References](#10-references)

---

## 1. ALTER DEFAULT PRIVILEGES — Deep Dive

### 1.1 Syntax (PostgreSQL 16)

```sql
ALTER DEFAULT PRIVILEGES
    [ FOR { ROLE | USER } target_role [, ...] ]
    [ IN SCHEMA schema_name [, ...] ]
    abbreviated_grant_or_revoke
```

**Source**: [PostgreSQL 16 ALTER DEFAULT PRIVILEGES docs](https://www.postgresql.org/docs/16/sql-alterdefaultprivileges.html)

### 1.2 CRITICAL: What `FOR ROLE` Actually Means

This is the **#1 misconception** in PostgreSQL privilege management:

- `FOR ROLE target_role` = **the role that will CREATE the objects**, NOT the role receiving privileges
- `GRANT ... TO recipient_role` = the role that **receives** the privileges on future objects

```sql
-- When guinevere_core creates a table in schema memory, auto-grant SELECT to guinevere_readonly
ALTER DEFAULT PRIVILEGES FOR ROLE guinevere_core IN SCHEMA memory
    GRANT SELECT ON TABLES TO guinevere_readonly;

-- This has NO EFFECT if guinevere_scheduler creates the table instead
```

**Consequence**: You need separate `ALTER DEFAULT PRIVILEGES` statements for **every role that will create objects**, not just for the role that receives privileges.

**Source**: [PostgreSQL 16 ALTER DEFAULT PRIVILEGES — Parameters](https://www.postgresql.org/docs/16/sql-alterdefaultprivileges.html)

### 1.3 Object Types Supported

| Object type | Default privileges on new objects | What you can grant |
|---|---|---|
| TABLES (incl. views, foreign tables) | Owner only | SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER |
| SEQUENCES | Owner only | USAGE, SELECT, UPDATE |
| FUNCTIONS / ROUTINES | PUBLIC gets EXECUTE by default | EXECUTE |
| TYPES (incl. domains) | PUBLIC gets USAGE by default | USAGE |
| SCHEMAS | Owner only | USAGE, CREATE |

**Critical distinction**: `IN SCHEMA` cannot be used for SCHEMA-type default privileges (schemas can't be nested). For schema defaults, use global ALTER DEFAULT PRIVILEGES.

### 1.4 Per-Schema vs Global: Additive Behavior

**Per-schema defaults ADD to global defaults** — they do NOT replace them.

```sql
-- Global default: PUBLIC gets EXECUTE on functions
-- (this is the built-in PostgreSQL default)
ALTER DEFAULT PRIVILEGES REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;  -- ✅ Works globally

ALTER DEFAULT PRIVILEGES IN SCHEMA memory REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
-- ❌ NO EFFECT! Per-schema REVOKE cannot remove a global grant.
-- Per-schema REVOKE only reverses a prior per-schema GRANT.
```

**Source**: [PostgreSQL 16 ALTER DEFAULT PRIVILEGES — Notes](https://www.postgresql.org/docs/16/sql-alterdefaultprivileges.html)

### 1.5 Timing: ALTER DEFAULT PRIVILEGES Only Affects Future Objects

```sql
-- Create table first
CREATE TABLE memory.conversations (id SERIAL PRIMARY KEY, ...);

-- Then set default privileges
ALTER DEFAULT PRIVILEGES IN SCHEMA memory GRANT SELECT ON TABLES TO guinevere_readonly;

-- ❌ 'conversations' still has no SELECT for guinevere_readonly
-- ✅ Any NEW tables created after this point WILL get the default grant

-- Fix: explicitly GRANT on existing tables
GRANT SELECT ON ALL TABLES IN SCHEMA memory TO guinevere_readonly;
```

### 1.6 Real-World Pattern (from production codebases)

From Supabase production migrations ([source](https://github.com/supabase/supabase/blob/master/examples/user-management/expo-push-notifications/supabase/migrations/20231106070403_remote_schema.sql)):

```sql
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public"
    GRANT ALL ON TABLES TO "anon", "authenticated", "service_role";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public"
    GRANT ALL ON SEQUENCES TO "anon", "authenticated", "service_role";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public"
    GRANT ALL ON FUNCTIONS TO "anon", "authenticated", "service_role";
```

From Cube.js production init ([source](https://github.com/cube-js/cube/blob/master/packages/cubejs-testing-drivers/fixtures/postgresql-init.sql)):

```sql
ALTER DEFAULT PRIVILEGES FOR ROLE test IN SCHEMA public
    GRANT SELECT ON TABLES TO test_readonly;
```

---

## 2. GRANT vs REVOKE PUBLIC — Production Lockdown Pattern

### 2.1 What PostgreSQL Grants to PUBLIC by Default

From [PostgreSQL 16 Section 5.7 Privileges](https://www.postgresql.org/docs/16/ddl-priv.html):

| Object Type | Default PUBLIC Privileges |
|---|---|
| DATABASE | CONNECT, TEMPORARY |
| SCHEMA | None |
| TABLES | None |
| SEQUENCES | None |
| FUNCTIONS / PROCEDURES | EXECUTE |
| TYPES / DOMAINS | USAGE |
| LANGUAGE | USAGE |

### 2.2 Production Lockdown Pattern

The industry-standard pattern (used by [Steampipe](https://github.com/turbot/steampipe/blob/develop/pkg/db/db_local/install.go), [Graphile](https://github.com/graphile/starter/blob/main/heroku-setup.template), [DefiLlama](https://github.com/DefiLlama/yield-server/blob/master/migrations/1662753238454_add-roles.js), [Polar](https://github.com/polarsource/polar/blob/main/server/scripts/preview.py)):

```sql
-- ============================================================
-- PHASE 1: Lock down database-level PUBLIC access
-- ============================================================

-- Revoke all default PUBLIC privileges on the database
REVOKE ALL ON DATABASE guinevere FROM PUBLIC;

-- Explicitly grant CONNECT only to roles that need it
GRANT CONNECT ON DATABASE guinevere TO guinevere_core;
GRANT CONNECT ON DATABASE guinevere TO guinevere_surveillance;
GRANT CONNECT ON DATABASE guinevere TO guinevere_scheduler;
GRANT CONNECT ON DATABASE guinevere TO guinevere_readonly;
GRANT CONNECT ON DATABASE guinevere TO guinevere_backup;

-- ============================================================
-- PHASE 2: Lock down default public schema
-- (we will create app-specific schemas, so public stays locked)
-- ============================================================

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;  -- prevent object creation in public

-- ============================================================
-- PHASE 3: Revoke default EXECUTE on functions from PUBLIC
-- (do this globally, per-schema REVOKE has no effect)
-- ============================================================

ALTER DEFAULT PRIVILEGES REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;

-- ============================================================
-- PHASE 4: Grant EXECUTE only to roles that need it per-schema
-- ============================================================

ALTER DEFAULT PRIVILEGES IN SCHEMA memory GRANT EXECUTE ON FUNCTIONS TO guinevere_core;
-- (only guinevere_core needs to CALL functions in memory schema)
```

### 2.3 Why REVOKE PUBLIC Matters

`PUBLIC` is an implicit group that includes **all roles**, including roles created in the future. Leaving `CONNECT` on the database granted to `PUBLIC` means any new role can connect. Leaving `EXECUTE` on functions granted to `PUBLIC` means any role can call any function.

**Source**: [PostgreSQL 16 GRANT docs](https://www.postgresql.org/docs/16/sql-grant.html) — "PUBLIC can be thought of as an implicitly defined group that always includes all roles."

---

## 3. Connection Privilege Handling

### 3.1 The Two-Layer Connection Control

PostgreSQL has two independent layers controlling connections:

1. **`pg_hba.conf`** — host-based authentication (IP, user, database, auth method)
2. **`GRANT CONNECT ON DATABASE`** — SQL-level privilege

Both must allow the connection. For Docker PostgreSQL 16:

- `pg_hba.conf` will typically allow `md5`/`scram-sha-256` for all users
- The SQL-level `GRANT CONNECT` is **your fine-grained control**

### 3.2 Template for Production

```sql
-- After REVOKE ALL ON DATABASE guinevere FROM PUBLIC:
GRANT CONNECT ON DATABASE guinevere TO guinevere_core;
GRANT CONNECT ON DATABASE guinevere TO guinevere_surveillance;
GRANT CONNECT ON DATABASE guinevere TO guinevere_scheduler;
GRANT CONNECT ON DATABASE guinevere TO guinevere_readonly;
GRANT CONNECT ON DATABASE guinevere TO guinevere_backup;
GRANT TEMPORARY ON DATABASE guinevere TO guinevere_core;  -- only core needs temp tables
```

**Source**: [PostgreSQL 16 GRANT docs](https://www.postgresql.org/docs/16/sql-grant.html) — "CONNECT privilege is checked at connection startup (in addition to checking any restrictions imposed by pg_hba.conf)."

### 3.3 Schema-Level Access (After Connection)

`GRANT CONNECT ON DATABASE` allows connecting but NOT accessing any objects. After connection, the user needs:

```sql
-- For each schema the user needs to access:
GRANT USAGE ON SCHEMA memory TO guinevere_core;
GRANT USAGE ON SCHEMA surveillance TO guinevere_surveillance;
-- etc.
```

Without `USAGE` on a schema, the user cannot see objects in it.

**Source**: [PostgreSQL 16 Privileges docs](https://www.postgresql.org/docs/16/ddl-priv.html)

---

## 4. NOLOGIN Roles + INHERIT — Group Role Pattern

### 4.1 The Supabase Pattern (Production Reference)

Supabase uses this pattern extensively ([source](https://github.com/supabase/postgres/blob/develop/migrations/db/init-scripts/00000000000000-initial-schema.sql)):

```sql
-- Group roles (NOLOGIN = cannot connect directly)
CREATE ROLE anon NOLOGIN NOINHERIT;
CREATE ROLE authenticated NOLOGIN NOINHERIT;
CREATE ROLE service_role NOLOGIN NOINHERIT BYPASSRLS;

-- Login user (NOINHERIT = must SET ROLE to gain privileges)
CREATE USER authenticator NOINHERIT;

-- Grant group membership
GRANT anon TO authenticator;
GRANT authenticated TO authenticator;
GRANT service_role TO authenticator;

-- Actual app user connects as 'authenticator', then SET ROLE to 'anon'/'authenticated'/'service_role'
```

### 4.2 When to Use NOLOGIN Group Roles vs Direct LOGIN Roles

**Use NOLOGIN group roles when**:
- You need to grant the same privilege set to multiple login users
- You want to separate "what you can do" (group) from "who you are" (login)
- You're using a connection pooler like PgBouncer with `SET ROLE` pattern

**Use direct LOGIN roles (simpler) when**:
- Each service has a distinct, non-overlapping privilege set
- You have 5 fixed services with fixed schemas
- You don't need shared privilege groups

### 4.3 Recommendation for Guinevere

**For 5 distinct services with distinct schemas, direct LOGIN roles are simpler and sufficient:**

```sql
CREATE USER guinevere_core WITH LOGIN PASSWORD '<password>' INHERIT;
CREATE USER guinevere_surveillance WITH LOGIN PASSWORD '<password>' INHERIT;
CREATE USER guinevere_scheduler WITH LOGIN PASSWORD '<password>' INHERIT;
CREATE USER guinevere_readonly WITH LOGIN PASSWORD '<password>' INHERIT;
CREATE USER guinevere_backup WITH LOGIN PASSWORD '<password>' INHERIT;
```

**If you anticipate adding more services later**, create NOLOGIN group roles:

```sql
CREATE ROLE guinevere_core_group NOLOGIN;
CREATE ROLE guinevere_surveillance_group NOLOGIN;
-- ... grant privileges to groups ...
CREATE USER guinevere_core WITH LOGIN PASSWORD '<password>' INHERIT;
GRANT guinevere_core_group TO guinevere_core;
```

**Source**: [PostgreSQL 16 Role Membership docs](https://www.postgresql.org/docs/16/role-membership.html) — "Typically a role being used as a group would not have the LOGIN attribute."

---

## 5. Password Generation for scram-sha-256

### 5.1 PostgreSQL 16 Password Hashing

PostgreSQL 16 defaults to `scram-sha-256` when `password_encryption = 'scram-sha-256'` (default since PostgreSQL 14). The SCRAM-SHA-256 algorithm:

- Uses PBKDF2 with SHA-256 (4096 iterations as per RFC 7677)
- Produces a 32-byte (256-bit) ServerKey and StoredKey
- The stored hash is completely different from the raw password
- The raw password length does NOT affect hash output size

**Source**: [PostgreSQL 16 Password Authentication docs](https://www.postgresql.org/docs/16/auth-password.html)

### 5.2 Password Generation Commands

```bash
# RECOMMENDED: 32 random bytes = 256 bits of entropy, base64-encoded
openssl rand -base64 32
# Example output: 7Xj3m8KpL9qR2vN5wB6yC4zA1dE0fG8hI2sT4uV6wX0=

# Alternative: 32 random bytes, hex-encoded (64 chars)
openssl rand -hex 32
# Example output: a1b2c3d4e5f6789012345678abcdef0123456789abcdef0123456789abcdef01

# For a password file (one password per line):
openssl rand -base64 32 > passwords/guinevere_core.txt
```

### 5.3 Is `openssl rand -base64 32` Sufficient?

**Yes, it is more than sufficient.**

| Metric | Value |
|---|---|
| Entropy | 256 bits |
| Brute-force at 10¹² guesses/sec | ~10⁶⁵ years |
| SCRAM-SHA-256 iteration count | 4096 (slows each guess by ~4000×) |
| Effective entropy against SCRAM | 256 + log₂(4096) = 268 bits |
| Comparison: AES-256 key | 256 bits |
| NIST minimum for top secret | 192 bits |

**Recommendation**: `openssl rand -base64 32` (256 bits of entropy) is the recommended standard. Do NOT use shorter passwords. The 44-character base64 output is human-manageable in env files and Docker secrets.

### 5.4 Handling Passwords in Docker

```dockerfile
# docker-compose.yml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/db_root_password
    secrets:
      - db_root_password
    volumes:
      - ./init-scripts:/docker-entrypoint-initdb.d/

secrets:
  guinevere_core_password:
    file: ./secrets/guinevere_core.txt
  guinevere_readonly_password:
    file: ./secrets/guinevere_readonly.txt
```

---

## 6. Schema Creation Ordering

### 6.1 Correct Order

```sql
-- ========== ORDER MATTERS ==========

-- Step 1: Create roles first (no dependency on schemas)
CREATE USER guinevere_core WITH LOGIN PASSWORD '...' INHERIT;
CREATE USER guinevere_surveillance WITH LOGIN PASSWORD '...' INHERIT;
CREATE USER guinevere_scheduler WITH LOGIN PASSWORD '...' INHERIT;
CREATE USER guinevere_readonly WITH LOGIN PASSWORD '...' INHERIT;
CREATE USER guinevere_backup WITH LOGIN PASSWORD '...' INHERIT;

-- Step 2: Lock down database-level PUBLIC access
REVOKE ALL ON DATABASE guinevere FROM PUBLIC;
GRANT CONNECT ON DATABASE guinevere TO guinevere_core, guinevere_surveillance,
                                     guinevere_scheduler, guinevere_readonly,
                                     guinevere_backup;

-- Step 3: Create schemas (ALTER DEFAULT PRIVILEGES needs them to exist)
CREATE SCHEMA IF NOT EXISTS memory;
CREATE SCHEMA IF NOT EXISTS persona;
CREATE SCHEMA IF NOT EXISTS surveillance;
CREATE SCHEMA IF NOT EXISTS loops;
CREATE SCHEMA IF NOT EXISTS financial;
CREATE SCHEMA IF NOT EXISTS config;
CREATE SCHEMA IF NOT EXISTS audit;

-- Step 4: Grant USAGE on schemas (required before any object access)
GRANT USAGE ON SCHEMA memory, persona, financial, config, audit TO guinevere_core;
GRANT USAGE ON SCHEMA surveillance TO guinevere_surveillance;
GRANT USAGE ON SCHEMA loops TO guinevere_scheduler;
-- ... etc.

-- Step 5: Grant on EXISTING objects (if any exist)
-- (none yet at init time, but needed after migrations create objects)

-- Step 6: Set ALTER DEFAULT PRIVILEGES for FUTURE objects
ALTER DEFAULT PRIVILEGES FOR ROLE guinevere_core IN SCHEMA memory
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO guinevere_core;
ALTER DEFAULT PRIVILEGES FOR ROLE guinevere_core IN SCHEMA memory
    GRANT SELECT ON TABLES TO guinevere_readonly;
-- ... etc. for each creator-role × schema × recipient combination
```

### 6.2 Why This Order?

1. **Roles before schemas**: Roles have no dependency on schemas. Creating them first is clean.
2. **Database lockdown before schema grants**: You want to revoke PUBLIC before adding specific grants.
3. **Schemas before `ALTER DEFAULT PRIVILEGES IN SCHEMA`**: The schema must exist for the `IN SCHEMA` clause.
4. **`ALTER DEFAULT PRIVILEGES` before object creation**: Default privileges only affect objects created AFTER the `ALTER` command.

### 6.3 Critical: Who Creates Objects?

`ALTER DEFAULT PRIVILEGES` must specify `FOR ROLE <creator>` — the role that will execute `CREATE TABLE`. If your migrations run as `guinevere_core`, that's the role to use in `FOR ROLE`. If they run as `postgres`, use `FOR ROLE postgres`.

For Docker PostgreSQL 16 init scripts, the default user is `postgres` (the `POSTGRES_USER`). Adjust `FOR ROLE` accordingly.

```sql
-- If init scripts run as 'postgres' (Docker default):
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA memory
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO guinevere_core;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA memory
    GRANT SELECT ON TABLES TO guinevere_readonly;

-- After migration, if app code running as guinevere_core creates tables:
ALTER DEFAULT PRIVILEGES FOR ROLE guinevere_core IN SCHEMA memory
    GRANT SELECT ON TABLES TO guinevere_readonly;
```

---

## 7. Least Privilege Patterns per Service Role

### 7.1 guinevere_core (Full CRUD on memory, persona, financial, config, audit)

Core application service. Needs full read/write on 5 schemas.

```sql
-- Schemas: memory, persona, financial, config, audit
DO $$
DECLARE
    schema_name text;
    schemas text[] := ARRAY['memory', 'persona', 'financial', 'config', 'audit'];
BEGIN
    FOREACH schema_name IN ARRAY schemas
    LOOP
        EXECUTE format('GRANT USAGE, CREATE ON SCHEMA %I TO guinevere_core', schema_name);
        EXECUTE format('GRANT ALL ON ALL TABLES IN SCHEMA %I TO guinevere_core', schema_name);
        EXECUTE format('GRANT ALL ON ALL SEQUENCES IN SCHEMA %I TO guinevere_core', schema_name);
        EXECUTE format('GRANT ALL ON ALL FUNCTIONS IN SCHEMA %I TO guinevere_core', schema_name);

        -- Future objects (created by postgres or guinevere_core)
        EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA %I
            GRANT ALL ON TABLES TO guinevere_core', schema_name);
        EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA %I
            GRANT ALL ON SEQUENCES TO guinevere_core', schema_name);
        EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA %I
            GRANT ALL ON FUNCTIONS TO guinevere_core', schema_name);
    END LOOP;
END $$;
```

### 7.2 guinevere_surveillance (INSERT only on surveillance schema)

Surveillance data ingestion — write-only, no read, no update, no delete.

```sql
-- Schema: surveillance
GRANT USAGE ON SCHEMA surveillance TO guinevere_surveillance;

-- Existing objects: INSERT only (no SELECT, UPDATE, DELETE)
GRANT INSERT ON ALL TABLES IN SCHEMA surveillance TO guinevere_surveillance;

-- Sequences need USAGE (for SERIAL/BIGSERIAL columns)
GRANT USAGE ON ALL SEQUENCES IN SCHEMA surveillance TO guinevere_surveillance;

-- Future objects: INSERT on tables, USAGE on sequences
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA surveillance
    GRANT INSERT ON TABLES TO guinevere_surveillance;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA surveillance
    GRANT USAGE ON SEQUENCES TO guinevere_surveillance;

-- EXPLICITLY deny everything else on existing objects
REVOKE SELECT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
    ON ALL TABLES IN SCHEMA surveillance FROM guinevere_surveillance;
```

### 7.3 guinevere_scheduler (CRUD on loops, scheduler schemas)

CRUD on scheduled tasks and loop management.

```sql
-- Schemas: loops, scheduler (if separate)
GRANT USAGE, CREATE ON SCHEMA loops TO guinevere_scheduler;
GRANT ALL ON ALL TABLES IN SCHEMA loops TO guinevere_scheduler;
GRANT ALL ON ALL SEQUENCES IN SCHEMA loops TO guinevere_scheduler;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA loops
    GRANT ALL ON TABLES TO guinevere_scheduler;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA loops
    GRANT ALL ON SEQUENCES TO guinevere_scheduler;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA loops
    GRANT ALL ON FUNCTIONS TO guinevere_scheduler;
```

### 7.4 guinevere_readonly (SELECT all schemas — for Grafana)

Grafana dashboard read-only user — needs SELECT across all schemas plus pg_monitor for metrics.

```sql
-- Option A: pg_read_all_data (simpler, PostgreSQL 15+)
-- Gives SELECT on all tables + USAGE on all schemas automatically
GRANT pg_read_all_data TO guinevere_readonly;

-- Also grant monitoring role for Grafana metrics
GRANT pg_monitor TO guinevere_readonly;

-- Option B: Per-schema granular (choose this if you want strict control)
DO $$
DECLARE
    schema_name text;
    schemas text[] := ARRAY['memory', 'persona', 'surveillance', 'loops', 'financial', 'config', 'audit'];
BEGIN
    FOREACH schema_name IN ARRAY schemas
    LOOP
        EXECUTE format('GRANT USAGE ON SCHEMA %I TO guinevere_readonly', schema_name);
        EXECUTE format('GRANT SELECT ON ALL TABLES IN SCHEMA %I TO guinevere_readonly', schema_name);
        EXECUTE format('GRANT SELECT ON ALL SEQUENCES IN SCHEMA %I TO guinevere_readonly', schema_name);

        -- Future objects (for each possible creator)
        EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA %I
            GRANT SELECT ON TABLES TO guinevere_readonly', schema_name);
        EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA %I
            GRANT SELECT ON SEQUENCES TO guinevere_readonly', schema_name);

        -- If guinevere_core also creates objects
        EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE guinevere_core IN SCHEMA %I
            GRANT SELECT ON TABLES TO guinevere_readonly', schema_name);
        EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE guinevere_core IN SCHEMA %I
            GRANT SELECT ON SEQUENCES TO guinevere_readonly', schema_name);
    END LOOP;
END $$;
```

**Trade-off**: `pg_read_all_data` is simpler but grants access to ALL schemas including system schemas. Per-schema SELECT is stricter. For Grafana dashboards limited to app data, per-schema is recommended; if Grafana also monitors system metrics, add `pg_monitor` separately.

**Source**: [PostgreSQL 16 Predefined Roles docs](https://www.postgresql.org/docs/16/predefined-roles.html)

### 7.5 guinevere_backup (pg_read_all_data + pg_dump)

Backup user — needs full read access for `pg_dump`.

```sql
-- pg_read_all_data gives SELECT on all tables + USAGE on all schemas
-- This is sufficient for pg_dump (non-exclusive, non-superuser backups)
GRANT pg_read_all_data TO guinevere_backup;

-- Backup doesn't need CONNECT to a specific database
-- pg_dump handles connection per-database
GRANT CONNECT ON DATABASE guinevere TO guinevere_backup;

-- If using pg_dump --no-owner or custom format:
-- pg_read_all_data is sufficient since PostgreSQL 15+

-- For pg_basebackup (physical backup), superuser or replication role is needed
-- This is NOT needed for logical backup (pg_dump)
```

**Key**: `pg_read_all_data` (introduced in PostgreSQL 15) allows `pg_dump` to export all data without superuser. No need for per-schema grants.

**Source**: [Cybertec: pg_read_all_data allows unfettered pg_dump](https://www.cybertec-postgresql.com/en/finally-a-system-level-read-all-data-role-for-postgresql/)

---

## 8. Complete Execution Order

```sql
-- ============================================================
-- EXECUTION ORDER FOR GUINEVERE POSTGRESQL 16 SETUP
-- ============================================================

-- 0. PRE-FLIGHT: Set password encryption
--    (already default in PostgreSQL 16 Docker image)

-- 1. CREATE ROLES (LOGIN users)
CREATE USER guinevere_core WITH LOGIN PASSWORD '...' INHERIT;
CREATE USER guinevere_surveillance WITH LOGIN PASSWORD '...' INHERIT;
CREATE USER guinevere_scheduler WITH LOGIN PASSWORD '...' INHERIT;
CREATE USER guinevere_readonly WITH LOGIN PASSWORD '...' INHERIT;
CREATE USER guinevere_backup WITH LOGIN PASSWORD '...' INHERIT;

-- 2. LOCKDOWN DATABASE
REVOKE ALL ON DATABASE guinevere FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
ALTER DEFAULT PRIVILEGES REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;

-- 3. GRANT CONNECT (selectively)
GRANT CONNECT ON DATABASE guinevere TO guinevere_core, guinevere_surveillance,
    guinevere_scheduler, guinevere_readonly, guinevere_backup;

-- 4. CREATE SCHEMAS
CREATE SCHEMA IF NOT EXISTS memory;
CREATE SCHEMA IF NOT EXISTS persona;
CREATE SCHEMA IF NOT EXISTS surveillance;
CREATE SCHEMA IF NOT EXISTS loops;
CREATE SCHEMA IF NOT EXISTS financial;
CREATE SCHEMA IF NOT EXISTS config;
CREATE SCHEMA IF NOT EXISTS audit;

-- 5. GRANT USAGE ON SCHEMAS (per service)
GRANT USAGE ON SCHEMA memory, persona, financial, config, audit TO guinevere_core;
GRANT USAGE ON SCHEMA surveillance TO guinevere_surveillance;
GRANT USAGE ON SCHEMA loops TO guinevere_scheduler;
-- guinevere_readonly: per-schema USAGE (or via pg_read_all_data)
-- guinevere_backup: via pg_read_all_data

-- 6. GRANT ON EXISTING OBJECTS (none yet, placeholder for post-migration)

-- 7. SET DEFAULT PRIVILEGES (per creator × schema × recipient)
-- (See section 7 for per-role details)

-- 8. GRANT PREDEFINED ROLES (for readonly and backup)
GRANT pg_monitor TO guinevere_readonly;
GRANT pg_read_all_data TO guinevere_backup;

-- 9. VERIFY
-- \du  -- list roles
-- \dn+ -- list schemas with privileges
-- \ddp -- show default privileges
-- SELECT * FROM information_schema.role_table_grants WHERE grantee = 'guinevere_core';
```

---

## 9. Key Traps and Pitfalls

### Trap 1: `FOR ROLE` is the Creator, Not the Recipient

```sql
-- ❌ WRONG: "I want future tables to be accessible by guinevere_readonly"
ALTER DEFAULT PRIVILEGES IN SCHEMA memory GRANT SELECT ON TABLES TO guinevere_readonly;
-- This only works if the CURRENT role creating the ALTER is also the role creating tables

-- ✅ CORRECT: Specify who creates the objects
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA memory GRANT SELECT ON TABLES TO guinevere_readonly;
ALTER DEFAULT PRIVILEGES FOR ROLE guinevere_core IN SCHEMA memory GRANT SELECT ON TABLES TO guinevere_readonly;
```

### Trap 2: Per-Schema REVOKE Cannot Override Global Grants

```sql
-- DEFAULT: PUBLIC gets EXECUTE on all functions
-- ❌ This does NOTHING:
ALTER DEFAULT PRIVILEGES IN SCHEMA memory REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
-- ✅ This works (global scope):
ALTER DEFAULT PRIVILEGES REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
```

### Trap 3: Default Privileges Don't Apply Retroactively

```sql
ALTER DEFAULT PRIVILEGES ... GRANT SELECT ON TABLES TO guinevere_readonly;
-- Only affects tables created AFTER this statement.
-- Existing tables need explicit GRANT.
```

### Trap 4: `ALL TABLES IN SCHEMA` Does Not Cover Sequences or Functions

```sql
-- ❌ Incomplete: sequences and functions are missed
GRANT ALL ON ALL TABLES IN SCHEMA memory TO guinevere_core;

-- ✅ Must also grant on sequences and functions
GRANT ALL ON ALL TABLES IN SCHEMA memory TO guinevere_core;
GRANT ALL ON ALL SEQUENCES IN SCHEMA memory TO guinevere_core;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA memory TO guinevere_core;
```

### Trap 5: `pg_read_all_data` Does NOT Bypass Row-Level Security

From [PostgreSQL 16 Predefined Roles](https://www.postgresql.org/docs/16/predefined-roles.html):

> "This role does not have the role attribute `BYPASSRLS` set. If RLS is being used, an administrator may wish to set `BYPASSRLS` on roles which this role is GRANTed to."

If you use Row-Level Security and want `guinevere_readonly` or `guinevere_backup` to bypass RLS, grant `BYPASSRLS`:

```sql
ALTER ROLE guinevere_backup BYPASSRLS;
ALTER ROLE guinevere_readonly BYPASSRLS;  -- only if Grafana needs to bypass RLS
```

### Trap 6: `ALTER DEFAULT PRIVILEGES` Persists After Role Drop

If you drop a role that has default privileges set, you'll get errors. Use `DROP OWNED BY role_name` first, or reverse the default privileges before dropping.

---

## 10. References

### Official PostgreSQL 16 Documentation

| Topic | URL |
|---|---|
| ALTER DEFAULT PRIVILEGES | https://www.postgresql.org/docs/16/sql-alterdefaultprivileges.html |
| GRANT | https://www.postgresql.org/docs/16/sql-grant.html |
| REVOKE | https://www.postgresql.org/docs/16/sql-revoke.html |
| CREATE ROLE | https://www.postgresql.org/docs/16/sql-createrole.html |
| Privileges (Section 5.7) | https://www.postgresql.org/docs/16/ddl-priv.html |
| Role Membership (Section 22.3) | https://www.postgresql.org/docs/16/role-membership.html |
| Predefined Roles (Section 22.5) | https://www.postgresql.org/docs/16/predefined-roles.html |
| Password Authentication (Section 21.5) | https://www.postgresql.org/docs/16/auth-password.html |

### Production Code References (GitHub)

| Codebase | Pattern | Source |
|---|---|---|
| Supabase | `NOLOGIN NOINHERIT` group roles + `ALTER DEFAULT PRIVILEGES` per schema | [supabase/postgres](https://github.com/supabase/postgres/blob/develop/migrations/db/init-scripts/00000000000000-initial-schema.sql) |
| Supabase realtime | `ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL` | [supabase/realtime](https://github.com/supabase/realtime/blob/main/dev/postgres/zz-supabase-schema.sql) |
| Cube.js | `ALTER DEFAULT PRIVILEGES FOR ROLE test IN SCHEMA public GRANT SELECT ON TABLES TO test_readonly` | [cube-js/cube](https://github.com/cube-js/cube/blob/master/packages/cubejs-testing-drivers/fixtures/postgresql-init.sql) |
| Encore | `GRANT pg_read_all_data` pattern for service roles | [encoredev/encore](https://github.com/encoredev/encore/blob/main/cli/daemon/sqldb/cluster.go) |
| Steampipe | `REVOKE ALL ON DATABASE FROM PUBLIC` lockdown | [turbot/steampipe](https://github.com/turbot/steampipe/blob/develop/pkg/db/db_local/install.go) |
| Graphile | `REVOKE ALL ON DATABASE + GRANT CONNECT` pattern | [graphile/starter](https://github.com/graphile/starter/blob/main/heroku-setup.template) |
| Polar | `REVOKE ALL ON DATABASE FROM PUBLIC` + init scripts | [polarsource/polar](https://github.com/polarsource/polar/blob/main/server/init-readonly-user.sql) |
| DefiLlama | `REVOKE CREATE ON SCHEMA public FROM PUBLIC` | [DefiLlama/yield-server](https://github.com/DefiLlama/yield-server/blob/master/migrations/1662753238454_add-roles.js) |

---

## Appendix: Verification Queries

After applying the privilege setup, verify with:

```sql
-- List all roles with attributes
\du

-- List all schemas with access privileges
\dn+

-- Show default privileges (ddp = describe default privileges)
\ddp

-- Check specific role's privileges on schemas
SELECT nspname AS schema,
       coalesce(nullif(array_to_string(nspacl, ', '), ''), '(none)') AS privileges
FROM pg_catalog.pg_namespace
WHERE nspname NOT LIKE 'pg_%' AND nspname <> 'information_schema'
ORDER BY nspname;

-- Check a specific role's table-level privileges
SELECT table_schema, table_name, privilege_type
FROM information_schema.role_table_grants
WHERE grantee = 'guinevere_core'
ORDER BY table_schema, table_name;

-- Check default privileges (pg_default_acl)
SELECT pg_catalog.pg_get_userbyid(defacluser) AS owner,
       defaclnamespace::regnamespace AS schema,
       CASE defaclobjtype
           WHEN 'r' THEN 'TABLES'
           WHEN 'S' THEN 'SEQUENCES'
           WHEN 'f' THEN 'FUNCTIONS'
           WHEN 'T' THEN 'TYPES'
           WHEN 'n' THEN 'SCHEMAS'
       END AS object_type,
       defaclacl AS acl
FROM pg_catalog.pg_default_acl
ORDER BY defacluser, defaclnamespace;

-- Test connection as a specific user (psql)
-- psql -h localhost -U guinevere_readonly -d guinevere -c "SELECT current_user;"
-- psql -h localhost -U guinevere_surveillance -d guinevere -c "INSERT INTO surveillance.test VALUES (1);"
```

---

*End of research report. Ready for downstream SQL implementation.*