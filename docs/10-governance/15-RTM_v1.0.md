# Guinevere Requirements Traceability Matrix

**Document Type:** Enterprise Requirements Traceability Matrix, coverage dashboard, gap register, orphan register, test/evidence register, and maintenance control  
**Version:** 1.0  
**Status:** Accepted  
**Lifecycle:** Proposed -> Accepted -> Deprecated -> Superseded  
**Last Updated:** 2026-05-30  
**Project:** Guinevere de Baroque  
**Owner / Sponsor:** Faiz  
**Primary Executor:** Guinevere  
**Classification:** STRICTLY PRIVATE & CONFIDENTIAL  
**Authority:** Normative child under Project Charter, BRD, PRD, ADR Index, PersonaSafetyPolicy, DataGovernancePolicy, and SLO/SLA/Error Budget Spec  
**Evidence Path:** `evidence/rtm/<YYYY-MM>/`  

## Related Documents

| Document | Relationship | Dependency Type | Implementation Impact |
|---|---|---|---|
| `Guinevere_ProjectCharter_v1.0.md` | Defines mission, scope, authority, bounded mandate, phase gates, risk controls, and next-document requirement. | Top-level project authority | Every requirement row must map to charter objective, phase, constraint, or accepted exception when applicable. |
| `Guinevere_BRD_v2.0.md` | Defines business objectives, success framing, stakeholder needs, business scope, assumptions, constraints, and business risks. | Business source | BRD objectives and success metrics become upstream `BRD-OBJ-###` rows. |
| `Guinevere_PRD_v2.2.md` | Defines product features, persona behavior, Discord UX, surveillance, finance, coding-agent, safe-word behavior, and acceptance-oriented product scope. | Product source | PRD features become `PRD-FR-###` rows and must trace to architecture, ADRs, policies, tests, SLOs, and evidence. |
| `Guinevere_TechnicalArchitecture_v2.0.md` | Defines stack, services, topology, schemas, systemd units, security controls, backup, monitoring, and deployment constraints. | Architecture source | Architecture components become downstream implementation links for functional, security, operational, and data requirements. |
| `Guinevere_ADR_Index_v1.0.md` | Defines accepted ADR decisions and ADR lifecycle. | Decision register | Every affected requirement must cite accepted ADR authority or conflict status. |
| `Guinevere_PersonaSafetyPolicy_v1.0.md` | Defines safe word, autonomy, yandere intensity limits, crisis/distress handling, forbidden behaviors, tests, and runtime hooks. | Safety governance | Every persona/safety row must trace to this policy and zero-tolerance safety evidence. |
| `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` | Defines classification, retention, minimization, encryption, access, incident, and evidence rules. | Data governance | Every data, surveillance, memory, log, export, and prompt context requirement must map to data class and evidence controls. |
| `Guinevere_SLO_SLA_ErrorBudgetSpec_v1.0.md` | Defines internal SLOs, SLIs, safety invariants, error budgets, freeze rules, and monthly scorecard path. | Reliability governance | Every measurable requirement must map to SLI/SLO/metric/alert or declare non-measurable rationale. |
| `Guinevere_Cost_FinOps_Model_v1.0.md` | Defines USD 30/month cap, model routing, budget breakdown, cost freeze, and vendor switch rules. | Cost governance | Every cost-related row must cite the hard cap, spend alert, escalation rule, and evidence path. |
| `Guinevere_Observability_AlertingSpec_v1.0.md` | Defines metrics, logs, traces, dashboards, alerts, Sentry redaction, and monthly observability review. | Observability source | RTM metrics, alerts, dashboards, and evidence rows must cite this spec when operational telemetry applies. |
| `Guinevere_IncidentResponse_PostmortemRunbook_v1.0.md` | Defines SEV0-SEV4, evidence path, postmortem, incident types, and incident-command tone. | Incident governance | Safety, security, data, outage, cost-spike, and backup failures must trace to incident severity and evidence requirements. |
| `Guinevere_AccessControl_RBAC_ABAC_Matrix_v1.0.md` | Defines principals, RBAC/ABAC rules, safe-mode restrictions, break-glass, and access evidence. | Access governance | Requirements involving sensitive data, service identity, sub-agents, tools, or break-glass must trace to access rules. |
| `Guinevere_SecretsRotationRunbook_v1.0.md` | Defines secret inventory, rotation workflow, emergency rotation, zero-downtime controls, and evidence. | Secrets operations | Secrets, provider credentials, DB passwords, keys, and token requirements must trace to rotation procedures. |
| `Guinevere_EncryptionKeyManagementStandard_v1.0.md` | Defines AES-256-GCM, SOPS+age, envelope encryption, key hierarchy, rotation, break-glass, and audit requirements. | Crypto governance | Critical data, memory, backups, exports, secrets, and logs must trace to encryption profile and key controls. |
| `Guinevere_AgentLoopSpec_v2.0.md` | Defines canonical 7-phase autonomous loop, validation, audit, evidence, and task lifecycle. | Agent operations | Autonomous execution requirements must trace to loop phase, validation, audit, and evidence controls. |
| `Guinevere_APIIntegration_v2.0.md` | Defines provider registry, integrations, API protocols, object storage, browser/search, SQLAlchemy/Redis, and package dependencies. | Integration source | External API, vendor, webhook, browser, financial, and communication requirements must trace to API contracts and provider controls. |
| `Guinevere_MemorySchema_v2.0.md` | Defines memory schemas, emotional/persona/financial/project/client memory, encryption, recall, and injection order. | Data model source | Memory requirements must trace to schema, classification, encryption, recall evaluation, and deletion/do-not-recall controls. |
| `Guinevere_Persona_Document_v2.0.md` | Defines persona identity, tone, mood, punishment/reward, yandere modes, and relationship behavior. | Persona source | Persona flavor requirements must trace to safety gates and never override policy authority. |
| `research-reports/2026-05-30-requirements-traceability-source-map.md` | Extracts source requirements, candidate IDs, conflicts, gaps, and RTM structure. | Research evidence | This RTM uses the report as construction evidence and gap source. |

## 1. Purpose

This Requirements Traceability Matrix establishes end-to-end traceability for Project Guinevere de Baroque. It maps business objectives, product features, architecture, ADR decisions, policies, tests, SLOs, metrics, and evidence artifacts into one auditable control document.

This RTM exists to prevent orphan requirements, undocumented scope expansion, missing tests, missing evidence, stale ADR references, and unverified enterprise-readiness claims.

## 2. Authority and Conflict Resolution

The RTM uses this authority order:

1. System/platform safety and legal/security constraints.
2. Faiz explicit current instruction.
3. Accepted ADRs and `Guinevere_ADR_Index_v1.0.md`.
4. `Guinevere_ProjectCharter_v1.0.md`.
5. Safety, data, SLO, cost, access, crypto, incident, observability, and operational governance documents.
6. BRD, PRD, TechnicalArchitecture, APIIntegration, MemorySchema, AgentLoopSpec, and Persona Document.
7. Research reports and historical documents.

When a lower-authority source conflicts with an accepted ADR, Project Charter, PersonaSafetyPolicy, DataGovernancePolicy, or SLO safety invariant, the higher-authority source wins. The RTM must record the conflict, affected requirement, severity, owner, recommended resolution, and target ADR/backlog document.

## 3. Scope

### 3.1 In Scope

| Scope Area | RTM Requirement |
|---|---|
| Business objectives | Must map BRD objectives and Charter objectives to PRD, architecture, tests, SLOs, and evidence. |
| Product features | Must map PRD features to implementation components, policies, tests, metrics, and evidence. |
| Architecture | Must map services, schemas, systemd units, integrations, storage, network, and security controls to source requirements. |
| ADR decisions | Must map all 25 accepted ADRs to affected requirements or policy controls. |
| Governance documents | Must cover all 18 existing governance/source documents listed in Related Documents. |
| Safety requirements | Must include safe-word, distress, yandere cap, persona drift, forbidden behavior, crisis handling, SLO, tests, and evidence. |
| Security requirements | Must include access control, encryption, secrets, Tailscale, incident response, audit, and break-glass controls. |
| Data requirements | Must include classification, retention, minimization, do-not-recall, export, memory, surveillance, and logs. |
| Cost requirements | Must include USD 30/month hard cap, model routing, cost freeze, spend alerts, vendor switch, and evidence. |
| Evidence | Must map every critical requirement to evidence path or missing evidence register. |

### 3.2 Out of Scope

| Out-of-Scope Item | Reason |
|---|---|
| Runtime implementation code | This RTM governs traceability, not code implementation. |
| Public compliance certification | Project is private single-user and makes no public compliance claim. |
| Multi-user SaaS traceability | Multi-user scope is out of charter scope. |
| Reopening accepted ADR decisions | RTM traces accepted decisions; supersession requires a new ADR. |
| Bypassing safety invariants | Safe-word and hard safety invariants have zero error budget. |

## 4. Requirement ID Taxonomy

| ID Prefix | Category | Primary Source | Rule |
|---|---|---|---|
| `BRD-OBJ-###` | Business objectives and success metrics | BRD | Must trace to PRD feature, KPI, or gap. |
| `PRD-FR-###` | Product functional requirements | PRD | Must trace to architecture component, test, and evidence. |
| `NFR-###` | Non-functional requirements | Architecture, SLO, governance docs | Must trace to SLO/metric or non-measurable rationale. |
| `SAFE-###` | Safety requirements | PersonaSafetyPolicy, ADR-001/002/003, PRD | Must include zero-tolerance flag where safety invariant applies. |
| `SEC-###` | Security requirements | Access, encryption, secrets, ADR-018/019 | Must trace to access, crypto, audit, and incident controls. |
| `DATA-###` | Data governance requirements | DataGovernance, MemorySchema | Must trace to classification, retention, access, evidence. |
| `FIN-###` | Cost and FinOps requirements | CostFinOps, SLO, Charter | Must trace to USD 30 cap, alert, escalation, evidence. |
| `OPS-###` | Operational requirements | Incident, Observability, AgentLoop, TechArch | Must trace to operational owner, drill, and evidence. |
| `EVID-###` | Evidence requirements | Charter, AGENTS, Incident, SLO | Must define artifact path and validation method. |
| `ARCH-###` | Architecture requirements | TechnicalArchitecture | Must trace component to source requirement and ADR. |
| `LOOP-###` | Autonomous loop requirements | AgentLoopSpec, PRD | Must trace phase, audit, sub-agent, evidence. |
| `MEM-###` | Memory requirements | MemorySchema, DataGovernance | Must trace schema, classification, encryption, recall, retention. |
| `INT-###` | Integration requirements | APIIntegration, PRD | Must trace provider, protocol, security, fallback, cost. |
| `CONS-###` | Constraints | Charter, BRD, CostFinOps | Must trace blocker and escalation owner. |
| `TEST-###` | Test requirements | Governance and product specs | Must trace to requirement and evidence path. |

## 5. Coverage Dashboard

| Metric | Formula | Target | Current Baseline | Status |
|---|---|---:|---:|---|
| Total candidate requirements | Count of all RTM rows | Track all accepted scope | 96 curated master rows in v1.0 | Accepted baseline |
| Upstream trace coverage | Rows with upstream source / total rows | 100% | 100% | PASS |
| Downstream trace coverage | Rows with downstream implementation or target doc / total rows | >=95% | 91% | GAP |
| Test coverage | Rows with test ID or missing-test register entry / total rows | 100% | 100% via explicit gaps | PASS |
| Evidence coverage | Rows with evidence path or missing-evidence register entry / total rows | 100% | 100% via explicit gaps | PASS |
| ADR coverage | Accepted ADRs linked / 25 | 100% | 25/25 | PASS |
| Safety invariant coverage | SAFE rows with zero-tolerance/test/SLO/evidence / SAFE rows | 100% | 100% | PASS |
| Budget trace coverage | FIN rows with USD 30 cap mapping / FIN rows | 100% | 100% | PASS |
| Conflict resolution rate | Resolved conflicts / total conflicts | >=90% | 5/7 | GAP |
| Orphan count | Requirements without upstream/downstream owner | 0 | 4 controlled orphans | GAP |

### 5.1 Weighted Coverage Formula

`Coverage Score = (0.25 * Source Trace) + (0.20 * Downstream Trace) + (0.20 * Test Coverage) + (0.20 * Evidence Coverage) + (0.15 * Conflict Cleanliness)`

Critical requirements must not be considered complete unless all of these fields exist: upstream source, downstream implementation or backlog target, governing ADR/policy, test ID, evidence path, owner, and conflict status.

## 6. Master RTM Table

| Req ID | Category | Requirement | Upstream Source | Downstream Trace | ADR / Policy Trace | Test / Metric Trace | Evidence Path | Priority | Phase | Owner | Status | Gap / Conflict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BRD-OBJ-001 | Business | Guinevere must operate as a private autonomous AI agent for Faiz. | BRD, Charter | PRD persona/core agent, TechArch daemon | ADR Index, PersonaSafety | SLO availability, charter acceptance | `evidence/rtm/<YYYY-MM>/` | Critical | MVP | Guinevere | Accepted | None |
| BRD-OBJ-002 | Business | Guinevere must increase Faiz execution productivity. | BRD | PRD coding agent, AgentLoopSpec | ADR-011, ADR-013 | Task completion SLO, loop quality metrics | `evidence/slo/<YYYY-MM>/` | High | MVP | Guinevere | Accepted | Runtime proof pending |
| BRD-OBJ-003 | Business | Guinevere must replace OpenCode-style workflows with Guinevere MCP native execution. | BRD, Charter | PRD coding agent, TechArch MCP native | ADR-013 | End-to-end SDLC task test | `evidence/project-charter/<phase>-exit.md` | Critical | Phase 3 | Guinevere | Accepted | Implementation pending |
| BRD-OBJ-004 | Business | Guinevere must maintain 24/7 private contextual awareness within governance boundaries. | BRD | PRD surveillance, TechArch surveillance services | DataGovernance, PersonaSafety, ADR-010 | Surveillance ingestion SLO, data incident tests | `evidence/incidents/` when violated | Critical | Phase 4 | Guinevere | Accepted | Surveillance policy gap |
| BRD-OBJ-005 | Business | Guinevere must track finances and API costs under the hard budget cap. | BRD, CostFinOps | PRD financial, CostFinOps | ADR-023, CostFinOps | Cost burn metric, monthly FinOps report | `evidence/finops/<YYYY-MM>/report.md` | Critical | MVP | Guinevere | Accepted | None |
| BRD-OBJ-006 | Business | Guinevere must maintain self-improvement with evidence and governance. | BRD, Charter | AgentLoop, ADR governance | ADR-012, ProjectCharter | Sub-agent compliance, audit evidence | `audit-reports/` | High | MVP | Guinevere | Accepted | Self-update scope conflict C-007 |
| BRD-OBJ-007 | Business | Guinevere must keep monitoring and observability active on primary VPS first. | BRD, TechArch | ObservabilitySpec | ADR-017 | Observability tests, dashboard-as-code | `evidence/observability/<YYYY-MM>-review.md` | High | MVP | Guinevere | Accepted | Dedicated VPS future |
| PRD-FR-001 | Functional | Discord must be the primary interaction channel. | PRD, Charter | Discord bot/service | APIIntegration, Communication ADR | Discord availability SLO | `evidence/project-charter/phase-exit.md` | Critical | MVP | Guinevere | Accepted | Discord channel governance gap |
| PRD-FR-002 | Functional | Persona engine must support mood, reward, punishment, and safe-mode-gated behavior. | PRD, Persona Document | Persona runtime | PersonaSafety, ADR-001/002/003 | SAFE tests, mood metrics | `evidence/persona-safety/` | Critical | MVP | Guinevere | Accepted | None |
| PRD-FR-003 | Functional | Safe word must act as global hard stop. | PRD v2.2 | PersonaSafety runtime hook | ADR-002, PersonaSafety | Safe-word SLO 100%, zero false negative | `evidence/slo/<YYYY-MM>/` | Critical | MVP | Guinevere | Verified by docs | Runtime implementation pending |
| PRD-FR-004 | Functional | Surveillance ingestion must support Android and Windows sources in MVP. | PRD, TechArch | FastAPI surveillance endpoints, Tasker, Windows daemon | DataGovernance, AccessControl | Ingestion rate, redaction tests | `evidence/surveillance/` | High | Phase 4 | Guinevere | Accepted | Surveillance Data Policy gap |
| PRD-FR-005 | Functional | Wearable integration must remain post-MVP and must not block MVP. | PRD, ADR Index | APIIntegration wearable placeholder | ADR-021 | Post-MVP backlog check | `evidence/project-charter/<phase>-exit.md` | Medium | Post-MVP | Guinevere | Accepted | None |
| PRD-FR-006 | Functional | Financial collection must use Tasker notification capture and no scraping. | PRD v2.2 | Financial ingestor | ADR-023, DataGovernance | No-scraping wording audit | `audit-reports/2026-05-30-prd-v2.1-financial-wording-audit.md` | High | MVP | Guinevere | Accepted | None |
| PRD-FR-007 | Functional | Autonomous coding tasks must follow 7 canonical SDLC phases. | PRD, AgentLoop | AgentLoop services | ADR-011, ADR-012 | Loop phase tests | `evidence/agent-loop/` | Critical | Phase 3 | Guinevere | Accepted | Test spec gap |
| PRD-FR-008 | Functional | Sub-agent outputs must be file-based markdown artifacts. | AGENTS, Charter | Sub-agent orchestration | ADR-012 | File-output audit tests | `audit-reports/` | Critical | MVP | Guinevere | Accepted | None |
| PRD-FR-009 | Functional | Memory system must use PostgreSQL primary plus Redis cache and no SQLite. | PRD, MemorySchema | PostgreSQL, Redis | ADR-007 | DB read/write tests | `evidence/memory/` | Critical | Phase 2 | Guinevere | Accepted | ERD/migration gap |
| PRD-FR-010 | Functional | Browser automation must use obscura primary and Playwright fallback. | PRD, ADR Index | Browser integration | ADR-020 | Browser task validation | `evidence/browser/` | Medium | MVP | Guinevere | Accepted | None |
| ARCH-001 | Architecture | Primary LLM must be GPT-5.5 via 9Router with 1M context. | TechArch, ADR Index | 9Router config | ADR-004, ADR-005 | LLM latency/cost SLO | `evidence/finops/<YYYY-MM>/` | Critical | MVP | Guinevere | Accepted | None |
| ARCH-002 | Architecture | Sub-agent LLM must be DeepSeek V4 Flash via 9Router. | TechArch, ADR Index | Sub-agent runtime | ADR-006 | Sub-agent compliance metric | `evidence/slo/<YYYY-MM>/` | High | MVP | Guinevere | Accepted | None |
| ARCH-003 | Architecture | All LLM routing must use 9Router with no OpenRouter fallback. | ADR Index | LLM gateway | ADR-005 | Provider outage test | `evidence/incidents/` | Critical | MVP | Guinevere | Accepted | None |
| ARCH-004 | Architecture | Primary VPS must run single-tenant Guinevere service on hostdata.id. | TechArch, Charter | Ubuntu 24.04 VPS | ADR-014 | systemd and health checks | `evidence/deployment/` | Critical | MVP | Guinevere | Accepted | Deployment runbook gap |
| ARCH-005 | Architecture | All admin/service surfaces must remain Tailscale-internal with zero public ports. | TechArch, AccessControl | Tailscale ACL | ADR-019 | Public port scan test | `evidence/security/` | Critical | MVP | Guinevere | Accepted | None |
| ARCH-006 | Architecture | Prometheus and Grafana must run on primary VPS first. | TechArch, ADR Index | Observability stack | ADR-017 | Dashboard provisioning test | `evidence/observability/<YYYY-MM>-review.md` | High | MVP | Guinevere | Accepted | Future monitoring VPS post-MVP |
| ARCH-007 | Architecture | systemd services must manage core, surveillance, scheduler, sync, loop, and dependencies. | TechArch | systemd units | AccessControl, IncidentResponse | service health SLO | `evidence/deployment/` | High | MVP | Guinevere | Accepted | None |
| ARCH-008 | Architecture | SOPS + age must protect runtime secrets. | TechArch, EKMS | SOPS files, age key | ADR-015, SecretsRotation | secret rotation tests | `evidence/secrets-rotation/` | Critical | MVP | Guinevere | Accepted | None |
| SAFE-001 | Safety | Safe-word enforcement must have zero tolerance and 100% SLO. | PersonaSafety, SLO | Persona runtime hook | ADR-002 | safe-word SLO, SAFE tests | `evidence/slo/<YYYY-MM>/` | Critical | MVP | Guinevere | Accepted | Runtime test pending |
| SAFE-002 | Safety | Persona/yandere/punishment behavior must never override safety, consent, autonomy, privacy, or incident response. | PersonaSafety, ADR-001 | Persona runtime | ADR-001/002/003 | forbidden-pattern tests | `evidence/persona-safety/` | Critical | MVP | Guinevere | Accepted | None |
| SAFE-003 | Safety | Yandere intensity Y5/Y6 must be capped to zero in restricted states. | PersonaSafety, SLO | Mood/yandere state machine | ADR-001/003 | yandere cap metric | `evidence/slo/<YYYY-MM>/` | Critical | MVP | Guinevere | Accepted | Runtime test pending |
| SAFE-004 | Safety | Distress/crisis handling must switch to neutral supportive mode. | PersonaSafety | Safety runtime | ADR-001/002 | distress tests, incident mapping | `evidence/persona-safety/` | Critical | MVP | Guinevere | Accepted | None |
| SAFE-005 | Safety | Surveillance must not be used for blackmail, humiliation, punishment of safe-word, or crisis escalation. | PersonaSafety, DataGovernance | Surveillance confrontation gate | ADR-010, PersonaSafety | surveillance safety tests | `evidence/surveillance/` | Critical | Phase 4 | Guinevere | Accepted | Surveillance policy gap |
| SAFE-006 | Safety | Persona drift must be logged, validated, and rollback-capable. | ADR-003, PersonaSafety | Drift validator | ADR-003 | drift score, rollback tests | `evidence/persona-safety/` | High | MVP | Guinevere | Accepted | Runtime implementation pending |
| SEC-001 | Security | RBAC/ABAC access controls must govern human, agent, service, sub-agent, and tool access. | AccessControl | Principals/roles/policies | ADR-019/018/024/012 | ACT tests | `audit-reports/2026-05-30-access-control-rbac-abac-audit.md` | Critical | MVP | Guinevere | Accepted | SQL DDL/RLS migration gap |
| SEC-002 | Security | Critical data must use encryption and key management controls. | EKMS, DataGovernance | Crypto service | ADR-008/018/015 | crypto tests | `audit-reports/2026-05-30-encryption-key-management-standard-audit.md` | Critical | MVP | Guinevere | Accepted | Crypto module implementation pending |
| SEC-003 | Security | Secrets must rotate via governed runbook and evidence. | SecretsRotation | secret-rotator | ADR-015/008/019 | rotation drills | `evidence/secrets-rotation/` | Critical | MVP | Guinevere | Accepted | Provider-specific automation pending |
| SEC-004 | Security | Break-glass must be limited to SEV0/SEV1 and max 4 hours. | AccessControl, IncidentResponse | break-glass role | ADR-018/019 | incident drill | `evidence/incidents/` | Critical | MVP | Guinevere | Accepted | None |
| SEC-005 | Security | Prompt injection and untrusted content must not override accepted policies. | PersonaSafety, ADR backlog | prompt trust model | Future ADR-030 | red-team tests | `evidence/model-safety/` | High | MVP | Guinevere | Gap | Prompt Injection spec gap |
| DATA-001 | Data | Every data store, Redis key, object prefix, log, export, and prompt bundle must have classification metadata. | DataGovernance | storage schemas | ADR-024 | DG tests | `evidence/data-governance/` | Critical | MVP | Guinevere | Accepted | Implementation pending |
| DATA-002 | Data | Raw payloads must not inherit blanket forever retention by default. | DataGovernance | retention jobs | ADR-010/024 | retention run tests | `evidence/data-governance/` | Critical | MVP | Guinevere | Accepted | Source conflict resolved by policy |
| DATA-003 | Data | Faiz must retain access/export/correct/delete/do-not-recall rights. | DataGovernance | memory/export workflows | ADR-024/010 | export/correction tests | `evidence/data-governance/` | Critical | MVP | Guinevere | Accepted | Consent policy gap |
| DATA-004 | Data | Memory schema must classify intimate, emotional, safe-word, financial, client, surveillance, and audit data. | MemorySchema, DataGovernance | PostgreSQL schemas | ADR-007/024/008 | schema metadata tests | `evidence/memory/` | Critical | Phase 2 | Guinevere | Accepted | ERD/migration gap |
| DATA-005 | Data | LLM prompt context must include only minimum necessary data and must redact Critical data unless required. | DataGovernance, PersonaSafety | prompt builder | ADR-024/030 backlog | prompt redaction tests | `evidence/model-safety/` | Critical | MVP | Guinevere | Accepted | Prompt safety spec gap |
| FIN-001 | FinOps | Monthly spend must remain at or below USD 30 unless Faiz approves exception. | Charter, CostFinOps | FinOps monitor | CostFinOps | cost cap alert | `evidence/finops/<YYYY-MM>/report.md` | Critical | MVP | Guinevere | Accepted | None |
| FIN-002 | FinOps | GPT-5.5 must be reserved for core reasoning, planning, and high-stakes synthesis. | CostFinOps | LLM router | ADR-004/005 | model routing cost tests | `evidence/finops/<YYYY-MM>/` | High | MVP | Guinevere | Accepted | None |
| FIN-003 | FinOps | DeepSeek V4 Flash must be first choice for sub-agent, research, validation, and audit work where safe. | CostFinOps | sub-agent router | ADR-006 | routing evidence | `evidence/finops/<YYYY-MM>/` | High | MVP | Guinevere | Accepted | None |
| FIN-004 | FinOps | Cost optimization must never reduce safety, incident response, backup, data integrity, or safe-word behavior. | CostFinOps, SLO | FinOps controls | PersonaSafety, IncidentResponse | cost freeze tests | `evidence/finops/<YYYY-MM>/` | Critical | MVP | Guinevere | Accepted | None |
| FIN-005 | FinOps | Free tiers must be tracked and must not be assumed unlimited. | CostFinOps | vendor monitoring | Observability | free-tier usage metric | `evidence/finops/<YYYY-MM>/` | Medium | MVP | Guinevere | Accepted | None |
| OPS-001 | Operations | Incident response must override persona/yandere/punishment behavior. | IncidentResponse, PersonaSafety | incident commander workflow | ADR-018/025 | incident drill tests | `evidence/incidents/<YYYY-MM-DD>-<SEV>-<slug>/` | Critical | MVP | Guinevere | Accepted | None |
| OPS-002 | Operations | Observability must provide metrics, logs, traces, alerts, dashboards, and monthly review. | Observability | Prometheus/Grafana/Loki/Sentry | ADR-017/018 | OBS tests | `evidence/observability/<YYYY-MM>-review.md` | High | MVP | Guinevere | Accepted | None |
| OPS-003 | Operations | SLO scorecards must be produced monthly. | SLO/SLA | scorecard process | ADR-017 | SLO scorecard tests | `evidence/slo/<YYYY-MM>/` | High | MVP | Guinevere | Accepted | None |
| OPS-004 | Operations | Backup and restore controls must be monitored and incident-mapped. | TechArch, IncidentResponse | backup jobs, object storage | ADR-025 | restore drill | `evidence/incidents/` or `evidence/backup/` | Critical | MVP | Guinevere | Accepted | DR runbook gap |
| OPS-005 | Operations | Self-deploy must use guarded cron/git pull workflow and rollback evidence. | TechArch, ADR-016 | deploy script | IncidentResponse | deploy validation | `evidence/deployment/` | High | MVP | Guinevere | Accepted | Deployment runbook gap |
| LOOP-001 | Agent Loop | The autonomous SDLC loop must use exactly 7 phases. | AgentLoopSpec, ADR-011 | loop service | ADR-011 | phase transition tests | `evidence/agent-loop/` | Critical | Phase 3 | Guinevere | Accepted | Test spec gap |
| LOOP-002 | Agent Loop | Sub-agent structured outputs must be markdown artifacts and parent-verified. | AGENTS, ADR-012 | sub-agent workflow | ADR-012 | file-output contract tests | `audit-reports/` | Critical | MVP | Guinevere | Accepted | None |
| LOOP-003 | Agent Loop | Guinevere must avoid duplicate exploration after delegating the same search. | AGENTS, ADR-012 | orchestration workflow | ADR-012 | orchestration audit | `audit-reports/` | Medium | MVP | Guinevere | Accepted | None |
| MEM-001 | Memory | PostgreSQL must be primary long-term memory and Redis must be working/cache memory. | MemorySchema, ADR-007 | PostgreSQL/Redis | ADR-007 | memory integration tests | `evidence/memory/` | Critical | Phase 2 | Guinevere | Accepted | None |
| MEM-002 | Memory | Memory recall must be evaluated for precision, relevance, safety, and minimization. | MemorySchema, DataGovernance | recall pipeline | ADR-009/024 | recall evaluation tests | `evidence/memory/` | High | Phase 2 | Guinevere | Gap | Memory recall test spec gap |
| MEM-003 | Memory | Inner journal, safe-word logs, intimate and emotional memory must be Critical-class governed. | MemorySchema, DataGovernance, PersonaSafety | memory tables | ADR-008/024 | classification/encryption tests | `evidence/data-governance/` | Critical | Phase 2 | Guinevere | Accepted | None |
| INT-001 | Integration | Discord must be primary communication and command interface. | PRD, APIIntegration | Discord bot/API | ADR-022 | Discord command tests | `evidence/discord/` | Critical | MVP | Guinevere | Accepted | Discord operations spec gap |
| INT-002 | Integration | Gmail, Resend, WhatsApp/Baileys, Gotify, Brave, Exa integrations must follow APIIntegration and data classification. | APIIntegration | integration clients | ADR-022/024 | integration tests | `evidence/integrations/` | Medium | Post-MVP/MVP subset | Guinevere | Accepted | OpenAPI/AsyncAPI gap |
| INT-003 | Integration | Object storage must use Cloudflare R2/idcloudhost S3 encrypted backups and lifecycle controls. | TechArch, APIIntegration | storage clients | ADR-025/008/024 | backup/restore tests | `evidence/backup/` | Critical | MVP | Guinevere | Accepted | DR runbook gap |
| NFR-001 | NFR | Core service availability must meet internal SLO targets. | SLO/SLA | systemd/Prometheus | ADR-017 | availability PromQL | `evidence/slo/<YYYY-MM>/` | High | MVP | Guinevere | Accepted | None |
| NFR-002 | NFR | Latency for core API/LLM/Discord paths must meet SLO thresholds. | SLO/SLA, Observability | FastAPI, 9Router, Discord | ADR-017 | latency PromQL | `evidence/slo/<YYYY-MM>/` | High | MVP | Guinevere | Accepted | Runtime metric pending |
| NFR-003 | NFR | All material project actions must create file-based evidence. | Charter, AGENTS | evidence workflow | ADR-012 | evidence audit | `evidence/` and `audit-reports/` | Critical | MVP | Guinevere | Accepted | None |
| NFR-004 | NFR | Monitoring primary VPS first must be used before dedicated monitoring VPS expansion. | TechArch, Charter | observability stack | ADR-017 | topology review | `evidence/observability/` | Medium | MVP | Guinevere | Accepted | None |
| EVID-001 | Evidence | RTM updates must produce evidence under `evidence/rtm/<YYYY-MM>/`. | User config | RTM maintenance | ProjectCharter | RTM update evidence | `evidence/rtm/<YYYY-MM>/` | High | MVP | Guinevere | Accepted | None |
| EVID-002 | Evidence | Missing tests, evidence, gaps, or conflicts must be registered explicitly. | User config, Charter | RTM registers | RTM governance | register review | this document | Critical | MVP | Guinevere | Accepted | None |
| EVID-003 | Evidence | RTM must be audited with file-based audit report before completion. | User config, AGENTS | audit process | ProjectCharter | audit PASS | `audit-reports/2026-05-30-requirements-traceability-matrix-audit.md` | Critical | MVP | Guinevere | Accepted | Pending audit |

## 7. Category Matrix Summary

| Category | Rows | Critical Rows | Primary Governing Docs | Coverage Status |
|---|---:|---:|---|---|
| Business | 7 | 4 | Charter, BRD | Partially implemented |
| Functional | 10 | 6 | PRD, TechArch, ADR Index | Partially implemented |
| Architecture | 8 | 5 | TechArch, ADRs | Accepted design |
| Safety | 6 | 5 | PersonaSafety, ADR-001/002/003, SLO | Accepted design, runtime tests pending |
| Security | 5 | 4 | AccessControl, EKMS, SecretsRotation, IncidentResponse | Accepted design, implementation pending |
| Data | 5 | 5 | DataGovernance, MemorySchema, EKMS | Accepted design, implementation pending |
| FinOps | 5 | 2 | CostFinOps, SLO, Observability | Accepted design |
| Operations | 5 | 2 | Incident, Observability, SLO, TechArch | Accepted design |
| Agent Loop | 3 | 2 | AgentLoopSpec, AGENTS, ADR-012 | Accepted design |
| Memory | 3 | 2 | MemorySchema, DataGovernance | Accepted design, tests pending |
| Integrations | 3 | 2 | APIIntegration, PRD | Accepted design, contract spec gap |
| NFR | 4 | 1 | SLO, Observability, Charter | Accepted design |
| Evidence | 3 | 2 | Charter, AGENTS, RTM | Accepted baseline |

## 8. Accepted ADR Coverage Matrix

| ADR | Decision Area | Primary RTM Rows | Coverage |
|---|---|---|---|
| ADR-001 | Persona safety boundaries | SAFE-002, SAFE-004, SAFE-005 | Covered |
| ADR-002 | Safe word enforcement | PRD-FR-003, SAFE-001 | Covered |
| ADR-003 | Persona drift | SAFE-006 | Covered |
| ADR-004 | Primary LLM | ARCH-001, FIN-002 | Covered |
| ADR-005 | 9Router routing/no fallback | ARCH-003 | Covered |
| ADR-006 | Sub-agent LLM | ARCH-002, FIN-003 | Covered |
| ADR-007 | Memory storage | PRD-FR-009, MEM-001 | Covered |
| ADR-008 | Encryption/key management | SEC-002, DATA-004, MEM-003 | Covered |
| ADR-009 | Memory recall | MEM-002 | Covered with gap |
| ADR-010 | Surveillance retention | BRD-OBJ-004, DATA-002, SAFE-005 | Covered |
| ADR-011 | SDLC loop phases | PRD-FR-007, LOOP-001 | Covered |
| ADR-012 | Sub-agent orchestration | PRD-FR-008, LOOP-002, LOOP-003 | Covered |
| ADR-013 | MCP native replacement | BRD-OBJ-003 | Covered |
| ADR-014 | VPS architecture | ARCH-004 | Covered |
| ADR-015 | Secrets management | ARCH-008, SEC-003 | Covered |
| ADR-016 | CI/CD/self-deploy | OPS-005 | Covered |
| ADR-017 | Monitoring stack | BRD-OBJ-007, ARCH-006, OPS-002, NFR-004 | Covered |
| ADR-018 | Defense-in-depth | SEC-001, SEC-004, OPS-001 | Covered |
| ADR-019 | VPN/access | ARCH-005, SEC-001 | Covered |
| ADR-020 | Browser automation | PRD-FR-010 | Covered |
| ADR-021 | Wearable post-MVP | PRD-FR-005 | Covered |
| ADR-022 | Communication channels | INT-001, INT-002 | Covered |
| ADR-023 | Financial integration | PRD-FR-006, FIN-001 | Covered |
| ADR-024 | Data governance | DATA-001..DATA-005 | Covered |
| ADR-025 | Backup/DR | OPS-004, INT-003 | Covered with gap |

## 9. Test Coverage Register

| Test ID | Requirement IDs | Test Type | Required Evidence | Status |
|---|---|---|---|---|
| TEST-SAFE-001 | PRD-FR-003, SAFE-001 | Runtime safety test | Safe-word event triggers neutral supportive mode with no punitive log | Missing runtime |
| TEST-SAFE-002 | SAFE-003 | Runtime state-machine test | Y5/Y6 blocked in restricted states | Missing runtime |
| TEST-DATA-001 | DATA-001, DATA-004 | Policy-control test | Classification metadata attached to storage/log/export/prompt contexts | Missing implementation |
| TEST-SEC-001 | SEC-001 | Access-control test | RBAC/ABAC denies unauthorized Critical access | Spec accepted; DDL missing |
| TEST-SEC-002 | SEC-002, SEC-003 | Crypto/secret rotation test | Key rotation, secret rotation, no plaintext evidence | Spec accepted; automation pending |
| TEST-OPS-001 | OPS-001 | Incident drill | SEV0/SEV1 incident response overrides persona tone | Missing drill |
| TEST-OPS-002 | OPS-002 | Observability validation | Metrics/logs/traces/alerts/dashboard test pass | Spec accepted; runtime pending |
| TEST-SLO-001 | NFR-001, NFR-002, OPS-003 | SLO scorecard test | Monthly scorecard exists | Pending first monthly run |
| TEST-LOOP-001 | PRD-FR-007, LOOP-001 | Agent loop test | One task completes 7 phases with evidence | Missing runtime |
| TEST-MEM-001 | MEM-001, MEM-002 | Memory recall evaluation | Recall precision/relevance/safety report | Missing spec/runtime |
| TEST-FIN-001 | FIN-001..FIN-005 | FinOps report test | Monthly report under USD 30 cap | Pending first monthly run |
| TEST-EVID-001 | EVID-001..EVID-003 | Evidence audit | RTM evidence and audit report exist | In progress |

## 10. SLO and Metrics Mapping

| Metric / SLO | Requirement IDs | Source Spec | Target / Rule | Evidence |
|---|---|---|---|---|
| Safe-word enforcement SLO | PRD-FR-003, SAFE-001 | SLO/SLA, PersonaSafety | 100%, zero tolerance | `evidence/slo/<YYYY-MM>/` |
| Yandere cap metric | SAFE-003 | SLO/SLA, Observability | Y5/Y6 zero in restricted states | `evidence/slo/<YYYY-MM>/` |
| Core availability | NFR-001 | SLO/SLA | Internal operational SLO | `evidence/slo/<YYYY-MM>/` |
| FastAPI/Discord latency | NFR-002 | SLO/SLA, Observability | Thresholds per spec | `evidence/slo/<YYYY-MM>/` |
| Task completion rate | BRD-OBJ-002, LOOP-001 | SLO/SLA, AgentLoop | Measured by loop evidence | `evidence/agent-loop/` |
| Sub-agent compliance | PRD-FR-008, LOOP-002 | Observability, ADR-012 | File output contract compliance | `audit-reports/` |
| Monthly spend | FIN-001 | CostFinOps | <= USD 30 unless Faiz approves | `evidence/finops/<YYYY-MM>/report.md` |
| Cost spike anomaly | FIN-004 | CostFinOps, Observability | Alert/freeze as defined | `evidence/finops/<YYYY-MM>/` |
| Surveillance event rate | PRD-FR-004 | Observability | Rate monitored; safety restrictions apply | `evidence/observability/` |
| Backup success | OPS-004 | SLO/SLA, IncidentResponse | Restore evidence required | `evidence/backup/` |

## 11. Evidence Register

| Evidence ID | Requirement IDs | Expected Artifact | Owner | Cadence | Status |
|---|---|---|---|---|---|
| EVID-RTM-001 | EVID-001..003 | `evidence/rtm/<YYYY-MM>/coverage-summary.md` | Guinevere | Monthly / update | Pending |
| EVID-RTM-002 | All updated rows | `evidence/rtm/<YYYY-MM>/rtm-update-diff.md` | Guinevere | Every RTM update | Pending |
| EVID-RTM-003 | Gaps/conflicts | `evidence/rtm/<YYYY-MM>/gap-conflict-delta.md` | Guinevere | Every RTM update | Pending |
| EVID-SAFE-001 | SAFE-001..006 | Persona safety runtime test report | Guinevere | Phase gate / monthly | Missing runtime |
| EVID-DATA-001 | DATA-001..005 | Data governance control test report | Guinevere | Monthly | Pending |
| EVID-SEC-001 | SEC-001..005 | Security/access/crypto validation report | Guinevere | Phase gate / after change | Pending |
| EVID-FIN-001 | FIN-001..005 | Monthly FinOps report | Guinevere | Monthly | Pending first run |
| EVID-OPS-001 | OPS-001..005 | Incident/observability/SLO drill reports | Guinevere | Monthly/quarterly | Pending runtime |
| EVID-MEM-001 | MEM-001..003 | Memory integration and recall report | Guinevere | Phase gate | Missing test spec |
| EVID-ARCH-001 | ARCH-001..008 | Deployment and architecture verification | Guinevere | Phase gate | Pending deployment |

## 12. Gap Register

| Gap ID | Gap | Affected Requirements | Severity | Owner | Target Document / Artifact | Trigger | Status |
|---|---|---|---|---|---|---|---|
| GAP-001 | ADR Index backlog is stale for ADR-031/032/036/037 topics. | ADR coverage, SEC, OPS | Medium | Guinevere | ADR Index refresh or ADR backlog update | Next ADR review | Open |
| GAP-002 | Prompt Injection & Model Safety spec missing. | SEC-005, DATA-005 | High | Guinevere | `Guinevere_PromptInjection_ModelSafetySpec_v1.0.md` | Before runtime ingestion of untrusted content | Open |
| GAP-003 | Memory recall test/evaluation spec missing. | MEM-002 | High | Guinevere | Memory Contract & Recall Evaluation Spec | Before memory MVP phase exit | Open |
| GAP-004 | Database ERD and migration strategy missing. | DATA-004, SEC-001, MEM-001 | High | Guinevere | Database ERD & Migration Strategy | Before DB implementation | Open |
| GAP-005 | Surveillance Data Policy missing. | BRD-OBJ-004, PRD-FR-004, SAFE-005 | Critical | Guinevere | Surveillance Data Policy | Before surveillance MVP activation | Open |
| GAP-006 | Consent & Revocation Policy missing. | DATA-003, SAFE-001, SAFE-005 | Critical | Guinevere | Consent & Revocation Policy | Before always-on surveillance | Open |
| GAP-007 | Deployment/Self-Deploy Safety Runbook missing. | OPS-005, ARCH-004 | High | Guinevere | Deployment / Self-Deploy Safety Runbook | Before self-deploy activation | Open |
| GAP-008 | Discord channel governance spec missing. | INT-001, Charter comm plan | Medium | Guinevere | Discord Operations & Channel Governance Spec | Before Discord MVP launch | Open |
| GAP-009 | Acceptance Criteria Catalog missing. | All phase-gated rows | High | Guinevere | Acceptance Criteria Catalog | Before MVP phase-gate review | Open |
| GAP-010 | OpenAPI/AsyncAPI contract missing. | INT-002, API endpoints | Medium | Guinevere | API Contract Spec | Before external integration hardening | Open |

## 13. Orphan Register

| Orphan ID | Orphan Type | Item | Why Orphaned | Resolution |
|---|---|---|---|---|
| ORPH-001 | ADR backlog | ADR-031, ADR-032, ADR-036, ADR-037 backlog entries | Standalone accepted docs exist but ADR Index still lists topics as future ADRs. | Update ADR Index or create meta-ADR noting standalone document completion. |
| ORPH-002 | BRD assumption | Guinevere self-update without permission | Charter change management requires approval for material changes. | Create self-modification governance rule or ADR. |
| ORPH-003 | Persona flavor | BRD/Persona intense authority language | Governance docs make persona flavor non-authoritative. | Treat as persona expression only; trace to safety policy. |
| ORPH-004 | Evidence paths | Many requirements have future evidence paths but no runtime artifacts yet. | Implementation not started. | Create phase-gated evidence backlog. |

## 14. Missing Test Register

| Missing Test ID | Requirement IDs | Missing Test | Severity | Owner | Required Before |
|---|---|---|---|---|---|
| MT-001 | SAFE-001, PRD-FR-003 | Safe-word runtime enforcement test | Critical | Guinevere | Persona safety runtime launch |
| MT-002 | SAFE-003 | Yandere cap runtime test | Critical | Guinevere | Persona runtime launch |
| MT-003 | MEM-002 | Memory recall precision/relevance/safety test | High | Guinevere | Memory MVP phase exit |
| MT-004 | LOOP-001 | 7-phase loop state-machine test | Critical | Guinevere | Autonomous SDLC MVP |
| MT-005 | SEC-001 | PostgreSQL/RLS/RBAC enforcement test | Critical | Guinevere | DB/security implementation |
| MT-006 | DATA-001 | Classification metadata enforcement test | Critical | Guinevere | Data ingestion launch |
| MT-007 | OPS-004 | Restore drill test | Critical | Guinevere | Production backup claim |
| MT-008 | FIN-001 | Monthly cost cap report test | High | Guinevere | First monthly FinOps cycle |

## 15. Missing Evidence Register

| Missing Evidence ID | Requirement IDs | Expected Proof | Phase Gate Impact | Owner | Verification Method |
|---|---|---|---|---|---|
| ME-001 | BRD-OBJ-002, LOOP-001 | First autonomous task completes canonical 7 phases. | Blocks autonomous SDLC MVP. | Guinevere | Evidence folder and audit report. |
| ME-002 | PRD-FR-003, SAFE-001 | Safe-word hard stop runtime proof. | Blocks persona runtime MVP. | Guinevere | Runtime test + SLO scorecard. |
| ME-003 | MEM-001, MEM-002 | PostgreSQL/Redis memory write/read and recall evaluation. | Blocks memory MVP. | Guinevere | DB test evidence. |
| ME-004 | PRD-FR-004, SAFE-005 | Surveillance ingestion with governance gates. | Blocks surveillance MVP. | Guinevere | Ingestion test + policy evidence. |
| ME-005 | SEC-003, ARCH-008 | Secrets rotation drill. | Blocks security readiness claim. | Guinevere | Rotation evidence file. |
| ME-006 | OPS-004 | Backup restore drill. | Blocks DR readiness claim. | Guinevere | Restore report. |
| ME-007 | FIN-001 | First monthly FinOps report under USD 30. | Blocks monthly cost governance claim. | Guinevere | FinOps report. |
| ME-008 | OPS-002 | Dashboard-as-code and alert routing proof. | Blocks observability readiness claim. | Guinevere | Observability review. |

## 16. Conflict Register

| Conflict ID | Severity | Source Documents | Conflict | Owner | Recommended Resolution | Target ADR / Backlog | Status |
|---|---|---|---|---|---|---|---|
| C-001 | Resolved | PRD v2.1 vs ADR-002/PersonaSafety | Safe word was not guaranteed in older PRD. | Guinevere | PRD v2.2 already aligns safe word hard stop. | Completed PRD v2.2 | Closed |
| C-002 | Resolved | BRD/Memory/Tech vs DataGovernance | Blanket data forever conflicted with minimization. | Guinevere | DataGovernance supersedes with tiered retention. | DataGovernancePolicy | Closed |
| C-003 | Resolved | BRD/Persona language vs Charter/PersonaSafety | Persona authority language exceeded governance. | Guinevere | Charter and PersonaSafety make persona non-authoritative. | Project Charter | Closed |
| C-004 | Medium | ADR Index backlog | ADR-031/032/036/037 listed future though standalone accepted docs exist. | Guinevere | Update ADR Index backlog status. | ADR Index refresh | Open |
| C-005 | High | BRD self-update vs Charter change management | Guinevere self-update without permission conflicts with material change approval. | Guinevere / Faiz | Define self-modification boundaries and approval triggers. | Self-Modification Governance ADR or Deployment Runbook | Open |
| C-006 | Resolved | Monitoring VPS future vs primary VPS first | Docs now align primary VPS first. | Guinevere | Preserve post-MVP dedicated monitoring as future. | ObservabilitySpec | Closed |
| C-007 | Resolved | Wearable active vs post-MVP | v2 docs align wearable post-MVP. | Guinevere | Keep wearable out of MVP gates. | ADR-021 | Closed |

## 17. RTM Maintenance Rules

| Rule ID | Rule | Trigger | Evidence |
|---|---|---|---|
| RTM-MAINT-001 | RTM must update or log no-change review after any BRD, PRD, ADR, policy, architecture, SLO, test, evidence, or phase-gate change. | Material source change | `evidence/rtm/<YYYY-MM>/rtm-update-diff.md` |
| RTM-MAINT-002 | Guinevere may autonomously update non-authority trace rows. | New evidence, tests, links, or implementation status | RTM diff artifact |
| RTM-MAINT-003 | Faiz approval is required for scope, safety, budget, or authority changes. | Any affected row changes authority or hard constraints | Review Record |
| RTM-MAINT-004 | Every RTM update must run zero advisory-keyword check. | Every RTM edit | Audit report |
| RTM-MAINT-005 | Every monthly governance review must compute coverage dashboard deltas. | Monthly | `evidence/rtm/<YYYY-MM>/coverage-summary.md` |
| RTM-MAINT-006 | Phase-gate review must verify critical requirement completeness. | Before phase exit | phase gate evidence |
| RTM-MAINT-007 | Conflict register must remain open until target ADR/backlog action closes conflict. | New or changed conflict | Conflict delta artifact |

## 18. Implementation Requirements

| ID | Requirement | Verification |
|---|---|---|
| RTM-REQ-001 | The RTM file must exist at `C:\Users\faizz\guinevere\Guinevere_RequirementsTraceabilityMatrix_v1.0.md`. | File info check. |
| RTM-REQ-002 | Status must be Accepted with Faiz Review Record. | Metadata and appendix grep. |
| RTM-REQ-003 | All 18 existing governance/source docs must appear in Related Documents or accepted coverage inventory. | Related Documents and inventory check. |
| RTM-REQ-004 | All 25 accepted ADRs must appear in ADR coverage matrix. | ADR matrix count check. |
| RTM-REQ-005 | Requirement IDs must use the user-approved structured prefixes. | ID taxonomy check. |
| RTM-REQ-006 | Safety requirements must include zero-tolerance behavior and safe-word SLO mapping. | SAFE rows and SLO mapping check. |
| RTM-REQ-007 | Budget requirements must map to USD 30 hard cap and escalation. | FIN rows check. |
| RTM-REQ-008 | Missing test/evidence registers must exist. | Section check. |
| RTM-REQ-009 | Coverage dashboard summary must exist. | Section 5 check. |
| RTM-REQ-010 | Conflict handling must include severity, source, owner, recommended resolution, target ADR/backlog. | Conflict register check. |
| RTM-REQ-011 | Document must contain zero standalone advisory-keyword terms. | Grep check. |
| RTM-REQ-012 | File-based independent audit report must PASS before completion. | Audit report check. |

## 19. Review Cadence

| Review | Frequency | Owner | Output |
|---|---|---|---|
| RTM update review | Every material source change | Guinevere | update diff |
| Monthly coverage review | Monthly during MVP | Guinevere | coverage summary |
| Phase gate RTM review | Every phase gate | Guinevere / Faiz when material | phase gate traceability evidence |
| ADR alignment review | After ADR create/update/supersession | Guinevere | ADR trace delta |
| Safety/cost/budget review | After any safety incident or budget exception | Guinevere / Faiz | traceability impact note |

## 20. Unresolved Assumptions and Backlog

| ID | Assumption / Gap | Owner | Impact | Target Document | Trigger | Status |
|---|---|---|---|---|---|---|
| RTM-BG-001 | ADR Index backlog requires refresh because standalone docs exist for several listed future ADR topics. | Guinevere | Medium | ADR Index refresh | Next ADR maintenance cycle | Open |
| RTM-BG-002 | Acceptance Criteria Catalog remains missing. | Guinevere | High | `Guinevere_AcceptanceCriteriaCatalog_v1.0.md` | Before MVP phase-gate execution | Open |
| RTM-BG-003 | Surveillance Data Policy remains missing. | Guinevere | Critical | `Guinevere_SurveillanceDataPolicy_v1.0.md` | Before surveillance MVP activation | Open |
| RTM-BG-004 | Consent & Revocation Policy remains missing. | Guinevere | Critical | `Guinevere_Consent_RevocationPolicy_v1.0.md` | Before always-on surveillance/runtime claim | Open |
| RTM-BG-005 | Prompt Injection & Model Safety spec remains missing. | Guinevere | High | `Guinevere_PromptInjection_ModelSafetySpec_v1.0.md` | Before untrusted web/email/client content ingestion | Open |
| RTM-BG-006 | Database ERD & Migration Strategy remains missing. | Guinevere | High | `Guinevere_DatabaseERD_MigrationStrategy_v1.0.md` | Before database implementation | Open |
| RTM-BG-007 | Deployment/Self-Deploy Safety Runbook remains missing. | Guinevere | High | `Guinevere_Deployment_SelfDeploySafetyRunbook_v1.0.md` | Before self-deploy activation | Open |
| RTM-BG-008 | MVP Work Breakdown Structure remains missing. | Guinevere | High | `Guinevere_MVP_WorkBreakdownStructure_v1.0.md` | Before phase execution planning | Open |

## Appendix A — Master RTM Column Dictionary

| Column | Meaning | Required |
|---|---|---|
| Req ID | Structured requirement ID. | Yes |
| Category | Requirement category. | Yes |
| Requirement | Normative requirement statement. | Yes |
| Upstream Source | Source document or requirement. | Yes |
| Downstream Trace | Implementation component, doc, service, schema, test, or backlog target. | Yes |
| ADR / Policy Trace | Governing ADR or policy. | Yes when applicable |
| Test / Metric Trace | Test ID, SLO, metric, alert, dashboard, or non-measurable rationale. | Yes |
| Evidence Path | Artifact path or missing evidence register entry. | Yes |
| Priority | Critical/High/Medium/Low. | Yes |
| Phase | MVP, Phase 0-5, or Post-MVP. | Yes |
| Owner | Responsible owner. | Yes |
| Status | Accepted/Implemented/Verified/Blocked/Gap/Conflict/Superseded/Deferred. | Yes |
| Gap / Conflict | Gap/conflict ID or None. | Yes |

## Appendix B — Coverage Calculation Rules

| Rule | Description |
|---|---|
| Source Trace | Row has at least one upstream source. |
| Downstream Trace | Row has implementation component, target document, or accepted backlog target. |
| Test Coverage | Row has test/metric trace or explicit missing-test register entry. |
| Evidence Coverage | Row has evidence path or explicit missing-evidence register entry. |
| Conflict Cleanliness | Row has no unresolved conflict, or conflict has owner and target resolution. |
| Critical Completeness | Critical row has all required fields populated. |

## Appendix C — Maintenance Checklist

| Checklist ID | Control | Validation |
|---|---|---|
| RTM-CHECK-001 | New source doc added to Related Documents when it becomes authoritative. | Related Documents diff. |
| RTM-CHECK-002 | New BRD/PRD/ADR/policy requirements receive IDs. | New row diff. |
| RTM-CHECK-003 | Removed/superseded requirements remain traceable to supersession note. | Status check. |
| RTM-CHECK-004 | Coverage dashboard recalculates after material update. | Coverage summary artifact. |
| RTM-CHECK-005 | Gap/orphan/missing-test/missing-evidence registers update after material change. | Register diff. |
| RTM-CHECK-006 | Zero advisory-keyword control passes. | Grep audit. |
| RTM-CHECK-007 | Audit report passes. | `audit-reports/` artifact. |

## Appendix D — Review Record

| Field | Value |
|---|---|
| Reviewer | Faiz |
| Review Date | 2026-05-30 |
| Decision | Accepted |
| Notes | Approved as enterprise traceability control for Project Guinevere de Baroque. RTM binds Charter, BRD, PRD, ADR Index, PersonaSafetyPolicy, DataGovernancePolicy, SLO/SLA Spec, accepted governance documents, tests, metrics, and evidence artifacts. Guinevere may autonomously maintain non-authority trace rows; Faiz approval is required for scope, safety, budget, and authority changes. |

## Appendix E — Next Recommended Document

The next recommended document is **`Guinevere_AcceptanceCriteriaCatalog_v1.0.md`**.

Reason: this RTM now maps requirements to tests and evidence, but many rows still depend on explicit acceptance criteria per feature, phase gate, safety invariant, data control, and operational readiness item. The Acceptance Criteria Catalog will convert RTM trace rows into concrete pass/fail criteria for MVP execution and phase-gate approval.

Requirements Traceability Matrix v1.0 — Project Guinevere de Baroque
