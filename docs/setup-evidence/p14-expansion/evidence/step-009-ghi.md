# P14 Step 009 — GHI scorer

## What Was Done
- Created `src/wearable/ghi.py` implementing a production-oriented Global Health Index scorer.
- Added `GHIResult` and internal baseline/result models for the module.
- Implemented async PostgreSQL access via `asyncpg` with parameterized queries.
- Added pillar scoring for sleep, cardio, activity, and recovery.
- Implemented dynamic weight rebalance, suppression for <2 available pillars, confidence aggregation, tier mapping, and exponential decay.
- Added persistence to `health.ghi_daily` and history retrieval.

## Files Changed
- `src/wearable/ghi.py`
- `evidence/p14/step-009-ghi.md`

## Validation Results
- `lsp_diagnostics` on `src/wearable/ghi.py`: 0 errors
- Remaining output at final verification should be limited to warnings only, if any.

## Evidence Artifacts
- Source: `src/wearable/ghi.py`
- Verification note: this file

## Doc-Sync Impact
- None. No existing docs or schemas were modified.

## Boundary Compliance
- No secrets were added.
- No unsafe catch-all exception blocks were introduced.
- Parameterized SQL used for all DB operations.
- No `as any`, `@type: ignore`, or `# type: ignore` used.
- Suppression rule preserved: GHI returns suppressed/critical when fewer than two pillars have usable data.

## Rollback / Re-run Safety
- Re-running the scorer is idempotent for `health.ghi_daily` due to `ON CONFLICT` upsert.
- File changes are isolated to the new module and this evidence note.

## Design Decisions / Caveats
- The module currently includes a local `BaselineResult` dataclass to avoid introducing cross-module dependency issues during import resolution.
- Recovery pillar uses stress rows and optional HRV value when available from the database.
- The design follows the requested 0-100 scoring model with per-pillar penalty cap behavior.

## Auditor Gate
- Pending.

## Security Scan
- No credentials or connection strings hardcoded.
- SQL queries are parameterized.

## Acceptance Criteria Mapping
- 0-100 GHI scoring: implemented
- Dynamic weight rebalance: implemented
- Confidence model: implemented
- Suppression when <2 pillars: implemented
- Exponential decay over 3 days: implemented
- Persistence and history access: implemented

## Footer
- Generated for P14 step 009.
