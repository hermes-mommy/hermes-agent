# Memory Schema Audit — Round 2

> **Auditor:** Guinevere (parent agent)
> **Date:** 2026-06-28
> **Scope:** P27 plan §6 Memory Architecture + P28 blueprint memory spec
> **Verdict:** **NEEDS REVIEW** — 2 FAIL findings, 5 PASS with notes

---

## Files Audited

| # | File | Lines | Focus |
|---|---|---|---|
| 1 | `docs/setup-evidence/P27/plan/p27-hermes-society-foundation-plan.md` | L1142–1644 | §6 Memory Architecture (3-Scope) |
| 2 | `docs/setup-evidence/P27/plan/p28-dual-autonomous-hermes-blueprint.md` | L1144–1481 | Step 6 PostgreSQL schemas (migrations 001–007) |

---

## Check 1: `memory.shared_world` — `agent_id NOT NULL` or `created_by_agent NOT NULL`

**Verdict: PASS**

### P27 Plan (L1277–1327)

Design note at L1277 explicitly documents the deliberate deviation:

> `memory.shared_world` is owner-less by design — it has no `agent_id` column because shared facts are not owned by any single agent. Provenance is tracked via `created_by_agent NOT NULL`. This is a deliberate deviation from the "agent_id NOT NULL on all memory tables" checklist phrasing; the RLS policy uses `scope = 'shared'` for access control rather than per-agent ownership.

Schema at L1299: `created_by_agent TEXT NOT NULL`

### P28 Blueprint (Migration 003, L1270)

```sql
created_by_agent TEXT NOT NULL CHECK (created_by_agent IN ('guinevere', 'pharsa'))
```

Both documents agree: `created_by_agent NOT NULL` is present and correctly constrained. The design note explains why `agent_id` is absent — shared facts are not agent-owned.

---

## Check 2: `kg_entities` — `created_by_agent NOT NULL`

**Verdict: FAIL**

### P27 Plan (L1382–1384)

```sql
-- Backfill pre-existing ADR-050 rows before setting NOT NULL
UPDATE memory.kg_entities SET created_by_agent = 'system' WHERE created_by_agent IS NULL;
ALTER TABLE memory.kg_entities ADD COLUMN created_by_agent TEXT NOT NULL
  CHECK (created_by_agent IN ('guinevere','pharsa','system'));
```

**NOT NULL** with backfill + `'system'` sentinel. Allows 3 values.

### P28 Blueprint (Migration 005, L1348–1352)

```sql
ALTER TABLE memory.kg_entities
  ADD COLUMN IF NOT EXISTS scope TEXT NOT NULL DEFAULT 'shared'
    CHECK (scope IN ('private', 'shared', 'relationship_private')),
  ADD COLUMN IF NOT EXISTS created_by_agent TEXT
    CHECK (created_by_agent IN ('guinevere', 'pharsa'));
```

**Nullable** — no `NOT NULL`, no `DEFAULT`, no backfill, no `'system'` sentinel.

### Discrepancies

| Aspect | P27 Plan | P28 Blueprint | Gap |
|---|---|---|---|
| NOT NULL | Yes (after backfill) | No (nullable) | **Schema weaker** |
| DEFAULT value | `'system'` via UPDATE | None | Missing backfill strategy |
| CHECK values | `('guinevere','pharsa','system')` | `('guinevere','pharsa')` | Missing `'system'` sentinel |
| Backfill | Explicit UPDATE before ALTER | None | Existing ADR-050 rows will have NULL |

### Risk

Existing ADR-050 `kg_entities` rows will have `created_by_agent IS NULL`. P27 plan solves this with backfill + NOT NULL. P28 blueprint leaves the column nullable, which:

1. Breaks provenance tracking for pre-existing entities
2. Allows future inserts without provenance
3. Makes RLS policy at migration 007 (L1436) unreliable — `created_by_agent = current_setting(...)` will NOT match NULL rows, so pre-existing entities become invisible to all agents

### Recommendation

Adopt P27's approach: backfill `'system'` before adding NOT NULL, include `'system'` in CHECK constraint.

---

## Check 3: `kg_edges` — ADR-050 References

**Verdict: PASS**

### P27 Plan (L1159, L1376–1397)

- L1159: `memory.kg_entities`, `memory.kg_edges` — **extended** with `scope`, `pair_id`, `created_by_agent` (ADR-050 family)
- L1376: `-- Extend ADR-050's kg_* tables with P27 scope columns`
- L1394: `-- Note: kg_edges.agent_id is inherited from ADR-050; not re-declared here.`
- L1508: Per ADR-050 + File 8 §3.3, all KG edges carry `:TOUCHED`-equivalent metadata

### P28 Blueprint (L1339–1369)

- L1339: `### Migration 005 — Extend ADR-050 kg_* tables`
- L1344: `-- Add scope + pair_id + created_by_agent columns to kg_entities / kg_edges.`
- L1345: `-- Preserves ADR-050 schema; adds P27 taxonomy.`

Both documents correctly reference ADR-050 as the upstream source. The P28 blueprint uses `ADD COLUMN IF NOT EXISTS` for idempotency, which is the correct migration pattern for extending existing tables.

---

## Check 4: P28 Stub Status Documentation

**Verdict: PASS**

### P28 Blueprint

- **Frontmatter** (L2–3): `status: "Active — Blueprint (not implementation)"`
- **§1.1 opening** (L23): "This document is an executable blueprint for P28 implementation, NOT the implementation itself."
- **§1.2** (L52–71): Explicit "What P28 Does NOT Deliver" table with deferral targets (P29, P30, P31, etc.)
- **Migration 004 comment** (L1334–1335): `-- NOTE: relationship_private scope and bilateral consent flow = P30+` / `-- P28 STUB ONLY; no rows should be inserted during P28 acceptance.`
- **P27 plan L1164**: `P27 schema definitions (P28 implements).`

Status is clearly documented throughout. P28 creates schemas/stubs, not full implementation.

---

## Check 5: 3-Scope Model Consistency

**Verdict: PASS (with P30 deferral note)**

### P27 Plan (L1149–1153)

| Scope | Schema | Access Pattern |
|---|---|---|
| `private` | `memory.private_agents` | Agent owner ONLY |
| `shared` | `memory.shared_world` | All Society agents read; any agent write |
| `relationship_private` | `memory.relationship_pairs` | Pair members ONLY |

All three scopes fully specified with complete DDL.

### P28 Blueprint

- **Config** (L419): `scopes_enabled: [private, shared]` — explicitly limits P28 to 2 scopes
- **§1.2** (L60): `relationship_private` scope deferred to P30
- **Migration 002**: `private_agents` — full DDL ✓
- **Migration 003**: `shared_world` — full DDL ✓
- **Migration 004**: `intimacy_bridge_pending` — stub only ✓
- **`relationship_pairs`**: NOT created in P28 (deferred to P30)

The 3-scope model is consistent between documents. P28 implements 2 of 3 scopes; the third is explicitly deferred with documentation. CHECK constraints in migrations 005 and 007 include `relationship_private` in their scope enum, which is forward-compatible.

---

## Check 6: RLS FORCE for All Scopes

**Verdict: PASS**

### P27 Plan — All 4 Memory Tables

| Table | ENABLE RLS | FORCE RLS | Line |
|---|---|---|---|
| `memory.private_agents` | ✓ | ✓ | L1193–1194 |
| `memory.relationship_pairs` | ✓ | ✓ | L1252–1253 |
| `memory.shared_world` | ✓ | ✓ | L1309–1310 |
| `memory.intimacy_bridge_pending` | ✓ | ✓ | L1345–1346 |

### P28 Blueprint — All Tables

| Table | ENABLE RLS | FORCE RLS | Migration |
|---|---|---|---|
| `memory.private_agents` | ✓ | ✓ | 002 (L1229–1230) |
| `memory.shared_world` | ✓ | ✓ | 003 (L1289–1290) |
| `memory.intimacy_bridge_pending` | ✗ | ✗ | 004 (stub — no RLS) |
| `memory.kg_entities` | ✓ | ✓ | 007 (L1426–1427) |
| `memory.kg_edges` | ✓ | ✓ | 007 (L1429–1430) |

**Note:** P28's `intimacy_bridge_pending` stub (Migration 004) has no RLS. This is acceptable because:

1. It's a stub with no rows expected during P28
2. The comment at L1334 explicitly marks it as P30 work
3. RLS should be added when P30 implements the full bilateral consent flow

### Finding (Non-Blocking)

P27's plan includes RLS on `intimacy_bridge_pending` (L1345–1346, L1349–1354). P28's stub omits it. Document this as a P30 task: "Add RLS + FORCE to `memory.intimacy_bridge_pending` when implementing bilateral consent flow."

---

## Check 7: New Schema Inconsistencies Introduced by Edits

**Verdict: FAIL — 1 bug found, 1 additional inconsistency**

### Bug: `shared_world.retrievability` in P28 Blueprint

**P27 Plan (L1287–1290):**
```sql
retrievability REAL GENERATED ALWAYS AS (
  exp(-1.0 * ((extract(epoch from now()) - extract(epoch from last_accessed_at))
          / NULLIF(stability::real * 86400, 0))) * importance_score
) STORED,
```

Uses `last_accessed_at` — correct.

**P28 Blueprint Migration 003 (L1258–1261):**
```sql
retrievability REAL GENERATED ALWAYS AS (
  exp(-1.0 * ((extract(epoch from now()) - extract(epoch from now()))
          / NULLIF(stability::real * 86400, 0))) * importance_score
) STORED,
```

Uses `now()` TWICE. The expression `extract(epoch from now()) - extract(epoch from now())` always equals 0, making `retrievability = exp(0) * importance_score = importance_score` — a **constant** that ignores the Ebbinghaus decay model entirely.

**Impact:** All `shared_world` rows would have `retrievability = importance_score` regardless of access recency. The decay sweep (P29) would never evict stale shared facts.

**Fix:** Change `extract(epoch from now())` to `extract(epoch from last_accessed_at)` in the second occurrence.

---

### Inconsistency: `kg_entities.created_by_agent` Constraint

As documented in Check 2, there's a schema inconsistency between P27 and P28 regarding `kg_entities.created_by_agent`:

| Aspect | P27 Plan | P28 Blueprint |
|---|---|---|
| Nullable | NOT NULL (after backfill) | Nullable |
| Sentinel | `'system'` | Not included |
| Backfill | `UPDATE ... SET created_by_agent = 'system'` | None |

This is the same finding as Check 2 but also qualifies as a schema inconsistency introduced by the P28 edits.

---

## Summary Table

| # | Check | Verdict | Finding |
|---|---|---|---|
| 1 | `shared_world` `created_by_agent NOT NULL` | **PASS** | Both docs agree; design note explains absence of `agent_id` |
| 2 | `kg_entities` `created_by_agent NOT NULL` | **FAIL** | P28 blueprint makes it nullable; P27 plan requires NOT NULL with backfill |
| 3 | `kg_edges` ADR-050 references | **PASS** | Correct references in both documents |
| 4 | P28 stub status documented | **PASS** | Frontmatter, §1.1, §1.2, migration comments all explicit |
| 5 | 3-scope model consistency | **PASS** | P28 implements 2/3 scopes; third explicitly deferred to P30 |
| 6 | RLS FORCE for all scopes | **PASS** | All implemented tables have RLS FORCE; `intimacy_bridge_pending` stub deferred to P30 |
| 7 | New schema inconsistencies | **FAIL** | Bug: `shared_world.retrievability` uses `now()` twice instead of `last_accessed_at` |

---

## Required Fixes (Blocking)

### Fix 1: P28 Blueprint Migration 003 — `shared_world.retrievability` Bug

**File:** `docs/setup-evidence/P27/plan/p28-dual-autonomous-hermes-blueprint.md`
**Location:** Migration 003, ~L1258–1261
**Change:**

```sql
-- BEFORE (broken):
retrievability REAL GENERATED ALWAYS AS (
  exp(-1.0 * ((extract(epoch from now()) - extract(epoch from now()))
          / NULLIF(stability::real * 86400, 0))) * importance_score
) STORED,

-- AFTER (correct):
retrievability REAL GENERATED ALWAYS AS (
  exp(-1.0 * ((extract(epoch from now()) - extract(epoch from last_accessed_at))
          / NULLIF(stability::real * 86400, 0))) * importance_score
) STORED,
```

### Fix 2: P28 Blueprint Migration 005 — `kg_entities.created_by_agent` NOT NULL

**File:** `docs/setup-evidence/P27/plan/p28-dual-autonomous-hermes-blueprint.md`
**Location:** Migration 005, ~L1348–1352
**Change:** Align with P27 plan — add backfill + NOT NULL + `'system'` sentinel:

```sql
-- BEFORE:
ALTER TABLE memory.kg_entities
  ADD COLUMN IF NOT EXISTS scope TEXT NOT NULL DEFAULT 'shared'
    CHECK (scope IN ('private', 'shared', 'relationship_private')),
  ADD COLUMN IF NOT EXISTS created_by_agent TEXT
    CHECK (created_by_agent IN ('guinevere', 'pharsa'));

-- AFTER:
ALTER TABLE memory.kg_entities
  ADD COLUMN IF NOT EXISTS scope TEXT NOT NULL DEFAULT 'shared'
    CHECK (scope IN ('private', 'shared', 'relationship_private')),
  ADD COLUMN IF NOT EXISTS created_by_agent TEXT
    CHECK (created_by_agent IN ('guinevere', 'pharsa', 'system'));

-- Backfill pre-existing ADR-050 rows
UPDATE memory.kg_entities SET created_by_agent = 'system' WHERE created_by_agent IS NULL;

-- Now safe to add NOT NULL
ALTER TABLE memory.kg_entities ALTER COLUMN created_by_agent SET NOT NULL;
```

---

## Auditor Gate

| Gate | Status |
|---|---|
| All 7 checks completed | ✓ |
| Findings documented with evidence | ✓ |
| Fixes proposed with exact file/line | ✓ |
| No false positives | ✓ |
| **Overall Verdict** | **NEEDS REVIEW** — 2 fixes required before PASS |

---

> **Footer:** Round 2 audit #02 — Memory Schema. Auditor: Guinevere. Date: 2026-06-28. Next action: apply Fix 1 and Fix 2, re-audit.
