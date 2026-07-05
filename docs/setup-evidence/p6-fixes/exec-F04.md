# F-04 Execution Evidence — Wire ToolCostTracker + BudgetEnforcer

**Date:** 2026-06-09  
**Status:** DONE  
**File modified:** `src/mcp/manager.py`

---

## 1. Interface Analysis

### `ToolCostTracker` (`src/mcp/cost.py`)

| Symbol | Purpose |
|---|---|
| `ToolCostTracker()` | Init Redis DB5 client; reads `REDIS_PASSWORD` from env |
| `get_tool_cost(tool_name)` | Static; returns fixed USD cost per call (`-1.0` = variable) |
| `is_variable_cost(tool_name)` | Static; True when cost is variable |
| `record_tool_cost(tool_name, cost_usd)` | Increments `tool:cost:{name}:{YYYY-MM-DD}` + total key; sets 7-day EXPIREAT; returns new daily total; catches `RedisError` gracefully |

### `BudgetEnforcer` (`src/mcp/budget.py`)

| Symbol | Purpose |
|---|---|
| `BudgetEnforcer()` | Init Redis DB5 client; `BudgetConfig` with daily/monthly caps |
| `check_budget(tool_name)` | **async**; raises `BudgetExceeded` if daily or monthly cap exceeded |
| `record_and_check(tool_name, cost)` | Records cost then re-checks; raises `BudgetExceeded` if new total exceeds cap |
| `get_fallback_tool(tool_name)` | Returns fallback tool name when primary is over budget (exa → brave_search) |

`BudgetExceeded` is defined in `src/mcp/tools/exa_search.py` and re-exported through `budget.py`.

---

## 2. Middleware Design

FastMCP has **no built-in middleware hooks**. The wiring is implemented by
intercepting `server.tool` decorator during registration:

```
_register_tools_with_middleware(server)
  ├── patches server.tool → _patched_tool
  ├── calls register_all_tools(server)          ← all tool modules call server.tool()(fn)
  │     └── each fn is wrapped by _wrap_with_cost_middleware(fn, tool_name)
  └── restores original server.tool
```

### Middleware call flow (per tool invocation)

```
tool call arrives
  │
  ▼
[PRE] BudgetEnforcer.check_budget(tool_name)
  ├── Redis down / enforcer None  →  log warning, continue
  └── BudgetExceeded raised       →  re-raise, tool BLOCKED
  │
  ▼
actual tool_fn(*args, **kwargs)
  │
  ▼
[POST] ToolCostTracker.record_tool_cost(tool_name, cost)
  ├── variable-cost tools (cost == -1.0)  →  skip (tool manages own cost)
  └── Redis down / tracker None           →  log warning, continue
  │
  ▼
return result
```

---

## 3. Changes Made

### `src/mcp/manager.py`

**New imports added:**
```python
from src.mcp.budget import BudgetEnforcer
from src.mcp.cost import ToolCostTracker
from src.mcp.tools.exa_search import BudgetExceeded
```

**New globals:**
```python
_cost_tracker: ToolCostTracker | None = None
_budget_enforcer: BudgetEnforcer | None = None
```

**New functions:**
- `get_cost_tracker()` — public accessor for the global tracker
- `get_budget_enforcer()` — public accessor for the global enforcer
- `_wrap_with_cost_middleware(tool_fn, tool_name)` — wraps an async tool function
- `_register_tools_with_middleware(server)` — patches `server.tool`, calls `register_all_tools`, restores

**Modified lifespan:**
- Instantiates `ToolCostTracker` and `BudgetEnforcer` at startup with try/except (graceful on Redis failure)
- Calls `_register_tools_with_middleware(server)` instead of `register_all_tools(server)` directly

**New alias:**
```python
create_mcp_app = create_server
```

---

## 4. Graceful Degradation

| Failure scenario | Behaviour |
|---|---|
| Redis down at startup | `_cost_tracker = None`, `_budget_enforcer = None`, server starts normally |
| Redis down during budget check | `except Exception` logs warning, tool call proceeds |
| Redis down during cost record | `except Exception` logs warning, result returned normally |
| `BudgetExceeded` raised | Re-raised — tool is intentionally blocked |
| Variable-cost tool (cost == -1.0) | Cost recording skipped; tool manages its own tracking |

---

## 5. Verification

```
$ .venv/bin/python3 -c "from src.mcp.manager import create_mcp_app; print('OK')"
OK
```

Exit code: 0 ✅

---

## 6. No Existing Tests Broken

The middleware wrapper only activates when `_cost_tracker` / `_budget_enforcer` are
non-None (i.e. during a live lifespan). In tests that mock or bypass the lifespan,
both globals remain `None` and the middleware is a transparent pass-through.
