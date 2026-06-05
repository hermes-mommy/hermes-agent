# Recheck Context — Phase 6 Cost & Budget Fix Recommendations (Auditor 6-1 / 6-2)

**Date:** 2026-06-05  
**Author:** Guinevere (Sisyphus-Junior — Research Agent)  
**Status:** PLANNING FIX ONLY — Zero Implementation  
**Audit Targets:** AUDIT-61-LLM-ROUTING (6-1), AUDIT-62-COST-ACCURACY (6-2)  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Fix 1: Empty Except in Step 6.3 (Auditor 6-1 Blocking)](#2-fix-1-empty-except-in-step-63-auditor-6-1-blocking)
3. [Fix 2: Add CostTracker Wiring Step (Auditor 6-2 Blocking)](#3-fix-2-add-costtracker-wiring-step-auditor-6-2-blocking)
4. [Fix 3: Update cost_per_1k Values in llm_router.py (Auditor 6-2 Blocking)](#4-fix-3-update-cost_per_1k-values-in-llm_routerpy-auditor-6-2-blocking)
5. [Fix 4: Fix Step 6.7 False Pre-condition (Auditor 6-2)](#5-fix-4-fix-step-67-false-pre-condition-auditor-6-2)
6. [Fix 5: Add Forbidden Grep to Step 6.3 Scaffold (Auditor 6-1)](#6-fix-5-add-forbidden-grep-to-step-63-scaffold-auditor-6-1)
7. [Fix 6: Add Cost_per_1k Grep to Step 6.7 Scaffold (Auditor 6-2)](#7-fix-6-add-cost_per_1k-grep-to-step-67-scaffold-auditor-6-2)
8. [Fix 7: Add End-to-End Budget Enforcement Test (Auditor 6-2)](#8-fix-7-add-end-to-end-budget-enforcement-test-auditor-6-2)
9. [Fix 8: Add Fallback Activation Test (Auditor 6-1)](#9-fix-8-add-fallback-activation-test-auditor-6-1)
10. [Fix 9: Update Caveat #5 in Design Decisions (Auditor 6-2)](#10-fix-9-update-caveat-5-in-design-decisions-auditor-6-2)
11. [Re-Audit PASS Criteria](#11-re-audit-pass-criteria)
12. [Application Order and Dependency Map](#12-application-order-and-dependency-map)

---

## 1. Executive Summary

| # | Issue | Audit | Severity | Location | Fix Type |
|---|-------|-------|----------|----------|----------|
| 1 | `except Exception: pass` in budget hook | 6-1 | **CRITICAL (blocking)** | `batch-plan-phase-6.md` lines 664-667 | Edit existing hook code |
| 2 | `llm_router.py` does not call `CostTracker.record_cost()` | 6-2 | **CRITICAL (blocking)** | `llm_router.py` lines 90-93 + new step | New Step 6.3b + edit llm_router.py |
| 3 | cost_per_1k values stale (off 1.4x-3x) | 6-2 | **HIGH (blocking)** | `llm_router.py` lines 35-36, 45-46, 53-54 | Numeric edit in llm_router.py |
| 4 | Step 6.7 pre-condition falsely claims `llm_router.py` calls `CostTracker` | 6-2 | **HIGH (misleading)** | `batch-plan-phase-6.md` line 1474 | Edit pre-condition text |
| 5 | No forbidden grep for empty except in Step 6.3 scaffold | 6-1 | **MEDIUM (self-violation)** | `batch-plan-phase-6.md` line 256 | Add forbidden grep pattern |
| 6 | No cost_per_1k validation grep in Step 6.7 scaffold | 6-2 | **MEDIUM** | `batch-plan-phase-6.md` line 260 | Add forbidden pattern check |
| 7 | No end-to-end budget enforcement test | 6-2 | **MEDIUM** | After Step 6.3 | Add sub-step OR step variant |
| 8 | No fallback activation test | 6-1 | **LOW (minor)** | After Step 6.5 | Add sub-step |
| 9 | Caveat #5 misleading: says dual-write but doesn't acknowledge missing call | 6-2 | **LOW (clarity)** | `batch-plan-phase-6.md` line 2110 | Edit caveat text |

**Total blocking: 4** (1 empty except, 2 CostTracker wiring, 1 stale prices).  
**Total non-blocking: 5** (cleanup/docs/scaffold reinforcement).

---

## 2. Fix 1: Empty Except in Step 6.3 (Auditor 6-1 Blocking)

### Source Location

**File:** `docs/setup-evidence/hermes-migration/batch-plan-phase-6.md`  
**Lines 664-667** (inside the budget hook code, `check_budget()` function, `BLOCK_THRESHOLD` branch):

```python
            try:
                r.incr(KEY_COST_COUNTER)
            except Exception:
                pass
```

### Exact Replacement

Replace **lines 664-667** with:

```python
            try:
                r.incr(KEY_COST_COUNTER)
            except Exception as exc:
                _LOG.error("block_counter_failed", error=str(exc))
```

### Why This Fix

- `_LOG` is already defined at line 625 (`_LOG = setup_logger('budget_hook')`)
- The `error` keyword arg matches structlog conventions used elsewhere in the hook (e.g., line 712: `_LOG.error('budget_check_failed', error=str(exc))`)
- Converts empty silent failure to logged failure — still fail-open (counter increment is non-critical) but visible in logs
- Complies with AGENTS.md BLOCKING rules and the Step 6.3 scaffold's own forbidden pattern

### Verification Command (for re-audit)

```bash
# Forbidden pattern: empty except — must return zero matches
grep -n "except Exception:" docs/setup-evidence/hermes-migration/batch-plan-phase-6.md | grep -v "as exc"
# Expected: Empty output (all except Exception lines use "as exc")
```

---

## 3. Fix 2: Add CostTracker Wiring Step (Auditor 6-2 Blocking)

### Context

Auditor 6-2 found zero references to `CostTracker`, `cost_tracker`, or `record_cost` in `llm_router.py`. The plan assumes cost tracking works from the LLM router layer, but the codebase does not wire it. The existing `CostTracker` class at `src/core/services/cost_tracker.py` (lines 25-43) has a clean `record_cost()` method that accepts `(model, input_tokens, output_tokens, cost_per_1k_input, cost_per_1k_output)` — exactly the data available in `llm_router.py.chat()`.

### Recommendation: New Step 6.3b — Wire CostTracker into llm_router.py

Insert a new step **between Step 6.3 (Budget Hook)** and **Step 6.4 (Register Hook)**.

**Step Number:** `Step 6.3b` (renumber existing 6.4 → 6.5, 6.5 → 6.6, etc.)  

**Rationale for position:**
1. Must happen AFTER Step 6.3 (budget hook file creation — both touch cost infrastructure)
2. Must happen BEFORE Step 6.7 (cost tracking verification — which depends on this wiring)
3. Can run parallel with 6.2 (fallback config) and 6.4 (hook registration) since it modifies `llm_router.py` which is not touched by those steps
4. Collision scan shows `llm_router.py` read-only during 6.5/6.6 — this is its only write

**If renumbering is too invasive, alternatively:** Insert as a new section `Step 6.3a` (CostTracker Wiring) before Step 6.7, but after step 6.4/6.5/6.6. This avoids renumbering.

**Recommended approach (lowest disruption):** Add as `Step 6.3a` right before Step 6.7. The dependency graph becomes:

```
Step 6.3 (Budget Hook) ──▶ Step 6.4 (Register Hook)
Step 6.5 (100-Prompt Test) ──▶ Step 6.3a (Wire CostTracker) ──▶ Step 6.7 (Cost Tracking Verification)
```

**Rationale for 6.3a position:** The CostTracker wiring modifies `llm_router.py` in the repo. It should happen AFTER the 100-prompt test creates `test_100_prompts.py` (so the test can be updated to verify cost recording) and BEFORE Step 6.7 queries Redis for cost keys.

### Exact Code Changes in llm_router.py

#### Change 1: Add import (after line 6, before line 7)

**File:** `src/core/services/llm_router.py`  
**Lines 1-9 (current):**
```python
"""LLM Router - Routes requests to appropriate models based on task type."""
import json
import re

import httpx
import structlog
from enum import Enum
from typing import Optional, Union
from dataclasses import dataclass
```

**Insert after line 6 (`import structlog`):**
```python
import os
from src.core.services.cost_tracker import CostTracker
```

#### Change 2: Add record_cost() call after successful response (between line 92 and line 93)

**File:** `src/core/services/llm_router.py`  
**Lines 90-93 (current):**
```python
                result = json.loads(raw)
                logger.info("llm_request", model=config.name,
                           tokens=result.get("usage", {}).get("total_tokens", 0))
                return result
```

**Replace with:**
```python
                result = json.loads(raw)
                logger.info("llm_request", model=config.name,
                           tokens=result.get("usage", {}).get("total_tokens", 0))
                # Record cost for budget enforcement
                usage = result.get("usage", {})
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)
                try:
                    ct = CostTracker()
                    ct.record_cost(
                        model=config.name,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        cost_per_1k_input=config.cost_per_1k_input,
                        cost_per_1k_output=config.cost_per_1k_output,
                    )
                except Exception as exc:
                    logger.warning("cost_track_failed", error=str(exc))
                return result
```

### New Step 6.3a Content Outline

The new step should include:

1. **Pre-conditions:** Step 6.5 complete (100-prompt test)
2. **Commands:**
   ```bash
   # 1. Add CostTracker import to llm_router.py
   ssh guinevere-vps "cd /home/guinevere/code/guinevere && \
     sed -i '6 a import os\nfrom src.core.services.cost_tracker import CostTracker' \
     src/core/services/llm_router.py"

   # 2. Add record_cost call after logger.info in chat() method
   # (Use Python insertion script for reliability)
   ssh guinevere-vps "cd /home/guinevere/code/guinevere && python3 << 'PYCOSTWIRE'
   with open('src/core/services/llm_router.py') as f:
       lines = f.readlines()

   # Find the return statement after logger.info in chat()
   insert_after = None
   for i, line in enumerate(lines):
       if 'tokens=result.get(\"usage\", {}).get(\"total_tokens\", 0))' in line:
           insert_after = i
           break

   if insert_after is not None:
       cost_block = '''                # Record cost for budget enforcement
               usage = result.get(\"usage\", {})
               input_tokens = usage.get(\"prompt_tokens\", 0)
               output_tokens = usage.get(\"completion_tokens\", 0)
               try:
                   ct = CostTracker()
                   ct.record_cost(
                       model=config.name,
                       input_tokens=input_tokens,
                       output_tokens=output_tokens,
                       cost_per_1k_input=config.cost_per_1k_input,
                       cost_per_1k_output=config.cost_per_1k_output,
                   )
               except Exception as exc:
                   logger.warning(\"cost_track_failed\", error=str(exc))
   '''
       indent = ' ' * 16  # 4 more than current indent level
       cost_block = cost_block.replace(' ' * 16, indent)
       lines.insert(insert_after + 1, cost_block)

       with open('src/core/services/llm_router.py', 'w') as f:
           f.writelines(lines)
       print('OK: CostTracker record_cost inserted')
   else:
       print('ERROR: Could not find insertion point')
   PYCOSTWIRE"

   # 3. Verify syntax
   ssh guinevere-vps "cd /home/guinevere/code/guinevere && \
     python3 -m py_compile src/core/services/llm_router.py && echo 'SYNTAX: OK'"
   ```

3. **Verification:**
   ```bash
   # V-6.3a.1: CostTracker import present
   ssh guinevere-vps "cd /home/guinevere/code/guinevere && \
     grep -n 'CostTracker\|record_cost\|cost_tracker' src/core/services/llm_router.py"
   # Expected: At least 2 lines (import + call)

   # V-6.3a.2: Syntax check passes
   ssh guinevere-vps "cd /home/guinevere/code/guinevere && \
     python3 -m py_compile src/core/services/llm_router.py && echo 'SYNTAX: OK'"
   ```

4. **Scaffold forbidden patterns:**
   - `as any` — zero matches
   - `# type: ignore` — zero matches
   - empty `except:` — zero matches
   - `CostTracker` NOT in file — **must FAIL (must be present)**

---

## 4. Fix 3: Update cost_per_1k Values in llm_router.py (Auditor 6-2 Blocking)

### Source Location

**File:** `src/core/services/llm_router.py`

| Line(s) | Current Value | Correct Value (plan rate ÷ 1000) |
|---------|---------------|----------------------------------|
| 35 | `cost_per_1k_input=0.0025` | `cost_per_1k_input=0.005` (GPT-5.5 input $5/1M) |
| 36 | `cost_per_1k_output=0.01` | `cost_per_1k_output=0.03` (GPT-5.5 output $30/1M) |
| 45 | `cost_per_1k_input=0.0001` | `cost_per_1k_input=0.00014` (DeepSeek input $0.14/1M) |
| 46 | `cost_per_1k_output=0.0002` | `cost_per_1k_output=0.00028` (DeepSeek output $0.28/1M) |
| 53 | `cost_per_1k_input=0.0001` | `cost_per_1k_input=0.00014` (FALLBACK mirrors DeepSeek) |
| 54 | `cost_per_1k_output=0.0002` | `cost_per_1k_output=0.00028` (FALLBACK mirrors DeepSeek) |

### Exact Edits

All changes in `src/core/services/llm_router.py`:

| Line | Old Text | New Text |
|------|----------|----------|
| 35 | `cost_per_1k_input=0.0025,` | `cost_per_1k_input=0.005,` |
| 36 | `cost_per_1k_output=0.01,` | `cost_per_1k_output=0.03,` |
| 45 | `cost_per_1k_input=0.0001,` | `cost_per_1k_input=0.00014,` |
| 46 | `cost_per_1k_output=0.0002,` | `cost_per_1k_output=0.00028,` |
| 53 | `cost_per_1k_input=0.0001,` | `cost_per_1k_input=0.00014,` |
| 54 | `cost_per_1k_output=0.0002,` | `cost_per_1k_output=0.00028,` |

### Verification Command (for re-audit)

```bash
# Verify llm_router.py cost_per_1k values match plan pricing (÷1000)
ssh guinevere-vps "cd /home/guinevere/code/guinevere && \
  python3 -c \"
import sys
sys.path.insert(0, '.')
from src.core.services.llm_router import MODELS, TaskType

# Expected from plan: $5/$30 per 1M for GPT-5.5, $0.14/$0.28 per 1M for DeepSeek
# Per 1K: divide by 1000
expected = {
    TaskType.CORE_REASONING: {'input': 0.005, 'output': 0.03},
    TaskType.SUB_AGENT: {'input': 0.00014, 'output': 0.00028},
    TaskType.FALLBACK: {'input': 0.00014, 'output': 0.00028},
}

all_ok = True
for tt, mc in MODELS.items():
    exp = expected[tt]
    errs = []
    if abs(mc.cost_per_1k_input - exp['input']) > 1e-6:
        errs.append(f'input: got {mc.cost_per_1k_input}, expected {exp[\"input\"]}')
    if abs(mc.cost_per_1k_output - exp['output']) > 1e-6:
        errs.append(f'output: got {mc.cost_per_1k_output}, expected {exp[\"output\"]}')
    if errs:
        print(f'FAIL: {tt.value} — {\"; \".join(errs)}')
        all_ok = False
    else:
        print(f'PASS: {tt.value} — input={mc.cost_per_1k_input}, output={mc.cost_per_1k_output}')

if not all_ok:
    sys.exit(1)
print('ALL PASS: cost_per_1k values match plan pricing')
\""
```

---

## 5. Fix 4: Fix Step 6.7 False Pre-condition (Auditor 6-2)

### Source Location

**File:** `docs/setup-evidence/hermes-migration/batch-plan-phase-6.md`  
**Line 1474** (Step 6.7 pre-conditions):

```
- [ ] `cost_tracker.py` instrumented and called by `llm_router.py`
```

### Problem

This statement is currently **false** — `llm_router.py` does NOT call `CostTracker`. Unless Fix 2 (new Step 6.3a) is applied before Step 6.7 executes, this precondition cannot be satisfied.

### Exact Replacement

Replace **line 1474** with:

```
- [ ] Step 6.3a complete — `CostTracker.record_cost()` wired into `llm_router.py.chat()`
```

This makes the precondition depend on the new wiring step, creating a clear execution guard.

---

## 6. Fix 5: Add Forbidden Grep to Step 6.3 Scaffold (Auditor 6-1)

### Source Location

**File:** `docs/setup-evidence/hermes-migration/batch-plan-phase-6.md`  
**Line 256** (Per-Step Verification Scaffold Summary, Step 6.3 row):

```
| **6.3** | `~/.hermes/hooks/budget.py` (created) | `as any`, `# type: ignore`, empty `except` | `python3 -m py_compile`, pytest | `phase-6/STEP-6.3/verification.md` |
```

### Problem

The scaffold forbids "empty `except`" as a pattern, but doesn't provide a **grep command** to enforce it. Auditor 6-1 flagged this as a self-violation because the hook code itself contained an empty except that a simple grep would have caught.

### Recommended Change

Update the "Required Commands" column to include the grep command:

```
| **6.3** | `~/.hermes/hooks/budget.py` (created) | `as any`, `# type: ignore`, empty `except` | `python3 -m py_compile`, `pytest`, `grep -n "except Exception:" hooks/budget.py \| grep -v "as exc" \|\| echo "clean"` | `phase-6/STEP-6.3/verification.md` |
```

Also, in the Step 6.3 Verification section (around line 797), add a new verification check:

```bash
# V-6.3.6: No empty except blocks (AGENTS.md BLOCKING rule)
ssh guinevere-vps "grep -n 'except Exception:' ~/.hermes/hooks/budget.py | grep -v 'as exc'"
# Expected: Empty output (all except blocks use "as exc")
```

---

## 7. Fix 6: Add Cost_per_1k Grep to Step 6.7 Scaffold (Auditor 6-2)

### Source Location

**File:** `docs/setup-evidence/hermes-migration/batch-plan-phase-6.md`  
**Line 260** (Per-Step Verification Scaffold Summary, Step 6.7 row):

```
| **6.7** | N/A (verification only) | N/A | `redis-cli` queries, cost diff | `phase-6/STEP-6.7/verification.md` |
```

### Recommended Change

Update to add cost_per_1k validation as a required command:

```
| **6.7** | N/A (verification only) | cost_per_1k values NOT matching plan pricing | `redis-cli` queries, cost diff, `python3 -c "..." cost_per_1k check` | `phase-6/STEP-6.7/verification.md` |
```

Also add a verification command in Step 6.7:

```bash
# V-6.7.6: llm_router.py cost_per_1k values match plan pricing
ssh guinevere-vps "cd /home/guinevere/code/guinevere && \
  python3 -c \"
from src.core.services.llm_router import MODELS, TaskType
expected = {
    TaskType.CORE_REASONING: (0.005, 0.03),
    TaskType.SUB_AGENT: (0.00014, 0.00028),
    TaskType.FALLBACK: (0.00014, 0.00028),
}
for tt, mc in MODELS.items():
    exp_in, exp_out = expected[tt]
    assert abs(mc.cost_per_1k_input - exp_in) < 1e-6, f'{tt.value} input mismatch: {mc.cost_per_1k_input} != {exp_in}'
    assert abs(mc.cost_per_1k_output - exp_out) < 1e-6, f'{tt.value} output mismatch: {mc.cost_per_1k_output} != {exp_out}'
print('PASS: All cost_per_1k values match plan pricing')
\""
```

---

## 8. Fix 7: Add End-to-End Budget Enforcement Test (Auditor 6-2)

### Context

Auditor 6-2 flagged that budget enforcement is only tested in isolation (subprocess hook call), not end-to-end through Hermes. Add a sub-step after Step 6.3 (or Step 6.5) that verifies the full pipeline.

### Recommended Location

Insert at the end of Step 6.5 (or as a new sub-step `6.5a`), after the 100-prompt test completes but before cost tracking verification:

```bash
# Budget enforcement end-to-end test
# 1. Temporarily lower cap to $0.01 to force block
ssh guinevere-vps "redis-cli -p 6380 -n 5 SET budget:monthly_cap 0.01"

# 2. Make a single LLM call through Hermes (should be blocked by hook)
ssh guinevere-vps "hermes model test --prompt 'Say OK' --max-tokens 5 2>&1"
# Expected: Error or block message (hook returns exit 1)

# 3. Verify block counter incremented
ssh guinevere-vps "redis-cli -p 6380 -n 5 GET budget:block_counter"
# Expected: "1" or higher

# 4. Reset cap
ssh guinevere-vps "redis-cli -p 6380 -n 5 SET budget:monthly_cap 30"
```

### Verification

```bash
# V-6.5.X: Budget enforcement blocks LLM call when cap exceeded
# (Manual check — test output shows block/error)
# Expected: Hermes model test returns error (budget blocked)
```

---

## 9. Fix 8: Add Fallback Activation Test (Auditor 6-1)

### Context

Auditor 6-1 flagged that the fallback chain is configured but never tested for actual activation. Add a sub-step in Step 6.5 that temporarily configures an invalid primary model to trigger fallback.

### Recommended Location

Add to Step 6.5 commands after the 100-prompt test:

```bash
# Fallback activation test: temporarily use invalid model to trigger fallback
ssh guinevere-vps 'curl -s http://localhost:20128/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $NINEROUTER_API_KEY" \
  -d "{\"model\":\"ds/nonexistent-model\",\"messages\":[{\"role\":\"user\",\"content\":\"OK\"}],\"max_tokens\":5}" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
# Should either return an error (9Router doesn't have model)
# or fall through to next provider
print('Status:', d.get('error', 'no error (unexpected)'))
print('Note: Fallback activation depends on 9Router error behavior')
"'
```

---

## 10. Fix 9: Update Caveat #5 in Design Decisions (Auditor 6-2)

### Source Location

**File:** `docs/setup-evidence/hermes-migration/batch-plan-phase-6.md`  
**Lines 2110** (Caveat #5):

```
5. **Cost tracking dual-write**: `llm_router.py` writes to Redis DB5 via `cost_tracker.py`. The budget hook reads from the same Redis keys. If `llm_router.py` is bypassed (e.g., Hermes makes direct LLM calls), cost tracking will be incomplete.
```

### Problem

This caveat describes a scenario where `llm_router.py` exists but is bypassed. The real problem (before Fix 2) was that `llm_router.py` doesn't call `CostTracker` at all. After Fix 2, the caveat becomes accurate, but should also acknowledge the new wiring dependency.

### Recommended Replacement

```
5. **Cost tracking via llm_router.py**: After Step 6.3a, `llm_router.py.chat()` calls `CostTracker.record_cost()` which writes to Redis DB5 keys (`cost:current_month`, `cost:by_model:*`, etc.). The budget hook in Step 6.3 reads from the same keys. If `llm_router.py` is bypassed (e.g., Hermes makes direct LLM calls), cost tracking will be incomplete.
```

---

## 11. Re-Audit PASS Criteria

### Auditor 6-1 (LLM Routing Correctness) — PASS Criteria

| Check | Command / Criterion | Expected |
|-------|---------------------|----------|
| **3a (CRITICAL): Empty except fixed** | `grep -n "except Exception:" docs/setup-evidence/hermes-migration/batch-plan-phase-6.md \| grep -v "as exc"` | **Zero matches** (Fix 1 applied) |
| **3a follow-up: grep in hook file** | `grep -n "except Exception:" ~/.hermes/hooks/budget.py \| grep -v "as exc"` | **Zero matches** (Fix 1 applied) |
| **2b: Fallback activation test** | Step 6.5 fallback test sub-step exists | Test with invalid model present |
| **4c: Direct-provider grep** | `grep -rE "api\.(openai\|deepseek\|anthropic)\.com" src/ hermes-config/` | Zero matches |
| **1b: Hermes auth verified** | `grep "key_env" ~/.hermes/config.yaml` shows `NINEROUTER_API_KEY` | At least 1 match |
| **Step 6.3 scaffold updated** | Scaffold table row for Step 6.3 includes grep command | Command present |

**FINAL PASS** for 6-1 requires:
1. ✅ Fix 1 applied (empty except → logged)
2. ✅ Fix 5 applied (scaffold grep command)
3. ✅ Fix 8 applied (fallback activation test)
4. ✅ Direct-provider grep returns zero
5. ✅ No other BLOCKING violations

### Auditor 6-2 (Cost Tracking & Budget Accuracy) — PASS Criteria

| Check | Command / Criterion | Expected |
|-------|---------------------|----------|
| **2.3 (CRITICAL): CostTracker wired** | `grep -c "CostTracker\|record_cost" src/core/services/llm_router.py` | **≥ 2 matches** (import + call), Fix 2 applied |
| **5.1 (HIGH): cost_per_1k correct** | Python verification script (see Fix 3) | ALL PASS for all 3 TaskTypes |
| **2.1: Step 6.7 pre-condition accurate** | Line 1474 text references "Step 6.3a" | Fix 4 applied |
| **3.3 (MEDIUM): End-to-end test** | Step 6.5 contains budget enforcement sub-step | Test present (Fix 7 applied) |
| **4.4: Cost optimization** | Caveat #5 updated to reflect wiring | Fix 9 applied |
| **cost_per_1k scaffold check** | Step 6.7 scaffold forbids stale values | Fix 6 applied |

**FINAL PASS** for 6-2 requires:
1. ✅ Fix 2 applied (CostTracker wiring step exists AND code deployed)
2. ✅ Fix 3 applied (cost_per_1k values corrected)
3. ✅ Fix 4 applied (pre-condition fixed)
4. ✅ Fix 7 applied (end-to-end test)
5. ✅ Fix 6 + Fix 9 applied (scaffold + caveat)

---

## 12. Application Order and Dependency Map

### Fix Application Sequence

```
Fixes 1, 3 ──▶ Fix 5, 6, 9 ──▶ Fix 4 ──▶ Fix 2 ──▶ Fix 7, 8
 (edit plan)    (scaffolds)    (pre-con)  (new step) (sub-steps)
```

**Detailed:**

| Order | Fix | What | File(s) | Can Parallel? |
|-------|-----|------|---------|---------------|
| 1 | **Fix 1** | Replace empty except with logged handler | `batch-plan-phase-6.md` only | Yes (with 3, 5, 6, 9) |
| 2 | **Fix 3** | Update cost_per_1k values | `llm_router.py` only | Yes (with 1, 5, 6, 9) |
| 3 | **Fix 5** | Add forbidden grep to Step 6.3 scaffold | `batch-plan-phase-6.md` only | Yes (with 1, 3, 6, 9) |
| 4 | **Fix 6** | Add cost_per_1k check to Step 6.7 scaffold | `batch-plan-phase-6.md` only | Yes (with 1, 3, 5, 9) |
| 5 | **Fix 9** | Update Caveat #5 text | `batch-plan-phase-6.md` only | Yes (with 1, 3, 5, 6) |
| 6 | **Fix 4** | Update Step 6.7 pre-condition | `batch-plan-phase-6.md` only | Sequential (after Fix 2 planned) |
| 7 | **Fix 2** | Add new Step 6.3a + Wire CostTracker | `batch-plan-phase-6.md` + `llm_router.py` | Sequential (after 1-6) |
| 8 | **Fix 7** | Add end-to-end budget test sub-step | `batch-plan-phase-6.md` only | With 8 (independent) |
| 9 | **Fix 8** | Add fallback activation test sub-step | `batch-plan-phase-6.md` only | With 7 (independent) |

### Execution Strategy

**Wave 1 (background parallel, 5 agents):** Fix 1, Fix 3, Fix 5, Fix 6, Fix 9  
**Wave 2 (sequential):** Fix 4 (depends on Fix 2 being planned)  
**Wave 3 (background parallel, 2 agents):** Fix 7, Fix 8 (independent sub-steps)  
**Wave 4 (single):** Fix 2 (new step insertion — highest collision risk, needs parent-only write)

---

## Appendix A: Exact Grep Commands for Re-Auditors

### Forbidden Grep Command (Auditor 6-1 — Empty Except)

```bash
grep -rn "except Exception:" docs/setup-evidence/hermes-migration/batch-plan-phase-6.md
# Then inspect each match — none should have bare ": pass" without "as exc"
```

**Expected result after fix:** All matches include `as exc`.

### CostTracker Presence Grep (Auditor 6-2 — Wiring)

```bash
grep -c "CostTracker\|record_cost" src/core/services/llm_router.py
```

**Expected result after fix:** `≥ 2`

### cost_per_1k Validation Grep (Auditor 6-2 — Pricing)

```bash
python3 -c "
from src.core.services.llm_router import MODELS, TaskType
expected = {
    TaskType.CORE_REASONING: (0.005, 0.03),
    TaskType.SUB_AGENT: (0.00014, 0.00028),
    TaskType.FALLBACK: (0.00014, 0.00028),
}
for tt, mc in MODELS.items():
    e_in, e_out = expected[tt]
    assert abs(mc.cost_per_1k_input - e_in) < 1e-6
    assert abs(mc.cost_per_1k_output - e_out) < 1e-6
print('ALL PASS')
"
```

**Expected result:** `ALL PASS`

### Direct Provider Grep (Auditor 6-1 — Safety)

```bash
grep -rE "api\.(openai|deepseek|anthropic)\.com" src/ hermes-config/ || echo "CLEAN: zero matches"
```

**Expected result:** `CLEAN: zero matches`

---

## Appendix B: File Change Summary

| File | Change Type | Lines Affected | Priority |
|------|-------------|----------------|----------|
| `batch-plan-phase-6.md` | Edit (Fix 1 — empty except) | Lines 664-667 | ✅ BLOCKING |
| `batch-plan-phase-6.md` | Edit (Fix 4 — pre-condition) | Line 1474 | ✅ BLOCKING |
| `batch-plan-phase-6.md` | Edit (Fix 5 — scaffold) | Line 256 | MEDIUM |
| `batch-plan-phase-6.md` | Edit (Fix 6 — scaffold) | Line 260 | MEDIUM |
| `batch-plan-phase-6.md` | Edit (Fix 9 — caveat) | Line 2110 | LOW |
| `batch-plan-phase-6.md` | Insert (Fix 2 — new Step 6.3a) | After Step 6.7 section or between 6.3/6.4 | ✅ BLOCKING |
| `batch-plan-phase-6.md` | Insert (Fix 7 — budget test sub-step) | In Step 6.5 | MEDIUM |
| `batch-plan-phase-6.md` | Insert (Fix 8 — fallback test sub-step) | In Step 6.5 | LOW |
| `src/core/services/llm_router.py` | Edit (Fix 2 — import + record_cost call) | After line 6 + between 92-93 | ✅ BLOCKING |
| `src/core/services/llm_router.py` | Edit (Fix 3 — cost_per_1k values) | Lines 35, 36, 45, 46, 53, 54 | ✅ BLOCKING |

**Total:** 10 changes across 2 files. 4 BLOCKING, 2 MEDIUM, 2 LOW.
