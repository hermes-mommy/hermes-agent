# P19 Research: Repo Architecture Inventory

**Status:** ✅ COMPLETE
**Date:** 2026-06-25
**Author:** Guinevere (parent-authored from scout reports + direct reads)
**Scope:** Full inventory of existing modules, schemas, and integration points relevant to P19 Multi-Project Context.

---

## 1. Executive Summary

The Guinevere codebase is **single-user, single-project, single-persona** today. There is no existing `project_id` or namespace concept anywhere in the runtime. P19 must introduce project-scoping as a cross-cutting concern that threads through:

- Memory/KG storage and recall
- Consent/surveillance scope
- Agent loop/session orchestration
- Discord channel routing
- Audit journals
- Observability metrics
- Domain actuators (finance, gmail, wearable, x_poster)

The good news: the architecture is clean enough that project-scoping can be added as an **orthogonal dimension** without breaking existing invariants. The bad news: it requires touching ~30 files across 8 subsystems.

---

## 2. Subsystem Inventory

### 2.1 Life Kernel (`src/life_kernel/`)

**Purpose:** 24/7 autonomous heartbeat + world model + Hermes brain bridge + background cognition.

**Key files:**
- `state.py:14-264` — `LifeMindState` TypedDict, `SessionState`, phase/priority enums, reducers. **No project_id.**
- `models.py:17-116` — SQLAlchemy models: `LifeMindStateModel`, `HeartbeatRecord`, `DomainMindState` (tables in `life_kernel.*` schema). **No project_id.**
- `graph.py:33-859` — Main 4-node LangGraph (observe/decide/act/reflect), `_ADAPTERS` global dict, `create_life_mind_graph()`. **No project_id.**
- `heartbeat.py:67-629` — 6-interval heartbeat service, polls Redis `life_kernel:hard_stop` every 1s, uses hardcoded `thread_id="heartbeat"`. **No project_id.**
- `cognition.py:44-405` — Background cognition loops (observer, memory, critic, curiosity, self-improvement, guardian). **No project_id.**
- `journal.py:27-66` — `JournalWriter` wraps `PostgresAuditJournal`, writes reflective entries. **No project_id in entry dict.**
- `dashboard.py:19-285` — Renders `LifeMindState` to markdown/embeds. **No project_id.**
- `dashboard_writer.py:59-126` — Edits single Discord dashboard message, Redis key `life_kernel:dashboard_message_id`. **No project_id.**
- `log_channel.py:54-150` — `DiscordLogChannel` / `StructlogLogChannel` abstractions. **No project_id.**
- `decision_context.py:33-47` — P16/P18 context builder, injects KG + memory recall. **No project_id.**
- `session_graph.py:32-456` — Per-session SDLC subgraph, `thread_id` per session. **Session != project.**
- `hermes_brain.py:169-454` — LLM brain bridge wrapping `AIAgent`. **No project_id.**
- `checkpoint.py:23-119` — Postgres/Redis LangGraph checkpointer factories. **No project_id.**
- `self_improve.py:64-365` — Reflection + improvement candidates. **No project_id.**
- `redis_client.py:24-119` — World-state cache, key prefix `life_kernel:world:{key}`. **No project_id.**
- `discord_rest_client.py:80-257` — Outbound Discord REST publisher. **No project_id.**
- `p16_adapter.py:35-99` — KG recall adapter, returns mock data (P20 continuation plan says this is fixed in production). **No project_id.**
- `p18_adapter.py:37-102` — Memory recall adapter, returns mock data (P20 continuation plan says this is fixed in production). **No project_id.**
- `domain_minds/` — Email/Finance/Engineer minds + `durability.py` (PostgresAuditJournal). **No project_id in audit_journal table.**
- `sensor_adapters/` — Placeholder adapters for sensors (discord, gmail, finance, wearable, surveillance, vps, repo, browser). **No project_id.**

**HARD STOP:**
- Redis key: `life_kernel:hard_stop` (global, DB unknown — research must pin it).
- Checked every 1s in `_heartbeat_1s` at `heartbeat.py:254-324`.
- **Global, not scoped to any project/namespace.**

**Critical finding:** The `thread_id="heartbeat"` is hardcoded in 5 places (`heartbeat.py:302, 341, 365, 446, 629`). This is the LangGraph checkpointer key. To make heartbeat project-aware, we need `thread_id=f"heartbeat-{project_id}"` and scope the graph state per project.

### 2.2 Discord (`src/discord/`)

**Purpose:** Discord bot + conversational handler + slash commands.

**Key files:**
- `_entrypoint.py:48-736` — `GuinevereBot`, `on_message()` routes to `handle_conversation` for `#guinevere-chat`.
- `hermes_conversational.py:358-349` — `handle_conversation()` → `_process_and_respond()` → memory recall → `HermesSessionAdapter.send_message()`. **Session by user_id only, no project_id.**
- `_command_registry.py` — Registers slash commands.
- `cmd_focus.py:34, 73` — `/focus` sets `persona:focus_mode` in Redis DB0. **Switch pattern exists.**
- `cmd_casual.py:33, 53` — `/casual` sets `persona:interaction_mode`. **Switch pattern exists.**
- `cmd_consent.py:38-39` — Legacy consent store in Redis DB0 `consent:grants` (not the same as `consent.consent_ledger`).
- `cmd_surveillance_status.py:157-167` — Surveillance status display.
- `cmd_surveillance_pause.py:112-126` — Pauses collection (does not modify consent).
- `cmd_surveillance_resume.py` — Resumes collection.
- `_auth_guard.py:11-22` — `is_faiz_interaction()` gates all sensitive commands to guild owner.

**Channel IDs:**
- Static artifact: `docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml` (includes `guinevere-chat: 1510914600777023659`, `project-alpha-dev`, `project-alpha-docs`, `project-beta-dev`).
- Runtime env vars: `LIFE_KERNEL_DASHBOARD_CHANNEL_ID`, `LIFE_KERNEL_LOG_CHANNEL_ID`.
- Hardcoded in code: `GUINEVERE_CHAT_CHANNEL_ID`.

**Critical finding:** The `/focus` and `/casual` commands are the existing "context switch" pattern. A `/project` or `/switch` command would mirror this, storing `project:active` in Redis DB0.

### 2.3 Hermes (`src/hermes/`)

**Purpose:** Wraps `AIAgent` for per-user Discord conversational sessions + memory bridge.

**Key files:**
- `_session_adapter.py:45-312` — `HermesSessionAdapter`, Redis key `hermes:session:{user_id}`, max 20 turns, TTL 2h. **Session by user_id only, no project_id.**
- `_memory_bridge.py:93-282` — `recall_for_context()` and `store_conversation()`, metadata only records `channel: "guinevere-chat"`. **No project_id filtering.**
- `adapter.py` — Singleton `get_adapter()` factory.
- `plugins/persona_plugin.py:13-531` — Persona plugin, reads global Redis DB5 keys (`guinevere:mood_variant`, `guinevere:yandere_level`, etc.), injects `[PERSONA STATE]` block per LLM call. **Persona is global.**

**Critical finding:** Session keys are `hermes:session:{user_id}` only. To scope by project, we need `hermes:session:{user_id}:{project_id}` and pass `project_id` to `recall_for_context()` and `store_conversation()`.

### 2.4 Agent Loop (`src/loops/`)

**Purpose:** Autonomous loop manager + state machine + conversation loop + tool registry.

**Key files:**
- `manager.py` — `LoopManager.start_loop(task, goal, priority)`.
- `state_machine.py` — `LoopStateMachine` with 7 phases + COMPLETE.
- `context.py:57-119` — `LoopContext` immutable context object. Fields: `loop_id`, `task`, `goal`, `principal`, `priority`, `trigger_source`, `created_at`, `phase`, `retry_count`, `parent_loop_id`. **No project_id or channel_id.**
- `conversation.py` — `ConversationLoop` ReAct-style loop, builds message history.
- `prompts.py` — `SystemPromptBuilder` builds 3-tier prompt (stable persona + context memories + volatile loop metadata). **No project_id in volatile tier.**
- `tool_registry.py` — `ToolRegistry` wraps MCP tools with auth levels.
- `state_store.py` — `LoopStateStore` persists to `projects.loop_instances`. `LoopState` dataclass has **no project_id**.

**Critical finding:** `LoopContext` is the immutable context passed through every loop. Adding `project_id` here would naturally flow into system prompts, tool selection, and state persistence.

### 2.5 Surveillance (`src/surveillance/`)

**Purpose:** Event ingestion, classification, consent gate, retention, safe mode.

**Key files:**
- `consent_gate.py:49-55` — `VALID_SURVEILLANCE_SCOPES` hardcoded frozenset: `surveillance.app_usage`, `surveillance.location`, `surveillance.notifications`, `surveillance.clipboard`, `surveillance.email`. **Global, not project-scoped.**
- `consent_gate.py:180-290` — `check_consent(scope)` gate function, fail-closed, queries `consent.consent_ledger`. **No project_id in query.**
- `consumer.py:49-64` — `_map_event_to_scope()` maps event_type to scope string (e.g., `app_usage` → `surveillance.app_usage`). **No project dimension.**
- `consumer.py:173-195` — `process_event()` calls `check_consent(scope)`, drops event if not allowed.
- `models.py:528-555` — `SurveillanceEvents` table has `event_type`, `device_id`, but **no project_id**.
- `redis_buffer.py:75` — Redis buffer uses single key `surveillance:buffer`. **No project dimension.**
- `safe_mode.py:31-163` — `SurveillanceSafeModeGuard` blocks confrontation actions when safety state is SAFE.
- `secret_scanner.py` — Scans for secrets in clipboard/events.

**Critical finding:** `check_consent(scope)` is THE gate function to wrap/replace. A per-project check would accept an optional `project_id` or use a composite scope key like `surveillance:{project}:{event_type}`.

### 2.6 Persona (`src/persona/`)

**Purpose:** Mood, punishment, reward, yandere, safe mode, drift, milestones.

**Key files:**
- `mood_engine.py` — Mood FSM.
- `mood_persistence.py:31-134` — Stores mood in `persona.persona_state` with `state_key='current_mood'`. **Single global key.**
- `punishment_engine.py:69-88` — Punishment ladder L1-L5 (L6 deferred).
- `reward_engine.py:35-47` — Reward tiers T1-T5.
- `yandere_fsm.py:62-77` — Yandere levels Y0-Y5.
- `safe_mode.py:46-282` — `SafeModeController` activates on distress >= D2_MODERATE.
- `milestone_engine.py:42-772` — Relationship milestones, uses global Redis keys (`guinevere:relationship_stage`, `guinevere:emotional_residue`, etc.) and `persona.relationship_state`/`persona.milestones` tables. **Single global persona.**
- `drift_detector.py` / `drift_corrector.py` — Persona drift detection/correction.
- `ritual_scheduler.py` — Deprecated.

**Critical finding:** Persona is **global / one shared Guinevere persona**. There is no project-isolated persona context today. This aligns with P19's requirement of "SHARED persona but project-isolated context" — but the "project-isolated context" part does not yet exist.

### 2.7 Consent (`consent.*` schema)

**Purpose:** Consent ledger, revocation, runtime enforcement.

**Key files:**
- `src/memory/models.py:943-962` — `consent.consent_ledger` table. Columns: `scope` (text, not project-qualified), `status` (ACTIVE/PAUSED/WITHDRAWN), `granted_at`, `granted_by`, `revoked_at`, `revocation_reason`, `evidence_hash`. **No project_id column.**
- `src/surveillance/consent_gate.py:393-397` — Query pattern: `SELECT status FROM consent.consent_ledger WHERE scope = :scope ORDER BY granted_at DESC LIMIT 1`. **No project_id filter.**
- `src/surveillance/consent_gate.py:43-46, 215, 353-369` — Redis cache key `consent:surveillance:{scope}` with TTL 300s. **No project dimension.**

**Wearable consent:**
- `src/wearable/health_consent.py:35-284` — Mirrors surveillance pattern, cache key `consent:wearable-health:{scope}`. **No project dimension.**

**KG consent:**
- `src/knowledge_graph/consent/manager.py:80-199` — Token-based consent `kg_{scope}_{category}_{uuid8}` stored in `memory.kg_consent_audit`. **No project dimension.**

**Critical finding:** Consent is **global / scope-wide**, not project-scoped. To make it per-project, P19 must add a `project_id` column to `consent.consent_ledger` and change `check_consent(scope)` to accept `project_id` or use composite scope keys.

### 2.8 Memory (`src/memory/`)

**Purpose:** Episodic/semantic/procedural memory, recall, FSRS scheduling.

**Key files:**
- `models.py` — `Episodes`, `SemanticMemories`, `ProceduralSkills`, `SessionSummaries` tables (all in `memory.*` schema). **No project_id columns.**
- `recall.py` — `recall_memories()` function, queries by embedding similarity + metadata filters. **No project_id filter.**
- `store.py` — `store_episode()`, `store_semantic()`, `store_procedural()`. **No project_id.**

**Critical finding:** Memory tables have no `project_id`. To scope recall/store, P19 must add `project_id` columns to all memory tables and thread it through `recall_memories()` and `store_*()` functions.

### 2.9 Knowledge Graph (`src/knowledge_graph/`)

**Purpose:** Entity/edge graph, consent-gated writes, recall.

**Key files:**
- `models.py` — `KGEntities`, `KGEdges`, `KGConsentAudit` tables (all in `memory.*` schema). **No project_id columns.**
- `query/context.py` — `RecallContextAssembler.assemble()`, assembles recall context; `query/engine.py` `KGQueryEngine.search_entities` queries entities/edges by embedding + metadata; `query/rrf_fusion.py` (RRF fusion) + `query/ppr.py` (PPR graph walk). **No project_id filter in any.** (P19-000 fix 2: original scout note referenced a non-existent `recall.py`; the real KG query path is `src/knowledge_graph/query/{context,engine,rrf_fusion,ppr}.py`.)
- `consent/manager.py` — KG consent manager, token-based consent. **No project dimension.**

**Critical finding:** KG tables have no `project_id`. To scope recall/store, P19 must add `project_id` columns to KG tables and thread it through `RecallContextAssembler`.

### 2.10 Audit (`audit.*` schema)

**Purpose:** Hash-chained audit trail for loop events.

**Key files:**
- `src/loops/audit_writer.py:32-97` — `AuditWriter.write_event()` writes to `audit.audit_trail`. Columns: `id`, `event_type`, `event_payload` (JSONB), `principal`, `event_hash`, `previous_hash`, `occurred_at`, plus ClassificationMetaMixin columns. **No project_id column.**
- `src/life_kernel/domain_minds/durability.py:44-142` — `PostgresAuditJournal` writes to `life_kernel.audit_journal`. Columns: `id`, `source`, `entry` (JSONB), `recorded_at`. **No project_id column.**
- `src/knowledge_graph/consent/audit.py:92-183` — Writes to `memory.kg_consent_audit`. Columns: `id`, `consent_token`, `action`, `affected_entity_id`, `affected_edge_id`, `principal`, `occurred_at`, `details`. **No project_id column.**

**Critical finding:** All three audit sinks have no `project_id`. P19 must add `project_id` columns to all audit tables and thread it through `write_event()` and `record()` functions.

### 2.11 Domain Actuators

**Finance (`src/finance/`):**
- `plugin.py:206-216` — `FinancePlugin` Hermes plugin, parses casual finance messages, records transactions.
- DB table: `finance.transactions`, `finance.accounts` (legacy Hermes schema). **No project_id.**
- SQLAlchemy `financial.transactions` table already has an optional `project_id` column (`src/memory/models.py:605-625`), but the plugin does not use it.

**Gmail (`src/gmail/`):**
- `main.py` — Gmail sync, classification, draft generation, notifications.
- `config.py` — `GmailSettings` loads from env vars with `GMAIL_` prefix.
- `metrics.py` — Prometheus metrics.
- **No project_id concept.** Pub/Sub project ID is a GCP project, not a Guinevere project scope.

**Wearable (`src/wearable/`):**
- `main.py` — Sync health data from Mi Fitness Cloud / Gadgetbridge / Health Connect, compute GHI, anomaly detection.
- `config.py` — `WearableConfig` loads from env vars.
- `metrics.py` — Prometheus metrics.
- **No project_id.** `wearable_device_id` and `wearable_owner_id` exist, but no `project_id`.

**X Poster (`src/x_poster/`):**
- `main.py` — Queue and publish posts to X, engagement tracking, moderation.
- `config.py` — `XPosterSettings` loads from env vars with `X_POSTER_` prefix.
- `metrics.py` — Prometheus metrics.
- **No project_id.**

**Critical finding:** All domain actuators are currently global single-instance with no `project_id` concept. P19 must add `project_id` to each actuator's config, DB writes, and metrics labels.

### 2.12 Observability (`src/observability/`, `monitoring/`)

**Purpose:** Prometheus metrics, Grafana dashboards, Loki logs, Sentry errors.

**Key files:**
- `src/core/main.py` — Core custom metrics (`guinevere_requests_total`, `guinevere_request_duration_seconds`).
- `src/observability/windows_metrics.py:50-77` — Windows daemon metrics with `event_type` and `reason` labels.
- `src/wearable/metrics.py:38-127` — Wearable metrics with `status`, `metric_type`, `reason`, `endpoint`, `error_type`, `severity` labels.
- `src/gmail/metrics.py:7-76` — Gmail metrics with `category` and `tier` labels.
- `src/x_poster/metrics.py:11-101` — X poster metrics with `state`, `status`, `action`, `result` labels.
- `src/observability/sentry_integration.py` — Sentry init, `send_default_pii = False`, PII scrubber.
- `monitoring/compose.monitoring.yml` — Docker Compose for Prometheus + Grafana + Loki + Promtail + Alertmanager.
- `monitoring/grafana/dashboards/` — 9 dashboards (agent-loop, database-memory, finops, hermes, infrastructure, llm-cost-latency, persona-safety, x-poster, x-poster-enterprise).

**Critical finding:** All counters/gauges with label dimensions could add `project_id` as a new label. None currently do. The closest existing dimension is `event_type` on Windows/wearable metrics.

### 2.13 Deployment (`systemd/`, `deploy/`)

**Purpose:** systemd units for all Guinevere services.

**Key files:**
- `systemd/guinevere-core.service` — FastAPI core.
- `systemd/guinevere-loops.service` — Agent loop daemon.
- `systemd/guinevere-mcp.service` — MCP gateway server.
- `systemd/guinevere-monitoring.service` — Docker Compose monitoring stack.
- `systemd/guinevere-surveillance.service` — Surveillance consumer.
- `systemd/guinevere-gmail.service` — Gmail integration.
- `systemd/guinevere-x-poster.service` — X poster service.
- `systemd/guinevere-discord.service` — Discord bot.
- `systemd/guinevere-obscura.service` — Obscura CDP server.
- `systemd/guinevere-scheduler.service` — Loop scheduler daemon.
- `systemd/guinevere-shadow-monitor.service` + `.timer` — Shadow monitor check every 60s.
- `systemd/guinevere-wearable-analysis.service` + `.timer` — Wearable daily analysis.
- `systemd/guinevere-wearable-sync.service` + `.timer` — Wearable sync.
- `systemd/hermes-gateway.service` — Hermes API gateway.
- `deploy/systemd/guinevere-whatsapp.service` — WhatsApp channel (Neonize).
- `deploy/discord/guinevere-discord.service` — Discord bot with SOPS decrypt in `ExecStartPre`.

**Deployment mechanism:** No high-level deploy scripts found. Services are run as systemd units under user `guinevere`, slice `guinevere.slice`. Each unit loads an `EnvironmentFile` (e.g., `.env.gmail`, `.env.x_poster`, `.env.wearable`, `.env.surveillance`, `.env.discord`, `.env.scheduler`, `.env.mcp`, `.env.hermes`). The discord unit decrypts `.env.discord.sops` at runtime using SOPS.

**Critical finding:** P19 must ensure per-project secrets (e.g., per-project API keys, per-project OAuth tokens) are **not stored in shared global `.env` files** but rather scoped per project and decrypted/loaded per project or service instance.

### 2.14 Secrets (`secrets/`, `.sops.yaml`)

**Purpose:** SOPS-encrypted secrets for all services.

**Key files:**
- `.sops.yaml` — SOPS config with `creation_rules` for `secrets/*.yaml`, `secrets/*.env`, `.env.wearable`, all encrypted with Faiz's age recipient (public key, as documented in the committed `.sops.yaml`; not reproduced here to keep P19 docs secret-free).
- `secrets/guinevere-secrets.yaml` — Global secrets.
- `secrets/db-passwords.yaml` — DB passwords.
- `secrets/redis-password.yaml` — Redis password.
- `secrets/discord-secrets.enc.yaml` — Discord bot token.
- `secrets/gmail-client-secrets.json` — Gmail OAuth client secrets.
- `secrets/gmail-token.json` — Gmail OAuth token.
- `secrets/backup/` — Plaintext backup env files (`restic-password-plaintext.env`, `idcloudhost-s3-plaintext.env`, `cloudflare-r2-plaintext.env`).

**Critical finding:** Secrets are currently global. P19 must introduce per-project secret files (e.g., `secrets/projects/{project_id}/secrets.enc.yaml`) and ensure systemd units can load project-specific secrets when needed.

### 2.15 Evidence (`docs/setup-evidence/`)

**Purpose:** Per-phase evidence artifacts.

**Convention:** Each phase has its own directory under `docs/setup-evidence/P{N}/` containing `README.md`, `plan/`, `research/`, `evidence/`.

**Existing phases:** P0-P23 (P19 directory exists but is mostly empty).

**Critical finding:** P19 must follow the existing convention and produce evidence artifacts under `docs/setup-evidence/P19/`.

---

## 3. Schema Inventory

### 3.1 PostgreSQL Schemas

- `public` — Baseline tables.
- `memory` — Episodic/semantic/procedural memory, session summaries, KG entities/edges/consent_audit.
- `life_kernel` — Life-mind state, heartbeat record, domain mind state, audit journal.
- `persona` — Persona state, mood history, milestones, relationship state, drift log.
- `consent` — Consent ledger.
- `surveillance` — Surveillance events (if separate from `memory`).
- `finance` — Finance transactions, accounts (legacy Hermes schema).
- `financial` — Financial transactions (SQLAlchemy schema, has optional `project_id`).
- `gamification` — XP/level tracking tables, functions, triggers.
- `projects` — Loop instances, tasks (has `project_id` concept but not used for scoping).
- `audit` — Audit trail (hash-chained).
- `health` — Wearable health hypertables (P14).

### 3.2 Alembic Migration Chain

**Current head:** `p20_001_life_kernel_schema` (revision `p20_001_life_kernel_schema`, down_revision `p5_024`).

**Lineage (newest to oldest):**
1. `p20_001_life_kernel_schema` → `p5_024` — `life_kernel.life_mind_state`, `domain_mind_state`, `heartbeat_record` + indexes.
2. `p5_024` → `p5_015_add_skill_embedding` — `memory.session_summaries` table + index.
3. `p5_015_add_skill_embedding` → `3d41deeca703` (P18) — `embedding vector(1536)` + ivfflat index on `memory.procedural_skills`.
4. `f47a9c2e8b1d` (merge point) → `7239fd4b3b5a`, `3d41deeca703` — Extends `projects.loop_instances` with status, checkpoint_data, retry_count, error_message, phase, phase_artifacts, parent_loop_id.
5. `7239fd4b3b5a` → `p6_gamification_schema` — Adds `reviewer` and `action` to `persona.drift_log`.
6. `p6_gamification_schema` → `p5_add_loop_indexes` — Creates `gamification` schema with XP/level tracking tables, functions, triggers.
7. `p5_add_loop_indexes` → `p5_extend_loops` — Indexes on `projects.loop_instances` (status, task_id, started_at).
8. `p5_extend_loops` → `65f863220922` — Adds goal, guardian_heartbeat_at, lqs_score, cost_estimate, error_count, retry_count to `projects.loop_instances`.
9. `3d41deeca703` (P18) → `65f863220922` — Adds FSRS columns to `memory.episodes`: tier, fsrs_state, last_reviewed_at, next_reviewed_at, retrievability, stability, difficulty.
10. `65f863220922` → `e401bb5fd274` — Adds `search_vector` TSVECTOR and `do_not_recall` boolean to `memory.episodes`.
11. `e401bb5fd274` → `2bed93fd1dd0` — Initial 47-table schema across 12 schemas.
12. `2bed93fd1dd0` → `<base>` — Baseline anchor (empty upgrade).

**Where a P19 migration slots in:** A new P19 migration would set `down_revision = "p20_001_life_kernel_schema"` and become the new head.

### 3.3 Redis DB Assignments (ADR-030)

- **DB0** — Rate limiting, persona state, consent grants (`conversational_handler.py`, `consent.py`, `cmd_punishment.py`, `cmd_reward.py`, `cmd_casual.py`, `cmd_focus.py`).
- **DB1** — Memory recall cache (PostgreSQL+pgvector query cache).
- **DB2** — Surveillance buffer, consent cache (`redis_buffer.py`, `consent_gate.py`, `consumer.py`, `replay.py`, `router.py`).
- **DB3** — Agent state (agent loop task metadata).
- **DB4** — Hermes session storage, Discord state (`session_adapter.py` REDIS_DB=4, `cmd_new_session.py`, `cmd_history.py`).
- **DB5** — Cost tracking, safety plugin state (`cost.py`, `budget.py`, `guinevere_safety` plugin state, DNR list, safe word cache, search tool counters).

**Critical finding:** P19 must decide which DB to use for project registry and project-specific caches. Likely candidates:
- Project registry: DB0 (alongside persona/consent).
- Project-scoped session keys: DB4 (alongside Hermes sessions).
- Project-scoped consent cache: DB2 (alongside surveillance consent cache).

---

## 4. Integration Points Inventory

### 4.1 Memory Recall Integration

**Current flow:**
1. `hermes_conversational.py` calls `HermesMemoryBridge.recall_for_context(query, safe_mode, principal, limit, token_budget, kg_enabled)`.
2. `HermesMemoryBridge` calls `p18_adapter.recall(context)` and `p16_adapter.recall(context)`.
3. Adapters query `memory.episodes` and `memory.kg_entities` by embedding similarity + metadata filters.
4. Results returned as `RecalledMemories` and `RecalledConcepts`.

**P19 integration point:**
- Add `project_id` parameter to `recall_for_context()`.
- Add `project_id` filter to `recall_memories()` and `RecallContextAssembler.assemble()` (in `src/knowledge_graph/query/context.py`) + `KGQueryEngine.search_entities` (in `src/knowledge_graph/query/engine.py`); carry through `rrf_fusion.py` + `ppr.py`.
- Add `project_id` column to `memory.episodes` and `memory.kg_entities`.

### 4.2 Consent Enforcement Integration

**Current flow:**
1. `surveillance/consumer.py` calls `check_consent(scope)` before processing event.
2. `check_consent()` queries `consent.consent_ledger` by `scope` only.
3. Returns `ConsentCheckResult` with `status` (ACTIVE/PAUSED/WITHDRAWN).

**P19 integration point:**
- Add `project_id` parameter to `check_consent()`.
- Add `project_id` column to `consent.consent_ledger`.
- Change query to filter by `(scope, project_id)` or use composite scope key.
- Update all callers in `consumer.py`, `cmd_surveillance_*.py`, `commands_surveillance/*.py`, `gmail/consent_manager.py`.

### 4.3 Audit Journal Integration

**Current flow:**
1. `loops/audit_writer.py` calls `write_event(event_type, event_payload, principal)` to write to `audit.audit_trail`.
2. `life_kernel/domain_minds/durability.py` calls `record(entry)` to write to `life_kernel.audit_journal`.
3. `knowledge_graph/consent/audit.py` calls `record(action, affected_entity_id, affected_edge_id, principal, details)` to write to `memory.kg_consent_audit`.

**P19 integration point:**
- Add `project_id` parameter to all three `write_event()` / `record()` functions.
- Add `project_id` column to all three audit tables.
- Ensure `project_id` is threaded through from loop context / journal entry / consent action.

### 4.4 Observability Integration

**Current flow:**
1. Each subsystem exposes Prometheus metrics with label dimensions (e.g., `event_type`, `category`, `metric_type`).
2. Grafana dashboards query Prometheus and aggregate by labels.

**P19 integration point:**
- Add `project_id` label to all counters/gauges.
- Update Grafana dashboards to filter/aggregate by `project_id`.

### 4.5 Discord Channel Routing Integration

**Current flow:**
1. `GuinevereBot.on_message()` routes to `handle_conversation()` for `#guinevere-chat`.
2. `handle_conversation()` processes message and sends response to same channel.

**P19 integration point:**
- Add `/project` or `/switch` command to set active project in Redis DB0 (`project:active`).
- Add project-scoped channel mapping (e.g., `project-alpha-dev` → project `alpha`).
- Thread `project_id` through `handle_conversation()` and `HermesSessionAdapter`.
- Update dashboard/log channels to indicate active project.

---

## 5. Summary: What Exists vs. What P19 Must Add

| Subsystem | Exists Today | P19 Must Add |
|---|---|---|
| Life kernel | Global heartbeat, graph, journal, dashboard | `project_id` in state, models, graph, heartbeat thread_id, journal entries, dashboard |
| Discord | Session by user_id, `/focus`/`/casual` switch pattern | `project_id` in session keys, `/project` command, channel→project mapping |
| Hermes | Per-user sessions, memory bridge | `project_id` in session keys, memory recall/store filters |
| Agent loop | `LoopContext` without project | `project_id` in `LoopContext`, system prompts, tool selection, state store |
| Surveillance | Global consent scopes, `check_consent(scope)` | `project_id` in consent ledger, `check_consent()` signature, event storage |
| Persona | Global mood/punishment/yandere/safe-mode | No change (persona stays global per P19 requirement) |
| Consent | Global consent ledger, scope-wide | `project_id` column in consent ledger, composite scope keys |
| Memory | Episodic/semantic/procedural tables without project | `project_id` columns in all memory tables, recall/store filters |
| KG | Entities/edges tables without project | `project_id` columns in KG tables, recall/store filters |
| Audit | Three audit sinks without project | `project_id` columns in all audit tables, write functions |
| Domain actuators | Global single-instance finance/gmail/wearable/x_poster | `project_id` in config, DB writes, metrics labels |
| Observability | Prometheus metrics with label dimensions | `project_id` label on all counters/gauges |
| Deployment | systemd units with global env files | Per-project secret files, project-aware service config |
| Secrets | Global SOPS-encrypted files | Per-project secret files under `secrets/projects/{project_id}/` |
| Evidence | Per-phase directories | `docs/setup-evidence/P19/` with plan/research/evidence |

---

## 6. Risk Assessment

### 6.1 HIGH Risk
- **Touching 30+ files across 8 subsystems** — high blast radius, requires careful collision scanning.
- **Schema migrations for 10+ tables** — must be idempotent, rollback-safe, and coordinated with runtime code changes.
- **Changing `check_consent()` signature** — all callers must be updated atomically or feature-flagged.
- **Changing `LoopContext`** — all loop instantiation sites must be updated.

### 6.2 MEDIUM Risk
- **Adding `project_id` to Redis keys** — must handle migration of existing keys (e.g., `hermes:session:{user_id}` → `hermes:session:{user_id}:{project_id}`).
- **Adding `project_id` label to Prometheus metrics** — must update Grafana dashboards and alerting rules.
- **Per-project secret files** — must update systemd units to load project-specific secrets.

### 6.3 LOW Risk
- **Adding `/project` command** — mirrors existing `/focus`/`/casual` pattern.
- **Adding `project_id` to dashboard/log channels** — additive change, no breaking changes.
- **Evidence artifacts** — follows existing convention.

---

## 7. Recommendations

1. **Start with project registry** — Define `projects.project_registry` table (or use existing `projects.tasks` if appropriate) and `ProjectRegistry` class.
2. **Add `project_id` to core data models** — Memory, KG, consent, audit tables. Use Alembic migrations.
3. **Thread `project_id` through function signatures** — `recall_memories()`, `check_consent()`, `write_event()`, `record()`, `LoopContext`.
4. **Use feature flags** — Gate project-scoping behind `project:enabled` Redis flag in DB0, default OFF.
5. **Migrate existing data** — Backfill `project_id = 'default'` for all existing rows.
6. **Add `/project` command** — Mirror `/focus` pattern, store active project in Redis DB0.
7. **Update observability** — Add `project_id` label to metrics, update dashboards.
8. **Document per-project secrets** — Define convention for `secrets/projects/{project_id}/secrets.enc.yaml`.

---

## 8. Conclusion

The Guinevere codebase is well-structured for adding project-aware orchestration. The architecture is clean enough that project-scoping can be added as an orthogonal dimension without breaking existing invariants. However, it requires touching ~30 files across 8 subsystems, which demands careful planning, phased implementation, and thorough testing.

P19 must introduce:
- Project registry (table + class)
- `project_id` columns in memory/KG/consent/audit tables
- `project_id` parameter in recall/consent/audit functions
- `project_id` in `LoopContext` and system prompts
- `project_id` in Redis session keys
- `/project` command for active project switching
- `project_id` label on Prometheus metrics
- Per-project secret files

All of this must be done while preserving:
- Global HARD STOP (`life_kernel:hard_stop` stays global)
- Global persona (mood/punishment/yandere/safe-mode stay global)
- Backward compatibility (existing data backfilled with `project_id = 'default'`)
- Feature-flag safety (project-scoping gated behind `project:enabled` flag)

The implementation can proceed in phases:
1. **Phase 1:** Project registry + schema migrations (add `project_id` columns).
2. **Phase 2:** Thread `project_id` through core functions (recall, consent, audit).
3. **Phase 3:** Add `/project` command + Discord channel routing.
4. **Phase 4:** Update observability + per-project secrets.
5. **Phase 5:** Testing + evidence + documentation.

This phased approach minimizes blast radius and allows incremental validation.
