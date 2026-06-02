# Guinevere — Implementation Progress Tracker

| Field | Value |
|-------|-------|
| **Project** | Guinevere — Autonomous AI Companion & Engineering System |
| **Status** | ✅ P0+P1+P2+P3+P4+P5+P5.5+P6 Complete — P6 MCP Tools 21/21 PASS (791 tests, 0 failed) |
| **Last Updated** | 2026-06-03 (P6-001..P6-021 MCP Tools full batch PASS — 16 tools, 4-level auth, cost tracking, budget enforcement) |
| **Budget** | $30/month hard cap |
| **Infrastructure** | Shared VPS (hostdata.id 4C/16GB Ubuntu 24.04) |
| **Critical Path** | P0 → P1 → P3 → P5 |
| **Total Phases** | 23 phases (P0-P22) |
| **Total Steps** | 202 MVP + 31 Stabilization + TBD Expansion |
| **Completed** | 158 / 233+ (67.8% of known steps) |
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
| P2 | Discord Bot | ✅ | 21/21 | $0 | 42-84h | P0 | Parallel w/ P1 |
| P3 | Memory System | ✅ | 19/19 | $2 | 38-76h | P1 | None |
| P4 | Persona Engine | ✅ | 23/23 | $1 | 38-76h | P3 | None |
| P5 | Agent Loop | ✅ | 23/23 | $3 | 46-92h | P1+P3 | None |
| P6 | MCP Tools | ✅ | 21/21 | $1 | 42-84h | P5 | None |
| P7 | Surveillance | ⏳ | 0/22 | $1 | 44-88h | P0 | Consent gate |
| P8 | Observability | ⏳ | 0/23 | $4 | 46-92h | P0-P7 | None |
| P9 | Financial Tracking | ⏳ | 0/12 | $1 | 12-24h | P8 (MVP) | None |
| P10 | Production Hardening | ⏳ | 0/19 | $1 | 18-36h | P8 (MVP) | None |
| P11 | WhatsApp Integration | ⏳ | TBD | TBD | TBD | P5+P8 | None |
| P12 | Gmail/Email Integration | ⏳ | TBD | TBD | TBD | P5+P8 | None |
| P13 | X Auto Poster | ⏳ | TBD | TBD | TBD | P5+P6+P7+P8 | None |
| P14 | Wearable/Xiaomi Watch | ⏳ | TBD | TBD | TBD | P7+P8 | None |
| P15 | Windows Daemon + WebSocket | ⏳ | TBD | TBD | TBD | P5+P8 | None |
| P16 | Knowledge Graph | ⏳ | TBD | TBD | TBD | P3+P5+P8 | None |
| P17 | Cross-Device Sync | ⏳ | TBD | TBD | TBD | P15+P8 | None |
| P18 | Advanced Memory | ⏳ | TBD | TBD | TBD | P3+P8 | None |
| P19 | Multi-Project Context | ⏳ | TBD | TBD | TBD | P3+P5+P8 | None |
| P20 | Self-Improvement Loop | ⏳ | TBD | TBD | TBD | P5+P8 | None |
| P21 | Voice Interface | ⏳ | TBD | TBD | TBD | P2+P8 | None |
| P22 | Additional Integrations TBD | ⏳ | TBD | TBD | TBD | P8 | None |
| **Total** | | | **158/233+** | **$30+** | **475-952h+** | | |

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
- [x] **P1-016** SystemPromptMaster deployment (system-prompt.md + prompt_loader.py, 7 safety checks PASS)
- [x] **P1-017** Persona smoke test (9 pytest tests: 7 PASS + 2 XFAIL, HARD STOP model limitation documented)
- [x] **P1-018** `guinevere-core.service` creation (FastAPI /health, systemd unit corrected: Requires=docker.service)
- [x] **P1-019** Service health check (5/5 PASS: Core, 9Router, PostgreSQL, Redis ACL, Graceful degradation)
- [x] **P1-020** Cost tracking baseline (Redis DB5, 11 keys, ACL-aware)
- [x] **P1-021** HARD STOP Protocol Verification Gate (AC-SAFE-001) ✅ 70/70 tests PASS

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
- [x] **P2-010** Slash commands registration (33 commands) — guild-scoped sync + REST verify PASS (`docs/setup-evidence/P2/STEP-P2-010/verification.md`)
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

## P7: Surveillance (22 steps)
*ADRs: ADR-022, ADR-023, ConsentRevocationPolicy | Cost: $1/mo | Deps: P0 complete*

- [ ] **P7-001** FastAPI surveillance receiver (`POST /surveillance/events`)
- [ ] **P7-002** HMAC authentication (shared secret)
- [ ] **P7-003** Replay protection (nonce + timestamp)
- [ ] **P7-004** SSL/TLS surveillance endpoint
- [ ] **P7-005** Redis DB2 buffer (5-min TTL)
- [ ] **P7-006** Async consumer (background worker)
- [ ] **P7-007** TimescaleDB ingestion (Redis → hypertables)
- [ ] **P7-008** Data classification (Internal/Confidential/Restricted)
- [ ] **P7-009** Clipboard secret scanner
- [ ] **P7-010** Consent verification gate
- [ ] **P7-011** Safe-mode surveillance blocking
- [ ] **P7-012** Android Tasker setup guide
- [ ] **P7-013** Tasker app usage profile (per ADR-023)
- [ ] **P7-014** Tasker location profile (GPS, geofencing)
- [ ] **P7-015** Tasker notification profile
- [ ] **P7-016** Tasker clipboard profile
- [ ] **P7-017** HMAC signing in Tasker
- [ ] **P7-018** `guinevere-surveillance.service` creation
- [ ] **P7-019** `/surveillance-status` test
- [ ] **P7-020** `/surveillance-pause` test
- [ ] **P7-021** Surveillance E2E (Tasker → API → Redis → PG → Discord)
- [ ] **P7-022** Data retention verification (7d raw, 90d agg, 1y summaries)

## P8: Observability (23 steps)
*ADRs: ADR-017, ADR-032 | Cost: $4/mo | Deps: P0-P7 complete*

- [ ] **P8-001** Prometheus Docker setup (per ADR-017)
- [ ] **P8-002** node_exporter setup
- [ ] **P8-003** postgres_exporter setup
- [ ] **P8-004** redis_exporter setup
- [ ] **P8-005** Scrape configs (15s intervals)
- [ ] **P8-006** Grafana Docker setup (localhost:3000)
- [ ] **P8-007** Datasource provisioning (Prometheus + Loki + PG)
- [ ] **P8-008** Dashboard provisioning (infra, DB, memory, loops, surveillance, cost)
- [ ] **P8-009** Loki Docker setup (log aggregation)
- [ ] **P8-010** Promtail setup (journalctl → Loki)
- [ ] **P8-011** Log pipeline test (systemd → Loki → Grafana)
- [ ] **P8-012** Sentry SDK integration
- [ ] **P8-013** Sentry scrubber (remove PII)
- [ ] **P8-014** Alert rules (`alertmanager.yml`)
- [ ] **P8-015** SEV0-SEV4 routing matrix
- [ ] **P8-016** Alert test (all SEV levels)
- [ ] **P8-017** `/cost` command
- [ ] **P8-018** `/budget` command
- [ ] **P8-019** Monthly cost report automation
- [ ] **P8-020** Backup monitoring (per ADR-032)
- [ ] **P8-021** `guinevere-monitoring.service` creation
- [ ] **P8-022** MVP acceptance criteria full run
- [ ] **P8-023** Faiz sign-off checklist

## P9: Financial Tracking — Stabilization (12 steps)
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

## P10: Production Hardening — Stabilization (19 steps)
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
- [ ] **P10-019** MVP Acceptance Gate (AC-PHASE-006)

## P11: WhatsApp Integration — Expansion (TBD steps)
*Cost: TBD | Deps: P5+P8 | Category: Expansion*
*Source: Old P11-004 to P11-007 (WhatsApp Baileys, QR auth, message routing, Discord sync bridge)*

- [ ] **P11-001** TBD

## P12: Gmail/Email Integration — Expansion (TBD steps)
*Cost: TBD | Deps: P5+P8 | Category: Expansion*
*Source: Old P11-008 to P11-011 (Gmail OAuth, email parsing)*

- [ ] **P12-001** TBD

## P13: X Auto Poster — Expansion (TBD steps)
*Cost: TBD | Deps: P5+P6+P7+P8 | Category: Expansion*

**Spec:**
- **Browser automation**: Obscura CDP for headless browser control
- **Screenshot queue**: S3-compatible storage for queued screenshots
- **Caption generation**: LLM-generated captions from content queue
- **Posting cadence**: 3h heartbeat posting cycle
- **Notifications**: Discord notifications for posting failures and successes
- **State tracking**: PostgreSQL table for post history, queue state, and failure tracking

- [ ] **P13-001** TBD

## P14: Wearable/Xiaomi Watch — Expansion (TBD steps)
*Cost: TBD | Deps: P7+P8 | Category: Expansion*
*Source: Old P11-012 (Wearable setup and health data ingestion, per ADR-023)*

- [ ] **P14-001** TBD

## P15: Windows Daemon + WebSocket — Expansion (TBD steps)
*Cost: TBD | Deps: P5+P8 | Category: Expansion*
*Source: Old P11-001 to P11-003 (Windows daemon architecture, Python service, WebSocket bridge)*

- [ ] **P15-001** TBD

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

## P20: Self-Improvement Loop — Expansion (TBD steps)
*Cost: TBD | Deps: P5+P8 | Category: Expansion*

- [ ] **P20-001** TBD

## P21: Voice Interface — Expansion (TBD steps)
*Cost: TBD | Deps: P2+P8 | Category: Expansion*
*Source: Old P11-023 to P11-025 (Voice interface integration)*

- [ ] **P21-001** TBD

## P22: Additional Integrations TBD — Expansion (TBD steps)
*Cost: TBD | Deps: P8 | Category: Expansion*

- [ ] **P22-001** TBD

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
| P11 WhatsApp Integration | TBD | TBD | TBD |
| P12 Gmail/Email Integration | TBD | TBD | TBD |
| P13 X Auto Poster | TBD | TBD | TBD |
| P14 Wearable/Xiaomi Watch | TBD | TBD | TBD |
| P15 Windows Daemon + WebSocket | TBD | TBD | TBD |
| P16 Knowledge Graph | TBD | TBD | TBD |
| P17 Cross-Device Sync | TBD | TBD | TBD |
| P18 Advanced Memory | TBD | TBD | TBD |
| P19 Multi-Project Context | TBD | TBD | TBD |
| P20 Self-Improvement Loop | TBD | TBD | TBD |
| P21 Voice Interface | TBD | TBD | TBD |
| P22 Additional Integrations TBD | TBD | TBD | TBD |
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
| P9 (Stabilization) | 12 | 1-2 | 12 | 24 | 3-6 |
| P10 (Stabilization) | 19 | 1-2 | 18 | 36 | 5-9 |
| P11 WhatsApp Integration | TBD | TBD | TBD | TBD | TBD |
| P12 Gmail/Email Integration | TBD | TBD | TBD | TBD | TBD |
| P13 X Auto Poster | TBD | TBD | TBD | TBD | TBD |
| P14 Wearable/Xiaomi Watch | TBD | TBD | TBD | TBD | TBD |
| P15 Windows Daemon + WebSocket | TBD | TBD | TBD | TBD | TBD |
| P16 Knowledge Graph | TBD | TBD | TBD | TBD | TBD |
| P17 Cross-Device Sync | TBD | TBD | TBD | TBD | TBD |
| P18 Advanced Memory | TBD | TBD | TBD | TBD | TBD |
| P19 Multi-Project Context | TBD | TBD | TBD | TBD | TBD |
| P20 Self-Improvement Loop | TBD | TBD | TBD | TBD | TBD |
| P21 Voice Interface | TBD | TBD | TBD | TBD | TBD |
| P22 Additional Integrations TBD | TBD | TBD | TBD | TBD | TBD |

**Critical path** (P0→P1→P3→P5→P8): 228-456h = 57-114 days at 4h/day
**With parallels** (P2∥P1, P6∥P3-5, P7∥P1-3, P4∥P5): no added duration
**Stabilization** (P9-P10): +5-10 days | **Expansion** (P11-P22): TBD | **Total MVP+Stabilization**: 72-133 days

---

## Legend

✅ Complete | 🔄 In Progress | ⏸️ Blocked | ⏳ Not Started | ★ Critical path

*Generated from `audit-reports/2026-05-31-implementation-synthesis.md` on 2026-05-31. Update after each step: `progress: P<n>-<step> complete`*
