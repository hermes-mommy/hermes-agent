# P5 Bug Register — All Severity

**Date:** 2026-06-27
**Audit ID:** GAS-AUDIT-P5-2026-06-27

---

## CRITICAL

### P5-BUG-001: No Safety Gate Between Loop Phases
- **Severity:** CRITICAL
- **Category:** Safety/Wiring
- **Source:** `src/loops/manager.py` lines 217-325
- **Expected:** LoopSafetyGate.check() called before each phase transition
- **Actual:** `_run_loop()` iterates all 7 phases with zero safety checks. HARD STOP runs only on Guardian's 30-second tick.
- **Impact:** Up to 30 seconds of phase execution after HARD STOP triggered. No consent check, no budget check between phases.
- **Fix Recommendation:** Wire `LoopSafetyGate.check()` at the top of each phase iteration in `_run_loop()`
- **Requires Mama Approval:** YES
- **Requires Runtime Restart:** YES (guinevere-core.service)
- **Classification:** IMPLEMENTED_BUT_NOT_WIRED

### P5-BUG-002: llm_router=None Makes Loop LLM-Dead
- **Severity:** CRITICAL
- **Category:** Architecture/Wiring
- **Source:** `src/core/main.py` line 103
- **Expected:** LoopManager receives LLM router for autonomous phase execution
- **Actual:** `LoopManager(llm_router=None)` — all 7 phase handlers receive None, cannot make LLM calls
- **Impact:** The SDLC loop is a task execution skeleton, NOT the autonomous brain described in Phase 5 scope. Phases generate fallback/template artifacts only.
- **Fix Recommendation:** Wire llm_router or HermesBrain to LoopManager, or explicitly document as non-LLM task executor
- **Requires Mama Approval:** YES (architecture decision)
- **Requires Runtime Restart:** YES
- **Classification:** DEPLOYED_BUT_FLAG_OFF_OR_INERT

### P5-BUG-003: Consent Boundary Not Programmatically Enforced
- **Severity:** CRITICAL
- **Category:** Safety/Consent
- **Source:** `src/loops/manager.py`, `src/loops/sub_agent.py`
- **Expected:** Consent check before sub-agent spawning and between phases
- **Actual:** Consent mentioned in system prompt only (prompts.py lines 100, 149-151). No code-level consent check.
- **Impact:** Loop can continue executing after consent revocation. Sub-agents spawn without consent verification.
- **Fix Recommendation:** Add consent state check to `_run_loop()` phase iteration and `SubAgentSpawner.spawn()`
- **Requires Mama Approval:** YES (safety boundary change)
- **Requires Runtime Restart:** YES
- **Classification:** DOCS_ONLY

### P5-BUG-004: Budget Enforcement Not Wired to Main Loop
- **Severity:** CRITICAL
- **Category:** Cost/Safety
- **Source:** `src/loops/manager.py`, `src/loops/cost.py`
- **Expected:** Pre-phase budget check blocking execution at $30/month cap
- **Actual:** `LoopCostTracker` records cost AFTER phase but never blocks. `IterationBudget` (fail-closed) exists but only used by `ConversationLoop`. Main loop has NO budget guard.
- **Impact:** Loop can accumulate unbounded cost without operator approval.
- **Fix Recommendation:** Wire `IterationBudget` or `CostTracker.check_budget()` as pre-phase guard
- **Requires Mama Approval:** YES
- **Requires Runtime Restart:** YES
- **Classification:** IMPLEMENTED_BUT_NOT_WIRED

### P5-BUG-005: LoopCostTracker Fail-Open on Redis Error
- **Severity:** CRITICAL
- **Category:** Error Handling
- **Source:** `src/loops/cost.py` line 123
- **Expected:** Fail-closed on Redis error (raise or return error status)
- **Actual:** Returns `0.0` on Redis error — cost silently lost
- **Impact:** Redis outage = cost tracking silently disabled, no alerts
- **Fix Recommendation:** Raise on Redis error or return error status, match P5.5 FIX-03 intent
- **Requires Mama Approval:** YES
- **Requires Runtime Restart:** NO (code fix only)
- **Classification:** IMPLEMENTED_WITH_BUG

---

## HIGH

### P5-BUG-006: Distress Detection (D0-D4) Not Implemented in Loop
- **Severity:** HIGH
- **Category:** Safety/Persona
- **Source:** `src/loops/` (entire package)
- **Expected:** D0-D4 distress detection pauses/stops loop execution
- **Actual:** `"distress"` exists as a label in priority.py and context.py — classification only, no detection mechanism
- **Impact:** Distress signals during loop execution are not detected or acted upon
- **Fix Recommendation:** Wire `src/persona/safe_mode.py` distress detection into loop's phase iteration
- **Requires Mama Approval:** YES
- **Requires Runtime Restart:** YES
- **Classification:** DEAD_CODE (labels only)

### P5-BUG-007: Two Independent HARD STOP Systems Without Coordination
- **Severity:** HIGH
- **Category:** Architecture/Safety
- **Source:** `src/core/services/hard_stop_handler.py`, `src/life_kernel/heartbeat.py`
- **Expected:** Unified HARD STOP across all autonomous systems
- **Actual:** P5 uses keyword-based HardStopHandler → guardian. P20 uses Redis key `life_kernel:hard_stop`. No coordination between them.
- **Impact:** HARD STOP from one system may not propagate to the other
- **Fix Recommendation:** Create unified HARD STOP coordinator or share Redis key
- **Requires Mama Approval:** YES (architecture)
- **Requires Runtime Restart:** YES
- **Classification:** IMPLEMENTED_WITH_ARCHITECTURAL_GAP

### P5-BUG-008: Semantic Bug in Guardian is_hard_stop_active Naming
- **Severity:** HIGH
- **Category:** Code Quality
- **Source:** `src/loops/guardian.py` line 54-62
- **Expected:** Property name accurately reflects semantics
- **Actual:** `is_hard_stop_active` returns `self._hard_stop_handler.is_safe`. `is_safe=True` means HARD STOP is ACTIVE. Inverted naming.
- **Impact:** Maintenance hazard — developers may misinterpret the condition
- **Fix Recommendation:** Rename to match semantics or add explicit comment
- **Requires Mama Approval:** NO
- **Requires Runtime Restart:** NO
- **Classification:** IMPLEMENTED_WITH_BUG

### P5-BUG-009: 5 Dead Code Modules (700 lines)
- **Severity:** HIGH
- **Category:** Code Quality
- **Source:** `src/loops/enforcer.py`, `hash_anchor.py`, `sub_agent.py`, `contract.py`, `verify.py`
- **Expected:** All exported modules are used by production code
- **Actual:** These 5 modules are exported from `__init__.py` but have ZERO production callers
- **Impact:** 700 lines of unmaintained code, false impression of functionality
- **Fix Recommendation:** Either wire into production path or mark as deprecated/archived
- **Requires Mama Approval:** NO
- **Requires Runtime Restart:** NO
- **Classification:** DEAD_CODE

### P5-BUG-010: HermesBridge Dead Code
- **Severity:** HIGH
- **Category:** Architecture
- **Source:** `src/loops/hermes_bridge.py`
- **Expected:** Active bridge between Hermes and LoopManager
- **Actual:** main.py line 464 explicitly states "superseded by the Living Autonomy Kernel"
- **Impact:** Confusing dead code, false impression of Hermes integration
- **Fix Recommendation:** Remove from __init__.py exports or mark deprecated
- **Requires Mama Approval:** NO
- **Requires Runtime Restart:** NO
- **Classification:** SUPERSEDED_BY_LATER_PHASE

---

## MEDIUM

### P5-BUG-011: Raw Surveillance Data Flows Into Loop Signals
- **Severity:** MEDIUM
- **Category:** Privacy/Safety
- **Source:** `src/loops/discovery.py` lines 108-159
- **Expected:** Sanitized surveillance signals
- **Actual:** `raw_event=str(dict(row))` dumps entire row including `extracted_facts` JSONB
- **Impact:** Raw surveillance data available to LLM context
- **Fix Recommendation:** Sanitize signal metadata before entering loop
- **Requires Mama Approval:** YES (privacy boundary)
- **Requires Runtime Restart:** YES
- **Classification:** IMPLEMENTED_WITH_BUG

### P5-BUG-012: P19 Project ID Not Threaded Through LoopManager
- **Severity:** MEDIUM
- **Category:** Architecture
- **Source:** `src/loops/manager.py` line 66-67
- **Expected:** LoopManager.start_loop() accepts project_id
- **Actual:** No project_id parameter. P19 plumbing exists in context/audit/metrics but not through manager entry point
- **Impact:** Loops are global-scoped despite P19 project isolation
- **Fix Recommendation:** Add project_id to start_loop() and thread through LoopStateMachine
- **Requires Mama Approval:** YES
- **Requires Runtime Restart:** YES
- **Classification:** IMPLEMENTED_BUT_NOT_WIRED

### P5-BUG-013: Two Autonomous Brain Systems Without Priority Arbitration
- **Severity:** MEDIUM
- **Category:** Architecture
- **Source:** `src/core/main.py`
- **Expected:** Clear hierarchy between SDLC loop and life_kernel
- **Actual:** Both run concurrently in same process. No shared decision-making or priority arbitration.
- **Impact:** Resource contention, potential conflicting actions
- **Fix Recommendation:** Document explicit boundary or create coordination layer
- **Requires Mama Approval:** YES
- **Requires Runtime Restart:** NO
- **Classification:** NEEDS_OPERATOR_DECISION

### P5-BUG-014: Only 2/21 Source Files Have Dedicated Tests
- **Severity:** MEDIUM
- **Category:** Test Coverage
- **Source:** `tests/` directory
- **Expected:** Per-module test coverage for all 21 source files
- **Actual:** Only `state_machine.py` (test_T1) and `manager.py` (test_e2e_loop) have dedicated tests. 7 phase handlers have zero individual tests.
- **Impact:** Regressions in individual modules undetectable
- **Fix Recommendation:** Add unit tests for phase handlers, guardian, routes, and Discord commands
- **Requires Mama Approval:** NO
- **Requires Runtime Restart:** NO
- **Classification:** IMPLEMENTED_WITH_LOW_COVERAGE

### P5-BUG-015: SDLC Scheduler Timezone Inconsistency
- **Severity:** MEDIUM
- **Category:** Configuration
- **Source:** `src/loops/scheduler.py` line 13
- **Expected:** Consistent timezone across all schedulers
- **Actual:** SDLC scheduler uses `Asia/Bangkok`, persona uses `Asia/Jakarta`
- **Impact:** Potential scheduling confusion
- **Fix Recommendation:** Align to `Asia/Jakarta` (WIB) per operator timezone
- **Requires Mama Approval:** NO
- **Requires Runtime Restart:** YES
- **Classification:** IMPLEMENTED_WITH_BUG

---

## LOW

### P5-BUG-016: P4 Ritual Scheduler Not Removed (Deprecated Phase 7)
- **Severity:** LOW
- **Category:** Cleanup
- **Source:** `src/persona/ritual_scheduler.py`
- **Expected:** Module removed by Phase 7 per deprecation notice
- **Actual:** Module remains importable with `warnings.warn()` on every import
- **Impact:** Import warnings, dead code
- **Fix Recommendation:** Remove module or archive
- **Requires Mama Approval:** NO
- **Requires Runtime Restart:** NO
- **Classification:** STALE_EVIDENCE

### P5-BUG-017: Stale Phase 5 Documentation
- **Severity:** LOW
- **Category:** Documentation
- **Source:** `docs/setup-evidence/hermes-migration/phase-5-skills.md`, `batch-plan-phase-5.md`
- **Expected:** Documentation reflects current Hermes v0.15.2 CLI
- **Actual:** Contains `hermes plugin trigger` CLI commands not in Hermes v0.15.2
- **Impact:** Misleading documentation for operators/auditors
- **Fix Recommendation:** Update or annotate as historical
- **Requires Mama Approval:** NO
- **Requires Runtime Restart:** NO
- **Classification:** STALE_EVIDENCE

---

## COSMETIC

### P5-BUG-018: Large __init__.py Export Surface
- **Severity:** COSMETIC
- **Category:** Code Quality
- **Source:** `src/loops/__init__.py` (218 lines, 100+ exports)
- **Expected:** Lean public API
- **Actual:** Exports everything including dead code and superseded modules
- **Impact:** Import overhead, unclear public API surface
- **Fix Recommendation:** Trim to active-only exports
- **Requires Mama Approval:** NO
- **Requires Runtime Restart:** NO
- **Classification:** IMPLEMENTED_WITH_BUG (cosmetic)

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 5 |
| HIGH | 5 |
| MEDIUM | 5 |
| LOW | 2 |
| COSMETIC | 1 |
| **TOTAL** | **18** |
