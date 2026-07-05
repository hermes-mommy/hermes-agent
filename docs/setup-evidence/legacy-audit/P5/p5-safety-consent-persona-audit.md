# P5 Safety/Consent/Persona Audit

**Date:** 2026-06-27
**Auditor:** Sub-agent (source-code-only)
**Verdict:** FAIL — 7 critical gaps, 3 warnings

---

## 1. HARD STOP INTEGRITY

**Score: PARTIAL — wiring exists, semantic bug, no per-phase gate**

- HardStopHandler imported in `src/loops/guardian.py` (TYPE_CHECKING) and wired via `set_hard_stop_handler()` (line 44)
- `cancel_all_loops()` exists at `src/loops/manager.py` line 170
- LoopSafetyGate in `src/loops/safety_integration.py` exists but is NOT called from `_run_loop()`

**CRITICAL GAP:** `LoopManager._run_loop()` runs all 7 phases with NO safety gate between them. HARD STOP check runs only on the Guardian's 30-second monitoring tick. Up to 30 seconds of phase execution can occur AFTER HARD STOP triggered.

**Semantic bug:** `is_hard_stop_active` returns `self._hard_stop_handler.is_safe` — `is_safe=True` means HARD STOP is ACTIVE (inverted naming, maintenance hazard).

---

## 2. CONSENT BOUNDARY

**Score: FAIL — no programmatic enforcement**

- Consent mentioned in 3 places in loop code, all prompt-level only (`src/loops/prompts.py` lines 149-151, 100; `src/loops/context.py` line 91)
- No consent check before sub-agent spawning (`SubAgentSpawner.spawn()`)
- No mechanism to stop loop if consent revoked mid-execution
- The loop runs all 7 phases in a tight `for` loop with no external signal check

---

## 3. PERSONA SAFETY

**Score: FAIL — prompt-only, no code enforcement**

- System prompt contains 4 absolute NEVERs (prompt-level soft constraint)
- Zero references to "Y6" or escalation-level enforcement in loop code
- `TaskContract.must_not_do` is rendered as text only — no post-execution validation
- `LoopSafetyGate` does NOT check persona state — only HARD STOP and Redis flags

---

## 4. COST / BUDGET ENFORCEMENT

**Score: FAIL — three disconnected budget systems, main loop has NO guard**

| System | Location | Fail-Closed? | Used by Main Loop? |
|--------|----------|-------------|-------------------|
| LoopCostTracker | src/loops/cost.py | NO (returns 0.0 on Redis error) | Records after phase, no pre-check |
| IterationBudget | src/loops/budget.py | YES (raises BudgetExhaustedError) | NO — only used by ConversationLoop |
| CostTracker | src/core/services/cost_tracker.py | YES (returns HARD_STOP at 100%) | NO — never called from loop |
| BudgetManager | src/mcp/budget.py | YES (raises BudgetExceeded) | NO — only MCP layer |

**The main loop has NO budget guard between phases.** Cost is recorded AFTER each phase but never blocks.

---

## 5. SUB-AGENT SAFETY

**Score: FAIL — no programmatic enforcement**

- `TaskContract.must_not_do` is prompt-level only
- Sub-agents have NO sandbox, capability restriction, or secret-access prevention
- `OutputVerifier.verify_file_exists()` checks `Path(path).is_file()` only — does not read content
- `verify_command()` runs arbitrary shell via `subprocess.run`

---

## 6. SURVEILLANCE BOUNDARY

**Score: WARNING — raw data flows into signals**

- `SurveillanceCollector` in `discovery.py` reads from `surveillance.events` PG table
- `raw_event=str(dict(row))` dumps entire row dict including `extracted_facts` JSONB (may contain raw surveillance data)
- No programmatic sanitization before data enters loop signal stream

---

## 7. DISTRESS PROTOCOL

**Score: FAIL — not implemented**

- NO distress detection (D0-D4) anywhere in loop system
- `"distress"` exists as a signal type label in priority.py and trigger_source in context.py — classification only, not detection
- HardStopHandler has semantic patterns for safe-word triggers, not distress detection

---

## Classification

| Claim | Classification |
|-------|---------------|
| HARD STOP integrated in agent loop | IMPLEMENTED_BUT_NOT_DEWIRED_TO_PHASES |
| Consent boundary enforced | DOCS_ONLY (prompt-level) |
| Persona safety in agent loop | DOCS_ONLY (prompt-level) |
| Budget enforcement in agent loop | IMPLEMENTED_BUT_NOT_WIRED (IterationBudget exists, not used) |
| Sub-agent constraints enforced | DOCS_ONLY (prompt-level) |
| Distress detection in agent loop | DEAD_CODE (labels only, no detection) |
| Surveillance boundary in agent loop | IMPLEMENTED_WITH_BUG (raw data flow) |
