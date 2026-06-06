# Step 8 Implementation Report — VPS Deployment, Service Restart & Runtime Verification

**Date:** 2026-06-06  
**Status:** COMPLETE  
**Evidence root:** `docs/setup-evidence/phase-6/STEP-8/`  
**Governing plan:** `docs/setup-evidence/phase-6/plan.md` Step 8  
**Skills loaded:** ocs-delegation-gate, ocs-runtime-validation  
**Operator:** Faiz / Guinevere (parent executor)

---

## 1. What Was Done

Deployed Phase 6 LLM router CostTracker/metrics changes to the VPS runtime repo, restarted both `hermes-gateway` and `guinevere-core` services, and verified runtime health, fallback chain, budget hooks, 9Router availability, and Prometheus metrics exposure.

### Detailed actions

1. Confirmed VPS runtime repo at `/home/guinevere/code/guinevere` via SSH alias `guinevere-vps` (guinevere@100.94.104.22).
2. Backed up existing VPS runtime files with timestamp `20260606_114227`.
3. Copied three local source files to VPS runtime repo.
4. Verified Python `py_compile` for all three files on VPS.
5. Installed missing `pgvector` dependency in VPS venv (blocking prior guinevere-core startup).
6. Restarted `hermes-gateway.service` via root SSH.
7. Restarted `guinevere-core.service` to pick up updated `main.py` with metrics server.
8. Verified all services active, journals clean of Phase 6-related errors.
9. Verified 9Router HTTP 200 + required models.
10. Verified fallback providers and budget hook preserved.
11. Verified metrics endpoint `localhost:9191` exposes all four required metric families.

---

## 2. Files Changed

### VPS runtime repo files deployed

| File | Action | Local source |
|---|---|---|
| `src/core/services/llm_router.py` | Overwritten with Phase 6 CostTracker + metrics integration | `C:\Users\faizz\guinevere\src\core\services\llm_router.py` |
| `src/core/services/llm_metrics.py` | **Created** (new file — did not exist on VPS) | `C:\Users\faizz\guinevere\src\core\services\llm_metrics.py` |
| `src/core/main.py` | Overwritten with metrics server startup in lifespan | `C:\Users\faizz\guinevere\src\core\main.py` |

### Backup paths (VPS)

| File | Backup path |
|---|---|
| `llm_router.py` | `/home/guinevere/backups/phase-6/llm_router.py.20260606_114227` |
| `main.py` | `/home/guinevere/backups/phase-6/main.py.20260606_114227` |
| `llm_metrics.py` | No backup required (file did not exist previously) |

---

## 3. Validation Results

### 3.1 Python compile check

All three files pass `python3 -m py_compile` on VPS:

```
ROUTER_OK
METRICS_OK
MAIN_OK
```

### 3.2 Dependency fix

`pgvector` was missing from the VPS venv, causing `guinevere-core.service` to fail with `ModuleNotFoundError`. Installed via:

```
.venv/bin/pip install pgvector  →  Successfully installed pgvector-0.4.2
```

### 3.3 Service status post-restart

```
hermes-gateway.service:   active
guinevere-9router.service: active
guinevere-core.service:    active
```

### 3.4 Journal health (post-restart)

**hermes-gateway** (PID 25820, started 11:45:29):
- `persona_plugin_init` succeeded at 11:45:32.
- No `Traceback`, import error, hook load error, `LLM cost tracking failed`, metrics startup error, or config parse error.
- Only pre-existing warnings: MCP server no-command configs, stale systemd unit timeouts, Discord voice codecs.

**guinevere-core** (PID 29212 master, workers 29272/29273):
- `llm_metrics_server_started port=9191` logged at 11:49:26.
- `guinevere_starting` logged.
- Pre-existing `AuthenticationError` from surveillance consumer (Redis DB2 credentials) — caught gracefully, does not block startup.

### 3.5 9Router health

```
HTTP 200 — http://localhost:20128/v1/models
```

Required models present:
- `ds/deepseek-v4-flash` ✅
- `cx/gpt-5.5` ✅
- `guinevere` ✅

### 3.6 Fallback providers preserved

From `/home/guinevere/.hermes/config.yaml`:

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

Both fallbacks are routed through 9Router at `localhost:20128`. No direct provider URLs.

Primary: `ds/deepseek-v4-flash` via `ninerouter` provider.

### 3.7 Budget hook config preserved

From `/home/guinevere/.hermes/config.yaml`:

```yaml
hooks:
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
  post_tool_call:
    - command: python3 ~/.hermes/hooks/dnr_filter.py
      event: post_tool_call
      on_failure: block
      priority: 70
      timeout_ms: 50
```

- Budget hook: priority 100, timeout 500ms, `on_failure: block` ✅
- Consent hook: priority 90, preserved ✅
- DNR hook: priority 70, preserved ✅
- `plugins.enabled` unchanged: `[auth_overlay, guinevere-persona]` (no `budget_hook` added) ✅

### 3.8 Metrics endpoint

`http://localhost:9191/metrics` exposes all four required metric families:

| Metric family | Present |
|---|---|
| `hermes_llm_calls_total` (HELP + TYPE) | ✅ |
| `hermes_llm_latency_seconds` (HELP + TYPE) | ✅ |
| `hermes_llm_cost_usd_total` (HELP + TYPE) | ✅ |
| `hermes_fallback_activations_total` (HELP + TYPE) | ✅ |

Metric families are zero-initialized as expected (no LLM calls through the updated router yet).

---

## 4. Evidence Artifacts

| Artifact | Path |
|---|---|
| Parent verification file | `docs/setup-evidence/phase-6/STEP-8/verification.md` |
| Implementation report | `docs/setup-evidence/phase-6/STEP-8/implementation-report.md` |
| VPS backups | `/home/guinevere/backups/phase-6/llm_router.py.20260606_114227`, `/home/guinevere/backups/phase-6/main.py.20260606_114227` |

---

## 5. Doc-Sync Impact

No governing ADR or product documentation changed. The Prometheus scrape job was already updated in Step 7. No additional doc edits required.

---

## 6. Boundary Compliance

- No direct provider URLs (`api.openai.com`, `openrouter.ai`, `api.anthropic.com`) introduced.
- No secrets, API keys, or decrypted credentials printed or written.
- No type-safety suppression introduced.
- No empty catch or fail-open path introduced.
- No `plugins.enabled` modified — `budget_hook` plugin not created.
- Consent and DNR hooks preserved.
- Metrics are observational; do not bypass budget, consent, or HARD STOP.

---

## 7. Rollback / Re-run Safety

### Rollback commands (VPS)

```bash
# Restore backed-up files
cp /home/guinevere/backups/phase-6/llm_router.py.20260606_114227 \
   /home/guinevere/code/guinevere/src/core/services/llm_router.py
cp /home/guinevere/backups/phase-6/main.py.20260606_114227 \
   /home/guinevere/code/guinevere/src/core/main.py

# Remove new metrics file
rm /home/guinevere/code/guinevere/src/core/services/llm_metrics.py

# Restart services
systemctl restart hermes-gateway
systemctl restart guinevere-core
```

### Re-run safety

All operations are idempotent:
- Backups use timestamp suffixes, never overwrite.
- `start_llm_metrics_server()` is guarded by `_metrics_server_started` flag.
- `pip install pgvector` is idempotent (already satisfied).

---

## 8. Design Decisions / Caveats

1. **guinevere-core also required restart**: Although Step 8's scope is `hermes-gateway`, the Phase 6 metrics server starts from `src/core/main.py` (the guinevere-core FastAPI app), not from Hermes. Both services share the same repo. The core service was restarted to expose `localhost:9191/metrics`.

2. **pgvector dependency**: The VPS venv was missing `pgvector`, which is imported transitively via `src.core.services.__init__`. Installation was required for guinevere-core to boot. This is a pre-existing environment gap, not a Phase 6 regression.

3. **Surveillance Redis auth failure**: The surveillance consumer (Redis DB2, user `guinevere_core`) has an authentication error. This is pre-existing and does not block startup or metrics. It is caught and logged as `surveillance_consumer_start_failed`.

4. **Metrics are zero-initialized**: The four metric families appear in the `/metrics` output with HELP/TYPE lines but no data samples yet. Real data will appear after LLM calls flow through the updated `llm_router.py`.

5. **Systemd TimeoutStopSec warning**: Both hermes-gateway logs show a stale systemd unit warning (`TimeoutStopSec=90s` vs `drain_timeout=180s`). Pre-existing — mitigation requires `hermes gateway service install --replace`.

---

## 9. Auditor Gate

Pending Step 12 independent auditors:
- LLM routing correctness auditor.
- Cost accuracy auditor.
- ADR-035 compliance auditor.

---

## 10. Security Scan

- No credentials, plaintext API keys, Redis passwords, or direct provider endpoints introduced.
- No `.env` values exposed in logs or this report.
- No token/secret patterns found in changed files.

---

## 11. Acceptance Criteria Mapping

| Criterion | Status | Evidence |
|---|---|---|
| Target runtime repo confirmed | PASS | `/home/guinevere/code/guinevere` |
| Backups taken before overwrite | PASS | `backups/phase-6/` with timestamp suffix |
| Files copied to VPS | PASS | SCP of 3 files |
| Python compile clean | PASS | `py_compile` PASS for all 3 files |
| `hermes-gateway` restart success | PASS | `systemctl is-active → active` |
| `guinevere-core` restart success | PASS | `systemctl is-active → active` |
| No post-restart journal errors | PASS | No Traceback/import/hook/metrics errors |
| 9Router HTTP 200 | PASS | `curl localhost:20128/v1/models → 200` |
| Required models present | PASS | `ds/deepseek-v4-flash`, `cx/gpt-5.5`, `guinevere` |
| Fallback list has 2 entries | PASS | `cx/gpt-5.5` + `guinevere` both through localhost:20128 |
| Budget hook priority/timeout/on_failure | PASS | priority 100, timeout_ms 500, on_failure block |
| Consent/DNR hooks preserved | PASS | priority 90 (consent) + 70 (DNR) intact |
| `plugins.enabled` unchanged | PASS | Only `auth_overlay`, `guinevere-persona` |
| Metrics port 9191 reachable | PASS | `curl localhost:9191/metrics` |
| `hermes_llm_calls_total` present | PASS | HELP + TYPE found |
| `hermes_llm_latency_seconds` present | PASS | HELP + TYPE found |
| `hermes_llm_cost_usd_total` present | PASS | HELP + TYPE found |
| `hermes_fallback_activations_total` present | PASS | HELP + TYPE found |
| No secrets/direct providers/type suppressions | PASS | Scanned clean |

---

## 12. Footer

Step 8 completed on 2026-06-06. VPS runtime now includes Phase 6 CostTracker, metrics integration, and Prometheus exposure. Services stable, fallback chain intact, budget hook active, metrics endpoint live.

Next step: Step 9 — 100-prompt VPS integration test through 9Router.

---

## Rollback Commands

### If hermes-gateway restart fails

```bash
ssh guinevere-root "systemctl restart hermes-gateway && systemctl is-active hermes-gateway"
```

### If guinevere-core restart fails

```bash
ssh guinevere-root "systemctl restart guinevere-core.service && systemctl is-active guinevere-core.service"
```

### Full file rollback

```bash
ssh guinevere-root "cp /home/guinevere/backups/phase-6/llm_router.py.20260606_114227 /home/guinevere/code/guinevere/src/core/services/llm_router.py && cp /home/guinevere/backups/phase-6/main.py.20260606_114227 /home/guinevere/code/guinevere/src/core/main.py && rm /home/guinevere/code/guinevere/src/core/services/llm_metrics.py && systemctl restart hermes-gateway && systemctl restart guinevere-core.service"
```
