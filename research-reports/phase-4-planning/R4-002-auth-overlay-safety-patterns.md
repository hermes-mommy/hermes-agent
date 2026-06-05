# R4-002: Auth Overlay & Safety Patterns Research Report

**Date:** 2026-06-05  
**Phase:** Phase 4 (MCP + Tools) Migration  
**Target:** `plugins/auth_overlay.py` (ADR-035 compliance)  
**Scope:** Auth matrix, safety plugins, FastMCP hooks, notification patterns  

---

## 1. Executive Summary

This report synthesizes existing authorization, safety, and plugin patterns in the Guinevere codebase to inform the design of the Phase 4 `plugins/auth_overlay.py`. The codebase already contains a robust, production-grade 4-level auth matrix, a comprehensive Hermes safety plugin (`GuinevereSafetyPlugin`), and established Discord/Gotify notification patterns. The new auth overlay plugin must integrate with these existing systems, enforcing `critical: true` and `on_failure: block` as mandated by ADR-035.

---

## 2. Auth Matrix & Authorization Levels

### 2.1 Core Definitions (`src/mcp/auth.py`)
The codebase defines a strict 4-level authorization enum:

```python
class AuthLevel(enum.Enum):
    READ_AUTO = "read_auto"               # Execute immediately, no side effects
    WRITE_NOTIFY = "write_notify"         # Execute then fire Discord notification (non-blocking)
    DESTRUCTIVE_APPROVAL = "destructive_approval"  # Notify Discord, wait for approval (5-min timeout)
    FORBIDDEN = "forbidden"               # Raise immediately, never execute
```

**Key Mechanisms:**
- `require_approval(level, tool_name)` decorator gates tool functions.
- `_wait_for_approval()` blocks via `asyncio.Event` until external Discord callback (`approve()`/`deny()`) resolves it.
- Timeout: 300 seconds (5 minutes) for `DESTRUCTIVE_APPROVAL`.
- `ForbiddenOperationError` is raised for denied/forbidden operations.

### 2.2 Auth Matrix Registry (`src/mcp/auth_matrix.py`)
A centralized, frozen registry mapping all 16 MCP tools to their allowed operations and `AuthLevel`:

- **READ_AUTO (Wildcard `*`)**: `brave_search`, `context7`, `exa`, `fetch`, `grep_app`, `sequential_thinking`, `time`, `websearch`.
- **Multi-level Tools**:
  - `filesystem`: `read`/`list` (READ_AUTO), `write` (WRITE_NOTIFY), `delete` (DESTRUCTIVE_APPROVAL).
  - `git`: `log`/`diff`/`status` (READ_AUTO), `commit`/`push` (WRITE_NOTIFY), `force_push` (DESTRUCTIVE_APPROVAL), `force_push_main` (FORBIDDEN).
  - `postgres`: `select`/`explain` (READ_AUTO), `insert`/`update`/`delete_row`/`drop`/`truncate` (FORBIDDEN).
  - `redis`: Read ops (READ_AUTO), write ops like `set`/`hset` (WRITE_NOTIFY), `del`/`expire` (DESTRUCTIVE_APPROVAL), `flushdb`/`flushall`/`config` (FORBIDDEN).
  - `shell`: `exec` (DESTRUCTIVE_APPROVAL), `rm_rf_root`/`sudo_rm_rf` (FORBIDDEN).
  - `docker`: `ps`/`logs` (READ_AUTO), `start`/`stop` (WRITE_NOTIFY), `rm`/`rmi` (DESTRUCTIVE_APPROVAL), `system_prune`/`rm_all` (FORBIDDEN).

**Lookup Function:**
```python
def get_auth_level(tool_name: str, operation: str) -> AuthLevel:
    # Returns AuthLevel, raises KeyError if tool/operation unknown (fail-closed)
```

---

## 3. Safety Plugin Patterns

### 3.1 `GuinevereSafetyPlugin` (`src/hermes/safety_plugin.py`)
The existing safety plugin implements 10 safety gates via Hermes hooks. It is the primary reference for the new auth overlay.

**Hook Mapping for Auth:**
- **`pre_tool_call`**: Intercepts tool execution. Checks `get_auth_level(tool_name, operation)`. If `FORBIDDEN` or `DESTRUCTIVE_APPROVAL`, it returns `{"action": "block", "reason": "...", "message": "..."}`.
- **`post_tool_call`**: Observational logging only.

**Key Implementation Details:**
- Lazy imports for graceful degradation (e.g., `from src.mcp.auth_matrix import get_auth_level`).
- Thread-safe per-session state (`SessionSafetyState`).
- Returns `None` to allow, or `dict` with `"action": "block"` to veto.

### 3.2 Hermes Plugin Structure (`hermes-config/plugins/guinevere_safety/plugin.py`)
Demonstrates the Hermes plugin lifecycle:
- `on_load()`: Initializes state (e.g., Redis DB5 connection).
- `on_unload()`: Cleans up resources.
- Command handlers (`cmd_get_state`, `cmd_set_punishment`, etc.) registered via `ctx.register_command()`.

---

## 4. Hook Definitions & Signatures

### 4.1 Hermes Hook System (`hermes-config/hooks/_hook_utils.py`)
Hermes hooks are shell-command scripts or Python callbacks that receive JSON via `stdin` and return JSON via `stdout`.

**Data Contract (stdin):**
```json
{
  "hook_event": "pre_tool_call",
  "session_id": "sess_abc123",
  "tool_name": "filesystem",
  "args": {"operation": "delete", "path": "/tmp/test"},
  "user_id": "987654321098765432",
  "timestamp": "2026-06-04T12:34:56Z"
}
```

**Response Contract (stdout):**
- **PASS (exit 0):** `{"action": "allow"}` or `{}`
- **BLOCK (exit 1):** `{"action": "block", "reason": "AUTH_FORBIDDEN:filesystem:delete", "message": "..."}`
- **WARN (exit 2):** `{"action": "warn", "reason": "...", "message": "..."}`

### 4.2 ADR-035 Hook Configuration for `pre_tool_call`
```yaml
hooks:
  pre_tool_call:
    command: "python /home/guinevere/code/guinevere/plugins/auth_overlay.py"
    timeout_ms: 300
    on_failure: block              # CRITICAL: Fail-closed
    stdin: json
    priority: 90
    retry: none
    description: "Auth matrix enforcement + consent gate + budget check"
```

---

## 5. FastMCP Server Implementation

### 5.1 Server Factory (`src/mcp/manager.py`)
The MCP server is built using `mcp.server.fastmcp.FastMCP`.

```python
def create_server(name: str = "guinevere-mcp") -> FastMCP:
    server = FastMCP(
        name=name,
        lifespan=_build_lifespan(),  # Registers tools and verifies auth matrix at startup
    )
    return server
```

**Lifespan Verification (RG-008):**
At startup, `_build_lifespan()` calls `verify_matrix_completeness()` to ensure all 16 tools are registered in `AUTH_MATRIX`. If incomplete, it logs a warning but does not crash (fail-soft at startup, fail-closed at runtime).

---

## 6. Approval & Notification Patterns

### 6.1 Discord Webhook Notifications (`src/discord/notifications.py`)
- **SEV Levels:** SEV0 (Urgent, ping Faiz, create thread), SEV1 (Alert), SEV2 (Budget), SEV3 (Status), SEV4 (Audit).
- **Mechanism:** `send_alert(bot, sev, title, description)` builds a `discord.Embed` and sends it to the appropriate channel (`system-health`, `cost-tracker`, etc.).
- **Fallback:** For SEV0/SEV1, it automatically triggers Gotify fallback.

### 6.2 Gotify Fallback (`src/discord/gotify_fallback.py`)
- **Endpoint:** `http://localhost:8081/message`
- **Auth:** `X-Gotify-Key` header from `GOTIFY_APP_TOKEN` env var.
- **Priority Mapping:** SEV0 → 10, SEV1 → 7, SEV2 → 5, SEV3 → 3, SEV4 → 1.
- **Behavior:** Fail-soft. Returns `False` on timeout, connection error, or missing token, logging the failure without crashing the main pipeline.

### 6.3 In-Process Discord Approval (`src/mcp/auth.py`)
For `DESTRUCTIVE_APPROVAL`, the system posts a Discord webhook message and blocks via `asyncio.Event`. External Discord slash commands (`/approve`, `/deny`) resolve the event:
```python
def approve(tool_name: str) -> None:
    _approval_results[tool_name] = True
    _pending_approvals[tool_name].set()
```

---

## 7. Recommendations for `plugins/auth_overlay.py`

Based on the research, the new `plugins/auth_overlay.py` should be structured as follows:

### 7.1 Plugin Registration
```python
def register(ctx: PluginContext) -> None:
    plugin = AuthOverlayPlugin()
    ctx.register_hook("pre_tool_call", plugin.pre_tool_call)
    # Optional: ctx.register_command("approve", plugin.cmd_approve)
    # Optional: ctx.register_command("deny", plugin.cmd_deny)
```

### 7.2 `pre_tool_call` Implementation
1. **Extract Context:** Parse `tool_name` and `operation` (from `args.operation` or `args.action`, default `"read"`).
2. **Matrix Lookup:** Call `get_auth_level(tool_name, operation)`.
3. **Enforcement Logic:**
   - `READ_AUTO`: Return `{"action": "allow"}`.
   - `WRITE_NOTIFY`: Return `{"action": "allow"}` and trigger async Discord/Gotify notification.
   - `DESTRUCTIVE_APPROVAL`: Post Discord notification with approval buttons. Block execution (`{"action": "block", "reason": "AWAITING_APPROVAL"}`) until resolved via `/approve` command or timeout (300s).
   - `FORBIDDEN`: Immediately return `{"action": "block", "reason": "AUTH_FORBIDDEN", "message": "..."}`.
4. **Fail-Closed:** Any `KeyError` (unknown tool/operation) or exception must return `{"action": "block", "reason": "AUTH_UNKNOWN"}`.

### 7.3 Configuration Requirements (`hermes-config/config.yaml`)
```yaml
plugins:
  auth_overlay:
    critical: true
    on_failure: block
    timeout_ms: 300
    environment:
      DISCORD_WEBHOOK_URL: "https://discord.com/api/webhooks/..."
      GOTIFY_APP_TOKEN: "${GOTIFY_APP_TOKEN}"
      GUINEVERE_FAIZ_MENTION: "<@123456789>"
```

---

## 8. File Inventory (Reference)

| File Path | Relevance |
|---|---|
| `src/mcp/auth.py` | Core `AuthLevel` enum, `require_approval` decorator, approval event logic. |
| `src/mcp/auth_matrix.py` | Centralized `AUTH_MATRIX` registry for all 16 tools. |
| `src/hermes/safety_plugin.py` | Reference implementation of `pre_tool_call` hook blocking logic. |
| `hermes-config/plugins/guinevere_safety/plugin.py` | Hermes plugin lifecycle and command registration patterns. |
| `hermes-config/hooks/_hook_utils.py` | stdin/stdout JSON contract and Redis utility patterns. |
| `src/mcp/manager.py` | FastMCP server factory and startup matrix verification. |
| `src/discord/notifications.py` | SEV-level Discord embed routing and channel mapping. |
| `src/discord/gotify_fallback.py` | Gotify HTTP client implementation for SEV0/SEV1 fallback. |
| `tests/mcp/test_auth_matrix.py` | Comprehensive test cases for all 4 auth levels and matrix completeness. |
| `adr/ADR-035-hermes-migration.md` | Architectural mandate for hook-based safety and auth overlay. |

---

## 9. Next Steps for Implementation

1. **Draft `plugins/auth_overlay.py`**: Implement the `AuthOverlayPlugin` class with `pre_tool_call` hook logic, mirroring the fail-closed behavior of `src/hermes/safety_plugin.py`.
2. **Add Approval Commands**: Implement `/approve` and `/deny` slash command handlers in the plugin to resolve `asyncio.Event` or Redis-based approval queues.
3. **Update `hermes-config/config.yaml`**: Add the `auth_overlay` plugin configuration with `critical: true` and `on_failure: block`.
4. **Write Tests**: Create `tests/plugins/test_auth_overlay.py` covering all 4 `AuthLevel` scenarios, timeout behavior, and fail-closed unknown tool handling.
5. **Run Auditor Gate**: Execute `lsp_diagnostics`, `pytest`, and forbidden pattern sweeps before marking the step complete.

---
*Report generated by Guinevere. Read-only research. No files modified.*
