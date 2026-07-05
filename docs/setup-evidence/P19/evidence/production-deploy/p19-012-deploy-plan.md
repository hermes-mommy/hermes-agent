# P19-012 Deploy Execution Plan

**Date:** 2026-06-26 21:45 WIB
**Author:** Guinevere (parent)
**Operator:** Faiz
**Phase:** 2 — Planning Executable

---

## 1. Preflight Summary

See `p19-012-runtime-preflight.md` for full details.

| Key Finding | Impact |
|---|---|
| Prod DB is `guinevere` (not `guinevere_core`) | Backup target corrected |
| `ops.alembic_version` EXISTS with `p20_001` | No need to create schema/table |
| P19 DDL NOT applied | Clean slate — apply all 3 migrations |
| P20 healthy | Safe to proceed |
| Redis feature flag NOT set | Flag stays OFF until smoke tests |

## 2. Deploy Strategy

### Strategy: Stamp + Targeted SQL (NOT `alembic upgrade head`)

The alembic migration files contain `op.execute()` with `IF NOT EXISTS` guards. We will run the upgrade SQL directly, then stamp the alembic version table. This avoids the alembic migration engine's schema discovery which could fail on a divergent production schema.

### Execution Order

1. **Backup** `guinevere` DB → verify backup
2. **Stamp** `p19_001` → run `p19_001_project_namespaces.py` upgrade SQL → verify
3. **Stamp** `p19_002` → run `p19_002_project_id_not_null.py` upgrade SQL → verify
4. **Stamp** `p19_003` → run `p19_003_audit_chain_version.py` upgrade SQL → verify
5. **Post-migration verification** → schema, registry, backfill, P20 health
6. **Deploy runtime files** (if needed) → restart only core if needed
7. **Smoke tests** → flag ON, verify, flag OFF
8. **Audit wave 1** → 6 dimensions
9. **Fix findings** → re-audit
10. **Finalize** → docs, evidence, final report

## 3. Exact DDL to Apply

### Migration 1: `p19_001_project_namespaces`

From `alembic/versions/p19_001_project_namespaces.py` upgrade():

1. **CREATE** `projects.project_registry` table (IF NOT EXISTS)
2. **SEED** default project UUID `00000000-0000-0000-0000-000000000001`
3. **ADD COLUMN IF NOT EXISTS** `project_id UUID` to 14 tables across 6 schemas
4. **ADD COLUMN IF NOT EXISTS** `project_scope TEXT NOT NULL DEFAULT 'project'` to 4 memory/KG tables
5. **BACKFILL** `project_id = default UUID` WHERE NULL for 11 tables
6. **CREATE INDEX IF NOT EXISTS** 18 composite indexes
7. **SWAP** domain_mind_state unique constraint from (domain) to (project_id, domain)

All statements guarded with `IF NOT EXISTS` / `ON CONFLICT DO NOTHING` — **idempotent**.

### Migration 2: `p19_002_project_id_not_null`

From `alembic/versions/p19_002_project_id_not_null.py` upgrade():

1. **PRE-CHECK** SELECT count(*) WHERE project_id IS NULL for 11 tables — abort if any > 0
2. **ALTER COLUMN SET NOT NULL** on project_id for 11 tables

### Migration 3: `p19_003_audit_chain_version`

From `alembic/versions/p19_003_audit_chain_version.py` upgrade():

1. **ADD COLUMN IF NOT EXISTS** `chain_version SMALLINT NOT NULL DEFAULT 1` to audit.audit_trail
2. **CREATE INDEX IF NOT EXISTS** `ix_audit_trail_chain_version`

## 4. Stamp Strategy

| Step | Version | Action |
|---|---|---|
| After p19_001 DDL | `p19_001_project_namespaces` | INSERT INTO ops.alembic_version |
| After p19_002 DDL | `p19_002_project_id_not_null` | INSERT INTO ops.alembic_version |
| After p19_003 DDL | `p19_003_audit_chain_version` | INSERT INTO ops.alembic_version |

## 5. Rollback Plan

**Primary rollback path: `scripts/p19_rollback.py`** (targeted SQL, mirrors the exact deploy).

The alembic `downgrade()` functions in `alembic/versions/p19_001..003` reference the test-DB table name `memory.knowledge_graph` which does NOT exist in production (prod uses `memory.kg_entities`/`kg_edges`/`kg_episodes`/`kg_consent_audit`). Since the deploy was via targeted SQL (not `alembic upgrade`), rollback is also targeted SQL. `scripts/p19_rollback.py` uses the REAL prod table names so rollback is clean and proven. Syntax-validated (py_compile OK).

Rollback order (reverse of deploy): p19_003 (chain_version) -> p19_002 (NOT NULL) -> p19_001 (indexes, unique swap, project_scope, project_id cols, project_registry) -> clear p19 alembic stamps.

If any step fails during deploy:
1. Check which alembic stamps were inserted
2. Run `scripts/p19_rollback.py` (reverse the exact DDL applied)
3. `DELETE FROM ops.alembic_version WHERE version_num LIKE 'p19%'` (handled by rollback script)
4. Verify P20 still healthy

If post-deploy P20 regression:
1. `redis DEL feature:projects:enabled` (already OFF)
2. Run `scripts/p19_rollback.py`
3. Verify P20 tests pass
4. Restore from backup `/tmp/p19_backup_20260626_2145.dump` (mode 600) if structural damage occurred

**DOWNGRADE WARNING:** dropping project_id columns LOSES project partitioning data (which project a row belongs to). Base rows preserved. Acceptable for prod data volume (all default project, no real partitioning to lose).

## 6. Stop Conditions

**HALT immediately if:**
- Any DDL statement returns an error
- `p19_002` pre-check finds NULL project_id rows (backfill failed)
- P20 `hard_stop_requested` becomes True during deploy
- Any destructive statement is detected (DROP, TRUNCATE, DELETE without WHERE)
- `guinevere-core` crashes or enters restart loop
- Brain fallback count > 0 after deploy
- Any secret appears in output

## 7. Runtime Deploy

### Files to Deploy

All P19 source files should already be on the VPS (they were deployed as part of the P19 implementation). Verify:

| Category | Files | Check |
|---|---|---|
| NEW | src/projects/*.py | Must exist on VPS |
| MODIFIED | src/life_kernel/*.py | Must have project_id fields |
| MIGRATIONS | alembic/versions/p19_*.py | Must exist on VPS |
| SCRIPTS | scripts/p19_backfill.py | Must exist on VPS |
| TESTS | tests/projects/*.py | Optional on VPS |

### Service Restart

Only restart `guinevere-core.service` if needed. The P19 DDL adds nullable columns — the existing code should work without restart. If the code was already deployed with P19 support, it just needs the DDL.

**Decision: Restart core after DDL to pick up schema changes, but only after verifying no crash risk.**

## 8. Smoke Test Plan

1. Verify `projects.project_registry` has default project
2. Verify `project_id` columns exist and are backfilled
3. Verify `project_scope` columns exist on memory tables
4. Verify `chain_version` column exists on audit.audit_trail
5. Verify P20 heartbeat still healthy (hard_stop=False, think_complete>0)
6. Verify no new errors in core journal
7. Set `feature:projects:enabled=true` → verify registry can be read
8. Set `feature:projects:enabled=false` → verify P20 unchanged

## 9. Evidence Deliverables

All files go under `docs/setup-evidence/P19/evidence/production-deploy/`:

| # | File | Phase |
|---|---|---|
| 1 | p19-012-runtime-preflight.md | ✅ DONE |
| 2 | p19-012-deploy-plan.md | ✅ DONE (this file) |
| 3 | p19-012-backup-evidence.md | Phase 3 |
| 4 | p19-012-schema-migration-evidence.md | Phase 4-5 |
| 5 | p19-012-service-deploy-evidence.md | Phase 6 |
| 6 | p19-012-smoke-test.md | Phase 7 |
| 7-12 | audits/round-1/*.md | Phase 8 |
| 13-18 | audits/round-2/*.md | Phase 10 |
| 19 | p19-012-final-production-report.md | Phase 11 |
| 20 | p19-012-auditor-gate.md | Phase 11 |

## 10. Footer

| Field | Value |
|---|---|
| Plan status | READY TO EXECUTE |
| DB target | `guinevere` (corrected from `guinevere_core`) |
| Migration strategy | Stamp + targeted SQL (3 migrations) |
| Rollback | Downgrade SQL + delete alembic stamps |
| Next step | Phase 3: Backup gate |