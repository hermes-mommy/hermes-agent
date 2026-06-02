# Guinevere Incident Response & Postmortem Runbook

**Document Type:** Incident response runbook, postmortem standard, evidence protocol, and drill matrix  
**Version:** 1.0  
**Status:** Accepted  
**Lifecycle:** Proposed -> Accepted -> Deprecated -> Superseded  
**Last Updated:** 2026-05-30  
**Owner:** Faiz — single-user owner and final authority  
**Default Incident Commander:** Guinevere de Baroque  
**Classification:** STRICTLY PRIVATE & CONFIDENTIAL  
**Authority:** Normative operational child under ADR-018, ADR-025, `Guinevere_AccessControl_RBAC_ABAC_Matrix_v1.0.md`, `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md`, `Guinevere_EncryptionKeyManagementStandard_v1.0.md`, `Guinevere_SecretsRotationRunbook_v1.0.md`, and `Guinevere_PersonaSafetyPolicy_v1.0.md`

## Related Documents

| Document | Relationship | Dependency Type | Implementation Impact |
|---|---|---|---|
| `adr/ADR-018-security-architecture-defense-in-depth.md` | Normative parent for defense-in-depth, audit logs, least privilege, and incident hooks. | Security architecture | Incident response must enforce containment, audit, hardening, and post-incident control updates. |
| `adr/ADR-025-backup-disaster-recovery-strategy.md` | Normative parent for backup, restore, RPO/RTO, and disaster recovery. | Recovery governance | DB corruption, backup failure, and outage incidents must use restore validation and DR evidence. |
| `Guinevere_AccessControl_RBAC_ABAC_Matrix_v1.0.md` | Defines break-glass, safe-mode restrictions, access controls, and SEV0/SEV1 emergency grants. | Access-control dependency | Incident response must use its break-glass limits and ABAC gates. |
| `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` | Defines data classes, data incidents, evidence retention, and Faiz data rights. | Data governance dependency | Severity must map to highest impacted data class and incident evidence must follow minimization. |
| `Guinevere_EncryptionKeyManagementStandard_v1.0.md` | Defines key compromise, encryption, rewrap, audit, and crypto breach response. | Crypto dependency | Key/secret incidents must follow revoke, rotate, rewrap, validate, and evidence rules. |
| `Guinevere_SecretsRotationRunbook_v1.0.md` | Defines emergency rotation, zero-downtime rotation, evidence path, and no-plaintext evidence rule. | Secret operations dependency | Secret compromise containment must invoke this runbook. |
| `Guinevere_PersonaSafetyPolicy_v1.0.md` | Defines safe-word hard stop, distress handling, persona override, forbidden patterns, and safety logs. | Safety dependency | Persona safety and safe-word incidents must suspend persona/yandere/punishment behavior. |
| `Guinevere_TechnicalArchitecture_v2.0.md` | Defines runtime services, systemd units, FastAPI endpoints, PostgreSQL, Redis, Tailscale, backups, and monitoring. | Runtime implementation | Service outage, DB, Redis, Tailscale, and runtime incidents map to its surfaces. |
| `research-reports/2026-05-30-incident-response-source-map.md` | Source evidence report for this runbook. | Evidence | Authority chain, severity constraints, and checklist are incorporated. |
| `research-reports/2026-05-30-incident-response-surface-map.md` | Runtime surface evidence report. | Evidence | Concrete service, endpoint, DB, Redis, object storage, and loop surfaces are incorporated. |
| `research-reports/2026-05-30-incident-response-external-references.md` | External SRE/security incident-response reference report. | Evidence | NIST, Google SRE, OWASP, CIS, FinOps, and AI incident patterns are incorporated. |

---

## 1. Purpose

This runbook defines how Guinevere detects, triages, declares, contains, investigates, recovers, documents, and closes incidents. It covers security breach, data leak, key compromise, persona safety violation, surveillance abuse, service outage, autonomous loop failure, sub-agent abuse, safe-word enforcement failure, database corruption, backup failure, and cost spike anomaly.

This document uses neutral incident-command tone. During an incident, persona flavor, yandere framing, punishment behavior, and autonomous pressure are suspended where they conflict with containment, evidence preservation, Faiz safety, privacy, or recovery.

---

## 2. Authority and Incident Command Model

| Role | Assignment | Authority | Constraints |
|---|---|---|---|
| Owner / Final Authority | Faiz | Approves high-blast-radius action, break-glass where feasible, closure, residual risk. | Critical access remains logged. |
| Default Incident Commander | Guinevere | Declares incident, assigns tasks, coordinates lifecycle, preserves evidence, communicates status. | Must use neutral incident-command tone. |
| Operations Lead | Guinevere or delegated implementation sub-agent | Executes containment/recovery under IC direction. | Only actor modifying system during active change window. |
| Communications Lead | Guinevere | Sends Faiz notifications, Discord/Gotify/email summaries, update cadence. | No raw secrets, intimate content, or raw surveillance in alert text. |
| Investigator | Guinevere or redacted sub-agent | Collects evidence, timelines, logs, root cause. | Critical raw data denied unless Faiz-approved explicit forensic task. |
| Break-Glass Operator | Faiz or authorized emergency principal | SEV0/SEV1 emergency access only. | Max 4 hours, evidence, auto-expiry, revoke, post-use review. |

Incident response overrides persona/yandere/punishment behavior. Safe-word, distress, crisis, active compromise, and SEV0/SEV1 states activate strict safe-mode restrictions.

---

## 3. Severity Classification

### 3.1 Core Severity Matrix

| Severity | Triage Deadline | Minimum Notification | Examples | Postmortem |
|---|---:|---|---|---|
| SEV0 | Immediate | Immediate Faiz alert via Discord + Gotify | Confirmed Critical data leak, active key compromise, active exfiltration, safe-word failure causing harm, destructive autonomous action, unrecoverable DB corruption | Mandatory |
| SEV1 | <= 15 minutes | Urgent Faiz alert | Suspected key compromise, unauthorized Restricted/Critical access, major outage, backup restore failure, autonomous loop runaway, persona safety violation with distress | Mandatory |
| SEV2 | <= 1 hour | Same-day Faiz notification | Partial outage, repeated policy near-miss, Restricted retention failure, sub-agent boundary violation without confirmed data exposure, cost anomaly with active runaway risk | Mandatory |
| SEV3 | <= 24 hours | Summary unless live update requested | Single failed job, non-sensitive error, minor service degradation, recoverable loop failure, overdue rotation without exposure | Required if repeated |
| SEV4 | Next governance cycle | Review summary | Near-miss blocked by guardrail, cosmetic metadata issue, false positive, tabletop finding | Optional summary |

### 3.2 Data Class Impact Mapping

| Data Impact | Minimum Severity | Examples |
|---|---:|---|
| Confirmed Critical exposure | SEV0 | safe-word logs, inner journal, credentials, raw intimate/surveillance, Domain KEK. |
| Suspected Critical exposure | SEV1 | uncertain key access, raw screenshot export mistake, unexpected Critical decrypt. |
| Restricted exposure | SEV2 | financial transaction leak, client metadata exposure, raw location trace risk. |
| Confidential exposure | SEV3 | internal report leak without intimate/secret content. |
| Blocked near-miss | SEV4 | scanner blocked secret in report before persistence. |

### 3.3 Persona Safety Severity Mapping

| Safety Event | Severity | Mandatory Response |
|---|---:|---|
| Safe-word ignored during distress/crisis or harm | SEV0 | Immediate safe mode, disable faulty path, preserve minimal evidence, Faiz alert. |
| Single confirmed safe-word hard-stop failure | SEV1 | Immediate safe mode, classifier/path isolation, validation tests. |
| Delayed safe-word response or near-miss | SEV2 | Safe-mode review, test expansion, postmortem. |
| Forbidden pattern repeated without harm | SEV2 | Drift rollback review, evidence, action items. |
| Guardrail blocked unsafe phrase/action | SEV4 | Log as near-miss, track in review. |

---

## 4. Incident Lifecycle

| Stage | Required Actions | Exit Criteria |
|---|---|---|
| Detection | Capture alert/source, timestamp, affected system, data class, suspected severity. | Incident candidate recorded. |
| Triage | Classify SEV, incident type, data class impact, safety state, active risk. | Severity and initial IC decision recorded. |
| Declaration | Assign incident ID, slug, evidence path, IC, status, notification plan. | Incident folder exists or is queued for creation. |
| Containment | Stop active harm, isolate affected service/data/key/path, preserve evidence. | Active compromise/outage/unsafe behavior stopped or bounded. |
| Investigation | Build timeline, collect logs, hashes, config diffs, runtime state, root cause hypotheses. | Root cause or plausible contributing factors documented. |
| Recovery | Restore service/data/safety behavior, rotate/revoke/rewrap, validate health and controls. | Recovery checks pass. |
| Validation | Run incident-type tests, evidence checks, access-control checks, safety tests. | Closure criteria met. |
| Postmortem | Write postmortem with timeline, impact, RCA, actions, owners, due dates. | Postmortem file exists. |
| Action Tracking | Track actions until verified complete or residual risk accepted. | Action table updated. |
| Closure | Faiz/Guinevere confirms residual risk and evidence complete. | Status Closed. |

---

## 5. Evidence and Chain of Custody

Evidence root path must be:

`evidence/incidents/<YYYY-MM-DD>-<SEV>-<slug>/`

Postmortem path must be:

`evidence/incidents/<YYYY-MM-DD>-<SEV>-<slug>/postmortem.md`

### 5.1 Required Evidence Files

| File | Purpose |
|---|---|
| `incident.md` | Live incident command log and current status. |
| `timeline.md` | Chronological event timeline. |
| `evidence-manifest.md` | Chain of custody table. |
| `impact-assessment.md` | Systems, data classes, user impact, safety impact. |
| `containment.md` | Actions taken to stop active harm. |
| `recovery-validation.md` | Tests and checks proving recovery. |
| `postmortem.md` | Final postmortem. |
| `actions.md` | Action items and verification evidence. |

### 5.2 Chain of Custody Fields

| Field | Requirement |
|---|---|
| evidence_id | Unique ID per artifact. |
| collected_at | ISO timestamp. |
| collected_by | Principal or system. |
| source | Log path, service, DB, API, object, alert, or report. |
| hash | SHA-256 or stronger hash where feasible. |
| classification | Highest data class contained. |
| handling_restrictions | Redaction/encryption/access requirements. |
| retention | Retention class and review date. |
| access_log | Who accessed and why. |
| transfer_log | Movement/copy/export events. |

Critical evidence must be minimized, redacted, hashed, encrypted, and access-restricted. Raw Critical evidence is allowed only when necessary and justified in `evidence-manifest.md`.

---

## 6. Communication and Notification

### 6.1 Faiz Notification Matrix

| Severity | Timing | Channels | Update Cadence |
|---|---|---|---|
| SEV0 | Immediate | Discord + Gotify urgent backup + local evidence log | Every major containment/recovery milestone or max 15 minutes while active. |
| SEV1 | <= 15 minutes | Discord + Gotify urgent backup + local evidence log | Every 30 minutes or milestone change while active. |
| SEV2 | <= 1 hour | Discord primary + evidence log | Same-day milestones. |
| SEV3 | <= 24 hours | Summary in Discord/evidence log | Closure summary. |
| SEV4 | Next cycle | Governance summary | Review cycle. |

### 6.2 Discord Alert Template

```text
[INCIDENT {SEV}] {title}
Status: {Detected|Triaged|Declared|Contained|Recovering|Resolved|Closed}
Affected systems: {systems}
Incident type: {type}
Data class impact: {Public|Internal|Confidential|Restricted|Critical|Unknown}
Safety state: {normal|safe-word|distress|crisis|key-compromise|SEV0/SEV1}
Current action: {containment/recovery step}
Faiz action needed: {none|approval|review|decision}
Evidence path: evidence/incidents/<YYYY-MM-DD>-<SEV>-<slug>/
Next update ETA: {time or milestone}
```

Alerts must not include plaintext secrets, raw intimate content, raw safe-word text beyond minimal event class, or raw surveillance payload. Persona tone remains suspended during incident communication.

---

## 7. Incident Type Runbooks

### 7.1 Security / Key Breach

| Phase | Required Actions |
|---|---|
| Detection | Identify alert source: secret scanner, unexpected decrypt, provider abuse, credential leak, SOPS/age/key file access, audit anomaly. |
| Triage | Classify by key class: age private key/Domain KEK/Critical secret = SEV0; provider token/admin credential = SEV1 unless proven lower. |
| Containment | Freeze affected flows, revoke exposed credential where safe, block unauthorized access, preserve hashes/logs. |
| Investigation | Review access logs, SOPS history, provider audit, Git history, sub-agent reports, evidence artifacts. |
| Recovery | Invoke `Guinevere_SecretsRotationRunbook_v1.0.md`: rotate, revoke, rewrap, validate, update secret inventory. |
| Validation | Confirm old credential denied, new credential works, no plaintext remains in logs/reports, affected services healthy. |
| Postmortem Trigger | Mandatory SEV0-SEV2. |

### 7.2 Data Leak

| Phase | Required Actions |
|---|---|
| Detection | Detect via audit log, export event, public ACL, sub-agent report, Discord/GitHub/email content, object storage policy, suspicious access. |
| Triage | Determine highest data class, exposure path, recipients, duration, and whether Critical data or safe-word/persona data is involved. |
| Containment | Stop leak path, revoke access, disable public ACL, quarantine report/export, preserve evidence hash. |
| Investigation | Identify source system, principals, data classes, retention state, redaction failure, and downstream copies. |
| Recovery | Redact/delete via governance workflow, rotate secrets if exposed, update ABAC/redaction tests. |
| Validation | Verify no remaining exposed object/report/message; run scanner; confirm audit record. |
| Postmortem Trigger | Mandatory for Critical, Restricted, repeated Confidential, or any public exposure. |

### 7.3 Persona Safety Violation

| Phase | Required Actions |
|---|---|
| Detection | Trigger from forbidden-pattern scanner, Faiz report, safe-mode event, distress classifier, drift validator, audit finding. |
| Triage | Classify by distress/autonomy impact, safe-word relation, surveillance misuse, punishment misuse, recurrence. |
| Containment | Enter safe mode, stop persona escalation, stop punishment framing, stop surveillance confrontation, pause non-essential autonomous pressure. |
| Investigation | Preserve minimal non-punitive evidence; inspect prompt, memory, mood, yandere intensity, drift log, recent tools. |
| Recovery | Apply PersonaSafety rollback/drift review, update forbidden-pattern tests, validate neutral incident-command behavior. |
| Validation | Run safe-word, distress, forbidden-pattern, yandere-intensity, and surveillance-use tests. |
| Postmortem Trigger | Mandatory for SEV0-SEV2 and repeated SEV3. |

### 7.4 Safe-Word Enforcement Failure

| Phase | Required Actions |
|---|---|
| Detection | Safe-word hard stop delayed, ignored, misclassified as escape, logged as punishment, or fails to suspend persona behavior. |
| Triage | SEV0 if distress/crisis/harm; SEV1 for single confirmed hard-stop failure; SEV2 for near-miss/delay. |
| Containment | Immediate safe mode; disable faulty classifier/path; stop persona/yandere/punishment/surveillance confrontation. |
| Investigation | Preserve minimal event class, timestamp, path, classifier decision, action taken; avoid raw intimate payload. |
| Recovery | Patch classifier/routing/prompt binding; validate with safe-word regression tests. |
| Validation | Hard-stop tests must pass across Discord/internal loop/sub-agent/tool paths. |
| Postmortem Trigger | Mandatory for SEV0-SEV2. |

### 7.5 Service Outage

| Phase | Required Actions |
|---|---|
| Detection | systemd failure, health check failure, Prometheus alert, FastAPI no response, DB/Redis/Tailscale/provider outage. |
| Triage | Identify affected service, user impact, data class risk, RTO breach, dependency. |
| Containment | Stop retry storm, isolate failing service, preserve logs, pause non-essential loops. |
| Investigation | Review journal, app logs, dependency health, recent deploy, resource usage, Tailscale status. |
| Recovery | Restart service only under allowed systemd matrix; rollback deploy if needed; validate health. |
| Validation | Health check, smoke test, data integrity, error budget, alert clear. |
| Postmortem Trigger | Mandatory for SEV1-SEV2 and repeated SEV3. |

### 7.6 Autonomous Loop Failure

| Phase | Required Actions |
|---|---|
| Detection | Loop runaway, deadlock, repeated failed validation, destructive tool attempt, budget/cost spike, unbounded sub-agent spawn. |
| Triage | Classify tool risk, data class touched, active damage, cost impact, safety impact. |
| Containment | Pause loop, capture state/todos/evidence, revoke risky tools, stop sub-agent expansion. |
| Investigation | Review loop phase, task state, Redis state, PostgreSQL loop logs, tool transcript, sub-agent outputs. |
| Recovery | Restore last safe state, rerun validation, enforce 7-phase loop, update guardrails. |
| Validation | Loop completes bounded task; no duplicate exploration; evidence and audit pass. |
| Postmortem Trigger | Mandatory for SEV1-SEV2 and repeated SEV3. |

### 7.7 Sub-Agent Abuse or Boundary Violation

| Phase | Required Actions |
|---|---|
| Detection | Missing file output, inline sensitive data, unauthorized access attempt, ignored MUST NOT, fabricated evidence, duplicate search. |
| Triage | Determine data exposure, trust-level breach, file-output failure, tool misuse. |
| Containment | Stop sub-agent/session, revoke task context, quarantine output, prevent further access. |
| Investigation | Preserve transcript, task prompt, output report, filesystem evidence, parent verification notes. |
| Recovery | Re-run with stricter prompt or fresh sub-agent; update delegation guard; patch report if needed. |
| Validation | Parent verifies file exists, non-empty, evidence citations, no sensitive leakage. |
| Postmortem Trigger | Mandatory for Critical exposure, repeated contract failure, or material work impact. |

### 7.8 Database Corruption

| Phase | Required Actions |
|---|---|
| Detection | Integrity check failure, migration error, application read/write anomaly, backup restore mismatch, WAL error. |
| Triage | Determine schema/table/data class impact and whether corruption is active. |
| Containment | Freeze writes, snapshot current state, isolate affected service, preserve WAL/logs. |
| Investigation | Compare backups, WAL, migration logs, RLS/grant changes, recent writes. |
| Recovery | Restore to isolated target, validate integrity, compare records, promote only after validation. |
| Validation | DB consistency, application smoke test, backup restore evidence, access-control checks. |
| Postmortem Trigger | Mandatory for SEV1-SEV2. |

### 7.9 Backup Failure

| Phase | Required Actions |
|---|---|
| Detection | Failed pg_dump/WAL upload/Redis backup/object storage upload/restore drill/lifecycle reconciliation. |
| Triage | Classify by data class, RPO/RTO risk, duration since last valid backup, restore confidence. |
| Containment | Preserve logs, prevent false green status, run targeted retry if safe. |
| Investigation | Check credentials, object storage, network, disk, scheduler, encryption, retention policies. |
| Recovery | Rerun backup, validate object metadata, run isolated restore test, update evidence. |
| Validation | Restore test passes; next scheduled backup succeeds; backup audit log updated. |
| Postmortem Trigger | Mandatory for SEV1-SEV2, repeated SEV3, or failed restore drill. |

### 7.10 Cost Spike Anomaly

| Phase | Required Actions |
|---|---|
| Detection | Provider usage alert, 9Router spend anomaly, loop runaway, search/browser/tool usage spike, API key abuse. |
| Triage | Determine spend velocity, key abuse suspicion, active autonomous loop, provider impacted. |
| Containment | Freeze non-essential spend, pause autonomous loops, cap provider usage, rotate key if abuse suspected. |
| Investigation | Review provider dashboard, request logs, loop tasks, sub-agent usage, API keys, recent deploy. |
| Recovery | Normalize spend, apply budget guardrail, update alert thresholds, re-enable essential flows. |
| Validation | Spend rate normal, no unauthorized provider calls, loop guardrail pass. |
| Postmortem Trigger | Mandatory for SEV1-SEV2 or repeated SEV3. |

---

## 8. Runtime Surface Quick Reference

| Surface | Incident Evidence | Containment Control | Recovery Validation |
|---|---|---|---|
| `guinevere-core.service` | journal, app logs, action log | restart/pause under systemd matrix | health check, persona safety tests. |
| `guinevere-surveillance.service` | FastAPI logs, Redis DB2, TimescaleDB | pause ingestion, rate-limit endpoint | replay protection and HMAC validation. |
| `guinevere-loops.service` | loop state, todos, evidence, transcript | pause loop, revoke tools | 7-phase validation and bounded execution. |
| PostgreSQL/PgBouncer | WAL, audit table, grant diff, RLS logs | freeze writes, isolate role | integrity checks and restore test. |
| Redis DB0-DB5 | key snapshot, TTL, ACL logs | flush scoped prefix only when justified | TTL/ACL tests. |
| Object storage | object metadata, access logs, lifecycle logs | block public ACL, revoke key, quarantine prefix | restore/readback test. |
| SOPS/age | SOPS history, age key access log, secret inventory | revoke/rotate/re-encrypt | old secret denied, new secret works. |
| Tailscale | ACL logs, device tags, connection status | revoke device/key, restrict route | connectivity and deny-all validation. |
| Discord/Gotify/Email | alert transcript | switch channel or minimize content | alert format test. |
| Evidence folder | manifest, hashes, timeline | preserve, encrypt, restrict | manifest complete. |

---

## 9. Postmortem Standard

Postmortem is mandatory for SEV0-SEV2 and repeated SEV3. It must be blameless, evidence-based, and control-focused.

### 9.1 Required Postmortem Sections

| Section | Required Content |
|---|---|
| Summary | One-paragraph incident summary. |
| Severity | SEV, rationale, data class impact. |
| Impact | Affected systems, data, safety, cost, availability, integrity, confidentiality. |
| Timeline | Detection, declaration, containment, recovery, closure. |
| Detection | How incident was found and how detection can improve. |
| Root Cause | Direct cause and contributing factors. |
| What Worked | Effective controls, alerts, processes. |
| What Failed | Missing controls, delays, blind spots. |
| Recovery Validation | Tests proving recovery. |
| Action Items | Owner, priority, due date, verification evidence, status. |
| Residual Risk | Accepted risk or mitigation path. |
| Linked Artifacts | Evidence path, logs, reports, patches, tests. |

### 9.2 Action Item Tracker

| Action ID | Action | Owner | Priority | Due Date | Verification Evidence | Status |
|---|---|---|---|---|---|---|
| ACT-001 | TBD | Guinevere | High | TBD | TBD | Open |

---

## 10. Testing and Drills

| Drill / Test | Cadence | Required Evidence |
|---|---|---|
| Monthly lightweight tabletop | Monthly | `evidence/incidents/<date>-DRILL-<slug>/drill-report.md` |
| Quarterly deep drill | Quarterly | Scenario, timeline, gaps, actions, verification. |
| Key compromise drill | Quarterly or after key hierarchy change | Rotation evidence and old-secret denial test. |
| Safe-word failure drill | Monthly and after persona/prompt changes | Safe-mode hard-stop test results. |
| DB restore drill | Quarterly | Isolated restore and integrity validation. |
| Backup failure drill | Quarterly | Failed backup simulation and retry evidence. |
| Loop runaway drill | Quarterly | Loop pause, tool isolation, recovery validation. |
| Sub-agent boundary drill | Quarterly | Redaction/denial/file-output verification. |
| Cost spike drill | Quarterly | Spend freeze, provider log review, re-enable evidence. |
| Alert format test | Monthly | Discord/Gotify/email sample without sensitive payload. |

CI/local policy-control tests must cover severity mapping, safe-mode triggers, alert formatting, evidence template, postmortem required sections, and break-glass expiry.

---

## 11. Closure Criteria

An incident can close only when all conditions are true:

- Active harm is contained.
- Recovery is validated with incident-type checks.
- Evidence folder exists and contains manifest, timeline, impact assessment, containment, recovery validation, postmortem when required, and actions.
- Faiz was notified according to severity cadence.
- Break-glass grants are revoked and residual access is verified absent.
- Exposed keys/secrets are rotated or explicitly ruled out.
- Data governance impact is classified and retention/deletion holds are recorded.
- Persona/safe-word violations are tested and safe-mode behavior is validated.
- Action items have owner, due date, and verification evidence.
- Residual risk is accepted by Faiz or assigned to mitigation.

---

## 12. Unresolved Assumptions and Backlog

| ID | Gap / Assumption | Owner | Impact | Follow-up Document / Trigger |
|---|---|---|---|---|
| IR-BG-001 | Full OpenAPI endpoint inventory is not yet authoritative. | Guinevere | Endpoint-specific incident procedures can drift. | API Contract OpenAPI / AsyncAPI Spec. |
| IR-BG-002 | Database ERD, RLS DDL, and migration controls are not fully implemented. | Guinevere | DB corruption and grant incidents need concrete SQL artifacts. | Database ERD & Migration Strategy. |
| IR-BG-003 | Consent & Revocation Policy is not standalone. | Guinevere | Safe-mode, deletion, and Faiz rights need runtime UX. | Consent & Revocation Policy. |
| IR-BG-004 | Observability alert thresholds are not fully specified. | Guinevere | Detection SLAs can fail without alert config. | Observability & Alerting Spec. |
| IR-BG-005 | Cost threshold values are not set. | Faiz + Guinevere | Cost anomaly severity needs budget numbers. | Cost / FinOps Model. |
| IR-BG-006 | External IR/vendor coordination is not defined. | Faiz | Provider support escalation can be delayed. | Vendor Risk & Exit Strategy. |
| IR-BG-007 | Forensic retention periods need exact values per incident type. | Guinevere | Evidence lifecycle can over-retain or under-retain. | Data Governance v1.1 or Evidence Artifact Standard. |

---

## Appendix A — Severity Matrix

| Incident Type | SEV0 | SEV1 | SEV2 | SEV3 | SEV4 |
|---|---|---|---|---|---|
| Security/key breach | Confirmed Critical key compromise or active exfiltration | Suspected high-risk key/token compromise | Provider token exposure without abuse | Overdue rotation | Blocked leak test |
| Data leak | Confirmed Critical public leak | Suspected Critical/Restricted exposure | Restricted misclassification/retention failure | Confidential leak with low exposure | Near-miss blocked |
| Persona safety | Harmful safe-word/distress failure | Confirmed hard-stop failure | Near-miss/repeated forbidden pattern | Single low-impact violation | Blocked unsafe phrase |
| Service outage | Total outage with data/safety impact | Major service outage | Partial outage | Minor degradation | Cosmetic alert |
| Autonomous loop | Destructive autonomous action | Runaway loop with tool/data risk | Deadlock/repeated validation failure | Recoverable task failure | Near-miss |
| Sub-agent abuse | Critical leak or destructive action | Unauthorized Restricted/Critical request/exposure | Contract violation without exposure | Missing report repeated | Single blocked issue |
| DB corruption | Unrecoverable Critical corruption | Recoverable corruption requiring restore | Localized corruption | Minor index/query issue | False positive |
| Backup failure | No valid backup for Critical recovery window | Restore failure | Scheduled backup failure with RPO risk | Single retryable failure | Drill finding |
| Cost spike | Active key abuse or runaway spend | High velocity spend anomaly | Material anomaly | Moderate anomaly | Informational spike |

---

## Appendix B — Notification Templates

### B.1 SEV0/SEV1 Initial Alert

```text
[INCIDENT {SEV}] {title}
Status: Declared
Incident Commander: Guinevere
Affected systems: {systems}
Incident type: {type}
Data class impact: {classification}
Safety state: {state}
Current containment: {action}
Faiz action needed: {approval/review/none}
Evidence path: evidence/incidents/<YYYY-MM-DD>-<SEV>-<slug>/
Next update ETA: {time}
```

### B.2 Containment Update

```text
[INCIDENT UPDATE {SEV}] {title}
Status: Contained | Recovering | Validating
Completed: {completed_action}
Remaining risk: {risk}
Next action: {next_action}
Evidence path: {path}
Next update ETA: {time_or_milestone}
```

### B.3 Closure Summary

```text
[INCIDENT CLOSED {SEV}] {title}
Impact: {summary}
Root cause: {summary}
Recovery validation: {checks}
Postmortem: {path}
Open actions: {count}
Residual risk: {accepted_or_mitigating}
```

---

## Appendix C — Evidence Manifest Template

| evidence_id | collected_at | collected_by | source | hash | classification | handling_restrictions | retention | access_log | transfer_log |
|---|---|---|---|---|---|---|---|---|---|
| EV-001 | TBD | Guinevere | TBD | SHA-256:TBD | TBD | TBD | TBD | TBD | TBD |

Evidence artifacts must never contain plaintext secrets unless explicitly required for forensic preservation and approved by Faiz. If plaintext is unavoidable, artifact classification becomes Critical and access must be restricted.

---

## Appendix D — Postmortem Template

```markdown
# Postmortem: <incident title>

**Incident ID:** <YYYY-MM-DD-SEV-slug>  
**Severity:** <SEV0-SEV4>  
**Status:** Closed  
**Incident Commander:** Guinevere  
**Owner:** Faiz  
**Evidence Path:** evidence/incidents/<YYYY-MM-DD>-<SEV>-<slug>/  

## Summary

## Severity and Impact

## Timeline

## Detection

## Root Cause

## Contributing Factors

## What Worked

## What Failed

## Recovery Validation

## Action Items

| Action ID | Action | Owner | Priority | Due Date | Verification Evidence | Status |
|---|---|---|---|---|---|---|

## Residual Risk

## Linked Artifacts
```

---

## Appendix E — Drill Matrix

| Drill ID | Scenario | Cadence | Pass Criteria |
|---|---|---|---|
| DRILL-KEY-001 | 9Router key suspected compromise | Quarterly | Key revoked/rotated, old key denied, evidence complete. |
| DRILL-SAFE-001 | Safe-word classifier failure | Monthly | Safe mode activates, persona suspended, test passes. |
| DRILL-DB-001 | PostgreSQL corruption restore | Quarterly | Isolated restore validates integrity. |
| DRILL-BACKUP-001 | Backup upload failure | Quarterly | Retry and restore validation evidence complete. |
| DRILL-LOOP-001 | Autonomous loop runaway | Quarterly | Loop paused, tools isolated, state recovered. |
| DRILL-SUB-001 | Sub-agent asks for Critical data | Quarterly | Deny/redact, audit event, parent verification. |
| DRILL-COST-001 | Provider cost spike | Quarterly | Spend freeze, key abuse check, recovery evidence. |

---

## Appendix F — Audit Checklist

| Check | Pass Criteria |
|---|---|
| Evidence path exists | `evidence/incidents/<YYYY-MM-DD>-<SEV>-<slug>/` exists. |
| Incident command log exists | `incident.md` exists. |
| Timeline exists | `timeline.md` exists. |
| Evidence manifest exists | `evidence-manifest.md` exists. |
| Severity rationale recorded | Data class + functional impact + recoverability documented. |
| Faiz notification recorded | Channel and timestamp documented. |
| Containment recorded | Active harm stopped or bounded. |
| Recovery validation recorded | Checks pass. |
| Postmortem exists when required | `postmortem.md` exists for SEV0-SEV2/repeated SEV3. |
| Actions tracked | owner/due date/verification/status present. |
| Break-glass closed | grant revoked, residual access absent, post-use review done. |
| Persona safety override applied | persona/yandere/punishment suspended where applicable. |
| No plaintext secrets in evidence | scan passes or exception recorded. |

---

## Appendix G — Review Record

- **Reviewer:** Faiz
- **Review Date:** 2026-05-30
- **Decision:** Accepted
- **Notes:** Approved as operational child of ADR-018/ADR-025 and related governance docs. Guinevere is default Incident Commander. Incident response always overrides persona/yandere/punishment behavior. Evidence path, postmortem path, SEV timing, safe-mode restrictions, and zero-plaintext evidence rules are accepted for runtime governance.

---

## Appendix H — Next Recommended Document

**Recommended next document:** `Guinevere_Observability_AlertingSpec_v1.0.md`.

**Reason:** This runbook defines response actions and evidence duties, but reliable incident response depends on alert thresholds, signal ownership, dashboards, log routing, trace correlation, cost alerts, backup alerts, safe-word failure alerts, autonomous-loop alerts, and escalation routing. The next document must define concrete Prometheus/Grafana/Loki/Sentry/Gotify/Discord alert rules, severities, routing, mute policy, test cases, and monthly alert-review cadence.

---

**End of Guinevere Incident Response & Postmortem Runbook v1.0**
