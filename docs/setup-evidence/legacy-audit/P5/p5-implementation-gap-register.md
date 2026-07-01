# P5 Implementation Gap Register

**Date:** 2026-06-27

---

## Gap Register

### GAP-001: Safety Gate Not Wired to Phase Transitions
- **Claimed:** LoopSafetyGate provides safety checks for autonomous loops
- **Actual:** LoopSafetyGate.check() exists in `safety_integration.py` but is NEVER called from `LoopManager._run_loop()`
- **Gap Type:** IMPLEMENTED_BUT_NOT_WIRED
- **Impact:** No safety checks between loop phases
- **Evidence:** `src/loops/safety_integration.py` line 97, `src/loops/manager.py` lines 217-325

### GAP-002: Consent Check Missing from Loop Execution
- **Claimed:** "consent and safety boundaries outrank any task" (prompts.py line 100)
- **Actual:** Prompt-level text only. No code-level consent state check in loop lifecycle.
- **Gap Type:** DOCS_ONLY
- **Impact:** Loop can continue after consent revocation

### GAP-003: Budget Pre-Check Missing from Loop
- **Claimed:** "Cost tracking per loop" (P5-023)
- **Actual:** Cost recorded AFTER phase but never blocks. IterationBudget (fail-closed) exists but unused by main loop.
- **Gap Type:** IMPLEMENTED_BUT_NOT_WIRED
- **Impact:** Unbounded cost accumulation possible

### GAP-004: LLM Integration Dormant
- **Claimed:** "7-phase autonomous SDLC engine" (src/loops/__init__.py docstring)
- **Actual:** `LoopManager(llm_router=None)` — phase handlers generate fallback/template artifacts only
- **Gap Type:** DEPLOYED_BUT_FLAG_OFF_OR_INERT
- **Impact:** Loop is a task skeleton, not an LLM-driven autonomous system

### GAP-005: Distress Detection Not Implemented
- **Claimed:** D0-D4 distress protocol integration (implied by persona safety)
- **Actual:** `"distress"` label in priority.py and context.py only. No detection mechanism.
- **Gap Type:** DEAD_CODE (labels only)
- **Impact:** Distress during loop execution not detected

### GAP-006: Sub-Agent Constraint Enforcement
- **Claimed:** "Sub-agent task contract" (P5-015), "MUST NOT DO" constraints
- **Actual:** TaskContract.must_not_do rendered as text in delegation prompt. No post-execution validation.
- **Gap Type:** DOCS_ONLY
- **Impact:** Sub-agents can violate MUST NOT constraints undetected

### GAP-007: Output Verification Limited
- **Claimed:** "Sub-agent output verification" (P5-016)
- **Actual:** OutputVerifier checks file existence (Path.is_file()) and optional text patterns. Does not read files. verify_command() runs arbitrary shell.
- **Gap Type:** IMPLEMENTED_WITH_LIMITATION
- **Impact:** Verification is shallow — existence check only, not content validation

### GAP-008: P19 Project Scoping Not Threaded
- **Claimed:** P19 project context integration
- **Actual:** LoopContext has project_id field but LoopManager.start_loop() does not accept or thread it
- **Gap Type:** IMPLEMENTED_BUT_NOT_WIRED
- **Impact:** Loops are global-scoped despite P19 project isolation

### GAP-009: Test Coverage Gap
- **Claimed:** "205 passed" verification suite
- **Actual:** Only 2/21 source files have dedicated tests. 7 phase handlers have zero individual tests. "205 passed" is from the T1-T10 verification suite, not per-module unit tests.
- **Gap Type:** STALE_EVIDENCE (misleading coverage claim)
- **Impact:** Individual module regressions undetectable

### GAP-010: Dead Code Acknowledgment
- **Claimed:** 23 steps all complete
- **Actual:** 5 modules (enforcer, hash_anchor, sub_agent, contract, verify) have zero production callers. 700 lines of dead code.
- **Gap Type:** DEAD_CODE
- **Impact:** False impression of functionality, unmaintained code

### GAP-011: HermesBridge Superseded
- **Claimed:** Hermes ↔ LoopManager coordination bridge
- **Actual:** main.py explicitly states "superseded by the Living Autonomy Kernel" (line 464)
- **Gap Type:** SUPERSEDED_BY_LATER_PHASE
- **Impact:** Dead code, confusing for auditors

### GAP-012: Dual HARD STOP Systems
- **Claimed:** HARD STOP protocol integrated
- **Actual:** Two independent systems: P5 HardStopHandler (keyword-based) and P20 Redis key. No coordination.
- **Gap Type:** IMPLEMENTED_WITH_ARCHITECTURAL_GAP
- **Impact:** HARD STOP from one system may not propagate to the other

---

## Summary

| Gap Type | Count |
|----------|-------|
| IMPLEMENTED_BUT_NOT_WIRED | 4 |
| DOCS_ONLY | 2 |
| DEPLOYED_BUT_FLAG_OFF_OR_INERT | 1 |
| DEAD_CODE | 2 |
| IMPLEMENTED_WITH_LIMITATION | 1 |
| IMPLEMENTED_WITH_ARCHITECTURAL_GAP | 1 |
| SUPERSEDED_BY_LATER_PHASE | 1 |
| STALE_EVIDENCE | 1 |
| **TOTAL** | **12** |
