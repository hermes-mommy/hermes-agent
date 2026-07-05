# P19-012 Audit: Rollback / Idempotency

**Auditor:** Independent sub-agent (rollback-idempotency scope)
**Date:** 2026-06-27
**Deploy target:** `guinevere` DB on guinevere-vps (localhost:5433)
**Migration files:** p19_001, p19_002, p19_003

---

## 1. Scope & Method

This audit verifies that P19-012 production deploy is safely reversible and
idempotent. Scope: backup integrity, downgrade() completeness, alembic stamp
rollback, script idempotency, feature flag path, and data preservation.

Evidence sources:
- `p19-012-deploy-plan.md` (rollback plan, section 5)
- `p19-012-backup-evidence.md`
- `p19-012-schema-migration-evidence.md`
- `alembic/versions/p19_001_project_namespaces.py` (upgrade + downgrade)
- `alembic/versions/p19_002_project_id_not_null.py` (upgrade + downgrade)
- `alembic/versions/p19_003_audit_chain_version.py` (upgrade + downgrade)
- `scripts/p19_001_deploy.py`
- `scripts/p19_002_003_deploy.py`

---

## 2. Audit Checks Summary

| ID | Check | Verdict | Notes |
|---|---|---|---|
| RB-01 | Backup exists + restorable | **PASS** | 1.2 GB, pg_restore -l verified |
| RB-02 | Rollback SQL in all 3 downgrade() | **NEEDS-REVIEW** | p19_001/p19_002 downgrade miss 4 KG tables adapted in prod |
| RB-03 | Alembic stamp rollback safe | **PASS** | DELETE ... LIKE 'p19%' preserves p20_001 |
| RB-04 | Idempotency — re-run safe | **PASS** | All IF NOT EXISTS / ON CONFLICT |
| RB-05 | Feature flag rollback path | **PASS** | flag=None/OFF, DEL returns byte-identical P20 |
| RB-06 | No prod data rewritten destructively | **PASS** | Additive DDL only, NULL-to-default backfill |
| RB-07 | Backup exclusions don't block P19 rollback | **PASS** | P19 DDL touches projects/memory/life_kernel/audit/consent/surveillance |
| RB-08 | Downgrade data-loss warning acceptable | **PASS** | 3 episodes, 6 facts; partitioning data is cosmetic |

**Overall: NEEDS-REVIEW** (RB-02 gap requires operator decision before rollback)

---

## 3. RB-01: Backup Exists + Restorable

**Verdict: PASS**

Evidence from `p19-012-backup-evidence.md`:

| Field | Value |
|---|---|
| Path | `/tmp/p19_backup_20260626_2145.dump` |
| Size | 1.2 GB |
| Format | pg_dump custom (-F c) |
| pg_restore -l | Verified, 49+ objects listed |
| Exit code | 0 |
| Excluded schemas | health, _timescaledb_internal, _timescaledb_cache, _timescaledb_functions, _timescaledb_config, timescaledb_experimental |

Restore command documented: `pg_restore -d guinevere -h localhost -p 5433 -U guinevere_core -c /tmp/p19_backup_20260626_2145.dump`

The `-c` flag provides a clean restore (drops objects first). The backup evidence warns that a full restore would overwrite P20 runtime data accumulated since backup time -- this is inherent to any backup-based rollback and is mitigated by the alternative path (downgrade DDL + backup as last resort only).

**No issues.**

---

## 4. RB-02: Rollback SQL in All 3 downgrade() Functions

**Verdict: NEEDS-REVIEW**

### 4.1 p19_003 downgrade() -- COMPLETE

- Drops `ix_audit_trail_chain_version` index (IF EXISTS)
- Drops `chain_version` column from `audit.audit_trail` (IF EXISTS)
- Covers the 2 upgrade statements exactly.

**p19_003 downgrade is complete and correct.**

### 4.2 p19_002 downgrade() -- INCOMPLETE FOR PRODUCTION

The downgrade function iterates `NOT_NULL_TABLES` (line 31-43) which includes:
```
memory.knowledge_graph     <-- does NOT exist in production
```

And does NOT include:
```
memory.kg_entities         <-- EXISTS in production, NOT NULL applied
memory.kg_edges            <-- EXISTS in production, NOT NULL NOT applied (nullable)
memory.kg_episodes         <-- EXISTS in production, NOT NULL NOT applied (nullable)
memory.kg_consent_audit    <-- EXISTS in production, NOT NULL NOT applied (nullable)
```

The production deploy script (`p19_002_003_deploy.py`) adapted its `not_null_tables` list to include `memory.kg_entities` instead of `memory.knowledge_graph`. The p19_002 alembic migration was NOT updated to match.

**Impact:** Running `alembic downgrade p19_001` would attempt to DROP NOT NULL on `memory.knowledge_graph` (non-existent table, would error or no-op depending on engine) and would NOT drop NOT NULL on `memory.kg_entities` (which remains constrained). After rollback, `kg_entities.project_id` stays NOT NULL.

**Risk assessment:** MODERATE. If post-rollback code inserts into `kg_entities` without project_id, it would fail with a NOT NULL constraint violation. However, since the feature flag is OFF and P20 code paths do not reference project_id, this is unlikely to trigger in practice.

### 4.3 p19_001 downgrade() -- INCOMPLETE FOR PRODUCTION

The downgrade function drops columns from 14 tables. Production adapted 4 KG tables:

| Alembic migration references | Production adapted to |
|---|---|
| `memory.knowledge_graph` (project_id + project_scope) | `memory.kg_entities` (project_id + project_scope) |
| — | `memory.kg_edges` (project_id) |
| — | `memory.kg_episodes` (project_id) |
| — | `memory.kg_consent_audit` (project_id) |

The p19_001 downgrade:
- **WILL** drop project_id from `memory.knowledge_graph` (no-op, table doesn't exist)
- **WILL NOT** drop project_id from `kg_entities`, `kg_edges`, `kg_episodes`, `kg_consent_audit`
- **WILL** drop project_scope from `memory.knowledge_graph` (no-op)
- **WILL NOT** drop project_scope from `kg_entities`

Additionally, `ix_kg_entities_project_id` index created by production script is NOT dropped by the alembic downgrade.

**Impact:** After alembic downgrade, 4 KG tables retain project_id columns (plus project_scope on kg_entities), and 1 extra index remains. These are inert (columns default to NULL, index is harmless), but the schema is not truly reverted to pre-P19 state.

### 4.4 Recommendation

Two options for the operator:

**Option A (surgical, preferred):** After running alembic downgrade, manually execute:
```sql
ALTER TABLE memory.kg_entities DROP COLUMN IF EXISTS project_id;
ALTER TABLE memory.kg_entities DROP COLUMN IF EXISTS project_scope;
ALTER TABLE memory.kg_edges DROP COLUMN IF EXISTS project_id;
ALTER TABLE memory.kg_episodes DROP COLUMN IF EXISTS project_id;
ALTER TABLE memory.kg_consent_audit DROP COLUMN IF EXISTS project_id;
DROP INDEX IF EXISTS memory.ix_kg_entities_project_id;
```
Then add these to a manual rollback script or fix the alembic migration files.

**Option B (full restore):** Use the pg_restore backup path, accepting P20 runtime data loss since backup time.

**Option C (leave residual columns):** The leftover columns are inert. If rollback is only needed to unblock P20, the residual columns can be cleaned up in a future migration. This is the lowest-risk option.

---

## 5. RB-03: Alembic Stamp Rollback Safe

**Verdict: PASS**

The deploy plan specifies:
```sql
DELETE FROM ops.alembic_version WHERE version_num LIKE 'p19%'
```

Evidence from migration evidence: the version table contains:
- `p19_001_project_namespaces`
- `p19_002_project_id_not_null`
- `p19_003_audit_chain_version`
- `p20_001_life_kernel_schema`

The `LIKE 'p19%'` pattern matches exactly the 3 P19 versions and does NOT touch `p20_001_life_kernel_schema`. The p20_001 stamp is preserved.

The stamp insertion in `p19_002_003_deploy.py` (line 103) uses `ON CONFLICT DO NOTHING`, confirming stamps were inserted safely.

**No issues.**

---

## 6. RB-04: Idempotency -- Re-run Safe

**Verdict: PASS**

### 6.1 scripts/p19_001_deploy.py

All statements use idiomatically safe SQL:
- `ADD COLUMN IF NOT EXISTS project_id UUID` (lines 27-28) -- no-op if column exists
- `ADD COLUMN IF NOT EXISTS project_scope ...` (line 42) -- no-op if column exists
- `UPDATE ... SET project_id = DEFAULT WHERE project_id IS NULL` (line 62) -- 0 rows affected if already backfilled (idempotent)

Re-running this script on an already-migrated DB would produce 0 actual changes (all columns exist, 0 NULLs to backfill).

### 6.2 scripts/p19_002_003_deploy.py

- **p19_002 pre-check:** `SELECT count(*) WHERE project_id IS NULL` (line 79). On an already-migrated DB, this returns 0 (all rows backfilled). The subsequent `ALTER TABLE ... SET NOT NULL` would no-op (column already NOT NULL).
- **Indexes:** All `CREATE INDEX IF NOT EXISTS` (lines 26-39) -- no-op if index exists.
- **pgvector indexes:** Conditional on `embedding` column existence (line 47) -- safe to re-run.
- **domain_mind_state swap:** `DROP INDEX IF EXISTS` + `CREATE UNIQUE INDEX IF NOT EXISTS` (lines 57-65) -- idempotent.
- **p19_003:** `ADD COLUMN IF NOT EXISTS chain_version` + `CREATE INDEX IF NOT EXISTS` (lines 94-97) -- no-op if already exists.
- **Alembic stamps:** `INSERT ... ON CONFLICT DO NOTHING` (line 104) -- no-op if already stamped.

**Both scripts are fully idempotent. Re-running them is safe.**

---

## 7. RB-05: Feature Flag Rollback Path

**Verdict: PASS**

The deploy plan specifies: `redis DEL feature:projects:enabled` returns to P20 byte-identical behavior.

Evidence from migration evidence (section 4):
- `feature:projects:enabled` is read by `_is_projects_flag_on` helper
- Current value: **None** (key does not exist in Redis db0)
- All P19 runtime code paths (cognition.py, dashboard_writer.py, graph.py, heartbeat.py, redis_client.py) read the flag with fail-safe OFF behavior
- When flag is OFF/None, P19 code paths are transparent -- byte-identical P20 behavior confirmed

The flag is already OFF. No action needed for rollback. If flag was ON, `redis DEL feature:projects:enabled` would immediately revert to fail-safe OFF behavior (no restart needed since it's read per-request).

**No issues.**

---

## 8. RB-06: No Existing Prod Data Rewritten Destructively

**Verdict: PASS**

All P19-012 DDL was purely additive:
- `ADD COLUMN IF NOT EXISTS` -- adds new columns, never modifies existing ones
- `UPDATE ... SET project_id = DEFAULT WHERE project_id IS NULL` -- backfills NULLs to a default UUID; rows that already have a value are untouched
- `CREATE TABLE IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS` -- new objects only
- `ALTER COLUMN SET NOT NULL` -- adds a constraint but doesn't modify data values

The only structural modification was the domain_mind_state unique constraint swap: dropping `ix_domain_mind_state_domain` (unique on domain) and creating `ix_domain_mind_state_project_id_domain` (unique on project_id, domain). The downgrade restores the original constraint. This is the only destructive action, and it's fully reversible via the downgrade function.

From backfill verification: 3 episodes, 6 facts, 6 KG entities. All were NULL project_id before deploy, now backfilled to default UUID. This backfill is idempotent (re-running sets the same value).

**No existing data was destructively rewritten.**

---

## 9. RB-07: Backup Exclusions Don't Block P19 Rollback

**Verdict: PASS**

Excluded schemas from backup:
- `health` -- monitoring tables, not touched by P19
- `_timescaledb_internal` -- TimescaleDB internal metadata
- `_timescaledb_cache` -- TimescaleDB internal cache
- `_timescaledb_functions` -- TimescaleDB internal functions
- `_timescaledb_config` -- TimescaleDB internal config
- `timescaledb_experimental` -- TimescaleDB experimental features

P19 DDL touches these schemas: `projects`, `memory`, `life_kernel`, `audit`, `consent`, `surveillance`.

None of the excluded schemas overlap with P19-migrated schemas. The `surveillance.events` table is in the `surveillance` schema (not `_timescaledb_internal`), and the backup includes it. TimescaleDB hypertable chunks within `surveillance` are also included.

**The exclusions do not affect P19-specific rollback capability.**

---

## 10. RB-08: Downgrade Data-Loss Warning Acceptable

**Verdict: PASS**

The p19_001 module docstring warns:
> "WARNING: project_id partitioning data is permanently lost when columns are dropped."

The upgrade() docstring elaborates:
> "Downgrade warning: base rows are preserved, but project_id partitioning data is lost on downgrade (columns are dropped)."

Current production data volume (from migration evidence section 3.8):

| Table | Rows |
|---|---|
| memory.episodes | 3 |
| memory.semantic_facts | 6 |
| memory.kg_entities | 6 |
| All other P19 tables | 0 |

Total: 15 rows with project_id assignments. All assigned to the default project UUID. Downgrade would drop the project_id columns, losing these assignments -- but since all rows belong to the same default project, the "lost" data is effectively the constant `00000000-0000-0000-0000-000000000001` repeated 15 times. No unique per-row project assignments exist.

**The data loss is cosmetic and acceptable for rollback of a minimal production dataset.**

---

## 11. Detailed Findings

### FINDING-01 (NEEDS-REVIEW): Alembic downgrade() functions not adapted to production KG tables

**Severity:** Moderate
**Check:** RB-02
**Description:** The production deploy adapted 4 KG tables (`kg_entities`, `kg_edges`, `kg_episodes`, `kg_consent_audit`) in place of the non-existent `memory.knowledge_graph`. The alembic downgrade functions for p19_001 and p19_002 were NOT updated to match. Running `alembic downgrade` would leave residual project_id columns and NOT NULL constraints on production KG tables, and would attempt to drop columns from the non-existent `memory.knowledge_graph`.
**Impact:** Rollback leaves 4 tables with residual columns + 1 residual index. Does NOT cause data loss or P20 regression. May cause insert failures into `kg_entities` if post-rollback code omits project_id.
**Mitigation:** Operator should choose Option A (manual cleanup SQL), Option B (full restore from backup), or Option C (accept residual columns as inert). See section 4.4.
**Root cause:** Production adaptation documented in `p19-012-schema-migration-evidence.md` section 2 was not back-ported to alembic migration files.

### FINDING-02 (INFO): Alembic migration references non-existent table

**Severity:** Low (informational)
**Check:** RB-02
**Description:** Both p19_001 and p19_002 alembic migrations reference `memory.knowledge_graph` which does not exist in production. The upgrade() functions also reference it (e.g., ADD COLUMN to knowledge_graph, backfill knowledge_graph). Running alembic upgrade directly (rather than the production scripts) would error on these statements. The production scripts correctly bypassed this by using the actual KG table names.
**Impact:** Alembic migrations as-written cannot run directly against production. The deploy plan anticipated this (section 2: "Stamp + Targeted SQL (NOT alembic upgrade head)"). This is a documentation/maintenance concern, not a runtime issue.
**Recommendation:** Either fix the alembic migration files to match production reality, or document clearly that these files are code-frozen test artifacts and the scripts are the production source of truth.

---

## 12. Verdict

**NEEDS-REVIEW**

| Component | Status |
|---|---|
| Backup | PASS -- exists, verified, restorable |
| Downgrade DDL | NEEDS-REVIEW -- 4 KG tables + 1 index not covered |
| Stamp rollback | PASS -- p20_001 preserved |
| Idempotency | PASS -- all statements guarded |
| Feature flag | PASS -- already OFF |
| Data safety | PASS -- additive only, minimal data |
| Backup scope | PASS -- exclusions don't affect P19 |
| Data loss risk | PASS -- 15 rows, all default-project |

**The deploy has a clean rollback path with one gap:** the alembic downgrade functions were not adapted to the production KG table adaptation. This gap is non-destructive (residual columns are inert, P20 is unaffected) but means a clean schema rollback requires manual SQL or backup restore. Operator should select a mitigation option from section 4.4 before declaring rollback tested/proven.

---

| Field | Value |
|---|---|
| Audit type | Rollback / Idempotency |
| Verdict | **NEEDS-REVIEW** |
| Blocking findings | 1 (FINDING-01: downgrade gap on 4 KG tables) |
| Informational findings | 1 (FINDING-02: alembic files reference non-existent table) |
| Audit file | `docs/setup-evidence/P19/evidence/production-deploy/audits/round-1/rollback-idempotency.md` |
