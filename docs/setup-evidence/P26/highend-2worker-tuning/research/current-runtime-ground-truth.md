# P26 Current Runtime Ground Truth

Date: 2026-06-27
Evidence root: `docs/setup-evidence/P26/highend-2worker-tuning`
Snapshot source: `verification/pre-tuning-snapshot.md` plus read-only runtime code probe.

## What Was Done

Captured the live 9Router VPS state before mutation. The snapshot was read-only: no PM2 reload, no SQLite write, no sysctl write, no firewall edit, and no Tailscale change.

## Current Runtime

| Surface | Ground Truth |
|---|---|
| Host | `ninerouter-vps` |
| SSH target | `root@49.12.82.34 -p 39999` |
| Endpoint | `http://100.104.210.75:20128/v1` |
| 9Router version | `0.5.8` |
| PM2 mode | `cluster` |
| Worker count | exactly `2` |
| Worker PIDs at snapshot | `31108`, `31121` |
| PM2 script | `/root/9router/.next/standalone/custom-server.js` |
| PM2 cwd | `/root/9router/.next/standalone` |
| Node.js | `22.23.1` |
| Node env | `production` |
| Node heap arg | `--max-old-space-size=1843` |
| PM2 max memory restart | `1992294400` bytes, about `1900M` |
| Worker NOFILE | `65535/65535` |
| Tailscale IP | `100.104.210.75` |
| Tailscale service | active, userspace networking per security research |
| Firewall posture | targeted IPv4 DROP for `20128` on `venet0`; no reset/flush performed |
| Public IPv4 `20128` | blocked during research |
| SQLite DB path | `/var/lib/9router/db/data.sqlite` |
| App-facing DB symlink | `/root/.9router/db/data.sqlite` |
| SQLite journal mode | WAL |
| SQLite lock evidence | recent `SQLITE_BUSY`, `SQLITE_BUSY_SNAPSHOT`, and `database is locked` in PM2 logs |

## Runtime Code Location

PM2 runs from `.next/standalone`, not directly from the root source tree.

PRAGMA/checkpoint code appears in:

- `/root/9router/src/lib/db/schema.js`
- `/root/9router/src/lib/db/adapters/betterSqliteAdapter.js`
- `/root/9router/src/lib/db/adapters/nodeSqliteAdapter.js`
- `/root/9router/src/lib/db/adapters/bunSqliteAdapter.js`
- `/root/9router/.next/standalone/src/lib/db/schema.js`
- `/root/9router/.next/standalone/src/lib/db/adapters/betterSqliteAdapter.js`
- `/root/9router/.next/standalone/src/lib/db/adapters/nodeSqliteAdapter.js`
- `/root/9router/.next/standalone/src/lib/db/adapters/bunSqliteAdapter.js`
- compiled server chunks under `/root/9router/.next/standalone/.next/server/chunks/`

The compiled chunks include the old values:

- `PRAGMA mmap_size = 30000000;`
- `PRAGMA busy_timeout = 5000;`
- `wal_checkpoint(TRUNCATE)`

Therefore, a runtime-effective patch must include the standalone source and compiled chunk artifacts, or rebuild `.next/standalone` and then restart PM2.

## Baseline Risks

| Risk | Evidence | Handling |
|---|---|---|
| SQLite write lock | Recent PM2 logs show `SQLITE_BUSY` and `SQLITE_BUSY_SNAPSHOT` | Tune app connection PRAGMAs and reduce checkpoint contention |
| Per-worker checkpoint contention | Current adapter uses `wal_checkpoint(TRUNCATE)` timer per worker | Replace with `wal_checkpoint(PASSIVE)` |
| Unsupported OS sysctls | VPS exposes constrained `venet0`/limited sysctl surface | Do not force unsupported sysctl keys |
| Public endpoint exposure | App listens on `0.0.0.0:20128`; security depends on existing rules/Tailscale path | Do not touch firewall/Tailscale; verify public IPv4 remains blocked |
| Evidence leakage | Logs include model names/request IDs | Avoid raw secret/env dumps and keep evidence sanitized |

## Boundary Compliance

- No secrets or env values were printed.
- No raw provider credential rows were inspected.
- No firewall/Tailscale/SSH mutations occurred.
- No worker count change occurred.
- No restart occurred before this ground-truth artifact existed.

## Footer

Current runtime ground truth created for P26 high-end 2-worker tuning before any mutation.
