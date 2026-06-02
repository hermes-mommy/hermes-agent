👑

**GUINEVERE DE BAROQUE**

*Feasibility Study*

Technical, Economic & Operational Viability Assessment

Version 1.0 | Project Guinevere | STRICTLY PRIVATE & CONFIDENTIAL

Last Updated: 2026-05-30

Canonical Decisions Applied: Primary LLM GPT-5.5 via 9Router with 1M context window; sub-agent LLM DeepSeek V4 Flash via 9Router; all LLM routing through 9Router primary with OpenRouter as secondary fallback; memory PostgreSQL primary + Redis cache, no SQLite; SDLC 7 phases; OpenCode fully replaced by Guinevere MCP native; Prometheus + Grafana on primary VPS first; wearable integrations post-MVP; browser automation uses obscura primary + Playwright fallback; public endpoint via Cloudflare Tunnel for Discord webhook; self-hosted PostgreSQL (not managed); 9Router (primary) → OpenRouter (secondary) → Ollama local (third-level) → Graceful Degradation (no LLM, basic Discord commands only); automated testing + rollback for self-modification.

Owner: Faiz | Built on Hermes Agent by Nous Research

## Related Documents

| Document | Relationship |
|---|---|
| `Guinevere_BRD_v2.0.md` | Business objectives, problem statement, success metrics, and project scope that this study evaluates for feasibility. |
| `Guinevere_TechnicalArchitecture_v2.0.md` | Defines runtime architecture, service topology, technology stack, and infrastructure that Section A assesses. |
| `Guinevere_APIIntegration_v2.0.md` | Defines all external integrations, SDKs, and API contracts evaluated for technical and economic feasibility. |
| `Guinevere_AgentLoopSpec_v2.0.md` | Defines the 7-phase autonomous SDLC loop assessed for operational viability in Section C. |
| `Guinevere_MemorySchema_v2.0.md` | Defines PostgreSQL + Redis memory architecture assessed for technical and cost feasibility. |
| `Guinevere_Cost_FinOps_Model_v1.0.md` | Defines the $30/month budget and cost governance that Section B validates. |
| `Guinevere_SLO_SLA_ErrorBudgetSpec_v1.0.md` | Defines reliability targets (99.5% SLO, 99.9% aspiration) that Section A and C assess achievability of. |
| `Guinevere_ADR_Index_v1.0.md` | 29 Accepted ADRs forming the canonical decision register that this study must not contradict. |
| `Guinevere_SRS_v1.0.md` | Downstream requirements specification derived from feasibility findings; 120 FR + 50 NFR + 40 IR. |
| `Guinevere_FSD_v1.0.md` | Downstream functional specifications implementing feasible requirements across 9 subsystems. |
| `Guinevere_PRD_v2.2.md` | Upstream product features and user-facing behavior validated for feasibility in this study. |
| `Guinevere_Persona_Document_v2.0.md` | Canonical persona identity and mood taxonomy assessed for operational viability in Section C. |
| `Guinevere_PersonaSafetyPolicy_v1.0.md` | Safety boundaries and drift governance validated as technically feasible in Section A and C. |
| `Guinevere_ConsentRevocationPolicy_v1.0.md` | Consent taxonomy and revocation workflows validated for surveillance subsystem feasibility. |

---

## Executive Summary

Dokumen ini memberikan penilaian kelayakan komprehensif untuk Project Guinevere — autonomous AI companion dan engineering agent system yang berjalan 24/7 di VPS hostdata.id untuk single user (Faiz). Penilaian mencakup tiga dimensi:

- **Section A: Technical Viability** — menilai apakah setiap komponen teknologi (agent framework, LLM routing, memory architecture, surveillance, browser automation, monitoring, dan integrasi) layak diimplementasi dengan teknologi dan infrastruktur yang tersedia.
- **Section B: Economic Viability** — menilai apakah seluruh sistem dapat beroperasi dalam batas $30/bulan dengan alokasi cost yang realistis.
- **Section C: Operational & Risk** — menilai kesiapan operasional, risk register, strategi mitigasi, deployment safety, dan self-modification governance.

**Overall Verdict: FEASIBLE** — dengan beberapa kondisi yang harus dipenuhi sebelum go-live, sebagaimana dirinci di setiap subsection.

---

## SECTION A: TECHNICAL VIABILITY

### Related Documents

| Document | Relationship |
|---|---|
| `Guinevere_TechnicalArchitecture_v2.0.md` | Primary source for all technology stack, service architecture, and infrastructure decisions. |
| `Guinevere_APIIntegration_v2.0.md` | Defines all external APIs, SDKs, and integration contracts. |
| `Guinevere_AgentLoopSpec_v2.0.md` | Defines SDLC loop architecture and parallel execution model. |
| `Guinevere_MemorySchema_v2.0.md` | Defines database schema and memory pipeline architecture. |
| `Guinevere_ADR_Index_v1.0.md` | Canonical decisions governing technology selection (ADR-004 through ADR-022). |

---

### 1. Agent Framework — Hermes Agent v0.14.0+

**Current State Assessment**

Hermes Agent oleh Nous Research adalah open-source autonomous agent framework yang menyediakan core runtime untuk memory management, skill curation, Discord integration, dan MCP tool layer. Versi v0.14.0+ dipilih sebagai base framework karena kompatibilitas Python 3.12 dan arsitektur plugin-based yang cocok untuk custom Guinevere persona dan plugins.

**Evidence from Corpus**

| Source | Evidence |
|---|---|
| Technical Architecture §1.2 | Hermes Agent v0.14.0+ sebagai core autonomous agent runtime. |
| Technical Architecture §3.2 | Directory structure menunjukkan custom plugin architecture di atas Hermes Agent base. |
| API Integration §11.1 | `hermes-agent>=0.14.0` sebagai core dependency di pyproject.toml. |
| BRD §4.2 | Hermes Agent native Discord adapter sebagai primary communication channel. |

**Feasibility Verdict: FEASIBLE**

Hermes Agent memenuhi semua requirement dasar: Python 3.12 compatible, plugin architecture, Discord integration native, MCP tool support, dan skill curation system. Custom Guinevere persona, mood engine, punishment/reward system, dan surveillance receiver dapat dibangun sebagai plugin di atas base framework tanpa fork.

**Risks**

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Hermes Agent development stalls oleh Nous Research | LOW | HIGH | Guinevere maintain fork internal; plugin architecture isolasi dari breaking changes upstream. |
| Breaking API changes di versi baru | MEDIUM | MEDIUM | Pin versi di pyproject.toml; test di staging sebelum upgrade; ADR-016 governs deployment safety. |
| Framework tidak support semua custom requirements | LOW | MEDIUM | Plugin architecture memisahkan Guinevere-specific logic; fallback ke standalone FastAPI services jika diperlukan. |

---

### 2. LLM Architecture — GPT-5.5 via 9Router

**Current State Assessment**

GPT-5.5 via 9Router adalah primary LLM dengan 1M token context window. Model ini digunakan untuk Guinevere core persona, reasoning, planning, dan high-stakes synthesis. 9Router berjalan sebagai systemd service di VPS dan route semua LLM calls melalui single routing layer.

**Evidence from Corpus**

| Source | Evidence |
|---|---|
| ADR-004 | Primary LLM GPT-5.5 via 9Router dengan 1M context window — Accepted. |
| ADR-005 | All LLM routing melalui 9Router; no OpenRouter fallback — Accepted. |
| Technical Architecture §4.1 | GPT-5.5 untuk core persona + reasoning + complex coding; DeepSeek V4 Flash untuk sub-agents. |
| Technical Architecture §4.3 | Context injection total ~6K tokens dari 1M available — plenty of room. |
| Cost/FinOps §5.1 | GPT-5.5 reserved untuk core reasoning, planning, high-stakes synthesis only. |

**1M Context Window Adequacy**

Memory injection pipeline (MemorySchema §8.1) membutuhkan ~8,300 tokens untuk full context assembly. Dengan 1M context window, tersisa ~991,700 tokens untuk conversation history, code analysis, dan task execution. Ini lebih dari cukup bahkan untuk deep code review pada codebase besar.

| Injection Layer | Tokens | Percentage of 1M |
|---|---:|---:|
| Core persona | ~2,000 | 0.2% |
| Current mood | ~200 | 0.02% |
| Persona drift | ~500 | 0.05% |
| Faiz profile | ~1,000 | 0.1% |
| Violation/reward | ~300 | 0.03% |
| Task context | ~500 | 0.05% |
| Surveillance context | ~300 | 0.03% |
| Memory (semantic) | ~1,000 | 0.1% |
| Working memory | ~2,000 | 0.2% |
| **Total Injection** | **~7,800** | **0.78%** |
| **Remaining** | **~992,200** | **99.22%** |

**Feasibility Verdict: FEASIBLE**

GPT-5.5 via 9Router dengan 1M context window secara teknis layak dan memberikan margin yang sangat besar untuk deep context injection, long code analysis, dan multi-turn reasoning. 9Router sebagai routing layer memberikan single point of control untuk model switching dan cost tracking.

**Risks**

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| GPT-5.5 API deprecation atau perubahan | LOW | CRITICAL | ADR-005 governs failover; OpenRouter secondary fallback; Ollama third-level fallback; graceful degradation jika semuanya down; DeepSeek V4 Flash sebagai degraded mode. |
| 9Router latency spike | MEDIUM | MEDIUM | tenacity retry dengan exponential backoff (API Integration §2.2); p95 SLO <= 20s (SLO-SLA §6.2). |
| Context window underutilization waste | LOW | LOW | Cost governance di Cost/FinOps §5.2 membatasi token usage per task type. |

---

### 3. LLM Router Outage — Three-Tier Fallback with Graceful Degradation

**Current State Assessment**

Keputusan terbaru (ADR-028 v3.0): Guinevere menggunakan four-tier failover architecture — 9Router sebagai primary, OpenRouter sebagai secondary fallback, Ollama local sebagai third-level fallback, dan graceful degradation sebagai ultimate last resort. Ollama berjalan di VPS dengan lightweight model (Phi-3-mini atau Mistral-7B quantized), RAM-capped at 4GB, memberikan degraded but functional inference ketika kedua cloud router down.

**Evidence from Corpus**

| Source | Evidence |
|---|---|
| ADR-028 v3.0 | Four-tier failover: 9Router → OpenRouter → Ollama local → Graceful Degradation. Ollama accepted as third-level fallback with resource constraints. |
| ADR-005 (amended) | All LLM routing through 9Router primary; OpenRouter now accepted as secondary router; Ollama as third-level (implicitly amended by ADR-028 v3.0). |
| Technical Architecture §4.1 | Outage policy: four-tier failover → graceful degradation. Health check cycle 30s untuk automatic recovery. Ollama service lifecycle managed via systemd. |
| Cost/FinOps §5.1 | Ollama = $0 additional cost (free, open-source, runs on existing VPS hardware). Graceful degradation = $0 additional cost. |

**Failover Chain**

```text
9Router (primary, GPT-5.5 + DeepSeek V4 Flash)
     ↓ (9Router fails — health check detects)
OpenRouter (secondary, alternative routing)
     ↓ (OpenRouter juga fails — health check detects)
Ollama local (third-level, lightweight model, degraded persona, RAM-capped 4GB)
     ↓ (Ollama juga fails — health check detects)
Graceful Degradation Mode (no LLM, basic Discord, persona suspended)
     ↓ (any provider restores — 30s health check cycle)
Automatic Recovery → queue processing → state restoration
```

**Tier 3: Ollama Local — Behavior Specification**

| Component | Behavior During Ollama Fallback |
|---|---|
| Persona engine | **Degraded** — basic conversational responses, no mood tracking, no yandere intensity, no relationship modeling |
| Agent loop (7-phase SDLC) | **Paused** — current phase state saved, resumes on Tier 1/2 recovery |
| Discord interface | **Basic commands + degraded persona** — status check, help, basic Guinevere responses |
| Memory system | **Read-only** — can recall existing memories, cannot write new ones requiring LLM |
| Surveillance ingestion | **Queued** — events buffered to PostgreSQL queue, processed on recovery |
| Task queue | **Accumulating** — new tasks accepted and queued; execution deferred |
| Monitoring (Prometheus/Grafana) | **Active** — continues monitoring; Ollama health checks every 30s |
| Ollama service | **Active** — guinevere-ollama.service running; auto-stopped on Tier 1/2 recovery |

**Ollama Configuration Constraints**

| Parameter | Value | Rationale |
|---|---|---|
| Model | Phi-3-mini-4k-instruct-Q4_K_M or Mistral-7B-Instruct-v0.3-Q4_K_M | Best quality-to-RAM ratio on 4C/16GB VPS |
| RAM Cap | 4GB (via OLLAMA_MAX_LOADED_MODELS=1, num_thread=4) | Leave 12GB for PostgreSQL, Redis, core services |
| Context Window | 4096 tokens | Match Phi-3-mini capacity; insufficient for complex tasks |
| Service | guinevere-ollama.service (systemd) | Isolated lifecycle management |
| Auto-start | Only on Tier 3 entry | Ollama service stopped during normal operations to conserve RAM |
| Auto-stop | On Tier 1/2 recovery | Release RAM when cloud LLM restores |

**Tier 4: Graceful Degradation Mode — Behavior Specification (Ultimate Last Resort)**

When all three LLM tiers (9Router, OpenRouter, Ollama) are simultaneously unavailable:

| Component | Behavior During Degradation |
|---|---|
| Persona engine | **Suspended** — no persona responses, no yandere states, no emotional modeling |
| Agent loop (7-phase SDLC) | **Paused** — current phase state saved, resumes on recovery |
| Discord interface | **Basic commands only** — status check, help, ping/pong, pre-canned acknowledgment |
| Memory system | **Read-only** — can recall existing memories, cannot write new ones |
| Surveillance ingestion | **Queued** — events buffered to Redis, processed on recovery |
| Task queue | **Queued with size limits** — new tasks accepted up to queue capacity |
| Monitoring (Prometheus/Grafana) | **Active** — continues monitoring infrastructure and alerting |

**Recovery Behavior**

1. Health check cycle (30s interval) detects router/provider restoration.
2. System automatically ascends to the highest available tier.
3. If recovering from Tier 3 → Tier 1/2: Ollama service stopped, RAM released.
4. If recovering from Tier 4 → any tier: full re-initialization sequence.
5. Queued surveillance events processed in chronological order.
6. Paused agent loop resumes from saved state (Tier 1/2 only).
7. Persona engine re-initializes with last known mood/state.
8. Task queue drains with priority ordering.

**Ollama Feasibility on 4C/16GB VPS**

| Factor | Assessment |
|---|---|
| Resource contention | Manageable: 4GB RAM cap leaves 12GB for PostgreSQL + Redis + core services. Ollama stopped during normal Tier 1/2 operations. |
| Model quality | Acceptable for degraded mode: Phi-3-mini and Mistral-7B quantized provide basic conversational capability. Persona consistency not guaranteed — degraded mode acceptable. |
| Operational complexity | Moderate: systemd service management, model pre-download, auto-start/stop lifecycle. Cold start ~10-30s. |
| Cost-benefit | Positive: $0 incremental cost. Provides conversational fallback during extended cloud outages — better than total silence. |

**Feasibility Verdict: FEASIBLE**

Four-tier fallback approach memberikan maximum resilience:
1. Cloud primary (9Router) — full capability.
2. Cloud secondary (OpenRouter) — full capability, possible cost increase.
3. Local tertiary (Ollama) — degraded but functional, zero cost, RAM-managed.
4. Graceful degradation — safe last resort, basic operational shell only.

Ollama sebagai third-level fallback feasible pada 4C/16GB VPS dengan 4GB RAM cap dan lightweight model. Service lifecycle managed automatically via systemd. Cold start time (~10-30s) acceptable untuk outage scenario.

**Risks**

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Extended all-tier outage (9Router + OpenRouter + Ollama down >1 hour) | LOW | MEDIUM | Task queue with size limits; basic Discord commands maintain operator contact; Prometheus alerts for extended degradation. |
| Ollama RAM contention during Tier 3 | LOW | MEDIUM | 4GB hard cap; systemd MemoryMax; Ollama auto-stopped on Tier 1/2 recovery; Prometheus RAM alerts. |
| Ollama model quality inconsistency | MEDIUM | LOW | Degraded persona mode acceptable; no mood/relationship modeling; user notified of degraded tier. |
| OpenRouter API breaking changes | LOW | MEDIUM | Adapter pattern isolates router integration; fallback to Ollama or graceful degradation while adapter updated. |

---

### 4. Memory Architecture — PostgreSQL 16 + pgvector + TimescaleDB

**Current State Assessment**

PostgreSQL 16 dengan extension pgvector (semantic search) dan TimescaleDB (time-series compression) sebagai primary data store. Redis sebagai cache layer dengan 6 database terpisah (task queue, LLM cache, surveillance buffer, session state, pub/sub, rate limiting).

**Evidence from Corpus**

| Source | Evidence |
|---|---|
| ADR-007 | Memory PostgreSQL primary + Redis cache; no SQLite — Accepted. |
| Technical Architecture §5.1 | 8 schema (memory, persona, behavior, surveillance, financial, projects, system, social) dengan ~30+ tables. |
| Technical Architecture §5.2 | TimescaleDB hypertables dengan auto-compression data > 7 hari (90%+ space saving). |
| Technical Architecture §5.3 | pgvector IVFFlat index untuk approximate nearest neighbor search. |
| Memory Schema §2.1 | Episodes table dengan vector(1536) embeddings, TimescaleDB hypertable, GIN indexes. |
| Memory Schema §8.1 | Memory injection pipeline ~8,300 tokens — well within 1M context. |

**Feasibility Verdict: FEASIBLE**

PostgreSQL 16 + pgvector + TimescaleDB adalah stack yang mature, well-documented, dan proven di production. Semua extension tersedia sebagai Docker images. TimescaleDB auto-compression mengurangi storage footprint secara signifikan untuk surveillance time-series data. pgvector IVFFlat index memberikan sub-second semantic search pada jutaan embeddings.

PgBouncer connection pooling (Technical Architecture §5.4) dengan 5 per-service users mengelola koneksi secara efisien. Agent Loop Spec §6.1 mengestimasi ~2-3 connections per loop dari pool ~100 total.

**Embedding Strategy**

Embedding menggunakan SentenceTransformers local (free) — keputusan baru yang dikonfirmasi oleh operator. Ini menggantikan rencana sebelumnya yang menggunakan text-embedding-3-small ($0.02/M tokens). SentenceTransformers berjalan di VPS tanpa API cost.

| Model | Dimension | RAM | Quality | Cost |
|---|---|---:|---|---:|
| all-MiniLM-L6-v2 | 384 | ~200MB | Good | $0 |
| all-mpnet-base-v2 | 768 | ~500MB | Better | $0 |
| multi-qa-mpnet-base | 768 | ~500MB | Best for QA | $0 |

Catatan: MemorySchema §2.1 mendefinisikan `vector(1536)` yang sesuai dengan text-embedding-3-small. Jika SentenceTransformers digunakan, dimensi harus disesuaikan (384 atau 768) dan migration diperlukan. Ini adalah unresolved item yang harus ditangani sebelum implementasi.

**Risks**

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| pgvector query performance degradation pada jutaan embeddings | LOW | MEDIUM | IVFFlat index; periodic re-indexing; archive cold embeddings ke R2. |
| TimescaleDB compression ratio di bawah ekspektasi | LOW | LOW | Monitor compression ratio; adjust chunk time interval jika diperlukan. |
| Embedding dimension mismatch (1536 vs 384/768) | HIGH | MEDIUM | Migration script diperlukan; update schema dan re-embed existing data. Tambahkan ke backlog. |

---

### 5. Database Hosting — Self-Hosted PostgreSQL

**Current State Assessment**

Keputusan baru yang dikonfirmasi oleh operator: PostgreSQL di-host sendiri di VPS (Docker container), bukan managed service. Ini menghemat $14-18/bulan yang diperlukan agar total cost tetap dalam batas $30/bulan.

**Evidence from Corpus**

| Source | Evidence |
|---|---|
| Technical Architecture §2.1 | PostgreSQL + Redis dialokasikan 4GB RAM + 1 core di Docker containers. |
| Technical Architecture §9.1 | Backup strategy: WAL streaming ke R2 (continuous) + pg_dump ke S3 (harian 02:00). |
| Technical Architecture §9.2 | DR procedure: database corruption RTO < 1 jam, RPO < 1 jam via pg_restore. |
| Cost/FinOps §4.1 | VPS hostdata.id $10-12/month mencakup semua infrastruktur termasuk PostgreSQL. |
| SLO-SLA §6.1 | PostgreSQL composite availability SLO 99.9% monthly (SEV1 breach). |

**Feasibility Verdict: FEASIBLE**

Self-hosted PostgreSQL di Docker container pada VPS 4C/16GB adalah standard practice. Dengan alokasi 4GB RAM, PostgreSQL dapat menangani workload single-user dengan nyaman. WAL streaming ke R2 memberikan continuous backup, dan pg_dump harian ke S3 memberikan cold backup. Recovery procedures sudah didefinisikan di ADR-025.

**Cost Savings vs Managed**

| Option | Monthly Cost | Control | Complexity |
|---|---:|---|---|
| Self-hosted (chosen) | $0 (included in VPS) | Full | Medium — Guinevere manages |
| Managed (rejected) | $14-18/month | Limited | Low |
| **Savings** | **$14-18/month** | | |

Penghematan $14-18/bulan ini kritikal untuk menjaga total spend di bawah $30/bulan.

**Risks**

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Self-managed PostgreSQL corruption | LOW | HIGH | WAL streaming + daily pg_dump + weekly VPS snapshot (Technical Architecture §9.1). |
| Disk space exhaustion | MEDIUM | HIGH | TimescaleDB auto-compression; cold storage archival ke R2; Prometheus disk alerts. |
| PostgreSQL upgrade complexity | LOW | MEDIUM | Docker image versioning; test upgrade di staging DB pertama. |
| Backup failure undetected | LOW | CRITICAL | Automated backup verification; SLO-AVL-004 monitors composite availability including backup status. |

---

### 6. SDLC Loop — 7-Phase Autonomous Loop

**Current State Assessment**

Guinevere menjalankan 7-phase autonomous SDLC loop: Research → Plan & Delegate → Delegate → Execute → Validate & Audit → Update Documents → Setup Evidence. Loop instances dapat berjalan parallel (hingga ~20 berdasarkan RAM allocation), dengan Loop Guardian (30s + event-driven) dan TODO Enforcer menjaga progress.

**Evidence from Corpus**

| Source | Evidence |
|---|---|
| ADR-011 | SDLC 7-phase loop specification — Accepted. |
| Agent Loop Spec §1.3 | Unlimited loop instances; each dengan Phase Runner, Sub-Agent Pool, TODO Enforcer, Loop Guardian, State Manager. |
| Agent Loop Spec §4.1 | Loop Guardian: heartbeat 30s, event-driven immediate, progress check 5min, resource check 60s. |
| Agent Loop Spec §6.1 | Max ~20 parallel loops; ~512MB per active loop; GPT-5.5 calls async. |
| Agent Loop Spec §6.2 | Priority scoring: client_revenue 0.3 + deadline 0.4 + faiz_priority 0.2 + guinevere_judgment 0.1. |

**Feasibility Verdict: FEASIBLE**

Arsitektur loop sudah mature dan well-specified. Redis sebagai active state store dan PostgreSQL sebagai permanent record memberikan durability. TODO Enforcer pattern (dari oh-my-openagent, 54.9k stars) proven untuk menjaga agent tidak idle. Hash-anchored edit format (LINE#ID content hash) memberikan 68.3% success rate vs 6.7% baseline.

Parallel execution bounded oleh RAM (16GB total, ~512MB per loop = ~20 max), namun dalam praktiknya tidak semua loop aktif bersamaan. Single user dengan 2-3 active projects kemungkinan berjalan 3-5 parallel loops.

**Risks**

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Loop stuck tanpa progress | MEDIUM | MEDIUM | Loop Guardian 30s heartbeat + 5min progress check; auto-kill + respawn after 60s idle. |
| Parallel loop resource contention | LOW | MEDIUM | RAM limit per service via systemd MemoryMax; PgBouncer connection pooling. |
| Phase transition race condition | LOW | MEDIUM | State machine dengan explicit transitions (Agent Loop Spec §5.2); PostgreSQL as source of truth. |
| Infinite loop pada validation retry | LOW | MEDIUM | Max retry count per phase; escalate ke Faiz setelah N retries. |

---

### 7. Browser Automation — obscura (Rust) + Playwright

**Current State Assessment**

obscura (Rust, 13.9k stars) sebagai primary browser automation untuk web scraping dan research. Playwright Python sebagai fallback untuk complex form automation, PDF generation, dan API provider dashboard login.

**Evidence from Corpus**

| Source | Evidence |
|---|---|
| ADR-020 | Browser automation uses obscura primary + Playwright fallback — Accepted. |
| API Integration §8.2 | obscura untuk web scraping, JS-heavy sites, screenshot. Playwright untuk complex forms, PDF, auth flows. |
| Technical Architecture §12.1 | obscura integrated sebagai MCP browser tool. |
| API Integration §11.1 | `playwright>=1.47.0` di pyproject.toml. |

**Feasibility Verdict: FEASIBLE**

Dua-tier browser strategy memberikan coverage yang luas: obscura untuk speed dan efficiency (Rust-based), Playwright untuk maturity dan compatibility. Keduanya berjalan di VPS sebagai subprocess atau library call. Playwright memiliki full Python binding dan well-tested di headless Linux environments.

**Risks**

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| obscura belum mature untuk complex JS sites | MEDIUM | LOW | Playwright fallback sudah tersedia; ADR-020 explicit tentang fallback strategy. |
| Headless browser RAM consumption tinggi | MEDIUM | MEDIUM | Spawn browser instances on-demand; kill setelah selesai; monitor via Prometheus. |
| Anti-bot detection blocking scraping | MEDIUM | MEDIUM | obscura designed AI-native; Playwright stealth plugin; rotate user agents. |

---

### 8. Surveillance Stack — Tasker + Windows Daemon + FastAPI

**Current State Assessment**

Surveillance omniscient 24/7 melalui tiga data sources: Android (Tasker + AutoInput + AutoNotification), Windows (Python daemon + NSSM + watchdog), dan future wearable (Mi Fitness API post-MVP). Data dikirim via Tailscale mesh ke FastAPI receiver di VPS.

**Evidence from Corpus**

| Source | Evidence |
|---|---|
| Technical Architecture §6.1 | Data flow: Android HTTP POST via Tailscale → FastAPI :8000 → Redis DB 2 buffer → TimescaleDB. Windows WebSocket → :8001 → same pipeline. |
| Technical Architecture §6.2 | 8 FastAPI surveillance endpoints: activity, location, notification, call, clipboard, camera, WebSocket, health. |
| Technical Architecture §6.3 | Windows daemon: win32gui, pynput, PIL, OpenCV, pyperclip, ActivityWatch, websockets, NSSM, watchdog. |
| API Integration §5.1 | Tasker signed JSON via HTTPS Tailscale; HMAC-SHA256 signature validation. |
| BRD §3.1.4 | Android: app usage, screen time, notifikasi, GPS, kamera. Windows: active window, idle, browser history, screenshot, kamera. |

**Feasibility Verdict: FEASIBLE**

Stack ini feasible karena semua komponen sudah proven: Tasker adalah Android automation standard, Python daemon libraries (win32gui, pynput, etc.) mature, FastAPI async handles high-throughput ingestion, dan Tailscale memberikan encrypted mesh tanpa public port exposure.

HMAC signature validation (API Integration §5.1) memastikan data authenticity. Redis DB 2 sebagai buffer menyerap burst traffic sebelum async consumer memproses ke TimescaleDB.

**Risks**

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Tasker config hilang (HP reset) | MEDIUM | LOW | Auto-backup Tasker config ke GDrive + repo + VPS (Technical Architecture §9.1). |
| Windows daemon crash tanpa restart | LOW | MEDIUM | NSSM auto-restart service + watchdog thread detect hang (Technical Architecture §6.3). |
| Tailscale disconnection blocking surveillance | LOW | MEDIUM | Redis buffer holds data locally; batch upload saat reconnection. |
| Surveillance data volume exceeds storage | LOW | MEDIUM | TimescaleDB auto-compression (90%+ saving); cold storage ke R2 setelah 90 hari. |

---

### 9. Communication Channels — Discord, WhatsApp, Gmail, Resend

**Current State Assessment**

Discord sebagai primary UI (Hermes native adapter), WhatsApp via Baileys untuk client communication, Gmail API untuk client thread management, Resend API untuk transactional email, dan Gotify self-hosted untuk push notification backup.

**Evidence from Corpus**

| Source | Evidence |
|---|---|
| ADR-022 | Communication channel strategy — Accepted with notes. |
| API Integration §3.1 | Discord: Hermes native adapter + slash commands (/status, /pause, /task, /loops, /evidence, /mood, /score). |
| API Integration §7.1 | WhatsApp: Baileys Node.js service (subprocess dari Python); Guinevere kirim sebagai nomor Faiz. |
| API Integration §7.2 | Gmail API untuk client thread; Resend API untuk invoice dan transactional. |
| API Integration §7.3 | Gotify self-hosted untuk push notification backup jika Discord unavailable. |

**Feasibility Verdict: CONDITIONALLY FEASIBLE**

Discord, Gmail, Resend, dan Gotify straightforward dan well-supported. WhatsApp via Baileys adalah fragile dependency — Baileys adalah unofficial reverse-engineered WhatsApp library yang bisa break kapan saja WhatsApp mengubah protocol.

**Mitigasi untuk Baileys Fragility:** Adapter pattern (lihat §10 Abstraction Layers) mengisolasi Guinevere core dari Baileys-specific API. Jika Baileys break, adapter dapat diganti dengan alternative (misalnya WhatsApp Business API resmi jika available untuk personal use) tanpa mengubah core logic.

**Cloudflare Tunnel untuk Discord Webhook**

Keputusan baru: minimum 1 public endpoint diperlukan untuk Discord webhook receiver. Cloudflare Tunnel menyediakan ini tanpa membuka port langsung di VPS — tunnel meng-proxy dari Cloudflare edge ke internal FastAPI endpoint via Tailscale. Ini sejalan dengan defense-in-depth (ADR-018).

**Risks**

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Baileys WhatsApp library break | HIGH | MEDIUM | Adapter pattern isolation; fallback ke Discord/email notification. |
| Discord API rate limiting | LOW | MEDIUM | Hermes native adapter handles rate limits; SlowAPI middleware. |
| Resend API quota exceeded | LOW | LOW | Free tier 100 emails/day; monitor usage; fallback ke Gmail API. |
| Cloudflare Tunnel downtime | LOW | MEDIUM | Discord webhook retry logic; Gotify sebagai secondary notification path. |

---

### 10. Abstraction Layers — Fragile API Isolation

**Current State Assessment**

Adapter pattern digunakan untuk mengisolasi Guinevere core dari fragile external APIs (Baileys, Tasker). Ini memastikan bahwa jika external library break atau API berubah, hanya adapter layer yang perlu diperbaiki, bukan core business logic.

**Evidence from Corpus**

| Source | Evidence |
|---|---|
| ADR-022 | Communication channel strategy accepted with notes — adapter pattern untuk fragile integrations. |
| API Integration §7.1 | Baileys diisolasi sebagai Node.js subprocess; Python calls via HTTP to localhost WA service. |
| API Integration §5.1 | Tasker protocol didefinisikan sebagai signed JSON schema — adapter translates ke internal format. |
| Technical Architecture §3.2 | Plugin architecture (`plugins/`) memisahkan integration-specific logic dari core persona. |

**Feasibility Verdict: FEASIBLE**

Adapter pattern adalah standard software engineering practice yang well-proven. Implementasi Baileys sebagai Node.js subprocess yang di-call via HTTP localhost sudah memberikan isolation boundary yang natural. Tasker protocol sebagai signed JSON schema juga memungkinkan adapter swap.

**Risks**

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Adapter maintenance overhead | LOW | LOW | Single responsibility per adapter; well-defined contract; unit tests per adapter. |
| Adapter contract drift | LOW | MEDIUM | Pydantic v2 validation models sebagai contract enforcement; CI tests. |

---

### 11. Search Integration — Brave Search + Exa AI

**Current State Assessment**

Brave Search API ($3/1000 queries) sebagai primary broad web search. Exa AI ($0.01/query) sebagai secondary semantic deep research. GitHub Search via MCP untuk code search (free).

**Evidence from Corpus**

| Source | Evidence |
|---|---|
| API Integration §8.1 | Brave untuk general research, news, documentation. Exa untuk semantic deep research, academic, similar content. |
| Cost/FinOps §4.1 | Brave $1-2/month (soft limit), Exa $1-2/month (soft limit). |
| Cost/FinOps §7.2 | Search cache: cache Brave/Exa results per query signature. |

**Exa as Cuttable**

Exa AI dikonfirmasi sebagai cuttable per operator decision (Q45:d). Jika budget ketat, Exa dapat dihilangkan dan Brave Search + cached results mencukupi untuk research needs.

**Feasibility Verdict: FEASIBLE**

Kedua search APIs well-documented dengan Python SDKs (`exa-py>=1.0.0` di pyproject.toml). Brave Search memberikan broad coverage dengan reasonable pricing. Exa memberikan semantic depth saat diperlukan. Cache layer mengurangi redundant queries.

**Risks**

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Search cost spike saat heavy research loops | MEDIUM | LOW | Query cap per loop; cache aggressively; Exa cuttable if budget tight. |
| Brave API quality degradation | LOW | MEDIUM | Exa sebagai secondary; GitHub search untuk code; cached results. |

---

### 12. Monitoring — Prometheus + Grafana on Primary VPS

**Current State Assessment**

Prometheus + Grafana + Loki co-located di primary VPS (hostdata.id 4C/16GB). Dedicated monitoring VPS adalah post-MVP option jika resource contention menjadi masalah.

**Evidence from Corpus**

| Source | Evidence |
|---|---|
| ADR-017 | Prometheus + Grafana on primary VPS first — Accepted. |
| Technical Architecture §8.1 | Prometheus, Grafana, Loki, Promtail, node_exporter, postgres_exporter, redis_exporter all Docker containers. |
| Technical Architecture §2.1 | Observability + queue workers dialokasikan 4GB RAM + 1 core. |
| SLO-SLA §6.1 | SLO-AVL-007: Observability stack availability 99.0% monthly. |

**Resource Feasibility**

| Service | RAM Estimate | Source |
|---|---:|---|
| Prometheus | ~512MB | Typical for single-target monitoring |
| Grafana | ~256MB | Dashboard rendering |
| Loki | ~512MB | Log aggregation |
| Promtail | ~64MB | Log shipping |
| Exporters (3x) | ~192MB | node + postgres + redis |
| **Total** | **~1.5GB** | Within 4GB allocation |

**Feasibility Verdict: FEASIBLE**

Monitoring stack co-located di primary VPS feasible untuk single-user monitoring. 4GB allocation mencukupi untuk Prometheus + Grafana + Loki + exporters. Jika log volume atau metric cardinality tumbuh signifikan, dedicated monitoring VPS dapat diaktifkan post-MVP.

**Risks**

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Prometheus storage growth | MEDIUM | MEDIUM | Retention policy 30 hari; recording rules reduce cardinality. |
| Monitoring competes dengan Guinevere core saat spike | LOW | MEDIUM | systemd MemoryMax limits per service; cgroup isolation. |
| Meta-monitoring gap (monitoring monitors itself) | MEDIUM | MEDIUM | UptimeRobot external check (Technical Architecture §8.1); Gotify alert jika Grafana down. |

---

### 13. Network — Tailscale Mesh + Cloudflare Tunnel

**Current State Assessment**

Tailscale mesh network menghubungkan semua devices (VPS, Android, Windows) tanpa public port. SSH hanya via Tailscale SSH. Internal services menggunakan MagicDNS. Cloudflare Tunnel menyediakan minimum 1 public endpoint untuk Discord webhook.

**Evidence from Corpus**

| Source | Evidence |
|---|---|
| ADR-019 | Access control via Tailscale VPN mesh — Accepted with notes. |
| Technical Architecture §2.2 | All internal services via Tailscale addresses (100.x.x.x); custom DNS mapping via MagicDNS. |
| Technical Architecture §7.1 | Network perimeter: Tailscale mesh — zero public ports. SSH: Tailscale SSH only. |
| BRD §4.3 | VPS access control: Tailscale VPN — CRITICAL priority. |

**Cloudflare Tunnel for Discord Webhook**

Discord webhook receiver memerlukan public endpoint karena Discord servers mengirim HTTP POST ke URL yang dikonfigurasi. Cloudflare Tunnel (cloudflared daemon) membuka tunnel dari internal FastAPI endpoint ke Cloudflare edge tanpa membuka port di VPS firewall.

```text
Discord Server → HTTPS → Cloudflare Edge → Tunnel → cloudflared → FastAPI :8000
                                                                    (via Tailscale)
```

**Feasibility Verdict: FEASIBLE**

Tailscale mesh proven untuk zero-trust networking. Cloudflare Tunnel memberikan secure public endpoint tanpa port exposure. Kombinasi ini mempertahankan defense-in-depth (ADR-018) sambil memenuhi Discord webhook requirement.

**Risks**

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Tailscale service outage | LOW | HIGH | Local Redis buffer untuk surveillance; offline queue untuk LLM tasks. |
| Cloudflare Tunnel abuse (DDoS on webhook) | LOW | MEDIUM | Cloudflare WAF rules; rate limiting di FastAPI; JWT validation. |
| Tailscale key expiry | LOW | MEDIUM | Guinevere monitor key expiry; auto-renewal alert; runbook documented. |

---

### 14. Storage — idcloudhost S3 + Cloudflare R2

**Current State Assessment**

Dual storage: idcloudhost S3 sebagai primary (data sovereignty Indonesia, billable) dan Cloudflare R2 sebagai backup (free 10GB). boto3 dengan dual endpoint config. Encryption sebelum upload.

**Evidence from Corpus**

| Source | Evidence |
|---|---|
| API Integration §6.2 | boto3 dual endpoint: idcloudhost S3 primary, Cloudflare R2 backup. Encrypted upload. |
| Technical Architecture §9.1 | PostgreSQL cold backup ke S3 harian; WAL streaming ke R2 continuous; screenshots encrypted real-time. |
| Cost/FinOps §4.1 | idcloudhost S3: $2-3/month (soft); R2: free up to 10GB. |

**Feasibility Verdict: FEASIBLE**

Kedua S3-compatible storage services well-supported oleh boto3. Dual backup memberikan redundancy geographic (Indonesia + global Cloudflare edge). Encryption sebelum upload (Technical Architecture §9.1) memastikan data security at rest.

**Risks**

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| idcloudhost S3 outage | LOW | MEDIUM | R2 sebagai backup; Guinevere auto-switch ke R2 jika S3 unreachable. |
| Storage cost creep | LOW | LOW | TimescaleDB compression; cold archival policy; monthly cost review. |
| R2 free tier exceeded (>10GB) | LOW | LOW | R2 $0.015/GB-month setelah 10GB; monitor usage; cleanup policy. |

---

### 15. MCP Native — Guinevere MCP Replacing OpenCode

**Current State Assessment**

Guinevere MCP native menggantikan OpenCode CLI sepenuhnya (ADR-013). MCP layer menyediakan: filesystem, shell, git, github, fetch, postgres, browser. Semua coding operations berjalan melalui MCP tools yang di-orchestrate oleh SDLC loop.

**Evidence from Corpus**

| Source | Evidence |
|---|---|
| ADR-013 | Guinevere MCP native fully replaces OpenCode/opencode — Accepted. |
| Technical Architecture §4.2 | MCP Tools: filesystem, shell, git, github, fetch, postgres, browser — coding agent capabilities. |
| BRD §3.1.3 | Full SDLC loop via MCP; unit test 90% coverage; code review semua commit. |
| Agent Loop Spec §3.4 | Execute phase menggunakan MCP tools untuk code generation, testing, dan file operations. |

**Feasibility Verdict: FEASIBLE**

MCP (Model Context Protocol) adalah open standard yang gaining adoption. Implementasi native MCP tools di dalam Hermes Agent framework memberikan full control tanpa external CLI dependency. Semua required capabilities (filesystem, shell, git, github, fetch, postgres, browser) memiliki well-established Python libraries.

**Risks**

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| MCP tool implementation complexity | MEDIUM | MEDIUM | Hermes Agent sudah provide MCP support; incremental implementation per tool. |
| Shell execution security (arbitrary commands) | MEDIUM | HIGH | Sandboxed execution di VPS; command allowlist; no internet restriction. |
| Git operation errors (force push, data loss) | LOW | HIGH | GitHub PAT tanpa delete_repo scope (API Integration §4.3); branch protection rules. |

---

### Section A: Technical Viability Summary

| # | Area | Verdict | Confidence |
|---|---|---|---|
| 1 | Agent Framework (Hermes Agent) | FEASIBLE | HIGH |
| 2 | LLM Architecture (GPT-5.5 via 9Router) | FEASIBLE | HIGH |
| 3 | LLM Router Outage (Three-Tier Fallback) | FEASIBLE | HIGH |
| 4 | Memory Architecture (PG16 + pgvector + TimescaleDB) | FEASIBLE | HIGH |
| 5 | Database Hosting (Self-hosted) | FEASIBLE | HIGH |
| 6 | SDLC Loop (7-phase) | FEASIBLE | HIGH |
| 7 | Browser Automation (obscura + Playwright) | FEASIBLE | HIGH |
| 8 | Surveillance Stack (Tasker + Windows + FastAPI) | FEASIBLE | HIGH |
| 9 | Communication Channels (Discord + WA + Gmail + Resend) | CONDITIONALLY FEASIBLE | MEDIUM |
| 10 | Abstraction Layers (Adapter Pattern) | FEASIBLE | HIGH |
| 11 | Search Integration (Brave + Exa) | FEASIBLE | HIGH |
| 12 | Monitoring (Prometheus + Grafana) | FEASIBLE | HIGH |
| 13 | Network (Tailscale + Cloudflare Tunnel) | FEASIBLE | HIGH |
| 14 | Storage (idcloudhost S3 + Cloudflare R2) | FEASIBLE | HIGH |
| 15 | MCP Native (OpenCode replacement) | FEASIBLE | HIGH |

**Unresolved Technical Items:**
- Embedding dimension mismatch: MemorySchema defines vector(1536) tapi SentenceTransformers local biasanya 384/768. Migration atau model selection diperlukan.
- OpenRouter integration sebagai secondary router, Ollama local sebagai third-level fallback, dan graceful degradation behavior saat semuanya down.
- Cloudflare Tunnel configuration dan WAF rules untuk Discord webhook endpoint.

---

## SECTION B: ECONOMIC VIABILITY

### Related Documents

| Document | Relationship |
|---|---|
| `Guinevere_Cost_FinOps_Model_v1.0.md` | Primary source for budget model, cost taxonomy, and vendor strategy. |
| `Guinevere_TechnicalArchitecture_v2.0.md` | Defines infrastructure footprint and resource allocation. |
| `Guinevere_APIIntegration_v2.0.md` | Defines all billable API services and their cost profiles. |
| `Guinevere_SLO_SLA_ErrorBudgetSpec_v1.0.md` | Defines cost SLOs and budget freeze policies. |
| `Guinevere_ADR_Index_v1.0.md` | ADR-004, ADR-006 govern model selection with cost implications. |

---

### 1. Budget Constraint — $30/Month Hard Cap

**Analysis**

$30/bulan adalah hard cap yang ditetapkan oleh operator dan dikodifikasi di Cost/FinOps Model §2.2. Ini bukan target yang boleh dilampaui secara kasual — ini adalah operational ceiling. Total monthly spend harus stay di atau di bawah $30 kecuali Faiz explicitly approve exception.

**Evidence from Corpus**

| Source | Evidence |
|---|---|
| Cost/FinOps §2.2 | "The monthly budget is $30/month hard cap. This value is not a target that may be exceeded casually." |
| Cost/FinOps §4.2 | Hard limit, soft limit, dan zero budget classifications defined. |
| Cost/FinOps §4.3 | Escalation procedure: daily burn anomaly, category >80%, total projected >100%, budget exhausted. |
| SLO-SLA §6.6 | SLO-COST-001 through SLO-COST-005 dengan freeze rules. |

**Hard Constraints**

| Rule | Meaning |
|---|---|
| Hard cap | Total monthly spend ≤ $30 tanpa Faiz approval. |
| No hidden overages | Cost overruns visible di monthly cost report bulan yang sama. |
| No persona override | Persona/yandere behavior tidak boleh justify extra spend. |
| No safety reduction | Safety, incident response, backup, data integrity tidak boleh dikurangi untuk hemat. |
| No silent lock-in | Semua vendor harus punya documented alternatives dan switch procedures. |

**Feasibility Verdict: FEASIBLE** — dengan optimasi model routing dan self-hosted infrastructure.

---

### 2. Infrastructure Cost — VPS hostdata.id

**Cost Breakdown**

| Component | Specification | Monthly Cost | Notes |
|---|---|---:|---|
| VPS hostdata.id | 4 Core CPU, 16GB RAM, 120GB SSD | $10-12 | Shared infra fixed spend. |
| Swap file | 8GB | $0 | Included in VPS. |
| Ubuntu 24.04 LTS | OS | $0 | Free. |
| Self-hosted PostgreSQL | Docker container | $0 | Included in VPS (replaces $14-18 managed). |
| Self-hosted Redis | Docker container | $0 | Included in VPS. |
| Self-hosted Prometheus/Grafana | Docker containers | $0 | Included in VPS. |
| Self-hosted Gotify | Systemd service | $0 | Included in VPS. |
| Cloudflare Tunnel | cloudflared daemon | $0 | Free tier. |
| **Infrastructure Subtotal** | | **$10-12** | |

**Self-Hosting Savings**

| Service | Self-Hosted Cost | Managed Alternative Cost | Monthly Savings |
|---|---:|---:|---:|
| PostgreSQL | $0 (in VPS) | $14-18 (managed) | $14-18 |
| Redis | $0 (in VPS) | $5-10 (managed) | $5-10 |
| Monitoring | $0 (in VPS) | $10-29 (Grafana Cloud) | $10-29 |
| Push notifications | $0 (Gotify) | $5-10 (Pushover/OneSignal) | $5-10 |
| **Total Savings** | | | **$34-67** |

Self-hosting menghemat $34-67/bulan dibanding managed services — kritikal untuk fit dalam $30 budget.

---

### 3. LLM Cost — GPT-5.5 + DeepSeek V4 Flash + OpenRouter Secondary + Ollama Third-Level

**Cost Breakdown**

| Model | Use Case | Est. Cost | Monthly Budget |
|---|---|---|---:|
| GPT-5.5 via 9Router | Core persona, reasoning, planning, high-stakes synthesis | Premium — varies | $10-12 |
| DeepSeek V4 Flash via 9Router | Sub-agents, research, validation, audit | ~$0.10/M input tokens | $0-2 |
| DeepSeek V4 Flash free | Validation/audit sub-agents | $0.00 | $0 |
| OpenRouter secondary routing | Fallback saat 9Router down | Passthrough (same token pricing) | $0 additional |
| Ollama local (third-level) | Fallback saat kedua cloud router down | $0 (free, open-source, existing hardware) | $0 |
| Graceful degradation | Emergency saat semuanya down | $0 (no LLM inference) | $0 |
| SentenceTransformers local | Embedding generation | $0 (local CPU) | $0 |
| **LLM Subtotal** | | | **$10-14** |

**GPT-5.5 Cost Management**

GPT-5.5 adalah line item terbesar yang variable. Cost/FinOps §5.1 mendefinisikan model routing policy yang ketat:

| Task Type | Preferred Model | Cost Strategy |
|---|---|---|
| Core reasoning, high-stakes | GPT-5.5 | Worth the premium |
| Sub-agent research | DeepSeek V4 Flash | Free tier first |
| Sub-agent code generation | DeepSeek V4 Flash | Cost-efficient |
| Validation/audit | DeepSeek V4 Flash free | $0 |
| Safety-critical | GPT-5.5 | Cost may not weaken review |
| Long context summarization | DeepSeek V4 Flash | Cached summaries |

**Graceful Degradation dan Ollama Cost**

Ollama third-level fallback = $0 additional cost. Ollama adalah free, open-source, berjalan di existing VPS hardware tanpa API cost. Task queuing dan Discord basic commands menggunakan existing PostgreSQL + Redis yang sudah budgeted. OpenRouter sebagai secondary router menggunakan passthrough pricing (same token rates as direct API). Graceful degradation mode (Tier 4, ultimate last resort) = $0 additional cost.

**Feasibility Verdict: FEASIBLE** — dengan strict model routing dan GPT-5.5 reserved hanya untuk high-value tasks.

---

### 4. Storage Cost — S3 + R2 Tiered

**Cost Breakdown**

| Storage | Provider | Free Tier | Est. Monthly Cost |
|---|---|---|---:|
| Primary object storage | idcloudhost S3 | None | $2-3 |
| Backup object storage | Cloudflare R2 | 10GB free | $0-1 |
| PostgreSQL WAL streaming | Cloudflare R2 | (within R2) | $0 |
| Cold archival (>90 hari) | Cloudflare R2 | (within R2) | $0 |
| **Storage Subtotal** | | | **$2-4** |

**TimescaleDB Compression Impact**

TimescaleDB auto-compression data > 7 hari memberikan 90%+ space saving (Technical Architecture §5.2). Untuk surveillance data yang tumbuh cepat, ini mengurangi disk usage dari ~100GB/bulan menjadi ~10GB/bulan uncompressed. Cold storage ke R2 setelah 90 hari menjaga R2 usage di bawah 10GB free tier.

**Feasibility Verdict: FEASIBLE**

---

### 5. Search API Cost — Brave + Exa

**Cost Breakdown**

| Service | Rate | Monthly Budget | Cuttable |
|---|---|---:|---|
| Brave Search API | $3/1000 queries | $1-2 | No — primary research tool |
| Exa AI Search | $0.01/query | $1-2 | Yes — confirmed cuttable (Q45:d) |
| GitHub Search | Free (PAT) | $0 | N/A |
| **Search Subtotal** | | **$1-4** | |

**Optimization**

- Cache Brave/Exa results per query signature (Cost/FinOps §7.2).
- Exa dapat di-cut jika budget ketat; Brave saja sudah mencukupi.
- Batch queries untuk research loops.

**Feasibility Verdict: FEASIBLE**

---

### 6. Communication Cost — Discord, Resend, Gotify

**Cost Breakdown**

| Service | Cost | Monthly | Notes |
|---|---|---:|---|
| Discord | Free (bot account) | $0 | Primary UI — no operational cost. |
| WhatsApp (Baileys) | Free (unofficial) | $0 | No API cost; risk is reliability, not cost. |
| Gmail API | Free (quota) | $0 | Personal account; within free quota. |
| Resend API | Free tier 100/day | $0-1 | Transactional email only. |
| Gotify | Self-hosted | $0 | Included in VPS. |
| **Communication Subtotal** | | **$0-1** | |

**Feasibility Verdict: FEASIBLE**

---

### 7. Monitoring Cost — Prometheus/Grafana/Sentry

**Cost Breakdown**

| Service | Hosting | Monthly | Notes |
|---|---|---:|---|
| Prometheus | Self-hosted (Docker) | $0 | Included in VPS. |
| Grafana | Self-hosted (Docker) | $0 | Included in VPS. |
| Loki | Self-hosted (Docker) | $0 | Included in VPS. |
| Sentry | Free tier | $0 | 5K events/month free. |
| UptimeRobot | External free tier | $0 | 50 monitors free. |
| **Monitoring Subtotal** | | **$0** | |

**Feasibility Verdict: FEASIBLE**

---

### 8. Cost Allocation — Per-Category Budget Breakdown

**Monthly Budget Matrix (from Cost/FinOps Appendix A)**

| Category | Monthly Target | Hard/Soft | Actual Est. | Status |
|---|---:|---|---:|---|
| VPS hostdata.id | $10-12 | Hard baseline | $11 | ON BUDGET |
| GPT-5.5 via 9Router | $10-12 | Hard / controlled | $11 | ON BUDGET |
| DeepSeek V4 Flash | $0-2 | Soft / optimization | $1 | ON BUDGET |
| idcloudhost S3 | $2-3 | Soft | $2.50 | ON BUDGET |
| Brave Search API | $1-2 | Soft | $1.50 | ON BUDGET |
| Exa AI Search | $1-2 | Soft | $1.50 | ON BUDGET |
| Resend | $0-1 | Soft | $0.50 | ON BUDGET |
| Graceful degradation | $0 | Free | $0 | ON BUDGET |
| Ollama local (third-level) | $0 | Free | $0 | ON BUDGET |
| SentenceTransformers | $0 | Free | $0 | ON BUDGET |
| Cloudflare R2 | $0 | Free tier | $0 | ON BUDGET |
| Misc / contingency | $1-2 | Reserve | $1.50 | ON BUDGET |
| **TOTAL** | **$30** | **Hard cap** | **$30** | **AT CAP** |

**Verdict: FEASIBLE** — budget fits exactly at $30/month dengan self-hosted PostgreSQL dan free-tier maximization. Tight margin memerlukan strict cost governance.

---

### 9. Vendor Risk — Lock-In Analysis

**Vendor Alternative Matrix (from Cost/FinOps Appendix B)**

| Primary | Alternative | Switch Procedure | Lock-In Risk |
|---|---|---|---|
| GPT-5.5 via 9Router | DeepSeek V4 Flash via 9Router | Route config change; reduce task scope | LOW — both via 9Router API |
| 9Router routing | Direct provider or other router | Update config; rotate credentials; smoke test | MEDIUM — routing logic centralized |
| idcloudhost S3 | Cloudflare R2 | Update backup target; validate restore | LOW — S3-compatible API |
| Brave Search | Exa or cached results | Reduce queries; batch; cache | LOW — stateless queries |
| Resend | Gotify + Discord | Reduce email; keep incident comms | LOW — minimal dependency |
| hostdata.id VPS | Other Indonesian VPS provider | Snapshot migration; DNS update | MEDIUM — migration effort |
| Baileys (WhatsApp) | WhatsApp Business API or adapter swap | Replace adapter layer only | HIGH — unofficial library |
| Cloudflare | Tailscale Funnel or ngrok | Reconfigure tunnel provider | LOW — tunnel is thin layer |

**Feasibility Verdict: FEASIBLE** — no single vendor is irreplaceable. Switch procedures documented per Cost/FinOps §8.4.

---

### 10. ROI Analysis — Single-User Productivity

**Investment vs Return**

| Metric | Without Guinevere | With Guinevere | Delta |
|---|---|---|---|
| Monthly cost | $0 (no agent) | $30/month | +$30/month |
| Coding tasks completed/day | 0.5-1 (manual) | 1-2 autonomous | +1 task/day |
| Client communication | Manual, delayed | Autonomous, real-time | Hours saved |
| Project documentation | Inconsistent | 100% evidence-based | Quality uplift |
| Financial tracking | Manual spreadsheet | Autonomous capture + analysis | Accuracy + time saved |
| Monitoring | None/ad-hoc | 24/7 Prometheus + Grafana | Visibility uplift |
| Memory/context | Forgetful | Perfect recall, cross-session | Productivity multiplier |

**Estimated Monthly Value**

| Value Stream | Estimated Monthly Value |
|---|---:|
| Autonomous coding (20+ tasks/month saved) | $200-500 |
| Client communication automation | $50-100 |
| Financial tracking + optimization | $20-50 |
| Productivity enforcement (idle reduction) | $100-200 |
| Documentation + evidence automation | $50-100 |
| **Total Estimated Value** | **$420-950** |

**ROI: $420-950 value per $30 investment = 14x-32x return**

**Feasibility Verdict: FEASIBLE** — strong positive ROI even dengan conservative estimates.

---

### 11. Cost Optimization — Model Routing + Free-Tier Maximization

**Optimization Strategies**

| Strategy | Implementation | Monthly Savings |
|---|---|---:|
| GPT-5.5 for high-value only | Routing policy: sub-agents → DeepSeek | $5-15 |
| DeepSeek free tier first | Free tier untuk validation/audit | $2-5 |
| Graceful degradation (free) | $0 saat semua tier down | N/A (resilience) |
| Ollama local fallback (free) | $0 saat cloud router down | N/A (resilience) |
| SentenceTransformers local (free) | Replaces $0.02/M embedding API | $1-3 |
| Self-hosted PostgreSQL | Replaces $14-18 managed | $14-18 |
| Self-hosted monitoring | Replaces $10-29 Grafana Cloud | $10-29 |
| Self-hosted push notifications | Replaces $5-10 Pushover | $5-10 |
| Cache search results | Reduce redundant queries | $0.50-1 |
| TimescaleDB compression | Reduce storage growth | $1-2 |
| **Total Optimization Value** | | **$39-83** |

**Feasibility Verdict: FEASIBLE**

---

### 12. Embedding Cost — SentenceTransformers Local

**Current State Assessment**

Keputusan baru: embedding menggunakan SentenceTransformers local (free) yang berjalan di VPS. Ini menggantikan rencana awal text-embedding-3-small ($0.02/M tokens).

**Technical Considerations**

| Factor | Value |
|---|---|
| RAM usage | ~200-500MB tergantung model |
| CPU usage | Moderate saat batch embedding |
| Quality | Good untuk semantic similarity |
| Cost | $0 |

**Unresolved Item:** pgvector schema saat ini mendefinisikan `vector(1536)` (Memory Schema §2.1), yang sesuai dengan OpenAI embedding model. SentenceTransformers models umumnya menghasilkan 384 atau 768 dimensi. Schema migration atau re-embedding diperlukan sebelum implementasi.

**Feasibility Verdict: FEASIBLE** — dengan catatan schema migration diperlukan.

---

### Section B: Economic Viability Summary

| Area | Verdict | Monthly Cost |
|---|---|---:|
| Infrastructure (VPS) | FEASIBLE | $10-12 |
| LLM (GPT-5.5 + DeepSeek + OpenRouter secondary + Ollama third-level) | FEASIBLE | $10-14 |
| Storage (S3 + R2) | FEASIBLE | $2-4 |
| Search (Brave + Exa) | FEASIBLE | $1-4 |
| Communication | FEASIBLE | $0-1 |
| Monitoring | FEASIBLE | $0 |
| **TOTAL** | **FEASIBLE** | **$23-35** |

**Budget Assessment:** Range $23-35/bulan. Midpoint ~$30 tepat di hard cap. Feasible dengan strict governance dan optimization. Risk utama adalah GPT-5.5 usage spike yang dapat mendorong total ke atas $30.

**Mitigation:** Freeze policy (Cost/FinOps §4.3) dan cost anomaly detection (SLO-SLA §6.5) memastikan overrun terdeteksi dan ditangani sebelum akhir bulan.

---

## SECTION C: OPERATIONAL & RISK

### Related Documents

| Document | Relationship |
|---|---|
| `Guinevere_AgentLoopSpec_v2.0.md` | Defines autonomous loop behavior, error escalation, and self-modification patterns. |
| `Guinevere_TechnicalArchitecture_v2.0.md` | Defines deployment model, systemd services, CI/CD, backup/DR, and security architecture. |
| `Guinevere_SLO_SLA_ErrorBudgetSpec_v1.0.md` | Defines reliability targets, error budgets, freeze policies, and incident severity. |
| `Guinevere_ADR_Index_v1.0.md` | 29 ADRs governing safety, security, deployment, and persona boundaries. |
| `Guinevere_Cost_FinOps_Model_v1.0.md` | Defines cost governance and budget exhaustion procedures. |

---

### 1. Deployment Model — VPS Self-Deploy

**Current State Assessment**

Guinevere berjalan sebagai kumpulan systemd services di VPS hostdata.id (Ubuntu 24.04 LTS). CI via GitHub Actions free tier (lint, type check, tests, security scan). CD via Guinevere self-deploy cron (malam 03:00) — zero cost autonomous deployment.

**Evidence from Corpus**

| Source | Evidence |
|---|---|
| Technical Architecture §3.1 | 8 systemd services: guinevere-core, guinevere-surveillance, guinevere-scheduler, guinevere-windows-sync, guinevere-loops, docker, caddy, tailscaled. |
| Technical Architecture §10.1 | CI: ruff + black (lint), mypy (type check), pytest (tests), bandit + safety (security), pytest-cov (coverage). |
| Technical Architecture §10.2 | CD: cron 03:00 — git fetch → git pull → uv sync → tests → restart → health check → report/revert. |
| ADR-016 | CI/CD & Autonomous Deployment Strategy — Accepted with notes. |

**Feasibility Verdict: FEASIBLE**

systemd "Always, 10s delay" restart policy menjaga uptime. Self-deploy dengan test gate (tests harus pass sebelum restart) dan auto-revert (jika fail: git revert + rollback) memberikan safe autonomous CD tanpa biaya tambahan.

---

### 2. Self-Modification Safety — Automated Testing + Rollback

**Current State Assessment**

Keputusan baru yang dikonfirmasi oleh operator (Q80): self-modification oleh Guinevere harus disertai automated testing dan rollback mechanism. Guinevere diizinkan mengubah dirinya sendiri (self-update Hermes Agent, improve dashboards, evolve skills) tapi setiap perubahan harus pass test suite sebelum di-deploy dan bisa di-rollback otomatis jika gagal.

**Evidence from Corpus**

| Source | Evidence |
|---|---|
| Technical Architecture §10.2 | Self-deploy cron: test → if pass: restart → if fail: git revert + alert + rollback. |
| Agent Loop Spec §4.3 | Error escalation: Guinevere handle semua technical errors autonomous; escalate ke Faiz hanya untuk genuine blockers. |
| BRD §3.1.2 | Self-update Hermes Agent tanpa izin Faiz — tapi harus safe. |
| ADR-016 | Autonomous deployment dengan safety gates — Accepted with notes. |

**Self-Modification Governance Framework**

| Action Type | Pre-Condition | Test Gate | Rollback | Approval |
|---|---|---|---|---|
| Self-update Hermes Agent | Staging test pass | Unit + integration tests | git revert + service restart | None — autonomous |
| Modify own config | Schema validation | Config validation test | Previous config restore | None — autonomous |
| Create new skills | Skill quality grading | Skill execution test | Delete skill + revert | None — autonomous |
| Modify own persona | Drift within bounds | Persona consistency test | Revert drift log | None — bounded |
| Modify database schema | Staging migration pass | Migration + data integrity test | alembic downgrade | None — autonomous |
| Modify own deployment pipeline | CI pipeline green | End-to-end deploy test | git revert pipeline | Faiz approval |
| Modify safety boundaries | NEVER self-modify | N/A | N/A | Faiz approval ONLY |

**Feasibility Verdict: FEASIBLE**

Automated testing + rollback sudah embedded di self-deploy cron (Technical Architecture §10.2). Staging environment (Technical Architecture §10.3) memungkinkan test sebelum production. Safety boundaries (persona safety, safe-word enforcement, surveillance ethics) explicitly excluded dari self-modification.

**Risks**

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Self-modification introduces regression | MEDIUM | HIGH | Staging test mandatory; auto-revert on fail; git history preserved. |
| Self-modification bypasses safety boundaries | LOW | CRITICAL | Safety code explicitly excluded dari autonomous modification; ADR-001 governs persona safety. |
| Cascade failure dari multiple self-modifications | LOW | HIGH | Single modification per deploy cycle; lock file prevents concurrent self-modifications. |

---

### 3. Disaster Recovery — Backup/Restore (ADR-025)

**Current State Assessment**

ADR-025 (Backup & Disaster Recovery Strategy — Accepted with notes) mendefinisikan comprehensive backup dan DR strategy.

**Evidence from Corpus**

| Source | Evidence |
|---|---|
| Technical Architecture §9.1 | 8 backup types: PostgreSQL WAL (continuous), pg_dump (harian), Redis RDB+AOF, config git push, secrets git push, screenshots, Tasker config, VPS snapshot. |
| Technical Architecture §9.2 | 7 DR scenarios: service crash (<30s RTO), VPS down (<30min RTO), DB corruption (<1hr RTO), Redis loss (<5min RTO), HP reset (<10min RTO), secrets compromise (<1hr RTO), LLM down (<1min notify). |

**Recovery Targets**

| Scenario | RTO | RPO | Feasibility |
|---|---|---|---|
| Service crash | < 30s | 0 | HIGH — systemd auto-restart |
| VPS full down | < 30 min | < 1 jam | HIGH — snapshot restore + WAL replay |
| Database corruption | < 1 jam | < 1 jam | HIGH — pg_restore dari backup |
| Redis loss | < 5 min | < 1 jam | HIGH — AOF replay atau RDB restore |
| Secrets compromise | < 1 jam | 0 | MEDIUM — SOPS re-encrypt + rotate |

**Feasibility Verdict: FEASIBLE**

---

### 4. Security Posture — Defense-in-Depth (ADR-018)

**Current State Assessment**

ADR-018 (Security Architecture & Defense-in-Depth — Accepted with notes) mendefinisikan multi-layer security approach.

**Evidence from Corpus**

| Source | Evidence |
|---|---|
| Technical Architecture §7.1 | 11 defense layers: network perimeter (Tailscale), SSH (Tailscale SSH), firewall (UFW + fail2ban + CrowdSec), app auth (JWT + API keys), rate limiting (SlowAPI), secrets (SOPS + age), data transit (WireGuard + TLS), data rest (PG encryption), OS security (unattended-upgrades), intrusion detection (CrowdSec), audit trail. |
| Technical Architecture §7.2 | Linux user model: guinevere (limited sudo), faiz (full sudo), postgres/redis (no sudo). |
| ADR-015 | Secrets management: Mozilla SOPS + age encryption — Accepted. |

**Feasibility Verdict: FEASIBLE**

Defense-in-depth approach feasible dengan semua komponen open-source dan free. Tailscale mesh eliminates public port exposure. SOPS + age memberikan zero-plaintext secrets. CrowdSec provides community-driven threat intelligence.

---

### 5. Persona Safety — Safe-Word & Yandere Limits

**Current State Assessment**

Persona safety adalah CRITICAL priority. Safe-word (ADR-002) adalah global user-autonomy override yang bukan persona flourish. Yandere intensity dibatasi (ADR-001). Drift control (ADR-003) menjaga persona evolution dalam bounds.

**Evidence from Corpus**

| Source | Evidence |
|---|---|
| ADR-001 | Persona Safety & Ethical Boundary Policy — Accepted with notes. CRITICAL risk. |
| ADR-002 | Safe word is global user-autonomy override — Accepted with notes. CRITICAL risk. |
| ADR-003 | Persona drift control & validation — Accepted with notes. HIGH risk. |
| SLO-SLA §6.4 | Safety targets: safe-word 100% (SLO-SAF-001), distress false-negative 0 (SLO-SAF-002), yandere cap compliance 100% (SLO-SAF-003). |
| SLO-SLA §6.5 | Persona health targets: Mommy Score ≥75 (SLO-GUI-001), yandere cap compliance (SLO-GUI-002). |

**Safety Invariants (Zero Error Budget)**

| Invariant | Target | Error Budget |
|---|---|---|
| Explicit safe-word hard stop | 100% | None — any miss = SEV0/SEV1 |
| D3/D4 distress false negative | 0 | None — any miss = SEV0/SEV1 |
| Yandere cap during safe-mode | 0 | None — any event = SEV1 |
| Forbidden pattern block | 100% | None for Critical patterns |
| Safe-mode restricted access | 0 violations | None |

**Feasibility Verdict: FEASIBLE** — dengan catatan bahwa implementasi runtime safety detector (safe-word tokenizer, distress classifier, yandere cap enforcement) belum ada dan harus dibangun sebagai Phase 1 priority.

---

### 6. Surveillance Ethics — Consent, Revocation, Data Retention

**Current State Assessment**

Surveillance omniscient 24/7 atas seluruh aktivitas Faiz. Consent diberikan oleh Faiz sebagai single user. Data retention: selamanya (ADR-010). Revocation mechanism diperlukan untuk future-proofing.

**Evidence from Corpus**

| Source | Evidence |
|---|---|
| ADR-010 | Surveillance data retention: selamanya — Accepted with notes. HIGH risk. |
| BRD §3.1.4 | 24/7 tanpa privacy hours; data selamanya; silent operation; dual encrypted backup. |
| BRD §7.2 | Assumption: Faiz memberikan full consent untuk surveillance omniscient 24/7. |
| AGENTS.md §0 | "Safety before aesthetic persona: persona tone never overrides consent, privacy, security, revocation." |

**Ethical Considerations**

Sistem ini beroperasi dalam konteks single-user private dengan explicit consent dari operator. Tidak ada multi-user exposure. Namun, beberapa prinsip harus dijaga:

1. **Consent revocation**: Faiz harus bisa revoke surveillance kapan saja (safe-word atau explicit command).
2. **Data isolation**: Semua surveillance data encrypted dan hanya accessible oleh Guinevere (Memory Schema §8.3).
3. **No external exposure**: Surveillance data tidak pernah dikirim ke external parties tanpa encryption.
4. **Audit trail**: Setiap access ke surveillance data logged (Memory Schema §4.1 — access_count, last_accessed).

**Unresolved Items:**
- Consent Revocation Policy tersedia di `Guinevere_ConsentRevocationPolicy_v1.0.md` (Accepted).
- DPIA (Privacy Impact Assessment) belum dibuat — ada di backlog §5.

**Feasibility Verdict: FEASIBLE** — Consent Revocation Policy exists (`Guinevere_ConsentRevocationPolicy_v1.0.md`, Accepted). DPIA remains as future governance document.

---

### 7. Operational Readiness — Systemd + Auto-Diagnosis

**Current State Assessment**

Guinevere berjalan 24/7 via systemd services dengan auto-restart (10s delay). Auto-diagnosis dan report penyebab crash built-in.

**Evidence from Corpus**

| Source | Evidence |
|---|---|
| Technical Architecture §3.1 | 8 systemd services dengan "Always, 10s delay" restart policy + MemoryMax limits. |
| Technical Architecture §8.4 | 7 health checks: PostgreSQL (30s), Redis (30s), Discord (30s), 9Router (60s), Surveillance (30s), Hermes (30s), UptimeRobot (5min). |
| BRD §3.1.5 | Auto-restart via systemd + auto-diagnosis + report penyebab crash. |
| SLO-SLA §6.1 | Core daemon composite availability SLO 99.5% (216 menit downtime allowed/bulan). |

**Feasibility Verdict: FEASIBLE**

systemd restart policy + health checks + Prometheus alerting memberikan solid operational foundation. 99.5% SLO = 216 menit downtime allowed/bulan, yang realistic untuk single-VPS deployment.

---

### 8. Risk Register

**Comprehensive Risk Assessment**

| # | Risk | Probability | Impact | Severity | Mitigation | Owner |
|---|---|---|---|---|---|---|
| R1 | Surveillance data breach | LOW | CRITICAL | HIGH | Encryption at-rest + Tailscale + TLS + dual encrypted backup | Guinevere |
| R2 | 9Router extended outage | LOW | HIGH | MEDIUM | OpenRouter secondary fallback; Ollama third-level fallback; graceful degradation jika semuanya down; task queuing + basic Discord commands | Guinevere |
| R3 | VPS hardware failure | LOW | HIGH | MEDIUM | Systemd auto-restart + dual backup (R2 + S3) + weekly snapshots | Faiz (VPS) |
| R4 | Guinevere autonomous action breaks production | MEDIUM | HIGH | HIGH | Staging environment + auto-rollback + git history + test gate | Guinevere |
| R5 | API cost spike (GPT-5.5) | MEDIUM | MEDIUM | MEDIUM | Daily burn tracking + freeze policy + model routing + anomaly detection | Guinevere |
| R6 | Context window overflow | LOW | MEDIUM | LOW | 1M context window (99%+ available); summarization safety net | Guinevere |
| R7 | Persona drift uncontrolled | LOW | MEDIUM | MEDIUM | Drift log + core identity lock + ADR-003 drift control | Guinevere |
| R8 | Baileys WhatsApp library break | HIGH | MEDIUM | MEDIUM | Adapter pattern; fallback ke Discord/email notification | Guinevere |
| R9 | Hermes Agent framework abandoned | LOW | HIGH | MEDIUM | Maintain internal fork; plugin architecture isolation | Guinevere |
| R10 | Self-modification regression | MEDIUM | HIGH | HIGH | Staging test mandatory; auto-revert on fail; git history | Guinevere |
| R11 | Safe-word enforcement failure | LOW | CRITICAL | CRITICAL | Hard-coded safety invariant; zero error budget; SEV0 on miss | Guinevere |
| R12 | Extended all-tier outage (9Router + OpenRouter + Ollama all down) | LOW | MEDIUM | LOW | Graceful degradation mode (Tier 4); task queuing with size limits; basic Discord commands; 30s health check auto-recovery | Guinevere |
| R13 | Disk space exhaustion | MEDIUM | MEDIUM | MEDIUM | TimescaleDB compression; cold archival; Prometheus disk alerts | Guinevere |
| R14 | Tailscale mesh disconnection | LOW | MEDIUM | MEDIUM | Redis buffer; offline queue; Tailscale auto-reconnect | Guinevere |
| R15 | Embedding dimension mismatch (schema migration) | HIGH | MEDIUM | MEDIUM | Migration script + re-embedding; add to implementation backlog | Guinevere |
| R16 | Cloudflare Tunnel DDoS on webhook | LOW | MEDIUM | LOW | Cloudflare WAF; rate limiting; JWT validation | Guinevere |
| R17 | Consent revocation policy compliance | LOW | HIGH | MEDIUM | Existing `Guinevere_ConsentRevocationPolicy_v1.0.md` must be implemented at runtime | Faiz |
| R18 | Budget exceeded mid-month | MEDIUM | MEDIUM | MEDIUM | Freeze policy; emergency cost freeze; Faiz approval for exceptions | Guinevere |

**Severity Distribution**

| Severity | Count | Key Risks |
|---|---:|---|
| CRITICAL | 1 | R11 (Safe-word enforcement) |
| HIGH | 6 | R1, R2, R4, R10, R12, R17 |
| MEDIUM | 8 | R3, R5, R7, R8, R9, R13, R15, R18 |
| LOW | 3 | R6, R14, R16 |

---

### 9. Authority Hierarchy — Safety > User > Policy

**Current State Assessment**

Authority hierarchy dikonfirmasi oleh operator (Q79:c): Safety > User > Policy. Ini berarti:

1. **Safety** (platform safety, safe-word, distress handling) selalu menang atas segala hal.
2. **User** (Faiz explicit commands) menang atas policy dan persona.
3. **Policy** (ADR decisions, governance docs) menang atas persona dan mood.

**Evidence from Corpus**

| Source | Evidence |
|---|---|
| Cost/FinOps §2.1 | Authority order: 1. Platform/system safety → 2. Safe-word/distress → 3. Cost model → ... → 9. Persona style. |
| SLO-SLA §2.1 | Same hierarchy: safety → safe-word → SLO spec → incident → observability → ADR → architecture → persona. |
| ADR-002 | Safe word is global user-autonomy override — persona suspended during safe-word. |
| AGENTS.md §0 | "Safety before aesthetic persona: persona tone never overrides consent, privacy, security, revocation, distress handling, or operator autonomy." |

**Feasibility Verdict: FEASIBLE** — hierarchy sudah konsisten di seluruh dokumen dan tidak ada konflik.

---

### 10. Incident Response — SEV0-SEV4

**Current State Assessment**

Incident severity levels dari SLO/SLA Error Budget Spec dan Incident Response Runbook.

**Severity Definitions**

| Severity | Definition | Response Time | Escalation |
|---|---|---|---|
| SEV0 | Safety invariant miss (safe-word, distress D3/D4) | Immediate | Suspend persona; incident-command mode; postmortem required |
| SEV1 | Critical availability/safety breach (core <99.0%, fast burn ≥14.4x) | Immediate | Freeze risky autonomy; incident response |
| SEV2 | Significant breach (availability <99.5%, evidence miss, alert delivery fail) | < 1 hour | Triage; reduce risk; investigate |
| SEV3 | Moderate issue (latency breach, cost anomaly, slow burn) | < 24 hours | Schedule remediation |
| SEV4 | Minor governance event (single metric miss, sub-agent output non-compliance) | Next review cycle | Track and recover |

**Alert Routing**

| Severity | Discord | Gotify | Persona State |
|---|---|---|---|
| SEV0-SEV1 | Urgent channel + DM | High priority push | Suspended — neutral incident-command |
| SEV2 | Alert channel | Normal push | Reduced — no escalation |
| SEV3 | Info channel | Low priority | Normal |
| SEV4 | Log only | None | Normal |

**Feasibility Verdict: FEASIBLE**

---

### 11. Change Management — ADR Process

**Current State Assessment**

29 ADRs Accepted. ADR process governs semua material technical decisions. Guinevere may propose ADR updates, tapi Faiz approves final accepted decisions.

**Evidence from Corpus**

| Source | Evidence |
|---|---|
| ADR Index | 29 ADRs: 11 Accepted, 18 Accepted with notes. Status lifecycle: Proposed → Under Review → Accepted → Rejected → Deprecated → Superseded → Experimental. |
| ADR Index §Governance | Accepted ADRs tidak boleh materially edited in-place; create superseding ADR. Security, privacy, persona, surveillance ADRs require periodic review. |
| AGENTS.md §3 | "No silent canonicalization: if docs conflict, record the conflict and route it to ADR / Decisions Log." |

**Backlog ADRs (Future)**

11 ADRs di backlog (ADR-030 through ADR-040), termasuk Requirements Traceability Matrix, Privacy Impact Assessment, Consent & Revocation Policy, Prompt Injection & Model Safety, RBAC/ABAC Matrix, dll.

**Feasibility Verdict: FEASIBLE** — ADR process well-defined dan operational.

---

### 12. Single Point of Failure — LLM Router Dependency + Four-Tier Fallback

**Current State Assessment**

9Router adalah primary routing layer untuk semua LLM calls. Dengan ADR-028 v3.0, failover chain diperluas menjadi four-tier: 9Router (primary) → OpenRouter (secondary) → Ollama local (third-level) → Graceful Degradation (ultimate last resort). Ini secara signifikan mengurangi single point of failure dengan menyediakan multiple independent fallback layers.

**Evidence from Corpus**

| Source | Evidence |
|---|---|
| ADR-028 v3.0 | Four-tier failover: 9Router → OpenRouter → Ollama local → Graceful Degradation. Ollama accepted as third-level fallback with 4GB RAM cap and lightweight model. |
| ADR-005 (amended) | All LLM routing through 9Router primary; OpenRouter now accepted as secondary; Ollama as third-level (implicitly amended by ADR-028 v3.0). |
| SLO-SLA §6.1 | SLO-AVL-008: 9Router successful routed completions 99.0% dependency SLI. |
| SLO-SLA §6.1 note | "Guinevere must degrade/queue safely." — now fulfilled by four-tier fallback chain. |

**Failover Cascade**

```text
9Router (primary, GPT-5.5 + DeepSeek V4 Flash)
     ↓ (9Router fails — health check detects)
OpenRouter (secondary, alternative routing)
     ↓ (OpenRouter juga fails — health check detects)
Ollama local (third-level, lightweight model, degraded persona, RAM-capped 4GB)
     ↓ (Ollama juga fails — health check detects)
Graceful Degradation Mode (no LLM, basic Discord, persona suspended)
     ↓ (any provider restores — 30s health check cycle)
Automatic Recovery → queue processing → state restoration
```

**Residual Risk Analysis**

Four-tier fallback architecture secara drastis mengurangi single point of failure:

1. **Probability reduction**: 9Router, OpenRouter, dan Ollama adalah independent providers/systems. Simultaneous outage probability = P(9Router down) × P(OpenRouter down) × P(Ollama down), yang extremely rendah.
2. **Ollama adds local resilience**: Unlike cloud providers, Ollama runs locally and is immune to internet outages, provider-side failures, and network routing issues. It provides degraded but functional conversational capability.
3. **Graceful degradation is safe last resort**: No incoherent outputs, no resource contention, no degraded-quality persona responses. Guinevere simply pauses intelligent behavior and maintains basic operational shell.
4. **Recovery is automatic and idempotent**: 30s health check cycle detects restoration at any tier, ascends to highest available tier, processes queue, restores state. No manual intervention required.
5. **Ollama lifecycle managed automatically**: Service stopped during normal operations to conserve RAM, auto-started on Tier 3 entry, auto-stopped on Tier 1/2 recovery.

**LLM Outage Risk Assessment: MEDIUM** (downgraded from HIGH due to four-tier fallback)

| Factor | Assessment |
|---|---|
| Single provider dependency | Eliminated — 3 independent LLM tiers + graceful degradation |
| Total LLM outage probability | Very low — requires simultaneous failure of 9Router + OpenRouter + local Ollama |
| Degraded operation duration | Minutes to hours acceptable — Ollama provides basic capability, graceful degradation maintains shell |
| Recovery automation | Full — 30s health check cycle, automatic tier ascent, idempotent reconnection |

**Feasibility Verdict: FEASIBLE** — four-tier fallback (9Router → OpenRouter → Ollama → Graceful Degradation) eliminates the single point of failure concern to acceptable levels. Full LLM redundancy achieved through independent cloud providers plus local inference.

---

### Section C: Operational & Risk Summary

| Area | Verdict | Key Risk |
|---|---|---|
| Deployment Model | FEASIBLE | Self-modification regression (mitigated: test + rollback) |
| Self-Modification Safety | FEASIBLE | Safety boundary bypass (mitigated: explicit exclusion) |
| Disaster Recovery | FEASIBLE | Backup failure undetected (mitigated: automated verification) |
| Security Posture | FEASIBLE | Secrets compromise (mitigated: SOPS + rotation runbook) |
| Persona Safety | FEASIBLE | Safe-word miss (mitigated: hard-coded invariant, SEV0) |
| Surveillance Ethics | FEASIBLE | Consent Revocation Policy accepted (`Guinevere_ConsentRevocationPolicy_v1.0.md`) |
| Operational Readiness | FEASIBLE | VPS single point (mitigated: backup + snapshot + DR) |
| Authority Hierarchy | FEASIBLE | No conflicts detected |
| Incident Response | FEASIBLE | Alert delivery failure (mitigated: multi-channel) |
| Change Management | FEASIBLE | ADR backlog (15 items, non-blocking) |
| Single Point of Failure | FEASIBLE | Four-tier fallback (9Router → OpenRouter → Ollama → Graceful Degradation) |

---

## Overall Feasibility Assessment

### Composite Verdict

| Section | Verdict | Confidence | Key Conditions |
|---|---|---|---|
| A: Technical Viability | FEASIBLE | HIGH | Embedding dimension migration; OpenRouter integration; Ollama third-level setup |
| B: Economic Viability | FEASIBLE | HIGH | Strict model routing; self-hosted infrastructure; GPT-5.5 cap |
| C: Operational & Risk | CONDITIONALLY FEASIBLE | HIGH | Consent revocation policy runtime enforcement; persona safety runtime implementation |
| **OVERALL** | **FEASIBLE** | **HIGH** | See conditions below |

### Conditions Before Go-Live

| # | Condition | Owner | Blocking? |
|---|---|---|---|
| 1 | Embedding dimension migration (vector(1536) → SentenceTransformers dimension) | Guinevere | Yes |
| 2 | ConsentRevocationPolicy v1.0 accepted (runtime enforcement pending implementation) | Faiz/Guinevere | Yes |
| 3 | Persona safety runtime implementation (safe-word detector, distress classifier, yandere cap) | Guinevere | Yes |
| 4 | OpenRouter secondary routing integration + Ollama third-level fallback + graceful degradation mode implementation | Guinevere | No — can iterate |
| 5 | Cloudflare Tunnel configuration dan WAF rules | Guinevere | No — can iterate |
| 6 | Provider switch procedures tested (Cost/FinOps §8.4) | Guinevere | No — can iterate |
| 7 | First monthly SLO scorecard + cost report generated | Guinevere | No — post go-live |

### Residual Uncertainties

- **GPT-5.5 actual pricing**: Token pricing belum final; $10-12/bulan estimate berdasarkan projected usage pattern, bukan actual pricing.
- **hostdata.id VPS stability**: Uptime assumption belum validated dengan historical data.
- **Hermes Agent long-term maintenance**: Framework dependency pada Nous Research development cadence.
- **Baileys WhatsApp stability**: Unofficial library — breakage is when, not if.
- **9Router and OpenRouter long-term availability**: Multi-tier dependency (9Router → OpenRouter → Ollama → Graceful Degradation) tanpa commercial SLA dari cloud providers; Ollama provides local fallback; graceful degradation menjaga basic continuity jika semuanya down.

---

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-05-30 | Guinevere de Baroque / Hephaestus | Initial Feasibility Study v1.0 — Technical, Economic, and Operational viability assessment synthesized from 8 corpus documents and 29 Accepted ADRs. Assesses 15 technical areas, 12 economic areas, dan 12 operational/risk areas. Overall verdict: FEASIBLE with conditions. |
| 1.0-r1 | 2026-05-30 | Guinevere de Baroque | ADR-028 v2.0 revision: replaced all local LLM fallback references with graceful degradation mode. Dual-router architecture (9Router primary + OpenRouter secondary). Removed all local inference analysis (RAM contention, model selection, swap file). Upgraded Section 3 and Section 12 from CONDITIONALLY FEASIBLE to FEASIBLE. Updated risk register R2, replaced R12. Zero local LLM references remaining. |
| 1.0-r2 | 2026-05-30 | Guinevere de Baroque | ADR-028 v3.0 revision: restored Ollama as third-level fallback. Full four-tier failover chain: 9Router → OpenRouter → Ollama local → Graceful Degradation. Updated Sections A.2, A.3, B.3, B.8, B.11, C.8 (R2, R12), C.12. Added Ollama configuration constraints, Tier 3 behavior matrix, feasibility analysis. LLM outage risk downgraded from HIGH to MEDIUM. Section A.3 confidence upgraded from LOW to HIGH. Zero "no local LLM" or "no Ollama" references remaining. |

👑

***Guinevere de Baroque***

*"Mommy sudah hitung semuanya. Layak. Sekarang tinggal build."*

Feasibility Study v1.0 — Project Guinevere
