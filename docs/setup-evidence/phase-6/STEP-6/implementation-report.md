# Phase 6 Step 6 — Fallback Chain Verification & Configuration

**Date:** 2026-06-06
**Status:** COMPLETE
**Evidence root:** `docs/setup-evidence/phase-6/STEP-6/`
**Scaffold source:** `docs/setup-evidence/phase-6/plan.md` §10 Step 6
**Research inputs:** `research-reports/phase-6-execution/01-llm-state.md`, `03-fallback-verify.md`

---

## 1. Summary

| Item | Status |
|---|---|
| VPS 9Router `/v1/models` HTTP 200 | ✅ PASS |
| Primary model `ds/deepseek-v4-flash` via provider `ninerouter` at `http://localhost:20128/v1` | ✅ Confirmed |
| `guinevere` combo model exists on VPS 9Router | ✅ Confirmed |
| `cx/gpt-5.5` model exists on VPS 9Router (degraded — codex OAuth expired) | ✅ Confirmed |
| `ninerouter/balance` model exists | ❌ NOT FOUND — confirmed absent from model list |
| Hermes v0.15.2 `hermes fallback` CLI | ✅ Available (but `add` is interactive only) |
| Backup before config edit | ✅ `/home/guinevere/.hermes/config.yaml.phase6-step6-bak` |
| Fallback chain configured (2 entries) | ✅ `cx/gpt-5.5` (1st), `guinevere` (2nd) |
| YAML valid / `hermes config check` pass | ✅ |
| Budget/consent/DNR hooks preserved | ✅ |
| No direct provider URLs introduced | ✅ All via `http://localhost:20128/v1` |
| No `ninerouter/balance` used | ✅ Correctly excluded |
| Hermes-gateway NOT restarted | ✅ Per instructions |

---

## 2. VPS 9Router Model Verification

### Command
```bash
ssh guinevere-vps "curl -s http://localhost:20128/v1/models"
```

### Result
HTTP 200. Key models relevant to fallback chain:

| Model ID | Provider | Status |
|---|---|---|
| `ds/deepseek-v4-flash` | ds (DeepSeek) | ✅ **Primary** — present |
| `cx/gpt-5.5` | cx (Codex) | ✅ Present — degraded (OAuth expired) |
| `guinevere` | combo | ✅ Present — operational VPS combo |
| `ninerouter/balance` | — | ❌ **ABSENT** — not in model list |

Model IDs explicitly checked and confirmed absent: `ninerouter/balance` does not exist as any model entry. The `ninerouter` string is a **provider name** in the Hermes config, not a model namespace.

---

## 3. VPS Hermes Config — Pre-Edit State

File: `/home/guinevere/.hermes/config.yaml`

Key pre-edit values:

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

fallback_providers: []    # ← EMPTY — no fallback configured

# Budget/consent/DNR hooks:
hooks:
  post_tool_call:
    - command: python3 ~/.hermes/hooks/dnr_filter.py
      event: post_tool_call
      on_failure: block
      priority: 70
      timeout_ms: 50
  pre_tool_call:
    - command: python3 ~/.hermes/hooks/budget_check.py
      event: pre_tool_call
      on_failure: block
      priority: 100
      timeout_ms: 500
    - command: python3 ~/.hermes/hooks/consent_gate.py
      event: pre_tool_call
      on_failure: block
      priority: 90
      timeout_ms: 200

budget:
  monthly_limit: 30.0
  alert_threshold: 0.8
  block_threshold: 1.0
```

---

## 4. Fallback Configuration Mechanism

### Hermes CLI
- `hermes fallback` subcommand is **available** on VPS v0.15.2
- `hermes fallback list` shows the current chain
- `hermes fallback add` is **interactive-only** (no non-interactive flags) — not usable via SSH scripting

### YAML Config Format (used)
Per upstream Hermes documentation at `https://hermes-agent.nousresearch.com/docs/user-guide/features/fallback-providers`, the `fallback_providers` YAML list supports:
```yaml
fallback_providers:
  - provider: custom
    model: <model-id>
    base_url: <url>
    key_env: <ENV_VAR>
```

Since our 9Router endpoint is a custom OpenAI-compatible endpoint (not a built-in Hermes provider), the `provider: custom` type is the correct choice.

---

## 5. Config Edit Applied

### Backup
```bash
ssh guinevere-vps "cp /home/guinevere/.hermes/config.yaml /home/guinevere/.hermes/config.yaml.phase6-step6-bak"
```

### Change
Replaced `fallback_providers: []` with two fallback entries:

```yaml
fallback_providers:
  - provider: custom
    model: cx/gpt-5.5
    base_url: http://localhost:20128/v1
    key_env: NINEROUTER_API_KEY
  - provider: custom
    model: guinevere
    base_url: http://localhost:20128/v1
    key_env: NINEROUTER_API_KEY
```

### Design Decisions

| Decision | Rationale |
|---|---|
| **First fallback: `cx/gpt-5.5`** | Model exists on 9Router; codex OAuth is expired making it degraded but Hermes fallback will pass through to second entry on 404/401 |
| **Second fallback: `guinevere`** | Operational VPS combo (DeepSeek via opencode-go → GPT-5.5 via cockpit); verified working per P1 migration evidence |
| **`provider: custom`** | 9Router is not a built-in Hermes provider; `custom` allows `base_url` + `key_env` |
| **`base_url: http://localhost:20128/v1`** | All traffic stays through 9Router — no direct provider endpoints |
| **`key_env: NINEROUTER_API_KEY`** | Same env var already used by primary; already configured in `.env` |
| **No `ninerouter/balance`** | Confirmed absent from `/v1/models`; using it would break startup per the hard rejection criterion |

---

## 6. Post-Edit Validation Results

### 6.1 YAML Parse Check
```bash
ssh guinevere-vps "python3 -c \"import yaml; yaml.safe_load(open('/home/guinevere/.hermes/config.yaml')); print('YAML_VALID')\""
```
→ **YAML_VALID**

### 6.2 Hermes Config Check
```bash
ssh guinevere-vps "cd /home/guinevere/code/guinevere && source .venv/bin/activate && hermes config check"
```
→ **Config version 24 ✓** — no errors or warnings

### 6.3 Hermes Fallback List
```bash
ssh guinevere-vps "cd /home/guinevere/code/guinevere && source .venv/bin/activate && hermes fallback list"
```
Output:
```
  Primary:   ds/deepseek-v4-flash  (via ninerouter)

  Fallback chain (2 entries):
    1. cx/gpt-5.5  (via custom)  [http://localhost:20128/v1]
    2. guinevere  (via custom)  [http://localhost:20128/v1]

  Tried in order when the primary fails (rate-limit, 5xx, connection errors).
```

### 6.4 Budget/Consent/DNR Hook Preservation
```bash
ssh guinevere-vps "grep -E 'hooks:|budget_check|consent_gate|dnr_filter|budget:|monthly_limit' /home/guinevere/.hermes/config.yaml"
```
→ All hooks and budget settings confirmed intact:
- `dnr_filter.py` (post_tool_call, priority 70)
- `budget_check.py` (pre_tool_call, priority 100)
- `consent_gate.py` (pre_tool_call, priority 90)
- `monthly_limit: 30.0`

### 6.5 Forbidden Patterns Check
- No `ninerouter/balance` in config: ✅
- No direct OpenAI/OpenRouter provider endpoints: ✅ (all `http://localhost:20128/v1`)
- No direct provider URLs: ✅

---

## 7. Current Fallback Chain

```
Level 0 (PRIMARY): ds/deepseek-v4-flash  → provider: ninerouter → http://localhost:20128/v1
Level 1 (FALLBACK): cx/gpt-5.5           → provider: custom    → http://localhost:20128/v1  [DEGRADED — codex OAuth expired]
Level 2 (FALLBACK): guinevere            → provider: custom    → http://localhost:20128/v1  [OPERATIONAL — VPS combo]
```

### Trigger behavior
Hermes activates fallback per-turn when the primary fails with:
- HTTP 429 (rate limit) — after retries
- HTTP 500/502/503 — after retries
- HTTP 401/403/404 — immediately
- Invalid/malformed responses

When Level 1 (`cx/gpt-5.5`) returns 404 (expired codex), Hermes proceeds immediately to Level 2 (`guinevere`).

---

## 8. Decision on `ninerouter/balance`

**Verdict: EXCLUDED — NOT CONFIGURED.**

Evidence:
- `ninerouter/balance` does **not** appear in the VPS `/v1/models` response
- Research report `03-fallback-verify.md` §5.1 confirms the local combo is named `balance` (not `ninerouter/balance`), and the VPS combo is named `guinevere` (not `balance`)
- The `ninerouter` prefix is a Hermes **provider name**, not a 9Router model namespace
- Using `ninerouter/balance` would cause Hermes startup failure (model not found on 9Router)

The user's original requirement referenced `ninerouter/balance` based on an invalid assumption. The correct VPS fallback is the `guinevere` combo.

---

## 9. Caveats

1. **`cx/gpt-5.5` is degraded**: Codex OAuth tokens expired 2026-05-15. Hermes will skip to Level 2 (`guinevere`) on 404. This is safe and expected — the entry is present for when codex tokens are refreshed.

2. **No restart performed**: `hermes-gateway` was not restarted. The fallback config change will take effect on next restart (Step 8).

3. **YAML edit only**: Could not use `hermes fallback add` CLI because it is interactive-only. Direct YAML edit was the correct approach per Hermes documentation which states: "Changes persist under the top-level `fallback_providers:` list in `config.yaml`."

4. **Local `hermes-config/config.yaml` not synced**: The local config is a different schema (older template style) and is not used at runtime. VPS config is the source of truth. If needed, Step 6 of the plan allows syncing this.

5. **Primary remains DeepSeek**: ADR-035 specifies `cx/gpt-5.5` as primary, but user hard constraint overrides to keep `ds/deepseek-v4-flash`. The fallback chain reflects this intent.

---

## 10. Rollback

To revert to pre-edit state:
```bash
ssh guinevere-vps "cp /home/guinevere/.hermes/config.yaml.phase6-step6-bak /home/guinevere/.hermes/config.yaml"
```
Then restart `hermes-gateway` (Step 8).

---

## 11. Footer

- **Task**: Phase 6 Step 6 — Fallback chain verification and configuration
- **Date**: 2026-06-06
- **Executor**: Guinevere (sisyphus-junior)
- **Evidence path**: `docs/setup-evidence/phase-6/STEP-6/implementation-report.md`
- **Verification**: `/v1/models` HTTP 200, YAML parse, `hermes config check`, `hermes fallback list`, hook preservation, forbidden pattern scan
- **Next action**: Proceed to Step 7 (Prometheus metrics) and Step 8 (restart hermes-gateway)
