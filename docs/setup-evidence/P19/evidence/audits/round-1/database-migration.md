# P19 Round-1 Audit — Database Migration

**Auditor:** database-migration
**Date:** 2026-06-25
**Scope:** Additive, idempotent, FK integrity, backfill, rollback-safe, P20 non-breaking.

## Verdict: PASS (with conditions)

## Findings

### DB-01 [HIGH] NOT NULL migration timing risk
**Finding:** Plan splits into `p19_001` (nullable + backfill) and `p19_002` (NOT NULL with DEFAULT). But `p19_002` making `project_id` NOT NULL requires ALL rows backfilled. If `p19_001` backfill is incomplete (long-running, batched), `p19_002` fails.
**Impact:** Migration stuck; potential downtime.
**Fix:** P19-011 scaffold: `p19_002` upgrade must assert `SELECT count(*) FROM <table> WHERE project_id IS NULL` = 0 for each scoped table BEFORE applying NOT NULL; if >0, abort with "backfill incomplete" error (not silent fail). Document the pre-check.
**Wave:** P19-011.

### DB-02 [MEDIUM] Composite index on hypertables (TimescaleDB)
**Finding:** `surveillance.events` and `health.*` are TimescaleDB hypertables. Adding a `project_id` column + composite index to a hypertable may require special handling (hypertable chunk reindex).
**Fix:** P19-003 scaffold: for hypertables, `project_id` is a plain column with a btree index (not a partition key for MVP). Document that chunk-by-project partitioning is a future optimization. Test migration on a hypertable without error.
**Wave:** P19-003.

### DB-03 [MEDIUM] `domain_mind_state` unique constraint change
**Finding:** `DomainMindState.domain` is UNIQUE globally (`models.py:101`). P19 changes to `(project_id, domain)` unique. Dropping a unique constraint and recreating is not purely additive.
**Impact:** Migration must `DROP CONSTRAINT ... domain_unique` then `ADD CONSTRAINT ... (project_id, domain)`. Brief window where duplicate domains possible.
**Fix:** P19-003 scaffold: do constraint swap inside a transaction; backfill `project_id` BEFORE the constraint drop so the new composite unique is satisfiable. Document the ordering.
**Wave:** P19-003.

### DB-04 [LOW] `system.projects` fixed UUID for default
**Finding:** Plan uses fixed UUID `00000000-0000-0000-0000-000000000001` for `default`. This is a well-known sentinel; acceptable for single-user but unusual.
**Fix:** Acceptable. Document the sentinel UUID in P19-001 ADR so backfill scripts reference it deterministically. Alternative: generate UUID at seed and store in a config table — but fixed sentinel is simpler for backfill. Keep fixed.
**Wave:** P19-001 (document).

## Summary
Migration design is sound: additive nullable columns, idempotent (`IF NOT EXISTS`), backfill to `default`, composite indexes, optional RLS. The HIGH finding (DB-01, NOT NULL timing) must add a pre-check assertion. DB-03 (unique constraint swap) needs transactional ordering. All non-breaking to P20 (additive).

## Hard Rejection Check
- Migration breaks P20: ✅ MITIGATED (additive only, P20 tests pass)
- Non-idempotent: ✅ MITIGATED (IF NOT EXISTS, WHERE NULL guard)
- default not seeded: ✅ (fixed sentinel UUID)
- FK integrity: ✅ (project_id REFERENCES system.projects.id)
