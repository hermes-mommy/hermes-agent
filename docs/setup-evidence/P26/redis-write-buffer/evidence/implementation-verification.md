# P26.1 - Redis Stream Write Buffer / DB Write Offload Verification

## What Was Done
- Added a Redis Stream based usage-event buffer in `/root/9router/src/lib/db/usageBuffer.js`.
- Kept SQLite as the persistence sink and added schema support for request-level metadata.
- Routed usage stats and SSE buffer status through the existing usage endpoints and dashboard.
- Added a dedicated systemd writer service:
  - `/etc/systemd/system/9router-usage-writer.service`
  - entrypoint: `/root/9router/scripts/usage-writer.mjs`

## Files Changed
- `/root/9router/src/lib/db/usageBuffer.js`
- `/root/9router/src/lib/db/schema.js`
- `/root/9router/src/lib/db/index.js`
- `/root/9router/src/lib/usageDb.js`
- `/root/9router/src/lib/db/repos/usageRepo.js`
- `/root/9router/open-sse/handlers/chatCore.js`
- `/root/9router/open-sse/handlers/chatCore/requestDetail.js`
- `/root/9router/open-sse/handlers/chatCore/nonStreamingHandler.js`
- `/root/9router/open-sse/handlers/chatCore/sseToJsonHandler.js`
- `/root/9router/open-sse/handlers/chatCore/streamingHandler.js`
- `/root/9router/src/app/api/usage/stats/route.js`
- `/root/9router/src/app/api/usage/stream/route.js`
- `/root/9router/src/shared/components/UsageStats.js`
- `/root/9router/src/sse/handlers/chat.js`
- `/root/9router/package.json`
- `/root/9router/package-lock.json` already contained the matching redis package version after install

## Validation Results
- `npm run build` completed successfully on the VPS.
- `systemctl status redis-server` showed Redis running on `127.0.0.1:6379`.
- `systemctl status 9router-usage-writer.service` showed the writer active and healthy.
- `pm2 list` still showed exactly 2 online `9router` workers.
- Smoke test confirmed end-to-end offload:
  - publish to Redis Stream succeeded
  - writer consumed the stream
  - SQLite row was inserted
  - pending count returned to 0

### Key runtime evidence
`scripts/smoke-buffer.mjs` output:
```json
{
  "requestId": "p26-smoke-1782587879877",
  "before": { "connected": true, "writerHealthy": true, "streamLength": 2, "pending": 0, "deadletterLength": 0 },
  "publish": { "delivered": true, "streamId": "1782587879941-0", "reason": null },
  "after": { "connected": true, "writerHealthy": true, "streamLength": 3, "pending": 0, "deadletterLength": 0 },
  "row": {
    "requestId": "p26-smoke-1782587879877",
    "provider": "p26-smoke",
    "model": "buffer-smoke",
    "combo": null,
    "promptTokens": 2,
    "completionTokens": 3,
    "apiKeyFp": "fp_1fdde6bd57ee1d1e",
    "status": "success"
  }
}
```

## Evidence Artifacts
- Build log: `next build --webpack` completed successfully.
- Redis state:
  - `XINFO GROUPS 9router:usage_events:v1` showed `pending: 0`.
  - `XINFO CONSUMERS 9router:usage_events:v1 usage-writers` showed the stable writer consumer.
- Writer service log:
  - startup lines present in `journalctl -u 9router-usage-writer.service`

## Doc-Sync Impact
- Preflight and research docs already existed in:
  - `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\preflight\current-runtime-ground-truth.md`
  - `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\research\research-synthesis.md`
  - `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\plan\p26-redis-write-buffer-plan.md`
- This file captures the runtime verification layer for the same task bundle.

## Boundary Compliance
- PM2 `9router` worker count remained at 2.
- No firewall changes were made.
- Redis listens on loopback only.
- Raw API keys are not written into Redis; only fingerprints are stored.

## Rollback / Re-run Safety
- Writer service can be stopped with:
  - `systemctl stop 9router-usage-writer.service`
- Redis can be disabled independently if needed.
- The smoke script only writes synthetic test usage events and can be re-run safely with unique request IDs.

## Design Decisions / Caveats
- The writer consumer name is stable across restarts so pending entries can be reclaimed.
- Redis Stream parsing was adjusted to match the actual `redis` client response shape.
- Usage stats endpoints still work if buffer status lookup fails; buffer is treated as additive metadata.

## Auditor Gate
- Not yet separately run in this workspace after the final runtime fix.
- Build and runtime smoke evidence were used as completion proof.

## Security Scan
- No secrets were added to repo files.
- The smoke event used a fake API key string that is only fingerprinted before persistence.

## Acceptance Criteria Mapping
- Redis Stream buffer exists: pass
- Dedicated writer exists: pass
- SQLite remains sink: pass
- Dashboard exposes buffer health: pass
- Runtime proof of publish -> consume -> persist: pass
- PM2 workers unchanged at 2: pass

## Footer
- Verified on 2026-06-28 from the VPS `ninerouter-vps`.
