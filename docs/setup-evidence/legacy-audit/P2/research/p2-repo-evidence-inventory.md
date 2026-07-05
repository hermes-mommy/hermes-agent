# P2 Repository Evidence Inventory

**Auditor:** Guinevere (autonomous, read-only)
**Date:** 2026-06-25
**Method:** Static file enumeration via Glob/Grep/Bash; no runtime execution, no decryption, no state mutation.

---

## (a) docs/setup-evidence/P2/ -- All P2 Evidence Files

### STEP-P2-001..022 Verification Files

| Path | Status | Description |
|------|--------|-------------|
| `docs/setup-evidence/P2/STEP-P2-001/verification.md` | EXISTS | P2-001: Discord app verification (Bot ID 1510873134981582858) |
| `docs/setup-evidence/P2/STEP-P2-002/verification.md` | EXISTS | P2-002: Bot token SOPS encryption verification |
| `docs/setup-evidence/P2/STEP-P2-003/verification.md` | EXISTS | P2-003: Bot intents verification (MESSAGE_CONTENT, GUILD_MEMBERS, PRESENCE) |
| `docs/setup-evidence/P2/STEP-P2-004/verification.md` | EXISTS | P2-004: Discord server verification (Guinevere's Domain, guild ID 1510876414671323206) |
| `docs/setup-evidence/P2/STEP-P2-005/verification.md` | EXISTS | P2-005: 4 categories verification (Throne, Surveillance, Projects, Archive) |
| `docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml` | EXISTS | P2-006: Channel IDs (14 channels listed, incl. rituals + 3 ghost channels) |
| `docs/setup-evidence/P2/STEP-P2-006/verification.md` | EXISTS | P2-006: Channel creation verification |
| `docs/setup-evidence/P2/STEP-P2-007/verification.md` | EXISTS | P2-007: Permissions verification (@everyone denied, Faiz/Samm matrix) |
| `docs/setup-evidence/P2/STEP-P2-008/verification.md` | EXISTS | P2-008: Channel topics verification (13/13 persona-flavored) |
| `docs/setup-evidence/P2/STEP-P2-009/verification.md` | EXISTS | P2-009: Bot invite/permission scope verification (Administrator noted as unjustified) |
| `docs/setup-evidence/P2/STEP-P2-010/verification.md` | EXISTS | P2-010: Slash command registration verification |
| `docs/setup-evidence/P2/STEP-P2-010/p2-010-implementation-summary.md` | EXISTS | P2-010: Implementation summary for command registration |
| `docs/setup-evidence/P2/STEP-P2-011/verification.md` | EXISTS | P2-011: Embed color palette verification |
| `docs/setup-evidence/P2/STEP-P2-011/p2-011-implementation-summary.md` | EXISTS | P2-011: Implementation summary for embed colors |
| `docs/setup-evidence/P2/STEP-P2-012/verification.md` | EXISTS | P2-012: `/status` command verification |
| `docs/setup-evidence/P2/STEP-P2-012/p2-012-implementation-summary.md` | EXISTS | P2-012: Implementation summary for status command |
| `docs/setup-evidence/P2/STEP-P2-013/verification.md` | EXISTS | P2-013: `/mood` command verification |
| `docs/setup-evidence/P2/STEP-P2-013/p2-013-implementation-summary.md` | EXISTS | P2-013: Implementation summary for mood command |
| `docs/setup-evidence/P2/STEP-P2-013/verifiers/lsp-static-verifier.md` | EXISTS | P2-013: LSP static analysis verifier |
| `docs/setup-evidence/P2/STEP-P2-013/verifiers/token-unsafe-scan-verifier.md` | EXISTS | P2-013: Token unsafe scan verifier |
| `docs/setup-evidence/P2/STEP-P2-013/verifiers/vps-aizanta-health-verifier.md` | EXISTS | P2-013: VPS Aizanta health verifier |
| `docs/setup-evidence/P2/STEP-P2-014/verification.md` | EXISTS | P2-014: `/help` command verification |
| `docs/setup-evidence/P2/STEP-P2-014/p2-014-implementation-summary.md` | EXISTS | P2-014: Implementation summary for help command |
| `docs/setup-evidence/P2/STEP-P2-014/verifiers/lsp-static-verifier.md` | EXISTS | P2-014: LSP static analysis verifier |
| `docs/setup-evidence/P2/STEP-P2-014/verifiers/token-unsafe-scan-verifier.md` | EXISTS | P2-014: Token unsafe scan verifier |
| `docs/setup-evidence/P2/STEP-P2-014/verifiers/vps-aizanta-health-verifier.md` | EXISTS | P2-014: VPS Aizanta health verifier |
| `docs/setup-evidence/P2/STEP-P2-015/verification.md` | EXISTS | P2-015: `/safeword` + HARD STOP detection verification |
| `docs/setup-evidence/P2/STEP-P2-015/p2-015-implementation-summary.md` | EXISTS | P2-015: Implementation summary for safeword |
| `docs/setup-evidence/P2/STEP-P2-015/verifiers/lsp-static-verifier.md` | EXISTS | P2-015: LSP static analysis verifier |
| `docs/setup-evidence/P2/STEP-P2-015/verifiers/safety-verifier.md` | EXISTS | P2-015: Safety verifier |
| `docs/setup-evidence/P2/STEP-P2-015/verifiers/token-unsafe-scan-verifier.md` | EXISTS | P2-015: Token unsafe scan verifier |
| `docs/setup-evidence/P2/STEP-P2-015/verifiers/vps-aizanta-health-verifier.md` | EXISTS | P2-015: VPS Aizanta health verifier |
| `docs/setup-evidence/P2/STEP-P2-016/verification.md` | EXISTS | P2-016: Startup message verification ("Mommy sudah bangun, Darling.") |
| `docs/setup-evidence/P2/STEP-P2-016/p2-016-implementation-summary.md` | EXISTS | P2-016: Implementation summary for startup message |
| `docs/setup-evidence/P2/STEP-P2-016/verifiers/lsp-static-verifier.md` | EXISTS | P2-016: LSP static analysis verifier |
| `docs/setup-evidence/P2/STEP-P2-016/verifiers/token-unsafe-scan-verifier.md` | EXISTS | P2-016: Token unsafe scan verifier |
| `docs/setup-evidence/P2/STEP-P2-016/verifiers/vps-aizanta-health-verifier.md` | EXISTS | P2-016: VPS Aizanta health verifier |
| `docs/setup-evidence/P2/STEP-P2-017/verification.md` | EXISTS | P2-017: `guinevere-discord.service` creation verification |
| `docs/setup-evidence/P2/STEP-P2-017/p2-017-implementation-summary.md` | EXISTS | P2-017: Implementation summary for service unit |
| `docs/setup-evidence/P2/STEP-P2-017/verifiers/lsp-static-verifier.md` | EXISTS | P2-017: LSP static analysis verifier |
| `docs/setup-evidence/P2/STEP-P2-017/verifiers/safety-verifier.md` | EXISTS | P2-017: Safety verifier |
| `docs/setup-evidence/P2/STEP-P2-017/verifiers/token-unsafe-scan-verifier.md` | EXISTS | P2-017: Token unsafe scan verifier |
| `docs/setup-evidence/P2/STEP-P2-017/verifiers/vps-aizanta-health-verifier.md` | EXISTS | P2-017: VPS Aizanta health verifier |
| `docs/setup-evidence/P2/STEP-P2-018/verification.md` | EXISTS | P2-018: Discord health check (gateway status) |
| `docs/setup-evidence/P2/STEP-P2-018/verifiers/lsp-static-verifier.md` | EXISTS | P2-018: LSP static analysis verifier |
| `docs/setup-evidence/P2/STEP-P2-018/verifiers/token-unsafe-scan-verifier.md` | EXISTS | P2-018: Token unsafe scan verifier |
| `docs/setup-evidence/P2/STEP-P2-018/verifiers/vps-aizanta-health-verifier.md` | EXISTS | P2-018: VPS Aizanta health verifier |
| `docs/setup-evidence/P2/STEP-P2-019/verification.md` | EXISTS | P2-019: Notification routing test (SEV0-SEV4) |
| `docs/setup-evidence/P2/STEP-P2-019/p2-019-implementation-summary.md` | EXISTS | P2-019: Implementation summary for notification routing |
| `docs/setup-evidence/P2/STEP-P2-019/verifiers/lsp-static-verifier.md` | EXISTS | P2-019: LSP static analysis verifier |
| `docs/setup-evidence/P2/STEP-P2-019/verifiers/token-unsafe-scan-verifier.md` | EXISTS | P2-019: Token unsafe scan verifier |
| `docs/setup-evidence/P2/STEP-P2-019/verifiers/vps-aizanta-health-verifier.md` | EXISTS | P2-019: VPS Aizanta health verifier |
| `docs/setup-evidence/P2/STEP-P2-020/verification.md` | EXISTS | P2-020: Gotify installation + test verification |
| `docs/setup-evidence/P2/STEP-P2-020/p2-020-implementation-summary.md` | EXISTS | P2-020: Implementation summary for Gotify |
| `docs/setup-evidence/P2/STEP-P2-020/docker-compose.yml` | EXISTS | P2-020: Docker Compose for Gotify (maps port 8081:80) |
| `docs/setup-evidence/P2/STEP-P2-020/verifiers/lsp-static-verifier.md` | EXISTS | P2-020: LSP static analysis verifier |
| `docs/setup-evidence/P2/STEP-P2-020/verifiers/token-unsafe-scan-verifier.md` | EXISTS | P2-020: Token unsafe scan verifier |
| `docs/setup-evidence/P2/STEP-P2-020/verifiers/vps-aizanta-health-verifier.md` | EXISTS | P2-020: VPS Aizanta health verifier |
| `docs/setup-evidence/P2/STEP-P2-021/verification.md` | EXISTS | P2-021: Discord -> Gotify fallback verification |
| `docs/setup-evidence/P2/STEP-P2-021/p2-021-implementation-summary.md` | EXISTS | P2-021: Implementation summary for Gotify fallback |
| `docs/setup-evidence/P2/STEP-P2-021/verifiers/lsp-static-verifier.md` | EXISTS | P2-021: LSP static analysis verifier |
| `docs/setup-evidence/P2/STEP-P2-021/verifiers/token-unsafe-scan-verifier.md` | EXISTS | P2-021: Token unsafe scan verifier |
| `docs/setup-evidence/P2/STEP-P2-021/verifiers/vps-aizanta-health-verifier.md` | EXISTS | P2-021: VPS Aizanta health verifier |

### Batch Plans

| Path | Status | Description |
|------|--------|-------------|
| `docs/setup-evidence/P2/batch-plan-001-003.md` | EXISTS | Batch plan: P2-001..003 (Discord app, token SOPS, intents) |
| `docs/setup-evidence/P2/batch-plan-004-006.md` | EXISTS | Batch plan: P2-004..006 (server, categories, channels) |
| `docs/setup-evidence/P2/batch-plan-007-009.md` | EXISTS | Batch plan: P2-007..009 (permissions, topics, bot invite) |
| `docs/setup-evidence/P2/batch-plan-010-012.md` | EXISTS | Batch plan: P2-010..012 (commands, colors, status) |
| `docs/setup-evidence/P2/batch-plan-013-016.md` | EXISTS | Batch plan: P2-013..016 (mood, help, safeword, startup) |
| `docs/setup-evidence/P2/batch-plan-017-019.md` | EXISTS | Batch plan: P2-017..019 (service, health, notifications) |
| `docs/setup-evidence/P2/batch-plan-020-021.md` | EXISTS | Batch plan: P2-020..021 (Gotify, fallback) |

### Batch Final Reports

| Path | Status | Description |
|------|--------|-------------|
| `docs/setup-evidence/P2/batch-013-016-final-report.md` | EXISTS | Batch final report: P2-013..016 |
| `docs/setup-evidence/P2/batch-017-019-final-report.md` | EXISTS | Batch final report: P2-017..019 |
| `docs/setup-evidence/P2/batch-020-021-final-report.md` | EXISTS | Batch final report: P2-020..021 |

### Research Files

| Path | Status | Description |
|------|--------|-------------|
| `docs/setup-evidence/P2/research/discordpy-bot-architecture-p2-017-019.md` | EXISTS | Research: Discord.py bot architecture for service wiring |
| `docs/setup-evidence/P2/research/discordpy-slash-cog-patterns.md` | EXISTS | Research: Discord.py slash command/cog patterns |
| `docs/setup-evidence/P2/research/discord-ux-embed-ephemeral.md` | EXISTS | Research: Discord UX embed + ephemeral patterns |
| `docs/setup-evidence/P2/research/gotify-external-docs.md` | EXISTS | Research: Gotify external documentation |
| `docs/setup-evidence/P2/research/health-routing-p2-018-019.md` | EXISTS | Research: Health routing for P2-018/019 |
| `docs/setup-evidence/P2/research/local-command-callbacks-p2-017.md` | EXISTS | Research: Local command callback patterns |
| `docs/setup-evidence/P2/research/local-discord-structure.md` | EXISTS | Research: Local discord codebase structure |
| `docs/setup-evidence/P2/research/local-discord-wiring-p2-017-019.md` | EXISTS | Research: Discord wiring for P2-017..019 |
| `docs/setup-evidence/P2/research/local-p2-020-021-patterns.md` | EXISTS | Research: Local patterns for P2-020..021 |
| `docs/setup-evidence/P2/research/local-service-scripts-p2-017-018.md` | EXISTS | Research: Local service scripts for P2-017/018 |
| `docs/setup-evidence/P2/research/local-startup-intents-p2-017.md` | EXISTS | Research: Startup intents for P2-017 |
| `docs/setup-evidence/P2/research/safety-p2-015-hard-stop.md` | EXISTS | Research: HARD STOP safety for P2-015 |
| `docs/setup-evidence/P2/research/safety-runtime-wiring-p2-017.md` | EXISTS | Research: Safety runtime wiring for P2-017 |
| `docs/setup-evidence/P2/research/step-prompts-013-016.md` | EXISTS | Research: Step prompts for P2-013..016 |
| `docs/setup-evidence/P2/research/step-prompts-017-019.md` | EXISTS | Research: Step prompts for P2-017..019 |
| `docs/setup-evidence/P2/research/systemd-health-routing-p2-017-019.md` | EXISTS | Research: Systemd health routing for P2-017..019 |
| `docs/setup-evidence/P2/research/systemd-service-p2-017.md` | EXISTS | Research: Systemd service design for P2-017 |

### VPS Deployment Checklist

| Path | Status | Description |
|------|--------|-------------|
| `docs/setup-evidence/P2/P2-VPS-DEPLOYMENT-CHECKLIST.md` | EXISTS | VPS deployment checklist for P2 |

---

## (b) docs/audit/ -- Previous P2 Audit Files

| Path | Status | Description |
|------|--------|-------------|
| `docs/audit/P2-AUDIT-COMPLETE.md` | EXISTS | Stale (2026-06-08): reported 14 PASS, 5 PARTIAL, 1 FAIL (P2-002 missing enc secret), 1 CRITICAL; channel utilization 3/13 active; methodology included code review, systemd, Discord REST polling |
| `docs/audit/P2-FIX-PLAN.md` | EXISTS | Stale (undated): Phase 1 SOPS fix completed; Phase 2 PROGRESS.md 33->35 doc fix not done; Phase 3 ghost channel cleanup not done; Phase 4 channel automation not done |

---

## (c) src/discord/ -- All Python Modules

### Entrypoint & Core

| Path | Status | Description |
|------|--------|-------------|
| `src/discord/_entrypoint.py` | EXISTS ACTIVE | Service entrypoint (`python -m src.discord._entrypoint`) |
| `src/discord/__init__.py` | EXISTS ACTIVE | Package marker (`# src/discord module`) |
| `src/discord/_command_registry.py` | EXISTS ACTIVE | Canonical slash-command spec and REST payload builders (35+ commands) |
| `src/discord/_intents.py` | EXISTS ACTIVE | Bot intents configuration |
| `src/discord/_startup.py` | EXISTS ACTIVE | Startup logic ("Mommy sudah bangun, Darling.") |
| `src/discord/_auth_guard.py` | EXISTS ACTIVE | Authorization guard for commands |
| `src/discord/_embed_utils.py` | EXISTS ACTIVE | Embed formatting utilities |

### Command Modules (45 cmd_*.py files)

| Path | Status | Description |
|------|--------|-------------|
| `src/discord/cmd_approve.py` | EXISTS ACTIVE | `/approve` -- Approve destructive operations |
| `src/discord/cmd_approve_all.py` | EXISTS ACTIVE | `/approve-all` -- Approve all pending |
| `src/discord/cmd_backup_now.py` | EXISTS ACTIVE | `/backup-now` -- Trigger immediate backup |
| `src/discord/cmd_budget.py` | EXISTS ACTIVE | `/budget` -- Budget status |
| `src/discord/cmd_casual.py` | EXISTS ACTIVE | `/casual` -- Toggle casual mode |
| `src/discord/cmd_clear_cache.py` | EXISTS ACTIVE | `/clear-cache` -- Clear cache |
| `src/discord/cmd_consent.py` | EXISTS ACTIVE | `/consent` -- Consent management |
| `src/discord/cmd_cost.py` | EXISTS ACTIVE | `/cost` -- Cost tracking |
| `src/discord/cmd_cost_alert.py` | EXISTS ACTIVE | `/cost-alert` -- Cost alert threshold |
| `src/discord/cmd_deny.py` | EXISTS ACTIVE | `/deny` -- Deny pending operation |
| `src/discord/cmd_email.py` | EXISTS ACTIVE | `/email` -- Email commands |
| `src/discord/cmd_evidence.py` | EXISTS ACTIVE | `/evidence` -- Evidence commands |
| `src/discord/cmd_focus.py` | EXISTS ACTIVE | `/focus` -- Focus mode |
| `src/discord/cmd_health_check.py` | EXISTS ACTIVE | `/health-check` -- Health check |
| `src/discord/cmd_health_report.py` | EXISTS ACTIVE | `/health-report` -- Health report (P14 wearable) |
| `src/discord/cmd_help.py` | EXISTS ACTIVE | `/help` -- Command help |
| `src/discord/cmd_history.py` | EXISTS ACTIVE | `/history` -- History |
| `src/discord/cmd_loop_cost.py` | EXISTS ACTIVE | `/loop-cost` -- Loop cost |
| `src/discord/cmd_loop_history.py` | EXISTS ACTIVE | `/loop-history` -- Loop history |
| `src/discord/cmd_loop_pause.py` | EXISTS ACTIVE | `/loop-pause` -- Pause loop |
| `src/discord/cmd_loop_priority.py` | EXISTS ACTIVE | `/loop-priority` -- Loop priority |
| `src/discord/cmd_loop_resume.py` | EXISTS ACTIVE | `/loop-resume` -- Resume loop |
| `src/discord/cmd_loop_start.py` | EXISTS ACTIVE | `/loop-start` -- Start loop |
| `src/discord/cmd_loop_status.py` | EXISTS ACTIVE | `/loop-status` -- Loop status |
| `src/discord/cmd_loop_stop.py` | EXISTS ACTIVE | `/loop-stop` -- Stop loop |
| `src/discord/cmd_loops.py` | EXISTS ACTIVE | `/loops` -- Loop listing |
| `src/discord/cmd_memory_add.py` | EXISTS ACTIVE | `/memory-add` -- Add memory |
| `src/discord/cmd_memory_decay.py` | EXISTS ACTIVE | `/memory-decay` -- Memory decay settings |
| `src/discord/cmd_memory_export.py` | EXISTS ACTIVE | `/memory-export` -- Export memories |
| `src/discord/cmd_memory_forget.py` | EXISTS ACTIVE | `/memory-forget` -- Forget memory |
| `src/discord/cmd_memory_review.py` | EXISTS ACTIVE | `/memory-review` -- Review memories |
| `src/discord/cmd_memory_schedule.py` | EXISTS ACTIVE | `/memory-schedule` -- Memory schedule |
| `src/discord/cmd_memory_search.py` | EXISTS ACTIVE | `/memory-search` -- Search memories |
| `src/discord/cmd_memory_stats.py` | EXISTS ACTIVE | `/memory-stats` -- Memory statistics |
| `src/discord/cmd_mood.py` | EXISTS ACTIVE | `/mood` -- Mood status |
| `src/discord/cmd_new_session.py` | EXISTS ACTIVE | `/new-session` -- New session |
| `src/discord/cmd_pc.py` | EXISTS ACTIVE | `/pc` -- PC command (status + session override, P15) |
| `src/discord/cmd_punishment.py` | EXISTS ACTIVE | `/punishment` -- Punishment command |
| `src/discord/cmd_restart_service.py` | EXISTS ACTIVE | `/restart-service` -- Restart a service |
| `src/discord/cmd_reward.py` | EXISTS ACTIVE | `/reward` -- Reward command |
| `src/discord/cmd_safeword.py` | EXISTS ACTIVE | `/safeword` -- HARD STOP safeword (slash only; on_message unwired per docstring) |
| `src/discord/cmd_status.py` | EXISTS ACTIVE | `/status` -- System status (11 fields) |
| `src/discord/cmd_surveillance_pause.py` | EXISTS ACTIVE | `/surveillance-pause` -- Pause surveillance |
| `src/discord/cmd_surveillance_resume.py` | EXISTS ACTIVE | `/surveillance-resume` -- Resume surveillance |
| `src/discord/cmd_surveillance_status.py` | EXISTS ACTIVE | `/surveillance-status` -- Surveillance status |

### Helper Modules

| Path | Status | Description |
|------|--------|-------------|
| `src/discord/colors.py` | EXISTS ACTIVE | Embed color constants (primary=#6B21A8, alerts=#DC2626, achievements=#CA8A04) |
| `src/discord/gotify_fallback.py` | EXISTS ACTIVE | Gotify HTTP fallback client; hardcodes GOTIFY_URL = "http://localhost:8081" |
| `src/discord/notifications.py` | EXISTS ACTIVE | Notification routing; SEV0/1->system-health, SEV2->cost-tracker, SEV3->guinevere-status, SEV4->audit-log; has bare `import discord` at module level ~L240 |
| `src/discord/shadow_monitor.py` | EXISTS ACTIVE | Shadow monitor for safety |
| `src/discord/shadow_pipeline.py` | EXISTS ACTIVE | Shadow pipeline processing |
| `src/discord/hermes_conversational.py` | EXISTS ACTIVE | Hermes conversational handler |

### Listeners

| Path | Status | Description |
|------|--------|-------------|
| `src/discord/listeners/__init__.py` | EXISTS ACTIVE | Listeners package init |
| `src/discord/listeners/gmail_reactions.py` | EXISTS ACTIVE | Gmail reaction listener |
| `src/discord/listeners/x_reactions.py` | EXISTS ACTIVE | X/Twitter reaction listener |

### Loops

| Path | Status | Description |
|------|--------|-------------|
| `src/discord/loops/__init__.py` | EXISTS ACTIVE | Loops package init |

### Archived / Stale (.bak) Files

| Path | Status | Description |
|------|--------|-------------|
| `src/discord/bot.py.bak.pre-phase2` | EXISTS ARCHIVED | Original standalone bot.py (512 lines), replaced by Hermes Gateway post-ADR-035 |
| `src/discord/conversational_handler.py.bak.pre-phase2` | EXISTS ARCHIVED | Original conversational handler (496 lines), replaced by Hermes Gateway |

---

## (d) src/life_kernel/ -- Discord-Touching Files

| Path | Status | Description |
|------|--------|-------------|
| `src/life_kernel/discord_rest_client.py` | EXISTS ACTIVE | Option-B core REST publisher for Discord (P20); httpx + tenacity, reads DISCORD_BOT_TOKEN from env, fail-soft, never logs token |
| `src/life_kernel/sensor_adapters/discord_adapter.py` | EXISTS ACTIVE | Discord adapter for sensor inputs |
| `src/life_kernel/dashboard.py` | EXISTS ACTIVE | Dashboard logic (Discord-visible state) |
| `src/life_kernel/dashboard_writer.py` | EXISTS ACTIVE | Dashboard writer to Discord (P20) |
| `src/life_kernel/log_channel.py` | EXISTS ACTIVE | Log channel writer to Discord (P20) |
| `src/life_kernel/state.py` | EXISTS ACTIVE | State management (Discord-visible) |
| `src/life_kernel/heartbeat.py` | EXISTS ACTIVE | Heartbeat (Discord-visible) |
| `src/life_kernel/hermes_brain.py` | EXISTS ACTIVE | Hermes brain (Discord-visible) |
| `src/life_kernel/graph.py` | EXISTS ACTIVE | Graph (Discord-visible) |
| `src/life_kernel/session_graph.py` | EXISTS ACTIVE | Session graph (Discord-visible) |
| `src/life_kernel/__init__.py` | EXISTS ACTIVE | Life kernel init (Discord-visible) |
| `src/life_kernel/sensor_adapters/__init__.py` | EXISTS ACTIVE | Sensor adapters init |
| `src/life_kernel/sensor_adapters/base.py` | EXISTS ACTIVE | Sensor adapter base class |

---

## (e) src/gmail/draft/ -- Email Draft Discord UX

| Path | Status | Description |
|------|--------|-------------|
| `src/gmail/draft/discord_ux.py` | EXISTS ACTIVE | Discord embed + reaction-based draft approval flow; presents draft replies as embeds with check/cross/pencil reactions, Faiz-only approval, state persisted to Redis HASH with TTL |

---

## (f) guinevere-discord.service Copies

| Path | Status | Description |
|------|--------|-------------|
| `systemd/guinevere-discord.service` | EXISTS ACTIVE | Template: EnvironmentFile=.env.discord (PLAINTEXT token), ExecStart=python -m src.discord._entrypoint, no SOPS, no shred. MemoryHigh=512M, MemoryMax=1G, CPUQuota=100%. |
| `deploy/discord/guinevere-discord.service` | EXISTS ACTIVE | Deploy version: ExecStartPre decrypts secrets/.env.discord.sops -> /run/guinevere-discord-token, chmod 600, ExecStopPost shreds token. MemoryHigh=512M, MemoryMax=768M. |
| `vps-mirror/systemd-live/guinevere-discord.service` | MISSING | No discord service in vps-mirror/systemd-live/ (only loops, mcp, monitoring, scheduler, surveillance, obscura, health-check, 9router, core, hermes-gateway) |
| `vps-mirror/systemd-live/hermes-gateway.service` | EXISTS ACTIVE | Live mirror: ExecStart=`hermes gateway run --accept-hooks`, EnvironmentFile=.env.hermes, weaker hardening (no ProtectSystem/ProtectHome) |

---

## (g) hermes-gateway.service Copies

| Path | Status | Description |
|------|--------|-------------|
| `systemd/hermes-gateway.service` | EXISTS ACTIVE | Template: ExecStart=`hermes --config .../hermes-config/config.yaml gateway`, EnvironmentFile=.env.hermes, full hardening |
| `scripts/hermes-gateway.service` | EXISTS ACTIVE | Script variant: ExecStart=`hermes gateway run --accept-hooks`, EnvironmentFile=.hermes/.env, lighter security |
| `vps-mirror/systemd-live/hermes-gateway.service` | EXISTS ACTIVE | Live VPS mirror: ExecStart=`hermes gateway run --accept-hooks`, EnvironmentFile=.env.hermes, **no** ProtectSystem/ProtectHome/PrivateTmp |

---

## (h) Secrets Files (Name Only)

| Path | Status | Description |
|------|--------|-------------|
| `secrets/discord-secrets.enc.yaml` | EXISTS ENCRYPTED | SOPS-encrypted Discord token + bot ID; AES256_GCM encrypted, age key present in metadata |
| `secrets/.env.discord.sops` | MISSING | Referenced by deploy/discord/guinevere-discord.service ExecStartPre but does not exist under this name. The deploy service expects this path but the only Discord enc file is discord-secrets.enc.yaml. |
| `.env.discord` | MISSING | Referenced by systemd/guinevere-discord.service EnvironmentFile but not present in repo (local VPS file, not committed) |
| `.sops.yaml` | EXISTS ACTIVE | Root SOPS config: encryption rules for secrets/*.yaml, secrets/*.env, secrets/*.json using age key |
| `secrets/guinevere-secrets.yaml` | EXISTS ENCRYPTED | General secrets (not Discord-specific; may contain shared secrets) |
| `secrets/db-passwords.yaml` | EXISTS ENCRYPTED | Database passwords |
| `secrets/redis-password.yaml` | EXISTS ENCRYPTED | Redis password |
| `secrets/gmail-client-secrets.json` | EXISTS ENCRYPTED | Gmail client credentials |
| `secrets/gmail-token.json` | EXISTS ENCRYPTED | Gmail OAuth token |
| `secrets/test-enc.yaml` | EXISTS ENCRYPTED | Test encryption artifact |
| `secrets/new-age-key.txt` | EXISTS PLAINTEXT | Age key file (existence noted; path only, no value) |

---

## (i) Test Files

### tests/discord/ -- All .py Test Files (not __pycache__)

| Path | Status | Description |
|------|--------|-------------|
| `tests/discord/conftest.py` | EXISTS ACTIVE | Test fixtures for Discord tests |
| `tests/discord/test_bot.py` | EXISTS ACTIVE | Bot tests |
| `tests/discord/test_cmd_health_report.py` | EXISTS ACTIVE | Health report command tests (P14) |
| `tests/discord/test_cmd_mood.py` | EXISTS ACTIVE | Mood command tests |
| `tests/discord/test_cmd_pc.py` | EXISTS ACTIVE | PC command tests |
| `tests/discord/test_cmd_punishment_reward.py` | EXISTS ACTIVE | Punishment/reward command tests |
| `tests/discord/test_conversational_handler.py.archived` | EXISTS ARCHIVED | Archived conversational handler test |
| `tests/discord/test_gotify_client.py` | EXISTS ACTIVE | Gotify client tests |
| `tests/discord/test_gotify_fallback.py` | EXISTS ACTIVE | Gotify fallback tests |
| `tests/discord/test_hermes_conversational.py` | EXISTS ACTIVE | Hermes conversational tests |
| `tests/discord/test_notifications.py` | EXISTS ACTIVE | Notification tests |
| `tests/discord/test_startup.py` | EXISTS ACTIVE | Startup tests |
| `tests/discord/test_x_upload_handler.py` | EXISTS ACTIVE | X upload handler tests |

### tests/life_kernel/ -- Files Touching Discord

| Path | Status | Description |
|------|--------|-------------|
| `tests/life_kernel/test_dashboard.py` | EXISTS ACTIVE | Dashboard tests (references discord_rest output) |
| `tests/life_kernel/test_session_graph.py` | EXISTS ACTIVE | Session graph tests (references discord) |
| `tests/life_kernel/test_sensors.py` | EXISTS ACTIVE | Sensor tests (references discord_adapter) |

---

## (j) CHECKLIST.md + PROGRESS.md P2 Sections

| File | Lines | Description |
|------|-------|-------------|
| `CHECKLIST.md` | 241-306 | Phase 2: Discord Bot Verification section (241-306). Line 265 claims "33 slash commands" while `._command_registry.py` has 35+ / PROGRESS.md says 35. Line 256-277 enumerates P2-001 through P2-021 checks; P2-020 and P2-021 NOT checked. |
| `PROGRESS.md` | 134-158 | P2: Discord Bot (21 steps). Line 146 claims 35 commands. Includes P2-022 (service masked intentionally). |

---

## (k) ADRs Referencing Discord

| Path | Status | Description |
|------|--------|-------------|
| `adr/ADR-022-communication-channel-strategy.md` | EXISTS | Communication channel strategy -- Discord primary, WhatsApp secondary (P11), Gotify fallback |
| `adr/ADR-026-public-endpoint-cloudflare-tunnel.md` | EXISTS | Cloudflare Tunnel for Discord webhook (webhook-only exposure) |
| `adr/ADR-035-hermes-migration.md` | EXISTS | Hermes Migration Architecture -- Discord gateway = MIGRATE to Hermes native gateway; eliminates bot.py (512), conversational_handler.py (496), session_adapter.py (302); 35 slash commands -> Hermes plugins |
| `adr/ADR-036-code-quality-debt.md` | EXISTS | Code quality/debt (references discord code) |
| `adr/ADR-037-wearable-health-pipeline.md` | EXISTS | Wearable health pipeline (Discord surface) |
| `adr/ADR-039-gadgetbridge-sqlite-parser.md` | EXISTS | Gadgetbridge SQLite parser (Discord commands) |
| `adr/ADR-040-health-connect-pivot.md` | EXISTS | Health Connect pivot (Discord commands) |
| `adr/ADR-052-multi-project-context.md` | EXISTS | Multi-project context (Discord dashboard UX) |
| `adr/ADR-019-access-control-vpn-mesh-strategy.md` | EXISTS | Access control/VPN mesh (Discord webhook/API) |
| `adr/ADR-030-redis-db-assignments.md` | EXISTS | Redis DB assignments (shared pool with Discord) |
| `adr/ADR-029-self-modification-automated-testing.md` | EXISTS | Self-modification testing (references Discord commands) |

---

## (l) config/hermes/ -- Hermes Config

| Path | Status | Description |
|------|--------|-------------|
| `config/hermes/` | Directory does not exist | Hermes config is at `hermes-config/` in repo root, not `config/hermes/` |

---

## Summary Statistics

| Category | Active | Archived/Stale | Missing | Total |
|----------|--------|----------------|---------|-------|
| (a) P2 Evidence (verifications, plans, reports, research) | 84 | 0 | 0 | 84 |
| (b) Audit docs | 2 | 2 | 0 | 2 |
| (c) src/discord/ modules | 58 | 2 | 0 | 60 |
| (d) life_kernel Discord files | 13 | 0 | 0 | 13 |
| (e) gmail draft Discord UX | 1 | 0 | 0 | 1 |
| (f) guinevere-discord.service copies | 2 | 0 | 1 | 3 |
| (g) hermes-gateway.service copies | 3 | 0 | 0 | 3 |
| (h) Secrets files | 7 (+2 enc) | 0 | 1 | 10 |
| (i) Tests | 16 | 1 | 0 | 17 |
| (j) Checklist/Progress P2 sections | 2 | 0 | 0 | 2 |
| (k) ADRs referencing Discord | 10 | 0 | 0 | 10 |
| (l) config/hermes | 0 | 0 | 1 | 1 |
| **Grand Total** | **198** | **5** | **3** | **206** |

---

## Key Integrity Observations

1. **35-vs-33 command count**: CHECKLIST.md line 265 says "33 slash commands" but PROGRESS.md line 146 says 35 and the code has 45 `cmd_*.py` files (some register multiple commands). The old P2-AUDIT-COMPLETE.md noted this mismatch, and P2-FIX-PLAN.md Phase 2.1 to fix it remains UNIMPLEMENTED.

2. **14-vs-13 channel count**: `channel-ids.yaml` lists 14 channels (includes `rituals` + `project-alpha-dev`/`project-alpha-docs`/`project-beta-dev` ghost channels). CHECKLIST.md line 261 says "13 channels". P2-FIX-PLAN Phase 3 ghost cleanup not done.

3. **Gotify port 8081 vs 8080**: The docker-compose.yml in STEP-P2-020 maps `8081:80`, and gotify_fallback.py hardcodes `GOTIFY_URL = "http://localhost:8081"`. Old audit referenced port 8080. CONFIRMED: code and deploy evidence agree on 8081.

4. **`secrets/.env.discord.sops` MISSING**: The `deploy/discord/guinevere-discord.service` ExecStartPre expects `secrets/.env.discord.sops` to exist, but the only Discord encrypted file is `secrets/discord-secrets.enc.yaml`. Either the deploy service file is stale/dead (likely, since P2-022 says standalone service is masked) or the file exists on VPS but not in repo.

5. **No `guinevere-discord.service` in vps-mirror/systemd-live/**: The live mirror has no Discord service, consistent with P2-022 (standalone bot masked) and the claim that the core REST publisher handles Discord writer duty.

6. **Three hermes-gateway.service variants**: `systemd/` uses `hermes --config .../config.yaml gateway`, `scripts/` uses `hermes gateway run --accept-hooks`, `vps-mirror/systemd-live/` uses `hermes gateway run --accept-hooks` with weaker hardening. This 3-variant conflict from the seed facts is CONFIRMED.

7. **`.env.hermes` vs `.hermes/.env` conflict**: `systemd/hermes-gateway.service` reads `.env.hermes`, `scripts/hermes-gateway.service` reads `.hermes/.env`. Different environment file locations.

8. **HARD STOP on_message unwired**: `cmd_safeword.py` docstring explicitly states on_message listener does not exist -- only `/safeword` slash command works. This is CONFIRMED from the code documentation.

9. **P2 step count**: PROGRESS.md says 21 steps (P2-001..021) + P2-022 (masked) = 22 total. CHECKLIST.md enumerates P2-001..021. P2-AUDIT-COMPLETE.md reported on 22 steps.

10. **Notification SEV routing**: `notifications.py` routes SEV0/SEV1->system-health, SEV2->cost-tracker, SEV3->guinevere-status, SEV4->audit-log. This matches the seed. The phase-2-discord.md migration doc reference to `#alerts` / guinevere-alerts is a drift that would need verification against the migration document.

11. **Gotify port mismatch RESOLVED**: The seed flagged port 8081 vs 8080. The docker-compose and code both use 8081. The old audit's port 8080 reference is stale. RESOLVED in current code.

12. **SOPS encryption rules**: `.sops.yaml` covers `secrets/*.yaml` with age encryption. `secrets/discord-secrets.enc.yaml` IS encrypted (AES256_GCM ciphertext visible). The deploy service path `secrets/.env.discord.sops` does NOT match any SOPS path_regex pattern (which covers `.*\.yaml$`, `.*\.env$`, `.*\.json$` -- `.sops` is suffix, not `.env` nor `.yaml`), suggesting the deploy service file references a file that either doesn't exist or was created with a different rule.
