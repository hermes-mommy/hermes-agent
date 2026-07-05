# P26 High-End 2-Worker Tuning - Final Runtime Audit Round 2

Date: 2026-06-27
Auditor: Codex runtime audit
Evidence root: `docs/setup-evidence/P26/highend-2worker-tuning`
VPS checked read-only: `root@49.12.82.34 -p 39999`
Verdict: **PASS WITH LIMITATION**

## 1. Scope

This round-2 audit reviewed the updated repair, verification, loadtest, and final runtime proof artifacts after round-1 findings. It also ran bounded read-only SSH/operator checks to confirm current runtime state without printing secrets or mutating the VPS.

Audited concerns:

- DB repair and current SQLite integrity.
- Loadtest artifacts fixed after round-1 empty-file failure.
- PM2 worker count remains exactly 2.
- Endpoint health from VPS and operator host.
- Restart loop and memory status.
- Post-load SQLite/runtime error scans.
- Scaffold violation closure.
- Unresolved strict worker-balance proof limitation.

## 2. Evidence Read

Read updated local evidence:

- `fixes/sqlite-repair-log.md`
- `fixes/round-1-fix-log.md`
- `verification/sqlite-integrity-investigation.md`
- `verification/sqlite-recovery-options.md`
- `verification/sqlite-repair-candidate-inspection.md`
- `verification/final-runtime-proof.md`
- `loadtest/baseline-loadtest.md`
- `loadtest/post-tuning-loadtest.md`
- `audits/round-1/runtime-audit.md`

## 3. Current Read-Only Runtime Checks

Commands were restricted to read-only runtime/status checks:

```bash
pm2 status --no-color
sqlite3 'file:/var/lib/9router/db/data.sqlite?mode=ro' 'PRAGMA integrity_check; PRAGMA journal_mode; PRAGMA wal_autocheckpoint;'
curl -sS -o /tmp/p26-r2-models.json -w 'local_http_code=%{http_code} time_total=%{time_total}\n' http://127.0.0.1:20128/v1/models
systemctl is-active tailscaled
sysctl net.core.somaxconn net.ipv4.ip_local_port_range
```

Operator host checks:

```powershell
curl.exe -sS -o NUL -w "operator_tailscale_http_code=%{http_code} time_total=%{time_total}\n" http://100.104.210.75:20128/v1/models
curl.exe -sS -o NUL -w "operator_public_http_code=%{http_code} exit=%{exitcode} time_total=%{time_total}\n" --connect-timeout 3 http://49.12.82.34:20128/v1/models
```

Current proof:

```text
captured_at=2026-06-27T18:28:08+07:00
SQLite integrity_check=ok
journal_mode=wal
wal_autocheckpoint=1000
local_http_code=200 time_total=0.023337
tailscaled=active
net.core.somaxconn = 4096
net.ipv4.ip_local_port_range = 32768 60999
operator_tailscale_http_code=200 time_total=0.412563
operator_public_http_code=000 exit=28 time_total=3.021462
```

Current PM2 status:

```text
id 0  9router  cluster  pid 43086  uptime 4m  restarts 5  online  cpu 0%  mem 195.3mb
id 1  9router  cluster  pid 43093  uptime 4m  restarts 5  online  cpu 0%  mem 230.2mb
```

Note: One attempted JSON projection command had shell quoting errors; it did not mutate state, did not print secrets, and was superseded by `pm2 status --no-color` plus existing `verification/final-runtime-proof.md`.

## 4. Round-1 Finding Resolution

### F1 - SQLite integrity failure

Status: **Fixed**

Evidence:

- `verification/sqlite-integrity-investigation.md` confirmed cold integrity failure with 9Router stopped and backed up current DB before repair.
- `verification/sqlite-recovery-options.md` identified the clean pre-mutation backup as the viable base; dump import candidate was not viable.
- `verification/sqlite-repair-candidate-inspection.md` showed repaired candidate integrity `ok` and expected table counts.
- `fixes/sqlite-repair-log.md` records the repaired DB swap, preservation of corrupt DB, live DB integrity `ok`, and restart of exactly 2 PM2 workers.
- `verification/final-runtime-proof.md` records final SQLite `ok`, WAL mode, endpoint 200, and marker-based no-new-error scan.
- Current read-only audit re-check returned SQLite `ok`.

### F2 - Empty loadtest artifacts

Status: **Fixed**

Evidence:

- `loadtest/baseline-loadtest.md`: 300 local `/v1/models` requests, concurrency 20, `statuses=200:300`, `success_rate=100.00%`, p50 0.200833s, p95 0.349287s, p99 0.456575s, SQLite `ok`, 0 new hard-error scan counts.
- `loadtest/post-tuning-loadtest.md`: 700 local `/v1/models` requests, concurrency 50, `statuses=200:700`, `success_rate=100.00%`, p50 0.391370s, p95 0.621673s, p99 0.660345s, SQLite `ok`, 0 new hard-error scan counts.

### F3 - Post-tuning SQLite/runtime error ambiguity

Status: **Fixed for audited `/v1/models` load path**

Evidence:

- Both loadtest artifacts use marker-based new-log-byte scans and record 0 new matches for SQLite lock/unhandledRejection patterns after load.
- `verification/final-runtime-proof.md` records a marker scan with 0 new error matches after a 100-request probe.

Limitation: This only proves the audited models endpoint/load path. It does not prove all real provider write paths under sustained production traffic.

### F4 - Scaffold violation handling open

Status: **Fixed**

Evidence:

- `fixes/round-1-fix-log.md` now marks Scaffold Violation 1 as `closed for scaffold handling`.
- It keeps the violation documented for traceability and cites corrected verification/PM2 restart evidence.

### F5 - PM2/process health

Status: **Still passing**

Evidence:

- Final proof and current audit show exactly two `9router` PM2 workers online.
- PM2 remains in cluster mode.
- Restart count is stable at 5 with no unstable restarts reported in final proof.
- Current memory is approximately 195.3 MB and 230.2 MB per worker, well below the configured memory restart limit.

## 5. Acceptance Criteria Mapping

| Criterion | Round-2 Result | Evidence |
|---|---:|---|
| Exactly 2 `9router` PM2 workers online | PASS | Current PM2 status and `final-runtime-proof.md` |
| Endpoint reachable at Tailscale `/v1/models` | PASS | Operator Tailscale HTTP 200 |
| Local `/v1/models` returns HTTP 200 | PASS | Current local HTTP 200; final proof HTTP 200 |
| No PM2 restart loop | PASS | Restart count stable at 5; no unstable restarts in final proof |
| Memory acceptable | PASS | 195.3 MB and 230.2 MB current worker memory |
| SQLite integrity check is `ok` | PASS | Repair log, final proof, and current audit re-check |
| Runtime artifact contains required PRAGMA/checkpoint patterns | PASS based on prior implementation evidence | `verification/post-tuning-snapshot.md` and implementation evidence |
| Recent audited load windows have 0 SQLite/unhandledRejection errors | PASS for `/v1/models` load path | Baseline/post loadtests and final marker proof |
| Loadtest has 0 HTTP failures and no worker-count regression | PASS WITH LIMITATION | 300/300 and 700/700 HTTP 200; 2 workers remained online |
| Strict 45/55 to 55/45 worker-balance proof | LIMITATION | `/v1/models` route lacks sufficient per-request worker logging |
| SSH still works | PASS | Read-only SSH audit completed |
| Tailscale still active | PASS | `systemctl is-active tailscaled` returned active |
| Public IPv4 20128 remains blocked | PASS | Operator public curl timed out |
| No secrets printed | PASS | No env dump, token, key, provider secret, or authorization header captured |

## 6. Worker-Balance Limitation

The final verdict must not claim strict worker-balance PASS. The updated loadtests prove:

- The service handled 300 requests at concurrency 20 and 700 requests at concurrency 50.
- All requests returned HTTP 200.
- PM2 retained exactly two online workers before and after load.
- No new SQLite lock/unhandledRejection errors appeared in marker scans.

They do not prove a 45/55 to 55/45 request distribution because the `/v1/models` route does not emit per-request worker logs sufficient to attribute each request to PM2 worker 0 vs worker 1. `loadtest/*` records `New Worker Prefix Counts` as insufficient (`out1` only), and `fixes/round-1-fix-log.md` explicitly carries this limitation.

Audit decision: strict worker-balance acceptance remains **LIMITATION**, not failure, because the plan allowed final status to include this limitation when logs are insufficient.

## 7. DB Repair Assessment

The DB repair is acceptable for this audit:

- Corrupt DB was confirmed cold and preserved.
- Repair candidate was built from clean pre-mutation backup plus readable current rows.
- Candidate integrity was `ok` before swap.
- Live DB integrity was `ok` after swap.
- Service restarted with exactly 2 workers.
- Final and current runtime checks still show SQLite integrity `ok`.

Caveat: The evidence indicates some data reconstruction occurred from readable rows and clean backup. This audit validates runtime integrity and service health, not semantic completeness of every historical analytics row beyond the captured counts.

## 8. Boundary Compliance

- No VPS mutation was performed during this round-2 audit.
- No service restart, PM2 mutation, DB write, firewall change, Tailscale change, sysctl write, or deployment action was performed by this auditor.
- No secrets, `.env` values, PM2 env values, provider keys, Authorization headers, cookies, or decrypted credentials were printed.
- Only this audit report file was written locally.

## 9. Final Verdict

**PASS WITH LIMITATION.**

The round-1 blockers are resolved: SQLite integrity is repaired and re-verified, loadtest artifacts are complete, endpoint health passes, PM2 remains exactly 2 workers, restart loop is absent, memory is healthy, and marker-based error scans are clean for the audited `/v1/models` load path.

The remaining limitation is strict worker-balance proof: the available route/logging does not prove a 45/55 to 55/45 worker split. Final claims should say worker count and load stability passed, while strict per-request balance remains unproven without instrumentation or a logged request path.

