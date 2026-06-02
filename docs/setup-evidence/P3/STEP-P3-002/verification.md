# STEP-P3-002 Verification — 47 Table Migration

## 1. What Was Done

Implemented and applied the initial Guinevere PostgreSQL schema migration for P3-002 on the VPS project root `/home/guinevere/code/guinevere`.

The migration creates the canonical ERD-defined 12 schemas and 47 application tables, using SQLAlchemy 2.x model metadata and Alembic. It also converts the four time-series tables into TimescaleDB hypertables and creates the required HNSW pgvector indexes for memory recall.

## 2. Files Changed

- `src/memory/models.py`
  - Defines `Base` and 47 SQLAlchemy 2.x application models across the canonical 12 schemas.
  - Uses Timescale-safe composite primary keys for hypertables:
    - `memory.episodes(id, started_at)`
    - `surveillance.events(id, occurred_at)`
    - `financial.transactions(id, occurred_at)`
    - `audit.audit_trail(id, occurred_at)`
  - Removes DB-level foreign keys to hypertable UUID-only IDs and keeps logical UUID reference columns plus indexes.
  - Adds explicit metadata for HNSW/manual indexes so `alembic check` is clean.
- `alembic/versions/e401bb5fd274_initial_schema_47_tables.py`
  - Creates all 12 canonical schemas before table creation.
  - Creates 47 tables.
  - Creates 4 TimescaleDB hypertables.
  - Creates 2 HNSW pgvector indexes.
  - Defers compression policy DDL to a later migration after Timescale columnstore/compression enablement.
- `docs/setup-evidence/P3/STEP-P3-002/backup-checkpoint-20260602.md`
  - Backup checkpoint evidence used as hard guard before migration.
- `docs/setup-evidence/P3/STEP-P3-002/research-timescale-columnstore.md`
  - Timescale compression/columnstore research.
- `docs/setup-evidence/P3/STEP-P3-002/oracle-timescale-compression.md`
  - Consultant analysis for the Timescale compression policy failure.

## 3. Validation Results

### Alembic

- `alembic current`: `e401bb5fd274 (head)`
- `alembic heads`: `e401bb5fd274 (head)`
- `alembic check`: `No new upgrade operations detected.`

### Model import

- VPS import check: `REMOTE_IMPORT_OK`
- SQLAlchemy metadata table count: `47`

### Database counts

- Alembic version: `e401bb5fd274`
- Canonical schemas present: `agents,audit,consent,extensions,financial,memory,ops,persona,projects,security,social,surveillance`
- Base tables in canonical schemas: `48` = 47 application tables + `ops.alembic_version`

### TimescaleDB / pgvector

- Hypertables present:
  - `audit.audit_trail`
  - `financial.transactions`
  - `memory.episodes`
  - `surveillance.events`
- HNSW indexes present:
  - `memory.ix_episodes_embedding_hnsw`
  - `memory.ix_semantic_facts_embedding_hnsw`
- Retention policies present:
  - `audit.audit_trail:policy_retention`
  - `financial.transactions:policy_retention`
  - `surveillance.events:policy_retention`
- Compression policies: deferred; no compression reloptions enabled.

## 4. Evidence Artifacts

- `docs/setup-evidence/P3/STEP-P3-002/backup-checkpoint-20260602.md`
- `docs/setup-evidence/P3/STEP-P3-002/research-timescale-columnstore.md`
- `docs/setup-evidence/P3/STEP-P3-002/oracle-timescale-compression.md`
- `docs/setup-evidence/P3/STEP-P3-002/verification.md`

Verifier and auditor reports are pending and must be added before P3-002 is marked complete.

## 5. Doc-Sync Impact

Pending tracker sync after verifier and auditor gates:

- `PROGRESS.md`
- `CHECKLIST.md`
- `docs/setup-evidence/P3/batch-plan-001-003.md`

## 6. Boundary Compliance

- Aizanta PostgreSQL on port 5432 was checked read-only only and not modified.
- Guinevere PostgreSQL target was port 5433.
- Backup checkpoint was verified before migration, with primary restic snapshot `13159f70` and secondary snapshot `13c66a7c` documented in backup evidence.
- No plaintext DB credentials were written to code, logs, or evidence.
- SOPS-only secret handling was used through process environment helpers.
- No surveillance/persona/consent runtime behavior was modified.

## 7. Rollback / Re-run Safety

- Alembic migration revision: `e401bb5fd274`
- Nominal rollback command: `alembic downgrade 2bed93fd1dd0`
- Backup checkpoint exists before the migration.
- Compression policy DDL is intentionally deferred to avoid repeating the Timescale `columnstore not enabled` failure.
- `CREATE SCHEMA IF NOT EXISTS`, `create_hypertable(... if_not_exists => TRUE)`, and `CREATE INDEX IF NOT EXISTS` are used where applicable.

## 8. Design Decisions / Caveats

### ERD authority

The ERD in `docs/30-data/33-DatabaseERD_MigrationStrategy_v1.0.md` is authoritative over the older StepPrompts schema scaffold.

### Timescale-safe primary keys

TimescaleDB requires unique constraints and primary keys on hypertables to include the partitioning time column. The four hypertables therefore use composite primary keys with the time column.

### Logical references to hypertables

DB-level foreign keys to UUID-only IDs on hypertables were removed because they would conflict with TimescaleDB composite primary key requirements. Logical UUID columns remain and are indexed.

### Compression policy deferral

The migration initially encountered `columnstore not enabled on hypertable "events"` when attempting `add_compression_policy` before enabling columnstore/compression on `surveillance.events`. Oracle and Timescale research confirmed the safe sequence. For P3-002, compression policy DDL is deferred to a later focused migration so the initial schema migration remains stable and verifiable.

## 9. Auditor Gate

Pending. P3-002 is not complete until independent auditor gate PASS.

Required auditor focus:

- 47 application tables exist.
- 12 canonical schemas exist.
- 4 hypertables exist.
- HNSW indexes exist.
- Alembic current/head/check are clean.
- Aizanta port 5432 untouched.
- Compression policy deferral is documented and does not violate P3-002 DoD.
- No secrets in evidence.

## 10. Security Scan

- No plaintext passwords in this evidence.
- No SOPS decrypted values included.
- No raw surveillance data included.
- No destructive Aizanta actions performed.

## 11. Acceptance Criteria Mapping

- AC-MEM-001: PostgreSQL schema foundation created across canonical schemas.
- AC-MEM-002: Memory tables, vector columns, HNSW indexes, and time-series hypertables created.
- ADR-009: pgvector 1536-dimensional embedding indexes implemented with HNSW.
- ADR-027: Self-hosted PostgreSQL target is Guinevere PostgreSQL on port 5433.

## 12. Footer

- Step: STEP-P3-002
- Verdict: Implementation applied; verifier/auditor gates pending.
- Timestamp: 2026-06-02
