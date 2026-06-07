# Phase 5 Verification — Services & Processes Health Baseline

**Report ID:** 01-services-baseline
**Date:** 2026-06-07 14:45 WIB (07:45 UTC)
**Environment:** Windows 11 Home (local dev) + VPS Ubuntu (guinevere-vps)
**Scope:** Comprehensive health baseline for all canonical Guinevere runtime services
**Status:** ⚠️ Partial — 1 of 5 canonical surfaces operational on local dev

---

## Executive Summary

| # | Service | Canonical Port | Local | VPS | Verdict |
|---|---------|:--------------:|:-----:|:---:|---------|
| 1 | **9Router** | 20128 | ✅ LIVE | ✅ LIVE | Fully operational. Next.js dashboard + OpenAI-compatible API. Health endpoint returns `{"ok":true}`. 44 models available. |
| 2 | **PostgreSQL** | 5433 | ❌ DOWN | ✅ ONLINE | No local listener. Docker/WSL unavailable. VPS instance accepting connections. |
| 3 | **Redis** | 6380 | ❌ DOWN | ✅ ONLINE | No local listener. VPS instance requires AUTH. |
| 4 | **guinevere-mcp** | 8090 | ❌ DOWN | ❌ NOT DEPLOYED | No listener. Not deployed as standalone HTTP service. FastMCP bridge defined in Hermes config but `enabled: false`. |
| 5 | **Discord / Hermes** | — | ❌ NOT LOCAL | ⚠️ PARTIAL | Standalone bot masked. Hermes gateway active but Discord connectivity unconfirmed. See `02-discord-status.md`. |

**Bottom-line:** Only **9Router** is operational in the local dev environment. All data-tier services (Postgres, Redis) and the agent runtime (Hermes/Discord) are VPS-deployed and not available for local testing. Phase 5 end-to-end tests requiring these services must either target the VPS or provision local equivalents.

---

## 1. Environment Context

### 1.1 Host System

| Property | Value |
|---|---|
| OS | Microsoft Windows 11 Home Single Language 10.0.26100 |
| CPU | AMD Ryzen 5 7530U with Radeon Graphics — 12 logical cores |
| RAM | 13.8 GB total, 3.1 GB free (77.9% used) |
| Uptime | 1 day 23 hours |
| Docker | ❌ Not installed |
| WSL | ❌ No distributions installed |

### 1.2 Network Listeners (All Ports)

Only non-system listeners:

| Port | Process | PID | Info |
|:----:|---------|:---:|------|
| 4096 | `kilo` | — | Text editor |
| 9222 | `msedgewebview2` | — | Edge WebView |
| 19528 | `cockpit-tools` | — | OCS cockpit |
| **20128** | **`node`** | **16088** | **9Router server** ✅ |
| 33395 | `tailscaled` | — | Tailscale |
| 42050 | `OneDrive.Sync.Service` | — | OneDrive |
| 51747 | `cockpit-cliproxy` | — | OCS cockpit |

No listeners on ports **5433** (Postgres), **6380** (Redis), or **8090** (guinevere-mcp).

---

## 2. Service-by-Service Probe Results

### 2.1 9Router — Port 20128 ✅

**Canonical port:** 20128
**Role:** AI model routing proxy (OpenAI-compatible API), provides LLM access to all Guinevere components.

#### Process Evidence

```
Process   : node.exe
PID       : 16088    (server process)
           18680    (CLI watcher)
Command   : node --max-old-space-size=6144 .../9router/app/server.js
           .../9router/cli.js
StartTime : 2026-06-05 23:07:14  (1d 15h 38m uptime)
Memory    : 263.8 MB (server) + 6.1 MB (CLI)
CPU (tot) : 24,779s (server)
```

#### HTTP Probe Results

| Endpoint | Method | HTTP Status | Response |
|----------|--------|:-----------:|----------|
| `/` | GET | 200 | Next.js dashboard (9341 B) — "9Router — AI Infrastructure Management" |
| `/api/health` | GET | 200 | `{"ok":true}` (2.2s response time) |
| `/v1` | GET | 200 | `{"object":"list","data":[...]}` — OpenAI-compatible models list |
| `/v1/models` | GET | 200 | 44 models available |

#### Available Models (44 total)

| Provider | Models |
|----------|--------|
| **combo** | `orcestrator`, `subagent`, `gpt`, `tester` |
| **ds (DeepSeek)** | `deepseek-v4-pro`, `deepseek-v4-pro-max`, `deepseek-v4-pro-none`, `deepseek-v4-flash`, `deepseek-chat`, `deepseek-reasoner` |
| **sf (StepFun)** | `step-3.5-flash`, `step-3.7-flash` |
| **xmtp** | `mimo-v2.5-pro`, `mimo-v2.5` |
| **cp (Codex)** | `gpt-5.5`, `gpt-5.4`, `gpt-5.4-mini` |
| **ocg (OpenCode Go)** | `deepseek-v4-flash`, `deepseek-v4-pro` |
| **openrouter** | `owl-alpha`, `lyria-3-pro-preview`, `lyria-3-clip-preview`, `qwen3-coder:free`, `nemotron-3-*:free`, `laguna-*:free`, `kimi-k2.6:free`, `gemma-4-*:free`, `qwen3-next:free` |
| **nvidia** | `minimax-m2.7`, `glm4.7`, `parakeet-ctc-1.1b-asr` |
| **ollama** | `gpt-oss:120b`, `minimax-m2.5` |
| **cf (Cloudflare)** | `kimi-k2.5`, `kimi-k2.6`, `glm-4.7-flash` |
| **cerebras** | `gpt-oss-120b`, `zai-glm-4.7` |

#### Verdict

**✅ PASS** — 9Router is fully operational. The health endpoint responds correctly, the models API returns a comprehensive list, and the dashboard is rendering. Response time for `/api/health` is ~2.2s (acceptable). Both server and CLI watcher processes have been running stably for >1.5 days.

---

### 2.2 PostgreSQL — Port 5433 ❌

**Canonical port:** 5433
**Role:** Primary persistent data store (memories, sessions, user data, audit logs).

#### Probe Evidence

```powershell
# TCP listener check
Get-NetTCPConnection -LocalPort 5433 -ErrorAction SilentlyContinue
# → No output (no listener)

# HTTP probe (TCP-level)
Invoke-WebRequest -Uri "http://localhost:5433/" -TimeoutSec 3
# → FAILED: The operation has timed out.

# Process check
Get-Process -Name "*postgres*" -ErrorAction SilentlyContinue
# → No output (no process)

# Service check
Get-Service -Name "*postgres*" -ErrorAction SilentlyContinue
# → No output (no service)

# Docker check
docker ps
# → 'docker' is not recognized (Docker not installed)

# WSL check
wsl --list --verbose
# → Windows Subsystem for Linux has no installed distributions
```

#### Root Cause

PostgreSQL is **not deployed locally**. It is only installed on the VPS (`guinevere-vps @ 100.94.104.22`) where it accepts connections on port 5433. The local dev environment (Windows 11) has:
- No Postgres Windows service installed
- No Docker (which could run a Postgres container)
- No WSL (which could host a Postgres instance)

The Hermes config template at `hermes-config/.env.template` confirms the canonical connection string:
```
DATABASE_URL=postgresql://hermes_app:<password>@localhost:5433/guinevere
```

#### Verdict

**❌ DOWN (local)** — Postgres is not available on the local development machine. Phase 5 tests requiring database operations must either:
1. Target the VPS instance directly
2. Provision a local Postgres instance (via installer or container)

---

### 2.3 Redis — Port 6380 ❌

**Canonical port:** 6380
**Role:** Caching, pub/sub, session storage, rate-limiting counters.

#### Probe Evidence

```powershell
# TCP listener check
Get-NetTCPConnection -LocalPort 6380 -ErrorAction SilentlyContinue
# → No output (no listener)

# HTTP probe (TCP-level)
Invoke-WebRequest -Uri "http://localhost:6380/" -TimeoutSec 3
# → FAILED: The operation has timed out.

# Process check
Get-Process -Name "*redis*" -ErrorAction SilentlyContinue
# → No output (no process)

# Service check
Get-Service -Name "*redis*" -ErrorAction SilentlyContinue
# → No output (no service)
```

#### Root Cause

Same as Postgres — Redis is **not deployed locally**. It runs only on the VPS. The canonical connection string from `hermes-config/.env.template`:
```
REDIS_URL=redis://localhost:6380/5
```

#### Verdict

**❌ DOWN (local)** — Redis is not available on the local development machine. Phase 5 tests requiring Redis must target the VPS or provision a local instance.

---

### 2.4 guinevere-mcp — Port 8090 ❌

**Canonical port:** 8090
**Role:** FastMCP custom bridge exposing KEEP-7 tools (postgres, redis, obscura_cdp, grep_app, context7, sequential_thinking, time).

#### Probe Evidence

```powershell
# HTTP probe
Invoke-WebRequest -Uri "http://localhost:8090/" -TimeoutSec 5
# → FAILED: Unable to connect to the remote server

# TCP listener check
Get-NetTCPConnection -LocalPort 8090 -ErrorAction SilentlyContinue
# → No output (no listener)

# Process check
Get-Process -Name "*mcp*","*guinevere*" -ErrorAction SilentlyContinue
# → No output (no process)
```

#### Configuration Reference

From `hermes-config/config.yaml`:
```yaml
mcp_servers:
  fastmcp_custom:
    enabled: false         # <-- EXPLICITLY DISABLED
    command: python
    args:
      - -m
      - src.mcp.custom_manager
    cwd: /home/guinevere/code/guinevere
    env_file: .env.mcp
```

The FastMCP bridge is:
1. **Disabled** (`enabled: false`) per BD-008 decision (direct production tool exposure blocked until pre_tool_call proof passes)
2. **VPS-only** — path references `/home/guinevere/code/guinevere`
3. **No HTTP server defined** — even if enabled, the Hermes MCP integration uses stdio transport, not an HTTP server on port 8090

Port 8090 is documented as "canonical" but there is no runtime component actually bound to it.

#### Verdict

**❌ NOT AVAILABLE** — The guinevere-mcp service is not deployed as an HTTP service anywhere. The FastMCP bridge exists in config but is disabled and uses stdio transport (not HTTP). Port 8090 appears to be an aspirational canonical port assignment that has not been implemented. Phase 5 cannot test against this endpoint.

---

### 2.5 Discord / Hermes Runtime ⚠️ PARTIAL

**Role:** Primary communication interface (Discord bot) and autonomous agent runtime (Hermes).

#### Local Environment

| Component | Status | Detail |
|-----------|--------|--------|
| Hermes Agent CLI | Installed v0.9.0 | 6673 commits behind upstream |
| Hermes gateway process | ❌ Not running | No local gateway daemon |
| Discord bot process | ❌ Not running | Not deployed on Windows |
| Hermes data directory | ✅ Exists | `C:\Users\faizz\.hermes\` with logs, sessions, memories |
| Hybrid guards logs | ✅ Active | Test cycles observed through Jun 7 04:08 UTC |

#### VPS Environment (guinevere-vps @ 100.94.104.22)

| Component | Status | Detail |
|-----------|--------|--------|
| `hermes-gateway.service` | ✅ **ACTIVE** | Running since Jun 7 12:05 WIB, PID 942968, ~3h uptime at probe time |
| `guinevere-discord.service` | ❌ **MASKED** | Inactive since Jun 5 07:54, requires unmask to restart |
| Discord adapter | ⚠️ Loaded | Opus/PyNaCl warnings but no "connected to Gateway" log observed |
| PostgreSQL (VPS) | ✅ Online | Accepting connections on port 5433 |
| Redis (VPS) | ✅ Online | Responding, requires AUTH |

#### Critical Blockers (from 02-discord-status.md)

| # | Blocker | T-Suite Impact |
|---|---------|:--------------:|
| B1 | Standalone bot service **masked** | T1, T2, T5 |
| B2 | Bot token SOPS-encrypted | T1, T2, T5 |
| B3 | Hermes Discord connectivity unconfirmed | T1, T2, T5 |
| B4 | Systemd unit timeout mismatch | T1 (indirect) |
| B5 | MCP servers misconfigured | T1 (indirect) |

#### Verdict

**⚠️ PARTIAL** — See `02-discord-status.md` for the full detailed report. The Hermes gateway is running but its Discord adapter connectivity is unconfirmed. The standalone Discord bot is masked and cannot be tested without SSH access to unmask and restart.

---

## 3. Additional Runtime Surfaces

### 3.1 Python Guinevere Package

| Check | Result |
|-------|--------|
| Global `guinevere` pip package | ❌ Not found |
| Venv `guinevere` pip package | ❌ pip not available in venv |
| `hermes-agent` pip package | ❌ Not found (dependency in pyproject.toml) |
| `cocoindex` pip package | ✅ Installed (v1.0.0a43, system Python 3.14) |
| Local `src/` directory | ✅ Present at `C:\Users\faizz\guinevere\src` |

The `guinevere` package is built from source via hatchling (see `pyproject.toml`). It is installed as editable (`pip install -e .`) in the project venv, but pip is not available in that venv to confirm.

### 3.2 Running Python Processes

| PID | Command | Started | Purpose |
|:---:|---------|---------|---------|
| 20284 | `python -m cocoindex_code.cli run-daemon` | Jun 6 13:50 | CocoIndex daemon (unrelated to Guinevere core) |
| 6168 | `python ...cerebras_benchmark2.py` | Jun 7 14:38 | Temporary benchmark script |

No Python processes related to Hermes, Discord, or guinevere-mcp are running locally.

### 3.3 Monitoring Stack

The monitoring stack (Prometheus, Grafana, Loki, Alertmanager) is defined in `monitoring/compose.monitoring.yml` as a Docker Compose deployment. Since Docker is not available locally, the monitoring stack is **not running**.

| Component | Status | Detail |
|-----------|--------|--------|
| Prometheus (9090) | ❌ DOWN | Docker-only |
| Grafana (3000) | ❌ DOWN | Docker-only |
| Loki (3100) | ❌ DOWN | Docker-only |
| Alertmanager (9093) | ❌ DOWN | Docker-only |

### 3.4 OCS/OpenCode MCP Servers (Local Only)

A large number of MCP server node processes are running locally. These are part of the OCS (OpenCode) runtime, not the Guinevere runtime. They are listed for completeness:

| Process Group | Count | Examples |
|--------------|:-----:|----------|
| 9Router core | 2 | server + CLI watcher |
| GitHub MCP | 2 | `@modelcontextprotocol/server-github` |
| Brave Search MCP | 2 | `@modelcontextprotocol/server-brave-search` |
| Filesystem MCP | 2 | `@modelcontextprotocol/server-filesystem` |
| Playwright MCP | 2 | `@playwright/mcp` |
| Sequential Thinking MCP | 2 | `@modelcontextprotocol/server-sequential-thinking` |
| Firecrawl MCP | 2 | `firecrawl-mcp` |
| Tavily MCP | 2 | `tavily-mcp` |
| Exa MCP | 2 | `exa-mcp-server` |
| Time MCP | 2 | `time-mcp` |
| Text Editor MCP | 2 | `mcp-server-text-editor` |
| MCP Fetch | 1 | `@kazuph/mcp-fetch` |
| Linkup MCP | 1 | `linkup-mcp-server` |
| Jina MCP | 1 | `jina-mcp-tools` |
| Cockpit tools | 1 | `cockpit-tools` |
| **Total** | **~30 node processes** | Including duplicates from npx caching |

All non-9Router MCP processes are **stdio-based** and service the OCS IDE, not the Guinevere runtime. They are irrelevant to Phase 5 verification except as potential resource consumers.

---

## 4. Canonical Port Audit

| Port | Service | Expected | Actual Local | Actual VPS | Mismatch |
|:----:|---------|:--------:|:------------:|:----------:|:--------:|
| 5433 | PostgreSQL | Required | ❌ No listener | ✅ Online | No local equivalent |
| 6380 | Redis | Required | ❌ No listener | ✅ Online | No local equivalent |
| 20128 | 9Router | Required | ✅ Listening | ✅ Online | None |
| 8090 | guinevere-mcp | Expected | ❌ No listener | ❌ Not deployed | Service does not exist as HTTP endpoint |
| 9090 | Prometheus | Optional | ❌ No listener | — | Docker-dependent |
| 3000 | Grafana | Optional | ❌ No listener | — | Docker-dependent |
| 3100 | Loki | Optional | ❌ No listener | — | Docker-dependent |
| 9093 | Alertmanager | Optional | ❌ No listener | — | Docker-dependent |
| 9191 | Hermes metrics | Expected | ❌ Not applicable | — | Hermes not running locally |

---

## 5. Process Resource Overview

### 5.1 Top Memory Consumers (Node.js)

| PID | Process | Memory | CPU Time | Uptime |
|:---:|---------|:------:|:--------:|:------:|
| 16088 | 9Router server | 263.8 MB | 24,779s | 1d 15h |
| 8040 | Filesystem MCP | 61.8 MB | 187.8s | 19h |
| 12384 | Filesystem MCP | 50.9 MB | 3.1s | 3h |
| 28432 | Exa MCP | 46.8 MB | 2.4s | 3h |
| 26760 | Brave Search MCP | 34.9 MB | 1.9s | 3h |
| 6824 | Seq Thinking MCP | 29.3 MB | 2.5s | 3h |
| 20284 | CocoIndex daemon | 25.9 MB | 0.4s | 1d |
| 14048 | Tavily MCP | 24.6 MB | 2.9s | 3h |
| 27416 | Text Editor MCP | 22.2 MB | 2.1s | 3h |

### 5.2 System Resource Pressure

| Resource | Value | Status |
|----------|:-----:|:------:|
| RAM usage | 77.9% (10.7 GB / 13.8 GB) | ⚠️ High |
| Free RAM | 3.1 GB | Adequate |
| CPU cores | 12 logical | Adequate |
| Node processes | ~30 | Moderate MCP overhead |

**Note:** The high RAM usage (~78%) is driven by the many MCP server processes plus the 9Router server. This is adequate for current operations but may cause pressure if additional services are started locally for testing.

---

## 6. Implications for Phase 5 Verification

### 6.1 Services Available for Local Testing

| Service | Usable Locally? | Notes |
|---------|:--------------:|-------|
| 9Router API | ✅ Yes | Full LLM routing available for test prompts |
| Node.js MCPs | ✅ Yes | Part of OCS, not Guinevere — but could be used for integration tests |

### 6.2 Services Requiring VPS Access

| Service | Required For | Action Needed |
|---------|-------------|---------------|
| PostgreSQL | T3 (Memory), T4 (Session), T6 (Audit) | SSH to VPS or provision local |
| Redis | T3 (Cache), T4 (Rate limiter), T6 (Pub/sub) | SSH to VPS or provision local |
| Hermes Gateway | T1 (Agent loop), T2 (Tool execution) | SSH to VPS for verification |
| Discord Bot | T1, T2, T5 (Channel tests) | Requires unmask + restart on VPS |

### 6.3 Services Not Available Anywhere

| Service | Impact | Mitigation |
|---------|--------|------------|
| guinevere-mcp (8090) | KEEP-7 tools not testable | Test individual tools via direct Hermes hook calls |

### 6.4 Recommendations

1. **For immediate local integration testing:** Only 9Router is available. Tests limited to LLM routing and model availability.

2. **For T1-T10 end-to-end verification:** Must target the VPS (guinevere-vps @ 100.94.104.22) via SSH. Requires:
   - SSH key access to `guinevere-vps`
   - `systemctl unmask guinevere-discord.service` (if standalone bot needed)
   - `systemctl restart hermes-gateway.service` (if gateway needs restart)

3. **For local service provisioning** (if VPS access is blocked):
   - Install PostgreSQL locally (standalone or via Chocolatey)
   - Install Redis locally (Memurai for Windows, or via Chocolatey)
   - Deploy monitoring stack via native installs (bypass Docker dependency)

4. **9Router health should be monitored** during Phase 5 testing — it is the single critical dependency available locally.

---

## 7. Evidence Sources

| # | Command | Output Location | Timestamp |
|---|---------|----------------|:---------:|
| E1 | `Get-NetTCPConnection -State Listen` | Inline | 14:45 WIB |
| E2 | `Get-Process \| Select Id, ProcessName, ...` | Inline | 14:45 WIB |
| E3 | `Get-CimInstance Win32_Process -Filter "Name='node.exe'"` | Inline | 14:46 WIB |
| E4 | `Get-CimInstance Win32_Process -Filter "Name='python.exe'"` | Inline | 14:46 WIB |
| E5 | `Invoke-WebRequest http://localhost:20128/api/health` | Inline | 14:47 WIB |
| E6 | `Invoke-WebRequest http://localhost:20128/v1/models` | Inline | 14:47 WIB |
| E7 | `Invoke-WebRequest http://localhost:20128/` | Inline | 14:46 WIB |
| E8 | `Invoke-WebRequest http://localhost:8090/` | Inline | 14:46 WIB |
| E9 | `Invoke-WebRequest http://localhost:5433/` | Inline | 14:46 WIB |
| E10 | `Invoke-WebRequest http://localhost:6380/` | Inline | 14:46 WIB |
| E11 | `Get-Service -Name '*postgres*','*redis*',...` | Inline | 14:45 WIB |
| E12 | `docker ps`, `wsl --list --verbose` | Inline | 14:45 WIB |
| E13 | `Get-CimInstance Win32_OperatingSystem` | Inline | 14:47 WIB |
| E14 | `hermes-config/config.yaml` (read) | Inline | 14:46 WIB |
| E15 | `hermes-config/.env.template` (read) | Inline | 14:47 WIB |
| E16 | `research-reports/phase5-verification/02-discord-status.md` | Cross-ref | 14:45 WIB |

### Command Reference

```powershell
# TCP listener audit
Get-NetTCPConnection -State Listen | Select-Object LocalPort, @{N='Process';E={(Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue).ProcessName}} | Sort-Object LocalPort

# Process audit
Get-CimInstance Win32_Process -Filter "Name='node.exe'" | Select-Object ProcessId, CommandLine

# HTTP health check
Invoke-WebRequest -Uri "http://localhost:<port>/<path>" -UseBasicParsing -TimeoutSec <N>

# Windows service check
Get-Service -Name '*keyword*' -ErrorAction SilentlyContinue

# System info
Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, TotalVisibleMemorySize, FreePhysicalMemory, LastBootUpTime
```

---

## 8. Footer

- **Authored:** 2026-06-07 14:45 WIB
- **Evidence root:** `research-reports/phase5-verification/`
- **Related reports:** `02-discord-status.md` (Discord/Hermes runtime deep-dive)
- **Canonical port source:** `hermes-config/config.yaml` line: `# CANONICAL PORTS: Redis 6380, Postgres 5433, 9Router 20128`
- **All status claims are directly observed** from process/service/HTTP evidence unless labeled as inferred
- **Next step:** Parent orchestrator reads this report before planning Phase 5 test execution
