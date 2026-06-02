# External Research Report: TimescaleDB Extension Installation — Docker PostgreSQL 16 on Ubuntu 24.04

> **Audit Report**: STEP-P0-016 — TimescaleDB 2.15 Extension Installation  
> **Date**: 2026-05-31  
> **Scope**: Safest way to add TimescaleDB 2.15 to the running `guinevere-postgres` Docker container (port 5433, `guinevere-net` bridge network) without affecting Aizanta PostgreSQL (port 5432).  
> **Downstream consumer**: P0-016 implementation step. Base container: `postgres:16-trixie` with pgvector pre-installed (from P0-015).

---

## Table of Contents

1. [Executive Summary: Two Viable Approaches](#1-executive-summary-two-viable-approaches)
2. [Approach A: Switch to Official TimescaleDB Docker Image](#2-approach-a-switch-to-official-timescaledb-docker-image)
3. [Approach B: Install TimescaleDB Inside Existing Container](#3-approach-b-install-timescaledb-inside-existing-container)
4. [shared_preload_libraries Configuration](#4-shared_preload_libraries-configuration)
5. [PostgreSQL Restart — Docker Safety](#5-postgresql-restart--docker-safety)
6. [TimescaleDB + pgvector Coexistence](#6-timescaledb--pgvector-coexistence)
7. [timescaledb-tune in Docker Environment](#7-timescaledb-tune-in-docker-environment)
8. [TimescaleDB 2.15 Apache-2 vs Community Edition](#8-timescaledb-215-apache-2-vs-community-edition)
9. [Docker Volume Persistence and Restart Safety](#9-docker-volume-persistence-and-restart-safety)
10. [Rollback Procedure](#10-rollback-procedure)
11. [Risk Assessment and Mitigation](#11-risk-assessment-and-mitigation)
12. [Recommended Implementation Plan for P0-016](#12-recommended-implementation-plan-for-p0-016)
13. [References](#13-references)

---

## 1. Executive Summary: Two Viable Approaches

There are two fundamentally different ways to add TimescaleDB 2.15 to the existing `guinevere-postgres` Docker container:

| Aspect | **Approach A** — Switch to Timescale Image | **Approach B** — Install Inside Container |
|--------|-------------------------------------------|-------------------------------------------|
| **Method** | Stop container, create new with `timescale/timescaledb:2.15.2-pg16`, reuse same volume | `apt install` inside existing container via `docker exec` |
| **Data safety** | ✅ Safe (same PG major version, same volume) | ✅ Safe (same container, same volume) |
| **pgvector** | ⚠️ `timescale/timescaledb` does NOT include pgvector; need `-ha` image or rebuild | ✅ pgvector already installed from P0-015 |
| **Simplicity** | Low — requires inspecting old volume, setting up new container | Medium — needs custom Dockerfile or persistent apt repo setup |
| **Reproducibility** | High — image is version-pinned | Low — apt install inside container is ephemeral unless baked into a new image |
| **Recommended** | ❌ **Not recommended** (pgvector conflict) | ✅ **Recommended** with custom Dockerfile |

**Final verdict**: Use **Approach B** with a custom Dockerfile that extends `postgres:16-trixie`, installs both TimescaleDB and pgvector at build time, and replaces the running container with the new image while reusing the same data volume. This gives reproducibility, data safety, and both extensions.

---

## 2. Approach A: Switch to Official TimescaleDB Docker Image

### 2.1 Available Docker Tags for TimescaleDB 2.15.x (PG 16)

From [Docker Hub — timescale/timescaledb tags](https://hub.docker.com/r/timescale/timescaledb/tags):

| Tag | TimescaleDB | PostgreSQL | Edition | Status |
|-----|-------------|-----------|---------|--------|
| `2.15.2-pg16` | 2.15.2 | 16 | Community (TSL) | ✅ Available |
| `2.15.2-pg16-oss` | 2.15.2 | 16 | Apache-2 (OSS) | ✅ Available |
| `2.15.1-pg16` | 2.15.1 | 16 | Community (TSL) | ✅ Available |
| `2.15.0-pg16` | 2.15.0 | 16 | Community (TSL) | ✅ Available |
| `latest-pg16` | Latest (2.27.x) | 16 | Community (TSL) | Available but not pinned |

**Key detail**: `2.15.2-pg16` is the latest 2.15.x patch for PG 16. The image is based on Alpine Linux, NOT Debian.

### 2.2 Data Safety Assessment — Switching Images

**Question**: Can I stop `guinevere-postgres` (running `postgres:16-trixie`) and start `timescale/timescaledb:2.15.2-pg16` with the same data volume without data loss?

**Answer: Yes, but with caveats.**

Both images are based on PostgreSQL 16 and the data directory format is identical. The TimescaleDB Docker image is based on Alpine Linux and uses the same data directory structure (`/var/lib/postgresql/data`).

**Critical difference**: The TimescaleDB Docker image uses **Alpine Linux** while `guinevere-postgres` uses **Debian Trixie**. This matters for:
- **pgvector**: The TimescaleDB image does NOT bundle pgvector (confirmed in [TimescaleDB issue #8895](https://github.com/timescale/timescaledb/issues/8895)). If you need pgvector (installed in P0-015), you lose it.
- **Extension binaries**: Alpine uses musl libc; Debian uses glibc. You cannot copy Debian-compiled `.so` files to Alpine. pgvector would need recompilation.
- **Tools**: Alpine uses `apk` instead of `apt`.

### 2.3 Migration Steps (if choosing this approach)

```bash
# 1. Inspect current volume
docker inspect guinevere-postgres --format='{{range .Mounts}}{{.Name}}{{end}}'
# Expected: guinevere_postgres_data or anonymous volume ID

# 2. Stop old container (does NOT delete volume)
docker stop guinevere-postgres

# 3. Pull TimescaleDB image
docker pull timescale/timescaledb:2.15.2-pg16

# 4. Start new container with SAME volume
docker run -d \
  --name guinevere-postgres \
  --network guinevere-net \
  --restart unless-stopped \
  -p 127.0.0.1:5433:5432 \
  -e POSTGRES_USER=guinevere \
  -e POSTGRES_DB=guinevere \
  -e POSTGRES_PASSWORD_FILE=/run/secrets/db_password \
  -e TZ=Asia/Bangkok \
  -v guinevere_postgres_data:/var/lib/postgresql/data \
  -v /home/guinevere/secrets/db_password:/run/secrets/db_password:ro \
  -v /home/guinevere/config/postgres/postgresql.conf:/etc/postgresql/postgresql.conf:ro \
  -v /etc/localtime:/etc/localtime:ro \
  --shm-size=256m \
  --memory=4g \
  --cpus=2 \
  timescale/timescaledb:2.15.2-pg16 \
  -c config_file=/etc/postgresql/postgresql.conf

# 5. Verify
docker logs guinevere-postgres --tail 20
docker exec guinevere-postgres psql -U guinevere -d guinevere -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"
```

### 2.4 Verdict

**Not recommended** due to pgvector incompatibility with the Alpine-based TimescaleDB image. If pgvector weren't needed, this would be the simplest approach. The `timescale/timescaledb-ha:pg16` image DOES include pgvector but is a very large image (~4 GB) and uses the HA setup with different data directory paths.

---

## 3. Approach B: Install TimescaleDB Inside Existing Container

### 3.1 The Container Environment

The existing `guinevere-postgres` uses `postgres:16-trixie` (Debian Trixie slim). TimescaleDB provides `.deb` packages for Debian/Ubuntu on their [packagecloud repository](https://packagecloud.io/timescale/timescaledb).

### 3.2 Option B1: Install at Runtime via docker exec (Quick but Ephemeral)

```bash
# Step 1: Enter the container and install TimescaleDB apt repo
docker exec -it guinevere-postgres /bin/bash -c "
  apt-get update && \
  apt-get install -y --no-install-recommends gnupg curl ca-certificates && \
  curl -s https://packagecloud.io/timescale/timescaledb/gpgkey | gpg --dearmor -o /usr/share/keyrings/timescaledb.gpg && \
  echo 'deb [signed-by=/usr/share/keyrings/timescaledb.gpg] https://packagecloud.io/timescale/timescaledb/ubuntu/ noble main' > /etc/apt/sources.list.d/timescaledb.list && \
  apt-get update && \
  apt-get install -y --no-install-recommends timescaledb-2-postgresql-16
"
```

> **Note**: The TimescaleDB Debian package (`timescaledb-2-postgresql-16`) installs to `/usr/lib/postgresql/16/lib/timescaledb.so` and `/usr/share/postgresql/16/extension/timescaledb*.control`. This works on Debian Trixie even though the repo targets Ubuntu Noble — both use glibc and the same PG extension API.

### 3.3 Option B2: Build a Custom Docker Image (Recommended)

**This is the recommended approach** because it is reproducible, testable, and the installed packages persist across container recreation.

```dockerfile
# Dockerfile — guinevere-postgres:16-pgvector-timescaledb
FROM postgres:16-trixie AS base

# Install TimescaleDB apt repository and packages
RUN apt-get update && apt-get install -y --no-install-recommends \
        gnupg \
        curl \
        ca-certificates \
    && curl -s https://packagecloud.io/timescale/timescaledb/gpgkey \
        | gpg --dearmor -o /usr/share/keyrings/timescaledb.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/timescaledb.gpg] https://packagecloud.io/timescale/timescaledb/ubuntu/ noble main" \
        > /etc/apt/sources.list.d/timescaledb.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        timescaledb-2-postgresql-16 \
        postgresql-16-pgvector \
    && rm -rf /var/lib/apt/lists/*

# Pre-configure shared_preload_libraries in the default postgresql.conf.sample
# This ensures it's included on first init (and any re-init that copies the sample)
RUN echo "shared_preload_libraries = 'timescaledb'" \
    >> /usr/share/postgresql/postgresql.conf.sample

# No ENTRYPOINT or CMD override needed — inherits from postgres:16
```

Build and tag:
```bash
docker build -t guinevere-postgres:16-pgvector-timescaledb .
```

Then update the running container:
```bash
# 1. Stop the old container (data volume persists)
docker stop guinevere-postgres

# 2. Remove the old container (NOT the volume)
docker rm guinevere-postgres

# 3. Start a new container with the same volume and new image
docker run -d \
  --name guinevere-postgres \
  --network guinevere-net \
  --restart unless-stopped \
  -p 127.0.0.1:5433:5432 \
  -e POSTGRES_USER=guinevere \
  -e POSTGRES_DB=guinevere \
  -e POSTGRES_PASSWORD_FILE=/run/secrets/db_password \
  -e TZ=Asia/Bangkok \
  -v guinevere_postgres_data:/var/lib/postgresql/data \
  -v /home/guinevere/secrets/db_password:/run/secrets/db_password:ro \
  -v /home/guinevere/config/postgres/postgresql.conf:/etc/postgresql/postgresql.conf:ro \
  -v /etc/localtime:/etc/localtime:ro \
  --shm-size=256m \
  --memory=4g \
  --cpus=2 \
  guinevere-postgres:16-pgvector-timescaledb \
  -c config_file=/etc/postgresql/postgresql.conf
```

**Data safety**: The data volume `guinevere_postgres_data` persists through `docker stop` and `docker rm`. Only `docker volume rm` deletes data. Reusing the same volume with the same PG major version (16) guarantees zero data loss.

### 3.4 Option B3: Use timescale/timescaledb-ha Image (Bundles pgvector)

The `timescale/timescaledb-ha:pg16` image bundles pgvector AND TimescaleDB. However:

- Very large image (~4 GB vs ~200 MB for postgres:16-trixie)
- Different data directory paths: `/home/postgres/pgdata/data` instead of `/var/lib/postgresql/data`
- Different UID/GID: uses `1000:1000` instead of `999:999`
- Requires `PGDATA` environment variable set explicitly

From [timescale/timescaledb-docker-ha issue #620](https://github.com/timescale/timescaledb-docker-ha/issues/620):

> The HA image requires volumes with `1000:1000` ownership (hardcoded postgres UID/GID).
> When using custom volume mounts, `PGDATA` must be explicitly set to match the mount point.

Migration would require:
```bash
# Create volume with correct permissions for HA image
docker run --rm \
  -v guinevere_postgres_data:/data \
  alpine:latest \
  sh -c "chown -R 1000:1000 /data && chmod -R 700 /data"
```

**Verdict**: Possible but riskier due to PGDATA path differences. Only consider if large image size is acceptable and the HA features are needed.

---

## 4. shared_preload_libraries Configuration

### 4.1 Why It's Required

TimescaleDB must be loaded at PostgreSQL startup because it allocates shared memory and registers background workers. From [PostgreSQL docs](https://postgresqlco.nf/doc/en/param/shared_preload_libraries/):

> This parameter can only be set at server start. If a specified library is not found, the server will fail to start.

The error when not preloaded:
```
FATAL: extension "timescaledb" must be preloaded
HINT: Please preload the timescaledb library via shared_preload_libraries.
```

### 4.2 Three Ways to Set It

#### Method 1: postgresql.conf (Persistent, survives container recreation)

Edit the config file (mounted as a volume or inside the container):

```ini
shared_preload_libraries = 'timescaledb'
```

If pg_stat_statements is also needed:
```ini
shared_preload_libraries = 'timescaledb,pg_stat_statements'
```

#### Method 2: ALTER SYSTEM SET (via psql, writes to postgresql.auto.conf)

This is the cleanest approach for Docker because it writes to `postgresql.auto.conf` inside the persistent data volume:

```sql
-- Check current value
SHOW shared_preload_libraries;

-- Append timescaledb (preserving existing libs)
ALTER SYSTEM SET shared_preload_libraries = 'timescaledb';

-- Then restart PostgreSQL
```

From [PostgreSQL ALTER SYSTEM docs](https://www.postgresql.org/docs/16/sql-altersystem.html):
> ALTER SYSTEM writes the given parameter setting to the `postgresql.auto.conf` file, which is read in addition to `postgresql.conf`. Settings in `postgresql.auto.conf` override those in `postgresql.conf`.

**Important**: `ALTER SYSTEM` cannot append to an existing value. You must specify the complete list. If pg_stat_statements is already in `shared_preload_libraries`:
```sql
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements,timescaledb';
```

#### Method 3: Docker command line (-c flag)

Pass the parameter directly on the Docker run command or in the Compose file:

```yaml
command: postgres -c shared_preload_libraries=timescaledb -c config_file=/etc/postgresql/postgresql.conf
```

```bash
docker run ... postgres:16-trixie \
  -c shared_preload_libraries=timescaledb \
  -c config_file=/etc/postgresql/postgresql.conf
```

**Caveat**: The `-c` flag **overrides** the setting in `postgresql.conf`. If both `postgresql.conf` and `-c` set the same parameter, the `-c` value wins. This is useful if you want to ensure `timescaledb` is loaded without editing config files.

### 4.3 Recommended Method for P0-016

Use **Method 3** (Docker command line) for the immediate implementation, combined with **Method 2** (ALTER SYSTEM) for persistence:

```
Step 1: docker stop guinevere-postgres
Step 2: docker start guinevere-postgres   # or docker run -c shared_preload_libraries=timescaledb
Step 3: psql -c "ALTER SYSTEM SET shared_preload_libraries = 'timescaledb';"
Step 4: docker restart guinevere-postgres
```

OR, for cleanest approach with the custom Dockerfile:
```dockerfile
RUN echo "shared_preload_libraries = 'timescaledb'" >> /usr/share/postgresql/postgresql.conf.sample
```
This ensures every new database initialization includes the setting.

### 4.4 Checking the Current Value

```sql
SHOW shared_preload_libraries;
```

To check if a restart is pending:
```sql
SELECT pending_restart FROM pg_settings WHERE name = 'shared_preload_libraries';
```

---

## 5. PostgreSQL Restart — Docker Safety

### 5.1 Does `docker restart` Pick Up Config Changes?

**Yes.** `docker restart guinevere-postgres` sends SIGTERM to the container's PID 1 (the PostgreSQL process), which performs a smart shutdown. When Docker starts the container again, the entrypoint runs and starts PostgreSQL, which reads the current configuration files.

This is documented in the official [TimescaleDB Docker config guide](https://github.com/timescale/docs/blob/latest/self-hosted/configuration/docker-config.md):

> 1. Start your Docker instance: `docker start timescaledb`
> 2. Open a shell: `docker exec -i -t timescaledb /bin/bash`
> 3. Open the configuration file in Vi editor: `vi /var/lib/postgresql/data/postgresql.conf`
> 4. Restart the container to reload the configuration: `docker restart timescaledb`

### 5.2 Restart Only Affects guinevere-postgres, Not Aizanta

This is the critical safety requirement for the shared VPS scenario:

```bash
# This ONLY restarts the guinevere-postgres container
docker restart guinevere-postgres

# Aizanta PostgreSQL on port 5432 is UNAFFECTED
```

The `docker restart` command operates on a single container. It does not affect other containers, host services, or processes in any way.

### 5.3 PostgreSQL Smart Shutdown in Docker

When `docker stop` or `docker restart` is sent to a PostgreSQL container:

1. Docker sends `SIGTERM` to PID 1 (the `postgres` master process)
2. PostgreSQL performs a **smart shutdown**: new connections are rejected, existing connections are allowed to finish, then a checkpoint runs
3. The `postgres` process exits cleanly
4. On restart, PostgreSQL replays WAL and recovers to a consistent state

**Risk**: If `docker stop --time=10` times out (10s default), Docker sends `SIGKILL`. This can cause a crash recovery on next start, which is safe but may take longer.

**For production safety**, use a longer stop timeout:

```bash
docker stop --time=120 guinevere-postgres
docker run ... --stop-timeout=120 ...
```

Or in Docker Compose:
```yaml
services:
  postgres:
    stop_grace_period: 2m
```

From [docker-library/postgres issue #1207](https://github.com/docker-library/postgres/issues/1207):
> You probably also want to set a much more generous `--stop-timeout` on your PostgreSQL containers — I usually use 120.

### 5.4 Restart Sequence for P0-016

```bash
# 1. Install TimescaleDB (either via custom image or docker exec)
# 2. Configure shared_preload_libraries
docker exec guinevere-postgres \
  psql -U guinevere -d guinevere \
  -c "ALTER SYSTEM SET shared_preload_libraries = 'timescaledb';"

# 3. Restart ONLY guinevere-postgres (Aizanta is unaffected)
docker restart guinevere-postgres

# 4. Wait for healthy
sleep 3
docker exec guinevere-postgres \
  psql -U guinevere -d guinevere \
  -c "SHOW shared_preload_libraries;"

# 5. Create the extension
docker exec guinevere-postgres \
  psql -U guinevere -d guinevere \
  -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"
```

---

## 6. TimescaleDB + pgvector Coexistence

### 6.1 Compatibility Confirmation

TimescaleDB 2.15 and pgvector 0.7.x/0.8.x are **fully compatible** on PostgreSQL 16. Both are PostgreSQL extensions that install to separate directories:

| Component | Install Path | shared_preload_libraries |
|-----------|-------------|--------------------------|
| TimescaleDB | `/usr/lib/postgresql/16/lib/timescaledb.so` | ✅ Required |
| pgvector | `/usr/lib/postgresql/16/lib/vector.so` | ❌ Not required |

TimescaleDB needs `shared_preload_libraries` because it allocates shared memory and background workers. pgvector does NOT need shared_preload_libraries — it loads on demand via `CREATE EXTENSION`.

### 6.2 Two Extensions in shared_preload_libraries

```sql
ALTER SYSTEM SET shared_preload_libraries = 'timescaledb,pg_stat_statements';
```

pgvector is intentionally NOT added to `shared_preload_libraries`. This is the standard practice.

### 6.3 Pgvectorscale Consideration

Timescale also offers [pgvectorscale](https://github.com/timescale/pgvectorscale), a DiskANN-based vector index that builds on pgvector. If needed in the future:

- Available in `timescale/timescaledb-ha` images (NOT in the standard `timescale/timescaledb` image)
- Can be installed separately via apt: `timescaledb-toolkit-postgresql-16`
- Adds `StreamingDiskANN` index type for large-scale vector search
- For datasets < 5-10 million vectors, pgvector's HNSW is sufficient

From [pgvectorscale docs](https://queryplane.com/docs/blog/scaling-vector-search-with-pgvectorscale):
> pgvectorscale builds on pgvector with higher performance embedding search and cost-efficient storage for AI applications.

### 6.4 Docker Image Recommendation

Since pgvector must coexist with TimescaleDB:

1. **Custom Dockerfile** (recommended): Base `postgres:16-trixie` with both `timescaledb-2-postgresql-16` and `postgresql-16-pgvector` installed via apt
2. **timescale/timescaledb-ha:pg16**: Has both bundled but is large (~4 GB) and uses different PGDATA paths
3. **Manual install via docker exec**: Works but is not reproducible

---

## 7. timescaledb-tune in Docker Environment

### 7.1 What timescaledb-tune Does

`timescaledb-tune` is a Go program that reads `postgresql.conf` and recommends optimal settings for:
- `shared_buffers`
- `effective_cache_size`
- `maintenance_work_mem`
- `work_mem`
- `max_worker_processes`
- `timescaledb.max_background_workers`

From [timescaledb-tune README](https://github.com/timescale/timescaledb-tune):
> It parses the existing `postgresql.conf` file to ensure that the TimescaleDB extension is appropriately installed and provides recommendations for memory, parallelism, WAL, and other settings.

### 7.2 Behavior on the Official TimescaleDB Docker Image

The `timescale/timescaledb` Docker image **automatically runs `timescaledb-tune` on first container initialization**. From the [timescaledb-docker README](https://github.com/timescale/timescaledb-docker):

> We run `timescaledb-tune` automatically on container initialization. By default, `timescaledb-tune` uses system calls to retrieve an instance's available CPU and memory. In docker images, these system calls reflect the available resources on the **host**.
>
> Therefore, this image looks in the cgroups metadata to determine the docker-defined limit sizes then passes those values to `timescaledb-tune`.

### 7.3 Disabling timescaledb-tune

If you're using a custom config and don't want `timescaledb-tune` to override it:

```bash
docker run -e NO_TS_TUNE=true ...
```

Or in Compose:
```yaml
environment:
  NO_TS_TUNE: "true"
```

### 7.4 Manual timescaledb-tune Inside Container

If installing via Option B (inside existing container), `timescaledb-tune` is installed as part of the `timescaledb-2-postgresql-16` package:

```bash
# Run with auto-confirm and quiet mode
timescaledb-tune --quiet --yes --conf-path="${PGDATA}/postgresql.conf"

# Dry-run to see what would change
timescaledb-tune --dry-run --conf-path="${PGDATA}/postgresql.conf"
```

### 7.5 Environment Variables for Tuning

When using the official TimescaleDB Docker image, you can control tuning with env vars:

| Variable | Purpose |
|----------|---------|
| `NO_TS_TUNE=true` | Disable auto-tuning entirely |
| `TS_TUNE_MEMORY=4GB` | Override detected memory |
| `TS_TUNE_NUM_CPUS=2` | Override detected CPU count |
| `TS_TUNE_MAX_CONNS=50` | Set max connections |
| `TS_TUNE_MAX_BG_WORKERS=8` | Set max background workers |

### 7.6 Recommendation for P0-016

Since we are NOT using the official TimescaleDB image (to preserve pgvector), `timescaledb-tune` does not auto-run. This is fine — we already have a tuned `postgresql.conf` from P0-014. Manual tuning is not necessary for the initial setup.

If tuning is desired later:
```bash
docker exec guinevere-postgres timescaledb-tune \
  --quiet --yes \
  --conf-path=/var/lib/postgresql/data/postgresql.conf
```

---

## 8. TimescaleDB 2.15 Apache-2 vs Community Edition

### 8.1 Edition Comparison

From [TigerData documentation](https://docs.tigerdata.com/about/latest/timescaledb-editions/):

| Feature | Apache-2 Edition (OSS) | Community Edition (TSL) |
|---------|----------------------|------------------------|
| License | Apache 2.0 (unrestricted) | Timescale License (TSL) — free to use, cannot offer as DBaaS |
| Hypertables | ✅ | ✅ |
| Compression | ❌ **Not available** | ✅ **Available** |
| Continuous Aggregates | ❌ | ✅ |
| Data Retention Policies | ❌ | ✅ |
| Jobs & Automation | ❌ | ✅ |
| SkipScan | ❌ | ✅ |
| Hypercore/Columnstore | ❌ | ✅ |
| Package name | `timescaledb-2-oss-postgresql-16` | `timescaledb-2-postgresql-16` |

### 8.2 Impact on Guinevere

From the Step prompts, TimescaleDB is needed for:
- **Surveillance events** (time-series data with compression)
- **Agent loop timestamps**
- **Observability metrics**

**Compression is critical** for reducing storage costs of surveillance data. Compression is a Community Edition feature.

**Recommendation**: Install Community Edition (`timescaledb-2-postgresql-16`). TSL allows free self-hosting; the restriction (cannot offer as DBaaS) does not apply to Guinevere's use case.

### 8.3 Switching Between Editions

If Apache-2 is installed and Community features are needed later:
```bash
# Install Community Edition alongside
apt-get install timescaledb-2-postgresql-16

# The Community Edition replaces the Apache-2 libraries when both are installed
# Check which is active:
psql -c "SELECT extname, extversion, extconfig FROM pg_extension WHERE extname = 'timescaledb';"
```

**Caveat**: The `\dx` command may display "Community Edition" even when the Apache-2 libraries take dominance ([TimescaleDB issue #7884](https://github.com/timescale/timescaledb/issues/7884)). Always verify with a feature test.

---

## 9. Docker Volume Persistence and Restart Safety

### 9.1 Volume Lifecycle

| Action | Volume Survives? | Data Safe? |
|--------|-----------------|------------|
| `docker stop` | ✅ Yes | ✅ Safe |
| `docker start` | ✅ Yes | ✅ Safe |
| `docker restart` | ✅ Yes | ✅ Safe |
| `docker rm` | ✅ Yes (volume independent) | ✅ Safe |
| `docker stop ; docker rm ; docker run -v same-volume` | ✅ Yes | ✅ Safe |
| `docker volume rm` | ❌ Volume deleted | ❌ Data lost |
| `docker compose down` | ✅ Yes (default) | ✅ Safe |
| `docker compose down --volumes` | ❌ Deletes named volumes | ❌ Data lost |

### 9.2 Named Volume vs Bind Mount

For P0-016, the setup uses either:

**Named volume** (recommended by P0-014):
```yaml
volumes:
  - guinevere_postgres_data:/var/lib/postgresql/data
```

**Bind mount** (alternative):
```yaml
volumes:
  - /home/guinevere/data/postgres:/var/lib/postgresql/data
```

Both survive `docker stop` and `docker rm`. Only explicit deletion removes data.

### 9.3 Verifying Volume Persistence

```bash
# Show current volume info
docker inspect guinevere-postgres --format='{{range .Mounts}}{{.Name}} {{.Source}} {{.Destination}}{{end}}'

# List volumes
docker volume ls | grep guinevere

# Inspect volume details
docker volume inspect guinevere_postgres_data
```

### 9.4 ALTER SYSTEM and postgresql.auto.conf Persistence

When `ALTER SYSTEM SET shared_preload_libraries = 'timescaledb'` is executed, PostgreSQL writes to `postgresql.auto.conf` inside the data directory (`/var/lib/postgresql/data/postgresql.auto.conf`). This file is part of the persistent volume.

**This means**: The `shared_preload_libraries` setting survives container recreation, image changes, and even `docker rm` + `docker run` with the same volume.

### 9.5 Data Directory Path Compatibility

For `postgres:16-trixie`: `PGDATA=/var/lib/postgresql/data`  
For `timescale/timescaledb:2.15.2-pg16`: `PGDATA=/var/lib/postgresql/data` (same)  
For `timescale/timescaledb-ha:pg16`: `PGDATA=/home/postgres/pgdata/data` (DIFFERENT)

When switching between images, verify PGDATA path matches.

---

## 10. Rollback Procedure

### 10.1 Rollback from TimescaleDB Installation

If TimescaleDB breaks PostgreSQL startup or causes issues:

```bash
# 1. If container won't start due to bad shared_preload_libraries:
# Find the volume
docker volume ls | grep guinevere

# Mount volume in a temporary container and fix the config
docker run --rm -it \
  -v guinevere_postgres_data:/data \
  alpine:latest \
  sh -c "sed -i 's/shared_preload_libraries.*//' /data/postgresql.auto.conf && cat /data/postgresql.auto.conf"

# 2. Start the container again
docker start guinevere-postgres

# 3. Once running, drop the extension
docker exec guinevere-postgres \
  psql -U guinevere -d guinevere \
  -c "DROP EXTENSION IF EXISTS timescaledb CASCADE;"
```

**Warning**: `DROP EXTENSION timescaledb CASCADE` deletes ALL hypertables and TimescaleDB-specific objects. Use only if you have a backup.

### 10.2 Rollback from Image Switch (Approach A)

If you switched to `timescale/timescaledb:2.15.2-pg16` and need to revert:

```bash
# 1. Stop the current container
docker stop guinevere-postgres
docker rm guinevere-postgres

# 2. Start with the original postgres:16-trixie image and same volume
docker run -d \
  --name guinevere-postgres \
  --network guinevere-net \
  -p 127.0.0.1:5433:5432 \
  -e POSTGRES_USER=guinevere \
  -e POSTGRES_DB=guinevere \
  -e POSTGRES_PASSWORD_FILE=/run/secrets/db_password \
  -v guinevere_postgres_data:/var/lib/postgresql/data \
  -v /home/guinevere/secrets/db_password:/run/secrets/db_password:ro \
  -v /home/guinevere/config/postgres/postgresql.conf:/etc/postgresql/postgresql.conf:ro \
  postgres:16-trixie \
  -c config_file=/etc/postgresql/postgresql.conf

# 3. The data is intact. TimescaleDB extension will fail to load
#    (shared_preload_libraries still references it), so:
docker exec guinevere-postgres \
  psql -U guinevere -d guinevere \
  -c "ALTER SYSTEM SET shared_preload_libraries = '';"
docker restart guinevere-postgres
```

### 10.3 Rollback from Custom Docker Image (Approach B — Recommended)

```bash
# Simply rebuild without TimescaleDB
# Dockerfile without timescaledb packages:
FROM postgres:16-trixie
RUN apt-get update && apt-get install -y --no-install-recommends \
        postgresql-16-pgvector \
    && rm -rf /var/lib/apt/lists/*

# Build and deploy
docker build -t guinevere-postgres:rollback -f Dockerfile.rollback .
docker stop guinevere-postgres
docker rm guinevere-postgres
docker run -d ... guinevere-postgres:rollback ...
```

### 10.4 Backup Before Installation

Before making ANY changes:

```bash
# Logical backup of the entire database
docker exec guinevere-postgres \
  pg_dump -U guinevere -Fc guinevere \
  > /backups/guinevere/pre-timescaledb-$(date +%Y%m%d).dump

# Verify the backup
docker run --rm -i postgres:16-trixie \
  pg_restore --list /dev/stdin \
  < /backups/guinevere/pre-timescaledb-$(date +%Y%m%d).dump \
  | head -5
```

---

## 11. Risk Assessment and Mitigation

| Risk | Severity | Probability | Mitigation |
|------|----------|-------------|------------|
| Container fails to start after shared_preload_libraries change | High | Low | Volume-mount the config, fix by editing postgresql.auto.conf from a temporary container |
| pgvector incompatible after image switch | High | Medium (Approach A only) | Use Approach B (custom Dockerfile) — keeps both extensions from same base image |
| TimescaleDB apt package incompatible with Debian Trixie | Medium | Low | The package targets Ubuntu Noble, but Debian Trixie uses the same glibc and PG extension API. Test in a temporary container first. |
| Docker stop timeout causes SIGKILL | Medium | Low | Use `--stop-timeout=120` for safe shutdown |
| Volume permission issues when switching image | High | Low (Approach A) | Verify UID/GID before switching. TimescaleDB Alpine image uses UID 70? No, it's 999 on Alpine too. Check: `docker run --rm timescale/timescaledb:2.15.2-pg16 id postgres` |
| ALTER SYSTEM writes to wrong location | Medium | Low | Ensure `PGDATA` is correct. Default for both images is `/var/lib/postgresql/data`. |
| Aizanta PostgreSQL accidentally restarted | Critical | Very Low | Commands use `docker restart guinevere-postgres` (specific container name), never `systemctl restart postgresql` |
| TimescaleDB Community license restricts future use | Low | Low | TSL allows free self-hosting. Only prohibits selling it as a DBaaS. Guinevere is a personal project. |

### 11.1 Pre-Installation Safety Checklist

- [ ] Backup taken: `pg_dump -Fc`
- [ ] Volume name/info recorded
- [ ] Container name confirmed: `docker ps --filter name=guinevere-postgres`
- [ ] Aizanta PG running and reachable: `psql -h 127.0.0.1 -p 5432 -U aizanta -c "SELECT 1;"`
- [ ] Shared_preload_libraries current value: `SHOW shared_preload_libraries;`
- [ ] pgvector current version: `SELECT extversion FROM pg_extension WHERE extname = 'vector';`
- [ ] Custom Dockerfile built and tested (if using Approach B)
- [ ] Rollback procedure reviewed

---

## 12. Recommended Implementation Plan for P0-016

### Phase 1: Prepare Custom Docker Image

```dockerfile
# Dockerfile — build on the VPS where Docker runs
FROM postgres:16-trixie

# Install pgvector (from P0-015) and TimescaleDB 2.15 Community Edition
RUN apt-get update && apt-get install -y --no-install-recommends \
        gnupg \
        curl \
        ca-certificates \
    && curl -s https://packagecloud.io/timescale/timescaledb/gpgkey \
        | gpg --dearmor -o /usr/share/keyrings/timescaledb.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/timescaledb.gpg] https://packagecloud.io/timescale/timescaledb/ubuntu/ noble main" \
        > /etc/apt/sources.list.d/timescaledb.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        timescaledb-2-postgresql-16 \
        postgresql-16-pgvector \
    && rm -rf /var/lib/apt/lists/*

# Pre-configure shared_preload_libraries for timescaledb
RUN echo "shared_preload_libraries = 'timescaledb'" \
    >> /usr/share/postgresql/postgresql.conf.sample
```

```bash
# Build
docker build -t guinevere-postgres:16-pgvector-timescaledb .
```

### Phase 2: Deploy

```bash
# Backup
docker exec guinevere-postgres \
  pg_dump -U guinevere -Fc guinevere \
  > /backups/guinevere/pre-timescaledb-$(date +%Y%m%d-%H%M%S).dump

# Stop and remove old container (data volume persists)
docker stop guinevere-postgres
docker rm guinevere-postgres

# Start with new image
docker run -d \
  --name guinevere-postgres \
  --network guinevere-net \
  --restart unless-stopped \
  -p 127.0.0.1:5433:5432 \
  -e POSTGRES_USER=guinevere \
  -e POSTGRES_DB=guinevere \
  -e POSTGRES_PASSWORD_FILE=/run/secrets/db_password \
  -e TZ=Asia/Bangkok \
  -v guinevere_postgres_data:/var/lib/postgresql/data \
  -v /home/guinevere/secrets/db_password:/run/secrets/db_password:ro \
  -v /home/guinevere/config/postgres/postgresql.conf:/etc/postgresql/postgresql.conf:ro \
  -v /etc/localtime:/etc/localtime:ro \
  --shm-size=256m \
  --memory=4g \
  --cpus=2 \
  --stop-timeout=120 \
  guinevere-postgres:16-pgvector-timescaledb \
  -c config_file=/etc/postgresql/postgresql.conf
```

### Phase 3: Configure and Enable

```bash
# Check container logs for startup issues
docker logs guinevere-postgres --tail 30

# Set shared_preload_libraries (if not already in postgresql.conf)
docker exec guinevere-postgres \
  psql -U guinevere -d guinevere \
  -c "ALTER SYSTEM SET shared_preload_libraries = 'timescaledb';"

# Restart to load TimescaleDB
docker restart guinevere-postgres

# Wait and verify
sleep 3
docker exec guinevere-postgres \
  psql -U guinevere -d guinevere \
  -c "SHOW shared_preload_libraries;"
# Expected: timescaledb

# Create the extension
docker exec guinevere-postgres \
  psql -U guinevere -d guinevere \
  -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"

# Verify
docker exec guinevere-postgres \
  psql -U guinevere -d guinevere \
  -c "SELECT extname, extversion FROM pg_extension WHERE extname IN ('timescaledb', 'vector');"

# Test hypertable creation
docker exec guinevere-postgres \
  psql -U guinevere -d guinevere \
  -c "
    CREATE TABLE test_metrics (
      ts TIMESTAMPTZ NOT NULL,
      value DOUBLE PRECISION
    );
    SELECT create_hypertable('test_metrics', 'ts');
    DROP TABLE test_metrics;
  "

# Verify pgvector still works
docker exec guinevere-postgres \
  psql -U guinevere -d guinevere \
  -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

### Phase 4: Verify Aizanta Isolation

```bash
# Confirm Aizanta PostgreSQL is unaffected
PGPASSWORD=$(cat /path/to/aizanta/password) \
  psql -h 127.0.0.1 -p 5432 -U aizanta -c "SELECT 1 AS aizanta_ok;"

# Confirm guinevere on 5433
docker exec guinevere-postgres \
  psql -U guinevere -d guinevere \
  -c "SELECT inet_server_port() AS guinevere_port;"
```

### Phase 5: Clean Up

```bash
# Remove the test Dockerfile from production (optional but recommended)
rm Dockerfile.timescaledb

# Clean up apt cache in the image (already done in the Dockerfile)
```

---

## 13. References

### Official Documentation
- [TimescaleDB Installation with Docker](https://github.com/timescale/docs.timescale.com-content/blob/master/getting-started/installation-docker.md)
- [TimescaleDB Docker Hub](https://hub.docker.com/r/timescale/timescaledb)
- [TimescaleDB Docker GitHub](https://github.com/timescale/timescaledb-docker)
- [TimescaleDB Docker config guide](https://github.com/timescale/docs/blob/latest/self-hosted/configuration/docker-config.md)
- [TimescaleDB Uninstall Guide](https://github.com/timescale/docs/blob/latest/self-hosted/uninstall.md)
- [TimescaleDB Downgrade Guide](http://docs.timescale.com/docs/self-hosted/latest/upgrades/downgrade)
- [TimescaleDB Editions Comparison](https://docs.tigerdata.com/about/latest/timescaledb-editions/)
- [TimescaleDB v2.15.0 Release Notes](https://github.com/timescale/timescaledb/releases/tag/2.15.0)
- [PostgreSQL ALTER SYSTEM docs](https://www.postgresql.org/docs/16/sql-altersystem.html)
- [PostgreSQL shared_preload_libraries docs](https://postgresqlco.nf/doc/en/param/shared_preload_libraries/)
- [TimescaleDB packagecloud for Ubuntu Noble](https://packagecloud.io/timescale/timescaledb/packages/ubuntu/noble/timescaledb-2-postgresql-16_2.15.0~ubuntu24.04_amd64.deb)

### Docker References
- [docker-library/postgres README](https://github.com/docker-library/docs/blob/master/postgres/README.md)
- [Docker PostgreSQL advanced configuration](https://docs.docker.com/guides/postgresql/advanced-configuration-and-initialization/)
- [docker-library/postgres issue #1207 — SIGKILL during restart](https://github.com/docker-library/postgres/issues/1207)
- [docker-library/postgres issue #1010 — bind mount ownership](https://github.com/docker-library/postgres/issues/1010)

### Extension Compatibility
- [TimescaleDB issue #8895 — pgvector not bundled](https://github.com/timescale/timescaledb/issues/8895)
- [TimescaleDB issue #5752 — PostgreSQL 16 support](https://github.com/timescale/timescaledb/issues/5752)
- [pgvectorscale — DiskANN vector index](https://github.com/timescale/pgvectorscale)
- [pgvectorscale Docker setup guide](https://queryplane.com/docs/blog/scaling-vector-search-with-pgvectorscale)
- [TimescaleDB HA image issue #620 — volume permissions](https://github.com/timescale/timescaledb-docker-ha/issues/620)

### Community References
- [KnYL blog — Install TimescaleDB on existing PostgreSQL container](https://www.knyl.me/blog/install-timescaledb-on-an-existing-postgresql-container/)
- [StackOverflow — shared_preload_libraries + Docker restart](https://stackoverflow.com/questions/68435038/fatal-extension-timescaledb-must-be-preloaded)
- [StackOverflow — Configure postgresql.conf via ALTER SYSTEM](https://stackoverflow.com/questions/75410516/configure-postgresql-conf-file-through-psql-command)
- [StackOverflow — Docker container broken after config change](https://stackoverflow.com/questions/68459566/postgres-docker-container-is-broken-after-changing-postgres-config)
- [pganalyze — Enable pg_stat_statements in Docker](https://pganalyze.com/docs/install/self_managed/02_enable_pg_stat_statements_docker)
- [TimescaleDB issue #66 — must be preloaded error](https://github.com/timescale/timescaledb-docker/issues/66)
- [TimescaleDB issue #7884 — Community vs Apache edition conflict](https://github.com/timescale/timescaledb/issues/7884)

---

*Report generated by Guinevere (Librarian agent) — 2026-05-31*  
*Research sources include Docker Hub, GitHub, PostgreSQL official documentation, TimescaleDB docs, packagecloud, and community guides.*