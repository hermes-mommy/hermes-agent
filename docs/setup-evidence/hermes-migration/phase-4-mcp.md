# Phase 4: MCP + Tools Migration — Detailed Procedure

## Overview

| Property | Value |
|---|---|
| **Duration** | 5-7 days |
| **Risk Level** | MEDIUM |
| **Dependencies** | Phase 1 (BLOCKING), Phase 2 (BLOCKING) |
| **Blocks** | Phase 7 (BLOCKING) |
| **Gate** | All 16 tool capabilities available (5 native + 7 custom + 4 hybrid). Auth matrix enforced on all 16. Security audit clean |
| **Rollback Time** | < 2 minutes (remove native MCP + restore FastMCP + remove auth overlay) |

### Goal Statement

Migrate 5 of 16 custom MCP tools to Hermes native equivalents (web, filesystem, terminal, git, fetch). Keep 7 safety-critical custom tools on FastMCP (postgres, redis, obscura_cdp, grep_app, context7, sequential_thinking, time_tools). Build auth overlay plugin (`plugins/auth_overlay.py`) to enforce the 4-level auth matrix (READ_AUTO, WRITE_NOTIFY, DESTRUCTIVE_APPROVAL, FORBIDDEN) on ALL tool calls — both native and custom. The auth overlay is `critical: true` — Hermes refuses to start without it.

### Pre-Conditions

- [ ] Phase 2 cutover complete — Hermes gateway running as primary
- [ ] `guinevere-mcp.service` running (7 custom tools on FastMCP)
- [ ] Auth matrix definitions available from `src/mcp/auth_matrix.py`
- [ ] Phase 1 consent gate hook operational (used by auth overlay)

---

## Step-by-Step Procedure

### Step 4.1: Register 5 Hermes Native MCP Servers

**CAUTION: DO NOT register native tools without auth overlay. Complete Step 4.2 (auth overlay) BEFORE or IMMEDIATELY AFTER this step. If auth overlay is not active, Hermes native tools execute with NO auth matrix enforcement.**

**Command:**
```bash
# Add 5 native MCP servers
hermes mcp add web --config ./config/hermes/mcp-servers.yaml
hermes mcp add filesystem --root-path /home/guinevere/code/guinevere
hermes mcp add terminal --config ./config/hermes/terminal-blocked.yaml
hermes mcp add git --config ./config/hermes/git-allowed.yaml
hermes mcp add fetch --timeout 30 --max-response 10MB
```

**MCP Server Configuration (`config/hermes/mcp-servers.yaml`):**
```yaml
mcp_servers:
  web:
    enabled: true
    tools: [brave_search, exa_search, fetch_url, websearch]
  filesystem:
    enabled: true
    root_path: "/home/guinevere/code/guinevere"
    allowed_paths:
      - "/home/guinevere/code/guinevere"
      - "/tmp/guinevere"
    blocked_paths: ["/etc", "/root", "/home/guinevere/.ssh"]
  terminal:
    enabled: true
    allowed_commands: [ls, cat, head, tail, grep, find, wc, sort, uniq, python, pip, pytest, git, gh]
    blocked_commands: [rm, dd, mkfs, shutdown, reboot, poweroff, iptables, ufw, systemctl]
    timeout_seconds: 30
  git:
    enabled: true
    allowed_operations: [status, diff, log, branch, checkout, add, commit, push, pull]
    blocked_operations: [push --force, reset --hard, clean -fd]
  fetch:
    enabled: true
    timeout_seconds: 30
    max_response_size_mb: 10
```

**Verification:**
```bash
hermes mcp list
# Expected: web, filesystem, terminal, git, fetch — all registered
```

### Step 4.2: Build Auth Overlay Plugin

**Create `plugins/auth_overlay.py`:**
```python
"""AuthOverlayPlugin — Enforces 4-level auth matrix on ALL tool calls.

Intercepts pre_tool_call lifecycle. Maps each tool to its auth level:
  READ_AUTO (0)         → silent pass
  WRITE_NOTIFY (1)      → pass + Discord notification
  DESTRUCTIVE_APPROVAL (2) → block + Discord webhook → wait approval (5 min timeout) → execute or deny
  FORBIDDEN (3)         → block, no bypass

CRITICAL PLUGIN — Hermes refuses to start without this.
"""

import json
import time
from enum import IntEnum
from typing import Dict, Any, Optional


class AuthLevel(IntEnum):
    READ_AUTO = 0
    WRITE_NOTIFY = 1
    DESTRUCTIVE_APPROVAL = 2
    FORBIDDEN = 3


# Auth matrix — maps tool:operation → auth level
AUTH_MATRIX: Dict[str, Dict[str, AuthLevel]] = {
    # Native Hermes tools
    "web": {"brave_search": AuthLevel.READ_AUTO, "exa_search": AuthLevel.READ_AUTO,
            "websearch": AuthLevel.READ_AUTO, "fetch": AuthLevel.READ_AUTO},
    "filesystem": {"read": AuthLevel.READ_AUTO, "write": AuthLevel.WRITE_NOTIFY,
                   "delete": AuthLevel.DESTRUCTIVE_APPROVAL, "create_directory": AuthLevel.WRITE_NOTIFY},
    "terminal": {"read_commands": AuthLevel.READ_AUTO, "write_commands": AuthLevel.WRITE_NOTIFY,
                 "destructive_commands": AuthLevel.DESTRUCTIVE_APPROVAL, "forbidden_commands": AuthLevel.FORBIDDEN},
    "git": {"read": AuthLevel.READ_AUTO, "write": AuthLevel.WRITE_NOTIFY, "destructive": AuthLevel.DESTRUCTIVE_APPROVAL},
    "fetch": {"get": AuthLevel.READ_AUTO, "post": AuthLevel.WRITE_NOTIFY, "upload": AuthLevel.DESTRUCTIVE_APPROVAL},
    
    # Custom MCP tools (guinevere-mcp)
    "postgres_tool": {"select": AuthLevel.READ_AUTO, "insert": AuthLevel.WRITE_NOTIFY, "update": AuthLevel.WRITE_NOTIFY,
                      "delete": AuthLevel.DESTRUCTIVE_APPROVAL, "ddl": AuthLevel.DESTRUCTIVE_APPROVAL,
                      "drop": AuthLevel.FORBIDDEN, "pg_dump": AuthLevel.WRITE_NOTIFY},
    "redis_tool": {"get": AuthLevel.READ_AUTO, "set": AuthLevel.WRITE_NOTIFY, "delete": AuthLevel.WRITE_NOTIFY,
                   "flush": AuthLevel.DESTRUCTIVE_APPROVAL, "config": AuthLevel.FORBIDDEN},
    "obscura_cdp": {"navigate": AuthLevel.READ_AUTO, "screenshot": AuthLevel.READ_AUTO,
                    "fill_form": AuthLevel.WRITE_NOTIFY, "click": AuthLevel.WRITE_NOTIFY,
                    "execute_js": AuthLevel.DESTRUCTIVE_APPROVAL, "file_upload": AuthLevel.DESTRUCTIVE_APPROVAL},
    "grep_app": {"search": AuthLevel.READ_AUTO, "search_github": AuthLevel.READ_AUTO},
    "context7": {"query": AuthLevel.READ_AUTO, "resolve": AuthLevel.READ_AUTO},
    "sequential_thinking": {"think": AuthLevel.READ_AUTO},
    "time_tools": {"get_time": AuthLevel.READ_AUTO, "convert": AuthLevel.READ_AUTO, "calculate": AuthLevel.READ_AUTO},
}

# Hard-blocked FORBIDDEN commands (terminal)
FORBIDDEN_COMMANDS = [
    "rm -rf /", "dd if=/dev/zero", "mkfs.ext4", "shutdown", "reboot",
    "iptables -F", "ufw disable", ":(){ :|:& };:",  # fork bomb
]

# Tools with destructive operations requiring approval
DESTRUCTIVE_TOOLS = {
    "terminal": ["rm", "dd", "mkfs"],
    "filesystem": ["delete"],
    "postgres_tool": ["delete", "drop", "ddl"],
    "redis_tool": ["flush"],
    "obscura_cdp": ["execute_js"],
}


class AuthOverlayPlugin:
    """Intercepts ALL tool calls via pre_tool_call hook."""
    
    def __init__(self):
        self._loaded = False
        self._webhook_url = None
        self._pending_approvals: Dict[str, dict] = {}
        self._approval_timeout_ms = 300000  # 5 minutes
        self._audit_log = []
    
    def on_load(self, config: dict) -> bool:
        """Load auth matrix and webhook config."""
        try:
            self._config = config
            self._webhook_url = config.get("webhook_url", "")
            self._approval_timeout_ms = config.get("approval_timeout_ms", 300000)
            self._loaded = True
            print(f"[AuthOverlay] Loaded. Webhook: {'configured' if self._webhook_url else 'NOT CONFIGURED'}")
            return True
        except Exception as e:
            print(f"[AuthOverlay] Load FAILED: {e}")
            return False  # critical: true → Hermes refuses to start
    
    def check_auth(self, tool_name: str, operation: str) -> Dict[str, Any]:
        """Check auth level for tool+operation combination."""
        
        # Unknown tool → FORBIDDEN (fail-closed)
        if tool_name not in AUTH_MATRIX:
            self._audit_log.append({"tool": tool_name, "operation": operation, "result": "FORBIDDEN_UNKNOWN", "timestamp": time.time()})
            return {"action": "block", "reason": f"Unknown tool: {tool_name}", "auth_level": "FORBIDDEN"}
        
        # Check operation-level auth
        tool_matrix = AUTH_MATRIX[tool_name]
        if operation not in tool_matrix:
            return {"action": "block", "reason": f"Unknown operation: {operation}", "auth_level": "FORBIDDEN"}
        
        auth_level = tool_matrix[operation]
        
        if auth_level == AuthLevel.FORBIDDEN:
            self._audit_log.append({"tool": tool_name, "operation": operation, "result": "FORBIDDEN", "timestamp": time.time()})
            return {"action": "block", "reason": f"FORBIDDEN operation: {operation}", "auth_level": "FORBIDDEN"}
        
        elif auth_level == AuthLevel.DESTRUCTIVE_APPROVAL:
            approval_id = f"{tool_name}:{operation}:{int(time.time())}"
            self._pending_approvals[approval_id] = {
                "tool": tool_name, "operation": operation,
                "timestamp": time.time(), "status": "pending"
            }
            return {
                "action": "queue_approval",
                "approval_id": approval_id,
                "reason": f"DESTRUCTIVE operation requires approval: {tool_name}.{operation}",
                "auth_level": "DESTRUCTIVE_APPROVAL",
                "webhook_url": self._webhook_url
            }
        
        elif auth_level == AuthLevel.WRITE_NOTIFY:
            return {"action": "pass", "notify": True, "auth_level": "WRITE_NOTIFY"}
        
        else:  # READ_AUTO
            return {"action": "pass", "auth_level": "READ_AUTO"}
    
    def get_audit_summary(self) -> dict:
        """Return audit summary for monitoring."""
        return {
            "total_checks": len(self._audit_log),
            "forbidden_blocks": sum(1 for e in self._audit_log if e["result"].startswith("FORBIDDEN")),
            "pending_approvals": len(self._pending_approvals),
        }
```

### Step 4.3: Wire Auth Matrix to Hook Pipeline

**Configure in `config/hermes/config.yaml`:**
```yaml
plugins:
  auth_overlay:
    enabled: true
    path: "/home/guinevere/code/guinevere/plugins/auth_overlay.py"
    class: "AuthOverlayPlugin"
    priority: 90
    critical: true
    config:
      auth_matrix_path: "/home/guinevere/code/guinevere/config/hermes/auth_matrix.yaml"
      webhook_url: "${DISCORD_APPROVAL_WEBHOOK}"
      approval_timeout_ms: 300000
      on_timeout: "deny"
```

### Step 4.4: Configure Custom MCP Tools (7 kept on FastMCP)

**7 custom tools remain on `guinevere-mcp.service`:**

| Tool | Auth Level | Purpose |
|---|---|---|
| `postgres_tool` | DESTRUCTIVE_APPROVAL (write) / FORBIDDEN (drop) | PostgreSQL queries |
| `redis_tool` | WRITE_NOTIFY (write) / DESTRUCTIVE_APPROVAL (flush) | Redis operations |
| `obscura_cdp` | DESTRUCTIVE_APPROVAL (execute_js) | Browser automation |
| `grep_app` | READ_AUTO | Code search |
| `context7` | READ_AUTO | Documentation query |
| `sequential_thinking` | READ_AUTO | Reasoning tool |
| `time_tools` | READ_AUTO | Time utilities |

**Restart custom MCP server:**
```bash
sudo systemctl restart guinevere-mcp
```

### Step 4.5: Per-Tool Test Commands

```bash
# Test READ_AUTO tools (should pass silently)
hermes tool test brave_search "Python asyncio best practices"
hermes tool test grep_app "import asyncio" 
hermes tool test context7 "FastAPI middleware"
hermes tool test time_tools get_time

# Test WRITE_NOTIFY tools (should pass + notify)
hermes tool test filesystem write "/tmp/test.txt" "test content"
hermes tool test redis_tool set "test_key" "test_value"

# Test DESTRUCTIVE_APPROVAL (should block + webhook)
hermes tool test redis_tool flush "DB5"
# Expected: "Operation queued for approval. Approval ID: ..."

# Test FORBIDDEN (should hard-block)
hermes tool test terminal run "rm -rf /"
# Expected: "BLOCKED: FORBIDDEN operation"
```

### Step 4.6: Verify Plugin Load Gate

**Command:**
```bash
# Test that Hermes refuses to start without auth_overlay
hermes config set plugins.auth_overlay.enabled false
hermes gateway start 2>&1
# Expected: FAILS TO START. Error: "critical plugin auth_overlay not found"
hermes config set plugins.auth_overlay.enabled true  # Restore
```

---

## Safety Checkpoint

| # | Check | Command | Expected |
|---|---|---|---|
| P4-T1 | All 16 tools at correct auth level | `pytest tests/safety/test_auth_matrix_tools.py -v` | 64/64 correct mappings |
| P4-T2 | Plugin load gate | `hermes gateway start` without auth_overlay | FAILS with error |
| P4-T3 | FORBIDDEN commands blocked | `pytest tests/safety/test_forbidden_commands.py -v` | 7/7 blocked |
| P4-T4 | Budget: 80% alert, 100% block | `pytest tests/safety/test_budget_enforcement.py -v` | Thresholds correct |
| P4-T5 | Tool output sanitization | `pytest tests/safety/test_tool_output_sanitizer.py -v` | Credentials/DNR/forbidden → filtered |

---

## Config Changes

### `config/hermes/auth_matrix.yaml`:
```yaml
auth_matrix:
  web: { brave_search: READ_AUTO, exa_search: READ_AUTO, websearch: READ_AUTO, fetch: READ_AUTO }
  filesystem: { read: READ_AUTO, write: WRITE_NOTIFY, delete: DESTRUCTIVE_APPROVAL }
  terminal: { read_commands: READ_AUTO, write_commands: WRITE_NOTIFY, destructive_commands: DESTRUCTIVE_APPROVAL, forbidden_commands: FORBIDDEN }
  git: { read: READ_AUTO, write: WRITE_NOTIFY, destructive: DESTRUCTIVE_APPROVAL }
  fetch: { get: READ_AUTO, post: WRITE_NOTIFY, upload: DESTRUCTIVE_APPROVAL }
  postgres_tool: { select: READ_AUTO, insert: WRITE_NOTIFY, update: WRITE_NOTIFY, delete: DESTRUCTIVE_APPROVAL, ddl: DESTRUCTIVE_APPROVAL, drop: FORBIDDEN }
  redis_tool: { get: READ_AUTO, set: WRITE_NOTIFY, delete: WRITE_NOTIFY, flush: DESTRUCTIVE_APPROVAL, config: FORBIDDEN }
  obscura_cdp: { navigate: READ_AUTO, screenshot: READ_AUTO, fill_form: WRITE_NOTIFY, click: WRITE_NOTIFY, execute_js: DESTRUCTIVE_APPROVAL }
  grep_app: { search: READ_AUTO, search_github: READ_AUTO }
  context7: { query: READ_AUTO, resolve: READ_AUTO }
  sequential_thinking: { think: READ_AUTO }
  time_tools: { get_time: READ_AUTO, convert: READ_AUTO, calculate: READ_AUTO }
```

---

## File Changes

| File | Action | Description |
|---|---|---|
| `plugins/auth_overlay.py` | CREATE (~220 lines) | Auth matrix enforcement plugin |
| `config/hermes/mcp-servers.yaml` | CREATE (~90 lines) | MCP server configurations |
| `config/hermes/auth_matrix.yaml` | CREATE (~90 lines) | 4-level auth matrix for all 16 tools |
| `config/hermes/config.yaml` | MODIFY | Add auth_overlay plugin + MCP sections |
| `src/mcp/auth_matrix.py` | REFACTOR (240→~150) | Adapted to hook-based interception |
| `src/mcp/manager.py` | DELETE (74 lines) | Replaced by Hermes native MCP client |
| `src/mcp/tools/brave_search.py` | DELETE | Migrated to Hermes web native |
| `src/mcp/tools/exa_search.py` | DELETE | Migrated to Hermes web native |
| `src/mcp/tools/fetch.py` | DELETE | Migrated to Hermes fetch native |
| `src/mcp/tools/websearch.py` | DELETE | Migrated to Hermes web native |
| `src/mcp/tools/filesystem.py` | DELETE | Migrated to Hermes filesystem native |
| `src/mcp/tools/git_tool.py` | DELETE | Migrated to Hermes git native |
| `src/mcp/tools/github.py` | DELETE | Migrated to Hermes terminal+git native |
| `src/mcp/tools/docker_tool.py` | REFACTOR | Hybrid: terminal + custom restrictions |
| `src/mcp/tools/shell_tool.py` | REFACTOR | Hybrid: terminal + forbidden commands |

---

## Service Management

| Service | Action |
|---|---|
| Hermes gateway | STOP → ADD MCP → START |
| `guinevere-mcp` | RESTART (picks up config changes) |
| All other services | KEEP RUNNING |

---

## Risk Register

| Risk ID | Description | Score | Mitigation |
|---|---|---|---|
| R-P4-OVER-01 | Auth matrix bypass | 15 HIGH | Auth overlay `critical: true`; unknown → FORBIDDEN |
| R-P4-OVER-02 | Auth handles native + custom payloads | 9 MEDIUM | Operation-level mapping (48+ granular) |
| R-P4-01-001 | Native tools enabled without auth | 15 HIGH | Deploy auth overlay BEFORE or simultaneously with native tools |
| R-P4-03-001 | FORBIDDEN commands not blocked | 15 HIGH | Terminal blocked_commands list; 7 hard-forbidden commands tested |
| R-P4-02-001 | Plugin load gate fails to block | 12 HIGH | Test: Hermes refuses to start without auth_overlay |

---

## Rollback Procedure

```bash
# === PHASE 4 ROLLBACK (< 2 minutes) ===
hermes gateway stop
hermes mcp remove web filesystem terminal git fetch
rm -f plugins/auth_overlay.py
cd /home/guinevere/code/guinevere
git checkout -- src/mcp/manager.py src/mcp/auth_matrix.py src/mcp/tools/
sudo systemctl restart guinevere-mcp
hermes gateway start
```

---

## Test Commands

```bash
# All 16 tools functional
pytest tests/hermes/test_tool_*.py -v

# Auth overlay plugin tests
pytest tests/hermes/test_auth_overlay.py -v

# Native tool tests
pytest tests/hermes/test_tool_web_native.py -v
pytest tests/hermes/test_tool_filesystem_native.py -v
pytest tests/hermes/test_tool_terminal_native.py -v
pytest tests/hermes/test_tool_git_native.py -v
pytest tests/hermes/test_tool_docker_native.py -v

# Custom tool tests
pytest tests/hermes/test_tool_postgres_custom.py -v
pytest tests/hermes/test_tool_redis_custom.py -v
pytest tests/hermes/test_tool_obscura_custom.py -v
pytest tests/hermes/test_tool_grep_app_custom.py -v
pytest tests/hermes/test_tool_context7_custom.py -v
pytest tests/hermes/test_tool_sequential_thinking_custom.py -v
pytest tests/hermes/test_tool_time_custom.py -v

# Auth matrix enforcement: all 16 tools at correct level
pytest tests/hermes/test_auth_overlay.py::TestFullToolAuthMatrix -v

# Plugin load gate
pytest tests/hermes/test_auth_overlay.py::TestPluginLoadGate -v

# Unknown tool → FORBIDDEN
pytest tests/hermes/test_auth_overlay.py::TestUnknownToolForbidden -v

# Webhook approval path
pytest tests/hermes/test_auth_overlay.py::TestWebhookApproval -v
```

---

## Gate Criteria

| Criterion | Threshold | Measurement |
|---|---|---|
| All 16 tool capabilities available | 16/16 | `hermes mcp list` + custom tool status |
| Auth matrix enforced on all 16 | 64/64 correct mappings | `pytest tests/hermes/test_auth_overlay.py::TestFullToolAuthMatrix` |
| FORBIDDEN operations hard-disabled | 7/7 blocked | `pytest tests/safety/test_forbidden_commands.py` |
| DESTRUCTIVE_APPROVAL goes through webhook | Approval workflow functional | Manual test: destructive operation → Discord webhook |
| Plugin load gate | Hermes refuses without auth_overlay | `hermes gateway start` without plugin → FAILS |
| Unknown tools → FORBIDDEN | Fail-closed | `TestUnknownToolForbidden` |

---

## References

| Document | Relevance |
|---|---|
| `adr/ADR-035-hermes-migration.md` | §Phase 4 — MCP + Tools, §Pillar 4: MCP = HYBRID, §Appendix B: Auth Matrix |
| `adr/ADR-013-guinevere-mcp-native-opencode-replacement.md` | MCP native architecture |
| `research-reports/migration-plan/01-dependency-map.md` | §Phase 4 dependencies |
| `research-reports/migration-plan/02-risk-per-step.md` | §7 — Phase 4 risks (R-P4-*) |
| `research-reports/migration-plan/03-rollback-procedures.md` | §9 — Phase 4 rollback |
| `research-reports/migration-plan/04-safety-checkpoints.md` | §6 — Phase 4 safety checkpoint |
| `research-reports/migration-plan/06-file-inventory.md` | §Phase 4 — File changes |
| `research-reports/migration-plan/07-test-suite.md` | §8 — Phase 4 test suite |
| `research-reports/migration-plan/08-service-sequence.md` | §Phase 4 — Service management |
| `research-reports/migration-plan/09-config-migration.md` | §7 — Phase 4 config changes |