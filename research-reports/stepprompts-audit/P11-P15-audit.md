# StepPrompts Audit: P11-P15 — Hermes Migration Impact (Post-ADR-035)

**Date:** 2026-06-05
**Auditor:** Guinevere (Sisyphus-Junior) — parent read + grep verification
**Scope:** `stepprompts/StepPrompts.md` phases P11-P15 (122 steps, lines 19492-57358)
**Context:** ADR-035 (Hermes NousResearch Migration Architecture) accepted 2026-06-04. None of P11-P15 are implemented. Hermes migration Pillar 1 replaces `bot.py`/`conversational_handler.py`/`session_adapter.py`/`commands.py` with Hermes native Discord gateway. All 35 slash commands migrate to Hermes plugins.

---

## Classification Key

| Verdict | Meaning | Impact |
|---|---|---|
| **VALID** | Zero Discord interaction, OR abstract patterns that map cleanly to Hermes. Backend logic, DB, API, infrastructure — no code changes needed post-ADR-035. | **0 work** |
| **NEEDS-UPDATE** | References Discord commands/notifications conceptually (e.g., "implement `/x-status` command") but core logic is backend-valid. Discord surface needs Hermes plugin wrapping with minimal redesign. | **~1h per step** — plugin wrapper |
| **DEPENDS-ON-OLD-BOT** | Codes to specific `discord.py`/`bot.py` patterns: `GuinevereBot`, `commands.Bot`, `discord.Client` as constructor param, `discord.Embed`, `discord.utils.get`, `tree.command`, `app_commands.CommandTree`, `channel.send`, DM patterns. Needs significant redesign for Hermes hooks/plugins. | **~3-4h per step** — redesign + reimplement |

---

## Per-Step Classification Tables

### P11: WhatsApp/Neonize Integration (23 steps)

| Step | Title | Classification | Rationale |
|---|---|---|---|
| P11-001 | Neonize Dependency + Environment Setup | **VALID** | Pure Python dependency setup, zero Discord interaction |
| P11-002 | Session Management — QR Scan, Pairing, SOPS + Redis | **VALID** | WhatsApp auth + session persistence, no Discord |
| P11-003 | Neonize Connection Handler — Send/Receive, Events | **VALID** | WhatsApp WebSocket handler, no Discord |
| P11-004 | ChannelAdapter Abstract Interface + UnifiedMessage | **VALID** | Abstract interface definition, transport-agnostic |
| P11-005 | WhatsApp ChannelAdapter Implementation | **VALID** | WhatsApp-specific adapter, no Discord |
| P11-006 | ConversationalAgent Core — LLMRouter + Persona + Response | **VALID** | LLM routing + persona, no Discord |
| P11-007 | Conversation Context Manager — Sliding Window, Shared Memory | **VALID** | Memory/context management, no Discord |
| P11-008 | Message Routing Pipeline — Intent → Agent/Command → Response | **VALID** | Internal routing logic, no Discord |
| P11-009 | Natural Language Intent Classifier | **VALID** | NL classification, no Discord |
| P11-010 | Command Handler (`!` prefix) — Mirror Discord Slash Commands | **NEEDS-UPDATE** | Core: WhatsApp `!` command handler. References Discord slash commands as equivalence target + `discord.app_commands.CommandTree` for audit. Backend valid; Discord surface needs Hermes plugin mapping. |
| P11-011 | Typing Indicator + Response Streaming | **VALID** | WhatsApp-native UI, no Discord |
| P11-012 | Response Formatting — Auto-Split, Markdown → WhatsApp | **VALID** | WhatsApp formatting, no Discord |
| P11-013 | Media Acknowledgment Handler | **VALID** | WhatsApp media handling, no Discord |
| P11-014 | Rate Limiter — 8/min, 30/hour, 200/day, Gaussian Jitter | **VALID** | WhatsApp rate limiting, no Discord |
| P11-015 | Cross-Channel HARD STOP — Shared Redis Flag | **NEEDS-UPDATE** | Core: shared Redis flag (valid). References `HardStopHandler` in `src/discord/bot.py` for Discord-side trigger. Redis flag logic unchanged; Discord trigger moves to `pre_prompt` hook per ADR-035. |
| P11-016 | Safe Word + Consent Flow | **VALID** | WhatsApp-native consent, no Discord dependency |
| P11-017 | Number Whitelist + Access Control | **VALID** | WhatsApp access control, no Discord |
| P11-018 | Discord Bridge — Message Mirror to Private Channel | **DEPENDS-ON-OLD-BOT** | Heavy: `GuinevereBot` constructor param, `discord.Embed`, `discord.utils.get`, `bot.get_channel()`, `src/discord/bot.py` imports, `src/discord/notifications.py` patterns. Needs full redesign as Hermes plugin or notification hook. |
| P11-019 | Discord Bridge — Notifications + Status Embed | **DEPENDS-ON-OLD-BOT** | Heavy: `GuinevereBot`, `commands.Bot`, `command_prefix="!"`, `!wa-status` text command, `send_alert()`, `SEV_MATRIX`, `src/discord/notifications.py`, Gotify fallback routing. Needs Hermes notification plugin + command plugin redesign. |
| P11-020 | Reconnection Handler — 3 Retry, Exponential Backoff | **VALID** | WhatsApp reconnection logic, no Discord |
| P11-021 | Health Check + Grafana Monitoring — 60s Interval | **VALID** | Monitoring infrastructure, no Discord |
| P11-022 | Systemd Unit + Operational Runbook | **VALID** | Systemd service definition, no Discord |
| P11-023 | E2E Integration Test — Full Flow Verification | **VALID** | Integration testing, no Discord |

**P11 Summary:** 19 VALID | 2 NEEDS-UPDATE | 2 DEPENDS-ON-OLD-BOT

---

### P12: Gmail/Email Integration (29 steps)

| Step | Title | Classification | Rationale |
|---|---|---|---|
| P12-001 | GCP Project + API Enablement | **VALID** | GCP infrastructure, no Discord |
| P12-002 | OAuth2 Token Management + `!email-reauth` | **NEEDS-UPDATE** | Core: OAuth2 token management (valid). References `!email-reauth` text command — needs Hermes plugin port. |
| P12-003 | Resend Client Setup | **VALID** | Email sending client, no Discord |
| P12-004 | Gmail API Client Wrapper | **VALID** | Gmail API wrapper, no Discord |
| P12-005 | Incremental Sync Engine | **VALID** | Email sync engine, no Discord |
| P12-006 | Pub/Sub StreamingPull + Watch Renewal | **VALID** | GCP Pub/Sub pipeline, no Discord |
| P12-007 | GmailAdapter (ChannelAdapter Implementation) | **VALID** | Channel adapter, no Discord |
| P12-008 | Channel Context Manager | **VALID** | Context management, no Discord |
| P12-009 | Email Classifier (Cascade Pattern) | **VALID** | ML classification, no Discord |
| P12-010 | Importance Scorer | **VALID** | Scoring algorithm, no Discord |
| P12-011 | Content Sanitizer + Injection Defense | **VALID** | Security sanitization, no Discord |
| P12-012 | Secret Scanner + PII Redactor | **VALID** | Security scanning, no Discord |
| P12-013 | Memory Store Integration | **VALID** | PostgreSQL memory store, no Discord |
| P12-014 | Financial Email → P9 Bridge | **VALID** | Backend bridge, no Discord |
| P12-015 | Draft Generator (LLM) | **VALID** | LLM draft generation, no Discord |
| P12-016 | Discord Draft UX | **DEPENDS-ON-OLD-BOT** | Draft approval UX references `src/discord/bot.py`, `discord.ext.commands.Bot`, `register_commands(bot)`, `cmd_status.py` UX patterns. Discord approval flow needs Hermes plugin redesign. |
| P12-017 | Gmail Draft Sync + Send | **VALID** | Gmail API draft operations, no Discord |
| P12-018 | Real-Time Email Notifications | **NEEDS-UPDATE** | Core: email notification logic (valid). References Discord DM/channel as delivery mechanism — needs Hermes notification plugin mapping. |
| P12-019 | Morning Briefing + On-Demand Digest | **DEPENDS-ON-OLD-BOT** | References `src/discord/bot.py` command registration, `register_commands(bot)` in `startup.py`, `!email-digest` text command pattern. Digest generation logic is valid but delivery is deeply tied to bot.py command infrastructure. |
| P12-020 | `!email-digest` Command | **NEEDS-UPDATE** | Discord text command for email digest. Core: queries email pipeline (valid). Command surface needs Hermes plugin port. |
| P12-021 | `!email-consent` + `!email-reauth` Commands | **NEEDS-UPDATE** | Discord commands for consent/reauth. Core: consent state management (valid). Command surface needs Hermes plugin port. |
| P12-022 | Cross-Channel HARD STOP | **VALID** | HARD STOP enforcement, no Discord-specific code |
| P12-023 | Surveillance Classification | **VALID** | Data classification, no Discord |
| P12-024 | Watch Renewal + Health Check | **VALID** | GCP watch renewal, no Discord |
| P12-025 | Grafana Dashboard + Metrics | **VALID** | Monitoring infrastructure, no Discord |
| P12-026 | Systemd Service + Runbook | **VALID** | Service definition, no Discord |
| P12-027 | E2E Integration Test — Full Flow Verification (P12 GATE) | **VALID** | Integration testing, no Discord |
| P12-028 | Agent Loop Trigger Detector | **VALID** | Loop integration, no Discord |
| P12-029 | TaskContract Email Context | **VALID** | Task context enrichment, no Discord |

**P12 Summary:** 22 VALID | 5 NEEDS-UPDATE | 2 DEPENDS-ON-OLD-BOT

---

### P13: X Auto Poster (28 steps)

| Step | Title | Classification | Rationale |
|---|---|---|---|
| P13-001 | S3 Queue Setup | **VALID** | S3 infrastructure, no Discord |
| P13-002 | Windows Watchdog Script | **VALID** | Windows daemon script, no Discord |
| P13-003 | Obscura CDP Dedicated Instance | **VALID** | Browser automation, no Discord |
| P13-004 | Systemd Service | **VALID** | Service definition, no Discord |
| P13-005 | Queue Polling Loop | **VALID** | Polling logic, no Discord |
| P13-006 | Sidecar Parser | **VALID** | Queue parser, no Discord |
| P13-007 | Rate Limiter | **VALID** | Rate limiting, no Discord |
| P13-008 | Cookie Injector | **VALID** | Cookie management, no Discord |
| P13-009 | Session Health Check | **VALID** | Session monitoring, no Discord |
| P13-010 | Session Recovery | **VALID** | Recovery logic, no Discord (references `/x-resume` conceptually, not in code) |
| P13-011 | Caption Generator | **VALID** | Gemini captioning, no Discord |
| P13-012 | Content Moderation | **VALID** | Content filtering, no Discord |
| P13-013 | Tone Controller | **VALID** | Tone adjustment, no Discord |
| P13-014 | Compose Adapter (CDP) | **VALID** | CDP compose, no Discord |
| P13-015 | Media Upload (CDP) | **VALID** | CDP upload, no Discord |
| P13-016 | Post Action | **VALID** | Post execution, no Discord |
| P13-017 | Dry-Run Mode | **VALID** | Dry-run logic, no Discord |
| P13-018 | Retry Engine | **VALID** | Retry logic, no Discord |
| P13-019 | Circuit Breaker | **VALID** | Circuit breaker, no Discord |
| P13-020 | Processing Timeout Handler | **VALID** | Timeout handling, no Discord |
| P13-021 | Post Notification | **NEEDS-UPDATE** | Core: notification generation (valid). References "Discord embed after successful post" as delivery — needs Hermes notification plugin mapping. |
| P13-022 | Status Commands (`/x-status`, `/x-list`, `/x-cancel`, `/x-hold`) | **NEEDS-UPDATE** | 4 Discord slash commands. Core: queries queue/state (valid). References abstract "Discord controls" — needs Hermes plugin ports. |
| P13-023 | Edit Command (`/x-edit`) | **NEEDS-UPDATE** | Discord slash command for editing scheduled posts. Core: edit logic (valid). Command surface needs Hermes plugin port. |
| P13-024 | Delete Command (`/x-delete`) | **NEEDS-UPDATE** | Discord slash command for deleting posts. Core: delete logic (valid). Command surface needs Hermes plugin port. |
| P13-025 | Retry Commands (`/x-retry`, `/x-dryrun`) | **NEEDS-UPDATE** | 2 Discord slash commands. Core: retry/dryrun logic (valid). Command surface needs Hermes plugin port. |
| P13-026 | Grafana Dashboard | **VALID** | Monitoring infrastructure, no Discord |
| P13-027 | Daily Summary | **NEEDS-UPDATE** | Core: summary generation (valid). References "Daily 20:00 WIB summary to Discord" — needs Hermes cron + notification plugin. |
| P13-028 | Integration Test + P13 GATE | **VALID** | Integration testing, no Discord |

**P13 Summary:** 22 VALID | 6 NEEDS-UPDATE | 0 DEPENDS-ON-OLD-BOT

---

### P14: Wearable/Xiaomi Watch (27 steps)

| Step | Title | Classification | Rationale |
|---|---|---|---|
| P14-001 | Device Procurement + Gadgetbridge Setup | **VALID** | Hardware procurement, no Discord |
| P14-002 | WebDAV Server Endpoint | **VALID** | WebDAV setup, no Discord |
| P14-003 | Database Schema Creation | **VALID** | PostgreSQL schema, no Discord |
| P14-004 | HMAC Key Provisioning | **VALID** | Security key provisioning, no Discord |
| P14-005 | Gadgetbridge SQLite Parser | **VALID** | Data parser, no Discord |
| P14-006 | Health Ingestion Endpoint | **VALID** | API endpoint, no Discord |
| P14-007 | Consumer Scope Mapping — Consent Gate for Health Data | **VALID** | Consent gate, no Discord |
| P14-008 | Mi Fitness Cloud SDK Fallback | **VALID** | Cloud SDK fallback, no Discord |
| P14-009 | Personal Baseline Computation | **VALID** | Baseline algorithm, no Discord |
| P14-010 | Anomaly Detection Engine | **VALID** | Anomaly detection, no Discord |
| P14-011 | GHI Composite Score Engine | **VALID** | GHI scoring, no Discord |
| P14-012 | Daily Summary Pre-computation | **VALID** | Summary computation, no Discord |
| P14-013 | Persona State Machine | **VALID** | FSM logic, no Discord |
| P14-014 | Health Memory Injection | **VALID** | Memory injection, no Discord |
| P14-015 | Distress Escalation Logic | **NEEDS-UPDATE** | Core: distress escalation FSM (valid). Integration table references `src/discord/notifications.py`, `src/discord/bot.py` for Discord notification routing. FSM logic unchanged; Discord delivery surface needs Hermes notification hook mapping. |
| P14-016 | `/health-status` + `/ghi-score` Discord Commands | **DEPENDS-ON-OLD-BOT** | Heavy: `@tree.command()` decorator, `defer_ephemeral()` + `followup.send()`, `app_commands.CommandTree`, integration table references `src/discord/_embed_helpers.py`, `src/discord/colors.py`, `src/discord/commands.py`. Embed construction logic valid but registration/delivery deeply tied to discord.py. Needs Hermes plugin redesign. |
| P14-017 | `/sleep-report` + `/activity-today` Discord Commands | **DEPENDS-ON-OLD-BOT** | Heavy: Same `@tree.command()` + `app_commands.CommandTree` patterns as P14-016. Query logic valid; command surface needs Hermes plugin redesign. |
| P14-018 | Morning Brief Health Section | **DEPENDS-ON-OLD-BOT** | References `src/discord/morning_brief.py` — extends existing Discord module. Uses APScheduler for timing. Core: health data enrichment (valid). Delivery mechanism (Discord module extension + APScheduler) needs Hermes cron + notification plugin redesign. |
| P14-019 | Proactive Health Alerts + Night Owl Behavior | **DEPENDS-ON-OLD-BOT** | **Heaviest Discord dependency in P11-P15.** `HealthAlertDispatcher.__init__(bot_client: discord.Client, ...)`, `discord.utils.get(self._bot.get_all_channels(), ...)`, `discord.Embed`, `channel.send(embed=embed)`, `self._bot.fetch_user(self._faiz_id)`, `user.create_dm()`, `dm.send()`. Integration table: `src/discord/notifications.py`, `src/discord/bot.py`, `#system-health` channel. Alert logic (severity routing, cooldown) is valid but constructor + delivery are entirely discord.py. Needs full Hermes `HealthAlertPlugin` redesign. |
| P14-020 | WAC-001..007 Activation Checklist Implementation | **VALID** | Checklist logic, no Discord |
| P14-021 | Health Data Export + Deletion | **VALID** | Data export, no Discord |
| P14-022 | P14 Health Prometheus Metrics | **VALID** | Monitoring infrastructure, no Discord |
| P14-023 | Grafana Health Dashboard | **VALID** | Dashboard, no Discord |
| P14-024 | Stale Data + Battery Alerts | **VALID** | Alert logic backend, no Discord (may conceptually ref notification channel but no code) |
| P14-025 | Systemd Service | **VALID** | Service definition, no Discord |
| P14-026 | Mock Health Data Generator | **VALID** | Test data generator, no Discord |
| P14-027 | Integration Test + P14 GATE | **VALID** | Integration testing, no Discord |

**P14 Summary:** 22 VALID | 1 NEEDS-UPDATE | 4 DEPENDS-ON-OLD-BOT

---

### P15: Windows Daemon + WebSocket (15 steps)

| Step | Title | Classification | Rationale |
|---|---|---|---|
| P15-001 | Project Scaffold + Base Tracker ABC | **VALID** | Python scaffold, no Discord |
| P15-002 | Active Window Tracker (win32gui + psutil) | **VALID** | Windows API, no Discord |
| P15-003 | Idle Tracker (GetLastInputInfo, graduated) | **VALID** | Windows API, no Discord |
| P15-004 | Git Context Tracker (traversal + project mapping) | **VALID** | Git operations, no Discord |
| P15-005 | Event Pipeline (MessagePack + EventRouter + WS Client) | **VALID** | WebSocket pipeline, no Discord |
| P15-006 | NSSM Service Wrapper + Config | **VALID** | Windows service, no Discord |
| P15-007 | VPS WebSocket Endpoint (FastAPI + ConnectionManager) | **VALID** | FastAPI server, no Discord |
| P15-008 | Command Protocol (ACK-based, Redis DB4 pub/sub) | **VALID** | Redis pub/sub protocol, no Discord |
| P15-009 | Consent Gate Integration (belt-and-suspenders) | **VALID** | Consent enforcement, no Discord |
| P15-010 | Discord `/pc` Command (status + session override) | **DEPENDS-ON-OLD-BOT** | Heavy: `self.tree.command()`, `app_commands.CommandTree`, `tree.sync()`, `discord.Object(id=GUILD_ID)`, `is_faiz_interaction()`, `defer_ephemeral()` + `followup.send(ephemeral=True)`, `register_pc_commands(bot.tree, guild_obj)` in `src/discord/bot.py`. Rollback uses `git checkout HEAD -- src/discord/bot.py`. Metadata references ADR-035 but implementation codes entirely to discord.py. Needs Hermes `PcPlugin` redesign. |
| P15-011 | Observability (Prometheus metrics + Grafana dashboard + alerting) | **NEEDS-UPDATE** | Core: Prometheus metrics, Grafana dashboard (valid). References "Discord channel-based alert routing" and "proactively notify Faiz of disconnections via Discord." Monitoring infrastructure valid; alert routing needs Hermes notification hook mapping. References ADR-035 in metadata (positive) but not in implementation patterns. |
| P15-012 | TimescaleDB Migration (windows_events hypertable) | **VALID** | Database migration, no Discord |
| P15-013 | Test Suite (unit + integration) | **VALID** | Testing, no Discord |
| P15-014 | Integration Test — End-to-End Daemon ↔ VPS | **VALID** | Integration testing, no Discord |
| P15-015 | Deployment + Smoke Test + README | **VALID** | Deployment docs, no Discord |

**P15 Summary:** 13 VALID | 1 NEEDS-UPDATE | 1 DEPENDS-ON-OLD-BOT

---

## Summary Table

| Phase | Name | Steps | VALID | NEEDS-UPDATE | DEPENDS-ON-OLD-BOT | Validity % |
|---|---|---|---|---|---|---|
| **P11** | WhatsApp/Neonize | 23 | 19 | 2 | 2 | 82.6% |
| **P12** | Gmail/Email | 29 | 22 | 5 | 2 | 75.9% |
| **P13** | X Auto Poster | 28 | 22 | 6 | 0 | 78.6% |
| **P14** | Wearable Health | 27 | 22 | 1 | 4 | 81.5% |
| **P15** | Windows Daemon | 15 | 13 | 1 | 1 | 86.7% |
| **TOTAL** | | **122** | **98** | **15** | **9** | **80.3%** |

---

## Per-Phase Detailed Analysis

### P11: WhatsApp/Neonize Integration

**Baileys Reference Audit:** ✅ **0 stale.** All 11 `Baileys` keyword matches are either:
- ADR-022 revision notes ("Requires revision from Baileys/Node.js to Neonize/pure Python" — line 19506, 19520, 19640, 19670)
- `baileys-antiban` npm library as conceptual reference for jitter patterns ("Reference only; not a dependency" — line 23179)
- Error categorization comment ("Neonize/Baileys internal error" — line 24483)
- Evolution API false logout bug reference ("Baileys-based libraries" — line 24664)

**Neonize Orientation:** ✅ All 23 steps reference Neonize v0.3.18, not Baileys. P11-001 explicitly documents the ADR-022 revision requirement.

**bot.py Dependencies:**
- P11-018 (`DiscordMirrorBridge`): Constructed with `GuinevereBot` instance, uses `discord.Embed`, `discord.utils.get`, `bot.get_channel()` — DEPENDS-ON-OLD-BOT
- P11-019 (Notifications + `!wa-status`): References `GuinevereBot`, `commands.Bot`, `command_prefix="!"`, `send_alert()`, `SEV_MATRIX` — DEPENDS-ON-OLD-BOT
- P11-015 (HARD STOP): References `HardStopHandler` in `src/discord/bot.py` but core logic is shared Redis flag — NEEDS-UPDATE
- P11-010 (Command Handler): Mirrors Discord slash commands as equivalence target — NEEDS-UPDATE

---

### P12: Gmail/Email Integration

**API Integration Validity:** ✅ Gmail API client (`google-api-python-client`), OAuth2 token management, GCP Pub/Sub StreamingPull, Resend client — all standard Google APIs, unaffected by Hermes. Zero architecture-level issues.

**Discord Surface:**
- P12-016 (Draft UX): Approval flow coded to `bot.py` command registration — DEPENDS-ON-OLD-BOT
- P12-019 (Morning Briefing): References `register_commands(bot)` in `startup.py` — DEPENDS-ON-OLD-BOT
- P12-020 (`!email-digest`): Text command — NEEDS-UPDATE
- P12-021 (`!email-consent`, `!email-reauth`): Text commands — NEEDS-UPDATE
- P12-018 (Real-Time Notifications): Discord as delivery mechanism — NEEDS-UPDATE

**Backend Health:** 22 of 29 steps are pure backend/infrastructure (GCP, OAuth2, Pub/Sub, sync engine, classifier, scorer, sanitizer, memory, financial bridge) — 75.9% unaffected.

---

### P13: X Auto Poster

**Social Media Integration Validity:** ✅ S3 queue, Obscura CDP posting engine, Gemini captioning, rate limiter, circuit breaker — all backend infrastructure. Zero `twitter-api-v2` or `tweepy` dependency issues. X posting via CDP is transport-agnostic.

**Discord Surface (lightest of the five phases):**
- 6 NEEDS-UPDATE steps, 0 DEPENDS-ON-OLD-BOT
- 9 Discord commands (`/x-status`, `/x-list`, `/x-cancel`, `/x-hold`, `/x-resume`, `/x-edit`, `/x-delete`, `/x-retry`, `/x-dryrun`) referenced abstractly, not coded to `bot.py` patterns
- P13-021 (Post Notification) and P13-027 (Daily Summary) reference Discord as delivery channel conceptually
- All 9 commands can be implemented as a single `XPosterCommandPlugin` with subcommands, minimizing migration effort

---

### P14: Wearable/Xiaomi Watch

**Hardware Integration Validity:** ✅ Gadgetbridge, WebDAV, PostgreSQL health schema, HMAC key provisioning, Mi Fitness fallback, baseline computation, anomaly engine, GHI scoring — all backend health pipeline. Zero hardware dependency issues.

**Discord Surface (HEAVIEST of the five phases):**
- 4 DEPENDS-ON-OLD-BOT steps — most severe Discord coupling
- P14-019 (`HealthAlertDispatcher`): Takes `discord.Client` as constructor parameter, uses `discord.utils.get`, `discord.Embed`, `channel.send`, `fetch_user`, `create_dm`, `dm.send` — structural dependency on discord.py's client model
- P14-016, P14-017: `@tree.command()` + `app_commands.CommandTree` patterns for 4 Discord commands
- P14-018: Extends `src/discord/morning_brief.py` (existing Discord module) + APScheduler
- P14-015: Integration table references `src/discord/notifications.py`, `src/discord/bot.py`

**Redesign Priority:** P14-019 needs the most significant Hermes adaptation — the `HealthAlertDispatcher` must be refactored to emit alert events via a protocol interface, with Discord delivery handled by a separate Hermes notification plugin. This is the only step in P11-P15 that requires architectural redesign, not just surface adaptation.

---

### P15: Windows Daemon

**Service Architecture Validity:** ✅ Windows daemon (Active Window, Idle, Git trackers), WebSocket transport (MessagePack), NSSM service wrapper, VPS FastAPI endpoint, command protocol (Redis pub/sub), consent gate — all backend infrastructure, Discord-independent. Cleanest architecture of the five phases.

**Discord Surface (lightest impact):**
- P15-010 (`/pc` command): Heavy `self.tree.command()` + `app_commands.CommandTree` patterns — DEPENDS-ON-OLD-BOT
- P15-011 (Observability): Core Prometheus/Grafana valid; Discord alert routing needs Hermes notification hook — NEEDS-UPDATE
- **Positive:** P15-011 references ADR-035 in metadata (only step to do so), showing awareness even though implementation patterns haven't been updated

---

## Cross-Phase Findings

### 1. Discord Command Migration Matrix

All P11-P15 Discord commands must be ported from `discord.py` patterns to Hermes plugins:

| Phase | Step | Command(s) | Current Pattern | Hermes Plugin Name | Feasibility |
|---|---|---|---|---|---|
| P11 | P11-010 | WhatsApp `!` commands (mirror Discord) | `commands.Bot` reference | `wa_commands_plugin.py` | MEDIUM |
| P11 | P11-019 | `!wa-status` (text) | `@bot.command()` in `bot.py` | `wa_status_plugin.py` | MEDIUM |
| P12 | P12-019 | `!email-digest` delivery | `register_commands(bot)` | `email_digest_plugin.py` | MEDIUM |
| P12 | P12-020 | `!email-digest` (text) | Discord text command | (merged into above) | MEDIUM |
| P12 | P12-021 | `!email-consent`, `!email-reauth` (text) | Discord text commands | `email_consent_plugin.py` | MEDIUM |
| P13 | P13-022 | `/x-status`, `/x-list`, `/x-cancel`, `/x-hold` | Abstract "Discord controls" | `x_poster_plugin.py` (single plugin, 4 subcommands) | MEDIUM |
| P13 | P13-023 | `/x-edit` | Abstract "Discord controls" | (same plugin) | LOW |
| P13 | P13-024 | `/x-delete` | Abstract "Discord controls" | (same plugin) | LOW |
| P13 | P13-025 | `/x-retry`, `/x-dryrun` | Abstract "Discord controls" | (same plugin) | MEDIUM |
| P14 | P14-016 | `/health-status`, `/ghi-score` | `@tree.command()` | `health_status_plugin.py` | MEDIUM |
| P14 | P14-017 | `/sleep-report`, `/activity-today` | `@tree.command()` | `sleep_report_plugin.py`, `activity_today_plugin.py` | MEDIUM |
| P15 | P15-010 | `/pc status`, `/pc session` | `self.tree.command()` | `pc_plugin.py` | LOW |
| **Total** | **9 steps** | **17 commands** | — | **8-10 plugins** | 5 MEDIUM, 4 LOW |

### 2. Notification Pattern Migration

Every phase has Discord notification patterns:

| Phase | Step | Notification Surface | Current Pattern | Severity | Post-ADR-035 Target |
|---|---|---|---|---|---|
| P11 | P11-019 | WhatsApp connection lifecycle | `send_alert()`, `SEV_MATRIX`, `src/discord/notifications.py` | **DEPENDS-ON-OLD-BOT** | Hermes `on_error` hook (ADR-035 Hook #7) + `WhatsAppNotificationPlugin` |
| P12 | P12-016 | Draft approval UX | `src/discord/bot.py` command registration | **DEPENDS-ON-OLD-BOT** | Hermes `email_approval_plugin.py` |
| P12 | P12-018 | Email notifications | Discord DM/channel | **NEEDS-UPDATE** | Hermes notification plugin |
| P12 | P12-019 | Morning briefing digest | `register_commands(bot)` in `startup.py` | **DEPENDS-ON-OLD-BOT** | Hermes cron + notification plugin |
| P13 | P13-021 | Post success/failure | Discord embed | **NEEDS-UPDATE** | Hermes notification plugin |
| P13 | P13-027 | Daily 20:00 summary | Discord channel | **NEEDS-UPDATE** | Hermes cron + notification plugin |
| P14 | P14-019 | Health alerts (SpO2, HR, GHI, sleep, battery, night owl) | `HealthAlertDispatcher(bot_client: discord.Client)` | **DEPENDS-ON-OLD-BOT** | Hermes `HealthAlertPlugin` — complete redesign needed |
| P14 | P14-015 | Distress escalation routing | `src/discord/notifications.py`, `src/discord/bot.py` | **NEEDS-UPDATE** | Hermes `pre_response`/`on_error` hooks |
| P15 | P15-011 | Daemon disconnection alerts | Discord channel-based alerting | **NEEDS-UPDATE** | Hermes `on_error` hook or monitoring plugin |

### 3. ADR-035 D9 WhatsApp Inconsistency (Confirmed)

| ADR-035 Location | Text | Correct? |
|---|---|---|
| **Line 116** (Architecture Overview) | "ADR-022 mandates Neonize ... rejecting the Baileys/Node.js bridge approach" | ✅ CORRECT |
| **Line 164** (Decision Driver D9) | "Hermes multi-platform gateway natively supports WhatsApp via BAW (Baileys WebSocket)" | ❌ INCORRECT — residual from pre-correction draft |
| **StepPrompts P11** | All 23 steps reference Neonize v0.3.18 | ✅ CORRECT |
| **ADR-022** | Revised 2026-06-03 to mandate Neonize | ✅ CORRECT |

**Recommendation:** Update ADR-035 line 164 to: "Hermes multi-platform gateway supports WhatsApp natively; however, Guinevere uses Neonize (per ADR-022)."

### 4. Steps with Zero Hermes Impact (Backend-Only)

| Phase | Count | Examples |
|---|---|---|
| P11 | 19/23 | Neonize deps, session mgmt, connection handler, adapter, agent core, context mgr, routing, classifier, typing, formatting, media, rate limiter, safe word, whitelist, reconnection, health check, systemd, E2E |
| P12 | 22/29 | GCP project, OAuth2, Resend, Gmail API, sync engine, Pub/Sub, adapter, context, classifier, scorer, sanitizer, secret scanner, memory store, financial bridge, draft gen, draft sync, HARD STOP, classification, watch renewal, Grafana, systemd, E2E, loop trigger, contract |
| P13 | 22/28 | S3 queue, watchdog, Obscura CDP, systemd, polling, sidecar, rate limiter, cookie, session health, recovery, caption, moderation, tone, compose, upload, post, dry-run, retry, circuit breaker, timeout, Grafana, E2E |
| P14 | 22/27 | Device, WebDAV, DB schema, HMAC, parser, ingestion, consent, Mi Fitness, baseline, anomaly, GHI, summary, persona FSM, memory injection, WAC, export, Prometheus, Grafana, stale alerts, systemd, mock data, E2E |
| P15 | 13/15 | Scaffold, Active Window, Idle, Git, event pipeline, NSSM, WS endpoint, command protocol, consent gate, TimescaleDB, test suite, integration test, deployment |

### 5. DEPENDS-ON-OLD-BOT Steps — Redesign Priority

These 9 steps code to specific `discord.py`/`bot.py` patterns and need significant redesign:

| Rank | Step | Phase | Severity | Concern |
|---|---|---|---|---|
| **1** | P14-019 | P14 | 🔴 CRITICAL | `HealthAlertDispatcher(bot_client: discord.Client)` — structural dependency on discord.py's client model. Constructor, channel routing, DM delivery all coded to discord.py. Needs full `HealthAlertPlugin` redesign. |
| **2** | P14-018 | P14 | 🔴 HIGH | Extends `src/discord/morning_brief.py` + APScheduler. Morning brief delivery needs Hermes cron + plugin architecture. |
| **3** | P14-016 | P14 | 🔴 HIGH | `@tree.command()` + `app_commands.CommandTree` for 2 health commands. Registration and delivery deeply tied to discord.py. |
| **4** | P14-017 | P14 | 🔴 HIGH | Same patterns as P14-016 for 2 additional health commands. |
| **5** | P11-018 | P11 | 🟡 MEDIUM | `DiscordMirrorBridge` with `GuinevereBot` constructor — mirror logic valid but bridge delivery is bot.py-specific. |
| **6** | P11-019 | P11 | 🟡 MEDIUM | `!wa-status` command + SEV_MATRIX notification routing — logic valid, delivery is bot.py-specific. |
| **7** | P12-016 | P12 | 🟡 MEDIUM | Draft approval UX — approval flow valid, Discord command registration is bot.py-specific. |
| **8** | P12-019 | P12 | 🟡 MEDIUM | Morning briefing + digest — digest generation valid, `register_commands(bot)` is bot.py-specific. |
| **9** | P15-010 | P15 | 🟡 MEDIUM | `/pc` command with `self.tree.command()` — daemon query logic valid, command registration is bot.py-specific. Metadata references ADR-035 but code doesn't follow it. |

---

## Recommendations

### Before Any P11-P15 Implementation

1. **Do NOT implement DEPENDS-ON-OLD-BOT steps as-written.** Steps P14-016, P14-017, P14-018, P14-019, P11-018, P11-019, P12-016, P12-019, and P15-010 will create dead-end code incompatible with the post-Hermes architecture. Wait for ADR-035 Phase 2 (Discord Gateway migration) to establish Hermes plugin patterns before implementing these.

2. **Backend steps (98 of 122) can be implemented NOW.** WhatsApp adapter, Gmail pipeline, X poster engine, wearable health pipeline, and Windows daemon are all transport-agnostic. Implementing them before Hermes migration produces zero rework.

3. **NEEDS-UPDATE steps (15 of 122) should wait for Hermes plugin patterns** but require minimal redesign. A single `stepprompts/HERMES-MIGRATION-ADDENDUM.md` can document the plugin mapping for all 15 steps without rewriting individual step specs.

4. **Resolve ADR-035 D9 inconsistency** — line 164 "BAW (Baileys WebSocket)" conflicts with line 116 and ADR-022. Update D9 to reference Neonize.

5. **Design Hermes notification architecture for non-safety events.** ADR-035 establishes 7 hooks for safety enforcement but does not specify how non-safety notifications (health alerts, WhatsApp status, Gmail digest, X poster results) are routed. P11-P15 notification steps need explicit Hermes notification design before implementation.

### Recommended Implementation Sequence

1. **P15 first** (1 DEPENDS-ON-OLD-BOT) — Windows daemon is Discord-independent. Only P15-010 needs Hermes plugin.
2. **P13 second** (0 DEPENDS-ON-OLD-BOT) — Lightest Discord surface. All 9 `/x-*` commands can be one `XPosterCommandPlugin`.
3. **P11 third** (2 DEPENDS-ON-OLD-BOT) — WhatsApp adapter itself is Hermes-independent. Bridge and notifications need design.
4. **P12 fourth** (2 DEPENDS-ON-OLD-BOT) — Gmail pipeline is large but Discord surface is small.
5. **P14 last** (4 DEPENDS-ON-OLD-BOT) — Heaviest Discord surface. P14-019 needs the most significant architectural redesign.

---

## Footer

| Field | Value |
|---|---|
| **Audit type** | Static specification analysis (no code execution) |
| **Classification system** | VALID / NEEDS-UPDATE / DEPENDS-ON-OLD-BOT |
| **Methods** | Read + grep of StepPrompts.md (5 phase ranges, lines 19492-57358), ADR-035 cross-reference, ADR-022 verification, spot-check of 3 key steps (P11-018, P14-019, P15-010) |
| **Tools used** | `read` (offset/limit chunks), `grep` (Baileys, Phase patterns, Step patterns), `filesystem_write_file` |
| **Data sources** | `stepprompts/StepPrompts.md` (lines 19492-57358), `adr/ADR-035-hermes-migration.md`, `adr/ADR-022-communication-channel-strategy.md` |
| **Files modified** | None (audit report only) |
| **Pre-existing issues found** | 0 (no implementation code exists for P11-P15) |
| **Baileys stale references** | 0 (all 11 matches are informational/correct) |
| **ADR-035 discrepancies** | 1 (D9 line 164 BAW vs line 116 Neonize) |
| **Related audits** | MASTER-AUDIT-REPORT.md (synthesis), P0-P10 phase audits |
| **Supersedes** | Previous P11-P15-audit.md (2026-06-04) |