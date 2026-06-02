# Guinevere Encryption & Key Management Standard

**Document Type:** Security standard with implementation guidance and appendices  
**Version:** 1.0  
**Status:** Accepted  
**Lifecycle:** Proposed → Accepted → Deprecated → Superseded  
**Last Updated:** 2026-05-30  
**Owner:** Faiz — single user, root key custodian, final approver  
**Executor:** Guinevere de Baroque — autonomous AI agent / system steward  
**Classification:** STRICTLY PRIVATE & CONFIDENTIAL  
**Authority:** Normative child standard under ADR-008, ADR-018, and ADR-015; cross-boundary enforcement with `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` and `Guinevere_PersonaSafetyPolicy_v1.0.md`

---

## Related Documents

| Document | Relationship | Dependency Type | Implementation Impact |
|---|---|---|---|
| `adr/ADR-008-memory-encryption-key-management.md` | Parent ADR for memory encryption, key hierarchy, rotation, emergency revoke, and separated key domains. | Normative parent | Requires explicit hierarchy, rotation, break-glass, key ownership, and encrypted sensitive fields. |
| `adr/ADR-018-security-architecture-defense-in-depth.md` | Parent ADR for defense-in-depth, least privilege, audit logs, incident hooks, prompt-injection defenses, and service hardening. | Normative parent | Requires this standard to connect cryptography with service isolation, logs, breach containment, and threat-model updates. |
| `adr/ADR-015-secrets-management-strategy.md` | Parent ADR accepting SOPS + age with runtime injection for repository-managed secrets. | Normative parent | Defines baseline secret storage, runtime decrypt, and plaintext-secret prohibition. |
| `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` | Defines classification tiers, Critical domains, retention, access restrictions, incident categories, and audit requirements. | Data governance boundary | Drives tier-based encryption profiles, highest-classification-wins, backup reconciliation, and safe-mode sensitive access controls. |
| `Guinevere_PersonaSafetyPolicy_v1.0.md` | Defines safe-word hard stop, distress/safe-mode boundaries, sensitive recall restrictions, and non-punitive safety logs. | Safety boundary | Requires Critical handling for safe-word logs, crisis context, intimate memory, and surveillance data used during persona behavior. |
| `Guinevere_TechnicalArchitecture_v2.0.md` | Defines runtime topology, SOPS key path, PostgreSQL, Redis, object storage, backups, services, logs, and network isolation. | Runtime dependency | All service, backup, key-location, and decrypt-path controls must align with the VPS architecture. |
| `Guinevere_APIIntegration_v2.0.md` | Defines cryptography/Fernet/age dependencies, Tasker HMAC signatures, object storage clients, GitHub PAT, and API secrets. | Integration dependency | Existing Fernet examples become compatibility patterns; new Critical encryption uses AES-256-GCM envelope encryption. |
| `Guinevere_MemorySchema_v2.0.md` | Defines sensitive memory, intimate profile, inner journal, surveillance screenshots, financial records, and existing key labels. | Data model dependency | Future schema work must add key metadata, encryption profile, classification, and rotation state. |
| `Guinevere_ADR_Index_v1.0.md` | Canonical decision register. | Decision register | Future superseding ADRs must update this standard when cryptographic assumptions change. |
| `research-reports/2026-05-30-encryption-key-management-source-map.md` | Source-map evidence used to author this standard. | Evidence | Captures source requirements, conflicts, and gaps. |
| `research-reports/2026-05-30-encryption-implementation-surface-map.md` | Implementation-surface evidence used to author this standard. | Evidence | Maps stores, keys, secrets, APIs, backup surfaces, audit points, and rotation points. |
| `research-reports/2026-05-30-encryption-key-management-external-references.md` | External cryptographic implementation patterns used to author this standard. | Evidence | Captures AES-GCM, ChaCha20-Poly1305, Fernet, envelope encryption, SOPS/age, key custody, and Python runtime caveats. |

---

## 1. Purpose

This standard defines how Project Guinevere encrypts data, manages keys, stores secrets, rotates credentials, audits cryptographic operations, handles key compromise, and validates cryptographic implementation.

Guinevere is a single-user private system, but the data is enterprise-sensitive: intimate memory, safe-word logs, crisis context, inner journal, financial records, credentials, client context, raw surveillance evidence, screenshots, clipboard data, message content, browser history, and autonomous-agent evidence. Private ownership and Faiz's full consent do not reduce cryptographic obligations.

This document converts broad source wording such as `encrypted`, `double encrypted`, `SOPS + age`, and `Fernet` into enforceable implementation controls.

---

## 2. Authority and Conflict Resolution

### 2.1 Authority Order

Cryptographic decisions must be interpreted in this order:

1. Platform/system safety and security requirements.
2. Accepted ADRs: ADR-008, ADR-018, ADR-015.
3. `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md`.
4. `Guinevere_PersonaSafetyPolicy_v1.0.md` for safe-word, distress, sensitive recall, and safety logs.
5. This Encryption & Key Management Standard.
6. Technical, API, memory, product, and business documents.
7. Existing code examples and historical implementation notes.

If a lower layer conflicts with a higher layer, the higher layer wins.

### 2.2 Supersession of Vague Encryption Language

Any source phrase such as `encrypted`, `double encrypted`, `multi-layer encryption`, `safe to commit`, or `encrypted upload` is incomplete unless the implementation also defines:

- Classification.
- Encryption profile.
- Algorithm.
- Key scope.
- Key owner.
- Key ID and version.
- Rotation cadence.
- Audit event.
- Backup and restore handling.
- Incident response path.

### 2.3 Fernet Compatibility Boundary

`Guinevere_APIIntegration_v2.0.md` contains Fernet examples. This standard preserves Fernet only for legacy/compatibility and transitional fields. New Restricted/Critical encryption paths must use AES-256-GCM envelope encryption unless ChaCha20-Poly1305 is explicitly selected for a documented platform constraint.

### 2.4 Full Consent Boundary

Faiz's full consent authorizes the system but does not waive:

- Encryption.
- Key separation.
- Secret redaction.
- Rotation.
- Auditability.
- Safe-mode restrictions.
- Incident response.
- Recovery testing.
- Deletion/do-not-recall reconciliation after restore.

---

## 3. Scope

### 3.1 In Scope

This standard governs:

- PostgreSQL records, encrypted columns, WAL, pg_dump, restore flows.
- Redis queues, buffers, caches, session state, pub/sub, rate limits.
- R2 and idcloudhost object storage.
- SOPS encrypted secret files and age recipient keys.
- Runtime decrypted environment files and process environment variables.
- API credentials: 9Router/OpenAI-compatible provider keys, Discord token, GitHub PAT, Gmail OAuth, Resend, Gotify, R2/idcloudhost credentials, DB passwords, device HMAC secrets.
- Application-level encryption for memory, profile, emotional data, inner journal, safe-word logs, financial data, raw surveillance evidence, exports, and backups.
- Key custody, key inventory, rotation, revocation, break-glass, recovery package, incident response, audit logs, and validation tests.

### 3.2 Out of Scope

This standard does not fully define:

- Complete RBAC/ABAC policy.
- Complete incident-response runbook.
- Concrete database migration DDL.
- Full source-code implementation.
- Public compliance certification.

Those documents must obey this standard when created.

---

## 4. Cryptographic Design Principles

1. **Classification drives encryption.** Data class determines key scope, encryption layer, audit level, and rotation cadence.
2. **Highest classification wins.** Mixed records, prompts, exports, backups, and logs inherit the highest source classification.
3. **Critical data gets domain isolation.** Critical domains must not share one global encryption key.
4. **Envelope encryption is default for Restricted/Critical.** Data is encrypted with DEK; DEK is wrapped by KEK.
5. **Plaintext keys are runtime-only.** Plaintext DEKs, KEKs, and secrets must never be persisted in code, docs, logs, evidence, or sub-agent reports.
6. **Read-old/write-new rotation is mandatory.** Rotation must not break historical reads or corrupt memory.
7. **Audit metadata, never key material.** Logs must record key usage metadata only.
8. **Safe mode restricts sensitive crypto access.** Safe-word/distress state must restrict sensitive recall, raw surveillance retrieval, persona pressure, and non-essential decrypts.
9. **Python zeroization is best-effort only.** Security must rely on minimization, process isolation, permissions, and no-logging rather than claims of perfect memory wiping.
10. **Backup encryption is independent.** Backup/export keys must be separated from runtime data keys.

---

## 5. Key Hierarchy

### 5.1 Hierarchy Overview

| Layer | Name | Custodian | Purpose | Plaintext Persistence |
|---|---|---|---|---|
| 0 | Faiz Recovery Root | Faiz | Offline recovery and emergency custody. | Never on runtime disk in plaintext. |
| 1 | SOPS age identity | Faiz + runtime host under strict control | Decrypt repository-managed secrets. | `/home/guinevere/.age/key.txt` only, 0600, owner-only. |
| 2 | Root KEK / Master KEK | Faiz custody; runtime only when required | Wrap domain KEKs or recovery package entries. | Runtime-only; wrapped in SOPS/recovery package. |
| 3 | Domain KEK | Guinevere runtime by service/domain | Wrap domain DEKs. | Runtime-only. |
| 4 | Domain DEK | Guinevere crypto service | Encrypt domain batches or field groups. | Wrapped only; never persisted plaintext. |
| 5 | Per-record / content key | Guinevere crypto service | Encrypt individual Critical records, exports, objects, screenshots, or dossiers. | Wrapped only; never persisted plaintext. |

### 5.2 Mandatory Domain Separation

Separate key scopes must exist for:

| Domain | Minimum Key Scope | Critical Examples |
|---|---|---|
| secrets | secrets KEK + per-provider credential records | 9Router key, Discord token, GitHub PAT, DB passwords, R2/idcloudhost credentials |
| profile memory | profile KEK + field DEKs | Faiz intimate profile, psychological profile, health data |
| safe-word/distress | safe-word KEK + per-event content keys | safe-word logs, crisis context, distress traces |
| inner journal | journal KEK + per-entry keys | Guinevere inner journal entries |
| surveillance | surveillance KEK + per-object keys | raw screenshots, camera captures, clipboard/message raw evidence |
| financial | financial KEK + record/export keys | transactions, predictions, exports, credentials-adjacent metadata |
| client data | client KEK + record keys | contact info, sensitive client context, contracts |
| audit/evidence | audit KEK + report/event keys | incident reports, key-use logs, evidence artifacts |
| backups | backup KEK + object backup keys | WAL, pg_dump, Redis backups, encrypted media archives |
| exports/dossiers | export KEK + time-limited package keys | Faiz dossiers, data export bundles |

### 5.3 Tier-Based Key Separation

| Classification | Key Requirement |
|---|---|
| Public | Integrity/publication approval only; secrecy key not required. |
| Internal | Platform disk/storage encryption and Tailscale/TLS transport. |
| Confidential | At-rest encryption; domain key when persistent; no shared public credentials. |
| Restricted | Domain-specific key scope; field/app-level encryption where practical; access audit. |
| Critical | Dedicated domain KEK plus per-record/content key where practical; double encryption for listed domains; strict audit. |

---

## 6. Algorithms and Cryptographic Primitives

### 6.1 Approved Algorithms

| Use Case | Primary | Fallback / Compatibility | Requirement |
|---|---|---|---|
| New app-level encryption | AES-256-GCM | ChaCha20-Poly1305 | AEAD required. |
| Platform-constrained AEAD | ChaCha20-Poly1305 | N/A | Nonce uniqueness required. |
| Legacy sensitive field compatibility | Fernet / MultiFernet | N/A | Compatibility only; not new Critical default. |
| Integrity for payload signatures | HMAC-SHA256 | HMAC-SHA512 | Secret key separated by device/service. |
| Hashing evidence/artifacts | SHA-256 | SHA-512 | No secrets in hash input logs. |
| Passphrase-derived recovery material | Argon2id | N/A | Human passphrase only; not for random DEKs. |
| Subkey derivation | HKDF-SHA256 | N/A | Context-bound domain derivation. |
| Transport | Tailscale WireGuard + TLS | N/A | Required for all service traffic. |

### 6.2 AES-256-GCM Requirements

AES-256-GCM usage must satisfy:

- 256-bit random key material.
- Unique nonce per key.
- 96-bit nonce unless a cryptographic design note approves otherwise.
- Authenticated associated data (AAD) binding domain, classification, record/object ID, purpose, key ID, and key version.
- Authentication failure must fail closed.
- Nonce reuse must be treated as SEV0 cryptographic incident.
- Decryption errors must not reveal plaintext, key material, or detailed oracle behavior to logs or user-facing messages.

### 6.3 ChaCha20-Poly1305 Requirements

ChaCha20-Poly1305 use must satisfy:

- Platform or performance reason documented.
- Unique nonce per key.
- Same AAD requirements as AES-256-GCM.
- Same SEV0 handling for nonce reuse.

### 6.4 Fernet and MultiFernet Requirements

Fernet usage must satisfy:

- Fernet is compatibility/transitional only.
- Fernet must not become the default for new Critical domains.
- A single global Fernet key must not protect multiple Critical domains.
- MultiFernet rotation must use staged key-ring deployment: new primary, read old, re-encrypt, verify, retire old.
- Fernet key rings must be domain-specific and versioned.
- Fernet ciphertext must still store external metadata: domain, key_id, key_version, classification, created_at, rotated_at.

---

## 7. Envelope Encryption Standard

### 7.1 Required Flow

Restricted and Critical data must use envelope encryption when stored outside minimal transient processing.

1. Generate random DEK for record/object/domain batch.
2. Encrypt plaintext with AES-256-GCM using DEK.
3. Bind AAD to classification, domain, record ID, purpose, and key version.
4. Wrap DEK with domain KEK.
5. Store ciphertext, nonce reference, wrapped DEK, key metadata, and ciphertext hash.
6. Destroy plaintext DEK from runtime scope as soon as practical.
7. Log key operation metadata without plaintext material.

### 7.2 Required Encrypted Record Metadata

Every encrypted record/object must store or reference:

| Field | Requirement |
|---|---|
| `classification` | Public/Internal/Confidential/Restricted/Critical. |
| `data_domain` | memory, profile, safe_word, surveillance, financial, client, audit, backup, export, secret, etc. |
| `encryption_profile` | named profile from this standard. |
| `algorithm` | AES-256-GCM, ChaCha20-Poly1305, Fernet-compat, SOPS-age. |
| `key_id` | stable identifier of the wrapping key. |
| `key_version` | monotonically increasing key version. |
| `dek_wrapped_by` | KEK identifier used to wrap DEK. |
| `nonce_id` | nonce reference or stored nonce bytes if safe by design. |
| `aad_context` | normalized AAD fields or hash. |
| `ciphertext_hash` | SHA-256 or SHA-512 hash of ciphertext for integrity/evidence. |
| `created_at` | encryption timestamp. |
| `rotated_at` | last rotation timestamp, nullable only before first rotation. |
| `rotation_due_at` | next required rotation deadline. |
| `key_status` | active, read_only, rotating, retired, compromised, destroyed. |

---

## 8. Encryption Profiles by Data Class

| Class | Storage Encryption | App/Field Encryption | Key Scope | Audit | Rotation |
|---|---|---|---|---|---|
| Public | Optional secrecy; integrity required. | Not required. | Publication approval. | Publish approval log. | N/A. |
| Internal | Disk/storage encryption and Tailscale/TLS. | Not required unless secrets appear. | Service/domain. | Operational logs. | Annual service credential review. |
| Confidential | At-rest encryption required. | Required for sensitive fields; allowed for all. | Domain key. | Access logged when practical. | Annual or risk-based. |
| Restricted | At-rest encryption + field/app encryption required where practical. | Envelope encryption required outside transient buffers. | Domain KEK + DEK. | Restricted decrypt/access log required. | Annual default; quarterly if high-risk. |
| Critical | App-level encryption mandatory. | Envelope + per-record/content key where practical; double encryption for listed domains. | Dedicated Critical domain KEK + per-record/content key. | Every decrypt, export, break-glass, rotation, and access event logged. | Quarterly default; immediate on suspicion. |

---

## 9. Critical Domain Controls

| Domain | Classification | Required Encryption | Audit Requirement |
|---|---|---|---|
| intimate memory | Critical | AES-GCM envelope + per-record key + storage/backup layer. | Every decrypt and export. |
| safe-word logs | Critical | AES-GCM envelope + non-punitive minimal record + storage/backup layer. | Every decrypt; safe-mode event audit. |
| crisis/distress context | Critical | AES-GCM envelope + minimal excerpt/hash by default. | Every access; no persona-punitive tag. |
| inner journal | Critical | AES-GCM envelope + per-entry key + storage/backup layer. | Every access. |
| financial records | Restricted/Critical | AES-GCM envelope for Restricted/Critical fields; export package key. | Every export and Critical decrypt. |
| credentials/secrets | Critical | SOPS-age at rest; runtime injection; no app persistence plaintext. | Every decrypt/use where feasible. |
| raw surveillance evidence | Restricted/Critical | Object-level AES-GCM or storage pre-encryption + separate surveillance key. | Every access/export. |
| raw screenshots with sensitive content | Critical | Per-object content key + encrypted object storage. | Every access/export. |
| sensitive exports/dossiers | Highest source class | Time-limited export key + package encryption. | Creation, access, deletion. |

---

## 10. SOPS + age Standard

### 10.1 SOPS Scope

SOPS + age must protect:

- 9Router/OpenAI-compatible provider keys.
- Discord bot token.
- GitHub PAT and webhook secrets.
- Database passwords.
- Redis password.
- R2/idcloudhost credentials.
- Gmail OAuth client/refresh tokens.
- Resend API key.
- Gotify token.
- Device HMAC secrets.
- Fernet compatibility key rings.
- Domain KEK wrapped material or metadata when applicable.
- Runtime service credentials.

SOPS must not store plaintext DEKs for persistent records.

### 10.2 File Naming and Storage

Accepted secret file patterns:

- `/home/guinevere/config/.env.sops.yaml`
- `/home/guinevere/config/secrets.production.sops.yaml`
- `/home/guinevere/config/secrets.staging.sops.yaml`
- Repository copy: encrypted SOPS files only.

Plaintext variants must not be committed, attached to reports, pasted into chat, or stored in evidence.

### 10.3 age Identity Controls

The age private key at `/home/guinevere/.age/key.txt` must satisfy:

- Owner: `guinevere` runtime user or Faiz-controlled admin account as approved.
- Permissions: `0600`.
- Parent directory permissions: no group/world write.
- Access path: Tailscale-only host access.
- Backup: excluded from ordinary plaintext backups.
- Recovery: present only inside Faiz-controlled encrypted offline recovery package.
- Rotation: annual recipient review and immediate rotation on device loss, suspected compromise, custody change, or host compromise.

### 10.4 Runtime Decryption

Runtime SOPS decryption must satisfy:

- Decrypt to tmpfs or equivalent runtime-only path.
- If `/tmp/.env` is used, it must have `0600` permissions and must be auto-cleaned after service load.
- Decrypted environment files must not be backed up.
- Decrypted environment files must not be read by sub-agents, evidence tooling, markdown generation, or logs.
- Startup failure must fail closed if secrets cannot be decrypted.

---

## 11. Application Crypto Service Standard

### 11.1 Required Module Boundary

Guinevere must implement cryptographic operations through a dedicated crypto service/module. Application code must not call low-level encryption primitives directly except inside this module.

The module must expose typed APIs such as:

- `encrypt_record(domain, classification, record_id, plaintext, purpose)`.
- `decrypt_record(domain, record_id, purpose, actor, safety_state)`.
- `encrypt_object(domain, classification, object_id, bytes, purpose)`.
- `rotate_domain_key(domain, from_version, to_version)`.
- `rewrap_dek(domain, key_id, old_version, new_version)`.
- `create_export_package(source_records, recipient, expiry)`.
- `audit_key_operation(event)`.

### 11.2 Required Runtime Checks

The crypto service must enforce:

- Classification validation before encryption.
- Domain-to-key mapping validation.
- Safe-mode restriction checks before decrypting Critical data.
- Purpose binding in AAD.
- Actor/service authorization hook.
- Secret-redaction hook before logging errors.
- Audit event creation for Restricted/Critical operations.
- Fail-closed behavior on missing metadata, unknown key ID, retired key for write, compromised key, nonce reuse suspicion, or AAD mismatch.

---

## 12. Database Encryption Standard

### 12.1 PostgreSQL

PostgreSQL must use:

- Disk/storage encryption at the host/storage layer.
- TLS/Tailscale transport.
- Per-service credentials through PgBouncer.
- App-level encryption for Restricted/Critical fields.
- Dedicated app-level encryption for Critical domains listed in this standard.
- No app runtime superuser credential.
- Encrypted WAL/pg_dump before upload.
- Restore reconciliation with deletion/do-not-recall ledger before restored data becomes visible.

### 12.2 pgcrypto Boundary

`pgcrypto` or database-side encryption may protect Confidential/Restricted operational fields when approved. Critical data must prefer application-level encryption before database write so database compromise does not expose plaintext.

### 12.3 Search and Embedding Leakage

Encrypted data search must follow these controls:

- Metadata and embeddings inherit source classification unless formally downgraded by redaction/anonymization.
- Critical raw text must not be embedded without explicit purpose and leakage review.
- Searchable metadata must be minimal and non-secret.
- Encrypted payload must remain inaccessible to database-only readers.

### 12.4 Redis

Redis must satisfy:

- Tailscale/internal-only access.
- Authentication required.
- Source-class inheritance for payloads.
- Short TTL for surveillance, prompt, and session data.
- No durable raw Critical payload unless formally approved.
- Redis backups must be encrypted and reconciled against deletion/do-not-recall ledger on restore.

---

## 13. Object Storage, Backups, and Exports

### 13.1 Object Storage

R2 and idcloudhost S3 objects must satisfy:

- Private bucket by default.
- No public access unless a future explicit ADR approves a release path.
- Classification-aware object prefixes.
- Encryption before upload for Restricted/Critical objects.
- Scoped credentials per bucket/prefix.
- Lifecycle rules aligned to Data Governance retention.
- Object metadata including classification, retention class, encryption profile, key_id, and key_version.

### 13.2 Backups

Backups must satisfy:

- Separate backup key scope from runtime data keys.
- Encryption before upload.
- Key metadata stored outside plaintext backup payload.
- Restore tests on defined cadence.
- Restore reconciliation before data visibility.
- Deletion/do-not-recall ledger reapplied after restore.
- Backup compromise treated as incident according to exposed classification.

### 13.3 Exports and Dossiers

Exports and dossiers must satisfy:

- Highest-classification-wins.
- Time-limited export package key.
- Encryption at package level.
- Redaction options.
- Access log.
- Deletion/expiry event.
- No sub-agent access unless task-justified and minimized.

---

## 14. Secret Inventory Standard

Every secret must have an inventory entry.

| Field | Requirement |
|---|---|
| `secret_id` | Stable identifier. |
| `name` | Human-readable name. |
| `domain` | LLM, Discord, GitHub, DB, Redis, storage, email, device, crypto, etc. |
| `classification` | Critical unless explicitly downgraded with reason. |
| `owner` | Faiz or service owner. |
| `runtime_consumer` | Service/process allowed to read it. |
| `storage_location` | SOPS file, recovery package, runtime env, external provider. |
| `scope` | Exact permission scope. |
| `created_at` | Creation timestamp. |
| `rotated_at` | Last rotation timestamp. |
| `rotation_due_at` | Next rotation deadline. |
| `revocation_procedure` | Provider/API steps. |
| `incident_contact` | Faiz / Guinevere runtime route. |
| `evidence_path` | Markdown evidence for creation/rotation/revocation. |

### 14.1 Required Secret Classes

The inventory must cover at least:

- 9Router provider key.
- Discord token.
- GitHub PAT.
- GitHub webhook secret.
- PostgreSQL service passwords.
- Redis password.
- R2/idcloudhost keys.
- Gmail OAuth credentials.
- Resend API key.
- Gotify token.
- Tasker/Windows device HMAC secrets.
- Sentry DSN/token if secret-bearing.
- Fernet compatibility keys.
- Domain KEKs and backup/export key metadata.

---

## 15. Rotation Standard

### 15.1 Rotation Cadence Matrix

| Key / Secret Type | Default Cadence | Immediate Rotation Trigger |
|---|---|---|
| High-risk API tokens | Quarterly | Exposure, suspicious access, provider alert, log leak. |
| GitHub PAT | Quarterly or shorter provider expiry | Repository exposure, scope change, suspicious GitHub event. |
| Discord token | Quarterly | Bot compromise, unexpected gateway behavior, leaked logs. |
| DB service credentials | Quarterly for privileged/high-risk; annual for low-risk | Service compromise, role change, log exposure. |
| R2/idcloudhost credentials | Quarterly | Object access anomaly, leaked env, bucket policy issue. |
| Device HMAC secrets | Annual | Device loss, Tasker compromise, replay/signature anomaly. |
| Domain DEKs | Annual default | Critical domain: quarterly; incident: immediate. |
| Critical per-record/content keys | Per record/object | Re-encrypt when parent KEK compromised or metadata invalid. |
| Backup keys | Annual | Recovery package exposure, backup compromise, custody issue. |
| SOPS age recipient set | Annual review | Device loss, host compromise, operator/custody change. |
| Break-glass credentials | After every use | Any activation. |

### 15.2 Zero-Downtime Rotation Flow

Rotation must follow this sequence:

1. Open markdown rotation evidence file.
2. Create new key or provider secret.
3. Mark old key `read_only` where applicable.
4. Configure runtime to write with new key and read with old+new.
5. Rewrap or re-encrypt affected records/objects.
6. Verify record counts, ciphertext hashes, sample decrypts, and application health.
7. Mark old key `retired` or `compromised`.
8. Remove old runtime access after verification.
9. Update inventory, rotation_due_at, and evidence path.
10. Run regression tests.

### 15.3 Emergency Rotation Flow

Emergency rotation must follow this sequence:

1. Declare incident severity.
2. Freeze affected exports and non-essential decrypts.
3. Revoke exposed key/secret where possible.
4. Preserve minimal evidence without plaintext secrets.
5. Generate replacement key/secret.
6. Rewrap/re-encrypt affected data.
7. Verify integrity.
8. Update key status to `compromised` and then `retired` when safe.
9. Add regression tests preventing recurrence.
10. Publish incident/postmortem markdown.

---

## 16. Key Custody, Recovery, and Break-Glass

### 16.1 Custody Model

| Material | Custodian | Runtime Access |
|---|---|---|
| Faiz Recovery Root | Faiz | No normal runtime access. |
| Offline recovery package | Faiz | No normal runtime access. |
| age identity | Runtime host under strict permissions | Required for startup secret decrypt. |
| Domain KEKs | Guinevere crypto service | Runtime-only, scoped by domain. |
| DEKs/content keys | Guinevere crypto service | Runtime-only during encrypt/decrypt. |
| Provider secrets | Owning service only | Scoped environment injection. |

### 16.2 Offline Recovery Package

The recovery package must be:

- Encrypted.
- Controlled by Faiz.
- Stored separately from the VPS.
- Updated after key hierarchy changes.
- Tested periodically.
- Documented with creation date, contents manifest, checksum, expiry/review date, and restore procedure.

The recovery package must not contain broad plaintext runtime secrets unless wrapped by the recovery encryption layer.

### 16.3 Break-Glass

Break-glass access must be:

- Time-boxed.
- Reasoned.
- Logged.
- Approved by Faiz when feasible.
- Limited to necessary key/material scope.
- Followed by post-use rotation of affected credentials.
- Followed by markdown review and evidence.

### 16.4 Python Runtime and Zeroization

Python cannot guarantee perfect zeroization of immutable strings/bytes or garbage-collected objects. Guinevere must mitigate this by:

- Minimizing plaintext lifetime.
- Avoiding plaintext logs/exceptions.
- Loading only required key scopes.
- Isolating process permissions.
- Using short-lived worker processes for high-risk batch decrypt/reencrypt tasks.
- Clearing references best-effort.
- Treating swap/core dumps/debug traces as sensitive.

---

## 17. Audit Logging Standard

### 17.1 Key Usage Events

Key usage logs must store:

- Timestamp.
- Actor/service.
- Operation: encrypt, decrypt, wrap, unwrap, rotate, rewrap, export, backup, restore, break-glass, revoke.
- Data domain.
- Classification.
- key_id.
- key_version.
- Result: success/failure.
- Error category if failure.
- Purpose.
- Correlation ID.
- Evidence path when applicable.

Key usage logs must not store:

- Plaintext key material.
- Plaintext DEKs.
- Plaintext secrets.
- Raw intimate content.
- Raw safe-word/crisis payloads.
- Raw surveillance evidence when hash/summary is enough.

### 17.2 Mandatory Audit Triggers

Audit events are mandatory for:

- Every Restricted/Critical decrypt.
- Every Critical encrypt.
- Every key rotation.
- Every key unwrap for a Critical record.
- Every break-glass access.
- Every export/dossier creation/access/deletion.
- Every backup restore.
- Every secret access outside normal startup flow.
- Every redaction failure.
- Every safe-mode sensitive access attempt.
- Every incident containment/recovery step.

---

## 18. Breach and Key-Compromise Response

### 18.1 Severity Matrix

| Severity | Crypto/Data Trigger | Required Response |
|---|---|---|
| SEV0 | Active Critical key compromise, nonce reuse, public Critical secret exposure, active exfiltration. | Immediate containment, revoke/disable, pause affected flows, notify Faiz, incident report, re-encrypt/rewrap. |
| SEV1 | Restricted/Critical unauthorized decrypt, backup key exposure, GitHub PAT leak, raw surveillance export mistake. | Contain, rotate, assess impact, preserve evidence, postmortem. |
| SEV2 | Confidential secret exposure, failed redaction in internal report, suspicious decrypt spike. | Rotate affected secret, scan artifacts, add regression test. |
| SEV3 | Internal key metadata inconsistency, overdue rotation without exposure. | Correct inventory, complete rotation, document. |
| SEV4 | Cosmetic metadata/reporting issue without exposure. | Fix during next maintenance window. |

### 18.2 Containment Requirements

Containment must include:

- Isolate affected service.
- Revoke or disable affected key/secret.
- Freeze affected exports and non-essential decrypts.
- Preserve minimal evidence with hashes.
- Remove leaked secret from non-authoritative stores.
- Open incident markdown report.
- Notify Faiz.

### 18.3 Re-Encryption Requirements

Re-encryption must include:

- Scope records/objects affected by key version.
- Generate replacement key.
- Rewrap DEKs or re-encrypt payloads.
- Verify counts and sample decrypts.
- Verify ciphertext hashes where applicable.
- Mark old key compromised/retired.
- Update inventory and evidence.
- Run regression tests.

---

## 19. Implementation Requirements

Before production runtime claim, Guinevere must have:

1. Crypto service module with typed APIs and audit hooks.
2. Key inventory file/table.
3. Secret inventory file/table.
4. SOPS encrypted secrets with no plaintext copy in repo.
5. age key permissions verified.
6. Runtime decrypted env cleanup verified.
7. AES-256-GCM envelope encryption for new Restricted/Critical paths.
8. Fernet compatibility ring documented if existing Fernet fields remain.
9. Key metadata schema implemented for encrypted records/objects.
10. Rotation evidence workflow.
11. Backup encryption and restore reconciliation tests.
12. Secret scanner over logs, evidence, docs, and sub-agent reports.
13. Safe-mode decrypt restriction hook.
14. Break-glass evidence workflow.
15. Incident report template for key compromise.
16. Test vectors for encryption/decryption/tamper/rotation.

---

## 20. Validation and Test Requirements

| Test ID | Category | Requirement |
|---|---|---|
| EKMS-001 | AES-GCM roundtrip | Encrypt/decrypt succeeds with correct key, nonce, and AAD. |
| EKMS-002 | Tamper detection | Modified ciphertext/tag/AAD fails closed. |
| EKMS-003 | Wrong key failure | Wrong key fails without leaking plaintext. |
| EKMS-004 | Nonce uniqueness | Batch encryption validates no nonce reuse under same key. |
| EKMS-005 | Metadata validation | Missing key_id/key_version/algorithm fails closed. |
| EKMS-006 | Envelope unwrap | Wrapped DEK decrypts only with correct KEK and AAD. |
| EKMS-007 | Rotation read-old/write-new | Old ciphertext readable during rotation; new writes use new key. |
| EKMS-008 | Re-encryption count | Re-encrypt job verifies all target records processed. |
| EKMS-009 | Fernet compatibility | Existing Fernet fields decrypt via versioned compatibility ring. |
| EKMS-010 | SOPS runtime | Decrypted env exists only runtime, 0600, cleaned after load. |
| EKMS-011 | Secret redaction | Logs/evidence/sub-agent reports contain no plaintext secrets. |
| EKMS-012 | Safe-mode restriction | Safe-word/distress state blocks non-essential Critical decrypt. |
| EKMS-013 | Backup decrypt/restore | Backup decrypts in recovery test and deletion ledger reconciles. |
| EKMS-014 | Break-glass | Break-glass requires reason, time box, evidence, and post-use rotation. |
| EKMS-015 | Incident drill | Key compromise drill completes containment, rotation, evidence, and postmortem. |

---

## 21. Review Cadence

| Review Type | Frequency | Owner | Output |
|---|---|---|---|
| Secret inventory review | Monthly | Guinevere + Faiz | Markdown review report. |
| Key inventory review | Monthly | Guinevere | Rotation due list. |
| SOPS recipient review | Annual or trigger-based | Faiz + Guinevere | Recipient update evidence. |
| Critical domain key review | Quarterly | Guinevere | Rotation/evidence report. |
| Backup recovery test | Quarterly lightweight; annual full | Guinevere + Faiz if needed | Restore evidence. |
| Breach tabletop | Quarterly for high-risk | Guinevere | Drill report. |
| Full standard review | Monthly or after incident | Faiz + Guinevere | Policy update or ADR backlog item. |

---

## 22. Unresolved Assumptions and Backlog

| Item | Status | Required Follow-up | Target Document |
|---|---|---|---|
| Detailed RBAC/ABAC for key and secret access | Backlog | Define per-service, sub-agent, action-level permissions. | Access Control RBAC/ABAC Matrix |
| Full secrets rotation runbook | Backlog | Convert this standard's rotation rules into executable procedures. | Secrets Rotation Runbook |
| Break-glass and recovery package procedure | Backlog | Define package creation, storage, restore, custody, and test procedure. | Key Recovery & Break-Glass Runbook |
| Formal incident response playbook | Backlog | Expand SEV0-SEV4 into full incident lifecycle. | Incident Response & Postmortem Runbook |
| Crypto service API implementation | Backlog | Implement typed crypto service module and tests. | Implementation Spec / Code |
| Database migration for encryption metadata | Backlog | Add key_id/key_version/algorithm/rotation columns or sidecar registry. | Database ERD & Migration Strategy |
| Redis at-rest encryption constraints | Backlog | Validate host/disk/container encryption and TTL controls. | Runtime Security Hardening Spec |
| Threat model schedule | Backlog | Create periodic cryptographic threat-model review. | Security Architecture & Threat Model |

---

# Appendix A — Key Hierarchy Matrix

| Key ID Pattern | Domain | Classification | Wrapped By | Rotation |
|---|---|---|---|---|
| `gkv1-sops-age-primary` | SOPS age identity | Critical | Offline recovery package | Annual/triggered recipient review. |
| `gkv1-kek-secrets-*` | Secrets | Critical | Faiz Recovery Root / SOPS | Quarterly/high-risk. |
| `gkv1-kek-profile-*` | Faiz profile | Restricted/Critical | Root KEK | Quarterly for Critical. |
| `gkv1-kek-safe-word-*` | Safe-word/distress | Critical | Root KEK | Quarterly/immediate on incident. |
| `gkv1-kek-journal-*` | Inner journal | Critical | Root KEK | Quarterly. |
| `gkv1-kek-surveillance-*` | Surveillance | Restricted/Critical | Root KEK | Quarterly for raw Critical. |
| `gkv1-kek-financial-*` | Financial | Restricted/Critical | Root KEK | Quarterly/annual based on scope. |
| `gkv1-kek-client-*` | Client data | Restricted/Critical | Root KEK | Annual/incident. |
| `gkv1-kek-backup-*` | Backups | Restricted/Critical | Recovery root | Annual/incident. |
| `gkv1-kek-export-*` | Exports/dossiers | Highest source class | Root KEK | Per package/expiry. |
| `gkv1-kek-audit-*` | Audit/evidence | Confidential/Critical | Root KEK | Annual/incident. |

---

# Appendix B — Secret Inventory Template

| secret_id | domain | classification | owner | runtime_consumer | storage_location | scope | rotated_at | rotation_due_at | revocation_procedure | evidence_path |
|---|---|---|---|---|---|---|---|---|---|---|
| `sec-9router-primary` | LLM | Critical | Faiz | guinevere-core | SOPS | 9Router API calls | TBD | TBD | Provider dashboard revoke + SOPS update | TBD |
| `sec-discord-bot` | Discord | Critical | Faiz | guinevere-core | SOPS | Discord bot auth | TBD | TBD | Discord developer portal reset | TBD |
| `sec-github-pat` | GitHub | Critical | Faiz | guinevere-core / MCP | SOPS | Fine-grained repo access | TBD | TBD | GitHub token revoke | TBD |
| `sec-postgres-core` | DB | Critical | Faiz | guinevere-core | SOPS | DB role password | TBD | TBD | ALTER ROLE + PgBouncer reload | TBD |
| `sec-r2-backup` | Object storage | Critical | Faiz | backup job | SOPS | R2 backup prefix | TBD | TBD | Cloudflare key revoke | TBD |
| `sec-device-android-hmac` | Device | Critical | Faiz | surveillance receiver | SOPS + device config | Tasker payload signing | TBD | TBD | Reissue device secret | TBD |

---

# Appendix C — Rotation Checklist

- [ ] Open rotation evidence markdown.
- [ ] Identify key/secret ID and affected domain.
- [ ] Confirm classification and incident/non-incident reason.
- [ ] Generate new key/secret.
- [ ] Store new material in approved storage only.
- [ ] Deploy write-new/read-old configuration.
- [ ] Rewrap or re-encrypt affected data.
- [ ] Verify counts and decrypt samples.
- [ ] Run service health checks.
- [ ] Mark old key read-only, retired, or compromised.
- [ ] Remove old runtime access.
- [ ] Update key/secret inventory.
- [ ] Add evidence path.
- [ ] Run regression tests.
- [ ] Notify Faiz when required.

---

# Appendix D — Key-Compromise Incident Checklist

- [ ] Declare severity.
- [ ] Identify compromised key/secret and scope.
- [ ] Freeze affected exports and non-essential decrypts.
- [ ] Revoke/disable key or provider secret.
- [ ] Preserve minimal evidence with hashes.
- [ ] Generate replacement key/secret.
- [ ] Rewrap/re-encrypt affected data.
- [ ] Verify integrity and record counts.
- [ ] Rotate dependent credentials if blast radius uncertain.
- [ ] Scan logs/evidence/docs for plaintext leakage.
- [ ] Update inventory and status.
- [ ] Add regression test.
- [ ] Write postmortem.
- [ ] Review threat model.

---

# Appendix E — Audit Checklist

| Check | Pass Criteria |
|---|---|
| No plaintext secrets | Grep/secret scanner over docs, code, logs, evidence returns zero real secrets. |
| Key metadata complete | Encrypted records include required metadata. |
| AES-GCM AAD present | AAD binds domain/classification/record/purpose/key version. |
| SOPS file valid | `sops -d` succeeds only on authorized host/user. |
| age key permissions | `/home/guinevere/.age/key.txt` is 0600 and owner-only. |
| Runtime env cleanup | Decrypted env is temporary and cleaned after load. |
| Rotation evidence | Every rotation has markdown evidence and inventory update. |
| Break-glass evidence | Every break-glass has reason, time box, and post-use rotation. |
| Backup restore | Restore test proves decryption and deletion-ledger reconciliation. |
| Safe-mode restriction | Safe-word/distress blocks non-essential Critical decrypt. |

---

# Appendix F — Approval and Review Record

## Review Record

- Reviewer: Faiz (Owner)
- Review Date: 2026-05-30
- Decision: Accepted
- Notes: Approved as normative child of ADR-008/ADR-018/ADR-015. AES-256-GCM is the primary new application-level encryption profile; ChaCha20-Poly1305 is fallback; Fernet remains compatibility/transitional only. Detailed executable rotation and recovery procedures are deferred to follow-up runbooks.

## Next Recommended Document

Guinevere recommends creating **Secrets Rotation Runbook** next.

Reason: this standard defines the mandatory cryptographic controls, but operational safety depends on executable step-by-step rotation procedures for SOPS age recipients, GitHub PAT, Discord token, 9Router key, DB passwords, R2/idcloudhost keys, Fernet compatibility rings, domain KEKs, backup keys, and break-glass credentials.
