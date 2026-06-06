# Phase 6 — Step 2/3 Implementation Report

**Date:** 2026-06-06  
**Files changed:** `src/core/services/llm_router.py`  
**Files created:** `tests/hermes/test_llm_router_cost.py`  
**Planner scaffold ref:** `docs/setup-evidence/phase-6/plan.md` Steps 2 & 3.

---

## 1. What Was Done

### `src/core/services/llm_router.py` — Full rewrite with Phase 6 requirements

| Requirement | Implementation |
|---|---|
| **Primary model** | `TaskType.CORE_REASONING` now uses `ds/deepseek-v4-flash` (was `cx/gpt-5.5`) |
| **All traffic via 9Router** | Every model config uses `base_url="http://localhost:20128/v1"` |
| **Pricing: `cx/gpt-5.5`** | `input_per_1k: 0.005`, `output_per_1k: 0.03` |
| **Pricing: `ds/deepseek-v4-flash`** | `input_per_1k: 0.00014`, `output_per_1k: 0.00028` |
| **Pricing: `guinevere`** | `input_per_1k: 0.00014`, `output_per_1k: 0.00028` |
| **CostTracker integration** | Import + init in `__init__` (constructor injection with default) |
| **Cost recording** | `CostTracker.record_cost()` called after every successful HTTP response |
| **Token extraction** | `usage.prompt_tokens` / `usage.completion_tokens` parsed from JSON, defaulted to 0 when missing/null |
| **Fail-closed cost error** | If `record_cost` raises → log `llm_cost_tracking_failed` + `raise RuntimeError("LLM cost tracking failed")`; error is OUTSIDE provider try/except so fallback does NOT swallow it |
| **Robust SSE strip** | Regex `data:\s*\[DONE\]\s*$` handles both `data: [DONE]` and `data:[DONE]` |
| **Provider fallback preserved** | HTTP/JSON errors continue the 3-tier chain; cost errors are not caught by this path |
| `PRICING` **dict** | New module-level dict with all three model pricings as a reference table |

### `tests/hermes/test_llm_router_cost.py` — 20 unit tests across 7 categories

| Category | Tests | Coverage |
|---|---|---|
| `TestCostRecording` | 3 | Successful cost recording with full usage, missing usage, null usage fields |
| `TestCostTrackingFailClosed` | 2 | Cost failure raises exact `RuntimeError("LLM cost tracking failed")`; NOT swallowed by fallback (exactly 1 HTTP call) |
| `TestPricingConstants` | 3 | All three PRICING entries match required values |
| `TestSseStrip` | 5 | `data: [DONE]`, `data:[DONE]`, trailing whitespace, normal JSON untouched, mid-content marker safe |
| `TestPrimaryModel` | 3 | CORE_REASONING is DeepSeek via localhost:20128; all routes through 9Router |
| `TestProviderFallback` | 3 | HTTP error falls back to next model, all providers fail raises RuntimeError, SUB_AGENT uses 2-tier chain |
| `TestModelConfigSanity` | 1 | ModelConfig dataclass construction |

---

## 2. Validation Results

### 2.1 Scaffold Commands (Step 2)

| Check | Result |
|---|---|
| `grep "CostTracker"` → import/use present | ✅ |
| `grep "record_cost"` → called after successful response | ✅ (line 191) |
| `grep "LLM cost tracking failed"` → exact text | ✅ (lines 10, 110, 204) |
| `grep "cost_per_1k_input\|cost_per_1k_output"` → pricing values present | ✅ |
| `grep "data:.*\[DONE\]"` → SSE regex handles `data:\s?\[DONE\]` | ✅ (regex: `data:\s*\[DONE\]\s*$`) |
| `lsp_diagnostics src/core/services/llm_router.py` | No errors; only strict-basedpyright warnings (pre-existing pattern) |

### 2.2 Scaffold Commands (Step 3)

| Check | Result |
|---|---|
| `python -m pytest tests/hermes/test_llm_router_cost.py -v` | ✅ 20/20 passed, exit 0 |

### 2.3 Forbidden Patterns

| Pattern | Result |
|---|---|
| `# type: ignore` | ✅ not found |
| `except Exception: pass` | ✅ not found |
| Empty `except:` | ✅ not found |
| Direct provider URLs (`api.openai.com`, `openrouter.ai`, `api.anthropic.com`) | ✅ not found |
| `pytest.skip` | ✅ not found |
| Fake assertions | ✅ not found |

---

## 3. Evidence Artifacts

- `src/core/services/llm_router.py` — modified implementation
- `tests/hermes/test_llm_router_cost.py` — 20 unit tests
- Pytest output: 20 passed, 0 failed (see above)

---

## 4. Doc-Sync Impact

None — no docs were modified. The `PRICING` dict is self-documenting within the router.

---

## 5. Boundary Compliance

- ✅ Consent safety: no persona/surveillance/memory changes
- ✅ No type suppression
- ✅ No secrets or credentials exposed
- ✅ All traffic through localhost 9Router only
- ✅ Cost failure is properly fail-closed, not swallowed by fallback chain
- ✅ No direct provider endpoints

---

## 6. Rollback / Re-run Safety

- Rollback: `git checkout -- src/core/services/llm_router.py tests/hermes/test_llm_router_cost.py`
- Tests are fully mocked with no network or Redis dependency; re-runnable offline.

---

## 7. Design Decisions and Caveats

1. **CostTracker fallback handling**: The cost-tracking call sits **outside** the provider try/except block to prevent the `except Exception` in the fallback loop from silently catching it. This is the key design change from the original code.
2. **`PRICING` dict**: Added as a module-level reference table for human readability and testability. The `cx/gpt-5.5` pricing is retained as a reference even though it's not the primary model.
3. **SUB_AGENT fallback chain**: When `task_type=SUB_AGENT`, the chain is `[SUB_AGENT, FALLBACK]` — CORE_REASONING is excluded (same as original behavior).
4. **No metrics integration**: Prometheus metrics are deferred to Step 7 per the planner. This Step 2/3 covers only CostTracker, pricing, SSE, and fail-closed behavior.

---

## 8. Auditor Gate Readiness

Ready for Step 3 independent auditor. See `test_llm_router_cost.py` for the complete test suite covering all required surfaces.
