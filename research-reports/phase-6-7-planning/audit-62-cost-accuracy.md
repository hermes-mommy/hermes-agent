# Audit Report: Cost Tracking & Budget Accuracy (Auditor 6-2)

**Auditor:** 6-2 (Phase 6 -- LLM Routing)
**Date:** 2026-06-05
**Scope:** Cost tracking per model, Redis DB5 updates, monthly budget alerts, token cost realism
**Governing Docs:** ADR-035 Phase 6, ADR-004, ADR-005
**Sources Examined:**
- docs/setup-evidence/hermes-migration/batch-plan-phase-6.md
- research-reports/phase-6-7-planning/01-llm-state.md
- research-reports/phase-6-7-planning/08-token-cost.md
- src/core/services/cost_tracker.py
- src/core/services/llm_router.py
---

## Executive Summary

| Section | Verdict |
|---------|---------|
| 1. Cost tracking per model | **PASS** |
| 2. Redis DB5 updated after each LLM call | **FAIL** -- critical gap in llm_router.py |
| 3. Monthly budget alerts (80%/100%) | **PASS** -- thresholds correct |
| 4. Budget enforcement end-to-end test | **NEEDS_REVIEW** -- missing integrated test |
| 5. Token costs realistic | **NEEDS_REVIEW** -- cost_per_1k mismatch with llm_router.py |
| **FINAL VERDICT** | **NEEDS_REVIEW** -- 3 blocking items must be fixed |

---

## Detailed Checklist

### 1. Cost Tracking Per Model

#### 1.1 Does plan track cost per model (deepseek vs gpt-5.5 vs guinevere)?

**FINDING:** PASS -- The plan tracks all three models.

The plan's **1.5 Model Pricing Reference** (lines 81-90) and **Step 6.7** cost calculation (lines 1539-1551) cover all three models:

| Model | Plan Input | Plan Output |
|---|---|---|
| DeepSeek V4 Flash | \.14/1M | \.28/1M |
| GPT-5.5 | \.00/1M | \.00/1M |
| 9Router | Free (MIT) | Free |

The per-model breakdown is also explicit in **Step 6.7** verification commands that check cost:by_model:* keys in Redis DB5 (lines 1561-1563).

---

#### 1.2 Are costs broken down by input/output tokens?

**FINDING:** PASS -- The plan's pricing table distinguishes cache miss, cache hit, and output costs per model.

However, **Step 6.7**'s cost estimation for 100 prompts (lines 1539-1551) uses a simplified 50/50 input/output split without accounting for cache hits, while the research report 08-token-cost.md (lines 31-34) uses a more realistic 70/30 ratio with 50% cache hit rate. The plan's calculation is a minor simplification -- acceptable for estimation purposes but the difference is material:

- Plan calc (50/50, no cache): ~\.0021 for 100 prompts
- Research calc (70/30, 50% cache): ~\.0011 (about half)

**Note:** The simplification is documented and acceptable for estimation. The actual token counts from the 100-prompt test will be used for verification, not the estimate.

---

#### 1.3 Are prices realistic (\.14/\.28 DeepSeek, \/\ GPT-5.5)?

**FINDING:** PASS -- Prices match the research report 08-token-cost.md exactly.

Cross-reference:
- Plan 1.5 (lines 84-85): DeepSeek \.14/1M input, \.28/1M output
- Research report 1 (line 12): DeepSeek \.14/1M input, \.28/1M output -- Match
- Plan 1.5 (line 86): GPT-5.5 \.00/1M input, \.00/1M output
- Research report 1 (line 13): GPT-5.5 \.00/1M input, \.00/1M output -- Match

DeepSeek V4 Flash pricing is current as of June 2026 with the 98% cache-hit discount reflected.

---

### 2. Redis DB5 Updated?

#### 2.1 Does plan verify Redis DB5 is updated after each LLM call?

**FINDING:** PASS -- **Step 6.7** (lines 1478-1588) explicitly verifies Redis DB5 keys after the 100-prompt test run:

- V-6.7.1: Verifies cost:current_month exists and is non-zero
- V-6.7.2: Verifies per-model breakdown key cost:by_model:ds/deepseek-v4-flash
- V-6.7.3: Verifies budget check returns valid status (NORMAL/remaining/used%)
- V-6.7.4: Verifies daily cost entries exist
- V-6.7.5: Verifies model selection logging

---

#### 2.2 Is cost tracking code already in cost_tracker.py?

**FINDING:** PASS -- cost_tracker.py (68 lines) at src/core/services/cost_tracker.py exists and is fully instrumented:

- record_cost() writes to Redis DB5 keys: cost:current_month, cost:current_day, cost:by_model:{model}, cost:daily:{today}, cost:monthly:{month} (lines 34-39)
- Uses pipeline() / incrbyfloat for atomic writes
- check_budget() reads Redis keys to return status with alert levels (NORMAL, NORMAL_ALERT, WARNING, CRITICAL, HARD_STOP)

---

#### 2.3 Does plan use existing cost tracking infrastructure?

**FINDING:** FAIL -- **CRITICAL GAP** -- The plan assumes llm_router.py calls CostTracker.record_cost(), but this is **NOT TRUE** in the current codebase.

Evidence:
- llm_router.py (104 lines) contains **zero references** to CostTracker, cost_tracker, or record_cost. Grep confirmed 0 matches across the entire file.
- llm_router.py's chat() method (lines 64-101) logs the call via structlog but never invokes CostTracker.record_cost().
- Cost tracking IS implemented in:
  - src/discord/conversational_handler.py (lines 557-569)
  - src/discord/hermes_conversational.py (lines 612-625)
  - src/loops/cost.py (line 118)
  - src/mcp/tools/brave_search.py (line 171)
  - src/mcp/tools/exa_search.py (line 177)
- BUT NOT in src/core/services/llm_router.py

**Impact:** If Hermes routes LLM calls through llm_router.py -- which is the plan's stated architecture for Phase 6 -- costs will **not** be recorded in Redis DB5. Step 6.7's verification would fail because cost:current_month would remain at 0 after the 100-prompt test.

The plan's **Step 6.7 pre-condition** states: "cost_tracker.py instrumented and called by llm_router.py" -- this is **false** and would block Step 6.7 from passing.

**Design Decisions and Caveats 19.2** (line 2110) acknowledges: "If llm_router.py is bypassed (e.g., Hermes makes direct LLM calls), cost tracking will be incomplete" -- but this caveat describes a different scenario (bypassing llm_router.py), not the missing call within llm_router.py itself.

**Remediation required before Phase 6 execution:**
1. Add CostTracker.record_cost() call inside llm_router.py's chat() method after successful response, OR
2. Update the plan to acknowledge cost tracking is done at the Discord handler/loop level (not llm_router) and adjust Step 6.7 accordingly.

---

### 3. Monthly Budget Alerts

#### 3.1 Does plan set 80% alert threshold?

**FINDING:** PASS -- The plan's budget hook code (budget.py, lines 627-631) defines:

MONTHLY_LIMIT = 30.00
ALERT_THRESHOLD = 0.80    (80% = \.00)
BLOCK_THRESHOLD = 1.00    (100% = \.00)

The 80% alert threshold triggers a WARN action (action='warn', exit code 2) at \.00+, logging the budget alert. The hook code also logs a BUDGET_WARN structlog event with ratio and spend data (lines 695-696).

---

#### 3.2 Does plan set 100% block threshold?

**FINDING:** PASS -- BLOCK_THRESHOLD = 1.00 (\.00+) triggers a BLOCK action (action='block', exit code 1) that rejects all LLM calls. The block also increments a Redis counter budget:block_counter for monitoring (lines 664-667).

---

#### 3.3 Does plan test budget enforcement end-to-end?

**FINDING:** NEEDS_REVIEW -- The plan tests the budget hook in isolation but not end-to-end.

**What exists:**
- V-6.3.5 (lines 812-817): Sets cap to \.01 via Redis, runs hook subprocess, verifies exit code 1, resets cap. Tests the Python logic in isolation.
- Lines 767-792: Dry-run test calling budget.py as a subprocess with mock stdin. Tests the hook contract but not Hermes integration.

**What's missing:**
- No test that Hermes actually invokes the pre_tool_call hook during a real LLM call
- No test that the budget enforcement blocks/skips the actual LLM request at the gateway level
- No test of the full pipeline: LLM call -> pre_tool_call hook -> Redis check -> block/pass verdict

**Recommended addition:** Add a Step 6.5 variant that:
1. Sets budget:monthly_cap to 0.01 in Redis
2. Makes a real LLM call through Hermes
3. Verifies the call is blocked with a budget enforcement error
4. Resets budget:monthly_cap to 30

---

### 4. Token Costs Realistic

#### 4.1 Are DeepSeek pricing figures correct for V4 Flash?

**FINDING:** PASS -- \.14/1M input and \.28/1M output are the current published rates for DeepSeek V4 Flash as of June 2026, matching the research report 1.

---

#### 4.2 Are GPT-5.5 pricing figures correct?

**FINDING:** PASS -- \.00/1M input and \.00/1M output match the research report 1. The research report also notes "Batch/Flex pricing at 50% discount" which is not reflected in the plan but is a minor detail.

---

#### 4.3 Does the \/month budget make sense given usage patterns?

**FINDING:** PASS with optimization recommendation -- The budget is very conservative but reasonable.

Analysis:
- At current usage with DeepSeek V4 Flash as primary (all traffic):
  - 10M tokens/month costs ~\.34 (research report 2)
  - This is only 4.5% of the \ budget (~22x headroom)
- If GPT-5.5 becomes available and is used for 50% of traffic:
  - 5M DeepSeek + 5M GPT-5.5 = \.67 + \.63 = ~\.30 (would exceed budget)
- The \/month budget acts as a safety net for GPT-5.5 fallback scenarios but is excessively generous for DeepSeek-only operation

**Recommendation:** Consider tiered budgets (\ DeepSeek cap, \ GPT-5.5 cap) for finer-grained control when GPT-5.5 is restored, or document that \ is 22x the expected DeepSeek-only spend.

---

#### 4.4 Is there a recommendation for primary vs fallback cost optimization?

**FINDING:** NEEDS_REVIEW -- The plan has implicit recommendations but no explicit cost optimization strategy.

**What exists:**
- Design Decision 19.1 defaults to DeepSeek V4 Flash as primary for cost savings (97% vs GPT-5.5)
- Research report 6 recommends: primary=DeepSeek (leverage cache hits), fallback=GPT-5.5 (quality), balanced=Guinevere combo (Tier 2 cheap providers)
- Risk register R-P6-07 estimates \.0014 for 100-prompt test cost

**What's missing:**
- No explicit "cost optimization playbook" defining WHEN to use each model based on task cost/quality tradeoffs
- No discussion of cache-hit optimization via 9Router RTK Token Saver (mentioned only in research report, not in plan)
- No budget allocation by task type (e.g., cap GPT-5.5 usage to \/month for CORE_REASONING)
- The fallback to gpt-5.5 will always 401 (documented gap), but when the token is refreshed, there's no cost guardrail to prevent expensive GPT-5.5 calls from consuming the entire budget

**Recommended addition:** Add a cost optimization section to the plan with:
1. Cache-hit optimization strategy (RTK Token Saver)
2. Per-task-type budget allocation
3. Explicit GPT-5.5 cost guardrails for when token is restored

---

### 5. Additional Findings

#### 5.1 Cost_per_1k mismatch between plan and llm_router.py

**FINDING:** FAIL -- The cost_per_1k values in llm_router.py do not match the plan's stated per-1M pricing:

| Model | Plan (\$/1M) | llm_router.py (\$/1K) | llm_router.py (\$/1M equiv) | Error |
|---|---|---|---|---|
| GPT-5.5 input | \.00 | \.0025 | \.50 | 2x low |
| GPT-5.5 output | \.00 | \.01 | \.00 | 3x low |
| DeepSeek V4 Flash input | \.14 | \.0001 | \.10 | 1.4x low |
| DeepSeek V4 Flash output | \.28 | \.0002 | \.20 | 1.4x low |

The llm_router.py values appear to be stale/approximate from an earlier pricing era. They use different base rates that do not match current market pricing.

**Impact:** If CostTracker.record_cost() is called using MODELS[task_type].cost_per_1k_* values, the recorded costs in Redis DB5 will be incorrect -- under-reporting spend by 1.4x-3x depending on the model.

**Recommended fix:** Update llm_router.py's cost_per_1k values to match the plan's per-1M pricing (divide by 1000):
- GPT-5.5 input: \.005/1K, GPT-5.5 output: \.03/1K
- DeepSeek V4 Flash input: \.00014/1K, DeepSeek V4 Flash output: \.00028/1K

---

#### 5.2 Budget hook fail-open policy

The budget hook uses fail-open (lines 709-717): if the check throws any exception, it returns action: 'pass' and exit code 0. This is a deliberate design choice per 19.1 ("Budget enforcement is operational, not safety-critical") but creates a risk of silent budget bypass.

**Finding:** PASS -- The plan documents this clearly and it's an acceptable trade-off. However, the risk register R-P6-01 (HIGH score) correctly flags budget hook fail-open as a risk. Consider adding a Prometheus metrics counter for hook errors so silent bypasses are detectable.

---

## FINAL VERDICT

| Criteria | Status |
|---|---|
| 1.1 Cost tracking per model | PASS |
| 1.2 Costs broken down by input/output | PASS |
| 1.3 Prices realistic | PASS |
| 2.1 Plan verifies Redis DB5 updated | PASS |
| 2.2 cost_tracker.py exists | PASS |
| **2.3 llm_router.py calls cost_tracker** | **FAIL** -- zero references found |
| 3.1 80% alert threshold | PASS |
| 3.2 100% block threshold | PASS |
| **3.3 Budget enforcement end-to-end test** | **NEEDS_REVIEW** -- hook tested in isolation only |
| 4.1 DeepSeek pricing correct | PASS |
| 4.2 GPT-5.5 pricing correct | PASS |
| 4.3 \/month budget realistic | PASS (with optimization note) |
| **4.4 Cost optimization recommendation** | **NEEDS_REVIEW** -- implicit only |
| **5.1 llm_router.py cost_per_1k match plan** | **FAIL** -- stale values off by 1.4x-3x |

### FINAL VERDICT: NEEDS REVIEW

**3 blocking issues must be resolved before Phase 6 implementation can proceed:**

1. **CRITICAL:** llm_router.py does not call CostTracker.record_cost() -- cost tracking from the LLM routing layer to Redis DB5 is a dead letter. Fix: add CostTracker.record_cost() call in llm_router.py.chat() after successful response parsing, OR update the plan to route cost tracking through Discord handlers and adjust Step 6.7 accordingly.

2. **HIGH:** llm_router.py's cost_per_1k_* values do not match the plan's per-1M pricing. DeepSeek is off by 1.4x and GPT-5.5 is off by 2-3x. Fix: update MODELS in llm_router.py to use the plan's rates divided by 1000.

3. **MEDIUM:** Add a full end-to-end budget enforcement test (trigger block threshold through a real or mocked Hermes invocation, not just a hook subprocess test).

### Recommended Remediation

| Issue | Action | Assignment | Before Step |
|---|---|---|---|
| 1 -- Missing record_cost in llm_router.py | Add CostTracker.record_cost() call after successful response in llm_router.py.chat() | Planner | Step 6.3 |
| 2 -- Stale cost_per_1k values | Update llm_router.py MODELS: GPT-5.5: 0.005/0.03, DeepSeek: 0.00014/0.00028 | Planner | Step 6.3 |
| 3 -- Missing end-to-end test | Add variant in Step 6.5 or Step 6.3 to verify block through Hermes | Planner | Step 6.5 |

---

## Evidence Reference

| Evidence | Path |
|---|---|
| llm_router.py no CostTracker reference | src/core/services/llm_router.py (lines 1-104) |
| cost_tracker.py Redis DB5 writes | src/core/services/cost_tracker.py (lines 34-39) |
| Plan pricing table | batch-plan-phase-6.md (lines 81-90) |
| Research pricing validation | research-reports/phase-6-7-planning/08-token-cost.md (lines 10-17) |
| LLM State analysis | research-reports/phase-6-7-planning/01-llm-state.md (lines 52-76) |
| Step 6.7 cost verification | batch-plan-phase-6.md (lines 1478-1588) |
| Budget hook threshold constants | batch-plan-phase-6.md (lines 629-631) |
| Block threshold test (isolated) | batch-plan-phase-6.md (lines 812-817) |
