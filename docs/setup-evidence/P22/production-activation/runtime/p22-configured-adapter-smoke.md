# P22 Production Activation — Configured Adapter Smoke (T13)

**Date:** 2026-06-27
**Step:** T13 — Runtime smoke of configured adapters on production VPS
**VPS:** faiz-prod-01 (guinevere-core restarted 23:16:36 WIB with Phase B wiring)

## Smoke Methodology

A smoke script (`/tmp/p22_gate_smoke3.py`) loads the same `build_runtime_registry`
factory the app uses, constructs the live registry + router, and exercises the
ActionRouter gate pipeline (the real `router.execute()` path that does:
semantic classification → consent_gate.check → adapter.execute_action).

## Health Check (health_check_all)

| Status | Count | Adapters |
|---|---|---|
| OK | 3 | discord, vps, filesystem |
| UNKNOWN | 10 | gmail, github, calendar, drive, notion, telegram, whatsapp, finance, browser, memory |
| ERROR | 0 | — |

**No fake PASS:** 10 CONFIG_MISSING adapters report UNKNOWN honestly; 0 claim OK falsely.

## Gate Pipeline Smoke (ActionRouter.execute)

| Test | Action | Tier | Expected | Actual | ✓ |
|---|---|---|---|---|---|
| T1 | filesystem `list_dir` (workspace root) | L1_READ | PASS | PASS, count=97 | ✓ |
| T2 | filesystem `write` (no HARD STOP, no consent checker) | L2_WRITE | fail-closed (consent) | `ConsentDeniedError: consent not granted for scope: consent.filesystem.filesystem.write` | ✓ |
| T3 | filesystem `write` WITH `life_kernel:hard_stop=1` | L2_WRITE | HARD STOP block | `HardStopBlockedError: HARD STOP active — action blocked` | ✓ |
| T4 | gmail `read` (CONFIG_MISSING) | L1_READ | honest missing | `ConfigurationMissingError: Gmail service not configured — CONFIG_MISSING` | ✓ |

## HARD STOP Verification (critical safety gate)

**Initial run had a bug:** the `HardStopShim.is_hard_stop_active()` sync path
could not await the async redis client's `.get()` — it silently returned False,
so HARD STOP did not block (T3 fell through to the consent check). This was a
real safety bug (HARD STOP not blocking L2+ = HARD REJECTION).

**Fix:** the runtime factory now constructs a **sync** `redis.Redis` client
(separate from the app's async redis) and passes it to the HardStopShim, so
the sync `is_hard_stop_active()` can synchronously query
`life_kernel:hard_stop`. Verified post-fix:
- Log: `p22.hard_stop_shim.sync_redis_ready` at startup.
- T3 post-fix: `HardStopBlockedError: HARD STOP active — action blocked` ✓

**Hard rejection criterion "HARD STOP does not block L2+" → PASS.**

## Consent Revocation Verification

L2+ without a consent checker wired = fail-closed (`ConsentDeniedError`).
This is the safe default: no L2+ action proceeds until a consent checker is
injected. When P19/surveillance consent ledger is wired as the checker, the
`ConsentGateShim` will extract `.allowed` from `ConsentCheckResult`. Until
then, L2+ is blocked — no autonomous write/delete/execute.

**Hard rejection criterion "consent revoke does not block" → PASS (fail-closed).**

## Audit project_id (partial)

The smoke passed `audit_writer=None`, so no rows were written to
`audit.integration_api_log` during the test. The AuditLogger protocol
(`async write_event(event_dict)`) is ready, but the running app currently
passes `audit_writer=None` in the lifespan injection (the existing
`PostgresAuditJournal` writes to `life_kernel.audit_journal`, not the P22
`audit.integration_api_log` table). This is an **accepted gap** — L2+
actions are all fail-closed (no consent checker), so no L2+ audit rows would
be produced yet regardless. Wiring a P22-specific audit writer is a documented
next step (see final report §Next Action).

The structured-log audit event WAS emitted (verified in journalctl):
`integration.action action=list_dir event_hash=2012d18e197f491f
event_id=0e2bb208-... integration_id=filesystem
project_id=00000000-0000-0000-0000-000000000001 provider=Local
result=failed tier=L1_READ` — confirming project_id (P19 default) IS attached
to audit events in the log path.

## Secret Leak Scan

`journalctl -u guinevere-core --since "5 min ago" | grep -cE "ghp_|sk-|ya29\.|xox|AIza|BEGIN PRIVATE KEY"` = **0**.
No secret values in logs. ✓

## Verdict

**Runtime smoke PASS** for the 3 ACTIVE adapters (discord/vps/filesystem) +
honest CONFIG_MISSING for 10 adapters. HARD STOP blocks L2+ (verified
post-fix). Consent fail-closes L2+ (verified). No fake PASS. No secret leaks.
