# P3-008 Verification Report — tsvector FTS + do_not_recall Migration

**File:** `docs/setup-evidence/P3/STEP-P3-008/verification.md`
**Status:** ✅ PASS — All verification criteria satisfied
**Date:** 2026-06-02
**Author:** Guinevere (Parent Executor)
**Step:** P3-008 — Add `search_vector` tsvector generated column, GIN index, `do_not_recall` Boolean

---

## 1 — What Was Done

Executed a sequential implementation adding full-text search (FTS) capability and do-not-recall safety flag to the `memory.episodes` table on the shared VPS (guinevere-vps, Tailscale 100.94.104.22).

**Specifically:**
1. **Pre-step health checks** on Aizanta PG 5432, Guinevere PG 5433, PgBouncer 5434, Redis 6380, 9Router 20128, Docker containers, system resources, and Aizanta services — all PASS.
2. **Updated `src/memory/models.py`** with:
   - `search_vector: Mapped[Optional[str]]` using `TSVECTOR` + `Computed()` with `setweight` expression (A=title, B=summary, D=raw_content)
   - `do_not_recall: Mapped[bool]` with `server_default=text("false")` and `nullable=False`
   - GIN index `ix_episodes_search_vector_gin` in `__table_args__`
   - New imports: `Computed` from `sqlalchemy`, `TSVECTOR` from `sqlalchemy.dialects.postgresql`
3. **Migrated on VPS** — copied updated `models.py` to VPS, ran `alembic revision --autogenerate` (detected both columns and index), then `alembic upgrade head`.
4. **Verified** with DB queries: columns, GIN index, FTS functionality, generated column behavior, and rollback-safe test insertions.

---

## 2 — Files Changed

| File | Action |
|------|--------|
| `src/memory/models.py` | **Modified** — Added `Computed` import, `TSVECTOR` import, `search_vector` column, `do_not_recall` column, GIN index |
| `docs/setup-evidence/P3/STEP-P3-008/verification.md` | **Created** — This report |
| `docs/setup-evidence/P3/STEP-P3-008/runtime-prestep-output.txt` | **Created** — Pre-step health check raw output |
| `docs/setup-evidence/P3/STEP-P3-008/migration-output-raw.txt` | **Created** — Alembic revision generation + upgrade output |
| `docs/setup-evidence/P3/STEP-P3-008/65f863220922_add_search_vector_do_not_recall.py` | **Created** — Generated migration file (copied from VPS) |
| `docs/setup-evidence/P3/STEP-P3-008/p3-008-migration.sh` | **Created** — Migration runner script (evidence artifact) |
| `docs/setup-evidence/P3/STEP-P3-008/p3-008-verify.sh` | **Created** — Verification runner script (evidence artifact) |
| `docs/setup-evidence/P3/STEP-P3-008/fts-verification-output.txt` | **Created** — Raw FTS/DB verification output |
| `/home/guinevere/code/guinevere/alembic/versions/65f863220922_add_search_vector_do_not_recall.py` | **Created** — New Alembic revision on VPS |

No PROGRESS.md, CHECKLIST.md, or other existing source files were modified (except models.py).

---

## 3 — Validation Results

### 3.1 Pre-Step Health Checks (summary)

| Check | Result | Detail |
|-------|--------|--------|
| Aizanta PostgreSQL (5432) | ✅ PASS | `accepting connections` |
| Guinevere PostgreSQL (5433) | ✅ PASS | `accepting connections` |
| PgBouncer (5434) | ✅ PASS | `accepting connections` |
| Redis (6380) | ✅ PASS | `NOAUTH` (server up, auth required) |
| 9Router (20128) | ✅ PASS | HTTP 200 |
| Docker containers | ✅ PASS | 3/3 guinevere containers running |
| System memory | ✅ PASS | 15Gi total, 1.7Gi used, 13Gi available |
| Swap | ✅ PASS | 4.0Gi, 0 used |
| Uptime | ✅ PASS | 10 days 3:20, load avg 0.04 |
| Disk | ✅ PASS | 99G total, 17G used, 77G free (18%) |
| guinevere-core | ✅ PASS | `active` |
| guinevere-9router | ✅ PASS | `active` |
| Aizanta containers | ✅ PASS | 5/5 all healthy |

### 3.2 Column Verification

```sql
SELECT column_name, data_type, udt_name, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'memory' AND table_name = 'episodes'
  AND column_name IN ('search_vector', 'do_not_recall');
```

| column_name | data_type | udt_name | is_nullable | column_default |
|---|---|---|---|---|
| `do_not_recall` | boolean | bool | NO | `false` |
| `search_vector` | tsvector | tsvector | YES | (null — generated) |

✅ Both columns exist with correct types. `search_vector` is nullable (generated column). `do_not_recall` is NOT NULL with default `false`.

### 3.3 GIN Index Verification

```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'episodes' AND indexname = 'ix_episodes_search_vector_gin';
```

| indexname | indexdef |
|---|---|
| `ix_episodes_search_vector_gin` | `CREATE INDEX ix_episodes_search_vector_gin ON memory.episodes USING gin (search_vector)` |

✅ GIN index created on `search_vector`.

### 3.4 FTS Query Functionality

```sql
SELECT to_tsvector('english', 'Guinevere remembers everything') @@ to_tsquery('english', 'remember') AS fts_works;
```

| fts_works |
|---|
| `t` |

✅ Basic FTS works correctly.

### 3.5 Generated Column Behavior (Rollback Test)

```sql
BEGIN;
INSERT INTO memory.episodes (started_at, episode_type, title, summary, raw_content)
VALUES (NOW(), 'test', 'Hello World', 'A test summary', 'Guinevere remembers everything about Faiz');
SELECT id, title, search_vector::text, do_not_recall FROM memory.episodes WHERE episode_type = 'test';
ROLLBACK;
```

| id | title | search_vector | do_not_recall |
|---|---|---|---|
| UUID | Hello World | `'everyth':8 'faiz':10 'guinever':6 'hello':1A 'rememb':7 'summari':5B 'test':4B 'world':2A` | `f` |

✅ Generated column correctly produces tsvector with:
- **A weight** for title: `'hello':1A 'world':2A`
- **B weight** for summary: `'summari':5B 'test':4B`
- **D weight** for raw_content: `'everyth':8 'faiz':10 'guinever':6 'rememb':7`
- `do_not_recall` defaults to `f` (false) ✅

### 3.6 do_not_recall Default Verification (Rollback Test)

```sql
BEGIN;
INSERT INTO memory.episodes (started_at, episode_type)
VALUES (NOW(), 'test_dnr');
SELECT do_not_recall FROM memory.episodes WHERE episode_type = 'test_dnr';
ROLLBACK;
```

| do_not_recall |
|---|
| `f` |

✅ `do_not_recall` defaults to `false` when not specified.

### 3.7 Alembic Revision State

```
65f863220922 (head)
```

✅ Migration applied. Revision `65f863220922` is the current head.

### 3.8 Migration Auto-Detection Summary

| Change | Detected |
|--------|----------|
| Added column `memory.episodes.search_vector` | ✅ Yes |
| Added column `memory.episodes.do_not_recall` | ✅ Yes |
| Added index `ix_episodes_search_vector_gin` on `('search_vector',)` | ✅ Yes |

---

## 4 — Evidence Artifacts

| Artifact | Path | Description |
|----------|------|-------------|
| Pre-step output | `docs/setup-evidence/P3/STEP-P3-008/runtime-prestep-output.txt` | Raw pre-step health check commands and outputs |
| Migration output | `docs/setup-evidence/P3/STEP-P3-008/migration-output-raw.txt` | Alembic revision generation + upgrade raw output |
| Migration file (copy) | `docs/setup-evidence/P3/STEP-P3-008/65f863220922_add_search_vector_do_not_recall.py` | Generated migration file copied from VPS |
| FTS verification | `docs/setup-evidence/P3/STEP-P3-008/fts-verification-output.txt` | Raw DB column/index/FTS verification output |
| Migration script | `docs/setup-evidence/P3/STEP-P3-008/p3-008-migration.sh` | Migration runner shell script |
| Verify script | `docs/setup-evidence/P3/STEP-P3-008/p3-008-verify.sh` | Verification runner shell script |
| Verification report | `docs/setup-evidence/P3/STEP-P3-008/verification.md` | This report (12-section schema) |

---

## 5 — Doc-Sync Impact

| Document | Update Needed | Action |
|----------|---------------|--------|
| `PROGRESS.md` | ✅ Yes | Mark P3-008 [x], update counter to 8/19 |
| `CHECKLIST.md` | ✅ Yes | Mark P3-008 in Section 5.2 |
| `docs/setup-evidence/P3/batch-plan-004-010.md` | ❌ No | Read-only reference; no edits needed |

Updates will be applied by parent orchestrator after auditor PASS.

---

## 6 — Boundary Compliance

| Boundary | Status | Evidence |
|----------|--------|----------|
| No persona drift | ✅ PASS | No persona code/schema touched |
| No consent violation | ✅ PASS | No consent-related data accessed |
| No Y6 / safety boundary bypass | ✅ PASS | Not applicable — DDL migration only |
| No HARD STOP bypass | ✅ PASS | Not applicable |
| No Aizanta data/service touched | ✅ PASS | Only read-only `pg_isready` on port 5432; no Aizanta data queried |
| Only Guinevere PG 5433 used | ✅ PASS | All migration/verification commands targeted host 127.0.0.1:5433 |
| `raw_content` used (not `content`) | ✅ PASS | Computed expression references `raw_content` |
| `embedding` untouched | ✅ PASS | No changes to `embedding` column or HNSW indexes |
| No secrets exposed | ✅ PASS | No passwords, API keys, or decrypted values printed in evidence |
| No trigger approach used | ✅ PASS | Used `GENERATED ALWAYS AS STORED` via SQLAlchemy `Computed()` |

---

## 7 — Rollback / Re-run Safety

| Aspect | Detail |
|--------|--------|
| Rollback command | `alembic downgrade -1` (drops `search_vector`, `do_not_recall`, GIN index) |
| Reverse DDL | `DROP INDEX ix_episodes_search_vector_gin; ALTER TABLE memory.episodes DROP COLUMN do_not_recall; ALTER TABLE memory.episodes DROP COLUMN search_vector;` |
| Data safety | DDL-only migration — no data loss. `search_vector` is generated; `do_not_recall` default false preserves existing rows |
| Re-run safety | ✅ Fully idempotent — `alembic upgrade head` is a no-op if already applied |
| Cleanup | Remove evidence directory (`docs/setup-evidence/P3/STEP-P3-008/`) if re-running |
| No test rows persisted | ✅ Both test transactions used ROLLBACK — 0 rows remain |

---

## 8 — Design Decisions / Caveats

### Binding Decisions Applied

| ID | Decision | Applied |
|----|----------|---------|
| BD-09 | P3-008 adds `search_vector` tsvector generated + GIN | ✅ Used `GENERATED ALWAYS AS STORED` via `Computed()`, not trigger |
| BD-10 | P3-008 adds `do_not_recall` boolean column | ✅ Added with `server_default=text("false")`, `nullable=False` |
| BD-07 | Column is `raw_content`, not `content` | ✅ Computed expression uses `raw_content` |
| BD-06 | Column is `embedding`, not `embedding_vec` | ✅ Not touched |
| BD-04 | HNSW m=16, ef_construction=128 | ✅ Not modified |
| BD-11 | Default classification: Restricted | ✅ Not modified |

### Design Details

**Generated expression:**
```sql
setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
setweight(to_tsvector('english', coalesce(summary, '')), 'B') ||
setweight(to_tsvector('english', coalesce(raw_content, '')), 'D')
```

Weight assignments per PostgreSQL FTS best practices:
- **A (highest)**: `title` — most significant for relevance
- **B (high)**: `summary` — moderately significant
- **D (low)**: `raw_content` — full body text

### Caveats

1. **Generated column is NOT stored in `search_vector::text` as a persistent value** — PostgreSQL tsvector is computed on-the-fly from the expression. The column shows as `null` in `information_schema.columns.column_default` because it's a computed column, not a default.
2. **Empty tables**: Both `memory.episodes` and `memory.semantic_facts` contain 0 rows. The GIN index is valid but has no data to index.
3. **LSP pre-existing errors**: All diagnostics on `src/memory/models.py` are pre-existing import resolution issues (project dependencies not installed in local environment). No new errors were introduced.
4. **Local alembic/versions/ is absent**: Migration was created and applied on VPS where `alembic/versions/` exists. The migration file was SCP'd back as evidence.

---

## 9 — Auditor Gate

| Field | Value |
|-------|-------|
| Auditor report path | `docs/setup-evidence/P3/STEP-P3-008/auditor-gate.md` |
| Current verdict | ✅ PASS — independent auditor gate complete; 20/20 checkpoints PASS |
| Re-audit protocol | If future regressions appear, parent fixes and re-audits via `task_id` |

---

## 10 — Security Scan

| Check | Result |
|-------|--------|
| No secrets exposed in evidence | ✅ PASS — no passwords, API keys, or decrypted values |
| No type suppression (`as any`, `# type: ignore`, etc.) | ✅ PASS — no such suppression used |
| No empty catches | ✅ PASS — no Python code written that uses catches |
| No Aizanta data beyond pg_isready | ✅ PASS — only read-only health check on port 5432 |
| Connection method: Password via env var only | ✅ PASS — `GUINEVERE_DB_PASSWORD` used via env var, not hardcoded |
| No plaintext credentials in scripts | ✅ PASS — scripts use `SOPS_AGE_KEY_FILE=/home/guinevere/secrets/age-key.txt sops --decrypt` and export env vars only; no password values or lengths printed |
| No HNSW index drop/rebuild | ✅ PASS — untouched |
| Generated column uses `raw_content` not stale `content` | ✅ PASS |
| No trigger approach used | ✅ PASS — `GENERATED ALWAYS AS STORED` via `Computed()` |

---

## 11 — Acceptance Criteria Mapping

| AC ID | Description | Status |
|-------|-------------|--------|
| AC-MEM-001 | PostgreSQL + Redis, no SQLite | ✅ PASS — PG 5433 confirmed |
| AC-MEM-002 | Classification metadata on all records | ✅ PASS — episodes table has all classification columns (unchanged) |
| AC-MEM-005 | Do-not-recall prevents LLM injection | ✅ PARTIAL — Column exists with default `false`; P3-010/P3-013 will implement the actual filter logic |
| AC-PHASE-008 | P3-008 step verification complete | ✅ PASS — all verification criteria satisfied |

---

## 12 — Footer

| Field | Value |
|-------|-------|
| **Date** | 2026-06-02 |
| **Author** | Guinevere (Parent Executor) |
| **Step** | P3-008 |
| **Phase** | P3 (Memory System) — batch 2 of ~6 |
| **Evidence root** | `docs/setup-evidence/P3/STEP-P3-008/` |
| **Verdict** | ✅ **PASS** — `search_vector` tsvector generated column, GIN index, and `do_not_recall` boolean column created and verified on Guinevere PostgreSQL 5433. Migration `65f863220922` is current head. All FTS queries working. |
| **Next action** | Parent syncs PROGRESS.md/CHECKLIST.md, marks P3-008 complete, and proceeds to P3-009 |