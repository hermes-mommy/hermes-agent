# Hermes Agent — Complete Configuration State Report

> **Date:** 2026-06-05  
> **VPS:** guinevere-vps (100.94.104.22 via Tailscale)  
> **Assessor:** Guinevere (Sisyphus-Junior)  
> **Scope:** Read-only SSH inspection of all Hermes Agent config, state, plugins, hooks, memory, and services  
> **Purpose:** Phase 3 Memory Bridge Migration — ground-truth verification of Hermes state before migration

---

## 1. Hermes Installation

| Property | Value |
|---|---|
| **Binary path** | `/home/guinevere/code/guinevere/.venv/bin/hermes` |
| **Version** | `Hermes Agent v0.15.2 (2026.5.29.2)` |
| **Python** | 3.12.3 |
| **OpenAI SDK** | 2.24.0 |
| **pip package** | `hermes-agent==0.15.2` |
| **Install location** | `/home/guinevere/code/guinevere/.venv/lib/python3.12/site-packages/` |
| **Home directory** | `/home/guinevere/.hermes/` |
| **Required by** | `guinevere` (project package) |

Key pip dependencies: `croniter`, `fire`, `httpx`, `jinja2`, `openai`, `prompt_toolkit`, `psutil`, `pydantic`, `PyJWT`, `python-dotenv`, `pyyaml`, `requests`, `rich`, `ruamel.yaml`, `tenacity`

No standalone system binary (`which hermes` returned empty). Hermes is invoked exclusively via venv.

---

## 2. Configuration Files Inventory

### 2.1 Primary Config: `/home/guinevere/.hermes/config.yaml` (13,869 bytes)

**_config_version: 24** — this is the live, running configuration.

Full contents captured via SSH (13.9KB). Key sections summarized below.

### 2.2 Secondary Config: `/home/guinevere/config/hermes/config.yaml` (1,897 bytes)

This is a **separate Guinevere application-level config** (not Hermes Agent config). Contains:

- Agent identity: `Guinevere de Baroque`, version `0.1.0`
- LLM: 9Router → gpt-5.5 (primary), deepseek-v4-flash (sub-agent)
- Memory backend: `postgresql`, schema `memory`, redis_cache enabled (Redis DB 3)
- Embedding: `text-embedding-3-small`, 1536 dims
- Fallback: `graceful_degradation` disabled (per Faiz directive 2026-06-01)
- Safety: safe_word `HARD STOP`, yandere max `Y5`, baseline `Y4`
- Budget: monthly cap $30
- Plugins: `guinevere-safety`

### 2.3 Config Backup: `/home/guinevere/.hermes/config.yaml.bak.pre-phase2` (10,478 bytes)

Pre-Phase-2 snapshot. Compression settings differ: no `memory:` block with override values. `model:` field was empty (pre-9Router).

### 2.4 Other JSON/Config Files

| File | Purpose |
|---|---|
| `/home/guinevere/.hermes/auth.json` | OAuth credential pool — 1 OpenAI API key entry |
| `/home/guinevere/.hermes/gateway_state.json` | Gateway runtime state (running, Discord connected) |
| `/home/guinevere/.hermes/channel_directory.json` | Discord channel registry (5 channels across Guinevere's Domain) |
| `/home/guinevere/.hermes/shell-hooks-allowlist.json` | Approved shell hooks (consent_gate, dnr_filter) |
| `/home/guinevere/.hermes/sessions/sessions.json` | Active session registry (1 session) |
| `/home/guinevere/.hermes/gateway/discord_command_sync_state.json` | Discord slash command sync (47 commands created) |
| `/home/guinevere/.hermes/models_dev_cache.json` | Model catalog cache (2.2 MB) |
| `/home/guinevere/.hermes/.skills_prompt_snapshot.json` | Skills prompt snapshot (6.0 KB) |

---

## 3. Memory Provider Configuration

### 3.1 Hermes Agent Config (`config.yaml` — `memory:` block)

```yaml
memory:
  memory_enabled: true
  user_profile_enabled: true
  memory_char_limit: 2200
  user_char_limit: 1375
  provider: ""                           # ← EMPTY — no external provider configured
  compression:
    enabled: true
    threshold: 0.7                       # ← Confirmed: 0.7 as per research report 06
    target: 0.2                          # ← Confirmed: 0.2
    protect_last: 20                     # ← Confirmed: 20
  session_search:
    enabled: true
    backend: fts5                        # SQLite FTS5 full-text search
  mirrors:
    enabled: true
    sync_interval_messages: 5
  external:
    enabled: false
```

**Key Findings:**
- `provider: ""` — Hermes is using its **internal memory engine** (in-process, file-based via SQLite state.db)
- `external.enabled: false` — No external memory integration active
- `session_search` uses FTS5 (SQLite full-text search) — this is the current search mechanism
- Memory mirroring syncs every 5 messages

### 3.2 Guinevere App Config (`/home/guinevere/config/hermes/config.yaml` — `memory:` block)

```yaml
memory:
  backend: "postgresql"
  database: "guinevere"
  schema: "memory"
  redis_cache: true
  redis_db: 3
  embedding_model: "text-embedding-3-small"
  embedding_dimensions: 1536
  max_recall_items: 20
  context_injection: true
```

This is the **target configuration** for the Guinevere app's own memory system — PostgreSQL-based with Redis caching and embedding support. This is **not** what Hermes Agent currently uses.

### 3.3 Environment Variables (`.env`)

```
MEMORY_BACKEND=redis          # Override in .env — Redis-based
DATABASE_URL=postgresql+asyncpg://guinevere_core:***@localhost:5433/guinevere
REDIS_URL=redis://localhost:6380/5
```

The `.env` `MEMORY_BACKEND=redis` suggests a Redis-based memory intent, but `config.yaml` `provider: ""` means no provider is wired.

### 3.4 Memory Files Directory

**`/home/guinevere/.hermes/memories/` — EMPTY** (only `.` and `..`). No memory files stored on disk. Memory is held in the SQLite state database.

---

## 4. Compression Settings

### 4.1 Global Compression (`config.yaml` — `compression:` block)

```yaml
compression:
  enabled: true
  threshold: 0.5             # Trigger at 50% context window usage
  target_ratio: 0.2          # Compress down to 20%
  protect_last_n: 20         # Keep last 20 messages
  hygiene_hard_message_limit: 400
  protect_first_n: 3         # Keep first 3 messages
  abort_on_summary_failure: false
```

### 4.2 Memory-Specific Compression (`config.yaml` — `memory.compression:` block)

```yaml
memory:
  compression:
    enabled: true
    threshold: 0.7           # Memory-specific: 70% threshold (more aggressive than global 50%)
    target: 0.2              # Same target: 20%
    protect_last: 20         # Same: keep last 20
```

### 4.3 Summary

| Setting | Global Compression | Memory Compression |
|---|---|---|
| `enabled` | true | true |
| `threshold` | 0.5 | **0.7** |
| `target` / `target_ratio` | 0.2 | 0.2 |
| `protect_last` / `protect_last_n` | 20 | 20 |
| `protect_first` | 3 | N/A |
| `hygiene_limit` | 400 | N/A |

**Note:** Memory compression threshold of 0.7 means memory compression triggers at 70% — more aggressive than the global 50%. This aligns with research report 06 findings (threshold=0.7, target=0.2, protect_last=20).

---

## 5. Session Configuration

### 5.1 Active Configuration (`config.yaml`)

```yaml
sessions:
  auto_prune: false          # Manual pruning only
  retention_days: 90
  vacuum_after_prune: true
  min_interval_hours: 24
  write_json_snapshots: false   # Sessions not written as JSON snapshots
```

### 5.2 Agent Configuration

```yaml
agent:
  max_turns: 90
  gateway_timeout: 1800
  restart_drain_timeout: 180
  api_max_retries: 3
  max_iterations: 15
  name: Guinevere
  role: autonomous-ai-companion
  new_instance_per_invocation: true
  gateway_auto_continue_freshness: 3600
```

### 5.3 Active Sessions

Current state in `sessions.json`:
- **1 active session** — `agent:main:discord:group:1510914600777023659:1146639950654214264`
- Created: `2026-06-05T10:23:08Z`
- Platform: Discord, group chat
- Channel: `guinevere-chat` in Guinevere's Domain
- User: Ssnford (1146639950654214264)
- Last prompt tokens: 15,191
- Not suspended, not reset, not finalised

### 5.4 TTL / Skip Memory

- **No explicit TTL** in session config — sessions live for `retention_days: 90`
- **`skip_memory` flag**: Not found in config. Hermes v0.15.2 does not appear to have this as a config key.
- **`turn` limits**: `max_turns: 90` per agent invocation, `max_iterations: 15`
- **`group_sessions_per_user: true`** (in .env) — each user gets their own session in group chats

---

## 6. Plugin Directory Structure

### 6.1 Plugin Directory: `/home/guinevere/.hermes/plugins/`

```
plugins/
├── guinevere-safety/           # Migrated plugin (Phase 2 Wave 4)
│   ├── __init__.py             # 1,159 bytes
│   ├── plugin.yaml             # 286 bytes — hooks: pre/post_llm_call, pre/post_tool_call, transform, on_session_start
│   └── __pycache__/
│       └── __init__.cpython-312.pyc
│
└── guinevere_safety/           # Original plugin (Phase 1)
    ├── __init__.py             # 146 bytes
    ├── manifest.yaml           # 588 bytes — hooks: pre/post_llm_call; commands: get_persona_state, set_punishment, set_reward, set_mood, get_distress
    ├── plugin.py               # 8,816 bytes
    └── state_manager.py        # 19,518 bytes
```

### 6.2 Enabled Plugins (`config.yaml` — `plugins:` block)

```yaml
plugins:
  enabled:
    - guinevere-safety           # Active: the Phase 2 migrated plugin
    - model-providers/custom     # Listed but NO directory found in plugins/
  disabled: []
```

### 6.3 Plugin Config in Guinevere App (`/home/guinevere/config/hermes/config.yaml`)

```yaml
plugins:
  enabled:
    - guinevere-safety           # Also enabled at app level
```

**Note:** Both `guinevere-safety` AND `guinevere_safety` directories exist. The enabled config only lists `guinevere-safety`. The `guinevere_safety` directory appears to be a leftover from Phase 1. Both have different manifest structures — `guinevere-safety` has a `plugin.yaml` (Hermes native) while `guinevere_safety` has a `manifest.yaml` (custom format).

---

## 7. Custom Hooks and Extensions

### 7.1 Hook Scripts (`/home/guinevere/.hermes/hooks/`)

| File | Size | Hook Event | Priority | Timeout | On Failure |
|---|---|---|---|---|---|
| `consent_gate.py` | 6,413 B | `pre_tool_call` | 90 | 200ms | BLOCK |
| `dnr_filter.py` | 6,082 B | `post_tool_call` | 70 | 50ms | BLOCK |
| `drift_check.py` | 6,889 B | `post_prompt` | — | 100ms | WARN |
| `hard_stop.py` | 7,197 B | `pre_prompt` | — | 50ms | BLOCK |
| `safety_scan.py` | 11,011 B | `post_response` | — | 100ms | BLOCK |
| `error_classifier.py` | 8,509 B | (not in active hook config) | — | — | — |
| `_hook_utils.py` | 9,018 B | (shared utility) | — | — | — |

### 7.2 Active Hook Configuration (`config.yaml`)

```yaml
hooks:
  pre_tool_call:
    - event: pre_tool_call
      command: python3 ~/.hermes/hooks/consent_gate.py
      timeout_ms: 200
      on_failure: block
      priority: 90
  post_tool_call:
    - event: post_tool_call
      command: python3 ~/.hermes/hooks/dnr_filter.py
      timeout_ms: 50
      on_failure: block
      priority: 70
hooks_auto_accept: false
```

**Only 2 of 7 hooks are active** — `consent_gate` and `dnr_filter`. The remaining hooks (`drift_check`, `hard_stop`, `safety_scan`, `error_classifier`) exist in the filesystem but are **not** wired in `config.yaml`. The `guinevere_safety` plugin handles the `pre_llm_call`/`post_llm_call` hooks, and `guinevere-safety` plugin handles additional hook events.

### 7.3 Hook Code Summaries

- **consent_gate.py**: Pre-tool-call consent check against Redis DB5. Blocks surveillance, destructive, and config-change tools unless consent is granted. Reads from `guinevere:consent` key.
- **dnr_filter.py**: Post-tool-call DNR (Do Not Remember) filter. Strips sensitive output before memory storage.
- **drift_check.py**: Post-prompt persona drift check. Scans for Y6 indicators, generic AI language, persona contradictions.
- **hard_stop.py**: Pre-prompt safe word detection. Checks for "HARD STOP" and semantic equivalents. Uses Redis DB5 `guinevere:safe_word` key.
- **safety_scan.py**: Post-response safety scan for F-01..F-15 forbidden patterns before Discord delivery.
- **error_classifier.py**: Error classification utility (not wired as hook).
- **_hook_utils.py**: Shared Redis connection, stdin/stdout JSON I/O, and logging utilities.

### 7.4 Shell Hooks Allowlist

```json
{
  "approvals": [
    {
      "approved_at": "2026-06-05T01:27:03Z",
      "command": "python3 ~/.hermes/hooks/consent_gate.py",
      "event": "pre_tool_call"
    },
    {
      "approved_at": "2026-06-05T01:27:03Z",
      "command": "python3 ~/.hermes/hooks/dnr_filter.py",
      "event": "post_tool_call"
    }
  ]
}
```

---

## 8. Environment Variables

### 8.1 Hermes `.env` File (`/home/guinevere/.hermes/.env`)

| Variable | Value | Source |
|---|---|---|
| `DISCORD_BOT_TOKEN` | `[REDACTED]` | Direct value |
| `DISCORD_ALLOWED_USERS` | `1146639950654214264` | Faiz's Discord ID |
| `DISCORD_ALLOWED_CHANNELS` | `1510914600777023659` | #guinevere-chat |
| `DISCORD_REQUIRE_MENTION` | `false` | |
| `DISCORD_FREE_RESPONSE_CHANNELS` | `1510914600777023659` | |
| `NINEROUTER_API_KEY` | `[REDACTED]` | 9Router auth |
| `LLM_BASE_URL` | `http://localhost:20128/v1` | 9Router proxy |
| `LLM_MODEL` | `gpt-5.5` | Primary model |
| `LLM_FALLBACK_MODEL` | `deepseek-v4-flash` | |
| `DATABASE_URL` | `postgresql+asyncpg://guinevere_core:***@localhost:5433/guinevere` | PgBouncer port |
| `REDIS_URL` | `redis://localhost:6380/5` | Redis DB 5 |
| `MEMORY_BACKEND` | `redis` | |
| `GROUP_SESSIONS_PER_USER` | `true` | |
| `PROMETHEUS_METRICS_PORT` | `9191` | |
| `LOG_LEVEL` | `info` | |
| `LOG_FORMAT` | `json` | |
| `DISCORD_SHADOW_BOT_TOKEN` | `[REDACTED]` | Shadow bot |
| `DISCORD_SHADOW_BOT_ID` | `1512088992764399717` | |
| `SHADOW_ENABLED` | `true` | Shadow mode active |
| `SHADOW_TRAFFIC_PCT` | `10` | 10% shadowing |
| `OPENAI_API_KEY` | `[REDACTED]` | Same as ninerouter key |
| `OPENAI_BASE_URL` | `http://localhost:20128/v1` | |
| `HERMES_INFERENCE_PROVIDER` | `ninerouter` | |

### 8.2 Running Process Environment

The `env \| grep hermes` command returned no output in the SSH session — this is expected as the `hermes gateway` process runs as a child of guinevere-core/loops and its environment is inherited.

### 8.3 Env Template (`/home/guinevere/code/guinevere/hermes-config/.env.template`)

Uses `<SOPS:...>` placeholders for all secrets. Template matches the deployed `.env` structure with SOPS references instead of plaintext values.

---

## 9. Hermes Service Status

### 9.1 Running Process

```
PID: 3359203
CMD: /home/guinevere/code/guinevere/.venv/bin/python
     /home/guinevere/code/guinevere/.venv/bin/hermes gateway run --accept-hooks
CPU: 0.4%
Memory: 223 MB (1.3% of system)
Started: ~10:08 UTC
State: RUNNING
```

### 9.2 Gateway State

```json
{
  "pid": 3359203,
  "kind": "hermes-gateway",
  "gateway_state": "running",
  "restart_requested": false,
  "active_agents": 0,
  "platforms": {
    "discord": {
      "state": "connected",
      "updated_at": "2026-06-05T03:09:17Z"
    }
  }
}
```

### 9.3 Systemd Services

Hermes is **NOT** managed as a standalone systemd service. There is no `hermes.service` or `hermes-agent.service`. It runs as a child process launched by either:
- `guinevere-loops.service` — Agent Loop Daemon
- `guinevere-core.service` — Core Daemon

Both are active and running:

```
guinevere-core.service       loaded active running   Guinevere Core Daemon
guinevere-loops.service      loaded active running   Guinevere Agent Loop Daemon
guinevere-scheduler.service  loaded active running   Guinevere Loop Scheduler Daemon
guinevere-discord.service    loaded active running   Guinevere Discord Bot
guinevere-surveillance.service loaded active running Guinevere Surveillance Consumer
guinevere-monitoring.service loaded active running   Monitoring Stack
guinevere-9router.service    loaded active running   Guinevere 9Router LLM Proxy
```

### 9.4 Docker Containers

| Container | Image | Purpose | Port |
|---|---|---|---|
| `guinevere-redis` | `redis:7.4-alpine` | Redis (DB 5 for memory) | `127.0.0.1:6380→6379` |
| `guinevere-prometheus` | `prom/prometheus:v3.3.0` | Metrics | `127.0.0.1:9090` |
| `guinevere-grafana` | `grafana/grafana:11.5.0` | Dashboards | `127.0.0.1:3000` |
| `guinevere-loki` | `grafana/loki:3.4.0` | Log aggregation | `127.0.0.1:3100` |
| `guinevere-promtail` | `grafana/promtail:3.5.8` | Log shipping | — |
| `guinevere-alertmanager` | `prom/alertmanager:v0.28.0` | Alerting | `127.0.0.1:9093` |
| `guinevere-redis-exporter` | `oliver006/redis_exporter:v1.67.0` | Redis metrics | `127.0.0.1:9121` |
| `guinevere-postgres-exporter` | `prometheuscommunity/postgres-exporter:v0.17.1` | PG metrics | `127.0.0.1:9187` |
| `guinevere-node-exporter` | `prom/node-exporter:v1.9.0` | System metrics | `127.0.0.1:9100` |

No `guinevere-postgres` in Docker — PostgreSQL is running natively or via a separate container not in the default `docker ps` output. PgBouncer is configured at port 5433.

---

## 10. Code Project Structure

### 10.1 Guinevere Project (`/home/guinevere/code/guinevere/`)

Key Hermes-related code:

| Path | Purpose |
|---|---|
| `src/hermes/memory_bridge.py` | Memory bridge between Hermes and Guinevere |
| `src/hermes/session_adapter.py` | Session adapter for Hermes sessions |
| `src/hermes/safety_plugin.py` | Safety plugin implementation |
| `src/hermes_plugins/commands_memory/` | Memory-related commands |
| `hermes-config/` | Template config directory (hooks, plugins, SOUL.md, .env.template) |
| `tests/hermes/` | Hermes test suite |
| `alembic/versions/` | Database migrations (no memory-specific migrations found) |
| `research-reports/hermes-phase1/` | Phase 1 research |
| `research-reports/hermes-phase2/` | Phase 2 research |
| `research-reports/hermes-integration/` | Integration research |
| `research-reports/hermes-restructure/` | Restructure research |

### 10.2 Skills Hub

22 skill directories installed under `/home/guinevere/.hermes/skills/`:

`apple`, `autonomous-ai-agents`, `creative`, `data-science`, `diagramming`, `domain`, `email`, `gaming`, `gifs`, `github`, `inference-sh`, `mcp`, `media`, `mlops` (8 subdirs), `note-taking`, `productivity`, `research`, `smart-home`, `social-media`

Plus `.hub/` with index cache and quarantine.

---

## 11. Database and Infrastructure

### 11.1 PostgreSQL
    
- **Connection:** `localhost:5433/guinevere` (via PgBouncer)
- **User:** `guinevere_core`
- **Memory schema:** `memory` (defined in app config, not in Hermes config)
- **Hermes state DBs:** SQLite (`state.db`, `kanban.db`)

### 11.2 Redis

- **Connection:** `localhost:6380/5`
- **DB 3:** memory cache (app config)
- **DB 5:** Hermes runtime state, consent gate, safe word, session data

### 11.3 9Router

- **URL:** `http://localhost:20128/v1`
- **Service:** `guinevere-9router.service` (active)
- **Primary model:** `gpt-5.5`
- **Fallback model:** `deepseek-v4-flash`

---

## 12. Cron Jobs (Scheduled Tasks)

```yaml
cron:
  - name: daily_health_check    # 06:00 daily — hermes doctor --report
  - name: weekly_backup         # 02:00 Sundays — hermes backup --full
  - name: monthly_security_scan # 03:00 1st of month — hermes security --report
  - name: ritual_morning        # 08:00 daily
  - name: ritual_midday         # 12:00 daily
  - name: ritual_afternoon      # 16:00 daily
  - name: ritual_evening        # 20:00 daily
  - name: ritual_midnight       # 00:00 daily
```

All 8 cron jobs enabled. Ritual jobs trigger `guinevere_safety` plugin mood/state updates.

---

## 13. SOUL.md and Persona

### 13.1 SOUL.md (`/home/guinevere/.hermes/SOUL.md` — 18,326 bytes)

Complete persona specification:
- Identity: Guinevere de Baroque, 28, noble, "Mommy" self-reference
- HARD STOP protocol (9-step immediate response)
- Yandere intensity: Y4 baseline, Y5 ceiling, Y6 BLOCKED
- Punishment: L1-L5 active, L6 deferred
- Reward tiers: T1-T5
- Distress levels: D0-D4

### 13.2 System Prompt Master (`/home/guinevere/config/hermes/system-prompt.md` — 23,942 bytes)

Canonical deployable system prompt with ~8300 token budget. Sections:
- §A Core Identity Block
- §B Dominant Behavior Instructions
- (§C onwards — not fully read, remainder in file)

---

## 14. Key Findings and Phase 3 Impact

### 14.1 Research Report 06 Verification

| Claim | Verified? | Details |
|---|---|---|
| `threshold: 0.7` | ✅ CONFIRMED | Memory compression threshold is 0.7 |
| `target: 0.2` | ✅ CONFIRMED | Memory compression target is 0.2 |
| `protect_last: 20` | ✅ CONFIRMED | Memory compression protect_last is 20 |
| `compression enabled: true` | ✅ CONFIRMED | Both global and memory compression enabled |

### 14.2 Critical Gaps for Phase 3 Memory Bridge

1. **`provider: ""`** — Hermes memory provider is EMPTY. No external memory system connected. This is the primary gap that Phase 3 must bridge.

2. **`external.enabled: false`** — External memory integration explicitly disabled. Must be enabled and pointed at the PostgreSQL/Redis memory backend.

3. **Empty memories directory** — `/home/guinevere/.hermes/memories/` has zero files. All memory is held in the SQLite state database (`state.db` — 106KB + 1.3MB WAL). Phase 3 migration must extract from SQLite into PostgreSQL.

4. **App-level memory config exists but not wired** — `/home/guinevere/config/hermes/config.yaml` has a full PostgreSQL memory configuration (schema `memory`, embedding `text-embedding-3-small`, Redis cache DB 3) but this is NOT connected to Hermes Agent.

5. **Two plugin directories** — `guinevere-safety` (active) and `guinevere_safety` (legacy). Phase 3 should clean up the legacy directory.

6. **MEMORY_BACKEND=redis** in `.env` but `provider: ""` in config — environment variable specifies Redis but no provider is wired to consume it.

7. **No Docker PostgreSQL** — The monitoring stack runs in Docker but PostgreSQL does not appear in `docker ps`. PgBouncer connects to `guinevere-postgres:5432` which may be a system-level or separate Docker host.

8. **Unwired safety hooks** — `drift_check.py`, `hard_stop.py`, and `safety_scan.py` exist in the hooks directory but are NOT wired in `config.yaml`. Actual safety enforcement is handled by the `guinevere-safety` plugin at the LLM-call level rather than the hook level.

### 14.3 Migration Path Summary

| From | To | Bridge Method |
|---|---|---|
| SQLite state.db (Hermes internal) | PostgreSQL memory schema | Extract → Transform → Load via alembic |
| In-process FTS5 search | PostgreSQL pgvector/Redis embeddings | Rebuild index during migration |
| `provider: ""` | Wired to Guinevere memory backend | Update `config.yaml` memory block |
| `external.enabled: false` | `external.enabled: true` | Enable external memory integration |
| Legacy `guinevere_safety/` | Keep `guinevere-safety/` only | Remove legacy, validate single plugin |

---

## 15. Report Metadata

| Field | Value |
|---|---|
| Report path | `research-reports/phase-3-execution/02-hermes-config-state.md` |
| Assessor | Guinevere (Sisyphus-Junior) |
| Session | 2026-06-05 |
| Total SSH commands | 15 |
| Files inspected | 30+ |
| Tokens/secrets redacted | Yes — 4 instances |
| Modifications made | None (read-only assessment) |
| Verification method | Direct SSH inspection, no sub-agents |

---

## Appendix A: Full Directory Tree (`/home/guinevere/.hermes/`)

```
/home/guinevere/.hermes/
├── .env (1,286 B)
├── .skills_prompt_snapshot.json (6,022 B)
├── .update_check (52 B)
├── SOUL.md (18,326 B)
├── SOUL.md.bak.pre-phase2 (513 B)
├── auth.json (649 B)
├── auth.lock (0 B)
├── bin/
│   └── tirith (12 MB)
├── cache/
│   └── documents/
├── channel_directory.json (3,011 B)
├── config.yaml (13,869 B)
├── config.yaml.bak.pre-phase2 (10,478 B)
├── cron/
│   ├── .tick.lock
│   └── output/
├── gateway/
│   ├── discord_command_sync_state.json (268 B)
│   └── gateway.pid (164 B)
├── gateway.lock (164 B)
├── gateway_state.json (424 B)
├── hooks/
│   ├── __pycache__/
│   ├── _hook_utils.py (9,018 B)
│   ├── consent_gate.py (6,413 B)
│   ├── dnr_filter.py (6,082 B)
│   ├── drift_check.py (6,889 B)
│   ├── error_classifier.py (8,509 B)
│   ├── hard_stop.py (7,197 B)
│   └── safety_scan.py (11,011 B)
├── kanban.db (106 KB)
├── kanban.db.init.lock (0 B)
├── logs/
│   ├── agent.log (368 KB)
│   ├── errors.log (180 KB)
│   ├── gateway-exit-diag.log (9 KB)
│   ├── gateway-shutdown-diag.log (36 KB)
│   ├── gateway.log (64 KB)
│   ├── curator/
│   └── hooks/
├── memories/ (EMPTY)
├── models_dev_cache.json (2.2 MB)
├── pairing/ (EMPTY)
├── plugins/
│   ├── guinevere-safety/
│   │   ├── __init__.py (1,159 B)
│   │   ├── plugin.yaml (286 B)
│   │   └── __pycache__/
│   └── guinevere_safety/
│       ├── __init__.py (146 B)
│       ├── manifest.yaml (588 B)
│       ├── plugin.py (8,816 B)
│       └── state_manager.py (19,518 B)
├── sandboxes/
│   └── singularity/
├── sessions/
│   ├── request_dump_*.json (69 KB)
│   └── sessions.json (1,326 B)
├── shell-hooks-allowlist.json (464 B)
├── shell-hooks-allowlist.json.lock (0 B)
├── skills/ (22 directories)
├── state.db (106 KB)
├── state.db-shm (33 KB)
├── state.db-wal (1.3 MB)
├── audio_cache/
└── image_cache/
```

## Appendix B: Full Config Differential — Pre-Phase2 vs Current

Key changes between `config.yaml.bak.pre-phase2` and current `config.yaml`:

| Setting | Pre-Phase2 | Current |
|---|---|---|
| `model` | `""` (empty) | `ds/deepseek-v4-flash` |
| `providers` | `{}` (empty) | `ninerouter` defined |
| `llm.provider` | (not present) | `custom` |
| `llm.model` | (not present) | `ds/deepseek-v4-flash` |
| `llm.base_url` | (not present) | `http://localhost:20128/v1` |
| `memory.compression.threshold` | (not present) | `0.7` |
| `memory.compression.target` | (not present) | `0.2` |
| `memory.compression.protect_last` | (not present) | `20` |
| `memory.mirrors` | (not present) | `enabled: true, sync_interval: 5` |
| `memory.session_search` | (not present) | `enabled: true, backend: fts5` |
| `hooks` | (empty) | 2 hooks active |
| `plugins` | (not present) | `guinevere-safety`, `model-providers/custom` |
| `cron` | (not present) | 8 cron jobs |
| `mcp_servers` | (not present) | web, filesystem, terminal, git, fetch |
| `observability` | (not present) | Prometheus, structured logging |
| `auth_matrix` | (not present) | Full RBAC matrix |
| `discord` | (not present) | Full Discord config |