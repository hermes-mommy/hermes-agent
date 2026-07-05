# P26.1 Rollback Instructions

Date: 2026-06-28
Scope: documentation only. No rollback was executed as part of finalization.

## Guardrails
- Require explicit operator approval before any rollback action.
- Do not change PM2 `9router` worker count from `2`.
- Do not open public IPv4 `49.12.82.34:20128`.
- Do not expose Redis beyond loopback.
- Do not use blind `git reset --hard` or assume this local repo is the deployed source of truth.

## Current Authoritative Paths
- App runtime authority: `/root/9router`
- Writer service authority: `/etc/systemd/system/9router-usage-writer.service`
- Local artifact manifest: `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\deployed-artifact-manifest.md`

## Pre-Rollback Capture
Run and save these before changing anything:
1. `pm2 list --no-color`
2. `pm2 show 9router`
3. `systemctl is-active redis-server 9router-usage-writer.service`
4. `redis-cli -h 127.0.0.1 -p 6379 XLEN 9router:usage_events:v1`
5. `redis-cli -h 127.0.0.1 -p 6379 XPENDING 9router:usage_events:v1 usage-writers`
6. `sqlite3 /var/lib/9router/db/data.sqlite 'pragma integrity_check;'`
7. backup `/root/9router`
8. backup `/etc/systemd/system/9router-usage-writer.service`
9. backup `/root/.pm2/dump.pm2`

## Choose an Explicit Rollback Target
Pick one explicit target before touching files:
1. A known-good VPS backup or tarball of `/root/9router`
2. A specific reviewed git commit already present on the VPS
3. A reviewed artifact set that matches the manifest and the intended rollback state

Do not proceed with rollback unless the target is named and verified.

## Restore Sequence
1. Restore the chosen `/root/9router` target.
2. Restore the intended writer unit file at `/etc/systemd/system/9router-usage-writer.service`.
3. If the chosen target requires a rebuild, run the target's normal install/build flow.
4. Reload systemd if the unit file changed:
   - `systemctl daemon-reload`
5. Start the selected app runtime with exactly `2` PM2 workers.
6. Start or stop `9router-usage-writer.service` only if the chosen rollback target explicitly requires that state.
7. Save the PM2 process list after the runtime is stable:
   - `pm2 save`

## Post-Rollback Validation
Rollback is incomplete until all of these pass:
1. `pm2 list --no-color` shows exactly `2` online `9router` workers
2. `pm2 show 9router` points at the intended entrypoint
3. `systemctl is-active redis-server` is `active`
4. `sqlite3 /var/lib/9router/db/data.sqlite 'pragma integrity_check;'` returns `ok`
5. `redis-cli -h 127.0.0.1 -p 6379 XPENDING 9router:usage_events:v1 usage-writers` does not show stuck growth
6. Tailscale endpoint is reachable in the expected auth mode
7. Public IPv4 `49.12.82.34:20128` remains blocked
8. Redis still listens only on loopback

## If Rollback Is Not Clean
- Stop and preserve evidence.
- Re-enable the last known good writer/app state if possible.
- Do not keep iterating with guessed targets.
- Escalate with:
  - chosen rollback target
  - command transcript
  - PM2 state
  - Redis stream state
  - SQLite integrity result

## Practical Note
Because the authoritative deployed source is the VPS worktree and that worktree is dirty, rollback should be treated as an artifact-driven operation, not a local-repo-driven one.
