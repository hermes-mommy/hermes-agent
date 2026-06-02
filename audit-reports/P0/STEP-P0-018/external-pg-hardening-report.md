# PostgreSQL 16 Hardening — Production Defense-in-Depth Report

**Scope**: PostgreSQL 16 running in Docker container (`postgres:16-trixie`) on `guinevere-net`  
**ADR alignment**: ADR-018 (defense-in-depth), ADR-027 (self-hosted)  
**Date**: 2026-05-31  
**Author**: Guinevere (Librarian)

---

## Table of Contents

1. [pg_hba.conf — Production Best Practices](#1-pg_hbaconf--production-best-practices)
2. [Connection Limits per User Role](#2-connection-limits-per-user-role)
3. [Audit Logging Configuration](#3-audit-logging-configuration)
4. [password_encryption — scram-sha-256](#4-password_encryption--scram-sha-256)
5. [SSL Inside Docker PostgreSQL — Feasibility Analysis](#5-ssl-inside-docker-postgresql--feasibility-analysis)
6. [PostgreSQL 16 Specific Hardening Settings](#6-postgresql-16-specific-hardening-settings)
7. [pg_hba.conf Reload Methods](#7-pg_hbaconf-reload-methods)
8. [Complete Recommended Configuration](#8-complete-recommended-configuration)
9. [Docker-Specific Deployment Notes](#9-docker-specific-deployment-notes)
10. [References](#10-references)

---

## 1. pg_hba.conf — Production Best Practices

### 1.1 Golden Rules

| Rule | Rationale | Source |
|---|---|---|
| **No `trust` anywhere** | Trust authentication provides zero identity verification. Any connection claiming a username is accepted. | CIS PG 16 Benchmark, StackHarden |
| **No `md5` for new deployments** | MD5 password hash is vulnerable to offline brute-force if leaked. SCRAM-SHA-256 uses salted iterative hashing (RFC 7677). | [PG Docs - Password Authentication](https://www.postgresql.org/docs/16/auth-password.html) |
| **No `password` (cleartext)** | Sends password in plaintext over the wire. Only acceptable over SSL, but `scram-sha-256` is still preferred. | [PG Docs - auth-methods](https://www.postgresql.org/docs/16/auth-methods.html) |
| **Use `hostssl` for all remote rules** | `host` accepts both SSL and non-SSL connections. Only `hostssl` enforces encryption. If SSL is not enabled server-side, `hostssl` records are ignored with a warning. | [PG Docs - pg_hba.conf](https://www.postgresql.org/docs/16/auth-pg-hba-conf.html) |
| **`reject` catch-all as last rule** | Ensures any connection not matching prior rules is explicitly denied, not silently allowed. | [PG Docs - auth-pg-hba-conf](https://postgrespro.com/docs/postgresql/16/auth-pg-hba-conf.html) |
| **Local socket for admin only** | Use `peer` for local Unix socket connections (inside Docker `docker exec`). This maps OS user to DB user without password. | StackHarden guide |

### 1.2 Recommended pg_hba.conf Structure

```postgresql
#==============================================================================
# PostgreSQL Client Authentication Configuration File
# Production — SCRAM-SHA-256 only, SSL-enforced, zero trust
# Location: /var/lib/postgresql/data/pg_hba.conf
#==============================================================================

# TYPE    DATABASE    USER              ADDRESS          METHOD

# --- Local Unix Socket (admin via docker exec) ---
local    all         postgres                            peer
local    all         all                                 scram-sha-256

# --- Loopback TCP (localhost) ---
host     all         all              127.0.0.1/32       scram-sha-256
host     all         all              ::1/128            scram-sha-256

# --- Docker Network (guinevere-net) — SSL required ---
# Core application services
hostssl  guinevere   core_user        172.16.0.0/24      scram-sha-256

# Surveillance pipeline
hostssl  guinevere   surveillance_user 172.16.0.0/24     scram-sha-256

# Scheduler / cron
hostssl  guinevere   scheduler_user   172.16.0.0/24      scram-sha-256

# Read-only analytics
hostssl  guinevere   readonly_user    172.16.0.0/24      scram-sha-256

# Backup (separate container or host)
hostssl  guinevere   backup_user      172.16.1.0/24      scram-sha-256

# --- Management / Admin IP (limited) ---
hostssl  all         postgres         10.0.0.5/32        scram-sha-256

# --- Catch-all: REJECT everything else ---
hostssl  all         all              0.0.0.0/0          reject
host     all         all              0.0.0.0/0          reject
```

**Key design decisions**:
- Local socket uses `peer` only for `postgres` superuser (admin access via `docker exec`). All other local users must authenticate via `scram-sha-256`.
- All TCP rules after loopback use `hostssl` — non-SSL connections are refused.
- Docker network CIDR `172.16.0.0/24` assumes default Docker bridge network. **Replace with actual `guinevere-net` subnet.**
- Backup subnet `172.16.1.0/24` assumes isolated backup network segment.
- Catch-all reject lines at the bottom — one for `hostssl` and one for `host` — to prevent any unencrypted fallback.

### 1.3 Production Examples from Open Source

The [StackHarden PG Hardening Guide](https://stackharden.com/guides/postgresql-hardening/) (2026) recommends:

```postgresql
# TYPE   DATABASE   USER          ADDRESS         METHOD
local    all        postgres                      peer
local    all        all                           scram-sha-256
host     all        all           127.0.0.1/32    scram-sha-256
host     all        all           ::1/128         scram-sha-256
hostssl  appdb      appuser       10.0.0.0/24     scram-sha-256
```

The [ppradela/postgres16-ol8-stig](https://github.com/ppradela/postgres16-ol8-stig) (2026) project uses:
- `hostssl` + SCRAM-SHA-256 for all remote connections
- Plain TCP connections rejected entirely
- Local socket uses peer auth only

**Source evidence**: ([StackHarden](https://stackharden.com/guides/postgresql-hardening/)), ([ppradela STIG repo](https://github.com/ppradela/postgres16-ol8-stig))

---

## 2. Connection Limits per User Role

### 2.1 PostgreSQL 16 Syntax

Connection limits are set via `ALTER ROLE ... CONNECTION LIMIT N` (or `ALTER USER`, which is an alias).

```sql
ALTER ROLE role_name CONNECTION LIMIT N;
```

- `N >= 0`: Maximum concurrent connections for this role
- `-1` or `UNLIMITED`: No limit (default)
- Superusers are **not** subject to connection limits — a superuser can always connect even if the limit is reached

**Source**: ([PG Docs - ALTER ROLE](https://www.postgresql.org/docs/16/sql-alterrole.html))

### 2.2 Recommended Connection Limits for Guinevere

| Role | Limit | Rationale |
|---|---|---|
| `postgres` (superuser) | `UNLIMITED` (cannot be limited) | Reserved for admin |
| `core_user` | **30** | Primary AI companion connections, allows connection pool overhead |
| `surveillance_user` | **10** | Surveillance pipeline — burst-y but bounded |
| `scheduler_user` | **10** | Cron/scheduled tasks, parallel job execution |
| `readonly_user` | **15** | Analytics, reporting, dashboard queries |
| `backup_user` | **5** | pg_dump / pgBackRest connections |

### 2.3 SQL to Apply

```sql
-- Core application (30 concurrent)
ALTER ROLE core_user CONNECTION LIMIT 30;

-- Surveillance pipeline (10 concurrent)
ALTER ROLE surveillance_user CONNECTION LIMIT 10;

-- Scheduler / cron (10 concurrent)
ALTER ROLE scheduler_user CONNECTION LIMIT 10;

-- Read-only analytics (15 concurrent)
ALTER ROLE readonly_user CONNECTION LIMIT 15;

-- Backup operations (5 concurrent)
ALTER ROLE backup_user CONNECTION LIMIT 5;

-- Verify all limits
SELECT rolname, rolconnlimit
FROM pg_roles
WHERE rolname IN ('core_user', 'surveillance_user', 'scheduler_user', 'readonly_user', 'backup_user');
```

### 2.4 Important Caveat

Connection limits are **per-role**, not per-pool. If using PgBouncer or another connection pooler between app and PostgreSQL, the pooler's connections count against the limit — not the original client connections. Account for pooler overhead when setting these values.

---

## 3. Audit Logging Configuration

### 3.1 Core Audit Parameters (PostgreSQL 16)

| Parameter | Recommended Value | Effect |
|---|---|---|
| `log_connections` | `on` | Logs every connection attempt + successful auth + authorization |
| `log_disconnections` | `on` | Logs session termination with duration |
| `log_statement` | `ddl` | Logs all DDL statements (CREATE, ALTER, DROP). Avoids logging data values |
| `log_line_prefix` | `'%m [%p] %q%u@%d/%a '` | Timestamp, PID, user@database/app for correlation |
| `log_min_duration_statement` | `500` (ms) | Logs slow queries ≥500ms with full SQL text |
| `log_timezone` | `'UTC'` | Consistent timestamps across logs |
| `logging_collector` | `on` | Enables PostgreSQL's built-in log rotation |

### 3.2 Parameter Documentation

**`log_connections`** ([PG Docs](https://www.postgresql.org/docs/16/runtime-config-logging.html)):
> Causes each attempted connection to the server to be logged, as well as successful completion of both client authentication (if necessary) and authorization.

**`log_disconnections`** ([PG Docs](https://www.postgresql.org/docs/16/runtime-config-logging.html)):
> Causes session terminations to be logged. The log output provides information similar to log_connections, plus the duration of the session.

**`log_statement`** ([PG Docs](https://www.postgresql.org/docs/16/runtime-config-logging.html)):
> Controls which SQL statements are logged. Valid values: `none` (off), `ddl`, `mod`, `all`.

**`log_line_prefix`** escape sequences:

| Escape | Meaning |
|---|---|
| `%m` | Timestamp with milliseconds |
| `%p` | Process ID (PID) |
| `%q` | Suppress prefix in non-session processes |
| `%u` | Database user name |
| `%d` | Database name |
| `%a` | Application name |
| `%r` | Remote host and port |
| `%c` | Session ID for correlation |

**`log_min_duration_statement`** ([PG Docs](https://www.postgresql.org/docs/16/runtime-config-logging.html)):
> Causes the duration of each completed statement to be logged if the statement ran for at least the specified amount of time. If this value is specified without units, it is taken as milliseconds. Setting this to zero prints all statement durations. `-1` (the default) disables logging statement durations.

### 3.3 CIS Benchmark Alignment

CIS PostgreSQL 16 Benchmark v1.0.0 Level 1 prescribes:

| CIS Item | Setting | Required |
|---|---|---|
| 3.1.20 | `log_connections = on` | Level 1 |
| 3.1.21 | `log_disconnections = on` | Level 1 |
| 3.1.13 | `log_statement = 'ddl'` | Level 1 (minimum) |
| 3.1.2 | `log_line_prefix` with timestamp & user | Level 1 |

**Tenable/CIS evidence**: ([CIS PG 16 L1 - log_connections](https://www.tenable.com/audits/items/CIS_PostgreSQL_16_v1.0.0_L1_Database.audit:349a18cb4dcc8a41cacbc69f7e127e8d))

### 3.4 SQL to Apply

```sql
ALTER SYSTEM SET log_connections = 'on';
ALTER SYSTEM SET log_disconnections = 'on';
ALTER SYSTEM SET log_statement = 'ddl';
ALTER SYSTEM SET log_line_prefix = '%m [%p] %q%u@%d/%a ';
ALTER SYSTEM SET log_min_duration_statement = 500;
ALTER SYSTEM SET log_timezone = 'UTC';
ALTER SYSTEM SET logging_collector = 'on';

SELECT pg_reload_conf();
```

### 3.5 pgAudit Consideration

For deeper audit requirements (e.g., logging `SELECT` statements that access sensitive data), consider [pgAudit](https://access.crunchydata.com/documentation/pgaudit/16.0/) (v16.X for PG 16). pgAudit provides:

- Object-level audit logging (per-table SELECT/INSERT/UPDATE/DELETE)
- Session-level vs object-level audit
- More granular than `log_statement = 'all'`

However, pgAudit requires `CREATE EXTENSION` and a shared library loaded via `shared_preload_libraries`. This adds operational complexity. **Start with built-in logging; add pgAudit if audit requirements demand it.**

---

## 4. password_encryption — scram-sha-256

### 4.1 Default in PostgreSQL 16

In PostgreSQL 14+, the default `password_encryption` is already `'scram-sha-256'`. For PG 16, this is the default. Verify:

```sql
SHOW password_encryption;
-- Expected: scram-sha-256
```

### 4.2 If Not Set, Apply

```sql
ALTER SYSTEM SET password_encryption = 'scram-sha-256';
SELECT pg_reload_conf();
```

### 4.3 Existing Passwords

Changing `password_encryption` only affects **newly set passwords**. Existing password hashes stored as `md5` remain. To fully migrate:

1. Set `password_encryption = 'scram-sha-256'`
2. Have each user run `ALTER USER username PASSWORD 'new_password';` to re-hash
3. Verify in `pg_authid`:
   ```sql
   SELECT rolname, rolpassword
   FROM pg_authid
   WHERE rolpassword LIKE 'SCRAM-SHA-256%';
   ```

**Source**: ([PG Docs - Password Authentication](https://www.postgresql.org/docs/16/auth-password.html))

---

## 5. SSL Inside Docker PostgreSQL — Feasibility Analysis

### 5.1 Verdict: ✅ Fully Feasible — Recommended for Production

PostgreSQL's official Docker image ships with OpenSSL support compiled in. SSL is disabled by default but can be activated with minimal config changes.

### 5.2 What PostgreSQL 16 Supports in Docker

| Capability | Supported? | Notes |
|---|---|---|
| SSL/TLS 1.2+ | ✅ YES | `ssl_min_protocol_version = 'TLSv1.2'` |
| Self-signed certs | ✅ YES | Acceptable for internal Docker network |
| CA-signed certs (Let's Encrypt) | ✅ YES | For internet-exposed deployments |
| Certificate auth (`cert` method) | ✅ YES | Client SSL cert replaces password |
| `hostssl` enforcement | ✅ YES | Requires `ssl=on` or hostssl records are ignored |

**Source**: ([PG Docs - SSL/TCP](https://www.postgresql.org/docs/16/ssl-tcp.html))

### 5.3 Self-Signed Certificate Approach (Recommended for Guinevere)

Since all traffic stays within `guinevere-net` Docker bridge network, a self-signed CA is sufficient. Attack surface: limited to other containers on the same Docker network, which are already within trust boundary under ADR-027.

#### Step 1: Generate Certificates

```bash
# Create CA
openssl genrsa -out ca-key.pem 4096
openssl req -new -x509 -days 365 -nodes -text \
  -out ca-cert.pem -keyout ca-key.pem \
  -subj "/CN=guinevere-ca"

# Create server key and CSR
openssl genrsa -out server-key.pem 4096
openssl req -new -nodes -text \
  -out server.csr -keyout server.key \
  -subj "/CN=postgres.guinevere-net"

# Sign server cert with CA
openssl x509 -req -in server.csr -text -days 365 \
  -CA ca-cert.pem -CAkey ca-key.pem -CAcreateserial \
  -out server.crt

# Permissions
chmod 600 server.key
chmod 644 server.crt ca-cert.pem
```

#### Step 2: Mount Certs into Container

```bash
docker run -d \
  --name guinevere-db \
  --network guinevere-net \
  -v /path/to/certs:/etc/postgresql/certs:ro \
  -v pgdata:/var/lib/postgresql/data \
  -e POSTGRES_PASSWORD_FILE=/run/secrets/db_password \
  postgres:16-trixie \
  -c ssl=on \
  -c ssl_cert_file=/etc/postgresql/certs/server.crt \
  -c ssl_key_file=/etc/postgresql/certs/server.key \
  -c ssl_ca_file=/etc/postgresql/certs/ca-cert.pem \
  -c ssl_min_protocol_version=TLSv1.2
```

#### Step 3: Update pg_hba.conf to Use hostssl

The pg_hba.conf shown in [Section 1.2](#12-recommended-pg_hbaconf-structure) already uses `hostssl` for all remote rules.

#### Step 4: Client Connection with SSL

```bash
psql "host=guinevere-db port=5432 dbname=guinevere \
  user=core_user sslmode=verify-full \
  sslrootcert=/path/to/ca-cert.pem"
```

### 5.4 Docker SSL: Certificate Management Patterns

| Pattern | Description | Best For |
|---|---|---|
| **Volume mount** | Certs generated on host, mounted read-only into container | Simple, no custom image needed |
| **Self-contained image** | Custom Dockerfile that generates certs at build time | Reproducible builds |
| **Init container** | Sidecar that provisions certs before PG starts | Kubernetes / orchestrated |
| **Let's Encrypt** | Certbot automation, volume-mount renewed certs | Internet-exposed PG |

**Recommendation for Guinevere**: Volume mount pattern. Simplest with `postgres:16-trixie` stock image — no custom Dockerfile needed. Certs are stored on host and mounted as `:ro` (read-only).

**Source**: ([Redgate - Secure PG in Docker](https://www.red-gate.com/simple-talk/databases/postgresql/running-postgresql-in-docker-with-proper-ssl-and-configuration/)), ([Smallstep - PG TLS](https://smallstep.com/practical-zero-trust/postgresql-tls))

### 5.5 Key Security Notes

- `ssl_key_file` permissions inside container must be `600` and owned by `postgres` (UID 999)
- If `ssl=on` but SSL negotiation fails, `hostssl` rules are skipped — the connection is rejected
- `hostssl` records are **silently ignored** if SSL is not enabled — always verify with `\conninfo`
- Do not use `POSTGRES_HOST_AUTH_METHOD=trust` in production — it overrides pg_hba.conf with a trust entry
- Self-signed certs do not protect against MitM from within the Docker network if an attacker gains access to `guinevere-net` — for higher security, use an internal CA or mTLS

---

## 6. PostgreSQL 16 Specific Hardening Settings

### 6.1 Parameter Matrix

| Parameter | Recommended Value | Scope | PG16 Change | Documentation |
|---|---|---|---|---|
| `idle_in_transaction_session_timeout` | `10min` | Global (`postgresql.conf`) | Unchanged from PG14 | [PG Docs - Client Defaults](https://www.postgresql.org/docs/16/runtime-config-client.html) |
| `idle_session_timeout` | `2h` | Global or per-role | Available since PG14 | [PG Docs](https://www.postgresql.org/docs/16/runtime-config-client.html) |
| `statement_timeout` | **DO NOT SET GLOBALLY** | Per-role or per-session | Unchanged | [PG Docs](https://www.postgresql.org/docs/16/runtime-config-client.html) |
| `log_min_duration_statement` | `500ms` | Global | Unchanged | [PG Docs - Logging](https://www.postgresql.org/docs/16/runtime-config-logging.html) |
| `log_min_error_statement` | `error` | Global | Unchanged | CIS PG 16 v1.1.0 |
| `ssl_min_protocol_version` | `TLSv1.2` | Global | Unchanged | [PG Docs - SSL](https://www.postgresql.org/docs/16/ssl-tcp.html) |

### 6.2 idle_in_transaction_session_timeout

**Purpose**: Terminates sessions that remain idle inside an open transaction longer than the threshold.

**Why 10 minutes**: Long-running idle transactions:
- Hold locks preventing concurrent operations
- Prevent `VACUUM` from reclaiming dead tuples (transaction visibility)
- Contribute to table bloat
- Consume connection slots

```sql
ALTER SYSTEM SET idle_in_transaction_session_timeout = '10min';
```

**CIS alignment**: CIS PG 16 v1.0.0 recommends this be set to a value ≤ 15 minutes.

**Source**: ([PG Docs](https://www.postgresql.org/docs/16/runtime-config-client.html)):
> "This option can be used to ensure that idle sessions do not hold locks for an unreasonable amount of time."

### 6.3 idle_session_timeout (PG 14+)

**Purpose**: Terminates sessions that are idle but **not** in a transaction. Added in PG 14, available in PG 16.

**Why 2 hours**: Sessions without open transactions impose minimal server cost, but zombie connections still consume:
- Connection slots (against the connection limit)
- Memory for backend process
- Potential for resource leaks

```sql
ALTER SYSTEM SET idle_session_timeout = '2h';
```

**Per-role alternative** (safer for connection-pooled apps):
```sql
ALTER ROLE readonly_user SET idle_session_timeout TO '1h';
ALTER ROLE core_user SET idle_session_timeout TO '4h'; -- pooler connections
```

**Source**: ([PG Docs](https://www.postgresql.org/docs/16/runtime-config-client.html)):
> "Unlike the case with an open transaction, an idle session without a transaction imposes no large costs on the server."

**Caveat**: Be cautious with connection-pooled applications — the pooler's persistent connections will be terminated if idle too long, causing reconnect churn.

### 6.4 statement_timeout — Do NOT Set Globally

The PostgreSQL documentation explicitly warns:

> "Setting `statement_timeout` in `postgresql.conf` is not recommended because it would affect all sessions."

A global `statement_timeout` can kill:
- Long-running maintenance commands (`VACUUM`, `ANALYZE`)
- `pg_dump` / `pg_restore` operations
- Data migration scripts

**Instead, set per-role or per-database**:

```sql
-- Read-only users: prevent runaway analytics queries
ALTER ROLE readonly_user SET statement_timeout TO '5min';

-- Application user: generous timeout for AI workloads
ALTER ROLE core_user SET statement_timeout TO '2min';

-- Backup user: no timeout (VACUUM, pg_dump can be long)
ALTER ROLE backup_user SET statement_timeout TO 0;

-- Scheduler: moderate timeout
ALTER ROLE scheduler_user SET statement_timeout TO '1min';
```

**Source**: ([PG Docs - Client Defaults](https://www.postgresql.org/docs/16/runtime-config-client.html))

### 6.5 log_min_duration_statement — Recommended Value

| Environment | Recommended | Rationale |
|---|---|---|
| Development | `0` (all statements) | Catch all slow queries during dev |
| Staging | `250ms` | Tighter threshold for pre-prod |
| **Production (AI workload)** | **`500ms`** | Balances signal vs log volume |
| Production (high traffic) | `1000ms` | Too many false positives below 1s |

For an AI system where query latency matters, `500ms` catches queries that impact user experience without flooding logs.

---

## 7. pg_hba.conf Reload Methods

### 7.1 Methods Ranked by Safety

| Method | Command | Superuser Required? | Restart Required? | Safety |
|---|---|---|---|---|
| **pg_reload_conf()** | `SELECT pg_reload_conf();` | ✅ Superuser | ❌ No reload | Most safe — validates config before applying |
| **pg_ctl reload** | `pg_ctl reload` (via `docker exec`) | ✅ OS user `postgres` | ❌ No reload | Safe — sends SIGHUP |
| **kill -HUP** | `kill -HUP $(cat /var/lib/postgresql/data/postmaster.pid)` | ✅ Root in container | ❌ No reload | Direct, fragile if PID wrong |
| **Docker restart** | `docker restart guinevere-db` | ❌ Not required | ✅ Full restart | Blunt — brief downtime during restart |

### 7.2 Recommended Method: pg_reload_conf()

**Why**: Can be executed from any superuser DB session. Validates config changes before applying. If config has errors, the reload is rejected with an error message.

```sql
-- Step 1: Validate current pg_hba.conf rules
SELECT * FROM pg_hba_file_rules;

-- Step 2: Apply changes
SELECT pg_reload_conf();
-- Returns: t if signal sent successfully

-- Step 3: Verify no errors after reload
SELECT * FROM pg_hba_file_rules WHERE error IS NOT NULL;
```

**Source**: ([PG Docs - pg_reload_conf](https://www.postgresql.org/docs/16/functions-admin.html))

### 7.3 Docker-Specific Commands

```bash
# Method A: via psql inside container
docker exec -it guinevere-db psql -U postgres -c "SELECT pg_reload_conf();"

# Method B: via pg_ctl inside container
docker exec -it guinevere-db pg_ctl reload

# Method C: Docker restart (only if reload fails)
docker restart guinevere-db
```

### 7.4 What Changes Require Restart vs Reload

| Change | Method | Notes |
|---|---|---|
| `pg_hba.conf` edits | **Reload** | `pg_reload_conf()` or SIGHUP |
| `postgresql.conf` edits (most params) | **Reload** | Exceptions documented in PG docs |
| `ssl_cert_file` / `ssl_key_file` | **Reload** | SSL certs are re-read on SIGHUP |
| `listen_addresses` | **Restart** | Requires full restart |
| `shared_preload_libraries` | **Restart** | Must be set before startup |
| `password_encryption` | **Reload** | Affects only new passwords |
| `log_connections` / `log_disconnections` | **Reload** | Takes effect immediately |
| `log_statement` | **Reload** | New sessions see it immediately |
| Connection limits (`ALTER ROLE`) | **No reload needed** | Applied immediately via SQL |
| `statement_timeout` / `idle_*_timeout` | **Reload** or per-role | Per-role takes effect immediately |

---

## 8. Complete Recommended Configuration

### 8.1 ALTER SYSTEM Commands (Apply Once)

```sql
-- ============================================================
-- PostgreSQL 16 Hardening — Production Application
-- Execute as superuser, then pg_reload_conf()
-- ============================================================

-- Authentication
ALTER SYSTEM SET password_encryption = 'scram-sha-256';

-- Audit Logging
ALTER SYSTEM SET log_connections = 'on';
ALTER SYSTEM SET log_disconnections = 'on';
ALTER SYSTEM SET log_statement = 'ddl';
ALTER SYSTEM SET log_line_prefix = '%m [%p] %q%u@%d/%a ';
ALTER SYSTEM SET log_min_duration_statement = 500;
ALTER SYSTEM SET log_timezone = 'UTC';
ALTER SYSTEM SET logging_collector = 'on';

-- Timeouts (global)
ALTER SYSTEM SET idle_in_transaction_session_timeout = '10min';
ALTER SYSTEM SET idle_session_timeout = '2h';

-- SSL
ALTER SYSTEM SET ssl = 'on';
ALTER SYSTEM SET ssl_cert_file = '/etc/postgresql/certs/server.crt';
ALTER SYSTEM SET ssl_key_file = '/etc/postgresql/certs/server.key';
ALTER SYSTEM SET ssl_ca_file = '/etc/postgresql/certs/ca-cert.pem';
ALTER SYSTEM SET ssl_min_protocol_version = 'TLSv1.2';
ALTER SYSTEM SET ssl_prefer_server_ciphers = 'on';

-- Apply
SELECT pg_reload_conf();
```

### 8.2 Per-Role Configuration (Apply Once)

```sql
-- Connection limits
ALTER ROLE core_user CONNECTION LIMIT 30;
ALTER ROLE surveillance_user CONNECTION LIMIT 10;
ALTER ROLE scheduler_user CONNECTION LIMIT 10;
ALTER ROLE readonly_user CONNECTION LIMIT 15;
ALTER ROLE backup_user CONNECTION LIMIT 5;

-- Per-role statement timeouts (NOT global)
ALTER ROLE core_user SET statement_timeout TO '2min';
ALTER ROLE surveillance_user SET statement_timeout TO '5min';
ALTER ROLE scheduler_user SET statement_timeout TO '1min';
ALTER ROLE readonly_user SET statement_timeout TO '5min';
ALTER ROLE backup_user SET statement_timeout TO 0;       -- unlimited
ALTER ROLE postgres SET statement_timeout TO 0;           -- superuser: unlimited
```

### 8.3 pg_hba.conf (Full Production Template)

See [Section 1.2](#12-recommended-pg_hbaconf-structure) above. The template uses:
- `peer` for local superuser
- `scram-sha-256` for all password-based auth
- `hostssl` for all Docker network rules
- `reject` catch-all at the bottom
- Role-specific database access per user

---

## 9. Docker-Specific Deployment Notes

### 9.1 pg_hba.conf Location in postgres:16-trixie

| Item | Path |
|---|---|
| PGDATA | `/var/lib/postgresql/data` |
| pg_hba.conf | `/var/lib/postgresql/data/pg_hba.conf` |
| postgresql.conf | `/var/lib/postgresql/data/postgresql.conf` |
| postmaster.pid | `/var/lib/postgresql/data/postmaster.pid` |

The `postgres:16-trixie` image uses the default PGDATA at `/var/lib/postgresql/data`. The `pg_hba.conf` is initialized by `initdb` during first container start. **Do not edit before first run** — let `initdb` create it, then overlay.

### 9.2 Deployment Strategy

**Option A: Mount custom pg_hba.conf (Recommended)**

```bash
# 1. Start container first run to initialize data
docker run -d --name guinevere-db-init \
  --network guinevere-net \
  -v pgdata:/var/lib/postgresql/data \
  -e POSTGRES_PASSWORD_FILE=/run/secrets/db_password \
  postgres:16-trixie

# 2. Stop, replace pg_hba.conf, restart
docker stop guinevere-db-init
# Copy hardened pg_hba.conf into the volume
# Start with config overrides
docker run -d --name guinevere-db \
  --network guinevere-net \
  -v pgdata:/var/lib/postgresql/data \
  -v /host/path/certs:/etc/postgresql/certs:ro \
  -v /host/path/pg_hba.conf:/var/lib/postgresql/data/pg_hba.conf \
  -e POSTGRES_PASSWORD_FILE=/run/secrets/db_password \
  postgres:16-trixie \
  -c ssl=on \
  -c ssl_cert_file=/etc/postgresql/certs/server.crt \
  -c ssl_key_file=/etc/postgresql/certs/server.key \
  -c ssl_ca_file=/etc/postgresql/certs/ca-cert.pem \
  -c ssl_min_protocol_version=TLSv1.2
```

**Option B: Edit inside running container (ad-hoc)**

```bash
# Copy hardened pg_hba.conf into container
docker cp pg_hba.conf guinevere-db:/var/lib/postgresql/data/pg_hba.conf

# Reload
docker exec -it guinevere-db psql -U postgres -c "SELECT pg_reload_conf();"

# Verify
docker exec -it guinevere-db psql -U postgres -c "SELECT * FROM pg_hba_file_rules;"
```

### 9.3 Important Docker Config Notes

1. **`POSTGRES_HOST_AUTH_METHOD=trust` is dangerous** — It adds a `trust` entry to pg_hba.conf during initialization, which overrides your hardened config. Never use this in production.

2. **Environment variable passwords** (`POSTGRES_PASSWORD`) appear in `docker inspect` and container history. Use `POSTGRES_PASSWORD_FILE` with Docker secrets instead.

3. **`listen_addresses`**: Default in Docker image is `'*'` (due to the default `postgresql.conf` shipped with the image). **Harden this** either by:
   - Setting `-c listen_addresses=172.16.0.x` (container's specific IP)
   - Or accepting `'*'` but relying on `pg_hba.conf` rules to restrict access + Docker network isolation

4. **Restart policy**: On `docker restart`, pg_hba.conf and postgresql.conf are re-read automatically. No explicit reload needed after container restart.

5. **Volume permissions**: The `pgdata` volume must be owned by UID `999` (postgres inside container). If pre-creating the volume directory on the host:
   ```bash
   mkdir -p /docker/volumes/pgdata
   sudo chown 999:999 /docker/volumes/pgdata
   sudo chmod 700 /docker/volumes/pgdata
   ```

### 9.4 Verification Checklist

After deployment, verify:

```bash
# 1. Check pg_hba.conf is loaded
docker exec guinevere-db psql -U postgres -c "SELECT * FROM pg_hba_file_rules;" | grep -c "error"

# 2. Confirm no trust entries
docker exec guinevere-db psql -U postgres -c "SELECT * FROM pg_hba_file_rules WHERE error IS NULL AND method = 'trust';"

# 3. Confirm SSL is running
docker exec guinevere-db psql -U postgres -c "SHOW ssl;"
# Expected: on

# 4. Confirm SSL protocol
docker exec guinevere-db psql -U postgres -c "SHOW ssl_min_protocol_version;"
# Expected: TLSv1.2

# 5. Test SSL connection from another container
docker run --rm --network guinevere-net postgres:16-trixie \
  psql "host=guinevere-db dbname=postgres user=core_user sslmode=require" \
  -c "SELECT 'SSL OK';"

# 6. Verify non-SSL connection is rejected
docker run --rm --network guinevere-net postgres:16-trixie \
  psql "host=guinevere-db dbname=postgres user=core_user sslmode=disable" \
  -c "SELECT 'should not reach';"
# Expected: FATAL: no pg_hba.conf entry for ...

# 7. Check connection limits
docker exec guinevere-db psql -U postgres -c "SELECT rolname, rolconnlimit FROM pg_roles WHERE rolconnlimit > 0;"
```

---

## 10. References

| Source | URL | Content |
|---|---|---|
| PostgreSQL 16 Docs — pg_hba.conf | https://www.postgresql.org/docs/16/auth-pg-hba-conf.html | Full HBA file reference |
| PostgreSQL 16 Docs — Auth Methods | https://www.postgresql.org/docs/16/auth-methods.html | scram-sha-256, cert, peer |
| PostgreSQL 16 Docs — Password Auth | https://www.postgresql.org/docs/16/auth-password.html | SCRAM-SHA-256 vs md5 migration |
| PostgreSQL 16 Docs — Logging Config | https://www.postgresql.org/docs/16/runtime-config-logging.html | log_connections, log_disconnections, log_statement, log_line_prefix |
| PostgreSQL 16 Docs — Client Defaults | https://www.postgresql.org/docs/16/runtime-config-client.html | idle_in_transaction_session_timeout, idle_session_timeout, statement_timeout |
| PostgreSQL 16 Docs — SSL/TCP | https://www.postgresql.org/docs/16/ssl-tcp.html | Self-signed cert generation, hostssl |
| PostgreSQL 16 Docs — ALTER ROLE | https://www.postgresql.org/docs/16/sql-alterrole.html | CONNECTION LIMIT syntax |
| PostgreSQL 16 Docs — pg_reload_conf() | https://www.postgresql.org/docs/16/functions-admin.html | Reload function reference |
| CIS PostgreSQL 16 Benchmark v1.1.0 | https://www.cisecurity.org/benchmark/postgresql | Industry standard for PG hardening |
| Tenable CIS PG 16 v1.0.0 L1 Audit | https://www.tenable.com/audits/items/CIS_PostgreSQL_16_v1.0.0_L1_Database.audit:349a18cb4dcc8a41cacbc69f7e127e8d | log_connections/log_disconnections audit |
| StackHarden PG Hardening Guide | https://stackharden.com/guides/postgresql-hardening/ | Production pg_hba.conf baseline with hostssl |
| Redgate — Secure PG in Docker | https://www.red-gate.com/simple-talk/databases/postgresql/running-postgresql-in-docker-with-proper-ssl-and-configuration/ | Full Docker+SSL+config workflow |
| Smallstep — PG TLS in Containers | https://smallstep.com/practical-zero-trust/postgresql-tls | Certificate management patterns for containers |
| ppradela/postgres16-ol8-stig | https://github.com/ppradela/postgres16-ol8-stig | STIG-hardened PG 16 config reference |
| SOCFortress PG Hardening | https://socfortress.medium.com/postgresql-hardening-guide-8b8554e22336 | CIS-aligned logging config |
| Crunchy Data — pgAudit 16.0 | https://access.crunchydata.com/documentation/pgaudit/16.0/ | Extension-based audit logging |

---

## Appendix A — Quick-Reference SQL Script

Save as `pg16-harden.sql` for one-shot application:

```sql
-- pg16-harden.sql — PostgreSQL 16 production hardening
-- Run: psql -U postgres -f pg16-harden.sql

-- === AUTHENTICATION ===
ALTER SYSTEM SET password_encryption = 'scram-sha-256';

-- === AUDIT LOGGING ===
ALTER SYSTEM SET log_connections = 'on';
ALTER SYSTEM SET log_disconnections = 'on';
ALTER SYSTEM SET log_statement = 'ddl';
ALTER SYSTEM SET log_line_prefix = '%m [%p] %q%u@%d/%a ';
ALTER SYSTEM SET log_min_duration_statement = 500;
ALTER SYSTEM SET log_timezone = 'UTC';
ALTER SYSTEM SET logging_collector = 'on';

-- === TIMEOUTS ===
ALTER SYSTEM SET idle_in_transaction_session_timeout = '10min';
ALTER SYSTEM SET idle_session_timeout = '2h';

-- === SSL ===
ALTER SYSTEM SET ssl = 'on';
ALTER SYSTEM SET ssl_min_protocol_version = 'TLSv1.2';
ALTER SYSTEM SET ssl_prefer_server_ciphers = 'on';
-- NOTE: Set ssl_cert_file, ssl_key_file, ssl_ca_file to actual paths

-- === CONNECTION LIMITS ===
ALTER ROLE core_user CONNECTION LIMIT 30;
ALTER ROLE surveillance_user CONNECTION LIMIT 10;
ALTER ROLE scheduler_user CONNECTION LIMIT 10;
ALTER ROLE readonly_user CONNECTION LIMIT 15;
ALTER ROLE backup_user CONNECTION LIMIT 5;

-- === PER-ROLE STATEMENT TIMEOUTS ===
ALTER ROLE core_user SET statement_timeout TO '2min';
ALTER ROLE surveillance_user SET statement_timeout TO '5min';
ALTER ROLE scheduler_user SET statement_timeout TO '1min';
ALTER ROLE readonly_user SET statement_timeout TO '5min';
ALTER ROLE backup_user SET statement_timeout TO 0;
ALTER ROLE postgres SET statement_timeout TO 0;

-- === APPLY ===
SELECT pg_reload_conf();
```

**End of report.**