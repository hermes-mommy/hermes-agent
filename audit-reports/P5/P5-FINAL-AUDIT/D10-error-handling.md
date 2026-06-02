# D10 — Error Handling & Resilience Audit

**Audit Dimension:** Error Handling & Resilience
**Scope:** P5 Agent Loop — all 13 source files
**Date:** 2026-06-02
**Auditor:** Independent Resilience Auditor
**Verdict:** **NEEDS REVIEW**

---

## Executive Summary

Audited all try/except blocks, exception logging patterns, CancelledError handling, and resilience mechanisms across 13 P5 files. Found **1 CRITICAL**, **4 HIGH**, **5 MEDIUM**, and **3 LOW** findings. The most severe issue is **cost.py having zero Redis error handling** across all operations, risking cost data loss and unhandled propagation. The guardian watchdog monitor has no exception safety net, meaning a single transient failure kills the watchdog silently. Discord commands and hash_anchor.py demonstrate excellent error handling patterns.

| Severity | Count | Summary |
|---|---|---|
| CRITICAL | 1 | cost.py — zero Redis error handling |
| HIGH | 4 | guardian monitor, kill_loop, manager _run_loop logging, evidence I/O |
| MEDIUM | 5 | scheduler logging, manager inner except, cost float(), routes endpoints, enforcer |
| LOW | 3 | sub_agent, contract, enforcer logging |

---

## File-by-File Analysis

### 1. `src/loops/manager.py` (272 lines)

**try/except blocks found:** 6

| Location | Pattern | Logged | Re-raised | Verdict |
|---|---|---|---|---|
| L117-120 `stop_loop` CancelledError | `except asyncio.CancelledError: pass` | N/A (intentional cancel) | N/A | PASS |
| L211-213 `_run_loop` CancelledError | `except asyncio.CancelledError: logger.info; raise` | YES (info) | YES | PASS |
| L214-222 `_run_loop` main except | `except Exception as exc: logger.error(... error=str(exc))` | PARTIAL | NO (handled) | **FINDING F-H1** |
| L227-232 `_run_loop` inner except | `except Exception as report_exc: logger.error(... str(report_exc))` | PARTIAL | NO (handled) | **FINDING F-M1** |
| L252-253 `main` service stop | `except (KeyboardInterrupt, CancelledError)` | YES | implicit | PASS |
| L258-261 `main` guardian cancel | `except asyncio.CancelledError: pass` | N/A (intentional) | N/A | PASS |

**Specific checks:**
- **Check 7 (Q7): manager.py _run_loop exception handler** — Does call `state.fail(reason)` (L222). Does attempt partial evidence report (L225-226). Inner except also logs (L228-232). `finally` block ensures `guardian.unregister_loop` cleanup (L234). **Structured resilience is correct.** The only gap is `logger.error` instead of `logger.exception` — no stack trace in logs.
- **Check 8 (Q8): manager.py start_loop exception handler** — `start_loop()` (L50-89) has NO try/except. If `asyncio.create_task()` or `state.set_status()` raises, the exception propagates to the caller. The loop state is already registered in `active_loops` and `evidence_pipelines` before the task starts, so partial state could leak. LOW risk — `create_task` rarely fails.

**Finding F-H1 — HIGH: `_run_loop` main except uses `logger.error` without stack trace**
- Location: L216-222
- Issue: Uses `logger.error("loop_manager.loop_failed", ... error=reason)` where `reason = f"{type(exc).__name__}: {exc}"`. This captures the exception type and message but NOT the traceback. When a phase handler crashes deep inside an LLM call, the stack trace is essential for debugging.
- Impact: Degraded debugging — operator cannot determine root cause from logs alone.
- Fix: Replace `logger.error(...)` with `logger.exception("loop_manager.loop_failed", ...)` to auto-include `exc_info=True`.

**Finding F-M1 — MEDIUM: `_run_loop` inner except missing stack trace**
- Location: L228-232
- Issue: `logger.error("loop_manager.final_report_failed", ... error=str(report_exc))` — no stack trace for partial report failure.
- Impact: Cannot debug why evidence report generation failed.
- Fix: Use `logger.exception(...)` instead.

---

### 2. `src/loops/guardian.py` (157 lines)

**try/except blocks found:** 1

| Location | Pattern | Logged | Re-raised | Verdict |
|---|---|---|---|---|
| L153-156 `stop` CancelledError | `except asyncio.CancelledError: pass` | N/A | N/A | PASS |

**Specific checks:**
- **Check 9 (Q9): guardian.py monitor exception handling on kill** — `kill_loop()` (L95-103) has NO try/except. If `unregister_loop()` or `logger.error()` raises, the exception propagates to the caller in `monitor()`.

**Finding F-H2 — HIGH: `monitor()` has NO exception handling around loop body**
- Location: L105-145 (entire `while self._running` body)
- Issue: The monitor loop iterates over all active loops, computes time deltas, checks heartbeats, and calls `kill_loop`. There is NO try/except wrapping any of this logic. If any single operation raises (e.g., a dict access on a loop that was concurrently unregistered, a `total_seconds()` calculation on a None value, or an `asyncio.sleep` interrupted), the entire monitor coroutine dies. The `_running` flag is never reset. No cleanup. No recovery. The watchdog is dead and no one knows.
- Impact: Watchdog silently dies → stuck loops go undetected → resource leaks, hung agents.
- Fix: Wrap the inner loop body in `try/except Exception`, log the error, and continue the while loop.

**Finding F-H3 — HIGH: `kill_loop()` cascading failure**
- Location: L140-141 (`for loop_id, reason in stale_loops: await self.kill_loop(...)`)
- Issue: If `kill_loop()` raises for one loop (e.g., due to `unregister_loop` failing), the remaining stale loops in the `stale_loops` list are never processed. One bad loop prevents cleanup of all others.
- Impact: Multiple stuck loops remain alive because one kill attempt failed.
- Fix: Wrap each `kill_loop()` call in its own try/except inside the for loop.

---

### 3. `src/loops/enforcer.py` (132 lines)

**try/except blocks found:** 0

**Finding F-M2 — MEDIUM: `enforce()` has no exception handling**
- Location: L96-132
- Issue: The `enforce()` method iterates all tracked agents, computes idle times, and mutates state. No try/except wraps this logic. If `datetime.now(timezone.utc)` or any dict operation raises, the entire enforcement pass fails uncaught.
- Impact: Enforcement pass silently skipped — idle agents remain untracked.
- Fix: Add try/except around the enforcement loop body with `logger.error` + continue.

**Finding F-L1 — LOW: No error logging anywhere in module**
- All log calls are for normal operations (info, warning, debug). No error-level logging for edge cases.

---

### 4. `src/loops/hash_anchor.py` (121 lines)

**try/except blocks found:** 3

| Location | Pattern | Logged | Re-raised | Verdict |
|---|---|---|---|---|
| L76-81 `validate_edit_content` IndexError | `except IndexError: logger.error; return False` | YES (error) | NO (safe return) | PASS |
| L110-113 `validate_edit` FileNotFoundError | `except FileNotFoundError: logger.error; return False` | YES (error) | NO (safe return) | PASS |
| L115-119 `validate_edit` OSError | `except OSError: logger.error; return False` | YES (error) | NO (safe return) | PASS |

**Verdict: CLEAN.** All exceptions properly caught, logged at error level, and converted to safe return values. No findings.

---

### 5. `src/loops/sub_agent.py` (128 lines)

**try/except blocks found:** 0

**Finding F-L2 — LOW: No exception handling**
- Location: Entire module
- Issue: No try/except in `spawn()`, `mark_complete()`, `mark_failed()`. If `uuid4()` or `datetime.now()` raises, exceptions propagate uncaught.
- Impact: Minimal — these are straightforward operations with very low failure probability.
- Fix: Optional — wrap with defensive try/except if this module gains complexity.

---

### 6. `src/loops/contract.py` (130 lines)

**try/except blocks found:** 0

**Finding F-L3 — LOW: No exception handling**
- Location: Entire module
- Issue: Pure data construction module. Relies on Pydantic for validation. No internal exception handling needed for its purpose.
- Impact: Minimal — Pydantic raises clear validation errors.
- Verdict: Acceptable for a pure data module.

---

### 7. `src/loops/verify.py` (183 lines)

**try/except blocks found:** 2

| Location | Pattern | Logged | Re-raised | Verdict |
|---|---|---|---|---|
| L121-128 `verify_command` TimeoutExpired | `except subprocess.TimeoutExpired: logger.error` | YES (error) | NO (safe result) | PASS |
| L129-136 `verify_command` OSError | `except OSError: logger.error` | YES (error) | NO (safe result) | PASS |

**Specific checks:**
- **Check 11 (Q11): verify.py command execution exception handling** — Both `TimeoutExpired` and `OSError` are caught, logged at error level, and converted to safe result dicts with `passed=False`. The 30-second timeout prevents infinite hangs. CLEAN.

**Verdict: CLEAN.** Command execution has proper timeout and OS error handling.

---

### 8. `src/loops/cost.py` (194 lines)

**try/except blocks found:** 0

**Specific checks:**
- **Check 12 (Q12): cost.py Redis connection failure handling** — NONE. Zero exception handling across all methods.

**Finding F-C1 — CRITICAL: Zero Redis error handling**
- Location: `record_loop_cost()` (L55-123), `get_loop_cost()` (L125-169), `get_all_loop_costs()` (L171-194)
- Issue: All Redis operations — `pipeline.execute()`, `redis.get()`, `redis.hget()`, `redis.scan_iter()`, `redis.smembers()`, `redis.incrbyfloat()` — have NO try/except. Redis can raise `ConnectionError`, `TimeoutError`, `AuthenticationError`, `BusyLoadingError`, `ReadOnlyError`, and `RedisError` at any point.
- Impact:
  - **Data loss**: If Redis is down during `record_loop_cost()`, cost data is lost and the exception propagates to the caller (likely `_run_loop` phase handler), potentially failing the entire loop for a transient infrastructure issue.
  - **Crash propagation**: `get_loop_cost()` called from a status endpoint would crash the endpoint.
  - **Silent accounting gap**: No retry, no fallback, no degradation.
- Fix: Wrap all Redis operations in `try/except redis.RedisError`, log the error, and either re-raise (for `record_loop_cost` where accuracy matters) or return a safe default (for reads).

**Finding F-M3 — MEDIUM: Unprotected `float()` conversion**
- Location: L113 (`float(self.redis.get(loop_key) or 0)`)
- Issue: If Redis returns a non-numeric string (data corruption, manual key tampering), `float()` raises `ValueError`. No protection.
- Impact: Uncaught ValueError propagates to caller.
- Fix: Use `try/except ValueError` or validate before conversion.

---

### 9. `src/loops/scheduler.py` (175 lines)

**try/except blocks found:** 3

| Location | Pattern | Logged | Re-raised | Verdict |
|---|---|---|---|---|
| L81-87 `remove_job` | `except Exception: logger.warning; raise` | YES (warning) | YES | PASS |
| L149-154 `_trigger_loop` | `except Exception: logger.error(str(exc))` | PARTIAL | NO (swallowed) | **FINDING F-M4** |
| L167-168 `main` service stop | `except (KeyboardInterrupt, CancelledError)` | YES | implicit | PASS |

**Finding F-M4 — MEDIUM: `_trigger_loop` missing stack trace**
- Location: L149-154
- Issue: `logger.error("loop_scheduler.trigger_failed", ... error=str(exc))` — only captures exception message string, not the traceback. When a scheduled loop trigger fails (e.g., due to Redis connection error from manager initialization), the root cause is lost.
- Impact: Cannot diagnose why scheduled loops fail to start.
- Fix: Replace `logger.error(... error=str(exc))` with `logger.exception(...)`.

---

### 10. `src/loops/evidence.py` (194 lines)

**try/except blocks found:** 0

**Finding F-H4 — HIGH: No exception handling on evidence I/O**
- Location: `collect_phase_artifact()` (L52-72), `generate_final_report()` (L74-173), `get_all_artifacts()` (L175-194)
- Issue: All file I/O operations (`write_artifact()`, `read_artifact()`, `evidence_dir()`) have zero exception handling. If disk is full, permissions denied, or path is corrupted:
  - `collect_phase_artifact()`: Exception propagates to `_run_loop` → fails the loop phase → `state.fail()` → loop dies because of an evidence write failure, not a real phase failure.
  - `generate_final_report()`: Same — evidence report failure could cascade.
  - `get_all_artifacts()`: Read failure on one artifact could prevent reading others.
- Impact: Evidence infrastructure failures are indistinguishable from real phase failures. Evidence loss is silent (no fallback log).
- Fix: Add try/except around each I/O operation. Log failures but don't let them kill the loop — record the failure in the evidence metadata instead.

---

### 11. `src/core/api/routes.py` (90 lines)

**try/except blocks found:** 0

**Specific checks:**
- **Check 13 (Q13): routes.py API endpoint exception handling** — No try/except in any endpoint. FastAPI's default exception handler returns 500 Internal Server Error with a generic body for unhandled exceptions. No custom error responses, no structured error logging.

**Finding F-M5 — MEDIUM: No exception handling in API endpoints**
- Location: All 4 endpoints (list_loops, create_loop, get_loop, cancel_loop)
- Issue: Currently all endpoints are stubs returning hardcoded values, so no real exceptions occur. However:
  - When connected to real `LoopManager`, any exception (e.g., Redis failure in `list_loops`) will produce an opaque 500 with no structured error body.
  - No `HTTPException` usage for known error cases (e.g., loop not found should return 404, not a stub response).
  - `get_loop` (L70-80) returns `"status": "unknown"` for any loop_id — should return 404 for non-existent loops.
- Impact: Degraded API consumer experience; no error differentiation.
- Fix: Add try/except with `HTTPException` for known errors, and a global exception handler middleware for logging.

---

### 12. `src/discord/cmd_loop_start.py` (453 lines)

**try/except blocks found:** 3

| Location | Pattern | Logged | Re-raised | Verdict |
|---|---|---|---|---|
| L367-375 HTTPStatusError | `except httpx.HTTPStatusError: logger.exception; followup` | YES (exception) | NO (handled) | PASS |
| L376-384 RequestError | `except httpx.RequestError: logger.exception; followup` | YES (exception) | NO (handled) | PASS |
| L385-393 Exception | `except Exception: logger.exception; followup` | YES (exception) | NO (handled) | PASS |

**Specific checks:**
- **Check 14 (Q14): cmd_loop_start.py 3-layer error handling** — All 3 layers present and correctly implemented:
  1. `HTTPStatusError` → logs full exception + shows status code to user. ✅
  2. `RequestError` → logs full exception + shows connectivity message. ✅
  3. `Exception` (catch-all) → logs full exception + shows generic error. ✅
- All use `logger.exception()` which auto-includes stack trace. User-facing messages are persona-appropriate and informative.

**Verdict: EXCELLENT.** Gold-standard error handling pattern for Discord commands.

---

### 13. `src/discord/cmd_loop_stop.py` (522 lines)

**try/except blocks found:** 3

| Location | Pattern | Logged | Re-raised | Verdict |
|---|---|---|---|---|
| L436-444 HTTPStatusError | `except httpx.HTTPStatusError: logger.exception; followup` | YES (exception) | NO (handled) | PASS |
| L445-453 RequestError | `except httpx.RequestError: logger.exception; followup` | YES (exception) | NO (handled) | PASS |
| L454-462 Exception | `except Exception: logger.exception; followup` | YES (exception) | NO (handled) | PASS |

**Specific checks:**
- **Check 15 (Q15): cmd_loop_stop.py same pattern** — Identical 3-layer error handling as cmd_loop_start.py. All layers use `logger.exception()`. User-facing messages are persona-appropriate.

**Verdict: EXCELLENT.** Matches cmd_loop_start.py gold-standard pattern.

---

## Cross-Cutting Checks

### Bare `except:` blocks
**Found: 0.** No bare except blocks anywhere. All exception handlers specify at minimum `Exception`.

### `except Exception:` with `pass`/empty body
**Found: 0.** Every `except Exception` handler includes logging and/or state management.

### CancelledError handling
**Found: 4 instances, all correct:**
1. manager.py L119-120 (`stop_loop`) — `pass` after intentional cancel. ✅
2. manager.py L211-213 (`_run_loop`) — logged + re-raised. ✅
3. manager.py L252-253 (`main`) — caught with KeyboardInterrupt. ✅
4. guardian.py L155-156 (`stop`) — `pass` after intentional cancel. ✅

### Swallowed exceptions (logged but state left inconsistent)
**Found: 1 (MEDIUM):**
- scheduler.py `_trigger_loop` (L149-154): Exception is logged but not re-raised. This is intentional (don't crash the scheduler), but the missing stack trace makes it effectively "swallowed for debugging purposes." The state is not inconsistent — the loop simply wasn't started — but diagnosing why is hard.

---

## Findings Summary

| ID | Severity | File | Location | Description |
|---|---|---|---|---|
| F-C1 | **CRITICAL** | cost.py | L55-194 | Zero Redis error handling across all methods. Connection/timeout/auth errors propagate uncaught, causing cost data loss and caller crashes. |
| F-H1 | HIGH | manager.py | L216-222 | `_run_loop` main except uses `logger.error` without stack trace. Cannot debug phase handler failures from logs. |
| F-H2 | HIGH | guardian.py | L105-145 | `monitor()` while-loop body has zero exception handling. Watchdog dies silently on any transient failure. |
| F-H3 | HIGH | guardian.py | L140-141 | `kill_loop()` failure for one loop prevents cleanup of remaining stale loops. No per-loop error isolation. |
| F-H4 | HIGH | evidence.py | L52-194 | All evidence I/O has zero exception handling. Disk/permission failures kill loop phases indistinguishably from real failures. |
| F-M1 | MEDIUM | manager.py | L228-232 | Inner except for partial report uses `str(report_exc)` — no stack trace. |
| F-M2 | MEDIUM | enforcer.py | L96-132 | `enforce()` has no exception handling. Full enforcement pass fails on any single error. |
| F-M3 | MEDIUM | cost.py | L113 | Unprotected `float()` conversion on Redis value — `ValueError` if non-numeric. |
| F-M4 | MEDIUM | scheduler.py | L149-154 | `_trigger_loop` uses `logger.error(str(exc))` — no stack trace for scheduled failures. |
| F-M5 | MEDIUM | routes.py | All endpoints | No exception handling in API endpoints. Stubs mask the gap; real integration will produce opaque 500s. |
| F-L1 | LOW | enforcer.py | Entire module | No error-level logging for edge cases. |
| F-L2 | LOW | sub_agent.py | Entire module | No exception handling (low-risk operations). |
| F-L3 | LOW | contract.py | Entire module | No exception handling (pure data module, acceptable). |

---

## Positive Patterns Observed

| Pattern | Files | Notes |
|---|---|---|
| 3-layer Discord error handling | cmd_loop_start.py, cmd_loop_stop.py | Gold standard: HTTPStatusError → RequestError → Exception, all with `logger.exception()` + user-friendly messages. |
| Defensive validation with safe returns | hash_anchor.py | IndexError, FileNotFoundError, OSError all caught, logged, and converted to `False`. |
| Command execution with timeout | verify.py | `subprocess.run` with 30s timeout, TimeoutExpired + OSError properly handled. |
| CancelledError re-raise | manager.py, guardian.py | All CancelledError handlers either re-raise or are in intentional cancel contexts. |
| Log + re-raise | scheduler.py `remove_job` | Correct pattern: log at warning, then re-raise for caller handling. |
| Finally cleanup | manager.py `_run_loop` | `finally: guardian.unregister_loop()` ensures cleanup regardless of exit path. |

---

## Verdict: NEEDS REVIEW

**Rationale:** The codebase demonstrates strong error handling discipline in its Discord layer and validation modules, but has critical gaps in infrastructure-facing code:

1. **cost.py CRITICAL finding** — Redis operations with zero resilience is a production-blocker. A Redis restart during a loop will crash cost tracking and potentially fail the loop.
2. **guardian.py watchdog gap** — The monitor that's supposed to catch stuck loops can itself die silently. This is an architectural resilience gap.
3. **evidence.py I/O gap** — Evidence infrastructure failures are indistinguishable from real phase failures, making root cause analysis harder.

**Recommended priority for fixes:**
1. F-C1 (cost.py Redis handling) — CRITICAL, fix before production
2. F-H2 (guardian monitor) — HIGH, fix before production
3. F-H4 (evidence I/O) — HIGH, fix before production
4. F-H3 (guardian kill isolation) — HIGH, fix before production
5. F-H1 (manager logger.exception) — HIGH, quick fix
6. F-M1, F-M4 (stack trace gaps) — MEDIUM, quick fixes
7. F-M5 (routes error handling) — MEDIUM, fix when endpoints are non-stub
8. F-M2, F-M3, F-L1-L3 — LOW-MEDIUM, fix in next iteration

---

_Audit complete. No source code was modified._
