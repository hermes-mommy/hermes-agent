# P19-003 Auditor Gate: Database Schema + Migrations

**Date:** 2026-06-25
**Wave/Step:** P19-003
**Migration Head:** `p19_002_project_id_not_null` (after `p19_001_project_namespaces`)

---

## Gate Checklist

### A. Structural Completeness (5 files)

| File | Exists | Notes |
|------|--------|-------|
| `alembic/versions/p19_001_project_namespaces.py` | YES | Full migration with 7 steps |
| `alembic/versions/p19_002_project_id_not_null.py` | YES | NOT NULL stub; real logic in P19-011 |
| `tests/projects/test_migration_p19_001.py` | YES | 18 test functions + parametrize |
| `docs/setup-evidence/P19/evidence/P19-003/verification.md` | YES | 12-section verification |
| `docs/setup-evidence/P19/evidence/P19-003/auditor-gate.md` | YES | This document |

### B. Migration Chain Integrity

| Check | Status |
|-------|--------|
| `p19_001` revision = `p19_001_project_namespaces` | PASS |
| `p19_001` down_revision = `p20_001_life_kernel_schema` | PASS |
| `p19_002` revision = `p19_002_project_id_not_null` | PASS |
| `p19_002` down_revision = `p19_001_project_namespaces` | PASS |
| Chain: `p20_001` -> `p19_001` -> `p19_002` (head) | PASS |
| Python syntax valid (both files) | PASS |

### C. DDL Correctness

| Check | Status |
|-------|--------|
| All CREATE TABLE / ADD COLUMN / CREATE INDEX use IF NOT EXISTS | PASS |
| Seed uses ON CONFLICT DO NOTHING | PASS |
| Backfill guarded by WHERE IS NULL (re-runnable) | PASS |
| No NOT NULL constraint applied in p19_001 | PASS |
| No DROP/RENAME of existing columns (outside constraint swap) | PASS |
| Constraint swap inside DO block (transaction-safe) | PASS |
| Hypertable-safe: no TimescaleDB API calls for project_id | PASS |
| project_scope NOT NULL DEFAULT 'project' on memory/KG | PASS |

### D. Data Integrity

| Check | Status |
|-------|--------|
| Default project UUID constistent (`00000000-0000-0000-0000-000000000001`) | PASS |
| consent.consent_ledger NULL allowed (global scope) | PASS |
| audit.audit_trail NULL allowed (global safety events) | PASS |
| surveillance.events NULL allowed | PASS |
| No "data intact" false claim | PASS |
| Honest downgrade warning documented | PASS |

### E. Hard Rejection Criteria

| Criterion | PASS/FAIL |
|-----------|-----------|
| Migration breaks P20 schema | PASS |
| Non-idempotent DDL | PASS |
| `default` project not seeded | PASS |
| FK integrity broken | PASS |
| "data intact" false claim | PASS |
| p19_001 down_revision != p20_001_life_kernel_schema | PASS |
| Python syntax invalid | PASS |
| Evidence files missing | PASS |

### F. DB Verification (Deferred)

The following checks REQUIRE a live Postgres database and are deferred to the parent step (VPS test DB `guinevere_p19_test`):

- `alembic upgrade head` (p19_001 + p19_002 applied)
- `alembic downgrade p20_001_life_kernel_schema` (rollback)
- `alembic upgrade head` (idempotent cycle)
- All 18 test functions in `test_migration_p19_001.py`
- Hypertable safety on surveillance.events

---

## Verdict

**PASS-WITH-DEFERRED-DB-VERIFICATION**

All structural, syntactic, and DDL-correctness checks pass. DB-level verification (alembic upgrade/downgrade/upgrade cycle, full test suite, hypertable safety) is deferred to the VPS test DB step.

**Sign-off:** Guinevere (P19-003 implementation agent)
