# STEP-P0-014 — PostgreSQL Deployment Summary

## What Was Done

Deployed PostgreSQL 16.14 as a Docker container on `guinevere-net` (172.28.0.2), bound to `127.0.0.1:5433`. Created `guinevere` database with `guinevere` superuser. Tuned configuration for the 8GB RAM allocation per ADR-014 and 100-connection ceiling per StepPrompts.

## Runtime Changes (VPS)

| Change | Details |
|---|---|
| Container | `guinevere-postgres` (image: `postgres:16`, resolved `16.14-trixie`) |
| Network | `guinevere-net`, IP 172.28.0.2 |
| Port binding | `127.0.0.1:5433:5432` |
| Database | `guinevere` with owner `guinevere` |
| Volume | `/home/guinevere/data/postgres` |
| Config | `guinevere.conf`: shared_buffers=1GB, timezone=Asia/Jakarta, max_connections=100, work_mem=16MB, effective_cache_size=3GB, maintenance_work_mem=256MB |

## Local Changes

| File | Action |
|---|---|
| `docs/setup-evidence/P0/STEP-P0-014/postgres-status.txt` | Created |
| `docs/setup-evidence/P0/STEP-P0-014/aizanta-post-check.md` | Created |
| `docs/setup-evidence/P0/STEP-P0-014/p0-014-summary.md` | Created |
| `docs/setup-evidence/P0/STEP-P0-014/verification.md` | Created |
| `PROGRESS.md` | Updated: 14→15/257, P0 14→15/29 |
| `CHECKLIST.md` | P0-014 checked |
| `stepprompts/StepPrompts.md` | P0-014 status → ✅ Completed |

## Validation

- `docker ps`: `guinevere-postgres Up (healthy)`
- `pg_isready -h 127.0.0.1 -p 5433 -U guinevere -d guinevere`: accepting connections
- `psql -c "SELECT version()"`: PostgreSQL 16.14
- `psql -c "SHOW shared_buffers"`: 1GB
- `psql -c "SELECT current_database()"`: guinevere
- Aizanta containers: 5/5 healthy, ports unchanged
- SSH alias: works

## Security

- PostgreSQL bind: `127.0.0.1:5433` only — not exposed to Tailscale or public internet
- Password: generated with `openssl rand -hex 32`, NOT stored in any evidence file
- UFW: no new rule needed (loopback-only)
- SOPS integration: P0-013 `.sops.yaml` ready for encrypted credential storage in later steps

## Rollback

```bash
docker stop guinevere-postgres
docker rm guinevere-postgres
sudo rm -rf /home/guinevere/data/postgres
```

## Caveats

- PostgreSQL runs as Docker container, not systemd. ADR-014 allows selective containerization; PostgreSQL is containerized per user directive.
- Superuser `guinevere` will be split into `guinevere_core`, `surveillance`, `scheduler` in P0-017.
- Volume ownership is `systemd-coredump:systemd-coredump` (Docker-internal UID 999) — acceptable for container-only access.