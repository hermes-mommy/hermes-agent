# STEP-P0-014 — PostgreSQL Deployment Verification

| Field | Value |
|---|---|
| **Step** | P0-014 |
| **Type** | Infrastructure |
| **Date** | 2026-05-31 |
| **Implementer** | Guinevere (parent orchestrator) |
| **Status** | PASS, independent auditor gate passed |

## What Was Done

Deployed PostgreSQL 16.14 as a Docker container on `guinevere-net`, bound to `127.0.0.1:5433` (loopback-only). Created `guinevere` database, configured per ADR-027 shared VPS resource allocation (shared_buffers=1GB, max_connections=100).

## Files Changed

### Remote (VPS)
| File | Action |
|---|---|
| `guinevere-postgres` (container) | Created (postgres:16, 172.28.0.2) |
| `/home/guinevere/data/postgres` | Created (volume) |
| `/home/guinevere/data/postgres/guinevere.conf` | Created |

### Local (repo)
| File | Action |
|---|---|
| `docs/setup-evidence/P0/STEP-P0-014/postgres-status.txt` | Created |
| `docs/setup-evidence/P0/STEP-P0-014/aizanta-post-check.md` | Created |
| `docs/setup-evidence/P0/STEP-P0-014/p0-014-summary.md` | Created |
| `docs/setup-evidence/P0/STEP-P0-014/verification.md` | Created |
| `PROGRESS.md` | Updated: 14→15/257, P0 14→15/29 |
| `CHECKLIST.md` | P0-014 checked |
| `stepprompts/StepPrompts.md` | P0-014 status → ✅ Completed |

## Validation Results

### Container Status
```
$ docker ps --filter name=guinevere-postgres --format '{{.Names}} {{.Status}} {{.Ports}}'
guinevere-postgres Up (healthy) 127.0.0.1:5433->5432/tcp
```

### Connectivity
```
$ pg_isready -h 127.0.0.1 -p 5433 -U guinevere -d guinevere
127.0.0.1:5433 - accepting connections
```

### Database & Version
```
$ psql -h 127.0.0.1 -p 5433 -U guinevere -d guinevere -c "SELECT version(), current_database(), current_user;"
PostgreSQL 16.14 (Debian 16.14-1.pgdg120+2)
 current_database | guinevere
 current_user     | guinevere
```

### Configuration
```
 shared_buffers = 1GB
 timezone = Asia/Jakarta
 max_connections = 100
 work_mem = 16MB
 effective_cache_size = 3GB
 maintenance_work_mem = 256MB
```

### Network Isolation
```
$ docker network inspect guinevere-net --format '{{range .Containers}}{{.IPv4Address}}{{end}}'
172.28.0.2/16

$ docker network ls
aizanta_aizanta-internal  172.18.0.0/16  (Aizanta)
guinevere-net             172.28.0.0/16  (Guinevere)
bridge                    172.17.0.0/16  (Docker default)
```

### Aizanta Health
```
aizanta-bot       Up 7 days (healthy)
aizanta-nginx     Up 7 days (healthy)
aizanta-frontend  Up 8 days (healthy)
aizanta-postgres  Up 8 days (healthy)
aizanta-redis     Up 8 days (healthy)
```

### Protected Ports
```
127.0.0.1:6379  docker-proxy (Aizanta Redis)     — unchanged
100.94.104.22:80 docker-proxy (Aizanta nginx)    — unchanged
127.0.0.1:5432  docker-proxy (Aizanta PostgreSQL) — unchanged
127.0.0.1:5433  docker-proxy (Guinevere PostgreSQL) — NEW
```

### SSH
```
$ ssh guinevere-vps "whoami && hostname"
guinevere  faiz-prod-01
```

## Evidence Artifacts

| File | Description |
|---|---|
| `postgres-status.txt` | Container status, connectivity, config, rollback |
| `aizanta-post-check.md` | Aizanta containers/ports/network health |
| `p0-014-summary.md` | Human-readable summary |
| `verification.md` | This file |

## Shared VPS Impact

- **Aizanta containers**: 5/5 healthy, no restarts, ports unchanged
- **Aizanta networks**: Separate `aizanta_aizanta-internal` (172.18.0.0/16) — no conflict with guinevere-net
- **Resource**: ~150MB RAM baseline (shared_buffers=1GB allocated), ~27MB disk
- **Ports**: 5433 is loopback-only, no conflict with Aizanta 5432

## ADR Compliance

| ADR | Status |
|---|---|
| ADR-014 (VPS/container architecture) | Compliant — Docker container, isolated network |
| ADR-015 (Secrets management) | Compliant — password generated with openssl rand, ready for SOPS encryption (P0-013 complete) |
| ADR-027 (Self-hosted PostgreSQL) | Compliant — PostgreSQL 16, loopback-only, Docker with volume persistence, configured per shared VPS limits |

## AC Reference

| AC | Status |
|---|---|
| AC-CORE-001 (systemd-managed core daemon) | Partial — PostgreSQL is Docker-managed, not systemd. ADR-014 allows selective containerization. |
| AC-CORE-002 (service resilience) | Compliant — Docker restart policy + health check |
| AC-DATA-001 (persistent storage) | Compliant — Volume at `/home/guinevere/data/postgres` |

## Rollback / Re-run Safety

**Rollback**:
```bash
docker stop guinevere-postgres && docker rm guinevere-postgres
# Optionally remove volume:
sudo rm -rf /home/guinevere/data/postgres
```

**Re-run safety**: Container would fail due to port conflict (5433 already bound). Stop existing first.

## Design Decisions / Caveats

1. **Docker vs systemd**: PostgreSQL deployed as Docker container per user directive. ADR-014 allows selective containerization.
2. **Loopback-only**: 127.0.0.1:5433 — not exposed to Tailscale or public. Penggunaan internal only.
3. **Superuser guinevere**: Single user for now; will split into `guinevere_core`, `surveillance`, `scheduler` in P0-017.
4. **Password**: Generated with `openssl rand -hex 32`, stored in Docker container env only. Not in any evidence file. Ready for SOPS encryption in later steps.
5. **Config**: `guinevere.conf` at `/home/guinevere/data/postgres/guinevere.conf` mounted via Docker bind.

## Evidence Gate

| Gate | Status |
|---|---|
| Parent verification | PASS — pg_isready, psql test, SHOW config, Aizanta healthy, ports OK, SSH works |
| Evidence files | 4 evidence files created |
| Diagnostics | Clean |
| Secret scan | No password/API key/private key matches |
| Tracker sync | PROGRESS, CHECKLIST, StepPrompts synced |
| Independent auditor gate | PASS — `audit-reports/P0/STEP-P0-014/step-p0-014-auditor-report.md` (2 minor findings, 0 blocking) |

## Footer

**Source task**: STEP-P0-014 (from `stepprompts/StepPrompts.md`)
**Date**: 2026-05-31
**Implementer**: Guinevere (parent orchestrator, via direct SSH)
**Validation method**: Live SSH command execution + output capture