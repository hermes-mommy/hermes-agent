# Phase 6, Step 7 — Prometheus LLM Routing Metrics

**Date:** 2026-06-06  
**Status:** COMPLETE  
**Evidence root:** `docs/setup-evidence/phase-6/STEP-7/`

## What Was Done

### 1. Created metrics module `src/core/services/llm_metrics.py`

New standalone module exposing four required Prometheus metric families:

| Metric | Type | Labels | Description |
|---|---|---|---|
| `hermes_llm_calls_total` | Counter | `model`, `status` | Per-model call count (success/error) |
| `hermes_llm_latency_seconds` | Histogram | `model` | Call duration buckets |
| `hermes_llm_cost_usd_total` | Counter | `model` | Accumulated USD cost |
| `hermes_fallback_activations_total` | Counter | `from_model`, `to_model` | Fallback chain transitions |

Observer helper functions (`observe_call`, `observe_latency`, `observe_cost`, `observe_fallback`) encapsulate label management and metric updates.

`start_llm_metrics_server(port=9191)` launches a Prometheus HTTP server in a background daemon thread via `prometheus_client.start_http_server()`. Idempotent — safe to call multiple times.

### 2. Integrated metrics into `src/core/services/llm_router.py`

- Added `import time` and imports from `llm_metrics`.
- Each provider attempt now:
  - On **failure**: calls `observe_call(model, "error")` and `observe_fallback(from, to)` if a next model exists.
  - On **success**: calls `observe_call(model, "success")`, `observe_latency(model, duration)`, and `observe_cost(model, cost_usd)`.
- Cost is computed once and passed to both `CostTracker.record_cost` and the metrics observer.
- `duration` is initialized to `0.0` before the loop (satisfies type checker).

### 3. Started metrics server in `src/core/main.py` lifespan

Added `start_llm_metrics_server(port=9191)` in the FastAPI `lifespan` function, right after Sentry initialization.

### 4. Updated `monitoring/prometheus/prometheus.yml`

Added Job 8 `hermes-llm-routing` with target `localhost:9191`.

### 5. Created `tests/hermes/test_llm_metrics.py`

16 tests covering:
- Metric family definitions (names, labels).
- Observer functions produce correct rendered output.
- Counter values increment correctly (value assertions).
- Metrics server idempotency.
- LLMRouter integration: success path, error path, fallback path all call correct observers.

### 6. Verification

- **LSP diagnostics**: Clean on all changed source files.
- **pytest**: 16/16 metrics tests + 20/20 existing cost tests = **36/36 passed**.
- **YAML validation**: `prometheus.yml` parses correctly.
- **Forbidden pattern scan**: No violations introduced (pre-existing `# type: ignore[override]` in `main.py` unchanged).
- **HTTP smoke test**: All four metrics accessible via HTTP, correct names and labels present.

## Files Changed

| File | Action | Description |
|---|---|---|
| `src/core/services/llm_metrics.py` | **CREATE** | Metrics module with 4 families + observer helpers |
| `src/core/services/llm_router.py` | **MODIFY** | Added metrics calls, timing, cost computation |
| `src/core/main.py` | **MODIFY** | Start metrics server in lifespan |
| `monitoring/prometheus/prometheus.yml` | **MODIFY** | Added Job 8 `hermes-llm-routing` |
| `tests/hermes/test_llm_metrics.py` | **CREATE** | 16 tests for metrics |

## Validation Results

### pytest output (summary)

```
collected 36 items
tests/hermes/test_llm_metrics.py ................  [44%]
tests/hermes/test_llm_router_cost.py ............ [100%]
====================== 36 passed in 10.35s ======================
```

### Rendered metric output sample

```
# HELP hermes_llm_calls_total Total LLM calls, partitioned by model and status
# TYPE hermes_llm_calls_total counter
hermes_llm_calls_total{model="test",status="success"} 1.0

# HELP hermes_llm_latency_seconds Latency of LLM calls in seconds
# TYPE hermes_llm_latency_seconds histogram
hermes_llm_latency_seconds_bucket{model="test",le="0.1"} 0.0
hermes_llm_latency_seconds_bucket{model="test",le="0.5"} 0.0
...

# HELP hermes_llm_cost_usd_total Total LLM cost in USD
# TYPE hermes_llm_cost_usd_total counter
hermes_llm_cost_usd_total{model="test"} 0.01

# HELP hermes_fallback_activations_total Total fallback activations
# TYPE hermes_fallback_activations_total counter
hermes_fallback_activations_total{from_model="a",to_model="b"} 1.0
```

## Evidence Artifacts

- Implementation: `src/core/services/llm_metrics.py`
- Integration: `src/core/services/llm_router.py` (metrics calls in `chat()`)
- Server startup: `src/core/main.py` (lifespan)
- Prometheus scrape: `monitoring/prometheus/prometheus.yml` (Job 8)
- Tests: `tests/hermes/test_llm_metrics.py`
- This report: `docs/setup-evidence/phase-6/STEP-7/implementation-report.md`

## Doc-Sync Impact

- `monitoring/prometheus/prometheus.yml` updated directly (new scrape job).
- No ADR/PersonaSafetyPolicy changes required.

## Boundary Compliance

- No secrets introduced.
- No direct provider calls.
- No empty catches (`except` blocks in router are pre-existing).
- No type suppression introduced (pre-existing `# type: ignore[override]` in `main.py` untouched).
- Port 9191 does not conflict with existing services.

## Rollback / Re-run Safety

- `start_http_server` is idempotent (guard prevents duplicate servers).
- Tests are self-contained (no network/Redis dependencies).
- All changes are additive — removing the metrics module and reverting the three modified files restores original state.

## Design Decisions / Caveats

- **Metrics server on port 9191**: Separate from FastAPI's port 8000 to allow standalone operation. Uses `prometheus_client.start_http_server` (daemon thread).
- **Prometheus scrape target**: `localhost:9191` per planner scaffold. If Prometheus runs in Docker, this may need adjustment to `host.docker.internal:9191` (same pattern as FastAPI job).
- **Cost computation**: Computed in router for consistency with CostTracker. The `CostTracker.record_cost` also computes internally; this duplication is acceptable for metrics independence.
- **Latency tracked per successful attempt**: Only records time for the attempt that succeeded, not wall-clock time including fallbacks.

## Auditor Gate

Not yet run — will be part of Phase 6, Step 12 parallel audit batch.

## Acceptance Criteria Mapping

| Criterion | Status |
|---|---|
| `hermes_llm_calls_total{model,status}` exists | ✅ |
| `hermes_llm_latency_seconds` exists | ✅ |
| `hermes_llm_cost_usd_total` exists | ✅ |
| `hermes_fallback_activations_total` exists | ✅ |
| Scrape job `hermes-llm-routing` → `localhost:9191` | ✅ |
| Metrics exposed on `/metrics` endpoint | ✅ |
| Tests pass for all metric families | ✅ |
| No type suppressions introduced | ✅ |
| No empty catches introduced | ✅ |

---

**Footer:** Implementation complete. Ready for Step 12 audit batch.
