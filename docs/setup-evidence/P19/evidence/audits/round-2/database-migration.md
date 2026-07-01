# P19 Round-2 Re-Audit — Database Migration

**Auditor:** database-migration
**Date:** 2026-06-25
**Scope:** Verify all round-1 database-migration findings resolved.

## Verdict: PASS

## Round-1 Findings — Resolution Status

| # | Round-1 Finding | Resolution | Status |
|---|---|---|---|
| DB-01 [HIGH] | NOT NULL migration timing | Plan §P19-011: p19_002 pre-check asserts NULL count = 0 before NOT NULL; aborts with "backfill incomplete" if >0 | ✅ RESOLVED |
| DB-02 [MEDIUM] | Hypertable composite index | Plan §P19-003: plain column + btree; chunk-by-project future; hypertable migration test | ✅ RESOLVED |
| DB-03 [MEDIUM] | `domain_mind_state` unique constraint swap | Plan §P19-003: transactional (backfill before DROP+ADD); ordering documented | ✅ RESOLVED |
| DB-04 [LOW] | Sentinel UUID for default | Plan §P19-001 ADR: fixed UUID documented | ✅ RESOLVED |

## Re-Audit Notes
All 4 database-migration findings resolved. The critical DB-01 fix adds a pre-check assertion to `p19_002` (NOT NULL migration): it asserts `SELECT count(*) FROM <table> WHERE project_id IS NULL` = 0 for each scoped table BEFORE applying NOT NULL, aborting with an explicit "backfill incomplete for <table>" error (not silent fail) if any rows remain. This prevents migration-stuck/downtime.

DB-03 (constraint swap) is transactional: backfill `project_id = default` BEFORE `DROP CONSTRAINT domain_unique`, then `ADD CONSTRAINT (project_id, domain)`. Hypertable handling (DB-02) documented. Sentinel UUID (DB-04) in ADR.

The hard-rejection criteria (migration breaks P20, non-idempotent, default not seeded, FK integrity) are all mitigated. Migrations remain additive + idempotent + rollback-safe.

## Hard Rejection Check
- Migration breaks P20: ✅ MITIGATED (additive only)
- Non-idempotent: ✅ MITIGATED (IF NOT EXISTS, WHERE NULL guard, pre-check)
- default not seeded: ✅ (sentinel UUID)
- FK integrity: ✅
