# VPS Service State - Pre P1-017 (Persona Smoke Test), P1-018 (guinevere-core.service), P1-019 (Health Check)

**Date**: 2026-06-01
**VPS Host**: guinevere-vps (Tailscale)
**Source**: Local evidence files (P0 + P1 documentation analysis)
**Purpose**: Determine correct systemd service dependencies for guinevere-core.service before implementation

---

## 1. Executive Summary

PostgreSQL and Redis run as **Docker containers**, not systemd native services. The service names `postgresql.service` and `redis-guinevere.service` referenced in the current StepPrompts.md P1-018 template (lines 4817-4818) **DO NOT EXIST** on the VPS. The correct dependency for guinevere-core.service is `docker.service`.

---

## 2. Database Runtime State

### 2.1 PostgreSQL - Docker Container

| Property | Value | Evidence |
|---|---|---|
| Container name | `guinevere-postgres` | P0-014 postgres-status.txt |
| Host port | 127.0.0.1:5433 -> 5432 | P0-014 |
| Status | Up (healthy) | P1 evidence |
| systemd service? | **NO** | P0-000 service-inventory |

### 2.2 Redis - Docker Container

| Property | Value | Evidence |
|---|---|---|
| Container name | `guinevere-redis` | P0-021 summary |
| Host port | 127.0.0.1:6380 -> 6379 | P0-021 |
| Status | Up (13+ hours) | P1 evidence |
| systemd service? | **NO** | P0-000 service-inventory |

### 2.3 PgBouncer - Docker Container

| Property | Value | Evidence |
|---|---|---|
| Container name | `guinevere-pgbouncer` | P1 evidence |
| Host port | 127.0.0.1:5434 | P1 evidence |
| systemd service? | **NO** | P0-000 service-inventory |


## 3. Systemd Service Inventory (Current VPS State)

### 3.1 Existing Guinevere Services

| Service Name | Status | Evidence |
|---|---|---|
| `guinevere-9router.service` | Active (running), enabled | P1-007 auditor report |
| `guinevere.slice` | Active | P1-007 auditor report |
| `guinevere-prune-weekly@.service` | File exists in repo | `scripts/guinevere-prune-weekly@.service` |
| `guinevere-backup@.service` | File exists in repo | `scripts/guinevere-backup@.service` |
| `guinevere-core.service` | **DOES NOT EXIST YET** | Being created in P1-018 |

### 3.2 Service Names That DO NOT Exist (Mythical)

| Name | Referenced In | Reality |
|---|---|---|
| `postgresql.service` | StepPrompts.md line 4817-4818 (P1-018 template) | **Does not exist** - PG is Docker container |
| `redis-guinevere.service` | StepPrompts.md line 4817-4818 (P1-018 template) | **Does not exist** - Redis is Docker container |
| `postgresql@17-guinevere.service` | `scripts/preflight-check.sh` line 142 | **Does not exist** - planned future state |

### 3.3 Correct Dependency Analysis

Since both PostgreSQL and Redis are Docker containers, the correct dependency chain is:

```
network-online.target
    |
    v
docker.service (Docker daemon - manages all containers)
    |
    v
guinevere-core.service
```

The DeploymentGuide v1.0 (lines 1096-1098) confirms this pattern:
```ini
After=network-online.target docker.service pgbouncer.service
Requires=docker.service
```

---

## 4. guinevere.slice Definition

**Status**: Already defined and active
**File**: `/etc/systemd/system/guinevere.slice` (deployed via P0-009)

**Configuration** (from `docs/setup-evidence/P0/STEP-P0-009/guinevere-slice.conf`):
```ini
[Unit]
Description=Guinevere resource control slice (8GB RAM, 2 CPU core quota) per ADR-014
Before=slices.target

[Slice]
MemoryMax=8G
MemoryHigh=7G
CPUQuota=200%
IOWeight=50
TasksMax=512
```

**Confirmed active**: P1-007 auditor report shows `CGroup: /guinevere.slice/guinevere-9router.service`


## 5. guinevere-9router.service - Reference Pattern

**Full unit** (from StepPrompts.md line 3733-3755, deployed P1-006):
```ini
[Unit]
Description=Guinevere 9Router LLM Proxy
After=network-online.target

[Service]
Type=simple
User=guinevere
WorkingDirectory=/home/guinevere/code/guinevere
EnvironmentFile=/home/guinevere/code/guinevere/secrets/.env.9router
Environment=DATA_DIR=/home/guinevere/.9router
Environment=PORT=20128
Environment=HOSTNAME=0.0.0.0
ExecStart=9router --port 20128 --host 0.0.0.0 --no-browser --skip-update
Restart=always
RestartSec=5
Slice=guinevere.slice

[Install]
WantedBy=multi-user.target
```

**Key observations**:
- No database dependencies (correct - 9Router does not need PG/Redis)
- `Slice=guinevere.slice` - resource control via cgroup
- `EnvironmentFile=` for secrets (not plaintext)
- `Restart=always` with `RestartSec=5`

---

## 6. StepPrompts P1-018 Template - Bug Analysis

### Current (Buggy) Template (StepPrompts.md lines 4814-4841)
```ini
[Unit]
Description=Guinevere Core Daemon
After=network.target postgresql.service redis-guinevere.service guinevere-9router.service   # BUG
Requires=postgresql.service redis-guinevere.service                                          # BUG

[Service]
Type=simple
User=guinevere
...
ExecStart=/home/guinevere/code/guinevere/.venv/bin/uvicorn src.core.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Slice=guinevere.slice
```

### Bugs Identified

| Line | Issue | Correct Value |
|---|---|---|
| 4817 | `After=postgresql.service redis-guinevere.service` | `After=docker.service` |
| 4818 | `Requires=postgresql.service redis-guinevere.service` | `Requires=docker.service` |
| 4817 | Missing `docker.service` in After | Add `docker.service` after `network.target` |

### This bug was ALREADY FIXED for guinevere-9router.service in P1-006

P1-006 evidence (line 18) and batch-plan-006-007.md note: `redis-guinevere.service dependency removed`. But P1-012 was **Ollama (SKIPPED)**, not PG/Redis systemd creation. So systemd services for PG/Redis were **never created**.

The preflight-check.sh expects `postgresql@17-guinevere.service` and `redis-guinevere.service` to exist - this reflects a **desired future state** never implemented.


## 7. Recommendations for P1-018

### Correct systemd unit for guinevere-core.service:

```ini
[Unit]
Description=Guinevere Core Daemon
After=network.target docker.service guinevere-9router.service
Requires=docker.service
Wants=guinevere-9router.service

[Service]
Type=simple
User=guinevere
WorkingDirectory=/home/guinevere/code/guinevere
EnvironmentFile=/home/guinevere/code/guinevere/secrets/.env.guinevere
Environment=PYTHONPATH=/home/guinevere/code/guinevere
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=/home/guinevere/code/guinevere/.venv/bin/uvicorn src.core.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Slice=guinevere.slice

NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/home/guinevere/code/guinevere /home/guinevere/data /home/guinevere/logs /home/guinevere/evidence

[Install]
WantedBy=multi-user.target
```

### Key Changes from Current StepPrompts Template:

1. **`Requires=docker.service`** - replaces `Requires=postgresql.service redis-guinevere.service` (Docker manages PG/Redis containers)
2. **`After=network.target docker.service guinevere-9router.service`** - replaces broken service name references
3. **`Wants=guinevere-9router.service`** - soft dependency: core can start without 9Router (graceful degradation)
4. **`Slice=guinevere.slice`** - already in template, keep as-is

### Alternative if Future State Includes Native PG/Redis Services

If future steps create `postgresql@17-guinevere.service` and `redis-guinevere.service`, update to:
```ini
After=network.target postgresql@17-guinevere.service redis-guinevere.service guinevere-9router.service
Requires=postgresql@17-guinevere.service redis-guinevere.service
```
This is NOT the current state. For now, `docker.service` is correct.

---

## 8. Source Files Index

| File | Relevance |
|---|---|
| `docs/setup-evidence/P0/STEP-P0-000/service-inventory.md` | No host-level PG/Redis services |
| `docs/setup-evidence/P0/STEP-P0-009/guinevere-slice.conf` | guinevere.slice definition |
| `docs/setup-evidence/P0/STEP-P0-014/postgres-status.txt` | PostgreSQL Docker container |
| `docs/setup-evidence/P0/STEP-P0-021/p0-021-summary.md` | Redis ACL - Docker-based |
| `docs/setup-evidence/P1/STEP-P1-006/evidence.md` | Deferred redis-guinevere.service |
| `docs/setup-evidence/P1/batch-plan-006-007.md` | Confirmed redis-guinevere.service bug |
| `stepprompts/StepPrompts.md` (lines 3731-3755) | 9router.service reference pattern |
| `stepprompts/StepPrompts.md` (lines 4814-4841) | **BUGGY** P1-018 template |
| `research-reports/P1/vps-state-pre-p1-015-016.md` | Current VPS service inventory |
| `scripts/preflight-check.sh` | Desired future state (not current) |
| `docs/40-operations/44-DeploymentGuide_v1.0.md` (lines 1090-1159) | Correct pattern: `Requires=docker.service` |

---

## 9. Verification Summary

- PostgreSQL: Docker container (guinevere-postgres), NOT systemd service
- Redis: Docker container (guinevere-redis), NOT systemd service
- PgBouncer: Docker container (guinevere-pgbouncer), NOT systemd service
- guinevere.slice: EXISTS, deployed, active (P0-009)
- guinevere-9router.service: EXISTS, active, under guinevere.slice
- postgresql.service: DOES NOT EXIST (StepPrompts P1-018 template - BUG)
- redis-guinevere.service: DOES NOT EXIST (StepPrompts P1-018 template - BUG)
- postgresql@17-guinevere.service: DOES NOT EXIST (preflight-check future state)

---

*Report compiled by Guinevere on 2026-06-01. File-based evidence from P0/P1 documentation suite.*
