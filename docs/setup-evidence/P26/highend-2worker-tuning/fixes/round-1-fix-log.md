# P26 Fix and Violation Log

Date: 2026-06-27

## Scaffold Violation 1

During Step B, the syntax-check scaffold included `/root/9router/.next/standalone/src/lib/db/schema.js`, but the live VPS runtime did not have that file. The patch had already applied to the planned file list before the check failed, and PM2 had not restarted yet.

Resolution:

- Treat the missing standalone schema file as a planner/scaffold specificity error.
- Re-run syntax checks only for existing source/standalone adapter files.
- Verify required PRAGMA/checkpoint patterns across the actual backed-up patch file list.
- Continue with PM2 restart only after that verification passes.

Status: closed for scaffold handling. Corrected verification and PM2 restart evidence are recorded in `implementation/sqlite-tuning.md` and `implementation/pm2-node-tuning.md`. The process defect remains documented for audit traceability.

## Round-1 Finding Fixes

### Runtime Audit F1 - SQLite Integrity Failure

Status: fixed.

Evidence:

- `verification/sqlite-integrity-investigation.md`
- `verification/sqlite-recovery-options.md`
- `verification/sqlite-repair-candidate-inspection.md`
- `fixes/sqlite-repair-log.md`

Resolution:

- Confirmed cold integrity failure with 9Router stopped.
- Preserved corrupt live DB before repair.
- Built a repaired candidate from the clean pre-mutation backup plus readable rows from the current corrupt copy.
- Verified repaired candidate integrity was `ok`.
- Swapped only the SQLite DB while 9Router was stopped.
- Verified live DB integrity `ok` after swap and restarted exactly 2 PM2 workers.

### Runtime/Worker Audit F2 - Empty Loadtest Artifacts

Status: fixed.

Evidence:

- `loadtest/baseline-loadtest.md`
- `loadtest/post-tuning-loadtest.md`

Resolution:

- Re-ran `/v1/models` loadtests after DB repair.
- Baseline run: 300 requests, concurrency 20, 100% HTTP 200.
- Post run: 700 requests, concurrency 50, 100% HTTP 200.
- Both artifacts include timing summaries, PM2 pre/post state, memory, SQLite integrity, and marker-based log scans.

### Worker Balance 45/55 Proof

Status: limitation remains.

Evidence:

- `loadtest/baseline-loadtest.md`
- `loadtest/post-tuning-loadtest.md`
- `audits/round-1/worker-balance-audit.md`

Resolution:

- Loadtest proves endpoint success and 2-worker stability.
- The `/v1/models` route did not emit per-request worker logs sufficient to calculate a 45/55 to 55/45 split.
- Final status must not claim strict worker-balance PASS unless additional instrumentation or a request path with per-worker logging is added.
