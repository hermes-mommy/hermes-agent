# F-04 + F-05 Fix Summary

**Date:** 2026-06-09  
**Agent:** Subagent (delegated task)  
**Status:** ✅ COMPLETE

---

## F-04: Wire ToolCostTracker + BudgetEnforcer

### What was done

1. **Read interfaces:** Analyzed `src/mcp/cost.py` (ToolCostTracker) and `src/mcp/budget.py` (BudgetEnforcer)
2. **Designed middleware:** FastMCP has no built-in middleware hooks, so implemented decorator interception pattern
3. **Implemented wiring in `src/mcp/manager.py`:**
   - Added global singletons `_cost_tracker` and `_budget_enforcer`
   - Initialize both at server startup with graceful degradation (log warning if Redis down)
   - Created `_wrap_with_cost_middleware()` that wraps each tool with:
     - **PRE-call:** `BudgetEnforcer.check_budget()` — raises `BudgetExceeded` if over cap
     - **POST-call:** `ToolCostTracker.record_tool_cost()` — records fixed cost to Redis
   - Created `_register_tools_with_middleware()` that patches `server.tool` during registration
   - Added `create_mcp_app` alias for `create_server`

### Graceful degradation

| Failure | Behaviour |
|---|---|
| Redis down at startup | Tracker/enforcer = None; server starts normally |
| Redis down during budget check | Log warning; tool call proceeds |
| Redis down during cost record | Log warning; result returned |
| BudgetExceeded raised | Re-raised; tool intentionally blocked |

### Verification

```bash
$ .venv/bin/python3 -c "from src.mcp.manager import create_mcp_app; print('OK')"
OK
```

✅ Import succeeds; no syntax errors

### Files modified

- `src/mcp/manager.py` — +150 lines (middleware, wiring, graceful init)

### Evidence

- `docs/setup-evidence/p6-fixes/exec-F04.md` — full interface analysis, middleware design, verification

---

## F-05: BRAVE_API_KEY Missing

### What was found

1. **brave_search.py loads key via:** `os.environ.get("BRAVE_API_KEY")` at call time
2. **No fallback:** Raises `BraveSearchConfigError` if absent
3. **SOPS secrets scan:** `sops --decrypt ~/secrets/*.yaml | grep -i brave` → no output
4. **Env files scan:** `grep BRAVE .env.*` → no output
5. **Conclusion:** Key is **NOT provisioned** anywhere

### Action taken

Added placeholder + provisioning instructions to `.env.mcp`:

```bash
# --- API keys (provision via SOPS before starting MCP server) ---
# BRAVE_API_KEY=<set-via-sops>   # Required by src/mcp/tools/brave_search.py — provision from SOPS
# EXA_API_KEY=<set-via-sops>     # Required by src/mcp/tools/exa_search.py — provision from SOPS
```

### Impact

- MCP server **starts successfully** (not an import-time check)
- `brave_search` tool **fails at runtime** when called until key is provisioned
- Same status for `EXA_API_KEY`

### Provisioning steps documented

1. Acquire Brave Search API key (free tier available)
2. Encrypt in SOPS (`~/secrets/api-keys.yaml`)
3. Decrypt and source into `.env.mcp`
4. Verify with Python import test

### Files modified

- `.env.mcp` — added 4 lines (comment block + 2 placeholder keys)

### Evidence

- `docs/setup-evidence/p6-fixes/exec-F05.md` — key load analysis, scan results, provisioning guide

---

## Summary

| Fix | Status | Files Changed | Evidence |
|---|---|---|---|
| F-04 | ✅ DONE | `src/mcp/manager.py` | `docs/setup-evidence/p6-fixes/exec-F04.md` |
| F-05 | ✅ DONE | `.env.mcp` | `docs/setup-evidence/p6-fixes/exec-F05.md` |

**Both tasks complete.** Middleware wired with graceful degradation; missing API keys documented with provisioning guide.
