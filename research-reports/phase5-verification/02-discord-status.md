# Phase 5 Verification — Discord Bot Runtime Status Report

**Report ID:** 02-discord-status
**Date:** 2026-06-07
**Environment:** Windows 11 (local dev) + VPS Ubuntu (guinevere-vps @ 100.94.104.22)
**Scope:** Local runtime evidence + VPS journal/service inspection
**Direct Discord API validation:** NOT POSSIBLE (no decrypted bot token available locally; SOPS-encrypted secrets)

---

## Executive Summary

| Component | Status | Verdict |
|---|---|---|
| `guinevere-discord.service` (standalone bot) | **MASKED — INACTIVE** | Stopped since Jun 5, cannot be started without unmasking |
| `hermes-gateway.service` (Hermes Discord adapter) | **ACTIVE — RUNNING** | Up since Jun 7 12:05 WIB, Discord library loaded, connectivity unconfirmed |
| Local Hermes CLI | Installed v0.9.0, 6673 commits behind | Hook logs show recent activity, no bot process |
| PostgreSQL (VPS) | Online, port 5433 accepting | Required by bot |
| Redis (VPS) | Online, port 6380, auth required | Required by bot |

**Bottom-line:** The standalone Discord bot is **not available** (service masked). The Hermes gateway is running and has a Discord adapter loaded, but no explicit "gateway connected" signal was observed in journal logs. Downstream T1/T2/T5 Discord-channel verification cannot proceed against the standalone bot without unmasking and restarting it.

---

## 1. Local Environment (Windows 11)

### 1.1 Running Processes

No Discord or Hermes bot process is running locally. All Python processes are unrelated (cocoindex daemon, temporary benchmark script). All Node.js processes are MCP servers/npx agents — none are Discord-related.

```powershell
# Python processes
ProcessId CommandLine
20284    C:\Python314\python.exe -m cocoindex_code.cli run-daemon
 6168    C:\Python314\python.exe ...\cerebras_benchmark2.py
```

### 1.2 Hermes CLI Installation

Hermes Agent v0.9.0 is installed locally at `C:\Users\faizz\AppData\Local\hermes\hermes-agent`:

```
Hermes Agent v0.9.0 (2026.4.13)
Project: C:\Users\faizz\AppData\Local\hermes\hermes-agent
Python: 3.12.10
Update available: 6673 commits behind — run 'hermes update'
```

The CLI supports `gateway` and `chat` commands, but no gateway process is running locally.

### 1.3 Local Hermes Data Directory

Path: `C:\Users\faizz\.hermes\`

| Item | Size | Last Modified | Notes |
|---|---|---|---|
| `logs/hooks/hybrid_guards.log` | 70,795 B | Jun 7 11:08 | Active hook test cycles |
| `logs/agent.log` | 0 B | Jun 5 | Empty — no agent errors |
| `logs/errors.log` | 0 B | Jun 5 | Empty — no errors |
| `logs/hooks/budget_check.log` | 0 B | Jun 5 | Empty |
| `sessions/` | — | Jun 5 | Session directory exists |
| `memories/` | — | Jun 5 | Memory directory exists |
| `SOUL.md` | 513 B | Jun 5 | Identity/Soul configuration |
| `cron/` | — | Jun 5 | Cron directory exists |

### 1.4 Hybrid Guards Log Analysis

The `hybrid_guards.log` shows repeated test cycles (JSONL format, ~10 entries per cycle) running from **Jun 5 13:01 UTC** through **Jun 7 04:08 UTC** (latest). Each test cycle exercises the same tools:

| Tool | Result | Notes |
|---|---|---|
| `time` | ALLOWED | Always passes |
| `shell` | BLOCKED | Shell injection pattern `;` detected (test input) |
| `docker` | BLOCKED | Non-guinevere container blocked (test input) |
| `docker` | ALLOWED | Valid operation |
| `git` | BLOCKED | Force-push to protected branch blocked (test input) |
| `filesystem` | BLOCKED | Aizanta directory isolation (test input) |
| `postgres` | BLOCKED | Standard port 5432 blocked (test input) |
| stdin | ERROR | Invalid/empty JSON (test input) |
| `git` | BLOCKED | Force-push check (test input) |
| `shell` | ALLOWED | Valid operation |

**Pattern:** These appear to be automated guard-rule test invocations, not actual interactive sessions. The `Failed to read stdin: invalid or empty JSON` error occurs on every cycle, suggesting these are triggered by a cron/scheduler that feeds empty JSON to the hook system.

---

## 2. VPS Environment (guinevere-vps @ 100.94.104.22)

### 2.1 Service Status

#### `guinevere-discord.service` — STANDALONE DISCORD BOT

```
○ guinevere-discord.service
     Loaded: masked (Reason: Unit guinevere-discord.service is masked.)
     Active: inactive (dead)
```

- **State:** MASKED (not just stopped — masked with `systemctl mask`)
- **Service type:** `Type=exec`, runs `python -m src.discord._entrypoint`
- **Token source:** SOPS-decrypted from `secrets/.env.discord.sops`
- **Last active:** June 5, 2026 (systemd journal below)

#### `hermes-gateway.service` — HERMES AGENT GATEWAY

```
● hermes-gateway.service - Hermes Agent Gateway (Discord)
     Loaded: loaded (/etc/systemd/system/hermes-gateway.service; enabled)
     Active: active (running) since Sun 2026-06-07 12:05:36 WIB; ~3h ago
   Main PID: 942968 (hermes)
      Tasks: 14
     Memory: 106.2M (high: 512.0M max: 1.0G)
```

- **State:** Active, running
- **User:** guinevere
- **Service definition:** `hermes gateway run --accept-hooks`
- **Environment file:** `/home/guinevere/.hermes/.env`
- **Discord config:** Present in `hermes-config/config.yaml` (channel #guinevere-chat)

### 2.2 Standalone Bot Last Activity (journal excerpt)

```
Jun 05 07:15:38 faiz-prod-01 python[3247866]: __main__ [INFO] guinevere_bot_init
Jun 05 07:15:38 faiz-prod-01 python[3247866]: src.discord.shadow_pipeline [INFO] shadow_pipeline_initialized
Jun 05 07:15:39 faiz-prod-01 python[3247866]: discord.client [INFO] logging in using static token
Jun 05 07:15:40 faiz-prod-01 python[3247866]: __main__ [INFO] commands_synced
Jun 05 07:15:40 faiz-prod-01 python[3247866]: apscheduler.scheduler [INFO] Scheduler started
Jun 05 07:15:40 faiz-prod-01 python[3247866]: 2026-06-05 07:15:40 [info] ritual_scheduler_started
Jun 05 07:15:41 faiz-prod-01 python[3247866]: discord.gateway [INFO] Shard ID None has connected to Gateway
Jun 05 07:15:43 faiz-prod-01 python[3247866]: __main__ [INFO] bot_ready
Jun 05 07:15:43 faiz-prod-01 python[3247866]: src.discord.startup [INFO] startup_greeting_sent
Jun 05 07:54:07 faiz-prod-01 systemd[1]: Stopping guinevere-discord.service...
Jun 05 07:54:07 faiz-prod-01 systemd[1]: guinevere-discord.service: Deactivated successfully.
```

**Observations:**
- The bot successfully connected to Discord Gateway (Shard ID None)
- It sent a startup greeting
- Ritual scheduler was active (morning, midday, afternoon, evening, midnight)
- It ran for ~38 minutes before being stopped on Jun 5 at 07:54
- After stopping, the unit was **masked** (preventing auto-restart)

### 2.3 Hermes Gateway Discord Adapter Status

The Hermes gateway logs show:

```
WARNING hermes_plugins.discord_platform.adapter: Opus codec not found
WARNING discord.client: PyNaCl is not installed, voice will NOT be supported
WARNING discord.client: davey is not installed, voice will NOT be supported
```

- The Discord platform adapter IS loaded (it initializes `discord.client`)
- Voice features are disabled (non-critical)
- **No explicit "connected to Gateway" message** was observed — may indicate:
  - The adapter has not fully connected to Discord
  - The connection log is at DEBUG level (not captured in journald default level)
  - The gateway is waiting for an incoming message to trigger the connection

### 2.4 Hermes Gateway Cron/Ritual Activity (Today)

| Time (WIB) | Session ID | Event |
|---|---|---|
| 00:00 | cron_e10e8335c953_20260607_000033 | Midnight ritual — persona injected, session start |
| 00:02 | — | session_search error (around_message_id 0) |
| 00:03 | same | post_llm complete |
| 07:00 | cron_74ea29317ab4_20260607_070025 | Morning ritual — persona injected, session start |
| 07:14 | same | post_llm complete |
| 12:00 | cron_0ea6cb898af6_20260607_120003 | Midday ritual — session start, tools used |
| 12:01 | same | post_llm complete |
| 12:05 | — | Gateway restarted (SIGTERM → new PID 942968) |

Today's rituals ran successfully on the **PREVIOUS** gateway instance (PID 65081). The **current** gateway instance (PID 942968, started 12:05) has been running ~3 hours with no new cron activity logged (next scheduled: evening at 17:00 WIB, afternoon at 17:00? — actually config shows afternoon at 17:00, evening at 21:00).

### 2.5 Supporting Services

| Service | Status | Port | Notes |
|---|---|---|---|
| PostgreSQL | Online | 5433 | `pg_isready` confirms accepting connections |
| Redis | Online | 6380 | Responds but requires AUTH |
| Nin Router | Local proxy | 20128 | Required by Hermes gateway for LLM calls |

---

## 3. Discord Channel Configuration

From `hermes-config/config.yaml`:

| Parameter | Value |
|---|---|
| Allowed users | `1146639950654214264` (Faiz Discord ID) |
| Allowed channels | `1510914600777023659` (#guinevere-chat) |
| Require mention | `false` |
| Free response channels | `1510914600777023659` |
| History backfill | `true` |
| Approval webhook (env) | `DISCORD_APPROVAL_WEBHOOK` (SOPS-encrypted) |
| Shadow bot | Disabled (`SHADOW_ENABLED=false`) |

---

## 4. Blockers for T1/T2/T5 Discord-Channel Verification

### Critical Blockers

| # | Blocker | Impact |
|---|---|---|
| B1 | `guinevere-discord.service` is **masked** | Cannot be started with `systemctl start`; requires `systemctl unmask` first |
| B2 | Discord bot token is **SOPS-encrypted** | Cannot validate Discord API directly without decryption key |
| B3 | Hermes gateway Discord adapter connectivity **unconfirmed** | No "connected to Gateway" log visible; may not be receiving/sending Discord messages |
| B4 | Hermes gateway systemd unit **stale** | `TimeoutStopSec=90s` but `drain_timeout=180s` — systemd may SIGKILL during drain |
| B5 | MCP tool servers **misconfigured** | All MCP servers (fetch, filesystem, git, terminal, web) fail to connect — no `command` in config |

### Minor Observations

- Hermes gateway uses `ds/deepseek-v4-flash` model (not gpt-5.5) — 9Router token for GPT-5.5 was invalidated
- The gateway is ~3h uptime with no recent journal output — appears idle
- Voice features disabled (non-critical)
- Local Hermes CLI is 6673 commits behind upstream

---

## 5. Recommendations

1. **Unmask and restart** `guinevere-discord.service` for full T1/T2/T5 verification:
   ```bash
   ssh guinevere-vps "sudo systemctl unmask guinevere-discord.service && sudo systemctl start guinevere-discord.service"
   ```
2. If using Hermes gateway for Discord verification instead, **confirm connectivity** by monitoring journal after sending a test message:
   ```bash
   ssh guinevere-vps "journalctl -u hermes-gateway.service -f"
   ```
3. **Fix MCP server configuration** (add `command` fields for each MCP server) or these tools will remain unavailable to the agent.
4. **Regenerate systemd unit** for hermes-gateway to fix drain timeout mismatch:
   ```bash
   ssh guinevere-vps "sudo hermes gateway restart --system"
   ```
5. **Update local Hermes CLI** (6673 commits behind) if local testing is needed.

---

## 6. Evidence Sources

| Source | Command/Path |
|---|---|
| Process listing | `Get-Process`, `Get-CimInstance Win32_Process` |
| Service status (VPS) | `systemctl status guinevere-discord.service`, `systemctl status hermes-gateway.service` |
| Journal (standalone bot) | `journalctl -u guinevere-discord.service --no-pager -n 30` |
| Journal (Hermes gateway) | `journalctl -u hermes-gateway.service --since ... --no-pager` |
| Hermes gateway status | `hermes gateway status` (via SSH) |
| Local Hermes data | `ls -la ~/.hermes/logs/hooks/` |
| Database check | `pg_isready -h localhost -p 5433`, `redis-cli -p 6380 ping` |
| Config | `hermes-config/config.yaml`, `hermes-config/.env.template` |
| Source code | `src/discord/hermes_conversational.py` |

---

## 7. Footer

- **Authored:** 2026-06-07
- **Evidence root:** `research-reports/phase5-verification/`
- **Direct Discord API validation:** ❌ Not performed (SOPS-encrypted tokens, no decryption context available)
- **All status claims are directly observed** from process/service/journal evidence unless labeled as inferred
