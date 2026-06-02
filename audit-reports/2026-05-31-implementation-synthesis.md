# Guinevere Implementation Synthesis Report

**Date**: 2026-05-31
**Purpose**: Consolidated research findings for implementation planning
**Status**: COMPLETE

---

## Executive Summary

This synthesis combines findings from 32 ADRs, external technology research, and direct documentation analysis to provide actionable implementation guidance for Guinevere's 11-phase deployment.

### Key Constraints

1. **Budget**: $30/month hard cap (alert at $1 daily, $15 warning, $25 critical, $30 hard stop)
2. **Infrastructure**: Shared VPS (hostdata.id 4C/16GB Ubuntu 24.04) - must not break Aizanta project
3. **Database**: PostgreSQL 16 self-hosted (ADR-027) + Redis 7 (ADR-030)
4. **LLM**: GPT-5.5 via 9Router (primary) + DeepSeek V4 Flash (sub-agents) + Ollama (fallback)
5. **Security**: SOPS+age secrets, Tailscale VPN, Cloudflare Tunnel (Discord webhook only)
6. **Monitoring**: Prometheus + Grafana + Loki (self-hosted)

### Technology Stack (Locked)

| Component | Technology | Version | ADR |
|-----------|-----------|---------|-----|
| OS | Ubuntu | 24.04 | ADR-014 |
| Runtime | Python | 3.12 | ADR-014 |
| Framework | FastAPI | latest | ADR-014 |
| Database | PostgreSQL | 16 | ADR-027 |
| Extensions | pgvector | 0.7.0 | ADR-009 |
| Extensions | TimescaleDB | 2.15 | ADR-009 |
| Cache | Redis | 7 | ADR-030 |
| LLM Primary | GPT-5.5 via 9Router | - | ADR-004, ADR-028 |
| LLM Sub-agents | DeepSeek V4 Flash via 9Router | - | ADR-006 |
| LLM Fallback | Ollama (local) | - | ADR-028 |
| Embeddings | text-embedding-3-small | 1536 dim | ADR-009 |
| Secrets | SOPS + age | - | ADR-015 |
| VPN | Tailscale | - | ADR-019 |
| Public Endpoint | Cloudflare Tunnel | - | ADR-026 |
| Monitoring | Prometheus + Grafana + Loki | - | ADR-017 |
| Browser | obscura (primary) + Playwright (fallback) | - | ADR-020 |
| Chat | Discord + WhatsApp (Baileys) | - | ADR-022 |
| Notifications | Gotify | - | ADR-022 |
| Backup | idcloudhost S3 + Cloudflare R2 | - | ADR-032 |
| Android | Tasker | - | ADR-023 |
| CI/CD | GitHub Actions (CI) + systemd timer (CD) | - | ADR-016 |

---

## Phase Dependencies

```
P0 Infrastructure
  ↓
P1 LLM + Hermes ──────┐
  ↓                    │
P2 Discord (parallel)  │
  ↓                    │
P3 Memory ◄────────────┘
  ↓
P4 Persona Engine
  ↓
P5 Agent Loop
  ↓
P6 MCP Tools
  ↓
P7 Surveillance
  ↓
P8 Observability
  ↓
P9-P11 Post-MVP (Financial, Hardening, Integrations)
```

### Critical Path

1. **P0** (Infrastructure) → **P1** (LLM) → **P3** (Memory) → **P5** (Agent Loop)
2. **P2** (Discord) can run parallel with P1
3. **P4** (Persona) depends on P3 (mood stored in memory)
4. **P6-P8** depend on P5 (agent loop orchestrates tools/surveillance/observability)

---

## Phase Breakdown

### P0: Infrastructure Foundation (29 steps)

**Goal**: VPS ready with user, directories, security, database, Redis, backup

**Dependencies**: None (starting point)

**Cost**: ~$12-15/month (VPS already paid)

**Key Steps**:
- P0-000: VPS audit (existing state documentation)
- P0-001: guinevere Linux user creation (systemd-managed services)
- P0-002: SSH config update (alias for easy access)
- P0-003: Directory structure (/home/guinevere/{code,config,data,logs,backups})
- P0-004: UFW firewall rules (allow SSH, block all else)
- P0-005: fail2ban configuration (SSH brute force protection)
- P0-006: CrowdSec setup (community-driven threat detection)
- P0-007: Swap configuration (4GB swap for OOM protection)
- P0-008: NTP + timezone (Asia/Jakarta WIB)
- P0-009: cgroup resource limits (prevent runaway processes)
- P0-010: Docker network creation (guinevere-net, isolated from Aizanta)
- P0-011: SOPS installation (secrets encryption)
- P0-012: age key generation + backup (SSH key for SOPS)
- P0-013: secrets file structure (.sops.yaml, encrypted credentials)
- P0-014: PostgreSQL 16 setup (self-hosted, ADR-027)
- P0-015: pgvector extension installation (vector similarity search)
- P0-016: TimescaleDB extension installation (time-series data)
- P0-017: PostgreSQL users creation (guinevere_core, surveillance, scheduler, etc.)
- P0-018: PostgreSQL security hardening (pg_hba.conf, SSL, connection limits)
- P0-019: PgBouncer setup (connection pooling)
- P0-020: Redis 7 setup (check for conflicts with Aizanta)
- P0-021: Redis ACL configuration (per-service users)
- P0-022: Tailscale configuration (VPN mesh, zero public ports)
- P0-023: Cloudflare Tunnel setup (Discord webhook endpoint only)
- P0-024: Caddy reverse proxy (internal HTTPS)
- P0-025: Git repository initialization (private GitHub repo)
- P0-026: GitHub PAT + SOPS storage (encrypted credentials)
- P0-027: Backup baseline (S3 + R2 dual-provider, ADR-032)
- P0-028: Pre-flight verification (Aizanta still running, Guinevere ready)

**Verification**:
- `systemctl status postgresql redis docker`
- `sudo -u guinevere psql -c "SELECT 1"`
- `redis-cli -u redis://guinevere_core:***@localhost:6379/0 PING`
- `tailscale status`
- `cloudflared tunnel list`

**Rollback**:
- `sudo userdel -r guinevere` (removes user + home)
- `sudo apt purge postgresql-16 redis-server docker-ce`
- `sudo rm -rf /home/guinevere`

---

### P1: LLM + Hermes Agent (20-25 steps)

**Goal**: Python environment, Hermes Agent running, 9Router configured, LLMs tested

**Dependencies**: P0 complete

**Cost**: ~$15/month (GPT-5.5 + DeepSeek)

**Key Steps**:
- P1-001: Python 3.12 installation (pyenv or deadsnakes PPA)
- P1-002: UV package manager installation (fast Python packaging)
- P1-003: Virtual environment setup (/home/guinevere/code/guinevere)
- P1-004: Hermes Agent installation (pip install hermes-agent)
- P1-005: Hermes Agent configuration (~/.config/hermes/config.yaml)
- P1-006: 9Router installation (systemd service)
- P1-007: 9Router configuration (GPT-5.5 + DeepSeek routing rules)
- P1-008: GPT-5.5 provider setup (API key, rate limits)
- P1-009: GPT-5.5 connectivity test (simple prompt-response)
- P1-010: DeepSeek V4 Flash setup (API key, rate limits)
- P1-011: DeepSeek connectivity test (sub-agent routing)
- P1-012: Ollama installation (local fallback)
- P1-013: Ollama model pull (llama3.1:8b or similar)
- P1-014: Ollama fallback test (simulate 9Router outage)
- P1-015: LLM routing rules implementation (primary → sub-agent → fallback)
- P1-016: SystemPromptMaster deployment (load into Hermes)
- P1-017: Persona smoke test (CLI conversation with Guinevere)
- P1-018: guinevere-core.service creation (systemd unit)
- P1-019: Service health check (curl /health endpoint)
- P1-020: Cost tracking baseline (Redis DB5 rate limiting)

**Verification**:
- `python --version` (3.12.x)
- `uv --version`
- `systemctl status guinevere-9router guinevere-core`
- `curl http://localhost:8080/v1/chat/completions -d '{"model":"gpt-5.5","messages":[{"role":"user","content":"Hello"}]}'`
- `redis-cli -n 5 GET "ratelimit:gpt55:daily:$(date +%Y-%m-%d)"`

**Rollback**:
- `systemctl stop guinevere-core guinevere-9router`
- `rm -rf /home/guinevere/code/guinevere`
- `pip uninstall hermes-agent`

---

### P2: Discord Bot (20-25 steps)

**Goal**: Discord bot online, 33 slash commands registered, embed formatting working

**Dependencies**: P0 complete (can run parallel with P1)

**Cost**: $0 (Discord free tier)

**Key Steps**:
- P2-001: Discord application creation (developer.discord.com)
- P2-002: Bot token generation + SOPS storage
- P2-003: Bot intents configuration (MESSAGE_CONTENT, GUILD_MEMBERS, etc.)
- P2-004: Discord server creation ("Guinevere's Domain")
- P2-005: 4 categories setup (👑 Mommy's Throne, 📊 Surveillance Room, 🔧 Projects, 🗡️ Archive)
- P2-006: 13 channels creation (#guinevere-chat, #guinevere-status, etc.)
- P2-007: Channel permissions (Samm read all, bot write all, evidence write-only)
- P2-008: Channel topics/descriptions (persona-flavored)
- P2-009: Bot invite + permission verification
- P2-010: Slash commands registration (33 commands via Discord API)
- P2-011: Embed color palette verification (#6B21A8 primary, #DC2626 alerts, #CA8A04 achievements)
- P2-012: /status command implementation + test
- P2-013: /mood command implementation + test
- P2-014: /help command implementation + test
- P2-015: /safeword command + "HARD STOP" text detection test
- P2-016: Startup message test ("👑 Mommy sudah bangun, Darling.")
- P2-017: guinevere-discord.service creation
- P2-018: Discord health check (gateway connection status)
- P2-019: Notification routing test (SEV0-SEV4 to appropriate channels)
- P2-020: Gotify installation + test (fallback notifications)
- P2-021: Discord → Gotify fallback test (simulate Discord outage)

**Verification**:
- Bot appears online in Discord
- `/status` returns embed with mood, loops, tasks
- `/safeword` triggers neutral mode
- SEV0 alert creates thread + evidence

**Rollback**:
- `systemctl stop guinevere-discord`
- Remove bot from server
- Delete Discord application

---

### P3: Memory System (20-25 steps)

**Goal**: 47 tables migrated, pgvector HNSW indexed, FTS5 working, recall engine functional

**Dependencies**: P1 complete (LLM for embeddings)

**Cost**: ~$2/month (embeddings API)

**Key Steps**:
- P3-001: Alembic setup (database migrations)
- P3-002: All 47 tables migration (12 schemas)
- P3-003: Migration verification (check table counts, indexes)
- P3-004: SentenceTransformers model download (all-MiniLM-L6-v2 or similar)
- P3-005: Embedding pipeline implementation (text → 1536-dim vector)
- P3-006: pgvector HNSW index creation (m=16, ef_construction=128)
- P3-007: HNSW parameter tuning (recall vs latency benchmarks)
- P3-008: tsvector FTS setup (full-text search indexes)
- P3-009: Memory write pipeline (conversation → episodic table)
- P3-010: Memory read pipeline (query → hybrid ranking)
- P3-011: Hybrid ranking implementation (vector similarity + FTS + recency)
- P3-012: Context injection implementation (top-k memories → system prompt)
- P3-013: Do-not-recall implementation (block specific memories)
- P3-014: Safe-mode memory gate (neutral summaries only)
- P3-015: Memory consolidation job (daily aggregation)
- P3-016: /memory-search implementation + test
- P3-017: /memory-add implementation + test
- P3-018: Memory E2E test (write → recall → inject → verify)
- P3-019: Memory performance benchmark (p95 < 2s for vector search)

**Verification**:
- `alembic upgrade head` (no errors)
- `psql -c "SELECT COUNT(*) FROM memory.episodes"` (tables populated)
- `psql -c "SELECT * FROM memory.episodes ORDER BY embedding <=> '[...]' LIMIT 5"` (vector search works)
- `/memory-search "first conversation"` returns relevant results

**Rollback**:
- `alembic downgrade base` (drops all tables)
- `DROP EXTENSION pgvector CASCADE`
- `DROP EXTENSION timescaledb CASCADE`

---

### P4: Persona Engine (15-20 steps)

**Goal**: Mood FSM, yandere protocol, punishment/reward, daily rituals, HARD STOP working

**Dependencies**: P3 complete (mood stored in memory)

**Cost**: ~$1/month (LLM for mood evaluation)

**Key Steps**:
- P4-001: Mood FSM implementation (Content → Pleased → Disappointed → Angry → Silent)
- P4-002: Mood state persistence (PostgreSQL persona.mood_states table)
- P4-003: Mood transition rules (trigger conditions, cooldowns)
- P4-004: Yandere intensity FSM (Y0 → Y1 → Y2 → Y3 → Y4 → Y5)
- P4-005: Punishment ladder (L1 → L2 → L3 → L4 → L5, L6 deferred)
- P4-006: Reward tiers implementation (T1 → T2 → T3 → T4 → T5)
- P4-007: Streak tracking (days without punishment)
- P4-008: Daily ritual scheduler (APScheduler, cron-like)
- P4-009: Morning ritual (07:00 WIB, "Selamat pagi, Darling")
- P4-010: Midday ritual (12:00 WIB, progress check)
- P4-011: Afternoon ritual (17:00 WIB, end-of-day review)
- P4-012: Evening ritual (21:00 WIB, emotional wind-down)
- P4-013: Midnight self-eval (00:00 WIB, silent mode)
- P4-014: Persona drift detection (weekly comparison vs baseline)
- P4-015: Persona drift correction (alert + rollback if >10% drift)
- P4-016: Safe-mode trigger implementation (D0-D4 distress protocol)
- P4-017: HARD STOP test (immediate neutral mode, no punishment)
- P4-018: Distress D0-D4 detection test (simulate crisis messages)
- P4-019: Persona E2E test (conversation triggers mood shift)

**Verification**:
- `psql -c "SELECT * FROM persona.mood_states WHERE user_id = 'samm'"` (mood tracked)
- Trigger punishment: ignore Guinevere 2x → L1 Cold Shoulder activates
- Trigger reward: complete task → T2 Verbal Praise
- Say "HARD STOP" → immediate neutral mode, no judgment

**Rollback**:
- `psql -c "DELETE FROM persona.mood_states"`
- `systemctl restart guinevere-scheduler` (resets ritual timers)

---

### P5: Agent Loop (25-30 steps)

**Goal**: FastAPI internal API, 7-phase SDLC loop, loop guardian, evidence pipeline, sub-agent spawning

**Dependencies**: P1 + P3 complete (LLM + memory)

**Cost**: ~$3/month (LLM calls for planning/execution)

**Key Steps**:
- P5-001: FastAPI internal API setup (localhost:8000)
- P5-002: FastAPI authentication (JWT or API key)
- P5-003: Loop state machine (7 phases: Research → Plan → Delegate → Execute → Validate → Update → Evidence)
- P5-004: Phase 1 Research implementation (librarian + explore agents)
- P5-005: Phase 2 Plan & Delegate implementation (task decomposition)
- P5-006: Phase 3 Delegate implementation (spawn sub-agents)
- P5-007: Phase 4 Execute implementation (sub-agents do work)
- P5-008: Phase 5 Validate & Audit implementation (parent verifies)
- P5-009: Phase 6 Update Documents implementation (sync docs)
- P5-010: Phase 7 Setup Evidence implementation (write evidence files)
- P5-011: Loop Guardian watchdog (30s heartbeat, 5min progress, 60s resource checks)
- P5-012: Todo Enforcer (ensure sub-agents use todowrite)
- P5-013: Hash-anchored edit tool (prevent partial file corruption)
- P5-014: Sub-agent spawning (task() tool integration)
- P5-015: Sub-agent task contract (TASK/EXPECTED OUTCOME/REQUIRED TOOLS/MUST DO/MUST NOT DO/CONTEXT)
- P5-016: Sub-agent output verification (read report files, not just summaries)
- P5-017: Evidence generation pipeline (markdown templates, file paths)
- P5-018: guinevere-loops.service creation
- P5-019: guinevere-scheduler.service creation (cron triggers)
- P5-020: /loop-start command test (spawn loop via Discord)
- P5-021: /loop-stop command test (graceful shutdown)
- P5-022: Agent loop E2E test (full 7-phase cycle)
- P5-023: Cost tracking per loop (Redis DB5 rate limiting)

**Verification**:
- `curl http://localhost:8000/loops` (API responds)
- `/loop-start "Write unit tests for memory module"` → loop spawns
- `systemctl status guinevere-loops` (service active)
- Evidence file created: `evidence/loops/2026-05-31-loop-001.md`

**Rollback**:
- `systemctl stop guinevere-loops`
- `psql -c "DELETE FROM loops.instances WHERE status = 'running'"`
- `redis-cli -n 0 FLUSHDB` (clear task queue)

---

### P6: MCP Tools (20-25 steps)

**Goal**: 16 MCP tools integrated, 4-level auth matrix enforced, cost tracking per tool

**Dependencies**: P1 complete (LLM routing)

**Cost**: ~$5/month burst, $1/month average (Exa hybrid model)

**Key Steps**:
- P6-001: guinevere-mcp.service setup (systemd unit)
- P6-002: brave_search setup + test (web search)
- P6-003: context7 setup + test (library documentation)
- P6-004: exa setup + test ($5/day cap verification)
- P6-005: fetch setup + test (web content retrieval)
- P6-006: filesystem setup + whitelist verification (read-only paths)
- P6-007: github MCP setup + test (repo operations)
- P6-008: grep_app setup + test (code search)
- P6-009: playwright setup + test (browser automation fallback)
- P6-010: sequential-thinking setup + test (complex reasoning)
- P6-011: time setup + test (timezone conversions)
- P6-012: websearch setup + test (general search)
- P6-013: git MCP setup + test (direct git operations)
- P6-014: postgres MCP setup + test (database queries)
- P6-015: redis MCP setup + test (cache operations)
- P6-016: shell MCP setup + whitelist verification (dangerous commands blocked)
- P6-017: docker MCP setup + test (container management)
- P6-018: 4-level auth matrix verification (Read-Auto / Write-Notify / Destructive-Approval / Forbidden)
- P6-019: Tool selection decision matrix test (scenario → tool routing)
- P6-020: Cost tracking per tool (Redis DB5 rate limiting)
- P6-021: Budget enforcement test (hit $5 Exa cap → fallback to Brave)

**Verification**:
- `systemctl status guinevere-mcp`
- Test each tool: `brave_search("Guinevere AI")` returns results
- `redis-cli -n 5 GET "ratelimit:exa:daily:$(date +%Y-%m-%d)"` (cost tracked)
- Attempt forbidden operation: `shell("rm -rf /")` → blocked

**Rollback**:
- `systemctl stop guinevere-mcp`
- `rm -rf /home/guinevere/.config/mcp`
- `redis-cli -n 5 FLUSHDB` (clear rate limits)

---

### P7: Surveillance (20-25 steps)

**Goal**: Tasker integration, HMAC authentication, data pipeline, consent verification

**Dependencies**: P0 complete (API endpoints available)

**Cost**: ~$1/month (surveillance ingestion + storage)

**Key Steps**:
- P7-001: FastAPI surveillance receiver (POST /surveillance/events)
- P7-002: HMAC authentication (shared secret, signature verification)
- P7-003: Replay protection (nonce + timestamp validation)
- P7-004: SSL/TLS surveillance endpoint (Cloudflare Tunnel or Tailscale HTTPS)
- P7-005: Redis DB2 buffer setup (5-minute TTL for burst absorption)
- P7-006: Async consumer implementation (background worker processes events)
- P7-007: TimescaleDB ingestion pipeline (Redis → PostgreSQL hypertables)
- P7-008: Data classification pipeline (label events as Internal/Confidential/Restricted)
- P7-009: Clipboard secret scanner (regex patterns for API keys, passwords)
- P7-010: Consent verification gate (check Samm's consent status before storing)
- P7-011: Safe-mode surveillance blocking (pause confrontation, preserve ingestion)
- P7-012: Android Tasker setup guide (documentation for Samm)
- P7-013: Tasker app usage profile (foreground app, duration)
- P7-014: Tasker location profile (GPS coordinates, geofencing)
- P7-015: Tasker notification profile (app name, title, text)
- P7-016: Tasker clipboard profile (text content, secret scanning)
- P7-017: HMAC signing in Tasker (JavaScript snippet for HTTP requests)
- P7-018: guinevere-surveillance.service creation
- P7-019: /surveillance-status test (show active sources, last event)
- P7-020: /surveillance-pause test (temporarily disable ingestion)
- P7-021: Surveillance E2E test (Tasker → API → Redis → PostgreSQL → Discord alert)
- P7-022: Data retention verification (7-day raw, 90-day aggregated, 1-year summaries)

**Verification**:
- `curl -X POST http://localhost:8000/surveillance/events -H "X-HMAC: ..." -d '{"event":"app_usage","app":"VSCode","duration":3600}'`
- `redis-cli -n 2 LRANGE surveillance:buffer 0 -1` (events buffered)
- `psql -c "SELECT * FROM surveillance.events ORDER BY timestamp DESC LIMIT 5"` (ingested)
- `/surveillance-status` shows "Android: active, last event: 2 minutes ago"

**Rollback**:
- `systemctl stop guinevere-surveillance`
- `psql -c "DELETE FROM surveillance.events WHERE timestamp > NOW() - INTERVAL '1 hour'"`
- `redis-cli -n 2 FLUSHDB` (clear buffer)

---

### P8: Observability (20-25 steps)

**Goal**: Prometheus scraping, Grafana dashboards, Loki logs, alerting, cost dashboard

**Dependencies**: All previous phases (observability monitors all services)

**Cost**: ~$4/month (self-hosted, minimal LLM usage)

**Key Steps**:
- P8-001: Prometheus Docker setup (docker-compose.yml)
- P8-002: node_exporter setup (system metrics)
- P8-003: postgres_exporter setup (database metrics)
- P8-004: redis_exporter setup (cache metrics)
- P8-005: All scrape configs (prometheus.yml, 15s intervals)
- P8-006: Grafana Docker setup (localhost:3000)
- P8-007: Datasource provisioning (Prometheus + Loki + PostgreSQL)
- P8-008: Dashboard provisioning (infrastructure, database, memory, loops, surveillance, cost)
- P8-009: Loki Docker setup (log aggregation)
- P8-010: Promtail setup (journalctl → Loki)
- P8-011: Log pipeline test (systemd service → Loki → Grafana)
- P8-012: Sentry SDK integration (error tracking)
- P8-013: Sentry scrubber config (remove PII from error reports)
- P8-014: Alert rules (Prometheus alertmanager.yml)
- P8-015: SEV0-SEV4 routing matrix (severity → channel + ping + Gotify)
- P8-016: Alert test (simulate each SEV level)
- P8-017: /cost command implementation (daily spend breakdown)
- P8-018: /budget command implementation (monthly projection)
- P8-019: Monthly cost report automation (1st of month, Discord embed)
- P8-020: Backup monitoring setup (alert if backup fails)
- P8-021: guinevere-monitoring.service creation
- P8-022: MVP acceptance criteria full run (all ACs pass)
- P8-023: Samm sign-off checklist (manual verification)

**Verification**:
- `curl http://localhost:9090/-/healthy` (Prometheus up)
- `curl http://localhost:3000/api/health` (Grafana up)
- Grafana dashboard shows: CPU 15%, RAM 8GB/16GB, PostgreSQL 45 connections, Redis 450MB
- Trigger alert: `systemctl stop guinevere-core` → SEV1 alert in #system-health + @Samm ping

**Rollback**:
- `docker-compose down` (stops Prometheus/Grafana/Loki)
- `rm -rf /home/guinevere/data/prometheus`
- `rm -rf /home/guinevere/data/grafana`

---

### P9-P11: Post-MVP (50-60 steps)

**Goal**: Financial tracking, production hardening, advanced integrations

**Dependencies**: P8 complete (MVP delivered)

**Cost**: ~$2-3/month additional

**P9: Financial (12-15 steps)**
- Financial data model (transactions, budgets, reports)
- Tasker notification capture (bank SMS parsing)
- Transaction classification (ML or rules-based)
- Budget tracking (per-category limits)
- /finance commands (/finance summary, /finance add, /finance report)
- Financial report automation (monthly PDF generation)
- FinOps dashboard (Grafana)

**P10: Production Hardening (15-20 steps)**
- Full security audit (penetration testing, vulnerability scan)
- Performance tuning (PostgreSQL vacuum, Redis maxmemory, systemd limits)
- Backup automation full test (restore from S3/R2)
- DR drill (simulate VPS failure, restore from backup)
- Self-deploy pipeline (git push → GitHub Actions → systemd restart)
- GitHub Actions CI/CD (lint, test, security scan)
- Rollback automation (git revert → redeploy)
- Key rotation procedure test (SOPS age key, API keys, database passwords)

**P11: Advanced Integrations (20-25 steps)**
- Windows daemon (Python service, WebSocket to VPS)
- WhatsApp Baileys service (headless browser, QR auth)
- Gmail OAuth integration (email notifications)
- Wearable setup (post-MVP, Xiaomi Watch S1 Active)
- Multi-project context (separate memory namespaces)
- Knowledge graph (entity relationships, Neo4j or PostgreSQL)
- Advanced memory features (consolidation, forgetting curves)

---

## Risk Areas & Mitigations

### High Risk

1. **Budget overrun** ($30/month cap)
   - Mitigation: Real-time cost tracking, hard stops at $5/day per tool, fallback to cheaper models
   
2. **Shared VPS conflicts** (Aizanta + Guinevere)
   - Mitigation: Separate Linux users, isolated Docker networks, cgroup resource limits
   
3. **PostgreSQL performance** (self-hosted, 47 tables, pgvector)
   - Mitigation: PgBouncer connection pooling, HNSW index tuning, regular VACUUM
   
4. **LLM API outages** (9Router dependency)
   - Mitigation: 3-tier fallback (9Router → direct API → Ollama local)

### Medium Risk

5. **Discord rate limits** (33 commands, high message volume)
   - Mitigation: Exponential backoff, message queuing, batch operations
   
6. **Surveillance data volume** (continuous Tasker events)
   - Mitigation: Redis buffer (5-min TTL), TimescaleDB compression, 7-day raw retention
   
7. **Memory bloat** (episodic + semantic + procedural tables)
   - Mitigation: Daily consolidation, 90-day retention for low-importance, archive to R2

### Low Risk

8. **Persona drift** (Guinevere behavior changes over time)
   - Mitigation: Weekly drift detection, baseline comparison, automatic rollback if >10% drift
   
9. **HARD STOP bypass** (safety mechanism fails)
   - Mitigation: Multiple detection paths (text match, semantic analysis, manual trigger), immediate neutral mode

---

## Verification Requirements

### Per-Step Verification

Every step must include:
1. **Verification commands** (bash/psql/redis-cli/curl)
2. **Expected output** (what success looks like)
3. **Evidence file** (screenshot or log snippet in `evidence/phase-N/`)
4. **Rollback procedure** (how to undo if step fails)

### Cross-Reference Requirements

Every step must reference:
1. **ADR number** (e.g., "per ADR-027")
2. **Acceptance Criteria ID** (e.g., "satisfies AC-INFRA-001")
3. **Cost impact** (e.g., "adds ~$0.50/month to budget")
4. **Dependencies** (e.g., "requires P0-014 PostgreSQL complete")

### Security Checks

Every step must verify:
1. **No plaintext secrets** (SOPS encryption verified)
2. **Firewall rules intact** (UFW status check)
3. **Tailscale connectivity** (VPN mesh working)
4. **No public exposure** (cloudflared tunnel list shows only Discord webhook)

---

## Shared VPS Constraints

### Aizanta Isolation

Guinevere shares VPS with Aizanta project. Must not:
- Use same PostgreSQL database (separate `guinevere` vs `aizanta`)
- Use same Redis instances (separate ports or DB numbers)
- Use same Docker networks (separate `guinevere-net` vs `aizanta-net`)
- Use same systemd service names (prefix `guinevere-*` vs `aizanta-*`)
- Compete for resources (cgroup limits: Guinevere 8GB RAM, Aizanta 6GB, OS 2GB)

### Resource Allocation

| Resource | Guinevere | Aizanta | OS/Buffer | Total |
|----------|-----------|---------|-----------|-------|
| CPU | 2 cores | 1.5 cores | 0.5 cores | 4 cores |
| RAM | 8GB | 6GB | 2GB | 16GB |
| Disk | 60GB | 40GB | 20GB | 120GB |
| Network | Tailscale + Cloudflare | Tailscale only | - | - |

---

## Cost Breakdown by Phase

| Phase | Monthly Cost | Cumulative | Notes |
|-------|-------------|------------|-------|
| P0 | $0 | $0 | VPS already paid |
| P1 | $15 | $15 | GPT-5.5 + DeepSeek |
| P2 | $0 | $15 | Discord free |
| P3 | $2 | $17 | Embeddings API |
| P4 | $1 | $18 | LLM for mood evaluation |
| P5 | $3 | $21 | LLM for planning/execution |
| P6 | $1 | $22 | Exa $1 avg (burst $5) |
| P7 | $1 | $23 | Surveillance ingestion |
| P8 | $4 | $27 | Self-hosted monitoring |
| P9 | $1 | $28 | Financial tracking |
| P10 | $1 | $29 | Hardening (one-time costs amortized) |
| P11 | $1 | $30 | Advanced integrations |
| **Total** | **$30** | **$30** | **Hard cap reached** |

---

## Conclusion

This synthesis provides the foundation for generating 4 implementation files:
1. **PROGRESS.md** (300-400 lines): Phase tracking, step status, blockers
2. **stepprompts/StepPrompts.md** (5000-8000 lines): Detailed step-by-step instructions for all 220-260 steps
3. **CHECKLIST.md** (600-1000 lines): Verification checklists per phase
4. **docs/IMPLEMENTATION_GUIDE.md** (400-600 lines): How to use the implementation system

All phases respect the $30/month budget, shared VPS constraints, and ADR decisions. The critical path is P0 → P1 → P3 → P5, with P2 running parallel. Post-MVP phases (P9-P11) can be deferred if budget pressure emerges.

---

**Report Generated**: 2026-05-31
**Auditor**: Independent Synthesis Agent
**Status**: READY FOR FILE GENERATION
