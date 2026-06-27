# P22 Production Activation — Deploy Evidence (T3 + T12 + T13)

**Date:** 2026-06-27
**VPS:** faiz-prod-01 (ssh guinevere-vps, Tailscale 100.94.104.22)
**Operator mode:** Full autonomous (per-action approved)
**Commits:** `ec53f70` (P22 core + migration), `fdf6f33` (Phase B runtime wiring)

## Deploy Summary

Two-phase deploy. Phase A: library + migration (low-risk, importability no-op). Phase B: runtime wiring + lifespan injection (restart required).

## Phase A — T3: Code Deploy

**Method:** `tar -czf - -C src life_integrations | ssh ... tar -xzf -` + `scp` for migration files (rsync not available on Windows Git Bash).

| Artifact | VPS Path | Verified |
|---|---|---|
| `src/life_integrations/` (14 modules + 14 adapters + `_clients/`) | `/home/guinevere/code/guinevere/src/life_integrations/` | 14 .py + 14 adapters ✓ |
| `alembic/versions/p19_003_audit_chain_version.py` | `.../alembic/versions/` | present ✓ |
| `alembic/versions/p22_001_integration_schema.py` | `.../alembic/versions/` | present ✓ |

**No `.env.core` modification.** No P20 closed file touched.

## Phase A — T5: Migration Apply

See `implementation/p22-migration-application.md` for full detail. Summary:
- Direct idempotent DDL (alembic `upgrade` blocked by branch-overlap; DDL is IF NOT EXISTS so applied directly via asyncpg, then `alembic stamp p22_001`).
- Post: schema p22 + 2 tables + 12 registry rows + audit.integration_api_log; WORM enforced (UPDATE/DELETE revoked from guinevere_core).

## Phase A — T6: Importability Smoke

`.venv/bin/python -c "import importlib; ...16 P22 modules..."` → **16/16 OK, 0 fail**.

## Phase B — T12: Wiring Deploy

| Artifact | Deployed |
|---|---|
| `src/life_integrations/runtime.py` | ✓ (tar via ssh) |
| `src/life_integrations/_shims.py` | ✓ |
| `src/life_integrations/adapters/_clients/` | ✓ |
| `src/core/main.py` (lifespan injection) | ✓ (scp) |

**P22 injection in VPS main.py:** `grep -c build_runtime_registry` = 3 ✓.

## Phase B — T13: Restart + Runtime Smoke

**Restart:** `sudo systemctl restart guinevere-core` ONLY (23:16:36 WIB final, after HARD STOP shim fix).

| Check | Result |
|---|---|
| guinevere-core post-restart | active, NRestarts=0, Memory 722MB |
| Other services (9Router/discord/mcp/whatsapp/monitoring/obscura/x-poster/cloudflared/docker) | ALL still active ✓ |
| `p22_integration_hub_active router=ActionRouter` log | present ✓ |
| `p22.adapter.wired adapter=discord/vps/filesystem` | present ✓ |
| `p22.adapter.config_missing` (10 adapters) | present, honest ✓ |
| `p22.hard_stop_shim.sync_redis_ready` | present (post-fix) ✓ |
| Health endpoint `/health/detailed` | 200, postgresql/redis/9router/loop_manager/guardian all ok |
| `hermes_brain_think_complete` (5 min) | 8 (P20 alive) |
| `dashboard_edited` (5 min) | 9 |
| Blockers (GraphRecursionError/heartbeat_stopped/fallback/publish_failed) | 0 |
| Secret leak scan (logs) | 0 |

## HARD STOP Shim Fix (mid-deploy)

Initial Phase B restart (22:46:48 WIB) revealed the HardStopShim could not
detect the Redis `life_kernel:hard_stop` key from the sync consent-gate path
(async redis `.get()` returns a coroutine, not awaitable in sync context).
T3 gate smoke confirmed the bug: HARD STOP did not block (fell through to
consent). Fix: runtime factory constructs a SYNC `redis.Redis` client for the
shim. Redeployed `_shims.py` + `runtime.py`, restarted (23:16:36 WIB).
Post-fix T3: `HardStopBlockedError: HARD STOP active — action blocked` ✓.

## Final Runtime State

- 3 adapters ACTIVE: filesystem, vps, discord (via shims)
- 10 adapters CONFIG_MISSING (honest): gmail, calendar, drive, notion, telegram, github, browser, memory, finance, whatsapp
- HARD STOP blocks L2+ ✓
- Consent fail-closes L2+ ✓
- P20 soak CLEAN ✓

## Footer

Deploy complete and verified. No service other than guinevere-core restarted.
No secrets exposed. Backup exists at `/home/guinevere/data/backups/guinevere-p22-predeploy-20260627T150750Z.sql.gz` (1.38 GB).
