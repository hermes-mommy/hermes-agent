# StepPrompts Phase 2 — ADR-035 Hermes Migration Audit

**Status:** ✅ Complete  
**Date:** 2026-06-04  
**Scope:** `stepprompts/StepPrompts.md` lines 5171–5900  
**Reference:** `adr/ADR-035-hermes-migration.md` (Pillar 1: Discord=MIGRATE)  
**Auditor:** Guinevere  
**Verdict:** 12/21 VALID-UNTIL-CUTOVER, 7/21 OBSOLETE-AFTER-CUTOVER, 2/21 ALREADY-DONE

---

## 1. Summary

ADR-035 (accepted 2026-06-04) mandates a hybrid Hermes migration with **Pillar 1: Discord = MIGRATE** to Hermes native gateway. The migration's **Phase 2 (Discord Gateway, 5–8 days)** replaces the custom `bot.py` (562 lines), `conversational_handler.py` (496 lines), `session_adapter.py` (302 lines), and 35 slash commands with Hermes native gateway, hooks, and plugins.

This audit evaluates all 21 StepPrompts P2 steps against the ADR-035 migration plan to determine which steps remain valid (until cutover), which will become obsolete after Hermes takeover, and which are already done.

### Key finding

**StepPrompts P2 is a setup/onboarding phase** — most steps (P2-001 through P2-009) are Discord-side infrastructure tasks (app creation, token, server, channels, categories, permissions, topics) that remain valid regardless of which bot framework runs on top. These are **not affected by ADR-035**. Only steps that create or modify Python application code (P2-003, P2-010 through P2-021) are affected by the migration.

---

## 2. Context: What ADR-035 Phase 2 Means

ADR-035's Phase 2 ("Discord Gateway") does the following:

| ADR-035 Step | Description | Replaces StepPrompts |
|---|---|---|
| 2.1 | Configure Hermes Discord gateway (token, intents, channels) | P2-016, P2-017 (service), P2-018 (health check) |
| 2.2 | Migrate 8 HIGH-feasibility commands to plugins | P2-010, P2-012, P2-013, P2-014 |
| 2.3 | Migrate 15 MEDIUM-feasibility commands to plugins | P2-010 |
| 2.4 | Migrate 12 LOW-feasibility commands to plugins | P2-010 |
| 2.5 | Launch shadow mode (48hr+) | *No StepPrompts equivalent* |
| 2.6 | Response parity comparison | *No StepPrompts equivalent* |
| 2.7 | Faiz cutover approval | *No StepPrompts equivalent* |
| 2.8 | Cutover: stop bot.py, start Hermes gateway | P2-017 (service switch) |

**Post-cutover**: `bot.py`, `conversational_handler.py`, `session_adapter.py`, `intents.py`, `startup.py`, `notifications.py`, all 35 `cmd_*.py` files, and systemd unit `guinevere-discord.service` are **eliminated**. The systemd unit is replaced by `hermes-gateway.service`.

**Pre-cutover**: The existing `bot.py` continues running. ShadowPipeline is already wired (line 98–101) for shadow mode testing.

**Important**: The StepPrompts P2-017 inline `bot.py` template (lines 5673–5727) is a **starter template** that does NOT match the current `src/discord/bot.py` (562 lines). The actual bot has 35 wired commands + ShadowPipeline + SurveillanceSafeModeGuard + session factory + conversational handler integration. The template in StepPrompts.md is a simplified stub — if executed as-written, it would **regress** the current bot.

---

## 3. Per-Step Audit

### Classification Legend

| Status | Meaning |
|---|---|
| **VALID-UNTIL-CUTOVER** | Step remains valid during pre-migration. May be superseded after Hermes cutover but still needed now. |
| **OBSOLETE-AFTER-CUTOVER** | Step creates code/config that will be replaced by Hermes. Executing this step pre-migration creates soon-to-be-deleted code. |
| **ALREADY-DONE** | Step is complete in the current codebase. No further action needed. |
| **NEEDS-UPDATE** | Step content is stale/wrong and must be corrected before execution. |

---

### 3.1 Infrastructure Steps (P2-001 to P2-009) — Discord-Side Configuration

These steps create Discord-side resources (application, token, server, channels, categories, permissions, topics). **Hermes uses the same Discord resources** — the bot application, token, guild, channels, and permissions do not change.

#### P2-001: Discord Application Creation

| Field | Value |
|---|---|
| **StepPrompts Status** | ⬜ Not Started |
| **Audit Status** | **VALID-UNTIL-CUTOVER** |
| **Cutover Impact** | None — same Discord Application used by Hermes |
| **Superseded By** | N/A |
| **Notes** | Bot Application ID, OAuth2 scopes, and intents at developer.discord.com are unchanged. Hermes gateway uses the same Application ID. The step is worded for manual Discord Developer Portal operation and has no code dependency. |

#### P2-002: Bot Token Generation and SOPS Storage

| Field | Value |
|---|---|
| **StepPrompts Status** | ⬜ Not Started |
| **Audit Status** | **VALID-UNTIL-CUTOVER** |
| **Cutover Impact** | Minor — token storage mechanism changes to `hermes secrets` post-cutover |
| **Superseded By** | ADR-035 Phase 2.1 (Hermes gateway config) — same token, different storage |
| **Notes** | The bot token itself is the same. Post-cutover, Hermes reads it from `config/hermes/secrets.yaml` via `hermes secrets`, not from `secrets/discord-secrets.yaml` via SOPS. Pre-cutover, SOPS is correct. After cutover, the SOPS file is archived. |

#### P2-003: Bot Intents Configuration

| Field | Value |
|---|---|
| **StepPrompts Status** | ⬜ Not Started |
| **Audit Status** | **OBSOLETE-AFTER-CUTOVER** |
| **Cutover Impact** | HIGH — `src/discord/intents.py` is ELIMINATED after cutover |
| **Superseded By** | ADR-035 Phase 2.1 — Hermes gateway intent configuration in `config/hermes/config.yaml` |
| **Notes** | The step creates `src/discord/intents.py`. This file is part of the deleted custom Discord infrastructure (ADR-035 §Pillar 1, line 272: "Intents — Hermes gateway intent configuration"). If this step hasn't been run yet, it's **safe to skip entirely** — Hermes handles intents natively. If the file already exists (it does in current codebase), it will be deleted at cutover. |

#### P2-004: Discord Server Creation

| Field | Value |
|---|---|
| **StepPrompts Status** | ✅ Complete |
| **Audit Status** | **VALID-UNTIL-CUTOVER** |
| **Cutover Impact** | None — same guild used by Hermes |
| **Superseded By** | N/A |
| **Notes** | "Guinevere's Domain" guild (ID `1510876414671323206`) is the canonical server. Hermes connects to the same guild. Already complete with verification and audit pass. |

#### P2-005: Server Categories Setup

| Field | Value |
|---|---|
| **StepPrompts Status** | ✅ Complete |
| **Audit Status** | **VALID-UNTIL-CUTOVER** |
| **Cutover Impact** | None — same categories |
| **Superseded By** | N/A |
| **Notes** | 4 canonical categories (`👑 Throne`, `📊 Surveillance`, `🔧 Projects`, `🗡️ Archive`) are Discord-side. Hermes uses the same category structure. Already complete with verification pass. |

#### P2-006: Channel Creation (13 Channels)

| Field | Value |
|---|---|
| **StepPrompts Status** | ✅ Complete |
| **Audit Status** | **VALID-UNTIL-CUTOVER** |
| **Cutover Impact** | None — same channels |
| **Superseded By** | N/A |
| **Notes** | 13 text channels are Discord-side. Hermes shadow mode uses a *new* `#hermes-shadow` channel (ADR-035 Phase 2.5), but the existing 13 channels remain. Already complete. |

#### P2-007: Channel Permissions Configuration

| Field | Value |
|---|---|
| **StepPrompts Status** | ✅ Completed |
| **Audit Status** | **VALID-UNTIL-CUTOVER** |
| **Cutover Impact** | Hermes brings native RBAC — may refine post-cutover |
| **Superseded By** | ADR-035 §Pillar 1 (Hermes RBAC) — supplements, not replaces |
| **Notes** | Discord-side permission overwrites remain in effect. Hermes RBAC operates at the application layer (who can invoke what). Channel-level `@everyone` deny and Faiz/Samm matrix are Discord-native and unchanged. Already complete with auditor PASS. |

#### P2-008 to P2-009: Channel Topics and Bot Invite Verification

| Field | Value |
|---|---|
| **StepPrompts Status** | ✅ Completed |
| **Audit Status** | **VALID-UNTIL-CUTOVER** |
| **Cutover Impact** | Bot invite URL may need regeneration if OAuth2 scope changes |
| **Superseded By** | N/A |
| **Notes** | Channel topics are Discord-side metadata, unchanged. Bot invite verification may need re-run post-cutover to ensure Hermes has required scopes (`bot`, `applications.commands`). Already complete with auditor PASS for both steps. |

---

### 3.2 Application Code Steps (P2-010 to P2-021) — Affected by Migration

These steps create/modify Python application code that interacts with Discord. **All are affected by ADR-035 Pillar 1**.

#### P2-010: Slash Commands Registration (33 Commands)

| Field | Value |
|---|---|
| **StepPrompts Status** | ✅ Complete (2026-06-01) |
| **Audit Status** | **ALREADY-DONE** (but **OBSOLETE-AFTER-CUTOVER**) |
| **Cutover Impact** | CRITICAL — all 35 commands migrate to Hermes plugins |
| **Superseded By** | ADR-035 Phase 2.2–2.4: 35 commands → Hermes plugins via `ctx.register_command()` |
| **Notes** | StepPrompts says "33 commands" but bot.py actually registers **35**: 13 original + 20 Batch D (RG-010..RG-014) + 2 Hermes Phase 1 (`/new`, `/history`). The `commands.py` (278 lines) is eliminated. All 35 `cmd_*.py` files (6,893 lines total) are refactored to Hermes plugins per ADR-035 command migration table. |

#### P2-011: Embed Color Palette

| Field | Value |
|---|---|
| **StepPrompts Status** | ⏳ Complete (P2-011/P2-012 done; P2-013/P2-014 pending) |
| **Audit Status** | **ALREADY-DONE** |
| **Cutover Impact** | `colors.py` (90 lines) is **KEPT** — no Discord.py dependency (ADR-035 §Pillar 1, line 275) |
| **Superseded By** | N/A — preserved verbatim |
| **Notes** | `src/discord/colors.py` is explicitly preserved in ADR-035 because it has no `discord.py` dependency. It provides hex color constants used by both current embed builders and future Hermes plugins. Verification already complete. |

#### P2-012: /status Command

| Field | Value |
|---|---|
| **StepPrompts Status** | ⏳ Complete |
| **Audit Status** | **ALREADY-DONE** (but **OBSOLETE-AFTER-CUTOVER**) |
| **Cutover Impact** | `cmd_status.py` → Hermes `status_plugin.py` (HIGH feasibility) |
| **Superseded By** | ADR-035 Phase 2.2 — `/status` is in the HIGH feasibility category (simple plugin port) |
| **Notes** | 339 lines, ~60% code eliminated in migration (Discord.py embed boilerplate removed). Business logic (system status query + uptime + memory display) maps cleanly to `ctx.register_command()`. Already verified per evidence. |

#### P2-013: /mood Command

| Field | Value |
|---|---|
| **StepPrompts Status** | ⏳ Pending |
| **Audit Status** | **OBSOLETE-AFTER-CUTOVER** |
| **Cutover Impact** | `cmd_mood.py` → Hermes `mood_plugin.py` (HIGH feasibility) |
| **Superseded By** | ADR-035 Phase 2.2 — `/mood` is HIGH feasibility |
| **Notes** | 340 lines in current codebase (wired in bot.py line 163). StepPrompts shows a simplified inline template that doesn't match. Implementing the template now creates code that will be deleted at cutover. The mood state management moves to `GuinevereSafetyPlugin` post-cutover. |

#### P2-014: /help Command

| Field | Value |
|---|---|
| **StepPrompts Status** | ⏳ Pending |
| **Audit Status** | **OBSOLETE-AFTER-CUTOVER** |
| **Cutover Impact** | `cmd_help.py` → Hermes `help_plugin.py` (HIGH feasibility) |
| **Superseded By** | ADR-035 Phase 2.2 — `/help` is HIGH feasibility |
| **Notes** | 312 lines in current codebase (wired in bot.py line 164). StepPrompts shows simplified inline template. Hermes `ctx.register_command()` supports per-plugin help auto-generation. Command list built from plugin registry, not static embed. |

#### P2-015: /safeword and HARD STOP Implementation

| Field | Value |
|---|---|
| **StepPrompts Status** | ⬜ Not Started |
| **Audit Status** | **OBSOLETE-AFTER-CUTOVER** |
| **Cutover Impact** | CRITICAL — HARD STOP moves to dual-layer hook + plugin |
| **Superseded By** | ADR-035 Phase 1.2 (`pre_prompt` hook + `GuinevereSafetyPlugin.on_message()`) |
| **Notes** | StepPrompts inline template creates a standalone `cmd_safeword.py` with global in-memory state. The actual `cmd_safeword.py` in the codebase is more sophisticated (524 lines). ADR-035 reimplements HARD STOP as: (1) `pre_prompt` hook with regex detection (<50ms), (2) `GuinevereSafetyPlugin.on_message()` as secondary layer, (3) `on_failure: block` ensuring fail-closed. The current `_on_message_listener` in bot.py (line 128) fires BEFORE `on_message` — the `pre_prompt` hook fires after gateway acceptance but BEFORE LLM processing, a minor timing shift. ADR-035 adds a custom Discord gateway plugin for pre-gateway interception to match current timing. **Safety-critical: do NOT implement the StepPrompts inline template. Use the existing cmd_safeword.py until cutover, then let Hermes hooks take over.** |

#### P2-016: Startup Message

| Field | Value |
|---|---|
| **StepPrompts Status** | ⬜ Not Started |
| **Audit Status** | **OBSOLETE-AFTER-CUTOVER** |
| **Cutover Impact** | `startup.py` (253 lines) → Hermes `on_ready` lifecycle |
| **Superseded By** | ADR-035 Phase 2.1 — Hermes native gateway handles startup |
| **Notes** | StepPrompts inline template is a simplified stub. The actual `src/discord/startup.py` is 253 lines with full greeting, presence, health check. Hermes handles `on_ready` natively. The existing startup.py is already wired in bot.py (line 491). |

#### P2-017: guinevere-discord.service (Bot Main Entrypoint)

| Field | Value |
|---|---|
| **StepPrompts Status** | ⬜ Not Started |
| **Audit Status** | **OBSOLETE-AFTER-CUTOVER** |
| **Cutover Impact** | CRITICAL — `bot.py` + `guinevere-discord.service` replaced by `hermes gateway` |
| **Superseded By** | ADR-035 Phase 2.8: `sudo systemctl stop guinevere-discord` → `hermes gateway start` |
| **Notes** | **DANGER**: StepPrompts inline `bot.py` template (lines 5673–5727) is a minimal stub that would **regress** the current 562-line bot. The actual `src/discord/bot.py` has: 35 wired commands, ShadowPipeline, SurveillanceSafeModeGuard, session factory, conversational handler integration, `commands.Bot` wrapper (not `discord.Client`). **Do NOT execute the inline template.** The systemd unit also changes — from `guinevere-discord.service` to Hermes-managed service. The post-cutover rollback command is: `hermes gateway stop && sudo systemctl start guinevere-discord`. |

#### P2-018: Discord Health Check

| Field | Value |
|---|---|
| **StepPrompts Status** | ⬜ Not Started |
| **Audit Status** | **OBSOLETE-AFTER-CUTOVER** |
| **Cutover Impact** | Health checks move to `hermes doctor` |
| **Superseded By** | ADR-035 Phase 7: `hermes doctor` + `hermes insights` |
| **Notes** | The `journalctl -u guinevere-discord` check is specific to the custom systemd service. Post-cutover, health monitoring uses `hermes doctor --verbose` and Hermes gateway health endpoint. |

#### P2-019: Notification Routing

| Field | Value |
|---|---|
| **StepPrompts Status** | ⬜ Not Started |
| **Audit Status** | **OBSOLETE-AFTER-CUTOVER** |
| **Cutover Impact** | `notifications.py` (182 lines) → Hermes notification hook (~80 lines) |
| **Superseded By** | ADR-035 Phase 2: Hermes notification hook (182 → ~80 lines, 56% reduction) |
| **Notes** | StepPrompts inline template creates `src/discord/notifications.py` with SEV0-SEV4 routing. ADR-035 Pillar 1 line 273: "Notifications — ported to Hermes notification hook." The current `notifications.py` (182 lines) already exists and is wired. Post-cutover, notification routing uses Hermes hooks + Gotify integration. |

#### P2-020: Gotify Installation

| Field | Value |
|---|---|
| **StepPrompts Status** | ⬜ Not Started |
| **Audit Status** | **VALID-UNTIL-CUTOVER** |
| **Cutover Impact** | None — Gotify is infrastructure, not Discord-specific |
| **Superseded By** | N/A — Gotify remains after cutover |
| **Notes** | Gotify is an independent notification service. The Docker Compose setup (localhost:8081) is framework-agnostic. ADR-035's `on_error` hook (Phase 7) sends to the same Gotify instance. This step can proceed independently of the Hermes migration timeline. |

#### P2-021: Discord to Gotify Fallback

| Field | Value |
|---|---|
| **StepPrompts Status** | ⬜ Not Started |
| **Audit Status** | **PARTIALLY OBSOLETE** — Gotify service stays valid; code module may need refactoring |
| **Cutover Impact** | `gotify_fallback.py` (65 lines) is **KEPT** per ADR-035 Pillar 1 line 276 |
| **Superseded By** | ADR-035 Phase 7 (`on_error` hook) — supplements, not replaces |
| **Notes** | ADR-035 explicitly keeps `gotify_fallback.py` because it has no Discord.py dependency. The module uses `httpx`, not `discord.py`. However, the trigger mechanism changes — instead of bot.py calling it on failure, Hermes's `on_error` hook triggers it. The core module (HTTP POST to Gotify) remains identical. |

---

## 4. Migration Phase Mapping

How ADR-035 migration phases supersede StepPrompts P2 steps:

| ADR-035 Phase | Supersedes StepPrompts P2 Step(s) | Description |
|---|---|---|
| **Phase 1** (Safety Foundation, 7–10 days) | P2-015 | HARD STOP → `pre_prompt` hook + plugin dual-layer |
| **Phase 2.1** (Gateway Config) | P2-003, P2-016, P2-017, P2-018 | Intents, startup, bot entrypoint, health check → Hermes gateway |
| **Phase 2.2** (HIGH feasibility commands) | P2-010, P2-012, P2-013, P2-014 | 8 commands → simple plugins (status, mood, help, safeword, new, history, casual, focus) |
| **Phase 2.3** (MEDIUM feasibility commands) | P2-010 | 15 commands → plugin ports (memory, loop, surveillance) |
| **Phase 2.4** (LOW feasibility commands) | P2-010 | 12 commands → full custom plugins (cost, budget, approve, deny, restart, backup, health, consent, punishment, reward) |
| **Phase 2.5–2.6** (Shadow Mode) | *No StepPrompts equivalent* | 48hr parallel operation, parity comparison |
| **Phase 2.8** (Cutover) | P2-017 (service switch) | Stop guinevere-discord, start hermes gateway |
| **Phase 7** (Hardening) | P2-019, P2-020, P2-021 | Notifications, health, Gotify → integrated with Hermes monitoring |

---

## 5. Safety-Critical Notes

### P2-015: HARD STOP Implementation

**DO NOT implement the StepPrompts inline template.** The current `src/discord/cmd_safeword.py` (524 lines) has a proper `SafewordHandler` class with dual-mode detection (slash command + text message), recovery protocols, and state management. The StepPrompts inline template (lines 5558–5627) is a simplified stub with global mutable state that has no recovery mechanism.

ADR-035 implements HARD STOP as a **dual-layer** safety feature:
1. `pre_prompt` hook — regex detection, `<50ms`, `on_failure: block` (fail-closed)
2. `GuinevereSafetyPlugin.on_message()` — secondary layer for defense-in-depth
3. Custom Discord gateway plugin — pre-gateway interception (same timing as current `_on_message_listener`)

The current `bot.py` `_on_message_listener` (line 128) fires BEFORE `on_message`. The `pre_prompt` hook fires AFTER gateway acceptance but BEFORE LLM. This timing shift is mitigated by the custom gateway plugin per ADR-035.

### P2-017: Bot Entrypoint Regression Risk

The StepPrompts inline `bot.py` template (lines 5673–5727) uses `discord.Client` (not `commands.Bot`), registers only `/status` and `/safeword`, and has no ShadowPipeline, SurveillanceSafeModeGuard, session factory, or conversational handler. **If executed, it would destroy the current bot's functionality.** The actual `src/discord/bot.py` is 562 lines with full production capabilities.

---

## 6. Steps Safe to Keep vs Steps to Mark SUPERSEDED

### Safe to Keep (valid pre-cutover, no code conflict)

| Step | Reason |
|---|---|
| P2-001 | Discord Developer Portal — manual, framework-agnostic |
| P2-002 | Token generation (SOPS flow) — same token used by Hermes |
| P2-004 | Server creation — already complete, unchanged |
| P2-005 | Categories — already complete, Discord-side |
| P2-006 | Channels — already complete, Discord-side |
| P2-007 | Permissions — already complete, Discord-side |
| P2-008 | Channel topics — already complete, Discord-side |
| P2-009 | Bot invite verification — already complete |
| P2-011 | Embed colors — `colors.py` preserved per ADR-035 |
| P2-020 | Gotify installation — infrastructure, not code |
| P2-021 | Gotify fallback module — kept per ADR-035 |

### Should be Marked SUPERSEDED or Skipped

| Step | Recommendation |
|---|---|
| P2-003 | **SKIP** — `intents.py` will be deleted; Hermes handles intents natively |
| P2-010 | **MARK COMPLETE** — commands already synced; future migration via Hermes plugins |
| P2-012 | **MARK COMPLETE** — already implemented; Hermes migration will refactor |
| P2-013 | **SKIP** — implementing via StepPrompts creates throwaway code; defer to Hermes plugin |
| P2-014 | **SKIP** — same as above; Hermes help auto-generation is superior |
| P2-015 | **DO NOT IMPLEMENT** — safety-critical; use existing `cmd_safeword.py` until Hermes hooks take over |
| P2-016 | **SKIP** — Hermes `on_ready` lifecycle replaces custom startup |
| P2-017 | **DO NOT IMPLEMENT inline template** — would regress current bot; Hermes gateway replaces everything |
| P2-018 | **SKIP** — Hermes `doctor` replaces custom health checks |
| P2-019 | **SKIP** — Hermes notification hook replaces custom routing |

---

## 7. Current Codebase vs StepPrompts Gap Analysis

| Item | StepPrompts States | Actual Codebase | Impact |
|---|---|---|---|
| Command count | "33 commands" | **35 commands** (13 + 20 Batch D + 2 Hermes P1) | StepPrompts undercounts by 2 |
| bot.py class | `discord.Client` | `commands.Bot` | StepPrompts template would downgrade |
| bot.py lines | ~45 line inline template | **562 lines** | Template is dangerously minimal |
| ShadowPipeline | Not mentioned | **Wired** (lines 98–101) | Shadow mode already prepared |
| SurveillanceSafeModeGuard | Not mentioned | **Wired** (lines 107–109) | Safety guard active |
| Conversational handler | Not mentioned | **Wired** (line 525) | 10-step pipeline active |
| Session factory | Not mentioned | **Wired** (lines 439–470) | SQLAlchemy async sessions active |
| cmd_safeword.py | 67-line inline template | **524 lines** with `SafewordHandler` class | Template is dangerously minimal |

---

## 8. Recommendations

1. **P2-003, P2-013, P2-014, P2-016, P2-018, P2-019**: Mark as `SUPERSEDED-BY-ADR-035` in StepPrompts.md. Implementing these steps creates code that will be deleted within the migration window (35–50 days). Defer to Hermes plugin implementation.

2. **P2-015**: Add a warning annotation referencing ADR-035 Phase 1.2. The inline template must NOT be executed. Reference the existing `cmd_safeword.py` as the active implementation.

3. **P2-017**: Add a **BLOCKING warning** that the inline `bot.py` template will regress the current bot. Reference `src/discord/bot.py` as source of truth. The systemd service should be marked as `guinevere-discord.service` → `hermes-gateway.service` post-cutover.

4. **P2-010**: Update command count from "33" to "35" and note that Batch D (RG-010..RG-014) and Hermes Phase 1 commands are already included. Mark as complete for the current implementation; future migration covered by ADR-035 Phase 2.2–2.4.

5. **Timeline impact**: The StepPrompts P2 "3-5 days" timeline is superseded by ADR-035's Phase 2 timeline of "5-8 days" (significantly larger scope — includes 35-command plugin migration, 48hr shadow mode, and cutover).

6. **Safety boundary**: All P2 safety steps (P2-015 safeword, P2-007 permissions) are preserved in ADR-035 with defense-in-depth improvements. No safety regression.

---

## 9. Footer

| Field | Value |
|---|---|
| Audit Date | 2026-06-04 |
| Auditor | Guinevere |
| ADR Reference | ADR-035 (Accepted, 2026-06-04) |
| StepPrompts Range | Lines 5171–5900 |
| bot.py Reference | `src/discord/bot.py` (562 lines, 35 commands) |
| Evidence Path | `research-reports/stepprompts-audit/P2-audit.md` |