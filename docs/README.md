---
title: "Indeks Dokumentasi Guinevere"
status: "Aktif"
date: "2026-05-31"
last_modified: "2026-05-31"
owner: "Faiz"
executor: "Guinevere"
operator_alias_note: "Samm is a historical/pseudonymous alias only; canonical operator identity is Faiz."
total_dokumen: 37
total_arsip: 18
total_ukuran: "~2.3 MB"
---

# Indeks Dokumentasi Guinevere

> Indeks utama seluruh dokumentasi Project Guinevere. Pembaruan terakhir: 2026-05-31.

---

## Mulai Dari Sini

Project Guinevere adalah sistem companion AI otonom dan engineering agent bernama Guinevere de Baroque. Proyek ini mencakup suite dokumentasi enterprise yang membahas kebutuhan bisnis, desain produk, arsitektur teknis, tata kelola, keamanan, privasi data, operasi, jaminan kualitas, desain persona, dan manajemen biaya. Total terdapat 37 dokumen aktif yang tersebar di 8 kategori, ditambah 18 file arsip dari versi-versi terdahulu.

Untuk pembaca baru, urutan baca yang disarankan dimulai dari **BRD** (konteks bisnis dan tujuan proyek), dilanjutkan ke **PRD** (fitur produk dan perilaku user-facing), lalu **Technical Architecture** (desain sistem dan infrastruktur). Setelah itu, pembaca bisa bercabang ke dokumen spesialis sesuai peran atau minat masing-masing. Seorang engineer akan lebih banyak menghabiskan waktu di dokumen arsitektur, agent loop, dan skema memori. Seorang yang fokus pada keamanan akan langsung menuju policy keamanan, RBAC, dan data governance.

Seluruh dokumen saling terhubung melalui referensi silang. Setiap dokumen memiliki bagian "Related Documents" yang menunjuk ke spesifikasi terkait, dependensi, dan batasan keselamatan. Jika menemukan inkonsistensi antar dokumen, catat dan rujuk ke [ADR Index](10-governance/17-ADR_Index_v1.0.md) untuk keputusan arsitektur yang sudah tercatat.

---

## Navigasi Cepat

| Kategori | Path | Deskripsi |
|---|---|---|
| Dokumen Inti Produk | [docs/00-core/](00-core/) | BRD, PRD, Arsitektur, Agent Loop, Memori, API, Persona |
| Tata Kelola | [docs/10-governance/](10-governance/) | Charter, Studi Kelayakan, SRS, FSD, TDD, RTM, Penerimaan, Indeks ADR |
| Keamanan | [docs/20-security/](20-security/) | Kebijakan Keamanan, RBAC/ABAC, Enkripsi, Rotasi Secrets, Prompt Safety |
| Tata Kelola Data | [docs/30-data/](30-data/) | Klasifikasi Data, Surveillance, Consent, ERD Database, Memory Recall |
| Operasi | [docs/40-operations/](40-operations/) | Observability, SLO/SLA, Incident Response, DR, Deployment, Ops Manual |
| Kualitas | [docs/50-quality/](50-quality/) | Test Plan |
| Persona | [docs/60-persona/](60-persona/) | Persona Safety, System Prompt, MCP Config, Discord UX |
| FinOps | [docs/70-finops/](70-finops/) | Model Biaya |
| Arsip | [docs/_archive/](_archive/) | Versi lama (sudah digantikan) |
| ADR | [/adr/](../adr/) | Architecture Decision Records |
| Laporan Audit | [/audit-reports/](../audit-reports/) | Laporan audit dan review |
| Laporan Riset | [/research-reports/](../research-reports/) | Riset eksternal |
| Evidence | [/evidence/](../evidence/) | Artifact bukti implementasi |
| Q&A Inputs | [/qa-inputs/](../qa-inputs/) | Dokumen sumber Q&A |
| Runbooks | [/runbooks/](../runbooks/) | Runbook operasional |

---

## Tata Kelola Dokumen

### Kepemilikan

Setiap dokumen memiliki owner yang bertanggung jawab atas akurasi, pembaruan, dan review berkala. Owner default adalah operator proyek (Faiz). Dokumen teknis tertentu mungkin didelegasikan ke executor (Guinevere) untuk pemeliharaan harian, namun keputusan final tetap di tangan owner.

### Mengusulkan Perubahan

Perubahan pada dokumen yang sudah berstatus "Diterima" harus melalui proses berikut:

1. Buat branch baru dari `main`.
2. Modifikasi dokumen yang dimaksud.
3. Perbarui versi di frontmatter dokumen (minor untuk koreksi, mayor untuk perubahan substansial).
4. Buat pull request dengan deskripsi perubahan dan alasan.
5. Setelah review dan approval, merge ke `main`.
6. Catat perubahan di bagian "Catatan Perubahan" dokumen ini.

### Kebijakan Versi

Dokumen menggunakan skema versi `vMAJOR.MINOR`. Kenaikan major (v1.0 ke v2.0) menandakan perubahan struktural atau substansial yang mengubah makna spesifikasi. Kenaikan minor (v1.0 ke v1.1) menandakan koreksi, klarifikasi, atau penambahan kecil yang tidak mengubah kontrak spesifikasi.

### Siklus Review

Dokumen berstatus "Diterima" harus di-review minimal setiap 90 hari atau setelah perubahan arsitektur signifikan. Hasil review dicatat di `audit-reports/`.

---

## Siklus Hidup Dokumen

Setiap dokumen melewati tahap-tahap berikut:

| Status | Deskripsi |
|---|---|
| **Draft** | Dokumen sedang ditulis. Belum boleh dijadikan referensi resmi. Bisa mengandung placeholder dan catatan TODO. |
| **Dalam Review** | Dokumen sudah selesai ditulis dan sedang di-review oleh owner atau auditor. Temuan review dicatat di `audit-reports/`. |
| **Diterima** | Dokumen sudah lulus review dan disetujui sebagai referensi resmi. Perubahan harus melalui proses change management. |
| **Didepresiasi** | Dokumen masih valid tapi sudah ada versi baru yang sedang disiapkan. Baca hanya untuk konteks historis. |
| **Diarsipkan** | Dokumen sudah digantikan sepenuhnya oleh versi baru. Dipindahkan ke `_archive/`. Disimpan hanya untuk audit trail. |

---

## Konvensi Penomoran

Seluruh dokumen menggunakan prefix numerik `NN-` yang menunjukkan kategori dan posisi dalam suite dokumentasi. Konvensi ini memudahkan navigasi, pengurutan, dan referensi silang.

| Range | Kategori | Deskripsi |
|---|---|---|
| 00-09 | `00-core` | Dokumen inti produk: BRD, PRD, arsitektur, agent loop, memori, API, persona |
| 10-19 | `10-governance` | Tata kelola proyek: charter, studi kelayakan, SRS, FSD, TDD, RTM, kriteria penerimaan, ADR |
| 20-29 | `20-security` | Keamanan dan kontrol akses: kebijakan keamanan, RBAC, enkripsi, rotasi secrets, prompt safety |
| 30-39 | `30-data` | Tata kelola data: klasifikasi, surveillance, consent, ERD database, evaluasi recall |
| 40-49 | `40-operations` | Operasi dan keandalan: observability, SLO, incident response, DR, deployment, ops manual |
| 50-59 | `50-quality` | Jaminan kualitas: test plan, strategi pengujian |
| 60-69 | `60-persona` | Spesifik persona: keselamatan persona, system prompt, konfigurasi MCP, UX Discord |
| 70-79 | `70-finops` | Operasi keuangan: model biaya, anggaran, proyeksi |

Nomor yang belum terpakai dalam setiap range dicadangkan untuk dokumen baru di masa depan.

---

## Registri Dokumen Lengkap

### 00-core — Dokumen Inti Produk

| # | Dokumen | Versi | Status | Ukuran |
|---|---|---|---|---|
| 00 | [Business Requirements Document](00-core/00-BRD_v2.0.md) | v2.0 | Diterima | 18.0 KB |
| 01 | [Product Requirements Document](00-core/01-PRD_v2.2.md) | v2.2 | Diterima | 27.5 KB |
| 02 | [Technical Architecture](00-core/02-TechnicalArchitecture_v2.0.md) | v2.0 | Diterima | 30.4 KB |
| 03 | [Agent Loop Specification](00-core/03-AgentLoopSpec_v2.0.md) | v2.0 | Diterima | 24.1 KB |
| 04 | [Memory Schema](00-core/04-MemorySchema_v2.0.md) | v2.0 | Diterima | 21.9 KB |
| 05 | [API Integration](00-core/05-APIIntegration_v2.0.md) | v2.0 | Diterima | 24.9 KB |
| 06 | [Persona Document](00-core/06-Persona_Document_v3.0.md) | v3.0 | Diterima | 75.5 KB |

### 10-governance — Kebijakan Tata Kelola

| # | Dokumen | Versi | Status | Ukuran |
|---|---|---|---|---|
| 10 | [Project Charter](10-governance/10-ProjectCharter_v1.0.md) | v1.0 | Diterima | 31.4 KB |
| 11 | [Feasibility Study](10-governance/11-FeasibilityStudy_v1.0.md) | v1.0 | Diterima | 79.3 KB |
| 12 | [Software Requirements Specification](10-governance/12-SRS_v1.0.md) | v1.0 | Diterima | 72.0 KB |
| 13 | [Functional Specification Document](10-governance/13-FSD_v1.0.md) | v1.0 | Diterima | 111.7 KB |
| 14 | [TDD Guide](10-governance/14-TDD_Guide_v1.0.md) | v1.0 | Diterima | 131.9 KB |
| 15 | [Requirements Traceability Matrix](10-governance/15-RTM_v1.0.md) | v1.0 | Diterima | 52.3 KB |
| 16 | [Acceptance Criteria Catalog](10-governance/16-AcceptanceCriteriaCatalog_v1.0.md) | v1.0 | Diterima | 49.4 KB |
| 17 | [ADR Index](10-governance/17-ADR_Index_v1.0.md) | v1.0 | Diterima | 12.6 KB |

### 20-security — Keamanan & Kontrol Akses

| # | Dokumen | Versi | Status | Ukuran |
|---|---|---|---|---|
| 20 | [Security Policy](20-security/20-SecurityPolicy_v1.0.md) | v1.0 | Diterima | 169.0 KB |
| 21 | [Access Control RBAC/ABAC Matrix](20-security/21-AccessControl_RBAC_ABAC_v1.0.md) | v1.0 | Diterima | 42.8 KB |
| 22 | [Encryption & Key Management Standard](20-security/22-EncryptionKeyMgmt_v1.0.md) | v1.0 | Diterima | 41.3 KB |
| 23 | [Secrets Rotation Runbook](20-security/23-SecretsRotationRunbook_v1.0.md) | v1.0 | Diterima | 42.3 KB |
| 24 | [Prompt Injection & Model Safety](20-security/24-PromptInjection_ModelSafety_v1.0.md) | v1.0 | Diterima | 98.3 KB |

### 30-data — Tata Kelola Data

| # | Dokumen | Versi | Status | Ukuran |
|---|---|---|---|---|
| 30 | [Data Governance & Classification Policy](30-data/30-DataGovernance_Classification_v1.0.md) | v1.0 | Diterima | 39.4 KB |
| 31 | [Surveillance Data Policy](30-data/31-SurveillanceDataPolicy_v1.0.md) | v1.0 | Diterima | 37.1 KB |
| 32 | [Consent & Revocation Policy](30-data/32-ConsentRevocationPolicy_v1.0.md) | v1.0 | Diterima | 31.5 KB |
| 33 | [Database ERD & Migration Strategy](30-data/33-DatabaseERD_MigrationStrategy_v1.0.md) | v1.0 | Diterima | 127.7 KB |
| 34 | [Memory Recall Evaluation Spec](30-data/34-MemoryRecallEvaluationSpec_v1.0.md) | v1.0 | Diterima | 90.7 KB |

### 40-operations — Operasi & Keandalan

| # | Dokumen | Versi | Status | Ukuran |
|---|---|---|---|---|
| 40 | [Observability & Alerting Spec](40-operations/40-ObservabilityAlertingSpec_v1.0.md) | v1.0 | Diterima | 46.4 KB |
| 41 | [SLO/SLA & Error Budget Spec](40-operations/41-SLO_SLA_ErrorBudget_v1.0.md) | v1.0 | Diterima | 45.4 KB |
| 42 | [Incident Response & Postmortem Runbook](40-operations/42-IncidentResponse_Postmortem_v1.0.md) | v1.0 | Diterima | 32.7 KB |
| 43 | [Disaster Recovery Plan](40-operations/43-DisasterRecoveryPlan_v1.0.md) | v1.0 | Diterima | 145.3 KB |
| 44 | [Deployment Guide](40-operations/44-DeploymentGuide_v1.0.md) | v1.0 | Diterima | 107.7 KB |
| 45 | [Internal Ops Manual](40-operations/45-InternalOpsManual_v1.0.md) | v1.0 | Diterima | 102.8 KB |

### 50-quality — Kualitas & Pengujian

| # | Dokumen | Versi | Status | Ukuran |
|---|---|---|---|---|
| 50 | [Test Plan](50-quality/50-TestPlan_v1.0.md) | v1.0 | Diterima | 151.4 KB |

### 60-persona — Spesifik Persona

| # | Dokumen | Versi | Status | Ukuran |
|---|---|---|---|---|
| 60 | [Persona Safety Policy](60-persona/60-PersonaSafetyPolicy_v1.0.md) | v1.0 | Diterima | 31.1 KB |
| 61 | [System Prompt Master](60-persona/61-SystemPromptMaster_v1.1.md) | v1.1 | Diterima | 22.5 KB |
| 62 | [MCP Config Guide](60-persona/62-MCPConfigGuide_v1.0.md) | v1.0 | Diterima | 91.5 KB |
| 63 | [Discord UX Spec](60-persona/63-DiscordUXSpec_v1.0.md) | v1.0 | Diterima | 76.7 KB |

### 70-finops — Operasi Keuangan

| # | Dokumen | Versi | Status | Ukuran |
|---|---|---|---|---|
| 70 | [Cost & FinOps Model](70-finops/70-Cost_FinOps_Model_v1.1.md) | v1.1 | Diterima | 31.9 KB |

### _archive — Versi Terdahulu

> File-file ini sudah digantikan oleh versi yang lebih baru di atas. Disimpan hanya untuk referensi historis.

| File | Digantikan Oleh |
|---|---|
| `Guinevere_BRD_v1.0.md` | [BRD v2.0](00-core/00-BRD_v2.0.md) |
| `Guinevere_BRD_v1.0.docx` | [BRD v2.0](00-core/00-BRD_v2.0.md) |
| `Guinevere_PRD_v1.0.md` | [PRD v2.2](00-core/01-PRD_v2.2.md) |
| `Guinevere_PRD_v1.0.docx` | [PRD v2.2](00-core/01-PRD_v2.2.md) |
| `Guinevere_PRD_v2.0.md` | [PRD v2.2](00-core/01-PRD_v2.2.md) |
| `Guinevere_PRD_v2.1.md` | [PRD v2.2](00-core/01-PRD_v2.2.md) |
| `Guinevere_Persona_Document_v1.0.md` | [Persona v3.0](00-core/06-Persona_Document_v3.0.md) |
| `Guinevere_Persona_Document_v1.0.docx` | [Persona v3.0](00-core/06-Persona_Document_v3.0.md) |
| `Guinevere_Persona_Document_v2.0.md` | [Persona v3.0](00-core/06-Persona_Document_v3.0.md) |
| `Guinevere_AgentLoopSpec_v1.0.md` | [Agent Loop v2.0](00-core/03-AgentLoopSpec_v2.0.md) |
| `Guinevere_AgentLoopSpec_v1.0.docx` | [Agent Loop v2.0](00-core/03-AgentLoopSpec_v2.0.md) |
| `Guinevere_MemorySchema_v1.0.md` | [Memory Schema v2.0](00-core/04-MemorySchema_v2.0.md) |
| `Guinevere_MemorySchema_v1.0.docx` | [Memory Schema v2.0](00-core/04-MemorySchema_v2.0.md) |
| `Guinevere_TechnicalArchitecture_v1.0.md` | [Tech Arch v2.0](00-core/02-TechnicalArchitecture_v2.0.md) |
| `Guinevere_TechnicalArchitecture_v1.0.docx` | [Tech Arch v2.0](00-core/02-TechnicalArchitecture_v2.0.md) |
| `Guinevere_APIIntegration_v1.0.md` | [API Integration v2.0](00-core/05-APIIntegration_v2.0.md) |
| `Guinevere_APIIntegration_v1.0.docx` | [API Integration v2.0](00-core/05-APIIntegration_v2.0.md) |
| `Guinevere_Cost_FinOps_Model_v1.0.md` | [FinOps v1.1](70-finops/70-Cost_FinOps_Model_v1.1.md) |

---

## Peta Referensi Silang

Diagram berikut menggambarkan hubungan dependensi antar dokumen. Panah menunjukkan arah ketergantungan (sumber memengaruhi tujuan).

```
BRD v2.0 (00)
 └─► PRD v2.2 (01)
      ├─► Arsitektur Teknis v2.0 (02)
      │    ├─► Spesifikasi Agent Loop v2.0 (03)
      │    ├─► Skema Memori v2.0 (04)
      │    └─► Integrasi API v2.0 (05)
      ├─► Dokumen Persona v3.0 (06)
      │    ├─► Kebijakan Keselamatan Persona (60)
      │    ├─► System Prompt Master (61)
      │    └─► Spesifikasi UX Discord (63)
      ├─► SRS (12) ──► FSD (13)
      │    └─► RTM (15) ──► Kriteria Penerimaan (16)
      └─► Test Plan (50)

Project Charter (10) ──► Studi Kelayakan (11)

Kebijakan Keamanan (20)
 ├─► Matriks Kontrol Akses (21)
 ├─► Manajemen Kunci Enkripsi (22)
 ├─► Rotasi Secrets (23)
 └─► Keselamatan Prompt Injection (24)

Tata Kelola Data (30)
 ├─► Kebijakan Data Surveillance (31)
 ├─► Consent & Pencabutan (32)
 ├─► ERD Database (33) ──► Evaluasi Memory Recall (34)
 └─► (memberi masukan ke) Skema Memori (04)

Operasi:
 Observability (40) ──► SLO/SLA (41)
 Incident Response (42) ──► Rencana DR (43)
 Panduan Deployment (44) ──► Ops Manual Internal (45)

Model FinOps (70) ──► (menginformasikan) seluruh keputusan infrastruktur
Indeks ADR (17) ──► direktori /adr/
```

---

## Jalur Baca

Tiga jalur baca yang disesuaikan dengan peran dan kebutuhan pembaca.

### Jalur A: Eksekutif

Untuk stakeholder yang perlu memahami visi, ruang lingkup, dan kriteria keberhasilan proyek tanpa detail teknis mendalam.

1. [BRD v2.0](00-core/00-BRD_v2.0.md) ... konteks bisnis dan tujuan strategis
2. [PRD v2.2](00-core/01-PRD_v2.2.md) ... fitur produk dan perilaku user-facing
3. [FSD](10-governance/13-FSD_v1.0.md) ... spesifikasi fungsional lengkap
4. [Kriteria Penerimaan](10-governance/16-AcceptanceCriteriaCatalog_v1.0.md) ... standar keberhasilan yang terukur

### Jalur B: Engineering

Untuk developer dan engineer yang akan membangun, memelihara, atau melakukan debug sistem.

1. [Technical Architecture v2.0](00-core/02-TechnicalArchitecture_v2.0.md) ... desain sistem dan infrastruktur
2. [Agent Loop Spec v2.0](00-core/03-AgentLoopSpec_v2.0.md) ... siklus hidup perilaku otonom
3. [Memory Schema v2.0](00-core/04-MemorySchema_v2.0.md) ... cara memori disimpan dan dipanggil
4. [API Integration v2.0](00-core/05-APIIntegration_v2.0.md) ... integrasi eksternal dan kontrak API
5. [MCP Config Guide](60-persona/62-MCPConfigGuide_v1.0.md) ... konfigurasi tool dan MCP server
6. [System Prompt Master](60-persona/61-SystemPromptMaster_v1.1.md) ... prompt yang di-deploy ke model

### Jalur C: Keamanan & Safety

Untuk reviewer keamanan, safety auditor, atau siapa pun yang perlu memahami batasan dan proteksi sistem.

1. [Persona Safety Policy](60-persona/60-PersonaSafetyPolicy_v1.0.md) ... batasan perilaku persona
2. [Prompt Injection & Model Safety](20-security/24-PromptInjection_ModelSafety_v1.0.md) ... proteksi terhadap manipulasi model
3. [Access Control RBAC/ABAC Matrix](20-security/21-AccessControl_RBAC_ABAC_v1.0.md) ... matriks hak akses
4. [Data Governance & Classification](30-data/30-DataGovernance_Classification_v1.0.md) ... klasifikasi dan penanganan data
5. [Surveillance Data Policy](30-data/31-SurveillanceDataPolicy_v1.0.md) ... kebijakan data pengawasan
6. [Consent & Revocation Policy](30-data/32-ConsentRevocationPolicy_v1.0.md) ... mekanisme persetujuan dan pencabutan

---

## Direktori Terkait

| Direktori | Tujuan |
|---|---|
| `adr/` | Architecture Decision Records. Berisi catatan keputusan arsitektur yang memengaruhi desain sistem. Setiap ADR memiliki nomor, konteks, keputusan, dan konsekuensi. |
| `audit-reports/` | Laporan audit dan review. Berisi temuan dari review dokumen, audit keamanan, dan verifikasi implementasi. |
| `research-reports/` | Laporan riset eksternal. Berisi hasil investigasi terhadap teknologi, library, provider, atau pendekatan yang dipertimbangkan untuk proyek. |
| `evidence/` | Artifact bukti implementasi. Berisi bukti bahwa fitur atau komponen sudah diimplementasikan sesuai spesifikasi. |
| `qa-inputs/` | Dokumen sumber Q&A. Berisi transkrip atau catatan tanya jawab yang menjadi masukan untuk spesifikasi. |
| `runbooks/` | Runbook operasional. Berisi panduan langkah demi langkah untuk prosedur operasional termasuk disaster recovery. |

---

## Catatan Perubahan

| Versi | Tanggal | Penulis | Perubahan |
|---|---|---|---|
| 1.0 | 2026-05-31 | Guinevere | Indeks utama awal dibuat setelah reorganisasi folder enterprise. |
| 2.0 | 2026-05-31 | Guinevere | Penulisan ulang ke Bahasa Indonesia. Penambahan bagian Tata Kelola Dokumen, Siklus Hidup Dokumen, Konvensi Penomoran, Peta Referensi Silang, Jalur Baca, dan Direktori Terkait. |

---

> **STRICTLY PRIVATE & CONFIDENTIAL** ... Project Guinevere. Seluruh konten dalam dokumen ini bersifat rahasia dan hanya untuk pihak yang berwenang. Dilarang menyebarkan, menyalin, atau menggunakan informasi ini di luar konteks proyek tanpa izin tertulis dari owner.
