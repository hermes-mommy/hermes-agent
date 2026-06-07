# Guinevere Implementation Guide

> User manual for the Guinevere implementation system — 202 steps (MVP) + 34 steps (Stabilization) + 122 steps (Expansion, P11-P15) across 23 phases (P0-P22), $35-44/month budget, shared VPS constraints. P16-P22: TBD.

**Audience**: Faiz (operator) and AI agents (Guinevere, sub-agents)
**Last updated**: 2026-06-07
**Companion files**: `PROGRESS.md`, `stepprompts/StepPrompts.md`, `CHECKLIST.md`

---

## 1. Introduction

Guinevere deploys on a shared VPS (hostdata.id, 4C/16GB, Ubuntu 24.04). The implementation system breaks deployment into **23 phases (P0-P22)** with **202 MVP steps (P0-P8), 34 Stabilization steps (P9-P10), and 122 Expansion steps (P11-P15) with P16-P22 TBD**, each with exact commands, verification, rollback, and cost impact.

**ADR-035 closure note (2026-06-07):** The Hybrid Hermes Migration architecture is implemented. Operational caveat B10 remains accepted risk until offline age-key recovery and `secrets/backup/` restoration re-enable encrypted S3/R2 restore; B11 uses the verified sentinel path `/home/guinevere/.backup/last-success`; B12 is resolved by exported metrics `hermes_safety_blocks_total`, `hermes_session_count`, and `hermes_message_count_total`, while `hermes_gateway_up` remains intentionally omitted.

### How to Use This System

```
1. Read PROGRESS.md       → see where you are
2. Open StepPrompts.md    → find the next step
3. Execute the step       → follow the stepprompt workflow
4. Verify with CHECKLIST  → confirm all items pass
5. Update PROGRESS.md     → record results, cost, blockers
6. Commit to git          → preserve state
7. Repeat
```

With AI agent: say `"lanjut"` — Guinevere reads state, finds next step, executes, verifies, updates, reports.

### Phase Overview

### MVP Phases (P0-P8)

| Phase | Name | Steps | Cost/mo | Depends On |
|-------|------|-------|---------|-----------|
| P0 | Infrastructure | 29 | $0 | — |
| P1 | LLM + Hermes | 20 | $15 | P0 |
| P2 | Discord Bot | 21 | $0 | P0 (parallel P1) |
| P3 | Memory System | 19 | $2 | P1 |
| P4 | Persona Engine | 19 | $1 | P3 |
| P5 | Agent Loop | 23 | $3 | P1+P3 |
| P6 | MCP Tools | 21 | $1 | P1 |
| P7 | Surveillance | 22 | $1 | P0 |
| P8 | Observability | 23 | $4 | P0-P7 |
| **MVP Total** | | **202** | **$27** | |

### Stabilization Phases (P9-P10)

| Phase | Name | Steps | Cost/mo | Depends On |
|-------|------|-------|---------|-----------|
| P9 | Financial Tracking | 13 | $1 | P8 |
| P10 | Production Hardening | 21 | $1 | P8 |
| **Stabilization Total** | | **34** | **$2** | |

### Expansion Phases (P11-P22)

| Phase | Name | Steps | Cost/mo | Depends On |
|-------|------|-------|---------|-----------|
| P11 | WhatsApp Integration | 23 | $0 | P5 + P8 |
| P12 | Gmail/Email Integration | 29 | $0 | P5 + P8 |
| P13 | X Auto Poster | 28 | TBD | P5 + P6 + P7 + P8 |
| P14 | Wearable/Xiaomi Watch | 27 | $0 | P7 + P8 |
| P15 | Windows Daemon + WebSocket | 15 | $5-15 | P5 + P8 + P12 |
| P16 | Knowledge Graph | TBD | TBD | P3 + P5 + P8 |
| P17 | Cross-Device Sync | TBD | TBD | P15 + P8 |
| P18 | Advanced Memory | TBD | TBD | P3 + P8 |
| P19 | Multi-Project Context | TBD | TBD | P3 + P5 + P8 |
| P20 | Self-Improvement Loop | TBD | TBD | P5 + P8 |
| P21 | Voice Interface | TBD | TBD | P2 + P8 |
| P22 | Additional Integrations TBD | TBD | TBD | P8 |
| **Expansion Total** | | **122 (P16-P22 TBD)** | **$5-15+TBD** | |

| **Grand Total** | **23 phases** | **358 (P16-P22 TBD)** | **$34-44+TBD** | |

**Critical path**: P0 → P1 → P3 → P5. P2 runs parallel with P1.

### Stabilization Phase Details (P9-P10)

P9 (Financial Tracking) and P10 (Production Hardening) are Stabilization phases that solidify the MVP foundation before Expansion begins. Step content is tracked in `PROGRESS.md`, `CHECKLIST.md`, and `stepprompts/StepPrompts.md`.

| Phase | Steps | Goal | Evidence Path |
|-------|-------|------|---------------|
| P9 | 13 | Cost tracking, budget alerts, FinOps dashboards | `evidence/phase-9/` |
| P10 | 21 | Hardening, reliability, DR validation, security audit | `evidence/phase-10/` |

### Expansion Phase Details (P11-P22)

Expansion phases build new capabilities on top of the MVP + Stabilization foundation. Each phase is independently scoped when ready for implementation. Steps are TBD until planner gate; P11-P13 now have Tier 1 step prompts.

#### Phase 11: WhatsApp Integration

- **Goal**: Bidirectional WhatsApp messaging via Neonize (pure Python, wraps Go whatsmeow). ChannelAdapter pattern, ConversationalAgent, intent classifier, Discord bridge, HARD STOP cross-channel.
- **Dependencies**: P5 (Agent Loop) + P8 (Observability)
- **Steps**: 23 (P11-001 to P11-023)
- **Evidence path**: `evidence/phase-11/`

### Phase 11: WhatsApp Integration (23 steps)

**Library:** Neonize v0.3.18 (pure Python, wraps Go whatsmeow) — replaces Baileys/Node.js from original ADR-022
**Hosting:** Same VPS, separate `guinevere-whatsapp.service` systemd unit

**Key Architecture Decisions:**

- ChannelAdapter interface (reusable for P12 Gmail, P13 X, P14 Wearable)
- UnifiedMessage dataclass for cross-channel message normalization
- ConversationalAgent using LLMRouter + shared memory pool
- `!` command prefix (not `/`)
- 10-message sliding window context, shared with Discord
- Text-only MVP; media → persona-consistent acknowledgment
- HARD STOP cross-channel via shared Redis flag
- Rate limiting: 8/min, 30/hour, 200/day with Gaussian jitter
- Discord bridge: mirror conversations to private channel

**Step Breakdown:**

| Category | Steps | Description |
|----------|-------|-------------|
| Infrastructure & Auth | P11-001 to P11-003 | Neonize setup, session auth, connection handler |
| Channel Layer | P11-004 to P11-005 | ChannelAdapter interface, WhatsAppAdapter |
| Conversational Agent | P11-006 to P11-007 | Core agent, context manager |
| Message Pipeline | P11-008 to P11-010 | Routing, intent classifier, command handler |
| UX & Formatting | P11-011 to P11-013 | Typing/streaming, formatter, media ack |
| Safety | P11-014 to P11-017 | Rate limiter, HARD STOP, safe word, whitelist |
| Discord Bridge | P11-018 to P11-019 | Message mirror, notifications |
| Operations | P11-020 to P11-022 | Reconnection, monitoring, systemd |
| E2E Testing | P11-023 | Full integration test (P11 GATE) |

#### Phase 12: Gmail/Email Integration

- **Goal**: Read, compose, and send emails via Gmail API; triage and summarize inbox
- **Dependencies**: P5 (Agent Loop) + P8 (Observability)
- **Steps**: 29 (P12-001 to P12-029)
- **Cost**: $0/month (Gmail API free tier + Resend free tier)
- **Evidence path**: `evidence/phase-12/`

**Key Architecture Decisions:**

- Gmail API REST client wrapper with OAuth2 token rotation via SOPS
- ChannelAdapter pattern (GmailAdapter) reusing P11 interface
- Resend for transactional email delivery (password reset, alerts)
- Cloud Pub/Sub push pipeline for real-time inbox watching
- Email classifier cascade: spam → priority → category → intent
- LLM-powered draft generation with Discord approval UX
- Cross-channel HARD STOP shared via Redis flag
- Secret scanner + PII redactor for all inbound/outbound email content

**Step Breakdown:**

| Category | Steps | Description |
|----------|-------|-------------|
| Infrastructure & Auth | P12-001 to P12-003 | GCP Project + Gmail API Enable, OAuth2 Credential + SOPS, Resend Transactional Email |
| Client & Sync | P12-004 to P12-006 | Gmail API Client Wrapper, Full/Hybrid Sync Engine, Cloud Pub/Sub Push Pipeline |
| Channel Layer | P12-007 to P12-008 | GmailAdapter (ChannelAdapter), Conversation Context Manager |
| Intelligence | P12-009 to P12-012 | Email Classifier Cascade, Priority Scorer, Content Sanitizer + Injection Defense, Secret Scanner + PII Redactor |
| Memory & Bridge | P12-013 to P12-014 | Memory Store Integration, Financial Email → P9 Bridge |
| Draft & Send | P12-015 to P12-017 | Draft Generator (LLM), Draft Approval UX (Discord), Draft Send via Gmail API |
| Notifications | P12-018 to P12-020 | Real-Time Notifications, Morning Briefing Generator, !email-digest Command |
| Safety & Compliance | P12-021 to P12-023 | Consent + Surveillance Policy, Cross-Channel HARD STOP, Surveillance Data Classification |
| Operations | P12-024 to P12-026 | Watch Health + Auto-Refresh, Grafana Dashboard + Metrics, Systemd Service + Runbook |
| Testing | P12-027 to P12-029 | Integration Test (10 Scenarios), Agent Loop Trigger Detector, TaskContract Email Context |

**Full Step List:**

| Step | Title |
|------|-------|
| P12-001 | GCP Project + Gmail API Enable |
| P12-002 | OAuth2 Credential + SOPS |
| P12-003 | Resend Transactional Email |
| P12-004 | Gmail API Client Wrapper |
| P12-005 | Full/Hybrid Sync Engine |
| P12-006 | Cloud Pub/Sub Push Pipeline |
| P12-007 | GmailAdapter (ChannelAdapter) |
| P12-008 | Conversation Context Manager |
| P12-009 | Email Classifier Cascade |
| P12-010 | Priority Scorer |
| P12-011 | Content Sanitizer + Injection Defense |
| P12-012 | Secret Scanner + PII Redactor |
| P12-013 | Memory Store Integration |
| P12-014 | Financial Email → P9 Bridge |
| P12-015 | Draft Generator (LLM) |
| P12-016 | Draft Approval UX (Discord) |
| P12-017 | Draft Send via Gmail API |
| P12-018 | Real-Time Notifications |
| P12-019 | Morning Briefing Generator |
| P12-020 | !email-digest Command |
| P12-021 | Consent + Surveillance Policy |
| P12-022 | Cross-Channel HARD STOP |
| P12-023 | Surveillance Data Classification |
| P12-024 | Watch Health + Auto-Refresh |
| P12-025 | Grafana Dashboard + Metrics |
| P12-026 | Systemd Service + Runbook |
| P12-027 | Integration Test (10 Scenarios) |
| P12-028 | Agent Loop Trigger Detector |
| P12-029 | TaskContract Email Context |

#### Phase 13: X Auto Poster

- **Goal**: Automated X/Twitter posting with manual Windows image drop-folder input, S3 queue lifecycle, Gemini captioning, dedicated Obscura CDP posting, Discord controls, PostgreSQL logs, and operational safeguards.
- **Dependencies**: P5 (Agent Loop) + P6 (MCP Tools) + P7 (Surveillance) + P8 (Observability)
- **Steps**: 28
- **Cost**: TBD — S3 media storage, Gemini caption generation, and Obscura CDP runtime; no paid X API dependency
- **Evidence path**: `evidence/phase-13/`
- **Key components**:
  - **Windows watchdog** for local image drop-folder upload to S3 `/pending/`
  - **S3 prefix queue** for `/pending/`, `/processing/`, `/posted/`, `/failed/`, `/held/`, `/archived/`
  - **Gemini captioning** with Flash primary, Pro fallback, alt text, hashtags, and moderation block path
  - **Obscura CDP** dedicated X automation instance on port 9223 with isolated storage and SOPS cookies
  - **Rate controls** with 3h minimum interval, max 5/day, night hold 23:00-06:00 WIB, and immediate override
  - **Discord controls** for status, list, cancel, hold/resume, edit, delete, retry, dry run, and daily summary
  - **PostgreSQL + Grafana** state, retry logs, session age, metrics, alerts, and 90-day retention

| Step | Title |
|------|-------|
| P13-001 | S3 Queue Setup |
| P13-002 | Windows Watchdog Script |
| P13-003 | Obscura CDP Dedicated Instance |
| P13-004 | Systemd Service |
| P13-005 | Queue Polling Loop |
| P13-006 | Sidecar Parser |
| P13-007 | Rate Limiter |
| P13-008 | Cookie Injector |
| P13-009 | Session Health Check |
| P13-010 | Session Recovery |
| P13-011 | Caption Generator |
| P13-012 | Content Moderation |
| P13-013 | Tone Controller |
| P13-014 | Compose Adapter (CDP) |
| P13-015 | Media Upload (CDP) |
| P13-016 | Post Action |
| P13-017 | Dry-Run Mode |
| P13-018 | Retry Engine |
| P13-019 | Circuit Breaker |
| P13-020 | Processing Timeout Handler |
| P13-021 | Post Notification |
| P13-022 | Status Commands |
| P13-023 | Edit Command |
| P13-024 | Delete Command |
| P13-025 | Retry Commands |
| P13-026 | Grafana Dashboard |
| P13-027 | Daily Summary |
| P13-028 | Integration Test + P13 GATE |

#### Phase 14: Wearable/Xiaomi Watch (Expansion)

- **Goal:** Xiaomi wearable health data ingestion via Gadgetbridge WebDAV sync → VPS pipeline → TimescaleDB → anomaly detection → GHI scoring → persona-adjusted behavior → Discord health commands.
- **Dependencies:** P7 (Surveillance) + P8 (Observability/MVP Gate)
- **Steps:** 27
- **Cost:** $0/month
- **Evidence path**: `evidence/phase-14/`
- **Key components**:
  - **Gadgetbridge primary** data path (watch → SQLite → WebDAV auto-sync → VPS)
  - **Mi Fitness Cloud SDK** fallback for gap detection
  - **7 hypertables** in `health.*` schema + 4 aggregate tables
  - **Anomaly detection**: ±20% from 28-day baseline, 3 severity tiers
  - **GHI scoring**: Sleep 40% / Cardio 20% / Activity 20% / Recovery 20%, 5 tiers
  - **Persona state machine** adjusts Y-level when sleep-deprived (NEVER for confrontation)
  - **4 Discord commands**, morning brief health section, proactive DM alerts
  - **CRITICAL classification**, 365d retention, data export/deletion support
  - **guinevere-health.service** separate systemd unit

| Step | Title |
|------|-------|
| P14-001 | Device Procurement + Gadgetbridge Setup |
| P14-002 | WebDAV Server Endpoint |
| P14-003 | Database Schema Creation (7 hypertables) |
| P14-004 | HMAC Key Provisioning |
| P14-005 | Gadgetbridge SQLite Parser |
| P14-006 | Health Ingestion Endpoint |
| P14-007 | Consumer Scope Mapping |
| P14-008 | Mi Fitness Cloud SDK Fallback |
| P14-009 | Personal Baseline Computation |
| P14-010 | Anomaly Detection Engine |
| P14-011 | GHI Composite Score Engine |
| P14-012 | Daily Summary Pre-computation |
| P14-013 | Persona State Machine (Health-Aware) |
| P14-014 | Health Memory Injection |
| P14-015 | Distress Escalation Logic |
| P14-016 | /health-status + /ghi-score Commands |
| P14-017 | /sleep-report + /activity-today Commands |
| P14-018 | Morning Brief Health Section |
| P14-019 | Proactive Health Alerts + Night Owl |
| P14-020 | WAC-001..007 Activation Checklist |
| P14-021 | Data Export + Deletion |
| P14-022 | Prometheus Metrics |
| P14-023 | Grafana Health Dashboard |
| P14-024 | Stale Data + Battery Alerts |
| P14-025 | Systemd Service |
| P14-026 | Mock Health Data Generator |
| P14-027 | Integration Test + P14 GATE |

#### Phase 15: Windows Daemon + WebSocket

- **Goal**: Windows surveillance daemon with WebSocket connection to VPS via Tailscale mesh
- **Dependencies**: P5 (Agent Loop) + P8 (Observability/MVP Gate) + P12 (Surveillance Pipeline)
- **Steps**: 15 (P15-001 through P15-015)
- **Cost**: $5-15/month (NSSM + minimal CPU on Windows PC)
- **Evidence path**: `docs/setup-evidence/p15-expansion/`
- **Planner Gate**: `docs/setup-evidence/plans/p15-windows-daemon.md`
- **StepPrompts**: `stepprompts/StepPrompts.md` Phase 15 section

| Step | Title |
|---|---|
| P15-001 | Project Scaffold + Base Tracker ABC |
| P15-002 | Active Window Tracker (win32gui + psutil) |
| P15-003 | Idle Tracker (GetLastInputInfo, graduated) |
| P15-004 | Git Context Tracker (traversal + project mapping) |
| P15-005 | Event Pipeline (MessagePack + EventRouter + WS Client) |
| P15-006 | NSSM Service Wrapper + Config |
| P15-007 | VPS WebSocket Endpoint (FastAPI + ConnectionManager) |
| P15-008 | Command Protocol (ACK-based, Redis DB4 pub/sub) |
| P15-009 | Consent Gate Integration (belt-and-suspenders) ⚠️ SAFETY-CRITICAL |
| P15-010 | Discord `/pc` Command (status + session override) |
| P15-011 | Observability (Prometheus metrics + Grafana dashboard + alerting) |
| P15-012 | TimescaleDB Migration (windows_events hypertable) |
| P15-013 | Test Suite (unit + integration) |
| P15-014 | Integration Test — End-to-End Daemon ↔ VPS |
| P15-015 | Deployment + Smoke Test + README |

#### Phase 16: Knowledge Graph

- **Goal**: Graph-based knowledge representation of memories, entities, and relationships
- **Dependencies**: P3 (Memory System) + P5 (Agent Loop) + P8 (Observability)
- **Steps**: TBD
- **Evidence path**: `evidence/phase-16/`

#### Phase 17: Cross-Device Sync

- **Goal**: Synchronize state, context, and notifications across Windows daemon and VPS
- **Dependencies**: P15 (Windows Daemon) + P8 (Observability)
- **Steps**: TBD
- **Evidence path**: `evidence/phase-17/`

#### Phase 18: Advanced Memory

- **Goal**: Enhanced memory with semantic search, episodic replay, and forgetting curves
- **Dependencies**: P3 (Memory System) + P8 (Observability)
- **Steps**: TBD
- **Evidence path**: `evidence/phase-18/`

#### Phase 19: Multi-Project Context

- **Goal**: Manage multiple project contexts simultaneously with isolated memory namespaces
- **Dependencies**: P3 (Memory System) + P5 (Agent Loop) + P8 (Observability)
- **Steps**: TBD
- **Evidence path**: `evidence/phase-19/`

#### Phase 20: Self-Improvement Loop

- **Goal**: Autonomous analysis of past interactions to refine prompts, memory retrieval, and behavior
- **Dependencies**: P5 (Agent Loop) + P8 (Observability)
- **Steps**: TBD
- **Evidence path**: `evidence/phase-20/`

#### Phase 21: Voice Interface

- **Goal**: Voice input/output via STT/TTS integration for hands-free interaction
- **Dependencies**: P2 (Discord Bot) + P8 (Observability)
- **Steps**: TBD
- **Evidence path**: `evidence/phase-21/`

#### Phase 22: Additional Integrations TBD

- **Goal**: Placeholder for future integrations not yet scoped
- **Dependencies**: P8 (Observability)
- **Steps**: TBD
- **Evidence path**: `evidence/phase-22/`

---

## 2. File Overview

| File | Purpose | Who Reads |
|------|---------|-----------|
| `PROGRESS.md` | Phase/step tracking, counters, blockers, cost | Agent every session |
| `stepprompts/StepPrompts.md` | Detailed per-step instructions (commands, verification, rollback) | Agent per step |
| `CHECKLIST.md` | Phase-level verification checklists | Agent per step |
| `docs/IMPLEMENTATION_GUIDE.md` | This file — system manual | Humans + agents |

### PROGRESS.md

Single source of truth for project state. Contains phase summary table, active step, blockers, cost tracking, and step counters. **Update rule**: after every completed step, update status + counters + cost. Never ask "mau saya update progress.md?" — just update.

### StepPrompts.md

Each step follows this template:

- **Header**: Phase, dependencies, cost impact, ADR reference, acceptance criteria
- **Context**: Why this step exists
- **Pre-flight Checks**: Commands to verify prerequisites
- **Execution**: Exact commands in order
- **Verification**: Commands + expected output
- **Evidence**: What to capture, where to store
- **Rollback**: How to undo if step fails

### CHECKLIST.md

Phase-level checklists. All items must be green before a phase is complete. Covers: step completion, evidence existence, verification commands, ADR implementation, cost within budget, no regressions, safety boundaries preserved.

---

## 3. Step Execution Workflow

Every step follows this 8-step workflow. No exceptions.

### 1. Read the Stepprompt

Find the step by ID (e.g., `P0-005`). Read context, pre-flight, execution, verification, evidence, and rollback.

### 2. Run Pre-flight Checks

Verify dependencies are met before execution:

```bash
sudo -u guinevere id                    # user exists?
dpkg -l | grep fail2ban                # already installed?
cat /etc/os-release | grep VERSION_ID  # Ubuntu 24.04?
```

If pre-flight fails: **stop and investigate**, do not proceed.

### 3. Execute Commands

Copy-paste from stepprompt. Do not improvise:

```bash
sudo apt install -y fail2ban
sudo tee /etc/fail2ban/jail.local << 'EOF'
[sshd]
enabled = true
maxretry = 3
bantime = 3600
EOF
sudo systemctl enable --now fail2ban
```

### 4. Verify Outputs

Compare actual to expected output from stepprompt:

```bash
sudo fail2ban-client status sshd   # Expected: enabled
sudo systemctl is-active fail2ban  # Expected: active
```

If output doesn't match: **stop, diagnose, do not force**.

### 5. Capture Evidence

Write to `evidence/phase-N/step-MMM/`:

```bash
mkdir -p evidence/phase-0/step-005
sudo fail2ban-client status sshd > evidence/phase-0/step-005/fail2ban-status.txt
```

### 6. Run Checklist

Open `CHECKLIST.md`, verify phase items still green, mark newly completed.

### 7. Update PROGRESS.md

```markdown
| P0-005 | fail2ban Configuration | ✅ Complete | $0 | 2026-05-31 |
```

Update counters, cumulative cost, note blockers.

### 8. Commit to Git

```bash
git add -A && git commit -m "P0-005: fail2ban configuration complete"
```

### Batch Execution

```
"lanjut P0-005 sampai P0-010"
```

Guinevere executes sequentially (unless independent), verifies each, reports at end.

---

## 4. Evidence System

### Directory Structure

```
evidence/phase-{N}/step-{MMM}/
```

Where `{N}` = phase number (0-22), `{MMM}` = zero-padded step number.

### Required Per Step

| Evidence | Description |
|----------|-------------|
| Verification output | Command output proving success |
| Error log (if any) | Errors encountered during execution |
| Cost impact | Effect on $30/month budget |

### Optional

Screenshots (UI changes), performance benchmarks (query times), config diffs, network captures.

### Evidence File Format

```markdown
# P0-005: fail2ban Configuration — Evidence

**Date**: 2026-05-31 14:30 WIB
**Step**: P0-005

## What Was Done
Installed and configured fail2ban with SSH protection.

## Verification Results
- fail2ban-client status sshd: enabled, 0 banned
- systemctl is-active fail2ban: active

## Files Changed
- /etc/fail2ban/jail.local (created)

## Cost Impact
$0 — no additional cost.

## Rollback
sudo systemctl stop fail2ban && sudo apt purge -y fail2ban

## References
ADR-014, AC-INFRA-005
```

---

## 5. Cost Management

### Budget Thresholds

| Threshold | Amount | Action |
|-----------|--------|--------|
| Daily alert | $1/day | Notification in #system-health |
| Warning | $15/month | Faiz notified, review spending |
| Critical | $25/month | Non-essential LLM calls paused |
| Hard stop | $30/month | All LLM API calls blocked |

### Tracking (Redis DB5)

```bash
redis-cli -n 5 GET "ratelimit:total:daily:$(date +%Y-%m-%d)"
redis-cli -n 5 GET "ratelimit:total:monthly:$(date +%Y-%m)"
redis-cli -n 5 GET "ratelimit:gpt55:daily:$(date +%Y-%m-%d)"
redis-cli -n 5 GET "ratelimit:exa:daily:$(date +%Y-%m-%d)"
```

### Per-Tool Caps

| Tool | Daily Cap | Monthly Avg |
|------|-----------|-------------|
| GPT-5.5 (9Router secondary) | $2/day | $15/mo ceiling |
| DeepSeek V4 Flash (9Router primary) | $1/day | $5/mo |
| Exa | $5/day burst | $1/mo avg |
| Embeddings | $0.50/day | $2/mo |
| Graceful degradation | $0 | $0 (no LLM) |

### Cost Reduction

1. Use DeepSeek V4 Flash via the 9Router `guinevere` combo as the low-cost primary route
2. Use GPT-5.5 via cockpit only as the secondary high-capability route
3. Gracefully degrade when routing is unavailable instead of running a local Ollama fallback
4. Exa hybrid model — cached results don't count against cap
5. Batch operations — combine queries into single LLM calls
6. P9-P10 are Stabilization phases and P11-P22 are Expansion phases — all deferrable under budget pressure

### Monitoring Commands

```bash
/cost              # Discord: daily spend breakdown
/budget            # Discord: monthly projection
```

Monthly cost report auto-generated on the 1st in #system-health.

---

## 6. Shared VPS Rules

### Cardinal Rule

**Guinevere shares VPS with Aizanta. Never touch Aizanta services, containers, databases, or files.**

### Isolation Matrix

| Resource | Guinevere | Aizanta | Rule |
|----------|-----------|---------|------|
| Linux user | `guinevere` | `aizanta` | Separate users |
| Docker network | `guinevere-net` | `aizanta-net` | No cross-network |
| PostgreSQL | `guinevere` db | `aizanta` db | Separate DB + users |
| Redis DB numbers | 0-5 | 10-15 | No overlap |
| Systemd services | `guinevere-*` | `aizanta-*` | Prefix convention |
| Home directory | `/home/guinevere/` | `/home/aizanta/` | Never cross |
| Docker containers | `guinevere-*` | `aizanta-*` | Prefix convention |

### Resource Allocation

| Resource | Guinevere | Aizanta | OS | Total |
|----------|-----------|---------|-----|-------|
| CPU | 2 cores | 1.5 cores | 0.5 | 4 cores |
| RAM | 8GB | 6GB | 2GB | 16GB |
| Disk | 60GB | 40GB | 20GB | 120GB |

Cgroup limits enforced via systemd: `MemoryMax=8G`, `CPUQuota=200%`.

### Verify Aizanta Unaffected (After Every P0 Step)

```bash
systemctl status aizanta-*                          # services running
docker ps --filter "name=aizanta"                   # containers up
psql -U aizanta -d aizanta -c "SELECT 1"           # DB accessible
redis-cli -n 10 PING                                # Redis responding
```

### If You Break Aizanta

1. **Stop** all Guinevere operations immediately
2. **Rollback** the last step (use stepprompt rollback section)
3. **Verify** Aizanta recovered
4. **Document** in `evidence/incidents/`
5. **Report** to Faiz before proceeding

---

## 7. Emergency Procedures

### Rollback

Every stepprompt includes rollback commands. Use them:

```bash
# Example: rollback P0-014 PostgreSQL
sudo systemctl stop postgresql
sudo apt purge -y postgresql-16
sudo rm -rf /etc/postgresql/16 /var/lib/postgresql/16
```

Rules: only rollback the failed step, verify Aizanta unaffected, document in evidence, update PROGRESS.md.

### HARD STOP (Persona Emergency)

Say **"HARD STOP"** → Guinevere enters neutral mode immediately:

- All persona behavior stops (no mood, yandere, punishment)
- Pure neutral assistant mode
- Audit trail preserved
- Only re-engaged by Faiz explicitly

### Break-Glass (Service Emergency)

```bash
sudo systemctl stop guinevere-*              # stop all services
docker stop $(docker ps -q --filter "name=guinevere")  # stop containers
sudo pkill -u guinevere                      # nuclear: kill all processes
```

### Data Loss Recovery

```bash
# PostgreSQL from S3
aws s3 cp s3://guinevere-backups/db/$(date +%Y-%m-%d).sql.gz /tmp/
gunzip /tmp/$(date +%Y-%m-%d).sql.gz
psql -U guinevere_core -d guinevere < /tmp/$(date +%Y-%m-%d).sql

# Files from R2
rclone copy cloudflare-r2:guinevere-backups/files/ /home/guinevere/
```

Redis is cache — regenerates automatically, no restore needed.

### Distress Protocol (D0-D4)

| Level | Response |
|-------|----------|
| D0 | Normal operation |
| D1 | Softened tone, no punishment |
| D2 | Pause non-essential tasks |
| D3 | Stop all tasks, prioritize wellbeing |
| D4 | Immediate HARD STOP, crisis resources |

Cannot be suppressed — overrides all persona behavior including punishment.

---

## 8. Troubleshooting

### Service Won't Start

```bash
journalctl -u guinevere-<service> -n 50    # check logs
ss -tlnp | grep <port>                      # port conflict?
systemctl list-units --type=service | grep guinevere  # conflicting service?
```

### Database Connection Failed

```bash
psql -U guinevere_core -h localhost -c "SELECT 1"  # connectivity
systemctl status postgresql                          # running?
cat /etc/postgresql/16/main/pg_hba.conf | grep guinevere  # allowed?
psql -U postgres -c "SELECT count(*) FROM pg_stat_activity WHERE usename='guinevere_core'"
```

### Redis Timeout

```bash
redis-cli -n 0 PING                         # PONG?
systemctl status redis-server                # running?
redis-cli -n 0 INFO memory | grep used_memory_human
redis-cli ACL LIST | grep guinevere          # ACL correct?
```

### LLM API Error

```bash
systemctl status guinevere-9router           # 9Router running?
curl http://localhost:20128/v1/chat/completions -H "Content-Type: application/json" \
  -d '{"model":"guinevere","messages":[{"role":"user","content":"test"}]}'
redis-cli -n 5 GET "ratelimit:gpt55:daily:$(date +%Y-%m-%d)"  # rate limited?
# Ollama fallback skipped per Faiz directive 2026-06-01; final fallback is graceful degradation.
```

### Discord Bot Offline

```bash
systemctl status guinevere-discord
sops -d /home/guinevere/config/secrets/discord.enc.yaml | grep token
journalctl -u guinevere-discord -n 20 | grep -i "gateway\|connect\|error"
# Verify intents on developer.discord.com: MESSAGE_CONTENT, GUILD_MEMBERS, GUILD_PRESENCES
```

### Browser Automation Failure

```bash
systemctl status guinevere-obscura                    # Obscura CDP running?
curl -s http://127.0.0.1:9222/json/version | head -5  # CDP endpoint responding?
# If fails: systemctl restart guinevere-obscura
# Playwright connects via: browser = await playwright.chromium.connect_over_cdp("http://127.0.0.1:9222")
# Rollback: see ADR-033 for Playwright+Chromium fallback procedure
```

### Shared VPS Conflict

```bash
ps -u guinevere -o pid,rss,comm --sort=-rss | head -10   # Guinevere RAM
ps -u aizanta -o pid,rss,comm --sort=-rss | head -10     # Aizanta RAM
docker network inspect guinevere-net | grep -i aizanta    # Expected: no results
```

### Cost Overrun

```bash
redis-cli -n 5 GET "ratelimit:total:monthly:$(date +%Y-%m)"  # current spend
redis-cli -n 5 KEYS "ratelimit:*:daily:$(date +%Y-%m-%d)"    # per-tool check
# Emergency: switch 9Router to prefer DeepSeek over GPT-5.5
```

---

## 9. OpenCode Session Management

### Session Commands

| Command | Effect |
|---------|--------|
| `"lanjut"` | Continue from PROGRESS.md last state |
| `"lanjut P0-005"` | Jump to specific step |
| `"lanjut P0-005 sampai P0-010"` | Batch execution |
| `"stop"` | Pause safely, save state |
| `"audit"` | Read-only audit of current state |
| `"fix 1+2+3"` | Apply specific fixes |
| `"bypass approval"` | Skip doc overhead (never skip safety) |
| `"HARD STOP"` | Emergency persona neutralization |

### Skipping a Step

Mark as ⏭️ Skipped in PROGRESS.md with reason. Document in blockers section:

```markdown
| P0-006 | CrowdSec Setup | ⏭️ Skipped | $0 | fail2ban sufficient for now |
```

### Resuming After Break

Guinevere reads PROGRESS.md, checks blockers, verifies last evidence exists, continues from next incomplete step.

### Tips

- **Commit after each step** — preserves state, enables rollback
- **Don't skip evidence** — future sessions need verification proof
- **Update cost after each step** — prevents budget surprises
- **Note blockers immediately** — don't let them fester
- **Use `task_id` continuation** — resume failed sub-agents rather than restarting

---

## 10. Escalation Rules

### Continue Without Asking

Standard steps with passing pre-flight, verification returning expected output, evidence capture, PROGRESS.md updates, git commits, sub-agent spawning, doc-sync without ADR changes, cost-neutral operations within budget.

### Ask Faiz First

| Situation | Why |
|-----------|-----|
| Destructive operations | `rm -rf`, `DROP TABLE`, force push |
| Budget exceptions | Exceeding $5/day tool cap |
| ADR conflicts | Step contradicts existing ADR |
| Aizanta impact | Might affect Aizanta services |
| Safety-affecting changes | Persona, surveillance, consent, encryption |
| Phase transitions | Moving between phases |
| Step skipping | Marking step skipped instead of complete |

### Hard Stop (No Continuation)

| Situation | Action |
|-----------|--------|
| Safety violation | HARD STOP, neutral mode |
| Data loss risk | Stop, rollback, report |
| Shared VPS conflict | Stop, verify Aizanta, report |
| Budget hard stop ($30) | Stop all LLM calls |
| Two consecutive failures | Stop, diagnose root cause |
| Consent boundary crossed | Stop, audit, report |

---

## 11. Quick Reference

### Services

| Service | Unit | Port |
|---------|------|------|
| Core API | `guinevere-core` | 8000 |
| Discord | `guinevere-discord` | — |
| 9Router | `guinevere-9router` | 8080 |
| MCP | `guinevere-mcp` | — |
| Obscura CDP | `guinevere-obscura` | 9222 |
| Loops | `guinevere-loops` | — |
| Scheduler | `guinevere-scheduler` | — |
| Surveillance | `guinevere-surveillance` | — |
| Monitoring | `guinevere-monitoring` | — |

### Key Paths

`/home/guinevere/{code,config,data,logs,backups}/` — application root
`evidence/` — implementation evidence | `audit-reports/` — auditor reports | `docs/` — documentation

### Ports

5433 PostgreSQL | 6380 Redis | 8000 Core API | 9222 Obscura CDP | 20128 9Router | 9090 Prometheus | 3000 Grafana | graceful degradation has no local port

### Redis DBs

0: task queue | 1: session cache | 2: surveillance buffer | 3: loop state | 4: reserved | 5: rate limits/cost | 10-15: Aizanta (do not touch)

### Critical Commands

```bash
# Health
systemctl status guinevere-*
curl http://localhost:8000/health
redis-cli -n 0 PING
psql -U guinevere_core -d guinevere -c "SELECT 1"

# Cost
redis-cli -n 5 GET "ratelimit:total:monthly:$(date +%Y-%m)"

# Emergency
sudo systemctl stop guinevere-*

# Aizanta check
systemctl status aizanta-*
docker ps --filter "name=aizanta"

# Logs
journalctl -u guinevere-core -n 50 --no-pager
```

---

*This guide is part of the Guinevere implementation system. Update when workflows, paths, or procedures change.*
*Last reviewed: 2026-05-31*
