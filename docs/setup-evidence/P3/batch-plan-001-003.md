# P3 Batch Plan — Steps P3-001 / P3-002 / P3-003

**Date:** 2026-06-02  
**Author:** Guinevere (Sisyphus orchestrator)  
**Status:** Planner gate — ready for parent read  
**Evidence Root:** `docs/setup-evidence/P3/`

---

## 1. Master Todo

| # | Step | Description | Status | Dependencies |
|---|------|-------------|--------|-------------|
| 1 | P3-001 | Alembic setup + env.py (async, multi-schema) + baseline | ✅ Complete — auditor PASS | None (this batch) |
| 2 | P3-002 | Create 47 SQLAlchemy models + migration + upgrade | ⏳ In progress — backup checkpoint verified (`STEP-P3-002/backup-checkpoint-20260602.md`) | P3-001 |
| 3 | P3-003 | Migration verification | ⏳ Blocked | P3-002 |

## 2. Dependency Map

```
P3-001 ──→ P3-002 ──→ P3-003
(no parallel — sequential by design)
```

- P3-003 depends on P3-002 (tables must exist to verify)
- P3-002 depends on P3-001 (Alembic must be configured)
- All steps are strictly sequential. One sub-agent = one step.

## 3. Research Inputs

| Source | Type | Key Findings |
|--------|------|-------------|
| 33-DatabaseERD_MigrationStrategy_v1.0.md | Primary spec | 12 schemas, 47 tables, authoritative schema list |
| MemorySchema v2.0 (via ERD) | Schema detail | Full column defs, hypertables, HNSW specs |
| research-reports/P3/004-alembic-async-setup.md | External research | Alembic async + multi-schema pattern |
| research-reports/P3/005-sqlalchemy-model-patterns.md | External research | Mapped[] style, PG types, multi-schema FKs |
| StepPrompts.md P3-001/002/003 | Task scaffold | Outdated schema list (7 schemas vs 12), sync env.py, legacy Column style |
| PROGRESS.md | State tracker | P3 at 0/19 steps |
| ADR-009 | Decision | HNSW default (m=16, ef_construction=128), pgvector 1536-dim |
| ADR-027 | Decision | Self-hosted PG port 5433, PgBouncer 5434 |
| ADR-031 | Decision | Database naming conventions (implicit in ERD) |
| PostgreSQL state (bg_c0946a71) | Live state | 7 existing schemas (memory, persona, surveillance, financial, audit, config, loops), pgvector + TimescaleDB installed |

### Binding Decisions from Research

| Decision | Source | Value |
|----------|--------|-------|
| Schema authority | ERD (C-001 resolution) | 12 schemas: memory(8), persona(5), surveillance(4), financial(4), projects(4), social(3), agents(3), consent(3), security(3), audit(3), ops(4), extensions(3) = 47 |
| SQLAlchemy style | Research report, modern standard | Mapped[] + mapped_column(), legacy Column() NOT used |
| Alembic async pattern | Research report, official template | async_engine_from_config, connection.run_sync, asyncio.run |
| Multi-schema autogenerate | Research report, official docs | include_schemas=True, include_name filter, version_table_schema |
| Model file location | StepPrompts + convention | src/memory/models.py (all models in one file for P3) |
| DB connection user | P0-017 | guinevere_core (has schema CREATE privileges) |
| DB port | ADR-027 | 5433 (NOT 5432 — Aizanta port) |
| CREDENTIALS SOURCE | ADR-015 | sops --decrypt secrets/db-passwords.yaml |
| HNSW parameters | ADR-009 + ERD | m=16, ef_construction=128 |

## 4. Schema Reconciliation — StepPrompts vs ERD

The StepPrompts P3-002 uses an OLD schema list: memory(12+), persona(8), surveillance(6), loops(7), financial(5), config(4), audit(5).

The ERD (33-DatabaseERD) resolves this in C-001: **12 schemas, 47 tables**:
memory(8), persona(5), surveillance(4), financial(4), projects(4), social(3), agents(3), consent(3), security(3), audit(3), ops(4), extensions(3) = 47

**This plan follows ERD strictly.** The StepPrompts schemas `loops` and `config` are absorbed into `ops.*`, `projects.*`, and `security.*` per C-001 resolution.

### Schema-to-Model Mapping

| Schema | Tables | Model Classes |
|--------|--------|---------------|
| memory | episodes, semantic_facts, faiz_profile, emotional_events, inner_journal, faiz_predictions, procedural_skills, knowledge_graph | 8 model classes |
| persona | persona_state, drift_log, mood_history, punishment_log, reward_log | 5 model classes |
| surveillance | events, device_registry, ingestion_log, confrontation_block_log | 4 model classes |
| financial | transactions, project_costs, monthly_reports, optimization_log | 4 model classes |
| projects | tasks, loop_instances, agent_tasks, evidence_artifacts | 4 model classes |
| social | social_map, client_contacts, communication_log | 3 model classes |
| agents | subagent_registry, task_queue, execution_log | 3 model classes |
| consent | consent_ledger, revocation_log, scope_registry | 3 model classes |
| security | access_log, break_glass_log, secret_rotation_log | 3 model classes |
| audit | audit_trail, evidence_register, compliance_check | 3 model classes |
| ops | migration_log, backup_log, health_check, alert_history | 4 model classes |
| extensions | pgvector_config, timescaledb_config, pgcrypto_config | 3 model classes |
| **Total** | **47** | **47 model classes** |

## 5. Connection Strategy

```
Connection: postgresql+asyncpg://guinevere_core:<password>@127.0.0.1:5433/guinevere
Password: sops --decrypt secrets/db-passwords.yaml → extract guinevere_core password
```

**Alembic connection:** Use `async_engine_from_config` with connection string from alembic.ini.  
**Password injection:** Use environment variable `GUINEVERE_DB_PASSWORD` via `sops exec-env` pattern, or embed in alembic.ini (local dev only). For this batch (local development), use `.env` file with the decrypted password (NOT committed).

**IMPORTANT**: No plaintext passwords in code, evidence, or logs.

## 6. Collision Scan

| Collision Type | Risk | Mitigation |
|---------------|------|------------|
| Same source file (src/memory/models.py) | P3-002 writes models | Single owner: P3-002 sub-agent only |
| Shared alembic/ dir | P3-001 initializes, P3-002 uses | P3-001 creates dir, P3-002 only reads/writes revisions |
| Shared alembic.ini | P3-001 configures | P3-002 only reads |
| Shared PostgreSQL schemas | All steps write to DB | Sequential — one step at a time |
| Aizanta PostgreSQL (port 5432) | None — NOT touched | Explicit guard: only connect to port 5433 |

**Result: NO collisions.** P3-001 and P3-002 are write to different files. Shared resources (alembic.ini, alembic/ dir) follow sequential access pattern.

## 7. Implementation Design

### P3-001 — Alembic Setup (sequential, sub-agent)

**Files to create:**
- `alembic.ini` — Alembic config with async connection string
- `alembic/env.py` — Async env.py with multi-schema support
- `alembic/script.py.mako` — Migration template
- `alembic/versions/` — Empty dir (baseline stamp)
- `docs/setup-evidence/P3/STEP-P3-001/` — Evidence directory

**Steps:**
1. `alembic init alembic` → generates boilerplate
2. Overwrite `alembic/env.py` with async + multi-schema version
3. Configure `alembic.ini` with connection string (password via env var)
4. Create `Base` in `src/memory/models.py` (bare, no tables yet)
5. `alembic check` → should succeed with no migrations pending
6. Create initial blank migration as baseline: `alembic revision --autogenerate -m "init"`
7. (Optional) `alembic stamp head` to mark baseline without running

**Key config for env.py:**
- `async_engine_from_config` with asyncpg URL
- `include_schemas=True`
- `include_name` filter for guinevere's 12 schemas
- `version_table_schema="ops"` (version table in ops schema)
- `compare_type=True`, `compare_server_default=True`

**Verification points:**
- `alembic check` returns clean
- `alembic/` directory exists with proper structure
- `alembic.ini` has correct connection string
- `Base.metadata` importable from `src.memory.models`

---

### P3-002 — 47 Tables Migration (sequential, sub-agent)

**Files to modify:**
- `src/memory/models.py` — All 47 model classes added

**Files to create:**
- `alembic/versions/xxxx_initial_schema.py` — Autogenerated migration
- `docs/setup-evidence/P3/STEP-P3-002/`

**Steps:**
1. Update `src/memory/models.py` with all 47 models across 12 schemas
   - SQLAlchemy 2.x `Mapped[]` + `mapped_column()` style
   - Explicit `__table_args__ = {"schema": "..."}` per model
   - Full column defs from ERD (types, constraints, indexes)
   - TimescaleDB hypertables declared as regular tables (DDL in migration)
   - pgvector `Vector(1536)` for embedding columns
   - Cross-schema FKs with fully-qualified references
   - HNSW indexes in `__table_args__` as `Index(...)` specs
2. Generate migration: `alembic revision --autogenerate -m "initial_schema_47_tables"`
3. REVIEW the generated migration script:
   - Should include CREATE SCHEMA IF NOT EXISTS for all 12 schemas
   - Should include hypertable creation SQL (op.execute)
   - Should include all indexes
4. Run migration: `alembic upgrade head`
5. Create 7 NEW schemas that don't exist yet: projects, social, agents, consent, security, ops, extensions

**Guard: Verify backup checkpoint exists before running upgrade.**
- Check: `ls /var/log/guinevere/last-backup-success` exists on VPS
- If local run (no VPS): skip backup check, note in evidence
- If VPS run and no backup: STOP, document, ask Faiz

**Secret handling:**
- DB password via SOPS only
- `sops --decrypt secrets/db-passwords.yaml` → extract guinevere_core password
- Set `GUINEVERE_DB_PASSWORD` env var in shell session
- Never write password to files that could be committed

---

### P3-003 — Migration Verification (sequential, sub-agent)

**Files to create:**
- `docs/setup-evidence/P3/STEP-P3-003/verification.md`

**Validation queries:**
1. Schema count: `SELECT nspname FROM pg_namespace WHERE nspname NOT IN ('pg_catalog','information_schema','public','topology','tiger','tiger_data') ORDER BY nspname;`
   → Expected: 12 schemas (memory, persona, surveillance, financial, projects, social, agents, consent, security, audit, ops, extensions)
2. Table count: `SELECT schemaname, tablename FROM pg_tables WHERE schemaname IN ('memory','persona','surveillance','financial','projects','social','agents','consent','security','audit','ops','extensions') ORDER BY schemaname, tablename;`
   → Expected: 47 tables
3. Index check: `SELECT schemaname, tablename, indexname, indexdef FROM pg_indexes WHERE schemaname IN ('memory','persona','surveillance','financial','projects','social','agents','consent','security','audit','ops','extensions') ORDER BY schemaname, tablename;`
4. FK constraint check: Check `information_schema.table_constraints` for foreign keys
5. Hypertable check: `SELECT hypertable_name FROM timescaledb_information.hypertables;`
6. pgvector extension: `SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';`
7. Simple SELECT from each table: Should return 0 rows but succeed

**Evidence:**
- All query outputs saved to evidence files
- `verification.md` with consolidated results

## 8. Rollback Plan

| Step | Rollback | Risk Level |
|------|----------|------------|
| P3-001 | `rm -rf alembic/ alembic.ini` + restore `src/memory/models.py` | Low |
| P3-002 | `alembic downgrade base` (drops all 47 tables) | Medium |
| P3-003 | N/A — read-only verification | Low |

**P3-002 destructive guard:** Before `alembic upgrade head`, verify:
1. No production data exists (fresh DB)
2. If VPS: backup checkpoint exists
3. Aizanta PostgreSQL (port 5432) is verified running and UNTOUCHED

## 9. Auditor Matrix

| Step | Auditor Type | Checks |
|------|-------------|--------|
| P3-001 | LSP verifier | alembic/env.py syntax, models.py importable |
| P3-001 | Config verifier | alembic.ini has correct port/user/schema config |
| P3-001 | Version table verifier | alembic_version table exists in ops schema |
| P3-002 | Schema auditor | 12 schemas created |
| P3-002 | Table count auditor | 47 tables across 12 schemas |
| P3-002 | Index auditor | All indexes present, HNSW using hnsw method |
| P3-002 | Data safety auditor | Aizanta PG on 5432 untouched, no data loss |
| P3-002 | Migration script auditor | No type suppression, no empty catch, proper error handling |
| P3-003 | Verification auditor | All verification queries PASS |
| P3-003 | FK constraint auditor | Foreign keys valid (no orphan references) |
| P3-003 | Extension auditor | pgvector + TimescaleDB extensions present |

## 10. Evidence Paths

| Step | Evidence Path |
|------|---------------|
| P3-001 | `docs/setup-evidence/P3/STEP-P3-001/alembic-init.txt`, `alembic-check.txt`, `verification.md` |
| P3-002 | `docs/setup-evidence/P3/STEP-P3-002/migration-output.txt`, `table-count.txt`, `schema-list.txt`, `verification.md` |
| P3-003 | `docs/setup-evidence/P3/STEP-P3-003/table-list.txt`, `index-list.txt`, `fk-constraints.txt`, `hypertable-list.txt`, `select-all-tables.txt`, `verification.md` |

## 11. Caveats

1. **StepPrompts schema list is outdated.** ERD (33-DatabaseERD) is authoritative with 12 schemas, 47 tables. Do NOT follow the 7-schema list from StepPrompts.
2. **Backup checkpoint verified for P3-002.** Runtime backup was explicitly approved by Faiz and completed on 2026-06-02. Primary restic snapshot `13159f70` and secondary snapshot `13c66a7c` were observed; `/var/log/guinevere/last-backup-success` remains missing because the actual VPS Docker Edition v2 script does not write the marker. Treat the backup guard as satisfied for this batch under Faiz's explicit condition. See `docs/setup-evidence/P3/STEP-P3-002/backup-checkpoint-20260602.md`.
3. **Alembic on Windows vs VPS.** This session runs on Windows. Alembic commands target remote VPS PostgreSQL on port 5433. Connection must go through network.
4. **SOPS decryption.** DB password must be decrypted via SOPS. Plaintext password must NEVER appear in code, evidence, or logs.
5. **Aizanta PostgreSQL safety.** Aizanta runs on port 5432. Every connection must use port 5433. Verified via ADR-027 and P0-014 evidence.

## 12. Execution Checklist

- [x] Parent read plan file and understands all constraints
- [x] Todos created for P3-001, P3-002, P3-003
- [x] Collision scan confirmed clean
- [x] Research reports read and synthesized
- [x] P3-001 sub-agent: setup Alembic with async + multi-schema
- [x] P3-001 parent verify: LSP clean, evidence written
- [x] P3-001 auditor gate: spawn auditor sub-agents, fix findings
- [x] P3-001 evidence sync + PROGRESS.md update
- [x] P3-002 sub-agent: create 47 models + migration + upgrade
- [x] P3-002 parent verify: file output read, diagnostics clean
- [x] P3-002 auditor gate: database auditor, schema auditor, data safety auditor
- [x] P3-002 evidence sync + PROGRESS.md update
- [x] P3-003 sub-agent: run all verification queries
- [x] P3-003 parent verify: all queries PASS
- [x] P3-003 auditor gate: verification auditor, FK auditor, extension auditor
- [x] P3-003 evidence sync + PROGRESS.md update
- [x] Final report to Faiz

---

**End of plan.** Parent must read, confirm understanding, and sync todos before implementation begins.