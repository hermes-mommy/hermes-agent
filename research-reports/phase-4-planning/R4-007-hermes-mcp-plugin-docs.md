# R4-007: Hermes Agent MCP, Plugin, and Hook System Documentation

**Date:** 2026-06-05  
**Target:** Guinevere Phase 4 (MCP + Tools) Migration Planning  
**Source:** Official NousResearch Hermes Agent Documentation & GitHub Repository (`NousResearch/hermes-agent`)  

---

## 1. Official Repository & Documentation
- **GitHub Repository:** `https://github.com/NousResearch/hermes-agent`
- **Official Documentation:** `https://hermes-agent.nousresearch.com/docs/`
- **Architecture Note:** Hermes is a self-improving AI agent with a built-in learning loop, supporting CLI, messaging gateways (Discord, Telegram, etc.), and extensive tool/plugin ecosystems.

---

## 2. MCP Server Configuration Format
Hermes uses a native MCP client that connects to servers at startup and registers their tools. Configuration lives in `~/.hermes/config.yaml` under the `mcp_servers` key.

### Root Config Shape (YAML)
```yaml
mcp_servers:
  <server_name>:
    # For stdio servers (local subprocess)
    command: "npx"               # Executable to launch
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/project"]
    env:                         # Environment variables passed to subprocess
      GITHUB_PERSONAL_ACCESS_TOKEN: "***"
    
    # OR for HTTP/StreamableHTTP servers (remote)
    # url: "https://mcp.example.com/mcp"
    # headers:
    #   Authorization: "Bearer ***"
    # auth: "oauth"              # Optional: enables OAuth 2.1 PKCE flow
    
    enabled: true                # Skip server entirely when false
    timeout: 120                 # Per-tool-call timeout in seconds
    connect_timeout: 60          # Initial connection timeout
    supports_parallel_tool_calls: false
    
    tools:                       # Per-server filtering and utility policy
      include: ["list_issues", "create_issue"]  # Whitelist (if set, ONLY these are registered)
      exclude: ["delete_customer"]              # Blacklist
      resources: true            # Enable/disable list_resources + read_resource wrappers
      prompts: false             # Enable/disable list_prompts + get_prompt wrappers
```
**Tool Naming:** Server-native MCP tools are registered with the prefix `mcp_<server>_<tool>`. Hyphens and dots in names are replaced with underscores.

---

## 3. Plugin Development & Architecture
Plugins are Python directories dropped into `~/.hermes/plugins/<plugin_name>/`. They require a `plugin.yaml` manifest and an `__init__.py` with a `register(ctx)` function.

### `plugin.yaml`
```yaml
name: my-custom-plugin
version: 1.0.0
description: Custom tool and hook integration
provides_tools:
  - my_custom_tool
provides_hooks:
  - pre_tool_call
  - post_tool_call
```

### `__init__.py` (Registration)
```python
import json

def register(ctx):
    # 1. Register a custom tool
    schema = {
        "name": "my_custom_tool",
        "description": "Does something custom",
        "parameters": {"type": "object", "properties": {"arg": {"type": "string"}}, "required": ["arg"]},
    }
    def handle_my_tool(params, **kwargs):
        return json.dumps({"success": True, "result": f"Processed {params.get('arg')}"})
    
    ctx.register_tool(
        name="my_custom_tool",
        toolset="my_custom_toolset",
        schema=schema,
        handler=handle_my_tool,
        description="Does something custom"
    )
    
    # 2. Register a lifecycle hook
    ctx.register_hook("post_tool_call", my_post_tool_hook)

def my_post_tool_hook(tool_name: str, args: dict, result: str, task_id: str, duration_ms: int, **kwargs):
    print(f"[my-plugin] Tool {tool_name} completed in {duration_ms}ms")
```
**Note:** Plugins are disabled by default. They must be explicitly enabled in `config.yaml` under `plugins.enabled: ["my-custom-plugin"]` to prevent third-party code from running without consent.

---

## 4. Hook System Documentation
Plugins can register callbacks for lifecycle events via `ctx.register_hook("event_name", callback)`. All callbacks should accept `**kwargs` for forward compatibility. If a hook crashes, it is caught, logged, and skipped—it **never crashes the agent**.

### Available Hooks
| Hook | Fires When | Return Value / Effect |
|---|---|---|
| `pre_tool_call` | Before **any** tool executes (built-in or plugin). | `{"action": "block", "message": "Reason"}` to veto the call. Any other return is ignored. |
| `post_tool_call` | After any tool returns (or returns an error JSON string). | Ignored (fire-and-forget observer). |
| `pre_llm_call` | Once per turn, before the tool-calling loop. | `{"context": "string"}` to prepend context to the user message. |
| `post_llm_call` | Once per turn, after the tool-calling loop (successful turns only). | Ignored. |
| `on_session_start` | New session created (first turn only). | Ignored. |
| `on_session_end` | End of every `run_conversation` call + CLI exit. | Ignored. |
| `on_session_finalize` | CLI/gateway tears down an active session (`/new`, GC, quit). | Ignored. |
| `on_session_reset` | Gateway swaps in a fresh session key. | Ignored. |
| `subagent_stop` | A `delegate_task` child has exited. | Ignored. |
| `pre_gateway_dispatch` | Gateway received a user message, before auth + dispatch. | `{"action": "skip" \| "rewrite" \| "allow", ...}` to influence flow. |
| `transform_tool_result` | After any tool returns, before result is handed to the model. | `str` to replace the result, `None` to leave unchanged. |
| `transform_terminal_output` | Inside the `terminal` tool, before truncation/ANSI-strip/redaction. | `str` to replace raw output, `None` to leave unchanged. |

---

## 5. `critical: true` and `on_failure: block` Plugin Flags
**Finding:** **These specific flags (`critical: true`, `on_failure: block`) DO NOT EXIST in the Hermes Agent plugin configuration schema.** 

Hermes employs a **fail-open, implicit-trust model** for Python plugins:
1. If a plugin's `register()` function crashes, the plugin is disabled, but Hermes continues running normally.
2. If a hook callback crashes, the error is caught, logged, and skipped. Other hooks and the agent loop continue unaffected.
3. There is no "load gate" that halts the entire agent startup if a plugin fails. 
4. *Hypothesis:* You may be conflating this with OpenClaw (the upstream project Hermes is forked from) or a different agent framework. In Hermes, safety is enforced via the `pre_tool_call` hook returning `{"action": "block", "message": "..."}`, not via plugin manifest flags.

---

## 6. Terminal/Shell Tool Configuration & Command Filtering
Hermes has a robust, multi-layered command approval and filtering system in `tools/approval.py`.

### Hard Blocklist (`UNRECOVERABLE_BLOCKLIST`)
These commands are **never** executed, regardless of `--yolo` or approval settings. The tool call returns an explanatory error immediately:
- `rm -rf /` (and `--no-preserve-root` variants)
- Bash fork bombs (`:(){ :|:& };:`)
- `mkfs.*` on mounted root devices
- `dd if=/dev/zero of=/dev/sd*`
- Piping untrusted URLs to `sh` at the rootfs level

### Dangerous Pattern Approval
Patterns like `rm -r`, `chmod 777`, `DROP TABLE`, `curl ... | sh`, `systemctl stop`, and `pkill` trigger a human-in-the-loop approval prompt. 
- Approving "always" adds the pattern to `command_allowlist` in `config.yaml`.
- **Container Bypass:** When using `docker`, `modal`, `singularity`, or `daytona` backends, dangerous command checks are **skipped** because the container itself is the security boundary.

### Shell Hooks (Alternative to Python Plugins)
You can also block/filter terminal commands via config-driven shell hooks:
```yaml
hooks:
  pre_tool_call:
    - matcher: "terminal"
      command: "~/.hermes/agent-hooks/block-rm-rf.sh"
      timeout: 5
```
The shell script receives JSON via stdin and can return `{"decision": "block", "reason": "..."}` to veto the call.

---

## 7. File/Filesystem Tool Configuration & Path-Based Permissions
Hermes does not have a native "allowed_paths" whitelist for its built-in `read_file`/`write_file` tools. Instead, it relies on working directory scoping and context reference blocking.

### Working Directory Scoping
- The `terminal.cwd` setting in `config.yaml` dictates the starting directory for `terminal`, `read_file`, `write_file`, `patch`, and `execute_code`.
- **Warning:** On the `local` backend, the agent still has the same filesystem access as your user account. `terminal.cwd` is a convenience, not a sandbox.

### Context Reference Blocking (`@file:`)
The CLI's `@file:` and `@folder:` reference expansion explicitly blocks sensitive paths to prevent credential exposure:
- **Blocked Files:** `~/.ssh/id_rsa`, `~/.ssh/config`, `~/.bashrc`, `~/.zshrc`, `~/.netrc`, `~/.npmrc`, `$HERMES_HOME/.env`
- **Blocked Directories:** `~/.ssh/`, `~/.aws/`, `~/.gnupg/`, `~/.kube/`, `$HERMES_HOME/skills/.hub/`
- Path traversal outside the allowed workspace root is rejected.

### Recommended Path-Based Permission Strategy
For strict path-based permissions, Hermes documentation explicitly recommends **not** using the built-in file tools on the `local` backend. Instead, use:
1. **MCP Filesystem Server:** Configure an MCP server with explicit allowed paths.
   ```yaml
   mcp_servers:
     project_fs:
       command: "npx"
       args: ["-y", "@modelcontextprotocol/server-filesystem", "/home/user/my-project"]
   ```
2. **Docker Backend:** Set `terminal.backend: docker` with `container_persistent: false` (ephemeral tmpfs) or bind-mount specific directories. This provides true OS-level filesystem isolation.

---

## 8. Migration Implications for Guinevere
1. **MCP Migration:** Guinevere's tool integrations can be cleanly mapped to Hermes' `mcp_servers` config. The `tools.include`/`tools.exclude` filtering provides the exact allowlist/blacklist control needed for safe tool exposure.
2. **Hook Migration:** Guinevere's `pre_tool_call` and `post_tool_call` logic can be directly ported to Hermes Python plugins using `ctx.register_hook()`. The `{"action": "block", "message": "..."}` return signature perfectly matches Guinevere's guardrail requirements.
3. **Missing Features:** The `critical: true` / `on_failure: block` concepts must be re-architected. Hermes relies on explicit `plugins.enabled` allowlisting and fail-open hook execution. If Guinevere requires hard-fail on plugin load, this must be implemented as a custom pre-startup validation script, as Hermes core will not halt for a failing plugin.
4. **Security:** To match Guinevere's strict consent and surveillance boundaries, the `docker` terminal backend should be mandated for all agent executions, bypassing the need for complex regex-based command approval and providing true filesystem isolation.

---
*Report generated by Guinevere Librarian Agent. Evidence sourced from `hermes-agent.nousresearch.com/docs/` and `github.com/NousResearch/hermes-agent`.*