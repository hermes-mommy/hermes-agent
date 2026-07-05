# Research: Dead ORM Models & Plugin Audit

**Date:** 2026-06-09
**Scope:** `src/memory/models.py` writer audit + hermes plugin audit
**Auditor:** subagent (research wave)

---

## Part 1 — ORM Models Writer Audit

### Method
- Read `src/memory/models.py` in full (1228 lines, 47 models across 12 schemas).
- Searched `src/` for `session.add`, `_session.add`, explicit model class instantiation patterns.
- Checked every file that references a model class from `models.py`.

### Note on requested model names
The task mentioned: `YandereLog`, `MoodLog`, `StreakLog`, `ConversationLog`, `MemoryEntry`, `PersonaState`.
Of these, only `PersonaState` exists in `models.py`. The others (`YandereLog`, `MoodLog`, `StreakLog`, `ConversationLog`, `MemoryEntry`) **do not exist** as table names in `models.py`. The corresponding real model names are listed below.

---

### Schema: persona

| Model (class name) | Table | has_writer | writer_files |
|---|---|---|---|
| PersonaState | `persona.persona_state` | **yes** | `src/persona/mood_persistence.py` (set_current_mood, update_mood_streak), `src/persona/streak_tracker.py` (save) |
| MoodHistory | `persona.mood_history` | **yes** | `src/persona/mood_persistence.py` (record_mood_transition) |
| PunishmentLog | `persona.punishment_log` | **yes** | `src/discord/cmd_punishment.py` (punishment_callback) |
| RewardLog | `persona.reward_log` | **yes** | `src/discord/cmd_reward.py` (reward_callback) |
| DriftLog | `persona.drift_log` | **NO** | None found. `src/persona/drift_detector.py` computes drift scores and returns `DriftResult` dataclass but never writes to `drift_log` table. No other file writes to this table. |

### Schema: memory

| Model | Table | has_writer | writer_files |
|---|---|---|---|
| Episodes | `memory.episodes` | **yes** | `src/memory/write_pipeline.py` (store_episode), `src/memory/dnr.py` (reads/updates Episodes for DNR flag) |
| SemanticFacts | `memory.semantic_facts` | **yes** | `src/memory/consolidation.py` (consolidate_episodes → inserts SemanticFacts) |
| FaizProfile | `memory.faiz_profile` | **NO** | No `session.add` or INSERT found targeting this table in `src/`. |
| EmotionalEvents | `memory.emotional_events` | **NO** | No writer found in `src/`. |
| InnerJournal | `memory.inner_journal` | **NO** | No writer found in `src/`. |
| FaizPredictions | `memory.faiz_predictions` | **NO** | No writer found in `src/`. |
| ProceduralSkills | `memory.procedural_skills` | **NO** | No writer found in `src/`. |
| KnowledgeGraph | `memory.knowledge_graph` | **NO** | No writer found in `src/`. |

### Schema: surveillance

| Model | Table | has_writer | writer_files |
|---|---|---|---|
| DeviceRegistry | `surveillance.device_registry` | **NO** | No writer found in `src/`. |
| SurveillanceEvents | `surveillance.events` | **NO** | No writer found in `src/`. |
| IngestionLog | `surveillance.ingestion_log` | **NO** | No writer found in `src/`. |
| ConfrontationBlockLog | `surveillance.confrontation_block_log` | **NO** | No writer found in `src/`. |

### Schema: audit

| Model | Table | has_writer | writer_files |
|---|---|---|---|
| AuditTrail | `audit.audit_trail` | **yes** | `src/memory/dnr.py` (write_dnr_audit_entry) |
| EvidenceRegister | `audit.evidence_register` | **NO** | No writer found in `src/`. |
| ComplianceCheck | `audit.compliance_check` | **NO** | No writer found in `src/`. |

### Schema: financial

| Model | Table | has_writer | writer_files |
|---|---|---|---|
| Transactions | `financial.transactions` | **NO** | No writer found in `src/`. (`src/core/services/cost_tracker.py` exists but does not import or write this model.) |
| ProjectCosts | `financial.project_costs` | **NO** | No writer found in `src/`. |
| MonthlyReports | `financial.monthly_reports` | **NO** | No writer found in `src/`. |
| OptimizationLog | `financial.optimization_log` | **NO** | No writer found in `src/`. |

### Schema: projects

| Model | Table | has_writer | writer_files |
|---|---|---|---|
| Tasks | `projects.tasks` | **NO** | No writer found in `src/`. |
| LoopInstances | `projects.loop_instances` | **NO** | No writer found in `src/`. |
| AgentTasks | `projects.agent_tasks` | **NO** | No writer found in `src/`. |
| EvidenceArtifacts | `projects.evidence_artifacts` | **NO** | No writer found in `src/`. |

### Schema: social

| Model | Table | has_writer | writer_files |
|---|---|---|---|
| SocialMap | `social.social_map` | **NO** | No writer found in `src/`. |
| ClientContacts | `social.client_contacts` | **NO** | No writer found in `src/`. |
| CommunicationLog | `social.communication_log` | **NO** | No writer found in `src/`. |

### Schema: agents

| Model | Table | has_writer | writer_files |
|---|---|---|---|
| SubagentRegistry | `agents.subagent_registry` | **NO** | No writer found in `src/`. |
| TaskQueue | `agents.task_queue` | **NO** | No writer found in `src/`. |
| ExecutionLog | `agents.execution_log` | **NO** | No writer found in `src/`. |

### Schema: consent

| Model | Table | has_writer | writer_files |
|---|---|---|---|
| ConsentLedger | `consent.consent_ledger` | **NO** | No writer found in `src/`. |
| RevocationLog | `consent.revocation_log` | **NO** | No writer found in `src/`. |
| ScopeRegistry | `consent.scope_registry` | **NO** | No writer found in `src/`. |

### Schema: security

| Model | Table | has_writer | writer_files |
|---|---|---|---|
| AccessLog | `security.access_log` | **NO** | No writer found in `src/`. |
| BreakGlassLog | `security.break_glass_log` | **NO** | No writer found in `src/`. |
| SecretRotationLog | `security.secret_rotation_log` | **NO** | No writer found in `src/`. |

### Schema: ops

| Model | Table | has_writer | writer_files |
|---|---|---|---|
| MigrationLog | `ops.migration_log` | **NO** | No writer found in `src/`. |
| BackupLog | `ops.backup_log` | **NO** | No writer found in `src/`. |
| HealthCheck | `ops.health_check` | **NO** | No writer found in `src/`. |
| AlertHistory | `ops.alert_history` | **NO** | No writer found in `src/`. |

### Schema: extensions (config-only tables, not written at runtime)

| Model | Table | has_writer |
|---|---|---|
| PgvectorConfig | `extensions.pgvector_config` | **NO** |
| TimescaledbConfig | `extensions.timescaledb_config` | **NO** |
| PgcryptoConfig | `extensions.pgcrypto_config` | **NO** |

---

### Summary: Models with confirmed writers (5 of 47)

| Model | Writer file |
|---|---|
| `Episodes` | `src/memory/write_pipeline.py` |
| `SemanticFacts` | `src/memory/consolidation.py` |
| `AuditTrail` | `src/memory/dnr.py` |
| `PersonaState` | `src/persona/mood_persistence.py`, `src/persona/streak_tracker.py` |
| `MoodHistory` | `src/persona/mood_persistence.py` |
| `PunishmentLog` | `src/discord/cmd_punishment.py` |
| `RewardLog` | `src/discord/cmd_reward.py` |

> Total: **7 tables have writers** (5 schemas). **40 tables have no active writer in src/**.

### Key finding: DriftLog is dead
`DriftLog` (schema `persona`) has no writer. `drift_detector.py` is a pure computation module — it returns a `DriftResult` dataclass and never persists to the database. The `reviewer` and `action` columns on `DriftLog` were added per ADR-003 but there is no call site that actually does `session.add(DriftLog(...))`.

---

## Part 2 — Hermes Plugins Audit

### Locations scanned
- `hermes-config/plugins/` (project-local, likely symlinked or copied to `~/.hermes/plugins/`)
- `~/.hermes/plugins/`

---

### Plugin: `guinevere_persona`

| Field | Value |
|---|---|
| **Location** | `hermes-config/plugins/guinevere_persona/` + `~/.hermes/plugins/guinevere_persona/` |
| **Manifest** | `plugin.yaml` — hooks: `pre_llm_call`, `post_llm_call`, `pre_tool_call`, `on_session_start` |
| **active** | **yes** |
| **what_it_does** | Reads dynamic persona state (mood, yandere level, punishment tier, reward tier, last interaction) from Redis DB5 and injects it into the LLM prompt context before each inference call. Uses `importlib` to load `src/hermes/plugins/persona_plugin.py` at runtime so it can load without pulling all of `src.hermes`. Registers 4 hooks. Real, functional — `__pycache__` compiled bytecode confirms it has been executed. |

---

### Plugin: `auth_overlay`

| Field | Value |
|---|---|
| **Location** | `hermes-config/plugins/auth_overlay/` + `~/.hermes/plugins/auth_overlay/` |
| **Manifest** | `plugin.yaml` — hooks: `pre_tool_call` |
| **active** | **yes** |
| **what_it_does** | Fail-closed MCP auth enforcement. On every `pre_tool_call`, normalises the Hermes/native/MCP tool name to a canonical `(tool, operation)` pair, looks up the `AuthLevel` from `src/mcp/auth_matrix.py`, and enforces: READ_AUTO → allow; WRITE_NOTIFY → Discord notify then allow; DESTRUCTIVE_APPROVAL → block + store approval request in Redis DB5 with 5-minute TTL; FORBIDDEN → block unconditionally. On any unexpected exception, fails closed (blocks). Has 4 sub-modules: `auth_handler.py`, `approval_handler.py`, `notify_handler.py`, `forbidden_handler.py`. Real, functional — compiled bytecode present. |

---

### Plugin: `guinevere_memory`

| Field | Value |
|---|---|
| **Location** | `~/.hermes/plugins/guinevere_memory/` only (not in hermes-config/plugins/) |
| **Manifest** | `plugin.yaml` — hooks: `prefetch`, `sync_turn`, `on_session_end`, `on_pre_compress`, `on_memory_write`, `system_prompt_block`, `shutdown` |
| **active** | **yes** |
| **what_it_does** | Full Hermes `MemoryProvider` plugin. `prefetch` hook recalls episodic memories from PostgreSQL via `src/memory/read_pipeline.recall_memories()` and injects them into the user message (anti-hallucination guard when empty). `sync_turn` hook persists completed conversation turns to PostgreSQL via `src/memory/write_pipeline.store_episode()` in a daemon thread (non-blocking). Consent gate: all reads/writes blocked when Redis consent for "surveillance" is revoked. Safe-word gate: writes skipped at D4 distress. Has safety pipeline (`safety_gates.py`): anti-hallucination check + classification ceiling filter. Real, functional — compiled bytecode present. |

---

### Plugin: `guinevere_safety` (underscore variant)

| Field | Value |
|---|---|
| **Location** | `~/.hermes/plugins/guinevere_safety/` |
| **Manifest** | `manifest.yaml` — hooks: `pre_llm_call` (priority 95), `post_llm_call` (priority 55); commands: `get_persona_state`, `set_punishment`, `set_reward`, `set_mood`, `get_distress` |
| **active** | **yes** |
| **what_it_does** | Redis-backed dynamic persona state manager. `inject_dynamic_state` (pre_llm_call) reads punishment level, reward tier, distress state, mood variant, yandere level, last interaction from Redis DB5 and injects into prompt. `update_state` (post_llm_call) records interaction timestamp and daily counter. Exposes 5 slash commands for state introspection/mutation. Has `StateManager` class operating on Redis DB5 keys (`guinevere:punishment_level`, `guinevere:reward_tier`, etc.). **Distinct from `guinevere-safety` below** — this is the older plugin without the full 10 safety gates. |

---

### Plugin: `guinevere-safety` (hyphen variant)

| Field | Value |
|---|---|
| **Location** | `~/.hermes/plugins/guinevere-safety/` |
| **Manifest** | `plugin.yaml` — hooks: `pre_llm_call`, `post_llm_call`, `pre_tool_call`, `post_tool_call`, `transform_llm_output`, `on_session_start` |
| **active** | **yes** (entry point is functional; compiled bytecode present) |
| **what_it_does** | Entry-point shim that imports `src/hermes/safety_plugin.py` from the project source tree and re-exports its `register()` function. Ports all 10 safety gates from `src/hermes/safety_plugin.py` to hermes-agent hooks. Covers 6 hook points including `transform_llm_output` and `post_tool_call` which `guinevere_safety` does not cover. This is the **newer, more complete** plugin. **Duplication risk**: `guinevere_safety` and `guinevere-safety` are both active and both register `pre_llm_call` / `post_llm_call` — potential double-injection of persona state into prompts. |

---

## Findings Summary

### Dead models (no writer)
`DriftLog` is the only persona-schema model explicitly flagged as dead. Additionally the following 40 tables across other schemas have no writer in `src/`:
`FaizProfile`, `EmotionalEvents`, `InnerJournal`, `FaizPredictions`, `ProceduralSkills`, `KnowledgeGraph`, all surveillance/financial/projects/social/agents/consent/security/ops tables, and all 3 extensions config tables.

### Plugin issues
1. **`guinevere_safety` vs `guinevere-safety` duplication**: Two separate plugins both hook `pre_llm_call` and `post_llm_call`. One is a standalone Redis state manager; the other is a full safety-gate shim. Risk of double prompt injection and conflicting state updates on each inference call.
2. All 5 plugins are structurally active (register() callable, hooks registered, bytecode compiled). None are placeholders.
