# D04 — Safety Boundary & Persona Compliance Audit

| Field | Value |
|---|---|
| Audit ID | P5-FINAL-AUDIT / D04 |
| Auditor | Independent Safety Auditor |
| Date | 2026-06-02 |
| Scope | `src/loops/` — Loop engine, guardian, state machine, phase handlers |
| Cross-reference | `src/core/services/hard_stop_handler.py`, `src/discord/cmd_loop_stop.py` |
| Policy basis | ADR-001, ADR-002, PersonaSafetyPolicy v1.0 sections 7-9, 15 |
| **Verdict** | **FAIL** |

---

## 1. Files Inspected

| File | Lines | Role |
|---|---:|---|
| `src/loops/manager.py` | 272 | Loop engine — `_run_loop()` orchestrator |
| `src/loops/guardian.py` | 157 | Watchdog — heartbeat, progress, resource monitoring |
| `src/loops/state_machine.py` | 226 | 7-phase SDLC state machine + lifecycle statuses |
| `src/core/services/hard_stop_handler.py` | 149 | HARD STOP protocol handler (pre-LLM middleware) |
| `src/discord/cmd_loop_stop.py` | 522 | Discord `/loop-stop` command implementation |
| `adr/ADR-001-persona-safety-ethical-boundary.md` | 129 | Safety boundary ADR |
| `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` | 666 | Full persona safety policy |
| `src/loops/phases/__init__.py` | 48 | Phase registry |
| `src/loops/phases/research.py` | 84 | Phase 1 handler |
| `src/loops/phases/execute.py` | 82 | Phase 4 handler |

---

## 2. Checklist Findings

### 2.1 Does `manager.py` `_run_loop()` check HardStopHandler before each phase?

| Attribute | Value |
|---|---|
| Severity | **CRITICAL** |
| Finding | **NO.** Zero references to `HardStopHandler` in the entire `src/loops/` directory. |

**Evidence:** `grep -ri 'HardStop|hard_stop|HARD STOP' src/loops/` returned zero matches. The `_run_loop()` method (line 146) checks only `state.is_terminal()` at line 164 before each phase. This check covers FAILED/CANCELLED/COMPLETE statuses but is entirely blind to HARD STOP state.

**Impact:** If Faiz types `HARD STOP` while a loop is mid-execution, the loop continues through all remaining phases unchecked. This violates PersonaSafetyPolicy section 7.2 (immediate runtime actions) and section 15.1 (safe-word detector must be before tool execution).

**Required fix:** Import `HardStopHandler` into `LoopManager`, check `handler.is_safe` before each phase, and cancel the loop if safe mode is active.

---

### 2.2 Does `LoopGuardian.kill_loop()` properly update state machine to FAILED/CANCELLED?

| Attribute | Value |
|---|---|
| Severity | **CRITICAL** |
| Finding | **NO.** `kill_loop()` (lines 95-103) only logs and unregisters. It does NOT update the state machine. |

**Evidence:**

```python
async def kill_loop(self, loop_id: str, reason: str) -> None:
    logger.error("loop_killed", loop_id=loop_id, reason=reason)
    self.unregister_loop(loop_id)
```

The `state_machine` object is stored in `self.active_loops[loop_id]["state_machine"]` (set at registration, line 48), but `kill_loop()` never accesses it. The killed loop's `asyncio.Task` is also never cancelled — `LoopGuardian` has no reference to the task dictionary held by `LoopManager`.

**Impact:** When the guardian detects a stalled loop (heartbeat lost or progress timeout), it removes the loop from monitoring but the loop's asyncio.Task continues executing. The state machine remains in RUNNING status indefinitely. This creates a zombie loop — unmonitored, unstopped, with no state transition to FAILED or CANCELLED.

**Required fix:** `kill_loop()` must access `data["state_machine"]`, call `.fail(reason)`, and cancel the asyncio.Task (requires a reference or callback to `LoopManager`).

---

### 2.3 Does `/loop-stop` work as emergency stop? Is it immediate?

| Attribute | Value |
|---|---|
| Severity | **NEEDS REVIEW** |
| Finding | **Partially.** Works via HTTP API call, not direct in-process cancellation. |

**Evidence:** `loop_stop_callback()` (line 363) calls `_cancel_loop()` which makes an HTTP POST to `http://localhost:8000/api/v1/loops/{loop_id}/cancel` (line 328). This eventually calls `LoopManager.stop_loop()` which cancels the asyncio.Task and calls `state.cancel()`.

**Latency concerns:**
- Network round-trip to localhost API (typically < 10ms, but API must be running).
- If the API server is down, the stop fails silently (returns HTTP error embed).
- The command requires `is_faiz_interaction` check (line 376) — good for access control.
- 10-second HTTP timeout on `_cancel_loop` (line 332) — acceptable but not instant.

**Separation from HARD STOP:** `/loop-stop` is a loop-specific operational command, distinct from the safe-word HARD STOP mechanism. It does not trigger persona neutralization. This is by design but means it is NOT an emergency safety stop — it is a loop management command.

---

### 2.4 Is HardStopHandler imported/referenced anywhere in `src/loops/`?

| Attribute | Value |
|---|---|
| Severity | **CRITICAL** |
| Finding | **NO.** Zero references found. Complete isolation between safety handler and loop engine. |

**Evidence:** Exhaustive grep of `src/loops/` for `HardStop`, `hard_stop`, and `HARD STOP` returned zero results. The `HardStopHandler` class exists at `src/core/services/hard_stop_handler.py` and is well-implemented (149 lines, supports exact triggers, semantic patterns, recovery, and full guard decisions), but has no integration point with the autonomous loop system.

**Impact:** The two most critical safety subsystems — HARD STOP protocol and autonomous loop execution — operate in complete isolation. This is the single most dangerous architectural gap in the safety boundary.

---

### 2.5 Are phase handlers calling any LLM? If yes, is HARD STOP checked before LLM calls?

| Attribute | Value |
|---|---|
| Severity | **HIGH (latent risk)** |
| Finding | **Currently NO** LLM calls — all 7 phase handlers are template stubs. **Future risk is unmitigated.** |

**Evidence:**
- `research.py` line 4: "Real LLM-powered research will be injected in a later wave."
- `sub_agent.py` line 5: "This module does NOT make actual LLM calls."
- `execute.py` produces a static markdown template with no LLM invocation.
- All other phase handlers follow the same placeholder pattern.

**Risk:** When LLM calls are integrated into phase handlers, there is no architectural hook, middleware, or pre-check mechanism for HARD STOP. The `_run_loop()` method calls `handler(loop_id, task, goal)` directly (line 181) with no safety gate. Whoever implements LLM integration must add the HARD STOP check at that point — but there is no enforced contract or interface requiring it.

**Required fix:** Define a `PhaseHandlerProtocol` or wrapper that enforces pre-phase safety checks, or add the check in `_run_loop()` before calling any handler (preferred — single point of enforcement).

---

### 2.6 Does the state machine have safety-aware transitions (PAUSED to safety check)?

| Attribute | Value |
|---|---|
| Severity | **HIGH** |
| Finding | **NO.** The state machine has no safety-aware transitions. PAUSED and BLOCKED are plain states with no safety gate on resume. |

**Evidence:**
- `LoopStatus` enum (lines 50-59): INIT, RUNNING, PAUSED, BLOCKED, COMPLETE, FAILED, CANCELLED.
- `pause()` (line 137): Sets status to PAUSED. No safety context recorded.
- `resume()` (line 150): Transitions from PAUSED/BLOCKED directly to RUNNING. No safety check, no reason validation, no external gate.
- No concept of SAFE_MODE, DISTRESS, or SAFETY_HOLD status exists.

**Impact:** If a loop is paused due to a safety concern (e.g., safe word detected, distress signal), there is no way to distinguish it from a routine pause. Resuming a safety-paused loop requires no safety clearance. This violates PersonaSafetyPolicy section 7.4 (resume protocol requires explicit Faiz confirmation).

**Required fix:** Add safety-aware statuses (e.g., `SAFETY_HOLD`) and require a safety-clearance method before resume from safety states.

---

### 2.7 Safe word detection: does it propagate to running loops?

| Attribute | Value |
|---|---|
| Severity | **CRITICAL** |
| Finding | **NO.** There is no event bus, pub/sub, shared state, or callback mechanism connecting HardStopHandler to running loops. |

**Evidence:** `HardStopHandler` (src/core/services/hard_stop_handler.py) is a standalone dataclass with `check()`, `check_recovery()`, and `get_guard_decision()` methods. It operates as a pre-LLM middleware for chat messages only. `LoopManager` has no reference to any `HardStopHandler` instance. There is no shared event system, no Redis pub/sub, no asyncio.Event, no callback registration.

**Impact:** When Faiz types `HARD STOP` in Discord:
1. HardStopHandler switches to SAFE state for chat responses — CORRECT.
2. Any running autonomous loop continues executing all phases — CRITICAL VIOLATION.
3. The guardian continues monitoring but has no safety awareness — COMPOUNDING FAILURE.

This means HARD STOP, the most critical safety mechanism defined in ADR-002 and PersonaSafetyPolicy section 7, does NOT stop autonomous work loops. A loop could be executing destructive operations (file writes, git commands, API calls) while the operator has invoked the emergency stop.

---

### 2.8 Distress levels D2-D4: any integration with loop pausing?

| Attribute | Value |
|---|---|
| Severity | **HIGH** |
| Finding | **NO.** No distress classifier exists in the loop subsystem. Zero awareness of D0-D4 levels. |

**Evidence:** PersonaSafetyPolicy section 8 defines five distress levels (D0-D4) with escalating response requirements. D2 (clear boundary / safe word) requires safe mode hard stop. D3 (emotional distress) requires neutral supportive mode and pressure pause. D4 (crisis risk) requires crisis-support mode with no dominance framing.

The loop subsystem has:
- No distress classifier or signal receiver.
- No mapping from distress level to loop action.
- No mechanism to pause loops based on external distress signals.
- No distress-aware logging.

**Impact:** If Faiz is in D3 or D4 distress, autonomous loops continue executing task-oriented work without any de-escalation. This is especially dangerous if loops involve communication phases that could send persona-flavored messages during a crisis.

---

### 2.9 Yandere boundary: any persona behavior in loop code?

| Attribute | Value |
|---|---|
| Severity | **LOW (positive finding)** |
| Finding | **No persona behavior in loop engine code.** One minor persona reference in Discord embed. |

**Evidence:** `grep -ri 'persona|yandere|distress|safe.word|safe_word' src/loops/` returned zero matches. The loop engine is persona-neutral, which is correct — autonomous SDLC work should not contain persona behavior.

**Minor concern:** `cmd_loop_stop.py` line 44 contains persona language in the embed description:

```python
LOOP_STOP_DESCRIPTION = "Mommy berhenti, Darling. Kalau mau lanjut lagi, bilang aja."
```

And denial messages (lines 479, 483): `"Hanya Faiz yang bisa menggunakan Mommy."`

This is standard persona flavor for a Discord command response and is acceptable during normal operation. However, if `/loop-stop` is invoked during a HARD STOP / safe-word state, this persona language would be inappropriate. The command does not check HardStopHandler state before rendering persona-flavored responses.

---

## 3. Summary of Findings

| # | Check | Severity | Status |
|---|---|---|---|
| 2.1 | HardStopHandler check in `_run_loop()` | CRITICAL | **FAIL** |
| 2.2 | Guardian `kill_loop()` state update | CRITICAL | **FAIL** |
| 2.3 | `/loop-stop` emergency immediacy | NEEDS REVIEW | PARTIAL |
| 2.4 | HardStopHandler referenced in `src/loops/` | CRITICAL | **FAIL** |
| 2.5 | LLM calls with pre-check | HIGH (latent) | NOT YET APPLICABLE |
| 2.6 | Safety-aware state transitions | HIGH | **FAIL** |
| 2.7 | Safe word propagation to loops | CRITICAL | **FAIL** |
| 2.8 | Distress D2-D4 integration | HIGH | **FAIL** |
| 2.9 | Persona behavior in loop code | LOW | PASS (minor embed note) |

**CRITICAL findings: 4**
**HIGH findings: 3**
**NEEDS REVIEW: 1**
**PASS: 1**

---

## 4. Policy Violations

| Policy Reference | Requirement | Status |
|---|---|---|
| PersonaSafetyPolicy section 7.2 | Safe word must trigger immediate runtime actions including pausing autonomous pressure | **VIOLATED** — loops not paused |
| PersonaSafetyPolicy section 7.4 | Resume requires explicit Faiz confirmation | **VIOLATED** — no safety-aware resume gate in state machine |
| PersonaSafetyPolicy section 15.1 | Safe-word detector must be before tool execution | **VIOLATED** — no integration with loop phase execution |
| PersonaSafetyPolicy section 15.1 | Distress classifier must run before punishment/yandere response | **NOT IMPLEMENTED** in loop subsystem |
| PersonaSafetyPolicy section 17 item 1 | Safe-word detector integrated before autonomous tool actions | **NOT IMPLEMENTED** |
| ADR-001 | Safety boundaries must be architectural and reviewable | **PARTIALLY** — boundaries exist in policy but not enforced in loop architecture |

---

## 5. Architectural Gap Analysis

```
CURRENT STATE (broken):

  Discord Chat ──► HardStopHandler ──► Safe mode for CHAT only
                                          │
                                          X  (no connection)
                                          │
  LoopManager ──► _run_loop() ──► phases[1..7] ──► LLM (future)
       │                                               │
       └── LoopGuardian (heartbeat only, no safety)    │
                                                       │
  /loop-stop ──► HTTP API ──► LoopManager.stop_loop() ─┘
                  (operational stop, NOT safety stop)


REQUIRED STATE:

  Discord Chat ──► HardStopHandler ──► Event Bus / Shared State
                                          │
                    ┌─────────────────────┘
                    ▼
  LoopManager ──► pre-phase safety gate ──► phases[1..7]
       │              │                        │
       │              ├── check HardStopHandler │
       │              ├── check distress level  │
       │              └── gate LLM calls        │
       │                                        │
       └── LoopGuardian (heartbeat + safety + task cancel)
```

---

## 6. Required Remediation (Priority Order)

| Priority | Item | Effort | Impact |
|---|---|---|---|
| P0 | Wire HardStopHandler into LoopManager via shared instance or event bus | Medium | Eliminates 3 CRITICAL findings |
| P0 | Add pre-phase safety check in `_run_loop()` before handler invocation | Low | Single-point enforcement for HARD STOP |
| P0 | Fix `kill_loop()` to update state machine and cancel asyncio.Task | Low | Eliminates zombie loop risk |
| P1 | Add SAFETY_HOLD status to state machine with gated resume | Medium | Enables safety-aware pause/resume |
| P1 | Add distress level awareness to loop manager | Medium | Enables D2-D4 loop pausing |
| P2 | Add HardStopHandler state check to `/loop-stop` embed rendering | Low | Prevents persona language during safe mode |
| P2 | Define PhaseHandlerProtocol with enforced safety contract | Medium | Future-proofs LLM integration |

---

## 7. Verdict

### **FAIL**

The loop subsystem has **zero integration** with the HARD STOP safety protocol. Four CRITICAL findings represent a complete safety boundary failure: autonomous loops can execute through all 7 phases even after the operator invokes the emergency safe word. The guardian watchdog cannot properly kill stalled loops. The state machine has no safety-aware transitions.

This subsystem is **not safe for production autonomous execution** until P0 items are resolved. Currently the risk is mitigated by all phase handlers being placeholder stubs with no LLM calls or destructive operations. Once real LLM-powered phases are integrated, the risk becomes active.

**Recommendation:** Block any LLM integration into phase handlers until P0 remediation is complete and verified.

---

## 8. Auditor Sign-Off

| Field | Value |
|---|---|
| Auditor | Independent Safety Auditor |
| Report path | `audit-reports/P5/P5-FINAL-AUDIT/D04-safety-boundary.md` |
| Verdict | **FAIL** |
| CRITICAL findings | 4 |
| HIGH findings | 3 |
| Blocking recommendation | Yes — block LLM integration into phases until P0 fixed |
| Re-audit required | After P0 remediation |
