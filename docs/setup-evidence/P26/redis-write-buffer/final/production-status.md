# P26.1 Production Status

Date: 2026-06-28
Status: `P26.1 REDIS WRITE BUFFER - PASS WITH LIMITATION`

## Runtime Snapshot
- PM2 `9router`: exactly `2` workers online (`pm_id 3`, `pm_id 4`), restart count `0` in the current post-cutover runtime
- Active PM2 entrypoint: `/root/9router/.next/standalone/server.js`
- Writer service: `active`
- Redis listener: loopback-only on `127.0.0.1:6379` and `[::1]:6379`
- Redis stream status at final spot-check:
  - stream length `911`
  - `pending 0`
  - `lag 0`
  - deadletter length `0`
- SQLite integrity: `ok`
- Public IPv4 `49.12.82.34:20128`: blocked from operator machine
- Tailscale endpoint `100.104.210.75:20128`: reachable and auth protected (`401` on anonymous `/v1` and `/v1/models`)

## Validated Runtime Results
- Authenticated loadtest:
  - phase `50`: `50/50` success
  - phase `200`: `200/200` success
  - phase `700`: `700/700` success
- Failure/recovery:
  - `4/4` authenticated requests succeeded while writer was intentionally stopped
  - stream length grew during outage and drained after restart
  - recovery rows landed with non-empty `streamId`
- SQLite lock verdict: `IMPROVED_WITH_RESIDUAL`
- Worker verdict: `PASS WITH MEASURED DUAL-WORKER TRAFFIC`

## Audit Summary
- Round 1:
  - no CRITICAL/HIGH findings
  - 2 material evidence-quality findings were logged and fixed
- Round 2:
  - no unresolved CRITICAL/HIGH findings
  - architecture and DB write-path gaps closed

## Accepted Limitations
1. The authoritative deployed 9Router source is the VPS worktree at `/root/9router`, not this local repo.
2. Historical SQLite lock residue remains in old PM2 logs from the pre-buffer runtime, so the honest SQLite verdict is not `CLEAN`.
3. Worker proof demonstrates dual-worker traffic, not an exact balancing ratio.

## Status Reason
This is `PASS WITH LIMITATION`, not `PRODUCTION PASS`, because the runtime is healthy and the final gates passed, but the authoritative deployed source remains split from this workspace and the SQLite story is "improved with residual history" rather than perfectly clean.
