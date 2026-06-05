# Phase 6: LLM Routing & Budget State Audit

> **Date:** 2026-06-05  
> **Context:** ADR-035 Hermes Migration — Phase 6 Planning  
> **Auditor:** Guinevere  

## 1. Current Config State (`hermes-config/config.yaml`)

| Property | Current Value | Notes |
|---|---|---|
| `model.provider` | `ninerouter` | Active |
| `model.base_url` | `http://localhost:20128/v1` | Active |
| `model.model` | `ds/deepseek-v4-flash` | **Changed**: GPT-5.5 removed due to 401 token invalidation |
| `providers.ninerouter.key_env` | `NINEROUTER_API_KEY` | Active |
| `fallback_providers` | **COMMENTED OUT** | Explicitly disabled with note: *"gpt-5.5 removed — 9Router token invalidated (HTTP 401)"* |
| `budget.monthly_limit` | `30.00` | **GAP**: Marked as "informational — not read by Hermes" |
| `budget.alert_threshold` | `0.80` | **GAP**: Not actively enforced by Hermes |
| `budget.block_threshold` | `1.00` | **GAP**: Not actively enforced by Hermes |

**Key Finding**: The current configuration has already pivoted away from GPT-5.5 as the primary model. DeepSeek V4 Flash is now the active primary. The fallback chain is currently disabled in the config file.

---

## 2. LLM Router Implementation (`src/core/services/llm_router.py`)

**File Size**: 104 lines  
**Architecture**: Hardcoded fallback chain with 9Router integration.

### Task Types & Model Configs
| Task Type | Model Name | Max Tokens | Temp | Cost / 1K Input | Cost / 1K Output |
|---|---|---|---|---|---|
| `CORE_REASONING` | `cx/gpt-5.5` | 16,384 | 0.7 | $0.0025 | $0.0100 |
| `SUB_AGENT` | `ds/deepseek-v4-flash` | 8,192 | 0.5 | $0.0001 | $0.0002 |
| `FALLBACK` | `guinevere` (combo) | 8,192 | 0.5 | $0.0001 | $0.0002 |

### Fallback Chain Logic
- Default chain: `[task_type, SUB_AGENT, FALLBACK]`
- If `task_type == SUB_AGENT`: chain is `[SUB_AGENT, FALLBACK]`
- Iterates through chain; on any exception, logs warning and proceeds to next model.
- Raises `RuntimeError("All LLM providers failed")` if entire chain exhausts.

### 9Router v0.4.66 Compatibility
- **SSE DONE Marker Stripping**: Implemented at line 89.
  ```python
  raw = re.sub(r"data: \[DONE\]\s*$", "", raw)
  result = json.loads(raw)
  ```
  This prevents JSON parsing errors when 9Router appends the SSE termination marker to non-streaming responses.

---

## 3. Budget Enforcement & Cost Tracking

### Global Cost Tracker (`src/core/services/cost_tracker.py`)
- Tracks Redis DB5 keys: `cost:current_month`, `cost:current_day`, `cost:by_model:{model}`, `cost:daily:{today}`, `cost:monthly:{month}`.
- **Calculation**: `(input_tokens / 1000 * cost_per_1k_input) + (output_tokens / 1000 * cost_per_1k_output)`
- **Status Levels**:
  - `HARD_STOP`: ratio >= 1.0 (100%)
  - `CRITICAL`: ratio >= 0.833 (83.3%)
  - `WARNING`: ratio >= 0.50 (50%)
  - `NORMAL_ALERT`: current >= $1.00
  - `NORMAL`: otherwise

### Loop Cost Tracker (`src/loops/cost.py`)
- Tracks per-loop instance costs and aggregates them into the global `CostTracker`.
- Stores per-model breakdown per loop in Redis DB5.

### MCP Tool Cost Tracker (`src/mcp/cost.py`)
- Tracks per-tool call costs in Redis DB5 with daily key rotation (`tool:cost:{tool_name}:YYYY-MM-DD`).
- Fixed costs defined: `brave_search` ($0.01), `exa` ($0.007), others $0.00 or variable (`websearch`).

### ⚠️ Budget Enforcement Gap
- The `budget` section in `hermes-config/config.yaml` explicitly states: *"Monthly budget tracking (informational — not read by Hermes)"*.
- The planned `hooks/budget.py` (Step 6.6 in `phase-6-llm.md`) **does not exist** in the codebase yet.
- **Conclusion**: Budget tracking is fully instrumented in Redis, but **active blocking/alerting at the Hermes gateway level is not yet implemented**.

---

## 4. 9Router Integration Details

| Component | Value / Location |
|---|---|
| Base URL | `http://localhost:20128/v1` (hardcoded in `llm_router.py`, `embeddings.py`, `main.py`, `config.yaml`) |
| API Key Env Var | `NINEROUTER_API_KEY` (referenced in `config.yaml` as `key_env`) |
| Model Namespace Format | `cx/` (OpenAI Codex), `ds/` (DeepSeek), or un-prefixed (`guinevere` combo) |
| Health Check Endpoint | `http://localhost:20128/health` (per Phase 6 docs) |
| Models Endpoint | `http://localhost:20128/v1/models` (checked in `src/core/main.py` line 263) |

---

## 5. Evidence from Previous Phases (`docs/setup-evidence/hermes-migration/phase-6-llm.md`)

The Phase 6 planning document outlines a 7-step procedure that is **partially complete**:

| Step | Status | Notes |
|---|---|---|
| 6.1 Configure 9Router as Custom Provider | ✅ **DONE** | Config reflects `ninerouter` provider at `localhost:20128`. |
| 6.2 Configure Fallback Chain | ⚠️ **PARTIAL** | `llm_router.py` has the logic, but `fallback_providers` is commented out in `config.yaml` due to GPT-5.5 token invalidation. |
| 6.3 Configure Budget Enforcement | ⚠️ **PARTIAL** | Config has the values, but Hermes does not read them. No active blocking. |
| 6.4 100-Prompt Compatibility Test | ❌ **PENDING** | `scripts/test_100_prompts.py` does not exist. |
| 6.5 Test Streaming Compatibility | ❌ **PENDING** | Requires manual or automated verification. |
| 6.6 Deploy Budget Enforcement Hook | ❌ **PENDING** | `hooks/budget.py` is not yet created. |
| 6.7 Test Conversation Commands | ❌ **PENDING** | Requires execution post-hook deployment. |

---

## 6. Exact Changes Needed for Phase 6

To align the codebase with the Phase 6 gate criteria, the following actions are required:

1. **Update `hermes-config/config.yaml`**:
   - Uncomment and configure `fallback_providers` with a valid, working model (e.g., keep `ds/deepseek-v4-flash` as primary, add `guinevere` combo as fallback, or await GPT-5.5 token refresh).
   - Ensure `budget` section is either removed (if Hermes truly ignores it) or integrated via the new hook.

2. **Create `hooks/budget.py`** (as specified in `phase-6-llm.md` Step 6.6):
   - Implement pre-tool-call or pre-LLM-call hook.
   - Read current spend from `hermes insights cost` or directly from Redis DB5 `cost:current_month`.
   - Return `{"action": "block"}` and exit 1 if ratio >= 1.00.
   - Return `{"action": "warn"}` and exit 2 if ratio >= 0.80.

3. **Register Budget Hook in `config.yaml`**:
   - Add `pre_llm_call` or `pre_tool_call` hook entry pointing to `python3 ~/.hermes/hooks/budget.py`.

4. **Create `scripts/test_100_prompts.py`**:
   - Implement the 100-prompt compatibility harness defined in the Phase 6 evidence doc.
   - Cover: short greetings, technical questions, emotional/persona, memory recall, long-form engineering, bilingual ID/EN, edge cases, and safety triggers.

5. **Verify SSE Stripping in Hermes Native Code**:
   - Confirm that Hermes Agent's native LLM client also strips the `data: [DONE]` marker, or rely entirely on `src/core/services/llm_router.py` for all LLM calls.

---

## 7. Risk Register for Phase 6 Execution

| Risk ID | Description | Score | Mitigation |
|---|---|---|---|
| R-P6-01 | Budget hook fails open, allowing overspend | HIGH | Implement strict `sys.exit(1)` on Redis read failure; default to block if cost data is stale > 1 hour. |
| R-P6-02 | 9Router token remains invalid for GPT-5.5 | MEDIUM | Proceed with DeepSeek V4 Flash as primary; use `guinevere` combo as fallback until token is refreshed. |
| R-P6-03 | Cost tracking diverges between Redis and PostgreSQL | MEDIUM | Add reconciliation job in Phase 7 to compare `cost:current_month` with DB ledger. |
| R-P6-04 | SSE `[DONE]` marker causes JSON parse errors in Hermes native client | MEDIUM | Audit Hermes Agent's internal HTTP client; apply regex strip if necessary. |

---

## 8. Auditor Gate Verification

- [x] `hermes-config/config.yaml` read and analyzed.
- [x] `src/core/services/llm_router.py` read and analyzed (104 lines).
- [x] Budget tracking code (`cost_tracker.py`, `loops/cost.py`, `mcp/cost.py`) audited.
- [x] 9Router integration points mapped.
- [x] Phase 6 evidence document cross-referenced.
- [x] Gap analysis completed and actionable steps defined.

> **Verdict**: READY FOR PLANNER GATE. Phase 6 implementation plan is fully scoped based on current state divergence from target state.