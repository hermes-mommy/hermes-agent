# Incident Response & Postmortem External References
## Research Report for Project Guinevere

**Date**: 2026-05-30  
**Prepared by**: Guinevere Research Agent  
**Classification**: Internal — Engineering Governance  
**Evidence path convention**: `evidence/incidents/<YYYY-MM-DD>-<SEV>-<slug>/`

---

## 1. Executive Summary

This report synthesizes authoritative incident response, postmortem, evidence preservation, security incident handling, tabletop drill, cost anomaly, AI safety, and secret-compromise patterns from NIST, Google SRE, OWASP, CIS, FinOps Foundation, OpenTelemetry, and cloud-vendor guidance. Each section translates external standards into concrete requirements for Project Guinevere’s single-user private AI agent context.

**Authoritative sources consulted**:
- NIST SP 800-61r3 (Incident Response as CSF 2.0 Community Profile)
- NIST SP 800-61r2 (Computer Security Incident Handling Guide)
- NIST IR 8387 (Digital Evidence Preservation)
- Google SRE Incident Management Guide / Postmortem Culture / Anatomy of an Incident
- OWASP SAMM Incident Management (Streams A & B)
- CIS Controls v8.1 — Control 17 (Incident Response Management), Control 11 (Data Recovery), Control 13 (Network Monitoring)
- Atlassian Incident Management Handbook (Blameless Postmortem)
- ISO/IEC 27037 (Digital Evidence Identification, Collection, Acquisition, Preservation)
- SWGDE Best Practices for Digital Evidence Collection / Computer Forensic Examinations
- OSAC 2024-N-0011 (Standard Guide for Forensic Digital Image Management)
- FinOps Foundation Anomaly Management Capability
- OpenTelemetry incident timeline reconstruction and trace-correlation guidance
- GenAI-IRF (Practical Incident-Response Framework for Generative AI Systems)
- AIR (Agent Incident Response for LLM Agent Systems)
- LLM Incident Response Playbook 2026 (FutureAGI)
- AI Incident Response for Agentic AI Misbehavior (Promptly Cloud)
- AWS / Google Cloud / HashiCorp secret-compromise runbook patterns
- 0xelitesystem/secrets-leak-response-runbook (GitHub)

---

## 2. Incident Severity Classification

### 2.1 NIST Prioritization Factors

NIST SP 800-61r3 identifies three dimensions for incident prioritization:

| Dimension | Definition |
|---|---|
| **Functional impact** | Current and likely future negative impact to business functions |
| **Information impact** | Effect on confidentiality, integrity, and availability of information |
| **Recoverability** | Time and types of resources required to recover |

**Guinevere translation**:
- **SEV-1 (Critical)**: Safety boundary breach, PII leak, secret/key compromise, regulatory exposure, agent acts outside action envelope, or complete service unavailability. Contain before RCA.
- **SEV-2 (High)**: Quality regression with no safety impact, hallucination drift on non-regulated routes, backup failure with RPO risk. RCA first, then rollback.
- **SEV-3 (Medium)**: Single-tenant edge case, observability gap, non-critical misconfiguration. Defer; add to golden set or fix in next sprint.
- **SEV-4 (Low)**: Near-miss, pre-incident anomaly, tabletop finding. Log and track; no emergency response.

### 2.2 AI-Specific Severity Rubric

FutureAGI’s LLM Incident Response Playbook (2026) defines severity by failure class:

| Failure Class | Default Severity | Escalation Trigger |
|---|---|---|
| Hallucination (factual_grounding < 3) | S2 | Regulated route (medical, financial, legal) → S1 |
| Jailbreak (instruction_adherence / privacy_and_safety breach) | S2 | Regulated category breached → S1 |
| Drift (rolling-mean rubric drop) | S2 | Drop magnitude + user count threshold → S1 |
| PII leak (privacy_and_safety = 1-2) | **S1 always** | Regulatory exposure (SOC 2, HIPAA, GDPR) starts at ship time |

**Guinevere rule**: Any incident where agent output contains unredacted PII, secrets, or jailbroken content escalates immediately to SEV-1 regardless of blast radius.

---

## 3. Incident Commander Model (ICS / IMAG)

### 3.1 Google IMAG Roles

Google’s Incident Management at Google (IMAG) adapts the Incident Command System (ICS) with three core roles:

| Role | Responsibility |
|---|---|
| **Incident Commander (IC)** | Coordinates overall response; holds high-level state; assigns roles by knowledge/context (not reporting chain); removes roadblocks; maintains living incident document |
| **Communications Lead (CL)** | Issues periodic updates to stakeholders; acts as point of contact for incoming communications; allows IC and OL to focus on mitigation |
| **Operations Lead (OL)** | Mitigates the issue, minimizes user impact, resolves the problem; **only group modifying the system during incident** |

### 3.2 Key ICS Principles for Guinevere

1. **Role-based on knowledge, not hierarchy**: The IC assigns roles based on who has the relevant context, not who is senior.
2. **Single incident document**: Maintain a living document (markdown file in `evidence/incidents/<slug>/`) editable by multiple responders.
3. **Explicit handoff**: If command is handed off, the outgoing IC must state: *"You’re now the incident commander, okay?"* and wait for explicit acknowledgment.
4. **Three Cs**: Coordinate, Communicate, Control.

**Guinevere implementation**:
- IC = Operator (Faiz) or delegated sub-agent with explicit handoff protocol
- CL = Agent responsible for stakeholder notifications (legal/compliance if external)
- OL = Agent or sub-agent executing containment/recovery with audit-logging enabled
- If operator is unavailable, a pre-authorized fallback (secondary account or designated human) assumes IC role

---

## 4. Incident Lifecycle

### 4.1 NIST SP 800-61r3 Phases (CSF 2.0 Mapping)

NIST SP 800-61r3 replaces the old four-phase cycle with CSF 2.0 Functions:

| CSF 2.0 Function | IR Phase | Key Activities |
|---|---|---|
| **Govern (GV)** | Policy, oversight, strategy | Management commitment, scope definition, authority delegation |
| **Identify (ID)** | Preparation | Risk assessment, control selection, team training, tooling |
| **Protect (PR)** | Prevention | Safeguards to reduce incident likelihood |
| **Detect (DE)** | Detection & Analysis | Monitoring, triage, severity assignment, notification triggers |
| **Respond (RS)** | Containment, Eradication, & Recovery | Contain strategy, evidence gathering, eradication, staged recovery |
| **Recover (RC)** | Recovery + Post-Incident Activity | Restore assets, validate integrity, lessons learned, evidence retention |

**Guinevere lifecycle**:
1. **Preparedness** (ongoing): Runbooks current, tabletop quarterly, backup restoration tested quarterly, secret rotation rehearsed annually.
2. **Detection** (automated + manual): Alert from monitoring, user report, or external notification.
3. **Triage & Declaration**: IC assigns SEV, activates runbook, declares incident in `evidence/incidents/`.
4. **Containment**: Disable agent tool access, revoke tokens, pause workflows, isolate service accounts.
5. **Eradication**: Remove root cause (patch, rotate, rebuild, re-index).
6. **Recovery**: Staged restoration; validate integrity before declaring restored.
7. **Post-Incident Activity**: Postmortem within 48 hours, action items with owners/due dates, evidence retention per policy.

### 4.2 Containment Sequencing (NIST 800-61r2 guidance)

NIST groups containment, eradication, and recovery because they are interdependent, but mandates **sequential execution**:

1. **Short-term containment**: Immediate actions to stop spread (isolate host, disable agent, revoke credential).
2. **Long-term containment**: Sustainable measures allowing continued operation while threat is eradicated (network segmentation, credential restrictions, reduced tool envelope).
3. **Eradication**: Remove malware/persistence/prompt-injection vectors; confirm all access vectors and persistence mechanisms remediated.
4. **Recovery**: Staged restoration in priority order; verify each restored component before proceeding; heightened monitoring for ≥30 days post-recovery.

**Guinevere rule**: Never declare recovery until eradication is documented and validated. Heightened monitoring continues for 30 days.

---

## 5. Evidence Preservation and Chain of Custody

### 5.1 Digital Evidence Standards

**NIST IR 8387** and **ISO/IEC 27037** establish:
- Hash evidence using NIST-approved algorithms (SHA-256 preferred) as close to collection as possible.
- Store hashes separately from evidence in a secure, immutable location.
- Document original source, creation method, and all transfers.
- Do not conduct direct examination on original evidence; use forensic images with write blockers.
- Retain digital evidence for at least 5 years after case adjudication (or per regulatory requirement).

**SWGDE Best Practices**:
- Contemporaneous notes: tools used, hash values, software versions, screenshots.
- Chain of custody documentation created upon collection and maintained throughout case life.
- Access logs for all evidence interactions.

### 5.2 Guinevere Evidence Path Specification

**Mandatory path**: `evidence/incidents/<YYYY-MM-DD>-<SEV>-<slug>/`

| Artifact | Description |
|---|---|
| `timeline.md` | Chronological incident timeline with timestamps, decisions, and actions |
| `evidence-hashes.sha256` | SHA-256 hashes of all collected artifacts, stored separately |
| `chain-of-custody.log` | Every transfer, access, or modification of evidence |
| `incident-report.md` | Full incident report (postmortem) |
| `artifacts/` | Screenshots, logs, config snapshots, trace exports |
| `action-items.md` | Remediation actions with owners and due dates |
| `communications/` | Stakeholder notification records |

**Hash chain requirement**: Append SHA-256 of each new artifact to `evidence-hashes.sha256` immediately upon creation. This creates an append-only integrity log.

---

## 6. Security Incident Response

### 6.1 OWASP SAMM Incident Management

OWASP SAMM defines two maturity streams:

| Stream | Maturity 1 | Maturity 2 | Maturity 3 |
|---|---|---|---|
| **A: Detection** | Best-effort detection | Established process with automated log evaluation | Proactively managed process |
| **B: Response** | Identify roles/responsibilities | Formal process, trained staff | Dedicated, continuously-improving team |

**Key requirements** (OWASP SAMM):
- Document common incident scenarios and high-level handling instructions.
- Triage rules for each incident.
- Stakeholder involvement rules (legal, PR, privacy, HR, law enforcement, customers) with mandatory timeframes.
- Root cause analysis (RCA) process and documentation.
- Trained team available 24/7 with up-to-date tools.

### 6.2 CIS Control 17 Safeguards

| Safeguard | Requirement |
|---|---|
| **17.1** | Designate personnel to manage incident handling (primary + backup). Review annually. |
| **17.2** | Maintain contact information for reporting security incidents (internal, vendors, law enforcement, insurers, ISACs). Verify annually. |
| **17.3** | Document enterprise process for workforce to report incidents: timeframe, personnel, mechanism, minimum info required. Available to all workforce. |
| **17.4** | Documented incident response process covering: roles/responsibilities, compliance requirements, communication plan. Review annually. |
| **17.5** | Key roles include: legal, IT, info sec, facilities, PR, HR, incident responders, analysts, third parties. |
| **17.6** | Primary and secondary communication mechanisms defined (phone, secure chat, email — noting email may fail during incident). |
| **17.7** | Routine IR exercises at least annually; test communication, decision-making, workflows. |
| **17.8** | Post-incident reviews identifying lessons learned and follow-up actions. |
| **17.9** | Security incident thresholds differentiating incidents from events, with prioritization schema, status update frequency, and escalation paths. |

### 6.3 Virtual Patching (OWASP)

When a vulnerability is identified during incident response:
1. **Preparation**: Pre-authorize virtual patches; sign up for vendor alerts.
2. **Identification**: Proactive (code review, pentest) or reactive (live incident).
3. **Analysis**: Determine applicability, verify CVE, designate impact level, list affected versions.
4. **Creation**: No false positives; no false negatives; positive security model preferred where feasible.
5. **Implementation/Testing**: Log-only mode first; retest; track in ticket system.
6. **Recovery/Follow Up**: Periodic re-assessment to remove virtual patch when source fix ships.

---

## 7. Postmortems and Blameless Root Cause Analysis

### 7.1 Google SRE Postmortem Culture

**Core principles** (Google SRE Workbook):
- Postmortems are letters to future team members.
- Write them while experience is fresh (within 2 weeks of resolution).
- Share as widely as possible — default to company-wide accessibility.
- Focus on gaps in system design that permitted failure modes.
- Incentivize both writing and closing action items.

**Postmortem checklist** (Google SRE):
- Complete assessment of incident impact.
- Detailed root-cause analysis driving action item planning.
- Action items vetted and approved by technical leads.
- Postmortem shared with wider organization.

### 7.2 Atlassian Blameless Postmortem Process

**Assumption**: Every team and employee acted with best intentions based on information available at the time.

**Process**:
1. Build timeline of what happened, when, and what information was available at each decision point.
2. Discuss circumstances honestly and objectively to find true root cause(s).
3. Focus on systemic fixes, not individual punishment.
4. Make decisions; get approval from designated authority (e.g., division-level head of engineering).
5. Assign action items with owners and due dates.

**Blameless language rules**:
- Reframe: *"What about our system allowed this mistake to have this impact?"* instead of *"Why did you not check the logs?"*
- Use conditions, not errors: *"What conditions existed that allowed the deploy to proceed without catching the issue?"*

### 7.3 Rootly / EM-Tools Blameless Postmortem Framework

**Structure** (45–60 minute meeting):
1. **Opening (5 min)**: State blameless norm, review agenda.
2. **Timeline walkthrough (15–20 min)**: Chronological review, filling gaps.
3. **Root cause and contributing factors (15–20 min)**: 5 Whys; systemic gaps.
4. **What went well / what didn’t (10 min)**: Balanced response review.
5. **Action items (10 min)**: 3–5 specific, actionable items with owners and due dates.

**Timing**:
- Hold within 48 hours of incident resolution (memory fresh, not yet emotionally activated).
- 60–90 minutes for significant incidents.

**Categorization of action items**:
- Immediate fixes (before next deployment)
- Short-term improvements (within 1–2 sprints)
- Systemic investments (broader organizational support)

**Metric**: Track postmortem action completion rate monthly. If actions from 6+ months ago remain incomplete, the process generates insights but not change.

---

## 8. Backup / Disaster Recovery Validation

### 8.1 CIS Control 11 Safeguards

| Safeguard | Requirement |
|---|---|
| **11.1** | Documented data recovery process: scope, recovery prioritization, backup data security. Review annually. |
| **11.2** | Automated backups weekly or more frequently based on data sensitivity. Verify successful backup within 7 days. |
| **11.3** | Recovery data protected with equivalent controls to original data (encryption, separation). |
| **11.4** | Isolated instance of recovery data (offline, off-site, or different cloud account). |
| **11.5** | Test backup recovery quarterly (or more frequently) for a sampling of in-scope assets. |

### 8.2 Guinevere DR Validation Requirements

1. **RTO/RPO targets documented**: Current targets, assumptions, and gap analysis.
2. **Restore runbook**: Step-by-step restoration procedure with owner and access requirements.
3. **Break-glass access**: Emergency access process for backup vaults, key management, DNS, and cloud accounts when primary admins are unavailable.
4. **Validation cadence**: Quarterly restore test for at least one backup per data class (memory, configuration, secrets, model weights).
5. **Tabletop integration**: DR tabletop exercises test recovery assumptions against realistic timelines.

---

## 9. Tabletop Drills

### 9.1 Design Principles

**Objective**: Test decision-making, communication, and process gaps under realistic uncertainty — not a playbook quiz.

**Scenario rotation** (2–3 year cycle):
1. Ransomware / extortion
2. Business email compromise / wire fraud
3. Cloud credential compromise / data exfiltration
4. Insider threat (malicious data theft)
5. Supply chain compromise (critical third-party dependency)

**Inject design**:
- **Early** (first 15 min): Establish situation is more complex than initial assessment.
- **Mid-exercise**: Introduce stakeholder/resource constraints forcing trade-off decisions.
- **Late**: Address recovery decisions, external communication, lessons-learned framing.
- **Density**: 3–5 injects in a 90–120 minute tabletop.

### 9.2 Participant Roster (Minimum)

| Role | Purpose |
|---|---|
| Incident Commander | Decision authority, escalation |
| Technical Lead (forensics/IT) | Containment and eradication |
| Communications Lead | Stakeholder updates |
| Legal / Privacy | Regulatory notification, disclosure |
| Operations Lead | Business resumption |
| Outsourced MDR/MSSP liaison | External IR support |

### 9.3 Key Discussion Questions

- Who declares a disaster, and what is the threshold?
- Who decides whether to wait or begin failover?
- What customer communication happens before root cause is known?
- Who has access to DNS, cloud accounts, backup vaults, key management?
- What happens if one key admin is unavailable?
- What is the minimum viable service restored first?
- What validation checks happen before declaring service restored?
- If the last successful backup misses RPO, what is the business impact?

### 9.4 After-Action Report (AAR) Structure

| Section | Content |
|---|---|
| Executive Summary | What was exercised and what was found (2 paragraphs) |
| Exercise Overview | Scenario, participants, objectives |
| Findings by Severity | Critical (capability gaps), High (process/playbook gaps), Medium (improvements) |
| Remediation Action Plan | Finding reference, description, assigned owner, due date, verification method, status |

**Guinevere cadence**:
- Tabletop: Quarterly for high-risk functions, semiannual for others.
- Full technical simulation: Annually or after major change.
- Track KPIs: time to decisive action, time to containment, communication SLA met, remediation closure rate.

---

## 10. Cost Anomaly Response

### 10.1 FinOps Foundation Anomaly Management

**Definition**: Unexpected variations (increases) in cloud spending larger than expected given historical patterns.

**Maturity indicators**:
- ML-based anomaly detection embedded in tooling.
- Alerts integrate to event management / ticketing systems.
- Granular context (service, team, deployment) linked to alerts.
- Runbooks exist for common anomaly types.
- Postmortems include root cause attribution and improvements.

### 10.2 Guinevere Cost Anomaly Playbook

**Detection**: Monitor egress cost per resource, node hours, API call volume, and model token consumption against baselines.

**Response triggers**:
- Unusual egress spike → suspect data exfiltration; trigger security IR.
- Sudden compute cost surge → suspect runaway job or cryptojacking; contain first.
- API cost spike → suspect prompt injection loop or model abuse; throttle + investigate.

**Runbook steps**:
1. Verify alert legitimacy via telemetry and recent deployments.
2. Map spend to owner and contact responsible party.
3. Execute mitigation (scale down, pause job, throttle API) from runbook.
4. Record actions and timestamps in incident ticket.
5. Postmortem includes root cause attribution and improvements (tagging, automation guardrails).

---

## 11. AI Safety Incidents

### 11.1 GenAI-IRF (Practical Incident-Response Framework for Generative AI)

**Six incident archetypes**:
1. **Prompt injection / jailbreak**: Adversarial input bypasses safety alignment.
2. **Data exfiltration**: Sensitive data leaked through model output.
3. **Model manipulation / poisoning**: Training or fine-tuning data corrupted.
4. **Misinformation cascade**: Model produces harmful false outputs at scale.
5. **Privilege escalation via agent tools**: Agent invokes unauthorized API calls.
6. **Availability / resource exhaustion**: Model or agent consumes excessive compute.

**Containment primitives**:
- Flip gateway routing rule to known-safe configuration.
- Deploy emergency filter at model input layer.
- Revoke tool-use permissions and external API access.
- Route traffic to static fallback (degraded but safe).
- Preserve runtime state, in-context memory, and active session data for forensics.

### 11.2 AIR (Agent Incident Response for LLM Agents)

AIR defines a DSL-driven lifecycle:
1. **Detect**: Runtime semantic checks grounded in environment state and execution context.
2. **Contain**: Halt ongoing harmful effects via tool interface (disable tools, revoke tokens, pause workflows).
3. **Recover**: Restore environment to safe configuration (rollback actions, restore deleted records, revoke created resources).
4. **Eradicate**: Synthesize guardrail rules from incident data to prevent recurrence in future plan generation.

**Guinevere integration**: Every incident involving the agent loop triggers guardrail rule synthesis. New rules are committed to the guardrail rule set and evaluated during plan-generation stage of subsequent tasks.

### 11.3 LLM Incident Response Playbook (2026)

**Six-step loop**: Detect → Triage → Contain → Eval → Fix → Review

| Step | Activity |
|---|---|
| **Detect** | Error feed cluster spike, per-rubric drift, customer escalation |
| **Triage** | Name class (hallucination, jailbreak, drift, PII leak) and severity |
| **Contain** | Flip gateway route to known-safe config; confirm via response headers |
| **Eval** | Run bug class on golden set to verify rubric caught it |
| **Fix** | Prompt rollback, rubric tighten, retrieval re-index, or data fix |
| **Review** | Postmortem → new golden-set entry → CI gate for next PR |

**Anti-patterns to avoid**:
1. No containment primitive (waiting on deploy pipeline while users see bad output).
2. No per-rubric alerting (finding out from a tweet).
3. No incident class taxonomy (every page becomes SEV-1; team burns out).
4. No eval-gated verification (shipping fix without validation).
5. No postmortem-to-golden-set loop (same failure ships again next month).

---

## 12. Secret / Key Compromise

### 12.1 0xelitesystem Runbook Framework

Eight runbook archetypes:
1. AWS access keys
2. GCP service account keys
3. GitHub PAT
4. Slack webhook
5. Database credentials
6. JWT signing keys
7. TLS private keys
8. OAuth client secrets

**Universal phases**:
1. **Trigger**: How the leak was discovered.
2. **Containment**: Actions before rotation to limit further damage.
3. **Rotation**: Exact steps in correct order, including dependencies.
4. **Investigation**: What attacker may have done with credential.
5. **Audit logging**: Vendor logs to scope the incident.
6. **Recovery**: Restore service and access for legitimate users.
7. **Post-rotation hardening**: Controls to prevent future leaks.

### 12.2 Critical Sequencing Rules

**Revoke first, investigate second** (Decryption Digest):
- **Minutes 0–15**: Revoke at source; update secrets manager; deploy replacement. Do not scrub history first.
- **Minutes 15–45**: Blast radius assessment (check access logs for unusual IPs, regions, API calls).
- **Minutes 45–75**: Clean repository (BFG Repo Cleaner for full history).
- **Minutes 75–90**: Notify security team, engineering leadership, legal/compliance.

**Key insight**: History scrubbing prevents casual discovery but cannot recall data already cloned. The only control that eliminates risk is credential revocation.

### 12.3 Guinevere Secret Compromise Requirements

| Secret Type | Rotation Order | Special Considerations |
|---|---|---|
| TLS private key | Generate new CSR, issue new cert, deploy, revoke old | Active sessions may need graceful termination |
| JWT signing key | Issue new key, update verifier, revoke old | Tokens in flight remain valid until expiry; consider shorter TTL |
| Database credential | Rotate in secrets manager, deploy, verify connections | Check for hardcoded connections in application configs |
| Cloud API key | Revoke at provider, rotate in secrets manager, audit last 90 days of usage | Check for secondary access paths (assume roles, instance profiles) |
| GitHub PAT | Revoke in GitHub, rotate in secrets manager, audit repo access | Check for cached tokens in CI/CD runners |

**Post-rotation hardening**:
- Pre-commit hooks (detect-secrets or git-secrets).
- GitHub push protection.
- Repository-level secret scanning (GitGuardian or GHAS).
- Move all secrets to environment variables or secrets manager (Vault, AWS Secrets Manager, Azure Key Vault).

---

## 13. Observability and Incident Forensics

### 13.1 OpenTelemetry Incident Timeline Reconstruction

**Correlation model**:
- Trace ID: Links all spans in a distributed transaction.
- Span ID: Links log records to specific spans.
- Resource attributes: Links all signals from same service instance.
- Timestamps: Precise ordering across signal types.

**Timeline reconstruction query pattern**:
1. Find error traces in incident window.
2. Get all spans from those traces.
3. Get all logs correlated by trace IDs.
4. Find metric anomalies in same window.
5. Combine and order by timestamp.

**Guinevere application**: Every incident in `evidence/incidents/<slug>/` must include an OpenTelemetry-derived timeline spanning traces, logs, and metrics from the incident window.

### 13.2 Incidentary Causal Traces

Incidentary maps OTel spans to causal event models automatically:
- `service.name` → service name in traces.
- Span kind + semantic conventions → event kind (HTTP_IN, HTTP_OUT, QUEUE_CONSUME, etc.).
- OTel trace IDs and parent span IDs preserved as causal links.

**Value**: Zero-code-change integration for existing OTel instrumentation; causal chain visualization reduces MTTR.

---

## 14. Checklist for Runbook Authoring

### 14.1 Pre-Writing Requirements

- [ ] Incident severity taxonomy defined and approved (SEV-1 through SEV-4).
- [ ] Incident Commander model documented with primary and backup designations.
- [ ] Evidence path convention established: `evidence/incidents/<YYYY-MM-DD>-<SEV>-<slug>/`.
- [ ] Communication mechanisms defined (primary + secondary, noting email failure scenarios).
- [ ] Stakeholder contact list maintained and verified annually.

### 14.2 Runbook Structure (Every Runbook Must Contain)

| Section | Content |
|---|---|
| **Trigger** | Specific indicators that activate this runbook (alert name, log pattern, user report, external notification). |
| **Severity** | SEV level and escalation triggers. |
| **Roles** | IC, CL, OL, and any specialized roles for this incident type. |
| **Containment** | Exact steps to stop spread, including order of operations. Document what NOT to do. |
| **Evidence collection** | Artifacts to capture, hash algorithm, storage location, chain-of-custody log format. |
| **Eradication** | Root cause removal steps with validation criteria. |
| **Recovery** | Staged restoration order, validation checks per stage, "restored" definition. |
| **Communication** | Templates for internal stakeholders, external parties, regulators (if applicable). Timeframes for each. |
| **Post-incident** | Postmortem timing (≤48 hours), action item template, golden-set entry requirement. |

### 14.3 Quality Gates

- [ ] Runbook reviewed by at least one person not involved in writing it.
- [ ] Tabletop exercise conducted within 90 days of creation.
- [ ] All steps tested in non-production environment where feasible.
- [ ] Hash chain and evidence path validated in test run.
- [ ] Communication templates reviewed by legal/compliance.
- [ ] Runbook versioned and stored in version control.
- [ ] Dependencies (secrets, access, tools) documented with owner and fallback.

### 14.4 Maintenance Requirements

- [ ] Review and update runbook at least annually.
- [ ] Update within 5 business days after any incident that reveals a gap.
- [ ] Update after any change to system architecture, tooling, or team structure.
- [ ] Archive superseded runbooks with clear version history.
- [ ] Track tabletop exercise results and remediation closure rate per runbook.

---

## 15. Cross-Reference Matrix

| External Standard | Guinevere Requirement | Evidence Path Artifact |
|---|---|---|
| NIST SP 800-61r3 | CSF 2.0-aligned lifecycle, IR policy, RS/RC subcategories | `incident-report.md`, timeline |
| NIST IR 8387 | SHA-256 hashing, separate hash storage, 5-year retention | `evidence-hashes.sha256`, chain-of-custody log |
| Google SRE IMAG | IC/CL/OL roles, living incident document, explicit handoff | `timeline.md` (IC handoff entries) |
| OWASP SAMM | Formal IR process, trained team, RCA documentation | `action-items.md` |
| CIS Control 17 | Designated personnel, contact info, reporting process, thresholds | Runbook header metadata |
| CIS Control 11 | Automated backups, isolated recovery data, quarterly restore test | DR validation log |
| ISO 27037 | Chain of custody, precautions at incident site, evidence preservation | `chain-of-custody.log` |
| SWGDE | Contemporaneous notes, hash verification, access logs | `artifacts/` with metadata |
| FinOps Foundation | Cost anomaly detection, attribution, runbook, postmortem | Cost incident section in `incident-report.md` |
| OpenTelemetry | Trace/log/metric correlation, timeline reconstruction | `timeline.md` with trace IDs |
| GenAI-IRF / AIR | AI-specific archetypes, containment primitives, guardrail synthesis | `action-items.md` (guardrail rules) |
| Secret leak runbooks | Revoke-first sequencing, blast radius assessment, history cleanup | `incident-report.md` (secret type appendix) |

---

## 16. Unresolved Assumptions

1. **Regulatory jurisdiction**: Guinevere’s operator location and applicable data protection laws (GDPR, HIPAA, local privacy statutes) must be confirmed before finalizing notification timeframes.
2. **External IR retainer**: Whether to engage third-party IR support for SEV-1 incidents, and under what conditions, is not yet decided.
3. **Evidence retention period**: Five years is NIST best practice in absence of statute; operator must confirm legal requirements.
4. **Multi-tenancy scope**: Current design is single-user; if multi-tenant features are added, cross-tenant contamination procedures must be added.
5. **AI provider incident coordination**: Process for coordinating with model providers (Google, OpenAI, etc.) during upstream model incidents is not yet defined.

---

## 17. Next Actions

1. **Draft** `Guinevere_IncidentResponse_Severity_v1.0.md` using Section 2 severity definitions.
2. **Draft** `Guinevere_IncidentLifecycle_v1.0.md` mapping NIST CSF 2.0 Functions to Guinevere-specific phases.
3. **Draft** `Guinevere_EvidencePolicy_v1.0.md` specifying hash algorithm, chain-of-custody format, and retention schedule.
4. **Draft** `Guinevere_SecretCompromise_Runbook_v1.0.md` using Section 12 runbook framework.
5. **Schedule** first tabletop exercise within 30 days, using ransomware scenario from Section 9.
6. **Validate** backup restoration procedure for at least one data class within 30 days.

---

*End of report.*
