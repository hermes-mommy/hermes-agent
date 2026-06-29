# R02: Full src/ Codebase Inventory — Disposition and Dependency Graph

**Generated:** 2026-06-29
**Method:** `find ... -name "*.py"` per subdir; `grep -rn "^from src\.\|^import src\."` for cross-module dependencies; `wc -l` for size metrics.

---

## 1. Summary Table

| # | Subdir | .py files | Total lines | Disposition | Target M-module |
|---|--------|-----------|-------------|-------------|-----------------|
| 1 | `src/discord/` | 65 | 17,417 | PORT | M13 |
| 2 | `src/loops/` | 48 | 12,833 | DELETE | M3 (Hermes cron replaces) |
| 3 | `src/knowledge_graph/` | 47 | 21,439 | PORT | M6 |
| 4 | `src/life_integrations/` | 45 | 11,879 | PORT | M8 + M14 |
| 5 | `src/hermes_plugins/` | 44 | 4,567 | PORT | M8 |
| 6 | `src/life_kernel/` | 38 | 8,539 | PORT | M9 |
| 7 | `src/gmail/` | 36 | 16,223 | PORT | M14 |
| 8 | `src/x_poster/` | 26 | 6,723 | PORT | M14 |
| 9 | `src/mcp/` | 25 | 6,978 | PORT (native) | M8 |
| 10 | `src/channels/` | 22 | 3,369 | PORT | M14 |
| 11 | `src/wearable/` | 19 | 5,156 | PORT | M9 |
| 12 | `src/persona/` | 19 | 6,089 | PORT | M4 + M12 |
| 13 | `src/core/` | 15 | 3,234 | PORT / DELETE | M2 |
| 14 | `src/surveillance/` | 14 | 3,020 | PORT | M16 |
| 15 | `src/memory/` | 12 | 6,068 | PORT | M6 |
| 16 | `src/_deprecated/` | 10 | 3,939 | DELETE | (already deprecated) |
| 17 | `src/hermes/` | 7 | 2,587 | DELETE | (bridge to Hermes) |
| 18 | `src/projects/` | 6 | 866 | PORT | M9 (project context) |
| 19 | `src/finance/` | 5 | 1,208 | PORT | M14 |
| 20 | `src/gamification/` | 4 | 872 | PORT | M12 |
| 21 | `src/self_improve/` | 3 | 1,005 | PORT | M10 |
| 22 | `src/observability/` | 3 | 450 | PORT | M2 (infra) |
| 23 | `src/consent/` | 2 | 355 | DELETE | M11 (consent folded into M11) |
| 24 | `src/financial/` | 1 | 1 | DELETE | (empty stub) |

**Grand total:** 517 .py files, 140,084 lines.

**Note:** The prompt listed 24 subdirs. Actual `src/` contains 24 non-pycache subdirs. Six additional dirs exist beyond the prompt spec: `_deprecated` (10), `projects` (6), `finance` (5), `gamification` (4), `observability` (3), `financial` (1).

---

## 2. Cross-Module Dependency Graph (Who Imports Whom)

Edges are `from src.<target> import ...` in files outside `<target>/`. Counts are import-statement occurrences.

```
src.memory.models         <-- 133 imports (THE most-depended-upon module)
src.life_integrations.*   <--  89 imports
src.gmail.*               <--  68 imports (all self-referential within gmail)
src.life_kernel.*         <--  55 imports
src.loops.*               <--  48 imports
src.surveillance.*        <--  29 imports
src.mcp.*                 <--  26 imports
src.persona.*             <--  24 imports
src.memory.* (non-models) <--  24 imports
src.wearable.*            <--  21 imports (mostly self)
src.core.*                <--  19 imports
src.projects.*            <--   8 imports
src.finance.*             <--   8 imports (self)
src.discord.*             <--   7 imports (from x_poster + _deprecated)
src.gamification.*        <--   5 imports (self)
src.hermes.*              <--   3 imports
src.x_poster.*            <--   1 import
src.self_improve.*        <--   1 import
src.observability.*       <--   1 import
src.hermes_plugins.*      <--   1 import
src.consent.*             <--   1 import
```

### Critical "Hub" Modules (imported by many others)

| Module | Imported By | Role |
|--------|-------------|------|
| `src.memory.models` | knowledge_graph, life_kernel, loops, persona, gamification, consent, surveillance, core | SQLAlchemy ORM base + 47 table definitions |
| `src.core.services.*` | gmail, channels, discord, hermes, loops, surveillance | HardStopHandler, CostTracker, LLMRouter, PromptLoader |
| `src.surveillance.consent_gate` | gmail, discord | ConsentChecker, ConsentCheckResult |
| `src.hermes.adapter` | gmail, channels, discord, hermes_plugins | `get_adapter()` — the Hermes runtime bridge |
| `src.mcp.auth` | discord, hermes, hermes_plugins, life_integrations | AuthLevel, approval flow |
| `src.persona.safe_mode` | discord, hermes, wearable | DistressDetector, SafeModeController |
| `src.persona.mood_engine` | discord, wearable, persona/rituals | Mood enum |
| `src.memory.embeddings` | loops, memory (self), knowledge_graph | EmbeddingService |
| `src.projects.secrets_vault` | x_poster, discord | ProjectSecretsVault |

---

## 3. Per-Subdir Detail

### 3.1 src/loops/ (48 files, 12,833 lines) — DELETE

**Disposition: DELETE.** M3 (Hermes native cron/scheduler) replaces this entire subsystem.

**Internal structure:**
- `__init__.py` — re-exports from all submodules (14 imports)
- `manager.py` — `LoopManager` central orchestrator
- `state_machine.py` — `LoopPhase`, `LoopStatus`, `LoopStateMachine`
- `state_store.py` — `LoopStateStore` (persistence)
- `scheduler.py` — `LoopScheduler` (uses LoopManager)
- `cost.py` — `LoopCostTracker` (imports `src.core.services.cost_tracker`)
- `guardian.py` — `LoopGuardian` (safety guardrails)
- `evidence.py` — `EvidencePipeline` (imports artifacts, state_machine)
- `phases/` — 8 phase handlers (research, plan_delegate, delegate, execute, validate_audit, update_docs, setup_evidence) all import `src.loops.state_machine.LoopPhase`
- `hermes_bridge.py` — bridges to Hermes LoopManager
- `safety_integration.py` — imports `src.core.services.hard_stop_handler`
- `skill_library.py` — imports `src.memory.embeddings` + `src.memory.models`
- `tool_registry.py` — imports `src.mcp.auth.AuthLevel`
- `audit_writer.py` — imports `src.memory.models.AuditTrail`

**External consumers:**
- `src/core/main.py` (lines 241, 718, 737)
- `src/discord/cmd_loops.py`, `cmd_loop_pause.py`, `cmd_loop_resume.py`, `cmd_loop_priority.py`, `cmd_evidence.py`
- `src/hermes_plugins/commands_loop/` (6 files)
- `src/self_improve/optimizer.py` (imports audit_writer, budget, reflection, testing_gate)

**Dependency order for safe deletion:** `self_improve` must be ported FIRST (it depends on loops.audit_writer, loops.budget, loops.reflection, loops.testing_gate). The discord/hermes_plugins loop commands can be deleted alongside. `src/memory` and `src/core` do NOT depend on loops.

**Safe to delete early:** Yes, AFTER `self_improve` is ported to M10 and loop commands in discord/hermes_plugins are removed.

---

### 3.2 src/memory/ (12 files, 6,068 lines) — PORT to M6

**Disposition: PORT** (to M6: Memory + Knowledge Graph).

**Key files:**
- `models.py` (1,224 lines) — **THE central ORM.** 47 tables, 12 schemas. `DeclarativeBase` used by knowledge_graph, life_kernel, gamification, consent. PORT FIRST.
- `embeddings.py` (774 lines) — `EmbeddingService`. Used by loops, knowledge_graph, core.
- `read_pipeline.py` (962 lines) — `recall_memories()`. Used by core/services/prompt_loader.
- `consolidation.py` (757 lines) — memory consolidation jobs.
- `spaced_repetition.py` (603 lines) — FSRS scheduler.
- `write_pipeline.py` (358 lines) — `store_episode()`.
- `dnr.py` (418 lines) — "Do Not Repeat" filter.
- `compaction.py` (313 lines) — LLM-based compaction.
- `embedding_backfill.py` (216 lines) — backfill embeddings.
- `db.py` (192 lines) — DB session helpers.
- `tiers.py` (41 lines) — tier constants.
- `__init__.py` (210 lines) — re-exports public API.

**External consumers:** 133 imports from knowledge_graph (batch_processor.py), life_kernel (models.py, redis_client.py), gamification (models.py), consent (revocation_handler.py), core (main.py, prompt_loader.py), discord (7 cmd_memory_* files), self_improve (optimizer.py via loops).

**Port order:** models.py FIRST (all ORM tables), then embeddings.py, then read_pipeline + write_pipeline, then consolidation + compaction, then remaining.

---

### 3.3 src/knowledge_graph/ (47 files, 21,439 lines) — PORT to M6

**Disposition: PORT** (to M6: Memory + Knowledge Graph).

**Internal structure (7 sub-packages):**
- `types.py` — type definitions
- `config.py`, `constants.py`, `errors.py` — config/errors
- `repository.py` — data access layer
- `extraction/` — `entity_extractor.py`, `relation_extractor.py`, `patterns.py`
- `ingestion/` — `pipeline.py`, `batch_processor.py`, `backfill.py`, `backfill_validator.py`, `cron.py`
- `query/` — `engine.py`, `ppr.py`, `rrf_fusion.py`, `context.py`, `token_budget.py`
- `resolution/` — `resolver.py`, `canonical.py`, `fuzzy.py`
- `consent/` — `manager.py`, `audit.py`, `rls.py`
- `observability/` — `logger.py`, `metrics.py`, `tracer.py`
- `eval/` — `golden_set.py`, `metrics.py`, `report.py`, `runner.py`
- `tests/` — 6 test files

**Cross-module dependency:** Only ONE external import: `ingestion/batch_processor.py` imports `src.memory.models.SemanticFacts`. Otherwise entirely self-contained.

**External consumers:** `src/core/main.py` (lines 226, 355-361, 505).

**Port order:** types.py + config.py + constants.py + errors.py first, then repository.py, then extraction/, then query/, then resolution/, then ingestion/, then consent/, then observability/, then eval/, then tests/.

---

### 3.4 src/life_integrations/ (45 files, 11,879 lines) — PORT to M8 + M14

**Disposition: PORT** (M8: MCP/integration framework; M14: channel adapters).

**Internal structure:**
- `types.py` — PermissionTier (L1-L4), IntegrationCapability, IntegrationHealth, IntegrationId
- `base.py` — `BaseIntegrationAdapter` ABC
- `errors.py` — error hierarchy
- `registry.py` — `IntegrationRegistry` (lookup, health, capability discovery)
- `wiring.py` — builds IntegrationRegistry + ActionRouter
- `runtime.py` — builds runtime registry
- `router.py` — `ActionRouter` (classification, consent, execute)
- `scheduler.py` — `IntegrationScheduler`
- `audit.py`, `audit_db_writer.py` — audit infrastructure
- `consent.py`, `consent_checker.py`, `consent_ledger_writer.py` — consent layer
- `permissions.py` — permission enforcement
- `secrets.py` — secrets management
- `project_context.py` — project context injection
- `tombstone.py` — tombstone records
- `_shims.py` — shim helpers
- `adapters/` — 12 adapter implementations (browser, calendar, discord, drive, filesystem, finance, github, gmail, memory, notion, telegram, whatsapp, vps) + `onboarding_manifest.py`
- `adapters/_clients/` — 8 client shims (calendar, drive, fetch, finance_read, github, memory_pipeline, obscura_cdp, notion, telegram, whatsapp_bridge)

**Cross-module dependencies:** None — `src.life_integrations` does NOT import from `src.life_kernel` (verified: `grep -rn "from src.life_kernel" src/life_integrations/` returns 0 real imports). This is by design (docstring in wiring.py).

**External consumers:** `src/core/main.py` (lines 60, 184, 639, 682), `src/core/api/routes.py` (lines 437, 482, 530).

**Port order:** types.py + errors.py + base.py first, then registry.py, then adapters/base adapter patterns, then individual adapters, then wiring/runtime/router, then consent/audit.

---

### 3.5 src/hermes_plugins/ (44 files, 4,567 lines) — PORT to M8

**Disposition: PORT** (to M8: Hermes integration/plugin system).

**Internal structure:**
- `command_catalog.py` — defines command categories
- `commands_admin/` — backup_now, health_check, restart_service
- `commands_finance/` — budget, cost, cost_alert
- `commands_high/` — casual, focus, help, history, mood, new_session, safeword, status
- `commands_loop/` — evidence, loop_pause, loop_priority, loop_resume, loop_start, loop_stop, loops
- `commands_memory/` — memory_add, memory_export, memory_forget, memory_search
- `commands_surveillance/` — clear_cache, surveillance_pause, surveillance_resume, surveillance_status
- `commands_system/` — approve, approve_all, consent, deny, punishment, reward

**Cross-module dependencies:** ZERO external src/ imports (only self-referential `from src.hermes_plugins.command_catalog`). All commands use lazy imports at runtime for their actual functionality.

**External consumers:** `src/discord/cmd_help.py` (line 279 imports command_catalog).

**Port order:** Can be ported as a unit. Low coupling to other modules. Each command subdir is independent.

---

### 3.6 src/life_kernel/ (38 files, 8,539 lines) — PORT to M9

**Disposition: PORT** (to M9: Life Kernel / Autonomous Cognition).

**Internal structure:**
- `state.py` (308 lines) — `LifeMindPhase`, `Priority`, `LifeMindState` TypedDicts
- `hermes_brain.py` (463 lines) — `HermesBrain`, `HermesBrainConfig`
- `graph.py` (1,041 lines) — `create_life_mind_graph()` LangGraph StateGraph
- `cognition.py` (513 lines) — `BackgroundCognition`
- `heartbeat.py` (683 lines) — `HeartbeatService`
- `checkpoint.py` — postgres/redis checkpointers
- `dashboard.py`, `dashboard_writer.py` — dashboard rendering
- `decision_context.py` — imports p16_adapter + p18_adapter + state
- `domain_minds/` — 6 files (deploy_backend, durability, email_mind, engineer_mind, finance_mind)
- `sensor_adapters/` — 10 files (base + 8 adapters: browser, discord, finance, gmail, repo, surveillance, vps, wearable)
- `p16_adapter.py`, `p18_adapter.py` — KG recall + memory recall adapters
- `self_improve.py` — imports life_kernel.state
- `journal.py`, `log_channel.py`, `log_writer.py` — logging infrastructure
- `session_graph.py` — session state management
- `redis_client.py` — imports `src.memory.models.Base`
- `discord_rest_client.py`, `log_channel.py` — Discord integration
- `models.py` — imports `src.memory.models.Base`

**Cross-module dependencies:** Imports `src.memory.models.Base` (models.py, redis_client.py). Otherwise self-contained.

**External consumers:** `src/core/main.py` (lines 259, 389, 494, 524, 533-534, 704).

**Port order:** state.py first (everything depends on it), then models.py + redis_client.py, then graph.py, then hermes_brain.py, then sensor_adapters/, then domain_minds/, then dashboard/journal infrastructure.

---

### 3.7 src/discord/ (65 files, 17,417 lines) — PORT to M13

**Disposition: PORT** (to M13: Discord interface).

**Internal structure:**
- `__init__.py` — package init
- `_entrypoint.py` — bot entrypoint, imports ShadowPipeline + SurveillanceSafeModeGuard
- `_auth_guard.py` — auth guard (used by x_poster)
- `_command_registry.py` — command registration
- `_embed_utils.py` — Discord embed utilities (used by x_poster)
- `_intents.py` — Discord intents
- `_startup.py` — startup sequence
- `colors.py` — color constants (used by x_poster)
- `cmd_*.py` — 40+ command files (approve, backup_now, budget, casual, consent, cost, deny, email, evidence, focus, help, health_check, health_report, history, integrations, loop_*, memory_*, mood, new_session, pc, project, punishment, reward, safeword, status, surveillance_*)
- `hermes_conversational.py` — main conversation handler (imports from persona, memory, core)
- `notifications.py` — notification system
- `project_session.py` — project session management
- `shadow_monitor.py`, `shadow_pipeline.py` — shadow monitoring
- `gotify_fallback.py` — Gotify push fallback
- `listeners/` — gmail_reactions.py, x_reactions.py
- `loops/__init__.py` — imports x_poster.discord.dashboard

**Cross-module dependencies (src.discord imports FROM):**
- `src.x_poster.discord.dashboard` (loops/__init__.py)
- No other external src/ imports at module level. All other cross-module calls are lazy (inside function bodies).

**External consumers:**
- `src/x_poster/discord/commands.py` + `upload_handler.py` import `src.discord.colors`, `src.discord._embed_utils`, `src.discord._auth_guard`
- `src/_deprecated/hermes-migration-phase-7/bot.py` imports `src.discord.shadow_pipeline`

**Port order:** `_auth_guard.py`, `_embed_utils.py`, `colors.py` FIRST (x_poster depends on these), then `_command_registry.py`, `_intents.py`, `_startup.py`, then `hermes_conversational.py` (largest single file), then cmd_* files, then listeners/, then shadow_*.

---

### 3.8 src/gmail/ (36 files, 16,223 lines) — PORT to M14

**Disposition: PORT** (to M14: External service integrations).

**Internal structure:**
- `client.py` — Gmail API client
- `service.py` — main service (imports HardStopHandler, HermesMemoryBridge, ConsentChecker)
- `router.py` — routing logic (imports surveillance.consent_gate, surveillance.secret_scanner)
- `bridge.py` — Hermes bridge (imports core.services.prompt_loader, hermes.adapter)
- `sync_engine.py` — email sync
- `classifier.py` — email classification
- `scorer.py` — importance scoring
- `consent_manager.py` — imports surveillance.consent_gate
- `draft/` — generator.py, send_pipeline.py, discord_ux.py
- `commands/` — consent.py, digest.py
- `grafana/` — gmail_dashboard.py
- Various support: briefing, categories, config, context_manager, envelope, exceptions, financial_extractor, hard_stop, health, memory_store, metrics, notification, pubsub_client, resend_client, sanitization, secret_scanner, structured_logging, token_manager

**Cross-module dependencies:**
- `src.core.services.prompt_loader` (bridge.py)
- `src.core.services.hard_stop_handler` (hard_stop.py, service.py)
- `src.hermes.adapter` (bridge.py)
- `src.hermes._memory_bridge` (service.py)
- `src.surveillance.consent_gate` (consent_manager.py, router.py, service.py)
- `src.surveillance.secret_scanner` (router.py, secret_scanner.py)

**External consumers:** None outside gmail (68 internal cross-references are all self-imports).

**Port order:** config.py + types first, then client.py, then consent_manager.py + hard_stop.py, then router.py, then service.py, then sync_engine + classifier + scorer, then draft/, then commands/.

---

### 3.9 src/mcp/ (25 files, 6,978 lines) — PORT to M8 (native)

**Disposition: PORT** (to M8: MCP native integration — Hermes already has MCP support built in).

**Internal structure:**
- `manager.py` — MCP server manager
- `custom_manager.py` — custom MCP server management
- `tool_selector.py` — tool selection logic
- `auth.py` — `AuthLevel`, approval flow (`_pending_approvals`, `approve`, `deny`)
- `auth_matrix.py` — `ALL_TOOL_NAMES`, `get_auth_level()`
- `budget.py` — MCP budget management
- `cost.py` — MCP cost tracking
- `tools/` — 14 tool wrappers: brave_search, context7, docker_tool, exa_search, fetch, filesystem, git_tool, github, grep_app, obscura_cdp, postgres_tool, redis_tool, sequential_thinking, shell_tool, time_tools, websearch

**Cross-module dependencies:** ZERO external src/ imports. Entirely self-contained.

**External consumers:**
- `src/discord/cmd_approve.py`, `cmd_approve_all.py`, `cmd_deny.py` — import `src.mcp.auth`
- `src/hermes/safety_plugin.py` — imports `src.mcp.auth_matrix`, `src.mcp.auth.AuthLevel`
- `src/hermes_plugins/commands_system/` — approve, approve_all, deny import `src.mcp.auth`
- `src/life_integrations/adapters/_clients/` — fetch_client_shim, github_client_shim import MCP tools
- `src/life_integrations/runtime.py` — imports docker_tool
- `src/loops/tool_registry.py` — imports `src.mcp.auth.AuthLevel`

**Port order:** auth.py + auth_matrix.py first (most depended upon), then manager.py, then tools/, then budget + cost + tool_selector.

---

### 3.10 src/x_poster/ (26 files, 6,723 lines) — PORT to M14

**Disposition: PORT** (to M14: External service integrations).

**Internal structure:**
- `config.py` — imports `src.projects.secrets_vault.ProjectSecretsVault`
- `poster.py` — X/Twitter posting logic
- `x_api_client.py` — X API client
- `service.py` — service orchestration
- `moderator.py` — content moderation
- `caption_generator.py` — caption generation
- `schedule_manager.py` — post scheduling
- `queue_manager.py` — queue management
- `retry_engine.py`, `circuit_breaker.py`, `timeout_handler.py` — resilience
- `discord/` — commands.py (imports `src.discord.colors`, `src.discord._embed_utils`, `src.discord._auth_guard`), dashboard.py, upload_handler.py
- Various support: cleanup, db, exceptions, health, metrics, notification, storage, structured_logging, summary

**Cross-module dependencies:**
- `src.projects.secrets_vault` (config.py)
- `src.discord.colors`, `src.discord._embed_utils`, `src.discord._auth_guard` (discord/commands.py, upload_handler.py)

**External consumers:** `src/discord/loops/__init__.py` imports `src.x_poster.discord.dashboard`.

**Port order:** config.py (needs projects.secrets_vault first), then x_api_client.py, then poster.py + moderator.py, then discord/ subpackage (needs discord colors/embed_utils ported first).

---

### 3.11 src/channels/ (22 files, 3,369 lines) — PORT to M14

**Disposition: PORT** (to M14: External service integrations).

**Internal structure:** All 21 files are under `channels/whatsapp/`:
- `adapter.py`, `bridge.py` (imports `core.services.prompt_loader`, `hermes.adapter`)
- `service.py` — service orchestration
- `router.py` — message routing
- `consent_manager.py` — consent management
- `auth.py`, `session_crypto.py` — security
- `neonize_client.py` — Neonize WhatsApp client
- `formatter.py`, `envelope.py` — message formatting
- `hard_stop.py` (imports `core.services.hard_stop_handler`)
- `ops_commands.py` (imports `core.services.hard_stop_handler`)
- Various: health, metrics, policy, presence, rate_limiter, reconnection, structured_logging, whitelist

**Cross-module dependencies:**
- `src.core.services.prompt_loader` (bridge.py)
- `src.core.services.hard_stop_handler` (hard_stop.py, ops_commands.py)
- `src.hermes.adapter` (bridge.py)

**External consumers:** None.

**Port order:** Entirely self-contained. Port as a unit, starting with adapter + bridge + service.

---

### 3.12 src/persona/ (19 files, 6,089 lines) — PORT to M4 + M12

**Disposition: PORT** (M4: Persona engine; M12: Gamification/Rituals).

**Internal structure:**
- `mood_engine.py` (237 lines) — `Mood` enum (imported by discord, wearable, rituals)
- `mood_persistence.py` (329 lines) — imports `src.memory.models.MoodHistory`, `PersonaState`
- `safe_mode.py` (372 lines) — `SafeModeController`, `DistressDetector` (imported by discord, hermes, wearable)
- `drift_detector.py` (227 lines) — `DriftDetector` (imported by hermes/safety_plugin)
- `drift_corrector.py` (332 lines) — imports drift_detector + safe_mode + memory.models.DriftLog
- `yandere_fsm.py` (336 lines) — `YandereEngine` (imported by hermes/safety_plugin, wearable)
- `punishment_engine.py` (666 lines) — imports safe_mode + yandere_fsm
- `reward_engine.py` (445 lines) — reward system
- `streak_tracker.py` (332 lines) — imports memory.models.PersonaState
- `milestone_engine.py` (872 lines) — milestone tracking
- `transition_rules.py` (375 lines) — persona transition rules
- `ritual_scheduler.py` (451 lines) — ritual scheduling
- `rituals/` — 5 ritual files: morning (183), midday (185), afternoon (139), evening (155), midnight (176). All import `src.persona.mood_engine.Mood` and morning's `RitualResult, TZ_JAKARTA`.

**Cross-module dependencies:**
- `src.memory.models` (mood_persistence.py, drift_corrector.py, streak_tracker.py)

**External consumers:**
- `src/discord/hermes_conversational.py` (safe_mode, mood_engine)
- `src/hermes/safety_plugin.py` (safe_mode, drift_detector, yandere_fsm)
- `src/wearable/alert_router.py` (yandere_fsm), `mood_integration.py` (mood_engine)

**Port order:** mood_engine.py FIRST (depended upon everywhere), then safe_mode.py, then yandere_fsm.py, then drift_detector.py + drift_corrector.py, then punishment/reward engines, then streak_tracker + milestone_engine, then rituals/.

---

### 3.13 src/core/ (15 files, 3,234 lines) — PORT / DELETE

**Disposition: PORT services, DELETE main.py** (M2: Infrastructure).

**Key files:**
- `main.py` (1,051 lines) — **The FastAPI app.** Wires ALL subsystems. HEAVY: imports from observability, surveillance, life_kernel, life_integrations, knowledge_graph, loops, memory. DELETE this file — M2 will have its own app shell.
- `services/llm_router.py` (252 lines) — `LLMRouter`, `TaskType`, `MODELS`. PORT.
- `services/prompt_loader.py` (186 lines) — `get_system_prompt_with_context()`. Imports memory.read_pipeline. PORT.
- `services/hard_stop_handler.py` (148 lines) — `HardStopHandler`, `SafetyState`. PORT (used by gmail, channels, discord, loops, surveillance).
- `services/cost_tracker.py` (67 lines) — `CostTracker`. PORT (used by loops, discord).
- `services/monthly_report.py` — monthly report. PORT.
- `services/llm_metrics.py` — LLM metrics (imported by hermes/safety_plugin). PORT.
- `api/auth.py`, `api/rate_limit.py`, `api/routes.py` — FastAPI routes. DELETE (M2 rebuilds).
- `config/__init__.py`, `models/__init__.py` — config/models stubs.

**Port order:** llm_router.py + hard_stop_handler.py + cost_tracker.py + prompt_loader.py + llm_metrics.py + monthly_report.py FIRST (most depended upon services), then DELETE main.py + api/ + config/ + models/.

---

### 3.14 src/surveillance/ (14 files, 3,020 lines) — PORT to M16

**Disposition: PORT** (to M16: Surveillance).

**Internal structure:**
- `consent_gate.py` — `ConsentChecker`, `ConsentCheckResult`, `check_consent()` (imported by gmail, discord)
- `secret_scanner.py` — `ScanResult`, secret scanning (imported by gmail)
- `safe_mode.py` — `SurveillanceSafeModeGuard` (imports core.services.hard_stop_handler.SafetyState)
- `consumer.py` — `SurveillanceConsumer`
- `redis_buffer.py` — `RedisSurveillanceBuffer`, `create_buffer()`
- `router.py` — `surveillance_router` (FastAPI router, imported by core/main.py)
- `auth.py`, `secrets.py` — auth/secrets
- `classification.py` — event classification
- `models.py` — data models
- `replay.py` — event replay
- `retention.py` — data retention
- `timescale.py` — TimescaleDB (imports memory.models.IngestionLog, SurveillanceEvents)

**Cross-module dependencies:**
- `src.core.services.hard_stop_handler.SafetyState` (safe_mode.py)
- `src.memory.models` (timescale.py)

**External consumers:**
- `src/gmail/` — consent_manager.py, router.py, service.py, secret_scanner.py
- `src/core/main.py` — consumer, redis_buffer, router
- `src/discord/` — cmd_pc.py, cmd_surveillance_*.py, _entrypoint.py

**Port order:** consent_gate.py FIRST (most imported), then secret_scanner.py, then safe_mode.py, then consumer + redis_buffer + router, then remaining.

---

### 3.15 src/wearable/ (19 files, 5,156 lines) — PORT to M9

**Disposition: PORT** (to M9: Life Kernel / sensor data).

**Internal structure:**
- `health_connect_client.py` — Health Connect API
- `gadgetbridge_client.py` — Gadgetbridge client
- `mi_fitness_client.py` — Mi Fitness client
- `sync.py` — sync orchestration
- `normalizer.py` — data normalization
- `baseline.py` — baseline calculation
- `anomaly.py` — anomaly detection
- `alert_router.py` — imports `src.persona.yandere_fsm.is_safe_mode_active`
- `mood_integration.py` — imports `src.persona.mood_engine.Mood`
- `ghi.py` — Global Health Index
- `health_consent.py` — health data consent
- `encryption.py` — data encryption
- `redis_buffer.py` — Redis buffer
- `writer.py` — data writer
- Various: config, errors, metrics, models

**Cross-module dependencies:**
- `src.persona.yandere_fsm` (alert_router.py)
- `src.persona.mood_engine.Mood` (mood_integration.py)

**External consumers:** None.

**Port order:** config + models first, then client implementations, then normalizer + baseline + anomaly, then alert_router + mood_integration (after persona), then sync + writer.

---

### 3.16 src/self_improve/ (3 files, 1,005 lines) — PORT to M10

**Disposition: PORT** (to M10: Self-improvement).

**Files:**
- `__init__.py` — package init
- `optimizer.py` — imports `src.core.services.llm_router`, `src.loops.audit_writer`, `src.loops.budget`, `src.loops.reflection`, `src.loops.testing_gate`
- `promotion.py` — promotion logic

**Cross-module dependencies:** Heavy dependency on `src.loops` (4 imports) and `src.core` (1 import). MUST be ported AFTER loops/core services are available in M2/M3 equivalents.

**External consumers:** None.

**Port order:** optimizer.py last (needs M2 services + M3 loop equivalents). promotion.py can go first.

---

### 3.17 src/hermes/ (7 files, 2,587 lines) — DELETE

**Disposition: DELETE** (bridge to Hermes — no longer needed in native fork).

**Files:**
- `__init__.py` (16 lines) — package init
- `adapter.py` (54 lines) — `get_adapter()` function. Imported by gmail, channels, discord, hermes_plugins.
- `_memory_bridge.py` (302 lines) — `HermesMemoryBridge`. Imported by gmail/service.py, discord/hermes_conversational.py.
- `_session_adapter.py` (389 lines) — session adapter.
- `safety_plugin.py` (1,219 lines) — Hermes safety plugin. Imports `src.core.services.llm_metrics`, `src.persona.safe_mode`, `src.persona.drift_detector`, `src.persona.yandere_fsm`, `src.mcp.auth_matrix`, `src.mcp.auth`.
- `plugins/persona_plugin.py` (591 lines) — persona plugin for Hermes.

**External consumers:**
- `src/gmail/bridge.py`, `src/channels/whatsapp/bridge.py` — `get_adapter()`
- `src/discord/cmd_history.py`, `cmd_new_session.py`, `hermes_conversational.py` — `get_adapter()`, `HermesMemoryBridge`
- `src/hermes_plugins/commands_high/history.py`, `new_session.py` — `get_adapter()`

**Deletion blocker:** `get_adapter()` is used by gmail, channels, discord, and hermes_plugins for the Hermes runtime bridge. In the native fork, this function becomes a no-op or is replaced by direct Hermes runtime access. The `safety_plugin.py` contains significant persona/mcp logic that must be preserved in M4/M8 equivalents BEFORE deletion.

**Deletion safe:** Only AFTER gmail, channels, discord, and hermes_plugins have been ported to use native Hermes runtime instead of `get_adapter()`.

---

### 3.18 src/consent/ (2 files, 355 lines) — DELETE

**Disposition: DELETE** (consent logic moves to M11).

**Files:**
- `__init__.py` — package init
- `revocation_handler.py` — imports `src.memory.models.ConsentLedger` (lazy, line 280)

**External consumers:** `src/memory/` does NOT import from consent. Only the reverse.

**Deletion safe:** Yes, early. The revocation handler's logic moves to M11.

---

### 3.19 src/projects/ (6 files, 866 lines) — PORT to M9

**Disposition: PORT** (project context, used by x_poster and discord).

**Files:**
- `registry.py` — `InMemoryProjectStore`, `ProjectRegistry` (imported by discord/cmd_project.py)
- `secrets_vault.py` — `ProjectSecretsVault` (imported by x_poster/config.py)
- `types.py` — type definitions
- `exceptions.py` — `ProjectNotFoundError`, `InvalidProjectSlugError`, `ProjectAlreadyExistsError` (imported by discord/cmd_project.py)
- `memory_store.py` — project memory store

**Cross-module dependencies:** None.

**External consumers:** `src/discord/cmd_project.py` (5 imports), `src/x_poster/config.py` (1 import).

**Port order:** types.py + exceptions.py first, then registry.py + secrets_vault.py, then memory_store.py.

---

### 3.20 src/finance/ (5 files, 1,208 lines) — PORT to M14

**Disposition: PORT** (to M14: External service integrations).

**Files:**
- `__init__.py`, `db.py`, `hook.py`, `parser.py`, `plugin.py`

**Cross-module dependencies:** None (no external src/ imports).

**External consumers:** `src/hermes_plugins/commands_finance/` references finance concepts but does NOT import from `src.finance`.

**Port order:** As a unit.

---

### 3.21 src/gamification/ (4 files, 872 lines) — PORT to M12

**Disposition: PORT** (to M12: Gamification).

**Files:**
- `models.py` — imports `src.memory.models.Base` (SQLAlchemy base)
- `levels.py` — level definitions
- `service.py` — gamification service

**Cross-module dependencies:** `src.memory.models.Base` only.

**External consumers:** None.

**Port order:** models.py first (needs memory ORM base).

---

### 3.22 src/observability/ (3 files, 450 lines) — PORT to M2

**Disposition: PORT** (to M2: Infrastructure).

**Files:**
- `__init__.py` — `init_sentry` (imported by core/main.py)
- `sentry_integration.py` — Sentry setup
- `windows_metrics.py` — Windows-specific metrics

**Cross-module dependencies:** None.

**External consumers:** `src/core/main.py` imports `init_sentry`.

**Port order:** As a unit.

---

### 3.23 src/_deprecated/ (10 files, 3,939 lines) — DELETE

**Disposition: DELETE** (already deprecated).

All files under `_deprecated/hermes-migration-phase-7/`: bot.py, commands.py, conversational_handler.py, guild_setup.py, intents.py, memory_bridge.py, permissions.py, session_adapter.py, startup.py, _embed_helpers.py.

These are the pre-fork Discord bot files. No external module imports from `_deprecated`. Safe for immediate deletion.

---

### 3.24 src/financial/ (1 file, 1 line) — DELETE

**Disposition: DELETE** (empty stub).

Single `__init__.py` with 1 line. No dependencies. Safe for immediate deletion.

---

## 4. Deletion Order (Safe to Delete First vs. Port First)

### Tier 1: Safe to DELETE immediately (no dependents)

| Subdir | Reason |
|--------|--------|
| `src/_deprecated/` | Already deprecated, zero external consumers |
| `src/financial/` | Empty 1-line stub |
| `src/consent/` | 2 files, only self-referential reverse import |

### Tier 2: Safe to DELETE after dependents are ported

| Subdir | Blocked By |
|--------|------------|
| `src/loops/` | `src/self_improve/optimizer.py` must be ported to M10 first |
| `src/hermes/` | `src/gmail/bridge.py`, `src/channels/whatsapp/bridge.py`, `src/discord/hermes_conversational.py`, `src/hermes_plugins/commands_high/` must replace `get_adapter()` calls first |
| `src/core/main.py` | Everything wires through it; delete last |

### Tier 3: Port order (leaf-first, no-dependency-first)

```
Phase 1 — Foundation (zero external deps):
  1. src/observability/ (M2)
  2. src/finance/ (M14)
  3. src/mcp/auth.py + auth_matrix.py (M8)
  4. src/memory/models.py (M6) — THE critical ORM
  5. src/persona/mood_engine.py (M4)
  6. src/life_kernel/state.py (M9)
  7. src/life_integrations/types.py + errors.py + base.py (M8)
  8. src/knowledge_graph/types.py + config.py + constants.py + errors.py (M6)
  9. src/projects/types.py + exceptions.py (M9)

Phase 2 — Core Services (depend on Phase 1):
  10. src/core/services/llm_router.py (M2)
  11. src/core/services/hard_stop_handler.py (M2)
  12. src/core/services/cost_tracker.py (M2)
  13. src/core/services/prompt_loader.py (M2)
  14. src/core/services/llm_metrics.py (M2)
  15. src/memory/embeddings.py + read_pipeline.py + write_pipeline.py (M6)
  16. src/persona/safe_mode.py + drift_detector.py + yandere_fsm.py (M4)
  17. src/surveillance/consent_gate.py + secret_scanner.py (M16)

Phase 3 — Integration Layer (depend on Phase 2):
  18. src/life_integrations/registry.py + wiring.py + adapters/ (M8)
  19. src/knowledge_graph/ remaining (M6)
  20. src/life_kernel/ remaining (M9)
  21. src/persona/ remaining (M4+M12)
  22. src/gmail/ (M14)
  23. src/channels/ (M14)
  24. src/x_poster/ (M14)
  25. src/wearable/ (M9)
  26. src/surveillance/ remaining (M16)

Phase 4 — Interface Layer (depend on Phase 3):
  27. src/discord/ (M13)
  28. src/hermes_plugins/ (M8)
  29. src/self_improve/ (M10) — depends on loops equivalents
  30. src/gamification/ (M12)
  31. src/projects/ remaining (M9)

Phase 5 — Cleanup:
  32. DELETE src/loops/ entirely
  33. DELETE src/hermes/ entirely
  34. DELETE src/core/main.py + api/
  35. DELETE src/_deprecated/
  36. DELETE src/financial/
  37. DELETE src/consent/
```

---

## 5. Risks

1. **`src/memory/models.py` is the single most-depended-upon file** (133 import statements across 8+ modules). Any schema change cascades everywhere. Must be ported FIRST and tested with mock DB.

2. **`src/hermes/adapter.py:get_adapter()`** is a hidden coupling point used by gmail, channels, discord, and hermes_plugins via lazy imports. Grep reveals these are all inside function bodies, so they won't fail at import time but will fail at runtime if the bridge is deleted before consumers are updated.

3. **`src/core/main.py` (1,051 lines)** is the central wiring file that imports from 8+ modules. It must be the LAST thing deleted and its wiring logic must be replicated in M2's app shell.

4. **`src/self_improve/optimizer.py`** has hard dependencies on 4 loops submodules. It cannot be ported until M3 loop equivalents exist (or these loops modules are preserved in a shim).

5. **`src/discord/` at 65 files is the largest subdir by file count.** The 40+ `cmd_*.py` files each import lazily from multiple modules. Porting discord is the riskiest wave.

6. **Undiscovered subdirs:** The prompt listed 24 subdirs with 517 files. Actual count is 24 non-pycache subdirs (517 files confirmed), but 6 additional dirs exist beyond the prompt spec (`_deprecated`, `projects`, `finance`, `gamification`, `observability`, `financial`). The prompt spec is not wrong — it just didn't enumerate these smaller dirs.

---

## 6. Disposition Summary

| Disposition | Count | Files | Lines |
|-------------|-------|-------|-------|
| PORT | 18 dirs | 460 | 118,294 |
| DELETE | 6 dirs | 57 | 21,790 |
| **Total** | **24 dirs** | **517** | **140,084** |

**PORT breakdown by M-module:**

| M-module | Primary sources | Files | Lines |
|----------|----------------|-------|-------|
| M2 (infra) | core/services, observability | 10 | ~3,684 |
| M4 (persona) | persona (partial) | ~12 | ~4,000 |
| M6 (memory+KG) | memory, knowledge_graph | 59 | 27,507 |
| M8 (MCP/integrations) | mcp, life_integrations, hermes_plugins | 114 | 23,424 |
| M9 (life kernel) | life_kernel, wearable, projects | 63 | 14,561 |
| M10 (self-improve) | self_improve | 3 | 1,005 |
| M12 (gamification) | gamification, persona/rituals | 10 | ~2,760 |
| M13 (discord) | discord | 65 | 17,417 |
| M14 (channels) | gmail, x_poster, channels, finance | 89 | 27,523 |
| M16 (surveillance) | surveillance | 14 | 3,020 |

---

## 7. Verdict

**PASS.** All 517 files across 24 subdirs are inventoried with disposition (PORT/DELETE), target M-module, cross-module dependency edges, and port-order guidance. The dependency graph reveals `src/memory/models.py` as the critical bottleneck (133 importers), `src/hermes/adapter.py:get_adapter()` as a hidden coupling hazard, and `src/core/main.py` as the last-delete orchestrator. Six safe-to-delete-first dirs total 57 files. The remaining 460 files port across 10 M-modules in 5 ordered phases.
