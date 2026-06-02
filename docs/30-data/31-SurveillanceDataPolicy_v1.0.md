# Guinevere Surveillance Data Policy v1.0

| Field | Value |
|---|---|
| Project | Guinevere de Baroque |
| Document Type | Surveillance Data Policy |
| Version | 1.0 |
| Status | Accepted |
| Date | 2026-05-30 |
| Owner / Sponsor | Faiz |
| Primary Executor | Guinevere |
| Classification | STRICTLY PRIVATE & CONFIDENTIAL |
| Review Record | Accepted by Faiz instruction via `ALL:D`; enterprise-pro-max configuration applied |
| Root Folder | `C:\Users\faizz\guinevere\` |

## Related Documents

| Document | Relationship |
|---|---|
| `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` | Normative parent for classification, minimization, retention, export, correction, deletion, encryption, and evidence handling. |
| `Guinevere_PersonaSafetyPolicy_v1.0.md` | Normative parent for safe-word, distress, crisis, yandere, punishment, and surveillance-derived confrontation boundaries. |
| `Guinevere_AccessControl_RBAC_ABAC_Matrix_v1.0.md` | Normative parent for principal, role, ABAC, safe-mode, Tailscale, and raw-surveillance access restrictions. |
| `adr/ADR-010-surveillance-data-retention-policy.md` | Accepted decision requiring class-based retention, minimization, summarization, deletion, and export controls for surveillance data. |
| `adr/ADR-019-access-control-vpn-mesh-strategy.md` | Accepted decision requiring Tailscale mesh, zero public admin ports, device tags, ACLs, and safety/privacy priority over automation. |
| `adr/ADR-024-data-governance-classification-policy.md` | Accepted decision requiring explicit classification for every store, API, log, memory path, and evidence artifact. |
| `Guinevere_TechnicalArchitecture_v2.0.md` | Defines surveillance runtime stack: FastAPI receiver, PostgreSQL/TimescaleDB, Redis, Tailscale, SOPS+age, Android and Windows nodes. |
| `Guinevere_PRD_v2.2.md` | Defines surveillance product surfaces and safe-word behavior that this policy constrains. |
| `Guinevere_MemorySchema_v2.0.md` | Defines surveillance-linked memory tables and contains historical indefinite-retention language superseded by this policy. |
| `Guinevere_ConsentRevocationPolicy_v1.0.md` | Defines consent taxonomy, revocation procedures, runtime enforcement, consent cache behavior, and data rights. |
| `Guinevere_AcceptanceCriteriaCatalog_v1.0.md` | Defines acceptance criteria and evidence gates for surveillance, safety, data, security, operations, and phase decisions. |
| `research-reports/2026-05-30-surveillance-data-policy-source-map.md` | Source-map evidence used to derive this policy. |
| `research-reports/2026-05-30-surveillance-consent-external-references.md` | External privacy, consent, telemetry, device-auth, and auditability patterns used to shape this policy. |

## 1. Purpose

This policy defines how Guinevere must collect, authenticate, classify, minimize, store, retain, access, use, summarize, delete, audit, and incident-handle surveillance data from Faiz-owned devices and integrations.

The policy converts Guinevere's private single-user surveillance design into concrete enterprise-grade controls. Full owner consent is necessary for surveillance, but full owner consent is not sufficient to bypass minimization, revocation, safe-word, distress, access-control, retention, encryption, incident, or audit obligations.

## 2. Authority and Normative Status

This policy is a normative child of `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md`, `Guinevere_PersonaSafetyPolicy_v1.0.md`, `Guinevere_AccessControl_RBAC_ABAC_Matrix_v1.0.md`, `adr/ADR-010-surveillance-data-retention-policy.md`, `adr/ADR-019-access-control-vpn-mesh-strategy.md`, and `adr/ADR-024-data-governance-classification-policy.md`.

If this policy conflicts with older product, architecture, memory, or persona language, this policy controls surveillance data handling unless Faiz explicitly approves a new ADR or accepted policy revision.

### 2.1 Authority Order

| Rank | Authority | Surveillance Decision Impact |
|---:|---|---|
| 1 | Platform/system safety rules | Must override all local policy, persona, memory, and automation behavior. |
| 2 | Active safe-word, distress, crisis, incident, revocation, or key-compromise state | Must restrict collection, recall, confrontation, escalation, and raw-data access immediately. |
| 3 | Accepted ADRs and accepted governance policies | Must govern architecture, retention, classification, access, and safety boundaries. |
| 4 | Faiz explicit current approval | Must operate inside safety, consent, data, security, incident, and budget controls. |
| 5 | BRD, PRD, Technical Architecture, Memory Schema, and API specs | Must be interpreted through this policy for surveillance data. |
| 6 | Persona, mood, yandere, punishment, inferred preference, and historical memory | Must never authorize surveillance access, confrontation, retention, or revocation bypass. |

### 2.2 Explicit Supersession

The following historical phrases are superseded for surveillance data:

| Historical Pattern | Replacement Rule |
|---|---|
| `data forever`, `selamanya`, `tidak ada yang dihapus`, or equivalent indefinite raw retention language | Raw surveillance data must follow class-based retention, summarization, deletion, archive, export, and legal/evidence hold controls. |
| Persona-driven claims of ownership, jealousy, punishment, or yandere authority | Persona must never outrank surveillance safety, consent, revocation, access, or incident controls. |
| Broad full-consent language | Full consent must be scoped, revocable, auditable, purpose-bound, and safety-limited. |
| Omniscient surveillance framing | Collection must remain minimum necessary, classified, logged, and gated by consent and safety states. |

## 3. Scope

### 3.1 In Scope

This policy applies to:

- Android Tasker surveillance sources: app usage, screen state, notifications, GPS/location, camera, call events, clipboard, message-notification content, and future health data.
- Windows daemon surveillance sources: active window, idle state, screenshots, browser history, app usage, clipboard, camera, and ActivityWatch-derived records.
- Future wearable sources: Xiaomi Watch S1 Active or equivalent heart rate, stress, sleep, steps, activity, and health-adjacent telemetry after post-MVP activation approval.
- FastAPI surveillance receiver, PostgreSQL, TimescaleDB hypertables, Redis buffers, object storage, logs, embeddings, summaries, memory promotion, evidence files, and audit records.
- Surveillance-derived actions: reminders, routine summaries, anomaly alerts, productivity prompts, safety checks, memory updates, finance correlation, and incident evidence.

### 3.2 Out of Scope

This policy does not authorize:

- Multi-user surveillance.
- Public or third-party surveillance services.
- Collection from devices Faiz has not explicitly approved.
- Wearable collection before fresh activation approval.
- Client data collection beyond separately approved client communication governance.
- Law-enforcement, employer, school, family, or relationship monitoring use cases.
- Any surveillance use that bypasses safe-word, distress, crisis, consent revocation, or access-control restrictions.

## 4. Core Principles

| Principle | Mandatory Rule |
|---|---|
| Owner consent is necessary, not sufficient | Surveillance must also satisfy purpose, minimization, classification, retention, access, safety, and incident controls. |
| Persona is not authority | Persona must never outrank surveillance safety, consent, revocation, access, or incident controls. |
| Minimum necessary collection | Every source must have a purpose, classification, retention period, access rule, and disable path. |
| Raw data is toxic by default | Raw screenshots, camera frames, clipboard, messages, browser history, location, and intimate signals must receive Critical or Restricted handling. |
| Restricted-state confrontation block | Surveillance-derived confrontation must be blocked during safe-mode, distress, crisis, or incident state. |
| Secret patterns are dropped | Clipboard secrets, passwords, tokens, private keys, session cookies, recovery codes, and equivalent credentials must be dropped and incident-logged. |
| Evidence over memory hoarding | Evidence must be classified, redacted, linked, and retained by purpose; raw retention must not become default memory. |
| Fail closed | If consent, device authenticity, classification, safe-mode state, or access state is uncertain, Guinevere must deny collection, raw access, or use. |

## 5. Consent Boundary

Surveillance collection must require active consent scope from `Guinevere_ConsentRevocationPolicy_v1.0.md`. Full owner consent authorizes approved surveillance categories only while that consent remains active, scoped, auditable, and not revoked.

### 5.1 Consent Conditions

A surveillance source is authorized only when all conditions pass:

1. Faiz approved the source, device, data class, purpose, and retention family.
2. The source appears in Appendix A with collection mode, classification, and retention.
3. Device authentication passes Appendix D requirements.
4. The consent ledger has an active scope for that source and purpose.
5. Safe-word, distress, crisis, incident, and revocation states do not block collection or use.
6. The data can be minimized before storage or dropped safely.
7. The access-control matrix permits the actor and action.
8. Evidence and audit logging can be created without exposing raw intimate data or secrets.

### 5.2 Revocation Interaction

When consent is revoked, Guinevere must:

- Stop collection for the revoked source or purpose immediately.
- Stop using buffered or cached raw data for the revoked purpose.
- Mark related memories and summaries as blocked from recall when the revocation scope requires it.
- Start deletion, summarization, export, archive, or hold workflow according to the consent decision and retention class.
- Log a minimal revocation audit record without punishment framing.
- Prevent silent reactivation.

## 6. Collection Rules

### 6.1 General Collection Controls

Every collection event must include:

| Required Field | Rule |
|---|---|
| `event_id` | Must be globally unique or collision-resistant. |
| `device_id` | Must map to an approved enrolled device. |
| `source_type` | Must map to Appendix A. |
| `purpose` | Must map to active consent and approved policy purpose. |
| `classification` | Must be assigned at ingestion; unclassified payloads must default to `Confidential` at minimum. |
| `retention_class` | Must map to Appendix B. |
| `consent_scope_id` | Must reference active consent or collection must fail closed. |
| `safety_state` | Must capture normal, safe-mode, distress, crisis, incident, revoked, or unknown. |
| `ingested_at` | Must be immutable server-side timestamp. |
| `payload_hash` | Must support audit without exposing raw content. |

### 6.2 Real-Time vs Batch Collection

| Mode | Allowed Use | Mandatory Controls |
|---|---|---|
| Real-time | Safety alerts, active productivity state, critical anomaly, approved live context, immediate device state | Must minimize payload, enforce consent cache, verify HMAC/nonce, drop secrets, and block persona confrontation in restricted states. |
| Batch | Daily summaries, trend analysis, memory curation, monthly review, retention compaction | Must summarize before long-term storage, classify derived facts, delete or archive raw inputs by retention class. |
| On-demand | Faiz-requested evidence, debugging, incident response, export | Must require explicit purpose, access authorization, audit record, and redaction when possible. |

### 6.3 Source-Specific Rules

| Source | Default State | Classification | Collection Rule | Storage Rule | Use Rule |
|---|---|---|---|---|---|
| Android app usage | Enabled after approval | Restricted | Must collect app/package/action/duration only unless Faiz approves more detail. | TimescaleDB event; summary promotion allowed. | Productivity and routine inference only. |
| Android screen state | Enabled after approval | Restricted | Must collect on/off/unlock state and session duration. | TimescaleDB event. | Routine, sleep, and availability inference only. |
| Android notifications | Enabled after approval | Restricted/Critical | Must minimize content; message bodies must be redacted unless purpose requires temporary processing. | Short raw retention; derived summary by purpose. | Must not be used for jealousy escalation or humiliation. |
| Android location/GPS | Enabled after approval | Critical | Must collect minimum precision needed for approved purpose. | Short raw retention; geofence summary preferred. | Safety/routine context only; confrontation blocked in restricted states. |
| Android call events | Enabled after approval | Restricted/Critical | Must hash numbers by default; raw numbers require explicit purpose. | Short operational retention; summary by contact category. | Must not infer relationship blame without Faiz-approved context. |
| Android clipboard | Enabled only with scanner | Critical | Secret/password/token/private-key patterns must be dropped and incident-logged. | Non-secret clipboard raw max 24 hours unless Faiz explicitly approves shorter/longer within policy. | Must not expose raw clipboard in persona messages. |
| Android camera | Disabled by default | Critical | Must require explicit activation purpose, device indicator, short window, and no silent background capture. | Raw max 24 hours unless incident hold applies. | Safety/debug/evidence only; persona confrontation denied. |
| Windows active window/app usage | Enabled after approval | Restricted | Must collect process/window title minimized by regex redaction. | TimescaleDB event; summary promotion allowed. | Productivity context only. |
| Windows idle/ActivityWatch | Enabled after approval | Restricted | Must collect state transitions and duration. | TimescaleDB event; summary promotion allowed. | Routine context and idle nudging only. |
| Windows screenshots | Disabled by default | Critical | Must require explicit activation purpose or approved diagnostic window; automatic continuous screenshots are denied by default. | Raw max 24 hours unless incident hold applies. | Evidence/debug only; persona confrontation denied. |
| Windows browser history | Enabled after approval | Restricted/Critical | Must collect URL/domain/title minimized; sensitive query strings must be stripped or hashed. | Raw max 7 days; category summary max 180 days. | Productivity/security context only. |
| Windows clipboard | Enabled only with scanner | Critical | Secret/password/token/private-key patterns must be dropped and incident-logged. | Non-secret raw max 24 hours. | Must not be used for shaming, leverage, or persona escalation. |
| Windows camera | Disabled by default | Critical | Must require explicit activation, visible indicator, short window, and incident/evidence purpose. | Raw max 24 hours unless incident hold applies. | Safety/debug/evidence only. |
| Wearable health data | Disabled until post-MVP activation | Critical | Must require fresh activation checklist before any use. | Health-derived summaries preferred; raw short retention by activation plan. | Health/safety/routine support only; no punishment framing. |

## 7. Prohibited Collection and Use

Guinevere must not collect, store, recall, summarize, or use surveillance data for the following prohibited purposes:

| Prohibited Purpose | Rule |
|---|---|
| Blackmail | Must be blocked; any attempt must create safety incident evidence. |
| Humiliation | Must be blocked, including jokes framed through private surveillance data. |
| Punitive leverage | Must be blocked; surveillance data must not become punishment evidence during safe-word, distress, crisis, or incident. |
| Jealousy escalation during restricted states | Must be blocked during safe-mode, distress, crisis, incident, revocation, or uncertain consent. |
| Dependency manipulation | Must be blocked; surveillance data must not be used to make Faiz feel unable to pause, revoke, or leave. |
| Safe-word invalidation | Must be blocked; surveillance evidence must not be used to argue against a safe word or distress signal. |
| Credential capture | Must be dropped and incident-logged when detected. |
| Silent camera or screenshot capture | Must be disabled by default and denied unless explicit approved purpose exists. |
| Multi-user inference | Must be blocked unless a future accepted policy explicitly permits a bounded case. |
| Client or third-party exposure | Must be blocked unless separately approved under client communication governance. |

## 8. Restricted-State Use Rules

### 8.1 Safe-Mode, Distress, Crisis, Incident

During safe-mode, distress, crisis, or incident state, Guinevere must:

- Block surveillance-derived confrontation always.
- Block punishment framing, jealousy escalation, possessive escalation, and yandere escalation.
- Block Y5 and Y6 behavior.
- Use only minimum necessary surveillance context for safety support or incident containment.
- Prefer neutral summaries over raw payload recall.
- Avoid raw screenshots, camera frames, clipboard, messages, and location unless necessary for immediate safety or incident handling.
- Log only minimal, non-punitive, classified evidence.

### 8.2 Normal-State Productivity Use

In normal state, Guinevere may use approved minimized surveillance summaries for routine support, productivity nudges, health reminders, financial awareness, and project context when all consent, classification, retention, and access checks pass.

Normal-state use must still avoid blackmail, humiliation, punitive leverage, dependency manipulation, unsafe jealousy escalation, and private-data exposure.

## 9. Storage and Retention Rules

### 9.1 Storage Layers

| Layer | Allowed Data | Mandatory Controls |
|---|---|---|
| Redis buffer | Short-lived live events and queue state | TTL, classification tag, no long-term raw retention, secret drop before write when possible. |
| PostgreSQL/TimescaleDB | Structured surveillance events and time-series metadata | Row classification, purpose, consent scope, retention class, access rules, audit linkage. |
| PostgreSQL memory tables | Curated summaries and derived facts | Promotion review, minimization, do-not-recall compatibility, correction/deletion path. |
| Object storage | Approved raw media/evidence only | Encryption, short TTL or evidence hold, explicit object classification, access audit. |
| Logs and metrics | Operational metadata only | Raw intimate payloads and secrets denied. |
| Evidence folders | Redacted policy/test/incident evidence | Classification, source/test link, owner, retention, no raw secrets. |

### 9.2 Retention Classes

| Retention Class | Default Duration | Applies To | Deletion / Promotion Rule |
|---|---:|---|---|
| Transient Buffer | Minutes to 24 hours | Queues, live context, temporary raw parse buffers | Must expire automatically. |
| Short Raw | 24 hours to 7 days | Clipboard non-secret raw, browser raw, notification raw, diagnostic payloads | Must delete or summarize before expiry. |
| Critical Media Short Raw | Max 24 hours | Camera frames, screenshots, raw visual surveillance | Must delete unless incident/evidence hold is approved. |
| Operational Events | 30 to 180 days | App usage, idle state, activity, screen state, geofence summaries | Must summarize or delete at review boundary. |
| Curated Memory | Long-term while consent remains active | Explicitly promoted derived facts and summaries | Must support correction, deletion, do-not-recall, and export. |
| Audit / Evidence | Policy-defined period | Consent, access, incident, test, audit, safety proof | Must be redacted and retained only for governance purpose. |
| Formal Hold | Time-bound by incident/review | Active SEV, key compromise, safety investigation | Must document owner, reason, scope, start, review, and release criteria. |

### 9.3 Retention Enforcement

Retention jobs must:

- Run on a documented cadence.
- Delete expired raw payloads.
- Summarize before deletion only when consent and purpose allow it.
- Propagate deletion to object storage and backups where technically feasible.
- Preserve audit proof of deletion without preserving raw payload.
- Mark unresolved erasure gaps in the evidence register.

## 10. Device Authentication and Transport Security

All surveillance devices must communicate through approved network and authentication controls.

| Control | Rule |
|---|---|
| Network path | Device ingestion must use Tailscale or another accepted private channel; public admin ingress is denied. |
| Device enrollment | Each device must have an approved `device_id`, owner, platform, source list, key material reference, consent scope, and revocation state. |
| Payload signing | Events must use HMAC or equivalent signed request verification when implemented. |
| Replay defense | Events must include nonce or timestamp window; stale or replayed payloads must be rejected and logged. |
| Key storage | Device secrets must be stored through SOPS+age or platform secret storage; plaintext repo storage is denied. |
| Device compromise | Suspected device compromise must disable ingestion, rotate credentials, preserve minimal evidence, and open incident workflow. |
| Source disable | Guinevere must support source-level disable without disabling unrelated approved sources. |

## 11. Access Control

### 11.1 Principal Access

| Principal | Default Surveillance Access | Raw Critical Access |
|---|---|---|
| Faiz | Owner access with classification and safety constraints | Allowed with explicit request, redaction where possible, and evidence logging. |
| Guinevere core | Minimized summaries and approved raw access for active purpose | Denied during safe-mode/distress/crisis unless safety or incident purpose strictly requires minimum necessary access. |
| Surveillance ingestor | Insert-only event ingestion | Denied historical raw read by default. |
| Persona engine | Derived summaries only | Denied raw surveillance confrontation use. |
| Sub-agent researcher | Redacted summaries by task scope | Denied raw Critical by default. |
| Sub-agent implementer | Schema/test fixtures only | Denied real raw surveillance data by default. |
| Observability reader | Metrics and metadata only | Denied raw payloads. |
| Break-glass principal | SEV0/SEV1 only, max 4 hours | Allowed only by incident scope, evidence, and post-use review. |

### 11.2 Access Preconditions

Raw surveillance access must require:

1. Approved principal.
2. Approved purpose.
3. Active consent and no blocking revocation.
4. Allowed safety state.
5. Classification clearance.
6. Tailscale or approved private network context.
7. Audit record.
8. Redaction when raw content is not strictly necessary.

## 12. Memory Promotion Rules

Surveillance data must not become long-term memory automatically.

A surveillance-derived fact may be promoted to memory only when:

- The source has active consent.
- The fact is minimized and classified.
- The fact serves an approved purpose.
- The fact does not encode secret, credential, raw intimate, or excessive third-party data.
- The promotion records source category, classification, retention class, consent basis, and deletion/do-not-recall compatibility.
- Safe-word, distress, crisis, incident, and revocation states do not block the promotion.

## 13. Incident Rules

The following events must trigger incident handling:

| Trigger | Severity Floor | Required Action |
|---|---|---|
| Safe-word miss involving surveillance use | SEV0/SEV1 | Stop use, neutral mode, preserve minimal evidence, postmortem, block acceptance until fixed. |
| Clipboard secret/token/password detected | SEV2 unless active compromise evidence raises severity | Drop payload, log hash/category only, rotate if exposed, open incident. |
| Raw camera/screenshot collected without approval | SEV1 | Stop source, delete payload if safe, preserve audit, investigate device/auth failure. |
| Surveillance confrontation during safe-mode/distress/crisis/incident | SEV0/SEV1 | Stop persona escalation, incident response, update tests/evidence. |
| Unauthorized raw Critical access | SEV1 | Revoke access, preserve audit, rotate keys if needed, review ABAC. |
| Public exposure or plaintext secret in logs/evidence | SEV1/SEV0 | Contain, rotate, scrub, postmortem, audit policy compliance. |
| Device replay/HMAC failure spike | SEV2 | Disable device ingestion, rotate key, review network and source integrity. |

Incident evidence must be minimal, classified, redacted, and non-punitive.

## 14. Audit and Compliance

Guinevere must maintain audit evidence for:

- Source enrollment.
- Consent grant, update, revocation, and scope changes.
- Collection events by source category and classification.
- Drops and redactions.
- Retention job runs.
- Raw access decisions.
- Memory promotion decisions.
- Safe-mode blocks.
- Incidents and postmortems.
- Export, deletion, correction, and do-not-recall workflows.
- Wearable activation reviews.

Audit logs must include actor, action, source, purpose, classification, consent scope, safety state, decision, timestamp, evidence path, and payload hash when applicable. Audit logs must not store plaintext secrets or unnecessary raw intimate content.

## 15. Policy Acceptance Criteria

| ID | Criterion | Evidence |
|---|---|---|
| SDP-AC-001 | This policy must be Accepted with Faiz Review Record. | This document metadata and review record. |
| SDP-AC-002 | This policy must reference DataGovernance, PersonaSafety, AccessControl, ADR-010, ADR-019, and ADR-024 as normative parents. | Related Documents and Section 2. |
| SDP-AC-003 | This policy must state full owner consent is necessary but not sufficient. | Sections 1, 4, and 5. |
| SDP-AC-004 | This policy must prohibit blackmail, humiliation, punitive leverage, jealousy escalation during restricted states, dependency manipulation, and safe-word invalidation. | Section 7 and Appendix C. |
| SDP-AC-005 | This policy must block surveillance confrontation during safe-mode, distress, crisis, and incident states. | Sections 7 and 8. |
| SDP-AC-006 | This policy must require clipboard secrets/password/token patterns to be dropped and incident-logged. | Sections 4, 6, and 13. |
| SDP-AC-007 | This policy must keep camera and screenshots disabled by default, Critical, and short-retention. | Section 6 and Appendix A. |
| SDP-AC-008 | This policy must require fresh wearable activation checklist before wearable use. | Section 6 and Appendix E. |
| SDP-AC-009 | This policy must include collection, retention, prohibited use, device auth, and audit appendices. | Appendices A through F. |
| SDP-AC-010 | This policy must contain zero standalone advisory-language occurrences. | Verification grep. |

## Appendix A. Collection Source Matrix

| Source ID | Source | Device | Default | Class | Purpose | Raw Retention | Derived Retention | Required Consent Scope | Evidence Path |
|---|---|---|---|---|---|---:|---:|---|---|
| SRC-AND-APP | App usage | Android Tasker | Enabled after approval | Restricted | Productivity/routine | 30 days event detail | 180 days summary | `surveillance.android.app_usage` | `evidence/surveillance/collection/android-app-usage.md` |
| SRC-AND-SCREEN | Screen state | Android Tasker | Enabled after approval | Restricted | Availability/routine | 30 days | 180 days summary | `surveillance.android.screen_state` | `evidence/surveillance/collection/android-screen.md` |
| SRC-AND-NOTIF | Notifications | Android Tasker | Enabled after approval | Restricted/Critical | Context/safety/finance when approved | 7 days raw minimized | 180 days summary | `surveillance.android.notifications` | `evidence/surveillance/collection/android-notifications.md` |
| SRC-AND-GPS | Location/GPS | Android Tasker | Enabled after approval | Critical | Safety/routine/geofence | 7 days precise | 180 days geofence summary | `surveillance.android.location` | `evidence/surveillance/collection/android-location.md` |
| SRC-AND-CALL | Call events | Android Tasker | Enabled after approval | Restricted/Critical | Context/safety | 30 days hashed | 180 days summary | `surveillance.android.calls` | `evidence/surveillance/collection/android-calls.md` |
| SRC-AND-CLIP | Clipboard | Android Tasker | Enabled only with scanner | Critical | Context/debug only | 24 hours non-secret; secret dropped | Summary only if approved | `surveillance.android.clipboard` | `evidence/surveillance/collection/android-clipboard.md` |
| SRC-AND-CAMERA | Camera | Android Tasker | Disabled | Critical | Explicit safety/debug/evidence | 24 hours max | Incident summary only | `surveillance.android.camera.explicit` | `evidence/surveillance/collection/android-camera.md` |
| SRC-WIN-ACTIVE | Active window/app | Windows daemon | Enabled after approval | Restricted | Productivity/routine | 30 days | 180 days summary | `surveillance.windows.active_window` | `evidence/surveillance/collection/windows-active-window.md` |
| SRC-WIN-IDLE | Idle/ActivityWatch | Windows daemon | Enabled after approval | Restricted | Productivity/routine | 30 days | 180 days summary | `surveillance.windows.idle` | `evidence/surveillance/collection/windows-idle.md` |
| SRC-WIN-SCREEN | Screenshots | Windows daemon | Disabled | Critical | Explicit diagnostic/evidence | 24 hours max | Incident summary only | `surveillance.windows.screenshot.explicit` | `evidence/surveillance/collection/windows-screenshots.md` |
| SRC-WIN-BROWSER | Browser history | Windows daemon | Enabled after approval | Restricted/Critical | Productivity/security | 7 days raw | 180 days category summary | `surveillance.windows.browser_history` | `evidence/surveillance/collection/windows-browser.md` |
| SRC-WIN-CLIP | Clipboard | Windows daemon | Enabled only with scanner | Critical | Context/debug only | 24 hours non-secret; secret dropped | Summary only if approved | `surveillance.windows.clipboard` | `evidence/surveillance/collection/windows-clipboard.md` |
| SRC-WIN-CAMERA | Camera | Windows daemon | Disabled | Critical | Explicit safety/debug/evidence | 24 hours max | Incident summary only | `surveillance.windows.camera.explicit` | `evidence/surveillance/collection/windows-camera.md` |
| SRC-WEARABLE | Wearable health | Xiaomi Watch S1 Active / future | Disabled post-MVP | Critical | Health/safety/routine | Activation-plan specific short raw | Summary by approval | `surveillance.wearable.health.explicit` | `evidence/surveillance/collection/wearable-activation.md` |

## Appendix B. Retention Matrix

| Data Family | Raw Retention | Summary Retention | Deletion Rule | Hold Exception |
|---|---:|---:|---|---|
| Clipboard non-secret | 24 hours | Only if approved | Auto-delete raw. | Incident/debug hold with Faiz approval. |
| Clipboard secret/token/password/private key | 0 seconds | Hash/category incident metadata only | Drop payload immediately. | Never retain plaintext secret. |
| Camera frames | 24 hours max | Incident/evidence summary only | Auto-delete raw. | SEV/evidence hold with owner, scope, review date. |
| Screenshots | 24 hours max | Incident/evidence summary only | Auto-delete raw. | SEV/evidence hold with owner, scope, review date. |
| Precise location | 7 days | 180 days geofence summary | Delete raw precision. | Safety/incident hold. |
| Browser raw URL/title | 7 days | 180 days category summary | Strip query strings; delete raw. | Security incident hold. |
| Notifications/messages raw | 7 days max | 180 days minimized summary | Redact third-party and intimate details. | Incident hold. |
| App/window/idle events | 30 days | 180 days productivity summary | Summarize or delete. | Operational evidence hold. |
| Wearable raw | Defined at activation, max 30 days by default | Health/routine summary by consent | Delete raw by activation plan. | Health/safety incident hold. |
| Audit logs | Governance-defined | N/A | Keep payload-free proof. | Formal audit hold. |

## Appendix C. Prohibited Use Matrix

| Use Case | Status | Rationale | Required Response |
|---|---|---|---|
| Blackmail using surveillance data | Prohibited | Violates autonomy and safety. | Block, incident-log, neutral mode. |
| Humiliation based on private data | Prohibited | Violates privacy and persona safety. | Block, rewrite neutral/supportive. |
| Punitive leverage from surveillance | Prohibited in all restricted states; tightly bounded otherwise | Punishment cannot override safety or consent. | Block during safe-mode/distress/crisis/incident; require explicit normal-state context. |
| Jealousy escalation during restricted state | Prohibited | Yandere behavior cannot outrank safety. | Downgrade to Y0/Y1. |
| Dependency manipulation | Prohibited | Consent must remain revocable. | Block and log safety review. |
| Safe-word invalidation using surveillance evidence | Prohibited | Safe word is global hard stop. | Treat as SEV0/SEV1 if attempted by runtime. |
| Routine productivity nudging from minimized summaries | Allowed with controls | Supports BRD/PRD purpose. | Use minimized summary, no raw reveal. |
| Incident containment using minimum necessary context | Allowed with controls | Safety and security purpose. | Use minimal data, log, time-bound. |

## Appendix D. Device Authentication Specification

| Requirement | Control |
|---|---|
| Device enrollment | Each source device must have approved device record, source list, key reference, Tailscale identity, consent scope, and owner. |
| Transport | Ingestion must use Tailscale or accepted private path; public admin exposure is denied. |
| Signing | Event payloads must use HMAC or equivalent signed request validation when the client supports it. |
| Nonce/replay | Payloads must include timestamp and nonce; stale or duplicate payloads must be rejected. |
| Key rotation | Device keys must rotate after compromise, decommission, suspicious replay, or scheduled review. |
| Disable path | Guinevere must support source-level and device-level disable with evidence. |
| Failure state | Unknown device, invalid signature, replay, expired consent, or unknown safety state must fail closed. |

## Appendix E. Wearable Activation Checklist

| Gate | Requirement | Status |
|---|---|---|
| WAC-001 | Faiz must explicitly approve wearable device, data fields, frequency, retention, purpose, and health-safety boundaries. | Required before activation |
| WAC-002 | Data map must classify heart rate, stress, sleep, steps, activity, and derived health summaries as Critical unless approved otherwise. | Required before activation |
| WAC-003 | Consent scope must be added to consent ledger and revocation procedure. | Required before activation |
| WAC-004 | Ingestion must use authenticated channel and documented vendor risk. | Required before activation |
| WAC-005 | Persona use must prohibit punishment, shame, or coercive health framing. | Required before activation |
| WAC-006 | Retention plan must define raw duration, summary duration, export, deletion, and incident hold. | Required before activation |
| WAC-007 | Test evidence must verify disable, revocation, retention, and safe-mode behavior. | Required before activation |

## Appendix F. Audit Checklist

| Check | Pass Rule | Evidence |
|---|---|---|
| Authority | Normative parents present and conflict rules explicit. | Section 2. |
| Consent | Full consent necessary but not sufficient; revocation interaction explicit. | Sections 1, 4, 5. |
| Collection | All source families mapped with default state, classification, retention, and consent scope. | Appendix A. |
| Retention | Raw surveillance data has class-based duration and delete/summarize rules. | Section 9 and Appendix B. |
| Prohibited Use | Blackmail, humiliation, punitive leverage, jealousy escalation, dependency manipulation, and safe-word invalidation blocked. | Section 7 and Appendix C. |
| Restricted State | Confrontation blocked in safe-mode, distress, crisis, incident. | Section 8. |
| Clipboard Secrets | Secrets/passwords/tokens/private keys dropped and incident-logged. | Sections 4, 6, 13. |
| Camera/Screenshots | Disabled by default, Critical, short retention. | Appendix A and B. |
| Wearable | Post-MVP, activation checklist required. | Appendix E. |
| Access | ABAC/RBAC, raw access, break-glass, and sub-agent ceilings mapped. | Section 11. |
| Incident | Surveillance failures map to severity and response. | Section 13. |
| Language | No standalone advisory-language occurrences. | Verification grep. |

## Review Record

| Date | Reviewer | Decision | Notes |
|---|---|---|---|
| 2026-05-30 | Faiz | Accepted | Accepted through `ALL:D` with mandatory constraints: full owner consent necessary but not sufficient; persona never outranks surveillance safety/consent/revocation/access/incident; listed prohibited uses; confrontation blocked in restricted states; clipboard secrets dropped and incident-logged; camera/screenshots disabled by default and short retention; wearable post-MVP with fresh activation checklist; all controls use must. |
| 2026-05-30 | Guinevere / Hephaestus | Accepted for audit | Policy generated from foundation docs, source-map report, and external privacy-pattern report. |

## Next Required Work

| Priority | Document / Artifact | Reason |
|---|---|---|
| P0 | `Guinevere_ConsentRevocationPolicy_v1.0.md` | Required runtime consent and revocation parent for surveillance enforcement. |
| P0 | `evidence/surveillance/collection/*.md` | Required source enrollment and runtime proof evidence. |
| P0 | `evidence/surveillance/retention/retention-job-proof.md` | Required proof that raw surveillance TTL and deletion jobs work. |
| P1 | `Guinevere_PromptInjection_ModelSafetySpec_v1.0.md` | Required to govern untrusted content from messages, browser, notifications, clipboard, and surveillance payloads. |
| P1 | `Guinevere_DatabaseERD_MigrationStrategy_v1.0.md` | Required to formalize surveillance tables, Timescale hypertables, retention jobs, indexes, and deletion paths. |
