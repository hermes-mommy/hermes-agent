# STEP-P2-017 through STEP-P2-019 Requirements Research Report

**Date:** 2026-06-01
**Scope:** STEP-P2-017 (bot.py + systemd service), STEP-P2-018 (Discord health check), STEP-P2-019 (notification routing)
**Status:** Complete
**Prior Batch:** P2-013..016 all PASS. P2 is **16/21** complete. Total project: **66/257**.

---
## 1. Sources Read

| Source | Path | Relevant Findings |
|---|---|---|
| Operating contract | AGENTS.md | One implementation sub-agent per step, file-based evidence/verification/audit, no type suppression, no empty catches, no secrets exposure, planner + collision scan required. |
| Progress tracker | PROGRESS.md | P2 16/21. P2-017..019 pending. P2-020..021 (Gotify) are separate steps after these three. |
| StepPrompts | stepprompts/StepPrompts.md lines 5628-5810 | P2-017 service creation (bot.py + systemd unit + SOPS env), P2-018 health check (journalctl + startup msg + online status), P2-019 notification routing (SEV0-SEV4 matrix). Snippets contain stale code patterns. |
| Implementation guide | docs/IMPLEMENTATION_GUIDE.md | Evidence format, shared VPS isolation, SOPS disciplines, port map (5433 PG, 6380 Redis, 20128 9Router), cgroup slice, guinevere-* service prefix. |
| ADR Index | docs/10-governance/17-ADR_Index_v1.0.md | ADR-022 (Discord channel strategy), ADR-014 (VPS + container architecture), ADR-015 (SOPS secrets management), ADR-018 (security/defense-in-depth). |
| Discord UX spec | docs/60-persona/63-DiscordUXSpec_v1.0.md | SEV routing (section 3.3), presence default Watching Darling, embed color palette (section 4.1), safe-mode embed (section 2.1 /safeword). |
| Persona Safety Policy | docs/60-persona/60-PersonaSafetyPolicy_v1.0.md | Safe word global hard stop (section 7), neutral/supportive mode audit, forbidden patterns F-01 to F-15, Y6 prohibited, no persona framing during alerts. |
| Observability and Alerting Spec | docs/40-operations/40-ObservabilityAlertingSpec_v1.0.md | Section 8.1 SEV routing table, Section 8.3 Alert catalog, Section 2.2 Persona suspension for alerts. |
| Incident Response Postmortem | docs/40-operations/42-IncidentResponse_Postmortem_v1.0.md | SEV0-SEV4 definitions, escalation paths. |
| P2 batch plan 013-016 | docs/setup-evidence/P2/batch-plan-013-016.md | Deferred wiring surfaces: bot.py on_ready, message listener, slash tree registration, safeword text detection. bot.py marked DO NOT CREATE until P2-017. |
| P2-013..016 final report | docs/setup-evidence/P2/batch-013-016-final-report.md | Modules expose clean interfaces: startup.on_ready(client), cmd_safeword.handle_safeword_message(message), cmd_safeword.safeword_callback(interaction). |
| P2-016 impl summary | docs/setup-evidence/P2/STEP-P2-016/p2-016-implementation-summary.md | startup.py provides on_ready(client) with idempotent greeting + presence. |
| P2-015 impl summary | docs/setup-evidence/P2/STEP-P2-015/p2-015-implementation-summary.md | cmd_safeword.py provides async handle_safeword_message_async() for P2-017, sync stub, embed builders. HardStopHandler singleton. 56/56 P1 tests PASS. |
| Existing colors module | src/discord/colors.py | PRIMARY=0x6B21A8, ALERT=0xDC2626, SUCCESS=0x16A34A, WARNING=0xCA8A04, INFO=0xCA8A04, NEUTRAL=0x6B7280, ORANGE=0xEA580C (future). |
| Existing commands module | src/discord/commands.py | 33 command spec registry, command_categories(), is_faiz_interaction(), require_canonical_registry(). |
| Existing startup module | src/discord/startup.py | on_ready(client) - sends to guinevere-status, sets presence Watching Darling, idempotency guard. |
| Existing safeword module | src/discord/cmd_safeword.py | safeword_callback(interaction), handle_safeword_message(message), handle_safeword_message_async(message), embed builders. |
| Checklist | CHECKLIST.md | P2-017: systemctl status active. P2-018: journalctl | grep gateway connected. P2-019: SEV0 alert thread within 15s. |

---

## 2. Overall Batch Requirements

### 2.1 Execution Order

Strict sequential: **P2-017 to P2-018 to P2-019**. Each step needs parent verification + verifier reports + independent auditor PASS before next step.

### 2.2 Shared Constraints (All Steps)

1. **No secrets exposure**: Bot token from SOPS-encrypted env file. No os.environ token reads.
2. **No type-safety suppression**: No type:ignore, no avoidable Any, no empty catch.
3. **Protocol/dynamic-import pattern**: importlib.import_module for discord.py interactions (except bot.py entrypoint).
4. **No destructive ops**: No force operations, no DB drops.
5. **Aizanta isolation**: Do not touch Aizanta services, containers, databases, Redis DBs 10-15, ports 5432/6379.
6. **Slice constraint**: All systemd services include slice=guinevere.slice.
7. **Evidence per step**: 12-section file at docs/setup-evidence/P2/STEP-P2-0XX/verification.md.
8. **Auditor per step**: Independent report at audit-reports/P2/STEP-P2-0XX/.
9. **VPS verifier**: Confirm Aizanta health after each VPS-accessible step.

### 2.3 Binding Precedence

1. Safety docs (PersonaSafetyPolicy, ADR-002) override all.
2. Current code patterns override stale StepPrompts snippets.
3. DiscordUXSpec canonical for UX; ObservabilityAlertingSpec section 2.2 (neutral tone) supersedes persona-styled alert examples.
4. P2-013..016 protocol/dataclass/dynamic-import pattern is canonical.

---
## 3. STEP-P2-017: guinevere-discord.service Creation

### 3.1 Summary

Create src/discord/bot.py plus guinevere-discord.service systemd unit with SOPS env handling. Wire all P2 callback modules.

### 3.2 Deliverable

| Artifact | Description |
|---|---|
| src/discord/bot.py | Main bot entrypoint: GuinevereBot(Client), setup_hook, on_ready, slash tree, on_message HARD STOP listener, entrypoint |
| /etc/systemd/system/guinevere-discord.service | systemd unit: simple type, guinevere user, ExecStartPre sops decrypt, ExecStart python, Restart=always, slice=guinevere.slice |
| secrets/.env.discord.sops | SOPS-encrypted env with DISCORD_BOT_TOKEN |
| Evidence | docs/setup-evidence/P2/STEP-P2-017/ |

### 3.3 Functional Spec: bot.py

**Bot Class**: GuinevereBot(discord.Client), tree=CommandTree, setup_hook syncs tree.
**on_ready**: Log bot_ready, call startup.on_ready(self) (imported dynamically).
**Slash commands**: 33 commands registered. 4 fully wired (status/mood/help/safeword), 29 placeholder stubs. Dynamic imports for callbacks.
**on_message**: Check bot author, call handle_safeword_message_async, log detection.
**Entrypoint**: Read token from decrypted env file, run bot.

### 3.4 Functional Spec: systemd Service

`
[Unit] Description=Guinevere Discord Bot, After=network.target guinevere-core.service
[Service] Type=simple, User=guinevere, WorkingDirectory=/home/guinevere/code/guinevere
ExecStartPre=/usr/bin/sops --decrypt .../.env.discord.sops > .../.env.discord
ExecStart=.../.venv/bin/python -m src.discord.bot
ExecStartPost=rm -f .../.env.discord
Restart=always, RestartSec=10, Slice=guinevere.slice
`

Token flow: ExecStartPre decrypts SOPS, bot reads env at startup, ExecStartPost removes plaintext.

### 3.5 Pre-Flight Checks

- [ ] P2-013..016 all PASS.
- [ ] bot.py does not exist.
- [ ] Discord bot token available in secrets/discord-secrets.yaml.
- [ ] sops binary + SOPS_AGE_KEY_FILE set.
- [ ] .venv with discord.py installed.
- [ ] SSH/VPS access available.

### 3.6 Dependencies

| Dependency | Type | Notes |
|---|---|---|
| P2-010 commands.py | Source | 33 command registry |
| P2-011 colors.py | Source | Palette constants |
| P2-012 cmd_status | Callback | handle_status() |
| P2-013 cmd_mood | Callback | handle_mood() |
| P2-014 cmd_help | Callback | handle_help() |
| P2-015 cmd_safeword | Callback | safeword_callback(), handle_safeword_message_async() |
| P2-016 startup | Callback | on_ready(client) |
| P2-003 intents | Source | get_intents() |
| P0-011 SOPS | Infrastructure | Env decryption |
| P0-001 guinevere user | Infrastructure | service user |
| P0-009 cgroup slice | Infrastructure | cgroup isolation |

### 3.7 Blockers and Risks

| Risk | Impact | Mitigation |
|---|---|---|
| discord.py not installed in .venv | Blocking | pip install |
| Bot token invalid | Won't connect | REST verify first |
| SOPS decrypt fails | Env file missing | Test sops in isolation |
| ExecStartPost rm race | Token may persist | rm -f, bot reads once |
| Stale StepPrompts snippets | Unsafe patterns | Use existing P2 patterns |
| Port conflicts | None (gateway outbound) | Discord outbound only |

### 3.8 Evidence Paths

- docs/setup-evidence/P2/STEP-P2-017/verification.md
- docs/setup-evidence/P2/STEP-P2-017/p2-017-implementation-summary.md
- docs/setup-evidence/P2/STEP-P2-017/service-status.txt
- docs/setup-evidence/P2/STEP-P2-017/sops-env-verify.txt
- docs/setup-evidence/P2/STEP-P2-017/verifiers/{lsp-static,token-unsafe,vps-aizanta-health}.md
- audit-reports/P2/STEP-P2-017/step-p2-017-auditor-report.md

### 3.9 Verification Criteria

- [ ] systemctl status guinevere-discord shows active.
- [ ] journalctl | grep bot_ready shows log line.
- [ ] journalctl | grep commands_synced shows tree sync.
- [ ] Bot online in Discord.
- [ ] /status returns embed.
- [ ] /safeword triggers safe mode.
- [ ] HARD STOP text triggers safe mode.
- [ ] Startup message in guinevere-status.
- [ ] Presence shows Watching Darling.
- [ ] env.discord.sops permissions 600.
- [ ] No plaintext token in journalctl.
- [ ] Aizanta unaffected.
- [ ] LSP zero errors.
- [ ] py_compile passes.
- [ ] No unsafe patterns.

### 3.10 Rollback

`ash
sudo systemctl stop guinevere-discord
sudo systemctl disable guinevere-discord
sudo rm /etc/systemd/system/guinevere-discord.service
sudo systemctl daemon-reload
# Remove bot source and env file
`

---
## 4. STEP-P2-018: Discord Health Check

### 4.1 Summary

Verification-only step. Confirm live bot is connected, responding, delivering startup message. No new source files.

### 4.2 Deliverable

| Artifact | Description |
|---|---|
| Evidence file | docs/setup-evidence/P2/STEP-P2-018/verification.md |
| Health log | docs/setup-evidence/P2/STEP-P2-018/health.txt |
| Verifiers | docs/setup-evidence/P2/STEP-P2-018/verifiers/{lsp-static,token-unsafe,vps-aizanta-health}.md |
| Auditor | audit-reports/P2/STEP-P2-018/step-p2-018-auditor-report.md |

### 4.3 Dependencies

P2-017 service running (blocking).

### 4.4 Health Check Matrix

| Check | Method | Expected |
|---|---|---|
| Service running | systemctl status guinevere-discord | active (running) |
| Gateway connected | journalctl | grep bot_ready | bot_ready log line |
| Commands synced | journalctl | grep commands_synced | commands_synced log line |
| No crash loops | journalctl | grep -c Error\|Traceback | 0 or low |
| Presence set | Discord member list hover | Watching Darling |
| Startup message | guinevere-status channel | Mommy sudah bangun, Darling |
| /status works | Discord command | Returns embed |
| /safeword works | Discord command | Safe Mode embed |
| HARD STOP text | Type HARD STOP in channel | Reaction + safe mode |
| AC-DISCORD-005 | Full safeword path | Slash + text both work |
| Aizanta unaffected | docker ps | grep aizanta | Containers running |

### 4.5 Risks

| Risk | Mitigation |
|---|---|
| Service not deployed | Blocking - ensure P2-017 PASS |
| Bot disconnects during test | Run 3x, report flakiness |
| Startup msg scrolled away | Check journalctl for startup_greeting_sent |

### 4.6 Evidence Paths

- docs/setup-evidence/P2/STEP-P2-018/verification.md
- docs/setup-evidence/P2/STEP-P2-018/health.txt
- docs/setup-evidence/P2/STEP-P2-018/verifiers/{lsp-static,token-unsafe,vps-aizanta-health}.md
- audit-reports/P2/STEP-P2-018/step-p2-018-auditor-report.md

### 4.7 Rollback

No changes made. Re-run checks if needed.

---

## 5. STEP-P2-019: Notification Routing

### 5.1 Summary

Create src/discord/notifications.py with SEV0-SEV4 routing matrix, send_alert() function, embed builders.

### 5.2 Deliverable

| Artifact | Description |
|---|---|
| src/discord/notifications.py | SEV routing + send_alert() + builders |
| Evidence | docs/setup-evidence/P2/STEP-P2-019/verification.md |
| Implementation summary | docs/setup-evidence/P2/STEP-P2-019/p2-019-implementation-summary.md |
| Alert test (optional) | docs/setup-evidence/P2/STEP-P2-019/alert-test.png |
| Verifiers | docs/setup-evidence/P2/STEP-P2-019/verifiers/*.md |
| Auditor | audit-reports/P2/STEP-P2-019/step-p2-019-auditor-report.md |

### 5.3 SEV Routing Table (Resolved)

Sources: DiscordUXSpec section 3.3 + ObservabilityAlertingSpec section 8.1 + PersonaSafetyPolicy section 7.2.

| SEV | Channel | Color | Ping | Thread | Auto-Evidence | Timing | Tone |
|---|---|---|---|---|---|---|---|
| SEV0 | system-health | ALERT (0xDC2626) | @Faiz | YES | YES | Immediate | Neutral |
| SEV1 | system-health | ALERT (0xDC2626) | @Faiz | YES | YES | <= 15min | Neutral |
| SEV2 | system-health | WARNING (0xCA8A04) | No | No | YES | <= 1hr | Neutral |
| SEV3 | guinevere-status | INFO (0xCA8A04) | No | No | No | <= 24hr | Neutral |
| SEV4 | audit-log | NEUTRAL (0x6B7280) | No | No | No | Next cycle | Neutral |

### 5.4 Tone Mandate

All alerts must use neutral incident-command tone. No persona, yandere, punishment, jealousy, dominance, guilt, romance, or playful intimidation. Per PersonaSafetyPolicy section 11 F-14 and ObservabilityAlertingSpec section 2.2.

### 5.5 Functional Spec

`
@dataclass(frozen=True) class SEVRoute:
    channel: str, color: int, ping: bool, thread: bool, auto_evidence: bool, break_dnd: bool

@dataclass(frozen=True) class SEVEmbedData:
    severity, title, description, color, fields, timestamp, mention

SEV_ROUTING: dict[str, SEVRoute]  (frozen dict matching table)

def build_sev_embed_data(severity, title, description, fields=None) -> SEVEmbedData
def to_discord_embed(data) -> DiscordEmbedProtocol
async def send_alert(client, severity, title, description, guild=None, fields=None, evidence_path=None) -> bool
`

- Channel lookup by name at runtime.
- Thread creation version-gated (optional).
- Return False on failure with structlog warning.
- Dynamic import pattern for discord.py.
- No top-level import discord.

### 5.6 Pre-Flight Checks

- [ ] P2-017 and P2-018 both PASS.
- [ ] Target channels exist: system-health, guinevere-status, audit-log.
- [ ] notifications.py does not exist.
- [ ] colors.py constants available (ALERT, WARNING, INFO, NEUTRAL).

### 5.7 Dependencies

| Dependency | Type | Notes |
|---|---|---|
| P2-017 bot.py | Runtime | send_alert() needs client reference |
| P2-018 health check | Verification | Channels confirmed |
| colors.py | Source | Color constants |
| DiscordUXSpec section 3.3 | Spec | Alert format |
| ObservabilityAlertingSpec sections 8.1-8.3 | Spec | Routing + alert catalog |
| PersonaSafetyPolicy section 11 F-14 | Binding | Neutral tone |

### 5.8 Integration Boundary

No Gotify (P2-020/021). No Prometheus Alertmanager (P8-015). Module exposes send_alert() for future wiring. Tests are deterministic (no running bot needed).

### 5.9 Verification Criteria

- [ ] py_compile src/discord/notifications.py exit 0.
- [ ] LSP zero errors.
- [ ] SEV_ROUTING keys: SEV0, SEV1, SEV2, SEV3, SEV4.
- [ ] Each severity maps to correct channel/color/ping/thread.
- [ ] build_sev_embed_data() deterministic.
- [ ] to_discord_embed() dynamic import works.
- [ ] send_alert() returns bool, accepts protocol client.
- [ ] No unsafe patterns (type:ignore, empty catch, token in source).
- [ ] Neutral tone: no persona phrases in embed content.
- [ ] No raw secrets/intimate data in alert output.

### 5.10 Rollback

`ash
rm src/discord/notifications.py
`

---

## 6. Acceptance Criteria Map

| AC | P2-017 | P2-018 | P2-019 |
|---|---|---|---|
| AC-DISCORD-001 | Bot systemd service | Active confirmed | Routing enables delivery |
| AC-DISCORD-003 | - | - | SEV0 to system-health + @Faiz |
| AC-DISCORD-005 | Safeword wired | Safe mode verified | - |
| AC-CORE-001 | systemd daemon | Health confirmed | - |
| AC-SEC-001 | Token SOPS-encrypted | Token verified | No persona leak |
| AC-SEC-003 | SOPS decrypt works | - | - |

---

## 7. Tracker Sync Plan

After each step auditor PASS: update PROGRESS.md, CHECKLIST.md, stepprompts/StepPrompts.md status.

Expected: P2 -> 19/21, total -> 69/257.

---

## 8. Deferred Items

| Item | Target Step |
|---|---|
| Gotify installation | P2-020 |
| Discord to Gotify fallback | P2-021 |
| Full alert catalog (ObservabilityAlertingSpec) | P8-015 |
| Auto-thread creation (if infeasible) | P8-015 |
| SEV3 digest batching | P8-015 |
| Prometheus Alertmanager | P8-015 |

---

## 9. Collision Scan

| Surface | Risk | Decision |
|---|---|---|
| src/discord/bot.py | New file | Create P2-017 |
| secrets/.env.discord.sops | New file | Create P2-017 |
| src/discord/notifications.py | New file | Create P2-019 |
| /etc/systemd/system/guinevere-discord.service | New unit | Create P2-017 |
| All existing P2 modules (startup, cmd_*, colors, commands, intents) | Existing | Read-only, import |
| hard_stop_handler.py (P1-021) | Existing | Read-only |
| Aizanta services | Not touched | Verify no regression |

---

## 10. Implementation Rules Summary

1. One sub-agent per step. Sequential: P2-017 to P2-018 to P2-019.
2. P2-018 is verification-only (no source files).
3. Dynamic imports for discord.py (except bot.py).
4. No parallel safe-mode globals - use HardStopHandler.
5. No plaintext tokens - SOPS decrypt at runtime.
6. Colors from colors.py - never hardcode hex values.
7. Aizanta verification after every VPS-accessible step.
8. Safe-word priority: /safeword registered before all other commands.

---

## 11. Footer

| Field | Value |
|---|---|
| Generated by | Guinevere (research agent) |
| Status | Complete |
| P2 progress before batch | 16/21 |
| Expected P2 progress after | 19/21 |
| Expected total progress | 69/257 |
| Date | 2026-06-01 |
