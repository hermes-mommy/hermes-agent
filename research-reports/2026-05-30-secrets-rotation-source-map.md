# Secrets Rotation Source Map

**Report ID:** 2026-05-30-secrets-rotation-source-map  
**Date:** 2026-05-30  
**Scope:** Requirements extraction for the Guinevere Secrets Rotation Runbook from foundation documents.  
**Status:** Complete  

---

## Related Documents

| Document | Relationship |
|---|---|
| `Guinevere_EncryptionKeyManagementStandard_v1.0.md` | Primary source for all rotation controls, key hierarchy, audit requirements, and break-glass procedures. |
| `adr/ADR-015-secrets-management-strategy.md` | Parent ADR accepting SOPS + age with runtime injection; defines baseline secret storage and plaintext prohibition. |
| `adr/ADR-008-memory-encryption-key-management.md` | Parent ADR for memory encryption, key hierarchy, rotation, emergency revoke, and separated key domains. |
| `adr/ADR-019-access-control-vpn-mesh-strategy.md` | Parent ADR defining Tailscale mesh, zero public ports, and access boundaries that constrain secret exposure paths. |
| `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` | Defines classification tiers (Public/Internal/Confidential/Restricted/Critical) that drive rotation cadences and audit levels. |
| `Guinevere_TechnicalArchitecture_v2.0.md` | Defines runtime topology, SOPS key path, PostgreSQL, Redis, object storage, backups, services, and decrypt paths. |
| `Guinevere_APIIntegration_v2.0.md` | Defines external API secrets, Fernet usage, and provider credentials that must be inventoried and rotated. |

---

## 1. Authority

### 1.1 Canonical Authority Chain

The Secrets Rotation Runbook is a normative child document derived from the following authority stack, in descending priority:

1. **Platform/system safety and security requirements** — highest priority; no operational convenience overrides cryptographic integrity.
2. **Accepted ADRs:**
   - ADR-008 (Memory Encryption & Key Management)
   - ADR-015 (Secrets Management Strategy)
   - ADR-019 (Access Control & VPN Mesh Strategy)
3. **Guinevere_DataGovernance_ClassificationPolicy_v1.0.md** — classification tiers, retention, incident categories, audit requirements.
4. **Guinevere_PersonaSafetyPolicy_v1.0.md** — safe-word hard stop, distress/safe-mode boundaries, non-punitive safety logs.
5. **Guinevere_EncryptionKeyManagementStandard_v1.0.md** — specific cryptographic controls, rotation cadences, key hierarchy, audit standards.
6. **Guinevere_TechnicalArchitecture_v2.0.md** — runtime topology, SOPS key path, service boundaries.
7. **Guinevere_APIIntegration_v2.0.md** — external API credentials, Fernet compatibility, provider keys.

### 1.2 Conflict Resolution Rule

If any lower-layer document conflicts with a higher-layer document, the higher layer wins. The runbook must not silently resolve conflicts; it must document the conflict and route it to the ADR/Decisions Log if resolution is unclear.

### 1.3 Owner and Custodian Model

| Material | Custodian | Runtime Access |
|---|---|---|
| Samm Recovery Root | Samm | No normal runtime access. |
| Offline recovery package | Samm | No normal runtime access. |
| SOPS age identity | Runtime host under strict permissions | Required for startup secret decrypt. |
| Domain KEKs | Guinevere crypto service | Runtime-only, scoped by domain. |
| Provider secrets | Owning service only | Scoped environment injection. |
| Break-glass credentials | Samm approval required | Time-boxed, logged, post-use rotation mandatory. |

---

## 2. SOPS Workflow Requirements

### 2.1 SOPS Scope

SOPS + age must protect the following secret classes (from Encryption Standard Section 10.1):

- 9Router/OpenAI-compatible provider keys
- Discord bot token
- GitHub PAT and webhook secrets
- Database passwords (PostgreSQL per-service)
- Redis password
- R2/idcloudhost credentials
- Gmail OAuth client/refresh tokens
- Resend API key
- Gotify token
- Device HMAC secrets (Tasker/Windows)
- Fernet compatibility key rings
- Domain KEK wrapped material or metadata when applicable
- Runtime service credentials

### 2.2 File Naming and Storage

Accepted secret file patterns (from Encryption Standard Section 10.2):

- `/home/guinevere/config/.env.sops.yaml`
- `/home/guinevere/config/secrets.production.sops.yaml`
- `/home/guinevere/config/secrets.staging.sops.yaml`
- Repository copy: encrypted SOPS files only.

Plaintext variants must not be committed, attached to reports, pasted into chat, or stored in evidence.

### 2.3 Runtime Decryption Requirements

Runtime SOPS decryption must satisfy (from Encryption Standard Section 10.4):

- Decrypt to tmpfs or equivalent runtime-only path.
- If `/tmp/.env` is used, it must have `0600` permissions and must be auto-cleaned after service load.
- Decrypted environment files must not be backed up.
- Decrypted environment files must not be read by sub-agents, evidence tooling, markdown generation, or logs.
- Startup failure must fail closed if secrets cannot be decrypted.

### 2.4 SOPS Rotation Workflow Steps

The runbook must define executable steps for:

1. Generate new age recipient or re-encrypt with existing age identity.
2. Update SOPS file with new encrypted values.
3. Verify `sops -d` succeeds on authorized host only.
4. Update age key rotation record in inventory.
5. Verify old key material is unrecoverable from runtime.
6. Update `rotation_due_at` and `evidence_path` in inventory.
7. Notify Samm when required.

---

## 3. age Key Requirements

### 3.1 age Identity Controls

The age private key at `/home/guinevere/.age/key.txt` must satisfy (from Encryption Standard Section 10.3):

- **Owner:** `guinevere` runtime user or Samm-controlled admin account as approved.
- **Permissions:** `0600`.
- **Parent directory permissions:** no group/world write.
- **Access path:** Tailscale-only host access.
- **Backup:** excluded from ordinary plaintext backups.
- **Recovery:** present only inside Samm-controlled encrypted offline recovery package.
- **Rotation:** annual recipient review and immediate rotation on device loss, suspected compromise, custody change, or host compromise.

### 3.2 age Key Rotation Triggers

Immediate rotation is required when:

- Device loss occurs.
- Host compromise is suspected.
- Operator/custody change happens.
- age private key file permissions are violated.
- Tailscale mesh is compromised.
- Recovery package is exposed.

### 3.3 age Key Recovery Path

The runbook must define:

- Recovery package creation procedure (Samm-controlled, encrypted, separate from VPS).
- Recovery package contents manifest and checksum.
- Recovery package expiry/review date.
- Restore procedure for age key from recovery package.
- Verification that recovered key matches expected recipient fingerprint.

---

## 4. Secret Inventory Requirements

### 4.1 Mandatory Inventory Fields

Every secret must have an inventory entry (from Encryption Standard Section 14):

| Field | Requirement |
|---|---|
| `secret_id` | Stable identifier. |
| `name` | Human-readable name. |
| `domain` | LLM, Discord, GitHub, DB, Redis, storage, email, device, crypto, etc. |
| `classification` | Critical unless explicitly downgraded with reason. |
| `owner` | Samm or service owner. |
| `runtime_consumer` | Service/process allowed to read it. |
| `storage_location` | SOPS file, recovery package, runtime env, external provider. |
| `scope` | Exact permission scope. |
| `created_at` | Creation timestamp. |
| `rotated_at` | Last rotation timestamp. |
| `rotation_due_at` | Next rotation deadline. |
| `revocation_procedure` | Provider/API steps. |
| `incident_contact` | Samm / Guinevere runtime route. |
| `evidence_path` | Markdown evidence for creation/rotation/revocation. |

### 4.2 Required Secret Classes

The inventory must cover at minimum (from Encryption Standard Section 14.1):

- 9Router provider key
- Discord token
- GitHub PAT
- GitHub webhook secret
- PostgreSQL service passwords (per PgBouncer user)
- Redis password
- R2/idcloudhost keys
- Gmail OAuth credentials
- Resend API key
- Gotify token
- Tasker/Windows device HMAC secrets
- Sentry DSN/token if secret-bearing
- Fernet compatibility keys
- Domain KEKs and backup/export key metadata

### 4.3 Inventory Maintenance

- Secret inventory must be reviewed monthly (from Encryption Standard Section 21).
- Each rotation must update `rotated_at`, `rotation_due_at`, and `evidence_path`.
- The inventory must be stored in a format that does not expose plaintext secrets (SOPS-encrypted or database table with app-level encryption).

---

## 5. Classification Requirements

### 5.1 Classification Tiers

From Data Governance Policy Section 4.1:

| Tier | Label | Definition | Minimum Handling |
|---|---|---|---|
| 0 | Public | Approved for public disclosure. | Explicit approval required; no private data. |
| 1 | Internal | Operational data with low sensitivity inside the private system. | Access controlled; no public exposure. |
| 2 | Confidential | Personal/project/system context that could expose private preferences, plans, or internal behavior. | Encrypted at rest; access logged when practical. |
| 3 | Restricted | Sensitive personal, surveillance, financial, client, or behavioral data with material privacy/security impact. | Strong encryption; least privilege; access logging; retention controls. |
| 4 | Critical | Intimate, safe-word, crisis, credential, raw high-risk surveillance, inner journal, secret, or severe-impact data. | App/field-level encryption where possible; double encryption where defined; strict audit; minimized access; safe-mode restrictions. |

### 5.2 Default and Escalation Rules

- Unclassified data must default to `Confidential`.
- Highest classification wins for mixed-category records, prompts, exports, backups, logs, and derived summaries.
- Any value containing credentials, private keys, API tokens, decrypted secrets, safe-word data, crisis context, intimate data, or raw high-risk surveillance must be `Critical`.
- Classification must be stored as metadata beside the record or in an auditable classification registry.

### 5.3 Classification Impact on Rotation

| Classification | Rotation Cadence | Audit Level |
|---|---|---|
| Public | N/A | N/A |
| Internal | Annual service credential review | Operational logs |
| Confidential | Annual or risk-based | Access logged when practical |
| Restricted | Annual default; quarterly if high-risk | Restricted decrypt/access log required |
| Critical | Quarterly default; immediate on suspicion | Every decrypt, export, break-glass, rotation, and access event logged |

---

## 6. Rotation Cadences

### 6.1 Standard Rotation Cadence Matrix

From Encryption Standard Section 15.1:

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

### 6.2 Rotation Cadence by Secret

| Secret | Default Cadence | Trigger | Classification |
|---|---|---|---|
| 9Router API key | Quarterly | Exposure, provider alert, log leak | Critical |
| Discord bot token | Quarterly | Bot compromise, gateway anomaly, leaked logs | Critical |
| GitHub PAT | Quarterly or provider expiry | Repository exposure, scope change, suspicious event | Critical |
| GitHub webhook secret | Quarterly | Repository exposure, scope change | Critical |
| PostgreSQL core password | Quarterly | Service compromise, role change, log exposure | Critical |
| PostgreSQL PgBouncer user passwords | Quarterly | Service compromise, role change | Critical |
| Redis password | Quarterly | Unauthorized access, log exposure | Critical |
| R2 backup credentials | Quarterly | Object access anomaly, leaked env | Critical |
| idcloudhost S3 credentials | Quarterly | Bucket access anomaly, leaked env | Critical |
| Gmail OAuth client/refresh tokens | Quarterly | Token exposure, suspicious access | Critical |
| Resend API key | Quarterly | Exposure, provider alert, log leak | Critical |
| Gotify token | Quarterly | Exposure, log leak | Critical |
| Sentry DSN/token | Quarterly | Exposure, log leak | Confidential |
| Tasker/device HMAC secrets | Annual | Device loss, Tasker compromise, replay anomaly | Critical |
| Fernet compatibility keys | Quarterly or per-domain | Key scope violation, metadata invalid | Critical |
| Domain KEKs | Quarterly for Critical; annual for others | Incident, compromise, metadata invalid | Critical |
| Backup KEK | Annual | Recovery package exposure, backup compromise | Critical |
| Export KEK | Per package/expiry | Package exposure, export deletion | Critical |
| age private key | Annual | Device loss, host compromise, custody change | Critical |
| Break-glass credentials | After every use | Any activation | Critical |

---

## 7. Break-Glass Requirements

### 7.1 Break-Glass Controls

Break-glass access must satisfy (from Encryption Standard Section 16.3):

- Time-boxed.
- Reasoned.
- Logged.
- Approved by Samm when feasible.
- Limited to necessary key/material scope.
- Followed by post-use rotation of affected credentials.
- Followed by markdown review and evidence.

### 7.2 Break-Glass Activation Steps

The runbook must define:

1. Break-glass request with reason and time box.
2. Samm approval (when feasible).
3. Unlock offline recovery package or recovery auth key.
4. Decrypt necessary material.
5. Log break-glass event with actor, reason, time box, scope.
6. Use material for intended purpose only.
7. Return material to secure storage.
8. Rotate affected credentials immediately after use.
9. Write break-glass evidence markdown.
10. Review break-glass necessity and reduce future need.

### 7.3 Break-Glass Recovery Paths

From ADR-019 and Technical Architecture:

- VPS console (cloud provider) if VPN misconfiguration locks out access.
- Tailscale recovery auth key stored offline.
- DERP relay fallback (30-100 Mbps throttled).

---

## 8. Emergency Rotation Requirements

### 8.1 Emergency Rotation Flow

From Encryption Standard Section 15.3, emergency rotation must follow this sequence:

1. Declare incident severity (SEV0-SEV4).
2. Freeze affected exports and non-essential decrypts.
3. Revoke exposed key/secret where possible.
4. Preserve minimal evidence without plaintext secrets.
5. Generate replacement key/secret.
6. Rewrap/re-encrypt affected data.
7. Verify integrity.
8. Update key status to `compromised` and then `retired` when safe.
9. Add regression tests preventing recurrence.
10. Publish incident/postmortem markdown.

### 8.2 Severity Matrix for Cryptographic Incidents

From Encryption Standard Section 18.1:

| Severity | Crypto/Data Trigger | Required Response |
|---|---|---|
| SEV0 | Active Critical key compromise, nonce reuse, public Critical secret exposure, active exfiltration. | Immediate containment, revoke/disable, pause affected flows, notify Samm, incident report, re-encrypt/rewrap. |
| SEV1 | Restricted/Critical unauthorized decrypt, backup key exposure, GitHub PAT leak, raw surveillance export mistake. | Contain, rotate, assess impact, preserve evidence, postmortem. |
| SEV2 | Confidential secret exposure, failed redaction in internal report, suspicious decrypt spike. | Rotate affected secret, scan artifacts, add regression test. |
| SEV3 | Internal key metadata inconsistency, overdue rotation without exposure. | Correct inventory, complete rotation, document. |
| SEV4 | Cosmetic metadata/reporting issue without exposure. | Fix during next maintenance window. |

### 8.3 Containment Requirements

Containment must include (from Encryption Standard Section 18.2):

- Isolate affected service.
- Revoke or disable affected key/secret.
- Freeze affected exports and non-essential decrypts.
- Preserve minimal evidence with hashes.
- Remove leaked secret from non-authoritative stores.
- Open incident markdown report.
- Notify Samm.

### 8.4 Re-Encryption Requirements

Re-encryption must include (from Encryption Standard Section 18.3):

- Scope records/objects affected by key version.
- Generate replacement key.
- Rewrap DEKs or re-encrypt payloads.
- Verify counts and sample decrypts.
- Verify ciphertext hashes where applicable.
- Mark old key compromised/retired.
- Update inventory and evidence.
- Run regression tests.

---

## 9. Zero-Downtime Rotation Requirements

### 9.1 Zero-Downtime Rotation Flow

From Encryption Standard Section 15.2, rotation must follow this sequence:

1. Open markdown rotation evidence file.
2. Create new key or provider secret.
3. Mark old key `read_only` where applicable.
4. Configure runtime to write with new key and read with old+new.
5. Rewrap or re-encrypt affected records/objects.
6. Verify record counts, ciphertext hashes, sample decrypts, and application health.
7. Mark old key `retired` or `compromised`.
8. Remove old runtime access after verification.
9. Update inventory, `rotation_due_at`, and evidence path.
10. Run regression tests.

### 9.2 Zero-Downtime Constraints

- Rotation must not break historical reads or corrupt memory (from Encryption Standard Section 4.6: "Read-old/write-new rotation is mandatory").
- Service must continue operating during rotation; no planned downtime for routine quarterly rotations.
- For database credentials: rotate PgBouncer user passwords without dropping active connections; use connection pool draining.
- For SOPS secrets: update SOPS file, redeploy with new decrypted env; service restart must be atomic or blue-green.
- For Fernet keys: use staged key-ring deployment (new primary, read old, re-encrypt, verify, retire old).
- For domain KEKs: support dual-key read during rotation window; old key marked `read_only`, new key marked `active`.

---

## 10. Audit and Evidence Requirements

### 10.1 Key Usage Events

Key usage logs must store (from Encryption Standard Section 17.1):

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

### 10.2 Mandatory Audit Triggers

Audit events are mandatory for (from Encryption Standard Section 17.2):

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

### 10.3 Evidence File Requirements

Every rotation, break-glass, incident, and recovery must produce a markdown evidence file with:

- Date and time.
- Actor/service performing the action.
- Key/secret ID and affected domain.
- Classification.
- Reason (scheduled, incident, break-glass, compromise).
- Steps performed.
- Verification results (counts, hashes, sample decrypts, health checks).
- Old key status transition (read_only -> retired/compromised).
- New key status.
- Inventory update confirmation.
- Regression test results.
- Samm notification confirmation (when required).

---

## 11. Constraints and Conflicts

### 11.1 Known Canonicalization Hotspots

These conflicts are documented in the AGENTS.md Guinevester operating contract and must be resolved through ADR/Decisions Log before the runbook can be considered fully canonical:

| Conflict Area | Current State | Required Resolution |
|---|---|---|
| SQLite vs PostgreSQL/Redis memory storage | ADR-008/Technical Architecture v2.0 resolve to PostgreSQL + Redis, no SQLite. | No conflict; resolved. Runbook must align with PostgreSQL + Redis. |
| 7-phase vs 8-phase SDLC loop | ADR-015 and Technical Architecture v2.0 specify exactly 7 phases. | No conflict; resolved. Runbook must align with 7-phase loop. |
| OpenCode replacement vs optional turbo mode | Guinevere MCP native fully replaces OpenCode; Guinevere MCP native is optional turbo mode per Technical Architecture. | Clarify whether Guinevere MCP native is primary or optional. Runbook should not depend on OpenCode tooling. |
| Fernet as default vs compatibility | Encryption Standard says Fernet is compatibility/transitional only; new Restricted/Critical paths must use AES-256-GCM. | No conflict; resolved. Runbook must not create new Fernet-dependent rotation paths. |
| Wearable active vs future status | Technical Architecture v2.0 lists Mi Fitness API as Future/post-MVP. | No conflict; resolved. Runbook must not include wearable secrets in active rotation cadence. |
| Monitoring VPS vs primary VPS | Technical Architecture v2.0 says Prometheus + Grafana on primary VPS first; monitoring VPS post-MVP. | No conflict; resolved. Runbook must align with primary VPS first. |

### 11.2 Unresolved Items Requiring Follow-Up

From Encryption Standard Section 22 (Unresolved Assumptions and Backlog):

| Item | Status | Required Follow-up | Target Document |
|---|---|---|---|
| Detailed RBAC/ABAC for key and secret access | Backlog | Define per-service, sub-agent, action-level permissions. | Access Control RBAC/ABAC Matrix |
| Full secrets rotation runbook | Backlog | Convert this standard's rotation rules into executable procedures. | Secrets Rotation Runbook (this document) |
| Break-glass and recovery package procedure | Backlog | Define package creation, storage, restore, custody, and test procedure. | Key Recovery & Break-Glass Runbook |
| Formal incident response playbook | Backlog | Expand SEV0-SEV4 into full incident lifecycle. | Incident Response & Postmortem Runbook |
| Crypto service API implementation | Backlog | Implement typed crypto service module and tests. | Implementation Spec / Code |
| Database migration for encryption metadata | Backlog | Add key_id/key_version/algorithm/rotation columns or sidecar registry. | Database ERD & Migration Strategy |
| Redis at-rest encryption constraints | Backlog | Validate host/disk/container encryption and TTL controls. | Runtime Security Hardening Spec |
| Threat model schedule | Backlog | Create periodic cryptographic threat-model review. | Security Architecture & Threat Model |

### 11.3 Constraints from Foundation Documents

1. **Plaintext prohibition:** No plaintext secrets in code, docs, evidence, logs, or sub-agent reports (ADR-015, Encryption Standard Section 10.2).
2. **Zero public ports:** All VPS admin surfaces are Tailscale-internal only (ADR-019, Technical Architecture v2.0). Secret rotation must not expose secrets via public endpoints.
3. **Safe-mode restrictions:** Safe-word/distress state restricts sensitive recall, raw surveillance retrieval, and non-essential decrypts (Data Governance Policy Section 7.5, Encryption Standard Section 4.8).
4. **Python zeroization limitations:** Python cannot guarantee perfect zeroization of immutable strings/bytes or garbage-collected objects (Encryption Standard Section 16.4). Mitigation: minimize plaintext lifetime, avoid plaintext logs/exceptions, load only required key scopes.
5. **Backup encryption independence:** Backup/export keys must be separated from runtime data keys (Encryption Standard Section 4.10).
6. **Backup reconciliation:** Backups must maintain a durable deletion/do-not-recall ledger. On restore, deleted record markers, do-not-recall states, correction supersessions, retention expirations, and safe-mode restrictions must be reapplied (Data Governance Policy Section 6.4).
7. **Sub-agent redaction:** Sub-agents must receive redacted/minimized context by default; Critical data is denied by default unless task-justified (Data Governance Policy Section 7.3).
8. **No silent canonicalization:** If docs conflict on model, storage, services, schemas, or safety boundaries, record the conflict and route to ADR/Decisions Log (AGENTS.md Section 3).

---

## 12. Validation Requirements

### 12.1 Test Requirements from Foundation Docs

From Encryption Standard Section 20:

| Test ID | Category | Requirement |
|---|---|---|
| EKMS-007 | Rotation read-old/write-new | Old ciphertext readable during rotation; new writes use new key. |
| EKMS-008 | Re-encryption count | Re-encrypt job verifies all target records processed. |
| EKMS-009 | Fernet compatibility | Existing Fernet fields decrypt via versioned compatibility ring. |
| EKMS-010 | SOPS runtime | Decrypted env exists only runtime, 0600, cleaned after load. |
| EKMS-011 | Secret redaction | Logs/evidence/sub-agent reports contain no plaintext secrets. |
| EKMS-013 | Backup decrypt/restore | Backup decrypts in recovery test and deletion ledger reconciles. |
| EKMS-014 | Break-glass | Break-glass requires reason, time box, evidence, and post-use rotation. |
| EKMS-015 | Incident drill | Key compromise drill completes containment, rotation, evidence, and postmortem. |

### 12.2 Data Governance Test Requirements

From Data Governance Policy Section 13:

| Test ID | Control Area | Required Test |
|---|---|---|
| DG-007 | Secret leakage | Secret in log/prompt triggers incident and rotation workflow. |
| DG-008 | Export encryption | Restricted/Critical export is encrypted and logged. |
| DG-009 | Delete-on-restore | Restored backup reapplies deletion/do-not-recall ledger before exposure. |

---

## 13. Checklist for Runbook Authoring

Before the Secrets Rotation Runbook is finalized, the following must be true:

- [ ] All secret types from Section 4.2 have inventory entries with complete fields.
- [ ] Rotation cadences match Section 6.2 exactly.
- [ ] Zero-downtime flow matches Section 9.1 sequence.
- [ ] Emergency rotation flow matches Section 8.1 sequence.
- [ ] Break-glass procedure matches Section 7.2 steps.
- [ ] Audit triggers match Section 10.2 mandatory list.
- [ ] Evidence file requirements match Section 10.3.
- [ ] All constraints from Section 11.3 are addressed.
- [ ] All unresolved items from Section 11.2 are either resolved or documented as deferred.
- [ ] No plaintext secrets appear in the runbook or its evidence files.
- [ ] Cross-references to parent documents (ADR-008, ADR-015, ADR-019, Encryption Standard, Data Governance Policy) are present and accurate.

---

*Report generated: 2026-05-30 | Guinevere de Baroque — autonomous system steward*
