# P3 Runtime Evidence Readiness — P3-004 through P3-010

**Date:** 2026-06-02
**Round:** Research wave — read-only file inspection
**Verdict:** READY with caveats
**Target Steps:** P3-004, P3-005, P3-006, P3-007, P3-008, P3-009, P3-010

---

## 1. P3-001..P3-003 Completion Status

| Step | Description | Status | Evidence Quality |
|------|-------------|--------|-----------------|
| P3-001 | Alembic setup + env.py | ✅ PASS (PROGRESS.md) | ⚠️ **Degraded** — evidence dir contains only auditor-gate.md (FAIL report). No verification.md, no verifier reports. |
| P3-002 | 47 tables migration | ✅ PASS | **Excellent** — verification.md + 3 verifier reports + auditor-gate.md + backup checkpoint evidence |
| P3-003 | Migration verification | ✅ PASS | **Excellent** — verification.md (12 sections, 10 categories PASS) + auditor-gate.md (12 DC PASS) |

### P3-001 Caveats

The P3-001 evidence directory at docs/setup-evidence/P3/STEP-P3-001/ contains **only** uditor-gate.md (which was a FAIL report). The P3-001 step was later resolved by the parent while working on P3-002, but no updated evidence was written. The verified state is:

- lembic/env.py — present (89 lines, correct async + multi-schema + 12-schema filter)
- lembic.ini — **NOT found locally** (exists only on VPS)
- lembic/versions/ — **EMPTY locally** (migration files exist only on VPS)
- src/memory/models.py — present (created during P3-002, 1189 lines, 47 models)
- PROGRESS.md marks P3-001 as complete; this is trusted based on P3-002/P3-003 evidence

**Impact for P3-004..P3-010:** P3-001 is functionally complete (Alembic runs on VPS with correct head at e401bb5fd274). Local lembic.ini and migration files must be fetched from VPS if Alembic operations need to run locally.

---

## 2. Backup Checkpoint Evidence — 13159f70

### Source File

docs/setup-evidence/P3/STEP-P3-002/backup-checkpoint-20260602.md

### Key Facts

| Property | Value |
|----------|-------|
| Primary restic snapshot ID | **13159f70** |
| Snapshot timestamp | 2026-06-02 06:27:33 UTC+07 |
| Hostname | aiz-prod-01 |
| Tags | guinevere,daily,20260602_062732 |
| Backup size | 31.718 KiB (config + pg_dumpall 4318 bytes) |
| Secondary snapshot ID | 13c66a7c (Cloudflare R2) |
| last-backup-success marker | **MISSING** — VPS Docker Edition v2 script does not write it |
| Local script marker | scripts/guinevere-backup.sh DOES write marker (line 581) |
| Faiz unblock condition | **Satisfied** — snapshot ID visible → backup guard approved |

### Checkpoint Script Requirements

The VPS script at /home/guinevere/code/guinevere/scripts/guinevere-backup.sh (Docker Edition v2) uses:
- PG_HOST: 127.0.0.1, PG_PORT: 5433 (Guinevere, not Aizanta 5432)
- docker exec guinevere-postgres pg_dumpall -U guinevere
- Dual restic targets: PRIMARY (idcloudhost S3) + SECONDARY (Cloudflare R2)
- Secrets via sops exec-env pattern
- Success marker at /var/log/guinevere/last-backup-success (Phase 7, line 567-582)

**Local script** C:\Users\faizz\guinevere\scripts\guinevere-backup.sh (615 lines) is a different version — the actual VPS script under Docker Edition v2 has a variant. The local version DOES write the marker (line 581: date -u '+%Y-%m-%dT%H:%M:%S%z' > "").

### P3-009 Guard

P3-009 requires: "writes only if valid backup checkpoint snapshot 13159f70 exists."  
**Status:** ✅ Snapshot 13159f70 confirmed via estic snapshots listing on VPS. Evidence is at docs/setup-evidence/P3/STEP-P3-002/backup-checkpoint-20260602.md.

---

## 3. Migration Revision IDs

| Revision | Type | Status |
|----------|------|--------|
| 2bed93fd1dd0 | Baseline (down revision) | Parent of e401bb5fd274 |
| e401bb5fd274 | Head — initial_schema_47_tables | **Applied** on VPS, verified by 3 independent sources |

### Evidence Chain

`
alembic heads               → e401bb5fd274 (head)
ops.alembic_version table   → e401bb5fd274
alembic current             → e401bb5fd274 (head) [parent-verified via /tmp/run_alembic_safe.py]
alembic check               → No new upgrade operations detected.
`

### Local vs VPS State

| Artifact | Local (C:\Users\faizz\guinevere) | VPS (/home/guinevere/code/guinevere) |
|----------|-----|-----|
| lembic.ini | **MISSING** | Present |
| lembic/env.py | Present (89 lines) | Present |
| lembic/versions/ | **EMPTY** | Contains e401bb5fd274_initial_schema_47_tables.py (1129 lines) |
| lembic/script.py.mako | **MISSING** | Present |
| src/memory/models.py | Present (1189 lines, 47 models) | Present |
| 	mp/migration.py | Present — local copy of e401bb5fd274 (1129 lines) | N/A |

**Conclusion:** Alembic version files exist **only on the VPS**. The local 	mp/migration.py is a historical copy/artifact, not the canonical location. For any future lembic revision --autogenerate operations, the VPS is the source of truth.

---

## 4. Temp Migration Files vs Actual Alembic Files

| Path | Type | Purpose |
|------|------|---------|
| 	mp/migration.py | **Local copy artifact** | Full migration revision e401bb5fd274 with all 47 tables + hypertables + HNSW + retention policies (1129 lines). Was used as a reference copy during P3-002 implementation. |
| 	mp/patch-migration.py | **Patching script** | Python script that regex-injected hypertable creation, HNSW indexes, and downgrade cleanup into an earlier autogenerated migration (71c219fcaee7). This was a transitional step — the final migration was regenerated cleanly. |
| lembic/versions/ | **EMPTY (local)** | No version files exist in the canonical Alambic versions directory on local. |
| VPS: lembic/versions/e401bb5fd274_initial_schema_47_tables.py | **Canonical migration** | The actual migration file on VPS that was generated via lembic revision --autogenerate and then manually adjusted for hypertables/retention. **This is the authoritative file.** |

### Key Finding

The local repo has **no actual Alembic migration files** — only temp artifacts in 	mp/. If a P3-004..P3-010 task needs to generate a follow-up migration (e.g., compression policy enablement, FTS tsvector column), it MUST:

1. Create lembic.ini locally (or fetch from VPS), OR
2. Run Alembic commands directly on VPS via SSH

---

## 5. Environment & Config Templates

| Resource | Path | Status |
|----------|------|--------|
| DB secrets | secrets/db-passwords.yaml | ✅ SOPS-encrypted (verified by P3-001 auditor) |
| Backup secrets | secrets/backup/cloudflare-r2-plaintext.env | ✅ Present |
| Backup secrets | secrets/backup/idcloudhost-s3-plaintext.env | ✅ Present |
| Backup secrets | secrets/backup/restic-password-plaintext.env | ✅ Present |
| .env file | (project root) | **NOT FOUND** — no local .env or .env.template |
| lembic.ini | (project root) | **NOT FOUND** locally |

### Password Handling

- GUINEVERE_DB_PASSWORD env var is required for Alembic operations
- Password obtained via: sops -d /home/guinevere/secrets/db-passwords.yaml (VPS)
- Never written to logs, evidence, or code
- lembic/env.py (lines 26-29) injects it from env var: db_url.replace(":****@", f":{password}@")

---

## 6. P3-004 through P3-010 — StepPrompts Requirements

### P3-004: SentenceTransformers Model
- **Requires:** pip install sentence-transformers openai in .venv
- **Primary strategy:** 	ext-embedding-3-small (1536 dim) via 9Router → OpenRouter at http://localhost:20128/v1
- **Fallback:** ll-MiniLM-L6-v2 (384 dim) — local, free
- **ADR:** ADR-009 (1536-dim embeddings)

### P3-005: Embedding Pipeline
- **Requires:** Create src/memory/embeddings.py
- **Requires:** 9Router running on port 20128
- **Requires:** OpenAI SDK configured with ase_url="http://localhost:20128/v1"
- **Functions:** embed_text(), embed_batch() → 1536-dim vectors

### P3-006: pgvector HNSW Index
- **Status:** ✅ **ALREADY DONE** in P3-002
- Two HNSW indexes already created on VPS:
  - memory.ix_episodes_embedding_hnsw — m=16, ef_construction=128, vector_cosine_ops
  - memory.ix_semantic_facts_embedding_hnsw — same params
- **StepPrompts P3-006** uses column name embedding_vec but P3-002 models use embedding.
  ⚠️ **Schema conflict** — StepPrompts references outdated column name.

### P3-007: HNSW Parameter Tuning
- **Requires:** Production-like data volumes for meaningful benchmarks
- **Requires:** SET hnsw.ef_search experimentation
- **Note:** P3-007 should reconcile with existing P3-002 HNSW indexes

### P3-008: tsvector FTS Setup
- **Requires:** Add search_vector tsvector column to memory.episodes
- **Requires:** GIN index on search_vector
- **Requires:** Trigger function memory.update_search_vector() for auto-update
- **Requires:** New Alembic migration (adds column + index + trigger)

### P3-009: Memory Write Pipeline
- **Requires:** Create src/memory/write_pipeline.py
- **Requires:** Integration with src/memory/embeddings.py from P3-005
- **Requires:** Async DB access to memory.episodes
- **Guard:** "writes only if valid backup checkpoint snapshot 13159f70 exists"
- **Dependencies:** P3-005 (embeddings) must be complete

### P3-010: Memory Read Pipeline
- **Requires:** Create src/memory/read_pipeline.py
- **Requires:** <=> vector distance operator + do_not_recall filter
- **Dependencies:** P3-005 (embeddings) + P3-006 (HNSW index) must be complete

---

## 7. Port Configuration (Canonical)

| Port | Service | Container | Status (VPS) |
|------|---------|-----------|--------------|
| 5432 | Aizanta PostgreSQL | izanta-postgres | ✅ Healthy, Up 9 days — **MUST NOT TOUCH** |
| 5433 | Guinevere PostgreSQL | guinevere-postgres → pgbouncer | ✅ Healthy, pg_isready -p 5433 accepting |
| 5434 | Guinevere PgBouncer | guinevere-pgbouncer (percona 1.25.2) | ✅ Healthy, pg_isready -p 5434 accepting |
| 6380 | Guinevere Redis | guinevere-redis (7.4-alpine) | ✅ Healthy, NOAUTH response (auth required) |
| 20128 | 9Router (LLM/embedding proxy) | (9Router endpoint) | Required for P3-004/P3-005 embedding API |

---

## 8. Aizanta Health Verification Requirement

Per AGENTS.md context: "User requires Aizanta health verified before every implementation step."

### Verification Commands (Read-Only)

`ash
# Network-level check (no auth required)
pg_isready -h 127.0.0.1 -p 5432

# Container check (via SSH)
docker inspect aizanta-postgres --format '{{.State.Status}} (Up {{.State.StartedAt}})' 

# Alternative container-internal check
docker exec aizanta-postgres psql -U aizanta -c "SELECT 1"
`

### Currently Verified

- Container izanta-postgres: Up 9 days (as of 2026-06-02 P3-003 audit)
- Port 5432: accepting connections
- **No modification** throughout P3-001..P3-003

---

## 9. Execution Prerequisites Summary

### For Local Execution

| Requirement | Status | Action |
|------------|--------|--------|
| lembic.ini | MISSING | Fetch from VPS or regenerate with lembic init |
| lembic/versions/ | EMPTY | No local migrations; run Alembic on VPS |
| src/memory/models.py | ✅ Present | 47 models, 12 schemas |
| Python deps | Partial | uv sync needed; also pip install sentence-transformers openai |
| DB access | Remote only | GUINEVERE_DB_PASSWORD env var from SOPS |
| 9Router | VPS only | Must tunnel or SSH to access 127.0.0.1:20128 |

### For VPS Execution (Recommended for P3-004..P3-010)

| Requirement | Status | Action |
|------------|--------|--------|
| Alembic | ✅ Configured | lembic current = e401bb5fd274 (head) |
| Migration files | ✅ Present | lembic/versions/e401bb5fd274_initial_schema_47_tables.py |
| Python deps | ✅ Installed | Verified .venv/bin/alembic works |
| DB access | ✅ Direct | DB password via SOPS on VPS |
| 9Router | ✅ Running | Embedding API at http://localhost:20128/v1 |

---

## 10. Gap Analysis — P3-004..P3-010 Readiness

| Step | Deps Met? | Schema Conflict? | Blocking Issue |
|------|-----------|-----------------|----------------|
| P3-004 | ✅ | No | Needs sentence-transformers and openai installed in .venv |
| P3-005 | Requires P3-004 | No | Needs 9Router running; creates src/memory/embeddings.py |
| P3-006 | ✅ Already done in P3-002 | ⚠️ Column name mismatch (StepPrompts uses embedding_vec; P3-002 uses embedding) | **May not need execution** — HNSW indexes already exist. StepPrompts may be stale. |
| P3-007 | Requires P3-006 | No | Needs data volume for benchmarks |
| P3-008 | ✅ | No | Requires new Alembic migration for tsvector column |
| P3-009 | Requires P3-005 + backup checkpoint | No | **Backup guard satisfied** — snapshot 13159f70 confirmed |
| P3-010 | Requires P3-005 + P3-006 | No | HNSW indexes already available |

---

## 11. Key Files Referenced

| File | Role |
|------|------|
| docs/setup-evidence/P3/batch-plan-001-003.md | P3 batch plan (270 lines) — schema authority, binding decisions |
| docs/setup-evidence/P3/STEP-P3-002/backup-checkpoint-20260602.md | Backup checkpoint evidence (137 lines) — snapshot 13159f70 |
| docs/setup-evidence/P3/STEP-P3-002/verification.md | P3-002 migration verification (153 lines) |
| docs/setup-evidence/P3/STEP-P3-002/verifier-db-migration.md | DB migration verifier (278 lines) — 12/12 PASS |
| docs/setup-evidence/P3/STEP-P3-002/verifier-lsp-code.md | Code quality verifier (116 lines) — 15/15 PASS |
| docs/setup-evidence/P3/STEP-P3-002/verifier-safety.md | Safety boundary verifier (197 lines) — 12/12 PASS |
| docs/setup-evidence/P3/STEP-P3-002/auditor-gate.md | P3-002 auditor gate (295 lines) — 13/13 DC PASS |
| docs/setup-evidence/P3/STEP-P3-003/verification.md | P3-003 verification (364 lines) — 10 categories PASS |
| docs/setup-evidence/P3/STEP-P3-003/auditor-gate.md | P3-003 auditor gate (323 lines) — 12 DC PASS |
| evidence/P3-002-timescaledb-consultation.md | TimescaleDB consultation (237 lines) — composite PK + FK removal rationale |
| src/memory/models.py | 47 SQLAlchemy models across 12 schemas (1189 lines) |
| lembic/env.py | Alembic async + multi-schema config (89 lines) |
| 	mp/migration.py | Local copy of migration e401bb5fd274 (1129 lines) |
| 	mp/patch-migration.py | Historical patching script (121 lines) |
| scripts/guinevere-backup.sh | Backup script — writes last-backup-success marker (615 lines) |
| scripts/preflight-check.sh | VPS health check script (467 lines) |
| stepprompts/StepPrompts.md (lines 6105-6274) | P3-003..P3-014 step descriptions |
| PROGRESS.md | Tracker — P3 at 3/19 complete, P3-001..003 PASS |

---

## 12. Recommendations

1. **P3-006 is effectively done.** The StepPrompts P3-006 uses embedding_vec column name; P3-002 already created HNSW indexes on embedding column. Verify with P3-002 evidence and skip or re-scope P3-006.

2. **P3-007 can run independently** after P3-006 is confirmed. Requires live DB data for benchmarking.

3. **P3-008 needs a follow-up Alembic migration** — adding search_vector column + GIN index + trigger to memory.episodes. Run on VPS where Alembic is configured.

4. **P3-009 backup guard is satisfied** — snapshot 13159f70 confirmed. Each P3-009 execution should reference docs/setup-evidence/P3/STEP-P3-002/backup-checkpoint-20260602.md as guard evidence.

5. **P3-004 and P3-005 form an embedding sub-chain.** P3-004 (install deps) → P3-005 (create pipeline). P3-009 and P3-010 depend on P3-005. Recommend sequential execution: P3-004 → P3-005 → then fork P3-009 || P3-010.

6. **Aizanta health must be verified before every step.** Use pg_isready -p 5432 as a quick pre-step check.

7. **Local Alembic gap.** If any P3-004..P3-010 step needs lembic revision --autogenerate, either: (a) run on VPS via SSH, or (b) fetch lembic.ini + lembic/versions/ + lembic/script.py.mako from VPS to local.

---

## 13. Footer

- **Verdict:** P3-004..P3-010 are READY to proceed with the caveats above.
- **Evidence Root:** docs/setup-evidence/P3/
- **Research Round:** Read-only file inspection — 28 evidence/reference files inspected, 10 directories scanned, no destructive operations.
- **Boundary Compliance:** ✅ No secrets exposed. ✅ No DB commands run. ✅ No file modifications. ✅ Aizanta untouched.
