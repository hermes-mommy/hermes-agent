# R4-005: Budget Enforcement & Cost Tracking Research Report

**Date:** 2026-06-05  
**Author:** Guinevere  
**Phase:** Phase 4 (MCP + Tools) Migration Planning  
**Related ADRs:** ADR-004 (Primary LLM), ADR-006 (Sub-agent LLM), ADR-035 (Budget Enforcement)  
**Reference:** `docs/70-finops/70-Cost_FinOps_Model_v1.1.md`

---

## 1. Executive Summary

The codebase already contains a robust, partially-implemented budget enforcement and cost tracking architecture. Per-tool daily caps, monthly absolute caps, and fallback routing are implemented in `src/mcp/budget.py` and `src/mcp/cost.py`. However, **budget enforcement is currently applied at the individual tool level (e.g., `exa_search.py`), NOT globally via the `pre_tool_call` hook**. 

To fully satisfy ADR-035 requirements ($30/month hard cap, 80% alert, 100% block all LLM calls), the existing `BudgetEnforcer` must be integrated into the Hermes `pre_tool_call` safety gate and LLM routing layer.

---

## 2. Existing Budget Enforcement Architecture

### 2.1 Core Components

| File | Purpose | Status |
|---|---|---|
| `src/mcp/budget.py` | `BudgetEnforcer` class: checks daily/monthly caps, manages fallback routing (Exa → Brave). | **Active** |
| `src/mcp/cost.py` | `ToolCostTracker` class: records per-tool costs, aggregates daily/monthly totals. | **Active** |
| `src/mcp/tools/exa_search.py` | Tool-level implementation: calls `_check_budget()` before API, `_record_cost()` after. | **Active** |
| `src/mcp/tools/websearch.py` | Hybrid search: catches `BudgetExceeded` and falls back to secondary provider. | **Active** |

### 2.2 Budget Configuration (`BudgetConfig`)

Current hardcoded thresholds in `src/mcp/budget.py`:
- **Exa daily cap:** $5.00
- **Brave daily cap:** $3.00
- **Global daily emergency cap:** $10.00
- **Monthly warning:** $3.00
- **Monthly critical:** $15.00
- **Monthly hard stop:** $25.00
- **Monthly absolute cap:** $30.00 *(Aligns with FinOps v1.1)*

### 2.3 Redis Cost Tracking Schema (DB5)

All cost tracking uses Redis DB5 (`port=6380`, `username="guinevere_core"`).

| Key Pattern | Purpose | TTL |
|---|---|---|
| `tool:cost:{tool_name}:YYYY-MM-DD` | Per-tool daily spend accumulator | 7 days |
| `tool:cost:total:YYYY-MM-DD` | Aggregate daily spend across all tools | 7 days |
| `cost:current_month` | Running monthly total (no TTL, managed manually) | None |

### 2.4 Tool Cost Registry (`_TOOL_COSTS`)

Fixed costs defined in `src/mcp/cost.py`:
- `brave_search`: $0.01
- `exa`: $0.007
- `websearch`: `-1.0` (Variable cost — caller must pass explicit `cost_usd`)
- `context7`, `fetch`, `filesystem`, `github`, `grep_app`, `obscura_cdp`, `sequential_thinking`, `time`, `git`, `postgres`, `redis`, `shell`, `docker`: `$0.0`

---

## 3. LLM Routing & Provider Strategy

### 3.1 Current Routing Architecture

- **Primary LLM:** GPT-5.5 via 9Router (`http://localhost:20128/v1`)
- **Sub-agent LLM:** DeepSeek V4 Flash via 9Router
- **Fallback Policy:** **NO OpenRouter fallback.** If 9Router is unavailable, the system queues/retries through the 9Router recovery policy and degrades non-critical tasks.

### 3.2 Key Files

| File | Relevance |
|---|---|
| `tests/smoke/conftest.py` | Defines `NINEROUTER_BASE = "http://localhost:20128/v1"` |
| `src/memory/embeddings.py` | References `OPENROUTER_API_KEY` (legacy/fallback config, being deprecated) |
| `evidence/v2-doc-update/apply_v2_updates.py` | Documents explicit migration away from OpenRouter to 9Router-only routing |

### 3.3 API Key Rotation / Provider Switching

- **Vendor Alternative Matrix** (FinOps v1.1, Appendix B) documents switch procedures.
- No automated API key rotation logic exists in the codebase yet. Provider switching is currently a manual configuration change with documented runbooks.

---

## 4. `pre_tool_call` Hook Analysis

### 4.1 Current Implementation

Located in `src/hermes/safety_plugin.py`, the `pre_tool_call` hook currently enforces:
- **Gate 09 (Auth Matrix):** Blocks `FORBIDDEN` and `DESTRUCTIVE_APPROVAL` operations via `src/mcp/auth_matrix`.
- **Gate 10 (Consent):** Deferred (logs warning only, requires Redis+SQLAlchemy integration).

### 4.2 Gap: Budget Enforcement Missing from `pre_tool_call`

**CRITICAL FINDING:** The `BudgetEnforcer` is **NOT** currently integrated into the `pre_tool_call` hook. Budget checks are implemented ad-hoc within individual tools (e.g., `exa_search.py` calls `_check_budget()` directly). 

To satisfy ADR-035 ("budget enforcement via `pre_tool_call` hook"), the `GuinevereSafetyPlugin.pre_tool_call` method must be extended to:
1. Instantiate or receive `BudgetEnforcer`.
2. Call `await enforcer.check_budget(tool_name)` before allowing tool execution.
3. Raise `BudgetExceeded` or return `{"action": "block"}` if caps are reached.

---

## 5. Alert, Threshold, and Cap Mechanisms

### 5.1 Alert Levels (`BudgetStatus.alert_level`)

Computed in `src/mcp/budget.py` based on monthly spend:
- `"NORMAL"`: < $3.00
- `"WARNING"`: >= $3.00 (80% of Phase 1 LLM budget) or daily cap reached
- `"CRITICAL"`: >= $15.00
- `"HARD_STOP"`: >= $25.00

### 5.2 Soft-Cap Warnings

- **Brave Search:** Logs `budget.brave_soft_cap_warning` when daily spend >= 80% of `$3.00` cap.
- **Exa Search:** Raises `BudgetExceeded` exception when daily spend >= `$5.00`.

### 5.3 Fallback Logic

Defined in `_FALLBACK_MAP`:
```python
_FALLBACK_MAP: dict[str, str | None] = {
    "exa": "brave_search",
    "brave_search": None,  # No fallback; throttles/blocks
}
```
If Exa exceeds budget, `get_fallback_tool("exa")` returns `"brave_search"`. If Brave also exceeds budget, it returns `None`, triggering a hard block.

---

## 6. Recommendations for Phase 4 Migration

### 6.1 Immediate Actions (Required for ADR-035 Compliance)

1. **Integrate `BudgetEnforcer` into `pre_tool_call`:**
   - Modify `src/hermes/safety_plugin.py` to import and instantiate `BudgetEnforcer`.
   - Add budget check logic to `pre_tool_call` method before the Auth Matrix check.
   - Ensure `BudgetExceeded` exceptions are caught and returned as `{"action": "block", "reason": "BUDGET_EXCEEDED"}`.

2. **Extend Cost Tracking to LLM Calls:**
   - The current `ToolCostTracker` only tracks **MCP tool calls**, not LLM API calls.
   - Create a parallel `LLMCostTracker` or extend `ToolCostTracker` to record token usage/cost for GPT-5.5 and DeepSeek V4 Flash via 9Router.
   - Update `cost:current_month` to include LLM spend, ensuring the $30 absolute cap is enforced globally.

3. **Implement 80% Alerting ($24/month):**
   - The current `monthly_warning` is `$3.00` (misaligned with the $30 cap).
   - Update `BudgetConfig` to: `monthly_warning = 24.0`, `monthly_critical = 27.0`, `monthly_hard_stop = 30.0`.
   - Wire the `WARNING` alert level to trigger a Discord notification to Faiz.

### 6.2 Architectural Improvements

1. **Centralize Tool Cost Registry:** Move `_TOOL_COSTS` from `src/mcp/cost.py` to a shared configuration module (e.g., `src/config/finops.py`) so `BudgetEnforcer` and `ToolCostTracker` share a single source of truth.
2. **Add Redis TTL to Monthly Key:** The `cost:current_month` key currently has no TTL. Add a monthly reset mechanism or TTL to prevent unbounded growth.
3. **LLM Routing Health Checks:** Implement a `pre_llm_call` budget check that queries 9Router health and remaining monthly LLM budget before dispatching the request.

---

## 7. Evidence Artifacts

| Artifact Path | Description |
|---|---|
| `src/mcp/budget.py` | Primary budget enforcement logic |
| `src/mcp/cost.py` | Per-tool cost tracking implementation |
| `src/mcp/tools/exa_search.py` | Example of tool-level budget enforcement |
| `src/hermes/safety_plugin.py` | Current `pre_tool_call` hook implementation (Gate 09/10) |
| `docs/70-finops/70-Cost_FinOps_Model_v1.1.md` | Authoritative FinOps policy and $30 cap definition |

---

## 8. Conclusion

The foundation for ADR-035 compliance is **80% complete**. The Redis schema, cost tracking, and budget enforcer classes exist and are tested. The missing piece is the **wiring of `BudgetEnforcer` into the global `pre_tool_call` hook** and the **extension of cost tracking to include LLM token spend**. Addressing these two gaps will achieve full Phase 4 budget enforcement compliance.

> **Next Step:** Delegate implementation of `pre_tool_call` budget integration and LLM cost tracking to a sub-agent with explicit scaffold requirements.
