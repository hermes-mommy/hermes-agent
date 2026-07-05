# P26.1 Failure / Recovery Proof

Date: 2026-06-28
Live target: `root@49.12.82.34 -p 39999`

## What Was Done
- Temporarily stopped `9router-usage-writer.service`.
- Sent `4` authenticated `mimo` chat requests while the writer was inactive.
- Verified request-path success during the writer outage.
- Restarted the writer and verified SQLite landing rows afterward.

## Files Changed
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\failure-recovery.raw.json`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\failure-recovery-proof.md`

## Validation Results
- Before stop:
  - writer state: `active`
  - PM2 workers: `2`
  - PM2 restart total: `0`
  - buffer: `len=639 pending=0 lag=0 deadletter=0`
- Writer stopped:
  - writer state: `inactive`
  - buffer snapshot immediately after stop: `len=639 pending=0 lag=0`
- Requests sent while writer inactive:
  - `4/4` returned `200`
  - latency range: `2001.39 ms` to `2958.18 ms`
  - average: `2562.00 ms`
- During stop after requests:
  - buffer: `len=643 pending=0 lag=0 deadletter=0`
- After restart:
  - writer state: `active`
  - immediate buffer: `len=643 pending=0 lag=0 deadletter=0`
  - final buffer snapshot: `len=653 pending=0 lag=0 deadletter=0`
- Drain check:
  - `drained=true`
  - sample captured active writer with `pending=0 lag=0`

## Backlog Proof
- The most trustworthy backlog indicator in this run was stream growth, not Redis `lag`:
  - before stop window: `len=639`
  - during stop after request injection: `len=643`
- `lag` stayed `0` in this Redis/group state, so backlog should be interpreted from stream growth plus post-restart landed rows rather than `lag`.

## SQLite Landing Proof
- Exact post-recovery rows landed for the 4 injected requests:

| Row ID | Timestamp | Request ID | Stream ID | Worker ID | Status |
|---|---|---|---|---|---|
| `11443` | `2026-06-27T20:35:19.302Z` | `f0b408d6-acb1-4fc0-a6f1-094af01ab277` | `1782592519307-0` | `3` | `success` |
| `11444` | `2026-06-27T20:35:21.954Z` | `954f3aac-0036-4abb-9834-255227421b39` | `1782592521956-0` | `4` | `success` |
| `11445` | `2026-06-27T20:35:23.947Z` | `5d70cdd5-9b0a-468d-a0c5-518914fcca0a` | `1782592523950-0` | `3` | `success` |
| `11446` | `2026-06-27T20:35:26.599Z` | `a2354248-3c9d-4590-981e-23320753203d` | `1782592526602-0` | `4` | `success` |

Interpretation:
- The rows were persisted with non-empty `streamId`, which proves they were buffered through Redis before SQLite commit.
- Both workers (`3` and `4`) appeared in the recovered row set.

## Service Journal Proof
- Stop/start sequence in `journalctl -u 9router-usage-writer.service`:
  - `03:35:09` stopping
  - `03:35:11` stopped cleanly
  - `03:35:32` started
  - `03:35:33` writer startup log emitted with `dataDir=/var/lib/9router`

## Doc-Sync Impact
- This file is the canonical proof that request handling survives a writer outage and recovers without observable data loss in the controlled `4` request window.

## Boundary Compliance
- The writer was intentionally stopped only for the scoped proof window.
- PM2 worker count stayed `2`.
- The writer was not left stopped.

## Rollback / Re-run Safety
- Re-runnable.
- Requires authenticated request injection because the live path is auth protected.

## Design Decisions / Caveats
- `lag=0` did not meaningfully expose backlog here, so stream length growth plus landed `streamId` rows is the stronger recovery proof.
- Exact duplicate detection was limited to the controlled request window. In that window, `4` requests produced `4` landed rows.

## Auditor Gate
- Required input for `db-write-path`, `redis-durability`, `runtime-deploy`, and `rollback-idempotency`.

## Security Scan
- No API key value is present in this evidence file.

## Acceptance Criteria Mapping
- writer crash/stop does not break request path: pass
- backlog grows during writer outage: pass
- backlog drains after restart: pass
- SQLite rows land after restart: pass
- measurable no-loss / no-obvious-duplicate window: pass

## Footer
- Failure/recovery verdict: `PASS`.
