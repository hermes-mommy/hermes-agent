# P23 Audit Round 1 — Database / Queue

> **Auditor:** Independent (subagent)  
> **Date:** 2026-06-25  
> **Dimension:** DATABASE / QUEUE  
> **Scope:** Durable queue design, audit log integrity, DB schema DDL, Redis key collision, column naming consistency, RBAC

---

## 1. Audit Scope

This audit verifies the database and queue architecture for P23 "Embodied Operations / Personal OS Action Layer" across six dimensions:

1. **Durable queue design**: Is PostgreSQL the source of truth? Is Redis DB0 BRPOPLPUSH pattern correct? Is idempotency key `UNIQUE(namespace, intent_hash)` enforced? Is at-least-once + idempotent side effects documented?
2. **Audit log integrity**: Is `audit.action_log` hash-chained with `event_hash = SHA256(payload + previous_hash)`? Is WORM enforced via `no_update_or_delete CHECK` + `REVOKE UPDATE/DELETE`? Does it mirror P22's `audit.integration_api_log`?
3. **DB schema soundness**: Are DDLs in section 32 correct? Is `down_revision = 'p20_001_life_kernel_schema'` the latest migration? Is the migration idempotent? Does it avoid touching P20 schema?
4. **Redis key collision**: Do P23 keys avoid collision with P20 (`life_kernel:*`) and Aizanta (DBs 10-15)? Is `life_kernel:hard_stop` owned by P20 (P23 reads only)?
5. **Column naming consistency**: Does the DDL match the plan's terminology for namespace columns?
6. **RBAC enforcement**: Is `guinevere_core` DB user non-superuser? Are `UPDATE/DELETE` revoked on audit tables?

**Ground truth sources:**
- `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md` (sections 7, 27, 32, 33)
- `docs/setup-evidence/P23/research/p23-rollback-idempotency-research.md` (sections 3.1, 3.2, 3.7)
- `docs/setup-evidence/P23/research/p23-security-secrets-consent-research.md` (section 3.8)
- `docs/setup-evidence/P22/plan/p22-life-integration-hub-plan.md` (lines 131-157, audit.integration_api_log DDL)
- `alembic/versions/p20_001_life_kernel_schema.py` (verified latest migration)
- ADR-030 (Redis DB assignments referenced in plan section 33)

---

## 2. Findings

### Finding 1: Durable Queue Design — PASS with Minor Clarification Needed

**Severity:** LOW (documentation precision)

**Location:** `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:497-517`, `docs/setup-evidence/P23/research/p23-rollback-idempotency-research.md:134-237`

**Finding:**
The durable queue design is sound:

✅ **PostgreSQL source of truth**: Section 7 (plan:140) and research §3.2.1 specify `p23.action_queue` table as the durable source of truth.

✅ **Redis DB0 BRPOPLPUSH**: Plan section 7 (plan:269-287) and research §3.2.2 correctly specify Redis DB0 hot queue with BRPOPLPUSH pattern for at-least-once delivery.

✅ **Idempotency key**: Plan section 32 DDL (plan:516) shows `UNIQUE (namespace, intent_hash)` constraint implemented as a partial unique index:
```sql
CREATE UNIQUE INDEX idx_action_queue_idempotency
    ON p23.action_queue (idempotency_key)
    WHERE status IN ('queued', 'scheduled', 'pre-flight', 'running')
      AND (dedup_until IS NULL OR dedup_until > now());
```

However, the DDL shows `idempotency_key` as a computed column (`namespace + ':' + intent_hash`) with a unique index on that column, rather than a direct UNIQUE constraint on `(namespace, intent_hash)` as two separate columns. The research §3.6 (research:416-421) clarifies this:
```
idempotency_key = namespace + ':' + intent_hash
```

This is **correct** but the plan should clarify that the uniqueness is enforced via a computed `idempotency_key` column, not a multi-column constraint.

✅ **At-least-once + idempotent**: Research §3.2.2 (research:269-287) documents BRPOPLPUSH at-least-once semantics. Research §3.4 and §3.6 (research:612-625, 442-453) document executor idempotency requirements per surface.

**Recommendation:** Add a note in plan section 32 DDL that the `idempotency_key` is a computed TEXT column (`namespace || ':' || intent_hash`) rather than a multi-column constraint, to clarify the implementation for future developers.

---

### Finding 2: Audit Log Integrity — PASS

**Severity:** N/A (compliant)

**Location:** `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:406-436`, `docs/setup-evidence/P22/plan/p22-life-integration-hub-plan.md:131-157`, `docs/setup-evidence/P23/research/p23-security-secrets-consent-research.md:196-237`

**Finding:**
The audit log design correctly mirrors P22's `audit.integration_api_log` pattern:

✅ **Hash-chaining**: Plan section 27 (plan:435) and security research §3.8 (security-research:230-237) specify:
```
event_hash = SHA256(canonical_payload + previous_hash)
```
This matches P22's pattern exactly (P22 plan:161-162).

✅ **WORM enforcement**: Plan section 27 DDL (plan:429-431) shows:
```sql
CONSTRAINT no_update_or_delete CHECK (false) NO INHERIT
REVOKE UPDATE, DELETE ON audit.action_log FROM guinevere_core;
GRANT INSERT, SELECT ON audit.action_log TO guinevere_core;
```
This exactly matches P22's DDL (P22 plan:152-156).

✅ **Schema mirroring**: The `audit.action_log` schema includes all required fields for action context:
- `event_id`, `sequence`, `occurred_at` (identity + ordering)
- `actor_type`, `actor_id` (who)
- `executor`, `surface`, `action_id`, `namespace` (what/where)
- `risk_tier`, `intent_hash`, `command_redacted` (classification + dedup)
- `outcome`, `artifact_path`, `rollback_state` (result + evidence)
- `previous_hash`, `event_hash` (chain integrity)

The schema is **appropriate for P23 action context** and follows the P22 audit pattern while adding P23-specific fields (`executor`, `surface`, `risk_tier`, `rollback_state`).

**Verdict:** The audit log design satisfies hard-rejection criterion #2 (actions must be auditable with hash-chained WORM trail).

---

### Finding 3: DB Schema DDL — PASS with Migration Verification Note

**Severity:** LOW (planning-phase caveat)

**Location:** `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:486-531`, `alembic/versions/p20_001_life_kernel_schema.py:1-149`

**Finding:**

✅ **DDL soundness**: The DDLs in plan section 32 are structurally sound:
- Creates new `p23` schema (plan:492)
- Creates `p23.action_queue` with proper constraints (plan:495-520)
- Creates indexes for query patterns (plan:518-520)
- Includes CHECK constraints for data integrity (plan:509-514)
- References `audit.action_log` for audit trail (plan:524)

✅ **down_revision correctness**: Plan section 32 (plan:489) specifies:
```python
down_revision = 'p20_001_life_kernel_schema'
```
Verified that `alembic/versions/p20_001_life_kernel_schema.py` exists with `revision = 'p20_001_life_kernel_schema'` and `down_revision = 'p5_024'`. This means P23's migration would be the next in the chain — **CORRECT**.

✅ **P20 schema non-interference**: The DDLs create a new `p23` schema and do not touch existing `life_kernel` schema tables. Plan section 18 (plan:280-286) explicitly states P20 changes are "ADDITIVE only" with a list of LOCKED P20 files that P23 MUST NOT modify.

⚠️ **Migration idempotency caveat**: Plan section 32 (plan:531) states:
```
Migration idempotent: `alembic upgrade head` + `alembic downgrade -1` + `alembic upgrade head` to exit 0 (§2.11).
```
However, no actual migration file exists yet (this is the planning phase per plan:3). The idempotency requirement is **documented** but cannot be verified until P23-003 implementation wave creates the actual `alembic/versions/p23_001_action_layer.py` file.

**Recommendation:** During P23-003 implementation, ensure the upgrade/downgrade functions handle `CREATE SCHEMA IF NOT EXISTS` and `DROP SCHEMA IF EXISTS` idempotently, and test the upgrade→downgrade→upgrade cycle as specified.

---

### Finding 4: Redis Key Collision — PASS

**Severity:** N/A (compliant)

**Location:** `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:534-549`, `src/life_kernel/redis_client.py:1-120`

**Finding:**

✅ **P23 key prefix isolation**: Plan section 33 (plan:537-547) shows all P23 keys use `p23:` prefix:
- `p23:queue:pending`, `p23:queue:processing` (DB0)
- `p23:cancel` (pub/sub, DB0)
- `p23:action:{action_id}:state` (DB3)
- `p23:executor:{name}:health` (DB3)
- `feature:p23:{executor}` (DB5)
- `p23:ratelimit:{executor}` (DB5)
- `cost:by_model:p23:*` (DB5)

No collision with P20's `life_kernel:*` prefix (verified in `src/life_kernel/redis_client.py:24` which uses `WORLD_STATE_KEY_PREFIX = "life_kernel:world:"`).

✅ **life_kernel:hard_stop ownership**: Plan section 33 (plan:546) explicitly states:
```
`life_kernel:hard_stop` (P20's DB) — HARD-STOP flag (P23 reads, does not own)
```
Plan section 25 (plan:366-374) and section 18 (plan:282) confirm P23 only **reads** this flag and never sets it (P20 `heartbeat.py` is the canonical setter).

✅ **Aizanta DB collision avoidance**: Plan section 33 (plan:548) states:
```
No collision with P20 keys (`life_kernel:*`) or Aizanta (DBs 10-15).
```
P23 uses Redis DB0 (queue), DB3 (state), DB5 (cost/features) per plan section 33. Aizanta uses DBs 10-15 per IMPLEMENTATION_GUIDE.md §6 (cited in rollback research:39).

**Verdict:** Redis key namespace is properly isolated.

---

### Finding 5: Column Naming Inconsistency — MAJOR FINDING (Terminology Mismatch)

**Severity:** MEDIUM (documentation consistency / developer confusion)

**Location:** `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:119,292-299,497`, `docs/setup-evidence/P23/research/p23-rollback-idempotency-research.md:163`

**Finding:**
There is a **terminology inconsistency** between the plan's narrative and the DDL:

❌ **Plan narrative uses `project_namespace`**: 
- Plan section 19 title (plan:291): "P19 Project Namespace Wiring"
- Plan section 19 (plan:292): "every P23 action carries `project_namespace` (PG column, default `'default'`)"
- Plan architecture section 5 (plan:119): "Every action carries a P19 project_namespace"
- Plan section 19 (plan:296): "Post-P19: `<project>:p23:<executor>:<surface>:<action-id>`. P19 owns the project registry; P23 reads read-only."

❌ **DDL uses just `namespace`**:
- Plan section 32 DDL (plan:497): `namespace       TEXT NOT NULL DEFAULT 'default',`
- Rollback research §3.2.1 DDL (research:163): `namespace           TEXT NOT NULL,`
- Security research §3.8 DDL (security-research:208): `namespace       TEXT NOT NULL DEFAULT 'default',`
- Plan section 27 audit.action_log DDL (plan:418): `namespace       TEXT NOT NULL DEFAULT 'default',`

This inconsistency was **explicitly flagged in the audit instructions** as something to check.

**Impact:**
- Developers reading the narrative will look for a column named `project_namespace` but find only `namespace` in the DDL
- Code references in plan section 19 use the term `project_namespace` but the actual column will be named `namespace`
- This creates a risk of confusion during P23-012 implementation (P19 namespace integration wave)

**Root cause:** The plan uses `project_namespace` to emphasize the P19 provenance of the concept, but the DDL uses the shorter `namespace` for SQL brevity.

**Recommendation:** 
1. **Option A (Preferred)**: Update all DDL occurrences to use `project_namespace` as the column name to match the plan narrative.
2. **Option B**: Update plan section 19 narrative to consistently use `namespace` and clarify that "project namespace" is the conceptual name while "namespace" is the column name.
3. **Option C**: Add an explicit note in section 32 DDL comments: `-- P19 project namespace (column named 'namespace' for SQL brevity)`

Choose Option A unless there's a strong reason for SQL brevity over documentation consistency.

---

### Finding 6: RBAC Enforcement — PASS

**Severity:** N/A (compliant)

**Location:** `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:429-432,529-530`, `docs/setup-evidence/P23/research/p23-security-secrets-consent-research.md:172-174`

**Finding:**

✅ **Non-superuser role**: Plan section 32 (plan:529) states:
```
No superuser: `guinevere_core` DB user (RBAC, ADR-018).
```
Security research §3.7 (security-research:172-174) confirms:
```
Application connects as `guinevere_core` PostgreSQL role, not superuser.
```

✅ **Audit table WORM enforcement**: Plan section 27 DDL (plan:431-432) shows:
```sql
REVOKE UPDATE, DELETE ON audit.action_log FROM guinevere_core;
GRANT INSERT, SELECT ON audit.action_log TO guinevere_core;
```

✅ **Action queue permissions**: Plan section 32 DDL (plan:533-534) shows:
```sql
REVOKE UPDATE, DELETE ON p23.action_queue FROM guinevere_core;
GRANT INSERT, SELECT ON p23.action_queue TO guinevere_core;
```
This enforces append-only semantics at the RBAC layer (status updates would require a stored procedure or trigger, as noted in the DDL comment at plan:535).

**Verdict:** RBAC is properly specified for WORM enforcement and least-privilege access.

---

## 3. Hard-Rejection Criteria Check

The audit instructions specified checking hard-rejection criteria #2 and #3:

### Hard-Rejection #2: "Action is not durable/auditable → FAIL"

**Status:** ✅ PASS

Evidence:
- PostgreSQL `p23.action_queue` provides durable storage (Finding 1)
- Hash-chained `audit.action_log` provides tamper-evident audit trail (Finding 2)
- WORM enforcement via CHECK constraint + RBAC (Finding 2, Finding 6)
- Plan section 45 (plan:726) explicitly states this as mitigated: "Durable queue PG+Redis; hash-chained audit; artifacts."

### Hard-Rejection #3: "Action queue lacks retry/backoff/cancel/rollback state → FAIL"

**Status:** ✅ PASS

Evidence:
- Retry/backoff: Research §3.3 documents exponential backoff + full jitter, max_retries per risk tier
- Cancel: Plan section 25 documents HARD STOP cancellation path; section 7 documents `p23:cancel` pub/sub channel
- Rollback state: Plan section 32 DDL includes `rollback_state JSONB` column (plan:511); research §3.4 documents per-executor rollback strategies
- Plan section 45 (plan:727) states this as mitigated: "Lifecycle state machine; rollback/idempotency; HARD-STOP cancel."

---

## 4. Verdict

**Overall Verdict:** ✅ **PASS with MINOR CORRECTIONS REQUIRED**

### Summary

The P23 database and queue architecture is **fundamentally sound** and satisfies all hard-rejection criteria:

**Strengths:**
1. Durable queue with PostgreSQL source of truth + Redis hot queue (BRPOPLPUSH) ✓
2. Idempotency key enforcement via computed column + partial unique index ✓
3. Hash-chained WORM audit log mirroring P22 pattern ✓
4. Proper down_revision chain (`p20_001_life_kernel_schema`) ✓
5. Redis key namespace isolation (no P20/Aizanta collision) ✓
6. RBAC enforcement (non-superuser, REVOKE UPDATE/DELETE) ✓

**Required Corrections (before P23-003 implementation):**

1. **MEDIUM Priority — Column Naming Consistency (Finding 5)**: Resolve the `project_namespace` vs `namespace` terminology mismatch. Recommend renaming DDL column to `project_namespace` to match the plan narrative, or add explicit documentation clarifying the naming choice.

**Minor Recommendations (nice-to-have):**

2. **LOW Priority — DDL Clarification (Finding 1)**: Add a comment in section 32 DDL explaining that `idempotency_key` is a computed column rather than a multi-column constraint.

3. **LOW Priority — Migration Verification (Finding 3)**: During P23-003 wave, verify upgrade→downgrade→upgrade idempotency as specified in plan section 32.

**No Blocking Issues:** All hard-rejection criteria (#2, #3) are satisfied. The architecture is ready for implementation pending the column naming resolution.

---

**Output Path:** `docs/setup-evidence/P23/evidence/audits/round-1/database-queue.md`  
**Audit Complete:** 2026-06-25  
**Key Finding:** Terminology inconsistency (`project_namespace` in narrative vs `namespace` in DDL) requires resolution before implementation.
