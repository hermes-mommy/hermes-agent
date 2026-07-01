# P5 Missing Docs Register

**Date:** 2026-06-27

---

## Missing Documentation

### MISSING-DOC-001: LoopManager Architecture Update
- **What's Missing:** No documentation reflecting that LoopManager is now a non-LLM task executor (llm_router=None) rather than the autonomous brain
- **Expected Location:** `docs/00-core/03-AgentLoopSpec_v2.0.md` or Phase 5 evidence
- **Impact:** Operators/auditors assume the loop is LLM-driven
- **Priority:** HIGH

### MISSING-DOC-002: Dual Autonomous System Architecture
- **What's Missing:** No document describing the coexistence of P5 LoopManager and P20 LifeKernel as two independent autonomous systems in the same process
- **Expected Location:** Architecture document or ADR
- **Impact:** Architectural confusion, no clear boundary documentation
- **Priority:** HIGH

### MISSING-DOC-003: Loop Safety Gate Integration Guide
- **What's Missing:** LoopSafetyGate exists but no documentation on how to wire it into `_run_loop()` or why it's not wired
- **Expected Location:** `src/loops/safety_integration.py` docstring or Phase 5 evidence
- **Impact:** Safety gap goes undocumented
- **Priority:** HIGH

### MISSING-DOC-004: Dead Code Register for src/loops/
- **What's Missing:** No register identifying the 5 dead code modules (enforcer, hash_anchor, sub_agent, contract, verify) and their intended purpose
- **Expected Location:** `docs/setup-evidence/P5/` or module docstrings
- **Impact:** 700 lines of dead code without explanation
- **Priority:** MEDIUM

### MISSING-DOC-005: Per-Module Test Coverage Report
- **What's Missing:** No per-module test coverage report showing 2/21 files tested
- **Expected Location:** `audit-reports/P5/`
- **Impact:** "205 passed" claim creates false impression of comprehensive testing
- **Priority:** MEDIUM

### MISSING-DOC-006: Hermes Plugin Loop Commands Documentation
- **What's Missing:** The 7 Hermes loop commands in `src/hermes_plugins/commands_loop/` are not documented in Phase 5 evidence
- **Expected Location:** Phase 5 evidence or hermes migration docs
- **Impact:** Production loop commands invisible to auditors
- **Priority:** MEDIUM

### MISSING-DOC-007: Loop Module Inventory (Beyond 23 Steps)
- **What's Missing:** No documentation listing the full 37+ modules in `src/loops/` beyond the original 23 steps
- **Expected Location:** Phase 5 evidence
- **Impact:** 14+ additional modules undocumented
- **Priority:** LOW
