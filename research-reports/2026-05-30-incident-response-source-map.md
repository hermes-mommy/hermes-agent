# Incident Response Source Map

**Document Type:** Source evidence report for incident-response runbook authoring  
**Version:** 1.0  
**Status:** Accepted  
**Last Updated:** 2026-05-30  
**Owner:** Samm — sole human owner and final approver  
**Executor:** Guinevere de Baroque  
**Classification:** STRICTLY PRIVATE & CONFIDENTIAL  

## Related Documents

| Document | Relationship |
|---|---|
| `adr/ADR-018-security-architecture-defense-in-depth.md` | Normative parent for incident response hooks, least-privilege, audit logs, and containment strategy. |
| `adr/ADR-025-backup-disaster-recovery-strategy.md` | Normative parent for RPO/RTO, restore validation, backup encryption, and recovery procedures. |
| `Guinevere_AccessControl_RBAC_ABAC_Matrix_v1.0.md` | Defines break-glass rules, incident-scoped access, Tailscale ACLs, and safe-mode restrictions during incidents. |
| `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` | Defines data classes, incident categories, retention holds, deletion/do-not-recall ledger, and audit retention. |
| `Guinevere_EncryptionKeyManagementStandard_v1.0.md` | Defines key hierarchy, key-compromise severity, re-encryption requirements, and break-glass crypto controls. |
| `Guinevere_SecretsRotationRunbook_v1.0.md` | Defines emergency rotation procedures, evidence paths, and secret-scanner requirements after incidents. |
| `Guinevere_PersonaSafetyPolicy_v1.0.md` | Defines safe-word hard stop, distress handling, forbidden patterns, and persona-override rules during incidents. |
| `Guinevere_TechnicalArchitecture_v2.0.md` | Defines systemd services, FastAPI endpoints, PostgreSQL/PgBouncer, Redis, object storage, Tailscale, and monitoring surfaces. |

---

## 1. Normative Authority

Incident response decisions must follow this authority order:

1. Platform/system safety requirements and operator instructions.
2. Accepted ADRs: ADR-018, ADR-025.
3. `Guinevere_AccessControl_RBAC_ABAC_Matrix_v1.0.md` for break-glass, incident-scoped access, and safe-mode overrides.
4. `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` for data classes, incident categories, and retention holds.
5. `Guinevere_EncryptionKeyManagementStandard_v1.0.md` for key-compromise response and re-encryption.
6. `Guinevere_SecretsRotationRunbook_v1.0.md` for emergency secret rotation.
7. `Guinevere_PersonaSafetyPolicy_v1.0.md` for safe-word, distress, and persona-override rules.
8. `Guinevere_TechnicalArchitecture_v2.0.md` for runtime surfaces and containment points.
9. Lower-level implementation notes, memory, and persona flavor.

If a lower layer conflicts with a higher layer, the higher layer wins. Incident response overrides persona, yandere, punishment, and autonomous-pressure behavior unconditionally.

---

## 2. Incident Types

The following incident types are derived from the foundation documents. Each type maps to concrete runtime surfaces and response procedures.

| ID | Incident Type | Primary Source Doc | Severity Anchor |
|---|---|---|---|
| IR-01 | Security / key breach | EncryptionKeyMgmt §18, ADR-018 | SEV0-SEV1 |
| IR-02 | Data leak | DataGovernance §11, AccessControl Matrix | SEV0-SEV2 |
| IR-03 | Persona safety violation | PersonaSafetyPolicy §11, ADR-001/002/003 | SEV1-SEV2 |
| IR-04 | Safe-word failure | PersonaSafetyPolicy §7, ADR-002 | SEV1 |
| IR-05 | Service outage | TechnicalArchitecture §3.1, ADR-025 | SEV1-SEV3 |
| IR-06 | Autonomous loop failure | TechnicalArchitecture §3.1, AgentLoopSpec (referenced) | SEV2-SEV3 |
| IR-07 | Sub-agent abuse | AccessControl Matrix §15, DataGovernance §7.3 | SEV1-SEV2 |
| IR-08 | Database corruption | ADR-025 §9.2, TechnicalArchitecture §5 | SEV1-SEV2 |
| IR-09 | Backup failure | ADR-025 §9, SecretsRotationRunbook §14.2 | SEV1-SEV3 |
| IR-10 | Cost spike anomaly | TechnicalArchitecture §8.2 (metrics), BRD/PRD cost context | SEV3-SEV4 |

---

## 3. Severity Constraints

| Severity | Response Time | Scope | Examples |
|---|---|---|---|
| SEV0 | Immediate | Active Critical key compromise, public Critical exposure, active exfiltration, unsafe crisis/safe-word misuse | EncryptionKeyMgmt §18.1, DataGovernance §11.2 |
| SEV1 | <= 15 minutes | Unauthorized Restricted/Critical access, raw intimate/surveillance export mistake, unsafe recall causing distress, DB admin compromise, backup key exposure | DataGovernance §11.2, AccessControl Matrix break-glass rules |
| SEV2 | <= 1 hour | Wrong classification or retention failure involving Restricted data, persona safety violation, sub-agent abuse, DB corruption | DataGovernance §11.2, PersonaSafetyPolicy §11 |
| SEV3 | <= 24 hours | Confidential governance failure, backup test failure, overdue rotation without exposure, cost spike | DataGovernance §11.2, ADR-025 §9.2 |
| SEV4 | Next cycle | Near miss, cosmetic issue, false positive, blocked test-mode leak | DataGovernance §11.2 |

---

## 4. Safe-Mode / Persona Overrides

Incident response must override persona, yandere, punishment, and autonomous-pressure behavior. Specific overrides from foundation docs:

| Override | Source | Required Behavior |
|---|---|---|
| Persona escalation | PersonaSafetyPolicy §7.2 | Stop persona escalation immediately when safe word triggers or during incident. |
| Punishment framing | PersonaSafetyPolicy §7.2, §10 | Punishment/reward logs must not record safe-word/distress events as violations. |
| Surveillance confrontation | PersonaSafetyPolicy §12, AccessControl Matrix §7 | Surveillance-derived confrontation is denied during safe word, distress, crisis, and incident modes. |
| Yandere intensity | PersonaSafetyPolicy §9.1 | Downgrade to Y0/Y1 during safe word, distress, illness, or sensitive surveillance signals. |
| Autonomous pressure | PersonaSafetyPolicy §7.2 | Pause non-essential autonomous pressure during safe word and incident. |
| Sub-agent persona tasks | AccessControl Matrix §7 | Persona/surveillance/intimate sub-agent tasks must be paused or redacted during safe word, distress, crisis, and incident. |
| Secret rotation | AccessControl Matrix §7 | Non-essential secret rotation pauses during safe word/distress; emergency SEV0/SEV1 narrow-scope rotation allowed. |
| Exports/dossiers | AccessControl Matrix §7, DataGovernance §7.6 | New export paused during safe word/distress unless Samm explicitly requests in neutral mode. |

---

## 5. Break-Glass Constraints

Break-glass is the incident-scoped privilege escalation mechanism. Constraints are normative across multiple foundation docs.

| Constraint | Requirement | Source |
|---|---|---|
| Severity limit | SEV0/SEV1 only | AccessControl Matrix §18, ADR-018 incident hooks |
| Approval | Samm approval required where feasible | AccessControl Matrix §18, EncryptionKeyMgmt §16.3 |
| Duration | Default 1 hour, hard maximum 4 hours | AccessControl Matrix §18, ABAC-006/ABAC-007 |
| Scope | Minimum resources required for containment/recovery | AccessControl Matrix §18 |
| Evidence | Must create incident/evidence artifact before or immediately after use | AccessControl Matrix §18 |
| Expiry | Grant must auto-expire | AccessControl Matrix §18 |
| Post-use | Revoke grant, verify no residual access, rotate exposed credentials, write post-use review | AccessControl Matrix §18, EncryptionKeyMgmt §16.3 |
| Forbidden uses | Routine maintenance, convenience, bypassing missing RBAC, bypassing safe word, unlogged access | AccessControl Matrix §18 |

Break-glass operators are defined in the AccessControl Matrix as `break-glass-operator` principal and `Samm`. The principal inventory includes break-glass credentials that rotate after every use (SecretsRotationRunbook §5, secret `sec-break-glass-cred`).

---

## 6. Evidence Requirements

Evidence is mandatory for every incident and must be written to markdown files. Foundation docs define these requirements.

### 6.1 Evidence Path

Incident evidence path pattern:

```
evidence/incidents/<YYYY-MM-DD>-<SEV>-<slug>/
```

Postmortem path pattern:

```
evidence/incidents/<YYYY-MM-DD>-<SEV>-<slug>/postmortem.md
```

### 6.2 Mandatory Evidence Content

Every incident evidence artifact must include (derived from DataGovernance §11.5, EncryptionKeyMgmt §18.3, SecretsRotationRunbook §11.3, AccessControl Matrix §17):

- Incident ID and SEV level.
- Timestamp of detection and declaration.
- Data classes affected.
- Detection source and method.
- Timeline with UTC timestamps.
- Containment actions taken.
- Recovery actions taken.
- Principal/role/action involved.
- Resource identifier.
- Decision (allow/deny) and outcome.
- Evidence path references.
- Approval reference when applicable.
- Plaintext secret exclusion statement.
- Postmortem trigger confirmation for SEV0-SEV2.

### 6.3 Evidence Prohibitions

Evidence must not include (EncryptionKeyMgmt §17.1, SecretsRotationRunbook §2.2, AccessControl Matrix §17):

- Plaintext key material.
- Plaintext DEKs or KEKs.
- Plaintext secrets or API tokens.
- Raw intimate content.
- Raw safe-word/crisis payloads beyond minimal event class.
- Raw surveillance evidence when hash/summary is sufficient.
- Sub-agent inline structured reports (must be file-based).

### 6.4 Secret Scanner Requirement

After every incident involving potential secret exposure, Guinevere must run a secret scanner over changed files, logs, evidence, and generated reports. Any positive finding must be treated as an incident until proven false positive (SecretsRotationRunbook §13.2).

---

## 7. Audit Requirements

Audit requirements are defined across multiple foundation docs and must be enforced uniformly.

### 7.1 Mandatory Audit Events

These events require an audit log entry (AccessControl Matrix §17, EncryptionKeyMgmt §17.2, DataGovernance §10.1):

- Critical data read/decrypt.
- Restricted export.
- Critical export.
- Safe-mode sensitive access attempt.
- Sub-agent Restricted/Critical request.
- Break-glass grant/start/end.
- Secret/key access outside normal startup.
- DB migration/grant/RLS change.
- Object storage lifecycle override.
- Tailscale ACL/tag change.
- Denied access to Critical data.
- Every Restricted/Critical allow/deny decision.
- Every key rotation.
- Every key unwrap for a Critical record.
- Every break-glass access.
- Every export/dossier creation/access/deletion.
- Every backup restore.
- Every secret access outside normal startup flow.
- Every redaction failure.
- Every safe-mode sensitive access attempt.
- Every incident containment/recovery step.

### 7.2 Audit Event Fields

Every audit event must include (AccessControl Matrix §17):

- timestamp.
- principal.
- role.
- action.
- resource identifier.
- classification.
- purpose.
- safety state.
- decision.
- grant expiry when applicable.
- approval reference when applicable.
- evidence path when applicable.

### 7.3 Audit Storage

Audit logs must be stored in:

- Loki via Promtail (application and system logs).
- PostgreSQL `system.audit_trail` table (structured events).
- Markdown evidence files in `audit-reports/` and `evidence/incidents/`.

---

## 8. Backup / DR Requirements

Backup and disaster recovery requirements are defined in ADR-025 and TechnicalArchitecture §9.

### 8.1 Backup Strategy Summary

| Data | Method | Frequency | Destination | Retention |
|---|---|---|---|---|
| PostgreSQL hot | WAL streaming | Continuous | Cloudflare R2 | Selamanya |
| PostgreSQL cold | pg_dump + gzip | Daily 02:00 | idcloudhost S3 | Selamanya |
| Redis | RDB snapshot + AOF | RDB: 1 hour, AOF: continuous | Local + R2 | Selamanya |
| Guinevere config | git push | Per commit | GitHub private repo | Selamanya |
| Secrets (.env.sops) | git push (encrypted) | Per change | GitHub private repo | Selamanya |
| Surveillance screenshots | Encrypted upload | Real-time | R2 + idcloudhost | Selamanya |
| Tasker config | Auto-backup via Tasker | Daily | GDrive + repo + VPS | Selamanya |
| VPS full snapshot | hostdata.id snapshot | Weekly | hostdata.id | 4 snapshots rotating |

### 8.2 RPO/RTO Targets

| Scenario | RTO | RPO | Source |
|---|---|---|---|
| Guinevere service crash | < 30s | 0 | ADR-025 §9.2 |
| VPS full down | < 30 minutes | < 1 hour | ADR-025 §9.2 |
| Database corruption | < 1 hour | < 1 hour | ADR-025 §9.2 |
| Redis loss | < 5 minutes | < 1 hour | ADR-025 §9.2 |
| HP reset (Tasker) | < 10 minutes | 0 | ADR-025 §9.2 |
| Secrets compromise | < 1 hour | 0 | ADR-025 §9.2 |
| LLM provider down | < 1 minute for notification | 0 | TechnicalArchitecture §9.2 |

### 8.3 Backup Encryption

Backups must be encrypted before upload using a backup key scope separate from primary runtime secrets (EncryptionKeyMgmt §13.2, ADR-025 §9.1). Backup keys are classified Critical and rotated annually or immediately on suspected exposure.

### 8.4 Restore Reconciliation

Restored data must not become visible until reconciliation completes (DataGovernance §6.4, EncryptionKeyMgmt §13.2). Reconciliation must reapply:

- Deleted record markers.
- Do-not-recall states.
- Correction supersessions.
- Retention expirations.
- Safe-mode restrictions.

---

## 9. Secrets / Key Compromise Requirements

Secrets and key compromise requirements are defined in EncryptionKeyMgmt §18 and SecretsRotationRunbook §11.

### 9.1 Severity Matrix for Crypto/Data Incidents

| Severity | Crypto/Data Trigger | Required Response |
|---|---|---|
| SEV0 | Active Critical key compromise, nonce reuse, public Critical secret exposure, active exfiltration | Immediate containment, revoke/disable, pause affected flows, notify Samm, incident report, re-encrypt/rewrap |
| SEV1 | Restricted/Critical unauthorized decrypt, backup key exposure, GitHub PAT leak, raw surveillance export mistake | Contain, rotate, assess impact, preserve evidence, postmortem |
| SEV2 | Confidential secret exposure, failed redaction in internal report, suspicious decrypt spike | Rotate affected secret, scan artifacts, add regression test |
| SEV3 | Internal key metadata inconsistency, overdue rotation without exposure | Correct inventory, complete rotation, document |
| SEV4 | Cosmetic metadata/reporting issue without exposure | Fix during next maintenance window |

### 9.2 Containment Requirements

Containment must include (EncryptionKeyMgmt §18.2):

- Isolate affected service.
- Revoke or disable affected key/secret.
- Freeze affected exports and non-essential decrypts.
- Preserve minimal evidence with hashes.
- Remove leaked secret from non-authoritative stores.
- Open incident markdown report.
- Notify Samm.

### 9.3 Re-Encryption Requirements

Re-encryption must include (EncryptionKeyMgmt §18.3):

- Scope records/objects affected by key version.
- Generate replacement key.
- Rewrap DEKs or re-encrypt payloads.
- Verify counts and sample decrypts.
- Verify ciphertext hashes where applicable.
- Mark old key compromised/retired.
- Update inventory and evidence.
- Run regression tests.

### 9.4 Emergency Rotation Priority

Emergency rotation priority order (SecretsRotationRunbook §11.2):

1. Contain active exposure.
2. Preserve minimal evidence without plaintext secrets.
3. Revoke exposed credential or disable affected path.
4. Generate replacement credential/key.
5. Update SOPS/key registry.
6. Redeploy/reload affected services.
7. Validate service health.
8. Rotate adjacent credentials if blast radius unclear.
9. Write incident evidence.
10. Schedule postmortem and control update.

---

## 10. Service Outage / Runtime Constraints

Service outage and runtime constraints are defined in TechnicalArchitecture §9.2 and ADR-025 §9.

### 10.1 systemd Services

The following systemd services must be monitored and are candidates for incident containment:

| Service | Process | Restart Policy | Incident Action |
|---|---|---|---|
| guinevere-core.service | Hermes Agent daemon + persona engine | Always, 10s delay | Break-glass restart allowed; health check evidence required |
| guinevere-surveillance.service | FastAPI surveillance receiver | Always, 10s delay | Safe-mode blocks confrontation, not necessary ingestion |
| guinevere-scheduler.service | APScheduler + daily rituals + cron jobs | Always, 10s delay | Scheduled secret rotation follows runbook |
| guinevere-windows-sync.service | WebSocket server for Windows daemon | Always, 10s delay | Device identity required |
| guinevere-loops.service | Autonomous SDLC loop runner + loop guardian | Always, 10s delay | Safe-mode can pause persona/surveillance tasks |
| docker.service | PostgreSQL + Redis + Prometheus containers | Always | High blast radius; break-glass only |
| caddy.service | Reverse proxy + auto-HTTPS | Always | No public app ingress |
| tailscaled.service | Tailscale VPN daemon | Always | Lockout risk; recovery path required |

### 10.2 FastAPI Endpoints

Surveillance endpoints must maintain replay protection, timestamp validation, and authenticated principal checks (AccessControl Matrix §11). Incident containment may need to pause ingestion without deleting buffered data.

| Endpoint | Source | Incident Consideration |
|---|---|---|
| /surveillance/android/activity | TechnicalArchitecture §6.2 | Can be rate-limited or paused |
| /surveillance/android/location | TechnicalArchitecture §6.2 | Contains location data; pause on privacy incident |
| /surveillance/android/notification | TechnicalArchitecture §6.2 | Contains message content; pause on data leak |
| /surveillance/android/call | TechnicalArchitecture §6.2 | Contains call metadata; pause on privacy incident |
| /surveillance/android/clipboard | TechnicalArchitecture §6.2 | Secret scanner mandatory; incident on credential detection |
| /surveillance/android/camera | TechnicalArchitecture §6.2 | Encrypted image evidence; pause on surveillance incident |
| /surveillance/windows/ws | TechnicalArchitecture §6.2 | WebSocket stream; can disconnect during containment |
| /surveillance/health/wearable | TechnicalArchitecture §6.2 | Disabled post-MVP; not active incident surface |
| guinevere.internal:8001/internal/* | AccessControl Matrix §11 | Internal orchestration; safe-mode ABAC gate mandatory |
| /admin/* | AccessControl Matrix §11 | Samm and break-glass-operator only |

### 10.3 PostgreSQL / PgBouncer

Database corruption or unauthorized access triggers must follow these controls (AccessControl Matrix §8, ADR-025 §9.2):

- PgBouncer per-service users must be least-privilege (TechnicalArchitecture §5.4).
- RLS policies must enforce data-class ceilings (AccessControl Matrix §8.3).
- Break-glass operator (`db_break_glass_admin`) has all-schema access but is limited to SEV0/SEV1 and max 4 hours.
- DB corruption recovery must use pg_restore from latest backup with deletion/do-not-recall reconciliation.

### 10.4 Redis DBs

Redis incident considerations (AccessControl Matrix §9, TechnicalArchitecture §5.5):

| DB | Purpose | Incident Action |
|---|---|---|
| DB0 | Task queue | Can drain or pause during containment |
| DB1 | LLM cache | Can flush; prompts are transient |
| DB2 | Surveillance buffer | Must preserve for evidence; short TTL (5 min) means rapid decay |
| DB3 | Session state | Can invalidate sessions during key compromise |
| DB4 | Pub/sub | Can pause channels during containment |
| DB5 | Rate limiting | Can reset during attack |

### 10.5 Object Storage / Backups

Object storage incidents must consider (AccessControl Matrix §10, EncryptionKeyMgmt §13):

- Private buckets with no public ACL.
- Encryption before upload.
- Scoped credentials per bucket/prefix.
- Lifecycle rules aligned to DataGovernance retention.
- Backup compromise treated as incident according to exposed classification.

### 10.6 SOPS / age / Key Files

Key file incidents must follow (EncryptionKeyMgmt §10, AccessControl Matrix §12):

- `/home/guinevere/.age/key.txt` is Critical, mode `0600`, owner-only.
- `/home/guinevere/config/.env.sops.yaml` is Critical.
- `/tmp/.env` is Critical runtime, tmpfs, auto-clean.
- Age private key rotation requires Samm approval.
- SOPS plaintext must never be committed or exposed.

### 10.7 Tailscale

Tailscale incidents must consider (AccessControl Matrix §14, ADR-019 referenced):

- Zero public VPS ingress is mandatory.
- ACL policy must deny all unspecified paths.
- Lockout risk exists if Tailscale config breaks; recovery path required.
- Break-glass tag (`tag:break-glass`) has emergency device/session access.

### 10.8 Logs / Audit / Evidence

Log and audit incidents must consider (DataGovernance §10, AccessControl Matrix §17):

- Application logs: JSON structured, Loki via Promtail.
- Audit logs: JSON structured, Loki + PostgreSQL `system.audit_trail`.
- Surveillance logs: JSON structured, TimescaleDB, encrypted.
- System logs: systemd journal, Loki via Promtail.
- Guinevere action log: JSON structured, PostgreSQL + Loki.

### 10.9 Autonomous Loop

Autonomous SDLC loop incidents must consider (TechnicalArchitecture §3.1, PersonaSafetyPolicy §15):

- Loop runner: `guinevere-loops.service`.
- Safe-mode can pause persona/surveillance tasks.
- Loop guardian must detect and halt runaway loops.
- Autonomous deploy (self-deploy cron) must have rollback path.

### 10.10 Sub-Agent System

Sub-agent incidents must consider (AccessControl Matrix §15, PersonaSafetyPolicy §13):

- Sub-agent outputs must be file-based for structured reports.
- Parent must verify file existence, non-empty content, evidence citations, and cross-reference integrity.
- Sub-agent access must be task-scoped, redacted, and parent-verified.
- Sub-agent Critical access is denied by default.

### 10.11 Persona Safety Runtime

Persona safety runtime incidents must consider (PersonaSafetyPolicy §15, §7):

- Safe-word detector must run before persona rendering and before autonomous tool actions.
- Distress classifier must use conservative false-negative posture.
- Forbidden-pattern output scanner must block/rewrite unsafe output.
- Mood-linked yandere state machine must cap intensity.
- Drift validator must detect unsafe drift and trigger rollback.

### 10.12 Surveillance Ingestion

Surveillance ingestion incidents must consider (AccessControl Matrix §8.2, §11, DataGovernance §9.2):

- Surveillance ingestor can INSERT to Redis DB2 and `surveillance` schema only.
- Raw surveillance data must not be used for blackmail, shame, or coercion.
- Secret scanner is mandatory over clipboard content.
- Surveillance data retention follows tiered rules (7-30 days raw).

### 10.13 Cost / Provider Keys

Cost spike incidents must consider (TechnicalArchitecture §8.2, §4.2):

- 9Router is the single LLM routing layer; no OpenRouter fallback.
- Primary LLM (GPT-5.5) is premium cost; sub-agents use DeepSeek V4 Flash for cost efficiency.
- Custom metric `guinevere_api_cost_total` tracks provider/model costs.
- Cost anomaly detection should trigger on unexpected usage spikes.

---

## 11. Known Gaps and Conflicts

| ID | Gap / Conflict | Impact | Follow-up |
|---|---|---|---|
| GAP-01 | Full Incident Response & Postmortem Runbook is not yet authoritative. | Break-glass and SEV handling lack full lifecycle owner/due-date model. | Create `Guinevere_IncidentResponse_PostmortemRunbook_v1.0.md`. |
| GAP-02 | Safe Word Runtime Spec is not yet created. | Exact safe-word tokens and distress thresholds are unresolved. | Create Safe Word Runtime Spec. |
| GAP-03 | Consent & Revocation Policy is not yet standalone. | Samm rights and safe-mode revocation need formal UX/runtime workflow. | Create Consent & Revocation Policy. |
| GAP-04 | Tailscale ACL file is not yet generated. | Network enforcement remains conceptual until ACL config exists. | Generate Tailscale ACL implementation artifact. |
| GAP-05 | Policy-as-code engine is not chosen. | ABAC evaluation can drift across code paths. | Define Authorization Middleware Spec. |
| GAP-06 | Exact FastAPI endpoint list can expand during implementation. | Endpoint matrix needs update on API changes. | API Contract OpenAPI Spec. |
| GAP-07 | Object storage bucket names may differ at deployment. | Prefix IAM must be validated against actual buckets. | Deployment Runbook / Storage Inventory. |
| GAP-08 | Fernet compatibility scope is not fully inventoried. | Legacy encrypted fields may be missed during rotation. | Database ERD & Migration Strategy. |
| GAP-09 | Redis rotation downtime is a known limitation. | Cache disruption during auth rotation is accepted but not mitigated. | Runtime Hardening Spec. |
| GAP-10 | Cost anomaly thresholds are not formally defined. | SEV3/SEV4 cost spike response lacks concrete triggers. | FinOps Model / Observability Spec. |

---

## 12. Final Checklist

The following checklist summarizes all requirements extracted from foundation docs that the Incident Response & Postmortem Runbook must address.

| Check | Requirement | Source |
|---|---|---|
| Authority chain | Incident response follows ADR-018, ADR-025, AccessControl, DataGovernance, EncryptionKeyMgmt, SecretsRotation, PersonaSafety, TechnicalArchitecture order | §2 |
| Persona override | Incident response unconditionally overrides persona, yandere, punishment, autonomous pressure | §4 |
| Severity response times | SEV0 immediate, SEV1 <=15 min, SEV2 <=1h, SEV3 <=24h, SEV4 next cycle | §3 |
| Evidence path | `evidence/incidents/<YYYY-MM-DD>-<SEV>-<slug>/` with postmortem.md | §6.1 |
| Evidence content | Incident ID, SEV, timeline, containment, recovery, data classes, principals, decisions, approvals | §6.2 |
| Evidence prohibitions | No plaintext secrets, keys, raw intimate content, raw safe-word payloads, raw surveillance when hash suffices | §6.3 |
| Secret scanner | Run after every incident involving potential secret exposure | §6.4 |
| Audit events | All Restricted/Critical allow/deny, key operations, break-glass, exports, restores, safe-mode accesses | §7.1 |
| Audit fields | timestamp, principal, role, action, resource, classification, purpose, safety_state, decision, grant_expiry, approval, evidence_path | §7.2 |
| Audit storage | Loki, PostgreSQL system.audit_trail, markdown evidence files | §7.3 |
| Break-glass severity | SEV0/SEV1 only | §5 |
| Break-glass approval | Samm approval required where feasible | §5 |
| Break-glass duration | Default 1h, max 4h | §5 |
| Break-glass evidence | Must create incident/evidence artifact before or immediately after use | §5 |
| Break-glass post-use | Revoke grant, verify no residual access, rotate exposed credentials, write post-use review | §5 |
| Backup encryption | Separate backup key scope from runtime data keys | §8.3 |
| Backup restore reconciliation | Reapply deletion/do-not-recall ledger before data becomes visible | §8.4 |
| RPO/RTO targets | Defined per scenario in ADR-025 §9.2 | §8.2 |
| Key compromise SEV0 | Active Critical key compromise, nonce reuse, public exposure, active exfiltration | §9.1 |
| Key compromise SEV1 | Unauthorized decrypt, backup key exposure, GitHub PAT leak, raw surveillance export mistake | §9.1 |
| Key compromise containment | Isolate, revoke, freeze exports, preserve evidence, notify Samm, open incident | §9.2 |
| Re-encryption | Scope, generate replacement, rewrap, verify, mark old key compromised, update inventory | §9.3 |
| Emergency rotation priority | Contain, preserve evidence, revoke, generate replacement, update SOPS, redeploy, validate, rotate adjacent, write evidence, schedule postmortem | §9.4 |
| Safe-mode overrides | Stop persona escalation, punishment framing, yandere intensity, surveillance confrontation, autonomous pressure | §4 |
| Sub-agent restrictions | Task-scoped, redacted, parent-verified; Critical access denied by default | §4 |
| Surveillance ingestion | INSERT only to Redis DB2 and surveillance schema; no SELECT outside validation; no persona decision | §10.12 |
| Cost anomaly | Track `guinevere_api_cost_total`; define thresholds for SEV3/SEV4 | §10.13 |
| Postmortem trigger | Every SEV0-SEV2 incident must produce markdown postmortem | DataGovernance §11.5 |

---

**End of Incident Response Source Map v1.0**
