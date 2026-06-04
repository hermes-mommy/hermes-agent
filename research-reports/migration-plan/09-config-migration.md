# Report 09: Config Migration Map Per Phase

**Date:** 2026-06-04
**Version:** 1.0
**Scope:** Every configuration change needed for each phase (0-7) of the Hermes migration
**Sources:** ADR-035 (full, 2512 lines), 02-CONFIG-SYSTEM.md (365 lines), all 7 systemd service files, all monitoring configs, `src/hermes/__init__.py`

---

## 1. Executive Summary

The Hermes migration spans 8 phases (0-7), touching 7 systemd services, 8 Docker monitoring containers, 5 configuration layers (config.yaml, SOUL.md, .env, auth.json, auth_matrix.yaml), SOPS-encrypted secrets, and the 9Router proxy. This report maps every config change by phase -- what is added, modified, or removed.

**Key changes at a glance:**
- **1 new systemd service**: `hermes-gateway.service` (replaces `guinevere-discord.service`)
- **5 service files modified**: monitoring (add Hermes scraper), MCP (restart after tool migration), loops, scheduler, surveillance (environment files updated)
- **1 service file removed**: `guinevere-discord.service` (Phase 2 cutover)
- **8 new config files**: config.yaml (rewritten), auth_matrix.yaml, hooks.yaml, mcp-servers.yaml, SOUL.md, system-prompt.md, MEMORY.md, USER.md
- **~15 new hook/plugin files**: hard_stop.py, consent_gate.py, drift_detector.py, output_sanitizer.py, etc.
- **Prometheus**: new scrape job for Hermes metrics at `localhost:9191`
- **Secrets**: 4 new SOPS-encrypted items migrated from `.env` plaintext

---

## 2. Current Configuration Baseline

### 2.1 systemd Services (Pre-Migration)

| Service | EnvironmentFile | ExecStart | Resource |
|---|---|---|---|
| `guinevere-discord.service` | `.env.discord` | `python -m src.discord.bot` | 512M/1G |
| `guinevere-mcp.service` | `.env.mcp` | `python -m src.mcp.manager` | 1G/2G |
| `guinevere-loops.service` | `.env.loops` | `python -m src.loops.manager` | 1G/2G |
| `guinevere-scheduler.service` | `.env.scheduler` | `python -m src.loops.scheduler` | 1G/2G |
| `guinevere-surveillance.service` | `.env.surveillance` | `python -m src.surveillance.consumer` | 512M/768M |
| `guinevere-monitoring.service` | None (Docker) | `docker compose up` | 900M/1G |
| `guinevere-obscura.service` | None | `obscura serve --port 9222` | 256M/512M |

### 2.2 Hardcoded Configurations (Pre-Migration)

| Config Item | Location | Current Value |
|---|---|---|
| LLM base_url | `src/hermes/__init__.py` line 34 | `http://localhost:20128/v1` |
| LLM model | `src/hermes/__init__.py` line 35 | `ds/deepseek-v4-flash` |
| LLM provider | `src/hermes/__init__.py` line 36 | `9router` |
| LLM api_key | `src/hermes/__init__.py` line 37 | `sk-local` |
| Discord token | `.env.discord` (SOPS) | `${DISCORD_BOT_TOKEN}` |
| Redis session | `session_adapter.py` | `localhost:6379 DB4` |
| PostgreSQL | `memory_bridge.py` | `localhost:5433 guinevere` |
| 9Router | static | `localhost:20128` |

### 2.3 Monitoring Stack (Pre-Migration)

| Component | Port | Scraped By |
|---|---|---|
| Prometheus | 127.0.0.1:9090 | Self |
| Node Exporter | 127.0.0.1:9100 | Prometheus |
| PostgreSQL Exporter | 127.0.0.1:9187 | Prometheus |
| Redis Exporter | 127.0.0.1:9121 | Prometheus |
| Guinevere FastAPI | host:8000 | Prometheus (job: fastapi) |
| Loki | 127.0.0.1:3100 | Prometheus |
| Alertmanager | 127.0.0.1:9093 | Prometheus |
| Grafana | 127.0.0.1:3000 | Not scraped |

---

## 3. Phase 0: Security Remediation (1-2 days)

### 3.1 Hermes config.yaml Changes

No structural YAML changes. Only pip-level dependency fixes.

```yaml
# No changes to config/hermes/config.yaml
# Phase 0 is purely pip-level security: aiohttp upgrade, --require-hashes, version pins
```

### 3.2 SOPS Secrets Needed

| Secret | Source | Phase Used |
|---|---|---|
| (None new -- Phase 0 works with existing SOPS secrets) | -- | -- |

### 3.3 Environment Variables

| Variable | Value | Service | Phase |
|---|---|---|---|
| (None new -- version pinning is at pip level, not env) | -- | -- | 0 |

### 3.4 Systemd Unit Changes

No systemd changes in Phase 0. Package-level remediation only.

### 3.5 pip-level Changes

```bash
# Phase 0: Pin Hermes with hashes
pip install hermes-agent==0.15.2 --require-hashes -r requirements-hashes.txt

# Upgrade vulnerable packages
pip install aiohttp>=3.9.0 --require-hashes

# Freeze for rollback
pip freeze > /home/guinevere/backups/pre-migration-pip-$(date +%Y%m%d).txt
```

### 3.6 Discord Token Handling

No changes in Phase 0. Token remains in `.env.discord` under SOPS encryption.

### 3.7 9Router Config Changes

No changes. `localhost:20128` unchanged.

### 3.8 Gate Criteria

- `hermes doctor --verbose` all PASS
- `hermes security --format json` zero HIGH/MODERATE

---

## 4. Phase 1: Safety Foundation (4-6 days)

### 4.1 Hermes config.yaml Changes

**Path:** `/home/guinevere/config/hermes/config.yaml`

```yaml
# === PHASE 1 ADDITIONS ===

# Agent Identity (overwrite empty/personality:kawaii)
agent:
  name: "Guinevere de Baroque"
  personality: "custom"          # Changed from "kawaii" -- use SOUL.md instead
  soul_file: "/home/guinevere/code/guinevere/config/hermes/SOUL.md"
  language: "id,en"
  max_turns: 100                 # Replace Redis DB4 20-turn hard truncation
  idle_timeout: 7200             # 2 hours -- matches Redis session TTL
  system_prompt_file: "/home/guinevere/code/guinevere/config/hermes/system-prompt.md"

# Hooks System (6 of 7 lifecycle hooks + 1 on_error)
hooks:
  pre_prompt:
    command: "python /home/guinevere/code/guinevere/hooks/hard_stop.py"
    timeout_ms: 50
    on_failure: block
    stdin: json
    priority: 100
    security:
      read_only_filesystem: true
      max_memory_mb: 64
      allowed_syscalls: ["read", "write", "exit"]
  post_prompt:
    command: "python /home/guinevere/code/guinevere/hooks/drift_detector.py"
    timeout_ms: 200
    on_failure: block
    stdin: json
    priority: 80
    security:
      read_only_filesystem: true
      max_memory_mb: 128
  pre_tool_call:
    command: "python /home/guinevere/code/guinevere/hooks/consent_gate.py"
    timeout_ms: 300
    on_failure: block
    stdin: json
    priority: 90
    security:
      read_only_filesystem: true
      max_memory_mb: 128
      allowed_network: ["localhost:6380", "localhost:5433"]
  post_tool_call:
    command: "python /home/guinevere/code/guinevere/hooks/output_sanitizer.py"
    timeout_ms: 500
    on_failure: block
    stdin: json
    priority: 70
    security:
      read_only_filesystem: true
      max_memory_mb: 64
  pre_response:
    command: "python /home/guinevere/code/guinevere/hooks/final_safety.py"
    timeout_ms: 100
    on_failure: block
    stdin: json
    priority: 60
  post_response:
    command: "python /home/guinevere/code/guinevere/hooks/response_scanner.py"
    timeout_ms: 200
    on_failure: block
    stdin: json
    priority: 50
    security:
      read_only_filesystem: true
      max_memory_mb: 128
  on_error:
    command: "python /home/guinevere/code/guinevere/hooks/error_handler.py"
    timeout_ms: 2000
    on_failure: warn
    stdin: json
    priority: 10

# Plugin System (GuinevereSafetyPlugin -- CRITICAL)
plugins:
  guinevere_safety:
    enabled: true
    path: "/home/guinevere/code/guinevere/guinevere/plugins/guinevere_safety_plugin.py"
    class: "GuinevereSafetyPlugin"
    priority: 100
    critical: true               # Hermes refuses to start without this plugin
    config:
      redis_url: "redis://localhost:6380/5"        # DB5 = safety state
      postgres_dsn: "postgresql://guinevere_app@localhost:5433/guinevere"
      soul_md_path: "/home/guinevere/code/guinevere/config/hermes/SOUL.md"
      hard_stop_triggers:
        - "hard stop"
        - "hardstop"
        - "safe word"
        - "safeword"
        - "hentikan"
        - "berhenti"
        - "stop persona"
        - "mode netral"
```

### 4.2 New Files Created

| File | Purpose | Lines (est.) |
|---|---|---|
| `config/hermes/SOUL.md` | Guinevere identity constitution (from ADR-035 Appendix C template) | ~130 |
| `config/hermes/system-prompt.md` | Base system prompt (from SystemPromptMaster v1.1) | ~200 |
| `hooks/hard_stop.py` | HARD STOP detection (dual-layer with plugin) | ~80 |
| `hooks/drift_detector.py` | SHA-256 persona drift detection | ~60 |
| `hooks/consent_gate.py` | 7-step fail-closed consent verification | ~100 |
| `hooks/output_sanitizer.py` | Post-tool output sanitization + DNR filter | ~80 |
| `hooks/final_safety.py` | Pre-response final safety check | ~50 |
| `hooks/response_scanner.py` | Post-response secret scanner + forbidden patterns (F-01..F-15) | ~120 |
| `hooks/error_handler.py` | Error classification + severity-based alerting | ~60 |
| `guinevere/plugins/guinevere_safety_plugin.py` | Stateful safety enforcement (all 15+ features) | ~1000 |
| `guinevere/plugins/memory_plugin.py` | PostgreSQL bridge + DNR + classification | ~180 |

### 4.3 SOPS Secrets Needed

| Secret | Source | Phase Used |
|---|---|---|
| `${DISCORD_BOT_TOKEN}` | SOPS-encrypted `.env.discord` | 1 (SOUL.md/system-prompt generation) |
| `${NINEROUTER_API_KEY}` | SOPS-encrypted `.env.ninerouter` | 1 (config.yaml llm section) |
| PostgreSQL password (guinevere_app) | SOPS | 1 (plugin postgres_dsn) |
| Redis password (if ACL applied) | SOPS | 1 (plugin redis_url) |

### 4.4 Environment Variables

| Variable | Value | Service | Phase |
|---|---|---|---|
| `DISCORD_BOT_TOKEN` | SOPS-decrypted | (not yet service-active -- Phase 2) | 1 |
| `NINEROUTER_API_KEY` | SOPS-decrypted | (config.yaml only) | 1 |

### 4.5 Systemd Unit Changes

No runtime systemd changes in Phase 1. All changes are code/config files tested offline. The existing 7 services continue running bot.py.

### 4.6 Discord Token Handling

- Token remains in `.env.discord` under SOPS encryption for now
- Phase 1 does not start the Hermes gateway -- token is only referenced in config.yaml template
- SOPS decrypt procedure (unchanged):
  ```bash
  export SOPS_AGE_KEY_FILE=/home/guinevere/.config/sops/age/keys.txt
  sops exec-env /home/guinevere/code/guinevere/.env.discord "python hooks/consent_gate.py"
  ```

### 4.7 9Router Config Changes

No changes. 9Router at `localhost:20128` is referenced in config.yaml but Hermes gateway is not running yet.

### 4.8 Gate Criteria

- ALL 10 safety gates PASS (integration tests)
- `hermes doctor` clean

---

## 5. Phase 2: Discord Gateway (4-6 days)

### 5.1 Hermes config.yaml Changes

```yaml
# === PHASE 2 ADDITIONS ===

# Discord Gateway (full section)
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
      primary: "guinevere-chat"        # Main channel (post-cutover)
      shadow: "hermes-shadow"          # Shadow mode channel
      alerts: "guinevere-alerts"
      surveillance: "guinevere-surveillance"
    commands:
      register_on_startup: true
      guild_scoped: true
      ephemeral_by_default: false
    streaming:
      enabled: true
      progressive_edit_interval_ms: 1200
      max_edits_per_5s: 5
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
        admin: []
        user: []

# Shadow Mode (temporary -- removed after cutover)
# During shadow mode:
#   memory.compression.enabled = false
#   memory.mirrors.enabled = false
#   memory.external.enabled = false
# Only bot.py writes to PostgreSQL (write mutex)
```

### 4.2 Command Plugins Created (35 new files)

**HIGH Feasibility (8 plugins -- simple Discord.py-free port):**

| Plugin File | Command | Phase |
|---|---|---|
| `plugins/status_plugin.py` | `/status` | 2 |
| `plugins/mood_plugin.py` | `/mood` | 2 |
| `plugins/help_plugin.py` | `/help` | 2 |
| `plugins/safeword_plugin.py` | `/safeword` | 2 |
| `plugins/new_session_plugin.py` | `/new` | 2 |
| `plugins/history_plugin.py` | `/history` | 2 |
| `plugins/casual_plugin.py` | `/casual` | 2 |
| `plugins/focus_plugin.py` | `/focus` | 2 |

**MEDIUM Feasibility (15 plugins):**

| Plugin File | Command | Phase |
|---|---|---|
| `plugins/memory_*.py` (x5) | `/memory` family | 2 |
| `plugins/loop_*.py` (x5) | `/loop` family | 2 |
| `plugins/surv_*.py` (x5) | `/surveillance` family | 2 |

**LOW Feasibility (12 plugins -- stateful):**

| Plugin File | Command | Phase |
|---|---|---|
| `plugins/cost_plugin.py` | `/cost` | 2 |
| `plugins/budget_plugin.py` | `/budget` | 2 |
| `plugins/approve_plugin.py` | `/approve` | 2 |
| `plugins/deny_plugin.py` | `/deny` | 2 |
| `plugins/restart_plugin.py` | `/restart` | 2 |
| `plugins/backup_plugin.py` | `/backup` | 2 |
| `plugins/health_plugin.py` | `/health` | 2 |
| `plugins/consent_plugin.py` | `/consent` | 2 |
| `plugins/punishment_plugin.py` | `/punishment` | 2 |
| `plugins/reward_plugin.py` | `/reward` | 2 |
| `plugins/dnr_plugin.py` | `/dnr` | 2 |
| `plugins/ritual_plugin.py` | `/ritual` | 2 |

### 5.3 SOPS Secrets Needed

| Secret | Source | Phase Used | Hermes Equivalent |
|---|---|---|---|
| `DISCORD_BOT_TOKEN` | SOPS `.env.discord` | 2 | `gateway.discord.token` (config.yaml) |
| `DISCORD_APPLICATION_ID` | SOPS `.env.discord` | 2 | `gateway.discord.application_id` |
| `DISCORD_GUILD_ID` | SOPS `.env.discord` | 2 | `gateway.discord.guild_id` |
| `NINEROUTER_API_KEY` | SOPS `.env.ninerouter` | 2 | `model.api_key` (config.yaml) |

### 5.4 Environment Variables

| Variable | Value | Service | Phase |
|---|---|---|---|
| `DISCORD_BOT_TOKEN` | `${SOPS_DECRYPTED}` | `hermes-gateway.service` (NEW) | 2 |
| `DISCORD_APPLICATION_ID` | `${SOPS_DECRYPTED}` | `hermes-gateway.service` (NEW) | 2 |
| `DISCORD_GUILD_ID` | `${SOPS_DECRYPTED}` | `hermes-gateway.service` (NEW) | 2 |
| `NINEROUTER_API_KEY` | `${SOPS_DECRYPTED}` | `hermes-gateway.service` (NEW) | 2 |
| `HERMES_CONFIG_PATH` | `/home/guinevere/config/hermes/config.yaml` | `hermes-gateway.service` | 2 |

### 5.5 Systemd Unit Changes

#### NEW: `hermes-gateway.service`

```ini
# /etc/systemd/system/hermes-gateway.service
# Phase 2 -- Created during shadow mode, activated at cutover

[Unit]
Description=Hermes Agent Discord Gateway (Guinevere)
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=exec
User=guinevere
WorkingDirectory=/home/guinevere/code/guinevere
Environment=PYTHONPATH=/home/guinevere/code/guinevere
Environment=PYTHONDONTWRITEBYTECODE=1
Environment=VIRTUAL_ENV=/home/guinevere/code/guinevere/.venv
Environment=HERMES_CONFIG_PATH=/home/guinevere/config/hermes/config.yaml
EnvironmentFile=/home/guinevere/code/guinevere/.env.hermes    # NEW -- SOPS-managed
ExecStart=/home/guinevere/code/guinevere/.venv/bin/hermes gateway start
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Slice=guinevere.slice

# Resource limits -- matches guinevere-discord.service
MemoryHigh=512M
MemoryMax=1G
CPUQuota=100%

# Security hardening -- matches existing pattern
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/home/guinevere/code/guinevere /home/guinevere/data /home/guinevere/logs /home/guinevere/evidence /home/guinevere/.hermes /home/guinevere/config

# Health check integration
# Hermes exposes metrics on port 9191 for Prometheus scraping
# Hermes gateway status is checked via `hermes gateway status`

[Install]
WantedBy=multi-user.target
```

#### MODIFIED: `guinevere-discord.service` -- DISABLED (post-cutover)

```ini
# Phase 2 Cutover: Stop and disable guinevere-discord.service
# sudo systemctl stop guinevere-discord.service
# sudo systemctl disable guinevere-discord.service

# Kept on disk for rollback -- restart via:
# sudo systemctl start guinevere-discord.service
```

#### NEW: `.env.hermes` (SOPS-encrypted)

```bash
# /home/guinevere/code/guinevere/.env.hermes
# Phase 2 -- Secrets for Hermes gateway
# Encrypted via: sops --encrypt --age $(cat /home/guinevere/.config/sops/age/keys.txt | grep 'public key' | head -1 | awk '{print $4}') .env.hermes

DISCORD_BOT_TOKEN=${DECRYPTED_DISCORD_BOT_TOKEN}
DISCORD_APPLICATION_ID=${DECRYPTED_DISCORD_APPLICATION_ID}
DISCORD_GUILD_ID=${DECRYPTED_DISCORD_GUILD_ID}
NINEROUTER_API_KEY=${DECRYPTED_NINEROUTER_API_KEY}
```

### 5.6 SOPS Decrypt Procedure (Hermes)

```bash
# Decrypt .env.hermes before starting Hermes gateway
# Option A: Use sops exec-env (one-shot)
sops exec-env /home/guinevere/code/guinevere/.env.hermes \
  /home/guinevere/code/guinevere/.venv/bin/hermes gateway start

# Option B: Decrypt to temp file (startup script)
sops --decrypt /home/guinevere/code/guinevere/.env.hermes > /tmp/hermes-env-decrypted
source /tmp/hermes-env-decrypted
/home/guinevere/code/guinevere/.venv/bin/hermes gateway start
shred -u /tmp/hermes-env-decrypted
```

### 5.7 Discord Token Handling

**Current (bot.py):**
```
.env.discord → SOPS decrypt → os.environ['DISCORD_BOT_TOKEN'] → discord.Client.run(token)
```

**Phase 2 Shadow Mode (Hermes):**
```
.env.hermes → SOPS decrypt → hermes config.yaml ${DISCORD_BOT_TOKEN} variable expansion
# Hermes reads token from config.yaml, NOT from environment directly
# The ${DISCORD_BOT_TOKEN} substitution happens at Hermes startup
```

**Phase 2 Cutover:**
```
hermes gateway start  → reads config.yaml  → connects to Discord
bot.py STOPPED         → no Discord connection from old system
```

**Token Rotation Plan:**
1. Generate new token in Discord Developer Portal
2. Update `.env.hermes` plaintext value
3. Re-encrypt with SOPS: `sops --encrypt .env.hermes`
4. Restart Hermes: `sudo systemctl restart hermes-gateway`
5. Revoke old token

### 5.8 9Router Config Changes

No changes. Hermes connects to `localhost:20128/v1` via config.yaml. 9Router proxy config unchanged.

### 5.9 Gate Criteria

- All 35 slash commands functional
- 48hr+ shadow mode parity confirmed by Faiz
- HARD STOP, Y6, consent, distress injections all pass during shadow mode
- `hermes gateway status` shows connected

---

## 6. Phase 3: Memory Bridge (3-4 days)

### 6.1 Hermes config.yaml Changes

```yaml
# === PHASE 3 ADDITIONS ===

# Memory Configuration
memory:
  compression:
    enabled: true
    threshold: 0.70         # Start at 70% (aggressive safe), tune down to 50% later
    target: 0.20
    protect_last: 20
  session_search:
    enabled: true
    backend: "fts5"          # Hermes SQLite FTS5 for cross-session agent browsing
  external:
    enabled: false           # All canonical memory is PostgreSQL -- no external providers
  mirrors:
    enabled: true
    memory_md_path: "/home/guinevere/code/guinevere/config/hermes/MEMORY.md"
    user_md_path: "/home/guinevere/code/guinevere/config/hermes/USER.md"
    sync_interval_messages: 5

# Memory Bridge Plugin (from Phase 1, now activated)
plugins:
  memory_bridge:             # Renamed from memory_plugin at creation
    enabled: true
    path: "/home/guinevere/code/guinevere/guinevere/plugins/memory_plugin.py"
    class: "MemoryBridgePlugin"
    priority: 80
    critical: false          # Non-critical -- system degrades without it
    config:
      postgres_dsn: "postgresql://guinevere_app@localhost:5433/guinevere"
      redis_url: "redis://localhost:6380/3"    # DB3 = Sessions (per ADR-030)
      dnr_enabled: true
      classification_fail_closed: true
```

### 6.2 New Files

| File | Purpose |
|---|---|
| `config/hermes/MEMORY.md` | Mirror of critical PostgreSQL facts (auto-synced every 5 messages) |
| `config/hermes/USER.md` | Mirror of Faiz profile facts (auto-synced every 5 messages) |

### 6.3 SOPS Secrets Needed

| Secret | Source | Phase Used |
|---|---|---|
| (None new -- PostgreSQL/Redis credentials already in Phase 1 plugin config) | -- | -- |

### 6.4 Environment Variables

| Variable | Value | Service | Phase |
|---|---|---|---|
| (None new) | -- | -- | 3 |

### 6.5 Systemd Unit Changes

No systemd changes. Memory bridge operates within the running Hermes gateway.

### 6.6 PostgreSQL/RBAC Changes

```sql
-- Phase 3: Ensure Hermes has read-only access to guinevere database
-- (per ADR-007: PostgreSQL primary write authority unchanged)

-- Hermes memory bridge user
CREATE ROLE hermes_memory_bridge WITH LOGIN PASSWORD '${SOPS_DECRYPTED}';
GRANT CONNECT ON DATABASE guinevere TO hermes_memory_bridge;
GRANT USAGE ON SCHEMA public, memory, persona, consent TO hermes_memory_bridge;
GRANT SELECT ON ALL TABLES IN SCHEMA memory TO hermes_memory_bridge;
GRANT SELECT ON ALL TABLES IN SCHEMA persona TO hermes_memory_bridge;
GRANT SELECT ON consent_ledger TO hermes_memory_bridge;

-- Write mutex: ONLY bot.py (or hermes_app in post-cutover) writes
-- Hermes memory bridge is READ-ONLY on PostgreSQL
ALTER DEFAULT PRIVILEGES IN SCHEMA memory GRANT SELECT ON TABLES TO hermes_memory_bridge;
```

### 6.7 9Router Config Changes

No changes.

### 6.8 Gate Criteria

- Memory recall quality unchanged (A/B test on 100 queries, p > 0.05)
- DNR + classification enforced
- Zero PostgreSQL data modifications from Hermes path
- `SELECT count(*) FROM audit.hermes_writes` = 0

---

## 7. Phase 4: MCP + Tools (3-4 days)

### 7.1 Hermes config.yaml Changes

```yaml
# === PHASE 4 ADDITIONS ===

# Plugin: Auth Overlay (CRITICAL -- Hermes refuses to start without it)
plugins:
  auth_overlay:
    enabled: true
    path: "/home/guinevere/code/guinevere/guinevere/plugins/auth_overlay.py"
    class: "AuthOverlayPlugin"
    priority: 90               # Loaded AFTER guinevere_safety (100) but BEFORE memory (80)
    critical: true             # Hermes refuses to start without this plugin
    config:
      auth_matrix_path: "/home/guinevere/code/guinevere/config/hermes/auth_matrix.yaml"
      webhook_url: "${DISCORD_APPROVAL_WEBHOOK}"
      approval_timeout_ms: 300000  # 5 minutes
      on_timeout: "deny"           # FAIL-CLOSED

# MCP Servers
mcp_servers:
  web:
    enabled: true
    tools: ["brave_search", "exa_search", "fetch_url", "websearch"]
  filesystem:
    enabled: true
    root_path: "/home/guinevere/code/guinevere"
    allowed_paths:
      - "/home/guinevere/code/guinevere"
      - "/tmp/guinevere"
    blocked_paths:
      - "/etc"
      - "/root"
      - "/home/guinevere/.ssh"
  terminal:
    enabled: true
    allowed_commands:
      - "ls,cat,head,tail,grep,find,wc,sort,uniq"
      - "python,pip,pytest"
      - "git,gh"
    blocked_commands:
      - "rm,dd,mkfs,shutdown,reboot,poweroff"
      - "iptables,ufw,systemctl"
    timeout_seconds: 30
  git:
    enabled: true
    allowed_operations: ["status","diff","log","branch","checkout","add","commit","push","pull"]
    blocked_operations: ["push --force","reset --hard","clean -fd"]
  fetch:
    enabled: true
    timeout_seconds: 30
    max_response_size_mb: 10
```

### 7.2 New Files

| File | Purpose | Lines (est.) |
|---|---|---|
| `config/hermes/auth_matrix.yaml` | 4-level auth matrix (from ADR-035 Appendix B) | ~120 |
| `guinevere/plugins/auth_overlay.py` | Auth matrix enforcement plugin | ~150 |
| `config/hermes/mcp-servers.yaml` | Hermes native MCP server configs | ~80 |

### 7.3 Auth Matrix Config (config/hermes/auth_matrix.yaml)

```yaml
# config/hermes/auth_matrix.yaml
# 4-Level Auth Matrix -- see ADR-035 Appendix B for full content
# READ_AUTO / WRITE_NOTIFY / DESTRUCTIVE_APPROVAL / FORBIDDEN

auth_matrix:
  web: { brave_search: READ_AUTO, exa_search: READ_AUTO, websearch: READ_AUTO, fetch: READ_AUTO }
  filesystem: { read: READ_AUTO, write: WRITE_NOTIFY, delete: DESTRUCTIVE_APPROVAL, create_directory: WRITE_NOTIFY }
  terminal: { read_commands: READ_AUTO, write_commands: WRITE_NOTIFY, destructive_commands: DESTRUCTIVE_APPROVAL, forbidden_commands: FORBIDDEN }
  git: { read: READ_AUTO, write: WRITE_NOTIFY, destructive: DESTRUCTIVE_APPROVAL }
  fetch: { get: READ_AUTO, post: WRITE_NOTIFY, upload: DESTRUCTIVE_APPROVAL }
  postgres_tool: { select: READ_AUTO, insert: WRITE_NOTIFY, update: WRITE_NOTIFY, delete: DESTRUCTIVE_APPROVAL, ddl: DESTRUCTIVE_APPROVAL, drop: FORBIDDEN, pg_dump: WRITE_NOTIFY }
  redis_tool: { get: READ_AUTO, set: WRITE_NOTIFY, delete: WRITE_NOTIFY, flush: DESTRUCTIVE_APPROVAL, config: FORBIDDEN }
  obscura_cdp: { navigate: READ_AUTO, screenshot: READ_AUTO, fill_form: WRITE_NOTIFY, click: WRITE_NOTIFY, execute_js: DESTRUCTIVE_APPROVAL, file_upload: DESTRUCTIVE_APPROVAL }
  grep_app: { search: READ_AUTO, search_github: READ_AUTO }
  context7: { query: READ_AUTO, resolve: READ_AUTO }
  sequential_thinking: { think: READ_AUTO }
  time_tools: { get_time: READ_AUTO, convert: READ_AUTO, calculate: READ_AUTO }

approval:
  discord_webhook_url: "${DISCORD_APPROVAL_WEBHOOK}"
  timeout_ms: 300000
  retry_count: 2
  retry_delay_ms: 30000
  fallback_on_timeout: "deny"

audit:
  log_all_destructive: true
  log_all_forbidden_attempts: true
  log_write_notify: false
  retention_days: 90
  alert_on_forbidden_attempt: true
```

### 7.4 SOPS Secrets Needed

| Secret | Source | Phase Used |
|---|---|---|
| `DISCORD_APPROVAL_WEBHOOK` | SOPS `.env.hermes` | 4 (auth overlay Discord approval webhook) |

### 7.5 Environment Variables

| Variable | Value | Service | Phase |
|---|---|---|---|
| `DISCORD_APPROVAL_WEBHOOK` | `${SOPS_DECRYPTED}` | `hermes-gateway.service` | 4 |

### 7.6 Systemd Unit Changes

#### MODIFIED: `guinevere-mcp.service`

```ini
# Phase 4: MCP manager now runs alongside Hermes native MCP servers
# Custom MCP tools (postgres, redis, obscura_cdp, grep_app, context7, sequential_thinking, time_tools)
# remain in FastMCP. Hermes native tools (web, filesystem, terminal, git, fetch) are Hermes-managed.

# ExecStart unchanged -- still runs as before
# But 5 of 16 tools are now handled by Hermes natively
# The FastMCP server continues hosting 7 custom tools + 4 hybrid tools

# Restart after auth overlay plugin deployment
ExecStartPost=sleep 2 && /home/guinevere/code/guinevere/.venv/bin/hermes mcp list
```

### 7.7 9Router Config Changes

No changes.

### 7.8 Gate Criteria

- All 16 tool capabilities available (5 native + 7 custom + 4 hybrid)
- Auth matrix enforced on all 16 tools
- Security audit clean
- `hermes gateway start` fails if auth_overlay plugin missing (load-gate test)

---

## 8. Phase 5: Skills + Persona (2-3 days)

### 8.1 Hermes config.yaml Changes

```yaml
# === PHASE 5 ADDITIONS ===

# Skills section (new top-level key)
skills:
  enabled: true
  marketplace: "agentskills.io"
  curator:
    enabled: true
    auto_approve: false     # Manual approval for all skills
  directory: "/home/guinevere/code/guinevere/skills/"

# Persona plugin activation (already in Phase 1, this phase customizes)
plugins:
  guinevere_safety:
    # (unchanged from Phase 1)
    # Phase 5 adds cron-based ritual triggering
  persona:
    enabled: true
    path: "/home/guinevere/code/guinevere/guinevere/plugins/persona_plugin.py"
    class: "PersonaPlugin"
    priority: 70
    critical: false
    config:
      mood_persistence: true
      mood_decay: 0.01     # Per hour of inactivity
      streak_grace_period_days: 1
      ritual_count: 5      # 5 daily rituals
      ritual_schedule:
        morning: "08:00"
        midday: "12:00"
        afternoon: "16:00"
        evening: "20:00"
        midnight: "00:00"

# Cron Jobs (ritual + maintenance)
cron:
  - name: "ritual_morning"
    schedule: "0 8 * * *"
    command: "hermes plugin trigger guinevere_safety ritual morning"
  - name: "ritual_midday"
    schedule: "0 12 * * *"
    command: "hermes plugin trigger guinevere_safety ritual midday"
  - name: "ritual_afternoon"
    schedule: "0 16 * * *"
    command: "hermes plugin trigger guinevere_safety ritual afternoon"
  - name: "ritual_evening"
    schedule: "0 20 * * *"
    command: "hermes plugin trigger guinevere_safety ritual evening"
  - name: "ritual_midnight"
    schedule: "0 0 * * *"
    command: "hermes plugin trigger guinevere_safety ritual midnight"
```

### 8.2 SOUL.md Finalization

SOUL.md already created in Phase 1. Phase 5 finalizes with:
- Address rules (Sayang, Darling, Good boy, etc.)
- Communication instructions (75% ID, 25% EN, Discord formatting)
- Prompt injection defense (trust hierarchy)
- `chmod 444` permissions hardening

### 8.3 SOPS Secrets Needed

| Secret | Source | Phase Used |
|---|---|---|
| (None new) | -- | -- |

### 8.4 Environment Variables

| Variable | Value | Service | Phase |
|---|---|---|---|
| (None new) | -- | -- | 5 |

### 8.5 Systemd Unit Changes

No systemd changes. Cron-based rituals run within Hermes gateway process.

### 8.6 9Router Config Changes

No changes.

### 8.7 Gate Criteria

- All persona features functional
- Mood persists across sessions
- 5 daily rituals fire on schedule
- `hermes skills list` shows installed skills

---

## 9. Phase 6: LLM Routing (1 day)

### 9.1 Hermes config.yaml Changes

```yaml
# === PHASE 6 ADDITIONS ===

# Overwrite empty LLM section
model:
  provider: "custom"
  model: "gpt-5.5"             # Primary model via 9Router
  base_url: "http://localhost:20128/v1"
  api_key: "${NINEROUTER_API_KEY}"
  max_tokens: 16384
  temperature: 0.7
  streaming: true

# Fallback configuration
fallback:
  enabled: true
  models:
    - "deepseek-v4-flash"      # DeepSeek V4 Flash via 9Router
  strategy: "sequential"

# Budget enforcement
budget:
  monthly_limit: 30.00         # $30/month cap
  alert_threshold: 0.80        # Alert at $24
  block_threshold: 1.00        # Block at $30
  currency: "USD"
```

### 9.2 Budget Enforcement Hook

```python
# hooks/budget.py (NEW)
# Custom pre_tool_call hook that checks cumulative cost
# Alerts at 80% ($24): Discord notification to #guinevere-alerts
# Blocks at 100% ($30): All LLM calls blocked
# Reset: Monthly via hermes insights reset or manual admin command
```

### 9.3 SOPS Secrets Needed

| Secret | Source | Phase Used |
|---|---|---|
| `NINEROUTER_API_KEY` (already in `.env.hermes`) | SOPS | 6 (model config) |

### 9.4 Environment Variables

| Variable | Value | Service | Phase |
|---|---|---|---|
| `NINEROUTER_API_KEY` | `${SOPS_DECRYPTED}` | `hermes-gateway.service` | 6 |

### 9.5 Systemd Unit Changes

No systemd changes.

### 9.6 9Router Config Changes

No changes to 9Router proxy config. Hermes connects to `http://localhost:20128/v1` as a custom provider. Fallback chain (GPT-5.5 → DeepSeek V4 Flash) is managed by Hermes, not 9Router.

**Pre-migration validation:**
```bash
# 100-test-prompt compatibility check
for i in $(seq 1 100); do
  curl -s http://localhost:20128/v1/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${NINEROUTER_API_KEY}" \
    -d '{"model":"gpt-5.5","messages":[{"role":"user","content":"test"}]}' \
    | jq -r '.choices[0].message.content' > /dev/null || echo "FAIL: prompt $i"
done
```

### 9.7 Gate Criteria

- LLM routing functional: GPT-5.5 → DeepSeek fallback works
- Budget enforced at $30/mo
- Streaming compatible with 9Router
- 100/100 test prompts route correctly

---

## 10. Phase 7: Hardening + Monitoring (2-3 days)

### 10.1 Hermes config.yaml Changes

```yaml
# === PHASE 7 ADDITIONS ===

# Observability
observability:
  prometheus:
    enabled: true
    metrics_port: 9191         # Hermes exposes metrics on localhost:9191
  logging:
    level: "info"
    format: "json"             # Structured JSON for Loki ingestion
    output: "both"             # stdout + loki
  insights:
    enabled: true
    cost_tracking: true
    latency_tracking: true

# Cron Jobs (maintenance -- full set)
cron:
  # (ritual jobs from Phase 5 retained)
  - name: "daily_health_check"
    schedule: "0 6 * * *"
    command: "hermes doctor --report"
  - name: "weekly_backup"
    schedule: "0 2 * * 0"
    command: "hermes backup --full --destination idcloudhost"
  - name: "monthly_security_scan"
    schedule: "0 3 1 * *"
    command: "hermes security --report"
  - name: "daily_checkpoint"
    schedule: "0 4 * * *"
    command: "hermes checkpoints create --label auto-daily-$(date +%Y%m%d)"
```

### 10.2 Monitoring Config Changes

#### Prometheus (`monitoring/prometheus/prometheus.yml`) -- ADD new scrape job

```yaml
# === PHASE 7 ADDITION -- new scrape job ===

scrape_configs:
  # ... existing 7 jobs retained ...

  # Job 8: Hermes Agent metrics (NEW)
  - job_name: "hermes"
    metrics_path: "/metrics"
    scrape_interval: 15s
    static_configs:
      - targets: ["host.docker.internal:9191"]
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
        replacement: "hermes-gateway"
```

#### Prometheus Alert Rules -- ADD new rules

```yaml
# monitoring/prometheus/rules/guinevere-hermes-alerts.yml (NEW)

groups:
  - name: guinevere-hermes
    rules:
      # SEV0: Hermes gateway down
      - alert: GuinevereHermesGatewayDown
        expr: up{job="hermes"} == 0
        for: 2m
        labels:
          severity: "critical"
          sev_level: "SEV0"
        annotations:
          summary: "Hermes gateway is down"
          description: "Hermes gateway has been unreachable for 2 minutes. bot.py rollback available."
          runbook: "runbooks/hermes-migration-runbook.md"

      # SEV1: Hermes safety plugin not loaded
      - alert: GuinevereHermesSafetyPluginMissing
        expr: guinevere_hermes_safety_plugin_loaded == 0
        for: 1m
        labels:
          severity: "critical"
          sev_level: "SEV0"
        annotations:
          summary: "GuinevereSafetyPlugin not loaded"
          description: "Critical safety plugin missing -- Hermes may be running without safety enforcement."

      # SEV2: Hermes hook failures rate
      - alert: GuinevereHermesHookFailureRate
        expr: rate(guinevere_hermes_hook_failures_total[15m]) > 0.01
        for: 5m
        labels:
          severity: "warning"
          sev_level: "SEV2"
        annotations:
          summary: "Elevated Hermes hook failure rate"

      # SEV2: Hermes context compression activated frequently
      - alert: GuinevereHermesCompressionFrequent
        expr: rate(guinevere_hermes_compression_total[30m]) > 2
        for: 10m
        labels:
          severity: "warning"
          sev_level: "SEV2"
        annotations:
          summary: "Frequent context compression -- possible memory pressure"

      # SEV3: Hermes LLM cost approaching budget
      - alert: GuinevereHermesBudgetWarning
        expr: guinevere_hermes_cost_monthly_usd > 24
        for: 5m
        labels:
          severity: "info"
          sev_level: "SEV3"
        annotations:
          summary: "Hermes monthly cost approaching $24 (80% of $30 cap)"

      # SEV3: Hermes backup stale
      - alert: GuinevereHermesBackupStale
        expr: time() - guinevere_hermes_last_backup_timestamp > 93600
        for: 5m
        labels:
          severity: "warning"
          sev_level: "SEV2"
        annotations:
          summary: "Hermes backup is stale (>26 hours)"
```

#### Grafana Dashboard -- ADD Hermes dashboard

```json
// monitoring/grafana/dashboards/guinevere-hermes.json (NEW)
// Panels include:
//  - Hermes gateway uptime (up{job="hermes"})
//  - Hook latency (p50/p95/p99 per hook)
//  - Safety events (hard_stop, consent_block, distress_crisis, y6_detected)
//  - LLM cost (cumulative monthly, per-model breakdown)
//  - LLM latency (first token, full response, streaming intervals)
//  - Memory compression rate
//  - Plugin state (loaded, session count, safe_mode active)
//  - Session count (active sessions via Redis DB3)
```

#### Loki / Promtail -- ADD Hermes log labels

```yaml
# monitoring/promtail/promtail-config.yml -- ADD pipeline stage

# In Job 1 (journal), add a relabel_config for hermes-gateway.service:
scrape_configs:
  - job_name: journal
    journal:
      max_age: 12h
      labels:
        job: systemd-journal
        environment: production
    relabel_configs:
      # ... existing relabel_configs ...
      # ADD: Extract Hermes-specific labels
      - source_labels: ["__journal__systemd_unit"]
        regex: "hermes-gateway.service"
        target_label: "service"
        replacement: "hermes"
```

#### Alertmanager -- No changes needed

Existing SEV0-SEV4 routing already handles new Hermes alerts correctly (severity routing by `sev_level` label).

### 10.3 SOPS Secrets Needed

| Secret | Source | Phase Used |
|---|---|---|
| (None new -- existing SOPS infrastructure used) | -- | -- |

### 10.4 Environment Variables

| Variable | Value | Service | Phase |
|---|---|---|---|
| `HERMES_METRICS_PORT` | `9191` | `hermes-gateway.service` | 7 |

### 10.5 Systemd Unit Changes

#### MODIFIED: `hermes-gateway.service`

```ini
# Phase 7 additions to existing hermes-gateway.service:

# Add metrics port environment variable
Environment=HERMES_METRICS_PORT=9191

# Add ExecStartPre for pre-flight checks
ExecStartPre=/home/guinevere/code/guinevere/.venv/bin/hermes doctor --quiet
ExecStartPre=/home/guinevere/code/guinevere/.venv/bin/hermes checkpoints create --label pre-start-$(date +%Y%m%d-%H%M%S)

# Add ExecStopPost for graceful shutdown
ExecStopPost=/home/guinevere/code/guinevere/.venv/bin/hermes checkpoints create --label post-stop-$(date +%Y%m%d-%H%M%S)
```

#### MODIFIED: `guinevere-monitoring.service`

```ini
# Phase 7: Restart monitoring stack to pick up new Hermes scrape config
# ExecReload already defined -- docker compose restart
# No structural changes needed, just ensure Hermes metrics port 9191 is reachable
# from Docker containers via host.docker.internal:9191
```

### 10.6 9Router Config Changes

No changes. 9Router remains at `localhost:20128`.

### 10.7 Gate Criteria

- All monitoring active (Hermes metrics in Grafana)
- `hermes security` clean (zero HIGH/MODERATE)
- `hermes doctor` clean (all PASS)
- Performance within +10% of baseline
- Runbook complete at `runbooks/hermes-migration-runbook.md`

---

## 11. Post-Migration Systemd Service Map

| Service | Status | Notes |
|---|---|---|
| `hermes-gateway.service` | **NEW** (enabled) | Replaces guinevere-discord.service |
| `guinevere-discord.service` | **DISABLED** | Kept on disk for rollback |
| `guinevere-mcp.service` | **ACTIVE** | 7 custom MCP tools still served |
| `guinevere-loops.service` | **ACTIVE** | Agent loop daemon unchanged |
| `guinevere-scheduler.service` | **ACTIVE** | Loop scheduling unchanged |
| `guinevere-surveillance.service` | **ACTIVE** | Surveillance consumer unchanged |
| `guinevere-monitoring.service` | **ACTIVE** | Added Hermes scrape job |
| `guinevere-obscura.service` | **ACTIVE** | Browser automation unchanged |

---

## 12. Complete Environment Variable Map (Post-Migration)

### 12.1 `hermes-gateway.service` -- `.env.hermes` (SOPS-encrypted)

| Variable | SOPS Source | Used In | Phase |
|---|---|---|---|
| `DISCORD_BOT_TOKEN` | `.env.hermes` | `config.yaml` gateway.discord.token | 2 |
| `DISCORD_APPLICATION_ID` | `.env.hermes` | `config.yaml` gateway.discord.application_id | 2 |
| `DISCORD_GUILD_ID` | `.env.hermes` | `config.yaml` gateway.discord.guild_id | 2 |
| `NINEROUTER_API_KEY` | `.env.hermes` | `config.yaml` model.api_key | 6 |
| `DISCORD_APPROVAL_WEBHOOK` | `.env.hermes` | `config.yaml` plugins.auth_overlay.config.webhook_url | 4 |
| `DISCORD_ALERTS_WEBHOOK` | `.env.hermes` | Alertmanager (existing) | 7 |
| `HERMES_CONFIG_PATH` | Hardcoded | `/home/guinevere/config/hermes/config.yaml` | 2 |
| `HERMES_METRICS_PORT` | Hardcoded | `9191` | 7 |

### 12.2 Other Services (unchanged)

| Service | EnvironmentFile | Variables |
|---|---|---|
| `guinevere-mcp.service` | `.env.mcp` | FastMCP config (unchanged) |
| `guinevere-loops.service` | `.env.loops` | Loop daemon config (unchanged) |
| `guinevere-scheduler.service` | `.env.scheduler` | Scheduler config (unchanged) |
| `guinevere-surveillance.service` | `.env.surveillance` | Surveillance consumer config (unchanged) |
| `guinevere-monitoring.service` | `monitoring/.env` | Grafana admin, exporter passwords |
| `guinevere-obscura.service` | None | None (CLI-only) |

---

## 13. SOPS Secrets Inventory (Complete Post-Migration)

| Secret Name | SOPS File | Plaintext Status (Pre-Migration) | Plaintext Status (Post-Migration) |
|---|---|---|---|
| `DISCORD_BOT_TOKEN` | `.env.hermes` | `.env.discord` (SOPS) | `.env.hermes` (SOPS) |
| `DISCORD_APPLICATION_ID` | `.env.hermes` | `.env.discord` (SOPS) | `.env.hermes` (SOPS) |
| `DISCORD_GUILD_ID` | `.env.hermes` | `.env.discord` (SOPS) | `.env.hermes` (SOPS) |
| `DISCORD_APPROVAL_WEBHOOK` | `.env.hermes` | Not applicable | `.env.hermes` (SOPS) |
| `NINEROUTER_API_KEY` | `.env.hermes` | Hardcoded `sk-local` | `.env.hermes` (SOPS) |
| `DISCORD_ALERTS_WEBHOOK` | `.env.hermes` | `monitoring/.env` (PLAINTEXT) | `.env.hermes` (SOPS) |
| `GRAFANA_ADMIN_PASSWORD` | `monitoring/.env` (SOPS) | `monitoring/.env` (PLAINTEXT) | `monitoring/.env` (SOPS) |
| `PG_EXPORTER_PASSWORD` | `monitoring/.env` (SOPS) | `monitoring/.env` (PLAINTEXT) | `monitoring/.env` (SOPS) |
| `REDIS_EXPORTER_PASSWORD` | `monitoring/.env` (SOPS) | `monitoring/.env` (PLAINTEXT) | `monitoring/.env` (SOPS) |
| `SOPS_AGE_KEY` | age keys.txt | `~/.config/sops/age/keys.txt` | Unchanged |
| `SURVEILLANCE_KEY` | `.env.surveillance` | `.env.surveillance` (SOPS) | Unchanged |

**Key improvement**: Pre-migration, `NINEROUTER_API_KEY` is hardcoded as `sk-local` in `src/hermes/__init__.py`. Post-migration, it is a SOPS-encrypted environment variable.

---

## 14. 9Router Config -- Complete Non-Change

Throughout all 8 phases, 9Router configuration is **untouched**:

```
# 9Router proxy (unchanged throughout migration)
Endpoint:    http://localhost:20128/v1
Auth:        ${NINEROUTER_API_KEY}
Primary:     gpt-5.5
Fallback:    deepseek-v4-flash
Combos:      Guinevere combo (DV4 primary via opencode-go, GPT-5.5 secondary via cockpit Tailscale)
```

The only change is that 9Router's API key moves from hardcoded `sk-local` to SOPS-encrypted `${NINEROUTER_API_KEY}`.

---

## 15. Port Map (Post-Migration)

| Port | Service | Visibility | Change |
|---|---|---|---|
| 20128 | 9Router | localhost | None |
| 5433 | PostgreSQL | localhost | None |
| 6380 | Redis | localhost | None |
| 8000 | Guinevere FastAPI | localhost | None |
| 9090 | Prometheus | 127.0.0.1 | None |
| 9093 | Alertmanager | 127.0.0.1 | None |
| 9100 | Node Exporter | 127.0.0.1 | None |
| 9121 | Redis Exporter | 127.0.0.1 | None |
| 9187 | PostgreSQL Exporter | 127.0.0.1 | None |
| 3000 | Grafana | 127.0.0.1 | None |
| 3100 | Loki | 127.0.0.1 | None |
| 9222 | Obscura CDP | localhost | None |
| **9191** | **Hermes metrics** | **127.0.0.1** | **NEW (Phase 7)** |

---

## 16. Rollback Configurations Reference

### 16.1 Universal Kill-Switch

```bash
# Any phase, any time -- stops Hermes, restores bot.py instantly
hermes gateway stop
sudo systemctl start guinevere-discord
sudo systemctl disable hermes-gateway
# Total downtime: < 10 seconds
```

### 16.2 Per-Phase Config Rollback Commands

| Phase | Config Rollback |
|---|---|
| 0 | `pip install -r pre-migration-pip-*.txt` |
| 1 | `rm -f plugins/*.py hooks/*.py` + `rm -f config/hermes/hooks.yaml` |
| 2 | `hermes gateway stop && hermes gateway uninstall` + `sudo systemctl start guinevere-discord` |
| 3 | `hermes config set memory.compression.enabled false` + `hermes config set memory.session_search.enabled false` |
| 4 | `hermes mcp remove web filesystem terminal git fetch` + `rm -f plugins/auth_overlay.py` |
| 5 | `hermes skills uninstall --all` + `git checkout -- config/hermes/SOUL.md` |
| 6 | `hermes model set --model default` + `hermes fallback set --model none` |
| 7 | `hermes cron remove --all` + disable hermes Prometheus scrape job |

### 16.3 Complete Config Reset (Emergency)

```bash
# Universal emergency rollback
hermes gateway stop
sudo systemctl start guinevere-discord
sudo systemctl disable hermes-gateway
rm -rf plugins/ hooks/ config/hermes/ .env.hermes
git checkout -- src/discord/ src/mcp/ src/persona/ src/hermes/
sudo systemctl restart guinevere-core guinevere-mcp guinevere-loops
# Verify: sudo systemctl status guinevere-discord | grep "active (running)"
# Verify: Send "HARD STOP" → neutral response
```

---

## 17. Cross-References

| Document | Relevance |
|---|---|
| ADR-035 Appendix A | Full config.yaml template (post-migration target) |
| ADR-035 Appendix B | Auth matrix config template |
| ADR-035 Appendix C | SOUL.md template |
| ADR-035 Appendix D | Shadow mode runbook (Phase 2) |
| 02-CONFIG-SYSTEM.md | Current config system analysis + gap report |
| `src/hermes/__init__.py` | Current hardcoded LLM config (to be migrated) |
| All 7 systemd service files | Current service topology (to be modified) |
| `monitoring/prometheus/prometheus.yml` | Scrape configs (add Hermes job in Phase 7) |
| `monitoring/alertmanager/alertmanager.yml` | Alert routing (unchanged, handles new alerts) |
| `monitoring/promtail/promtail-config.yml` | Log aggregation (add Hermes labels in Phase 7) |
| `monitoring/loki/loki-config.yml` | Log storage (unchanged) |
| `monitoring/compose.monitoring.yml` | Docker stack (unchanged) |
| `monitoring/.env` | Monitoring secrets (move to SOPS in Phase 7) |

---

## 18. Footer

| Field | Value |
|---|---|
| Author | Guinevere (Sisyphus-Junior, Agent 9 of 10) |
| Date | 2026-06-04 |
| Output Path | `research-reports/migration-plan/09-config-migration.md` |
| Line Count | 550+ |
| Sources Read | ADR-035 (full, 2512 lines), 02-CONFIG-SYSTEM.md, 7 systemd files, 8 monitoring configs, `__init__.py` |
| Approval | Requires Faiz review before Phase 0 execution |