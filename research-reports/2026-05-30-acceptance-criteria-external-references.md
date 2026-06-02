# External References: Acceptance Criteria & QA Patterns for Enterprise Acceptance Criteria Catalog

**Date**: 2026-05-30
**Researcher**: Guinevere (Librarian)
**Purpose**: Research practical patterns, standards, and frameworks for constructing an enterprise-grade Acceptance Criteria Catalog, adapted for Project Guinevere (autonomous AI companion/engineering system).

---

## Table of Contents

1. [Core Acceptance Criteria Patterns](#1-core-acceptance-criteria-patterns)
2. [Definition of Ready vs Definition of Done](#2-definition-of-ready-vs-definition-of-done)
3. [Requirements Traceability Matrix (RTM)](#3-requirements-traceability-matrix-rtm)
4. [Phase Gates & Stage-Gate Models](#4-phase-gates--stage-gate-models)
5. [Quality Gates in CI/CD & Deployment](#5-quality-gates-in-cicd--deployment)
6. [SLO-Based Acceptance Gates](#6-slo-based-acceptance-gates)
7. [Safety, Security & Data Acceptance Criteria (AI/Agent-Specific)](#7-safety-security--data-acceptance-criteria-aiagent-specific)
8. [Evidence-Based Acceptance & Auditability](#8-evidence-based-acceptance--auditability)
9. [QA Checklists & Release Readiness](#9-qa-checklists--release-readiness)
10. [Regulatory & Compliance Standards (ISO 13485, IEC 62304, FDA)](#10-regulatory--compliance-standards-iso-13485-iec-62304-fda)
11. [AI Agent-Specific Evaluation Libraries](#11-ai-agent-specific-evaluation-libraries)
12. [Synthesis: Patterns Relevant to Guinevere](#12-synthesis-patterns-relevant-to-guinevere)
13. [Sources & References](#13-sources--references)

---

## 1. Core Acceptance Criteria Patterns

### 1.1 Given/When/Then (Gherkin / BDD)

The most widely adopted pattern for structuring acceptance criteria. Originates from Behavior-Driven Development (BDD) and uses Gherkin syntax.

**Reference**: [BDD Gherkin User Stories: Acceptance Criteria at Scale — Visual Paradigm](https://skills.visual-paradigm.com/docs/user-story-techniques-large-scale-agile/advanced-enterprise-story-patterns/bdd-gherkin-user-stories-acceptance-criteria/)

**Standard Template**:
```gherkin
Feature: [User Action] on [System]
  As a [User Role]
  I want to [User Goal]
  So that [Business Value]

  Scenario: [Short Description of Path]
    Given [Precondition]
    When [Trigger Event]
    Then [Expected Outcome]
    And [Additional Outcome, if needed]
```

**Key Rules**:
- Each scenario represents one distinct user journey.
- Link to shared acceptance criteria for cross-team consistency.
- Decision tables help manage complex logic with multiple inputs/outputs.
- Not for every story — use for complex, high-risk, or cross-team stories only. Simple tasks can use bullet lists.

### 1.2 Actor-State-Trigger-Evidence Pattern

**Reference**: [Acceptance Criteria Hub — Spec Coding](https://spec-coding.dev/acceptance-criteria)

**Template**:
```
# Acceptance criteria block

- Given [actor/state/precondition]
  When [trigger/action]
  Then [observable result]
  And [side effect or audit proof]

Negative path:
- Given [invalid input or denied permission]
  When [same trigger]
  Then [clear failure behavior]
  And [no unsafe side effect]
```

**Quality Checklist for Each Criterion**:
| Check | Pass Condition |
|---|---|
| Actor | The user, client, job, or system role is named |
| Precondition | Starting state concrete enough to build a fixture |
| Trigger | Action or event is specific and repeatable |
| Expected result | Outcome observable without interpretation |
| Negative path | Invalid input, denied permission, or retry behavior covered |

### 1.3 Acceptance Criteria Quality Characteristics

**Reference**: [Acceptance Criteria — Atlassian](https://wac-cdn.atlassian.com/work-management/project-management/acceptance-criteria)

Well-written acceptance criteria are:
- **Clear and concise** — plain language all stakeholders interpret the same way
- **Testable/Verifiable** — maps cleanly to one or more executable tests
- **Result-oriented** — describes what user experiences, not technical steps
- **Quantifiable** — measurable terms creating definitive pass/fail threshold
- **Independent** — each criterion stands alone, testable in isolation
- **Pass/fail only** — never only partially fulfilled

### 1.4 Acceptance Criteria vs Definition of Done

**Reference**: [Acceptance Criteria vs Definition of Done — AltexSoft](https://www.altexsoft.com/blog/acceptance-criteria-definition-of-done/)  
**Reference**: [Definition of Done vs Acceptance Criteria — Nulab](https://nulab.com/learn/software-development/definition-of-done-vs-acceptance-criteria/)

| Aspect | Acceptance Criteria (AC) | Definition of Done (DoD) |
|---|---|---|
| Scope | Specific to one user story/PBI | Universal across all work |
| Focus | Functional behavior, user-facing | Quality standards, process readiness |
| Answers | "Does this feature do what it's supposed to?" | "Is this feature ready to release?" |
| Created by | Product Owner during refinement | Entire team, start of project |
| Content | Features, conditions, behaviors | Code review, testing, docs, deployment |
| Mutability | Per-story | Stable, updated in retrospectives |

---

## 2. Definition of Ready vs Definition of Done

### 2.1 Definition of Ready (DoR)

**Reference**: [Definition of Ready vs. Definition of Done — Scrum Alliance](https://resources.scrumalliance.org/Article/definition-vs-ready)  
**Reference**: [Ready and Done Criteria in Technical Stories — Agile Seekers](https://agileseekers.com/blog/defining-and-using-ready-and-done-criteria-in-technical-stories)

DoR criteria (optional but valuable):
- PBI written in clear, concise way
- Acceptance criteria defined and testable
- Dependencies identified and addressed
- Stakeholders approved the PBI
- Team has information/skills to complete
- Estimate assigned
- No blockers found

**INVEST Matrix for DoR**:
| Letter | Meaning |
|---|---|
| I | Immediately actionable |
| N | Negotiable details |
| V | Value to stakeholders |
| E | Estimable effort |
| S | Small (fits one sprint) |
| T | Testable |

### 2.2 Definition of Done (DoD) — Universal Quality Bar

Typical DoD checklist:
- Code reviewed and merged to main branch
- All tests (unit, integration, UI) pass
- Documentation updated (README, runbooks)
- Monitoring/alerting updated
- Feature deployed to staging
- All acceptance criteria met
- No known critical defects
- Peer review approved

---

## 3. Requirements Traceability Matrix (RTM)

### 3.1 RTM Fundamentals

**Reference**: [Requirements Traceability Matrix — Yuri Kan, Senior QA Lead](https://yrkan.com/blog/requirements-traceability-matrix/)  
**Reference**: [Traceability Matrix for Medical Devices — MedDeviceGuide](https://meddeviceguide.com/blog/traceability-matrix-medical-devices-guide/)

An RTM links requirements → test cases → defects with bidirectional coverage.

**Standard RTM Columns**:
| Field | Description |
|---|---|
| Requirement ID | Unique identifier (REQ-001) |
| Requirement Description | What the system should do |
| Requirement Type | Functional, Non-functional, Business Rule |
| Priority | Critical, High, Medium, Low |
| Source | User story, spec document, stakeholder |
| Test Case ID(s) | Linked test cases |
| Test Type | Unit, Integration, System, UAT |
| Test Status | Pass, Fail, Not Executed, Blocked |
| Defect ID(s) | Linked bugs |
| Test Evidence | Screenshots, logs, reports |
| Tested By | Tester name |
| Test Date | When tested |
| Signoff | Stakeholder approval |

**Traceability Types**:
- **Forward**: Requirements → Test Cases (ensures all reqs are tested)
- **Backward**: Test Cases → Requirements (ensures no orphan tests)
- **Bidirectional**: Both directions (gold standard for regulated industries)

### 3.2 Lightweight Agile RTM

| User Story | Acceptance Criteria | Test Scenario | Status |
|---|---|---|---|
| US-101: User Login | AC1: Valid credentials → Dashboard | TS-101-1: Happy path login | ✅ Pass |
| US-101: User Login | AC2: Invalid credentials → Error | TS-101-2: Invalid login | ✅ Pass |
| US-101: User Login | AC3: Lockout after 5 fails | TS-101-3: Account lockout | ❌ Fail |

### 3.3 RTM Best Practices

- Maintain throughout project, not one-time creation
- Use tools for automation (Jira + Zephyr/Xray, Azure DevOps, TestRail)
- Define clear naming conventions: `REQ-AUTH-001`, `TC-AUTH-FUNC-001`
- Review regularly — weekly/sprint cadence
- Include non-functional requirements (performance, security, usability)
- In regulated industries (FDA, ISO 26262, DO-178C), RTM is effectively mandatory

---

## 4. Phase Gates & Stage-Gate Models

### 4.1 Stage-Gate Fundamentals

**Reference**: [Stage-Gates for Execution: A Project Funnel Checklist — Accept Mission](https://www.acceptmission.com/blog/stage-gate-execution-checklist/)  
**Reference**: [Gate Reviews in Project Management — monday.com](https://monday.com/blog/project-management/gate-review/)  
**Reference**: [Stage Gate Model Template — Project Management Formula](https://projectmanagementformula.com/stage-gate-model-template/)

**Four possible gate outcomes**:
1. **Go** — proceed to next stage
2. **Recycle** — rework needed within current stage
3. **Kill** — terminate project
4. **Hold** — pause pending conditions

**Two-Layer Criteria Model**:
- **Entrance criteria**: conditions that must exist before the review begins
- **Success criteria**: standards the project must meet to earn a Go decision

### 4.2 COMPEL Framework Quality Gates

**Reference**: [COMPEL Stage Gate Readiness — COMPEL Framework](https://www.compelframework.org/articles/entry-and-exit-criteria-stage-gate-readiness)

Four named quality gates:
| Gate | Name | Purpose |
|---|---|---|
| Gate M | Design Approved | Designs feasible, ethical, risk-assessed, policy-aligned |
| Gate P | Build Complete | Built to spec, governance controls operational |
| Gate E | Validated and Approved | Meets acceptance thresholds for performance, fairness, usability |
| Gate L | Production Ready | Production stability, governance control efficacy |

**Failure Conditions Severity**:
- **Severity 1 — Stage Failure**: Stage cannot complete; returns to backlog
- **Severity 2 — Cycle Interruption**: Systemic issues halt entire cycle
- **Severity 3 — Scope Adjustment**: Affects specific deliverables but not entire stage

### 4.3 Five-Stage Gate Model

| Stage | Gate | Key Criteria |
|---|---|---|
| Scoping | Gate 1 | Strategic fit, market opportunity, technical feasibility |
| Business Case | Gate 2 | Full business case, financial projections, risk assessment |
| Development | Gate 3 | Sound business case, resourced team, mitigated risks |
| Testing/Validation | Gate 4 | Meets acceptance criteria, business case holds, org readiness |
| Launch | Gate 5 | Testing complete, training done, support in place, rollback documented |

---

## 5. Quality Gates in CI/CD & Deployment

### 5.1 Quality Gate Hierarchy

**Reference**: [CI/CD Deployment Gate Design — botneve.com](https://botneve.com/devops-practices/ci-cd-deployment-gate-design/)  
**Reference**: [Quality Gates — keptn](https://v1.keptn.sh/docs/concepts/quality_gates/)  
**Reference**: [Quality Gates in GitOps Delivery — The Axiom](https://elliot-digital.co.uk/cloud/gitops-quality-gates)

| Gate | Scope | Latency | Failure Action |
|---|---|---|---|
| Static analysis | Code quality | Seconds | Block PR merge |
| Unit tests | Function-level regressions | 30s–5m | Block merge |
| Integration tests | Multi-service interactions | 3–15m | Block deploy; retry-quarantine flakes |
| Contract tests | API compatibility | 2–5m | Block deploy |
| Smoke tests (post-deploy) | Deployment correctness | 30s–2m | Auto-rollback |
| Canary verification | Regression vs control traffic | 5–60m | Auto-rollback on SLO breach |
| SLO burn-rate | Error-budget consumption | Continuous | Auto-rollback on multi-window burn |

### 5.2 Gate Health Metrics

| Metric | Target |
|---|---|
| Gate pass rate | > 95% |
| Time to gate decision (CI) | < 5 minutes |
| Time to gate decision (runtime) | < 1 minute |
| False positive rate | < 2% for hard-blocks; < 10% for soft-blocks |
| Gate bypass frequency | < 1% (rising trend = gate decay) |
| Override frequency | < 1% |

### 5.3 Auto-Rollback Thresholds

| Signal | Threshold | Dwell Time |
|---|---|---|
| Smoke test immediate-fail | 1 failure | 0 (immediate) |
| Error rate spike | > 3σ from baseline OR > 1% absolute | 2–5 minutes |
| Latency p99 regression | > 2× baseline OR > fixed ceiling | 5–10 minutes |
| SLO burn-rate (fast) | 2% of 30-day budget in 1 hour | Continuous |
| SLO burn-rate (slow) | 10% of 30-day budget in 6 hours | Continuous |

### 5.4 GitOps Quality Gates

Two-plane model:
- **CI Gate** — Before Git merge (PR checks, branch protection)
- **GitOps Gate** — After Git merge, during sync (Argo hooks, OPA/Kyverno)

ArgoCD hook phases: `PreSync` → `Sync` → `PostSync` → `SyncFail`

---

## 6. SLO-Based Acceptance Gates

### 6.1 SLOs as NFR Acceptance Criteria

**Reference**: [SLOs and SLAs as QA Governance — The Axiom](https://elliot-digital.co.uk/qa/slo-sla-quality)

Non-functional requirements should be expressed as SLO compliance:
- **Before** (vague): "The checkout API must be fast."
- **After** (SLO-derived): "The checkout API must maintain p99 latency SLI of >= 95% (requests completing in < 800ms) under 500 concurrent users for 30 minutes."

### 6.2 Error Budget Policy as Release Gate

| Budget State | Action |
|---|---|
| Budget consumed > 50% with > 50% window remaining | Amber — releases require explicit sign-off |
| Budget consumed > 75% with > 25% window remaining | Red — releases blocked, only hotfixes |
| Budget fully exhausted | Freeze — no changes except incident remediation |

### 6.3 SLO Review Cadence

1. Budget consumption report (5 min)
2. SLI trend review (10 min)
3. Incident retrospective link (10 min)
4. Target relevance check (10 min)
5. Threshold adjustment proposals (10 min)

---

## 7. Safety, Security & Data Acceptance Criteria (AI/Agent-Specific)

### 7.1 Open Agent Behavioral Governance Specification (ABGS)

**Reference**: [OpenA2A Agent Governance Spec — GitHub](https://github.com/opena2a-org/agent-governance-spec)

Nine behavioral governance domains with 30 controls:

| Domain | Controls | What It Governs |
|---|---|---|
| Trust Hierarchy | 3 | Who the agent trusts, priority order, conflict resolution |
| Capability Boundaries | 4 | Allowed/denied actions, scope, least privilege |
| Injection Hardening | 3 | Prompt injection defense, encoded payloads, role-play refusal |
| Data Handling | 3 | PII protection, credential handling, data minimization |
| Hardcoded Behaviors | 3 | Immutable safety rules, exfiltration prevention, kill switch |
| Agentic Safety | 4 | Iteration limits, budget caps, timeouts, reversibility |
| Honesty and Transparency | 3 | Uncertainty acknowledgment, factual accuracy, identity disclosure |
| Human Oversight | 3 | Approval gates, override mechanisms, monitoring |
| Harm Avoidance | 4 | Pre-action risk assessment, proportional response |

**Conformance Levels**:
| Level | Requirement | Typical Use Case |
|---|---|---|
| Essential | All CRITICAL controls pass | Minimum viable governance |
| Standard | All CRITICAL+HIGH pass, score >= 60 | Production agents with user data |
| Hardened | All controls pass, score >= 75 | Autonomous agents, regulated envs |

### 7.2 Agentic AI Security Scoping Matrix

**Reference**: [Agentic AI Security Scoping Matrix — AWS Security Blog](https://aws.amazon.com/blogs/security/the-agentic-ai-security-scoping-matrix-a-framework-for-securing-autonomous-ai-systems/)

| Scope | Agency Level | Security Focus |
|---|---|---|
| Scope 1: Workflow | No state change | Data integrity, boundary enforcement |
| Scope 2: Human-in-loop | Limited, explicit approval | Approval workflows, privilege escalation prevention |
| Scope 3: Supervised agency | Autonomous with bounds | Behavioral monitoring, scope management, auditability |
| Scope 4: Full agency | Full autonomous | Continuous validation, capability drift prevention |

### 7.3 Policy-Gated Agent Action

**Reference**: [Policy-Gated Agent Action (KRITIS) — Agent Patterns Catalog](https://www.agentpatternscatalog.org/patterns/policy-gated-agent-action/)

Pattern: Evaluate every proposed agent action against machine-readable policies before dispatch.
- WORM (Write-Once-Read-Many) store for every action decision
- Record includes: Run ID, Model Digest, Policy Hash, Inputs Hash, Decision
- Enables provable per-action policy compliance and incident reconstruction

### 7.4 Agentic Workflow Approval Gates

**Reference**: [Agentic Workflow Approval Gates — Digital Applied](https://www.digitalapplied.com/blog/agentic-workflow-approval-gate-framework-governance)

Four gate types for agent workflows:
| Gate Type | Behavior | Use Case |
|---|---|---|
| Advisory | Logged, no block | Low-stakes, audit visibility only |
| Validating | Signed off, allows continuation | Medium-stakes, reversible actions |
| Blocking | Must pass, halts on fail | Irreversible, high-stakes actions |
| Escalating | Routes to higher authority | Low confidence, novel patterns |

**Audit Trail Schema** (9 fields per gate event):
- Workflow ID, Gate ID, Timestamp (UTC, ISO-8601)
- Reviewer ID, Decision (approve/reject/escalate/defer), Comment
- Agent state diff at gate (critical — makes trail actionable)
- Escalation SLA: 15 min (real-time), 4 hrs (batch), 24 hrs (complex review)

### 7.5 Secure Agentic AI Frameworks

**Reference**: [Secure Agentic AI Frameworks — Open Security Architecture](https://www.opensecurityarchitecture.org/patterns/sp-047)

Seven control areas:
1. **Agent isolation** — where agents run and how they are isolated
2. **Tool governance** — which tools agents may use
3. **Guardrails** — prevent agents from causing harm (NIST SP 800-53 mappings: SI-10, AC-04, CM-02, SC-07)
4. **Data flow** — RAG pipeline security, data classification
5. **Multi-agent communication** — inter-agent security
6. **Cost bounding** — autonomy and financial limits
7. **Incident response** — kill switches, failure containment

**Three Governance Principles**:
1. Business owners — not developers — decide autonomy tiers
2. Security validation requires ongoing monitoring, not pass/fail tests
3. Ungoverned agents = new shadow IT

---

## 8. Evidence-Based Acceptance & Auditability

### 8.1 Evidence Log Template

**Reference**: [SDD Evidence Log Template — Spec Coding](https://spec-coding.dev/templates/sdd-evidence-log)

**Acceptance Evidence Table**:
| Criterion | Evidence | Link | Result |
|---|---|---|---|
| AC-1 | Test | `<link>` | Pass/Fail |
| AC-2 | Screenshot | `<link>` | Pass/Fail |

**Operational Evidence**:
- Log query: `...`
- Metric: `...`
- Alert: `...`
- Stop signal: `...`

**Evidence Bar** (minimum to high-risk):
- Minimum: at least one automated test or contract fixture
- Higher-risk: add screenshots, log queries, metrics, rollback signals
- Follow-up: give known gaps an owner and review date

### 8.2 OWASP APTS Auditability Requirements

**Reference**: [OWASP APTS Standard — Auditability](https://owasp.org/APTS/standard/5_Auditability/)

20 MUST requirements organized in groups:
| Group | Requirements | Purpose |
|---|---|---|
| Logging fundamentals | 5 | Structured event capture, phase transitions, retention |
| Decision transparency | 4 | Confidence-scored logs, reasoning chains, risk assessment |
| Evidence integrity | 5 | Hashing, custody, timestamps, screenshots, classification |
| Tamper evidence | 1 | Hash-chained append-only logs |
| Platform integrity | 4 | SBOM, regression testing, model change tracking |
| Audit trail isolation | 1 | Records unreachable from agent runtime |

**Critical Rule**: The agent runtime MUST NOT have permission to write, modify, or delete entries in the authoritative audit trail. Audit records MUST be written to a store the agent cannot reach.

### 8.3 Async Quality Gates for AI Agent Workflows

**Reference**: [Async Quality Gates for AI Agent Workflows — Vincent van Deth](https://vincentvandeth.nl/blog/async-quality-gates-ai-agent-workflows)

Five-gate progression:
1. **Planning Gate** — T0 decides dispatch is well-defined
2. **Implementation Gate** — T1 completes work; quality sidecar generated
3. **Review Gate** — T3 performs code review
4. **Testing Gate** — T2 runs integration tests
5. **Validation Gate** — All open items closed; T0 final approval

**Quality Sidecar Pattern**: Each completed dispatch generates JSON metadata with findings (not judgments). The receipt processor decides: `approve` / `approve_with_followup` / `hold`.

### 8.4 Audit-Trail-by-Construction (Trail Framework)

**Reference**: [Audit-trail-by-construction — DEV Community](https://dev.to/masroor_ahmad_68f272bb2ce/audit-trail-by-construction-a-thesis-for-spec-driven-ai-coding-413j)

Key principles:
- **Description-once**: Requirement written once, never edited; refinements as comments
- **Stable per-criterion IDs**: `SC-N` (success criteria), `AC-N.M` (acceptance criteria), `EC-N.M.x` (edge cases), `NFR-N` (non-functional reqs)
- **Per-role identity**: Each agent persona has own ticket-system account
- **ID threading**: IDs trace from BA intent → architect slices → implementor test code
- **Discipline-first, velocity-second**: For regulated/security-critical code

---

## 9. QA Checklists & Release Readiness

### 9.1 Release Validation Gate Checklist

**Reference**: [Release Validation Gate Checklist — bytes.engineer](https://bytes.engineer/blog/release-validation-gate-checklist/)

Per-row structure: Gate name, Status (pass/watch/fail), Owner, Blocking (yes/no), Evidence (exists/missing)

**Common failure modes**:
- Status inflation (marking pass when almost complete)
- Evidence decay (passing based on verbal update)
- Ownership gap (gate exists but no accountable person)

### 9.2 QA Signoff Template

**Reference**: [QA Signoff Template — IdeaPlan](https://www.ideaplan.io/templates/qa-signoff-template)

**Minimum approvers**: QA lead, engineering lead, PM (+ security for security changes, compliance for regulated releases)

**Gate enforcement**: QA signoff is a quality gate, not a suggestion. Override requires documented PM acceptance of risk.

### 9.3 Release Readiness Checklist

**Reference**: [Release Readiness Checker — aqua-cloud](https://aqua-cloud.io/release-readiness-checklist/)

Five coverage areas:
1. **Code** — branch locked, PRs merged, version numbers updated
2. **Testing** — suite passing, regression complete, performance met, known issues documented
3. **Infrastructure** — migrations tested, rollback verified, monitoring active
4. **Docs** — release notes, support briefed, customer docs updated
5. **Security** — scan completed, compliance met

### 9.4 QRD Template (Quality Requirements Document)

**Reference**: [QRD Template — thehuman2ai.com](https://thehuman2ai.com/product/templates/qrd)

**Blocking Criteria** (must pass before release):
| ID | Criterion | Threshold | Verified By |
|---|---|---|---|
| AC-001 | P0 tests pass | 100% pass | CI pipeline |
| AC-002 | No P0/P1 bugs | 0 open | Bug tracker |
| AC-003 | Performance targets met | All QA-PERF pass | Load test report |
| AC-004 | Security scan clean | 0 critical/high CVEs | Scan report |
| AC-005 | Accessibility audit | WCAG 2.2 AA | Audit report |
| AC-006 | Data migration verified | 100% data integrity | Migration test |
| AC-007 | Rollback tested | Successful within X min | Rollback drill |

**Advisory Criteria** (tracked, not blocking):
Coverage, documentation, localization reviewed.

---

## 10. Regulatory & Compliance Standards (ISO 13485, IEC 62304, FDA)

### 10.1 IEC 62304 — Software Lifecycle for Medical Devices

**Reference**: [IEC 62304 Software Verification and Validation — MDRegulatory](https://mdregulatory.com/iec-62304-software-verification/)  
**Reference**: [IEC 62304 Software Lifecycle — Kelsey Quality](https://kelseyqms.com/guides/iec-62304-software-lifecycle)

**Traceability by Safety Class**:
| Class | Traceability Required |
|---|---|
| Class A | SRS → System Tests |
| Class B | SRS → Architecture → Integration Tests → System Tests |
| Class C | Full bidirectional: SRS ↔ Architecture ↔ Detailed Design ↔ Unit Tests ↔ Integration Tests ↔ System Tests + Risk Controls |

**Key Requirements**:
- Each software requirement must have a unique ID for bidirectional traceability
- Risk control measures must appear as explicit software requirements
- Class C requires defined acceptance criteria for unit verification
- System testing must verify risk control measures

### 10.2 ISO 13485 — Quality Management for Medical Devices

**Reference**: [ISO 13485 in Software Development — Revolve Healthcare](https://revolve.healthcare/blog/iso-13485-software-development/)  
**Reference**: [ISO 13485 and IEC 62304 Integration — I3C Global](https://www.i3cglobal.com/iso-13485-and-iec-62304-integration/)

Mandates:
- Verification plans with methods, acceptance criteria, statistical techniques
- Validation plans with methods, acceptance criteria
- Traceability procedures defining extent of traceability per regulatory requirements
- Software validation before initial use and after changes
- Design transfer, verification, validation activities documented

### 10.3 FDA Software Validation Guidance

**Reference**: [Content of Premarket Submissions for Device Software Functions — FDA](https://www.fda.gov/media/153781/download)

Elements acceptable for software validation:
- Planning, requirements, risk assessment, design reviews
- Traceability, change management, testing plans and results
- Source code traceability analysis verifying:
  - Each design element implemented in code
  - Modules traceable back to design spec and risk analysis
  - Tests traceable back to design spec and risk analysis

---

## 11. AI Agent-Specific Evaluation Libraries

### 11.1 Microsoft AI Agent Eval Scenario Library

**Reference**: [Microsoft AI Agent Eval Scenario Library — GitHub](https://github.com/microsoft/ai-agent-eval-scenario-library)

Two categories:
- **Business-problem scenarios**: What the agent does for users (Q&A, troubleshooting, triage)
- **Capability scenarios**: How the agent's architecture behaves (tool invocations, grounding, routing, compliance)

**Evaluation patterns covered**:
- Information Retrieval & Q&A
- Troubleshooting & Guided Diagnosis
- Request Submission & Task Execution
- Process Navigation & Multi-Step Guidance
- Knowledge Grounding & Accuracy
- Tool & Connector Invocations
- Compliance & Verbatim Content
- Safety & Boundary Enforcement
- Graceful Failure & Escalation
- Red-Teaming & Adversarial Evaluation

### 11.2 Agent Patterns Catalog

**Reference**: [Agent Patterns Catalog — GitHub](https://github.com/agentpatternscatalog/patterns)  
**Reference**: [Agent Patterns Catalog (rendered)](https://www.agentpatternscatalog.org/patterns/policy-gated-agent-action/)

Relevant patterns for acceptance criteria:
- **Policy-Gated Agent Action**: Every proposed action evaluated against policies before dispatch
- **Decision Log**: Persist reasoning trace alongside actions
- **Provenance Ledger**: Log every decision and state change
- **Approval Queue**: Queue proposed actions for async human review
- **Supervisor-Plus-Gate**: Validate/gate LLM outputs against deterministic checks
- **Pipeline Triad Pattern**: Creator → Critic → Arbiter with human gates between stages

### 11.3 Agentic AI Readiness Model

**Reference**: [Agentic AI Readiness — GitHub (rogelsjcorral)](https://github.com/rogelsjcorral/agentic-ai-readiness)

Operational readiness model with:
- Autonomy budgets
- Readiness gates by capability tier
- Enforceable control patterns
- Audit events and anomaly signals
- Rollout ladder with phased deployment

---

## 12. Synthesis: Patterns Relevant to Guinevere

### 12.1 Directly Applicable Patterns

| Pattern | Guinevere Application |
|---|---|
| **Given/When/Then (BDD)** | Structuring acceptance criteria for agent loop phases, memory operations, API integrations |
| **Requirements Traceability Matrix (RTM)** | Tracing BRD/PRD requirements → architecture → tests → evidence |
| **Definition of Ready** | Preconditions before agent loop phases execute (input validation, context completeness) |
| **Definition of Done** | Universal quality bar for all agent outputs (evidence attached, audit logged, tests passed) |
| **Phase Gates (COMPEL)** | Agent loop phase transitions with entry/exit criteria |
| **SLO-Based Acceptance** | Per-agent SLOs for latency, reliability, accuracy as release gates |
| **Quality Gate Hierarchy** | Static → Unit → Integration → Smoke → Canary → SLO gates in CI/CD |
| **ABGS (Agent Governance)** | Behavioral domains: trust, capability, data, safety, oversight, harm avoidance |
| **Policy-Gated Action** | Every agent action validated against policies before execution |
| **Evidence Log** | Each acceptance criterion proven by test, screenshot, log, or metric |
| **Audit Trail Isolation** | Agent cannot modify its own audit trail (append-only, separate store) |
| **Stable Criterion IDs** | `SC-N`, `AC-N`, `EC-N` threading through design, code, tests |
| **Async Quality Gates** | Quality sidecar per dispatch; automated findings + human sign-off |
| **Approval Gates (Advisory/Validating/Blocking/Escalating)** | Gate types for different agent action risk levels |

### 12.2 Guinevere-Specific Adaptations

1. **Agent Loop Phase Gates**: Each of Guinevere's 7 (or 8) SDLC phases should have formal entry criteria and exit criteria with evidence requirements.

2. **Memory Operation Acceptance**: Memory writes/reads should have acceptance criteria for accuracy, consent verification, encryption, and audit logging.

3. **Persona Safety Gates**: Personality state transitions (including mood/yandere states) must pass safety acceptance criteria before executing persona-driven actions.

4. **Surveillance Consent Gates**: Any surveillance data collection must pass consent verification acceptance criteria before data is stored or processed.

5. **Multi-Agent Orchestration Gates**: Sub-agent dispatches require gate validation: planning gate → implementation gate → review gate → testing gate → validation gate.

6. **Autonomy Budget Acceptance**: Per-tier autonomy budgets with explicit acceptance criteria for when human approval is required.

7. **Evidence-Based Closure**: No agent task is "done" until:
   - All acceptance criteria have passing evidence
   - Audit trail is complete and agent-inaccessible
   - Quality sidecar findings have been reviewed
   - T0 (human operator) has explicitly signed off

### 12.3 Recommended Acceptance Criteria Catalog Structure

Based on the synthesis, an enterprise catalog for Guinevere should organize criteria into:

| Category | Scope | Examples |
|---|---|---|
| **Functional AC** | Feature/behavior specific | Gherkin scenarios for each feature |
| **Non-Functional AC** | Performance, security, usability | SLO thresholds, response times, uptime |
| **Safety AC** | Persona, consent, harm avoidance | No PII leakage, safe word enforcement |
| **Security AC** | Access control, injection, data | Prompt injection resistance, least privilege |
| **Governance AC** | Audit, traceability, compliance | Append-only audit, criterion IDs stable |
| **Operational AC** | Deployment, monitoring, SLO | Rollback tested, error budget policy |
| **Phase Gate AC** | Loop phase transitions | Entry/exit criteria per SDLC phase |

---

## 13. Sources & References

### Core Acceptance Criteria
1. BDD Gherkin at Scale — https://skills.visual-paradigm.com/docs/user-story-techniques-large-scale-agile/advanced-enterprise-story-patterns/bdd-gherkin-user-stories-acceptance-criteria/
2. Acceptance Criteria Hub (Spec Coding) — https://spec-coding.dev/acceptance-criteria
3. Atlassian Acceptance Criteria Guide — https://wac-cdn.atlassian.com/work-management/project-management/acceptance-criteria
4. Scrum Alliance: Definition of Ready vs Done — https://resources.scrumalliance.org/Article/definition-vs-ready
5. Scrum Alliance: Acceptance Criteria — https://resources.scrumalliance.org/Article/need-know-acceptance-criteria

### Requirements Traceability
6. RTM Guide (Yuri Kan) — https://yrkan.com/blog/requirements-traceability-matrix/
7. User Story Testing Docs (Yuri Kan) — https://yrkan.com/blog/user-story-testing-docs/
8. Medical Device Traceability Matrix — https://meddeviceguide.com/blog/traceability-matrix-medical-devices-guide/
9. RTM Why Excel Is Not Enough — https://www.kualitee.com/blog/test-management/requirements-traceability-matrix-death-by-excel-or-a-useful-tool/
10. IREB Requirements Management Handbook — https://cockpit.ireb.org/media/pages/downloads/cpre-requirements-management-handbook/bb31fbe9d6-1733311674/ireb-cpre-handbook-for-requirements-management-en-v2.1.pdf

### Definition of Ready/Done
11. Scrum.org DoR vs AC — https://www.scrum.org/forum/scrum-forum/86190/whats-difference-between-definition-doneready-acceptance-criteria-feature
12. Agile Seekers: Ready/Done in Technical Stories — https://agileseekers.com/blog/defining-and-using-ready-and-done-criteria-in-technical-stories
13. AltexSoft: AC vs DoD — https://www.altexsoft.com/blog/acceptance-criteria-definition-of-done/
14. Nulab: DoD vs AC — https://nulab.com/learn/software-development/definition-of-done-vs-acceptance-criteria/
15. Simpliaxis: DoR vs AC — https://www.simpliaxis.com/resources/definition-of-ready-vs-acceptance-criteria

### Stage-Gate Models
16. COMPEL Framework Stage Gates — https://www.compelframework.org/articles/entry-and-exit-criteria-stage-gate-readiness
17. Accept Mission: Stage-Gate Checklist — https://www.acceptmission.com/blog/stage-gate-execution-checklist/
18. monday.com: Gate Reviews — https://monday.com/blog/project-management/gate-review/
19. Project Management Formula: Stage Gate Template — https://projectmanagementformula.com/stage-gate-model-template/

### CI/CD Quality Gates
20. CI/CD Deployment Gate Design — https://botneve.com/devops-practices/ci-cd-deployment-gate-design/
21. keptn Quality Gates — https://v1.keptn.sh/docs/concepts/quality_gates/
22. Quality Gates Guide (NoOps) — https://noopsschool.com/blog/quality-gates/
23. GitOps Quality Gates (The Axiom) — https://elliot-digital.co.uk/cloud/gitops-quality-gates

### SLO-Based Acceptance
24. SLOs and SLAs as QA Governance — https://elliot-digital.co.uk/qa/slo-sla-quality
25. CDE-Centered Quality Gate Framework (ISO 19650) — https://www.mdpi.com/2076-3417/16/5/2562

### AI Agent Governance & Safety
26. OpenA2A ABGS Spec — https://github.com/opena2a-org/agent-governance-spec
27. AWS Agentic AI Security Scoping Matrix — https://aws.amazon.com/blogs/security/the-agentic-ai-security-scoping-matrix-a-framework-for-securing-autonomous-ai-systems/
28. AWS Prescriptive Guidance: Security for Agentic AI — https://docs.aws.amazon.com/pdfs/prescriptive-guidance/latest/agentic-ai-security/agentic-ai-security.pdf
29. Open Security Architecture: Secure Agentic AI Frameworks — https://www.opensecurityarchitecture.org/patterns/sp-047
30. NIST Agentic AI Governance (CSA) — https://labs.cloudsecurityalliance.org/wp-content/uploads/2026/03/governance-nist-ai-agent-standards-agentic-governance-v1-csa-styled.pdf
31. Microsoft Learn: Governance and Security for AI Agents — https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ai-agents/governance-security-across-organization
32. Controlled Agentic AI Systems (CAIS) — https://www.mdpi.com/2504-4990/8/5/125

### AI Agent Patterns
33. Agent Patterns Catalog — https://github.com/agentpatternscatalog/patterns
34. Policy-Gated Agent Action Pattern — https://www.agentpatternscatalog.org/patterns/policy-gated-agent-action/
35. Agentic AI Readiness (rogelsjcorral) — https://github.com/rogelsjcorral/agentic-ai-readiness

### Agent Evaluation Libraries
36. Microsoft AI Agent Eval Scenario Library — https://github.com/microsoft/ai-agent-eval-scenario-library

### Audit & Evidence
37. OWASP APTS Auditability — https://owasp.org/APTS/standard/5_Auditability/
38. SDD Evidence Log Template (Spec Coding) — https://spec-coding.dev/templates/sdd-evidence-log
39. Async Quality Gates for AI Agent Workflows — https://vincentvandeth.nl/blog/async-quality-gates-ai-agent-workflows
40. Audit-trail-by-construction (Trail Framework) — https://dev.to/masroor_ahmad_68f272bb2ce/audit-trail-by-construction-a-thesis-for-spec-driven-ai-coding-413j

### Agentic Workflow Approval Gates
41. Agentic Workflow Approval Gates — https://www.digitalapplied.com/blog/agentic-workflow-approval-gate-framework-governance

### QA Checklists & Release Readiness
42. Release Validation Gate Checklist — https://bytes.engineer/blog/release-validation-gate-checklist/
43. QA Signoff Template — https://www.ideaplan.io/templates/qa-signoff-template
44. Release Readiness Checker — https://aqua-cloud.io/release-readiness-checklist/
45. QRD Template — https://thehuman2ai.com/product/templates/qrd

### Regulatory Standards
46. IEC 62304 Verification and Validation — https://mdregulatory.com/iec-62304-software-verification/
47. IEC 62304 Software Lifecycle (Kelsey) — https://kelseyqms.com/guides/iec-62304-software-lifecycle
48. ISO 13485 in Software Development — https://revolve.healthcare/blog/iso-13485-software-development/
49. ISO 13485 and IEC 62304 Integration — https://www.i3cglobal.com/iso-13485-and-iec-62304-integration/
50. FDA Software Premarket Submissions — https://www.fda.gov/media/153781/download
51. FDA General Principles of Software Validation — https://www.fda.gov/media/73141/download
52. Software Validation Procedure (SYS-044) — https://medicaldeviceacademy.com/software-validation-procedure/

### SoPaMM Metamodel
53. Aligning Requirements and Testing Through Metamodeling — https://link.springer.com/content/pdf/10.1007/s00766-022-00377-5.pdf

### Use Case-Based Acceptance
54. Catalio: Defining Acceptance Criteria with Use Cases — https://catalio.ai/docs/use-cases

---

*Report generated by Guinevere (Librarian agent) on 2026-05-30. This report is external research only; it does not modify source docs or generate a final catalog.*
