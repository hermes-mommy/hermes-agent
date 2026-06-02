# Data Governance / Classification — External Reference Patterns
**Date:** 2026-05-30  
**Scope:** Single-user private AI with intimate surveillance/memory data  
**Purpose:** Internal governance model — not formal compliance certification  

---

## 1. Executive Summary

This report distills implementable patterns from broadly recognized standards and open-source implementations for an internal data governance and classification policy. It tailors enterprise-grade controls (NIST, ISO/IEC 27701, CIS, OWASP LLM Top 10, CSA AICM) to a single-user private AI context with intimate memory/surveillance data. Every pattern includes a concrete reference so the policy author can trace the source.

**Scope boundary:** internal/private use only; user-selected enterprise controls applied at reduced organizational scale. No claim of legal compliance is made or implied.

---

## 2. Reference Catalog

| Ref ID | Source | Primary Relevance |
|---|---|---|
| [NIST-PF-1.1] | NIST Privacy Framework 1.1 (2025) | Privacy risk management; governance tiers |
| [NIST-SP-1800-39] | NIST SP 1800-39 (Feb 2026) | Data classification practices for unstructured data |
| [NIST-IR-8496] | NIST IR 8496 | Data classification concepts and schema design |
| [NIST-800-53R5] | NIST SP 800-53 Rev 5 | Security & privacy control catalog (AC, AU, IR, SC, PL) |
| [ISO-27701-2025] | ISO/IEC 27701:2025 | PIMS; privacy extension to ISO 27001 |
| [ISO-27001-2022] | ISO/IEC 27001:2022 | Information security management system baseline |
| [CIS-8.1] | CIS Controls v8.1 (2024) | Prioritized safeguards: Data Protection (Ctrl 3), Audit (Ctrl 8), Access (Ctrl 6) |
| [CIS-AI-LLM] | CIS AI/LLM Companion Guide (Apr 2026) | GenAI-specific interpretation of CIS Controls |
| [OWASP-LLMTOP10-2025] | OWASP Top 10 for LLMs v2025 | LLM-specific threat taxonomy (prompt injection, data leakage, etc.) |
| [OWASP-PROMPT-INJ] | OWASP Prompt Injection Prevention Cheat Sheet | Defensive patterns for instruction manipulation |
| [OWASP-LLMSVS-2.0] | OWASP LLMSVS v2.0 | Verification requirements for LLM security |
| [OWASP-GENAI-DATA] | OWASP GenAI Data Security 2026 (v1.0) | 21 data-security risks across GenAI lifecycle |
| [CSA-AICM-1.0] | CSA AI Controls Matrix v1.0 | AI supply-chain security controls incl. CEK, DSP, Logging |
| [GDPR-ART-15-22] | GDPR Articles 15–22 (EU) | Data subject rights model (access, erasure, portability) |
| [CNIL-AI-RIGHTS] | CNIL guidance on data subject rights in AI (2024) | AI-specific exercise of rights, retraining/filters for erasure |
| [EDPB-ACCESS-GUIDE] | EDPB Guidelines 01/2022 on right of access | Interpretation of access rights including ML context |
| [GDPR-ENG-ERASURE] | Engineering GDPR Erasure in SaaS (2026) | Technical patterns for deletion in complex systems |

---

## 3. Data Classification Tiers

### 3.1 Recommended Tier Model for Single-User Private AI

Adopt a **three-tier** classification aligned with NIST data classification concepts and CIS Control 3.7. For an intimate AI system, tiers should reflect both sensitivity of the underlying human data and the blast radius if leaked or misused.

| Tier | Label | Example Data | Handling Requirement |
|---|---|---|---|
| **T1** | `INTIMATE` | Diary entries, health disclosures, relationship history, location traces, voice transcripts, biometric/affective signals | Maximum protection; strictest access; longest retention review |
| **T2** | `PERSONAL` | Preferences, schedule, notes, task history, conversation summaries | Standard protection; owner-only access |
| **T3** | `OPERATIONAL` | System logs, model metadata, configuration, performance metrics | Basic protection; local-only |

**Source rationale:**
- NIST SP 1800-39 (Feb 2026) demonstrates how organizations discover, identify, and label unstructured data using schemas, and explicitly calls out Privacy High / Personal Credit / Health Information as classification categories ([NIST-SP-1800-39]).
- NIST IR 8496 emphasizes that classification policies should be monitored, auditable, and change-managed ([NIST-IR-8496]).
- CIS Control 3.7 requires enterprises to establish and maintain an overall data classification scheme and review it annually or upon significant changes ([CIS-8.1]).

**Implementable pattern:**
1. Define the tier set in a `data-classification-schema` file (versioned).
2. Every ingestion pipeline (user input, file import, API call, surveillance feed) applies a classifier at write time.
3. Default tier = `PERSONAL`; classifier must explicitly downgrade to `OPERATIONAL` or upgrade to `INTIMATE`.
4. Tiers are stored as metadata alongside the record (not inferred later from content).

### 3.2 Schema Design Considerations

- Use **labels**, not just categories. NIST SP 1800-39’s demonstration tools (ActiveNav, Trellix, Janusseal) assign sensitivity levels plus lifecycle facets ([NIST-SP-1800-39]).
- Include a **retention category** and calculated `deletion_date` at creation (GDPR engineering pattern: retention metadata layer) ([GDPR-ENG-ERASURE]).
- Version schemas. NIST SP 1800-39 explicitly notes that schema versioning is important; maintain records of schema versions with label counts ([NIST-SP-1800-39]).

---

## 4. Retention Schedules

### 4.1 Principles

- **Maximum and minimum timelines**: CIS Control 3.4 requires both minimum and maximum retention timelines ([CIS-8.1]).
- **Automated enforcement**: GDPR engineering literature treats the gap between documented retention and actual deletion as a systematic violation; automate deletion jobs that evaluate records against `deletion_date` ([GDPR-ENG-ERASURE]).
- **Exception handling**: Records under legal hold or legitimate interest override are flagged separately and reviewed on a schedule ([GDPR-ENG-ERASURE]).

### 4.2 Sample Retention Rules for Single-User AI

| Data Type | Default Retention | Rationale |
|---|---|---|
| Conversation transcripts | 90 days (min) / 2 years (max) | Balance recall utility vs. minimization |
| Surveillance/ambient captures | 30 days (min) / 6 months (max) | High sensitivity; frequent review |
| Derived summaries/embeddings | Match source retention | Do not outlive raw data |
| Audit/access logs | 90 days min (CIS 8.10) | Incident investigation baseline |
| Model checkpoints | 30 days (unless flagged) | Avoid stale intimate data in weights |
| Deletion markers / pseudonym tables | Indefinite | Required for backup-restore reconciliation |

**Source rationale:**
- CIS Control 3.4: “Data retention must include both minimum and maximum timelines” ([CIS-8.1]).
- CIS Control 8.10: minimum 90 days for audit logs ([CIS-8.1]).
- NIST Privacy Framework CT.DM-P5: “Data are destroyed according to policy” ([NIST-PF-1.1]).
- GDPR Art. 5(1)(e): personal data kept no longer than necessary ([GDPR-ART-15-22]).

### 4.3 Backup-Reconciliation Pattern

For append-only stores (event logs, vector DB snapshots, backups), use a **pending-erasure / delete-on-resurrection** pattern:
- Maintain a durable append-only list of erased subject identifiers.
- On backup restore, re-applies every erasure before data is exposed ([GDPR-ENG-ERASURE]).
- Defensible backup retention: 30–60 days for operational backups; longer only where law explicitly requires it ([GDPR-ENG-ERASURE]).

---

## 5. Data Minimization

### 5.1 Collection Minimization

- **Limit collection to minimum necessary** for identified purposes: ISO 27701 Annex A.7.4.1, aligned to GDPR Art. 5(1)(c) ([ISO-27701-2025]).
- **Limit processing**: restrict processing to what is adequate, relevant, and necessary — ISO 27701 A.7.4.2 / GDPR Art. 5(1)(b)(c) ([ISO-27701-2025]).

### 5.2 Processing Minimization

- **Disassociated Processing**: NIST Privacy Framework CT.DP-P encourages increasing disassociability (pseudonymization, aggregation, noise injection) to protect privacy while retaining utility ([NIST-PF-1.1]).
- **Prompt/RAG minimization for LLMs**: OWASP GenAI Data Security 2026 recommends:
  - Redact or tokenize sensitive fields before training/indexing.
  - Apply structured masking on inputs/outputs/logs.
  - “No-train/no-retain” policy enforcement for specific data types ([OWASP-GENAI-DATA]).

### 5.3 Storage Minimization

- **Ephemeral context windows**: do not persist full prompts if only derived state is needed.
- **Summarization with deletion**: compress conversation history into summaries and delete raw transcripts when the summary meets a quality threshold.
- **Retention metadata at creation**: tag every record with retention category and calculated deletion date at ingestion, not as a post-processing step ([GDPR-ENG-ERASURE]).

---

## 6. Audit Logs

### 6.1 What to Log

Log security-relevant events without capturing sensitive conversation content:
- Authentication events (success/failure).
- Data classification changes.
- Retention actions (deletions, anonymizations).
- Access to `INTIMATE` tier records (who, when, query hash if not full text).
- LLM interactions: request metadata, output metadata, but **not** full prompt/response payloads for sensitive data (OWASP LLMSVS V5.10: do not write secrets or full sensitive prompts to broadly accessible logs) ([OWASP-LLMSVS-2.0]).
- Tool invocations / agent actions (input, target, result status).
- Guardrail decisions (approval/refusal, reason category).

**Source rationale:**
- CIS Control 8.2: collect audit logs; 8.5: detailed logs with source/destination/username/timestamp ([CIS-8.1]).
- CIS Control 8.9: centralize logs; 8.10: retain minimum 90 days ([CIS-8.1]).
- NIST SP 800-53 AU-2 (Event Logging), AU-11 (Audit Record Retention) ([NIST-800-53R5]).
- CIS AI/LLM Companion Guide: “Validation failures logged with sufficient context for incident investigation” ([CIS-AI-LLM]).
- OWASP GenAI Data Security: DLP applied to telemetry pipelines; PII and credentials redacted before log storage ([OWASP-GENAI-DATA]).

### 6.2 Log Integrity

- **Tamper-evident storage**: use hash-chaining or append-only stores with periodic sealing (Semblance pattern: cryptographic signatures on every action before execution) ([Semblance-ref]).
- **Separation of duties**: logging service should not be writable by the component producing the events.

---

## 7. Encryption and Key Management

### 7.1 At-Rest Encryption

- **Encrypt sensitive data at rest**: servers, applications, databases. Storage-layer encryption is minimum; application-layer (client-side) encryption preferred for highest sensitivity data so storage-device access does not yield plaintext (CIS 3.11) ([CIS-8.1]).
- **End-user devices**: BitLocker / FileVault / dm-crypt (CIS 3.6) ([CIS-8.1]).
- **Vector stores and embeddings**: encrypt embedding vectors at rest to prevent inversion attacks and raw data extraction (CIS 3.11 mapping in DSGAI07) ([CIS-AI-LLM]).

### 7.2 In-Transit Encryption

- TLS for all network traffic; SSH for administrative access (CIS 3.10) ([CIS-8.1]).
- Mutual TLS or equivalent for any inter-process or cross-device communication involving intimate data.

### 7.3 Key Management Practices

Key management from Defense Cloud Top 10 / CIS / NIST patterns ([CSI-CloudTop10], [NIST-800-53R5], [CSA-AICM-1.0]):
- Keys generated on HSM should never be exported in plaintext.
- Key policies: implicit deny; least privilege; separation of duties between key management and key usage.
- Rotate keys periodically; destroy old keys only after confirming no encrypted data still depends on them.
- Encrypt customer/secret keys at rest and in transit.
- Do not store secrets in system prompts, config files, or CI/CD pipelines (OWASP LLMSVS V2.10 / V13.3) ([OWASP-LLMSVS-2.0]).
- Use OS keychain or dedicated secrets manager for API keys and credential material.

### 7.4 Cryptographic Erasure for Deletion

- **Key destruction as deletion**: encrypt personal data with a key held separately; upon erasure request, destroy the key. Data remains in append-only logs but becomes unreadable ([GDPR-ENG-ERASURE]).
- **Pseudonymization tables**: maintain a mapping table; destroy the mapping key upon erasure, replacing references with opaque stable pseudonyms ([GDPR-ENG-ERASURE]).

---

## 8. Access Control

### 8.1 Principles

- **Need-to-know / least privilege**: CIS Control 6.1 (inventory), 6.3 (ACLs based on need-to-know), 6.5 (principle of least privilege) ([CIS-8.1]).
- **Separation of duties**: no single account has all privileges needed for a critical function (e.g., key management vs. key usage) ([CSI-CloudTop10]).
- **Dormant account removal**: disable and eventually remove dormant accounts ([CIS-8.1]).

### 8.2 AI/LLM-Specific Access Control

- **Data access control lists on vector stores**: per-document ACLs; retrieval-time filtering; per-user/task memory isolation (OWASP GenAI Data Security DSGAI06, DSGAI13) ([OWASP-GENAI-DATA]).
- **Role-based / attribute-based access**: ISO 27001 A.9.1.1 (access control policy), A.9.2.1/2 (user registration, provisioning) mapped in ISO 27701 6.6.2.1/2 ([ISO-27701-2025]).
- **Purpose-based access**: ISO 27701 A.7.4.2 — limit processing to adequate, relevant, necessary purposes ([ISO-27701-2025]).
- **Privileged access management**: CIS 5.2 (unique passwords / keypairs), 5.3 (disable dormant), 5.4 (restrict admin privileges) ([CIS-8.1]).

### 8.3 Single-User Tailoring

- The operator is the sole authorized user; **all other identities are service identities** (LLM runtime, embedding model, vector store, OS).
- Service-to-service access must use authenticated local channels (Unix socket, mTLS on loopback) — no anonymous localhost access.
- Any cross-device sync must be opt-in and encrypted end-to-end with user-held keys (Cortex AES-256-GCM pattern) ([Cortex-ref]).

---

## 9. Incident Response

### 9.1 Plan Elements (Adapted from NIST / CIS)

NIST SP 800-53 IR family and CIS Control 17 ([NIST-800-53R5], [CIS-8.1]) define incident response as: preparation, detection and analysis, containment/eradication/recovery, post-incident activity.

For a single-user private AI, tailor as follows:

| Phase | Action | Owner (Single-User) |
|---|---|---|
| **Prepare** | Define incident taxonomy (data leak, prompt injection, key compromise, model poisoning, unauthorized access). Maintain a runbook. | User + Auditor sub-agent |
| **Detect** | Monitor anomaly patterns: spike in sensitive-topic queries, unexpected tool calls, guardrail refusal-rate shifts, encoding/prompt-injection signatures. | Automated monitors |
| **Analyze** | Determine scope: which data tiers affected? Was it a prompt injection, model extraction, or storage breach? | User |
| **Contain** | Revoke compromised keys/credentials; disable affected integration; isolate contaminated memory namespace. | User |
| **Eradicate / Recover** | Re-ingest from last clean checkpoint; re-encrypt with new key; rerun classification on restored data. | User + automation |
| **Post-incident** | Document timeline; update classification rules and guardrails; rotate all secrets; notify affected parties if applicable. | User |

**Source rationale:**
- NIST SP 800-53 IR-8 (Incident Response Plan), IR-4 (Incident Handling), IR-6 (Incident Reporting) ([NIST-800-53R5]).
- CIS Control 17.1: incident response management plan covers regulatory notification obligations for AI-related data breaches ([CIS-AI-LLM]).
- OWASP LLMSVS 8.1: continuously monitor usage patterns for anomalies; 8.2: alerting for prompt leaks / canary tokens ([OWASP-LLMSVS-2.0]).

### 9.2 AI-Specific Incident Scenarios

The incident taxonomy must include AI-native failure modes:
- **Prompt injection / jailbreak**: user or external data manipulates model behavior.
- **Data exfiltration via completion**: model reveals sensitive strings, keys, or PII from training/index.
- **RAG poisoning**: adversary injects malicious documents into retrieval corpus.
- **Model extraction**: systematic probing to replicate model behavior.
- **Cross-session bleed**: conversation history leaks across user contexts.
- **Tool misuse**: agent invokes unauthorized external action via compromised instruction.

**Source rationale:** OWASP GenAI Data Security 2026 enumerates 21 data-security risks across the GenAI lifecycle; the most operationally critical are DSGAI01 (sensitive data leakage), DSGAI03 (un-governed data flows), DSGAI06 (tool/plugin data drains), DSGAI11 (conversation bleed), DSGAI14 (telemetry leakage), DSGAI15 (over-broad context windows) ([OWASP-GENAI-DATA]).

---

## 10. Privacy-by-Design and Privacy-by-Default

### 10.1 Foundational Principles

- **Data minimization by default**: ISO 27701 A.7.4.4 (PII minimization objectives) and GDPR Art. 25 require that default settings enforce the minimum necessary data collection and processing ([ISO-27701-2025], [GDPR-ART-15-22]).
- **Privacy by design**: ISO 31700 (referenced in ISO 27701:2025) codifies privacy-by-design requirements including collection limitation, purpose binding, and end-of-processing requirements ([ISO-27701-2025]).
- **Local-first / sovereign architecture**: Several 2026 open-source implementations (Cortex, MemPalace, Semblance, SuperLocalMemory, Opal) operationalize privacy-by-design by architectural means:
  - Zero cloud calls by default for memory operations.
  - On-device encryption with user-held keys.
  - No telemetry.
  - Verified via automated audits (e.g., Semblance CI scans for networking imports in core) ([Cortex-ref], [MemPalace-ref], [Semblance-ref], [SuperLocalMemory-ref], [Opal-ref]).

### 10.2 Implementation Patterns

| Pattern | Description | Reference |
|---|---|---|
| **Enclave-resident reasoning** | All data-dependent decisions happen inside a trusted boundary; untrusted storage sees only fixed-size oblivious accesses. | Opal (arxiv 2604.02522) ([Opal-ref]) |
| **Dual-LLM quarantine** | Privileged LLM holds tools but never reads untrusted content; quarantined LLM reads untrusted content but cannot act. Structured summaries cross the boundary. | OWASP Prompt Injection Cheat Sheet ([OWASP-PROMPT-INJ]) |
| **System prompt hygiene** | Never embed secrets, credentials, or connection strings in system prompts. Treat system prompt as observable, not secret. | OWASP LLMSVS 5.7 / 5.10; OWASP Top 10 LLM01/LLM07 ([OWASP-LLMSVS-2.0], [OWASP-LLMTOP10-2025]) |
| **Local-only ingestion** | Memory and embedding pipelines run on-device; zero network calls during core operations. | SuperLocalMemory Mode A; MemPalace; Semblance Core ([SuperLocalMemory-ref], [MemPalace-ref], [Semblance-ref]) |
| **Cryptographic erasure** | Destroy decryption key to render stored data unreadable; satisfies erasure without corrupting append-only logs. | GDPR Engineering pattern ([GDPR-ENG-ERASURE]) |
| **Consent withdrawal / opt-out architecture** | Process data subject requests as system APIs, not support tickets; include identity verification, orchestration across stores, tamper-evident evidence. | WithSecure GDPR Subject Rights API; The Algo data-subject-rights-engineering-api ([WithSecure-API], [Algo-DSR]) |

---

## 11. Data Subject Rights as Internal Governance Model

Even for a single-user private system, modeling internal operations after GDPR-style rights provides audit-ready structure:

| Right | Internal Equivalent | Implementation Hint |
|---|---|---|
| **Access (Art. 15)** | Operator export of all personal data in structured format | Maintain a data-store registry; export JSON with metadata |
| **Rectification (Art. 16)** | Correction/update with audit trail | Append correction record; do not silently overwrite |
| **Erasure (Art. 17)** | Secure deletion + key destruction + tombstone replacement | Delete-on-resurrection pattern for backups |
| **Restriction (Art. 18)** | Freeze processing of flagged records | Legal-hold flag reviewed on schedule |
| **Portability (Art. 20)** | Structured, machine-readable export | JSON lines with schema version header |
| **Objection (Art. 21)** | Halt specific processing categories | Purpose-based access control toggle |
| **Consent withdrawal (Art. 7(3))** | Revoke authorization for a data category | Policy change + retroactive deletion where feasible |

**Source rationale:**
- EDPB Guidelines 01/2022 clarify scope of access, copy provision, and retention interplay ([EDPB-ACCESS-GUIDE]).
- CNIL 2024 guidance for AI systems emphasizes that controller must inform data subjects of inability to identify them, provide annotations/metadata in extracts, and use retraining or filters to honor erasure where direct deletion is impossible ([CNIL-AI-RIGHTS]).
- Engineering GDPR Erasure in SaaS (2026) provides deletion patterns including structural record retention with pseudonym replacement ([GDPR-ENG-ERASURE]).

---

## 12. Cross-Reference to Guinevere Seed Documents

| Policy Area | Relevant Seed Document(s) |
|---|---|
| Data classification schema + tiers | Guinevere_MemorySchema_v1.0.md |
| Retention schedules + deletion | Guinevere_APIIntegration_v1.0.md; Guinevere_MemorySchema_v1.0.md |
| Encryption / key management | Guinevere_TechnicalArchitecture_v1.0.md |
| Access control / RBAC | Guinevere_TechnicalArchitecture_v1.0.md |
| Audit logs / observability | Guinevere_TechnicalArchitecture_v1.0.md |
| Incident response | Guinevere_AgentLoopSpec_v1.0.md (safety gates) |
| Privacy-by-design | Guinevere_PRD_v1.0.md; Guinevere_Persona_Document_v1.0.md (consent/revocation) |

---

## 13. Implementation Roadmap (Suggested)

1. **Draft classification schema** (T1/T2/T3) and version it. ([NIST-SP-1800-39], [NIST-IR-8496])
2. **Add retention metadata** (`retention_category`, `deletion_date`) to every write path. ([GDPR-ENG-ERASURE], [CIS-8.1])
3. **Configure encryption**: at-rest (storage-layer + application-layer for T1), in-transit (TLS/mTLS), secrets in OS keychain. ([CIS-8.1], [CSI-CloudTop10])
4. **Stand up audit logging**: hash-chained, retention 90 days min, no full sensitive payloads. ([CIS-8.1], [OWASP-LLMSVS-2.0])
5. **Implement access control lists** on vector stores and databases; per-user/task memory isolation. ([OWASP-GENAI-DATA], [CIS-8.1])
6. **Write incident response runbook** including AI-specific scenarios (prompt injection, RAG poisoning, exfiltration). ([NIST-800-53R5], [CIS-AI-LLM])
7. **Adopt privacy-by-default settings**: local-only mode, minimal collection, no telemetry, verified by automated import scan. ([ISO-27701-2025], [Semblance-ref])
8. **Create data-subject-rights API** (internal) for export, correction, erasure orchestration with evidence generation. ([WithSecure-API], [Algo-DSR])

---

## 14. Caveats

- **Not legal advice.** This report surveys standards and patterns for internal governance design. It does not assert that Guinevere is compliant with GDPR, ISO 27701, NIST SP 800-53, CIS, or any other framework.
- **Scale mismatch.** The references target enterprises; application to a single-user system requires deliberate simplification (e.g., no DPO appointment, no multi-jurisdiction transfer mechanisms unless cross-border processing applies).
- **Technology evolves.** OWASP LLM Top 10 and GenAI Data Security are updated regularly; the 2025/2026 editions cited here should be re-checked when implementation begins.
- **Local-first implementations vary.** Cortex, MemPalace, Semblance, SuperLocalMemory, and Opal are independent projects with different threat models. Patterns are borrowed selectively.

---

## 15. References (URLs)

- [NIST-PF-1.1] https://www.nist.gov/privacy-framework
- [NIST-SP-1800-39] https://csrc.nist.gov/pubs/sp/1800/39/ipd
- [NIST-IR-8496] https://nvlpubs.nist.gov/nistpubs/ir/2023/NIST.IR.8496.ipd.pdf
- [NIST-800-53R5] https://csrc.nist.gov/pubs/sp/800/53/r5/final
- [ISO-27701-2025] https://www.iso.org/standard/27701
- [ISO-27001-2022] https://www.iso.org/standard/27001
- [CIS-8.1] https://www.cisecurity.org/controls/cis-controls-list
- [CIS-AI-LLM] https://www.cisecurity.org/insights/white-papers/controls-v8-1-ai-llm-companion-guide
- [OWASP-LLMTOP10-2025] https://owasp.org/www-project-top-10-for-large-language-model-applications/
- [OWASP-PROMPT-INJ] https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html
- [OWASP-LLMSVS-2.0] https://owasp.org/www-project-llm-verification-standard/LLMSVS-v2.0-en.html
- [OWASP-GENAI-DATA] https://www.lotharschulz.info/wp-content/uploads/OWASP-GenAI-Data-Security-Risks-and-Mitigations-2026-v1.0.pdf
- [CSA-AICM-1.0] https://www.cloudsecurityalliance.org/artifacts/ai-controls-matrix/
- [GDPR-ART-15-22] https://gdpr-info.eu/art-15-gdpr/ through https://gdpr-info.eu/art-22-gdpr/
- [CNIL-AI-RIGHTS] https://cnil.fr/en/ensuring-and-facilitating-exercise-data-subjects-rights
- [EDPB-ACCESS-GUIDE] https://www.edpb.europa.eu/system/files/2023-04/edpb_guidelines_202201_data_subject_rights_access_v2_en.pdf
- [GDPR-ENG-ERASURE] https://wolf-tech.io/blog/gdpr-right-to-erasure-engineering-deleting-users-from-complex-saas-systems
- [WithSecure-API] https://github.com/WithSecureOpenSource/gdpr-subject-rights-api
- [Algo-DSR] https://www.the-algo.com/insights/gdpr-data-subject-rights-engineering-api
- [CSI-CloudTop10] https://media.defense.gov/2024/Mar/07/2003407858/-1/-1/0/CSI-CloudTop10-Key-Management.PDF
- [Cortex-ref] https://github.com/gambletan/cortex
- [MemPalace-ref] https://github.com/milla-jovovich/mempalace
- [Semblance-ref] https://github.com/skygkruger/semblance-core
- [SuperLocalMemory-ref] https://github.com/qualixar/superlocalmemory
- [Opal-ref] https://arxiv.org/html/2604.02522

---

*Report written by Guinevere research sub-agent. Output file is the sole deliverable.*
