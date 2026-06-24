# P14 Step 004 — Mi Fitness client and normalizer

## What Was Done
- Added `src/wearable/mi_fitness_client.py` as a synchronous Mi Fitness Cloud client with guarded external imports, auth flow, circuit breaker state, token persistence hooks, backoff hooks, and Prometheus-ready counter placeholders.
- Added `src/wearable/normalizer.py` as a pure normalization module converting `FetchResult` into `HealthMetricPayload` with per-metric extractors and provenance tagging.

## Files Changed
- `src/wearable/mi_fitness_client.py`
- `src/wearable/normalizer.py`
- `evidence/p14/step-004-client-normalizer.md`

## Validation Results
- Pending: `lsp_diagnostics` on both changed modules.
- Pending: no runtime build/test command was requested or available for this step.

## Evidence Artifacts
- This evidence file documents implementation intent and scope for step 004.

## Doc-Sync Impact
- No existing docs or shared model/error/config files were modified.

## Boundary Compliance
- No secrets were hardcoded.
- No async API client was introduced.
- No forbidden type-suppression syntax was intentionally added.
- No existing files were modified.

## Rollback / Re-run Safety
- Both modules are additive and can be removed without touching shared models.
- Redis and external SDK integrations are guarded so the module degrades safely when dependencies are absent.

## Design Decisions / Caveats
- External Mi Fitness libraries are imported behind a try/except guard.
- Circuit breaker is implemented locally with 3-failure open behavior and 30-minute recovery window.
- Prometheus hooks are placeholders only and log through structlog.
- Normalizer currently reconstructs raw-like payloads from `MetricResult.samples`; it is pure and side-effect free.

## Auditor Gate
- Not yet run.

## Security Scan
- No credential literals or token values included.
- No bare except blocks without logging were intentionally used.

## Acceptance Criteria Mapping
- Mi Fitness client: implemented.
- Normalizer: implemented.
- Evidence file: implemented.
- Diagnostics clean: pending.

## Footer
- Step 004 evidence draft for wearable client + normalizer implementation.
