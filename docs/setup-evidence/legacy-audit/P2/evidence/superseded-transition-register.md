# P2 Superseded / Transition Register

**Date:** 2026-06-25
**Auditor:** Read-only implementation audit
**Scope:** Every P2 surface superseded by a later phase, and whether the transition is cleanly documented.
**Key question:** "If someone reactivates the old surface, what breaks?"

---

## 1. SUPERSEDED SURFACES

### SUP-TR-001: Standalone guinevere-discord.service → Hermes Gateway / P20 REST Publisher

| Field | Value |
|-------|-------|
| **Old surface** | `src/discord/_entrypoint.py` → `python -m src.discord._entrypoint` → discord.py gateway bot |
| **Superseded by** | Hermes Gateway (`hermes-gateway.service`) + P20 core REST publisher (`src/life_kernel/discord_rest_client.py`) |
| **ADR/Decision** | ADR-035 (Hermes migration), P2-022 (service masked) |
| **Documented?** | PARTIAL — PROGRESS.md:158 documents P2-022. ADR-035 documents the migration. CHECKLIST.md does NOT document the transition. No single "Discord Writer Ownership" document exists. |
| **Reactivation risk** | **HIGH.** If `guinevere-discord.service` is unmasked: (1) The standalone bot connects to Discord gateway with the same token as Hermes Gateway → Discord disconnects one (token collision). (2) The deploy unit uses a non-existent SOPS file path → ExecStartPre fails → service won't start. (3) The systemd/ unit uses plaintext `.env.discord` → insecure token loading. |
| **Current state** | Service is masked. `vps-mirror/systemd-live/` has no discord unit. `hermes-gateway.service` is the active Discord gateway. |
| **Recommendation** | Document the fallback role of the standalone bot. Either: (a) keep it as a documented fallback with working deploy unit, or (b) delete the standalone bot code and remove the service units. The current ambiguity is the worst state. |

### SUP-TR-002: bot.py / conversational_handler.py → _entrypoint.py

| Field | Value |
|-------|-------|
| **Old surface** | `src/discord/bot.py` (512 lines, old audit) + `src/discord/conversational_handler.py` (496 lines) |
| **Superseded by** | `src/discord/_entrypoint.py` (current entrypoint) |
| **ADR/Decision** | P2-017 (systemd service creation) — the old bot.py was the original entrypoint, replaced by _entrypoint.py during P2 implementation |
| **Documented?** | YES — files are archived with `.bak.pre-phase2` suffix. `_entrypoint.py` docstring explains it's the active entrypoint. |
| **Reactivation risk** | LOW — `.bak` files are not importable by Python (non-.py extension). No code imports them. |
| **Current state** | Cleanly archived. No active references. |
| **Recommendation** | None — clean transition. |

### SUP-TR-003: P2 Slash Commands → Hermes Discord Plugins

| Field | Value |
|-------|-------|
| **Old surface** | 49 `cmd_*.py` files in `src/discord/` registered via `_command_registry.py` + `_entrypoint.py:setup_hook` |
| **Superseded by** | Hermes plugins under `hermes_plugins/` (47 plugins exist, organized in `commands_*/` subdirectories) |
| **ADR/Decision** | `docs/setup-evidence/hermes-migration/phase-2-discord.md` — migration plan with 35-plugin table |
| **Documented?** | PARTIAL. The migration doc exists but: (1) it references 35 plugins, but 47 exist; (2) it references `plugins/*_plugin.py` paths, but actual structure is `hermes_plugins/commands_*/`; (3) 0 of the documented 35 plugin file paths exist. The migration doc is an aspirational design doc, not a reflection of current state. |
| **Reactivation risk** | MEDIUM — if someone runs the standalone bot, 49 commands are registered. If Hermes Gateway also registers commands, there could be duplicate command names. The bot and Hermes plugins SHARE command names (e.g., both register `/status`). |
| **Current state** | Both codebases exist in parallel: `src/discord/` (49 commands, discord.py) and `hermes_plugins/` (47 commands, Hermes). The standalone bot is masked, so only Hermes commands are active. |
| **Recommendation** | Update phase-2-discord.md to reflect actual plugin structure. Document the command duplication risk. Decide whether to keep standalone bot commands as fallback or delete them. |

### SUP-TR-004: notifications.py Channel Routing → P20 Dashboard Writer

| Field | Value |
|-------|-------|
| **Old surface** | `src/discord/notifications.py` — SEV0-SEV4 routing matrix, embed builder, `send_alert()`, channel lookup |
| **Superseded by** | P20 `src/life_kernel/discord_rest_client.py` + `dashboard_writer.py` + `log_channel.py` — Option-B core REST publisher |
| **ADR/Decision** | P20 CLOSED (EARLY PRODUCTION ACCEPTANCE). P20 uses REST publisher for dashboard/log, not the old notifications system. |
| **Documented?** | PARTIAL. P20 evidence documents the REST publisher. `notifications.py` is never mentioned in P20 docs. The old notifications system is dead code but not documented as superseded. |
| **Reactivation risk** | LOW — `send_alert()` is never called, so reactivation requires code changes. But `notifications.py` is imported by `shadow_monitor.py` (for `NotificationEmbedField`), so the module IS loaded. The bare `import discord` at line 240 is a crash risk. |
| **Current state** | Dead code. `send_alert()` never called. P20 REST publisher is the active Discord writer. |
| **Recommendation** | Either: (a) delete `notifications.py` and update `shadow_monitor.py` to not import it, or (b) wire `send_alert()` into P20/complementary path and fix the crash bug. Current state (dead code with import side effects) is the worst state. |

### SUP-TR-005: gotify_fallback.py → P8 alertmanager.yml

| Field | Value |
|-------|-------|
| **Old surface** | `src/discord/gotify_fallback.py` — Gotify notification fallback for SEV0/SEV1 |
| **Superseded by** | P8 `alertmanager.yml` — centralized alerting with Discord+Gotify channels |
| **ADR/Decision** | ADR-022 (Gotify integration). P8-015 (SEV0-SEV4 routing matrix). |
| **Documented?** | PARTIAL. P8 alertmanager references Gotify. `gotify_fallback.py` is not mentioned as superseded. Gotify deployment is half-implemented (Docker compose only, no SOPS token, no systemd). |
| **Reactivation risk** | LOW — `send_fallback()` is only called from `send_alert()` which is dead code. But Gotify port 8081 is hardcoded. |
| **Current state** | Half-implemented, dead code. P8 alertmanager is the active alerting system. |
| **Recommendation** | Either deploy Gotify properly (SOPS token, systemd, health check) or delete the Gotify code and document P8 alertmanager as the sole alerting path. |

### SUP-TR-006: Shadow Pipeline → Hermes Shadow Mode

| Field | Value |
|-------|-------|
| **Old surface** | `src/discord/shadow_monitor.py` + `src/discord/shadow_pipeline.py` — discord.py shadow mode for bot.py vs Hermes parity testing |
| **Superseded by** | `docs/setup-evidence/hermes-migration/phase-2-discord.md` — Hermes shadow mode with 4 traffic stages, 48hr+ dual-bot operation |
| **ADR/Decision** | phase-2-discord.md Step 2.4-2.5 |
| **Documented?** | NO. The shadow pipeline is disabled by default (`enabled=False`, `traffic_pct=0`). No deployment documentation. The Hermes migration doc's shadow mode plan is aspirational (0 of its steps are implemented). |
| **Reactivation risk** | LOW — modules are disabled by default. But `shadow_monitor.py` imports `notifications.py` (bare `import discord` crash risk). |
| **Current state** | Disabled. No deployment mechanism. Hermes shadow mode is aspirational. |
| **Recommendation** | Either implement shadow mode or delete the shadow modules. Current state is dead code with import side effects. |

### SUP-TR-007: systemd/ and deploy/discord/ service units → vps-mirror/systemd-live/

| Field | Value |
|-------|-------|
| **Old surface** | `systemd/guinevere-discord.service` (plaintext env), `deploy/discord/guinevere-discord.service` (SOPS decrypt, broken path) |
| **Superseded by** | `vps-mirror/systemd-live/hermes-gateway.service` (active Discord gateway) |
| **ADR/Decision** | ADR-035, P2-022 |
| **Documented?** | NO. No document explains which service unit is canonical or why conflicting copies exist. |
| **Reactivation risk** | **HIGH.** If someone copies `systemd/guinevere-discord.service` to `/etc/systemd/system/`: token loaded from plaintext `.env.discord` (insecure). If someone copies `deploy/discord/guinevere-discord.service`: `ExecStartPre` fails because `secrets/.env.discord.sops` doesn't exist. Neither unit works correctly. |
| **Current state** | Two broken service units, one masked service. No working standalone bot deployment path. |
| **Recommendation** | Delete or fix the broken service units. If standalone bot is a fallback, ensure the deploy unit works. If not, remove both units to prevent accidental deployment. |

---

## 2. DUPLICATE WRITER RISK ASSESSMENT

| Writer | Token | Type | Active? | Collision Risk |
|--------|-------|------|---------|---------------|
| Standalone bot (`_entrypoint.py`) | `DISCORD_BOT_TOKEN` | Gateway (WebSocket) | **Masked** | HIGH if unmasked — token collision with Hermes |
| Hermes Gateway (`hermes gateway run`) | `DISCORD_BOT_TOKEN` | Gateway (WebSocket) | **Active** | Active writer |
| P20 REST publisher (`discord_rest_client.py`) | `DISCORD_BOT_TOKEN` | REST (HTTP) | **Active** | No collision — REST-only, no gateway |
| Core API alertmanager (`routes.py`) | `DISCORD_BOT_TOKEN` | REST (HTTP) | **Active** | No collision — REST-only |
| Finance hooks | `DISCORD_BOT_TOKEN` | REST (HTTP) | **Active** | No collision — REST-only |

**Key finding:** Only ONE gateway consumer (Hermes) is active. The standalone bot is masked. REST consumers are safe from token collision. **Duplicate writer risk is currently mitigated by the mask.**

---

## 3. DOCUMENTATION QUALITY ASSESSMENT

| Transition | doc-ADR | doc-CHECKLIST | doc-PROGRESS | doc-evidence | doc-migration | Overall |
|------------|---------|---------------|-------------|-------------|---------------|---------|
| Standalone bot → Hermes/P20 | ✅ ADR-035 | ❌ Missing | ⚠️ P2-022 only | ❌ Scattered | ✅ phase-2-discord.md | PARTIAL |
| bot.py → _entrypoint.py | N/A | N/A | N/A | ✅ .bak files | N/A | GOOD |
| Slash commands → Hermes plugins | ⚠️ ADR-035 | ❌ Not mentioned | ❌ Not mentioned | ❌ Not mentioned | ⚠️ Aspirational | POOR |
| notifications → P20 REST | N/A | ❌ Old claims | ❌ Old claims | ✅ P20 evidence | N/A | POOR |
| Gotify → P8 alertmanager | ✅ ADR-022 | ❌ Not mentioned | ⚠️ P8-015 | ❌ Half-implemented | N/A | POOR |
| Shadow → Hermes shadow | N/A | N/A | N/A | N/A | ⚠️ Aspirational | POOR |
| Service units → vps-mirror | N/A | ❌ Not mentioned | ❌ Not mentioned | ❌ Not mentioned | N/A | POOR |

---

## 4. CONCLUSION

**The transition from standalone P2 Discord bot to Hermes Gateway + P20 REST publisher is the most significant architectural change in the project's Discord surface. It is documented at the ADR level but NOT at the implementation/docs level.** The standalone bot is intentionally masked, but:
- CHECKLIST.md still claims it's active
- The deploy unit is broken (references non-existent file)
- The systemd unit is insecure (plaintext token)
- No fallback reactivation procedure is documented
- The command duplication risk (49 P2 vs 47 Hermes commands) is not documented

**Recommendation:** The project needs a single canonical "Discord Writer Ownership" document that answers: (1) Who writes to Discord now? (2) What is the standalone bot's role? (3) How to reactivate it in an emergency? (4) What is the migration path to P24 fork convergence? Until this document exists, the transition is PARTIALLY SUPERSEDED with documentation gaps.

---

*End of superseded/transition register.*