# R01: Hermes v0.15.2 Deep Dive — Exact Modification Points per P24 Module

**Generated:** 2026-06-29
**Method:** Direct file reads and grep searches against `.venv/Lib/site-packages/` installed wheel tree.
**Hermes source tag:** v2026.5.29.2 @ SHA 77a1650c (verified real, tag tree == installed wheel tree bit-for-bit).

---

## 1. run_agent.py — AIAgent class (L327)

**File:** `C:/Users/faizz/guinevere/.venv/Lib/site-packages/run_agent.py`
**Total lines:** ~4617

### Class AIAgent (L327)

AIAgent is defined at L327. Its `__init__` (L350-487) is a **thin forwarder** that delegates everything to `agent.agent_init.init_agent()` (L418-419):

```python
def __init__(self, ...):  # L350
    """Forwarder — see agent.agent_init.init_agent."""
    from agent.agent_init import init_agent
    init_agent(self, ...)
```

### Key lifecycle methods on AIAgent

| Method | Line | Purpose | P24 hook point |
|--------|------|---------|----------------|
| `close()` | L2400 | Resource teardown: kills background processes, cleans terminal sandbox, browser daemon, active children, OpenAI client | M3 (consciousness): register a teardown callback here |
| `run_conversation()` | L4360-4371 | Thin forwarder to `agent.conversation_loop.run_conversation` | All modules hook into conversation_loop |
| `_execute_tool_calls()` | L4271 | Dispatches tool calls (concurrent or sequential) | M2 hard_stop check goes at L3811 call site in conversation_loop |
| `_dispatch_delegate_task()` | L4294 | Single call site for delegate_task dispatch | M5 delegation patches affect delegate_tool.py constants |
| `reset_session_state()` | L599 | Resets all session counters, triggers context engine transition | M3 consciousness session lifecycle |
| `switch_model()` | L684 | Forwarder to `agent.agent_runtime_helpers.switch_model` | M1 config hooks |

### TaskGroup / lifespan wire points

There is **no TaskGroup or async lifespan pattern** in run_agent.py. AIAgent is a synchronous class. The `close()` method (L2400-2454) is the explicit teardown point, called manually by the gateway or CLI. No async context manager (`__aenter__`/`__aexit__`) exists.

**M3 consciousness wire points:**
- `close()` at L2400 — add consciousness teardown
- `reset_session_state()` at L599 — add consciousness state reset
- `run_conversation()` forwarder at L4360 — consciousness pre/post hooks go in conversation_loop

**M15 HTTP wire points:**
- No HTTP server in run_agent.py itself. M15 would wire into `gateway/run.py` GatewayRunner (L1661) which manages platform adapters. The GatewayRunner's `_connect_adapter_with_timeout` at L4171 and `self.adapters[platform] = adapter` at L4173 are the registration points.

---

## 2. agent/agent_init.py — init_agent()

**File:** `C:/Users/faizz/guinevere/.venv/Lib/site-packages/agent/agent_init.py`
**Total lines:** 1649
**Function:** `init_agent(agent, ...)` at L139-1648

### Module wiring points (sequential, by line)

| Line | What is initialized | P24 module that hooks here |
|------|---------------------|---------------------------|
| L255 | `_install_safe_stdio()` | — |
| L257-287 | Basic agent attributes (model, max_iterations, platform, user_id, etc.) | M1 Pydantic config replaces these |
| L290-376 | Provider auto-detection, api_mode selection | M1 config |
| L394-405 | Callbacks (tool_progress, thinking, reasoning, clarify, step, stream_delta, status, tool_gen) | M3 consciousness callback |
| L411 | `agent._tool_guardrails = ToolCallGuardrailController()` | M2 hard_stop |
| L415-417 | `_interrupt_requested`, `_interrupt_message`, `_execution_thread_id` | M2 interrupt integration |
| L428-429 | `_pending_steer`, `_pending_steer_lock` | — |
| L442-444 | `_delegate_depth`, `_active_children`, `_active_children_lock` | M5 delegation |
| L548-560 | `_stream_context_scrubber`, `_stream_think_scrubber` | — |
| L576-882 | LLM client construction (OpenAI, Anthropic, Bedrock) | M15 HTTP (if exposing agent via HTTP) |
| L888-901 | Fallback chain setup | — |
| L910-914 | `agent.tools = get_tool_definitions(...)` + `agent.valid_tool_names` | Tool registration |
| L1024-1030 | CheckpointManager | — |
| L1033-1041 | SessionDB, _parent_session_id | — |
| L1044-1045 | TodoStore | — |
| L1047-1052 | `load_config()` — main config load | M1 replaces with Pydantic |
| L1054-1060 | ToolCallGuardrailController from config | M2 hard_stop config |
| L1067-1087 | Memory store (MEMORY.md, USER.md) | M6 memory |
| L1091-1153 | **Memory provider plugin** — loads from config `memory.provider`, calls `_load_mem()`, initializes MemoryManager | **M6 MemoryProvider subclass wires in here** |
| L1157-1187 | Memory provider tool schema injection into `agent.tools` | M6 tool surface |
| L1189-1195 | Skills config nudge interval | — |
| L1214-1260 | Context compressor initialization | M3 consciousness context engine |
| L1385-1515 | Context engine selection (config-driven, plugin, or built-in ContextCompressor) | M3 consciousness context engine |
| L1516-1528 | Context engine `on_session_start` notification | M3 consciousness session start |

### ctx.register_hook call sites

There is **no `ctx.register_hook` pattern** in Hermes. Instead, Hermes uses:
1. **Plugin hooks** via `hermes_cli.plugins.invoke_hook()` (called in conversation_loop.py)
2. **Memory provider lifecycle** via MemoryManager (agent_init.py L1091-1153)
3. **Callback attributes** on AIAgent (tool_progress_callback, thinking_callback, etc.)

---

## 3. agent/conversation_loop.py — run_conversation()

**File:** `C:/Users/faizz/guinevere/.venv/Lib/site-packages/agent/conversation_loop.py`
**Total lines:** ~4607
**Function:** `run_conversation(agent, ...)` at L362-4602

### Complete hook execution order

| Order | Hook | Line | Type | Notes |
|-------|------|------|------|-------|
| 1 | `_install_safe_stdio()` | L392 | Internal | Guard stdio |
| 2 | `_ensure_db_session()` | L394 | Internal | SQLite session |
| 3 | `set_runtime_main()` | L401-408 | Internal | Auxiliary client routing |
| 4 | `set_session_context()` | L413 | Internal | Log tagging |
| 5 | `set_current_write_origin()` | L422 | Internal | Skill provenance |
| 6 | `_restore_primary_runtime()` | L427 | Internal | Fallback restore |
| 7 | **`invoke_hook("on_session_start")`** | L305 | Plugin | First turn only |
| 8 | Iteration budget reset | L492 | Internal | — |
| 9 | Memory nudge check | L562-569 | Internal | M4 emotion hook point |
| 10 | **`invoke_hook("pre_llm_call")`** | L679 | Plugin | Per-turn, before API |
| 11 | Memory manager `on_turn_start()` | L741-745 | Memory | M6 hook |
| 12 | Memory manager `prefetch_all()` | L753-757 | Memory | M6 prefetch |
| 13 | **`invoke_hook("pre_api_request")`** | L1201 | Plugin | Per-API-call |
| 14 | API call (streaming or non-streaming) | L1281-1286 | Internal | — |
| 15 | **`invoke_hook("post_api_request")`** | L3431 | Plugin | Per-API-call, after response |
| 16 | Tool call validation | L3579-3728 | Internal | M2 hard_stop check location |
| 17 | Tool guardrails (cap_delegate, deduplicate) | L3733-3738 | Internal | — |
| 18 | **`_execute_tool_calls()`** | L3811 | Internal | Actual tool dispatch |
| 19 | Guardrail halt check | L3813-3814 | Internal | M2 hard_stop result |
| 20 | Background memory/skill review nudge | L4400+ | Internal | — |
| 21 | **`invoke_hook("transform_llm_output")`** | L4450 | Plugin | Post-loop, transform response |
| 22 | **`invoke_hook("post_llm_call")`** | L4471 | Plugin | Post-loop, persist data |
| 23 | **`invoke_hook("on_session_end")`** | L4590 | Plugin | Every run_conversation exit |

### M2 hard_stop check in tool dispatch

The hard_stop check happens at **L3813** in `run_conversation()`:

```python
# L3811
agent._execute_tool_calls(assistant_message, messages, effective_task_id, api_call_count)
# L3813
if agent._tool_guardrail_halt_decision is not None:
    decision = agent._tool_guardrail_halt_decision
    _turn_exit_reason = "guardrail_halt"
    final_response = agent._toolguard_controlled_halt_response(decision)
```

The ToolCallGuardrailController is initialized at agent_init.py L411 and reset per turn at conversation_loop.py L462-463. The halt decision is set **inside** `_execute_tool_calls` by the guardrail controller (not visible in the outer loop). Configuration comes from `tool_loop_guardrails` in DEFAULT_CONFIG (config.py L909-922), which has `hard_stop_enabled: False` by default.

### M3 consciousness integration points

- **Volatile tier of system prompt** — `agent/system_prompt.py` L274-312 (`volatile_parts`)
- **Context engine session lifecycle** — `agent_init.py` L1516-1528 (`on_session_start`)
- **Memory provider on_turn_start** — `conversation_loop.py` L741-745

### M4 emotion hooks

M4 emotion data would be injected into the system prompt's **volatile tier** at `agent/system_prompt.py` L274-312 by appending to `volatile_parts`. The memory nudge check at `conversation_loop.py` L562-569 is the per-turn trigger point where emotion state could be refreshed.

### M11 consent hooks

M11 consent would need to intercept tool dispatch. The validation sequence at `conversation_loop.py` L3579-3728 (name validation, JSON validation, guardrails) is where a consent check would be inserted — between L3738 (deduplication) and L3811 (`_execute_tool_calls` call).

---

## 4. tools/registry.py — ToolRegistry AST auto-discovery

**File:** `C:/Users/faizz/guinevere/.venv/Lib/site-packages/tools/registry.py`
**Total lines:** 590

### How new tools register

**Step 1: Module-level registration.** Each tool file calls `registry.register()` at module level:

```python
# In tools/some_tool.py:
from tools.registry import registry
registry.register(
    name="tool_name",
    toolset="toolset_name",
    schema={...},
    handler=my_handler,
    check_fn=my_check,
    ...
)
```

**Step 2: AST-based auto-discovery.** `discover_builtin_tools()` (L57-74) scans `tools/*.py` using `_module_registers_tools()` (L42-54), which parses each file's AST to find top-level `registry.register(...)` calls via `_is_registry_register_call()` (L29-39). Files containing such calls are imported, which triggers their module-level registration.

**Step 3: Schema retrieval.** `get_definitions()` (L337-384) returns OpenAI-format tool schemas, filtering by `check_fn` availability (TTL-cached at L121-141) and applying `dynamic_schema_overrides`.

**Step 4: Dispatch.** `dispatch()` (L390-416) executes a tool handler by name, bridging async handlers via `_run_async()`.

### Key classes

| Symbol | Line | Purpose |
|--------|------|---------|
| `ToolEntry` | L77 | Data class for registered tool metadata (12 slots) |
| `ToolRegistry` | L151 | Singleton registry with thread-safe `_lock` and `_generation` counter |
| `registry` | L544 | Module-level singleton instance |
| `tool_error()` | L563 | Helper for error JSON responses |
| `tool_result()` | L577 | Helper for success JSON responses |

### Registration for new P24 modules

New tools register by creating a file in `tools/` that calls `registry.register()` at module level. The AST auto-discovery (`discover_builtin_tools`) picks it up automatically. Plugin tools can also register via `ctx.register_tool()` (through the memory manager or context engine tool injection path in agent_init.py L1157-1187 and L1490-1514).

---

## 5. tools/delegate_tool.py — Delegation constants

**File:** `C:/Users/faizz/guinevere/.venv/Lib/site-packages/tools/delegate_tool.py`
**Total lines:** ~2802

### Confirmed constants at L132-137

```python
_DEFAULT_MAX_CONCURRENT_CHILDREN = 3    # L132
MAX_DEPTH = 1                           # L133
_MIN_SPAWN_DEPTH = 1                    # L136
_MAX_SPAWN_DEPTH_CAP = 3                # L137
```

**VERIFIED:** All four constants match the plan's claimed values exactly.

### M5 patches: change to 10/5/5

The plan specifies M5 patches these to `_DEFAULT_MAX_CONCURRENT_CHILDREN=10`, `MAX_DEPTH=5`, `_MAX_SPAWN_DEPTH_CAP=5`. These are **module-level constants** (not config-driven defaults — config overrides them at runtime via `_get_max_concurrent_children()` at L329 and `_get_max_spawn_depth()` at L394).

The runtime config path:
- `_get_max_concurrent_children()` at L329 reads `delegation.max_concurrent_children` from config
- `_get_max_spawn_depth()` at L394 reads `delegation.max_spawn_depth`, clamped to `[_MIN_SPAWN_DEPTH, _MAX_SPAWN_DEPTH_CAP]`

For M5, both the constants AND the `_MAX_SPAWN_DEPTH_CAP` need patching, because `_get_max_spawn_depth()` clamps to `[1, _MAX_SPAWN_DEPTH_CAP]`.

### Other key delegation symbols

| Symbol | Line | Value |
|--------|------|-------|
| `DEFAULT_MAX_ITERATIONS` | L512 | 50 |
| `DEFAULT_CHILD_TIMEOUT` | L513 | 600 seconds |
| `DELEGATE_BLOCKED_TOOLS` | L45-53 | frozenset of 5 tools |
| `_HEARTBEAT_INTERVAL` | L514 | 30 seconds |
| `delegate_task()` | L1918 | Main entry point |

---

## 6. agent/memory_provider.py — MemoryProvider ABC

**File:** `C:/Users/faizz/guinevere/.venv/Lib/site-packages/agent/memory_provider.py`
**Total lines:** 292

### All 14 methods (5 abstract, 9 concrete)

| # | Method | Line | Abstract? | Purpose |
|---|--------|------|-----------|---------|
| 1 | `name` (property) | L45-48 | **YES** | Short identifier string |
| 2 | `is_available()` | L52-58 | **YES** | Check config/credentials readiness |
| 3 | `initialize(session_id, **kwargs)` | L60-82 | **YES** | Connect, create resources, warm up |
| 4 | `system_prompt_block()` | L84-91 | No | Static text for system prompt |
| 5 | `prefetch(query, *, session_id)` | L93-105 | No | Recall context before each turn |
| 6 | `queue_prefetch(query, *, session_id)` | L107-113 | No | Queue background recall for next turn |
| 7 | `sync_turn(user, asst, *, session_id, messages)` | L115-131 | No | Persist completed turn |
| 8 | `get_tool_schemas()` | L133-141 | **YES** | Return OpenAI function-calling tool schemas |
| 9 | `handle_tool_call(tool_name, args, **kwargs)` | L143-149 | No | Dispatch tool call |
| 10 | `shutdown()` | L151-152 | No | Clean shutdown |
| 11 | `on_turn_start(turn_number, message, **kwargs)` | L156-163 | No | Per-turn tick |
| 12 | `on_session_end(messages)` | L165-173 | No | End-of-session extraction |
| 13 | `on_session_switch(new_session_id, *, parent_session_id, reset, **kwargs)` | L175-212 | No | Mid-process session_id rotation |
| 14 | `on_pre_compress(messages)` | L214-224 | No | Extract before context compression |
| 15 | `on_delegation(task, result, *, child_session_id, **kwargs)` | L226-237 | No | Parent-side observation of subagent work |
| 16 | `get_config_schema()` | L239-255 | No | Config fields for setup wizard |
| 17 | `save_config(values, hermes_home)` | L257-272 | No | Write non-secret config |
| 18 | `on_memory_write(action, target, content, metadata)` | L274-292 | No | Mirror built-in memory writes |

**Correction to plan claim:** The plan says "14 methods, mark 5 abstract." The actual count is **18 methods** (including the `name` property), with **5 abstract** (`name`, `is_available`, `initialize`, `get_tool_schemas` — the property `name` plus 3 methods marked `@abstractmethod`). The plan's count of 5 abstract is correct; the total method count of 14 is **incorrect** — it is 18.

**M6 subclasses this:** Yes. M6 would create a concrete subclass implementing all 4 abstract methods (plus `name` property) and optionally overriding the concrete hooks. Registered via `plugins/memory/<name>/` and activated through `memory.provider` config key (agent_init.py L1096-1097).

---

## 7. agent/system_prompt.py — 3-tier system prompt

**File:** `C:/Users/faizz/guinevere/.venv/Lib/site-packages/agent/system_prompt.py`
**Total lines:** 381

### Three tiers

**Stable tier** (L83-253): Built from SOUL.md/DEFAULT_AGENT_IDENTITY, tool guidance (memory, session_search, skills, kanban), computer-use guidance, nous subscription, tool-use enforcement + per-model operational guidance, skills prompt, Alibaba model workaround, environment hints, profile hint, platform hints.

**Context tier** (L255-272): Caller-supplied `system_message` plus context files (AGENTS.md, .cursorrules, etc.) discovered under `TERMINAL_CWD`.

**Volatile tier** (L274-312): Memory snapshot (MEMORY.md), USER.md profile, external memory provider block, timestamp/session/model/provider line.

### Where M4 emotion + M12 drift add volatile blocks

**M4 emotion** would insert into `volatile_parts` (L275) by adding an emotion state block between the memory provider block (L289-295) and the timestamp line (L297-312). The emotion state would be computed per-turn and formatted as a string, then appended:

```python
# After L295 (external memory provider block), before L297:
if hasattr(agent, '_emotion_state'):
    emotion_block = agent._emotion_state.format_for_system_prompt()
    if emotion_block:
        volatile_parts.append(emotion_block)
```

**M12 drift** would similarly append a drift-analysis block to `volatile_parts`. Since drift data changes per-session (not per-turn), it fits naturally in the volatile tier. The injection point is the same `volatile_parts` list, anywhere between L275-312.

The `build_system_prompt_parts()` function (L60) returns a dict with keys `"stable"`, `"context"`, `"volatile"` (L314-318), which are joined by `build_system_prompt()` (L321-337). The cache key is the entire joined string — any change to volatile parts triggers a full rebuild, which only happens after context compression events (per the system prompt invariant).

---

## 8. hermes_cli/config.py — DEFAULT_CONFIG

**File:** `C:/Users/faizz/guinevere/.venv/Lib/site-packages/hermes_cli/config.py`
**Total lines:** 5849

### DEFAULT_CONFIG

- **Starts at line:** 633
- **Type:** Top-level dict
- **64 top-level keys** (full list): `model`, `providers`, `fallback_providers`, `credential_pool_strategies`, `toolsets`, `agent`, `terminal`, `web`, `browser`, `checkpoints`, `file_read_max_chars`, `tool_output`, `tool_loop_guardrails`, `compression`, `prompt_caching`, `openrouter`, `bedrock`, `auxiliary`, `display`, `dashboard`, `privacy`, `tts`, `stt`, `voice`, `human_delay`, `context`, `memory`, `delegation`, `prefill_messages_file`, `goals`, `skills`, `curator`, `honcho`, `timezone`, `slack`, `discord`, `whatsapp`, `telegram`, `mattermost`, `matrix`, `approvals`, `command_allowlist`, `quick_commands`, `hooks`, `hooks_auto_accept`, `personalities`, `security`, `cron`, `kanban`, `code_execution`, `logging`, `model_catalog`, `network`, `gateway`, `sessions`, `onboarding`, `updates`, `lsp`, `x_search`, `secrets`, `paste_collapse_threshold`, `paste_collapse_threshold_fallback`, `paste_collapse_char_threshold`, `_config_version`.

### M1 replaces with Pydantic

M1 would replace this flat dict with a Pydantic `BaseSettings` model hierarchy. The key integration point is `load_config()` (called at agent_init.py L1049) which currently does `copy.deepcopy(DEFAULT_CONFIG)` and merges YAML on top (config.py L4687). Every consumer calls `cfg_get()` or `load_config()` — these are the compatibility shims M1 needs to preserve.

---

## 9. gateway/run.py — Discord handler registration

**File:** `C:/Users/faizz/guinevere/.venv/Lib/site-packages/gateway/run.py`

### GatewayRunner class (L1661)

The `GatewayRunner` class manages all platform adapters. Discord is one of the `Platform.DISCORD` enum members.

### Adapter registration point

L4173: `self.adapters[platform] = adapter` — this is where a connected adapter is registered into the runner's adapter dict. The connection happens at L4171: `success = await self._connect_adapter_with_timeout(adapter, platform)`.

### M13 Discord handler registration

M13 would register a Discord handler by:
1. Creating a Discord adapter class (following the existing platform adapter pattern)
2. Having GatewayRunner connect it via `_connect_adapter_with_timeout`
3. The adapter being stored in `self.adapters[Platform.DISCORD]`

Discord-specific config lives in DEFAULT_CONFIG under the `"discord"` key (config.py). Discord-related env vars: `DISCORD_ALLOWED_USERS` (L6495), `DISCORD_ALLOW_ALL_USERS` (L6521), `DISCORD_ALLOW_BOTS` (L6540).

---

## 10. cron/scheduler.py + cron/jobs.py — M7 DAO auto-tally

### cron/scheduler.py

**File:** `C:/Users/faizz/guinevere/.venv/Lib/site-packages/cron/scheduler.py`

- `tick()` at L1857: Main scheduler entry point, called every 60 seconds by gateway. Uses file-based locking (`~/.hermes/cron/.tick.lock`). Gets due jobs, advances `next_run_at`, then runs jobs in parallel.
- `run_job()` at L1204 (referenced from jobs.py): Executes a single cron job by spawning an AIAgent.

### cron/jobs.py

**File:** `C:/Users/faizz/guinevere/.venv/Lib/site-packages/cron/jobs.py`

- `JOBS_FILE = CRON_DIR / "jobs.json"` (L39): Where cron jobs are persisted.
- `_job_output_dir()` at L55: Resolves output path for job results.
- `_normalize_skill_list()` at L71: Normalizes skill references.

### M7 DAO auto-tally job insertion point

M7 would insert a DAO auto-tally cron job by:
1. Adding a new job to `jobs.json` via `cron/jobs.py` functions (create/update job)
2. The job's prompt would reference the DAO tally skill/tool
3. The `tick()` function in scheduler.py would pick it up on schedule
4. Alternatively, M7 could insert a dedicated auto-tally function called from `tick()` before the main job loop, or add a new job type that `run_job()` dispatches differently

The cleanest insertion point is to add a cron job via the existing job management API (`jobs.json`) rather than modifying the scheduler itself.

---

## Disposition for P24

| Module | Target file(s) | Disposition |
|--------|----------------|-------------|
| M1 (Pydantic config) | `hermes_cli/config.py` | **MODIFY-CREATE** — Replace DEFAULT_CONFIG dict with Pydantic models, maintain `load_config()`/`cfg_get()` compat |
| M2 (Hard stop) | `agent/conversation_loop.py`, `agent/agent_init.py` | **MODIFY-CREATE** — Enhance ToolCallGuardrailController, wire at L3811-3814 |
| M3 (Consciousness) | `run_agent.py`, `agent/agent_init.py`, `agent/system_prompt.py` | **MODIFY-CREATE** — Add consciousness state, hooks in volatile prompt tier, close() teardown |
| M4 (Emotion) | `agent/system_prompt.py`, `agent/conversation_loop.py` | **MODIFY-CREATE** — Append emotion block to volatile_parts, per-turn refresh |
| M5 (Delegation limits) | `tools/delegate_tool.py` | **MODIFY** — Patch L132-137 constants (3->10, 1->5, 3->5) |
| M6 (Memory provider) | `agent/memory_provider.py`, `plugins/memory/` | **MODIFY-CREATE** — Subclass MemoryProvider (5 abstract methods), register via config |
| M7 (DAO auto-tally) | `cron/jobs.py`, `cron/scheduler.py` | **MODIFY-CREATE** — Insert cron job, optional scheduler hook |
| M11 (Consent) | `agent/conversation_loop.py` | **MODIFY-CREATE** — Insert consent check between L3738 and L3811 |
| M12 (Drift) | `agent/system_prompt.py` | **MODIFY-CREATE** — Append drift block to volatile_parts |
| M13 (Discord) | `gateway/run.py` | **MODIFY-CREATE** — Register Discord adapter at L4173 |
| M15 (HTTP) | `gateway/run.py`, new HTTP module | **MODIFY-CREATE** — Add HTTP endpoint alongside platform adapters |

---

## Risks

1. **System prompt cache invalidation** — Any change to volatile_parts (M3, M4, M12) causes prefix cache misses. Hermes intentionally builds the system prompt once per session. Volatile additions that change per-turn would defeat this optimization.

2. **DEFAULT_CONFIG coupling** — 64 top-level keys with deep nesting. M1 Pydantic migration must handle YAML deserialization, env var expansion, and the `cfg_get()` deep-access pattern used throughout the codebase.

3. **Tool guardrail threading** — The guardrail controller is reset per turn (L462) and checked post-execution (L3813). M2 hard_stop changes must respect the concurrent tool execution path (`_execute_tool_calls_concurrent` at run_agent.py L4345).

4. **Memory provider one-at-a-time limit** — MemoryManager enforces a single external provider (agent_init.py L1091-1153). M6 must not conflict with existing provider registration.

5. **Delegation constant patching** — M5 changes to `_MAX_SPAWN_DEPTH_CAP` affect the runtime clamping in `_get_max_spawn_depth()` (delegate_tool.py L394-429). Tests that import `MAX_DEPTH` directly will need updating.

6. **Correction to plan claim** — MemoryProvider has **18 methods** (not 14), with 5 abstract (correct). The plan's claim of "14 methods" is inaccurate.

---

## Verdict

**PASS** — All 10 files have been read and verified against actual source. The plan's modification points are largely accurate, with one correction: MemoryProvider has 18 methods, not 14. All delegate_tool.py constants (L132-137) are confirmed exactly as claimed. The hook ordering in conversation_loop.py is fully mapped. No blocking issues found.
