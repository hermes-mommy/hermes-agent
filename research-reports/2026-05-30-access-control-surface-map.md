# Access Control Surface Map

**Report Type:** Implementation surface evidence for Access Control RBAC/ABAC Matrix  
**Date:** 2026-05-30  
**Owner:** Samm  
**Prepared by:** Guinevere de Baroque  
**Status:** Accepted evidence for RBAC/ABAC Matrix v1.0  

## Related Documents

| Document | Relationship |
|---|---|
| `adr/ADR-019-access-control-vpn-mesh-strategy.md` | Normative parent ADR: Tailscale mesh, zero public ports. |
| `adr/ADR-018-security-architecture-defense-in-depth.md` | Normative parent ADR: least privilege, service hardening, audit logs. |
| `adr/ADR-008-memory-encryption-key-management.md` | Normative parent ADR: key hierarchy, encryption, break-glass. |
| `adr/ADR-024-data-governance-classification-policy.md` | Normative parent ADR: classification tiers, access control. |
| `adr/ADR-012-sub-agent-orchestration-governance.md` | Normative parent ADR: sub-agent file-based output, trust levels. |
| `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` | Child policy: classification tiers, retention, access control, incident response. |
| `Guinevere_EncryptionKeyManagementStandard_v1.0.md` | Child standard: key hierarchy, envelope encryption, rotation, break-glass. |
| `Guinevere_PersonaSafetyPolicy_v1.0.md` | Cross-boundary safety policy: safe word, distress, sensitive recall restrictions. |
| `Guinevere_TechnicalArchitecture_v2.0.md` | Runtime architecture: services, network topology, systemd units, PgBouncer users. |
| `Guinevere_MemorySchema_v2.0.md` | Memory model: schemas, tables, sensitive fields, encryption profiles. |
| `research-reports/2026-05-30-access-control-source-map.md` | Source evidence report for this matrix. |

---

## 1. Purpose

This report maps the concrete enforcement surfaces where access control must be implemented. Each surface is traced to its source document requirement, current state, and the specific permission rules the final RBAC/ABAC Matrix must define. This is not the matrix itself; it is the evidence base for writing the matrix.

---

## 2. Principals

The following principals must exist in the final matrix. Names and descriptions are derived from source documents and architecture.

| Principal | Source | Description | Trust Level |
|---|---|---|---|
| `Samm` | All source docs | Sole human owner; full access to all data classes; final approver. | Owner |
| `guinevere_core` | `TechnicalArchitecture_v2.0.md` §5.4 | Primary Guinevere daemon; all persona, memory, task, and orchestration logic. | Write-capable (code) |
| `sub-agent-researcher` | Derived from ADR-012 | Research sub-agent; read-only access to source docs and public/internal data. | Read-only |
| `sub-agent-implementer` | Derived from ADR-012 | Implementation sub-agent; write access to code and evidence paths. | Write-capable (evidence) |
| `surveillance-ingestor` | Derived from architecture | Ingests surveillance data from Android/Windows; INSERT to surveillance schema and Redis DB2. | Write-capable (data) |
| `financial-ingestor` | Derived from architecture | Ingests financial transactions; INSERT to financial schema. | Write-capable (data) |
| `backup-operator` | Derived from architecture | Runs backup jobs; needs backup key scope and backup storage access. | Write-capable (ops) |
| `observability-reader` | Derived from architecture | Reads metrics/logs from Prometheus/Grafana/Loki; no write access to app data. | Read-only |
| `secret-rotator` | Derived from EncryptionKeyManagementStandard | Rotates secrets and keys; needs secret inventory and SOPS access. | Write-capable (ops) |
| `break-glass-operator` | Derived from EncryptionKeyManagementStandard | Emergency access; time-boxed; requires Samm approval where feasible. | Restricted |
| `migration-principal` | Derived from architecture | Runs database migrations; needs schema modification access. | Write-capable (ops) |
| `external-integration` | Derived from architecture | External API integrations (Discord, GitHub, Gmail, etc.); scoped API credentials only. | Write-capable (external) |
| `readonly-auditor` | Derived from DataGovernancePolicy | External or independent audit; read-only access to logs and evidence. | Read-only |

---

## 3. PostgreSQL / PgBouncer Enforcement Surfaces

### 3.1 Schemas and Tables

| Schema | Tables | Default Classification | Sensitive Tables/Columns | Source |
|---|---|---|---|---|
| `memory` | episodes, semantic_facts, procedural_skills, lessons_learned, best_practices, samm_predictions, version_history | Restricted (episodes) / Confidential (semantic_facts) / Confidential (procedural) | `samm_profile` (Critical for intimate), `emotional_events` (Critical), `inner_journal` (Critical) | `MemorySchema_v2.0.md` §1-8; `DataGovernance_ClassificationPolicy_v1.0.md` §5 |
| `persona` | drift_log, mood_history, samm_profile, identity, inner_journal | Restricted (drift_log) / Critical (inner_journal) | `inner_journal.content` (BYTEA, double encrypted), `samm_profile` (Critical for intimate) | `MemorySchema_v2.0.md` §5; `PersonaSafetyPolicy_v1.0.md` §16 |
| `behavior` | violation_log, reward_streak, goals, mommy_score | Restricted | Safe-word events must not be marked as violations by default. | `PersonaSafetyPolicy_v1.0.md` §10.2, §11 |
| `surveillance` | activity_log, location_history, health_data, messages, screenshots | Restricted (summary) / Critical (raw) | Raw screenshots, raw messages, raw location traces are Critical. | `DataGovernance_ClassificationPolicy_v1.0.md` §5; `TechnicalArchitecture_v2.0.md` §6 |
| `financial` | transactions, budgets, invoices, api_costs, predictions | Restricted | Financial records are Restricted; credentials-adjacent is Critical. | `DataGovernance_ClassificationPolicy_v1.0.md` §5; `EncryptionKeyManagementStandard_v1.0.md` §9 |
| `projects` | projects, tasks, evidence, documents, clients | Internal (projects/tasks) / Restricted (clients) | `projects.clients` contact_info (encrypted), negotiation_tactics, guinevere_notes | `MemorySchema_v2.0.md` §7.3 |
| `system` | feature_flags, config, health_log, audit_trail | Internal (feature_flags/config) / Confidential (audit_trail) | Audit trail contains sensitive payload fragments. | `TechnicalArchitecture_v2.0.md` §5.1; `DataGovernance_ClassificationPolicy_v1.0.md` §5 |
| `social` | contacts, call_log, relationship_map | Restricted | Intimate/crisis/client-sensitive escalates to Critical. | `DataGovernance_ClassificationPolicy_v1.0.md` §5 |

### 3.2 PgBouncer Service Users (Current State vs Required)

| DB User | Current Permissions (Source) | Required Permissions (Matrix) | Gap |
|---|---|---|---|
| `guinevere_core` | SELECT, INSERT, UPDATE all schemas | Per-schema/per-action least privilege; no broad all-schema role in production. | Broad role is temporary bootstrap; matrix must split. |
| `guinevere_surveillance` | INSERT surveillance schema only | INSERT surveillance schema only; no cross-schema access. | Aligns with least privilege. |
| `guinevere_financial` | ALL financial schema | ALL financial schema is acceptable for financial domain; must not access other schemas. | Acceptable if scoped to financial only. |
| `guinevere_readonly` | SELECT only all schemas | SELECT only on specific schemas/tables needed for Grafana/reporting; exclude sensitive columns (e.g., `samm_profile.value`, `inner_journal.content`, `emotional_events.description`). | Too broad; matrix must restrict. |
| `guinevere_admin` | Superuser — rotate, backup | Break-glass-only role; max 4h duration; must not be used for normal runtime; post-use rotation required. | Superuser in runtime is violation; matrix must redefine as break-glass. |

### 3.3 Row-Level Security (RLS) Requirements

RLS must be enforced for:

| Table | RLS Policy | Basis |
|---|---|---|
| `memory.samm_profile` | Users may only access rows where `category` is not `intimate` unless explicitly authorized; intimate rows require break-glass or Samm direct access. | `DataGovernance_ClassificationPolicy_v1.0.md` §7.1, §7.5; `EncryptionKeyManagementStandard_v1.0.md` §9 |
| `persona.inner_journal` | Only `Samm` and `guinevere_core` with safe-mode off and purpose validation may SELECT; all other principals denied. | `PersonaSafetyPolicy_v1.0.md` §16; `EncryptionKeyManagementStandard_v1.0.md` §9 |
| `surveillance.screenshots` | Raw screenshots restricted to `surveillance-ingestor` INSERT and `guinevere_core` SELECT with purpose; `readonly-auditor` gets hashed references only. | `DataGovernance_ClassificationPolicy_v1.0.md` §5; `EncryptionKeyManagementStandard_v1.0.md` §9 |
| `surveillance.messages` | Raw message content restricted; extracted events may be more broadly read. | `DataGovernance_ClassificationPolicy_v1.0.md` §5, §9.2 |
| `system.audit_trail` | Append-only; no DELETE/UPDATE except by `guinevere_admin` break-glass; SELECT restricted to `observability-reader` and `readonly-auditor`. | `DataGovernance_ClassificationPolicy_v1.0.md` §10.1; `EncryptionKeyManagementStandard_v1.0.md` §17 |
| `behavior.violation_log` | Safe-word events must not be recorded as violations by default; INSERT restricted to `guinevere_core` with safe-mode validation. | `PersonaSafetyPolicy_v1.0.md` §10.2, §11 (F-11) |

---

## 4. Redis Enforcement Surfaces

### 4.1 Databases and Key Patterns

| DB | Purpose | Key Pattern | Default Class | TTL | Source |
|---|---|---|---|---|---|
| Redis DB0 | Task queue — SDLC jobs | `task:{id}` | Internal | No expiry | `TechnicalArchitecture_v2.0.md` §5.5; `DataGovernance_ClassificationPolicy_v1.0.md` §5 |
| Redis DB1 | LLM response cache | `llm:{hash}` | Internal | 1 hour | `TechnicalArchitecture_v2.0.md` §5.5; `DataGovernance_ClassificationPolicy_v1.0.md` §5 |
| Redis DB2 | Surveillance data buffer | `surv:{device}:{ts}` | Restricted | 5 minutes | `TechnicalArchitecture_v2.0.md` §5.5; `DataGovernance_ClassificationPolicy_v1.0.md` §5 |
| Redis DB3 | Session state | `session:{id}` | Confidential | 24 hours | `TechnicalArchitecture_v2.0.md` §5.5; `DataGovernance_ClassificationPolicy_v1.0.md` §5 |
| Redis DB4 | Pub/sub channels | `chan:{component}` | Internal | No expiry | `TechnicalArchitecture_v2.0.md` §5.5; `DataGovernance_ClassificationPolicy_v1.0.md` §5 |
| Redis DB5 | Rate limiting | `ratelimit:{ip}` | Internal | 1 minute | `TechnicalArchitecture_v2.0.md` §5.5; `DataGovernance_ClassificationPolicy_v1.0.md` §5 |

### 4.2 Redis ACL Requirements

Redis ACL users must be defined per principal:

| ACL User | Accessible DB(s) | Key Patterns Allowed | Commands Allowed | Source |
|---|---|---|---|---|
| `guinevere_core` | DB0, DB1, DB3 | `task:*`, `llm:*`, `session:*` | GET, SET, DEL, EXPIRE, TTL | Derived from architecture |
| `surveillance-ingestor` | DB2 | `surv:*` | SET, EXPIRE | Derived from architecture |
| `guinevere_surveillance` | DB2 | `surv:*` | GET, SET, DEL, EXPIRE | Derived from architecture |
| `observability-reader` | DB0, DB1, DB2, DB3, DB4, DB5 | `*` (read-only) | GET, TTL, INFO | Derived from architecture |
| `backup-operator` | DB0, DB1, DB2, DB3 | `*` (for backup) | GET, SET, DEL, EXPIRE, BGSAVE | Derived from architecture |

Redis ACL must deny:
- Cross-DB access (e.g., `surveillance-ingestor` must not access DB0).
- `FLUSHALL`, `FLUSHDB`, `DEBUG`, `CONFIG` commands for non-admin users.
- `KEYS` or `SCAN` patterns that bypass key-prefix restrictions.

### 4.3 Redis Key-Prefix Classification Rules

Every Redis key must carry a data class prefix or be mapped in a sidecar registry:

| Key Pattern | Data Class | TTL Rule | Encryption |
|---|---|---|---|
| `task:*` | Internal | No expiry; explicit delete on completion. | No app-level encryption required. |
| `llm:*` | Internal (cache) / Confidential (if sensitive prompt cached) | 1 hour TTL; Critical raw prompts prohibited. | No app-level encryption; sensitive prompts must not be cached. |
| `surv:*` | Restricted (summary) / Critical (raw) | 5 minutes; no durable raw cache. | No durable raw Critical cache; summaries may be cached. |
| `session:*` | Confidential / Restricted (if safe-mode active) | 24 hours; explicit delete on logout/safe-mode end. | Session tokens encrypted in transit; sensitive session data encrypted at rest. |
| `chan:*` | Internal | No expiry; no durable payload retention. | No app-level encryption required. |
| `ratelimit:*` | Internal | 1 minute TTL. | No app-level encryption required. |

---

## 5. Object Storage Enforcement Surfaces

### 5.1 Buckets and Prefixes

| Bucket | Prefix | Purpose | Default Class | Source |
|---|---|---|---|---|
| `guinevere-raw` | `surveillance/screenshots/` | Raw surveillance screenshots | Restricted / Critical | `TechnicalArchitecture_v2.0.md` §6, §9; `DataGovernance_ClassificationPolicy_v1.0.md` §5 |
| `guinevere-raw` | `surveillance/camera/` | Raw camera captures | Restricted / Critical | `TechnicalArchitecture_v2.0.md` §6; `DataGovernance_ClassificationPolicy_v1.0.md` §5 |
| `guinevere-raw` | `surveillance/clipboard/` | Raw clipboard captures | Restricted / Critical | `DataGovernance_ClassificationPolicy_v1.0.md` §5 |
| `guinevere-backups` | `postgres/` | PostgreSQL WAL/pg_dump | Restricted | `TechnicalArchitecture_v2.0.md` §9.1; `EncryptionKeyManagementStandard_v1.0.md` §13.2 |
| `guinevere-backups` | `redis/` | Redis RDB/AOF | Confidential | `TechnicalArchitecture_v2.0.md` §9.1; `EncryptionKeyManagementStandard_v1.0.md` §13.2 |
| `guinevere-backups` | `config/` | Config/secrets backups | Critical | `EncryptionKeyManagementStandard_v1.0.md` §13.2; `DataGovernance_ClassificationPolicy_v1.0.md` §5 |
| `guinevere-exports` | `dossiers/` | Samm dossiers and exports | Highest source class | `DataGovernance_ClassificationPolicy_v1.0.md` §5, §7.6; `EncryptionKeyManagementStandard_v1.0.md` §13.3 |
| `guinevere-archives` | `cold/` | Cold archival data (>90 days) | Varies by source | `TechnicalArchitecture_v2.0.md` §5.2 (TimescaleDB cold storage) |

### 5.2 Object Storage IAM Prefix Policies

Object storage (R2/idcloudhost) must enforce:

| Principal | Allowed Buckets | Allowed Prefixes | Actions | Source |
|---|---|---|---|---|
| `surveillance-ingestor` | `guinevere-raw` | `surveillance/screenshots/`, `surveillance/camera/`, `surveillance/clipboard/` | PutObject, GetObject (own prefix only) | Derived from architecture |
| `backup-operator` | `guinevere-backups` | `postgres/`, `redis/`, `config/` | PutObject, GetObject, DeleteObject | Derived from architecture |
| `guinevere_core` | `guinevere-raw`, `guinevere-exports`, `guinevere-archives` | All prefixes | PutObject, GetObject, DeleteObject | Derived from architecture |
| `observability-reader` | None (read via app APIs) | N/A | No direct object storage access. | Derived from architecture |
| `readonly-auditor` | `guinevere-backups` | `postgres/` (hashed manifests only) | GetObject (read-only) | Derived from DataGovernancePolicy |

Object storage must enforce:
- No public access by default.
- Encryption before upload for Restricted/Critical objects.
- Scoped credentials per bucket/prefix.
- Lifecycle rules aligned to Data Governance retention.
- Object metadata including classification, retention class, encryption profile, key_id, key_version.

---

## 6. FastAPI Endpoint Enforcement Surfaces

### 6.1 Surveillance Endpoints

| Endpoint | Method | Required Principal | Required Data Class | Auth Method | Source |
|---|---|---|---|---|---|
| `/surveillance/android/activity` | POST | `surveillance-ingestor` | Restricted (activity summary) / Critical (raw) | Tailscale IP whitelist + JWT + API key | `TechnicalArchitecture_v2.0.md` §6.2 |
| `/surveillance/android/location` | POST | `surveillance-ingestor` | Restricted (location summary) / Critical (raw trace) | Tailscale IP whitelist + JWT + API key | `TechnicalArchitecture_v2.0.md` §6.2 |
| `/surveillance/android/notification` | POST | `surveillance-ingestor` | Restricted (notification content) / Critical (raw) | Tailscale IP whitelist + JWT + API key | `TechnicalArchitecture_v2.0.md` §6.2 |
| `/surveillance/android/call` | POST | `surveillance-ingestor` | Restricted (call metadata) / Critical (raw) | Tailscale IP whitelist + JWT + API key | `TechnicalArchitecture_v2.0.md` §6.2 |
| `/surveillance/android/clipboard` | POST | `surveillance-ingestor` | Restricted (clipboard content) / Critical (credentials) | Tailscale IP whitelist + JWT + API key | `TechnicalArchitecture_v2.0.md` §6.2 |
| `/surveillance/android/camera` | POST | `surveillance-ingestor` | Restricted (camera capture) / Critical (intimate) | Tailscale IP whitelist + JWT + API key | `TechnicalArchitecture_v2.0.md` §6.2 |
| `/surveillance/windows/ws` | WebSocket | `surveillance-ingestor` | Restricted (activity stream) | Tailscale IP whitelist + JWT + API key | `TechnicalArchitecture_v2.0.md` §6.2 |
| `/surveillance/health/wearable` | POST | `surveillance-ingestor` | Restricted (health data) / Critical (medical) | Tailscale IP whitelist + JWT + API key | `TechnicalArchitecture_v2.0.md` §6.2 (post-MVP) |

### 6.2 Internal API Endpoints

| Endpoint | Method | Required Principal | Required Data Class | Auth Method | Source |
|---|---|---|---|---|---|
| `/api/v1/memory/*` | Various | `guinevere_core` | Varies by endpoint | JWT + Tailscale IP whitelist | Derived from architecture |
| `/api/v1/persona/*` | Various | `guinevere_core` | Varies by endpoint | JWT + Tailscale IP whitelist | Derived from architecture |
| `/api/v1/financial/*` | Various | `guinevere_core` + `financial-ingestor` for ingest | Restricted / Critical | JWT + Tailscale IP whitelist | Derived from architecture |
| `/api/v1/surveillance/query` | GET | `guinevere_core` | Restricted / Critical | JWT + Tailscale IP whitelist + purpose validation | Derived from DataGovernancePolicy |
| `/api/v1/export/*` | Various | `guinevere_core` + Samm approval for Critical | Highest source class | JWT + Tailscale IP whitelist + approval token | `DataGovernance_ClassificationPolicy_v1.0.md` §7.6 |
| `/api/v1/admin/*` | Various | `guinevere_admin` (break-glass) | Varies | Break-glass token + Samm approval + time-box | `EncryptionKeyManagementStandard_v1.0.md` §16.3 |
| `/health` | GET | Any (internal) | N/A | None (Tailscale-only) | `TechnicalArchitecture_v2.0.md` §8.4 |

### 6.3 FastAPI Auth Requirements

Every FastAPI endpoint must enforce:
- Tailscale IP whitelist: only Tailscale-internal IPs may connect.
- JWT validation: token must be valid and not expired.
- API key validation: for service-to-service calls.
- Principal mapping: JWT/subject must map to a known principal.
- Data class validation: requested data class must be within principal's allowed scope.
- Safe-mode check: if safe word/distress is active, sensitive endpoints must return minimal/supportive responses.

---

## 7. Filesystem Path Enforcement Surfaces

### 7.1 SOPS Encrypted Secret Files

| Path | Owner | Permissions | Classification | Source |
|---|---|---|---|---|
| `/home/guinevere/config/.env.sops.yaml` | `guinevere` | 0600, owner-only | Critical | `EncryptionKeyManagementStandard_v1.0.md` §10.2 |
| `/home/guinevere/config/secrets.production.sops.yaml` | `guinevere` | 0600, owner-only | Critical | `EncryptionKeyManagementStandard_v1.0.md` §10.2 |
| `/home/guinevere/config/secrets.staging.sops.yaml` | `guinevere` | 0600, owner-only | Critical | `EncryptionKeyManagementStandard_v1.0.md` §10.2 |

Plaintext variants must not exist in repo, evidence, logs, or sub-agent reports.

### 7.2 Age Identity Key

| Path | Owner | Permissions | Classification | Source |
|---|---|---|---|---|
| `/home/guinevere/.age/key.txt` | `guinevere` or Samm-controlled admin | 0600, owner-only; parent directory no group/world write | Critical | `EncryptionKeyManagementStandard_v1.0.md` §10.3 |

### 7.3 Runtime Decrypted Environment

| Path | Owner | Permissions | Classification | Source |
|---|---|---|---|---|
| `/tmp/.env` (or equivalent tmpfs) | `guinevere` | 0600; auto-cleaned after service load | Critical | `EncryptionKeyManagementStandard_v1.0.md` §10.4 |

Decrypted environment files must not be backed up, read by sub-agents, or exposed to logs.

### 7.4 Application Data Paths

| Path | Owner | Permissions | Classification | Source |
|---|---|---|---|---|
| `/home/guinevere/core/` | `guinevere` | 0700, owner-only | Varies by file | `TechnicalArchitecture_v2.0.md` §3.2 |
| `/home/guinevere/data/logs/` | `guinevere` | 0750, group `guinevere` | Confidential / Restricted / Critical | `TechnicalArchitecture_v2.0.md` §3.2; `DataGovernance_ClassificationPolicy_v1.0.md` §5 |
| `/home/guinevere/data/cache/` | `guinevere` | 0700, owner-only | Internal / Confidential | `TechnicalArchitecture_v2.0.md` §3.2 |
| `/home/guinevere/scripts/` | `guinevere` | 0750, owner-only | Internal | `TechnicalArchitecture_v2.0.md` §3.2 |

### 7.5 Evidence and Audit Paths

| Path | Owner | Permissions | Classification | Source |
|---|---|---|---|---|
| `/home/guinevere/evidence/` | `guinevere` | 0750, owner-only | Varies by evidence type | `TechnicalArchitecture_v2.0.md` §3.2; AGENTS.md |
| `/home/guinevere/audit-reports/` | `guinevere` | 0750, owner-only | Confidential / Restricted | AGENTS.md |
| `/home/guinevere/research-reports/` | `guinevere` | 0750, owner-only | Internal / Confidential | AGENTS.md |

Evidence directories must be append-only where possible; no deletion without audit trail.

---

## 8. systemd Service Enforcement Surfaces

### 8.1 Service Units and Isolation

| Service Unit | Process | Memory Limit | CPU Limit | User | Isolation Requirements | Source |
|---|---|---|---|---|---|---|
| `guinevere-core.service` | Hermes Agent daemon + persona engine | 4GB | 2 cores | `guinevere` | No network access beyond Tailscale; no filesystem access outside `/home/guinevere/core/` and approved paths. | `TechnicalArchitecture_v2.0.md` §3.1 |
| `guinevere-surveillance.service` | FastAPI surveillance receiver | 512MB | Shared | `guinevere` | Tailscale-only bind; no outbound internet except approved integrations; input validation required. | `TechnicalArchitecture_v2.0.md` §3.1 |
| `guinevere-scheduler.service` | APScheduler + daily rituals + cron jobs | 256MB | Shared | `guinevere` | No direct network access; all tasks must go through approved APIs. | `TechnicalArchitecture_v2.0.md` §3.1 |
| `guinevere-windows-sync.service` | WebSocket server for Windows daemon | 256MB | Shared | `guinevere` | Tailscale-only bind; WebSocket auth required. | `TechnicalArchitecture_v2.0.md` §3.1 |
| `guinevere-loops.service` | Autonomous SDLC loop runner + loop guardian | 512MB | Shared | `guinevere` | No direct network access; file-based output only; parent verification required for sub-agent outputs. | `TechnicalArchitecture_v2.0.md` §3.1; ADR-012 |
| `docker.service` | PostgreSQL + Redis + Prometheus containers | System | System | `root` (container runtime) | Containers must bind to Tailscale-only interfaces; no port exposure. | `TechnicalArchitecture_v2.0.md` §3.1 |
| `caddy.service` | Reverse proxy + auto-HTTPS | 128MB | Shared | `guinevere` | Tailscale-only bind; no public ingress. | `TechnicalArchitecture_v2.0.md` §3.1 |
| `tailscaled.service` | Tailscale VPN daemon | 128MB | Shared | `root` | Network access required; auth key expiry monitoring required. | `TechnicalArchitecture_v2.0.md` §3.1; ADR-019 |

### 8.2 Service User Requirements

| Service | Linux User | sudo Access | Justification |
|---|---|---|---|
| `guinevere-core` | `guinevere` | systemctl restart guinevere-*, docker, ufw, apt | Required for service management. |
| `guinevere-surveillance` | `guinevere` | None (inherits from core) | No direct sudo needed. |
| `guinevere-scheduler` | `guinevere` | None (inherits from core) | No direct sudo needed. |
| `guinevere-windows-sync` | `guinevere` | None (inherits from core) | No direct sudo needed. |
| `guinevere-loops` | `guinevere` | None (inherits from core) | No direct sudo needed. |
| `samm` | `samm` | Full sudo | Human admin access. |
| `postgres` | `postgres` | None | PostgreSQL service. |
| `redis` | `redis` | None | Redis service (Docker). |

---

## 9. Tailscale ACL / Tags Enforcement Surfaces

### 9.1 Device Tags

| Tag | Devices | Auto-Approvers | Allowed Services | Source |
|---|---|---|---|---|
| `tag:admin` | Samm workstations, mobile, break-glass devices | Samm devices | All Tailscale-internal services. | ADR-019 §Review Record |
| `tag:service` | VPS, monitoring VPS | N/A | Internal service mesh only. | ADR-019 §Review Record |
| `tag:service:guinevere` | Primary VPS | N/A | All service ports. | Derived from architecture |
| `tag:service:monitoring` | Monitoring VPS (post-MVP) | N/A | Prometheus, Grafana, Loki only. | Derived from architecture |

### 9.2 ACL Policy Requirements

Tailscale ACL policy file must define:

- Device tags: `tag:admin`, `tag:service`, `tag:service:guinevere`, `tag:service:monitoring`.
- Auto-approvers: Samm devices auto-approve new devices in `tag:admin`.
- Subnet routing rules: security groups must allow inbound from Tailscale subnet router IPs.
- Non-overlapping subnets across all tailnet members.
- No public port exposure via Tailscale funnel or HTTPS routes.

### 9.3 Tailscale SSH Requirements

- Regular SSH disabled from internet.
- Tailscale SSH only for admin access.
- Auth key expiry: 180 days default; VPS requires appropriate expiry settings or disabled expiry.
- Renewal procedure documented; offline backup of recovery auth key.

---

## 10. Logs, Evidence, Backups, Exports Enforcement Surfaces

### 10.1 Log Destinations and Classification

| Log Type | Destination | Classification | Retention | Source |
|---|---|---|---|---|
| Application logs | Loki via Promtail | Confidential | Medium Operational (30-180 days) | `TechnicalArchitecture_v2.0.md` §8.3; `DataGovernance_ClassificationPolicy_v1.0.md` §5 |
| Audit logs | Loki + PostgreSQL audit table | Confidential (summary) / Restricted (sensitive payloads) | Regulated/Audit (1 year+) | `TechnicalArchitecture_v2.0.md` §8.3; `DataGovernance_ClassificationPolicy_v1.0.md` §10.1 |
| Surveillance logs | TimescaleDB surveillance schema | Restricted (summary) / Critical (raw) | Tiered per source | `TechnicalArchitecture_v2.0.md` §8.3; `DataGovernance_ClassificationPolicy_v1.0.md` §6 |
| System logs | systemd journal → Loki via Promtail | Internal | Medium Operational | `TechnicalArchitecture_v2.0.md` §8.3 |
| Guinevere action log | PostgreSQL + Loki | Confidential (summary) / Restricted (action touches Restricted/Critical) | Regulated/Audit | `TechnicalArchitecture_v2.0.md` §8.3; `DataGovernance_ClassificationPolicy_v1.0.md` §5 |
| Safety logs | PostgreSQL + Loki | Critical | Long-Term Curated | `PersonaSafetyPolicy_v1.0.md` §16; `DataGovernance_ClassificationPolicy_v1.0.md` §5 |

### 10.2 Backup Enforcement

| Backup Type | Destination | Encryption | Classification | Retention | Source |
|---|---|---|---|---|---|
| PostgreSQL hot (WAL streaming) | Cloudflare R2 | Encrypted before upload (backup KEK) | Restricted | Selamanya (with tiered retention for raw) | `TechnicalArchitecture_v2.0.md` §9.1; `EncryptionKeyManagementStandard_v1.0.md` §13.2 |
| PostgreSQL cold (pg_dump) | idcloudhost S3 | Encrypted before upload (backup KEK) | Restricted | Selamanya | `TechnicalArchitecture_v2.0.md` §9.1; `EncryptionKeyManagementStandard_v1.0.md` §13.2 |
| Redis (RDB + AOF) | Local + R2 | Encrypted before upload | Confidential | Selamanya | `TechnicalArchitecture_v2.0.md` §9.1; `EncryptionKeyManagementStandard_v1.0.md` §13.2 |
| Guinevere config | GitHub private repo | SOPS encrypted | Critical | Selamanya | `TechnicalArchitecture_v2.0.md` §9.1 |
| Secrets (.env.sops) | GitHub private repo | SOPS encrypted | Critical | Selamanya | `TechnicalArchitecture_v2.0.md` §9.1 |
| Surveillance screenshots | R2 + idcloudhost | Encrypted before upload | Restricted / Critical | Selamanya | `TechnicalArchitecture_v2.0.md` §9.1; `DataGovernance_ClassificationPolicy_v1.0.md` §5 |
| Tasker config | GDrive + repo + VPS | Encrypted | Critical | Selamanya | `TechnicalArchitecture_v2.0.md` §9.1 |
| VPS full snapshot | hostdata.id snapshot | Host-level encryption | Internal | 4 snapshots rotating | `TechnicalArchitecture_v2.0.md` §9.1 |

### 10.3 Export and Dossier Enforcement

Exports and dossiers must be:
- Classified at highest source class.
- Encrypted with time-limited export package key.
- Logged with creation, access, and deletion events.
- Time-limited with explicit expiry.
- Redactable and revocable where technically feasible.
- No sub-agent access unless task-justified and minimized.

---

## 11. SOPS / age / Key Files Enforcement Surfaces

### 11.1 SOPS File Access

| File | Allowed Principals | Actions | Source |
|---|---|---|---|
| `/home/guinevere/config/.env.sops.yaml` | `secret-rotator` (read/decrypt), `guinevere_core` (runtime decrypt only), `break-glass-operator` (emergency only) | Read, decrypt, rotate | `EncryptionKeyManagementStandard_v1.0.md` §10.1-10.4 |
| `/home/guinevere/.age/key.txt` | `guinevere` runtime user, `secret-rotator` (rotation only), `break-glass-operator` (emergency only) | Read for decrypt; rotation requires evidence | `EncryptionKeyManagementStandard_v1.0.md` §10.3 |

### 11.2 Key Hierarchy Access

| Key Layer | Custodian | Runtime Access | Allowed Principals | Source |
|---|---|---|---|---|
| Samm Recovery Root | Samm | No normal runtime access | Samm only | `EncryptionKeyManagementStandard_v1.0.md` §5.1, §16.1 |
| Offline recovery package | Samm | No normal runtime access | Samm only | `EncryptionKeyManagementStandard_v1.0.md` §16.2 |
| SOPS age identity | Runtime host | Required for startup secret decrypt | `guinevere` runtime user | `EncryptionKeyManagementStandard_v1.0.md` §5.1, §10.3 |
| Domain KEKs | Guinevere crypto service | Runtime-only, scoped by domain | `guinevere_core` (via crypto service) | `EncryptionKeyManagementStandard_v1.0.md` §5.1, §16.1 |
| DEKs/content keys | Guinevere crypto service | Runtime-only during encrypt/decrypt | `guinevere_core` (via crypto service) | `EncryptionKeyManagementStandard_v1.0.md` §5.1, §16.1 |
| Provider secrets | Owning service | Scoped environment injection | Owning service principal only | `EncryptionKeyManagementStandard_v1.0.md` §5.1, §16.1 |

---

## 12. Tools / MCP / Sub-Agent Context Enforcement Surfaces

### 12.1 MCP Tool Context Boundaries

| MCP Tool / Context | Allowed Principals | Context Minimization Requirement | Source |
|---|---|---|---|
| `guinevere_core` full context | `guinevere_core` | Full context allowed; safe-mode restrictions apply. | Derived from architecture |
| Sub-agent research context | `sub-agent-researcher` | Redacted/minimized; no Critical raw data; no secrets. | `DataGovernance_ClassificationPolicy_v1.0.md` §7.3; ADR-012 |
| Sub-agent implementation context | `sub-agent-implementer` | Code-only context; no production secrets; no Critical memory data. | `DataGovernance_ClassificationPolicy_v1.0.md` §7.3; ADR-012 |
| Surveillance ingestion context | `surveillance-ingestor` | Payload-specific only; no cross-schema data; no memory access. | Derived from architecture |
| Financial ingestion context | `financial-ingestor` | Financial schema only; no cross-schema data. | Derived from architecture |
| Backup operator context | `backup-operator` | Backup paths and keys only; no app data access. | Derived from architecture |
| Observability reader context | `observability-reader` | Metrics and logs only; no sensitive payloads. | Derived from architecture |
| Secret rotator context | `secret-rotator` | Secret inventory and SOPS paths only; no app data. | Derived from EncryptionKeyManagementStandard |
| Break-glass operator context | `break-glass-operator` | Time-boxed; all surfaces; requires Samm approval where feasible. | `EncryptionKeyManagementStandard_v1.0.md` §16.3 |
| Migration principal context | `migration-principal` | Schema modification only; no data access outside migration scope. | Derived from architecture |
| External integration context | `external-integration` | Scoped API credentials only; no internal data access. | Derived from architecture |
| Readonly auditor context | `readonly-auditor` | Logs and evidence only; no write access; no app data. | `DataGovernance_ClassificationPolicy_v1.0.md` §7.3 |

### 12.2 Sub-Agent Context Gating Requirements

Sub-agent prompts and context must be gated:

- Critical data must be redacted, summarized, or omitted unless required for the task.
- Prompt logs must not persist full sensitive prompt/response payloads by default.
- Sub-agent prompts must not include raw Critical data unless justified and audited.
- Memory injection must use summaries and confidence labels where raw content is not needed.
- Sub-agent outputs must be written to markdown files; parent must verify before accepting.

---

## 13. Safe-Mode Enforcement per Surface

### 13.1 Safe-Mode Blocked Actions by Surface

| Surface | Blocked Actions During Safe Mode | Source |
|---|---|---|
| PostgreSQL | No SELECT on `inner_journal`, `emotional_events.description`, `samm_profile` (intimate category), `surveillance` raw tables unless needed for immediate safety. | `PersonaSafetyPolicy_v1.0.md` §7.2, §15.1; `DataGovernance_ClassificationPolicy_v1.0.md` §7.5 |
| Redis | No GET on `surv:*` raw keys; no GET on `session:*` if session contains sensitive state. | Derived from DataGovernancePolicy safe-mode rules |
| FastAPI | Surveillance query endpoints return empty/summary only; export endpoints blocked for Critical data; admin endpoints blocked. | `PersonaSafetyPolicy_v1.0.md` §7.2; `DataGovernance_ClassificationPolicy_v1.0.md` §7.5 |
| Object storage | No GetObject on `guinevere-raw/surveillance/` raw prefixes; no export creation for Critical data. | Derived from DataGovernancePolicy safe-mode rules |
| Filesystem | No read of `/home/guinevere/data/logs/` safety logs by non-Samm principals; no access to `.env.sops` or `.age/key.txt` except runtime decrypt. | `EncryptionKeyManagementStandard_v1.0.md` §10.4; `PersonaSafetyPolicy_v1.0.md` §16 |
| systemd | No restart of services that would bypass safe-mode state; no modification of safety-critical configs. | Derived from PersonaSafetyPolicy runtime hooks |
| Sub-agent | No sub-agent spawn for persona-intensive or surveillance-confrontation tasks; sub-agent context minimized. | `PersonaSafetyPolicy_v1.0.md` §7.2; ADR-012 |
| MCP/tools | No irreversible actions (git push, file deletion, financial transactions) without non-persona confirmation. | `PersonaSafetyPolicy_v1.0.md` §15.1 (tool-risk gate) |

---

## 14. Checklist: What the Final RBAC/ABAC Matrix Must Contain

- [ ] All 13 principals defined with exact trust level, scope, and Linux/user mapping.
- [ ] PostgreSQL PgBouncer user mapping: exact schemas, tables, actions (SELECT/INSERT/UPDATE/DELETE) per principal.
- [ ] PostgreSQL RLS policies for sensitive tables: `samm_profile`, `inner_journal`, `emotional_events`, `surveillance.*`, `behavior.violation_log`, `system.audit_trail`.
- [ ] Redis ACL users and key-prefix rules per principal and data class.
- [ ] Object storage bucket/prefix IAM policies per principal and data class.
- [ ] FastAPI endpoint authorization mapping: endpoint, method, required principal, required data class, safe-mode behavior, auth method.
- [ ] Filesystem path permissions: SOPS files, age key, config, logs, evidence, backups.
- [ ] systemd service isolation: resource limits, user mapping, network restrictions.
- [ ] Tailscale ACL/tag policy: device tags, auto-approvers, subnet rules, SSH restrictions.
- [ ] Safe-mode restrictions per surface: explicit blocked actions per data class during safe word/distress.
- [ ] Break-glass constraints: SEV0/SEV1 only; max 4h; Samm approval where feasible; post-use rotation.
- [ ] Sub-agent access matrix: trust level, data class access, redaction rules, audit requirements, context gating.
- [ ] Audit log requirements: mandatory audit events per data class, action, and principal.
- [ ] Secret access matrix: which principals may access which secrets; rotation schedule; audit.
- [ ] Backup and export access: who may create, read, delete backups and exports; encryption requirements.
- [ ] Incident response hooks: which actions trigger SEV0-SEV4; required containment actions per surface.
- [ ] All controls use `must` (zero `should`).
- [ ] Language: Indonesian + technical English.
- [ ] Normative child of ADR-019, ADR-018, ADR-024, ADR-012 plus DataGovernancePolicy, EncryptionKeyMgmtStandard, PersonaSafetyPolicy.
