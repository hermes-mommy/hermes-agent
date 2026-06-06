# CostTracker State — Research Report

**Date:** 2026-06-06  
**Author:** Guinevere (Sisyphus-Junior — Research Agent)  
**Status:** COMPLETE  
**Scope:** `CostTracker` (P1), `LoopCostTracker`, `ToolCostTracker`, Redis DB5 key patterns, callsite wiring, fail-open/fail-closed behavior, monthly cap enforcement  
**Purpose:** Unblock Phase 6 CostTracker wiring implementation planning  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [CostTracker Implementation (`cost_tracker.py`)](#2-costtracker-implementation)
3. [All Redis DB5 Key Patterns](#3-all-redis-db5-key-patterns)
4. [CostTracker Callsites — `record_cost()`](#4-costtracker-callsites)
5. [CostTracker Callsites — Redis Client Extraction Only](#5-costtracker-callsites-redis-client-extraction-only)
6. [toolCostTracker — Dead but Complete](#6-toolcosttracker)
7. [LoopCostTracker — The Wrapper Layer](#7-loopcosttracker)
8. [MCP Tool Inline Cost Recording](#8-mcp-tool-inline-cost-recording)
9. [Monthly Cap and Status Thresholds](#9-monthly-cap-and-status-thresholds)
10. [Fail-Open / Fail-Closed Analysis](#10-fail-open--fail-closed-analysis)
11. [Redis DB5 Accessibility](#11-redis-db5-accessibility)
12. [Critical Gaps](#12-critical-gaps)
13. [Wiring Map Summary](#13-wiring-map-summary)
14. [Key Files Reference](#14-key-files-reference)

---

## 1. Executive Summary

| Metric | Value |
|---|---|
| Cost service classes | 3 (`CostTracker`, `LoopCostTracker`, `ToolCostTracker`) |
| Total Redis DB5 key patterns | 13 distinct patterns |
| `CostTracker.record_cost()` callsites | 4 call sites (2 Discord handlers + 1 loop wrapper + 0 in llm_router) |
| Files importing `CostTracker` | 7 files (2 for record_cost, 5 for Redis client extraction only) |
| `ToolCostTracker` production callers | **0** (dead code — deferred to P8) |
| Tools with inline cost recording | 3 of 16 (brave_search, exa_search, context7) |
| Tools with cost tracking entirely | 3 of 16 (13 tools have zero cost tracking) |
| Monthly cap default | $30.00 |
| Fail-closed at core level | Yes (`record_cost` raises) |
| Fail-open at handler level | Yes (exceptions caught and logged) |
| `llm_router.py` wired to CostTracker | **NO** — confirmed gap by 2 prior audits |

---

## 2. CostTracker Implementation (`cost_tracker.py`)

**File:** `src/core/services/cost_tracker.py` (68 lines)

```python
class CostTracker:
    def __init__(self, host="localhost", port=6380, db=5,
                 username="guinevere_core", password=None, decode_responses=True):
        self.redis = redis.Redis(...)

    def record_cost(self, model, input_tokens, output_tokens,
                    cost_per_1k_input, cost_per_1k_output):
        cost = (input_tokens/1000 * cost_per_1k_input +
                output_tokens/1000 * cost_per_1k_output)
        today = date.today().isoformat()
        month = date.today().strftime("%Y-%m")
        pipe = self.redis.pipeline()
        pipe.incrbyfloat("cost:current_month", cost)
        pipe.incrbyfloat("cost:current_day", cost)
        pipe.incrbyfloat(f"cost:by_model:{model}", cost)
        pipe.incrbyfloat(f"cost:daily:{today}", cost)
        pipe.incrbyfloat(f"cost:monthly:{month}", cost)
        pipe.execute()

    def check_budget(self) -> dict:
        current = float(self.redis.get("cost:current_month") or 0)
        cap = float(self.redis.get("budget:monthly_cap") or 30)
        return {current_month, monthly_cap, remaining, percent_used, status}
```

### Key Design Notes

- **Synchronous** — all methods are sync. Discord handlers wrap in `asyncio.to_thread()`.
- **`record_cost()` has no try/except** — exceptions from Redis propagate to caller. This means the *class itself* is fail-closed.
- **No TTL on any keys** — `cost:current_month`, `cost:current_day`, `cost:by_model:*`, `cost:daily:*`, `cost:monthly:*` are **never expired**. These are intended as permanent roll-up counters.
- **Uses pipeline** — atomic multi-key update via `INCRBYFLOAT` on 5 keys.
- **`check_budget()`** reads `cost:current_month` and `budget:monthly_cap`, returns status dict with 5 levels.

---

## 3. All Redis DB5 Key Patterns

### 3.1 CostTracker (LLM costs) — P1

| Key Pattern | Type | Written By | TTL | Example |
|---|---|---|---|---|
| `cost:current_month` | Float (aggregate) | `CostTracker.record_cost()` | None | `"12.345"` |
| `cost:current_day` | Float (aggregate) | `CostTracker.record_cost()` | None | `"1.234"` |
| `cost:by_model:{model}` | Float per model | `CostTracker.record_cost()` | None | `cost:by_model:ds/deepseek-v4-flash` |
| `cost:daily:{YYYY-MM-DD}` | Float per day | `CostTracker.record_cost()` | None | `cost:daily:2026-06-06` |
| `cost:monthly:{YYYY-MM}` | Float per month | `CostTracker.record_cost()` | None | `cost:monthly:2026-06` |

### 3.2 Budget Control Keys

| Key Pattern | Type | Written By | TTL | Example |
|---|---|---|---|---|
| `budget:monthly_cap` | String float | `cmd_budget.py`, `CostTracker.__init__` default | None | `"30.0"` |
| `cost:alert_threshold` | String float | `cmd_cost_alert.py` | None | `"10.0"` |
| `budget:block_counter` | Integer | Budget hook (planned) | None | `"0"` |

### 3.3 ToolCostTracker (MCP tool costs) — P6 (Dead Code)

| Key Pattern | Type | Written By | TTL | Example |
|---|---|---|---|---|
| `tool:cost:{name}:{YYYY-MM-DD}` | Float per tool per day | `ToolCostTracker.record_tool_cost()` | 7-day EXPIREAT | `tool:cost:brave_search:2026-06-06` |
| `tool:cost:total:{YYYY-MM-DD}` | Float aggregate per day | `ToolCostTracker.record_tool_cost()` | 7-day EXPIREAT | `tool:cost:total:2026-06-06` |

### 3.4 MCP Tool Inline Cost Keys

| Key Pattern | Type | Written By | TTL | Example |
|---|---|---|---|---|
| `tool:cost:{name}:{YYYY-MM-DD}` | Float per tool per day | `brave_search._record_cost()`, `exa_search._record_cost()`, `context7._record_cost()` | 0 (brave), 172800s (exa/context7) | `tool:cost:exa:2026-06-06` |

These keys use the SAME format as ToolCostTracker keys (tool prefix). However, the inline implementations do NOT update the `tool:cost:total:*` aggregate key.

### 3.5 LoopCostTracker Keys

| Key Pattern | Type | Written By | TTL | Example |
|---|---|---|---|---|
| `loop:cost:{loop_id}` | Float (total) + hash fields | `LoopCostTracker.record_loop_cost()` | None | `loop:cost:a1b2c3d4e5f6` |
| `loop:cost:{loop_id}:by_model:{model}` | Float per model + hash fields | `LoopCostTracker.record_loop_cost()` | None | `loop:cost:a1b2c3d4e5f6:by_model:deepseek` |
| `loop:cost:month:{YYYY-MM}` | Set of loop IDs | `LoopCostTracker.record_loop_cost()` | None | `loop:cost:month:2026-06` |

LoopCostTracker uses hash fields to store `calls`, `input_tokens`, `output_tokens` counters alongside the float cost value (stored via `INCRBYFLOAT` on the key itself, with hash fields via `HINCRBY`).

### 3.6 Observed Redis DB5 State

**NEGATIVE FINDING:** Redis DB5 is hosted on the remote VPS (`guinevere-vps` port 6380), not accessible from the local Windows development machine. Attempted connection timed out after 15 seconds. Actual key values and counts cannot be inspected from this environment. The VPS must be accessed via SSH for runtime verification.

---

## 4. CostTracker Callsites — `record_cost()`

### 4.1 `src/discord/conversational_handler.py` — Lines 557, 569

```python
# Step 12: Cost tracking (lines 550-582)
tracker = _get_cost_tracker()  # lazy singleton
if estimated_cost > 0:
    await asyncio.to_thread(tracker.record_cost, ...)  # line 557
else:
    await asyncio.to_thread(tracker.record_cost, ...)  # line 569
```

- **Called after** every successful LLM response in the `#guinevere-chat` channel pipeline.
- Uses module-level lazy singleton `_get_cost_tracker()`.
- Two branches:
  - If `estimated_cost_usd` in Hermes metadata > 0: uses Hermes-reported cost with `cost_per_1k_input=0.0, cost_per_1k_output=0.0`.
  - Otherwise: estimates from `MODELS[TaskType.CORE_REASONING]` config.
- **Wrapped in try/except** that logs warning (fail-open at handler level).
- `record_cost` is sync → wrapped in `asyncio.to_thread()`.

### 4.2 `src/discord/hermes_conversational.py` — Lines 612, 625

```python
# Step 11: Cost tracking (lines 603-638)
tracker = _get_cost_tracker()  # lazy singleton
if estimated_cost > 0:
    await asyncio.to_thread(tracker.record_cost, ...)  # line 612
else:
    await asyncio.to_thread(tracker.record_cost, ...)  # line 625
```

- Identical pattern to `conversational_handler.py`.
- Hermes-native handler variant.
- **Wrapped in try/except** that logs warning (fail-open at handler level).

### 4.3 `src/loops/cost.py` — Line 118

```python
# LoopCostTracker.record_loop_cost() lines 116-130
self._global_tracker.record_cost(
    model=model,
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    cost_per_1k_input=cost_per_1k_input,
    cost_per_1k_output=cost_per_1k_output,
)
```

- Called inside `LoopCostTracker.record_loop_cost()` AFTER the per-loop keys are written.
- **Wrapped in try/except** that logs error (fail-open at loop level).
- NOT wrapped in `asyncio.to_thread` — loops run synchronously.

### 4.4 `src/core/services/llm_router.py` — **MISSING**

**CRITICAL GAP:** `llm_router.py` (104 lines) has **zero references** to `CostTracker`, `cost_tracker`, or `record_cost`. The `chat()` method (lines 64-101) logs via structlog after a successful response but never calls `CostTracker.record_cost()`.

This is the central gap identified by:
- Auditor 6-2 audit (`research-reports/phase-6-7-planning/audit-62-cost-accuracy.md` — CRITICAL finding)
- Re-audit (`research-reports/phase-6-7-planning/reaudit-62-cost-accuracy.md` — requires Step 6.6A)
- Recheck context (`research-reports/phase-6-7-planning/recheck-context-phase6-cost.md` — Fix 2 blocking)

The Phase 6 batch plan (`docs/setup-evidence/hermes-migration/batch-plan-phase-6.md`) has a planned **Step 6.6A** that would insert `CostTracker.record_cost()` into `llm_router.py.chat()` after line 92, but this step has NOT been executed yet.

---

## 5. CostTracker Callsites — Redis Client Extraction Only

These files import `CostTracker` solely to get its `.redis` attribute for direct Redis queries. They do NOT call `record_cost()`.

### 5.1 `src/discord/cmd_cost.py` — Line 245-248

```python
def _get_redis_client() -> redis.Redis:
    from src.core.services.cost_tracker import CostTracker
    tracker = CostTracker()
    return cast(redis.Redis, cast(object, tracker.redis))
```

- Creates `CostTracker()` to get the `redis` attribute.
- Uses it to read `cost:current_day`, `cost:daily:*`, `cost:by_model:*`, `tool:cost:*` keys.
- Used by `/cost` slash command.

### 5.2 `src/discord/cmd_budget.py` — Line 287-290

```python
def _get_redis_client() -> redis.Redis:
    from src.core.services.cost_tracker import CostTracker
    tracker = CostTracker()
    return cast(redis.Redis, cast(object, tracker.redis))
```

- Same pattern as `cmd_cost.py`.
- Used by `/budget` slash command.

### 5.3 `src/discord/cmd_cost_alert.py` — Line 54-57

```python
def _get_redis_client() -> redis.Redis:
    from src.core.services.cost_tracker import CostTracker
    tracker = CostTracker()
    return cast(redis.Redis, cast(object, tracker.redis))
```

- Same pattern.
- Used by `/cost-alert` slash command.

### 5.4 `src/core/services/monthly_report.py` — Line 145-147

```python
def _get_redis_client() -> redis.Redis:
    from src.core.services.cost_tracker import CostTracker
    return cast(redis.Redis, cast(object, CostTracker().redis))
```

- Same pattern.
- Used by monthly APScheduler job.

---

## 6. ToolCostTracker — Dead but Complete

**File:** `src/mcp/cost.py` (241 lines)

### What exists

- `ToolCostTracker` class with:
  - `record_tool_cost(tool_name, cost_usd=None)` — pipeline with INCRBYFLOAT + EXPIREAT (7-day grace)
  - `get_tool_daily_cost(tool_name)` — read single key
  - `get_all_daily_costs()` — SCAN pattern `tool:cost:*:{today}`
  - `get_tool_monthly_cost(tool_name)` — sum last 30 daily keys
  - `get_tool_cost(tool_name)` — static lookup in `_TOOL_COSTS`
  - `is_variable_cost(tool_name)` — static check for `-1.0` cost
- `_TOOL_COSTS` dict with costs for 16 tools
- 462-line test suite (`tests/mcp/test_cost.py`) — comprehensive, mocked

### Production callers: ZERO

- `grep "ToolCostTracker\|from src.mcp.cost import" src/mcp/tools/*.py` → 0 matches
- `grep "ToolCostTracker" src/ --include="*.py"` → only definition file and test file
- Deferred to P8 per P6 audit remediation

### Known Issues

1. **Name mismatches** in `_TOOL_COSTS`: keys use short names (`exa`, `time`, `git`) that don't match file names (`exa_search`, `time_tools`, `git_tool`). Calling `record_tool_cost("exa_search")` would return -1.0 since the key `"exa_search"` is not in the dict — the dict key is `"exa"`.
2. **No calls to record_tool_cost anywhere** — the 3 inline tools (brave/exa/context7) use their own `_record_cost()` functions, not the centralized class.
3. **Inline tools don't update `tool:cost:total:*`** — the aggregate key that ToolCostTracker writes is never touched by the inline implementations.

---

## 7. LoopCostTracker — The Wrapper Layer

**File:** `src/loops/cost.py` (235 lines)

### Architecture

```
LoopCostTracker.record_loop_cost()
  ├── Per-loop Redis writes (loop:cost:{loop_id}, loop:cost:{loop_id}:by_model:{model}, loop:cost:month:{YYYY-MM})
  ├── Catches RedisError → returns 0.0 (fail-open)
  └── Calls self._global_tracker.record_cost()  ← CostTracker aggregate write
       └── Catches RedisError → logs error
```

### Wiring

- `LoopCostTracker` is created by `LoopManager.__init__()` (line 51).
- `LoopManager` catches exceptions during init and sets `cost_tracker = None`.
- `LoopManager._run_loop()` calls `cost_tracker.record_loop_cost()` inside each phase handler if `artifact_content.token_usage` is not None.
- **Current status:** the `token_usage` attribute is never populated (phase handlers return static templates), so `record_loop_cost()` is effectively a no-op at runtime.

### Key Details

- Key prefix: `loop:cost`
- Uses hash fields for counters (`calls`, `input_tokens`, `output_tokens`) alongside `INCRBYFLOAT` cost value
- Set-based month tracking via `SADD`
- Dedicated `get_loop_cost()` and `get_all_loop_costs()` query methods

---

## 8. MCP Tool Inline Cost Recording

### 8.1 `brave_search.py`

- `_record_cost(client: redis.Redis)` — inline function (line 76)
- Key: `tool:cost:brave_search:{YYYY-MM-DD}` ($0.01/call)
- Creates Redis client per-call (line 64-73)
- **No TTL** on cost keys (original — P6 remediation may have added)
- Called after successful API response (line 171)

### 8.2 `exa_search.py`

- `_record_cost(redis_client: aioredis.Redis, cost: float)` — async inline function (line 110)
- Key: `tool:cost:exa:{YYYY-MM-DD}` ($0.007/call)
- TTL: `expire(key, 172800)` — 2 days
- Budget check BEFORE API call (`_check_budget`, $5/day cap) — line 169
- Cost recorded AFTER successful API call — line 177
- Best-implemented tool (pre-check + post-record + TTL + pipeline)

### 8.3 `context7.py`

- Inline cost tracking with `INCR` (not INCRBYFLOAT — $0 cost, counts calls)
- Key: `tool:cost:context7:{YYYY-MM-DD}`
- TTL: `expire(key, 172800)` — 2 days
- Runs in `asyncio.to_thread` (sync Redis)
- Fire-and-forget, best-effort

### 8.4 Other 13 Tools — ZERO Cost Tracking

The remaining 13 tools (`fetch`, `filesystem`, `github`, `grep_app`, `obscura_cdp`, `sequential_thinking`, `time_tools`, `git_tool`, `postgres_tool`, `redis_tool`, `shell_tool`, `docker_tool`, `websearch`) have **no cost tracking at all**. Even tools with `$0.00` cost in `_TOOL_COSTS` do not track call counts.

---

## 9. Monthly Cap and Status Thresholds

### Default Configuration

| Parameter | Value | Source |
|---|---|---|
| Monthly cap | $30.00 | `CostTracker.check_budget()` default, `cmd_budget.py` |
| Alert threshold | $10.00 | `cmd_cost_alert.py` default |

### Status Levels (defined in `CostTracker._get_status` and duplicated in `cmd_budget.py`)

| Ratio | Status | Emoji |
|---|---|---|
| N/A (current < $1) | `NORMAL` | ✅ |
| current >= $1 | `NORMAL_ALERT` | 🟡 |
| >= 50% of cap | `WARNING` | ⚠️ |
| >= 83.3% (5/6) | `CRITICAL` | 🚨 |
| >= 100% | `HARD_STOP` | 🛑 |

### Budget Hook (Planned in Phase 6, Step 6.3)

The Hermes `pre_tool_call` budget hook (`~/.hermes/hooks/budget.py`) is planned with:
- `MONTHLY_LIMIT = 30.00`
- `ALERT_THRESHOLD = 0.80` (warn at $24)
- `BLOCK_THRESHOLD = 1.00` (block at $30)
- Reads `cost:current_month` from Redis DB5
- On block: exit code 1 + increment `budget:block_counter`
- On warn: exit code 2 + log
- On pass: exit code 0
- **Fail-open**: any exception returns `action: 'pass'` (exit code 0)

---

## 10. Fail-Open / Fail-Closed Analysis

### Per-Layer Analysis

| Layer | File | Behavior | Details |
|---|---|---|---|
| **Core** | `cost_tracker.py:record_cost()` | **Fail-closed** | No try/except — Redis exception propagates to caller |
| **Core** | `cost_tracker.py:check_budget()` | **Fail-open** | `float(self.redis.get(...) or 0)` — returns 0 on None, but Redis exception propagates |
| **Discord handler** | `conversational_handler.py:550-582` | **Fail-open** | `try/except Exception` logs warning, continues without recording cost |
| **Discord handler** | `hermes_conversational.py:603-638` | **Fail-open** | `try/except Exception` logs warning, continues without recording cost |
| **Loop** | `loops/cost.py:record_loop_cost()` | **Fail-open** | Catches `RedisError`, returns 0.0 for loop cost. Catches `RedisError` on global record too. |
| **Loop Manager** | `loops/manager.py:__init__` | **Fail-open** | Catches `Exception`, sets `cost_tracker = None` |
| **Loop Manager** | `loops/manager.py:_run_loop` | **Fail-open** | Checks `if self.cost_tracker is not None`, wraps in `try/except Exception` |
| **Budget hook** | Phase 6 Step 6.3 (planned) | **Fail-open** | Returns `action: 'pass'` on any exception (documented, acceptable trade-off) |
| **Planned Step 6.6A** | `llm_router.py` wiring (planned) | **Fail-closed** | `raise RuntimeError("LLM cost tracking failed")` after logging |

### Summary

The core `CostTracker` class itself is fail-closed (exceptions propagate). Every *consumer* wraps the call in a try/except to prevent cost tracking failures from crashing the main flow. The budget hook uses deliberate fail-open (cost enforcement is operational, not safety-critical).

Phase 6's planned Step 6.6A introduces fail-closed behavior at the LLM router layer: if `record_cost()` fails, the entire LLM response is aborted with `RuntimeError`.

---

## 11. Redis DB5 Accessibility

### Connection Configuration

| Parameter | Value |
|---|---|
| Host | `localhost` (127.0.0.1) |
| Port | 6380 |
| DB | 5 |
| Username | `guinevere_core` |
| Password | `REDIS_PASSWORD` env var |
| Encoding | `decode_responses=True` |

### Local Accessibility

**NEGATIVE FINDING:** Redis is running on the remote VPS (`guinevere-vps`), not locally. From the local Windows machine:
- `redis-cli` is not installed (`'redis-cli' is not recognized`)
- Python connection attempt timed out (15s timeout, no Redis available locally)
- Direct Redis inspection of DB5 key values is not possible from this environment

**To inspect DB5 from production:** SSH into the VPS and use:
```bash
ssh guinevere-vps
redis-cli -p 6380 -n 5 --user guinevere_core --pass "$REDIS_PASSWORD" KEYS '*'
```

---

## 12. Critical Gaps

### Gap 1: `llm_router.py` Does Not Call `CostTracker.record_cost()` (BLOCKING)

**Status:** Unresolved (planned as Step 6.6A in Phase 6 batch plan, not yet executed)

`src/core/services/llm_router.py`'s `chat()` method returns the LLM response at line 93 without any cost tracking call. This means:
- If Hermes routes through `llm_router.py` → costs are NOT recorded in Redis DB5
- Step 6.7 Redis verification would fail (zero keys)
- All Discord handler-level cost tracking is bypassed when LLM calls go through the router

**Evidence:**
```bash
grep -c "CostTracker\|record_cost\|cost_tracker" src/core/services/llm_router.py
# → 0 (confirmed)
```

### Gap 2: `ToolCostTracker` Is Dead Code

**Status:** Deferred to P8 (documented in P6 audit, P6-REMEDIATION-AUDIT)

The centralized MCP tool cost tracking class exists (241 lines, fully tested) but is imported by zero production files. Only 3 of 16 MCP tools track costs via inline functions.

### Gap 3: 13 of 16 MCP Tools Have Zero Cost Tracking

**Status:** Deferred (tied to Gap 2)

Tools with $0.00 cost per call should at minimum track call counts for auditability.

### Gap 4: Inline Tool Cost Keys Missing `tool:cost:total:*` Aggregate

The 3 inline implementations write `tool:cost:{name}:{YYYY-MM-DD}` but never update `tool:cost:total:{YYYY-MM-DD}`. Any consumer reading the aggregate key would see incomplete data.

### Gap 5: `cost_per_1k` Values Stale in `llm_router.py`

The pricing constants in `llm_router.py` (lines 35, 36, 45, 46, 53, 54) are off by 1.4x–3x vs current market pricing:

| Model | Current Code ($/1K) | Correct ($/1K) | Error |
|---|---|---|---|
| GPT-5.5 input | 0.0025 | 0.005 | 2x low |
| GPT-5.5 output | 0.01 | 0.03 | 3x low |
| DeepSeek V4 Flash input | 0.0001 | 0.00014 | 1.4x low |
| DeepSeek V4 Flash output | 0.0002 | 0.00028 | 1.4x low |

If CostTracker is wired into `llm_router.py` before these are corrected, recorded costs will be inaccurate.

### Gap 6: Redis DB5 Not Accessible from Local Dev

Cannot inspect live key values without SSH to VPS. Verification depends on production access.

---

## 13. Wiring Map Summary

### Code Paths for LLM Cost Recording

```
User message in #guinevere-chat
  ├──> conversational_handler.py
  │     ├── LLMRouter.chat() → ❌ NO record_cost
  │     └── After response → record_cost() via asyncio.to_thread ✅
  │
  ├──> hermes_conversational.py
  │     ├── HermesSessionAdapter.send_message() → ❌ NO record_cost
  │     └── After response → record_cost() via asyncio.to_thread ✅
  │
  └──> LoopManager._run_loop()
        └── Phase handler returns artifact → LoopCostTracker.record_loop_cost()
              └── Calls CostTracker.record_cost() ✅ (but token_usage always None currently)

MCP Tool Call
  ├──> brave_search → inline _record_cost() ✅ (key: tool:cost:brave_search:*)
  ├──> exa_search → inline _record_cost() ✅ (key: tool:cost:exa:*)
  ├──> context7 → inline _record_cost() ✅ (key: tool:cost:context7:*)
  └──> 13 other tools → ❌ NO cost tracking

Slash Commands (read-only)
  /cost      → cmd_cost.py → creates CostTracker() → reads Redis DB5
  /budget    → cmd_budget.py → creates CostTracker() → reads/writes Redis DB5
  /cost-alert → cmd_cost_alert.py → creates CostTracker() → reads/writes Redis DB5

Scheduled Jobs
  monthly_report.py → creates CostTracker() → reads Redis DB5 → posts to Discord
```

### Planned Wiring (Step 6.6A — Not Yet Executed)

```
llm_router.py.chat()
  ├── After line 92 (logger.info)
  ├── Insert:
  │     ct = CostTracker()
  │     ct.record_cost(model=config.name, input_tokens=..., ...)
  │     (fail-closed: raises RuntimeError on failure)
  └── Then continue to return result
```

---

## 14. Key Files Reference

| File | Lines | Role | Status |
|---|---|---|---|
| `src/core/services/cost_tracker.py` | 68 | Core CostTracker class | ✅ Active |
| `src/core/services/llm_router.py` | 104 | LLM routing (missing CostTracker) | ⚠️ Needs wiring |
| `src/loops/cost.py` | 235 | LoopCostTracker wrapper | ✅ Active (no-op currently) |
| `src/loops/manager.py` | 304 | Loop manager (creates LoopCostTracker) | ✅ Active |
| `src/mcp/cost.py` | 241 | ToolCostTracker class (dead code) | ❌ Dead |
| `src/mcp/tools/brave_search.py` | 186 | Inline cost tracking | ✅ Partial (no TTL originally) |
| `src/mcp/tools/exa_search.py` | 212 | Inline cost tracking + budget | ✅ Best |
| `src/mcp/tools/context7.py` | 407 | Inline cost tracking | ✅ Partial |
| `src/discord/conversational_handler.py` | 634 | Discord handler (calls record_cost) | ✅ Active |
| `src/discord/hermes_conversational.py` | 691 | Hermes Discord handler (calls record_cost) | ✅ Active |
| `src/discord/cmd_cost.py` | 662 | /cost command | ✅ Active |
| `src/discord/cmd_budget.py` | 643 | /budget command | ✅ Active |
| `src/discord/cmd_cost_alert.py` | 196 | /cost-alert command | ✅ Active |
| `src/core/services/monthly_report.py` | 538 | Monthly FinOps report | ✅ Active |
| `tests/mcp/test_cost.py` | 462 | ToolCostTracker tests | ✅ Comprehensive |
| `tests/discord/test_conversational_handler.py` | 701 | Discord handler tests | ✅ Covers cost tracking |
| `docs/setup-evidence/hermes-migration/batch-plan-phase-6.md` | ~2400 | Phase 6 plan (Step 6.6A planned) | ⚠️ Not executed |

---

## Appendix A: Verification Commands

### Check if CostTracker is wired in llm_router.py
```bash
grep -c "CostTracker\|record_cost\|cost_tracker" src/core/services/llm_router.py
# Expected after Phase 6: ≥ 2 (import + call)
```

### Check live Redis DB5 (on VPS)
```bash
ssh guinevere-vps
redis-cli -p 6380 -n 5 --user guinevere_core --pass "$REDIS_PASSWORD" KEYS '*'
redis-cli -p 6380 -n 5 --user guinevere_core --pass "$REDIS_PASSWORD" GET cost:current_month
redis-cli -p 6380 -n 5 --user guinevere_core --pass "$REDIS_PASSWORD" GET budget:monthly_cap
```

### Verify cost_per_1k values
```bash
python -c "
from src.core.services.llm_router import MODELS, TaskType
expected = {
    TaskType.CORE_REASONING: (0.005, 0.03),
    TaskType.SUB_AGENT: (0.00014, 0.00028),
    TaskType.FALLBACK: (0.00014, 0.00028),
}
for tt, mc in MODELS.items():
    e_in, e_out = expected[tt]
    errs = []
    if abs(mc.cost_per_1k_input - e_in) > 1e-6:
        errs.append(f'input: got {mc.cost_per_1k_input}, expected {e_in}')
    if abs(mc.cost_per_1k_output - e_out) > 1e-6:
        errs.append(f'output: got {mc.cost_per_1k_output}, expected {e_out}')
    if errs:
        print(f'FAIL: {tt.value} — {\"; \".join(errs)}')
    else:
        print(f'PASS: {tt.value}')
"
```

---

## Appendix B: Prior Audit References

| Report | Path | Key Finding |
|---|---|---|
| Auditor 6-2 (Cost Accuracy) | `research-reports/phase-6-7-planning/audit-62-cost-accuracy.md` | CRITICAL: llm_router.py has zero CostTracker references |
| Re-audit 6-2 | `research-reports/phase-6-7-planning/reaudit-62-cost-accuracy.md` | PASS after planning fix (Step 6.6A) but plan not executed |
| Recheck Context | `research-reports/phase-6-7-planning/recheck-context-phase6-cost.md` | 9 fixes identified, 4 blocking |
| P6 Cost Tracking Audit | `audit-reports/P6/P6-FINAL-AUDIT/D05-cost-tracking.md` | FAIL: ToolCostTracker dead code, brave TTL missing |
| Phase 4 Budget Gap | `research-reports/phase-4-execution/05-budget-gap.md` | ToolCostTracker zero-referenced in production |

---

## Footer

| Field | Value |
|---|---|
| Report Date | 2026-06-06 |
| Author | Guinevere (Sisyphus-Junior — Research Agent) |
| Scope | CostTracker + Redis DB5 + All Callsites + Fail-Open/Closed + Cap Behavior |
| Status | COMPLETE |
| Next Action | Wire `CostTracker.record_cost()` into `llm_router.py.chat()` (Step 6.6A) and update stale `cost_per_1k` values before Phase 6 execution |
