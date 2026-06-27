# P22 Production Activation — Real Client Wiring (T7-T10)

**Date:** 2026-06-27
**Steps:** T7 (_shims.py) + T8 (memory_pipeline_shim.py) + T9 (runtime.py) + T10 (main.py lifespan)
**Commits:** `fdf6f33`

## Design: Additive Wiring (no P20 closed-file changes)

P22 activation is wiring, not a rewrite. 3 new files + 1 lifespan edit.

## T7 — `_shims.py` (safety-critical)

Two shims bridge existing Guinevere services to P22 protocols:

### HardStopShim
- **Problem:** P22 `ConsentGate.check()` (consent.py:106) calls `is_hard_stop_active()` synchronously. The app's `redis_client` is async (`redis.asyncio.Redis`) — its `.get()` returns a coroutine not awaitable from sync context.
- **Fix:** the runtime factory constructs a **sync** `redis.Redis` client (separate from async) and passes it to the shim. `is_hard_stop_active()` checks Redis `life_kernel:hard_stop` (P20 authority) + `HardStopHandler.is_safe` (in-process), conservative OR.
- **Verified:** T3 gate smoke with `life_kernel:hard_stop=1` → `HardStopBlockedError: HARD STOP active — action blocked`.
- **Bug found+fixed mid-deploy:** initial version silently returned False for async redis (coroutine not awaited) → HARD STOP bypass. Fixed by sync-redis construction + warning on async-redis-in-sync-path.

### ConsentGateShim
- **Problem:** existing consent checkers return `ConsentCheckResult(allowed: bool, ...)`; P22 protocol expects `check_consent() -> bool`.
- **Fix:** shim extracts `.allowed`; fail-closed on None checker, exception, or ambiguous result.
- **Verified:** T2 gate smoke (no consent checker) → `ConsentDeniedError` (L2+ fail-closed).

## T8 — `memory_pipeline_shim.py` (for future memory wiring)

`MemoryWritePipelineShim` / `MemoryReadPipelineShim` / `KGQueryShim` wrap
module-level functions (`store_episode`, `recall_memories`) + `KGQueryEngine.search_entities`
as instance protocols the memory adapter expects. Uses `get_async_session`
(canonical session provider). Memory adapter left CONFIG_MISSING in this phase
(shim built + tested for import, but full memory wiring is a follow-up to
avoid rushing session-pool integration).

## T9 — `runtime.py` factory

`build_runtime_registry()` constructs:
- **filesystem** ACTIVE: `workspace_root="/home/guinevere/code/guinevere"` (no client needed).
- **vps** ACTIVE: `DockerClientShim` (parses `docker ps --format {{json .}}` stdout) + `ShellClientShim` (forwards to `shell_exec`).
- **discord** ACTIVE: `DiscordRestShim` wrapping `DiscordRestClient` (maps `get_messages`→`get_recent_messages`, `delete_message` via REST, `health()`=`enabled`).
- 10 adapters CONFIG_MISSING (None): gmail, calendar, drive, notion, telegram, github, browser, memory, finance, whatsapp.
- Sync redis client for HardStopShim.

## T10 — `main.py` lifespan injection

Added ~30 LOC in `lifespan()` after heartbeat start (line ~453):
```python
from src.life_integrations.runtime import build_runtime_registry
_p22_registry, _p22_router = await build_runtime_registry(
    redis_client=redis_client,
    hard_stop_handler=app.state.hard_stop_handler,
    consent_checker=None,  # fail-closed L2+ until consent wired
    project_registry=None,
    audit_writer=None,
    workspace_root=os.environ.get("GUINEVERE_REPO_ROOT") or "/home/guinevere/code/guinevere",
    discord_rest_client=discord_rest,
)
app.state.p22_registry = _p22_registry
app.state.p22_router = _p22_router
```
Wrapped in try/except → fail-OPEN for app (P22 failure logs `p22.activation_failed`, core continues).

## Interface Mismatches Resolved (parent-verified)

| P22 protocol expects | Real Guinevere | Resolution |
|---|---|---|
| `is_hard_stop_active()` | `HardStopHandler.is_safe` | HardStopShim (sync redis + is_safe) |
| `check_consent() -> bool` | `ConsentCheckResult` | ConsentGateShim (.allowed, fail-closed) |
| `ProjectRegistry.resolve/get/list_active` | P19 ProjectRegistry has them | NO shim needed ✓ |
| `discord_rest.get_messages/delete_message/health` | DiscordRestClient has `get_recent_messages`, lacks others | DiscordRestShim |
| `docker.list_containers()` | `_run_docker()` module func | DockerClientShim (parses JSON stdout) |
| `shell.run(cmd)` | `shell_exec()` module func | ShellClientShim |

## Verification

- Local: P22 tests 76 passed; `main.py` imports OK; 0 forbidden patterns; 0 secrets in code.
- VPS: `p22_integration_hub_active` log; health_check_all 3 OK + 10 UNKNOWN; gate smoke T1-T4 pass; HARD STOP blocks L2+.

## Accepted Gaps (honest, documented)

1. **10 adapters CONFIG_MISSING**: 5 operator-gated creds (gmail/calendar/drive/notion/telegram) + 5 need shim-testing (github/browser/memory/finance/whatsapp). All report UNKNOWN honestly.
2. **audit_writer=None**: P22 AuditLogger not yet wired to `audit.integration_api_log` (existing `PostgresAuditJournal` targets `life_kernel.audit_journal`). Audit events emit to structured log (with project_id) but not the P22 table. L2+ actions are fail-closed, so no L2+ audit rows would exist yet anyway. Follow-up.
3. **consent_checker=None**: L2+ fail-closed until P19/surveillance consent ledger wired as checker. Safe default.

## Footer

Wiring is additive, safety-critical shims verified, no fake PASS. 3 ACTIVE +
10 honest CONFIG_MISSING.
