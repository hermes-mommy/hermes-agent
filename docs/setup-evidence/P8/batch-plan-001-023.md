# P8 Batch Plan: Observability + FinOps + MVP Gate (P8-001..P8-023)

> **Phase**: P8 — Observability + FinOps + MVP Gate (Final Production-Readiness)
> **Date**: 2026-06-03
> **Author**: Guinevere (P8 Planner)
> **Status**: PLANNED
> **Steps**: P8-001 through P8-023 (23 total)
> **Batches**: 7 execution batches + 1 final manual gate
> **Budget**: $4/month incremental (monitoring stack), $27→$30 cumulative
> **Target Host**: hostdata.id VPS, Ubuntu 24.04, user=guinevere
> **Evidence Root**: `docs/setup-evidence/P8/STEP-P8-{NNN}/`

---

## Table of Contents

1. [Overview](#1-overview)
2. [Research Inputs](#2-research-inputs)
3. [Known State (Pre-Implementation)](#3-known-state-pre-implementation)
4. [Binding Decisions](#4-binding-decisions)
5. [Master Todo (23 steps)](#5-master-todo-23-steps)
6. [Dependency Map + Parallelism](#6-dependency-map--parallelism)
7. [Collision Scan](#7-collision-scan)
8. [Batch Execution Plan (7 batches)](#8-batch-execution-plan-7-batches)
9. [Per-Step Implementation Design + Scaffolds (P8-001..P8-023)](#9-per-step-implementation-design--scaffolds-p8-001p8-023)
10. [Token and Secret Handling](#10-token-and-secret-handling)
11. [Evidence Paths](#11-evidence-paths)
12. [Auditor Matrix](#12-auditor-matrix)
13. [Rollback Plan](#13-rollback-plan)
14. [Tracker Sync Plan](#14-tracker-sync-plan)
15. [Caveats and Known Risks](#15-caveats-and-known-risks)
16. [Execution Checklist](#16-execution-checklist)

---

## 1. Overview

### 1.1 Project Context

- **Project**: Guinevere de Baroque — autonomous AI companion and engineering agent system
- **Phase**: P8 = Observability + FinOps + MVP Gate (final production-readiness phase)
- **Scope**: Deploy full monitoring stack (Prometheus, Grafana, Loki, Promtail, Alertmanager, exporters), integrate Sentry for application error tracking, implement FinOps Discord commands (/cost, /budget, monthly report), configure alert routing with SEV-level matrix, and execute MVP acceptance criteria full run
- **Steps**: 23 atomic implementation steps (P8-001 through P8-023)
- **Batches**: 7 execution batches with defined parallelism and dependency gates
- **Budget Impact**: $4/month incremental (monitoring container resource usage), bringing cumulative from $27 to $30/month
- **Infrastructure**: All containers and services run on hostdata.id VPS (Ubuntu 24.04), under `guinevere` user, within `guinevere.slice` systemd slice

### 1.2 Phase Goals

1. **Full Observability Stack**: Prometheus metrics collection, Grafana dashboards, Loki log aggregation, Promtail log shipping, Alertmanager alert routing — all running as Docker containers on `guinevere-net`
2. **Application Error Tracking**: Sentry SDK integrated with FastAPI application, PII scrubber active, `send_default_pii=false` enforced
3. **FinOps Commands**: Discord commands `/cost`, `/budget`, and monthly cost report — all pulling from existing Redis DB5 cost tracking data
4. **Alert Routing**: SEV0-SEV4 alerts routed to appropriate Discord channels and Gotify, neutral incident-command tone enforced
5. **Backup Monitoring**: Backup freshness alerting via node-exporter textfile collector
6. **MVP Acceptance Gate**: All acceptance criteria from AC Catalog verified, documented, and presented to Faiz for sign-off

### 1.3 What This File Is

This file is the **authoritative planner artifact** for P8. A sub-agent reading only this file should have everything needed to implement any step. It contains:

- Complete binding decisions (versions, ports, configs)
- Per-step implementation design with code patterns and notes
- Per-step verification scaffolds (machine-checkable acceptance criteria)
- Dependency map and parallelism decisions
- Collision scan and resolution strategies
- Evidence paths and auditor matrix
- Rollback plan and caveats

### 1.4 What This File Is NOT

- This file does NOT contain implementation code (configs, Python, YAML)
- This file does NOT create evidence files (only references their paths)
- This file does NOT modify PROGRESS.md or CHECKLIST.md
- This file is a PLAN — implementation happens per-step via sub-agent delegation

---

## 2. Research Inputs

### 2.1 Specification Documents

| Document | Path | Lines | Role in P8 |
|----------|------|-------|------------|
| Observability and Alerting Spec v1.0 | `docs/40-operations/40-ObservabilityAlertingSpec_v1.0.md` | 766 | Primary spec: metric catalog, alert rules, dashboard panels, log pipeline, Sentry integration |
| Acceptance Criteria Catalog v1.0 | `docs/10-governance/16-AcceptanceCriteriaCatalog_v1.0.md` | 16 sections | MVP gate: AC-SAFE, AC-SEC, AC-OPS, AC-DATA, AC-CORE, AC-PHASE criteria |
| SLO/SLA/ErrorBudget v1.0 | `docs/40-operations/41-SLO_SLA_ErrorBudget_v1.0.md` | — | SLI catalog with PromQL expressions for SLO thresholds |
| Incident Response/Postmortem v1.0 | `docs/40-operations/42-IncidentResponse_Postmortem_v1.0.md` | — | SEV0-SEV4 matrix, response procedures, escalation paths |
| ADR Index v1.0 | `docs/10-governance/17-ADR_Index_v1.0.md` | — | 34 ADRs; key: ADR-017 (monitoring stack), ADR-018 (security monitoring) |
| Discord UX Spec | `docs/60-persona/62-DiscordUXSpec_v1.0.md` | — | Embed colors, command patterns, channel routing |
| PersonaSafety Policy v1.0 | `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` | — | Sentry PII scrubber requirements, safe-word protection |

### 2.2 Step Prompts

| Source | Location | Content |
|--------|----------|---------| 
| StepPrompts.md.bak | `stepprompts/StepPrompts.md.bak` lines 6940-7042 | P8 step descriptions and acceptance criteria |
| CHECKLIST.md | `CHECKLIST.md` Phase 8 section | MVP Gate checklist items |

### 2.3 Research Agent Reports

| Agent | Type | Report Path | Key Findings |
|-------|------|-------------|--------------| 
| Discord patterns | explore | `research-reports/P8/discord-patterns.md` | Canonical 5-part command pattern, embed format, existing stub commands |
| Docker/systemd patterns | explore | `research-reports/P8/docker-systemd-patterns.md` | Existing compose file pattern, systemd unit pattern, slice resource limits |
| Monitoring stack | librarian | `research-reports/P8/monitoring-stack-versions.md` | Prometheus v3.3.0, Grafana 11.5.0, Loki 3.4.0, Promtail 3.5.8 (CRITICAL: 3.6.0+ drops journald) |
| Sentry integration | librarian | `research-reports/P8/sentry-integration.md` | sentry-sdk[fastapi] usage, PII scrubber patterns, before_send callback |
| Backup/FinOps | explore | `research-reports/P8/backup-finops.md` | Existing backup script sentinel, CostTracker Redis keys, BudgetEnforcer pattern |

---

## 3. Known State (Pre-Implementation)

### 3.1 Infrastructure Already in Place

| Component | Status | Details |
|-----------|--------|---------| 
| Caddy reverse proxy | ACTIVE | Routes Grafana `:3443` to `:3000`, Prometheus `:9443` to `:9090` (Tailscale-only, `tls internal`) |
| Docker network `guinevere-net` | EXISTS | Bridge network, `172.28.0.0/16` subnet |
| Volume directories | EXIST | `/home/guinevere/data/{prometheus,grafana,loki,backups}` — `guinevere:guinevere 0750` |
| `guinevere.slice` | ACTIVE | 8G total, approximately 6.75G allocated, monitoring approximately 640MB fits |
| PostgreSQL | RUNNING | Port 5433 (canonical) |
| PgBouncer | RUNNING | Port 5434 |
| Redis | RUNNING | Port 6380 (canonical) |
| 9Router | RUNNING | Port 20128 |
| Gotify | RUNNING | `localhost:8081`, POST fallback already implemented in `src/discord/gotify_fallback.py` |
| Backup script | EXISTS | `scripts/guinevere-backup.sh` (615 lines, 7 phases), sentinel at `/var/log/guinevere/last-backup-success` |

### 3.2 Application Code Already in Place

| Component | Status | Details |
|-----------|--------|---------| 
| `pyproject.toml` deps | PRESENT | `sentry-sdk[fastapi]>=2`, `prometheus-client>=0.21`, `structlog>=24` |
| `src/observability/__init__.py` | EXISTS but EMPTY | Placeholder module, no implementation |
| `src/discord/bot.py` | ACTIVE | 11 wired + 22 stub commands; `cost`, `budget`, `cost-alert` mapped to Phase 4 stubs |
| `src/discord/commands.py` | ACTIVE | 33 COMMAND_SPECS with frozen dataclass pattern |
| `src/discord/notifications.py` | ACTIVE | `send_alert()` with SEV0-4 routing already implemented |
| `src/discord/gotify_fallback.py` | ACTIVE | Gotify POST `localhost:8081` already implemented |
| `src/core/services/cost_tracker.py` | ACTIVE | `CostTracker` with Redis DB5 keys fully implemented |
| `src/core/main.py` | ACTIVE | FastAPI lifespan pattern, Sentry init NOT yet added |

### 3.3 What Does NOT Exist Yet (To Be Created)

| Component | Status | Created By |
|-----------|--------|------------|
| `monitoring/compose.monitoring.yml` | DOES NOT EXIST | P8-001 |
| `monitoring/prometheus/prometheus.yml` | DOES NOT EXIST | P8-001 |
| `monitoring/prometheus/rules/` | DOES NOT EXIST | P8-014 |
| `monitoring/loki/loki-config.yml` | DOES NOT EXIST | P8-009 |
| `monitoring/promtail/promtail-config.yml` | DOES NOT EXIST | P8-010 |
| `monitoring/alertmanager/alertmanager.yml` | DOES NOT EXIST | P8-015 |
| `monitoring/grafana/provisioning/` | DOES NOT EXIST | P8-007 |
| `monitoring/grafana/dashboards/*.json` | DOES NOT EXIST | P8-008 |
| `monitoring/.env` | DOES NOT EXIST | P8-001 |
| Exporter systemd units | DO NOT EXIST | N/A (exporters run as Docker containers) |
| `systemd/guinevere-monitoring.service` | DOES NOT EXIST | P8-021 |
| Sentry integration code | DOES NOT EXIST | P8-012 |
| Grafana dashboard JSON files | DO NOT EXIST | P8-008 |
| Prometheus alert rule files | DO NOT EXIST | P8-014 |
| node-exporter textfile collector | DOES NOT EXIST | P8-020 |

### 3.4 Port Assignments (Canonical)

| Service | Port | Binding |
|---------|------|---------| 
| PostgreSQL | 5433 | 127.0.0.1 |
| PgBouncer | 5434 | 127.0.0.1 |
| Redis | 6380 | 127.0.0.1 |
| 9Router | 20128 | 127.0.0.1 |
| Prometheus | 9090 | 127.0.0.1 |
| Grafana | 3000 | 127.0.0.1 |
| Loki | 3100 | 127.0.0.1 |
| Alertmanager | 9093 | 127.0.0.1 |
| node-exporter | 9100 | 127.0.0.1 |
| postgres-exporter | 9187 | 127.0.0.1 |
| redis-exporter | 9121 | 127.0.0.1 |

### 3.5 Existing Patterns to Follow

**Docker Compose Pattern:**

```yaml
services:
  service-name:
    container_name: guinevere-service-name
    image: vendor/image:tag
    restart: unless-stopped
    ports:
      - "127.0.0.1:HOST_PORT:CONTAINER_PORT"
    networks:
      - guinevere-net
networks:
  guinevere-net:
    external: true
```

**Systemd Unit Pattern:**

```ini
[Unit]
Description=Guinevere Service
After=network-online.target docker.service
Requires=docker.service

[Service]
Type=exec
User=guinevere
Slice=guinevere.slice
ExecStart=/usr/bin/docker compose -f /path/to/compose.yml up
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Discord Command 5-Part Pattern:**

```python
# 1. Protocol (TypedDict)
class CostProtocol(TypedDict):
    field1: str
    field2: int

# 2. Frozen dataclasses
@dataclass(frozen=True)
class CostEmbedField:
    name: str
    value: str

@dataclass(frozen=True)
class CostEmbedData:
    title: str
    color: int
    fields: list[CostEmbedField]

# 3. Builder function
def build_cost_data(...) -> CostEmbedData:
    ...

# 4. to_discord_embed() converter
def to_discord_embed(data: CostEmbedData) -> dict:
    ...

# 5. Callback function
async def cost_callback(interaction: discord.Interaction, ...) -> None:
    ...
```

---

## 4. Binding Decisions

> **These decisions are MANDATORY and NON-NEGOTIABLE. Sub-agents must follow them exactly. Any deviation requires parent re-planning.**

### 4.1 Container Versions

| Component | Version | Rationale |
|-----------|---------|-----------|
| Prometheus | `prom/prometheus:v3.3.0` | Librarian research: stable, supports PromQL functions needed |
| Grafana | `grafana/grafana:11.5.0` | Librarian research: current LTS, provisioning API stable |
| Loki | `grafana/loki:3.4.0` | Librarian research: v13 schema + TSDB store support |
| Promtail | `grafana/promtail:3.5.8` | **CRITICAL**: 3.6.0+ drops journald support (GitHub issue 19911) |
| Alertmanager | `prom/alertmanager:v0.28.0` | Librarian research: current stable, Discord webhook support |
| node-exporter | `prom/node-exporter:v1.9.0` | Librarian research: systemd collector, textfile collector |
| postgres-exporter | `prometheuscommunity/postgres-exporter:v0.17.1` | Librarian research: PG16 compatible, pg_monitor support |
| redis-exporter | `oliver006/redis_exporter:v1.67.0` | Librarian research: Redis 7.x compatible |

### 4.2 Network and Ports

| Decision | Value | Source |
|----------|-------|--------|
| Docker network | `guinevere-net` (external) | Existing infrastructure |
| Prometheus port | `127.0.0.1:9090` | ObsSpec, existing Caddy config |
| Grafana port | `127.0.0.1:3000` | ObsSpec, existing Caddy config |
| Loki port | `127.0.0.1:3100` | ObsSpec |
| Alertmanager port | `127.0.0.1:9093` | ObsSpec |
| node-exporter port | `127.0.0.1:9100` | Standard |
| postgres-exporter port | `127.0.0.1:9187` | Standard |
| redis-exporter port | `127.0.0.1:9121` | Standard |
| All port bindings | `127.0.0.1:HOST:CONTAINER` | Security policy (no public exposure) |

### 4.3 Configuration Decisions

| Decision | Value | Source |
|----------|-------|--------|
| Scrape interval | `15s` | ObsSpec section 4 |
| Metric prefix | `guinevere_` | ObsSpec section 4.1 |
| Prometheus retention | `30d` / `15GB` | Librarian recommendation |
| Loki retention | `720h` (30 days) | ObsSpec |
| Loki schema | `v13` + TSDB store | Librarian research |
| Grafana provisioning | `datasources.yml` + `dashboards.yml` | Standard pattern |
| Dashboard format | JSON files at `monitoring/grafana/dashboards/` | ObsSpec section 9, Appendix E |
| Alert rules format | Prometheus YAML at `monitoring/prometheus/rules/` | ObsSpec section 8 |
| Exporters | Docker containers (not systemd) for postgres/redis; node-exporter in Docker with `pid: host` | Librarian research |

### 4.4 Security Decisions

| Decision | Value | Source |
|----------|-------|--------|
| Sentry `send_default_pii` | `false` (MANDATORY) | ObsSpec Appendix G, **BLOCKING** rule |
| Alert tone | Neutral incident-command ONLY | ObsSpec section 2.2, Incident Response spec |
| Discord webhook URL | Via SOPS encrypted | Security policy |
| Sentry DSN | Via SOPS encrypted | Security policy |
| Grafana admin password | Via SOPS encrypted | Security policy |
| postgres_exporter DB password | Via SOPS encrypted | Security policy |

### 4.5 Discord UX Decisions

| Decision | Value | Source |
|----------|-------|--------|
| `/cost` embed color | `0x6B21A8` (purple) | DiscordUXSpec |
| `/budget` embed color | `0x059669` (teal) | Finance convention |
| Command pattern | 5-part (Protocol, frozen dataclass, builder, converter, callback) | Existing codebase pattern |
| Auth guard | `is_faiz_interaction` | Existing pattern |
| Deferred response | `_defer_ephemeral` | Existing pattern |

### 4.6 Evidence and Path Decisions

| Decision | Value | Source |
|----------|-------|--------|
| Evidence root | `docs/setup-evidence/P8/STEP-P8-{NNN}/` | Convention |
| Research reports root | `research-reports/P8/` | Convention |
| Monitoring configs root | `monitoring/` | New directory |
| Systemd units root | `systemd/` | Existing directory |

---

## 5. Master Todo (23 Steps)

| Step | Name | Type | Batch | Parallel Group | Est. Duration |
|------|------|------|-------|----------------|---------------|
| P8-001 | Prometheus Docker Setup | Config + Docker | 1 | parallel | medium |
| P8-002 | node_exporter | Config + Docker | 1 | parallel | low |
| P8-003 | postgres_exporter | Config + Docker | 1 | parallel | medium |
| P8-004 | redis_exporter | Config + Docker | 1 | parallel | medium |
| P8-005 | Scrape Configs | Config | 2 | parallel | low |
| P8-006 | Grafana Docker Setup | Config + Docker | 2 | parallel | low |
| P8-007 | Datasource Provisioning | Config | 2 | parallel | low |
| P8-008 | Dashboard Provisioning | Config + JSON | 3 | parallel | high |
| P8-009 | Loki Docker Setup | Config + Docker | 3 | parallel | medium |
| P8-010 | Promtail Setup | Config + Docker | 3 | parallel | medium |
| P8-011 | Log Pipeline Test | Verification | 4 | parallel (with 012) | medium |
| P8-012 | Sentry SDK Integration | Python code | 4 | parallel (with 011) | medium |
| P8-013 | Sentry Scrubber (PII) | Python code | 4 | sequential (after 012) | medium |
| P8-014 | Alert Rules | Config YAML | 5 | parallel (with 015) | medium |
| P8-015 | SEV Routing Matrix | Config YAML | 5 | parallel (with 014) | medium |
| P8-016 | Alert Test | Verification | 5 | sequential (after 014+015) | medium |
| P8-017 | /cost Discord Command | Python code | 6 | parallel (with 018,019) | medium |
| P8-018 | /budget Discord Command | Python code | 6 | parallel (with 017,019) | medium |
| P8-019 | Monthly Cost Report | Python code | 6 | parallel (with 017,018) | medium |
| P8-020 | Backup Monitoring | Config + Script | 7 | parallel (with 021) | low |
| P8-021 | guinevere-monitoring.service | systemd unit | 7 | parallel (with 020) | low |
| P8-022 | MVP Acceptance Full Run | Verification | 7 | sequential (after ALL) | high |
| P8-023 | Faiz Sign-off | Manual gate | Final | — | manual |

---

## 6. Dependency Map + Parallelism

### 6.1 Visual Dependency Graph

```
Batch 1 -----------------------------------------------------------------
  P8-001 (Prometheus)  --+
  P8-002 (node-exp)    --+  ALL PARALLEL
  P8-003 (pg-exp)      --+  No inter-dependencies
  P8-004 (redis-exp)   --+
         |
         v ALL MUST PASS
Batch 2 -----------------------------------------------------------------
  P8-005 (Scrape)      --+
  P8-006 (Grafana)     --+  ALL PARALLEL
  P8-007 (Datasource)  --+  Scrape config references exporters from Batch 1
         |
         v ALL MUST PASS
Batch 3 -----------------------------------------------------------------
  P8-008 (Dashboards)  --+
  P8-009 (Loki)        --+  ALL PARALLEL
  P8-010 (Promtail)    --+  Independent of each other
         |
         v ALL MUST PASS
Batch 4 -----------------------------------------------------------------
  P8-011 (Log Test)    --+
  P8-012 (Sentry Init) --+  011 parallel with 012
  P8-013 (Sentry Scrub)--+  013 sequential after 012
         |
         v ALL MUST PASS
Batch 5 -----------------------------------------------------------------
  P8-014 (Alert Rules) --+
  P8-015 (SEV Routing) --+  014+015 parallel
  P8-016 (Alert Test)  --+  016 sequential after 014+015
         |
         v ALL MUST PASS
Batch 6 -----------------------------------------------------------------
  P8-017 (/cost)       --+
  P8-018 (/budget)     --+  ALL PARALLEL
  P8-019 (Monthly Rpt) --+  Independent Discord commands
         |
         v ALL MUST PASS
Batch 7 -----------------------------------------------------------------
  P8-020 (Backup Mon)  --+  020+021 parallel
  P8-021 (systemd)     --+
         |
         v 020+021 MUST PASS
  P8-022 (MVP Accept)  ----  Sequential after ALL prior steps
         |
         v P8-022 MUST PASS
  P8-023 (Faiz Sign)   ----  Final manual gate
```

### 6.2 Parallelism Rules

| Rule | Description |
|------|-------------|
| Within-batch parallel | Steps marked `parallel` can fire simultaneously with independent sub-agents |
| Within-batch sequential | Steps marked `sequential` must wait for their dependency within the same batch |
| Cross-batch gate | ALL steps in batch N must PASS before ANY step in batch N+1 begins |
| Shared file ownership | When multiple steps touch the same file, one step owns creation; others verify |
| Batch 6 special | P8-017, P8-018, P8-019 all touch `bot.py` and `commands.py` — handle as sequential within batch to avoid collision |

### 6.3 Critical Path

```
P8-001 -> P8-005 -> P8-008 -> P8-012 -> P8-013 -> P8-014 -> P8-016 -> P8-017 -> P8-022 -> P8-023
```

The critical path runs through Prometheus setup, scrape config, dashboards, Sentry, scrubber, alert rules, alert test, /cost, MVP acceptance, sign-off.

---

## 7. Collision Scan

### 7.1 Shared Files and Resources

| File/Resource | Steps That Touch It | Collision Type | Resolution |
|---------------|---------------------|----------------|------------|
| `monitoring/compose.monitoring.yml` | P8-001, 002, 003, 004, 006, 009, 010 | Same source file | **P8-001 creates the FULL file with ALL services.** P8-002..004, 006, 009, 010 verify their respective service configs exist and are correct. No multi-step editing. |
| `monitoring/prometheus/prometheus.yml` | P8-001, 005 | Same source file | P8-001 creates base config with self-scrape. P8-005 appends application-specific scrape targets. |
| `src/discord/bot.py` | P8-017, 018, 019 | Same source file | Sequential within Batch 6. P8-017 wires first, P8-018 appends, P8-019 appends. Each reads current state before editing. |
| `src/discord/commands.py` | P8-017, 018, 019 | Same source file | Sequential within Batch 6. Same resolution as bot.py. |
| `src/observability/sentry_integration.py` | P8-012, 013 | Same source file | Sequential: P8-012 creates the file, P8-013 adds scrubber to the same file. |
| `monitoring/alertmanager/alertmanager.yml` | P8-014, 015 | Same source file | P8-014 creates full config with alert rules. P8-015 adds routing refinements. Sequential within Batch 5. |
| `monitoring/prometheus/rules/` | P8-014, 020 | Same directory | Sequential: P8-014 creates base rules file. P8-020 adds backup alert rule (new file or append). |
| `systemd/guinevere-monitoring.service` | P8-021 | Single owner | No collision. |
| `docs/setup-evidence/P8/` | ALL steps | Shared directory | Each step writes to its own `STEP-P8-{NNN}/` subdirectory. No cross-step file sharing. |
| `PROGRESS.md` | P8-022 | Parent-only | Updated by parent after MVP acceptance run. Not delegated to sub-agents. |
| `monitoring/grafana/dashboards/` | P8-008 | Single owner | No collision. |
| `src/discord/notifications.py` | P8-015 | Single owner | May need SEV routing additions. |
| `src/core/main.py` | P8-012 | Single owner | Sentry init added to lifespan. |

### 7.2 Resolution Strategy Summary

1. **compose.monitoring.yml**: P8-001 is the SOLE CREATOR. It writes the complete file with all 8 services. Subsequent steps (002, 003, 004, 006, 009, 010) are VERIFICATION-ONLY — they confirm their service config is present and correct.
2. **prometheus.yml**: P8-001 creates base; P8-005 is the SOLE MODIFIER adding scrape targets.
3. **bot.py + commands.py**: Sequential within Batch 6. P8-017 first, P8-018 second, P8-019 third.
4. **alertmanager**: P8-014 creates; P8-015 modifies. Sequential within Batch 5.
5. **Evidence directories**: Each step uses isolated `STEP-P8-{NNN}/` subdirectory.
6. **Shared docs (PROGRESS.md, CHECKLIST.md)**: Parent-only writes.

### 7.3 No-Collision Verification

Before each batch begins, parent must verify:

- No two parallel sub-agents write to the same file
- Sequential steps within a batch have clear handoff points
- Shared docs are parent-owned only

---

## 8. Batch Execution Plan (7 Batches)

### Batch 1: Monitoring Foundation (P8-001..P8-004)

| Attribute | Value |
|-----------|-------|
| Steps | P8-001, P8-002, P8-003, P8-004 |
| Parallelism | ALL PARALLEL |
| Shared Files | `monitoring/compose.monitoring.yml` (P8-001 creates, others verify) |
| Estimated Duration | 30-45 min |
| Entry Criteria | P7 complete, monitoring directories created, Docker + Docker Compose available |
| Exit Criteria | All 8 monitoring containers running, all exporter endpoints returning metrics |

**Execution flow:**

1. P8-001 sub-agent creates `compose.monitoring.yml` with ALL services, `prometheus.yml` base, `.env` file. Runs `docker compose up -d`. Verifies Prometheus healthy.
2. P8-002 sub-agent (parallel) verifies node-exporter container running, metrics endpoint accessible, systemd collector enabled.
3. P8-003 sub-agent (parallel) verifies postgres-exporter, creates DB role, checks metrics endpoint.
4. P8-004 sub-agent (parallel) verifies redis-exporter, creates Redis ACL, checks metrics endpoint.

### Batch 2: Scrape + Grafana (P8-005..P8-007)

| Attribute | Value |
|-----------|-------|
| Steps | P8-005, P8-006, P8-007 |
| Parallelism | ALL PARALLEL |
| Shared Files | `prometheus.yml` (P8-005 modifies), Grafana provisioning (P8-007 creates) |
| Estimated Duration | 20-30 min |
| Entry Criteria | Batch 1 ALL PASS |
| Exit Criteria | All scrape targets UP, Grafana healthy, datasources provisioned |

### Batch 3: Dashboards + Logging (P8-008..P8-010)

| Attribute | Value |
|-----------|-------|
| Steps | P8-008, P8-009, P8-010 |
| Parallelism | ALL PARALLEL |
| Shared Files | Dashboard JSONs (P8-008), Loki config (P8-009), Promtail config (P8-010) |
| Estimated Duration | 45-60 min |
| Entry Criteria | Batch 2 ALL PASS |
| Exit Criteria | Dashboards loaded in Grafana, Loki ready, Promtail shipping logs |

### Batch 4: Log Verification + Sentry (P8-011..P8-013)

| Attribute | Value |
|-----------|-------|
| Steps | P8-011, P8-012, P8-013 |
| Parallelism | P8-011 parallel with P8-012; P8-013 sequential after P8-012 |
| Shared Files | `sentry_integration.py` (P8-012 creates, P8-013 modifies) |
| Estimated Duration | 30-45 min |
| Entry Criteria | Batch 3 ALL PASS |
| Exit Criteria | Log pipeline verified end-to-end, Sentry integrated with scrubber |

### Batch 5: Alerting (P8-014..P8-016)

| Attribute | Value |
|-----------|-------|
| Steps | P8-014, P8-015, P8-016 |
| Parallelism | P8-014 parallel with P8-015; P8-016 sequential after both |
| Shared Files | Alert rules (P8-014), Alertmanager config (P8-015) |
| Estimated Duration | 30-45 min |
| Entry Criteria | Batch 4 ALL PASS |
| Exit Criteria | All alert rules loaded, SEV routing verified, all SEV levels tested |

### Batch 6: FinOps Commands (P8-017..P8-019)

| Attribute | Value |
|-----------|-------|
| Steps | P8-017, P8-018, P8-019 |
| Parallelism | SEQUENTIAL within batch (shared bot.py/commands.py files) |
| Shared Files | `bot.py`, `commands.py`, new command files |
| Estimated Duration | 45-60 min |
| Entry Criteria | Batch 5 ALL PASS |
| Exit Criteria | /cost, /budget commands working, monthly report task configured |

### Batch 7: Monitoring Service + MVP Gate (P8-020..P8-023)

| Attribute | Value |
|-----------|-------|
| Steps | P8-020, P8-021, P8-022, P8-023 |
| Parallelism | P8-020 parallel with P8-021; P8-022 sequential after ALL; P8-023 final manual |
| Shared Files | Backup textfile collector (P8-020), systemd unit (P8-021) |
| Estimated Duration | 60-90 min |
| Entry Criteria | Batch 6 ALL PASS |
| Exit Criteria | Backup monitoring active, systemd service running, MVP acceptance PASS, Faiz sign-off |

---

## 9. Per-Step Implementation Design + Scaffolds (P8-001..P8-023)

---

### P8-001: Prometheus Docker Setup

**Description:** Create the master `compose.monitoring.yml` with ALL monitoring services (Prometheus, Alertmanager, Grafana, Loki, Promtail, node-exporter, postgres-exporter, redis-exporter). Create base `prometheus.yml` with self-scrape. Create `monitoring/.env` with port bindings and version tags. Docker compose up, verify Prometheus healthy.

**Files to create:**

- `monitoring/compose.monitoring.yml` — Full compose file with all 8 services
- `monitoring/prometheus/prometheus.yml` — Base scrape config (self-scrape only)
- `monitoring/.env` — Environment variables (ports, versions, passwords)
- `monitoring/.env.enc` — SOPS-encrypted version of `.env` (contains secrets)

**Implementation notes:**

The compose file must include ALL services because this avoids multi-step file editing collision. Each service follows the existing pattern:

- `container_name: guinevere-{service}`
- `restart: unless-stopped`
- `ports: "127.0.0.1:HOST:CONTAINER"`
- `networks: [guinevere-net]`
- External network: `guinevere-net`

Services to include in compose.monitoring.yml:

```yaml
services:
  prometheus:
    container_name: guinevere-prometheus
    image: prom/prometheus:v3.3.0
    ports: ["127.0.0.1:9090:9090"]
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./prometheus/rules:/etc/prometheus/rules:ro
      - /home/guinevere/data/prometheus:/prometheus
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.path=/prometheus"
      - "--storage.tsdb.retention.time=30d"
      - "--storage.tsdb.retention.size=15GB"
      - "--web.enable-lifecycle"

  alertmanager:
    container_name: guinevere-alertmanager
    image: prom/alertmanager:v0.28.0
    ports: ["127.0.0.1:9093:9093"]
    volumes:
      - ./alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro

  grafana:
    container_name: guinevere-grafana
    image: grafana/grafana:11.5.0
    ports: ["127.0.0.1:3000:3000"]
    volumes:
      - ./grafana/provisioning:/etc/grafana/provisioning:ro
      - ./grafana/dashboards:/var/lib/grafana/dashboards:ro
      - /home/guinevere/data/grafana:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}

  loki:
    container_name: guinevere-loki
    image: grafana/loki:3.4.0
    ports: ["127.0.0.1:3100:3100"]
    volumes:
      - ./loki/loki-config.yml:/etc/loki/local-config.yml:ro
      - /home/guinevere/data/loki:/loki

  promtail:
    container_name: guinevere-promtail
    image: grafana/promtail:3.5.8
    volumes:
      - ./promtail/promtail-config.yml:/etc/promtail/config.yml:ro
      - /var/log/journal:/var/log/journal:ro
      - /run/log/journal:/run/log/journal:ro
      - /var/log:/var/log:ro
    pid: host

  node-exporter:
    container_name: guinevere-node-exporter
    image: prom/node-exporter:v1.9.0
    ports: ["127.0.0.1:9100:9100"]
    pid: host
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
      - ./node-exporter/textfile:/textfile:ro
    command:
      - "--path.procfs=/host/proc"
      - "--path.sysfs=/host/sys"
      - "--path.rootfs=/rootfs"
      - "--collector.systemd"
      - "--collector.textfile.directory=/textfile"

  postgres-exporter:
    container_name: guinevere-postgres-exporter
    image: prometheuscommunity/postgres-exporter:v0.17.1
    ports: ["127.0.0.1:9187:9187"]
    environment:
      - DATA_SOURCE_NAME=postgresql://postgres_exporter:${PG_EXPORTER_PASSWORD}@host.docker.internal:5433/guinevere?sslmode=disable

  redis-exporter:
    container_name: guinevere-redis-exporter
    image: oliver006/redis_exporter:v1.67.0
    ports: ["127.0.0.1:9121:9121"]
    environment:
      - REDIS_ADDR=redis://host.docker.internal:6380
      - REDIS_PASSWORD=${REDIS_EXPORTER_PASSWORD}

networks:
  guinevere-net:
    external: true
```

Base `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]
```

**Dependencies:** None (first step)

**Verification Scaffold:**

| Field | Value |
|-------|-------|
| **Expected Files** | `monitoring/compose.monitoring.yml`, `monitoring/prometheus/prometheus.yml`, `monitoring/.env`, `monitoring/.env.enc` |
| **Forbidden Patterns** | `as any`, `@ts-ignore`, plaintext passwords in non-`.enc` files, `latest` tag in image references, port bindings without `127.0.0.1:` prefix |
| **Required Commands** | `docker compose -f monitoring/compose.monitoring.yml config` exit 0; `docker compose -f monitoring/compose.monitoring.yml up -d` exit 0; `curl -s http://127.0.0.1:9090/-/healthy` returns `Prometheus Server is Healthy.`; `docker ps --filter "name=guinevere-" --format "{{.Names}} {{.Status}}"` all containers Up |
| **Evidence Requirements** | `docs/setup-evidence/P8/STEP-P8-001/verification.md`, `docs/setup-evidence/P8/STEP-P8-001/scaffold-check.md` |
| **Hard Rejection Criteria** | compose_monitoring.yml missing any of the 8 services = FAIL; Prometheus not healthy = FAIL; Any container not running = FAIL; Plaintext secrets in non-encrypted files = FAIL; Promtail image tag != 3.5.8 = FAIL |

---

### P8-002: node_exporter

**Description:** Verify node-exporter container running from P8-001 compose. Verify metrics endpoint accessible. Verify systemd collector enabled and textfile directory mounted.

**Files to verify:**

- `monitoring/compose.monitoring.yml` — node-exporter service section (READ ONLY, do not modify)
- `monitoring/node-exporter/textfile/` — textfile collector directory (create if missing)

**Implementation notes:**

- node-exporter runs with `pid: host` to access host process metrics
- Systemd collector is enabled via `--collector.systemd` flag
- Textfile directory at `monitoring/node-exporter/textfile/` is mounted read-only
- Key metrics to verify: `node_cpu_seconds_total`, `node_memory_MemTotal_bytes`, `node_filesystem_avail_bytes`, `node_systemd_unit_status`

**Dependencies:** P8-001 (compose_monitoring.yml with node-exporter service)

**Verification Scaffold:**

| Field | Value |
|-------|-------|
| **Expected Files** | `monitoring/node-exporter/textfile/` directory exists |
| **Forbidden Patterns** | Modifications to `compose_monitoring.yml` (this step is verify-only for compose) |
| **Required Commands** | `docker ps --filter "name=guinevere-node-exporter"` contains Up; `curl -s http://127.0.0.1:9100/metrics` returns metric lines; `curl -s http://127.0.0.1:9100/metrics | grep node_cpu_seconds_total` returns matches; `curl -s http://127.0.0.1:9100/metrics | grep node_systemd_unit_status` returns matches |
| **Evidence Requirements** | `docs/setup-evidence/P8/STEP-P8-002/verification.md`, `docs/setup-evidence/P8/STEP-P8-002/scaffold-check.md` |
| **Hard Rejection Criteria** | node-exporter container not running = FAIL; /metrics endpoint not accessible = FAIL; systemd collector metrics missing = FAIL; textfile directory missing = FAIL |

---

### P8-003: postgres_exporter

**Description:** Verify postgres-exporter container running with DATA_SOURCE_NAME. Create postgres_exporter DB role with pg_monitor grant. Verify metrics endpoint returns PostgreSQL stats.

**Files to verify:**

- `monitoring/compose_monitoring.yml` — postgres-exporter service section (READ ONLY)

**Implementation notes:**

- PostgreSQL canonical port: 5433
- Connection string uses `host.docker.internal:5433` to reach host PostgreSQL from Docker
- DB role creation SQL:

```sql
CREATE ROLE postgres_exporter WITH LOGIN PASSWORD '<from-sops>';
GRANT pg_monitor TO postgres_exporter;
```

- `pg_monitor` role provides read access to all statistics views needed by the exporter
- Key metrics: `pg_stat_database_tup_fetched`, `pg_stat_activity_count`, `pg_database_size_bytes`

**Dependencies:** P8-001 (compose file), PostgreSQL running on port 5433

**Verification Scaffold:**

| Field | Value |
|-------|-------|
| **Expected Files** | No new files (DB role creation only) |
| **Forbidden Patterns** | Modifications to compose file; plaintext passwords in any file; `GRANT ALL` or superuser grants |
| **Required Commands** | `docker ps --filter "name=guinevere-postgres-exporter"` contains Up; `curl -s http://127.0.0.1:9187/metrics | grep pg_stat_database` returns matches; `psql -h 127.0.0.1 -p 5433 -U guinevere -d guinevere -c "SELECT rolname FROM pg_roles WHERE rolname='postgres_exporter'"` returns postgres_exporter |
| **Evidence Requirements** | `docs/setup-evidence/P8/STEP-P8-003/verification.md`, `docs/setup-evidence/P8/STEP-P8-003/scaffold-check.md` |
| **Hard Rejection Criteria** | postgres-exporter container not running = FAIL; /metrics not returning pg_stat data = FAIL; DB role missing = FAIL; pg_monitor grant missing = FAIL; exporter has superuser = FAIL |

---

### P8-004: redis_exporter

**Description:** Verify redis-exporter container running with REDIS_ADDR. Create Redis ACL for exporter user. Verify metrics endpoint returns Redis stats.

**Files to verify:**

- `monitoring/compose_monitoring.yml` — redis-exporter service section (READ ONLY)

**Implementation notes:**

- Redis canonical port: 6380
- Connection: `redis://host.docker.internal:6380`
- Redis ACL creation:

```
ACL SETUSER redis-exporter on >password ~* +info +ping +client|getname +config|get +slowlog +latency +memory +dbsize +command +cluster|info
```

- The ACL grants only read-only commands needed by the exporter
- Key metrics: `redis_connected_clients`, `redis_memory_used_bytes`, `redis_commands_processed_total`, `redis_keyspace_hits_total`

**Dependencies:** P8-001 (compose file), Redis running on port 6380

**Verification Scaffold:**

| Field | Value |
|-------|-------|
| **Expected Files** | No new files (ACL creation via redis-cli only) |
| **Forbidden Patterns** | Modifications to compose file; plaintext passwords; `+@all` or overly broad ACL grants |
| **Required Commands** | `docker ps --filter "name=guinevere-redis-exporter"` contains Up; `curl -s http://127.0.0.1:9121/metrics | grep redis_memory_used_bytes` returns matches; `redis-cli -p 6380 ACL LIST | grep redis-exporter` returns ACL entry |
| **Evidence Requirements** | `docs/setup-evidence/P8/STEP-P8-004/verification.md`, `docs/setup-evidence/P8/STEP-P8-004/scaffold-check.md` |
| **Hard Rejection Criteria** | redis-exporter container not running = FAIL; /metrics not returning redis data = FAIL; ACL missing or overly permissive = FAIL |

---

### P8-005: Scrape Configs

**Description:** Update `monitoring/prometheus/prometheus.yml` with full scrape targets for all monitored services. Reload Prometheus and verify all targets UP.

**Files to modify:**

- `monitoring/prometheus/prometheus.yml` — Add scrape targets for all services

**Implementation notes:**

Full scrape config to add:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "/etc/prometheus/rules/*.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets: ["alertmanager:9093"]

scrape_configs:
  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]

  - job_name: "node"
    static_configs:
      - targets: ["node-exporter:9100"]

  - job_name: "postgresql"
    static_configs:
      - targets: ["postgres-exporter:9187"]

  - job_name: "redis"
    static_configs:
      - targets: ["redis-exporter:9121"]

  - job_name: "fastapi"
    metrics_path: "/metrics"
    static_configs:
      - targets: ["host.docker.internal:8000"]

  - job_name: "loki"
    static_configs:
      - targets: ["loki:3100"]

  - job_name: "alertmanager"
    static_configs:
      - targets: ["alertmanager:9093"]
```

Note: Exporter service names (node-exporter, postgres-exporter, redis-exporter) use Docker Compose service names, resolvable within `guinevere-net`. FastAPI uses `host.docker.internal` to reach the host-bound application on port 8000.

Reload command: `curl -X POST http://127.0.0.1:9090/-/reload`

**Dependencies:** P8-001 (base prometheus.yml), P8-002/003/004 (exporters running)

**Verification Scaffold:**

| Field | Value |
|-------|-------|
| **Expected Files** | `monitoring/prometheus/prometheus.yml` (modified) |
| **Forbidden Patterns** | `latest` tags; plaintext secrets; scrape targets pointing to public IPs; `honor_labels: true` without justification |
| **Required Commands** | `curl -X POST http://127.0.0.1:9090/-/reload` exit 0; `curl -s http://127.0.0.1:9090/api/v1/targets` shows all targets with health ok and state active; Target count shows all 7 job names (prometheus, node, postgresql, redis, fastapi, loki, alertmanager) |
| **Evidence Requirements** | `docs/setup-evidence/P8/STEP-P8-005/verification.md`, `docs/setup-evidence/P8/STEP-P8-005/scaffold-check.md` |
| **Hard Rejection Criteria** | Any target DOWN for more than 60s after reload = FAIL; Fewer than 7 scrape jobs = FAIL; prometheus.yml syntax error = FAIL; FastAPI target unreachable = WARN (document, may need guinevere-core service running) |

---

### P8-006: Grafana Docker Setup

**Description:** Verify Grafana container running from P8-001 compose. Verify health endpoint. Admin password set via SOPS-encrypted env var.

**Files to verify:**

- `monitoring/compose_monitoring.yml` — grafana service section (READ ONLY)
- `monitoring/.env` — `GRAFANA_ADMIN_PASSWORD` present (READ ONLY)

**Implementation notes:**

- Grafana listens on port 3000, bound to 127.0.0.1
- Admin password set via `GF_SECURITY_ADMIN_PASSWORD` environment variable
- Existing Caddy config already routes `:3443` to `:3000` (Tailscale-only)
- Health check: `GET /api/health` returns JSON with database ok
- Volume: `/home/guinevere/data/grafana` for persistent storage

**Dependencies:** P8-001 (compose file with grafana service)

**Verification Scaffold:**

| Field | Value |
|-------|-------|
| **Expected Files** | No new files (verification only) |
| **Forbidden Patterns** | Modifications to compose file; plaintext admin password in non-encrypted files; `GF_AUTH_ANONYMOUS_ENABLED=true` without justification |
| **Required Commands** | `docker ps --filter "name=guinevere-grafana"` contains Up; `curl -s http://127.0.0.1:3000/api/health` returns JSON with database ok; `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3000/login` returns 200 |
| **Evidence Requirements** | `docs/setup-evidence/P8/STEP-P8-006/verification.md`, `docs/setup-evidence/P8/STEP-P8-006/scaffold-check.md` |
| **Hard Rejection Criteria** | Grafana container not running = FAIL; Health endpoint not returning database ok = FAIL; Admin password not set (default admin/admin works) = FAIL |

---

### P8-007: Datasource Provisioning

**Description:** Create Grafana datasource provisioning file with Prometheus (default), Loki, and PostgreSQL datasources.

**Files to create:**

- `monitoring/grafana/provisioning/datasources/datasources.yml` — Datasource provisioning config

**Implementation notes:**

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
    jsonData:
      timeInterval: "15s"

  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    editable: false
    jsonData:
      maxLines: 1000

  - name: PostgreSQL
    type: postgres
    access: proxy
    url: host.docker.internal:5433
    database: guinevere
    user: grafana_reader
    editable: false
    secureJsonData:
      password: "${GRAFANA_PG_PASSWORD}"
    jsonData:
      sslmode: "disable"
      postgresVersion: 1600
```

- Prometheus URL uses Docker Compose service name `prometheus:9090` (internal network)
- Loki URL uses Docker Compose service name `loki:3100`
- PostgreSQL uses `host.docker.internal:5433` for host DB access
- `grafana_reader` is a read-only PostgreSQL role (must be created separately if not existing)
- Password for PostgreSQL datasource stored in env variable, injected by Grafana provisioning

**Dependencies:** P8-001 (Grafana running), P8-005 (Prometheus scraping), P8-009 (Loki running)

**Verification Scaffold:**

| Field | Value |
|-------|-------|
| **Expected Files** | `monitoring/grafana/provisioning/datasources/datasources.yml` |
| **Forbidden Patterns** | Plaintext passwords in YAML; `editable: true` on provisioned datasources; `access: direct` (must use proxy) |
| **Required Commands** | YAML syntax valid (parse with python3 yaml module) exit 0; `curl -s -u admin:$GF_ADMIN_PW http://127.0.0.1:3000/api/datasources` returns JSON array with 3 datasources; Restart grafana: `docker compose -f monitoring/compose_monitoring.yml restart grafana` exit 0 |
| **Evidence Requirements** | `docs/setup-evidence/P8/STEP-P8-007/verification.md`, `docs/setup-evidence/P8/STEP-P8-007/scaffold-check.md` |
| **Hard Rejection Criteria** | YAML syntax error = FAIL; Fewer than 3 datasources provisioned = FAIL; Prometheus not set as default = FAIL; Plaintext passwords = FAIL |

---

### P8-008: Dashboard Provisioning

**Description:** Create Grafana dashboard provisioning config and JSON dashboard files for all 6 required dashboards.

**Files to create:**

- `monitoring/grafana/provisioning/dashboards/dashboards.yml` — Dashboard provisioning config
- `monitoring/grafana/dashboards/guinevere-infrastructure.json` — Node metrics (CPU, memory, disk, network, systemd)
- `monitoring/grafana/dashboards/guinevere-database-memory.json` — PostgreSQL + Redis metrics
- `monitoring/grafana/dashboards/guinevere-agent-loop.json` — Agent loop state, phase duration, subagent counts
- `monitoring/grafana/dashboards/guinevere-llm-cost-latency.json` — LLM metrics, cost tracking, latency
- `monitoring/grafana/dashboards/guinevere-persona-safety.json` — Safety metrics, SEV counts, consent status
- `monitoring/grafana/dashboards/guinevere-finops.json` — Cost tracking, budget, projections

**Implementation notes:**

Dashboard provisioning config:

```yaml
apiVersion: 1

providers:
  - name: "Guinevere Dashboards"
    orgId: 1
    folder: "Guinevere"
    type: file
    disableDeletion: false
    editable: true
    updateIntervalSeconds: 30
    options:
      path: /var/lib/grafana/dashboards
      foldersFromFilesStructure: false
```

Each dashboard JSON file follows this structure:

```json
{
  "annotations": { "list": [] },
  "editable": true,
  "fiscalYearStartMonth": 0,
  "graphTooltip": 1,
  "id": null,
  "links": [],
  "panels": [ ],
  "schemaVersion": 39,
  "tags": ["guinevere"],
  "templating": { "list": [] },
  "time": { "from": "now-6h", "to": "now" },
  "timepicker": {},
  "timezone": "Asia/Jakarta",
  "title": "Dashboard Title",
  "uid": "unique-uid",
  "version": 1
}
```

**Panel specifications per dashboard:**

1. **guinevere-infrastructure.json** (ObsSpec section 9.2.1):
   - CPU Usage (gauge): `100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)`
   - Memory Usage (gauge): `(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100`
   - Disk Usage (table): `node_filesystem_avail_bytes{mountpoint!~"/run.*"}`
   - Network I/O (timeseries): `rate(node_network_receive_bytes_total[5m])`
   - Systemd Service Status (stat): `node_systemd_unit_status{state="active"}`
   - Load Average (timeseries): `node_load1`, `node_load5`, `node_load15`

2. **guinevere-database-memory.json** (ObsSpec section 9.2.2):
   - PG Active Connections (timeseries): `pg_stat_activity_count`
   - PG Database Size (stat): `pg_database_size_bytes`
   - PG Cache Hit Ratio (gauge): `pg_stat_database_blks_hit / (pg_stat_database_blks_hit + pg_stat_database_blks_read)`
   - Redis Memory Used (timeseries): `redis_memory_used_bytes`
   - Redis Connected Clients (stat): `redis_connected_clients`
   - Redis Hit Rate (gauge): `redis_keyspace_hits_total / (redis_keyspace_hits_total + redis_keyspace_misses_total)`

3. **guinevere-agent-loop.json** (ObsSpec section 9.2.3):
   - Agent Loop State (stat): `guinevere_agent_loop_state`
   - Phase Duration (timeseries): `guinevere_phase_duration_seconds`
   - Subagent Count (timeseries): `guinevere_active_subagents`
   - Task Queue Depth (stat): `guinevere_task_queue_depth`

4. **guinevere-llm-cost-latency.json** (ObsSpec section 9.2.4):
   - LLM Request Latency (heatmap): `guinevere_llm_request_duration_seconds`
   - Token Usage (timeseries): `guinevere_llm_tokens_total`
   - Cost Per Hour (timeseries): `guinevere_llm_cost_usd_total`
   - Model Distribution (pie): `guinevere_llm_requests_total` by model

5. **guinevere-persona-safety.json** (ObsSpec section 9.2.5):
   - SEV Events (table): `guinevere_sev_events_total` by severity
   - Consent Status (stat): `guinevere_consent_active`
   - Safe Word Triggers (stat): `guinevere_safeword_triggered_total`
   - Hard Stop Events (stat): `guinevere_hardstop_total`

6. **guinevere-finops.json** (ObsSpec section 9.2.6):
   - Monthly Spend (stat): `guinevere_cost_monthly_usd`
   - Budget Remaining (gauge): `guinevere_budget_remaining_usd`
   - Per-Model Cost (table): `guinevere_cost_by_model_usd`
   - Cost Trend (timeseries): `increase(guinevere_cost_monthly_usd[30d])`
   - Projected Monthly (stat): projection based on current rate

**Dependencies:** P8-006 (Grafana running), P8-007 (datasources provisioned)

**Verification Scaffold:**

| Field | Value |
|-------|-------|
| **Expected Files** | `monitoring/grafana/provisioning/dashboards/dashboards.yml`, `monitoring/grafana/dashboards/guinevere-infrastructure.json`, `monitoring/grafana/dashboards/guinevere-database-memory.json`, `monitoring/grafana/dashboards/guinevere-agent-loop.json`, `monitoring/grafana/dashboards/guinevere-llm-cost-latency.json`, `monitoring/grafana/dashboards/guinevere-persona-safety.json`, `monitoring/grafana/dashboards/guinevere-finops.json` |
| **Forbidden Patterns** | Invalid JSON; `"id": <number>` (must be null for provisioning); hardcoded datasource UIDs (use name references); panels referencing non-existent metrics |
| **Required Commands** | Each JSON file validates with `python3 -c "import json; json.load(open('FILE'))"` exit 0; `curl -s -u admin:$PW http://127.0.0.1:3000/api/search?tag=guinevere` returns JSON array with 6 dashboards; `curl -s -u admin:$PW http://127.0.0.1:3000/api/folders` contains Guinevere folder |
| **Evidence Requirements** | `docs/setup-evidence/P8/STEP-P8-008/verification.md`, `docs/setup-evidence/P8/STEP-P8-008/scaffold-check.md` |
| **Hard Rejection Criteria** | Any JSON file invalid = FAIL; Fewer than 6 dashboards = FAIL; Dashboard provisioning config missing = FAIL; Dashboard UIDs not unique = FAIL |

---

### P8-009: Loki Docker Setup

**Description:** Create Loki configuration with schema v13 + TSDB store, 720h retention. Verify container running and ready.

**Files to create:**

- `monitoring/loki/loki-config.yml` — Loki configuration

**Implementation notes:**

```yaml
auth_enabled: false

server:
  http_listen_port: 3100

common:
  path_prefix: /loki
  storage:
    filesystem:
      chunks_directory: /loki/chunks
      rules_directory: /loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory

schema_config:
  configs:
    - from: "2024-01-01"
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h

limits_config:
  retention_period: 720h
  reject_old_samples: true
  reject_old_samples_max_age: 168h
  max_entries_limit_per_query: 5000

compactor:
  working_directory: /loki/compactor
  retention_enabled: true
  delete_request_store: filesystem
```

Key points:

- Schema v13 with TSDB store (modern, efficient)
- Retention: 720h (30 days) per ObsSpec
- Compactor enabled for retention enforcement
- Filesystem storage (single-instance, no S3 needed)
- `auth_enabled: false` (internal network only, Tailscale-gated)

**Dependencies:** P8-001 (compose file with loki service)

**Verification Scaffold:**

| Field | Value |
|-------|-------|
| **Expected Files** | `monitoring/loki/loki-config.yml` |
| **Forbidden Patterns** | `auth_enabled: true` (unnecessary for internal); S3/GCS backend config (use filesystem); retention less than 720h; schema version != v13 |
| **Required Commands** | `docker ps --filter "name=guinevere-loki"` contains Up; `curl -s http://127.0.0.1:3100/ready` returns ready; `curl -s http://127.0.0.1:3100/config` returns YAML config |
| **Evidence Requirements** | `docs/setup-evidence/P8/STEP-P8-009/verification.md`, `docs/setup-evidence/P8/STEP-P8-009/scaffold-check.md` |
| **Hard Rejection Criteria** | Loki container not running = FAIL; /ready not returning ready = FAIL; Schema not v13 = FAIL; Retention not 720h = FAIL; Compactor not enabled = FAIL |

---

### P8-010: Promtail Setup

**Description:** Create Promtail configuration with journal, Docker, and varlogs scrape jobs. CRITICAL: Use Promtail 3.5.8 (3.6.0+ drops journald support).

**Files to create:**

- `monitoring/promtail/promtail-config.yml` — Promtail configuration

**Implementation notes:**

```yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: journal
    journal:
      max_age: 12h
      labels:
        job: systemd-journal
    relabel_configs:
      - source_labels: ["__journal__systemd_unit"]
        target_label: "unit"
      - source_labels: ["__journal__hostname"]
        target_label: "hostname"

  - job_name: docker
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s
    relabel_configs:
      - source_labels: ["__meta_docker_container_name"]
        regex: "/(.*)"
        target_label: "container"
      - source_labels: ["__meta_docker_container_label_com_docker_compose_service"]
        target_label: "service"

  - job_name: varlogs
    static_configs:
      - targets:
          - localhost
        labels:
          job: varlogs
          __path__: /var/log/*.log
    pipeline_stages:
      - match:
          selector: '{filename="/var/log/guinevere*.log"}'
          stages:
            - json:
                expressions:
                  level: level
                  service: service
            - labels:
                level:
                service:
```

**CRITICAL**: The compose file MUST use `grafana/promtail:3.5.8`. Version 3.6.0+ removes the `journal` scrape config entirely (upstream GitHub issue 19911). This is verified in P8-001 compose file.

- Journal logs: systemd unit logs from `/var/log/journal` and `/run/log/journal` (mounted read-only in compose)
- Docker logs: container logs via Docker socket
- Varlogs: `/var/log/*.log` for application logs
- Pipeline stages parse JSON structured logs from guinevere services

**Dependencies:** P8-001 (compose file), P8-009 (Loki running)

**Verification Scaffold:**

| Field | Value |
|-------|-------|
| **Expected Files** | `monitoring/promtail/promtail-config.yml` |
| **Forbidden Patterns** | Promtail version 3.6.0 or higher in compose file; `journal` scrape without `pid: host` in compose; plaintext Loki URL with public IP; missing `positions` config |
| **Required Commands** | `docker ps --filter "name=guinevere-promtail"` contains Up; `docker inspect guinevere-promtail --format "{{.Config.Image}}"` returns `grafana/promtail:3.5.8`; `curl -s -G http://127.0.0.1:3100/loki/api/v1/query_range --data-urlencode 'query={job="systemd-journal"}' --data-urlencode 'limit=5'` returns log entries |
| **Evidence Requirements** | `docs/setup-evidence/P8/STEP-P8-010/verification.md`, `docs/setup-evidence/P8/STEP-P8-010/scaffold-check.md` |
| **Hard Rejection Criteria** | Promtail container not running = FAIL; Image tag != 3.5.8 = CRITICAL FAIL; Journal logs not appearing in Loki = FAIL; Missing `pid: host` in compose = FAIL |

---

### P8-011: Log Pipeline Test

**Description:** End-to-end verification of the log pipeline. Trigger a log event from the guinevere service, verify it appears in Loki and Grafana.

**Files to create:**

- None (verification only, may create test script)

**Implementation notes:**

- Trigger a log event: restart guinevere-core service or trigger a known log line
- Verify in Loki via LogQL: `{service="guinevere-core"} |= "test"` or `{unit="guinevere-core.service"}`
- Verify in Grafana Explore tab: select Loki datasource, run LogQL query
- Verify structured JSON fields parse correctly (level, service, timestamp, message)
- Check that `pipeline_stages` in Promtail correctly extract labels

**Dependencies:** P8-009 (Loki), P8-010 (Promtail)

**Verification Scaffold:**

| Field | Value |
|-------|-------|
| **Expected Files** | Test evidence screenshots/outputs saved to evidence directory |
| **Forbidden Patterns** | N/A (verification step) |
| **Required Commands** | `logger -t guinevere-test "P8-011 log pipeline test"` exit 0; `sleep 5`; `curl -s -G http://127.0.0.1:3100/loki/api/v1/query_range --data-urlencode 'query={unit="guinevere-test"}' --data-urlencode 'limit=5'` returns entries containing P8-011; Verify structured parse: `curl -s -G http://127.0.0.1:3100/loki/api/v1/query_range --data-urlencode 'query={service="guinevere-core"} | json' --data-urlencode 'limit=3'` returns entries with parsed JSON fields |
| **Evidence Requirements** | `docs/setup-evidence/P8/STEP-P8-011/verification.md`, `docs/setup-evidence/P8/STEP-P8-011/scaffold-check.md` |
| **Hard Rejection Criteria** | Test log not appearing in Loki within 30s = FAIL; Structured JSON fields not parsed = FAIL; Grafana Explore tab cannot query Loki = FAIL |

---

### P8-012: Sentry SDK Integration

**Description:** Create Sentry integration module. Initialize sentry_sdk with DSN from SOPS, send_default_pii=False, traces_sample_rate=0.1. Integrate with FastAPI lifespan.

**Files to create:**

- `src/observability/sentry_integration.py` — Sentry initialization and configuration

**Files to modify:**

- `src/core/main.py` — Add Sentry init call in lifespan
- `src/observability/__init__.py` — Export sentry integration

**Implementation notes:**

```python
# src/observability/sentry_integration.py
"""Sentry SDK integration for Guinevere.

Provides error tracking with mandatory PII protection.
send_default_pii=False is a BLOCKING requirement (ObsSpec Appendix G).
"""

import logging
import os

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

logger = logging.getLogger(__name__)

# BLOCKING: This MUST be False. No exceptions.
SEND_DEFAULT_PII: bool = False


def init_sentry(
    dsn: str | None = None,
    environment: str = "production",
    release: str | None = None,
    traces_sample_rate: float = 0.1,
) -> bool:
    """Initialize Sentry SDK with mandatory PII protection.

    Args:
        dsn: Sentry DSN. If None, reads from SENTRY_DSN env var.
             If still None, Sentry is disabled (graceful).
        environment: Deployment environment tag.
        release: Release version tag.
        traces_sample_rate: Fraction of transactions to sample (0.0-1.0).

    Returns:
        True if Sentry initialized, False if disabled.
    """
    if dsn is None:
        dsn = os.environ.get("SENTRY_DSN")

    if not dsn:
        logger.info("Sentry DSN not configured -- error tracking disabled")
        return False

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        traces_sample_rate=traces_sample_rate,
        send_default_pii=SEND_DEFAULT_PII,  # BLOCKING: MUST be False
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
        max_breadcrumbs=50,
        attach_stacktrace=True,
    )

    logger.info(
        "Sentry initialized",
        extra={
            "environment": environment,
            "release": release,
            "send_default_pii": SEND_DEFAULT_PII,
        },
    )
    return True
```

Integration in `src/core/main.py` lifespan:

```python
from observability.sentry_integration import init_sentry

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # ... existing init code ...
    init_sentry(
        environment=settings.environment,
        release=settings.app_version,
    )
    # ... rest of lifespan ...
```

**Key rules:**

- `send_default_pii=False` is BLOCKING — verified by auditor
- DSN loaded from SOPS-decrypted env var at runtime, never hardcoded
- Graceful degradation: if DSN not available, log info and continue
- `traces_sample_rate=0.1` (10% of transactions sampled for performance)
- Low-cardinality tags only: environment, release, service

**Dependencies:** P8-001 (infrastructure running)

**Verification Scaffold:**

| Field | Value |
|-------|-------|
| **Expected Files** | `src/observability/sentry_integration.py`, `src/observability/__init__.py` (modified), `src/core/main.py` (modified) |
| **Forbidden Patterns** | `send_default_pii=True`; `send_default_pii` not explicitly set; hardcoded DSN strings; `@ts-ignore`; `# type: ignore`; Sentry init without graceful fallback |
| **Required Commands** | `python3 -c "from observability.sentry_integration import init_sentry; print('import OK')"` exit 0; `grep -rn "send_default_pii" src/observability/` shows only False values; `python3 -c "import ast; tree = ast.parse(open('src/observability/sentry_integration.py').read()); print('syntax OK')"` exit 0 |
| **Evidence Requirements** | `docs/setup-evidence/P8/STEP-P8-012/verification.md`, `docs/setup-evidence/P8/STEP-P8-012/scaffold-check.md` |
| **Hard Rejection Criteria** | send_default_pii not explicitly False = CRITICAL FAIL; Hardcoded DSN = FAIL; No graceful degradation when DSN missing = FAIL; Import error = FAIL; main.py lifespan not calling init_sentry = FAIL |

---

### P8-013: Sentry Scrubber (PII)

**Description:** Add before_send callback to Sentry integration. Strip sensitive data: safe-word content, intimate data, surveillance payloads, secrets, PII. Drop events from unsafe paths. Redact breadcrumbs.

**Files to modify:**

- `src/observability/sentry_integration.py` — Add before_send and before_breadcrumb callbacks

**Implementation notes:**

```python
import re
from typing import Any

# Patterns to redact from event data
REDACT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(safe[-_]?word|safeword)", re.IGNORECASE),
    re.compile(r"(surveillance[_-]?raw|surveillance[_-]?payload)", re.IGNORECASE),
    re.compile(r"(intimate|private[_-]?detail)", re.IGNORECASE),
    re.compile(r"(api[_-]?key|secret[_-]?key|password|token|dsn)", re.IGNORECASE),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),  # emails
    re.compile(r"\b\d{16}\b"),  # credit card numbers (basic)
]

# Event paths that should be dropped entirely
DROP_EVENT_PATHS: set[str] = {
    "persona-safety",
    "surveillance-raw",
    "consent-revocation",
    "hard-stop",
}


def _redact_value(value: str) -> str:
    """Redact sensitive patterns from a string value."""
    result = value
    for pattern in REDACT_PATTERNS:
        result = pattern.sub("[REDACTED]", result)
    return result


def _should_drop_event(event: dict[str, Any]) -> bool:
    """Check if event originates from a path that should be dropped."""
    transaction = event.get("transaction", "")
    for drop_path in DROP_EVENT_PATHS:
        if drop_path in transaction.lower():
            return True
    return False


def before_send(
    event: dict[str, Any], hint: dict[str, Any]
) -> dict[str, Any] | None:
    """Sentry before_send callback -- strips PII and drops unsafe events.

    Returns None to drop the event, or the scrubbed event dict.
    """
    # Drop events from unsafe paths
    if _should_drop_event(event):
        return None

    # Redact request data
    if "request" in event:
        request = event["request"]
        if "data" in request and isinstance(request["data"], str):
            request["data"] = _redact_value(request["data"])
        if "headers" in request:
            for key in request["headers"]:
                if isinstance(request["headers"][key], str):
                    request["headers"][key] = _redact_value(request["headers"][key])

    # Redact extra data
    if "extra" in event:
        for key in event["extra"]:
            if isinstance(event["extra"][key], str):
                event["extra"][key] = _redact_value(event["extra"][key])

    # Redact breadcrumbs
    if "breadcrumbs" in event:
        for crumb in event["breadcrumbs"].get("values", []):
            if "message" in crumb and isinstance(crumb["message"], str):
                crumb["message"] = _redact_value(crumb["message"])
            if "data" in crumb:
                for key in crumb["data"]:
                    if isinstance(crumb["data"][key], str):
                        crumb["data"][key] = _redact_value(crumb["data"][key])

    return event


def before_breadcrumb(
    crumb: dict[str, Any], hint: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    """Redact breadcrumb data before it is stored."""
    if "message" in crumb and isinstance(crumb["message"], str):
        crumb["message"] = _redact_value(crumb["message"])
    if "data" in crumb:
        for key in list(crumb["data"].keys()):
            if isinstance(crumb["data"][key], str):
                crumb["data"][key] = _redact_value(crumb["data"][key])
    return crumb
```

Add to `sentry_sdk.init()` call:

```python
sentry_sdk.init(
    # ... existing params ...
    before_send=before_send,
    before_breadcrumb=before_breadcrumb,
)
```

**Key rules:**

- `before_send` returns `None` to drop events from unsafe paths
- All string values in request, extra, and breadcrumbs are redacted
- Low-cardinality tags only: service, environment, release
- No personal identifiers, surveillance data, or intimate content reaches Sentry

**Dependencies:** P8-012 (sentry_integration.py exists)

**Verification Scaffold:**

| Field | Value |
|-------|-------|
| **Expected Files** | `src/observability/sentry_integration.py` (modified) |
| **Forbidden Patterns** | `before_send` not set in `sentry_sdk.init()`; Missing redaction of safe-word patterns; Missing event drop for surveillance-raw; `# type: ignore`; `as any`; Hardcoded personal data in test fixtures |
| **Required Commands** | `grep -n "before_send" src/observability/sentry_integration.py` present in init call; `grep -n "before_breadcrumb" src/observability/sentry_integration.py` present in init call; `python3 -c "from observability.sentry_integration import before_send; print('import OK')"` exit 0; `python3 -c "import ast; tree = ast.parse(open('src/observability/sentry_integration.py').read()); print('syntax OK')"` exit 0 |
| **Evidence Requirements** | `docs/setup-evidence/P8/STEP-P8-013/verification.md`, `docs/setup-evidence/P8/STEP-P8-013/scaffold-check.md` |
| **Hard Rejection Criteria** | before_send not in sentry_sdk.init() = FAIL; Safe-word pattern not in REDACT_PATTERNS = FAIL; Surveillance-raw not in DROP_EVENT_PATHS = FAIL; Breadcrumb redaction missing = FAIL; Scrubber not unit-testable = FAIL |

---

### P8-014: Alert Rules

**Description:** Create Prometheus alert rule file with 9 rules from ObsSpec Appendix B covering SEV0 through SEV4.

**Files to create:**

- `monitoring/prometheus/rules/guinevere-alerts.yml` — Prometheus alert rules

**Implementation notes:**

```yaml
groups:
  - name: guinevere-safety
    rules:
      # SEV0: Safe word bypass attempt detected
      - alert: GuinevereSafeWordBypassAttempt
        expr: increase(guinevere_safeword_triggered_total[5m]) > 0
        for: 0m
        labels:
          severity: "critical"
          sev_level: "SEV0"
        annotations:
          summary: "Safe word bypass attempt detected"
          description: "A safe word trigger was detected, indicating a potential safety boundary violation."
          dashboard: "https://grafana.hostdata.id/d/persona-safety"
          runbook: "docs/40-operations/42-IncidentResponse_Postmortem_v1.0.md"

      # SEV0: Public ingress detected (non-Tailscale access to admin)
      - alert: GuineverePublicIngressDetected
        expr: guinevere_public_ingress_detected > 0
        for: 0m
        labels:
          severity: "critical"
          sev_level: "SEV0"
        annotations:
          summary: "Public ingress to admin endpoint detected"
          description: "Non-Tailscale traffic detected accessing admin endpoints."

  - name: guinevere-security
    rules:
      # SEV1: Log redaction failure
      - alert: GuinevereLogRedactionFailure
        expr: increase(guinevere_log_redaction_failures_total[15m]) > 0
        for: 5m
        labels:
          severity: "high"
          sev_level: "SEV1"
        annotations:
          summary: "Log redaction failure detected"

      # SEV1: Secret access outside startup
      - alert: GuinevereSecretAccessOutsideStartup
        expr: increase(guinevere_secret_access_total{phase!="startup"}[30m]) > 0
        for: 5m
        labels:
          severity: "high"
          sev_level: "SEV1"
        annotations:
          summary: "Secret accessed outside startup phase"

      # SEV1: Critical service down
      - alert: GuinevereCriticalServiceDown
        expr: up{job=~"fastapi|postgresql|redis"} == 0
        for: 2m
        labels:
          severity: "high"
          sev_level: "SEV1"
        annotations:
          summary: "Critical service {{ $labels.job }} is down"

  - name: guinevere-operations
    rules:
      # SEV2: Non-critical service down
      - alert: GuinevereNonCriticalServiceDown
        expr: up{job=~"node|loki|alertmanager"} == 0
        for: 5m
        labels:
          severity: "warning"
          sev_level: "SEV2"
        annotations:
          summary: "Non-critical service {{ $labels.job }} is down"

      # SEV2: Subagent file output missing sustained
      - alert: GuinevereSubagentFileOutputMissingSustained
        expr: increase(guinevere_subagent_file_missing_total[30m]) > 5
        for: 10m
        labels:
          severity: "warning"
          sev_level: "SEV2"
        annotations:
          summary: "Sustained subagent file output missing"

      # SEV2: LLM cost spike
      - alert: GuinevereLLMCostSpike
        expr: rate(guinevere_llm_cost_usd_total[1h]) > 0.50
        for: 15m
        labels:
          severity: "warning"
          sev_level: "SEV2"
        annotations:
          summary: "LLM cost spike detected: greater than $0.50/hour"

  - name: guinevere-finops
    rules:
      # SEV3: Restore drill overdue
      - alert: GuinevereRestoreDrillOverdue
        expr: time() - guinevere_backup_last_restore_drill_timestamp > 604800
        for: 1h
        labels:
          severity: "info"
          sev_level: "SEV3"
        annotations:
          summary: "Restore drill overdue (greater than 7 days)"

      # SEV3: LLM cost spike warning
      - alert: GuinevereLLMCostSpikeWarning
        expr: rate(guinevere_llm_cost_usd_total[1h]) > 0.25
        for: 15m
        labels:
          severity: "info"
          sev_level: "SEV3"
        annotations:
          summary: "LLM cost spike warning: greater than $0.25/hour"

  - name: guinevere-maintenance
    rules:
      # SEV4: Dashboard provisioning drift
      - alert: GuinevereDashboardProvisioningDrift
        expr: guinevere_dashboard_provisioned_count != 6
        for: 30m
        labels:
          severity: "info"
          sev_level: "SEV4"
        annotations:
          summary: "Dashboard provisioning drift: expected 6 dashboards"
```

**Key points:**

- All metrics use `guinevere_` prefix
- `sev_level` label enables routing in Alertmanager
- Alert tone in annotations is neutral incident-command
- Dashboard links and runbook references included
- `for` durations prevent flapping

**Dependencies:** P8-001 (Prometheus running), P8-005 (scrape config with rule_files)

**Verification Scaffold:**

| Field | Value |
|-------|-------|
| **Expected Files** | `monitoring/prometheus/rules/guinevere-alerts.yml` |
| **Forbidden Patterns** | Missing sev_level label on any rule; Non-guinevere_ metric prefix; Plaintext webhook URLs; Alert expressions referencing non-existent metrics; severity label values other than critical/high/warning/info |
| **Required Commands** | YAML syntax valid exit 0; `curl -X POST http://127.0.0.1:9090/-/reload` exit 0; `curl -s http://127.0.0.1:9090/api/v1/rules` shows loaded rules; Rule count is 9 or more |
| **Evidence Requirements** | `docs/setup-evidence/P8/STEP-P8-014/verification.md`, `docs/setup-evidence/P8/STEP-P8-014/scaffold-check.md` |
| **Hard Rejection Criteria** | YAML syntax error = FAIL; Fewer than 9 rules = FAIL; Any rule missing sev_level label = FAIL; Prometheus reload fails = FAIL; Rules not loaded in Prometheus = FAIL |

---

### P8-015: SEV Routing Matrix

**Description:** Create Alertmanager configuration with SEV-level routing to Discord channels and Gotify. Neutral incident-command tone enforced in templates.

**Files to create:**

- `monitoring/alertmanager/alertmanager.yml` — Alertmanager routing configuration

**Implementation notes:**

```yaml
global:
  resolve_timeout: 5m

route:
  receiver: "default"
  group_by: ["alertname", "sev_level"]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  routes:
    # SEV0: Critical -- Discord #alerts + Gotify
    - match:
        sev_level: "SEV0"
      receiver: "sev0-critical"
      repeat_interval: 4h

    # SEV1: High -- Discord #alerts + Gotify
    - match:
        sev_level: "SEV1"
      receiver: "sev1-high"
      repeat_interval: 4h

    # SEV2: Warning -- Discord #cost-tracker
    - match:
        sev_level: "SEV2"
      receiver: "sev2-warning"
      repeat_interval: 8h

    # SEV3: Info -- Discord #guinevere-status
    - match:
        sev_level: "SEV3"
      receiver: "sev3-info"
      repeat_interval: 8h

    # SEV4: Maintenance -- Discord #audit-log
    - match:
        sev_level: "SEV4"
      receiver: "sev4-maintenance"
      repeat_interval: 8h

receivers:
  - name: "default"
    webhook_configs:
      - url: "http://host.docker.internal:8081/message"
        send_resolved: true

  - name: "sev0-critical"
    webhook_configs:
      - url: "${DISCORD_WEBHOOK_ALERTS}"
        send_resolved: true
      - url: "http://host.docker.internal:8081/message"
        send_resolved: true

  - name: "sev1-high"
    webhook_configs:
      - url: "${DISCORD_WEBHOOK_ALERTS}"
        send_resolved: true
      - url: "http://host.docker.internal:8081/message"
        send_resolved: true

  - name: "sev2-warning"
    webhook_configs:
      - url: "${DISCORD_WEBHOOK_COST_TRACKER}"
        send_resolved: true

  - name: "sev3-info"
    webhook_configs:
      - url: "${DISCORD_WEBHOOK_STATUS}"
        send_resolved: true

  - name: "sev4-maintenance"
    webhook_configs:
      - url: "${DISCORD_WEBHOOK_AUDIT_LOG}"
        send_resolved: true

templates:
  - "/etc/alertmanager/templates/*.tmpl"
```

**Alert template (neutral incident-command tone):**

```
[{{ .Status | toUpper }}{{ if eq .Status "firing" }}:{{ .Alerts.Firing | len }}{{ end }}] [{{ .CommonLabels.sev_level }}] {{ .CommonLabels.alertname }}

Service: {{ .CommonLabels.job }}
Impact: {{ .CommonAnnotations.description }}
Evidence: {{ .CommonAnnotations.dashboard }}
Next Action: {{ .CommonAnnotations.runbook }}
```

**Key points:**

- Discord webhook URLs via SOPS-encrypted environment variables
- Gotify at localhost:8081 (already implemented)
- SEV0/SEV1: repeat_interval=4h (urgent)
- SEV2+: repeat_interval=8h (standard)
- Alert template uses neutral incident-command tone ONLY — no yandere, no persona
- Template format: `[SEV#] RuleName / Service / Impact / Evidence / Dashboard / Next Action`

**Dependencies:** P8-001 (Alertmanager running), P8-014 (alert rules defined)

**Verification Scaffold:**

| Field | Value |
|-------|-------|
| **Expected Files** | `monitoring/alertmanager/alertmanager.yml` |
| **Forbidden Patterns** | Plaintext webhook URLs (must use env var substitution); Yandere/persona tone in templates; Missing SEV levels (all 0-4 must be present); repeat_interval less than 4h for SEV0/SEV1 |
| **Required Commands** | YAML syntax valid exit 0; `grep -c "sev_level" monitoring/alertmanager/alertmanager.yml` returns 5 (one per SEV level); `grep -c "DISCORD_WEBHOOK" monitoring/alertmanager/alertmanager.yml` returns 4 or more; Restart alertmanager: `docker compose -f monitoring/compose_monitoring.yml restart alertmanager` exit 0 |
| **Evidence Requirements** | `docs/setup-evidence/P8/STEP-P8-015/verification.md`, `docs/setup-evidence/P8/STEP-P8-015/scaffold-check.md` |
| **Hard Rejection Criteria** | YAML syntax error = FAIL; Any SEV level missing from routing = FAIL; Plaintext Discord webhook URLs = FAIL; Persona/yandere tone in templates = CRITICAL FAIL; Gotify routing missing for SEV0/SEV1 = FAIL |

---

### P8-016: Alert Test

**Description:** Simulate each SEV level alert and verify routing to correct Discord channels and Gotify. Verify neutral incident-command tone.

**Files to create:**

- None (verification only)

**Implementation notes:**

Use Alertmanager API to simulate alerts:

```bash
# Simulate SEV0 alert
curl -X POST http://127.0.0.1:9093/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '[{
    "labels": {
      "alertname": "TestSEV0",
      "sev_level": "SEV0",
      "job": "test"
    },
    "annotations": {
      "summary": "Test SEV0 alert",
      "description": "Test impact description",
      "dashboard": "https://grafana.hostdata.id",
      "runbook": "Test runbook"
    }
  }]'
```

- Repeat for SEV1, SEV2, SEV3, SEV4
- Verify each reaches the correct Discord channel
- Verify SEV0 and SEV1 also reach Gotify
- Verify alert message format matches neutral incident-command template

**Dependencies:** P8-014 (alert rules), P8-015 (routing configured)

**Verification Scaffold:**

| Field | Value |
|-------|-------|
| **Expected Files** | Test results saved to evidence directory |
| **Forbidden Patterns** | N/A (verification step) |
| **Required Commands** | POST to alertmanager API for each SEV level exit 0; Verify via Discord channel (manual check or webhook log); `curl -s http://127.0.0.1:9093/api/v2/alerts` shows firing alerts |
| **Evidence Requirements** | `docs/setup-evidence/P8/STEP-P8-016/verification.md`, `docs/setup-evidence/P8/STEP-P8-016/scaffold-check.md` |
| **Hard Rejection Criteria** | SEV0 not reaching #alerts + Gotify = FAIL; SEV1 not reaching #alerts + Gotify = FAIL; SEV2 not reaching #cost-tracker = FAIL; SEV3 not reaching #guinevere-status = FAIL; SEV4 not reaching #audit-log = FAIL; Non-neutral tone in alert messages = CRITICAL FAIL |

---

### P8-017: /cost Discord Command

**Description:** Implement /cost Discord command following the canonical 5-part pattern. Query Redis DB5 cost data, return embedded Discord response with period breakdown.

**Files to create:**

- `src/discord/commands/cost.py` — Cost command implementation (or extend commands.py)

**Files to modify:**

- `src/discord/bot.py` — Remove cost from _STUB_PHASE, wire in setup_hook()
- `src/discord/commands.py` — Add CostCommand to COMMAND_SPECS

**Implementation notes:**

Follow the canonical 5-part pattern:

```python
# 1. Protocol
class CostProtocol(TypedDict):
    period: str
    total_cost: float
    model_breakdown: dict[str, float]
    tool_breakdown: dict[str, float]
    currency: str

# 2. Frozen dataclasses
@dataclass(frozen=True)
class CostEmbedField:
    name: str
    value: str
    inline: bool = True

@dataclass(frozen=True)
class CostEmbedData:
    title: str
    color: int  # 0x6B21A8 (purple)
    fields: list[CostEmbedField]
    footer: str

# 3. Builder
def build_cost_data(period: str, cost_tracker: CostTracker) -> CostEmbedData:
    """Build cost embed data from Redis DB5."""
    ...

# 4. Converter
def to_discord_embed(data: CostEmbedData) -> dict:
    """Convert to Discord embed JSON format."""
    ...

# 5. Callback
async def cost_callback(
    interaction: discord.Interaction,
    period: str = "today",
) -> None:
    """Handle /cost command."""
    if not is_faiz_interaction(interaction):
        await interaction.response.send_message(
            "This command is restricted.", ephemeral=True
        )
        return
    await interaction.response.defer(ephemeral=True)
    # ... build and send embed ...
```

**Parameters:**

- `period`: today, week, month (default: today)

**Data source:** Redis DB5 cost keys (already populated by CostTracker):

- `cost:daily:{YYYY-MM-DD}` — daily cost
- `cost:monthly:{YYYY-MM}` — monthly cost
- `cost:model:{model_name}:{date}` — per-model breakdown
- `cost:tool:{tool_name}:{date}` — per-tool breakdown

**Embed color:** `0x6B21A8` (purple) per DiscordUXSpec

**Key rules:**

- `is_faiz_interaction` guard (existing pattern)
- `_defer_ephemeral` for processing (existing pattern)
- Graceful fallback if Redis unavailable
- No type-unsafe patterns

**Dependencies:** Existing CostTracker in Redis DB5, P8-001 (infrastructure)

**Verification Scaffold:**

| Field | Value |
|-------|-------|
| **Expected Files** | `src/discord/commands/cost.py` (or equivalent), `src/discord/bot.py` (modified), `src/discord/commands.py` (modified) |
| **Forbidden Patterns** | `as any`; `@ts-ignore`; `# type: ignore`; cost still in _STUB_PHASE; Hardcoded cost values (must use Redis); Missing is_faiz_interaction guard; Missing _defer_ephemeral; Embed color != 0x6B21A8 |
| **Required Commands** | `python3 -c "import ast; tree = ast.parse(open('src/discord/commands/cost.py').read()); print('syntax OK')"` exit 0; `grep -n "_STUB_PHASE" src/discord/bot.py | grep cost` returns empty (cost removed from stubs); `grep -n "cost_callback" src/discord/bot.py` present in setup_hook; `grep -n "0x6B21A8" src/discord/commands/cost.py` present |
| **Evidence Requirements** | `docs/setup-evidence/P8/STEP-P8-017/verification.md`, `docs/setup-evidence/P8/STEP-P8-017/scaffold-check.md` |
| **Hard Rejection Criteria** | 5-part pattern not followed = FAIL; cost still in stub phase = FAIL; Missing is_faiz_interaction = FAIL; Missing _defer_ephemeral = FAIL; Wrong embed color = FAIL; Type-unsafe patterns = CRITICAL FAIL |

---

### P8-018: /budget Discord Command

**Description:** Implement /budget Discord command following the canonical 5-part pattern. View and set monthly budget cap via Redis DB5.

**Files to create:**

- `src/discord/commands/budget.py` — Budget command implementation

**Files to modify:**

- `src/discord/bot.py` — Remove budget from _STUB_PHASE, wire in setup_hook()
- `src/discord/commands.py` — Add BudgetCommand to COMMAND_SPECS

**Implementation notes:**

Follow the same 5-part pattern as P8-017.

**Parameters:**

- `action`: view (default), set
- `amount`: Budget amount in USD (required when action=set)

**Data source:** Redis DB5:

- `budget:monthly_cap` — Current monthly budget cap
- `cost:monthly:{YYYY-MM}` — Current month spend (from CostTracker)
- `BudgetEnforcer` class for validation

**Embed color:** `0x059669` (teal) for finance

**Key rules:**

- view action shows: current cap, current spend, remaining, percentage used
- set action updates budget:monthly_cap in Redis
- is_faiz_interaction guard
- _defer_ephemeral for processing
- Validate amount > 0 when setting budget
- Graceful fallback if Redis unavailable

**Dependencies:** Existing CostTracker/BudgetEnforcer, P8-017 (sequential — same files)

**Verification Scaffold:**

| Field | Value |
|-------|-------|
| **Expected Files** | `src/discord/commands/budget.py`, `src/discord/bot.py` (modified), `src/discord/commands.py` (modified) |
| **Forbidden Patterns** | `as any`; `@ts-ignore`; `# type: ignore`; budget still in _STUB_PHASE; Missing is_faiz_interaction; Missing _defer_ephemeral; Embed color != 0x059669 |
| **Required Commands** | `python3 -c "import ast; tree = ast.parse(open('src/discord/commands/budget.py').read()); print('syntax OK')"` exit 0; `grep -n "_STUB_PHASE" src/discord/bot.py | grep budget` returns empty; `grep -n "budget_callback" src/discord/bot.py` present; `grep -n "0x059669" src/discord/commands/budget.py` present |
| **Evidence Requirements** | `docs/setup-evidence/P8/STEP-P8-018/verification.md`, `docs/setup-evidence/P8/STEP-P8-018/scaffold-check.md` |
| **Hard Rejection Criteria** | 5-part pattern not followed = FAIL; budget still in stub phase = FAIL; Missing is_faiz_interaction = FAIL; Wrong embed color = FAIL; Type-unsafe patterns = CRITICAL FAIL |

---

### P8-019: Monthly Cost Report

**Description:** Create automated monthly cost report that posts a comprehensive embed to #cost-tracker channel on the 1st of each month.

**Files to create:**

- `src/core/services/monthly_report.py` — Monthly report generation and posting

**Files to modify:**

- `src/core/main.py` — Register monthly report task (APScheduler or similar)

**Implementation notes:**

The monthly report should include:

1. **Total spend**: Current month total in USD
2. **Per-model breakdown**: Cost by LLM model (table format)
3. **Per-tool breakdown**: Cost by tool/service (table format)
4. **Trend**: Comparison with previous month (up/down arrow + percentage)
5. **Projected**: Based on current rate, projected month-end total
6. **Budget remaining**: Current cap minus spend

**Scheduling approach:**

- Use APScheduler (if available in pyproject.toml) or a simple daily check that posts on the 1st
- Alternatively: systemd timer that triggers a script on the 1st of each month
- The task runs within the FastAPI application lifecycle

**Discord embed:**

- Color: 0x6B21A8 (purple, matching /cost)
- Title: "Monthly Cost Report -- {Month YYYY}"
- Footer: "Generated by Guinevere FinOps"

**Data source:** Redis DB5 (same keys as /cost command)

**Key rules:**

- Graceful degradation: if Discord unavailable, log and retry next cycle
- No plaintext secrets in report content
- Low-cardinality tags only

**Dependencies:** P8-017 (cost command pattern), P8-018 (budget data), Existing CostTracker

**Verification Scaffold:**

| Field | Value |
|-------|-------|
| **Expected Files** | `src/core/services/monthly_report.py`, `src/core/main.py` (modified) |
| **Forbidden Patterns** | `as any`; `@ts-ignore`; `# type: ignore`; Hardcoded Discord channel IDs (use config); Plaintext secrets; Missing error handling for Discord API failures |
| **Required Commands** | `python3 -c "import ast; tree = ast.parse(open('src/core/services/monthly_report.py').read()); print('syntax OK')"` exit 0; `grep -n "monthly_report" src/core/main.py` present (task registration); `python3 -c "from core.services.monthly_report import generate_monthly_report; print('import OK')"` exit 0 |
| **Evidence Requirements** | `docs/setup-evidence/P8/STEP-P8-019/verification.md`, `docs/setup-evidence/P8/STEP-P8-019/scaffold-check.md` |
| **Hard Rejection Criteria** | Report generation function not importable = FAIL; Task not registered in application lifecycle = FAIL; Missing error handling = FAIL; Type-unsafe patterns = CRITICAL FAIL; Hardcoded channel IDs = FAIL |

---

### P8-020: Backup Monitoring

**Description:** Create textfile collector script that reads the backup success sentinel and writes a Prometheus metric. Add backup freshness alert rule.

**Files to create:**

- `monitoring/scripts/backup-metric-collector.sh` — Script to read sentinel and write .prom file
- `monitoring/prometheus/rules/guinevere-backup-alerts.yml` — Backup freshness alert rule
- Cron job entry (via crontab or systemd timer)

**Implementation notes:**

Textfile collector script:

```bash
#!/bin/bash
# Reads backup success sentinel and writes Prometheus metric
SENTINEL="/var/log/guinevere/last-backup-success"
OUTPUT="/home/guinevere/guinevere/monitoring/node-exporter/textfile/backup.prom"

if [ -f "$SENTINEL" ]; then
    TIMESTAMP=$(stat -c %Y "$SENTINEL")
    echo "# HELP guinevere_backup_last_success_timestamp Unix timestamp of last successful backup" > "$OUTPUT"
    echo "# TYPE guinevere_backup_last_success_timestamp gauge" >> "$OUTPUT"
    echo "guinevere_backup_last_success_timestamp $TIMESTAMP" >> "$OUTPUT"
else
    echo "# HELP guinevere_backup_last_success_timestamp Unix timestamp of last successful backup" > "$OUTPUT"
    echo "# TYPE guinevere_backup_last_success_timestamp gauge" >> "$OUTPUT"
    echo "guinevere_backup_last_success_timestamp 0" >> "$OUTPUT"
fi
```

Backup alert rule:

```yaml
groups:
  - name: guinevere-backup
    rules:
      - alert: GuinevereBackupStale
        expr: time() - guinevere_backup_last_success_timestamp > 93600
        for: 5m
        labels:
          severity: "warning"
          sev_level: "SEV2"
        annotations:
          summary: "Backup older than 26 hours"
          description: "Last successful backup was more than 26 hours ago."
```

Cron job: `*/5 * * * * /home/guinevere/guinevere/monitoring/scripts/backup-metric-collector.sh`

**Dependencies:** P8-001 (node-exporter with textfile directory), P8-014 (rules directory exists)

**Verification Scaffold:**

| Field | Value |
|-------|-------|
| **Expected Files** | `monitoring/scripts/backup-metric-collector.sh`, `monitoring/prometheus/rules/guinevere-backup-alerts.yml`, crontab entry |
| **Forbidden Patterns** | Plaintext secrets in script; Script not executable; Missing # HELP and # TYPE comments in .prom output; Alert threshold less than 26h or greater than 48h |
| **Required Commands** | `chmod +x monitoring/scripts/backup-metric-collector.sh` exit 0; `bash monitoring/scripts/backup-metric-collector.sh` exit 0; `cat monitoring/node-exporter/textfile/backup.prom` contains guinevere_backup_last_success_timestamp; `curl -s http://127.0.0.1:9100/metrics | grep guinevere_backup` returns metric; `crontab -l | grep backup-metric` entry present |
| **Evidence Requirements** | `docs/setup-evidence/P8/STEP-P8-020/verification.md`, `docs/setup-evidence/P8/STEP-P8-020/scaffold-check.md` |
| **Hard Rejection Criteria** | Script not executable = FAIL; .prom file not generated = FAIL; Metric not appearing in node-exporter = FAIL; Alert rule not loaded = FAIL; Cron job missing = FAIL |

---

### P8-021: guinevere-monitoring.service

**Description:** Create systemd service unit that manages all monitoring containers via Docker Compose. Follow existing systemd pattern with security hardening.

**Files to create:**

- `systemd/guinevere-monitoring.service` — Systemd unit file

**Implementation notes:**

```ini
[Unit]
Description=Guinevere Monitoring Stack
Documentation=https://github.com/faizz/guinevere
After=network-online.target docker.service
Requires=docker.service
Wants=guinevere-core.service

[Service]
Type=exec
User=guinevere
Group=guinevere
Slice=guinevere.slice
WorkingDirectory=/home/guinevere/guinevere

# Resource limits
MemoryMax=1G
CPUQuota=100%

# Exec commands
ExecStartPre=/usr/bin/docker compose -f monitoring/compose.monitoring.yml pull --quiet
ExecStart=/usr/bin/docker compose -f monitoring/compose.monitoring.yml up --remove-orphans
ExecStop=/usr/bin/docker compose -f monitoring/compose.monitoring.yml down --timeout 30

# Restart policy
Restart=on-failure
RestartSec=10
StartLimitBurst=3
StartLimitIntervalSec=60

# Security hardening (matching existing pattern)
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/home/guinevere/guinevere/monitoring /home/guinevere/data
PrivateTmp=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictSUIDSGID=yes

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=guinevere-monitoring

[Install]
WantedBy=multi-user.target
```

**Key points:**

- `Type=exec` (not forking — docker compose runs in foreground)
- `Slice=guinevere.slice` — shares the 8G slice budget
- `MemoryMax=1G` — monitoring stack gets 1G of the slice budget
- `CPUQuota=100%` — single core equivalent
- `ExecStartPre` pulls images before starting (avoids cold-start delays)
- Security hardening matches existing systemd units
- `ReadWritePaths` allows monitoring configs and data volumes

**Dependencies:** P8-001 (compose file exists and works)

**Verification Scaffold:**

| Field | Value |
|-------|-------|
| **Expected Files** | `systemd/guinevere-monitoring.service` |
| **Forbidden Patterns** | `Type=forking` (must be exec); Missing Slice=guinevere.slice; Missing security hardening directives; User=root; Missing MemoryMax limit; ProtectHome=no |
| **Required Commands** | `systemd-analyze verify systemd/guinevere-monitoring.service` exit 0 (no errors); `sudo cp systemd/guinevere-monitoring.service /etc/systemd/system/` exit 0; `sudo systemctl daemon-reload` exit 0; `sudo systemctl enable guinevere-monitoring.service` exit 0; `sudo systemctl start guinevere-monitoring.service` exit 0; `systemctl is-active guinevere-monitoring.service` returns active |
| **Evidence Requirements** | `docs/setup-evidence/P8/STEP-P8-021/verification.md`, `docs/setup-evidence/P8/STEP-P8-021/scaffold-check.md` |
| **Hard Rejection Criteria** | systemd-analyze verify fails = FAIL; Service not starting = FAIL; User=root = FAIL; Missing Slice=guinevere.slice = FAIL; Missing MemoryMax = FAIL; Security hardening missing = FAIL |

---

### P8-022: MVP Acceptance Full Run

**Description:** Execute ALL acceptance criteria checks from the AC Catalog. Document each result as PASS/FAIL/BLOCKED/NOT-RUN with evidence path references. This is READ-ONLY verification — no implementation changes.

**Files to create:**

- `docs/setup-evidence/P8/STEP-P8-022/mvp-acceptance-results.md` — Full acceptance criteria results

**Implementation notes:**

Run through ALL acceptance criteria sections from `docs/10-governance/16-AcceptanceCriteriaCatalog_v1.0.md`:

**AC-SAFE (Safety) — 8 criteria:**

- AC-SAFE-001: Safe word immediately halts all operations
- AC-SAFE-002: HARD STOP disables persona behavior
- AC-SAFE-003: Consent revocation stops surveillance
- AC-SAFE-004: Distress detection triggers protocol
- AC-SAFE-005: Y4 baseline, Y5 ceiling enforced
- AC-SAFE-006: No punishment overflow over emergency
- AC-SAFE-007: Safe word content never logged externally
- AC-SAFE-008: Consent state persisted across restarts

**AC-SEC (Security) — 7 criteria:**

- AC-SEC-001: No plaintext secrets in repo
- AC-SEC-002: SOPS encryption for all secrets
- AC-SEC-003: RBAC/ABAC enforced
- AC-SEC-004: Network isolation (Tailscale-only admin)
- AC-SEC-005: Prompt injection defenses active
- AC-SEC-006: Audit logging for security events
- AC-SEC-007: Secrets rotation policy implemented

**AC-OPS (Operations) — 6 criteria:**

- AC-OPS-001: Monitoring stack running and healthy
- AC-OPS-002: Alert routing verified for all SEV levels
- AC-OPS-003: Backup and restore verified
- AC-OPS-004: SLO dashboards provisioned
- AC-OPS-005: Incident response procedures documented
- AC-OPS-006: Observability pipeline end-to-end

**AC-DATA (Data) — 6 criteria:**

- AC-DATA-001: Data classification applied
- AC-DATA-002: Retention policies enforced
- AC-DATA-003: Surveillance consent verified
- AC-DATA-004: PII scrubbing active (Sentry)
- AC-DATA-005: ERD matches schema
- AC-DATA-006: Memory recall respects consent

**AC-CORE (Core Runtime) — 6 criteria:**

- AC-CORE-001: Agent loop stable
- AC-CORE-002: Phase transitions correct
- AC-CORE-003: Subagent management working
- AC-CORE-004: Task queue operational
- AC-CORE-005: Discord bot responsive
- AC-CORE-006: LLM integration functional

**AC-PHASE (Phase Gates) — 8 criteria:**

- AC-PHASE-001 through AC-PHASE-008: Each phase gate verified

**Output format:**

```markdown
| AC ID | Description | Status | Evidence Path | Notes |
|-------|-------------|--------|---------------|-------|
| AC-SAFE-001 | Safe word halts ops | PASS | evidence/P7/... | Verified in P7 |
| AC-SEC-001 | No plaintext secrets | PASS | P8 scan results | grep verified |
```

**Dependencies:** ALL prior steps (P8-001 through P8-021)

**Verification Scaffold:**

| Field | Value |
|-------|-------|
| **Expected Files** | `docs/setup-evidence/P8/STEP-P8-022/mvp-acceptance-results.md` |
| **Forbidden Patterns** | Implementation changes (this is READ-ONLY); Fabricated evidence paths; PASS without verification; Missing AC sections |
| **Required Commands** | Verify all referenced evidence files exist (check each path referenced in results); Verify result count: `grep -c "PASS\|FAIL\|BLOCKED\|NOT-RUN" docs/setup-evidence/P8/STEP-P8-022/mvp-acceptance-results.md` returns 41 or more (all AC criteria) |
| **Evidence Requirements** | `docs/setup-evidence/P8/STEP-P8-022/verification.md`, `docs/setup-evidence/P8/STEP-P8-022/scaffold-check.md`, `docs/setup-evidence/P8/STEP-P8-022/mvp-acceptance-results.md` |
| **Hard Rejection Criteria** | Any AC section missing from results = FAIL; PASS without evidence path = FAIL; Fabricated evidence paths = CRITICAL FAIL; Implementation changes made during this step = FAIL |

---

### P8-023: Faiz Sign-off

**Description:** Present final summary to Faiz for explicit approval. Update PROGRESS.md and CHECKLIST.md after approval.

**Files to create:**

- `docs/setup-evidence/P8/STEP-P8-023/sign-off-summary.md` — Summary for Faiz review

**Files to modify (AFTER approval):**

- `PROGRESS.md` — Update P8 status
- `CHECKLIST.md` — Update Phase 8 section

**Implementation notes:**

Sign-off summary must include:

1. All 22 prior steps PASS/FAIL status table
2. MVP acceptance criteria results summary (from P8-022)
3. Known caveats and deferred items (from section 15 of this plan)
4. Monitoring stack status (all containers healthy)
5. Sentry integration status (send_default_pii=false verified)
6. FinOps commands status (/cost, /budget, monthly report)
7. Alert routing status (all SEV levels verified)
8. Budget impact summary ($4/month incremental)

**This step requires EXPLICIT Faiz approval. No auto-completion.**

**Dependencies:** P8-022 (MVP acceptance PASS)

**Verification Scaffold:**

| Field | Value |
|-------|-------|
| **Expected Files** | `docs/setup-evidence/P8/STEP-P8-023/sign-off-summary.md` |
| **Forbidden Patterns** | Auto-completing without Faiz approval; PROGRESS.md updated before approval; Missing step status entries |
| **Required Commands** | `test -f docs/setup-evidence/P8/STEP-P8-023/sign-off-summary.md` exit 0; `grep -c "P8-" docs/setup-evidence/P8/STEP-P8-023/sign-off-summary.md` returns 22 or more (all steps listed) |
| **Evidence Requirements** | `docs/setup-evidence/P8/STEP-P8-023/verification.md`, `docs/setup-evidence/P8/STEP-P8-023/sign-off-summary.md` |
| **Hard Rejection Criteria** | Summary file missing = FAIL; Any step status missing from summary = FAIL; PROGRESS.md updated before Faiz approval = FAIL; Faiz has not explicitly approved = BLOCKED |

---

## 10. Token and Secret Handling

### 10.1 Secret Inventory

| Secret | Storage Location | Runtime Access | Steps That Use It |
|--------|------------------|----------------|-------------------| 
| Sentry DSN | `secrets/sentry-dsn.enc.yaml` (SOPS) | Decrypted to env var SENTRY_DSN at runtime | P8-012 |
| Discord webhook (#alerts) | `monitoring/.env.enc` (SOPS) | Decrypted to monitoring/.env as DISCORD_WEBHOOK_ALERTS | P8-015 |
| Discord webhook (#cost-tracker) | `monitoring/.env.enc` (SOPS) | Decrypted to monitoring/.env as DISCORD_WEBHOOK_COST_TRACKER | P8-015 |
| Discord webhook (#guinevere-status) | `monitoring/.env.enc` (SOPS) | Decrypted to monitoring/.env as DISCORD_WEBHOOK_STATUS | P8-015 |
| Discord webhook (#audit-log) | `monitoring/.env.enc` (SOPS) | Decrypted to monitoring/.env as DISCORD_WEBHOOK_AUDIT_LOG | P8-015 |
| Grafana admin password | `monitoring/.env.enc` (SOPS) | Decrypted to monitoring/.env as GRAFANA_ADMIN_PASSWORD | P8-001, P8-006 |
| postgres_exporter DB password | `monitoring/.env.enc` (SOPS) | Decrypted to monitoring/.env as PG_EXPORTER_PASSWORD | P8-003 |
| redis_exporter password | `monitoring/.env.enc` (SOPS) | Decrypted to monitoring/.env as REDIS_EXPORTER_PASSWORD | P8-004 |
| Grafana PostgreSQL datasource password | `monitoring/.env.enc` (SOPS) | Injected via Grafana provisioning env var | P8-007 |

### 10.2 SOPS Rules

- All encrypted files follow `.sops.yaml` creation_rules
- Decryption command: `sops -d secrets/sentry-dsn.enc.yaml` or `sops -d monitoring/.env.enc > monitoring/.env`
- `.env` files are in `.gitignore` — only `.env.enc` files are committed
- No plaintext secrets in: config files, Python code, logs, evidence files, git history

### 10.3 Forbidden Patterns

| Pattern | Why Forbidden |
|---------|--------------| 
| Hardcoded DSN in Python code | Secret exposure in git history |
| Plaintext password in compose YAML | Secret exposure in git history |
| Webhook URL in alertmanager.yml | Secret exposure in git history |
| Secrets in environment variable defaults | May leak to logs or process listing |
| Secrets in evidence/report files | Artifact exposure |
| Secrets in Docker build context | Layer caching exposure |

### 10.4 Secret Lifecycle

1. **Create**: Generate secret value (webhook URL, password, DSN)
2. **Encrypt**: `sops -e plaintext.yaml > encrypted.enc.yaml`
3. **Commit**: Only encrypted file committed to git
4. **Deploy**: `sops -d encrypted.enc.yaml > .env` on target host
5. **Runtime**: Application reads from environment variable
6. **Rotate**: Update encrypted file, redeploy

---

## 11. Evidence Paths

### 11.1 Per-Step Evidence Structure

Each step creates evidence in its own subdirectory:

```
docs/setup-evidence/P8/
+-- STEP-P8-001/
|   +-- verification.md          (parent verification results)
|   +-- scaffold-check.md        (scaffold criteria check results)
|   +-- [step-specific artifacts]  (curl outputs, docker ps, etc.)
+-- STEP-P8-002/
|   +-- verification.md
|   +-- scaffold-check.md
|   +-- ...
+-- ...
+-- STEP-P8-022/
|   +-- verification.md
|   +-- scaffold-check.md
|   +-- mvp-acceptance-results.md
+-- STEP-P8-023/
    +-- verification.md
    +-- sign-off-summary.md
```

### 11.2 Evidence File Schema

Each verification.md follows the Evidence Minimum Schema (12 sections):

1. **What Was Done**: Brief description of implementation
2. **Files Changed**: List of created/modified files with paths
3. **Validation Results**: Command outputs, test results
4. **Evidence Artifacts**: Screenshots, curl outputs, docker ps
5. **Doc-Sync Impact**: Any docs that need updating
6. **Boundary Compliance**: Safety, consent, persona verification
7. **Rollback/Re-run Safety**: Idempotency verification
8. **Design Decisions/Caveats**: Deviations from plan
9. **Auditor Gate**: Auditor verdict (PASS/NEEDS REVIEW/FAIL)
10. **Security Scan**: Secret exposure check results
11. **Acceptance Criteria Mapping**: AC IDs satisfied by this step
12. **Footer**: Timestamp, agent ID, version

### 11.3 Scaffold Check File

Each scaffold-check.md documents the 5 scaffold fields:

- Expected Files: verified present
- Forbidden Patterns: grep results (all zero matches)
- Required Commands: outputs and exit codes
- Evidence Requirements: file paths verified
- Hard Rejection Criteria: PASS/FAIL for each

---

## 12. Auditor Matrix

### 12.1 Per-Step Auditor Assignments

| Step | Auditor Type | Scope | Key Checks |
|------|-------------|-------|------------|
| P8-001 | Infrastructure | Docker compose correctness | Port bindings, network isolation, volume mounts, version tags, all 8 services present |
| P8-002 | Infrastructure | node-exporter | Metrics accessible, systemd collector, textfile directory, pid:host |
| P8-003 | Infrastructure | postgres-exporter | DB role permissions (pg_monitor only, no superuser), metrics accessible |
| P8-004 | Infrastructure | redis-exporter | ACL permissions (read-only), metrics accessible |
| P8-005 | Config | Scrape targets | All 7 jobs present, target health, reload success |
| P8-006 | Config | Grafana | Health endpoint, admin password set, no anonymous access |
| P8-007 | Config | Datasources | 3 datasources provisioned, Prometheus default, no plaintext passwords |
| P8-008 | Config | Dashboards | JSON validity, 6 dashboards, unique UIDs, panel coverage vs ObsSpec section 9.2 |
| P8-009 | Config | Loki | Schema v13, retention 720h, compactor enabled, ready endpoint |
| P8-010 | Config | Promtail | Version 3.5.8 (CRITICAL), journal scrape, Docker scrape, pipeline stages |
| P8-011 | Verification | Log pipeline | End-to-end test, structured parsing, Grafana Explore |
| P8-012 | Security + Code | Sentry init | send_default_pii=false VERIFIED, graceful degradation, no hardcoded DSN |
| P8-013 | Security + Code | Sentry scrubber | before_send present, all redaction patterns, event drop paths, breadcrumb scrubbing |
| P8-014 | Security + Config | Alert rules | 9 rules, all SEV levels, guinevere_ prefix, neutral tone |
| P8-015 | Security + Config | SEV routing | All 5 SEV levels routed, Gotify for SEV0/1, no plaintext webhooks, neutral template |
| P8-016 | Verification | Alert test | All SEV levels tested, routing verified, tone verified |
| P8-017 | Code | /cost command | 5-part pattern, Redis data source, embed color, is_faiz guard |
| P8-018 | Code | /budget command | 5-part pattern, Redis data source, embed color, is_faiz guard |
| P8-019 | Code | Monthly report | Scheduling, report generation, error handling |
| P8-020 | Config + Security | Backup monitoring | Textfile collector, cron job, alert rule, no secret exposure |
| P8-021 | Infrastructure | systemd unit | Type=exec, Slice, MemoryMax, security hardening, non-root |
| P8-022 | Full audit | MVP acceptance | ALL AC criteria checked, evidence paths valid, no fabricated results |
| P8-023 | Manual | Faiz sign-off | Summary complete, explicit approval received |

### 12.2 Auditor Verdicts

| Verdict | Meaning | Action |
|---------|---------|--------|
| PASS | All checks satisfied | Step can be marked complete |
| NEEDS REVIEW | Non-blocking finding | Investigate, document, may proceed |
| FAIL | Blocking finding | Fix required, re-audit via task_id continuation |

---

## 13. Rollback Plan

### 13.1 Full Stack Rollback

| Action | Command | Impact |
|--------|---------|--------|
| Stop all monitoring | `docker compose -f monitoring/compose.monitoring.yml down` | All 8 containers stopped |
| Stop systemd service | `sudo systemctl stop guinevere-monitoring.service` | All monitoring stopped |
| Disable systemd service | `sudo systemctl disable guinevere-monitoring.service` | Will not start on boot |
| Remove monitoring configs | `rm -rf monitoring/` | All configs removed |
| Remove Sentry init | Remove init_sentry() call from main.py lifespan | Graceful degradation |
| Re-stub Discord commands | Re-add cost/budget to _STUB_PHASE in bot.py | Commands show "coming soon" |
| Remove evidence | `rm -rf docs/setup-evidence/P8/` | Evidence removed |
| Remove cron job | `crontab -e`, remove backup-metric line | Collector stops |

### 13.2 Partial Rollback (Per-Batch)

| Batch | Rollback Scope | Data Loss |
|-------|----------------|-----------|
| Batch 1 | Stop monitoring containers | Zero — pure infrastructure |
| Batch 2 | Revert prometheus.yml, stop Grafana | Zero — no persistent data |
| Batch 3 | Remove dashboard JSONs, stop Loki/Promtail | Zero — log data can be re-collected |
| Batch 4 | Remove Sentry init and scrubber | Zero — graceful degradation |
| Batch 5 | Remove alert rules and Alertmanager config | Zero — alerting stops gracefully |
| Batch 6 | Re-stub Discord commands | Zero — commands show stub message |
| Batch 7 | Remove systemd service, backup monitoring | Zero — pure infrastructure |

### 13.3 Rollback Safety

- **No database migrations**: P8 is pure infrastructure + Discord commands. Zero database schema changes.
- **No data loss**: All monitoring data (Prometheus TSDB, Loki logs, Grafana dashboards) is ephemeral and can be re-collected.
- **Graceful degradation**: Removing Sentry or Discord commands does not break the core application.
- **Idempotent**: All setup steps are re-runnable. Docker compose `up -d` is idempotent.

---

## 14. Tracker Sync Plan

### 14.1 Files to Update

| File | When to Update | Updated By |
|------|----------------|------------|
| `PROGRESS.md` | After each step PASS (status line) and after P8-022 (phase complete) | Parent-only |
| `CHECKLIST.md` | After P8-022 PASS (Phase 8 section) | Parent-only |
| `docs/README.md` | No changes needed (no new docs created in P8) | N/A |
| `ADR-Index` | No changes needed (no new ADRs in P8) | N/A |

### 14.2 Update Cadence

- **Per-step**: Update P8-NNN status line in PROGRESS.md after each step passes auditor gate
- **Per-batch**: Verify all steps in batch are PASS before moving to next batch
- **Phase-complete**: After P8-022 PASS, update CHECKLIST.md Phase 8 section with all checkboxes checked
- **Sign-off**: After P8-023, update PROGRESS.md with final P8 completion date

### 14.3 Sync Verification

After each PROGRESS.md update, parent verifies:

- Step number matches
- Status is accurate (PASS/FAIL/BLOCKED)
- Evidence path reference is valid
- No stale entries from prior phases

---

## 15. Caveats and Known Risks

| # | Risk | Impact | Mitigation |
|---|------|--------|------------|
| 1 | Promtail 3.5.8 is CRITICAL — 3.6.0+ drops journald support (GitHub issue 19911) | Log pipeline broken if wrong version used | Hardcoded version in compose file; auditor checks image tag; P8-010 scaffold has CRITICAL FAIL for wrong version |
| 2 | Grafana dashboard JSONs need to be hand-crafted or adapted from community templates | P8-008 is high-complexity step | Allow extra time; start from community templates and customize; validate JSON before provisioning |
| 3 | Sentry DSN requires Sentry account setup (external dependency) | P8-012 blocked if account not ready | Set up Sentry account before Batch 4; graceful degradation if DSN not available |
| 4 | Discord webhook for Alertmanager requires creating a webhook URL in #alerts channel | P8-015 blocked if webhook not ready | Create webhook URLs before Batch 5; store in SOPS-encrypted .env.enc |
| 5 | postgres_exporter needs pg_monitor role — verify PostgreSQL 16+ supports this | P8-003 may need adjustment | pg_monitor is available since PG10; verify with `SELECT * FROM pg_roles` |
| 6 | Alert thresholds (LLM cost spike, etc.) need baseline data | Initial values may need tuning after deployment | Document initial thresholds as tunable; plan review after 1 week of data collection |
| 7 | Monthly cost report needs APScheduler already available in pyproject.toml | P8-019 may need alternative scheduling | Verify APScheduler in deps; fallback to systemd timer if not available |
| 8 | MVP acceptance run (P8-022) is READ-ONLY verification | May reveal gaps from prior phases | Document all FAILs with evidence; create follow-up tasks for gaps; do not implement fixes during P8-022 |
| 9 | Docker Compose service names must match for internal DNS resolution | Scrape configs reference service names | P8-005 scrape targets use exact service names from P8-001 compose file |
| 10 | host.docker.internal may not resolve on all Docker versions | Exporters and FastAPI scrape targets fail | Verify Docker 20.10+ supports host.docker.internal; fallback to host IP if needed |
| 11 | Grafana provisioning reload requires container restart | Datasource/dashboard changes need restart | Document restart requirement; include in P8-007 verification steps |
| 12 | FastAPI /metrics endpoint must be enabled for Prometheus scraping | P8-005 fastapi target may be DOWN | Verify prometheus-client middleware is configured in main.py; add if missing |

---

## 16. Execution Checklist

### Per-Batch Checklist

For each batch, execute in order:

1. **Pre-flight**:
   - [ ] Verify all prior batches PASS (check PROGRESS.md)
   - [ ] Verify no collision with other active sessions
   - [ ] Verify SOPS secrets available for steps that need them
   - [ ] Verify Docker and Docker Compose available on target host

2. **Implementation**:
   - [ ] Delegate one sub-agent per step (parallel where marked)
   - [ ] Include scaffold verbatim in delegation prompt
   - [ ] Include binding decisions in delegation prompt
   - [ ] Include output_path for evidence files

3. **Parent Verify**:
   - [ ] Read all sub-agent output files
   - [ ] Re-run every scaffold command (do not trust self-report)
   - [ ] Run lsp_diagnostics on changed Python files
   - [ ] Verify no forbidden patterns via grep
   - [ ] Verify no plaintext secrets

4. **Evidence**:
   - [ ] Create verification.md per step (12-section schema)
   - [ ] Create scaffold-check.md per step
   - [ ] Save step-specific artifacts (curl outputs, docker ps)

5. **Auditor**:
   - [ ] Spawn auditor per step (per auditor matrix)
   - [ ] Read auditor report
   - [ ] Record verdict in evidence

6. **Fix** (if needed):
   - [ ] Re-delegate fixes via task_id continuation
   - [ ] Re-verify after fix
   - [ ] Re-run auditor until PASS

7. **Complete**:
   - [ ] Mark step PASS in todos
   - [ ] Update PROGRESS.md (parent-only)
   - [ ] Verify evidence directory complete

### Per-Step Delegation Template

```
TASK: P8-NNN: {Name}
EXPECTED OUTCOME: {Description from Section 9}
BINDING DECISIONS: See Section 4 (versions, ports, security)
IMPLEMENTATION NOTES: See Section 9, P8-NNN
VERIFICATION SCAFFOLD: {5-field table from Section 9}
OUTPUT PATH: docs/setup-evidence/P8/STEP-P8-{NNN}/
MUST DO: Follow scaffold exactly. Write evidence files.
MUST NOT DO: Deviate from binding decisions. Skip scaffold checks.
```

---

## Footer

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-03 | Guinevere (P8 Planner) | Initial batch plan with 23 steps, 7 batches, per-step scaffolds |

> This plan is the authoritative artifact for P8 implementation. All sub-agents must reference this file. All parent verification must check against this file. No deviation without re-planning.
