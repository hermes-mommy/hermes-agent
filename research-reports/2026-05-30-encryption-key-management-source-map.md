# Encryption & Key Management Source Map

**Date:** 2026-05-30
**Status:** Recovery evidence from background task `bg_a4752540`
**Reason:** The sub-agent returned a detailed inline report but did not create the required markdown file. Parent converted the collected findings into this evidence artifact.

## Sources Read by Sub-Agent

- `adr/ADR-008-memory-encryption-key-management.md`
- `adr/ADR-018-security-architecture-defense-in-depth.md`
- `adr/ADR-015-secrets-management-strategy.md`
- `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md`
- `Guinevere_PersonaSafetyPolicy_v1.0.md`
- `Guinevere_TechnicalArchitecture_v2.0.md`
- `Guinevere_APIIntegration_v2.0.md`

## Key Requirements Extracted

### ADR-008

- Must create explicit key hierarchy and rotation policy.
- Sensitive fields require encryption-at-rest, auditable key ownership, rotation procedure, emergency revoke path, and separation between secrets, profile memory, surveillance events, and operational logs.
- Follow-up gap: explicit master-key recovery, break-glass procedure, and key-escrow policy.

### ADR-018

- Must implement defense-in-depth: network isolation, least privilege, service hardening, secret protection, audit logs, dependency scanning, webhook verification, prompt-injection defenses, and incident response hooks.
- Follow-up gap: formal incident response playbook and threat-model update schedule.

### ADR-015

- SOPS + age with runtime injection is the accepted secret-management baseline.
- Plaintext secrets are forbidden in ADRs, docs, code, evidence, logs, and sub-agent reports.
- Risks: accidental logging bypasses SOPS; lost age key can block recovery.

### Data Governance Policy

- Critical domains include intimate memory, safe-word logs, crisis logs, inner journal, financial records, credentials/secrets, raw surveillance evidence, raw screenshots containing Restricted/Critical content, and sensitive exports/dossiers.
- SOPS + age must protect secrets files.
- Restricted filesystem permissions must protect private keys.
- Separate key scopes are required for secrets, profile memory, surveillance media, financial data, backups, and audit logs.
- Rotation records, emergency revoke path, and offline encrypted recovery package controlled by Samm are required.
- Backup keys must have separate scope from runtime secrets.
- Audit logs must cover Restricted/Critical access, safe-mode sensitive access, break-glass, secret redaction failures, incidents, exports, and sub-agent access.

### Persona Safety Policy

- Safe word is a global hard stop.
- Safe-mode state must restrict sensitive recall, surveillance-driven confrontation, autonomous pressure, punishment lookup, intimate memory retrieval, and raw surveillance retrieval.
- Safety logs must be minimal, non-punitive, encrypted, and must not store full intimate content by default.

### Technical Architecture v2.0

- SOPS secret management stores encrypted `.env.sops` files.
- age key path: `/home/guinevere/.age/key.txt`.
- Startup decrypt pattern: `sops -d .env.sops > /tmp/.env` with auto-cleanup.
- Covered secrets: 9Router API key, Discord token, GitHub PAT, DB passwords, R2 credentials.
- PostgreSQL, Redis, TimescaleDB, R2/idcloudhost, Loki, and backups are encryption surfaces.

### API Integration v2.0

- Integration registry lists `cryptography + Fernet + age`.
- Field-level encryption example uses Fernet.
- Double encryption example uses nested Fernet for intimate data.
- Tasker payloads use HMAC-SHA256 signature validation.

## Conflicts and Gaps

| Area | Finding | Required Resolution in Standard |
|---|---|---|
| AES-256-GCM | Foundation docs mention Fernet, not AES-GCM. User selected AES-256-GCM primary. | Standard must make AES-256-GCM primary for new app-level/envelope encryption and treat Fernet as transitional/compat. |
| Fernet | Existing code examples use Fernet globally. | Must forbid single global Fernet key for Critical domains and require domain/versioned key rings. |
| Key recovery | ADR-008/DataGovernance mention recovery but no procedure. | Must define offline encrypted recovery package, break-glass controls, post-use rotation. |
| Redis encryption | Redis carries sensitive buffers but no explicit at-rest encryption. | Must require source-class inheritance, short TTL, no durable raw Critical payload, and host/storage encryption. |
| Backups | Architecture says forever backups; Data Governance requires tiered retention and deletion reconciliation. | Must require encrypted backups, separate backup keys, restore reconciliation, and deletion ledger. |
| Double encryption | APIIntegration only covers intimate data. | Standard must expand Critical domains per user: intimate memory, safe-word logs, inner journal, financial, credentials, raw surveillance evidence. |
| Incident response | ADR-018 requires hooks but runbook missing. | Standard must define key-compromise containment/re-encryption evidence and recommend Incident Response/Secrets Rotation runbook. |

## Requirements for Final Standard

- Must be normative child of ADR-008, ADR-018, ADR-015.
- Must cross-enforce DataGovernancePolicy and PersonaSafetyPolicy.
- Must define key hierarchy: Samm root/recovery custody, KEK, domain DEK, per-record/content keys.
- Must define metadata: `key_id`, `key_version`, `algorithm`, `created_at`, `rotated_at`, `dek_wrapped_by`, `aad_context`, `ciphertext_hash`.
- Must require AES-256-GCM primary, ChaCha20-Poly1305 fallback, Fernet compatibility only.
- Must require SOPS+age operational controls and runtime plaintext cleanup.
- Must require rotation, break-glass, audit, recovery tests, and incident evidence.
