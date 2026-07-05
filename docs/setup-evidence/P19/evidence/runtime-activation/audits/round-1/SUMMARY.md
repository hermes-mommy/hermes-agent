# P19 Runtime Activation — Audit Round 1 Summary

**Date:** 2026-06-27 13:10 WIB
**Author:** Guinevere (parent)

---

## Round 1 Results (4 dimensions)

| # | Dimension | Verdict | Findings |
|---|---|---|---|
| 1 | Runtime/P20 regression | NEEDS-REVIEW → fixed | RA-RT-10 doc imprecision (systemd dependency cascade) |
| 2 | Project-scoping correctness | PASS WITH FINDINGS (6/7) | RA-SC-04 INFO: adapter principal not project-scoped |
| 3 | DB/security/rollback | PASS (all) | 0 |
| 4 | Evidence/docs consistency | PASS (8/8) | 0 |

**0 CRITICAL, 0 HIGH, 0 MEDIUM.**

## Findings & Fixes

### RA-RT-10 (NEEDS-REVIEW → fixed): Documentation imprecision
- **Issue:** service-restart evidence claimed "only guinevere-core restarted" but live state showed discord/mcp share same ActiveEnterTimestamp.
- **Root cause:** systemd dependency cascade (`Requires=guinevere-core.service`).
- **Fix:** Updated evidence §6 to honestly document the cascade behavior.
- **Status:** ✅ FIXED

### RA-SC-04 (PASS/INFO): Memory adapter principal not project-scoped
- **Issue:** `MemoryRecallAdapter.recall()` scopes principal to `"project:{project_id}"` when context has project_id, but the live graph state doesn't propagate project_id from the decision context, so adapter falls back to `"guinevere_core"`.
- **Classification:** INFO severity — not a data leak (single project), not a blocker for runtime-active status. Deeper P19 wiring gap (project_id in graph state propagation).
- **Status:** Documented, not fixed (requires graph state plumbing, separate work item).

## Footer

| Field | Value |
|---|---|
| Round 1 verdict | PASS (4/4 dimensions clear) |
| Fixed findings | 1 (RA-RT-10) |
| Documented gaps | 1 (RA-SC-04 INFO) |
| Next step | Round 2 re-audit |