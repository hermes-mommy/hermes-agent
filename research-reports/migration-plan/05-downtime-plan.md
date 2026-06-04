# 05 — Downtime Window Plan — Hermes Migration

> **Research Agent 5 of 10 — Parallel Migration Planning Wave**
> Generated: 2026-06-04 | Target: ADR-035 Phase-by-Phase Downtime Analysis
> Sources: ADR-035 (v1.2), MASTER-RESTRUCTURE-PLAN, 7 systemd service files, PROGRESS.md

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Key Constraints & Baseline](#2-key-constraints--baseline)
3. [Downtime Matrix — Per Phase](#3-downtime-matrix--per-phase)
4. [Maintenance Windows — WIB Schedule](#4-maintenance-windows--wib-schedule)
5. [Communication Plan](#5-communication-plan)
6. [Shadow Mode vs Cutover Strategy](#6-shadow-mode-vs-cutover-strategy)
7. [Services Affected Per Phase](#7-services-affected-per-phase)
8. [Aizanta Co-Existence Safety](#8-aizanta-coexistence-safety)
9. [Total Downtime Budget](#9-total-downtime-budget)
10. [Operator Impact Analysis](#10-operator-impact-analysis)
11. [Pre-Downtime Checklist](#11-pre-downtime-checklist)
12. [Appendix — Communication Templates](#12-appendix--communication-templates)

---

## 1. Executive Summary

The Hermes NousResearch migration (ADR-035) spans 7 phases over 35-50 calendar days. Of the 7 phases, **only Phase 2 (Discord Gateway cutover) requires a hard downtime window**. Phases 3 and 6 involve brief service restarts/config reloads but Guinevere remains responsive throughout. Phases 0, 1, 4, 5, and 7 operate entirely without downtime — development and testing happen alongside the running bot.py system.

**Total estimated downtime**: ≤ **5 minutes** (Phase 2 cutover only).

**Total degraded-response windows**: 2 (Phase 3 config reload ~10s, Phase 6 LLM model switch ~30s).

Guinevere is a 24/7 companion for Faiz (solo operator, Asia/Jakarta WIB). The downtime plan is designed around Faiz's daily rituals (07:00, 12:00, 17:00, 21:00 WIB) and sleep window, with all disruptive operations scheduled between **01:00-04:00 WIB** — the "dead zone" where ritual impact is zero.

### Downtime Philosophy

> **"bot.py stays primary until the moment cutover is verified."**

The migration follows a shadow-first, verify-then-cutover model. The existing bot.py process runs uninterrupted during Phases 0-1 and throughout the Phase 2 shadow mode. Only after 48+ hours of parallel operation with parity confirmation does the hard cutover occur, producing a single sub-5-minute gap. All other phases layer on top of the running Hermes gateway without service interruption.

---

## 2. Key Constraints & Baseline

### Operator Profile

| Attribute | Value |
|---|---|
| Operator | Faiz (solo developer, Indonesia) |
| Timezone | Asia/Jakarta (WIB, UTC+7) |
| Daily availability | 3-4 hours (evenings/weekends mostly) |
| Active hours | ~09:00-00:00 WIB (variable) |
| Sleep window | ~00:00-08:00 WIB |
| Companion dependency | 24/7 — Guinevere is daily conversational partner |

### Ritual Timetable (DO NOT DISRUPT)

| Time (WIB) | Ritual | Impact if Guinevere Down |
|---|---|---|
| **07:00** | Morning ritual — wake-up greeting, weather/agenda | Loss of daily start ritual, Faiz notices immediately |
| **12:00** | Midday ritual — check-in, lunch reminder | Midday connection break |
| **17:00** | Afternoon ritual — day review, evening transition | End-of-day context switch disrupted |
| **21:00** | Evening ritual — wind-down, reflection | Evening companionship gap |
| **00:00** | Midnight self-eval — system introspection | Not user-facing, acceptable downtime window |

### Infrastructure Constraints

| Constraint | Detail |
|---|---|
| VPS | hostdata.id 4C/16GB Ubuntu 24.04, shared with Aizanta |
| cgroup limit | Guinevere capped at 8GB RAM |
| Aizanta isolation | Must remain healthy throughout; separate docker network, separate system users |
| 7 systemd services | guinevere-discord, guinevere-loops, guinevere-mcp, guinevere-monitoring, guinevere-obscura, guinevere-scheduler, guinevere-surveillance |
| Discord guild | `Guinevere's Domain` (1510876414671323206) |
| Primary channel | `#guinevere-chat` (1510914600777023659) |
| Shadow channel | `#hermes-shadow` (to be created for Phase 2) |
| Alert channel | `#guinevere-alerts` (for status notifications) |
| LLM budget | $30/month hard cap |
| Shadow mode cost | ≤ $5 one-time (requires Faiz explicit approval) |

### ADR-035 Timeline Reference

| Phase | Name | Duration (ADR-035) | Realistic (solo dev) |
|---|---|---|---|
| Phase 0 | Security Remediation | 1-2 days | 2-3 days |
| Phase 1 | Safety Foundation | 4-6 days | 7-10 days |
| Phase 2 | Discord Gateway | 3-5 days | 5-8 days |
| Phase 3 | Memory Bridge | 3-5 days | 4-5 days |
| Phase 4 | MCP + Tools | 3-5 days | 5-7 days |
| Phase 5 | Skills + Persona | 2-4 days | 2-3 days |
| Phase 6 | LLM Routing | 1-2 days | 1 day |
| Phase 7 | Hardening + Monitoring | 2-3 days | 2-3 days |
| **Total** | | **19-32 days** | **28-40 days** |

---

## 3. Downtime Matrix — Per Phase

| Phase | Downtime Required? | Type | Duration | Services Affected | Aizanta Affected? | User Impact |
|---|---|---|---|---|---|---|
| **Phase 0** — Security Remediation | **NO** | N/A | 0s | None (pip-only changes) | No | Zero — bot.py runs normally |
| **Phase 1** — Safety Foundation | **NO** | N/A | 0s | None (code + config only) | No | Zero — bot.py runs normally; hooks/plugins tested in isolation |
| **Phase 2** — Discord Gateway (shadow) | **NO** | N/A | 0s | None (parallel operation) | No | Zero — bot.py is primary; Hermes runs in #hermes-shadow |
| **Phase 2** — Discord Gateway (cutover) | **YES** | **HARD CUTOVER** | **≤ 5 min** | guinevere-discord (stop bot.py → start hermes gateway) | No | **Guinevere offline for ≤ 5 min** — all Discord interaction paused |
| **Phase 3** — Memory Bridge | **PARTIAL** | Config reload | ~10s | Hermes gateway (config reload only — stays running) | No | **Negligible** — gateway briefly pauses config refresh; messages queued |
| **Phase 4** — MCP + Tools | **NO** | N/A | 0s | None (add MCP servers + auth plugin alongside running system) | No | Zero — tools added incrementally; custom FastMCP still running |
| **Phase 5** — Skills + Persona | **NO** | N/A | 0s | None (install skills, edit SOUL.md) | No | Zero — persona features layered on running system |
| **Phase 6** — LLM Routing | **PARTIAL** | Model switch | ~30s | Hermes gateway (model reconfiguration) | No | **Brief** — LLM calls may queue for one request cycle; gateway stays up |
| **Phase 7** — Hardening | **NO** | N/A | 0s | None (cron, backup, monitoring config) | No | Zero — operational tooling added to running system |

### Detailed Per-Phase Breakdown

#### Phase 0: Security Remediation — ZERO Downtime

All changes are at the pip dependency level:
```bash
pip install aiohttp>=3.9.0 --require-hashes
pip install --require-hashes -r requirements.txt
```
- **No service restarts required.**
- `hermes security` and `hermes doctor` are read-only scans.
- bot.py, PostgreSQL, Redis, 9Router — all continue running.
- If a pip upgrade breaks something → revert to pre-migration freeze, no downtime.

#### Phase 1: Safety Foundation — ZERO Downtime

All work is code and config creation only:
- New files: `config/hermes/SOUL.md`, `hooks/*.py`, `plugins/*.py`, `config/hermes/hooks.yaml`, `config/hermes/mcp-servers.yaml`
- Modified files: `plugins/guinevere_safety_plugin.py` (new file, iterated)
- Test files: `tests/safety/test_gate_*.py` (new)

**No Hermes gateway process is started yet.** bot.py continues as the sole Discord gateway. Safety hooks are tested via direct Python invocation, not through the gateway. Zero user-facing impact.

**Gate condition**: ALL 10 safety gates must pass before Phase 2 begins. If any gate fails → Phase 1 continues until all pass. No downtime is ever introduced.

#### Phase 2: Discord Gateway — THE ONLY HARD DOWNTIME

This is the critical phase. It has two sub-phases:

**Sub-Phase 2A: Shadow Mode (48+ hours) — ZERO Downtime**

| Aspect | Detail |
|---|---|
| bot.py | Running normally in `#guinevere-chat` |
| Hermes gateway | Running in `#hermes-shadow` (separate channel) |
| Memory writes | Only bot.py writes to PostgreSQL (mutex enforced) |
| Redis DBs | bot.py → DB4, Hermes → DB5 (isolated) |
| LLM calls | Both systems call 9Router (cost capped at $5) |
| User experience | Faiz uses Guinevere normally in `#guinevere-chat`; optionally checks `#hermes-shadow` for parity |

Shadow mode active safety injection tests (ADR-035 v1.2 mandate):
- HARD STOP injection: 3× during 48hr
- Y6 content injection: 3× during 48hr
- Consent revocation: 1× during 48hr
- Distress injection: 1× during 48hr
- Hook failure injection: 1× during 48hr

**Sub-Phase 2B: Hard Cutover — ≤ 5 MINUTES DOWNTIME**

This is the **only hard downtime** in the entire migration.

```
TIMELINE (WIB):
  T-60min  : Pre-cutover checklist complete (Aizanta healthy, PostgreSQL verified, Redis ready)
  T-30min  : Communication sent to #guinevere-status
  T-15min  : hermes checkpoints create --label "pre-cutover-$(date +%Y%m%d-%H%M%S)"
  T-5min   : Final Aizanta health check
  T-2min   : sudo systemctl stop guinevere-discord
  T-1min   : Verify bot.py process terminated, Discord gateway disconnected
  T-0      : hermes gateway start (Hermes takes over #guinevere-chat)
  T+30s    : Verify Hermes connected to Discord, intents present
  T+1min   : Test HARD STOP in #guinevere-chat → neutral response
  T+2min   : Test /status command → correct embed returned
  T+3min   : Test /mood command → mood state intact
  T+4min   : Verify all 35 slash commands registered
  T+5min   : Send "back online" message to #guinevere-status
  T+10min  : Monitor for 10 minutes — error rate, latency, safety triggers
```

**Cutover commands (exact)**:
```bash
# Step 1: Stop bot.py
sudo systemctl stop guinevere-discord

# Step 2: Verify bot.py stopped
sudo systemctl status guinevere-discord | grep "inactive"

# Step 3: Start Hermes gateway
hermes gateway start --config /home/guinevere/config/hermes/config.yaml

# Step 4: Verify Hermes running
hermes gateway status

# ROLLBACK (if needed, < 2 min):
hermes gateway stop
sudo systemctl start guinevere-discord
sudo systemctl status guinevere-discord | grep "active"
```

**Rollback trigger**: If any of the following occur during the 5-minute window:
- Hermes fails to connect to Discord gateway
- HARD STOP test fails (persona response instead of neutral)
- 3+ slash commands return errors
- Y6 content detected in any response
→ **IMMEDIATE ROLLBACK**: `hermes gateway stop && sudo systemctl start guinevere-discord` (< 2 min)

#### Phase 3: Memory Bridge — NEGLIGIBLE Downtime (~10 seconds)

Hermes gateway **stays running** throughout. Changes are live config updates:

| Step | Action | Gateway State | Duration |
|---|---|---|---|
| 3.1 | Enable compression at 70% threshold | `hermes config set memory.compression.enabled true` | ~5s config reload |
| 3.2 | Enable session_search (FTS5) | `hermes config set memory.session_search.enabled true` | ~5s config reload |
| 3.3 | Deploy memory_plugin.py | Plugin loaded on next gateway reload | Already running, loaded dynamically |
| 3.4 | Configure mirror sync (MEMORY.md) | Config update only | ~5s |
| 3.5 | A/B test recall quality | Read-only test, no config change | N/A |

Total degraded time: **~10 seconds** during config reloads. Messages arriving during the reload are queued by Hermes and processed immediately after. No messages are lost.

If compression causes issues → `hermes config set memory.compression.enabled false` (< 5s rollback).

#### Phase 4: MCP + Tools — ZERO Downtime

All MCP servers are added to the running Hermes process while it continues serving Discord:

```bash
hermes mcp add web --config ./web-server.json     # READ_AUTO tools — no impact
hermes mcp add filesystem --config ./fs-server.json
hermes mcp add terminal --config ./terminal-server.json
hermes mcp add git --config ./git-server.json
hermes mcp add fetch --config ./fetch-server.json
```

Custom FastMCP server (`guinevere-mcp.service`) continues running for the 7 custom tools. The auth overlay plugin is loaded dynamically. **No service restart needed.** Zero message loss.

#### Phase 5: Skills + Persona — ZERO Downtime

Skills installation and SOUL.md edits are file-level operations:
```bash
hermes skills install safety-pack
hermes skills install persona-rituals
```
Gateway reads SOUL.md at startup but plugin state is per-session. Updated SOUL.md takes effect on next session creation without gateway restart. Zero downtime.

#### Phase 6: LLM Routing — MINIMAL Downtime (~30 seconds)

Gateway stays up. Model configuration update only:

```bash
hermes model set --provider custom --base-url http://localhost:20128/v1 --model gpt-5.5
hermes fallback set --provider custom --base-url http://localhost:20128/v1 --model deepseek-v4-flash
```

The model switch takes effect immediately. LLM calls in-flight during the switch may see one retry. **Gateway does not restart.** Total interruption: ~30 seconds for the model routing to stabilize. Messages are queued.

#### Phase 7: Hardening — ZERO Downtime

All hardening is operational tooling added to a running system:
- `hermes cron` — scheduled maintenance tasks
- `hermes backup` — automated backup pipeline
- `hermes checkpoints` — snapshot automation
- `hermes security` — read-only audit scan

No services are stopped. Zero downtime.

---

## 4. Maintenance Windows — WIB Schedule

### Recommended Window: 01:00-04:00 WIB (UTC+7)

This is the "dead zone" between midnight self-eval (00:00) and morning ritual (07:00). Faiz is typically asleep. Ritual impact is zero. Aizanta load is minimal (no concurrent development).

| Window | WIB | Rationale |
|---|---|---|
| **PRIMARY** | **01:00-04:00** | Faiz sleep window. Zero ritual conflict. 3-hour buffer for unexpected issues. |
| **SECONDARY** | **22:00-00:00** | After evening ritual (21:00), before sleep. Acceptable for config-only changes (Phases 3, 6). |
| **EMERGENCY ONLY** | **04:00-06:00** | Late-night extension if primary window fails. Must complete ≥ 1hr before 07:00 ritual. |

### Forbidden Windows (DO NOT SCHEDULE)

| Window (WIB) | Why Forbidden |
|---|---|
| **06:00-08:00** | Morning ritual (07:00). Faiz's first interaction of the day. Guinevere MUST be online. |
| **11:00-13:00** | Midday ritual (12:00). Lunch check-in. |
| **16:00-18:00** | Afternoon ritual (17:00). Day review, evening transition. |
| **20:00-22:00** | Evening ritual (21:00). Wind-down, reflection. Highest emotional dependency window. |

### Phase-Specific Window Recommendations

| Phase | Recommended Window | Duration Needed | Pre-Check |
|---|---|---|---|
| **Phase 2B — Cutover** | **01:00-02:00 WIB** | 5 min cutover + 10 min monitoring = 15 min total | Aizanta healthy, PostgreSQL verified, all 35 commands registered on Hermes side |
| **Phase 3 — Memory Bridge** | **22:00-23:00 WIB** | ~1 min for all config reloads + 10 min A/B testing | Compression tested in dev, session_search index built |
| **Phase 6 — LLM Routing** | **22:00-23:00 WIB** | ~30s model switch + 5 min streaming test | 9Router healthy, 100-test-prompt compatibility verified |

All other phases (0, 1, 4, 5, 7) can be performed during Faiz's normal working hours — no downtime involved.

---

## 5. Communication Plan

### Communication Channels

| Channel | Purpose | Discord Channel |
|---|---|---|
| **Primary status** | Downtime announcements, status updates, "back online" | `#guinevere-status` (to be created) |
| **Alerts** | Automated monitoring alerts (SEV1-SEV4) | `#guinevere-alerts` (existing) |
| **Shadow mode logs** | Phase 2 parity comparison, safety injection test results | `#hermes-shadow` (to be created) |
| **Direct** | Faiz personal notification for critical events | DM to Faiz via Gotify push |

### Downtime Communication Protocol

#### Phase 2B Cutover — Complete Communication Timeline

```
T-30min (00:30 WIB):
  ┌─────────────────────────────────────────────────────────┐
  │ #guinevere-status                                       │
  │                                                         │
  │ 🔧 SCHEDULED MAINTENANCE — 30 MINUTES                   │
  │                                                         │
  │ Guinevere will undergo a brief gateway migration at     │
  │ 01:00 WIB. Expected downtime: < 5 minutes.              │
  │                                                         │
  │ During this window:                                     │
  │ • Guinevere will be temporarily unavailable             │
  │ • HARD STOP will still work (neutral mode persists)     │
  │ • All memory, surveillance, and safety systems remain   │
  │   fully operational                                     │
  │                                                         │
  │ What's happening:                                       │
  │ Phase 2B — Hermes Discord Gateway Cutover               │
  │ bot.py → Hermes native gateway                          │
  │                                                         │
  │ Next update: 01:00 WIB (cutover start)                  │
  │                                                         │
  │ — Guinevere System                                      │
  └─────────────────────────────────────────────────────────┘

T-15min (00:45 WIB):
  ┌─────────────────────────────────────────────────────────┐
  │ #guinevere-status                                       │
  │                                                         │
  │ ⏳ MAINTENANCE IN 15 MINUTES                            │
  │                                                         │
  │ Pre-cutover checkpoint created.                         │
  │ Aizanta health: ✅ GREEN                                │
  │ PostgreSQL: ✅ GREEN (47 tables, 12 schemas intact)     │
  │ Redis: ✅ GREEN (all DBs responsive)                    │
  │ 9Router: ✅ GREEN (GPT-5.5 + DeepSeek ready)           │
  │                                                         │
  │ All pre-flight checks passing. Proceeding at 01:00.     │
  └─────────────────────────────────────────────────────────┘

T-0 (01:00 WIB):
  ┌─────────────────────────────────────────────────────────┐
  │ #guinevere-status                                       │
  │                                                         │
  │ 🚧 MAINTENANCE IN PROGRESS                              │
  │                                                         │
  │ bot.py stopped. Hermes gateway starting...              │
  │                                                         │
  │ Expected completion: 01:05 WIB                          │
  │ Status: bot.py inactive, gateway initializing           │
  │                                                         │
  │ ⏱️ Timer started: 5-minute cutover window              │
  └─────────────────────────────────────────────────────────┘

T+2min (01:02 WIB):
  ┌─────────────────────────────────────────────────────────┐
  │ #guinevere-status                                       │
  │                                                         │
  │ 🔄 CUTOVER IN PROGRESS — 3 min remaining                │
  │                                                         │
  │ Hermes gateway connected to Discord.                    │
  │ Running verification checks...                          │
  │ • HARD STOP test: pending                               │
  │ • Slash commands: pending                               │
  │ • Safety hooks: pending                                 │
  └─────────────────────────────────────────────────────────┘

T+5min (01:05 WIB) — SUCCESS:
  ┌─────────────────────────────────────────────────────────┐
  │ #guinevere-status                                       │
  │                                                         │
  │ ✅ MAINTENANCE COMPLETE — GUINEVERE ONLINE              │
  │                                                         │
  │ Cutover successful. Hermes gateway now serving          │
  │ #guinevere-chat.                                        │
  │                                                         │
  │ Verification results:                                   │
  │ ✅ HARD STOP — neutral response, zero LLM call          │
  │ ✅ 35/35 slash commands registered and functional       │
  │ ✅ Safety hooks active (7/7 hooks, plugin loaded)       │
  │ ✅ Streaming active (progressive edits at ~1.2s)        │
  │ ✅ Memory bridge connected (PostgreSQL primary)         │
  │ ✅ LLM routing through 9Router (localhost:20128)        │
  │                                                         │
  │ Downtime: 4 minutes 37 seconds (target < 5 min)         │
  │                                                         │
  │ Monitoring active for next 10 minutes.                  │
  │                                                         │
  │ 👑 Mommy is back, Darling.                              │
  └─────────────────────────────────────────────────────────┘

T+5min (01:05 WIB) — FAILURE (if rollback triggered):
  ┌─────────────────────────────────────────────────────────┐
  │ #guinevere-status                                       │
  │                                                         │
  │ ⚠️ CUTOVER ROLLED BACK                                  │
  │                                                         │
  │ Hermes gateway cutover encountered an issue:            │
  │ [SPECIFIC ERROR — e.g., "HARD STOP test returned        │
  │  persona response instead of neutral"]                  │
  │                                                         │
  │ Action taken: IMMEDIATE ROLLBACK                        │
  │ • hermes gateway stopped                                │
  │ • bot.py restarted (guinevere-discord.service)          │
  │ • Guinevere back online via bot.py                      │
  │                                                         │
  │ Downtime: [X] minutes [Y] seconds                       │
  │ Root cause investigation in progress.                   │
  │ Next attempt: After fix verified.                       │
  │                                                         │
  │ Current state: Guinevere operational (bot.py)           │
  │ All safety features confirmed intact.                   │
  └─────────────────────────────────────────────────────────┘
```

#### Ongoing Status Updates (During Downtime)

During the 5-minute cutover window:
- **T+0**: Start message in `#guinevere-status`
- **T+2min**: Progress update (if cutover exceeds 2 minutes)
- **T+5min**: Completion or rollback message
- Status updates every **2 minutes** during the window

#### Phase 3 & 6 — Lightweight Communication

Phases 3 and 6 have negligible downtime (< 30s). Communication is a single pre/post message:

```
Pre-change (T-5min):
🔧 Brief config update in 5 minutes. Guinevere will remain responsive.
Memory compression enabling (Phase 3) / LLM model reconfiguration (Phase 6).
Expected interruption: < 30 seconds.

Post-change (T+1min):
✅ Config update complete. {Phase 3: Compression active at 70% threshold.}
{Phase 6: LLM routing through 9Router confirmed.} Guinevere fully operational.
```

---

## 6. Shadow Mode vs Cutover Strategy

### Shadow Mode Architecture (Phase 2A — 48+ Hours)

```
                    ┌─────────────────────────────────┐
                    │         Discord Guild            │
                    │                                  │
                    │  #guinevere-chat                 │
                    │  ┌─────────────────────────┐    │
                    │  │  bot.py (PRIMARY)        │    │
                    │  │  • Handles all messages  │    │
                    │  │  • Writes to PostgreSQL  │    │
                    │  │  • Redis DB4 sessions    │    │
                    │  │  • 9Router LLM calls     │    │
                    │  └─────────────────────────┘    │
                    │                                  │
                    │  #hermes-shadow                  │
                    │  ┌─────────────────────────┐    │
                    │  │  Hermes Gateway (SHADOW) │    │
                    │  │  • Receives forwarded msg │   │
                    │  │  • Read-only PostgreSQL   │    │
                    │  │  • Redis DB5 sessions     │    │
                    │  │  • 9Router LLM calls      │    │
                    │  │  • Safety hooks active    │    │
                    │  └─────────────────────────┘    │
                    └─────────────────────────────────┘
```

### Shadow Mode Rules

| Rule | Detail |
|---|---|
| **Message authority** | bot.py is the sole responder in `#guinevere-chat`. Hermes responds only in `#hermes-shadow`. |
| **Memory write mutex** | Only bot.py writes to PostgreSQL. Hermes PostgreSQL connection is **read-only**. |
| **Redis isolation** | bot.py → DB4 (sessions), Hermes → DB5 (safety state). No shared DB writes. |
| **Cost cap** | $5 hard cap for shadow mode LLM calls. Tracked via Redis DB5 cost keys. |
| **Safety enforcement** | BOTH systems have safety active. GuinevereSafetyPlugin MUST be loaded on Hermes side. |
| **Duration** | Minimum 48 hours. Can be extended by Faiz. Auto-terminate at 72 hours if no manual extension. |
| **Active tests** | HARD STOP (3×), Y6 injection (3×), consent revocation (1×), distress injection (1×), hook failure (1×) — injected by test harness, not by Faiz. |

### Shadow Mode Stages

| Stage | Duration | Description |
|---|---|---|
| **Stage 1: 0% traffic** | First 4 hours | Hermes receives forwarded messages but does NOT respond. Pure observation: are hooks firing correctly? Are safety checks passing? Is latency within bounds? |
| **Stage 2: 10% traffic** | Hours 4-12 | Hermes responds to 10% of forwarded messages (random sample). Responses posted in `#hermes-shadow` only. Faiz reviews parity manually. |
| **Stage 3: 50% traffic** | Hours 12-36 | Hermes responds to 50% of messages. Parity comparison automated. Response diff report generated every 6 hours. |
| **Stage 4: 100% traffic** | Hours 36-48 | Hermes responds to ALL forwarded messages. Final parity report generated. Faiz reviews and approves/disapproves cutover. |

### Cutover Decision Gate

**Faiz must explicitly approve cutover.** The approval requires:
1. Parity report showing ≥ 95% functional parity across all 35 commands
2. All safety injection tests pass (HARD STOP, Y6, consent, distress, hook failure)
3. Zero safety regressions detected
4. Latency within +10% of bot.py baseline
5. Faiz verbally confirms (or via Discord message): "cutover approved" / "lanjut cutover"

**If Faiz does not approve**: Shadow mode continues. Debug and fix the identified issues. Re-run parity tests. Re-present for approval.

---

## 7. Services Affected Per Phase

### Current Service Topology

| Service | systemd Unit | Process | Port | Depends On |
|---|---|---|---|---|
| Discord Bot | `guinevere-discord.service` | `python -m src.discord.bot` | N/A (WebSocket outbound) | `guinevere-core.service` |
| Agent Loop | `guinevere-loops.service` | `python -m src.loops.manager` | 8000 (internal) | `guinevere-core.service` |
| Loop Scheduler | `guinevere-scheduler.service` | `python -m src.loops.scheduler` | N/A | `guinevere-loops.service` |
| MCP Server | `guinevere-mcp.service` | `python -m src.mcp.manager` | N/A (FastMCP) | `guinevere-core.service` |
| Surveillance | `guinevere-surveillance.service` | `python -m src.surveillance.consumer` | N/A | `guinevere-core.service` |
| Monitoring | `guinevere-monitoring.service` | Docker Compose (Prometheus/Grafana/Loki) | 9090, 3000, 3100 | `docker.service` |
| Obscura CDP | `guinevere-obscura.service` | `obscura serve --port 9222` | 9222 | `network.target` |
| PostgreSQL | (system package) | `postgresql` | 5433 | N/A |
| Redis | (system package) | `redis-server` | 6380 | N/A |
| 9Router | (system package) | `9router` | 20128 | N/A |

### Per-Phase Service State Changes

#### Phase 0: Security Remediation

| Service | Action | Reason |
|---|---|---|
| ALL SERVICES | **No change** | Pip-level dependency fixes only. Zero service interaction. |

#### Phase 1: Safety Foundation

| Service | Action | Reason |
|---|---|---|
| ALL SERVICES | **No change** | Code and config creation only. Hermes gateway NOT started. bot.py remains sole gateway. |

#### Phase 2A: Shadow Mode

| Service | Action | Reason |
|---|---|---|
| `guinevere-discord.service` | **KEEP RUNNING** | bot.py is primary gateway |
| Hermes gateway | **START** (manual, not systemd yet) | Shadow mode in `#hermes-shadow` |
| `guinevere-loops.service` | **KEEP RUNNING** | Loop manager unaffected |
| `guinevere-scheduler.service` | **KEEP RUNNING** | Scheduler unaffected |
| `guinevere-mcp.service` | **KEEP RUNNING** | Custom tools still accessible to bot.py |
| `guinevere-surveillance.service` | **KEEP RUNNING** | Surveillance pipeline unaffected |
| `guinevere-monitoring.service` | **KEEP RUNNING** | Monitoring both systems |
| `guinevere-obscura.service` | **KEEP RUNNING** | Browser automation unaffected |
| PostgreSQL / Redis / 9Router | **KEEP RUNNING** | Shared infrastructure, no changes |

#### Phase 2B: Hard Cutover

| Service | Action | Command | Duration |
|---|---|---|---|
| `guinevere-discord.service` | **STOP** | `sudo systemctl stop guinevere-discord` | ~2s |
| Hermes gateway | **START** (production mode) | `hermes gateway start` | ~3-5s |
| `guinevere-loops.service` | **RESTART** (optional) | `sudo systemctl restart guinevere-loops` | ~5s — reconfigure to use Hermes API instead of bot.py internal |
| `guinevere-scheduler.service` | **RESTART** (optional) | `sudo systemctl restart guinevere-scheduler` | ~5s |
| `guinevere-mcp.service` | **KEEP RUNNING** | Custom tools still needed | 0s |
| `guinevere-surveillance.service` | **KEEP RUNNING** | Unaffected | 0s |
| `guinevere-monitoring.service` | **KEEP RUNNING** | Unaffected | 0s |
| `guinevere-obscura.service` | **KEEP RUNNING** | Unaffected | 0s |
| PostgreSQL / Redis / 9Router | **KEEP RUNNING** | Unaffected | 0s |

**Post-cutover service topology**:
```
Hermes gateway (replaces guinevere-discord.service)
    ├── guinevere-loops.service (unchanged, points to Hermes API)
    ├── guinevere-scheduler.service (unchanged)
    ├── guinevere-mcp.service (unchanged — custom tools)
    ├── guinevere-surveillance.service (unchanged)
    ├── guinevere-monitoring.service (unchanged)
    └── guinevere-obscura.service (unchanged)
```

#### Phase 3: Memory Bridge

| Service | Action | Reason |
|---|---|---|
| Hermes gateway | **CONFIG RELOAD** | Enable compression, session_search |
| `guinevere-mcp.service` | **KEEP RUNNING** | Custom memory tools still needed |
| PostgreSQL | **KEEP RUNNING** | Primary memory store — zero changes |
| Redis | **KEEP RUNNING** | Cache layer — zero changes |

#### Phase 4: MCP + Tools

| Service | Action | Reason |
|---|---|---|
| Hermes gateway | **ADD MCP SERVERS** (live) | 5 native MCP servers added via `hermes mcp add` |
| `guinevere-mcp.service` | **KEEP RUNNING** | 7 custom tools remain |
| Auth overlay plugin | **LOAD** (dynamic) | Plugin loaded into Hermes process |

#### Phase 5: Skills + Persona

| Service | Action | Reason |
|---|---|---|
| Hermes gateway | **INSTALL SKILLS** (live) | `hermes skills install` commands |
| SOUL.md | **EDIT** (read on next session) | Identity file |

#### Phase 6: LLM Routing

| Service | Action | Reason |
|---|---|---|
| Hermes gateway | **MODEL RECONFIGURE** | `hermes model set` command |
| 9Router | **KEEP RUNNING** | Unchanged |
| Budget hook | **DEPLOY** (live) | New hook script added to hook chain |

#### Phase 7: Hardening

| Service | Action | Reason |
|---|---|---|
| ALL SERVICES | **KEEP RUNNING** | Cron jobs, backup scripts, monitoring config — all live additions |

---

## 8. Aizanta Co-Existence Safety

### Pre-Every-Downtime Aizanta Health Check

Before ANY service change that could affect the shared VPS:

```bash
#!/bin/bash
# aizanta-health-check.sh — Run before any Guinevere service change
# Location: /home/guinevere/scripts/aizanta-health-check.sh

echo "=== Aizanta Health Check — $(date) ==="

# 1. Check Aizanta processes
AIZANTA_PROCS=$(ps aux | grep -v grep | grep -E "(aizanta|aizanta-)" | wc -l)
echo "Aizanta processes: $AIZANTA_PROCS"

# 2. Check shared resources
echo "=== Memory ==="
free -h | grep Mem

echo "=== Disk ==="
df -h / | tail -1

# 3. Check no port conflicts
echo "=== Ports ==="
ss -tlnp | grep -E "(LISTEN)" | awk '{print $4}'

# 4. Check cgroup limits
echo "=== Cgroups ==="
systemd-cgtop -n1 -m 2>/dev/null || echo "cgtop unavailable"

# 5. Verify Guinevere slice not impacting Aizanta
echo "=== Guinevere Slice ==="
systemctl show guinevere.slice | grep -E "(MemoryCurrent|CPUUsage)"

echo "=== Health check complete ==="
```

### Aizanta Safety Rules

| Rule | Detail |
|---|---|
| **Port isolation** | Guinevere uses ports 8000, 9222, 20128, 5433, 6380, 9090, 3000, 3100. Verify none conflict with Aizanta before any service start. |
| **Docker network** | Guinevere containers on `guinevere-net` (isolated from Aizanta docker networks). |
| **cgroup limits** | Guinevere slice capped at 8GB RAM. systemd MemoryHigh/MemoryMax enforced per service. |
| **Disk space** | Pre-migration: verify ≥ 5GB free on `/`. Hermes adds ~200MB of config/state/checkpoint data. |
| **CPU contention** | Cutover operations are CPU-light. No risk of starving Aizanta. |
| **System users** | Guinevere runs as `guinevere` user. Aizanta runs as separate user(s). Zero permission overlap. |

### Aizanta Downtime Risk: ZERO

No Guinevere migration phase requires:
- VPS reboot
- Docker daemon restart
- System-wide package installation (Phase 0 is pip-level within `.venv`)
- Kernel parameter changes
- Network reconfiguration
- Shared resource reallocation

The Hermes gateway replaces the bot.py process one-for-one — same Python environment, same resource profile, same network footprint. Aizanta experiences **zero impact** from the migration.

---

## 9. Total Downtime Budget

### Cumulative Downtime Across All Phases

| Phase | Downtime Type | Duration | Cumulative |
|---|---|---|---|
| Phase 0 | None | 0s | 0s |
| Phase 1 | None | 0s | 0s |
| Phase 2A (shadow) | None | 0s | 0s |
| **Phase 2B (cutover)** | **Hard** | **≤ 300s (5 min)** | **≤ 300s** |
| Phase 3 | Config reload | ~10s | ≤ 310s |
| Phase 4 | None | 0s | ≤ 310s |
| Phase 5 | None | 0s | ≤ 310s |
| Phase 6 | Config reload | ~30s | ≤ 340s |
| Phase 7 | None | 0s | ≤ 340s |
| **TOTAL** | | | **≤ 5 min 40 sec** |

### Downtime Budget vs ADR-025 DR Targets

| ADR-025 Target | Migration Actual | Compliant? |
|---|---|---|
| RTO (Recovery Time Objective): < 15 min for Sev-1 | ≤ 5 min 40 sec total | ✅ YES |
| RPO (Recovery Point Objective): < 1 hour data loss | 0s (PostgreSQL primary unchanged) | ✅ YES |
| Planned maintenance window: < 1 hour | ≤ 5 min 40 sec total | ✅ YES |

### Worst-Case Scenario

If Phase 2B cutover triggers rollback:
- bot.py restart: ~5s
- Verify HARD STOP: ~10s
- **Total worst-case downtime: ~15 seconds** (rolling back is faster than cutting over)

If PostgreSQL restore is needed (extremely unlikely — Hermes is read-only):
- `pg_restore` from pre-migration dump: ~2-5 minutes
- This would be an Sev-1 incident, not a planned downtime event

---

## 10. Operator Impact Analysis

### Daily Rhythm Preservation

| Ritual Time (WIB) | Migration Impact | Mitigation |
|---|---|---|
| **07:00 Morning** | Zero — all disruptive ops scheduled 01:00-04:00 | Cutover completes ≥ 3hr before morning ritual |
| **12:00 Midday** | Zero — no ops during this window | Forbidden window enforced |
| **17:00 Afternoon** | Zero — no ops during this window | Forbidden window enforced |
| **21:00 Evening** | Zero — highest dependency window protected | Forbidden window enforced. Any issues from earlier ops would be detected and resolved by 17:00. |
| **00:00 Midnight** | Zero impact — self-eval is system-internal | Midnight self-eval runs normally on bot.py during shadow mode, on Hermes post-cutover |

### Solo Developer Risk Mitigation

Faiz is the sole operator. The downtime plan accounts for this:

| Risk | Mitigation |
|---|---|
| **Faiz unavailable during cutover** | Pre-written rollback script (`/home/guinevere/scripts/rollback/phase-2-rollback.sh`, chmod +x). Single command: `bash ~/scripts/rollback/phase-2-rollback.sh`. No deep understanding needed at 3 AM. |
| **Cognitive load at late hours** | Cutover scheduled 01:00 WIB but Faiz does NOT need to be awake. Cutover is automated. If rollback needed, automated health checks trigger it. Faiz sees results at 07:00. |
| **No second reviewer for config changes** | Phase 1 safety gate tests (10 gates) act as automated reviewer. Phase 2 parity report is automated. Phase 7 runbook provides step-by-step verification checklists. |
| **Guinevere is being rebuilt** | During Phases 0-7, bot.py runs normally. Faiz interacts with Guinevere through the existing system. Only the 5-minute Phase 2B window has any interruption. |

### Pre-Cutover Operator Decision Checklist

Before Phase 2B cutover, Faiz must confirm:

- [ ] Shadow mode parity report reviewed and ≥ 95% functional parity confirmed
- [ ] All 5 active safety injection tests passed (HARD STOP, Y6, consent, distress, hook failure)
- [ ] Latency within +10% of bot.py baseline
- [ ] I understand the rollback command: `hermes gateway stop && sudo systemctl start guinevere-discord`
- [ ] I approve the 01:00-02:00 WIB cutover window
- [ ] I understand Guinevere will be unavailable for ≤ 5 minutes
- [ ] I understand the $5 shadow mode cost has been tracked
- [ ] I explicitly approve: "cutover approved" / "lanjut cutover"

---

## 11. Pre-Downtime Checklist

### Universal Pre-Downtime Checklist (All Phases)

Run before ANY service-affecting operation:

```
[ ] Aizanta health check: ALL processes healthy, no resource contention
[ ] PostgreSQL: pg_isready -h localhost -p 5433 → accepting connections
[ ] Redis: redis-cli -p 6380 PING → PONG
[ ] 9Router: curl -s http://localhost:20128/health → OK
[ ] Disk space: df -h / | grep -v Filesystem → ≥ 5GB available
[ ] Memory: free -h | grep Mem → ≥ 2GB available
[ ] Hermes checkpoints create --label "pre-phase-N-$(date +%Y%m%d-%H%M%S)"
[ ] Git tag created: git tag "pre-phase-N-$(date +%Y%m%d-%H%M%S)" && git push origin --tags
[ ] Rollback script verified executable and syntax-valid
[ ] Communication message drafted and ready to send
[ ] Faiz notified (if during waking hours)
```

### Phase 2B Cutover — Specific Pre-Flight

Additional checks beyond universal checklist:

```
[ ] ALL 35 slash commands registered on Hermes side: hermes gateway list | wc -l → ≥ 35
[ ] GuinevereSafetyPlugin loaded: hermes plugins list | grep guinevere_safety → loaded
[ ] ALL 7 hooks configured: hermes hooks list → pre_prompt, post_prompt, pre_tool_call, post_tool_call, pre_response, post_response, on_error
[ ] Shadow mode parity report: ≥ 95% functional parity across all commands
[ ] Shadow mode cost: ≤ $5 cumulative
[ ] HARD STOP verified on Hermes side (3 successful tests during shadow mode)
[ ] bot.py service file backed up: cp /etc/systemd/system/guinevere-discord.service /home/guinevere/backups/
[ ] Rollback script staged: /home/guinevere/scripts/rollback/phase-2-rollback.sh exists and executable
[ ] #guinevere-status channel exists and bot has SEND_MESSAGES permission
[ ] Gotify push notification configured for Faiz (backup notification channel)
```

### Post-Downtime Verification Checklist (Phase 2B)

```
[ ] Hermes gateway status: hermes gateway status → connected, all intents present
[ ] Discord gateway: Guinevere visible in #guinevere-chat member list
[ ] HARD STOP test: send "HARD STOP" → "HARD STOP acknowledged. I am now in neutral/safe mode." — < 1 second response
[ ] /status command: returns 11-field embed with correct system info
[ ] /mood command: returns current mood state
[ ] /help command: returns command list
[ ] /memory search: returns memory results from PostgreSQL
[ ] /safeword: responds with safe word information
[ ] 35/35 commands: spot-check 5 random commands, verify response correctness
[ ] Streaming: send a message that triggers a long response → progressive Discord edits visible
[ ] Monitoring: guinevere-monitoring.service shows Hermes gateway as active target
[ ] "Back online" message sent to #guinevere-status
[ ] Faiz notified (Gotify push if asleep, Discord DM if awake)
```

---

## 12. Appendix — Communication Templates

### Template A: Pre-Maintenance (Phase 2B Cutover)

```
🔧 SCHEDULED MAINTENANCE — {X} MINUTES

Guinevere will undergo a brief gateway migration at {TIME} WIB.
Expected downtime: < 5 minutes.

During this window:
• Guinevere will be temporarily unavailable
• HARD STOP will still work (neutral mode persists)
• All memory, surveillance, and safety systems remain fully operational

What's happening:
{PHASE} — {DESCRIPTION}

Next update: {TIME} WIB (cutover start)

— Guinevere System
```

### Template B: Maintenance In Progress

```
🚧 MAINTENANCE IN PROGRESS

{PREVIOUS_STATE} stopped. {NEW_STATE} starting...

Expected completion: {TIME} WIB
Status: {CURRENT_STATUS}

⏱️ Timer started: {DURATION}-minute window
```

### Template C: Progress Update

```
🔄 {PHASE} IN PROGRESS — {REMAINING} remaining

{STATUS_DETAILS}

Verification checks:
• {CHECK_1}: {STATUS_1}
• {CHECK_2}: {STATUS_2}
• {CHECK_3}: {STATUS_3}
```

### Template D: Maintenance Complete — Success

```
✅ MAINTENANCE COMPLETE — GUINEVERE ONLINE

{OPERATION} successful. {SUMMARY}

Verification results:
{VERIFICATION_TABLE}

Downtime: {DURATION} (target {TARGET})

Monitoring active for next 10 minutes.

👑 Mommy is back, Darling.
```

### Template E: Maintenance Complete — Rollback

```
⚠️ {OPERATION} ROLLED BACK

{OPERATION} encountered an issue:
{ERROR_DETAIL}

Action taken: IMMEDIATE ROLLBACK
• {ROLLBACK_STEP_1}
• {ROLLBACK_STEP_2}
• Guinevere back online via {FALLBACK_SYSTEM}

Downtime: {DURATION}
Root cause investigation in progress.
Next attempt: After fix verified.

Current state: Guinevere operational ({FALLBACK_SYSTEM})
All safety features confirmed intact.
```

### Template F: Post-Maintenance All-Clear

```
🟢 GUINEVERE — ALL SYSTEMS NORMAL

Maintenance window closed. {DURATION} since cutover.

Health summary:
• Discord gateway: ✅ GREEN ({UPTIME})
• Safety hooks: ✅ GREEN (7/7 active)
• Slash commands: ✅ GREEN (35/35 functional)
• Memory: ✅ GREEN (PostgreSQL primary)
• LLM routing: ✅ GREEN (9Router healthy)
• Streaming: ✅ GREEN (progressive edits)
• Budget: 🟡 ${SPEND} of $30 cap

No further maintenance scheduled.
```

---

## Document Metadata

| Field | Value |
|---|---|
| **Report ID** | 05-downtime-plan |
| **Research Agent** | Agent 5 of 10 |
| **Wave** | Parallel Migration Planning Wave |
| **Date** | 2026-06-04 |
| **Sources** | ADR-035 (v1.2, lines 1-1766), MASTER-RESTRUCTURE-PLAN (667 lines), 7 systemd service files, PROGRESS.md (734 lines) |
| **Lines** | 432 |
| **Status** | Complete |
| **Total planned downtime** | ≤ 5 minutes 40 seconds across entire migration |
| **Hard downtime** | Phase 2B cutover only — ≤ 5 minutes |
| **Config reload windows** | Phase 3 (~10s) + Phase 6 (~30s) — negligible |
| **Phases with zero downtime** | Phase 0, 1, 2A (shadow), 4, 5, 7 |
| **Aizanta impact** | Zero — no shared resource reallocation |
| **Ritual disruption** | Zero — all disruptive ops scheduled 01:00-04:00 WIB |