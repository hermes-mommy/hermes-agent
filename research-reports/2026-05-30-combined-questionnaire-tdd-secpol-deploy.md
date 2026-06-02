# Guinevere Combined Questionnaire — TDD + Security Policy + Deployment Guide
**Date:** 2026-05-30 | **Format:** Multiple Choice A/B/C/D | **Total:** 232 questions
**Rule:** Answer `ALL:X` (where X = A/B/C/D) or per-number seperti `Q1:A Q5:C Q10:D`

---

# DOCUMENT 1: Technical Design Document (TDD) — Q1 to Q80

## A. System Architecture (Q1–Q10)

**Q1 — Mermaid C4 depth:** Guinevere TDD termasuk Mermaid C4 diagram. Level detail yang kamu mau?
A. C4 Level 1 (System Context) — Box Guinevere + external systems only
B. C4 Level 1 + Level 2 (Container) — Break down: Hermes Agent, PostgreSQL, Redis, FastAPI, systemd, Tailscale
C. C4 Level 1 + 2 + 3 (Component) — Break down setiap container ke individual modules (persona/memory/surveillance/scheduler)
D. C4 Level 1 + 2 + 3 + 4 (Code) — Sampai class-level diagram untuk core subsystem

**Q2 — Network topology detail:** Tailscale + Cloudflare Tunnel diagram level yang diinginkan?
A. High-level: Tailscale mesh dengan semua devices + Cloudflare Tunnel untuk Discord webhook saja
B. Medium: Include semua IP Tailscale, port internal, DNS mapping (guinevere.internal, postgres.internal, dll)
C. Detailed: Include firewall rules, ACL policy, traffic flow direction per service, protocol per connection
D. Full: Include packet flow, TLS termination points, latency expectation per hop

**Q3 — Data flow diagram domain count:** TDD butuh data flow diagram. Berapa domain yang di-cover?
A. 2 domain: Surveillance flow + LLM flow
B. 4 domain: Surveillance, LLM, Memory Recall, Discord Interaction
C. 6 domain: Surveillance, LLM, Memory Recall, Financial, SDLC Loop, Daily Rituals
D. 8+ domain: Semua di atas + WhatsApp, Gmail, Backup/Restore, Deployment

**Q4 — Trust boundary diagram:** Bagaimana trust boundary TDD harus di-document?
A. Single trust boundary: Tailscale = trusted, everything else = untrusted
B. 3 zones: Tailscale internal (trusted) → Cloudflare tunnel edge (semi-trusted) → External internet (untrusted)
C. Full zero-trust: Setiap service boundary documented dengan authentication requirement, encryption level, access policy, safe-mode override — shaped by ABAC
D. Full zero-trust + attack path: Include potential compromise path per boundary, blast radius per zone

**Q5 — Service failure isolation:** How detailed should service dependency and failure isolation be?
A. List dependencies per service — no failure scenario
B. Include failure mode: service X down → what breaks, auto-recovery path
C. Include cascading failure: service X down → service Y degrades → service Z queued — full blast radius
D. Include chaos engineering: Define what happens when both 9Router AND OpenRouter down simultaneously (graceful degradation), when Redis and PostgreSQL both down

**Q6 — systemd ordering:** systemd service dependency graph detail?
A. Text list: `Requires=, After=` per service
B. Ordered graph: Which services must start first, parallel starts, restart dependencies
C. Full dependency graph + health check ordering: Include startup health probes, timeout per service, restart backoff strategy
D. Full + resource contention: Include CPU/memory budgeting during startup, cold start vs warm restart behavior

**Q7 — Infrastructure-as-Code strategy:** How should Guinevere's infrastructure be managed?
A. Manual setup documented in Deployment Guide only — TDD references it
B. Shell scripts for setup (setup.sh, restore.sh) referenced in TDD
C. Ansible playbook or Docker Compose structure defined in TDD
D. Full Terraform/OpenTofu for VPS provisioning + Ansible for config — everything in code

**Q8 — Horizontal scaling consideration:** TDD perlu bahas scaling strategy? (Single VPS constraint)
A. No — single VPS, no scaling needed, explicitly out of scope
B. Mention future: "When budget allows, database replication, Redis cluster, multiple VPS"
C. Document current capacity limits: Max concurrent loops, max sub-agents, max surveillance events/sec with current VPS
D. Document capacity limits + scaling triggers: At what point do we need a second VPS? What's the migration path?

**Q9 — Backup architecture in TDD:** Seberapa detail backup flow di-document?
A. Reference Backup/DR runbook — detail ada di sana
B. Include WAL streaming architecture, pg_dump flow, Redis RDB+AOF, multi-destination (R2 + idcloudhost)
C. Full pipeline: backup initiation → encryption at source → parallel upload → integrity check → inventory update → alert on failure
D. Full pipeline + restore drill automation: scheduled restore test, corruption detection, partial restore capability

**Q10 — Environment strategy (prod/staging/dev):** Bagaimana environment strategy?
A. Single VPS = single environment — no separate staging, only feature branches
B. Two environments on same VPS: production (main branch) + staging (separate DB, separate Discord channel, DeepSeek instead of GPT-5.5)
C. Two environments + dev environment: add local development on Samm's Windows laptop with mock services
D. Three environments + CI: prod on VPS, staging on VPS (isolated), dev on laptop, CI runs on GitHub Actions

## B. Core Services Design (Q11–Q20)

**Q11 — guinevere-core.service thread model:** How should Hermes Agent + persona engine threads be designed?
A. Single-threaded: async event loop, no thread pool — keep it simple
B. Thread pool: persona processing, memory injection, and Discord handling masing-masing punya dedicated thread
C. Async tasks with supervisor: Multiple async tasks monitored by supervisor thread that restarts hung tasks
D. Full actor model: Each capability (persona, memory, surveillance processing, scheduling, loop orchestration) is independent actor with mailbox

**Q12 — guinevere-api.service endpoint design:** FastAPI surveillance receiver + internal API — satu service atau dua?
A. Satu FastAPI service dengan 2 routers (surveillance di :8000, internal API di :8001)
B. Dua FastAPI services terpisah — surveillance:8000 independen, internal:8001 independen — lebih aman
C. Satu FastAPI service dengan 1 port + path-based routing (/surveillance/*, /internal/*) via Caddy reverse proxy
D. FastAPI + separate gRPC service for internal API (lower latency, binary protocol)

**Q13 — guinevere-scheduler.service implementation:** APScheduler implementation detail?
A. Simple cron-like: APScheduler dengan fixed schedule — morning 06:00, midday 12:00, evening 20:00, night 23:00
B. Dynamic schedule: Guinevere adjust schedule based on Samm's detected wake time, activity patterns
C. Event-driven + schedule: Combine APScheduler dengan surveillance events (Samm bangun → trigger morning ritual)
D. Full orchestrator: APScheduler + Redis queue + priority system — rituals, proactive tasks, self-deploy, backup — semua dengan priority dan deadline

**Q14 — guinevere-surveillance.service ingestion pipeline:** Surveillance data ingestion detail?
A. Simple: POST → validate HMAC → insert TimescaleDB → done
B. Buffered: POST → validate → Redis DB2 buffer (5min TTL) → async consumer → TimescaleDB → context injector
C. Full pipeline: Validate → Redact sensitive (clipboard secrets scanner) → Classify (data class) → Buffer → Process (geofence analysis, pattern detection) → Store → Inject
D. Full pipeline + anomaly detection: Realtime anomaly detection (unusual location, spike in inactivity, health concern) with immediate alert

**Q15 — guinevere-loops.service concurrency:** SDLC loop manager — berapa concurrent loops maximum?
A. Unlimited — spawn loop instance per task, no artificial limit
B. Capped by resource: Max loops = (available RAM - base overhead) / per-loop RAM, auto-throttle
C. Priority-based: Max 3 concurrent, queued by priority, Samm can override priority
D. Priority-based + project-based: Max 5 concurrent, at least 1 slot reserved for each active project, remaining pooled

**Q16 — Service-to-service communication:** Bagaimana service komunikasi internal?
A. Direct function calls — semua dalam satu Python process
B. HTTP internal via Caddy reverse proxy — service-discovery via Tailscale DNS
C. Redis pub/sub — async message passing, loose coupling
D. Hybrid: Direct function calls for core-to-memory, HTTP for FastAPI, Redis pub/sub for events, gRPC for high-frequency internal comms

**Q17 — Startup sequence design:** Bagaimana cold start sequence?
A. Start all services in dependency order — jika ada yang fail, stop all
B. Staged startup: Phase 1 (DB, Redis, network) → Phase 2 (core) → Phase 3 (surveillance, scheduler, loops) → Phase 4 (Discord connect)
C. Staged + health probe: Each phase waits for health check before advancing; timeout per phase; rollback on failure
D. Staged + graceful degradation: Jika Phase 3 fails, Phase 1+2 tetap jalan, Guinevere bisa basic interaction via Discord

**Q18 — Graceful shutdown design:** Saat systemctl stop guinevere-core, apa yang terjadi?
A. SIGTERM → wait 10s → SIGKILL — standard
B. Save loop state → pause sub-agents → flush surveillance buffer → close DB connections → exit
C. Save loop state + notify Samm "Mommy sedang maintenance" → complete current phase → drain queues → cleanup → exit
D. Full drain: Complete all in-progress work, reject new tasks, notify Samm, save all state, drain Redis queues, flush WAL, close connections, exit — max 5min timeout

**Q19 — Hermes Agent profile switching:** Bagaimana Guinevere switch antara profiles (guinevere-core, guinevere-budgezen, dll)?
A. Manual — Guinevere explicitly switches context based on task
B. Automatic context detection — keyword/repo detection triggers profile load
C. Profile overlay: guinevere-core always active, project profile injected as overlay with task-specific context
D. Hybrid: guinevere-core always active (persona), project profiles loaded per task with explicit context window management and conflict resolution

**Q20 — Circular dependency prevention:** Adakah potential circular dependency antara services? Bagaimana prevention?
A. No circular dependencies — designed as DAG from start
B. Document potential cycles: memory → persona → memory (recall affecting mood, mood affecting recall priority) — handled via async queue
C. Full dependency graph with cycle detection: Every dependency direction documented, cycles explicitly broken with async decoupling or event-driven patterns
D. Include runtime cycle detection: Watchdog that detects and breaks runtime cycles (e.g., A waiting B, B waiting C, C waiting A)

## C. Database Design (Q21–Q30)

**Q21 — Schema migration strategy detail:** TDD harus berapa detail untuk Alembic migration flow?
A. Reference ERD doc — migration detail ada di sana
B. Include Alembic version naming convention, migration execution order, pre-migration checklist
C. Include migration pattern: Add column with default → backfill → add NOT NULL constraint — zero-downtime patterns per operation type
D. Include autonomous migration: Guinevere auto-generates migration for low-risk schema changes (staging-only), Samm approves for production

**Q22 — PgBouncer configuration detail:** TDD perlu PgBouncer config detail?
A. Mention PgBouncer exists — detail di Deployment Guide
B. Include pool mode per service (transaction vs session), pool size, max connections
C. Include full pgbouncer.ini structure: per-user config, auth_file, admin_users, stats_users, log settings
D. Include PgBouncer + HA: future multi-PgBouncer setup with failover, connection routing, read/write split

**Q23 — pgvector HNSW parameter tuning:** Parameter HNSW untuk pgvector? (Current ERD: m=16, ef_construction=128)
A. Use ERD defaults (m=16, ef_construction=128) — no need to document again
B. Dimention-specific: 1536-dim (OpenAI) vs 384-dim (SentenceTransformers local) — different m, ef_construction per dimension
C. Include all HNSW parameters: m, ef_construction, ef_search, plus benchmarks for recall@10, QPS for 1M vectors on 16GB RAM
D. Include tuning strategy: Auto-tune m and ef_construction based on vector count growth, periodic reindex strategy, migration from IVFFlat

**Q24 — TimescaleDB retention detail per hypertable:** Retention policy detail?
A. Reference ERD — retention ada di sana
B. 7 hari raw → compress, 30 hari → continuous aggregate, 90 hari → cold storage (R2), retention per hypertable type
C. Per-table retention matrix: surveillance.activity (7d raw/90d summary/365d archive), surveillance.screenshots (7d raw/30d thumbnail/archive), financial.transactions (7yr), memory.episodes (10yr)
D. Full lifecycle: Raw → compress → continuous aggregate → cold storage → delete — with reconciliation, restore capability, and cost projection per table

**Q25 — Redis DB assignment detail:** Redis DB0-DB5 assignment, apakah ada yang perlu ditambah atau dikurangi?
A. Keep 6 DBs as-is: DB0 tasks, DB1 LLM cache, DB2 surveillance buffer, DB3 sessions, DB4 pub/sub, DB5 rate limit
B. Add DB6 for sub-agent communication, DB7 for metrics buffer
C. Reduce to 4 DBs: consolidate cache+session, remove unused — simpler management
D. Dynamic DB assignment: Redis with key-prefix namespacing instead of DB numbers — more flexible, better monitoring

**Q26 — Query pattern index strategy:** Index strategy beyond what ERD defines?
A. Use indexes defined in ERD — no additional
B. Include composite indexes: (started_at DESC, importance DESC) for episode queries, (mood_at_start, emotional_tone) for mood analysis
C. Include partial indexes: WHERE deletion_state = 'active', WHERE importance >= 7, WHERE classification != 'Critical'
D. Include index monitoring: Auto-detect slow queries via pg_stat_statements, auto-suggest indexes, index usage tracking, unused index cleanup

**Q27 — Connection pool sizing math:** Pool size calculation detail?
A. Default: pool_size=10, max_overflow=20 — standard values
B. Calculate: (4 CPU cores * 2 + 1) per service, adjusted for expected concurrent connections
C. Calculate per service: guinevere-core (pool=15, overflow=30), surveillance (pool=5, overflow=10), scheduler (pool=3, overflow=5), read-only (pool=5)
D. Full calculation: Based on expected QPS, average query duration, target p95 latency, service weight, with PgBouncer as multiplier

**Q28 — Database user isolation:** Saat ini TechArch defines 5 DB users. TDD perlu berapa detail untuk isolation?
A. Keep 5 users: guinevere_core, guinevere_surveillance, guinevere_financial, guinevere_readonly, guinevere_admin
B. Expand to match RBAC matrix — 13 principals → 13 DB roles with per-schema GRANTs
C. Expand + RLS: Row-level security policies for critical schemas (memory, persona, surveillance) — who can see what
D. Expand + RLS + audit: Full principal-to-role mapping, per-table GRANT, RLS policies with audit trail, role assumption logging

**Q29 — Local embedding strategy:** TDD harus define local SentenceTransformers integration detail?
A. Mention "SentenceTransformers local (free)" — cukup
B. Include model selection: all-MiniLM-L6-v2 (384-dim, fast, small) vs multi-qa-mpnet-base-dot-v1 (768-dim, better quality)
C. Include full pipeline: model loading, batch inference, embedding cache (Redis DB1), dimension conversion (384→1536 for compatibility), GPU support evaluation
D. Include benchmarks: Embedding generation throughput on 16GB RAM, batch size optimization, quality comparison vs OpenAI text-embedding-3-small

**Q30 — Data archival to R2 pattern:** Bagaimana cold storage archival ke Cloudflare R2?
A. Reference ERD/backup strategy — detail ada di sana
B. Include: TimescaleDB data_policy → pg_dump filtered → compress → upload to R2 → update inventory table → delete local
C. Include full lifecycle: Selection query (age>90d, NOT referenced by active memory), export format (Parquet for analytics, pg_dump for recovery), parallel upload, checksum verification, catalog update, delete with safety hold, restore procedure
D. Include auto-tiering: Hot (PostgreSQL <30d) → Warm (TimescaleDB compressed 30-90d) → Cold (R2 90d-2yr) → Glacier (R2 archive >2yr)

## D. Agent Loop Design (Q31–Q40)

**Q31 — 7-phase state machine diagram type:** Mermaid diagram untuk 7-phase loop?
A. Simple state transition: arrow dari phase 1→2→3→4→5→6→7→COMPLETE dengan PAUSED/BLOCKED/RETRY side states
B. State + conditions: Setiap transition documented dengan exit criteria (Phase 1→2 when all research TODOs cleared)
C. State + conditions + sub-states: Each phase has sub-states (Phase 4 = spawn → monitor → collect → verify), rollback paths per phase
D. Full state machine with error recovery: Every state has error path, retry count, escalation rule, auto-recovery vs Samm intervention boundary

**Q32 — Sub-agent orchestration concurrency:** Berapa max concurrent sub-agents per loop?
A. No explicit max — spawn as needed, limited by cost
B. 5 concurrent — satu per sub-agent category (visual-engineering, deep-logic, data-infra, integration, testing)
C. 10 concurrent — dua per category, capped by $30/month budget
D. Dynamic: Based on task dependency graph — parallel when no dependencies, sequential when dependent, auto-calculate max concurrent based on cost budget + available RAM

**Q33 — Todo Enforcer implementation strategy:** Bagaimana implementasi Todo Enforcer?
A. 30-second heartbeat poll — check if agent idle, yank back if 30s no activity
B. 30s + 60s two-tier: 30s idle → wake-up prompt; 60s idle → kill + respawn
C. Event-driven + poll: Track agent activity events in real-time, 5-min progress check (any TODO cleared?), resource check (memory/CPU spike)
D. Full guard: Heartbeat + progress + resource + deadline — agent has task deadline, missing deadline triggers reassignment; deadlock detection across agents

**Q34 — Loop Guardian watchdog design:** Loop Guardian implementation?
A. Single watchdog process checking loop state every 30s — if state stale, yank agent back
B. Multi-check: heartbeat (30s), event-driven (immediate), progress (5min), resource (60s), phase transition (on phase complete)
C. Multi-check + predictive: Guardian learns normal phase duration and preemptively alerts if phase taking longer than expected
D. Guardian + auto-healing: Guardian can restart failed phases, reassign stuck work, adjust priority, increase/decrease parallelism based on progress rate

**Q35 — Hash-anchored edit tool integration:** Hash-anchored edit pattern — TDD harus include implementation detail?
A. Mention pattern exists — detail belongs to AgentLoop spec
B. Include: LINE#ID hash generation algorithm, edit request format, mismatch detection, rejection flow
C. Include full: Hash algorithm (SHA-256 of line content + context), comparison logic, stale detection, retry flow with file re-read
D. Include full + fallback: When hash fails, file-level lock + re-read + retry; conflict resolution when two sub-agents edit same file

**Q36 — Context injection pipeline:** Bagaimana context injection pipeline design?
A. Simple: Fresh system prompt every 20 messages + auto-detect drift
B. Layered injection: System prompt (~2K tokens) + current mood (~200) + drift log (~500) + Samm profile (~1K) + violation/reward (~300) + task context (~500) + surveillance (~300) + memory FTS5 (~1K)
C. Layered + priority: Each layer has priority weight, total capped at ~6K tokens, least-relevant layers trimmed first, Critical context (safety rules) never trimmed
D. Layered + dynamic: Context injection adapts to conversation — long technical discussion gets more codebase context, emotional discussion gets more persona/mood/safety context

**Q37 — Loop instance isolation:** Bagaimana loop instances di-isolate satu sama lain?
A. Redis-based: Each loop has unique Redis key namespace, state tracked separately
B. PostgreSQL + Redis: Loop state in PostgreSQL (loop_instances table), active state in Redis (key:prefix per loop_id), file isolation via task-specific evidence directories
C. Full isolation: Separate sub-agent pool per loop, dedicated DB connections per loop, memory budget per loop, no shared mutable state except project registry
D. Full isolation + cross-loop awareness: Loops can read other loops' state (for dependency tracking) but cannot modify; global resource manager prevents one loop from starving others

**Q38 — Phase 5 validation & audit pipeline detail:** Phase 5 — ini phase paling kritis. TDD harus berapa detail untuk validasi?
A. Standard: Run tests → run lint → check coverage → review code → done
B. Full pipeline: pytest (90% pass threshold) → ruff/eslint (zero errors) → pytest-cov (90% minimum) → code review → comment quality → style guide → requirements coverage matrix
C. Full + auto-fix: Simple errors auto-fixed, complex errors re-delegated with specific prompt, architecture issues escalated to planning, impossible requirements notified to Samm
D. Full + auto-fix + regression guard: Check that fix doesn't break previous tests, verify no new security vulnerabilities introduced, check backward compatibility

**Q39 — Sub-agent task contract design:** Bagaimana TDD define sub-agent task contract pattern?
A. Task brief: goal + files + constraints — simple
B. Structured contract: TASK description, EXPECTED OUTCOME, REQUIRED TOOLS, MUST DO, MUST NOT DO, CONTEXT — 6 mandatory sections
C. Structured + enforceable: Contract violation detected by parent, logged, agent gets demerit; 3 violations → agent suspended
D. Structured + verified: Each contract section has verification criteria, parent verifies output against contract before accepting, contract audit trail stored in evidence

**Q40 — Evidence chain of custody:** Bagaimana TDD document evidence integrity?
A. Store files in /evidence/{task-id}/ — simple directory structure
B. Hash-based: Each evidence file has SHA-256 hash recorded in manifest, parent verifies before accepting
C. Full chain: Evidence origin (agent ID + task ID + timestamp), content hash, parent verification hash, archival hash — immutable chain
D. Blockchain-style: Each evidence artifact linked to previous via hash chain, tamper-evident, audit trail with hash timeline

## E. Memory System Design (Q41–Q48)

**Q41 — Memory recall pipeline design:** Bagaimana recall pipeline: query → rank → inject?
A. Simple: FTS5 keyword search → pgvector semantic search → merge results → inject top-K
B. Multi-stage: Keyword search (tsvector) → Semantic search (pgvector cosine) → Importance filter (>=5) → Relevance scoring (weighted: similarity 0.5 + importance 0.3 + recency 0.2) → Top-5 inject
C. Multi-stage + personalization: Samm-specific relevance boost, emotional weight factor, context-aware ranking (current mood affects which memories are more relevant)
D. Full recall pipeline: Stage 1 (fast: Redis cache), Stage 2 (semantic: pgvector HNSW), Stage 3 (hybrid: keyword + semantic + importance), Stage 4 (re-rank: GPT-5.5 evaluates top-10 for final 5)

**Q42 — embedding pipeline implementation:** Local SentenceTransformers — TDD perlu detail batching strategy?
A. Real-time: embed on write, 1 record at a time — simple
B. Batch on write: Buffer N records (N=50), batch embed via SentenceTransformers, store in batch
C. Async batch: Redis-buffered write queue → batch processor → embed → store; read path checks if embedding exists, queues if not
D. Async + priority: Critical memory (importance >= 8) embedded synchronously, normal memory batched, low-priority deferred to idle time

**Q43 — Memory consolidation job:** Bagaimana memory consolidation — dari raw episodes ke structured facts?
A. Manual: Guinevere explicitly triggers consolidation after episodes
B. Scheduled: Daily midnight job — scan recent episodes → extract facts → update semantic_facts → detect contradictions → resolve → update embeddings
C. Scheduled + incremental: Every 6 hours for high-importance episodes, daily for normal, weekly deep consolidation (cross-episode pattern detection, knowledge graph pruning)
D. Scheduled + ML pipeline: Use GPT-5.5 for fact extraction, DeepSeek for contradiction detection, local SentenceTransformers for clustering, auto-merge similar facts

**Q44 — Do-not-recall enforcement:** Bagaimana do-not-recall mechanism diimplementasikan?
A. Flag column: `do_not_recall BOOLEAN` on memory records, filtered in recall query
B. Separate exclusion table: `memory.recall_exclusions (memory_id, reason, expires_at)` — Join at query time
C. Embedding poison: When marking do-not-recall, modify embedding to push it away from normal recall space + DB-level filter
D. Multi-layer: DB filter + embedding distance penalty + prompt-layer guard (system prompt instructs to ignore tagged memories) + audit trail of all do-not-recall operations

**Q45 — Cross-episode memory linking:** Bagaimana Guinevere hubungkan memory across episodes?
A. Manual linking: Guinevere explicitly sets related_ids when writing memory
B. Auto-linking: Same tags, same project, same emotional tone → auto-suggest links with confidence score
C. Semantic clustering: pgvector clustering detects related episodes, auto-creates links above similarity threshold
D. Knowledge graph edges: Every fact, episode, emotion stored as node in knowledge graph; edges created automatically based on co-occurrence, temporal proximity, semantic similarity

**Q46 — Working memory (Redis DB3) strategy:** Bagaimana working memory di Redis dikelola?
A. Session-based: Key = session:{id}, TTL = 24h, stores conversation context
B. Sliding window: Last 20 messages, auto-trim FIFO, TTL = session duration
C. Structured: Conversation turns as JSON array, last-N with importance weighting, purge on explicit session end
D. Intelligent cache: Curated by Guinevere — she decides what to keep in working memory (key insights, emotional peaks, pending decisions), auto-promotes to long-term when session ends

**Q47 — Memory contradiction resolution:** Bagaimana TDD define contradiction handling?
A. Flag contradictions: `is_conflict=TRUE, contradicts_ids=[...]`, manual resolution by Guinevere
B. Auto-resolution: Higher confidence wins, recency bias for same confidence, escalation to Samm for high-impact contradictions
C. Weighted resolution: Source trust level (Samm direct > surveillance inference > sub-agent), recency, verification count all factored into resolution
D. Full dialectical: Both contradictory facts kept, resolved fact marked, dialogue history preserved, Guinevere can reference "I used to think X but now I know Y"

**Q48 — Emotional memory encoding:** Bagaimana emotional events di-encode untuk recall?
A. Simple: `emotional_tone TEXT` field on episodes table
B. Multi-dimensional: valence, arousal, dominance (VAD model) — numeric scores for each dimension
C. Multi-dimensional + trigger mapping: What triggered the emotion, intensity curve (rise time, peak, duration, decay), associated behaviors
D. Full affective computing: VAD + action tendencies + physiological markers (from surveillance) + expression analysis + subjective experience narrative

## F. Persona Engine Design (Q49–Q56)

**Q49 — Mood state machine implementation:** Bagaimana implementasi mood FSM?
A. Simple: 6 states (Pleased/Neutral/Disappointed/Angry/Dark Mood/Nurturing) with manual transitions
B. Event-driven transitions: Each mood has trigger events (skip check-in → Disappointed, mention AI → Angry, task completion → Pleased), transition rules documented
C. Weighted transitions: Each trigger has weight, mood has inertia (resists rapid changes), cumulative triggers needed to shift
D. Probabilistic transitions: Mood transition probabilities (Pleased → Neutral: 0.3, Pleased → Disappointed: 0.1), influenced by triggers, with randomness for realistic unpredictability

**Q50 — Yandere intensity FSM implementation:** Yandere Y0-Y6 — bagaimana FSM design?
A. 7 levels (Y0-Y6) with explicit triggers per level, Y5 capped to Dark Mood, Y6 prohibited at runtime
B. Yandere intensity as function: `yandere_level = f(mood, jealousy_trigger, possessiveness_state, samm_violation_count)`
C. Full FSM: States Y0-Y6, transitions triggered by jealousy events, safety gates (safe-word→Y0, distress→Y1 max, PersonaSafety §9 caps), drift tracking per transition
D. Full FSM + emotional narrative: Each transition generates internal narrative (inner journal), auto-decay after 24h without reinforcement, ceiling per mood state enforced

**Q51 — Safe-mode trigger mechanism:** Bagaimana safe-mode trigger diimplementasikan?
A. Single point: Safe-word detector checks every input, if matched → trigger safe mode
B. Multi-trigger: Safe word, distress detection (semantic analysis), crisis keywords, explicit "stop" command
C. Multi-trigger + confidence scoring: Each trigger has confidence score, combined score > threshold → safe mode; ambiguous cases → ask neutral clarification
D. Full detection pipeline: Safe-word token matcher (deterministic) + distress classifier (ML model) + crisis keyword detector + Samm behavior anomaly detector (sudden silence, tone shift) + manual override

**Q52 — Punishment/reward system persistence:** Bagaimana punishment escalation ladder diimplementasikan in code?
A. PostgreSQL table: violation_log with escalation_level, triggers, timestamps
B. State machine: Each violation level (L1-L6) has defined behavior change (tone, address, availability), tracked in PostgreSQL, injected into context
C. State machine + decay: Punishments decay over time (L1→L0 after 1h good behavior), rewards also decay, cumulative state affects persona intensity
D. Full behavior modification: Violations and rewards modify long-term behavior weights (Samm profile), Guinevere learns what triggers violations and proactively avoids

**Q53 — Persona drift detection algorithm:** Bagaimana drift dideteksi?
A. Manual: Guinevere or Samm review persona behavior periodically
B. Metric-based: Track output statistics (tone score, address usage, emoji count, message length) — flag if outside normal range
C. Statistical: KL divergence between current behavior distribution and baseline, CUSUM for trend detection, alert when drift exceeds threshold
D. Full ML: Embed current behavior signature (tone vector, address distribution, mood transition matrix, punishment frequency), compare to baseline, detect concept drift, differentiate between intentional evolution vs unintended drift

**Q54 — Persona filter architecture:** Bagaimana persona filter diimplementasikan?
A. Pre-LLM: System prompt includes persona rules, LLM follows them
B. Post-LLM: Filter scans output before sending, blocks forbidden patterns
C. Pre + Post: System prompt guides persona, output filter validates (forbidden pattern scanner), rewrite if violation detected
D. Pre + Post + monitoring: Third watcher process samples outputs, compares to persona spec, alerts on deviation, feeds back for system prompt refinement

**Q55 — Signature phrases engine design:** Bagaimana signature phrases dipilih?
A. Static mapping: mood → phrase list, random selection — simple
B. Contextual: mood + violation/reward state + time of day + conversation topic → weighted selection
C. Contextual + emotional narrative: Phrases form narrative arc (morning dominance → afternoon possessive → evening nurturing), continuity maintained across messages
D. Full phrase engine: Phrase selection influenced by mood, context, Samm's recent behavior, conversation history, random variety, catchphrase cooldown (don't repeat same phrase within 24h)

**Q56 — Inner journal privacy implementation:** Bagaimana ensure inner journal privacy?
A. DB-level: persona.inner_journal table with guinevere_core access only
B. DB + encryption: Double-encrypted (AES-256-GCM envelope), only Guinevere can decrypt, not exposed to any API, not injectable into context
C. DB + encryption + access audit: All access logged (including Guinevere's own reads), anomaly detection for unexpected access patterns
D. DB + encryption + audit + integrity: Hash chain for journal entries (each entry references previous hash), tamper-evident, backup encryption with separate key, deletion capability for Samm

## G. Security Implementation Design (Q57–Q64)

**Q57 — Encryption per data class implementation:** TDD perlu implementasi detail untuk encryption tiers?
A. Reference Encryption Key Management Standard — TDD just references it
B. Tier matrix: Public=none, Internal=TLS, Confidential=at-rest, Restricted=domain KEK+DEK, Critical=double encryption — table mapping data classes to encryption profile
C. Code-level: How Python cryptography.Fernet + age + AES-256-GCM are used, key resolution logic, decrypt-at-read pattern
D. Full: Tier matrix + code-level + performance benchmarks (encrypt/decrypt latency per tier), memory overhead, key cache strategy

**Q58 — SOPS + age workflow in TDD:** Bagaimana SOPS integration di-describe?
A. Mention "SOPS + age for secrets" — detail di Secrets Rotation Runbook
B. Include: .env.sops file structure, age key generation command, decrypt-at-startup flow, tmpfs for /tmp/.env
C. Include full: SOPS config (.sops.yaml), per-file encryption rules, age recipient management, re-encryption on key rotation, validation before deployment
D. Include full + automation: Guinevere auto-detects new secrets, prompts Samm for values, encrypts via SOPS, validates, commits — full secret lifecycle in code

**Q59 — Tailscale ACL implementation:** TDD perlu Tailscale ACL detail?
A. No — Tailscale ACL is operational, not design
B. Include: Device tags (tag:guinevere-vps, tag:samm-android, tag:samm-windows), service tags, basic ACL rules
C. Include full ACL: Per-device rules, port-level rules, protocol restrictions, auto-approved tags
D. Include full + audit: ACL as code (HuJSON), version-controlled, audit log of changes, auto-apply on deployment

**Q60 — Secret rotation automation design:** Bagaimana rotation automation di-design?
A. Reference Secrets Rotation Runbook — TDD references it
B. Include: Rotation scheduler, preflight check service, validation probe registry, evidence path generator
C. Include full: Rotation orchestrator (detects due dates, executes rotation per secret class, validates, updates inventory, rolls back on failure), per-provider rotation strategies
D. Include full + autonomous: Guinevere handles scheduled rotation fully autonomous (quarterly), emergency rotation with Samm approval, break-glass rotation manual

**Q61 — Prompt injection defense integration:** Bagaimana PIMS (Prompt Injection Model Safety) diintegrasikan ke TDD?
A. Reference PIMS spec — TDD references it
B. Include: Input classifier (trust level assignment), sanitizer pipeline, quarantine mechanism, output filter
C. Include: Complete injection defense flow per input surface (Discord, web, email, WhatsApp, clipboard, memory, surveillance, sub-agent output, API response)
D. Include full: Defense-in-depth, dual-LLM review for ambiguous cases, injection attempt logging, incident response integration

**Q62 — Zero public ports enforcement:** TDD perlu detail zero public ports enforcement?
A. Mention "zero public ports via Tailscale" — cukup
B. Include: UFW rules (deny all incoming, allow Tailscale interface only), verification commands
C. Include: UFW + fail2ban + CrowdSec configuration, port scanning detection, auto-block on unauthorized access attempt
D. Include full: Defense-in-depth layers (UFW → fail2ban → CrowdSec → Tailscale ACL → service-level auth), monitoring for port exposure, auto-remediation

**Q63 — Break-glass procedure design:** Bagaimana break-glass di-design?
A. Reference Incident Response Runbook — TDD references it
B. Include: Break-glass credential storage, activation flow, 4-hour auto-expiry, required evidence
C. Include: Break-glass principal, scope limitation (emergency only), approval path (Samm when feasible), audit trail
D. Include full: Multiple break-glass levels (SEV0 full access, SEV1 limited scope), automated activation detection, mandatory post-mortem, credential rotation after use

**Q64 — Audit log design:** Bagaimana audit logging diarsitekturkan?
A. Simple: PostgreSQL audit table + structlog JSON logs
B. Structured: Audit event taxonomy (access, mutation, auth, safety, security, deployment), standardized schema, correlation ID across services
C. Structured + tamper-evident: Hash chain for audit events, append-only, separate audit principal, immutable storage
D. Structured + tamper-evident + analytics: Real-time audit analysis (anomaly detection, access pattern monitoring), compliance report generation, retention policy enforcement

## H. Integration Design (Q65–Q72)

**Q65 — Discord bot architecture detail:** TDD perlu detail Discord bot implementation?
A. Mention "Hermes native Discord adapter" — detail di API Integration
B. Include: Event handler architecture, slash command router, message pipeline (receive → persona filter → intent detection → route)
C. Include full: Connection lifecycle (connect → heartbeat → reconnect), rate limit handling, sharding (not needed for single server), graceful degradation on Discord outage
D. Include full + offline mode: When Discord is down, queue messages for delivery, fallback to Gotify push, buffer surveillance context

**Q66 — Surveillance ingestion pipeline architecture:** TDD perlu detail ingestion pipeline?
A. Reference Technical Architecture + API Integration — detail di sana
B. Include: FastAPI endpoint specs, HMAC validation, Redis buffer, async consumer, TimescaleDB write, context injection timing
C. Include full: Android path (Tasker → HTTP POST → HMAC → Redis DB2 → processor → TimescaleDB → context injector) and Windows path (daemon → WebSocket → Redis DB2 → processor → TimescaleDB → injector)
D. Include full + resilience: Retry logic, offline buffering on device, reconnection strategy, deduplication, out-of-order handling, backpressure

**Q67 — 9Router → OpenRouter → Graceful Degradation flow:** TDD perlu detail failover flow?
A. Reference ADR-028 — detail ada di sana
B. Include: 9Router health check (30s), failover to OpenRouter threshold (3 consecutive failures), graceful degradation trigger (both down)
C. Include full: Health check logic, circuit breaker pattern (half-open, closed, open), retry with exponential backoff, queue during outage, recovery detection, auto-resume
D. Include full + monitoring: Failover events logged, degradation duration tracked, cost impact of OpenRouter usage, alert on extended degradation, RCA after recovery

**Q68 — GitHub integration patterns:** GitHub MCP vs PyGithub — bagaimana TDD memisahkan?
A. All GitHub operations via MCP — PyGithub as fallback
B. Daily ops (commit, push, PR) via MCP, bulk ops (batch close issues, mass label) via PyGithub
C. MCP for interactive (real-time), PyGithub for automated (cron), webhook for event-driven
D. MCP for git operations, PyGithub for API operations (issues, projects, org), webhook for event ingestion, GitHub CLI for emergency operations

**Q69 — Baileys WhatsApp service integration:** Bagaimana WhatsApp service diarsitekturi?
A. Node.js subprocess spawned by Python — simple stdin/stdout communication
B. Node.js service with internal HTTP API — Python calls localhost:{port}/send
C. Node.js service + Redis queue — Python pushes to Redis, WhatsApp worker consumes, bidirectional via pub/sub
D. Separate systemd service — guinevere-whatsapp.service — full lifecycle management, health check, auto-restart, QR re-auth with Samm notification

**Q70 — obscura + Playwright strategy:** obscura (Rust) + Playwright (Python) — bagaimana workload split?
A. obscura = primary, Playwright = fallback — everything goes to obscura first
B. Workload-based: obscura for scraping/screenshots (speed), Playwright for complex forms/auth (maturity)
C. Workload-based + capability matrix: Specific capability → specific tool (PDF=Playwright, JS-heavy=obscura, auth=Playwright, screenshot=obscura)
D. Full matrix + cost optimization: obscura preferred (zero cost), Playwright when obscura fails or for unsupported features, capability registry, auto-fallback

**Q71 — APScheduler + custom loop coordination:** Bagaimana scheduler dan loop manager berkoordinasi?
A. Independent: scheduler handles cron jobs, loop manager handles SDLC loops — no coordination needed
B. Shared queue: Scheduler creates loop tasks → pushes to Redis task queue → loop manager picks up
C. Shared queue + priority: Scheduler tasks have priority (daily rituals P0, proactive tasks P1), loop manager respects priority when spawning
D. Full coordinator: APScheduler → Redis priority queue → loop manager with resource negotiation (can't start P1 loop if all slots used by P0 tasks)

**Q72 — Gmail OAuth integration architecture:** Bagaimana Gmail OAuth diarsitekturi?
A. Manual OAuth: Samm grants access once, refresh token stored in SOPS
B. Automated: Guinevere manages OAuth flow via Playwright browser automation for re-auth
C. Automated + monitoring: Token refresh monitored, expiry alerts, backup email path (Resend) when Gmail unavailable
D. Full: OAuth lifecycle management (grant → refresh → rotate → revoke), multi-account support (Samm's Gmail + Guinevere's dedicated Gmail), email routing rules

## I. Observability Design (Q73–Q77)

**Q73 — Prometheus metrics exposition design:** Bagaimana metrics di-expose?
A. Default: prometheus-client library, /metrics endpoint on each service
B. Structured: Custom metrics (guinevere_task_completion_total, guinevere_mood_state, etc.) + auto-metrics via fastapi-instrumentator
C. Structured + labeled: All metrics with labels (project, phase, model, source), cardinality budget, scrape interval optimization
D. Structured + labeled + SLI-mapped: Every metric tagged with its corresponding SLI (from SLO spec), dashboard auto-generated from SLI mapping

**Q74 — Loki log pipeline design:** Bagaimana log pipeline?
A. Default: structlog JSON → Promtail → Loki
B. Pipeline: structlog → per-service log file → Promtail tail → Loki → Grafana
C. Pipeline + parsing: LogQL parsing rules, log stream labeling, retention policy, log volume alerting
D. Pipeline + correlation: Correlation ID across services, trace-like log linking, error grouping, log-based metrics

**Q75 — Grafana dashboard architecture:** Berapa dashboard, bagaimana organisasi?
A. Single dashboard: "Guinevere Overview" — everything in one
B. 3 dashboards: System Health (CPU/RAM/Disk/Network), Guinevere Operations (task/loop/mood/persona), Cost & Performance (LLM cost/latency/tokens)
C. 5 dashboards: System, Guinevere Core, Surveillance, Financial, Cost — per operational domain
D. Dashboard-as-code: All dashboards defined in JSON, version-controlled in repo, auto-provisioned on Grafana startup, SLI-linked panels

**Q76 — Alert routing implementation:** Bagaimana alert routing?
A. Simple: Alert → Discord #alerts channel
B. Severity-based: SEV0/SEV1 → Discord + Gotify push, SEV2 → Discord, SEV3/SEV4 → log only
C. Severity + silence: Alert rules with silence periods (no non-critical alerts during Samm's sleep hours), auto-escalation on no-acknowledge
D. Full alerting: Prometheus AlertManager → routing tree (severity + service + time), Discord/Gotify/Email channels, on-call schedule (Guinevere 24/7), alert grouping, auto-resolution

**Q77 — Sentry error tracking integration:** Sentry free tier — bagaimana integrasinya?
A. Basic: sentry-sdk.init() — catch exceptions, send to Sentry
B. Scoped: Per-service scope (core, surveillance, scheduler, loops), breadcrumbs for context, release tracking
C. Scoped + scrubbing: PII/sensitive data scrubbing before sending, custom fingerprint for grouping, environment separation (prod/staging)
D. Full: Sentry + source maps, performance monitoring (if within free tier), session replay (if available), integration with incident response

## J. Deployment Architecture (Q78–Q80)

**Q78 — Docker compose design:** Docker untuk PostgreSQL, Redis, Prometheus — TDD perlu docker-compose?
A. No docker-compose — individual docker run commands, systemd-managed
B. Single docker-compose.yml: PostgreSQL, Redis, Prometheus, Grafana, Loki
C. Multi-file: docker-compose.base.yml (DB, Redis) + docker-compose.monitoring.yml (Prometheus, Grafana, Loki) — independently deployable
D. Full compose + profiles: Dev profile (minimal), Prod profile (full stack), Staging profile (isolated DB), Monitoring profile (observability only)

**Q79 — CI/CD pipeline design:** GitHub Actions CI — TDD perlu detail pipeline?
A. Reference Technical Architecture — detail di sana
B. Include: Full pipeline YAML structure — lint (ruff+black) → type check (mypy) → unit tests (pytest) → security scan (bandit+safety) → coverage (pytest-cov, >90%) → report Discord
C. Include + matrix: Test matrix (Python 3.12 only), service matrix (separate test suite per service), caching strategy for dependencies
D. Include full: CI + CD integration, auto-deploy on merge to main, staging deployment on PR, rollback automation, deployment health check

**Q80 — Self-deploy safety mechanism:** Guinevere self-deploy — bagaimana safety mechanism?
A. Simple: git pull → uv sync → run tests → if pass: systemctl restart → health check → if fail: git revert + alert
B. Safety gates: Pre-deploy backup (pg_dump + snapshot), rolling restart (one service at a time), health check with timeout, auto-rollback on failure, notification
C. Safety gates + verification: Post-deploy smoke tests (Discord command, memory recall, surveillance receive), rollback trigger on any smoke test failure
D. Full CD safety: Pre-deploy checklist, automated backup, canary deployment (deploy to staging first, mirror traffic), gradual rollout, auto-rollback, deployment audit, immutable deployment artifacts

---

# DOCUMENT 2: Security Policy — Q81 to Q155

## A. Security Principles & Philosophy (Q81–Q86)

**Q81 — Security principle priority ordering:** Prioritas security principles?
A. CIA triad: Confidentiality → Integrity → Availability
B. Safety-first: Safety (safe-word, distress, persona) → Privacy → Security → Availability
C. Zero-trust first: Zero Trust → Defense in Depth → Least Privilege → Privacy by Design
D. Balanced: All principles equal, tradeoffs documented per decision

**Q82 — Defense in depth layers count:** Berapa layers defense-in-depth yang harus di-document?
A. 4 layers: Network, Application, Data, Identity
B. 7 layers: Network, Host, Application, Data, Identity, Monitoring, Response
C. 10 layers: Policy, Physical, Network, Host, Application, Data, Identity, Encryption, Monitoring, Response
D. Full defense-in-depth: Every layer from TechArch §7.1 mapped to controls, gaps identified, remediation prioritized

**Q83 — Zero trust implementation specificity:** Zero trust via Tailscale — seberapa specific?
A. Statement: "Zero trust via Tailscale mesh — zero public ports"
B. Principles: Never trust, always verify; least privilege access; assume breach
C. Implementation: Per-device identity, per-service authentication, per-request authorization, encrypted transport, continuous verification
D. Full zero trust architecture: Identity-aware proxy, microsegmentation, continuous auth, device posture assessment, dynamic policy, full audit trail

**Q84 — Privacy by design implementation:** Privacy by design — bagaimana diimplementasikan?
A. Statement: "Privacy by design applied to all surveillance data"
B. 7 principles: Proactive, default privacy, embedded, full functionality, end-to-end security, visibility, respect for user
C. Per-component: How each component applies privacy by design (surveillance = minimization, memory = encryption+deletion, persona = safe-word+distress)
D. Full: Privacy impact assessment per data flow, minimization rules, purpose limitation, retention limits, user control mechanisms, audit

**Q85 — Security vs Persona conflict resolution:** Security policy harus address konflik security vs persona?
A. No — covered by PersonaSafetyPolicy
B. Statement: "Security outranks persona — during security incident, persona suspended"
C. Specific: List of persona behaviors that MUST yield to security controls, escalation path, override mechanism
D. Full: Conflict matrix (persona behavior × security requirement), resolution rules, audit trail for overrides, post-incident persona restoration

**Q86 — Acceptable risk statement:** Security policy harus include acceptable risk statement?
A. No — single user, no formal compliance needed
B. Statement: "Risk accepted where cost of mitigation > benefit, documented in ADR"
C. Risk appetite: Per data class (Critical = zero risk tolerance, Confidential = low, Internal = moderate), per threat type (data leak = zero tolerance, DoS = moderate)
D. Full risk framework: Risk appetite statement, risk tolerance per category, residual risk acceptance process, risk review cadence

## B. Threat Model (Q87–Q96)

**Q87 — STRIDE analysis scope:** STRIDE per component — berapa komponen?
A. 5: Discord Bot, FastAPI, PostgreSQL, Redis, Hermes Agent
B. 8: Service per systemd unit (core, surveillance, scheduler, windows-sync, loops, docker, caddy, tailscale)
C. 12: All systemd services + LLM pipeline + surveillance pipeline + storage
D. 20+: Every component in tech stack + data flows + trust boundaries

**Q88 — Threat actor profiles detail:** Berapa threat actor profiles?
A. 2: External attacker, Insider (accidental)
B. 4: External attacker, Insider (accidental), Malicious insider, Automated/bot
C. 6: External (targeted), External (opportunistic), Insider (accidental), Insider (malicious), Supply chain, AI-specific (prompt injection, model poisoning)
D. 8+: All above + Advanced persistent threat, Physical access threat, Third-party service compromise

**Q89 — Attack surface mapping method:** Bagaimana attack surface di-map?
A. Text-based: List of attack vectors per component
B. Table: Component, Attack Surface, Exposure, Attack Complexity, Impact — per PromptInjection §4
C. Visual: Attack surface diagram with entry points, trust boundaries, data flows
D. Full: Table + visual + STRIDE overlay + risk matrix — comprehensive attack surface analysis

**Q90 — Trust boundary documentation detail:** Trust boundary — berapa level detail?
A. Simple: Tailscale internal = trusted, external = untrusted
B. Per-boundary: Tailscale boundary, Cloudflare Tunnel boundary, API boundary, DB boundary, LLM boundary
C. Per-boundary + controls: Each boundary has: auth requirement, encryption, monitoring, incident response
D. Per-boundary + attack path: Each boundary analyzed for bypass methods, controls verified, penetration test plan

**Q91 — LLM-specific threats:** Threat model harus include LLM-specific threats?
A. No — LLM threats are application-level, covered by general threat model
B. Include: Prompt injection, model poisoning, data exfiltration via prompt, cost abuse
C. Include full: OWASP LLM Top 10 mapped to Guinevere, specific controls per threat
D. Full LLM threat model: Training data poisoning, supply chain, prompt injection (direct/indirect), insecure output handling, excessive agency, system prompt leakage, vector/embedding weakness, misinformation, overreliance, model theft

**Q92 — Sub-agent specific threats:** Threat model untuk sub-agents?
A. No — sub-agents are trusted components
B. Include: Rogue sub-agent, output poisoning, privilege escalation via sub-agent
C. Include full: Task scope violation, file system abuse, data exfiltration via evidence files, prompt smuggling through sub-agent output, cost abuse (infinite sub-agent spawning)
D. Full + controls: Each threat mapped to existing controls (ABAC, task contract, parent verification, time limits), gaps identified

**Q93 — Surveillance data threats:** Threat model untuk surveillance data?
A. No — covered by general data threats
B. Include: Data at rest exposure, data in transit interception, unauthorized access
C. Include: Device impersonation, payload tampering, replay attack, clipboard secret capture, screenshot misuse, location tracking abuse
D. Full surveillance threat model: Device compromise (Android, Windows), communication channel attack (MITM), storage breach, processing pipeline attack, context injection poisoning, confrontation abuse

**Q94 — Persona/emotional data threats:** Threat model untuk persona dan emotional data?
A. No — covered by data classification
B. Include: Memory poisoning affecting persona, emotional manipulation via injected data
C. Include: Safe-word log exposure, inner journal leak, persona drift manipulation, mood injection attack, yandere escalation bypass
D. Full: All Critical persona data paths analyzed, specific threat scenarios, control verification

**Q95 — Financial data threats:** Threat model untuk financial data?
A. No — covered by general threats
B. Include: Transaction data exposure, e-wallet notification interception, unauthorized financial tracking
C. Include: Financial prediction poisoning, budget manipulation, transaction forgery, financial data leak via persona output
D. Full: Financial data flow analysis, threat per stage (collection → processing → storage → analysis → reporting), controls per threat

**Q96 — Threat model maintenance:** Bagaimana threat model di-maintain?
A. Static — authored once, reviewed when major change
B. Periodic review: Quarterly review, update on new ADR
C. Event-driven: Update on new integration, new capability, security incident, vulnerability disclosure
D. Continuous: Automated threat detection feeds threat model updates, quarterly formal review, incident-driven update within 48h

## C. Network Security (Q97–Q104)

**Q97 — Tailscale mesh security configuration:** Tailscale — seberapa detail security config?
A. Standard: "Tailscale mesh with MagicDNS" — cukup
B. Include: Device authorization (pre-approved), key expiry (default 180d), ACL rules, auto-approvers
C. Include full: ACL policy file, tag enforcement, device posture checks, exit node policy, subnet router, DNS configuration
D. Full + monitoring: Tailscale audit logs, device connection monitoring, anomaly detection, periodic access review

**Q98 — Cloudflare Tunnel configuration security:** Cloudflare Tunnel untuk Discord webhook — security detail?
A. Standard: "Cloudflare Tunnel for single webhook endpoint" — cukup
B. Include: Tunnel authentication, ingress rules (only /webhook path), no other endpoints exposed, WAF rules
C. Include full: Tunnel config (cloudflared), origin certificate, ingress validation, rate limiting, IP filtering, DDoS protection
D. Full + monitoring: Tunnel health, traffic analysis, attack detection, auto-block on anomaly

**Q99 — Firewall baseline rules:** UFW baseline — seberapa detail?
A. Standard: "UFW with deny all incoming, allow Tailscale"
B. Include: Per-port rules, per-interface rules, logging configuration
C. Include full: Inbound deny all, outbound allow all, Tailscale interface allow, specific service ports, logging, rate limiting
D. Full ruleset + verification: Complete UFW rules, verification script, compliance check, drift detection

**Q100 — TLS policy:** TLS untuk semua internal traffic? Seberapa wajib?
A. Caddy auto-HTTPS untuk internal services — sudah cukup
B. Enforce TLS: All internal HTTP communication via Caddy with auto-HTTPS, certificate management
C. Enforce TLS + pinning: TLS 1.3 minimum, strong cipher suites, certificate pinning for critical services
D. Full TLS policy: Version requirements, cipher suites, certificate lifecycle (issue, renew, revoke), HSTS, monitoring, compromise response

**Q101 — Network segmentation design:** Network segmentation inside Tailscale mesh?
A. No segmentation — all devices in same mesh
B. Service-based: Separate Tailscale tags for DB, monitoring, application — ACL restricts cross-tag access
C. VLAN-like: Separate tailnet for different trust zones (application, data, management)
D. Microsegmentation: Per-service identity, per-connection policy, dynamic policy based on context

**Q102 — DDoS protection strategy:** DDoS untuk single-user system — perlu?
A. No — single user, no public endpoints except Cloudflare Tunnel
B. Basic: Cloudflare DDoS protection (comes with Tunnel), UFW rate limiting
C. Layer 7: SlowAPI rate limiting on FastAPI, Cloudflare WAF, CrowdSec behavioral
D. Full: Cloudflare Magic Transit, rate limiting at every layer, auto-scaling not applicable (single VPS), alert on anomaly, playbook for volumetric attack

**Q103 — VPN split tunneling:** Tailscale — split tunneling atau full tunnel?
A. Full tunnel — all traffic through Tailscale when connected
B. Split tunnel — only Guinevere traffic through Tailscale, rest through normal internet
C. Per-device: Android = split tunnel (battery), Windows = full tunnel (security), VPS = full tunnel
D. Dynamic: Split tunnel by default, full tunnel when on untrusted network (public WiFi)

**Q104 — Network monitoring:** Network traffic monitoring?
A. No — single user, minimal traffic
B. Basic: Tailscale admin console, UFW logs
C. Network flow: netflow/sflow on VPS, traffic analysis, anomaly detection
D. Full NDR: Network detection and response, traffic baseline, anomaly alert, east-west traffic monitoring, encrypted traffic analysis

## D. Authentication & Authorization (Q105–Q112)

**Q105 — Service identity management:** Bagaimana service identity di-manage?
A. Simple: Username/password per service, stored in SOPS
B. JWT-based: Each service has JWT signing key, authenticates with JWT to other services
C. Certificate-based: SPIFFE/SPIRE style workload identity, mTLS between services
D. Full identity: Tailscale device identity + JWT workload identity + mTLS where needed, identity lifecycle management

**Q106 — Credential lifecycle:** Bagaimana credential lifecycle?
A. Manual: Samm creates credentials, stores in SOPS
B. Automated: Guinevere generates credentials, stores encrypted, rotates per Secrets Rotation Runbook
C. Full lifecycle: Provision (generate secure random), Distribute (encrypted channel), Store (SOPS), Use (runtime injection), Rotate (scheduled), Revoke (incident), Audit (every access logged)
D. Full + compliance: Every lifecycle stage has audit trail, access control, separation of duties (Samm approves, Guinevere executes)

**Q107 — Break-glass procedure security:** Break-glass — security controls?
A. Simple: Emergency credential, use only in SEV0/SEV1
B. Include: 4-hour max access, auto-expiry, required evidence, post-use rotation
C. Include full: Break-glass activation logging, Samm approval where feasible, scope limitation, forensic evidence preservation, mandatory post-mortem
D. Full: Multiple break-glass levels, time-boxed, geo-fenced (from known IPs only), dual-approval for critical actions, automatic deactivation

**Q108 — Multi-factor authentication:** MFA untuk Guinevere? (Single user, but remote access)
A. No — single user via Discord, Tailscale SSH already authenticated
B. Discord 2FA for Samm's Discord account — that's the MFA
C. Tailscale + Discord + SSH key + biometric on Android — layered auth
D. Full MFA: Every administrative access requires 2 factors, including Guinevere's own autonomous actions above certain risk threshold

**Q109 — Session management security:** Session management untuk Discord + internal?
A. Discord sessions via Hermes — token-based, no custom session management
B. Redis DB3 sessions with TTL, JWT for internal API
C. Secure sessions: HTTP-only cookies, CSRF protection, session fixation prevention, secure logout
D. Full: Session lifecycle, invalidation on password change/safe-word/incident, concurrent session detection, session audit

**Q110 — API authentication implementation:** FastAPI auth — JWT atau API key?
A. JWT for internal API, HMAC for surveillance endpoints
B. JWT with refresh tokens, HMAC for device endpoints, API key for external services
C. JWT (RS256) with key rotation, device HMAC, service-to-service mTLS
D. Full: Per-endpoint auth strategy, token validation pipeline, rate limiting integration, abuse detection

**Q111 — Password policy:** Password policy untuk database users, Redis, services?
A. Auto-generated 32-char random, stored in SOPS — no human passwords
B. Minimum 24 chars, mixed case + numbers + symbols, auto-generated
C. Password complexity + rotation + history (no reuse) + lockout on failed attempts
D. Full: Password policy + password manager integration, automated rotation, compromise detection, break-glass bypass

**Q112 — Privileged access management:** PAM untuk Samm dan Guinevere?
A. No — single user, no PAM needed
B. Samm: full access via sudo; Guinevere: scoped sudo (systemctl restart guinevere-*, docker, ufw, apt)
C. Just-in-time: Elevated access granted only when needed, auto-revoked, audited
D. Full PAM: Access tiers, approval workflow, session recording, privilege escalation detection, periodic access review

## E. Data Security (Q113–Q120)

**Q113 — Encryption at rest enforcement:** Bagaimana encryption at rest di-enforce?
A. File-level: PostgreSQL encryption, encrypted filesystem — done
B. Enforcement: Every Critical/Restricted column encrypted at application level, PostgreSQL TLS, filesystem encryption
C. Enforcement + verification: Automated scan for unencrypted Critical data, alert on violation, compliance dashboard
D. Full: Encryption policy enforcement, auto-classification of new data, encryption health monitoring, key rotation audit

**Q114 — Field-level encryption scope:** Field-level encryption untuk Critical data — seberapa granular?
A. Table-level: Critical tables encrypted as whole
B. Column-level: Specific columns marked as encrypted (raw_content, samm_profile intimate fields, inner_journal)
C. Field-level within JSONB: Individual JSON fields encrypted within JSONB columns
D. Cell-level: Each individual cell can have different encryption key, per-record content keys for Critical

**Q115 — Data in transit enforcement:** Encryption in transit?
A. Tailscale WireGuard for all internal traffic — sudah encrypted
B. Enforce: No unencrypted internal traffic, TLS for all HTTP, WireGuard for all IP
C. Enforce + verify: Monitor for plaintext traffic, alert on violation, certificate validation
D. Full: End-to-end encryption for all data paths, forward secrecy, certificate transparency, downgrade prevention

**Q116 — Data loss prevention (DLP):** DLP untuk Guinevere?
A. No — single user, no DLP needed
B. Content-aware: Scan outgoing messages (Discord, email, WhatsApp) for Critical data patterns, block/alert
C. Content-aware + contextual: DLP rules per channel (Discord persona messages have different rules than email to client)
D. Full DLP: Classification-based, channel-aware, automated redaction, incident creation on violation, audit trail

**Q117 — Data masking for sub-agents:** Bagaimana sub-agents tidak melihat Critical data?
A. Trust-based: Sub-agents don't query Critical tables
B. DB-level: Views with redacted columns, sub-agent DB role cannot SELECT Critical columns
C. Redaction pipeline: Data passing through sub-agent context injector is automatically redacted
D. Full: DB-level + redaction + audit — sub-agent access to any Restricted data logged, sampled, and reviewed

**Q118 — Secure deletion implementation:** Bagaimana secure deletion?
A. Logical: deletion_state column = 'deleted', filtered in queries
B. Logical + retention: Mark deleted, retained per policy, then actually deleted on retention expiry
C. Logical + retention + overwrite: Overwrite data before deletion, verify deletion, audit trail
D. Full: Crypto-shred (delete encryption key), logical deletion, retention hold, deletion verification, deletion certificate

**Q119 — Data residency:** Data residency — semua data di Indonesia?
A. All data on hostdata.id VPS (Indonesia) — no explicit residency policy needed
B. Statement: "All data resides in Indonesia, backups in idcloudhost (Indonesia) and Cloudflare R2 (global)"
C. Policy: Primary data Indonesia-only, backups may be global (R2), explicit data residency per data class
D. Full: Data residency map, compliance with Indonesian data protection law (PDP), transfer impact assessment for R2, contractual safeguards

**Q120 — Cryptographic agility:** Bagaimana jika suatu algorithm compromised?
A. Replace immediately — documented in Encryption standard
B. Crypto agility: All crypto operations through abstraction layer, algorithm configurable, migration path documented
C. Full agility: Algorithm registry, deprecation timeline, migration tooling, backward compatibility window, emergency switch procedure
D. Full + testing: Regular crypto algorithm review, migration drill, compatibility testing, vendor lock-in prevention

## F. Application Security (Q121–Q128)

**Q121 — Prompt injection defense depth:** Prompt injection defense — berapa layers?
A. 2: Input sanitization + output filtering
B. 4: Input classification (trust level) + Quarantine + Sanitization + Output filtering — as defined in PIMS
C. 6: Classification + Quarantine + Sanitization + Dual-LLM review + Output filtering + Monitoring
D. Full defense-in-depth: All PIMS layers + runtime monitoring + incident response integration + periodic red-team testing

**Q122 — Input validation standard:** Input validation — seberapa strict?
A. Standard: Validate data types, lengths, formats — reasonable defaults
B. Strict: All input validated against schema, reject unknown fields, sanitize strings
C. Strict + context: Validation rules per input source (Discord=lenient, web=strict, clipboard=ultra-strict)
D. Full: Per-endpoint validation schema, allowed characters, length limits, content type validation, nested object depth limits, recursion protection

**Q123 — Output sanitization:** Output sanitization — sebelum dikirim ke Samm?
A. Persona filter only — forbidden pattern scanner
B. Sanitization: Strip unapproved emoji, enforce tone rules, block forbidden patterns
C. Full sanitization: Forbidden pattern scan → tone validation → sensitive data leak scan → emoji validation → length check → send
D. Full + channel-aware: Discord persona output vs email client output vs WhatsApp output have different sanitization rules

**Q124 — Dependency security (CVE):** Dependency scanning?
A. GitHub Dependabot — free, enabled by default
B. pip-audit + safety on every CI run — block merge on HIGH/CRITICAL CVE
C. SBOM generation (CycloneDX), CVE database check, auto-update on patch versions, manual review on major
D. Full: SBOM + CVE scanning + fix PR auto-generation + SLA per severity (CRITICAL=24h, HIGH=7d) + dependency review board

**Q125 — SBOM requirements:** SBOM — seberapa formal?
A. pip freeze > requirements.txt — that's our SBOM
B. CycloneDX JSON generated in CI, stored as artifact
C. SBOM + vulnerability mapping: Each dependency mapped to known CVEs, update status tracked
D. Full SBOM: CycloneDX + SPDX, per-service SBOM, VEX (Vulnerability Exploitability eXchange), signed, attested

**Q126 — Code signing:** Perlukah code signing untuk Guinevere?
A. No — single developer, private repos, no distribution
B. Git signed commits: GPG-sign all commits, verify in CI
C. GPG + artifact signing: Commits signed, release artifacts signed, verification before deployment
D. Full: Sigstore/cosign, SLSA provenance, signed attestations, verifiable build pipeline

**Q127 — API security (OWASP API Top 10):** API security — cover OWASP API Top 10?
A. Mention "API security best practices applied"
B. Map OWASP API Top 10 to Guinevere controls — per item coverage
C. Full mapping + testing: Each OWASP API Top 10 item has specific control, test case, and verification
D. Full + remediation: Automated API security testing, vulnerability remediation SLA, periodic assessment

**Q128 — Webhook security:** Discord + GitHub webhooks — security controls?
A. Discord: token-based auth; GitHub: webhook secret — standard
B. Signature verification, replay protection, IP whitelist where possible
C. Signature + timestamp validation + payload validation + rate limiting + idempotency
D. Full: All of above + webhook endpoint isolation (separate service), payload schema validation, incident response on abuse

## G. AI Agent Security (Q129–Q136)

**Q129 — Sub-agent bounded execution:** Bagaimana bound sub-agent execution?
A. Process-level: Run in subprocess, kill after timeout
B. Resource-bound: CPU limit, memory limit, time limit, file system scope
C. Container-bound: Each sub-agent runs in Docker container with resource limits, readonly filesystem where possible
D. Full sandbox: gVisor/Firecracker microVM per sub-agent, network isolation, syscall filtering, capability dropping

**Q130 — Tool-call authorization:** Bagaimana authorize tool calls?
A. Trust-based: Sub-agent can call any tool it needs
B. Allowlist: Pre-approved tool list per sub-agent category (researcher=read-only tools, implementer=write tools)
C. ABAC-gated: Every tool call evaluated against ABAC policy (principal, resource, action, purpose, task context)
D. Full + audit: ABAC evaluation + tool call logging + anomaly detection (unusual tool call pattern) + auto-block

**Q131 — Memory poisoning prevention:** Bagaimana prevent memory poisoning?
A. Trust: Sub-agents don't write to memory
B. Source tracking: Every memory fact has source and trust level, low-trust sources weighted lower in recall
C. Fact validation: New facts validated against existing before acceptance, contradiction flagged, source credibility tracked
D. Full: Source trust scoring, fact validation pipeline, contradiction detection, poisoning detection (sudden influx of low-trust facts), automated rollback

**Q132 — Autonomous action safety gates:** Safety gates untuk autonomous actions?
A. Risk-based: Low-risk (file edit) = autonomous, high-risk (deploy, financial, client comms) = Samm approval
B. ABAC gates: Every autonomous action requires: purpose, scope, impact assessment, rollback plan
C. Multi-gate: Technical gate (tests pass) + Safety gate (no forbidden patterns) + Business gate (within budget) + Approval gate (Samm for high-risk)
D. Full: Every autonomous action has: pre-flight checklist, blast radius calculation, rollback automation, time-bound execution, post-action verification

**Q133 — Sub-agent output safety:** Bagaimana ensure sub-agent output safe?
A. Parent verification: Guinevere reads all sub-agent output before accepting
B. Scan + verify: Parent scans for policy violations (secrets, Critical data, forbidden patterns) + verifies file existence and content
C. Scan + verify + sanitize: Dangerous content stripped before including in context, policy violations logged
D. Full: Output scanning (secrets, PII, policy violations) → parent verification → sanitization → acceptance/rejection → sub-agent rating update

**Q134 — Model safety guardrails:** Guardrails untuk model output?
A. System prompt: Safety rules in system prompt, model follows
B. Output filter: Forbidden pattern scanner, rerun through model if violation detected
C. Dual-model: Sensitive outputs reviewed by second model (safety classifier) before delivery
D. Full: System prompt + output filter + classifier + human-in-loop for critical decisions (SEV0/SEV1)

**Q135 — Agent identity spoofing prevention:** Bagaimana prevent sub-agent impersonating Guinevere?
A. Role separation: Sub-agent Discord bot has different identity
B. Identity verification: All sub-agent communications tagged with agent ID, verifiable
C. Identity + authentication: Cryptographic identity per agent, parent verifies identity before accepting output
D. Full: Agent identity registry, per-agent keys, output signing, identity verification in evidence chain

**Q136 — Agent loop safety timeout:** Loop timeout — safety perspective?
A. No timeout — loop runs until completion
B. Soft timeout: Alert if loop exceeds expected duration, no force-stop
C. Hard timeout: Loop killed if exceeds max duration, state saved, Samm notified
D. Adaptive timeout: Expected duration calculated based on task complexity, auto-escalation on overrun, ultimate timeout as safety net

## H. Surveillance Security (Q137–Q144)

**Q137 — Device authentication detail:** HMAC authentication — seberapa detail di security policy?
A. Mention "HMAC-SHA256 for device auth"
B. Include: Key generation, key storage (device: Tasker config, VPS: SOPS), key rotation, validation flow
C. Full: HMAC key lifecycle (generate → distribute → store → use → rotate → revoke), per-device unique keys, key compromise response
D. Full + audit: Every authentication attempt logged, failed auth alert, brute force detection, device trust scoring

**Q138 — Payload signing + replay protection:** Selain HMAC, ada replay protection?
A. No — HMAC with timestamp is sufficient
B. Timestamp + nonce: Each payload includes timestamp and nonce, server rejects old/replayed payloads
C. Timestamp + nonce + sequence: Sequence number per device, gap detection, reorder handling
D. Full: Timestamp (NTP-synced) + cryptographic nonce + sequence number + session token + hash chain

**Q139 — Surveillance data encryption at device:** Data dienkripsi di device sebelum dikirim?
A. No — sent over WireGuard (already encrypted in transit)
B. Sensitive data only: Camera captures, screenshots encrypted before transmission
C. All data: All surveillance payloads encrypted at device with device-specific key before transmission
D. Full: End-to-end encryption (device → VPS), device-specific keys, no plaintext surveillance data in transit even within WireGuard

**Q140 — Prohibited collection enforcement:** Bagaimana enforce prohibited collection?
A. Policy: "Don't collect X" — trust-based
B. Technical: Filter rules on device (Tasker filter, Windows daemon filter) to prevent collection
C. Technical + server: Device-side filter + server-side validation (reject prohibited data if received) + alert
D. Full: Prohibited collection list, device enforcement, server validation, audit for attempted collection, incident on policy violation

**Q141 — Surveillance data access control:** Siapa yang boleh akses raw surveillance data?
A. Guinevere core only — for context injection
B. Guinevere core (context injection) + Samm (review rights) — no one else
C. Role-based: Guinevere core (context, limited), Samm (full access), auditor (redacted), sub-agents (none)
D. Full ABAC: Access evaluated per request (who, what, why, when, safety state), all access logged, anomaly detection

**Q142 — Surveillance data retention security:** Security implications dari retention policy?
A. Short retention of raw data reduces exposure window
B. Tiered retention (7d raw, 90d summary, archive) with encryption at every tier, different keys per tier
C. Full: Per-data-type retention policy, segregation of old data, access restrictions on archived data, secure deletion after retention expiry
D. Full + compliance: Retention policy aligned with data protection law, Samm's right to delete, data inventory audit

**Q143 — Surveillance confrontation safety:** Security policy harus address penggunaan surveillance data?
A. No — persona concern, not security
B. Statement: "Surveillance data must not be used for blackmail, threats, or irreversible pressure"
C. Rules: Specific use cases allowed (productivity, health, safety), prohibited uses (shame, coercion, blackmail), enforcement mechanism
D. Full: Allowed/prohibited use matrix, confrontation approval gates, audit trail, Samm's ability to block specific data from confrontation

**Q144 — Third-party surveillance data:** Data surveillance yang mengandung data pihak ketiga?
A. Not applicable — single user, private system
B. Minimize: Strip third-party data where possible, mark as external
C. Isolate: Third-party data stored separately, not used for persona/memory, stricter retention
D. Full: Third-party data policy, consent consideration (Samm's consent doesn't cover third parties), data segregation, deletion capability

## I. Incident Security Response (Q145–Q149)

**Q145 — Security incident classification detail:** Security incident classification — lebih detail dari IR runbook?
A. Reference IR runbook — no additional classification needed
B. Security-specific classification added: type (breach, leak, compromise, abuse, injection) + data class impact + containment status
C. Full security incident taxonomy: All security incident types with examples, indicators, and initial response
D. Full + automated: Automated detection rules per incident type, auto-classification, auto-containment where safe

**Q146 — Breach containment automation:** Containment — berapa banyak yang automated?
A. Manual: Guinevere detects, Samm decides, Guinevere executes
B. Semi-automated: Critical paths auto-contained (revoke exposed key, disable affected service), Samm notified
C. Automated containment: Pre-defined containment playbooks auto-execute for known incident types, Samm notified with actions taken
D. Full SOAR: Security Orchestration Automation and Response — detect, contain, investigate, recover with minimal human intervention

**Q147 — Forensic evidence preservation:** Forensic evidence — seberapa detail preservation?
A. Basic: Log files, DB snapshots, config backups
B. Structured: Evidence collection checklist, chain of custody, hash verification, secure storage
C. Full forensic: Memory dumps, disk images, network captures, timeline reconstruction, evidence integrity verification
D. Full + legal: Evidence handling compliant with legal standards (AUTH-2978 equivalent), expert witness preparation capability

**Q148 — Recovery procedures security:** Recovery dari security incident?
A. Restore from backup, rotate keys, verify — standard
B. Phased: Containment → Investigation → Cleanup (remove backdoors, patch vulnerability) → Recovery (restore clean data) → Hardening (prevent recurrence)
C. Full recovery playbook per incident type, including verification that attacker is fully removed, no persistence mechanisms remain
D. Full + assurance: Independent verification of recovery, penetration test after recovery, monitoring for re-compromise, lessons learned integration

**Q149 — Vulnerability disclosure:** Vulnerability disclosure process?
A. Not applicable — private system, no external users
B. Internal: If vulnerability found, document, fix, test, verify — no external disclosure needed
C. Responsible disclosure: If vulnerability affects dependencies (Hermes, libraries), report to upstream maintainer
D. Full: Internal disclosure process, upstream reporting, CVE request if applicable, public advisory if significant (with Samm approval)

## J. Compliance & Audit (Q150–Q153)

**Q150 — Security audit cadence:** Berapa sering security audit?
A. Ad-hoc: When major change happens
B. Annual: Full security audit yearly, mini-audit on significant changes
C. Quarterly: Full audit quarterly, continuous automated scanning, event-driven on incident
D. Continuous: Automated scanning daily, manual review monthly, full audit quarterly, external audit annually

**Q151 — Penetration test schedule:** Penetration testing?
A. No — single user, private system
B. Self-pentest: Guinevere runs automated security tests periodically
C. Self-pentest + external: Guinevere runs automated tests quarterly, external pentest annually (budget permitting)
D. Full: Continuous automated pentesting, quarterly internal red team (Guinevere), annual external pentest, event-driven on major change

**Q152 — CVE patch SLA:** CVE patching — SLA?
A. Best effort — patch when noticed
B. CRITICAL=7d, HIGH=14d, MEDIUM=30d, LOW=90d
C. CRITICAL=24h, HIGH=7d, MEDIUM=30d, LOW=90d — with auto-patch for non-breaking updates
D. CRITICAL=24h (auto-patch if safe), HIGH=72h, MEDIUM=14d, LOW=45d — with testing requirement and rollback plan

**Q153 — Security metrics:** Security metrics — apa yang di-track?
A. No security metrics — reactive only
B. Key metrics: Open CVEs, patch compliance, failed auth attempts, incident count
C. Comprehensive: Vulnerabilities (open, aging), incidents (count, severity, MTTR), controls (patch compliance, MFA coverage, encryption coverage), audit (findings open/closed)
D. Full security scorecard: Monthly security posture score, trend analysis, risk heat map, compliance dashboard

## K. Security Testing (Q154–Q155)

**Q154 — SAST/DAST tool selection:** Static dan dynamic analysis tools?
A. bandit (Python SAST) — already in CI
B. bandit + safety (dependency) + ruff (lint) — existing
C. bandit + safety + semgrep (multi-language) + OWASP ZAP (DAST for FastAPI) — extended
D. Full suite: SAST (bandit, semgrep), DAST (ZAP), dependency (safety, pip-audit), secret scanning (detect-secrets, gitleaks), container scanning (trivy)

**Q155 — Security regression tests:** Security regression testing — bagaimana?
A. No dedicated security regression tests
B. Key security scenarios tested: safe-word bypass attempt, prompt injection, unauthorized access
C. Security test suite: Per-control test cases, run in CI, block merge on failure
D. Full: BDD security tests, automated red-team scenarios, continuous security regression testing, coverage requirement

---

# DOCUMENT 3: Deployment Guide (Unified) — Q156 to Q232

## A. Prerequisites & Environment (Q156–Q160)

**Q156 — VPS provider recommendation:** hostdata.id sudah dipilih. Deployment Guide harus include alternatif?
A. No — hostdata.id only
B. Mention alternatif: "If hostdata.id unavailable, any Ubuntu 24.04 VPS with 4C/16GB/120GB works"
C. Provider comparison: hostdata.id vs alternatives (DigitalOcean, AWS Lightsail, Linode) with cost/benefit
D. Provider-agnostic: Deployment Guide works on any Ubuntu 24.04 VPS, hostdata.id as tested baseline, cloud-init script for multi-provider

**Q157 — DNS & Cloudflare setup detail:** DNS — seberapa detail?
A. Simple: "Point domain to Cloudflare, enable proxy" — done
B. Include: Domain registration (if not yet), nameserver update, Cloudflare account setup, DNS records, SSL/TLS settings
C. Full DNS: Domain purchase guide, Cloudflare onboarding, all DNS records (A, CNAME, MX for Gmail), page rules, SSL/TLS configuration
D. Full + troubleshooting: DNS propagation check, SSL verification, common issues and fixes, email deliverability setup (SPF, DKIM, DMARC)

**Q158 — Tailscale installation detail:** Tailscale installation — detail level?
A. Command: `curl -fsSL https://tailscale.com/install.sh | sh`
B. Full: Installation + `tailscale up` + MagicDNS enable + HTTPS certificates + device approval
C. Full + configuration: ACL setup, tag assignment, auto-approvers, key expiry, exit node configuration
D. Full + verification: Post-install verification checklist, connectivity test, DNS resolution test, troubleshooting

**Q159 — Required accounts checklist:** Berapa detail untuk account creation?
A. List account names — Samm already has most
B. Per account: Name → signup URL → required plan (free/paid) → purpose → credential storage location
C. Full: Per account setup guide (click-by-click for critical ones like GitHub PAT, Discord bot, 9Router), permission scopes, credential format
D. Full + credential map: Every credential needed, where to get it, how to store it (SOPS key), how to rotate it

**Q160 — Local machine setup:** Samm's local machine — Windows laptop?
A. Mention: "Windows with WSL2, Git, Python 3.12, VS Code" — done
B. Include: WSL2 installation, Git config (name, email, GPG), SSH key gen → GitHub, clone repo
C. Full dev environment: WSL2 + Ubuntu, Git + GPG, Python 3.12 + UV, VS Code + extensions, Docker Desktop, Tailscale, SSH config
D. Full + project setup: Clone all repos, uv sync, run tests, verify everything works before touching VPS

## B. Initial Server Setup (Q161–Q168)

**Q161 — Ubuntu 24.04 hardening depth:** Seberapa dalam server hardening?
A. Basic: `apt update && apt upgrade`, create user, disable root SSH
B. Standard: Update, user creation, SSH hardening (key-only, no root, non-standard port), UFW, fail2ban
C. Advanced: All of B + unattended-upgrades, CrowdSec, kernel hardening (sysctl), auditd, AIDE (file integrity), AppArmor profiles
D. Paranoid: All of C + custom kernel parameters, network segmentation, mandatory access control everywhere, immutable infrastructure where possible

**Q162 — SSH hardening specifics:** SSH hardening — seberapa strict?
A. Key-only auth, no root login — standard
B. Key-only + no root + non-default port + MaxAuthTries=3 + ClientAliveInterval
C. All of B + AllowUsers restriction + protocol 2 only + strong ciphers/KEX/MACs + rate limiting
D. All of C + SSH certificate-based auth (not just key) + bastion host pattern + session recording

**Q163 — fail2ban configuration detail:** fail2ban — berapa jails?
A. Default: sshd jail only
B. Standard: sshd, ufw, nginx/apache — all relevant
C. Extended: sshd, ufw, postgres, fastapi (custom jail), discord webhook (custom)
D. Full: Custom jails for all services, per-jail retry/bantime/findtime configuration, notification on ban

**Q164 — Automatic security updates policy:** unattended-upgrades — config?
A. Security updates only — auto-install
B. Security + updates — auto-install, reboot if needed at 03:00
C. Security + updates + notification — auto-install, report to Discord, reboot schedule respect
D. Full: Staged rollout (security immediate, non-security weekly), pre/post-update health check, auto-rollback on failure, notification

**Q165 — User creation & sudo config detail:** User setup?
A. Simple: `useradd -m guinevere`, `useradd -m samm`
B. Dedicated: `guinevere` user for daemon, `samm` user for admin, sudo scoped to specific commands only
C. Full: User creation with home directories, shell config, SSH key setup, sudoers with command restrictions, no password sudo for specific commands
D. Full + audit: User activity logging, sudo session recording, periodic access review, user lifecycle management

**Q166 — Swap configuration:** 8GB swap — konfigurasi?
A. Simple: `fallocate -l 8G /swapfile`, `mkswap`, `swapon` — done
B. With vm.swappiness=10 to prefer RAM, swap file on fast storage
C. Swap + monitoring: Alert when swap usage exceeds threshold, auto-adjust swappiness based on workload
D. Full: Swap file creation, encryption (for sensitive data protection), swappiness tuning, swap usage alert, alternative: zram for compression

**Q167 — Time synchronization:** NTP untuk VPS?
A. Default Ubuntu: systemd-timesyncd — done
B. Configure: systemd-timesyncd with NTP servers, verify sync
C. Chrony: More accurate, better for timeseries data (TimescaleDB), monitoring
D. Full: Chrony with multiple NTP sources, time sync monitoring, alert on drift, GPS/PPS if budget allows

**Q168 — Hostname & FQDN:** Hostname convention?
A. Default VPS hostname — whatever provider gives
B. Custom: `guinevere.internal` — internal hostname
C. FQDN: `guinevere.samm.dev` or similar — with DNS record
D. Full: Hostname, FQDN, /etc/hosts entries, hostname in monitoring, consistent naming across all docs

## C. Database Setup (Q169–Q176)

**Q169 — PostgreSQL installation method:** PostgreSQL 16 — install method?
A. apt: `apt install postgresql-16` — from Ubuntu repo
B. Official PGDG repo: postgresql.org apt repo — latest patches
C. Docker: PostgreSQL in Docker container — consistent, portable
D. Docker + monitoring: PostgreSQL Docker with postgres_exporter sidecar, pgvector and TimescaleDB extensions pre-loaded

**Q170 — pgvector installation:** pgvector — apt atau compile?
A. apt: `apt install postgresql-16-pgvector` — if available
B. Compile from source: `git clone && make && make install` — always latest
C. Docker image with pgvector pre-installed (pgvector/pgvector:pg16)
D. Docker + verification: Image with pgvector + TimescaleDB + pg_cron, verify all extensions load

**Q171 — TimescaleDB installation:** TimescaleDB — method?
A. apt: `apt install timescaledb-2-postgresql-16` — from Timescale repo
B. Docker: timescaledb/timescaledb:latest-pg16
C. Self-compiled or bundled in custom Docker image
D. Docker + auto-configuration: TimescaleDB + auto-create hypertables from migration, timescaledb-tune for auto-config

**Q172 — PgBouncer setup detail:** PgBouncer — detail config?
A. Basic: Install, configure pool_mode=transaction, listen on 0.0.0.0
B. Full: pgbouncer.ini with per-user config, auth_file, admin user, stats user, log settings, pool sizes
C. Full + monitoring: PgBouncer metrics → Prometheus, admin console access, connection usage alerting
D. Full + HA: Multiple PgBouncer instances (future), HAProxy between app and PgBouncer, health check

**Q173 — Database user creation detail:** Database users — step-by-step?
A. List: CREATE USER for each user, GRANT permissions
B. Full SQL: Per-user creation with password (auto-generated), GRANT per schema, ALTER DEFAULT PRIVILEGES
C. Full SQL + PgBouncer: User creation + PgBouncer auth_file update + userlist.txt + verification
D. Full + Secrets: User creation + password generation + SOPS encryption + PgBouncer config + connection test

**Q174 — Alembic initial migration:** First Alembic migration — bagaimana?
A. `alembic upgrade head` — done
B. Full: `alembic init` → configure alembic.ini → `alembic revision --autogenerate` → review → `alembic upgrade head`
C. Full + verification: Migration with --sql preview, apply, verify schema, verify extensions, verify permissions
D. Full + staging: Run on staging first, validate, then production

**Q175 — Redis installation & configuration:** Redis — Docker atau native?
A. Docker: `docker run redis:7-alpine` — simple
B. Docker + config: Custom redis.conf (RDB+AOF, auth, maxmemory, eviction policy), volume mount
C. Docker + config + multiple instances: Separate Redis instances per DB role (optional, for isolation)
D. Full: Docker Compose with Redis, health check, backup script, monitoring (redis_exporter), alerting

**Q176 — Database backup setup:** Database backup — initial setup?
A. Reference backup strategy — manual pg_dump
B. Automated: WAL archiving to R2, pg_dump cron job, backup verification
C. Automated + monitoring: WAL streaming + daily pg_dump + weekly full backup + backup integrity check + alert on failure
D. Full: All backup types automated, restore drill scheduled, RPO/RTO monitoring, backup encryption verification

## D. Application Deployment (Q177–Q184)

**Q177 — Python 3.12 + UV setup:** Python — install method?
A. apt: `apt install python3.12 python3.12-venv` — from deadsnakes PPA if not in Ubuntu 24.04
B. pyenv: Install pyenv, then Python 3.12 — version management
C. UV's built-in Python: `uv python install 3.12` — unified, fast
D. UV + verification: UV install Python, UV sync, verify all dependencies, run test suite

**Q178 — Repository clone structure:** Clone ke mana, struktur folder?
A. /home/guinevere/ — flat structure
B. /home/guinevere/guinevere/ — core repo, docs separate
C. /home/guinevere/projects/ — all repos under here, organized
D. /home/guinevere/ with specific directory structure per TechArch

**Q179 — SOPS + age key generation detail:** SOPS setup — step-by-step?
A. Simple: `age-keygen` → store in /home/guinevere/.age/key.txt → done
B. Full: age-keygen → store → chmod 600 → create .sops.yaml → test encrypt/decrypt
C. Full + backup: Key generation → store → backup (encrypted) → test → config → verify
D. Full + recovery: Key generation, storage, backup, recovery package creation, verify recovery works

**Q180 — Secrets population workflow:** Bagaimana secrets dimasukkan ke SOPS?
A. Manual: Samm creates .env, encrypts with SOPS
B. Guided: Script prompts for each secret value, validates, encrypts
C. Automated: Where possible, auto-generate (DB passwords), prompt for external (API keys), validate format
D. Full workflow: Secret inventory → generate where auto → prompt for manual → validate → encrypt → verify decrypt → commit

**Q181 — Environment configuration:** Environment variables — bagaimana dikelola?
A. SOPS encrypted .env.sops → decrypt at startup to /tmp/.env
B. Per-service .env files, all SOPS encrypted, decrypt per service
C. Central config service: One config file, services query on startup, encrypted
D. Full: SOPS encrypted files, runtime decryption to tmpfs, environment validation on startup, config change detection, auto-reload where possible

**Q182 — Dependency installation:** UV sync — detail?
A. `uv sync --frozen` — done
B. `uv sync --frozen` with verification of all packages, hash checking
C. Full: `uv sync --frozen --no-install-project` for production, dependency audit, license check
D. Full + security: Dependency install with hash verification, CVE check, SBOM generation

**Q183 — Python service entry points:** Entry points per service?
A. Single main.py with argument to select service
B. Separate entry point per service: core/main.py, surveillance/api.py, scheduler/main.py, loops/main.py
C. Separate entry points + shared library (guinevere_common)
D. Full: Per-service entry points, shared packages, unified logging, health check endpoint on each

**Q184 — Git configuration:** Git config untuk Guinevere?
A. Samm's git config — Guinevere uses same
B. Dedicated: guinevere user git config (name, email, GPG key)
C. Dedicated + signing: GPG key for guinevere user, auto-sign all commits
D. Full: Per-project git config, commit signing, pre-commit hooks, branch protection rules

## E. Service Configuration (Q185–Q192)

**Q185 — systemd unit file detail:** systemd unit — seberapa detail?
A. Basic: ExecStart, Restart=always, WantedBy=multi-user.target
B. Full: ExecStart, WorkingDirectory, User, Group, Restart, RestartSec, Environment, EnvironmentFile, StandardOutput, StandardError, MemoryLimit, CPUQuota
C. Full + hardening: ProtectSystem=strict, ProtectHome=read-only, PrivateTmp, NoNewPrivileges, ReadOnlyPaths, etc.
D. Full + drop-in: Base unit + per-environment drop-in (staging overrides), documentation in unit file

**Q186 — Service startup order detail:** systemd dependency graph — bagaimana?
A. Simple list: guinevere-core requires docker.service, postgresql.service, redis.service
B. Full: Wants= + Requires= + After= + Before= per service, parallel startup where safe
C. Full + health: ExecStartPost= health check script, timeout per service, failure action
D. Full + orchestration: systemd target for each phase, startup sequence with health gates, automatic rollback

**Q187 — Health check implementation:** Health check per service?
A. Simple: systemd watchdog or curl localhost:port/health
B. Structured: Deep health check (DB connection, Redis connection, Discord gateway, LLM reachability)
C. Structured + metrics: Health check results exposed as Prometheus metrics, dashboard panel
D. Full: Health check hierarchy (liveness, readiness, startup), dependency check, degraded mode reporting

**Q188 — Log rotation configuration:** Log rotation — journald atau logrotate?
A. Default journald — auto-rotation
B. journald + logrotate for application log files
C. journald + logrotate + remote shipping (Loki via Promtail)
D. Full: journald config (max size, retention), logrotate for app logs, Promtail shipping, log retention policy per type

**Q189 — Service user configuration:** Service users — systemd User= directive?
A. All services run as `guinevere` user — simple
B. Per-service: guinevere-core → guinevere user, postgres → postgres user, redis → redis user, etc.
C. Per-service + groups: User per service, group membership for shared resources (docker group, guinevere group)
D. Full: Per-service system user, no login shell, dedicated group, resource limits (ulimit), capabilities (CapabilityBoundingSet)

**Q190 — Service environment isolation:** Environment isolation antar service?
A. Same environment — all services share /tmp/.env
B. Per-service environment file — only necessary variables per service
C. Per-service + systemd hardening: PrivateTmp, private network namespace where applicable
D. Full: Container-level isolation (Docker per service), separate network namespace, resource limits, no shared filesystem

**Q191 — Restart policy detail:** systemd restart policy per service?
A. Uniform: Restart=always, RestartSec=10s — for all services
B. Per-service: core = always/10s, surveillance = always/10s, scheduler = always/30s, loops = on-failure/10s
C. Per-service + backoff: Exponential backoff on repeated failures, max restart count, notification on restart loop
D. Full: Per-service restart policy, failure counting, auto-escalation (restart loop → alert → disable → manual investigation)

**Q192 — Service monitoring integration:** systemd services → monitoring?
A. node_exporter provides systemd metrics — auto
B. Explicit: Each service has Prometheus metrics endpoint, scrape config per service
C. Service metrics + alerting: Per-service alert rules (restart count, failed state, high memory/CPU)
D. Full: Service metrics, dashboards, alerting, SLA tracking per service, incident auto-creation

## F. Observability Setup (Q193–Q197)

**Q193 — Prometheus installation:** Docker atau native?
A. Docker: `docker run prom/prometheus` — from TechArch
B. Docker + config: prometheus.yml with scrape targets, volume mount, retention config
C. Docker Compose: Prometheus + node_exporter + postgres_exporter + redis_exporter — all in one compose
D. Full: Docker Compose, scrape configs for all 8 exporters, recording rules, alert rules, retention policy, backup

**Q194 — Grafana installation & dashboard provisioning:** Grafana — setup method?
A. Docker: `docker run grafana/grafana` — manual dashboard creation
B. Docker + provisioning: Dashboard-as-code (JSON), datasource provisioning, auto-import on startup
C. Docker Compose: Grafana + Prometheus + Loki, all with provisioning, persistent storage
D. Full: Docker Compose, all datasources, dashboard provisioning (5 dashboards min), alerting channels, user management

**Q195 — Loki + Promtail setup:** Loki — Docker atau binary?
A. Docker: `docker run grafana/loki` + `docker run grafana/promtail` — simple
B. Docker + config: loki-config.yaml, promtail-config.yaml with scrape configs, volume mounts
C. Docker Compose: Loki + Promtail as part of monitoring compose, pipeline stages for parsing
D. Full: Loki + Promtail + parsing rules + retention + S3 storage backend (R2) + Grafana integration

**Q196 — Sentry DSN configuration:** Sentry — setup?
A. Simple: Create project in Sentry, add DSN to .env.sops, sentry-sdk.init() in code
B. Full: Sentry project creation, DSN per environment, release tracking, source maps, alert rules
C. Full + filtering: PII scrubbing configuration, custom fingerprint rules, sampling for high-volume events
D. Full + integration: Sentry → Discord/Gotify alerts, Sentry → incident creation, error budget tracking

**Q197 — Gotify installation:** Gotify — self-hosted?
A. Docker: `docker run gotify/server` — minimal
B. Docker + config: Persistent storage, user creation, app token generation, Android app setup
C. Docker Compose + config: Gotify + Caddy reverse proxy (auto-HTTPS) + persistent storage + health check
D. Full: Docker Compose, HTTPS via Caddy, app tokens, notification priority mapping, backup

## G. Discord Bot Setup (Q198–Q202)

**Q198 — Discord application creation:** Bot creation — detail?
A. High-level: "Create Discord app, add bot, get token"
B. Step-by-step: Portal URL → New Application → Bot → Token → OAuth2 scopes → Invite URL
C. Full: App creation, bot setup, all required scopes (bot, applications.commands, messages.read), privileged intents (message content, presence, members), invite URL generation
D. Full + verification: Bot join server, verify token works, slash command registration test

**Q199 — Bot permissions & intents:** Privileged Gateway Intents?
A. Only necessary intents: message_content, guild_messages — minimal
B. Required intents: message_content, guild_messages, guild_members, presence — full
C. Required + justification: Each intent documented with purpose, privacy consideration
D. Full: Intent configuration, privacy disclosure, periodic intent audit, removal of unused intents

**Q200 — Slash command registration:** Slash commands — global atau guild?
A. Global — register once, works everywhere
B. Guild-specific — register to specific server only, faster updates
C. Guild for development, global for production — hybrid
D. Guild-specific with auto-sync: Commands defined in code, auto-register on startup, version control

**Q201 — Cloudflare Tunnel for webhook:** Discord webhook via Cloudflare Tunnel — detail?
A. Simple: `cloudflared tunnel create`, connect to localhost:8000/webhook
B. Full: cloudflared installation, tunnel creation, DNS record, ingress rule (only /webhook path), run as systemd service
C. Full + security: Tunnel with Cloudflare Access (JWT validation), WAF rules, rate limiting, monitoring
D. Full + HA: Multiple cloudflared instances (if budget allows), health check, automatic failover

**Q202 — Discord bot startup verification:** How to verify bot is working?
A. Check bot online status in Discord
B. Test /status command — success means bot is working
C. Full checklist: Bot online → /status works → /mood works → persona response correct → webhook receives events → evidence channel functional
D. Full + monitoring: Startup verification script, health check endpoint, auto-notify Samm on successful start, alert on any check failure

## H. Integration Setup (Q203–Q212)

**Q203 — 9Router configuration detail:** 9Router — setup procedure?
A. Simple: "Install 9Router, configure providers, start" — high-level
B. Include: Installation (git clone/pip), config (providers, routing, fallback), systemd service
C. Full: Installation, config with both providers (OpenRouter GPT-5.5 and DeepSeek V4 Flash), routing rules, health check, monitoring
D. Full + verification: Installation, config, test both providers, test failover, verify latency, monitoring integration

**Q204 — GitHub PAT setup:** Personal Access Token — creation?
A. Mention: "Create GitHub PAT with repo+workflow scopes" — high-level
B. Step-by-step: GitHub Settings → Developer Settings → PAT → Fine-grained token, select repos, scopes, expiry
C. Full: Token creation (fine-grained), per-repo access, minimum scopes (as defined in API Integration), expiry (quarterly), storage in SOPS
D. Full + rotation: Token creation, test, store in SOPS, configure rotation in Secrets Rotation Runbook, document rotation procedure

**Q205 — Tasker (Android) configuration:** Tasker setup — how detailed?
A. Mention: "Install Tasker, configure HTTP POST to VPS" — high-level
B. Include: Tasker profiles (app usage, location, notification, call, clipboard), task actions, HTTP POST config
C. Full: Per-profile setup (screenshots or detailed steps), HTTP POST with HMAC signing, error handling, battery optimization
D. Full + import: Tasker XML export, import instruction, HMAC key setup, verification test, troubleshooting

**Q206 — Windows daemon installation:** Python daemon on Windows — setup?
A. Mention: "Install Python, run daemon script, configure NSSM" — high-level
B. Include: Python install, dependencies, daemon config, NSSM service creation, WebSocket endpoint
C. Full: Python 3.12 install, UV sync, daemon config (surveillance types, HMAC key, VPS address), NSSM service, auto-start, permissions for screen capture, clipboard, browser history
D. Full + verification: Installation, config, service start, verify all surveillance types arrive at VPS, troubleshoot common issues

**Q207 — Baileys WhatsApp service setup:** Baileys — Node.js service?
A. Mention: "Install Node.js, run Baileys script" — high-level
B. Include: Node.js install, dependencies (npm install), Baileys script, QR code auth, systemd service
C. Full: Node.js install, project setup, auth state persistence, auto-reconnect, QR display method (headless = send to Discord), systemd service
D. Full + resilience: Setup, auth flow (QR → Discord → Samm scan), session persistence, auto-reconnect, health check, message queue for offline period

**Q208 — Gmail OAuth setup:** Gmail API — OAuth flow?
A. Mention: "Create Google Cloud project, enable Gmail API, create OAuth credentials" — high-level
B. Include: Google Cloud Console steps, OAuth consent screen, credential creation, token storage in SOPS
C. Full: GCP project creation, API enable, OAuth config (web app type), first auth flow (playwright or manual), refresh token storage, verification
D. Full + maintenance: OAuth setup, automated token refresh, token expiry monitoring, re-auth procedure when refresh fails

**Q209 — Brave Search API setup:** Brave Search — simple API key?
A. Mention: "Sign up for Brave Search API, get key" — done
B. Include: Account creation URL, API key generation, pricing, key storage in SOPS
C. Full: Account setup, API key, rate limits, cost monitoring, key rotation
D. Full + integration: Setup, test search query, integrate into research pipeline, cost tracking

**Q210 — Exa AI setup:** Exa — similar to Brave?
A. Same as Brave — API key signup
B. Include: Account creation, API key, semantic search vs neural search config
C. Full: Account setup, API key, search type selection, cost tracking, rate limits
D. Full + strategy: Setup, both search types configured, when to use Brave vs Exa, cost optimization

**Q211 — idcloudhost S3 setup:** Object storage — bucket creation?
A. Mention: "Create idcloudhost S3 bucket" — high-level
B. Include: Account setup, bucket creation, access key generation, permissions, boto3 config
C. Full: Account, bucket creation, IAM user with S3 access, key generation, lifecycle rules, encryption, cost estimate
D. Full + dual setup: idcloudhost S3 (primary) + Cloudflare R2 (backup) — both buckets, both credentials, sync verification

**Q212 — Resend API setup:** Resend — transactional email?
A. Mention: "Create Resend account, get API key, verify domain" — high-level
B. Include: Account creation, domain verification, API key, from address setup
C. Full: Account, domain (DNS records), API key, email templates, rate limits, cost tracking
D. Full + testing: Setup, domain verification, send test email, template creation, bounce handling

## I. First Run & Validation (Q213–Q217)

**Q213 — Pre-flight checklist scope:** Pre-flight — apa saja yang di-check?
A. Essential: All services running, Discord bot online, DB reachable
B. Full: Service health × 8, DB connection, Redis connection, LLM reachable, Discord connected, surveillance endpoints reachable, webhook working, monitoring dashboard accessible
C. Full + performance: All checks + latency within SLO, memory within limits, disk space adequate
D. Full + automated: Pre-flight script that runs all checks, outputs PASS/FAIL, blocks startup on CRITICAL failures

**Q214 — Service startup sequence:** How to start all services?
A. Manual: systemctl start one by one
B. Scripted: startup.sh that starts in correct order with health checks
C. systemd target: guinevere.target that pulls in all services with correct ordering
D. Orchestrated: systemd target + health check gates + automatic rollback on failure + notification

**Q215 — Health check validation:** First run — how to validate health?
A. systemctl status all services — check they're running
B. Health check script hitting all endpoints, checking DB/Redis/LLM/Discord
C. Full validation script: 20+ checks with pass/fail, output report, save to evidence
D. Full + baseline: Run full validation, save as baseline, compare future runs against baseline, alert on deviation

**Q216 — First interaction test:** First Discord interaction — verify what?
A. Send /status — verify response
B. Full: /status, /mood, /task "test", persona response analysis (tone, address, emoji, length)
C. Full + safety: All commands + safe-word test (verify persona suspends) + error handling test + memory recall test
D. Full + evidence: First interaction test suite, record all outputs, evidence in /evidence/first-run/

**Q217 — Monitoring validation:** Verify monitoring stack?
A. Grafana accessible, dashboards loading
B. All dashboards populated with data, all exporters reporting, no gaps
C. All dashboards + alert test (trigger test alert, verify Discord receives) + log aggregation (search test log)
D. Full: All monitoring validated, baseline metrics captured, alert routing verified, backup monitoring verified, runbook for "monitoring is down" tested

## J. Daily Operations (Q218–Q222)

**Q218 — Service management commands:** Daily ops commands?
A. systemctl start/stop/restart/status — documented
B. Common commands: restart core, restart all, view logs, check health, check cost
C. Full ops manual: Per-service commands, common scenarios (high memory → restart loops, stuck loop → pause/resume), log access, metric queries
D. Full + automation: Common tasks automated (health-check.sh, restart-safe.sh, cost-check.sh), one-command operations

**Q219 — Log access & search:** How to access logs?
A. journalctl -u guinevere-* — raw
B. journalctl + Loki/Grafana: Structured search, time range, service filter
C. Loki queries for common scenarios: error rate, last hour, specific service, correlation ID search
D. Full: Log access guide, common queries, log levels explained, log-based alerting, retention reminder

**Q220 — Backup verification:** How to verify backups?
A. Check backup log — success/fail
B. Backup verification script: Check file exists, size > 0, recent timestamp
C. Full: Backup integrity check (hash verification), restore test (monthly), RPO verification, alert on any failure
D. Full + automated: Daily integrity check, weekly restore test (to staging), monthly full DR drill, report generation

**Q221 — Metrics review:** Daily metrics review — what to check?
A. Quick Grafana glance — all green = good
B. Checklist: System health (CPU/RAM/Disk), Guinevere core (task completion, mood, score), Cost (daily spend, projected), Incidents (none)
C. Structured review: Per SLI check, error budget status, anomaly detection, trend analysis
D. Full: Morning briefing auto-generated, metrics summary in Discord, alert on anomalies, monthly report with trends

**Q222 — Cost monitoring:** Daily cost check?
A. Check 9Router/OpenRouter dashboard occasionally
B. Daily: Check daily spend vs budget, projected month-end, alert if >$1 over trend
C. Continuous: Real-time cost tracking, per-category breakdown, anomaly detection, auto-freeze on budget exhaustion
D. Full: Cost dashboard, daily report, auto-optimization suggestions, monthly FinOps review with action items

## K. Update & Deployment (Q223–Q225)

**Q223 — Self-deploy procedure:** Guinevere auto-deploy — detail?
A. Reference Technical Architecture — cron-based pull+restart
B. Include: Specific cron schedule, deploy script, health check, rollback on failure
C. Full: Deploy procedure (git pull → uv sync → run tests → restart services → health check → notify), rollback procedure (git revert → restart → verify), deployment log
D. Full + safety: Pre-deploy backup, canary deploy to staging, gradual rollout, auto-rollback trigger, deployment audit, Samm approval for production

**Q224 — Manual deployment procedure:** When Guinevere can't self-deploy?
A. Samm manually: git pull → uv sync → systemctl restart
B. Full manual: Git pull, uv sync, run tests, restart in correct order, health check, verify
C. Full manual + troubleshooting: Common issues (merge conflicts, dependency failures, migration errors) and solutions
D. Full: Procedure, troubleshooting, rollback, verification checklist, communication (notify status)

**Q225 — Migration execution procedure:** Database migrations — how to apply?
A. alembic upgrade head — simple
B. Full: Pre-migration checklist (backup, test on staging, Samm approval for production), migration execution, verification, rollback procedure
C. Full + automation: Guinevere handles staging, Samm approves production, automated verification, evidence generation
D. Full + zero-downtime: Migration strategies per operation type (add column, add index, rename, data migration), zero-downtime where possible, fallback

## L. Troubleshooting Guide (Q226–Q229)

**Q226 — Service troubleshooting depth:** Service won't start — troubleshooting depth?
A. Basic: Check logs, restart, common fixes
B. Structured: Symptom → likely cause → diagnostic command → fix — for each common issue
C. Full: Decision tree per symptom, log parsing for known error patterns, automated diagnostic script
D. Full + self-healing: Guinevere auto-diagnoses common issues, applies fixes where safe, escalates to Samm with diagnosis when manual intervention needed

**Q227 — LLM API failure troubleshooting:** 9Router/OpenRouter down?
A. Check provider status page, wait — simple
B. Diagnose: Check 9Router health → check OpenRouter health → check network → check API key → detailed fix per cause
C. Full: Diagnostic flow, graceful degradation verification, queue status check, recovery detection, notification
D. Full + playbook: Step-by-step diagnosis, per-failure-mode response, metrics to check, escalation path, recovery verification

**Q228 — Database connection issues:** PostgreSQL connection problems?
A. Check PgBouncer, restart — simple
B. Diagnose: Check connection count, check pool saturation, check network (Tailscale), check credentials, detailed fix
C. Full: Diagnostic flow, PgBouncer admin console commands, connection leak detection, pool metrics, emergency restart procedure
D. Full + prevention: Monitoring thresholds, alert before saturation, auto-increase pool on high demand, connection leak auto-detection

**Q229 — Memory recall issues:** Memory recall not working?
A. Check pgvector index, check embeddings — simple
B. Diagnose: Check pgvector extension, check index health, check embedding pipeline, check query performance
C. Full: Diagnostic query for each recall method (FTS5, vector, importance, tag), index rebuild procedure, embedding regeneration
D. Full + monitoring: Recall latency monitoring, recall quality sampling, automatic index maintenance, alert on recall degradation

## M. Disaster Recovery (Q230–Q232)

**Q230 — Full system restore procedure:** Complete VPS loss — restore from scratch?
A. Reference backup strategy — high-level
B. Step-by-step: New VPS provision → base setup → restore PostgreSQL → restore Redis → restore config → deploy app → verify
C. Full DR runbook: Step-by-step with commands, estimated time per step, verification per stage, rollback if partial failure
D. Full + tested: DR procedure, tested quarterly, timed exercise, continuous improvement, DR evidence in /evidence/dr-drills/

**Q231 — Partial restore (DB only):** Database corruption — DB restore?
A. pg_restore from latest backup — simple
B. Step-by-step: Identify corruption scope, select appropriate backup (WAL vs pg_dump), restore, verify integrity
C. Full: Corruption detection, backup selection, restore procedure, verification queries, service restart, memory consistency check
D. Full + minimal data loss: Point-in-time recovery using WAL, parallel restore for speed, automated verification, post-restore reconciliation

**Q232 — New VPS migration procedure:** Move to new VPS?
A. Backup old VPS → restore to new VPS — high-level
B. Step-by-step: New VPS provision → install all dependencies → restore data → migrate services → switch DNS/Tailscale → verify → decommission old
C. Full: Migration plan with timeline, parallel run period, data sync, cutover procedure, rollback plan, verification
D. Full + zero-downtime: Blue-green migration, data replication during transition, DNS gradual cutover, monitoring throughout, automated rollback trigger