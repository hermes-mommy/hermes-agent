# D05 — COST TRACKING (P6 MCP Tools)

**Audit Date:** 2026-06-03
**Auditor:** Guinevere (Sisyphus-Junior)
**Dimension:** 5 — Cost Tracking
**Scope:** `src/mcp/cost.py`, `src/mcp/budget.py`, all 16 `src/mcp/tools/*.py`
**P6 Requirements:** P6-020 (per-tool cost in Redis DB5), P6-021 (budget enforcement: $5/day Exa cap → Brave fallback)
**Verdict:** **FAIL — CRITICAL DEFECTS FOUND**

---

## §1 Executive Summary

P6 mandates centralized per-tool cost tracking via `ToolCostTracker` (P6-020) and budget enforcement via `BudgetEnforcer` (P6-021). **Both modules are dead code** — defined but never imported or called by any of the 16 tool modules. Only 3 tools have ad-hoc inline cost tracking, 13 are completely untracked, and the centralized architecture specified by the requirements is entirely absent from the runtime code path.

| Metric | Count | Status |
|---|---|---|
| Tools with cost tracking | 3 / 16 (18.75%) | ❌ FAIL |
| Tools using centralized `ToolCostTracker` | 0 / 16 | ❌ FAIL |
| Tools using centralized `BudgetEnforcer` | 0 / 16 | ❌ FAIL |
| Tools with budget enforcement | 1 / 16 (exa_search only) | ❌ FAIL |
| Inline tracking with correct key format | 3 / 3 | ✅ PASS |
| Inline tracking with TTL/expire | 2 / 3 (brave missing) | ❌ FAIL |
| Hardcoded Redis passwords | 0 | ✅ PASS |

---

## §2 DEAD CODE: ToolCostTracker and BudgetEnforcer

### 2.1 Evidence of Non-Import

Performed exhaustive grep across all `src/mcp/tools/*.py`:

```bash
# Search 1: Import statements
grep "from src\.mcp\.cost import" src/mcp/tools/*.py
grep "from src\.mcp\.budget import" src/mcp/tools/*.py
# Result: ZERO matches

# Search 2: Class references
grep "ToolCostTracker" src/mcp/tools/*.py
grep "BudgetEnforcer" src/mcp/tools/*.py
# Result: ZERO matches
```

Neither `ToolCostTracker` nor `BudgetEnforcer` is referenced anywhere outside their own defining files.

### 2.2 What They Provide (Unused)

**`ToolCostTracker`** (`src/mcp/cost.py`, 241 lines):
- Redis DB5 connection (port 6380, user `guinevere_core`)
- Key format: `tool:cost:{name}:YYYY-MM-DD` + `tool:cost:total:YYYY-MM-DD`
- `record_tool_cost()` — pipeline with INCRBYFLOAT + EXPIREAT (7-day grace)
- `get_tool_daily_cost()`, `get_all_daily_costs()`, `get_tool_monthly_cost()`
- Fixed cost table for all 16 tools (`_TOOL_COSTS` dict)
- None of this is ever called.

**`BudgetEnforcer`** (`src/mcp/budget.py`, 364 lines):
- `BudgetConfig`: $5/day Exa, $3/day Brave, $10/day global, $30/month absolute
- `check_budget()` — raises `BudgetExceeded` on cap breach
- `get_fallback_tool()` — Exa → Brave routing
- `record_and_check()` — combined record + enforce
- `get_monthly_status()` — full dashboard
- Alert levels: NORMAL, WARNING, CRITICAL, HARD_STOP
- None of this is ever called.

### 2.3 Circular Import Danger

`budget.py` line 24 imports FROM a tool:
```python
from src.mcp.tools.exa_search import BudgetExceeded
```

This means `budget.py` depends on `exa_search.py`. If any tool ever imports `BudgetEnforcer`, a circular dependency chain is triggered:
```
tools/brave_search.py → budget.py → tools/exa_search.py
```

This is a latent structural defect. `BudgetExceeded` should be defined in a shared exception module, not inside a tool.

---

## §3 Actual Inline Cost Tracking (Ad-Hoc)

Three tools implement their own cost tracking without the centralized modules:

### 3.1 brave_search.py ✅ (with defect)

| Attribute | Value |
|---|---|
| Key format | `tool:cost:brave_search:YYYY-MM-DD` |
| Cost per call | $0.01 (`_COST_PER_SEARCH`) |
| Redis connection | `redis.Redis`, port 6380, DB5, `guinevere_core` |
| Operation | `incrbyfloat` (line 80) |
| TTL / expireat | **NONE — DEFECT** |
| Budget enforcement | None |
| When recorded | After successful API response (line 162) |

**Defect: No TTL on cost keys.** Unlike `exa_search` (172800s) and `context7` (172800s), `brave_search` never sets `expire` or `expireat` on its cost keys. Keys accumulate indefinitely, wasting Redis memory without ever being cleaned up.

### 3.2 exa_search.py ✅

| Attribute | Value |
|---|---|
| Key format | `tool:cost:exa:YYYY-MM-DD` |
| Cost per call | $0.007 (`_COST_PER_REQUEST`) |
| Daily cap | $5.00 (`_DAILY_CAP`) |
| Redis connection | `redis.asyncio.Redis`, port 6380, DB5, `guinevere_core` |
| Operation | `incrbyfloat` in pipeline (line 114) |
| TTL | `expire(key, 172800)` — 2 days (line 115) |
| Budget enforcement | ✅ `_check_budget()` BEFORE API call (line 169) |
| When recorded | After successful API response (line 177) |
| Defines | `BudgetExceeded` exception (imported by `budget.py` and `websearch.py`) |

This is the best-implemented tool. It has both budget enforcement (pre-call check) and cost recording (post-call) with proper TTL.

### 3.3 context7.py ✅

| Attribute | Value |
|---|---|
| Key format | `tool:cost:context7:YYYY-MM-DD` |
| Cost per call | Free tier ($0) — tracks call count via `INCR` |
| Redis connection | Sync `redis.Redis`, port 6380, DB5, `guinevere_core` |
| Operation | `incr(key)` (line 171) — counts calls, not dollars |
| TTL | `expire(key, 172800)` — 2 days (line 172) |
| Budget enforcement | None (free tier) |
| When recorded | Both `context7_resolve` (line 279) and `context7_query` (line 347) |
| Delivery | `asyncio.to_thread` + fire-and-forget, best-effort |

### 3.4 websearch.py — Proxy Only

| Attribute | Value |
|---|---|
| Own cost tracking | **None** |
| imports `redis` | Only for catching `redis.RedisError` in exception handlers (lines 88, 129) |
| Budget enforcement | Indirect via delegating to `exa_search`/`brave_search` which do their own tracking |
| `BudgetExceeded` handling | Catches and handles fallback routing (lines 82, 117) |

`websearch` is a composite router — it doesn't track its own costs but the delegated tools do. This is architecturally correct: costs are tracked at the leaf tool level.

---

## §4 Untracked Tools (13 of 16)

These 13 tools have **zero cost tracking** — no Redis calls, no cost keys, no budget checks:

| # | Tool | File | cost.py `_TOOL_COSTS` | Has Tracking |
|---|---|---|---|---|
| 1 | brave_search | `brave_search.py` | $0.01 | ✅ Inline |
| 2 | context7 | `context7.py` | $0.00 | ✅ Inline (call count) |
| 3 | exa_search | `exa_search.py` | $0.007 | ✅ Inline + budget |
| 4 | websearch | `websearch.py` | variable (-1.0) | ⚠️ Proxy (delegates) |
| 5 | fetch | `fetch.py` | $0.00 | ❌ |
| 6 | filesystem | `filesystem.py` | $0.00 | ❌ |
| 7 | github | `github.py` | $0.00 | ❌ |
| 8 | grep_app | `grep_app.py` | $0.00 | ❌ |
| 9 | obscura_cdp | `obscura_cdp.py` | $0.00 | ❌ |
| 10 | sequential_thinking | `sequential_thinking.py` | $0.00 | ❌ |
| 11 | time_tools | `time_tools.py` | $0.00 | ❌ |
| 12 | git_tool | `git_tool.py` | $0.00 | ❌ |
| 13 | postgres_tool | `postgres_tool.py` | $0.00 | ❌ |
| 14 | redis_tool | `redis_tool.py` | $0.00 | ❌ |
| 15 | shell_tool | `shell_tool.py` | $0.00 | ❌ |
| 16 | docker_tool | `docker_tool.py` | $0.00 | ❌ |

### Comment on $0-cost tools

Even tools with $0.00 cost should be tracked (call count at minimum) to:
- Detect unexpected usage spikes
- Provide audit trails
- Enable Prometheus dashboards for tool utilization
- Verify the $0 assumption holds over time

The `redis_tool.py` itself defaults to DB5 (the cost tracking namespace) but paradoxically has no cost tracking for its own usage.

---

## §5 Key Format Consistency

All three inline implementations follow `tool:cost:{name}:YYYY-MM-DD`:

| Tool | Inline Key | cost.py Design |
|---|---|---|
| brave_search | `tool:cost:brave_search:YYYY-MM-DD` | `tool:cost:brave_search:YYYY-MM-DD` |
| exa | `tool:cost:exa:YYYY-MM-DD` | `tool:cost:exa:YYYY-MM-DD` |
| context7 | `tool:cost:context7:YYYY-MM-DD` | `tool:cost:context7:YYYY-MM-DD` |

**Names are consistent.** However, `cost.py` also tracks a `tool:cost:total:YYYY-MM-DD` aggregate key — the inline implementations do NOT update this aggregate key. This means any tool consuming the aggregate (BudgetEnforcer's `_get_global_daily_spend()`) would never see costs from the inline-tracked tools.

### Name Mismatches in `_TOOL_COSTS` Dict

The `cost.py` `_TOOL_COSTS` dictionary uses short names that don't match actual file names:

| cost.py Name | Actual File | Mismatch? |
|---|---|---|
| `exa` | `exa_search.py` | ❌ Mismatch |
| `time` | `time_tools.py` | ❌ Mismatch |
| `git` | `git_tool.py` | ❌ Mismatch |
| `postgres` | `postgres_tool.py` | ❌ Mismatch |
| `redis` | `redis_tool.py` | ❌ Mismatch |
| `shell` | `shell_tool.py` | ❌ Mismatch |
| `docker` | `docker_tool.py` | ❌ Mismatch |

If `ToolCostTracker.record_tool_cost("exa_search")` were ever called, it would treat it as a variable-cost tool (returning -1.0) since "exa_search" is not in the dict — the dict key is "exa".

---

## §6 TTL / Expiry Defect in brave_search

### Confirmed: No TTL on brave_search cost keys

```python
# brave_search.py lines 76-83
def _record_cost(client: redis.Redis) -> None:
    """Increment the daily cost counter in Redis."""
    today = date.today().isoformat()
    key = f"{_REDIS_KEY_PREFIX}:{today}"
    client.incrbyfloat(key, _COST_PER_SEARCH)
    # ⚠️ NO expire / expireat call!
```

Compare with the other two:
- `exa_search.py`: `pipe.expire(key, 172800)` ✅
- `context7.py`: `client.expire(key, 86400 * 2)` ✅

And with `cost.py`'s design: `pipe.expireat(tool_key, expire_ts)` (7-day grace) ✅

**Impact:** Brave search cost keys will accumulate in Redis DB5 indefinitely. Over months of operation, this causes unbounded key growth. While each key stores only a float value (negligible memory), the key count itself grows linearly with no cleanup mechanism.

---

## §7 Redis Configuration Audit

All implementations use identical Redis configuration:

| Attribute | cost.py | budget.py | brave_search | exa_search | context7 | P1 cost_tracker |
|---|---|---|---|---|---|---|
| Host | localhost | localhost | localhost | localhost | localhost | localhost |
| Port | 6380 | 6380 | 6380 | 6380 | 6380 | 6380 |
| DB | 5 | 5 | 5 | 5 | 5 | 5 |
| Username | guinevere_core | guinevere_core | guinevere_core | guinevere_core | guinevere_core | guinevere_core |
| Password | env `REDIS_PASSWORD` | env `REDIS_PASSWORD` | env `REDIS_PASSWORD` | env `REDIS_PASSWORD` | env `REDIS_PASSWORD` | env `REDIS_PASSWORD` |
| Hardcoded pwd | None | None | None | None | None | None |

**PASS: No hardcoded passwords. All implementations read from environment.**

### Difference: context7 is sync-only

`context7.py` uses sync `redis.Redis` wrapped in `asyncio.to_thread()`. All others use async (`redis.asyncio.Redis`) or are unused. This is a minor inconsistency but functional.

---

## §8 P1 Cost Tracker vs P6 Comparison

| Aspect | P1 `CostTracker` | P6 `ToolCostTracker` |
|---|---|---|
| Location | `src/core/services/cost_tracker.py` | `src/mcp/cost.py` |
| Purpose | LLM token cost tracking | MCP per-tool cost tracking |
| Key namespace | `cost:current_month`, `cost:daily:*`, `cost:by_model:*` | `tool:cost:{name}:YYYY-MM-DD` |
| Usage | Imported by `src/loops/cost.py` | **NOT imported anywhere** |
| Budget | Has `check_budget()` with alert levels | No budget enforcement |
| Monthly cap | $30 (configurable via Redis key) | $30 (hardcoded) |
| TTL handling | None (roll-up keys, not daily) | EXPIREAT with 7-day grace |
| Model tracking | Yes (per-model breakdown) | N/A |

**Key difference:** P1 tracks LLM costs (input/output tokens by model), P6 tracks MCP tool calls. They use separate key namespaces in the same Redis DB5. This is intentional and correct — no collision.

The P1 `CostTracker` is actually used (via `src/loops/cost.py`). The P6 `ToolCostTracker` is dead code.

---

## §9 Findings Summary

### CRITICAL (FAIL)

| ID | Finding | Impact |
|---|---|---|
| D05-C01 | `ToolCostTracker` is dead code — never imported or called | P6-020 requirement unmet: no centralized tracking |
| D05-C02 | `BudgetEnforcer` is dead code — never imported or called | P6-021 requirement unmet: no centralized budget enforcement |
| D05-C03 | 13 of 16 tools have no cost tracking whatsoever | 81% of tools are invisible to FinOps |
| D05-C04 | `budget.py` has latent circular import: imports from `exa_search.py` | Blocks any future import of BudgetEnforcer by tool modules |

### HIGH

| ID | Finding | Impact |
|---|---|---|
| D05-H01 | `brave_search.py` has no TTL/expire on cost keys | Unbounded Redis key growth over time |
| D05-H02 | Inline cost tracking does not update `tool:cost:total:*` aggregate | BudgetEnforcer global daily cap broken even if it were used |
| D05-H03 | `cost.py` `_TOOL_COSTS` uses abbreviated names (exa, git, time) that don't match file names | Lookup failures if centralized tracker ever connected |

### MEDIUM

| ID | Finding | Impact |
|---|---|---|
| D05-M01 | context7 uses sync Redis via `asyncio.to_thread` while exa uses async | Inconsistent pattern; context7 approach is fine but different |
| D05-M02 | No tool tracks call count for $0-cost tools | Cannot detect abuse or verify $0 cost assumption |
| D05-M03 | `redis_tool.py` defaults to DB5 (cost namespace) but doesn't track its own usage | Meta-irony: Redis tool in cost DB with no cost tracking |

### PASS

| ID | Finding |
|---|---|
| D05-P01 | No hardcoded Redis passwords — all use `REDIS_PASSWORD` env var |
| D05-P02 | All implementations use consistent Redis config (host/port/DB/username) |
| D05-P03 | Key format `tool:cost:{name}:YYYY-MM-DD` consistent across all 3 inline implementations |
| D05-P04 | `exa_search.py` has correct pre-call budget check + post-call cost record + TTL |
| D05-P05 | `websearch.py` correctly delegates cost tracking to leaf tools (brave/exa) |

---

## §10 Recommendations

1. **Fix C01/C02 (CRITICAL):** Wire `ToolCostTracker` and `BudgetEnforcer` into a unified MCP tool dispatch layer — a single `MCPToolRegistry` or `with_cost_tracking()` decorator that wraps all tool calls. The current approach of requiring each tool to manually call cost APIs is architecturally fragile.

2. **Fix C03 (CRITICAL):** Add cost tracking to all 13 untracked tools. Even $0-cost tools should log call counts. Use the centralized `ToolCostTracker`, not ad-hoc inline code.

3. **Fix C04 (CRITICAL):** Extract `BudgetExceeded` from `exa_search.py` into `src/mcp/exceptions.py` to break the circular import chain.

4. **Fix H01 (HIGH):** Add `expire` TTL to `brave_search._record_cost()` — use 172800 seconds (2 days) consistent with exa and context7.

5. **Fix H02 (HIGH):** Ensure the centralized tracker updates `tool:cost:total:*` aggregate keys that the inline implementations currently miss.

6. **Fix H03 (HIGH):** Update `_TOOL_COSTS` dict keys to match actual tool registration names (e.g., `"exa_search"` not `"exa"`).

7. **Consider:** Implement `BudgetEnforcer` as middleware/async context manager that wraps every MCP tool call with automatic budget check + cost recording, eliminating the need for per-tool boilerplate.

---

## §11 Verification Evidence

### Files Read

| File | Lines |
|---|---|
| `src/mcp/cost.py` | 241 |
| `src/mcp/budget.py` | 364 |
| `src/mcp/tools/brave_search.py` | 177 |
| `src/mcp/tools/exa_search.py` | 212 |
| `src/mcp/tools/context7.py` | 407 |
| `src/mcp/tools/websearch.py` | 164 |
| `src/core/services/cost_tracker.py` | 68 |

### Grep Results

| Search | Pattern | Files | Matches |
|---|---|---|---|
| ToolCostTracker/BudgetEnforcer in tools/ | `ToolCostTracker\|BudgetEnforcer` | 17 | 0 |
| Import from cost/budget in tools/ | `from src\.mcp\.(cost\|budget) import` | 17 | 0 |
| cost/budget references in all of src/mcp/ | `ToolCostTracker\|BudgetEnforcer\|from src\.mcp\.(cost\|budget)` | 19+ | 2 (self-definition only) |
| Redis/cost patterns in tools/ | `redis\|Redis\|cost\|COST\|tool:cost\|incrbyfloat\|incr\b` | 17 | 131 (only brave/exa/context7/websearch) |
| TTL/expire in brave_search | `expire\|EXPIRE\|TTL\|ttl` | 1 | 0 (CONFIRMED MISSING) |
| TTL/expire in exa_search | `expire\|EXPIRE\|TTL\|ttl` | 1 | 3 (present) |

---

## §12 Auditor Gate

| Criterion | Status |
|---|---|
| All 16 tools inspected for cost tracking | ✅ |
| ToolCostTracker import chain verified (zero callers) | ✅ |
| BudgetEnforcer import chain verified (zero callers) | ✅ |
| Inline cost tracking implementations read and analyzed | ✅ |
| Redis TTL/expiry verified for all 3 inline trackers | ✅ |
| P1 vs P6 cost_tracker comparison complete | ✅ |
| BudgetExceeded import chain traced | ✅ |
| Key format consistency checked | ✅ |
| No hardcoded secrets found | ✅ |

**Auditor Verdict:** FAIL — 4 CRITICAL, 3 HIGH, 3 MEDIUM findings. P6-020 and P6-021 are not implemented in the runtime code path. The centralized modules exist but are completely disconnected from the tools they are meant to govern.

---

## §13 Footer

| Field | Value |
|---|---|
| Audit Date | 2026-06-03 |
| Auditor | Guinevere (Sisyphus-Junior) |
| Report Path | `audit-reports/P6/P6-FINAL-AUDIT/D05-cost-tracking.md` |
| Scope | P6 MCP Tools — Dimension 5: Cost Tracking |
| Tools Audited | 16 / 16 |
| Requirements Checked | P6-020, P6-021 |
| Verdict | **FAIL** |
| Next Action | Implement D05-RECOMMENDATIONS §10 items 1-7 before P6 sign-off |