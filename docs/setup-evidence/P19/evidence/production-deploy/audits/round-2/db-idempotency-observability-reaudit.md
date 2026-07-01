# P19-012 Re-Audit: DB Idempotency Fix + Live audit_trail DDL Inspection

**Auditor:** Independent (Claude sub-agent, round 2)
**Date:** 2026-06-26
**Scope:** RE-DB-02 (idempotency fix verification) + RE-OBS-03 (live audit_trail DDL inspection that round 1 skipped)
**Method:** Source code review of `scripts/p19_001_deploy.py` + live VPS re-run + live Postgres DDL queries

---

## 1. Background

Round 1 produced two findings relevant to this re-audit:

- **FINDING-02 / DB-02 (LOW):** `scripts/p19_001_deploy.py` had a non-idempotent INSERT for `projects.project_registry` -- no `ON CONFLICT DO NOTHING`. Re-running would fail with a unique violation on the `slug` column.
- **OBS-03 (NEEDS-REVIEW):** The observability auditor did not SSH to the VPS to run `\d audit.audit_trail`. The DDL (project_id column, chain_version column, indexes) was verified only via deploy script source code and smoke test corroboration.

The remediation summary (`SUMMARY-remediation.md`) states:
- DB-02 was fixed by adding an idempotent `CREATE TABLE IF NOT EXISTS` + `INSERT ... ON CONFLICT (slug) DO NOTHING` block to `p19_001_deploy.py`.
- OBS-03 was deferred to round 2 for live DDL confirmation.

This re-audit verifies both fixes with live evidence.

---

## 2. Files Reviewed

| File | Purpose |
|---|---|
| `scripts/p19_001_deploy.py` | Hardened deploy script (source of RE-DB-02a check) |
| `docs/setup-evidence/P19/evidence/production-deploy/audits/round-1/db-migration-safety.md` | Round 1 FINDING-02 |
| `docs/setup-evidence/P19/evidence/production-deploy/audits/round-1/observability-evidence.md` | Round 1 OBS-03 |
| `docs/setup-evidence/P19/evidence/production-deploy/audits/round-1/SUMMARY-remediation.md` | Fix tracking |
| Live VPS Postgres (`guinevere` DB, port 5433) | DDL + data integrity queries |

---

## 3. RE-DB-02a: Idempotent CREATE+SEED Block Present

**PASS**

Source code review of `scripts/p19_001_deploy.py` confirms the idempotent block at lines 19-44:

```python
# 0. CREATE project_registry + seed default (idempotent) - makes script self-contained
try:
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS projects.project_registry (...)
    ''')
    await conn.execute(
        "INSERT INTO projects.project_registry (id, slug, name, status) "
        "VALUES ($1, 'default', 'Default Project', 'active') "
        "ON CONFLICT (slug) DO NOTHING", DEFAULT)
```

The module docstring (line 3) also declares: `Idempotent: all statements use IF NOT EXISTS / ON CONFLICT DO NOTHING.`

Both the `CREATE TABLE IF NOT EXISTS` and `INSERT ... ON CONFLICT (slug) DO NOTHING` are present. The block is wrapped in try/except with OK/FAIL counters. This is the exact fix described in the remediation summary.

---

## 4. RE-DB-02b: Re-Run is a No-Op (0 FAIL)

**PASS**

Re-execution of the deploy script on the live VPS:

```
=== P19-001 PHASE 2 DONE: 32 OK, 0 FAIL ===
```

Breakdown:
- 1 OK: CREATE+SEED project_registry (idempotent) -- no-op, table+row already exist
- 13 OK: ADD project_id -- `IF NOT EXISTS`, columns already present
- 4 OK: ADD project_scope -- `IF NOT EXISTS`, columns already present
- 14 OK: BACKFILL -- all `UPDATE ... WHERE project_id IS NULL` set 0 rows (already backfilled)

**Total: 32 OK, 0 FAIL.** Every statement was a safe no-op.

---

## 5. RE-DB-02c: No Data Corruption After Re-Run

**PASS**

Live query of `projects.project_registry` after the re-run:

| id | slug | name | status |
|---|---|---|---|
| `00000000-0000-0000-0000-000000000001` | `default` | `Default Project` | `active` |

**Total rows: 1.** No duplicates. The default project UUID matches ADR-052 canonical value. The `ON CONFLICT (slug) DO NOTHING` correctly prevented any duplicate insertion.

---

## 6. RE-OBS-03a: audit.audit_trail.project_id Column (Live DDL)

**PASS**

Live query of `information_schema.columns` for `audit.audit_trail`:

| column_name | data_type | is_nullable | column_default |
|---|---|---|---|
| **project_id** | **uuid** | **YES** | `None` |

The `project_id` column exists as `UUID`, nullable (`is_nullable=YES`), with no default. This matches the expected schema: audit_trail is a global-capable table where project_id is optional (NULL = global event, UUID = project-scoped event).

---

## 7. RE-OBS-03b: audit.audit_trail.chain_version Column (Live DDL)

**PASS**

Live query result:

| column_name | data_type | is_nullable | column_default |
|---|---|---|---|
| **chain_version** | **smallint** | **NO** | **1** |

The `chain_version` column exists as `SMALLINT`, NOT NULL, with DEFAULT 1. This matches the exact specification from `p19_003` migration and the round-1 audit's expectation.

Default semantics (from `alembic/versions/p19_003_audit_chain_version.py`):
- `chain_version=1` (default, legacy): rows created before P19. Canonical payload does NOT include project_id. Hash computed with original algorithm.
- `chain_version=2` (P19+): rows created after P19. Canonical payload MAY include project_id. Hash includes chain_version in canonical input.

`AuditWriter` (`src/loops/audit_writer.py`) explicitly writes `chain_version=2` for all new events. The DEFAULT 1 backfills existing rows atomically without hash recomputation.

---

## 8. RE-OBS-03c: Both audit_trail Indexes Exist (Live DDL)

**PASS**

Live query of `pg_indexes` for `audit.audit_trail`:

| indexname | indexdef |
|---|---|
| `ix_audit_trail_chain_version` | `CREATE INDEX ix_audit_trail_chain_version ON audit.audit_trail USING btree (chain_version)` |
| `ix_audit_trail_project_id_created_at` | `CREATE INDEX ix_audit_trail_project_id_created_at ON audit.audit_trail USING btree (project_id, created_at)` |

Both P19 indexes are confirmed present:
1. `ix_audit_trail_chain_version` -- btree on `(chain_version)` for chain-integrity queries
2. `ix_audit_trail_project_id_created_at` -- composite btree on `(project_id, created_at)` for project-scoped time-range queries

Additionally, two pre-existing indexes are present (not P19-specific):
- `audit_trail_occurred_at_idx` -- btree on `(occurred_at DESC)`
- `pk_audit_trail` -- unique btree on `(id, occurred_at)`

---

## 9. chain_version=1 Default Row Count

```
chain_version=1 row count: 0
```

The `audit.audit_trail` table is empty in production (0 total rows). This is expected -- the audit trail collects runtime events and no P19 code paths have executed yet (`feature:projects:enabled` is OFF). The column + DEFAULT is what matters for schema correctness, not the row count.

---

## 10. Risk Assessment

| Risk | Level | Notes |
|---|---|---|
| Re-run data corruption | **NONE** | Proven: 1 row, correct UUID, no duplicates |
| DDL schema drift | **NONE** | Live DDL matches deploy script + alembic migration specifications |
| chain_version semantics | **NONE** | DEFAULT 1 correct; AuditWriter writes 2; three-source consistency confirmed |
| Index coverage | **NONE** | Both P19 audit_trail indexes present in live DB |
| Re-runability | **NONE** | 32 OK / 0 FAIL; full idempotent no-op proven |

---

## 11. Acceptance Criteria

| ID | Criterion | Verdict | Evidence |
|---|---|---|---|
| RE-DB-02a | `p19_001_deploy.py` has idempotent CREATE+SEED block | **PASS** | Lines 22 (`CREATE TABLE IF NOT EXISTS`) + 39 (`ON CONFLICT (slug) DO NOTHING`) in source code |
| RE-DB-02b | Re-run is a no-op (0 FAIL) | **PASS** | Live VPS re-run: 32 OK, 0 FAIL |
| RE-DB-02c | No data corruption after re-run | **PASS** | Live query: 1 row, UUID `00000000-0000-0000-0000-000000000001`, slug=`default`, no duplicates |
| RE-OBS-03a | `audit.audit_trail.project_id` exists (uuid, nullable) | **PASS** | Live DDL: `project_id uuid YES default=None` |
| RE-OBS-03b | `audit.audit_trail.chain_version` exists (smallint, NOT NULL, default 1) | **PASS** | Live DDL: `chain_version smallint NO default=1` |
| RE-OBS-03c | Both audit_trail indexes exist | **PASS** | Live DDL: `ix_audit_trail_chain_version` + `ix_audit_trail_project_id_created_at` confirmed |

**6/6 PASS. 0 FAIL.**

---

## 12. Summary & Verdict

### Verdict: PASS (6/6)

| Check | Verdict | Source |
|---|---|---|
| RE-DB-02a | **PASS** | Source code: `CREATE TABLE IF NOT EXISTS` + `ON CONFLICT (slug) DO NOTHING` in `p19_001_deploy.py` |
| RE-DB-02b | **PASS** | Live VPS re-run: 32 OK, 0 FAIL (complete no-op) |
| RE-DB-02c | **PASS** | Live query: 1 row, correct UUID, no duplicates |
| RE-OBS-03a | **PASS** | Live DDL: `project_id uuid nullable=YES` |
| RE-OBS-03b | **PASS** | Live DDL: `chain_version smallint nullable=NO default=1` |
| RE-OBS-03c | **PASS** | Live DDL: both P19 indexes confirmed in `pg_indexes` |

All round-1 findings (FINDING-02 / DB-02 idempotency gap, OBS-03 missing live DDL inspection) are now fully resolved with live evidence. No new findings. The round-1 OBS-03 NEEDS-REVIEW is resolved to PASS.

---

## Footer

| Field | Value |
|---|---|
| Audit status | **PASS** -- 6/6 criteria PASS |
| Critical findings | 0 |
| Medium findings | 0 |
| Low findings | 0 |
| New findings | 0 |
| Round-1 items resolved | FINDING-02/DB-02 (idempotency) + OBS-03 (live DDL) |
| VPS verified | YES -- live queries against `guinevere` DB on port 5433 |
| Re-run verified | YES -- 32 OK / 0 FAIL, no data corruption |
| Recommendation | CLOSE. All round-2 re-audit items pass. P19-012 idempotency and observability are production-ready. |
