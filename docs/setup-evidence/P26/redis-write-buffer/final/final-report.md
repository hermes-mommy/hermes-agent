# P26.1 Final Report - Redis Write Buffer

Date: 2026-06-28
Final status: `P26.1 REDIS WRITE BUFFER - PASS WITH LIMITATION`
Workspace: `C:\Users\faizz\guinevere`
Deployed host: `root@49.12.82.34 -p 39999`

## What Was Completed
- Verified the live runtime after Redis Stream write-buffer implementation.
- Resolved source-of-truth ambiguity with an explicit deployed artifact manifest.
- Proved the post-cutover PM2 entrypoint at `/root/9router/.next/standalone/server.js`.
- Ran authenticated production-path loadtests at `50`, `200`, and `700` requests.
- Ran controlled writer stop/restart recovery proof.
- Re-baselined SQLite lock behavior and dual-worker traffic evidence.
- Completed round-1 and round-2 audits.
- Closed the round-1 evidence-quality findings and refreshed the affected runtime docs.

## Final Runtime Outcome
- PM2 `9router` remained exactly `2` workers online.
- The writer service remained active after recovery testing.
- Redis stayed loopback-only.
- Public IPv4 `49.12.82.34:20128` remained blocked from the operator workstation.
- Tailscale stayed reachable, and anonymous requests now correctly return `401` after the auth-protected cutover.
- SQLite integrity stayed `ok`.

## Loadtest Summary
- Phase `50`
  - success `50/50`
  - `/v1/models` p50/p95/p99: `235.13 / 550.91 / 609.06 ms`
  - `/v1/chat/completions` p50/p95/p99: `3035.72 / 17621.41 / 17621.41 ms`
  - stream `len 592 -> 599`
  - busy delta `0`
- Phase `200`
  - success `200/200`
  - `/v1/models` p50/p95/p99: `252.03 / 572.35 / 654.09 ms`
  - `/v1/chat/completions` p50/p95/p99: `2846.13 / 4007.16 / 4007.16 ms`
  - stream `len 601 -> 611`
  - busy delta `0`
- Phase `700`
  - success `700/700`
  - `/v1/models` p50/p95/p99: `339.89 / 701.80 / 972.66 ms`
  - `/v1/chat/completions` p50/p95/p99: `3183.90 / 8113.39 / 11220.37 ms`
  - stream `len 613 -> 637`
  - busy delta `0`

## Backlog / Recovery Summary
- Before controlled outage: stream length `639`
- During writer stop after injected requests: stream length `643`
- After restart immediate snapshot: stream length `643`
- Final post-drain snapshot: stream length `653`
- Controlled outage request result: `4/4` successful responses while writer was stopped
- Landed recovery rows: `11443` through `11446`, each with non-empty `streamId`

## SQLite / Worker Summary
- SQLite verdict: `IMPROVED_WITH_RESIDUAL`
- Current live `usageHistory` spot-check count after validation: `11625`
- No lock matches in active PM2 worker logs `9router-error-3.log` and `9router-error-4.log`
- Historical residue remains in old logs from the stale/pre-buffer runtime
- Worker verdict: `PASS WITH MEASURED DUAL-WORKER TRAFFIC`

## Exact Source-of-Truth Paths
- Deployed application source: `/root/9router`
- Active PM2 runtime entrypoint: `/root/9router/.next/standalone/server.js`
- Writer unit: `/etc/systemd/system/9router-usage-writer.service`
- Local evidence authority: `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\`
- Local staging mirror: `C:\Users\faizz\guinevere\.codex\staging\p26-redis-write-buffer`

## Exact Changed / Deployed Files
- Deployed application/runtime surfaces:
  - `src/lib/db/usageBuffer.js`
  - `src/lib/db/schema.js`
  - `src/lib/db/index.js`
  - `src/lib/usageDb.js`
  - `src/lib/db/repos/usageRepo.js`
  - `open-sse/handlers/chatCore.js`
  - `open-sse/handlers/chatCore/requestDetail.js`
  - `open-sse/handlers/chatCore/nonStreamingHandler.js`
  - `open-sse/handlers/chatCore/sseToJsonHandler.js`
  - `open-sse/handlers/chatCore/streamingHandler.js`
  - `src/app/api/usage/stats/route.js`
  - `src/app/api/usage/stream/route.js`
  - `src/shared/components/UsageStats.js`
  - `src/sse/handlers/chat.js`
  - `package.json`
  - `package-lock.json`
  - `scripts/usage-writer.mjs`
  - `/etc/systemd/system/9router-usage-writer.service`
- Operator-side helper surfaces:
  - `.codex/staging/p26-redis-write-buffer/p26-loadtest.mjs`
  - `.codex/staging/p26-redis-write-buffer/p26-failure-recovery.mjs`

## Audit Summary
- Round 1:
  - architecture: `PASS WITH DOCUMENTATION GAP`
  - db-write-path: `PASS with evidence-quality caveats`
  - redis-durability: `PASS`
  - runtime-deploy: `PASS WITH LIMITATION`
  - performance-loadtest: `PASS`
  - worker-health: `PASS WITH LIMITATION`
  - security-secrets: `PASS`
  - evidence-docs: `PASS`
  - rollback-idempotency: `PASS WITH LIMITATION`
- Round 2:
  - no unresolved CRITICAL/HIGH findings
  - architecture gap closed
  - db-write-path evidence gaps closed

## Accepted Limitations
1. The authoritative deployed 9Router source remains the VPS worktree, not this local repo.
2. Historical `SQLITE_BUSY` residue remains in old PM2 logs, so the honest SQLite verdict is `IMPROVED_WITH_RESIDUAL`, not `CLEAN`.
3. Worker proof demonstrates real dual-worker traffic but not an exact balancing ratio.

## Rollback Position
- No rollback was executed.
- Rollback instructions are documented in `final/rollback-instructions.md`.
- Any future rollback must use an explicit VPS-side artifact or commit target.

## Tracker Note
- `PROGRESS.md` and `CHECKLIST.md` were left unchanged because P26 is still marked `(reserved)` in those global trackers and this finalization bundle already carries the authoritative P26 evidence trail.

## Final Verdict
P26.1 is production-viable and passed the runtime, recovery, and audit gates, but the cleanest honest status is `PASS WITH LIMITATION` because deployment authority is still split from this repo and SQLite history still contains pre-fix residual lock signatures.
