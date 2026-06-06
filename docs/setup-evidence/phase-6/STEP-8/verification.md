# Step 8 Verification — VPS Deployment and Runtime Restart

## 1. What Was Done

Parent-verified the delegated VPS runtime deployment for Phase 6 source changes and service restart.

The delegated Step 8 task deployed:

- `src/core/services/llm_router.py`
- `src/core/services/llm_metrics.py`
- `src/core/main.py`

into `/home/guinevere/code/guinevere` on the VPS, restarted `hermes-gateway`, and also restarted `guinevere-core` because the metrics server is started by `src/core/main.py`.

## 2. Files Changed

### Local evidence

- `docs/setup-evidence/phase-6/STEP-8/implementation-report.md`
- `docs/setup-evidence/phase-6/STEP-8/verification.md`

### VPS runtime files deployed

- `/home/guinevere/code/guinevere/src/core/services/llm_router.py`
- `/home/guinevere/code/guinevere/src/core/services/llm_metrics.py`
- `/home/guinevere/code/guinevere/src/core/main.py`

### VPS backups

- `/home/guinevere/backups/phase-6/llm_router.py.20260606_114227`
- `/home/guinevere/backups/phase-6/main.py.20260606_114227`

## 3. Validation Results

### Service status

Command:

```powershell
ssh guinevere-vps "systemctl is-active hermes-gateway; systemctl is-active guinevere-9router; systemctl is-active guinevere-core"
```

Result:

```text
active
active
active
```

### 9Router model inventory

Command verified `http://localhost:20128/v1/models`.

Result:

```text
status 200
ds/deepseek-v4-flash True
cx/gpt-5.5 True
guinevere True
```

### Hermes config state

Command parsed `/home/guinevere/.hermes/config.yaml`.

Result:

```text
model ninerouter http://localhost:20128/v1 ds/deepseek-v4-flash
fallbacks [('custom', 'cx/gpt-5.5', 'http://localhost:20128/v1'), ('custom', 'guinevere', 'http://localhost:20128/v1')]
pre_hooks [('python3 ~/.hermes/hooks/budget_check.py', 500, 'block', 100), ('python3 ~/.hermes/hooks/consent_gate.py', 200, 'block', 90)]
post_hooks [('python3 ~/.hermes/hooks/dnr_filter.py', 50, 'block', 70)]
plugins ['auth_overlay', 'guinevere-persona']
```

### Metrics endpoint

Command fetched `http://localhost:9191/metrics`.

Result:

```text
metrics_ok True
hermes_llm_calls_total True
hermes_llm_latency_seconds True
hermes_llm_cost_usd_total True
hermes_fallback_activations_total True
```

### Recent journal error scan

Command scanned recent `hermes-gateway` and `guinevere-core` logs for:

- `Traceback`
- `ModuleNotFoundError`
- `ImportError`
- hook errors
- metrics errors
- config errors
- `LLM cost tracking failed`

Result: no matching recent errors. Journal access emitted the standard non-privileged visibility hint only.

## 4. Evidence Artifacts

- Implementation report: `docs/setup-evidence/phase-6/STEP-8/implementation-report.md`
- Parent verification: `docs/setup-evidence/phase-6/STEP-8/verification.md`

## 5. Doc-Sync Impact

No docs outside the Phase 6 evidence root were changed in this verification step.

## 6. Boundary Compliance

- LLM routing remains via `http://localhost:20128/v1`.
- No direct provider URLs were introduced.
- No secrets were printed or written.
- Budget hook remains priority 100, timeout 500, `on_failure: block`.
- Consent and DNR hooks remain configured.
- `plugins.enabled` remains unchanged (`auth_overlay`, `guinevere-persona` only).

## 7. Rollback / Re-run Safety

Rollback commands are documented in `STEP-8/implementation-report.md` lines 198-213 and 289-307. Backups are timestamped and were not overwritten.

## 8. Design Decisions / Caveats

- `guinevere-core` restart was required because metrics live in the FastAPI core app, not `hermes-gateway`.
- `pgvector` was installed in the VPS venv by the delegated task to fix a pre-existing startup blocker.
- Metrics are present and zero-initialized; Step 9 traffic should produce live samples.

## 9. Auditor Gate

Pending Step 12 independent auditors.

## 10. Security Scan

No secrets or direct provider endpoints appeared in parent verification output.

## 11. Acceptance Criteria Mapping

| Criterion | Status |
|---|---|
| Runtime source files deployed to VPS | PASS |
| `hermes-gateway` active | PASS |
| `guinevere-9router` active | PASS |
| `guinevere-core` active | PASS |
| 9Router HTTP 200 | PASS |
| Primary DeepSeek model present | PASS |
| Two fallbacks configured through localhost 9Router | PASS |
| Budget hook fail-closed config active | PASS |
| Metrics endpoint exposes all four required families | PASS |
| Recent logs show no Phase 6 startup errors | PASS |

## 12. Footer

Step 8 parent verification completed on 2026-06-06. Next step: Step 9 100-prompt VPS integration test through 9Router, followed by Redis DB5 cost-key and budget fail-closed verification.
