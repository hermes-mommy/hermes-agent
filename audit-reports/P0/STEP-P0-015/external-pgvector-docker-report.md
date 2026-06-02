# External Research Report: pgvector Installation for PostgreSQL 16 (Docker)

**Date**: 2026-05-31  
**Scope**: STEP-P0-015 — Install pgvector extension on guinevere-postgres Docker container  
**Context**: PostgreSQL 16 (`postgres:16-trixie` or similar) running in Docker on VPS `faiz-prod-01`.  
**Constraint**: MUST NOT disrupt Aizanta PostgreSQL (running on `127.0.0.1:5432`).  
**Consumer**: P0-015 implementation step.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [pgvector & PostgreSQL 16 Compatibility](#2-pgvector--postgresql-16-compatibility)
3. [Docker Image Landscape](#3-docker-image-landscape)
4. [Volume Persistence — How Docker Data Survives](#4-volume-persistence--how-docker-data-survives)
5. [Three Installation Approaches for an Already-Running Container](#5-three-installation-approaches-for-an-already-running-container)
   - [Method A: Custom Dockerfile (Recommended for Control)](#method-a-custom-dockerfile-recommended-for-control)
   - [Method B: Directly Switch to pgvector/pgvector Image](#method-b-directly-switch-to-pgvectorpgvector-image)
   - [Method C: Exec Into Running Container (Non-Persistent)](#method-c-exec-into-running-container-non-persistent)
6. [Detailed Comparison: Method A vs Method B vs Method C](#6-detailed-comparison-method-a-vs-method-b-vs-method-c)
7. [Data Safety & Rollback Procedure](#7-data-safety--rollback-procedure)
8. [Risk Analysis: Switching Images Without Data Loss](#8-risk-analysis-switching-images-without-data-loss)
9. [Aizanta PostgreSQL Isolation](#9-aizanta-postgresql-isolation)
10. [Installation Command Reference](#10-installation-command-reference)
11. [References & Source Permalinks](#11-references--source-permalinks)

---

## 1. Executive Summary

**pgvector 0.7.x is fully compatible with PostgreSQL 16.** The extension is a shared library (`.so`) + SQL control files installed into PostgreSQL's extension directory. It does NOT modify the PostgreSQL data directory format — enabling it is purely a `CREATE EXTENSION vector;` SQL command after the binary is installed.

For a **running Docker PostgreSQL container**, the safest approaches to add pgvector are (in order of preference):

| Priority | Method | Risk Level | Data Persistence |
|---|---|---|---|
| **1 (Best)** | Build custom Dockerfile from `postgres:16` + add pgvector, then recreate container with same volume | ✅ Low | Full — same volume mount |
| **2** | Switch to `pgvector/pgvector:pg16` image with same volume | ✅ Low | Full — same volume mount |
| **3** | `docker exec` and install via apt/compile in-place | ⚠️ Medium | Lost on container recreate |

**Key finding**: Docker named volumes at `/var/lib/postgresql/data` survive container deletion and recreation. Switching from `postgres:16` to any image based on the same PostgreSQL major version (like `pgvector/pgvector:pg16`) does NOT lose data — as long as the same volume is mounted at the same path.

---

## 2. pgvector & PostgreSQL 16 Compatibility

| pgvector Version | PG 12 | PG 13 | PG 14 | PG 15 | **PG 16** | PG 17 | PG 18 |
|---|---|---|---|---|---|---|---|
| **0.7.x** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | **✅ Yes** | ❌ No | ❌ No |
| **0.8.x** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | **✅ Yes** | ✅ Yes | ✅ Yes |

Source: [pgvector/pgvector README](https://github.com/pgvector/pgvector), [DBA Data Verse compatibility matrix](https://dbadataverse.com/tech/postgresql/2026/05/pgvector-release-notes-updates-2026)

**Note on version selection**:
- The user specified **pgvector 0.7.0** specifically.
- As of May 2026, the latest pgvector release is **0.8.2**.
- The `pgvector/pgvector:pg16` Docker tag tracks the latest pgvector for PG16 (currently 0.8.2).
- The `0.7.0-pg16` tag **does exist** on Docker Hub (confirmed by GitHub issue #540 referencing `pgvector/pgvector:0.7.0-pg16`).
- If you need specifically 0.7.0, use `pgvector/pgvector:0.7.0-pg16` or pin it in a custom Dockerfile with `git clone --branch v0.7.0`.

### pgvector 0.7.0 Key Features
- Added `halfvec` type (2-byte floats, up to 4,000 dimensions)
- Added `sparsevec` type (up to 1,000 non-zero dimensions)
- Added `binary_quantize` function
- Added HNSW parallel index builds
- Added CPU dispatching for distance functions (Linux x86-64)
- Added `hamming_distance`, `jaccard_distance`, `l2_normalize`, `subvector` functions
- Supports indexing `bit` type for binary vectors (up to 64,000 dimensions)

Source: [PostgreSQL.org — pgvector 0.7.0 Released](https://www.postgresql.org/about/news/pgvector-070-released-2852/)

---

## 3. Docker Image Landscape

### 3.1 Official pgvector Images (`pgvector/pgvector`)

Available tags for PostgreSQL 16 (from [Docker Hub](https://hub.docker.com/r/pgvector/pgvector)):

| Tag | Base Image | pgvector Version | Use Case |
|---|---|---|---|
| `pg16` | `postgres:16-bookworm` | Latest (0.8.2) | Rolling latest, convenient for dev |
| `pg16-trixie` | `postgres:16-trixie` | Latest (0.8.2) | Trixie variant (newer Debian) |
| `pg16-bookworm` | `postgres:16-bookworm` | Latest (0.8.2) | Explicit Bookworm |
| `0.8.2-pg16` | `postgres:16-bookworm` | 0.8.2 | Pinned version, recommended for prod |
| `0.8.2-pg16-trixie` | `postgres:16-trixie` | 0.8.2 | Pinned + trixie |
| `0.8.2-pg16-bookworm` | `postgres:16-bookworm` | 0.8.2 | Pinned + bookworm |
| `0.7.0-pg16` | `postgres:16-bookworm` | 0.7.0 | Pinned 0.7.0, if specifically needed |

**Important**: There is no `latest` tag for `pgvector/pgvector`. Use explicit tags.

### 3.2 Image Architecture

The `pgvector/pgvector` images are built on top of the **official `postgres` Docker images**. They:
- Use the exact same entrypoint, init scripts, and volume paths
- Add only the pgvector extension binaries (shared library + SQL control files)
- Compile with `OPTFLAGS=""` to ensure CPU-architecture portability
- Remove build dependencies after compilation to keep image size minimal
- Support both AMD64 and ARM64

Source: [DeepWiki — Docker Deployment for pgvector](https://deepwiki.com/pgvector/pgvector/8.3-docker-deployment)

### 3.3 What Gets Added

Compared to `postgres:16`, the `pgvector/pgvector:pg16` image adds:

```
/usr/lib/postgresql/16/lib/vector.so         # Shared library
/usr/share/postgresql/16/extension/vector.control   # Extension control file
/usr/share/postgresql/16/extension/vector--*.sql     # SQL upgrade scripts
/usr/share/doc/pgvector/                               # Documentation
```

Nothing else changes — same PostgreSQL binary, same config, same init behavior.

---

## 4. Volume Persistence — How Docker Data Survives

### 4.1 Critical Understanding

Docker named volumes **persist independently of container lifecycle**. When you:

```bash
docker stop guinevere-postgres     # Container stops, data in volume is safe
docker rm guinevere-postgres        # Container deleted, volume still exists
docker run --name guinevere-postgres \
  -v guinevere-pgdata:/var/lib/postgresql/data \  # Same volume
  ... \                           # Different image — data survives
  pgvector/pgvector:pg16
```

**The data is in the volume, not in the container's writable layer.** Switching images does not touch the volume.

### 4.2 Volume Path for PostgreSQL 16

For PostgreSQL **16 and below**, the data directory is at:

```
/var/lib/postgresql/data
```

For PostgreSQL **18+**, the path changes to a versioned subdirectory (`/var/lib/postgresql/18/docker`). Since we are on PG16, the traditional path applies.

**Mount consistently**: Always mount to `/var/lib/postgresql/data`.

### 4.3 Named Volume vs Bind Mount

| Type | Example | Persistence | Best For |
|---|---|---|---|
| Named volume | `-v pgdata:/var/lib/postgresql/data` | ✅ Survives container delete | Production |
| Bind mount | `-v /host/path:/var/lib/postgresql/data` | ✅ Survives container delete | Dev/backup |

### 4.4 What Could Go Wrong

The only way data loss occurs is if you:
1. Delete the named volume (`docker volume rm pgdata`)
2. Mount to a **different** volume path (data still exists in the old volume, new container starts empty)
3. Mount to `/var/lib/postgresql` (parent) instead of `/var/lib/postgresql/data` (subdirectory) — on PG16, this causes init to not find existing data

---

## 5. Three Installation Approaches for an Already-Running Container

### Method A: Custom Dockerfile ✅ RECOMMENDED

**Best for**: Full control, auditability, internal registry, pinning exact pgvector 0.7.0.

#### Dockerfile

```dockerfile
# Dockerfile.pgvector
FROM postgres:16-trixie

ENV DEBIAN_FRONTEND=noninteractive

# Option A1: Install via apt (simplest, if package matches)
# The PGDG apt repo is already configured in the official postgres:16 image
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        postgresql-16-pgvector && \
    rm -rf /var/lib/apt/lists/*

# Option A2: Compile from source (use if you need exact v0.7.0)
# RUN apt-get update && \
#     apt-get install -y --no-install-recommends \
#         build-essential git ca-certificates postgresql-server-dev-16 && \
#     update-ca-certificates && \
#     git clone --branch v0.7.0 --depth 1 https://github.com/pgvector/pgvector.git /tmp/pgvector && \
#     cd /tmp/pgvector && \
#     make OPTFLAGS="" && \
#     make install && \
#     rm -rf /tmp/pgvector && \
#     apt-get purge -y build-essential git postgresql-server-dev-16 && \
#     apt-get autoremove -y && \
#     apt-get clean && \
#     rm -rf /var/lib/apt/lists/*

# Keep the default PostgreSQL entrypoint
CMD ["postgres"]
```

#### Procedure

```bash
# 1. Build the new image
docker build -t guinevere-postgres-pgvector -f Dockerfile.pgvector .

# 2. Stop the running container
docker stop guinevere-postgres

# 3. Recreate with the same volume (critical: verify volume name first!)
docker run -d \
  --name guinevere-postgres \
  -e POSTGRES_USER=... \
  -e POSTGRES_PASSWORD=... \
  -e POSTGRES_DB=guinevere \
  -v guinevere-pgdata:/var/lib/postgresql/data \
  -p 5432:5432 \
  --restart unless-stopped \
  guinevere-postgres-pgvector

# 4. Verify data survived
docker exec guinevere-postgres psql -U postgres -d guinevere -c "SELECT count(*) FROM pg_database;"

# 5. Enable pgvector extension
docker exec guinevere-postgres psql -U postgres -d guinevere -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 6. Verify
docker exec guinevere-postgres psql -U postgres -d guinevere -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
```

**Sources**:
- [GitHub Issue #91 — pgvector maintainer recommendation](https://github.com/pgvector/pgvector/issues/91#issuecomment-1506756429)
- [Medium — Building a postgres docker image with pgvector support](https://medium.com/@smrati.katiyar/building-a-postgres-docker-image-with-pgvector-support-1da08faa4ce5)
- [UserJot — Setting up Postgres and pgvector with Docker for RAG](https://userjot.com/blog/setting-up-postgres-pgvector-docker-rag.html)

---

### Method B: Directly Switch to pgvector/pgvector Image

**Best for**: Quickest path, no build step, uses pre-built image.

#### Procedure

```bash
# 1. Pull the official pgvector image
docker pull pgvector/pgvector:pg16

# 2. Note the current container's volume name
docker inspect guinevere-postgres --format='{{range .Mounts}}{{.Name}}{{end}}'
# Example output: guinevere-pgdata

# 3. Stop and remove the container (volume persists!)
docker stop guinevere-postgres
docker rm guinevere-postgres

# 4. Recreate using the pgvector image with the SAME volume
docker run -d \
  --name guinevere-postgres \
  -e POSTGRES_USER=... \
  -e POSTGRES_PASSWORD=... \
  -e POSTGRES_DB=guinevere \
  -v guinevere-pgdata:/var/lib/postgresql/data \
  -p 5432:5432 \
  --restart unless-stopped \
  --shm-size=1g \
  pgvector/pgvector:0.7.0-pg16

# 5. Verify data before enabling extension
docker exec guinevere-postgres psql -U postgres -d guinevere -c "SELECT count(*) FROM pg_database;"

# 6. Enable the extension
docker exec guinevere-postgres psql -U postgres -d guinevere -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 7. Verify
docker exec guinevere-postgres psql -U postgres -d guinevere -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
```

**Important**: If the current container uses `postgres:16-trixie`, use `pgvector/pgvector:pg16-trixie` (or `:0.7.0-pg16-trixie`) to match the Debian base. Using `bookworm` variant on a system that expects `trixie` might cause subtle libc issues. Check current base with:

```bash
docker inspect guinevere-postgres --format='{{.Config.Image}}'
```

**Sources**:
- [Docker Hub — pgvector/pgvector](https://hub.docker.com/r/pgvector/pgvector)
- [pgvector/pgvector README](https://github.com/pgvector/pgvector)
- [VibeCode Platform — PostgreSQL + pgvector Setup](https://ryanmaclean.github.io/vibecode-webui/prisma-pgvector/)
- [Serverpod docs — Upgrading to pgvector support](https://docs.serverpod.dev/2.9.0/upgrading/upgrade-to-pgvector)

---

### Method C: Exec Into Running Container (Non-Persistent)

**Best for**: Quick test/validation only. **NOT recommended for production** because changes are lost when the container is recreated.

#### Procedure

```bash
# Option C1: apt install (if the container has PGDG apt source)
docker exec -it guinevere-postgres bash -c "apt-get update && apt-get install -y postgresql-16-pgvector"

# Option C2: Compile from source (works on any postgres:16 image)
docker exec -it guinevere-postgres bash -c "
  apt-get update && \
  apt-get install -y --no-install-recommends build-essential git ca-certificates postgresql-server-dev-16 && \
  git clone --branch v0.7.0 --depth 1 https://github.com/pgvector/pgvector.git /tmp/pgvector && \
  cd /tmp/pgvector && \
  make OPTFLAGS=\"\" && \
  make install && \
  rm -rf /tmp/pgvector && \
  apt-get purge -y build-essential git postgresql-server-dev-16 && \
  apt-get autoremove -y && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*
"

# Then enable
docker exec guinevere-postgres psql -U postgres -d guinevere -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

**⚠️ Warnings from the pgvector maintainer** ([GitHub Issue #91](https://github.com/pgvector/pgvector/issues/91#issuecomment-1506756429)):

> "If you install it directly in the running container, it won't persist if the container is ever stopped (due to how Docker works)."

The maintainer's explicit recommendation is to create a new image and restart.

---

## 6. Detailed Comparison: Method A vs Method B vs Method C

| Criterion | Method A: Custom Dockerfile | Method B: Switch Image | Method C: Exec In-Place |
|---|---|---|---|
| **Effort** | Medium (write Dockerfile, build) | Low (one-line pull) | Low (one command) |
| **Data Safety** | ✅ Full (same volume) | ✅ Full (same volume) | ✅ Immediate (but ephemeral) |
| **Persistence across recreate** | ✅ Yes | ✅ Yes | ❌ No — lost on `docker rm` |
| **Version pinning** | ✅ Exact control | ✅ Use tagged image | ✅ Pin branch in clone |
| **Audit trail** | ✅ Dockerfile in repo | ⚠️ Image tag only | ❌ No trace |
| **Build time** | ⏱ 2–5 min (first time) | ⏱ Instant (pull) | ⏱ 2–5 min |
| **Image size overhead** | ~50 MB (build deps removed) | ~50 MB (pre-built) | N/A (in-container) |
| **Rollback** | ✅ Switch back to old image + same volume | ✅ Switch back to old image + same volume | ⚠️ Recreate from original image |
| **Risk of OOM during build** | Low (build runs on host, not PG container) | None (pre-built) | ⚠️ Medium (shares PG container resources) |
| **Official recommendation** | ✅ [pgvector maintainer](https://github.com/pgvector/pgvector/issues/91) | ✅ [pgvector README](https://github.com/pgvector/pgvector) | ❌ Explicitly discouraged |

---

## 7. Data Safety & Rollback Procedure

### 7.1 Pre-Migration Checklist

Before any change:

```bash
# 1. Identify the current volume
docker inspect guinevere-postgres --format='{{range .Mounts}}{{.Name}} -> {{.Destination}}{{end}}'

# 2. Verify data exists in the volume
docker run --rm -v guinevere-pgdata:/data alpine ls -la /data

# 3. Take a backup (safety net)
docker exec guinevere-postgres pg_dump -U postgres -d guinevere -Fc -f /tmp/guinevere-backup.dump
docker cp guinevere-postgres:/tmp/guinevere-backup.dump ./guinevere-backup-$(date +%Y%m%d).dump

# 4. Note the current image
docker inspect guinevere-postgres --format='{{.Config.Image}}'
# Save this for rollback
```

### 7.2 Rollback Procedure (Method A or B)

If something goes wrong after switching to the pgvector image:

```bash
# 1. Stop the new container
docker stop guinevere-postgres
docker rm guinevere-postgres

# 2. Restart with the ORIGINAL image and SAME volume
docker run -d \
  --name guinevere-postgres \
  -e POSTGRES_USER=... \
  -e POSTGRES_PASSWORD=... \
  -e POSTGRES_DB=guinevere \
  -v guinevere-pgdata:/var/lib/postgresql/data \
  -p 5432:5432 \
  --restart unless-stopped \
  postgres:16-trixie  # Original image

# 3. Verify data
docker exec guinevere-postgres psql -U postgres -d guinevere -c "SELECT count(*) FROM pg_database;"
```

**The volume is never modified by the image switch.** Data only needs restoration from backup if you accidentally deleted the volume.

### 7.3 Data Directory Integrity

The `pgvector/pgvector` image does NOT:
- Run `initdb` if data already exists at the mount path
- Modify existing PostgreSQL data files
- Change the data directory structure
- Touch `pg_hba.conf` or `postgresql.conf` (these come from the volume or are generated by the entrypoint on first init only)

The PostgreSQL entrypoint script checks for existing data. If it finds `PG_VERSION` in the data directory, it skips `initdb` and starts the existing cluster. This is standard behavior shared by both `postgres:16` and `pgvector/pgvector:pg16` images.

---

## 8. Risk Analysis: Switching Images Without Data Loss

### Summary of Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Volume not mounted on recreate | Low | Total data loss (appears empty) | Pre-check volume name, use docker-compose |
| Wrong mount path (PG16 vs PG18) | Low-Medium | Container starts empty | Verify mount is `/var/lib/postgresql/data` |
| Base image mismatch (trixie vs bookworm) | Low | libc incompatibility | Match base distro (use `-trixie` variant) |
| Extension already exists in data | Low | No-op (`CREATE EXTENSION IF NOT EXISTS`) | Use `IF NOT EXISTS` |
| pgvector version mismatch | Low | Wrong version installed | Pin exact tag |
| Aizanta PG port conflict | Low | Port binding collision | Use different port or host network isolation |
| HNSW index build OOM | Medium | PostgreSQL crash | Set `--shm-size=1g` and `maintenance_work_mem` appropriately |
| Docker daemon restart | Low | Temporary downtime | Container has `--restart unless-stopped` |

### Risk: Data format compatibility

**pgvector does not change the PostgreSQL data format.** The extension adds:
- New SQL types (`vector`, `halfvec`, `sparsevec`)
- New index access methods (IVFFlat, HNSW)
- New functions and operators

All of these are stored as **catalog entries** in the database, not in filesystem data files. Removing pgvector would simply make those types inaccessible — it would not corrupt the database.

---

## 9. Aizanta PostgreSQL Isolation

The system has two PostgreSQL instances:

| Instance | Location | Port | Docker | pgvector needed? |
|---|---|---|---|---|
| **Guinevere Postgres** | VPS `faiz-prod-01` | 5432 (or custom) | ✅ Docker | ✅ Yes |
| **Aizanta Postgres** | `127.0.0.1` | 5432 | ❌ Native or separate Docker | ❌ No |

**Isolation measures**:
1. Use `docker port` to verify Guinevere's exposed port is distinct from Aizanta's `127.0.0.1:5432`.
2. If both use Docker, ensure they are on different networks or use different host ports.
3. The pgvector installation only affects the Guinevere container.
4. **Never run** `apt install postgresql-16-pgvector` on the host — that would install it for Aizanta's PostgreSQL.

---

## 10. Installation Command Reference

### 10.1 Discover Current Container Setup

```bash
# Find current image
docker inspect guinevere-postgres --format='{{.Config.Image}}'

# Find volume mount
docker inspect guinevere-postgres --format='{{json .Mounts}}' | python -m json.tool

# Check if volume is named or bind mount
docker volume ls

# Check PostgreSQL version inside
docker exec guinevere-postgres psql -U postgres -c "SELECT version();"

# Check Debian version
docker exec guinevere-postgres cat /etc/os-release
```

### 10.2 Verify pgvector is Not Already Installed

```bash
docker exec guinevere-postgres psql -U postgres -d guinevere -c "SELECT * FROM pg_available_extensions WHERE name = 'vector';"
# If empty, pgvector is not installed.
```

### 10.3 Enable Extension (After Installation)

```bash
docker exec guinevere-postgres psql -U postgres -d guinevere -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 10.4 Verify Extension

```bash
docker exec guinevere-postgres psql -U postgres -d guinevere -c "
SELECT e.extname, e.extversion, n.nspname AS schema
FROM pg_extension e
JOIN pg_namespace n ON n.oid = e.extnamespace
WHERE e.extname = 'vector';
"
```

Expected output:

```
 extname | extversion | schema
---------+------------+---------
 vector  | 0.7.0      | public
(1 row)
```

### 10.5 Test Vector Functionality

```sql
CREATE TABLE test_vectors (id bigserial PRIMARY KEY, embedding vector(3));
INSERT INTO test_vectors (embedding) VALUES ('[1,2,3]'), ('[4,5,6]');
SELECT * FROM test_vectors ORDER BY embedding <-> '[3,1,2]' LIMIT 5;
```

### 10.6 docker-compose.yml Integration

If using compose, update the service definition:

```yaml
services:
  guinevere-postgres:
    image: pgvector/pgvector:0.7.0-pg16   # or: build: ./docker/pgvector
    container_name: guinevere-postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: guinevere
    ports:
      - "5432:5432"
    volumes:
      - guinevere-pgdata:/var/lib/postgresql/data
    shm_size: 1g
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d guinevere"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

volumes:
  guinevere-pgdata:
    external: true   # Use existing volume, don't create new
```

**Note**: Use `external: true` to ensure compose picks up the existing named volume instead of creating a new one with a prefix.

---

## 11. References & Source Permalinks

### Official Sources

| Source | URL | Key Content |
|---|---|---|
| pgvector GitHub README | [github.com/pgvector/pgvector](https://github.com/pgvector/pgvector) | Installation methods, Docker image, version matrix |
| pgvector Docker Hub | [hub.docker.com/r/pgvector/pgvector](https://hub.docker.com/r/pgvector/pgvector) | Docker image tags (pg16, 0.8.2-pg16, etc.) |
| pgvector 0.7.0 Release | [postgresql.org/about/news/pgvector-070-released-2852/](https://www.postgresql.org/about/news/pgvector-070-released-2852/) | What's new in 0.7.0 |
| pgvector 0.7.0 on PGXN | [pgxn.org/dist/vector/0.7.0/](https://pgxn.org/dist/vector/0.7.0/) | PGXN package, compilation instructions |
| DeepWiki — Docker Deployment | [deepwiki.com/pgvector/pgvector/8.3-docker-deployment](https://deepwiki.com/pgvector/pgvector/8.3-docker-deployment) | Build process, OPTFLAGS, multi-arch details |

### Community & Issue Tracker

| Source | URL | Key Content |
|---|---|---|
| GH Issue #91 — "Install to existing container" | [github.com/pgvector/pgvector/issues/91](https://github.com/pgvector/pgvector/issues/91) | Maintainer recommends custom Dockerfile, NOT in-place install |
| GH Issue #484 — "Add to existing docker postgresql" | [github.com/pgvector/pgvector/issues/484](https://github.com/pgvector/pgvector/issues/484) | Build from source or use custom image |
| GH Issue #540 — "0.7.0-pg16 tag usage" | [github.com/pgvector/pgvector/issues/540](https://github.com/pgvector/pgvector/issues/540) | Confirms `0.7.0-pg16` Docker tag exists |

### Guides & Tutorials

| Source | URL | Key Content |
|---|---|---|
| Medium — Building pgvector Docker image | [medium.com/@smrati.katiyar/...](https://medium.com/@smrati.katiyar/building-a-postgres-docker-image-with-pgvector-support-1da08faa4ce5) | Custom Dockerfile for pgvector on PG16 |
| UserJot — Postgres + pgvector with Docker | [userjot.com/blog/...](https://userjot.com/blog/setting-up-postgres-pgvector-docker-rag.html) | Step-by-step Docker build + run |
| Markaicode — pgvector Setup 2026 | [markaicode.com/tutorial/...](https://markaicode.com/tutorial/how-to-set-up-pgvector-in-postgres/) | apt vs Docker vs compile trade-offs |
| VibeCode — PG + pgvector Setup | [ryanmaclean.github.io/vibecode-webui/prisma-pgvector/](https://ryanmaclean.github.io/vibecode-webui/prisma-pgvector/) | docker-compose patterns, manual extension creation |
| Serverpod — Upgrading to pgvector | [docs.serverpod.dev/2.9.0/upgrading/upgrade-to-pgvector](https://docs.serverpod.dev/2.9.0/upgrading/upgrade-to-pgvector) | Switching postgres image to pgvector/pgvector in compose |
| Yonk-Labs — GraphRag with pgvector | [yonk.dev/blog/...](https://yonk.dev/blog/graphrag-part2-postgres-age-pgvector/) | Dockerfile compiling pgvector 0.8.0 from source |
| DBA Data Verse — Install pgvector 2026 | [dbadataverse.com/tech/postgresql/...](https://dbadataverse.com/tech/postgresql/2026/05/install-and-configure-pgvector-on-postgresql-16-and-17-step-by-step-guide-2026) | PGDG apt repo setup, PG16 vs PG17 differences |
| DBA Data Verse — pgvector Release Notes | [dbadataverse.com/tech/postgresql/...](https://dbadataverse.com/tech/postgresql/2026/05/pgvector-release-notes-updates-2026) | Compatibility matrix (pgvector 0.7.x vs PG 12-16) |

### Volume & Data Safety

| Source | URL | Key Content |
|---|---|---|
| Potato Energy — PG Docker Migration | [potatoenergy.ru/en/blog/docker/postgres-upgrade/](https://potatoenergy.ru/en/blog/docker/postgres-upgrade/) | Volume persistence, pg_upgrade in Docker, PG18 path changes |
| Nite07 — PG18 Docker Migration | [nite07.com/en/posts/postgres-docker-18-migration/](https://www.nite07.com/en/posts/postgres-docker-18-migration/) | PG18 versioned data dir, mount path changes |

---

## Appendix A: PGDG apt Repository in Docker

The official `postgres:16` Docker image does **not** include the PGDG apt repository by default. If using Method C (exec), you may need to add it:

```bash
docker exec guinevere-postgres bash -c "
  apt-get update && \
  apt-get install -y --no-install-recommends ca-certificates curl gnupg && \
  curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /usr/share/keyrings/pgdg.gpg && \
  echo 'deb [signed-by=/usr/share/keyrings/pgdg.gpg] http://apt.postgresql.org/pub/repos/apt trixie-pgdg main' > /etc/apt/sources.list.d/pgdg.list && \
  apt-get update && \
  apt-get install -y --no-install-recommends postgresql-16-pgvector && \
  rm -rf /var/lib/apt/lists/*
"
```

**Note**: Replace `trixie` with the correct Debian codename matching your container base (`cat /etc/os-release`).

**However**, the **recommended approach** (Method A or B) does not need this — the custom Dockerfile or pre-built image handles installation during build time.

---

## Appendix B: Docker Hub Tags for pgvector/pgvector (May 2026)

The following tags are confirmed for PG16 as of the research date:

```
pg16
pg16-trixie
pg16-bookworm
0.8.2-pg16
0.8.2-pg16-trixie
0.8.2-pg16-bookworm
0.7.0-pg16          # Verified by GH issue #540
```

The `latest` tag does not exist. Always use explicit tags.

---

## Appendix C: Post-Install Verification Checklist

- [ ] Container starts without errors
- [ ] `docker exec guinevere-postgres psql -U postgres -c "SELECT version();"` returns PostgreSQL 16.x
- [ ] `docker exec guinevere-postgres psql -U postgres -d guinevere -c "SELECT * FROM pg_available_extensions WHERE name = 'vector';"` shows version
- [ ] `CREATE EXTENSION vector;` succeeds
- [ ] Existing data is present (query a table from before migration)
- [ ] Vector column creation works: `CREATE TABLE test_vec (id serial, v vector(3));`
- [ ] INSERT and SELECT work with vector data
- [ ] Aizanta PostgreSQL on 127.0.0.1:5432 is unaffected
- [ ] Container restart is stable: `docker restart guinevere-postgres` → everything still works

---

*End of report. Prepared for STEP-P0-015 implementation.*