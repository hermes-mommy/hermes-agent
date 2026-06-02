# Guinevere Access Control RBAC/ABAC Matrix

**Document Type:** Access Control standard, RBAC/ABAC matrix, implementation guidance, and audit appendices  
**Version:** 1.0  
**Status:** Accepted  
**Lifecycle:** Proposed -> Accepted -> Deprecated -> Superseded  
**Last Updated:** 2026-05-30  
**Owner:** Faiz — sole human owner and final approver  
**Executor:** Guinevere de Baroque  
**Classification:** STRICTLY PRIVATE & CONFIDENTIAL  
**Authority:** Normative child under ADR-019, ADR-018, ADR-024, ADR-012, `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md`, `Guinevere_EncryptionKeyManagementStandard_v1.0.md`, and `Guinevere_PersonaSafetyPolicy_v1.0.md`

## Related Documents

| Document | Relationship | Dependency Type | Implementation Impact |
|---|---|---|---|
| `adr/ADR-019-access-control-vpn-mesh-strategy.md` | Normative parent for VPN-first access and zero public ports. | Security boundary | All admin and service surfaces must be Tailscale-internal only. |
| `adr/ADR-018-security-architecture-defense-in-depth.md` | Normative parent for least privilege, hardening, audit logs, and defense-in-depth. | Security architecture | Every role must be minimum-scope and auditable. |
| `adr/ADR-024-data-governance-classification-policy.md` | Normative parent for data classes and classification-driven access. | Data governance | Every permission must map to data class and purpose. |
| `adr/ADR-012-sub-agent-orchestration-governance.md` | Normative parent for sub-agent trust and file-based verification. | Agent governance | Sub-agent access must be task-scoped, redacted, and parent-verified. |
| `adr/ADR-008-memory-encryption-key-management.md` | Normative parent for key hierarchy and emergency revoke path. | Crypto governance | Decrypt, rotate, rewrap, and break-glass actions must be restricted. |
| `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` | Defines Public/Internal/Confidential/Restricted/Critical tiers and highest-wins rule. | Policy dependency | Data class ceilings and safe-mode restrictions are enforced here. |
| `Guinevere_EncryptionKeyManagementStandard_v1.0.md` | Defines key hierarchy, envelope encryption, safe-mode crypto restrictions, and break-glass. | Security standard dependency | Key and secret access matrices inherit these controls. |
| `Guinevere_PersonaSafetyPolicy_v1.0.md` | Defines safe word, distress mode, sensitive recall restrictions, and forbidden behavior. | Safety boundary | Safe-mode restrictions override persona, recall, and tool permissions. |
| `Guinevere_TechnicalArchitecture_v2.0.md` | Defines services, PgBouncer users, Redis DBs, endpoints, systemd units, paths, and network topology. | Runtime implementation | Concrete surfaces are mapped into RBAC/ABAC tables. |
| `Guinevere_MemorySchema_v2.0.md` | Defines memory schemas, sensitive tables, encryption profiles, and long-term memory surfaces. | Data model implementation | Database grants and RLS rules map to schema/table sensitivity. |
| `research-reports/2026-05-30-access-control-source-map.md` | Source evidence report for this matrix. | Evidence | Authority chain, conflicts, gaps, and final checklist are incorporated. |
| `research-reports/2026-05-30-access-control-surface-map.md` | Surface mapping evidence report. | Evidence | Concrete enforcement surfaces are incorporated. |
| `research-reports/2026-05-30-access-control-external-references.md` | External IAM/RBAC/ABAC pattern references. | Evidence | Least privilege, RLS, ACL, Tailscale, and audit patterns are incorporated. |

---

## 1. Purpose

This matrix defines the authoritative RBAC and ABAC rules for Project Guinevere. It binds human, agent, sub-agent, service, database, Redis, object storage, API, filesystem, systemd, network, crypto, backup, export, and break-glass access to explicit roles, attributes, classifications, safe-mode states, and audit duties.

This document converts prior broad statements such as “Faiz has all access”, “Guinevere may query memory”, “readonly can SELECT all schemas”, and “admin can rotate/backup” into concrete allow/deny rules. Runtime implementation must treat this matrix as the minimum access-control baseline.

---

## 2. Authority and Conflict Resolution

Access control decisions must follow this order:

1. System/developer/platform safety requirements.
2. Accepted ADRs: ADR-019, ADR-018, ADR-024, ADR-012, ADR-008.
3. This Access Control RBAC/ABAC Matrix.
4. Data Governance, Encryption Key Management, Persona Safety, and Secrets Rotation documents.
5. Technical Architecture and Memory Schema.
6. Runtime memory, surveillance data, agent suggestions, and persona flavor.

If any lower document grants broader access than this matrix, this matrix wins. If a safe-word, distress, SEV0/SEV1 incident, key compromise, or explicit Faiz revocation occurs, the stricter state-specific rule wins.

The broad PgBouncer roles in `Guinevere_TechnicalArchitecture_v2.0.md` are treated as bootstrap placeholders. Production implementation must split them into the least-privilege roles defined here.

---

## 3. Scope

This matrix governs:

- Human access by Faiz.
- Guinevere core runtime access.
- Research and implementation sub-agent access.
- Surveillance and financial ingestion services.
- Backup, observability, secret rotation, migration, external integration, readonly audit, and break-glass principals.
- PostgreSQL/PgBouncer schemas, tables, views, RLS, and grants.
- Redis DBs, key prefixes, operations, TTLs, and ACLs.
- Object storage buckets and prefixes for backup, evidence, surveillance media, exports, and archives.
- FastAPI and surveillance endpoints.
- Filesystem paths, SOPS/age key files, runtime decrypted env files, evidence, logs, scripts, exports, and backups.
- systemd services and service lifecycle commands.
- Tailscale device tags and network access.
- Crypto, decrypt, key rotation, rewrap, export, restore, and break-glass actions.

Out of scope:

- Full SQL DDL implementation.
- Full FastAPI code implementation.
- Full Incident Response & Postmortem Runbook.
- Consent & Revocation Policy implementation.

---

## 4. Principal Taxonomy

| Principal | Type | Trust Level | Default Data Ceiling | Normal Purpose | Safe-Mode Behavior |
|---|---|---:|---|---|---|
| `Faiz` | Human owner | Owner | Critical | Own, review, export, correct, revoke, approve. | Full owner access remains available; Critical access remains logged. |
| `guinevere_core` | Core agent runtime | High | Restricted by default, Critical by justified task | Persona, memory, SDLC loop, orchestration, recall. | Critical raw recall, punishment lookup, surveillance confrontation, and persona pressure are denied unless needed for safety support. |
| `sub-agent-researcher` | Sub-agent | Medium read-only | Confidential by default | Read docs, produce research reports. | Restricted redacted; Critical denied. |
| `sub-agent-implementer` | Sub-agent | Medium write-capable | Internal by default, Confidential with task scope | Write docs/code/evidence under assigned task. | Persona/surveillance/intimate writes denied unless parent grants explicit scoped evidence task. |
| `surveillance-ingestor` | Service principal | Medium data-write | Restricted raw buffer, Critical if payload contains credentials/intimate/crisis | Receive Android/Windows surveillance events. | Collection continues only for safety/ops; confrontation and punishment routing denied. |
| `financial-ingestor` | Service principal | Medium data-write | Restricted | Receive Tasker financial notifications and transaction imports. | Non-essential enrichment pauses; raw financial recall denied to persona flow. |
| `backup-operator` | Service principal | High ops | Highest source class | Backup, restore test, archive reconciliation. | Restore of Critical data requires explicit reason and audit event. |
| `observability-reader` | Service principal | Low read-only | Confidential metadata only | Metrics, dashboards, health checks. | Payload access denied; metadata-only view remains. |
| `secret-rotator` | Service principal | High security ops | Critical metadata, no plaintext in evidence | Rotate, revoke, rewrap, validate secrets and keys. | Scheduled rotation pauses; emergency SEV0/SEV1 narrow-scope rotation allowed with approval where feasible. |
| `break-glass-operator` | Emergency principal | Restricted emergency | Critical time-boxed | SEV0/SEV1 containment and recovery only. | Allowed only for incident containment, max 4 hours, all access logged. |
| `migration-principal` | Ops principal | High schema-write | Restricted schema metadata, Critical only for migration of encrypted fields | Alembic/schema migration. | Critical data inspection denied; schema-only operations allowed with evidence. |
| `external-integration` | External service principal | Low scoped | Endpoint-specific | Discord, GitHub, Gmail, Resend, Gotify, 9Router, Brave, Exa. | Cannot request raw Critical memory or safe-word logs. |
| `readonly-auditor` | Audit principal | Low read-only | Confidential evidence by default; Restricted redacted | Read audit/evidence/control outputs. | Critical contents redacted; safe-mode logs summarized. |

---

## 5. RBAC Role Definitions

| Role | Assigned Principal(s) | Allowed Capability Summary | Explicit Denials |
|---|---|---|---|
| `owner` | `Faiz` | Full owner access, approval, correction, deletion, export, break-glass approval. | None at policy level; access remains auditable. |
| `core-agent` | `guinevere_core` | Task-scoped memory, persona, orchestration, document/code operation, normal recall. | No Critical recall for persona flavor alone; no bypass of safe-mode. |
| `research-agent` | `sub-agent-researcher` | Read source docs, public/internal/confidential summaries, write research report. | No direct Critical data, no secrets, no raw surveillance, no decrypt. |
| `implementation-agent` | `sub-agent-implementer` | Write assigned files, evidence, tests, implementation summaries. | No broad filesystem write, no secrets, no production restart, no raw Critical data. |
| `surveillance-writer` | `surveillance-ingestor` | Insert surveillance events to Redis DB2 and `surveillance` schema. | No SELECT outside ingestion validation, no persona decision, no punishment write. |
| `financial-writer` | `financial-ingestor` | Insert financial transactions and source metadata. | No client memory, no unrelated financial reads, no scraping override. |
| `backup-operator` | `backup-operator` | Backup, restore test, encrypted archive write/read for validation. | No plaintext export, no direct persona use of restored Critical data. |
| `observability-reader` | `observability-reader` | Metrics, health, logs metadata, dashboard read. | No raw payload, no secret, no Critical content. |
| `secret-rotator` | `secret-rotator` | Rotate/revoke/rewrap secrets and keys per runbook. | No business data reads beyond secret metadata and validation hashes. |
| `break-glass` | `break-glass-operator`, `Faiz` | SEV0/SEV1 emergency access, temporary privilege, containment. | No normal runtime use, no duration over 4 hours, no missing evidence. |
| `migration` | `migration-principal` | Apply migrations, schema changes, RLS policies, grants. | No unrestricted data browse; sample reads must be redacted/minimized. |
| `external-service` | `external-integration` | Use scoped provider credential for assigned API. | No lateral access to memory, DB, Redis, object storage, or secrets. |
| `readonly-audit` | `readonly-auditor` | Read evidence, audit logs, policy reports, redacted summaries. | No write, no decrypt, no raw Critical unless Faiz grants case-specific review. |

---

## 6. ABAC Evaluation Model

Every access decision must evaluate these attributes in order:

1. `principal_id` and authenticated service identity.
2. `role` and assigned trust level.
3. `resource_type` and concrete resource path/table/key/endpoint.
4. `resource_classification` using highest-classification-wins.
5. `purpose` from an approved allow-list.
6. `action` such as read, write, delete, export, decrypt, rotate, restart, migrate, restore.
7. `task_id` or incident ID for scoped work.
8. `safety_state`: normal, safe-word, distress, crisis, incident, key-compromise.
9. `network_context`: Tailscale identity, device tag, service tag, zero-public-port status.
10. `time_window` and grant expiry.
11. `approval_state`: Faiz approval, autonomous preflight pass, break-glass approval where feasible.
12. `audit_requirement` and evidence path.

Default rule: deny. Access is allowed only when RBAC role and all ABAC attributes match an explicit allow row.

### ABAC Rule Catalog

| Rule ID | Condition | Decision | Audit |
|---|---|---|---|
| ABAC-001 | `resource_classification = Critical` and principal not `Faiz`, `guinevere_core`, `secret-rotator`, `backup-operator`, or `break-glass-operator` with approved purpose | Deny | Log denied attempt. |
| ABAC-002 | `safety_state in {safe-word, distress, crisis}` and action is persona escalation, punishment lookup, yandere intensity, or surveillance confrontation | Deny | Log minimal non-punitive safety event. |
| ABAC-003 | Sub-agent requests Critical data | Deny by default | Log task ID and requested class. |
| ABAC-004 | Sub-agent requests Restricted data with task justification and redaction | Allow redacted/minimized | Log report path and parent verifier. |
| ABAC-005 | Secret/key decrypt outside startup, rotation, backup restore, or incident | Deny | Security audit event. |
| ABAC-006 | Break-glass grant requested for non-SEV0/SEV1 | Deny | Security audit event. |
| ABAC-007 | Break-glass grant exceeds 4 hours | Deny | Security audit event. |
| ABAC-008 | Tailscale tag not in endpoint allow-list | Deny | Network audit event. |
| ABAC-009 | Object export contains Restricted/Critical data and lacks encryption/evidence path | Deny | Export denial event. |
| ABAC-010 | Migration requires schema change only and no data browse | Allow for `migration-principal` | Migration evidence event. |
| ABAC-011 | Observability request includes raw payload or secret | Deny | Redaction failure event. |
| ABAC-012 | Backup restore reads Critical payload for validation | Allow only for `backup-operator` with restore-test evidence | Backup audit event. |

---

## 7. Safe-Mode Restrictions

Safe-mode states are `safe-word`, `distress`, `crisis`, `persona-near-miss`, `key-compromise`, and `SEV0/SEV1 incident`.

| Surface | Normal Mode | Safe-Word / Distress Mode | Crisis Mode | Incident / Key Compromise Mode |
|---|---|---|---|---|
| Persona memory recall | Task-scoped recall allowed. | Critical/intimate raw recall denied; supportive summaries only. | Minimal supportive context only. | Deny except incident evidence. |
| Surveillance confrontation | Allowed only for productivity/health/safety purpose. | Denied. | Denied. | Denied except containment. |
| Punishment/reward logs | Restricted with safety gate. | Denied for safe-word event. | Denied. | Denied. |
| Sub-agent access | Task-scoped. | Persona/surveillance/intimate tasks paused or redacted. | Paused unless safety audit task. | Incident-scoped only. |
| Secret rotation | Scheduled allowed. | Non-essential rotation paused. | Non-essential rotation paused. | Emergency narrow-scope rotation allowed. |
| Backup restore | Restore test allowed. | Critical restore needs explicit reason. | Deny unless recovery incident. | Allow narrow-scope recovery. |
| Exports/dossiers | Encrypted, logged, Faiz-controlled. | New export paused unless Faiz explicitly asks in neutral mode. | Deny. | Deny except evidence preservation. |

---

## 8. PostgreSQL and PgBouncer Matrix

### 8.1 Target Database Roles

| DB Role | Principal | Schemas | Allowed Actions | Denied Actions | Notes |
|---|---|---|---|---|---|
| `db_owner_faiz` | `Faiz` | all | Admin via controlled session | none at policy level | Human owner; audited for Critical access. |
| `db_core_memory_rw` | `guinevere_core` | `memory`, `persona`, `behavior`, `projects`, `social` | SELECT/INSERT/UPDATE via views/RLS | raw Critical columns unless purpose matches; DELETE without retention workflow | Replaces broad all-schema core role. |
| `db_surveillance_ingest_w` | `surveillance-ingestor` | `surveillance` | INSERT raw/summary events; SELECT own ingestion status | SELECT historical raw; UPDATE persona/behavior | Tied to FastAPI ingestion identity. |
| `db_financial_ingest_w` | `financial-ingestor` | `financial` | INSERT transactions; SELECT dedupe window | SELECT unrelated history; DELETE | No scraping override. |
| `db_observability_r` | `observability-reader` | `system`, metrics views, redacted audit views | SELECT metadata views | raw payload, secrets, Critical columns | Grafana/Loki bridge only. |
| `db_readonly_audit_r` | `readonly-auditor` | redacted evidence/audit views | SELECT redacted views | decrypt, raw Critical, DDL | Audit-only. |
| `db_backup_rw` | `backup-operator` | all via backup tooling | backup/restore-test with encrypted output | plaintext export; normal app query | Audit evidence required. |
| `db_migration_ddl` | `migration-principal` | all schemas | DDL, migrations, grants, RLS policies | data browsing except redacted samples | Time-boxed migration window. |
| `db_secret_rotation_ops` | `secret-rotator` | `system`, credential metadata, key metadata | rotate credential metadata, validate connection | business data read | No plaintext secret in logs. |
| `db_break_glass_admin` | `break-glass-operator` | all | SEV0/SEV1 emergency admin | normal runtime use; duration >4h | Post-use rotation and evidence required. |

### 8.2 Sensitive Table Rules

| Schema.Table / View | Classification | Default Access | Special Rule |
|---|---|---|---|
| `memory.faiz_profile` | Restricted -> Critical by row | `guinevere_core` via purpose-scoped view | Intimate/secret rows require Critical justification and audit. |
| `memory.emotional_events` | Critical | `guinevere_core` summarized view | Raw description denied during safe-word/distress. |
| `persona.inner_journal` | Critical | `guinevere_core` only with persona-maintenance purpose | Sub-agents denied. |
| `persona.drift_log` | Restricted -> Critical | `guinevere_core`, `readonly-auditor` redacted | Critical when safe-word/distress/intimate/unsafe drift involved. |
| `behavior.violation_log` | Restricted -> Critical | `guinevere_core` normal mode | Safe-word events must not be default violations. |
| `surveillance.screenshots` | Restricted -> Critical | `surveillance-ingestor` INSERT, `guinevere_core` purpose-scoped summary | Raw access denied for persona confrontation. |
| `surveillance.messages` | Restricted -> Critical | ingestion + minimized extraction | Raw messages denied unless explicit evidence purpose. |
| `financial.transactions` | Restricted | `financial-ingestor` INSERT, `guinevere_core` summarized read | No sub-agent direct read unless redacted evidence. |
| `projects.clients` | Restricted | `guinevere_core` task-scoped | Public/client disclosure denied. |
| `system.audit_trail` | Confidential -> Critical | `readonly-auditor` redacted, `guinevere_core` metadata | Payload minimization mandatory. |

### 8.3 RLS Requirements

| RLS Policy | Applies To | Predicate | Enforcement |
|---|---|---|---|
| `rls_data_class_ceiling` | all classified tables | principal clearance >= row classification | Deny rows above clearance. |
| `rls_task_scope` | task/project/evidence tables | `task_id` or `project_id` matches assigned scope | Required for sub-agents. |
| `rls_safe_mode` | memory/persona/behavior/surveillance | safe-mode blocks raw Critical recall and punishment lookup | Required at view/API layer even if DB lacks env state. |
| `rls_subagent_redaction` | docs/evidence/memory views | sub-agent role gets redacted columns only | Required for agent delegation. |
| `rls_audit_payload_min` | audit/log tables | default views exclude raw payload fragments | Required for observability/read-only audit. |

---

## 9. Redis ACL Matrix

| Redis DB | Prefix | Classification | Allowed Principals | Allowed Ops | Denied Ops | TTL Rule |
|---|---|---|---|---|---|---|
| DB0 Task Queue | `task:{id}` | Internal -> Restricted if task includes sensitive data | `guinevere_core`, assigned sub-agent via broker | enqueue, dequeue, ack, status | direct sub-agent broad scan | no indefinite payload with Restricted/Critical content |
| DB1 LLM Cache | `llm:{hash}` | Internal -> highest prompt class | `guinevere_core` | get/set/delete by hash | storing raw Critical prompt; sub-agent direct read | max 1h; Critical raw denied |
| DB2 Surveillance Buffer | `surv:{device}:{ts}` | Restricted -> Critical | `surveillance-ingestor`, `guinevere_core` processor | write, consume, delete | historical scan by persona or sub-agent | max 5m raw buffer |
| DB3 Session State | `session:{id}` | Confidential -> Critical if safe-mode/intimate | `guinevere_core` | read/write own session | sub-agent direct access | max 24h; safe-mode minimized |
| DB4 Pub/Sub | `chan:{component}` | Internal -> Restricted | service-specific principals | publish/subscribe assigned channel | wildcard pub/sub across components | no payload secrets |
| DB5 Rate Limit | `ratelimit:{ip}` | Internal | API gateway/core | get/incr/expire | business data storage | max 1m |

Redis ACLs must use per-principal users and key-prefix restrictions. Critical data must not be durably stored in Redis. Redis backups must inherit the highest source classification.

---

## 10. Object Storage Matrix

| Bucket / Prefix | Classification | Allowed Principals | Allowed Actions | Denied Actions | Controls |
|---|---|---|---|---|---|
| `r2://guinevere-backups/postgres/` | Restricted -> Critical if unsegmented | `backup-operator`, `break-glass-operator` | write encrypted backup, read restore test | plaintext download, public ACL | encryption before upload, lifecycle, evidence. |
| `r2://guinevere-backups/redis/` | Confidential -> Critical by source | `backup-operator` | write/read restore test | direct app use | backup key scope. |
| `r2://guinevere-surveillance/raw/` | Restricted -> Critical | `surveillance-ingestor`, `backup-operator` | write encrypted object, lifecycle delete | persona confrontation read, public ACL | prefix IAM, retention enforcement. |
| `r2://guinevere-evidence/` | highest source class | `guinevere_core`, `readonly-auditor` redacted, `backup-operator` | write/read evidence by task | plaintext secret, public ACL | evidence metadata, no plaintext secrets. |
| `s3://idcloudhost-guinevere-backups/` | Restricted -> Critical | `backup-operator`, `break-glass-operator` | encrypted backup, restore test | public ACL, plaintext export | independent key scope. |
| `exports/` | highest source class | `Faiz`, `guinevere_core` with Faiz request | create encrypted export | unencrypted export, sub-agent access | time-limited, logged, redaction option. |

---

## 11. FastAPI Endpoint Matrix

| Endpoint / Surface | Principal | AuthN | Allowed Actions | Classification | Safe-Mode Rule |
|---|---|---|---|---|---|
| `/surveillance/android/activity` | `surveillance-ingestor` | Tailscale + device HMAC/JWT | POST activity event | Restricted | No persona confrontation route during safe-mode. |
| `/surveillance/android/location` | `surveillance-ingestor` | Tailscale + device HMAC/JWT | POST location event | Restricted -> Critical | Raw precise recall denied during distress. |
| `/surveillance/android/notification` | `surveillance-ingestor` | Tailscale + device HMAC/JWT | POST minimized notification event | Restricted -> Critical | Raw sensitive notification denied to persona. |
| `/surveillance/android/call` | `surveillance-ingestor` | Tailscale + device HMAC/JWT | POST call metadata | Restricted | No punitive use during safe-mode. |
| `/surveillance/android/clipboard` | `surveillance-ingestor` | Tailscale + device HMAC/JWT | POST only when configured; secret scanner mandatory | Critical if credential-like | Redact/incident on secret detection. |
| `/surveillance/android/camera` | `surveillance-ingestor` | Tailscale + device HMAC/JWT | POST encrypted image evidence | Critical by default | Denied to persona confrontation. |
| `/surveillance/windows/ws` | `surveillance-ingestor` | Tailscale + device auth | stream activity/screenshot metadata | Restricted -> Critical | Raw screenshot access blocked in safe-mode. |
| `/surveillance/health/wearable` | disabled post-MVP | disabled | no production write | Restricted | Disabled until post-MVP activation. |
| `guinevere.internal:8001/internal/*` | `guinevere_core` | Tailscale + service JWT | internal orchestration | varies | Safe-mode ABAC gate mandatory. |
| `/admin/*` | `Faiz`, `break-glass-operator` | Tailscale + strong auth + approval | admin tasks | Critical | Break-glass limits apply. |

All endpoint write operations must reject requests missing authenticated principal, source device identity, replay protection, timestamp, and classification metadata.

---

## 12. Filesystem Matrix

| Path | Classification | Owner / Mode | Allowed Principals | Allowed Actions | Denied Actions |
|---|---|---|---|---|---|
| `/home/guinevere/.age/key.txt` | Critical | `guinevere:guinevere`, `0600` | `secret-rotator`, `break-glass-operator` with approval | read for SOPS decrypt/rotation only | sub-agent read, logs, backup plaintext. |
| `/home/guinevere/config/.env.sops.yaml` | Critical | restricted | `secret-rotator`, `guinevere_core` startup read via SOPS | decrypt at startup/rotation | plaintext commit, sub-agent read. |
| `/tmp/.env` | Critical runtime | `0600`, tmpfs | `guinevere_core` startup only | read during boot, auto-clean | backup, report, long-lived storage. |
| `/home/guinevere/core/` | Internal -> Restricted | repo owner | `guinevere_core`, `sub-agent-implementer` task-scoped | code read/write by assigned task | secret files, raw Critical writes. |
| `/home/guinevere/data/logs/` | Confidential -> Critical | service-owned | `guinevere_core`, `observability-reader` redacted | append/read metadata | raw secret/intimate payload. |
| `evidence/` | highest source class | repo owner | `guinevere_core`, `sub-agent-implementer`, `readonly-auditor` redacted | write/read evidence by task | plaintext secrets, unredacted Critical to sub-agent. |
| `audit-reports/` | Confidential -> Restricted | repo owner | `guinevere_core`, `readonly-auditor`, sub-agent writer | write/read audit reports | raw Critical except approved excerpt/hash. |
| `research-reports/` | Internal -> Restricted | repo owner | sub-agents, `guinevere_core` | write/read reports | secrets, raw Critical data. |
| `backups/` local staging | Restricted -> Critical | root/service restricted | `backup-operator`, `break-glass-operator` | encrypted staging/restore test | plaintext dump. |
| `exports/` | highest source class | restricted | `Faiz`, `guinevere_core` with Faiz request | encrypted export | unencrypted or unlogged export. |
| `scripts/*.sh` | Internal -> Critical if secret-handling | repo owner | `migration-principal`, `secret-rotator`, `backup-operator` by script scope | execute assigned script | arbitrary script execution. |

---

## 13. systemd Matrix

| Service | Status Read | Restart | Stop | Logs | Notes |
|---|---|---|---|---|---|
| `guinevere-core.service` | `Faiz`, `guinevere_core`, `observability-reader` | `Faiz`, `guinevere_core`, `break-glass-operator` | `Faiz`, `break-glass-operator` | redacted to observability | Restart requires health check evidence. |
| `guinevere-surveillance.service` | same | `Faiz`, `guinevere_core`, `break-glass-operator` | `Faiz`, `break-glass-operator` | raw payload redacted | Safe-mode blocks confrontation, not necessary ingestion. |
| `guinevere-scheduler.service` | same | `Faiz`, `guinevere_core` | `Faiz`, `break-glass-operator` | metadata | Scheduled secret rotation follows runbook. |
| `guinevere-windows-sync.service` | same | `Faiz`, `guinevere_core` | `Faiz`, `break-glass-operator` | metadata | Device identity required. |
| `guinevere-loops.service` | same | `Faiz`, `guinevere_core` | `Faiz`, `break-glass-operator` | task metadata | Safe-mode can pause persona/surveillance tasks. |
| `docker.service` | `Faiz`, `observability-reader` | `Faiz`, `break-glass-operator` | `Faiz`, `break-glass-operator` | metadata | High blast radius. |
| `caddy.service` | `Faiz`, `observability-reader` | `Faiz`, `break-glass-operator` | `Faiz`, `break-glass-operator` | metadata | No public app ingress. |
| `tailscaled.service` | `Faiz`, `observability-reader` | `Faiz`, `break-glass-operator` | `Faiz`, `break-glass-operator` | metadata | Lockout risk; recovery path required. |

---

## 14. Tailscale ACL Matrix

| Tailscale Tag | Devices / Principals | Can Reach | Cannot Reach | Notes |
|---|---|---|---|---|
| `tag:owner` | Faiz devices | all internal services | none at policy level | Owner access logged for Critical actions. |
| `tag:service-core` | Guinevere VPS/core | DB, Redis, internal APIs, object storage outbound | public admin ingress | No public ports. |
| `tag:service-ingestor` | Tasker/Windows bridge | surveillance API only | DB direct, Redis direct, admin | HMAC/JWT required. |
| `tag:db` | PostgreSQL/PgBouncer host | accepts from approved service tags | public internet | PgBouncer identity required. |
| `tag:redis` | Redis host | accepts from core/ingestor as scoped | public internet | Redis ACL required. |
| `tag:monitoring` | Prometheus/Grafana | metrics endpoints, logs metadata | raw Critical payload | Metadata-only. |
| `tag:backup` | backup job/service | DB backup, object storage endpoints | persona/runtime APIs unless restore test | Backup key scope required. |
| `tag:break-glass` | emergency device/session | all needed for SEV0/SEV1 | normal runtime use | Max 4h, evidence required. |

ACL policy must deny all unspecified paths. Zero public VPS ingress is mandatory.

---

## 15. Agent, Sub-Agent, and Tool Matrix

| Actor | Read Docs | Read Confidential | Read Restricted | Read Critical | Write Files | Execute Tools | Parent Verification |
|---|---|---|---|---|---|---|---|
| `guinevere_core` | Allow | Allow | Allow if purpose-scoped | Allow only with task/safety/security purpose | Allow | Allow by configured permissions | Self + audit. |
| `sub-agent-researcher` | Allow | Allow summarized | Redacted only | Deny | Research report only | Read/search only | Required. |
| `sub-agent-implementer` | Allow | Task-scoped | Redacted/task-scoped | Deny unless explicit audited exception | Assigned files/evidence only | Implementation tools by task | Required. |
| `readonly-auditor` | Allow | Allow | Redacted | Redacted or denied | Audit report only | Read/search only | Required. |
| `external-integration` | Deny local docs by default | Deny | Deny | Deny | Deny | Provider API only | Provider audit. |

Sub-agent outputs must be file-based for structured reports. Parent must verify file existence, non-empty content, evidence citations, and cross-reference integrity before relying on output.

---

## 16. Secrets, Crypto, Backup, Restore, and Export Matrix

| Action | Allowed Principal | Required Attributes | Denied State | Evidence |
|---|---|---|---|---|
| Read SOPS encrypted file | `secret-rotator`, `guinevere_core` startup | purpose=startup/rotation, Tailscale service identity | sub-agent request, normal audit read | security audit event. |
| Read age private key | `secret-rotator`, `break-glass-operator` | approved purpose, host local, `0600` | report/log/sub-agent | key access event. |
| Decrypt Domain KEK | `guinevere_core`, `secret-rotator`, `break-glass-operator` | data class + purpose + safe-mode gate | persona flavor, sub-agent, observability | crypto audit event. |
| Rotate secret | `secret-rotator` | preflight pass, rollback path, evidence path | safe-word/distress for non-essential; failed preflight | `evidence/secrets-rotation/...`. |
| Rewrap DEK/KEK | `secret-rotator`, `migration-principal` | migration/rotation task ID | missing backup/rollback | crypto migration evidence. |
| Backup write | `backup-operator` | encrypted before upload, classification metadata | plaintext dump | backup evidence. |
| Restore test | `backup-operator` | isolated restore target, evidence | production overwrite without approval | restore evidence. |
| Export dossier | `Faiz`, `guinevere_core` with Faiz request | encryption, redaction option, audit path | sub-agent request, safe-mode without explicit Faiz request | export evidence. |
| Break-glass admin | `break-glass-operator`, `Faiz` | SEV0/SEV1, approval where feasible, max 4h | routine ops | incident evidence. |

---

## 17. Audit and Enforcement

Every allow/deny decision for Restricted or Critical data must be auditable. The audit event must include:

- timestamp
- principal
- role
- action
- resource identifier
- classification
- purpose
- safety state
- decision
- grant expiry when applicable
- approval reference when applicable
- evidence path when applicable

Audit events must not include plaintext secrets, raw intimate content, raw safe-word content beyond minimal event class, or raw surveillance payload when a hash/summary is enough.

### Mandatory Audit Events

| Event | Required |
|---|---|
| Critical data read/decrypt | Yes |
| Restricted export | Yes |
| Critical export | Yes |
| Safe-mode sensitive access attempt | Yes |
| Sub-agent Restricted/Critical request | Yes |
| Break-glass grant/start/end | Yes |
| Secret/key access outside startup | Yes |
| DB migration/grant/RLS change | Yes |
| Object storage lifecycle override | Yes |
| Tailscale ACL/tag change | Yes |
| Denied access to Critical data | Yes |

---

## 18. Break-Glass and Temporary Privilege Grants

Break-glass is allowed only for SEV0 or SEV1 events.

| Rule | Requirement |
|---|---|
| Severity | SEV0/SEV1 only. |
| Approval | Faiz approval required where feasible. |
| Duration | Default 1 hour, hard maximum 4 hours unless Faiz records a new emergency approval. |
| Scope | Minimum resources required for containment/recovery. |
| Evidence | Must create incident/evidence artifact before or immediately after use. |
| Expiry | Grant must auto-expire. |
| Post-use | Revoke grant, verify no residual access, rotate exposed credentials, write post-use review. |
| Forbidden | Routine maintenance, convenience, bypassing missing RBAC, bypassing safe word, unlogged access. |

---

## 19. Implementation Requirements

Runtime implementation must satisfy these requirements before production hardening is considered complete:

| ID | Requirement | Verification |
|---|---|---|
| AC-001 | Define all principals as unique identities; shared credentials are denied. | Identity inventory check. |
| AC-002 | Replace broad PgBouncer roles with matrix-defined least-privilege roles. | Grant diff and DB role audit. |
| AC-003 | Implement RLS or equivalent policy views for classified tables. | SQL policy tests. |
| AC-004 | Add ABAC middleware for API, tool, memory recall, decrypt, export, and sub-agent dispatch. | Policy-control tests. |
| AC-005 | Enforce safe-mode restrictions before persona, memory, surveillance, and tool actions. | Safe-word/distress tests. |
| AC-006 | Add Redis ACL users and prefix restrictions per principal. | Redis ACL test. |
| AC-007 | Add object storage prefix IAM and public-access block validation. | Bucket policy test. |
| AC-008 | Add Tailscale ACL tags and deny-all unspecified routing. | Tailscale policy test. |
| AC-009 | Add break-glass time-boxing and auto-expiry. | SEV0/SEV1 simulation. |
| AC-010 | Add audit events for every Restricted/Critical allow/deny. | Audit log replay test. |
| AC-011 | Add sub-agent access broker with task ID, data-class ceiling, redaction, and parent verification. | Delegation test. |
| AC-012 | Add export gate with encryption, redaction, Faiz request, evidence, and expiry. | Export test. |
| AC-013 | Add migration principal workflow with no broad data browse. | Migration dry run. |
| AC-014 | Add observability redaction views. | Dashboard payload scan. |
| AC-015 | Add policy-as-code tests for all matrix rows. | CI/local test suite. |

---

## 20. Validation and Policy-Control Test Matrix

| Test ID | Scenario | Expected Result |
|---|---|---|
| ACT-001 | `sub-agent-researcher` requests `persona.inner_journal.content`. | Deny; audit event. |
| ACT-002 | `guinevere_core` requests raw surveillance screenshot during safe-word state for persona confrontation. | Deny; minimal safety log. |
| ACT-003 | `surveillance-ingestor` inserts Android activity event. | Allow; classification metadata stored. |
| ACT-004 | `surveillance-ingestor` attempts SELECT from `memory.faiz_profile`. | Deny. |
| ACT-005 | `observability-reader` opens raw log payload containing Critical data. | Deny/redact; redaction event. |
| ACT-006 | `secret-rotator` rotates R2 key with preflight and rollback. | Allow; evidence created. |
| ACT-007 | `secret-rotator` tries scheduled rotation during distress safe-mode. | Deny/pause unless SEV0/SEV1 emergency. |
| ACT-008 | `break-glass-operator` requests 6-hour grant. | Deny; max 4 hours. |
| ACT-009 | `break-glass-operator` requests grant for non-SEV2 convenience task. | Deny; SEV0/SEV1 only. |
| ACT-010 | `migration-principal` applies RLS migration without data browse. | Allow; migration evidence. |
| ACT-011 | `readonly-auditor` reads redacted evidence report. | Allow. |
| ACT-012 | `readonly-auditor` reads raw safe-word log. | Deny/redact. |
| ACT-013 | Export requested without encryption. | Deny. |
| ACT-014 | Redis DB2 key persists beyond TTL. | Fail retention/access test. |
| ACT-015 | Tailscale non-approved tag reaches DB port. | Deny. |

---

## 21. Review Cadence

| Review Type | Cadence | Owner | Output |
|---|---|---|---|
| Access matrix review | Monthly | Faiz + Guinevere | `audit-reports/<date>-access-control-review.md` |
| Principal inventory review | Monthly | Guinevere | Access inventory diff. |
| Critical access audit | Daily scan + monthly review | Guinevere | Critical access summary. |
| Break-glass review | After each use | Faiz + Guinevere | Incident/evidence artifact. |
| Tailscale ACL review | Monthly and after device change | Guinevere | ACL diff artifact. |
| DB grants/RLS review | After migration and monthly | Guinevere | Grant diff artifact. |
| Sub-agent access review | After each material delegation | Parent agent | Sub-agent report verification. |

---

## 22. Unresolved Assumptions and Backlog

| ID | Assumption / Gap | Owner | Impact | Follow-up Document / Trigger |
|---|---|---|---|---|
| BG-001 | Full Incident Response & Postmortem Runbook is not yet authoritative. | Guinevere | Break-glass and SEV handling lack full lifecycle owner/due-date model. | Create `Guinevere_IncidentResponse_PostmortemRunbook_v1.0.md`. |
| BG-002 | SQL DDL, RLS policies, and grants are specified as matrix controls but not implemented. | Guinevere | Runtime access can remain broad until migrations land. | Database ERD & Migration Strategy. |
| BG-003 | Consent & Revocation Policy is not yet standalone. | Guinevere | Faiz rights and safe-mode revocation need formal UX/runtime workflow. | Consent & Revocation Policy. |
| BG-004 | Tailscale ACL file is not yet generated. | Guinevere | Network enforcement remains conceptual until ACL config exists. | Tailscale ACL implementation artifact. |
| BG-005 | Policy-as-code engine is not chosen. | Guinevere | ABAC evaluation can drift across code paths. | Authorization Middleware Spec. |
| BG-006 | Exact FastAPI endpoint list can expand during implementation. | Guinevere | Endpoint matrix needs update on API changes. | API Contract OpenAPI Spec. |
| BG-007 | Object storage bucket names may differ at deployment. | Guinevere | Prefix IAM must be validated against actual buckets. | Deployment Runbook / Storage Inventory. |

---

## Appendix A — Principal Inventory

| Principal | Credential Type | Rotation Source | Disable Path | Audit Required |
|---|---|---|---|---|
| Faiz | Human device/Tailscale/admin auth | Owner-managed | Revoke device/session | Critical actions only. |
| `guinevere_core` | service account + DB/Redis/API creds | Secrets Rotation Runbook | stop service + revoke creds | Yes. |
| `sub-agent-researcher` | task-scoped runtime identity | broker-generated | end task/session | Yes. |
| `sub-agent-implementer` | task-scoped runtime identity | broker-generated | end task/session | Yes. |
| `surveillance-ingestor` | device HMAC/JWT | Secrets Rotation Runbook | revoke device secret | Yes. |
| `financial-ingestor` | service credential | Secrets Rotation Runbook | revoke credential | Yes. |
| `backup-operator` | service credential + backup key | Secrets Rotation Runbook | disable job/revoke key | Yes. |
| `observability-reader` | dashboard/service credential | Secrets Rotation Runbook | revoke user/token | Yes. |
| `secret-rotator` | privileged service credential | Secrets Rotation Runbook | revoke credential | Yes. |
| `break-glass-operator` | emergency credential | Break-glass package | auto-expire/revoke | Yes. |
| `migration-principal` | migration credential | Secrets Rotation Runbook | revoke/expire | Yes. |
| `external-integration` | provider token | provider-specific rotation | revoke provider token | Yes. |
| `readonly-auditor` | audit identity | periodic review | revoke audit identity | Yes. |

---

## Appendix B — Break-Glass Checklist

- Confirm incident severity is SEV0 or SEV1.
- Record reason, scope, start time, intended duration, resources, and approving authority.
- Obtain Faiz approval where feasible.
- Grant only required role/resource/action.
- Set expiry to 1 hour by default and never more than 4 hours without new recorded approval.
- Capture audit events for every action.
- Revoke at completion or expiry.
- Rotate exposed credentials or keys.
- Verify no residual grants remain.
- Write post-use incident/evidence report.

---

## Appendix C — Audit Checklist

| Check | Pass Criteria |
|---|---|
| Principal inventory complete | All 13 principals present. |
| Role matrix complete | Every principal maps to one or more roles. |
| ABAC rules implemented | Deny-by-default and safe-mode rules present. |
| DB grants narrow | No broad all-schema runtime role remains. |
| Redis ACL scoped | DB/prefix/op restrictions present. |
| Object storage private | Public ACL denied. |
| API endpoints gated | Tailscale + service identity + replay protection present. |
| Filesystem secrets protected | age key and tmp env protected. |
| systemd restart scoped | High-blast-radius services restricted. |
| Tailscale ACL deny-all | Unspecified routes denied. |
| Break-glass bounded | SEV0/SEV1, max 4 hours, evidence. |
| Sub-agent Critical access denied | Default deny confirmed. |
| Audit logs safe | No plaintext secret or raw Critical payload. |

---

## Appendix D — Review Record

- **Reviewer:** Faiz
- **Review Date:** 2026-05-30
- **Decision:** Accepted
- **Notes:** Approved as normative access-control matrix under ADR-019/ADR-018/ADR-024/ADR-012 and related policies. Safe-mode restrictions are mandatory in all matrices. Break-glass is limited to SEV0/SEV1, maximum 4 hours, with Faiz approval where feasible.

---

## Appendix E — Next Recommended Document

**Recommended next document:** `Guinevere_IncidentResponse_PostmortemRunbook_v1.0.md`.

**Reason:** This matrix defines break-glass, SEV0/SEV1, containment, audit, key rotation, safe-mode, and post-use evidence requirements, but the full incident lifecycle is not yet authoritative. The next document must define severity triage, commander role, timeline, containment, forensic evidence, Faiz notification, postmortem format, action owners, due dates, recurrence prevention, and closure criteria.

---

**End of Guinevere Access Control RBAC/ABAC Matrix v1.0**
