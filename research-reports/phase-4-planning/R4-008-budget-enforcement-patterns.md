# R4-008: Budget Enforcement Patterns for AI Agent Systems

**Date**: 2026-06-05  
**Target**: Guinevere Phase 4 (MCP + Tools) Migration  
**Goal**: Implement per-tool cost tracking and budget enforcement ($30/month hard cap, $24 alert threshold) via pre-tool call hooks.

---

## 1. Executive Summary

Real-world open-source AI agent frameworks enforce budget limits through a combination of **pre-execution hooks**, **atomic Redis operations**, and **provider-specific cost metadata**. The most robust patterns avoid race conditions by using Redis Lua scripts for atomic "check-and-deduct" operations, while leveraging framework-level `before_tool_call` hooks to intercept execution before network requests are made. LiteLLM and OpenRouter provide native cost metadata that can be fed back into the tracking system for accurate reconciliation.

---

## 2. Pre-Tool Call Hook Patterns

Intercepting tool execution before it runs is the standard mechanism for budget enforcement. Three major frameworks demonstrate this pattern:

### 2.1 Hermes Agent (Native to Guinevere)
Hermes Agent explicitly supports a `pre_tool_call` hook that receives execution context before the tool runs.
- **Evidence**: `NousResearch/hermes-agent` passes `tool_name`, `args`, `task_id`, `session_id`, and `tool_call_id` to the hook.
- **Pattern**: The hook can return a blocking response or raise an exception to prevent execution.
- **Link**: [hermes-agent test_model_tools.py](https://github.com/NousResearch/hermes-agent/blob/main/tests/test_model_tools.py#L54-L107)

### 2.2 crewAI
Uses decorator-based hooks for tool execution.
- **Evidence**: `@before_tool_call` decorator intercepts `ToolCallHookContext`. Returning `False` or raising an exception blocks the tool.
- **Link**: [crewAI decorators.py](https://github.com/crewAIInc/crewAI/blob/main/lib/crewai/src/crewai/hooks/decorators.py#L188-L210)

### 2.3 Google ADK (Agent Development Kit)
Provides plugin-based callbacks that can short-circuit execution.
- **Evidence**: `before_tool_callback` receives `tool`, `tool_args`, and `tool_context`. Modifications or early returns prevent the underlying tool from executing.
- **Link**: [google/adk-python base_plugin.py](https://github.com/google/adk-python/blob/main/src/google/adk/plugins/base_plugin.py#L64-L78)

---

## 3. Redis Cost Counter Patterns (Increment, Check, Alert)

To prevent race conditions in concurrent agent executions, cost tracking must be atomic.

### 3.1 Atomic Lua Script (Check-and-Deduct)
The most robust pattern uses a Redis Lua script to atomically verify balance and deduct cost in a single operation.
- **Evidence**: `2API-Fuse` uses a Lua script that checks `if balance < cost then return 0` (blocked), otherwise `redis.call('hincrby', k, 'balance', -cost)` and returns `1` (allowed).
- **Link**: [2API-Fuse cache.py](https://github.com/fengwind2006/2API-Fuse/blob/main/app/core/redis/cache.py#L218-L225)

### 3.2 Hash Increment with TTL
For monthly rolling windows, storing spend in a Redis Hash with an expiration time is standard.
- **Evidence**: `openadserver` uses `redis.hincrbyfloat(key, "spent_today", float(cost))` and `redis.hincrbyfloat(key, "spent_total", float(cost))` followed by `redis.expire(key, 86400 * 2)`.
- **Link**: [openadserver budget.py](https://github.com/seanZhang414/openadserver/blob/main/liteads/rec_engine/filter/budget.py#L139-L145)
- **Evidence**: `inbox-zero` uses `redis.hincrbyfloat(key, "cost", cost)` for weekly usage tracking.
- **Link**: [inbox-zero usage.ts](https://github.com/elie222/inbox-zero/blob/main/apps/web/utils/redis/usage.ts#L431-L436)

---

## 4. Webhook Notification Patterns (Discord, Slack, Gotify)

When thresholds are hit, asynchronous webhook notifications are triggered.

### 4.1 LiteLLM Slack/Webhook Alerting
LiteLLM has built-in budget alerting that maps alert types to webhook URLs.
- **Evidence**: `alert_to_webhook_url` configuration maps `'budget_alerts'` to Slack/Discord webhook URLs. The `SlackAlerting` module evaluates `get_budget_alert_type` based on spend vs. max_budget.
- **Link**: [litellm slack_alerting.py](https://github.com/BerriAI/litellm/blob/litellm_internal_staging/litellm/integrations/SlackAlerting/slack_alerting.py#L16-L558)

### 4.2 Dedicated Webhook Module
- **Evidence**: `AgentBudget` provides a standalone `send_webhook(url, payload, timeout)` function that posts JSON payloads to generic webhook endpoints (e.g., Gotify, Discord) on budget events.
- **Link**: [agentbudget webhook.py](https://github.com/AgentBudget/agentbudget/blob/main/agentbudget/webhook.py#L1-L15)

### 4.3 Policy-Driven Guard
- **Evidence**: `cashclaw` defines a guard policy mapping events like `'budget_exceeded'` to specific webhook providers (`telegram`, `slack`, `discord`).
- **Link**: [cashclaw policy.js](https://github.com/ertugrulakben/cashclaw/blob/main/src/guard/policy.js#L31-L38)

---

## 5. Monthly Spend Caps & Auto-Shutoff

### 5.1 LiteLLM Budget Reset Jobs
LiteLLM handles monthly caps via background jobs that reset budget counters based on `budget_duration`.
- **Evidence**: `reset_budget_job.py` iterates through teams, users, and API keys, resetting spend counters when the duration window expires.
- **Link**: [litellm reset_budget_job.py](https://github.com/BerriAI/litellm/blob/litellm_internal_staging/litellm/proxy/common_utils/reset_budget_job.py#L5-L45)

### 5.2 SDK Output Sniffing (Fallback Shutoff)
When explicit cost tracking fails, some systems parse the LLM's own error output for billing caps.
- **Evidence**: `shannon` monitors Anthropic SDK output for strings like `"spending cap"` or `"spending limit"` to trigger an immediate halt and prevent further calls.
- **Link**: [shannon billing-detection.ts](https://github.com/KeygraphHQ/shannon/blob/main/apps/worker/src/utils/billing-detection.ts#L3-L19)

### 5.3 Token Budget State Machine
- **Evidence**: `suna` tracks `tokenBudget` in its goal config. When exceeded, the goal status transitions to `"budget_limited"`, pausing further agent iterations.
- **Link**: [suna config.ts](https://github.com/kortix-ai/suna/blob/main/core/kortix-master/opencode/plugin/kortix-system/goal/config.ts#L7-L36)

---

## 6. LiteLLM & OpenRouter Cost Data Exposure

To track actual costs (not just estimates), frameworks extract cost data from provider responses.

### 6.1 OpenRouter Cost Metadata
OpenRouter returns exact dollar costs in the response metadata, which SDKs parse and forward to tracking systems.
- **Evidence**: `AutoGPT` parses `payload.get("total_cost")` from the OpenRouter `/generation` response.
- **Link**: [AutoGPT openrouter_cost.py](https://github.com/Significant-Gravitas/AutoGPT/blob/master/autogpt_platform/backend/backend/copilot/sdk/openrouter_cost.py#L129-L280)
- **Evidence**: `Upsonic` wraps OpenAI usage with `_OpenRouterCostDetails` containing `upstream_inference_cost`.
- **Link**: [Upsonic openrouter.py](https://github.com/Upsonic/Upsonic/blob/master/src/upsonic/models/openrouter.py#L430-L456)
- **Evidence**: `Helicone` priority logic: `if cost and cost > 0: return cost` from `cost_details`.
- **Link**: [helicone openRouterUsageProcessor.ts](https://github.com/Helicone/helicone/blob/main/packages/cost/usage/openRouterUsageProcessor.ts#L1-L17)

### 6.2 LiteLLM Prometheus Metrics
LiteLLM exposes real-time budget metrics for external monitoring.
- **Evidence**: Metrics include `litellm_remaining_api_key_budget_metric`, `litellm_api_key_max_budget_metric`, and `litellm_api_key_budget_remaining_hours_metric`.
- **Link**: [litellm prometheus.py](https://github.com/BerriAI/litellm/blob/litellm_internal_staging/litellm/types/integrations/prometheus.py#L197-L219)

---

## 7. Recommended Architecture for Guinevere

Based on the evidence, the following architecture satisfies the $30 hard cap / $24 alert threshold requirement:

### 7.1 Data Model (Redis)
Use a Redis Hash with a 35-day TTL (to cover month boundaries safely):
```python
key = f"guinevere:llm_budget:{YYYY-MM}"
# Fields:
# - spent_estimated: float (incremented pre-call)
# - spent_actual: float (incremented post-call via OpenRouter/LiteLLM metadata)
# - last_alert_sent_at: timestamp (to prevent webhook spam)
```

### 7.2 Atomic Pre-Tool Call Hook (Hermes Agent)
Implement a `pre_tool_call` hook that executes a Redis Lua script:
```lua
-- Keys: KEYS[1] = budget key
-- Args: ARGV[1] = tool_cost_estimate, ARGV[2] = alert_threshold (24.0), ARGV[3] = hard_cap (30.0)
local current = tonumber(redis.call('hget', KEYS[1], 'spent_estimated') or '0')
local projected = current + tonumber(ARGV[1])

if projected > tonumber(ARGV[3]) then
    return "BLOCKED"
elseif projected > tonumber(ARGV[2]) then
    redis.call('hincrbyfloat', KEYS[1], 'spent_estimated', ARGV[1])
    return "WARNING"
else
    redis.call('hincrbyfloat', KEYS[1], 'spent_estimated', ARGV[1])
    return "ALLOWED"
end
```

### 7.3 Hook Response Handling
- **`ALLOWED`**: Proceed with tool execution.
- **`WARNING`**: Proceed with execution, but trigger an **asynchronous** webhook to Discord/Gotify. Include a debounce check (`last_alert_sent_at`) to avoid spam.
- **`BLOCKED`**: Abort tool execution. Return a structured error to the LLM: `{"error": "budget_exceeded", "message": "Monthly LLM budget cap of $30.00 reached. Tool execution halted."}`

### 7.4 Post-Call Reconciliation
- Use an `after_tool_call` hook (or LiteLLM callback) to read the **actual** cost from OpenRouter's `response_metadata["cost"]` or `cost_details`.
- Adjust the Redis hash: `spent_actual += actual_cost`. (The `spent_estimated` acts as a pessimistic guard; `spent_actual` is for accurate monthly reporting).

### 7.5 Webhook Payload Structure
```json
{
  "event": "budget_threshold_exceeded",
  "timestamp": "2026-06-05T10:00:00Z",
  "current_estimated_spend": 24.05,
  "hard_cap": 30.00,
  "triggering_tool": "exa_web_search_exa",
  "estimated_tool_cost": 0.01,
  "action_taken": "allowed_with_warning"
}
```

---

## 8. Anti-Patterns to Avoid

1. **Non-Atomic Redis Checks**: `GET` then `SET` without Lua scripts will cause race conditions if multiple sub-agents fire tools concurrently.
2. **Relying Solely on Estimates**: OpenRouter/LiteLLM provide exact costs. Always reconcile estimated pre-call deductions with actual post-call costs.
3. **Blocking the Main Thread for Webhooks**: Webhook calls must be fire-and-forget (e.g., `run_in_background=true` in Guinevere's task system) to avoid adding latency to the agent loop.
4. **Hardcoding Provider Costs**: Tool costs (e.g., Exa at $0.01) should be defined in a central configuration or fetched from LiteLLM's model cost map, not hardcoded in the hook logic.

---

## 9. Next Actions for Phase 4

1. **Define Tool Cost Registry**: Create a configuration mapping each MCP tool (brave_search, exa, websearch) to its per-call cost.
2. **Implement Redis Lua Script**: Write and test the atomic check-and-deduct script.
3. **Register Hermes `pre_tool_call` Hook**: Integrate the Lua script execution into the Hermes Agent lifecycle.
4. **Build Webhook Dispatcher**: Implement the Discord/Gotify notification logic with debounce protection.
5. **Add Post-Call Reconciliation**: Ensure OpenRouter/LiteLLM actual costs are fed back to Redis to correct the estimated spend.
