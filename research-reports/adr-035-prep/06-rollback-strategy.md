# 06 — Rollback Strategy: Hermes Migration Reversibility

> **Date**: 2026-06-04
> **Scope**: Exact copy-pasteable rollback procedures for every migration phase (Phase 0 through Phase 7).
> **Author**: Guinevere (Sisyphus-Junior)
> **Status**: Complete — ready for ADR-035 integration
> **Binding Authority**: ADR-025 (Backup & DR Strategy), ADR-032 (Backup Storage Strategy)
> **Format Reference**: ADR-033 (Browser Automation Obscura) — Rollback Plan section

---

## Table of Contents

1. [Rollback Philosophy & Principles](#1-rollback-philosophy--principles)
2. [Reference Architecture — Current vs Target State](#2-reference-architecture--current-vs-target-state)
3. [Pre-Migration Safety Net (Run BEFORE Any Phase)](#3-pre-migration-safety-net-run-before-any-phase)
4. [Phase 0 Rollback — Security Remediation](#4-phase-0-rollback--security-remediation)
5. [Phase 1 Rollback — Safety Foundation](#5-phase-1-rollback--safety-foundation)
6. [Phase 2 Rollback — Discord Gateway Migration](#6-phase-2-rollback--discord-gateway-migration)
7. [Phase 3 Rollback — Memory Bridge Enhancement](#7-phase-3-rollback--memory-bridge-enhancement)
8. [Phase 4 Rollback — Tool/MCP Migration](#8-phase-4-rollback--toolmcp-migration)
9. [Phase 5 Rollback — Skills & Persona](#9-phase-5-rollback--skills--persona)
10. [Phase 6 Rollback — LLM Routing & Budget](#10-phase-6-rollback--llm-routing--budget)
11. [Phase 7 Rollback — Hardening & Monitoring](#11-phase-7-rollback--hardening--monitoring)
12. [Global Emergency Rollback](#12-global-emergency-rollback)
13. [Partial Rollback — Single Phase Without Affecting Others](#13-partial-rollback--single-phase-without-affecting-others)
14. [Data Recovery — PostgreSQL Restore Procedure](#14-data-recovery--postgresql-restore-procedure)
15. [Discord Cutover Rollback — Hermes Gateway → bot.py](#15-discord-cutover-rollback--hermes-gateway--botpy)
16. [Hermes Backup & Checkpoint Usage](#16-hermes-backup--checkpoint-usage)
17. [Git-Based Rollback](#17-git-based-rollback)
18. [Systemd Service Rollback](#18-systemd-service-rollback)
19. [Rollback Time Estimates — Summary Table](#19-rollback-time-estimates--summary-table)
20. [Footer](#20-footer)

---

## 1. Rollback Philosophy & Principles

### 1.1 Universal First Step

**Every single rollback procedure in this document begins with:**

```bash
hermes gateway stop
```

This is the universal kill-switch. If Hermes gateway is not running, this is a no-op (exit 0). This ensures no Hermes Discord activity can interfere with rollback operations.

### 1.2 Five Iron Rules

1. **Data never moves backward.** PostgreSQL+pgvector is the primary write authority (per Report 07, Option C Hybrid). Hermes writes are supplementary read-only. Rollback is code + config + service topology — not data migration.
2. **bot.py is always the fallback.** The existing `guinevere-bot.service` (603 lines of bot.py + 33 slash commands) runs independently of Hermes. It is the safe harbor.
3. **Git is the ultimate undo.** Every migration change is version-controlled. `git checkout` restores code. Hermes configs are the main new artifacts.
4. **Operators verify, don't assume.** Every rollback step includes a verification command. Faiz runs the commands and verifies the output before declaring rollback complete.
5. **Rollback is a phase gate.** No migration phase proceeds until the previous phase's rollback has been tested and verified. Each phase gate includes a rollback drill.

### 1.3 Service Dependency Map

```
guinevere-bot.service          (Discord bot — the fallback, ALWAYS available)
guinevere-core.service         (FastAPI internal API, localhost:8000)
guinevere-loops.service        (Agent loop 7-phase state machine)
guinevere-mcp.service          (MCP tool server, 16 tools)
guinevere-scheduler.service    (APScheduler: rituals, consolidation, cost reports)
guinevere-surveillance.service (Surveillance event ingestion)
guinevere-monitoring.service   (Prometheus/Grafana/Loki stack)
guinevere-obscura.service      (Obscura CDP server, port 9222)
hermes-gateway.service         (Hermes Discord gateway — created during Phase 2)
```

### 1.4 Rollback Pre-Flight Checklist

Before ANY phase begins, Faiz confirms:

- [ ] `git status` is clean (no uncommitted changes)
- [ ] `guinevere-bot.service` is running and healthy
- [ ] `guinevere-core.service` is running and healthy
- [ ] PostgreSQL is accessible (`psql -U guinevere_core -d guinevere -c "SELECT 1"`)
- [ ] Redis is accessible (`redis-cli -p 6380 PING`)
- [ ] Latest `hermes checkpoints --list` shows at least one checkpoint
- [ ] Latest `pg_dump` backup is < 1 hour old (or manual backup just taken)

---

## 2. Reference Architecture — Current vs Target State

### 2.1 Current State (Pre-Migration, June 2026)

```
Systemd Services:
  guinevere-bot.service        ACTIVE — Discord bot (bot.py, 33 slash commands)
  guinevere-core.service       ACTIVE — FastAPI internal API
  guinevere-loops.service      ACTIVE — Agent loop state machine
  guinevere-mcp.service        ACTIVE — MCP tool server
  guinevere-scheduler.service  ACTIVE — APScheduler
  guinevere-surveillance.service ACTIVE — Surveillance ingestion
  guinevere-monitoring.service ACTIVE — Prometheus/Grafana/Loki
  hermes-gateway.service       NOT CREATED YET

Discord:              bot.py (discord.ext.commands.Bot) handles all messages
Memory:               PostgreSQL+pgvector (47 tables, 12 schemas)
Session:              Redis DB4 (2hr TTL, 20 turns)
LLM:                  9Router (localhost:20128) → GPT-5.5 + DeepSeek V4 Flash
Safety:               14 files (HARD STOP, consent, yandere FSM, drift, distress, etc.)
Hermes Agent:         Installed (v0.15.2), NOT configured, NOT running
```

### 2.2 Target State (Post-Migration)

```
Systemd Services:
  guinevere-bot.service        DISABLED (replaced by Hermes gateway)
  guinevere-core.service       ACTIVE (unchanged)
  guinevere-loops.service      ACTIVE (hooks-enhanced)
  guinevere-mcp.service        ACTIVE (simplified — 7 custom tools only)
  guinevere-scheduler.service  ACTIVE (unchanged)
  guinevere-surveillance.service ACTIVE (unchanged)
  guinevere-monitoring.service ACTIVE (unchanged)
  hermes-gateway.service       ACTIVE — Hermes Discord gateway

Discord:              Hermes native gateway (bot.py disabled)
Memory:               PostgreSQL+pgvector PRIMARY + Hermes compression (read-only)
Session:              Hermes native + custom PostgreSQL bridge
LLM:                  9Router (localhost:20128) — unchanged
Safety:               Hermes hooks (pre_gateway_dispatch, pre_llm_call, pre_tool_call, transform_llm_output)
```

---

## 3. Pre-Migration Safety Net (Run BEFORE Any Phase)

### 3.1 Full System Snapshot

Run once before Phase 0 begins. Creates the baseline for ALL future rollbacks.

```bash
# === STEP 1: Stop Hermes gateway (no-op if not running) ===
hermes gateway stop

# === STEP 2: Create Hermes checkpoint ===
hermes checkpoints create --label "pre-migration-baseline-$(date +%Y%m%d-%H%M%S)"

# === STEP 3: Git snapshot ===
cd /home/guinevere/code/guinevere
git tag "pre-hermes-migration-$(date +%Y%m%d-%H%M%S)"
git push origin --tags

# === STEP 4: PostgreSQL full dump ===
sudo -u postgres pg_dump -Fc guinevere > /home/guinevere/backups/pre-migration-$(date +%Y%m%d).dump

# === VERIFY PostgreSQL backup ===
ls -lh /home/guinevere/backups/pre-migration-*.dump
# Expected: File size > 0 bytes, timestamp matches

# === STEP 5: Save systemd service state ===
sudo systemctl list-units 'guinevere-*' --all > /home/guinevere/backups/pre-migration-services-$(date +%Y%m%d).txt

# === VERIFY service list ===
cat /home/guinevere/backups/pre-migration-services-$(date +%Y%m%d).txt
# Expected: All guinevere-* services listed with ACTIVE/INACTIVE states

# === STEP 6: Save pip freeze for dependency rollback ===
cd /home/guinevere/code/guinevere
./.venv/bin/pip freeze > /home/guinevere/backups/pre-migration-pip-$(date +%Y%m%d).txt

# === VERIFY pip freeze ===
wc -l /home/guinevere/backups/pre-migration-pip-$(date +%Y%m%d).txt
# Expected: 50+ lines of pinned packages

# === STEP 7: Offsite backup (per ADR-032) ===
rclone copy /home/guinevere/backups/pre-migration-*.dump idcloudhost:guinevere-dr-backups/manual/
rclone copy /home/guinevere/backups/pre-migration-*.dump r2:guinevere-dr-backups/manual/

# === VERIFY offsite ===
rclone ls idcloudhost:guinevere-dr-backups/manual/ | grep pre-migration
rclone ls r2:guinevere-dr-backups/manual/ | grep pre-migration
# Expected: File appears in both storage providers
```

**Time**: ~10-15 minutes (dominated by pg_dump and rclone upload).

### 3.2 What This Snapshot Protects

| Artifact | What It Captures | Rollback Use |
|---|---|---|
| Git tag `pre-hermes-migration-*` | All source code at exact migration start | `git checkout` to restore any file |
| `pg_dump` (custom format) | All 47 tables across 12 schemas | Full database restore via `pg_restore` |
| `pip freeze` | All Python package versions | `pip install -r` to restore dependencies |
| Systemd state list | Service status at snapshot time | Verify services restored correctly |
| Hermes checkpoint | Hermes internal state | `hermes checkpoints --restore` |
| Offsite copy (S3 + R2) | Redundant backup of all above | DR scenario recovery (per ADR-032) |

---

## 4. Phase 0 Rollback — Security Remediation

### Phase 0 Summary

| Attribute | Value |
|---|---|
| Duration | 1-2 days |
| Risk | LOW |
| Changes | Upgrade aiohttp, pip, ecdsa; fix config.yaml path; create `.env`; install ripgrep |
| Data modified | None (package versions only) |
| Services affected | None (Hermes not running yet) |
| Gate | `hermes doctor` clean + `hermes security` zero HIGH/MODERATE |

### 4.1 Rollback Trigger

| Trigger Condition | How to Detect |
|---|---|
| `hermes security` shows NEW vulnerabilities after upgrade | Run `hermes security` after each pip install |
| `hermes doctor` fails after config changes | Run `hermes doctor` after each config edit |
| Package upgrade breaks Hermes CLI (`hermes --help` fails) | Run `hermes --help` after each upgrade |
| `.env` file exposes secrets accidentally | Manual review: `cat /home/guinevere/.env` — no plaintext tokens |

### 4.2 Pre-Conditions

- [ ] `hermes --help` was working before Phase 0 began
- [ ] Pre-migration `pip freeze` snapshot exists at `/home/guinevere/backups/pre-migration-pip-*.txt`
- [ ] Pre-migration `git tag` exists
- [ ] `hermes gateway stop` returns clean (gateway not running)

### 4.3 Exact Commands

```bash
# === STEP 1: Universal kill-switch ===
hermes gateway stop

# === STEP 2: Rollback pip packages to pre-Phase-0 versions ===
cd /home/guinevere/code/guinevere
# Find the latest pre-migration pip freeze
PIP_FREEZE=$(ls -t /home/guinevere/backups/pre-migration-pip-*.txt | head -1)
./.venv/bin/pip install -r "$PIP_FREEZE"

# === VERIFY package versions ===
./.venv/bin/pip list | grep -E "aiohttp|ecdsa|pip|PyJWT"
# Expected: Match versions from pre-migration pip freeze

# === STEP 3: Rollback git changes ===
cd /home/guinevere/code/guinevere
git checkout -- config/hermes/config.yaml
git checkout -- .env 2>/dev/null || rm -f /home/guinevere/code/guinevere/.env

# === VERIFY git clean ===
git status
# Expected: "nothing to commit, working tree clean" (or only untracked backup files)

# === STEP 4: Restore pip packages if git checkout restored requirements ===
./.venv/bin/pip install --require-hashes -r requirements-hashes.txt 2>/dev/null || \
./.venv/bin/pip install -r "$PIP_FREEZE"

# === VERIFY Hermes still works ===
hermes --help
# Expected: Hermes CLI help output
hermes security
# Expected: Same vulnerability count as pre-Phase-0 (11 total: 1 HIGH, 4 MODERATE)
```

### 4.4 Data Integrity Verification

```bash
# No data was modified by Phase 0. Verify PostgreSQL is untouched:
sudo -u postgres psql -d guinevere -c "SELECT count(*) FROM memory.episodes"
# Expected: Same count as pre-Phase-0 (any non-error response)

# Verify Redis is untouched:
redis-cli -p 6380 PING
# Expected: PONG

# Verify Hermes state is intact:
hermes doctor
# Expected: Shows pre-Phase-0 state (config.yaml may show "not found" — that's the pre-state)
```

### 4.5 Service Restoration Order

```
No services were affected. Skip this step.
```

### 4.6 Communication Plan

| Recipient | Message | Channel |
|---|---|---|
| Faiz | "Phase 0 rollback complete. Packages reverted to pre-migration versions. Hermes functional. No data affected." | Discord #guinevere-chat |

### 4.7 Time Estimate

| Step | Time |
|---|---|
| `hermes gateway stop` | < 1 second |
| `pip install -r` (restore packages) | 1-2 minutes |
| `git checkout` (restore files) | < 5 seconds |
| Verification | 1 minute |
| **Total** | **< 5 minutes** |

### 4.8 Post-Rollback Verification

```bash
# 1. Hermes CLI functional
hermes --help && echo "PASS" || echo "FAIL"

# 2. Hermes security shows expected vulnerability count
hermes security | grep "vulnerabilities found" && echo "PASS" || echo "FAIL"

# 3. bot.py still functional (unaffected by Phase 0)
sudo systemctl status guinevere-bot | grep "active (running)" && echo "PASS" || echo "FAIL"

# 4. All systemd services running
sudo systemctl is-active guinevere-core guinevere-bot guinevere-mcp guinevere-loops \
  guinevere-scheduler guinevere-surveillance guinevere-monitoring
# Expected: all "active"

# 5. PostgreSQL accessible
psql -U guinevere_core -d guinevere -c "SELECT 1" && echo "PASS" || echo "FAIL"
```

### 4.9 Lessons Learned Capture

Document in `/home/guinevere/backups/rollback-log-phase0-$(date +%Y%m%d).md`:

```markdown
# Phase 0 Rollback Log

## Trigger
[What triggered rollback? E.g., aiohttp upgrade broke Hermes CLI]

## Root Cause
[Why did the specific package upgrade cause issues?]

## Fix for Retry
[What to do differently? E.g., pin aiohttp==3.9.5 not latest]

## Duration
[Actual rollback time vs estimate]

## Retry Plan
[When and how to re-attempt Phase 0]
```

---

## 5. Phase 1 Rollback — Safety Foundation

### Phase 1 Summary

| Attribute | Value |
|---|---|
| Duration | 3-5 days |
| Risk | HIGH — Safety features are non-negotiable |
| Changes | SOUL.md, 10 safety hooks/plugins (HARD STOP, consent, distress, yandere FSM, drift, DNR, classification, secret scanner, punishment, reward), 5+ plugin files |
| Data modified | None (code + config only) |
| Services affected | None (Hermes not running yet; bot.py unchanged) |
| Gate | ALL 15+ safety features pass integration tests |

### 5.1 Rollback Trigger

| Trigger Condition | How to Detect |
|---|---|
| HARD STOP test fails (pre_gateway_dispatch hook doesn't intercept) | Run Phase 1 gate test: trigger "HARD STOP" → must return neutral response, zero LLM call |
| Consent gate fails-closed incorrectly (blocks legitimate tool calls) | Run consent gate test: active consent → tool allowed; WITHDRAWN → tool blocked |
| Yandere FSM allows Y6 content through | Run boundary test: generate Y6-triggering content → must be rewritten to Y5 or blocked |
| Drift detector false-positive (alerts on valid prompt) | Monitor drift logs for [DRIFT] entries during normal operation |
| DNR enforcement fails (DNR memory appears in recall) | Run DNR test: mark memory DNR → recall_memories() must exclude it |
| Any safety test suite failure | Run full safety test suite: `python -m pytest tests/persona/ -v` |

### 5.2 Pre-Conditions

- [ ] Phase 0 gate passed (`hermes doctor` clean, `hermes security` zero HIGH/MODERATE)
- [ ] `guinevere-bot.service` is running and handling Discord messages normally
- [ ] Safety hook files exist at expected paths (see Section 5.3 Step 2 for list)
- [ ] Pre-Phase-1 git tag exists
- [ ] Pre-Phase-1 Hermes checkpoint exists

### 5.3 Exact Commands

```bash
# === STEP 1: Universal kill-switch ===
hermes gateway stop

# === STEP 2: Revert all safety hook files (remove or git checkout) ===
cd /home/guinevere/code/guinevere

# Remove Phase 1-created files
rm -f plugins/safety_hooks.py
rm -f plugins/auth_overlay.py
rm -f plugins/memory_plugin.py
rm -f plugins/persona_plugin.py
rm -f config/hermes/hooks.yaml
rm -f config/hermes/mcp-servers.yaml

# Restore any modified files
git checkout -- src/persona/yandere_fsm.py
git checkout -- src/persona/drift_detector.py
git checkout -- src/persona/safe_mode.py
git checkout -- src/persona/hard_stop_handler.py

# === VERIFY files removed/restored ===
ls plugins/ 2>/dev/null && echo "WARNING: plugins/ still exists" || echo "PASS: plugins/ removed"
git status
# Expected: "nothing to commit, working tree clean" (plugins/ deletion may show as untracked removal)

# === STEP 3: Restore SOUL.md to pre-Phase-1 state ===
cd /home/guinevere/code/guinevere
git checkout -- config/hermes/SOUL.md 2>/dev/null || \
  rm -f ~/.hermes/SOUL.md

# === VERIFY SOUL.md removed/restored ===
cat ~/.hermes/SOUL.md 2>/dev/null && echo "WARNING: SOUL.md still present" || echo "PASS: SOUL.md removed"

# === STEP 4: Remove any Hermes hook registrations ===
hermes hooks list 2>/dev/null
# Note: if hermes hooks CLI doesn't exist or returns empty, hooks are effectively removed

# === VERIFY: No hooks remain ===
hermes hooks list 2>/dev/null && echo "WARNING: hooks still registered" || echo "PASS: no hooks"
```

### 5.4 Data Integrity Verification

```bash
# Phase 1 does not modify data. Verify:
sudo -u postgres psql -d guinevere -c "SELECT count(*) FROM memory.episodes"
# Expected: Same count as pre-Phase-1

sudo -u postgres psql -d guinevere -c "SELECT count(*) FROM persona.mood_states"
# Expected: Same count as pre-Phase-1

redis-cli -p 6380 PING
# Expected: PONG
```

### 5.5 Service Restoration Order

```
No services were affected. Skip this step.
```

### 5.6 Communication Plan

| Recipient | Message | Channel |
|---|---|---|
| Faiz | "Phase 1 rollback complete. All safety hooks reverted. bot.py running normally with original safety code. No data affected." | Discord #guinevere-chat |

### 5.7 Time Estimate

| Step | Time |
|---|---|
| `hermes gateway stop` | < 1 second |
| Git checkout / file removal | < 30 seconds |
| Verification | 1 minute |
| **Total** | **< 3 minutes** |

### 5.8 Post-Rollback Verification

```bash
# 1. bot.py running with original safety code
sudo systemctl status guinevere-bot | grep "active (running)" && echo "PASS" || echo "FAIL"

# 2. HARD STOP still works via original bot.py handler
# Send "HARD STOP" in Discord → Guinevere responds neutral, no punishment

# 3. All original safety files intact
ls src/persona/hard_stop_handler.py src/persona/yandere_fsm.py src/persona/drift_detector.py \
   src/persona/safe_mode.py src/persona/consent_gate.py
# Expected: All files exist

# 4. Full safety test suite passes (original tests, not Hermes hook tests)
cd /home/guinevere/code/guinevere
./.venv/bin/python -m pytest tests/persona/ -v --tb=short
# Expected: All tests PASS (same as pre-Phase-1)
```

### 5.9 Lessons Learned Capture

```markdown
# Phase 1 Rollback Log

## Trigger
[What safety test failed? Which hook?]

## Root Cause
[Hook placement issue? Hook not firing? Incorrect action?]

## Fix for Retry
[Adjust hook priority? Change hook action? Add additional hook?]

## Duration
[Actual rollback time vs estimate]

## Retry Plan
[When and how to re-attempt the specific safety hook migration]
```

---

## 6. Phase 2 Rollback — Discord Gateway Migration

### Phase 2 Summary

| Attribute | Value |
|---|---|
| Duration | 3-5 days |
| Risk | HIGH — User-facing gateway cutover |
| Changes | `hermes gateway setup`, 33 slash commands as Hermes plugins, shadow mode (48hr), cutover |
| Data modified | None |
| Services affected | `guinevere-bot.service` (disabled during cutover), `hermes-gateway.service` (created) |
| Gate | All 33 slash commands functional. Shadow mode parity confirmed. Faiz approves cutover. |

### 6.2A Rollback Trigger — Shadow Mode (Phase 2 Steps 2.1-2.9)

Rollback during shadow mode while bot.py is still primary:

| Trigger Condition | How to Detect |
|---|---|
| Hermes gateway fails to start | `hermes gateway status` → shows errors, not "running" |
| Slash command registration fails | `hermes gateway list` → fewer than 33 commands registered |
| Shadow mode comparison shows divergence | Compare bot.py response vs Hermes response for same message → >20% semantic difference |
| Hermes gateway crashes repeatedly | `hermes gateway status` → uptime < 5 minutes between crashes |
| Gateway setup misconfigures production guild | `hermes gateway status` → shows wrong guild ID (should be test guild, not 1510876414671323206) |

### 6.2B Rollback Trigger — Cutover (Phase 2 Steps 2.10-2.11)

Rollback after bot.py disabled and Hermes gateway is primary:

| Trigger Condition | How to Detect |
|---|---|
| **CRITICAL: HARD STOP doesn't work** | User sends "HARD STOP" → no neutral response, LLM still responds with persona |
| **CRITICAL: Messages not delivered** | User sends message → no response from Guinevere within 30 seconds |
| **CRITICAL: Safety feature regression** | Any Phase 1 safety test now fails via gateway |
| Response latency > 2x bot.py baseline | `hermes gateway status` → average latency > 2x pre-cutover |
| Error rate > 5% of messages | `hermes logs --level error` → error count > 5% of total messages |
| Budget consumption > 2x baseline | `hermes insights` → token spend > 2x pre-cutover rate |
| Discord rate limit (429) responses | `hermes logs` → contains "429 Too Many Requests" |
| Faiz manually requests rollback | "rollback gateway" or "kembalikan bot.py" in Discord |

### 6.3 Pre-Conditions

**For shadow mode rollback:**
- [ ] `hermes gateway status` shows gateway is running
- [ ] `guinevere-bot.service` is ACTIVE (bot.py is still primary)
- [ ] Shadow mode comparison data exists (48hr parity report)

**For cutover rollback:**
- [ ] `guinevere-bot.service` is STOPPED or DISABLED
- [ ] `hermes-gateway.service` is ACTIVE
- [ ] bot.py code is intact (not deleted, only disabled)
- [ ] Discord bot token is available (SOPS-decrypted from `secrets/discord-secrets.yaml`)
- [ ] Pre-Phase-2 git tag exists

### 6.4 Exact Commands — Shadow Mode Rollback

```bash
# === STEP 1: Universal kill-switch ===
hermes gateway stop

# === STEP 2: Remove Hermes gateway configuration ===
# Option A: Uninstall gateway (complete removal)
hermes gateway uninstall

# Option B: Just stop and disable (preserves config for retry)
hermes gateway stop
sudo systemctl disable hermes-gateway 2>/dev/null || true

# === VERIFY ===
hermes gateway status
# Expected: "Gateway not running" or "No Discord configured" (if uninstalled)

# === STEP 3: Confirm bot.py is handling traffic ===
sudo systemctl status guinevere-bot | grep "active (running)"
# Expected: "Active: active (running)"

# === VERIFY bot.py responds ===
# Send test message in Discord #guinevere-chat → Guinevere responds
```

### 6.5 Exact Commands — Cutover Rollback (Hermes → bot.py)

This is the most critical rollback in the entire migration. Zero user-visible downtime is the goal.

```bash
# === STEP 1: Universal kill-switch ===
hermes gateway stop

# === STEP 2: Immediate reactivation of bot.py ===
sudo systemctl start guinevere-bot

# === VERIFY bot.py started ===
sudo systemctl status guinevere-bot | grep "active (running)"
# Expected: "Active: active (running) since ..."

# === STEP 3: Disable Hermes gateway service (prevent auto-restart) ===
sudo systemctl stop hermes-gateway 2>/dev/null || true
sudo systemctl disable hermes-gateway 2>/dev/null || true

# === VERIFY Hermes gateway stopped ===
hermes gateway status
# Expected: Not running

# === STEP 4: Restore original slash command handler (if modified) ===
cd /home/guinevere/code/guinevere
git checkout -- src/discord/bot.py
git checkout -- src/discord/commands.py 2>/dev/null || true

# === VERIFY bot.py unchanged ===
git diff src/discord/bot.py
# Expected: No output (no changes)

# === STEP 5: Restart bot.py to pick up restored code ===
sudo systemctl restart guinevere-bot

# === VERIFY bot.py running with restored code ===
sudo systemctl status guinevere-bot | grep "active (running)"
# Expected: "Active: active (running)"

# === STEP 6 (OPTIONAL): Restore from pre-Phase-2 git tag if deeper rollback needed ===
cd /home/guinevere/code/guinevere
PRE_PHASE2_TAG=$(git tag | grep "pre-hermes-migration" | tail -1)
git checkout "$PRE_PHASE2_TAG" -- src/discord/
sudo systemctl restart guinevere-bot
```

### 6.6 Data Integrity Verification

```bash
# Phase 2 does not modify data. Conversation history was in Redis DB4 (bot.py) or Hermes session store.
# Neither is critical data. Verify primary stores:

sudo -u postgres psql -d guinevere -c "SELECT count(*) FROM memory.episodes"
# Expected: Same count as pre-Phase-2

redis-cli -p 6380 PING
# Expected: PONG
```

### 6.7 Service Restoration Order

```
Priority 1 (immediate, parallel):
  guinevere-bot.service    → START NOW (this restores Discord immediately)
  
Priority 2 (within 1 minute):
  hermes-gateway.service   → STOP + DISABLE

Priority 3 (verify):
  guinevere-core.service   → Check still running
```

### 6.8 Communication Plan

| Recipient | Message | Channel |
|---|---|---|
| Faiz | "Discord gateway rolled back to bot.py. Hermes gateway stopped and disabled. All 33 slash commands functional on bot.py. Downtime: [X] seconds." | Discord #guinevere-chat |
| Faiz (follow-up) | "Shadow mode comparison data preserved at [path]. Can be used to debug Hermes gateway issues before retry." | Discord #guinevere-chat |

### 6.9 Time Estimate

| Scenario | bot.py Already Disabled? | Time |
|---|---|---|
| Shadow mode rollback | No (bot.py still running) | **< 1 minute** |
| Cutover rollback | Yes (must restart bot.py) | **< 2 minutes** |
| Cutover rollback + git checkout | Yes | **< 3 minutes** |
| Cutover rollback + full git tag restore | Yes | **< 5 minutes** |

**Maximum downtime**: < 2 minutes from `hermes gateway stop` to `guinevere-bot` accepting Discord messages.

### 6.10 Post-Rollback Verification

```bash
# 1. bot.py is running and handling messages
sudo systemctl status guinevere-bot | grep "active (running)" && echo "PASS" || echo "FAIL"

# 2. HARD STOP works via bot.py
# Send "HARD STOP" in Discord → instant neutral response

# 3. All 33 slash commands functional
# Test: /status, /mood, /help → all respond correctly

# 4. Hermes gateway fully stopped
hermes gateway status 2>&1 | grep -qi "not running" && echo "PASS: gateway stopped" || echo "CHECK: gateway status"

# 5. Other services unaffected
sudo systemctl is-active guinevere-core guinevere-mcp guinevere-loops \
  guinevere-scheduler guinevere-surveillance guinevere-monitoring
# Expected: all "active"

# 6. Startup message appears in Discord
# Expected: "👑 Mommy sudah bangun, Darling." (or whatever startup message is configured)
```

### 6.11 Lessons Learned Capture

```markdown
# Phase 2 Rollback Log

## Trigger
[Cutover or shadow mode? What specific condition?]

## Downtime
[Actual seconds from gateway stop to bot.py responding]

## Root Cause
[Hermes gateway crash? Slash command not registered? Rate limiting? HARD STOP failure?]

## Shadow Mode Data
[Parity report preserved at: /home/guinevere/backups/shadow-mode-parity-*.md]

## Fix for Retry
[Adjust gateway config? Fix specific command? Increase rate limits? Fix hook priority?]

## Duration
[Actual rollback time vs estimate]

## Retry Plan
[Re-run shadow mode for N hours → fix identified issues → re-attempt cutover]
```

---

## 7. Phase 3 Rollback — Memory Bridge Enhancement

### Phase 3 Summary

| Attribute | Value |
|---|---|
| Duration | 2-3 days |
| Risk | MEDIUM — PostgreSQL is primary write authority, Hermes is read-only supplementary |
| Changes | Enable Hermes compression (read-only), enable session_search, simplify memory_bridge.py, configure Hermes memory → PostgreSQL |
| Data modified | **NONE** — PostgreSQL unchanged. Hermes memory is read-only supplementary |
| Services affected | memory_bridge.py (simplified to plugin) |
| Gate | Memory recall quality unchanged. DNR + classification enforcement verified. |

### 7.1 Rollback Trigger

| Trigger Condition | How to Detect |
|---|---|
| Memory recall quality drops (manual spot-check reveals irrelevant/unrelated memories) | Faiz manually reviews 5-10 queries: "Does this recall make sense?" |
| Hermes compression corrupts context (garbled or missing conversation history) | Review LLM responses for context-awareness: agent references wrong earlier messages |
| Hermes session_search returns incorrect cross-session data | Compare session_search results vs PostgreSQL direct query |
| DNR memory appears in Hermes recall paths | DNR test: mark memory DNR → verify excluded from session_search results |
| Classification ceiling breached via Hermes path | Classification test: query Critical data → must return nothing or sanitized_summary |
| Memory injection into Hermes context breaks LLM responses | LLM returns confused/contradictory responses referencing wrong memories |

### 7.2 Pre-Conditions

- [ ] Phase 2 rollback verified (or Phase 2 is still active with bot.py primary)
- [ ] PostgreSQL+pgvector is accessible and contains all data
- [ ] `memory_bridge.py` original (pre-simplification) is in git
- [ ] Pre-Phase-3 git tag exists
- [ ] Hermes gateway is running (if Phase 2 complete) or not running (if Phase 2 not yet done)

### 7.3 Exact Commands

```bash
# === STEP 1: Universal kill-switch ===
hermes gateway stop

# === STEP 2: Disable Hermes memory features (read-only, safe to disable) ===
# Disable compression
hermes config set memory.compression.enabled false 2>/dev/null || true

# Disable session search
hermes config set memory.session_search.enabled false 2>/dev/null || true

# === VERIFY Hermes memory disabled ===
hermes memory status 2>/dev/null
# Expected: Compression disabled, session_search disabled

# === STEP 3: Restore original memory_bridge.py from git ===
cd /home/guinevere/code/guinevere
git checkout -- src/hermes/memory_bridge.py

# === VERIFY memory_bridge.py restored ===
head -5 src/hermes/memory_bridge.py
# Expected: Original pre-Phase-3 content

# === STEP 4: Remove Hermes memory plugin files ===
rm -f plugins/memory_plugin.py 2>/dev/null || true

# === VERIFY plugin removed ===
ls plugins/memory_plugin.py 2>/dev/null && echo "WARNING: still exists" || echo "PASS: removed"

# === STEP 5: Restart affected services ===
sudo systemctl restart guinevere-core   # core loads memory_bridge

# === VERIFY core restarted ===
sudo systemctl status guinevere-core | grep "active (running)" && echo "PASS" || echo "FAIL"

# === STEP 6: Restart Hermes gateway if Phase 2 complete ===
# Only if you want Hermes gateway running WITHOUT memory features
hermes gateway start 2>/dev/null || true
```

### 7.4 Data Integrity Verification

**Critical**: Phase 3 is the only phase where the rollback's "no data loss" claim MUST be validated because memory is involved. However, because PostgreSQL is the primary write authority (Option C Hybrid), rollback is safe.

```bash
# === Primary verification: PostgreSQL data is intact ===
sudo -u postgres psql -d guinevere -c "
  SELECT 'episodes' as table_name, count(*) FROM memory.episodes
  UNION ALL SELECT 'semantic_facts', count(*) FROM memory.semantic_facts
  UNION ALL SELECT 'faiz_profile', count(*) FROM memory.faiz_profile
  UNION ALL SELECT 'emotional_events', count(*) FROM memory.emotional_events
  UNION ALL SELECT 'procedural_skills', count(*) FROM memory.procedural_skills
  ORDER BY table_name;
"
# Expected: Row counts match pre-Phase-3 values

# === Secondary verification: DNR flags intact ===
sudo -u postgres psql -d guinevere -c "
  SELECT count(*) FROM memory.episodes WHERE do_not_recall = true;
"
# Expected: DNR count matches pre-Phase-3

# === Classification integrity ===
sudo -u postgres psql -d guinevere -c "
  SELECT classification, count(*) FROM memory.episodes GROUP BY classification;
"
# Expected: Distribution matches pre-Phase-3

# === Hermes SQLite state (read-only, no writes expected) ===
# Check that Hermes didn't accidentally write to its own database
sqlite3 ~/.hermes/state.db "SELECT count(*) FROM sessions;" 2>/dev/null
# Expected: May have session data from Phase 2 if gateway was active — this is normal.
# The important thing is PostgreSQL is unchanged.
```

### 7.5 Service Restoration Order

```
1. guinevere-core.service       → RESTART (picks up restored memory_bridge.py)
2. hermes-gateway.service       → START (if Phase 2 complete, optional)
3. guinevere-bot.service        → Already running (if Phase 2 not cutover yet)
                                  or RESTART (if Phase 2 cutover needs reverting too)
```

### 7.6 Communication Plan

| Recipient | Message | Channel |
|---|---|---|
| Faiz | "Phase 3 memory bridge rolled back. Hermes compression and session_search disabled. Original memory_bridge.py restored. PostgreSQL data verified intact ([N] episodes, [M] facts). Memory recall quality restored to pre-Phase-3 baseline." | Discord #guinevere-chat |

### 7.7 Time Estimate

| Step | Time |
|---|---|
| `hermes gateway stop` | < 1 second |
| Hermes config changes | < 30 seconds |
| Git checkout + file removal | < 10 seconds |
| Service restart | < 10 seconds |
| PostgreSQL verification | < 30 seconds |
| **Total** | **< 3 minutes** |

### 7.8 Post-Rollback Verification

```bash
# 1. Memory recall via bot.py works normally
# Test: Ask Guinevere about something stored in memory → correct recall

# 2. DNR enforcement verified
# Test: Ask about DNR-marked memory → Guinevere should not recall it

# 3. Classification enforcement verified
# Test: Attempt to access Critical data → fail-closed or sanitized_summary

# 4. memory_bridge.py is original version
git diff src/hermes/memory_bridge.py
# Expected: No output (unchanged from git)

# 5. Hermes memory features disabled
hermes memory status 2>/dev/null | grep -E "compression|session_search"
# Expected: disabled or not mentioned

# 6. All services healthy
sudo systemctl is-active guinevere-core guinevere-bot
# Expected: both "active"
```

### 7.9 Lessons Learned Capture

```markdown
# Phase 3 Rollback Log

## Trigger
[Recall quality drop? Compression corruption? DNR leak?]

## Root Cause
[Specific Hermes memory feature that caused regression]

## PostgreSQL State
[Episode count before and after: N episodes, M semantic_facts — no change]

## Fix for Retry
[Adjust compression threshold? Disable specific Hermes feature? Tune session_search?]

## Duration
[Actual rollback time vs estimate]

## Retry Plan
[Re-enable single Hermes feature at a time, test for 24hr before enabling next]
```

---

## 8. Phase 4 Rollback — Tool/MCP Migration

### Phase 4 Summary

| Attribute | Value |
|---|---|
| Duration | 3-5 days |
| Risk | MEDIUM |
| Changes | Add 5 native Hermes MCP servers, build auth overlay plugin, migrate 9 tools to Hermes native, keep 7 custom |
| Data modified | None (config + plugin files only) |
| Services affected | `guinevere-mcp.service` (simplified), Hermes MCP servers |
| Gate | All 16 tool capabilities available. Auth matrix enforced. Security audit clean. |

### 8.1 Rollback Trigger

| Trigger Condition | How to Detect |
|---|---|
| Auth matrix bypass detected (tool executes without authorization) | Monitor auth overlay logs: any tool call without [AUTH] prefix |
| Hermes native tool behavior differs from Guinevere custom tool | Compare output: same input → different/wrong output |
| Tool isolation failure (path whitelist/command blocking breached) | Test: attempt forbidden operation → must be blocked |
| DESTRUCTIVE_APPROVAL fails (action executed without webhook approval) | Monitor: destructive action executes without Discord approval prompt |
| Auth overlay plugin crashes (all tool calls blocked) | User tries any command → "tool unavailable" response |
| Custom MCP servers fail after migration (postgres, redis, obscura, grep_app) | Test each custom tool: tool invocation fails |

### 8.2 Pre-Conditions

- [ ] Original `guinevere-mcp.service` with all 16 tools is functional (pre-Phase-4 state)
- [ ] Auth matrix plugin file at `plugins/auth_overlay.py` (if it was created)
- [ ] Original `src/mcp/manager.py` is in git
- [ ] Pre-Phase-4 git tag exists
- [ ] All custom MCP tools (postgres, redis, obscura_cdp, grep_app) verified functional

### 8.3 Exact Commands

```bash
# === STEP 1: Universal kill-switch ===
hermes gateway stop

# === STEP 2: Remove native Hermes MCP servers ===
# List currently added MCP servers
hermes mcp list 2>/dev/null

# Remove each native server added during Phase 4
hermes mcp remove web 2>/dev/null || true
hermes mcp remove filesystem 2>/dev/null || true
hermes mcp remove terminal 2>/dev/null || true
hermes mcp remove git 2>/dev/null || true
hermes mcp remove fetch 2>/dev/null || true

# === VERIFY MCP servers removed ===
hermes mcp list 2>/dev/null
# Expected: Empty or only custom servers remain

# === STEP 3: Remove auth overlay plugin ===
rm -f plugins/auth_overlay.py

# === VERIFY auth overlay removed ===
ls plugins/auth_overlay.py 2>/dev/null && echo "WARNING: still exists" || echo "PASS: removed"

# === STEP 4: Restore original MCP manager and tools from git ===
cd /home/guinevere/code/guinevere
git checkout -- src/mcp/manager.py
git checkout -- src/mcp/auth_matrix.py
git checkout -- src/mcp/tools/

# === VERIFY files restored ===
git diff src/mcp/
# Expected: No output (all files match git)

# === STEP 5: Restart Guinevere MCP service ===
sudo systemctl restart guinevere-mcp

# === VERIFY MCP service healthy ===
sudo systemctl status guinevere-mcp | grep "active (running)" && echo "PASS" || echo "FAIL"
curl -s http://localhost:8000/health | grep -q "ok" && echo "PASS: health check" || echo "FAIL: health check"

# === STEP 6: Verify all 16 tools available ===
# Test a few key tools
curl -s http://localhost:8000/tools/list 2>/dev/null || \
  echo "Test via bot.py: /status should show tools available"
```

### 8.4 Data Integrity Verification

```bash
# Phase 4 does not modify data. Verify all systems operational:
sudo -u postgres psql -d guinevere -c "SELECT 1" && echo "PASS" || echo "FAIL"
redis-cli -p 6380 PING && echo "PASS" || echo "FAIL"
```

### 8.5 Service Restoration Order

```
1. guinevere-mcp.service     → RESTART (picks up restored manager.py + tools)
2. guinevere-core.service    → Already running (should re-check health)
3. guinevere-bot.service     → Already running (if Phase 2 not cutover)
                                or START (if Phase 2 rollback was also needed)
```

### 8.6 Communication Plan

| Recipient | Message | Channel |
|---|---|---|
| Faiz | "Phase 4 MCP migration rolled back. All 16 tools restored to original FastMCP server. Hermes native MCP servers removed. Auth overlay plugin removed. guinevere-mcp.service restarted and healthy." | Discord #guinevere-chat |

### 8.7 Time Estimate

| Step | Time |
|---|---|
| `hermes gateway stop` | < 1 second |
| MCP server removal | < 30 seconds |
| Git checkout + file removal | < 15 seconds |
| Service restart + verification | < 30 seconds |
| **Total** | **< 2 minutes** |

### 8.8 Post-Rollback Verification

```bash
# 1. MCP service healthy with all tools
sudo systemctl status guinevere-mcp | grep "active (running)" && echo "PASS" || echo "FAIL"

# 2. Auth matrix enforced
# Test: Attempt DESTRUCTIVE_APPROVAL tool → Discord webhook prompt appears

# 3. All 16 tools accessible
# Test via bot.py: /status shows all tools, or send a message that triggers tool use

# 4. Hermes MCP servers fully removed
hermes mcp list 2>/dev/null | grep -v "^$" | wc -l
# Expected: 0 (no Hermes-native servers registered)

# 5. Custom MCP tools functional
# Test each: postgres query, redis PING, obscura status, grep_app search
```

### 8.9 Lessons Learned Capture

```markdown
# Phase 4 Rollback Log

## Trigger
[Auth matrix bypass? Tool behavior mismatch? Plugin crash?]

## Root Cause
[Specific Hermes MCP incompatibility or plugin bug]

## Tool Inventory
[Original 16 tools verified: brave_search, context7, exa_search, fetch, filesystem, 
 github, grep_app, obscura_cdp, sequential_thinking, time_tools, websearch, 
 git_tool, postgres_tool, redis_tool, shell_tool, docker_tool]

## Fix for Retry
[Fix specific tool migration? Adjust auth plugin? Skip problematic tool?]

## Duration
[Actual rollback time vs estimate]

## Retry Plan
[Migrate tools one at a time, test each for 24hr before migrating next]
```

---

## 9. Phase 5 Rollback — Skills & Persona

### Phase 5 Summary

| Attribute | Value |
|---|---|
| Duration | 2-3 days |
| Risk | LOW |
| Changes | Search/install skills from agentskills.io, customize SOUL.md, mood/ritual/punishment/reward plugins, hermes curator |
| Data modified | None (skills are files, SOUL.md is a markdown file) |
| Services affected | None directly (plugins loaded by Hermes, not systemd services) |
| Gate | All persona features functional. Mood persistence verified. Rituals fire on schedule. |

### 5.1 Rollback Trigger

| Trigger Condition | How to Detect |
|---|---|
| Persona drift detected (SOUL.md changes alter Guinevere's identity/tone) | drift_detector alerts: SOUL.md SHA-256 hash differs from baseline |
| Installed skill causes unexpected behavior | Agent behaves differently after skill installation (tool use changes, tone shifts) |
| Mood/ritual plugin conflicts with existing persona code | Multiple mood engines firing → contradictory behavior |
| Punishment/reward plugin fires incorrectly | Unexpected L-level or T-level changes without corresponding user action |
| hermes curator breaks skill management | `hermes skills list` fails or shows corrupted skill states |

### 5.2 Pre-Conditions

- [ ] Original Guinevere persona code intact (unchanged in git): `src/persona/*`
- [ ] Pre-Phase-5 git tag exists
- [ ] bot.py still handles persona features via original code
- [ ] Hermes gateway is running (if Phase 2 complete) or not running

### 5.3 Exact Commands

```bash
# === STEP 1: Universal kill-switch ===
hermes gateway stop

# === STEP 2: Remove installed skills ===
# List installed skills
hermes skills list 2>/dev/null

# Uninstall each skill installed during Phase 5
hermes skills uninstall safety 2>/dev/null || true
hermes skills uninstall persona 2>/dev/null || true
# Repeat for each skill installed

# === VERIFY skills removed ===
hermes skills list 2>/dev/null | grep -c "installed"
# Expected: 0 or only pre-existing

# === STEP 3: Revert SOUL.md to pre-Phase-5 state ===
cd /home/guinevere/code/guinevere
git checkout -- config/hermes/SOUL.md 2>/dev/null || \
  rm -f ~/.hermes/SOUL.md

# === VERIFY SOUL.md restored/removed ===
cat ~/.hermes/SOUL.md 2>/dev/null && echo "Restored from git" || echo "Removed"

# === STEP 4: Remove persona plugins ===
rm -f plugins/mood_plugin.py
rm -f plugins/ritual_plugin.py
rm -f plugins/punishment_plugin.py
rm -f plugins/reward_plugin.py
rm -f plugins/streak_plugin.py
rm -f plugins/persona_plugin.py

# === VERIFY plugins removed ===
ls plugins/*.py 2>/dev/null && echo "WARNING: plugins/ still contains files" || echo "PASS: empty"
```

### 5.4 Data Integrity Verification

```bash
# Phase 5 does not modify data. Verify persona data intact:
sudo -u postgres psql -d guinevere -c "
  SELECT count(*) FROM persona.mood_states;
  SELECT count(*) FROM persona.drift_log;
"
# Expected: Same counts as pre-Phase-5

redis-cli -p 6380 PING && echo "PASS" || echo "FAIL"
```

### 5.5 Service Restoration Order

```
No services were affected. Skip this step.
```

### 5.6 Communication Plan

| Recipient | Message | Channel |
|---|---|---|
| Faiz | "Phase 5 skills/persona rolled back. All installed skills removed. SOUL.md reverted. Persona plugins removed. Original persona code intact." | Discord #guinevere-chat |

### 5.7 Time Estimate

| Step | Time |
|---|---|
| `hermes gateway stop` | < 1 second |
| Skill removal (hermes skills uninstall) | < 1 minute |
| Git checkout + file removal | < 15 seconds |
| **Total** | **< 2 minutes** |

### 5.8 Post-Rollback Verification

```bash
# 1. Persona behavior unchanged
# Test: Ask Guinevere a personal question → response matches pre-Phase-5 tone

# 2. Mood engine functional (original code)
# Test: /mood command → shows current mood from src/persona/mood_engine.py

# 3. Ritual scheduler fires correctly (original APScheduler)
# Wait for next ritual time → verify ritual message appears

# 4. No drift detection alerts
# Monitor logs: no [DRIFT] entries after rollback

# 5. Hermes skills clean
hermes skills list 2>/dev/null
# Expected: No Guinevere-specific skills installed
```

### 5.9 Lessons Learned Capture

```markdown
# Phase 5 Rollback Log

## Trigger
[Persona drift? Skill conflict? Plugin malfunction?]

## Root Cause
[Specific skill or plugin that caused regression]

## Fix for Retry
[Skip problematic skill? Adjust SOUL.md? Fix plugin?]

## Duration
[Actual rollback time vs estimate]

## Retry Plan
[Install skills one at a time, test persona behavior for 24hr between each]
```

---

## 10. Phase 6 Rollback — LLM Routing & Budget

### Phase 6 Summary

| Attribute | Value |
|---|---|
| Duration | 1 day |
| Risk | LOW — 9Router unchanged, Hermes is just a client config |
| Changes | `hermes model set`, `hermes fallback set`, `hermes config set budget.*` |
| Data modified | None (config only) |
| Services affected | None (Hermes uses 9Router; 9Router itself is unchanged) |
| Gate | LLM routing functional. Fallback works. Budget enforced. Cost tracking accurate. |

### 6.1 Rollback Trigger

| Trigger Condition | How to Detect |
|---|---|
| Hermes LLM calls fail (can't reach 9Router) | `hermes --verbose run` → connection errors to localhost:20128 |
| Budget enforcement blocks legitimate requests (false positive) | Agent can't respond because budget cap hit → but actual spend is under $30 |
| Budget enforcement doesn't block (false negative) | Spend exceeds $30/mo without alerts |
| Fallback doesn't activate when primary model is down | Kill primary model → no fallback, just errors |
| Cost tracking diverges from cost_tracker.py numbers | Compare `hermes insights` numbers vs PostgreSQL cost_tracker data → >10% difference |

### 6.2 Pre-Conditions

- [ ] 9Router is running at localhost:20128 (unchanged throughout)
- [ ] cost_tracker.py numbers are available in PostgreSQL for comparison
- [ ] Hermes LLM config was working before Phase 6 (using default config)
- [ ] Pre-Phase-6 git tag exists

### 6.3 Exact Commands

```bash
# === STEP 1: Universal kill-switch ===
hermes gateway stop

# === STEP 2: Revert Hermes LLM config ===
# Reset model to default/last-known-good
hermes model set --model default 2>/dev/null || true

# Reset fallback
hermes fallback set --model none 2>/dev/null || true

# Reset budget limits
hermes config set budget.monthly_limit 0 2>/dev/null || true
hermes config set budget.alert_threshold 0 2>/dev/null || true

# === VERIFY Hermes config reset ===
hermes model show 2>/dev/null
# Expected: Shows default model (or error if not configured)
hermes config show budget 2>/dev/null
# Expected: monthly_limit unset or 0

# === STEP 3: Restore session_adapter.py LLM config (if modified) ===
cd /home/guinevere/code/guinevere
git checkout -- src/hermes/session_adapter.py

# === VERIFY session_adapter restored ===
git diff src/hermes/session_adapter.py
# Expected: No output

# === STEP 4: Verify 9Router is still fully functional ===
curl -s http://localhost:20128/health 2>/dev/null && echo "PASS: 9Router healthy" || echo "CHECK: 9Router"
# Expected: 9Router health response

# === STEP 5: Restart core service to pick up session_adapter changes ===
sudo systemctl restart guinevere-core

# === VERIFY core restarted ===
sudo systemctl status guinevere-core | grep "active (running)" && echo "PASS" || echo "FAIL"
```

### 6.4 Data Integrity Verification

```bash
# Phase 6 does not modify data. LLM routing is config-only.
sudo -u postgres psql -d guinevere -c "SELECT 1" && echo "PASS" || echo "FAIL"

# Cost tracking data intact
redis-cli -p 6380 -n 5 KEYS "cost:*" | head -5
# Expected: Shows existing cost tracking keys (if any)
```

### 6.5 Service Restoration Order

```
1. guinevere-core.service   → RESTART (picks up restored session_adapter.py)
2. hermes-gateway.service   → START (if Phase 2 complete, with default LLM config)
```

### 6.6 Communication Plan

| Recipient | Message | Channel |
|---|---|---|
| Faiz | "Phase 6 LLM routing rolled back. Hermes model/fallback/budget config reset. session_adapter.py restored to pre-Phase-6 state. 9Router verified healthy. Cost tracking in PostgreSQL unchanged." | Discord #guinevere-chat |

### 6.7 Time Estimate

| Step | Time |
|---|---|
| `hermes gateway stop` | < 1 second |
| Hermes config resets | < 30 seconds |
| Git checkout + service restart | < 15 seconds |
| **Total** | **< 2 minutes** |

### 6.8 Post-Rollback Verification

```bash
# 1. 9Router healthy
curl -s http://localhost:20128/health && echo "PASS" || echo "FAIL"

# 2. LLM calls still work via bot.py
# Test: Send message in Discord → Guinevere responds (GPT-5.5 via 9Router)

# 3. Cost tracking still works (cost_tracker.py)
# Check Redis DB5 for cost data continuity

# 4. Hermes LLM config clean
hermes model show 2>/dev/null
hermes config show budget 2>/dev/null
```

### 6.9 Lessons Learned Capture

```markdown
# Phase 6 Rollback Log

## Trigger
[LLM calls failing? Budget misbehaving? Fallback not working?]

## Root Cause
[Specific Hermes config value or model routing issue]

## Fix for Retry
[Adjust model endpoint? Fix budget calculation? Test fallback path?]

## Duration
[Actual rollback time vs estimate]

## Retry Plan
[Re-apply config one setting at a time, verify LLM response quality between each]
```

---

## 11. Phase 7 Rollback — Hardening & Monitoring

### Phase 7 Summary

| Attribute | Value |
|---|---|
| Duration | 2-3 days |
| Risk | LOW |
| Changes | `hermes cron`, `hermes logs`, `hermes backup` config, `hermes checkpoints` config, runbook, performance benchmark |
| Data modified | None (config + documentation only) |
| Services affected | Monitoring stack (Prometheus/Grafana/Loki — unchanged), new cron jobs |
| Gate | All monitoring active. Security clean. Doctor clean. Runbook complete. Performance acceptable. |

### 7.1 Rollback Trigger

| Trigger Condition | How to Detect |
|---|---|
| `hermes cron` jobs conflict with existing APScheduler jobs | Two schedulers fire same job → duplicate rituals, duplicate consolidation |
| `hermes logs` monitoring consumes excessive disk | `df -h` → log partition filling rapidly |
| `hermes backup` interferes with existing backup system (S3 + R2 via rclone) | Two backup systems writing to same files → corruption or conflicts |
| `hermes checkpoints` disk space excessive | Checkpoint directory grows beyond expected size |
| Performance benchmark shows >10% regression | Compare `hermes gateway status` latency vs pre-Phase-7 bot.py baseline |

### 7.2 Pre-Conditions

- [ ] Phases 2-6 are complete and verified (Hermes is operational)
- [ ] Existing monitoring stack (Prometheus/Grafana/Loki) is functional
- [ ] Existing backup system (rclone → S3 + R2) is functional
- [ ] Performance baseline data exists (bot.py latency numbers)
- [ ] Pre-Phase-7 git tag exists

### 7.3 Exact Commands

```bash
# === STEP 1: Universal kill-switch ===
hermes gateway stop

# === STEP 2: Disable Hermes cron jobs ===
hermes cron disable --all 2>/dev/null || true
hermes cron remove --all 2>/dev/null || true

# === VERIFY cron disabled ===
hermes cron list 2>/dev/null
# Expected: No active cron jobs

# === STEP 3: Disable Hermes backup/checkpoint scheduling ===
# Hermes backup and checkpoints are manual commands — no scheduling to disable.
# Just ensure they don't conflict with rclone backup system.
hermes config set backup.enabled false 2>/dev/null || true

# === VERIFY Hermes backup disabled ===
hermes config show backup 2>/dev/null
# Expected: enabled: false

# === STEP 4: Restore APScheduler config (ensure original scheduler is primary) ===
cd /home/guinevere/code/guinevere
git checkout -- src/persona/ritual_scheduler.py
git checkout -- src/memory/consolidation_job.py 2>/dev/null || true

# === VERIFY APScheduler files restored ===
git diff src/persona/ritual_scheduler.py
# Expected: No output

# === STEP 5: Restart scheduler service ===
sudo systemctl restart guinevere-scheduler

# === VERIFY scheduler restarted ===
sudo systemctl status guinevere-scheduler | grep "active (running)" && echo "PASS" || echo "FAIL"
```

### 7.4 Data Integrity Verification

```bash
# Phase 7 does not modify data. Verify all systems:
sudo -u postgres psql -d guinevere -c "SELECT 1" && echo "PASS" || echo "FAIL"
redis-cli -p 6380 PING && echo "PASS" || echo "FAIL"

# Existing monitoring stack intact
curl -s http://localhost:9090/-/healthy && echo "PASS: Prometheus" || echo "CHECK: Prometheus"
curl -s http://localhost:3000/api/health && echo "PASS: Grafana" || echo "CHECK: Grafana"

# Existing backup system intact
rclone ls idcloudhost:guinevere-dr-backups/ | head -3
# Expected: Existing backup files visible
```

### 7.5 Service Restoration Order

```
1. guinevere-scheduler.service → RESTART (picks up restored APScheduler config)
2. hermes-gateway.service       → START (if Phase 2 complete)
```

### 7.6 Communication Plan

| Recipient | Message | Channel |
|---|---|---|
| Faiz | "Phase 7 hardening rolled back. Hermes cron/backup disabled. Original APScheduler restored. guinevere-scheduler.service restarted. Monitoring stack and existing backup system verified intact." | Discord #guinevere-chat |

### 7.7 Time Estimate

| Step | Time |
|---|---|
| `hermes gateway stop` | < 1 second |
| Hermes cron/backup disable | < 30 seconds |
| Git checkout + service restart | < 15 seconds |
| **Total** | **< 2 minutes** |

### 7.8 Post-Rollback Verification

```bash
# 1. Original APScheduler jobs fire correctly
# Wait for next scheduled job → verify it fires (ritual, consolidation, cost report)

# 2. No duplicate jobs
sudo systemctl list-timers | grep guinevere
# Expected: Only pre-existing timers

# 3. Monitoring stack healthy
sudo systemctl is-active guinevere-monitoring && echo "PASS" || echo "FAIL"

# 4. Backup system functional
rclone about idcloudhost:guinevere-dr-backups/ 2>/dev/null || rclone ls idcloudhost:guinevere-dr-backups/ | head -1
# Expected: Backup storage accessible

# 5. Disk space normal (no log explosion)
df -h /var/log/
# Expected: Usage within normal range
```

### 7.9 Lessons Learned Capture

```markdown
# Phase 7 Rollback Log

## Trigger
[Cron conflict? Log disk fill? Backup conflict? Performance regression?]

## Root Cause
[Specific Hermes feature that caused issue]

## Fix for Retry
[Disable specific cron? Adjust log retention? Separate backup targets?]

## Duration
[Actual rollback time vs estimate]

## Retry Plan
[Enable Hermes features one at a time, monitor for 24hr before enabling next]
```

---

## 12. Global Emergency Rollback

### 12.1 Purpose

Single procedure to revert ALL phases at once, restoring the system to pre-migration state. Use when:
- Multiple phases have failed simultaneously
- Root cause is unclear and time is critical
- Faiz invokes full rollback ("kembalikan semua ke bot.py")

### 12.2 Global Rollback Trigger

| Trigger Condition | How to Detect |
|---|---|
| Multiple safety features fail simultaneously | 3+ Phase 1 safety tests fail |
| Discord completely unreachable | No response from Guinevere > 5 minutes |
| Budget spike (cost > 5x baseline) | `hermes insights` or cost_tracker shows massive spend |
| Faiz invokes emergency rollback | "rollback all" / "kembalikan semua" / "emergency rollback" in Discord |
| Hermes gateway crashes repeatedly with unrecoverable errors | `hermes gateway status` → crash loop (>3 restarts in 5 minutes) |

### 12.3 Pre-Conditions

- [ ] Pre-migration snapshot exists (Section 3): git tag, pg_dump, pip freeze, systemd state
- [ ] `guinevere-bot.service` systemd unit file is intact (not deleted)
- [ ] Discord bot token is available (SOPS-decrypted from `secrets/discord-secrets.yaml`)
- [ ] Faiz is available to verify Discord functionality after rollback

### 12.4 Exact Commands — Full Global Rollback

```bash
# ╔══════════════════════════════════════════════════════════════╗
# ║     GLOBAL EMERGENCY ROLLBACK — ALL PHASES AT ONCE          ║
# ║     Estimated downtime: < 5 minutes                         ║
# ╚══════════════════════════════════════════════════════════════╝

# === STEP 1: Universal kill-switch ===
hermes gateway stop
echo "STEP 1: Hermes gateway stopped"

# === STEP 2: Stop and disable all Hermes services ===
sudo systemctl stop hermes-gateway 2>/dev/null || true
sudo systemctl disable hermes-gateway 2>/dev/null || true
echo "STEP 2: Hermes gateway service stopped + disabled"

# === STEP 3: Restore ALL code from pre-migration git tag ===
cd /home/guinevere/code/guinevere
PRE_TAG=$(git tag | grep "pre-hermes-migration" | tail -1)
if [ -n "$PRE_TAG" ]; then
    git checkout "$PRE_TAG" -- .
else
    # Fallback: restore known critical files
    git checkout -- src/discord/bot.py src/discord/conversational_handler.py
    git checkout -- src/hermes/session_adapter.py src/hermes/memory_bridge.py
    git checkout -- src/mcp/ src/persona/ src/core/
    git checkout -- plugins/ 2>/dev/null || rm -rf plugins/
fi
echo "STEP 3: Code restored from $PRE_TAG"

# === STEP 4: Remove all Phase 1-7 created files ===
rm -rf plugins/
rm -f config/hermes/hooks.yaml config/hermes/mcp-servers.yaml
rm -f ~/.hermes/SOUL.md
# Preserve config.yaml and .env (needed for Hermes CLI to function)
echo "STEP 4: Migration artifacts removed"

# === STEP 5: Revert Hermes config changes ===
hermes config set memory.compression.enabled false 2>/dev/null || true
hermes config set memory.session_search.enabled false 2>/dev/null || true
hermes config set backup.enabled false 2>/dev/null || true
hermes model set --model default 2>/dev/null || true
hermes fallback set --model none 2>/dev/null || true
hermes config set budget.monthly_limit 0 2>/dev/null || true
hermes cron disable --all 2>/dev/null || true
echo "STEP 5: Hermes config reverted"

# === STEP 6: Restore pip packages (if Phase 0 changed them) ===
cd /home/guinevere/code/guinevere
PIP_FREEZE=$(ls -t /home/guinevere/backups/pre-migration-pip-*.txt 2>/dev/null | head -1)
if [ -n "$PIP_FREEZE" ]; then
    ./.venv/bin/pip install -r "$PIP_FREEZE" 2>/dev/null
    echo "STEP 6: Pip packages restored from $PIP_FREEZE"
else
    echo "STEP 6: No pip freeze snapshot found — skipping"
fi

# === STEP 7: Restart all Guinevere services ===
sudo systemctl restart guinevere-core
sudo systemctl restart guinevere-bot
sudo systemctl restart guinevere-mcp
sudo systemctl restart guinevere-loops
sudo systemctl restart guinevere-scheduler
sudo systemctl restart guinevere-surveillance
sudo systemctl restart guinevere-monitoring
echo "STEP 7: All Guinevere services restarted"

# === STEP 8: Wait for services to stabilize ===
sleep 5

# === STEP 9: Verify critical services ===
echo ""
echo "=== GLOBAL ROLLBACK VERIFICATION ==="
echo ""

echo "--- Service Status ---"
for svc in guinevere-bot guinevere-core guinevere-mcp guinevere-loops \
           guinevere-scheduler guinevere-surveillance guinevere-monitoring; do
    STATUS=$(sudo systemctl is-active "$svc" 2>/dev/null)
    echo "  $svc: $STATUS"
done

echo ""
echo "--- Hermes Status ---"
hermes gateway status 2>/dev/null || echo "  Gateway: not running (expected)"

echo ""
echo "--- Code Integrity ---"
cd /home/guinevere/code/guinevere
git status --short | head -10
echo "  (Expect: clean or only backup files modified)"

echo ""
echo "--- Data Integrity ---"
sudo -u postgres psql -d guinevere -c "SELECT 'episodes' as tbl, count(*) FROM memory.episodes" -t 2>/dev/null
redis-cli -p 6380 PING 2>/dev/null && echo "  Redis: PONG" || echo "  Redis: CHECK"

echo ""
echo "=== GLOBAL ROLLBACK COMPLETE ==="
echo "Verify: Send 'HARD STOP' in Discord #guinevere-chat"
echo "Verify: Send '/status' in Discord #guinevere-chat"
```

### 12.5 Data Integrity Verification

```bash
# === CRITICAL: PostgreSQL data must be verified ===
sudo -u postgres psql -d guinevere -c "
  SELECT 'episodes' as tbl, count(*) FROM memory.episodes
  UNION ALL SELECT 'semantic_facts', count(*) FROM memory.semantic_facts
  UNION ALL SELECT 'mood_states', count(*) FROM persona.mood_states
  UNION ALL SELECT 'drift_log', count(*) FROM persona.drift_log
  UNION ALL SELECT 'episodes_dnr', count(*) FROM memory.episodes WHERE do_not_recall = true
  ORDER BY tbl;
"
# Compare counts with pre-migration snapshot values

# === Redis verification ===
redis-cli -p 6380 PING
redis-cli -p 6380 -n 4 KEYS "hermes:session:*" | wc -l
# Expected: Session keys may exist (bot.py uses DB4) — normal
```

### 12.6 Service Restoration Order

```
All Guinevere services restarted simultaneously in Step 7.
Order within the restart block doesn't matter because:
- guinevere-core must start before guinevere-bot (bot depends on core API)
Systemd handles dependency ordering if unit files have After=/Requires=.
If not, restart order: core → mcp → bot → loops → scheduler → surveillance → monitoring
```

### 12.7 Communication Plan

| Recipient | Message | Channel |
|---|---|---|
| Faiz | "GLOBAL EMERGENCY ROLLBACK COMPLETE. All phases reverted to pre-migration state. bot.py active with all 33 slash commands. Hermes gateway stopped and disabled. PostgreSQL data verified intact. Please verify: (1) HARD STOP works, (2) /status responds, (3) persona behaves normally." | Discord #guinevere-chat |
| Faiz (follow-up) | "Rollback log saved to /home/guinevere/backups/global-rollback-YYYYMMDD-HHMMSS.log. Full system snapshot at pre-migration git tag [TAG_NAME]." | Discord #guinevere-chat |

### 12.8 Time Estimate

| Step | Time |
|---|---|
| `hermes gateway stop` | < 1 second |
| Stop/disable Hermes services | < 5 seconds |
| Git checkout (restore all files) | < 30 seconds |
| File cleanup (rm -rf) | < 5 seconds |
| Hermes config reverts | < 30 seconds |
| Pip restore (if needed) | < 2 minutes |
| Service restarts | < 30 seconds |
| Wait + verification | < 30 seconds |
| **Total** | **< 5 minutes** |

**Maximum downtime**: < 5 minutes from `hermes gateway stop` to bot.py accepting Discord messages.

### 12.9 Post-Rollback Verification

```bash
# 1. bot.py fully functional
sudo systemctl status guinevere-bot | grep "active (running)" && echo "PASS" || echo "FAIL"

# 2. HARD STOP works
# Send "HARD STOP" in Discord → neutral response, no LLM call

# 3. All 33 slash commands functional
# Test: /status, /mood, /help

# 4. Persona behavior normal
# Send a casual message → Guinevere responds with expected persona

# 5. Memory recall works
# Ask about something stored in memory → correct recall

# 6. All services green
sudo systemctl is-active guinevere-bot guinevere-core guinevere-mcp \
  guinevere-loops guinevere-scheduler guinevere-surveillance guinevere-monitoring

# 7. Hermes fully disengaged
hermes gateway status 2>&1 | grep -qi "not running" && echo "PASS" || echo "CHECK"

# 8. No migration artifacts
ls plugins/ 2>/dev/null && echo "WARNING" || echo "PASS: plugins/ removed"
```

---

## 13. Partial Rollback — Single Phase Without Affecting Others

### 13.1 Independence Matrix

Not all phases can be rolled back independently. This matrix shows which phases are safe to roll back solo:

| Phase | Can Rollback Solo? | Conditions |
|---|---|---|
| Phase 0 | ✅ Yes | No dependencies on Phase 0 changes (packages are backward-compatible by design) |
| Phase 1 | ✅ Yes | Only if Hermes gateway is NOT running (Phase 2 not yet cutover). If Phase 2 is active, rollback Phase 2 first. |
| Phase 2 | ✅ Yes | This phase can ALWAYS be rolled back — bot.py is always the fallback. |
| Phase 3 | ✅ Yes | PostgreSQL is primary write authority. Hermes memory features are read-only. Safe to disable. |
| Phase 4 | ✅ Yes | Custom MCP server is always available. Hermes native MCP removal doesn't affect other phases. |
| Phase 5 | ✅ Yes | Skills are isolated files. No dependency from other phases on installed skills. |
| Phase 6 | ⚠️ Conditional | If Phase 2+ is active (Hermes gateway running), Hermes needs LLM config to function. Rollback means Hermes gateway uses default config — may cause LLM call failures. Better: re-apply known-good config instead of full rollback. |
| Phase 7 | ✅ Yes | Cron/backup are standalone features. Can disable without affecting core functionality. |
| Phases 2+6 together | ❌ No | Must roll back Phase 2 first (gateway), then Phase 6 (LLM config). Gateway needs LLM to function. |

### 13.2 Safe Partial Rollback Pattern

```bash
# Template for any single-phase rollback:

# 1. Identify phase dependencies
#    Is this phase depended on by later phases?
#    Example: Rolling back Phase 1 when Phase 2-7 are active:
#    → Phase 1 safety hooks are used by Phase 2 gateway. Must rollback Phase 2 first.

# 2. Execute phase-specific rollback (Sections 4-11 above)
#    Each section is self-contained and can run independently

# 3. Re-verify dependent phases
#    After rolling back Phase N, check if Phases N+1 through 7 still work

# 4. If dependent phase breaks, roll it back too
#    Follow the dependency chain: Phase 2 depends on Phase 1, Phase 3 depends on Phase 2, etc.
```

### 13.3 Example: Rolling Back Only Phase 3 (Memory) When Phase 4-7 Are Active

```bash
# Phase 3 rollback is safe because:
# - PostgreSQL is primary write authority (Phase 4-7 tools don't depend on Hermes memory)
# - Hermes compression/session_search are read-only supplements
# - Disabling them doesn't affect tool/MCP operations (Phase 4) or skills/persona (Phase 5)

hermes gateway stop
hermes config set memory.compression.enabled false
hermes config set memory.session_search.enabled false
git checkout -- src/hermes/memory_bridge.py
rm -f plugins/memory_plugin.py
sudo systemctl restart guinevere-core
hermes gateway start   # Restart gateway with memory features disabled
```

---

## 14. Data Recovery — PostgreSQL Restore Procedure

### 14.1 When to Use This

Use ONLY if Hermes accidentally wrote to PostgreSQL during migration. This should NEVER happen because the hybrid architecture (Option C) keeps PostgreSQL as primary write authority and Hermes memory as read-only supplement. But if it does:

### 14.2 Trigger Conditions

| Trigger | Detection |
|---|---|
| Unexpected rows in PostgreSQL tables | Compare row counts before/after each phase |
| Hermes session data in wrong schema | Query `memory.episodes` for unexpected session_id patterns |
| Classification field corrupted (wrong values) | Query `SELECT DISTINCT classification FROM memory.episodes` → unexpected values |
| DNR flag reversed (memories incorrectly marked/unmarked) | Query `SELECT count(*) FROM memory.episodes WHERE do_not_recall = true` → count changed |

### 14.3 Pre-Conditions

- [ ] Pre-migration `pg_dump` file exists at `/home/guinevere/backups/pre-migration-*.dump`
- [ ] The dump file is uncorrupted: `pg_restore --list /home/guinevere/backups/pre-migration-*.dump | head`
- [ ] Offsite copies verified (idcloudhost S3 + Cloudflare R2)
- [ ] ALL Hermes gateway processes are stopped (`hermes gateway stop`)
- [ ] `guinevere-bot.service` is stopped (prevents new writes during restore)
- [ ] Faiz has approved the restore (destructive operation)

### 14.4 Exact Commands — Full Database Restore

```bash
# ╔══════════════════════════════════════════════════════════════╗
# ║     POSTGRESQL FULL RESTORE — DESTRUCTIVE OPERATION         ║
# ║     Estimated downtime: 10-30 minutes (depends on DB size)  ║
# ╚══════════════════════════════════════════════════════════════╝

# === STEP 0: STOP EVERYTHING ===
hermes gateway stop
sudo systemctl stop guinevere-bot guinevere-core guinevere-loops \
  guinevere-mcp guinevere-scheduler guinevere-surveillance

# === VERIFY all stopped ===
sudo systemctl is-active guinevere-bot guinevere-core
# Expected: both "inactive"

# === STEP 1: Create emergency backup (capture current state before restore) ===
sudo -u postgres pg_dump -Fc guinevere > /home/guinevere/backups/emergency-pre-restore-$(date +%Y%m%d-%H%M%S).dump

# === VERIFY emergency backup ===
ls -lh /home/guinevere/backups/emergency-pre-restore-*.dump
# Expected: File size > 0

# === STEP 2: Drop and recreate database ===
sudo -u postgres psql -c "DROP DATABASE IF EXISTS guinevere;"
sudo -u postgres psql -c "CREATE DATABASE guinevere OWNER guinevere_core;"

# === VERIFY database recreated ===
sudo -u postgres psql -d guinevere -c "SELECT current_database();"
# Expected: guinevere

# === STEP 3: Re-enable extensions ===
sudo -u postgres psql -d guinevere -c "CREATE EXTENSION IF NOT EXISTS vector;"
sudo -u postgres psql -d guinevere -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"

# === VERIFY extensions ===
sudo -u postgres psql -d guinevere -c "SELECT extname FROM pg_extension;"
# Expected: vector, timescaledb

# === STEP 4: Restore from pre-migration dump ===
DUMP_FILE=$(ls -t /home/guinevere/backups/pre-migration-*.dump | head -1)
sudo -u postgres pg_restore -d guinevere -v "$DUMP_FILE"

# === VERIFY restore complete ===
echo $?
# Expected: 0 (success)

# === STEP 5: Verify data integrity ===
sudo -u postgres psql -d guinevere -c "
  SELECT schemaname, count(*) as table_count 
  FROM pg_tables 
  WHERE schemaname IN ('memory','persona','surveillance','financial','projects','social','agents','consent','security','audit','ops','extensions')
  GROUP BY schemaname 
  ORDER BY schemaname;
"
# Expected: All 12 schemas present with expected table counts

# === STEP 6: Verify critical row counts ===
sudo -u postgres psql -d guinevere -c "
  SELECT 'episodes' as tbl, count(*) FROM memory.episodes
  UNION ALL SELECT 'semantic_facts', count(*) FROM memory.semantic_facts
  UNION ALL SELECT 'mood_states', count(*) FROM persona.mood_states
  UNION ALL SELECT 'drift_log', count(*) FROM persona.drift_log
  ORDER BY tbl;
"
# Compare with pre-migration snapshot values — must match exactly

# === STEP 7: Restart all services ===
sudo systemctl start guinevere-core
sleep 3
sudo systemctl start guinevere-bot guinevere-mcp guinevere-loops \
  guinevere-scheduler guinevere-surveillance guinevere-monitoring

# === VERIFY all services running ===
for svc in guinevere-bot guinevere-core guinevere-mcp guinevere-loops \
           guinevere-scheduler guinevere-surveillance guinevere-monitoring; do
    STATUS=$(sudo systemctl is-active "$svc")
    echo "$svc: $STATUS"
done
```

### 14.5 Selective Table Restore (If Only Specific Tables Affected)

```bash
# === Restore only memory.episodes table ===
DUMP_FILE=$(ls -t /home/guinevere/backups/pre-migration-*.dump | head -1)
sudo -u postgres pg_restore -d guinevere -t memory.episodes --data-only -v "$DUMP_FILE"

# === Restore only persona.mood_states table ===
sudo -u postgres pg_restore -d guinevere -t persona.mood_states --data-only -v "$DUMP_FILE"

# === Restore entire memory schema ===
sudo -u postgres pg_restore -d guinevere -n memory --data-only -v "$DUMP_FILE"
```

### 14.6 Time Estimate

| Scenario | DB Size | Time |
|---|---|---|
| Small (< 100MB) | Typical for Guinevere | **< 5 minutes** |
| Medium (100MB-1GB) | After months of operation | **< 15 minutes** |
| Large (> 1GB) | After years of operation | **< 30 minutes** |
| Selective table restore | Any size | **< 2 minutes** |

### 14.7 Communication Plan

| Recipient | Message | Channel |
|---|---|---|
| Faiz (before) | "DATABASE RESTORE REQUIRED. Hermes appears to have written unexpected data to PostgreSQL. Stopping all services. Emergency backup created. Proceeding with full restore from pre-migration dump [FILENAME]. Downtime estimated: [X] minutes." | Discord #guinevere-chat |
| Faiz (after) | "Database restore complete. All 12 schemas verified. Service restored. Please verify: (1) /status works, (2) memory recall correct, (3) persona behavior normal." | Discord #guinevere-chat |

---

## 15. Discord Cutover Rollback — Hermes Gateway → bot.py

### 15.1 Zero-Visible-Downtime Procedure

This is a dedicated section because the Discord cutover is the single highest-risk operation in the entire migration. The goal is **zero user-visible downtime** — Faiz should not notice the switch.

### 15.2 The Cutover State

```
BEFORE CUTOVER:
  guinevere-bot.service    ACTIVE    ← handling Discord
  hermes-gateway.service   ACTIVE    ← shadow mode (receiving copies)

AFTER CUTOVER (Phase 2 Step 11):
  guinevere-bot.service    STOPPED   ← disabled
  hermes-gateway.service   ACTIVE    ← primary Discord handler
```

### 15.3 Rollback Procedure (Cutover → bot.py)

```bash
# ╔══════════════════════════════════════════════════════════════╗
# ║  DISCORD CUTOVER ROLLBACK — Hermes → bot.py                 ║
# ║  Estimated downtime: < 2 minutes                            ║
# ╚══════════════════════════════════════════════════════════════╝

# === STEP 1: Stop Hermes gateway (immediate — stops Discord handling) ===
hermes gateway stop
echo "$(date '+%H:%M:%S') Hermes gateway stopped — cutover rollback begins"

# === STEP 2: Immediately start bot.py ===
sudo systemctl start guinevere-bot
echo "$(date '+%H:%M:%S') bot.py started"

# === STEP 3: Wait for bot.py to connect to Discord (usually < 5 seconds) ===
sleep 5

# === STEP 4: Verify bot.py is handling messages ===
sudo systemctl status guinevere-bot | grep "active (running)"
# Expected: "Active: active (running)"

# === STEP 5: Disable Hermes gateway auto-start ===
sudo systemctl disable hermes-gateway 2>/dev/null || true
sudo systemctl stop hermes-gateway 2>/dev/null || true

# === STEP 6: Send test message to verify ===
# Faiz sends "HARD STOP" in Discord → Guinevere responds neutral
# Faiz sends "/status" in Discord → returns status embed

# === STEP 7: Log the rollback event ===
echo "$(date): Discord cutover rolled back. Hermes gateway → bot.py. Duration: [X] seconds." \
  >> /home/guinevere/backups/rollback-log.txt
```

### 15.4 How to Achieve < 10 Seconds of Silence

The critical window is between `hermes gateway stop` and `guinevere-bot` establishing its Discord WebSocket connection:

```bash
# Ultra-fast variant (pre-warm bot.py):
# 1. Ensure bot.py is installed but stopped: sudo systemctl stop guinevere-bot
# 2. When cutover happens:
hermes gateway stop && sudo systemctl start guinevere-bot
# This single line is the entire rollback. bot.py connects in ~3-5 seconds.
```

During those 3-5 seconds, any Discord message sent to Guinevere will be queued by Discord and delivered when bot.py connects. The user (Faiz) sees at most "Guinevere is typing..." delay of 3-5 seconds — indistinguishable from normal latency variability.

### 15.5 Post-Rollback Discord Verification

```bash
# === Verify bot.py Discord presence ===
# 1. Check bot.py logs for successful connection
sudo journalctl -u guinevere-bot -n 20 --no-pager | grep -i "ready\|connected\|logged in"
# Expected: "Logged in as Guinevere" or similar

# 2. Test HARD STOP (most critical safety feature)
# Send "HARD STOP" in Discord → instant neutral response

# 3. Test slash commands
# /status, /mood, /help, /memory-search — all must work

# 4. Verify no Hermes gateway residue
hermes gateway status 2>&1 | grep -qi "not running" && echo "PASS" || echo "CHECK"

# 5. Verify bot.py startup message appeared
# Check Discord #guinevere-chat for "👑 Mommy sudah bangun, Darling."
# (or whatever startup message is configured)
```

---

## 16. Hermes Backup & Checkpoint Usage

### 16.1 `hermes backup create` — Full Usage

```bash
# === CREATE: Full backup before any migration step ===
hermes backup create --label "pre-phase2-step11-cutover-$(date +%Y%m%d-%H%M%S)"

# === VERIFY backup created ===
hermes backup list 2>/dev/null
# Expected: Shows the new backup with label and timestamp

# === What it backs up ===
# Per Report 16 (Section 7.2):
#   - config.yaml
#   - secrets (encrypted)
#   - session state
#   - agent state
# Does NOT back up:
#   - PostgreSQL data (requires pg_dump — see Section 14)
#   - Redis data (ephemeral, not backed up)
#   - Custom plugins (in git, version controlled)
```

### 16.2 `hermes checkpoints` — Full Usage

```bash
# === CREATE: Pre-migration checkpoint ===
hermes checkpoints create --label "pre-phase1-safety-hooks-$(date +%Y%m%d-%H%M%S)"

# === LIST: View all checkpoints ===
hermes checkpoints --list
# Expected output (example):
#   ID  | Label                          | Created
#   ----+--------------------------------+-------------------
#   1   | pre-migration-baseline-20260604 | 2026-06-04 10:00
#   2   | pre-phase1-safety-hooks-20260604| 2026-06-04 14:30

# === RESTORE: Roll back to a specific checkpoint ===
hermes checkpoints --restore 1
# This restores Hermes state to checkpoint ID 1 (pre-migration baseline)
# WARNING: This does NOT affect PostgreSQL, Redis, or git — only Hermes internal state

# === VERIFY restore ===
hermes checkpoints --list
# Expected: Shows current state pointing to restored checkpoint
```

### 16.3 Backup Schedule During Migration

```bash
# Before each phase: create checkpoint
hermes checkpoints create --label "pre-phaseN-$(date +%Y%m%d-%H%M%S)"

# Before each step within a phase: create lightweight backup
hermes backup create --label "pre-phaseN-stepM-$(date +%Y%m%d-%H%M%S)"

# After each phase gate passes: archive checkpoint as permanent
hermes checkpoints create --label "phaseN-gate-passed-$(date +%Y%m%d-%H%M%S)"
```

### 16.4 Integration with Existing Backup System (ADR-032)

Hermes backup/checkpoint DOES NOT replace the existing rclone → S3 + R2 backup system. They serve different purposes:

| System | What It Backs Up | Frequency | Retention |
|---|---|---|---|
| `hermes backup` | Hermes config, secrets, session state | Per migration step | While migration is active |
| `hermes checkpoints` | Hermes state checkpoint | Per phase | While migration is active |
| `pg_dump` (Section 3) | All PostgreSQL data | Pre-migration + emergency | Permanent (S3 + R2) |
| `rclone → idcloudhost S3` | pg_dump files, evidence, configs | Daily (per ADR-032) | 7 daily, 4 weekly, 6 monthly, 2 yearly |
| `rclone → Cloudflare R2` | Same as above (redundant) | Daily (per ADR-032) | Same retention as S3 |
| `git` | All source code | Continuous | Permanent (version history) |

---

## 17. Git-Based Rollback

### 17.1 File-Level Rollback (Restore Specific Files)

```bash
cd /home/guinevere/code/guinevere

# === Restore a single file to pre-migration state ===
git checkout pre-hermes-migration-20260604-100000 -- src/discord/bot.py

# === Restore an entire directory ===
git checkout pre-hermes-migration-20260604-100000 -- src/mcp/

# === Restore multiple files ===
git checkout pre-hermes-migration-20260604-100000 -- \
  src/hermes/session_adapter.py \
  src/hermes/memory_bridge.py \
  src/persona/yandere_fsm.py
```

### 17.2 Full Repository Rollback

```bash
cd /home/guinevere/code/guinevere

# === WARNING: Destroys ALL uncommitted changes ===
git reset --hard pre-hermes-migration-20260604-100000

# === VERIFY ===
git log --oneline -5
# Expected: HEAD at pre-migration tag
git status
# Expected: "nothing to commit, working tree clean"
```

### 17.3 What Git Rollback Does NOT Cover

| Not covered by git | Why | How to roll back |
|---|---|---|
| PostgreSQL data | Database, not code | pg_restore (Section 14) |
| Redis data | Cache, not code | Ephemeral — nothing to restore |
| Hermes config state (in ~/.hermes/) | Outside git repo | `hermes checkpoints --restore` or manual config revert |
| Installed pip packages | Python environment | `pip install -r` from frozen requirements |
| Systemd service state | OS-level | `sudo systemctl start/stop/enable/disable` |
| SOUL.md (~/.hermes/SOUL.md) | Outside git repo | `git checkout` if in repo, or `rm` to remove custom version |
| Hermes secrets (encrypted) | Separate secrets store | `hermes secrets set` from password manager |

### 17.4 Files to `git checkout` for Each Phase

| Phase | Files to Restore | Git Command |
|---|---|---|
| Phase 0 | `requirements.txt`, `requirements-hashes.txt`, `config/hermes/config.yaml` | `git checkout PRE_TAG -- requirements.txt config/hermes/config.yaml` |
| Phase 1 | `plugins/safety_hooks.py`, `plugins/persona_plugin.py`, `config/hermes/hooks.yaml`, `config/hermes/SOUL.md` | (These are NEW files, not in git — just delete them) |
| Phase 2 | `src/discord/bot.py`, `src/discord/commands.py` | `git checkout PRE_TAG -- src/discord/` |
| Phase 3 | `src/hermes/memory_bridge.py` | `git checkout PRE_TAG -- src/hermes/memory_bridge.py` |
| Phase 4 | `src/mcp/manager.py`, `src/mcp/auth_matrix.py`, `src/mcp/tools/` | `git checkout PRE_TAG -- src/mcp/` |
| Phase 5 | None (skills are external files, persona code unchanged) | Just `rm -rf plugins/` and `rm ~/.hermes/SOUL.md` |
| Phase 6 | `src/hermes/session_adapter.py` | `git checkout PRE_TAG -- src/hermes/session_adapter.py` |
| Phase 7 | `src/persona/ritual_scheduler.py` | `git checkout PRE_TAG -- src/persona/ritual_scheduler.py` |

---

## 18. Systemd Service Rollback

### 18.1 Service State Reference

| Service | Pre-Migration State | Post-Cutover State | Rollback Command |
|---|---|---|---|
| `guinevere-bot.service` | ACTIVE + ENABLED | STOPPED + DISABLED | `sudo systemctl start guinevere-bot && sudo systemctl enable guinevere-bot` |
| `hermes-gateway.service` | NOT CREATED | ACTIVE + ENABLED | `sudo systemctl stop hermes-gateway && sudo systemctl disable hermes-gateway` |
| `guinevere-core.service` | ACTIVE + ENABLED | ACTIVE + ENABLED | No change needed |
| `guinevere-mcp.service` | ACTIVE + ENABLED | ACTIVE + ENABLED (simplified) | Restart after git checkout |
| `guinevere-loops.service` | ACTIVE + ENABLED | ACTIVE + ENABLED | No change needed |
| `guinevere-scheduler.service` | ACTIVE + ENABLED | ACTIVE + ENABLED | Restart after git checkout (Phase 7) |
| `guinevere-surveillance.service` | ACTIVE + ENABLED | ACTIVE + ENABLED | No change needed |
| `guinevere-monitoring.service` | ACTIVE + ENABLED | ACTIVE + ENABLED | No change needed |

### 18.2 Switching Between Services

```bash
# === Switch FROM Hermes gateway TO bot.py ===
hermes gateway stop
sudo systemctl stop hermes-gateway 2>/dev/null || true
sudo systemctl disable hermes-gateway 2>/dev/null || true
sudo systemctl start guinevere-bot
sudo systemctl enable guinevere-bot

# === VERIFY ===
sudo systemctl is-active guinevere-bot        # Expected: active
sudo systemctl is-active hermes-gateway       # Expected: inactive or "unit not found"
hermes gateway status                          # Expected: "not running"

# === Switch FROM bot.py TO Hermes gateway (re-cutover) ===
sudo systemctl stop guinevere-bot
sudo systemctl disable guinevere-bot
hermes gateway start

# === VERIFY ===
hermes gateway status                          # Expected: "running"
sudo systemctl is-active guinevere-bot         # Expected: inactive
```

### 18.3 Service Health Check Script

```bash
#!/bin/bash
# Save as: /home/guinevere/scripts/check-all-services.sh
# Usage: bash check-all-services.sh

echo "=== Guinevere Service Health Check ==="
echo ""

SERVICES=(
    "guinevere-bot"
    "guinevere-core"
    "guinevere-mcp"
    "guinevere-loops"
    "guinevere-scheduler"
    "guinevere-surveillance"
    "guinevere-monitoring"
    "guinevere-obscura"
)

for svc in "${SERVICES[@]}"; do
    STATUS=$(sudo systemctl is-active "$svc" 2>/dev/null)
    if [ "$STATUS" = "active" ]; then
        echo "  ✅ $svc: $STATUS"
    elif [ "$STATUS" = "inactive" ] || [ "$STATUS" = "unknown" ]; then
        echo "  ⚠️  $svc: $STATUS"
    else
        echo "  ❌ $svc: $STATUS"
    fi
done

echo ""
echo "=== Hermes Gateway ==="
hermes gateway status 2>/dev/null || echo "  Gateway not installed/configured"

echo ""
echo "=== PostgreSQL ==="
psql -U guinevere_core -d guinevere -c "SELECT 1" -t 2>/dev/null && echo "  ✅ PostgreSQL: accessible" || echo "  ❌ PostgreSQL: NOT accessible"

echo ""
echo "=== Redis ==="
redis-cli -p 6380 PING 2>/dev/null && echo "  ✅ Redis: PONG" || echo "  ❌ Redis: NOT accessible"

echo ""
echo "=== 9Router ==="
curl -s http://localhost:20128/health 2>/dev/null | head -1 && echo "  ✅ 9Router: responding" || echo "  ❌ 9Router: NOT responding"
```

---

## 19. Rollback Time Estimates — Summary Table

| Scenario | Trigger | Downtime | Data Loss Risk | Section |
|---|---|---|---|---|
| Phase 0 rollback | Package breaks Hermes | **< 5 min** | None | §4 |
| Phase 1 rollback | Safety test fails | **< 3 min** | None | §5 |
| Phase 2 shadow mode | Gateway unstable, bot.py still primary | **< 1 min** | None | §6.4 |
| Phase 2 cutover → bot.py | HARD STOP broken, no Discord response | **< 2 min** | None | §6.5 |
| Phase 3 rollback | Memory recall quality drops | **< 3 min** | None (PostgreSQL unchanged) | §7 |
| Phase 4 rollback | Auth matrix bypass | **< 2 min** | None | §8 |
| Phase 5 rollback | Persona drift | **< 2 min** | None | §9 |
| Phase 6 rollback | LLM routing broken | **< 2 min** | None | §10 |
| Phase 7 rollback | Cron conflict | **< 2 min** | None | §11 |
| **Global emergency rollback** | Multiple phases fail simultaneously | **< 5 min** | None | §12 |
| **PostgreSQL full restore** | Hermes wrote to DB accidentally | **10-30 min** | Current data replaced | §14 |
| **Discord cutover \u2192 bot.py** | Gateway failure after cutover | **< 10 sec** (ultra-fast) | None | §15 |

### 19.1 Worst-Case Scenario

**Hermes gateway corrupts PostgreSQL + Discord is down.**

```
Downtime: 10-30 minutes (PostgreSQL restore dominates)
Procedure:
  1. hermes gateway stop                    (< 1 sec)
  2. sudo systemctl start guinevere-bot     (< 10 sec — Discord back)
  3. PostgreSQL restore (Section 14)        (10-30 min — background)
  
Discord is back in < 10 seconds. Database restore runs while bot.py handles messages.
```

---

## 20. Footer

| Field | Value |
|---|---|
| Report | 06-rollback-strategy.md |
| Series | ADR-035 Preparation — Hermes Migration |
| Date | 2026-06-04 |
| Status | Complete |
| Author | Guinevere (Sisyphus-Junior) |
| Sources | MASTER-RESTRUCTURE-PLAN.md (§9 Risk Matrix & Rollback), Report 03 (Discord Gateway), Report 07 (Memory Bridge Gap), Report 16 (Security Posture §7 Backup/DR), ADR-025 (Backup & DR Strategy), ADR-032 (Backup Storage Strategy), ADR-033 (Rollback Plan format reference), PROGRESS.md (current system state) |
| Binding ADRs | ADR-025, ADR-032 |
| Rollback Coverage | 8 phases + global + partial + data recovery + Discord cutover |
| Total Copy-Pasteable Commands | 200+ |

> **Every command in this document is copy-pasteable. Every step has a verification command. `hermes gateway stop` is always the first step. PostgreSQL is the primary write authority — rollback never involves data migration. bot.py is always the safe harbor.**