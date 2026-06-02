# D10 — Error Handling Re-Audit (P5.5 Remediation)

**Re-Audit Dimension:** Error Handling & Resilience
**Scope:** P5.5 fixes applied to cost.py, guardian.py, manager.py
**Date:** 2026-06-02
**Auditor:** Independent Re-Auditor (Read-Only)
**Verdict:** **PASS**

---

## Executive Summary

Re-audited 3 source files against 3 P5.5 remediation fixes addressing 4 original findings (F-C1, F-H2, F-H3, F-H1 + F-M1). **All 4 findings are RESOLVED.** All grep checks pass. Zero regression detected. No bare excepts introduced. All fixes follow proper error-handling patterns with `logger.error` (for recoverable errors), `logger.exception` (for diagnostics with stack trace), and exception isolation where needed.

---

## Per-Finding Verification

### FIX 3 (F-C1) — cost.py Redis Error Handling

| Item | Expected | Actual | Result |
|---|---|---|---|
| File line count | 235 (from 194) | 235 | ✅ |
| `RedisError` grep matches | ≥5 (1 import + 4 except) | 5 | ✅ |
| Import line | L14 | `from redis.exceptions import RedisError` | ✅ |
| Block 1: pipeline | try/except RedisError | Lines 86-114 | ✅ |
| Block 2: global tracker | try/except RedisError | Lines 117-131 | ✅ |
| Block 3: get_loop_cost | try/except RedisError | Lines 154-186 | ✅ |
| Block 4: get_all_loop_costs | try/except RedisError | Lines 214-227 | ✅ |

**Block-level analysis:**

1. **`record_loop_cost()` pipeline block (L86-114):** Try wraps `pipe.execute()` and `float(self.redis.get(...))`. Except logs `"loop_cost.record_failed"` and returns `0.0`. Safe degradation — cost data loss is logged but doesn't propagate.

2. **Global CostTracker block (L117-131):** Separate try/except for `self._global_tracker.record_cost(...)`. Failure is logged as `"loop_cost.global_record_failed"` but does NOT prevent the method from returning the correct per-loop total. Executes after the per-loop pipeline, so per-loop data is preserved even if global tracking fails.

3. **`get_loop_cost()` block (L154-186):** Try wraps `redis.get()`, `redis.hget()`, `redis.scan_iter()`. Except logs `"loop_cost.fetch_failed"` and returns a complete safe default dict (`total_cost: 0.0, by_model: {}`). Clean degradation.

4. **`get_all_loop_costs()` block (L214-227):** Try wraps `redis.smembers()` and per-loop `redis.get()`. Except logs `"loop_cost.fetch_all_failed"` and returns `{}`. Clean degradation.

**Block isolation quality:** Excellent. The per-loop pipeline (block 1) and global tracker (block 2) are isolated — a global tracker failure doesn't lose per-loop data. Read methods (blocks 3, 4) return safe defaults rather than propagating exceptions.

**Verdict: RESOLVED.**

---

### FIX 5 (F-H2) — guardian.py monitor() Exception Handling

| Item | Expected | Actual | Result |
|---|---|---|---|
| monitor() while-body in try/except | try at L137, except at L169 | Lines 137-173 | ✅ |
| `logger.exception` on monitor error | Yes, includes stack trace | Lines 170-173 | ✅ |
| Sleep still executes after error | `await asyncio.sleep` outside try | Line 175 (outside except block) | ✅ |

**Detailed analysis:**

The `monitor()` method (L128-177) now has the following structure:
```
while self._running:
    try:
        # all heartbeat/phase-advance/resource checks (L138-168)
        # inner kill_loop calls with per-call try/except (L164-168)
    except Exception:
        logger.exception("guardian.monitor_error", ...)
    await asyncio.sleep(self.HEARTBEAT_INTERVAL)
```

Key design decisions verified:
- **Sleep outside try/except**: Ensures the monitor always sleeps between ticks even if an exception occurs, preventing tight error loops.
- **`_running` flag not reset**: The loop continues on error — the watchdog doesn't die on transient failures. A permanent failure (e.g., corrupted data structure) will keep erroring but won't crash the asyncio task.
- **`logger.exception`**: Auto-includes `exc_info=True` — stack trace available for debugging.

**Verdict: RESOLVED.**

---

### FIX 5 (F-H3) — guardian.py kill_loop() Exception Isolation

| Item | Expected | Actual | Result |
|---|---|---|---|
| `state_machine.fail()` isolated | Individual try/except | Lines 112-115 | ✅ |
| `cancel_cb()` isolated | Individual try/except | Lines 120-123 | ✅ |
| Per-loop kill isolation in monitor() | Each kill_loop in try/except | Lines 165-168 | ✅ |
| `logger.exception` on all failure paths | Yes | Lines 115, 123, 168 | ✅ |

**Kill chain analysis:**

```
kill_loop() called from monitor() [per-loop try/except: L165-168]
  ├─ state_machine.fail(reason)  [individual try/except: L112-115]
  │    └─ on failure: logger.exception("guardian.state_fail_failed") — continues ↓
  ├─ cancel_cb()                 [individual try/except: L120-123]
  │    └─ on failure: logger.exception("guardian.cancel_callback_failed") — continues ↓
  ├─ unregister_loop(loop_id)    [no try/except; safe — dict.pop with default]
  └─ logger.warning("loop_killed")
```

All 3 failure points have independent exception handling:
1. `state_machine.fail()` failure → logged + continues to callback
2. `cancel_callback()` failure → logged + continues to unregister
3. `kill_loop()` itself in monitor → logged per-loop + continues to next stale loop

**Verdict: RESOLVED.**

---

### FIX 9 (F-H1 + F-M1) — manager.py Stack Traces

| Item | Expected | Actual | Result |
|---|---|---|---|
| `logger.error` in manager.py | 0 matches | 0 matches | ✅ |
| `logger.exception` in manager.py | ≥2 matches | 2 matches (L216, L228) | ✅ |
| Main except (F-H1) uses `logger.exception` | Yes | Line 216 | ✅ |
| Inner except (F-M1) uses `logger.exception` | Yes | Line 228 | ✅ |

**Before/after comparison:**

| Location | Before (P5) | After (P5.5) |
|---|---|---|
| `_run_loop` main except (L214-222) | `logger.error("loop_manager.loop_failed", ... error=reason)` | `logger.exception("loop_manager.loop_failed", ... error=reason)` |
| `_run_loop` inner except (L227-232) | `logger.error("loop_manager.final_report_failed", ... error=str(report_exc))` | `logger.exception("loop_manager.final_report_failed", ... error=str(report_exc))` |

Both now include `exc_info=True` via `logger.exception()`, providing full traceback for root cause analysis.

**Verdict: RESOLVED.**

---

## Grep Verification Results

| # | Check | Command | Expected | Actual | Result |
|---|---|---|---|---|---|
| 1 | RedisError in cost.py | `grep RedisError cost.py` | ≥5 matches | 5 matches | ✅ PASS |
| 2 | logger.error in manager.py | `grep logger\\.error manager.py` | 0 matches | 0 matches | ✅ PASS |
| 3 | logger.exception in manager.py | `grep logger\\.exception manager.py` | ≥2 matches | 2 matches | ✅ PASS |
| 4 | monitor() try/except | File read inspection | while body wrapped | Lines 137-173 | ✅ PASS |
| 5 | kill_loop() isolation | File read inspection | 3 individual blocks | L112-115, L120-123, L165-168 | ✅ PASS |
| 6 | Bare except: in src/loops/ | `grep except\\s*:` | 0 matches | 0 matches | ✅ PASS |

**All 6 checks PASS.**

---

## Regression Check

No regression detected. All 3 files maintain functional equivalence:

- **cost.py**: Methods still return the same types and semantics; failures now return safe defaults instead of crashing.
- **guardian.py**: `monitor()` loop logic unchanged; `kill_loop()` execution order unchanged — only exception handling added.
- **manager.py**: `_run_loop` behavior unchanged; only logging method changed from `logger.error` to `logger.exception`. The `error=reason` parameter is preserved (added to `logger.exception` call alongside auto-traceback).

---

## Remaining Unaddressed Findings (Not in P5.5 Scope)

The following findings from the original D10 audit were NOT part of P5.5 remediation. They remain unresolved and require future attention:

| ID | Severity | File | Description |
|---|---|---|---|
| F-H4 | **HIGH** | evidence.py | All evidence I/O has zero exception handling. Disk/permission failures kill loop phases. |
| F-M2 | MEDIUM | enforcer.py | `enforce()` has no exception handling. Single error kills entire enforcement pass. |
| F-M3 | MEDIUM | cost.py | Unprotected `float()` conversion on Redis values — `ValueError` risk (non-RedisError, not caught by current handlers). |
| F-M4 | MEDIUM | scheduler.py | `_trigger_loop` uses `logger.error(str(exc))` — no stack trace. |
| F-M5 | MEDIUM | routes.py | No exception handling in API endpoints. Stubs mask the gap. |
| F-L1 | LOW | enforcer.py | No error-level logging for edge cases. |
| F-L2 | LOW | sub_agent.py | No exception handling (low-risk, acceptable). |
| F-L3 | LOW | contract.py | No exception handling (pure data module, acceptable). |

**Note on F-M3 (cost.py float()):** The `float()` call at L107 (`float(self.redis.get(loop_key) or 0)`) is now inside the `try/except RedisError` block (L86-114). However, `ValueError` is not a subclass of `RedisError`. If Redis returns a non-numeric string (data corruption), `float()` will raise `ValueError` which will NOT be caught by `except RedisError`. This remains unhandled. Same applies to float/int conversions at L156, L160-161, L171, L221 inside their respective RedisError blocks.

---

## Evidence Artifacts

| Artifact | Path | Status |
|---|---|---|
| Source: cost.py | `src/loops/cost.py` (235 lines) | Read + verified |
| Source: guardian.py | `src/loops/guardian.py` (189 lines) | Read + verified |
| Source: manager.py | `src/loops/manager.py` (272 lines) | Read + verified |
| Original audit | `audit-reports/P5/P5-FINAL-AUDIT/D10-error-handling.md` | Read + cross-referenced |
| Re-audit report | `audit-reports/P5/P5-FINAL-AUDIT/D10-re-audit.md` | This file |

---

## Conclusion

**All 4 P5.5-targeted findings are RESOLVED.** The 3 fixes are correctly implemented with proper error-handling patterns:

- **FIX 3**: cost.py now has 4 independent `try/except RedisError` blocks with structured logging and safe defaults.
- **FIX 5**: guardian.py `monitor()` has top-level exception safety, and `kill_loop()` has per-operation + per-loop exception isolation.
- **FIX 9**: manager.py replaced all `logger.error` with `logger.exception`, ensuring stack traces in production logs.

Zero bare excepts. Zero type suppression. Zero regression. All grep checks pass.

**Re-Audit Verdict: PASS.**

---

_Re-audit complete. No source code was modified. 8 medium/low findings remain for future iteration._