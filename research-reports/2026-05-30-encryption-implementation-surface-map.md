# Encryption Implementation Surface Map

**Date:** 2026-05-30
**Status:** Recovery evidence from background task `bg_55ff8043`
**Reason:** The sub-agent returned implementation findings inline but did not create the required markdown file. Parent converted the collected findings into this artifact.

## Data Stores and Secret Stores

| Surface | Location / Example | Source Evidence | Encryption/Key Concern |
|---|---|---|---|
| age private key | `/home/guinevere/.age/key.txt` | TechnicalArchitecture §7.2 | Must be 0600, owner-only, excluded from plain backups, represented in recovery package only encrypted. |
| SOPS secrets | `/home/guinevere/config/.env.sops`, `.env.sops` | TechnicalArchitecture §7.2, ADR-015 | Must be repo-safe encrypted config; plaintext forbidden in docs/code/logs/evidence. |
| Runtime decrypted env | `/tmp/.env` | TechnicalArchitecture §7.2 | Must be tmpfs/runtime-only, 0600, auto-cleaned, never logged/backed up. |
| 9Router key | `OPENROUTER_API_KEY` style provider variable | APIIntegration §2.1 | Must be SOPS-protected high-risk API credential. |
| Discord token | Discord bot runtime secret | TechnicalArchitecture §7.2 | Must be SOPS-protected, rotated on leak, redacted in logs. |
| GitHub PAT | GitHub integration token | APIIntegration §4.3 | Must be least privilege, expiry/rotation, never logged. |
| DB passwords | PostgreSQL/PgBouncer service credentials | TechnicalArchitecture §7.2 | Must be per-service, no app superuser, rotated. |
| R2/idcloudhost keys | `R2_ACCESS_KEY`, `IDCLOUD_KEY` etc. | APIIntegration §6.2 | Must be scoped to buckets/prefixes, encrypted, rotated. |
| Device HMAC secret | `DEVICE_SECRET` | APIIntegration §5.1 | Must be per-device, rotated on device compromise. |
| Fernet keys | `FERNET_KEY`, `INTIMATE_KEY` | APIIntegration §10.5 | Must be domain-separated, versioned, SOPS-wrapped, not global for Critical. |
| Baileys auth | WhatsApp session state | APIIntegration communication stack | Must be Restricted/Critical depending contents; protected as credential. |
| Gmail OAuth token | Gmail API integration | APIIntegration registry | Must be SOPS-protected credential with refresh-token handling. |
| Resend API key | Email integration | APIIntegration registry | Must be SOPS-protected API token. |
| Gotify token | Push notification backup | APIIntegration registry | Must be SOPS-protected token. |
| Sentry DSN/token | Error tracking | APIIntegration registry | Must be classified and redacted if secret-capable. |

## Persistent Data Surfaces

| Store | Data | Required Control |
|---|---|---|
| PostgreSQL | memory, persona, behavior, surveillance, financial, projects, system, social | Disk/storage encryption plus app-level field encryption for Restricted/Critical fields. |
| TimescaleDB | surveillance time-series | Restricted/Critical inheritance, encryption, retention and backup reconciliation. |
| Redis DB0 | task queue | Internal by default; payload inherits source class. |
| Redis DB1 | LLM cache | Internal by default; sensitive prompts inherit and must be minimized. |
| Redis DB2 | surveillance buffer | Restricted/Critical, short TTL, no durable raw Critical payload. |
| Redis DB3 | session state | Confidential/Restricted/Critical depending active safe mode/context. |
| Redis DB4 | pub/sub | Internal; no durable payload. |
| Redis DB5 | rate limiting | Internal metadata only. |
| R2/idcloudhost | backups, screenshots, cold storage, exports | Private buckets, encryption before upload, separate backup/export keys, lifecycle/retention controls. |
| Loki/PostgreSQL audit | logs and audit events | No plaintext secrets; metadata-only key usage logs; encrypted Restricted/Critical excerpts. |
| GitHub private repo | SOPS secrets and configs | Encrypted artifacts only; no plaintext secrets. |

## Rotation Points

- SOPS age recipient set: annual review and immediate rotation on device loss/operator change/suspected compromise.
- High-risk API tokens: quarterly and immediate on exposure.
- Domain DEKs: annual default, quarterly for Critical/high-risk domains, immediate incident rotation.
- Backup keys: annual and immediate if recovery package/storage exposure suspected.
- Break-glass credentials: rotate after every use.
- Device HMAC secrets: rotate on device compromise/replacement.
- Fernet/MultiFernet rings: add new primary, read old, re-encrypt, retire old after verification.

## Audit Points

- Every Restricted/Critical decrypt.
- Every key rotation, key unwrap, re-encryption job, break-glass, export creation, backup restore, secret access, secret scan failure, and incident containment/recovery event.
- Audit records must include key_id, key_version, operation, actor/service, data domain, result, correlation_id, and evidence path; never plaintext keys or secrets.

## Breach Response Surfaces

- SOPS key compromise: re-encrypt all SOPS files, rotate all credentials represented in affected files, invalidate runtime plaintext env, write incident report.
- Fernet/domain DEK compromise: mark key compromised, create new key version, re-encrypt affected domain records, verify counts/hashes, retire compromised key.
- Backup key compromise: rotate backup key, re-encrypt retained backups where feasible, mark unrecoverable exposure risk for immutable backups, test restore.
- GitHub PAT leak: revoke PAT, rotate webhooks/tokens if affected, scan logs/evidence for leaked token, add regression redaction test.
- Device HMAC secret leak: revoke device secret, issue new per-device secret, quarantine payloads during compromise window.

## Gaps for Final Standard

- Need formal key inventory schema.
- Need concrete key metadata schema for encrypted records.
- Need SOPS runtime decryption hardening beyond `/tmp/.env`.
- Need app crypto service API contract.
- Need break-glass and recovery package procedure.
- Need Redis encryption/minimization rule.
- Need backup deletion-ledger reconciliation rule.
