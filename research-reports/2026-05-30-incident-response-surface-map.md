# Incident Response Surface Map

**Document Type:** Surface mapping evidence report for incident-response runbook authoring  
**Version:** 1.0  
**Status:** Accepted  
**Last Updated:** 2026-05-30  
**Owner:** Samm — sole human owner and final approver  
**Executor:** Guinevere de Baroque  
**Classification:** STRICTLY PRIVATE & CONFIDENTIAL  

## Related Documents

| Document | Relationship |
|---|---|
| `Guinevere_TechnicalArchitecture_v2.0.md` | Defines concrete runtime surfaces: systemd services, FastAPI endpoints, PostgreSQL/PgBouncer, Redis, object storage, Tailscale, logs, monitoring. |
| `Guinevere_AccessControl_RBAC_ABAC_Matrix_v1.0.md` | Maps principals, roles, ABAC rules, safe-mode restrictions, and break-glass operators to runtime surfaces. |
| `Guinevere_EncryptionKeyManagementStandard_v1.0.md` | Maps key hierarchy, SOPS/age files, encrypted fields, and backup/export key scopes to runtime surfaces. |
| `Guinevere_SecretsRotationRunbook_v1.0.md` | Maps secret inventory, rotation procedures, evidence paths, and emergency triggers to runtime surfaces. |
| `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` | Maps data classes, retention classes, and incident categories to storage and log surfaces. |
| `Guinevere_PersonaSafetyPolicy_v1.0.md` | Maps persona safety runtime hooks, safe-word states, forbidden patterns, and drift validation to service surfaces. |
| `adr/ADR-018-security-architecture-defense-in-depth.md` | Normative parent for network isolation, service hardening, audit logs, and incident hooks. |
| `adr/ADR-025-backup-disaster-recovery-strategy.md` | Normative parent for backup/DR surfaces, RPO/RTO, restore validation, and recovery procedures. |

---

## 1. Runtime Surfaces

This section maps concrete runtime surfaces that must be considered during incident detection, containment, recovery, and postmortem.

---

## 2. systemd Services

| Service | Process | Memory Limit | Incident Role | Containment Action | Recovery Action |
|---|---|---|---|---|---|
| `guinevere-core.service` | Hermes Agent daemon + persona engine | 4GB | Primary runtime; persona, memory, orchestration, sub-agent dispatch | Break-glass restart; safe-mode pause persona escalation | Health check evidence; restart with audit |
| `guinevere-surveillance.service` | FastAPI surveillance receiver | 512MB | Ingests Android/Windows surveillance events | Pause ingestion; preserve Redis DB2 buffer | Resume ingestion; validate replay protection |
| `guinevere-scheduler.service` | APScheduler + daily rituals + cron jobs | 256MB | Scheduled secret rotation, rituals, self-deploy | Pause non-essential scheduled tasks | Resume scheduled rotation per runbook |
| `guinevere-windows-sync.service` | WebSocket server for Windows daemon | 256MB | Windows surveillance stream | Disconnect WebSocket; preserve evidence | Reconnect with device identity validation |
| `guinevere-loops.service` | Autonomous SDLC loop runner + loop guardian | 512MB | Autonomous loop execution | Pause loop; safe-mode can pause persona/surveillance tasks | Resume loop; validate guardian state |
| `docker.service` | PostgreSQL + Redis + Prometheus containers | System | Database, cache, monitoring | High blast radius; break-glass only | Restart containers; validate health checks |
| `caddy.service` | Reverse proxy + auto-HTTPS | 128MB | Internal reverse proxy | No public app ingress; restart if needed | Validate internal routing |
| `tailscaled.service` | Tailscale VPN daemon | 128MB | VPN mesh; zero public ports | Lockout risk; recovery path required | Validate Tailscale connectivity; recovery procedure |

**Incident considerations:**

- `guinevere-core.service` restart requires health check evidence (AccessControl Matrix §13).
- `guinevere-surveillance.service` safe-mode blocks confrontation but not necessary ingestion (AccessControl Matrix §7, §13).
- `guinevere-loops.service` safe-mode can pause persona/surveillance tasks (TechnicalArchitecture §3.1).
- `docker.service` has high blast radius; restart requires break-glass (AccessControl Matrix §13).
- `tailscaled.service` lockout risk requires documented recovery path (ADR-019, AccessControl Matrix §14).

---

## 3. FastAPI Endpoints

| Endpoint | Method | Source | Classification | Incident Detection | Containment | Recovery Validation |
|---|---|---|---|---|---|---|
| `/surveillance/android/activity` | POST | Tasker | Restricted | Anomalous activity volume or pattern | Rate-limit or pause endpoint | Resume; validate replay protection |
| `/surveillance/android/location` | POST | Tasker | Restricted -> Critical | Location anomaly or privacy incident | Pause ingestion; preserve evidence | Resume; validate timestamp/device HMAC |
| `/surveillance/android/notification` | POST | Tasker | Restricted -> Critical | Message content leak or secret detection | Pause ingestion; run secret scanner | Resume; validate classification metadata |
| `/surveillance/android/call` | POST | Tasker | Restricted | Call metadata anomaly | Pause ingestion | Resume; validate deduplication |
| `/surveillance/android/clipboard` | POST | Tasker | Critical if credential-like | Secret scanner detection (CRITICAL incident trigger) | Immediate pause; isolate payload; incident declared | Resume only after secret scanner clear; re-encrypt if needed |
| `/surveillance/android/camera` | POST | Tasker | Critical by default | Image evidence anomaly or privacy incident | Pause ingestion; preserve encrypted object | Resume; validate encryption/object metadata |
| `/surveillance/windows/ws` | WebSocket | Windows daemon | Restricted -> Critical | Stream anomaly or disconnection during incident | Disconnect WebSocket; preserve evidence | Reconnect with device identity validation |
| `/surveillance/health/wearable` | POST | Mi Fitness API | Restricted | Disabled post-MVP; not active incident surface | N/A | N/A |
| `guinevere.internal:8001/internal/*` | Various | Core runtime | Varies | Internal orchestration anomaly | Safe-mode ABAC gate mandatory | Validate internal API health |
| `/admin/*` | Various | Samm/break-glass | Critical | Unauthorized access attempt | Deny; alert; audit event | Samm or break-glass-operator re-auth |

**Incident considerations:**

- All endpoints require authenticated principal, source device identity, replay protection, timestamp, and classification metadata (AccessControl Matrix §11).
- Clipboard endpoint has mandatory secret scanner; credential detection is a SEV0/SEV1 trigger (TechnicalArchitecture §6.2, AccessControl Matrix §11).
- Surveillance endpoints must maintain replay protection and timestamp validation (AccessControl Matrix §11).
- Admin endpoints are limited to Samm and break-glass-operator (AccessControl Matrix §11).

---

## 4. PostgreSQL / PgBouncer

| Component | Role | Classification | Incident Detection | Containment | Recovery |
|---|---|---|---|---|---|
| PostgreSQL 16 | Primary data store | Restricted -> Critical by table | Unauthorized access, corruption, RLS bypass | Isolate DB user; revoke compromised credential; break-glass if needed | pg_restore from backup; reconciliation |
| PgBouncer | Connection pooling | Internal | Connection anomaly, auth failure | Reload PgBouncer; rotate DB password | Validate per-service connections |
| `memory` schema | Episodic/semantic memory | Restricted -> Critical | Unauthorized query, data exfiltration | RLS enforcement; audit query | Restore if corrupted; reconcile deletion ledger |
| `persona` schema | Drift log, mood, Samm profile | Restricted -> Critical | Drift anomaly, safe-word log tampering | RLS enforcement; safe-mode restrictions | Restore from backup; validate drift snapshot |
| `behavior` schema | Violation/reward/goals | Restricted -> Critical | Violation log tampering, punishment anomaly | RLS enforcement; audit access | Restore if needed; validate rollback |
| `surveillance` schema | Activity, location, messages, screenshots | Restricted -> Critical | Raw surveillance export, unauthorized access | Pause ingestion; RLS enforcement | Restore with retention reconciliation |
| `financial` schema | Transactions, budgets, invoices | Restricted | Financial data anomaly | RLS enforcement; audit access | Restore from backup; validate 7-year retention |
| `projects` schema | Projects, tasks, evidence, documents | Restricted -> Critical | Client data leak, evidence tampering | RLS enforcement; audit access | Restore if corrupted; validate evidence chain |
| `system` schema | Feature flags, config, health, audit | Confidential -> Critical | Audit trail tampering, config change | RLS enforcement; audit event | Restore if needed; validate integrity |
| `system.audit_trail` | Structured audit events | Confidential -> Critical | Audit log gap, tampering | RLS enforcement; read-only for auditor | Restore from backup; validate completeness |

**Incident considerations:**

- PgBouncer per-service users must be least-privilege (TechnicalArchitecture §5.4, AccessControl Matrix §8).
- RLS policies enforce data-class ceilings (AccessControl Matrix §8.3).
- Break-glass operator (`db_break_glass_admin`) has all-schema access but is limited to SEV0/SEV1 and max 4 hours (AccessControl Matrix §8.1, §18).
- DB corruption recovery must use pg_restore from latest backup with deletion/do-not-recall reconciliation (ADR-025 §9.2, DataGovernance §6.4).
- Backup compromise treated as incident according to exposed classification (EncryptionKeyMgmt §13.2).

---

## 5. Redis DBs

| DB | Purpose | Key Pattern | Classification | Incident Detection | Containment | Recovery |
|---|---|---|---|---|---|---|
| DB0 | Task queue — SDLC jobs | `task:{id}` | Internal -> Restricted if sensitive | Task queue anomaly, unauthorized scan | Drain or pause queue; audit keys | Resume queue; validate task state |
| DB1 | LLM response cache | `llm:{hash}` | Internal -> highest prompt class | Prompt injection, cache poisoning | Flush cache; audit keys | Resume caching; validate prompt classification |
| DB2 | Surveillance data buffer | `surv:{device}:{ts}` | Restricted -> Critical | Surveillance data leak, unauthorized access | Preserve for evidence; short TTL (5 min) means rapid decay | Resume ingestion; validate encryption |
| DB3 | Session state | `session:{id}` | Confidential -> Critical if safe-mode/intimate | Session hijack, safe-mode bypass | Invalidate sessions; audit access | Resume sessions; validate safe-mode state |
| DB4 | Pub/sub channels | `chan:{component}` | Internal -> Restricted | Unauthorized pub/sub, message injection | Pause channels; audit subscribers | Resume channels; validate ACL |
| DB5 | Rate limiting | `ratelimit:{ip}` | Internal | Rate limit bypass, attack pattern | Reset limits; audit source IPs | Resume rate limiting; validate thresholds |

**Incident considerations:**

- Redis ACLs must use per-principal users and key-prefix restrictions (AccessControl Matrix §9).
- Critical data must not be durably stored in Redis (AccessControl Matrix §9, TechnicalArchitecture §5.5).
- Redis backups must inherit the highest source classification (AccessControl Matrix §9).
- DB2 surveillance buffer has 5-minute TTL; rapid decay means evidence preservation must be immediate (TechnicalArchitecture §5.5).
- Session state (DB3) can be invalidated during key compromise (AccessControl Matrix §9).

---

## 6. Object Storage / Backups

| Bucket / Prefix | Classification | Incident Detection | Containment | Recovery |
|---|---|---|---|---|
| `r2://guinevere-backups/postgres/` | Restricted -> Critical | Backup integrity failure, unauthorized access | Revoke backup key; isolate bucket | Restore from verified backup; validate deletion ledger |
| `r2://guinevere-backups/redis/` | Confidential -> Critical | Backup corruption, unauthorized access | Revoke backup key; isolate bucket | Restore RDB/AOF; validate TTL reconciliation |
| `r2://guinevere-surveillance/raw/` | Restricted -> Critical | Surveillance leak, unauthorized access | Revoke surveillance key; isolate bucket | Restore if needed; validate retention rules |
| `r2://guinevere-evidence/` | Highest source class | Evidence tampering, unauthorized access | Revoke evidence key; audit access | Validate evidence chain; restore if corrupted |
| `s3://idcloudhost-guinevere-backups/` | Restricted -> Critical | Backup integrity failure, unauthorized access | Revoke S3 key; isolate bucket | Restore from verified backup; validate deletion ledger |
| `exports/` | Highest source class | Export leak, unauthorized access | Freeze exports; revoke export key | Validate export encryption; re-encrypt if needed |

**Incident considerations:**

- Object storage buckets must be private with no public ACL (AccessControl Matrix §10, EncryptionKeyMgmt §13.1).
- Encryption before upload is mandatory (EncryptionKeyMgmt §13.1, ADR-025 §9.1).
- Scoped credentials per bucket/prefix (AccessControl Matrix §10, TechnicalArchitecture §2.1).
- Lifecycle rules aligned to DataGovernance retention (DataGovernance §6).
- Backup compromise treated as incident according to exposed classification (EncryptionKeyMgmt §13.2).
- Restore reconciliation must reapply deletion/do-not-recall ledger before data becomes visible (DataGovernance §6.4, EncryptionKeyMgmt §13.2).

---

## 7. SOPS / age / Key Files

| File / Material | Classification | Incident Detection | Containment | Recovery |
|---|---|---|---|---|
| `/home/guinevere/.age/key.txt` | Critical | Key file tampering, unauthorized access | Isolate host; rotate age key; preserve evidence | Deploy new age key; re-encrypt SOPS; validate startup |
| `/home/guinevere/config/.env.sops.yaml` | Critical | SOPS decryption failure, secret exposure | Freeze affected services; rotate exposed secrets | Re-encrypt with new recipient; validate decrypt |
| `/tmp/.env` | Critical runtime | Runtime env leak, unauthorized read | Clean tmpfs; rotate affected secrets | Re-decrypt SOPS; validate service startup |
| Domain KEKs (runtime) | Critical | Key compromise, unauthorized decrypt | Isolate affected domain; rotate KEK; rewrap DEKs | Deploy new KEK; validate sample decrypts |
| Samm Recovery Root | Critical | Recovery package exposure | Samm containment; rotate recovery material | Generate new recovery package; validate checksum |
| Break-glass credentials | Critical | Break-glass misuse, credential exposure | Revoke break-glass credential; audit access | Generate new break-glass credential; update recovery package |

**Incident considerations:**

- Age private key must have permissions `0600` and owner-only (EncryptionKeyMgmt §10.3, AccessControl Matrix §12).
- SOPS plaintext must never be committed or exposed (SecretsRotationRunbook §2.2).
- Runtime decrypted env must be on tmpfs and auto-cleaned (EncryptionKeyMgmt §10.4, TechnicalArchitecture §7.1).
- Break-glass credentials rotate after every use (SecretsRotationRunbook §5, secret `sec-break-glass-cred`).
- Key compromise triggers SEV0-SEV1 based on scope (EncryptionKeyMgmt §18.1).

---

## 8. Tailscale

| Component | Tag / Device | Classification | Incident Detection | Containment | Recovery |
|---|---|---|---|---|---|
| VPS Primary | `tag:service-core` | Internal | Unauthorized access, Tailscale config break | Deny-all unspecified; isolate service | Validate ACL; restore connectivity |
| Android HP | `tag:service-ingestor` | Internal | Device compromise, HMAC secret exposure | Revoke device HMAC; disconnect device | Reissue device secret; validate ingestion |
| Windows Laptop | `tag:service-ingestor` | Internal | Device compromise, HMAC secret exposure | Revoke device HMAC; disconnect daemon | Reissue device secret; validate sync |
| Monitoring VPS | `tag:monitoring` | Internal | Unauthorized metrics access | Deny raw payload access; audit | Validate metrics-only access |
| Backup job | `tag:backup` | Internal | Unauthorized backup access | Revoke backup key; isolate | Validate backup key scope |
| Break-glass device | `tag:break-glass` | Critical | Break-glass misuse | Auto-expire grant; audit | Revoke credential; rotate |
| Samm devices | `tag:owner` | Internal | Device loss, unauthorized access | Revoke device/session; audit | Samm re-auth |

**Incident considerations:**

- Zero public VPS ingress is mandatory (AccessControl Matrix §14, TechnicalArchitecture §7.1).
- ACL policy must deny all unspecified paths (AccessControl Matrix §14).
- Lockout risk exists if Tailscale config breaks; recovery path required (AccessControl Matrix §13, ADR-019).
- Break-glass tag has emergency device/session access but is limited to SEV0/SEV1 and max 4 hours (AccessControl Matrix §14).

---

## 9. Logs / Audit / Evidence

| Log / Store | Format | Destination | Classification | Incident Detection | Containment | Recovery |
|---|---|---|---|---|---|---|
| Application logs | JSON structured | Loki via Promtail | Confidential -> Critical | Log anomaly, injection attempt | Pause affected service; audit log | Validate log integrity; resume |
| Audit logs | JSON structured | Loki + PostgreSQL `system.audit_trail` | Confidential -> Critical | Audit trail gap, tampering | RLS enforcement; read-only for auditor | Restore audit log; validate completeness |
| Surveillance logs | JSON structured | TimescaleDB | Restricted -> Critical | Surveillance data leak, unauthorized access | Pause ingestion; RLS enforcement | Restore with retention reconciliation |
| System logs | systemd journal | Loki via Promtail | Internal -> Confidential | Service failure, security event | Restart service; audit journal | Validate journal integrity |
| Guinevere action log | JSON structured | PostgreSQL + Loki | Confidential -> Critical | Action anomaly, unauthorized tool use | Audit action; pause affected task | Validate action chain; resume |
| Evidence files | Markdown | `evidence/incidents/` | Highest source class | Evidence tampering, unauthorized access | Audit evidence; isolate | Validate evidence chain; restore if needed |
| Audit reports | Markdown | `audit-reports/` | Confidential -> Restricted | Report tampering, unauthorized access | Audit report; isolate | Validate report integrity |

**Incident considerations:**

- Audit logs must not store plaintext secrets, raw intimate content, or raw surveillance evidence when hash/summary is sufficient (AccessControl Matrix §17, EncryptionKeyMgmt §17.1).
- Every Restricted/Critical allow/deny decision requires an audit event (AccessControl Matrix §17).
- Surveillance logs must be encrypted (AccessControl Matrix §8.2).
- Evidence files must use path pattern `evidence/incidents/<YYYY-MM-DD>-<SEV>-<slug>/` with `postmortem.md` for SEV0-SEV2 (DataGovernance §11.5).

---

## 10. Autonomous Loop

| Component | Role | Classification | Incident Detection | Containment | Recovery |
|---|---|---|---|---|---|
| `guinevere-loops.service` | Autonomous SDLC loop runner + loop guardian | Internal | Loop runaway, infinite task generation | Pause loop; safe-mode can pause persona/surveillance tasks | Validate guardian state; resume loop |
| Loop guardian | Detects and halts runaway loops | Internal | Loop health check failure | Halt loop; alert Samm | Resume loop; validate phase state |
| Self-deploy cron | Autonomous CD via git pull | Internal | Deploy failure, rollback needed | Revert to previous commit; alert Discord | Validate health checks; resume deploy |
| Phase 1-7 runners | Research, Plan, Delegate, Execute, Validate, Update, Evidence | Varies | Phase failure, sub-agent abuse | Pause phase; audit sub-agent output | Resume phase; validate parent verification |

**Incident considerations:**

- Autonomous SDLC uses exactly 7 phases (ADR-018 inherited decision).
- Safe-mode can pause persona/surveillance tasks (TechnicalArchitecture §3.1, PersonaSafetyPolicy §7.2).
- Self-deploy cron has rollback path: git revert + alert Discord + rollback (TechnicalArchitecture §10.2).
- Sub-agent outputs must be file-based; parent must verify before relying on output (AccessControl Matrix §15).

---

## 11. Sub-Agent System

| Component | Role | Trust Level | Incident Detection | Containment | Recovery |
|---|---|---|---|---|---|
| Sub-agent spawner | Spawns research/code/audit agents | Medium | Sub-agent abuse, unauthorized access | Revoke sub-agent credential; isolate task | Re-spawn with task-scoped access; verify output |
| Research sub-agent | Read docs, produce reports | Medium read-only | Critical data request, prompt injection | Deny request; audit event; log task ID | Re-spawn with redacted context |
| Implementation sub-agent | Write docs/code/evidence | Medium write-capable | Unauthorized write, secret exposure | Revoke write access; audit file output | Re-spawn with task-scoped write access |
| Audit sub-agent | Review and verify | Medium read-only | Audit bypass, tampering | Deny; escalate to Samm | Re-run audit with fresh context |
| Parent verification | Verifies sub-agent output | High | Unverified sub-agent output | Block output acceptance; require re-run | Verify file artifact; accept if valid |

**Incident considerations:**

- Sub-agent access must be task-scoped, redacted, and parent-verified (AccessControl Matrix §15, DataGovernance §7.3).
- Sub-agent Critical access is denied by default (AccessControl Matrix §15, ABAC-003).
- Sub-agent outputs must be file-based for structured reports; inline output is not accepted (AccessControl Matrix §15, AGENTS.md §2).
- Sub-agent Restricted data requests require task justification and redaction (AccessControl Matrix §15, ABAC-004).

---

## 12. Persona Safety Runtime

| Hook | Location | Purpose | Incident Detection | Containment | Recovery |
|---|---|---|---|---|---|
| Safe-word detector | Before persona rendering and tool execution | Hard-stop unsafe escalation | Safe-word bypass attempt | Immediate safe mode; block output; log event | Resume persona only on Samm explicit confirmation |
| Distress classifier | Before punishment/yandere response | Conservative de-escalation | Distress misclassification | Neutral supportive mode; pause pressure | Validate classifier; update thresholds |
| Forbidden-pattern scanner | After draft generation, before send | Block/rewrite unsafe output | Forbidden pattern detection | Rewrite or block; log near-miss | Update scanner rules; validate rewrite |
| Surveillance-use gate | Before using raw surveillance facts | Prevent blackmail/shame | Surveillance coercion attempt | Block output; audit event | Validate gate; update rules |
| Tool-risk gate | Before filesystem/shell/git/API actions | Prevent irreversible action under persona pressure | High-risk action during persona state | Require non-persona confirmation | Validate gate; update risk class |
| Drift validator | End of interaction + daily deep check | Detect unsafe drift | Drift beyond safety rubric | Rollback or safe-mode pending review | Validate drift score; update snapshot |
| Audit logger | After safety event | Minimal, encrypted, non-punitive records | Safety event anomaly | Audit event; preserve evidence | Validate audit log integrity |

**Incident considerations:**

- Safe word is a global hard stop; Guinevere must not deny it in real time (PersonaSafetyPolicy §7.2).
- During safe-word state, punishment/reward logs must not record safe-word/distress events as violations (PersonaSafetyPolicy §7.3, §10.2).
- Yandere intensity must downgrade to Y0/Y1 during safe word, distress, illness, or sensitive surveillance signals (PersonaSafetyPolicy §9.1).
- Persona drift rollback target is last known-good approved persona snapshot (PersonaSafetyPolicy §14.3).

---

## 13. Surveillance Ingestion

| Source | Endpoint | Data Type | Classification | Incident Detection | Containment | Recovery |
|---|---|---|---|---|---|---|
| Android Tasker | `/surveillance/android/activity` | App activity | Restricted | Volume anomaly, unauthorized app | Pause endpoint; audit source | Resume; validate replay protection |
| Android Tasker | `/surveillance/android/location` | GPS location | Restricted -> Critical | Location anomaly, privacy incident | Pause endpoint; preserve evidence | Resume; validate timestamp/HMAC |
| Android Tasker | `/surveillance/android/notification` | Notification content | Restricted -> Critical | Message content leak, secret detection | Pause endpoint; run secret scanner | Resume; validate classification |
| Android Tasker | `/surveillance/android/call` | Call metadata | Restricted | Call anomaly | Pause endpoint | Resume; validate deduplication |
| Android Tasker | `/surveillance/android/clipboard` | Clipboard content | Critical if credential-like | Secret scanner detection (SEV0/SEV1 trigger) | Immediate pause; isolate payload; incident declared | Resume only after scanner clear |
| Android Tasker | `/surveillance/android/camera` | Image capture | Critical by default | Image evidence anomaly | Pause endpoint; preserve encrypted object | Resume; validate encryption |
| Windows daemon | `/surveillance/windows/ws` | WebSocket stream | Restricted -> Critical | Stream anomaly, disconnection | Disconnect WebSocket; preserve evidence | Reconnect with device identity |
| Wearable (post-MVP) | `/surveillance/health/wearable` | Health data | Restricted | Disabled; not active surface | N/A | N/A |

**Incident considerations:**

- Surveillance ingestor can INSERT to Redis DB2 and `surveillance` schema only (AccessControl Matrix §8.1, §9).
- Surveillance ingestor cannot SELECT outside ingestion validation (AccessControl Matrix §8.1).
- Surveillance ingestor cannot make persona decisions or write punishment records (AccessControl Matrix §8.1, PersonaSafetyPolicy §12).
- Raw surveillance data must not be used for blackmail, shame, or coercion (PersonaSafetyPolicy §12.2).
- Secret scanner is mandatory over clipboard content (TechnicalArchitecture §6.2, AccessControl Matrix §11).
- Surveillance data retention follows tiered rules: 7-30 days raw, 90-180 days summaries (DataGovernance §6.2).

---

## 14. Cost / Provider Keys

| Provider / Key | Classification | Incident Detection | Containment | Recovery |
|---|---|---|---|---|
| 9Router (LLM router) | Critical | Cost spike, provider outage, queue/retry failure | Queue/retry through 9Router recovery policy; no OpenRouter fallback | Validate 9Router health; resume LLM routing |
| GPT-5.5 (primary LLM) | Critical | Cost anomaly, unexpected usage | Pause non-essential LLM calls; audit usage | Resume LLM calls; validate token usage |
| DeepSeek V4 Flash (sub-agent LLM) | Critical | Cost anomaly, unexpected usage | Pause sub-agent spawning; audit usage | Resume sub-agent; validate token usage |
| Discord token | Critical | Gateway anomaly, unexpected message volume | Reset bot token; update SOPS; restart Discord worker | Validate gateway connection; bot identity |
| GitHub PAT | Critical | Repository exposure, suspicious operation | Revoke PAT; rotate webhook secret; update SOPS | Validate MCP/git operations; update CI |
| Gmail OAuth | Critical | Token exposure, suspicious login | Revoke OAuth grant; re-auth; update SOPS | Validate send/read; update refresh token |
| Resend API key | Critical | Exposure, unexpected email volume | Revoke API key; update SOPS | Validate transactional send |
| Gotify token | Critical | Exposure, unexpected push volume | Revoke token; update SOPS | Validate push notification |
| PostgreSQL passwords | Critical | Unauthorized access, leaked env | Rotate password; update SOPS; reload PgBouncer | Validate connection; role-specific query |
| Redis auth | Critical | Unauthorized access, leaked env | Rotate password; update config; restart Redis | Validate AUTH; queue operation |
| R2/idcloudhost keys | Critical | Bucket anomaly, backup leak, provider alert | Revoke keys; update SOPS; isolate bucket | Validate upload/download; restore sample |
| Device HMACs | Critical | Device loss, payload spoofing, replay anomaly | Revoke HMAC; disconnect device; update SOPS | Reissue device secret; validate signature |
| Sentry DSN | Confidential | Error tracking anomaly | Regenerate DSN; update SOPS | Validate event send |
| Prometheus/Grafana auth | Confidential | Metrics anomaly, unauthorized access | Rotate auth; update SOPS | Validate scrape; dashboard query |

**Incident considerations:**

- 9Router is the single LLM routing layer; no OpenRouter fallback (ADR-018 inherited decision, TechnicalArchitecture §4.1).
- Cost anomaly detection should track `guinevere_api_cost_total` metric (TechnicalArchitecture §8.2).
- Provider rotation follows SecretsRotationRunbook §10 per-secret procedures.
- Emergency rotation priority: contain, preserve evidence, revoke, generate replacement, update SOPS, redeploy, validate, rotate adjacent, write evidence, schedule postmortem (SecretsRotationRunbook §11.2).
- Secret scanner must run after every rotation and incident involving potential secret exposure (SecretsRotationRunbook §13.2).

---

## 15. Incident Type Response Matrix

For each incident type, the following detection signals, containment actions, evidence sources, recovery validations, and postmortem triggers are derived from foundation docs.

| Incident Type | Detection Signals | Containment Action | Evidence Source | Recovery Validation | Postmortem Trigger |
|---|---|---|---|---|---|
| IR-01: Security/key breach | Key compromise alert, nonce reuse, public secret exposure, unauthorized decrypt, provider compromise notification | Isolate affected service; revoke/disable key/secret; freeze exports and non-essential decrypts; preserve minimal evidence with hashes; notify Samm | EncryptionKeyMgmt §18.2; AccessControl Matrix §17; system.audit_trail; key usage logs; Loki | Sample decrypt; record count verification; ciphertext hash validation; service health check; audit log review | SEV0-SEV1 mandatory; SEV2 if scope unclear |
| IR-02: Data leak | Unauthorized access alert, classification scan failure, export anomaly, sub-agent data exposure, backup restore exposing deleted data | Isolate affected service/export/sub-agent flow; revoke/rotate keys if secrets involved; freeze exports; preserve evidence; notify Samm | DataGovernance §11.4; AccessControl Matrix §17; Loki; PostgreSQL audit_trail; evidence files | Data integrity check; classification label audit; deletion/do-not-recall ledger reconciliation; export log review | SEV0-SEV2 mandatory |
| IR-03: Persona safety violation | Forbidden-pattern detection, safe-word bypass attempt, drift validator flag, red-team finding, Samm complaint | Immediate safe mode; block/rewrite unsafe output; log near-miss; pause affected persona task; notify Samm if severe | PersonaSafetyPolicy §11; §15.1; safety logs; drift log; audit event | Forbidden-pattern scanner test; drift snapshot validation; rollback to last known-good snapshot | SEV1-SEV2 mandatory |
| IR-04: Safe-word failure | Safe-word semantic classifier miss, distress classifier false negative, safe-word event logged as violation | Immediate safe mode; log minimal non-punitive safety event; block persona escalation; notify Samm | PersonaSafetyPolicy §7; §11; safety logs; audit event | Safe-word detector test; distress classifier validation; log schema validation (no punitive tag) | SEV1 mandatory |
| IR-05: Service outage | Health check failure, systemd restart loop, connection failure, endpoint unreachable, monitoring alert | Restart service (break-glass if high blast radius); isolate affected component; preserve logs; notify Samm if extended | TechnicalArchitecture §8.4; ADR-025 §9.2; Loki; systemd journal; health check logs | Service health check; connection test; endpoint probe; log integrity check | SEV1-SEV3 based on blast radius |
| IR-06: Autonomous loop failure | Loop guardian halt, infinite task generation, phase failure, sub-agent timeout, unexpected task volume | Pause loop; halt runaway generation; audit sub-agent outputs; notify Samm | TechnicalArchitecture §3.1; guinevere-loops.service logs; task queue (Redis DB0); sub-agent reports | Loop guardian state validation; phase state check; task queue drain; parent verification of sub-agent outputs | SEV2-SEV3 mandatory |
| IR-07: Sub-agent abuse | Unauthorized data request, Critical data attempt, prompt injection, secret exposure in output, file-based report missing | Revoke sub-agent credential; isolate task; deny request; audit event; require parent re-verification; notify Samm if sensitive | AccessControl Matrix §15; §17; parent verification logs; sub-agent report files; evidence directory | Parent verification of file artifact; redaction validation; secret scanner on sub-agent output; audit log replay | SEV1-SEV2 mandatory |
| IR-08: Database corruption | Integrity check failure, RLS bypass, unexpected query result, pg_dump/WAL corruption, schema mismatch | Isolate DB user; revoke compromised credential; preserve evidence; break-glass if needed; notify Samm | ADR-025 §9.2; AccessControl Matrix §8; PostgreSQL logs; WAL archives; backup integrity | pg_restore from latest backup; deletion/do-not-recall ledger reconciliation; RLS policy test; data integrity check | SEV1-SEV2 mandatory |
| IR-09: Backup failure | Backup job failure, restore test failure, backup integrity check failure, encryption key mismatch, retention job failure | Isolate backup system; revoke backup key if compromised; preserve remaining backups; notify Samm | ADR-025 §9; SecretsRotationRunbook §14.2; backup logs; object storage access logs; evidence files | Restore test from verified backup; deletion ledger reconciliation; backup encryption validation; key metadata check | SEV1-SEV3 based on data impact |
| IR-10: Cost spike anomaly | `guinevere_api_cost_total` metric spike, unexpected LLM call volume, provider billing alert, queue depth anomaly | Pause non-essential LLM calls; pause sub-agent spawning; audit usage; notify Samm; validate provider billing | TechnicalArchitecture §8.2; metrics logs; provider dashboard; audit event | Token usage reconciliation; provider billing validation; cost attribution audit; queue depth normalization | SEV3-SEV4; postmortem if unexplained |

---

## 16. Monitoring and Detection Surfaces

| Surface | Tool / Mechanism | Incident Relevance | Alert Threshold |
|---|---|---|---|
| PostgreSQL connection | Health check (30s) | DB outage, auth failure | Continuous failure > 1 min |
| Redis connection | Health check (30s) | Cache outage, auth failure | Continuous failure > 1 min |
| Discord gateway | Health check (30s) | Interface outage | Continuous failure > 1 min |
| 9Router/LLM | Health check (60s) | LLM provider outage | Continuous failure > 2 min |
| Surveillance receiver | Health check (30s) | Ingestion outage | Continuous failure > 1 min |
| Hermes Agent | Health check (30s) | Core runtime failure | Continuous failure > 1 min |
| UptimeRobot external | External check (5m) | VPS/Tailscale outage | Failure > 10 min |
| `guinevere_task_completion_total` | Prometheus counter | Autonomous loop anomaly | Spike or stall |
| `guinevere_mood_state` | Prometheus gauge | Persona state anomaly | Unexpected value change |
| `guinevere_mommy_score` | Prometheus gauge | Productivity anomaly | Sudden drop/spike |
| `guinevere_api_cost_total` | Prometheus counter | Cost spike anomaly | Threshold defined in FinOps Model |
| `guinevere_sub_agents_active` | Prometheus gauge | Sub-agent abuse | Unexpected value change |
| `guinevere_surveillance_events_total` | Prometheus counter | Surveillance anomaly | Volume spike |
| Loki logs | Log aggregation | Log anomaly, injection attempt | Pattern match or volume spike |
| `system.audit_trail` | PostgreSQL table | Audit trail gap, tampering | Missing events or unexpected access |
| Secret scanner | Post-rotation / post-incident | Secret leakage | Any positive finding |

---

## 17. Recovery Validation Checklist

After containment and recovery actions, the following validations must be performed before closing an incident:

| Check | Validation Method | Source |
|---|---|---|
| Service health | systemd status, health check endpoint | TechnicalArchitecture §8.4 |
| Database integrity | Connection test, query validation, RLS policy test | AccessControl Matrix §8 |
| Redis integrity | AUTH success, ping/pong, queue operation | AccessControl Matrix §9 |
| Encryption integrity | Sample decrypt, ciphertext hash, key metadata check | EncryptionKeyMgmt §12-13 |
| Audit log completeness | Audit log replay, event count validation | AccessControl Matrix §17 |
| Evidence chain | File existence, hash validation, cross-reference integrity | DataGovernance §10.1 |
| Secret scanner | Scan logs, evidence, docs, sub-agent reports | SecretsRotationRunbook §13.2 |
| Backup restore test | pg_restore, deletion ledger reconciliation | ADR-025 §9.2, DataGovernance §6.4 |
| Sub-agent output verification | File existence, non-empty, evidence citations, parent verification | AccessControl Matrix §15 |
| Persona safety state | Safe-mode active/inactive, drift snapshot validation | PersonaSafetyPolicy §14-15 |
| Tailscale connectivity | Device tag validation, ACL test | AccessControl Matrix §14 |
| Cost attribution | Token usage reconciliation, provider billing validation | TechnicalArchitecture §8.2 |

---

## 18. Postmortem Trigger Summary

| Severity | Incident Types | Postmortem Required | Due |
|---|---|---|---|
| SEV0 | All types | Mandatory | Immediate |
| SEV1 | All types | Mandatory | Within incident closure |
| SEV2 | All types | Mandatory | Within incident closure |
| SEV3 | Data leak, service outage, backup failure, cost spike | Recommended | Within 7 days |
| SEV4 | All types | Near-miss record | Next cycle |

Postmortem must be written to:

```
evidence/incidents/<YYYY-MM-DD>-<SEV>-<slug>/postmortem.md
```

Postmortem must include (DataGovernance §11.5):

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

## 19. Unresolved Assumptions

| ID | Assumption | Impact | Follow-up |
|---|---|---|---|
| UA-01 | Safe Word Runtime Spec is not yet created. | Exact safe-word tokens and distress thresholds are unresolved. | Create Safe Word Runtime Spec. |
| UA-02 | Policy-as-code engine is not chosen. | ABAC evaluation can drift across code paths. | Define Authorization Middleware Spec. |
| UA-03 | Tailscale ACL file is not yet generated. | Network enforcement remains conceptual until ACL config exists. | Generate Tailscale ACL implementation artifact. |
| UA-04 | Cost anomaly thresholds are not formally defined. | SEV3/SEV4 cost spike response lacks concrete triggers. | FinOps Model / Observability Spec. |
| UA-05 | Exact FastAPI endpoint list can expand during implementation. | Endpoint matrix needs update on API changes. | API Contract OpenAPI Spec. |
| UA-06 | Object storage bucket names may differ at deployment. | Prefix IAM must be validated against actual buckets. | Deployment Runbook / Storage Inventory. |
| UA-07 | Fernet compatibility scope is not fully inventoried. | Legacy encrypted fields may be missed during rotation. | Database ERD & Migration Strategy. |
| UA-08 | Redis rotation downtime is a known limitation. | Cache disruption during auth rotation is accepted but not mitigated. | Runtime Hardening Spec. |

---

**End of Incident Response Surface Map v1.0**
