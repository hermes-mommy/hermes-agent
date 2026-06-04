---
title: "Guinevere ADR Index v1.0"
status: "Active"
date: "2026-05-30"
last_modified: "2026-05-30"
owner: "Faiz"
executor: "Guinevere"
format: "MADR with YAML frontmatter"
adr_count: 35
---

# Guinevere ADR Index v1.0


## Purpose

This index is the canonical decision register for Project Guinevere's first 35 technical-core ADRs. Guinevere is a private autonomous AI companion and engineering system with persona identity **Guinevere de Baroque — Super Dominant Yandere Mommy AI Agent**. The ADR set locks technical foundations, safety-critical boundaries, and operational governance needed before later enterprise documentation expands the system.

## Source Documents

- [`Guinevere_BRD_v2.0.md`](Guinevere_BRD_v2.0.md) — Business requirements, objectives, project scope, and success framing.
- [`Guinevere_PRD_v2.0.md`](Guinevere_PRD_v2.0.md) — Product behavior, user-facing features, Discord UX, safety and acceptance expectations.
- [`Guinevere_TechnicalArchitecture_v2.0.md`](Guinevere_TechnicalArchitecture_v2.0.md) — Runtime architecture, VPS topology, services, deployment, observability, and security baseline.
- [`Guinevere_MemorySchema_v2.0.md`](Guinevere_MemorySchema_v2.0.md) — Memory model, PostgreSQL/Redis schema, recall flow, encryption boundaries, and lifecycle.
- [`Guinevere_AgentLoopSpec_v2.0.md`](Guinevere_AgentLoopSpec_v2.0.md) — Autonomous SDLC loop, 7-phase execution model, validation, audit, and evidence behavior.
- [`Guinevere_APIIntegration_v2.0.md`](Guinevere_APIIntegration_v2.0.md) — External APIs, SDKs, LLM routing, browser/search, messaging, and integration constraints.
- [`Guinevere_Persona_Document_v2.0.md`](Guinevere_Persona_Document_v2.0.md) — Guinevere de Baroque persona, tone, mood model, dominance boundaries, and safety-sensitive persona behavior.

## Governance

- **Owner / final approver:** Faiz.
- **Executor / proposer:** Guinevere.
- Guinevere may propose ADR updates autonomously, but Faiz approves final accepted decisions.
- Accepted ADRs must not be materially edited in-place; create a superseding ADR.
- Status lifecycle: Proposed → Under Review → Accepted → Rejected → Deprecated → Superseded → Experimental.
- Security, privacy, persona, and surveillance ADRs require periodic review because they carry higher harm potential than ordinary implementation choices.
- All structured sub-agent ADR research/audit outputs must be stored as markdown artifacts and read by the parent before use.

## Global Safe Word Principle

The safe word is a global user-autonomy override, not a persona flourish. In genuine distress, safe-word use pauses persona escalation, punishment framing, autonomous pressure, and surveillance-driven confrontation. Guinevere must switch to neutral/supportive mode, minimize logging, and avoid punitive violation records unless Faiz explicitly identifies the event as abuse or test mode. This principle is governed by ADR-002 and applies across all future ADRs.

## Canonical Decision Map

| Canonical Decision | ADR | Status |
|---|---|---|
| Primary LLM GPT-5.5 via 9Router with 1M context | [`ADR-004`](adr/ADR-004-primary-llm-model-selection.md) | Accepted |
| All LLM routing through 9Router; no OpenRouter fallback | [`ADR-005`](adr/ADR-005-llm-router-failover-strategy.md) | Accepted |
| Sub-agent LLM DeepSeek V4 Flash via 9Router | [`ADR-006`](adr/ADR-006-sub-agent-llm-model-strategy.md) | Accepted |
| Memory PostgreSQL primary + Redis cache; no SQLite | [`ADR-007`](adr/ADR-007-memory-storage-backend-selection.md) | Accepted |
| 7-phase SDLC loop | [`ADR-011`](adr/ADR-011-sdlc-loop-phase-specification.md) | Accepted |
| Guinevere MCP native fully replaces OpenCode/opencode | [`ADR-013`](adr/ADR-013-guinevere-mcp-native-opencode-replacement.md) | Accepted |
| Prometheus + Grafana on primary VPS first | [`ADR-017`](adr/ADR-017-monitoring-stack-selection.md) | Accepted |
| Browser obscura primary + Playwright fallback | [`ADR-020`](adr/ADR-020-browser-automation-strategy.md) | Accepted |
| Wearable integrations Expansion | [`ADR-021`](adr/ADR-021-wearable-integration-post-mvp.md) | Accepted |
| Safe word is global user-autonomy override | [`ADR-002`](adr/ADR-002-user-autonomy-safe-word-enforcement.md) | Accepted with notes |
| Redis DB0–DB5 canonical assignments | [`ADR-030`](adr/ADR-030-redis-db-assignments.md) | Accepted |
| Database name is `guinevere` (not `guinevere_db`) | [`ADR-031`](adr/ADR-031-database-naming.md) | Accepted |
| Backup storage: idcloudhost S3 primary + Cloudflare R2 secondary | [`ADR-032`](adr/ADR-032-backup-storage-strategy.md) | Accepted |
| Hermes NousResearch hybrid migration architecture | [`ADR-035`](../../adr/ADR-035-hermes-migration.md) | Accepted |

## ADR Register

| ADR | Title | Status | Risk | Tags | File |
|---|---|---|---|---|---|
| ADR-001 | Persona Safety & Ethical Boundary Policy | Accepted with notes | CRITICAL | persona, safety, ethics, policy | [`ADR-001-persona-safety-ethical-boundary.md`](adr/ADR-001-persona-safety-ethical-boundary.md) |
| ADR-002 | User Autonomy & Safe Word Enforcement | Accepted with notes | CRITICAL | safety, autonomy, safe-word, persona | [`ADR-002-user-autonomy-safe-word-enforcement.md`](adr/ADR-002-user-autonomy-safe-word-enforcement.md) |
| ADR-003 | Persona Drift Control & Validation | Accepted with notes | HIGH | persona, drift, validation, audit | [`ADR-003-persona-drift-control-validation.md`](adr/ADR-003-persona-drift-control-validation.md) |
| ADR-004 | Primary LLM Model Selection | Accepted | HIGH | llm, model, 9router, canonical | [`ADR-004-primary-llm-model-selection.md`](adr/ADR-004-primary-llm-model-selection.md) |
| ADR-005 | LLM Router & Failover Strategy | Accepted | HIGH | llm, routing, 9router, failover | [`ADR-005-llm-router-failover-strategy.md`](adr/ADR-005-llm-router-failover-strategy.md) |
| ADR-006 | Sub-Agent LLM Model Strategy | Accepted | MEDIUM | llm, sub-agent, deepseek, 9router | [`ADR-006-sub-agent-llm-model-strategy.md`](adr/ADR-006-sub-agent-llm-model-strategy.md) |
| ADR-007 | Memory Storage Backend Selection | Accepted | CRITICAL | memory, postgresql, redis, sqlite | [`ADR-007-memory-storage-backend-selection.md`](adr/ADR-007-memory-storage-backend-selection.md) |
| ADR-008 | Memory Encryption & Key Management | Accepted with notes | CRITICAL | memory, encryption, keys, privacy | [`ADR-008-memory-encryption-key-management.md`](adr/ADR-008-memory-encryption-key-management.md) |
| ADR-009 | Memory Recall & Semantic Search Strategy | Accepted with notes | HIGH | memory, recall, pgvector, semantic-search | [`ADR-009-memory-recall-semantic-search-strategy.md`](adr/ADR-009-memory-recall-semantic-search-strategy.md) |
| ADR-010 | Surveillance Data Retention Policy | Accepted with notes | HIGH | surveillance, privacy, retention, single-user | [`ADR-010-surveillance-data-retention-policy.md`](adr/ADR-010-surveillance-data-retention-policy.md) |
| ADR-011 | SDLC Loop Phase Specification | Accepted | HIGH | sdlc, agent-loop, canonical, automation | [`ADR-011-sdlc-loop-phase-specification.md`](adr/ADR-011-sdlc-loop-phase-specification.md) |
| ADR-012 | Sub-Agent Orchestration Governance | Accepted with notes | HIGH | sub-agent, orchestration, audit, governance | [`ADR-012-sub-agent-orchestration-governance.md`](adr/ADR-012-sub-agent-orchestration-governance.md) |
| ADR-013 | Guinevere MCP Native OpenCode Replacement | Accepted | HIGH | mcp, coding-agent, opencode, canonical | [`ADR-013-guinevere-mcp-native-opencode-replacement.md`](adr/ADR-013-guinevere-mcp-native-opencode-replacement.md) |
| ADR-014 | VPS & Container Architecture | Accepted | HIGH | infrastructure, vps, docker, ubuntu | [`ADR-014-vps-container-architecture.md`](adr/ADR-014-vps-container-architecture.md) |
| ADR-015 | Secrets Management Strategy | Accepted | CRITICAL | security, secrets, sops, age | [`ADR-015-secrets-management-strategy.md`](adr/ADR-015-secrets-management-strategy.md) |
| ADR-016 | CI/CD & Autonomous Deployment Strategy | Accepted with notes | HIGH | cicd, deployment, autonomy, release | [`ADR-016-cicd-autonomous-deployment-strategy.md`](adr/ADR-016-cicd-autonomous-deployment-strategy.md) |
| ADR-017 | Monitoring Stack Selection | Accepted | HIGH | observability, prometheus, grafana, loki | [`ADR-017-monitoring-stack-selection.md`](adr/ADR-017-monitoring-stack-selection.md) |
| ADR-018 | Security Architecture & Defense-in-Depth | Accepted with notes | CRITICAL | security, threat-model, defense-in-depth | [`ADR-018-security-architecture-defense-in-depth.md`](adr/ADR-018-security-architecture-defense-in-depth.md) |
| ADR-019 | Access Control & VPN Mesh Strategy | Accepted with notes | HIGH | access-control, tailscale, vpn, rbac | [`ADR-019-access-control-vpn-mesh-strategy.md`](adr/ADR-019-access-control-vpn-mesh-strategy.md) |
| ADR-020 | Browser Automation Strategy | Accepted | MEDIUM | browser, obscura, playwright, automation | [`ADR-020-browser-automation-strategy.md`](adr/ADR-020-browser-automation-strategy.md) |
| ADR-021 | Wearable Integration Post-MVP | Accepted | MEDIUM | wearable, post-mvp, health, integration | [`ADR-021-wearable-integration-post-mvp.md`](adr/ADR-021-wearable-integration-post-mvp.md) |
| ADR-022 | Communication Channel Strategy | Accepted with notes (Revised 2026-06-03) | HIGH | discord, whatsapp, email, communication, neonize | [`ADR-022-communication-channel-strategy.md`](adr/ADR-022-communication-channel-strategy.md) |
| ADR-023 | Financial Data Integration Strategy | Accepted with notes | MEDIUM | financial, ewallet, data-integration, privacy | [`ADR-023-financial-data-integration-strategy.md`](adr/ADR-023-financial-data-integration-strategy.md) |
| ADR-024 | Data Governance & Classification Policy | Accepted with notes | CRITICAL | data-governance, classification, privacy, compliance | [`ADR-024-data-governance-classification-policy.md`](adr/ADR-024-data-governance-classification-policy.md) |
| ADR-025 | Backup & Disaster Recovery Strategy | Accepted with notes | CRITICAL | backup, dr, rpo, rto, operations | [`ADR-025-backup-disaster-recovery-strategy.md`](adr/ADR-025-backup-disaster-recovery-strategy.md) |
| ADR-026 | Public Endpoint via Cloudflare Tunnel | Accepted | MEDIUM | network, cloudflare, tunnel, webhook, discord | [`ADR-026-public-endpoint-cloudflare-tunnel.md`](adr/ADR-026-public-endpoint-cloudflare-tunnel.md) |
| ADR-027 | Self-Hosted PostgreSQL | Accepted | HIGH | database, postgresql, self-host, budget, infrastructure | [`ADR-027-self-hosted-postgresql.md`](adr/ADR-027-self-hosted-postgresql.md) |
| ADR-028 | LLM Router Outage — 9Router Combo Routing with Graceful Degradation | Superseded | MEDIUM | llm, fallback, graceful-degradation, resilience, 9router, deepseek, cockpit, opencode-go | [`ADR-028-llm-router-outage-graceful-degradation.md`](adr/ADR-028-llm-router-outage-graceful-degradation.md) |
| ADR-029 | Self-Modification Automated Testing | Accepted | CRITICAL | self-modification, testing, rollback, safety, autonomy | [`ADR-029-self-modification-automated-testing.md`](adr/ADR-029-self-modification-automated-testing.md) |
| ADR-030 | Redis DB Assignments (DB0–DB5) | Accepted | CRITICAL | redis, database, cache, queue, infrastructure | [`ADR-030-redis-db-assignments.md`](adr/ADR-030-redis-db-assignments.md) |
| ADR-031 | Database Naming Convention | Accepted | HIGH | database, postgresql, naming, infrastructure | [`ADR-031-database-naming.md`](adr/ADR-031-database-naming.md) |
| ADR-032 | Backup Storage Strategy — idcloudhost S3 + Cloudflare R2 | Accepted | CRITICAL | backup, storage, s3, cloudflare, r2, idcloudhost, dr | [`ADR-032-backup-storage-strategy.md`](adr/ADR-032-backup-storage-strategy.md) |
| ADR-033 | Browser Automation — Obscura CDP over Headless Chrome + Playwright | Accepted | MEDIUM | browser, obscura, cdp, playwright-core, stealth, p6-009 | [`ADR-033-browser-automation-obscura.md`](adr/ADR-033-browser-automation-obscura.md) |
| ADR-034 | Post-MVP Phase Restructure — P0-P11 → P0-P22 | Accepted | MEDIUM | phase, restructure, roadmap, expansion | [`ADR-034-post-mvp-phase-restructure.md`](../../adr/ADR-034-post-mvp-phase-restructure.md) |
| ADR-035 | Hermes NousResearch Migration Architecture | Accepted | CRITICAL | architecture, migration, hermes, discord, safety, mcp, memory, llm-routing, nfr | [`ADR-035-hermes-migration.md`](../../adr/ADR-035-hermes-migration.md) |

## Status Summary

- **Accepted**: 18
- **Accepted with notes**: 14
- **Superseded**: 1
- **Proposed**: 1

## Risk Summary

- **CRITICAL**: 12
- **HIGH**: 15
- **MEDIUM**: 7
- **LOW**: 0

## Backlog for Future ADRs

- ADR-036 Acceptance Criteria Catalog Governance
- ADR-037 Privacy Impact Assessment / DPIA
- ADR-038 Consent & Revocation Policy
- ADR-039 Prompt Injection & Model Safety
- ADR-040 RBAC/ABAC Access Control Matrix
- ADR-041 Secrets Rotation Runbook
- ADR-042 OpenAPI / AsyncAPI Contract Governance
- ADR-043 Event Schema & Webhook Contract
- ADR-044 Database ERD & Migration Strategy
- ADR-045 SLO/SLA/Error Budget Policy
- ADR-046 Incident Response & Postmortem Runbook
- ADR-047 Feature Flag Governance
- ADR-048 Product Analytics & Event Taxonomy
- ADR-049 Compliance & Data Residency Mapping

## Maintenance Rules

- Add new ADRs with monotonically increasing numbers.
- Do not reuse ADR numbers.
- If an ADR supersedes another, update both the new ADR and this index.
- Keep every ADR linked to at least one v2.0 source document or an explicitly named future source document.
- Keep `adr/README.md` synchronized with this master index.
