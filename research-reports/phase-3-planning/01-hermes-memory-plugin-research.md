# Hermes Agent Memory Plugin Architecture Research

**Date**: 2026-06-04  
**Target**: Phase 3 Memory Bridge Migration (ADR-035)  
**Source**: [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) (v0.2.0+)  

---

## 1. Overview

Hermes Agent uses a **pluggable memory provider system** that allows external memory backends to integrate seamlessly alongside the always-on built-in memory (`MEMORY.md` / `USER.md`). The architecture is managed by a central `MemoryManager` and enforces a **single external provider limit** to prevent tool schema bloat and conflicting backends.

To refactor `memory_bridge.py` into a Hermes memory plugin, the new module must implement the `MemoryProvider` abstract base class and follow the standardized lifecycle hooks, config management, and threading contracts.

---

## 2. Plugin Interface (`MemoryProvider` ABC)

The plugin must inherit from `agent.memory_provider.MemoryProvider`. Below are the required and optional methods.

### 2.1 Required Methods

| Method | Signature | Purpose |
|--------|-----------|---------|
| `name` | `@property def name(self) -> str:` | Provider identifier (e.g., `"guinevere-memory"`). |
| `is_available` | `def is_available(self) -> bool:` | Check if provider can activate. **MUST NOT make network calls.** Check env vars or local file existence. |
| `initialize` | `def initialize(self, session_id: str, **kwargs) -> None:` | Called once at agent startup. `kwargs` always includes `hermes_home` (str) for profile-isolated storage paths. |
| `get_tool_schemas` | `def get_tool_schemas(self) -> list:` | Return OpenAI function-calling format schemas for tools to expose to the LLM. |
| `handle_tool_call` | `def handle_tool_call(self, name: str, args: dict, **kwargs) -> str:` | Dispatch and handle tool calls. Must return a JSON-formatted result string. |
| `get_config_schema` | `def get_config_schema(self) -> list:` | Declare config fields for the `hermes memory setup` wizard. |
| `save_config` | `def save_config(self, values: dict, hermes_home: str) -> None:` | Write non-secret config to native location (e.g., `$HERMES_HOME/guinevere-memory.json`). |

### 2.2 Optional Lifecycle Hooks

| Hook | Signature | When Called | Use Case for Memory Bridge |
|------|-----------|-------------|----------------------------|
| `system_prompt_block` | `def system_prompt_block(self) -> str:` | System prompt assembly | Inject static provider capabilities into the system prompt. |
| `prefetch` | `def prefetch(self, query: str, *, session_id: str = "") -> str:` | Before each API call | Recall relevant context for the current turn. Injected into the user message. |
| `queue_prefetch` | `def queue_prefetch(self, query: str) -> None:` | After each turn | Pre-warm background recall for the next turn. |
| `sync_turn` | `def sync_turn(self, user: str, assistant: str, *, session_id: str = "") -> None:` | After each completed turn | Persist conversation. **MUST be non-blocking** (use daemon threads for network I/O). |
| `on_session_end` | `def on_session_end(self, messages: list) -> None:` | Conversation ends | Final extraction, flush, or session summary retention. |
| `on_pre_compress` | `def on_pre_compress(self, messages: list) -> str:` | Before context compression | Save insights about to be discarded so they aren't lost from memory. |
| `on_memory_write` | `def on_memory_write(self, action: str, target: str, content: str, metadata: dict = None) -> None:` | Built-in memory writes | Mirror built-in `MEMORY.md`/`USER.md` writes to the external backend. |
| `shutdown` | `def shutdown(self) -> None:` | Process exit | Clean up connections, close DBs, flush buffers. |

---

## 3. Configuration Schema Pattern

The `get_config_schema()` method returns a list of field descriptors used by the `hermes memory setup` wizard.

```python
def get_config_schema(self) -> list:
    return [
        {
            "key": "api_key",
            "description": "Guinevere Memory API key",
            "secret": True,           # Written to .env
            "required": True,
            "env_var": "GUINEVERE_MEMORY_API_KEY",
            "url": "https://guinevere.example.com/keys",
        },
        {
            "key": "db_path",
            "description": "Local SQLite database path",
            "default": "guinevere_memory.db",
        },
        {
            "key": "compression_enabled",
            "description": "Enable built-in compression before storage",
            "default": True,
            "choices": [True, False],
        }
    ]
```

**Rules**:
- Fields with `"secret": True` and `"env_var"` are written to `$HERMES_HOME/.env`.
- Non-secret fields are passed to `save_config(values, hermes_home)`.
- Keep the schema minimal. Document advanced optional settings in a `README.md` config reference rather than prompting for them all during setup.

---

## 4. Directory Structure & Registration

The plugin must be self-contained under `plugins/memory/<name>/`:

```text
plugins/memory/guinevere-memory/
├── __init__.py      # MemoryProvider implementation + register() entry point
├── plugin.yaml      # Metadata, pip_dependencies, hooks list
├── README.md        # Setup instructions, config reference, tools table
└── (optional)       # Supporting modules (client.py, store.py, compressor.py)
```

### 4.1 `plugin.yaml`
```yaml
name: guinevere-memory
version: 1.0.0
description: "Guinevere Phase 3 Memory Bridge Plugin for Hermes Agent"
pip_dependencies:
  - "sqlite-utils>=3.36"
  - "pydantic>=2.0"
hooks:
  - prefetch
  - sync_turn
  - on_session_end
  - on_pre_compress
  - on_memory_write
```

### 4.2 Entry Point (`__init__.py`)
```python
from agent.memory_provider import MemoryProvider

class GuinevereMemoryProvider(MemoryProvider):
    # ... implementation ...
    pass

def register(ctx) -> None:
    """Called by the memory plugin discovery system."""
    ctx.register_memory_provider(GuinevereMemoryProvider())
```

---

## 5. Service Registry & Dependency Injection

- **Registry**: `agent.memory_manager.MemoryManager` orchestrates built-in + one external provider.
- **Discovery**: Scans `plugins/memory/` at runtime via a dedicated scanner (`load_memory_provider(name)`).
- **Single Provider Rule**: `MemoryManager.add_provider()` accepts unlimited `"builtin"` providers but **only ONE non-builtin**. A second attempt is rejected with a warning pointing to `memory.provider` in `config.yaml`.
- **Integration Points in `run_agent.py`**:
  1. **Init**: Creates `MemoryManager`, loads provider matching `memory.provider` config.
  2. **Tool Injection**: Appends provider tool schemas to `self.tools` and `self.valid_tool_names`.
  3. **System Prompt**: Adds provider's `system_prompt_block()`.
  4. **Tool Routing**: Routes provider tool calls through `memory_manager.handle_tool_call()`.
  5. **Memory Bridge**: Calls `on_memory_write()` to notify external provider of built-in memory writes.
  6. **Pre-compress**: Calls `on_pre_compress()` before context compression.
  7. **Prefetch**: Injects `prefetch_all()` result into current-turn user message.
  8. **Turn Sync**: `sync_all()` + `queue_prefetch_all()` after response.
  9. **Session End**: `on_session_end()` + `shutdown_all()`.

---

## 6. Built-in Compression, FTS, and Session Search

- **Context Compression**: Hermes has a built-in context compressor. The `on_pre_compress(messages)` hook is triggered *before* compression, allowing the plugin to extract and save insights that would otherwise be discarded.
- **Full-Text Search (FTS)**: Hermes does not enforce a specific FTS engine on plugins. Providers like Hindsight and Supermemory implement their own hybrid search (Vector + BM25 + Reranking). The plugin is responsible for its own search logic, exposed via the `prefetch` hook or custom tools.
- **Session Search**: Managed via the `session_id` passed to `initialize()` and optional hooks. Plugins should scope their storage/retrieval by `session_id` or `hermes_home` to ensure profile isolation.

---

## 7. Threading Contract (CRITICAL)

- **`sync_turn()` MUST be non-blocking.** If the backend has latency (API calls, LLM processing, DB writes), the work **must** be wrapped in a daemon thread with join-before-new-thread guards.
- Blocking the main agent loop during `sync_turn` will cause severe performance degradation and timeout failures.

```python
import threading

def sync_turn(self, user: str, assistant: str, *, session_id: str = "") -> None:
    def _async_sync():
        # Perform network I/O or heavy DB writes here
        pass
    
    thread = threading.Thread(target=_async_sync, daemon=True)
    thread.start()
```

---

## 8. Actionable Recommendations for Phase 3 Refactor (Step 1)

1. **Map Existing Methods**:
   - `recall_for_context()` → `prefetch(query, session_id=session_id)` + custom tool schemas via `get_tool_schemas()`.
   - `store_conversation()` → `sync_turn(user, assistant, session_id=session_id)` (ensure daemon thread implementation).
2. **Create Plugin Scaffold**:
   - Create `plugins/memory/guinevere-memory/` directory structure.
   - Implement `GuinevereMemoryProvider` inheriting from `MemoryProvider`.
   - Define `plugin.yaml` with required hooks.
3. **Config Migration**:
   - Map existing bridge config to `get_config_schema()`.
   - Implement `save_config()` to write to `$HERMES_HOME/guinevere-memory.json`.
4. **Compression Integration**:
   - Implement `on_pre_compress(messages)` to capture pre-compression state, replacing any ad-hoc compression logic in the old bridge.
5. **Profile Isolation**:
   - Ensure all file paths use `kwargs.get("hermes_home")` from `initialize()`, **not** hardcoded `~/.hermes` or absolute paths.

---

## 9. Evidence & References

- [Memory Provider Plugins Developer Guide](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/memory-provider-plugin.md)
- [MemoryProvider ABC Source](https://github.com/NousResearch/hermes-agent/blob/main/agent/memory_provider.py)
- [Pluggable Memory Provider PR #4154](https://github.com/NousResearch/hermes-agent/pull/4154)
- [Hindsight Plugin Example](https://github.com/NousResearch/hermes-agent/blob/main/plugins/memory/hindsight/README.md)
