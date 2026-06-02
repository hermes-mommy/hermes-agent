# P2 Batch Plan 017–019 — Bot Integration, Health Check, Notification Routing

**Date:** 2026-06-01
**Status:** Planner Gate — Awaiting Parent Read
**Prior Batch:** P2-013..016 all PASS. P2 = 16/21. Project = 66/257.

---

## 1. Research Inputs (All Read by Parent)

| # | Report | Scope |
|---|---|---|
| R1 | `research/step-prompts-017-019.md` | Requirements, deliverables, evidence paths, binding decisions |
| R2 | `research/safety-runtime-wiring-p2-017.md` | HARD STOP on_message wiring order, AC-SAFE-001 preservation |
| R3 | `research/discordpy-bot-architecture-p2-017-019.md` | commands.Bot anatomy, flat registration, lifecycle, pitfalls |
| R4 | `research/systemd-service-p2-017.md` | systemd unit template, SOPS ExecStartPre, hardening |
| R5 | `research/health-routing-p2-018-019.md` | is_ready()/latency patterns, channel routing by name, fail-soft |
| R6 | `research/local-command-callbacks-p2-017.md` | Exact callback signatures, builder APIs, Faiz guards |
| R7 | `research/local-startup-intents-p2-017.md` | on_ready() API, intents, channel lookup, permissions |
| R8 | `research/local-service-scripts-p2-017-018.md` | SOPS token pattern, systemd style, health scripts |

---

## 2. Binding Decisions

| # | Decision | Basis |
|---|---|---|
| D1 | Use `commands.Bot` (not `discord.Client`) | R3 §1 — slash tree auto-created, text commands supported, official recommendation |
| D2 | Flat registration — no Cogs | R3 §6 — simpler for 4 wired + 29 stub commands; Cogs tradeoff deferred |
| D3 | `@bot.listen('on_message')` for HARD STOP guard | R2 §2.3 — listeners fire BEFORE main on_message; prevents command processing bypass |
| D4 | HARD STOP guard is Message 1, pre-everything | R2 §2.1 — AC-SAFE-001 non-negotiable; guard block returns early before process_commands |
| D5 | Bot reads token from env var set by systemd ExecStartPre | R4 §1, R8 §2.1 — canonical SOPS pattern; ExecStartPost cleans plaintext |
| D6 | Channel lookup by name (`guinevere-status`, etc.) | R5 §2, R7 §2.3 — no hardcoded channel IDs in bot.py |
| D7 | Notification routing neutral tone | R1 §2.3 — ObservabilityAlertingSpec §2.2: persona suspended during alerts |
| D8 | Sequential execution: P2-017 → P2-018 → P2-019 | P2-018 depends on bot running; P2-019 needs online bot for channel routing |
| D9 | Protocol/dataclass/dynamic-importlib pattern canonical | R1 §2.3 — match P2-013..016 style |
| D10 | VPS-only steps (systemd, token, gateway) — local prep + evidence staging | Cannot run bot.py locally (no Discord token in Windows); evidence staged for VPS deploy |

---

## 3. Dependency Map

```
P2-017 (bot.py + systemd)
├── P2-010 commands.py ── 33 command spec registry
├── P2-011 colors.py ── palette constants
├── P2-012 cmd_status.py ── status_callback()
├── P2-013 cmd_mood.py ── mood_callback()
├── P2-014 cmd_help.py ── help_callback()
├── P2-015 cmd_safeword.py ── safeword_callback(), handle_safeword_message_async()
├── P2-016 startup.py ── on_ready(client)
├── P2-003 intents.py ── get_intents()
├── P0-011 SOPS ── secrets decryption
├── P0-001 guinevere user ── service user
└── P0-009 cgroup slice ── isolation

P2-018 (health check)
└── P2-017 complete ── bot must be running

P2-019 (notification routing)
└── P2-017 complete ── bot must be online for channel.send()
```

---

## 4. Parallelism Decision

**Strictly sequential.** P2-018 is verification-only on running bot after P2-017. P2-019 sends to live Discord channels requiring P2-017.

No parallel implementation within this batch.

---

## 5. Master Todo

| # | Step | Scope | Status |
|---|---|---|---|
| T1 | P2-017 | Create bot.py + systemd unit + SOPS env wiring | pending |
| T2 | P2-018 | Discord health verification (no new code) | pending |
| T3 | P2-019 | Create notifications.py SEV routing | pending |
| T4 | Sync | Update PROGRESS.md, CHECKLIST.md | pending |
| T5 | Report | Final batch report | pending |

---

## 6. Collision Scan

| Collision Type | Files | Risk | Mitigation |
|---|---|---|---|
| bot.py creation | `src/discord/bot.py` | First write — no collision | Safe |
| systemd unit | `/etc/systemd/system/guinevere-discord.service` | First write | Safe |
| SOPS env | `secrets/.env.discord.sops` | New file | Safe |
| notifications.py | `src/discord/notifications.py` | First write | Safe |
| PROGRESS.md update | PROGRESS.md shared | Collision with other branches | Parent-only edit after all steps |
| CHECKLIST.md update | CHECKLIST.md shared | Collision with other branches | Parent-only edit after all steps |

**Verdict: No collisions.** All writes are net-new files. Shared docs edited only by parent at batch end.

---

## 7. STEP-P2-017 — bot.py + systemd Service

### 7.1 Safety Classification

**Safety-critical.** Touches AC-SAFE-001 via `on_message` HARD STOP guard. Any guard misordering = SEV0/SEV1.

### 7.2 Deliverable

| Artifact | Path | Description |
|---|---|---|
| bot.py | `src/discord/bot.py` | Main entrypoint: GuinevereBot(commands.Bot), setup_hook, on_ready, slash tree, on_message guard |
| systemd unit | Evidence: unit file text in evidence | `guinevere-discord.service` — Type=simple, User=guinevere, ExecStartPre sops decrypt |
| SOPS env | `secrets/.env.discord.sops` | Encrypted env with DISCORD_BOT_TOKEN |
| Tests | `tests/discord/test_bot.py` | Deterministic: class instantiation, command registration count, handler imports |
| Evidence | `docs/setup-evidence/P2/STEP-P2-017/verification.md` | 12-section evidence |
| Summary | `docs/setup-evidence/P2/STEP-P2-017/p2-017-implementation-summary.md` | Implementation narrative |

### 7.3 Functional Spec: bot.py

```
class GuinevereBot(commands.Bot):
    __init__: intents from get_intents(), command_prefix="!", tree=app_commands.CommandTree
    
    setup_hook:
        - Register 4 wired slash commands: status, mood, help, safeword
        - Register 29 placeholder stubs (remaining categories)
        - Guild-scoped sync (single guild: TARGET_GUILD)
        - Log commands_synced with count
    
    on_ready:
        - Log bot_ready (user, guild count, latency)
        - Call startup.on_ready(self)
    
    on_message guard (@bot.listen('on_message')):
        - Skip if author is bot (including self)
        - Call handle_safeword_message_async(message)
        - If True: return (consumed — block further processing)
        - If in safe mode + non-recovery: return (block non-recovery messages)
    
    main on_message:
        - Call on_message guard result (listener returns don't block main event)
        - Check handler._handler.is_safe before process_commands
        - await bot.process_commands(message) only if not in safe mode
    
    Entrypoint (main/__main__):
        - Read DISCORD_BOT_TOKEN from os.environ
        - Run bot.start(token)
```

### 7.4 Functional Spec: systemd Unit

```
[Unit]
Description=Guinevere Discord Bot
After=network-online.target guinevere-core.service
Wants=network-online.target

[Service]
Type=simple
User=guinevere
Group=guinevere
WorkingDirectory=/home/guinevere/code/guinevere

ExecStartPre=/usr/bin/sops --decrypt --input-type dotenv --output-type dotenv \
  /home/guinevere/code/guinevere/secrets/.env.discord.sops \
  > /run/guinevere/discord.env
ExecStartPre=/usr/bin/chmod 600 /run/guinevere/discord.env

EnvironmentFile=/run/guinevere/discord.env
Environment=PYTHONUNBUFFERED=1

ExecStart=/home/guinevere/code/guinevere/.venv/bin/python -m src.discord.bot

ExecStopPost=/usr/bin/rm -f /run/guinevere/discord.env

Restart=on-failure
RestartSec=10
StartLimitIntervalSec=300
StartLimitBurst=5

KillSignal=SIGTERM
TimeoutStopSec=30

StandardOutput=journal
StandardError=journal

NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/home/guinevere/code/guinevere /var/lib/guinevere
Slice=guinevere.slice

[Install]
WantedBy=multi-user.target
```

### 7.5 Validation

- [ ] LSP zero errors on bot.py
- [ ] py_compile bot.py exit 0
- [ ] Deterministic tests: class instantiation, command count, handler imports
- [ ] 4 callback modules import without error
- [ ] on_message guard skips bot messages
- [ ] handle_safeword_message_async wired as @bot.listen
- [ ] startup.on_ready called in on_ready
- [ ] Token read from DISCORD_BOT_TOKEN env var only
- [ ] No hardcoded TOKEN string, no os.environ.get with default
- [ ] No unsafe patterns (type ignore, empty catch, avoidable Any)
- [ ] systemd unit syntax valid (systemd-analyze verify)
- [ ] 56/56 hard_stop_handler tests still PASS
- [ ] Aizanta unaffected
- [ ] ExecStartPost removes plaintext env

### 7.6 Rollback

```bash
sudo systemctl stop guinevere-discord
sudo systemctl disable guinevere-discord
sudo rm /etc/systemd/system/guinevere-discord.service
sudo systemctl daemon-reload
rm src/discord/bot.py
rm tests/discord/test_bot.py
```

---

## 8. STEP-P2-018 — Discord Health Verification

### 8.1 Summary

Verification-only. No new source files. Confirm live bot is connected, responding, delivering startup message, slash commands work.

### 8.2 Deliverable

| Artifact | Path |
|---|---|
| Evidence | `docs/setup-evidence/P2/STEP-P2-018/verification.md` |
| Verifier reports | `docs/setup-evidence/P2/STEP-P2-018/verifiers/*.md` |
| Auditor report | `audit-reports/P2/STEP-P2-018/step-p2-018-auditor-report.md` |

### 8.3 Verification Checks

- [ ] `systemctl status guinevere-discord` shows active (running)
- [ ] `journalctl -u guinevere-discord -n 20` shows bot_ready log
- [ ] `journalctl -u guinevere-discord | grep commands_synced` shows tree sync
- [ ] Bot appears online in Discord
- [ ] `/status` returns embed in #guinevere-chat
- [ ] `/mood` returns embed
- [ ] `/help` returns embed with 33 commands
- [ ] `/safeword` triggers safe mode embed
- [ ] "HARD STOP" text in #guinevere-chat triggers safe mode
- [ ] Startup message "Mommy sudah bangun, Darling." in #guinevere-status
- [ ] Presence shows "Watching Darling"
- [ ] No plaintext token in journalctl output

### 8.4 Auditor Surface

- [ ] All 12 verification checks confirm
- [ ] Gateway connection stable (no reconnect loops in journal)
- [ ] No crash/error logs after startup
- [ ] Aizanta unaffected (docker ps, ss -tlnp)

---

## 9. STEP-P2-019 — Notification Routing

### 9.1 Summary

Create `src/discord/notifications.py` implementing SEV0-SEV4 routing matrix to Discord channels. Neutral tone (persona suspended per ObservabilityAlertingSpec §2.2).

### 9.2 Deliverable

| Artifact | Path |
|---|---|
| Source | `src/discord/notifications.py` |
| Tests | `tests/discord/test_notifications.py` |
| Evidence | `docs/setup-evidence/P2/STEP-P2-019/verification.md` |
| Summary | `docs/setup-evidence/P2/STEP-P2-019/p2-019-implementation-summary.md` |

### 9.3 SEV Routing Matrix

| SEV | Channel | Color | Tone | Extras |
|---|---|---|---|---|
| SEV0 | `#system-health` | ALERT (#DC2626) | Urgent, neutral, no persona | Ping @Faiz, create thread |
| SEV1 | `#system-health` | WARNING (#CA8A04) | Alert, neutral | No ping |
| SEV2 | `#cost-tracker` | WARNING (#CA8A04) | Informational | Budget detail |
| SEV3 | `#guinevere-status` | PRIMARY (#6B21A8) | Status update | —
| SEV4 | `#audit-log` | NEUTRAL (#6B7280) | Audit record | Timestamp only |

### 9.4 API Surface

- `async def send_alert(bot, sev: str, title: str, description: str, **kwargs) -> bool`
- `async def send_to_channel(bot, channel_name: str, embed_data: ...) -> bool`
- Channel lookup by name via `discord.utils.get(bot.get_all_channels(), name=...)`
- Fail-soft: try/except + logger.error, return False on failure

### 9.5 Validation

- [ ] LSP zero errors
- [ ] py_compile exit 0
- [ ] Routed message embed color matches SEV
- [ ] Channel lookup by name works
- [ ] Missing channel → logger.error, does not crash
- [ ] No @everyone, no ping-except-SEV0
- [ ] Neutral tone: no "Mommy", "Darling", punishment, yandere, surveillance language
- [ ] No unsafe patterns

---

## 10. Delegation Assignments

| Step | Agent Type | Scope | Must Not Touch |
|---|---|---|---|
| P2-017 | `deep` | bot.py + systemd unit + tests + evidence summary | P2-018/019 files, trackers, existing cmd_* modules |
| P2-018 | Parent + verifiers | Verification only — no code | bot.py modifications, trackers |
| P2-019 | `deep` | notifications.py + tests + evidence summary | bot.py, trackers |

**Note:** P2-018 is verification-only (no code). Parent orchestrates the verification checks plus delegates independent LSP/static, token/unsafe, and VPS verifiers.

---

## 11. Parent Verification Delegation (Post-Implementation)

| Verifier | Per-Step Output Path | Scope |
|---|---|---|
| LSP/static verifier | `STEP-P2-0XX/verifiers/lsp-static-verifier.md` | LSP diagnostics, py_compile, import checks |
| Token/unsafe verifier | `STEP-P2-0XX/verifiers/token-unsafe-scan-verifier.md` | No token env, no unsafe SOPS, no type ignore, no empty catch |
| VPS/Aizanta health | `STEP-P2-0XX/verifiers/vps-aizanta-health-verifier.md` | docker ps, ss -tlnp, Aizanta intact |
| Safety verifier | `STEP-P2-017/verifiers/safety-verifier.md` | P2-017 only: guard order, AC-SAFE-001, handler tests PASS |

---

## 12. Auditor Gates

| Step | Auditor Path | Blocking Criteria |
|---|---|---|
| P2-017 | `audit-reports/P2/STEP-P2-017/step-p2-017-auditor-report.md` | Guard order correct, handler 56/56 PASS, token secure, systemd valid, bot connects |
| P2-018 | `audit-reports/P2/STEP-P2-018/step-p2-018-auditor-report.md` | 12/12 checks PASS, gateway stable, no token leak |
| P2-019 | `audit-reports/P2/STEP-P2-019/step-p2-019-auditor-report.md` | SEV routing confirmed, neutral tone, no persona language |

---

## 13. VPS/Deployment Note

P2-017 requires VPS deployment for full verification (token, gateway, systemd). Implementation sub-agent creates module + tests locally. Evidence staged. VPS deployment + live verification is per-step parent responsibility via SSH.

---

## 14. Exit Criteria — Batch Complete

- [ ] P2-017 bot.py created, LSP clean, tests pass, auditor PASS
- [ ] P2-018 health verification 12/12 checks PASS, auditor PASS
- [ ] P2-019 notifications.py created, LSP clean, tests pass, auditor PASS
- [ ] PROGRESS.md updated: P2 19/21, project 69/257
- [ ] CHECKLIST.md P2-017..019 checked
- [ ] Final report at `docs/setup-evidence/P2/batch-017-019-final-report.md`
- [ ] No drift from safety invariants (AC-SAFE-001, HARD STOP guard order, neutral alerts)

---

## Footer

| Field | Value |
|---|---|
| Generated by | Guinevere (Sisyphus agent) |
| Research inputs | 8 reports, all parent-read |
| Date | 2026-06-01 |
| Next | Parent read + todo sync → P2-017 implementation |