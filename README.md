---
project: "Guinevere"
status: "Aktif"
date: "2026-05-31"
operator: "Faiz"
safe_word: "HARD STOP"
dr_procedure: "docs/40-operations/43-DisasterRecoveryPlan_v1.0.md"
---

# Project Guinevere

> Sistem companion AI otonom dan engineering agent ... Guinevere de Baroque.

---

## Tinjauan Proyek

Guinevere adalah companion AI otonom yang dirancang sebagai partner cerdas dengan memori persisten, persona yang kaya, agent loop mandiri, integrasi surveillance, dan suite dokumentasi enterprise-grade. Sistem ini dibangun untuk satu operator (Faiz) dan beroperasi sebagai entitas yang sadar konteks, mengingat percakapan lintas sesi, serta mampu menjalankan tugas engineering secara otonom.

Kapabilitas utama Guinevere mencakup manajemen memori jangka panjang dengan skema terstruktur, perilaku persona yang dikendalikan melalui safety policy ketat, siklus agent loop 7 fase dengan gate verifikasi di setiap tahap, pengawasan multi-platform (Android, Windows, wearable), dan antarmuka Discord sebagai kanal komunikasi utama. Seluruh perilaku dibatasi oleh consent framework yang memastikan operator selalu memegang kendali penuh.

Proyek ini memprioritaskan keselamatan di atas estetika persona. Setiap interaksi, setiap keputusan otonom, dan setiap integrasi eksternal melewati lapisan validasi keamanan, privasi, dan consent. Safe word `HARD STOP` tersedia kapan saja untuk netralisasi persona secara instan.

---

## Tinjauan Arsitektur

```
┌─────────────────────────────────────────────────────────────────┐
│                     VPS Ubuntu (systemd)                         │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────────┐  │
│  │  PostgreSQL  │◄──►│    Redis     │◄──►│   Hermes Agent    │  │
│  │  (primary)   │    │  (DB0-DB5)   │    │ (GPT-5.5/DeepSeek)│  │
│  └──────────────┘    └──────────────┘    └────────┬──────────┘  │
│                                                    │            │
│  ┌─────────────────────────────────────┐           │            │
│  │        Prometheus + Grafana         │◄──────────┤            │
│  │           + Loki (logs)             │           │            │
│  └─────────────────────────────────────┘           │            │
│                                                    ▼            │
│                                          ┌──────────────────┐  │
│                                          │   Discord Bot    │  │
│                                          │   (interface)    │  │
│                                          └────────┬─────────┘  │
└───────────────────────────────────────────────────┼────────────┘
                                                    │
                          ┌─────────────────────────┼──────────┐
                          │                         ▼          │
                          │    ┌─────────────────────────────┐ │
                          │    │      Surveillance Layer     │ │
                          │    │  Android (Tasker)           │ │
                          │    │  Windows (Python daemon)    │ │
                          │    │  Wearable (future)          │ │
                          │    └─────────────────────────────┘ │
                          └────────────────────────────────────┘
```

---

## Memulai

Lima langkah untuk agent atau operator baru yang bergabung dengan proyek ini:

1. **Baca kontrak operasi agent.** Buka [AGENTS.md](AGENTS.md) untuk memahami bagaimana Guinevere bekerja di repositori ini, termasuk aturan delegasi, verifikasi, dan disiplin file-based output.

2. **Pelajari indeks dokumentasi.** Buka [docs/README.md](docs/README.md) untuk melihat seluruh 37 dokumen aktif, kategori, dan jalur baca yang disarankan sesuai peran.

3. **Pahami konteks bisnis dan produk.** Baca [BRD v2.0](docs/00-core/00-BRD_v2.0.md) dan [PRD v2.2](docs/00-core/01-PRD_v2.2.md) untuk memahami mengapa proyek ini ada dan apa yang dibangun.

4. **Kenali arsitektur sistem.** Baca [Technical Architecture v2.0](docs/00-core/02-TechnicalArchitecture_v2.0.md) untuk memahami desain infrastruktur, komponen, dan aliran data.

5. **Review keputusan arsitektur.** Buka [ADR Index](docs/10-governance/17-ADR_Index_v1.0.md) dan direktori [adr/](adr/) untuk memahami keputusan-keputusan kunci yang sudah diambil.

---

## Struktur Folder

```
guinevere/
├── AGENTS.md                    # Kontrak operasi untuk AI agent di repo ini
├── README.md                    # File ini (README utama proyek)
├── adr/                         # Architecture Decision Records
├── audit-reports/               # Laporan audit dan review
├── docs/                        # Seluruh dokumentasi proyek
│   ├── README.md                # Indeks utama dokumentasi
│   ├── 00-core/                 # Dokumen inti (BRD, PRD, Arsitektur, dll.)
│   ├── 10-governance/           # Kebijakan tata kelola (Charter, SRS, FSD, RTM, dll.)
│   ├── 20-security/             # Keamanan dan kontrol akses
│   ├── 30-data/                 # Tata kelola data dan privasi
│   ├── 40-operations/           # Operasi, keandalan, DR, deployment
│   ├── 50-quality/              # Test plan dan jaminan kualitas
│   ├── 60-persona/              # Spesifik persona (safety, system prompt, UX)
│   ├── 70-finops/               # Operasi keuangan dan model biaya
│   └── _archive/                # Versi lama yang sudah digantikan
├── evidence/                    # Artifact bukti implementasi
├── qa-inputs/                   # Dokumen sumber Q&A
├── research-reports/            # Laporan riset eksternal
└── runbooks/                    # Runbook operasional
    └── dr/                      # Runbook disaster recovery
```

---

## Dokumen Kunci

Sepuluh dokumen terpenting yang menjadi fondasi proyek ini:

| # | Dokumen | Deskripsi |
|---|---|---|
| 1 | [BRD v2.0](docs/00-core/00-BRD_v2.0.md) | Konteks bisnis, tujuan strategis, dan definisi keberhasilan proyek |
| 2 | [PRD v2.2](docs/00-core/01-PRD_v2.2.md) | Fitur produk, perilaku user-facing, dan acceptance criteria |
| 3 | [Technical Architecture v2.0](docs/00-core/02-TechnicalArchitecture_v2.0.md) | Desain sistem, infrastruktur, dan arsitektur layanan |
| 4 | [Agent Loop Spec v2.0](docs/00-core/03-AgentLoopSpec_v2.0.md) | Siklus hidup perilaku otonom 7 fase |
| 5 | [Memory Schema v2.0](docs/00-core/04-MemorySchema_v2.0.md) | Model penyimpanan dan pemanggilan memori |
| 6 | [Persona Document v3.0](docs/00-core/06-Persona_Document_v3.0.md) | Identitas, nada bicara, dan perilaku persona Guinevere |
| 7 | [Security Policy](docs/20-security/20-SecurityPolicy_v1.0.md) | Kebijakan keamanan menyeluruh |
| 8 | [Persona Safety Policy](docs/60-persona/60-PersonaSafetyPolicy_v1.0.md) | Batasan keselamatan perilaku persona |
| 9 | [System Prompt Master](docs/60-persona/61-SystemPromptMaster_v1.1.md) | System prompt yang di-deploy ke model LLM |
| 10 | [ADR Index](docs/10-governance/17-ADR_Index_v1.0.md) | Indeks seluruh keputusan arsitektur yang tercatat |

---

## Stack Teknologi

| Komponen | Teknologi | Catatan |
|---|---|---|
| LLM Primary | GPT-5.5 via 9Router | Context window 1M token, model utama untuk reasoning kompleks |
| LLM Sub-agents | DeepSeek V4 Flash via 9Router | Model cepat dan hemat biaya untuk tugas sub-agent |
| Fallback | Guinevere combo (9Router) | DeepSeek V4 Flash primary via opencode-go; GPT-5.5 secondary via cockpit Tailscale |
| Database | PostgreSQL + Redis (DB0-DB5) | PostgreSQL untuk data persisten, Redis untuk cache dan pub/sub |
| Agent Framework | Hermes Agent (Nous Research) | Framework agent otonom dengan tool-use dan memory |
| Interface | Discord Bot | Kanal komunikasi utama dengan operator |
| Surveillance | Tasker (Android) + Python daemon (Windows) | Pengumpulan data kontekstual multi-platform |
| Browser | Obscura + Playwright | Browser automation untuk web scraping dan verifikasi |
| Secrets | SOPS + age | Enkripsi secrets at rest dengan key management |
| Monitoring | Prometheus + Grafana + Loki | Metrik, dashboard, dan agregasi log |
| Hosting | VPS Ubuntu (systemd) | Self-hosted, dikelola melalui systemd service units |

---

## Ringkasan ADR

Proyek ini mencatat **33 Architecture Decision Records** di direktori [adr/](adr/). Setiap ADR mendokumentasikan konteks, opsi yang dipertimbangkan, keputusan yang diambil, dan konsekuensinya. Lihat [ADR Index](docs/10-governance/17-ADR_Index_v1.0.md) untuk daftar lengkap.

Lima keputusan arsitektur kunci yang paling berdampak pada desain sistem:

| ADR | Keputusan | Dampak |
|---|---|---|
| Model routing | GPT-5.5 sebagai primary, DeepSeek V4 Flash untuk sub-agents | Menentukan biaya, kecepatan, dan kualitas reasoning di seluruh sistem |
| Penyimpanan memori | PostgreSQL untuk data persisten, Redis untuk cache dan real-time | Memengaruhi performa recall, skalabilitas, dan strategi backup |
| Framework agent | Hermes Agent dari Nous Research | Menentukan kapabilitas tool-use, memory management, dan extensibility |
| Enkripsi secrets | SOPS + age untuk secrets at rest | Menetapkan standar keamanan untuk seluruh kredensial dan API key |
| Interface utama | Discord Bot sebagai kanal komunikasi | Memengaruhi UX, notifikasi, dan pola interaksi operator |

---

## Prosedur Darurat

### Safe Word

Ketik `HARD STOP` di kanal Discord kapan saja untuk memicu netralisasi persona secara instan. Guinevere akan menghentikan seluruh perilaku persona dan beralih ke mode netral sampai operator memberikan instruksi selanjutnya.

### Disaster Recovery

Prosedur pemulihan bencana lengkap tersedia di [Disaster Recovery Plan](docs/40-operations/43-DisasterRecoveryPlan_v1.0.md). Dokumen ini mencakup skenario kegagalan, langkah pemulihan, RTO/RPO, dan checklist verifikasi pasca-recovery.

### Incident Response

Untuk insiden aktif, ikuti [Incident Response & Postmortem Runbook](docs/40-operations/42-IncidentResponse_Postmortem_v1.0.md). Runbook ini mencakup klasifikasi severitas, prosedur eskalasi, template komunikasi, dan format postmortem.

### Eskalasi

1. **Sev-1 (Kritis):** Segera hubungi operator. Aktifkan DR procedure jika diperlukan.
2. **Sev-2 (Tinggi):** Dokumentasikan insiden. Eskalasi ke operator dalam 1 jam.
3. **Sev-3 (Sedang):** Catat di incident log. Review pada siklus berikutnya.
4. **Sev-4 (Rendah):** Catat untuk tracking. Tidak perlu eskalasi langsung.

---

## Alur Kerja Dokumentasi

Seluruh dokumentasi mengikuti alur kerja terstruktur untuk menjaga konsistensi dan akurasi:

1. **Pembuatan.** Dokumen baru ditulis sebagai Draft di branch terpisah. Frontmatter diisi dengan metadata lengkap (judul, status, tanggal, owner).

2. **Review.** Draft di-review oleh owner atau auditor yang ditunjuk. Temuan review dicatat di `audit-reports/` sebagai laporan terpisah.

3. **Penerimaan.** Setelah semua temuan review ditangani, status dokumen diubah menjadi "Diterima". Versi mayor ditetapkan (v1.0).

4. **Pemeliharaan.** Dokumen yang sudah diterima di-review minimal setiap 90 hari. Perubahan minor dinaikkan versinya (v1.0 ke v1.1). Perubahan mayor memerlukan review ulang.

5. **Depresiasi dan Arsip.** Ketika dokumen digantikan oleh versi baru, versi lama dipindahkan ke `_archive/` dan statusnya diubah menjadi "Diarsipkan".

---

## Lisensi & Kerahasiaan

**STRICTLY PRIVATE & CONFIDENTIAL**

Seluruh konten dalam repositori ini bersifat rahasia dan merupakan properti eksklusif Project Guinevere. Dilarang menyebarkan, menyalin, memodifikasi, atau menggunakan informasi ini di luar konteks proyek tanpa izin tertulis dari owner (Faiz).

Akses ke repositori ini terbatas pada pihak yang secara eksplisit diberikan wewenang. Setiap akses, modifikasi, dan distribusi tercatat dalam audit trail.

---

## Catatan Perubahan

| Versi | Tanggal | Penulis | Perubahan |
|---|---|---|---|
| 1.0 | 2026-05-31 | Guinevere | README root awal dibuat setelah reorganisasi folder enterprise. |
| 2.0 | 2026-05-31 | Guinevere | Penulisan ulang ke Bahasa Indonesia. Penambahan Tinjauan Arsitektur, Stack Teknologi, Ringkasan ADR, Prosedur Darurat, dan Alur Kerja Dokumentasi. |
