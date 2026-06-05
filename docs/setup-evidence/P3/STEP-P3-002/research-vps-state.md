# Research: Guinevere VPS State

**Date:** 2026-06-02
**Step:** P3-002
**Command:** ssh -F C:\Users\faizz\.ssh\config guinevere-vps

---

## 1. Directory Structure — /home/guinevere/code/guinevere/ (Top 2 Levels)

### Root level
| Entry | Type | Notes |
|---|---|---|
| lembic/ | dir | Migration scripts |
| lembic.ini | file | DB connection config |
| docs/ | dir | Documentation suite |
| scripts/ | dir | Backup, health-check, setup scripts |
| secrets/ | dir | SOPS-encrypted secrets, backup env files |
| src/ | dir | Application source (12 packages) |
| 	ests/ | dir | Test suite |
| stepprompts/ | dir | Step prompts |
| 	mp/ | dir | Temp setup/verify scripts |
| .venv/ | dir | Python virtual environment |
| .git/ | dir | Git repository |
| .sops.yaml | file | SOPS config (AGE key reference) |
| pyproject.toml | file | Project config + dependencies |
| uv.lock | file | UV lock file (452KB) |
| README.md | file | Minimal README |

### src/ packages
core, discord, inancial, loops, mcp, memory, observability, persona, surveillance

### lembic/ structure
- env.py — Async multi-schema env with GUINEVERE_DB_PASSWORD injection
- script.py.mako — Migration template
- ersions/ — 2 migration files:
  - 2bed93fd1dd0_baseline_init.py (741 bytes)
  - e401bb5fd274_initial_schema_47_tables.py (77,190 bytes)

### docs/setup-evidence/P3/
- STEP-P3-001/ — Contains earlier step evidence
- STEP-P3-002/ — Contains current step evidence

### scripts/
- guinevere-backup.sh (Docker Edition v2)
- guinevere-backup-docker.sh
- Systemd timer/service files for backup/prune
- health-check-p1.sh, preflight-check.sh, setup-guild.sh, etc.

### secrets/
- .env.9router — 9Router env (SOPS source)
- .env.9router.sops — SOPS-encrypted 9Router env
- discord-secrets.yaml — Discord bot secrets (SOPS-encrypted)
- ackup/ — Backend backup credentials (Cloudflare R2, IDCloudHost S3, restic password)

---

## 2. Database Connection String (alembic.ini)

**File:** /home/guinevere/code/guinevere/alembic.ini

`
sqlalchemy.url = postgresql+asyncpg://guinevere_core:****@127.0.0.1:5433/guinevere
`

- **User:** guinevere_core
- **Password:** Masked as **** — resolved at runtime via GUINEVERE_DB_PASSWORD environment variable
- **Host:** 127.0.0.1 (via pgbouncer on 5433 → postgres on 5432)
- **Port:** 5433 (pgbouncer port)
- **Database:** guinevere
- **Driver:** syncpg
- **Password Mechanism:** In lembic/env.py, the :****@ placeholder is replaced with the actual password from os.environ.get("GUINEVERE_DB_PASSWORD", "").

---

## 3. Backup Checkpoint Evidence

**File:** /home/guinevere/code/guinevere/docs/setup-evidence/P3/STEP-P3-002/backup-checkpoint-20260602.md

**Verdict:** ✅ PASS WITH MARKER CAVEAT

Key findings:
- Pre-migration backup executed: # guinevere-backup.sh (Docker Edition v2)
- PostgreSQL dump via docker exec guinevere-postgres pg_dumpall -U guinevere — 4318 bytes
- Redis SAVE produced NOAUTH Authentication required warning (non-fatal, treated as informational)
- Primary restic snapshot: 13159f70 (S3: is3.cloudhost.id/s3-guinevere)
- Secondary restic snapshot: 13c66a7c
- Caveat: /var/log/guinevere/last-backup-success marker missing — the Docker Edition v2 script does not write it

---

## 4. Migration Verification Evidence

**File:** /home/guinevere/code/guinevere/docs/setup-evidence/P3/STEP-P3-002/verification.md

**Verdict:** ✅ Implementation applied (verifier/auditor gates pending at time of writing)

Key findings:
- lembic current → e401bb5fd274 (head)
- lembic heads → e401bb5fd274 (head)
- lembic check → No new upgrade operations detected.
- Model import: REMOTE_IMPORT_OK
- SQLAlchemy metadata table count: **47**
- 12 canonical schemas created and verified
- 48 base tables in canonical schemas (47 app tables + ops.alembic_version)
- 4 TimescaleDB hypertables created: udit.audit_trail, inancial.transactions, memory.episodes, surveillance.events
- 2 HNSW pgvector indexes created: memory.ix_episodes_embedding_hnsw, memory.ix_semantic_facts_embedding_hnsw
- Retention policies active on 3 hypertables (audit, financial, surveillance)
- Compression policies **deferred** — will be done in a later migration
- Aizanta port 5432 untouched

---

## 5. Alembic Directory

**Path:** /home/guinevere/code/guinevere/alembic/ ✅ Exists

| Item | Details |
|---|---|
| env.py | Async env with GUINEVERE_DB_PASSWORD substitution, schema filtering |
| README | Alembic README |
| script.py.mako | Migration file template |
| ersions/ | Directory containing migration revisions |
| Version 1 | 2bed93fd1dd0_baseline_init.py — Baseline/empty init |
| Version 2 | e401bb5fd274_initial_schema_47_tables.py — Full 47-table schema |

---

## 6. Python Virtual Environment

**Path:** /home/guinevere/code/guinevere/.venv/ ✅ Exists (not env/)

- **Python version:** 3.12.3
- **Type:** Standard virtual environment (venv)
- **Content:** in/, include/, lib/, lib64 -> lib, optional-skills/, skills/, pyvenv.cfg
- **Skills directory:** 27 installed packages in skills/, 19 in optional-skills/
- **UV lock file:** uv.lock (452KB) present at project root

---

## 7. PostgreSQL Connection Health

**Connection method:** docker exec guinevere-postgres psql -U guinevere -d guinevere

### Connection info
- You are connected to database guinevere as user guinevere via socket at port 5432
- PostgreSQL version: **16.14 (Debian 16.14-1.pgdg13+1)** with TimescaleDB + pgvector
- Container name: guinevere-postgres
- Image: guinevere-postgres-pgvector:16 (custom image with pgvector + TimescaleDB)
- Port mapping: 127.0.0.1:5433->5432/tcp (pgbouncer on 5433 → postgres on 5432)

### Docker containers running on VPS
| Container | Image | Ports |
|---|---|---|
| guinevere-postgres | guinevere-postgres-pgvector:16 | 5433→5432 |
| guinevere-pgbouncer | percona/percona-pgbouncer:1.25.2 | 5434→5432 |
| guinevere-redis | redis:7.4-alpine | 6380→6379 |
| izanta-postgres | postgres:16-alpine | 5432→5432 (Aizanta, separate) |
| izanta-redis | redis:7.2-alpine | 6379→6379 |
| Others | aizanta-bot, aizanta-nginx, aizanta-frontend | |

### PostgreSQL schemas (23 total)
- **12 canonical guinevere schemas:** gents, udit, consent, extensions, inancial, memory, ops, persona, projects, security, social, surveillance
- **TimescaleDB internal schemas:** _timescaledb_cache, _timescaledb_catalog, _timescaledb_config, _timescaledb_functions, _timescaledb_internal, _timescaledb_experimental, _timescaledb_information
- **System schemas:** config, loops, pgbouncer, public

### Application tables (count: 93 total non-system tables including TimescaleDB internal)
- 47 canonical application tables (across 12 schemas)
- Plus TimescaleDB internal tables (chunk, dimension, hypertable, etc.)

### Health check: ✅ **PASS** (SELECT 1 returned 1 row)

---

## Summary

| Check | Status | Details |
|---|---|---|
| Directory structure | ✅ | Well-organized, 12 src packages |
| alembic.ini connection | ✅ | guinevere_core:****@127.0.0.1:5433/guinevere via env var |
| Backup checkpoint exists | ✅ | ackup-checkpoint-20260602.md — PASS with marker caveat |
| Verification exists | ✅ | erification.md — Implementation applied, auditor pending |
| Alembic directory | ✅ | 2 migration versions (baseline + 47-table schema) |
| Python venv | ✅ | .venv/ with Python 3.12.3 |
| PG connection | ✅ | PostgreSQL 16.14 + TimescaleDB + pgvector — healthy |

### Caveats / Follow-ups
1. **Compression policy deferred** — TimescaleDB hypertables created but compression DDL not yet applied
2. **last-backup-success marker missing** — Docker Edition v2 script needs patching
3. **Verifier/auditor gates pending** — Not yet completed for P3-002
4. **DB password is env-var only** — No .env file at project root; password must be set in shell/service environment
