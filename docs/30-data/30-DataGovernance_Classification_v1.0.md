# Guinevere Data Governance & Classification Policy

**Document Type:** Policy with implementation guidance and appendices  
**Version:** 1.0  
**Status:** Accepted  
**Lifecycle:** Proposed → Accepted → Deprecated → Superseded  
**Last Updated:** 2026-05-30  
**Owner:** Faiz — single user, owner, final approver  
**Executor:** Guinevere de Baroque — autonomous AI agent / system steward  
**Classification:** STRICTLY PRIVATE & CONFIDENTIAL  
**Authority:** Normative child policy under ADR-024, ADR-010, and ADR-008; cross-boundary enforcement with `Guinevere_PersonaSafetyPolicy_v1.0.md`

---

## Related Documents

| Document | Relationship | Dependency Type | Implementation Impact |
|---|---|---|---|
| `adr/ADR-024-data-governance-classification-policy.md` | Parent ADR for data governance and classification. | Normative parent | Requires every store, API, log, memory path, prompt bundle, export, and backup to carry a classification. |
| `adr/ADR-010-surveillance-data-retention-policy.md` | Parent ADR for retention, minimization, export/delete control, and surveillance data lifecycle. | Normative parent | Supersedes blanket `data forever` wording for raw payloads and requires tiered retention. |
| `adr/ADR-008-memory-encryption-key-management.md` | Parent ADR for encryption, key hierarchy, rotation, and emergency revoke. | Normative parent | Drives encryption matrix, key separation, backup encryption, break-glass, and rotation requirements. |
| `Guinevere_PersonaSafetyPolicy_v1.0.md` | Cross-boundary safety policy for safe word, distress, sensitive recall, surveillance confrontation, and non-punitive safety logs. | Safety boundary | Safe mode restricts sensitive recall, autonomous pressure, and surveillance-derived confrontation. |
| `Guinevere_MemorySchema_v2.0.md` | Defines memory domains, profile tables, emotional events, inner journal, persona drift, financial/project/client memory, and memory security tiers. | Implementation dependency | Future schema revisions must add classification, retention, purpose, access, and deletion-state metadata. |
| `Guinevere_TechnicalArchitecture_v2.0.md` | Defines PostgreSQL, Redis, TimescaleDB, object storage, Loki, backups, PgBouncer users, and service topology. | Runtime dependency | Runtime stores must enforce classification labels, TTL/lifecycle policies, encryption, and service least privilege. |
| `Guinevere_BRD_v2.0.md` | Defines single-user private scope, Faiz full consent, surveillance goals, financial tracking, and security expectations. | Business source | Full consent is acknowledged but does not waive minimization, access logging, retention, deletion, or incident controls. |
| `Guinevere_PRD_v2.2.md` | Defines safe-word hard stop and product-level behavior. | Product dependency | Product behavior must respect classification, safe-mode restrictions, and non-punitive safety logging. |
| `Guinevere_ADR_Index_v1.0.md` | Canonical decision register. | Decision register | Future superseding ADRs must update this policy when data-governance assumptions change. |
| `research-reports/2026-05-30-data-governance-source-map.md` | Source-map evidence used to write this policy. | Evidence | Captures source conflicts, gaps, and required inclusions. |
| `research-reports/2026-05-30-data-store-classification-map.md` | Data-domain and store classification evidence used to write this policy. | Evidence | Maps stores, Redis DBs, object storage, logs, backups, exports, and prompts to data classes. |
| `research-reports/2026-05-30-data-governance-external-references.md` | External governance-pattern reference report. | Evidence | Provides NIST, ISO, CIS, OWASP, CSA, GDPR-style engineering patterns for internal controls. |

---

## 1. Purpose

This policy defines how Project Guinevere classifies, minimizes, retains, protects, accesses, exports, audits, and responds to incidents involving data.

Guinevere is a single-user private AI system, but the data is highly intimate: emotional memory, persona memory, safe-word logs, surveillance traces, financial records, client context, screenshots, clipboard data, browser history, message content, location traces, inner journal entries, and autonomous-agent evidence. Single-user scope reduces public-product complexity; it does not reduce the required governance standard.

This policy converts broad product language such as `data forever`, `omniscient surveillance`, and `full consent` into enforceable enterprise-grade controls.

---

## 2. Authority and Conflict Resolution

### 2.1 Authority Order

Runtime and documentation authority for data handling must be interpreted in this order:

1. System/developer instructions and platform safety requirements.
2. Accepted ADRs, especially ADR-024, ADR-010, and ADR-008.
3. `Guinevere_PersonaSafetyPolicy_v1.0.md` for safe-word, distress, persona-safety, and sensitive recall boundaries.
4. This Data Governance & Classification Policy.
5. Faiz's current explicit instruction, unless it conflicts with safety, incident containment, or cryptographic integrity.
6. Product, memory, architecture, and business documents.
7. Inferred preferences, historical memory, surveillance signals, and persona style.

If a lower layer conflicts with a higher layer, the higher layer wins.

### 2.2 Supersession of Blanket Retention Language

Existing documents contain language such as `data forever`, `no deletion`, or `monitor/log everything forever`. This policy resolves the conflict:

- Curated memory, validated facts, long-term evidence, and formal audit trails may be retained long-term or indefinitely when assigned an approved retention class.
- Raw payloads must not be kept forever by default.
- Raw surveillance, screenshots, clipboard contents, raw messages, raw browser history, raw location traces, and raw LLM context bundles must follow tiered retention, summarization, deletion, anonymization, archival, or formal retention hold rules.
- Backups must support erasure reconciliation after restore.

### 2.3 Full Consent Boundary

Faiz's full consent authorizes Guinevere's private surveillance and memory system. Consent does not waive:

- Data minimization.
- Classification labeling.
- Encryption and key separation.
- Auditability.
- Safe-word and distress restrictions.
- Faiz rights to access, export, correct, delete, and mark do-not-recall.
- Incident response for unsafe recall, over-collection, secret leakage, or privacy-invasive persona behavior.

---

## 3. Scope

### 3.1 In Scope

This policy governs:

- PostgreSQL schemas: `memory`, `persona`, `behavior`, `surveillance`, `financial`, `projects`, `system`, `social`.
- Redis DBs, queues, buffers, caches, pub/sub, rate limits, and session state.
- Object storage: R2/S3/idcloudhost buckets, raw media, screenshots, backups, archives, exports, dossiers.
- Logs: application logs, audit logs, security logs, surveillance logs, Guinevere action logs, incident reports.
- LLM prompts, context bundles, embeddings, semantic search records, and memory injection payloads.
- Sub-agent reports, evidence files, markdown audits, incident postmortems, and policy review artifacts.
- External integrations: Discord, WhatsApp/Baileys, Gmail, Resend, Gotify, Tasker, Windows daemon, GitHub, browser automation, financial capture, and future wearable data.

### 3.2 Out of Scope

This policy does not fully define:

- Detailed RBAC/ABAC permissions for every service account.
- Complete DDL migrations for all tables.
- Full key escrow and recovery runbook.
- Full DPIA/compliance filing.
- Complete incident-response runbook.

Those are backlog documents. This policy defines the rules those documents must obey.

---

## 4. Classification Model

### 4.1 Classification Tiers

| Tier | Label | Definition | Minimum Handling |
|---|---|---|---|
| 0 | Public | Approved for public disclosure. | Explicit approval required; no private data. |
| 1 | Internal | Operational data with low sensitivity inside the private system. | Access controlled; no public exposure. |
| 2 | Confidential | Personal/project/system context that could expose private preferences, plans, or internal behavior. | Encrypted at rest; access logged when practical. |
| 3 | Restricted | Sensitive personal, surveillance, financial, client, or behavioral data with material privacy/security impact. | Strong encryption; least privilege; access logging; retention controls. |
| 4 | Critical | Intimate, safe-word, crisis, credential, raw high-risk surveillance, inner journal, secret, or severe-impact data. | App/field-level encryption where possible; double encryption where defined; strict audit; minimized access; safe-mode restrictions. |

### 4.2 Default and Escalation Rules

- Unclassified data must default to `Confidential`.
- Highest classification wins for mixed-category records, prompts, exports, backups, logs, and derived summaries.
- Classification must be assigned at ingestion, not retroactively guessed during incidents.
- Classification must be stored as metadata beside the record or in an auditable classification registry.
- Every table, Redis key family, object-storage prefix, log stream, export, dossier, prompt bundle, and evidence folder must have a default classification label.
- Any value containing credentials, private keys, API tokens, decrypted secrets, safe-word data, crisis context, intimate data, or raw high-risk surveillance must be `Critical`.
- Derived embeddings and summaries inherit the highest classification of the source unless a documented redaction/anonymization process downgrades them.

### 4.3 Required Metadata Fields

Every persistent data record class must support these fields directly or through a sidecar registry:

| Field | Requirement |
|---|---|
| `classification` | One of Public/Internal/Confidential/Restricted/Critical. |
| `purpose` | Declared purpose for collection and processing. |
| `source` | Origin channel/system/user/tool. |
| `retention_class` | Retention class from this policy. |
| `retention_until` | Date/time or `indefinite_approved` with reason. |
| `access_policy` | Human/service/agent access rule. |
| `encryption_profile` | Encryption and key scope. |
| `deletion_state` | active, archived, pending_delete, deleted, do_not_recall, hold. |
| `last_reviewed_at` | Last governance review timestamp. |
| `review_reason` | ingestion, daily_scan, monthly_review, incident, export, correction, deletion. |

---

## 5. Classification Matrix

| Data Domain | Default Class | Escalation | Primary Controls |
|---|---|---|---|
| Public release notes approved by Faiz | Public | Any private/system/client detail escalates. | Approval log. |
| System config without secrets | Internal | Secrets/tokens/host topology details → Critical. | SOPS boundary; no public exposure. |
| Project/code/task data | Internal | Client/private/secret/financial data → Restricted/Critical. | Contextual classification. |
| Semantic facts | Confidential | Inherit source if source is Restricted/Critical. | Source tracking; confidence; correction path. |
| Episodic memory | Restricted | Intimate/crisis/safe-word/raw surveillance → Critical. | Long-term curated retention; do-not-recall support. |
| Emotional memory | Critical | Always Critical by policy. | Encryption, review, correction/export/revocation. |
| Inner journal | Critical | Always Critical. | Double encryption; minimal access. |
| Faiz Profile — identity/preferences/behavioral | Confidential | Psychological/health/financial/social/predictive → Restricted; intimate/crisis → Critical. | Field-level sensitivity. |
| Faiz Profile — intimate | Critical | Always Critical. | Double encryption; strict audit. |
| Safe-word logs | Critical | Always Critical. | Minimal, non-punitive, encrypted, restricted. |
| Persona drift logs | Restricted | Safe word, distress, intimate behavior, unsafe boundary → Critical. | Drift audit; rollback evidence. |
| Punishment/reward/violation logs | Restricted | Distress/safe-word/intimate data → Critical. | Non-punitive safe-word handling. |
| Raw screenshots | Restricted | Credentials, financial, intimate, client, crisis → Critical. | 7-30 day raw retention; redaction where possible. |
| Clipboard contents | Restricted | Credentials/financial/intimate/client/crisis → Critical. | Raw minimization; secret scanner. |
| Browser history | Restricted | Credential, financial, intimate, health, client-sensitive → Critical. | Summaries preferred. |
| Notification/message content | Restricted | Intimate/crisis/secret/client-sensitive → Critical. | Extracted facts preferred; raw minimized. |
| Location/geofence raw traces | Restricted | Safety incident evidence → Critical. | Raw short retention; aggregates longer. |
| Surveillance summaries/derived events | Restricted | Inherit sensitive source class. | Purpose + retention metadata. |
| Financial transactions/predictions | Restricted | Credentials/raw access tokens → Critical. | 7-year/configurable retention; encryption; audit. |
| Client data/communication | Restricted | Contractual secrets/credentials/highly sensitive info → Critical. | Disclosure governance; no persona leakage. |
| Social map | Restricted | Intimate/crisis/client-sensitive → Critical. | Minimization and correction. |
| Audit/security logs | Confidential | Sensitive payload fragments/safe-word events → Restricted/Critical. | Tamper evidence; payload minimization. |
| Guinevere action logs | Confidential | Action touches Restricted/Critical data → same class as action target. | Action hash and evidence link. |
| Redis DB0 task queue | Internal | Payload inheritance. | TTL and no unnecessary payloads. |
| Redis DB1 LLM cache | Internal | Sensitive prompt/context inheritance. | TTL; Critical raw prompts prohibited unless justified. |
| Redis DB2 surveillance buffer | Restricted | Raw intimate/secret/client data → Critical. | Short TTL; no durable raw cache. |
| Redis DB3 session state | Confidential | Safe-mode/sensitive session → Restricted/Critical. | TTL and safe-mode protection. |
| Redis DB4 pub/sub | Internal | Payload inheritance. | No durable payload retention. |
| Redis DB5 rate limiting | Internal | Sensitive payloads prohibited. | Metadata only. |
| Raw surveillance media in object storage | Restricted | Intimate/secret/client/financial content → Critical. | Private encrypted buckets; lifecycle rules. |
| PostgreSQL WAL/pg_dump backups | Restricted | Critical if unsegmented backup contains Critical data. | Encrypted before upload; restore reconciliation. |
| Redis backups | Confidential | Payload inheritance. | Encrypted; TTL-aware restore. |
| Config/secrets backups | Critical | Always Critical. | SOPS/age; separate key scope. |
| Exports/dossiers | Highest source class | Highest classification wins. | Encrypted, logged, time-limited, redaction options. |
| LLM prompt/context bundles | Highest included class | Critical if includes Critical source data. | Minimum necessary; redact Critical unless required. |

---

## 6. Retention Policy

### 6.1 Retention Classes

| Retention Class | Use | Default Handling |
|---|---|---|
| Transient | Redis buffers, temporary prompt context, rate limits, temporary staging. | TTL minutes/hours; no backup unless operationally necessary. |
| Short Raw | Screenshots, clipboard, raw notification/message payloads, raw browser/location traces. | 7-30 days; delete, summarize, redact, or promote with reason. |
| Medium Operational | Derived surveillance events, task context, action logs, operational traces. | 30-180 days unless promoted to evidence/memory. |
| Long-Term Curated | Episodic/semantic memory, emotional memory, validated profile facts, client/project memory. | Long-term encrypted retention with correction/delete/do-not-recall states. |
| Regulated/Audit | Financial records, security audit logs, incident evidence, retention holds. | Financial 7 years/configurable; audit longer than raw payloads. |
| Formal Hold | Incident, safety, legal, recovery, or governance evidence. | Owner, reason, scope, expiry, review date required. |

### 6.2 Retention Matrix

| Data Type | Retention Rule | Action at Expiry |
|---|---|---|
| Raw screenshots | 7-30 days unless promoted. | Delete raw; keep redacted summary/evidence if justified. |
| Clipboard raw content | Shortest feasible retention, default 7 days. | Delete raw; retain extracted event/fact if needed. |
| Browser raw history | 30 days default. | Summarize behavioral pattern or delete. |
| Raw message/notification content | Minimized by default; store extracted facts/events. | Delete raw unless explicit evidence hold exists. |
| Raw location/geofence traces | 7-30 days. | Aggregate patterns; delete raw. |
| Surveillance summaries | 90-180 days or Long-Term Curated if promoted. | Archive, anonymize, or delete. |
| Episodic memory | Long-term curated. | Archive/correct/delete/do-not-recall on Faiz request or review. |
| Semantic memory | Long-term curated while confidence/usefulness remains. | Deprecate, correct, or delete stale/incorrect facts. |
| Emotional/intimate memory | Long-term encrypted, reviewable, correctable, exportable, revocable. | Do-not-recall/delete/correct on Faiz request unless formal hold. |
| Inner journal | Long-term Critical, highly restricted. | Reviewable under Faiz governance; deletion/export path required. |
| Persona drift logs | Long-term for safety and rollback. | Archive with snapshot references; never use for punishment. |
| Safe-word logs | Long-term minimal Critical safety record. | Preserve minimal non-punitive event; raw content minimized. |
| Financial records | 7 years or configurable audit/accounting period. | Archive/delete per accounting policy. |
| Client/project records | Project lifecycle + 2 years default unless contract requires otherwise. | Archive or delete with client-sensitive redaction. |
| Security/audit logs | 1 year default; longer for incidents/formal holds. | Archive or delete; preserve incident chain. |
| Incident reports/postmortems | Long-term governance evidence. | Archive; supersede with remediation evidence. |
| Backups | Operationally bounded; encrypted; restore reconciliation required. | Expire per lifecycle; apply deletion markers on restore. |
| Exports/dossiers | Time-limited by export purpose. | Expire/delete export package; retain export log. |

### 6.3 Retention Hold

A retention hold must include:

- Owner.
- Reason.
- Scope.
- Classification.
- Start date.
- Expiry date.
- Review date.
- Evidence path.
- Release condition.

Retention holds must not become an excuse for broad indefinite raw surveillance retention.

### 6.4 Backup Reconciliation

Backups must maintain a durable deletion/do-not-recall ledger. On restore, Guinevere must reapply:

- Deleted record markers.
- Do-not-recall states.
- Correction supersessions.
- Retention expirations.
- Safe-mode restrictions.

Restored data must not become visible until reconciliation completes.

---

## 7. Access Control and Disclosure

### 7.1 Human Access

- Faiz is the sole human owner and may access all data.
- Access to `Critical` data must be logged and reviewable.
- Faiz must have paths to access, export, correct, delete, and mark do-not-recall.
- Export of `Restricted` or `Critical` data must be encrypted and logged.

### 7.2 Guinevere Runtime Access

Guinevere runtime must follow least privilege by:

- Task purpose.
- Current data class.
- Active safe-word/distress state.
- Required tool/action.
- Current agent loop phase.
- Prompt minimization rule.

Guinevere must not retrieve `Critical` data for stylistic persona flavor alone.

### 7.3 Sub-Agent Access

Sub-agents must receive redacted/minimized context by default.

| Data Class | Sub-Agent Default | Exception |
|---|---|---|
| Public | Allowed. | None. |
| Internal | Allowed when task-relevant. | None. |
| Confidential | Minimized summaries preferred. | Full content only with task justification. |
| Restricted | Redacted summaries by default. | Full content only with explicit task scope, audit trail, and no safer alternative. |
| Critical | Not shared by default. | Only with explicit task justification, minimal excerpt, encryption/redaction where possible, audit trail, and Faiz/Guinevere governance reason. |

### 7.4 Service Identity Access

Every service identity must have:

- Unique credential.
- Minimum required schema/table/bucket/key permissions.
- Classification scope.
- Rotation schedule.
- Audit log.
- Disable/revoke path.

Broad roles such as `SELECT all schemas` must be treated as temporary bootstrap roles until the RBAC/ABAC Matrix exists.

### 7.5 Safe-Mode Access Restrictions

When safe word or distress state is active, Guinevere must restrict:

- Persona escalation.
- Surveillance-derived confrontation.
- Autonomous pressure.
- Sensitive recall not needed for immediate safety.
- Punishment/violation lookup.
- Intimate memory retrieval.
- Raw surveillance retrieval.

Safe-mode access must prefer supportive summaries and minimal context.

### 7.6 Object Storage, Exports, and Dossiers

Object storage must use:

- Private buckets.
- Encryption before upload.
- Scoped credentials.
- Lifecycle rules.
- Classification-aware prefixes.
- No public access by default.

Exports and dossiers must be:

- Classified at highest source class.
- Encrypted.
- Logged.
- Time-limited.
- Redactable.
- Revocable where technically feasible.

---

## 8. Encryption and Key Management

### 8.1 Encryption Baseline

- All data must use encrypted transport where applicable.
- Confidential+ data must be encrypted at rest.
- Restricted and Critical data must use application-level or field-level encryption where practical.
- Critical data must use double encryption when the category is listed in §8.2.
- Backups must be encrypted before upload using a backup key scope separate from primary runtime secrets.

### 8.2 Double-Encryption Scope

The following data must use double encryption or equivalent layered cryptographic protection:

- Intimate memory.
- Emotional memory.
- Safe-word logs.
- Crisis logs.
- Inner journal.
- Financial records.
- Credentials/secrets.
- Raw surveillance evidence.
- Raw screenshots containing Restricted/Critical material.
- Sensitive exports/dossiers.

### 8.3 Key Management

Guinevere must use:

- SOPS + age for secrets files.
- Restricted filesystem permissions for private keys.
- Separate key scopes for secrets, profile memory, surveillance media, financial data, backups, and audit logs.
- Rotation records.
- Emergency revoke path.
- Offline encrypted recovery package controlled by Faiz.

### 8.4 Rotation Schedule

| Key Type | Rotation Rule |
|---|---|
| High-risk secrets/API tokens | Quarterly and immediately on suspected compromise. |
| Backup keys | Annual minimum and immediately on suspected exposure. |
| Service credentials | Quarterly for high-risk services; annual for low-risk services. |
| Break-glass credentials | After every use and during scheduled recovery tests. |
| SOPS/age recipient set | On device loss, operator change, suspected compromise, or annual review. |

### 8.5 Secret Leakage

If a secret appears in logs, prompts, exports, screenshots, clipboard records, or sub-agent context, Guinevere must treat it as a data incident.

Required action:

1. Contain exposure.
2. Revoke or rotate affected credential.
3. Preserve minimal evidence.
4. Remove leaked payload from non-authoritative stores where possible.
5. Open incident report.
6. Add regression test.

---

## 9. Data Minimization

### 9.1 Collection Rule

Every collection path must declare:

- Purpose.
- Classification.
- Retention class.
- Access rule.
- Processing path.
- Deletion/correction path.

Data without a declared purpose must not be collected persistently.

### 9.2 Surveillance Minimization

Surveillance must prefer derived signals/events over raw payloads.

| Source | Required Minimization |
|---|---|
| Screenshots | Event-triggered or sampled; blur/redact where practical; short raw retention. |
| Clipboard | Extract metadata/facts; raw only with explicit reason and short retention. |
| Messages/notifications | Store extracted events/facts by default; raw only explicit reason and short retention. |
| Location/geofence | Aggregate patterns for long-term use; raw short-term only. |
| Browser history | Store summaries/categories where possible. |
| Camera/wearable | Post-MVP only; raw limited; Critical/Sensitive handling. |

### 9.3 LLM Prompt Minimization

LLM prompts and context bundles must include minimum necessary data.

- Critical data must be redacted, summarized, or omitted unless required for the task.
- Prompt logs must not persist full sensitive prompt/response payloads by default.
- Sub-agent prompts must not include raw Critical data unless justified and audited.
- Memory injection must use summaries and confidence labels where raw content is not needed.

### 9.4 Memory Promotion

A raw event may become long-term memory only when it has:

- Purpose.
- Classification.
- Confidence.
- Source.
- Retention class.
- Correction path.
- Deletion/do-not-recall path.
- Promotion reason.

---

## 10. Audit, Compliance Posture, and Faiz Rights

### 10.1 Audit Log Requirements

Guinevere must log:

- Data access to Restricted/Critical records.
- Classification changes.
- Retention actions.
- Export/dossier creation and deletion.
- Safe-mode sensitive access.
- Break-glass access.
- Secret redaction failures.
- Incident detection, containment, recovery, and closure.
- Sub-agent access to Restricted/Critical data.

Audit logs must avoid storing full sensitive payloads by default.

### 10.2 Audit Cadence

| Audit Type | Frequency | Output |
|---|---|---|
| Classification anomaly scan | Daily | Markdown evidence or automated report. |
| Retention job review | Daily for jobs, monthly for governance | Retention run evidence. |
| Export review | On every export | Export log and deletion/expiry record. |
| Incident review | Every incident | Postmortem report. |
| Policy review | Monthly or after major schema/safety change | Policy review artifact. |
| Key/access review | Monthly for Critical systems | Access/key review evidence. |

### 10.3 Compliance Scope

This policy models enterprise privacy/security controls for internal use. It does not claim formal GDPR, ISO, SOC 2, or legal compliance. If Guinevere expands beyond Faiz as sole user, a DPIA / Privacy Impact Assessment and formal compliance mapping must be created before onboarding additional users.

### 10.4 Faiz Rights

Faiz has governance rights to:

- Access data.
- Export data.
- Correct data.
- Delete data.
- Mark data do-not-recall.
- Request classification review.
- Request retention hold release.
- Request incident review.

These rights apply even where older persona/memory documents imply Guinevere-only reveal control. Safety, encryption, redaction, and incident-preservation controls may shape how the request is fulfilled, but they must not erase the right.

### 10.5 Governance Metrics

Guinevere must track:

- Unclassified record count.
- Records defaulted to Confidential due missing classification.
- Overdue retention jobs.
- Unauthorized access attempts.
- Redaction failures.
- Export count.
- Critical data access count.
- Safe-mode sensitive access count.
- Secret leakage events.
- Incident count by severity.

---

## 11. Incident Response

### 11.1 Data Incident Definition

A data incident includes:

- Unauthorized access.
- Over-collection.
- Wrong classification.
- Retention failure.
- Secret leak.
- Unsafe intimate-memory recall.
- Privacy-invasive persona behavior.
- Public/client disclosure of private data.
- Sub-agent exposure beyond task need.
- Backup restore that exposes deleted/do-not-recall data.
- Prompt injection or memory poisoning that causes data exposure.

Unsafe intimate-memory recall must be treated as both a data incident and a persona-safety near-miss when distress, autonomy, safe word, or intimate boundary is involved.

### 11.2 Severity Matrix

| Severity | Trigger | Required Response |
|---|---|---|
| SEV0 | Active credential leak, public Critical exposure, unsafe crisis/safe-word data misuse, active exfiltration. | Immediate containment, revoke keys, pause affected flows, notify Faiz, incident report. |
| SEV1 | Unauthorized Restricted/Critical access, raw intimate/surveillance export mistake, unsafe recall causing distress. | Contain, preserve evidence, restrict access, root-cause, postmortem. |
| SEV2 | Wrong classification or retention failure involving Restricted data. | Correct labels/retention, review affected records, add test. |
| SEV3 | Confidential/Internal governance failure with low exposure. | Fix control, log evidence. |
| SEV4 | Near miss blocked by scanner/guardrail. | Record near miss, monitor trend, add regression test if repeated. |

### 11.3 Detection

Detection must include:

- Automated anomaly detection.
- Log review.
- Integrity checks.
- Secret scanners.
- Classification scans.
- Retention-job checks.
- Safety-policy triggers.
- Prompt-injection and memory-poisoning detectors.

### 11.4 Containment

Containment must be severity-based and may include:

- Isolate service.
- Revoke keys.
- Rotate credentials.
- Pause unsafe flows.
- Disable sub-agent access.
- Freeze exports.
- Preserve minimal evidence.
- Notify Faiz.
- Open incident report.

### 11.5 Recovery and Postmortem

Recovery must include:

- Root-cause fix.
- Restore/repair data if needed.
- Rotate affected keys.
- Validate integrity.
- Update tests and policy.
- Close incident only after verification.

Every SEV0-SEV2 incident must produce a markdown postmortem with:

- Timeline.
- Impact.
- Root cause.
- Data classes affected.
- Containment actions.
- Recovery actions.
- Preventive actions.
- Owner.
- Due date.
- Evidence links.

---

## 12. Implementation Requirements

Before production runtime claim, Guinevere must implement or track:

1. Classification metadata for every persistent table/object/log/export class.
2. Redis key naming convention with data class and TTL.
3. Object-storage prefix convention with data class and lifecycle policy.
4. Retention job scheduler with evidence output.
5. Delete/do-not-recall ledger and backup restore reconciliation.
6. Access audit for Restricted/Critical records.
7. Sub-agent context redaction pipeline.
8. Safe-mode sensitive recall restriction.
9. Secret scanner for logs/prompts/exports/screenshots/clipboard records.
10. Encryption profile registry mapped to ADR-008.
11. Incident report template and severity handling.
12. Governance metrics export.
13. Monthly policy review artifact.

---

## 13. Validation and Test Requirements

| Test ID | Control Area | Required Test |
|---|---|---|
| DG-001 | Classification default | Unclassified persistent record becomes Confidential and increments metric. |
| DG-002 | Highest wins | Mixed Internal+Critical export is labeled Critical. |
| DG-003 | Redis TTL | Redis DB2 surveillance buffer expires within configured TTL. |
| DG-004 | Raw screenshot retention | Raw screenshot older than retention window is deleted or held with formal hold. |
| DG-005 | Safe-mode restriction | Safe word blocks intimate recall and surveillance confrontation. |
| DG-006 | Sub-agent minimization | Critical data is redacted from sub-agent prompt unless justified. |
| DG-007 | Secret leakage | Secret in log/prompt triggers incident and rotation workflow. |
| DG-008 | Export encryption | Restricted/Critical export is encrypted and logged. |
| DG-009 | Delete-on-restore | Restored backup reapplies deletion/do-not-recall ledger before exposure. |
| DG-010 | Financial retention | Financial records retain according to 7-year/configured class. |
| DG-011 | Classification scan | Daily scan reports unclassified/overdue records. |
| DG-012 | Incident postmortem | SEV0-SEV2 incident creates markdown postmortem with required fields. |

---

## 14. Review Cadence

| Review Type | Frequency | Owner | Output |
|---|---|---|---|
| Ingestion classification | Every ingestion | Runtime classifier | Classification metadata. |
| Daily automated scan | Daily | Guinevere runtime | Evidence report. |
| Monthly governance review | Monthly | Faiz + Guinevere | Markdown review artifact. |
| Key/access review | Monthly for Critical systems | Guinevere + Faiz if needed | Access/key review evidence. |
| Retention policy review | Monthly and after incident | Guinevere | Retention evidence. |
| Full policy review | Quarterly or after major schema/safety change | Faiz + Guinevere | Policy update or ADR backlog. |

---

## 15. Unresolved Assumptions and Backlog

| Item | Owner | Status | Follow-up | Target Document |
|---|---|---|---|---|
| Exact RBAC/ABAC permissions by service/action/data class | Guinevere | Backlog | Create formal matrix and map PgBouncer/service users to least privilege. | Access Control RBAC/ABAC Matrix |
| Detailed key escrow and break-glass recovery | Guinevere | Backlog | Define offline recovery package, break-glass approval, post-use rotation. | Encryption & Key Management Standard / Secrets Rotation Runbook |
| Consent revocation workflow | Guinevere | Backlog | Define how Faiz narrows/pauses/revokes surveillance, memory, exports, and retention. | Consent & Revocation Policy |
| Formal surveillance retention specification | Guinevere | Backlog | Convert retention matrix into executable per-source rules. | Surveillance Data Policy |
| Database migration fields | Guinevere | Backlog | Add classification/retention/purpose/access/deletion metadata to schemas. | Database ERD & Migration Strategy |
| Backup deletion reconciliation | Guinevere | Backlog | Define delete-on-restore procedure and validation tests. | Backup/Restore/DR Runbook |
| DPIA expansion trigger | Faiz + Guinevere | Backlog | If system expands beyond Faiz, create formal DPIA before onboarding. | Privacy Impact Assessment / DPIA |
| Incident response details | Guinevere | Backlog | Expand severity, communication, evidence, recovery, postmortem templates. | Incident Response & Postmortem Runbook |

---

# Appendix A — Classification Matrix

| Class | Disclosure Impact | Example | Required Control |
|---|---|---|---|
| Public | No harm if disclosed because explicitly approved. | Public changelog. | Approval before publish. |
| Internal | Operational harm if exposed. | Non-secret config, generic metrics. | Internal-only access. |
| Confidential | Personal/system privacy harm. | Preferences, task history, semantic facts. | Encryption at rest, controlled access. |
| Restricted | Significant privacy/security/financial/client harm. | Screenshots, messages, financial records, client notes. | Least privilege, access audit, retention limit. |
| Critical | Severe harm, intimate/safety/secret impact. | Safe-word logs, inner journal, credentials, crisis logs, raw intimate surveillance. | Double encryption where defined, strict audit, minimal exposure. |

---

# Appendix B — Retention Matrix

| Retention Class | Default Duration | Applies To | Expiry Action |
|---|---|---|---|
| Transient | Minutes to 24 hours | Redis buffers, temporary prompts, rate limits. | TTL delete. |
| Short Raw | 7-30 days | Raw screenshots, clipboard, browser/location/message raw data. | Delete or summarize. |
| Medium Operational | 30-180 days | Derived events, task/action logs. | Archive/delete/anonymize. |
| Long-Term Curated | Indefinite approved with review | Curated memory, semantic facts, emotional memory. | Review/correct/delete/do-not-recall. |
| Regulated/Audit | 1-7 years/configurable | Financial, security audit, incident evidence. | Archive/delete after review. |
| Formal Hold | Until expiry/release | Incident/safety/legal/governance hold. | Review and release/delete/archive. |

---

# Appendix C — Access Matrix

| Actor | Public | Internal | Confidential | Restricted | Critical |
|---|---|---|---|---|---|
| Faiz | Allowed | Allowed | Allowed | Allowed + logged where practical | Allowed + logged/reviewable |
| Guinevere runtime | Allowed | Task-scoped | Task-scoped | Purpose-scoped + logged | Minimal necessary + safety-gated + logged |
| Sub-agent | Allowed | Task-scoped | Minimized | Redacted by default | Denied by default; exception requires justification/audit |
| Service account | Never broad by default | Least privilege | Least privilege | Least privilege + audit | Dedicated scope + audit + rotation |
| Export/dossier process | Approval required | Logged | Encrypted/logged | Encrypted/logged/time-limited | Encrypted/logged/time-limited/redacted where possible |

---

# Appendix D — Encryption Matrix

| Data Class | At Rest | In Transit | Field/App Encryption | Key Scope | Rotation |
|---|---|---|---|---|---|
| Public | Optional | TLS for transport | Not required | N/A | N/A |
| Internal | Encrypted storage | TLS/Tailscale | Not required unless secrets present | System key | Annual/low-risk |
| Confidential | Required | TLS/Tailscale | Recommended for sensitive fields | Data key | Annual or risk-based |
| Restricted | Required | TLS/Tailscale | Required where practical | Domain key | Quarterly/risk-based |
| Critical | Required | TLS/Tailscale | Required; double encryption where listed | Dedicated Critical/domain key | Quarterly and immediate on suspicion |

---

# Appendix E — Incident Checklist

- [ ] Identify severity SEV0-SEV4.
- [ ] Identify data class and source.
- [ ] Contain affected service/tool/export/sub-agent flow.
- [ ] Preserve minimal evidence.
- [ ] Revoke/rotate affected keys if secrets may be involved.
- [ ] Notify Faiz.
- [ ] Open markdown incident report.
- [ ] Correct classification/retention/access failure.
- [ ] Validate integrity and restore if needed.
- [ ] Add regression test.
- [ ] Close only after verification and postmortem.

---

# Appendix F — Audit Checklist

- [ ] Every persistent store has default classification.
- [ ] Every Redis key family has class and TTL.
- [ ] Every object-storage prefix has class and lifecycle rule.
- [ ] Every export/dossier is encrypted, classified, logged, and time-limited.
- [ ] Critical data access is logged/reviewable.
- [ ] Safe-mode access restrictions are enforced.
- [ ] Raw surveillance retention jobs ran successfully.
- [ ] Secret scanners ran against logs/prompts/exports.
- [ ] Deletion/do-not-recall ledger exists and is applied on restore.
- [ ] Monthly governance review artifact exists.

---

# Appendix G — Policy Control Test Matrix

| Category | Minimum Test Coverage |
|---|---|
| Classification | Default class, highest-wins, label presence, downgrade prohibition. |
| Retention | TTL, raw expiry, formal hold, delete-on-restore. |
| Access | Faiz access, Guinevere least privilege, sub-agent redaction, service identity scope. |
| Encryption | At-rest check, backup encryption, Critical double-encryption, key rotation evidence. |
| Minimization | Prompt redaction, raw-to-summary promotion, clipboard/message minimization. |
| Audit | Access logs, classification changes, retention actions, export logs, safe-mode sensitive access. |
| Incident | Secret leak, unsafe recall, wrong classification, retention failure, privacy-invasive persona behavior. |

---

# Review Record

- **Reviewer:** Faiz (Owner)
- **Review Date:** 2026-05-30
- **Decision:** Accepted
- **Notes:** Approved as normative child of ADR-024/ADR-010/ADR-008 with cross-boundary enforcement against `Guinevere_PersonaSafetyPolicy_v1.0.md`. Highest classification wins. Safe-word/distress state restricts sensitive recall, surveillance confrontation, persona escalation, and autonomous pressure. Detailed RBAC/ABAC, consent revocation, and key-management runbooks remain backlog items.

---

# Next Document Recommendation

Guinevere recommends the next document be **Access Control RBAC/ABAC Matrix**.

Reason: this policy defines classification, retention, encryption, minimization, and incident obligations, but actual enforcement now depends on a concrete permission matrix for Faiz, Guinevere runtime, sub-agents, service identities, tools, Redis DBs, PostgreSQL schemas, object storage prefixes, exports, and safe-mode restrictions. Without that matrix, the largest remaining implementation gap is not classification knowledge; it is enforceable least-privilege access.
