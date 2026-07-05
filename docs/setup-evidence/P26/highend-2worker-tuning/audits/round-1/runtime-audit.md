# P26 High-End 2-Worker Tuning - Runtime Audit Round 1

Date: 2026-06-27
Auditor: Codex runtime audit
Evidence root: `docs/setup-evidence/P26/highend-2worker-tuning`
VPS checked read-only: `root@49.12.82.34 -p 39999`
Verdict: **FAIL**

## 1. Scope

This audit reviewed the P26 high-end 2-worker tuning evidence and performed read-only runtime checks for:

- PM2 worker count equals 2.
- Endpoint health.
- Restart loop status.
- Memory posture.
- Runtime proof completeness.
- Loadtest proof.
- Scaffold violation handling.
- SQLite integrity and lock/error posture.

No VPS mutation, service restart, file edit, firewall change, Tailscale change, or secret-printing command was intentionally run.

## 2. Evidence Read

Read local evidence files:

- `plan/p26-highend-2worker-tuning-plan.md`
- `implementation/sqlite-tuning.md`
- `implementation/pm2-node-tuning.md`
- `implementation/os-network-tuning.md`
- `verification/pre-tuning-snapshot.md`
- `verification/post-tuning-snapshot.md`
- `verification/post-marker-sqlite-lock-verification.md`
- `verification/post-load-error-classification.md`
- `loadtest/baseline-loadtest.md`
- `loadtest/post-tuning-loadtest.md`
- `fixes/round-1-fix-log.md`

Key plan hard rejection criteria included: exactly 2 workers, reachable Tailscale endpoint, no restart loop, SQLite integrity `ok`, no post-tuning SQLite lock errors attributable to tuned window, loadtest evidence present, and no PASS claim without loadtest.

## 3. Runtime Commands Executed

Read-only commands were executed over SSH:

```bash
pm2 jlist | python3 -c '<safe field projection only>'
pm2 status --no-color
curl -sS -o /tmp/p26-audit-models.json -w 'local_http_code=%{http_code} time_total=%{time_total}\n' http://127.0.0.1:20128/v1/models
sqlite3 'file:/var/lib/9router/db/data.sqlite?mode=ro' 'PRAGMA integrity_check; PRAGMA journal_mode; PRAGMA wal_autocheckpoint; PRAGMA busy_timeout; PRAGMA mmap_size; PRAGMA cache_size;'
tail -n 200 /root/.pm2/logs/9router-error-*.log | grep -Eic 'SQLITE_BUSY|SQLITE_BUSY_SNAPSHOT|database is locked|unhandledRejection'
stat -c '%n size=%s mtime=%y' /root/.pm2/logs/9router-*.log
free -m
systemctl is-active tailscaled
sysctl net.core.somaxconn net.ipv4.ip_local_port_range
```

Operator host checks:

```powershell
curl.exe -sS -o NUL -w "operator_tailscale_http_code=%{http_code} time_total=%{time_total}\n" http://100.104.210.75:20128/v1/models
curl.exe -sS -o NUL -w "operator_public_http_code=%{http_code} exit=%{exitcode} time_total=%{time_total}\n" --connect-timeout 3 http://49.12.82.34:20128/v1/models
```

## 4. Runtime Evidence

Captured at VPS time `2026-06-27T18:17:16+07:00` to `2026-06-27T18:17:36+07:00`.

Safe PM2 projection:

```json
[
  {
    "pm_id": 0,
    "name": "9router",
    "pid": 39839,
    "status": "online",
    "exec_mode": "cluster_mode",
    "instances": 2,
    "restart_time": 5,
    "unstable_restarts": 0,
    "pm_uptime": 1782558682137,
    "node_args": ["--max-old-space-size=1843"],
    "max_memory_restart": 1992294400,
    "memory_mb": 217.5,
    "cpu": 0,
    "node_version": "22.23.1"
  },
  {
    "pm_id": 1,
    "name": "9router",
    "pid": 39852,
    "status": "online",
    "exec_mode": "cluster_mode",
    "instances": 2,
    "restart_time": 5,
    "unstable_restarts": 0,
    "pm_uptime": 1782558682303,
    "node_args": ["--max-old-space-size=1843"],
    "max_memory_restart": 1992294400,
    "memory_mb": 170.0,
    "cpu": 0,
    "node_version": "22.23.1"
  }
]
```

Endpoint checks:

```text
local_http_code=200 time_total=0.023578
models_count=45
operator_tailscale_http_code=200 time_total=0.487227
operator_public_http_code=000 exit=28 time_total=3.003677
```

Memory and network:

```text
Mem: total=4000MB used=456MB free=1MB buff/cache=3542MB available=3543MB
tailscaled=active
net.core.somaxconn = 4096
net.ipv4.ip_local_port_range = 32768 60999
```

SQLite integrity re-check:

```text
*** in database main ***
Tree 36 page 16963 cell 1: overflow list length is 27 but should be 320
Tree 34 page 168832 cell 0: invalid page number 218103808
Page 34827: never used
...
integrity_check line count: 75
quick_check reproduced the same first corruption lines
```

Recent PM2 error tail count:

```text
/root/.pm2/logs/9router-error-0.log 6
/root/.pm2/logs/9router-error-1.log 0
```

## 5. Findings

### F1 - SQLite integrity check currently fails

Severity: **Critical**

The plan requires SQLite DB integrity check output `ok`. Earlier evidence claimed `ok` in `verification/post-tuning-snapshot.md`, but current read-only audit checks twice returned structural integrity errors and `quick_check` reproduced the same class of errors. This violates a hard acceptance criterion and blocks PASS.

Impact: The tuned runtime may be serving `/v1/models`, but DB durability/integrity is not proven. Any final PASS would be unsafe until DB integrity is explained and remediated or proven to be a read-mode artifact by stronger evidence.

### F2 - Required loadtest evidence is missing/incomplete

Severity: **High**

`loadtest/baseline-loadtest.md` is only 28 bytes and contains only the header `# P26 baseline Loadtest`. `loadtest/post-tuning-loadtest.md` is 5 bytes and has no meaningful results. The plan requires at least 200 local `/v1/models` requests with concurrency 20 or equivalent, success/failure counts, timing summary, CPU/RAM before and after, and worker distribution evidence or limitation.

Impact: This directly triggers the hard rejection criterion: no final PASS without loadtest.

### F3 - Post-tuning SQLite/runtime error evidence is not clean enough for PASS

Severity: **High**

`implementation/sqlite-tuning.md` and `verification/post-tuning-snapshot.md` record filtered hard error count `6` after restart, while `verification/post-marker-sqlite-lock-verification.md` later records 0 new bytes after a marker. Current audit tail still counts 6 SQLite/unhandledRejection-related lines in `9router-error-0.log`.

Impact: The marker evidence is useful, but the evidence set still contains unresolved post-restart hard-error counts. Given F1 DB integrity failure, runtime status cannot be upgraded to PASS on the basis of marker-only log evidence.

### F4 - Scaffold violation handling remains open

Severity: **Medium**

`fixes/round-1-fix-log.md` records Scaffold Violation 1 for the missing `/root/9router/.next/standalone/src/lib/db/schema.js` syntax-check path. It documents a reasonable resolution path and later implementation evidence shows continued checks/restart, but the violation log still says: `Status: open until corrected verification and PM2 restart evidence are recorded.`

Impact: This is not the primary runtime blocker, but the scaffold violation is not formally closed in evidence and therefore the scaffold-handling requirement is incomplete.

### F5 - PM2 worker count, endpoint health, restart loop, memory, and network boundary pass current checks

Severity: Informational

Current read-only runtime proof shows exactly two `9router` workers online in `cluster_mode`, restart count stable at `5`, `unstable_restarts=0`, memory around 170-225 MB per worker under a 1.99 GB memory restart limit, local and Tailscale `/v1/models` HTTP 200, Tailscale active, and public IPv4 port 20128 blocked/timed out.

Impact: The process supervisor and endpoint layer look healthy, but this does not overcome the DB integrity and loadtest blockers.

## 6. Acceptance Criteria Mapping

| Criterion | Result | Evidence |
|---|---:|---|
| Exactly 2 `9router` PM2 workers online | PASS | Current PM2 safe projection shows pm_id 0 and 1 online, instances 2 |
| Endpoint reachable at Tailscale `/v1/models` | PASS | Operator `100.104.210.75:20128` returned HTTP 200 |
| Local `/v1/models` returns HTTP 200 | PASS | VPS local curl returned HTTP 200, 45 models |
| No PM2 restart loop | PASS | `restart_time=5`, `unstable_restarts=0`, uptime increasing |
| Memory acceptable | PASS | 170-225 MB per worker vs 1992294400 byte restart limit |
| SQLite integrity check is `ok` | FAIL | Current read-only `integrity_check` returns 75 lines of corruption/errors |
| Runtime artifact contains required PRAGMA/checkpoint patterns | PASS based on prior evidence | `post-tuning-snapshot.md` counts required patterns and old-pattern PASS |
| Recent post-tuning log window has 0 SQLite/unhandledRejection errors | NEEDS REVIEW | Marker file says 0 new bytes; other post-restart/current tail evidence still counts 6 |
| Loadtest has 0 HTTP failures and no worker-count regression | FAIL | Loadtest files have no usable data |
| SSH still works | PASS | Read-only SSH audit completed |
| Tailscale still active | PASS | `systemctl is-active tailscaled` returned active |
| Public IPv4 20128 remains blocked | PASS | Operator public curl timed out |
| No secrets printed | PASS WITH NOTE | Audit avoided env dumps; existing `post-load-error-classification.md` contains redacted token wording |

## 7. Scaffold Violation Handling

The violation was recorded, which satisfies the requirement not to silently sanitize scaffold violations. However, the status remains open in `fixes/round-1-fix-log.md`. The implementation evidence should explicitly close or supersede it after corrected verification, or keep it open as a known unresolved process defect.

Audit decision: **NEEDS REVIEW**, not PASS.

## 8. Runtime Proof Verdict

Runtime service liveness is proven. Runtime correctness is not proven.

The audit cannot pass because:

1. Current SQLite integrity checks fail.
2. Loadtest evidence is effectively absent.
3. Post-restart SQLite/unhandledRejection evidence remains ambiguous.
4. Scaffold violation handling is documented but not closed.

## 9. Required Remediation Before PASS

1. Investigate SQLite integrity failure using non-destructive backup-first workflow; do not mutate the live DB without explicit approved recovery plan.
2. Produce complete baseline/post loadtest evidence or clearly mark this tuning as failed/partial.
3. Reconcile log-window evidence with marker-based evidence and prove zero new SQLite lock/unhandledRejection errors after a clean marker under load.
4. Close or explicitly carry forward Scaffold Violation 1 in the fix log.
5. Re-run runtime audit round 2 after remediation.

## 10. Boundary Compliance

- No secrets, API keys, provider credentials, Authorization headers, cookies, or PM2 env values were intentionally printed.
- No services were restarted.
- No files were edited except this audit report.
- No firewall, Tailscale, sysctl, DB, PM2, or application state mutation was intentionally performed.

## 11. Final Verdict

**FAIL.** PM2/process health passes, but P26 high-end 2-worker tuning cannot be accepted because SQLite integrity currently fails and required loadtest evidence is missing.

