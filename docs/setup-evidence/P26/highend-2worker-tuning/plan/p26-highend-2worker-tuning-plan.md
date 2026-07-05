# P26 High-End 2-Worker Tuning Plan

Date: 2026-06-27
Evidence root: `docs/setup-evidence/P26/highend-2worker-tuning`
Endpoint: `http://100.104.210.75:20128/v1`
VPS: `root@49.12.82.34 -p 39999`

## Verdict

Executable plan approved for controlled mutation after pre-snapshot and research. The main tuning target is SQLite write contention inside the current 2-worker PM2 runtime. PM2/Node and NOFILE are already close to target. OS/network tuning is intentionally minimal because the VPS exposes a constrained `venet0` sysctl surface and unsupported keys must not be persisted.

## Research Inputs

- `research/current-runtime-ground-truth.md`
- `research/sqlite-lock-analysis.md`
- `research/pm2-node-runtime-analysis.md`
- `research/os-network-tuning-analysis.md`
- `research/security-network-analysis.md`
- `research/loadtest-design-analysis.md`
- `research/evidence-passfail-analysis.md`
- `verification/pre-tuning-snapshot.md`

## Binding Decisions

| Decision | Binding |
|---|---|
| Worker count | Must remain exactly `2` |
| VPS spec | No upgrade |
| Endpoint | Must remain `http://100.104.210.75:20128/v1` |
| Tailscale | Do not stop, restart, reset, or change mode |
| Firewall | Read-only verification only; no reset, flush, delete, save, or default-policy change |
| SQLite DB | Single DB only: `/var/lib/9router/db/data.sqlite` |
| App analytics | Do not delete/disable usage/dashboard analytics |
| PM2 restart scope | Only `9router` may be reloaded/restarted if needed |
| OS/network | Keep existing `net.core.somaxconn=4096`; do not force unsupported sysctls |
| Runtime artifact | Patch `/root/9router/src`, `/root/9router/.next/standalone/src`, and compiled chunks containing old PRAGMA/checkpoint strings |

## Dependency Map

1. Step A: Backup and mutation preflight. Sequential.
2. Step B: SQLite runtime patch. Depends on Step A.
3. Step C: PM2/Node verification and restart. Depends on Step B.
4. Step D: OS/network no-op verification. Can run after Step C.
5. Step E: Post-tuning runtime snapshot. Depends on Step C and D.
6. Step F: Baseline/post loadtest. Depends on Step E.
7. Step G: Audit round 1. Depends on Step F.
8. Step H: Fix valid findings. Depends on Step G, only if needed.
9. Step I: Audit round 2 and final report. Depends on Step G/H.

Parallelism: implementation is sequential because all runtime changes touch the same service and shared SQLite writer behavior. Audit specialists may run in parallel after Step F.

## Collision Scan

| Surface | Collision | Mitigation |
|---|---|---|
| SQLite DB file | Shared by two workers | Backup first; use SQLite backup API; do not raw-copy live DB as sole backup |
| Runtime source and standalone artifact | Multiple files represent same adapter logic | Parent owns all runtime patching in one step |
| PM2 state | Shared service supervisor | One restart/reload window only |
| Firewall/Tailscale/SSH | Connectivity-critical | Read-only only |
| Evidence docs | Shared output tree | Parent writes plan/final; sub-agents write assigned audit files |

## Implementation Design

### Step A: Backup

Create backups on VPS under `/root/p26-highend-2worker-tuning-backups/<timestamp>/`:

- SQLite backup via `.backup`.
- PM2 `jlist` and `/root/.pm2/dump.pm2`.
- `pm2-root.service` unit and drop-ins via `systemctl cat`.
- `/etc/sysctl.d/99-9router-hightraffic.conf` if present.
- Runtime files to be patched from `/root/9router/src`, `/root/9router/.next/standalone/src`, and matching compiled chunks.

### Step B: SQLite Runtime Patch

Patch PRAGMA block to:

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA temp_store = MEMORY;
PRAGMA mmap_size = 268435456;
PRAGMA cache_size = -64000;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 30000;
PRAGMA wal_autocheckpoint = 10000;
```

Patch checkpoint behavior from `wal_checkpoint(TRUNCATE)` to `wal_checkpoint(PASSIVE)` in active better/node/bun adapters and compiled chunks.

Do not introduce empty catches beyond existing upstream style in this runtime hotfix; record existing empty catches as pre-existing upstream pattern and do not widen them.

### Step C: PM2/Node

Keep:

- `instances=2`
- `cluster_mode`
- `NODE_ENV=production`
- `--max-old-space-size=1843`
- `max_memory_restart ~= 1900M`
- `NOFILE=65535`

Run `pm2 restart 9router --update-env` or `pm2 reload 9router --update-env` only after backups. Use restart if compiled runtime patch requires clean process load. Then `pm2 save` if and only if workers return healthy with exactly 2 online.

### Step D: OS/Network

No broad kernel tuning. Verify existing `net.core.somaxconn=4096` and record unsupported `tcp_fin_timeout`/`tcp_tw_reuse` as intentionally not applied.

### Step E/F: Verification and Loadtest

Run local and Tailscale `/v1/models` checks, PM2 worker/restart checks, SQLite PRAGMA/lock checks, and a bounded `/v1/models` loadtest. Real model smoke is allowed only if existing configured 9Router route works without printing keys; if auth key is not safely available, mark real smoke as not run and final status cannot exceed PASS WITH LIMITS.

## Exact Commands

Commands are embedded in the step scaffolds below and must be captured into the requested evidence files.

## Token and Secret Handling

- Do not run `pm2 env`.
- Do not print `.env`, provider tables, API key rows, Authorization headers, cookies, JWTs, or Tailscale state files.
- Evidence may include model IDs, HTTP status codes, counts, timings, PM2 process metadata, and sanitized error counts.
- Any accidental secret-like output must be redacted before writing evidence and recorded as a violation.

## Rollback Plan

1. If endpoint fails immediately after restart, restore patched runtime files from the timestamped backup and restart only `9router`.
2. If PM2 state breaks, restore `/root/.pm2/dump.pm2` from backup and run `pm2 resurrect`.
3. If DB integrity fails, stop only PM2/9Router, preserve bad DB copy, restore SQLite `.backup`, verify integrity, start PM2.
4. Do not change firewall/Tailscale/SSH as rollback.

## Acceptance Criteria

- Exactly 2 `9router` PM2 workers online.
- Endpoint reachable at `http://100.104.210.75:20128/v1/models`.
- Local `/v1/models` returns HTTP 200.
- No PM2 restart loop.
- SQLite DB integrity check is `ok`.
- Runtime artifact contains `busy_timeout = 30000`, `wal_autocheckpoint = 10000`, `mmap_size = 268435456`, and `wal_checkpoint(PASSIVE)`.
- Recent post-tuning log window has 0 `SQLITE_BUSY`, `SQLITE_BUSY_SNAPSHOT`, `database is locked`, and `unhandledRejection`.
- Loadtest has 0 HTTP failures and no worker-count regression.
- SSH still works.
- Tailscale still active.
- Public IPv4 `20128` remains blocked.
- No secrets printed.

## Hard Rejection Criteria

- Worker count is not exactly 2.
- SSH to `root@49.12.82.34 -p 39999` fails.
- Tailscale endpoint fails after tuning.
- Firewall is flushed/reset or SSH rules deleted.
- Any secret appears in evidence.
- No backup before mutation.
- Final claims PASS while post-tuning `SQLITE_BUSY` still appears, unless final status is `P26 TUNING PARTIAL - APP WRITE PATH PATCH REQUIRED`.
- Final claims PASS without loadtest.

## Per-Step Verification Scaffold

### Step A Scaffold - Backup

Expected Files:

- `implementation/sqlite-tuning.md`
- `implementation/pm2-node-tuning.md`
- `implementation/os-network-tuning.md`

Forbidden Patterns:

- `(?i)(sk-[A-Za-z0-9]|authorization: bearer|api[_-]?key\\s*=\\s*[^<]|token\\s*=\\s*[^<]|password\\s*=\\s*[^<])`
- `iptables -F|iptables --flush|ufw reset|tailscale (down|logout|up|set)|systemctl (stop|restart) tailscaled`

Required Commands:

- `ssh -p 39999 root@49.12.82.34 "test -f /var/lib/9router/db/data.sqlite"` -> exit 0
- `sqlite3 /var/lib/9router/db/data.sqlite ".backup '<backup-path>/data.sqlite.backup'"` -> exit 0
- `sqlite3 'file:<backup-path>/data.sqlite.backup?mode=ro' 'PRAGMA integrity_check;'` -> output `ok`
- `pm2 jlist > <backup-path>/pm2-jlist.json` -> exit 0
- `cp -a /root/.pm2/dump.pm2 <backup-path>/dump.pm2` when present -> exit 0 or documented absent

Evidence Requirements:

- Backup path recorded in `implementation/sqlite-tuning.md`.
- Restore commands recorded in `implementation/sqlite-tuning.md`.

Hard Rejection Criteria:

- Any mutation happens before backup evidence exists.
- SQLite backup integrity is not `ok`.

### Step B Scaffold - SQLite Runtime Patch

Expected Files:

- Runtime files on VPS under `/root/9router/src`, `/root/9router/.next/standalone/src`, `/root/9router/.next/standalone/.next/server/chunks/`
- `implementation/sqlite-tuning.md`

Forbidden Patterns:

- `as any|@ts-ignore|@ts-expect-error|# type: ignore`
- `wal_checkpoint\\(TRUNCATE\\)` in patched active runtime files/chunks
- `PRAGMA busy_timeout = 5000`
- `PRAGMA mmap_size = 30000000`

Required Commands:

- `grep -RIn 'PRAGMA busy_timeout = 30000' /root/9router/src /root/9router/.next/standalone/src /root/9router/.next/standalone/.next/server/chunks` -> exit 0
- `grep -RIn 'PRAGMA wal_autocheckpoint = 10000' /root/9router/src /root/9router/.next/standalone/src /root/9router/.next/standalone/.next/server/chunks` -> exit 0
- `grep -RIn 'wal_checkpoint(TRUNCATE)' <patched-file-list>` -> exit non-zero
- `node --check /root/9router/src/lib/db/schema.js` -> exit 0
- `node --check /root/9router/src/lib/db/adapters/betterSqliteAdapter.js` -> exit 0

Evidence Requirements:

- `implementation/sqlite-tuning.md`
- `verification/post-tuning-snapshot.md`
- `audits/round-1/sqlite-lock-audit.md`

Hard Rejection Criteria:

- Runtime still contains old PRAGMA values in active files.
- Syntax check fails.

### Step C Scaffold - PM2/Node Restart and Verification

Expected Files:

- `implementation/pm2-node-tuning.md`
- `verification/post-tuning-snapshot.md`

Forbidden Patterns:

- `pm2 scale 9router 3|pm2 scale 9router 4|instances[=: ]+[3-9]`
- `systemctl restart tailscaled|systemctl stop tailscaled`

Required Commands:

- `pm2 restart 9router --update-env` -> exit 0 after backup and patch
- `pm2 status --no-color` -> exactly 2 `9router` online workers
- `pm2 describe 9router --no-color` -> cluster mode and node env production
- `curl -fsS http://127.0.0.1:20128/v1/models` -> exit 0
- operator host `curl http://100.104.210.75:20128/v1/models` -> HTTP 200

Evidence Requirements:

- Restart timestamp and pre/post PM2 restart counts recorded.
- Worker count proof recorded.
- Endpoint proof recorded.

Hard Rejection Criteria:

- Worker count not 2.
- Endpoint not reachable.
- Restart loop or unstable restart observed.

### Step D Scaffold - OS/Network Verification

Expected Files:

- `implementation/os-network-tuning.md`
- `verification/post-tuning-snapshot.md`

Forbidden Patterns:

- `iptables -F|iptables --flush|iptables -D|ufw reset|nft flush`
- `sysctl -w net.ipv4.tcp_fin_timeout|sysctl -w net.ipv4.tcp_tw_reuse` when unsupported

Required Commands:

- `sysctl net.core.somaxconn` -> `4096`
- `sysctl net.ipv4.ip_local_port_range` -> recorded
- `systemctl is-active tailscaled` -> `active`
- `iptables -S INPUT` -> read-only output captured

Evidence Requirements:

- Unsupported sysctls documented as intentionally not applied.
- Tailscale/firewall read-only state recorded.

Hard Rejection Criteria:

- Firewall/Tailscale/SSH mutated.
- `somaxconn` lower than 4096.

### Step E/F Scaffold - Runtime and Load Verification

Expected Files:

- `verification/post-tuning-snapshot.md`
- `loadtest/baseline-loadtest.md`
- `loadtest/post-tuning-loadtest.md`

Forbidden Patterns:

- Secret-like values from Authorization/API keys.
- High-rate real-provider load loops.

Required Commands:

- Baseline/post `/v1/models` load: at least 200 local requests with concurrency 20 or equivalent.
- Post PM2 status: exactly 2 workers online.
- Post log scan: 0 new `SQLITE_BUSY`, `SQLITE_BUSY_SNAPSHOT`, `database is locked`, `unhandledRejection`.
- SQLite integrity: `PRAGMA integrity_check;` -> `ok`.

Evidence Requirements:

- p50/p95/p99 or equivalent timing summary.
- HTTP success/failure counts.
- CPU/RAM before and after.
- Worker distribution evidence from logs or per-worker PM2 counters.

Hard Rejection Criteria:

- No loadtest evidence.
- Any new post-tuning SQLite lock error attributable to tuned window.
- Worker split strongly imbalanced outside 45/55 to 55/45 when request logs can prove distribution; if logs are insufficient, final status must include limitation.

## Auditor Matrix

Round 1:

- `audits/round-1/runtime-audit.md`
- `audits/round-1/sqlite-lock-audit.md`
- `audits/round-1/worker-balance-audit.md`
- `audits/round-1/security-network-audit.md`
- Additional PM2 memory/evidence findings may be folded into runtime audit.

Round 2:

- `audits/round-2/final-runtime-audit.md`

## Tracker Sync Plan

No roadmap/ADR updates are required unless tuning changes reveal an architecture conflict. Final evidence must be written to `final/p26-highend-2worker-tuning-final-report.md`.

## Caveats

- `SQLITE_BUSY_SNAPSHOT` may require deeper app write-path retry if PRAGMA/checkpoint tuning is insufficient.
- Real model smoke may be skipped if no safe key path exists; final status then becomes PASS WITH UPSTREAM LIMITS or PARTIAL depending runtime evidence.
- Security research found SSH hardening issues, but hardening is out of scope because it risks connectivity and requires separate approval.

## Execution Checklist

- [x] AGENTS.md read.
- [x] ADR index and PersonaSafetyPolicy read.
- [x] Pre-tuning snapshot exists.
- [x] Research reports read by parent.
- [x] Collision scan completed.
- [ ] Backups created.
- [ ] SQLite runtime patched.
- [ ] PM2 restarted with exactly 2 workers.
- [ ] OS/network read-only verification captured.
- [ ] Post-tuning snapshot captured.
- [ ] Loadtest captured.
- [ ] Round-1 audits completed.
- [ ] Valid findings fixed.
- [ ] Round-2 audit completed.
- [ ] Final report written.

## Footer

Planner gate for Guinevere P26 high-end 2-worker tuning.
