# P26.1 Deployed Artifact Manifest

Date: 2026-06-28
Authoritative deployed app root: `/root/9router`
Authoritative service-unit path: `/etc/systemd/system/9router-usage-writer.service`
Local staging mirror root: `C:\Users\faizz\guinevere\.codex\staging\p26-redis-write-buffer`

## What Was Done
- Recorded the exact deployed P26.1 artifact set and hashes from the live VPS.
- Marked which artifacts have matching local staging mirrors.
- Marked which artifacts are deployed-only and not mirrored into the local repo source tree.

## Files Changed
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\deployed-artifact-manifest.md`

## Validation Results
- Deployed runtime authority is `/root/9router` plus the systemd unit at `/etc/systemd/system/9router-usage-writer.service`.
- Local staging mirrors only part of the deployed artifact set.
- The Guinevere repo source tree is not the deployed 9Router source tree.

## Artifact Table

| Artifact | Deployed Path | SHA256 | Staging Mirror | Mirror SHA Match |
|---|---|---|---|---|
| Usage buffer module | `/root/9router/src/lib/db/usageBuffer.js` | `3b675cfb8adddfa4c0983e2ec1b4cecd88e30b464a89403dc6643a6b3e0cf150` | `usageBuffer.js` | yes |
| Schema patch | `/root/9router/src/lib/db/schema.js` | `3c2c7059552c787e5fe0b014a4eb49b0203beef63882c2dca205a256f4c35072` | none | n/a |
| DB index exports | `/root/9router/src/lib/db/index.js` | `92fe7317493373866e251c7a49636d9893c7c4d6607f2eef997141b7af3985d4` | none | n/a |
| usageDb shim | `/root/9router/src/lib/usageDb.js` | `8778a67947a2d577c60f8ae017fce939d655d75f52186634a3c0193ff63c2810` | `usageDb.js` | yes |
| Usage repo producer path | `/root/9router/src/lib/db/repos/usageRepo.js` | `4d5e1310b4b45d71c8a7f192406114f48e7d10d6e8cbab4b6914481720a2380e` | none | n/a |
| Chat core | `/root/9router/open-sse/handlers/chatCore.js` | `eeae55529d708bbc564d26eb67f5173b9e6b3e67752a9138376491ae43d9447a` | none | n/a |
| Request detail usage emit | `/root/9router/open-sse/handlers/chatCore/requestDetail.js` | `7360ad5ecf8c162fd28c85a11dadbfc1850e782cec54d6fa961679a59808eb54` | none | n/a |
| Non-streaming handler | `/root/9router/open-sse/handlers/chatCore/nonStreamingHandler.js` | `28a4981c5b29430584e8545936aa056479e04787377ba1153cefbcf953f159f5` | none | n/a |
| SSE-to-JSON handler | `/root/9router/open-sse/handlers/chatCore/sseToJsonHandler.js` | `97ee0ebcfee3673b668f7325ffe82cec1b4c90ae46f6a5bc1ba7560fd7884406` | none | n/a |
| Streaming handler | `/root/9router/open-sse/handlers/chatCore/streamingHandler.js` | `70a92288476eecd9e076d3a4f7b8f18868818c5f50d27d449d91ee94a5ec3d2f` | none | n/a |
| Stats route | `/root/9router/src/app/api/usage/stats/route.js` | `49427822618e3656df0db44fa47a3d749d5f9459475b571a90f6c7cbb9dea0ba` | none | n/a |
| Stream route | `/root/9router/src/app/api/usage/stream/route.js` | `dddff2c1bc9bad23453ccb81d1c2fae422fe3ec42bd427136a88e4a29f493aca` | none | n/a |
| Dashboard buffer strip | `/root/9router/src/shared/components/UsageStats.js` | `5ccafd70d3f3047159a23be112e024ca29baf2cdb33aba27b55cd9dc8e67cb27` | `UsageStats.js` | yes |
| SSE router combo threading | `/root/9router/src/sse/handlers/chat.js` | `a0c4b42b5542fa9aca744b1b9363007664a5f8486e6c5fe3234ad924a9fad277` | none | n/a |
| Package manifest | `/root/9router/package.json` | `5b9616661e48a4aa13047bf4c41c720a7e3a89f156fcaec6539ad4b4b1325ae0` | none | n/a |
| Package lock | `/root/9router/package-lock.json` | `eba01708d17ee561bff867b6b7355a8fb6ec211946b18d16e94e1d7a797ffd7e` | none | n/a |
| Writer entrypoint | `/root/9router/scripts/usage-writer.mjs` | `8b5a940620005c93feefd39d901d29306c180687271bd728fa82e9adac239ad5` | `usage-writer.mjs` | yes |
| Writer service unit | `/etc/systemd/system/9router-usage-writer.service` | `bfb1dbf84b75f1a921a190e21bff1132f00c509aa2597ecf0654c6bf91cafaf6` | `9router-usage-writer.service` | yes |

## Local-Only Staging Helpers
- `smoke-buffer.mjs`
- `check-smoke-rows.mjs`
- `inspect-xreadgroup.mjs`
- `p26-loadtest.mjs`

These are operator-side validation helpers and are not part of the deployed artifact set unless separately copied to the VPS.

## Deployed Worktree Drift Outside Minimal P26 Mirror
- `/root/9router/src/lib/db/adapters/betterSqliteAdapter.js`
- `/root/9router/src/lib/db/adapters/bunSqliteAdapter.js`
- `/root/9router/src/lib/db/adapters/nodeSqliteAdapter.js`
- `/root/9router/.next-build-backup/` (untracked)
- `/root/9router/server.js` (untracked)

These paths are present in the deployed worktree state and should be treated as surrounding VPS drift unless separately traced to P26 in a future reconciliation pass.

## Doc-Sync Impact
- This manifest is the required bridge between deployed runtime authority and the local evidence repo.
- Final status must refer to this manifest when listing exact changed/deployed files.

## Boundary Compliance
- Manifest creation did not alter runtime state.
- No secrets were captured.

## Rollback / Re-run Safety
- Read-only inventory only.
- Safe to refresh at any time.

## Design Decisions / Caveats
- This manifest intentionally separates:
  - deployed authority
  - local staging mirror
  - local-only helper harnesses
  - unrelated deployed worktree drift
- That split is necessary to avoid a false impression that the Guinevere repo is the canonical 9Router source.

## Auditor Gate
- Required input for `evidence-docs`, `architecture`, and `rollback-idempotency` audit surfaces.

## Security Scan
- Hashes and paths only.
- No environment contents or secrets recorded.

## Acceptance Criteria Mapping
- Exact deployed artifact paths: pass
- Exact source-of-truth paths: pass
- Partial mirror transparency: pass
- Full repo-sync in this workspace: fail

## Footer
- Manifest verdict: `DEPLOYED ARTIFACTS IDENTIFIED, LOCAL SOURCE SPLIT EXPLICIT`.
