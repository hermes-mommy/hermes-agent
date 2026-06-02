# PgBouncer Docker Deployment — Comprehensive Research Report

**Scope**: PgBouncer as Docker container on `guinevere-net`, listening `127.0.0.1:5434`, connecting to `guinevere-postgres:5433` with `scram-sha-256` auth, PostgreSQL 16, 5 service users, VPS 4C/16GB.

**Date**: 2026-05-31  
**Status**: Complete  
**Downstream**: STEP-P0-019 — docker run command, `pgbouncer.ini`, `userlist.txt` generation strategy.

---

## 1. Official Documentation Sources

| Source | URL | Content |
|--------|-----|---------|
| Official PgBouncer site (config) | <https://www.pgbouncer.org/config.html> | Full `pgbouncer.ini` reference |
| Official PgBouncer site (usage) | <https://www.pgbouncer.org/usage.html> | SHOW commands, admin console, signals |
| GitHub config.md | <https://github.com/pgbouncer/pgbouncer/blob/master/doc/config.md> | Auth file format, SCRAM details |
| GitHub usage.md | <https://github.com/pgbouncer/pgbouncer/blob/master/doc/usage.md> | SHOW command reference |
| Context7 /pgbouncer/pgbouncer | Context7 library ID | 405 code snippets, benchmark 87 |

---

## 2. Docker Image Comparison

### 2.1 Recommended: `percona/percona-pgbouncer`

| Attribute | Value |
|-----------|-------|
| Image | `percona/percona-pgbouncer:1.25.2` |
| Base | Debian 12 (not Alpine) |
| Size | ~81.6 MB |
| Last Updated | ~2 months ago (Mar 2026) |
| Pulls | 100K+ (Verified Publisher) |
| Arch | amd64, arm64 |
| Tags | `1.25.2`, `1.25.2-1`, `1.25.2-amd64`, `1.25.2-arm64` |

**Critical config-mount note**: The Percona entrypoint script **processes config files on startup** and needs write access. Mount **without `:ro`** flag:
```yaml
volumes:
  - ./pgbouncer.ini:/etc/pgbouncer/pgbouncer.ini       # NO :ro
  - ./userlist.txt:/etc/pgbouncer/userlist.txt           # NO :ro
```
Source: [Docker Docs — Companions for PostgreSQL](https://docs.docker.com/guides/postgresql/companions-for-postgresql/)

### 2.2 Alternative: `edoburu/pgbouncer`

| Attribute | Value |
|-----------|-------|
| Image | `edoburu/pgbouncer:1.25.1-p0` |
| Base | Alpine Linux |
| Size | ~15 MB |
| Stars | 576 (most popular community image) |
| Last Push | 2025-12-21 |
| Features | Auto-creates config if missing, env-var driven, includes `psql` + `pg_isready` |

Supports `:ro` mounts. Config at `/etc/pgbouncer/pgbouncer.ini`. Can be configured via env vars (`DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_NAME`) or custom `pgbouncer.ini`.

### 2.3 Alternative: `icoretech/pgbouncer-docker` (GHCR)

| Attribute | Value |
|-----------|-------|
| Image | `ghcr.io/icoretech/pgbouncer-docker:1.25.1` |
| Base | Alpine (multi-arch amd64/arm64) |
| Last Push | 2026-03-06 |
| Reason | Bitnami went commercial; community migration target |

Config at `/etc/pgbouncer/pgbouncer.ini`, port 6432. Ships without config — must mount your own.

### 2.4 NOT Recommended: `bitnami/pgbouncer`

Bitnami **ended free Docker Hub availability** in 2025. Now requires commercial subscription (Bitnami Secure Images). Config at `/opt/bitnami/pgbouncer/conf/`. Do not use.

### 2.5 NOT Recommended: `ongres/pgbouncer`

StackGres-adjacent image. UBI8-based. Less community adoption, version tags are opaque hashes.

### 2.6 Custom Dockerfile

Can build from upstream release. Example from `icoretech/pgbouncer-docker`:
```dockerfile
FROM alpine:3.19
ARG REPO_TAG=pgbouncer_1_25_1
RUN apk add --no-cache pgbouncer~=${REPO_TAG#pgbouncer_}
COPY pgbouncer.ini /etc/pgbouncer/pgbouncer.ini
COPY userlist.txt /etc/pgbouncer/userlist.txt
EXPOSE 5432
USER pgbouncer
ENTRYPOINT ["/usr/bin/pgbouncer"]
CMD ["/etc/pgbouncer/pgbouncer.ini"]
```

### 2.7 Recommendation for Guinevere

**Use `percona/percona-pgbouncer:1.25.2`** — actively maintained, verified publisher, Debian-based (no Alpine musl edge cases), 100K+ pulls, and used in official Docker docs examples. Only caveat: mount config without `:ro`.

---

## 3. Docker Networking — Container Name vs IP

### 3.1 By Container Name (Recommended)

On Docker user-defined networks (like `guinevere-net`), Docker's embedded DNS resolves container names:

```ini
[databases]
guinevere = host=guinevere-postgres port=5433 dbname=guinevere
```

**Why preferred**: Container IPs can change on restart; DNS names are stable.

### 3.2 By Static IP

```ini
[databases]
guinevere = host=172.28.0.2 port=5433 dbname=guinevere
```

Requires static IP assignment at PostgreSQL container creation. More brittle.

### 3.3 Docker Run Networking

```bash
docker run --name guinevere-pgbouncer \
  --network guinevere-net \
  -p 127.0.0.1:5434:5432 \
  ...
```

The `--network guinevere-net` flag puts PgBouncer on the same Docker network as PostgreSQL, enabling container-name DNS resolution.

### 3.4 Reference: Official Docker Docs Example

From [Companions for PostgreSQL — Docker Docs](https://docs.docker.com/guides/postgresql/companions-for-postgresql/):
```yaml
networks:
  - pgnet
```
```yaml
postgres:
  image: postgres:18
  container_name: postgres
  networks:
    - pgnet
pgbouncer:
  image: percona/percona-pgbouncer:1.25.0
  container_name: pgbouncer
  networks:
    - pgnet
  depends_on:
    postgres:
      condition: service_healthy
```

And `pgbouncer.ini` references by container name:
```ini
[databases]
benchmark = host=postgres port=5432 dbname=benchmark user=postgres
```

---

## 4. `pgbouncer.ini` Configuration

### 4.1 `[databases]` Section

Connection to backend PostgreSQL. Container-name based:

```ini
[databases]
guinevere = host=guinevere-postgres port=5433 dbname=guinevere
```

Can also specify `user=` here to force all client connections to use a single backend user. Without it, each client user maps to the same PostgreSQL user.

### 4.2 `pool_mode` — Transaction vs Session

| Aspect | Transaction (`pool_mode = transaction`) | Session (`pool_mode = session`) |
|--------|----------------------------------------|----------------------------------|
| Server released | After each transaction completes | When client disconnects |
| Multiplexing ratio | High (N clients : few backends) | Low (N clients : N backends worst case) |
| Session state | **Lost** — `SET`, temp tables, `LISTEN`, cursors don't persist across transactions | Preserved |
| Prepared statements | Works with `max_prepared_statements` tracking | Works natively |
| `server_reset_query` | Not used (no session state to reset) | `DISCARD ALL` runs on release |
| Use case | **Web apps, REST APIs, microservices** | Legacy apps, session-dependent code |
| Connection reduction | Dramatic (e.g., 500 clients → 25 backends) | Modest (500 clients → 500 backends if all active) |

**Decision for Guinevere**: **Transaction mode** — 5 service users, none need session state (no `SET`, temp tables, cursors). Provides maximum connection efficiency.

Source: [Official config docs](https://www.pgbouncer.org/config.html#pool_mode), [Qisthi's comparison](https://qisthi.dev/blog/pgbouncer-connection-pooling-modes/)

### 4.3 `auth_type` — SCRAM-SHA-256

```ini
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt
```

- SCRAM-SHA-256 is the **only recommended** method for PostgreSQL 16+.
- PgBouncer 1.20+ supports it natively.
- `auth_file` must contain either:
  - **SCRAM secrets** (extracted from PostgreSQL's `pg_authid`) — used for client auth verification
  - **Plain-text passwords** (less secure, but also works)

**Critical constraint**: For the `auth_user` approach (see §4.4), the dedicated auth user in `userlist.txt` MUST use a **plain-text password**. SCRAM secrets cannot be used for the auth_user's own server login because PgBouncer needs to derive login credentials from the stored secret, which SCRAM's design prevents.

Source: [GitHub issue #1186](https://github.com/pgbouncer/pgbouncer/issues/1186), [Stack Overflow discussion](https://stackoverflow.com/questions/69473519/pgbouncer-and-scram-sha-256-setup)

### 4.4 `auth_user` + `auth_query` Approach (Recommended for 5+ Users)

Instead of maintaining all 5 users in `userlist.txt`:

```ini
[databases]
guinevere = host=guinevere-postgres port=5433 dbname=guinevere auth_user=pgbouncer_auth

[pgbouncer]
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt
auth_user = pgbouncer_auth
auth_query = SELECT rolname, rolpassword FROM pg_authid WHERE rolname=$1 AND rolcanlogin
```

**Setup**:
1. Create a dedicated PostgreSQL user:
   ```sql
   CREATE USER pgbouncer_auth WITH PASSWORD 'strong-password';
   GRANT SELECT ON pg_authid TO pgbouncer_auth;
   ```
2. In `userlist.txt`, put the **plain-text** password for `pgbouncer_auth`:
   ```
   "pgbouncer_auth" "strong-password"
   ```

**Security improvement**: Use a SECURITY DEFINER function instead of direct `pg_authid` access:

```sql
CREATE SCHEMA pgbouncer;
CREATE OR REPLACE FUNCTION pgbouncer.lookup_user(p_username text)
RETURNS TABLE(username text, password text) 
LANGUAGE plpgsql SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY 
    SELECT rolname::text, rolpassword::text 
    FROM pg_authid 
    WHERE rolname = p_username AND rolcanlogin;
END;
$$;
REVOKE ALL ON FUNCTION pgbouncer.lookup_user(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION pgbouncer.lookup_user(text) TO pgbouncer_auth;
```

Then use:
```ini
auth_query = SELECT username, password FROM pgbouncer.lookup_user($1)
```

Source: [Percona blog — Configuring auth_type with trust and HBA](https://www.percona.com/blog/configuring-pgbouncer-auth_type-with-trust-and-hba-examples-and-known-issues/)

### 4.5 `auth_file`-Only Approach (Simpler, More Manual)

All 5 users in `userlist.txt` with SCRAM hashes extracted from PostgreSQL:

```
"guinevere_core" "SCRAM-SHA-256$4096:<salt>$<storedkey>:<serverkey>"
"surveillance" "SCRAM-SHA-256$4096:<salt>$<storedkey>:<serverkey>"
"scheduler" "SCRAM-SHA-256$4096:<salt>$<storedkey>:<serverkey>"
"readonly" "SCRAM-SHA-256$4096:<salt>$<storedkey>:<serverkey>"
"backup" "SCRAM-SHA-256$4096:<salt>$<storedkey>:<serverkey>"
```

**Generating SCRAM hashes**:
```bash
# Method 1: psql --echo-hidden (prints the hash before sending)
psql --echo-hidden -h guinevere-postgres -p 5433 -U postgres -d guinevere
# Then: \password guinevere_core
# Note the SCRAM hash printed in the ALTER USER query

# Method 2: Query pg_authid directly
psql -h guinevere-postgres -p 5433 -U postgres -d guinevere \
  -t -A \
  -c "SELECT '\"' || rolname || '\" \"' || rolpassword || '\"' FROM pg_authid WHERE rolcanlogin;"
```

**Important**: The SCRAM hash in `userlist.txt` must be **byte-for-byte identical** to the one in PostgreSQL (same salt, iterations, stored key, server key). If you change the password later, you must update both PostgreSQL and `userlist.txt`.

Source: [Official auth file format](https://www.pgbouncer.org/config.html#authentication-file-format), [Crunchy Data Blog](https://www.crunchydata.com/blog/pgbouncer-scram-authentication-postgresql)

---

## 5. Pool Sizing for 4C/16GB VPS with 5 Service Users

### 5.1 Memory Budget

| Component | Estimated Usage |
|-----------|----------------|
| OS + Docker overhead | ~2 GB |
| PostgreSQL 16 (shared_buffers ~4GB, connections) | ~5 GB |
| PgBouncer (lightweight, each client ~few KB) | ~0.5 GB |
| Application overhead | ~2 GB |
| **Buffer** | **~6.5 GB remaining** |

Each PostgreSQL backend connection consumes ~10 MB RAM. With 16 GB total, PostgreSQL `max_connections` should be kept under 200 (ideally 100-150).

### 5.2 Recommended Sizing

```ini
[pgbouncer]
; Client-side (many can connect)
max_client_conn = 500

; Per user/database pool
default_pool_size = 20       ; Per (database, user) pair
min_pool_size = 5            ; Keep warm connections ready
reserve_pool_size = 10       ; Burst capacity
reserve_pool_timeout = 5.0   ; Seconds before reserve kicks in

; Global caps
max_db_connections = 100     ; Total backends to PostgreSQL (global)
max_db_client_connections = 500  ; Clients per database
max_user_connections = 50    ; Per-user server limit
max_user_client_connections = 200  ; Per-user client limit

; Timeouts
server_lifetime = 3600       ; Recycle connections every hour
server_idle_timeout = 600    ; Close idle after 10 min
server_connect_timeout = 15  ; Connection attempt timeout
query_wait_timeout = 120     ; How long a query can wait in queue
```

### 5.3 Rationale

- **5 users × 20 pool_size = 100 max backends** → ~1 GB PostgreSQL RAM for connections. Well within 16 GB.
- **500 max clients** → Each client connection in PgBouncer uses ~few KB (not the ~10MB of a full PostgreSQL backend). Completely fine for VPS.
- **reserve_pool_size + min_pool_size** → Warm pool absorbs traffic spikes without latency penalty.
- **max_db_connections = 100** → Hard cap prevents PostgreSQL overload even if client count spikes.
- **max_user_connections = 50** → Prevents any single user from consuming all pool connections.

For comparison: icoretech Helm chart defaults for production use `default_pool_size=100`, `max_client_conn=8192`, `max_db_connections=200` — those assume bigger hardware. Our 4C/16GB is more modest.

### 5.4 PgBouncer is Single-Threaded

PgBouncer uses one CPU core. On 4 cores, a single instance handles 500-1000 clients easily. If you ever need more throughput, use `so_reuseport=1` with a second peered PgBouncer instance on the same port (kernel distributes connections across cores).

Source: [Official config — "so_reuseport" section](https://www.pgbouncer.org/config.html#so_reuseport), pool sizing calculations.

---

## 6. Health Check Methods

### 6.1 PgBouncer Responds to `pg_isready`

PgBouncer implements the PostgreSQL readiness protocol on its admin port. Simple health check:

```bash
pg_isready -h localhost -p 5434
# Returns: localhost:5434 - accepting connections
```

### 6.2 Docker Healthcheck Configuration

```dockerfile
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
  CMD pg_isready -h localhost -p 5432 -U pgbouncer_auth -d pgbouncer || exit 1
```

Or use the admin database (no auth required for local socket):
```dockerfile
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
  CMD pg_isready -h 127.0.0.1 -p 5432 || exit 1
```

### 6.3 Enhanced Health Check (via psql)

More thorough: actually connect and run a SHOW command:
```bash
psql -h localhost -p 5432 -U pgbouncer_auth -d pgbouncer -c "SHOW POOLS;" > /dev/null 2>&1 || exit 1
```

### 6.4 Docker Compose Pattern

From [Docker Hardened Images guide](https://hub.docker.com/hardened-images/catalog/dhi/pgbouncer/guides):
```yaml
healthcheck:
  test: ['CMD', 'pg_isready', '-h', 'localhost', '-p', '6432']
  interval: 10s
  timeout: 5s
  retries: 3
```

Source: [Official usage docs](https://www.pgbouncer.org/usage.html), [Docker Hardened Images catalog](https://hub.docker.com/hardened-images/catalog/dhi/pgbouncer/guides)

---

## 7. Stats & Monitoring Commands

### 7.1 Connecting to Admin Console

```bash
psql -h 127.0.0.1 -p 5434 -U <admin_user> -d pgbouncer
```

Only users in `admin_users` or `stats_users` can connect (unless `auth_type=any`).

### 7.2 `SHOW HELP`

Lists all available commands:
```
  SHOW [HELP|CONFIG|DATABASES|FDS|POOLS|CLIENTS|SERVERS|SOCKETS|LISTS|VERSION|...]
  SET key = arg
  RELOAD
  PAUSE
  SUSPEND
  RESUME
  SHUTDOWN
```

### 7.3 `SHOW POOLS` — Per-Pool Connection States

| Column | Description | Signal |
|--------|-------------|--------|
| `database` | Database name | — |
| `user` | User name | — |
| `cl_active` | Clients linked to servers or idle | Normal |
| `cl_waiting` | Clients queued waiting for a server | **If >0 persistently → increase pool_size** |
| `sv_active` | Server connections linked to clients | Normal |
| `sv_idle` | Server connections unused, ready | Normal |
| `sv_used` | Server connections idle > `server_check_delay` | Normal (will be tested) |
| `sv_login` | Servers currently logging in | Should be transient |
| `maxwait` | Oldest client queue wait (seconds) | **If growing → overloaded or too-small pool** |

### 7.4 `SHOW STATS` — Performance Metrics

| Column | Description |
|--------|-------------|
| `total_xact_count` | Total transactions pooled |
| `total_query_count` | Total SQL commands pooled |
| `total_received` / `total_sent` | Traffic volume (bytes) |
| `total_xact_time` | Microseconds in transactions |
| `total_query_time` | Microseconds executing queries |
| `total_wait_time` | Microseconds clients waited for a server |
| `avg_xact_count` | Avg transactions/sec (last stats period) |
| `avg_xact_time` | Avg transaction duration (μs) |
| `avg_wait_time` | Avg wait time (μs) |

### 7.5 `SHOW CLIENTS` — Connected Clients

| Column | Description |
|--------|-------------|
| `type` | Always `C` for client |
| `user` | Connected user |
| `database` | Database name |
| `state` | `active`, `waiting`, `active_cancel_req`, `waiting_cancel_req` |
| `addr` | Client IP address |
| `connect_time` | When connection was established |
| `request_time` | When last request was made |

### 7.6 `SHOW SERVERS` — Backend Connections

| Column | Description |
|--------|-------------|
| `type` | Always `S` for server |
| `user` | Backend PostgreSQL user |
| `state` | `active`, `idle`, `used`, `tested`, `new`, `login` |
| `addr` / `port` | PostgreSQL server address |
| `connect_time` | When connection was made |
| `close_needed` | `1` if connection will be closed (config reload) |

### 7.7 Other Useful SHOW Commands

| Command | Purpose |
|---------|---------|
| `SHOW CONFIG` | Current runtime config values |
| `SHOW DATABASES` | Per-database pool sizes, connection limits |
| `SHOW USERS` | Per-user pool sizes, connection counts |
| `SHOW LISTS` | Internal counts (databases, users, pools, free/used clients/servers) |
| `SHOW VERSION` | PgBouncer version string |
| `SHOW TOTALS` | Aggregated stats across all databases |
| `SHOW FDS` | File descriptors (internal debugging) |

### 7.8 Control Commands

| Command | Purpose |
|---------|---------|
| `RELOAD` | Reload config without restart |
| `PAUSE [db]` | Disconnect all servers (for DB restart) |
| `RESUME [db]` | Resume after PAUSE |
| `RECONNECT [db]` | Close/refresh all server connections |
| `KILL [db]` | Drop all client and server connections immediately |
| `SET key = value` | Change runtime setting (e.g., `SET log_connections = 1`) |
| `SHUTDOWN` | Exit PgBouncer |

Source: [Official usage docs — SHOW commands](https://www.pgbouncer.org/usage.html#show-commands)

---

## 8. Secrets Handling — `userlist.txt`

### 8.1 Never Commit Plaintext Passwords

**Hard rule**: `userlist.txt` must **never** contain plaintext passwords in git. Three strategies:

#### Strategy A: `auth_user` + `auth_query` (Best — no passwords in file)

Only the dedicated auth user's plaintext password is in `userlist.txt`. All other users are queried dynamically from PostgreSQL at runtime. Only the auth user password needs to be managed securely.

#### Strategy B: SCRAM Hashes in `userlist.txt` (Good)

```
"guinevere_core" "SCRAM-SHA-256$4096:<salt>$<storedkey>:<serverkey>"
```

SCRAM hashes are one-way; even if leaked, attackers cannot derive the original password. Still, treat as sensitive.

#### Strategy C: Use Docker Secrets (for Docker Swarm)

```yaml
secrets:
  userlist:
    file: ./secrets/userlist.txt
services:
  pgbouncer:
    image: percona/percona-pgbouncer:1.25.2
    secrets:
      - source: userlist
        target: /etc/pgbouncer/userlist.txt
```

### 8.2 Generation Flow (for Downstream STEP-P0-019)

1. **For `auth_user` approach**: Create one user in PostgreSQL, put its **plaintext password** in `userlist.txt`. Use `auth_query` for all other users.
2. **For all-users-in-file approach**: For each of the 5 users:
   ```bash
   psql -h guinevere-postgres -p 5433 -U postgres -d guinevere \
     -t -A \
     -c "SELECT '\"' || rolname || '\" \"' || rolpassword || '\"' FROM pg_authid WHERE rolname='<user>';"
   ```
   Paste output into `userlist.txt`.

### 8.3 Password Change Procedure

| Approach | Password Change |
|----------|----------------|
| `auth_user` + `auth_query` | Change in PostgreSQL only. Dynamic lookup picks it up. |
| `auth_file` (SCRAM hashes) | Change in PostgreSQL, re-extract hash, update `userlist.txt`, `RELOAD`. |
| `auth_file` (plaintext) | Change in both PostgreSQL and `userlist.txt`, `RELOAD`. |

### 8.4 SOPS Integration (for Guinevere's encrypted secrets)

If passwords are SOPS-encrypted, the deployment script should:
1. Decrypt the SOPS-encrypted credentials file
2. Generate `userlist.txt` from decrypted values
3. Mount into container
4. Never persist `userlist.txt` on disk in plaintext

Source: [CYBERTEC blog](https://www.cybertec-postgresql.com/en/pgbouncer-authentication-made-easy/), [Official auth file format](https://www.pgbouncer.org/config.html#authentication-file-format)

---

## 9. Complete Reference Configuration (Downstream-Ready)

### 9.1 `pgbouncer.ini`

```ini
[databases]
guinevere = host=guinevere-postgres port=5433 dbname=guinevere

[pgbouncer]
; Listen on all interfaces inside container, map to 127.0.0.1:5434 outside
listen_addr = 0.0.0.0
listen_port = 5432

; Authentication
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt
auth_user = pgbouncer_auth
auth_query = SELECT rolname, rolpassword FROM pg_authid WHERE rolname=$1 AND rolcanlogin

; Pooling mode
pool_mode = transaction

; Connection sizing (4C/16GB VPS, 5 service users)
max_client_conn = 500
default_pool_size = 20
min_pool_size = 5
reserve_pool_size = 10
reserve_pool_timeout = 5.0
max_db_connections = 100
max_user_connections = 50

; Timeouts
server_lifetime = 3600
server_idle_timeout = 600
server_connect_timeout = 15
server_login_retry = 15
query_wait_timeout = 120
client_login_timeout = 60

; Prepared statement support (transaction mode needs tracking)
max_prepared_statements = 200
ignore_startup_parameters = extra_float_digits

; Logging
log_connections = 1
log_disconnections = 1
log_pooler_errors = 1
log_stats = 1
stats_period = 60

; Admin
admin_users = guinevere_core
stats_users = guinevere_core, readonly

; TLS (optional for internal Docker network — disable if not needed)
; client_tls_sslmode = disable
; server_tls_sslmode = prefer
```

### 9.2 `userlist.txt` (auth_user approach — minimal)

```
"pgbouncer_auth" "plain-text-password-from-sops"
```

### 9.3 Docker Run Command

```bash
docker run -d \
  --name guinevere-pgbouncer \
  --network guinevere-net \
  --restart unless-stopped \
  -p 127.0.0.1:5434:5432 \
  -v /path/to/pgbouncer.ini:/etc/pgbouncer/pgbouncer.ini \
  -v /path/to/userlist.txt:/etc/pgbouncer/userlist.txt \
  percona/percona-pgbouncer:1.25.2
```

### 9.4 Docker Compose Snippet

```yaml
services:
  pgbouncer:
    image: percona/percona-pgbouncer:1.25.2
    container_name: guinevere-pgbouncer
    restart: unless-stopped
    ports:
      - "127.0.0.1:5434:5432"
    networks:
      - guinevere-net
    volumes:
      - ./pgbouncer/pgbouncer.ini:/etc/pgbouncer/pgbouncer.ini
      - ./pgbouncer/userlist.txt:/etc/pgbouncer/userlist.txt
    depends_on:
      guinevere-postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "pg_isready", "-h", "localhost", "-p", "5432"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 10s
```

---

## 10. References

| # | Source | URL |
|---|--------|-----|
| 1 | Official PgBouncer Configuration | <https://www.pgbouncer.org/config.html> |
| 2 | Official PgBouncer Usage (SHOW commands) | <https://www.pgbouncer.org/usage.html> |
| 3 | GitHub config.md (auth file format) | <https://github.com/pgbouncer/pgbouncer/blob/master/doc/config.md> |
| 4 | Docker Docs — Companions for PostgreSQL | <https://docs.docker.com/guides/postgresql/companions-for-postgresql/> |
| 5 | Percona PgBouncer Docker Hub | <https://hub.docker.com/r/percona/percona-pgbouncer> |
| 6 | Docker Hardened Images — PgBouncer Guide | <https://hub.docker.com/hardened-images/catalog/dhi/pgbouncer/guides> |
| 7 | Percona Blog — PgBouncer auth_type config | <https://www.percona.com/blog/configuring-pgbouncer-auth_type-with-trust-and-hba-examples-and-known-issues/> |
| 8 | Crunchy Data — SCRAM in PgBouncer | <https://www.crunchydata.com/blog/pgbouncer-scram-authentication-postgresql> |
| 9 | CYBERTEC — PgBouncer Authentication | <https://www.cybertec-postgresql.com/en/pgbouncer-authentication-made-easy/> |
| 10 | GitHub Issue #1186 — SCRAM + auth_user bug | <https://github.com/pgbouncer/pgbouncer/issues/1186> |
| 11 | GitHub Issue #1429 — Docker image requests | <https://github.com/pgbouncer/pgbouncer/issues/1429> |
| 12 | icoretech/pgbouncer-docker (alternative image) | <https://github.com/icoretech/pgbouncer-docker> |
| 13 | edoburu/docker-pgbouncer (Alpine alternative) | <https://github.com/edoburu/docker-pgbouncer> |
| 14 | Qisthi — Pool mode comparison | <https://qisthi.dev/blog/pgbouncer-connection-pooling-modes/> |
| 15 | PostgreSQL Connection Pooling 2026 | <https://postgresqlhtx.com/postgresql-connection-pooling-in-2026-when-to-use-pgbouncer-vs-built-in-pooling/> |

---

*Report generated for STEP-P0-019 downstream use. See `audit-reports/P0/STEP-P0-019/` for the implementation artifacts.*