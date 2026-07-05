# P26.1 Audit - DB Write Path

Date: 2026-06-28
Scope: normal hot path offload, failure/recovery landing proof, SQLite-before-`XACK`, SQLite lock verdict honesty

## Findings

### Medium - Failure/recovery `streamId` landing proof is stated in prose but not preserved in the machine-readable artifact
- The controlled failure/recovery helper only queried `id`, `timestamp`, `model`, `workerId`, `status`, and `endpoint` from `usageHistory`, so the raw artifact does not retain either `requestId` or `streamId` for the 4 recovered rows in its `usageWindow.rows` payload: [p26-failure-recovery.mjs](C:\Users\faizz\guinevere\.codex\staging\p26-redis-write-buffer\p26-failure-recovery.mjs:38), [failure-recovery.raw.json](C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\failure-recovery.raw.json:213).
- The rendered proof then claims exact `requestId` and non-empty `streamId` values for those same 4 rows and uses that as the key landing proof: [failure-recovery-proof.md](C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\failure-recovery-proof.md:44).
- Impact: the recovery run still credibly shows request-path survival and backlog growth/drain, but the strongest claim, "these exact recovered SQLite rows carried non-empty `streamId` after restart", is not fully reproducible from the raw artifact alone.

### Medium - Loadtest `sqliteBusy` delta sampled stale PM2 log files, not the current post-cutover workers
- The load harness computes `sqliteBusyCount` only from `/root/.pm2/logs/9router-error-0.log` and `/root/.pm2/logs/9router-error-1.log`: [p26-loadtest.mjs](C:\Users\faizz\guinevere\.codex\staging\p26-redis-write-buffer\p26-loadtest.mjs:75).
- The active post-cutover workers in the validated runtime are `pm_id=3` and `pm_id=4`, not `0` and `1`: [pm2-cutover-proof.md](C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\pm2-cutover-proof.md:13), [loadtest-results.md](C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\loadtest-results.md:54).
- `sqlite-lock-proof.md` separately and honestly says current logs `9router-error-3.log` and `9router-error-4.log` had no lock matches while historical residue remained in `9router-error-0.log`: [sqlite-lock-proof.md](C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\sqlite-lock-proof.md:18).
- Impact: the final verdict `IMPROVED_WITH_RESIDUAL` is directionally honest, but the per-phase "busy-count delta stayed 0" evidence is weaker than presented because it tracks historical residue files rather than the current worker logs.

## Assumptions / Open Questions

- The normal healthy hot path appears to be Redis-first in the live runtime. `saveUsageStats(...)` calls `saveRequestUsage(...)` from request completion/error handling, `saveRequestUsage(...)` first attempts `publishUsageEvent(...)`, and only falls back to `persistUsageHistoryDirect(...)` if publish fails: `/root/9router/open-sse/handlers/chatCore/requestDetail.js:75-115`, `/root/9router/src/lib/db/repos/usageRepo.js:244-299`, [implementation-verification.md](C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\evidence\implementation-verification.md:29).
- The live runtime evidence is consistent with that healthy-path offload claim: authenticated load phases advanced Redis stream length while keeping `pending=0`, `deadletter=0`, and PM2 stable at 2 workers: [loadtest-results.md](C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\loadtest-results.md:16).
- Writer ordering is correct in code. The writer reads stream messages, persists them through `persistUsageHistoryDirect(events)`, and only then issues `XACK`: [usageBuffer.js](C:\Users\faizz\guinevere\.codex\staging\p26-redis-write-buffer\usageBuffer.js:651). `persistUsageHistoryDirect(...)` writes inside a SQLite transaction before control returns: [usageBuffer.js](C:\Users\faizz\guinevere\.codex\staging\p26-redis-write-buffer\usageBuffer.js:326).
- The codebase is not Redis-only. If Redis publish fails, `saveRequestUsage(...)` intentionally falls back to direct SQLite persistence, so this audit's "offloaded hot path" conclusion applies to the currently healthy runtime, not every degraded mode: `/root/9router/src/lib/db/repos/usageRepo.js:252-299`.

## Summary Verdict

PASS with evidence-quality caveats.

The live normal path is convincingly Redis-first rather than direct SQLite in the current healthy runtime, and the writer code clearly persists SQLite before `XACK`. The two issues above do not overturn that conclusion, but they do mean the evidence bundle slightly overstates (1) exact recovered `streamId` traceability and (2) how directly the loadtest proves absence of new SQLite lock growth in the active PM2 workers.
