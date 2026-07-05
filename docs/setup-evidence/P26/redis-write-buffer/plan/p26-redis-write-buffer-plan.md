# P26.1 Redis Write Buffer Implementation Plan

Date: 2026-06-28
Workspace: `C:\Users\faizz\guinevere`
Evidence root: `docs/setup-evidence/P26/redis-write-buffer`
Target host: `root@49.12.82.34 -p 39999`

## Goal

Reduce SQLite lock pressure on the 9Router request path by moving usage-event writes to Redis Streams and draining them with a dedicated writer service, while keeping:

- exactly 2 PM2 `9router` workers
- the public IPv4 firewall block on `:20128`
- Tailscale access intact
- SQLite as the final sink

`requestDetails` stays on the existing buffered SQLite path in this phase.

## Binding Decisions

1. Use Redis Streams, not Redis Lists.
2. Keep SQLite as the final accounting sink.
3. Keep the 9Router PM2 worker count at exactly 2.
4. Install Redis only on the 9Router VPS.
5. Bind Redis to loopback only.
6. Use `appendonly yes` with `appendfsync everysec`.
7. Store only safe metadata in the stream. Raw API keys become fingerprints before enqueue.
8. Emit error events too, not just success events.
9. Make SQLite idempotent on `request_id`.
10. Use a direct SQLite fallback only when Redis is unavailable.

## Collision Scan

Shared writers and ownership:

| Surface | Owner | Notes |
|---|---|---|
| `src/lib/db/repos/usageRepo.js` | P26.1 | producer + fallback logic |
| `src/lib/db/schema.js` | P26.1 | additive columns/indexes |
| `open-sse/handlers/chatCore/*.js` | P26.1 | request-completion event emission |
| `open-sse/utils/usageTracking.js` | P26.1 | alternate usage path |
| `src/app/api/usage/stats/route.js` | P26.1 | buffer health exposure |
| `src/shared/components/UsageStats.js` | P26.1 | visible backlog/status |
| `package.json` / `package-lock.json` | P26.1 | Redis client dependency |
| `scripts/usage-writer.mjs` | P26.1 | dedicated writer process |
| `/etc/systemd/system/9router-usage-writer.service` | P26.1 runtime | writer unit |
| `/etc/redis/redis.conf` | P26.1 runtime | loopback-only Redis config |

No other task should edit these files while P26.1 is in progress.

## Dependency Map

```text
P26.1-001 Redis preflight/install/config
  -> P26.1-002 Usage event schema + producer adapter
  -> P26.1-003 Hot path switch from direct DB write to Redis XADD
  -> P26.1-004 Usage writer service with batch transaction + ACK/retry
  -> P26.1-005 PM2/systemd wiring
  -> P26.1-006 Dashboard/backlog/health visibility
  -> P26.1-007 Tests and failure simulation
  -> P26.1-008 Deploy/canary/runtime proof
  -> P26.1-009 Audit/fix/final
```

## Runtime Services

- `redis-server.service` or the equivalent loopback-only Redis service on the 9Router VPS
- `9router-usage-writer.service`
- `pm2-root.service` remains the supervisor for the existing 9Router app

## Step Scaffolds

### P26.1-001 Redis preflight/install/config

**Expected Files**

- `package.json`
- `package-lock.json`
- `/etc/redis/redis.conf`
- `docs/setup-evidence/P26/redis-write-buffer/preflight/current-runtime-ground-truth.md`

**Forbidden Patterns**

- Redis listener on `0.0.0.0`, public IPv4, or Tailscale IP
- `maxmemory-policy` set to an eviction policy that silently drops usage events
- `as any`
- `@ts-ignore`
- `@ts-expect-error`
- bare `except`
- empty catch

**Required Commands**

- `ssh -p 39999 root@49.12.82.34 "systemctl is-active redis-server redis valkey 2>/dev/null || true"`
- `ssh -p 39999 root@49.12.82.34 "ss -H -ltnp | grep -E ':(6379|20128) ' || true"`
- `ssh -p 39999 root@49.12.82.34 "cd /root/9router && npm install redis@^5"`
- `ssh -p 39999 root@49.12.82.34 "redis-cli -h 127.0.0.1 -p 6379 PING"`

**Evidence Requirements**

- `preflight/current-runtime-ground-truth.md`
- `research/research-synthesis.md`

**Hard Rejection Criteria**

- Redis is exposed off loopback.
- Redis package is not installed.
- The install step changes PM2 worker count or firewall state.

### P26.1-002 Usage event schema + producer adapter

**Expected Files**

- `src/lib/db/usageBuffer.mjs`
- `src/lib/db/schema.js`
- `src/lib/db/index.js`
- `src/lib/db/repos/usageRepo.js`
- `open-sse/handlers/chatCore/requestDetail.js`
- `open-sse/utils/usageTracking.js`

**Forbidden Patterns**

- raw API key values in Redis stream payloads
- `INSERT INTO usageHistory` in request handlers
- `SELECT *`
- bare `except`
- empty catch
- `as any`

**Required Commands**

- `ssh -p 39999 root@49.12.82.34 "cd /root/9router && grep -nE 'requestId|workerId|combo|latencyMs|errorClass' src/lib/db/schema.js src/lib/db/repos/usageRepo.js src/lib/db/usageBuffer.mjs"`
- `ssh -p 39999 root@49.12.82.34 "cd /root/9router && npx vitest run tests/unit/usage-buffer.test.js"`

**Evidence Requirements**

- `verification/local-tests.md`

**Hard Rejection Criteria**

- The event schema omits required fields.
- The producer still writes directly to SQLite on the normal hot path.
- The stream carries raw secrets.

### P26.1-003 Hot path switch from direct DB write to Redis XADD

**Expected Files**

- `open-sse/handlers/chatCore.js`
- `open-sse/handlers/chatCore/nonStreamingHandler.js`
- `open-sse/handlers/chatCore/streamingHandler.js`
- `open-sse/handlers/chatCore/sseToJsonHandler.js`

**Forbidden Patterns**

- direct `usageHistory` inserts from request handlers
- success-only accounting that drops error events
- `saveRequestUsageDirect` being called from request handlers except as explicit fallback on Redis failure

**Required Commands**

- `ssh -p 39999 root@49.12.82.34 "cd /root/9router && grep -RIn --exclude-dir=node_modules --exclude-dir=.git 'saveUsageStats(' open-sse/handlers/chatCore* open-sse/utils/usageTracking.js"`
- `ssh -p 39999 root@49.12.82.34 "cd /root/9router && grep -RIn --exclude-dir=node_modules --exclude-dir=.git 'INSERT INTO usageHistory' open-sse src | head -40"`

**Evidence Requirements**

- `verification/local-tests.md`

**Hard Rejection Criteria**

- The request path still blocks on SQLite in the normal buffered mode.
- Error events are not emitted.
- `combo` is lost for combo requests.

### P26.1-004 Usage writer service with batch transaction + ACK/retry

**Expected Files**

- `scripts/usage-writer.mjs`
- `/etc/systemd/system/9router-usage-writer.service`

**Forbidden Patterns**

- `XACK` before SQLite commit
- ACKing validation failures without dead-letter handling
- `DELETE FROM usageHistory`
- `DELETE FROM usageDaily`
- `VACUUM`
- secrets in logs

**Required Commands**

- `ssh -p 39999 root@49.12.82.34 "systemd-analyze verify /etc/systemd/system/9router-usage-writer.service"`
- `ssh -p 39999 root@49.12.82.34 "systemctl daemon-reload"`
- `ssh -p 39999 root@49.12.82.34 "systemctl enable --now 9router-usage-writer"`
- `ssh -p 39999 root@49.12.82.34 "systemctl status 9router-usage-writer --no-pager"`
- `ssh -p 39999 root@49.12.82.34 "redis-cli -h 127.0.0.1 -p 6379 XGROUP CREATE 9router:usage_events:v1 usage-writers 0 MKSTREAM"`

**Evidence Requirements**

- `deploy/deploy-evidence.md`
- `runtime/redis-backlog-proof.md`
- `runtime/sqlite-lock-proof.md`

**Hard Rejection Criteria**

- The writer ACKs before commit.
- Pending entries cannot be reclaimed.
- The dead-letter path is absent or unsafe.

### P26.1-005 PM2/systemd wiring

**Expected Files**

- `redis-server.service` runtime state or `/etc/redis/redis.conf`
- `9router-usage-writer.service`
- `pm2-root.service` unchanged

**Forbidden Patterns**

- `9router` PM2 worker count changes
- public Redis listener
- firewall resets
- SSH disruption

**Required Commands**

- `ssh -p 39999 root@49.12.82.34 "pm2 status --no-color"`
- `ssh -p 39999 root@49.12.82.34 "systemctl is-active pm2-root tailscaled redis-server 9router-usage-writer"`
- `ssh -p 39999 root@49.12.82.34 "ss -H -ltnp | grep -E ':(6379|20128|22) ' || true"`

**Evidence Requirements**

- `deploy/deploy-evidence.md`

**Hard Rejection Criteria**

- `9router` is no longer exactly 2 workers.
- Redis is visible off loopback.
- `pm2-root.service` or `tailscaled` becomes unhealthy.

### P26.1-006 Dashboard/backlog/health visibility

**Expected Files**

- `src/app/api/usage/stats/route.js`
- `src/lib/db/index.js`
- `src/lib/db/usageBuffer.mjs`
- `src/shared/components/UsageStats.js`

**Forbidden Patterns**

- large payload scans for buffer status
- `SELECT *`
- exposing raw secrets
- dashboard changes that slow the page down materially

**Required Commands**

- `ssh -p 39999 root@49.12.82.34 "cd /root/9router && npx vitest run tests/unit/usage-buffer-health.test.js"`
- `ssh -p 39999 root@49.12.82.34 "cd /root/9router && grep -nE 'buffer|backlog|pending|stream' src/app/api/usage/stats/route.js src/shared/components/UsageStats.js"`

**Evidence Requirements**

- `runtime/worker-health-proof.md`

**Hard Rejection Criteria**

- Buffer health is not visible anywhere.
- The stats payload regresses response time materially.

### P26.1-007 Tests and failure simulation

**Expected Files**

- `tests/unit/usage-buffer.test.js`
- `tests/unit/usage-writer.test.js`
- `tests/unit/usage-buffer-health.test.js`
- `tests/unit/usage-buffer-failure.test.js`
- `docs/setup-evidence/P26/redis-write-buffer/verification/local-tests.md`

**Forbidden Patterns**

- `as any`
- `@ts-ignore`
- `@ts-expect-error`
- bare `catch`
- flaky sleeps without assertions

**Required Commands**

- `ssh -p 39999 root@49.12.82.34 "cd /root/9router && npx vitest run tests/unit/usage-buffer.test.js tests/unit/usage-writer.test.js tests/unit/usage-buffer-health.test.js tests/unit/usage-buffer-failure.test.js"`

**Evidence Requirements**

- `verification/local-tests.md`

**Hard Rejection Criteria**

- ACK-after-commit is not proven.
- Writer-down fallback is not proven.
- Recovery drain is not proven.
- The 2-worker regression is not proven.

### P26.1-008 Deploy/canary/runtime proof

**Expected Files**

- `docs/setup-evidence/P26/redis-write-buffer/deploy/deploy-evidence.md`
- `docs/setup-evidence/P26/redis-write-buffer/runtime/loadtest-results.md`
- `docs/setup-evidence/P26/redis-write-buffer/runtime/redis-backlog-proof.md`
- `docs/setup-evidence/P26/redis-write-buffer/runtime/sqlite-lock-proof.md`
- `docs/setup-evidence/P26/redis-write-buffer/runtime/worker-health-proof.md`

**Forbidden Patterns**

- production PASS claims without runtime proof
- public IPv4 exposure on `:20128`
- PM2 worker drift
- secret leakage in logs or evidence

**Required Commands**

- `ssh -p 39999 root@49.12.82.34 "pm2 status --no-color"`
- `ssh -p 39999 root@49.12.82.34 "redis-cli -h 127.0.0.1 -p 6379 XLEN 9router:usage_events:v1"`
- `ssh -p 39999 root@49.12.82.34 "redis-cli -h 127.0.0.1 -p 6379 XPENDING 9router:usage_events:v1 usage-writers"`
- `ssh -p 39999 root@49.12.82.34 "curl -sS -o /dev/null -w 'local_models=%{http_code} time=%{time_total}\n' --max-time 5 http://127.0.0.1:20128/v1/models"`

**Evidence Requirements**

- all runtime proof files above

**Hard Rejection Criteria**

- backlog does not drain after writer recovery
- SQLite lock storm remains same or worse
- any network boundary changes

### P26.1-009 Audit/fix/final

**Expected Files**

- `docs/setup-evidence/P26/redis-write-buffer/audits/round-1/*.md`
- `docs/setup-evidence/P26/redis-write-buffer/fixes/round-1-fix-log.md`
- `docs/setup-evidence/P26/redis-write-buffer/audits/round-2/*.md`
- `docs/setup-evidence/P26/redis-write-buffer/final/final-report.md`
- `docs/setup-evidence/P26/redis-write-buffer/final/production-status.md`
- `docs/setup-evidence/P26/redis-write-buffer/final/rollback-instructions.md`
- `docs/setup-evidence/P26/redis-write-buffer/README.md`

**Forbidden Patterns**

- unresolved CRITICAL or HIGH findings
- fake PASS claims
- missing runtime proof
- missing rollback state

**Required Commands**

- Read every audit file fully.
- Re-run only the verification commands touched by valid findings.
- Re-run `git diff --check`.

**Evidence Requirements**

- round-1 audits
- fix log
- round-2 audits
- final report and status docs

**Hard Rejection Criteria**

- any audit finding remains unresolved
- final report omits worker count, backlog, SQLite integrity, or rollback state

## Verification Scaffold Rules

- One step, one owner.
- Parent verifies every claimed file and command result directly.
- Any failed command is recorded before fixes.
- Evidence files are written after implementation, not before.
- No sub-step may silently absorb a scaffold violation.

## Final Status Targets

- `P26.1 REDIS WRITE BUFFER - PRODUCTION PASS`
- `P26.1 REDIS WRITE BUFFER - PASS WITH LIMITATION`
- `P26.1 REDIS WRITE BUFFER - ROLLED BACK`
- `P26.1 BLOCKED - NEEDS MAMA DECISION`

## Footer

This plan intentionally keeps the hot path narrow: usage events go through Redis Streams, SQLite remains the sink, and requestDetails keeps its existing buffered path until a separate phase proves safe.
