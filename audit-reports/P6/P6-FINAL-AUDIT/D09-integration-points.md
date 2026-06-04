# D09 — Integration Points Audit

**Date:** 2026-06-03  
**Auditor:** Guinevere (consultant mode)  
**Scope:** Wiring/integration between all P6 MCP components and the P5 Agent Loop  
**Verdict:** **FAIL** — 4 of 7 integration surfaces are disconnected

---

## Integration Map

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CONNECTED (PASS)                                  │
│                                                                      │
│  tools/*.py ──→ tools/__init__.py ──→ manager.py ──→ FastMCP.run()  │
│       │                                                              │
│       └──→ each @require_approval(AuthLevel.xxx) applied BEFORE      │
│            mcp.tool()(func) registration                             │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                    DISCONNECTED (FAIL)                               │
│                                                                      │
│  auth_matrix.py ◄──── NEVER CONSUMED ────► auth.py                   │
│       • get_auth_level() never called                                │
│       • verify_matrix_completeness() never called                    │
│       • No runtime binding between matrix entries and decorator args │
│                                                                      │
│  cost.py ◄──── NEVER IMPORTED ────► (any tool module)                │
│       • ToolCostTracker never instantiated                           │
│       • Tools use ad-hoc inline _record_cost() instead               │
│                                                                      │
│  budget.py ◄──── NEVER IMPORTED ────► (any tool module)              │
│       • BudgetEnforcer never instantiated                            │
│       • budget.py → exa_search.BudgetExceeded (circular import risk) │
│                                                                      │
│  tool_selector.py ◄──── NEVER IMPORTED ────► src/loops/              │
│       • select_tool() is never called from any production path       │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                           ISOLATION                                  │
│                                                                      │
│  src/mcp/  ────✗────  src/loops/                                     │
│       • Zero imports of src.mcp anywhere in src/loops/               │
│       • Zero mentions of "mcp" / "MCP" / "FastMCP" in src/loops/     │
│       • Agent loop phases are stubs (generate markdown templates)    │
│       • P6 MCP is a standalone, unreachable subsystem                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Per-Surface Findings

### 1. `tools/__init__.py` Registry — PASS

All 16 tool modules are imported and listed in `_TOOL_MODULES`. `register_all_tools(server)` iterates each module, calls `register_tools(server)`, and each module's `register_tools` calls `mcp.tool()(decorated_func)`.

**Evidence:**
- Lines 29–64: 16 explicit imports matching 16 list entries
- Lines 68–94: `register_all_tools` iterates and calls each module's `register_fn`
- Each tool module (e.g., `brave_search.py:174-177`) calls `mcp.tool()(func)`

### 2. `manager.py` Lifespan — PASS

`_build_lifespan()` returns an async context manager that calls `register_all_tools(server)` during startup via the FastMCP lifespan protocol. On shutdown it logs only — no cleanup needed (FastMCP handles that).

**Evidence:**
- `manager.py:45-60`: lifespan calls `register_all_tools(server)` on startup
- `manager.py:74-77`: lifespan wired into `FastMCP(lifespan=...)`

### 3. `auth.py` Decorator — PASS (Applied, but missing runtime verification)

`require_approval()` is applied **57 times** across all 16 tool modules. Each tool function is decorated before registration. The auth gate (READ_AUTO / WRITE_NOTIFY / DESTRUCTIVE_APPROVAL / FORBIDDEN) will fire on every invocation.

**Evidence:**
- `@require_approval` found 57 times in 16 files (grep confirmed)
- All 16 tools import `from src.mcp.auth import AuthLevel, require_approval`
- Decoration happens before `mcp.tool()(func)` in `register_tools`

### 4. `auth_matrix.py` ↔ `auth.py` — FAIL (Documentation-only, no runtime enforcement)

`auth_matrix.py` imports `AuthLevel` from `auth.py`, but `auth.py` has **no awareness** of `auth_matrix.py`. The `AUTH_MATRIX` dict, `get_auth_level()`, and `verify_matrix_completeness()` are defined but **never called** anywhere in production code — only in test files.

There is **no runtime binding** between what the matrix declares and what each tool module's `@require_approval(AuthLevel.xxx)` hardcodes. If a tool author changes the decorator level, the matrix won't detect the inconsistency.

**Evidence:**
- `auth.py`: zero imports of `auth_matrix.py`
- `auth_matrix.py`: `get_auth_level` and `verify_matrix_completeness` defined at lines 194, 244 — but grep shows zero calls outside `auth_matrix.py` itself
- No source file (excluding tests) imports `auth_matrix`

### 5. `cost.py` / `budget.py` — FAIL (Dead code)

Both classes are **defined but never instantiated** in production code. No tool module imports them. No loop phase imports them.

**What tools actually do instead:** Brave search has ad-hoc inline `_record_cost()` writing directly to Redis with its own constants. No other tool module has any cost tracking at all (verify by reading any other tool module — e.g., `context7.py`, `fetch.py`, `grep_app.py` — no cost recording).

`budget.py` imports `BudgetExceeded` from `src.mcp.tools.exa_search` (line 23), creating a **circular dependency hazard**: `budget.py` depends on a tool module it's supposed to enforce. The `exa_search.py` module defines `BudgetExceeded` but never instantiates `BudgetEnforcer` to use it.

**Evidence:**
- `ToolCostTracker`: defined in `cost.py:42`, grep confirms zero imports from `src.mcp.cost` anywhere in `src/`
- `BudgetEnforcer`: defined in `budget.py:67`, grep confirms zero imports from `src.mcp.budget` anywhere in `src/`
- Only `tests/` files import these classes

### 6. `tool_selector.py` — FAIL (Orphaned module)

`select_tool()` and `get_tool_matrix()` are defined but **never called** from any production code path. The decision matrix (8 task types, with scored alternatives) is complete but unreachable.

**Evidence:**
- `select_tool`: defined at `tool_selector.py:202`, grep shows zero imports of `tool_selector` outside tests
- `src/loops/`: zero references to `select_tool` or `tool_selector`

### 7. MCP ↔ Agent Loop — FAIL (Complete isolation)

**Zero imports** of `src.mcp` from `src/loops/`. **Zero mentions** of "mcp"/"MCP"/"FastMCP" anywhere in the loops directory. The agent loop phases (`delegate.py`, `execute.py`, etc.) are stubs that generate markdown template artifacts — they do not invoke MCP tools or even reference them.

`src/__init__.py` does not import MCP either.

**Evidence:**
- `src/loops/`: grep for `from src.mcp` returns zero matches
- `src/loops/`: grep for `mcp`/`MCP`/`FastMCP` returns zero matches
- `delegate.py`: generates a delegation manifest template, no tool invocation
- `execute.py`: generates an execution log template, no tool invocation
- `src/__init__.py`: does not mention MCP

---

## Dead Code Inventory

| File | Class/Function | Lines | Status | Severity |
|---|---|---|---|---|
| `src/mcp/cost.py` | `ToolCostTracker` (full class, 241 lines) | 42–241 | Never instantiated | **H** |
| `src/mcp/budget.py` | `BudgetEnforcer` (full class, 297 lines) | 67–364 | Never instantiated | **H** |
| `src/mcp/budget.py` | `BudgetConfig`, `BudgetStatus` dataclasses | 32–55 | Used only by BudgetEnforcer | **H** |
| `src/mcp/auth_matrix.py` | `AUTH_MATRIX` dict (114 lines) | 52–166 | Read only in tests | **M** |
| `src/mcp/auth_matrix.py` | `get_auth_level()` | 194–236 | Never called in production | **M** |
| `src/mcp/auth_matrix.py` | `verify_matrix_completeness()` | 244–277 | Never called in production | **M** |
| `src/mcp/tool_selector.py` | `select_tool()` | 202–280 | Never called in production | **H** |
| `src/mcp/tool_selector.py` | `get_tool_matrix()` | 283–292 | Never called in production | **M** |
| `src/mcp/tool_selector.py` | `_DECISION_MATRIX` dict (42 lines) | 131–173 | Never read in production | **M** |

**Total dead code:** ~750 lines of production-grade code with zero runtime callers.

---

## Wiring Gaps

| # | Gap | Components | Severity | Impact |
|---|---|---|---|---|
| G1 | Auth matrix not bound to decorator runtime | `auth_matrix.py` → `auth.py` | **HIGH** | Decorator levels can drift from matrix; no enforcement. Matrix is documentation, not code. |
| G2 | Cost tracker never wired into tools | `cost.py` → `tools/*.py` | **HIGH** | 241 lines unused. Tools track costs ad-hoc or not at all. No unified cost recording. |
| G3 | Budget enforcer never wired into tools | `budget.py` → `tools/*.py` | **HIGH** | 364 lines unused. No budget caps enforced at runtime. BudgetExceeded exists but never raised. |
| G4 | Tool selector never called by agent loop | `tool_selector.py` → `src/loops/` | **HIGH** | 332 lines unused. Agent loop has no mechanism to select or invoke tools. |
| G5 | MCP completely isolated from agent loop | `src/mcp/` → `src/loops/` | **CRITICAL** | P6 tools exist but the agent cannot use them. P6 is a standalone server with no caller. |
| G6 | `src/mcp/__init__.py` exports incomplete | `__init__.py` | **MEDIUM** | Exports `AuthLevel`, `create_server`, `require_approval`, `ForbiddenOperationError` — but NOT `auth_matrix`, `cost`, `budget`, or `tool_selector` |

---

## Summary

| Dimension | Verdict |
|---|---|
| Tool registry → FastMCP | ✅ PASS |
| Manager lifespan wiring | ✅ PASS |
| Auth decorator application | ✅ PASS |
| Auth matrix ↔ Auth decorator | ❌ FAIL — disconnected |
| Cost tracker integration | ❌ FAIL — dead code |
| Budget enforcer integration | ❌ FAIL — dead code |
| Tool selector integration | ❌ FAIL — orphaned |
| MCP ↔ Agent Loop | ❌ FAIL — completely isolated |

**Overall:** P6's internal wiring (tools → registry → FastMCP) works correctly. The auth decorator is applied everywhere it should be. But the entire MCP subsystem is **an island** — no agent loop phase knows it exists, and the supporting infrastructure (cost, budget, selector, matrix enforcement) was built but never connected. P6 delivers a functional MCP server but not an integrated one.

---

## Recommended Remediation Path

1. **Wire agent loop to MCP** (Critical): Add `from src.mcp.tool_selector import select_tool` to `src/loops/phases/execute.py` or a new tool-execution phase. This is the bridge that makes P6 tools reachable.

2. **Bind auth_matrix to auth** (High): Add `verify_matrix_completeness()` call in `manager.py` lifespan startup. Add an optional `auth_matrix.get_auth_level()` check inside `require_approval()` wrapper to detect decorator/matrix drift at runtime.

3. **Wire cost/budget into tools** (High): Import `ToolCostTracker` and `BudgetEnforcer` in each tool module's `register_tools()` or in a shared middleware. Replace ad-hoc `_record_cost()` calls with the centralized tracker.

4. **Export cost/budget/selector/matrix from `src/mcp/__init__.py`** (Medium): These are intended public API but hidden from importers.

5. **Resolve `budget.py` → `exa_search.py` circular dependency** (Medium): Move `BudgetExceeded` to a shared exceptions module or invert the dependency.