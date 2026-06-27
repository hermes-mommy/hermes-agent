# P22 Production Activation — Round 1 Audit: P20 Regression Dimension

**Auditor:** Claude (independent audit sub-agent, READ-ONLY, no secrets printed)
**Date:** 2026-06-27
**Audit Dimension:** `p20-regression`
**Source claims:** `runtime/p22-p19-p20-regression-proof.md`, `deploy/p22-deploy-evidence.md`
**VPS verified:** `faiz-prod-01` (ssh guinevere-vps, Tailscale 100.94.104.22)

---

## Verdict

**NEEDS_REVIEW**

P20 runtime is healthy post-P22-activation across all runtime dimensions (cadence, no blockers, HARD STOP not set, dashboards editing). P22↔P20 boundary is preserved in code (no `from src.life_kernel` imports in P22; P22's own `IntegrationRegistry.register()`, not P20's `SensorRegistry`). The migration is applied (alembic_version = p22_001_integration_schema, 12 registry rows, WORM enforced on `audit.integration_api_log`).

Two non-blocking factual deviations from the docs require clarification before round-2 sign-off:

1. **The regression-proof claim "no other systemd service restarted" is INACCURATE.** The journal proves `guinevere-discord` and `guinevere-mcp` were each stopped + started at 23:16:27–23:16:28 WIB (within 1 second of `guinevere-core`). Root cause is the systemd dependency chain — both units have `Requires=guinevere-core.service` in their unit files — NOT operator action. Both came back up cleanly (NRestarts=0, state=running), so no runtime impact, but the docs should be corrected.
2. **The docstring of `wiring.py` says it "uses existing SensorRegistry.register() API"** but the actual code calls P22's own `IntegrationRegistry.register()` (no P20 import). The docstring is misleading wording — the runtime boundary is structurally correct (grep `from src.life_kernel` = 0). Recommend a docstring correction.

The runtime itself passes every hard-rejection criterion (no crash loop, no fallback storm, no HARD STOP, no recursion, dashboard alive, cadence healthy). Round 2 will close the doc-vs-journal discrepancy by either correcting the proof file or adding a post-activation systemd dependent-restart waiver.

---

## Findings

| # | Severity | Title | Detail | Evidence |
|---|---|---|---|---|
| F-01 | medium | Doc claim "only guinevere-core was restarted" is factually inaccurate | The proof file asserts "Restart of `guinevere-core` is the ONLY service restarted." Journal queries show `guinevere-discord.service` and `guinevere-mcp.service` were each Stopped and Started at 23:16:27–23:16:28 WIB (same window as core). Cause: both unit files declare `Requires=guinevere-core.service`, so when core was restarted systemd tore down dependents in dependency order and brought them back. NRestarts counter stayed 0 because the restart was graceful, not a crash-loop. No runtime impact (discord came back at 23:16:28 WIB, mcp at 23:16:28 WIB, both `state=running`), but the doc claim should be corrected. | `journalctl -u guinevere-{discord,mcp,core} --since "6 hours ago"` — three matching Stop/Start pairs at 23:16:27–28 WIB; `/etc/systemd/system/guinevere-{discord,mcp}.service` line `[Unit]` `Requires=guinevere-core.service`. |
| F-02 | low | `wiring.py` docstring says "uses existing SensorRegistry.register() API" | The module-level docstring of `src/life_integrations/wiring.py` references P20's `SensorRegistry.register()` API. The actual implementation calls `IntegrationRegistry.register()` on the P22-owned `IntegrationRegistry` class (defined in `src/life_integrations/registry.py`). The runtime boundary is preserved (`grep "from src.life_kernel" src/life_integrations/` = 0 matches verified live), but the docstring is misleading. | `src/life_integrations/wiring.py:1-7` (docstring); `src/life_integrations/registry.py:31-71` (IntegrationRegistry definition); live VPS grep returns 0 hits. |
| F-03 | info | MemoryCurrent at 638MB > reported 722MB after restart | The doc claims MemoryCurrent=722MB post-restart. Live SSH shows 638MB (lower — favorable, but a value gap from the doc). Likely measurement timing variability between 23:16:36 WIB and 23:38 WIB (snapshot now). Below the 2GB `MemoryHigh` threshold — not a concern. | `systemctl show guinevere-core -p MemoryCurrent` (live) → 638500864 bytes; MemoryHigh=2147483648; doc states 722 MB. |
| F-04 | info | Dashboard cadence 8 edits/5min — slightly under doc's "9" but consistent | Live `dashboard_edited` count over the last 5 min was 8 (vs doc's "9"). `hermes_brain_think_complete` similarly 8. Both are >= 1 (the threshold); not a regression. Cadence steady ~1.6/min. | `journalctl -u guinevere-core --since "5 min ago"`; doc claims 9 each; live grep yields 8 each. |
| F-05 | info | `audit.audit_trail` is empty (0 rows) | The P19 audit trail table has zero rows. P19-012 production report claims the chain is "live"; the regression-proof.md cites "P22 audit log event carries `project_id`" as confirming P19 project_id propagation. Either P19 audit events have not been emitted yet (recent deployment), or the audit chain is still warming up. Not a blocker for P20 regression. | DB query `SELECT count(*) FROM audit.audit_trail` → 0 (live). |

---

## What Was Verified

**Live VPS state (2026-06-27 23:30–23:38 WIB):**

| Check | Live Result | Doc Claim | Match? |
|---|---|---|---|
| `systemctl is-active guinevere-core` | active | active | ✓ |
| `systemctl is-active guinevere-discord` | active | active | ✓ |
| `systemctl is-active guinevere-mcp` | active | active | ✓ |
| `systemctl show guinevere-core -p NRestarts` | 0 | 0 | ✓ |
| `systemctl show guinevere-core -p Result` | success | success | ✓ |
| `systemctl show guinevere-core -p ActiveEnterTimestamp` | Sat 2026-06-27 23:16:28 WIB | 23:16:36 WIB | ~ (8 sec earlier than doc; consistent with restart cycle observed in journal) |
| `systemctl show guinevere-core -p MemoryCurrent` | 638 MB | 722 MB | slight miss (F-03) |
| All 9 unrelated services (9Router, 9router-proxy, whatsapp, monitoring, obscura, x-poster, cloudflared, docker, guinevere-9router) | active | active | ✓ |
| `grep "from src.life_kernel" src/life_integrations/` | 0 matches | 0 | ✓ |
| `integration_registry.register()` call target | P22's `IntegrationRegistry.register` (own class) | Not P20's `SensorRegistry.register` | ✓ (boundary preserved) |
| P20 closed files (heartbeat, cognition, hermes_brain, dashboard_writer, sensors) mtimes | 2026-06-24 to 2026-06-27 — none after P22 deploy (mtime 22:46 main.py / 23:15-16 runtime/_shims) | not modified | ✓ |
| `redis.get("life_kernel:hard_stop")` (live Python) | None (empty) | empty | ✓ |
| `redis-cli GET life_kernel:dashboard_message_id` (via python) | None (empty) — runtime discovers dashboard dynamically | — | ✓ |
| `dashboard_edited` count, 5-min window | 8 (live) | 9 | F-04 (info) |
| `hermes_brain_think_complete` count, 5-min window | 8 (live) | 8 | ✓ |
| `GraphRecursionError` count, 5-min | 0 | 0 | ✓ |
| `hermes_brain_fallback` count, 5-min | 0 | 0 | ✓ |
| `dashboard_publish_failed` count, 5-min | 0 | 0 | ✓ |
| `heartbeat_stopped` count, 5-min | 0 | 0 | ✓ |
| `hard_stop_detected_live` count, 5-min | 0 | 0 | ✓ |
| `hermes_brain_think_failed` count, 5-min | 0 | 0 | ✓ |
| `dashboard_edit_failed` count, 5-min | 0 | 0 | ✓ |
| `HARD STOP requested - routing to END` count, 5-min | 0 | 0 | ✓ |
| Discord dashboard message target | `1519135545501028549` (continuously edited) | `1519135545501028549` | ✓ |
| Embed color (code-defined) | 0x5865F2 (blurple) when not hard_stop; 0xED4245 when hard_stop | 0x5865f2 (blurple) | ✓ |
| `LIFE_KERNEL_LOG_CHANNEL_ID` env | `1510914623367413850` (in `.env.discord`) | matches doc | ✓ |
| `LIFE_KERNEL_PROJECT_ID` env present in `.env.core` | confirmed (referenced via projects.project_registry UUID `00000000-0000-0000-0000-000000000001`) | present | ✓ |
| DB schemas (`ops`, `audit`, `consent`, `projects`, `p22`) | all present | — | ✓ |
| `p22.schema` tables | 2 (`integration_registry`, `secret_ref_metadata`) | 2 | ✓ |
| `audit.schema` tables | 4 (`audit_trail`, `compliance_check`, `evidence_register`, `integration_api_log`) | 4 (last new) | ✓ |
| `projects.project_registry` rows | 1 (slug=default, status=active) | 1 | ✓ |
| `ops.alembic_version` rows | 1 (value = `p22_001_integration_schema`) | 1 | ✓ |
| `p22.integration_registry` rows | 12 — all `enabled=False`, all `config_status='config_missing'` | 12 | ✓ |
| `audit.integration_api_log` rows | 0 (no P22 production traffic yet) | 0 | ✓ |
| WORM grants (guinevere_core on `audit.integration_api_log`) | INSERT/SELECT/REFERENCES/TRIGGER/TRUNCATE only (no UPDATE, no DELETE) | WORM enforced | ✓ |
| Lifecycle event in last 6h: guinevere-core | Stop at 23:16:27 | Stop at 23:16:27 | ✓ |
| Lifecycle event in last 6h: guinevere-discord | ALSO Stop at 23:16:27 + Started at 23:16:28 | "untouched" | F-01 (medium) |
| Lifecycle event in last 6h: guinevere-mcp | ALSO Stop at 23:16:27 + Started at 23:16:28 | "untouched" | F-01 (medium) |
| `reflect_node_complete` 30-min window | cycles 995→997 (steady climb, errors=0) | healthy | ✓ |
| 5-min secret-leak grep across `guinevere-core` journal | no secret/token/password/PAT/API-key prints | clean | ✓ |

---

## Hard-Rejection Check

| Hard-Rejection Criterion | Result |
|---|---|
| **Secrets printed:** No secret/token/password/PAT/API key value echoed in any log output across round-1 audit. Discord bot token reference is in `.env.core`/`env.discord` files (pre-existing, not printed or modified by P22 deploy). | PASS |
| **Fake PASS:** No claim of "P22 production live" vs. reality. P22 integration_registry has 12 rows but all `enabled=False, config_status='config_missing'` — honest representation of "library wired, no live traffic." 10/13 adapters CONFIG_MISSING per activation report matches the live DB (`enabled=False` for all 12). | PASS |
| **HARD STOP not blocking L2+:** Audit-log query confirms ZERO `HARD_STOP requested`, `hard_stop_detected_live`, or related entries in 5-min + 6-hour windows. Redis `life_kernel:hard_stop` is empty. | PASS |
| **Migration not applied but claimed pass:** `ops.alembic_version.version_num = "p22_001_integration_schema"` — applied & stamped clean. Schema `p22` has 2 tables. 12 registry rows. | PASS |
| **P20 closed file modification:** `git status` shows ~30 modified files on VPS (scp/tar-deploy strategy, not git commit), but `src/life_kernel/heartbeat.py`, `cognition.py`, `hermes_brain.py`, `dashboard_writer.py`, `sensors.py` are NOT in the modified list — confirmed by file mtimes (all pre-date P22 deployment at 22:46–23:16 WIB). | PASS |
| **P22 import-boundary violation:** `grep -rn "from src.life_kernel" src/life_integrations/` returns 0 matches. Wiring uses P22's own `IntegrationRegistry.register()`. | PASS |
| **Dashboard publishing crash:** dashboard_edited successfully logs 1519135545501028549 at a steady ~1.6/min. | PASS |
| **Recursion/fallback/heartbeat-stop:** All zero in 5-min + 6h windows. | PASS |

No hard-rejection criterion violated. Verdict cannot be hard-FAIL.

---

## Recommendations

1. **Correct the proof file** (§"P22↔P20 Boundary Proof"): the line "Restart of `guinevere-core` is the ONLY service restarted; 9Router/discord/etc untouched" should be amended to acknowledge that `guinevere-discord` and `guinevere-mcp` have `Requires=guinevere-core.service` and therefore tore down/restarted in lockstep. This is benign systemd behavior (NRestarts=0, 1-second cycle time, fresh process PIDs) but the doc claim should reflect the truth.

2. **Fix `wiring.py`** module docstring (line 1-7): replace the misleading "uses existing SensorRegistry.register() API" wording with the correct statement: "registers adapters with P22's own `IntegrationRegistry.register()`; does NOT call any P20 API; P22 imports 0 P20 modules."

3. **Add audit-trail initialization**: `audit.audit_trail` is empty (0 rows). If P19 audit-chain is supposed to be active, investigate why no rows are present. Out of scope for P22 regression but should be tracked for round 2 if still empty.

4. **Add a regression-proof firewall between P22 restart and dependent services**, OR document the systemd dep behavior in `deploy/p22-deploy-evidence.md` so the next operator is not surprised by the dependent restart cycle.

5. **No code changes recommended.** Runtime is healthy, codebase boundary is preserved, migration is correct, dashboard is alive. Only doc strings need correction.

---

## Pre-existing / Out-of-Scope

- `tests/life_kernel/test_sensors.py::test_sense_all_skips_failing_adapter` is failing in local P20 zone (TypeError in `src/life_kernel/sensors.py`). Pre-existing, NOT caused by P22 (P22 does not touch `sensors.py`). Out-of-scope for P22 activation (P20 is CLOSED).
- `milestone_init_failed` `RuntimeWarning` from `persona/milestone_engine.py:872` on every startup. Pre-existing, not P22-related, not in P20 blocker list.
- `recall_degraded` 24h averaging ~3.3/h. Below P20 threshold; soft monitor, not blocker.
- `audit.audit_trail` empty — likely because P19 audit-chain is in passive mode (no event types triggered yet). Not a P22 regression.

---

## Footer

Audit performed 2026-06-27, 23:30–23:38 WIB via SSH to VPS without any destructive operation, restart, env modification, secret exposure, or DB write. All source evidence (live journal, syscall/filesystem state, DB introspection) is reproducible for round 2 via the recorded commands.
