# P26.1 Worker Health Proof

Date: 2026-06-28
Live target: `root@49.12.82.34 -p 39999`

## What Was Done
- Verified live PM2 worker count after the production cutover to `/root/9router/.next/standalone/server.js`.
- Used PM2 metrics plus usage-row `workerId` evidence to confirm both workers receive traffic.

## Files Changed
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\worker-health-proof.md`

## Validation Results
- PM2 worker count is exactly `2`:
  - `pm_id=3`, pid `56767`
  - `pm_id=4`, pid `56774`
- Restart count remained `0` throughout the authenticated loadtest and failure/recovery run.
- Both workers remained `online`.

## Traffic Distribution Evidence

### PM2 HTTP Metrics
- Phase `50` after snapshot:
  - worker `3` -> `httpReqPerMin=0.35`
  - worker `4` -> `httpReqPerMin=0.19`
- Phase `200` after snapshot:
  - worker `3` -> `httpReqPerMin=1.99`
  - worker `4` -> `httpReqPerMin=0.78`
- Phase `700` after snapshot:
  - worker `3` -> `httpReqPerMin=3.42`
  - worker `4` -> `httpReqPerMin=3.68`

### Usage Row Worker IDs
- Authenticated loadtest windows showed both worker IDs:
  - phase `50` -> worker `3`=`4`, worker `4`=`1`
  - phase `200` -> worker `3`=`7`, worker `4`=`3`
  - phase `700` -> worker `3`=`7`, worker `4`=`13`
- Controlled failure/recovery window showed an exact `2 + 2` split:
  - worker `3` rows: `11443`, `11445`
  - worker `4` rows: `11444`, `11446`

## Honest Scope Statement
- This proof supports:
  - exactly `2` PM2 workers online
  - both workers receiving real traffic
- This proof does **not** claim perfect `50/50` balancing.
- Timestamp-window row counts during live load can include ambient production traffic, so they are treated as presence/distribution evidence rather than exact test-only percentages.

## Doc-Sync Impact
- Final status should cite this file when claiming dual-worker health.

## Boundary Compliance
- No worker count changes were made during the proof.
- PM2 remained at exactly `2` workers.

## Rollback / Re-run Safety
- Safe to re-run alongside the authenticated load harness.

## Auditor Gate
- Required input for `worker-health`, `runtime-deploy`, and `performance-loadtest`.

## Security Scan
- No secrets recorded.

## Acceptance Criteria Mapping
- PM2 exactly 2 workers: pass
- both workers measurably receive traffic: pass
- no fake 50/50 claim: pass

## Footer
- Worker verdict: `PASS WITH MEASURED DUAL-WORKER TRAFFIC`.
