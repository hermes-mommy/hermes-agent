# ADR-052 Addendum: Database Schema Deviations

**Date:** 2026-06-27  
**Author:** Guinevere (parent)  
**Status:** Accepted  
**Related ADR:** ADR-052-multi-project-context.md

---

## Context

During the P19 round-2 completion audit (2026-06-27), two schema deviations from ADR-052 were identified. Both are functionally correct and have no impact on P19 operations. This addendum documents the deviations and the rationale for accepting them.

---

## Deviation 1: audit_journal JSON Storage

### ADR-052 Specification
ADR-052 states that 22 tables should have a `project_id` SQL column for queryability and indexing.

### Actual Implementation
`life_kernel.audit_journal` does NOT have a SQL `project_id` column. Instead, `project_id` is stored inside the `entry` JSONB payload.

### Evidence
```sql
SELECT column_name FROM information_schema.columns 
WHERE table_schema = 'life_kernel' AND table_name = 'audit_journal';
-- Result: id, source, entry, recorded_at (4 columns, no project_id)

SELECT entry->'project_id' FROM life_kernel.audit_journal 
WHERE recorded_at > '2026-06-27T15:00:00Z' LIMIT 3;
-- Result: 196/196 post-cutover rows have project_id = 00000000-0000-0000-0000-000000000001
```

### Rationale for Acceptance
1. **Sharp cutover:** All entries after 2026-06-27 15:25 WIB include `project_id` in JSON
2. **Pre-P19 legacy:** 5,588 pre-cutover rows are historical self-reflection journals — no project context needed
3. **Flexible schema:** JSONB storage allows audit_journal to evolve without DDL changes
4. **Application layer:** Python code reads `entry->'project_id'` correctly
5. **Scale:** Current volume (5,784 rows) does not require SQL-level indexing on project_id

### Trade-offs
- **Pro:** Flexible schema, no DDL needed for new audit fields
- **Con:** Cannot use `WHERE project_id = :pid` in SQL without JSON extraction
- **Mitigation:** If volume grows significantly, add a generated column or index on `entry->'project_id'`

### Decision
**ACCEPTED** — JSON storage is an acceptable design choice for audit_journal. No fix required.

---

## Deviation 2: project_registry Column Naming

### ADR-052 Specification
ADR-052 §Key Elements #1 specifies:
- `project_id UUID PK`
- `display_name VARCHAR`
- `description TEXT`
- `project_scope VARCHAR` (project or global)
- `updated_at TIMESTAMP`

### Actual Implementation
`projects.project_registry` uses:
- `id UUID PK` (not `project_id`)
- `name TEXT` (not `display_name`)
- Missing: `description`, `project_scope`, `updated_at`

### Evidence
```sql
SELECT column_name FROM information_schema.columns 
WHERE table_schema = 'projects' AND table_name = 'project_registry';
-- Result: id, slug, name, status, created_at, archived_at, metadata, 
--         default_channel_id, dashboard_channel_id, log_channel_id, accent_color
```

### Rationale for Acceptance
1. **Functional mapping:** Python layer (`src/projects/registry.py`) maps `id` to `project_id` correctly
2. **Metadata field:** `description` and `project_scope` can be stored in the `metadata` JSONB column
3. **No functional impact:** All P19 operations work correctly with the current schema
4. **Cosmetic deviation:** Column naming does not affect data integrity or isolation

### Trade-offs
- **Pro:** Simpler schema, fewer columns
- **Con:** Deviates from ADR-052 spec, requires Python-layer mapping
- **Mitigation:** If downstream phases (P21/P22) need direct SQL access to these fields, add them via additive migration

### Decision
**ACCEPTED** — Cosmetic schema deviation with no functional impact. No fix required.

---

## Impact Assessment

Both deviations are **low risk** and **acceptable** for P19 production:

| Deviation | Risk Level | Functional Impact | Fix Required? |
|-----------|-----------|-------------------|---------------|
| audit_journal JSON storage | LOW | None | No |
| project_registry column naming | LOW | None | No |

---

## Future Considerations

If P19 scales to multiple projects or downstream phases (P21/P22) require direct SQL access:

1. **audit_journal:** Add a generated column `project_id GENERATED ALWAYS AS (entry->>'project_id')` with index
2. **project_registry:** Add `description`, `project_scope`, `updated_at` columns via additive migration

These are **optional enhancements**, not blockers for P19 completion.

---

## Footer

| Field | Value |
|-------|-------|
| Addendum date | 2026-06-27 |
| Related ADR | ADR-052-multi-project-context.md |
| Status | Accepted |
| Author | Guinevere (parent) |
