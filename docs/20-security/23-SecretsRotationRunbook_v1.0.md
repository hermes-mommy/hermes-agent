# Guinevere Secrets Rotation Runbook

**Document Type:** Operational runbook with implementation controls and audit appendices  
**Version:** 1.0  
**Status:** Accepted  
**Lifecycle:** Proposed → Accepted → Deprecated → Superseded  
**Last Updated:** 2026-05-30  
**Owner:** Faiz — single user, root custodian, emergency approver  
**Executor:** Guinevere de Baroque — autonomous AI agent / DevSecOps executor  
**Classification:** STRICTLY PRIVATE & CONFIDENTIAL  
**Authority:** Normative child under ADR-015, ADR-008, ADR-019, and `Guinevere_EncryptionKeyManagementStandard_v1.0.md`

---

## Related Documents

| Document | Relationship | Dependency Type | Implementation Impact |
|---|---|---|---|
| `Guinevere_EncryptionKeyManagementStandard_v1.0.md` | Defines key hierarchy, encryption profiles, SOPS+age controls, break-glass, audit, and validation requirements. | Normative parent | This runbook operationalizes rotation, verification, evidence, and emergency procedures. |
| `adr/ADR-015-secrets-management-strategy.md` | Accepts SOPS+age with runtime injection and forbids plaintext secrets in docs, code, logs, evidence, and sub-agent reports. | Normative parent | Rotation steps must update encrypted SOPS files only and never expose plaintext secrets. |
| `adr/ADR-008-memory-encryption-key-management.md` | Requires key hierarchy, rotation policy, emergency revoke path, separated key domains, and recovery controls. | Normative parent | Domain KEK, Fernet ring, backup key, and break-glass procedures must follow key-separation and recovery rules. |
| `adr/ADR-019-access-control-vpn-mesh-strategy.md` | Defines Tailscale mesh, zero public ports, device access boundaries, and lockout recovery constraints. | Normative parent | Rotation access must occur through Tailscale or provider dashboards, never by opening public VPS ingress. |
| `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` | Defines Critical/Restricted classifications, incident categories, audit retention, and Faiz rights. | Governance boundary | All secrets are classified at least Confidential; operational secrets and keys are Critical unless explicitly lower. |
| `Guinevere_TechnicalArchitecture_v2.0.md` | Defines VPS topology, SOPS file paths, services, PgBouncer, Redis, object storage, backups, and systemd units. | Runtime dependency | Procedures must match service names, secret paths, and zero-public-port deployment model. |
| `Guinevere_APIIntegration_v2.0.md` | Defines external providers, API tokens, HMAC signatures, OAuth tokens, Fernet compatibility, and object storage clients. | Integration dependency | Per-secret procedures must cover all provider credentials and validation probes. |
| `research-reports/2026-05-30-secrets-rotation-source-map.md` | Extracts source requirements from foundation docs. | Evidence | Supplies authority chain, SOPS workflow, rotation cadence, break-glass, evidence, and conflict map. |
| `research-reports/2026-05-30-secrets-rotation-surface-map.md` | Maps secret surfaces, owners, consumers, storage, validation evidence, revoke path, rollback, and blast radius. | Evidence | Supplies the inventory baseline for Section 5 and Appendix A. |
| `research-reports/2026-05-30-secrets-rotation-external-references.md` | Provides provider and security reference patterns for rotation. | Evidence | Supplies practical rotation patterns for SOPS+age, GitHub, Discord, OAuth, PostgreSQL, Redis, object storage, and Fernet. |

---

## 1. Purpose

This runbook defines the mandatory procedures for scheduled, autonomous, emergency, and recovery-driven rotation of every Project Guinevere secret. It translates accepted security decisions into executable operations with preflight checks, zero-downtime controls where possible, validation probes, revocation steps, rollback paths, and markdown evidence artifacts.

Guinevere is a single-user private system, but the data is highly intimate and operationally sensitive. Therefore every secret rotation must meet enterprise-grade controls even when Faiz is the only human user.

---

## 2. Authority and Conflict Resolution

### 2.1 Authority Order

Runtime rotation decisions must follow this authority order:

1. Platform security constraints and provider revocation rules.
2. Accepted ADRs: ADR-015, ADR-008, ADR-019.
3. `Guinevere_EncryptionKeyManagementStandard_v1.0.md`.
4. `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md`.
5. `Guinevere_PersonaSafetyPolicy_v1.0.md` when safe-word, distress, sensitive recall, or non-punitive safety logs are involved.
6. This runbook.
7. Lower-level implementation notes, provider dashboards, source comments, or memory.

If lower guidance conflicts with this authority chain, Guinevere must stop, document the conflict, and escalate to Faiz or ADR backlog instead of improvising.

### 2.2 Plaintext Prohibition

Secrets must not appear in markdown files, task prompts, sub-agent outputs, screenshots, logs, audit artifacts, shell history, browser transcripts, or issue/PR comments. Evidence must use secret IDs, key IDs, fingerprints, hashes, provider key labels, timestamps, and validation outcomes only.

### 2.3 Approval Boundary

Guinevere may perform scheduled/provider-supported rotation autonomously when preflight, rollback, evidence, and validation requirements pass. Guinevere must obtain Faiz approval where feasible for emergency/high-blast-radius rotation, including age private key rotation, Faiz Recovery Root rotation, Domain KEK compromise, GitHub PAT compromise affecting deployment, and provider account takeover.

If waiting for approval increases confirmed compromise impact, Guinevere may contain first, then document the reason and request post-action review.

---

## 3. Scope and Assumptions

### 3.1 In Scope

This runbook covers:

- SOPS encrypted secret files and age recipient/private key handling.
- Runtime decrypted environment files such as `/tmp/.env`.
- Provider API keys and tokens.
- OAuth refresh tokens and sessions.
- PostgreSQL per-service passwords and Redis auth.
- Object storage credentials for Cloudflare R2 and idcloudhost S3.
- Fernet compatibility rings, Domain KEKs, wrapped DEKs, backup keys, export keys, and recovery roots.
- Device HMAC secrets for Tasker/Android and Windows daemon payload signing.
- Break-glass credentials, offline recovery package, and evidence requirements.

### 3.2 Out of Scope

This runbook does not define full RBAC/ABAC policy, provider-specific UI screenshots, full incident postmortem template, or executable automation code. Those must be produced as follow-up implementation artifacts.

---

## 4. Global Rotation Rules and Preflight

### 4.1 Universal Rules

Every rotation must satisfy these controls:

1. The secret must have a `secret_id` in inventory before rotation.
2. The secret must have classification, owner, provider, consumer service, storage location, rotation cadence, revoke path, rollback concern, blast radius, and evidence path.
3. Rotation must use least privilege credentials.
4. Rotation must happen through Tailscale or provider-managed outbound/browser/API access; the VPS must not expose public admin ingress.
5. Plaintext must remain runtime-only and must be cleaned immediately after use.
6. Old secrets must remain usable only during an explicitly bounded overlap window.
7. New secrets must be validated before old secrets are revoked unless active compromise requires immediate revocation.
8. Evidence must be written to `evidence/secrets-rotation/<date>-<secret-id>.md` or `evidence/secrets-rotation/<date>-incident-<sev>.md`.
9. Evidence must not include plaintext secret values.
10. Rotation must update the secret inventory and `rotation_due_at`.

### 4.2 Preflight Checklist

Before any non-emergency rotation, Guinevere must verify:

- Current service health is acceptable.
- Backup or rollback path exists.
- Provider dashboard/API access works.
- SOPS decryption works on authorized host.
- Tailscale access is available.
- Target service has a validation probe.
- No active safe-word/distress state restricts sensitive recall or autonomous pressure.
- No incident response freeze blocks the change.
- Evidence path is prepared.
- Faiz approval is captured when required.

---

## 5. Secret Inventory and Classification

Every secret below is mandatory inventory scope. Unknown fields must be marked `TBD` and resolved before production rotation automation.

| secret_id | Secret | Classification | Primary Consumer | Storage | Default Cadence | Approval |
|---|---|---|---|---|---|---|
| `sec-9router-primary` | 9Router primary API key | Critical | `guinevere-core` | SOPS | Quarterly / incident | Autonomous scheduled; Faiz for emergency if feasible |
| `sec-9router-fallback` | 9Router fallback key | Critical | `guinevere-core` | SOPS | Quarterly / incident | Autonomous scheduled |
| `sec-discord-bot` | Discord bot token | Critical | Discord interface | SOPS | Quarterly / gateway anomaly | Faiz for emergency reset if feasible |
| `sec-github-pat` | GitHub PAT | Critical | MCP / self-deploy | SOPS | Quarterly / provider expiry / repo exposure | Faiz for high-blast-radius |
| `sec-github-webhook` | GitHub webhook secret | Critical | webhook receiver | SOPS | Quarterly / repo exposure | Autonomous scheduled |
| `sec-gmail-oauth` | Gmail OAuth refresh/client token | Critical | email integration | SOPS | Quarterly / token exposure | Faiz present for re-auth |
| `sec-resend-api` | Resend API key | Critical | transactional email | SOPS | Quarterly / exposure | Autonomous if API/dashboard available |
| `sec-gotify-token` | Gotify token | Critical | push fallback | SOPS | Quarterly / exposure | Autonomous scheduled |
| `sec-postgres-core` | PostgreSQL core password | Critical | `guinevere-core` via PgBouncer | SOPS | Quarterly / DB compromise | Scheduled low-traffic |
| `sec-postgres-surveillance` | PostgreSQL surveillance password | Critical | `guinevere-surveillance` | SOPS | Quarterly / compromise | Scheduled low-traffic |
| `sec-postgres-financial` | PostgreSQL financial password | Critical | financial worker | SOPS | Quarterly / compromise | Scheduled low-traffic |
| `sec-postgres-readonly` | PostgreSQL read-only password | Critical | Grafana/reporting | SOPS | Quarterly / exposure | Scheduled |
| `sec-postgres-admin` | PostgreSQL admin password | Critical | maintenance/recovery | SOPS | Quarterly / compromise | Faiz approval |
| `sec-redis-auth` | Redis password | Critical | all services | SOPS | Quarterly / unauthorized access | Scheduled window |
| `sec-r2-backup` | Cloudflare R2 backup credentials | Critical | backup job | SOPS | Quarterly / anomaly | Autonomous scheduled |
| `sec-r2-surveillance` | Cloudflare R2 surveillance credentials | Critical | surveillance processor | SOPS | Quarterly / anomaly | Autonomous scheduled |
| `sec-idcloudhost-s3` | idcloudhost S3 credentials | Critical | backup/archive | SOPS | Quarterly / anomaly | Autonomous scheduled |
| `sec-fernet-compat` | Fernet compatibility key ring | Critical | legacy encrypted fields | SOPS + runtime | Quarterly / scope violation | Faiz for emergency |
| `sec-domain-kek-secrets` | Domain KEK for secrets | Critical | crypto service | runtime wrapped | Quarterly / incident | Faiz approval |
| `sec-domain-kek-profile` | Domain KEK for Faiz profile | Critical | crypto service | runtime wrapped | Quarterly / incident | Faiz approval |
| `sec-domain-kek-safe-word` | Domain KEK for safe-word/distress | Critical | crypto service | runtime wrapped | Quarterly / incident | Faiz approval |
| `sec-domain-kek-journal` | Domain KEK for inner journal | Critical | crypto service | runtime wrapped | Quarterly / incident | Faiz approval |
| `sec-domain-kek-surveillance` | Domain KEK for surveillance | Critical | crypto service | runtime wrapped | Quarterly / incident | Faiz approval |
| `sec-domain-kek-financial` | Domain KEK for financial | Critical | crypto service | runtime wrapped | Quarterly / incident | Faiz approval |
| `sec-domain-kek-backup` | Domain KEK for backups | Critical | backup job | runtime wrapped | Annual / exposure | Faiz approval |
| `sec-domain-kek-export` | Domain KEK for exports | Critical | export process | runtime wrapped | Per package / expiry | Autonomous per package |
| `sec-domain-kek-audit` | Domain KEK for audit/evidence | Critical | audit/evidence | runtime wrapped | Annual / incident | Faiz approval |
| `sec-age-private-key` | age private key | Critical | SOPS decrypt | `/home/guinevere/.age/key.txt` | Annual / device-host compromise | Faiz approval |
| `sec-faiz-recovery-root` | Faiz Recovery Root | Critical | offline recovery | offline package | custody/compromise | Faiz only |
| `sec-device-android-hmac` | Android Tasker HMAC secret | Critical | surveillance receiver | SOPS + device config | Annual / device loss | Faiz if device access required |
| `sec-device-windows-hmac` | Windows daemon HMAC secret | Critical | windows sync | SOPS + device config | Annual / device loss | Faiz if device access required |
| `sec-tasker-config-backup` | Tasker backup encryption key | Critical | Tasker backup | SOPS/device backup | Annual / device loss | Faiz if device access required |
| `sec-sentry-dsn` | Sentry DSN | Confidential | error tracking | SOPS | Quarterly / exposure | Autonomous scheduled |
| `sec-prometheus-auth` | Prometheus auth if enabled | Confidential | metrics | SOPS | Quarterly / exposure | Autonomous scheduled |
| `sec-grafana-auth` | Grafana admin auth | Confidential | Grafana | SOPS | Quarterly / exposure | Autonomous scheduled |
| `sec-brave-api` | Brave API key | Critical | search provider | SOPS | Quarterly / exposure | Autonomous scheduled |
| `sec-exa-api` | Exa API key | Critical | search provider | SOPS | Quarterly / exposure | Autonomous scheduled |
| `sec-baileys-session` | WhatsApp Baileys session | Critical | communication worker | encrypted session store + SOPS metadata | Quarterly / session anomaly | Faiz if QR/re-link needed |
| `sec-runtime-decrypted-env` | runtime decrypted env | Critical | systemd services | tmpfs `/tmp/.env` | every SOPS update | Autonomous cleanup |
| `sec-sops-encrypted-files` | SOPS encrypted files | Critical | startup decrypt | encrypted repo/config | every secret change | Autonomous with evidence |
| `sec-backup-encryption-key` | backup encryption key | Critical | backup job | runtime wrapped + recovery package | Annual / exposure | Faiz approval |
| `sec-break-glass-cred` | break-glass credentials | Critical | emergency access | offline recovery package | after every use | Faiz approval |

---

## 6. Rotation Cadence Matrix

| Secret Class | Routine Cadence | Immediate Trigger | Approval | Evidence Level |
|---|---|---|---|---|
| Provider API keys | Quarterly | provider alert, log exposure, abuse spike, dashboard anomaly | Autonomous scheduled; Faiz for emergency if high blast radius | full evidence artifact |
| GitHub PAT / deployment credentials | Quarterly or provider expiry | repo exposure, CI/CD auth anomaly, suspicious operation | Faiz for emergency | full evidence + post-review |
| PostgreSQL per-service passwords | Quarterly | service compromise, leaked env, suspicious DB access | scheduled low-traffic; Faiz for admin | DB evidence + PgBouncer evidence |
| Redis auth | Quarterly | unauthorized access, leaked env, suspicious Redis command | scheduled window | Redis validation evidence |
| Object storage keys | Quarterly | bucket anomaly, backup leak, provider alert | autonomous scheduled; Faiz for destructive emergency | upload/download evidence |
| OAuth/session secrets | Quarterly where feasible | token exposure, suspicious login, provider alert | Faiz when re-auth needed | re-auth evidence |
| Device HMAC secrets | Annual | device loss, payload spoofing, Tasker/daemon compromise | Faiz when device access required | signature validation evidence |
| Fernet compatibility rings | Quarterly | domain scope violation, key exposure, legacy decrypt anomaly | Faiz for incident rotation | decrypt + re-encryption evidence |
| Domain KEKs | Quarterly for Critical domains | key compromise, unsafe decrypt, storage exposure | Faiz approval | rewrap/decrypt sample evidence |
| age private key | Annual recipient review | host/device/custody/recovery exposure | Faiz approval | SOPS re-encryption evidence |
| Faiz Recovery Root | custody/compromise only | offline package exposure, root compromise | Faiz only | offline recovery evidence |
| Break-glass credentials | after every use | any activation | Faiz approval | break-glass post-review |

---

## 7. Standard Rotation Workflow

Every scheduled rotation must follow this sequence:

1. **Open evidence artifact** at `evidence/secrets-rotation/<date>-<secret-id>.md`.
2. **Record scope**: secret_id, provider, consumer, current key label/fingerprint, classification, approval mode, planned window.
3. **Run preflight** from Section 4.2.
4. **Create new secret** in provider dashboard/API or crypto service.
5. **Store new secret only in SOPS or approved key registry**.
6. **Deploy new secret** using read-old/write-new or overlap pattern where provider supports it.
7. **Validate new secret** with provider/service-specific probe.
8. **Monitor service health** for the defined observation window.
9. **Revoke old secret** after validation, unless emergency revocation required earlier.
10. **Verify old secret is no longer accepted** where provider supports negative validation.
11. **Clean runtime plaintext** including `/tmp/.env` and any temporary provider export.
12. **Update inventory**: `rotated_at`, `rotation_due_at`, `key_version`, evidence path, status.
13. **Write final evidence** with no plaintext secrets.
14. **Notify Faiz** if approval was required or blast radius exceeded expected scope.

---

## 8. SOPS + age Rotation Workflow

### 8.1 SOPS Secret Value Rotation

For a provider secret stored in `/home/guinevere/config/.env.sops.yaml`, Guinevere must:

1. Confirm `/home/guinevere/.age/key.txt` exists, owner-only, mode `0600`.
2. Decrypt SOPS only on authorized host with Tailscale access.
3. Write plaintext only to tmpfs/runtime path when unavoidable.
4. Insert the new value into the SOPS document.
5. Re-encrypt with SOPS immediately.
6. Validate `sops -d /home/guinevere/config/.env.sops.yaml` succeeds.
7. Restart or reload only the affected service.
8. Verify service-specific probe.
9. Shred or delete temporary plaintext material.
10. Commit only encrypted SOPS file if repository workflow is used.

### 8.2 age Recipient Rotation

For `sec-age-private-key`, Guinevere must:

1. Obtain Faiz approval.
2. Generate new age keypair on authorized host or offline recovery environment.
3. Add new age public recipient to SOPS configuration.
4. Re-encrypt every SOPS file.
5. Validate decrypt with new private key.
6. Keep old age key only during bounded transition window.
7. Deploy new private key to `/home/guinevere/.age/key.txt` with mode `0600`.
8. Validate startup decrypt and affected services.
9. Remove old recipient from SOPS after validation.
10. Rotate offline recovery package copy.
11. Record evidence without private key material.

### 8.3 Runtime Decrypted Env Cleanup

Every rotation touching SOPS must verify:

- `/tmp/.env` or equivalent runtime file is `0600`.
- The file is on tmpfs or runtime-only storage when available.
- The file is not included in backups.
- The file is removed after service load or stop.
- No sub-agent, markdown generation step, grep output, screenshot, or log captures plaintext values.

---

## 9. Autonomous Rotation Governance

Guinevere may rotate autonomously when all conditions are true:

- Rotation is scheduled or low-risk provider-supported.
- Secret is not `sec-age-private-key`, `sec-faiz-recovery-root`, `sec-break-glass-cred`, or compromised Domain KEK requiring high-blast-radius rewrap.
- Preflight passes.
- Provider dashboard/API flow is unambiguous.
- Rollback path exists.
- Evidence path is ready.
- No safe-word/distress state is active.
- No incident freeze is active.

Guinevere must pause and request Faiz review when:

- Provider UI/API changed unexpectedly.
- Scope or permissions are unclear.
- Validation fails.
- Revoke path is destructive or irreversible.
- Rotation could cause prolonged outage.
- Emergency response requires high-blast-radius revocation.
- Tailscale/VPS lockout risk exists.

---

## 10. Per-Secret Rotation Procedures

### 10.1 9Router Credentials (`sec-9router-primary`, `sec-9router-fallback`)

| Field | Procedure |
|---|---|
| Preconditions | Verify queue can tolerate brief LLM retry; open evidence; confirm provider dashboard/API access. |
| Rotation Steps | Generate new key in 9Router dashboard; update SOPS; reload `guinevere-core`; keep old key until validation passes. |
| Validation | Execute minimal LLM call; verify model route; verify core and sub-agent retry behavior. |
| Revoke Old | Revoke old provider key after successful validation. |
| Rollback | Restore old SOPS value only if old key has not been revoked; otherwise queue tasks and generate replacement. |
| Evidence | provider key label/fingerprint, validation timestamp, service health, revoke confirmation. |
| Blast Radius | core persona, reasoning, sub-agents, autonomous coding. |

### 10.2 Discord Bot Token (`sec-discord-bot`)

| Field | Procedure |
|---|---|
| Preconditions | Confirm Faiz can tolerate Discord interface reconnect; prepare fallback notification path. |
| Rotation Steps | Reset bot token in Discord Developer Portal; update SOPS; restart Discord worker/core. |
| Validation | Gateway connection, bot identity, slash command, message send/receive. |
| Revoke Old | Token reset revokes old token automatically. |
| Rollback | No rollback to old token after reset; generate new token if validation fails. |
| Evidence | bot ID, reset timestamp, command test result, gateway reconnect status. |
| Blast Radius | primary interface and notifications. |

### 10.3 GitHub PAT and Webhook Secret (`sec-github-pat`, `sec-github-webhook`)

| Field | Procedure |
|---|---|
| Preconditions | Verify required repository scopes; pause non-essential deploy operations. |
| Rotation Steps | Create new fine-grained PAT; update SOPS; validate MCP/git operations; rotate webhook secret separately; update receiver config. |
| Validation | GitHub API call, repository read/write per scope, MCP operation, webhook signature verification. |
| Revoke Old | Revoke old PAT and old webhook secret after validation. |
| Rollback | If old PAT still active, restore SOPS; otherwise issue a new PAT with corrected scope. |
| Evidence | token label, scopes, expiry, API result, webhook signature test. |
| Blast Radius | coding agent, evidence/reporting, self-deploy, GitHub automation. |

### 10.4 Gmail OAuth and Resend (`sec-gmail-oauth`, `sec-resend-api`)

| Field | Procedure |
|---|---|
| Preconditions | Faiz available for OAuth re-auth if required; email send/receive test account ready. |
| Rotation Steps | Revoke or refresh Gmail OAuth credentials; complete re-auth; update SOPS; generate new Resend key; update SOPS. |
| Validation | Gmail send/read test, refresh-token persistence test, Resend transactional send test. |
| Revoke Old | Revoke old OAuth grant/key and old Resend API key. |
| Rollback | OAuth rollback requires re-auth; Resend old key usable only if not revoked. |
| Evidence | provider key label, OAuth client ID, test message IDs, revoke timestamp. |
| Blast Radius | client communication, invoices, email notifications. |

### 10.5 Gotify Token (`sec-gotify-token`)

| Field | Procedure |
|---|---|
| Preconditions | Confirm backup notification channel; open evidence. |
| Rotation Steps | Create new Gotify token; update SOPS; reload notification worker. |
| Validation | Send test push and confirm receipt. |
| Revoke Old | Revoke old Gotify token. |
| Rollback | Restore old token only if not revoked; otherwise create another token. |
| Evidence | token label/fingerprint, push test timestamp. |
| Blast Radius | push backup notifications. |

### 10.6 PostgreSQL Per-Service Passwords

Applies to `sec-postgres-core`, `sec-postgres-surveillance`, `sec-postgres-financial`, `sec-postgres-readonly`, and `sec-postgres-admin`.

| Field | Procedure |
|---|---|
| Preconditions | Low-traffic window; backup healthy; PgBouncer reachable; affected service health checked. |
| Rotation Steps | Create/stage new password with `ALTER ROLE`; update SOPS; reload PgBouncer; restart affected service if needed. |
| Validation | Connection test through PgBouncer, role-specific query, write/insert test for writer roles, Grafana query for read-only. |
| Revoke Old | PostgreSQL password replacement revokes old password; force disconnect old sessions if compromise. |
| Rollback | Apply previous password only if not compromised and still available in encrypted recovery path. |
| Evidence | role name, rotation time, connection test, PgBouncer reload result, no plaintext password. |
| Blast Radius | memory, surveillance, financial, dashboards, maintenance. |

### 10.7 Redis Auth (`sec-redis-auth`)

| Field | Procedure |
|---|---|
| Preconditions | Accept cache/session disruption; verify Redis persistence mode; prepare service restart. |
| Rotation Steps | Update Redis password in config/SOPS; apply `CONFIG SET requirepass` where safe; restart Redis and dependent services. |
| Validation | AUTH success, ping/pong, queue operation, session state behavior. |
| Revoke Old | Old password invalid after config change/restart. |
| Rollback | Reapply previous password only if not compromised. |
| Evidence | Redis auth test and service health. |
| Blast Radius | cache, queue, pub/sub, session state. |

### 10.8 Cloudflare R2 and idcloudhost S3 Credentials

| Field | Procedure |
|---|---|
| Preconditions | Backup window safe; object lifecycle known; provider dashboard/API access. |
| Rotation Steps | Create new scoped key; update SOPS; run upload/download/list test; validate backup job; keep old key during overlap. |
| Validation | R2 upload/download; idcloudhost S3 upload/download; restore sample; lifecycle rule check. |
| Revoke Old | Revoke old access key after successful backup validation. |
| Rollback | Restore old key if active; otherwise create replacement key. |
| Evidence | key label, bucket/prefix, test object ID, restore check result, revoke confirmation. |
| Blast Radius | WAL backups, pg_dump, surveillance archive, disaster recovery. |

### 10.9 Fernet Compatibility Ring (`sec-fernet-compat`)

| Field | Procedure |
|---|---|
| Preconditions | Identify all fields using Fernet compatibility; confirm AES-256-GCM migration state. |
| Rotation Steps | Add new key to MultiFernet ring as primary; keep old keys read-only; re-encrypt legacy fields; verify counts. |
| Validation | Legacy decrypt test, new encrypt test, record-count reconciliation, sample ciphertext metadata. |
| Revoke Old | Retire old key only after all records re-encrypted and verified. |
| Rollback | Keep old read-only key until verification complete; if data unreadable, pause retirement and restore ring order. |
| Evidence | key_version, record counts, sample hashes, no plaintext content. |
| Blast Radius | legacy encrypted fields and migration path. |

### 10.10 Domain KEKs and Wrapped DEKs

Applies to secrets, profile, safe-word/distress, journal, surveillance, financial, backup, export, and audit domains.

| Field | Procedure |
|---|---|
| Preconditions | Faiz approval; domain inventory complete; sample decrypt set selected; incident freeze checked. |
| Rotation Steps | Generate new Domain KEK; mark old `read_only`; wrap new DEKs or rewrap existing DEKs; update `key_version`; run rewrap job. |
| Validation | DEK wrap/unwrap test, sample decrypt, record count, ciphertext hash, audit log review. |
| Revoke Old | Retire old KEK after full verification; mark compromised immediately if incident. |
| Rollback | Dual-key read window must remain until all samples and counts pass. |
| Evidence | key_id, key_version, domain, counts, validation hashes, no plaintext. |
| Blast Radius | entire encrypted data domain. |

### 10.11 age Private Key and SOPS Files

| Field | Procedure |
|---|---|
| Preconditions | Faiz approval; maintenance window; recovery package ready; all SOPS files enumerated. |
| Rotation Steps | Generate new age keypair; re-encrypt every SOPS file; deploy new private key to `/home/guinevere/.age/key.txt`; chmod `0600`; validate decrypt. |
| Validation | `sops -d` succeeds on authorized host; unauthorized host fails; services start. |
| Revoke Old | Remove old recipient and delete old private key after transition. |
| Rollback | Keep old key offline during bounded window until all files validated. |
| Evidence | public recipient fingerprint, file list, decrypt test, permission check. |
| Blast Radius | entire SOPS secret inventory. |

### 10.12 Device HMACs and Tasker/Windows Secrets

| Field | Procedure |
|---|---|
| Preconditions | Device access available; spoofing risk assessed; receiver can reject old signatures. |
| Rotation Steps | Generate new HMAC secret; update SOPS and device config; deploy to Tasker/Windows daemon. |
| Validation | Signed payload accepted with new secret; old signature rejected. |
| Revoke Old | Remove old secret from device and receiver. |
| Rollback | Reissue another secret if device config fails; do not reuse exposed secret. |
| Evidence | signature validation timestamp, device ID, receiver result. |
| Blast Radius | Android/Windows surveillance ingestion. |

### 10.13 Sentry, Brave, Exa, Prometheus, Grafana

| Field | Procedure |
|---|---|
| Preconditions | Confirm provider/dashboard access and test probes. |
| Rotation Steps | Generate/regenerate token or credential; update SOPS; reload affected service. |
| Validation | Sentry event send, Brave/Exa search test, Prometheus scrape, Grafana login/query. |
| Revoke Old | Revoke old provider credential. |
| Rollback | Use old credential only if not revoked/exposed. |
| Evidence | provider key label, test result, revoke confirmation. |
| Blast Radius | observability, search, diagnostics. |

### 10.14 Baileys Session

| Field | Procedure |
|---|---|
| Preconditions | Faiz available if QR/re-link required; WhatsApp risk accepted. |
| Rotation Steps | Invalidate old session; generate new session/auth state; encrypt session store; update SOPS metadata if used. |
| Validation | WhatsApp connect, send/receive test, reconnection test. |
| Revoke Old | Remove old session files and invalidate linked device if provider supports. |
| Rollback | Re-link through Faiz; do not restore exposed session. |
| Evidence | session label/hash, connection timestamp, no message content. |
| Blast Radius | WhatsApp client communication. |

### 10.15 Break-Glass Credentials and Recovery Package

| Field | Procedure |
|---|---|
| Preconditions | Faiz explicit approval except confirmed emergency containment; offline package available. |
| Rotation Steps | Generate new break-glass credential; update offline recovery package; verify sealed package; retire old credential. |
| Validation | Recovery drill or non-destructive access test. |
| Revoke Old | Revoke immediately after every use. |
| Rollback | No rollback to used break-glass secret; generate replacement. |
| Evidence | time box, reason, approver, post-use rotation, recovery checksum. |
| Blast Radius | full recovery/admin plane. |

---

## 11. Emergency and Breach Rotation

### 11.1 Emergency Triggers

Emergency rotation must start when any of these occur:

- Plaintext secret appears in logs, docs, chat, reports, screenshots, browser transcript, or shell history.
- Provider reports compromise or suspicious access.
- GitHub repository exposure includes secrets or SOPS plaintext.
- VPS, Tailscale device, or age key compromise is suspected.
- Unauthorized DB/object storage access appears.
- Safe-word/distress log or intimate data encryption key exposure is suspected.
- Break-glass credential is used.
- Recovery package exposure is suspected.

### 11.2 Emergency Priority Order

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

### 11.3 Emergency Evidence

Emergency evidence must include:

- Incident ID and SEV level.
- Secret IDs affected.
- Detection source.
- Timeline.
- Containment action.
- Rotation/revocation action.
- Validation result.
- Residual risk.
- Follow-up owner and due date.

Emergency evidence must not include plaintext secret values.

---

## 12. Zero-Downtime Strategies

| Secret Type | Zero-Downtime Pattern | Required Validation |
|---|---|---|
| Provider API keys | create new key → deploy new → validate → revoke old | API call success and old key revocation confirmation |
| PostgreSQL passwords | staged `ALTER ROLE` + SOPS update + PgBouncer reload + connection drain | role-specific query and service health |
| Redis auth | planned restart; cache-miss accepted | AUTH + ping/pong + queue behavior |
| Object storage keys | dual-key overlap + backup/restore probe | upload/download/restore sample |
| Fernet key ring | MultiFernet new primary + read-old/write-new + re-encrypt | decrypt old, encrypt new, count reconciliation |
| Domain KEK | dual-key read + rewrap DEKs + retire old after verification | sample decrypt and count verification |
| age key | maintenance window + re-encrypt all SOPS + bounded old-key overlap | authorized decrypt succeeds and services start |
| OAuth tokens | re-auth overlap when provider supports | send/read provider test |
| Device HMAC | deploy new device secret + receiver overlap if supported | new signature accepted, old rejected after cutover |

If zero downtime is impossible, the runbook must document expected downtime, fallback channel, affected services, and Faiz notification requirement.

---

## 13. Verification and Testing

### 13.1 Required Rotation Tests

| Test ID | Scope | Required Result |
|---|---|---|
| SROT-001 | SOPS decrypt | Authorized host decrypts; unauthorized path fails. |
| SROT-002 | Plaintext leak scan | No plaintext secret appears in docs/logs/evidence. |
| SROT-003 | Provider API key | New key works; old key revoked. |
| SROT-004 | Discord | Gateway reconnect and command test pass. |
| SROT-005 | GitHub PAT | API and MCP operation pass with intended scopes. |
| SROT-006 | PostgreSQL | PgBouncer connection and role-specific query pass. |
| SROT-007 | Redis | AUTH and queue/cache probe pass. |
| SROT-008 | Object storage | Upload/download/restore probe passes. |
| SROT-009 | OAuth/email | send/read or send-only probe passes. |
| SROT-010 | Fernet ring | old decrypt/new encrypt/re-encrypt count pass. |
| SROT-011 | Domain KEK | DEK rewrap and sample decrypt pass. |
| SROT-012 | age key | SOPS files decrypt after recipient rotation. |
| SROT-013 | Device HMAC | new signature accepted, old rejected. |
| SROT-014 | Recovery package | checksum and non-destructive restore drill pass. |
| SROT-015 | Evidence artifact | evidence contains IDs/hashes only, no secret values. |

### 13.2 Secret Scanner Requirement

After every rotation, Guinevere must scan changed files, logs, evidence, and generated reports for secret-shaped values. Any positive finding must become an incident until proven false positive.

---

## 14. Audit Trail and Evidence

### 14.1 Evidence Path

Routine evidence must be written to:

`evidence/secrets-rotation/<YYYY-MM-DD>-<secret-id>.md`

Incident evidence must be written to:

`evidence/secrets-rotation/<YYYY-MM-DD>-incident-<SEV>-<short-scope>.md`

### 14.2 Evidence Template

Every evidence file must include:

- Secret ID.
- Classification.
- Rotation type: scheduled, autonomous, emergency, recovery, break-glass.
- Approver and approval evidence when required.
- Preflight checklist outcome.
- Rotation action summary.
- Validation probes and results.
- Old credential revocation status.
- Rollback status.
- Service health after rotation.
- Inventory update status.
- Follow-up items.
- Explicit statement: `No plaintext secret values are included in this artifact.`

---

## 15. Recovery Package and Break-Glass

The offline recovery package must contain only encrypted or sealed material and must include:

- Faiz Recovery Root material or recovery instructions.
- age key backup or recovery path.
- Break-glass credentials.
- SOPS bootstrap instructions.
- Domain KEK recovery metadata.
- Provider account recovery notes.
- Inventory snapshot with secret IDs and fingerprints only.
- Restore procedure.
- Checksum/manifest.
- Last-tested date.

Break-glass access must be time-boxed, logged, followed by mandatory rotation of every credential used, and reviewed by Faiz after the event.

---

## 16. Incident Escalation

| Severity | Data / Secret Impact | Required Action |
|---|---|---|
| SEV0 | Faiz Recovery Root, age private key, break-glass, Domain KEK, Critical intimate/safe-word key compromise | immediate containment, Faiz approval where feasible, rotate root/affected domains, incident report |
| SEV1 | GitHub PAT, DB admin, R2/S3 backup key, 9Router key, Discord token compromise | revoke/rotate immediately, validate services, rotate adjacent secrets if blast radius unclear |
| SEV2 | provider API key or OAuth token exposure without confirmed abuse | rotate within same day, validate, audit logs |
| SEV3 | Confidential observability credential exposure | rotate within 24 hours, validate observability |
| SEV4 | false positive or test-mode leak blocked before exposure | document near miss, update scanner/test |

Unsafe recall or exposure of intimate/safe-word data tied to a secret failure must also trigger Persona Safety near-miss handling.

---

## 17. Implementation Readiness Requirements

Before claiming automated secrets rotation is production-ready, Guinevere must have:

1. Complete secret inventory with all Section 5 fields.
2. SOPS file inventory and authorized age recipient list.
3. Provider rotation probes for every external provider.
4. Database role rotation procedure tested in staging or dry run.
5. Redis auth rotation tested.
6. Object storage key rotation and restore sample tested.
7. Fernet compatibility ring scope identified.
8. Domain KEK rewrap job implemented and tested.
9. Recovery package checksum and restore drill completed.
10. Break-glass post-use rotation procedure tested.
11. Secret scanner configured for docs, logs, evidence, and generated reports.
12. Evidence writer that redacts secret values by construction.
13. Scheduler that respects approval gates and safe-mode restrictions.
14. Incident escalation path and postmortem template.
15. Monthly review of overdue rotations.

---

## 18. Review Cadence

| Review | Frequency | Owner | Output |
|---|---|---|---|
| Secret inventory review | Monthly | Guinevere + Faiz | inventory update evidence |
| Overdue rotation review | Weekly | Guinevere | overdue list and remediation plan |
| SOPS recipient review | Annual and trigger-based | Faiz + Guinevere | recipient review evidence |
| Recovery package test | Quarterly | Faiz + Guinevere | recovery drill evidence |
| Break-glass review | After every use | Faiz | post-use rotation evidence |
| Provider scope review | Quarterly | Guinevere | least-privilege scope update |
| Runbook review | Monthly or after incident | Faiz + Guinevere | runbook update or ADR backlog item |

---

## 19. Unresolved Assumptions and Backlog

| Item | Status | Required Follow-up | Target Document |
|---|---|---|---|
| Exact provider dashboard UI/API steps | Open | Capture provider-specific screenshots or API commands without secrets. | Provider Rotation Playbooks |
| RBAC/ABAC approval matrix | Backlog | Define which services/actions can rotate which secret classes. | Access Control RBAC/ABAC Matrix |
| Full incident process | Backlog | Define postmortem, escalation, notification, and severity owner model. | Incident Response & Postmortem Runbook |
| Fernet compatibility scope | Open | Inventory exact fields still using Fernet. | Database ERD & Migration Strategy |
| Domain KEK automation | Backlog | Implement rewrap jobs and validation probes. | Crypto Service Implementation Spec |
| Recovery package format | Open | Define sealed package layout and storage medium. | Key Recovery & Break-Glass Runbook |
| Redis rotation downtime | Known limitation | Accept cache disruption or implement dual-auth pattern if available. | Runtime Hardening Spec |
| Baileys session re-link | Open | Define QR/re-link procedure with Faiz availability. | Communication Channel Runbook |

---

# Appendix A — Rotation Checklist

- [ ] Secret ID exists in inventory.
- [ ] Classification confirmed.
- [ ] Approval mode confirmed.
- [ ] Evidence file opened.
- [ ] Provider/API access verified.
- [ ] SOPS decrypt verified.
- [ ] New secret created.
- [ ] SOPS updated.
- [ ] Service reloaded/restarted.
- [ ] Validation probe passed.
- [ ] Old secret revoked.
- [ ] Old secret negative test performed where possible.
- [ ] Runtime plaintext cleaned.
- [ ] Inventory updated.
- [ ] Evidence finalized with no plaintext values.

---

# Appendix B — Emergency Rotation Checklist

- [ ] Incident ID assigned.
- [ ] SEV level assigned.
- [ ] Affected secret IDs identified.
- [ ] Active exposure contained.
- [ ] Minimal evidence preserved.
- [ ] Faiz approval captured or emergency rationale documented.
- [ ] Exposed secret revoked.
- [ ] Replacement generated.
- [ ] SOPS/key registry updated.
- [ ] Affected services validated.
- [ ] Adjacent secrets assessed.
- [ ] Secret scanner run.
- [ ] Incident evidence written.
- [ ] Postmortem scheduled.

---

# Appendix C — Evidence Redaction Rules

Evidence may include:

- secret_id.
- provider name.
- key label.
- key fingerprint/hash prefix if non-sensitive.
- key version.
- rotation timestamp.
- validation result.
- revoke confirmation.
- service health status.

Evidence must not include:

- plaintext secret values.
- full OAuth refresh tokens.
- full API keys.
- decrypted SOPS content.
- private age keys.
- KEK/DEK material.
- screenshots showing provider secret values.
- shell history with secret values.

---

# Appendix D — Approval and Review Record

## Review Record

- Reviewer: Faiz (Owner)
- Review Date: 2026-05-30
- Decision: Accepted
- Notes: Approved as operational child of ADR-015/ADR-008/ADR-019 and `Guinevere_EncryptionKeyManagementStandard_v1.0.md`. Autonomous scheduled rotation is allowed with preflight, evidence, and rollback controls. Emergency or high-blast-radius rotation requires Faiz approval where feasible.

---

# Appendix E — Next Recommended Document

Guinevere recommends creating **Access Control RBAC/ABAC Matrix** next.

Reason: this runbook defines how secrets are rotated, but it repeatedly depends on action-level authorization: which runtime service, sub-agent, tool, or autonomous workflow may read, rotate, revoke, rewrap, approve, or break-glass each secret class. Without RBAC/ABAC, rotation controls remain operationally defined but not enforceable at permission boundaries.
