# Phase 6 — LLM Routing State Research Report

**Date**: 2026-06-06
**Scope**: Current VPS Hermes LLM configuration, active model, provider/base_url, fallback settings, budget, credential pooling, discrepancies vs ADR-035 Phase 6 requirements
**Method**: Remote SSH inspection (`guinevere-vps`), `hermes doctor`, `hermes security`, direct 9Router API query, local config comparison

---

## 1. VPS Hermes Config — Core LLM Section

File: `/home/guinevere/.hermes/config.yaml` (14,753 bytes, `_config_version: 24`)

```yaml
model:
  base_url: http://localhost:20128/v1
  model: ds/deepseek-v4-flash
  provider: ninerouter

providers:
  ninerouter:
    base_url: http://localhost:20128/v1
    key_env: NINEROUTER_API_KEY
    model: ds/deepseek-v4-flash
    name: ninerouter

fallback_providers: []

credential_pool_strategies: {}
```

**Key values**:
| Field | Value |
|---|---|
| **Active Model** | `ds/deepseek-v4-flash` |
| **Provider** | `ninerouter` |
| **Base URL** | `http://localhost:20128/v1` |
| **API Key Env Var** | `NINEROUTER_API_KEY` |
| **Fallback Providers** | `[]` — **empty** |
| **Credential Pool Strategies** | `{}` — **empty** |

---

## 2. Hermes Gateway Status

| Property | Value |
|---|---|
| **Hermes Version** | `v0.15.2` (2026.5.29.2) |
| **PID** | 4124751 |
| **State** | `running` |
| **Discord** | `connected` |
| **Active Agents** | 0 |
| **Config Version** | v24 |

Gateway started from: `/home/guinevere/code/guinevere/.venv/bin/hermes gateway run --accept-hooks`

### Active systemd Services

| Service | Status |
|---|---|
| `hermes-gateway.service` | active (running) — Hermes Agent Discord gateway |
| `guinevere-9router.service` | active (running) — 9Router LLM Proxy |
| `guinevere-core.service` | active (running) |
| `guinevere-loops.service` | active (running) |
| `guinevere-scheduler.service` | active (running) |
| `guinevere-surveillance.service` | active (running) |
| `guinevere-monitoring.service` | active (running) |
| `cloudflared.service` | active (running) — Cloudflare Tunnel for Discord webhook |

**Note**: `guinevere-discord` service is **inactive** — old custom bot.py stack is fully replaced by `hermes-gateway.service`.

---

## 3. `hermes doctor` Findings

Run via `source .venv/bin/activate && hermes doctor`:

### Healthy
- ✓ Python 3.12.3, virtual env OK
- ✓ OpenAI SDK v2.24.0
- ✓ Config file exists and parseable
- ✓ Config version up to date (v24)
- ✓ SOUL.md exists (persona configured)
- ✓ state.db exists (4 sessions)
- ✓ No active security advisories
- ✓ API connectivity: 26 checks passed (no direct failures)
- ✓ Directory structure complete
- ✓ All required packages installed

### Warnings / Issues

| # | Severity | Finding |
|---|---|---|
| 1 | ⚠️ | `model.default 'ds/deepseek-v4-flash'` uses a vendor/model slug but `provider` is `ninerouter` (vendor-prefixed slugs belong to aggregators like OpenRouter). **Either set provider to `openrouter` or drop the vendor prefix.** |
| 2 | ⚠️ | Missing API keys for full tool access: `EXA_API_KEY`, `PARALLEL_API_KEY`, `TAVILY_API_KEY`, `FIRECRAWL_API_KEY`, `XAI_API_KEY` |
| 3 | ⚠️ | Entry point not found in venv bin — recommended: `pip install -e '.[all]'` |
| 4 | ⚠️ | Optional: ripgrep not installed, agent-browser not installed |

### `hermes security` Findings
- 10 vulnerability findings across 136 components
- All MODERATE/LOW/UNKNOWN severity — no HIGH/CRITICAL
- Primarily pip, PyJWT, torch CVEs — none directly affecting LLM routing

---

## 4. 9Router Model Availability

HTTP 200 at `http://localhost:20128/v1/models`. Complete model list:

| Model ID | Provider |
|---|---|
| `guinevere` | combo (custom routing) |
| `ds/deepseek-v4-pro` | deepseek |
| `ds/deepseek-v4-pro-max` | deepseek |
| `ds/deepseek-v4-pro-none` | deepseek |
| `ds/deepseek-v4-flash` | deepseek |
| `ds/deepseek-chat` | deepseek |
| `ds/deepseek-reasoner` | deepseek |
| `xmtp/mimo-v2.5-pro` | xmtp |
| `xmtp/mimo-v2.5` | xmtp |
| `xmtp/mimo-v2-pro` | xmtp |
| `xmtp/mimo-v2-omni` | xmtp |
| `xmtp/mimo-v2-tts` | xmtp |
| `xmtp/mimo-v2.5-tts` | xmtp |
| `xmtp/mimo-v2.5-tts-voiceclone` | xmtp |
| `xmtp/mimo-v2.5-tts-voicedesign` | xmtp |
| `cx/gpt-5.5` | cx |
| `cx/gpt-5.5-review` | cx |
| `cx/gpt-5.4` | cx |
| `cx/gpt-5.4-review` | cx |
| `cx/gpt-5.4-mini` | cx |
| `cx/gpt-5.4-mini-review` | cx |
| `cx/gpt-5.3-codex` | cx |
| `cx/gpt-5.3-codex-review` | cx |
| `cx/gpt-5.3-codex-xhigh` | cx |
| `cx/gpt-5.3-codex-xhigh-review` | cx |
| `cx/gpt-5.3-codex-high` | cx |
| `cx/gpt-5.3-codex-high-review` | cx |
| `cx/gpt-5.3-codex-low` | cx |
| `cx/gpt-5.3-codex-low-review` | cx |
| `cx/gpt-5.3-codex-none` | cx |
| `cx/gpt-5.3-codex-none-review` | cx |
| `cx/gpt-5.3-codex-spark` | cx |
| `cx/gpt-5.3-codex-spark-review` | cx |
| `ocg/kimi-k2.6` | ocg |
| `ocg/kimi-k2.5` | ocg |
| `ocg/glm-5.1` | ocg |
| `ocg/glm-5` | ocg |
| `ocg/qwen3.5-plus` | ocg |
| `ocg/qwen3.6-plus` | ocg |
| `ocg/mimo-v2-pro` | ocg |
| `ocg/mimo-v2-omni` | ocg |
| `ocg/minimax-m2.7` | ocg |
| `ocg/minimax-m2.5` | ocg |
| `qd/auto` | qd |
| `qd/ultimate` | qd |
| `qd/performance` | qd |
| `qd/efficient` | qd |
| `qd/lite` | qd |
| `qd/qmodel_latest` | qd |
| `qd/qmodel` | qd |
| `qd/dmodel` | qd |
| `qd/dfmodel` | qd |
| `qd/gm51model` | qd |
| `qd/kmodel` | qd |
| `qd/mmodel` | qd |

**Note**: `cx/gpt-5.5` is available via 9Router but **NOT configured** as primary or fallback in Hermes config.

---

## 5. Budget Settings

From VPS `/home/guinevere/.hermes/config.yaml`:

```yaml
budget:
  alert_threshold: 0.8
  block_threshold: 1.0
  currency: USD
  monthly_limit: 30.0
```

```yaml
approvals:
  mode: manual
  timeout: 60
  cron_mode: deny
  mcp_reload_confirm: true
  destructive_slash_confirm: true
```

| Field | Value | Note |
|---|---|---|
| `monthly_limit` | 30.0 USD | ✓ Matches FinOps target |
| `alert_threshold` | 0.8 (80%) | Alert at $24 |
| `block_threshold` | 1.0 (100%) | Block at $30 |
| Enforcement | `approvals.mode: manual` | Hermes native; no custom `pre_tool_call` budget hook |

**ADR-035-specified budget enforcement**: ADR-035 §Pillar 5 recommends a custom `pre_tool_call` hook for budget enforcement. The VPS does **not** have this — it uses Hermes native `approvals.mode: manual` instead.

---

## 6. Plugins & Hooks Configuration

### Active Plugins
```yaml
plugins:
  enabled:
    - auth_overlay    # Auth matrix enforcement
    - guinevere-persona  # Persona state injection
  disabled: []
```

### Active Hooks
```yaml
hooks:
  post_tool_call:
    - command: python3 ~/.hermes/hooks/dnr_filter.py
      event: post_tool_call
      on_failure: block
      priority: 70
      timeout_ms: 50
  pre_tool_call:
    - command: python3 ~/.hermes/hooks/consent_gate.py
      event: pre_tool_call
      on_failure: block
      priority: 90
      timeout_ms: 200
```

Only **2 hooks** are active: `pre_tool_call` (consent_gate) and `post_tool_call` (dnr_filter). No `pre_prompt` HARD STOP hook, no `post_prompt` drift detection, no `post_response` yandere/secret scanner — these safety features are presumably handled by the `guinevere-persona` plugin instead.

---

## 7. Local vs VPS Config Discrepancy

The local `hermes-config/config.yaml` (338 lines) is a **completely different schema** from the VPS `/home/guinevere/.hermes/config.yaml` (14,753 bytes, ~320+ keys).

| Aspect | Local `hermes-config/config.yaml` | VPS `.hermes/config.yaml` |
|---|---|---|
| **Config version** | Not versioned | `_config_version: 24` |
| **Schema** | Old Guinevere-style | Hermes-native flat schema |
| **model** dict | Uses old nested format | Uses Hermes `model:` / `providers:` split |
| **discord** section | Custom Guinevere keys | Hermes native discord keys |
| **hooks** section | Full safety hook config | Minimal — only 2 hooks |
| **plugins** | Not supported in old schema | `auth_overlay` + `guinevere-persona` |
| **mcp_servers** | Custom FastMCP config | Hermes native MCP (stdio-based) |
| **budget** | Present, same values | Present, same values |
| **auth_matrix** | Reference YAML | Embedded in config |

The local `hermes-config/config.yaml` appears to be a **deployment reference / plan template** — it documents the intended config shape but does NOT match the actual running config on the VPS.

---

## 8. Discrepancies vs ADR-035 Phase 6 Requirements

ADR-035 specifies:

### Pillar 5: LLM = RETAIN 9Router at localhost:20128

| Requirement (ADR-035) | VPS Actual | Status |
|---|---|---|
| **Primary model**: `gpt-5.5` | `ds/deepseek-v4-flash` | ❌ **MISMATCH** |
| **Provider**: `custom` | `ninerouter` | ⚠️ **Nominal mismatch** — flagged by `hermes doctor` |
| **Base URL**: `http://localhost:20128/v1` | `http://localhost:20128/v1` | ✅ **Match** |
| **Fallback chain**: GPT-5.5 → DeepSeek V4 Flash | `fallback_providers: []` (empty) | ❌ **NO FALLBACK CONFIGURED** |
| **API Key**: `${NINEROUTER_API_KEY}` | `key_env: NINEROUTER_API_KEY` in config | ✅ **Configured** |
| **`credential_pool_strategies`** | `{}` (empty) | ❌ **NOT CONFIGURED** |
| **Budget: $30/month** | `monthly_limit: 30.0` | ✅ **Set** |
| **Budget enforcement**: custom `pre_tool_call` hook | `approvals.mode: manual` (Hermes native) | ⚠️ **Different mechanism** |
| **Shadow mode**: old `guinevere-discord` + Hermes | `guinevere-discord` service is **inactive** | ❌ **NOT IN SHADOW MODE** — cutover already complete |

---

## 9. Risk Analysis

### Critical Risks

1. **No fallback model configured**: If 9Router goes down or `ds/deepseek-v4-flash` returns errors, Hermes has zero fallback — the entire agent goes offline. ADR-005 mandates failover strategy.

2. **Primary model mismatch**: ADR-035 specifies `gpt-5.5` as the primary LLM for reasoning-heavy tasks. The VPS runs `ds/deepseek-v4-flash` exclusively. This means:
   - No access to GPT-5.5's 1M context window
   - Reduced reasoning quality for complex tasks
   - No GPT-5.5 Codex capabilities for engineering work

3. **Provider naming flagged**: `hermes doctor` explicitly warns that using `ninerouter` as provider with a vendor-prefixed model slug is incorrect — this may cause routing issues or unexpected behavior.

### High Risks

1. **No credential rotation**: `credential_pool_strategies: {}` means no multi-key rotation if the `NINEROUTER_API_KEY` is rate-limited or expires.

2. **Budget enforcement gap**: ADR-035 specifically recommends a custom `pre_tool_call` hook to enforce budget caps with real-time cost tracking. The current `approvals.mode: manual` is less granular — it blocks all tool calls rather than selectively blocking LLM calls when the budget is exceeded.

3. **Cutover already complete**: Shadow mode (where old bot.py and Hermes run in parallel) is no longer active. The old bot service is stopped. There is no rollback path to the old stack without redeploying.

### Moderate Observations

1. The local `hermes-config/config.yaml` is stale — it doesn't reflect the running VPS state. Phase 6 updates should sync this.

2. The `.env` file still has `LLM_MODEL=gpt-5.5` referencing the old stack's primary model — this is unused by Hermes but may cause confusion.

---

## 10. Exact Commands Executed

```bash
# 1. Read VPS Hermes config
ssh guinevere-vps "cat /home/guinevere/.hermes/config.yaml"

# 2. Check gateway state
ssh guinevere-vps "cat /home/guinevere/.hermes/gateway_state.json"

# 3. Check Hermes version and doctor report
ssh guinevere-vps "cd /home/guinevere/code/guinevere && source .venv/bin/activate && hermes --version && hermes doctor"

# 4. Security scan
ssh guinevere-vps "cd /home/guinevere/code/guinevere && source .venv/bin/activate && hermes security"

# 5. 9Router model list
ssh guinevere-vps "curl -s http://localhost:20128/v1/models > /tmp/models.json && python3 /tmp/list_models.py"

# 6. Service status
ssh guinevere-vps "systemctl list-units --type=service --state=running | grep -E 'guinevere|discord|hermes'"

# 7. Read old .env for comparison
ssh guinevere-vps "grep -v '^#' /home/guinevere/.hermes/.env | grep LLM"
```

---

## 11. Verdict

**Phase 6 LLM Routing state: ⚠️ PARTIALLY COMPLETE — requires corrective action before Phase 6 can be marked done.**

### What's Working (✅)
- [x] 9Router proxy is running and accessible at `http://localhost:20128/v1`
- [x] Hermes gateway is connected to Discord with `ds/deepseek-v4-flash`
- [x] `NINEROUTER_API_KEY` is configured in `.env`
- [x] Budget limits are set ($30/month, 80% alert, 100% block)
- [x] Consent gate hook and DNR filter hook are active
- [x] Auth overlay plugin and persona plugin are loaded
- [x] No HIGH/CRITICAL security vulnerabilities

### What Needs Fixing (❌)
1. **Set primary model to `cx/gpt-5.5`** per ADR-035 specification (or document why `ds/deepseek-v4-flash` is the intentional primary)
2. **Configure fallback** — either add `cx/gpt-5.5` as fallback (if deepseek is primary) or `ds/deepseek-v4-flash` as fallback (if gpt-5.5 is primary)
3. **Fix provider naming** — `hermes doctor` flags the vendor-prefixed slug with `ninerouter` provider as incorrect. Options: change to `provider: openrouter` or drop the `ds/` prefix
4. **Add `credential_pool_strategies`** for key rotation readiness
5. **Sync local `hermes-config/config.yaml`** to match the running VPS config
6. **Clean up old `.env` LLM vars** (`LLM_MODEL=gpt-5.5`, `LLM_FALLBACK_MODEL=deepseek-v4-flash`) that are no longer consumed by Hermes
