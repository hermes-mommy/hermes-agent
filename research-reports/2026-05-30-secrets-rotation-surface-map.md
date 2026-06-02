# Secrets Rotation Surface Map

**Report ID:** 2026-05-30-secrets-rotation-surface-map  
**Date:** 2026-05-30  
**Scope:** Complete mapping of all secret surfaces in Project Guinevere for rotation planning.  
**Status:** Complete  

---

## Related Documents

| Document | Relationship |
|---|---|
| `Guinevere_EncryptionKeyManagementStandard_v1.0.md` | Primary source for secret inventory fields, classification requirements, and rotation controls. |
| `adr/ADR-015-secrets-management-strategy.md` | Defines SOPS + age baseline and runtime injection pattern. |
| `adr/ADR-008-memory-encryption-key-management.md` | Defines key hierarchy, domain separation, and rotation triggers. |
| `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` | Defines classification tiers that determine rotation cadences and audit levels. |
| `Guinevere_TechnicalArchitecture_v2.0.md` | Defines runtime topology, service boundaries, backup paths, and SOPS key path. |
| `Guinevere_APIIntegration_v2.0.md` | Defines external API credentials and provider integrations. |

---

## 1. Secret Inventory Surface Map

The following table maps every secret/surface in Project Guinevere to its provider, owner, consumer service, storage location, classification, rotation method, validation evidence, revoke path, rollback concern, and blast radius.

---

### 1.1 LLM Provider Secrets

| secret_id | name | provider | owner | runtime_consumer | storage_location | classification | rotation_method | validation_evidence | revoke_path | rollback_concern | blast_radius |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `sec-9router-primary` | 9Router API key | 9Router (OpenAI-compatible) | Samm | guinevere-core | SOPS: `/home/guinevere/config/.env.sops.yaml` | Critical | Quarterly or on exposure/provider alert | LLM call success after rotation; 9Router dashboard key status | 9Router dashboard revoke + SOPS update | Service restart required; queued prompts may fail | Core persona + reasoning down; sub-agents queue for retry |
| `sec-9router-fallback` | 9Router fallback key | 9Router | Samm | guinevere-core | SOPS | Critical | Quarterly or on exposure | Fallback LLM call test after rotation | 9Router dashboard revoke + SOPS update | Same as primary | Sub-agent cost escalation if fallback activates |

---

### 1.2 Communication Service Secrets

| secret_id | name | provider | owner | runtime_consumer | storage_location | classification | rotation_method | validation_evidence | revoke_path | rollback_concern | blast_radius |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `sec-discord-bot` | Discord bot token | Discord Developer Portal | Samm | guinevere-core | SOPS | Critical | Quarterly or on bot compromise/gateway anomaly | Discord gateway connection test; slash command response | Discord developer portal bot reset + SOPS update | Discord UI layer down; Samm loses primary interface | Full system inaccessible via Discord; surveillance notifs fail |
| `sec-github-pat` | GitHub PAT | GitHub | Samm | guinevere-core / MCP | SOPS | Critical | Quarterly or provider expiry; immediate on repository exposure | GitHub API call; MCP git operation test | GitHub token revoke in settings + SOPS update | CI/CD pipeline fails; self-deploy stops | Code operations blocked; evidence/reporting halted |
| `sec-github-webhook` | GitHub webhook secret | GitHub | Samm | guinevere-core | SOPS | Critical | Quarterly or on repository exposure | Webhook payload signature verification test | GitHub webhook secret rotation + SOPS update | Missed webhook events until secret updated | Real-time event processing delayed |
| `sec-gmail-oauth` | Gmail OAuth client/refresh tokens | Google Cloud Console | Samm | guinevere-core | SOPS | Critical | Quarterly or on token exposure | Gmail API send/receive test | Google Cloud Console token revoke + SOPS update + re-auth | Client email + transactional email down | Client communication fails; invoice delivery blocked |
| `sec-resend-api` | Resend API key | Resend | Samm | guinevere-core | SOPS | Critical | Quarterly or on exposure | Resend API test send | Resend dashboard key revoke + SOPS update | Transactional email (invoice) down | Invoice delivery fails |
| `sec-gotify-token` | Gotify token | Gotify (self-hosted/external) | Samm | guinevere-core | SOPS | Critical | Quarterly or on exposure | Gotify push notification test | Gotify server token revoke + SOPS update | Push notification backup down | HP notification fallback fails |

---

### 1.3 Database Secrets

| secret_id | name | provider | owner | runtime_consumer | storage_location | classification | rotation_method | validation_evidence | revoke_path | rollback_concern | blast_radius |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `sec-postgres-core` | PostgreSQL core service password | PostgreSQL | Samm | guinevere-core (PgBouncer) | SOPS | Critical | Quarterly or on service compromise | Connection test; query execution | ALTER ROLE guinevere_core PASSWORD 'new'; PgBouncer reload | Connection pool flush; active queries may fail | Core daemon cannot access memory/persona/behavior data |
| `sec-postgres-surveillance` | PostgreSQL surveillance user password | PostgreSQL | Samm | guinevere-surveillance (PgBouncer) | SOPS | Critical | Quarterly or on compromise | Surveillance INSERT test; TimescaleDB hypertable write | ALTER ROLE guinevere_surveillance PASSWORD 'new'; PgBouncer reload | Surveillance data buffer overflow; data loss | Surveillance receiver down; real-time activity tracking fails |
| `sec-postgres-financial` | PostgreSQL financial user password | PostgreSQL | Samm | guinevere-financial (PgBouncer) | SOPS | Critical | Quarterly or on compromise | Financial schema query test | ALTER ROLE guinevere_financial PASSWORD 'new'; PgBouncer reload | Financial tracking stops | Budget/invoice/transaction tracking fails |
| `sec-postgres-readonly` | PostgreSQL read-only user password | PostgreSQL | Samm | Grafana/reporting (PgBouncer) | SOPS | Critical | Quarterly or on compromise | Grafana dashboard query test | ALTER ROLE guinevere_readonly PASSWORD 'new'; PgBouncer reload | Reporting/monitoring dashboards fail | Observability gap; Samm cannot see metrics |
| `sec-postgres-admin` | PostgreSQL admin/superuser password | PostgreSQL | Samm | guinevere-admin (self-maintenance) | SOPS | Critical | Quarterly or on compromise | Maintenance operation test | ALTER ROLE guinevere_admin PASSWORD 'new'; direct connection | Self-maintenance blocked; backup/rotate operations fail | Autonomous recovery operations fail |
| `sec-redis-auth` | Redis password | Redis | Samm | All services | SOPS | Critical | Quarterly or on unauthorized access | Redis AUTH test; ping/pong | CONFIG SET requirepass 'new'; service restart | Connection pool flush; cache miss | Queue/cache/state loss; session state cleared |

---

### 1.4 Object Storage Secrets

| secret_id | name | provider | owner | runtime_consumer | storage_location | classification | rotation_method | validation_evidence | revoke_path | rollback_concern | blast_radius |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `sec-r2-backup` | Cloudflare R2 backup credentials | Cloudflare | Samm | backup job | SOPS | Critical | Quarterly or on object access anomaly | R2 upload/download test; bucket listing | Cloudflare dashboard key revoke + SOPS update | Backup upload fails; WAL streaming stops | PostgreSQL WAL backup halted; disaster recovery gap |
| `sec-r2-surveillance` | Cloudflare R2 surveillance credentials | Cloudflare | Samm | surveillance processor | SOPS | Critical | Quarterly or on access anomaly | R2 encrypted screenshot upload test | Cloudflare dashboard key revoke + SOPS update | Surveillance media upload stops | Raw surveillance evidence not archived |
| `sec-idcloudhost-s3` | idcloudhost S3 primary object storage credentials | idcloudhost | Samm | backup job / archival | SOPS | Critical | Quarterly or on bucket access anomaly | S3 upload/download test; lifecycle rule test | idcloudhost console key revoke + SOPS update | Cold storage upload fails | PostgreSQL cold backup (pg_dump) halted; archival stops |

---

### 1.5 Cryptographic Material

| secret_id | name | provider | owner | runtime_consumer | storage_location | classification | rotation_method | validation_evidence | revoke_path | rollback_concern | blast_radius |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `sec-fernet-compat` | Fernet compatibility key ring | Guinevere runtime | Samm | guinevere-core (legacy fields) | SOPS (key ring metadata) + runtime memory | Critical | Quarterly or per-domain on key scope violation | Legacy field decrypt test; MultiFernet ring validation | Remove key from ring; re-encrypt with new primary | Legacy field data unreadable until re-encrypted | Historical encrypted fields (financial/surveillance compat) unreadable |
| `sec-domain-kek-secrets` | Domain KEK for secrets | Guinevere crypto service | Samm | guinevere-core | Runtime-only (wrapped in SOPS/recovery package) | Critical | Quarterly or on incident | DEK wrap/unwrap test; key metadata validation | Rotate KEK; rewrap all domain DEKs | All provider credentials re-encryption required | All SOPS secrets + runtime env must be re-encrypted |
| `sec-domain-kek-profile` | Domain KEK for Samm profile | Guinevere crypto service | Samm | guinevere-core | Runtime-only | Critical | Quarterly (Critical domain) | Profile field encrypt/decrypt test | Rotate KEK; rewrap profile DEKs | Profile memory re-encryption | Samm intimate profile temporarily unreadable |
| `sec-domain-kek-safe-word` | Domain KEK for safe-word/distress | Guinevere crypto service | Samm | guinevere-core | Runtime-only | Critical | Quarterly or immediate on incident | Safe-word log encrypt/decrypt test | Rotate KEK; rewrap safe-word DEKs | Crisis context re-encryption | Safe-word logs temporarily unreadable |
| `sec-domain-kek-journal` | Domain KEK for inner journal | Guinevere crypto service | Samm | guinevere-core | Runtime-only | Critical | Quarterly | Journal entry encrypt/decrypt test | Rotate KEK; rewrap journal DEKs | Journal entries re-encryption | Inner journal temporarily unreadable |
| `sec-domain-kek-surveillance` | Domain KEK for surveillance | Guinevere crypto service | Samm | guinevere-core / surveillance | Runtime-only | Critical (raw) / Restricted (summaries) | Quarterly for raw Critical | Surveillance object encrypt/decrypt test | Rotate KEK; rewrap surveillance DEKs | Raw surveillance evidence re-encryption | Surveillance media temporarily unreadable |
| `sec-domain-kek-financial` | Domain KEK for financial | Guinevere crypto service | Samm | guinevere-financial | Runtime-only | Critical | Quarterly/annual based on scope | Financial record encrypt/decrypt test | Rotate KEK; rewrap financial DEKs | Financial records re-encryption | Financial tracking data temporarily unreadable |
| `sec-domain-kek-backup` | Domain KEK for backups | Guinevere crypto service | Samm | backup job | Runtime-only | Critical | Annual or on recovery package exposure | Backup decrypt test in recovery procedure | Rotate KEK; re-encrypt backup keys | Backup re-encryption required | Existing backups may need re-encryption |
| `sec-domain-kek-export` | Domain KEK for exports/dossiers | Guinevere crypto service | Samm | export process | Runtime-only | Critical | Per package/expiry | Export package decrypt test | Rotate KEK; re-encrypt active exports | Active export packages must be re-issued | Outstanding dossiers become unreadable |
| `sec-domain-kek-audit` | Domain KEK for audit/evidence | Guinevere crypto service | Samm | audit/evidence | Runtime-only | Critical | Annual or on incident | Audit artifact encrypt/decrypt test | Rotate KEK; rewrap audit DEKs | Historical audit evidence re-encryption | Incident evidence temporarily unreadable |
| `sec-age-private-key` | age private key for SOPS | age | Samm | Runtime host (guinevere user) | `/home/guinevere/.age/key.txt` (0600) | Critical | Annual or immediate on device loss/host compromise | SOPS decrypt test; `sops -d` succeeds on authorized host | Rotate age key pair; re-encrypt all SOPS files with new public key | All SOPS secrets must be re-encrypted | Entire secret inventory inaccessible until re-encrypted |
| `sec-samm-recovery-root` | Samm Recovery Root | Samm (offline) | Samm | Offline recovery only | Offline encrypted recovery package | Critical | On custody change or suspected compromise | Recovery package restore test | Generate new recovery root; re-wrap all KEKs | All domain KEKs must be re-wrapped | Full system recovery capability reset |

---

### 1.6 Device and Surveillance Secrets

| secret_id | name | provider | owner | runtime_consumer | storage_location | classification | rotation_method | validation_evidence | revoke_path | rollback_concern | blast_radius |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `sec-device-android-hmac` | Tasker/Android device HMAC secret | Guinevere runtime | Samm | surveillance receiver | SOPS + Tasker config | Critical | Annual or on device loss/Tasker compromise | Android payload signature verification test | Reissue device secret; update SOPS + Tasker config | Android surveillance data rejected until HMAC updated | Android surveillance receiver down; spoofed payload risk |
| `sec-device-windows-hmac` | Windows daemon HMAC secret | Guinevere runtime | Samm | guinevere-windows-sync | SOPS + Windows daemon config | Critical | Annual or on device loss/daemon compromise | Windows payload signature verification test | Reissue device secret; update SOPS + Windows config | Windows surveillance data rejected | Windows surveillance receiver down |
| `sec-tasker-config-backup` | Tasker config backup encryption key | Guinevere runtime | Samm | Tasker auto-backup | SOPS + GDrive + repo | Critical | Annual or on device loss | Tasker config restore test | Reissue backup encryption key | Historical Tasker configs unreadable | Android setup recovery delayed |

---

### 1.7 Monitoring and Error Tracking

| secret_id | name | provider | owner | runtime_consumer | storage_location | classification | rotation_method | validation_evidence | revoke_path | rollback_concern | blast_radius |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `sec-sentry-dsn` | Sentry DSN | Sentry | Samm | guinevere-core | SOPS | Confidential | Quarterly or on exposure | Sentry event send test | Sentry dashboard DSN revoke + SOPS update | Error tracking stops | Error visibility lost; debugging delayed |
| `sec-prometheus-auth` | Prometheus basic auth (if enabled) | Prometheus | Samm | metrics.internal | SOPS | Confidential | Quarterly or on exposure | Prometheus scrape test | Prometheus config auth update + service restart | Metrics collection may fail | Observability gap |
| `sec-grafana-auth` | Grafana admin auth | Grafana | Samm | grafana.internal | SOPS | Confidential | Quarterly or on exposure | Grafana login test | Grafana admin password reset + SOPS update | Dashboard access blocked | Samm cannot view metrics |

---

### 1.8 Runtime Environment and Decrypted Secrets

| secret_id | name | provider | owner | runtime_consumer | storage_location | classification | rotation_method | validation_evidence | revoke_path | rollback_concern | blast_radius |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `sec-runtime-decrypted-env` | Runtime decrypted environment variables | Multiple providers | Samm | All systemd services | `/tmp/.env` (tmpfs, 0600, auto-cleaned) | Critical | On SOPS update + service restart | Service startup success; `sops -d` validation | Service restart with new SOPS decryption | Brief service restart window | All services restart; brief downtime |
| `sec-sops-encrypted-files` | SOPS encrypted secret files | SOPS + age | Samm | guinevere-core (startup) | `/home/guinevere/config/.env.sops.yaml` (repo) | Critical | On age key rotation or secret change | `sops -d` succeeds; file integrity check | SOPS re-encrypt with new age public key | Git commit required; all hosts must have new age key | Secret decrypt failure on unauthorized hosts |

---

### 1.9 Backup and Recovery Secrets

| secret_id | name | provider | owner | runtime_consumer | storage_location | classification | rotation_method | validation_evidence | revoke_path | rollback_concern | blast_radius |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `sec-backup-encryption-key` | Backup encryption key | Guinevere crypto | Samm | backup job | Runtime-only + SOPS metadata | Critical | Annual or on recovery package exposure | Backup decrypt test; restore reconciliation test | Rotate backup KEK; re-encrypt new backups | Historical backups may need re-encryption | Historical backup restore may fail |
| `sec-recovery-package-key` | Recovery package encryption key | Samm (offline) | Samm | Recovery procedure only | Offline encrypted package | Critical | On custody change or suspected compromise | Recovery package decrypt test | Generate new recovery package | All recovery material must be re-wrapped | Recovery capability reset |
| `sec-break-glass-cred` | Break-glass credentials | Various | Samm | Emergency recovery | Offline recovery package | Critical | After every use | Break-glass access log review | Rotate immediately after use | Must be rotated immediately after activation | Compromised break-glass credential risk |

---

## 2. Secret Surface Storage Locations Summary

| Storage Location | Secrets Stored | Classification | Access Control | Backup Status |
|---|---|---|---|---|
| `/home/guinevere/config/.env.sops.yaml` | All provider API keys, DB passwords, Redis auth, object storage credentials, HMAC secrets, Sentry DSN | Critical | SOPS encrypted; repo private; age key 0600 | Committed to private repo (encrypted) |
| `/home/guinevere/.age/key.txt` | age private key for SOPS decrypt | Critical | 0600 permissions; owner-only; Tailscale-only host access | Excluded from plaintext backups; present only in offline recovery package |
| `/tmp/.env` (tmpfs) | Runtime-decrypted environment variables | Critical | 0600; auto-cleaned after service load; not backed up; not readable by sub-agents | Not backed up |
| Runtime process environment | Decrypted secrets injected as env vars | Critical | Process-scoped; not persisted | Not persisted |
| Offline recovery package | Samm Recovery Root, age key backup, break-glass credentials, domain KEK metadata | Critical | Samm-controlled; encrypted; stored separately from VPS | Not on VPS; tested periodically |
| External provider dashboards | 9Router, Discord, GitHub, Google Cloud, Resend, Gotify, Cloudflare, idcloudhost, Sentry secrets | Critical | Provider-managed; API-based revoke | Provider-dependent |
| PgBouncer config | PostgreSQL per-service passwords | Critical | PostgreSQL auth; PgBouncer pooling | In SOPS |
| Redis config | Redis password | Critical | Redis auth required | In SOPS |
| Tasker config (Android) | Device HMAC secret | Critical | Tasker private storage + SOPS | GDrive + repo + VPS backup |

---

## 3. Rotation Method Summary by Secret Type

| Secret Type | Rotation Method | Zero-Downtime Approach | Emergency Approach |
|---|---|---|---|
| 9Router API key | Generate new key in 9Router dashboard; update SOPS; restart service with new env | Blue-green service restart; queue retry during swap | Immediate revoke; generate new; service restart |
| Discord bot token | Regenerate in Discord Developer Portal; update SOPS; reconnect gateway | Reconnect with new token; Discord handles reconnection | Immediate token reset; bot goes offline until new token deployed |
| GitHub PAT | Generate new fine-grained PAT; update SOPS; verify MCP git operations | MCP retry on auth failure; fallback to cached token if available | Immediate revoke; new PAT generation; CI/CD pause until restored |
| PostgreSQL passwords | ALTER ROLE + new password; PgBouncer reload | Connection pool drain; new connections use new password | Immediate ALTER ROLE; force disconnect old connections |
| Redis password | CONFIG SET requirepass; service restart | Redis restart with new password; cache miss acceptable | Immediate password change; force disconnect |
| R2/S3 credentials | Generate new keys in provider dashboard; update SOPS; redeploy | Backup job retry on auth failure | Immediate key revoke; new key generation |
| Gmail OAuth | Revoke in Google Cloud; re-auth flow; update SOPS | Re-auth during next scheduled window | Immediate revoke; re-auth required |
| Fernet key ring | Add new key to ring; mark as primary; re-encrypt with new key | Read-old/write-new; staged key-ring deployment | Rotate compromised key to `compromised` status; re-encrypt affected fields |
| Domain KEK | Generate new KEK; rewrap all domain DEKs; dual-key read window | Old key `read_only`; new key `active`; verify decrypts; retire old | Immediate key compromise; freeze decrypts; rewrap all DEKs |
| age private key | Generate new age key pair; re-encrypt all SOPS files | Re-encrypt SOPS during maintenance window; deploy new age key | Immediate key compromise; re-encrypt all SOPS; update all hosts |
| Device HMAC | Reissue secret; update SOPS + device config | Deploy new HMAC to device; verify signature | Immediate reissue; reject old HMAC signatures |

---

## 4. Validation Evidence Requirements

Every rotation must produce validation evidence. Minimum evidence requirements by secret type:

| Secret Type | Minimum Evidence |
|---|---|
| API tokens (9Router, Discord, Resend, Gotify) | Successful API call after rotation; provider dashboard confirmation of old key revocation. |
| GitHub PAT | Successful MCP git operation; GitHub API call; CI/CD pipeline green. |
| Database passwords | Successful connection test; active query count after rotation; PgBouncer pool status. |
| Redis password | AUTH success; ping/pong; key TTL preservation. |
| Object storage keys | Upload/download test; bucket listing; lifecycle rule validation. |
| OAuth tokens | Token refresh test; API call success; re-auth flow completion. |
| Fernet keys | Legacy field decrypt test; MultiFernet ring validation; re-encryption count. |
| Domain KEKs | DEK wrap/unwrap test; sample record decrypt; record count verification; ciphertext hash match. |
| age key | SOPS decrypt test on authorized host; `sops -d` success; re-encrypted file integrity. |
| Device HMAC | Payload signature verification test; device config update confirmation. |
| Backup keys | Backup decrypt test; restore reconciliation test; deletion ledger re-application. |
| Break-glass credentials | Break-glass access log; reason record; time-box confirmation; post-use rotation evidence. |

---

## 5. Revoke Path Summary

| Secret Type | Revoke Path | Time to Revoke | Notes |
|---|---|---|---|
| 9Router API key | 9Router dashboard → API keys → Revoke | Immediate | New key generation required before SOPS update. |
| Discord bot token | Discord Developer Portal → Bot → Reset Token | Immediate | All gateway connections drop; automatic reconnect with new token. |
| GitHub PAT | GitHub Settings → Developer settings → Personal access tokens → Revoke | Immediate | Fine-grained tokens can be scoped to reduce blast radius. |
| GitHub webhook secret | GitHub repo → Settings → Webhooks → Update secret | Immediate | Existing webhooks continue; new payloads use new secret. |
| PostgreSQL passwords | `ALTER ROLE ... PASSWORD 'new'` + PgBouncer reload | Near-immediate | Connection pool flush; brief connection interruption. |
| Redis password | `CONFIG SET requirepass 'new'` + service restart | Near-immediate | All existing connections dropped. |
| R2/S3 credentials | Provider dashboard → API tokens → Revoke/Delete | Immediate | New key pair generation required. |
| Gmail OAuth | Google Cloud Console → OAuth consent screen → Revoke access | Immediate | Re-auth flow required for new tokens. |
| Resend API key | Resend dashboard → API Keys → Revoke | Immediate | New key generation required. |
| Gotify token | Gotify server admin → Tokens → Revoke | Immediate | New token generation required. |
| Sentry DSN | Sentry project → Settings → Client Keys → Regenerate | Immediate | New DSN required. |
| Fernet key | Remove from key ring or mark `compromised` | Immediate | Re-encrypt affected fields with new primary key. |
| Domain KEK | Rotate in crypto service; mark old key `compromised` | Near-immediate | Rewrap all domain DEKs; dual-key read during transition. |
| age private key | Rotate age key pair; re-encrypt SOPS | Maintenance window | All SOPS files must be re-encrypted; all hosts updated. |
| Device HMAC | Reissue secret; update device config | Near-immediate | Old HMAC signatures rejected after update. |
| Backup encryption key | Rotate in crypto service | Maintenance window | New backups use new key; historical backups may need re-encryption. |

---

## 6. Rollback Concerns

| Secret Type | Rollback Concern | Mitigation |
|---|---|---|
| 9Router API key | Service restart may fail if new key invalid | Validate new key before SOPS update; keep old key accessible during transition. |
| Discord bot token | Bot offline until new token deployed | Deploy new token immediately; monitor reconnection. |
| GitHub PAT | CI/CD pipeline blocked if new PAT lacks required scopes | Verify scopes before revoking old PAT; test MCP operations. |
| PostgreSQL passwords | Active transactions may fail during pool flush | Use connection pool draining; rotate during low-traffic window. |
| Redis password | Cache miss during restart | Acceptable; Redis is cache; data not lost (AOF/RDB). |
| R2/S3 credentials | Backup upload failure during rotation | Validate new credentials before revoking old; queue backup retry. |
| Gmail OAuth | Re-auth flow may fail if redirect URI misconfigured | Test re-auth flow before revoking old tokens. |
| Fernet key | Legacy field data unreadable if re-encryption fails | Stage key-ring deployment; verify re-encryption before retiring old key. |
| Domain KEK | All domain data unreadable if KEK rotation fails | Dual-key read during rotation; verify sample decrypts before retiring old key. |
| age private key | All SOPS secrets inaccessible if re-encryption fails | Test re-encryption on non-production copy first; verify on authorized host before pushing. |
| Device HMAC | Surveillance data rejected if device not updated | Deploy new HMAC to device before rejecting old signatures. |

---

## 7. Blast Radius Summary

| Secret Type | Blast Radius | Recovery Time |
|---|---|---|
| 9Router API key | Core persona + all sub-agents | Minutes (9Router key generation + SOPS update + restart) |
| Discord bot token | Primary UI layer + notifications | Minutes (token reset + reconnect) |
| GitHub PAT | CI/CD + self-deploy + code operations | Minutes-Hours (new PAT + scope verification) |
| PostgreSQL passwords | All database-dependent services | Minutes (ALTER ROLE + PgBouncer reload) |
| Redis password | Cache/queue/session state | Minutes (password change + restart) |
| R2/S3 credentials | Backup/archival pipeline | Minutes-Hours (new credentials + validation) |
| Gmail OAuth | Client email + transactional email | Minutes-Hours (re-auth flow) |
| Fernet key ring | Legacy encrypted fields | Hours (re-encryption job) |
| Domain KEK | Entire domain data | Hours (rewrap all DEKs + verify) |
| age private key | Entire SOPS secret inventory | Hours (re-encrypt all SOPS + update all hosts) |
| Device HMAC | Single device surveillance stream | Minutes (device config update) |
| Backup encryption key | Future backups only | Minutes (new key for new backups) |
| Recovery package key | Recovery capability | Hours (new recovery package creation) |
| Break-glass credentials | Emergency access | Minutes (credential rotation) |

---

## 8. Rotation Windows and Scheduling

| Secret Type | Preferred Rotation Window | Avoid Windows | Rationale |
|---|---|---|---|
| 9Router API key | Any time (9Router queue/retry) | Peak LLM usage if possible | Low blast radius; queue handles retry |
| Discord bot token | Low-activity period | During active SDLC loops | Samm may need interface during rotation |
| GitHub PAT | Any time | During CI/CD pipeline runs | Brief CI/CD pause acceptable |
| PostgreSQL passwords | Low-traffic window | During backup operations | Connection pool flush |
| Redis password | Any time | During session-heavy operations | Cache miss acceptable |
| R2/S3 credentials | Any time | During backup window | Backup retry handles failure |
| Gmail OAuth | Business hours (Samm available for re-auth) | After hours | Re-auth may require Samm interaction |
| Fernet key ring | Low-activity period | During financial/surveillance operations | Re-encryption job |
| Domain KEK | Low-activity period | During active decrypt operations | Rewrap requires decrypt/encrypt cycle |
| age private key | Maintenance window | Any active service | All SOPS must be re-encrypted |
| Device HMAC | Any time | During active surveillance streaming | Brief surveillance gap acceptable |
| Backup keys | Maintenance window | During backup operations | New backups use new key |
| Recovery package key | Samm-controlled offline session | N/A | Offline procedure |

---

## 9. Critical Path Dependencies

Some secret rotations depend on other secrets or systems:

1. **age private key rotation depends on:**
   - Samm recovery root access (for offline verification).
   - All SOPS files being re-encryptable.
   - All runtime hosts being updated with new age public key.

2. **Domain KEK rotation depends on:**
   - Crypto service module being operational.
   - All domain DEKs being accessible for rewrap.
   - Sample decrypt verification capability.

3. **SOPS secret rotation depends on:**
   - age private key being valid.
   - Runtime decryption path being functional.
   - Service restart capability.

4. **Database credential rotation depends on:**
   - PgBouncer being operational.
   - Connection pool management capability.
   - Service restart or hot-reload capability.

5. **Break-glass rotation depends on:**
   - Offline recovery package being accessible.
   - Recovery procedure being tested and documented.

---

## 10. Unresolved Surface Concerns

| Concern | Impact | Required Follow-up |
|---|---|---|
| Fernet compatibility ring exact scope | Unknown which fields still use Fernet; re-encryption scope unclear | Memory schema audit for Fernet-encrypted fields |
| Redis at-rest encryption constraints | Unknown if host/disk/container encryption is sufficient | Runtime security hardening spec |
| Windows daemon HMAC deployment mechanism | Unknown exact deployment path for new HMAC to Windows device | Windows daemon configuration documentation |
| idcloudhost S3 key scope granularity | Unknown if per-bucket or per-prefix credentials are supported | Object storage credential scoping review |
| Backup restore reconciliation testing frequency | Unknown if quarterly is sufficient | Backup/restore/DR runbook definition |
| Break-glass credential storage format | Unknown exact format of offline recovery package | Key recovery & break-glass runbook |

---

*Report generated: 2026-05-30 | Guinevere de Baroque — autonomous system steward*
