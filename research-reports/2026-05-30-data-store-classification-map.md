# Data Store Classification Map — Recovery Evidence

**Date:** 2026-05-30  
**Status:** Recovery evidence written by parent agent because the original sub-agent report file was not created.  
**Scope:** Data-store and data-domain classification input for `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md`.

---

## Classification Inputs

User-selected answers are authoritative where this recovery map differs from sub-agent recommendations.

| Data Domain / Store | Default Classification | Notes |
|---|---:|---|
| Public docs intentionally published | Public | Only if explicitly approved for public disclosure. |
| System config without secrets | Internal | Escalates to Critical if secrets, tokens, credentials, keys, or deployment-sensitive values appear. |
| Project/code/task data | Internal | Escalates to Restricted/Critical if client, secret, financial, or private operator data is embedded. |
| Semantic facts | Confidential | Escalates based on source content. |
| Episodic memory | Restricted | Long-term, correction/delete/do-not-recall supported. |
| Emotional memory | Critical | User-selected: intimate/emotional memory is Critical. |
| Inner journal | Critical | Double-encrypted, minimal access. |
| Samm Profile — identity/preferences/behavioral | Confidential | Escalates if intimate, health, psychological, financial, or predictive. |
| Samm Profile — psychological/health/predictive/social | Restricted | Escalates to Critical if distress, safe-word, intimate behavior, crisis, or raw surveillance included. |
| Samm Profile — intimate | Critical | Double encryption and access audit required. |
| Safe-word logs | Critical | Minimal, non-punitive, encrypted. |
| Persona drift logs | Restricted | Critical if tied to safe word, distress, intimate behavior, or unsafe persona boundary. |
| Punishment/reward/violation logs | Restricted | Critical if tied to distress/safe word/intimate data. |
| Raw screenshots | Restricted | Short retention 7-30 days unless promoted to evidence/memory; Critical if intimate/financial/secret/client content visible. |
| Clipboard contents | Restricted | Raw short retention; Critical if credentials, financial, intimate, crisis, or client data. |
| Browser history | Restricted | Critical if credentials, financial, health, intimate, or client-sensitive context. |
| Notification/message content | Restricted | Store extracted facts by default; raw minimized. Critical if intimate/crisis/secret/client-sensitive. |
| Location/geofence raw traces | Restricted | Raw short-term; aggregates may be longer. Critical if safety incident evidence. |
| Surveillance summaries/derived events | Restricted | Escalates based on content. |
| Financial transactions and predictions | Restricted | Seven-year/configurable retention; encrypt and audit. Critical if credentials/raw account access tokens. |
| Client data and communication | Restricted | Critical if contractual secrets, credentials, or highly sensitive client info. |
| Social map | Restricted | Escalates if intimate/crisis/client-sensitive. |
| Audit/security logs | Confidential | Restricted/Critical if they contain sensitive payload fragments or safe-word events. |
| Guinevere action logs | Confidential | Escalates when action touches Restricted/Critical data. |
| Redis DB0 task queue | Internal | Escalates per payload. |
| Redis DB1 LLM cache | Internal | Must not store Critical raw prompts unless explicitly justified; TTL required. |
| Redis DB2 surveillance buffer | Restricted | Critical if raw intimate/secret/client data. Short TTL. |
| Redis DB3 session state | Confidential | Escalates per payload; safe-mode state must be protected. |
| Redis DB4 pub/sub | Internal | Payloads inherit source classification. |
| Redis DB5 rate limit | Internal | No sensitive payloads. |
| Object storage raw surveillance media | Restricted | Critical if intimate/secret/client/financial content; private encrypted buckets only. |
| PostgreSQL WAL/pg_dump backups | Restricted | Critical if containing Critical data and not segmented. Encrypted before upload. |
| Redis backups | Confidential | Escalates by payload; encrypted. |
| Config/secrets backups | Critical | SOPS/age; separate key scope; rotation. |
| Exports/dossiers | Highest source classification | Encrypted, logged, time-limited, redaction options. |
| LLM prompts/context bundles | Highest included source classification | Minimum necessary; redact Critical unless required. |

---

## Retention Class Inputs

| Retention Class | Typical Use | Handling |
|---|---|---|
| Transient | Redis buffers, temporary prompt context, rate limits | TTL minutes/hours; no backup unless operationally necessary. |
| Short Raw | Screenshots, clipboard, raw notification/message payloads, raw browser/location traces | 7-30 days by default; delete or summarize. |
| Medium Operational | Derived surveillance events, system/action logs, task context | 30-180 days unless promoted. |
| Long-Term Curated | Episodic/semantic memory, emotional memory, validated profiles, client/project memory | Archive with correction/delete/do-not-recall states. |
| Regulated/Audit | Financial records, security/audit logs, incident evidence | Financial 7 years/configurable; audit longer than raw payloads. |
| Formal Hold | Incident/legal/safety evidence | Owner, reason, scope, expiry, review date required. |

---

## Enforcement Gaps

- Current schemas do not consistently include `classification`, `retention_class`, `retention_until`, `purpose`, `source`, `access_policy`, or `deletion_state` fields.
- Current Redis key taxonomy does not encode classification or retention class.
- Current object storage prefix taxonomy does not encode classification or lifecycle policy.
- Current service roles need a formal RBAC/ABAC matrix.
- Current backup model needs delete-on-restore / erasure reconciliation.

---

## Recovery Note

The original sub-agent summary was collected, but the promised markdown output was missing. This file preserves the actionable classification map in project-required file-based form.
