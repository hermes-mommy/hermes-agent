# P22 Production Activation — P19/P20 Regression Proof (T14)

**Date:** 2026-06-27
**Step:** T14 — Prove P22 activation did not regress P19/P20

## P19 Regression Checks

| Check | Expected | Actual | ✓ |
|---|---|---|---|
| `feature:projects:enabled` Redis flag | true | (P19 production-complete, flag ON per p19-012 final report) | ✓ |
| `LIFE_KERNEL_PROJECT_ID` env | `00000000-0000-0000-0000-000000000001` | present in `.env.core` | ✓ |
| P19 audit journal `project_id` propagation | live | P22 audit log event carries `project_id=00000000-0000-0000-0000-000000000001` | ✓ |
| P22↔P19 boundary: ProjectRegistry | no shim needed | P19 `ProjectRegistry` implements `get`/`resolve`/`list_active` matching P22 protocol | ✓ |
| P19 schema intact | yes | migration p22_001 created NEW schema `p22` + NEW table `audit.integration_api_log`; did NOT touch `projects.*` | ✓ |

## P20 Regression Checks (5-min window post-P22-restart 23:16:36 WIB)

| Check | Expected | Actual | ✓ |
|---|---|---|---|
| `guinevere-core` active | active | active | ✓ |
| NRestarts | 0 (since restart) | 0 | ✓ |
| Result | success | success | ✓ |
| MemoryCurrent < 2GB | yes | 722 MB | ✓ |
| `hermes_brain_think_complete` (5 min) | >0 | 8 | ✓ |
| `hermes_brain_fallback_used` (5 min) | 0 | 0 | ✓ |
| `dashboard_edited` (5 min) | >0 | 9 | ✓ |
| `dashboard_publish_failed` (5 min) | 0 | 0 | ✓ |
| `dashboard_edit_failed` (5 min) | 0 | 0 | ✓ |
| `GraphRecursionError` | 0 | 0 | ✓ |
| `HARD_STOP requested - routing to END` | 0 | 0 | ✓ |
| `hard_stop_detected_live` | 0 | 0 | ✓ |
| `hermes_brain_think_failed` | 0 | 0 | ✓ |
| `heartbeat_stopped` | 0 | 0 | ✓ |
| Redis `life_kernel:hard_stop` | clear (empty) | empty | ✓ |
| Discord REST canonical embed 1519135545501028549 | present, edited, blurple | present, edited 16:07:54 UTC, color 0x5865f2 | ✓ |
| Log channel 1510914623367413850 fresh events | yes | cycles 939/948 append-only | ✓ |

## P22↔P20 Boundary Proof

- `grep -rn "from src.life_kernel" src/life_integrations/` → 0 hits (P22 does not import P20 closed modules).
- `wiring.py` calls only `IntegrationRegistry.register()`, NOT `life_kernel.SensorRegistry.register()`.
- `runtime.py` is additive; `main.py` lifespan injection is a new try/except block that fails OPEN (P22 failure does not crash guinevere-core).
- No P20 closed file (`heartbeat*`, `cognition.py`, `hermes_brain.py`, `dashboard_writer.py`, `sensors.py`) was modified.
- Restart of `guinevere-core` is the primary service restarted. NOTE (audit r1 M4
  correction): `guinevere-discord` and `guinevere-mcp` declare
  `Requires=guinevere-core.service`, so systemd tore them down and brought them
  back in lockstep during the restart (stopped+started at 23:16:27-28 WIB).
  Both came back active within ~1s; NRestarts stayed 0 (graceful). 9Router,
  whatsapp, monitoring, obscura, x-poster, cloudflared, docker were NOT touched
  (no `Requires=guinevere-core`). No runtime impact.

## Pre-existing Issue (not a P22 regression)

- `tests/life_kernel/test_sensors.py::test_sense_all_skips_failing_adapter` fails locally due to a `TypeError` in untracked `src/life_kernel/sensors.py:140` (`zip(*adapters)` on empty). This is **pre-existing P20 untracked code**, NOT caused by P22 (P22 does not touch sensors.py). Documented, not fixed (out of P22 scope; P20 is CLOSED).
- `milestone_init_failed` startup `RuntimeWarning` (persona/milestone_engine.py:872) fires on every startup, pre-existing, not P22-related, not in P20 blocker list.

## Verdict

**P19/P20 regression: NONE.** P22 activation is purely additive, did not touch
P19 schema or P20 closed files, and the P20 runtime remained CLEAN across all
dimensions post-restart. P19 project_id propagation confirmed in P22 audit
events. P20 soak clock reset to 23:16:36 WIB (authorized deploy restart).

**Hard rejection criterion "P19/P20 regression not checked" → PASS.**
