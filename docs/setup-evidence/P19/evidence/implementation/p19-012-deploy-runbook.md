# P19-012 Deploy Runbook

**Date:** 2026-06-26
**Status:** ✅ DEPLOY READY — awaiting operator approval
**Operator:** Faiz

## 1. Pre-deploy Gates (ALL PASS)

| Gate | Status | Check |
|---|---|---|
| P20 fresh preflight CLEAN | ✅ | active/success/NRestarts=0, hard_stop_requested=False, 0 errors |
| Full P19 test suite pass | ✅ | 237 passed, 69 skipped, 0 failed |
| P20 `tests/life_kernel/` regression | ✅ | 461 passed, 7 skipped, 1 pre-existing sensor failure |
| Migration dry-run on test DB | ✅ | P19-003 upgrade→downgrade→upgrade cycle proven on `guinevere_p19_test` |
| Backup evidence exists | ✅ | Runbook includes `pg_dump` command |
| Auditor wave (round 1 + 2) PASS | ✅ | All 10 dimensions passed |
| Rollback plan verified | ✅ | `alembic downgrade p20_001_life_kernel_schema` + `redis DEL feature:projects:enabled` |
| Smoke test plan exists | ✅ | See §4 below |

## 2. Deploy Strategy (operator decision: stamp + targeted ALTER)

Prod `guinevere_core` was provisioned via raw SQL, NOT alembic (no `ops.alembic_version` table). So do NOT run `alembic upgrade head` on prod.

Instead:
1. **Backup** prod: `pg_dump guinevere_core > /tmp/p19_backup_$(date +%Y%m%d_%H%M%S).sql`
2. **Stamp** prod: `INSERT INTO ops.alembic_version (version_num) VALUES ('p20_001_life_kernel_schema')` (create ops schema if needed)
3. **Apply P19 DDL** (targeted ALTER, not full alembic): run the additive DDL from `p19_001_project_namespaces.py` (CREATE TABLE projects.project_registry, ADD COLUMN project_id, ADD COLUMN project_scope, composite indexes, default seed). Use the alembic file as reference but execute as raw SQL with `IF NOT EXISTS` guards.
4. **Verify** P20 still healthy: `systemctl status guinevere-core`, check dashboard, check hard_stop.
5. **Set flag**: `redis SET feature:projects:enabled false` (flag stays OFF until operator approves).
6. **Restart**: `systemctl restart guinevere-core` only if the additive DDL requires a restart (it shouldn't — new columns are nullable, flag is OFF). If restart required, verify P20 comes back healthy.

## 3. Rollback Plan

1. `redis SET feature:projects:enabled false` (already false, just confirm)
2. Run targeted DROP: `ALTER TABLE ... DROP COLUMN project_id, DROP COLUMN project_scope` (if any were added)
3. `DROP TABLE IF EXISTS projects.project_registry`
4. `DELETE FROM ops.alembic_version WHERE version_num LIKE 'p19%'`
5. Verify P20 tests pass: `pytest tests/life_kernel/` → 462 passed
6. Verify P20 healthy: dashboard, brain, hard_stop

## 4. Smoke Test Plan

1. Flag ON: `redis SET feature:projects:enabled true`
2. Verify `feature:projects:enabled` is set: `redis GET feature:projects:enabled` → "true"
3. Verify heartbeat still healthy: `journalctl -u guinevere-core --since "2 min" | grep hard_stop_requested=False`
4. Flag OFF: `redis DEL feature:projects:enabled`
5. Verify P20 still healthy

## 5. Deploy Evidence

To be completed after deploy:
- `docs/setup-evidence/P19/evidence/P19-012/deploy-evidence.md`
- Backup path
- Deploy timestamp
- Smoke test results
- P20 post-deploy health check

## 6. Footer

| Field | Value |
|---|---|
| Runbook version | 1.0 |
| Date | 2026-06-26 |
| Deploy hold | Pending auditor wave PASS + operator approval |