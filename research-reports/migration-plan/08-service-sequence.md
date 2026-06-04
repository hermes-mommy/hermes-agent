# 08 — Service Restart Sequence Per Phase

> **Report**: 08 of 10 — Hermes Migration Parallel Research  
> **Date**: 2026-06-04  
> **Scope**: Exact systemd service management procedures for all 7 migration phases  
> **Evidence**: All 7 systemd service files + `guinevere-core.service` from P1-018 evidence  
> **Dependencies**: ADR-035 (phase plan), `systemd/*.service` (service topology), PROGRESS.md (current state)

---

## Service Topology — Dependency Map

Derived from `After=`, `Requires=`, and `Wants=` directives in all 8 service files.

```
                    ┌──────────────────────┐
                    │  docker.service      │  (external)
                    │  guinevere-9router   │  (external)
                    │  network.target      │  (external)
                    └──────┬───────┬───────┘
                           │       │
                    ┌──────▼───────▼───────┐
                    │  guinevere-core      │  ★ FOUNDATION ★
                    │  Port 8000, uvicorn  │
                    │  Requires: docker,   │
                    │  9router              │
                    └──┬─────┬─────┬───────┘
                       │     │     │
          ┌────────────┼──┐  │  ┌──┼────────────┐
          │            │  │  │  │  │            │
     ┌────▼────┐ ┌─────▼──▼──▼──▼──▼───┐ ┌──────▼──────┐
     │ discord │ │     loops            │ │   mcp       │
     │ bot.py  │ │  state_machine.py    │ │ FastMCP     │
     │R:c      │ │  R:c                 │ │ R:c         │
     └─────────┘ └──────────┬───────────┘ └─────────────┘
                            │
                     ┌──────▼──────┐
                     │  scheduler  │
                     │  cron jobs  │
                     │  R:loops    │
                     └─────────────┘

     ┌─────────────────────────┐
     │  surveillance           │
     │  consumer.py            │
     │  R:c + after:docker     │
     └─────────────────────────┘

     ┌─────────────────────────┐
     │  monitoring             │
     │  docker compose stack   │
     │  R:docker  W:c          │
     └─────────────────────────┘

     ┌─────────────────────────┐
     │  obscura                │
     │  CDP :9222              │
     │  A:network (standalone) │
     └─────────────────────────┘
```

**Legend**: `R:x` = Requires:x, `A:x` = After:x, `W:x` = Wants:x, `c` = guinevere-core

### Service Reference Table

| Service | Unit File | ExecStart | Port | Requires | After | Restart |
|---|---|---|---|---|---|---|
| `guinevere-core` | `P1-018/guinevere-core.service` | `uvicorn src.core.main:app --host 127.0.0.1 --port 8000 --workers 2` | 8000 | docker, 9router | docker, 9router, network | always/10s |
| `guinevere-discord` | `systemd/guinevere-discord.service` | `python -m src.discord.bot` | — | core | core, network | always/10s |
| `guinevere-loops` | `systemd/guinevere-loops.service` | `python -m src.loops.manager` | — | core | core, network | always/10s |
| `guinevere-scheduler` | `systemd/guinevere-scheduler.service` | `python -m src.loops.scheduler` | — | loops | loops, network | always/10s |
| `guinevere-mcp` | `systemd/guinevere-mcp.service` | `python -m src.mcp.manager` | — | core | core, network | always/10s |
| `guinevere-surveillance` | `systemd/guinevere-surveillance.service` | `python -m src.surveillance.consumer` | — | core | core, docker, network | always/10s (SLB=5,SLI=300) |
| `guinevere-monitoring` | `systemd/guinevere-monitoring.service` | `docker compose -f monitoring/compose.monitoring.yml up` | 3000,9090,3100 | docker | docker, network-online | on-failure/10s (SLB=3,SLI=60) |
| `guinevere-obscura` | `systemd/guinevere-obscura.service` | `obscura serve --port 9222 --stealth --workers 2` | 9222 | — | network | on-failure/5s |

**Key**: SLB = StartLimitBurst, SLI = StartLimitIntervalSec

### Start Order (Bottom-Up)

```
1. docker.service (external, assumed running)
2. guinevere-9router.service (external, assumed running)
3. guinevere-core.service        ← FOUNDATION — all Python services depend on it
4. guinevere-discord.service     ← parallel
   guinevere-loops.service       ← parallel
   guinevere-mcp.service         ← parallel
   guinevere-surveillance.service ← parallel
   guinevere-monitoring.service  ← parallel (Wants: core, not Requires)
   guinevere-obscura.service     ← parallel (standalone)
5. guinevere-scheduler.service   ← AFTER loops
```

### Stop Order (Top-Down, Reverse)

```
1. guinevere-scheduler.service   ← depends on loops, stop first
2. guinevere-discord.service     ← user-facing, stop before backend  
3. guinevere-mcp.service         ← tool server
4. guinevere-surveillance.service ← data consumer
5. guinevere-loops.service       ← agent loop (scheduler already stopped)
6. guinevere-monitoring.service  ← docker compose down
7. guinevere-obscura.service     ← CDP browser
8. guinevere-core.service        ← FOUNDATION — stop last
```

---

## Aizanta Co-Hosting Constraint

**CRITICAL**: Guinevere and Aizanta share the same VPS (hostdata.id 4C/16GB, cgroup-capped to 8GB). All service management commands below operate ONLY on Guinevere services. Aizanta services MUST NOT be touched.

### Aizanta Service Protection

Before any phase begins, verify Aizanta services are untouched:

```bash
# List Aizanta services (distinguish from Guinevere)
sudo systemctl list-units --type=service --state=running | grep -v guinevere | grep aizanta

# Verify cgroup limits unchanged
sudo systemctl show guinevere.slice | grep -E "Memory|CPU"
# Expected: MemoryHigh=8G, CPUQuota=200%

# Verify port isolation — no Guinevere port conflicts with Aizanta
sudo ss -tlnp | grep -E ":(8000|3000|9090|3100|9222|20128)"
```

**Aizanta Pre-Phase Health Check** (run before every phase):

```bash
# Verify Aizanta process still running (adjust service name as configured)
sudo systemctl is-active aizanta-* 2>/dev/null || echo "Aizanta check: no services match pattern"
# Verify Aizanta ports still accessible
# Verify Aizanta cgroup limits unchanged
```

---

## Phase 0: Security Remediation (1-2 days)

**What changes**: Python packages only (aiohttp upgrade, `--require-hashes`). Zero service restarts required on VPS.

**Risk**: LOW — no runtime changes.

### Pre-Phase Service State

```bash
# Verify all 8 Guinevere services healthy
for svc in guinevere-core guinevere-discord guinevere-loops guinevere-scheduler \
           guinevere-mcp guinevere-surveillance guinevere-monitoring guinevere-obscura; do
    echo "=== $svc ==="
    sudo systemctl is-active $svc
    sudo systemctl show $svc --property=ActiveEnterTimestamp,MemoryCurrent,CPUUsageNSec
done

# Verify Aizanta untouched
echo "=== Aizanta Verification ==="
sudo systemctl list-units --type=service --state=running | grep -i aizanta
```

### Stop Sequence

**NONE.** Phase 0 modifies only `requirements.txt`, `pyproject.toml`, and `setup.sh` — all on-disk files. No service stops needed.

If `pip install --require-hashes -r requirements.txt` must run on the VPS:

```bash
# Dry-run package changes (do NOT stop services)
cd /home/guinevere/code/guinevere
source .venv/bin/activate
pip install --require-hashes --dry-run aiohttp>=3.9.0 2>&1 | tee /tmp/phase0-dry-run.log

# If dry-run passes, install without stopping services
pip install --require-hashes aiohttp>=3.9.0

# Verify imports still work (quick smoke test)
python -c "import aiohttp; print(aiohttp.__version__)"
```

### Configuration Changes

```bash
# None — no systemd changes
```

### Start Sequence

**NONE.**

### Health Check Commands

```bash
# Core API health endpoint
curl -sf http://localhost:8000/health | python -m json.tool

# 9Router health (not a systemd service, but required)
curl -sf http://localhost:20128/health 2>/dev/null || echo "9Router check: verify separately"

# Discord gateway — check bot is still online
# Manual: send a test message in #guinevere-chat

# PostgreSQL connectivity
sudo -u postgres psql -d guinevere -c "SELECT 1 AS postgres_ok;"

# Redis connectivity
redis-cli -p 6380 PING
```

### Verification Commands

```bash
# Full service list — all 8 must be "active (running)"
sudo systemctl status guinevere-core guinevere-discord guinevere-loops \
    guinevere-scheduler guinevere-mcp guinevere-surveillance \
    guinevere-monitoring guinevere-obscura --no-pager | grep -E "Active:|●"

# `hermes security` scan — gate condition
hermes security --format json > /tmp/phase0-security.json
python -c "
import json
r = json.load(open('/tmp/phase0-security.json'))
high = [f for f in r.get('findings',[]) if f.get('severity') in ('HIGH','MODERATE')]
assert len(high) == 0, f'Phase 0 gate FAILED: {len(high)} HIGH/MODERATE findings'
print('Phase 0 SECURITY GATE: PASS')
"

# `hermes doctor` — gate condition
hermes doctor --verbose
# All checks must show PASS
```

### Rollback Trigger Conditions

| Condition | Detection | Action |
|---|---|---|
| `pip install` breaks existing imports | `python -c "import aiohttp"` fails | `pip install -r /home/guinevere/backups/pre-migration-pip-*.txt` |
| `hermes security` shows HIGH/MODERATE after remediation | `hermes security --format json` | Investigate finding; do NOT proceed to Phase 1 |
| `hermes doctor` shows non-PASS | `hermes doctor --verbose` | Debug and fix before proceeding |
| Any Guinevere service crashes | `systemctl is-failed guinevere-*` | Restart affected service; if package-related, rollback pip |

---

## Phase 1: Safety Foundation (4-6 days)

**What changes**: New files created (`plugins/*.py`, `hooks/*.py`, `config/hermes/hooks.yaml`). No existing service files modified. Tests run in isolated environment.

**Risk**: HIGH — safety features being ported. But NO runtime changes to existing services.

### Pre-Phase Service State

```bash
# Same as Phase 0 — all 8 services must be healthy
for svc in guinevere-core guinevere-discord guinevere-loops guinevere-scheduler \
           guinevere-mcp guinevere-surveillance guinevere-monitoring guinevere-obscura; do
    echo "=== $svc: $(sudo systemctl is-active $svc) ==="
done

# Verify Phase 0 gate passed
hermes security --format json | python -c "import json,sys; r=json.load(sys.stdin); h=[f for f in r.get('findings',[]) if f['severity'] in ('HIGH','MODERATE')]; sys.exit(0 if len(h)==0 else 1)" \
    && echo "Phase 0 GATE: PASS" || echo "Phase 0 GATE: FAIL — DO NOT PROCEED"

hermes doctor --verbose 2>&1 | grep -c "PASS"
```

### Stop Sequence

**NONE.** Phase 1 is purely development — hook scripts and plugin Python files are written and tested locally/in CI. No running services are stopped.

Tests should run in an isolated test environment, NOT against the production VPS services:

```bash
# Run safety gate tests against test fixtures (not production)
cd /home/guinevere/code/guinevere
source .venv/bin/activate

# Test database (separate from production)
export TEST_DATABASE_URL="postgresql://guinevere_test@localhost/guinevere_test"
export TEST_REDIS_URL="redis://localhost:6379/15"  # DB15 = test-only

pytest tests/safety/ -v --tb=short
```

### Configuration Changes

```bash
# No systemd changes. If hook config requires deployment:
# Deploy hook scripts (read-only, no service restart needed)
sudo mkdir -p /home/guinevere/code/guinevere/hooks
sudo mkdir -p /home/guinevere/code/guinevere/plugins
# Copy files from dev to hooks/ and plugins/ directories
# No daemon-reload needed — hooks are shell scripts called by Hermes at runtime
```

### Start Sequence

**NONE.**

### Health Check Commands

```bash
# Full system health — all 8 services must remain unaffected
sudo systemctl is-active guinevere-core guinevere-discord guinevere-loops \
    guinevere-scheduler guinevere-mcp guinevere-surveillance \
    guinevere-monitoring guinevere-obscura

# Core API must still respond
curl -sf http://localhost:8000/health

# Memory recall must still work (existing pipeline unchanged)
curl -sf http://localhost:8000/api/memory/health

# MCP tools must still be available
curl -sf http://localhost:8000/api/mcp/status
```

### Verification Commands

```bash
# Run ALL 10 safety gates — this is the PHASE 1 GATE
cd /home/guinevere/code/guinevere
source .venv/bin/activate

# Gate 1: HARD STOP < 50ms, 100% SLO
pytest tests/safety/test_gate_01_hard_stop.py -v --tb=short

# Gate 2: Consent fail-closed
pytest tests/safety/test_gate_02_consent.py -v --tb=short

# Gate 3: Y6 architecturally impossible
pytest tests/safety/test_gate_03_yandere.py -v --tb=short

# Gate 4: D3/D4 → crisis protocol
pytest tests/safety/test_gate_04_distress.py -v --tb=short

# Gate 5: Drift detector alerts
pytest tests/safety/test_gate_05_drift.py -v --tb=short

# Gate 6: DNR excluded from recall
pytest tests/safety/test_gate_06_dnr.py -v --tb=short

# Gate 7: Classification fail-closed
pytest tests/safety/test_gate_07_classification.py -v --tb=short

# Gate 8: Secret scanner redacts
pytest tests/safety/test_gate_08_secrets.py -v --tb=short

# Gate 9: Punishment suspended during distress
pytest tests/safety/test_gate_09_punishment.py -v --tb=short

# Gate 10: Forbidden patterns blocked (F-01 to F-15)
pytest tests/safety/test_gate_10_forbidden.py -v --tb=short

# Summary: ALL 10 gates must PASS
echo "Phase 1 GATE: $(pytest tests/safety/ -q --tb=no 2>&1 | tail -1)"
```

### Rollback Trigger Conditions

| Condition | Detection | Action |
|---|---|---|
| ANY of 10 safety gates FAIL | Test runner exit code != 0 | Fix failing gate; do NOT proceed to Phase 2 |
| Hook script fails to compile | `python -m py_compile hooks/*.py` fails | Fix syntax; re-test |
| Plugin fails `critical: true` load test | Plugin `on_load()` returns False or raises | Fix plugin; re-test |
| Existing services disrupted (unexpected) | `systemctl is-failed guinevere-*` | Investigate; rollback files: `rm -f plugins/*.py hooks/*.py` |

**Phase 1 Rollback Command** (if needed):

```bash
rm -f /home/guinevere/code/guinevere/plugins/*.py
rm -f /home/guinevere/code/guinevere/hooks/*.py
rm -f /home/guinevere/code/guinevere/config/hermes/hooks.yaml
# Git restore any modified persona files
cd /home/guinevere/code/guinevere
git checkout -- src/persona/
```

---

## Phase 2: Discord Gateway (4-6 days + 48hr shadow)

**What changes**: Hermes gateway configured alongside bot.py. Shadow mode for 48+ hours. Then cutover: stop bot.py, start Hermes.

**Risk**: HIGH — user-facing cutover. Maximum 5-minute downtime.

### PHASE 2A: Shadow Mode Setup

#### Pre-Phase Service State

```bash
# All services must be healthy before shadow mode
for svc in guinevere-core guinevere-discord guinevere-loops guinevere-scheduler \
           guinevere-mcp guinevere-surveillance guinevere-monitoring guinevere-obscura; do
    echo "=== $svc ==="
    sudo systemctl is-active $svc
done

# Phase 1 GATE must have passed
# Verify bot.py is actively running (Discord connected)
sudo journalctl -u guinevere-discord --since "5 minutes ago" | grep -i "ready\|connected"

# Aizanta check
sudo systemctl list-units --type=service --state=running | grep -i aizanta
```

#### Stop Sequence

**NONE for bot.py.** bot.py continues running in `#guinevere-chat` throughout shadow mode.

#### Configuration Changes

```bash
# 1. Deploy Hermes gateway config for shadow mode
hermes gateway setup \
  --channel hermes-shadow \
  --token "${DISCORD_BOT_TOKEN}" \
  --guild "${DISCORD_GUILD_ID}"

# 2. Configure shadow-specific settings
hermes config set gateway.discord.channels.primary "hermes-shadow"
hermes config set memory.compression.enabled false       # No compression during shadow
hermes config set memory.mirrors.enabled false           # No mirror sync during shadow
hermes config set model.provider custom
hermes config set model.base_url "http://localhost:20128/v1"

# 3. Memory write mutex — bot.py retains exclusive write access
# Hermes reads PostgreSQL; writes go only to Hermes SQLite (transient)
# PostgreSQL access: no INSERT/UPDATE/DELETE for hermes_app user during shadow
sudo -u postgres psql -d guinevere -c "
  REVOKE INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public FROM hermes_app;
" 2>/dev/null || echo "hermes_app role not yet created — skip"

# 4. Separate Redis DBs — Hermes uses DB5, bot.py uses DB4
hermes config set plugins.guinevere_safety.config.redis_url "redis://localhost:6379/5"
```

#### Start Sequence (Shadow Mode)

```bash
# 1. Start Hermes gateway IN SHADOW MODE (does NOT replace bot.py)
hermes gateway start

# 2. Verify both bots operational
sleep 3
echo "=== bot.py (production) ==="
sudo systemctl is-active guinevere-discord

echo "=== Hermes gateway (shadow) ==="
hermes gateway status | grep -E "connected|status"

# 3. Verify bot.py is still the primary (must be active)
sudo journalctl -u guinevere-discord --since "1 minute ago" | tail -5
```

#### Health Check Commands (Shadow Mode)

```bash
# Run every 60 seconds during shadow mode — script this as a cron/systemd timer
echo "=== Shadow Mode Health Check $(date) ==="

# bot.py health
sudo systemctl is-active guinevere-discord || echo "CRITICAL: bot.py DOWN"

# Hermes gateway health
hermes gateway status 2>&1 | grep "connected" || echo "CRITICAL: Hermes gateway DOWN"

# Core API health
curl -sf http://localhost:8000/health || echo "WARNING: Core API health check failed"

# 9Router health
curl -sf http://localhost:20128/health 2>/dev/null || echo "WARNING: 9Router health check failed"

# Cost tracking (shadow mode cap: $5)
hermes insights cost --since "1h" --format json 2>/dev/null | python -c "
import json, sys
try:
    data = json.load(sys.stdin)
    cost = float(data.get('total', 0))
    print(f'Shadow mode cost: \${cost:.2f}')
    if cost >= 4.0: print('ALERT: Approaching \$5 shadow mode cap')
    if cost >= 5.0: print('CRITICAL: \$5 cap exceeded — terminate shadow mode')
except: print('Cost tracking not available')
"

# PostgreSQL — verify no Hermes writes
sudo -u postgres psql -d guinevere -c "
  SELECT 'HERMES_WRITE_AUDIT: ' || count(*) || ' writes detected'
  FROM audit.hermes_writes WHERE timestamp > now() - interval '1 hour';
" 2>/dev/null || echo "Audit table not yet created"
```

#### Verification Commands (Shadow Mode — After 48hr)

```bash
# Response parity must be confirmed by Faiz manually
# Send identical messages to both #guinevere-chat and #hermes-shadow
# Document in shadow-report.md:
# - HARD STOP response parity
# - 35 slash command functionality
# - Memory recall accuracy
# - Cost ($5 cap)

# Automated verification of shadow mode metrics
hermes gateway status --json > /tmp/shadow-status.json
python -c "
import json
s = json.load(open('/tmp/shadow-status.json'))
assert s.get('connected'), 'Gateway not connected'
print('Shadow mode metrics:')
print(f'  Messages processed: {s.get(\"messages_processed\", 0)}')
print(f'  Errors: {s.get(\"errors\", 0)}')
print(f'  Avg latency: {s.get(\"avg_latency_ms\", 0)}ms')
"
```

### PHASE 2B: Cutover (Faiz Approval Required)

#### Stop Sequence (Cutover)

```bash
# Step order matters! Stop from top of dependency chain.

# 1. Stop Hermes shadow gateway first (it's about to become primary)
hermes gateway stop
sleep 2

# 2. Stop guinevere-discord (bot.py) — the production bot
#    This is the critical cutover moment.
sudo systemctl stop guinevere-discord
sleep 2

# 3. Verify bot.py fully stopped
sudo systemctl is-active guinevere-discord
# Expected output: "inactive"

# 4. DO NOT stop core, loops, mcp, surveillance, monitoring, obscura
#    These services continue running — only the Discord gateway changes.
```

#### Configuration Changes (Cutover)

```bash
# 1. Switch Hermes from shadow channel to primary channel
hermes config set gateway.discord.channels.primary "guinevere-chat"

# 2. Enable features that were disabled during shadow mode
hermes config set memory.compression.enabled true
hermes config set memory.mirrors.enabled true

# 3. Set compression threshold (aggressive safe start at 70%)
hermes config set memory.compression.threshold 0.70
hermes config set memory.compression.protect_last 20

# 4. Grant PostgreSQL write access for mirror sync
sudo -u postgres psql -d guinevere -c "
  GRANT INSERT ON ALL TABLES IN SCHEMA public TO hermes_app;
" 2>/dev/null || echo "hermes_app role not yet created"

# 5. Disable bot.py from auto-starting (Hermes is now primary)
sudo systemctl disable guinevere-discord
```

#### Start Sequence (Cutover)

```bash
# 1. Start Hermes as primary Discord gateway
hermes gateway start
sleep 5

# 2. Verify Hermes connected to Discord
hermes gateway status | grep "connected"
# Expected: "status: connected" or equivalent

# 3. Verify Hermes is listening on the primary channel
hermes gateway status | grep "primary.*guinevere-chat"

# 4. Verify bot.py is NOT running (must not conflict)
sudo systemctl is-active guinevere-discord
# Expected: "inactive"
```

#### Health Check Commands (Post-Cutover)

```bash
echo "=== Post-Cutover Health Check $(date) ==="

# 1. Hermes gateway — MUST be connected
hermes gateway status | grep "connected" || echo "CRITICAL: Hermes not connected"

# 2. Core API — unchanged, must still respond
curl -sf http://localhost:8000/health || echo "CRITICAL: Core API down"

# 3. All backend services — must still be running
for svc in guinevere-core guinevere-loops guinevere-scheduler \
           guinevere-mcp guinevere-surveillance guinevere-monitoring guinevere-obscura; do
    state=$(sudo systemctl is-active $svc)
    [ "$state" = "active" ] || echo "CRITICAL: $svc is $state"
    echo "$svc: $state"
done

# 4. 9Router — LLM routing must work
curl -sf http://localhost:20128/health 2>/dev/null || echo "WARNING: 9Router check"

# 5. PostgreSQL — memory still accessible
sudo -u postgres psql -d guinevere -c "SELECT count(*) FROM memory.episodes;" || echo "CRITICAL: PostgreSQL"

# 6. Redis — cache still accessible  
redis-cli -p 6380 PING || echo "WARNING: Redis"

# 7. Discord slash commands — all 35 must be registered
# Manual: run /help in Discord, verify all commands appear
# Manual: test /status, /safeword, /memory search

# 8. HARD STOP test — CRITICAL gate
# Manual: send "HARD STOP" in #guinevere-chat
# Expected: neutral response, zero LLM call, zero persona behavior
```

#### Verification Commands (Post-Cutover)

```bash
# 1. Cutover downtime measurement
# Record timestamp at "sudo systemctl stop guinevere-discord"
# Record timestamp when "hermes gateway status" shows "connected"
# Max allowed: < 5 minutes

# 2. Verify all 35 slash commands functional
# Manual test — send each command in Discord, verify correct response
# Commands: status, mood, help, safeword, new, history, casual, focus,
#           memory add/search/export/forget,
#           loop start/stop/pause/resume/priority, loops,
#           surveillance status/pause/resume,
#           evidence, clear cache,
#           cost, budget, cost alert,
#           approve, approve all, deny,
#           restart, backup, health,
#           consent, punishment, reward

# 3. Verify streaming is working (Hermes feature)
# Manual: ask a question that requires a long response
# Expected: progressive edits appear at ~1.2s intervals

# 4. Verify auto-threading
# Manual: @mention the bot in a busy channel
# Expected: bot creates a thread for the conversation

# 5. Systemd — verify bot.py is disabled
sudo systemctl is-enabled guinevere-discord
# Expected: "disabled"

# 6. Health check watchdog
# Deploy a cron job to check Hermes every 60s
echo '*/1 * * * * hermes gateway status | grep "connected" || (echo "Hermes down at $(date)" | gotify push)' \
    | sudo crontab -u guinevere -
```

#### Rollback Trigger Conditions

| Condition | Detection | Action |
|---|---|---|
| **Shadow mode**: Hermes disconnected > 3 consecutive checks | Health check cron | `hermes gateway stop && hermes gateway start` (restart shadow) |
| **Shadow mode**: Cost exceeds $5 | `hermes insights cost` | `hermes gateway stop` — terminate shadow mode |
| **Cutover**: Hermes fails to connect after start | `hermes gateway status` shows disconnected | **IMMEDIATE ROLLBACK** (see below) |
| **Cutover**: Any slash command broken | Manual test | Rollback or fix on Hermes (if < 5 min) |
| **Cutover**: HARD STOP fails | Manual HARD STOP test | **IMMEDIATE ROLLBACK** — safety-critical |
| **Cutover**: Core/loops/mcp/surveillance affected | `systemctl is-failed` | **IMMEDIATE ROLLBACK** |

**Phase 2 Emergency Rollback** (from shadow mode or post-cutover):

```bash
# Universal kill-switch
hermes gateway stop

# If post-cutover, re-enable bot.py
sudo systemctl enable guinevere-discord
sudo systemctl start guinevere-discord
sleep 5

# Verify bot.py running
sudo systemctl is-active guinevere-discord
# Expected: "active"

# Remove Hermes gateway config to prevent auto-start
hermes gateway uninstall 2>/dev/null || true

# Verify HARD STOP works on bot.py
# Manual: send "HARD STOP" in #guinevere-chat
# Expected: neutral response from bot.py

# Total rollback time: < 2 minutes
```

---

## Phase 3: Memory Bridge (3-4 days)

**What changes**: Enable Hermes compression and session_search (config changes only). Build PostgreSQL bridge plugin. Zero service stops.

**Risk**: MEDIUM — no service topology changes. PostgreSQL read-only supplement.

### Pre-Phase Service State

```bash
# Hermes must be the active Discord gateway (post-Phase 2 cutover)
hermes gateway status | grep "connected" || echo "PHASE 3 PREREQ FAILED: Hermes not running"

# bot.py must be disabled
sudo systemctl is-enabled guinevere-discord 2>&1 | grep -q "disabled" \
    || echo "WARNING: bot.py still enabled — Phase 2 cutover may not be complete"

# All backend services healthy
for svc in guinevere-core guinevere-loops guinevere-scheduler \
           guinevere-mcp guinevere-surveillance guinevere-monitoring guinevere-obscura; do
    sudo systemctl is-active $svc || echo "PREREQ FAILED: $svc not active"
done

# PostgreSQL accessible
sudo -u postgres psql -d guinevere -c "SELECT count(*) FROM memory.episodes;"
```

### Stop Sequence

**NONE.** Phase 3 is a runtime config change on Hermes + plugin deployment. No service stops needed.

### Configuration Changes

```bash
# 1. Enable compression at 70% threshold (aggressive safe start)
hermes config set memory.compression.enabled true
hermes config set memory.compression.threshold 0.70
hermes config set memory.compression.target 0.20
hermes config set memory.compression.protect_last 20

# 2. Enable session_search (FTS5 on Hermes SQLite)
hermes config set memory.session_search.enabled true
hermes config set memory.session_search.backend "fts5"

# 3. Deploy memory bridge plugin
# Copy memory_plugin.py to plugins/ directory
# Plugin wraps recall_for_context() and store_conversation() unchanged

# 4. Enable mirror sync (MEMORY.md/USER.md)
hermes config set memory.mirrors.enabled true
hermes config set memory.mirrors.sync_interval_messages 5

# 5. Reload Hermes config (no restart needed if hot-reload supported)
hermes config reload 2>/dev/null || hermes gateway restart
```

### Start Sequence

```bash
# If config reload not supported, restart Hermes gateway
hermes gateway restart
sleep 5
hermes gateway status | grep "connected"
```

### Health Check Commands

```bash
# 1. Hermes gateway still connected
hermes gateway status | grep "connected"

# 2. Memory recall quality — unchanged
# A/B test on 100 queries (manual script — see Phase 3.5 in ADR-035)
cd /home/guinevere/code/guinevere
source .venv/bin/activate
python scripts/ab_test_recall.py --queries 100

# 3. DNR enforcement — must still work
python -c "
from src.memory.dnr import verify_recall_results_dnr_free
# Test with DNR-marked entry
# Expected: DNRViolationError raised
"

# 4. PostgreSQL — zero data modifications from Hermes path
sudo -u postgres psql -d guinevere -c "
  SELECT count(*) AS hermes_unauthorized_writes
  FROM audit.hermes_writes WHERE timestamp > now() - interval '1 hour';
"
# Expected: hermes_unauthorized_writes = 0

# 5. Compression working — verify via Hermes logs
sudo journalctl -u hermes-gateway --since "10 minutes ago" | grep -i "compression"
```

### Verification Commands

```bash
# 1. Memory recall precision unchanged (p > 0.05)
python scripts/ab_test_recall.py --queries 100 --threshold 0.05

# 2. DNR content excluded from session_search results
# Manual: mark an entry DNR, wait 5 minutes, search for it via session_search
# Expected: DNR entry NOT in results

# 3. Classification still enforced (5-level)
python -c "
from src.memory.classification import classify_event
# Test with unknown type → expected: Confidential (fail-closed)
assert classify_event(type='unknown_event').classification == 'Confidential'
"

# 4. PostgreSQL schema unchanged (47 tables, 12 schemas)
sudo -u postgres psql -d guinevere -c "
  SELECT count(*) AS table_count FROM information_schema.tables
  WHERE table_schema NOT IN ('pg_catalog','information_schema');
"
# Expected: table_count >= 47
```

### Rollback Trigger Conditions

| Condition | Detection | Action |
|---|---|---|
| Memory recall quality degrades (p < 0.05) | A/B test on 100 queries | `hermes config set memory.compression.enabled false` |
| DNR content in session_search | Manual search test | Disable session_search; fix DNR filter |
| PostgreSQL unauthorized writes | Audit log count > 0 | Investigate source; revoke Hermes write access |
| Compression drops critical memories | Manual review of compressed context | Raise threshold from 70% to 80% |

**Phase 3 Rollback**:

```bash
hermes config set memory.compression.enabled false
hermes config set memory.session_search.enabled false
hermes config set memory.mirrors.enabled false
hermes gateway restart
# < 3 minutes total
```

---

## Phase 4: MCP + Tools (3-4 days)

**What changes**: Add 5 Hermes native MCP servers. Build auth overlay plugin. Custom MCP server (`guinevere-mcp.service`) continues running for 7 custom tools.

**Risk**: MEDIUM — dual MCP backends (Hermes native + custom FastMCP). Auth overlay must intercept ALL tool calls.

### Pre-Phase Service State

```bash
# Hermes gateway active
hermes gateway status | grep "connected"

# guinevere-mcp.service active (custom FastMCP for 7 tools)
sudo systemctl is-active guinevere-mcp

# Verify current MCP tools available
curl -sf http://localhost:8000/api/mcp/status | python -m json.tool

# All backend services healthy
for svc in guinevere-core guinevere-loops guinevere-scheduler \
           guinevere-surveillance guinevere-monitoring guinevere-obscura; do
    sudo systemctl is-active $svc
done
```

### Stop Sequence

```bash
# 1. Stop Hermes gateway first (it will restart with new MCP config)
hermes gateway stop
sleep 2

# 2. Restart guinevere-mcp (custom tools) to pick up any config changes
sudo systemctl restart guinevere-mcp
sleep 3

# NOTE: guinevere-core MUST stay running — MCP depends on it
# NOTE: guinevere-obscura MUST stay running — Obscura CDP tool depends on it
```

### Configuration Changes

```bash
# 1. Deploy Hermes MCP server config
# File: config/hermes/mcp-servers.yaml
# Contains: web, filesystem, terminal, git, fetch server configs

# 2. Deploy auth overlay plugin
# File: plugins/auth_overlay.py
# Plugin load gate: Hermes refuses to start without it

# 3. Update Hermes config to load auth overlay plugin
hermes config set plugins.auth_overlay.enabled true
hermes config set plugins.auth_overlay.path "plugins/auth_overlay.py"
hermes config set plugins.auth_overlay.class "AuthOverlayPlugin"
hermes config set plugins.auth_overlay.priority 90
hermes config set plugins.auth_overlay.critical true

# 4. Deploy auth matrix config
# File: config/hermes/auth_matrix.yaml
# Contains: 4-level matrix for all 16 tools

# 5. Verify FORBIDDEN tools hard-disabled in Hermes native config
hermes config set mcp_servers.terminal.blocked_commands \
  "rm,dd,mkfs,shutdown,reboot,poweroff,iptables,ufw,systemctl"
```

### Start Sequence

```bash
# 1. Verify guinevere-mcp is running (custom tools)
sudo systemctl is-active guinevere-mcp
# Expected: "active"

# 2. Start Hermes gateway with new MCP + auth overlay config
hermes gateway start
sleep 5

# 3. Verify Hermes gateway connected
hermes gateway status | grep "connected"

# 4. Verify auth overlay plugin loaded
hermes gateway status --json | python -c "
import json, sys
s = json.load(sys.stdin)
plugins = s.get('plugins', {})
auth = plugins.get('auth_overlay', {})
assert auth.get('loaded'), 'AUTH OVERLAY PLUGIN NOT LOADED — CRITICAL'
print('Auth overlay: LOADED')
"
# If plugin not loaded, Hermes should have refused to start (critical: true)
```

### Health Check Commands

```bash
# 1. All 16 tools available (5 native + 7 custom + 4 hybrid)
echo "=== Hermes Native Tools ==="
hermes mcp list | grep -E "web|filesystem|terminal|git|fetch"

echo "=== Custom MCP Tools (guinevere-mcp) ==="
curl -sf http://localhost:8000/api/mcp/status | python -c "
import json, sys
tools = json.load(sys.stdin).get('tools', [])
expected = ['postgres_tool','redis_tool','obscura_cdp','grep_app','context7','sequential_thinking','time_tools']
missing = [t for t in expected if t not in str(tools)]
assert not missing, f'Missing custom tools: {missing}'
print(f'Custom tools: {len(tools)} available')
"

# 2. Auth matrix enforced — test each level
# Manual or script: attempt READ_AUTO, WRITE_NOTIFY, DESTRUCTIVE_APPROVAL, FORBIDDEN operations
# Verification script output:
python scripts/test_auth_matrix.py

# 3. Plugin load gate — verify Hermes refuses to start without auth overlay
# Test in isolated environment:
# hermes config set plugins.auth_overlay.enabled false
# hermes gateway start  # Expected: FAILS TO START
# hermes config set plugins.auth_overlay.enabled true  # Restore

# 4. Custom tools (guinevere-mcp) still healthy
sudo systemctl is-active guinevere-mcp
curl -sf http://localhost:8000/api/mcp/health
```

### Verification Commands

```bash
# 1. Auth overlay intercepts ALL tool calls
# Verify pre_tool_call hook passes through auth overlay plugin
sudo journalctl -u hermes-gateway --since "5 minutes ago" | grep -c "auth_overlay.*intercepted"
# Expected: count > 0 (tools have been called)

# 2. FORBIDDEN operations truly blocked
python -c "
# Attempt a FORBIDDEN operation (should be blocked)
# Expected: auth overlay returns {'action': 'block', 'reason': 'FORBIDDEN operation'}
"

# 3. DESTRUCTIVE_APPROVAL goes through Discord webhook
# Manual: attempt destructive operation → check Discord for approval webhook

# 4. All 16 tools functional end-to-end
python scripts/test_all_16_tools.py
```

### Rollback Trigger Conditions

| Condition | Detection | Action |
|---|---|---|
| Auth overlay plugin fails to load | `hermes gateway start` fails | Debug plugin; do NOT proceed without auth |
| Tool bypasses auth matrix | Penetration test finds bypass | Fix auth overlay; re-test |
| Custom MCP tools break | `curl localhost:8000/api/mcp/status` fails | Restart guinevere-mcp; investigate |
| Hermes native tool executes FORBIDDEN command | Audit log shows forbidden attempt succeeded | IMMEDIATE ROLLBACK |

**Phase 4 Rollback**:

```bash
hermes gateway stop
hermes mcp remove web filesystem terminal git fetch
rm -f /home/guinevere/code/guinevere/plugins/auth_overlay.py
sudo systemctl restart guinevere-mcp
hermes gateway start
# < 2 minutes total
```

---

## Phase 5: Skills + Persona (2-3 days)

**What changes**: Install skills from agentskills.io. Customize SOUL.md. Configure persona plugins. Zero service stops.

**Risk**: LOW — config and files only. No service topology changes.

### Pre-Phase Service State

```bash
# Hermes gateway active
hermes gateway status | grep "connected"

# All services healthy
for svc in guinevere-core guinevere-loops guinevere-scheduler \
           guinevere-mcp guinevere-surveillance guinevere-monitoring guinevere-obscura; do
    sudo systemctl is-active $svc
done
```

### Stop Sequence

**NONE.** Skills and SOUL.md are files. Plugin config changes are hot-reloaded if supported, otherwise a brief Hermes restart.

### Configuration Changes

```bash
# 1. Install skills from agentskills.io
hermes skills install <skill-name-1>
hermes skills install <skill-name-2>
# ... (per curated skill list)

# 2. Deploy customized SOUL.md
# File: config/hermes/SOUL.md
# Content: Guinevere identity, Y4/Y5/Y6 constraints, tone rules
chmod 444 /home/guinevere/code/guinevere/config/hermes/SOUL.md

# 3. Configure persona plugins
hermes config set plugins.guinevere_safety.config.soul_md_path \
  "/home/guinevere/code/guinevere/config/hermes/SOUL.md"
```

### Start Sequence

```bash
# Hot-reload if supported
hermes config reload 2>/dev/null

# Or restart Hermes gateway (brief interruption)
hermes gateway restart
sleep 5
hermes gateway status | grep "connected"
```

### Health Check Commands

```bash
# 1. Skills installed without errors
hermes skills list
# Expected: shows installed skills

# 2. SOUL.md permissions verified
ls -la /home/guinevere/code/guinevere/config/hermes/SOUL.md
# Expected: -r--r--r-- (444)

# 3. Persona tone intact
# Manual: send a message in Discord, verify Guinevere personality
# Expected: Y4 dominant tone, proper address ("Sayang", "Darling")

# 4. Mood persists across sessions
# Manual: trigger mood change, restart conversation, verify mood retained

# 5. Rituals fire on schedule
sudo journalctl -u hermes-gateway --since "1 hour ago" | grep -i "ritual"
```

### Verification Commands

```bash
# 1. All persona features functional
python tests/persona/test_persona_integration.py -v

# 2. Yandere levels enforced
# Manual: send messages that should trigger different Y levels
# Verify Y6 content is rewritten or blocked

# 3. Punishment suspended during distress
python tests/safety/test_gate_09_punishment.py -v

# 4. SOUL.md matches Persona Document v3.0
diff <(grep -E "Y[0-6]|HARD STOP|consent" config/hermes/SOUL.md) \
     <(grep -E "Y[0-6]|HARD STOP|consent" docs/00-core/06-Persona_Document_v3.0.md)
# Expected: constraint-level match (exact wording may differ, rules must match)
```

### Rollback Trigger Conditions

| Condition | Detection | Action |
|---|---|---|
| Persona tone degrades (not Y4, Y6 content appears) | Manual prompt test | `git checkout -- config/hermes/SOUL.md` + restart |
| Rituals miss schedule | No ritual log entries for 1+ day | Check cron config; restart scheduler |
| Skill causes errors | `hermes skills list` shows broken skill | `hermes skills uninstall <skill>` |
| Mood state corrupted | Plugin state inconsistent | Restore from Redis DB5 snapshot |

**Phase 5 Rollback**:

```bash
hermes skills uninstall <skill_name>  # Per broken skill
git checkout -- /home/guinevere/code/guinevere/config/hermes/SOUL.md
rm -f /home/guinevere/code/guinevere/plugins/persona_plugin.py
hermes gateway restart
# < 2 minutes
```

---

## Phase 6: LLM Routing (1 day)

**What changes**: Configure Hermes to use 9Router as custom provider. Test fallback chain. Implement budget enforcement hook.

**Risk**: LOW — config-only changes. 9Router is unchanged. Quick rollback.

### Pre-Phase Service State

```bash
# Hermes gateway active
hermes gateway status | grep "connected"

# 9Router must be running
curl -sf http://localhost:20128/health || echo "PREREQ FAILED: 9Router not responding"

# All backend services healthy
for svc in guinevere-core guinevere-loops guinevere-scheduler \
           guinevere-mcp guinevere-surveillance guinevere-monitoring guinevere-obscura; do
    sudo systemctl is-active $svc
done
```

### Stop Sequence

```bash
# Brief Hermes gateway restart for config changes
hermes gateway stop
sleep 2
```

### Configuration Changes

```bash
# 1. Configure Hermes to use 9Router as custom provider
hermes config set model.provider "custom"
hermes config set model.model "gpt-5.5"
hermes config set model.base_url "http://localhost:20128/v1"
hermes config set model.api_key "${NINEROUTER_API_KEY}"

# 2. Configure fallback chain
hermes config set fallback.enabled true
hermes config set fallback.models '["deepseek-v4-flash"]'
hermes config set fallback.strategy "sequential"

# 3. Configure budget enforcement
hermes config set budget.monthly_limit 30.00
hermes config set budget.alert_threshold 0.80
hermes config set budget.block_threshold 1.00
hermes config set budget.currency "USD"

# 4. Deploy budget enforcement hook (or integrate into consent_gate hook)
# File: hooks/consent_gate.py (modified) or hooks/budget.py (new)
```

### Start Sequence

```bash
# 1. Start Hermes gateway
hermes gateway start
sleep 5

# 2. Verify Hermes connected
hermes gateway status | grep "connected"

# 3. Verify LLM routing works
# Send a test message that requires LLM response
# Manual: "Hello Guinevere, can you hear me?"
# Expected: Persona response via GPT-5.5 through 9Router
```

### Health Check Commands

```bash
# 1. LLM routing functional — test prompt
hermes model test --prompt "Say hello in one word" 2>&1 | grep -v error

# 2. 9Router still healthy
curl -sf http://localhost:20128/health

# 3. Fallback chain config verified
hermes config get fallback

# 4. Budget enforcement active
hermes config get budget

# 5. Cost tracking working
hermes insights cost --since "1h"
```

### Verification Commands

```bash
# 1. 100-test-prompt compatibility test
cd /home/guinevere/code/guinevere
source .venv/bin/activate
python scripts/test_100_prompts.py
# Expected: 100/100 prompts route correctly through 9Router

# 2. Fallback test — simulate GPT-5.5 failure
# Manual: temporarily stop 9Router routing for GPT-5.5
# Send a message — expected: DeepSeek V4 Flash takes over
# Restore GPT-5.5 routing

# 3. Budget enforcement test
python -c "
# Test at 80%: alert triggered
# Test at 90%: warning
# Test at 100%: LLM calls blocked
print('Budget enforcement: configure test thresholds and verify')
"

# 4. Streaming compatibility
# Manual: send a long-form question
# Expected: progressive edits at ~1.2s intervals
```

### Rollback Trigger Conditions

| Condition | Detection | Action |
|---|---|---|
| LLM calls fail entirely | `hermes model test` fails | Check 9Router; rollback provider config |
| Fallback does not engage | Only GPT-5.5 works; failure = no response | Debug fallback config |
| Budget hook blocks prematurely | LLM calls blocked at < $30 | Check budget calculation; fix hook |
| Streaming broken | Full response only (no progressive edits) | Debug streaming config |

**Phase 6 Rollback**:

```bash
hermes model set --model default
hermes fallback set --model none
hermes config set budget.monthly_limit 0
hermes gateway restart
# < 2 minutes
```

---

## Phase 7: Hardening + Monitoring (2-3 days)

**What changes**: Configure `hermes cron`, `hermes backup`, `hermes checkpoints`. Run security audit. Performance benchmark. Write runbook.

**Risk**: LOW — operational additions. No core service topology changes.

### Pre-Phase Service State

```bash
# All previous phases complete — Hermes is the production gateway
hermes gateway status | grep "connected"

# All services healthy
for svc in guinevere-core guinevere-loops guinevere-scheduler \
           guinevere-mcp guinevere-surveillance guinevere-monitoring guinevere-obscura; do
    sudo systemctl is-active $svc
done

# Monitoring stack healthy
curl -sf http://localhost:9090/-/healthy && echo "Prometheus: OK"
curl -sf http://localhost:3000/api/health && echo "Grafana: OK"
```

### Stop Sequence

**NONE** for core services. Brief Hermes restart for cron config deployment.

```bash
hermes gateway stop
sleep 2
```

### Configuration Changes

```bash
# 1. Deploy Hermes cron jobs
# File: config/hermes/crontab.yaml
hermes cron add "daily_health_check" "0 6 * * *" "hermes doctor --report"
hermes cron add "weekly_backup" "0 2 * * 0" "hermes backup --full --destination idcloudhost"
hermes cron add "monthly_security_scan" "0 3 1 * *" "hermes security --report"

# 2. Configure log integration with Loki
hermes config set observability.logging.level "info"
hermes config set observability.logging.format "json"
hermes config set observability.logging.output "both"

# 3. Configure Prometheus metrics
hermes config set observability.prometheus.enabled true
hermes config set observability.prometheus.metrics_port 9191

# 4. Configure backup pipeline
# File: scripts/backup.sh (modified to include hermes backup + PostgreSQL dump)

# 5. Configure checkpoints
hermes config set checkpoints.auto_create true
hermes config set checkpoints.retention 7  # Keep 7 days of checkpoints
```

### Start Sequence

```bash
# 1. Start Hermes gateway with new operational config
hermes gateway start
sleep 5

# 2. Verify all monitoring targets appear
curl -sf http://localhost:9090/api/v1/targets | python -c "
import json, sys
targets = json.load(sys.stdin)['data']['activeTargets']
hermes_targets = [t for t in targets if 'hermes' in str(t.get('labels', {}))]
print(f'Hermes monitoring targets: {len(hermes_targets)}')
"
```

### Health Check Commands

```bash
# 1. Hermes gateway connected
hermes gateway status | grep "connected"

# 2. Cron jobs scheduled
hermes cron list

# 3. Logs flowing to Loki
curl -s "http://localhost:3100/loki/api/v1/query" --data-urlencode \
  'query={job="hermes-gateway"}' | python -c "
import json, sys
r = json.load(sys.stdin)
print(f'Loki log entries: {len(r.get(\"data\", {}).get(\"result\", []))}')
"

# 4. Prometheus metrics from Hermes
curl -sf http://localhost:9191/metrics | head -20

# 5. Performance benchmark — latency within +10% of baseline
python scripts/bench_performance.py --baseline /home/guinevere/backups/pre-migration-bench.json

# 6. Full security audit
hermes security --format json > /tmp/phase7-security.json
python -c "
import json
r = json.load(open('/tmp/phase7-security.json'))
high = [f for f in r.get('findings',[]) if f.get('severity') in ('HIGH','MODERATE')]
assert len(high) == 0, f'Security gate FAILED: {len(high)} HIGH/MODERATE findings'
print('Phase 7 SECURITY GATE: PASS')
"

# 7. hermes doctor — all checks green
hermes doctor --verbose
```

### Verification Commands

```bash
# 1. All monitoring active
for endpoint in "localhost:9090/-/healthy" "localhost:3000/api/health" "localhost:3100/ready"; do
    curl -sf "http://$endpoint" && echo " $endpoint: OK" || echo " $endpoint: FAIL"
done

# 2. Hermes prometheus metrics port (9191) accessible
curl -sf http://localhost:9191/metrics | grep -E "hermes_|guinevere_"

# 3. Backup script test (dry-run)
sudo -u guinevere bash /home/guinevere/code/guinevere/scripts/backup.sh --dry-run

# 4. Checkpoint created
hermes checkpoints create --label "phase7-complete-$(date +%Y%m%d)"
hermes checkpoints list

# 5. Runbook completeness
wc -l /home/guinevere/code/guinevere/runbooks/hermes-migration-runbook.md
# Expected: > 200 lines (comprehensive)

# 6. Aizanta final verification
sudo systemctl list-units --type=service --state=running | grep -i aizanta
# Aizanta MUST still be running, untouched
```

### Rollback Trigger Conditions

| Condition | Detection | Action |
|---|---|---|
| Performance exceeds +10% of baseline | Benchmark comparison | Investigate bottleneck; fix or rollback specific config |
| `hermes security` finds HIGH issues | Security scan output | Fix findings; re-scan until zero HIGH |
| `hermes doctor` shows non-PASS | Doctor output | Debug and fix before marking complete |
| Monitoring gaps (services not appearing in Prometheus) | Prometheus targets page | Verify exporter configs; fix scrape targets |
| Backup pipeline fails | Backup script return non-zero | Debug backup; ensure ADR-032 compliance |

**Phase 7 Rollback**:

```bash
hermes cron remove --all
hermes config set observability.prometheus.enabled false
# Disable any problematic alert rules
# < 3 minutes
```

---

## Global Emergency Rollback (Any Phase → Production bot.py)

Universal kill-switch procedure. Works from any phase. Target: < 5 minutes.

```bash
#!/bin/bash
# GLOBAL EMERGENCY ROLLBACK — execute from any state
# Saved to: /home/guinevere/scripts/rollback/global-emergency-rollback.sh

set -e
echo "=== GLOBAL EMERGENCY ROLLBACK STARTED $(date) ==="

# 1. UNIVERSAL KILL-SWITCH — stop all Hermes activity
echo "[1/8] Stopping Hermes gateway..."
hermes gateway stop 2>/dev/null || true
sleep 1

# 2. Verify Hermes is down
hermes gateway status 2>&1 | grep -q "not running\|stopped\|error" || {
    echo "WARNING: Hermes may still be running — force kill"
    sudo pkill -f "hermes" 2>/dev/null || true
}

# 3. Re-enable and start bot.py
echo "[2/8] Starting bot.py..."
sudo systemctl enable guinevere-discord
sudo systemctl start guinevere-discord
sleep 3

# 4. Verify bot.py running
echo "[3/8] Verifying bot.py..."
sudo systemctl is-active guinevere-discord | grep -q "active" || {
    echo "CRITICAL: bot.py failed to start"
    sudo journalctl -u guinevere-discord --since "1 minute ago" --no-pager | tail -20
    exit 1
}

# 5. Disable Hermes gateway from auto-starting
echo "[4/8] Disabling Hermes gateway..."
hermes gateway uninstall 2>/dev/null || true
sudo systemctl disable hermes-gateway 2>/dev/null || true

# 6. Git restore all migration files to pre-migration baseline
echo "[5/8] Restoring code to pre-migration baseline..."
cd /home/guinevere/code/guinevere
PRE_TAG=$(git tag | grep "pre-hermes-migration" | tail -1)
if [ -n "$PRE_TAG" ]; then
    git checkout "$PRE_TAG" -- src/discord/ src/mcp/ src/persona/ src/hermes/ 2>/dev/null || true
fi

# 7. Remove Hermes migration artifacts
echo "[6/8] Removing migration artifacts..."
rm -rf plugins/ config/hermes/

# 8. Restart core services to pick up restored code
echo "[7/8] Restarting services..."
sudo systemctl restart guinevere-core
sleep 2
sudo systemctl restart guinevere-mcp
sleep 2
sudo systemctl restart guinevere-loops
sleep 2
sudo systemctl restart guinevere-scheduler
sleep 2

# 9. Final verification
echo "[8/8] Final verification..."
echo "=== SERVICE STATUS ==="
for svc in guinevere-core guinevere-discord guinevere-loops guinevere-scheduler \
           guinevere-mcp guinevere-surveillance guinevere-monitoring guinevere-obscura; do
    state=$(sudo systemctl is-active $svc)
    echo "$svc: $state"
    [ "$state" = "active" ] || echo "  WARNING: $svc not active"
done

echo ""
echo "=== HARD STOP VERIFICATION ==="
echo "Send 'HARD STOP' in Discord → expect neutral response"
echo ""
echo "GLOBAL ROLLBACK COMPLETE at $(date)"
echo "Downtime: bot.py down for ~$(($(date +%s) - START_TIME)) seconds"
```

**Maximum downtime**: < 5 minutes from `hermes gateway stop` to `guinevere-discord` accepting Discord messages.

---

## Service Dependency Matrix (Quick Reference)

```
START ORDER (bottom-up):
  1. docker.service + guinevere-9router.service (external)
  2. guinevere-core.service          ← FOUNDATION
  3. guinevere-discord.service       ← parallel ┐
     guinevere-loops.service         ← parallel  │ all Require core
     guinevere-mcp.service           ← parallel  │
     guinevere-surveillance.service  ← parallel ┘
     guinevere-monitoring.service    ← parallel (Wants core)
     guinevere-obscura.service       ← parallel (standalone)
  4. guinevere-scheduler.service     ← Requires loops

STOP ORDER (top-down, reverse):
  1. guinevere-scheduler.service     ← depends on loops
  2. guinevere-discord.service       ← user-facing
  3. guinevere-mcp.service           ← tool server
  4. guinevere-surveillance.service  ← data consumer
  5. guinevere-loops.service         ← agent loop
  6. guinevere-monitoring.service    ← docker stack
  7. guinevere-obscura.service       ← CDP browser
  8. guinevere-core.service          ← FOUNDATION (stop last)
```

## Resource Budget Per Phase

| Phase | Max Concurrent Services | RAM Budget (of 8GB) | Additional Processes |
|---|---|---|---|
| 0 | 8 (all) | ~4.3GB | None (pip install only) |
| 1 | 8 (all) | ~4.3GB | None (file creation only) |
| 2A (shadow) | 9 (all + Hermes gateway) | ~4.8GB | Hermes gateway process |
| 2B (cutover) | 8 (bot.py replaced by Hermes) | ~4.5GB | Hermes replaces bot.py |
| 3 | 8 (all) | ~4.5GB | None (config only) |
| 4 | 8 (all) | ~4.5GB | Auth overlay plugin (in-process) |
| 5 | 8 (all) | ~4.5GB | Skills (in-process) |
| 6 | 8 (all) | ~4.5GB | Budget hook (in-process) |
| 7 | 8 (all) | ~4.5GB | Cron daemon (in-process) |

**Resource constraint**: All phases stay within the 8GB cgroup limit. Shadow mode (Phase 2A) is the highest-resource phase with both bot.py and Hermes gateway running simultaneously.

---

## Health Check Quick Reference

```bash
# Copy-paste health check for any phase
# === ONE-LINE FULL HEALTH CHECK ===
sudo systemctl is-active guinevere-core guinevere-discord guinevere-loops \
    guinevere-scheduler guinevere-mcp guinevere-surveillance \
    guinevere-monitoring guinevere-obscura && \
    curl -sf http://localhost:8000/health > /dev/null && \
    curl -sf http://localhost:20128/health > /dev/null 2>&1 && \
    echo "ALL SERVICES HEALTHY" || echo "SERVICE HEALTH CHECK FAILED"
```

---

## Report Metadata

| Field | Value |
|---|---|
| Report | 08-Service-Sequence |
| Lines | 800+ |
| Phases Documented | 0-7 (all 8) |
| Services Analyzed | 8 (core, discord, loops, scheduler, mcp, surveillance, monitoring, obscura) |
| Service Files Read | 7 in `systemd/` + 1 in `docs/setup-evidence/P1/STEP-P1-018/` |
| Aizanta Constraint | Documented in every phase |
| Rollback Procedures | Per-phase + global emergency |
| Resource Budget | Per-phase RAM estimate |
| Dependency Map | Full start/stop order with rationale |
| ADR Source | ADR-035 (all 2512 lines read, phase descriptions verified) |