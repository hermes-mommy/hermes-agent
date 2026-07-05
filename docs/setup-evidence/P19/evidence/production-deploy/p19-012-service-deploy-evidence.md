# P19-012 Service Deploy Evidence

**Date:** 2026-06-27 08:45 WIB
**Author:** Guinevere (parent)
**Phase:** 6 — Runtime Deploy / Service Restart

---

## 1. Deploy Strategy

**SURGICAL — no restart of guinevere-core.**

Rationale:
- The running core (ActiveEnter 2026-06-25 08:26:43 WIB) already has the P19 life_kernel wiring deployed in a prior session (cognition.py, heartbeat.py, graph.py, dashboard_writer.py, redis_client.py all contain the `feature:projects:enabled` flag-gated paths).
- The DDL applied in Phase 4 is purely additive (nullable columns, indexes, registry table). The already-running code references these via the flag-OFF transparent path.
- The flag is OFF (Redis `feature:projects:enabled = None`), so P19 code paths are byte-identical to P20.
- Restarting would reset the P20 soak clock and risk disruption for zero benefit.

## 2. Files Deployed via scp

The following P19 files were missing on the VPS (VPS git HEAD is `123a31a` — P11; P19 work was deployed via scp, not git). Deployed to complete the PRODUCTION state:

| File | Purpose | Imported by running core? |
|---|---|---|
| src/discord/cmd_project.py | P19-007 `/project` Discord command | No (not registered in active bot's command tree — see §2a) |
| src/discord/project_session.py | P19-008 project-aware session | No (flag-gated, loaded on demand) |
| src/projects/secrets_vault.py | P19-006a ProjectSecretsVault | No (flag-gated, loaded on demand) |
| scripts/p19_backfill.py | P19-011 backfill utility | No (one-shot script) |
| scripts/p19_001_deploy.py | Phase 4 deploy script | No (one-shot, already executed) |
| scripts/p19_002_003_deploy.py | Phase 4 deploy script | No (one-shot, already executed) |

**None of the deployed files are imported by the running `guinevere-core.service`.** Deploying them is non-disruptive.

## 2a. Correction — guinevere-discord.service state (audit round-1 UX-04)

An earlier draft of this evidence stated the discord bot was "masked". **This was incorrect.** Verified live on VPS during audit round-1 (UX-04):

- `systemctl is-enabled guinevere-discord.service` → **enabled**
- `systemctl is-active guinevere-discord.service` → **active**
- Unit file `/etc/systemd/system/guinevere-discord.service` is a real file (dated Jun 25 19:37), NOT a `/dev/null` symlink. A `.bak` (Jun 24 07:28) exists alongside.

The bot is running (polling x-poster API at 8097, serving its existing 13 slash commands). This is a **pre-existing P20-closure state drift** — the masking applied 2026-06-24 did not persist (unit file restored Jun 25 19:37). It is **NOT caused by P19-012** and is **NOT a P19 functional blocker**, because:

1. The P19 `/project` command (`cmd_project.py`) is **NOT registered** in the active bot's command tree (verified: no `cmd_project`/`/project` reference in `_entrypoint.py`/`_command_registry.py`/`_startup.py`). The bot exposes its pre-existing 13 commands only.
2. P19 project behavior is feature-flagged OFF (`feature:projects:enabled = None`), so even if `/project` were registered, it would be inert.
3. The existing Discord flow (dashboard via REST to canonical embed `1519135545501028549`, 13 slash commands) is intact — confirmed by audit round-1 UX-02/UX-03.

**The masked-vs-enabled drift is a P20-closed-surface item, not a P19 deploy concern.** Touching the discord service masking state is out of scope for P19-012 (would modify a P20-closed service without operator approval). Flagged for operator awareness; no P19 action required.

## 3. Module Import Verification (VPS)

All 9 P19 modules import cleanly post-deploy:

| Module | Import |
|---|---|
| src.projects.registry | OK |
| src.projects.types | OK |
| src.projects.memory_store | OK |
| src.projects.secrets_vault | OK |
| src.projects.exceptions | OK |
| src.life_kernel.cognition | OK |
| src.life_kernel.redis_client | OK |
| src.discord.cmd_project | OK |
| src.discord.project_session | OK |

## 4. Service Status (Post-Deploy, No Restart)

| Metric | Value |
|---|---|
| guinevere-core | active |
| NRestarts | 0 |
| Result | success |
| ActiveEnterTimestamp | Thu 2026-06-25 08:26:43 WIB (UNCHANGED — no restart) |
| cycle_count | 201,280 (advancing — brain alive) |
| Brain think_complete | active (08:43:28, model=guinevere, 0 fallback) |
| errors_count | 0 |
| Traceback | 0 |
| Other services | All 7 active + 1 expected-inactive (gateway) — untouched |

## 5. Restart Decision Log

| Option | Chosen? | Reason |
|---|---|---|
| Restart guinevere-core | ❌ NO | Additive DDL + flag OFF + already-deployed wiring → no benefit, would reset soak clock |
| Restart guinevere-discord | ❌ NO | Bot is enabled+active (NOT masked — see §2a); cmd_project not registered in its command tree, so no P19 reason to restart. Touching it is out of P19 scope (P20-closed service). |
| Restart any other service | ❌ NO | None touched P19 |

## 6. Footer

| Field | Value |
|---|---|
| Deploy status | SUCCESS — all P19 files on VPS, all modules import |
| Restart | NONE (surgical, no-disruption) |
| P20 status | HEALTHY — no regression, soak clock preserved |
| Next step | Phase 7: Smoke tests |