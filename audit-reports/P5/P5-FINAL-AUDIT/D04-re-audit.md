# D04 Re-Audit — P5.5 Remediation Verification (Safety Boundary)

| Field | Value |
|---|---|
| Audit ID | P5-FINAL-AUDIT / D04 Re-Audit |
| Auditor | Read-Only Re-Auditor |
| Original Audit | `audit-reports/P5/P5-FINAL-AUDIT/D04-safety-boundary.md` |
| Date | 2026-06-02 |
| Scope | P5.5 remediation: guardian.py kill_loop(), monitor(), HardStopHandler integration |
| **Re-Audit Verdict** | **NEEDS REVIEW** |

---

## 1. Remediation Checklist

| Fix | Description | Source Finding | Status |
|---|---|---|---|
| FIX 4 (C-02) | Guardian.kill_loop() rewrite — state machine fail + task cancel | §2.2 CRITICAL | **PARTIALLY RESOLVED** |
| FIX 5 (H-02) | Guardian monitor() exception handling | §2.2 infra | **RESOLVED** |
| (No Fix) | HardStopHandler integration into src/loops/ | §2.1, §2.4, §2.7 CRITICAL | **NOT RESOLVED (known deferred)** |
| (No Fix) | Safety-aware state transitions | §2.6 HIGH | **NOT RESOLVED (known deferred)** |
| (No Fix) | Distress D2-D4 integration | §2.8 HIGH | **NOT RESOLVED (known deferred)** |

---

## 2. Per-Finding Detailed Analysis

### 2.1 FIX 4 (C-02): Guardian.kill_loop() Rewrite — State Machine + Task Cancel

**Original Finding (§2.2):** kill_loop() only logged and unregistered — no state machine update, no task cancellation. Created zombie loops.

**P5.5 Remediation Applied:** kill_loop() rewritten to call `state_machine.fail(reason)` and `cancel_callback()` with isolated exception handling.

**Evidence (guardian.py lines 100-117):**

```python
async def kill_loop(self, loop_id: str, reason: str) -> None:
    """Kill a stalled loop: update state machine, cancel task, unregister."""
    data = self.active_loops.get(loop_id)
    if data is None:
        logger.warning("guardian.kill_loop_not_found", loop_id=loop_id)
        return

    # Update state machine to FAILED
    state_machine = data.get("state_machine")
    if state_machine is not None:
        try:
            state_machine.fail(reason)
        except Exception:
            logger.exception("guardian.state_fail_failed", loop_id=loop_id)

    # Cancel the asyncio task via callback
    cancel_cb = data.get("cancel_callback")
    if cancel_cb is not None:
        try:
            cancel_cb()
        except Exception:
            logger.exception("guardian.cancel_callback_failed", loop_id=loop_id)

    logger.warning("loop_killed", loop_id=loop_id, reason=reason)
    self.unregister_loop(loop_id)
```

**Verification:**

| Check | Result | Evidence |
|---|---|---|
| Calls state_machine.fail(reason)? | **YES** | guardian.py line 106 |
| Isolated exception handling? | **YES** | guardian.py lines 107-108 |
| Calls cancel_callback()? | **YES** (functionally) | guardian.py lines 112-115 |
| Is cancel_callback WIRED at registration? | **NO** | manager.py line 72 |

**CRITICAL GAP — cancel_callback never wired:**

`manager.py` line 72:
```python
self.guardian.register_loop(loop_id, state)
# ─── cancel_callback parameter defaults to None ───
```

The `LoopGuardian.register_loop()` signature (guardian.py line 44):
```python
def register_loop(self, loop_id: str, state_machine: object,
                  cancel_callback: Optional[Callable[[], None]] = None) -> None:
```

`start_loop()` never passes a `cancel_callback`. This means:
1. When guardian calls `kill_loop()`, `cancel_cb` is always `None` → task cancellation branch is **never executed**.
2. The asyncio task continues running until it reaches the `state.is_terminal()` check on the next phase boundary.

**Mitigation exists:** `_run_loop()` (manager.py line ~150) checks `state.is_terminal()` before each phase:
```python
if state.is_terminal():
    logger.info(...)
    return
```
Since `state_machine.fail()` sets status to `LoopStatus.FAILED` (in `_TERMINAL_STATUSES`), the loop WILL exit — but only at the next phase boundary. A long-running phase handler (e.g., future LLM call) would not be interrupted until it completes.

**Verdict: PARTIALLY RESOLVED**

The state machine fix is correct and complete. The cancel_callback mechanism is architecturally present but operationally inert. The gap is:
- State transitions correctly from RUNNING → FAILED ✓
- Loop exits cleanly at next phase boundary via `is_terminal()` ✓
- Loop is NOT interrupted mid-phase ✗
- `start_loop()` should pass the task's `.cancel()` as the `cancel_callback` to close this gap

---

### 2.2 FIX 5 (H-02): Guardian monitor() Exception Handling

**Original Finding:** monitor() could crash from unhandled exceptions during kill loop operations, dropping all monitoring.

**P5.5 Remediation Applied:** monitor() now wraps kill_loop() calls and the outer loop body in isolated try/except blocks.

**Evidence (guardian.py lines 126-157):**

```python
async def monitor(self) -> None:
    """Main monitoring loop..."""
    self._running = True
    logger.info("guardian_monitor_started")
    while self._running:
        try:                                    # ← OUTER try/except (line 131)
            now = datetime.now(timezone.utc)
            stale_loops: list[tuple[str, str]] = []

            for loop_id, data in list(self.active_loops.items()):
                # Heartbeat check...
                # Progress timeout check...
                # Resource check...

            for loop_id, reason in stale_loops:
                try:                             # ← INNER try/except per kill (line 146)
                    await self.kill_loop(loop_id, reason)
                except Exception:
                    logger.exception("guardian.kill_failed", loop_id=loop_id)
        except Exception:                        # ← OUTER catch-all (line 155)
            logger.exception(
                "guardian.monitor_error",
                error="unexpected error in monitoring loop",
            )

        await asyncio.sleep(self.HEARTBEAT_INTERVAL)
```

**Verification:**

| Check | Result | Evidence |
|---|---|---|
| Outer try/except guards entire tick? | **YES** | guardian.py line 131-155 |
| Individual kill_loop() failures isolated? | **YES** | guardian.py lines 146-149 |
| Monitoring loop survives errors? | **YES** | Both levels catch and continue |
| Monitoring loop can be stopped? | **YES** | `stop()` sets `_running = False` (line 163) |

**Verdict: RESOLVED**

The monitor loop is now resilient — a single kill failure won't prevent other loop checks, and unexpected errors in the tick body won't crash the monitoring loop.

---

### 2.3 HardStopHandler Integration into src/loops/ (No Fix — Known Deferred)

**Original Findings (§2.1, §2.4, §2.7):** Three CRITICAL findings: no pre-phase safety check, complete isolation from loop engine, no safe word propagation.

**Grep Confirmation:**

```
grep -ri "HardStopHandler|hard_stop|safe_word|HARD STOP" src/loops/
  → 0 matches
```

**HardStopHandler status (src/core/services/hard_stop_handler.py):**
- 149 lines, fully implemented ✓
- Supports exact triggers + semantic patterns + recovery ✓
- `check()`, `check_recovery()`, `get_guard_decision()` all functional ✓
- Partially integrated in `src/core/services/prompt_loader.py` (pre-LLM chat middleware) ✓
- **No integration with `src/loops/`** — confirmed isolation ✗

**Impact remains:**
- `HARD STOP` in Discord neutralizes chat persona — CORRECT
- Autonomous loops continue executing regardless — CRITICAL GAP
- No event bus, shared state, or callback connecting the two subsystems

**Known Deferred Gap:** Documented in original audit as "phases are templates, no LLM calls yet." The mitigation is that all 7 phase handlers (`src/loops/phases/`) are static template stubs with no LLM invocation, no destructive operations, no external API calls. The risk is latent until LLM integration.

**Verdict: NOT RESOLVED (known deferred)**

Not marked as FAIL per instructions — this is a documented deferred gap with valid mitigation (no LLM calls in phases). Must be resolved before LLM integration wave.

---

### 2.4 Safety-Aware State Transitions (No Fix — Known Deferred)

**Original Finding (§2.6, HIGH):** No SAFETY_HOLD status, no gated resume, no safety clearance on state transitions.

**Current State (unchanged):**
- `LoopStatus` enum: INIT, RUNNING, PAUSED, BLOCKED, COMPLETE, FAILED, CANCELLED
- No SAFETY_HOLD or SAFE_MODE status
- `resume()` transitions PAUSED/BLOCKED → RUNNING directly with no safety gate

**Verdict: NOT RESOLVED (known deferred)**

---

### 2.5 Distress D2-D4 Integration (No Fix — Known Deferred)

**Original Finding (§2.8, HIGH):** No distress classifier, no mapping from distress level to loop action, no distress-aware logging in loop subsystem.

**Current State (unchanged):** Zero distress awareness in `src/loops/`.

**Verdict: NOT RESOLVED (known deferred)**

---

### 2.6 New Finding: cancel_callback Wiring Gap in start_loop()

**Severity: MEDIUM**

`manager.py` `start_loop()` (line 72) registers the loop with guardian but does NOT pass a cancel callback:

```python
# manager.py lines 72-82
self.guardian.register_loop(loop_id, state)
#                          ↑ missing cancel_callback argument

loop_task = asyncio.create_task(
    self._run_loop(loop_id, task, goal),
    name=f"loop-{loop_id}",
)
self._tasks[loop_id] = loop_task
```

The task reference `self._tasks[loop_id]` exists in `LoopManager` but is not wired to `LoopGuardian`. Should be:

```python
self.guardian.register_loop(
    loop_id, state,
    cancel_callback=lambda: loop_task.cancel()
)
```

This is a one-line fix that would make the guardian's cancel_callback mechanism operational, enabling true mid-phase cancellation rather than relying solely on the phase-boundary `is_terminal()` check.

---

## 3. Summary: Resolved vs Remaining

### Resolved

| Original Finding | Severity | P5.5 Status | Evidence |
|---|---|---|---|
| §2.2 kill_loop() no state update | CRITICAL | **RESOLVED** (state machine fix) | guardian.py:106 |
| §2.2 kill_loop() no task cancel | CRITICAL | **PARTIALLY RESOLVED** (callback exists, not wired) | guardian.py:112-115 vs manager.py:72 |
| monitor() crash risk | HIGH | **RESOLVED** | guardian.py:131-155 |

### Still Open (Known Deferred)

| Original Finding | Severity | Status | Mitigation |
|---|---|---|---|
| §2.1 HardStopHandler in _run_loop() | CRITICAL | NOT RESOLVED | All phases are stubs — no LLM, no destructive ops |
| §2.4 HardStopHandler isolation | CRITICAL | NOT RESOLVED | Deferred to LLM integration wave |
| §2.7 Safe word propagation to loops | CRITICAL | NOT RESOLVED | Deferred to LLM integration wave |
| §2.6 Safety-aware transitions | HIGH | NOT RESOLVED | Deferred |
| §2.8 Distress D2-D4 integration | HIGH | NOT RESOLVED | Deferred |

---

## 4. Re-Audit Verdict

### **NEEDS REVIEW**

**Rationale:**

FIX 4 (kill_loop) and FIX 5 (monitor) are correctly implemented and verified. The guardian now properly transitions killed loops to FAILED state and monitors with resilience. These are meaningful, verifiable improvements over the original audit state.

However, the cancel_callback wiring gap means the guardian still cannot actually interrupt a running asyncio task mid-execution. This limits the effectiveness of kill_loop() — state is correct, but the running task continues until the next phase boundary. This is a functional gap worth closing with a one-line fix.

The HardStopHandler integration findings remain NOT RESOLVED, as documented. This is accepted as a known deferred gap with the valid mitigation that all phase handlers are currently static templates. The latency of this risk will activate only when LLM calls are integrated into phase handlers.

**Recommendation (unchanged from original audit):** Block LLM integration into phase handlers until:
1. HardStopHandler is wired into LoopManager
2. Pre-phase safety check is added to `_run_loop()`
3. cancel_callback is wired in `start_loop()`

---

## 5. Auditor Sign-Off

| Field | Value |
|---|---|
| Auditor | Read-Only Re-Auditor |
| Report path | `audit-reports/P5/P5-FINAL-AUDIT/D04-re-audit.md` |
| Original audit | `audit-reports/P5/P5-FINAL-AUDIT/D04-safety-boundary.md` |
| **Re-Audit Verdict** | **NEEDS REVIEW** |
| Resolved findings | 2.5 of 8 (kill_loop state, monitor exceptions, partial task cancel) |
| Deferred findings | 5 of 8 (HardStopHandler integration ×3, safety transitions, distress) |
| New findings | 1 (cancel_callback wiring gap — MEDIUM) |
| Files read | `src/loops/guardian.py`, `src/loops/manager.py`, `src/loops/state_machine.py`, `src/core/services/hard_stop_handler.py` |
| Grep performed | `src/loops/` for `HardStopHandler\|hard_stop\|safe_word\|HARD STOP\|HardStop` — 0 matches confirmed |