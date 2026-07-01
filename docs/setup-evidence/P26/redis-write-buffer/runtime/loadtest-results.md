# P26.1 Loadtest Results

Date: 2026-06-28
Workspace: `C:\Users\faizz\guinevere`
Live target: `root@49.12.82.34 -p 39999`

## What Was Done
- Re-ran the full production-path loadtest after cutting PM2 over from the stale deleted standalone bundle to the current `/root/9router/.next/standalone/server.js`.
- Used an active API key loaded in-memory from the live SQLite `apiKeys` table for authenticated requests over Tailscale.
- Mixed high-volume `GET /v1/models` traffic with light `POST /v1/chat/completions` traffic against model alias `mimo`.

## Files Changed
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\loadtest-results.raw.json`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\loadtest-results.md`

## Validation Results
- All 3 phases completed with full request success:
  - `50/50`
  - `200/200`
  - `700/700`
- PM2 stayed at exactly `2` online workers before and after every phase.
- PM2 total restart delta stayed `0` for every phase.
- Redis deadletter stayed `0`.
- SQLite busy-count delta stayed `0` in every phase.
- Public IPv4 `49.12.82.34:20128` stayed blocked from the operator machine.

## Phase Metrics

| Phase | Requests | Success | Failure | `/v1/models` p50 / p95 / p99 | `/v1/chat/completions` p50 / p95 / p99 |
|---|---:|---:|---:|---|---|
| 50 | 50 | 50 | 0 | `235.13 / 550.91 / 609.06 ms` | `3035.72 / 17621.41 / 17621.41 ms` |
| 200 | 200 | 200 | 0 | `252.03 / 572.35 / 654.09 ms` | `2846.13 / 4007.16 / 4007.16 ms` |
| 700 | 700 | 700 | 0 | `339.89 / 701.80 / 972.66 ms` | `3183.90 / 8113.39 / 11220.37 ms` |

## Buffer / Throughput Evidence
- Phase `50`:
  - before: `len=592 pending=0 lag=0`
  - peak: `len=599 pending=0 lag=0`
  - after: `len=599 pending=0 lag=0 deadletter=0`
- Phase `200`:
  - before: `len=601 pending=0 lag=0`
  - peak: `len=611 pending=0 lag=0`
  - after: `len=611 pending=0 lag=0 deadletter=0`
- Phase `700`:
  - before: `len=613 pending=0 lag=0`
  - peak: `len=637 pending=0 lag=0`
  - after: `len=637 pending=0 lag=0 deadletter=0`

Interpretation:
- The stream length continued to advance under live authenticated traffic.
- Pending always drained back to `0`.
- No deadletter growth occurred.

## Worker / PM2 Evidence
- PM2 workers stayed online as:
  - `pm_id=3`, pid `56767`
  - `pm_id=4`, pid `56774`
- PM2 HTTP request metrics increased on both workers during load:
  - Phase `50` after snapshot:
    - worker `3` -> `httpReqPerMin=0.35`
    - worker `4` -> `httpReqPerMin=0.19`
  - Phase `200` after snapshot:
    - worker `3` -> `httpReqPerMin=1.99`
    - worker `4` -> `httpReqPerMin=0.78`
  - Phase `700` after snapshot:
    - worker `3` -> `httpReqPerMin=3.42`
    - worker `4` -> `httpReqPerMin=3.68`
- Usage rows in the sampled windows also showed both worker IDs:
  - Phase `50`: worker `3`=`4`, worker `4`=`1`
  - Phase `200`: worker `3`=`7`, worker `4`=`3`
  - Phase `700`: worker `3`=`7`, worker `4`=`13`

## System Load
- Phase `700` was the heaviest authenticated run and still completed with:
  - 2 PM2 workers online
  - 0 restart growth
  - 0 SQLite busy growth
  - 0 deadletter growth

## Reachability / Boundary Proof
- Tailscale path remained reachable on the production port.
- Anonymous `GET /v1/models` now returns `401 Unauthorized`, which is expected after the current auth-protected runtime cutover.
- The authenticated load harness proved the real Tailscale request path with `915/915` successful responses.
- Public IPv4 `49.12.82.34:20128` remained blocked from the operator machine after the test.

## Doc-Sync Impact
- This file supersedes the earlier unauthenticated post-cutover probe and the pre-cutover stale-runtime loadtest attempt.
- Final production status must cite this authenticated run, not the earlier stale or anonymous runs.

## Boundary Compliance
- PM2 worker count remained exactly `2`.
- No firewall or public exposure changes were made.
- No secrets were written into this evidence file.

## Rollback / Re-run Safety
- The loadtest is re-runnable.
- It requires an active API key in-memory at runtime because the live path is auth protected.

## Design Decisions / Caveats
- Chat latency is materially higher than `/v1/models`, which is expected because the chat sample hits upstream model execution while `/v1/models` is a lighter metadata path.
- Worker-row counts can include ambient live traffic in the same timestamp window, so they are evidence of both workers receiving traffic, not a strict test-only split.

## Auditor Gate
- Required input for `performance-loadtest`, `worker-health`, `runtime-deploy`, and `evidence-docs`.

## Security Scan
- The authenticated run used an active API key loaded only into process environment.
- No API key value was persisted into evidence.

## Acceptance Criteria Mapping
- Real 50/200/700 loadtest: pass
- 2 PM2 workers before/after: pass
- restart storm absent: pass
- Redis pending drains: pass
- deadletter stable: pass
- SQLite lock growth absent: pass
- Tailscale production path works: pass
- public IPv4 remains blocked: pass

## Footer
- Loadtest verdict: `PASS`.
