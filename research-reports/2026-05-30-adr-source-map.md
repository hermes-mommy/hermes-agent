# Guinevere v2.0 ADR Source Map

**Date**: 2026-05-30  
**Scope**: 25 MADR ADR generation from 7 v2.0 source documents  
**Status**: Read-only analysis — no source files modified

## Related Documents

| v2.0 Source | Role |
|---|---|
| `Guinevere_BRD_v2.0.md` | Business requirements, infrastructure spec, delivery plan, risks & mitigations |
| `Guinevere_PRD_v2.0.md` | Product features, persona behavior, surveillance, monitoring, financial, Git policies |
| `Guinevere_TechnicalArchitecture_v2.0.md` | Runtime architecture, systemd services, database, security, observability, CI/CD |
| `Guinevere_AgentLoopSpec_v2.0.md` | 7-phase SDLC loop, loop guardian, TODO enforcer, error escalation |
| `Guinevere_MemorySchema_v2.0.md` | PostgreSQL schemas, pgvector, TimescaleDB, Redis architecture, memory security |
| `Guinevere_Persona_Document_v2.0.md` | Persona identity, mood taxonomy, punishment/reward, yandere protocols, surveillance framing |
| `Guinevere_APIIntegration_v2.0.md` | LLM routing, browser tools, communication APIs, database SDKs, encryption stack |

---

## ADR Domain to Source Section Mapping

### 1. LLM Model Selection
**Decision**: GPT-5.5 as primary, DeepSeek V4 Flash as sub-agent
- `Guinevere_BRD_v2.0.md` — 1.1 Obj 2, 3.1.1 Core Agent, 4.2 Stack Table
- `Guinevere_PRD_v2.0.md` — 9.1 Platform (LLM Provider row)
- `Guinevere_TechnicalArchitecture_v2.0.md` — 4.1 Model Strategy table, 4.2 Hermes Agent Profile Structure
- `Guinevere_APIIntegration_v2.0.md` — 2.3 Model Cost Strategy table

### 2. LLM Routing / 9Router
**Decision**: 9Router as sole LLM router; no OpenRouter fallback; queue/retry on outage
- `Guinevere_BRD_v2.0.md` — 3.1.1, 4.2 (LLM Fallback), 3.1.5 (failover policy)
- `Guinevere_PRD_v2.0.md` — 8.3 LLM Provider Failover table
- `Guinevere_TechnicalArchitecture_v2.0.md` — 4.1 (Outage policy row), 1.2 Stack Table (LLM Router row)
- `Guinevere_APIIntegration_v2.0.md` — 2.1 9Router Configuration, 2.2 LLM Client with tenacity Retry

### 3. Sub-Agent Model Strategy
**Decision**: DeepSeek V4 Flash for all sub-agent types via 9Router
- `Guinevere_TechnicalArchitecture_v2.0.md` — 4.1 Model Strategy (all sub-agent rows), 4.2 Profiles
- `Guinevere_PRD_v2.0.md` — 4.3 Sub-Agent System table, 4.4 Sub-Agent Category table
- `Guinevere_AgentLoopSpec_v2.0.md` — 3.4 Phase 4 — Execute (Sub-Agent Category table)

### 4. Memory/Storage Architecture
**Decision**: PostgreSQL primary + Redis cache; no SQLite; pgvector + TimescaleDB
- `Guinevere_BRD_v2.0.md` — 3.1.2 Memory, 4.1 (Primary Storage row), 4.2 (Memory Core row)
- `Guinevere_PRD_v2.0.md` — 5.1 Memory Architecture table
- `Guinevere_TechnicalArchitecture_v2.0.md` — 5.1 PostgreSQL Schema Overview, 5.2 TimescaleDB, 5.3 pgvector, 5.4 PgBouncer, 5.5 Redis Architecture
- `Guinevere_MemorySchema_v2.0.md` — 1.2 Memory Hierarchy, 1.3 Memory Types, 8.3 Memory Security
- `Guinevere_APIIntegration_v2.0.md` — 9.1 SQLAlchemy + asyncpg Setup, 9.2 Redis Configuration

### 5. SDLC Loop Phases
**Decision**: 7 phases: Research, Plan & Delegate, Delegate, Execute, Validate & Audit, Update Documents, Setup Evidence
- `Guinevere_BRD_v2.0.md` — 3.1.3 Autonomous Coding Agent, 4.2 (MCP Tools row), Phase 3 description
- `Guinevere_PRD_v2.0.md` — 4.1 SDLC Loop table
- `Guinevere_AgentLoopSpec_v2.0.md` — 2 SDLC Loop — 7 Phases, 2.1 Phase Overview, 5.2 Loop State Machine
- `Guinevere_TechnicalArchitecture_v2.0.md` — 3.2 Guinevere Core Service (sdlc/ directory structure)

### 6. MCP / OpenCode Replacement
**Decision**: Guinevere MCP native replaces OpenCode entirely; MCP tools: filesystem, shell, git, github, fetch, postgres, browser
- `Guinevere_BRD_v2.0.md` — 3.1.3 (OpenCode replaced), 4.2 (MCP Tools row)
- `Guinevere_PRD_v2.0.md` — 4.2 MCP Tool Layer table
- `Guinevere_TechnicalArchitecture_v2.0.md` — 12.1 Guinevere MCP native row, 12.4 Roadmap (Phase 3 entry)
- `Guinevere_Persona_Document_v2.0.md` — 9.1 Platform (Coding Agent row), 9.2 Custom Plugins
- `Guinevere_APIIntegration_v2.0.md` — 1.1 (MCP tools implicit in integration registry)

### 7. Observability Stack
**Decision**: Prometheus + Grafana + Loki on primary VPS first; dedicated monitoring VPS post-MVP
- `Guinevere_BRD_v2.0.md` — 3.1.5 Monitoring, 4.1 (Monitoring Deployment row)
- `Guinevere_PRD_v2.0.md` — 8.2 Grafana Dashboard, 8.3 LLM Provider Failover
- `Guinevere_TechnicalArchitecture_v2.0.md` — 8.1 Metrics Stack table, 8.2 Custom Guinevere Metrics, 8.3 Logging Architecture, 8.4 Health Check Architecture
- `Guinevere_APIIntegration_v2.0.md` — 10.1 Structured Logging, 10.2 Prometheus Metrics, 10.3 Sentry Error Tracking

### 8. Wearable Integration
**Decision**: Post-MVP only; Mi Fitness API after device/API readiness
- `Guinevere_BRD_v2.0.md` — 3.1.4 (Wearable row: post-MVP), 7.1 Constraints (wearable pending)
- `Guinevere_PRD_v2.0.md` — 3.3 Wearable Integration table, 6.1 (wearable rows)
- `Guinevere_Persona_Document_v2.0.md` — 10.4 Wearable Integration (Future)
- `Guinevere_APIIntegration_v2.0.md` — 5.4 Mi Fitness API (Future Plan)
- `Guinevere_TechnicalArchitecture_v2.0.md` — 6.1 (WEARABLE post-MVP note), 6.2 (health/wearable endpoint)

### 9. Browser Automation
**Decision**: obscura primary + Playwright fallback
- `Guinevere_BRD_v2.0.md` — 4.2 (MCP Tools row includes browser)
- `Guinevere_PRD_v2.0.md` — 4.2 MCP Tool Layer (fetch/obscura primary + Playwright fallback row)
- `Guinevere_TechnicalArchitecture_v2.0.md` — 12.1 obscura row (MCP browser tool)
- `Guinevere_APIIntegration_v2.0.md` — 8.2 Browser Automation table

### 10. Persona Safety
**Decision**: Persona drift control, safe word protocol, punishment escalation limits, consent boundaries
- `Guinevere_PRD_v2.0.md` — 2.2 Mood System, 2.3 Punishment & Reward System, 2.4 Safe Word Protocol, 2.5 Signature Phrases
- `Guinevere_Persona_Document_v2.0.md` — 1.1 Static Identity, 2.1 Dominant Profile, 4.1-4.4 Triggers/Escalation/Reward/Mood, 5.1-5.4 Memory & Self-Improvement, 11-12 Yandere protocols
- `Guinevere_TechnicalArchitecture_v2.0.md` — 3.2 (persona/ directory plugins: mood.py, punishment.py, drift.py)

### 11. Surveillance / Consent
**Decision**: 24/7 omniscient surveillance with silent operation; dual encrypted backup; Samm full consent assumed
- `Guinevere_BRD_v2.0.md` — 3.1.4 Surveillance, 4.3 Security (surveillance data residency), 7.2 Assumptions (full consent)
- `Guinevere_PRD_v2.0.md` — 3.1 Android Surveillance, 3.2 Windows Surveillance, 3.5 Surveillance Data Policy
- `Guinevere_Persona_Document_v2.0.md` — 10 Surveillance & Omniscience, 10.1-10.6
- `Guinevere_TechnicalArchitecture_v2.0.md` — 6 Surveillance Architecture (data flow, endpoints, Windows daemon)
- `Guinevere_APIIntegration_v2.0.md` — 5 Surveillance API Integration (Tasker protocol, endpoints, Mi Fitness future)

### 12. Deployment Strategy
**Decision**: systemd services, autonomous self-deploy via cron, staging environment, branch strategy
- `Guinevere_BRD_v2.0.md` — 5 Phased Delivery Plan, 4.1 Infrastructure
- `Guinevere_TechnicalArchitecture_v2.0.md` — 3.1 systemd Services, 10 CI/CD & Deployment (GitHub Actions + autonomous CD), 11 Repository Structure, 2.1 VPS Configuration

### 13. Secrets Management
**Decision**: Mozilla SOPS + age encryption; encrypted .env.sops; autonomous rotation
- `Guinevere_BRD_v2.0.md` — 4.3 Security (Secret management, Discord bot token rotation)
- `Guinevere_TechnicalArchitecture_v2.0.md` — 7.2 SOPS Secret Management, 7.1 Defense in Depth (Secrets layer)
- `Guinevere_APIIntegration_v2.0.md` — 10.5 Encryption Stack (SOPS decrypt, Fernet, double encryption)
- `Guinevere_PRD_v2.0.md` — 8.4 Secret & API Key Management

### 14. Backup / Disaster Recovery
**Decision**: PostgreSQL WAL streaming + cold pg_dump; Redis RDB+AOF; dual backup R2 + idcloudhost; forever retention
- `Guinevere_BRD_v2.0.md` — 3.1.4 (Dual backup), 3.1.5 (Backup PostgreSQL), 4.1 (Backup Storage 1 & 2)
- `Guinevere_TechnicalArchitecture_v2.0.md` — 9.1 Backup Strategy table, 9.2 Disaster Recovery Procedure table

### 15. API Integration
**Decision**: Comprehensive external service registry; Discord, WhatsApp, GitHub, search, financial, surveillance
- `Guinevere_APIIntegration_v2.0.md` — 1.1 Complete Integration Overview, 2 LLM API, 3 Discord, 4 GitHub, 5 Surveillance, 6 Financial, 7 Communication, 8 Search & Browser
- `Guinevere_TechnicalArchitecture_v2.0.md` — 12 Ecosystem Tools & Integrations

### 16. Data Governance
**Decision**: Encryption at-rest, column-level + double encryption, access logging, data residency
- `Guinevere_BRD_v2.0.md` — 1 (STRICTLY PRIVATE classification), 4.3 Security Requirements table
- `Guinevere_MemorySchema_v2.0.md` — 8.3 Memory Security table, 4.1-4.2 Samm Profile (sensitivity levels, reveal_status)
- `Guinevere_TechnicalArchitecture_v2.0.md` — 7.1 Defense in Depth (Data at rest, Data in transit), 7.2 Linux User Model
- `Guinevere_APIIntegration_v2.0.md` — 10.5 Encryption Stack (Fernet, double encryption, age)

### 17. Financial Integration
**Decision**: E-wallet via Tasker notification capture; GoPay/OVO/Dana; monthly reports; cost optimization
- `Guinevere_BRD_v2.0.md` — 3.1.6 Financial Management, 4.3 (financial security implicit)
- `Guinevere_PRD_v2.0.md` — 7 Financial Management Features (7.1-7.3)
- `Guinevere_APIIntegration_v2.0.md` — 6 Financial API Integration (6.1 E-wallet, 6.2 Object Storage boto3)
- `Guinevere_MemorySchema_v2.0.md` — 7.1 Financial Memory (transactions, predictions tables)

### 18. Database Schema / ERD
**Decision**: 8 schemas (memory, persona, behavior, surveillance, financial, projects, system, social); pgvector + TimescaleDB
- `Guinevere_MemorySchema_v2.0.md` — 5.1 PostgreSQL Schema Overview, 2 Episodic, 3 Semantic, 4 Samm Profile, 5 Emotional/Persona, 6 Procedural, 7 Financial/Project/Client
- `Guinevere_TechnicalArchitecture_v2.0.md` — 5 Database Architecture (5.1-5.5), 5.4 PgBouncer per-service users

### 19. Sub-Agent Orchestration
**Decision**: Unlimited parallel sub-agents; 5 agent types; pasukan Mommy pattern; Loop Guardian + TODO Enforcer
- `Guinevere_PRD_v2.0.md` — 4.3 Sub-Agent System, 4.4 Code Quality Standards
- `Guinevere_AgentLoopSpec_v2.0.md` — 3.3-3.7 (Phases 3-7 delegation), 4 Loop Guardian & TODO Enforcer, 6 Multi-Project Parallel Management
- `Guinevere_TechnicalArchitecture_v2.0.md` — 3.2 (agents/ directory), 4.2 Profiles

### 20. Autonomous Loop Safety
**Decision**: Loop Guardian (30s heartbeat), TODO Enforcer, error escalation framework, state machine with PAUSED/BLOCKED/RETRY
- `Guinevere_AgentLoopSpec_v2.0.md` — 4.1 Loop Guardian, 4.2 TODO Enforcer, 4.3 Error Escalation Framework, 5.3 Loop Interruption
- `Guinevere_PRD_v2.0.md` — 8.1 Crash Recovery Protocol
- `Guinevere_TechnicalArchitecture_v2.0.md` — 3.1 guinevere-loops.service, 7.1 (application auth, rate limiting)

### 21. Persona Drift Control
**Decision**: Autonomous drift logging; daily + triggered updates; core identity lock in system prompt; versioned drift entries
- `Guinevere_Persona_Document_v2.0.md` — 5.1 Memory Architecture, 5.3 Autonomy dalam Evolusi, 5.4 Progress Tracking
- `Guinevere_MemorySchema_v2.0.md` — 5.2 Persona Drift Log schema, 8.4 Memory Versioning
- `Guinevere_TechnicalArchitecture_v2.0.md` — 3.2 (persona/drift.py), 4.3 System Prompt Injection Strategy (Persona drift log injection)

### 22. VPN / Network Security
**Decision**: Tailscale mesh only; zero public ports; Tailscale SSH; JWT + API keys internal auth
- `Guinevere_BRD_v2.0.md` — 4.3 (Tailscale VPN, Data in transit)
- `Guinevere_TechnicalArchitecture_v2.0.md` — 2.2 Network Architecture (all Tailscale internal), 7.1 Defense in Depth (Network perimeter, SSH, Application auth)

### 23. Monitoring VPS Decision
**Decision**: Prometheus + Grafana on primary VPS first; dedicated monitoring VPS deferred to post-MVP scaling
- `Guinevere_BRD_v2.0.md` — 3.1.5 (Prometheus + Grafana di primary VPS dulu), 4.1 (Monitoring Deployment row)
- `Guinevere_TechnicalArchitecture_v2.0.md` — 8.1 Metrics Stack (Prometheus/Grafana location: VPS primary), 2.1 (monitoring VPS post-MVP)

### 24. Feature Flags
**Decision**: Feature toggles in config/feature_flags.py; enable/disable features without deploy
- `Guinevere_TechnicalArchitecture_v2.0.md` — 3.2 (config/feature_flags.py)
- `Guinevere_PRD_v2.0.md` — 8.1 Crash Recovery (implicit feature-gated behavior)

### 25. Systemd Service Management
**Decision**: 7 systemd units; auto-restart policies; memory limits; process isolation
- `Guinevere_TechnicalArchitecture_v2.0.md` — 3.1 systemd Services table (7 units with restart policy + memory limit), 2.1 (systemd reference)
- `Guinevere_BRD_v2.0.md` — 4.2 (Process Manager: systemd), 3.1.5 (Auto-restart via systemd)

---

## Cross-Cutting Canonical Decisions (Apply to All ADRs)

These 9 decisions appear in every v2.0 document Canonical Decisions Applied header and must be referenced in every ADR:

| # | Canonical Decision | Source Anchor |
|---|---|---|
| 1 | Primary LLM: GPT-5.5 via 9Router with 1M context window | TechArch 4.1, BRD 3.1.1 |
| 2 | Sub-agent LLM: DeepSeek V4 Flash via 9Router | TechArch 4.1, BRD 3.1.1 |
| 3 | No OpenRouter fallback — 9Router sole routing layer | TechArch 4.1, APIIntegration 2.1 |
| 4 | Memory: PostgreSQL primary + Redis cache; no SQLite | MemorySchema 1.2, BRD 3.1.2 |
| 5 | SDLC: 7 phases (Research, Plan & Delegate, Delegate, Execute, Validate & Audit, Update Documents, Setup Evidence) | AgentLoopSpec 2, BRD 3.1.3 |
| 6 | OpenCode fully replaced by Guinevere MCP native | BRD 3.1.3, TechArch 12.1 |
| 7 | Monitoring: Prometheus + Grafana on primary VPS first | BRD 3.1.5, TechArch 8.1 |
| 8 | Wearable integrations: post-MVP (not active) | BRD 3.1.4, Persona 10.4 |
| 9 | Browser automation: obscura primary + Playwright fallback | BRD 4.2, APIIntegration 8.2 |

---

## Recommended ADR Batch Order

Batch 1 — Foundation (persona safety + core architecture):
- ADR-01: LLM Model Selection (GPT-5.5 + DeepSeek V4 Flash)
- ADR-02: LLM Routing / 9Router (no OpenRouter fallback)
- ADR-03: Memory/Storage Architecture (PostgreSQL + Redis, no SQLite)
- ADR-04: SDLC Loop Phases (7-phase canonical model)
- ADR-05: Persona Safety & Drift Control (persona safety in batch 1 per user directive)

Batch 2 — Infrastructure:
- ADR-06: MCP / OpenCode Replacement
- ADR-07: Observability Stack (Prometheus + Grafana + Loki)
- ADR-08: Wearable Integration (post-MVP decision)
- ADR-09: Browser Automation (obscura + Playwright)
- ADR-10: Surveillance / Consent (24/7 omniscience policy)

Batch 3 — Operations:
- ADR-11: Deployment Strategy (systemd + autonomous CD)
- ADR-12: Secrets Management (SOPS + age)
- ADR-13: Backup / DR (dual backup, forever retention)
- ADR-14: API Integration Registry
- ADR-15: Data Governance & Encryption

Batch 4 — Extended:
- ADR-16: Financial Integration (e-wallet capture)
- ADR-17: Database Schema / ERD (8 schemas, pgvector, TimescaleDB)
- ADR-18: Sub-Agent Orchestration (pasukan Mommy pattern)
- ADR-19: Autonomous Loop Safety (Guardian + TODO Enforcer)
- ADR-20: VPN / Network Security (Tailscale mesh)

Batch 5 — Remaining:
- ADR-21: Monitoring VPS Decision (primary-first, post-MVP scaling)
- ADR-22: Feature Flags
- ADR-23: Systemd Service Management
- ADR-24: Persona Drift Control (standalone from ADR-05)
- ADR-25: Sub-Agent Model Strategy (standalone from ADR-01)

---

## Notes for ADR Generation

1. Indonesian + technical English: Each ADR should use Bahasa Indonesia for rationale and narrative, technical English for model names, service names, and protocol identifiers.
2. MADR format: Use standard MADR template with Context, Decision, Consequences, Status, References.
3. Cross-references: Every ADR must reference at least 2 v2.0 source documents in its References section.
4. Persona safety: ADR-05 (Persona Safety & Drift Control) should be in batch 1 per user directive; it draws from PRD 2 + Persona 1-12 + MemorySchema 5.2 + TechArch 3.2.
5. Unresolved conflicts: The conflict map (2026-05-30-v2-doc-conflict-map.md) identifies mood taxonomy as still needing ADR resolution — ADR-05 should address this.
6. Canonical decisions: Each ADR must explicitly state which of the 9 canonical decisions it implements or depends on.
