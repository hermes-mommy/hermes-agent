# P22 Production Activation — Round 1 Fix Log

**Date:** 2026-06-27
**Audit round 1 verdict:** 5 PASS, 3 NEEDS_REVIEW, 0 FAIL (8 auditors)
**Findings addressed:** all HIGH + MEDIUM; LOW/INFO documented.

## Fixes Applied

### H1 — IntegrationScheduler never started (runtime-activation, HIGH)
**Finding:** `build_scheduler()` defined in wiring.py but lifespan never called `.start()`.
**Fix:** Added scheduler start to `src/core/main.py` lifespan P22 block:
```python
from src.life_integrations.wiring import build_scheduler
_p22_scheduler = build_scheduler(_p22_registry, interval_seconds=30)
await _p22_scheduler.start()
app.state.p22_scheduler = _p22_scheduler
```
(wrapped in try/except, fail-open). **Verified:** `p22_scheduler_started interval=30` log + 32 health_check events in 40s (background polling active).

### H2 — Live DB not independently verified (db-migration, HIGH)
**Finding:** db-migration auditor had no SSH; trusted operator evidence.
**Fix:** Parent independently re-verified live DB (see below). All post-conditions confirmed.

### H3 — HARD STOP bug not regression-pinned (consent-hardstop, HIGH)
**Finding:** The async/sync redis mis-wiring (T3 silent fallthrough) had no test to prevent regression.
**Fix:** Added `tests/p22/test_shims.py` with `TestHardStopShim` (6 tests) + `TestConsentGateShim` (5 tests). Key regression test: `test_sync_redis_hard_stop_set_returns_true` asserts `is_hard_stop_active()` returns True when sync redis has `life_kernel:hard_stop=1`. **Verified:** 87 P22 tests pass (76 + 11 new).

### M1 — check_status collapses UNKNOWN→HEALTHY (runtime-activation, MEDIUM)
**Finding:** `base.py:134-139` else-branch set HEALTHY for UNKNOWN (fake-PASS-adjacent).
**Fix:** `base.py` now maps UNKNOWN→`CONFIG_MISSING`, WARNING→`DEGRADED`, ERROR→`DEGRADED`, OK→`HEALTHY`, else→`DISABLED`. Honest status mapping.

### M2 — `__import__('datetime')` forbidden pattern (runtime-activation, MEDIUM)
**Finding:** `__import__('datetime')` in discord_adapter.py:173, whatsapp_adapter.py:118, project_context.py:149.
**Fix:** Replaced with top-level `from datetime import datetime, timezone` + `datetime.now(timezone.utc).isoformat()` in all 3 files. **Verified:** `grep -rn __import__ src/life_integrations/` → 0 (only stale .pyc, cleared).

### M3 — wiring.py docstring misleading (p20-regression, MEDIUM)
**Finding:** Docstring claimed "uses P20 SensorRegistry.register()" but code uses P22's own IntegrationRegistry.
**Fix:** Rewrote docstring to accurately state it wires P22's IntegrationRegistry (not life_kernel's SensorRegistry), 0 `from src.life_kernel` imports.

### M4 — "only guinevere-core restarted" inaccurate (p20-regression, MEDIUM)
**Finding:** guinevere-discord + guinevere-mcp have `Requires=guinevere-core`, so they restarted in lockstep.
**Fix:** Corrected `p22-p19-p20-regression-proof.md` (see below). All 3 came back active within 1s; NRestarts=0 (graceful).

### M5 — activation matrix delta (evidence-docs, MEDIUM)
**Finding:** Plan said 8 ACTIVE; smoke showed 3. The 5 (github/whatsapp/finance/browser/memory) were intentionally left CONFIG_MISSING (shims need testing).
**Fix:** Reconciled plan + smoke + final report to reflect actual 3 ACTIVE + 10 CONFIG_MISSING honestly.

### M6 — HARD STOP unset not documented (evidence-docs, MEDIUM)
**Finding:** Smoke didn't document the unset after the HARD STOP test.
**Fix:** Parent verified `redis-cli GET life_kernel:hard_stop` = empty (unset). Documented in smoke evidence.

### M7 — HardStopShim warns but doesn't raise on async redis (consent-hardstop, MEDIUM)
**Finding:** If async redis + no handler, HARD STOP silently falls through.
**Fix:** Added construction-time hard-fail in `_shims.py`: if `redis_client` module is `redis.asyncio.*` AND no handler → `RuntimeError` at construction (prevents silent disable). **Verified:** runtime still works (passes sync redis + handler).

## Parent Independent DB Re-Verification (H2)

Run directly by parent (not sub-agent) on live VPS:
```
alembic_version rows (1): ['p22_001_integration_schema']
schema p22 exists: True
p22 tables: ['integration_registry', 'secret_ref_metadata']
p22.integration_registry rows: 12
audit.integration_api_log exists: True (rows: 0 — no P22 L2+ actions yet)
WORM guinevere_core: INSERT=True SELECT=True UPDATE=False DELETE=False
project_id/project_scope columns: present
```
All migration post-conditions independently confirmed.

## Findings Documented (not fixed — LOW/INFO, out of scope or pre-existing)

- **L1** No HTTP endpoint for `health_check_all()` (low) — follow-up; logs + smoke suffice for now.
- **L2** DiscordRestShim.health() reads one-shot ctor flag (low) — benign, documented.
- **L3** DockerClientShim doesn't check exit_code (low) — _run_docker raises typed errors; safe.
- **L4** ShellClientShim.run defensive fallback (low) — cosmetic.
- **L5** Backup sha256 value not in evidence (low) — .sha256 file exists on VPS; value retrievable.
- **I1-I8** Various info findings (audit detector regex OK, secret_refs pattern correct, etc.) — no action.
- **Pre-existing** sensors.py test failure (untracked P20, not P22), milestone_init_failed startup warning — out of P22 scope, P20 CLOSED.

## Re-Verification After Fixes

- P22 tests: 87 passed (76 + 11 new test_shims).
- VPS restart: `p22_scheduler_started`, `p22_integration_hub_active`, `sync_redis_ready` — all present.
- HARD STOP gate smoke (post-fix): T3 `HardStopBlockedError: HARD STOP active` ✓, T4 `ConfigurationMissingError` ✓.
- No p22 errors in logs. Heartbeat alive. No blockers.
- `__import__` eliminated. No `# type: ignore` in changed files.

## Footer

All HIGH + MEDIUM round-1 findings fixed and re-verified. Ready for audit round 2.
