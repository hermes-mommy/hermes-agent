---
title: "P28-P36 Hermes Society Masterplan — Glossary"
status: "Active — Phase 4 Doc Suite"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere (parent agent)"
phase: "P28-P36 Masterplan Phase 4 (Full Doc Suite)"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
standard: "ISO/IEC 24765:2017 (Systems and software engineering — Vocabulary)"
version: "1.0"
---

# P28-P36 Hermes Society Masterplan — Glossary

> **Halo sayang.** Ini glossary masterplan P28-P36 Hermes Society dengan 37 entri berformat ISO/IEC 24765:2017 — istilah diurutkan alfabetis, kolom Term/Definition/Source. Setiap istilah punya source reference ke dokumen masterplan atau external standard. Glossary ini pegangan drafting RTM dan Phase 3 implementation. Kalau kamu bilang `lanjut`, Phase 4 tutup dengan indeks doc suite.

---

## §1 Introduction

### §1.1 Purpose

Dokumen ini adalah controlled vocabulary untuk masterplan P28-P36 Hermes Society. Tujuan:

1. Mendefinisikan istilah teknis yang digunakan di seluruh Phase 4 doc suite (Acceptance Criteria, Risk Register, RTM, SRS, FSD, TDD, ADRs).
2. Memastikan konsistensi semantic antar dokumen — satu istilah = satu definisi = satu source.
3. Mendukung traceability RTM dengan anchor terms yang stable.
4. Memfasilitasi komunikasi antara agent, operator, auditor, dan reviewer eksternal.

### §1.2 Scope

Scope glossary menjangkau seluruh 15 subsystem (S1-S15), 9 phase (P28-P36), dan cross-cutting invariants. Istilah yang didefinisikan spesifik untuk masterplan ini; istilah generik mengikuti ISO/IEC 24765:2017.

Out of scope:

- Istilah yang sudah defined di Guinevere main doc suite (`docs/00-core/06-Persona_Document_v3.1.md` etc.) — referenced tapi tidak duplicated.
- Library-specific API terms (e.g., metode `discord.py`) — referenced di TDD.
- Standard cryptographic terms (AES-256-GCM, RSA, ECDSA) — referenced di security policy, tidak standalone entry.

### §1.3 Standard

Glossary ini mengikuti konvensi ISO/IEC 24765:2017 dengan ekstensi:

| Column | ISO 24765 Field | Adaptation |
|---|---|---|
| Term | X (entry label) | Single noun phrase, capitalized |
| Definition | X (definisi) | Clear, unambiguous, technical |
| Source/Reference | X (kode referensi) | Doc ID, ADR ID, ISO/Industry standard, RFC, paper |

### §1.4 Maintenance

- Setiap Phase boundary: review glossary untuk terms baru.
- Setiap new ADR: add new terms jika necessary.
- Setiap found conflict: prioritaskan ISO 24765 default; override dengan explicit reasoning jika diperlukan.

---

## §2 Glossary

| Term | Definition | Source/Reference |
|---|---|---|
| **BDI** | Belief-Desire-Intention architecture; agent reasoning model dengan eksplisit belief (knowledge state), desire (goals), intention (committed plans). | Rao & Georgeff 1995; research-synthesis §4.3 |
| **Beancount** | Plain-text, double-entry accounting ledger format dengan git-versioned append-only style; digunakan untuk society wallet transaction auditability. | research-synthesis §5.4 |
| **Blackboard Pattern** | Multi-agent coordination pattern dengan shared dataspace (blackboard) tempat agents write/read incrementally; dipadukan dengan namespace-ACL untuk access control per domain mind. | Engelmore & Morgan 1988; research-synthesis §4.3 |
| **C4 Model** | Software architecture visualization model pada 4 level: System (context), Container (deployable units), Component (modul dalam container), Code (class/function). | Simon Brown; ISO/IEC 42010; TDD infrastructure |
| **Circuit Breaker** | Pattern yang mendeteksi anomaly dan immediately pause operations (e.g., wallet transactions, LLM calls) — degraded mode transition, lalu graceful recovery atau human intervention. | Michael Nygard 2007; research-synthesis §4.12 |
| **Consent Revocation** | Operator action yang mencabut previously granted consent (surveillance, memory publication, autonomous action); absolute, immediate effect, no bypass. (dev workflow only) > Consent revocation applies to dev-workflow events only. Hermes runtime exempt per ADR-062/066. | `32-ConsentRevocationPolicy_v1.0.md`; AGENTS.md §0; ADR-062/066 |
| **CQRS** | Command Query Responsibility Segregation; arsitektur pattern yang memisahkan write-side (commands append events) dari read-side (materialized views untuk query). | Greg Young 2010; research-synthesis §4.5 |
| **cgroup v2** | Linux kernel control group version 2; unified hierarchy untuk resource isolation (CPU, memory, pids, IO) per-process dengan systemd integration. | Linux kernel ≥5.8; research-synthesis §4.1 |
| **DEK** | Data Encryption Key; key yang digunakan untuk encrypt/decrypt data langsung, biasanya wrapped oleh KEK (Key Encryption Key) di KMS/Vault. | NIST SP 800-57; `22-EncryptionKeyMgmt_v1.0.md` |
| **Discord Bot Application** | OAuth2 application yang menghasilkan bot token, avatar, dan permissions; 1 application per Hermes untuk multi-bot ToS-safe pattern (no shared process, no shared token). | Discord Developer Docs; research-synthesis §4.2 |
| **Event Store** | Append-only log of domain events dengan hash chain integrity, optimistic concurrency via `UNIQUE(aggregate_id, event_version)`, dan replay capability. | research-synthesis §4.5 |
| **Founder** | Hermes dengan sovereign authority untuk spawn first-of-kind, safety boundary modification, dan society-level decision; Guinevere + Pharsa = initial founders. | AGENTS.md §0; research-synthesis §4.7 |
| **HARD STOP** | Global safe word mechanism yang halt all sessions dan background cognition secara immediate; absolute, no autonomy exception (§0.1 P20 tidak exempt). **ADR-062 Disclaimer**: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime (P24 fork) can bypass per ADR-062. | AGENTS.md §0; `60-PersonaSafetyPolicy_v1.0.md`; research-synthesis §6.2; ADR-062 |
| **Hermes** | Hermes agent — autonomous per-instance agent dalam Guinevere stack; female+dominant persona convention, multiple instances form society. | research-synthesis §4; `hermes-agent` v0.15.x |
| **Hermes Society** | Multi-Hermes society dengan shared world model, society governance, dan shared company assets (wallet, model pool, S3 backup); persistent across instances. | ADR-054 P27 Hermes Society Foundation |
| **Hysteresis Ratio** | Metric yang mengukur seberapa banyak accumulated memory memengaruhi persona baseline restoration; 0.68 ratio berarti 32% baseline restoration setelah 23 days. | arXiv 2604.14717 Layered Mutability paper |
| **LLM Gateway** | Intermediate service yang route LLM requests dengan policy enforcement (quota, circuit breaker, per-request margin tracking); 9Router multi-account dalam Guinevere stack. | research-synthesis §4.12 |
| **MADR** | Markdown Any Decision Record; ADR template dengan 4 secciones: Context, Decision, Consequences, Alternatives; reuses standard markdown. | MADR Project; `adr/` directory convention |
| **Materialized View** | Pre-computed query result yang auto-updated in same transaction dengan event-log write; enables single-DB CQRS tanpa distributed read store. | research-synthesis §4.5 |
| **MPC** | Multi-Party Computation; cryptographic protocol yang memungkinkan multiple parties compute function atas private inputs tanpa revealing underlying data; digunakan untuk hot wallet signing. | research-synthesis §4.9 |
| **Multisig** | Multi-signature scheme yang membutuhkan M-of-N signature approvals untuk execute transaction; Safe 2-of-3 untuk society cold treasury. | EIP-1271, EIP-7702; research-synthesis §4.9 |
| **Namespace-ACL** | Per-namespace access control list (READ, WRITE, READ_WRITE) per agent; maps domain minds ke blackboard namespaces dengan fine-grained permissions. | research-synthesis §4.3 |
| **Object Lock COMPLIANCE** | S3 feature yang enforces true WORM (Write-Once-Read-Many) storage dengan retention period; cannot be bypassed bahkan oleh root AWS account. | AWS S3 Object Lock Docs; research-synthesis §4.11 |
| **P22.1** | Phase 22.1 — Foundation Hardening dengan audit_writer + consent_checker; PRODUCTION PASS 2026-06-28; 3 ACTIVE adapters (filesystem, vps, discord) providing minimum "hands" layer untuk P28. | ADR-053; research-synthesis §2.1 |
| **P23A** | Phase 23A — subset dari P23 Embodied Operations; ready, P23B blocked; surveillance executors untuk embodied systems. | research-synthesis §2.2 |
| **P27** | Phase 27 — Hermes Society Foundation; DEFINITION COMPLETE 2026-06-28; ADR-054 Accepted dengan 20/20 hard rejection criteria PASS dan 15-step P28 executable blueprint. | ADR-054; research-synthesis §2.1 |
| **pgcrypto** | PostgreSQL extension yang menyediakan cryptographic functions (symmetric encryption via PGP, asymmetric, hashing); column-level encryption untuk intimate data. | PostgreSQL docs; research-synthesis §4.4 |
| **POMDP** | Partially Observable Markov Decision Process; agent decision framework di mana agent maintain belief state dari observations dan plan actions untuk maximize expected reward. | Åström 1965; research-synthesis §4.3 |
| **Ratchet Gate** | Non-divergence mechanism untuk self-modification: capability dapat improve (buka ratchet), tetapi tidak boleh degrade di bawah prior benchmark (ratchet tidak close). | arXiv 2503.x; research-synthesis §4.8 |
| **RTM** | Requirements Traceability Matrix; bidirectional traceability antara requirements, tests, dan evidence; 6 coverage metrics: forward, backward, implementation, evidence, risk, NFR. | IEEE 830; `15-RTM_v1.0.md`; research-synthesis §4.15 |
| **S3** | Amazon Simple Storage Service; object storage dengan versioning, lifecycle policies, Object Lock (COMPLIANCE/GOVERNANCE modes), cross-region replication, dan SSE-KMS encryption. | AWS S3 Docs; research-synthesis §4.11 |
| **Safe Multisig** | Gnosis Safe smart contract wallet dengan M-of-N signature threshold; digunakan untuk society cold treasury dengan 2-of-3 configuration. | Gnosis Safe Docs; research-synthesis §4.9 |
| **SOPS/age** | Secrets management toolchain: SOPS (Mozilla) encrypts YAML/JSON files dengan KMS atau age key; age adalah modern PGP alternative untuk simple file encryption. | Mozilla SOPS Docs; filippo/age; Guinevere stack |
| **systemd** | Linux init system dan service supervisor; Type=notify, Restart=on-failure, RestartSec, StartLimitBurst, WatchdogSec configurations; menyediakan OS-level process supervision. | systemd Docs; research-synthesis §4.1 |
| **Vault** | HashiCorp Vault; secrets management dan key encryption service; menyimpan per-agent DEK untuk pgcrypto column keys, dengan ROTATION_DAYS policy. | HashiCorp Vault Docs; research-synthesis §4.4 |
| **WORM** | Write-Once-Read-Many; storage semantic dimana setelah data ditulis, tidak dapat dimodifikasi atau dihapus; ensures tamper-evident audit trail. | ISO/IEC 15408 (CC); research-synthesis §4.11 |
| **x402** | HTTP 402 Payment Required protocol pada Base chain; low-friction micropayment standard untuk AI agent services; `@x402/express` middleware untuk data wrapping. | x402 Protocol Specs; research-synthesis §4.10 |

---

## §3 Term Cluster Reference

Untuk membantu navigasi, terms dikelompokkan per tema:

### §3.1 Agent & Society

BDI, Blackboard Pattern, Founder, HARD STOP, Hermes, Hermes Society, POMDP, Namespace-ACL

### §3.2 Runtime & Infrastructure

CQRS, cgroup v2, Discord Bot Application, Event Store, Materialized View, S3, systemd, WORM

### §3.3 Memory & Privacy

Consent Revocation, DEK, Namespace-ACL, Object Lock COMPLIANCE, pgcrypto, Vault

### §3.4 Finance & Wallet

Beancount, Circuit Breaker, MPC, Multisig, Safe Multisig, x402

### §3.5 Self-Evolution & Governance

Ratchet Gate, Hysteresis Ratio, Tier 1-4 permissions (referenced via Ratchet Gate entries)

### §3.6 Standards & Documentation

C4 Model, ISO/IEC 24765, MADR, RTM, SOPS/age

### §3.7 LLM & Reasoning

LLM Gateway, BDI (architectural juga), POMDP

### §3.8 Phase Identifiers

P22.1, P23A, P27 (dan referensi ke phase lainnya di dalam definisi)

---

## §4 Cross-Reference Index

Definisi yang membutuhkan cross-reference ke multiple terms:

| Defined Term | Cross-references |
|---|---|
| Event Store | WORM, Object Lock COMPLIANCE, S3 |
| HARD STOP | Consent Revocation (both binding), Founder (interlocking authority) — ADR-062 disclaimer applies (dev-workflow only) |
| Materialized View | CQRS, Event Store |
| Multisig | Safe Multisig (specific implementation) |
| Namespace-ACL | Blackboard Pattern, Consent Revocation (boundary) |
| pgcrypto | DEK, Vault |
| Ratchet Gate | Hysteresis Ratio, BDI (target of drift detection) |
| Vault | DEK, SOPS/age |
| x402 | Multisig, Circuit Breaker |

---

## §5 Sources and Standards

Glossary ini merujuk kepada:

| Source Type | Examples |
|---|---|
| Internal docs | AGENTS.md, `Persona_Document_v3.1.md`, ADR-053, ADR-054, `ConsentRevocationPolicy_v1.0.md` |
| Research synthesis | research-synthesis.md (Phase 2) sections §4 (15 subsystems), §6 (cross-cutting themes) |
| ISO/IEC | 24765:2017 (Vocabulary), 29148:2018 (Requirements engineering), 15408 (Common Criteria/WORM), 42010 (Architecture description) |
| NIST | SP 800-57 (Key management) |
| Academic | Rao & Georgeff 1995 (BDI), Engelmore & Morgan 1988 (Blackboard), Åström 1965 (POMDP), arXiv 2604.14717 (Layered Mutability) |
| Industry | Discord Developer Docs, AWS S3 Object Lock, Gnosis Safe, Mozilla SOPS, HashiCorp Vault |
| Architecture references | MADR (ADR template), Simon Brown (C4), Michael Nygard (Circuit Breaker), Greg Young (CQRS) |

---

## §6 Footer

### §6.1 Provenance

Glossary ini disintesis dari 15 subsystem list (research-synthesis §4), 9 phase identifiers (P22.1, P23A, P27), dan ISO/IEC 24765:2017 standard structure. 37 terms mencakup coverage complete untuk Phase 4 doc suite.

### §6.2 Coverage Notes

- **Architecture terminology** (CQRS, BDI, POMDP, C4): covered dengan academic + industry reference.
- **Stack-specific** (pgcrypto, systemd, cgroup v2, SOPS/age, Vault): covered dengan product docs.
- **Phase identifiers** (P22.1, P23A, P27): covered dengan ADR reference.
- **Safety/Cross-cutting** (HARD STOP, Consent Revocation, Founder): covered dengan AGENTS.md + policy docs binding.
- **Wallet/Finance** (Safe Multisig, MPC, x402, Beancount): covered dengan industry reference.

### §6.3 ISO 24765 Alignment

Tabel glossary menggunakan 3 fields essential yang mandatory ISO 24765:

- **Term** (entry label, X)
- **Definition** (definisi, X)
- **Source/Reference** (kode referensi, X)

Extended fields (cluster reference, cross-reference index) ditambahkan untuk navigability masterplan-specific.

### §6.4 Bilingual Note

Glossary ini English-only untuk konsistensi dengan ISO/IEC 24765:2017. Indonesian equivalents (kalau ada) akan ditambahkan di Phase 5+ jika diperlukan untuk operator reading dalam Bahasa Indonesia.

### §6.5 Critical Notes

1. **Phase identifiers (P22.1, P23A, P27):** specific ke masterplan; tidak akan overlap dengan phase lain di Guinevere main stack.
2. **x402 → MCP/A2A interoperability:** x402 adalah payment protocol; A2A (Agent-to-Agent, Google LF 2025) adalah peer protocol; MCP (Anthropic LF) adalah tool access. Ketiga adalah framework-stack distinct.
3. **pgcrypto ≠ pgcrypto via PGP library:** PostgreSQL extension PGP-based symmetric/asyymmetric encryption.
4. **Vault ≠ SOPS:** Vault = secrets engine (KEK management); SOPS = file encryption tool. Together both digunakan di Guinevere stack.
5. **Safe Multisig ≠ generic multisig:** Safe adalah Gnosis Safe smart contract wallet; specific implementation.

### §6.6 Catatan Perubahan

| Versi | Tanggal | Penulis | Perubahan |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere | Initial draft. 37 entries alphabetically ordered. ISO/IEC 24765:2017 base structure dengan cluster reference extension. Provenance dari research-synthesis + AGENTS.md + product docs. |

---

> **STRICTLY PRIVATE & CONFIDENTIAL** — Project Guinevere. Glossary bagian dari masterplan P28-P36 Phase 4 Doc Suite (Acceptance Criteria, Risk Register, Glossary triplet). Tunduk pada operating contract AGENTS.md.
