# Budget State Ground-Truth Report

**Date:** 2026-06-06
**Author:** Sisyphus-Junior (Research Agent)
**Scope:** Budget config/state, hook files, registration status, enforcement mode, Phase 6 requirement mismatches
**Evidence root:** `research-reports/phase-6-execution/04-budget-state.md`

---

## 1. Executive Summary

| Dimension | Status |
|---|---|
| **Budget hook code exists?** | ✅ YES — 3 files in `hermes-config/hooks/` |
| **Budget hook registered in config?** | ❌ NO — not in `hermes-config/config.yaml` `hooks.pre_tool_call` |
| **Enforcement mode** | **Fail-closed** (all Redis/Lua/parse errors → block) |
| **`plugins.enabled` in config?** | ❌ NO — key does not exist in `config.yaml` |
| **Lua atomic check+deduct?** | ✅ YES — both `budget_lua.py` and `budget_lua_extended.py` |
| **Per-tool daily caps?** | ✅ YES — exa=$5, brave=$3, default=$10, global=$10 |
| **Monthly cap / alert / block** | $30 / $24 (80%) / $30 (100%) |
| **`budget_check_failed` in prod code?** | ❌ NO — only in planning docs |
| **Phase 6 plan alignment** | **MISMATCH** — plan expects `~/.hermes/hooks/budget.py` but actual code is `hermes-config/hooks/budget_check.py` + Lua modules |

---

## 2. Config File Budget Section

**File:** `hermes-config/config.yaml` (lines 66–71)

```yaml
# Monthly budget tracking (informational — not read by Hermes)
budget:
  monthly_limit: 30.00
  alert_threshold: 0.80
  block_threshold: 1.00
  currency: USD
```

**Status:** Reference-only. The comment explicitly states "informational — not read by Hermes." No runtime enforcement derives from this section. The values match the Phase 6 requirement ($30 cap, 80% alert, 100% block).

---

## 3. Budget Hook Code — File Inventory

Three files exist in the repo under `hermes-config/hooks/`. **None are registered in `config.yaml` for runtime execution.**

### 3.1 `hermes-config/hooks/budget_check.py` (262 lines)

- **Role:** Hermes `pre_tool_call` shell hook entry point
- **Protocol:** stdin/stdout JSON — reads `tool_name` from hook context, writes `{"action": "allow" | "block"}` to stdout
- **Exit codes:** 0 = ALLOW, 1 = BLOCK
- **Monthly cap:** `MONTHLY_CAP = 30.0`
- **Warning threshold:** `WARN_THRESHOLD = 24.0`
- **Default tool cost:** `DEFAULT_TOOL_COST = 0.01` (USD)
- **Known tool fixed costs** (15 tools mapped): brave_search=0.01, exa=0.007, git/postgres/redis/shell/docker=0.0, unknown=0.01
- **Daily caps:** `exa=5.0`, `brave_search=3.0`, all others=10.0
- **Global daily cap:** 10.0
- **Redis:** Connects to Redis DB5 on port 6380 via `_hook_utils.get_redis_connection()`
- **Lua scripts used:** Both `SCRIPT_MONTHLY_CHECK` (monthly only) and `SCRIPT_EXTENDED_CHECK` (monthly + daily caps)
- **Fail-closed:** All error paths (Redis down, Lua load fail, Lua exec fail, invalid input, unknown tool) → `{"action": "block"}` + `sys.exit(1)`
- **Tests:** 47 tests in `tests/hermes/test_budget_hook.py` — all passing

### 3.2 `hermes-config/hooks/budget_lua.py` (138 lines)

- **Role:** Lua script source + loading utilities for monthly-only check
- **Script:** `SCRIPT_MONTHLY_CHECK` — single Redis Lua atom:
  - Read `cost:current_month` → check `projected = current + estimated` → if > cap → `MONTHLY_BLOCKED` (NO deduct)
  - If OK → `INCRBYFLOAT` (deduct) → return `ALLOWED` or `WARNING`
  - No daily caps
- **Keys:** `cost:current_month`
- **Params:** estimated_cost, monthly_cap (default 30.0), warn_threshold (default 24.0)
- **Returns:** `"ALLOWED"`, `"WARNING"`, `"MONTHLY_BLOCKED"`
- **Helper:** `load_script()` wraps `SCRIPT LOAD`, `call_monthly_check()` wraps `EVALSHA`
- **Fail-closed:** Any `evalsha` exception is re-raised (caller must block)

### 3.3 `hermes-config/hooks/budget_lua_extended.py` (140 lines)

- **Role:** Extended Lua script with per-tool daily + global daily caps
- **Script:** `SCRIPT_EXTENDED_CHECK` — atomic check of 3 keys:
  - `cost:current_month` (monthly total)
  - `tool:cost:{name}:YYYY-MM-DD` (per-tool daily)
  - `cost:daily:YYYY-MM-DD` (global daily)
- **Atomic flow:** Read all 3 keys → check 3 caps → if all OK, deduct all 3 + set 48h TTL on daily keys → return verdict
- **Returns:** `"ALLOWED"`, `"WARNING"`, `"MONTHLY_BLOCKED"`, `"DAILY_TOOL_BLOCKED"`, `"DAILY_GLOBAL_BLOCKED"`
- **Monthly defaults:** cap=30.0, warn=24.0, daily_tool_cap=5.0, daily_global_cap=10.0

### 3.4 `hermes-config/hooks/_hook_utils.py` (248 lines)

- **Role:** Shared utilities for all Hermes hooks
- **Redis URL:** `os.environ.get("GUINEVERE_REDIS_URL", "redis://localhost:6380/5")`
- **Pooling:** Connection pool with retry (3 attempts, exponential backoff)
- **Logging:** Rotating JSON file logger to `~/.hermes/logs/hooks/`
- **I/O:** `read_stdin_json()`, `write_stdout_json()` for Hermes hook protocol
- **Timing:** `timing_guard()` context manager

---

## 4. Registration Status — NOT REGISTERED

### 4.1 `plugins.enabled` does not exist

`hermes-config/config.yaml` has **no** `plugins.enabled` key. Earlier Phase 4 plans reference adding it (e.g., `plugins.enabled: [guinevere_safety, auth_overlay]`), but it was never added to the actual deployed config.

### 4.2 Budget hook not in `hooks.pre_tool_call`

The existing `hooks.pre_tool_call` section in `config.yaml` registers only:

```yaml
hooks:
  pre_tool_call:
    - event: pre_tool_call
      command: "python3 ~/.hermes/hooks/consent_gate.py"
      timeout_ms: 200
      on_failure: block
      priority: 90
```

**No budget hook entry exists.** The `budget_check.py` code is verified, tested, and ready but is **dead code at runtime** — it is never invoked.

### 4.3 `.hermes/plugins/guinevere-safety/plugin.yaml`

Declares hooks (`pre_llm_call`, `post_llm_call`, `pre_tool_call`, `post_tool_call`, `transform_llm_output`, `on_session_start`) but the `pre_tool_call` handler in the plugin covers auth + consent, **not** budget.

### 4.4 `~/.hermes/` does not exist locally

The `~/.hermes/hooks/` and `~/.hermes/plugins/` directories are **absent on the local Windows machine**. These paths are VPS-specific (Ubuntu, deployed at `/home/guinevere/.hermes/`). The VPS was not directly inspected (no SSH key available in this session), so the VPS runtime state is inferred from the repo artifacts.

---

## 5. Enforcement Mode: Fail-Closed

The hook code is **unambiguously fail-closed**:

| Failure Mode | Behavior | Evidence |
|---|---|---|
| Redis unavailable | Block with "Budget check unavailable (Redis down)" | `budget_check.py:179-181` |
| Lua script load failure | Exception propagates → caught → block | `budget_check.py:187-200` |
| Lua execution failure | Exception caught → block with "Budget check error" | `budget_check.py:201-208` |
| Invalid/missing `tool_name` | Block with "Missing tool_name in budget check" | `budget_check.py:161-167` |
| Unknown tool name | Block with `DEFAULT_TOOL_COST=0.01` (conservative) | `budget_check.py:138-141` |
| Any unexpected exception | Broad `except Exception` → block | `budget_check.py:201-208` |
| `_hook_utils` Redis ping failure | Returns None → block | `_hook_utils.py:103-111` |

**Verdict:** When/if registered, the hook is **fail-closed**. The Phase 6 plan's Step 6.3 hook (`budget.py` with `on_failure: block`) is consistent.

---

## 6. Lua Atomic Check+Deduct

Both Lua scripts execute as a single atomic unit on the Redis server:

1. **Read** current values from Redis keys
2. **Check** projected spend against caps
3. **Only if all caps OK** → `INCRBYFLOAT` (deduct)
4. **If any cap exceeded** → return block status (no deduction)

There is **no client-side read-then-increment** pattern. All `redis.call('INCRBYFLOAT', ...)` calls are inside Lua. The Python test suite (`test_monthly_script_calls_redis_atomically`, `test_extended_script_calls_redis_atomically`) verifies this by asserting `evalsha` is called once and `get`/`incrbyfloat` are not called.

---

## 7. Redis Key Schema

| Key | Purpose | Set By | Lua Key Index |
|---|---|---|---|
| `cost:current_month` | Monthly running total | Lua `INCRBYFLOAT` in both scripts | KEYS[1] |
| `tool:cost:{name}:YYYY-MM-DD` | Per-tool daily spend | Extended Lua script | KEYS[2] |
| `cost:daily:YYYY-MM-DD` | Global daily spend | Extended Lua script | KEYS[3] |
| `budget:monthly_cap` | Configurable cap (set via Discord `/budget set`) | `cmd_budget.py` / `commands_finance/budget.py` | Not used by hook (hardcoded as $30) |
| `budget:block_counter` | Block event counter | Phase 6 plan hook (not in current `budget_check.py`) | Not present |

---

## 8. Auxiliary Budget Systems

### 8.1 `src/mcp/budget.py` (364 lines) — MCP-Level BudgetEnforcer

- **Role:** Python-class-level budget enforcement for MCP tools
- **Status:** Separate path, **not wired into `pre_tool_call` hook**
- **Uses:** Client-side `redis.get()` → comparison → `redis.incrbyfloat()` — **NOT atomic** (TOCTOU race with parallel tool calls)
- **Thresholds:** Different from hook:
  - `monthly_warning = 3.0`, `monthly_critical = 15.0`, `monthly_hard_stop = 25.0`, `monthly_absolute_cap = 30.0`
- **Fallback:** `exa` → `brave_search`, `brave_search` → `None`
- **Hooks into individual tools** (`exa_search.py` calls `_check_budget()` directly), not global `pre_tool_call`
- **Known limitation:** `record_and_check()` method — designed as primary enforcement entry point — is **never called** from any production code path (per `research-reports/phase-4-execution/05-budget-gap.md`)

### 8.2 `src/hermes_plugins/commands_finance/budget.py` (212 lines) — Discord Plugin

- **Role:** Hermes command plugin — `/budget` view/set
- **Reads:** `cost:current_month` and `budget:monthly_cap` from Redis DB5
- **Default cap:** 30.0
- **Status levels:** NORMAL → NORMAL_ALERT ($1+) → WARNING (≥50%) → CRITICAL (≥83.3%) → HARD_STOP (≥100%)
- **Used via:** `register()` → `ctx.register_command("budget", ...)`

### 8.3 `src/discord/cmd_budget.py` (643 lines) — Discord Slash Command

- **Role:** Discord `/budget` slash command implementation
- **Same Redis reads:** `cost:current_month`, `budget:monthly_cap`
- **Same status levels** as plugin version
- **Persona-flavored embeds:** "Mommy jaga budget biar nggak boros, Darling."
- **Access-controlled:** Faiz-only via `is_faiz_interaction`

### 8.4 `src/core/services/cost_tracker.py` — Cost Tracking

- **Role:** Records per-model token costs to Redis DB5
- **Status:** Used by `src/mcp/budget.py` and `llm_router.py` (but `llm_router.py` does **NOT** currently call `CostTracker.record_cost()` — per recheck-context-phase6-cost.md Fix 2)
- **Keys written:** `cost:current_month`, `cost:by_model:*`, etc.

---

## 9. Phase 6 Plan vs Current State — Mismatches

| Aspect | Phase 6 Plan (`batch-plan-phase-6.md`) | Current Repo State | Mismatch? |
|---|---|---|---|
| Hook file path | `~/.hermes/hooks/budget.py` | `hermes-config/hooks/budget_check.py` + `budget_lua.py` + `budget_lua_extended.py` | **YES** — plan expects single file at VPS path; repo has 3 files in the config directory |
| Hook registration | Add to `hooks.pre_tool_call` in config.yaml | **NOT REGISTERED** | **YES** — registration is the blocking gap |
| Budget thresholds | $30 cap, 80% alert ($24), 100% block ($30) | Same values in `budget_check.py` | ✅ Match |
| Lua atomicity | Single Lua check+deduct | Both `budget_lua.py` and `budget_lua_extended.py` provide this | ✅ Match (better than planned — daily caps added) |
| Per-tool daily caps | Not in plan's Step 6.3 | Implemented in `budget_lua_extended.py` | ⚠️ Plan scope smaller than actual |
| `on_failure: block` | Specified in plan registration | Not yet applied (not registered) | ⚠️ Pending |
| `timeout_ms` | 500ms (plan) vs existing hooks use 200ms | N/A (not registered yet) | ⚠️ Plan uses 500ms, consent gate uses 200ms |
| `plugins.enabled` | Referenced in Phase 4 plans but never added | Does NOT exist in `config.yaml` | **YES** — still absent |
| `budget_check_failed` string | Appears in plan's Step 6.3 hook code (line 676) | **NOT** in actual `budget_check.py` — uses different messages | **YES** — plan's hook differs from code |
| `CostTracker` wiring in `llm_router.py` | Assumed but not verified in plan | `llm_router.py` does NOT call `CostTracker.record_cost()` | **YES** — per recheck-context report Fix 2 |
| `cost_per_1k` values | Plan rates ($5/$30, $0.14/$0.28 per 1M) | `llm_router.py` has older values (0.0025/0.01, 0.0001/0.0002) | **YES** — stale, off by 1.4x–3x |

---

## 10. Key Gaps for Planner Decisions

### GAP-001: Budget hook not registered (CRITICAL)
The three hook files are verified and tested but are **dead code**. `config.yaml` `hooks.pre_tool_call` has no budget hook entry. Without registration, no runtime budget enforcement exists.

**Action:** Add to `config.yaml` `hooks.pre_tool_call`:
```yaml
    - event: pre_tool_call
      command: "python3 ~/.hermes/hooks/budget_check.py"
      timeout_ms: 500
      on_failure: block
      priority: 100
```

### GAP-002: Hook path mismatch (MEDIUM)
The plan references `~/.hermes/hooks/budget.py` but the actual file is `hermes-config/hooks/budget_check.py`. The deployment either needs to:
- (a) Copy `hermes-config/hooks/budget_check.py` + `budget_lua.py` + `budget_lua_extended.py` + `_hook_utils.py` to `~/.hermes/hooks/` on VPS, OR
- (b) Update the config to point to a different path, OR
- (c) Create a wrapper `~/.hermes/hooks/budget.py` that imports `budget_check.py`

### GAP-003: CostTracker not wired into llm_router.py (CRITICAL)
LLM call costs are not being recorded to Redis DB5. The budget hook reads from `cost:current_month` which is only populated by `cost_tracker.py` — but `llm_router.py` never calls it. Without this wiring, the budget hook will always see zero spend and never block.

**Action:** Add `CostTracker.record_cost()` call in `llm_router.py.chat()` after successful response.

### GAP-004: Stale cost_per_1k values (HIGH)
`llm_router.py` has cost_per_1k values that are 1.4x–3x off from current plan pricing. This affects cost tracking accuracy when/after CostTracker is wired.

**Action:** Update all 6 cost_per_1k values in `llm_router.py` to match $5/$30 (GPT-5.5) and $0.14/$0.28 (DeepSeek) per 1M tokens.

### GAP-005: `plugins.enabled` still absent (LOW)
Phase 4 plans reference adding `plugins.enabled: [guinevere_safety, auth_overlay]` but it was never added. The `guinevere_safety` plugin at `.hermes/plugins/guinevere-safety/` exists but has no explicit enable flag in config.

### GAP-006: Dual-write risk (MEDIUM)
`src/mcp/budget.py` (BudgetEnforcer) writes to the same Redis keys (`cost:current_month`, `tool:cost:*`) as the hook's Lua scripts. If both paths are active simultaneously, costs will be double-counted.

---

## 11. File Inventory

| File | Lines | Role | Registered? |
|---|---|---|---|
| `hermes-config/config.yaml` | 338 | Main Hermes config; budget section is informational only | N/A |
| `hermes-config/hooks/budget_check.py` | 262 | Budget pre_tool_call shell hook entry point | ❌ |
| `hermes-config/hooks/budget_lua.py` | 138 | Monthly Lua atomic check+deduct | ❌ |
| `hermes-config/hooks/budget_lua_extended.py` | 140 | Extended Lua with daily caps | ❌ |
| `hermes-config/hooks/_hook_utils.py` | 248 | Shared hook utilities | ✅ (used by consent_gate) |
| `src/mcp/budget.py` | 364 | MCP-level BudgetEnforcer (separate path) | ❌ (used by individual tools) |
| `src/hermes_plugins/commands_finance/budget.py` | 212 | Discord budget command plugin | ✅ (Hermes plugin system) |
| `src/discord/cmd_budget.py` | 643 | Discord /budget slash command | ✅ (Discord bot tree) |
| `src/core/services/cost_tracker.py` | ~50 | Cost recording service | ⚠️ Not wired into llm_router |
| `tests/hermes/test_budget_hook.py` | 593 | Budget hook test suite (47 tests) | N/A |
| `.hermes/plugins/guinevere-safety/plugin.yaml` | 11 | Safety plugin hook declaration | ⚠️ No plugins.enabled |
| `hermes-config/SOUL.md` | 463 | Static persona core (deployed to `~/.hermes/SOUL.md`) | ✅ |

---

## 12. VPS Accessibility

**Local Windows machine:** No `~/.hermes/` directory exists. No SSH access was available in this session to inspect VPS at `/home/guinevere/.hermes/`. The VPS state is inferred from:
- `hermes-config/config.yaml` (header says "Deployed on VPS Ubuntu alongside ~/.hermes/.env")
- `hermes-config/SOUL.md` (deployed to `~/.hermes/SOUL.md`)
- Phase 4/6 batch plans (reference VPS paths extensively)
- Planning docs with SSH commands targeting `guinevere-vps`

**Recommendation:** A dedicated VPS state inspection task should verify:
- Whether `~/.hermes/hooks/budget_check.py` or `~/.hermes/hooks/budget.py` exists
- Whether `plugins.enabled` exists in the deployed `~/.hermes/config.yaml`
- Whether `CostTracker.record_cost()` is called from `llm_router.py`
- Actual `cost:current_month` value in Redis DB5

---

## 13. Summary: Phase 6 Requirement Fit

| Phase 6 Requirement | Current State | Fit |
|---|---|---|
| Monthly cap $30, alert $24, hard block $30 | ✅ Correct in config + hook code | ✅ FIT |
| Per-tool daily caps | ✅ Implemented (exa=$5, brave=$3, global=$10) | ✅ FIT |
| Lua atomic check+deduct | ✅ Both monthly-only and extended scripts | ✅ FIT |
| Fail-closed Redis error handling | ✅ All error paths → block | ✅ FIT |
| Hook registered in pre_tool_call | ❌ Not registered — dead code | ❌ **BLOCKING** |
| CostTracker wired into llm_router | ❌ Not wired — cost tracking incomplete | ❌ **BLOCKING** |
| Hook deployed to VPS `~/.hermes/hooks/` | ❌ Unknown (VPS not inspected) | ⚠️ UNKNOWN |
| `plugins.enabled` in config | ❌ Key does not exist | ⚠️ GAP |

---

## 14. References

- `hermes-config/config.yaml` — main config
- `hermes-config/hooks/budget_check.py` — hook entry point
- `hermes-config/hooks/budget_lua.py` — Lua monthly script
- `hermes-config/hooks/budget_lua_extended.py` — Lua extended script
- `hermes-config/hooks/_hook_utils.py` — shared utilities
- `src/mcp/budget.py` — MCP-level BudgetEnforcer
- `tests/hermes/test_budget_hook.py` — 47 tests (all passing)
- `docs/setup-evidence/phase-4/P4-003-verification.md` — P4-003 verification
- `docs/setup-evidence/phase-4/audit-budget-guards.md` — security audit (PASS)
- `docs/setup-evidence/hermes-migration/batch-plan-phase-6.md` — Phase 6 plan
- `research-reports/phase-6-7-planning/recheck-context-phase6-cost.md` — audit fixes
- `research-reports/phase-4-execution/05-budget-gap.md` — prior gap analysis
- `research-reports/phase-4-planning/R4-005-budget-enforcement.md` — budget planning
