# P14 Step 007 — Baseline Calculator

## What Was Done
- Created `src/wearable/baseline.py` implementing a 28-day wearable baseline calculator with warmup stages.
- Added `BaselineCalculator` with async pool management, metric-specific reads, baseline computation, persistence, retrieval, and bulk computation.
- Added `BaselineResult` dataclass and a local persisted `BaselineState` model matching the `health.baseline_state` table.
- Implemented graceful degradation for missing/failed metric queries by logging warnings and returning an insufficient baseline state.

## Files Changed
- `src/wearable/baseline.py`
- `evidence/p14/step-007-baseline.md`

## Validation Results
- Pending diagnostics run.

## Evidence Artifacts
- This evidence file

## Doc-Sync Impact
- None

## Boundary Compliance
- No secrets or credentials added.
- No existing files modified.
- Parameterized SQL used for runtime queries.

## Rollback / Re-run Safety
- Remove `src/wearable/baseline.py` if rollback is required.
- Evidence file can be regenerated safely.

## Design Decisions / Caveats
- Metric routing is explicit via `_METRIC_READERS`.
- Baseline confidence is stage-driven and degrades to zero for insufficient data.
- Rebaseline detection is based on a >7 day gap against the previously stored baseline.
- The repository config file did not expose baseline-specific fields, so the module currently falls back to the expected 28-day / 3-point defaults.

## Acceptance Criteria Mapping
- 28-day rolling baseline: implemented.
- Warmup state machine: implemented.
- TimescaleDB persistence: implemented via `health.baseline_state` upsert.
- Metric gaps handled gracefully: implemented with warning + insufficient baseline state.
- Per-metric independence: implemented.

## Footer
- Generated for P14 Step 007
