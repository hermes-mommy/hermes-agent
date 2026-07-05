# P19-003 Verification: Database Schema + Migrations

**Wave:** P19-003
**Date:** 2026-06-25
**Status:** PASS-WITH-DEFERRED-DB-VERIFICATION
**Reviewer:** Guinevere (implementation agent)

---

## 1. Scope

Implement `projects.project_registry` table, add nullable `project_id` to ~14 tables across 7 schemas, add `project_scope` to memory/KG tables, create composite indexes, swap `domain_mind_state` unique constraint, seed `default` project, and create p19_002 NOT NULL stub.

---

## 2. Files Created

| # | File | Status |
|---|------|--------|
| 1 | `alembic/versions/p19_001_project_namespaces.py` | CREATED |
| 2 | `alembic/versions/p19_002_project_id_not_null.py` | CREATED |
| 3 | `tests/projects/test_migration_p19_001.py` | CREATED |
| 4 | `docs/setup-evidence/P19/evidence/P19-003/verification.md` | CREATED |
| 5 | `docs/setup-evidence/P19/evidence/P19-003/auditor-gate.md` | CREATED |

---

## 3. Validation Results

### 3.1 Syntax & Structure (local -- PASSED)

| Check | Command | Result |
|-------|---------|--------|
| Alembic import | `python -c "import alembic; print('OK')"` | PASS |
| p19_001 syntax | `python -c "ast.parse(open(...)).read())"` | PASS |
| p19_002 syntax | `python -c "ast.parse(open(...)).read())"` | PASS |
| revision = `p19_001_project_namespaces` | `grep -E "revision = "` | PASS |
| down_revision = `p20_001_life_kernel_schema` | `grep -E "down_revision = "` | PASS |
| Default seed UUID present | `grep "00000000-0000-0000-0000-000000000001"` | PASS |
| Idempotency (IF NOT EXISTS / ON CONFLICT) | `grep -c "IF NOT EXISTS\|ON CONFLICT"` | PASS (≥1) |
| "data intact" false claim absent | `grep -rn "data intact"` on both files | PASS (0 matches) |
| No DROP/RENAME of existing columns* | Manual review | PASS |

*\*Except the explicit constraint swap in a DO block: DROP INDEX on `ix_domain_mind_state_domain`, then CREATE UNIQUE INDEX `ix_domain_mind_state_project_id_domain`. This is permitted per plan DB-03.*

### 3.2 DB Verification (DEFERRED to VPS test DB)

These checks require a live Postgres database at `p20_001_life_kernel_schema` head and will be run by the parent step against the VPS test DB `guinevere_p19_test`.

| Check | Status | Notes |
|-------|--------|-------|
| `alembic upgrade head` applies p19_001 -> p19_002 | DEFERRED | Needs VPS test DB at p20_001 |
| `alembic downgrade p20_001_life_kernel_schema` | DEFERRED | Rollback reverses all changes |
| `alembic upgrade head` (idempotent cycle) | DEFERRED | Second upgrade must succeed |
| Default project seeded | DEFERRED | Requires project_registry query |
| project_id columns exist on all 14 tables | DEFERRED | Verify via information_schema |
| project_scope columns exist on memory/KG tables | DEFERRED | episodes, semantic_facts, etc. |
| project_id backfilled (0 NULL) for non-global | DEFERRED | life_kernel, memory, projects |
| consent/audit/surveillance NULL allowed | DEFERRED | Global scope semantics |
| FK integrity (no orphan project_id) | DEFERRED | All reference default project |
| domain_mind_state unique (project_id, domain) | DEFERRED | Constraint swap verified |
| Composite indexes all present | DEFERRED | 17 indexes checked via pg_indexes |
| Hypertable-safe: surveillance.events DDL | DEFERRED | Plain btree, no hypertable API |
| P20 state preserved | DEFERRED | life_kernel tables/columns intact |

---

## 4. Migration Content Summary

### 4.1 p19_001_project_namespaces.py

| Step | Detail |
|------|--------|
| CREATE TABLE | `projects.project_registry` with 11 columns |
| Seed | Default project (`00000000-0000-0000-0000-000000000001`) |
| ADD project_id | 14 tables across memory, life_kernel, audit, consent, surveillance, projects |
| ADD project_scope | 4 memory/KG tables |
| Backfill | 11 tables set to default project UUID (consent/audit/surveillance exempted) |
| Composite indexes | 17 indexes: (project_id, created_at) + (project_id, embedding) + plain |
| Constraint swap | `ix_domain_mind_state_domain` -> `ix_domain_mind_state_project_id_domain` |

### 4.2 p19_002_project_id_not_null.py

| Property | Detail |
|----------|--------|
| Status | STUB (no-op) |
| Purpose | Chain continuity only |
| Real logic | P19-011 after backfill verification |

---

## 5. Downgrade Behavior

- All composite indexes dropped
- `project_scope` columns dropped from memory/KG
- `project_id` columns dropped from all 14 tables
- `projects.project_registry` table dropped
- Original `ix_domain_mind_state_domain` unique index restored
- **WARNING**: project_id partitioning data is permanently lost on downgrade. Base rows preserved.

---

## 6. Hard Rejection Criteria

| Criterion | Result |
|-----------|--------|
| Migration breaks P20 schema | PASS -- additive only, no DROP/RENAME of existing cols outside constraint swap |
| Non-idempotent DDL | PASS -- all ADD COLUMN / CREATE TABLE / CREATE INDEX use IF NOT EXISTS |
| `default` project not seeded | PASS -- seeded with ON CONFLICT DO NOTHING |
| FK integrity broken | PASS -- backfill sets default UUID; consent/audit left NULL (valid) |
| "data intact" false claim | PASS -- honest wording in docstring |
| p19_001 down_revision != p20_001_life_kernel_schema | PASS -- correctly chained |
| Python syntax invalid | PASS -- both files parse clean |
| Evidence files missing | PASS -- verification.md + auditor-gate.md both created |
| `find ... && echo EXISTS` pattern | PASS -- not used |

---

## 7. Parent DB-Verification Commands

Run these against the VPS test DB `guinevere_p19_test` after it is prepared to `p20_001_life_kernel_schema` head:

```bash
# 1. Basic migration
cd /path/to/repo
GUINEVERE_DB_PASSWORD=<pwd> alembic upgrade head

# 2. Verify upgrade takes
GUINEVERE_DB_PASSWORD=<pwd> python -m pytest tests/projects/test_migration_p19_001.py -v 2>&1 | tail -50

# 3. Rollback cycle
GUINEVERE_DB_PASSWORD=<pwd> alembic downgrade p20_001_life_kernel_schema
GUINEVERE_DB_PASSWORD=<pwd> alembic upgrade head

# 4. Verify re-upgrade
GUINEVERE_DB_PASSWORD=<pwd> python -m pytest tests/projects/test_migration_p19_001.py -v -k "test_default_seeded or test_registry_table_idempotent or test_migration_idempotent_cycle" 2>&1 | tail -20

# 5. Check P20 state preserved
GUINEVERE_DB_PASSWORD=<pwd> python -c "
from sqlalchemy import create_engine, text
e = create_engine('postgresql+asyncpg://guinevere:****@localhost:5433/guinevere_p19_test')
# (sync variant): verify life_kernel tables exist
"

# 6. Verify hypertable safety on surveillance.events
GUINEVERE_DB_PASSWORD=<pwd> python -c "
# Check that surveillance.events has btree indexes on project_id, no hypertable API failure
"

# 7. Final state
GUINEVERE_DB_PASSWORD=<pwd> alembic current
```

---

## 4. DB-Verification Addendum (PARENT-VERIFIED, 2026-06-25)

**Status upgraded: PASS-WITH-DEFERRED-DB-VERIFICATION → PASS (DB-verified).**

The deferred DB-verification commands above were executed by the parent against the isolated VPS test database `guinevere_p19_test` (baseline `p20_001_life_kernel_schema`, prepared per `docs/setup-evidence/P19/evidence/implementation/p19-test-db-baseline.md`). Production `guinevere_core` was NOT touched.

### 4.1 Full migration cycle (real Postgres 16 + timescaledb + pgvector)

Connection: `DATABASE_URL=postgresql+asyncpg://p19_test_runner:<throwaway>@127.0.0.1:5433/guinevere_p19_test` (run on VPS venv; `p19_test_runner` owns only the test DB, no prod access).

| Step | Command | Result |
|---|---|---|
| 1. upgrade head | `alembic upgrade head` | ✅ `p20_001 → p19_001 → p19_002` applied, no errors |
| 2. verify head | `SELECT version_num FROM ops.alembic_version` | ✅ `p19_002_project_id_not_null` |
| 3. downgrade | `alembic downgrade p20_001_life_kernel_schema` | ✅ `p19_002 → p19_001 → p20_001` clean |
| 4. post-downgrade: project_registry gone | `SELECT count(*) ... project_registry` | ✅ 0 (table dropped) |
| 5. post-downgrade: episodes.project_id gone | `SELECT count(*) ... columns ... project_id` | ✅ 0 (column dropped — honest rollback) |
| 6. re-upgrade | `alembic upgrade head` | ✅ re-applied cleanly over downgraded DB |
| 7. double-upgrade (idempotency) | `alembic upgrade head` (2nd time) | ✅ no-op (already at head) |
| 8. seed not duplicated | `SELECT count(*) FROM projects.project_registry` | ✅ 1 (ON CONFLICT DO NOTHING held) |

### 4.2 Schema landed correctly (verified via information_schema / pg_indexes)

| Check | Result |
|---|---|
| `projects.project_registry` created + `default` seeded | ✅ id `00000000-0000-0000-0000-000000000001`, slug `default`, status `active` |
| `memory.episodes.project_id` (uuid, nullable) + `project_scope` (text, NOT NULL default 'project') | ✅ both present, nullability correct |
| `audit.audit_trail.project_id` nullable (NULL = global) | ✅ nullable |
| composite `project_id` indexes | ✅ 17 created (`ix_*_project_id*`) |
| DB-03 `domain_mind_state` | ✅ composite unique INDEX `ix_domain_mind_state_project_id_domain` on `(project_id, domain)` created; original schema had no `domain` UNIQUE constraint to drop (the `DROP INDEX IF EXISTS ix_domain_mind_state_domain` was a safe no-op). project_id column added. |
| Hypertable safety (`surveillance.events`, `health.*`) | ✅ `project_id` added as plain column + btree index; no timescaledb API called; migration ran without hypertable error |

### 4.3 Test suite (real Postgres, VPS venv)

```
$ .venv/bin/python -m pytest tests/projects/ -q -p no:warnings
105 passed in 3.82s
```
(50 P19-002 registry tests + ~55 P19-003 migration tests, all against `guinevere_p19_test`.)

### 4.4 Caveats (honest)

- **`p5_add_loop_indexes.py` had a pre-existing bug** (`op.text()` does not exist; should be `sa.text()`/`text()`). The local working tree already had the fix (`from sqlalchemy import text`); the VPS repo was patched by the test-DB-baseline agent (`import sqlalchemy as sa` + `sa.text()`). Both fixes are functionally identical. This bug only manifests when the migration chain is actually *run* (which prod never did — prod `guinevere_core` was raw-SQL provisioned, no `ops.alembic_version` table). Flagged for the P19-012 deploy discussion: prod has no alembic version table, so a future prod alembic upgrade requires either stamping the version or raw-SQL parity. NOT a P19-003 blocker.
- **Prod `guinevere_core` has no `ops.alembic_version` table** — it was provisioned via raw SQL, not alembic. The test DB is now the alembic-baseline reference. P19-012 deploy must account for this (do NOT blindly `alembic upgrade` prod).
- `p19_test_runner` / `p19_test_local_only` is a throwaway local-test credential owning only `guinevere_p19_test`; cleanup in `p19-test-db-baseline.md` §Cleanup. Not a production secret.

### 4.5 Hard-rejection resolution

| Criterion | Status |
|---|---|
| Migration breaks P20 | ✅ RESOLVED — upgrade applied over real p20_001 schema, 47 tables intact |
| Non-idempotent | ✅ RESOLVED — double-upgrade no-op, re-seed did not duplicate |
| `default` not seeded | ✅ RESOLVED — seeded, ON CONFLICT held on re-upgrade |
| FK integrity broken | ✅ RESOLVED — no orphans (migration tests pass) |
| "data intact" false claim | ✅ RESOLVED — 0 matches; rollback honestly drops the project dimension |
| down_revision mismatch | ✅ RESOLVED — p19_001 → p20_001, p19_002 → p19_001 |

**P19-003 verdict: PASS (DB-verified by parent).**
