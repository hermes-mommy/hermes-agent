# External Research Report: PostgreSQL 16 Docker Deployment on Ubuntu 24.04

> **Audit Report**: STEP-P0-014 — PostgreSQL 16 Docker Container  
> **Date**: 2026-05-31  
> **Scope**: External reference for deploying PostgreSQL 16 via Docker on Ubuntu 24.04, port 5433, bind-mount data directory, guinevere-net bridge network, guinevere.slice cgroup isolation  
> **Downstream**: Safe deployment without touching Aizanta PostgreSQL on 5432

---

## Table of Contents

1. [Official PostgreSQL Docker Image — Tags, Variants, Multi-Arch](#1-official-postgresql-docker-image--tags-variants-multi-arch)
2. [Docker Run / Docker Compose Patterns](#2-docker-run--docker-compose-patterns)
3. [Data Directory Permissions — Bind Mount with UID 999](#3-data-directory-permissions--bind-mount-with-uid-999)
4. [Initial Configuration — POSTGRES_PASSWORD, DB, USER](#4-initial-configuration)
5. [postgresql.conf — Tuning for 8 GB / 2 Core VPS](#5-postgresqlconf--tuning-for-8-gb--2-core-vps)
6. [pg_hba.conf — hostssl, scram-sha-256](#6-pg_hbaconf--hostssl-scram-sha-256)
7. [PostgreSQL 16 + pgvector 0.7.0+ Compatibility](#7-postgresql-16--pgvector-070-compatibility)
8. [PostgreSQL 16 + TimescaleDB 2.15 Compatibility](#8-postgresql-16--timescaledb-215-compatibility)
9. [pgvector + TimescaleDB in Same Instance](#9-pgvector--timescaledb-in-same-instance)
10. [Shared VPS Isolation — Port, Network, Cgroups](#10-shared-vps-isolation)
11. [Healthcheck with pg_isready](#11-healthcheck-with-pg_isready)
12. [Volume / Persistence Best Practices](#12-volume--persistence-best-practices)
13. [Backup Considerations — pg_dump, pg_basebackup](#13-backup-considerations)
14. [Recommended Implementation Plan](#14-recommended-implementation-plan)
15. [References](#15-references)

---

## 1. Official PostgreSQL Docker Image — Tags, Variants, Multi-Arch

### Latest PostgreSQL 16 Tags (as of May 2026)

From the [official Docker Hub `postgres` tags](https://hub.docker.com/_/postgres/tags) and the [docker-library/official-images manifest](https://github.com/docker-library/official-images/blob/master/library/postgres):

| Tag | Base OS | Arch Support | Size | Notes |
|-----|---------|-------------|------|-------|
| `16.14`, `16`, `16.14-trixie`, `16-trixie` | Debian Trixie (slim) | amd64, arm64, ppc64el (binary); s390x, riscv64 (source) | ~200 MB | **Recommended for production** |
| `16.14-alpine3.23`, `16-alpine3.23`, `16.14-alpine`, `16-alpine` | Alpine 3.23 | amd64, arm32v6, arm32v7, arm64v8, i386, ppc64le, riscv64, s390x | ~90 MB | Smaller, but extensions need compilation |
| `16.14-alpine3.22`, `16-alpine3.22` | Alpine 3.22 | Same as above | ~90 MB | Older Alpine, fewer package issues |

**Key findings:**

- **Current PG 16 version**: `16.14` as of May 2026 (Debian Trixie packages: `16.12`). The official image is at `16.14` based on Debian Trixie slim.
- **Multi-arch**: Debian variants use binary packages for amd64/arm64/ppc64el; source build for s390x/riscv64. Alpine always compiles from source.
- **Alpine caveat**: Extensions not in `postgres-contrib` must be compiled in a custom image. The Alpine variant also uses musl libc which can cause locale issues (PG 15+ Alpine supports ICU locales, so this is mitigated).
- **Debian advantage**: Extensions like PostGIS, pgvector can be installed via `apt-get`; the base image already includes `apt.postgresql.org` repos.

**Recommendation**: Use **`postgres:16-trixie`** (Debian Trixie slim) for maximum extension compatibility and easier package management. Use Alpine only if image size is a critical constraint.

---

## 2. Docker Run / Docker Compose Patterns

### Docker Run — Direct

```bash
# Create network
docker network create guinevere-net

# Pull image
docker pull postgres:16-trixie

# Run container
docker run -d \
  --name guinevere-postgres \
  --network guinevere-net \
  --restart unless-stopped \
  -p 127.0.0.1:5433:5432 \
  -e POSTGRES_PASSWORD_FILE=/run/secrets/db_password \
  -e POSTGRES_USER=guinevere \
  -e POSTGRES_DB=guinevere \
  -e PGDATA=/var/lib/postgresql/data/pgdata \
  -e TZ=Asia/Bangkok \
  -v /home/guinevere/data/postgres:/var/lib/postgresql/data \
  -v /etc/localtime:/etc/localtime:ro \
  --shm-size=256m \
  --memory=4g \
  --cpus=2 \
  postgres:16-trixie
```

**Key points**:
- Port mapping `127.0.0.1:5433:5432` binds only to localhost, avoiding public exposure. (Source: [Docker PostgreSQL networking guide](https://docs.docker.com/guides/postgresql/networking-and-connectivity/))
- `--restart unless-stopped` ensures auto-restart on crash or host reboot.
- `--shm-size=256m` required for parallel query execution and HNSW index builds (pgvector requirement).
- `TZ=Asia/Bangkok` sets the container timezone.

### Docker Compose — Production Baseline

```yaml
services:
  postgres:
    image: postgres:16-trixie
    container_name: guinevere-postgres
    restart: unless-stopped
    shm_size: 256m
    environment:
      POSTGRES_USER: guinevere
      POSTGRES_DB: guinevere
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
      TZ: Asia/Bangkok
    ports:
      - "127.0.0.1:5433:5432"
    volumes:
      - guinevere_postgres_data:/var/lib/postgresql/data
      - ./postgresql.conf:/etc/postgresql/postgresql.conf:ro
      - ./pg_hba.conf:/etc/postgresql/pg_hba.conf:ro
      - /etc/localtime:/etc/localtime:ro
    networks:
      - guinevere-net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U guinevere -d guinevere"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
    command: >
      postgres
        -c config_file=/etc/postgresql/postgresql.conf
        -c hba_file=/etc/postgresql/pg_hba.conf

volumes:
  guinevere_postgres_data:
    driver: local

networks:
  guinevere-net:
    driver: bridge
```

(Sources: [Docker PostgreSQL advanced config guide](https://docs.docker.com/guides/postgresql/advanced-configuration-and-initialization/), [OneUptime production config](https://oneuptime.com/blog/post/2026-01-21-postgresql-docker-compose/view))

**Important note for PG 16 (below 18)**: Mount at `/var/lib/postgresql/data` not `/var/lib/postgresql` because the Dockerfile declares a `VOLUME` at the former. Mounting the parent path will cause data loss on container re-creation. (Source: [docker-library/postgres README](https://github.com/docker-library/docs/blob/master/postgres/README.md))

---

## 3. Data Directory Permissions — Bind Mount with UID 999

### The UID 999 Problem

Inside the official PostgreSQL Docker image, the `postgres` user has **UID 999** and **GID 999**. This is hardcoded in the Dockerfile:

```dockerfile
RUN groupadd -r postgres --gid 999
RUN useradd -r -g postgres --uid 999 --home-dir=/var/lib/postgresql ...
```

(Source: [docker-library/postgres Dockerfile-debian.template, lines 5-10](https://github.com/docker-library/postgres/blob/66da3846b40396249936938ee17e9684e6968a57/Dockerfile-debian.template#L5-L10))

When using a **bind mount** (host directory mapped into container), the host directory must be owned by UID 999 for PostgreSQL to write to it. Otherwise, you get:

```
FATAL: data directory "/var/lib/postgresql/data" has wrong ownership
```

### Solution 1: Named Volume (Recommended)

Use a Docker named volume instead of a bind mount. Docker manages ownership automatically:

```yaml
volumes:
  - guinevere_postgres_data:/var/lib/postgresql/data
```

Docker named volumes are the **recommended approach** by the official image maintainers. (Source: [docker-library/postgres README - Where to Store Data](https://github.com/docker-library/docs/blob/master/postgres/README.md))

### Solution 2: Bind Mount with Pre-set Ownership

If you must use the bind mount at `/home/guinevere/data/postgres`:

```bash
# Create directory
sudo mkdir -p /home/guinevere/data/postgres

# Set ownership to UID 999 (postgres inside container)
sudo chown -R 999:999 /home/guinevere/data/postgres

# Set permissions
sudo chmod 700 /home/guinevere/data/postgres

# Verify
ls -lna /home/guinevere/data/postgres
# Should show: drwx------ 2 999 999 ...
```

> **Warning**: UID 999 on the host may conflict with other system users (e.g., `systemd-coredump` on Debian/Ubuntu). Check with `getent passwd 999` before proceeding.

### Solution 3: Use `--user` and NSS Wrapper

Since PR [#1018](https://github.com/docker-library/postgres/pull/1018), the Alpine variant supports NSS Wrapper, allowing the container to run as an arbitrary `--user`:

```bash
# Create directory with host user ownership
mkdir -p /home/guinevere/data/postgres
chown -R $(id -u):$(id -g) /home/guinevere/data/postgres

# Run container with the same UID
docker run --user $(id -u):$(id-g) ...
```

The entrypoint script uses `nss_wrapper` to fake `/etc/passwd` entries for arbitrary UIDs. (Source: [docker-entrypoint.sh](https://github.com/docker-library/postgres/blob/74e51d102aede/docker-entrypoint.sh), lines 93-108)

### Solution 4: Chown via Ephemeral Container

If the directory already exists with the wrong owner:

```bash
docker run --rm \
  -v /home/guinevere/data/postgres:/var/lib/postgresql/data \
  --entrypoint /bin/chown \
  postgres:16-trixie \
  -Rc postgres:postgres /var/lib/postgresql/data
```

(Source: [docker-library/postgres issue #1010](https://github.com/docker-library/postgres/issues/1010))

**Recommendation**: Use named volumes for simplicity. If bind mount is required (e.g., for direct filesystem backup access), create the directory with `chown 999:999` before first startup.

---

## 4. Initial Configuration

### Environment Variables

| Variable | Required | Default | Value for Guinevere | Notes |
|----------|----------|---------|--------------------|-------|
| `POSTGRES_PASSWORD` | Yes (or `_FILE`) | — | Use secret file | Set via `_FILE` for security |
| `POSTGRES_USER` | No | `postgres` | `guinevere` | Per ADR-031 |
| `POSTGRES_DB` | No | Same as user | `guinevere` | Per ADR-031 |
| `PGDATA` | No | `/var/lib/postgresql/data` | Keep default for PG 16 | For PG 16, keep `/var/lib/postgresql/data` |
| `POSTGRES_HOST_AUTH_METHOD` | No | `scram-sha-256` | Keep default | Already secure for PG 16 |
| `POSTGRES_INITDB_ARGS` | No | — | `--encoding=UTF8 --lc-collate=en_US.UTF-8 --lc-ctype=en_US.UTF-8` | Locale init args |
| `TZ` | No | UTC | `Asia/Bangkok` | Server timezone |

### Using Docker Secrets (Production)

Instead of plaintext `POSTGRES_PASSWORD` in compose, use `POSTGRES_PASSWORD_FILE`:

```yaml
secrets:
  db_password:
    file: ./secrets/db_password.txt

services:
  postgres:
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    secrets:
      - db_password
```

The entrypoint script reads the file and uses its content as the password. This keeps credentials out of environment variables exposed via `docker inspect`. (Source: [docker-library/postgres entrypoint.sh](https://github.com/docker-library/postgres/blob/74e51d102aede/docker-entrypoint.sh), uses `file_env` function)

### Initialization Scripts

Place `.sql` or `.sh` files in `/docker-entrypoint-initdb.d/` to run on first database initialization:

```yaml
volumes:
  - ./init-scripts:/docker-entrypoint-initdb.d
```

Example `init.sql`:
```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS vector;
```

These run only when the data directory is empty. (Source: [Docker PostgreSQL advanced init guide](https://docs.docker.com/guides/postgresql/advanced-configuration-and-initialization/))

---

## 5. postgresql.conf — Tuning for 8 GB / 2 Core VPS

### Container vs Host Memory

> **Critical**: Always set container memory limits (`--memory=4g`) and tune PostgreSQL parameters relative to the container limit, NOT the host total. Without limits, PostgreSQL sees the host's 8 GB and may overallocate.

**Container budget**: 4 GB memory limit, 2 CPU cores

| Parameter | Recommended Value | Formula | Notes |
|-----------|------------------|---------|-------|
| `shared_buffers` | **1 GB** | 25% of container memory | PostgreSQL's page cache |
| `effective_cache_size` | **3 GB** | 75% of container memory | Planner hint, not allocation |
| `work_mem` | **16 MB** | Conservative per-query | 4 concurrent queries × 16 MB × 2 sort nodes = 128 MB peak |
| `maintenance_work_mem` | **256 MB** | Autovacuum, CREATE INDEX | Keep under 512 MB to avoid OOM |
| `wal_buffers` | **16 MB** | Auto-tunes, but pin it | WAL write buffer |
| `max_connections` | **50** | Conservative with pooler | Reduce if using PgBouncer |
| `random_page_cost` | **1.1** | SSD optimization | Default 4.0 is for HDD |
| `effective_io_concurrency` | **200** | SSD optimization | Parallel I/O requests |
| `checkpoint_completion_target` | **0.9** | Spread write load | Reduces I/O spikes |
| `max_wal_size` | **2 GB** | Upper WAL limit | Monitor disk space |
| `min_wal_size` | **256 MB** | Lower WAL limit | — |
| `synchronous_commit` | `on` | Data safety | Consider `off` for performance |
| `huge_pages` | `try` | Large memory pages | Requires host hugetlbfs config for `on` |

### Full postgresql.conf Snippet for Container

```ini
# Memory (container limit: 4 GB)
shared_buffers = 1GB
effective_cache_size = 3GB
work_mem = 16MB
maintenance_work_mem = 256MB
wal_buffers = 16MB
huge_pages = try

# Connections
max_connections = 50

# Storage (SSD)
random_page_cost = 1.1
effective_io_concurrency = 200

# WAL
wal_level = replica
synchronous_commit = on
max_wal_size = 2GB
min_wal_size = 256MB
checkpoint_completion_target = 0.9

# Autovacuum
autovacuum_vacuum_threshold = 50
autovacuum_vacuum_cost_limit = 200

# Monitoring
shared_preload_libraries = 'pg_stat_statements'
track_io_timing = on

# Timezone
timezone = 'Asia/Bangkok'
```

**Sources**:
- [Docker PostgreSQL advanced config](https://docs.docker.com/guides/postgresql/advanced-configuration-and-initialization/) — official 25% shared_buffers guidance
- [HostMyCode PostgreSQL tuning 2026](https://www.hostmycode.com/tutorials/postgresql-memory-configuration-tutorial-buffer-pool-work-memory-optimization-linux-vps-2026) — 8 GB VPS values
- [MonPG memory tuning guide](https://monpg.app/blog/postgresql-memory-tuning) — shared_buffers 25% rule
- [RDP.sh PostgreSQL tuning walkthrough](https://rdp.sh/en/blog/postgresql-tuning-for-a-small-vps-a-practical-walkthrough) — small VPS practical guide

### Mounting Custom Config

```yaml
volumes:
  - ./postgresql.conf:/etc/postgresql/postgresql.conf:ro
command: postgres -c config_file=/etc/postgresql/postgresql.conf
```

---

## 6. pg_hba.conf — hostssl, scram-sha-256

### Default Behavior

In PostgreSQL 16+, if `POSTGRES_HOST_AUTH_METHOD` is not set, the image uses `scram-sha-256` by default. The entrypoint generates:

```
echo "host all all all scram-sha-256" >> pg_hba.conf
```

(Source: [Docker Hub postgres - POSTGRES_HOST_AUTH_METHOD](https://hub.docker.com/_/postgres))

### Recommended pg_hba.conf for Guinevere

```conf
# TYPE  DATABASE   USER       ADDRESS        METHOD

# Local Unix socket
local   all        postgres                   peer
local   all        all                        scram-sha-256

# Local TCP (IPv4)
host    all        all        127.0.0.1/32    scram-sha-256

# Local TCP (IPv6)
host    all        all        ::1/128         scram-sha-256

# Guinevere app container (internal Docker network)
hostssl guinevere  guinevere  172.0.0.0/8    scram-sha-256

# Reject everything else
hostssl all        all        0.0.0.0/0       reject
```

**Key points**:
- `hostssl` requires SSL/TLS encryption — non-SSL connections are rejected.
- `scram-sha-256` is the strongest password-based authentication method in PG 16.
- The `reject` catch-all at the bottom ensures no unintended access.
- Mount via `-c hba_file=/etc/postgresql/pg_hba.conf`.

### Generating SSL Certificates (if needed)

```bash
# Self-signed for internal Docker network
openssl req -new -text -nodes -subj '/CN=guinevere' \
  -keyout server.key -out server.csr
openssl x509 -req -in server.csr -text -days 365 \
  -signkey server.key -out server.crt
chmod 600 server.key
chown 999:999 server.key server.crt
```

(Sources: [PostgreSQL 16 pg_hba.conf docs](https://postgrespro.com/docs/postgresql/16/auth-pg-hba-conf.html), [StackHarden PostgreSQL hardening](https://stackharden.com/guides/postgresql-hardening/))

---

## 7. PostgreSQL 16 + pgvector 0.7.0+ Compatibility

### Available Docker Images

The [pgvector Docker Hub](https://hub.docker.com/r/pgvector/pgvector/tags) provides pre-built images:

| Tag | pgvector Version | PostgreSQL | Base OS | Use Case |
|-----|-----------------|-----------|---------|----------|
| `pgvector/pgvector:pg16` | Latest | 16 | Debian Trixie | General purpose |
| `pgvector/pgvector:0.8.2-pg16` | 0.8.2 pinned | 16 | Debian Trixie | **Recommended for production** |
| `pgvector/pgvector:0.8.2-pg16-trixie` | 0.8.2 pinned | 16 | Debian Trixie | Explicit base |
| `pgvector/pgvector:0.8.2-pg16-bookworm` | 0.8.2 pinned | 16 | Debian Bookworm | Older base |
| `pgvector/pgvector:pg16-trixie` | Latest | 16 | Debian Trixie | Rolling |
| `pgvector/pgvector:pg16-bookworm` | Latest | 16 | Debian Bookworm | Rolling |

**Current versions** (as of May 2026):
- pgvector: **0.8.2** is the latest stable release.
- pgvector 0.7.0 was released in February 2024 and is now two major versions behind.
- PostgreSQL 16 + pgvector 0.8.x is fully compatible and production-proven.

(Source: [pgvector GitHub README](https://github.com/pgvector/pgvector))

### Using pgvector Image

```yaml
services:
  postgres:
    image: pgvector/pgvector:0.8.2-pg16
    environment:
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: guinevere
      POSTGRES_USER: guinevere
    # All other settings (ports, volumes, healthcheck) are identical
    # to the official postgres:16 image
```

Then enable in SQL:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

**Compatibility**: PostgreSQL 16 + pgvector 0.7.x, 0.8.x are fully compatible. pgvector requires PostgreSQL 12+. (Source: [pgvector install docs](https://github.com/pgvector/pgvector))

**Note for HNSW indexes**: Set `--shm-size` large enough for parallel HNSW builds (at least 256 MB, or match `maintenance_work_mem`). ([pgvector README](https://github.com/pgvector/pgvector))

---

## 8. PostgreSQL 16 + TimescaleDB 2.15 Compatibility

### Available Docker Images

The [TimescaleDB Docker Hub](https://hub.docker.com/r/timescale/timescaledb/tags) provides pre-built images:

| Tag | TimescaleDB | PostgreSQL | Notes |
|-----|-------------|-----------|-------|
| `timescale/timescaledb:latest-pg16` | Latest 2.27.x | 16 | Rolling, production-proven |
| `timescale/timescaledb:2.27.0-pg16` | 2.27.0 pinned | 16 | **Recommended** |
| `timescale/timescaledb:2.26.4-pg16` | 2.26.4 pinned | 16 | Previous stable |
| `timescale/timescaledb:2.15.2-pg16` | 2.15.2 pinned | 16 | Historical — available on Hub |
| `timescale/timescaledb:latest-pg16-oss` | Latest OSS | 16 | Open-source-only version |
| `timescale/timescaledb:2.27.0-pg16-oss` | 2.27.0 OSS | 16 | Pinned OSS |

### Version Compatibility Matrix (from [Tiger Data docs](https://www.tigerdata.com/docs/deploy/self-hosted/upgrades/upgrade-pg))

| TimescaleDB | PG 18 | PG 17 | PG 16 | PG 15 | PG 14- |
|-------------|-------|-------|-------|-------|--------|
| 2.27.x | ✅ | ✅ | ✅ | ✅ | ❌ |
| 2.26.x | ✅ | ✅ | ✅ | ✅ | ❌ |
| 2.25.x | ✅ | ✅ | ✅ | ✅ | ❌ |
| 2.24.x | ✅ | ✅ | ✅ | ✅ | ❌ |
| 2.23.x | ✅ | ✅ | ✅ | ✅ | ❌ |
| 2.22.x | ❌ | ✅ | ✅ | ✅ | ❌ |
| 2.15.x | ❌ | ❌ | ✅ | ✅ | ✅ |
| 2.13.x | ❌ | ❌ | ✅ | ✅ | ✅ |

**Key findings**:
- TimescaleDB 2.15.x is compatible with PG 16, but the current stable is **2.27.x**.
- Use `timescale/timescaledb:2.27.0-pg16` for the latest stable release.
- The OSS variant excludes TimescaleDB-licensed features (compression policies, etc.) — use the standard image for full functionality.
- The image inherits all settings from the official `postgres:16` image — environment variables, volumes, healthchecks all work identically.

(Source: [TimescaleDB Docker Hub](https://hub.docker.com/r/timescale/timescaledb))

---

## 9. pgvector + TimescaleDB in Same Instance

### The Problem

Neither `pgvector/pgvector` nor `timescale/timescaledb` ships the other extension. The official TimescaleDB image **does not bundle pgvector** (confirmed in [TimescaleDB issue #8895](https://github.com/timescale/timescaledb/issues/8895): "The pgvector extension is not part of timescaledb").

### Solution Options

#### Option A: Custom Docker Image (Recommended)

Build a custom image starting from `postgres:16-trixie` and install both extensions:

```dockerfile
FROM postgres:16-trixie

# Install TimescaleDB from official apt repo
RUN apt-get update && apt-get install -y --no-install-recommends \
        gnupg \
        curl \
    && curl -s https://packagecloud.io/timescale/timescaledb/gpgkey | gpg --dearmor -o /usr/share/keyrings/timescaledb.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/timescaledb.gpg] https://packagecloud.io/timescale/timescaledb/ubuntu/ noble main" > /etc/apt/sources.list.d/timescaledb.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        timescaledb-2-postgresql-16 \
        postgresql-16-pgvector \
    && rm -rf /var/lib/apt/lists/*

# Preload TimescaleDB
RUN echo "shared_preload_libraries = 'timescaledb'" >> /usr/share/postgresql/postgresql.conf.sample

# No ENTRYPOINT change needed — inherits from postgres:16
```

Build and tag:
```bash
docker build -t guinevere-postgres:16-pgvector-timescaledb .
```

#### Option B: Use Community Images

Multiple community images exist on Docker Hub:
- `sforcedocker/pgvectortimescale` — PG 17.3, pgvector 0.8.0, TimescaleDB 2.19.0-dev ([Docker Hub](https://hub.docker.com/r/sforcedocker/pgvectortimescale))
- `chrismervyn/posgtres-pgvector-timescaledb:16` — PG 16, TimescaleDB 2, pgvector ([Docker Hub](https://hub.docker.com/r/chrismervyn/posgtres-pgvector-timescaledb))

**Warning**: Community images may not be maintained. Option A is safer for production.

#### Option C: Install Extensions Separately (via init script)

If using the standard `postgres:16-trixie` image, add init scripts:

```yaml
services:
  postgres:
    image: postgres:16-trixie
    volumes:
      - ./init-extensions:/docker-entrypoint-initdb.d
```

`init-extensions/01-install-extensions.sh`:
```bash
#!/bin/bash
set -e

# Install pgvector and TimescaleDB
apt-get update
apt-get install -y --no-install-recommends \
    postgresql-16-pgvector \
    timescaledb-2-postgresql-16

# Enable TimescaleDB in shared_preload_libraries
echo "shared_preload_libraries = 'timescaledb'" >> "${PGDATA}/postgresql.conf"
```

**Recommendation**: Use **Option A** (custom Dockerfile) for reproducibility and production safety.

---

## 10. Shared VPS Isolation

### Port Conflict Prevention

Aizanta PostgreSQL runs on **5432**. Guinevere uses **5433**.

```bash
# Verify port is free BEFORE deployment
ss -tlnp | grep :5433
# or
netstat -tlnp | grep :5433

# Bind only to localhost for additional safety
# Docker: -p 127.0.0.1:5433:5432
# Compose: ports: - "127.0.0.1:5433:5432"
```

Binding to `127.0.0.1` prevents external network access. This is the recommended production pattern. (Source: [Docker PostgreSQL networking guide](https://docs.docker.com/guides/postgresql/networking-and-connectivity/))

### Network Isolation — guinevere-net

```bash
# Create dedicated bridge network
docker network create guinevere-net \
  --driver bridge \
  --subnet 172.28.0.0/16 \
  --ip-range 172.28.5.0/24 \
  --label project=guinevere

# Run container on this network
docker run ... --network guinevere-net ...

# Verify no other containers share this network
docker network inspect guinevere-net
```

**Isolation benefits**:
- Automatic DNS resolution between containers on the same network.
- Containers on other networks (including Aizanta's) cannot reach Guinevere's PostgreSQL.
- No port exposure to the host is needed for inter-container communication — the network handles it internally.

(Sources: [Docker networking docs](https://docs.docker.com/guides/postgresql/networking-and-connectivity/), [AI VOID secure networking guide](https://aivoid.dev/docker-compose-prod-stack-2026/establishing-secure-inter-service-networking/))

### Cgroup Resource Limits — guinevere.slice

Systemd slice configuration for host-level cgroup isolation:

```ini
# /etc/systemd/system/guinevere.slice
[Unit]
Description=Guinevere Services Slice
Before=slices.target

[Slice]
MemoryAccounting=true
MemoryMax=6G
MemoryHigh=5G
CPUAccounting=true
CPUQuota=50%
TasksMax=4096
```

Then enable:
```bash
sudo systemctl daemon-reload
sudo systemctl start guinevere.slice
```

**Docker-level limits** (in addition to systemd slice):

```bash
docker run \
  --memory=4g \
  --memory-reservation=2g \
  --cpus=2 \
  --cpuset-cpus=0,1 \
  --oom-kill-disable=false \
  ...
```

**Why both layers matter**:
- Docker cgroup limits prevent the container from starving other containers.
- Systemd `guinevere.slice` prevents all Guinevere services combined from starving Aizanta or system processes.
- cgroups v2 (default on Ubuntu 24.04) provides unified hierarchy for memory, CPU, and I/O accounting.

(Source: [Docker resource constraints](https://docs.docker.com/engine/containers/resource_constraints/), [Percona cgroup2 blog](https://www.percona.com/blog/controlling-resource-consumption-on-a-postgresql-server-using-linux-cgroup2/), [CYBERTEC cgroups guide](https://www.cybertec-postgresql.com/en/linux-cgroups-for-postgresql/))

### Summary Isolation Matrix

| Dimension | Aizanta PG | Guinevere PG | Isolation Mechanism |
|-----------|-----------|--------------|-------------------|
| Port | 5432 | 5433 | Separate port + localhost bind |
| Network | aizanta-net | guinevere-net | Separate Docker bridge |
| Data dir | /home/aizanta/... | /home/guinevere/... | Separate path |
| Container | aizanta-postgres | guinevere-postgres | Separate container |
| Cgroup | system.slice | guinevere.slice | systemd isolation |
| Memory limit | No explicit limit | 4 GB | Docker + systemd |
| CPU limit | No explicit limit | 2 cores | Docker + systemd |

---

## 11. Healthcheck with pg_isready

### Recommended Healthcheck

```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U guinevere -d guinevere"]
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 30s
```

### Critical: Why `-d guinevere` Matters

`pg_isready` without `-d` defaults to connecting to a database matching the username. If the healthcheck user differs from the default database, pg_isready may return healthy before the actual database is ready, or fail despite the database being operational.

```bash
# WRONG — may falsely succeed or fail
pg_isready -U guinevere

# CORRECT — explicitly checks the target database
pg_isready -U guinevere -d guinevere
```

(Sources: [DEV pg_isready healthcheck fix](https://dev.to/frio_16/fixing-fatal-database-does-not-exist-in-postgresql-docker-healthcheck-mistake-3il8), [Docker official PostgreSQL healthcheck discussion](https://github.com/docker-library/postgres/issues/1237))

### Caveat: `pg_isready` via Unix Socket During Init

The official entrypoint runs a temporary PostgreSQL server for initialization scripts. If the healthcheck uses only `pg_isready` (without `-h`), it connects via Unix socket to the initialization server and reports healthy before the real server is ready.

**Fix**: Use `-h 127.0.0.1` to force TCP connection:

```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -h 127.0.0.1 -U guinevere -d guinevere"]
```

(Source: [docker-library/postgres issue #880](https://github.com/docker-library/postgres/issues/880), tianon's comment: "If you do `pg_isready --host 127.0.0.1` it should do the 'right' thing")

### Docker Run Equivalent

```bash
docker run \
  --health-cmd="pg_isready -h 127.0.0.1 -U guinevere -d guinevere" \
  --health-interval=10s \
  --health-timeout=5s \
  --health-retries=5 \
  --health-start-period=30s \
  ...
```

### `depends_on` with `condition: service_healthy`

For dependent services:

```yaml
services:
  app:
    depends_on:
      postgres:
        condition: service_healthy
```

This ensures the app container only starts after PostgreSQL is confirmed accepting connections. (Source: [Docker compose healthcheck guide 2026](https://blog.dtio.app/2026/05/docker-compose-depends-on-health-checks-startup-readiness.html))

### pg_isready Return Codes

| Code | Meaning |
|------|---------|
| 0 | Server is accepting connections |
| 1 | Server is rejecting connections (e.g., during recovery) |
| 2 | Server is not running |
| 3 | No connection possible (e.g., connection refused) |

---

## 12. Volume / Persistence Best Practices

### Named Volume vs Bind Mount

| Aspect | Named Volume | Bind Mount |
|--------|-------------|------------|
| Permission mgmt | Docker manages | Manual chown 999:999 |
| Backup | `docker run --rm -v volume:/data ... tar` | Direct filesystem access |
| Portability | Docker-managed, portable | Host-path-dependent |
| Inspection | `docker volume inspect` | `ls -la /path` |
| Performance | Equivalent (both use overlay) | Equivalent |
| **Recommendation** | **Use for simplicity** | Use only if direct FS access needed |

### PostgreSQL 16 Volume Path

**Critical**: Mount at `/var/lib/postgresql/data`, NOT `/var/lib/postgresql`.

For PG 16 (and all versions below 18), the Dockerfile declares:
```dockerfile
VOLUME /var/lib/postgresql/data
```

Mounting at the parent path causes an anonymous volume to be created for `/var/lib/postgresql/data`, and data is written there instead of your intended mount. (Source: [docker-library docs README](https://github.com/docker-library/docs/blob/master/postgres/README.md))

### Volume Creation

```yaml
volumes:
  guinevere_postgres_data:
    driver: local
    # Optional: pin to host path
    # driver_opts:
    #   type: none
    #   device: /home/guinevere/data/postgres
    #   o: bind
```

### Verify Volume Contents

```bash
docker run --rm -it \
  -v guinevere_postgres_data:/data \
  alpine:latest ls -la /data
```

### Persistence Checklist

- [ ] Volume is mounted at `/var/lib/postgresql/data` (not parent)
- [ ] `restart: unless-stopped` is set
- [ ] No `docker compose down --volumes` used in production
- [ ] Volume backup procedure documented and tested
- [ ] Data directory permissions verified (UID 999 for bind mounts)

---

## 13. Backup Considerations

### Method 1: pg_dump (Logical Backup — Recommended for Daily)

**Simple backup command**:
```bash
docker exec -t guinevere-postgres \
  pg_dump -U guinevere -Fc guinevere > /backups/guinevere_$(date +%Y%m%d).dump
```

**Automated daily backup via cron**:
```bash
#!/bin/bash
# /usr/local/bin/backup-guinevere-pg.sh
BACKUP_DIR="/backups/guinevere/postgres"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

mkdir -p "$BACKUP_DIR"

# Logical backup in custom format (compressed, supports selective restore)
docker exec -t guinevere-postgres \
  pg_dump -U guinevere -Fc guinevere \
  | gzip > "${BACKUP_DIR}/guinevere_${TIMESTAMP}.dump.gz"

# Also dump pgvector-specific schemas if needed
docker exec -t guinevere-postgres \
  pg_dump -U guinevere -Fc -n vector guinevere \
  > "${BACKUP_DIR}/guinevere_vector_${TIMESTAMP}.dump"

# Rotate old backups
find "$BACKUP_DIR" -name "guinevere_*.dump.gz" -mtime +$RETENTION_DAYS -delete

# Verify backup integrity
docker run --rm -i \
  -v "$BACKUP_DIR":/backup \
  postgres:16-trixie \
  pg_restore --list /backup/guinevere_${TIMESTAMP}.dump.gz \
  > /dev/null 2>&1 && echo "Backup verified: $TIMESTAMP" || echo "Backup CORRUPT: $TIMESTAMP"
```

**Crontab entry**:
```cron
0 2 * * * /usr/local/bin/backup-guinevere-pg.sh
```

### Method 2: pg_basebackup (Physical Backup — for PITR)

Requires:
- `wal_level = replica` in postgresql.conf
- Replication slot or connection

```bash
# Initialize a base backup directory
mkdir -p /backups/guinevere/base

# Take physical backup via Docker exec
docker exec -t guinevere-postgres \
  pg_basebackup \
    -U guinevere \
    -D /tmp/guinevere-basebackup \
    -Ft -z -P -c fast
```

**Limitation**: `pg_basebackup` runs inside the container; output must be copied out:
```bash
docker cp guinevere-postgres:/tmp/guinevere-basebackup /backups/guinevere/base/
```

### Method 3: Volume Snapshot (for DR)

```bash
# Stop container for consistency
docker stop guinevere-postgres

# Backup the volume
docker run --rm \
  -v guinevere_postgres_data:/source:ro \
  -v /backups/guinevere/volume:/backup \
  alpine:latest \
  tar czf /backup/pgdata-$(date +%Y%m%d).tar.gz -C /source .

# Restart
docker start guinevere-postgres
```

### Recommended Strategy

| Backup Type | Frequency | Retention | Method | RPO | RTO |
|------------|-----------|-----------|--------|-----|-----|
| Logical (pg_dump -Fc) | Daily | 7 days | cron + Docker exec | 24 hours | 1-2 hours |
| Physical (volume) | Weekly | 4 weeks | Volume snapshot + tar | 1 week | 30 min |
| Streaming WAL | Continuous | Until base backup | Future: WAL-G or pgBackRest | Seconds | Minutes |

**Minimum viable**: Daily pg_dump with 7-day retention, tested monthly.

(Sources: [Docker PostgreSQL backup strategies](https://dev.to/piteradyson/postgresql-docker-backup-strategies-how-to-backup-postgresql-running-in-docker-containers-1bla), [OneUptime backup guide](https://oneuptime.com/blog/post/2026-02-08-how-to-create-a-full-docker-backup-strategy/view), [StackHarden PostgreSQL backups](https://stackharden.com/guides/postgres-backups/))

---

## 14. Recommended Implementation Plan

### Phase 1: Preparation

```bash
# 1. Create directory structure
sudo mkdir -p /home/guinevere/data/postgres
sudo mkdir -p /home/guinevere/config/postgres
mkdir -p /backups/guinevere/postgres

# 2. Set permissions (if using bind mount)
sudo chown -R 999:999 /home/guinevere/data/postgres
sudo chmod 700 /home/guinevere/data/postgres

# 3. Create Docker network
docker network create guinevere-net \
  --driver bridge \
  --subnet 172.28.0.0/16 \
  --ip-range 172.28.5.0/24 \
  --label project=guinevere

# 4. Verify port 5433 is free
ss -tlnp | grep :5433 || echo "Port 5433 is free"

# 5. Create config files
# postgresql.conf (from Section 5)
# pg_hba.conf (from Section 6)
```

### Phase 2: Deploy

```bash
# Using docker run
docker run -d \
  --name guinevere-postgres \
  --network guinevere-net \
  --restart unless-stopped \
  -p 127.0.0.1:5433:5432 \
  -e POSTGRES_USER=guinevere \
  -e POSTGRES_DB=guinevere \
  -e POSTGRES_PASSWORD_FILE=/run/secrets/db_password \
  -e TZ=Asia/Bangkok \
  -v /home/guinevere/data/postgres:/var/lib/postgresql/data \
  -v /home/guinevere/config/postgres/postgresql.conf:/etc/postgresql/postgresql.conf:ro \
  -v /home/guinevere/config/postgres/pg_hba.conf:/etc/postgresql/pg_hba.conf:ro \
  -v /etc/localtime:/etc/localtime:ro \
  -v /home/guinevere/secrets/db_password:/run/secrets/db_password:ro \
  --shm-size=256m \
  --memory=4g \
  --cpus=2 \
  --health-cmd="pg_isready -h 127.0.0.1 -U guinevere -d guinevere" \
  --health-interval=10s \
  --health-timeout=5s \
  --health-retries=5 \
  --health-start-period=30s \
  postgres:16-trixie \
  -c config_file=/etc/postgresql/postgresql.conf \
  -c hba_file=/etc/postgresql/pg_hba.conf
```

### Phase 3: Verify

```bash
# Check container status
docker ps --filter name=guinevere-postgres --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check health status
docker inspect --format='{{.State.Health.Status}}' guinevere-postgres

# Test connection from host
PGPASSWORD=$(cat /home/guinevere/secrets/db_password) \
  psql -h 127.0.0.1 -p 5433 -U guinevere -d guinevere -c "SELECT version();"

# Test from another container on same network
docker run --rm --network guinevere-net \
  postgres:16-trixie \
  psql -h guinevere-postgres -U guinevere -d guinevere -c "SELECT 1;"

# Verify port isolation
ss -tlnp | grep 5433  # Should show 127.0.0.1:5433 only

# Verify extensions (if installed)
docker exec guinevere-postgres \
  psql -U guinevere -d guinevere -c "SELECT * FROM pg_extension;"
```

---

## 15. References

### Official Documentation
- [Docker Hub — postgres official image](https://hub.docker.com/_/postgres)
- [docker-library/postgres GitHub](https://github.com/docker-library/postgres)
- [docker-library/postgres README](https://github.com/docker-library/docs/blob/master/postgres/README.md)
- [docker-entrypoint.sh](https://github.com/docker-library/postgres/blob/74e51d102aede/docker-entrypoint.sh)
- [PostgreSQL 16 pg_hba.conf docs](https://postgrespro.com/docs/postgresql/16/auth-pg-hba-conf.html)
- [PostgreSQL hardening guide](https://stackharden.com/guides/postgresql-hardening/)

### Docker Guides
- [Docker PostgreSQL networking](https://docs.docker.com/guides/postgresql/networking-and-connectivity/)
- [Docker PostgreSQL immediate setup](https://docs.docker.com/guides/postgresql/immediate-setup-and-data-persistence/)
- [Docker PostgreSQL advanced config](https://docs.docker.com/guides/postgresql/advanced-configuration-and-initialization/)
- [Docker resource constraints](https://docs.docker.com/engine/containers/resource_constraints/)

### Extensions
- [pgvector Docker Hub](https://hub.docker.com/r/pgvector/pgvector)
- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [TimescaleDB Docker Hub](https://hub.docker.com/r/timescale/timescaledb)
- [TimescaleDB version compatibility](https://www.tigerdata.com/docs/deploy/self-hosted/upgrades/upgrade-pg)

### Performance Tuning
- [Docker PostgreSQL memory tuning guidance](https://docs.docker.com/guides/postgresql/advanced-configuration-and-initialization/)
- [PostgreSQL memory tuning guide (HostMyCode)](https://www.hostmycode.com/tutorials/postgresql-memory-configuration-tutorial-buffer-pool-work-memory-optimization-linux-vps-2026)
- [MonPG memory tuning deep dive](https://monpg.app/blog/postgresql-memory-tuning)
- [RDP.sh small VPS tuning](https://rdp.sh/en/blog/postgresql-tuning-for-a-small-vps-a-practical-walkthrough)

### Security
- [PostgreSQL Docker security checklist (Dev.to)](https://dev.to/yash_pritwani_07a77613fd6/the-5-minute-docker-compose-security-checklist-we-run-for-every-client-a31)
- [Docker security best practices 2026 (ZeonEdge)](https://zeonedge.com/blog/docker-security-best-practices-2026-hardening-containers-build-runtime)

### Backup
- [Docker PostgreSQL backup strategies (Dev.to)](https://dev.to/piteradyson/postgresql-docker-backup-strategies-how-to-backup-postgresql-running-in-docker-containers-1bla)
- [PostgreSQL backup guide 2026](https://tutorials.technology/tutorials/postgresql-backup-restore-2026.html)
- [StackHarden PostgreSQL backups](https://stackharden.com/guides/postgres-backups/)

### Community References
- [docker-library/postgres issue #1010 — bind mount ownership](https://github.com/docker-library/postgres/issues/1010)
- [docker-library/postgres issue #1260 — UID 999 discussion](https://github.com/docker-library/postgres/issues/1260)
- [docker-library/postgres issue #1237 — HEALTHCHECK request](https://github.com/docker-library/postgres/issues/1237)
- [docker-library/postgres issue #880 — pg_isready timeout](https://github.com/docker-library/postgres/issues/880)
- [pgvector issue #903 — + TimescaleDB](https://github.com/pgvector/pgvector/issues/903)
- [TimescaleDB issue #8895 — pgvector missing](https://github.com/timescale/timescaledb/issues/8895)

---

*Report generated by Guinevere (Librarian agent) — 2026-05-31*
*Research sources include Docker Hub, GitHub, official PostgreSQL documentation, and community guides.*