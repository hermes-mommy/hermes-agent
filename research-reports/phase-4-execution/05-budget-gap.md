# 05-budget-gap.md — Budget/Cost Enforcement Gap Analysis for Hermes MCP Tool Calls

**Date:** 2026-06-05  
**Author:** Guinevere (Research Agent)  
**Phase:** Phase 4 Execution — P4-003 (Budget Enforcement)  
**Status:** COMPLETE — Gap Analysis Ready  

---

## 1. Executive Summary

The codebase contains **three** partially-implemented cost/budget tracking classes, but **zero** global enforcement in the Hermes tool call path. Budget checks exist only at the individual tool level (`exa_search.py`), not in the `pre_tool_call` hook, not in `llm_router.py`, and not in any Hermes shell hook. The `BudgetEnforcer.record_and_check()` method — designed as the primary enforcement entry point — is **never called** from any production code path.

### Critical Finding

**Budget enforcement is fail-open by default.** There is no `pre_tool_call` budget gate. Every Hermes MCP tool call (Brave, websearch, filesystem, etc.) proceeds without checking daily caps or monthly budgets unless the tool itself implements its own check. Currently only `exa_search.py` does so — and even that uses a direct Redis connection, not the centralized `BudgetEnforcer`.

---

## 2. Component Inventory

### 2.1 Existing Cost/Budget Classes

| Class | File | Purpose | Called From Production? | Redis DB |
|-------|------|---------|------------------------|----------|
| `BudgetEnforcer` | `src/mcp/budget.py` | Per-tool daily cap, monthly $30 cap, fallback routing, alert levels | **NO** — never instantiated in any production path | DB5 |
| `ToolCostTracker` | `src/mcp/cost.py` | Record per-tool MCP call costs, query daily/monthly aggregates | **NO** — only used in tests | DB5 |
| `CostTracker` | `src/core/services/cost_tracker.py` | Record LLM token costs, `check_budget()` returns status (not enforced) | **YES** — `conversational_handler.py`, `loops/cost.py`, Discord commands | DB5 |
| `LoopCostTracker` | `src/loops/cost.py` | Per-loop cost recording, delegates to `CostTracker` for global tracking | **YES** — `loops/manager.py` | DB5 |

### 2.2 Tool-Level Budget Enforcement (Ad-Hoc)

| Tool | File | Has Budget Check? | Uses `BudgetEnforcer`? | Mechanism |
|------|------|-------------------|------------------------|-----------|
| `exa_search` | `src/mcp/tools/exa_search.py` | **YES** | **NO** — direct Redis | `_check_budget()` reads `tool:cost:exa:YYYY-MM-DD` directly |
| `brave_search` | `src/mcp/tools/brave_search.py` | Unknown (not inspected) | **NO** | — |
| `websearch` | `src/mcp/tools/websearch.py` | Catches `BudgetExceeded` for fallback | Indirect | Catches exception from exa |
| All other tools (16+) | `src/mcp/tools/*.py` | **NO** | **NO** | No budget check at all |

### 2.3 Production Code Paths That Call Cost/Budget Code

| Code Path | What It Calls | What It Does NOT Call | Fail-Open Risk |
|-----------|---------------|----------------------|----------------|
| `conversational_handler.py` > Step 12 | `CostTracker.record_cost()` | Does NOT call `BudgetEnforcer.check_budget()` or `BudgetEnforcer.record_and_check()` | LLM calls are recorded but never blocked |
| `conversational_handler.py` > Hermes `send_message()` > `session_adapter.py` | Stores metadata in `_last_metadata` | Does NOT check budget before LLM call | No pre-LLM budget gate |
| `llm_router.py` > `chat()` | Sends HTTP POST to 9Router | Does NOT call `CostTracker.record_cost()` or `BudgetEnforcer.check_budget()` | No cost recording, no enforcement |
| `loops/manager.py` > `record_loop_cost()` | `LoopCostTracker.record_loop_cost()` > `CostTracker.record_cost()` | Does NOT call `BudgetEnforcer.check_budget()` | Loops recorded but never blocked |
| `safety_plugin.py` > `pre_tool_call` | Auth Matrix (G09), Consent deferred (G10) | Does NOT call `BudgetEnforcer.check_budget()` | No pre-tool budget gate |
| Hermes shell hooks (`pre_tool_call`) | `consent_gate.py` | No budget hook exists | No pre-tool budget gate |

---

## 3. Redis DB5 Key Usage Analysis

### 3.1 Key Registry

| Key Pattern | Writer | Reader | TTL | Conflict? |
|-------------|--------|--------|-----|-----------|
| `tool:cost:{name}:YYYY-MM-DD` | `BudgetEnforcer.record_and_check()`, `ToolCostTracker.record_tool_cost()`, `exa_search._record_cost()` | `BudgetEnforcer`, `ToolCostTracker` | 7 days (ToolCostTracker), 2 days (exa_search), none (BudgetEnforcer) | **YES** - inconsistent TTL |
| `tool:cost:total:YYYY-MM-DD` | `BudgetEnforcer`, `ToolCostTracker` | `BudgetEnforcer` | 7 days / none | **Overlap** - same key, different classes |
| `cost:current_month` | `BudgetEnforcer.record_and_check()`, `CostTracker.record_cost()` | `BudgetEnforcer`, `CostTracker`, Discord commands | **None** | **Overlap** - both classes write to same key (this is actually correct for unified cap) |
| `cost:current_day` | `CostTracker.record_cost()` | - | None | - |
| `cost:by_model:{model}` | `CostTracker.record_cost()` | Discord commands | None | - |
| `cost:daily:{today}` | `CostTracker.record_cost()` | - | None | - |
| `cost:monthly:{month}` | `CostTracker.record_cost()` | - | None | - |
| `loop:cost:{loop_id}` | `LoopCostTracker` | `LoopCostTracker` | None | - |
| `budget:monthly_cap` | - | `CostTracker.check_budget()` | None | **Not set anywhere** - defaults to $30 |

### 3.2 Key Collision: `cost:current_month` Both Written and Read

`cost:current_month` is written by **both** `BudgetEnforcer.record_and_check()` (Exa/Brave costs) and `CostTracker.record_cost()` (LLM token costs). This means MCP tool costs and LLM token costs accumulate in the **same key** - which is actually **correct** for a unified $30 cap. However:

- `BudgetEnforcer.check_budget()` reads `cost:current_month` (includes LLM costs from `CostTracker`)
- `CostTracker.check_budget()` also reads `cost:current_month` (includes MCP costs from `BudgetEnforcer`)

The keys converge, but the enforcement paths don't communicate. Both can independently block, but neither is wired to actually block production calls.

---

## 4. Fail-Open Risk Analysis

### 4.1 Redis Read Failure - Treated as $0 - Allows Calls

```python
# BudgetEnforcer._get_daily_spend - line 301
def _get_daily_spend(self, tool_name: str) -> float:
    try:
        raw = self.redis.get(tool_key)
        return float(str(raw)) if raw is not None else 0.0
    except (RedisError, ValueError) as exc:
        logger.error(...)
        return 0.0  # FAIL-OPEN: Redis down -> $0 spend -> all calls allowed
```

All three `_get_*_spend()` methods in `BudgetEnforcer` (daily, global, monthly) return `0.0` on Redis error. If Redis DB5 is unavailable:
- Every budget check passes
- Every tool call is allowed
- Costs are not recorded (silent data loss)

### 4.2 BudgetEnforcer Never Instantiated in Production

`BudgetEnforcer` exists only as an importable class. No production code path creates an instance. The only budget check that runs in production is `exa_search._check_budget()`, which uses a **separate** Redis connection and runs independently.

### 4.3 ToolCostTracker Never Called

`ToolCostTracker` has comprehensive recording and querying capabilities but is **zero-referenced** outside its test file. No tool calls `record_tool_cost()`. No production code queries `get_all_daily_costs()`.

### 4.4 llm_router.py Records Nothing

`llm_router.py` makes the actual HTTP calls to 9Router but neither records the cost nor checks budget. It reads token counts from the API response for logging but discards them after the log line.

### 4.5 CostTracker.check_budget() Returns Status Only

`CostTracker.check_budget()` returns a dict with `status` field but is **never called by any enforcement gate**. It is only used by Discord read commands to display the current budget state. It does not raise exceptions or block calls.

---

## 5. Hermes Hook Integration Points

### 5.1 In-Process Python Plugin: `safety_plugin.py`

**Current:** `pre_tool_call` handles G09 (Auth Matrix) and G10 (Consent deferred).  
**Gap:** No G11 (Budget check).  

**Integration Point:** `GuinevereSafetyPlugin.pre_tool_call()` method (line 721):
- Import `BudgetEnforcer` from `src.mcp.budget`
- Instantiate as a lazy singleton (like `_hard_stop_handler`)
- Call `self._budget_enforcer.check_budget(tool_name)` before the Auth Matrix check
- Return `{"action": "block", "reason": "BUDGET_EXCEEDED:..."}` when caps are hit

### 5.2 Shell Hook: `hermes-config/hooks/`

**Current:** `pre_tool_call` > `consent_gate.py`, `post_tool_call` > `dnr_filter.py`  
**Gap:** No budget shell hook exists.

**Integration Point:** New hook script `budget_gate.py`:
- Reads `tool_name` from stdin JSON
- Calls `BudgetEnforcer.check_budget()` or reads Redis directly
- Returns `{"action": "block", "reason": "..."}` or `{"action": "allow"}`
- Register in `hermes-config/config.yaml` under `hooks.pre_tool_call`

### 5.3 post_tool_call - Cost Recording

**Current:** Observational logging only.  
**Gap:** No cost recording after tool calls.

**Integration Point:** Either in the Python plugin's `post_tool_call` or a new shell hook:
- Call `ToolCostTracker.record_tool_cost(tool_name)` or `BudgetEnforcer.record_and_check(tool_name, cost)`
- `record_and_check()` is preferred (records + rechecks budget atomically)

---

## 6. LLM Cost Tracking Gap

### 6.1 Current State

| Code Path | Records LLM Cost? | Checks LLM Budget? |
|-----------|-------------------|-------------------|
| `conversational_handler.py` > Hermes `send_message()` | **YES** - via `CostTracker.record_cost()` | **NO** |
| `llm_router.py` > `chat()` | **NO** - router does not record | **NO** |
| `loops/manager.py` > `LoopCostTracker` | **YES** - delegates to `CostTracker` | **NO** |
| `hermes/config > pre_llm_call` | **NO** | **NO** |

### 6.2 Missing: Pre-LLM Budget Check

There is no budget check before LLM calls. If the monthly $30 cap is hit:
- `CostTracker` will record the cost (incrementing `cost:current_month` past $30)
- But nothing will block the call
- Only after the fact will records show the overage

---

## 7. Specific Code Integration Points for P4-003

### 7.1 P0-R1: BudgetEnforcer > Hermes pre_tool_call Plugin

**File:** `src/hermes/safety_plugin.py`  
**Change:** Add `BudgetEnforcer` singleton and budget check in `pre_tool_call()`

Steps:
1. Add `from src.mcp.budget import BudgetEnforcer` as lazy import in `_init_safety_modules()`
2. Add `self._budget_enforcer` instance and `self._budget_available` flag
3. In `pre_tool_call()`, after G09 auth check:
   - Call `self._budget_enforcer.check_budget(tool_name)`
   - Catch `BudgetExceeded` > return `{"action": "block", "reason": "BUDGET_EXCEEDED"}`
   - Catch generic Exception > fail-closed: return `{"action": "block", "reason": "BUDGET_CHECK_ERROR"}`

### 7.2 P0-R2: Cost Recording in post_tool_call

**File:** `src/hermes/safety_plugin.py`  
**Change:** Add `ToolCostTracker` recording in `post_tool_call()`

Steps:
1. Add `from src.mcp.cost import ToolCostTracker` as lazy import
2. In `post_tool_call()`:
   - `cost = ToolCostTracker.get_tool_cost(tool_name)`
   - If `cost > 0` or variable cost, record via `ToolCostTracker.record_tool_cost(tool_name, cost)`

### 7.3 P0-R3: Fail-Closed on Redis Error

**File:** `src/mcp/budget.py`  
**Change:** Add `fail_closed_on_redis_error` config option

Steps:
1. Add `fail_closed_on_redis_error: bool = True` to `BudgetConfig`
2. In `_get_daily_spend()`, `_get_global_daily_spend()`, `_get_monthly_spend()`:
   - When `fail_closed_on_redis_error` is True, raise `BudgetExceeded` instead of returning 0.0
   - Log the error before raising

### 7.4 P0-R4: CostTracker.record_cost() into llm_router.py

**File:** `src/core/services/llm_router.py`  
**Change:** Call `CostTracker.record_cost()` after successful LLM response

Steps:
1. Import `CostTracker` at top of file
2. In `chat()`, after successful response:
   - Create `tracker = CostTracker()` instance
   - Call `tracker.record_cost(model=config.name, input_tokens=..., output_tokens=..., cost_per_1k_input=config.cost_per_1k_input, cost_per_1k_output=config.cost_per_1k_output)`
   - Use token counts from `result["usage"]`

### 7.5 P1-R5: Pre-LLM Budget Check

**File:** `src/core/services/llm_router.py`  
**Change:** Check budget before dispatching

Steps:
1. In `chat()`, before the fallback loop:
   - `tracker = CostTracker()`
   - `budget = tracker.check_budget()`
   - If `budget["status"] == "HARD_STOP"`: raise `RuntimeError("Monthly budget cap reached - all LLM calls blocked")`
   - Log warning at CRITICAL/WARNING levels

---

## 8. Implementation Effort Estimate

| Priority | Items | Complexity | Risk | Dependencies |
|----------|-------|------------|------|-------------|
| P0 | 4 | Medium | **HIGH** - fail-open currently | None (all classes exist, tested) |
| P1 | 4 | Small-Medium | Medium | P0-R1 recommended first |
| P2 | 3 | Small | Low | None |

**Total estimated effort:** 1-2 days for all P0 items, 1 day for P1, 1 day for P2.

---

## 9. Verification Criteria for P4-003

A successful implementation must pass:

1. **pre_tool_call blocks when budget exceeded:** Unit test creates `BudgetEnforcer` with mocked Redis at cap > calls `pre_tool_call` > asserts `{"action": "block"}` returned
2. **post_tool_call records costs:** Unit test > mocked Redis > asserts `INCRBYFLOAT` called on correct key
3. **llm_router.py records costs:** Integration test > mock HTTP > asserts `CostTracker.record_cost()` called
4. **Fail-closed on Redis error:** Unit test with `RedisError` > asserts `BudgetExceeded` raised or `{"action": "block"}` returned
5. **Monthly $30 cap blocks all:** Integration test > seed Redis with $30 monthly > asserts all subsequent calls blocked
6. **Per-tool daily cap blocks specific tool:** Similar to above with daily key
7. **Existing tests still pass:** `pytest tests/mcp/test_budget.py tests/mcp/test_cost.py`

---

## 10. Evidence Artifacts

| Artifact | Description |
|----------|-------------|
| `src/mcp/budget.py` (364 lines) | BudgetEnforcer - exists, tested, unused in production |
| `src/mcp/cost.py` (241 lines) | ToolCostTracker - exists, tested, unused in production |
| `src/core/services/cost_tracker.py` (68 lines) | CostTracker - used for LLM recording but not enforcement |
| `src/hermes/safety_plugin.py` (1054 lines) | pre_tool_call hook - missing budget gate |
| `src/core/services/llm_router.py` (104 lines) | LLM router - missing cost recording and budget check |
| `src/discord/conversational_handler.py` (634 lines) | Main Discord handler - records LLM costs but does not check |
| `hermes-config/config.yaml` (334 lines) | Hermes config - budget section is informational only |
| `hermes-config/hooks/consent_gate.py` (199 lines) | Existing pre_tool_call shell hook - pattern to replicate |
| `tests/mcp/test_budget.py` (781 lines) | BudgetEnforcer test suite |
| `tests/mcp/test_cost.py` (462 lines) | ToolCostTracker test suite |
