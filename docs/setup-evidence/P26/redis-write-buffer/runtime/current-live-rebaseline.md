# P26.1 Current Live Rebaseline

Date: 2026-06-28
Operator workspace: `C:\Users\faizz\guinevere`
Target host: `root@49.12.82.34 -p 39999`

## What Was Done
- Re-checked the live 9Router runtime after the Redis Stream smoke-pass state.
- Re-verified PM2 worker count, Redis service, writer service, listener exposure, Tailscale reachability, public IPv4 block, stream backlog, and SQLite integrity.
- Re-checked recent service/log signals for writer crash-loop or active SQLite lock storm evidence.

## Files Changed
- None. This phase was runtime verification only.

## Validation Results
- `pm2 list` still shows exactly 2 online `9router` workers:
  - worker `3`, pid `56767`, restarts `0`
  - worker `4`, pid `56774`, restarts `0`
- `systemctl status redis-server` is `active (running)` and bound as `/usr/bin/redis-server 127.0.0.1:6379`.
- `systemctl status 9router-usage-writer.service` is `active (running)`.
- Listener proof from `ss -lntp`:
  - Redis only on `127.0.0.1:6379` and `[::1]:6379`
  - 9Router on `0.0.0.0:20128`
  - SSH still on `0.0.0.0:22` and `[::]:22`
- Tailscale proof from the local workstation:
  - `curl.exe -sS -o NUL -w "v1=%{http_code}" http://100.104.210.75:20128/v1` returned `401`
  - `curl.exe -sS -o NUL -w "models=%{http_code}" http://100.104.210.75:20128/v1/models` returned `401`
  - this is expected after the auth-protected PM2 cutover
- Public IPv4 boundary proof from the local workstation:
  - `Test-NetConnection 49.12.82.34 -Port 20128` returned `TcpTestSucceeded : False`
- Redis stream state at rebaseline:
  - `XLEN 9router:usage_events:v1` = `911`
  - `XINFO GROUPS 9router:usage_events:v1` = `consumers 1`, `pending 0`, `lag 0`
  - `XLEN 9router:usage_events:deadletter:v1` = `0`
- SQLite integrity proof:
  - `sqlite3 /var/lib/9router/db/data.sqlite 'pragma integrity_check;'` returned `ok`
- PM2 restart proof from `pm2 jlist`:
  - active worker restarts remain `0`
  - no current unstable restart growth observed during this rebaseline window

## Evidence Artifacts
- `pm2 list` snapshot:
  - `9router` worker count = `2`
  - both workers `online`
- `systemctl status redis-server --no-pager -l`:
  - `Active: active (running)`
  - `Status: "Ready to accept connections"`
- `systemctl status 9router-usage-writer.service --no-pager -l`:
  - `Active: active (running)`
  - startup lines only, no crash-loop markers
- `ss -lntp`:
  - `127.0.0.1:6379`
  - `[::1]:6379`
  - `0.0.0.0:20128`
- Local boundary probes:
  - Tailscale IP `100.104.210.75:20128` reachable and auth protected
  - public IPv4 `49.12.82.34:20128` blocked

## Doc-Sync Impact
- This file becomes the fresh baseline for Phases C through J.
- Later phases should cite this file instead of the earlier smoke-only verification when referring to the live state.

## Boundary Compliance
- PM2 `9router` worker count remains exactly `2`.
- Redis remains loopback-only.
- Public IPv4 `49.12.82.34:20128` remains blocked from the operator machine.
- Tailscale endpoint remains reachable from the operator machine.
- SSH remained up throughout the phase.

## Rollback / Re-run Safety
- Read-only runtime checks only.
- No service state was changed during this phase.
- Commands are safe to re-run.

## Design Decisions / Caveats
- The VPS runs `tailscaled` with `--tun=userspace-networking`. Curling the node's own Tailscale IP from the VPS itself produced a connection-reset path in `tailscaled` logs, but the operator workstation proved the external Tailscale path is reachable and now responds with `401 Unauthorized` on anonymous requests after the auth-protected cutover.
- After PM2 cutover to the standalone `server.js` runtime, anonymous requests now return `401 Unauthorized` on both `/v1` and `/v1/models`. That is treated as healthy reachability for the auth-protected live path, not a regression.
- Historical SQLite lock entries are still present in `/root/.pm2/logs/9router-error-0.log` from the pre-buffer era:
  - `SqliteError: database is locked`
  - `code: 'SQLITE_BUSY'`
- During this rebaseline there was no evidence of a current writer crash-loop. The writer log shows one intentional stop/start during the earlier parser-fix recovery and then a clean running state.
- Proxy-related upstream errors exist in `/root/.pm2/logs/9router-error-1.log`, but they are provider-path errors, not Redis/writer crash evidence.

## Auditor Gate
- Pending. This file is input to round-1 and round-2 audits.

## Security Scan
- No secrets were printed into this evidence file.
- Only status lines, listener bindings, counts, and non-secret log fragments were captured.

## Acceptance Criteria Mapping
- PM2 exactly 2 workers: pass
- Redis service healthy: pass
- Writer service healthy: pass
- Redis loopback-only: pass
- Tailscale endpoint works: pass
  - reachable and auth protected
- Public IPv4 remains blocked: pass
- Redis backlog/pending healthy at baseline: pass
- SQLite integrity check ok: pass
- No active writer crash loop at baseline: pass
- Historical SQLite lock residue exists and must be judged later in Phase E: noted

## Footer
- Rebaseline verdict: `LIVE OK WITH HISTORICAL SQLITE RESIDUALS`.
