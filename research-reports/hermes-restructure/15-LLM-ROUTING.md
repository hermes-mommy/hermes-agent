# Report 15: LLM Routing — Guinevere to Hermes Migration

**Date:** 2026-06-04
**Scope:** LLM routing, model management, cost tracking, and budget enforcement migration analysis
**Status:** Research complete, awaiting planner gate
**Cross-references:** Report 13 (Hooks/Plugins), Report 14 (Safety Mapping), Report 16 (Security Posture)

---

## Executive Summary

Guinevere currently routes LLM requests through 9Router at `localhost:20128` with a GPT-5.5 primary and DeepSeek V4 Flash fallback, tracking costs via a custom `cost_tracker.py` with a $30/month hard cap. Hermes provides native model management, custom provider support, auth pooling, and an `insights` command for cost visibility — but lacks budget enforcement. Migration requires configuring Hermes to use 9Router as a custom OpenAI-compatible provider, implementing fallback logic that Hermes does not natively support, and bridging the budget enforcement gap.

**Key finding:** Hermes can use 9Router as a custom provider with minimal config. Fallback chaining requires custom work. Budget enforcement is a gap that needs external implementation.

---

## 1. Current Guinevere LLM Architecture

### 1.1 Routing Stack

```
User Message
     │
     ▼
session_adapter.py
     │
     │  llm_config = {
     │    "provider": "9router",
     │    "base_url": "http://localhost:20128",
     │    "model": "gpt-5.5",
     │    "fallback_model": "deepseek-v4-flash"
     │  }
     │
     ▼
Hermes AIAgent (wraps 9Router)
     │
     ▼
9Router (localhost:20128)
     ├── Primary: GPT-5.5
     ├── Fallback: DeepSeek V4 Flash
     └── Auth: Single API key
     │
     ▼
cost_tracker.py
     ├── input_tokens (per request)
     ├── output_tokens (per request)
     ├── estimated_cost_usd (computed)
     └── Budget cap: $30/month (hard stop at limit)
```

### 1.2 Key Files

| File | Role | Key Details |
|---|---|---|
| `session_adapter.py` | Orchestrator | Hardcoded 9Router config at `localhost:20128` |
| `llm_router.py` | Model selection | GPT-5.5 primary, DeepSeek V4 Flash fallback |
| `cost_tracker.py` | Cost analytics | Token counting, cost estimation, budget enforcement |
| Hermes AIAgent | LLM wrapper | Wraps 9Router as the LLM provider |

### 1.3 Current Configuration (Pseudocode)

```python
# session_adapter.py — current hardcoded config
LLM_CONFIG = {
    "base_url": "http://localhost:20128/v1",
    "api_key": os.environ.get("NINEROUTER_API_KEY"),
    "model": "gpt-5.5",
    "fallback_model": "deepseek-v4-flash",
    "max_tokens": 4096,
    "temperature": 0.7,
}

# llm_router.py — fallback logic
class LLMRouter:
    def route(self, messages):
        try:
            return self.call_model("gpt-5.5", messages)
        except (TimeoutError, RateLimitError, ConnectionError):
            logger.warning("Primary model failed, falling back to DeepSeek V4")
            return self.call_model("deepseek-v4-flash", messages)

# cost_tracker.py — budget enforcement
class CostTracker:
    MONTHLY_BUDGET_USD = 30.00

    def track(self, input_tokens, output_tokens, model):
        cost = self.estimate(input_tokens, output_tokens, model)
        if self.monthly_total + cost > self.MONTHLY_BUDGET_USD:
            raise BudgetExceededError(f"Monthly budget of ${self.MONTHLY_BUDGET_USD} exceeded")
        self.monthly_total += cost
```

---

## 2. Hermes LLM Capabilities

### 2.1 Native Model Management

```
$ hermes model list
  (lists available models from configured providers)

$ hermes model set gpt-5.5
  (sets active model)

$ hermes model show
  gpt-5.5 (active)
  Provider: custom (http://localhost:20128/v1)
  Context: 128K tokens
  Max output: 4096 tokens
```

### 2.2 Custom Provider Configuration

Hermes supports any OpenAI-compatible API endpoint as a custom provider:

```yaml
# config.yaml
llm:
  model: gpt-5.5
  base_url: http://localhost:20128/v1
  api_key: ${NINEROUTER_API_KEY}
  provider: custom
```

### 2.3 CLI Commands

| Command | Description | Guinevere Relevance |
|---|---|---|
| `hermes model set <model>` | Set active model | Replace `llm_router.py` model selection |
| `hermes model list` | List available models | Discover models from 9Router |
| `hermes model show` | Show current model details | Debug current routing |
| `hermes fallback` | Configure fallback model | Replace `llm_router.py` fallback logic |
| `hermes auth login` | Authenticate to provider | Replace hardcoded API key |
| `hermes auth logout` | Remove provider auth | Session cleanup |
| `hermes secrets set` | Store encrypted secrets | Replace env-var API key storage |
| `hermes secrets list` | List stored secrets | Audit credential storage |
| `hermes insights` | View usage and cost insights | Replace `cost_tracker.py` readout |

### 2.4 Auth Pooling

Hermes supports multiple API keys per provider, rotating or pooling:

```
$ hermes auth login --provider custom --key sk-xxx1
$ hermes auth login --provider custom --key sk-xxx2
$ hermes auth list
  custom: 2 keys configured (pool mode)
```

This is a superset of Guinevere's current single-key approach.

### 2.5 Secrets Encryption

```
$ hermes secrets set NINEROUTER_API_KEY "sk-..." 
  (encrypted at rest)

$ hermes secrets list
  NINEROUTER_API_KEY  (encrypted)  last_rotated: 2026-06-01
```

---

## 3. Migration Path

### 3.1 Phase 1: Configure Hermes for 9Router

**Step 1: Set custom provider**

```bash
hermes model set gpt-5.5
hermes config set llm.base_url http://localhost:20128/v1
hermes config set llm.provider custom
```

**Step 2: Store API key securely**

```bash
hermes secrets set NINEROUTER_API_KEY "$NINEROUTER_API_KEY"
hermes config set llm.api_key "${NINEROUTER_API_KEY}"
```

**Step 3: Verify connectivity**

```bash
hermes model show
# Expected: gpt-5.5 via custom provider at localhost:20128
```

### 3.2 Phase 2: Implement Fallback Chain

Hermes has a `fallback` command but its behavior for custom providers is undocumented. The current Guinevere fallback chain (GPT-5.5 → DeepSeek V4 Flash) must be replicated.

**Option A: Hermes native fallback (if supported with custom providers)**

```yaml
llm:
  model: gpt-5.5
  fallback:
    - model: deepseek-v4-flash
      on_error: [timeout, rate_limit, connection_error]
```

**Option B: Custom plugin-based fallback (if Hermes fallback doesn't support custom providers)**

```python
# Plugin method in GuinevereSafetyPlugin or dedicated RoutingPlugin
class LLMFallbackPlugin(BasePlugin):
    PRIMARY_MODEL = "gpt-5.5"
    FALLBACK_MODEL = "deepseek-v4-flash"
    FALLBACK_ERRORS = (TimeoutError, ConnectionError, RateLimitError)

    def on_message(self, message, context):
        context.set("model", self.PRIMARY_MODEL)
        context.set("fallback_used", False)

    def on_error(self, error, context):
        if isinstance(error, self.FALLBACK_ERRORS) and not context.get("fallback_used"):
            context.set("model", self.FALLBACK_MODEL)
            context.set("fallback_used", True)
            context.set("retry", True)  # Signal to retry with new model
```

**Recommended:** Test Option A first. If unsupported, use Option B. Fallback test scenarios:

| Failure Mode | Expected Behavior |
|---|---|
| GPT-5.5 timeout (30s) | Switch to DeepSeek V4 Flash, retry |
| GPT-5.5 rate limit (429) | Switch to DeepSeek V4 Flash, retry |
| GPT-5.5 connection refused | Switch to DeepSeek V4 Flash, retry |
| 9Router entirely down | Both models fail; escalate to operator |
| DeepSeek V4 also fails | Halt all LLM calls, notify operator |

### 3.3 Phase 3: Cost Tracking Migration

| Capability | Current (`cost_tracker.py`) | Hermes Equivalent | Gap |
|---|---|---|---|
| Token counting | Per-request input/output tokens | `hermes insights` (aggregated) | Hermes insights is read-only, no per-request visibility |
| Cost estimation | `estimated_cost_usd` computed per model pricing | `hermes insights` shows cost | May use different pricing model |
| Budget enforcement | $30/month hard cap, raises `BudgetExceededError` | **NONE** — Hermes has no budget enforcement | Critical gap |
| Cost history | Custom storage | `hermes insights` (time-series, detailed unknown) | Format compatibility unknown |
| Per-model breakdown | Tracked per model | `hermes insights` likely shows per-model | Need to verify |

**Budget enforcement strategy:**

Since Hermes lacks native budget enforcement, implement via `pre_tool_call` hook or plugin:

```python
# guinevere/hooks/budget_check.py
import sys, json

MONTHLY_BUDGET_USD = 30.00

def main():
    request = json.loads(sys.stdin.read())
    estimated_cost = request.get("estimated_cost", 0)
    current_monthly = get_current_monthly_spend()  # Query cost_tracker or Hermes insights

    if current_monthly + estimated_cost > MONTHLY_BUDGET_USD:
        print(json.dumps({
            "action": "block",
            "reason": f"budget_exceeded: ${current_monthly:.2f} + ${estimated_cost:.4f} > ${MONTHLY_BUDGET_USD}",
            "metadata": {"current_spend": current_monthly, "estimated_cost": estimated_cost}
        }))
        sys.exit(1)  # BLOCK

    print(json.dumps({"action": "pass"}))
    sys.exit(0)
```

```yaml
hooks:
  pre_tool_call:
    - command: "python -m guinevere.hooks.budget_check"
      on_failure: block
```

### 3.4 Phase 4: Auth Pooling Migration

| Aspect | Current | Hermes | Migration |
|---|---|---|---|
| Keys per provider | 1 (single 9Router key) | Multiple (auth pooling) | `hermes auth login --provider custom --key <key>` per key |
| Key rotation | Manual env var change | `hermes secrets set` + `hermes auth` | Automate rotation via hook |
| Key storage | Environment variable (.env) | Encrypted (`hermes secrets`) | Migrate to encrypted storage |

**Auth pooling adds resilience:** If one 9Router key hits rate limits, Hermes can rotate to the next key in the pool. Current Guinevere has no such capability.

---

## 4. Gap Analysis

### 4.1 What Hermes Provides

| Capability | Quality | Notes |
|---|---|---|
| Custom provider support | Good | Any OpenAI-compatible endpoint; 9Router qualifies |
| Model management | Good | Set, list, show commands; clean CLI |
| Auth pooling | Good | Multiple keys per provider, rotation |
| Secret encryption | Good | Encrypted at rest via `hermes secrets` |
| Cost visibility | Adequate | `hermes insights` gives aggregate data |
| Configuration persistence | Good | `config.yaml` with env var interpolation |

### 4.2 What Hermes Lacks

| Gap | Severity | Impact | Mitigation |
|---|---|---|---|
| No budget enforcement | **High** | No automatic $30/mo cap; risk of cost overrun | Implement via `pre_tool_call` hook (Section 3.3) |
| Undocumented fallback for custom providers | **High** | May need custom plugin if native fallback doesn't work | Custom plugin fallback (Section 3.2, Option B) |
| Limited per-request cost visibility | Medium | Can't track individual request costs in real-time | Keep `cost_tracker.py` as external service |
| No multi-model routing strategies | Medium | Only primary/fallback; no round-robin, weighted, or latency-based | Acceptable for 2-model setup |
| `insights` format is undocumented | Low | Unknown if it exposes programmatic cost data | Test `hermes insights --json` (if supported) |

### 4.3 What Guinevere Must Keep External

| Component | Reason to Keep |
|---|---|
| `cost_tracker.py` | Hermes has no budget enforcement; this provides the hard cap |
| Budget state (monthly total) | Must persist across Hermes restarts; file-based or PostgreSQL |
| Fallback state machine | If Hermes native fallback doesn't work with 9Router |

---

## 5. Configuration Specification

### 5.1 Target Hermes Config

```yaml
# config.yaml — Guinevere LLM section
llm:
  model: gpt-5.5
  base_url: http://localhost:20128/v1
  api_key: ${NINEROUTER_API_KEY}
  provider: custom
  max_tokens: 4096
  temperature: 0.7
  timeout: 30s

  # Fallback configuration (if supported by Hermes for custom providers)
  fallback:
    enabled: true
    models:
      - deepseek-v4-flash
    on_errors:
      - timeout
      - rate_limit
      - connection_error
    max_retries: 1

# Auth pooling (multiple 9Router keys)
auth:
  providers:
    custom:
      pool_mode: round_robin
      keys:
        - ${NINEROUTER_KEY_1}
        - ${NINEROUTER_KEY_2}  # optional, for redundancy

# Hooks for budget enforcement
hooks:
  pre_tool_call:
    - command: "python -m guinevere.hooks.budget_check"
      on_failure: block
```

### 5.2 Environment Variables

```bash
# .env (migrated to hermes secrets)
NINEROUTER_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
NINEROUTER_KEY_1=sk-xxxxxxxxxxxxxxxxxxxxxxxx
NINEROUTER_KEY_2=sk-yyyyyyyyyyyyyyyyyyyyyyyy  # optional
```

Migrate to encrypted storage:
```bash
hermes secrets set NINEROUTER_API_KEY "sk-..."
hermes secrets set NINEROUTER_KEY_1 "sk-..."
hermes secrets set NINEROUTER_KEY_2 "sk-..."
```

---

## 6. Fallback Chain Specification

### 6.1 Current Chain

```
Request → GPT-5.5 (primary)
              │
              ├── Success → Response
              │
              └── Failure (timeout/rate-limit/connection)
                      │
                      └── DeepSeek V4 Flash (fallback)
                              │
                              ├── Success → Response (with fallback flag)
                              │
                              └── Failure → Escalate to operator
```

### 6.2 Target Chain (Hermes-Integrated)

```
Request → [budget_check hook] → GPT-5.5 (primary via 9Router)
                                      │
                                      ├── Success → [cost_tracker] → Response
                                      │
                                      └── Failure
                                              │
                                              └── [pre_tool_call hook: fallback_switch]
                                                      │
                                                      └── DeepSeek V4 Flash (via 9Router)
                                                              │
                                                              ├── Success → [cost_tracker] → Response
                                                              │
                                                              └── Failure → [on_error hook: escalate]
```

### 6.3 Fallback Error Mapping

| 9Router Error | HTTP Status | Fallback? | Notes |
|---|---|---|---|
| Model timeout | 504 | Yes | Switch to DeepSeek V4 |
| Rate limit | 429 | Yes | Switch to DeepSeek V4; could also rotate auth key |
| Connection refused | — | Yes | 9Router is down; DeepSeek may also fail |
| Invalid API key | 401 | No | Auth error; escalate immediately |
| Model not found | 404 | No | Config error; escalate immediately |
| Content filtered | 400 | No | Safety filter; respect the block |

---

## 7. Recommendations

### 7.1 Immediate Actions

1. **Test Hermes custom provider with 9Router:** Configure `llm.base_url` to `http://localhost:20128/v1` and verify connectivity with `hermes model show`
2. **Test Hermes fallback with custom provider:** Attempt to configure `llm.fallback` and verify it triggers on simulated failures
3. **Evaluate `hermes insights` output:** Determine if it exposes programmatic cost data and budget thresholds
4. **Implement budget enforcement hook:** If `insights` is insufficient, implement budget_check hook immediately

### 7.2 Short-term Actions

5. **Migrate API keys to `hermes secrets`:** Replace env-var storage with encrypted secret storage
6. **Configure auth pooling:** Add secondary 9Router key if available for redundancy
7. **Port cost_tracker.py state:** Ensure monthly budget state persists across restarts

### 7.3 Long-term Actions

8. **Automate key rotation:** Create hook that rotates API keys on a schedule
9. **Build cost dashboard:** Expose `hermes insights` data to monitoring system (Prometheus/Grafana)
10. **Hard cap circuit breaker:** If budget is at 90%, reduce max_tokens to stretch remaining budget

### 7.4 Acceptance Criteria

- [ ] Hermes routes LLM calls through 9Router at `localhost:20128`
- [ ] GPT-5.5 is primary model
- [ ] DeepSeek V4 Flash is used on GPT-5.5 failure (timeout, rate-limit, connection)
- [ ] Budget enforcement blocks requests at $30/month
- [ ] API keys stored encrypted via `hermes secrets`
- [ ] Auth pooling functional if multiple keys are configured
- [ ] Cost tracking continues to work (tokens, estimated cost)
- [ ] Fallback events are logged and auditable

---

## 8. Footnotes

- 9Router must remain running at `localhost:20128` throughout migration
- See Report 14 (Safety Mapping) for pre-LLM safety hooks that run before model routing
- See Report 16 (Security Posture) for API key management and secret scanning
- Budget enforcement is a non-negotiable requirement (see PROGRESS.md: $30/month cap)