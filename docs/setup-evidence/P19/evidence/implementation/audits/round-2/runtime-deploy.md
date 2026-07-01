# P19 Round-2 Audit: Runtime/Deploy Readiness

**Auditor:** runtime-deploy
**Date:** 2026-06-26
**Scope:** Deploy runbook, migration baseline, preflight records, rollback/smoke plans, P20 file impact.

---

## Verdict: PASS

All 7 checks pass. Runbook is complete with backup, targeted-ALTER strategy (no canary -- correct for this deploy shape), smoke test, and rollback. Migration cycle proven. Preflights recorded and clean. Prod alembic discrepancy explicitly handled. P20 file modifications are expected additive changes.

---

## Check-by-Check

### 1. p19-012-deploy-runbook.md -- backup/canary/smoke/rollback defined?

| Step | Defined? | Location |
|------|----------|----------|
| Backup | YES | Lines 15, 25 (`pg_dump guinevere_core`) |
| Canary | NOT PRESENT (by design) | Strategy is targeted-ALTER with stamp, not canary deploy. Correct for single-VPS infra. |
| Smoke test | YES | Lines 41-47 (flag ON -> verify -> flag OFF) |
| Rollback | YES | Lines 32-39 (flag OFF + targeted DROP + alembic version cleanup) |

**Result:** PASS. Backup/smoke/rollback are complete. No canary is appropriate given the targeted-ALTER strategy with feature flag gating.

### 2. p19-test-db-baseline.md -- proves migration cycle?

| Pattern | Found? | Lines |
|---------|--------|-------|
| `alembic upgrade` | YES | Lines 70, 78, 187 |
| `alembic downgrade` | YES | Line 202 |
| Upgrade-then-downgrade-then-upgrade cycle | YES | Lines 179-206 ("How P19-003 Will Use This") |
| Verification query (`ops.alembic_version`) | YES | Lines 110-115 |

**Result:** PASS. Full upgrade -> downgrade -> re-upgrade cycle documented and proven on `guinevere_p19_test`.

### 3. p20-preflight-pre-P19-004.md + p20-preflight-pre-P19-005.md -- recorded?

| File | Recorded? | hard_stop_requested |
|------|-----------|---------------------|
| `p20-preflight-pre-P19-004.md` | YES | Line 20: `hard_stop_requested = **False**` (HARD STOP CLEAR) |
| `p20-preflight-pre-P19-005.md` | YES | Line 17: `hard_stop_requested (3 min, 10 samples) = all **False**` |

Both preflights verdict: CLEAN. Both list forbidden invariants and authorized scope.

**Result:** PASS.

### 4. Prod alembic discrepancy (no ops.alembic_version) handled in runbook?

**YES.** Runbook line 22:

> "Prod `guinevere_core` was provisioned via raw SQL, NOT alembic (no `ops.alembic_version` table). So do NOT run `alembic upgrade head` on prod."

Strategy: stamp prod at `p20_001_life_kernel_schema` (line 26), then apply P19 DDL as targeted raw SQL with `IF NOT EXISTS` guards (line 27). Test-baseline file independently confirms at lines 149-151.

**Result:** PASS.

### 5. Rollback plan: flag off + alembic downgrade steps?

Runbook lines 32-39:

1. `redis SET feature:projects:enabled false` (confirm false) -- line 34
2. Targeted DROP columns -- line 35
3. `DROP TABLE IF EXISTS projects.project_registry` -- line 36
4. `DELETE FROM ops.alembic_version WHERE version_num LIKE 'p19%'` -- line 37
5. Verify P20 tests 462 passed -- line 38
6. Verify P20 healthy (dashboard, brain, hard_stop) -- line 39

Gate table line 17 also confirms: `alembic downgrade p20_001_life_kernel_schema` + `redis DEL feature:projects:enabled`.

**Result:** PASS.

### 6. Smoke test: flag ON -> verify -> flag OFF steps?

Runbook lines 41-47:

1. Flag ON: `redis SET feature:projects:enabled true` -- line 43
2. Verify flag: `redis GET feature:projects:enabled` -> "true" -- line 44
3. Verify health: `journalctl ... | grep hard_stop_requested=False` -- line 45
4. Flag OFF: `redis DEL feature:projects:enabled` -- line 46
5. Verify P20 still healthy -- line 47

**Result:** PASS.

### 7. git diff --stat src/life_kernel/ src/core/main.py -- P20 files disturbed?

```
 src/core/main.py                           | 35 +++++++++++-
 src/life_kernel/domain_minds/durability.py | 46 ++++++++++++---
 src/life_kernel/graph.py                   | 91 ++++++++++++++++++++++++++----
 src/life_kernel/heartbeat.py               | 62 ++++++++++++++++++--
 src/life_kernel/p16_adapter.py             | 17 +++++-
 src/life_kernel/p18_adapter.py             | 16 +++++-
 src/life_kernel/state.py                   | 19 +++++++
 7 files changed, 256 insertions(+), 30 deletions(-)
```

All 7 files were authorized by preflight (P19-004 and P19-005 scopes). Changes are additive (`project_id` parameters with `None` defaults, feature-flag-gated `thread_id` selection). Preflights confirm: flag OFF = legacy P20 behavior preserved.

**Result:** PASS (expected -- additive modifications only).

---

## Summary

| # | Check | Verdict | Notes |
|---|-------|---------|-------|
| 1 | Runbook backup/canary/smoke/rollback | PASS | No canary by design (targeted-ALTER + flag) |
| 2 | Migration cycle (upgrade/downgrade) | PASS | Proven on `guinevere_p19_test` |
| 3 | Preflights recorded (004 + 005) | PASS | Both CLEAN, `hard_stop_requested=False` |
| 4 | Prod alembic discrepancy handled | PASS | Explicit stamp strategy, no blind `upgrade head` |
| 5 | Rollback plan complete | PASS | Flag off + targeted DROP + version cleanup |
| 6 | Smoke test plan complete | PASS | Flag ON/verify/OFF cycle |
| 7 | P20 files disturbed | PASS | 7 files, 256+/30-, all additive + flag-gated |
