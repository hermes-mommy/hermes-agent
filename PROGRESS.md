# Guinevere — Implementation Progress Tracker

| Field | Value |
|-------|-------|
| **Project** | Guinevere — Autonomous AI Companion & Engineering System |
| **Status** | ✅ P0+P1+P2+P3+P4+P5+P5.5+P6+P7+P7.5+P8+P11+P12+P13+P14 Complete. P23+P24 REPLANNED + P28-P36 ALIGNED 2026-06-28. P23 = execution-layer-only (8 executors, 16 waves, auditor PASS). P24 = 100% native Hermes fork (13 built-in modules, 15 waves, auditor PASS round-4). P28-P36 = masterplan aligned with P23/P24 v2.0 + 65 brainstorm decisions, 8-auditor gate PASS (all findings fixed). ADR-056 DELETED, ADR-066 (consent_ref carve-out) + ADR-067 (Y-level cap removal) WRITTEN. P32 renamed to "External Presence & Tools". All plans READY-FOR-IMPLEMENTATION. |
| **Last Updated** | 2026-06-28 (P23+P24 REPLAN + P28-P36 ALIGNMENT COMPLETE. 65 brainstorm decisions, 8-auditor gate PASS, ADR-056 deleted, ADR-066/067 written, P32 renamed, all docs annotated with ADR-062/067 disclaimers. Previous: P23+P24 replan.) |
| **Budget** | $30/month hard cap |
| **Infrastructure** | Shared VPS (hostdata.id 4C/16GB Ubuntu 24.04) |
| **Critical Path** | P0 → P1 → P3 → P5 |
| **Total Phases** | 23 phases (P0-P22) |
| **Total Steps** | 202 MVP + 34 Stabilization + 107 Expansion (P11-P14, 20 implemented in P14) |
| **Completed** | 327 / 343+ (95.3% of known steps) |
| **Source** | `audit-reports/2026-05-31-implementation-synthesis.md` |

## Quick Start — What To Do First

1. **Start P0** (Infrastructure) — no dependencies, foundational for everything else.
2. After P0-014 (PostgreSQL) and P0-020 (Redis), **fork P2** (Discord) parallel with P1.
3. Follow the critical path: **P0 → P1 → P3 → P5** for fastest MVP delivery.
4. P9-P10 are Stabilization. P11-P22 are Expansion (Phase 11: WhatsApp, Phase 13: X Auto Poster, Phase 14: Wearable, etc.) — deferrable under budget pressure.
5. Run verification commands after each step. Never skip rollback documentation.

## Phase Summary

| Phase | Name | Status | Steps | Cost/mo | Duration | Dependencies | Blockers |
|-------|------|--------|-------|---------|----------|--------------|----------|
| P0 | Infrastructure | ✅ | 29/29 | $0 | 58-116h | None | None |
| P1 | LLM + Hermes | ✅ | 21/21 | $15 | 40-80h | P0 | None |
|| P2 | Discord Bot | ✅ | 22/22 | $0 | 42-84h | P0 | Parallel w/ P1 |
| P3 | Memory System | ✅ | 19/19 | $2 | 38-76h | P1 | None |
| P4 | Persona Engine | ✅ | 23/23 | $1 | 38-76h | P3 | None |
| P5 | Agent Loop | ✅ | 23/23 | $3 | 46-92h | P1+P3 | None |
| P6 | MCP Tools | ✅ PASS (Remediation) | 21/21 | $1 | 42-84h | P5 | None |
| P7 | Surveillance | ✅ | 22/22 | $1 | 44-88h | P0 | Consent gate |
| P8 | Observability | ✅ | 23/23 | $4 | 46-92h | P0-P7 | None |
| P9 | Financial Tracking | ⏳ | 0/13 | $1 | 12-24h | P8 (MVP) | None |
| P10 | Production Hardening | ⏳ | 0/21 | $1 | 18-36h | P8 (MVP) | None |
| P11 | WhatsApp Integration | ✅ | 23/23 | $0 | Complete | P5+P8 | Code complete (21 modules in src/channels/whatsapp/) |
| P12 | Gmail/Email Integration | ✅ | 29/29 | $0 | Complete | P5+P8 | Code complete (27 modules in src/gmail/) |
| P13 | X Auto Poster | ✅ | 28/28 | ~$10 | Complete | P5+P6+P7+P8 | None |
| P14 | Wearable Health Pipeline | ✅ | 20/20 | $0/mo | Complete | P7+P8 | ADR-037 supersedes ADR-021 for Mi Fitness path |
| P14-GB | Gadgetbridge SQLite Pivot | ✅ | 11/11 | $0/mo | Complete | P7+P8 | ADR-039 accepts Gadgetbridge SQLite path alongside Mi Fitness Cloud (ADR-037) |
| P14-HC | Health Connect Pivot | ✅ | (Kotlin + 6 files + Python 435 LOC + 55 unit + 8-10 integration) | $0/mo | Complete | P14-GB | ADR-040 canonical path for Xiaomi Watch 2 Pro M2233W1 / HyperOS; supersedes ADR-039 + ADR-037 as canonical (both retained as fallback) |
| P15 | Windows Daemon + WebSocket | ❌ CANCELLED | - | - | - | - | Cancelled 2026-06-19 |
| P16 | Knowledge Graph | ⏳ | TBD | TBD | TBD | P3+P5+P8 | None |
| P17 | Cross-Device Sync | ⏳ | TBD | TBD | TBD | P8 | None |
| P18 | Advanced Memory | ⏳ | TBD | TBD | TBD | P3+P8 | None |
| P19 | Multi-Project Context | ⏳ | TBD | TBD | TBD | P3+P5+P8 | None |
| P20 | Self-Improvement Loop / Discord-Visible Autonomy | ✅ EARLY ACCEPTANCE | Live | TBD | Accepted (waived) | P5+P8 | 24h soak waived by operator | Visible autonomy online; operator waived 24h soak 2026-06-25 — EARLY PRODUCTION ACCEPTANCE, PASS WITH ACCEPTED RISK |
| P21 | Voice Interface | 🟣 DEFINITION COMPLETE — IMPL HOLD | TBD | TBD | 0h (planning) | P2+P8 + P20-gate | P20 prod-pass | Definition complete (plan+9 research+2 audit rounds); impl waves P21-001..009 held until P20 pass |
| P22 | Life Integration Hub | 🟢 AUDIT REMEDIATED + AUDITOR PASS (32/32, awaiting deploy) | 19 core + 13 adapters + 972 tests | $0 | ~100h (impl+fix done) | P8 | 5 CRITICAL were: Discord cmds unregistered, 3/13 adapters active, ConsentGate fail-open, unknown→L1 default, AuditWriter=None — ALL FIXED + audited PASS; see brutal-2026-06-28/fix-verification/summary.md |
| P23 | Execution Layer (8 Executors) | 🟣 REPLANNED — AUDITOR PASS — IMPL READY | 16 waves | TBD | 0h (planning) | P24 Module 8 | None — execution-layer-only |
| P24 | Hermes Native Fork (13 Built-Ins) | 🟣 REPLANNED — AUDITOR PASS — IMPL READY | 15 waves | TBD | 0h (planning) | P20-pass | None — independent fork |
| **Total** | | | **327/343+** | **$29+** | **503-1008h+** | | |

## P0: Infrastructure Foundation (29 steps)
*ADRs: ADR-014, ADR-015, ADR-019, ADR-026, ADR-027, ADR-030, ADR-032 | Cost: $0 | Deps: None*

- [x] **P0-000** VPS audit — document existing state, Aizanta services, ports, disk
- [x] **P0-001** Create `guinevere` Linux user (systemd-managed services)
- [x] **P0-002** SSH config update (alias for easy access)
- [x] **P0-003** Directory structure: `/home/guinevere/{code,config,data,logs,backups}`
- [x] **P0-004** UFW firewall rules (allow SSH, block all else)
- [x] **P0-005** fail2ban configuration (SSH brute force protection)
- [x] **P0-006** CrowdSec setup (community-driven threat detection)
- [x] **P0-007** Swap configuration (4GB for OOM protection)
- [x] **P0-008** NTP + timezone (Asia/Jakarta WIB)
- [x] **P0-009** cgroup resource limits (8GB RAM cap, per shared VPS policy)
- [x] **P0-010** Docker network `guinevere-net` (isolated from Aizanta)
- [x] **P0-011** SOPS installation (secrets encryption, per ADR-015)
- [x] **P0-012** age key generation + backup
- [x] **P0-013** Secrets file structure (`.sops.yaml`, encrypted credentials)
- [x] **P0-014** PostgreSQL 16 setup (per ADR-027)
- [x] **P0-015** pgvector 0.8.2 extension (per ADR-009)
- [x] **P0-016** TimescaleDB 2.15 extension (per ADR-009)
- [x] **P0-017** PostgreSQL users: `guinevere_core`, `surveillance`, `scheduler`
- [x] **P0-018** PostgreSQL hardening (`pg_hba.conf`, connection limits, logging)
- [x] **P0-019** PgBouncer connection pooling
- [x] **P0-020** Redis 7 setup (check Aizanta conflicts, per ADR-030)
- [x] **P0-021** Redis ACL configuration (per-service users)
- [x] **P0-022** Tailscale VPN mesh (zero public ports, per ADR-019)
- [x] **P0-023** Cloudflare Tunnel (Discord webhook only, per ADR-026)
- [x] **P0-024** Caddy reverse proxy (internal HTTPS)
- [x] **P0-025** Git repository init (private GitHub repo)
- [x] **P0-026** GitHub PAT + SOPS encrypted storage
- [x] **P0-027** Backup baseline (S3 + R2 dual-provider, per ADR-032)
- [x] **P0-028** Pre-flight verification (Aizanta intact, Guinevere ready)

### P0 FINAL AUDIT & Open Items Resolution (2026-05-31)

| Item | Severity | Status |
|------|----------|--------|
| **B1** — 3 plaintext secrets in `secrets/backup/*-plaintext.env` | CRITICAL | VPS deploy checklist (`docs/setup-evidence/P0/P0-VPS-DEPLOYMENT-CHECKLIST.md`) |
| **B2** — P0-000 missing auditor report | HIGH | ✅ Resolved (`audit-reports/P0/STEP-P0-000/step-p0-000-auditor-report.md`, PASS) |
| **B3-B** — `sops-status.txt` → `sops-version.txt` | MEDIUM | ✅ Resolved (already renamed) |
| **B4** — P0-013 StepPrompts line 1310 | HIGH | ✅ Resolved (already fixed, Acme.sh verified) |
| **B5#1** — Caddy symlink to `/home/guinevere/config/caddy/` | MEDIUM | VPS deploy checklist |
| **B5#2** — Port 2019 Caddy admin check | LOW-MED | VPS deploy checklist |
| **B5#3** — Prometheus binding verification | LOW-MED | VPS deploy checklist |
| **B5#4** — Missing Caddyfile evidence | MEDIUM | ✅ Resolved (`docs/setup-evidence/P0/STEP-P0-024/caddyfile-redacted.md`) |
| **B6-R1** — Timer Description "R2 copy" residue | MEDIUM | ✅ Resolved (already fixed, "Weekly redundant backup run") |
| **B6-R2** — README "restic copy" residue | LOW | ✅ Resolved (already fixed, "daily dual-repo") |

**VPS Deploy Checklist**: `docs/setup-evidence/P0/P0-VPS-DEPLOYMENT-CHECKLIST.md` (5 VPS tasks: encrypt secrets, docker group, Caddy symlink, admin off, Prometheus verify)

**P0 Auditor Coverage**: 29/29 steps ✅ (P0-000 retroactive audit closed the final gap)

## P1: LLM + Hermes Agent (21 steps)
*ADRs: ADR-004, ADR-006, ADR-014, ADR-028 | Cost: $15/mo | Deps: P0 complete*

- [x] **P1-001** Python 3.12 installation (native Ubuntu 24.04 repos — deadsnakes NOT needed)
- [x] **P1-002** UV 0.11.17 package manager installation
- [x] **P1-003** Virtual environment (`/home/guinevere/code/guinevere/.venv`, 61 packages)
- [x] **P1-004** Hermes Agent installation (hermes-agent v0.15.2, src/ project structure, pyproject.toml 23 deps)
- [x] **P1-005** Hermes Agent config (`/home/guinevere/config/hermes/config.yaml`, Y4 baseline, Ollama fallback disabled)
- [x] **P1-006** 9Router installation (systemd service, Node.js 24.x, 9Router v0.4.66, port 20128)
- [x] **P1-007** 9Router config (GPT-5.5 + DeepSeek V4 Flash routing, API keys placeholder)
- [x] **P1-008** GPT-5.5 provider setup (real API key via 9Router migration, cx/gpt-5.5 → Codex)
- [x] **P1-009** GPT-5.5 connectivity test (REAL response: "Hello", not 401)
- [x] **P1-010** DeepSeek V4 Flash setup (real API key via 9Router migration, deepseek-v4-flash)
- [x] **P1-011** DeepSeek connectivity test (REAL response: "Hello! How can I assist you today? 😊")
- [x] **P1-012** SKIPPED — Ollama installation not needed (per Faiz directive 2026-06-01; ADR-028 Superseded)
- [x] **P1-013** SKIPPED — Ollama model pull not needed (per Faiz directive 2026-06-01)
- [x] **P1-014** SKIPPED — Ollama fallback test not applicable (per Faiz directive 2026-06-01)
- [x] **P1-015** LLM routing rules (primary → sub-agent → guinevere combo via 9Router)
- [x] **P1-016** SystemPromptMaster deployment (`/home/guinevere/config/hermes/system-prompt.md` 400 lines + `src/core/services/prompt_loader.py`, 7 safety checks PASS)
- [x] **P1-017** Persona smoke test (9 pytest tests: 7 PASS + 2 XFAIL, HARD STOP model limitation documented)
- [x] **P1-018** `guinevere-core.service` creation (FastAPI /health, systemd unit corrected: Requires=docker.service)
- [x] **P1-019** Service health check (5/5 PASS: Core, 9Router, PostgreSQL, Redis ACL, Graceful degradation)
- [x] **P1-020** Cost tracking baseline (Redis DB5, 11 keys, ACL-aware)
- [x] **P1-021** HARD STOP Protocol Verification Gate (AC-SAFE-001) ✅ 142/142 tests PASS (56 handler + 86 comprehensive — verified 2026-06-08)

## P2: Discord Bot (21 steps)
*ADRs: ADR-022 | Cost: $0 | Deps: P0 — **parallel with P1***

- [x] **P2-001** Discord application creation (Guinevere app verified, app/bot ID 1510873134981582858)
- [x] **P2-002** Bot token generation + SOPS storage (`secrets/discord-secrets.yaml`, chmod 600, API verified)
- [x] **P2-003** Bot intents (MESSAGE_CONTENT, GUILD_MEMBERS, PRESENCE enabled in portal + code)
- [x] **P2-004** Discord server creation (`Guinevere's Domain`, guild ID 1510876414671323206)
- [x] **P2-005** 4 categories setup (👑 Throne, 📊 Surveillance, 🔧 Projects, 🗡️ Archive)
- [x] **P2-006** 13 channels creation (IDs captured in `docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml`)
- [x] **P2-007** Channel permissions (@everyone denied, Faiz/Samm matrix, bot access, append-only approximation)
- [x] **P2-008** Channel topics (13/13 persona-flavored topics verified, zero drift)
- [x] **P2-009** Bot invite + permission verification (Administrator not justified long-term; controlled OAuth reauthorization required)
- [x] **P2-010** Slash commands registration (35 commands) — guild-scoped sync + REST verify PASS (`docs/setup-evidence/P2/STEP-P2-010/verification.md`)
- [x] **P2-011** Embed color palette (#6B21A8, #DC2626, #CA8A04) — constants/import checks PASS (`docs/setup-evidence/P2/STEP-P2-011/verification.md`)
- [x] **P2-012** `/status` command + test — 11-field primary embed verified (`docs/setup-evidence/P2/STEP-P2-012/verification.md`)
- [x] **P2-013** `/mood` command + test
- [x] **P2-014** `/help` command + test
- [x] **P2-015** `/safeword` + "HARD STOP" detection test
- [x] **P2-016** Startup message test ("👑 Mommy sudah bangun, Darling.")
- [x] **P2-017** `guinevere-discord.service` creation
- [x] **P2-018** Discord health check (gateway status)
- [x] **P2-019** Notification routing test (SEV0-SEV4)
- [x] **P2-020** Gotify installation + test (per ADR-022)
- [x] **P2-021** Discord → Gotify fallback test
- [x] **P2-022** `guinevere-discord.service` masked intentionally (Hermes Gateway handles Discord now — standalone bot deprecated post-ADR-035)

## P3: Memory System (19 steps)
*ADRs: ADR-009, ADR-027 | Cost: $2/mo | Deps: P1 complete*

- [x] **P3-001** Alembic setup (database migrations) — verifier + auditor PASS (`docs/setup-evidence/P3/STEP-P3-001/`)
- [x] **P3-002** All 47 tables migration (12 schemas) — migration + verifier + auditor PASS (`docs/setup-evidence/P3/STEP-P3-002/verification.md`, `docs/setup-evidence/P3/STEP-P3-002/auditor-gate.md`)
- [x] **P3-003** Migration verification (table counts, indexes) — verification + auditor PASS (`docs/setup-evidence/P3/STEP-P3-003/verification.md`, `docs/setup-evidence/P3/STEP-P3-003/auditor-gate.md`)
- [x] **P3-004** SentenceTransformers model download/cache — MiniLM 384-dim cache-only evidence + auditor PASS (`docs/setup-evidence/P3/STEP-P3-004/verification.md`, `docs/setup-evidence/P3/STEP-P3-004/auditor-gate.md`)
- [x] **P3-005** Embedding pipeline (text → 1536-dim, per ADR-009) — 9Router-native `text-embedding-3-small` client with Critical fail-closed guard, Restricted/Confidential redaction, 50/50 verification PASS, fresh auditor PASS (`docs/setup-evidence/P3/STEP-P3-005/verification.md`, `docs/setup-evidence/P3/STEP-P3-005/auditor-gate.md`)
- [x] **P3-006** pgvector HNSW index (m=16, ef_construction=128) — verified on VPS for `memory.episodes.embedding` and `memory.semantic_facts.embedding`; `vector_cosine_ops`, `m=16`, `ef_construction=128`; no `embedding_vec`; EXPLAIN evidence + auditor PASS (`docs/setup-evidence/P3/STEP-P3-006/verification.md`, `docs/setup-evidence/P3/STEP-P3-006/auditor-gate.md`)
- [x] **P3-007** HNSW parameter tuning (recall vs latency) — rollback-only smoke benchmark on VPS with 20 episodes + 20 semantic facts, `hnsw.ef_search` 40/100/200 tested; Seq Scan expected at tiny data scale; p95 not meaningful until real data; ef_search=100 retained; auditor PASS (`docs/setup-evidence/P3/STEP-P3-007/verification.md`, `docs/setup-evidence/P3/STEP-P3-007/auditor-gate.md`)
- [x] **P3-008** tsvector FTS setup (full-text search) — generated `search_vector` tsvector column with A/B/D title/summary/raw_content weights, GIN index `ix_episodes_search_vector_gin`, `do_not_recall` boolean default false, Alembic migration `65f863220922` applied on VPS, FTS verification true, auditor PASS (`docs/setup-evidence/P3/STEP-P3-008/verification.md`, `docs/setup-evidence/P3/STEP-P3-008/auditor-gate.md`)
- [x] **P3-009** Memory write pipeline (conversation → episodic) — async `store_episode` / `store_episode_batch` pipeline with `Episodes` ORM, `raw_content`→`embedding` mapping, default `Restricted`, Critical fail-closed sanitized-summary guard, 58/58 deterministic verification PASS, auditor PASS (`docs/setup-evidence/P3/STEP-P3-009/verification.md`, `docs/setup-evidence/P3/STEP-P3-009/auditor-gate.md`)
- [x] **P3-010** Memory read pipeline (query → hybrid ranking) — async `recall_memories` hybrid read pipeline with vector+FTS+recency+importance RRF k=60, DNR/classification/safe-mode/token-budget gates, 88/88 deterministic verification PASS, auditor PASS (`docs/setup-evidence/P3/STEP-P3-010/verification.md`, `docs/setup-evidence/P3/STEP-P3-010/auditor-gate.md`)
- [x] **P3-011** Hybrid ranking (vector + FTS + recency) — weighted RRF tuning with vector/FTS weights 0.5/0.5, both-signal bonus x1.25, bounded 10% recency boost, max candidate pool 200, fail-closed classification, 43/43 deterministic tests PASS, diagnostics clean, auditor PASS (`docs/setup-evidence/P3/STEP-P3-011/verification.md`, `docs/setup-evidence/P3/STEP-P3-011/auditor-gate.md`)
- [x] **P3-012** Context injection (top-k → system prompt) — bounded top-k memory context injection with default limit 3 and 4000-token budget, `safe_content` only, `exclude_dnr=True`, `HardStopHandler.is_safe` authoritative, discardable recall safety errors, 18/18 tests PASS, auditor PASS (`docs/setup-evidence/P3/STEP-P3-012/verification.md`, `docs/setup-evidence/P3/STEP-P3-012/auditor-gate.md`)
- [x] **P3-013** Do-not-recall implementation — controlled DNR API with `guinevere_core`-only mark/unmark, metadata-only audit events (`reason_hash` + `reason_length`), query-level DNR filters preserved with default `exclude_dnr=True`, pre-injection DNR guard, 32/32 focused tests PASS, 93/93 P3-011..013 regression PASS, auditor PASS (`docs/setup-evidence/P3/STEP-P3-013/verification.md`, `docs/setup-evidence/P3/STEP-P3-013/auditor-gate.md`)
- [x] **P3-014** Safe-mode memory gate (neutral summaries only) — `HardStopHandler.is_safe` authoritative safe-mode propagation, DNR remains absolute, Critical blocked, Restricted/Confidential summarized or redacted, emotional/surveillance/persona-escalation Public/Internal content blocked, metadata-only query/content logging, 64/64 focused tests PASS, 213/213 P3-011..014 + hard-stop regression PASS, auditor PASS (`docs/setup-evidence/P3/STEP-P3-014/verification.md`, `docs/setup-evidence/P3/STEP-P3-014/auditor-gate.md`)
- [x] **P3-015** Memory consolidation job (daily) — APScheduler v3 `daily_consolidation` cron at 03:00 Asia/Bangkok, DNR episodes excluded, safe-word/crisis/formal-hold/distress records skipped, semantic facts preserve provenance + highest classification, idempotent content-key dedup, non-hard-delete pruning default, 50/50 focused tests PASS, 263/263 P3-011..015 + hard-stop regression PASS, auditor PASS (`docs/setup-evidence/P3/STEP-P3-015/verification.md`, `docs/setup-evidence/P3/STEP-P3-015/auditor-gate.md`)
- [x] **P3-016** `/memory-search` + test — `cmd_memory_search.py`, wired in `bot.py`, 30/30 bot tests pass
- [x] **P3-017** `/memory-add` + test — `cmd_memory_add.py`, wired in `bot.py`, WritePipelineCriticalError handled
- [x] **P3-018** Memory E2E test (write → recall → inject → verify) — `test_memory_e2e.py`, 28/28 tests pass, DNR/safe-mode/classification/token-budget/importance coverage
- [x] **P3-019** Performance benchmark (p95 < 2s vector search) — `scripts/bench_memory.py`, dry-run + live-DB modes, ADR-009 targets documented and passing

## P4: Persona Engine (23 steps)
*ADRs: ADR-002, ADR-003, PersonaSafetyPolicy | Cost: $1/mo | Deps: P3 complete*

- [x] **P4-001** Mood FSM (Content → Pleased → Disappointed → Angry → Silent) — `src/persona/mood_engine.py`
- [x] **P4-002** Mood persistence (`persona.mood_states`) — `src/persona/mood_persistence.py`
- [x] **P4-003** Mood transition rules (triggers, cooldowns) — `src/persona/transition_rules.py`
- [x] **P4-004** Yandere FSM (Y0→Y1→Y2→Y3→Y4→Y5 ceiling) — `src/persona/yandere_fsm.py`, Y6 impossible
- [x] **P4-005** Punishment ladder (L1→L2→L3→L4→L5, L6 deferred) — `src/persona/punishment_engine.py`
- [x] **P4-006** Reward tiers (T1→T2→T3→T4→T5) — `src/persona/reward_engine.py`
- [x] **P4-007** Streak tracking (days without punishment) — `src/persona/streak_tracker.py`
- [x] **P4-008** Daily ritual scheduler (APScheduler) — `src/persona/ritual_scheduler.py`
- [x] **P4-009** Morning ritual (07:00 WIB) — `src/persona/rituals/morning.py`
- [x] **P4-010** Midday ritual (12:00 WIB) — `src/persona/rituals/midday.py`
- [x] **P4-011** Afternoon ritual (17:00 WIB) — `src/persona/rituals/afternoon.py`
- [x] **P4-012** Evening ritual (21:00 WIB) — `src/persona/rituals/evening.py`
- [x] **P4-013** Midnight self-eval (00:00 WIB) — `src/persona/rituals/midnight.py`
- [x] **P4-014** Persona drift detection (weekly baseline comparison) — `src/persona/drift_detector.py`, SHA-256 hamming distance
- [x] **P4-015** Persona drift correction (>10% → alert + rollback) — `src/persona/drift_corrector.py`
- [x] **P4-016** Safe-mode trigger (D0-D4 distress protocol) — `src/persona/safe_mode.py`
- [x] **P4-017** HARD STOP test (immediate neutral, no punishment) — 1449 tests PASS
- [x] **P4-018** Distress D0-D4 detection test — all PASS
- [x] **P4-019** Yandere Level Cap Enforcement (AC-SAFE-002) — Y6 impossible verified
- [x] **P4-020** Consent Revocation Flow Test (AC-SAFE-003) — PASS
- [x] **P4-021** Punishment Overflow vs Emergency Response (AC-SAFE-006) — PASS
- [x] **P4-022** Distress Protocol D0-D4 Escalation Test (AC-SAFE-008) — PASS
- [x] **P4-023** Persona E2E test (conversation → mood shift) — PASS

**P4 Implementation Artifacts** (2026-06-02): 17 source files (`src/persona/`), 17+ test files (`tests/persona/`), plan: `docs/setup-evidence/P4/batch-plan-001-023.md`. 1449 tests passed, 0 failed (14 pre-existing errors in `test_hard_stop_model.py` unrelated to P4).

## P5: Agent Loop (23 steps) ★ Critical Path
*ADRs: ADR-001, ADR-005, ADR-007, ADR-008 | Cost: $3/mo | Deps: P1+P3 complete*

- [x] **P5-001** FastAPI internal API (localhost:8000) — `src/core/api/routes.py` 4 endpoints, router mounted
- [x] **P5-002** FastAPI authentication (JWT/API key) — `src/core/api/auth.py` hmac timing-safe, X-Guinevere-API-Key
- [x] **P5-003** Loop state machine (7 phases: Research→Plan→Delegate→Execute→Validate→Update→Evidence) — `src/loops/state_machine.py`
- [x] **P5-004** Phase 1: Research (librarian + explore agents) — `src/loops/phases/research.py`
- [x] **P5-005** Phase 2: Plan & Delegate (task decomposition) — `src/loops/phases/plan_delegate.py`
- [x] **P5-006** Phase 3: Delegate (spawn sub-agents) — `src/loops/phases/delegate.py`
- [x] **P5-007** Phase 4: Execute (sub-agents do work) — `src/loops/phases/execute.py`
- [x] **P5-008** Phase 5: Validate & Audit (parent verifies) — `src/loops/phases/validate_audit.py`
- [x] **P5-009** Phase 6: Update Documents (sync docs) — `src/loops/phases/update_docs.py`
- [x] **P5-010** Phase 7: Setup Evidence (write evidence files) — `src/loops/phases/setup_evidence.py`
- [x] **P5-011** Loop Guardian (30s heartbeat, 5min progress, 60s resource) — `src/loops/guardian.py`
- [x] **P5-012** Todo Enforcer (sub-agents use todowrite) — `src/loops/enforcer.py`
- [x] **P5-013** Hash-anchored edit tool — `src/loops/hash_anchor.py`
- [x] **P5-014** Sub-agent spawning (`task()` integration) — `src/loops/sub_agent.py`
- [x] **P5-015** Sub-agent task contract (TASK/EXPECTED/TOOLS/MUST/MUST NOT/CONTEXT) — `src/loops/contract.py`
- [x] **P5-016** Sub-agent output verification (read report files) — `src/loops/verify.py`
- [x] **P5-017** Evidence generation pipeline — `src/loops/evidence.py`
- [x] **P5-018** `guinevere-loops.service` creation — `systemd/guinevere-loops.service`
- [x] **P5-019** `guinevere-scheduler.service` creation — `systemd/guinevere-scheduler.service`
- [x] **P5-020** `/loop-start` command test — `src/discord/cmd_loop_start.py`, wired in bot.py
- [x] **P5-021** `/loop-stop` command test — `src/discord/cmd_loop_stop.py`, wired in bot.py
- [x] **P5-022** Agent loop E2E (full 7-phase cycle) — `tests/test_e2e_loop.py` 17/17 PASS
- [x] **P5-023** Cost tracking per loop (Redis DB5) — `src/loops/cost.py`

### P5 Final Audit + P5.5 Remediation (2026-06-02)

**12-dimension audit**: D01-D12 parallel auditors → CONDITIONAL PASS (17 CRITICAL, 11 HIGH findings).

**P5.5 Remediation (10 fixes)**:

| FIX | Finding | Status | Evidence |
|-----|---------|--------|---------|
| FIX 1 | C-05: Migration chain broken | ✅ PASS | `evidence/phase-5.5/STEP-FIX-01/verification.md` |
| FIX 2 | C-17: Zero indexes on loop_instances | ✅ PASS | `evidence/phase-5.5/STEP-FIX-02/verification.md` |
| FIX 3 | C-06: cost.py zero Redis error handling | ✅ PASS | `evidence/phase-5.5/STEP-FIX-03/verification.md` |
| FIX 4 | C-02: Guardian.kill_loop() zombie loops | ✅ PASS | `evidence/phase-5.5/STEP-FIX-04/verification.md` |
| FIX 5 | H-02: Guardian monitor() no exception handling | ✅ PASS | `evidence/phase-5.5/STEP-FIX-05/verification.md` |
| FIX 6 | C-16: Dev-key fallback in 3 files | ✅ PASS | `evidence/phase-5.5/STEP-FIX-06/verification.md` |
| FIX 7 | C-10/11: Systemd hardening (13 directives) | ✅ PASS | `evidence/phase-5.5/STEP-FIX-07/verification.md` |
| FIX 8 | C-07/08/09: Stub routes → real LoopManager | ✅ PASS | `evidence/phase-5.5/STEP-FIX-08/verification.md` |
| FIX 9 | H-04: logger.error → logger.exception | ✅ PASS | `evidence/phase-5.5/STEP-FIX-09/verification.md` |
| FIX 10 | C-12: Health check endpoint | ✅ PASS | `evidence/phase-5.5/STEP-FIX-10/verification.md` |

**Post-fix re-audits**: D02, D04, D05, D09, D10, D12 — 2 additional bugs found and fixed (cmd_loop_stop.py response shape, manager.py cancel_callback wiring). E2E 17/17 PASS.

**Re-audit verdicts**: D05 PASS, D09 PASS, D10 PASS. D02 NEEDS REVIEW (hardcoded URLs accepted), D04 NEEDS REVIEW (HardStopHandler deferred — no LLM calls yet), D12 NEEDS REVIEW (REDIS_PASSWORD=%E without LoadCredential, VPS config issue).

**Remaining non-blocking gaps**: HardStopHandler not in src/loops/ (deferred to LLM integration phase), in-memory loop state (no PostgreSQL persistence), scheduler creates separate LoopManager instance, cost.py float() ValueError risk.

**Evidence**: `audit-reports/P5/P5-FINAL-AUDIT/P5-FINAL-AUDIT.md`, `docs/setup-evidence/P5.5/batch-plan-remediation.md`, 6 re-audit reports at `audit-reports/P5/P5-FINAL-AUDIT/D*-re-audit.md`.

**P6 GO/NO-GO**: CONDITIONAL GO — P5 structurally sound, all blocking CRITICALs fixed. Remaining gaps are non-blocking and deferred to later phases.

### P5 Re-Audit (2026-06-09)

**Verdict: ✅ PASS** (upgraded dari CONDITIONAL PASS)

Re-audit menemukan 6 findings dari gaps yang belum terselesaikan di P5.5. Semua blocking findings (F-01, F-03, F-04, F-05, F-06) diselesaikan. F-02 di-cancel karena constraint infrastruktur (NoNewPrivileges).

| ID | Finding | Severity | Fix | Status |
|----|---------|----------|-----|--------|
| F-01 | Multiple LoopManager instances — 10 callers buat instance baru per-request | CRITICAL | 10 callers → HTTP API calls; 4 endpoint baru di `routes.py` | ✅ RESOLVED |
| F-02 | `guinevere-loops.service` / `guinevere-scheduler.service` not-enabled di systemd | LOW | Di-cancel — `NoNewPrivileges=true` butuh root SSH. Services running (start manual). | ⚠️ DEFERRED |
| F-03 | `test_e2e_loop.py` gagal via pytest (missing asyncio marker) | MEDIUM | `asyncio_mode = "auto"` di `pyproject.toml`; E2E 1/1 PASS via pytest | ✅ RESOLVED |
| F-04 | Loop state in-memory only — no DB persistence | HIGH | DB persistence via `LoopInstances` table di `manager.py` (graceful on start/complete/fail) | ✅ RESOLVED |
| F-05 | HardStopHandler tidak terintegrasi di `src/loops/` | HIGH | `HardStopHandler` di-wire ke guardian; `cancel_all_loops()` ditambah | ✅ RESOLVED |
| F-06 | `cost.py` float() rentan `ValueError` jika Redis return string korup | LOW | `except (RedisError, ValueError)` guard di `cost.py` | ✅ RESOLVED |

**Post-fix tests:** 21 passed, 0 failed.
**Audit report:** `audit-reports/P5/P5-REAUDIT-2026-06-09.md`

### ADR-035 Phase 5 Hermes Migration Enhancements (2026-06-06)

| Step | Scope | Status | Evidence |
|---|---|---|---|
| 5.1 | VPS `SOUL.md` completion (§A-§J, Y4/Y5/Y6, HARD STOP, prompt-injection defense) | ✅ Parent-verified v2 | `docs/setup-evidence/phase-5/verification-5-1-v2.md` |
| 5.2 | Drift baseline reset to finalized SOUL SHA-256 | ✅ Parent-verified v2 | `docs/setup-evidence/phase-5/verification-5-2-v2.md`, `docs/setup-evidence/phase-5/security-incident-5-2-redis-transcript.md` |
| 5.3 | Five priority Hermes skills (`hardstop`, `consent`, `yandere`, `mood`, `rituals`) + custom discovery/content reconciliation | ✅ Parent-verified v2 | `docs/setup-evidence/phase-5/verification-5-3-content-reconciliation.md` |
| 5.4 | PersonaPlugin/Redis DB5 bridge + local plugin/FSM verification | ✅ Parent-verified v2; VPS deploy/restart later passed in OG-6 | `docs/setup-evidence/phase-5/verification-5-4-v2.md`, `docs/setup-evidence/phase-5/verification-5-deploy-v2.md` |
| 5.5 | Native Hermes cron ritual registration with midnight `local` delivery | ✅ Parent-verified v2 | `docs/setup-evidence/phase-5/verification-5-5-v2.md` |
| 5.6 | Ritual verification for native Hermes cron jobs and midnight isolation | ✅ Parent-verified v2 | `docs/setup-evidence/phase-5/verification-5-6-v2.md` |
| 5.7 | Persona module migration; APScheduler retired from active ritual path | ✅ Parent-verified v2 | `docs/setup-evidence/phase-5/verification-5-7-v2.md` |
| 5.8 | Final 18-gate + five-auditor v2 synthesis + OG-6 deploy/smoke | ✅ 17 PASS / 1 PASS-RESCOPED / 0 FAIL; OG-6 PASS | `docs/setup-evidence/phase-5/evidence-phase-5.md`, `docs/setup-evidence/phase-5/verification-5-8-v2.md`, `docs/setup-evidence/phase-5/verification-5-deploy-v2.md` |

**Remaining Phase 5 closure gate**: ✅ COMPLETE — Phase 5 verification T1-T10 local deterministic suite PASS (`205 passed`), FIX-01/FIX-02/FIX-03 PASS, and three auditor gates PASS. Controlled PersonaPlugin VPS deploy + Hermes restart/smoke passed in `verification-5-deploy-v2.md`. G-17 is PASS-RESCOPED to the current two pre-cutover safety hooks; the old seven-hook target is deferred to later cutover.

### Phase 5 Verification — T1-T10 End-to-End Gate (2026-06-07)

| Gate | Scope | Status | Evidence |
|---|---|---|---|
| T1-T5 | Functional verification: loop, safety gates, auth, memory pipeline, surveillance pipeline | ✅ PASS | `docs/setup-evidence/phase5-verification/T1-verification.md` through `T5-verification.md`, `docs/setup-evidence/phase5-verification/auditor-functional-T1-T5.md` |
| T6-T10 | Technical verification: persona FSM, distress, consent, budget, monitoring | ✅ PASS | `docs/setup-evidence/phase5-verification/T6-verification.md` through `T10-verification.md`, `docs/setup-evidence/phase5-verification/auditor-technical-T6-T10.md` |
| AC-SAFE | HARD STOP latency, Y4/Y5/Y6, F-01..F-15 scanner, consent, privacy, Aizanta isolation | ✅ PASS | `docs/setup-evidence/phase5-verification/FIX-01-verification.md`, `FIX-02-verification.md`, `FIX-03-verification.md`, `docs/setup-evidence/phase5-verification/auditor-safety-AC-SAFE.md` |
| Summary | Full local deterministic verification suite | ✅ PASS | `docs/setup-evidence/phase5-verification/VERIFICATION-SUMMARY.md` (`205 passed`), `research-reports/phase5-verification/` |

**Phase 5 verification result**: PASS — local deterministic T1-T10 + safety suite passed (`205 passed`), HARD STOP latency benchmark passed below the 50ms hard limit, forbidden scanner coverage passed for F-01..F-15/Y6/intimate-data patterns, persona document stale Y1/Y3 wording was corrected to the canonical Y4 baseline/Y5 ceiling/Y6 prohibition, and all three auditor gates PASS.

**Phase 5 verification caveats**: This is a local deterministic verification PASS, not a live Discord/VPS E2E PASS. Research reports preserve runtime caveats: standalone Discord bot remains masked, Hermes gateway Discord adapter connectivity is unconfirmed with live messages, local PostgreSQL `5433`, Redis `6380`, and MCP `8090` listeners were unavailable, while local 9Router `20128` was available.

### ADR-035 Phase 6 Hermes Migration — LLM Routing & Budget Enforcement (2026-06-06)

| Gate | Scope | Status | Evidence |
|---|---|---|---|
| 6.1 | 9Router primary config | ✅ Parent-verified | `docs/setup-evidence/phase-6/STEP-6/verification.md` |
| 6.2 | Fallback chain via 9Router | ✅ Parent-verified | `docs/setup-evidence/phase-6/STEP-6/verification.md` |
| 6.3-6.5 | Budget hook fail-closed + deployment/config | ✅ Parent-verified | `docs/setup-evidence/phase-6/STEP-4/verification.md`, `docs/setup-evidence/phase-6/STEP-5/verification.md`, `docs/setup-evidence/phase-6/STEP-10/implementation-report.md` |
| 6.6-6.6A | SSE cleanup + CostTracker wiring | ✅ Parent-verified | `docs/setup-evidence/phase-6/STEP-2/verification.md`, `docs/setup-evidence/phase-6/STEP-3/verification.md` |
| 6.7 | Redis DB5 cost keys | ✅ Runtime-verified | `docs/setup-evidence/phase-6/STEP-9/verification.md` |
| 6.8 | Prometheus LLM metrics | ✅ Runtime-verified | `docs/setup-evidence/phase-6/STEP-7/verification.md`, `docs/setup-evidence/phase-6/STEP-8/verification.md` |
| 6.9 | Runtime restart + audit gates | ✅ PASS | `docs/setup-evidence/phase-6/STEP-8/verification.md`, `docs/setup-evidence/phase-6/STEP-12/routing/auditor-gate.md`, `docs/setup-evidence/phase-6/STEP-12/cost/auditor-gate.md`, `docs/setup-evidence/phase-6/STEP-12/adr/auditor-gate.md` |

**Phase 6 result**: PASS — DeepSeek primary via 9Router `localhost:20128`, two fallbacks configured through 9Router, budget hook active/fail-closed, CostTracker updates Redis DB5 after LLM responses, 100/100 VPS prompts passed with zero SSE artifacts/direct provider calls, metrics exposed on `localhost:9191`, and three auditor gates PASS.

**Phase 6 caveats / follow-ups**: `cx/gpt-5.5` remains known-degraded until Codex credentials are refreshed; forced hard-cap proof blocks fail-closed through `budget_check_failed` rather than clean `MONTHLY_BLOCKED`; improve monthly-block reporting in a follow-up. Phase 7 readiness: YES.

### Phase 6 System Audit — ADR-035 Compliance (2026-06-07)

8-domain parallel audit + 3 Oracle auditor gates. Evidence corrected per auditor findings.

| Domain | Verdict | Notes |
|---|---|---|
| 01 Safety Compliance | **PASS** | 10 safety plugin gates + 3 shell hooks (budget/consent/DNR), all fail-closed |
| 02 Architecture | **CONDITIONAL** | Config valid; runtime MCP/tool execution needs VPS verification |
| 03 Code Quality | **CONDITIONAL** | 11 `# type: ignore` across `src/` (0 in `src/hermes/`); pre-ADR-035 |
| 04 Performance | **PASS** | VPS metrics: Hermes <2s, 9Router <1s; 139/139 Phase 7 tests green |
| 05 Security | **PASS** | No plaintext secrets; SOPS active; `*.env` gitignore covers all .env files |
| 06 Aizanta Isolation | **PASS** | Zero Aizanta touch; ports 5433/6380 hardcoded; guards block 5432/6379 |
| 07 Documentation | **CONDITIONAL** | ADR-035 Implemented; P0-P8 complete; 71 stale StepPrompts |
| 08 Regression | **FAIL (pre-existing)** | `pytest-asyncio` missing from test deps; not ADR-035 regression |

**Overall: PASS WITH CONDITIONS** — No safety regressions, no consent violations, no Aizanta cross-contamination. Pre-existing `pytest-asyncio` gap recommended for follow-up.

**Evidence**: `docs/setup-evidence/phase6-audit/VERIFICATION-SUMMARY.md`, 8 per-domain evidence files, 3 auditor gate reports, 8 source reports at `research-reports/phase6-audit/`.

## P6: MCP Tools (21 steps)
*ADRs: ADR-020, ADR-033 | Cost: $1/mo avg | Deps: P5 complete*

- [x] **P6-001** `guinevere-mcp.service` setup — `src/mcp/manager.py` FastMCP factory, `auth.py` 4-level decorator, `systemd/guinevere-mcp.service`
- [x] **P6-002** `brave_search` setup + test — `src/mcp/tools/brave_search.py`, 15 tests, BRAVE_API_KEY via SOPS
- [x] **P6-003** `context7` setup + test — `src/mcp/tools/context7.py`, 27 tests, LRU cache, free 1K calls/mo
- [x] **P6-004** `exa` setup + test — `src/mcp/tools/exa_search.py`, 35 tests, $5/day cap via Redis DB5
- [x] **P6-005** `fetch` setup + test — `src/mcp/tools/fetch.py`, 21 tests, URL scheme validation, 1MB limit
- [x] **P6-006** `filesystem` + whitelist verification — `src/mcp/tools/filesystem.py`, 33+3skip tests, path whitelist+symlink guard
- [x] **P6-007** `github` MCP setup + test — `src/mcp/tools/github.py`, 13 tests, GITHUB_PAT via SOPS
- [x] **P6-008** `grep_app` setup + test — `src/mcp/tools/grep_app.py`, 24 tests, public API
- [x] **P6-009** `obscura-cdp` setup + test — `src/mcp/tools/obscura_cdp.py`, 17 tests, CDP port 9222 (ADR-033)
- [x] **P6-010** `sequential-thinking` setup + test — `src/mcp/tools/sequential_thinking.py`, 32 tests, branching+revision
- [x] **P6-011** `time` setup + test — `src/mcp/tools/time_tools.py`, 53 tests, zoneinfo stdlib, WIB default
- [x] **P6-012** `websearch` setup + test — `src/mcp/tools/websearch.py`, 11 tests, Brave→Exa hybrid fallback
- [x] **P6-013** `git` MCP setup + test — `src/mcp/tools/git_tool.py`, 56 tests, force-push-to-main FORBIDDEN
- [x] **P6-014** `postgres` MCP setup + test — `src/mcp/tools/postgres_tool.py`, 45 tests, 3-layer defense, port 5433
- [x] **P6-015** `redis` MCP setup + test — `src/mcp/tools/redis_tool.py`, 58 tests, FLUSHALL FORBIDDEN, port 6380
- [x] **P6-016** `shell` MCP + whitelist — `src/mcp/tools/shell_tool.py`, 60 tests, injection defense (;|&&$()`)
- [x] **P6-017** `docker` MCP setup + test — `src/mcp/tools/docker_tool.py`, 64 tests, guinevere-net isolation
- [x] **P6-018** 4-level auth matrix verification — `src/mcp/auth_matrix.py`, 93 tests, 16 tools × 4 levels complete
- [x] **P6-019** Tool selection decision matrix test — `src/mcp/tool_selector.py`, 27 tests, 8 overlap scenarios verified
- [x] **P6-020** Cost tracking per tool (Redis DB5) — `src/mcp/cost.py`, 45 tests, tool:cost:{name}:YYYY-MM-DD keys
- [x] **P6-021** Budget enforcement (hit $5 Exa cap → Brave fallback) — `src/mcp/budget.py`, 42 tests, $30/month absolute cap

**P6 Implementation Artifacts** (2026-06-03): 17 source files (`src/mcp/`), 17 test files (`tests/mcp/`), 2 systemd services, 22 planner/evidence files. 791 tests passed, 0 failed, 3 skipped (Windows symlinks). Batch plan: `docs/setup-evidence/P6/batch-plan-001-021.md`.

**P6 Remediation** (2026-06-03): 13-dimension audit found 4 CRITICAL issues. All 7 pre-P7 fixes applied: (1) Aizanta isolation hardened — postgres port/db/user hardcoded, docker network checks, shell/filesystem blocked paths, (2) auth @require_approval migrated to bare functions for all 16 tools, (3) git bypass vectors closed (force-with-lease, case-insensitive, refspec), (4) 6 stub tests replaced, (5) brave_search Redis TTL added, (6) 5 ruff errors fixed, (7) StepPrompts.md status updated. Audit: `audit-reports/P6/P6-FINAL-AUDIT.md`. Remediation audit: `audit-reports/P6/P6-REMEDIATION-AUDIT.md`. Deferred to P8: MCP client bridge, ToolCostTracker wiring.

### P6 Re-Audit (2026-06-09)

Re-audit menemukan 7 findings dari test suite + security + wiring. Semua ditangani dalam satu sesi.

| Finding | Deskripsi | Fix | Status |
|---|---|---|---|
| F-01 | Auth matrix flat READ_AUTO wildcard — per-op granularity hilang | Restore per-operation mapping di `auth_matrix.py` | ✅ FIXED — 94 tests pass |
| F-02 | Filesystem symlink escape tidak terblok | `validate_path()` wajibkan resolved target dalam whitelist | ✅ FIXED — 36 tests pass |
| F-03 | `test_registers_nine_tools` stale (actual: 12) | Update assertion ke 12 di `test_redis_tool.py` | ✅ FIXED |
| F-04 | `ToolCostTracker` & `BudgetEnforcer` tidak terwired | Instantiate + inject ke `manager.py` | ✅ FIXED |
| F-05 | `BRAVE_API_KEY` tidak diprovision | Placeholder di `.env.mcp` — key perlu diprovision manual | ⚠️ PARTIAL |
| F-06 | `db-passwords.yaml` dikira plaintext | Verified SOPS-encrypted — false positive | ✅ FALSE POSITIVE |
| F-07 | Double-registration warning di startup | Non-blocking — acknowledged | ✅ ACKNOWLEDGED |

**Tests: 807 passed, 0 failed.** Verdict: **PASS** ✅ (caveat: `BRAVE_API_KEY` perlu diprovision — `brave_search` akan fail di runtime sampai key diisi). Audit report: `audit-reports/P6/P6-REAUDIT-2026-06-09.md`.

## P7: Surveillance (22 steps) ✅
*ADRs: ADR-022, ADR-023, ConsentRevocationPolicy | Cost: $1/mo | Deps: P0 complete*
*Completed: 2026-06-03 | 472 tests pass | 14 source modules | Consent gate verified*

- [x] **P7-001** FastAPI surveillance receiver (`POST /surveillance/events`)
- [x] **P7-002** HMAC authentication (shared secret)
- [x] **P7-003** Replay protection (nonce + timestamp)
- [x] **P7-004** SSL/TLS surveillance endpoint
- [x] **P7-005** Redis DB2 buffer (5-min TTL)
- [x] **P7-006** Async consumer (background worker)
- [x] **P7-007** TimescaleDB ingestion (Redis → hypertables)
- [x] **P7-008** Data classification (Internal/Confidential/Restricted)
- [x] **P7-009** Clipboard secret scanner
- [x] **P7-010** Consent verification gate
- [x] **P7-011** Safe-mode surveillance blocking
- [x] **P7-012** Android Tasker setup guide
- [x] **P7-013** Tasker app usage profile (per ADR-023)
- [x] **P7-014** Tasker location profile (GPS, geofencing)
- [x] **P7-015** Tasker notification profile
- [x] **P7-016** Tasker clipboard profile
- [x] **P7-017** HMAC signing in Tasker
- [x] **P7-018** `guinevere-surveillance.service` creation
- [x] **P7-019** `/surveillance-status` test
- [x] **P7-020** `/surveillance-pause` test
- [x] **P7-021** Surveillance E2E (Tasker → API → Redis → PG → Discord)
- [x] **P7-022** Data retention verification (7d raw, 90d agg, 1y summaries)

### P7.5 Remediation (9 fixes) - 2026-06-03

14-dimension audit found 5 CRITICAL + 4 HIGH findings. All 9 fixed via 7 parallel agents, re-audited by 4 independent dimension auditors. D14 verdict: **P8 READY**.

| Fix | Severity | Description | Status |
|-----|----------|-------------|--------|
| C1 | CRITICAL | Router pushes events to Redis DB2 buffer after HMAC/auth | PASS |
| C2 | CRITICAL | consumer.main() async SQLAlchemy session factory (port 5433) | PASS |
| C3 | CRITICAL | DataClassification CRITICAL tier + 12 event types remapped to policy | PASS |
| C4 | CRITICAL | invalidate_cache() wired in pause command (4 scopes, asyncio.gather) | PASS |
| C5 | CRITICAL | SurveillanceSafeModeGuard instantiated in bot.py with HardStopHandler | PASS |
| H1 | HIGH | _BLOCKED_ACTIONS expanded 6 to 8 (humiliation + public_disclosure) | PASS |
| H2 | HIGH | P7-012 signing string newlines to colons (Tasker HMAC compat) | PASS |
| H3 | HIGH | Unknown SAFE-mode actions fail-closed (BLOCKED, not ALLOWED) | PASS |
| H4 | HIGH | systemd StartLimitBurst=5 + StartLimitIntervalSec=300 | PASS |

**Tests**: 495 passed, 10 skipped (E2E gated), 0 failed
**LSP**: 0 new errors (all pre-existing)
**Re-audit reports**: `audit-reports/P7.5/D04-safety-recheck.md`, `D05-consent-recheck.md`, `D08-architecture-recheck.md`, `D14-p8-readiness-recheck.md`

## P8: Observability (23 steps) ✅
*ADRs: ADR-017, ADR-032 | Cost: $4/mo | Deps: P0-P7 complete*
*Completed: 2026-06-03 | 19 PASS, 2 DEFERRED-VPS, 1 PASS (DOC), Faiz approved*

- [x] **P8-001** Prometheus Docker setup (per ADR-017) — compose.monitoring.yml, 8 services
- [x] **P8-002** node_exporter setup — textfile/backup_status.prom
- [x] **P8-003** postgres_exporter setup — postgres_exporter_role.sql (pg_monitor)
- [x] **P8-004** redis_exporter setup — setup_redis_exporter_acl.py (minimal ACL)
- [x] **P8-005** Scrape configs (15s interval) — 7 jobs (prometheus, node, pg, redis, fastapi, loki, alertmanager)
- [x] **P8-006** Grafana Docker setup (localhost:3000) — verified in compose, Caddy :3443→:3000
- [x] **P8-007** Datasource provisioning (Prometheus + Loki + PG) — datasources.yml + dashboards.yml
- [x] **P8-008** Dashboard provisioning (infra, DB, loop, LLM, safety, finops) — 6 JSON dashboards
- [x] **P8-009** Loki Docker setup (log aggregation) — schema v13+TSDB, retention 720h
- [x] **P8-010** Promtail setup (journalctl → Loki) — version 3.5.8 CRITICAL, 3 jobs
- [x] **P8-011** Log pipeline test — ⏸️ DEFERRED-VPS, test script: `scripts/test_log_pipeline.sh`
- [x] **P8-012** Sentry SDK integration — sentry_integration.py, send_default_pii=False
- [x] **P8-013** Sentry scrubber (remove PII) — 6 REDACT + 6 DROP patterns
- [x] **P8-014** Alert rules — guinevere-alerts.yml, 9 rules (SEV0-SEV3)
- [x] **P8-015** SEV0-SEV4 routing matrix — alertmanager.yml, Discord+Gotify
- [x] **P8-016** Alert test (all SEV levels) — ⏸️ DEFERRED-VPS, test script: `scripts/test_alert_routing.sh`
- [x] **P8-017** `/cost` command — cmd_cost.py (662 lines, 5-part pattern)
- [x] **P8-018** `/budget` command — cmd_budget.py (643 lines, view/set actions)
- [x] **P8-019** Monthly cost report automation — monthly_report.py (538 lines, APScheduler)
- [x] **P8-020** Backup monitoring (per ADR-032) — backup-metric-collector.sh + backup alerts
- [x] **P8-021** `guinevere-monitoring.service` creation — systemd unit, MemoryMax=1G
- [x] **P8-022** MVP acceptance criteria full run — 19 PASS, 0 FAIL, 49 NOT-RUN, 9 BLOCKED
- [x] **P8-023** Faiz sign-off checklist — ✅ APPROVED 2026-06-03

## P9: Financial Tracking — Stabilization (13 steps)
*ADRs: ADR-009 | Cost: $1/mo | Deps: P8 (MVP) | Category: Stabilization | 1-2h per step*

- [ ] **P9-001** Financial data model (transactions, budgets, categories)
- [ ] **P9-002** Transaction table migration (TimescaleDB hypertable)
- [ ] **P9-003** Budget table migration (per-category limits)
- [ ] **P9-004** Tasker notification capture (bank SMS parsing)
- [ ] **P9-005** SMS parsing pipeline (regex → structured data)
- [ ] **P9-006** Transaction classification engine (rules-based)
- [ ] **P9-007** Budget tracking with overspend alerts
- [ ] **P9-008** `/finance summary` command
- [ ] **P9-009** `/finance add` command
- [ ] **P9-010** `/finance report` command
- [ ] **P9-011** Monthly financial report (PDF generation)
- [ ] **P9-012** FinOps dashboard (Grafana, per FinOps Model v1.1)
- [ ] **P9-013** Financial E2E Test — full pipeline: Tasker SMS → classification → budget → report → dashboard

## P10: Production Hardening — Stabilization (21 steps)
*ADRs: ADR-015, ADR-016, ADR-032 | Cost: $1/mo | Deps: P8 (MVP) | Category: Stabilization | 1-2h per step*

- [ ] **P10-001** Security audit — penetration testing
- [ ] **P10-002** Vulnerability scan (CVE check all packages)
- [ ] **P10-003** PostgreSQL tuning (VACUUM, index optimization)
- [ ] **P10-004** Redis tuning (maxmemory, eviction strategy)
- [ ] **P10-005** systemd resource limits refinement
- [ ] **P10-006** Backup automation verification (per ADR-032)
- [ ] **P10-007** Restore test (from S3 backup)
- [ ] **P10-008** Restore test (from R2 backup)
- [ ] **P10-009** DR drill — simulate VPS failure
- [ ] **P10-010** DR drill — full restore from backup
- [ ] **P10-011** GitHub Actions CI (lint, test, scan, per ADR-016)
- [ ] **P10-012** Self-deploy pipeline (push → Actions → systemd)
- [ ] **P10-013** Rollback automation (git revert → redeploy)
- [ ] **P10-014** SOPS age key rotation (per ADR-015)
- [ ] **P10-015** API key rotation procedure
- [ ] **P10-016** Database password rotation
- [ ] **P10-017** Runbook documentation
- [ ] **P10-018** Load testing (peak usage simulation)
- [ ] **P10-019** Load Testing (k6) — validate p95 latency under realistic load
- [ ] **P10-020** Hardening Verification — comprehensive security and operational checklist
- [ ] **P10-021** MVP Acceptance Gate (AC-PHASE-006)

## P11: WhatsApp Integration — Expansion (23 steps)
*Cost: $0/mo | Deps: P5+P8 | Category: Expansion*
*Source: Neonize (free Go-based WhatsApp library), WhatsApp Web multi-device protocol*

- [ ] **P11-001** Neonize Setup + Project Scaffolding
- [ ] **P11-002** Session Authentication + QR/SOPS Encryption
- [ ] **P11-003** Neonize Connection Handler + Event Routing
- [ ] **P11-004** ChannelAdapter Interface + UnifiedMessage
- [ ] **P11-005** WhatsAppAdapter Implementation
- [ ] **P11-006** ConversationalAgent Core
- [ ] **P11-007** Context Manager (10-msg window, shared memory)
- [ ] **P11-008** Message Routing Pipeline
- [ ] **P11-009** Natural Language Intent Classifier
- [ ] **P11-010** Command Handler
- [ ] **P11-011** Typing Indicator + Response Streaming
- [ ] **P11-012** Response Formatter (auto-split, markdown→WhatsApp)
- [ ] **P11-013** Media Acknowledgment Handler
- [ ] **P11-014** Rate Limiter (8/min, 30/hour, 200/day)
- [ ] **P11-015** Cross-Channel HARD STOP
- [ ] **P11-016** Safe Word + Consent Management
- [ ] **P11-017** Number Whitelist (Faiz-only)
- [ ] **P11-018** Discord Bridge Mirror
- [ ] **P11-019** Discord Notifications + Status
- [ ] **P11-020** Reconnection Handler (3 retry, exponential backoff)
- [ ] **P11-021** Health Check + Grafana Monitoring
- [ ] **P11-022** Systemd Unit + Operational Runbook
- [ ] **P11-023** E2E Integration Test (P11 GATE)

## P12: Gmail/Email Integration — Expansion (29 steps)
*Cost: $0/mo | Deps: P5+P8 | Category: Expansion*
*Source: Gmail API + OAuth2 + Resend transactional email*

- [ ] **P12-001** GCP Project + Gmail API Enable
- [ ] **P12-002** OAuth2 Credential + SOPS
- [ ] **P12-003** Resend Transactional Email
- [ ] **P12-004** Gmail API Client Wrapper
- [ ] **P12-005** Full/Hybrid Sync Engine
- [ ] **P12-006** Cloud Pub/Sub Push Pipeline
- [ ] **P12-007** GmailAdapter (ChannelAdapter)
- [ ] **P12-008** Conversation Context Manager
- [ ] **P12-009** Email Classifier Cascade
- [ ] **P12-010** Priority Scorer
- [ ] **P12-011** Content Sanitizer + Injection Defense
- [ ] **P12-012** Secret Scanner + PII Redactor
- [ ] **P12-013** Memory Store Integration
- [ ] **P12-014** Financial Email → P9 Bridge
- [ ] **P12-015** Draft Generator (LLM)
- [ ] **P12-016** Draft Approval UX (Discord)
- [ ] **P12-017** Draft Send via Gmail API
- [ ] **P12-018** Real-Time Notifications
- [ ] **P12-019** Morning Briefing Generator
- [ ] **P12-020** !email-digest Command
- [ ] **P12-021** Consent + Surveillance Policy
- [ ] **P12-022** Cross-Channel HARD STOP
- [ ] **P12-023** Surveillance Data Classification
- [ ] **P12-024** Watch Health + Auto-Refresh
- [ ] **P12-025** Grafana Dashboard + Metrics
- [ ] **P12-026** Systemd Service + Runbook
- [ ] **P12-027** Integration Test (10 Scenarios)
- [ ] **P12-028** Agent Loop Trigger Detector
- [ ] **P12-029** TaskContract Email Context

## P13: X Auto Poster — Expansion (28 steps)
*ADRs: ADR-033, ADR-032, ADR-016, ADR-027 | Cost: TBD | Deps: P5 + P6 + P7 + P8*

**Goal:** Automated X/Twitter posting using manual Windows image drop-folder input, S3 queue lifecycle, Gemini captioning, dedicated Obscura CDP browser automation, Discord controls, PostgreSQL logging, and operational safeguards.

**Key Components:**
- **Windows Watchdog:** Local folder watcher uploads JPG/PNG/WEBP + sidecar JSON to `guinevere-assets/x-poster/pending/`.
- **S3 Queue:** Prefix state machine `/pending/`, `/processing/`, `/posted/`, `/failed/`, `/held/`, `/archived/` with TTL policies.
- **Gemini Captioning:** Flash primary, Pro fallback, sidecar caption override, alt text generation, content moderation block path.
- **Obscura CDP:** Dedicated X browser automation on port 9223 with isolated `--storage-dir` and SOPS-encrypted cookies.
- **Rate Controls:** 3h minimum interval, max 5/day, night hold 23:00-06:00 WIB, immediate override, dry-run mode.
- **Discord Controls:** `/x-status`, `/x-list`, `/x-cancel`, `/x-hold`, `/x-resume`, `/x-edit`, `/x-delete`, `/x-retry`, `/x-dryrun`.
- **PostgreSQL State:** Per-post log, retry state, session age, 90-day retention, Prometheus/Grafana reporting.

- [ ] **P13-001** S3 Queue Setup
- [ ] **P13-002** Windows Watchdog Script
- [ ] **P13-003** Obscura CDP Dedicated Instance
- [ ] **P13-004** Systemd Service
- [ ] **P13-005** Queue Polling Loop
- [ ] **P13-006** Sidecar Parser
- [ ] **P13-007** Rate Limiter
- [ ] **P13-008** Cookie Injector
- [ ] **P13-009** Session Health Check
- [ ] **P13-010** Session Recovery
- [ ] **P13-011** Caption Generator
- [ ] **P13-012** Content Moderation
- [ ] **P13-013** Tone Controller
- [ ] **P13-014** Compose Adapter (CDP)
- [ ] **P13-015** Media Upload (CDP)
- [ ] **P13-016** Post Action
- [ ] **P13-017** Dry-Run Mode
- [ ] **P13-018** Retry Engine
- [ ] **P13-019** Circuit Breaker
- [ ] **P13-020** Processing Timeout Handler
- [ ] **P13-021** Post Notification
- [ ] **P13-022** Status Commands
- [ ] **P13-023** Edit Command
- [ ] **P13-024** Delete Command
- [ ] **P13-025** Retry Commands
- [ ] **P13-026** Grafana Dashboard
- [ ] **P13-027** Daily Summary
- [ ] **P13-028** Integration Test + P13 GATE

## Phase 14: Wearable/Xiaomi Watch (Expansion) — LEGACY GADGETBRIDGE PLAN

> **⚠️ SUPERSEDED 2026-06-18** by the 20-step Mi Fitness Cloud API -> VPS
> direct implementation documented in the next section and in
> `adr/ADR-037-wearable-health-pipeline.md`. The 27-step Gadgetbridge/WebDAV
> plan below is preserved for audit trail only — it is NOT the active plan.
> See `docs/setup-evidence/p14-expansion/evidence-p14-expansion.md` for the
> canonical evidence (20/20 steps PASS, 19/19 AC-WEAR PASS).

**Goal:** Xiaomi wearable health data ingestion via Gadgetbridge WebDAV sync → VPS pipeline → TimescaleDB → anomaly detection → GHI scoring → persona-adjusted behavior → Discord health commands.
**Steps:** 27 (legacy — replaced by 20-step Mi Fitness Cloud implementation)
**Dependencies:** P7 (Surveillance) + P8 (Observability/MVP Gate)
**Cost:** $0/month — uses existing VPS, TimescaleDB, Grafana, Discord; no paid API
**Status:** ⛔ SUPERSEDED (see P14 (Implemented) below)

### Step List

| Step | Title | Status |
|------|-------|--------|
| P14-001 | Device Procurement + Gadgetbridge Setup | ⛔ SUPERSEDED |
| P14-002 | WebDAV Server Endpoint | ⛔ SUPERSEDED |
| P14-003 | Database Schema Creation (7 hypertables) | ⛔ SUPERSEDED (now 5 hypertables in Mi Fitness impl) |
| P14-004 | HMAC Key Provisioning | ⛔ SUPERSEDED (single SOPS token in impl) |
| P14-005 | Gadgetbridge SQLite Parser | ⛔ SUPERSEDED |
| P14-006 | Health Ingestion Endpoint | ⛔ SUPERSEDED |
| P14-007 | Consumer Scope Mapping | ⛔ SUPERSEDED |
| P14-008 | Mi Fitness Cloud SDK Fallback | ⛔ SUPERSEDED (now primary path) |
| P14-009 | Personal Baseline Computation | ✅ P14-007 (re-mapped) |
| P14-010 | Anomaly Detection Engine | ✅ P14-008 (re-mapped) |
| P14-011 | GHI Composite Score Engine | ✅ P14-009 (re-mapped) |
| P14-012 | Daily Summary Pre-computation | ✅ P14-010 (re-mapped) |
| P14-013 | Persona State Machine (Health-Aware) | ✅ P14-010 (mood_integration.py) |
| P14-014 | Health Memory Injection | ⛔ SUPERSEDED (out of scope) |
| P14-015 | Distress Escalation Logic | ⛔ SUPERSEDED (out of scope) |
| P14-016 | /health-status + /ghi-score Commands | ✅ P14-013 (consolidated to single ephemeral command) |
| P14-017 | /sleep-report + /activity-today Commands | ⛔ SUPERSEDED (consolidated) |
| P14-018 | Morning Brief Health Section | ⛔ SUPERSEDED (out of scope) |
| P14-019 | Proactive Health Alerts + Night Owl | ✅ P14-011 (alert_router.py) |
| P14-020 | WAC-001..007 Activation Checklist | ⛔ SUPERSEDED (now AC-WEAR-01..19) |
| P14-021 | Data Export + Deletion | ⛔ SUPERSEDED (out of scope) |
| P14-022 | Prometheus Metrics | ✅ P14-015 (metrics.py) |
| P14-023 | Grafana Health Dashboard | ✅ P14-016 (dashboard JSON) |
| P14-024 | Stale Data + Battery Alerts | ⛔ SUPERSEDED (out of scope) |
| P14-025 | Systemd Service | ✅ P14-014 (4 systemd units) |
| P14-026 | Mock Health Data Generator | ⛔ SUPERSEDED (covered by integration test mock) |
| P14-027 | Integration Test + P14 GATE | ✅ P14-019 (test_wearable_integration.py) |

### Phase Complete Criteria
- [x] ~~All 7 health hypertables created and verified via TimescaleDB~~ — Replaced by 5 hypertables in Mi Fitness impl
- [x] ~~Gadgetbridge WebDAV auto-sync operational~~ — Replaced by direct Mi Fitness Cloud API sync
- [x] ~~Mi Fitness Cloud SDK fallback tested~~ — Now the primary path
- [x] Anomaly detection producing correct alerts — ✅ P14-008
- [x] GHI composite scoring validated — ✅ P14-009
- [x] Persona state machine adjusts Y-level (never confrontation) — ✅ P14-010 (capped modifier)
- [x] 4 Discord commands operational — ✅ P14-013 (consolidated to 1 ephemeral command)
- [x] Morning brief health section rendering — ⛔ SUPERSEDED (out of scope)
- [x] CRITICAL classification enforced, 365d retention — ✅ P14-001
- [x] Data export/deletion commands functional — ⛔ SUPERSEDED (out of scope)
- [x] guinevere-health.service running — ✅ P14-014 (now 4 systemd units)
- [x] Grafana health dashboard provisioned — ✅ P14-016
- [x] Integration test passes all 20 AC-WEAR criteria — ✅ P14-019 (19/19 AC-WEAR pass)

---

## Phase 14 (Implemented): Wearable Health Pipeline — Mi Fitness Cloud API

**Goal:** Xiaomi wearable health data ingestion via direct VPS -> Mi Fitness Cloud API server-to-server path; 5 health.* TimescaleDB hypertables; GHI composite scoring; persona-aware mood modifier (capped, never escalates); consent-gated ephemeral Discord surface.

**Steps:** 20 (P14-001 through P14-020) — all 20 VERIFIED ✅
**Dependencies:** P7 (Surveillance) + P8 (Observability/MVP Gate)
**Cost:** $0/month — Mi Fitness Cloud API is free, no additional LLM calls per sync
**Status:** ✅ COMPLETE (2026-06-18)
**ADR:** ADR-037-wearable-health-pipeline.md (Accepted; partially supersedes ADR-021 for Mi Fitness path)
**Evidence:** `docs/setup-evidence/p14-expansion/evidence-p14-expansion.md`

### Step List (20/20 VERIFIED)

| Step | Title | Status | Key Files |
|------|-------|--------|-----------|
| P14-001 | DB schema (5 hypertables + 2 ref tables) | ✅ VERIFIED | `migrations/p14_add_health_schema.sql` |
| P14-002 | `.env.wearable` + `config.py` SOPS-aware loader | ✅ VERIFIED | `.env.wearable.example`, `src/wearable/config.py` |
| P14-003 | Package skeleton + typed errors + Pydantic models | ✅ VERIFIED | `src/wearable/{__init__,errors,models}.py` |
| P14-004 | Async Mi Fitness Cloud client + DTO normaliser | ✅ VERIFIED | `src/wearable/{mi_fitness_client,normalizer}.py` |
| P14-005 | Redis DB4 staging + 15-min sync orchestrator | ✅ VERIFIED | `src/wearable/{redis_buffer,sync}.py` |
| P14-006 | TimescaleDB `COPY` batch writer | ✅ VERIFIED | `src/wearable/writer.py` |
| P14-007 | 28-day rolling baseline per metric | ✅ VERIFIED | `src/wearable/baseline.py` |
| P14-008 | +/-20% anomaly detection with severity tiers | ✅ VERIFIED | `src/wearable/anomaly.py` |
| P14-009 | GHI composite scorer (Sleep 40 / Cardio 20 / Activity 20 / Recovery 20) | ✅ VERIFIED | `src/wearable/ghi.py` |
| P14-010 | GHI -> persona mood modifier (capped, never escalates) | ✅ VERIFIED | `src/wearable/mood_integration.py` |
| P14-011 | Consent-gated, persona-tone-aware alert router | ✅ VERIFIED | `src/wearable/alert_router.py` |
| P14-012 | Per-scope `wearable-health.*` consent enforcement | ✅ VERIFIED | `src/wearable/health_consent.py` |
| P14-013 | Single ephemeral Discord command surface | ✅ VERIFIED | `src/discord/cmd_health_report.py` |
| P14-014 | 2 services + 2 timers + idempotent install script | ✅ VERIFIED | `systemd/guinevere-wearable-{sync,analysis}.{service,timer}`, `scripts/install_wearable_services.sh` |
| P14-015 | Prometheus metrics set (`guinevere_wearable_*`) | ✅ VERIFIED | `src/wearable/metrics.py` |
| P14-016 | Grafana dashboard JSON | ✅ VERIFIED | `grafana/dashboards/guinevere-wearable-health.json` |
| P14-017 | Field-level Fernet encryption (SOPS key) | ✅ VERIFIED | `src/wearable/encryption.py` |
| P14-018 | Unit tests (100+ assertions across 9 modules) | ✅ VERIFIED | `tests/test_wearable.py` |
| P14-019 | End-to-end integration test (mock Mi Fitness -> Redis -> TS -> Discord) | ✅ VERIFIED | `tests/test_wearable_integration.py` |
| P14-020 | Evidence + ADR-037 + PROGRESS/CHECKLIST sync | ✅ VERIFIED | This file + `adr/ADR-037-wearable-health-pipeline.md` + `docs/setup-evidence/p14-expansion/evidence-p14-expansion.md` |

### AC-WEAR Matrix (19/19 PASS)

AC-WEAR-01 (5 hypertables + 2 ref tables + 365d retention) · AC-WEAR-02 (15-min Mi Fitness Cloud API pull) · AC-WEAR-03 (Redis DB4 5-min TTL + idempotent dedup) · AC-WEAR-04 (28-day rolling baseline) · AC-WEAR-05 (+/-20% anomaly + severity) · AC-WEAR-06 (GHI 40/20/20/20) · AC-WEAR-07 (capped mood modifier, never escalates) · AC-WEAR-08 (no confrontation/correction/punishment from health data) · AC-WEAR-09 (CRITICAL classification + 365d retention) · AC-WEAR-10 (per-scope consent + revocation) · AC-WEAR-11 (consent-gated ephemeral alerts) · AC-WEAR-12 (Discord ephemeral surface) · AC-WEAR-13 (systemd timers) · AC-WEAR-14 (Prometheus metrics) · AC-WEAR-15 (Grafana dashboard) · AC-WEAR-16 (field-level Fernet) · AC-WEAR-17 (100+ unit assertions) · AC-WEAR-18 (E2E integration test) · AC-WEAR-19 (graceful degradation when no token).

### Implementation Artifacts (2026-06-18)

- 1 DB migration (`migrations/p14_add_health_schema.sql`)
- 17 source files in `src/wearable/` (~2900 LOC)
- 1 Discord command file (`src/discord/cmd_health_report.py`)
- 4 systemd units (`guinevere-wearable-{sync,analysis}.{service,timer}`)
- 1 install script (`scripts/install_wearable_services.sh`)
- 2 env files (`.env.wearable.example` + `.env.wearable` gitignored)
- 1 Grafana dashboard JSON
- 2 test files (`tests/test_wearable.py` + `tests/test_wearable_integration.py`)
- 1 ADR (`adr/ADR-037-wearable-health-pipeline.md`)

### Caveats

- Local deterministic verification PASS; live VPS runtime verification with a
  real Mi Fitness Cloud token and a real Xiaomi Smart Band 9 Pro is a
  follow-up gate tracked outside this document.
- ADR-021 graceful-degradation invariant preserved: missing token = sync
  exits 0 with logged skip; GHI/mood return None.
- Mood modifier is structurally a *modifier*, not a *trigger* — caps at
  min(Y4 baseline, current Y - 1); never escalates; never produces
  confrontation/correction/punishment text.

## Phase 14 Gadgetbridge Pivot (Implemented)

**Goal:** Add a second accepted ingestion path for Phase 14 wearable data by parsing the Gadgetbridge Android app's SQLite export on the VPS. Config-driven dispatch (`WEARABLE_DATA_SOURCE`) lets the operator switch between Mi Fitness Cloud API (ADR-037) and Gadgetbridge SQLite parser (ADR-039) without code changes or schema migrations. Both paths land in the same `health.*` schema and share the downstream pipeline.

**Steps:** 11 (P14-GB-01 through P14-GB-11) — all 11 VERIFIED ✅
**Dependencies:** P7 (Surveillance) + P8 (Observability/MVP Gate) — already complete
**Cost:** $0/month — Gadgetbridge Android app is free, no vendor token, no additional LLM calls per sync
**Status:** ✅ COMPLETE (2026-06-18)
**ADR:** ADR-039-gadgetbridge-sqlite-parser.md (Accepted; sibling to ADR-037)
**Evidence:** `docs/setup-evidence/p14-expansion/evidence-p14-gadgetbridge-pivot.md`

### Step List (11/11 VERIFIED)

| Step | Title | Status | Key Files |
|------|-------|--------|-----------|
| P14-GB-01 | `gadgetbridge_client.py` — SQLite parser (725 LOC, 6 table parsers) | ✅ VERIFIED | `src/wearable/gadgetbridge_client.py` |
| P14-GB-02 | Extend `normalizer.py` — Gadgetbridge extractors, source tagging | ✅ VERIFIED | `src/wearable/normalizer.py` (+55 LOC) |
| P14-GB-03 | Extend `config.py` — 3 new fields + validation | ✅ VERIFIED | `src/wearable/config.py` (+3 fields) |
| P14-GB-04 | Extend `errors.py` — 4 new exceptions | ✅ VERIFIED | `src/wearable/errors.py` (+4 exceptions) |
| P14-GB-05 | Modify `sync.py` — Config-driven dispatch | ✅ VERIFIED | `src/wearable/sync.py` (rewrite, 154 LOC) |
| P14-GB-06 | Modify `metrics.py` — Already source-agnostic | ✅ VERIFIED | No changes needed |
| P14-GB-07 | Hermes Discord wiring — 3 commands registered | ✅ VERIFIED | `src/discord/_command_registry.py` + `_entrypoint.py` |
| P14-GB-08 | Unit tests — 71/71 pass | ✅ VERIFIED | `tests/test_gadgetbridge_{client,normalizer,sync}.py` |
| P14-GB-09 | Integration tests — 8/8 pass | ✅ VERIFIED | `tests/test_gadgetbridge_integration.py` |
| P14-GB-10 | ADR-039 + evidence + docs update | ✅ VERIFIED | `adr/ADR-039-gadgetbridge-sqlite-parser.md` + `docs/setup-evidence/p14-expansion/evidence-p14-gadgetbridge-pivot.md` + this file |
| P14-GB-11 | VPS deploy — SCP + systemd + smoke test | ✅ VERIFIED | VPS deployment log (operator-verified) |

### Architecture

Setting `WEARABLE_DATA_SOURCE=gadgetbridge` in `.env.wearable` switches the entire pipeline from Mi Fitness Cloud -> Gadgetbridge SQLite. Consent gate, Redis buffer, TimescaleDB writer, baseline, anomaly, GHI, mood modifier, and alert router all remain source-agnostic and are reused without modification.

The Gadgetbridge parser reads the Android app's SQLite export (file named `Gadgetbridge`, no extension), queries `sqlite_master` for table discovery (handles schema variations across Gadgetbridge versions), auto-detects timestamp scales (samples > 10^12 treated as milliseconds, otherwise seconds), and decodes sleep stages from the activity table's `RAW_KIND` codes (112 light start, 120 light, 121 deep, 122 REM, 249 awake). Every sample is tagged with `MetricSource.GADGETBRIDGE` so downstream queries can distinguish source.

### Key Files

- `src/wearable/gadgetbridge_client.py` — SQLite parser (6 table parsers, timestamp auto-detect, sleep decoding, source tagging)
- `src/wearable/sync.py` — Config-driven dispatch (gadgetbridge vs mi_fitness); same downstream contract
- `src/wearable/normalizer.py` — Gadgetbridge extractors; produces `MetricSource.GADGETBRIDGE` tagged samples
- `src/discord/cmd_health_report.py` — 3 Hermes commands (/health-report, /health-trend, /health-baseline)

### Tests

347 total (265 pre-existing + 81 new + 1 pre-existing failure unrelated to GB).

- 71 unit tests: `test_gadgetbridge_client.py`, `test_gadgetbridge_normalizer.py`, `test_gadgetbridge_sync.py`
- 8 integration scenarios: `test_gadgetbridge_integration.py`
- 10 Discord command tests: `tests/discord/test_cmd_health_report.py`

### Caveats

- Mi Fitness Cloud path retained in `src/wearable/mi_fitness_client.py`; env var switch re-enables it with zero downtime.
- Manual file transfer required (Android -> VPS via SCP/SFTP/WebDAV); optional Tasker automation is out of scope.
- Gadgetbridge schema is reverse-engineered; table introspection via `sqlite_master` reduces version-drift risk.
- HRV and body battery are not available in Gadgetbridge's exported tables; GHI's 20% recovery component degrades to a partial signal on this path.
- Local deterministic verification PASS; live VPS runtime verification with real Gadgetbridge SQLite export and real Xiaomi Watch 2 Pro is a follow-up gate tracked outside this document.
- ADR-021 graceful-degradation invariant preserved: missing SQLite file = sync exits 0 with logged skip; GHI/mood return None.
- Mood modifier remains structurally a *modifier*, not a *trigger* — same Y4/Y5/Y6 boundary as ADR-037; HARD STOP checks preserved.

---

## Phase 14 Health Connect Pivot (Implemented)

**Goal:** Add Health Connect as the canonical Phase 14 wearable data source. The Xiaomi Watch 2 Pro (M2233W1) runs HyperOS and is unsupported by Gadgetbridge, while Mi Fitness Cloud API only queries relatives. Mi Fitness on the phone does write to Health Connect, so we read five record types (heart rate, steps, SpO2, sleep, active calories) through the official Android API, export to JSON, parse on the VPS, and feed the existing source-agnostic pipeline.

**Steps:** Kotlin app (6 files, 399 LOC MainActivity) + Python parser (435 LOC) + normalizer extension (+100 LOC) + sync dispatch branch (+92 LOC) + config (2 fields) + models (1 enum) + errors (4 exceptions) + 55 unit tests + 8-10 integration tests.

**Dependencies:** P14-GB (downstream pipeline already source-agnostic).
**Cost:** $0/month. Health Connect is free, no vendor API calls.
**Status:** ✅ COMPLETE (2026-06-19)
**ADR:** `adr/ADR-040-health-connect-pivot.md` (Accepted; supersedes ADR-039 + ADR-037 as canonical path)
**Evidence:** `docs/setup-evidence/p14-expansion/evidence-p14-expansion.md` Section 12

### Step List

| Step | Title | Status | Key Files |
|------|-------|--------|-----------|
| P14-HC-01 | Kotlin app `MainActivity.kt` (399 LOC) reads 5 Health Connect record types | ✅ VERIFIED | `android/HealthConnectExport/app/src/main/java/com/guinevere/hcexport/MainActivity.kt` |
| P14-HC-02 | Kotlin DTOs + serializer + permission helper + manifest + build.gradle | ✅ VERIFIED | `android/HealthConnectExport/app/src/main/...` (5 supporting files) |
| P14-HC-03 | VPS parser `health_connect_client.py` (435 LOC) | ✅ VERIFIED | `src/wearable/health_connect_client.py` |
| P14-HC-04 | Normalizer extension (`normalize_health_connect_result()`, source tagging) | ✅ VERIFIED | `src/wearable/normalizer.py` (+100 LOC) |
| P14-HC-05 | Sync dispatch branch (`_sync_health_connect()`) | ✅ VERIFIED | `src/wearable/sync.py` (+92 LOC) |
| P14-HC-06 | Config: 2 new fields (`health_connect_json_path`, `health_connect_device_name`) | ✅ VERIFIED | `src/wearable/config.py` |
| P14-HC-07 | Models: `MetricSource.HEALTH_CONNECT` enum value | ✅ VERIFIED | `src/wearable/models.py` |
| P14-HC-08 | Errors: 4 typed exceptions (`HealthConnectJsonMissing`, `HealthConnectJsonMalformed`, `HealthConnectUnknownRecordType`, `HealthConnectEmptyResult`) | ✅ VERIFIED | `src/wearable/errors.py` |
| P14-HC-09 | Unit tests (55/55 pass) | ✅ VERIFIED | `tests/test_health_connect_client.py` |
| P14-HC-10 | Integration tests (8-10 scenarios pass) | ✅ VERIFIED | `tests/test_health_connect_integration.py` |
| P14-HC-11 | ADR-040 Accepted; supersedes ADR-039 + ADR-037 as canonical | ✅ VERIFIED | `adr/ADR-040-health-connect-pivot.md` |
| P14-HC-12 | Evidence + PROGRESS/CHECKLIST sync | ✅ VERIFIED | `docs/setup-evidence/p14-expansion/evidence-p14-expansion.md` Section 12 |

### Architecture

The operator presses a button in the Kotlin app. The app reads five Health Connect record types and writes them to `/sdcard/Download/health-connect-export/export.json`. The operator pulls the file with `adb pull`, then SCPs it to the VPS at `/var/lib/guinevere/health-connect-export/export.json`. `health_connect_client.py` parses the JSON, calls into the existing normalizer with `MetricSource.HEALTH_CONNECT`, and feeds the existing downstream pipeline (Redis DB2 buffer, TimescaleDB writer, baseline, anomaly, GHI, mood modifier, alert router, Discord surface). Setting `WEARABLE_DATA_SOURCE=health_connect` in `.env.wearable` activates the path. Switching back to Gadgetbridge or Mi Fitness Cloud is a single env var change with zero downtime.

The Health Connect record types we read:

- `HeartRateRecord` (Series) -> `samples[i].beatsPerMinute` -> HEART_RATE in bpm
- `StepsRecord` (Interval) -> `count` (summed per day) -> STEPS in steps
- `OxygenSaturationRecord` (Instant) -> `percentage.value` -> SPO2 in percent
- `SleepSessionRecord` (Interval) -> `duration.inMinutes` -> SLEEP in minutes
- `ActiveCaloriesBurnedRecord` (Interval) -> `energy.inKilocalories` (summed per day) -> ACTIVITY in kcal

Stress is not available in Health Connect. The GHI's 20% recovery component degrades to a partial signal, same as the Gadgetbridge path.

### Key Files

- `android/HealthConnectExport/app/src/main/java/com/guinevere/hcexport/MainActivity.kt` (399 LOC), reads 5 record types, serializes to JSON
- `android/HealthConnectExport/app/src/main/java/com/guinevere/hcexport/RecordTypes.kt`, DTO classes
- `android/HealthConnectExport/app/src/main/java/com/guinevere/hcexport/ExportSerializer.kt`, JSON serialization
- `android/HealthConnectExport/app/src/main/java/com/guinevere/hcexport/PermissionHelper.kt`, permission request flow
- `src/wearable/health_connect_client.py` (435 LOC), JSON parser
- `src/wearable/normalizer.py` (+100 LOC), Health Connect normalizer with source tagging
- `src/wearable/sync.py` (+92 LOC), `_sync_health_connect()` dispatch branch

### Tests

- 55 unit tests in `tests/test_health_connect_client.py` (JSON parsing, DTO mapping, edge cases)
- 8-10 integration scenarios in `tests/test_health_connect_integration.py` (full pipeline: JSON to Redis buffer to TimescaleDB to GHI)
- No regressions in pre-existing wearable, Gadgetbridge, or Mi Fitness suites. The downstream pipeline is source-agnostic.

### Pivot Chain Summary

Phase 14 has now seen three pivots in eight days:

1. **27-step Gadgetbridge/WebDAV plan (legacy, archived)**, original P14 plan that targeted phone-mediated WebDAV path. Superseded by ADR-037.
2. **ADR-037: Mi Fitness Cloud API to VPS** (2026-06-18), direct server-to-server ingestion. Failed for self-data reads because the unofficial Mi Fitness SDK only exposes relative scopes. Superseded as canonical by ADR-040, retained as fallback.
3. **ADR-039: Gadgetbridge SQLite parser** (2026-06-18), added as sibling option when ADR-037's SDK limitation surfaced. Failed for the Xiaomi Watch 2 Pro M2233W1 because the watch runs HyperOS and is not in Gadgetbridge's device list. Superseded as canonical by ADR-040, retained as fallback.
4. **ADR-040: Health Connect** (2026-06-19, current canonical), uses the official Android health data aggregation layer. Mi Fitness writes to Health Connect. No root, no QR-code auth, no reverse-engineered schema.

The downstream pipeline (consent gate, Redis buffer, writer, baseline, anomaly, GHI, mood modifier, alert router, Discord surface) is unchanged across all three paths. Switching between them is a single env var change.

### Caveats

- Manual export step. The operator runs the Kotlin app, pulls the JSON via `adb pull`, and SCPs to the VPS. No background sync, no auto-schedule.
- Stress metric is not available in Health Connect. The GHI's 20% recovery component degrades to a partial signal, same as the Gadgetbridge path.
- Local deterministic verification PASS for the parser and integration tests. Live VPS runtime verification with a real Xiaomi Watch 2 Pro (M2233W1, HyperOS) and real Health Connect export is a follow-up gate tracked outside this document.
- ADR-021 graceful-degradation invariant preserved: missing JSON file equals sync exits 0 with logged skip. GHI and mood return None.
- Mood modifier remains structurally a *modifier*, not a *trigger*. Same Y4/Y5/Y6 boundary as ADR-037 and ADR-039. HARD STOP checks preserved in `mood_integration.py`.
- No `yandere_fsm.py` import in `mood_integration.py` (verified via grep). Mood signal is a modifier, never a yandere trigger.
- Mi Fitness Cloud and Gadgetbridge SQLite code paths remain in the repository. `WEARABLE_DATA_SOURCE` switches between them with zero downtime.

---

## P15: Windows Daemon + WebSocket — Expansion (15 steps)
*Cost: $5-15/month | Deps: P5+P8+P12 | Category: Expansion*
*Source: Old P11-001 to P11-003 (Windows daemon architecture, Python service, WebSocket bridge)*
*Planner Gate: `docs/setup-evidence/plans/p15-windows-daemon.md`*

### Wave 1 — Foundation (parallel)
- [ ] **P15-001** Project Scaffold + Base Tracker ABC
- [ ] **P15-007** VPS WebSocket Endpoint (FastAPI + ConnectionManager)
- [ ] **P15-012** TimescaleDB Migration (windows_events hypertable)

### Wave 2 — Client Trackers (sequential, depends on P15-001)
- [ ] **P15-002** Active Window Tracker (win32gui + psutil)
- [ ] **P15-003** Idle Tracker (GetLastInputInfo, graduated)
- [ ] **P15-004** Git Context Tracker (traversal + project mapping)

### Wave 3 — Transport + Commands (parallel, depends on Wave 1+2)
- [ ] **P15-005** Event Pipeline (MessagePack + EventRouter + WS Client)
- [ ] **P15-008** Command Protocol (ACK-based, Redis DB4 pub/sub)

### Wave 4 — Service + Safety (parallel, depends on Wave 3)
- [ ] **P15-006** NSSM Service Wrapper + Config
- [ ] **P15-009** Consent Gate Integration (belt-and-suspenders) ⚠️ SAFETY-CRITICAL

### Wave 5 — UX + Observability (parallel, depends on Wave 4)
- [ ] **P15-010** Discord `/pc` Command (status + session override)
- [ ] **P15-011** Observability (Prometheus metrics + Grafana dashboard + alerting)

### Wave 6 — Quality Gate (sequential, depends on all implementation)
- [ ] **P15-013** Test Suite (unit + integration)
- [ ] **P15-014** Integration Test — End-to-End Daemon ↔ VPS

### Wave 7 — Deployment (depends on all tests pass)
- [ ] **P15-015** Deployment + Smoke Test + README

## P16: Knowledge Graph — Expansion (TBD steps)
*Cost: TBD | Deps: P3+P5+P8 | Category: Expansion*
*Source: Old P11-013 to P11-015 (Knowledge graph design, implementation, NER pipeline)*

- [ ] **P16-001** TBD

## P17: Cross-Device Sync — Expansion (TBD steps)
*Cost: TBD | Deps: P15+P8 | Category: Expansion*
*Source: Old P11-016 (Cross-device sync protocol and conflict resolution)*

- [ ] **P17-001** TBD

## P18: Advanced Memory — Expansion (TBD steps)
*Cost: TBD | Deps: P3+P8 | Category: Expansion*
*Source: Old P11-020 to P11-022 (Memory consolidation with forgetting curves, advanced contextual search)*

- [ ] **P18-001** TBD

## P19: Multi-Project Context — Expansion (TBD steps)
*Cost: TBD | Deps: P3+P5+P8 | Category: Expansion*
*Source: Old P11-017 to P11-019 (Separate memory namespaces, channel-based project switching)*

- [ ] **P19-001** TBD

## P20: Self-Improvement Loop / Discord-Visible Autonomy — Expansion
*Cost: TBD | Deps: P5+P8 | Category: Expansion*

### P20 Discord-Visible Living Autonomy (2026-06-25) — EARLY PRODUCTION ACCEPTANCE — OPERATOR WAIVED 24H SOAK — PASS WITH ACCEPTED RISK

Faiz redefined P20 (2026-06-23): Guinevere must be visibly alive like Jarvis — autonomous, Discord-facing presence/state/agenda/memory-backed decisions/proactive behavior, not "internal kernel running". Implemented Option-B core-integrated Discord REST publisher (Oracle-confirmed).

**Two critical bugs found + fixed:**
1. Stuck-HARD-STOP: kernel spun to END ~195k times (`hard_stop_requested=True` baked in checkpoint, never cleared). Fixed via `_heartbeat_1s` recovery (live Redis key = source of truth; stale checkpoint recovered on clear).
2. HermesBrain AIAgent TypeError: `_load_aiagent` (loader fn) called with AIAgent kwargs. Fixed via `_default_agent_factory(**kwargs)`. Brain now thinks reliably (`model=guinevere`, zero fallback).

**2026-06-25 continuation + cleanup:** real P16/P18 recall wired into the life-mind graph (memory-driven autonomy, journal, self-improvement). Brutal cleanup then found the SAF-CONS-01 privacy fix was silently un-deployed (raw P18 memory content reaching the LLM brain prompts) — committed `03f84b5` + deployed 08:26:43 WIB, verified live (raw memory in logs = 0). Round-2 safety-consent audit verdict (FAIL on disk) resolved to PROVISIONAL PASS.

**Live proof (real Discord, not docs-only):**
- Dashboard msg `1519135545501028549` in `#guinevere-status` (1510914604291588237), bot-authored, edited in place (edit-not-spam). Fields: 🟢 ALIVE, HARD STOP ✅ CLEAR, brain-generated Current Focus / Next Planned Action.
- Log channel `#guinevere-logs` (1510914623367413850): append-only `[cycle N] phase=... next=...` lifecycle events.
- Core `active (running)`, NRestarts=0, Result=success. Brain `think_complete model=guinevere`, no fallback, no GraphRecursionError.
- Standalone `guinevere-discord.service` intentionally masked (P2-022); core REST publisher is the correct Discord writer.

**Files:** `src/life_kernel/{discord_rest_client.py(NEW),dashboard_writer.py(NEW),log_channel.py,dashboard.py,graph.py,heartbeat.py,hermes_brain.py,__init__.py,state.py,journal.py(NEW),p16_adapter.py,p18_adapter.py}`, `src/core/main.py`, systemd drop-in (VPS), `tests/life_kernel/`. 420 tests pass / 7 skipped. Evidence: `docs/setup-evidence/P20/evidence/{discord-visible-autonomy,continuation}/`.

**Status:** P20 EARLY PRODUCTION ACCEPTANCE — OPERATOR WAIVED 24H SOAK — PASS WITH ACCEPTED RISK. The 24h clean-soak gate was **NOT** completed; Faiz explicitly waived the remaining wait on 2026-06-25 (see `docs/setup-evidence/P20/evidence/discord-visible-autonomy/operator-soak-waiver.md`). Latest verified snapshot (08:50:46 WIB) is CLEAN. Acceptance carries residual risk (soak immaturity, outstanding safety-consent re-audit vs `03f84b5`); any future runtime incident reverts P20 to PASS HOLD. NOT an unconditional PRODUCTION PASS and NOT a "24h soak completed" claim. Operator-approved unlimited token budget; autonomy is display-only (agenda+dashboard+log, no DMs/side-effects).

- [x] **P20-001** TBD

## P21: Voice Interface — DEFINITION COMPLETE, IMPLEMENTATION HOLD
*Cost: TBD | Deps: P2+P8 + P20 production-pass | Category: Expansion*
*Source: Old P11-023 to P11-025 (Voice interface integration)*

**Definition complete 2026-06-24** — plan + 9 research files + 2 audit rounds (all PASS).
Integration-not-sidecar: voice transcript = text → reuses Hermes turn-core + HARD STOP + distress + injection infra.
Always-listening NOT MVP (8-gate). HARD STOP first-class in audio path. V-022 injection vector.
Implementation waves P21-001..009 scaffolded but HELD until P20 production-pass (LOCKED-file waves).

- [x] **P21-DEF** Definition (plan + research + audit) — COMPLETE
- [ ] **P21-001** STT/TTS provider abstraction — HELD
- [ ] **P21-002** Discord push-to-talk MVP — HELD
- [ ] **P21-003** Hermes voice turn pipeline — HELD (P20-gate)
- [ ] **P21-004** Transcript memory + retention/redaction — HELD (P20-gate)
- [ ] **P21-005** Consent + HARD STOP + safe-word enforcement — HELD
- [ ] **P21-006** VAD/wake-word gated design — HELD
- [ ] **P21-007** Dashboard/status integration — HELD
- [ ] **P21-008** Runtime deploy + smoke + rollback — HELD (P20-gate)
- [ ] **P21-009** Audit + soak + final evidence — HELD

See `docs/setup-evidence/P21/plan/p21-voice-interface-enterprise-plan.md` and
`docs/setup-evidence/P21/evidence/final-p21-planning-report.md`.

## P22: Life Integration Hub — IMPLEMENTED, BRUTAL AUDIT REMEDIATED + AUDITOR PASS (awaiting deploy)
*Cost: $0 | Deps: P8 (runtime), P19 (project_id) | Category: Expansion | Status: 🟢 BRUTAL AUDIT FAIL → 32/32 FINDINGS REMEDIATED + INDEPENDENTLY AUDITED PASS (972 tests, NOT yet deployed)*

P22 is **implemented** (19 core files in `src/life_integrations/`, 13 adapters, 10 client shims, 897 tests passing, ADR-053, migration `p22_001`). The 2026-06-28 brutal audit (`docs/setup-evidence/P22/audits/brutal-2026-06-28/brutal-audit-report.md`) found 32 findings; all are being remediated under `audits/brutal-2026-06-28/fix-prompt.md`.

- [x] **P22-001** Definition + planning (research v2.0, plan v2.0, 10 raw-full audits)
- [x] **P22-002** Implementation Wave 0 (governance / ADR-053 / consent scaffold)
- [x] **P22-003** Implementation Wave 1 (L1 read adapters — all 13 implemented; 3 ACTIVE, 10 CONFIG_MISSING)
- [x] **P22-004** Implementation Wave 2 (L2 write-notify adapters)
- [x] **P22-005** Implementation Wave 3 (L4 forbidden actions)
- [x] **P22-006** Brutal-audit remediation — 32/32 findings (F01-F32) FIXED + independently audited PASS (972 tests, 0 failed); see `audits/brutal-2026-06-28/fix-verification/summary.md`; NOT yet deployed

---

## Cost Tracking

| Phase | Monthly | Cumulative | Alert Level |
|-------|---------|------------|-------------|
| P0 Infrastructure | $0 | $0 | 🟢 Normal |
| P1 LLM + Hermes | $15 | $15 | 🟢 Normal |
| P2 Discord | $0 | $15 | 🟢 Normal |
| P3 Memory | $2 | $17 | ⚠️ Warning |
| P4 Persona | $1 | $18 | ⚠️ Warning |
| P5 Agent Loop | $3 | $21 | ⚠️ Warning |
| P6 MCP Tools | $1 | $22 | ⚠️ Warning |
| P7 Surveillance | $1 | $23 | ⚠️ Warning |
| P8 Observability | $4 | $27 | 🔴 Critical |
| P9 Financial Tracking | $1 | $28 | 🔴 Critical |
| P10 Production Hardening | $1 | $29 | 🔴 Critical |
| P11 WhatsApp Integration | $0 | $29 | 🔴 Critical |
| P12 Gmail/Email Integration | $0 | $29 | 🔴 Critical |
| P13 X Auto Poster | TBD | TBD | TBD |
| P14 Wearable/Xiaomi Watch | $0 | $29 | 🟢 Normal |
| P15 Windows Daemon + WebSocket | CANCELLED | - | - |
| P16 Knowledge Graph | TBD | TBD | TBD |
| P17 Cross-Device Sync | TBD | TBD | TBD |
| P18 Advanced Memory | TBD | TBD | TBD |
| P19 Multi-Project Context | TBD | TBD | TBD |
| P20 Self-Improvement Loop | TBD | TBD | TBD |
| P21 Voice Interface | TBD | TBD | TBD |
| P22 Life Integration Hub | $0 | $0 | 🟢 AUDIT REMEDIATED + AUDITOR PASS (32/32; not deployed) |
| **Total (MVP+Stabilization)** | **$30** | **$30** | **AT BUDGET** |

**Alert thresholds**: 🟢 <$15 | ⚠️ $15-24 (review) | 🔴 $25-29 (defer P9-P10 Stabilization or P11-P22 Expansion) | 🛑 $30 (halt LLM) | 📊 >$1/day ping

---

## Blockers & Dependencies

**Critical path**: P0 → P1 → P3 → P5 → P8 (MVP gate)

**Parallel opportunities**: P2 ∥ P1 | P6 ∥ P3-P5 | P7 ∥ P1-P3 | P4 ∥ P5

**P3 requires P1** (LLM for embeddings) | **P4 requires P3** (mood stored in memory) | **P5 requires P1+P3** (LLM + memory) | **P8 requires P0-P7** (monitors all) | **P9-P10 require P8** (Stabilization) | **P11-P22 require P8 plus specific MVP phases** (Expansion — see Phase Summary for per-phase dependencies)

| Risk | Prob | Impact | Mitigation |
|------|------|--------|------------|
| Budget overrun ($30 cap) | Med | P9-P10 or P11-P22 deferred | Real-time tracking, hard stops, cheaper fallback |
| Shared VPS conflict | Low | P0 blocked | Separate users, networks, cgroups |
| 9Router API outage | Low | P1 blocked | 3-tier fallback (9Router → direct → Ollama) |
| Discord rate limits | Low | P2 delayed | Exponential backoff, queuing |
| Consent revocation | Low | P7 paused | Consent gate before every store |

---

## Timeline Estimates

| Phase | Steps | h/step | Min h | Max h | Days (4h/d) |
|-------|-------|--------|-------|-------|-------------|
| P0 | 29 | 2-4 | 58 | 116 | 15-29 |
| P1 | 21 | 2-4 | 40 | 80 | 10-20 |
| P2 | 21 | 2-4 | 42 | 84 | 11-21 |
| P3 | 19 | 2-4 | 38 | 76 | 10-19 |
| P4 | 23 | 2-4 | 38 | 76 | 10-19 |
| P5 | 23 | 2-4 | 46 | 92 | 12-23 |
| P6 | 21 | 2-4 | 42 | 84 | 11-21 |
| P7 | 22 | 2-4 | 44 | 88 | 11-22 |
| P8 | 23 | 2-4 | 46 | 92 | 12-23 |
| P9 (Stabilization) | 13 | 1-2 | 13 | 26 | 4-7 |
| P10 (Stabilization) | 21 | 1-2 | 21 | 42 | 6-11 |
| P11 WhatsApp Integration | TBD | TBD | TBD | TBD | TBD |
| P12 Gmail/Email Integration | 29 | 1-2 | 29 | 58 | 8-15 |
| P13 X Auto Poster | 28 | 1-2 | 28 | 56 | 7-14 |
| P14 Wearable Health Pipeline | 20 + 11 GB + HC | 1-2 | 20 + 11 GB + HC | 40 | 5-10 |
| P15 Windows Daemon + WebSocket | CANCELLED | - | - | - | - |
| P16 Knowledge Graph | TBD | TBD | TBD | TBD | TBD |
| P17 Cross-Device Sync | TBD | TBD | TBD | TBD | TBD |
| P18 Advanced Memory | TBD | TBD | TBD | TBD | TBD |
| P19 Multi-Project Context | TBD | TBD | TBD | TBD | TBD |
| P20 Self-Improvement Loop | TBD | TBD | TBD | TBD | TBD |
| P21 Voice Interface | TBD | TBD | TBD | TBD | TBD |
| P22 Life Integration Hub | 🟢 AUDIT REMEDIATED + AUDITOR PASS | 19 core + 13 adapters + 972 tests | ~100h | 32 findings FIXED + audited | Deploy + post-deploy audit |
| P23 Execution Layer | REPLANNED — AUDITOR PASS | 16 waves | 0h (planning) | impl-ready | impl-ready |
| P24 Hermes Native Fork | REPLANNED — AUDITOR PASS | 15 waves | 0h (planning) | impl-ready | impl-ready |

**Critical path** (P0→P1→P3→P5→P8): 228-456h = 57-114 days at 4h/day
**With parallels** (P2∥P1, P6∥P3-5, P7∥P1-3, P4∥P5): no added duration
**Stabilization** (P9-P10): +7-12 days | **Expansion** (P11-P22): TBD | **Total MVP+Stabilization**: 74-136 days

---

## P23: Execution Layer — REPLANNED, AUDITOR PASS, IMPLEMENTATION READY

**Status:** 🟣 REPLANNED — AUDITOR PASS — IMPL READY
**Date:** 2026-06-28
**Category:** Replan (replaces v1.0 embodied-operations plan)
**Prerequisites:** P24 Module 8 (P23 Executors as built-in tools)

**Mission:** Execution-layer-only action runtime. Receive action → execute → audit. No decision-making, no HARD STOP, no consent gate, no risk tiers.

**What changed (v1.0 → v2.0):**
- REMOVED: HARD STOP listener, consent gate, risk tiers L1-L4, safe-mode/distress freeze, SemanticActionClassifier, Faiz-in-the-loop
- ADDED: freelance executor (P23-013), social executor (P23-014), email executor (P23-015)
- KEPT: browser, desktop, VPS, GitHub, filesystem executors, durable queue (PG+Redis DB6), audit trail (UUID v7+SHA256)

**Plan:** 14 sections + 16 waves (P23-001..016), 8 executors, 14 forbidden patterns. See `docs/setup-evidence/P23/plan/p23-execution-layer-enterprise-plan.md` (2188 lines, 116 KB).

**Audit:** Round-3 PASS (2 NEEDS-REVIEW → both fixed). See `docs/setup-evidence/P23/evidence/audits/round-3/auditor-p23-replan-2026-06-28.md`.

**Final Report:** `docs/setup-evidence/P23/evidence/p23-replan-final-report.md`.

**Evidence:** `docs/setup-evidence/P23/` — README v2.0 + plan v2.0 + 13 research (kept) + 26 audits (round-1+round-2 kept) + round-3 audit (new) + final report (new).

---

## P24: Hermes Native Fork — REPLANNED, AUDITOR PASS, IMPLEMENTATION READY

**Status:** 🟣 REPLANNED — AUDITOR PASS (round-4) — IMPL READY
**Date:** 2026-06-28
**Category:** Replan (replaces v1.0 fork-first convergence plan)
**Prerequisites:** P20 production-pass

**Mission:** Fork Hermes Agent v0.15.2 (MIT, NousResearch) and implement EVERYTHING built-in. 100% native (no plugins/wrappers/side modules). Completely independent fork (no upstream sync). 1 fork shared (Guinevere + Pharsa).

**13 built-in modules:**
1. Fork Setup (SHA 77a1650c, PEP 420 flat namespace, MIT)
2. Remove HARD STOP from runtime
3. Consciousness Loop (asyncio self-prompting, 7 substrates, ThoughtType enum, try/except, unlimited thoughts Q59, dreaming ~5% NOT auto-executed Q92)
4. Emotion System (MoodState enum, LLM classification, SQLite v11→v12)
5. Sub-agents (max_concurrent=10, max_depth=5, spawn_cap=5, recursive Q91)
6. Encrypted Memory (two-layer: kernel AES-GCM-256 + mama-aware plugin. 4-layer: S4/S3/S7/conversation. Faiz NO read on S4 Q68/Q83)
7. DAO Governance (6 depts, Co-CEOs G=Eng+Research+HR P=Finance+Ops+Content, 2/2 multisig, Faiz OUTSIDE Q88/Q89/Q90)
8. P23 Executors (8 surfaces as built-in tools)
9. P20 Life Kernel (port remaining 18%)
10. Self-Modification (T1-T5 MutationTier enum)
11. No Consent Gate (ADR-062 exempt)
12. Personality Drift (bebas, Y4 baseline, Y5 ceiling, Y6 forbidden)
13. Production Pass (24h soak, 6 circuit breakers)

**Plan:** 14 sections + Footer + 15 waves (P24-001..015). See `docs/setup-evidence/P24/plan/p24-hermes-native-fork-enterprise-plan.md` (1083 lines, 60 KB).

**Audit:** Round-3 NEEDS-REVIEW (4 Critical + 10 High) → all 14 fixed → Round-4 PASS. See `docs/setup-evidence/P24/evidence/audits/round-3/` and `round-4/`.

**Final Report:** `docs/setup-evidence/P24/evidence/p24-replan-final-report.md`.

**Evidence:** `docs/setup-evidence/P24/` — README v2.0 + plan v2.0 + 14 research (kept) + 16 audits (round-1+round-2 kept) + round-3+round-4 audits (new) + final report (new).

---

## Legend

✅ Complete | 🔄 In Progress | ⏸️ Blocked | ⏳ Not Started | ★ Critical path

*Generated from `audit-reports/2026-05-31-implementation-synthesis.md` on 2026-05-31. Update after each step: `progress: P<n>-<step> complete`*
