# P5 Docs/Evidence Consistency Audit

**Date:** 2026-06-27

---

## Evidence Files Inventory

| Directory | File Count | Description |
|-----------|-----------|-------------|
| `docs/setup-evidence/phase-5/` | 37 files | ADR-035 Phase 5 enhancements (SOUL.md, skills, PersonaPlugin, cron, v2 verifications) |
| `docs/setup-evidence/phase5-verification/` | 18 files | T1-T10 verification gates + 3 auditor gates + 3 FIX verifications |
| `evidence/phase-5.5/` | 10 files | P5.5 remediation (FIX-01 through FIX-10) |
| `audit-reports/P5/` | 21 files | P5 Final Audit (12 dimensions D01-D12) + 6 re-audits + P5.5 re-audit synthesis |
| `docs/setup-evidence/hermes-migration/phase-5-skills.md` | 1 file | Phase 5 skills/procedure document |
| **TOTAL** | **87 files** | |

---

## Consistency Checks

### CLAIM-001: "205 passed" verification suite
- **Source:** PROGRESS.md Phase 5 verification section
- **Evidence:** `docs/setup-evidence/phase5-verification/VERIFICATION-SUMMARY.md`
- **Consistent?** YES — the T1-T10 verification suite did pass 205 tests
- **Caveat:** This is a local deterministic verification suite, not per-module unit tests. The 205 tests cover functional/technical/safety gates, not individual module test coverage.

### CLAIM-002: "22/22 files exist" (from source inventory)
- **Source:** P5-001 through P5-023 claimed files
- **Evidence:** All 23 files (21 source + 2 systemd) confirmed via glob/read
- **Consistent?** YES — all claimed files exist

### CLAIM-003: "E2E 17/17 PASS" 
- **Source:** PROGRESS.md P5-022
- **Evidence:** `tests/test_e2e_loop.py`
- **Consistent?** PARTIAL — test file exists and is structured for 17 test cases, but `asyncio_mode = "auto"` was added in P5.5 FIX-03. Pre-fix, the test failed via pytest (F-03 in re-audit).

### CLAIM-004: "1449 tests passed" (P4 persona)
- **Source:** PROGRESS.md P4 section
- **Evidence:** P4 batch plan + remediation
- **Consistent?** YES — P4 tests are separate from P5 tests

### CLAIM-005: "LoopSafetyGate" safety integration
- **Source:** `src/loops/safety_integration.py` exists
- **Evidence:** Module exists with LoopSafetyGate class
- **Consistent?** MISLEADING — the module exists but is NOT called from `_run_loop()`. Documenting its existence implies it's active.

### CLAIM-006: "HardStopHandler integrated in agent loop"
- **Source:** P5 re-audit F-05
- **Evidence:** `guardian.py` has `set_hard_stop_handler()` and `is_hard_stop_active`
- **Consistent?** PARTIAL — HardStopHandler IS wired to guardian (30-second tick check), but NOT checked between phases in `_run_loop()`

### CLAIM-007: "DB persistence via LoopInstances table"
- **Source:** P5 re-audit F-04
- **Evidence:** `manager.py` imports from `src.memory.models` (LoopInstances)
- **Consistent?** YES — loop state persists to PostgreSQL

### CLAIM-008: "10 callers → HTTP API calls" (F-01 fix)
- **Source:** P5 re-audit F-01
- **Evidence:** Hermes plugin commands use httpx calls to routes.py endpoints
- **Consistent?** YES — `src/hermes_plugins/commands_loop/*.py` all use httpx

### CLAIM-009: "ADR-035 Phase 5 enhancements complete"
- **Source:** PROGRESS.md ADR-035 section
- **Evidence:** `docs/setup-evidence/phase-5/evidence-phase-5.md` — 17 PASS / 1 PASS-RESCOPED
- **Consistent?** YES — verified with v2 auditors

### CLAIM-010: "Phase 5 is the autonomous brain"
- **Source:** `src/loops/__init__.py` docstring: "7-phase autonomous SDLC engine"
- **Evidence:** `main.py` line 103: `LoopManager(llm_router=None)`
- **Consistent?** **NO — CONTRADICTED.** The loop is LLM-dead. P20's life_kernel is the active autonomous brain.

---

## Overclaims

| # | Overclaim | Evidence | Severity |
|---|-----------|----------|----------|
| 1 | "7-phase autonomous SDLC engine" | llm_router=None, phase handlers generate fallback artifacts | HIGH |
| 2 | "LoopSafetyGate" implies active safety | Module exists but NOT called from _run_loop() | HIGH |
| 3 | "consent boundaries" enforced | Prompt-level text only, no code enforcement | CRITICAL |
| 4 | "Cost tracking per loop" implies budget enforcement | Cost recorded but never blocks | HIGH |
| 5 | "Sub-agent task contract" implies constraint enforcement | Prompt-level text only | MEDIUM |
| 6 | "205 passed" implies comprehensive testing | Per-module coverage is 2/21 | MEDIUM |

---

## Stale Evidence

| # | Evidence | Why Stale |
|---|----------|-----------|
| 1 | `batch-plan-phase-5.md` | Superseded by v1.1 planner + v2 evidence |
| 2 | `phase-5-skills.md` CLI commands | `hermes plugin trigger` not in Hermes v0.15.2 |
| 3 | `ritual_scheduler.py` deprecation timeline | "Phase 7 removal" not executed |
| 4 | HermesBridge references in evidence | Superseded by Living Autonomy Kernel |
| 5 | "autonomous" claims in Phase 5 scope | llm_router=None makes it non-autonomous |
