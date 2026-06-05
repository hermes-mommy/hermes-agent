# P9-P10 Step Prompts Audit: Post-Hermes Migration Validity

**Date:** 2026-06-05  
**Auditor:** Guinevere (Sisyphus-Junior executor)  
**Scope:** Phase 9 (Financial Tracking) and Phase 10 (Production Hardening) steps from `stepprompts/StepPrompts.md`  
**Reference:** ADR-035 (Hermes NousResearch Migration Architecture, Accepted 2026-06-04)  
**Status:** P9 and P10 are NOT YET IMPLEMENTED — this audit assesses forward compatibility

---

## Executive Summary

**36 steps audited (13 P9 + 21 P10 + 2 transition checklists).** The Hermes migration (ADR-035) fundamentally changes the Discord gateway from custom `discord.py` (`bot.py`, `conversational_handler.py`, `session_adapter.py`) to Hermes Agent native gateway with hook/plugin architecture. This audit identifies **2 CONFLICTS** (both in P9 — Discord slash command steps), **13 NEEDS-UPDATE** (service name references, notification pipelines, runbook sections), and **19 VALID** (infrastructure/data-layer steps that are implementation-agnostic).

**Key finding:** Financial data pipeline (P9-001 through P9-007, P9-010 through P9-012) is largely unaffected — PostgreSQL, TimescaleDB, Redis, FastAPI, Grafana, and the parsing pipeline are all implementation-agnostic. The conflicts are concentrated in P9-008 and P9-009 (Discord slash commands that assume `discord.py` Cog/Interaction patterns). P10 hardening steps are mostly infrastructure-level and survive the migration, but 10 of 21 need service name updates and notification pipeline adjustments.

---

## Classification Legend

| Classification | Meaning |
|---|---|
| **VALID** | Step is implementation-agnostic. Survives Hermes migration unchanged. Can be implemented as-written. |
| **NEEDS-UPDATE** | Step references deprecated architecture (service names, notification pipeline, bot.py patterns) but core logic survives. Minor spec revision needed before implementation. |
| **CONFLICTS-WITH-HERMES** | Step ASSUMES old `discord.py` architecture. Must be substantially rewritten using Hermes plugin/hook patterns before implementation. Blocked until Hermes Phase 2 (Discord Gateway) is complete. |

---

## Phase 9: Financial Tracking (Stabilization) — 13 Steps

### P9-001: Financial Data Model + Schema Audit + ClassificationMetaMixin Fix

**Classification: VALID**

**Rationale:** Pure PostgreSQL schema work. Audits `financial` schema, verifies TimescaleDB hypertable, fixes `ClassificationMetaMixin` on `OptimizationLog` model, creates CRUD service stubs. Zero Discord or bot.py dependencies. All references are to PostgreSQL (`psql`), Alembic, and `src/financial/` directory.

**ADR-035 Impact:** None. PostgreSQL remains primary write authority (Pillar 2: Memory = HYBRID). Financial schema is unchanged.

---

### P9-002: Transaction Table Migration (TimescaleDB Hypertable)

**Classification: VALID**

**Rationale:** Pure PostgreSQL/TimescaleDB work. Extends `financial.transactions` hypertable with SMS banking columns, adds indexes, check constraints, compression policy. Creates `TransactionRepository` CRUD stub. No Discord dependencies.

**ADR-035 Impact:** None. TimescaleDB extension and PostgreSQL remain unchanged.

---

### P9-003: Budget Table Migration

**Classification: VALID**

**Rationale:** Creates `financial.budget_categories` table with trigger function, seeds 8 default categories, creates `BudgetRepository` CRUD stub. Pure PostgreSQL work with Alembic migrations. The only external reference is to `src/loops/enforcer.py` (Redis BudgetEnforcer) which is unchanged.

**ADR-035 Impact:** None.

---

### P9-004: Tasker Notification Capture (SMS Webhook Endpoint)

**Classification: NEEDS-UPDATE**

**Rationale:** The FastAPI webhook endpoint itself (`src/financial/webhook.py`) is implementation-agnostic — it receives HTTP POST, authenticates via HMAC-SHA256, rate-limits via Redis, queues to Redis, and stores in PostgreSQL. No `discord.py` dependency.

**Issues Found:**

| Reference | Location | Issue |
|---|---|---|
| `systemctl restart guinevere-api` | Commands §4, Rollback | **Minor:** Service name `guinevere-api` may change under Hermes. The FastAPI service is separate from the Discord gateway and should survive, but the exact service unit name needs verification. |
| `src/core/main.py` registration | Commands §3 | **Minor:** FastAPI app registration point. Should be unchanged under Hermes (Hermes replaces Discord gateway, not the API layer). |
| `classification_level='CRITICAL'` | Webhook inline code | **No issue:** Classification is PostgreSQL-level, unaffected. |

**Recommendation:** Verify `guinevere-api` systemd service name post-Hermes before implementing. The webhook code itself is valid as-written.

---

### P9-005: SMS Parsing Pipeline (Unified Regex + Indonesian Decimal)

**Classification: VALID**

**Rationale:** Python consumer daemon that reads from Redis `financial.sms_queue`, parses bank SMS with per-bank regex, writes to `financial.transactions` via `TransactionRepository`. Entirely self-contained. References to `src/loops/enforcer.py` (Redis BudgetEnforcer) are unchanged. No `discord.py` references.

**ADR-035 Impact:** None.

---

### P9-006: Transaction Classification (15+ Indonesian Spending Categories)

**Classification: VALID**

**Rationale:** Python classifier with keyword matching and LLM fallback. Categorizes transactions from P9-005 parser. References `ToolCostTracker` (Redis DB5) for LLM/API cost integration. The Redis-to-PostgreSQL bridge reference (P9-012) is unaffected by Hermes.

**ADR-035 Impact:** None. LLM cost tracking via Redis DB5 is unchanged. The LLM call for category suggestion uses 9Router (Pillar 5: LLM = RETAIN).

---

### P9-007: Budget Tracking + Alert Levels (Real-Time Threshold Enforcement)

**Classification: NEEDS-UPDATE**

**Rationale:** Core budget logic (threshold checks, freeze signals, monthly reset, dual-write Redis+PostgreSQL) is implementation-agnostic. The issue is the Discord notification delivery pipeline.

**Issues Found:**

| Reference | Location | Issue |
|---|---|---|
| "Discord alert to Faiz via existing notification pipeline" | Context §8789 | **Medium:** Under Hermes, notifications go through Hermes plugin `on_tool_call()` or a custom notification hook, not `bot.py`'s `send_message()`. The notification *content* (embed format) is unchanged; the *delivery mechanism* changes. |
| `systemctl status guinevere-discord` | Troubleshooting §8934 | **Minor:** Service name changes to Hermes gateway. |
| `discord.py` package dependency reference | Pre-flight §8798 | **Minor:** `discord.py` is replaced by Hermes. Package dependency changes. |

**Recommendation:** When implementing, use Hermes notification hook instead of `bot.py` channel send. Budget logic is unchanged. Update service name references.

---

### P9-008: /finance summary + /finance add (Discord Slash Commands)

**Classification: CONFLICTS-WITH-HERMES**

**Rationale:** This step is **fully blocked** until Hermes Phase 2 (Discord Gateway) is complete. The step assumes `discord.py` Cog architecture throughout.

**Hermes Conflicts:**

| Current Pattern | Hermes Equivalent | Migration Effort |
|---|---|---|
| `discord.py Cog` (`class FinanceCommands(commands.Cog)`) | Hermes plugin with `ctx.register_command()` | **Rewrite:** Cog → Plugin class |
| `discord.Embed` with color coding | Hermes native embed support | **Adapt:** Hermes supports embeds natively. Format preserved. |
| `@commands.is_owner()` / Discord user ID check | Hermes RBAC or plugin permission check | **Rewrite:** Use Hermes RBAC or plugin-level owner check |
| `bot.load_extension('src.financial.commands')` | Hermes plugin registration in `config.yaml` | **Rewrite:** Plugin registration via config, not `load_extension` |
| `bot.tree.sync()` | Hermes auto-registers commands | **Remove:** No manual sync needed |
| `systemctl restart guinevere-discord` | `hermes gateway restart` or systemd Hermes unit | **Replace:** Different service management |
| `from src.discord.bot import bot` | Plugin receives Hermes context | **Rewrite:** Plugin API, not global bot object |

**ADR-035 Mapping:** This is a MEDIUM feasibility command (similar to `/cost`, `/budget` in the ADR-035 command migration table). The 36% code reduction estimate applies — Discord.py boilerplate (embed builders, interaction defer/response) is eliminated.

**Recommendation:** Do NOT implement this step before Hermes Phase 2. After Hermes cutover, implement as a Hermes plugin using `ctx.register_command()`. The business logic (budget queries, embed formatting, manual transaction insertion) is reusable.

---

### P9-009: /finance report Command — Detailed Financial Breakdown

**Classification: CONFLICTS-WITH-HERMES**

**Rationale:** Same situation as P9-008 but more complex due to CSV export via `discord.File`.

**Hermes Conflicts:**

| Current Pattern | Issue |
|---|---|
| `discord.Interaction`, `discord.File` for CSV attachment | Hermes plugin API for file attachments is different |
| `@owner_only()` decorator from `src.bot.utils.permissions` | Must use Hermes RBAC or plugin permission check |
| `app_commands.Group` with Discord.py decorators | Hermes `ctx.register_command()` with options |
| `interaction.response.defer(thinking=True)` | Hermes handles defer natively |
| `interaction.followup.send()` for deferred responses | Hermes plugin response API |

**Recommendation:** Blocked until Hermes Phase 2. Implement as Hermes plugin after cutover. Query functions (`get_category_breakdown`, `get_top_merchants`, etc.) remain unchanged — only the Discord interface layer changes.

---

### P9-010: Monthly PDF Report — WeasyPrint + Jinja2 + Matplotlib

**Classification: VALID**

**Rationale:** PDF generation pipeline is entirely server-side (WeasyPrint + Jinja2 HTML templates + Matplotlib charts). No `discord.py` dependency in the core generation logic. The step references S3 upload and systemd timer — both unchanged under Hermes.

**ADR-035 Impact:** None. If the generated PDF needs to be sent via Discord, that notification path changes (Hermes plugin instead of `bot.py` send), but the PDF *generation* is unaffected.

**Recommendation:** Implement as-written. If post-generation Discord notification is needed, defer the notification portion until Hermes Phase 2.

---

### P9-011: FinOps Dashboard — grafanalib + Grafana File Provisioning

**Classification: VALID**

**Rationale:** Grafana dashboard provisioning via `grafanalib` Python library. Grafana is accessed via browser, not Discord. Prometheus datasource and TimescaleDB queries are unchanged. The Redis bridge reference (P9-012) is unaffected.

**ADR-035 Impact:** None. Grafana, Prometheus, and Loki are unchanged by Hermes.

---

### P9-012: Provider Cost Attribution — Redis-to-PG Bridge Pipeline

**Classification: VALID**

**Rationale:** Redis DB5 cost tracking data is synced to PostgreSQL `financial.transactions` via an async bridge daemon. Uses systemd timer and Python bridge service. No `discord.py` dependency. Provider attribution (9Router, DeepSeek, GPT-5.5) uses 9Router which is unchanged (Pillar 5: LLM = RETAIN).

**ADR-035 Impact:** None. 9Router is retained. Redis DB5 cost tracking is unchanged.

---

### P9-013: Financial E2E Test — Full Pipeline Integration

**Classification: NEEDS-UPDATE**

**Rationale:** The E2E test validates the entire P9 pipeline. While the core pipeline (SMS → parse → classify → budget → store) is implementation-agnostic, the test may include Discord command testing (P9-008/P9-009) which needs Hermes plugin equivalents.

**Issues Found:**

| Reference | Issue |
|---|---|
| `/finance` commands testing (P9-008/P9-009) | Test must use Hermes plugin API instead of `discord.py` interaction simulation |
| `source = 'test'` isolation strategy | Still valid — unaffected by Hermes |
| Coverage threshold >= 70% on `src/financial/` | Still valid — `src/financial/` directory is unaffected |

**Recommendation:** Implement after Hermes Phase 2. Test Discord command portions using Hermes plugin test harness. Pipeline integration tests (SMS → parse → classify → budget → DB) can be implemented immediately.

---

## Phase 10: Production Hardening (Stabilization) — 21 Steps

### P10-001: Security Audit (Pen Test + Vuln Scan)

**Classification: VALID**

**Rationale:** nmap, lynis, bandit, semgrep, trivy, pip-audit — all scan the system and source code. Implementation-agnostic. The `src/` directory structure changes under Hermes (files deleted/refactored), but the scanners run against whatever code exists.

**Note:** Post-Hermes, bandit/semgrep scan results will be different (fewer files, new hook/plugin code to scan). This is expected — the audit step itself is valid regardless of code content.

**ADR-035 Impact:** None on the scanning methodology. The scan surface changes but the step is valid.

---

### P10-002: PostgreSQL Performance Tuning

**Classification: VALID**

**Rationale:** PostgreSQL 16 configuration tuning (shared_buffers, work_mem, effective_cache_size, PgBouncer, TimescaleDB compression, continuous aggregates). Infrastructure-level, zero application code dependency.

**ADR-035 Impact:** None. PostgreSQL remains primary (ADR-007). Hermes SQLite is supplementary transient storage only.

---

### P10-003: Redis maxmemory Tuning

**Classification: VALID**

**Rationale:** Redis 7 configuration tuning (maxmemory, eviction policy, AOF+RDB persistence, ACL users, active defrag, cost key protection). Infrastructure-level. Redis DB assignments (DB0-DB5 per ADR-030) are unchanged.

**ADR-035 Impact:** Minor — ADR-035 §146 notes a pre-existing runtime-vs-ADR discrepancy for Redis DB assignments (DB4 used for sessions vs ADR-030 assigning DB3). This is documented but not resolved by ADR-035. P10-003 should verify DB assignments match current runtime state.

---

### P10-004: Systemd Resource Limits

**Classification: NEEDS-UPDATE**

**Rationale:** Systemd hardening directives (MemoryMax, CPUQuota, ProtectSystem, NoNewPrivileges, etc.) are generally valid. The issue is service names and service count change under Hermes.

**Issues Found:**

| Reference | Issue |
|---|---|
| Service loop includes `guinevere-bot` | **Replaced:** `guinevere-bot` → Hermes gateway service. Service name changes. Memory/CPU limits need recalculation for Hermes gateway. |
| CFFI exceptions document lists `guinevere-bot` | **Update:** Hermes gateway may also use CFFI (cryptography, pydantic-core). Document accordingly. |
| `guinevere-api guinevere-worker guinevere-scheduler guinevere-bot` enumeration | **Update:** Service list changes — some services may be consolidated under Hermes, new services may appear. |

**Recommendation:** Update service enumeration to reflect post-Hermes service topology. Recalculate resource limits for the Hermes gateway process. The hardening directives themselves (NoNewPrivileges, ProtectSystem, etc.) remain valid.

---

### P10-005: Backup Automation Full Test

**Classification: VALID**

**Rationale:** End-to-end backup test: pg_dump + Redis BGSAVE + config tar + SOPS encrypt → S3 + R2 upload → restore verification. Fully infrastructure-level. PostgreSQL, Redis, S3, R2 — all unchanged.

**ADR-035 Impact:** None. `hermes backup` is a new complementary tool (ADR-035 §1268) but doesn't replace the PostgreSQL/Redis backup pipeline.

---

### P10-006: Disaster Recovery Drill

**Classification: VALID**

**Rationale:** Full DR drill: simulate data loss, restore from S3/R2 backups, verify service recovery. Infrastructure-level. Service restoration commands use systemd which is unchanged. The services being restored may have different names post-Hermes but the DR procedure concept is identical.

**Note:** The universal kill-switch changes: `hermes gateway stop && sudo systemctl start guinevere-discord` → but this is documented in ADR-035 §1210. The DR drill can use the new kill-switch.

**ADR-035 Impact:** Minor — DR plan should reference Hermes-specific rollback commands (`hermes gateway stop`) alongside current commands.

---

### P10-007: Self-Deploy Pipeline

**Classification: NEEDS-UPDATE**

**Rationale:** The deploy script (`scripts/deploy.sh`) with preflight checks, atomic restart, health validation, and rollback is conceptually valid. References to service names and Discord notification need updating.

**Issues Found:**

| Reference | Issue |
|---|---|
| `systemctl restart guinevere-*` service patterns | **Update:** Post-Hermes service names may differ. Service restart sequence changes. |
| Discord webhook notification for deploy status | **Update:** Notification delivery mechanism changes under Hermes. Webhook URL may be different. |
| Health endpoint `http://localhost:8080/health` | **Verify:** Ensure health endpoint exists post-Hermes. May be on different port. |

**Recommendation:** Update deploy script service names and notification webhook to post-Hermes equivalents. The deploy logic (preflight → restart → health check → rollback) is valid.

---

### P10-008: GitHub Actions CI Pipeline

**Classification: VALID**

**Rationale:** GitHub-hosted CI with pytest, bandit, mypy, coverage. The CI pipeline runs against the codebase — whatever shape it takes post-Hermes. The workflow file (`.github/workflows/ci.yml`) needs to test the new code structure but the step of *creating* the CI pipeline is valid.

**Note:** Coverage threshold (80% target) may be temporarily lower post-migration due to code reduction (31.2% fewer lines). Adjust threshold accordingly.

---

### P10-009: CD via systemd Timer

**Classification: NEEDS-UPDATE**

**Rationale:** CD timer that triggers deploy on schedule. References `guinevere-core`, `guinevere-9router`, `guinevere-gateway` services.

**Issues Found:**

| Reference | Issue |
|---|---|
| `guinevere-gateway` service name | **Verify:** May be the Hermes gateway service. If Hermes uses different service name, update. |
| `guinevere-core` service | **Verify:** Core service may be consolidated under Hermes. |
| Service dependency ordering in timer | **Update:** Dependency chain changes — Hermes gateway must start after PostgreSQL, Redis, and 9Router. |

**Recommendation:** Update service names and dependency ordering to match post-Hermes topology. Timer concept is valid.

---

### P10-010: Rollback Automation

**Classification: NEEDS-UPDATE**

**Rationale:** Rollback script with automatic detection of failed deploy. References systemd service names and restart patterns.

**Issues Found:** Similar to P10-007/P10-009 — service names and restart commands need updating for Hermes. The rollback logic (detect failure → restore previous version → restart services → health check) is valid.

---

### P10-011: Key Rotation Procedure

**Classification: VALID**

**Rationale:** SOPS+age key rotation procedure. Pure cryptography/infrastructure — zero application code dependency.

**ADR-035 Impact:** None. `hermes secrets` provides additional secret management but doesn't replace SOPS+age for infrastructure secrets.

---

### P10-012: Log Rotation

**Classification: VALID**

**Rationale:** logrotate configuration for application logs, PostgreSQL logs, Redis logs, nginx/Caddy logs. Infrastructure-level. Zero application code dependency.

**ADR-035 Impact:** Minor — Hermes generates its own logs (`~/.hermes/logs/`) that should be added to logrotate configuration.

---

### P10-013: Rate Limiting

**Classification: VALID**

**Rationale:** FastAPI middleware for API rate limiting. References the API layer, not the Discord bot. ADR-035 does not change the FastAPI application.

**ADR-035 Impact:** None. Hermes replaces Discord gateway, not the API layer. However, Hermes has its own built-in rate limiting — the two rate limiters (API middleware + Hermes built-in) serve different purposes and don't conflict.

---

### P10-014: CORS Configuration

**Classification: VALID**

**Rationale:** FastAPI CORS middleware for Tailscale-internal origins. API-layer configuration, unaffected by Hermes.

**Note:** CORS headers include `X-Discord-User-Id` and `X-Guild-Id` which are Discord-specific. These may still be relevant if the API receives requests from Hermes plugins. Keep them.

---

### P10-015: Health Check Enhancement (Deep Checks)

**Classification: NEEDS-UPDATE**

**Rationale:** Deep health checks for PostgreSQL, Redis, 9Router, Discord bot, and disk. The Discord bot health check needs updating.

**Issues Found:**

| Reference | Issue |
|---|---|
| Discord bot health check (connectivity + latency) | **Replace:** Discord bot health check → Hermes gateway health check (`hermes doctor` equivalent) |
| `guinevere-gateway` service reference | **Verify:** Confirm this maps to Hermes gateway service |
| Gotify notification for health check failures | **Unchanged:** Gotify is independent of Discord |

**Recommendation:** Replace Discord bot health probe with Hermes gateway health probe. Other health checks (PostgreSQL, Redis, 9Router, disk) are unchanged.

---

### P10-016: Graceful Shutdown (SIGTERM + Drain)

**Classification: NEEDS-UPDATE**

**Rationale:** Graceful shutdown handler with drain-and-close sequence. The shutdown logic is valid but dependency list references `discord.py`.

**Issues Found:**

| Reference | Issue |
|---|---|
| "Discord.py bot running" in dependencies | **Replace:** Hermes gateway runs instead of discord.py bot. Graceful shutdown for Hermes uses `hermes gateway stop`. |
| `discord.py bot has close/cleanup method available` | **Remove:** Hermes gateway has its own shutdown sequence. |
| `guinevere-gateway` service reference | **Verify:** Should map to Hermes gateway. |

**Recommendation:** Update shutdown sequence to include Hermes gateway cleanup. The drain-and-close pattern for PostgreSQL, Redis, and cost tracker is unchanged.

---

### P10-017: Connection Pool Monitoring

**Classification: VALID**

**Rationale:** PostgreSQL (PgBouncer) and Redis connection pool monitoring via Prometheus metrics. Infrastructure-level, database-focused. Zero Discord dependency.

**ADR-035 Impact:** None.

---

### P10-018: Runbook Documentation

**Classification: NEEDS-UPDATE**

**Rationale:** Runbook documents operational procedures. Post-Hermes, new sections are needed.

**New Sections Required:**
- Hermes gateway management (`hermes gateway start/stop/restart`, log locations)
- Hook debugging (`hermes hooks list`, hook failure troubleshooting)
- Plugin lifecycle (`GuinevereSafetyPlugin` — loading, state recovery, crash behavior)
- Hermes backup/checkpoint procedures (`hermes backup`, `hermes checkpoints`)
- Shadow mode procedures (documented in ADR-035 §1234-1247)
- Universal kill-switch (`hermes gateway stop && systemctl start guinevere-discord` — ADR-035 §1210)

**Existing sections that survive:** PostgreSQL operations, Redis operations, backup/restore, systemd management, monitoring, incident response.

---

### P10-019: Load Testing (k6)

**Classification: NEEDS-UPDATE**

**Rationale:** k6 load testing scripts test API endpoints and Discord bot message throughput. Discord bot load testing patterns change under Hermes.

**Issues Found:**

| Reference | Issue |
|---|---|
| Discord bot message throughput testing | **Replace:** Hermes gateway has different throughput characteristics (streaming, auto-threading, circuit breaker). Test Hermes gateway instead of discord.py bot. |
| API endpoint load testing | **Unchanged:** FastAPI endpoints are unaffected. |
| WebSocket connection testing | **Adapt:** Hermes uses WebSocket for Discord gateway. Test Hermes WebSocket stability. |

**Recommendation:** Adapt Discord-related test scenarios for Hermes gateway. API load tests are unchanged.

---

### P10-020: Hardening Verification

**Classification: NEEDS-UPDATE**

**Rationale:** Final verification gate that checks all hardening steps pass. References `guinevere-discord` service verification.

**Issues Found:**

| Reference | Issue |
|---|---|
| Discord bot verification checklist items | **Replace:** Hermes gateway verification items |
| `systemctl is-active guinevere-discord` | **Replace:** Hermes gateway service status check |
| Discord bot-specific hardening checks | **Replace:** Hermes hook/plugin safety checks |

---

### P10-021: MVP Acceptance Gate (Tier 1 Reformat of P10-018b)

**Classification: NEEDS-UPDATE**

**Rationale:** Final MVP sign-off gate. References current system state and acceptance criteria inventory. Must be updated to reflect Hermes migration status and any deferred items.

---

## Summary Table

### Phase 9 (13 Steps)

| Step | Title | Classification | Blocked by Hermes? |
|---|---|---|---|
| P9-001 | Financial Data Model + Schema Audit | **VALID** | No |
| P9-002 | Transaction Table Migration (TimescaleDB) | **VALID** | No |
| P9-003 | Budget Table Migration | **VALID** | No |
| P9-004 | Tasker Notification Capture (SMS Webhook) | **NEEDS-UPDATE** | No (minor service name) |
| P9-005 | SMS Parsing Pipeline | **VALID** | No |
| P9-006 | Transaction Classification | **VALID** | No |
| P9-007 | Budget Tracking + Alert Levels | **NEEDS-UPDATE** | No (notification pipeline) |
| P9-008 | /finance summary + /finance add | **CONFLICTS-WITH-HERMES** | **Yes — Phase 2** |
| P9-009 | /finance report Command | **CONFLICTS-WITH-HERMES** | **Yes — Phase 2** |
| P9-010 | Monthly PDF Report (WeasyPrint) | **VALID** | No |
| P9-011 | FinOps Dashboard (grafanalib) | **VALID** | No |
| P9-012 | Provider Cost Attribution (Redis→PG) | **VALID** | No |
| P9-013 | Financial E2E Test | **NEEDS-UPDATE** | Partial (discord commands) |

### Phase 10 (21 Steps)

| Step | Title | Classification | Blocked by Hermes? |
|---|---|---|---|
| P10-001 | Security Audit (Pen Test + Vuln Scan) | **VALID** | No |
| P10-002 | PostgreSQL Performance Tuning | **VALID** | No |
| P10-003 | Redis maxmemory Tuning | **VALID** | No |
| P10-004 | Systemd Resource Limits | **NEEDS-UPDATE** | No (service names) |
| P10-005 | Backup Automation Full Test | **VALID** | No |
| P10-006 | Disaster Recovery Drill | **VALID** | No |
| P10-007 | Self-Deploy Pipeline | **NEEDS-UPDATE** | No (service names, webhook) |
| P10-008 | GitHub Actions CI Pipeline | **VALID** | No |
| P10-009 | CD via systemd Timer | **NEEDS-UPDATE** | No (service names) |
| P10-010 | Rollback Automation | **NEEDS-UPDATE** | No (service names) |
| P10-011 | Key Rotation Procedure | **VALID** | No |
| P10-012 | Log Rotation | **VALID** | No |
| P10-013 | Rate Limiting | **VALID** | No |
| P10-014 | CORS Configuration | **VALID** | No |
| P10-015 | Health Check Enhancement | **NEEDS-UPDATE** | No (discord bot probe) |
| P10-016 | Graceful Shutdown (SIGTERM + Drain) | **NEEDS-UPDATE** | No (discord.py ref) |
| P10-017 | Connection Pool Monitoring | **VALID** | No |
| P10-018 | Runbook Documentation | **NEEDS-UPDATE** | No (add Hermes sections) |
| P10-019 | Load Testing (k6) | **NEEDS-UPDATE** | No (discord bot → gateway) |
| P10-020 | Hardening Verification | **NEEDS-UPDATE** | No (verification items) |
| P10-021 | MVP Acceptance Gate | **NEEDS-UPDATE** | No (gate criteria) |

### Totals

| Classification | P9 Count | P10 Count | Total |
|---|---|---|---|
| **VALID** | 8 | 11 | **19** |
| **NEEDS-UPDATE** | 3 | 10 | **13** |
| **CONFLICTS-WITH-HERMES** | 2 | 0 | **2** |

---

## Key Findings

### 1. Financial Data Pipeline is Largely Unaffected

P9-001 through P9-007 form a PostgreSQL-centric data pipeline (schema → transactions → budget → SMS capture → parse → classify → enforce). All seven steps operate on PostgreSQL, TimescaleDB, Redis, and FastAPI — none of which are changed by the Hermes migration. **8 of 13 P9 steps are VALID as-written.**

### 2. Discord Command Steps are the Sole Hard Conflicts

P9-008 and P9-009 are the only steps that **must** be rewritten. Both assume `discord.py` Cog/Interaction patterns that Hermes replaces with plugin/`ctx.register_command()` patterns. According to ADR-035's command migration table (§281-351), finance commands fall into the MEDIUM feasibility category (plugin port with custom logic). The business logic (budget queries, embed formatting, transaction insertion) survives — only the Discord interface layer changes.

**Recommendation:** Defer P9-008 and P9-009 until after Hermes Phase 2 (Discord Gateway cutover). Implement as Hermes plugins using the same query functions. Estimated effort: 2-3 hours per command (down from 3 hours each, since Discord.py boilerplate is eliminated).

### 3. P10 Hardening Steps are Mostly Infrastructure-Level

P10 steps focus on security scanning, database tuning, backup/DR, CI/CD, and operational procedures. These are **infrastructure-level concerns** that survive the application-level migration to Hermes. The 10 NEEDS-UPDATE classifications are for service name references, notification delivery mechanisms, and runbook sections — all minor spec updates, not rewrites.

### 4. Service Name References are the Most Common Issue

The most frequent pattern in NEEDS-UPDATE steps is references to `guinevere-discord`, `guinevere-bot`, or `guinevere-gateway` service names. These need to be verified against the actual post-Hermes systemd service topology. The underlying hardening/config logic is valid regardless of service name.

### 5. No P9/P10 Steps Assume Old bot.py Internals

None of the audited steps reference `bot.py` internals (message pipeline, `conversational_handler.py`, `session_adapter.py`). The steps that reference the Discord bot do so at the interface level (slash commands, notification delivery) — not at the implementation level. This means the stabilization phases were designed with reasonable abstraction from the bot implementation.

### 6. P9 Can Be Partially Implemented Before Hermes

The data pipeline steps (P9-001 through P9-007, P9-010 through P9-012) can be implemented **before** the Hermes migration. Only P9-008, P9-009, and portions of P9-013 (Discord command testing) must wait. This allows the financial tracking system to be built and tested with synthetic SMS data while the Hermes migration proceeds in parallel.

---

## Recommended Implementation Order

```
Phase A (NOW — pre-Hermes, parallel with ADR-035 Phase 0-1):
  P9-001 → P9-002 → P9-003 → P9-004 → P9-005 → P9-006 → P9-007
  (Financial data pipeline: schema → capture → parse → classify → enforce)
  P9-010, P9-011, P9-012 (PDF reports, Grafana, cost bridge)

Phase B (AFTER Hermes Phase 2 — Discord Gateway cutover):
  P9-008, P9-009 (Discord /finance commands as Hermes plugins)
  P9-013 (E2E test including Discord command testing)

Phase C (post-Hermes, infrastructure hardening):
  P10-001 through P10-021 (with service name updates from this audit)

Parallel opportunity: P10-002, P10-003, P10-005, P10-006, P10-008, P10-011,
  P10-012, P10-013, P10-014 can be done ANYTIME (fully VALID, no Hermes dependency)
```

---

## Appendix: ADR-035 Cross-Reference

### ADR-035 Sections Relevant to P9/P10

| ADR-035 Section | Relevance to P9/P10 |
|---|---|
| Pillar 1: Discord = MIGRATE (§259-366) | P9-008/P9-009 must become Hermes plugins. `ctx.register_command()` replaces `discord.py` Cog. |
| Pillar 2: Memory = HYBRID (§584-606) | PostgreSQL+pgvector unchanged — all P9 financial schema work survives. |
| Pillar 4: MCP = HYBRID (§1118-1143) | Custom MCP tools (postgres, redis) unchanged — P9 data pipeline survives. |
| Pillar 5: LLM = RETAIN (§1145-1160) | 9Router unchanged — P9-012 cost attribution survives. Budget enforcement via `pre_tool_call` hook replaces Redis-only enforcement for P9-007. |
| Command Migration Table (§281-351) | `/cost`, `/budget`, `/cost alert` classified as LOW feasibility (hook+plugin). Similar pattern for `/finance` commands. |
| Migration Phases (§1179-1193) | Phase 7 (Hardening + Monitoring, 2-3 days) aligns with P10 but at Hermes level. |
| Code Reduction (§1161-1178) | 36% reduction in command files expected. P9-008/P9-009 will be shorter as Hermes plugins. |
| Budget Enforcement (§1159) | Custom `pre_tool_call` hook enforces $30/month cap. Complements P9-007 budget tracking. |

---

## Footer

| Field | Value |
|---|---|
| Audit Date | 2026-06-05 |
| Auditor | Guinevere (Sisyphus-Junior executor) |
| Source Files | `stepprompts/StepPrompts.md` (P9: lines 7616-11529, P10: lines 11530-19300+), `adr/ADR-035-hermes-migration.md` (full) |
| ADR-035 Status | Accepted (2026-06-04) |
| P9/P10 Status | Not yet implemented |
| Next Action | Implement P9-001 through P9-007 (pre-Hermes safe). Defer P9-008/P9-009 until Hermes Phase 2 complete. |