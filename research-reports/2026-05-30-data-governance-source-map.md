# Data Governance Source Map — Recovery Evidence

**Date:** 2026-05-30  
**Status:** Recovery evidence written by parent agent because the original sub-agent output file existed but was empty.  
**Scope:** Source mapping for `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md`.

---

## Source Documents Reviewed

| Document | Role |
|---|---|
| `adr/ADR-024-data-governance-classification-policy.md` | Normative parent for data governance and classification. |
| `adr/ADR-010-surveillance-data-retention-policy.md` | Normative parent for retention, minimization, export/delete controls. |
| `adr/ADR-008-memory-encryption-key-management.md` | Normative parent for encryption, key hierarchy, rotation, emergency revoke. |
| `Guinevere_PersonaSafetyPolicy_v1.0.md` | Cross-boundary safety policy for safe mode, sensitive recall, surveillance confrontation, and non-punitive safety logs. |
| `Guinevere_MemorySchema_v2.0.md` | Implementation source for memory domains, encryption classes, raw/content fields, and known retention conflicts. |
| `Guinevere_TechnicalArchitecture_v2.0.md` | Runtime/storage source for PostgreSQL, Redis, TimescaleDB, object storage, logs, backups, PgBouncer, and service identities. |
| `Guinevere_BRD_v2.0.md` | Business source for single-user consent, omniscient surveillance, financial tracking, client communication, and security requirements. |

---

## Key Source Findings

### ADR-024 — Data Governance & Classification

- Guinevere stores personal, intimate, surveillance, financial, client, operational, and security-sensitive data.
- Every store, API, log, memory path, and export must map to a data class.
- Classification must drive retention, encryption, access control, audit logging, and sub-agent visibility.
- Follow-up note requires explicit PII/data-class mapping and integration with ADR-008 key hierarchy.

### ADR-010 — Surveillance Data Retention

- Retention must be by data class, usefulness, sensitivity, and safety risk.
- Raw telemetry, summaries, derived facts, emotional annotations, financial data, and audit logs must be distinguished.
- Raw retention should be minimized; curated summaries/evidence may live longer.
- Samm-controlled deletion/export must be supported.
- Follow-up note requires a data-minimization checklist and DPIA-style mapping if scope expands beyond single-user.

### ADR-008 — Memory Encryption & Key Management

- Sensitive memory requires encryption-at-rest, auditable key ownership, rotation, emergency revoke, and separation between secrets/profile/surveillance/operational logs.
- Follow-up note requires break-glass, master-key recovery, and key-escrow procedure.

### PersonaSafetyPolicy Cross-Boundary Requirements

- Consent is specific, revocable, auditable, and non-transferable.
- Safe word/distress state restricts persona escalation, surveillance confrontation, autonomous pressure, and sensitive recall.
- Safety logs must be minimal, non-punitive, restricted, and encrypted.
- Raw surveillance must not be stored where a summary/hash is sufficient.
- Sensitive contexts include medical, intimate, financial, client-confidential, and crisis-related data.

### MemorySchema Findings

- Stores episodic memory, semantic facts, Samm Profile, emotional events, persona drift logs, inner journal, financial data, project/client data, social map, and surveillance-derived data.
- Existing docs contain `data forever` / `no deletion` philosophy that conflicts with ADR-010 minimization.
- Samm Profile, intimate profile, inner journal, surveillance screenshots, and financial data already imply higher encryption requirements.
- Export/dossier rules in MemorySchema may conflict with Samm rights; this policy must govern access/export/correct/delete/do-not-recall rights.

### TechnicalArchitecture Findings

- PostgreSQL, Redis, TimescaleDB, R2/S3, Loki, and backup flows all need classification metadata.
- Redis DB2 surveillance buffer, raw screenshot object storage, audit logs, WAL/pg_dump backups, and secrets/config backups need explicit classification and retention rules.
- PgBouncer service users exist but need least-privilege alignment with data class.
- Current backup and Timescale sections include `forever` retention language that this policy must supersede for raw payloads.

### BRD Findings

- System is single-user and fully consented, but data is highly intimate and enterprise-grade governance is still required.
- BRD includes 24/7 surveillance, financial tracking, client communication, monitoring/logging, and encrypted backups.
- `data forever` and `no privacy hours` must be interpreted under ADR-010/024 and this policy, not as unlimited raw data retention.

---

## Conflicts This Policy Must Resolve

| Conflict | Resolution Required |
|---|---|
| `data forever` in BRD/Memory/TechnicalArchitecture vs ADR-010 minimization | Tiered retention: curated memory/evidence may be long-term; raw payloads must expire, summarize, archive, anonymize, or be held under formal retention hold. |
| Memory export rules restricting intimate profile reveal | Samm rights to access/export/correct/delete/do-not-recall must govern, with redaction, safety, and encryption controls. |
| PgBouncer broad roles vs least privilege | Future RBAC/ABAC matrix must map service/action/data-class permissions. |
| Surveillance scope broadness vs PersonaSafety safe mode | Safe word/distress must restrict surveillance confrontation, sensitive recall, and autonomous pressure. |
| Backups with forever retention vs deletion/correction rights | Backup reconciliation and delete-on-restore controls are required. |

---

## Required Policy Inclusions

- Five-tier classification model: Public, Internal, Confidential, Restricted, Critical.
- Default unclassified data: Confidential.
- Highest classification wins.
- Table/Redis/object/log/export labels mandatory.
- Tiered retention matrix by data type and risk.
- Safe-mode access restrictions.
- Encryption matrix integrated with ADR-008.
- Audit logs for access, classification changes, retention actions, exports, and safe-mode sensitive access.
- Incident response for unsafe recall, over-collection, wrong classification, secret leak, unauthorized access, retention failure, and privacy-invasive persona behavior.
- Evidence artifacts in Markdown for governance reviews, retention runs, exports, incidents, and policy reviews.

---

## Recovery Note

The original sub-agent summary was collected, but the promised markdown output was empty. This file preserves the actionable source-map findings in project-required file-based form.
