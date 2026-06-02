# Infrastructure Stack Research Report
## PostgreSQL 16, Redis 7, PgBouncer & systemd Service Patterns

**Date**: 2026-05-31  
**Scope**: Guinevere project infrastructure layer  
**Target OS**: Ubuntu 22.04 LTS (Jammy)  
**Downstream**: Step-by-step implementation prompts with exact commands  

---

## Table of Contents

1. [PostgreSQL 16 + Extensions](#1-postgresql-16--extensions)
   - [1.1 Installation](#11-installation)
   - [1.2 pgvector Extension](#12-pgvector-extension)
   - [1.3 TimescaleDB Extension](#13-timescaledb-extension)
   - [1.4 Full-Text Search (tsvector + GIN)](#14-full-text-search-tsvector--gin)
   - [1.5 User/Role Creation (Least-Privilege)](#15-userrole-creation-least-privilege)
   - [1.6 pg_hba.conf Security Hardening](#16-pg_hbaconf-security-hardening)
   - [1.7 Performance Tuning](#17-performance-tuning)
2. [PgBouncer](#2-pgbouncer)
   - [2.1 Installation & Setup](#21-installation--setup)
   - [2.2 Connection Pooling Configuration](#22-connection-pooling-configuration)
   - [2.3 Per-User Auth Patterns](#23-per-user-auth-patterns)
   - [2.4 PostgreSQL Integration](#24-postgresql-integration)
3. [Redis 7](#3-redis-7)
   - [3.1 Installation](#31-installation)
   - [3.2 ACL Configuration](#32-acl-configuration)
   - [3.3 DB Separation](#33-db-separation)
   - [3.4 Persistence (RDB vs AOF)](#34-persistence-rdb-vs-aof)
   - [3.5 Memory Limits & Eviction](#35-memory-limits--eviction)
4. [systemd Service Patterns](#4-systemd-service-patterns)
   - [4.1 Service File Structure](#41-service-file-structure)
   - [4.2 Restart Policies](#42-restart-policies)
   - [4.3 Environment Variables](#43-environment-variables)
   - [4.4 Logging with journald](#44-logging-with-journald)
   - [4.5 Dependencies](#45-dependencies)

---

## 1. PostgreSQL 16 + Extensions

### 1.1 Installation

**Source**: Official [PostgreSQL APT Repository](https://wiki.postgresql.org/wiki/Apt) (PGDG).  
**Evidence**: [linuxcapable.com guide](https://linuxcapable.com/how-to-install-postgresql-16-on-ubuntu-linux/) confirms PGDG is required for Ubuntu 22.04 (Jammy) since postgresql-16 is not in the standard repos.

**Installation commands**:

```bash
# Add PGDG repository
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'

# Import signing key
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -

# Install PostgreSQL 16
sudo apt update
sudo apt install -y postgresql-16 postgresql-client-16

# Verify
pg_config --version  # Should show PostgreSQL 16.x
systemctl status postgresql@16-main
```

**Key packages**:
| Package | Purpose |
|---|---|
| `postgresql-16` | Core server |
| `postgresql-client-16` | psql cli tools |
| `postgresql-server-dev-16` | Build extensions from source |
| `postgresql-16-pgvector` | pgvector (if available via PGDG) |
| `postgresql-16-tsdb` | TimescaleDB (if available via Timescale repo) |

### 1.2 pgvector Extension

**Source**: Real-world examples from [genkit-ai/genkit](https://github.com/genkit-ai/genkit/blob/main/go/samples/pgvector/pgvector.sql#L21), [0xPlaygrounds/rig](https://github.com/0xPlaygrounds/rig/blob/main/tests/migrations/001_setup.sql#L2).

**Installation**:

```bash
# Option A: From PGDG (if available for 16)
sudo apt install postgresql-16-pgvector

# Option B: From source
cd /tmp
git clone --branch v0.8.0 https://github.com/pgvector/pgvector.git
cd pgvector
make clean && make PG_CONFIG=/usr/lib/postgresql/16/bin/pg_config
sudo make install PG_CONFIG=/usr/lib/postgresql/16/bin/pg_config
```

**Usage pattern**:

```sql
-- Enable extension (as superuser)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create table with embeddings (1536d = text-embedding-3-small)
CREATE TABLE documents (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    content text NOT NULL,
    embedding vector(1536),
    metadata jsonb DEFAULT '{}'
);

-- Create vector index (IVFFlat for memory-constrained, HNSW for faster search)
CREATE INDEX documents_embedding_hnsw_idx ON documents
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 200);

-- Cosine similarity search
SELECT id, content, 1 - (embedding <=> $1::vector) AS similarity
FROM documents
ORDER BY embedding <=> $1::vector
LIMIT 10;
```

**Index comparison** [source: pdichone/vector-databases-course](https://github.com/pdichone/vector-databases-course/blob/main/pg_vector_section/4-indexes/02_create_ivfflat_index.sql):
| Index Type | Best For | Build Time | Query Speed |
|---|---|---|---|
| IVFFlat | Memory constrained, static data | ~5s | Fast (approximate) |
| HNSW | Frequent updates, fastest search | ~10s | Fastest |

### 1.3 TimescaleDB Extension

**Source**: TimescaleDB test suite [timescale/timescaledb](https://github.com/timescale/timescaledb/blob/main/test/sql/trusted_extension.sql#L12), real deploy [datahub-project/datahub](https://github.com/datahub-project/datahub/blob/master/metadata-ingestion/tests/integration/timescaledb/setup/setup.sql#L10).

**Installation**:

```bash
# Add TimescaleDB repository
echo "deb https://packagecloud.io/timescale/timescaledb/ubuntu/ $(lsb_release -c -s) main" | sudo tee /etc/apt/sources.list.d/timescaledb.list
wget --quiet -O - https://packagecloud.io/timescale/timescaledb/gpgkey | sudo apt-key add -
sudo apt update
sudo apt install timescaledb-2-postgresql-16

# Configure shared_preload_libraries
sudo timescaledb-tune --pg-config /usr/lib/postgresql/16/bin/pg_config
sudo systemctl restart postgresql@16-main
```

**Usage pattern**:

```sql
-- Enable extension (as superuser)
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create hypertable for time-series data
CREATE TABLE sensor_data (
    time TIMESTAMPTZ NOT NULL,
    device_id INTEGER NOT NULL,
    temperature DOUBLE PRECISION,
    humidity DOUBLE PRECISION,
    location VARCHAR(100)
);

SELECT create_hypertable('sensor_data', 'time',
    chunk_time_interval => INTERVAL '1 day'
);

-- Create index on hypertable
CREATE INDEX ON sensor_data (device_id, time DESC);

-- Enable compression (older chunks)
ALTER TABLE sensor_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'device_id',
    timescaledb.compress_orderby = 'time DESC'
);

-- Auto-compress chunks older than 7 days
SELECT add_compression_policy('sensor_data', INTERVAL '7 days');
```

**Key settings** (via timescaledb-tune):
```ini
# postgresql.conf additions
shared_preload_libraries = 'timescaledb'
timescaledb.telemetry_level = 'off'  # Disable telemetry
```

### 1.4 Full-Text Search (tsvector + GIN)

**Source**: PostgreSQL docs, real-world pattern from [laguagu/claude-code-nextjs-skills](https://github.com/laguagu/claude-code-nextjs-skills/blob/main/skills/postgres-semantic-search/scripts/indexes.sql#L74).

**Usage pattern**:

```sql
-- Enable pg_trgm for fuzzy search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Approach 1: Generated column with GIN index
CREATE TABLE chat_messages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('simple', coalesce(content, ''))
    ) STORED
);

CREATE INDEX chat_messages_fts_idx ON chat_messages
    USING GIN (search_vector);

-- Approach 2: Index on expression (no extra column)
CREATE INDEX documents_fts_idx ON documents
    USING GIN (to_tsvector('simple', coalesce(content, '')));

-- Query with ranking
SELECT content,
       ts_rank(search_vector, query) AS rank
FROM chat_messages,
     to_tsquery('simple', 'postgresql & performance') query
WHERE search_vector @@ query
ORDER BY rank DESC
LIMIT 20;

-- Fuzzy search with pg_trgm
CREATE INDEX chat_trgm_idx ON chat_messages
    USING GIN (content gin_trgm_ops);

-- ILIKE / similarity queries now use index
SELECT * FROM chat_messages
WHERE content % 'porstgresql'  -- fuzzy match (trigram similarity)
ORDER BY similarity(content, 'porstgresql') DESC;
```

**Common pitfalls**:
- `GIN` indexes are expensive to build on large existing tables (>1M rows). Consider building off-peak.
- `tsvector` with `'english'` vs `'simple'`: `'english'` strips stopwords and stems ("running" → "run"), `'simple'` is exact-match. Choose based on use case.
- Generated `STORED` columns increase write-time overhead vs expression indexes.

### 1.5 User/Role Creation (Least-Privilege)

**Source**: PostgreSQL test suite role attributes [postgres/postgres](https://github.com/postgres/postgres/blob/master/src/test/regress/sql/roleattributes.sql#L2).

**Security hierarchy**:

```sql
-- 1. Create NO-LOGIN group roles (access containers)
CREATE ROLE guinevere_readonly NOLOGIN;
CREATE ROLE guinevere_readwrite NOLOGIN;
CREATE ROLE guinevere_admin NOLOGIN;

-- 2. Grant schema-level permissions to group roles
GRANT CONNECT ON DATABASE guinevere_db TO guinevere_readonly;
GRANT USAGE ON SCHEMA public TO guinevere_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO guinevere_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO guinevere_readonly;

GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO guinevere_readwrite;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO guinevere_readwrite;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT INSERT, UPDATE, DELETE ON TABLES TO guinevere_readwrite;

-- 3. Create user accounts with LOGIN + inherit privileges
CREATE ROLE guinevere_app WITH
    LOGIN
    PASSWORD 'strong-password-here'
    INHERIT
    CONNECTION LIMIT 20
    IN ROLE guinevere_readwrite;

CREATE ROLE guinevere_monitor WITH
    LOGIN
    PASSWORD 'monitor-password-here'
    INHERIT
    IN ROLE guinevere_readonly;

-- 4. Extension bootstrap: create dedicated admin user (NOT postgres)
CREATE ROLE guinevere_dba WITH
    LOGIN
    SUPERUSER
    PASSWORD 'dba-strong-password';

-- IMPORTANT: After setup, revoke non-essential superuser
-- ALTER ROLE guinevere_dba NOSUPERUSER;
```

**Least-privilege checklist**:
- [ ] Never use `postgres` superuser for application connections
- [ ] Separate group roles from login roles
- [ ] Use `CONNECTION LIMIT` to prevent connection exhaustion
- [ ] `NOLOGIN` for roles that only group permissions
- [ ] `ALTER DEFAULT PRIVILEGES` ensures future tables inherit grants
- [ ] Application users get `IN ROLE <group>` not direct grants

### 1.6 pg_hba.conf Security Hardening

**Source**: [PostgreSQL 16 docs](https://www.postgresql.org/docs/16/client-authentication-problems.html), PgBouncer docs.

**Recommended `/etc/postgresql/16/main/pg_hba.conf`**:

```conf
# TYPE  DATABASE        USER            ADDRESS                 METHOD

# Database administrator — local socket only
local   all             guinevere_dba                           peer

# Application users — localhost with password
host    guinevere_db    guinevere_app   127.0.0.1/32            scram-sha-256
host    guinevere_db    guinevere_app   ::1/128                 scram-sha-256

# PgBouncer — localhost with scram-sha-256 (PgBouncer 1.22+)
host    all             guinevere_bouncer 127.0.0.1/32          scram-sha-256

# Replication — restricted subnet
host    replication     replicator      10.0.0.0/8              md5

# Monitoring — localhost only
host    all             guinevere_monitor 127.0.0.1/32          scram-sha-256

# Default: deny everything
host    all             all             0.0.0.0/0               reject
```

**Security rules**:
1. **Always use `scram-sha-256`**, never `md5` unless legacy. Passwords are salted with SCRAM.
2. **No `trust` auth** outside local socket peer.
3. **No `0.0.0.0/0` entries** except explicit `reject` at the bottom.
4. **pg_hba.conf order matters** — first match wins.
5. **Pitfall**: Changing auth method requires `pg_reload_conf()` or `systemctl reload postgresql@16-main`.

**Set password encryption to scram-sha-256**:

```ini
# postgresql.conf
password_encryption = scram-sha-256
```

### 1.7 Performance Tuning

**Source**: [PostgreSQL 16 docs: shared_buffers](https://www.postgresql.org/docs/16/runtime-config-resource.html#GUC-SHARED-BUFFERS), [Performance section](https://www.postgresql.org/docs/16/release-16.html).

**Recommended baseline for Guinevere (4 GB RAM VM)**:

```ini
# postgresql.conf
# --- Memory ---
shared_buffers = 1GB                # 25% of system RAM (dedicated server)
work_mem = 64MB                     # Per-operation sort/hash memory
maintenance_work_mem = 256MB        # VACUUM, CREATE INDEX, etc.
effective_cache_size = 3GB          # 75% of RAM (advises planner)

# --- WAL ---
wal_level = replica                 # Enough for replication + logical
wal_buffers = 16MB                  # Write-ahead log buffer
max_wal_size = 2GB                  # Soft limit before auto-checkpoint

# --- Planner ---
random_page_cost = 1.1              # 1.1 if SSD, 4.0 if HDD
effective_io_concurrency = 200      # SSD concurrency

# --- Connections ---
max_connections = 100               # Keep low; use PgBouncer for pooling

# --- Extension libraries ---
shared_preload_libraries = 'pg_stat_statements, timescaledb'

# --- Query monitoring ---
pg_stat_statements.track = all

# --- Parallelism ---
max_parallel_workers_per_gather = 2
max_parallel_workers = 4
```

**Formula reference**:
| Parameter | Formula | Example (4 GB) |
|---|---|---|
| `shared_buffers` | 25% RAM | 1 GB |
| `work_mem` | (RAM - shared_buffers) / (max_connections × 4) | ~64 MB |
| `maintenance_work_mem` | 10% RAM (cap 1 GB) | 256 MB |
| `effective_cache_size` | 75% RAM | 3 GB |
| `max_connections` | Cores × 25 | 100 |

**Pitfall**: Setting `shared_buffers` above 40% on Linux can reduce performance because PostgreSQL's double-buffering fights the OS page cache. The PostgreSQL docs explicitly state exceeding 40% is "unlikely to improve performance."

---

## 2. PgBouncer

### 2.1 Installation & Setup

**Source**: [PgBouncer official docs](https://github.com/pgbouncer/pgbouncer/blob/master/doc/usage.md), real configs from [neondatabase/neon](https://github.com/neondatabase/neon/blob/main/compute/etc/pgbouncer.ini).

**Installation**:

```bash
# Install from repo (Ubuntu 22.04 has pgbouncer >= 1.17)
sudo apt update
sudo apt install -y pgbouncer

# Verify version (must be >= 1.22 for scram-sha-256 support)
pgbouncer --version

# Stop the default service (we'll create our own)
sudo systemctl stop pgbouncer
sudo systemctl disable pgbouncer
```

### 2.2 Connection Pooling Configuration

**Recommended `/etc/pgbouncer/pgbouncer.ini`**:

```ini
[databases]
; Database definitions: name = connection_string
guinevere_db = host=127.0.0.1 port=5432 dbname=guinevere_db

; Wildcard fallback (optional — auth_user handles all)
* = host=127.0.0.1 port=5432 auth_user=guinevere_bouncer

[pgbouncer]
;;; Administrative
logfile = /var/log/pgbouncer/pgbouncer.log
pidfile = /var/run/pgbouncer/pgbouncer.pid

;;; Networking
listen_addr = 127.0.0.1        # NEVER 0.0.0.0 unless behind firewall
listen_port = 6432
unix_socket_dir = /var/run/postgresql

;;; Authentication
auth_type = scram-sha-256      # Match PostgreSQL auth method
auth_file = /etc/pgbouncer/userlist.txt
auth_user = guinevere_bouncer  # Single user that connects to PostgreSQL for auth
auth_dbname = postgres         # Database for auth_query (when not using auth_user)

;;; Pooling
pool_mode = transaction        # Best for web apps; alternatives: session, statement
default_pool_size = 20         # Connections per user/db pair
max_client_conn = 200          # Max incoming client connections
max_db_connections = 50        # Max connections to PostgreSQL
max_user_connections = 30      # Max connections per user

;;; Timeouts
server_idle_timeout = 600      # Drop idle server connections (10 min)
client_idle_timeout = 0        # Never timeout client connections by default
query_timeout = 0              # Never timeout queries (override per-db)

;;; TLS (enable in production)
client_tls_sslmode = disable   # Internal traffic on localhost
; client_tls_cert_file = /etc/ssl/certs/pgbouncer.crt
; client_tls_key_file = /etc/ssl/private/pgbouncer.key

;;; Admin
admin_users = guinevere_dba
stats_users = guinevere_monitor
```

**Pool mode comparison**:
| Mode | When to Use | Caveat |
|---|---|---|
| `transaction` | Stateless web apps | Don't use with `SET session` or prepared statements |
| `session` | Stateful apps, migrations | Each client gets dedicated server connection |
| `statement` | Connection-constrained microservices | Most aggressive pooling |

**Source for config values**: [zalando/postgres-operator](https://github.com/zalando/postgres-operator/blob/master/pooler/pgbouncer.ini.tmpl), [tldraw/tldraw](https://github.com/tldraw/tldraw/blob/main/apps/dotcom/zero-cache/docker/pgbouncer.ini), [symfony test fixtures](https://github.com/symfony/symfony/blob/8.1/src/Symfony/Component/Messenger/Bridge/Doctrine/Tests/Fixtures/pgbouncer/pgbouncer.ini).

### 2.3 Per-User Auth Patterns

**Option A: userlist.txt (simple, single password per user)**:

```text
# /etc/pgbouncer/userlist.txt
"guinevere_app" "scram-sha-256$4096:hashvalue..."
"guinevere_monitor" "scram-sha-256$4096:hashvalue..."
"guinevere_dba" "scram-sha-256$4096:hashvalue..."
```

To get the SCRAM hash, run on PostgreSQL:
```sql
SELECT rolpassword FROM pg_authid WHERE rolname = 'guinevere_app';
```

**Option B: auth_user (delegates auth to PostgreSQL)**:

```ini
auth_user = guinevere_bouncer  # PgBouncer connects as this user
```

With this pattern, you create a single `guinevere_bouncer` user in PostgreSQL and PgBouncer asks PostgreSQL to verify the client's credentials.

**Option C: HBA file (fine-grained, PostgreSQL-style)**:

```ini
auth_type = hba
auth_hba_file = /etc/pgbouncer/pg_hba.conf
```

```conf
# /etc/pgbouncer/pg_hba.conf
local   all         all                         peer
host    all         all         127.0.0.1/32    scram-sha-256
hostssl all         admin       0.0.0.0/0       cert
```

**Recommended for Guinevere**: Use **auth_user** pattern — simple, centralizes auth in PostgreSQL, no need to sync userlist.txt when passwords change.

### 2.4 PostgreSQL Integration

**Steps to wire PgBouncer ↔ PostgreSQL**:

1. **Create the bouncer auth user in PostgreSQL**:

```sql
CREATE ROLE guinevere_bouncer WITH LOGIN PASSWORD 'bouncer-password';
-- Grant CONNECT on relevant databases
GRANT CONNECT ON DATABASE guinevere_db TO guinevere_bouncer;
```

2. **Add pg_hba.conf entry for PgBouncer** (see [1.6](#16-pg_hbaconf-security-hardening)):
```conf
host    all    guinevere_bouncer  127.0.0.1/32   scram-sha-256
```

3. **Verify connection**:
```bash
psql -h 127.0.0.1 -p 6432 -U guinevere_app -d guinevere_db
```

4. **Admin console**:
```bash
# Connect to PgBouncer admin
psql -h 127.0.0.1 -p 6432 -U guinevere_dba -d pgbouncer

-- Show pool stats
SHOW POOLS;
SHOW STATS;
SHOW CLIENTS;
SHOW SERVERS;

-- Pause/resume (drain connections before restart)
PAUSE;
RESUME;
```

**Integration checklist**:
- [ ] PgBouncer listens on `127.0.0.1:6432`, PostgreSQL on `127.0.0.1:5432`
- [ ] Application connection string points to port `6432` not `5432`
- [ ] `pool_mode = transaction` for web-app workloads
- [ ] `server_idle_timeout` lower than PostgreSQL's `idle_in_transaction_session_timeout`
- [ ] Monitor pool health: `SHOW POOLS` should not show `cl_waiting > 0`

---

## 3. Redis 7

### 3.1 Installation

**Installation**:

```bash
# Install from official Redis repository
curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/redis.list

sudo apt update
sudo apt install -y redis-server

# Verify
redis-server --version   # Should show >= 7.x
redis-cli ping           # Should return PONG
```

### 3.2 ACL Configuration

**Source**: [Redis ACL SETUSER docs](https://redis.io/docs/latest/commands/acl-setuser), [ACL categories](https://redis.io/docs/latest/commands/acl-cat).

**Recommended `/etc/redis/redis.conf` ACL section**:

```conf
# --- ACL Configuration ---
# Disable default user (no auth = no access)
user default off nopass

# Database administrator (full access)
user guinevere_dba on >dba-strong-password ~* &* +@all

# Application read-write (no dangerous ops)
user guinevere_app on >app-password ~* &* +@all -@dangerous -@admin -@slow

# Monitoring (read-only, no writes)
user guinevere_monitor on >monitor-password +@read +info +ping +slowlog|get
                                    +slowlog|len +command|info +cluster|info
                                    +client|list +memory|stats -@write -@dangerous

# Discord bot (specific key patterns)
user guinevere_discord on >discord-password ~discord:* ~cache:discord:*
                         +@all -@dangerous -@admin -@slow

# Pub/Sub only (no key access)
user guinevere_pubsub on >pubsub-password &guinevere:* +subscribe +publish +ping
```

**ACL rule reference**:
| Rule | Meaning |
|---|---|
| `on` | User is active |
| `off` | User is disabled |
| `>password` | Set password |
| `~pattern` | Allow key pattern (e.g., `~app:*`) |
| `&pattern` | Allow channel pattern |
| `+@all` | All commands |
| `-@dangerous` | Remove dangerous commands |
| `-@admin` | Remove admin commands |
| `reset` | Reset user to default |

**Available eviction policies** [source: Redis docs](https://redis.io/docs/latest/operate/rc/databases):
| Policy | Behavior |
|---|---|
| `noeviction` | Error on write when full |
| `allkeys-lru` | Evict LRU from all keys |
| `allkeys-lfu` | Evict LFU from all keys |
| `allkeys-random` | Evict random from all keys |
| `volatile-lru` | Evict LRU from keys with TTL |
| `volatile-lfu` | Evict LFU from keys with TTL |
| `volatile-ttl` | Evict shortest TTL first |

**Pitfalls**:
- Default user `on nopass` is a security hole — **always disable with `user default off`**
- `~*` (all keys) is permissive — use pattern-based keys like `~guinevere:*` when possible
- ACL changes require `CONFIG REWRITE` to persist across restarts

### 3.3 DB Separation

Redis instances are single-threaded. DB separation uses `SELECT` command:

**Assignments for Guinevere**:

| DB | Purpose | Example Keys |
|---|---|---|
| DB0 | Cache layer | `cache:session:*`, `cache:query:*` |
| DB1 | Discord bot state | `discord:guild:*`, `discord:user:*` |
| DB2 | Task queue (Celery/BullMQ) | `bull:task-queue:*` |
| DB3 | Rate limiting | `ratelimit:api:*`, `ratelimit:ws:*` |
| DB4 | Pub/Sub channels | `channel:notifications:*` |
| DB5 | Development/testing | `test:*` |

```conf
# redis.conf
databases 16               # Default: 16 logical databases (0-15)
```

```redis
# Connect to specific DB
redis-cli -n 0             # DB0 (cache)
redis-cli -a password -n 1 # DB1 (discord)
SELECT 2                   # Switch to DB2
```

**Note**: Redis 7 Cluster mode does NOT support multiple databases — only DB0 is available. For production Redis Cluster, use key prefixes instead (e.g., `cache:`, `discord:`, `queue:`). This is fine for a single-node dev/deployment.

### 3.4 Persistence (RDB vs AOF)

**Source**: Real-world configs from [frain-dev/convoy](https://github.com/frain-dev/convoy/blob/main/configs/local/conf/redis/redis.conf#L21) and [GoFilm](https://github.com/ProudMuBai/GoFilm/blob/main/film/data/redis/redis.conf#L20).

**Recommended hybrid persistence**:

```conf
# /etc/redis/redis.conf
# --- RDB Snapshots ---
save 900 1               # After 15 min if >= 1 key changed
save 300 10              # After 5 min if >= 10 keys changed
save 60 10000            # After 60 sec if >= 10000 keys changed
stop-writes-on-bgsave-error no  # Don't stop writing if snapshot fails
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir /var/lib/redis

# --- AOF (Append Only File) ---
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec      # Fsync once per second (best balance)
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb

# --- Hybrid (Redis 5+) ---
aof-use-rdb-preamble yes  # Use RDB format for AOF base + AOF for tail
```

**Persistence comparison**:
| Feature | RDB | AOF |
|---|---|---|
| Format | Binary snapshot | Append-only log |
| Restore speed | Fast | Slower (replay) |
| Data loss window | Minutes (between snapshots) | ≤ 1 second with `everysec` |
| File size | Compact | Larger (compacted periodically) |
| Use case | Backup, disaster recovery | Durability-critical |

**Recommendation**: Enable both with `aof-use-rdb-preamble yes` for the best of both worlds — fast startup from RDB-formatted AOF base.

### 3.5 Memory Limits & Eviction

```conf
# redis.conf
maxmemory 512mb
maxmemory-policy allkeys-lru     # Evict least recently used keys
maxmemory-samples 10              # LRU/LFU approximation accuracy
```

**Policy selection guide**:
- **Cache use case (default)**: `allkeys-lru` — evict least recently used
- **Session store**: `volatile-ttl` — let sessions expire naturally
- **Queue/rate limiter**: `noeviction` — never lose a queued task

**Monitoring**:
```redis
INFO memory
# Check: used_memory_human, maxmemory_human, evicted_keys
```

---

## 4. systemd Service Patterns

### 4.1 Service File Structure

**Source**: Apache Airflow [production systemd units](https://github.com/apache/airflow/blob/main/scripts/systemd/airflow-kerberos.service), [ONLYOFFICE](https://github.com/ONLYOFFICE/document-server-package/blob/master/common/documentserver/systemd/ds-metrics.service.m4).

All custom services go in `/etc/systemd/system/<name>.service`.

### 4.2 Restart Policies

| Policy | Behavior | Use Case |
|---|---|---|
| `Restart=always` | Always restart, even on clean exit | Critical services (PG, Redis, PgBouncer) |
| `Restart=on-failure` | Restart only on error exit | One-shot migrations, healthchecks |
| `Restart=on-abnormal` | Restart on signal/core dump | Long-running daemons |
| `RestartSec=5s` | Wait before restarting | Avoid tight crash loops |
| `StartLimitBurst=5` | Max restarts in period | Cap restart storms |
| `StartLimitIntervalSec=30s` | Reset window for StartLimitBurst | Prevents thrashing |

### 4.3 Environment Variables

Two methods:

**Method 1: EnvironmentFile (preferred for secrets)**:
```ini
[Service]
EnvironmentFile=/etc/guinevere/db.conf
# File content:
#   PGUSER=guinevere_app
#   PGPASSWORD=secret
```

**Method 2: Inline Environment**:
```ini
[Service]
Environment="REDIS_URL=redis://127.0.0.1:6379"
Environment="DISCORD_TOKEN=${DISCORD_TOKEN}"
```

### 4.4 Logging with journald

systemd captures stdout/stderr automatically. For structured logging:

```ini
[Service]
StandardOutput=journal
StandardError=journal
SyslogIdentifier=guinevere-postgres
```

**View logs**:
```bash
journalctl -u postgresql@16-main -f --since "10 min ago"
journalctl -u redis-server -n 100 --no-pager
```

### 4.5 Dependencies

Source patterns from [Apache Airflow](https://github.com/apache/airflow/blob/main/scripts/systemd/airflow-flower.service#L21-L22), [icinga2](https://github.com/Icinga/icinga2/blob/master/etc/initsystem/icinga2.service.cmake#L3-L4), [Nezha](https://github.com/midoks/mdserver-web/blob/master/plugins/nezha/init.d/nezha.service.tpl#L4-L6).

| Directive | Meaning |
|---|---|
| `After=network.target` | Start after network is up |
| `After=postgresql.service` | Order: PostgreSQL first |
| `Requires=postgresql.service` | Hard dependency (fail if PG down) |
| `Wants=redis.service` | Soft dependency (start if possible) |

**Full service examples for Guinevere**:

**PostgreSQL 16 service** (`guanevere-postgresql.service`):
```ini
[Unit]
Description=Guinevere PostgreSQL 16 Database
After=network.target local-fs.target

[Service]
Type=notify
User=postgres
Group=postgres
Environment="PGDATA=/var/lib/postgresql/16/main"
ExecStart=/usr/lib/postgresql/16/bin/pg_ctl start -D ${PGDATA} -s -w -t 300
ExecStop=/usr/lib/postgresql/16/bin/pg_ctl stop -D ${PGDATA} -s -m fast
ExecReload=/usr/lib/postgresql/16/bin/pg_ctl reload -D ${PGDATA} -s

Restart=always
RestartSec=5s
StartLimitBurst=5
StartLimitIntervalSec=60s

StandardOutput=journal
StandardError=journal
SyslogIdentifier=guinevere-postgres

LimitNOFILE=65536
LimitMEMLOCK=infinity

[Install]
WantedBy=multi-user.target
```

**Redis 7 service** (`guinevere-redis.service`):
```ini
[Unit]
Description=Guinevere Redis 7 In-Memory Store
After=network.target

[Service]
Type=notify
User=redis
Group=redis
ExecStart=/usr/bin/redis-server /etc/redis/redis.conf --supervised systemd
ExecStop=/usr/bin/redis-cli SHUTDOWN

Restart=always
RestartSec=5s
StartLimitBurst=5
StartLimitIntervalSec=60s

StandardOutput=journal
StandardError=journal
SyslogIdentifier=guinevere-redis

LimitNOFILE=10032
MemoryMax=768M  # Slightly above configured maxmemory

[Install]
WantedBy=multi-user.target
```

**PgBouncer service** (`guinevere-pgbouncer.service`):
```ini
[Unit]
Description=Guinevere PgBouncer Connection Pooler
After=network.target guinevere-postgresql.service
Requires=guinevere-postgresql.service

[Service]
Type=simple
User=postgres
Group=postgres
ExecStart=/usr/sbin/pgbouncer /etc/pgbouncer/pgbouncer.ini
ExecReload=/bin/kill -HUP $MAINPID
ExecStop=/bin/kill -INT $MAINPID

Restart=always
RestartSec=5s
StartLimitBurst=5
StartLimitIntervalSec=60s

StandardOutput=journal
StandardError=journal
SyslogIdentifier=guinevere-pgbouncer

LimitNOFILE=10240

[Install]
WantedBy=multi-user.target
```

**Activate services**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now guinevere-postgresql.service
sudo systemctl enable --now guinevere-redis.service
sudo systemctl enable --now guinevere-pgbouncer.service
```

---

## Quick Reference: Startup Order

The dependency chain for Guinevere:

```
network.target
    |
    v
guinevere-postgresql.service  (first — other services depend on it)
    |
    +---> guinevere-pgbouncer.service  (needs PostgreSQL alive)
    |
guinevere-redis.service       (independent — can start in parallel with PG)
```

**Verification script** (to run after all services are up):

```bash
# PostgreSQL
pg_isready -h 127.0.0.1 -p 5432 -U guinevere_dba

# PgBouncer
pg_isready -h 127.0.0.1 -p 6432 -U guinevere_app

# Redis
redis-cli -a app-password ping
```

---

## Common Pitfalls Across the Stack

| Pitfall | Symptom | Fix |
|---|---|---|
| PG listens only on localhost after install | Remote connection refused | Edit `postgresql.conf`: `listen_addresses = '*'`, then fix `pg_hba.conf` |
| scram-sha-256 with old PgBouncer (< 1.22) | `auth_type` not supported | Upgrade PgBouncer or use `md5` |
| Redis `maxmemory` set but `maxmemory-policy noeviction` | OOM errors on writes | Set `maxmemory-policy allkeys-lru` |
| `appendonly yes` without periodic rewrite | AOF file grows to GBs | Enable `auto-aof-rewrite-percentage 100` |
| systemd `Restart=always` + `StartLimitBurst` too low | Service stays dead after crash loop | Increase `StartLimitBurst` to 10 |
| `pool_mode=transaction` with prepared statements | `ERROR: prepared statement does not exist` | Use `pool_mode=session` for prepared statements |
| Redis default user left `on nopass` | Unauthenticated access | Set `user default off` in ACL |

---

## Source References

| Source | Type | Link |
|---|---|---|
| PostgreSQL 16 docs (shared_buffers) | Official docs | https://www.postgresql.org/docs/16/runtime-config-resource.html |
| PostgreSQL 16 release notes (performance) | Official docs | https://www.postgresql.org/docs/16/release-16.html |
| PostgreSQL APT repository | Wiki | https://wiki.postgresql.org/wiki/Apt |
| pgvector usage patterns | GitHub | https://github.com/genkit-ai/genkit/blob/main/go/samples/pgvector/pgvector.sql |
| TimescaleDB hypertable creation | GitHub | https://github.com/datahub-project/datahub/blob/master/metadata-ingestion/tests/integration/timescaledb/setup/setup.sql |
| FTS GIN index patterns | GitHub | https://github.com/laguagu/claude-code-nextjs-skills/blob/main/skills/postgres-semantic-search/scripts/indexes.sql |
| Role creation tests | GitHub | https://github.com/postgres/postgres/blob/master/src/test/regress/sql/roleattributes.sql |
| PgBouncer config format | GitHub | https://github.com/pgbouncer/pgbouncer/blob/master/doc/config.md |
| PgBouncer HBA auth | GitHub | https://github.com/pgbouncer/pgbouncer/blob/master/doc/usage.md |
| PgBouncer production config (Neon) | GitHub | https://github.com/neondatabase/neon/blob/main/compute/etc/pgbouncer.ini |
| PgBouncer helm template (Zalando) | GitHub | https://github.com/zalando/postgres-operator/blob/master/pooler/pgbouncer.ini.tmpl |
| Redis ACL SETUSER | Official docs | https://redis.io/docs/latest/commands/acl-setuser |
| Redis data eviction policies | Official docs | https://redis.io/docs/latest/operate/rc/databases |
| Redis ACL categories | Official docs | https://redis.io/docs/latest/commands/acl-cat |
| Redis production config | GitHub | https://github.com/frain-dev/convoy/blob/main/configs/local/conf/redis/redis.conf |
| systemd unit patterns (Airflow) | GitHub | https://github.com/apache/airflow/blob/main/scripts/systemd/airflow-flower.service |
| systemd unit patterns (Icinga2) | GitHub | https://github.com/Icinga/icinga2/blob/master/etc/initsystem/icinga2.service.cmake |

---

*Report compiled by Guinevere (librarian research agent) on 2026-05-31. Evidence sourced from official PostgreSQL/Redis/PgBouncer documentation and real-world open-source configurations.*