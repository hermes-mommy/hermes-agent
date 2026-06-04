# 08 — MCP Native: Hermes MCP Ecosystem vs Guinevere Custom MCP

> **Date**: 2026-06-04
> **Scope**: Hermes native MCP client capabilities, Guinevere's current FastMCP server with 16 custom tools and auth matrix, migration assessment
> **Series**: Guinevere Hermes NousResearch Migration Assessment
> **Cross-references**: 05-MEMORY-BUILTIN.md, 06-MEMORY-EXTERNAL.md, 07-MEMORY-BRIDGE-GAP.md

---

## Executive Summary

Hermes Agent ships with a comprehensive native MCP client that supports tool server management (add/remove/list/serve/test/configure), dual transport (stdio + HTTP), OAuth authentication, auto-prefix collision avoidance, interactive server picker, catalog-based installation, and the ability to act as an MCP server itself (`hermes mcp serve`). Guinevere currently operates a **separate** MCP ecosystem: a custom FastMCP server (`src/mcp/manager.py`) with 16 purpose-built tools and a sophisticated 4-level auth matrix (`src/mcp/auth_matrix.py`) that enforces fine-grained operation-level access control with Discord webhook approval flows.

The two MCP systems are **completely independent** — Guinevere's `AIAgent` is constructed with `disabled_toolsets=["*"]` and `enabled_toolsets=[]`, which disables ALL Hermes MCP tools. Guinevere's 16 tools are served through its own FastMCP server, not through Hermes. This architectural choice preserves Guinevere's auth matrix and approval flow but foregoes Hermes MCP capabilities including auto-prefix, server catalog, picker UI, and OAuth support.

This report catalogs both systems, maps Guinevere's 16 tools to potential Hermes MCP equivalents, identifies gaps, and presents a migration path for tool ecosystem consolidation.

---

## 1. Hermes Native MCP Client — Full Capability Catalog

### 1.1 CLI Commands

```bash
# Server lifecycle
hermes mcp add <name> <command> [args...]     # Add stdio-based MCP server
hermes mcp remove <name>                       # Remove a configured server
hermes mcp list                                # List all configured MCP servers
hermes mcp serve                               # Start Hermes as MCP server
hermes mcp test <name>                         # Test server connectivity

# Configuration
hermes mcp configure <name>                    # Interactive server configuration
hermes mcp login <name>                        # OAuth authentication flow
hermes mcp picker                              # Interactive server selection from catalog
hermes mcp catalog                             # Browse installable MCP servers
hermes mcp install <server>                    # Install from catalog (or URL)
```

### 1.2 Transport Support

| Transport | Protocol | Use Case | Hermes Support |
|---|---|---|---|
| **stdio** | JSON-RPC over stdin/stdout | Local process-based MCP servers (e.g., npx-based) | Full support |
| **HTTP** | JSON-RPC over HTTP | Remote or HTTP-based MCP servers | Full support |
| **OAuth** | Authenticated HTTP | MCP servers requiring authentication | `hermes mcp login` flow |

### 1.3 Auto-Prefix Collision Avoidance

Hermes automatically prefixes MCP tool names with the server name to prevent collisions:

```
Pattern: mcp_<server_name>_<tool_name>

Examples:
  mcp_filesystem_read_file
  mcp_github_create_issue
  mcp_my_api_query_data
```

When a server also provides utility operations (`list_resources`, `read_resource`, `list_prompts`, `get_prompt`), these follow the same pattern:

```
  mcp_github_list_resources
  mcp_github_read_resource
  mcp_filesystem_list_prompts
  mcp_filesystem_get_prompt
```

### 1.4 Server Configuration YAML

```yaml
mcp_servers:
  filesystem:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/home/user/projects"]
    # stdio transport

  github:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "***"
    tools:
      include: [list_issues, create_issue, search_code]  # whitelist
      prompts: false
      resources: false

  my_api:
    url: "https://api.example.com/mcp"
    headers:
      Authorization: "Bearer ${MY_API_TOKEN}"
    timeout: 30
    connect_timeout: 10
    # HTTP transport

  parallel_docs:
    command: "docs-server"
    supports_parallel_tool_calls: true
    # Enables concurrent execution of safe tools
```

### 1.5 Hermes as MCP Server (`hermes mcp serve`)

When Hermes acts as an MCP server, it exposes:

| Tool | Description |
|---|---|
| `conversations_list` | List all conversations/sessions |
| `conversation_get` | Get a specific conversation by ID |
| `messages_read` | Read messages from a conversation |
| `attachments_fetch` | Fetch file attachments |
| `events_poll` | Poll for new events |
| `events_wait` | Block and wait for new events |
| `messages_send` | Send a message (when acting as gateway) |
| `channels_list` | List available channels |
| `permissions_list_open` | List open permission requests |
| `permissions_respond` | Respond to permission requests |

### 1.6 Per-Server Tool Filtering

```yaml
mcp_servers:
  github:
    tools:
      include: [list_issues, create_issue]   # Only these tools
      # OR
      exclude: [delete_repo, force_push]     # Everything except these
    prompts: false    # Don't expose prompt utilities
    resources: false  # Don't expose resource utilities
```

### 1.7 Parallel Tool Execution

```yaml
mcp_servers:
  fast_api:
    supports_parallel_tool_calls: true
    # Hermes can call multiple tools from this server concurrently
```

---

## 2. Guinevere Current MCP System

### 2.1 Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     Guinevere MCP System                          │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │               FastMCP Server (manager.py)                   │  │
│  │                                                            │  │
│  │  Dynamic tool registration:                                │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │  │
│  │  │ brave_   │ │ context7 │ │ docker_  │ │ exa_     │     │  │
│  │  │ search   │ │          │ │ tool     │ │ search   │     │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘     │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │  │
│  │  │ fetch    │ │ filesys  │ │ git_tool │ │ github   │     │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘     │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │  │
│  │  │ grep_app │ │ obscura  │ │ postgres │ │ redis_   │     │  │
│  │  │          │ │ _cdp     │ │ _tool    │ │ tool     │     │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘     │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │  │
│  │  │ sequent  │ │ shell    │ │ time_    │ │ websearch│     │  │
│  │  │ _thinking│ │ _tool    │ │ tools    │ │          │     │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘     │  │
│  └───────────────────────────┬────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────▼────────────────────────────────┐  │
│  │              Auth Layer (auth.py + auth_matrix.py)          │  │
│  │                                                            │  │
│  │  Every tool call → get_auth_level(tool, operation)         │  │
│  │                     ↓                                      │  │
│  │  ┌─────────────────┬──────────────────────────────────┐   │  │
│  │  │ AuthLevel        │ Behavior                         │   │  │
│  │  ├─────────────────┼──────────────────────────────────┤   │  │
│  │  │ READ_AUTO        │ Execute immediately              │   │  │
│  │  │ WRITE_NOTIFY     │ Execute + Discord notification   │   │  │
│  │  │ DESTRUCTIVE_     │ Discord webhook → asyncio.Event  │   │  │
│  │  │ APPROVAL         │ (5-min timeout) → execute/deny   │   │  │
│  │  │ FORBIDDEN        │ Block immediately; NEVER execute │   │  │
│  │  └─────────────────┴──────────────────────────────────┘   │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              Tool Isolation                                 │  │
│  │  • filesystem: path whitelist                              │  │
│  │  • shell: forbidden command blocking (rm -rf /, sudo, etc) │  │
│  │  • postgres: FORBIDDEN for insert/update/delete/drop       │  │
│  │  • redis: FORBIDDEN for flushdb/flushall/config/shutdown   │  │
│  │  • git: FORBIDDEN for force_push_main                      │  │
│  │  • docker: FORBIDDEN for system_prune/rm_all               │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 Complete 16-Tool Auth Matrix

**Auth Level Legend**: `RA`=READ_AUTO, `WN`=WRITE_NOTIFY, `DA`=DESTRUCTIVE_APPROVAL, `FB`=FORBIDDEN

| Tool | Operations | Auth Levels |
|---|---|---|
| `brave_search` | All | `RA` |
| `context7` | resolve, query | `RA`, `RA` |
| `exa` | All | `RA` |
| `fetch` | All | `RA` |
| `grep_app` | All | `RA` |
| `sequential_thinking` | All | `RA` |
| `time` | All | `RA` |
| `websearch` | All | `RA` |
| `filesystem` | read, list, write, delete | `RA`, `RA`, `WN`, `DA` |
| `github` | read, get, search, create_issue, create_pr, delete_repo | `RA`, `RA`, `RA`, `WN`, `WN`, `DA` |
| `obscura_cdp` | navigate, read, form_fill, click, file_upload | `RA`, `RA`, `WN`, `WN`, `DA` |
| `git` | log, diff, status, commit, push, force_push, force_push_main | `RA`, `RA`, `RA`, `WN`, `WN`, `DA`, `FB` |
| `postgres` | select, explain, insert, update, delete_row, drop, truncate | `RA`, `RA`, `FB`, `FB`, `FB`, `FB`, `FB` |
| `redis` | get/lrange/hget/hgetall/keys/scan/ttl/exists/type (9 reads), set/hset/lpush/rpush/sadd/setnx/setex/incr/incrbyfloat (8 writes), del/expire/persist/rename (4 destructive), flushdb/flushall/config/debug/shutdown/slaveof (6 forbidden) | 9×`RA`, 8×`WN`, 4×`DA`, 6×`FB` |
| `shell` | exec, rm_rf_root, sudo_rm_rf | `DA`, `FB`, `FB` |
| `docker` | ps, logs, inspect, images, start, stop, restart, rm, rmi, system_prune, rm_all | 4×`RA`, 3×`WN`, 2×`DA`, 2×`FB` |

### 2.3 Approval Flow Details

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Agent wants │     │  Auth Matrix │     │  Discord     │
│  to execute  │────▶│  Lookup      │────▶│  Webhook     │
│  tool        │     │              │     │  Notification│
└──────────────┘     └──────┬───────┘     └──────┬───────┘
                            │                     │
                   ┌────────▼────────┐            │
                   │  AuthLevel?     │            │
                   └────────┬────────┘            │
          ┌─────────────────┼─────────────────┐   │
          ▼                 ▼                 ▼   │
   ┌──────────┐    ┌──────────────┐   ┌──────────┐│
   │READ_AUTO │    │WRITE_NOTIFY  │   │FORBIDDEN ││
   │Execute   │    │Execute +     │   │Block     ││
   │immediate │    │Notify        │   │immediate ││
   └──────────┘    └──────────────┘   └──────────┘│
                                    ┌──────────────▼┐
                                    │DESTRUCTIVE_   │
                                    │APPROVAL       │
                                    │              │
                                    │ 1. Send      │
                                    │    Discord    │
                                    │    webhook    │
                                    │ 2. asyncio.   │
                                    │    Event.wait │
                                    │    (5 min)    │
                                    │ 3. Execute or │
                                    │    deny       │
                                    └──────────────┘
```

---

## 3. Tool Mapping: Guinevere 16 Tools to Hermes MCP

### 3.1 Can Be Served by Standard MCP Servers

| Guinevere Tool | Standard MCP Server Equivalent | Transport | Status |
|---|---|---|---|
| `filesystem` | `@modelcontextprotocol/server-filesystem` | stdio (npx) | **Available** — mature, widely used |
| `github` | `@modelcontextprotocol/server-github` | stdio (npx) | **Available** — mature, widely used |
| `postgres` | `@modelcontextprotocol/server-postgres` | stdio (npx) | **Available** — mature |
| `redis` | `@anthropic/mcp-server-redis` or custom | stdio/HTTP | **Available** — community or custom |
| `git` | `@modelcontextprotocol/server-git` or custom | stdio | **Partial** — standard git MCP exists but may not match Guinevere's operation set |
| `brave_search` | `@anthropic/mcp-server-brave-search` | stdio | **Available** |
| `fetch` | `@modelcontextprotocol/server-fetch` | stdio | **Available** |
| `docker` | Community MCP servers exist | stdio | **Available** — community-maintained |

### 3.2 Require Custom MCP Servers

| Guinevere Tool | Why Custom | Effort |
|---|---|---|
| `context7` | Context7 is a specific documentation API with resolve/query semantics — no standard MCP server exists | **Medium** — wrap existing `src/mcp/tools/context7.py` logic in MCP server |
| `exa_search` | Exa is a specific search API — no standard MCP server | **Medium** — wrap existing logic |
| `grep_app` | GitHub code search with custom patterns — no standard MCP server | **Medium** — wrap existing logic |
| `obscura_cdp` | Custom Chrome DevTools Protocol browser automation — highly Guinevere-specific | **High** — complex browser automation logic |
| `sequential_thinking` | Custom reasoning tool unique to Guinevere's agent loop | **Low** — lightweight, logic-only |
| `shell_tool` | Custom shell with forbidden command blocking and path isolation — safety-critical | **High** — cannot trust generic shell MCP |
| `time_tools` | Timezone-aware time utilities — straightforward but no standard MCP server | **Low** — simple utility |
| `websearch` | Aggregated web search with multiple backends — no standard MCP server | **Medium** — wrap existing logic |

### 3.3 Mapping Summary

| Category | Count | Tools |
|---|---|---|
| **Standard MCP available** | 8 | filesystem, github, postgres, redis, git, brave_search, fetch, docker |
| **Requires custom MCP server** | 8 | context7, exa_search, grep_app, obscura_cdp, sequential_thinking, shell_tool, time_tools, websearch |

---

## 4. Gap Analysis: Hermes MCP vs Guinevere MCP

### 4.1 What Hermes MCP Has That Guinevere Lacks

| Capability | Hermes Implementation | Guinevere Gap | Relevance |
|---|---|---|---|
| **Auto-prefix naming** | `mcp_<server>_<tool>` prevents collisions | Guinevere tools are flat-named; collisions possible if two servers expose same tool | **Medium** — Guinevere has only one MCP server, so collisions are unlikely |
| **Server catalog** | `hermes mcp catalog` browses installable servers | No catalog — all tools are custom-built | **Low** — Guinevere's tools are purpose-built |
| **Picker UI** | `hermes mcp picker` interactive selection | No picker — tools are registered at startup | **Low** — not needed for pre-configured agent |
| **OAuth support** | `hermes mcp login` for authenticated servers | No OAuth flow — API keys are env-based | **Low** — SOPS+age already handles secrets |
| **Parallel tool calls** | `supports_parallel_tool_calls` per server | No parallel execution model | **Medium** — could improve performance for independent tool calls |
| **Per-server tool filtering** | `include`/`exclude` lists per server | Filtering is auth-level based, not server-based | **Low** — different filtering philosophy |
| **MCP server mode** | `hermes mcp serve` exposes session/channel/attachment tools | No equivalent — Guinevere's MCP is tool-only, no session introspection | **Medium** — could enable external monitoring |

### 4.2 What Guinevere MCP Has That Hermes Lacks

| Capability | Guinevere Implementation | Hermes Gap | Criticality |
|---|---|---|---|
| **4-level auth matrix** | READ_AUTO, WRITE_NOTIFY, DESTRUCTIVE_APPROVAL, FORBIDDEN | No auth level concept — tools are either enabled or disabled | **Critical** — safety |
| **Operation-level auth** | Every operation has its own auth level (e.g., git commit=WN, git force_push_main=FB) | Server-level enable/disable only; no operation granularity | **Critical** — safety |
| **Discord approval flow** | Webhook notification + asyncio.Event blocking (5-min timeout) for destructive ops | No approval flow | **Critical** — operator control |
| **FORBIDDEN operations** | Hard block — postgres insert/update/delete/drop/truncate, redis flushdb/flushall, shell rm_rf_root, git force_push_main | No concept of permanently forbidden operations | **Critical** — safety |
| **Path whitelist (filesystem)** | Filesystem tool restricted to allowed directories | Generic filesystem access (any path passed as arg) | **Critical** — security |
| **Forbidden command blocking (shell)** | Shell tool blocks destructive patterns (rm -rf /, sudo, etc.) | No command pattern blocking | **Critical** — security |
| **Tool isolation** | Each tool has independent safety constraints | No isolation — tools share server-level config | **High** — security |
| **Budget tracking** | `src/mcp/budget.py` and `src/mcp/cost.py` track tool costs | No cost tracking for tool execution | **Medium** — cost management |
| **Tool selector** | `src/mcp/tool_selector.py` dynamically selects tools based on context | All enabled tools are available to agent | **Medium** — efficiency |

---

## 5. Migration Assessment

### 5.1 Option A: Keep Guinevere MCP (Status Quo)

**Description**: Continue serving all 16 tools through Guinevere's FastMCP server with auth matrix. Do not adopt Hermes MCP.

**Assessment**: This is the **correct current state**. Guinevere's auth matrix provides safety guarantees that Hermes MCP cannot match:
- Operation-level auth (128+ individual operation mappings)
- FORBIDDEN level for permanent safety blocks
- Discord approval flow for destructive operations
- Path whitelisting and command pattern blocking
- Budget and cost tracking

**Risk**: None. This is the safe default.

### 5.2 Option B: Migrate All Tools to Hermes MCP

**Description**: Convert all 16 tools to standard or custom MCP servers registered with Hermes. Remove Guinevere's FastMCP server.

**Assessment**: **NOT RECOMMENDED**. The auth matrix is safety-critical and Hermes MCP has no equivalent mechanism. Losing operation-level auth, FORBIDDEN blocks, approval flows, and tool isolation would be a regression. Additionally, 8 tools would still need custom MCP servers, so only half the migration yields standardization benefit.

**Risks**:
- Loss of auth matrix → safety regression
- Custom MCP servers still needed for 8 tools
- Hermes MCP API changes could break tool connectivity
- No FORBIDDEN operations → dangerous operations become possible

### 5.3 Option C: Hybrid — Standard Servers via Hermes, Safety-Critical via Guinevere (Recommended)

**Description**: Register standard MCP servers (filesystem, github, postgres, redis, git, brave_search, fetch, docker) with Hermes MCP but **with tool filtering to exclude unsafe operations**. Keep safety-critical and custom tools (shell_tool, obscura_cdp, sequential_thinking, context7, exa_search, grep_app, time_tools, websearch) in Guinevere's FastMCP server with full auth matrix. The Guinevere auth matrix becomes a **safety overlay** that intercepts tool calls regardless of which MCP server they originate from.

**Architecture**:

```
┌──────────────────────────────────────────────────────────────────┐
│                     Hybrid MCP Architecture                       │
│                                                                  │
│  ┌──────────────────────────────┐  ┌──────────────────────────┐  │
│  │  Hermes MCP (Standard)       │  │  Guinevere MCP (Custom)   │  │
│  │                              │  │                          │  │
│  │  mcp_filesystem_*            │  │  shell_tool              │  │
│  │  mcp_github_*                │  │  obscura_cdp             │  │
│  │  mcp_postgres_*              │  │  sequential_thinking     │  │
│  │  mcp_redis_*                 │  │  context7                │  │
│  │  mcp_git_*                   │  │  exa_search              │  │
│  │  mcp_brave_search            │  │  grep_app                │  │
│  │  mcp_fetch                   │  │  time_tools              │  │
│  │  mcp_docker_*                │  │  websearch               │  │
│  └──────────────┬───────────────┘  └──────────┬───────────────┘  │
│                 │                              │                 │
│                 └──────────┬───────────────────┘                 │
│                            │                                     │
│              ┌─────────────▼──────────────┐                     │
│              │  Guinevere Auth Overlay     │                     │
│              │  (Safety Gate)             │                     │
│              │                            │                     │
│              │  Every tool call → get_    │                     │
│              │  auth_level(tool, op) →    │                     │
│              │  enforce level             │                     │
│              │                            │                     │
│              │  ┌──────────────────────┐  │                     │
│              │  │ HERMES TOOLS         │  │                     │
│              │  │ • Safe ops → pass    │  │                     │
│              │  │ • Dangerous ops via  │  │                     │
│              │  │   Hermes → BLOCKED   │  │                     │
│              │  │   at auth overlay    │  │                     │
│              │  └──────────────────────┘  │                     │
│              │  ┌──────────────────────┐  │                     │
│              │  │ GUINEVERE TOOLS      │  │                     │
│              │  │ • Full auth matrix   │  │                     │
│              │  │ • Approval flow      │  │                     │
│              │  │ • Tool isolation     │  │                     │
│              │  └──────────────────────┘  │                     │
│              └────────────────────────────┘                     │
└──────────────────────────────────────────────────────────────────┘
```

**Advantages**:
- Standard tools get Hermes-native integration (auto-prefix, parallel calls, catalog)
- Safety-critical tools remain in Guinevere with full auth matrix
- Auth overlay ensures Hermes tools cannot bypass safety constraints
- Hermes tools filtered to exclude unsafe operations at server config level
- Incremental adoption — add standard servers one at a time
- Auth matrix expanded to cover Hermes-prefixed tool names

**Disadvantages**:
- Increased complexity (two MCP backends + overlay)
- Auth matrix must be updated for Hermes-prefixed names
- Dual tool naming (Guinevere flat vs Hermes `mcp_` prefix)
- Hermes MCP tools need tool filtering to avoid exposing dangerous ops

### 5.4 Auth Matrix Extension for Hybrid Mode

When Hermes MCP servers are registered, the auth matrix must be extended to cover `mcp_`-prefixed tool names:

```python
# Extension to AUTH_MATRIX in auth_matrix.py

AUTH_MATRIX_HERMES_OVERLAY = {
    # Standard MCP servers via Hermes — safety-filtered
    "mcp_filesystem": {
        "read_file": AuthLevel.READ_AUTO,
        "list_directory": AuthLevel.READ_AUTO,
        "write_file": AuthLevel.WRITE_NOTIFY,
        "delete_file": AuthLevel.DESTRUCTIVE_APPROVAL,
        # write/delete must go through approval flow
    },
    "mcp_github": {
        "list_issues": AuthLevel.READ_AUTO,
        "search_code": AuthLevel.READ_AUTO,
        "create_issue": AuthLevel.WRITE_NOTIFY,
        "create_pr": AuthLevel.WRITE_NOTIFY,
        # delete_repo excluded at Hermes config level (tools.include)
    },
    "mcp_postgres": {
        "query": AuthLevel.READ_AUTO,
        "execute": AuthLevel.FORBIDDEN,
        # All mutations FORBIDDEN — must use Guinevere postgres_tool
        # which already has FORBIDDEN for insert/update/delete/drop
    },
    # ... other Hermes tools mapped similarly
}
```

---

## 6. Recommendations

### 6.1 Immediate: Keep Status Quo

Do not migrate any tools to Hermes MCP until the auth overlay is designed and tested. The current system is safe and functional. Migration offers standardization benefits but introduces auth bypass risk.

### 6.2 Short-term: Auth Overlay Design

Design the auth overlay layer that intercepts tool calls from both Guinevere MCP and Hermes MCP and enforces a unified auth matrix. This is the prerequisite for any hybrid approach.

### 6.3 Medium-term: Standard Servers via Hermes

Once auth overlay is in place:
1. Register `@modelcontextprotocol/server-filesystem` via Hermes MCP with tool filtering (write/delete require approval)
2. Register `@modelcontextprotocol/server-github` via Hermes MCP with tool filtering
3. Test auth overlay interception on Hermes-originated calls
4. Gradually add more standard servers (postgres, redis, git, brave_search, fetch, docker)

### 6.4 Long-term: Full Ecosystem Consolidation

- All 8 standard tools served by Hermes MCP with auth overlay
- 8 custom tools remain in Guinevere MCP with full auth matrix
- Unified tool registry maps both Hermes-prefixed and Guinevere-flat tool names
- Auth matrix covers all tools regardless of origin
- Cost tracking updated for dual-backend architecture

### 6.5 Do Not Migrate

The following MUST remain in Guinevere's MCP with full auth matrix — NEVER delegate to Hermes or standard MCP servers:

| Tool | Reason |
|---|---|
| `shell_tool` | Forbidden command blocking; path isolation; safety-critical |
| `obscura_cdp` | Custom CDP logic; browser isolation; highly Guinevere-specific |
| `postgres_tool` (write ops) | FORBIDDEN for mutations; must maintain operation-level control |
| `redis_tool` (destructive ops) | FORBIDDEN for flush/config; must maintain operation-level control |

---

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Hermes MCP tool bypasses auth | Medium | **Critical** | Auth overlay intercepts ALL tool calls; test with Hermes-originated calls |
| Standard MCP server exposes unsafe ops | High | **Critical** | Hermes `tools.include` whitelist; auth overlay as second gate |
| Auth matrix naming mismatch | High | Medium | Extend matrix with `mcp_`-prefixed names; test completeness |
| Dual-backend complexity | High | Medium | Clean interface; comprehensive tests; documentation |
| Hermes MCP server unavailable | Low | Medium | Health checks; fallback to Guinevere equivalent |
| Standard MCP server API drift | Medium | Medium | Version pinning; integration tests |
| Operator confusion (two naming schemes) | Medium | Low | Documentation; consistent tool selection logic |

---

## 8. Implementation Sequence

```
Phase 1 (Immediate): Status quo — keep all 16 tools in Guinevere MCP
                     No Hermes MCP servers registered

Phase 2 (Short-term): Design and implement auth overlay
                      Extend AUTH_MATRIX with mcp_ prefix entries
                      Test overlay interception

Phase 3 (Medium-term): Register 1-2 standard MCP servers via Hermes
                       Start with filesystem (lowest risk)
                       Test auth overlay on Hermes-originated calls
                       Verify approval flow works for Hermes tools

Phase 4 (Medium-term): Register remaining standard servers
                       github, postgres (read-only), redis (read-only),
                       git (read-only ops), brave_search, fetch, docker

Phase 5 (Long-term): Full consolidation
                     Unified tool registry
                     Updated cost tracking
                     Documentation and runbooks
```

---

## 9. Footer

| Field | Value |
|---|---|
| Report | 08-MCP-NATIVE.md |
| Series | Guinevere Hermes NousResearch Migration Assessment |
| Date | 2026-06-04 |
| Status | Complete |
| Sources | Hermes Agent official docs (MCP feature page, MCP guide), Guinevere source code (manager.py, auth_matrix.py, auth.py, all 16 tool modules), Hermes integration research (01-hermes-api-surface.md), Hermes Phase 2 research reports |
| Recommendation | **Option C (Hybrid)** — Standard servers via Hermes with auth overlay; safety-critical tools remain in Guinevere MCP |