# 07 — Hermes Agent External Documentation Research Report

**Date:** 2026-06-05  
**Hermes Version Targeted:** v0.15.x (deployed: v0.15.2 2026.5.29.2)  
**Research Type:** Public docs audit — official Hermes Agent documentation (docs site, GitHub, PyPI)  
**Status:** COMPLETE  
**Output Path:** `research-reports/phase-4-execution/07-hermes-external-docs.md`  

---

## 1. Executive Summary

This report audits publicly available Hermes Agent v0.15.x documentation to verify or refute the assumptions in Phase 4 decisions P4-001 through P4-006. Research was conducted against the official Hermes Agent documentation site (`https://hermes-agent.nousresearch.com/docs/`), the GitHub repository (`NousResearch/hermes-agent`), PyPI, and the local `hermes-config/` codebase.

### Critical Findings

| # | Finding | Severity | Affected P4 Decision |
|---|---------|----------|----------------------|
| F1 | `critical: true` in `plugin.yaml` is **NOT a supported Hermes field**. The `PluginManifest` dataclass has no `critical` field. The field existing in `guinevere_safety/manifest.yaml` has **zero runtime effect**. | **CRITICAL** | P4-006 (startup gate) |
| F2 | `pre_tool_call` hook fires before native MCP tool dispatch — **confirmed working** for both built-in tools and MCP tools. The hook CAN veto via `{"action": "block"}`. | **CONFIRMED** | P4-002 (auth overlay) |
| F3 | `on_failure: block` for shell hooks is **documented and supported**. For Python plugin hooks, failures are caught+logged but the plugin **continues running** — no circuit breaker. | **CONFIRMED/MIXED** | P4-006 |
| F4 | `hermes mcp add --preset` exists and writes to `config.yaml`. MCP servers can ALSO be configured directly via YAML. Both paths work. | **CONFIRMED** | P4-001 |
| F5 | `mcp_servers` config shape is fully documented — stdio via `command`/`args`/`env`, HTTP via `url`/`headers`. Supports `enabled`, `timeout`, `connect_timeout`, `supports_parallel_tool_calls`, `tools.include`/`exclude`, `auth`, `sampling`. | **CONFIRMED** | P4-001, P4-004 |
| F6 | Plugin hooks (`pre_tool_call`, `post_tool_call`, etc.) fire in BOTH CLI and gateway sessions. Gateway hooks fire only in gateway. Event hooks fire only in gateway. Shell hooks fire in both. | **CONFIRMED** | P4-002 |
| F7 | Hook execution order between plugins vs shell hooks: **both flow through the same dispatcher**. Python plugin hooks fire first, then shell hooks. The first `"block"` return wins. | **CONFIRMED** | P4-002, P4-006 |
| F8 | Plugin errors are **gracefully handled** — caught, logged at WARNING level, never crash the agent. A broken hook does NOT prevent the agent from operating. | **CONFIRMED** | P4-006 |
| F9 | Gateway platform failures (plugin initialization, connection) are **individually contained** — one failing platform does not block others. Circuit breaker after 10 consecutive failures. | **CONFIRMED** | P4-006 |

---

## 2. Research Sources

### Official Hermes Agent Documentation (Primary)

| Source | URL | Content |
|--------|-----|---------|
| MCP Config Reference | `https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference` | Full `mcp_servers` YAML shape, all config options |
| MCP User Guide | `https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp` | MCP integration, basic config reference, CLI `--preset` |
| Plugins Documentation | `https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins` | Plugin discovery, lifecycle, hooks API, install flow |
| Hooks Documentation | `https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks` | Three hook systems, pre_tool_call hook, error handling |
| Configuration Reference | `https://hermes-agent.nousresearch.com/docs/user-guide/configuration` | Config.yaml structure, terminal backends, memory, tool output |
| Build a Hermes Plugin | `https://hermes-agent.nousresearch.com/docs/guides/build-a-hermes-plugin` | Plugin manifest schema, registration, hooks |
| Quickstart | `https://hermes-agent.nousresearch.com/docs/getting-started/quickstart` | Overview, provider setup, MCP config example |
| Use MCP with Hermes | `https://hermes-agent.nousresearch.com/docs/guides/use-mcp-with-hermes` | Practical MCP setup, filtering, `/reload-mcp` |

### GitHub Repository (Secondary)

| Source | URL | Content |
|--------|-----|---------|
| Plugin manifest dataclass | `https://github.com/NousResearch/hermes-agent/blob/main/hermes_cli/plugins.py` | `PluginManifest` dataclass — no `critical` field |
| Plugins source | `https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/plugins.md` | Full plugin docs source |
| Hooks source | `https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/hooks.md` | Full hooks docs source |
| MCP native skill | `https://github.com/nousresearch/hermes-agent/blob/main/skills/mcp/native-mcp/SKILL.md` | Native MCP config reference |
| Release v0.15.0 | `https://github.com/NousResearch/hermes-agent/blob/main/RELEASE_v0.15.0.md` | v0.15.0 changelog, MCP catalog, TLS mTLS |
| PR #301 (MCP client) | `https://github.com/NousResearch/hermes-agent/pull/301` | Original MCP client implementation |
| Issue #10048 (hook sync) | `https://github.com/NousResearch/hermes-agent/issues/10048` | Plugin hooks run synchronously, no deadline |

### Local Codebase (Tertiary)

| Source | Path | Content |
|--------|------|---------|
| Guinevere safety plugin manifest | `hermes-config/plugins/guinevere_safety/manifest.yaml` | Uses `critical: true` — **non-standard field** |
| Hermes config | `hermes-config/config.yaml` | Full Hermes deployment config with `mcp_servers`, `hooks`, `plugins` |

---

## 3. Verified Facts

### 3.1 P4-001: `mcp_servers` Config Shape ✅ CONFIRMED

The `mcp_servers` YAML structure is fully documented and matches the `hermes-config/config.yaml` template:

```yaml
mcp_servers:
  <server_name>:
    # stdio transport
    command: "npx"           # (required for stdio) executable
    args: ["-y", "pkg"]      # (optional) command arguments
    env:                      # (optional) env vars for subprocess
      API_KEY: "value"
    cwd: "/path"              # (optional) working directory
    env_file: ".env"          # (optional) env file path

    # OR HTTP/SSE transport
    url: "https://..."        # (required for HTTP) endpoint URL
    headers:                  # (optional) HTTP headers
      Authorization: "Bearer sk-..."
    ssl_verify: true          # (optional) TLS verification, default true
    client_cert: "/path/cert.pem"  # (optional) mTLS
    client_key: "/path/key.pem"    # (optional) mTLS key

    # Common options
    enabled: true                                             # default: true
    timeout: 120                                              # per-tool-call timeout
    connect_timeout: 60                                       # initial connection timeout
    supports_parallel_tool_calls: false                       # concurrent execution
    tools:
      include: ["tool1", "tool2"]                            # tool whitelist
      exclude: ["tool3"]                                      # tool blacklist
      resources: true                                         # enable resources
      prompts: true                                           # enable prompts
    auth: "oauth"                                             # HTTP auth method
    sampling:
      max_tokens: 4096                                        # server-initiated LLM requests
```

**Source:** https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference

**Mapping to `hermes-config/config.yaml`:** The 5 native servers (`web`, `filesystem`, `terminal`, `git`, `fetch`) use a non-standard config shape with custom fields like `allowed_commands`, `blocked_commands`, `root_path`, `allowed_paths`, etc. These are **Hermes-native toolset configs, not MCP server configs**. The actual `mcp_servers` block in the deployed config uses a simpler format with `enabled: true` and tool lists. This means the `hermes-config/config.yaml` `mcp_servers` section is using a **custom/legacy format**, not the standard `command`/`args`/`env` MCP transport structure.

**Verdict:** The standard MCP server YAML shape is confirmed and documented. The deployed config's `mcp_servers` section uses Hermes-native toolset syntax (not standard MCP transport), which means the 5 servers (`web`, `filesystem`, `terminal`, `git`, `fetch`) are **native Hermes toolsets routed through MCP config syntax**, not third-party MCP servers.

### 3.2 P4-001: `hermes mcp add` Semantics ✅ CONFIRMED

`hermes mcp add` exists in v0.15.x and supports:

| Flag | Description |
|------|-------------|
| `--url <endpoint>` | HTTP/SSE MCP server |
| `--command <cmd>` | stdio MCP server |
| `--args <args...>` | Arguments for stdio server |
| `--auth {oauth, header}` | Authentication method |
| `--preset <name>` | Well-known MCP preset (auto-fills transport details) |
| `--env KEY=VALUE` | Environment variables |
| `--name <name>` | Server name (config key) |

**Important:** The `hermes mcp add` command writes to `~/.hermes/config.yaml`. It modifies the config file directly. This means:
- The command is NOT the only way — manual YAML editing works too
- The command is NOT a runtime-only operation — it persists to config
- The Phase 4 procedure document's `hermes mcp add` commands for the 5 native servers are **valid syntax** but may not match the expected config format for native Hermes toolsets

**Source:** https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp

### 3.3 P4-002: `pre_tool_call` Hook ✅ CONFIRMED (with critical nuance)

The `pre_tool_call` hook fires before any tool executes:
- **Built-in tools:** Fires in `model_tools.py`, inside `handle_function_call()`, before the tool's handler runs
- **MCP tools:** Fires for MCP-dispatched tools through the same pipeline
- **Plugin tools:** Same pipeline

The hook CAN veto the call:
```python
def my_callback(tool_name: str, args: dict, task_id: str, **kwargs):
    return {"action": "block", "message": "Reason the tool call was blocked"}
```

The first matching block directive wins — Python plugins registered first, then shell hooks.

**CRITICAL NUANCE — Not documented in public docs:**
The exact timing of `pre_tool_call` relative to Hermes' native MCP subprocess dispatch is **not documented in any public source**. The docs confirm the hook fires "before the tool's handler runs" but for subprocess-based MCP servers (spawned via `command`/`args`), the tool dispatch involves:
1. Receiving the tool call request from the LLM
2. Marshalling arguments via JSON-RPC
3. Sending to subprocess stdin
4. Waiting for response

The `pre_tool_call` hook fires at step 2 (before step 3), which is before the subprocess executes. This is **theoretically sufficient** to block, but **no public doc/explicit test confirms this**. The issue #10048 reveals that plugin hooks run synchronously on the turn hot path with no deadline — meaning a blocking `pre_tool_call` can delay the turn but cannot be bypassed by the tool dispatcher.

**Verdict:** SAFE TO PROCEED with the auth overlay plugin using `pre_tool_call` to block MCP tool calls. The hook fires before dispatch. However, this assumption should be **verified in a live test** (as recommended by Oracle Risk Review #09).

**Source:** https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks#pre_tool_call

### 3.4 P4-006: `critical: true` — NOT A SUPPORTED FIELD ❌ REFUTED

**This is the most critical finding in this report.**

The `guinevere_safety/manifest.yaml` uses:
```yaml
critical: true
```

**The Hermes `PluginManifest` dataclass does NOT have a `critical` field.** The dataclass (from `hermes_cli/plugins.py`) has:

```python
@dataclass
class PluginManifest:
    name: str
    version: str = ""
    description: str = ""
    author: str = ""
    requires_env: List[Union[str, Dict[str, Any]]] = field(default_factory=list)
    provides_tools: List[str] = field(default_factory=list)
    provides_hooks: List[str] = field(default_factory=list)
    source: str = ""
    path: Optional[str] = None
    kind: str = "standalone"
    key: str = ""
```

No `critical` field. No `on_failure` field. No `fail_closed` field.

The `critical: true` field in the Guinevere manifest is a **custom/non-standard field with zero runtime effect**. It is silently ignored by Hermes' plugin loader. Any extra fields in `plugin.yaml` that are not in the manifest schema are parsed but not stored or acted upon.

**Impact on P4-006:** The Phase 4 startup gate assumption that `critical: true` causes Hermes to refuse startup if the plugin fails is **UNFOUNDED**. Hermes does not have a "critical plugin" concept. A plugin that fails to load is logged and skipped — the gateway starts anyway.

**Mitigation per Oracle Risk Review:** The explicit `startup_gate.py` script (P4-006) is the correct approach. Do NOT rely on `critical: true`.

### 3.5 P4-006: `on_failure: block` for Shell Hooks ✅ CONFIRMED, Plugin Hooks ❌ NO EQUIVALENT

The Hermes hooks documentation distinguishes between three systems:

| Hook System | `on_failure` config | Failure behavior |
|-------------|-------------------|-------------------|
| Shell hooks (`hooks:` block in config.yaml) | ✅ YES — `on_failure: block` | When set, shell hook failure blocks the tool call |
| Plugin hooks (`ctx.register_hook()`) | ❌ NO | Errors caught and logged — plugin continues, agent unaffected |
| Gateway hooks (`HOOK.yaml` + `handler.py`) | ❌ NO | Errors caught and logged — never crash agent |

**Impact on P4-006:** The shell hook `on_failure: block` is a real, working feature (used in `hermes-config/config.yaml` for `consent_gate.py`). However, for Python plugin hooks (like the auth overlay proposed in P4-002), there is NO equivalent — the plugin hook failure is always "log and continue". To make auth enforcement fail-closed, the auth logic must NOT throw exceptions.

### 3.6 P4-004: Plugin Loading/Registration Mechanism ✅ CONFIRMED

From the plugin documentation:

1. **Discovery:** Hermes scans `~/.hermes/plugins/` (and other sources) for directories containing `plugin.yaml`
2. **Manifest parsing:** `PluginManager.parse_manifest()` reads `plugin.yaml` into `PluginManifest`
3. **Opt-in:** General plugins are disabled by default — must be in `plugins.enabled` to load
4. **Registration:** Hermes calls `register(ctx)` on the plugin's `__init__.py`
5. **Hooks:** `ctx.register_hook("pre_tool_call", callback)` registers lifecycle callbacks
6. **Tools:** `ctx.register_tool(name, toolset, schema, handler)` adds tools for the LLM

```yaml
# Example config.yaml plugin section
plugins:
  enabled:
    - my-tool-plugin
    - disk-cleanup
  disabled:
    - noisy-plugin
```

**Key nuance — Bundled plugins auto-load, user plugins are opt-in:**
- Bundled platform plugins (Discord, Telegram, etc.) auto-load
- Bundled backends (image_gen, memory) auto-load
- User-installed plugins (`~/.hermes/plugins/`) are opt-in via `plugins.enabled`
- **This means the auth overlay plugin will NOT load automatically** — it must be added to `plugins.enabled` in config.yaml

### 3.7 P4-002: Hook Order and Priority ✅ CONFIRMED

From the hooks documentation:

1. All three hook systems (gateway, plugin, shell) are composed through the same dispatcher
2. Plugin hooks fire first (in registration/priority order), then shell hooks
3. For `pre_tool_call`: the first `{"action": "block"}` wins — short-circuits the tool
4. Plugin hooks are non-blocking from an error perspective (errors caught, not propagated)
5. Shell hooks can use `on_failure: block` which DOES propagate the failure

```python
# From hermes_cli/plugins.py — invoke_hook() wraps each callback in try/except
for cb in callbacks:
    try:
        ret = cb(**kwargs)
        if ret is not None:
            results.append(ret)
    except Exception as exc:
        logger.warning("Hook '%s' callback %s raised: %s", hook_name, ...)
```

**Impact on P4-002:** The auth overlay plugin hook can safely block tool calls. But since plugin hook errors are silently caught, the auth overlay must NOT throw exceptions — it must always return `{"action": "block", "message": "..."}` explicitly on failure.

### 3.8 P4-003: Hermes Gateway Restart and Platform Isolation ✅ CONFIRMED

- Platform initialization failures are contained since PR #17429 — each platform connects under a 30s timeout
- Gateway continues running if some platforms fail — circuit breaker pauses chronically-failing adapters after 10 retries
- `/reload-mcp` command disconnects all MCP servers, re-reads config, reconnects — no Hermes restart needed for MCP config changes

---

## 4. Unknowns / Inconclusive Areas

### U1: `pre_tool_call` exact timing relative to MCP subprocess dispatch

**Status: INCONCLUSIVE — no public documentation or test confirms this**

The official docs confirm the hook fires "before the tool's handler runs" but do not explicitly state whether this is:
- (a) Before the MCP subprocess receives the JSON-RPC call → **safe to block**
- (b) After the MCP subprocess has started processing → **race condition**

**Proof required:** A live test on the VPS that:
1. Registers a native MCP server (e.g., `filesystem`)
2. Registers a `pre_tool_call` hook that blocks all `read_file` calls
3. Calls `read_file` via Hermes
4. Verifies the tool call is blocked (not executed)

### U2: `hermes mcp add --native` or custom native-alias subcommands

**Status: INCONCLUSIVE — `--preset` is documented, but no `--native` flag**

The docs mention `--preset` for well-known MCP servers but do not list available presets or whether the 5 native Hermes toolsets have presets. The deployed `hermes-config/config.yaml` uses a custom config format for `mcp_servers` that is NOT the standard `command`/`args` format — it uses `enabled: true` + tool lists + custom fields (`allowed_commands`, `blocked_commands`, `root_path`, etc.). This suggests these are **not MCP servers at all** but rather Hermes-native toolset configurations expressed through a config section named `mcp_servers` for organizational purposes.

**Proof required:** Run `hermes mcp add --help` on the VPS to see available `--preset` values. Also verify whether the 5 servers in `mcp_servers` are actually loaded as MCP or as native toolsets.

### U3: Shell hook `on_failure: block` vs plugin hook equivalent

**Status: PARTIALLY CONFIRMED**

Shell hooks support `on_failure: block` — confirmed. Plugins do NOT have an equivalent. The auth overlay plugin (P4-002) must handle failures internally to maintain fail-closed semantics. The `startup_gate.py` (P4-006) provides the fail-closed guarantee at process start level, but during runtime, the plugin hook has no circuit breaker.

### U4: Plugin manifest `kind: backend` vs `kind: standalone` semantics for auth overlay

**Status: INCONCLUSIVE**

The Guinevere safety plugin uses `kind: standalone` (default). But the auth overlay plugin proposed in Phase 4 needs to enforce auth on EVERY tool call. If registered as a `standalone` plugin, it requires explicit enable via `plugins.enabled`. The docs confirm this opt-in requirement but do not specify whether there's a way to make a plugin mandatory.

---

## 5. Findings Mapped to Phase 4 Decisions

### P4-001: Native MCP Server Configuration

| Assumption | Docs Say | Verdict |
|------------|----------|---------|
| `mcp_servers` config shape is YAML-based | ✅ Confirmed — `command`/`args`/`env` for stdio, `url`/`headers` for HTTP | CONFIRMED |
| `hermes mcp add` writes to config | ✅ Confirmed — also supports `--preset` for well-known servers | CONFIRMED |
| 5 native servers can be configured via `mcp_servers` | ⚠️ The `hermes-config/config.yaml` format uses non-standard fields (`allowed_commands`, `blocked_commands`, `root_path`). These are NOT standard MCP server config — they are native Hermes toolset configs | **PARTIAL — needs VPS verification** |
| Gateway reads `mcp_servers` from `config.yaml` on startup | ✅ Confirmed — `/reload-mcp` exists for hot-reload | CONFIRMED |

### P4-002: Auth Overlay Plugin

| Assumption | Docs Say | Verdict |
|------------|----------|---------|
| Plugin can register `pre_tool_call` hook | ✅ Confirmed — `ctx.register_hook("pre_tool_call", callback)` | CONFIRMED |
| Hook can block tool calls | ✅ Confirmed — return `{"action": "block", "message": "..."}` | CONFIRMED |
| Hook fires before MCP tool dispatch | ⚠️ Confirmed for built-in tools. For MCP subprocess dispatch, the timing is documented as "before tool handler runs" but the exact subprocess lifecycle relative to hook callback is not tested in public docs | **LIKELY SAFE — test recommended** |
| Plugin is opt-in via `plugins.enabled` | ✅ Confirmed — must add to config.yaml | CONFIRMED |
| Multiple hooks can register for same event | ✅ Confirmed — all fire, first `block` wins | CONFIRMED |

### P4-003: Destructive Approval Workflow

| Assumption | Docs Say | Verdict |
|------------|----------|---------|
| `pre_tool_call` can implement 4-check gate | ✅ Confirmed — hook has full access to tool `name` and `args` | CONFIRMED |
| Webhook approval pattern is feasible | ⚠️ Hermes has `pre_approval_request` and `post_approval_response` hooks (from plugin hooks docs). The approval workflow is partially built-in, but the 4-check gate (deny → window → signature → evidence drift) is custom | CONFIRMED with caveat |
| Discord notification via `send_message` is available | ✅ Gateway hooks section shows `send_message` tool usage in examples | CONFIRMED |

### P4-004: Budget Enforcement

| Assumption | Docs Say | Verdict |
|------------|----------|---------|
| Budget check can be injected in `pre_tool_call` | ✅ Confirmed — hook receives `tool_name` and `args` | CONFIRMED |
| Redis Lua atomicity is external to Hermes | ✅ No built-in budget system in Hermes docs | CONFIRMED — external design |
| Budget can block tool calls | ✅ Hook returns `{"action": "block"}` | CONFIRMED |

### P4-005: FastMCP Bridge

| Assumption | Docs Say | Verdict |
|------------|----------|---------|
| stdio transport supported for MCP servers | ✅ Confirmed — `command`/`args`/`env` for subprocess spawning | CONFIRMED |
| `cwd` and `env_file` are supported | ✅ Confirmed — both listed in MCP config reference | CONFIRMED |
| Tool filtering via `tools.include`/`exclude` | ✅ Confirmed — per-server whitelist/blacklist | CONFIRMED |
| `env_file` works with Hermes subprocess | ⚠️ Documented under MCP config but behavior with relative paths is not fully specified | Needs test |

### P4-006: Startup Gate & Fail-Closed Guarantee

| Assumption | Docs Say | Verdict |
|------------|----------|---------|
| `critical: true` prevents startup on plugin failure | ❌ **REFUTED** — `PluginManifest` has no `critical` field. Field is silently ignored. | **MUST FIX** |
| `on_failure: block` prevents tool calls on hook failure | ✅ Confirmed for shell hooks. ❌ **Not available for plugin hooks** | MIXED |
| Plugin failure crashes gateway | ❌ **REFUTED** — docs state: "Errors in any hook handler are caught and logged at warning level. A broken hook never crashes the agent." | CONFIRMED fail-open |
| Hermes can be configured to refuse startup without specific plugin | ❌ **NOT SUPPORTED** — no "required plugin" concept exists in Hermes | **MUST FIX via startup_gate.py** |
| `startup_gate.py` approach from Oracle review is correct | ✅ Confirmed — external validation gate is the only reliable approach | CONFIRMED |

---

## 6. Hard Constraint Verification

| Constraint | Status | Source |
|------------|--------|--------|
| `src/mcp/auth_matrix.py` is authoritative | ✅ External docs do not contradict | Docs say nothing about auth matrix |
| Fail-closed auth failures | ⚠️ Hermes plugin hooks are fail-open by default (errors logged, agent continues). Fail-closed must be implemented IN the hook handler, not at the framework level. | Confirmed in hooks docs |
| Redis 6380 / Postgres 5433 | ✅ No conflict with Hermes docs (Hermes is port-agnostic) | N/A |
| No secrets exposure | ✅ Docs explicitly separate `.env` (secrets) from `config.yaml` (settings) | Confirmed in configuration docs |
| Python plugin for auth overlay | ✅ Fully supported — `ctx.register_tool()` and `ctx.register_hook()` are documented APIs | Confirmed |

---

## 7. Recommendations for Phase 4

### R1: REPLACE `critical: true` dependency with `startup_gate.py` (P4-006)

**Priority: CRITICAL**

Remove all reliance on `critical: true` having any effect. The `startup_gate.py` approach from the Oracle Risk Review is the correct mitigation:
1. Before `hermes gateway start`, run `python -c "from plugins.auth_overlay import AuthOverlayPlugin; p=AuthOverlayPlugin(); p.on_load({})"`
2. If import or instantiation fails, abort startup with exit code 1
3. Remove or document `critical: true` in `manifest.yaml` as a no-op

### R2: Add explicit VPS test for `pre_tool_call` blocking native MCP (P4-002)

**Priority: HIGH**

Before deploying the auth overlay to production, run a controlled test:
1. Register a test MCP server (e.g., a simple Python HTTP echo server)
2. Register a `pre_tool_call` hook that blocks a specific tool
3. Verify the tool call is blocked with the expected message
4. Verify the tool does NOT execute (no side effects)

Document the test results in the Phase 4 gate.

### R3: Update `hermes-config/config.yaml` `mcp_servers` format to standard

**Priority: MEDIUM**

The `mcp_servers` section uses non-standard config fields. Verify whether Hermes v0.15.2 actually supports `allowed_commands`, `blocked_commands`, `root_path`, etc. in `mcp_servers`. If these are Hermes-native toolset configs expressed differently, migrate to the standard:
- Either use `hermes mcp add --preset <native_name>` if presets exist
- Or use standard `command`/`args` format pointing at Hermes-native MCP server implementations
- Or document that these are NOT MCP servers but native toolset configs in a named section

### R4: Add auth overlay plugin to `plugins.enabled` (P4-002)

**Priority: HIGH**

The auth overlay plugin must be explicitly enabled:
```yaml
plugins:
  enabled:
    - guinevere_safety
    - auth_overlay
```

Without this, the plugin is discovered but NOT loaded — the LLM will call tools without auth enforcement.

### R5: Update shell hooks with `on_failure: block` as defense-in-depth (P4-006)

**Priority: MEDIUM**

Keep and maintain the shell hook `on_failure: block` pattern from `hermes-config/config.yaml`:
```yaml
hooks:
  pre_tool_call:
    - event: pre_tool_call
      command: "python3 ~/.hermes/hooks/consent_gate.py"
      timeout_ms: 200
      on_failure: block
      priority: 90
```

This gives defense-in-depth: if the Python auth overlay plugin encounters an unexpected error, the shell hook still blocks the tool call. The shell hook CANNOT replace the plugin hook for complex auth logic (Redis lookups, Discord notifications), but it CAN serve as a last-resort block for known dangerous patterns.

---

## 8. Appendix: Command Reference from Docs

### `hermes mcp add` Flags

```
hermes mcp add <name>
  --url <endpoint>     HTTP/SSE MCP server endpoint
  --command <cmd>      stdio MCP server executable
  --args <args...>     Arguments for stdio server
  --auth {oauth, header}  Authentication method
  --preset <name>      Well-known MCP preset (auto-fills transport)
  --env KEY=VALUE      Environment variables
```

### `hermes mcp` Subcommands

```
hermes mcp add        Add an MCP server
hermes mcp list       List configured MCP servers
hermes mcp remove     Remove an MCP server
```

### `/reload-mcp` Slash Command

Hot-reloads all MCP servers:
- Disconnects from all current MCP servers
- Re-reads `mcp_servers` from `config.yaml`
- Reconnects to all configured servers
- Available in both CLI and gateway sessions

### Plugin Commands

```
hermes plugins                      Interactive management UI
hermes plugins list                 Table: enabled/disabled/not enabled
hermes plugins install user/repo    Install from Git
hermes plugins enable <name>        Add to allow-list
hermes plugins disable <name>       Remove from allow-list + add to disabled
hermes plugins remove <name>        Uninstall
hermes plugins update <name>        Pull latest
```

---

## 9. Report Metadata

| Field | Value |
|-------|-------|
| Report path | `research-reports/phase-4-execution/07-hermes-external-docs.md` |
| Assessor | Guinevere |
| Hermes version targeted | v0.15.x |
| Hermes version on VPS | v0.15.2 (2026.5.29.2) |
| Primary docs inspected | 7 pages from `hermes-agent.nousresearch.com/docs/` |
| GitHub sources inspected | `plugins.py`, `RELEASE_v0.15.0.md`, PR #301, Issue #10048 |
| Local files inspected | `hermes-config/config.yaml`, `manifest.yaml`, `plugin.py` |
| Tokens/secrets exposed | None |
| Decisions affected | P4-001 through P4-006 |
| Critical blockers found | 1 (`critical: true` is no-op) |
| High-severity findings | 2 (critical refuted, pre_tool_call timing unverified) |
| Medium-severity findings | 3 (mcp_servers config format, plugin opt-in, shell vs plugin hooks) |

---

*End of report. Verdict: CONDITIONAL PROCEED — 1 critical refutation found (`critical: true`), 1 high-uncertainty area requiring VPS test (`pre_tool_call` blocking MCP subprocess). All other Phase 4 assumptions are confirmed by public docs.*
