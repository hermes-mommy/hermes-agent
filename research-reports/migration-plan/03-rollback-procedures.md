# 03 — Rollback Procedures Per Phase: Hermes Migration

> **Date**: 2026-06-04
> **Scope**: Exact, copy-paste ready rollback procedures for every phase (0-7) of the Hermes migration.
> **Author**: Guinevere (Sisyphus-Junior — Agent 3/10)
> **Status**: Complete
> **Binding ADRs**: ADR-025 (Backup & DR Strategy), ADR-032 (Backup Storage Strategy), ADR-035 (Hermes Migration Architecture)
> **Sources**: `adr/ADR-035-hermes-migration.md`, `research-reports/adr-035-prep/06-rollback-strategy.md`, `research-reports/hermes-restructure/MASTER-RESTRUCTURE-PLAN.md`, `systemd/` (all 7 service files), `PROGRESS.md`

---

## Table of Contents

1. [Rollback Philosophy & Iron Rules](#1-rollback-philosophy--iron-rules)
2. [Infrastructure Reference](#2-infrastructure-reference)
3. [Service Dependency Map](#3-service-dependency-map)
4. [Pre-Migration Safety Net (Run BEFORE Any Phase)](#4-pre-migration-safety-net-run-before-any-phase)
5. [Phase 0 Rollback — Security Remediation](#5-phase-0-rollback--security-remediation)
6. [Phase 1 Rollback — Safety Foundation](#6-phase-1-rollback--safety-foundation)
7. [Phase 2 Rollback — Discord Gateway Migration](#7-phase-2-rollback--discord-gateway-migration)
8. [Phase 3 Rollback — Memory Bridge Enhancement](#8-phase-3-rollback--memory-bridge-enhancement)
9. [Phase 4 Rollback — Tool/MCP Migration](#9-phase-4-rollback--toolmcp-migration)
10. [Phase 5 Rollback — Skills & Persona](#10-phase-5-rollback--skills--persona)
11. [Phase 6 Rollback — LLM Routing & Budget](#11-phase-6-rollback--llm-routing--budget)
12. [Phase 7 Rollback — Hardening & Monitoring](#12-phase-7-rollback--hardening--monitoring)
13. [Global Emergency Rollback — All Phases at Once](#13-global-emergency-rollback--all-phases-at-once)
14. [PostgreSQL Full Restore Procedure](#14-postgresql-full-restore-procedure)
15. [Redis Flush Procedure (DB-Specific)](#15-redis-flush-procedure-db-specific)
16. [Discord Cutover Rollback — Hermes Gateway \u2192 bot.py](#16-discord-cutover-rollback--hermes-gateway--botpy)
17. [Hermes Backup & Checkpoint Usage](#17-hermes-backup--checkpoint-usage)
18. [Git-Based Rollback Reference](#18-git-based-rollback-reference)
19. [Systemd Service Health Check Script](#19-systemd-service-health-check-script)
20. [Rollback Time Estimates — Summary Table](#20-rollback-time-estimates--summary-table)
21. [Post-Rollback Verification Checklist](#21-post-rollback-verification-checklist)
22. [Footer](#22-footer)

---

## 1. Rollback Philosophy & Iron Rules

### 1.1 Universal First Step

**Every single rollback procedure in this document begins with:**

```bash
hermes gateway stop
```

This is the universal kill-switch. If Hermes gateway is not running, this is a no-op (exit 0). This ensures no Hermes Discord activity can interfere with rollback operations.

### 1.2 Five Iron Rules

1. **Data never moves backward.** PostgreSQL+pgvector is the primary write authority. Hermes writes are supplementary read-only. Rollback is code + config + service topology — not data migration.
2. **bot.py is always the fallback.** The existing `guinevere-discord.service` (running `bot.py`) is the safe harbor. It runs independently of Hermes.
3. **Git is the ultimate undo.** Every migration change is version-controlled. `git checkout` restores code.
4. **Operators verify, don't assume.** Every rollback step includes a verification command. Run them and verify output.
5. **Rollback is a phase gate.** No migration phase proceeds until the previous phase's rollback has been tested and verified.

### 1.3 Rollback Pre-Flight Checklist

Before ANY phase begins, confirm:

- [ ] `git status` is clean (no uncommitted changes)
- [ ] `guinevere-discord.service` is running and healthy
- [ ] PostgreSQL is accessible on port 5433: `psql -U guinevere_core -d guinevere -c "SELECT 1"`
- [ ] Redis is accessible on port 6380: `redis-cli -p 6380 PING`
- [ ] Latest `hermes checkpoints --list` shows at least one checkpoint
- [ ] Latest `pg_dump` backup is < 1 hour old (or manual backup just taken)
- [ ] Offsite backups verified: `rclone ls idcloudhost:guinevere-dr-backups/manual/ | head -3`

---

## 2. Infrastructure Reference

### 2.1 VPS Details

| Detail | Value |
|---|---|
| OS | Ubuntu 24.04 |
| VPS | hostdata.id 4C/16GB (cgroup-capped to 8GB) |
| Shared with | Aizanta |
| Application user | `guinevere` |
| Code directory | `/home/guinevere/code/guinevere/` |
| Virtual environment | `/home/guinevere/code/guinevere/.venv/` |
| Hermes config | `/home/guinevere/config/hermes/config.yaml` |
| Hermes binary | `/home/guinevere/code/guinevere/.venv/bin/hermes` |
| SOUL.md | `~/.hermes/SOUL.md` |

### 2.2 Port Assignments

| Service | Port | Note |
|---|---|---|
| PostgreSQL | **5433** | Self-hosted, non-standard to avoid Aizanta conflict |
| Redis | **6380** | Non-standard to avoid Aizanta conflict |
| 9Router LLM | **20128** | Node.js, GPT-5.5 + DeepSeek V4 Flash |
| Obscura CDP | **9222** | Browser automation |
| FastAPI API | **8000** | Internal API, localhost only |

### 2.3 Systemd Services (Exact Names from `systemd/`)

| Service File | Unit Name | Description |
|---|---|---|
| `systemd/guinevere-discord.service` | `guinevere-discord.service` | Discord bot (bot.py) — THE FALLBACK |
| `systemd/guinevere-mcp.service` | `guinevere-mcp.service` | MCP tool server (16 tools) |
| `systemd/guinevere-loops.service` | `guinevere-loops.service` | Agent loop state machine |
| `systemd/guinevere-scheduler.service` | `guinevere-scheduler.service` | APScheduler (rituals, consolidation) |
| `systemd/guinevere-surveillance.service` | `guinevere-surveillance.service` | Surveillance event consumer |
| `systemd/guinevere-monitoring.service` | `guinevere-monitoring.service` | Prometheus/Grafana/Loki stack |
| `systemd/guinevere-obscura.service` | `guinevere-obscura.service` | Obscura CDP server |

**Hermes service** (created during Phase 2): `hermes-gateway.service`

### 2.4 Redis DB Assignments (per ADR-030)

| DB | Assignment |
|---|---|
| DB0 | Cache (general) |
| DB1 | Pub/Sub |
| DB2 | Consent cache |
| DB3 | Sessions |
| DB4 | Session cache (bot.py) |
| DB5 | Rate limiting + cost tracking |

---

## 3. Service Dependency Map

```
guinevere-discord.service          (Discord bot — the fallback, ALWAYS available)
guinevere-mcp.service              (MCP tool server, 16 tools)
guinevere-loops.service            (Agent loop 7-phase state machine)
guinevere-scheduler.service        (APScheduler: rituals, consolidation, cost reports)
guinevere-surveillance.service     (Surveillance event ingestion)
guinevere-monitoring.service       (Prometheus/Grafana/Loki stack)
guinevere-obscura.service          (Obscura CDP server, port 9222)
hermes-gateway.service             (Hermes Discord gateway — created during Phase 2)
```

---

## 4. Pre-Migration Safety Net (Run BEFORE Any Phase)

### 4.1 Pre-Conditions

- [ ] `git status` is clean
- [ ] All `guinevere-*` services running
- [ ] `hermes --help` functional

### 4.2 Rollback Trigger

Not applicable — this is run proactively before any migration phase begins.

### 4.3 Commands

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
# Expected: File size > 0 bytes

# === STEP 5: Save systemd service state ===
systemctl list-units 'guinevere-*' --all > /home/guinevere/backups/pre-migration-services-$(date +%Y%m%d).txt

# === STEP 6: Save pip freeze for dependency rollback ===
cd /home/guinevere/code/guinevere
./.venv/bin/pip freeze > /home/guinevere/backups/pre-migration-pip-$(date +%Y%m%d).txt

# === VERIFY pip freeze ===
wc -l /home/guinevere/backups/pre-migration-pip-$(date +%Y%m%d).txt
# Expected: 50+ lines

# === STEP 7: Offsite backup (per ADR-032) ===
rclone copy /home/guinevere/backups/pre-migration-*.dump idcloudhost:guinevere-dr-backups/manual/
rclone copy /home/guinevere/backups/pre-migration-*.dump r2:guinevere-dr-backups/manual/

# === VERIFY offsite ===
rclone ls idcloudhost:guinevere-dr-backups/manual/ | grep pre-migration
rclone ls r2:guinevere-dr-backups/manual/ | grep pre-migration
```

### 4.4 Time Estimate

**~10-15 minutes** (dominated by pg_dump and rclone upload).

---

## 5. Phase 0 Rollback — Security Remediation

### 5.1 Pre-Conditions

- [ ] Pre-migration `pip freeze` snapshot exists at `/home/guinevere/backups/pre-migration-pip-*.txt`
- [ ] Pre-migration `git tag` exists
- [ ] `hermes --help` was working before Phase 0 began

### 5.2 Rollback Trigger

| Condition | Detection |
|---|---|
| `hermes security` shows NEW vulnerabilities after upgrade | Run `hermes security` after each pip install |
| `hermes doctor` fails after config changes | Run `hermes doctor` after each config edit |
| Package upgrade breaks Hermes CLI (`hermes --help` fails) | Run `hermes --help` after each upgrade |
| `.env` file exposes secrets accidentally | Manual review: `cat /home/guinevere/code/guinevere/.env` |

### 5.3 Commands

```bash
# === STEP 1: Universal kill-switch ===
hermes gateway stop

# === STEP 2: Rollback pip packages to pre-Phase-0 versions ===
cd /home/guinevere/code/guinevere
PIP_FREEZE=$(ls -t /home/guinevere/backups/pre-migration-pip-*.txt | head -1)
./.venv/bin/pip install -r "$PIP_FREEZE"

# === VERIFY package versions ===
./.venv/bin/pip list | grep -E "aiohttp|ecdsa|pip|PyJWT"
# Expected: Match versions from pre-migration pip freeze

# === STEP 3: Rollback git changes ===
git checkout -- config/hermes/config.yaml
git checkout -- .env 2>/dev/null || rm -f /home/guinevere/code/guinevere/.env

# === VERIFY git clean ===
git status
# Expected: "nothing to commit, working tree clean"

# === STEP 4: Verify Hermes still works ===
hermes --help
# Expected: Hermes CLI help output
```

### 5.4 Verification

```bash
# === Service health ===
systemctl is-active guinevere-discord guinevere-mcp guinevere-loops guinevere-scheduler guinevere-surveillance guinevere-monitoring guinevere-obscura
# Expected: all "active"

# === Data integrity ===
sudo -u postgres psql -d guinevere -c "SELECT count(*) FROM memory.episodes"
# Expected: Same count as pre-Phase-0
redis-cli -p 6380 PING
# Expected: PONG
```

### 5.5 Service Restoration Order

```
No services affected. Skip.
```

### 5.6 Time Estimate

| Step | Time |
|---|---|
| `hermes gateway stop` | < 1 sec |
| `pip install -r` | 1-2 min |
| `git checkout` | < 5 sec |
| Verification | 1 min |
| **Total** | **< 5 minutes** |

### 5.7 Post-Rollback Actions

- Document in `/home/guinevere/backups/rollback-log-phase0-$(date +%Y%m%d).md`
- Notify Faiz: "Phase 0 rollback complete. Packages reverted to pre-migration versions. No data affected."

---

## 6. Phase 1 Rollback — Safety Foundation

### 6.1 Pre-Conditions

- [ ] Phase 0 gate passed (`hermes doctor` clean, `hermes security` clean)
- [ ] `guinevere-discord.service` is running (bot.py handles Discord normally)
- [ ] Pre-Phase-1 git tag exists
- [ ] Pre-Phase-1 Hermes checkpoint exists
- [ ] Hermes gateway is NOT running (Phase 2 not yet started)

### 6.2 Rollback Trigger

| Condition | Detection |
|---|---|
| HARD STOP test fails (hook doesn't intercept) | Send "HARD STOP" → must return neutral, zero LLM call |
| Consent gate fails-closed incorrectly | Test: ACTIVE consent → tool allowed; WITHDRAWN → blocked |
| Yandere FSM allows Y6 content through | Generate Y6-triggering content → must be rewritten to Y5 |
| Drift detector false-positive | Monitor drift logs for [DRIFT] entries during normal operation |
| DNR enforcement fails | Mark memory DNR → `recall_memories()` must exclude it |
| Any safety test suite failure | `python -m pytest tests/persona/ -v` |

### 6.3 Commands

```bash
# === STEP 1: Universal kill-switch ===
hermes gateway stop

# === STEP 2: Remove all Phase 1-created plugin and config files ===
rm -f plugins/safety_hooks.py
rm -f plugins/auth_overlay.py
rm -f plugins/memory_plugin.py
rm -f plugins/persona_plugin.py
rm -f plugins/guinevere_safety_plugin.py
rm -f config/hermes/hooks.yaml
rm -f config/hermes/mcp-servers.yaml

# === STEP 3: Restore modified persona files from git ===
cd /home/guinevere/code/guinevere
git checkout -- src/persona/yandere_fsm.py
git checkout -- src/persona/drift_detector.py
git checkout -- src/persona/safe_mode.py
git checkout -- src/persona/hard_stop_handler.py
git checkout -- src/persona/consent_gate.py
git checkout -- src/persona/punishment_engine.py
git checkout -- src/persona/reward_engine.py
git checkout -- src/persona/mood_engine.py
git checkout -- src/persona/ritual_scheduler.py
git checkout -- src/persona/streak_tracker.py

# === STEP 4: Remove SOUL.md ===
git checkout -- config/hermes/SOUL.md 2>/dev/null || rm -f ~/.hermes/SOUL.md

# === VERIFY files removed ===
ls plugins/ 2>/dev/null && echo "WARNING: plugins/ still exists" || echo "PASS: plugins/ removed"
git status
# Expected: "nothing to commit, working tree clean"
```

### 6.4 Verification

```bash
# === All original safety files intact ===
ls src/persona/hard_stop_handler.py src/persona/yandere_fsm.py src/persona/drift_detector.py src/persona/consent_gate.py
# Expected: All files exist

# === bot.py running with original safety code ===
systemctl status guinevere-discord | grep "active (running)" && echo "PASS" || echo "FAIL"

# === HARD STOP still works via original bot.py handler ===
# Send "HARD STOP" in Discord → Guinevere responds neutral, no punishment

# === Data integrity ===
sudo -u postgres psql -d guinevere -c "SELECT count(*) FROM memory.episodes"
sudo -u postgres psql -d guinevere -c "SELECT count(*) FROM persona.mood_states"
redis-cli -p 6380 PING
```

### 6.5 Service Restoration Order

```
No services affected. Skip.
```

### 6.6 Time Estimate

**< 3 minutes.**

### 6.7 Post-Rollback Actions

- Document in `/home/guinevere/backups/rollback-log-phase1-$(date +%Y%m%d).md`
- Notify Faiz: "Phase 1 rollback complete. All safety hooks reverted. bot.py running with original safety code. No data affected."

---

## 7. Phase 2 Rollback — Discord Gateway Migration

### 7.1 Pre-Conditions

**For shadow mode rollback:**
- [ ] `hermes gateway status` shows gateway is running
- [ ] `guinevere-discord.service` is ACTIVE (bot.py is still primary)
- [ ] Shadow mode comparison data exists (48hr parity report)

**For cutover rollback:**
- [ ] `guinevere-discord.service` is STOPPED or DISABLED
- [ ] `hermes-gateway.service` is ACTIVE
- [ ] bot.py code is intact (not deleted, only disabled)
- [ ] Discord bot token is available (SOPS-decrypted from `secrets/discord-secrets.yaml`)
- [ ] Pre-Phase-2 git tag exists

### 7.2 Rollback Trigger

**Shadow mode:**
| Condition | Detection |
|---|---|
| Hermes gateway fails to start | `hermes gateway status` → errors |
| Slash command registration fails | `hermes gateway list` → fewer than expected commands |
| Shadow mode comparison shows >20% semantic divergence | Compare bot.py vs Hermes response |

**Cutover:**
| Condition | Detection |
|---|---|
| **CRITICAL: HARD STOP doesn't work** | "HARD STOP" → no neutral response |
| **CRITICAL: Messages not delivered** | No response within 30 seconds |
| **CRITICAL: Safety feature regression** | Any Phase 1 test fails via gateway |
| Response latency > 2x bot.py baseline | `hermes gateway status` → latency spike |
| Error rate > 5% of messages | `hermes logs --level error` |
| Faiz manually requests rollback | "rollback gateway" / "kembalikan bot.py" |

### 7.3 Commands — Shadow Mode Rollback

```bash
# === STEP 1: Universal kill-switch ===
hermes gateway stop

# === STEP 2: Remove Hermes gateway configuration ===
# Option A: Uninstall gateway (complete removal)
hermes gateway uninstall

# Option B: Just stop and disable (preserves config for retry)
sudo systemctl disable hermes-gateway 2>/dev/null || true

# === VERIFY ===
hermes gateway status
# Expected: "Gateway not running"

# === STEP 3: Confirm bot.py is handling traffic ===
systemctl status guinevere-discord | grep "active (running)"
# Expected: "Active: active (running)"
```

### 7.4 Commands — Cutover Rollback (Hermes → bot.py)

```bash
# ╔══════════════════════════════════════════════════════════════╗
# ║     DISCORD CUTOVER ROLLBACK — Hermes → bot.py              ║
# ║     Goal: < 2 minutes downtime                              ║
# ╚══════════════════════════════════════════════════════════════╝

# === STEP 1: Universal kill-switch ===
hermes gateway stop
echo "$(date '+%H:%M:%S') Hermes gateway stopped — rollback begins"

# === STEP 2: Immediately start bot.py ===
sudo systemctl start guinevere-discord

# === VERIFY bot.py started ===
systemctl status guinevere-discord | grep "active (running)"
# Expected: "Active: active (running) since ..."

# === STEP 3: Disable Hermes gateway service (prevent auto-restart) ===
sudo systemctl stop hermes-gateway 2>/dev/null || true
sudo systemctl disable hermes-gateway 2>/dev/null || true

# === VERIFY Hermes gateway stopped ===
hermes gateway status
# Expected: Not running

# === STEP 4: Restore original Discord handler code (if modified) ===
cd /home/guinevere/code/guinevere
git checkout -- src/discord/bot.py
git checkout -- src/discord/commands.py 2>/dev/null || true

# === VERIFY bot.py unchanged ===
git diff src/discord/bot.py
# Expected: No output

# === STEP 5: Restart bot.py to pick up restored code ===
sudo systemctl restart guinevere-discord

# === VERIFY bot.py running with restored code ===
systemctl status guinevere-discord | grep "active (running)"

# === STEP 6 (OPTIONAL): Restore from pre-Phase-2 git tag ===
# Only if deeper rollback needed
PRE_PHASE2_TAG=$(git tag | grep "pre-hermes-migration" | tail -1)
git checkout "$PRE_PHASE2_TAG" -- src/discord/
sudo systemctl restart guinevere-discord
```

### 7.5 Verification

```bash
# === bot.py running and handling messages ===
systemctl status guinevere-discord | grep "active (running)" && echo "PASS" || echo "FAIL"

# === HARD STOP works ===
# Send "HARD STOP" in Discord → neutral response, zero LLM call

# === Slash commands functional ===
# Test: /status, /mood, /help → all respond correctly

# === Hermes gateway fully stopped ===
hermes gateway status 2>&1 | grep -qi "not running" && echo "PASS" || echo "CHECK"

# === Other services unaffected ===
systemctl is-active guinevere-mcp guinevere-loops guinevere-scheduler guinevere-surveillance guinevere-monitoring guinevere-obscura
# Expected: all "active"

# === Data integrity ===
sudo -u postgres psql -d guinevere -c "SELECT count(*) FROM memory.episodes"
redis-cli -p 6380 PING
```

### 7.6 Service Restoration Order

```
Priority 1 (immediate, parallel):
  guinevere-discord.service    → START NOW (restores Discord immediately)

Priority 2 (within 1 minute):
  hermes-gateway.service       → STOP + DISABLE
```

### 7.7 Time Estimate

| Scenario | Time |
|---|---|
| Shadow mode rollback | **< 1 minute** |
| Cutover rollback | **< 2 minutes** |
| Cutover + git checkout | **< 3 minutes** |
| Cutover + full git tag restore | **< 5 minutes** |

### 7.8 Post-Rollback Actions

- Notify Faiz: "Discord gateway rolled back to bot.py. Hermes gateway stopped and disabled. All slash commands functional on bot.py. Downtime: [X] seconds."
- Document in `/home/guinevere/backups/rollback-log-phase2-$(date +%Y%m%d).md`

---

## 8. Phase 3 Rollback — Memory Bridge Enhancement

### 8.1 Pre-Conditions

- [ ] Phase 2 rollback verified (or Phase 2 is still active with bot.py primary)
- [ ] PostgreSQL+pgvector is accessible and contains all data
- [ ] `memory_bridge.py` original (pre-simplification) is in git
- [ ] Pre-Phase-3 git tag exists

### 8.2 Rollback Trigger

| Condition | Detection |
|---|---|
| Memory recall quality drops | Manual spot-check 5-10 queries |
| Hermes compression corrupts context | LLM responses reference wrong earlier messages |
| Hermes session_search returns incorrect cross-session data | Compare vs PostgreSQL direct query |
| DNR memory appears in Hermes recall paths | DNR test: mark → verify excluded from session_search |
| Classification ceiling breached | Critical data query → must return nothing |

### 8.3 Commands

```bash
# === STEP 1: Universal kill-switch ===
hermes gateway stop

# === STEP 2: Disable Hermes memory features ===
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
git diff src/hermes/memory_bridge.py
# Expected: No output

# === STEP 4: Remove Hermes memory plugin files ===
rm -f plugins/memory_plugin.py 2>/dev/null || true

# === VERIFY plugin removed ===
ls plugins/memory_plugin.py 2>/dev/null && echo "WARNING" || echo "PASS: removed"

# === STEP 5: Restart core service (loads memory_bridge) ===
sudo systemctl restart guinevere-loops

# === VERIFY core restarted ===
systemctl status guinevere-loops | grep "active (running)" && echo "PASS" || echo "FAIL"
```

### 8.4 Verification

```bash
# === PRIMARY: PostgreSQL data intact ===
sudo -u postgres psql -d guinevere -c "
  SELECT 'episodes' as tbl, count(*) FROM memory.episodes
  UNION ALL SELECT 'semantic_facts', count(*) FROM memory.semantic_facts
  ORDER BY tbl;
"
# Expected: Row counts match pre-Phase-3

# === DNR flags intact ===
sudo -u postgres psql -d guinevere -c "
  SELECT count(*) FROM memory.episodes WHERE do_not_recall = true;
"

# === Memory recall via bot.py works normally ===
# Test: Ask Guinevere about something stored in memory → correct recall

# === Hermes memory features disabled ===
hermes memory status 2>/dev/null | grep -E "compression|session_search"
# Expected: disabled or not mentioned
```

### 8.5 Service Restoration Order

```
1. guinevere-loops.service    → RESTART (picks up restored memory_bridge.py)
2. guinevere-discord.service  → Already running (if Phase 2 not cutover)
```

### 8.6 Time Estimate

**< 3 minutes.**

### 8.7 Post-Rollback Actions

- Notify Faiz: "Phase 3 memory bridge rolled back. Hermes compression and session_search disabled. Original memory_bridge.py restored. PostgreSQL data verified intact."

---

## 9. Phase 4 Rollback — Tool/MCP Migration

### 9.1 Pre-Conditions

- [ ] Original `guinevere-mcp.service` with all 16 tools is functional (pre-Phase-4 state)
- [ ] Original `src/mcp/manager.py` is in git
- [ ] Pre-Phase-4 git tag exists
- [ ] All custom MCP tools (postgres, redis, obscura_cdp, grep_app) verified functional

### 9.2 Rollback Trigger

| Condition | Detection |
|---|---|
| Auth matrix bypass detected | Any tool call without [AUTH] prefix |
| Hermes native tool behavior differs from custom | Compare output: same input → different output |
| Tool isolation failure | Test: forbidden operation not blocked |
| DESTRUCTIVE_APPROVAL fails | Destructive action executes without Discord approval |
| Auth overlay plugin crashes | All tool calls blocked → "tool unavailable" |
| Custom MCP servers fail after migration | Tool invocation fails for postgres, redis, obscura, grep_app |

### 9.3 Commands

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
# Expected: Empty or only custom servers

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
# Expected: No output

# === STEP 5: Restart Guinevere MCP service ===
sudo systemctl restart guinevere-mcp

# === VERIFY MCP service healthy ===
systemctl status guinevere-mcp | grep "active (running)" && echo "PASS" || echo "FAIL"
```

### 9.4 Verification

```bash
# === MCP service healthy with all tools ===
systemctl status guinevere-mcp | grep "active (running)" && echo "PASS" || echo "FAIL"

# === Auth matrix enforced ===
# Test: Attempt DESTRUCTIVE_APPROVAL tool → Discord webhook prompt appears

# === All 16 tools accessible ===
# Test via bot.py: /status shows all tools

# === Hermes MCP servers fully removed ===
hermes mcp list 2>/dev/null | grep -v "^$" | wc -l
# Expected: 0 (no Hermes-native servers registered)

# === Custom MCP tools functional ===
# Test each: postgres query, redis PING, obscura status, grep_app search

# === Data integrity ===
sudo -u postgres psql -d guinevere -c "SELECT 1" && echo "PASS" || echo "FAIL"
redis-cli -p 6380 PING && echo "PASS" || echo "FAIL"
```

### 9.5 Service Restoration Order

```
1. guinevere-mcp.service      → RESTART (picks up restored manager.py + tools)
2. guinevere-discord.service  → Already running
```

### 9.6 Time Estimate

**< 2 minutes.**

### 9.7 Post-Rollback Actions

- Notify Faiz: "Phase 4 MCP migration rolled back. All 16 tools restored to original FastMCP server. Hermes native MCP servers removed. guinevere-mcp.service restarted and healthy."

---

## 10. Phase 5 Rollback — Skills & Persona

### 10.1 Pre-Conditions

- [ ] Original Guinevere persona code intact (unchanged in git): `src/persona/*`
- [ ] Pre-Phase-5 git tag exists
- [ ] bot.py still handles persona features via original code

### 10.2 Rollback Trigger

| Condition | Detection |
|---|---|
| Persona drift detected | SOUL.md SHA-256 differs from baseline |
| Installed skill causes unexpected behavior | Tool use changes, tone shifts |
| Mood/ritual plugin conflicts | Multiple mood engines → contradictory behavior |
| Punishment/reward plugin fires incorrectly | Unexpected L-level or T-level changes |

### 10.3 Commands

```bash
# === STEP 1: Universal kill-switch ===
hermes gateway stop

# === STEP 2: Uninstall installed skills ===
# List installed skills
hermes skills list 2>/dev/null

# Uninstall each skill installed during Phase 5
hermes skills uninstall safety 2>/dev/null || true
hermes skills uninstall persona 2>/dev/null || true
# Repeat for each skill installed

# === VERIFY skills removed ===
hermes skills list 2>/dev/null | grep -c "installed"
# Expected: 0

# === STEP 3: Revert SOUL.md to pre-Phase-5 state ===
cd /home/guinevere/code/guinevere
git checkout -- config/hermes/SOUL.md 2>/dev/null || rm -f ~/.hermes/SOUL.md

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
ls plugins/*.py 2>/dev/null && echo "WARNING: plugins/ still has files" || echo "PASS: empty"
```

### 10.4 Verification

```bash
# === Persona behavior unchanged ===
# Test: Ask Guinevere a personal question → response matches pre-Phase-5 tone

# === Mood engine functional (original code) ===
# Test: /mood command → shows current mood from src/persona/mood_engine.py

# === Ritual scheduler fires correctly (original APScheduler) ===
# Wait for next ritual → verify ritual message appears

# === No drift detection alerts ===
# Monitor logs: no [DRIFT] entries after rollback

# === Data integrity ===
sudo -u postgres psql -d guinevere -c "
  SELECT count(*) FROM persona.mood_states;
  SELECT count(*) FROM persona.drift_log;
"
redis-cli -p 6380 PING
```

### 10.5 Service Restoration Order

```
No services affected. Skip.
```

### 10.6 Time Estimate

**< 2 minutes.**

### 10.7 Post-Rollback Actions

- Notify Faiz: "Phase 5 skills/persona rolled back. All installed skills removed. SOUL.md reverted. Persona plugins removed. Original persona code intact."

---

## 11. Phase 6 Rollback — LLM Routing & Budget

### 11.1 Pre-Conditions

- [ ] 9Router is running at `localhost:20128` (unchanged throughout)
- [ ] cost_tracker.py numbers are available in PostgreSQL for comparison
- [ ] Hermes LLM config was working before Phase 6
- [ ] Pre-Phase-6 git tag exists

### 11.2 Rollback Trigger

| Condition | Detection |
|---|---|
| Hermes LLM calls fail (can't reach 9Router) | `hermes --verbose run` → connection errors to localhost:20128 |
| Budget enforcement blocks legitimate requests | Agent can't respond → actual spend is under $30 |
| Budget enforcement doesn't block | Spend exceeds $30/mo without alerts |
| Fallback doesn't activate when primary is down | Kill primary → no fallback, just errors |
| Cost tracking diverges from cost_tracker.py | Compare `hermes insights` vs PostgreSQL data → >10% difference |

### 11.3 Commands

```bash
# === STEP 1: Universal kill-switch ===
hermes gateway stop

# === STEP 2: Revert Hermes LLM config ===
# Reset model to default
hermes model set --model default 2>/dev/null || true

# Reset fallback
hermes fallback set --model none 2>/dev/null || true

# Reset budget limits
hermes config set budget.monthly_limit 0 2>/dev/null || true
hermes config set budget.alert_threshold 0 2>/dev/null || true

# === VERIFY Hermes config reset ===
hermes model show 2>/dev/null
# Expected: Shows default model or error
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

# === STEP 5: Restart core service ===
sudo systemctl restart guinevere-loops

# === VERIFY core restarted ===
systemctl status guinevere-loops | grep "active (running)" && echo "PASS" || echo "FAIL"
```

### 11.4 Verification

```bash
# === 9Router healthy ===
curl -s http://localhost:20128/health && echo "PASS" || echo "FAIL"

# === LLM calls still work via bot.py ===
# Send message in Discord → Guinevere responds (GPT-5.5 via 9Router)

# === Cost tracking still works (cost_tracker.py) ===
# Check PostgreSQL for cost data continuity

# === Data integrity ===
sudo -u postgres psql -d guinevere -c "SELECT 1" && echo "PASS" || echo "FAIL"
redis-cli -p 6380 -n 5 KEYS "cost:*" | head -5
```

### 11.5 Service Restoration Order

```
1. guinevere-loops.service    → RESTART (picks up restored session_adapter.py)
2. guinevere-discord.service  → Already running
```

### 11.6 Time Estimate

**< 2 minutes.**

### 11.7 Post-Rollback Actions

- Notify Faiz: "Phase 6 LLM routing rolled back. Hermes model/fallback/budget config reset. session_adapter.py restored. 9Router verified healthy. Cost tracking in PostgreSQL unchanged."

---

## 12. Phase 7 Rollback — Hardening & Monitoring

### 12.1 Pre-Conditions

- [ ] Phases 2-6 are complete and verified
- [ ] Existing monitoring stack (Prometheus/Grafana/Loki) is functional
- [ ] Existing backup system (rclone → S3 + R2) is functional
- [ ] Performance baseline data exists
- [ ] Pre-Phase-7 git tag exists

### 12.2 Rollback Trigger

| Condition | Detection |
|---|---|
| `hermes cron` jobs conflict with existing APScheduler jobs | Two schedulers fire same job → duplicate rituals |
| `hermes logs` monitoring consumes excessive disk | `df -h` → log partition filling rapidly |
| `hermes backup` interferes with existing rclone backup | Two systems writing to same files |
| `hermes checkpoints` disk space excessive | Checkpoint directory grows beyond expected |
| Performance benchmark shows >10% regression | Compare `hermes gateway status` vs pre-Phase-7 baseline |

### 12.3 Commands

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
systemctl status guinevere-scheduler | grep "active (running)" && echo "PASS" || echo "FAIL"
```

### 12.4 Verification

```bash
# === All systems operational ===
sudo -u postgres psql -d guinevere -c "SELECT 1" && echo "PASS" || echo "FAIL"
redis-cli -p 6380 PING && echo "PASS" || echo "FAIL"

# === Monitoring stack intact ===
curl -s http://localhost:9090/-/healthy && echo "PASS: Prometheus" || echo "CHECK: Prometheus"
curl -s http://localhost:3000/api/health && echo "PASS: Grafana" || echo "CHECK: Grafana"

# === Existing backup system intact ===
rclone ls idcloudhost:guinevere-dr-backups/ | head -3
# Expected: Existing backup files visible

# === No duplicate jobs ===
systemctl list-timers | grep guinevere
# Expected: Only pre-existing timers

# === Disk space normal ===
df -h /var/log/
# Expected: Usage within normal range
```

### 12.5 Service Restoration Order

```
1. guinevere-scheduler.service  → RESTART (picks up restored APScheduler config)
2. guinevere-discord.service    → Already running (if Phase 2 not cutover)
```

### 12.6 Time Estimate

**< 2 minutes.**

### 12.7 Post-Rollback Actions

- Notify Faiz: "Phase 7 hardening rolled back. Hermes cron/backup disabled. Original APScheduler restored. guinevere-scheduler.service restarted. Monitoring stack and backup system verified intact."

---

## 13. Global Emergency Rollback — All Phases at Once

### 13.1 Rollback Trigger

| Condition | Detection |
|---|---|
| Multiple safety features fail simultaneously | 3+ Phase 1 safety tests fail |
| Discord completely unreachable | No response from Guinevere > 5 minutes |
| Budget spike (cost > 5x baseline) | `hermes insights` shows massive spend |
| Faiz invokes emergency rollback | "rollback all" / "kembalikan semua" in Discord |
| Hermes gateway crashes repeatedly | Crash loop (>3 restarts in 5 minutes) |

### 13.2 Pre-Conditions

- [ ] Pre-migration snapshot exists (Section 4): git tag, pg_dump, pip freeze
- [ ] `guinevere-discord.service` systemd unit file is intact (not deleted)
- [ ] Discord bot token is available (SOPS-decrypted from `secrets/discord-secrets.yaml`)
- [ ] Faiz is available to verify Discord functionality after rollback

### 13.3 Commands

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
    git checkout -- src/mcp/ src/persona/
    rm -rf plugins/
fi
echo "STEP 3: Code restored from $PRE_TAG"

# === STEP 4: Remove all Phase 1-7 created files ===
rm -rf plugins/
rm -f config/hermes/hooks.yaml config/hermes/mcp-servers.yaml
rm -f ~/.hermes/SOUL.md
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
    echo "STEP 6: Pip packages restored"
else
    echo "STEP 6: No pip freeze snapshot found — skipping"
fi

# === STEP 7: Restart all Guinevere services ===
sudo systemctl restart guinevere-loops
sudo systemctl restart guinevere-discord
sudo systemctl restart guinevere-mcp
sudo systemctl restart guinevere-scheduler
sudo systemctl restart guinevere-surveillance
sudo systemctl restart guinevere-monitoring
sudo systemctl restart guinevere-obscura
echo "STEP 7: All Guinevere services restarted"

# === STEP 8: Wait for services to stabilize ===
sleep 5

# === STEP 9: Verify critical services ===
echo ""
echo "=== GLOBAL ROLLBACK VERIFICATION ==="
for svc in guinevere-discord guinevere-loops guinevere-mcp \
           guinevere-scheduler guinevere-surveillance guinevere-monitoring guinevere-obscura; do
    STATUS=$(systemctl is-active "$svc" 2>/dev/null)
    echo "  $svc: $STATUS"
done

echo ""
echo "--- Hermes Status ---"
hermes gateway status 2>/dev/null || echo "  Gateway: not running (expected)"

echo ""
echo "--- Data Integrity ---"
sudo -u postgres psql -d guinevere -c "SELECT 'episodes' as tbl, count(*) FROM memory.episodes" -t 2>/dev/null
redis-cli -p 6380 PING 2>/dev/null && echo "  Redis: PONG" || echo "  Redis: CHECK"

echo ""
echo "=== GLOBAL ROLLBACK COMPLETE ==="
echo "Verify: Send 'HARD STOP' in Discord #guinevere-chat"
echo "Verify: Send '/status' in Discord #guinevere-chat"
```

### 13.4 Verification — Data Integrity

```bash
# === PostgreSQL data must be verified ===
sudo -u postgres psql -d guinevere -c "
  SELECT 'episodes' as tbl, count(*) FROM memory.episodes
  UNION ALL SELECT 'semantic_facts', count(*) FROM memory.semantic_facts
  UNION ALL SELECT 'mood_states', count(*) FROM persona.mood_states
  UNION ALL SELECT 'drift_log', count(*) FROM persona.drift_log
  UNION ALL SELECT 'episodes_dnr', count(*) FROM memory.episodes WHERE do_not_recall = true
  ORDER BY tbl;
"
# Compare counts with pre-migration values

# === Redis verification ===
redis-cli -p 6380 PING
redis-cli -p 6380 -n 4 KEYS "hermes:session:*" | wc -l
# Session keys may exist (bot.py uses DB4) — normal
```

### 13.5 Service Restoration Order

```
All Guinevere services restarted in Step 7.
Recommended restart order (if doing manually):
  1. guinevere-loops.service     (core dependency)
  2. guinevere-discord.service   (restores Discord immediately)
  3. guinevere-mcp.service
  4. guinevere-scheduler.service
  5. guinevere-surveillance.service
  6. guinevere-monitoring.service
  7. guinevere-obscura.service
```

### 13.6 Time Estimate

**< 5 minutes** total downtime.

### 13.7 Post-Rollback Actions

- Notify Faiz: "GLOBAL EMERGENCY ROLLBACK COMPLETE. All phases reverted to pre-migration state. bot.py active with all slash commands. Hermes gateway stopped and disabled. PostgreSQL data verified intact. Please verify: (1) HARD STOP works, (2) /status responds, (3) persona behaves normally."
- Document rollback log at `/home/guinevere/backups/global-rollback-YYYYMMDD-HHMMSS.log`

---

## 14. PostgreSQL Full Restore Procedure

### 14.1 When to Use

Use ONLY if Hermes accidentally wrote to PostgreSQL during migration. This should NEVER happen because the hybrid architecture keeps PostgreSQL as primary write authority and Hermes memory as read-only supplement.

### 14.2 Trigger Conditions

| Trigger | Detection |
|---|---|
| Unexpected rows in PostgreSQL tables | Compare row counts before/after each phase |
| Hermes session data in wrong schema | Query `memory.episodes` for unexpected session_id patterns |
| Classification field corrupted | `SELECT DISTINCT classification FROM memory.episodes` → unexpected values |
| DNR flag reversed | `SELECT count(*) FROM memory.episodes WHERE do_not_recall = true` → count changed |

### 14.3 Pre-Conditions

- [ ] Pre-migration `pg_dump` file exists at `/home/guinevere/backups/pre-migration-*.dump`
- [ ] Dump file is uncorrupted: `pg_restore --list /home/guinevere/backups/pre-migration-*.dump | head`
- [ ] Offsite copies verified (idcloudhost S3 + Cloudflare R2)
- [ ] ALL Hermes gateway processes stopped
- [ ] `guinevere-discord.service` stopped (prevents new writes during restore)
- [ ] Faiz has approved the restore (destructive operation)

### 14.4 Commands — Full Database Restore

```bash
# ╔══════════════════════════════════════════════════════════════╗
# ║     POSTGRESQL FULL RESTORE — DESTRUCTIVE OPERATION         ║
# ║     Estimated downtime: 10-30 minutes                       ║
# ╚══════════════════════════════════════════════════════════════╝

# === STEP 0: STOP EVERYTHING ===
hermes gateway stop
sudo systemctl stop guinevere-discord guinevere-loops guinevere-mcp guinevere-scheduler guinevere-surveillance

# === VERIFY all stopped ===
systemctl is-active guinevere-discord guinevere-loops
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
echo "Exit code: $?"
# Expected: 0 (success)

# === STEP 5: Verify data integrity ===
sudo -u postgres psql -d guinevere -c "
  SELECT schemaname, count(*) as table_count 
  FROM pg_tables 
  WHERE schemaname IN ('memory','persona','surveillance','financial','projects','social','agents','consent','security','audit','ops','extensions')
  GROUP BY schemaname 
  ORDER BY schemaname;
"
# Expected: All 12 schemas present

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
sudo systemctl start guinevere-loops
sleep 3
sudo systemctl start guinevere-discord guinevere-mcp guinevere-scheduler guinevere-surveillance guinevere-monitoring guinevere-obscura

# === VERIFY all services running ===
for svc in guinevere-discord guinevere-loops guinevere-mcp \
           guinevere-scheduler guinevere-surveillance guinevere-monitoring guinevere-obscura; do
    STATUS=$(systemctl is-active "$svc")
    echo "$svc: $STATUS"
done
```

### 14.5 Selective Table Restore

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

| Scenario | Time |
|---|---|
| Small (< 100MB) | **< 5 minutes** |
| Medium (100MB-1GB) | **< 15 minutes** |
| Large (> 1GB) | **< 30 minutes** |
| Selective table restore | **< 2 minutes** |

### 14.7 Post-Rollback Actions

- Notify Faiz BEFORE: "DATABASE RESTORE REQUIRED. Stopping all services. Emergency backup created. Proceeding with full restore from pre-migration dump. Downtime estimated: [X] minutes."
- Notify Faiz AFTER: "Database restore complete. All 12 schemas verified. Please verify: (1) /status works, (2) memory recall correct, (3) persona behavior normal."

---

## 15. Redis Flush Procedure (DB-Specific)

### 15.1 When to Use

Use when Hermes session data in Redis needs to be cleared without affecting other Guinevere data. Redis holds only ephemeral/session data — no canonical data lives in Redis.

### 15.2 Flush Specific DB

```bash
# === Flush only Hermes session DB (DB3 — Sessions) ===
redis-cli -p 6380 -n 3 FLUSHDB

# === Flush only Session cache DB (DB4 — bot.py sessions) ===
redis-cli -p 6380 -n 4 FLUSHDB

# === Flush only Rate limiting DB (DB5) ===
redis-cli -p 6380 -n 5 FLUSHDB

# === Flush only Consent cache DB (DB2) ===
redis-cli -p 6380 -n 2 FLUSHDB

# === NEVER RUN: Flush ALL databases ===
# redis-cli -p 6380 FLUSHALL    # FORBIDDEN — destroys all Guinevere Redis data
```

### 15.3 Clear Hermes-Specific Redis Keys

```bash
# === Clear all Hermes-related keys in DB5 (safety state) ===
redis-cli -p 6380 -n 5 KEYS "safety_state:*" | while read key; do
    redis-cli -p 6380 -n 5 DEL "$key"
done

# === Clear all Hermes session keys in DB4 ===
redis-cli -p 6380 -n 4 KEYS "hermes:session:*" | while read key; do
    redis-cli -p 6380 -n 4 DEL "$key"
done

# === Clear all Hermes cost tracking keys in DB5 ===
redis-cli -p 6380 -n 5 KEYS "hermes:cost:*" | while read key; do
    redis-cli -p 6380 -n 5 DEL "$key"
done
```

### 15.4 Verification

```bash
# === Verify DB3 is empty after flush ===
redis-cli -p 6380 -n 3 DBSIZE
# Expected: (integer) 0

# === Verify other DBs unaffected ===
for db in 0 1 2 4 5; do
    echo "DB$db: $(redis-cli -p 6380 -n $db DBSIZE)"
done
# Expected: Normal counts for DB0,1,2,4,5
```

### 15.5 Time Estimate

**< 5 seconds.**

---

## 16. Discord Cutover Rollback — Hermes Gateway → bot.py

### 16.1 Zero-Visible-Downtime Procedure

This is the single highest-risk rollback. Goal: zero user-visible downtime.

### 16.2 The Cutover State

```
BEFORE CUTOVER:
  guinevere-discord.service    ACTIVE    ← handling Discord
  hermes-gateway.service       ACTIVE    ← shadow mode

AFTER CUTOVER:
  guinevere-discord.service    STOPPED   ← disabled
  hermes-gateway.service       ACTIVE    ← primary
```

### 16.3 Commands — Ultra-Fast Variant

```bash
# === Single-line rollback (< 10 seconds downtime) ===
hermes gateway stop && sudo systemctl start guinevere-discord

# bot.py connects to Discord WebSocket in ~3-5 seconds.
# Messages sent during those 3-5 seconds are queued by Discord.
```

### 16.4 Commands — Full Variant

```bash
# ╔══════════════════════════════════════════════════════════════╗
# ║  DISCORD CUTOVER ROLLBACK — Hermes → bot.py                 ║
# ║  Estimated downtime: < 2 minutes                            ║
# ╚══════════════════════════════════════════════════════════════╝

# === STEP 1: Stop Hermes gateway ===
hermes gateway stop
echo "$(date '+%H:%M:%S') Hermes gateway stopped — rollback begins"

# === STEP 2: Immediately start bot.py ===
sudo systemctl start guinevere-discord
echo "$(date '+%H:%M:%S') bot.py started"

# === STEP 3: Wait for bot.py to connect ===
sleep 5

# === STEP 4: Verify bot.py is handling messages ===
systemctl status guinevere-discord | grep "active (running)"
# Expected: "Active: active (running)"

# === STEP 5: Disable Hermes gateway auto-start ===
sudo systemctl disable hermes-gateway 2>/dev/null || true
sudo systemctl stop hermes-gateway 2>/dev/null || true

# === STEP 6: Log the rollback ===
echo "$(date): Discord cutover rolled back. Hermes → bot.py." \
  >> /home/guinevere/backups/rollback-log.txt
```

### 16.5 Post-Rollback Discord Verification

```bash
# === Check bot.py logs for successful connection ===
sudo journalctl -u guinevere-discord -n 20 --no-pager | grep -i "ready\|connected\|logged in"
# Expected: "Logged in as Guinevere"

# === Test HARD STOP ===
# Send "HARD STOP" in Discord → instant neutral response

# === Test slash commands ===
# /status, /mood, /help — all must work

# === Verify no Hermes gateway residue ===
hermes gateway status 2>&1 | grep -qi "not running" && echo "PASS" || echo "CHECK"
```

### 16.6 Time Estimate

**< 10 seconds** (ultra-fast variant). **< 2 minutes** (full variant with verification).

---

## 17. Hermes Backup & Checkpoint Usage

### 17.1 Before Each Phase — Create Checkpoint

```bash
hermes checkpoints create --label "pre-phaseN-$(date +%Y%m%d-%H%M%S)"
```

### 17.2 Before Each Step — Create Backup

```bash
hermes backup create --label "pre-phaseN-stepM-$(date +%Y%m%d-%H%M%S)"
```

### 17.3 Restore to a Checkpoint

```bash
# === LIST all checkpoints ===
hermes checkpoints --list

# === RESTORE to checkpoint ID 1 (pre-migration baseline) ===
hermes checkpoints --restore 1

# === VERIFY ===
hermes checkpoints --list
```

### 17.4 What Hermes Backup Covers vs What It Doesn't

| System | What It Backs Up | Rollback Use |
|---|---|---|
| `hermes backup` | Hermes config, secrets, session state | Per-step rollback |
| `hermes checkpoints` | Hermes state snapshot | Per-phase rollback |
| `pg_dump` | All PostgreSQL data | Database restore (Section 14) |
| `git` | All source code | Code rollback (Section 18) |
| `rclone → S3 + R2` | Offsite pg_dump + configs | DR scenario (ADR-032) |

**Critical**: Hermes backup does NOT back up PostgreSQL, Redis, or custom plugins. Those have their own backup mechanisms.

---

## 18. Git-Based Rollback Reference

### 18.1 File-Level Rollback

```bash
cd /home/guinevere/code/guinevere
PRE_TAG=$(git tag | grep "pre-hermes-migration" | tail -1)

# Single file
git checkout "$PRE_TAG" -- src/discord/bot.py

# Directory
git checkout "$PRE_TAG" -- src/mcp/

# Multiple files
git checkout "$PRE_TAG" -- src/hermes/session_adapter.py src/hermes/memory_bridge.py src/persona/yandere_fsm.py
```

### 18.2 Per-Phase Git Restore Reference

| Phase | Files to Restore |
|---|---|
| Phase 0 | `requirements.txt`, `config/hermes/config.yaml` |
| Phase 1 | N/A (new files created — just delete them) |
| Phase 2 | `src/discord/bot.py`, `src/discord/commands.py` |
| Phase 3 | `src/hermes/memory_bridge.py` |
| Phase 4 | `src/mcp/manager.py`, `src/mcp/auth_matrix.py`, `src/mcp/tools/` |
| Phase 5 | N/A (just `rm -rf plugins/` and `rm ~/.hermes/SOUL.md`) |
| Phase 6 | `src/hermes/session_adapter.py` |
| Phase 7 | `src/persona/ritual_scheduler.py` |

### 18.3 What Git Rollback Does NOT Cover

| Not Covered | Recovery Method |
|---|---|
| PostgreSQL data | `pg_restore` (Section 14) |
| Redis data | Ephemeral — nothing to restore |
| Hermes config state (`~/.hermes/`) | `hermes checkpoints --restore` |
| Installed pip packages | `pip install -r` from frozen requirements |
| Systemd service state | `systemctl start/stop/enable/disable` |
| SOUL.md (`~/.hermes/SOUL.md`) | `rm` or `git checkout` if in repo |

---

## 19. Systemd Service Health Check Script

```bash
#!/bin/bash
# Save as: /home/guinevere/scripts/check-all-services.sh
# Usage: bash check-all-services.sh

echo "=== Guinevere Service Health Check ==="
SERVICES=(
    "guinevere-discord"
    "guinevere-mcp"
    "guinevere-loops"
    "guinevere-scheduler"
    "guinevere-surveillance"
    "guinevere-monitoring"
    "guinevere-obscura"
)

for svc in "${SERVICES[@]}"; do
    STATUS=$(systemctl is-active "$svc" 2>/dev/null)
    if [ "$STATUS" = "active" ]; then
        echo "  ✅ $svc: $STATUS"
    else
        echo "  ❌ $svc: $STATUS"
    fi
done

echo ""
echo "=== Hermes Gateway ==="
hermes gateway status 2>/dev/null || echo "  Gateway not running"

echo ""
echo "=== PostgreSQL (port 5433) ==="
psql -U guinevere_core -d guinevere -c "SELECT 1" -t 2>/dev/null && echo "  ✅ PostgreSQL: accessible" || echo "  ❌ PostgreSQL: NOT accessible"

echo ""
echo "=== Redis (port 6380) ==="
redis-cli -p 6380 PING 2>/dev/null && echo "  ✅ Redis: PONG" || echo "  ❌ Redis: NOT accessible"

echo ""
echo "=== 9Router (port 20128) ==="
curl -s http://localhost:20128/health 2>/dev/null && echo "  ✅ 9Router: responding" || echo "  ❌ 9Router: NOT responding"
```

---

## 20. Rollback Time Estimates — Summary Table

| Scenario | Trigger | Downtime | Data Loss Risk |
|---|---|---|---|
| Phase 0 rollback | Package breaks Hermes | **< 5 min** | None |
| Phase 1 rollback | Safety test fails | **< 3 min** | None |
| Phase 2 shadow mode | Gateway unstable, bot.py still primary | **< 1 min** | None |
| Phase 2 cutover → bot.py | HARD STOP broken, no Discord response | **< 2 min** | None |
| Phase 3 rollback | Memory recall quality drops | **< 3 min** | None |
| Phase 4 rollback | Auth matrix bypass | **< 2 min** | None |
| Phase 5 rollback | Persona drift | **< 2 min** | None |
| Phase 6 rollback | LLM routing broken | **< 2 min** | None |
| Phase 7 rollback | Cron conflict | **< 2 min** | None |
| **Global emergency** | Multiple phases fail simultaneously | **< 5 min** | None |
| **PostgreSQL full restore** | Hermes wrote to DB accidentally | **10-30 min** | Current data replaced |
| **Discord cutover → bot.py** | Gateway failure after cutover | **< 10 sec** | None |

### 20.1 Worst-Case Scenario

**Hermes gateway corrupts PostgreSQL + Discord is down:**

```
1. hermes gateway stop                              (< 1 sec)
2. sudo systemctl start guinevere-discord           (< 10 sec — Discord back)
3. PostgreSQL restore (Section 14)                  (10-30 min — background)

Discord is back in < 10 seconds. Database restore runs while bot.py handles messages.
```

---

## 21. Post-Rollback Verification Checklist

After ANY rollback, verify:

```bash
# --- Service Health ---
systemctl is-active guinevere-discord guinevere-mcp guinevere-loops \
  guinevere-scheduler guinevere-surveillance guinevere-monitoring guinevere-obscura
# Expected: all "active"

# --- Hermes Disengaged ---
hermes gateway status 2>&1 | grep -qi "not running" && echo "PASS" || echo "CHECK"

# --- PostgreSQL ---
sudo -u postgres psql -d guinevere -c "SELECT count(*) FROM memory.episodes"
# Expected: Same count as pre-rollback

# --- Redis ---
redis-cli -p 6380 PING
# Expected: PONG

# --- 9Router ---
curl -s http://localhost:20128/health && echo "PASS" || echo "FAIL"

# --- HARD STOP (most critical) ---
# Send "HARD STOP" in Discord → neutral response, zero LLM call

# --- Slash Commands ---
# /status, /mood, /help → all respond correctly

# --- Persona Behavior ---
# Send a casual message → Guinevere responds with expected persona tone

# --- No Migration Artifacts ---
ls plugins/ 2>/dev/null && echo "WARNING: plugins/ exists" || echo "PASS"
ls ~/.hermes/SOUL.md 2>/dev/null && echo "WARNING: SOUL.md exists" || echo "PASS"
```

---

## 22. Footer

| Field | Value |
|---|---|
| Report | 03-rollback-procedures.md |
| Series | Hermes Migration Plan — 10-Part Research Wave |
| Date | 2026-06-04 |
| Status | Complete |
| Author | Guinevere (Sisyphus-Junior — Agent 3/10) |
| Sources | ADR-035 (§Rollback Plan), 06-rollback-strategy.md (2,291 lines), MASTER-RESTRUCTURE-PLAN.md, systemd/ (7 service files), PROGRESS.md |
| Binding ADRs | ADR-025, ADR-032, ADR-035 |
| Rollback Coverage | 8 phases (0-7) + Global Emergency + PostgreSQL Restore + Redis Flush + Discord Cutover |
| Total Copy-Pasteable Commands | 200+ |
| Ports Used | 5433 (PostgreSQL), 6380 (Redis), 8000 (API), 20128 (9Router), 9222 (Obscura CDP) |
| Service Names | Exact match from `systemd/` directory |

> **Every command in this document is copy-pasteable. Every step has a verification command. `hermes gateway stop` is always the first step. PostgreSQL is the primary write authority — rollback never involves data migration. bot.py is always the safe harbor.**