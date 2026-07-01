# P26.1 Round 1 Fix Log

Date: 2026-06-28

## What Was Done
- Fixed the live runtime mismatch where PM2 was still serving a deleted stale standalone bundle.
- Updated the local validation harnesses so they can exercise the now-authenticated live runtime without persisting secrets.
- Tightened evidence quality so post-fix artifacts now sample the active PM2 workers and preserve request-to-stream-to-SQLite linkage in the failure/recovery raw output.

## Fixes

### CRITICAL - PM2 was serving a stale deleted standalone bundle instead of the current build
- Symptom:
  - PM2 workers were running from `/root/9router/.next/standalone/custom-server.js`
  - process cwd showed `/root/9router/.next/standalone (deleted)`
  - live request path still behaved like the old direct-write/auth-older runtime
- Fix:
  - cut PM2 over to `/root/9router/.next/standalone/server.js`
  - preserved exactly `2` workers
  - preserved cluster mode
  - saved updated PM2 process list
- Proof:
  - `runtime/pm2-cutover-proof.md`
  - `runtime/loadtest-results.md`
  - `runtime/failure-recovery-proof.md`

### MEDIUM - Anonymous validation harness no longer matched the current auth-protected live runtime
- Symptom:
  - post-cutover anonymous `/v1/models` returned `401 Unauthorized`
  - initial post-cutover loadtest run measured unauthorized failures rather than real production-path behavior
- Fix:
  - updated `.codex/staging/p26-redis-write-buffer/p26-loadtest.mjs` to read `P26_API_KEY` from runtime environment only
  - updated `.codex/staging/p26-redis-write-buffer/p26-failure-recovery.mjs` to read `P26_API_KEY` from runtime environment only
  - reran authenticated loadtest and failure/recovery against the real live path
- Proof:
  - `runtime/loadtest-results.md`
  - `runtime/failure-recovery-proof.md`

### LOW - Local verification helpers had timeout / quoting issues that could falsely break evidence capture
- Symptom:
  - remote helper processes did not always exit cleanly after printing
  - a SQL literal in the loadtest helper was shell-fragile
  - PM2 snapshot timeout was too short for stable evidence capture
- Fix:
  - forced explicit process exit in remote helper snippets
  - parameterized the `mimo-v2.5-pro` worker-row SQL query
  - widened PM2 snapshot timeout in both helper scripts
- Proof:
  - authenticated raw runtime artifacts were produced successfully after the fixes

### MEDIUM - Loadtest sqlite-busy sampling still pointed at stale PM2 worker logs
- Symptom:
  - the first authenticated rerun still counted `SQLITE_BUSY` from old `9router-error-0.log` / `9router-error-1.log`
  - that did not reflect the active post-cutover workers `3` and `4`
- Fix:
  - updated `.codex/staging/p26-redis-write-buffer/p26-loadtest.mjs` to sample busy signatures from the active PM2 worker ids returned by the current runtime snapshot
  - reran the authenticated `50/200/700` phases and regenerated `loadtest-results.raw.json`
- Proof:
  - `runtime/loadtest-results.raw.json`
  - `runtime/loadtest-results.md`
  - `runtime/sqlite-lock-proof.md`

### MEDIUM - Failure/recovery raw artifact needed request-to-stream linkage for auditability
- Symptom:
  - the earlier raw artifact proved row landing, but did not include `requestId` and `streamId` in the captured recovery window rows
  - that made the Redis-to-SQLite chain stronger in prose than in the raw evidence itself
- Fix:
  - updated `.codex/staging/p26-redis-write-buffer/p26-failure-recovery.mjs` to capture `requestId`, `streamId`, and `workerId` in `usageWindow.rows`
  - reran the authenticated failure/recovery proof and regenerated the raw artifact
- Proof:
  - `runtime/failure-recovery.raw.json`
  - `runtime/failure-recovery-proof.md`

## Files Changed
- `C:\Users\faizz\guinevere\.codex\staging\p26-redis-write-buffer\p26-loadtest.mjs`
- `C:\Users\faizz\guinevere\.codex\staging\p26-redis-write-buffer\p26-failure-recovery.mjs`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\fixes\round-1-fix-log.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\loadtest-results.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\failure-recovery-proof.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\sqlite-lock-proof.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\worker-health-proof.md`

## Boundary Compliance
- PM2 worker count was preserved at exactly `2`.
- No firewall changes were made.
- No secrets were written to disk in the fix process.

## Footer
- Round-1 fix status: `STALE RUNTIME FIXED; AUTHENTICATED VALIDATION PATH RESTORED; EVIDENCE QUALITY GAPS CLOSED`.
