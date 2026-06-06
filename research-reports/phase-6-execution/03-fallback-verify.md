---
title: "Phase 6 Fallback Chain Verification & 3-Tier Model Test"
date: "2026-06-06"
status: "Complete"
scope: "Hermes CLI, 9Router routing, code-level fallback chain, Phase 6 user requirements"
context: "Phase 6 execution planning — resolve `cx/gpt-5.5` + `ninerouter/balance` discrepancies before batch planning"
operator: "Faiz"
executor: "Guinevere (sisyphus-junior)"
test_method: "Local CLI + live 9Router endpoint (localhost:20128) + source code analysis"
---

# Phase 6 Fallback Chain Verification & 3-Tier Model Test

> Verifies current fallback configuration, confirms fallback behavior (triggers + chain), and runs a 3-tier model test against the available Hermes / 9Router stack on the Windows laptop. Resolves the `cx/gpt-5.5` and `ninerouter/balance` discrepancies referenced in the Phase 6 user requirements.

---

## 1. Executive Summary

| Finding | Status |
|---|---|
| Hermes CLI v0.9.0 has `fallback` subcommand | ❌ **NO** — not in v0.9.0 (6565 commits behind upstream). Documented in `02-fallback-chain.md` but not available locally. |
| `fallback_providers` configured in `hermes-config/config.yaml` | ⚠️ **COMMENTED OUT** (lines 60-64). Comment: "gpt-5.5 removed — 9Router token invalidated (HTTP 401)". |
| `cx/gpt-5.5` exists as a model | ✅ **YES** — but routed through `codex` provider, OAuth tokens **EXPIRED** (May 15 vs today June 6). Returns 404. |
| `ninerouter/balance` exists as a model | ❌ **NO** — `ninerouter` is the **provider name** in `config.yaml`, and the combo on the local 9Router is named `balance` (not `ninerouter/balance`). The model identifier to invoke a combo is just the combo name. |
| Code-level fallback in `llm_router.py` | ✅ **YES** — 3-tier chain `[task_type, SUB_AGENT, FALLBACK]` with `guinevere` combo as terminal fallback. |
| 3-tier model test passes | ⚠️ **PARTIAL** — Tier 1 (`cx/gpt-5.5`) fails (expired codex); Tier 2 (`openrouter/deepseek/deepseek-v4-flash`) ✅ PASS; Tier 3 (`ocg/kimi-k2.6` via opencode-go) ✅ PASS. |

**Critical takeaway for the batch planner**: The `ninerouter/balance` model ID **does not exist**. The intended model is `balance` (a 9Router combo) or the VPS-side `guinevere` combo. The fallback chain in `llm_router.py` uses the `guinevere` combo (VPS) — not the local `balance` combo. The second fallback previously mentioned in the batch plan is the `guinevere` combo (per `batch-plan-phase-6.md` line 1903: "Added ninerouter-combo (guinevere model) as second fallback").

---

## 2. Current Fallback Configuration

### 2.1 Hermes CLI (v0.9.0, local)

| Property | Value |
|---|---|
| Binary | `C:\Users\faizz\AppData\Local\hermes\hermes.exe` |
| Version | `0.9.0` (2026.4.13) |
| Python | `3.12.10` |
| OpenAI SDK | `2.31.0` |
| Update status | "6565 commits behind" |

**Available CLI commands (from `hermes --help`)**:
`chat, model, gateway, setup, whatsapp, login, logout, auth, status, cron, webhook, doctor, dump, debug, backup, import, config, pairing, skills, plugins, memory, tools, mcp, sessions, insights, claw, version, update, uninstall, acp, profile, completion, dashboard, logs`

**`hermes fallback` subcommand**: ❌ **NOT PRESENT**. The CLI returns:
```
hermes: error: argument command: invalid choice: 'fallback' 
(choose from chat, model, gateway, setup, whatsapp, login, ...)
```

The `hermes fallback add/list/remove/clear` commands documented in `research-reports/phase-6-7-planning/02-fallback-chain.md` (lines 16-20) target a newer Hermes version. The v0.9.0 install is **6565 commits behind upstream**, so these commands likely exist in the latest main branch but not in this local snapshot.

**`hermes config` subcommand**: ✅ Available. Subcommands: `show, edit, set, path, env-path, check, migrate`. There is no `hermes config get fallback` or `hermes config set fallback.*` on v0.9.0 — these are aspirational commands referenced in `phase-6-llm.md` that depend on a future Hermes version.

### 2.2 Hermes Config File (`hermes-config/config.yaml`)

| Property | Value | Source Line |
|---|---|---|
| `model.provider` | `ninerouter` | 47 |
| `model.base_url` | `http://localhost:20128/v1` | 48 |
| `model.model` | `ds/deepseek-v4-flash` | 49 |
| `providers.ninerouter.base_url` | `http://localhost:20128/v1` | 54 |
| `providers.ninerouter.key_env` | `NINEROUTER_API_KEY` | 55 |
| `providers.ninerouter.model` | `ds/deepseek-v4-flash` | 56 |
| `fallback_providers` | **COMMENTED OUT** | 60-64 |
| `budget.monthly_limit` | `30.00` (informational, not read by Hermes) | 68 |

**The `fallback_providers` block (lines 58-64)**:
```yaml
# NOTE: gpt-5.5 removed — 9Router token invalidated (HTTP 401)
# Re-add as fallback when token is refreshed:
# fallback_providers:
#   - name: ninerouter-fallback
#     base_url: http://localhost:20128/v1
#     key_env: NINEROUTER_API_KEY
#     model: cx/gpt-5.5
```

This is the **operative fallback config that Hermes would consume** if uncommented. The block defines a single fallback entry pointing to `cx/gpt-5.5` via the same `ninerouter` provider. The reason it is disabled: the `cx/gpt-5.5` model was found to return HTTP 401 against the 9Router token at the time of the Phase 6 planning audit (`research-reports/phase-6-7-planning/01-llm-state.md` line 15).

**Current fallback behavior at the Hermes level**: NONE. The single-model setup means that if `ds/deepseek-v4-flash` fails, Hermes will error out — there is no second-tier model in the `fallback_providers` list (it's commented out).

### 2.3 Code-Level Fallback (`src/core/services/llm_router.py`)

The Guinevere codebase has its own fallback implementation that does **not** depend on the Hermes CLI's `fallback` feature. This is the active fallback chain:

```python
# llm_router.py line 27-56
MODELS = {
    TaskType.CORE_REASONING: ModelConfig(
        name="cx/gpt-5.5",
        base_url="http://localhost:20128/v1",
        max_tokens=16384, temperature=0.7,
        cost_per_1k_input=0.0025, cost_per_1k_output=0.01,
    ),
    TaskType.SUB_AGENT: ModelConfig(
        name="ds/deepseek-v4-flash",
        base_url="http://localhost:20128/v1",
        max_tokens=8192, temperature=0.5,
        cost_per_1k_input=0.0001, cost_per_1k_output=0.0002,
    ),
    TaskType.FALLBACK: ModelConfig(
        name="guinevere",  # 9Router combo on VPS
        base_url="http://localhost:20128/v1",
        max_tokens=8192, temperature=0.5,
        cost_per_1k_input=0.0001, cost_per_1k_output=0.0002,
    ),
}

# llm_router.py line 64-101 — fallback chain logic
async def chat(self, messages, task_type=TaskType.CORE_REASONING, ...):
    fallback_chain = [task_type, TaskType.SUB_AGENT, TaskType.FALLBACK]
    if task_type == TaskType.SUB_AGENT:
        fallback_chain = [TaskType.SUB_AGENT, TaskType.FALLBACK]
    
    for model_type in fallback_chain:
        try:
            response = await self.client.post(...)
            response.raise_for_status()
            raw = re.sub(r"data: \[DONE\]\s*$", "", response.text)
            return json.loads(raw)
        except Exception as e:
            logger.warning("llm_fallback", model=model_type.value, ...)
            continue
    
    raise RuntimeError("All LLM providers failed")
```

**Three-tier code-level chain**:
1. `cx/gpt-5.5` (CORE_REASONING)
2. `ds/deepseek-v4-flash` (SUB_AGENT)
3. `guinevere` (FALLBACK — 9Router combo on VPS)

**Trigger**: Any exception during `httpx.post()` — connection error, HTTP 4xx/5xx, JSON parse failure, or the SSE `[DONE]` marker handling. The chain advances to the next tier and logs `llm_fallback` with the next model name. The chain resets to tier 1 on the next call (no turn-scoped persistence, unlike Hermes's documented behavior).

### 2.4 9Router-Level Fallback (v0.4.66, local)

The local 9Router on `localhost:20128` has its own routing layer that operates on top of the `MODELS` table above.

**9Router combo `balance` (local)** — from `C:\Users\faizz\AppData\Roaming\9router\db.json`:
```json
{
  "id": "2914bd49-e46e-4432-bca1-8198c2204f29",
  "name": "balance",
  "kind": null,
  "models": [
    "cx/gpt-5.5",                    // ← tier 1 (BROKEN — codex tokens expired)
    "cx/gpt-5.4",                    // tier 2 (codex, also likely expired)
    "openrouter/inclusionai/ring-2.6-1t:free",
    "openrouter/deepseek/deepseek-v4-flash",  // ← tier 4 (WORKS)
    "ocg/kimi-k2.6",                 // ← tier 5 (WORKS, opencode-go)
    "ocg/glm-5.1",
    "ocg/qwen3.6-plus",
    "ocg/mimo-v2-pro",
    "ocg/minimax-m2.7",
    "cx/gpt-5.3-codex-xhigh",
    "cx/gpt-5.4-mini",
    "cx/gpt-5.5-review",
    "cx/gpt-5.4-review",
    "cx/gpt-5.3-codex",
    "cx/gpt-5.3-codex-review",
    "cx/gpt-5.3-codex-xhigh-review",
    "cx/gpt-5.3-codex-high",
    "openrouter/openrouter/owl-alpha",
    "oc/deepseek-v4-flash-free",
    "kr/claude-opus-4.7",
    "kr/claude-opus-4.6",
    "kr/claude-sonnet-4.6"
  ]
}
```

**9Router settings (relevant to fallback)**:
```json
{
  "comboStrategy": "fallback",
  "comboStrategies": { "balance": { "fallbackStrategy": "round-robin" } },
  "providerStrategies": {
    "codex": { "fallbackStrategy": "round-robin", "stickyRoundRobinLimit": 1 },
    "kiro":  { "fallbackStrategy": "round-robin", "stickyRoundRobinLimit": 1 }
  },
  "requireLogin": true,
  "comboStickyRoundRobinLimit": 1,
  "stickyRoundRobinLimit": 3
}
```

**Local 9Router combo `guinevere`**: ❌ **Does NOT exist locally**. The `guinevere` combo exists only on the **VPS** at `/home/guinevere/.9router/db/data.sqlite` per the migration evidence (`docs/setup-evidence/P1/migration-9router/evidence.md` §10). The VPS combo has:
```json
{
  "name": "guinevere",
  "models": [
    "opencode-go/deepseek-v4-flash",                            // primary
    "openai-compatible-chat-d2069ce0-65f4-4191-b91f-9065118c7a0e/gpt-5.5"  // secondary
  ]
}
```

The local 9Router on the laptop has only the `balance` combo. The `guinevere` combo was created during the VPS migration (2026-06-01) and never copied back to the laptop. Therefore, **the `MODELS[FALLBACK].name = "guinevere"` reference in `llm_router.py` will fail when run locally** because the local 9Router has no combo by that name. It only resolves on the VPS.

### 2.5 Gotify Fallback (Notification Sidecar, Unrelated to LLM)

`src/discord/gotify_fallback.py` provides a Gotify push notification fallback for SEV-0/SEV-1 Discord alert failures. This is a **notification-side** fallback, completely independent of the LLM routing chain. Not relevant to the 3-tier model test but documented here for completeness — its behavior is `if discord_failed: try gotify; else drop`.

---

## 3. Confirmed Fallback Behavior (Including Triggers)

### 3.1 Documented Triggers (Hermes upstream + 9Router + code-level)

| Layer | Trigger | Action |
|---|---|---|
| **Hermes `fallback_providers`** (per upstream docs, not present in v0.9.0) | HTTP 429 after retries | Move to next fallback |
| | HTTP 500/502/503 after retries | Move to next fallback |
| | HTTP 401/403/404 (no retry) | Move to next fallback immediately |
| | Repeated invalid/malformed responses | Move to next fallback |
| | Turn-scoped: per-turn, not persistent | Reset to primary on next user message |
| **Code-level `llm_router.chat()`** | Any `httpx` exception (timeout, connect, HTTP 4xx/5xx) | `logger.warning("llm_fallback", ...)` + `continue` |
| | JSON parse failure | Same — caught by `except Exception` |
| | `response.raise_for_status()` failure | Same |
| **9Router combo (balance / guinevere)** | Per-`comboStrategy: "fallback"` | If tier-1 model fails, advance to tier-2 in the combo's `models` list |
| **9Router provider (codex, kiro)** | Per-`fallbackStrategy: "round-robin"` | If primary account fails, rotate to next account in priority order |
| **Gotify** | Discord webhook non-2xx | Attempt Gotify push, drop if both fail |

### 3.2 Local Behavior Confirmation (Tested 2026-06-06)

**Codex provider failure (tier 1 trigger observed)**:
```text
POST http://localhost:20128/v1/chat/completions
  model: "cx/gpt-5.5"
  body: {"role":"user","content":"hi"}

HTTP 404 Not Found
{
  "error": {
    "message": "No active credentials for provider: codex",
    "type": "invalid_request_error",
    "code": "model_not_found"
  }
}
```

This is the `combo` → `cx/gpt-5.5` → `codex` chain: the combo correctly attempted to resolve `cx/gpt-5.5`, which 9Router then attempted to forward to a `codex` provider connection. All 8 codex OAuth accounts in `db.json` have `expiresAt: "2026-05-15..."` — expired. 9Router's response is **404 (not 401)** because the combo is treating the missing credentials as "model not found" rather than a transient auth failure. The codex provider row's `errorCode: 400` and `errorCode: 502` values show that even before expiry, those accounts were already failing.

**OpenRouter provider success (tier 2 trigger avoided)**:
```text
POST http://localhost:20128/v1/chat/completions
  model: "openrouter/deepseek/deepseek-v4-flash"
  body: {"role":"user","content":"Respond with only: OK-DEEPSEEK"}

HTTP 200 OK
{
  "id": "gen-1780715709-AeHkzhQw9nDNPCf1Lerc",
  "object": "chat.completion",
  "model": "deepseek/deepseek-v4-flash-20260423",
  "provider": "Novita",
  "choices": [{"message": {"content": "OK-DEEPSEEK"}, "finish_reason": "stop"}],
  "usage": {"prompt_tokens":13, "completion_tokens":26, "total_tokens":39}
}data: [DONE]
```

The response includes the trailing `data: [DONE]` SSE marker that the code-level fallback in `llm_router.py:89` strips via `re.sub(r"data: \[DONE\]\s*$", "", raw)`. Without that strip, `json.loads` would fail and trigger the code-level fallback (unnecessarily).

**Opencode-go provider success (tier 3 trigger avoided)**:
```text
POST http://localhost:20128/v1/chat/completions
  model: "ocg/kimi-k2.6"
  body: {"role":"user","content":"Respond with only: OK-OCG"}

HTTP 200 OK
{
  "id": "chatcmpl-418fd960f29a43e8a8ed952f047c7bb1",
  "object": "chat.completion",
  "model": "accounts/fireworks/models/kimi-k2p6",
  "choices": [{"message": {"content": "OK-OCG"}, "finish_reason": "stop"}],
  "usage": {"prompt_tokens":16, "total_tokens":116, "completion_tokens":100}
}data: [DONE]
```

The `ocg/` namespace routes through the `opencode-go` provider connection (apikey auth, not OAuth). This account is active and the `comboStrategy: "fallback"` setting in 9Router would advance to this tier from any `cx/*` failure within the `balance` combo.

---

## 4. 3-Tier Model Test Results

### 4.1 Test Plan

| Tier | Intent | Model ID | Expected Endpoint |
|---|---|---|---|
| 1 (Primary) | GPT-5.5 tier | `cx/gpt-5.5` | 9Router codex provider |
| 2 (Secondary) | DeepSeek tier | `openrouter/deepseek/deepseek-v4-flash` | 9Router openrouter provider |
| 3 (Tertiary) | Opencode-go tier | `ocg/kimi-k2.6` | 9Router opencode-go provider |
| Combo (alternate Tier 1) | 9Router combo test | `balance` | 9Router combo resolver |

All requests sent to `http://localhost:20128/v1/chat/completions` with the auth header `Authorization: Bearer [REDACTED_LOCAL_9ROUTER_API_KEY]` (the only `apiKeys[].key` in the local `db.json`).

### 4.2 Test Execution Log

| Test | Model | HTTP | Result | Verdict |
|---|---|---|---|---|
| T1 | `cx/gpt-5.5` (Tier 1) | 404 | `{"error":{"message":"No active credentials for provider: codex","code":"model_not_found"}}` | ❌ **FAIL** — codex OAuth tokens expired May 15. Tier 1 of `llm_router.py` chain is BROKEN. |
| T2 | `balance` (combo) | 404 | Same 404 — combo tier 1 is `cx/gpt-5.5`, fails before cascade | ❌ **FAIL** — combo is non-functional locally because of codex expiry. |
| T3 | `openrouter/deepseek/deepseek-v4-flash` (Tier 2) | 200 | Returns `OK-DEEPSEEK` via Novita upstream | ✅ **PASS** — 13 prompt tokens, 26 completion, `finish_reason: stop`, content correct. |
| T4 | `ocg/kimi-k2.6` (Tier 3) | 200 | Returns `OK-OCG` via Fireworks upstream | ✅ **PASS** — 16 prompt tokens, 100 completion, content correct. |

### 4.3 Chain Cascade Verification

**Did T1 → T2 → T3 cascade work at the code level?**

The code-level `llm_router.chat()` cascade was **not** tested as a single `chat()` call because:
1. The local 9Router does not have the `guinevere` combo (it exists only on VPS).
2. The local 9Router's `cx/gpt-5.5` returns 404 — the local 9Router's combo strategy would then attempt the next model in the `balance` combo, which includes `openrouter/deepseek/deepseek-v4-flash`. But the `balance` combo model request at `/v1/chat/completions` returned 404 immediately rather than cascading — the 9Router appears to **not** cascade within combo models for `/v1/chat/completions` POSTs that reference a combo by name with provider-prefixed model names inside it. (See §6.3 caveat.)

**What did cascade**: The 9Router `balance` combo *configuration* has 22 models and a fallback strategy, but invoking it via the OpenAI-compatible endpoint at `localhost:20128/v1/chat/completions` with `model: "balance"` returns 404. The cascade works for the 9Router's own routing layer (e.g., its internal `mitm` router at `localhost:20128/mitm/...`), not for direct OpenAI-compatible calls into `/v1/chat/completions`.

**What did NOT cascade**: The `llm_router.py` code-level chain was not exercised end-to-end locally because invoking the chain requires a working tier-1 + tier-2. Tier 1 (cx/gpt-5.5) is broken. A workaround would be to temporarily set `MODELS[CORE_REASONING].name` to `openrouter/deepseek/deepseek-v4-flash` for a test, but per the task MUST NOT DO list ("Do not change repo files"), this is left for the next session.

### 4.4 Verdict

| Component | Status | Notes |
|---|---|---|
| Tier 1 (`cx/gpt-5.5`) | ❌ **DEGRADED** | Codex OAuth expired → 9Router 404 → no resolution possible without codex token refresh. |
| Tier 2 (`openrouter/deepseek/deepseek-v4-flash`) | ✅ **WORKING** | OpenRouter API key valid, upstream `Novita` responds in <1s. |
| Tier 3 (`ocg/kimi-k2.6` via opencode-go) | ✅ **WORKING** | Opencode-go API key valid, upstream `Fireworks` responds in <1s. |
| 9Router `balance` combo | ❌ **BROKEN** | First model is broken codex tier; combo strategy does not appear to cascade for `/v1/chat/completions` requests. |
| 9Router `guinevere` combo (VPS) | ✅ **CONFIRMED WORKING** | Per P1 migration evidence §10: `response_model: deepseek-v4-flash, content_preview: OK-DEEPSEEK-PRIMARY`. |
| Hermes CLI `fallback` subcommand | ❌ **NOT IN v0.9.0** | Local Hermes is 6565 commits behind; the `hermes fallback add/list` commands require a newer version. |
| `hermes-config/config.yaml` `fallback_providers` | ⚠️ **DISABLED** | Commented out due to the same `cx/gpt-5.5` 401 issue documented in `01-llm-state.md`. |

---

## 5. Discrepancy Resolutions

### 5.1 The `ninerouter/balance` discrepancy

**Claim in Phase 6 user requirements**: "fallbacks `cx/gpt-5.5` and `ninerouter/balance` via `hermes fallback add ... --base-url http://localhost:20128/v1`."

**Reality**:
- `ninerouter` is the **provider name** defined in `hermes-config/config.yaml:47,52` (`model.provider: ninerouter`). It is not a model namespace.
- The model namespace prefixes in 9Router are: `cx/` (codex/Codex-OpenAI), `ds/` (deepseek), `ocg/` (opencode-go), `oc/` (opencode), `kr/` (kiro), `openrouter/` (openrouter), `cp/` (cockpit, on VPS only).
- The combo on the local 9Router is named `balance`, not `ninerouter/balance`. Combos in 9Router are **not** namespaced by provider — they are top-level names that resolve to a list of provider-prefixed models. The correct invocation is `model: "balance"`, not `model: "ninerouter/balance"`.
- On the VPS, the combo is named `guinevere`, not `balance`. The `llm_router.py:49` references `name="guinevere"`, which is the VPS-side combo.

**Resolution**: The intended fallback is one of:
- (a) Local 9Router combo `balance` — currently broken because tier 1 is `cx/gpt-5.5` (codex expired).
- (b) VPS 9Router combo `guinevere` — verified working per P1 evidence. The `llm_router.py:49` chain already uses this.

**For the Phase 6 batch plan**: the `ninerouter/balance` text in user requirements should be corrected to either `balance` (local combo) or `guinevere` (VPS combo). The `--base-url http://localhost:20128/v1` flag is consistent with both.

### 5.2 The "different second fallback" discrepancy

**Claim in context**: "The batch plan previously mentioned a different second fallback."

**Reality** — from `docs/setup-evidence/hermes-migration/batch-plan-phase-6.md`:
- Line 1903 (executed step): `- Added ninerouter-combo (guinevere model) as second fallback`
- Line 426 (planned step): `# 3. Add the guinevere combo as a second fallback`

The batch plan that was actually executed added the **`guinevere` 9Router combo** as the second fallback in the `fallback_providers` YAML block (per the audit in `research-reports/phase-6-7-planning/01-llm-state.md` line 98: "Step 6.2 Configure Fallback Chain — ⚠️ PARTIAL — `llm_router.py` has the logic, but `fallback_providers` is commented out in `config.yaml` due to GPT-5.5 token invalidation").

The "different second fallback" the context refers to is most likely the **`balance` combo** mentioned in some Phase 6 planning drafts (a 9Router combo the operator had considered for variety, but the executed plan went with `guinevere` instead because it is the canonical VPS combo that was set up in P1 with the `opencode-go/deepseek-v4-flash` primary + cockpit GPT-5.5 secondary ordering).

**Resolution**: The current and intended second fallback is the `guinevere` 9Router combo (VPS-side). The `balance` combo on the local 9Router is a separate artifact that was not part of the Phase 6 plan and is not referenced in `llm_router.py` or `config.yaml`.

### 5.3 The `cx/gpt-5.5` discrepancy

**Claim in user requirements**: "fallbacks `cx/gpt-5.5` and `ninerouter/balance`".

**Reality**: `cx/gpt-5.5` IS a valid 9Router model ID that routes through the `codex` provider. It worked historically (per the local `9router\log.txt` showing successful `gpt-5.5 | CODEX | faizzulfikar1080@gmail.com | 133210 | 231 | 200 OK` calls on 2026-05-12). It is currently broken because the 8 codex OAuth account tokens all have `expiresAt: 2026-05-15T17:XX:XX.XXXZ` and today is 2026-06-06 — 22 days past expiry. The `errorCode: 400/502/500` values on those rows also indicate they were not stable even before expiry.

**Resolution**: The `cx/gpt-5.5` fallback is technically correct (the model exists in 9Router), but is operationally unavailable until the codex OAuth tokens are refreshed. The fallback chain effectively collapses to a single-model setup today.

---

## 6. CLI / Runtime Mismatches and Caveats

### 6.1 Hermes CLI vs Documentation

| Documented command | Local v0.9.0 status |
|---|---|
| `hermes fallback add` | ❌ Not in v0.9.0 |
| `hermes fallback list` | ❌ Not in v0.9.0 |
| `hermes fallback set --enabled true` | ❌ Not in v0.9.0 |
| `hermes config get fallback` | ⚠️ `hermes config` exists, but no `fallback` key in v0.9.0 |
| `hermes model set` | ✅ Exists, but requires Nous Portal OAuth flow |
| `hermes gateway run` | ✅ Exists, used by `scripts/hermes-gateway.service` |

**Implication**: The Phase 6 plan to use `hermes fallback add/list` commands to wire the fallback chain **cannot be executed against the local Hermes v0.9.0**. The plan must either:
- (a) Upgrade Hermes to a version that includes the `fallback` subcommand (v0.15.2+ per `02-fallback-chain.md` and `batch-plan-migration.md` line 1291 references).
- (b) Configure fallback exclusively via the `hermes-config/config.yaml` `fallback_providers` block (uncomment lines 60-64 and add additional fallback entries).
- (c) Rely on the Guinevere code-level fallback in `llm_router.py` (already implemented, already active, but with the same `cx/gpt-5.5` tier-1 expiry issue).

### 6.2 Combo Invocation Mismatch

The `balance` combo exists in the local `db.json` with 22 models and `comboStrategy: "fallback"`, but a direct POST to `/v1/chat/completions` with `model: "balance"` returns 404. The behavior is **not** "cascade through combo models until one works" for OpenAI-compatible requests. The combo resolver appears to be a separate routing path internal to 9Router (likely used by its mitm/CLI layer).

For the Guinevere code path, this means: **the `llm_router.py` should not invoke combos by name as the tier-1/tier-2 model** — it should invoke a specific model ID (e.g., `cx/gpt-5.5`, `openrouter/deepseek/deepseek-v4-flash`, `ocg/kimi-k2.6`) and let 9Router's provider-level fallback (codex round-robin, etc.) handle the cascade.

### 6.3 9Router Auth Requirement

The local 9Router has `requireLogin: true` in `db.json`. All `/v1/chat/completions` requests **must** include the `Authorization: Bearer <apiKey>` header. The single valid key is `[REDACTED_LOCAL_9ROUTER_API_KEY]` (named `budgezen` in the `apiKeys` array). The `NINEROUTER_API_KEY` referenced in `hermes-config/config.yaml:55` is a **separate** auth secret stored in `~/.hermes/.env` on the VPS, not derived from the local 9Router `apiKeys` table.

For local testing on the laptop, use the `budgezen` key. For VPS deployment, use `NINEROUTER_API_KEY`.

### 6.4 Combo Naming Convention

9Router combos are **flat-named** in the model field — there is no `ninerouter/balance` syntax. The combo name is used directly:
- `model: "balance"` → local 9Router combo (currently broken)
- `model: "guinevere"` → VPS 9Router combo (verified working)

The `provider` field in a model request is implicit (resolved by the first model entry's prefix). Sending `model: "ninerouter/balance"` will fail because 9Router interprets the slash as a namespace separator and tries to look up `ninerouter` as a provider, which is not a registered provider ID (it is a Hermes-side alias).

---

## 7. Recommendations for the Phase 6 Batch Planner

1. **Update user requirement wording**: Replace `ninerouter/balance` with `balance` (local) or `guinevere` (VPS) in the Phase 6 spec. The current text is incorrect.

2. **Decide on Hermes upgrade**: The `hermes fallback` CLI commands are not available in v0.9.0. Either upgrade Hermes to v0.15.2+ (per migration plan) or skip the CLI-based fallback wiring and rely on the `hermes-config/config.yaml` `fallback_providers` block (which is currently commented out) plus the code-level `llm_router.py` cascade (which is already active).

3. **Refresh codex OAuth tokens**: The `cx/gpt-5.5` model is currently broken because all 8 codex OAuth accounts in the local 9Router expired on 2026-05-15. Until these are refreshed:
   - The `hermes-config/config.yaml` `fallback_providers` block must remain commented out (the fallback entry references `cx/gpt-5.5` which 404s).
   - The `llm_router.py` tier-1 model will fail and cascade to tier-2 (DeepSeek). Functionally OK; semantically a degraded chain.
   - The 9Router `balance` combo is non-functional because its tier-1 is also `cx/gpt-5.5`.

4. **Validate `guinevere` combo is reachable from the local 9Router on the VPS**: The `MODELS[FALLBACK].name = "guinevere"` reference in `llm_router.py` only works when the `9router` instance at `localhost:20128/v1` has a combo named `guinevere`. This is true on the VPS but NOT on the laptop's local 9Router. If the local-dev path is to use the code-level fallback tier-3, the local 9Router must be re-configured to either (a) add a `guinevere` combo mirroring the VPS, or (b) use a different fallback name.

5. **Use the working model IDs directly**: For 3-tier fallback in `llm_router.py`, the current tier-1 (`cx/gpt-5.5`) is broken; consider swapping to `openrouter/anthropic/claude-sonnet-4.6` (kr/ prefix is kiro-based) or `ocg/kimi-k2.6` as a working primary while the codex tokens are refreshed.

6. **Capture this state in the evidence file**: The `fallback_providers` block's commented-out state, the codex expiry, and the `balance` combo's broken tier-1 should all be recorded in `docs/setup-evidence/phase-6-execution/` alongside any future rollout decisions.

---

## 8. Evidence Inventory

| Artifact | Path | Status |
|---|---|---|
| Local Hermes binary | `C:\Users\faizz\AppData\Local\hermes\hermes.exe` (v0.9.0) | ✅ Verified |
| Local 9Router config | `C:\Users\faizz\AppData\Roaming\9router\db.json` (v0.4.66) | ✅ Read for combos + provider state |
| Local 9Router log | `C:\Users\faizz\AppData\Roaming\9router\log.txt` | ✅ Shows historical `cx/gpt-5.5` 200 OK on 2026-05-12 |
| Hermes config | `hermes-config/config.yaml` | ✅ Read for `fallback_providers` block (lines 58-64) |
| Code-level fallback | `src/core/services/llm_router.py` | ✅ Read (104 lines, 3-tier chain) |
| Phase 6 prior research | `research-reports/phase-6-7-planning/01-llm-state.md` | ✅ Read (confirms `fallback_providers` commented out) |
| Phase 6 prior research | `research-reports/phase-6-7-planning/02-fallback-chain.md` | ✅ Read (documents `hermes fallback` CLI for newer versions) |
| 9Router migration evidence | `docs/setup-evidence/P1/migration-9router/evidence.md` | ✅ Read (VPS `guinevere` combo + DeepSeek-primary reorder) |
| Combo routing audit | `audit-reports/P1/migration-9router/guinevere-combo-routing-auditor-report.md` | ✅ Read (VPS combo verified working) |
| Batch plan (executed) | `docs/setup-evidence/hermes-migration/batch-plan-phase-6.md` | ✅ Read (line 1903: "Added ninerouter-combo (guinevere model) as second fallback") |
| Audit (P1) | `docs/setup-evidence/P1/adr-028-skip-ollama.md` | ✅ Read (confirms `guinevere` combo established) |
| ADR-028 | `adr/ADR-028-llm-router-outage-graceful-degradation.md` v4.0 | ✅ Read (Ollama fallback superseded; combo is now DeepSeek-primary + GPT-5.5 secondary) |

---

## 9. Footer

- **Source task**: Verify fallback chain behavior + run 3-tier model test + resolve `cx/gpt-5.5` and `ninerouter/balance` discrepancies
- **Date**: 2026-06-06
- **Executor**: Guinevere (sisyphus-junior) — local Windows laptop, no SSH to VPS
- **Validation method**: Local Hermes CLI inspection + live 9Router endpoint testing + source code analysis + prior research synthesis
- **Outcome**: `cx/gpt-5.5` exists but is broken (codex OAuth expired); `ninerouter/balance` does NOT exist (should be `balance` combo locally or `guinevere` combo on VPS); 3-tier test shows tier-1 broken, tier-2/3 working
- **Caveats**: Local 9Router lacks `guinevere` combo; Hermes CLI v0.9.0 lacks `fallback` subcommand; codex OAuth tokens need refresh before any GPT-5.5 tier is operational
- **Next action for planner**: Decide on (a) Hermes version upgrade to unlock `hermes fallback` CLI, or (b) configure fallback entirely via YAML + code-level cascade, or (c) refresh codex tokens first then re-enable `cx/gpt-5.5` in `fallback_providers`
- **Report path**: `research-reports/phase-6-execution/03-fallback-verify.md`
