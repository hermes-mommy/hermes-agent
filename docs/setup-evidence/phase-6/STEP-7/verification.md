# Step 7 Verification — Prometheus LLM Metrics

## 1. What Was Done

Implemented and parent-verified Phase 6 LLM routing Prometheus metrics:

- Added `src/core/services/llm_metrics.py` with four required metric families.
- Wired metrics observers into `src/core/services/llm_router.py` success, error, latency, cost, and fallback paths.
- Started the metrics HTTP server from `src/core/main.py` on port `9191`.
- Added Prometheus scrape job `hermes-llm-routing` targeting `localhost:9191`.
- Added `tests/hermes/test_llm_metrics.py` and refined it to avoid protected Prometheus internals.
- Fixed the `start_http_server()` unused-call diagnostic in `llm_metrics.py`.

## 2. Files Changed

- `src/core/services/llm_metrics.py` — new Prometheus metric definitions, observer helpers, idempotent server starter.
- `src/core/services/llm_router.py` — metrics integration for success/error/fallback/cost/latency.
- `src/core/main.py` — starts LLM metrics server during FastAPI lifespan.
- `monitoring/prometheus/prometheus.yml` — adds scrape job targeting `localhost:9191`.
- `tests/hermes/test_llm_metrics.py` — new metrics tests.
- `docs/setup-evidence/phase-6/STEP-7/implementation-report.md` — implementation report from sub-agent.
- `docs/setup-evidence/phase-6/STEP-7/verification.md` — this parent verification file.

## 3. Validation Results

### Targeted tests

Command:

```powershell
python -m pytest tests/hermes/test_llm_metrics.py tests/hermes/test_llm_router_cost.py -v
```

Result: PASS — `36 passed, 100 warnings in 9.25s`.

Warnings are pytest/pytest-asyncio deprecations already present in this test environment; no test failures.

### LSP diagnostics

- `src/core/services/llm_metrics.py`: PASS — no diagnostics after assigning `start_http_server()` return value to `_`.
- `src/core/services/llm_router.py`: no errors; warnings are strict basedpyright third-party `structlog`/`json.loads` Any/Unknown warnings, already documented in Step 2.
- `src/core/main.py`: warnings remain from pre-existing strict typing debt (`structlog` Any, existing middleware typing, missing asyncpg stubs, unused call result in existing lifecycle code). The new metrics-server call did not introduce an LSP error.
- `tests/hermes/test_llm_metrics.py`: runtime tests pass; LSP still cannot resolve `pytest`, matching the existing test-environment issue documented in Steps 2-4. Protected Prometheus private-attribute warnings were removed by validating rendered Prometheus output instead of `_name`/`_labelnames`.

### Prometheus YAML validation

Command parsed `monitoring/prometheus/prometheus.yml` successfully with `yaml.safe_load`; result: `YAML_OK`.

Scrape job evidence from grep:

```text
- job_name: "hermes-llm-routing"
- targets: ["localhost:9191"]
```

### Metrics HTTP smoke test

Command started the metrics server on port `9191`, emitted one sample for each metric family, fetched `http://localhost:9191/metrics`, and verified all required families.

Result:

```text
METRICS_OK
hermes_llm_calls_total
hermes_llm_latency_seconds
hermes_llm_cost_usd_total
hermes_fallback_activations_total
```

### Forbidden-pattern scans

Targeted scans on changed metrics/router source and metrics tests found no matches for:

- `as any`
- `@ts-ignore`
- `@ts-expect-error`
- empty catches (`except Exception: pass`, `except: pass`)
- direct provider URLs (`api.openai.com`, `openrouter.ai`, `api.anthropic.com`)
- long `sk-` token patterns
- `NINEROUTER_API_KEY=` or `REDIS_PASSWORD=` assignments

`monitoring/prometheus/prometheus.yml` contains only the expected `hermes-llm-routing` and `localhost:9191` matches; no direct provider URLs or secrets.

## 4. Evidence Artifacts

- Sub-agent implementation report: `docs/setup-evidence/phase-6/STEP-7/implementation-report.md`
- Parent verification file: `docs/setup-evidence/phase-6/STEP-7/verification.md`
- Metrics tests: `tests/hermes/test_llm_metrics.py`
- Runtime smoke result: `METRICS_OK` with all four required metric family names.

## 5. Doc-Sync Impact

No governing ADR or product documentation was changed in this step. The Prometheus scrape job is now represented in `monitoring/prometheus/prometheus.yml`.

## 6. Boundary Compliance

- No direct provider calls were introduced; LLM routing remains through `http://localhost:20128/v1`.
- No secrets or decrypted credentials were written.
- No type-safety suppression was introduced.
- No empty catch or fail-open path was introduced.
- Metrics are observational only; they do not bypass budget, consent, or HARD STOP behavior.

## 7. Rollback / Re-run Safety

Rollback:

```powershell
git checkout -- src/core/services/llm_router.py src/core/main.py monitoring/prometheus/prometheus.yml
Remove-Item -LiteralPath "src/core/services/llm_metrics.py"
Remove-Item -LiteralPath "tests/hermes/test_llm_metrics.py"
```

Re-run validation:

```powershell
python -m pytest tests/hermes/test_llm_metrics.py tests/hermes/test_llm_router_cost.py -v
python -c "import yaml; yaml.safe_load(open('monitoring/prometheus/prometheus.yml')); print('YAML_OK')"
```

## 8. Design Decisions / Caveats

- The scrape target is exactly `localhost:9191` because Faiz explicitly required it.
- If Prometheus runs inside Docker in a topology where `localhost` points at the Prometheus container rather than the host, a later operations step may need `host.docker.internal:9191`; this is intentionally not changed in Phase 6 because it would violate the user-specified target.
- Metrics are emitted only after successful cost tracking; if `CostTracker.record_cost()` fails, the router raises `RuntimeError("LLM cost tracking failed")` before emitting success/cost metrics, preserving fail-closed behavior for untracked spend.
- The metrics server is started from FastAPI lifespan. VPS deployment/restart verification is required next before claiming runtime activation.

## 9. Auditor Gate

Pending Step 12 independent auditors:

- LLM routing correctness auditor.
- Cost accuracy auditor.
- ADR-035 compliance auditor.

## 10. Security Scan

Targeted scans found no credentials, plaintext API keys, Redis passwords, or direct provider endpoints in changed metrics files.

## 11. Acceptance Criteria Mapping

| Criterion | Status |
|---|---|
| `hermes_llm_calls_total{model,status}` exists | PASS |
| `hermes_llm_latency_seconds` exists | PASS |
| `hermes_llm_cost_usd_total` exists | PASS |
| `hermes_fallback_activations_total` exists | PASS |
| Prometheus scrape job targets `localhost:9191` | PASS |
| Router metrics do not bypass CostTracker fail-closed behavior | PASS |
| No secrets/direct providers/type suppressions/empty catches introduced | PASS |
| Targeted metrics/router tests pass | PASS |

## 12. Footer

Step 7 parent verification completed on 2026-06-06. Next step: deploy source/config changes to VPS, restart `hermes-gateway`, and verify runtime service/metrics/logs.
