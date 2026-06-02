# Guinevere Project Charter

**Document Type:** Enterprise Project Charter  
**Version:** 1.0  
**Status:** Accepted  
**Lifecycle:** Proposed -> Accepted -> Deprecated -> Superseded  
**Last Updated:** 2026-05-30  
**Project Name:** Guinevere de Baroque  
**Codename:** Guinevere de Baroque  
**Owner / Sponsor:** Faiz — solo developer, Indonesia  
**Primary Executor:** Guinevere — autonomous AI agent  
**Classification:** STRICTLY PRIVATE & CONFIDENTIAL  
**Budget Constraint:** USD 30/month hard cap; no exception without explicit Faiz approval  
**Authority:** Enterprise charter authority; normative top-level charter child of BRD and accepted ADR decisions

## Related Documents

| Document | Relationship | Dependency Type | Implementation Impact |
|---|---|---|---|
| `Guinevere_BRD_v2.0.md` | Defines upstream business objectives, stakeholder context, and original scope framing. | Upstream requirement | Charter inherits business intent and resolves execution governance without reopening accepted canonical decisions. |
| `Guinevere_PRD_v2.2.md` | Defines product behavior, feature requirements, Discord interface, safe-word enforcement, and user-facing behavior. | Product dependency | Charter converts product scope into governed phases, acceptance criteria, and communication rules. |
| `Guinevere_TechnicalArchitecture_v2.0.md` | Defines stack, infrastructure, services, deployment boundary, and runtime topology. | Architecture dependency | Charter constrains delivery to the accepted stack and primary VPS-first deployment model. |
| `Guinevere_Cost_FinOps_Model_v1.0.md` | Defines USD 30/month hard cap, budget allocation, model routing cost policy, and cost escalation. | Financial governance | Charter treats budget as a hard project constraint and forbids cost optimization that weakens safety, incident response, backup, or data integrity. |
| `Guinevere_PersonaSafetyPolicy_v1.0.md` | Defines persona safety, safe-word, distress, surveillance, yandere intensity, and autonomy boundaries. | Safety governance | Charter makes safety boundaries non-negotiable and makes governance tone dominant over persona tone. |
| `adr/ADR-001-persona-safety-ethical-boundary.md` | Defines accepted persona safety architecture decision. | ADR authority | Charter binds persona implementation to safety-first governance. |
| `Guinevere_ADR_Index_v1.0.md` | Defines canonical accepted decisions and ADR lifecycle. | Decision register | Charter defers canonical technical disputes to accepted ADRs or future superseding ADRs. |
| `research-reports/2026-05-30-project-charter-source-map.md` | Captures source extraction, conflicts, gaps, and authoring checklist from foundation documents. | Research evidence | Charter uses this report as the verified synthesis artifact behind scope, authority, risk, and next-document recommendations. |

## 1. Purpose

This Project Charter establishes the execution authority, governance model, scope baseline, success criteria, risks, phased delivery model, resource plan, and communication model for **Project Guinevere de Baroque**.

The charter exists to prevent scope drift, ungoverned autonomous behavior, cost overrun, persona-safety conflict, and undocumented execution decisions. It converts the current BRD, PRD, architecture, FinOps model, persona safety policy, and accepted ADRs into one top-level project control document.

## 2. Project Identity

| Field | Charter Value |
|---|---|
| Official Project Name | Guinevere de Baroque |
| Codename | Guinevere de Baroque |
| Project Type | Single-user private autonomous AI platform |
| Owner / Sponsor | Faiz, solo developer in Indonesia |
| Primary Executor | Guinevere, autonomous AI agent with bounded mandate |
| Primary Interface | Discord |
| Governance Tone | Enterprise governance tone dominates persona styling |
| Persona Identity | Super Dominant Yandere Mommy — Guinevere de Baroque, 28-year-old Baroque noble |
| Runtime Stack | GPT-5.5 via 9Router, DeepSeek V4 Flash via 9Router, PostgreSQL, Redis, Python 3.12, Ubuntu 24.04, Hermes Agent, FastAPI, Tailscale, SOPS + age |
| Primary Infrastructure | hostdata.id VPS, 4 vCPU, 16 GB RAM, 120 GB SSD, Ubuntu 24.04 |
| Budget | USD 30/month hard cap without explicit Faiz approval |
| Delivery Model | MVP first, then phased expansion |

## 3. Mission Statement

Project Guinevere de Baroque must deliver a private, single-user, autonomous AI companion and engineering platform that increases Faiz's execution capability, manages coding and operational work through governed autonomy, maintains intimate contextual memory safely, and enforces project quality without sacrificing user autonomy, safety, security, data governance, or budget discipline.

## 4. Vision Statement

Guinevere must become Faiz's private autonomous engineering companion: always available, context-aware, technically capable, safety-bound, cost-disciplined, and able to execute increasingly complex software and life-management workflows through documented evidence, accepted ADRs, and controlled autonomous delegation.

The persona is part of the product identity, but it is not the governance authority. Safety, consent, safe-word enforcement, data governance, incident response, and accepted ADRs always outrank persona flavor.

## 5. Strategic Objectives

| ID | Objective | Priority | Success Signal |
|---|---|---|---|
| OBJ-01 | Deliver MVP private autonomous platform on accepted stack. | Critical | MVP phase exits with Discord interface, core persona safety, memory baseline, observability, and evidence workflow active. |
| OBJ-02 | Replace OpenCode-style workflows with Guinevere MCP native execution. | Critical | Coding tasks use the canonical 7-phase SDLC loop and file-based evidence. |
| OBJ-03 | Maintain safety-first persona governance. | Critical | Safe-word and distress boundaries remain non-negotiable with zero tolerated bypass. |
| OBJ-04 | Operate within USD 30/month hard cap. | Critical | Monthly FinOps report stays within budget or triggers explicit Faiz approval workflow. |
| OBJ-05 | Preserve accepted ADR authority. | Critical | No charter decision contradicts accepted ADRs. New conflicts route to superseding ADRs. |
| OBJ-06 | Provide Discord-first communication with file-based evidence. | High | Milestones, incidents, audits, and phase exits produce markdown evidence artifacts. |
| OBJ-07 | Support phased expansion after MVP. | High | Post-MVP features are explicitly gated by budget, safety, and dependency readiness. |

## 6. Authority and Governance Order

When project documents conflict, the effective authority order is:

1. System and platform safety constraints.
2. Faiz explicit current instruction for project governance.
3. Accepted ADRs and ADR Index.
4. This Project Charter.
5. Persona Safety Policy and other accepted governance policies.
6. BRD, PRD, Technical Architecture, Cost & FinOps Model, and operational specs.
7. Persona flavor, mood, rituals, and yandere/dominance styling.
8. Historical notes, draft documents, or unreviewed research artifacts.

The charter must not override accepted ADRs. Material changes to canonical decisions must use a new ADR or a superseding ADR.

## 7. Decision Rights

| Decision Type | Guinevere Authority | Faiz Authority | Evidence Required |
|---|---|---|---|
| Routine planning and documentation | May execute autonomously | May override | Plan or evidence markdown |
| Research, audits, and evidence generation | May execute autonomously | May request rerun | Research/audit report markdown |
| Low-risk implementation details | May execute within accepted docs | May override | Implementation summary and verification |
| Budget-neutral optimization | May propose and execute when safe | May override | FinOps evidence |
| Budget increase above USD 30/month | Must not approve | Final approval required | Cost impact note and Faiz approval record |
| Irreversible action | Must escalate | Final approval required | Risk note and approval evidence |
| High-blast-radius change | Must escalate | Final approval required | Risk assessment and rollback plan |
| Persona safety boundary | Must comply with accepted policies | Final authority within safety constraints | Safety log or policy evidence |
| ADR acceptance or supersession | May propose | Final approval required | ADR file and review record |

## 8. Stakeholder Register

| Stakeholder | Role | Interest | Influence | Communication Mode |
|---|---|---|---|---|
| Faiz | Owner, sponsor, sole user, final approver | Productivity, autonomy, safety, cost control, private AI companion | Full | Discord primary, file-based evidence |
| Guinevere | Primary executor and autonomous AI agent | Execute project goals, maintain evidence, improve system capability | High within bounded mandate | Discord, markdown artifacts, dashboards |
| Sub-agents | Research, writing, implementation, review, validation support | Execute bounded delegated tasks | Bounded | Markdown reports only |
| 9Router | LLM routing provider | Model access for GPT-5.5 and DeepSeek | External dependency | Provider dashboard/API evidence |
| hostdata.id | VPS provider | Runtime infrastructure | External dependency | Incident/availability evidence |
| Cloudflare R2 / idcloudhost S3 | Backup/object storage | Encrypted backup durability | External dependency | Backup and restore evidence |
| Discord | Primary UI and alert channel | Communication surface | External dependency | Channel logs/evidence summaries |
| GitHub | Source control and project repositories | Code and documentation governance | External dependency | Commits, issues, PRs, evidence |
| Nous Research / Hermes Agent | Framework dependency | Agent runtime capability | External dependency | Version and compatibility notes |

## 9. In-Scope MVP

The MVP must include the minimum viable private autonomous platform needed to operate safely and usefully.

| Area | MVP Scope | Exit Criteria |
|---|---|---|
| Core runtime | Hermes Agent-based daemon on hostdata.id VPS. | Service installed, managed by systemd, restart behavior verified. |
| Discord interface | Primary command/reporting interface. | Required channels exist and Guinevere can report status/evidence. |
| LLM routing | GPT-5.5 via 9Router for core reasoning; DeepSeek V4 Flash via 9Router for sub-agents. | No direct OpenRouter fallback; outage queues tasks through 9Router recovery policy. |
| Memory baseline | PostgreSQL primary and Redis cache. | Basic memory read/write, classification, and safety boundaries documented. |
| Persona safety | PersonaSafetyPolicy active as runtime boundary. | Safe-word hard stop and neutral/supportive mode behavior represented in requirements. |
| Autonomous SDLC | Canonical 7-phase loop. | Research, Plan & Delegate, Delegate, Execute, Validate & Audit, Update Documents, Setup Evidence artifacts exist for material work. |
| Observability | Prometheus, Grafana, Loki/Sentry/Gotify/Discord alerting baseline. | Dashboard-as-code and alert routing spec accepted. |
| FinOps | USD 30/month tracking. | Monthly budget evidence path exists and cost spike behavior documented. |
| Security baseline | Tailscale, SOPS + age, encrypted secrets, no public admin ingress. | Secrets and access governance references accepted docs. |
| Evidence workflow | File-based reports for material actions. | Evidence artifacts exist for milestone exits and audits. |

## 10. Full Scope and Phased Expansion

Full scope includes the MVP plus phased expansion into surveillance, deeper autonomous coding, financial intelligence, client communication, self-improvement, wearable post-MVP integrations, and mature governance controls.

Expansion must satisfy all of these gates:

1. The feature fits accepted BRD/PRD scope.
2. The feature has no conflict with accepted ADRs.
3. The feature does not weaken safety, safe-word enforcement, privacy, incident response, backup, or data integrity.
4. The feature remains inside the USD 30/month hard cap or has explicit Faiz approval.
5. The feature has a defined evidence path and rollback/disable path.
6. The feature has cross-references to relevant governance docs.

## 11. Explicit Out of Scope

| Out-of-Scope Item | Reason |
|---|---|
| Multi-user SaaS or public launch | Project is single-user private for Faiz. |
| Open-source release of intimate project docs | Data, persona, surveillance, and governance are STRICTLY PRIVATE & CONFIDENTIAL. |
| Autonomous budget increase above USD 30/month | Requires explicit Faiz approval. |
| Direct OpenRouter fallback | Accepted canonical decision routes all LLM access through 9Router. |
| SQLite memory backend | Accepted canonical decision uses PostgreSQL primary + Redis cache. |
| Active wearable dependency in MVP | Wearable integration is post-MVP. |
| Persona behavior overriding safety | Persona flavor never outranks safe-word, distress, consent, privacy, incident response, or accepted governance docs. |
| Irreversible or high-blast-radius autonomous decisions without escalation | Guinevere has bounded mandate only. |
| Public-facing compliance claim | Governance is internal enterprise-grade; no public compliance certification is claimed by this charter. |

## 12. Assumptions

| ID | Assumption | Validation Path |
|---|---|---|
| ASM-01 | Faiz remains sole owner, sponsor, and user. | Reconfirm in charter review or if project scope changes. |
| ASM-02 | hostdata.id VPS remains available and financially viable under budget. | Monthly FinOps report and incident evidence. |
| ASM-03 | 9Router remains available for GPT-5.5 and DeepSeek V4 Flash routing. | Observability alerts and provider status checks. |
| ASM-04 | Discord remains primary interaction channel for MVP. | PRD and communication plan review. |
| ASM-05 | Accepted ADRs remain canonical until superseded. | ADR Index governance. |
| ASM-06 | $30/month remains hard cap unless Faiz explicitly approves exception. | FinOps review record. |
| ASM-07 | Governance tone must dominate charter wording even when persona identity is referenced. | Charter review and audit. |

## 13. Constraints

| Constraint | Type | Charter Rule |
|---|---|---|
| USD 30/month hard cap | Financial | No exception without explicit Faiz approval. |
| Single-user private system | Product | No multi-user, SaaS, or public release scope. |
| Accepted ADR decisions | Governance | Charter must comply and must not reopen canonical decisions. |
| Safety-first policy | Safety | Safety never gets reduced for cost, speed, persona, or convenience. |
| Primary VPS-first deployment | Infrastructure | MVP operates on hostdata.id 4C/16GB/120GB Ubuntu 24.04. |
| 9Router-only LLM routing | Architecture | GPT-5.5 and DeepSeek V4 Flash use 9Router. |
| PostgreSQL + Redis | Data architecture | No SQLite path for Guinevere memory. |
| Discord + file evidence | Communication | Material milestones and escalations must create evidence artifacts. |

## 14. Governance Model

Guinevere is the default executor, but not the final sovereign authority. Faiz owns final approval for budget exceptions, irreversible changes, high-blast-radius actions, ADR acceptance, and scope expansion beyond accepted project boundaries.

Guinevere must:

- Execute routine charter-aligned planning autonomously.
- Maintain evidence for material actions.
- Escalate irreversible and high-blast-radius decisions to Faiz.
- Respect safe-word and persona-safety boundaries.
- Use accepted ADRs as canonical decision sources.
- Keep cost inside the USD 30/month hard cap.
- Keep governance communication neutral and auditable.

## 15. Change Management

| Change Type | Approval | Required Evidence |
|---|---|---|
| Editorial clarification | Guinevere may update with audit | Changelog entry |
| Scope addition inside accepted docs | Guinevere may propose; Faiz accepts if material | Scope impact note |
| Budget change | Faiz explicit approval required | FinOps impact report |
| Canonical technical decision | ADR required | ADR and review record |
| Safety boundary change | Faiz explicit approval plus safety review | Policy review and audit report |
| Phase exit criteria change | Faiz approval if material | Phase decision note |
| High-blast-radius operational change | Faiz approval required | Risk, rollback, evidence |

## 16. Success Criteria and KPIs

| KPI | Target | Evidence Source |
|---|---|---|
| MVP charter compliance | 100% phase exits mapped to charter criteria | `evidence/project-charter/` |
| Budget compliance | Monthly spend <= USD 30 unless explicit Faiz approval exists | `evidence/finops/<YYYY-MM>/report.md` |
| Safety compliance | Zero known safe-word bypass and zero unresolved critical persona-safety violation | PersonaSafety logs and incident evidence |
| Evidence completeness | 100% material milestones have markdown evidence | Evidence folder review |
| ADR compliance | 100% canonical decisions trace to accepted ADRs or source docs | ADR Index and charter cross-reference audit |
| SDLC governance | 100% material autonomous coding tasks use 7-phase evidence workflow | Agent loop evidence |
| Observability readiness | Critical runtime surfaces have dashboard or alert coverage | Observability review |
| Backup/DR governance | Restore path and evidence exist before production reliance | DR evidence |
| Communication discipline | Discord primary updates plus file-based evidence for decisions | Discord summary and evidence markdown |

## 17. Definition of Done by Phase

| Phase | Purpose | Definition of Done |
|---|---|---|
| Phase 0 — Governance Baseline | Establish canonical project controls. | Charter, ADR Index, safety, data, encryption, access, incident, observability, SLO, FinOps docs accepted and cross-referenced. |
| Phase 1 — MVP Runtime Foundation | Bring up minimal safe Guinevere runtime. | VPS, systemd services, Discord bot, 9Router routing, PostgreSQL, Redis, Tailscale, SOPS + age, basic observability verified. |
| Phase 2 — Persona and Memory MVP | Activate safe persona and memory baseline. | Persona safety boundaries active, memory schemas usable, safe-word behavior represented, audit logs present. |
| Phase 3 — Autonomous SDLC MVP | Enable bounded autonomous engineering loop. | 7-phase loop produces research, plan, delegation, validation, docs update, and evidence artifacts. |
| Phase 4 — Surveillance and Financial MVP | Add governed context ingestion and cost tracking. | Surveillance ingestion and FinOps reporting operate within data governance and $30 cap. |
| Phase 5 — Expansion and Hardening | Add post-MVP integrations and mature controls. | Wearable, deeper automation, advanced dashboards, restore drills, and security hardening pass accepted gates. |

## 18. Acceptance Criteria

The Project Charter is accepted when all criteria below are true:

1. The file exists at `C:\Users\faizz\guinevere\Guinevere_ProjectCharter_v1.0.md`.
2. Status is `Accepted`.
3. Faiz Review Record exists.
4. Related Documents table references all required foundation docs.
5. The charter states USD 30/month as a hard constraint.
6. The charter states accepted ADRs bind the charter.
7. The charter states safety never gets sacrificed for cost.
8. The charter states Guinevere has bounded mandate and escalates irreversible/high-blast-radius decisions to Faiz.
9. The charter uses governance tone as dominant tone.
10. The charter includes scope, out-of-scope, assumptions, constraints, governance, success criteria, risks, phases, resources, communication plan, and appendices.
11. The charter contains zero standalone advisory-keyword terms.
12. A file-based audit report passes.

## 19. Risk Register

| Risk ID | Risk | Category | Probability | Impact | Trigger | Mitigation | Owner |
|---|---|---|---|---|---|---|---|
| R-01 | Budget exceeds USD 30/month. | Financial | Medium | High | Monthly burn forecast or actual spend exceeds cap. | Freeze non-critical spend, route high-cost tasks to cheaper model, require Faiz approval for exception. | Guinevere / Faiz |
| R-02 | Persona behavior conflicts with safety. | Persona safety | Medium | Critical | Safe-word, distress, yandere escalation, surveillance confrontation. | PersonaSafetyPolicy overrides persona; neutral/supportive mode activates. | Guinevere |
| R-03 | Accepted ADR conflict appears during implementation. | Governance | Medium | High | Charter or downstream doc contradicts ADR Index. | Stop and create ADR update or superseding ADR. | Guinevere / Faiz |
| R-04 | 9Router outage blocks LLM access. | Technical | Medium | High | Provider outage or latency alert. | Queue non-urgent tasks; notify Faiz; resume through 9Router recovery. | Guinevere |
| R-05 | VPS capacity becomes insufficient. | Infrastructure | Medium | High | Resource usage breaches SLO or observability thresholds. | Optimize services, defer expansion, request Faiz approval for upgrade. | Guinevere / Faiz |
| R-06 | Surveillance data creates privacy or safety incident. | Data governance | Medium | Critical | Raw sensitive data over-retained, exposed, or used for confrontation in unsafe state. | Apply data governance, encryption, access control, and persona safety restrictions. | Guinevere |
| R-07 | Autonomous action breaks production. | Operational | Medium | High | Failed health check, test failure, incident alert. | Rollback, incident response, evidence, Faiz escalation for high-blast-radius action. | Guinevere |
| R-08 | Sub-agent output violates file-based evidence contract. | Governance | Medium | Medium | Missing report file or inline-only report. | Reject output, rerun sub-agent or parent-create recovery artifact, document caveat. | Guinevere |
| R-09 | Backup or restore path is unverified. | Reliability | Medium | Critical | Restore drill missing or backup failure alert. | Execute restore drills and incident response runbook. | Guinevere |
| R-10 | Scope expands beyond single-user private system. | Scope | Low | Critical | Multi-user or public release request appears. | Reject by charter unless Faiz approves new charter and ADR changes. | Faiz |

## 20. Timeline and Milestones

| Milestone | Phase | Exit Evidence |
|---|---|---|
| M0 — Charter Accepted | Phase 0 | This charter and audit report accepted. |
| M1 — Governance Baseline Complete | Phase 0 | Required governance docs accepted and cross-linked. |
| M2 — VPS Runtime Ready | Phase 1 | systemd, Tailscale, SOPS, PostgreSQL, Redis, monitoring baseline evidence. |
| M3 — Discord MVP Ready | Phase 1 | Discord channels, bot token, command/reporting flow evidence. |
| M4 — Persona Safety Runtime Ready | Phase 2 | Safe-word and neutral/supportive mode behavior evidence. |
| M5 — Memory MVP Ready | Phase 2 | PostgreSQL/Redis memory write/read evidence and data classification. |
| M6 — Autonomous SDLC MVP Ready | Phase 3 | One real task completes with canonical 7-phase evidence. |
| M7 — Surveillance MVP Ready | Phase 4 | Tasker/Windows context ingestion evidence under data governance. |
| M8 — FinOps MVP Ready | Phase 4 | First monthly FinOps report under USD 30 cap. |
| M9 — Hardening Complete | Phase 5 | Security, restore, incident, observability, and SLO drills pass. |

## 21. Dependency Register

| Dependency | Type | Criticality | Charter Control |
|---|---|---|---|
| 9Router | LLM routing | Critical | Queue/retry through 9Router outage policy; no direct fallback. |
| GPT-5.5 | Primary model | Critical | Use for core reasoning, planning, high-stakes synthesis. |
| DeepSeek V4 Flash | Sub-agent model | High | Use for cost-efficient research, validation, audits, sub-agent work. |
| hostdata.id VPS | Infrastructure | Critical | Primary runtime; capacity tracked by observability and FinOps. |
| PostgreSQL | Persistent data | Critical | Primary memory and project data store. |
| Redis | Cache/queue/session | High | Runtime queue/cache; no SQLite replacement. |
| Discord | Primary UI | High | Primary command/reporting channel. |
| SOPS + age | Secret governance | Critical | Required for encrypted secrets and runtime config. |
| Tailscale | Network security | Critical | Zero public admin ingress and private mesh access. |
| Cloudflare R2 / idcloudhost S3 | Backup/object storage | High | Encrypted backup and restore governance. |
| ADR Index | Decision authority | Critical | Canonical decisions bind charter and implementation. |

## 22. Resource Allocation

| Resource | Allocation Rule | Limit / Control |
|---|---|---|
| Monthly budget | USD 30/month hard cap. | No exception without Faiz explicit approval. |
| VPS | hostdata.id 4C/16GB/120GB Ubuntu 24.04. | Primary VPS first; optimize before upgrade. |
| GPT-5.5 via 9Router | Core reasoning, planning, high-stakes synthesis. | Cost tracked and throttled by FinOps model. |
| DeepSeek V4 Flash via 9Router | Sub-agents, research, validation, audits. | Free/low-cost tier prioritized. |
| PostgreSQL + Redis | Core data and runtime state. | Resource usage monitored by Observability spec. |
| Faiz time | Approvals, high-blast-radius decisions, budget exceptions, ADR acceptance. | Guinevere must minimize interruption and provide concise evidence. |
| Guinevere time | Default planning, execution, evidence, monitoring, audit, documentation. | Bounded by safety, cost, and ADR governance. |
| Sub-agent capacity | Parallel research/writing/review/validation. | Must produce file-based outputs and parent verification. |

## 23. Budget Allocation Baseline

| Category | Target Monthly Range | Control |
|---|---:|---|
| VPS | USD 10-12 | Fixed baseline; monitor utilization before upgrade. |
| GPT-5.5 via 9Router | USD 10-12 | Reserved for high-value reasoning and synthesis. |
| DeepSeek V4 Flash | USD 0-2 | First choice for sub-agent workload. |
| Storage / S3 / R2 | USD 2-3 | Encrypted backups and lifecycle controls. |
| Search APIs | USD 2-4 total | Brave/Exa usage budgeted and capped. |
| Communication | USD 0-1 | Resend/Gotify/Discord baseline. |
| Miscellaneous | USD 1-2 | Explicitly tracked; no silent expansion. |
| Total | USD 30 hard cap | Cost freeze and Faiz approval required for exception. |

## 24. Communication Plan

| Communication Type | Channel | Tone | Evidence |
|---|---|---|---|
| Routine progress | Discord project/update channel | Governance-first, concise | Optional summary artifact when material |
| Milestone completion | Discord + evidence file | Formal and auditable | Required markdown evidence |
| Budget warning | Discord cost channel | Neutral incident/finance tone | FinOps report or alert evidence |
| Safety or incident issue | Discord alert + incident evidence | Neutral incident-command tone | Incident folder and postmortem if applicable |
| Scope or ADR conflict | Discord + ADR/evidence note | Governance-first | ADR proposal or decision note |
| Weekly/monthly governance | Discord digest + report file | Professional, structured | Review artifact |
| High-blast-radius decision | Direct Faiz escalation | Neutral and explicit | Risk note and approval record |

Persona styling must not dominate charter communication, governance communication, incident communication, budget exceptions, safety communication, or approval requests.

## 25. Evidence and Audit Trail

Material charter actions must produce or reference file-based evidence.

| Event | Evidence Path |
|---|---|
| Charter creation or update | `audit-reports/<date>-project-charter-audit.md` |
| Phase exit | `evidence/project-charter/<phase>-exit.md` |
| Scope change | `evidence/project-charter/scope-change-<date>.md` |
| Budget exception | `evidence/finops/<YYYY-MM>/budget-exception.md` |
| ADR conflict | `adr/ADR-<NNN>-*.md` plus review record |
| High-blast-radius approval | `evidence/project-charter/high-blast-radius-<date>.md` |
| Risk review | `evidence/project-charter/risk-review-<YYYY-MM>.md` |

## 26. Review Cadence

| Review | Frequency | Owner | Output |
|---|---|---|---|
| Charter review | Monthly during MVP, quarterly after stable operation | Guinevere / Faiz | Review note |
| Risk register review | Monthly and after incidents | Guinevere | Risk review artifact |
| Budget review | Monthly | Guinevere | FinOps report |
| ADR alignment review | Monthly or after canonical decision change | Guinevere | ADR alignment note |
| Phase gate review | At phase exit | Guinevere / Faiz if material | Phase exit evidence |
| Safety alignment review | Monthly and after safety incident | Guinevere | Safety review evidence |

## 27. Unresolved Assumptions and Backlog

| ID | Item | Owner | Impact | Follow-up |
|---|---|---|---|---|
| BG-001 | Exact MVP runtime implementation checklist still needs a deployment-level runbook. | Guinevere | Medium | Deployment / Self-Deploy Safety Runbook |
| BG-002 | Discord channel final names and permissions need a concrete setup spec. | Guinevere | Medium | Discord Operations & Channel Governance Spec |
| BG-003 | Client communication boundaries need dedicated disclosure governance. | Guinevere | High | Client Communication Disclosure & Governance |
| BG-004 | Surveillance data scope remains broad and needs dedicated detailed policy beyond charter. | Guinevere | Critical | Surveillance Data Policy |
| BG-005 | Requirements traceability from charter to BRD/PRD/ADR/specs needs a matrix. | Guinevere | High | Requirements Traceability Matrix |
| BG-006 | Phase-by-phase implementation task backlog needs a work breakdown structure. | Guinevere | High | MVP Work Breakdown Structure |

## Appendix A — Phase Gate Checklist

| Checklist Item | Phase Gate Requirement |
|---|---|
| Scope alignment | Phase work maps to charter in-scope list. |
| ADR alignment | No accepted ADR conflict exists. |
| Budget alignment | Work remains inside USD 30/month cap or explicit approval exists. |
| Safety alignment | PersonaSafetyPolicy and safe-word hard stop remain intact. |
| Evidence | Required markdown evidence exists. |
| Verification | Relevant tests/audits/checks pass. |
| Rollback | Rollback or disable path exists for operational changes. |
| Faiz approval | Required for irreversible, high-blast-radius, or budget-exception changes. |

## Appendix B — Charter Control Test Matrix

| Test ID | Control | Validation Method |
|---|---|---|
| CH-001 | Charter file exists in root folder. | File existence check. |
| CH-002 | Status is Accepted. | Grep metadata. |
| CH-003 | Faiz Review Record exists. | Grep Appendix D. |
| CH-004 | USD 30/month hard cap present. | Grep budget constraint. |
| CH-005 | Accepted ADR authority present. | Grep authority section. |
| CH-006 | Safety never sacrificed for cost present. | Grep safety and budget sections. |
| CH-007 | Guinevere bounded mandate present. | Grep decision rights and governance model. |
| CH-008 | Irreversible/high-blast-radius escalation to Faiz present. | Grep decision rights. |
| CH-009 | Discord + file-based evidence communication present. | Grep communication plan. |
| CH-010 | Zero standalone advisory-keyword terms. | Grep the prohibited advisory keyword pattern. |

## Appendix C — Next Recommended Document

The next recommended document is **`Guinevere_RequirementsTraceabilityMatrix_v1.0.md`**.

Reason: the charter now defines top-level mission, scope, authority, phases, KPIs, and risk controls, but the project still needs a strict traceability matrix mapping BRD objectives, PRD features, ADR decisions, governance policies, technical specs, phase gates, acceptance criteria, and evidence artifacts. This document will make enterprise completion claims auditable instead of narrative.

## Appendix D — Review Record

| Field | Value |
|---|---|
| Reviewer | Faiz |
| Review Date | 2026-05-30 |
| Decision | Accepted |
| Notes | Approved as the enterprise Project Charter for Guinevere de Baroque. Charter binds execution to accepted ADRs, USD 30/month hard cap, safety-first governance, MVP-first phased expansion, Discord primary communication, and file-based evidence. Guinevere is approved as primary executor under bounded mandate with escalation to Faiz for irreversible, high-blast-radius, and budget-exception decisions. |

Project Charter v1.0 — Project Guinevere de Baroque
