# P22 Production Activation — Backup Evidence (T2)

**Date:** 2026-06-27
**Step:** T2 — Backup production DB + code snapshot (BEFORE migration/deploy)
**Operator mode:** Full autonomous (per-action approved)
**VPS:** faiz-prod-01 via `ssh guinevere-vps`

## What Was Done

Pre-deploy backup of the production Guinevere DB + code tree, performed BEFORE any migration or code deploy. Both artifacts written to `/home/guinevere/data/backups/`.

## DB Backup

| Field | Value |
|---|---|
| Command | `docker exec guinevere-postgres pg_dumpall -U guinevere --no-role-passwords \| gzip -9` |
| Container | `guinevere-postgres` (PostgreSQL 16 + pgvector) |
| Role | `guinevere` (DB superuser, canonical backup role per `scripts/guinevere-backup-docker.sh`) |
| Timestamp | `20260627T150750Z` |
| Path | `/home/guinevere/data/backups/guinevere-p22-predeploy-20260627T150750Z.sql.gz` |
| Size | 1,381,128,913 bytes (~1.38 GB) — > 1 GB threshold ✓ |
| Exit code | 0 ✓ |
| sha256 | generated → `…sql.gz.sha256` |

**stderr (benign):** `pg_dump: warning: circular foreign-key constraints on continuous_agg` — TimescaleDB continuous aggregate; restore may need `--disable-triggers`. Does not affect P22 migration (P22 creates NEW tables, does not touch continuous_agg).

**No secrets in backup:** `--no-role-passwords` flag used; role passwords not captured. Backup file stored under `/home/guinevere/data/backups/` (owner `guinevere`, not offloaded).

## Code Snapshot

| Field | Value |
|---|---|
| Command | `cp -a /home/guinevere/code/guinevere …/guinevere-code-bak-<TS>` then strip `.env*` + `.venv` |
| Path | `/home/guinevere/data/backups/guinevere-code-bak-20260627T150750Z` |
| `.env` files in snapshot | 0 (stripped via `find … -name '.env*' -delete`) ✓ |
| `.venv` | removed (saves ~500 MB) |

## Disk

- `/dev/vda1` 99G total, 56G used, **39G free** (> 15 GB threshold) ✓

## Rollback Readiness

- DB restore: `gunzip -c …sql.gz | docker exec -i guinevere-postgres psql -U guinevere` (may need `--disable-triggers` for continuous_agg).
- Code restore: `mv …/guinevere …/guinevere.failed-p22 && cp -a …/guinevere-code-bak-<TS> …/guinevere`.
- WORM caveat: `audit.integration_api_log` is new (empty pre-migration); rollback is code-only per plan §8.3 if rows exist post-migration.

## Verification

- [x] DB backup > 1 GB
- [x] sha256 generated
- [x] No `.env` files in code snapshot
- [x] pg_dumpall exit 0
- [x] Disk > 15 GB free
- [x] No secret values printed in this evidence

## Footer

Backup complete and verified. Safe to proceed to T3 (deploy code) and T5 (apply migration).
