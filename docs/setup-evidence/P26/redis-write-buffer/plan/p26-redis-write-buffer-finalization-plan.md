# P26.1 Redis Write Buffer Continuation Finalization Plan

Date: 2026-06-28
Workspace: `C:\Users\faizz\guinevere`
Target host: `root@49.12.82.34 -p 39999`
Evidence root: `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer`
Planner scope: continuation finalization only, from current smoke-pass state to final status.

## 1. Planner Inputs

Required inputs read before this plan:

1. `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\evidence\implementation-verification.md`
2. `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\plan\p26-redis-write-buffer-plan.md`
3. `C:\Users\faizz\.codex\attachments\e116ef6c-b6b9-4076-b718-d6da683472f3\pasted-text.txt`

Supplemental context read to keep this plan concrete:

4. `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\preflight\current-runtime-ground-truth.md`
5. `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\research\research-synthesis.md`
6. local staging inventory under `C:\Users\faizz\guinevere\.codex\staging\p26-redis-write-buffer\`

## 2. Current Verified State

This continuation plan starts from the already-proven live state below. It must not restart P26.1 from zero.

- Redis Stream buffer is live on the 9Router VPS.
- `9router-usage-writer.service` is active.
- PM2 `9router` remains exactly 2 workers.
- Smoke pass already proved publish -> writer consume -> SQLite row inserted -> pending back to 0.
- The `XREADGROUP` response-shape bug has already been fixed.
- Existing runtime proof is in `evidence/implementation-verification.md`.
- The local Guinevere workspace does **not** contain the live `/root/9router` source tree.
- Local staging contains P26 artifacts (`usageBuffer.js`, `usage-writer.mjs`, `smoke-buffer.mjs`, service unit, helper scripts), so source-of-truth clarity is now a first-class finalization requirement.

## 3. Objective and Final Gate

Finish P26.1 from "core implemented, smoke pass" to one of these honest final states:

- `P26.1 REDIS WRITE BUFFER - PRODUCTION PASS`
- `P26.1 REDIS WRITE BUFFER - PASS WITH LIMITATION`
- `P26.1 REDIS WRITE BUFFER - BLOCKED`
- `P26.1 REDIS WRITE BUFFER - ROLLED BACK`

No final PASS claim is allowed without:

- fresh runtime rebaseline
- source-of-truth resolution
- real loadtest evidence
- failure/recovery proof
- SQLite lock verdict
- worker-health verdict
- round-1 audit
- fix wave
- round-2 audit
- final report and rollback instructions

## 4. Scope

In scope:

- Runtime rebaseline against the current live VPS
- Source-of-truth and deployed artifact clarity
- Loadtest and backlog-drain proof
- Failure/recovery proof
- SQLite lock proof
- Worker-health proof
- Two audit rounds and one fix wave
- Final P26 README/final report/final status docs
- Optional `PROGRESS.md` / `CHECKLIST.md` sync only if P26 tracking is intentionally added

Out of scope:

- Re-implementing the buffer
- Changing PM2 worker count
- Firewall resets or UFW/iptables flushes
- Tailscale changes
- Provider/model/combo changes
- Touching Guinevere VPS/P19/P20/P22/P23/P24 surfaces
- Silent rollback

## 5. Binding Decisions

1. Continue from the live implementation. Do not rollback unless a hard rejection criterion forces it.
2. Keep PM2 `9router` at exactly 2 workers for every phase.
3. Redis must remain loopback-only.
4. Public IPv4 `49.12.82.34:20128` must remain blocked throughout.
5. Tailscale endpoint `http://100.104.210.75:20128/v1` must remain reachable.
6. Runtime evidence wins over static assumptions.
7. Source-of-truth ambiguity is blocking for `PRODUCTION PASS`.
8. The local workspace currently looks like an evidence/control repo, not the deployed 9Router source tree. Phase B must say exactly where the authoritative source lives.
9. `PROGRESS.md` and `CHECKLIST.md` currently show P26 as reserved, so tracker edits are conditional and must not be done by habit.

## 6. Atomic Phase Map and Dependencies

| Phase | Purpose | Output | Depends On | Mode |
|---|---|---|---|---|
| A | Rebaseline current live state | `runtime/current-live-rebaseline.md` | none | sequential |
| B | Source-of-truth sync check | `runtime/source-sync-check.md` (+ manifest if needed) | none | parallel with A |
| C | Real loadtest | `runtime/loadtest-results.md` | A | sequential |
| D | Failure/recovery proof | `runtime/failure-recovery-proof.md` | A, C | sequential |
| E | SQLite lock proof | `runtime/sqlite-lock-proof.md` | C, D | sequential |
| F | Worker health proof | `runtime/worker-health-proof.md` | C | sequential |
| G | Audit round 1 | `audits/round-1/*.md` | A, B, C, D, E, F | audit-batch parallel |
| H | Fix wave for round-1 findings | `fixes/round-1-fix-log.md` | G | sequential per finding |
| I | Audit round 2 | `audits/round-2/*.md` | H | audit-batch parallel |
| J | Finalization | `final/*.md`, `README.md`, optional tracker sync | I | sequential |

Important dependency notes:

- Phase B can run beside A because it writes different files and does not change runtime state.
- Phases C, D, E, and F must share one runtime owner to avoid test collision.
- Phase G and Phase I are the main parallelization windows.
- Phase H is a coordination phase: every valid finding becomes its own micro-fix task with one owner, one surface, one re-check.

## 7. Collision Scan

### 7.1 Runtime-state collisions

| Surface | Collision Risk | Owner Rule |
|---|---|---|
| `pm2 list` / PM2 health | shared runtime read | A/C/F/J may read; no write allowed |
| `9router-usage-writer.service` | stop/start risk | D only may stop/start it |
| Redis stream state | shared runtime read/write via requests | C and D only may intentionally change backlog |
| SQLite row counts/log windows | shared runtime read | C/D/E/F may read; only request traffic may mutate |
| public/Tailscale endpoint reachability | shared runtime read | A/C/J may probe |

### 7.2 Evidence-file collisions

| Surface | Collision Risk | Owner Rule |
|---|---|---|
| `runtime/current-live-rebaseline.md` | single file | A only |
| `runtime/source-sync-check.md` | single file | B only |
| `runtime/deployed-artifact-manifest.md` | single file | B only |
| `runtime/loadtest-results.md` | single file | C only |
| `runtime/failure-recovery-proof.md` | single file | D only |
| `runtime/sqlite-lock-proof.md` | single file | E only |
| `runtime/worker-health-proof.md` | single file | F only |
| `audits/round-1/*.md` | one file per auditor | parallel safe |
| `fixes/round-1-fix-log.md` | shared finding log | H coordinator only |
| `audits/round-2/*.md` | one file per auditor | parallel safe |
| `final/*.md` and `README.md` | shared summary docs | J only |
| `PROGRESS.md`, `CHECKLIST.md` | shared global trackers | J only, conditional |

### 7.3 Source collisions

Phase B must explicitly determine whether the authoritative deployed source is:

- only `/root/9router` on the VPS
- mirrored in `C:\Users\faizz\guinevere\.codex\staging\p26-redis-write-buffer\`
- synced elsewhere in the Guinevere repo
- or split across more than one location

No final PASS if this remains unclear.

## 8. Evidence Matrix

| Phase | Exact Evidence Path(s) |
|---|---|
| A | `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\current-live-rebaseline.md` |
| B | `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\source-sync-check.md` |
| B conditional | `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\deployed-artifact-manifest.md` |
| C | `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\loadtest-results.md` |
| D | `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\failure-recovery-proof.md` |
| E | `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\sqlite-lock-proof.md` |
| F | `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\worker-health-proof.md` |
| G | `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\architecture.md` |
| G | `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\db-write-path.md` |
| G | `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\redis-durability.md` |
| G | `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\runtime-deploy.md` |
| G | `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\performance-loadtest.md` |
| G | `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\worker-health.md` |
| G | `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\security-secrets.md` |
| G | `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\evidence-docs.md` |
| G | `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\rollback-idempotency.md` |
| H | `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\fixes\round-1-fix-log.md` |
| I | `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-2\architecture.md` |
| I | `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-2\db-write-path.md` |
| I | `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-2\redis-durability.md` |
| I | `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-2\runtime-deploy.md` |
| I | `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-2\performance-loadtest.md` |
| I | `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-2\worker-health.md` |
| I | `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-2\security-secrets.md` |
| I | `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-2\evidence-docs.md` |
| I | `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-2\rollback-idempotency.md` |
| J | `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\final\final-report.md` |
| J | `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\final\production-status.md` |
| J | `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\final\rollback-instructions.md` |
| J | `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\README.md` |
| J conditional | `C:\Users\faizz\guinevere\PROGRESS.md` |
| J conditional | `C:\Users\faizz\guinevere\CHECKLIST.md` |

## 9. Rollback and Stop Notes

1. This continuation should not rollback by default.
2. Phase D is the only planned intentional service interruption, and it is temporary: stop writer, prove request-path survivability, restart writer, prove drain.
3. Halt execution immediately if any of these happen:
   - PM2 `9router` is no longer exactly 2 workers
   - public IPv4 `:20128` becomes reachable
   - Redis is exposed beyond loopback
   - writer cannot restart cleanly after recovery test
   - backlog does not drain after restart
4. If a hard rejection is hit during C/D/E/F:
   - stop further phases
   - capture exact failing evidence
   - restore writer to active state if it was intentionally stopped
   - do not claim PASS WITH LIMITATION for a broken boundary condition
5. Phase H fixes must capture any rollback action taken for each accepted finding.

## 10. Per-Phase Verification Scaffolds

### Phase A - Rebaseline Current Live State

**Dependencies**
- none

**Parallelism**
- sequential

**Expected Files**
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\current-live-rebaseline.md`

**Forbidden Patterns**
- `PRODUCTION PASS` without fresh command output
- `public open` for `49.12.82.34:20128`
- `127.0.0.1` omitted from Redis listener proof
- secret values, API keys, bearer tokens, raw request/response bodies

**Required Commands**
- `ssh -p 39999 root@49.12.82.34 "pm2 list --no-color"`
- `ssh -p 39999 root@49.12.82.34 "systemctl status redis-server --no-pager"`
- `ssh -p 39999 root@49.12.82.34 "systemctl status 9router-usage-writer.service --no-pager"`
- `ssh -p 39999 root@49.12.82.34 "ss -H -ltnp | grep ':6379 ' || true"`
- `curl.exe -sS -o NUL -w "tailscale_models=%{http_code} total=%{time_total}`n" http://100.104.210.75:20128/v1/models`
- `curl.exe -sS --connect-timeout 5 --max-time 5 http://49.12.82.34:20128/v1/models`
- `ssh -p 39999 root@49.12.82.34 "redis-cli -h 127.0.0.1 -p 6379 XLEN 9router:usage_events:v1 && redis-cli -h 127.0.0.1 -p 6379 XINFO GROUPS 9router:usage_events:v1 && redis-cli -h 127.0.0.1 -p 6379 XPENDING 9router:usage_events:v1 usage-writers && redis-cli -h 127.0.0.1 -p 6379 XLEN 9router:usage_events:deadletter:v1"`
- `ssh -p 39999 root@49.12.82.34 "sqlite3 /var/lib/9router/db/data.sqlite 'PRAGMA integrity_check;'"`
- `ssh -p 39999 root@49.12.82.34 "pm2 jlist"`
- `ssh -p 39999 root@49.12.82.34 "journalctl -u 9router-usage-writer.service --since '-30 min' --no-pager"`
- `ssh -p 39999 root@49.12.82.34 "grep -RInE 'SQLITE_BUSY|SQLITE_BUSY_SNAPSHOT|database is locked|writer crash|uncaught' /root/.pm2/logs 2>/dev/null || true"`

**Evidence Requirements**
- capture worker count, restart count, listener proof, endpoint reachability, stream stats, deadletter length, SQLite integrity verdict, and recent log verdicts

**Hard Rejection Criteria**
- PM2 `9router` is not exactly 2 workers
- Redis listener is not loopback-only
- Tailscale endpoint fails
- public IPv4 endpoint succeeds
- SQLite integrity check is not `ok`
- logs show active writer crash loop

### Phase B - Source-of-Truth Sync Check

**Dependencies**
- none

**Parallelism**
- parallel with Phase A

**Expected Files**
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\source-sync-check.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\deployed-artifact-manifest.md` (required if repo source is not clearly synced)

**Forbidden Patterns**
- `repo unclear`
- `looks synced`
- unstated hash comparisons
- unstated authoritative path

**Required Commands**
- `Get-ChildItem -Recurse 'C:\Users\faizz\guinevere\.codex\staging\p26-redis-write-buffer' | Select-Object FullName,Length`
- `Get-ChildItem -Recurse 'C:\Users\faizz\guinevere\.codex\staging\p26-redis-write-buffer' -File | Get-FileHash -Algorithm SHA256`
- `$paths = @('C:\Users\faizz\guinevere\src\lib\db\usageBuffer.js','C:\Users\faizz\guinevere\src\lib\usageDb.js','C:\Users\faizz\guinevere\src\shared\components\UsageStats.js','C:\Users\faizz\guinevere\scripts\usage-writer.mjs'); foreach ($p in $paths) { '{0}`t{1}' -f (Test-Path $p), $p }`
- `ssh -p 39999 root@49.12.82.34 "cd /root/9router && git rev-parse --show-toplevel && git status --short && git rev-parse HEAD"`
- `ssh -p 39999 root@49.12.82.34 "cd /root/9router && sha256sum src/lib/db/usageBuffer.js src/lib/db/schema.js src/lib/db/index.js src/lib/usageDb.js src/lib/db/repos/usageRepo.js open-sse/handlers/chatCore.js open-sse/handlers/chatCore/requestDetail.js open-sse/handlers/chatCore/nonStreamingHandler.js open-sse/handlers/chatCore/sseToJsonHandler.js open-sse/handlers/chatCore/streamingHandler.js src/app/api/usage/stats/route.js src/app/api/usage/stream/route.js src/shared/components/UsageStats.js src/sse/handlers/chat.js package.json package-lock.json scripts/usage-writer.mjs"`
- `ssh -p 39999 root@49.12.82.34 "sha256sum /etc/systemd/system/9router-usage-writer.service"`

**Evidence Requirements**
- exact authoritative source path(s)
- exact deployed path(s)
- explicit repo/staging/VPS sync verdict
- manifest with hashes if the deployed source is not mirrored cleanly in the repo

**Hard Rejection Criteria**
- authoritative source path remains unclear
- deployed artifacts are unverifiable by hash/path
- plan reaches final PASS without either repo sync proof or artifact-manifest proof

### Phase C - Loadtest

**Dependencies**
- Phase A PASS

**Parallelism**
- sequential

**Expected Files**
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\loadtest-results.md`

**Forbidden Patterns**
- fake p50/p95/p99 values
- `manual loadtest`
- public IPv4 probing omitted
- worker count omitted

**Required Commands**
- `ssh -p 39999 root@49.12.82.34 "date -Is && pm2 list --no-color && redis-cli -h 127.0.0.1 -p 6379 XLEN 9router:usage_events:v1 && redis-cli -h 127.0.0.1 -p 6379 XPENDING 9router:usage_events:v1 usage-writers && uptime && free -m"`
- `ssh -p 39999 root@49.12.82.34 "npx --yes autocannon -j -c 10 -a 50 http://127.0.0.1:20128/v1/models"`
- `ssh -p 39999 root@49.12.82.34 "npx --yes autocannon -j -c 20 -a 200 http://127.0.0.1:20128/v1/models"`
- `ssh -p 39999 root@49.12.82.34 "npx --yes autocannon -j -c 35 -a 700 http://127.0.0.1:20128/v1/models"`
- `ssh -p 39999 root@49.12.82.34 "date -Is && pm2 list --no-color && redis-cli -h 127.0.0.1 -p 6379 XLEN 9router:usage_events:v1 && redis-cli -h 127.0.0.1 -p 6379 XPENDING 9router:usage_events:v1 usage-writers && uptime && free -m && journalctl -u 9router-usage-writer.service --since '-15 min' --no-pager"`
- `curl.exe -sS -o NUL -w "tailscale_post=%{http_code} total=%{time_total}`n" http://100.104.210.75:20128/v1/models`
- `curl.exe -sS --connect-timeout 5 --max-time 5 http://49.12.82.34:20128/v1/models`

**Evidence Requirements**
- 50, 200, and 700 request runs
- success/failure counts
- p50/p95/p99 if emitted by `autocannon`
- CPU/RAM/load snapshot
- PM2 restart counts before/after
- stream length and pending before/after
- Tailscale still reachable
- public IPv4 still blocked

**Hard Rejection Criteria**
- PM2 worker count is no longer 2
- new restart storm appears
- Redis pending never drains after runs
- writer crash loop starts
- public IPv4 becomes reachable
- loadtest is not backed by real command output

### Phase D - Failure/Recovery Proof

**Dependencies**
- Phase A PASS
- Phase C PASS

**Parallelism**
- sequential

**Expected Files**
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\failure-recovery-proof.md`

**Forbidden Patterns**
- writer left stopped
- synthetic success claim without row/backlog proof
- duplicate-avoidance claim without measurable basis

**Required Commands**
- `ssh -p 39999 root@49.12.82.34 "systemctl stop 9router-usage-writer.service"`
- `ssh -p 39999 root@49.12.82.34 "systemctl is-active 9router-usage-writer.service || true"`
- `ssh -p 39999 root@49.12.82.34 "sqlite3 /var/lib/9router/db/data.sqlite 'SELECT COUNT(*) FROM usageHistory;' && redis-cli -h 127.0.0.1 -p 6379 XLEN 9router:usage_events:v1 && redis-cli -h 127.0.0.1 -p 6379 XPENDING 9router:usage_events:v1 usage-writers"`
- `ssh -p 39999 root@49.12.82.34 "for i in 1 2 3; do curl -sS http://127.0.0.1:20128/v1/chat/completions -H 'Content-Type: application/json' -d '{\"model\":\"deepseek/deepseek-v4-flash\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with ok.\"}],\"max_tokens\":8,\"stream\":false}' >/tmp/p26-recovery-$i.json; done"`
- `ssh -p 39999 root@49.12.82.34 "sqlite3 /var/lib/9router/db/data.sqlite 'SELECT COUNT(*) FROM usageHistory;' && redis-cli -h 127.0.0.1 -p 6379 XLEN 9router:usage_events:v1 && redis-cli -h 127.0.0.1 -p 6379 XPENDING 9router:usage_events:v1 usage-writers && systemctl status 9router-usage-writer.service --no-pager || true"`
- `ssh -p 39999 root@49.12.82.34 "systemctl start 9router-usage-writer.service && systemctl is-active 9router-usage-writer.service"`
- `ssh -p 39999 root@49.12.82.34 "for i in 1 2 3 4 5 6 7 8 9 10; do sqlite3 /var/lib/9router/db/data.sqlite 'SELECT COUNT(*) FROM usageHistory;'; redis-cli -h 127.0.0.1 -p 6379 XPENDING 9router:usage_events:v1 usage-writers; sleep 1; done"`
- `ssh -p 39999 root@49.12.82.34 "journalctl -u 9router-usage-writer.service --since '-10 min' --no-pager"`

**Evidence Requirements**
- requests still succeed while writer is stopped
- backlog grows while writer is stopped
- writer restarts cleanly
- backlog drains after restart
- SQLite row count increases after restart
- honest note on whether duplicate/non-loss proof was exact or only count-based

**Hard Rejection Criteria**
- writer remains stopped at the end of the phase
- requests fail when only the writer is stopped
- backlog does not grow while writer is down
- backlog does not drain after restart
- row count does not recover after restart

### Phase E - SQLite Lock Proof

**Dependencies**
- Phase C PASS
- Phase D PASS

**Parallelism**
- sequential

**Expected Files**
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\sqlite-lock-proof.md`

**Forbidden Patterns**
- `CLEAN` without command output
- omitted marker window timestamps
- `database is locked` omitted from search terms

**Required Commands**
- `ssh -p 39999 root@49.12.82.34 "date -Is"`
- `ssh -p 39999 root@49.12.82.34 "journalctl -u 9router-usage-writer.service --since '-30 min' --no-pager | grep -Ei 'SQLITE_BUSY|SQLITE_BUSY_SNAPSHOT|database is locked|better-sqlite3' || true"`
- `ssh -p 39999 root@49.12.82.34 "grep -RInE 'SQLITE_BUSY|SQLITE_BUSY_SNAPSHOT|database is locked|better-sqlite3' /root/.pm2/logs 2>/dev/null || true"`
- `ssh -p 39999 root@49.12.82.34 "sqlite3 /var/lib/9router/db/data.sqlite 'PRAGMA integrity_check;'"`

**Evidence Requirements**
- marker-window framing for before/during/after loadtest and recovery
- exact match count or explicit `no matches`
- one of `CLEAN`, `IMPROVED_WITH_RESIDUAL`, or `FAIL`
- explicit reasoning for the verdict

**Hard Rejection Criteria**
- repeated lock errors appear during the loadtest/recovery window
- SQLite integrity check is not `ok`
- verdict is stronger than the command output supports

### Phase F - Worker Health Proof

**Dependencies**
- Phase C PASS

**Parallelism**
- sequential

**Expected Files**
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\worker-health-proof.md`

**Forbidden Patterns**
- fake `50/50` claim
- `both workers handled traffic` without attribution evidence
- omitted limitation if attribution is unavailable

**Required Commands**
- `ssh -p 39999 root@49.12.82.34 "pm2 list --no-color"`
- `ssh -p 39999 root@49.12.82.34 "pm2 jlist"`
- `ssh -p 39999 root@49.12.82.34 "sqlite3 /var/lib/9router/db/data.sqlite 'PRAGMA table_info(usageHistory);'"`
- `ssh -p 39999 root@49.12.82.34 "sqlite3 /var/lib/9router/db/data.sqlite \"SELECT workerId, COUNT(*) FROM (SELECT workerId FROM usageHistory WHERE workerId IS NOT NULL ORDER BY rowid DESC LIMIT 200) GROUP BY workerId;\""`

**Evidence Requirements**
- exactly 2 PM2 workers online
- restart counts and status for both workers
- either recent multi-worker attribution proof from `usageHistory.workerId` or an explicit limitation statement
- no overclaim beyond what the data proves

**Hard Rejection Criteria**
- PM2 worker count is not 2
- any worker is offline or crash-looping
- the document claims balanced traffic without evidence

### Phase G - Audit Round 1

**Dependencies**
- Phases A through F PASS

**Parallelism**
- audit-batch parallel

**Expected Files**
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\architecture.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\db-write-path.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\redis-durability.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\runtime-deploy.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\performance-loadtest.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\worker-health.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\security-secrets.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\evidence-docs.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\rollback-idempotency.md`

**Forbidden Patterns**
- `PASS` with no cited evidence file
- unresolved boundary issues marked informational
- source-of-truth ambiguity ignored

**Required Commands**
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\current-live-rebaseline.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\source-sync-check.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\loadtest-results.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\failure-recovery-proof.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\sqlite-lock-proof.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\worker-health-proof.md'`
- `ssh -p 39999 root@49.12.82.34 "grep -RInE 'XACK|XREADGROUP|XAUTOCLAIM|usageHistory|workerId|apiKeyFp' /root/9router/src /root/9router/open-sse /root/9router/scripts 2>/dev/null"`

**Evidence Requirements**
- each auditor must cite the exact evidence and exact rejection checks it reviewed
- each finding must have severity and proof
- false positives must still carry proof

**Hard Rejection Criteria**
- any required audit file is missing
- any audit file gives a pass/fail verdict without evidence
- hot path, durability, network boundary, or source-of-truth concerns are skipped

### Phase H - Fix All Valid Findings

**Dependencies**
- Phase G complete

**Parallelism**
- sequential per finding; no overlapping edits on the same surface

**Expected Files**
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\fixes\round-1-fix-log.md`
- only the exact evidence/source surfaces cited by accepted round-1 findings

**Forbidden Patterns**
- unresolved CRITICAL/HIGH marked `accepted`
- silent fix with no finding reference
- unlogged re-run

**Required Commands**
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\architecture.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\db-write-path.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\redis-durability.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\runtime-deploy.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\performance-loadtest.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\worker-health.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\security-secrets.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\evidence-docs.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\rollback-idempotency.md'`
- `git diff --check`
- `ssh -p 39999 root@49.12.82.34 "cd /root/9router && git diff --check || true"`

**Evidence Requirements**
- every valid finding logged with fix/no-fix/false-positive disposition
- every re-run command logged
- every rollback note logged if a fix touched runtime state

**Hard Rejection Criteria**
- any CRITICAL or HIGH finding remains unresolved
- a fix is applied without being tied to a round-1 finding
- affected verification commands are not re-run

### Phase I - Audit Round 2

**Dependencies**
- Phase H complete

**Parallelism**
- audit-batch parallel

**Expected Files**
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-2\architecture.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-2\db-write-path.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-2\redis-durability.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-2\runtime-deploy.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-2\performance-loadtest.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-2\worker-health.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-2\security-secrets.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-2\evidence-docs.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-2\rollback-idempotency.md`

**Forbidden Patterns**
- re-audit that does not mention round-1 finding closure
- new PASS claim without checking changed surfaces

**Required Commands**
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\fixes\round-1-fix-log.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\architecture.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\db-write-path.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\redis-durability.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\runtime-deploy.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\performance-loadtest.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\worker-health.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\security-secrets.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\evidence-docs.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-1\rollback-idempotency.md'`

**Evidence Requirements**
- every round-2 file must state whether each round-1 concern is resolved, reduced, or still open
- no unresolved CRITICAL/HIGH may survive

**Hard Rejection Criteria**
- any CRITICAL or HIGH finding remains open
- round-2 ignores valid round-1 findings
- round-2 audit files are missing or evidence-thin

### Phase J - Finalization

**Dependencies**
- Phase I PASS

**Parallelism**
- sequential

**Expected Files**
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\final\final-report.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\final\production-status.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\final\rollback-instructions.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\README.md`
- `C:\Users\faizz\guinevere\PROGRESS.md` (conditional)
- `C:\Users\faizz\guinevere\CHECKLIST.md` (conditional)

**Forbidden Patterns**
- final status stronger than evidence supports
- `PRODUCTION PASS` while source-of-truth remains unclear
- missing rollback steps
- missing limitation section when limitations exist

**Required Commands**
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\current-live-rebaseline.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\source-sync-check.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\loadtest-results.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\failure-recovery-proof.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\sqlite-lock-proof.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\worker-health-proof.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\fixes\round-1-fix-log.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-2\architecture.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-2\db-write-path.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-2\redis-durability.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-2\runtime-deploy.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-2\performance-loadtest.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-2\worker-health.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-2\security-secrets.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-2\evidence-docs.md'`
- `Get-Content -Raw 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\audits\round-2\rollback-idempotency.md'`
- `ssh -p 39999 root@49.12.82.34 "pm2 list --no-color && systemctl is-active redis-server 9router-usage-writer.service && redis-cli -h 127.0.0.1 -p 6379 XPENDING 9router:usage_events:v1 usage-writers && sqlite3 /var/lib/9router/db/data.sqlite 'PRAGMA integrity_check;'"`
- `curl.exe -sS -o NUL -w "tailscale_final=%{http_code} total=%{time_total}`n" http://100.104.210.75:20128/v1/models`
- `curl.exe -sS --connect-timeout 5 --max-time 5 http://49.12.82.34:20128/v1/models`

**Evidence Requirements**
- final status
- exact changed/deployed files
- exact source-of-truth paths
- PM2 worker count
- Redis stream/backlog result
- writer service result
- SQLite lock verdict
- loadtest result
- failure/recovery proof
- public IPv4 block proof
- Tailscale proof
- audit round 1 and round 2 verdicts
- accepted limitations
- rollback instructions

**Hard Rejection Criteria**
- final report omits any mandatory field above
- status is `PRODUCTION PASS` while any hard rejection is still true
- rollback instructions are missing
- final docs do not match round-2 audit reality

## 11. Phase-Specific Final Status Rules

`P26.1 REDIS WRITE BUFFER - PRODUCTION PASS` requires all of:

- A through J complete
- no unresolved CRITICAL/HIGH in round 2
- source-of-truth resolved
- PM2 exactly 2 workers
- backlog drains after recovery
- SQLite lock verdict not `FAIL`
- public IPv4 still blocked
- Redis still loopback-only

`P26.1 REDIS WRITE BUFFER - PASS WITH LIMITATION` is allowed only if:

- safety/network/runtime invariants still pass
- any limitation is documented and non-critical
- source-of-truth is still adequately evidenced, even if not ideal

`P26.1 REDIS WRITE BUFFER - BLOCKED` is required if:

- source-of-truth cannot be resolved
- real loadtest cannot be run
- round-2 audit cannot clear CRITICAL/HIGH findings

`P26.1 REDIS WRITE BUFFER - ROLLED BACK` is required if:

- a hard runtime boundary is violated and rollback is used to restore safety

## 12. Execution Summary

This finalization plan is intentionally narrow:

- keep the existing implementation
- prove it under load and recovery
- prove the runtime boundaries stayed intact
- prove where the real source lives
- let auditors decide whether the final status is full PASS or PASS WITH LIMITATION

Anything weaker than that is not finalization.
