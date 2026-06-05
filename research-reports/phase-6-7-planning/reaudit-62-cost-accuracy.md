# Re-Audit Report: Cost Tracking & Budget Accuracy (Auditor 6-2) — Post Planning-Fix

**Auditor:** 6-2 (Re-audit — Phase 6 LLM Routing Cost Accuracy)
**Date:** 2026-06-05
**Scope:** Verify the v1.1 planning-doc fixes resolve all 3 blocking items from the prior audit.
**Plan Examined:** `docs/setup-evidence/hermes-migration/batch-plan-phase-6.md` (v1.1 — "Planning fix: fail-closed budget hook exception, Step 6.6A CostTracker wiring contract, updated Step 6.7 cost verification dependencies")
**Prior Audit:** `research-reports/phase-6-7-planning/audit-62-cost-accuracy.md` (verdict: NEEDS REVIEW — 3 blocking items)
**Source Evidence Examined:**
- `src/core/services/cost_tracker.py` — synchronous `record_cost()` signature
- `src/core/services/llm_router.py` — current code (no CostTracker, stale pricing constants)
- `docs/setup-evidence/hermes-migration/batch-plan-phase-6.md` — v1.1 full plan
- `research-reports/phase-6-7-planning/audit-62-cost-accuracy.md` — prior findings

---

## Re-Audit Checklist

Each check corresponds to a prior-audit blocking item or a MUST DO from the re-audit brief.

### 1. Step 6.6A exists before Step 6.7

**FINDING:** ✅ **PASS**

The plan contains `## 11A. Step 6.6A: Wire CostTracker to LLMRouter` (line 1474) as a dedicated section between Step 6.6 (line 1373) and Step 6.7 (line 1630). Step numbering: 6.1 → 6.2 → 6.3 → 6.4 → 6.5 → 6.6 → **6.6A** → 6.7.

| Property | Value |
|---|---|
| Section heading | `## 11A. Step 6.6A: Wire CostTracker to LLMRouter` |
| Plan line | 1474 |
| Position relative to 6.7 | BEFORE (line 1630) |
| Duration | 1 hour |
| Risk | MEDIUM |

**Residual:** The Table of Contents (v1.1 lines 27-28) lists `11. [Step 6.6: ...]` then `12. [Step 6.7: ...]` without a visible 11A entry. The section exists at line 1474 but the ToC was not updated to reflect the insertion. This is a minor documentation inconsistency — the operational ordering (section 6.6A physically precedes 6.7) is correct and unambiguous.

---

### 2. Step 6.6A uses actual synchronous `CostTracker.record_cost()` signature

**FINDING:** ✅ **PASS**

**Actual signature** in `src/core/services/cost_tracker.py` (line 19):
```python
def record_cost(self, model: str, input_tokens: int, output_tokens: int,
                cost_per_1k_input: float, cost_per_1k_output: float):
```

**Plan's expected call** in Step 6.6A (lines 1519-1525):
```python
self.cost_tracker.record_cost(
    model=config.name,
    input_tokens=prompt_tokens,
    output_tokens=completion_tokens,
    cost_per_1k_input=config.cost_per_1k_input,
    cost_per_1k_output=config.cost_per_1k_output,
)
```

**Verification criteria** in plan:
- V-6.6A.1 (line 1560): Confirms `CostTracker`, `cost_tracker`, `record_cost` present in imports
- V-6.6A.2 (line 1565): Confirms `cost_per_1k_input`, `cost_per_1k_output`, `prompt_tokens`, `completion_tokens` arguments are used
- On Failure table (line 1617): Instructs "Use the actual synchronous signature from `src/core/services/cost_tracker.py`; do not add `await`"

Every argument name, count, and position matches the synchronous signature. The plan also documents the optional host/port/db/username/password constructor parameters in pre-conditions (line 1483) and verification commands (line 1701).

---

### 3. Stale pricing constants called out and corrected in plan

**FINDING:** ✅ **PASS**

**Prior audit finding 5.1:** llm_router.py's cost_per_1k values are stale (off by 1.4x–3x):

| Model | Current Code ($/1K) | Correct ($/1K) | Error |
|---|---|---|---|
| GPT-5.5 input | 0.0025 | 0.005 | 2x low |
| GPT-5.5 output | 0.01 | 0.03 | 3x low |
| DeepSeek V4 Flash input | 0.0001 | 0.00014 | 1.4x low |
| DeepSeek V4 Flash output | 0.0002 | 0.00028 | 1.4x low |
| Guinevere input | 0.0001 | 0.00014 | 1.4x low |
| Guinevere output | 0.0002 | 0.00028 | 1.4x low |

**Plan fix** in Step 6.6A Commands (lines 1506-1509):
```python
# In MODELS pricing:
# cx/gpt-5.5: cost_per_1k_input=0.005, cost_per_1k_output=0.03
# ds/deepseek-v4-flash: cost_per_1k_input=0.00014, cost_per_1k_output=0.00028
# guinevere: cost_per_1k_input=0.00014, cost_per_1k_output=0.00028
```

**Explicit assertion** V-6.6A.3 (lines 1571-1580):
```python
assert MODELS[TaskType.CORE_REASONING].cost_per_1k_input == 0.005
assert MODELS[TaskType.CORE_REASONING].cost_per_1k_output == 0.03
assert MODELS[TaskType.SUB_AGENT].cost_per_1k_input == 0.00014
assert MODELS[TaskType.SUB_AGENT].cost_per_1k_output == 0.00028
assert MODELS[TaskType.FALLBACK].cost_per_1k_input == 0.00014
assert MODELS[TaskType.FALLBACK].cost_per_1k_output == 0.00028
```

**Step 6.7 pre-condition** (line 1643):
> Model pricing constants updated before test traffic: `cx/gpt-5.5` = `$0.005/$0.03` per 1K, `ds/deepseek-v4-flash` and `guinevere` = `$0.00014/$0.00028` per 1K.

**On Failure table** (line 1618): "Pricing constants stale — Update MODELS constants before integration testing; otherwise Redis DB5 totals will be inaccurate."

Corrected values match `research-reports/phase-6-7-planning/08-token-cost.md` (which derives from $0.14/1M / 1000 = $0.00014/1K, $0.28/1M / 1000 = $0.00028/1K, $5.00/1M / 1000 = $0.005/1K, $30.00/1M / 1000 = $0.03/1K). Error: fully resolved.

---

### 4. Step 6.7 no longer has false precondition claiming existing wiring

**FINDING:** ✅ **PASS**

**Prior audit finding 2.3 (CRITICAL):** The plan originally listed a pre-condition "cost_tracker.py instrumented and called by llm_router.py" — which was **FALSE** (llm_router.py had zero references to CostTracker).

**Current Step 6.7 pre-conditions** (lines 1639-1644):
- `Step 6.6A complete — llm_router.py imports CostTracker and calls record_cost() after every successful LLM response.`
- `Step 6.5 complete — at least 50 LLM calls made after CostTracker wiring.`
- `Redis DB5 accessible.`
- `src/core/services/cost_tracker.py synchronous signature confirmed: record_cost(model, input_tokens, output_tokens, cost_per_1k_input, cost_per_1k_output).`
- `Model pricing constants updated before test traffic: [...]`
- `Budget hook Step 6.3 fail-closed behavior verified; no empty exception-handler patterns remain.`

All pre-conditions are now **correct and honest** — they depend on Step 6.6A doing the wiring, not on pre-existing code. Step 6.7's `Depends` header (line 1634) explicitly lists `Step 6.6A` as a dependency.

**Step 6.7 verification step 0** (lines 1649-1652) now begins by checking that CostTracker is actually wired:
```bash
# 0. Verify CostTracker is wired into llm_router.py before inspecting Redis
grep -nE 'CostTracker|cost_tracker|record_cost|cost_per_1k_input|cost_per_1k_output|prompt_tokens|completion_tokens'
```

**Residual:** Section 3.2 Parallelism Markers table still shows `6.7 Cost Tracking` with `parallel` and dependency `6.5 (verify after prompts run)` only — it was not updated to reflect the new `6.6A` dependency. However, the Step 6.7 section header (line 1634-1635) correctly overrides:
> **Depends:** Step 6.6A (CostTracker wired to LLMRouter), Step 6.5 (100-prompt test generates cost data)
> **Parallel with:** Step 6.8 only after Step 6.6A and Step 6.5 PASS

This is a minor documentation inconsistency in the parallelism table (section 3.2). The operational dependency is correct in the step definition itself, which is what an implementer would follow.

---

### 5. Redis DB5 verification requires non-zero spend after LLM traffic

**FINDING:** ✅ **PASS**

Step 6.7 contains explicit assertions that Redis DB5 keys must have **positive, non-zero** values after the 100-prompt test:

| Verification | Assertion | Line |
|---|---|---|
| V-6.7.1 | `cost:current_month` exists and `assert v > 0` | 1725-1727 |
| V-6.7.2 | `cost:by_model:ds/deepseek-v4-flash` exists and `assert v > 0` | 1729-1731 |
| V-6.7.3 | `check_budget()` returns `current_month > 0` | 1733-1745 |
| V-6.7.4 | Daily and monthly cost keys both count >= 1 | 1749-1750 |
| V-6.7.5 | Per-model breakdown keys count >= 1 | 1752-1754 |

**On Failure** (line 1761): "`cost:current_month` is 0 when calls were made — `CostTracker.record_cost()` is not being called by `LLMRouter.chat()` or Redis DB5 writes failed. Return to Step 6.6A and fix before proceeding."

Additionally, Step 6.7 Command 4 (lines 1709-1719) calculates the **expected cost** for 100 prompts using the corrected pricing constants ($0.00014/$0.00028 per 1K) and an average of 50/50 input/output tokens, providing a sanity-check range.

---

### 6. Cost tracking failure is fail-closed (not swallowed)

**FINDING:** ✅ **PASS**

Three separate layers enforce fail-closed behavior in the plan:

**Layer 1 — Step 6.6A record_cost exception handler** (lines 1526-1534):
```python
except Exception as exc:
    logger.error("llm_cost_tracking_failed", ...)
    raise RuntimeError("LLM cost tracking failed; refusing untracked spend") from exc
```
This raises a `RuntimeError`, propagating through `chat()` which will log the fallback chain and ultimately raise `RuntimeError("All LLM providers failed")`. Cost tracking failure prevents the response from being returned.

**Layer 2 — Step 6.7 On Failure** (line 1765):
> Cost tracking exception occurs during successful LLM response — Treat as fail-closed and return to Step 6.6A; untracked LLM spend is not acceptable for Phase 6 execution.

**Layer 3 — Budget hook (Step 6.3) on_failure** (Step 6.4 hook registration): `on_failure: block` — if the budget hook itself fails, the LLM call is blocked.

Additionally, Step 6.6A V-6.6A.5 (lines 1587-1603) checks for empty exception handlers (forbidden pattern `except: pass`) in the planned llm_router.py changes.

---

### 7. Plan does not merely verify Redis — it requires LLMRouter to call CostTracker

**FINDING:** ✅ **PASS**

This was the core structural gap identified by the prior audit. The prior audit found the plan would fail Step 6.7 because cost tracking was a dead letter — `llm_router.py` had no CostTracker wiring.

The v1.1 fix adds **Step 6.6A** as a required implementation step that:

1. Imports `CostTracker` into `llm_router.py`
2. Initializes `self.cost_tracker = CostTracker()` in `LLMRouter.__init__`
3. Calls `record_cost()` after every successful response parse (before returning)
4. Includes explicit test expectations for the wiring
5. Verifies wiring via grep before allowing Step 6.7 to inspect Redis

Step 6.7's first command (line 1649-1652) — "Verify CostTracker is wired into llm_router.py before inspecting Redis" — ensures verification cannot pass without the wiring being present. The evidence path (line 1770) explicitly includes "proof that Step 6.6A wiring exists."

---

## Final Verdict

| # | Prior Blocking Issue | Status | Evidence |
|---|---|---|---|
| 1 | **CRITICAL:** llm_router.py does not call `CostTracker.record_cost()` | **✅ FIXED** | Step 6.6A (line 1474) explicitly wires CostTracker with import, init, and record_cost call; V-6.6A.1 verifies; Step 6.7 depends on Step 6.6A |
| 2 | **HIGH:** llm_router.py cost_per_1k values stale (1.4x–3x off) | **✅ FIXED** | Step 6.6A corrects all 6 constants (lines 1506-1509); V-6.6A.3 asserts each value; Step 6.7 pre-condition restates corrected values |
| 3 | **MEDIUM:** Missing end-to-end budget enforcement test | **✅ FIXED** | Step 6.6A (lines 1544-1554) adds explicit test scaffold with assertions for mock success and record_cost exception paths |

| Additional Checks | Status | Evidence |
|---|---|---|
| Step 6.6A exists before Step 6.7 | ✅ PASS | Section 11A at line 1474, section 12 at line 1630 |
| Uses actual synchronous signature | ✅ PASS | 5-param record_cost matches cost_tracker.py exactly |
| Redis verification requires non-zero spend | ✅ PASS | V-6.7.1, V-6.7.2, V-6.7.3 all assert > 0 |
| Cost tracking failure is fail-closed | ✅ PASS | RuntimeError raised; on_failure: block; no empty except |
| Requires LLMRouter → CostTracker wiring | ✅ PASS | Step 6.6A is mandatory before Step 6.7 can pass |

### VERDICT: PASS

The v1.1 planning-doc fixes resolve all three blocking items from the prior audit with explicit, verifiable, and operationally correct specifications:

1. **CostTracker wiring** is now a dedicated implementation step (6.6A) with clear code diff, test scaffold, and grep-based verification before Redis inspection.
2. **Pricing constants** are corrected to match the research-validated $/1M rates divided by 1000, with compile-time assertions in V-6.6A.3.
3. **Fail-closed semantics** are documented at every layer: record_cost exception → RuntimeError, budget hook on_failure → block, no empty exception handlers permitted.

**Residual minor issues (non-blocking):**
- Section 3.2 parallelism table not updated to reflect 6.6A dependency for Step 6.7 (though the step header overrides correctly)
- ToC does not list Step 6.6A (though section exists physically between 6.6 and 6.7)

These are documentation cosmetics that do not affect the plan's correctness or implementability. They could be fixed in a subsequent ToC/table update but are not blockers.

**Next action per execution phase:** Implement Step 6.6A before Step 6.7. Run V-6.6A.1–V-6.6A.6 to confirm wiring, pricing, and fail-closed behavior before moving to Step 6.7 Redis verification.

---

## Evidence Reference

| Evidence | Path |
|---|---|
| Step 6.6A section | `batch-plan-phase-6.md` (lines 1474–1627) |
| Corrected pricing constants | `batch-plan-phase-6.md` (lines 1506-1509) |
| Pricing constant assertions | `batch-plan-phase-6.md` (lines 1571-1580) |
| synchronous record_cost signature | `src/core/services/cost_tracker.py` (line 19) |
| Fail-closed raise in record_cost | `batch-plan-phase-6.md` (lines 1526-1534) |
| Non-zero Redis assertion (V-6.7.1) | `batch-plan-phase-6.md` (lines 1725-1727) |
| Step 6.7 pre-conditions (corrected) | `batch-plan-phase-6.md` (lines 1639-1644) |
| Prior audit report | `research-reports/phase-6-7-planning/audit-62-cost-accuracy.md` |
| Plan version history (v1.1 planning fix) | `batch-plan-phase-6.md` (line 2404) |
