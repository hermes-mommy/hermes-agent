# Hermes Phase 1 — Memory Disable Research Report

**Date:** 2026-06-03
**Target:** `guinevere-vps` — Hermes AIAgent memory subsystem
**Goal:** Verify that Hermes AIAgent can have its native memory disabled, enumerate all memory-related parameters, and confirm compatibility with library-mode usage.

---

## 1. AIAgent Constructor Signature — Memory Parameters

### Source: `agent/agent_init.py` (line 195)

The `init_agent()` function accepts `skip_memory: bool = False` as an explicit parameter:

```python
def init_agent(
    agent,
    base_url: str = None,
    api_key: str = None,
    provider: str = None,
    # ... (other params)
    skip_context_files: bool = False,
    load_soul_identity: bool = False,
    skip_memory: bool = False,          # <--- KEY PARAMETER
    session_db=None,
    parent_session_id: str = None,
    # ...
)
```

The wrapper `AIAgent.__init__` (in `run_agent.py`, line 420) passes all parameters verbatim to `init_agent()`.

### Full parameter list (captured via `inspect.signature`):

```
base_url: None
api_key: None
provider: None
api_mode: None
acp_command: None
acp_args: None
command: None
args: None
model: (empty string)
max_iterations: 90
tool_delay: 1.0
enabled_toolsets: None
disabled_toolsets: None
save_trajectories: False
verbose_logging: False
quiet_mode: False
ephemeral_system_prompt: None
log_prefix_chars: 100
log_prefix: (empty string)
providers_allowed: None
providers_ignored: None
providers_order: None
provider_sort: None
provider_require_parameters: False
provider_data_collection: None
openrouter_min_coding_score: None
session_id: None
[callbacks omitted]
max_tokens: None
reasoning_config: None
service_tier: None
request_overrides: None
prefill_messages: None
platform: None
user_id: None
user_id_alt: None
user_name: None
chat_id: None
chat_name: None
chat_type: None
thread_id: None
gateway_session_key: None
skip_context_files: False
load_soul_identity: False
skip_memory: False            # <--- default False, set True to disable
session_db: None
parent_session_id: None
iteration_budget: None
fallback_model: None
credential_pool: None
checkpoints_enabled: False
checkpoint_max_snapshots: 20
checkpoint_max_total_size_mb: 500
checkpoint_max_file_size_mb: 10
pass_session_id: False
```

---

## 2. How `skip_memory=True` Disables Memory (Code-Verified)

### Source: `agent/agent_init.py` lines 1068–1138

Two distinct memory subsystems are both gated by `skip_memory`:

#### 2a. Built-in Memory Store (`_memory_store`)

```python
agent._memory_enabled = False
agent._user_profile_enabled = False
agent._memory_nudge_interval = 10
agent._turns_since_memory = 0
agent._iters_since_skill = 0
if not skip_memory:                                # LINE 1073
    try:
        mem_config = _agent_cfg.get("memory", {})
        agent._memory_enabled = mem_config.get("memory_enabled", False)
        agent._user_profile_enabled = mem_config.get("user_profile_enabled", False)
        agent._memory_nudge_interval = int(mem_config.get("nudge_interval", 10))
        if agent._memory_enabled or agent._user_profile_enabled:
            from tools.memory_tool import MemoryStore
            agent._memory_store = MemoryStore(
                memory_char_limit=mem_config.get("memory_char_limit", 2200),
                user_char_limit=mem_config.get("user_char_limit", 1375),
            )
            agent._memory_store.load_from_disk()
    except Exception:
        pass  # Memory is optional -- don't break agent init
```

**Effect when `skip_memory=True`:** `_memory_enabled`, `_user_profile_enabled` stay `False`; `_memory_store` is never created. The built-in `/memory` tool has no backing store.

#### 2b. External Memory Provider Plugin (`_memory_manager`)

```python
agent._memory_manager = None
if not skip_memory:                                # LINE 1094
    try:
        _mem_provider_name = mem_config.get("provider", "") if mem_config else ""
        if _mem_provider_name and _mem_provider_name.strip():
            from agent.memory_manager import MemoryManager
            from plugins.memory import load_memory_provider
            agent._memory_manager = MemoryManager()
            _mp = load_memory_provider(_mem_provider_name)
            if _mp and _mp.is_available():
                agent._memory_manager.add_provider(_mp)
            # ... provider init with session/user/chat scoping
    except Exception:
        pass
```

**Effect when `skip_memory=True`:** `_memory_manager` stays `None`. No external provider (honcho, mem0, supermemory, etc.) is loaded. All downstream code in `conversation_loop.py`, `system_prompt.py`, and `memory_manager.py` that checks `if agent._memory_manager:` short-circuits.

### Verification: Attribute States with `skip_memory=True`

> **Note:** AIAgent instantiation requires a properly configured LLM provider (API key). The VPS installation does not have a provider configured for the `agent` package scope — `hermes_cli.config.cfg_get()` returns None for all keys. Therefore runtime instantiation was blocked before memory init. The code paths are definitive based on source analysis.

| Attribute | skip_memory=False (default) | skip_memory=True |
|---|---|---|
| `_memory_enabled` | From config (default: False) | **False** |
| `_user_profile_enabled` | From config (default: False) | **False** |
| `_memory_nudge_interval` | From config (default: 10) | **10** (unused) |
| `_memory_store` | MemoryStore instance | **None** |
| `_memory_manager` | MemoryManager (if provider configured) | **None** |
| Memory in system prompt | Built from MemoryManager | **Not injected** |
| Memory prefetch per turn | On if _memory_manager set | **Skipped** |
| Memory sync per turn | On if _memory_manager set | **Skipped** |

---

## 3. All Memory-Related Configuration Parameters

From `agent_init.py` config resolution and `memory_provider.py` class:

### Built-in memory config (from Hermes config.yaml → `memory:` section):

| Key | Type | Default | Description |
|---|---|---|---|
| `memory.memory_enabled` | bool | false | Enable built-in `/memory` tool |
| `memory.user_profile_enabled` | bool | false | Enable user profile tracking |
| `memory.nudge_interval` | int | 10 | Turns between memory nudge prompts |
| `memory.memory_char_limit` | int | 2200 | Max characters per memory entry |
| `memory.user_char_limit` | int | 1375 | Max characters per user profile entry |
| `memory.provider` | str | "" | External memory provider plugin name |

### Internal agent attributes (set during `init_agent`):

| Attribute | Type | Purpose |
|---|---|---|
| `skip_memory` | bool | Constructor param; gates all memory init |
| `_memory_enabled` | bool | Whether built-in `/memory` tool works |
| `_user_profile_enabled` | bool | Whether user profile tracking is active |
| `_memory_nudge_interval` | int | Frequency of memory nudge prompts |
| `_turns_since_memory` | int | Counter for nudge scheduling |
| `_memory_store` | MemoryStore or None | Built-in memory persistence layer |
| `_memory_manager` | MemoryManager or None | External plugin memory manager |

### External memory provider plugin interface (`MemoryProvider` base class hooks):

| Method | When Called | Purpose |
|---|---|---|
| `is_available()` | Init | Validate provider can connect |
| `build_system_prompt()` | System prompt assembly | Inject memory context |
| `on_turn_start(turn_count, message)` | Each user turn | Pre-turn processing |
| `prefetch_all(query)` | Before LLM inference | Retrieve relevant memories |
| `sync_all(user_msg, assistant_resp)` | After LLM response | Persist conversation |
| `queue_prefetch_all(user_msg)` | Async prefetch | Background memory retrieval |
| `on_pre_compress(messages)` | Before context compression | Extract insights before compression |
| `on_delegation(task, result, child_session_id)` | Subagent completion | Parent learns about delegation |
| `on_memory_write(action, target, content, metadata)` | Built-in memory write | Mirror to external backend |
| `get_config_schema()` | Setup | Return config fields |
| `save_config(values, hermes_home)` | Setup | Write config to disk |

---

## 4. How Downstream Code Honors `_memory_manager = None`

All memory integration points use guard checks on `_memory_manager`:

### `conversation_loop.py` (lines 740, 753):
```python
if agent._memory_manager:                              # guard
    agent._memory_manager.on_turn_start(...)

if agent._memory_manager:                              # guard
    _ext_prefetch_cache = agent._memory_manager.prefetch_all(_query) or ""
```

### `system_prompt.py` (line 289):
```python
if agent._memory_manager:                              # guard
    _ext_mem_block = agent._memory_manager.build_system_prompt()
```

### `background_review.py` (line 415):
```python
skip_memory=True,   # hardcoded in subagent creation
```

### `curator.py` (line 1725):
```python
skip_memory=True,   # hardcoded in curator subagent
```

Any consumed memory provider is fully isolated. The `MemoryProvider` base class explicitly documents at `memory_provider.py` line 232:

> "The subagent itself has no provider session (skip_memory=True)."

---

## 5. Hermes Config.yaml on VPS — Library-Mode Compatibility

### VPS config location: `/home/guinevere/config/hermes/config.yaml`

```yaml
agent:
  name: "Guinevere"
  version: "0.1.0"
  identity: "Guinevere de Baroque"
  description: "Autonomous AI companion and engineering agent"

llm:
  primary:
    provider: "9router"
    model: "gpt-5.5"
    base_url: "http://localhost:20128/v1"
    max_tokens: 16384
    temperature: 0.7
    context_window: 1000000
  sub_agent:
    provider: "9router"
    model: "deepseek-v4-flash"
    base_url: "http://localhost:20128/v1"
    max_tokens: 8192
    temperature: 0.5

memory:
  backend: "postgresql"
  database: "guinevere"
  schema: "memory"
  redis_cache: true
  redis_db: 3
  embedding_model: "text-embedding-3-small"
  embedding_dimensions: 1536
  max_recall_items: 20
  context_injection: true

# loop, safety, budget, tools, messaging, monitoring sections omitted for brevity
```

### Key findings:

1. **config.yaml is NOT the Hermes CLI config** — `hermes_cli.config.cfg_get()` returned `None` for all queried keys (`llm.provider`, `memory.provider`, `memory.memory_enabled`, etc.). This means the Hermes `agent` package looks for its config in the standard Hermes location (`~/.hermes/config.yaml` or `$HERMES_HOME`), not at `/home/guinevere/config/hermes/config.yaml`.

2. **Config structure is Guinevere-specific** — The YAML has a `memory:` section but with a different schema (PostgreSQL backend, Redis cache, embedding model) than what Hermes expects (which uses `memory.memory_enabled`, `memory.provider`, etc.). This config appears designed for a custom memory layer, not the built-in Hermes memory subsystem.

3. **Library-mode compatibility** — Since the `agent` package reads its config via `_agent_cfg = cfg_get()` which fails to resolve these custom config keys, running AIAgent in library-mode would:
   - Fall back to defaults (`_memory_enabled=False`, `_memory_manager=None`)
   - Skip both built-in and external memory automatically
   - **OR**: Accept explicit `skip_memory=True` for guaranteed disable

4. **Provider resolution blocks instantiation** — To instantiate AIAgent on the VPS, a valid provider+API key is needed through Hermes CLI config (`~/.hermes/config.yaml` or `hermes model` command). The current `config/hermes/config.yaml` structure with `llm.primary.provider: 9router` is not recognized by Hermes CLI's `cfg_get()` because it expects different key paths.

### Directory listing of `/home/guinevere/config/hermes/`:
```
total 36
drwxr-x--- 2 guinevere guinevere  4096 Jun  1 08:58 .
drwxr-x--- 9 guinevere guinevere  4096 May 31 19:55 ..
-rw-rw-r-- 1 guinevere guinevere  1853 Jun  1 08:37 config.yaml
-rw-rw-r-- 1 guinevere guinevere 23942 Jun  1 08:58 system-prompt.md
```

---

## 6. All `skip_memory` Usage Sites in Hermes Source

| File | Line | Usage |
|---|---|---|
| `agent/agent_init.py` | 195 | Parameter declaration: `skip_memory: bool = False` |
| `agent/agent_init.py` | 1073 | Gate for built-in memory store init |
| `agent/agent_init.py` | 1094 | Gate for external memory provider plugin init |
| `agent/memory_provider.py` | 232 | Docstring: subagent has no provider session |
| `agent/background_review.py` | 384 | Docstring: explains why fork uses skip_memory=True |
| `agent/background_review.py` | 415 | Subagent creation: `skip_memory=True` |
| `agent/background_review.py` | 496 | `shutdown_memory_provider()` for review agent |
| `agent/background_review.py` | 545 | `shutdown_memory_provider()` (cleanup path) |
| `agent/curator.py` | 1725 | Curator subagent: `skip_memory=True` |

---

## 7. Conclusions

| Question | Answer |
|---|---|
| Does `skip_memory=True` work in AIAgent constructor? | **Yes** — confirmed via source code. Parameter is declared at line 195 of `agent_init.py`. Both memory subsystems are gated by `if not skip_memory:`. |
| Can `memory_provider` be None/disabled? | **Yes** — `_memory_manager` is initialized to `None` and stays `None` when `skip_memory=True`. All downstream code guards on `if agent._memory_manager:`. |
| Does AIAgent remember details across calls when `skip_memory=True`? | **Not via memory subsystem** — both `_memory_store` and `_memory_manager` are skipped. LLM context retention via conversation history still works. |
| Is the VPS Hermes config compatible with library-mode? | **Partially** — config uses custom key layout not recognized by Hermes CLI's `cfg_get()`. The `agent` package defaults to no memory. Provider config needs injection via Hermes CLI setup or explicit constructor args. |
| What memory parameters exist? | `skip_memory`, `_memory_enabled`, `_user_profile_enabled`, `_memory_nudge_interval`, `_memory_store`, `_memory_manager`, plus config values: `memory.memory_enabled`, `memory.user_profile_enabled`, `memory.nudge_interval`, `memory.memory_char_limit`, `memory.user_char_limit`, `memory.provider`. |

### Recommendation for library-mode memory disable:

```python
from run_agent import AIAgent

agent = AIAgent(
    base_url="http://localhost:20128/v1",
    provider="9router",
    model="ds/deepseek-v4-flash",
    api_key="<key>",           # required for provider resolution
    quiet_mode=True,
    skip_memory=True,          # disables ALL memory subsystems
    skip_context_files=True,
)
```

This guarantees:
- `_memory_manager` = None (no external memory plugin)
- `_memory_store` = None (no built-in /memory tool)
- `_memory_enabled` = False
- Zero memory context injected into system prompt
- Zero memory prefetch/sync per turn

---

## 8. Commands Executed

All commands were run via SSH on `guinevere-vps`:

```bash
# Activate venv
cd /home/guinevere/code/guinevere && source .venv/bin/activate

# Inspect AIAgent signature
python -c "from run_agent import AIAgent; import inspect; sig = inspect.signature(AIAgent.__init__); [print(f'{name}: {param.default if param.default is not inspect.Parameter.empty else \"(required)\"}') for name, param in sig.parameters.items() if name != 'self']"

# Check memory config handling source
sed -n '1068,1138p' /home/guinevere/code/guinevere/.venv/lib/python3.12/site-packages/agent/agent_init.py

# Grep memory-related code
grep -rn "memory_provider\|enable_memory\|use_memory\|skip_memory\|memory_manager" /home/guinevere/code/guinevere/.venv/lib/python3.12/site-packages/agent/ 2>/dev/null | head -20

# Read VPS config
cat /home/guinevere/config/hermes/config.yaml

# Check config resolution
python -c "from hermes_cli.config import cfg_get; print(cfg_get('memory.provider')); print(cfg_get('llm.primary.provider'))"
```

### Cannot-test notes:

A full end-to-end chat recall test (inject "favorite color is blue" then ask "what is my favorite color?") could not be performed because the VPS Hermes installation lacks a configured LLM provider in the Hermes CLI scope. The provider resolution in `agent_init.py` (lines 780–860) requires either:
- A valid API key in env vars or Hermes CLI config (`~/.hermes/config.yaml`)
- A fallback provider with credentials

The Guinevere-specific config at `/home/guinevere/config/hermes/config.yaml` uses a custom key layout not recognized by `hermes_cli.config.cfg_get()`. This is expected to be resolved in Phase 2 where the library-mode provider injection is implemented.
