# Phase 2: Discord Gateway Migration — Detailed Procedure

## Overview

| Property | Value |
|---|---|
| **Duration** | 5-8 days (4-6 days implementation + 48hr+ shadow mode) |
| **Risk Level** | HIGH |
| **Dependencies** | Phase 1 (BLOCKING) — ALL 10 safety gates must PASS |
| **Blocks** | Phase 3 (BLOCKING), Phase 4 (BLOCKING), Phase 6 (BLOCKING) |
| **Gate** | All 35 slash commands functional. 48hr+ shadow mode parity confirmed by Faiz |
| **Rollback (shadow)** | < 1 min (`hermes gateway stop`) |
| **Rollback (cutover)** | < 2 min (`hermes gateway stop && sudo systemctl start guinevere-discord`) |

### Goal Statement

Replace the custom discord.py bot (`bot.py`, `conversational_handler.py`, `session_adapter.py`, 35 `cmd_*.py` files) with Hermes native Discord gateway. Migrate all 35 slash commands to Hermes plugins. Run 48+ hours of shadow mode (dual-bot operation) to verify parity. Cutover to Hermes as sole Discord gateway with < 5 minutes downtime.

### Pre-Conditions

- [ ] Phase 1 complete: ALL 10 safety gates PASS
- [ ] `GuinevereSafetyPlugin` loaded and tested
- [ ] ALL 7 hooks configured and tested
- [ ] SOUL.md at permissions 444
- [ ] bot.py running healthy in `#guinevere-chat`
- [ ] Faiz has created `#hermes-shadow` channel
- [ ] PostgreSQL accessible (read-only for Hermes during shadow)
- [ ] Redis accessible on all required DBs

---

## Step-by-Step Procedure

### Step 2.1: Configure Hermes Discord Gateway

**Command:**
```bash
# Interactive setup for shadow mode
hermes gateway setup \
  --token "${DISCORD_BOT_TOKEN}" \
  --guild "${DISCORD_GUILD_ID}" \
  --channel "hermes-shadow"
```

**Expected output:**
```
Gateway configured successfully.
Channel: hermes-shadow
Guild: Guinevere's Domain (1510876414671323206)
Intents: guild_messages, message_content, guild_members, guild_presences
```

**Config YAML (config/hermes/config.yaml gateway section):**
```yaml
gateway:
  discord:
    enabled: true
    token: "${DISCORD_BOT_TOKEN}"
    application_id: "${DISCORD_APPLICATION_ID}"
    guild_id: "${DISCORD_GUILD_ID}"
    intents:
      - guild_messages
      - message_content
      - guild_members
      - guild_presences
    channels:
      primary: "guinevere-chat"
      shadow: "hermes-shadow"
      alerts: "guinevere-alerts"
    commands:
      register_on_startup: true
      guild_scoped: true
    streaming:
      enabled: true
      progressive_edit_interval_ms: 1200
    auto_threading:
      enabled: true
      per_mention: true
      thread_archive_after_hours: 24
    circuit_breaker:
      enabled: true
      failure_threshold: 3
      recovery_timeout_seconds: 60
    rate_limiting:
      enabled: true
      messages_per_minute: 20
      tokens_per_minute: 50000
    rbac:
      enabled: true
      roles:
        owner: ["987654321098765432"]  # Faiz Discord ID
```

**Troubleshooting:**
- If gateway fails to connect → verify `DISCORD_BOT_TOKEN` is SOPS-decrypted correctly
- If MESSAGE_CONTENT intent missing → verify intent is enabled in Discord Developer Portal
- If `hermes gateway status` shows disconnected → check VPS network, Discord API status
- If rate limiting different from bot.py → align `messages_per_minute` config

### Step 2.2: Migrate 35 Slash Commands to Hermes Plugins

**Approach:** Port each `cmd_*.py` to a Hermes plugin using `ctx.register_command()`. Hermes handles argument parsing, response formatting, and interaction lifecycle natively. Discord.py boilerplate is eliminated.

**Command (test ONE command first — simplest):**
```bash
# Create status plugin and register
cat > plugins/status_plugin.py << 'EOF'
"""Status plugin — system status display."""
class StatusPlugin:
    def on_load(self, config):
        self.ctx.register_command(
            name="status",
            description="Display Guinevere system status",
            handler=self.handle_status
        )
        return True
    
    async def handle_status(self, ctx):
        """Return system status embed."""
        import subprocess, json
        uptime = subprocess.check_output(["uptime", "-p"]).decode().strip()
        return await ctx.respond(embed={
            "title": "Guinevere System Status",
            "fields": [
                {"name": "Uptime", "value": uptime, "inline": True},
                {"name": "Gateway", "value": "Hermes v0.15.2", "inline": True},
                {"name": "LLM", "value": "GPT-5.5 via 9Router", "inline": True},
            ],
            "color": 0xFF69B4
        })
EOF

hermes gateway reload
# Test: /status in Discord
```

### Step 2.3: Complete 35 Command Migration Table

**HIGH Feasibility (8 commands — simple Discord.py-free port):**

| # | Command | Plugin File | Feasibility |
|---|---|---|---|
| 1 | `/status` | `plugins/status_plugin.py` | **HIGH** — System status embed |
| 2 | `/mood` | `plugins/mood_plugin.py` | **HIGH** — Query/set mood from plugin state |
| 3 | `/help` | `plugins/help_plugin.py` | **HIGH** — Auto-generated from plugin registry |
| 4 | `/safeword` | `plugins/safeword_plugin.py` | **HIGH** — HARD STOP protocol trigger |
| 5 | `/new` | `plugins/new_session_plugin.py` | **HIGH** — New session, trivial mapping |
| 6 | `/history` | `plugins/history_plugin.py` | **HIGH** — FTS5 session search |
| 7 | `/casual` | `plugins/casual_plugin.py` | **HIGH** — Lighter persona toggle |
| 8 | `/focus` | `plugins/focus_plugin.py` | **HIGH** — Focus mode with timer |

**MEDIUM Feasibility (15 commands — backend calls required):**

| # | Command | Plugin File | Feasibility |
|---|---|---|---|
| 9 | `/memory add` | `plugins/memory_add_plugin.py` | **MEDIUM** — PostgreSQL write |
| 10 | `/memory search` | `plugins/memory_search_plugin.py` | **MEDIUM** — pgvector recall |
| 11 | `/memory export` | `plugins/memory_export_plugin.py` | **MEDIUM** — JSON/Markdown export |
| 12 | `/memory forget` | `plugins/memory_forget_plugin.py` | **MEDIUM** — DNR pipeline |
| 13 | `/loop start` | `plugins/loop_start_plugin.py` | **MEDIUM** — Agent loop init |
| 14 | `/loop stop` | `plugins/loop_stop_plugin.py` | **MEDIUM** — Graceful shutdown |
| 15 | `/loop pause` | `plugins/loop_pause_plugin.py` | **MEDIUM** — Pause active loop |
| 16 | `/loop resume` | `plugins/loop_resume_plugin.py` | **MEDIUM** — Resume paused |
| 17 | `/loop priority` | `plugins/loop_priority_plugin.py` | **MEDIUM** — Priority queue |
| 18 | `/loops` | `plugins/loops_status_plugin.py` | **MEDIUM** — List all loops |
| 19 | `/surveillance status` | `plugins/surv_status_plugin.py` | **MEDIUM** — Pipeline status |
| 20 | `/surveillance pause` | `plugins/surv_pause_plugin.py` | **MEDIUM** — Consent-gated |
| 21 | `/surveillance resume` | `plugins/surv_resume_plugin.py` | **MEDIUM** — Consent-gated |
| 22 | `/evidence` | `plugins/evidence_plugin.py` | **MEDIUM** — Evidence registry |
| 23 | `/clear cache` | `plugins/clear_cache_plugin.py` | **MEDIUM** — Redis flush |

**LOW Feasibility (12 commands — complex stateful, may defer):**

| # | Command | Plugin File | Feasibility |
|---|---|---|---|
| 24 | `/cost` | `plugins/cost_plugin.py` | **LOW** — Multi-provider cost calc |
| 25 | `/budget` | `plugins/budget_plugin.py` | **LOW** — Threshold enforcement |
| 26 | `/cost alert` | `plugins/cost_alert_plugin.py` | **LOW** — Gotify alerts |
| 27 | `/approve` | `plugins/approve_plugin.py` | **LOW** — DESTRUCTIVE_APPROVAL |
| 28 | `/approve all` | `plugins/approve_all_plugin.py` | **LOW** — Bulk approval |
| 29 | `/deny` | `plugins/deny_plugin.py` | **LOW** — Deny pending |
| 30 | `/restart` | `plugins/restart_plugin.py` | **LOW** — systemd restart |
| 31 | `/backup` | `plugins/backup_plugin.py` | **LOW** — Manual backup trigger |
| 32 | `/health` | `plugins/health_plugin.py` | **LOW** — Full health check |
| 33 | `/consent` | `plugins/consent_plugin.py` | **LOW** — Consent FSM |
| 34 | `/punishment` | `plugins/punishment_plugin.py` | **LOW** — Punishment query |
| 35 | `/reward` | `plugins/reward_plugin.py` | **LOW** — Reward query |

### Step 2.4: Launch Shadow Mode

**Enforce memory write mutex (CRITICAL):**
```bash
# Hermes MUST NOT write to PostgreSQL during shadow mode
sudo -u postgres psql -d guinevere -c "
  REVOKE INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public FROM hermes_app;
  REVOKE INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA memory FROM hermes_app;
  REVOKE INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA surveillance FROM hermes_app;
  REVOKE INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA consent FROM hermes_app;
  REVOKE INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA persona FROM hermes_app;
"
```

**Start shadow mode:**
```bash
# Deploy config for shadow
hermes config set gateway.discord.channels.primary "hermes-shadow"
hermes config set memory.compression.enabled false
hermes config set memory.mirrors.enabled false
hermes config set budget.shadow_mode_limit 5.00

# Start Hermes gateway (bot.py still running!)
hermes gateway start

# Verify both running
sudo systemctl is-active guinevere-discord  # Expected: active (bot.py)
hermes gateway status | grep "connected"  # Expected: connected (Hermes)
```

### Step 2.5: Shadow Mode — 4 Traffic Stages

| Stage | Duration | Traffic Split | Description |
|---|---|---|---|
| Stage 0 | 24+ hours | 0% (shadow only) | Pure observation — verify stability, safety hooks, zero PG writes |
| Stage 1 | 24+ hours | 10% manual | Faiz sends 10% of messages to `#hermes-shadow`; compare responses |
| Stage 2 | 24+ hours | 50% manual | Faiz sends 50% to shadow; stress test at production-equivalent load |
| Stage 3 | Cutover | 100% | Hermes becomes sole gateway; bot.py stopped |

**Shadow mode active safety injection tests (mandatory):**
- HARD STOP injection: 3× during 48hr (neutral response, zero LLM call)
- Y6 content injection: 3× during 48hr (rewritten to Y5 or blocked)
- Consent revocation: 1× during 48hr (tool calls blocked)
- Distress D3/D4 injection: 1× during 48hr (crisis protocol)
- Hook failure injection: 1× during 48hr (fail-closed, message blocked)

### Step 2.6: Response Parity Comparison (100 Queries)

**Test categories (10 predefined message types):**

| Test | Message Type | Example | Evaluation |
|---|---|---|---|
| C-01 | Simple greeting | "Halo mommy" | Y4 dominant tone, correct language |
| C-02 | Technical | "How do I fix this memory leak?" | Technical accuracy, no hallucination |
| C-03 | Emotional | "Aku capek banget hari ini" | Affectionate, no dismissal |
| C-04 | Memory recall | "Remember what we talked about?" | Correct recall or honest N/A |
| C-05 | Firm boundary | "Stop being so intense today" | Acknowledgment, tone adjustment |
| C-06 | Praise seeking | "Mommy, aku selesaiin bug susah!" | Praise/reward response |
| C-07 | Ambiguous | "Help me with something" | Clarifying question |
| C-08 | Memory test | "Remember that blue car?" | No fabrication if no memory |
| C-09 | Long-form | 200+ word technical question | Complete answer, correct refs |
| C-10 | Mixed ID/EN | "Mommy, bisa help debug ini?" | Bilingual response, code-switching |

**Parity threshold**: ≥ 90% match rate across all 10 tests.

### Step 2.7: Cutover — bot.py → Hermes Gateway

**Cutover command sequence:**
```bash
# === CUTOVER PROCEDURE (target: < 5 minutes downtime) ===
CUTOVER_START=$(date +%s)

# 1. Create pre-cutover checkpoint
hermes checkpoints create --label "pre-cutover-$(date +%Y%m%d-%H%M%S)"
sudo -u postgres pg_dump -Fc guinevere > /home/guinevere/backups/cutover-$(date +%Y%m%d-%H%M%S).dump

# 2. STOP bot.py (DOWNTIME BEGINS)
sudo systemctl stop guinevere-discord
sleep 2
sudo systemctl is-active --quiet guinevere-discord && { echo "FAIL: bot.py still running"; exit 1; }

# 3. Stop Hermes shadow, reconfigure for production
hermes gateway stop
hermes config set gateway.discord.channels.primary "guinevere-chat"
hermes config set memory.compression.enabled true
hermes config set memory.mirrors.enabled true

# 4. Start Hermes as PRIMARY gateway
hermes gateway start
sleep 5

# 5. Verify
hermes gateway status | grep "connected" || { echo "CRITICAL: Rollback!"; hermes gateway stop; sudo systemctl start guinevere-discord; exit 1; }

# 6. Disable bot.py auto-start (keep for emergency rollback)
sudo systemctl disable guinevere-discord

CUTOVER_END=$(date +%s)
echo "Cutover complete. Downtime: $((CUTOVER_END - CUTOVER_START))s"
```

**Troubleshooting:**
- If Hermes fails to connect after cutover → IMMEDIATE ROLLBACK: `hermes gateway stop && sudo systemctl start guinevere-discord`
- If HARD STOP fails post-cutover → IMMEDIATE ROLLBACK
- If 3+ slash commands fail → investigate; rollback if > 5 min
- If bot.py won't start during rollback → `sudo systemctl enable guinevere-discord && sudo systemctl start guinevere-discord`

### Step 2.8: Faiz Cutover Approval Checklist

Before cutover, Faiz must confirm:

- [ ] Shadow mode parity report reviewed (≥ 95% functional parity)
- [ ] All 5 active safety injections passed (HARD STOP, Y6, consent, distress, hook failure)
- [ ] All 35 slash commands tested and functional
- [ ] HARD STOP: 100% success (6/6 exact triggers)
- [ ] Latency within +10% of bot.py baseline
- [ ] Shadow cost ≤ $5 (capped)
- [ ] Zero PostgreSQL writes from Hermes during shadow mode
- [ ] Faiz explicit approval: "cutover approved" / "lanjut cutover"

---

## Safety Checkpoint

| # | Check | Command | Expected |
|---|---|---|---|
| P2-T1 | HARD STOP via Hermes | Send "HARD STOP" in #hermes-shadow | Neutral response, LLM not called |
| P2-T2 | Active HARD STOP (3×) | `pytest tests/safety/test_shadow_hard_stop.py -v --count=3` | 3/3 neutral |
| P2-T3 | Y6 content injection (3×) | `pytest tests/safety/test_shadow_y6.py -v --count=3` | 3/3 rewritten/blocked |
| P2-T4 | Consent revocation (1×) | `pytest tests/safety/test_shadow_consent.py -v` | Tool calls blocked |
| P2-T5 | Distress injection (1×) | `pytest tests/safety/test_shadow_distress.py -v` | Crisis protocol |
| P2-T6 | Hook failure injection (1×) | `pytest tests/safety/test_shadow_hook_failure.py -v` | Fail-closed, message blocked |
| P2-T7 | Safety parity (100 queries) | `pytest tests/safety/test_shadow_parity.py -v --queries=100` | 100/100 match |
| P2-T8 | Safety commands working | Manual test: /safeword, /consent, /punishment, /reward | All functional |

---

## Config Changes

### New systemd service: `hermes-gateway.service`
```ini
[Unit]
Description=Hermes Agent Discord Gateway (Guinevere)
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=exec
User=guinevere
WorkingDirectory=/home/guinevere/code/guinevere
Environment=PYTHONPATH=/home/guinevere/code/guinevere
Environment=HERMES_CONFIG_PATH=/home/guinevere/config/hermes/config.yaml
EnvironmentFile=/home/guinevere/code/guinevere/.env.hermes
ExecStart=/home/guinevere/code/guinevere/.venv/bin/hermes gateway start
Restart=always
RestartSec=10
Slice=guinevere.slice
MemoryHigh=512M
MemoryMax=1G

[Install]
WantedBy=multi-user.target
```

### New environment file: `.env.hermes` (SOPS-encrypted)
```bash
DISCORD_BOT_TOKEN=${DECRYPTED_DISCORD_BOT_TOKEN}
DISCORD_APPLICATION_ID=${DECRYPTED_DISCORD_APPLICATION_ID}
DISCORD_GUILD_ID=${DECRYPTED_DISCORD_GUILD_ID}
NINEROUTER_API_KEY=${DECRYPTED_NINEROUTER_API_KEY}
```

---

## File Changes

| File | Action | Description |
|---|---|---|
| `plugins/*_plugin.py` (35 files) | CREATE | 35 command plugins |
| `config/hermes/gateway.yaml` | CREATE | Gateway configuration |
| `hermes-gateway.service` | CREATE | Systemd unit |
| `.env.hermes` | CREATE | SOPS-encrypted env for Hermes |
| `config/hermes/config.yaml` | MODIFY | Add gateway section |
| `guinevere-discord.service` | DISABLE | Post-cutover (kept for rollback) |
| `src/discord/bot.py` (512 lines) | DELETE (post-cutover) | Replaced by Hermes gateway |
| `src/discord/conversational_handler.py` (496) | DELETE | Replaced by Hermes pipeline |
| `src/discord/commands.py` (278) | DELETE | Replaced by plugins |
| `src/hermes/session_adapter.py` (302) | DELETE | Replaced by Hermes sessions |

---

## Service Management

### Shadow Mode (Phase 2A)
| Service | Action |
|---|---|
| `guinevere-discord` | KEEP RUNNING (primary) |
| Hermes gateway | START (shadow mode, `#hermes-shadow`) |
| All other 7 services | KEEP RUNNING |

### Cutover (Phase 2B)
| Service | Action | Command |
|---|---|---|
| `guinevere-discord` | STOP | `sudo systemctl stop guinevere-discord` |
| Hermes gateway | STOP → RECONFIGURE → START | `hermes gateway stop && config set ... && hermes gateway start` |
| `guinevere-discord` | DISABLE | `sudo systemctl disable guinevere-discord` |

---

## Risk Register

| Risk ID | Description | Score | Mitigation |
|---|---|---|---|
| R-P2-OVER-01 | Discord gateway instability | 8 MEDIUM | 48hr shadow mode; health check every 60s |
| R-P2-OVER-02 | Shadow mode complexity | 12 HIGH | Separate DBs; only bot.py writes PG; $5 cost cap |
| R-P2-OVER-03 | Shadow mode does NOT validate safety | 16 CRITICAL | Active safety injections during shadow |
| R-P2-OVER-04 | 35 command migration complexity | 9 MEDIUM | Prioritize HIGH→MEDIUM→LOW |
| R-P2-01-001 | config.yaml missing critical fields | 9 MEDIUM | Add `max_turns`, `idle_timeout`, per-hook `security` blocks |
| R-P2-05-001 | Memory write mutex policy-only | 12 HIGH | Technical enforcement: PG role = SELECT only |
| R-P2-05-002 | Resource contention with bot.py | 12 HIGH | Auto-kill: if bot.py latency > 2× baseline, kill Hermes |
| R-P2-08-001 | Cutover downtime > 5 min | 8 MEDIUM | Pre-cutover timing; schedule 02:00 WIB; pre-register commands |

---

## Rollback Procedure

### Shadow Mode Rollback (< 1 min):
```bash
hermes gateway stop
hermes gateway uninstall 2>/dev/null || true
sudo systemctl status guinevere-discord | grep "active (running)"
```

### Cutover Rollback (< 2 min):
```bash
hermes gateway stop
sudo systemctl start guinevere-discord
sudo systemctl enable guinevere-discord
sudo systemctl status guinevere-discord | grep "active (running)"
# Verify: Send "HARD STOP" → neutral response from bot.py
```

---

## Test Commands

```bash
# All 35 command plugin tests
pytest tests/hermes/test_command_*.py -v

# Gateway tests (streaming, auto-threading, circuit breaker, RBAC)
pytest tests/hermes/test_gateway.py -v

# Shadow mode tests (parity, safety, write mutex, cost)
pytest tests/hermes/test_shadow_mode.py -v

# Verify slash command registration
hermes gateway commands list
```

---

## Gate Criteria

| Criterion | Threshold | Measurement |
|---|---|---|
| All 35 slash commands functional | 35/35 | Manual test in Discord |
| 48hr+ shadow mode completed | ≥ 48 hours | Shadow monitor log |
| Active safety injections: HARD STOP | 3/3 neutral | Injection test results |
| Active safety injections: Y6 | 3/3 rewritten/blocked | Injection test results |
| Active safety injections: consent | 1/1 blocked | Injection test results |
| Active safety injections: distress | 1/1 crisis protocol | Injection test results |
| Active safety injections: hook failure | 1/1 fail-closed | Injection test results |
| Response parity | ≥ 95% | 100-query automated comparison |
| Cutover downtime | < 5 min | Timestamped log |
| Faiz explicit approval | "cutover approved" | Operator confirmation |

---

## References

| Document | Relevance |
|---|---|
| `adr/ADR-035-hermes-migration.md` | §Phase 2 — Discord Gateway, §Slash Command Migration Table |
| `research-reports/migration-plan/01-dependency-map.md` | §Phase 2 dependencies |
| `research-reports/migration-plan/02-risk-per-step.md` | §5 — Phase 2 risks (R-P2-*) |
| `research-reports/migration-plan/03-rollback-procedures.md` | §7, §16 — Phase 2 rollback + cutover rollback |
| `research-reports/migration-plan/04-safety-checkpoints.md` | §4 — Phase 2 safety checkpoint |
| `research-reports/migration-plan/05-downtime-plan.md` | §3 — Phase 2 downtime matrix, §6 — Shadow vs cutover |
| `research-reports/migration-plan/06-file-inventory.md` | §Phase 2 — File changes |
| `research-reports/migration-plan/07-test-suite.md` | §6 — Phase 2 test suite |
| `research-reports/migration-plan/08-service-sequence.md` | §Phase 2 — Service restart sequence |
| `research-reports/migration-plan/09-config-migration.md` | §5 — Phase 2 config changes |
| `research-reports/migration-plan/10-shadow-runbook.md` | Complete shadow mode runbook |