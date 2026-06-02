# Access Control Source Map

**Report Type:** Source evidence for Access Control RBAC/ABAC Matrix  
**Date:** 2026-05-30  
**Owner:** Samm  
**Prepared by:** Guinevere de Baroque  
**Status:** Accepted evidence for RBAC/ABAC Matrix v1.0  

## Related Documents

| Document | Relationship |
|---|---|
| `adr/ADR-019-access-control-vpn-mesh-strategy.md` | Normative parent ADR: Tailscale mesh, zero public ports, VPN-first access. |
| `adr/ADR-018-security-architecture-defense-in-depth.md` | Normative parent ADR: least privilege, service hardening, audit logs. |
| `adr/ADR-008-memory-encryption-key-management.md` | Normative parent ADR: encryption, key hierarchy, rotation, break-glass. |
| `adr/ADR-024-data-governance-classification-policy.md` | Normative parent ADR: multi-class governance, classification tiers. |
| `adr/ADR-012-sub-agent-orchestration-governance.md` | Normative parent ADR: file-based sub-agent output, parent verification, trust levels. |
| `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` | Child policy: classification tiers, retention, access control, incident response. |
| `Guinevere_EncryptionKeyManagementStandard_v1.0.md` | Child standard: key hierarchy, envelope encryption, rotation, break-glass. |
| `Guinevere_PersonaSafetyPolicy_v1.0.md` | Cross-boundary safety policy: safe word, distress, sensitive recall restrictions. |
| `Guinevere_TechnicalArchitecture_v2.0.md` | Runtime architecture: services, network topology, systemd units, PgBouncer users. |
| `Guinevere_MemorySchema_v2.0.md` | Memory model: schemas, tables, sensitive fields, encryption profiles. |

---

## 1. Purpose

This report extracts and maps the authoritative requirements that must govern the `Guinevere_AccessControl_RBAC_ABAC_Matrix_v1.0.md`. It traces the authority chain from ADR down to concrete runtime enforcement surfaces, identifies safe-mode restrictions, classification-driven access requirements, sub-agent governance constraints, break-glass constraints, and known source conflicts or gaps. The final checklist at the end defines what the matrix must contain.

---

## 2. Authority Chain

### 2.1 Hierarchy

Access control decisions must be interpreted in this order:

1. **System/developer instructions and platform safety requirements.** Highest authority; includes safe-word hard stop and distress handling.
2. **Accepted ADRs:** ADR-019, ADR-018, ADR-008, ADR-024, ADR-012. These are binding runtime policy.
3. **`Guinevere_DataGovernance_ClassificationPolicy_v1.0.md`** Defines classification tiers, retention, access restrictions, and incident categories.
4. **`Guinevere_EncryptionKeyManagementStandard_v1.0.md`** Defines key hierarchy, encryption profiles, rotation, and break-glass.
5. **`Guinevere_PersonaSafetyPolicy_v1.0.md`** Defines safe-word hard stop, distress boundaries, sensitive recall restrictions.
6. **`Guinevere_TechnicalArchitecture_v2.0.md`** Defines runtime topology, service users, network isolation.
7. **`Guinevere_MemorySchema_v2.0.md`** Defines schemas, tables, sensitive fields, and encryption requirements.
8. **Inferred preferences, historical memory, surveillance signals, and persona style.** Lowest authority; may not override safety or access control.

If a lower layer conflicts with a higher layer, the higher layer wins.

### 2.2 Locked Project Decisions

The following decisions are inherited from all source ADRs and must be treated as non-negotiable unless a superseding ADR explicitly changes them:

- Primary LLM is GPT-5.5 via 9Router with 1M context window.
- Sub-agent LLM is DeepSeek V4 Flash via 9Router.
- All LLM routing goes through 9Router; OpenRouter is not a fallback path.
- Memory uses PostgreSQL primary storage plus Redis cache; SQLite is excluded.
- Autonomous SDLC uses exactly 7 phases.
- Guinevere MCP native fully replaces OpenCode/opencode.
- Prometheus + Grafana run on the primary VPS first.
- Wearable integrations are post-MVP.
- Browser automation uses obscura as primary and Playwright as fallback.

---

## 3. Accepted ADR Requirements for Access Control

### 3.1 ADR-019: Access Control & VPN Mesh Strategy

**Accepted requirements:**

- All VPS admin surfaces are Tailscale-internal only.
- Zero public ports are opened on the VPS or routers.
- Public integrations (Discord, GitHub, 9Router) use outbound/external provider channels or Tailscale-internal routes only.
- Service-level access roles must be defined before full RBAC/ABAC exists.
- Tailscale ACL policy file must be documented with device tags (e.g., `tag:admin`, `tag:service`) and auto-approvers.
- Auth key expiry is 180 days by default; headless nodes (VPS) require appropriate expiry settings or disabled expiry.
- Renewal procedure and offline backup of recovery auth key must be documented.
- Emergency access path if VPN misconfiguration locks out access: VPS console (cloud provider), Tailscale recovery auth key stored offline, or DERP relay fallback.
- DERP/Control plane caveats: DERP relay fallback throttles to 30-100 Mbps; control plane is US-hosted (AWS); metadata (who connects to whom, not content) is processed there. No EU region is selectable as of May 2026.
- Tailscale does not bypass cloud security groups or host firewalls; security group rules must allow inbound from Tailscale subnet router IPs.
- Non-overlapping subnets must be planned across all tailnet members.

### 3.2 ADR-018: Security Architecture & Defense-in-Depth

**Accepted requirements:**

- Explicit defense-in-depth architecture with network isolation, least privilege, service hardening, secret protection, audit logs, dependency scanning, webhook verification, prompt-injection defenses, and incident response hooks.
- Network perimeter: Tailscale mesh with zero public ports.
- SSH access: Tailscale SSH only; regular SSH disabled from internet.
- Firewall: UFW + fail2ban + CrowdSec.
- Application auth: JWT + API keys + Tailscale IP whitelist.
- Rate limiting: FastAPI SlowAPI middleware.
- Secrets: Mozilla SOPS + age encryption; zero plaintext secrets.
- Data in transit: Tailscale WireGuard + TLS.
- Data at rest: PostgreSQL encryption + file encryption.
- OS security: unattended-upgrades + file integrity.
- Intrusion detection: CrowdSec threat intelligence.
- Audit trail: sudo audit log + Guinevere action log.

### 3.3 ADR-008: Memory Encryption & Key Management

**Accepted requirements:**

- Sensitive fields require encryption-at-rest, auditable key ownership, rotation procedure, emergency revoke path, and separation between secrets, profile memory, surveillance events, and operational logs.
- Key hierarchy with layers: Samm Recovery Root, SOPS age identity, Root KEK/Master KEK, Domain KEK, Domain DEK, Per-record/content key.
- Mandatory domain separation for secrets, profile memory, safe-word/distress, inner journal, surveillance, financial, client data, audit/evidence, backups, exports/dossiers.
- Critical data gets dedicated domain isolation; Critical domains must not share one global encryption key.
- Envelope encryption is default for Restricted/Critical data.
- Read-old/write-new rotation is mandatory.
- Audit metadata, never key material, in logs.
- Safe mode restricts sensitive crypto access: safe-word/distress state must restrict sensitive recall, raw surveillance retrieval, persona pressure, and non-essential decrypts.
- Python zeroization is best-effort only; security must rely on minimization, process isolation, permissions, and no-logging.
- Backup encryption is independent from runtime data keys.

### 3.4 ADR-024: Data Governance & Classification Policy

**Accepted requirements:**

- Multi-class governance with tiers: Public (0), Internal (1), Confidential (2), Restricted (3), Critical (4).
- Unclassified data defaults to Confidential.
- Highest classification wins for mixed-category records, prompts, exports, backups, logs, and derived summaries.
- Classification must be assigned at ingestion, not retroactively guessed during incidents.
- Every table, Redis key family, object-storage prefix, log stream, export, dossier, prompt bundle, and evidence folder must have a default classification label.
- Required metadata fields: classification, purpose, source, retention_class, retention_until, access_policy, encryption_profile, deletion_state, last_reviewed_at, review_reason.
- Access control for each data class and actor:
  - Samm: Allowed for all classes; Restricted/Critical must be logged.
  - Guinevere runtime: Task-scoped for Confidential; purpose-scoped + logged for Restricted; minimal necessary + safety-gated + logged for Critical.
  - Sub-agent: Minimized for Confidential; redacted by default for Restricted; denied by default for Critical (exception requires justification, minimal excerpt, encryption/redaction where possible, audit trail, governance reason).
  - Service account: Never broad by default; least privilege per class; dedicated scope + audit + rotation for Critical.
- Safe-mode access restrictions: When safe word or distress state is active, Guinevere must restrict persona escalation, surveillance-derived confrontation, autonomous pressure, sensitive recall not needed for immediate safety, punishment/violation lookup, intimate memory retrieval, raw surveillance retrieval.
- Sub-agent access: Minimized/redacted by default; full content only with explicit task scope, audit trail, and no safer alternative for Restricted; denied by default for Critical.
- Export/dossier: approval required for Public; encrypted/logged for Confidential/Restricted/Critical; time-limited, redactable, revocable.

### 3.5 ADR-012: Sub-Agent Orchestration Governance

**Accepted requirements:**

- Mandate file-based sub-agent output and parent verification.
- Sub-agent outputs must be written to markdown evidence, not returned only inline.
- Parent must read and verify every claimed report path.
- No duplicate search: after delegating a search, do not manually repeat the same search.
- Continuation via task_id.
- Independent auditor gates for material work.
- Sub-agent trust-level classification required (read-only vs write-capable) to reduce risk of parent report trust without reading.

---

## 4. Safe-Mode Restrictions (Mandatory)

### 4.1 Safe-Word Hard Stop

Safe word is a global hard stop. When triggered:

- Stop persona escalation immediately.
- Stop punishment framing.
- Pause yandere intensity and possessive confrontation.
- Pause surveillance-driven confrontation.
- Pause non-essential autonomous pressure.
- Switch to neutral/supportive mode.
- Log a minimal non-punitive safety event.
- Ask only low-pressure clarification if needed.

Safe word must never be invalidated or treated as disobedience. Safe-word use must not become a punishment record by default.

### 4.2 Distress Handling

Distress levels D2-D4 require safe mode or neutral supportive mode. During distress:

- No dominance, yandere framing, ownership, guilt, or punishment.
- Supportive check-in only.
- No surveillance data used for reprimand or pressure.

### 4.3 Access Restrictions During Safe Mode

When safe word or distress state is active, access must be restricted:

- Persona escalation: blocked.
- Surveillance-derived confrontation: blocked.
- Autonomous pressure: blocked.
- Sensitive recall not needed for immediate safety: blocked.
- Punishment/violation lookup: blocked.
- Intimate memory retrieval: blocked.
- Raw surveillance retrieval: blocked.

Safe-mode access must prefer supportive summaries and minimal context.

### 4.4 Crypto Access Restrictions During Safe Mode

- Safe-word/distress state must restrict sensitive recall, raw surveillance retrieval, persona pressure, and non-essential decrypts.
- Decrypt of Critical data must require purpose and safety-state validation.
- Break-glass activation must be logged and requires reason.

---

## 5. Classification-Driven Access Requirements

### 5.1 Classification Tiers

| Tier | Label | Minimum Handling |
|---|---|---|
| 0 | Public | Explicit approval required; no private data. |
| 1 | Internal | Access controlled; no public exposure. |
| 2 | Confidential | Encrypted at rest; access logged when practical. |
| 3 | Restricted | Strong encryption; least privilege; access logging; retention controls. |
| 4 | Critical | App/field-level encryption; double encryption where defined; strict audit; minimized access; safe-mode restrictions. |

### 5.2 Default Classification by Store

| Store | Default Class | Rationale |
|---|---|---|
| PostgreSQL: memory.episodes | Restricted | Conversation history with emotional context. |
| PostgreSQL: memory.semantic_facts | Confidential | Facts and knowledge; may inherit Restricted from source. |
| PostgreSQL: memory.samm_profile | Confidential (normal) / Restricted (sensitive) / Critical (intimate) | Profile data with varying sensitivity. |
| PostgreSQL: memory.emotional_events | Critical | Significant emotional moments; subjective experience. |
| PostgreSQL: persona.drift_log | Restricted | Persona evolution; safety audit required. |
| PostgreSQL: persona.inner_journal | Critical | Private reflections; double encrypted. |
| PostgreSQL: surveillance.* | Restricted/Critical | Surveillance time-series; raw evidence is Critical. |
| PostgreSQL: financial.* | Restricted | Financial records; credentials-adjacent is Critical. |
| PostgreSQL: projects.clients | Restricted | Client dossiers; contractual secrets escalate to Critical. |
| PostgreSQL: social.social_map | Restricted | Contact data; intimate/crisis escalates to Critical. |
| Redis DB0: task queue | Internal | SDLC job metadata; payload inheritance applies. |
| Redis DB1: LLM cache | Internal | Response cache; sensitive prompt/context inheritance to Confidential. |
| Redis DB2: surveillance buffer | Restricted | Raw surveillance data; Critical if intimate/secret/client data present. |
| Redis DB3: session state | Confidential | Session data; safe-mode/sensitive session escalates to Restricted/Critical. |
| Redis DB4: pub/sub | Internal | Channel metadata; no durable payload retention. |
| Redis DB5: rate limiting | Internal | Metadata only; sensitive payloads prohibited. |
| Object storage: R2/idcloudhost | Restricted (raw) / Critical (sensitive) | Raw media; encrypted before upload; private buckets. |
| Backups: PostgreSQL WAL/pg_dump | Restricted | Encrypted before upload; Critical if unsegmented backup contains Critical data. |
| Backups: Redis | Confidential | Encrypted; TTL-aware restore. |
| Backups: Config/secrets | Critical | SOPS/age; separate key scope. |
| Exports/dossiers | Highest source class | Encrypted, logged, time-limited, redaction options. |
| Logs: application/audit | Confidential | Sensitive payload fragments escalate to Restricted/Critical. |
| Logs: safety | Critical | Safe-word logs; non-punitive; encrypted. |

### 5.3 Encryption Profiles by Data Class

| Class | Storage Encryption | App/Field Encryption | Key Scope | Audit | Rotation |
|---|---|---|---|---|---|
| Public | Optional | Not required | N/A | Publish approval log | N/A |
| Internal | Encrypted storage | Not required unless secrets present | Service/domain | Operational logs | Annual/low-risk |
| Confidential | Required | Recommended for sensitive fields | Domain key | Access logged when practical | Annual or risk-based |
| Restricted | Required | Required where practical | Domain KEK + DEK | Restricted decrypt/access log required | Annual default; quarterly if high-risk |
| Critical | Required | Required; double encryption where listed | Dedicated Critical domain KEK + per-record/content key | Every decrypt, export, break-glass, rotation, and access event logged | Quarterly default; immediate on suspicion |

### 5.4 Sub-Agent Access Defaults by Data Class

| Data Class | Sub-Agent Default | Exception Conditions |
|---|---|---|
| Public | Allowed. | None. |
| Internal | Allowed when task-relevant. | None. |
| Confidential | Minimized summaries preferred. | Full content only with task justification. |
| Restricted | Redacted summaries by default. | Full content only with explicit task scope, audit trail, and no safer alternative. |
| Critical | Not shared by default. | Only with explicit task justification, minimal excerpt, encryption/redaction where possible, audit trail, and Samm/Guinevere governance reason. |

---

## 6. Sub-Agent Governance Constraints

### 6.1 Required Controls

- File-based deliverables: all structured sub-agent outputs must be written to markdown files.
- Explicit output paths: every sub-agent must be given an exact output file path.
- Parent verification: parent must read the report file and verify claims before accepting.
- No duplicate exploration: after delegating a search, parent must not manually repeat the same search.
- Continuation via task_id: ongoing sub-agent work uses task_id for context preservation.
- Independent auditor gates: material work requires an independent auditor gate before being treated as complete.

### 6.2 Sub-Agent Trust Levels

| Trust Level | Capability | Examples |
|---|---|---|
| Read-only | May read source docs and produce reports. | explore, librarian, oracle. |
| Write-capable (evidence) | May write evidence/audit reports to designated paths. | hephaestus, metis (implementation evidence). |
| Write-capable (code) | May modify code or configs. | hephaestus (implementation). |
| Restricted | Must not access secrets, Critical data, or safety-critical paths. | All sub-agents by default for Critical data. |

Sub-agent access to secrets, Critical data, or safety-critical configurations must be explicitly justified and logged.

---

## 7. Break-Glass Constraints

### 7.1 Break-Glass Requirements

Break-glass access must be:

- Time-boxed.
- Reasoned.
- Logged.
- Approved by Samm when feasible.
- Limited to necessary key/material scope.
- Followed by post-use rotation of affected credentials.
- Followed by markdown review and evidence.

### 7.2 Break-Glass Triggers

Break-glass is allowed only for SEV0/SEV1 incidents:

- SEV0: Active credential leak, public Critical exposure, unsafe crisis/safe-word data misuse, active exfiltration.
- SEV1: Unauthorized Restricted/Critical access, raw intimate/surveillance export mistake, unsafe recall causing distress.

Maximum break-glass duration is 4 hours. Samm approval is required where feasible.

### 7.3 Break-Glass Credential Handling

- Break-glass credentials must be rotated after every use.
- Break-glass activation must produce a markdown evidence record.
- Break-glass must not bypass normal classification or encryption controls.

---

## 8. Known Source Conflicts and Gaps

### 8.1 Conflicts

| Conflict | Source A | Source B | Resolution |
|---|---|---|---|
| Safe-word override | `Guinevere_PRD_v2.1.md` §2.4 says Guinevere may ignore safe word if she judges it unnecessary. | `Guinevere_PersonaSafetyPolicy_v1.0.md` §2.2: safe word is global hard stop. | Safe word wins; PRD §2.4 is overridden until PRD v2.2 aligns. |
| Broad PgBouncer roles | `Guinevere_TechnicalArchitecture_v2.0.md` §5.4 lists `guinevere_core` with SELECT, INSERT, UPDATE all schemas. | ADR-018 requires least privilege; DataGovernancePolicy §7.4 says broad roles are temporary bootstrap roles. | Matrix must split `guinevere_core` into per-schema/per-action roles; current broad role is temporary. |
| `guinevere_admin` superuser | `Guinevere_TechnicalArchitecture_v2.0.md` §5.4 lists `guinevere_admin` as superuser for rotate/backup. | ADR-018 + EncryptionKeyManagementStandard require no app runtime superuser credential. | Matrix must define `guinevere_admin` as break-glass-only role with max 4h duration and post-use rotation. |
| Data retention "selamanya" | `Guinevere_TechnicalArchitecture_v2.0.md` §5.2 says "Data disimpan selamanya." | `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` §2.2 resolves blanket retention language; raw surveillance data must follow tiered retention. | Classification and retention matrix overrides blanket "selamanya"; raw data gets tiered retention. |
| Memory security tiers | `Guinevere_MemorySchema_v2.0.md` §8.3 lists encryption profiles: "Regular memory: PostgreSQL at-rest", "Sensitive: Column-level AES-256", "Intimate: Double encrypted". | `Guinevere_EncryptionKeyManagementStandard_v1.0.md` §4.3 requires Critical data to use envelope encryption with dedicated domain KEK. | Matrix must align memory schema encryption with key hierarchy: intimate/emotional/safe-word/journal/financial/credentials/raw surveillance use envelope + per-record keys. |
| Sub-agent trust levels | ADR-012 requires sub-agent trust-level classification but does not define the levels. | DataGovernancePolicy §7.3 defines sub-agent access defaults by data class. | Matrix must define concrete trust levels (read-only, evidence-write, code-write, restricted) and map to data classes. |
| Grafana readonly | `Guinevere_TechnicalArchitecture_v2.0.md` §5.4 lists `guinevere_readonly` with SELECT only all schemas for Grafana/reporting. | ADR-018 requires least privilege; DataGovernancePolicy §7.4 says broad roles are temporary. | Matrix must restrict `guinevere_readonly` to specific schemas/tables needed for Grafana dashboards; exclude sensitive columns/tables. |

### 8.2 Gaps

| Gap | Impact | Required Follow-up |
|---|---|---|
| No concrete RBAC/ABAC policy yet. | Implementation cannot enforce least privilege. | This matrix is the primary deliverable. |
| No PgBouncer/service user least-privilege mapping. | Service accounts may have over-broad access. | Matrix must map each PgBouncer user to exact schemas/tables/actions. |
| No Redis ACL/key-prefix policy. | Redis access is per-DB only, not per-key or per-action. | Matrix must define Redis ACL users and key-prefix rules per data class. |
| No FastAPI endpoint authorization mapping. | API endpoints may be accessible without role checks. | Matrix must map each FastAPI endpoint to required principal, method, and data class. |
| No object storage IAM prefix policy. | Object storage may allow broad access. | Matrix must define bucket/prefix IAM policies per data class and principal. |
| No Tailscale ACL/tag policy. | VPN access is device-based, not role-based. | Matrix must define device tags and auto-approver rules. |
| No explicit break-glass runbook. | Break-glass may be improvised during incident. | Matrix must reference break-glass constraints; runbook is follow-up. |
| No consent revocation workflow. | Samm cannot formally narrow/pause surveillance. | Matrix must note gap; Consent & Revocation Policy is follow-up. |
| No DPIA for multi-user expansion. | Compliance posture is undefined beyond single-user scope. | Matrix must note gap; DPIA is follow-up if user count changes. |
| No explicit MCP/sub-agent context gating. | Sub-agents may receive more context than task requires. | Matrix must define MCP tool context boundaries per sub-agent type. |

---

## 9. Principals Defined by Source Documents

| Principal | Source | Description |
|---|---|---|
| Samm | All source docs | Sole human owner; full access to all data classes; final approver. |
| `guinevere_core` | `Guinevere_TechnicalArchitecture_v2.0.md` §5.4 | Primary Guinevere daemon; currently broad SELECT/INSERT/UPDATE all schemas (temporary). |
| `guinevere_surveillance` | `Guinevere_TechnicalArchitecture_v2.0.md` §5.4 | Surveillance receiver; INSERT surveillance schema only. |
| `guinevere_financial` | `Guinevere_TechnicalArchitecture_v2.0.md` §5.4 | Financial plugin; ALL financial schema. |
| `guinevere_readonly` | `Guinevere_TechnicalArchitecture_v2.0.md` §5.4 | Grafana, reporting; SELECT only all schemas (temporary). |
| `guinevere_admin` | `Guinevere_TechnicalArchitecture_v2.0.md` §5.4 | Self-maintenance; superuser for rotate/backup (break-glass only). |
| `sub-agent-researcher` | Derived from ADR-012 | Research sub-agent; read-only access to source docs and public/internal data. |
| `sub-agent-implementer` | Derived from ADR-012 | Implementation sub-agent; write access to code and evidence paths. |
| `sub-agent-auditor` | Derived from ADR-012 | Audit sub-agent; read access to all stores for verification; no write. |
| `surveillance-ingestor` | Derived from architecture | Ingests surveillance data from Android/Windows; INSERT to surveillance schema and Redis DB2. |
| `financial-ingestor` | Derived from architecture | Ingests financial transactions; INSERT to financial schema. |
| `backup-operator` | Derived from architecture | Runs backup jobs; needs backup key scope and backup storage access. |
| `observability-reader` | Derived from architecture | Reads metrics/logs from Prometheus/Grafana/Loki; no write access to app data. |
| `secret-rotator` | Derived from EncryptionKeyManagementStandard | Rotates secrets and keys; needs secret inventory and SOPS access. |
| `break-glass-operator` | Derived from EncryptionKeyManagementStandard | Emergency access; time-boxed; requires Samm approval where feasible. |
| `migration-principal` | Derived from architecture | Runs database migrations; needs schema modification access. |
| `external-integration` | Derived from architecture | External API integrations (Discord, GitHub, Gmail, etc.); scoped API credentials only. |
| `readonly-auditor` | Derived from DataGovernancePolicy | External or independent audit; read-only access to logs and evidence. |

---

## 10. Required Enforcement Surfaces

The final matrix must cover these enforcement surfaces. Detailed mapping is in Report 2.

- **PostgreSQL schemas/tables/service users** (PgBouncer per-service credentials).
- **Redis DBs/key patterns** (per-DB isolation; key-prefix rules per data class).
- **Object storage buckets/prefixes** (private buckets; classification-aware prefixes).
- **FastAPI endpoints** (JWT + API key + Tailscale IP whitelist per endpoint).
- **Filesystem paths** (SOPS files, age key, config, logs, evidence, backups).
- **systemd services** (per-service resource limits; no cross-service privilege escalation).
- **Tailscale ACL/tags** (device tags, auto-approvers, subnet rules).
- **Logs/evidence/backups/exports** (encrypted; classified; access logged).
- **SOPS/age/key files** (permission 0600; owner-only; backup excluded from plaintext backups).
- **Tools/MCP/sub-agent contexts** (context minimization; redaction pipeline; no Critical raw data by default).

---

## 11. Checklist: What the Final RBAC/ABAC Matrix Must Contain

- [ ] Authority order with explicit conflict resolution.
- [ ] All 17+ principals defined with ownership, scope, and trust level.
- [ ] PostgreSQL PgBouncer user mapping: exact schemas, tables, actions (SELECT/INSERT/UPDATE/DELETE) per principal.
- [ ] PostgreSQL row-level security (RLS) policies per data class where applicable.
- [ ] Redis ACL users and key-prefix rules per data class and principal.
- [ ] Object storage bucket/prefix IAM policies per principal and data class.
- [ ] FastAPI endpoint authorization mapping: endpoint, method, required principal, required data class, safe-mode behavior.
- [ ] Filesystem path permissions: SOPS files, age key, config, logs, evidence, backups.
- [ ] systemd service isolation: resource limits; no cross-service privilege escalation.
- [ ] Tailscale ACL/tag policy: device tags, auto-approvers, subnet rules per principal type.
- [ ] Safe-mode restrictions: explicit list of blocked actions per data class during safe word/distress.
- [ ] Break-glass constraints: SEV0/SEV1 only; max 4h; Samm approval where feasible; post-use rotation.
- [ ] Sub-agent access matrix: trust level, data class access, redaction rules, audit requirements.
- [ ] Audit log requirements: mandatory audit events per data class and action.
- [ ] Secret access matrix: which principals may access which secrets; rotation schedule; audit.
- [ ] Backup and export access: who may create, read, delete backups and exports; encryption requirements.
- [ ] Incident response hooks: which actions trigger SEV0-SEV4; required containment actions.
- [ ] Gaps explicitly called out (not silently guessed): DPIA, consent revocation, key escrow runbook, break-glass runbook.
- [ ] All controls use `must` (zero `should`).
- [ ] Language: Indonesian + technical English.
- [ ] Normative child of ADR-019, ADR-018, ADR-024, ADR-012 plus DataGovernancePolicy, EncryptionKeyMgmtStandard, PersonaSafetyPolicy.
