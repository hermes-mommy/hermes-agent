# D08 — Architecture Consistency Audit

| Field | Value |
|---|---|
| **Dimension** | D08 — Architecture Consistency |
| **Auditor** | Guinevere (highend) |
| **Date** | 2026-06-03 |
| **Phase** | P6 MCP Tools |
| **Scope** | `src/mcp/` (24 source files, 6,598 lines) vs rest of codebase |
| **Verdict** | **NEEDS REVIEW** |
| **Grade** | **B** |

---

## 1. Verdict & Summary

**NEEDS REVIEW** — The P6 MCP module has a clean dependency direction, consistent structural logging, and good dataclass discipline. However, it has three integration debts that block a PASS: (1) no module-level exception hierarchy, (2) a layer violation in `budget.py` importing from a tool submodule, and (3) `cost.py`/`budget.py` duplicate Redis connection logic instead of reusing `src.core.services.cost_tracker.CostTracker`. None are CRITICAL — all are fixable without re-architecting the module.

---

## 2. Findings Table

| # | Severity | File:Line | Finding | Recommendation |
|---|---|---|---|---|
| 1 | MEDIUM | `src/mcp/budget.py:23` | **Layer violation**: Level-2 module imports `BudgetExceeded` from level-3 `src/mcp.tools.exa_search`. A parent module depends on a leaf module for an exception type. | Move `BudgetExceeded` to `src/mcp/exceptions.py` (new file) with the rest of the MCP exception hierarchy. Import from there in both `budget.py` and `exa_search.py`. |
| 2 | MEDIUM | `src/mcp/cost.py:42-70`, `src/mcp/budget.py:74-87` | **Duplicate infrastructure**: Both `ToolCostTracker` and `BudgetEnforcer` create their own `redis.Redis` clients with identical credentials, bypassing the shared `CostTracker` from `src.core.services.cost_tracker`. `BudgetEnforcer` reads `cost:current_month` which `CostTracker` writes. | Inject `CostTracker` into `BudgetEnforcer.__init__()` as an optional dependency. `ToolCostTracker` has a distinct key namespace (`tool:cost:*`) — it's justified as separate. But shared Redis connection pool should come from `CostTracker`. |
| 3 | MEDIUM | `src/mcp/auth.py:56`, `tool_selector.py:42,59`, `brave_search.py:45`, `shell_tool.py:112,117` | **No module-level base exception**: All MCP exceptions inherit directly from `Exception`, unlike the rest of the codebase which uses module-level base exceptions (`MemoryError`, `YandereError`, `EmbeddingError`, etc.). Only `CommandForbiddenError` inherits from `ForbiddenOperationError` properly. | Create `MCPError(Exception)` as the module base. Subclass all existing MCP exceptions from it. Move `BudgetExceeded` (currently in `exa_search.py`) to this hierarchy. |
| 4 | LOW | `src/mcp/manager.py:23-33` | **`sys.path` mutilation**: Temporarily removes `src/` from `sys.path` to resolve the `mcp` package name collision between local `src/mcp/` and the pip-installed `mcp` library. Works but is fragile: not thread-safe, can fail under concurrent imports. | Acceptable as documented workaround for now. Long-term fix: rename `src/mcp/` → `src/guinevere_mcp/` or `src/mcp_gateway/` to eliminate the namespace collision. |
| 5 | LOW | `src/mcp/cost.py`, `src/mcp/budget.py`, `src/mcp/tools/brave_search.py:64-73` | **Scattered Redis clients**: Three different files each create their own `redis.Redis()` instance with the same hardcoded `host="localhost"`, `port=6380`, `db=5`, `username="guinevere_core"`. Tool modules (`brave_search.py`) shouldn't connect to Redis directly. | Extract a shared `get_mcp_redis()` helper in `src/mcp/cost.py` (or a new `src/mcp/redis.py`). All MCP modules use it. Tool modules should NOT create Redis clients at all — cost recording should go through `ToolCostTracker`. |
| 6 | LOW | `src/mcp/` (all files) | **No Protocol interfaces**: The codebase uses `Protocol` extensively for abstraction (`src/memory/`, `src/surveillance/`, `src/persona/`, `src/discord/`). P6 has zero Protocol classes. | May not be needed currently — the MCP module is a tool layer, not a service with swappable implementations. Revisit if tool modules need to be tested with mock infrastructure. |
| 7 | LOW | `src/mcp/budget.py:67-87` | **Async methods with synchronous internals**: `check_budget()`, `get_fallback_tool()`, etc. are `async def` but all internal helpers (`_get_daily_spend()`, `_get_global_daily_spend()`, `_get_monthly_spend()`) are synchronous Redis reads — no actual async I/O. | Either make the methods synchronous (since Redis `get` is blocking anyway) or use `redis.asyncio` for genuine async I/O. Current state is misleading. |

---

## 3. Pattern Comparison Table

| Pattern | Expected (rest of codebase) | Actual (P6 `src/mcp/`) | Verdict |
|---|---|---|---|
| **structlog** | `structlog.get_logger()` at module level, event-based keys | Same: `logger.info("event_name", key=val)` | ✅ MATCH |
| **Frozen dataclasses** | Mixed — `mood_engine.py` uses mutable `@dataclass`, `memory/` uses `Protocol` | P6 uses `@dataclass(frozen=True)` for `ToolAuthEntry`, `BudgetConfig`, `BudgetStatus`, `ToolOption`, `ToolRecommendation` — strictly better than existing code | ✅ EXCEEDS |
| **Protocol interfaces** | Ubiquitous: `WritePipeline`, `ReadPipeline`, `SurveillanceBuffer`, `ConsentChecker`, `SupportsIsSafe`, etc. | None — zero Protocol classes in entire `src/mcp/` | ⚠️ MISSING (may not be needed) |
| **Exception hierarchy** | Module base → specialized: `MemoryError → WritePipelineError → WritePipelineCriticalError`, `YandereError → YandereSafetyError`, `EmbeddingError → EmbeddingAPIError` | Flat: all exceptions extend `Exception` directly. No `MCPError` base. Only `CommandForbiddenError(ForbiddenOperationError)` forms a hierarchy. | ❌ VIOLATION |
| **Async patterns** | `async def` + `await` + `asyncio.create_subprocess_exec` | Same: `async def`, `asyncio.wait_for`, `asyncio.create_subprocess_exec` | ✅ MATCH |
| **Module `__init__.py` exports** | Explicit `__all__` with selected public API (`src/memory/`, `src/loops/`) | `src/mcp/__init__.py` exports `AuthLevel`, `create_server`, `ForbiddenOperationError`, `require_approval` | ✅ MATCH |
| **from __future__ import annotations** | Present in most modules (`src/loops/cost.py`, `src/memory/write_pipeline.py`) | Present in ALL 7 audited P6 files | ✅ EXCEEDS |
| **Typed return values** | `→ dict[str, Any]`, `→ list[dict]`, `→ MoodTransition \| None` | Same: `→ list[dict[str, str]]`, `→ ToolRecommendation`, `→ dict[str, object]` | ✅ MATCH |
| **Dependency direction** | Modules depend on `src/core`, NOT on `src/discord` (layered architecture) | `src/mcp/` imports from: internal only (`src.mcp.auth`, `src.mcp.tools`). Zero imports from `src/core`, `src/loops`, `src/discord`, `src/memory`, `src/persona`. | ✅ MATCH (but should import from `src/core` for cost tracking) |
| **Tool registration pattern** | `src/loops/` uses a state machine with phases | `src/mcp/tools/__init__.py` uses explicit module list + `getattr(module, "register_tools")` with `mcp.tool()` decorators | ✅ MATCH (appropriate for tool plugins) |

---

## 4. Dependency Direction Analysis

**Current state (clean diagram):**

```
src/mcp/                          (independent — no upstream deps)
├── manager.py         → tools/__init__
├── auth.py            → (self-contained)
├── auth_matrix.py     → src.mcp.auth ✅
├── cost.py            → (self-contained)
├── budget.py          → src.mcp.tools.exa_search  ⚠️ LAYER VIOLATION
├── tool_selector.py   → (self-contained)
└── tools/__init__.py  → brave_search, context7, …, websearch (16 tools)
    ├── brave_search   → src.mcp.auth ✅
    ├── postgres_tool  → src.mcp.auth ✅
    ├── shell_tool     → src.mcp.auth ✅
    └── exa_search     → src.mcp.auth, BudgetExceeded (defined here) ✅
```

**What SHOULD exist:**

```
src/mcp/
├── exceptions.py      → MCPError, ForbiddenOperationError, BudgetExceeded, …
├── cost.py            → ToolCostTracker (tool-level keys: tool:cost:*)
├── budget.py          → BudgetEnforcer (depends on CostTracker from src.core)
│                        (depends on src.mcp.exceptions ✅, NOT src.mcp.tools)
```

**Verdict**: No `src/discord`, `src/persona`, or `src/memory` dependencies — clean. The only problem is `budget.py → exa_search.py` which crosses the manager → tools boundary in the wrong direction.

---

## 5. Cost Tracker Integration Debt

| Aspect | `src/core/services/cost_tracker.py` | `src/mcp/cost.py` | `src/mcp/budget.py` | Assessment |
|---|---|---|---|---|
| Purpose | LLM model spend tracking | Per-tool call cost tracking | Budget caps & fallback routing | Different concerns — justified split |
| Key namespace | `cost:current_month`, `cost:by_model:{model}`, `cost:daily:{today}` | `tool:cost:{tool}:{date}`, `tool:cost:total:{date}` | Reads `tool:cost:*` AND `cost:current_month` | `budget.py` reads from BOTH namespaces |
| Redis client | Direct `redis.Redis()` | Direct `redis.Redis()` | Direct `redis.Redis()` | **3 separate client instances — should share** |
| Pipeline usage | `pipe.incrbyfloat()` | `pipe.incrbyfloat()` + `pipe.expireat()` | `pipe.incrbyfloat()` | Same pattern — could share a base Redis helper |
| Budget checking | `check_budget()` (ratio-based) | None | `check_budget()` (cap-based with `BudgetExceeded`) | Different algorithms — justified |

**Recommendation**: Keep `ToolCostTracker` separate (distinct key namespace is correct). But inject `CostTracker` into `BudgetEnforcer` so the monthly global spend is read through a single source of truth, and the Redis client is shared.

---

## 6. Layer Architecture Assessment

```
┌────────────────────────────────────────────────┐
│ Level 1: Entry Point                           │
│   manager.py  — create_server(), lifespan       │
├────────────────────────────────────────────────┤
│ Level 2: Infrastructure / Middleware            │
│   auth.py         — require_approval decorator  │
│   auth_matrix.py  — AUTH_MATRIX registry        │
│   cost.py         — ToolCostTracker              │
│   budget.py       — BudgetEnforcer  ⚠️           │
│   tool_selector.py — select_tool()              │
├────────────────────────────────────────────────┤
│ Level 3: Tool Implementations (16 modules)       │
│   tools/brave_search.py, postgres_tool.py, …     │
│   tools/websearch.py                            │
│   tools/exa_search.py  ← BudgetExceeded defined │
└────────────────────────────────────────────────┘

⚠️ budget.py (L2) imports BudgetExceeded from exa_search.py (L3)
```

**Fix path**: Move `BudgetExceeded` up to a new `src/mcp/exceptions.py` at Level 2, alongside `auth.py` and `cost.py`. Both `budget.py` (L2) and `exa_search.py` (L3) import from there.

---

## 7. Integration Debt Summary

| Debt | Severity | Effort | Blocking? |
|---|---|---|---|
| No `MCPError` base exception | MEDIUM | Quick (<1h) | No — cosmetic but violates codebase pattern |
| `budget.py` L2→L3 import | MEDIUM | Short (1-2h) | No — works but architectural smell |
| Duplicate Redis clients | MEDIUM | Short (1-2h) | No — works but maintenance risk |
| No `src.core.CostTracker` reuse in `budget.py` | MEDIUM | Short (1-2h) | No — separate key namespaces mean no data corruption risk |
| `sys.path` dance in `manager.py` | LOW | Quick (<1h) to document; Large (2d+) to rename package | No — documented workaround |
| No Protocol interfaces | LOW | Not needed now | No — tool layer doesn't need swappable implementations |
| Sync Redis in async methods | LOW | Short (1-2h) | No — misleading but functional |

**Total remediation effort**: ~1 day for all MEDIUM items. Make one consolidated fix PR covering items #1–#4 from the Findings Table.

---

## 8. Escalation Triggers

- **Rename `src/mcp/`** → Only justified if the `sys.path` workaround causes an actual failure in production or CI. Current state: works.
- **Protocol interfaces for tools** → Only justified if multiple tool implementations need to satisfy the same interface (e.g., pluggable search backends). Current state: not needed.
- **Full cost tracker unification** → Only justified if `CostTracker` and `ToolCostTracker` need to share budget logic (e.g., a single daily cap across LLM + MCP tool costs). Current state: separate budgets.

---

## 9. Architecture Grade Justification

**B (82/100)** — Not an A because of the exception hierarchy deficit and cost tracker duplication. Not a C or lower because:
- Dependency direction is fundamentally correct (no upstream leaks)
- 3-level tree is clean and well-organized
- `frozen=True` dataclass discipline exceeds existing codebase patterns
- `auth_matrix.py` with `ToolAuthEntry`, wildcard support, and `verify_matrix_completeness()` is exemplary
- `classify_sql()`, `validate_command()`, and injection checks in `postgres_tool.py`/`shell_tool.py` are well-designed defense layers

**What would make it an A**: Extract `src/mcp/exceptions.py` with proper hierarchy, inject `CostTracker` into `BudgetEnforcer`, move `BudgetExceeded` to shared exceptions, and consolidate Redis connection into a shared helper.

---

*Audit completed 2026-06-03. No secrets or credentials exposed in this report.*