# P26.1 Source-of-Truth Sync Check

Date: 2026-06-28
Workspace: `C:\Users\faizz\guinevere`
Deployed host: `root@49.12.82.34 -p 39999`

## What Was Done
- Checked whether the authoritative P26.1 source is present in the local Guinevere repo.
- Checked the local staging mirror under `.codex/staging/p26-redis-write-buffer`.
- Checked the deployed `/root/9router` worktree path, git state, commit base, and deployed file hashes.
- Compared mirrored files by SHA256 where the local staging copy exists.

## Files Changed
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\source-sync-check.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\deployed-artifact-manifest.md`

## Validation Results
- Local repo-path check:
  - `C:\Users\faizz\guinevere\src\lib\db\usageBuffer.js` -> missing
  - `C:\Users\faizz\guinevere\src\lib\usageDb.js` -> missing
  - `C:\Users\faizz\guinevere\src\shared\components\UsageStats.js` -> missing
  - `C:\Users\faizz\guinevere\scripts\usage-writer.mjs` -> missing
- Local staging path exists and contains P26 support artifacts:
  - `usageBuffer.js`
  - `usageDb.js`
  - `UsageStats.js`
  - `usage-writer.mjs`
  - `9router-usage-writer.service`
  - local-only helper scripts such as `smoke-buffer.mjs`, `check-smoke-rows.mjs`, `inspect-xreadgroup.mjs`, `p26-loadtest.mjs`
- Deployed repo root:
  - `/root/9router`
- Deployed git base commit at check time:
  - `0c47c891e7a6c1a47c35b286235a132c0a5aa0a8`
- Deployed worktree is dirty and contains uncommitted changes.

## Source-of-Truth Verdict
- The authoritative deployed P26.1 source currently lives in:
  - `/root/9router` for application/runtime code
  - `/etc/systemd/system/9router-usage-writer.service` for the writer unit
- The authoritative local evidence/control path lives in:
  - `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\`
- The local staging path:
  - `C:\Users\faizz\guinevere\.codex\staging\p26-redis-write-buffer`
  is a partial mirror / operator staging area, not the full authoritative source tree.
- The Guinevere repo itself is **not** a synced source checkout of `/root/9router`.

## Sync Assessment
- Confirmed hash matches between staging and deployed files:
  - `usageBuffer.js`
  - `usageDb.js`
  - `UsageStats.js`
  - `usage-writer.mjs`
  - `9router-usage-writer.service`
- Not mirrored in local repo source tree:
  - all deployed 9Router source files under `/root/9router/...`
- Therefore the source of truth is clear enough for runtime audit, but **not repo-synced** in this workspace.

## Deployed Worktree State
- P26-related deployed files known changed or added:
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
- Additional deployed worktree drift detected outside the minimal mirrored staging set:
  - `src/lib/db/adapters/betterSqliteAdapter.js`
  - `src/lib/db/adapters/bunSqliteAdapter.js`
  - `src/lib/db/adapters/nodeSqliteAdapter.js`
  - untracked `.next-build-backup/`
  - untracked `server.js`

## Doc-Sync Impact
- Because this workspace does not contain the authoritative 9Router repo, a deployed artifact manifest is mandatory and has been created.
- Any final status stronger than `PASS WITH LIMITATION` must be justified against this split-source reality.

## Boundary Compliance
- No source files were modified during this check.
- No runtime state was changed.
- No secrets were captured.

## Rollback / Re-run Safety
- Read-only path, hash, and git-state inspection only.
- Safe to re-run.

## Design Decisions / Caveats
- The cleanest statement today is:
  - runtime authority = VPS `/root/9router`
  - service-unit authority = `/etc/systemd/system/9router-usage-writer.service`
  - evidence authority = local Guinevere docs tree
  - local staging = partial mirror plus helper harnesses
- That is workable for audit and rollback, but it is not the same as "deployed source is fully synced into this repo".

## Auditor Gate
- This file must be cited by the `architecture`, `evidence-docs`, and `rollback-idempotency` auditors.

## Security Scan
- Only hashes, file paths, and git-state metadata were recorded.
- No secrets, tokens, or environment contents were printed.

## Acceptance Criteria Mapping
- Exact source-of-truth paths documented: pass
- Deployed artifact manifest required and created: pass
- "works on VPS but repo unclear" not left implicit: pass
- Full repo-sync to this workspace: fail

## Footer
- Source-of-truth verdict: `DEPLOYED SOURCE CLEAR, LOCAL REPO NOT AUTHORITATIVE`.
