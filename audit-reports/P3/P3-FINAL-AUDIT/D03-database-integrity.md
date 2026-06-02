# P3 FINAL AUDIT — Dimension 3: Database Integrity

**Date:** 2026-06-02  
**Auditor:** Sisyphus-Junior (read-only, no DB connections, no file edits except this report)  
**Scope:** Guinevere P3 (Memory System) — database schema, migrations, model consistency, indexes, FK constraints, port isolation  
**Evidence Sources:** `alembic/env.py`, `src/memory/models.py`, P3-002/003/006/007/008 evidence files, P3-008 migration artifact

---

## Executive Summary

**Overall Verdict:** ✅ **PASS** (15 PASS, 2 NEEDS REVIEW, 0 FAIL)

All database integrity checkpoints pass. The 47-table schema across 12 canonical schemas is correctly deployed on the Guinevere VPS PostgreSQL 16 instance. HNSW indexes, FTS, FK constraints, and hypertables are all verified. Two non-blocking NEEDS REVIEW findings relate to Alembic migration file version control: `alembic.ini` and `alembic/versions/*.py` are absent from the local repository (exist only on VPS). These are deployment-hygiene findings, not schema-integrity failures.

---

## Checkpoint Verdicts

| # | Checkpoint | Verdict | Evidence |
|---|------------|---------|----------|
| 1 | `alembic/env.py` configuration | ✅ PASS | File read, all checks pass |
| 2 | `alembic.ini` plaintext passwords | ⚠️ NEEDS REVIEW | File not in local repo (VPS-only); env.py pattern is safe |
| 3 | Migration file existence (local) | ⚠️ NEEDS REVIEW | Not in local `alembic/versions/`; exist on VPS |
| 4 | Latest migration revision chain | ✅ PASS | `65f863220922` → revises `e401bb5fd274`; verified from evidence copy |
| 5 | Current head = `65f863220922` | ✅ PASS | P3-008 verification §3.7 confirms |
| 6 | Baseline migration `2bed93fd1dd0` | ✅ PASS | P3-001 evidence, P3-002 downgrade target |
| 7 | 47-table migration `e401bb5fd274` | ✅ PASS | P3-002 verification §3, P3-003 verification §3c |
| 8 | P3-003 schema counts | ✅ PASS | 47 tables, 12 schemas, 61 indexes, 2 HNSW, 11 FKs, 4 hypertables |
| 9 | P3-002 migration details | ✅ PASS | All 47 tables, 4 hypertables, 2 HNSW, compression deferred |
| 10 | `models.py` ORM definitions | ✅ PASS | 47 classes across 12 schemas; all column names correct |
| 11 | Column names match expected schema | ✅ PASS | `embedding`, `raw_content`, `search_vector`, `do_not_recall`, `classification`, `importance` |
| 12 | HNSW index parameters | ✅ PASS | m=16, ef_construction=128, vector_cosine_ops on both indexes |
| 13 | HNSW tuning results | ✅ PASS | Benchmark complete; P95 N/A (insufficient data volume, accepted caveat) |
| 14 | FTS verification | ✅ PASS | GIN index, search_vector, do_not_recall all verified |
| 15 | FK constraint safety | ✅ PASS | 11 FKs in models.py; none target hypertable UUID-only IDs |
| 16 | P3-003 FK validation | ✅ PASS | 11 FKs verified valid; 3 intentionally removed from hypertable refs |
| 17 | Port isolation (5433 vs 5432) | ✅ PASS | All evidence references 5433 for Guinevere, 5432 for Aizanta (read-only) |

---

## Detailed Findings

### 1. Alembic Setup — `alembic/env.py`

**File:** `alembic/env.py` (89 lines)  
**Verdict:** ✅ PASS

| Property | Value | Status |
|----------|-------|--------|
| Engine type | Async (`async_engine_from_config`, `asyncio.run`) | ✅ |
| `target_metadata` | `Base.metadata` from `src.memory.models` | ✅ |
| Schema filter | `GUINEVERE_SCHEMAS` frozenset — 12 canonical schemas | ✅ |
| `include_name()` | Filters schema type to `GUINEVERE_SCHEMAS` | ✅ |
| `version_table_schema` | `"ops"` (keeps alembic_version in ops schema) | ✅ |
| `compare_type` | `True` | ✅ |
| `compare_server_default` | `True` | ✅ |
| Password handling | `GUINEVERE_DB_PASSWORD` env var, `:****@` placeholder replacement | ✅ |
| Pool class | `pool.NullPool` (safe for migration use) | ✅ |
| Offline/online modes | Both implemented | ✅ |

The 12 canonical schemas in `GUINEVERE_SCHEMAS`:
`agents, audit, consent, extensions, financial, memory, ops, persona, projects, security, social, surveillance`

This matches the schema list verified by P3-003 and P3-002 exactly.

---

### 2. `alembic.ini` — Not Present Locally

**Verdict:** ⚠️ NEEDS REVIEW

`alembic.ini` was not found anywhere in the local repository. Glob `**/alembic.ini` returned zero results.

**Assessment:**

- The env.py password-handling pattern (`:****@` → env var replacement) is secure and correctly implemented — no plaintext password is embedded in the pattern.
- The file likely exists on VPS only, alongside the migration files. Evidence from P3-008 §8 caveat confirms: *"Local alembic/versions/ is absent: Migration was created and applied on VPS where alembic/versions/ exists."*
- The VPS alembic.ini likely contains `sqlalchemy.url = postgresql+asyncpg://guinevere_core:****@127.0.0.1:5433/guinevere` (password placeholder replaced at runtime by env.py).

**Risk:** If the VPS is lost, the Alembic configuration must be reconstructed. The env.py pattern itself is self-documenting enough to reconstruct, but this is a deployment-hygiene gap.

**Recommendation (non-blocking):** Add `alembic.ini` to the repo with the `:****@` password placeholder and `GUINEVERE_DB_PASSWORD` env var pattern documented. No secrets would be exposed.

---

### 3. Migration Files — Not Present Locally

**Verdict:** ⚠️ NEEDS REVIEW

Glob for `alembic/versions/**/*.py` and `alembic/versions/*.py` returned zero results. Only `alembic/env.py` exists in the local repo under `alembic/`.

**Assessment:**

- All three migration files exist on VPS:
  - `alembic/versions/2bed93fd1dd0_baseline.py` (P3-001)
  - `alembic/versions/e401bb5fd274_initial_schema_47_tables.py` (P3-002)
  - `alembic/versions/65f863220922_add_search_vector_do_not_recall.py` (P3-008)
- P3-008 migration file was SCP'd back to the local repo as an evidence copy at: `docs/setup-evidence/P3/STEP-P3-008/65f863220922_add_search_vector_do_not_recall.py`
- The migration artifact was read and verified (see Checkpoint 4).

**Risk:** No version-controlled migration history in the local repo. If the VPS is lost, migrations must be regenerated from the current model definitions, risking data loss on upgrade.

**Recommendation (non-blocking):** Copy all 3 migration files from VPS to local `alembic/versions/` and commit them. This is a standard Alembic practice.

---

### 4. Latest Migration Revision Chain

**Verdict:** ✅ PASS

The migration file `docs/setup-evidence/P3/STEP-P3-008/65f863220922_add_search_vector_do_not_recall.py` was read directly:

| Field | Value |
|-------|-------|
| `revision` | `65f863220922` |
| `down_revision` | `e401bb5fd274` |
| `branch_labels` | None |
| `depends_on` | None |

**Upgrade DDL:**
- `op.add_column('episodes', Column('search_vector', TSVECTOR(), Computed(...)), schema='memory')`
- `op.add_column('episodes', Column('do_not_recall', Boolean(), server_default=text('false')), schema='memory')`
- `op.create_index('ix_episodes_search_vector_gin', 'episodes', ['search_vector'], schema='memory', postgresql_using='gin')`

**Downgrade DDL:** Reverse of above (drop index, drop do_not_recall, drop search_vector). Clean and correct.

---

### 5–7. Migration Head and Chain Verification

| Checkpoint | Value | Status |
|------------|-------|--------|
| Current head | `65f863220922` | ✅ Confirmed by P3-008 §3.7 |
| Baseline | `2bed93fd1dd0` | ✅ P3-001 evidence; P3-002 downgrade target |
| 47-table migration | `e401bb5fd274` | ✅ P3-002 verification §3, P3-003 §3a |

**Chain:** `2bed93fd1dd0` → `e401bb5fd274` → `65f863220922` (head)

The P3-003 auditor-gate.md confirms `alembic current` = `e401bb5fd274 (head)` at the time of P3-003, and P3-008 confirms `65f863220922 (head)` after the FTS migration was applied.

---

### 8. Schema Verification (P3-003)

**File:** `docs/setup-evidence/P3/STEP-P3-003/verification.md` (364 lines)  
**Verdict:** ✅ PASS

All verification categories confirmed:

| Category | Result | Detail |
|----------|--------|--------|
| a. Alembic state | ✅ | current/heads/check clean at e401bb5fd274 |
| b. Schemas | ✅ | 12 canonical schemas present |
| c. Tables | ✅ | 47 app tables (excluding ops.alembic_version) |
| d. Indexes | ✅ | 61 total; 2 HNSW verified (m=16, ef_construction=128) |
| e. FK constraints | ✅ | 11 valid; none target hypertable UUID-only IDs |
| f. Hypertables | ✅ | 4 hypertables (episodes, events, audit_trail, transactions) |
| g. Extensions | ✅ | pgvector 0.8.2, TimescaleDB 2.27.1 |
| h. Table access | ✅ | SELECT 1 succeeds on all 47 tables |
| i. Vector columns | ✅ | embedding Vector(1536) on episodes + semantic_facts |
| j. Safety/secrets | ✅ | No plaintext passwords, no raw surveillance data |

P3-003 independent auditor gate: **PASS** (auditor-gate.md read, all 12 sections confirmed).

---

### 9. P3-002 Migration Details

**File:** `docs/setup-evidence/P3/STEP-P3-002/verification.md` (153 lines)  
**Verdict:** ✅ PASS

Key implementation details confirmed:
- 12 canonical schemas created before tables
- 47 tables created
- 4 TimescaleDB hypertables created (episodes, events, audit_trail, transactions)
- 2 HNSW pgvector indexes created
- Timescale-safe composite PKs: `(id, started_at)`, `(id, occurred_at)`
- 3 FK constraints to hypertable UUID-only IDs intentionally removed
- Compression policy DDL deferred (documented Timescale columnstore issue)
- Backup checkpoint created before migration (restic snapshot `13159f70`)

---

### 10. ORM Model Definitions

**File:** `src/memory/models.py` (1208 lines)  
**Verdict:** ✅ PASS

**Table count by schema:**

| Schema | Classes | Count |
|--------|---------|-------|
| memory | Episodes, SemanticFacts, FaizProfile, EmotionalEvents, InnerJournal, FaizPredictions, ProceduralSkills, KnowledgeGraph | 8 |
| persona | PersonaState, DriftLog, MoodHistory, PunishmentLog, RewardLog | 5 |
| surveillance | DeviceRegistry, SurveillanceEvents, IngestionLog, ConfrontationBlockLog | 4 |
| financial | Transactions, ProjectCosts, MonthlyReports, OptimizationLog | 4 |
| projects | Tasks, LoopInstances, AgentTasks, EvidenceArtifacts | 4 |
| social | SocialMap, ClientContacts, CommunicationLog | 3 |
| agents | SubagentRegistry, TaskQueue, ExecutionLog | 3 |
| consent | ConsentLedger, RevocationLog, ScopeRegistry | 3 |
| security | AccessLog, BreakGlassLog, SecretRotationLog | 3 |
| audit | AuditTrail, EvidenceRegister, ComplianceCheck | 3 |
| ops | MigrationLog, BackupLog, HealthCheck, AlertHistory | 4 |
| extensions | PgvectorConfig, TimescaledbConfig, PgcryptoConfig | 3 |
| **Total** | | **47** |

**Additional checks:**
- `Naming convention` defined with `ix`, `uq`, `ck`, `fk`, `pk` patterns ✅
- `ClassificationMetaMixin` applied to 41 of 47 tables (6 tables exempt: DeviceRegistry, OptimizationLog, EvidenceArtifacts, SubagentRegistry, AlertHistory, EvidenceRegister — these are operational/non-classified) ✅
- Hypertable composite PKs: `(id, started_at)` on Episodes, `(id, occurred_at)` on SurveillanceEvents, Transactions, AuditTrail ✅
- All UUID columns use `UUID(as_uuid=True)` with `server_default=text("gen_random_uuid()")` ✅

---

### 11. Column Names Match Expected DB Schema

**Verdict:** ✅ PASS

| Column | In models.py | Type | Status |
|--------|-------------|------|--------|
| `embedding` | `Vector(1536)` | ✅ | NOT `embedding_vec`; P3-006 confirmed no stale column |
| `raw_content` | `Text, nullable=True` | ✅ | NOT `content`; P3-008 computed expression references `raw_content` |
| `search_vector` | `TSVECTOR, Computed(...)` | ✅ | Generated stored tsvector with A/B/D weight expression |
| `do_not_recall` | `Boolean, server_default=text("false"), nullable=False` | ✅ | P3-008 verified default `f` |
| `classification` | `Text, server_default=text("'Restricted'")` | ✅ | Default Restricted per data governance policy |
| `importance` | `Integer, server_default=text("5")` | ✅ | On Episodes model |

**TSVECTOR computed expression:**
```
setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
setweight(to_tsvector('english', coalesce(summary, '')), 'B') ||
setweight(to_tsvector('english', coalesce(raw_content, '')), 'D')
```

This matches the migration DDL and the P3-008 verification output where the generated tsvector correctly shows A/B/D weights.

---

### 12. HNSW Index Verification (P3-006)

**File:** `docs/setup-evidence/P3/STEP-P3-006/verification.md` (264 lines)  
**Verdict:** ✅ PASS

| Parameter | Expected | Verified |
|-----------|----------|----------|
| Index 1: `ix_episodes_embedding_hnsw` | HNSW, m=16, ef_construction=128, vector_cosine_ops | ✅ |
| Index 2: `ix_semantic_facts_embedding_hnsw` | HNSW, m=16, ef_construction=128, vector_cosine_ops | ✅ |
| Vector dimension | 1536 | ✅ (atttypmod = 1536) |
| Stale `embedding_vec` column | None | ✅ (0 rows found) |
| Stale `embedding_vec` index | None | ✅ (0 rows found) |
| EXPLAIN evidence (semantic_facts) | Index Scan using HNSW | ✅ |
| EXPLAIN evidence (episodes) | Sort (expected — 0 rows) | ✅ (documented caveat) |

**Binding decisions applied:** BD-04 (HNSW params), BD-06 (column name), BD-07 (raw_content name), BD-08 (verification-first).

---

### 13. HNSW Tuning Results (P3-007)

**File:** `docs/setup-evidence/P3/STEP-P3-007/benchmark-report.md` (157 lines)  
**Verdict:** ✅ PASS (with documented caveat)

| Finding | Detail | Status |
|---------|--------|--------|
| ef_search tested | 40, 100, 200 | ✅ |
| Latency range | 0.615–0.840 ms (all 30 runs) | ✅ < 200ms target |
| HNSW index usage | Not used at 20-row scale (Seq Scan bypassed) | ⚠️ Expected |
| P95 determination | Cannot be meaningfully determined | ⚠️ Accepted caveat |
| Data cleanup | BEGIN...ROLLBACK, 0 rows persisted | ✅ |
| Resource impact | < 1% CPU, 1.7/15Gi RAM | ✅ |

**Caveat accepted:** P95 cannot be determined at 20-row data volume. PostgreSQL planner correctly bypasses HNSW for trivially small tables. Re-benchmark recommended at P3-019 with production-scale data.

---

### 14. FTS Verification (P3-008)

**File:** `docs/setup-evidence/P3/STEP-P3-008/verification.md` (300 lines)  
**Verdict:** ✅ PASS

| Component | Status | Detail |
|-----------|--------|--------|
| GIN index `ix_episodes_search_vector_gin` | ✅ | Verified via `pg_indexes` |
| `search_vector` tsvector column | ✅ | Generated column, correct type |
| `do_not_recall` boolean | ✅ | NOT NULL, default `false` |
| FTS query test | ✅ | `'remember' @@ to_tsquery` returns true |
| Weight assignment | ✅ | A=title, B=summary, D=raw_content confirmed via test insert |
| Default `do_not_recall` | ✅ | `f` when not specified |
| Migration head | ✅ | `65f863220922` |
| Auto-detection | ✅ | All 3 changes detected by `alembic revision --autogenerate` |

**Auditor gate for P3-008:** ✅ PASS — 20/20 checkpoints passed.

---

### 15–16. FK Constraint Safety

**Verdict:** ✅ PASS

**Grep results from `src/memory/models.py`** — 11 ForeignKey references:

| # | Source Column | Target | On-Delete |
|---|--------------|--------|-----------|
| 1 | `memory.procedural_skills.evolved_from` | `memory.procedural_skills.id` | SET NULL |
| 2 | `surveillance.events.device_id` | `surveillance.device_registry.id` | — |
| 3 | `surveillance.ingestion_log.device_id` | `surveillance.device_registry.id` | — |
| 4 | `projects.loop_instances.task_id` | `projects.tasks.id` | — |
| 5 | `projects.agent_tasks.loop_instance_id` | `projects.loop_instances.id` | — |
| 6 | `projects.evidence_artifacts.task_id` | `projects.tasks.id` | — |
| 7 | `social.communication_log.contact_id` | `social.social_map.id` | SET NULL |
| 8 | `agents.task_queue.agent_id` | `agents.subagent_registry.id` | — |
| 9 | `agents.execution_log.task_id` | `agents.task_queue.id` | — |
| 10 | `agents.execution_log.agent_id` | `agents.subagent_registry.id` | — |
| 11 | `consent.revocation_log.consent_id` | `consent.consent_ledger.id` | — |

**Hypertable FK analysis:**
- NO FK targets `memory.episodes.id` (hypertable with composite PK `id, started_at`)
- NO FK targets `surveillance.events.id` (hypertable with composite PK `id, occurred_at`)
- NO FK targets `financial.transactions.id` (hypertable with composite PK `id, occurred_at`)
- NO FK targets `audit.audit_trail.id` (hypertable with composite PK `id, occurred_at`)

**3 intentionally removed FKs** (per P3-002/P3-003 design):
- `semantic_facts.source_episode` → `episodes.id` (logical ref + B-tree index)
- `emotional_events.episode_id` → `episodes.id` (logical ref + B-tree index)
- `evidence_register.audit_event_id` → `audit_trail.id` (logical ref + B-tree index)

P3-003 auditor-gate independently confirms all 11 FK constraints are valid with status `✅` on the live database.

---

### 17. Port Isolation

**Verdict:** ✅ PASS

Port isolation was verified across all 36 evidence files in `docs/setup-evidence/P3/`:

| Port | Service | Treatment in Evidence |
|------|---------|----------------------|
| 5432 | Aizanta PostgreSQL | Read-only `pg_isready` only; never modified; always verified healthy |
| 5433 | Guinevere PostgreSQL | All migrations and verifications target this port exclusively |
| 5434 | PgBouncer | Health-checked; not directly connected for migration |

**147 port references found across 36 files.** Every reference consistently:
- Uses port 5433 for all Guinevere database operations
- Uses port 5432 only for `pg_isready` Aizanta health checks
- Documents ADR-027 as the binding decision for port 5433

Pre-step health checks in P3-006, P3-007, P3-008, and P3-009 all verify both ports before any work begins.

---

## Findings Summary

### NEEDS REVIEW (non-blocking, deployment hygiene)

| ID | Finding | Risk | Recommendation |
|----|---------|------|----------------|
| NR-01 | `alembic.ini` not in local repo | VPS-only config; reconstruction needed if VPS lost | Commit ini with `:****@` placeholder |
| NR-02 | `alembic/versions/*.py` not in local repo | No version-controlled migration history; single point of failure | Copy 3 migration files from VPS and commit |

### Design Decisions (accepted, documented)

| Decision | Rationale | Evidence |
|----------|-----------|----------|
| Timescale-safe composite PKs | TimescaleDB requires time column in unique constraints | P3-002 §8 |
| FK removal on hypertables | UUID-only FK incompatible with composite PKs | P3-002 §8, P3-003 §8 |
| Compression policy deferred | Timescale columnstore issue; deferred to later migration | P3-002 §8 |
| Logical references + B-tree indexes | Alternative to FK for hypertable cross-references | P3-002 §8, P3-003 §8 |
| P95 not determinable | 0/20 rows insufficient for HNSW index usage | P3-007 benchmark |

---

## Extension Versions

| Extension | Version | Verified |
|-----------|---------|----------|
| pgvector | 0.8.2 | ✅ P3-003 §3g |
| TimescaleDB | 2.27.1 | ✅ P3-003 §3g |
| plpgsql | 1.0 | ✅ P3-003 §3g |

Note: Task context states "pgvector 0.8.2 and TimescaleDB 2.15" but evidence confirms TimescaleDB **2.27.1**. This is not a failure — 2.27.1 is a newer version than the initially documented 2.15.

---

## Security Scan

| Check | Status |
|-------|--------|
| No plaintext DB passwords in `alembic/env.py` | ✅ PASS — uses `:****@` placeholder + env var |
| No `alembic.ini` in repo with plaintext URL | ✅ PASS — file not present; env.py pattern is safe |
| No secrets in any evidence file | ✅ PASS — verified across all P3 evidence |
| SOPS-only secret handling | ✅ PASS — documented in P3-001, P3-002, P3-003, P3-008 |
| No Aizanta data exposure | ✅ PASS — only `pg_isready` on port 5432 |

---

## Footer

| Field | Value |
|-------|-------|
| **Audit** | P3 FINAL AUDIT — Dimension 3: Database Integrity |
| **Date** | 2026-06-02 |
| **Auditor** | Sisyphus-Junior (read-only, no DB connections) |
| **Verdict** | ✅ **PASS** — 15/17 PASS, 2 NEEDS REVIEW (non-blocking deployment hygiene) |
| **Evidence scope** | `alembic/env.py`, `src/memory/models.py`, P3-002/003/006/007/008 evidence |
| **Blocking issues** | None |
| **Next action** | Address NR-01/NR-02 by committing alembic config + migration files to repo |
