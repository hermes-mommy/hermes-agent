# P26 Highend 2-Worker Tuning - SQLite Lock Audit Round 1

Date: 2026-06-27  
Auditor: Codex  
Scope: SQLite lock mitigation evidence for P26 highend 2-worker tuning  
Output path: `docs/setup-evidence/P26/highend-2worker-tuning/audits/round-1/sqlite-lock-audit.md`

## Verdict

PASS WITH CAVEAT.

The available evidence supports that the SQLite runtime PRAGMA/checkpoint patch was applied to the intended runtime file set, old high-contention patterns were absent from the patched file list, and the clean post-marker verification recorded 0 new SQLite lock matches after the marker. The remaining caveat is that the app write-path retry recommendation from research is not proven implemented in this patch set, so future SQLite lock resilience still depends on adding bounded retry/full transaction retry for write paths if contention recurs.

## Files Read

- `AGENTS.md`
- `docs/setup-evidence/P26/highend-2worker-tuning/research/sqlite-lock-analysis.md`
- `docs/setup-evidence/P26/highend-2worker-tuning/implementation/sqlite-tuning.md`
- `docs/setup-evidence/P26/highend-2worker-tuning/verification/post-marker-sqlite-lock-verification.md`
- `docs/setup-evidence/P26/highend-2worker-tuning/verification/post-load-error-classification.md`
- `docs/setup-evidence/P26/highend-2worker-tuning/fixes/round-1-fix-log.md`
- Supporting grep scan across `docs/setup-evidence/P26/highend-2worker-tuning`

## Audit Criteria

| Criterion | Result | Evidence |
|---|---:|---|
| AGENTS.md read first | PASS | `AGENTS.md` was read before substantive audit work. |
| SQLite research reviewed | PASS | Research documents prior `SQLITE_BUSY`, `SQLITE_BUSY_SNAPSHOT`, WAL state, recommended PRAGMAs, checkpoint changes, and write-path retry. |
| PRAGMA patch evidence present | PASS | Implementation records required counts for `busy_timeout=30000`, `wal_autocheckpoint=10000`, `mmap_size=268435456`, and passive checkpointing. |
| Old pattern absence checked | PASS | Implementation records `PASS: old PRAGMA/checkpoint patterns absent from patched file list`. |
| Post-marker 0 new SQLite lock matches | PASS | Post-marker verification scans only bytes after the marker and records `0` for all four PM2 log files. |
| Caveat around app write-path retry | PASS WITH CAVEAT | Research recommends bounded retry/full transaction retry; implementation evidence does not prove that retry layer was added. |

## Research Evidence Review

`sqlite-lock-analysis.md` establishes that SQLite was already in WAL mode but that recent PM2 logs contained real lock failures under the 2-worker PM2 topology:

- `SQLITE_BUSY`
- `SQLITE_BUSY_SNAPSHOT`
- `database is locked`

The research identified two separate mitigation layers:

1. Connection/runtime tuning:
   - `PRAGMA busy_timeout = 30000`
   - `PRAGMA wal_autocheckpoint = 10000`
   - `PRAGMA mmap_size = 268435456`
   - replace disruptive `wal_checkpoint(TRUNCATE)` with less disruptive passive checkpoint behavior or leader-only checkpointing.
2. App write-path resilience:
   - bounded retry for `SQLITE_BUSY`
   - full transaction retry for `SQLITE_BUSY_SNAPSHOT`
   - no retry around non-idempotent external side effects unless DB writes are separated.

This matters because the implemented evidence strongly covers item 1, but not item 2.

## Implementation Evidence Review

`sqlite-tuning.md` documents a backup root and runtime patch application to 17 files, including:

- `/root/9router/src/lib/db/schema.js`
- `/root/9router/src/lib/db/adapters/betterSqliteAdapter.js`
- `/root/9router/src/lib/db/adapters/bunSqliteAdapter.js`
- `/root/9router/src/lib/db/adapters/nodeSqliteAdapter.js`
- standalone adapter files
- compiled Next.js chunk files

The key patch evidence is:

```text
PASS: old PRAGMA/checkpoint patterns absent from patched file list
busy_timeout_30000=11
wal_autocheckpoint_10000=11
mmap_268435456=11
checkpoint_passive=24
```

This is sufficient evidence that the intended PRAGMA/checkpoint runtime patch was applied broadly across the active source/standalone/chunk surface. A read-only SSH spot check also produced matching new-pattern counts for the first three PRAGMAs and zero old-pattern counts before a shell quoting issue stopped the supplemental command; I did not rely on that failed command for the post-marker verdict.

## Old Pattern Absence

The audit accepts the old-pattern absence claim because the implementation report explicitly records it after the patched file list was established:

```text
PASS: old PRAGMA/checkpoint patterns absent from patched file list
```

The old patterns under review were:

- `PRAGMA busy_timeout = 5000`
- `PRAGMA mmap_size = 30000000`
- `wal_checkpoint(TRUNCATE)`

No evidence was found in the reviewed files contradicting the absence claim.

## Post-Marker SQLite Lock Verification

`post-marker-sqlite-lock-verification.md` establishes a marker at:

```text
2026-06-27T18:14:55+07:00
```

It records old and new byte sizes for four PM2 logs and scans only new bytes after the marker:

```text
/root/.pm2/logs/9router-error-0.log old_size=25230 new_size=25230 -> 0
/root/.pm2/logs/9router-error-1.log old_size=47211 new_size=47211 -> 0
/root/.pm2/logs/9router-out-0.log old_size=2769775 new_size=2769905 -> 0
/root/.pm2/logs/9router-out-1.log old_size=5747777 new_size=5747777 -> 0
```

The post-marker probe returned:

```text
200 200
```

PM2 state in the same file shows both 9Router cluster workers online after restart:

```text
id 0 pid 39839 online
id 1 pid 39852 online
```

Audit conclusion: the post-marker evidence supports the claim of 0 new `SQLITE_BUSY`, `SQLITE_BUSY_SNAPSHOT`, `database is locked`, or `SQLITE_LOCKED` matches in the scanned new log bytes.

## Important Timing Distinction

`post-load-error-classification.md` and `post-tuning-snapshot.md` still show SQLite lock lines around `2026-06-27T18:14:11+07:00`, before the clean marker at `2026-06-27T18:14:55+07:00`.

Those earlier lines are real and should not be erased from the record, but they do not contradict the post-marker verification because the post-marker scan intentionally uses byte offsets captured after those failures.

## Caveat: App Write-Path Retry

The SQLite research explicitly recommends bounded retry for app writes and full transaction retry for `SQLITE_BUSY_SNAPSHOT`. The implementation evidence reviewed here proves PRAGMA/checkpoint tuning, but does not prove a retry wrapper was added around provider/settings/request-success write paths.

This is acceptable for round 1 only as `PASS WITH CAVEAT`, because:

- the requested PRAGMA/checkpoint mitigation appears applied;
- the post-marker lock scan is clean;
- the original `SQLITE_BUSY_SNAPSHOT` risk can still reappear under concurrent write pressure without whole-transaction retry.

Recommended follow-up if any new post-marker SQLite lock appears:

1. Add a bounded retry helper for safe SQLite write transactions.
2. Retry the whole transaction on `SQLITE_BUSY_SNAPSHOT`.
3. Keep external provider calls outside retry loops unless DB writes are clearly separated from external side effects.
4. Add a non-secret, non-destructive write-path smoke test to the evidence gate.

## Scaffold and Evidence Integrity

`fixes/round-1-fix-log.md` records a scaffold specificity violation: the planned standalone schema syntax-check path did not exist on the live VPS. The fix log says the issue was handled by treating it as a planner/scaffold specificity error, re-running checks only against existing files, and continuing only after pattern verification passed.

Audit status: acceptable with caveat. The violation was not silently sanitized; it was recorded in the fix log, and the subsequent implementation evidence contains the required pattern counts and restart evidence.

## Boundary and Safety Review

- No secrets were required for this audit.
- No secrets are included in this audit report.
- VPS access, where attempted, was read-only.
- No service restart, file edit, firewall change, database mutation, PM2 mutation, or deployment action was performed by this auditor.
- This audit writes only the requested local output file.

## Final Round 1 Decision

Round 1 SQLite lock audit passes with a bounded caveat:

- PRAGMA/checkpoint patch evidence: PASS.
- Old high-contention pattern absence: PASS.
- Clean post-marker SQLite lock scan: PASS.
- App write-path retry: NOT PROVEN; keep as caveat/follow-up unless new lock evidence appears.

Footer: P26 highend 2-worker tuning SQLite lock audit round 1, generated 2026-06-27.
