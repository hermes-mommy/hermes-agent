---
title: "P27 Round 2 — Blueprint Bugs Audit"
date: "2026-06-28"
agent: "Sisyphus-Junior (sub-agent executor)"
scope: "Audit of 4 remaining blueprint bugs from Phase 7 fix log (F-01 through F-04)"
file_audited: "docs/setup-evidence/P27/plan/p28-dual-autonomous-hermes-blueprint.md"
audit_type: "targeted bug classification + regression check"
---

# Blueprint Bugs Audit (Round 2, Auditor 05)

## Summary

This audit classifies the 4 remaining blueprint bugs identified by auditor 13-impl-feasibility during round 1. All 4 are **DEFINITION issues** — errors in the blueprint document itself that should be fixed before P28 implementation begins. None are deferred implementation concerns. The implementation guidance note added in Fix 7 does NOT cover these specific bugs (it addresses only general inference gaps).

**Verdict: FAIL — 4 DEFINITION bugs require blueprint fixes before P28 implementation.**

---

## Bug Classification

### F-01: `society_app.py` Phantom Reference

| Field | Value |
|---|---|
| **Location** | Blueprint §3.5 Step 5, L1012 and L1032 |
| **Bug** | Pharsa's `ExecStart=` references `src.core.society_app:app` but no `society_app.py` file exists in `src/core/`. Only `src/core/main.py` exists (confirmed via glob). |
| **Classification** | **DEFINITION issue** |
| **Severity** | HIGH — Pharsa's systemd service will fail to start (`ModuleNotFoundError: No module named 'src.core.society_app'`) |
| **Root Cause** | The blueprint assumes a separate FastAPI entrypoint for Pharsa but never defines the file or specifies that it should be created as a Step 5 deliverable. The `Files to create` list in §2.6 does not include `src/core/society_app.py`. |
| **Fix Options** | (A) Add `src/core/society_app.py` to the Step 5 `Files to create` list with a spec for what it should contain (Pharsa-specific FastAPI app with society manifest loading, different port, different env vars). (B) Change `ExecStart` to reuse `src.core.main:app` with Pharsa-specific env vars distinguishing the instance (simpler but requires `main.py` to support multi-instance config). |
| **Recommended Fix** | Option A — create a dedicated `society_app.py` that loads the society manifest, selects the Pharsa config, and starts the Pharsa-specific FastAPI app. This preserves clean separation. Add `src/core/society_app.py` to §2.6 Files to create and add a Sub-step 5C with the file's purpose and skeleton. |
| **Fixable Now?** | YES — blueprint-only change (add file spec + skeleton) |

---

### F-02: `shared_world.retrievability` Formula Bug

| Field | Value |
|---|---|
| **Location** | Blueprint §3.6 Step 6, Migration 003, L1258-1261 |
| **Bug** | The `retrievability` generated column in `memory.shared_world` uses `extract(epoch from now()) - extract(epoch from now())` which always evaluates to `0`, making `exp(0) * importance_score = importance_score`. The column never decays. |
| **Correct Formula** | Should be `extract(epoch from now()) - extract(epoch from last_accessed_at)` (matching the `private_agents` formula at L1203-1206). The `last_accessed_at` column EXISTS on `shared_world` (L1262) but is not used in the formula. |
| **Classification** | **DEFINITION issue** |
| **Severity** | MEDIUM — `shared_world` entries would never decay, meaning stale shared facts accumulate indefinitely. P28 uses static defaults (no nightly sweep), so the generated column is semantically wrong but won't crash at runtime. However, it creates a misleading schema that will confuse P30 implementers. |
| **Root Cause** | Copy-paste error from `private_agents` DDL. The second `now()` should be `last_accessed_at`. |
| **Fix** | Change L1259 from `extract(epoch from now())` (second occurrence) to `extract(epoch from last_accessed_at)`. |
| **Fixable Now?** | YES — single-line DDL fix |

---

### F-03: `hpp_outbox`/`hpp_inbox` DDL Missing

| Field | Value |
|---|---|
| **Location** | Blueprint §2.4 L134-135 (lists tables as P28 creates), Step 8 (L1554-1649), Step 9 (L1653-1700), §11.2 Rollback (L2732-2733) |
| **Bug** | The blueprint lists `hpp_outbox` (Step 8) and `hpp_inbox` (Step 9) as tables P28 creates, and the rollback script references `DROP TABLE IF EXISTS hpp_inbox/hpp_outbox`, but NO migration file (001-007) contains CREATE TABLE DDL for either table. The file list in §2.6 shows 7 migrations (001-007) — no 008/009. |
| **Classification** | **DEFINITION issue** |
| **Severity** | HIGH — Implementer must invent the DDL. Step 8 describes the outbox *pattern* conceptually but provides no schema. Step 9 describes the inbox dedup pattern but provides no schema. The rollback script assumes the tables exist. |
| **Root Cause** | The blueprint was written at architecture level and Step 6 (migrations) was scoped for memory tables only. The HPP outbox/inbox tables were described in Steps 8/9 but their DDL was never added to the migrations sequence. |
| **Fix** | Add `migrations/p28/008_hpp_outbox.sql` and `migrations/p28/009_hpp_inbox.sql` to: (1) §2.6 Files to create, (2) Step 6 migration file list, (3) Step 8/9 with inline DDL or reference to the migration files. Minimal DDL spec: |
| **Fixable Now?** | YES — blueprint-only change (add DDL + file entries) |

**Suggested DDL for 008_hpp_outbox.sql:**

```sql
BEGIN;
CREATE TABLE hpp_outbox (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  idempotency_key UUID NOT NULL UNIQUE,
  sender_instance_id TEXT NOT NULL,
  receiver_instance_id TEXT NOT NULL,
  envelope_json JSONB NOT NULL,
  published BOOLEAN NOT NULL DEFAULT false,
  published_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX hpp_outbox_pending_idx ON hpp_outbox (published, created_at) WHERE NOT published;
COMMIT;
```

**Suggested DDL for 009_hpp_inbox.sql:**

```sql
BEGIN;
CREATE TABLE hpp_inbox (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  received_by TEXT NOT NULL,
  idempotency_key UUID NOT NULL,
  envelope_json JSONB NOT NULL,
  processed BOOLEAN NOT NULL DEFAULT false,
  received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (received_by, idempotency_key)
);
CREATE INDEX hpp_inbox_unprocessed_idx ON hpp_inbox (received_by, processed) WHERE NOT processed;
COMMIT;
```

---

### F-04: `_cascade_halt()` Logs But Does Not Halt Instances

| Field | Value |
|---|---|
| **Location** | Blueprint §3.4 Step 4, L871-880 |
| **Bug** | `_cascade_halt()` writes audit entries (`write_hard_stop_state`) for each instance but never calls `stop_all(graceful=False)` or `_stop_one()`. After cascade: (a) `_is_halted` flag is set (L865), (b) watcher loop exits, (c) BUT each instance's `brain`, `redis_client`, and `pg_pool` remain active. The HARD STOP "halts" the watcher but not the actual Hermes instances. |
| **Classification** | **DEFINITION issue** |
| **Severity** | HIGH — HARD STOP is a safety-critical invariant (AGENTS.md V-008). A HARD STOP that only writes audit rows but doesn't stop instances violates the safety contract. Acceptance criterion #10 says "halts both within 50ms." |
| **Root Cause** | `_cascade_halt` was designed as audit-only. `stop_all` exists (L882-893) and correctly calls `_stop_one` (brain.dispose + redis.close + pg_pool.close) but is never invoked from the cascade path. |
| **Fix** | Add `await self.stop_all(graceful=False)` as the last line of `_cascade_halt()`, after the audit writes. This ensures audit trail is written BEFORE instances are torn down. |
| **Test Impact** | The existing cascade test (L952-973) only checks `reg._is_halted` flag. It should ALSO verify instances are disposed (e.g., check `brain.disposed` flag or `redis_client.closed`). |
| **Fixable Now?** | YES — blueprint code change (add one line + update test) |

**Suggested fix (L871-880):**

```python
async def _cascade_halt(self) -> None:
    """Halt all instances atomically; flush audit."""
    for instance in self._instances.values():
        try:
            await instance.audit_writer.write_hard_stop_state(
                society_key=SOCIETY_HARD_STOP_KEY,
            )
        except Exception as e:
            logger.exception("cascade_halt.instance_failed",
                             extra={"instance_id": instance.instance_id, "err": str(e)})
    # Actually halt all instances (not just audit)
    await self.stop_all(graceful=False)
```

---

## Implementation Guidance Note Coverage

The implementation guidance note added in Fix 7 (L278) states:

> "Some P28 implementation steps require minor inference from the implementer. The blueprint provides architecture-level guidance, not line-by-line code. Implementers should refer to the research files in `docs/setup-evidence/P27/research/` for detailed patterns."

**Assessment:** This note does NOT cover F-01 through F-04. These are not "minor inference" gaps — they are concrete errors:

- F-01 is a missing file that will cause a runtime crash.
- F-02 is a mathematical error in DDL.
- F-03 is missing DDL entirely for 2 tables.
- F-04 is a logic error in safety-critical code.

The guidance note is appropriate for its intended scope (general architecture-level guidance) but should NOT be used to justify leaving these 4 bugs unfixed. Each requires a specific blueprint correction.

---

## Regression Check (Phase 7 Edits)

Phase 7 made 3 edits to the blueprint:

| Edit | Location | Regression Risk |
|---|---|---|
| Fix 7: Implementation guidance note | L278 (after §3 preamble) | NONE — additive blockquote, no code/DDL changed |
| Fix 4: `idempotency_key` field | L2109 (§5.1 envelope schema) | NONE — additive field, consistent with outbox/inbox dedup pattern |
| Fix 4: P28 envelope simplification note | After L2106 (§5.1 post-schema) | NONE — clarification note only |

**Assessment:** No regressions introduced by Phase 7 edits. All 3 changes are additive (new content, no modifications to existing code/DDL).

---

## Findings Summary

| Bug | Classification | Severity | Fixable Now? | Fix Complexity |
|---|---|---|---|---|
| F-01: `society_app.py` phantom | DEFINITION | HIGH | YES | Add file spec + skeleton to Step 5 |
| F-02: retrievability formula | DEFINITION | MEDIUM | YES | Single-line DDL fix |
| F-03: hpp_outbox/inbox DDL missing | DEFINITION | HIGH | YES | Add 2 migration files + DDL |
| F-04: cascade_halt doesn't halt | DEFINITION | HIGH | YES | Add 1 line + update test |

**All 4 bugs are blueprint-definition issues.** None should be deferred to P28 implementation. Fixing them now prevents:
- F-01: Pharsa service crash on first boot
- F-02: Silent data model error confusing P30 implementers
- F-03: Implementer inventing DDL (inconsistency risk across instances)
- F-04: HARD STOP safety invariant violation (AGENTS.md V-008)

---

## Verdict

| Criterion | Result |
|---|---|
| All 4 bugs classified | PASS |
| Implementation guidance note assessed | PASS — does not cover these bugs |
| Regression check | PASS — no regressions from Phase 7 |
| Blueprint fixable without architecture change | PASS — all 4 are surgical fixes |
| **Overall** | **FAIL — 4 DEFINITION bugs require fixes before P28 implementation** |

---

## Recommended Fix Order

1. **F-04** (safety-critical) — HARD STOP cascade must actually halt instances
2. **F-01** (service crash) — Pharsa cannot start without `society_app.py` spec
3. **F-03** (missing DDL) — implementer cannot create tables without DDL
4. **F-02** (formula) — single-line fix, lowest urgency but highest ease

---

## Footer

| Field | Value |
|---|---|
| Date | 2026-06-28 |
| Agent | Sisyphus-Junior (sub-agent executor) |
| File audited | `p28-dual-autonomous-hermes-blueprint.md` (2925 lines) |
| Fix log referenced | `p27-round-1-fix-log.md` |
| Bugs audited | 4 (F-01 through F-04) |
| Regressions found | 0 |
| Next action | Apply blueprint fixes for F-01 through F-04; re-audit after fixes |
