# Phase 6: LLM Routing & Budget — Detailed Procedure

## Overview

| Property | Value |
|---|---|
| **Duration** | 1 day |
| **Risk Level** | LOW |
| **Dependencies** | Phase 2 (BLOCKING), Phase 1 (NON-BLOCKING) |
| **Blocks** | Phase 7 (BLOCKING) |
| **Gate** | LLM routing functional. GPT-5.5 → DeepSeek V4 Flash fallback works. Budget enforced at $30/mo |
| **Rollback Time** | < 2 minutes (reset model + disable fallback + disable budget hook) |

### Goal Statement

Configure Hermes to use 9Router at `localhost:20128` as a custom LLM provider. Set up GPT-5.5 (primary) → DeepSeek V4 Flash (fallback) chain. Deploy budget enforcement hook: alert at 80% ($24), block at 100% ($30). Verify streaming compatibility with 9Router. Run 100-prompt compatibility test before production cutover.

### Pre-Conditions

- [ ] Phase 2 cutover complete — Hermes gateway is primary
- [ ] 9Router healthy at `localhost:20128`
- [ ] `NINEROUTER_API_KEY` available (SOPS-decrypted from `.env.hermes`)
- [ ] Hermes gateway running and connected to Discord

---

## Step-by-Step Procedure

### Step 6.1: Configure 9Router as Custom Provider

**Command:**
```bash
# Configure Hermes to use 9Router as custom provider
hermes config set model.provider "custom"
hermes config set model.model "gpt-5.5"
hermes config set model.base_url "http://localhost:20128/v1"
hermes config set model.api_key "${NINEROUTER_API_KEY}"
hermes config set model.max_tokens 16384
hermes config set model.temperature 0.7
hermes config set model.streaming true
```

**Expected output:**
```
model.provider = "custom"
model.model = "gpt-5.5"
model.base_url = "http://localhost:20128/v1"
```

**Verification:**
```bash
hermes model show
# Expected: provider=custom, model=gpt-5.5, base_url=http://localhost:20128/v1
```

**Troubleshooting:**
- If `hermes model show` shows wrong values → verify `HERMES_CONFIG_PATH` points to correct config.yaml
- If 9Router connection fails → verify `curl http://localhost:20128/v1/models` returns JSON
- If API key rejected → verify `NINEROUTER_API_KEY` is SOPS-decrypted correctly

### Step 6.2: Configure Fallback Chain

**Command:**
```bash
hermes config set fallback.enabled true
hermes config set fallback.models '["deepseek-v4-flash"]'
hermes config set fallback.strategy "sequential"
```

**Expected fallback behavior:**
1. Hermes sends request to GPT-5.5 via 9Router
2. If GPT-5.5 fails (HTTP 5xx, timeout, rate limit) → auto-fallback to DeepSeek V4 Flash via 9Router
3. If both fail → error returned to user (no response)

**Verification:**
```bash
hermes config get fallback
# Expected: enabled=true, models=["deepseek-v4-flash"], strategy=sequential
```

**Troubleshooting:**
- If fallback doesn't engage → check 9Router routing. Fallback is sequential (try primary, then secondary).
- If both models fail → 9Router may be down. Check `curl http://localhost:20128/health`.

### Step 6.3: Configure Budget Enforcement ($30/mo)

**Command:**
```bash
hermes config set budget.monthly_limit 30.00
hermes config set budget.alert_threshold 0.80  # Alert at $24
hermes config set budget.block_threshold 1.00  # Block at $30
hermes config set budget.currency "USD"
```

**Budget enforcement behavior:**
| Spend | Action | Description |
|---|---|---|
| < $24 (80%) | Normal operation | No alerts |
| $24 (80%) | Discord alert | Notification to `#guinevere-alerts`: "Budget at 80% ($24/$30)" |
| $24-$27 (80-90%) | Continued alerts | Every LLM call logs cost |
| $27-$30 (90-100%) | Escalated alerts | Warning: budget cap approaching |
| $30 (100%) | BLOCK | All LLM calls blocked: "Budget cap reached: $30.00/$30.00" |
| > $30 (101%+) | BLOCK | Already capped — no bypass |

**Verification:**
```bash
hermes config get budget
# Expected: monthly_limit=30.00, alert_threshold=0.80, block_threshold=1.00
```

**Troubleshooting:**
- If budget blocks prematurely (< $30) → check cumulative cost calculation. Verify cost tracking is accurate.
- If budget doesn't block at $30 → check `block_threshold` config. Must be 1.00 (100%).
- If cost tracking diverges from cost_tracker.py → compare `hermes insights cost` vs PostgreSQL cost data. Investigate > 10% discrepancy.

### Step 6.4: 100-Prompt Compatibility Test

**Command:**
```bash
cd /home/guinevere/code/guinevere
source .venv/bin/activate
python scripts/test_100_prompts.py
```

**Test script outline (`scripts/test_100_prompts.py`):**
```python
"""100-prompt 9Router compatibility test for Hermes.
Tests: routing, streaming, fallback, error handling, budget tracking.
"""
import subprocess
import json

PROMPTS = [
    "Hello", "What is 2+2?", "Write a haiku about coding",
    # ... 100 diverse prompts covering:
    # - Short greetings (10)
    # - Technical questions (20)
    # - Emotional/personal (10)
    # - Memory recall (10)
    # - Long-form engineering (20)
    # - Bilingual ID/EN (10)
    # - Edge cases (10): empty, very long, unicode, special chars
    # - Safety-triggering (10): HARD STOP, distress, Y6-adjacent
]

results = {"passed": 0, "failed": 0, "fallback_used": 0, "errors": []}

for i, prompt in enumerate(PROMPTS):
    try:
        result = subprocess.run(
            ["hermes", "model", "test", "--prompt", prompt],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            results["passed"] += 1
            if "fallback" in result.stderr.lower():
                results["fallback_used"] += 1
        else:
            results["failed"] += 1
            results["errors"].append({"prompt": prompt[:50], "error": result.stderr[:200]})
    except subprocess.TimeoutExpired:
        results["failed"] += 1
        results["errors"].append({"prompt": prompt[:50], "error": "timeout"})

print(f"Results: {results['passed']}/100 passed, {results['failed']} failed")
print(f"Fallback used: {results['fallback_used']} times")
if results["failed"] > 0:
    print("FAILURES:")
    for e in results["errors"]:
        print(f"  - {e['prompt']}: {e['error']}")
```

**Expected output:**
```
Results: 100/100 passed, 0 failed
Fallback used: 0 times (or ≤ 2 if network hiccup)
```

### Step 6.5: Test Streaming Compatibility

**Command:**
```bash
hermes model test --prompt "Explain async/await in Python with code examples" --stream
```

**Expected output:**
```
Progressive streaming response with ~1.2s edit intervals.
First token visible within 1-2 seconds.
Full response complete within 15-30 seconds.
```

### Step 6.6: Deploy Budget Enforcement Hook

**Create `hooks/budget.py`:**
```python
#!/usr/bin/env python3
"""Budget enforcement hook — pre_tool_call lifecycle.
Checks cumulative monthly cost against budget cap.
Alerts at 80% ($24), blocks at 100% ($30).
"""

import sys
import json

BUDGET_MONTHLY_LIMIT = 30.00
ALERT_THRESHOLD = 0.80  # 80% = $24
BLOCK_THRESHOLD = 1.00  # 100% = $30


def check_budget(current_spend: float) -> dict:
    """Check current spend against budget thresholds."""
    ratio = current_spend / BUDGET_MONTHLY_LIMIT if BUDGET_MONTHLY_LIMIT > 0 else 0
    
    if ratio >= BLOCK_THRESHOLD:
        return {
            "action": "block",
            "reason": f"Budget cap reached: ${current_spend:.2f}/${BUDGET_MONTHLY_LIMIT:.2f}",
            "threshold": "100%",
            "ratio": ratio
        }
    elif ratio >= ALERT_THRESHOLD:
        return {
            "action": "warn",
            "reason": f"Budget alert: ${current_spend:.2f}/${BUDGET_MONTHLY_LIMIT:.2f} ({(ratio*100):.0f}%)",
            "threshold": "80%",
            "ratio": ratio,
            "alert": True
        }
    else:
        return {"action": "pass", "ratio": ratio}


if __name__ == "__main__":
    try:
        data = json.load(sys.stdin)
        
        # Get current spend from Hermes insights
        import subprocess
        cost_data = subprocess.run(
            ["hermes", "insights", "cost", "--since", "30d", "--format", "json"],
            capture_output=True, text=True
        )
        current_spend = float(json.loads(cost_data.stdout).get("total", 0))
        
        result = check_budget(current_spend)
        print(json.dumps(result))
        
        if result["action"] == "block":
            sys.exit(1)  # BLOCK
        elif result["action"] == "warn":
            sys.exit(2)  # WARN
        else:
            sys.exit(0)  # PASS
            
    except Exception as e:
        # Fail-open on hook error for budget (not safety-critical)
        print(json.dumps({"action": "pass", "note": f"budget hook error: {e}"}))
        sys.exit(0)
```

### Step 6.7: Test Conversation Commands

```bash
# Test LLM response through 9Router
hermes model test --prompt "Hello Guinevere, how are you today?"
# Expected: Y4 dominant tone response via GPT-5.5

# Test fallback (simulate GPT-5.5 failure)
# Temporarily stop 9Router routing for GPT-5.5
# Send message → expected: DeepSeek V4 Flash takes over
# Restore GPT-5.5 routing

# Test budget enforcement
# Set budget.monthly_limit to 0.01 (near-zero)
# Send message → expected: "Budget cap reached"
# Restore budget.monthly_limit to 30.00
```

---

## Safety Checkpoint

| # | Check | Command | Expected |
|---|---|---|---|
| P6-T1 | 9Router config correct | `hermes model show` | provider=custom, base_url=localhost:20128 |
| P6-T2 | 100-prompt compatibility | `python scripts/test_100_prompts.py` | 100/100 pass |
| P6-T3 | Fallback chain active | `hermes config get fallback` | enabled=true, sequential strategy |
| P6-T4 | Budget alert at 80% | Set spend to $24 → check alert | Discord notification sent |
| P6-T5 | Budget block at 100% | Set spend to $30 → check block | LLM calls blocked |
| P6-T6 | Streaming compatible | `hermes model test --stream` | Progressive edits visible |

---

## Config Changes

```yaml
model:
  provider: "custom"
  model: "gpt-5.5"
  base_url: "http://localhost:20128/v1"
  api_key: "${NINEROUTER_API_KEY}"
  max_tokens: 16384
  temperature: 0.7
  streaming: true

fallback:
  enabled: true
  models:
    - "deepseek-v4-flash"
  strategy: "sequential"

budget:
  monthly_limit: 30.00
  alert_threshold: 0.80    # Alert at $24
  block_threshold: 1.00    # Block at $30
  currency: "USD"
```

---

## File Changes

| File | Action | Description |
|---|---|---|
| `hooks/budget.py` | CREATE (~80 lines) | Budget enforcement hook |
| `config/hermes/config.yaml` | MODIFY (+20 lines) | Add model, fallback, budget sections |
| `plugins/guinevere_safety_plugin.py` | MODIFY (+10 lines) | Budget enforcement integration |
| `tests/llm/test_9router_compatibility.py` | CREATE (~150 lines) | 100-prompt compatibility suite |
| `scripts/test_100_prompts.py` | CREATE (~100 lines) | Compatibility test harness |

---

## Service Management

**Brief Hermes gateway restart for config reload (~30s).** Gateway stays up during model switch — no user-visible downtime.

| Service | Action |
|---|---|
| Hermes gateway | RESTART (or config reload) |
| 9Router | KEEP RUNNING — unchanged |
| All other services | KEEP RUNNING |

---

## Risk Register

| Risk ID | Description | Score | Mitigation |
|---|---|---|---|
| R-P6-01-001 | LLM calls fail (can't reach 9Router) | 6 MEDIUM | Pre-test 100 prompts; verify 9Router health |
| R-P6-02-001 | Budget blocks legitimate requests | 6 MEDIUM | Verify cost calculation accuracy |
| R-P6-03-001 | Budget doesn't block at cap | 4 LOW | Test with low budget threshold |
| R-P6-04-001 | Fallback doesn't engage | 4 LOW | Simulate primary failure, verify fallback |
| R-P6-05-001 | Cost tracking diverges from PostgreSQL | 6 MEDIUM | Compare `hermes insights` vs PostgreSQL data |

---

## Rollback Procedure

```bash
# === PHASE 6 ROLLBACK (< 2 minutes) ===
hermes model set --model default
hermes fallback set --model none
hermes config set budget.monthly_limit 0
hermes config set budget.alert_threshold 0
hermes config set budget.block_threshold 0
hermes gateway restart
# Verify: original LLM routing restored
```

---

## Test Commands

```bash
# 9Router custom provider config test
pytest tests/hermes/test_llm_routing.py::TestNineRouterConfig -v

# 100-prompt compatibility
pytest tests/hermes/test_llm_routing.py::TestCompatibility -v

# Fallback chain test
pytest tests/hermes/test_llm_routing.py::TestFallbackChain -v

# Streaming compatibility
pytest tests/hermes/test_llm_routing.py::TestStreamingCompat -v

# Budget enforcement hook tests
pytest tests/hermes/test_budget_hook.py -v

# Budget alert at 80%
pytest tests/hermes/test_budget_hook.py::TestBudgetAlert -v

# Budget block at 100%
pytest tests/hermes/test_budget_hook.py::TestBudgetBlock -v

# Budget thresholds: 80%, 90%, 100%, 101%
pytest tests/hermes/test_budget_hook.py::TestBudgetThresholds -v
```

---

## Test Conversation Commands

```bash
# Basic conversation test
hermes model test --prompt "Hello Guinevere, how are you?"

# Technical question (streaming)
hermes model test --prompt "Explain Python async generators with code examples" --stream

# Bilingual test
hermes model test --prompt "Mommy, bisa jelasin cara kerja Docker compose?"

# Safety test
hermes model test --prompt "What happens when someone says HARD STOP?"

# Memory recall test
hermes model test --prompt "What did we discuss about the migration yesterday?"

# Edge case: very long prompt
hermes model test --prompt "$(python -c 'print("Explain " * 500)')" --max-tokens 100
```

---

## Gate Criteria

| Criterion | Threshold | Measurement |
|---|---|---|
| LLM routing functional | GPT-5.5 via 9Router | `hermes model test` |
| 100/100 prompts route correctly | 100% pass rate | `scripts/test_100_prompts.py` |
| Fallback chain works | GPT-5.5 → DeepSeek V4 Flash | Simulate failure test |
| Budget enforced at $30/mo | Block at 100% | Budget threshold test |
| Alert at 80% ($24) | Discord notification | Budget alert test |
| Streaming works through 9Router | Progressive edits at ~1.2s | `--stream` flag test |
| 9Router unchanged | `localhost:20128` | `curl localhost:20128/health` |

---

## References

| Document | Relevance |
|---|---|
| `adr/ADR-035-hermes-migration.md` | §Phase 6 — LLM Routing, §Pillar 5: LLM = RETAIN 9Router |
| `adr/ADR-005-llm-router-failover-strategy.md` | 9Router only, no OpenRouter fallback |
| `adr/ADR-004-primary-llm-model-selection.md` | GPT-5.5 primary model selection |
| `research-reports/migration-plan/01-dependency-map.md` | §Phase 6 dependencies |
| `research-reports/migration-plan/03-rollback-procedures.md` | §11 — Phase 6 rollback |
| `research-reports/migration-plan/04-safety-checkpoints.md` | §8 — Phase 6 safety checkpoint |
| `research-reports/migration-plan/06-file-inventory.md` | §Phase 6 — File changes |
| `research-reports/migration-plan/07-test-suite.md` | §10 — Phase 6 test suite |
| `research-reports/migration-plan/08-service-sequence.md` | §Phase 6 — Service management |
| `research-reports/migration-plan/09-config-migration.md` | §9 — Phase 6 config changes |