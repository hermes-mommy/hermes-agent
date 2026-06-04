# Phase 2: Agent 5 Commands Migration Map

**Context**: ADR-035 maps 35 Discord commands with feasibility ratings (8 HIGH, 15 MEDIUM, 12 LOW). This document provides a detailed analysis of each command's migration path to Hermes Agent v0.15.2.

**Date**: 2026-06-04  
**Author**: Guinevere (Autonomous Engineering Agent)  
**Status**: Read-Only Research Output  

---

## Executive Summary

The 35 Discord commands (totaling 6,893 lines across src/discord/cmd_*.py and conversational_handler.py) are refactored into Hermes plugins and lifecycle hooks. The 36% net line reduction in this category comes from eliminating discord.py boilerplate (embed builders, interaction defer/response, option extraction, error formatting) that Hermes handles natively via ctx.register_command() and the plugin lifecycle.

| Feasibility | Command Count | Current Lines | Est. Post-Migration Lines | Reduction % |
|---|---|---|---|---|
| **HIGH** (Simple Plugin Port) | 8 | 1,815 | ~900 | 50.4% |
| **MEDIUM** (Plugin with Custom Logic) | 15 | 3,003 | ~1,952 | 35.0% |
| **LOW** (Full Custom Plugin with State) | 12 | 2,075 | ~1,557 | 25.0% |
| **TOTAL** | **35** | **6,893** | **~4,409** | **36.0%** |

---

## HIGH-Priority Command Deep Analysis

### 1. Conversational Handler (Natural Text / "ask" equivalent)
- **Current File**: src/discord/conversational_handler.py (614 lines)
- **Backend Services**: DistressDetector, SafeModeController, HermesMemoryBridge, EmbeddingService, LLMRouter, CostTracker, write_pipeline.store_episode
- **Current Flow**: 13-step pipeline (channel guard -> rate limit -> distress detection -> mood evaluation -> system prompt assembly + memory recall -> LLM call -> response splitting -> cost tracking -> auto-store to memory -> structured logging)
- **Hermes Native Capability**: Hermes natively handles the message pipeline, streaming (progressive edits at ~1.2s intervals), session management, and response formatting.
- **Custom Implementation Needed**: 
  - Distress detection (D0-D4) and HARD STOP must be ported to the pre_prompt hook (fail-closed, <50ms timeout).
  - Memory recall bridge (HermesMemoryBridge.recall_for_context) must be invoked via a custom plugin before LLM call to inject context.
  - Auto-store to memory (store_conversation) must be queued asynchronously post-response.
  - Rate limiting and cost tracking remain as custom plugin state or hook integrations.
- **Migration Verdict**: **HYBRID**. Hermes provides the pipeline skeleton; Guinevere's safety and memory bridges are injected as hooks/plugins.

### 2. /memory-search (Recall)
- **Current File**: src/discord/cmd_memory_search.py (371 lines)
- **Backend Services**: EmbeddingService, ecall_memories (PostgreSQL+pgvector hybrid ranking: Vector+FTS+Recency, RRF k=60)
- **Current Flow**: Extracts query option -> calls ecall_memories with exclude_dnr=True -> builds ranked embed.
- **Hermes Native Capability**: Hermes provides session_search (FTS5) for session-level context browsing.
- **Custom Implementation Needed**: The canonical PostgreSQL+pgvector recall pipeline with 5-level classification and DNR filtering must be preserved verbatim. The plugin will wrap the existing ecall_memories function, using Hermes only for formatting the output embed.
- **Migration Verdict**: **MEDIUM**. Backend logic unchanged; only Discord interaction boilerplate is eliminated.

### 3. /memory-forget (Forget / DNR List)
- **Current File**: src/discord/cmd_memory_forget.py (141 lines)
- **Backend Services**: PostgreSQL memories table (direct SQL UPDATE to set dnr = true)
- **Current Flow**: Extracts memory_id -> executes UPDATE memories SET dnr = true, updated_at = NOW() WHERE id = :mid -> returns status embed.
- **Hermes Native Capability**: None. Hermes has no native "forget" or DNR mechanism.
- **Custom Implementation Needed**: Full custom plugin that executes the exact same SQL UPDATE via the shared session factory. This is a non-negotiable safety requirement (ADR-007, PersonaSafetyPolicy).
- **Migration Verdict**: **LOW**. Pure custom logic wrapped in a Hermes plugin command.

### 4. /status (Ritual State / Multiple Data Sources)
- **Current File**: src/discord/cmd_status.py (339 lines)
- **Backend Services**: Module-level start time, degraded placeholders for loops, tasks, cost, yandere, next scheduled, project, streak, memory health, surveillance.
- **Current Flow**: Builds deterministic embed data with 11 fields -> converts to discord.Embed.
- **Hermes Native Capability**: hermes gateway status provides basic uptime and gateway health.
- **Custom Implementation Needed**: The plugin must query multiple backend services (Redis for streak/cost, PostgreSQL for memory health/surveillance status, GuinevereSafetyPlugin state for yandere level) to populate the embed fields dynamically, replacing the current degraded placeholders.
- **Migration Verdict**: **MEDIUM**. Embed building is native; data aggregation requires custom plugin logic.

### 5. /mood (Persona System / Mood State Machine)
- **Current File**: src/discord/cmd_mood.py (340 lines)
- **Backend Services**: Mood enum, color_for_mood helper.
- **Current Flow**: Builds embed with current mood, undertone, 24h history, triggers, streak, forecast (currently degraded placeholders).
- **Hermes Native Capability**: None. Hermes SOUL.md provides static identity, but not dynamic mood state.
- **Custom Implementation Needed**: GuinevereSafetyPlugin maintains per-session mood state. The command plugin will query this plugin state to display current mood and allow Faiz to override it.
- **Migration Verdict**: **HIGH**. Simple state query wrapped in Hermes plugin command.

---

## Category-by-Category Migration Map

### 1. Core Commands (HIGH Feasibility)
| Command | Current File | Lines | Migration Method | Hermes Plugin | Rationale |
|---|---|---|---|---|---|
| /status | cmd_status.py | 339 | Native Hermes plugin | status_plugin.py | Displays system status. Hermes native embed + plugin state queries. |
| /mood | cmd_mood.py | 340 | Native Hermes plugin | mood_plugin.py | Queries/sets mood level. Maps to SOUL.md mood section + plugin state. |
| /help | cmd_help.py | 312 | Native Hermes plugin | help_plugin.py | Dynamically generated help text from plugin registry. |
| /safeword | cmd_safeword.py | 524 | Native Hermes plugin | safeword_plugin.py | Triggers HARD STOP. Maps to pre_prompt hook dual-layer. |
| /new | cmd_new_session.py | 65 | Native Hermes plugin | 
ew_session_plugin.py | Creates new chat session. Hermes native session management. |
| /history | cmd_history.py | 98 | Native Hermes plugin | history_plugin.py | Displays session history via Hermes session_search (FTS5). |

### 2. Loop Commands (MEDIUM Feasibility)
| Command | Current File | Lines | Migration Method | Hermes Plugin | Rationale |
|---|---|---|---|---|---|
| /loop-start | cmd_loop_start.py | 348 | Plugin port | loop_start_plugin.py | Calls existing loop orchestrator API. Plugin manages lifecycle state. |
| /loop-stop | cmd_loop_stop.py | 404 | Plugin port | loop_stop_plugin.py | Calls existing loop interrupt mechanism. Graceful shutdown logic preserved. |
| /loop-pause | cmd_loop_pause.py | 81 | Plugin port | loop_pause_plugin.py | Sets pause flag in plugin state. Minimal logic. |
| /loop-resume | cmd_loop_resume.py | 100 | Plugin port | loop_resume_plugin.py | Clears pause flag. Re-enters loop orchestrator. |
| /loop-priority | cmd_loop_priority.py | 104 | Plugin port | loop_priority_plugin.py | Updates priority queue in Redis. Plugin calls same Redis operations. |
| /loops | cmd_loops.py | 89 | Plugin port | loops_status_plugin.py | Queries loop orchestrator state. Plugin wraps the same status query. |
| /evidence | cmd_evidence.py | 130 | Plugin port | evidence_plugin.py | Queries implementation evidence registry unchanged. |

### 3. Memory Commands (MEDIUM Feasibility)
| Command | Current File | Lines | Migration Method | Hermes Plugin | Rationale |
|---|---|---|---|---|---|
| /memory-search | cmd_memory_search.py | 371 | Plugin port | memory_search_plugin.py | Queries PostgreSQL+pgvector via ecall_memories. Same backend. |
| /memory-add | cmd_memory_add.py | 366 | Plugin port | memory_add_plugin.py | Writes to PostgreSQL memory store via store_conversation. |
| /memory-export | cmd_memory_export.py | 208 | Plugin port | memory_export_plugin.py | Calls PostgreSQL export functions unchanged. |
| /memory-forget | cmd_memory_forget.py | 141 | Plugin port | memory_forget_plugin.py | Deletes memory entries via DNR pipeline (SQL UPDATE). |

### 4. Surveillance Commands (MEDIUM Feasibility)
| Command | Current File | Lines | Migration Method | Hermes Plugin | Rationale |
|---|---|---|---|---|---|
| /surveillance-status | cmd_surveillance_status.py | 287 | Plugin port | surv_status_plugin.py | Calls existing surveillance status APIs unchanged. |
| /surveillance-pause | cmd_surveillance_pause.py | 144 | Plugin port | surv_pause_plugin.py | Sets pause flag in surveillance controller. Consent-gated via hook. |
| /surveillance-resume | cmd_surveillance_resume.py | 143 | Plugin port | surv_resume_plugin.py | Clears pause flag. Consent check before resume. |

### 5. Finance Commands (LOW Feasibility)
| Command | Current File | Lines | Migration Method | Hermes Plugin | Rationale |
|---|---|---|---|---|---|
| /cost | cmd_cost.py | 502 | Hook + Plugin | cost_plugin.py | Complex cost calculation. Requires pre_tool_call hook integration for real-time tracking. |
| /budget | cmd_budget.py | 488 | Hook + Plugin | udget_plugin.py | Budget enforcement with thresholds. pre_tool_call hook enforces cap. |
| /cost-alert | cmd_cost_alert.py | 149 | Hook + Plugin | cost_alert_plugin.py | Configures cost threshold alerts + Gotify integration. |

### 6. System Commands (LOW Feasibility)
| Command | Current File | Lines | Migration Method | Hermes Plugin | Rationale |
|---|---|---|---|---|---|
| /approve | cmd_approve.py | 72 | Full custom plugin | pprove_plugin.py | Approves pending DESTRUCTIVE_APPROVAL operations via auth overlay. |
| /approve-all | cmd_approve_all.py | 74 | Full custom plugin | pprove_all_plugin.py | Bulk-approves all pending operations. |
| /deny | cmd_deny.py | 72 | Full custom plugin | deny_plugin.py | Denies pending DESTRUCTIVE_APPROVAL operations. |
| /consent | cmd_consent.py | 141 | Full custom plugin | consent_plugin.py | Manages consent state (ACTIVE/PAUSED/WITHDRAWN). Core safety feature. |
| /punishment | cmd_punishment.py | 135 | Full custom plugin | punishment_plugin.py | Manages punishment engine state (L1-L5). Stateful FSM. |
| /reward | cmd_reward.py | 94 | Full custom plugin | eward_plugin.py | Manages reward engine state (T1-T5). Always permitted. |
| /casual | cmd_casual.py | 59 | Native Hermes plugin | casual_plugin.py | Switches to lighter persona mode. Maps to SOUL.md mode toggle. |
| /focus | cmd_focus.py | 78 | Native Hermes plugin | ocus_plugin.py | Enables focus/pomodoro mode. Maps to plugin timer state. |

### 7. Admin Commands (LOW/MEDIUM Feasibility)
| Command | Current File | Lines | Migration Method | Hermes Plugin | Rationale |
|---|---|---|---|---|---|
| /restart-service | cmd_restart_service.py | 133 | Full custom plugin | estart_plugin.py | Restarts systemd services. DESTRUCTIVE_APPROVAL gated via auth overlay. |
| /backup-now | cmd_backup_now.py | 91 | Hook + Plugin | ackup_plugin.py | Integrates with hermes backup + custom PostgreSQL dump pipeline. |
| /health-check | cmd_health_check.py | 124 | Full custom plugin | health_plugin.py | Integrates hermes doctor + custom PostgreSQL/Redis/9Router health probes. |
| /clear-cache | cmd_clear_cache.py | 87 | Plugin port | clear_cache_plugin.py | Calls existing Redis flush operations. Auth-gated via hook. |

---

## Backend Service Dependency Matrix

| Backend Service | Commands Using It | Hermes Migration Strategy |
|---|---|---|
| **PostgreSQL+pgvector** | /memory-search, /memory-add, /memory-forget, /consent | **UNCHANGED**. Accessed via custom plugin wrapping existing src/memory/ functions. |
| **Redis (DB0-DB5)** | /cost, /budget, /clear-cache, /loop-priority, /mood (state) | **UNCHANGED**. Accessed via custom plugin. DB assignments preserved per ADR-030. |
| **HermesMemoryBridge** | Conversational handler, /memory-* | **PORTED**. Plugin invokes ecall_for_context and store_conversation verbatim. |
| **DistressDetector / SafeMode** | Conversational handler, /safeword | **PORTED TO HOOK**. pre_prompt hook with <50ms timeout, fail-closed. |
| **Loop Orchestrator API** | /loop-start, /loop-stop, /loop-pause, /loop-resume, /loops | **UNCHANGED**. Plugin makes HTTP calls to existing internal API (localhost:8000). |
| **Systemd / subprocess** | /restart-service | **PORTED TO PLUGIN**. Custom plugin executes sudo systemctl restart with whitelist validation. |
| **Auth Matrix (src/mcp/auth)** | /approve, /approve-all, /deny | **PORTED TO PLUGIN**. Auth overlay plugin manages approval queue + Discord webhook. |

---

## Hermes Agent Capability Assessment

### What Hermes Agent CLI Handles Natively
1. **Discord Gateway**: WebSocket handling, auto-threading per @mention, RBAC, rate limiting.
2. **Streaming Responses**: Progressive edits at ~1.2s intervals (replaces full-response-then-send).
3. **Session Management**: Native session state, replacing custom Redis DB4 session cache.
4. **Context Compression**: Adaptive compression at 50-70% threshold, protecting last 20 messages.
5. **Circuit Breaker**: Automatic failure isolation preventing cascading errors.
6. **Command Registration**: ctx.register_command() eliminates embed builder and interaction defer boilerplate.
7. **Operational Tooling**: hermes gateway, hermes backup, hermes checkpoints, hermes doctor, hermes security, hermes insights.

### What Requires Custom Implementation (Plugin/Hook)
1. **Safety Enforcement (15+ features)**: HARD STOP, distress detection, consent gate, Yandere FSM, drift detector, DNR enforcement, classification, secret scanner, punishment, reward, mood, rituals, streaks, safe mode, forbidden patterns. **Solution**: GuinevereSafetyPlugin + 7 lifecycle hooks.
2. **Memory Bridge**: PostgreSQL+pgvector recall/write with hybrid ranking and DNR filtering. **Solution**: Custom plugin invoking existing src/memory/ functions.
3. **Auth Matrix**: 4-level authorization (READ_AUTO, WRITE_NOTIFY, DESTRUCTIVE_APPROVAL, FORBIDDEN). **Solution**: Auth overlay plugin intercepting pre_tool_call hook.
4. **LLM Routing**: 9Router at localhost:20128 with custom fallback chain. **Solution**: Hermes configured as custom provider; fallback logic in plugin if native unsupported.
5. **Budget Enforcement**: \/month hard cap. **Solution**: Custom pre_tool_call hook checking cumulative cost.

---

## Migration Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| **HARD STOP timing shift** | Current _on_message_listener fires BEFORE on_message. pre_prompt hook fires after gateway acceptance but BEFORE LLM. | Dual-layer: custom Discord gateway plugin for pre-gateway interception + pre_prompt hook. |
| **Auth matrix has no Hermes equivalent** | Binary enable/disable model lacks 4-level granularity. | Auth overlay plugin is a compile-time gate; Hermes refuses to start without it. |
| **Shadow mode complexity** | Running bot.py AND Hermes gateway in parallel for 48+ hours. | Separate Discord channels, memory write mutex (only bot.py writes), separate Redis DBs, daily cost reports. |
| **Solo-developer cognitive load** | Faiz is the sole operator, developer, tester, reviewer. | Pre-written rollback scripts, 3-4 hours/day cap, rollback dry-run before Phase 2 cutover. |

---

## Conclusion

The migration of 35 Discord commands to Hermes Agent is **highly feasible** with a **36% net line reduction** in command-specific code. The architecture preserves all safety-critical backend services (PostgreSQL+pgvector, Redis, custom memory bridge) while offloading Discord gateway boilerplate, session management, and streaming to Hermes native capabilities. 

The **HIGH-priority commands** (sk/conversational, ecall, orget, status, mood) require careful porting of business logic to Hermes hooks and the GuinevereSafetyPlugin, but none require fundamental re-architecture of the underlying data pipelines.

**Next Action**: Proceed to Phase 1 (Safety Foundation) implementation, beginning with the GuinevereSafetyPlugin and pre_prompt HARD STOP hook, as dictated by ADR-035 migration phases.
