# P26.1 SQLite Lock Proof

Date: 2026-06-28
Live target: `root@49.12.82.34 -p 39999`

## What Was Done
- Examined SQLite lock signatures before and after the authenticated loadtest plus failure/recovery run.
- Checked:
  - `SQLITE_BUSY`
  - `SQLITE_BUSY_SNAPSHOT`
  - `database is locked`
  - `better-sqlite3`
- Compared old worker logs with the current post-cutover worker logs.
- Spot-checked the live SQLite row count after validation.

## Files Changed
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\sqlite-lock-proof.md`

## Validation Results
- SQLite integrity still returns `ok`.
- Live `usageHistory` total rows on spot-check after runtime validation: `11625`.
- Authenticated loadtest per-phase busy-count deltas:
  - phase `50` -> `0`
  - phase `200` -> `0`
  - phase `700` -> `0`
- Current PM2 worker error logs:
  - `/root/.pm2/logs/9router-error-3.log` -> no lock matches
  - `/root/.pm2/logs/9router-error-4.log` -> no lock matches
- Historical lock residue still exists in the stale-runtime-era log:
  - `/root/.pm2/logs/9router-error-0.log`

## Historical Residuals
- Historical matches remain visible:
  - `SqliteError: database is locked`
  - `code: 'SQLITE_BUSY'`
  - `unhandledRejection: SqliteError: database is locked`
- Those matches are attached to the pre-cutover / stale-runtime lineage and were not reproduced by the current authenticated runtime validation.

## Interpretation
- The Redis stream offload is reducing hot-path SQLite contention in the currently active runtime.
- The old lock signatures are not erased from historical logs, so the honest verdict is not `CLEAN`.

## Doc-Sync Impact
- Final status should cite this file when explaining why the verdict is improved rather than perfectly clean.

## Boundary Compliance
- Read-only verification only.
- No DB mutation was performed for this proof beyond the already executed runtime tests and a row-count spot-check.

## Rollback / Re-run Safety
- Safe to re-run.

## Design Decisions / Caveats
- Log history is cumulative, so old lock signatures remain visible even after the current runtime is fixed.
- The stronger signal is: no new busy growth during authenticated load and no new matches in current worker logs.

## Auditor Gate
- Required input for `db-write-path`, `performance-loadtest`, and `evidence-docs`.

## Security Scan
- No secrets recorded.

## Acceptance Criteria Mapping
- current runtime avoids reproducing historical lock storm during loadtest: pass
- new busy-count growth absent: pass
- old historical residue acknowledged: pass

## Footer
- SQLite lock verdict: `IMPROVED_WITH_RESIDUAL`.
