# P14 Step 008 — Anomaly Detection Engine

## What Was Done
Created `src/wearable/anomaly.py` implementing a per-metric anomaly detection engine with metric-specific thresholds, consecutive-reading persistence checks, SEV routing, and asyncpg persistence into `health.anomaly_events`.

## Files Changed
- `src/wearable/anomaly.py`
- `evidence/p14/step-008-anomaly.md`

## Validation Results
- Pending diagnostics run.
- Pending any runtime tests, if applicable.

## Evidence Artifacts
- Source implementation: `src/wearable/anomaly.py`
- DB target table: `health.anomaly_events`

## Doc-Sync Impact
- None. No existing docs were modified.

## Boundary Compliance
- Uses parameterized SQL for persistence.
- No hardcoded connection string.
- No single-reading anomaly routing; detection requires consecutive-rule confirmation.
- No type-ignore or `as any` usage.

## Rollback / Re-run Safety
- Safe to re-run detection; persistence is insert-only and isolated to anomaly events.
- File can be replaced without touching existing modules.

## Design Decisions / Caveats
- Baseline contract is handled via a small protocol fallback so the module can import even if `src/wearable/baseline.py` is not yet present.
- Metric thresholds are modeled as structured rules for future tuning.
- If a baseline is insufficient or missing a value, the detector skips that metric and logs the condition.

## Auditor Gate
- Not yet run.

## Security Scan
- No secrets, tokens, or raw surveillance data introduced.

## Acceptance Criteria Mapping
- Per-metric thresholds: implemented.
- SEV routing: implemented via rule→AlertSeverity mapping.
- Persistence requirements: implemented via min_consecutive checks.
- Database logging: implemented for `health.anomaly_events`.

## Footer
- Generated for P14 step 008 anomaly detection implementation.
