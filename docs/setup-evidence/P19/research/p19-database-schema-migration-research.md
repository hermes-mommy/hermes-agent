# P19 Research: Database Schema & Migration

**Status:** ✅ COMPLETE
**Date:** 2026-06-25
**Author:** Guinevere (parent-authored from scout reports + direct reads)
**Scope:** Database schema changes needed for P19 across all PostgreSQL schemas.

---

## 1. Executive Summary

P19 requires adding a `project_id` column to ~14 tables across 7 PostgreSQL schemas, plus a new `projects.project_registry` registry table. All migrations must be **additive** (nullable columns first, backfill, then NOT NULL), **idempotent** (`alembic upgrade head` + `downgrade -1` + `upgrade head` works), and **non-breaking to P20** (no drop/rename of existing columns). The P19 migration slots in after `p20_001_life_kernel_schema` as the new Alembic head.

---

## 2. Existing PostgreSQL Schemas

- `public` — baseline.
- `memory` — episodes, semantic_memories, procedural_skills, session_summaries, kg_entities, kg_edges, kg_consent_audit.
- `life_kernel` — life_mind_state, heartbeat_record, domain_mind_state, audit_journal.
- `persona` — persona_state, mood_history, milestones, relationship_state, drift_log.
- `consent` — consent_ledger.
- `surveillance` — events (windows_events hypertable P15).
- `finance` / `financial` — transactions, accounts.
- `gamification` — XP/level tracking.
- `projects` — loop_instances, tasks.
- `audit` — audit_trail.
- `health` — wearable health hypertables (P14).
- `system` — feature_flags (referenced in P22 plan).

---

## 3. Existing Migrations

**Current head:** `p20_001_life_kernel_schema` (down_revision `p5_024`).

**Lineage (newest→oldest):**
1. `p20_001_life_kernel_schema` → `p5_024` — life_kernel tables.
2. `p5_024` → `p5_015_add_skill_embedding` — session_summaries.
3. `p5_015_add_skill_embedding` → `3d41deeca703` (P18) — procedural_skills embedding.
4. `f47a9c2e8b1d` (merge) → `7239fd4b3b5a`, `3d41deeca703` — projects.loop_instances extensions.
5. `7239fd4b3b5a` → `p6_gamification_schema` — drift_log reviewer/action.
6. `p6_gamification_schema` → `p5_add_loop_indexes` — gamification schema.
7. `p5_add_loop_indexes` → `p5_extend_loops` — loop_instances indexes.
8. `p5_extend_loops` → `65f863220922` — loop_instances columns.
9. `3d41deeca703` (P18) → `65f863220922` — episodes FSRS columns.
10. `65f863220922` → `e401bb5fd274` — episodes search_vector + do_not_recall.
11. `e401bb5fd274` → `2bed93fd1dd0` — initial 47-table schema.
12. `2bed93fd1dd0` → `<base>`.

**Naming convention:** `p{phase}_{seq}_{description}.py`. P19 migration: `p19_001_project_namespaces.py`.

---

## 4. Project Registry Table (NEW)

```sql
CREATE TABLE projects.project_registry (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            TEXT NOT NULL UNIQUE,          -- e.g. 'work', 'personal', 'default'
    name            TEXT NOT NULL,                  -- display name
    status          TEXT NOT NULL DEFAULT 'active'  -- active | paused | archived
                    CHECK (status IN ('active','paused','archived')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    archived_at     TIMESTAMPTZ,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    default_channel_id    TEXT,                    -- Discord channel default for this project
    dashboard_channel_id  TEXT,                    -- per-project dashboard channel (nullable)
    log_channel_id        TEXT,                    -- per-project log channel (nullable)
    accent_color          TEXT,                    -- optional Discord embed accent
    CONSTRAINT slug_format CHECK (slug ~ '^[a-z0-9][a-z0-9_-]*$')
);
```

Seed `default` project:
```sql
INSERT INTO projects.project_registry (id, slug, name, status)
VALUES ('00000000-0000-0000-0000-000000000001', 'default', 'Default Project', 'active')
ON CONFLICT (slug) DO NOTHING;
```

---

## 5. Tables Requiring project_id Column

| Schema.Table | Current columns | P19 addition |
|---|---|---|
| `life_kernel.life_mind_state` | id, phase, is_active, observations, goals, commitments, concerns, decision_context, last_heartbeat, updated_at | + `project_id UUID` (FK projects.project_registry, default 'default') |
| `life_kernel.heartbeat_record` | id, heartbeat_type, success, latency_ms, recorded_at | + `project_id UUID` |
| `life_kernel.domain_mind_state` | id, domain, state_json, is_active, last_run, run_count, error_count | + `project_id UUID`; unique `(project_id, domain)` (was `domain` alone) |
| `life_kernel.audit_journal` | id, source, entry, recorded_at | + `project_id UUID` |
| `memory.episodes` | (+ FSRS, search_vector, do_not_recall) | + `project_id UUID`, + `project_scope TEXT DEFAULT 'project'` |
| `memory.semantic_memories` | ... | + `project_id UUID`, + `project_scope TEXT` |
| `memory.procedural_skills` | ... | + `project_id UUID`, + `project_scope TEXT` |
| `memory.session_summaries` | ... | + `project_id UUID` |
| `memory.kg_entities` | ... | + `project_id UUID` |
| `memory.kg_edges` | ... | + `project_id UUID` |
| `memory.kg_consent_audit` | ... | + `project_id UUID` |
| `surveillance.events` | event_type, device_id, ... | + `project_id UUID` (nullable) |
| `consent.consent_ledger` | scope, status, granted_at, ... | + `project_id UUID` (nullable; NULL = global) |
| `audit.audit_trail` | event_type, event_payload, principal, event_hash, ... | + `project_id UUID` (nullable; NULL = global safety event) |
| `audit.integration_api_log` (P22) | integration_id, provider, ... | + `project_id UUID` |
| `audit.voice_stream` (P21) | ... | + `project_id UUID` (P21 already specifies nullable) |
| `projects.loop_instances` | loop_id, task, goal, ... | + `project_id UUID` |
| `projects.tasks` | ... | + `project_id UUID` |

---

## 6. Migration Strategy

Per `docs/30-data/33-DatabaseERD_MigrationStrategy_v1.0.md`:

1. **Step 1 (p19_001):** Add nullable `project_id` column to all tables above (no lock — `ADD COLUMN ... NULL`).
2. **Step 2 (p19_001):** Create `projects.project_registry` table + seed `default`.
3. **Step 3 (p19_001 backfill):** Batched `UPDATE ... SET project_id = '<default-uuid>' WHERE project_id IS NULL` for tables where NULL is not the desired final state (life_kernel, memory, projects — NOT consent/audit where NULL = global).
4. **Step 4 (p19_001):** Create composite indexes: `(project_id, created_at)`, `(project_id, embedding)` for vector, `(project_id, domain)` unique.
5. **Step 5 (p19_002, follow-up):** Make `project_id` NOT NULL with DEFAULT for tables where it's always set (life_kernel, memory, projects). Keep nullable for consent/audit/surveillance (NULL = global).
6. **Step 6:** Add foreign keys `project_id REFERENCES projects.project_registry(id)`.

---

## 7. Row-Level Security (RLS)

Optional defense-in-depth (behind feature flag `project:rls_enabled`):
```sql
ALTER TABLE memory.episodes ENABLE ROW LEVEL SECURITY;
CREATE POLICY project_isolation ON memory.episodes
  USING (project_scope = 'global' OR project_id = current_setting('app.current_project', true)::uuid);
```
- Requires `SET app.current_project = <uuid>` per connection.
- Global-scope rows always visible.
- **P19 MVP: wrapper + tests are primary; RLS optional in a later hardening wave.**

---

## 8. Indexing Strategy

- `(project_id, created_at)` composite — time-range queries per project.
- `(project_id, embedding)` — pgvector filtered similarity (or partial ivfflat index per project for large datasets).
- `(project_id, domain)` UNIQUE on `domain_mind_state`.
- `(project_id, scope)` on `consent_ledger` — consent lookup.
- `project_scope` partial index on `memory.episodes` WHERE `project_scope = 'global'` — fast global recall.

---

## 9. Foreign Key Strategy

Every `project_id` references `projects.project_registry.id`. For nullable columns (consent/audit/surveillance), FK is `NULL`-able. For NOT NULL columns (life_kernel/memory/projects), FK is mandatory.

---

## 10. Migration Ordering

`p19_001_project_namespaces.py`:
- `down_revision = "p20_001_life_kernel_schema"` (current head).
- `revision = "p19_001_project_namespaces"`.
- Becomes new head.
- Must NOT break P20 production (additive only).

Follow-up `p19_002_project_id_not_null.py`:
- `down_revision = "p19_001_project_namespaces"`.
- Makes `project_id` NOT NULL with DEFAULT for life_kernel/memory/projects tables.
- Runs AFTER backfill verified.

---

## 11. Backfill Script

Batched to avoid long locks (e.g., 1000 rows per batch):
```sql
UPDATE memory.episodes SET project_id = '00000000-0000-0000-0000-000000000001', project_scope = 'project'
WHERE id IN (SELECT id FROM memory.episodes WHERE project_id IS NULL LIMIT 1000);
```
Repeat until 0 rows. Same for semantic_memories, procedural_skills, session_summaries, kg_entities, kg_edges, kg_consent_audit, life_kernel.*, projects.loop_instances, projects.tasks.

**NOT backfilled (NULL = global is correct):** consent.consent_ledger, audit.audit_trail, audit.integration_api_log, surveillance.events (these can legitimately be NULL/global).

---

## 12. Default Project Record

Seeded in `p19_001` before backfill:
```sql
INSERT INTO projects.project_registry (id, slug, name, status)
VALUES ('00000000-0000-0000-0000-000000000001', 'default', 'Default Project', 'active')
ON CONFLICT (slug) DO NOTHING;
```
Fixed UUID so backfill can reference it deterministically.

---

## 13. Project Archive Strategy

When `/projects archive <slug>`:
```sql
UPDATE projects.project_registry SET status='archived', archived_at=now() WHERE slug = :slug;
```
- Cascading: autonomous work on archived project pauses (heartbeat skips archived projects); data retained; memory recall for archived project still works if explicitly selected.
- No cascade DELETE — data preserved for audit/history.

---

## 14. Cross-Project Query API

Admin API (Faiz-only, audited): query across projects for admin/oversight:
```sql
SELECT project_id, count(*) FROM memory.episodes GROUP BY project_id;
```
Rare, audited via `audit.audit_trail` (event_type `cross_project_query`).

---

## 15. TimescaleDB Hypertables

`surveillance.events` and `health.*` are TimescaleDB hypertables. `project_id` becomes a partition key candidate. For MVP, `project_id` is a plain column with index; chunk-by-project can be evaluated later.

---

## 16. Hard Rejection: Migration Breaking P20

- Migration is additive (nullable columns, new table). No DROP, no RENAME, no type change of existing columns. ✅
- `alembic upgrade head` must leave P20's `life_kernel.*` tables intact (only adds a column). ✅
- P20 tests must still pass post-migration. ✅

---

## 17. Hard Rejection: Non-Idempotent Migration

- `CREATE TABLE IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`. ✅
- `alembic upgrade head` → `alembic downgrade -1` → `alembic upgrade head` must succeed. ✅
- Backfill uses `WHERE project_id IS NULL` guard — re-runnable. ✅

---

## 18. Rollback Plan

```bash
alembic downgrade p20_001_life_kernel_schema  # removes p19_001
# verify P20 still works:
python -m pytest tests/life_kernel/ -q
```
- Downgrade drops `project_id` columns and `projects.project_registry` (after confirming no dependent rows).
- Existing P20 data unaffected (columns were additive).

---

## 19. Testing Strategy

- `test_migration_preserves_p20_state`: snapshot row counts before/after migration; assert unchanged.
- `test_migration_idempotent`: upgrade → downgrade → upgrade succeeds.
- `test_default_project_seeded`: `projects.project_registry` has `default` row after migration.
- `test_project_id_backfilled`: no NULL `project_id` in life_kernel/memory/projects tables after backfill.
- `test_fk_integrity`: all `project_id` values reference `projects.project_registry.id`.

---

## 20. Conclusion

P19 adds `project_id` to ~14 tables + a new `projects.project_registry` registry via two additive, idempotent migrations (`p19_001`, `p19_002`) that slot after `p20_001_life_kernel_schema`. Backfill assigns existing rows to `default` project. Consent/audit/surveillance keep nullable `project_id` (NULL = global). Composite indexes + optional RLS enforce isolation. Migrations are non-breaking to P20 and rollback-safe.
