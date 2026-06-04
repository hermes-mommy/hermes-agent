# Plugin Instance Model: GLOBAL vs PER-SESSION

**ADR-035 — Blocker B-004**  
**Date:** 2026-06-04  
**Method:** SSH to guinevere-vps + source-code analysis of `hermes_cli/plugins.py` (1847 lines, v? from site-packages)  
**Status:** RESOLVED

---

## 1. Tests Executed

### Test 1: Plugin CLI surface

```bash
$ hermes plugins --help 2>&1 | head -30
```

<details>
<summary>Output (click to expand)</summary>

```
usage: hermes plugins [-h]
                      {install,update,remove,rm,uninstall,list,ls,enable,disable}
                      ...

Install plugins from Git repositories, update, remove, or list them.

positional arguments:
  {install,update,remove,rm,uninstall,list,ls,enable,disable}
    install             Install a plugin from a Git URL or owner/repo
    update              Pull latest changes for an installed plugin
    remove (rm, uninstall)
                        Remove an installed plugin
    list (ls)           List installed plugins
    enable              Enable a disabled plugin
    disable             Disable a plugin without removing it

options:
  -h, --help            show this help message and exit
```
</details>

```bash
$ hermes plugins list
```

<details>
<summary>Output (click to expand)</summary>

```
                                    Plugins                                     
[...]
│ disk-cleanup        │ not enabled │ 2.0.0   │ Auto-track and clean ...  │ bundled │
│ security-guidance   │ not enabled │ 0.1.0   │ Append security warnings...│ bundled │
│ platforms/discord   │ not enabled │ 1.0.0   │ Discord gateway adapter... │ bundled │
│ observability/langfuse│not enabled│ 1.0.0   │ Optional Langfuse...      │ bundled │
[...]
```

All ~60 bundled plugins show **not enabled** — opt-in by default. Footer text: _"Plugins are opt-in by default — only 'enabled' plugins load."_

</details>

### Test 2: Plugin documentation files

```bash
$ find ~/.hermes -name "*.md" -path "*plugin*" 2>/dev/null | head -10
$ find ~/.hermes -name "PLUGINS*" 2>/dev/null | head -10
```

**Result:** No output — no plugin-specific markdown docs exist in the Hermes home directory.

### Test 3: Package identification

```bash
$ pip list | grep -i hermes
$ pip show hermes-agent
```

**Result:** `hermes-agent` not found as a pip package. Trail led to:

```
/home/guinevere/code/guinevere/.venv/lib/python3.12/site-packages/hermes_cli/plugins.py
```

The actual package is `hermes_cli` (installed as a dependency, not directly pip-installable by that name). The correction was critical — all Python introspection used `hermes_cli.plugins`, not `hermes.plugins`.

### Test 4–6: Source-code introspection (combined)

Instead of `inspect.getsource()` (module not importable via `hermes` name), we read the complete `plugins.py` source (1847 lines) directly:

```bash
$ wc -l /home/guinevere/code/guinevere/.venv/lib/python3.12/site-packages/hermes_cli/plugins.py
1847
```

The complete source was read in 4 chunks (lines 1-100, 100-300, 300-600, 600-1000, 1000-1400, 1400-1847).

---

## 2. Source-Code Analysis

### 2.1 Module-Level Singleton: Decisive Evidence

Lines 1780-1790 of `hermes_cli/plugins.py`:

```python
# ---------------------------------------------------------------------------
# Module-level singleton & convenience functions
# ---------------------------------------------------------------------------

_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """Return (and lazily create) the global PluginManager singleton."""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager
```

**The `PluginManager` is a Python module-level singleton.** There is exactly **one** `PluginManager` instance per Python process. The lazy-init pattern `_plugin_manager` is a global variable — all convenience functions (`discover_plugins`, `invoke_hook`, `get_plugin_commands`, etc.) route through this single instance.

### 2.2 PluginManager Internal State

```python
class PluginManager:
    def __init__(self) -> None:
        self._plugins: Dict[str, LoadedPlugin] = {}       # All plugins, stored once
        self._hooks: Dict[str, List[Callable]] = {}        # Hook callbacks, global
        self._plugin_tool_names: Set[str] = set()          # Global tool set
        self._plugin_platform_names: Set[str] = set()      # Global platform set
        self._cli_commands: Dict[str, dict] = {}           # Global CLI commands
        self._context_engine = None                        # Single instance
        self._plugin_commands: Dict[str, dict] = {}        # Global slash commands
        self._discovered: bool = False                     # Discovery flag
        self._cli_ref = None                               # CLI reference
        self._plugin_skills: Dict[str, Dict[str, Any]] = {}
        self._aux_tasks: Dict[str, Dict[str, Any]] = {}
```

Every data structure in PluginManager is initialized once and shared across all sessions. There is no session-scoped dict, no per-session plugin instance, no session ID in PluginManager.

### 2.3 Plugin Loading: ONE-TIME Registration

```python
def _load_plugin(self, manifest: PluginManifest) -> None:
    """Import a plugin module and call its register(ctx) function."""
    loaded = LoadedPlugin(manifest=manifest)
    ...
    module = self._load_directory_module(manifest)   # Import ONCE
    loaded.module = module

    register_fn = getattr(module, "register", None)
    if register_fn is not None:
        ctx = PluginContext(manifest, self)
        register_fn(ctx)  # Called ONCE
```

Key observations:
- Each plugin module is **imported once** via `importlib.util.module_from_spec()` and stored in `sys.modules`
- `register(ctx)` is called **exactly once** during discovery
- All hooks, tools, commands are registered into global dicts (`self._hooks`, `self._plugin_tool_names`, etc.)
- Python's module cache (`sys.modules`) ensures the module is never reloaded (unless `force=True` is passed)

### 2.4 Hook Lifecycle: Global Registration, Session-Aware Invocation

Available session hooks from `VALID_HOOKS`:

```python
VALID_HOOKS: Set[str] = {
    "on_session_start",
    "on_session_end",
    "on_session_finalize",
    "on_session_reset",
    "pre_tool_call",
    "post_tool_call",
    "pre_llm_call",
    "post_llm_call",
    "transform_llm_output",
    "transform_tool_result",
    "transform_terminal_output",
    "pre_api_request",
    "post_api_request",
    "subagent_stop",
    "pre_gateway_dispatch",
    "pre_approval_request",
    "post_approval_response",
}
```

Hook invocation:

```python
def invoke_hook(self, hook_name: str, **kwargs: Any) -> List[Any]:
    callbacks = self._hooks.get(hook_name, [])
    results = []
    for cb in callbacks:
        try:
            ret = cb(**kwargs)
            if ret is not None:
                results.append(ret)
        except Exception as exc:
            logger.warning(...)
    return results
```

The `**kwargs` pass session context dynamically (e.g., `pre_tool_call` receives `session_id`, `task_id`, `tool_call_id`), but the **callbacks themselves** are stored globally and shared across all sessions.

### 2.5 PluginContext: Per-Registration, Not Per-Session

```python
class PluginContext:
    def __init__(self, manifest: PluginManifest, manager: "PluginManager"):
        self.manifest = manifest
        self._manager = manager
        self._llm: Any = None  # Lazy, host-owned, created once
```

`PluginContext` is created once per plugin during `register()` — not per session. The `ctx.llm` facade (`PluginLlm`) is lazily built on first access and stored indefinitely.

---

## 3. Analysis: GLOBAL or PER-SESSION?

### Verdict: **GLOBAL**

| Aspect | Behavior | Evidence |
|--------|----------|----------|
| PluginManager instance | **Singleton** — one per process | `_plugin_manager` module global, lines 1780-1790 |
| Plugin module import | **Once** per process | `importlib.util.module_from_spec()` + `sys.modules` cache |
| `register(ctx)` call | **Once** during discovery | `_load_plugin()` line ~1410 |
| Hook callbacks | **Global** dict, shared across sessions | `self._hooks: Dict[str, List[Callable]]` |
| PluginContext | **One** per plugin registration | Created in `_load_plugin()`, not per-session |
| PluginLlm facade | **One** per plugin, lazy-built | `self._llm` cached in PluginContext |
| Module-level plugin state | **Persists** across sessions | Python module global variables survive indefinitely |
| Session isolation | **NOT built-in** — plugins must DIY | No session-scoped state in PluginManager |

### What "GLOBAL singleton" means for plugins:

1. A plugin's Python module is imported **once** when Hermes starts
2. Any module-level variables (globals) survive between sessions
3. `register(ctx)` runs once — all hooks/tools are registered globally
4. **No automatic state cleanup between sessions**
5. Plugins must implement their own session-aware state via hook callbacks

### What DOES provide session awareness:

- **`on_session_start` hook**: Plugins receive this call when a session begins; they can build per-session state then
- **`on_session_end` / `on_session_finalize` hooks**: Plugins must clean up their own per-session state
- **`pre_tool_call` receives `session_id`**: Plugins can key their internal state by session ID
- **`PluginContext.inject_message()`** operates on the CLI's current session via `self._manager._cli_ref`

---

## 4. Design Constraint for GuinevereSafetyPlugin

Given the **GLOBAL singleton** model, the `GuinevereSafetyPlugin` must address:

### 4.1 State Isolation

```
MUST implement session-keyed state:
  self._sessions: Dict[str, PluginSessionState] = {}

  def on_session_start(self, session_id: str, ...):
      self._sessions[session_id] = PluginSessionState(...)

  def on_session_end(self, session_id: str, ...):
      self._sessions.pop(session_id, None)
```

**Failure to clean up** `on_session_end`/`on_session_finalize` means state accumulates indefinitely — a memory leak.

### 4.2 Thread Safety

`PluginManager.invoke_hook()` iterates `self._hooks` sequentially — no async/thread safety on the dict access. If Hermes runs multiple sessions concurrently (gateway mode with Discord + Telegram), hook callbacks may be called from different threads. **The plugin must protect its own session-keyed dict with a lock.**

### 4.3 Module-Level vs Session-Level

- **Module-level (safe for singleton):** Configuration, compiled regex patterns, constant lookup tables
- **Session-level (must be keyed):** Safety violation counts, consent state, surveillance flags, persona drift trackers

### 4.4 Plugin Re-Discovery (`force=True`)

`discover_and_load(force=True)` clears ALL state and reimports plugins. If GuinevereSafetyPlugin stores critical state in module globals, it will be **destroyed** on force reload. The plugin should:
- Register a hook for `on_session_finalize` to persist critical state before reload
- Not rely on module globals for anything that must survive a force reload

### 4.5 Simultaneous Sessions (Gateway Mode)

In gateway mode (Discord, Telegram, etc.), multiple sessions may be active simultaneously. The plugin:
- Must NOT use a single global "current session" variable
- Must key ALL per-session state by `session_id`
- Must handle `on_session_start` being called concurrently for different sessions

### 4.6 Sub-Agent Sessions

When Hermes spawns sub-agents via `delegate_task`, each sub-agent may be a separate session. The plugin must decide whether:
- Sub-agents inherit the parent's safety state (shared session context), or
- Each sub-agent gets independent safety tracking (separate `session_id`)

This depends on how Hermes assigns `session_id` to sub-agents — a separate investigation.

---

## 5. Verdict

| Property | Value |
|----------|-------|
| **Instance model** | **GLOBAL singleton** (one PluginManager per Python process) |
| **Plugin modules** | Imported once, cached in `sys.modules` |
| **`register()`** | Called once during discovery |
| **Hook callbacks** | Stored globally; invoked with session context via kwargs |
| **Session isolation** | NOT built-in; plugins must implement their own session-keyed state |
| **State cleanup** | Plugin's responsibility; use `on_session_end`/`on_session_finalize` |
| **Thread safety** | Plugin's responsibility; protect shared dicts with locks |
| **Force reload safety** | Plugin's responsibility; persist state before `on_session_finalize` |

---

## 6. Sources

- **Primary:** `/home/guinevere/code/guinevere/.venv/lib/python3.12/site-packages/hermes_cli/plugins.py` (1847 lines, full read)
- **Secondary:** `hermes plugins --help`, `hermes plugins list`
- **Confidence:** HIGH — source code is definitive and unambiguous

---

## 7. Footer

| Field | Value |
|-------|-------|
| **ADR** | ADR-035 |
| **Blocker** | B-004 |
| **Report** | 03-plugin-isolation.md |
| **Author** | Guinevere (Sisyphus-Junior) |
| **Date** | 2026-06-04 |
| **Next action** | Proceed to B-005: Sub-agent session ID assignment |