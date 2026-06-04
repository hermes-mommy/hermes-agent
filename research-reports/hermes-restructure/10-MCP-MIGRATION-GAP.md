# Report 10: MCP Migration Gap Analysis

**Date:** 2026-06-04
**Author:** Guinevere (automated research synthesis)
**Subject:** Guinevere 16 Custom MCP Tools to Hermes Native Toolsets Migration Mapping
**Status:** RESEARCH REPORT -- No Implementation
**Cross-Reference:** Report 09 (Tools System), Report 11 (Skills System)

---

## 1. Executive Summary

Guinevere operates **16 custom MCP tools** served through a bespoke MCP server with a **4-level auth matrix** (READ_AUTO, WRITE_NOTIFY, DESTRUCTIVE_APPROVAL, FORBIDDEN) and a **Discord webhook approval flow** for destructive operations. Hermes NousResearch provides **12 available native toolsets** with a simpler binary enable/disable model per platform.

Of the 16 Guinevere tools:
- **5 can migrate directly** to Hermes native equivalents with low risk
- **2 can migrate partially** with reduced capability or hybrid wrappers
- **7 have no Hermes equivalent** and must continue as custom implementations
- **1 (sequential_thinking) is not a tool** -- it is an agent reasoning pattern

The **auth matrix is a critical gap**: Hermes has no equivalent to Guinevere's 4-level granularity, Discord webhook approval, or command-blocking. This must be preserved via Hermes plugin architecture or custom wrapper code.

---

## 2. Detailed Tool-by-Tool Migration Mapping

### 2.1 Direct Migration Candidates (LOW RISK)

| # | Guinevere Tool | Auth Level | Hermes Equivalent | Migration Path | Risk |
|---|---------------|------------|-------------------|----------------|------|
| 1 | `brave_search` | READ_AUTO | `web` (Brave backend) | Enable `web`, configure Brave API key | LOW |
| 2 | `exa_search` | READ_AUTO | `web` (Exa backend) | Enable `web`, configure Exa API key | LOW |
| 3 | `websearch` | READ_AUTO | `web` | Enable `web`, generic search config | LOW |
| 4 | `fetch` | READ_AUTO | `web` (fetch mode) | Built into `web` toolset | LOW |
| 5 | `filesystem` | WRITE_NOTIFY | `file` | Enable `file`, verify path whitelist | MEDIUM |

#### Migration Detail: Search Consolidation

```yaml
# Current Guinevere: 4 separate search tools
brave_search:  # Brave Search API wrapper
exa_search:    # Exa Search API wrapper
websearch:     # Generic web search abstraction
fetch:         # Raw URL content fetcher

# Target Hermes: single 'web' toolset
web:
  backends:
    - brave    # maps brave_search
    - exa      # maps exa_search
    - generic  # maps websearch
  modes:
    - search   # query-based search
    - fetch    # URL content extraction (maps fetch)
```

**Migration gain**: 4 tools collapse into 1 toolset with backend configuration. No functional loss. API key provisioning is the only blocker.

#### Migration Detail: Filesystem

```yaml
# Current Guinevere 'filesystem' MCP tool
filesystem:
  path_whitelist:    # Reads from allowed dirs only
    - /home/guinevere/projects/
    - /home/guinevere/data/
  operations:
    read:  READ_AUTO
    write: WRITE_NOTIFY    # Logged write operations
    list:  READ_AUTO
  forbidden:              # Blocked paths
    - /etc/
    - /home/guinevere/.ssh/

# Target Hermes 'file' toolset
# UNKNOWN: Does Hermes enforce path whitelist?
# RISK: If no whitelist, this is a security regression
```

**Pre-migration audit required**: Verify Hermes `file` path restrictions. If absent, Hermes `file` can only be used for read operations, with Guinevere `filesystem` retained for writes.

### 2.2 Partial Migration Candidates (MEDIUM RISK)

| # | Guinevere Tool | Auth Level | Hermes Equivalent | Migration Path | Risk |
|---|---------------|------------|-------------------|----------------|------|
| 6 | `context7` | READ_AUTO | `web` (partial) | Context7 has SDK-specific query format. Hermes `web` may not support Context7's API protocol directly. Consider a lightweight custom wrapper that uses Hermes `web` as transport. | MEDIUM |
| 7 | `shell_tool` | DESTRUCTIVE_APPROVAL | `terminal` | **HIGH RISK**. Hermes `terminal` likely lacks command blocking. Must audit before migration. | HIGH |

#### Migration Detail: shell_tool -> terminal (SECURITY-CRITICAL)

```yaml
# Current Guinevere 'shell_tool' security model
shell_tool:
  auth_level: DESTRUCTIVE_APPROVAL
  approval_flow:
    type: discord_webhook
    timeout_seconds: 300
    required_approvers: 1
    description: "5-min timeout, user must approve in Discord"
  blocked_patterns:
    - "rm -rf /"
    - "DROP "
    - "> /dev/"
    - "chmod 777 /"
    - "mkfs."
    - "dd if="
    - "shutdown"
    - "reboot"
    - "wget.*| sh"
    - "curl.*| bash"
  allowed_commands:
    - git
    - python
    - node
    - npm
    - pip
    - docker
    - systemctl
    - journalctl
    - grep
    - find

# Target Hermes 'terminal' -- SECURITY GAP
# UNKNOWN: command filtering?
# UNKNOWN: destructive operation gating?
# UNKNOWN: approval flow?
# RISK: If Hermes 'terminal' runs raw shell with no filtering,
#       this is an UNACCEPTABLE regression.
```

**Verdict**: Do NOT migrate `shell_tool` to Hermes `terminal` unless:
1. Hermes `terminal` supports command pattern blocking, OR
2. A custom plugin wraps Hermes `terminal` with the blocking layer, OR
3. Hermes `terminal` is disabled on all platforms and Guinevere `shell_tool` persists

### 2.3 No Hermes Equivalent (Custom Must Persist)

| # | Guinevere Tool | Auth Level | Why No Equivalent | Preservation Strategy |
|---|---------------|------------|-------------------|----------------------|
| 8 | `docker_tool` | WRITE_NOTIFY | No Docker toolset in Hermes | Port as Hermes custom plugin |
| 9 | `git_tool` | WRITE_NOTIFY | No VCS toolset in Hermes | Port as Hermes custom plugin |
| 10 | `github` | WRITE_NOTIFY | No GitHub API toolset | Port as Hermes custom plugin |
| 11 | `grep_app` | READ_AUTO | No code search toolset | Port as Hermes custom plugin |
| 12 | `postgres_tool` | DESTRUCTIVE_APPROVAL | No DB toolset | Must persist -- CRITICAL |
| 13 | `redis_tool` | WRITE_NOTIFY | No cache toolset | Must persist -- CRITICAL |
| 14 | `time_tools` | READ_AUTO | No time utility toolset | Embed as Hermes skill or plugin |
| 15 | `obscura_cdp` | DESTRUCTIVE_APPROVAL | Hermes has `browser` but not CDP-specific | Keep as custom; evaluate `browser` overlap |

#### Critical Infrastructure Tools

```
postgres_tool:  # CRITICAL -- Guinevere's data layer
  - Schema management, query execution, migration support
  - DROP prevention built in
  - No Hermes equivalent exists or is planned

redis_tool:     # CRITICAL -- Guinevere's cache/session layer
  - Session state, rate limiting, pub/sub
  - No Hermes equivalent exists or is planned
```

These two tools are **non-negotiable**. They must persist as custom implementations regardless of Hermes migration.

### 2.4 Not a Tool: Agent Reasoning Pattern

| # | Guinevere Tool | Actual Category | Hermes Status |
|---|---------------|-----------------|---------------|
| 16 | `sequential_thinking` | Agent reasoning pattern (CoT) | May be innate to Hermes agent loop -- not a standalone tool |

`sequential_thinking` is a MCP tool wrapper around chain-of-thought reasoning. Hermes likely implements its own reasoning patterns internally. If Hermes' native reasoning is sufficient, this tool can be deprecated.

---

## 3. Auth Matrix Migration Strategy

### 3.1 Current Guinevere Auth Matrix

| Level | Abbreviation | Behavior | Applied To |
|-------|-------------|----------|------------|
| 0 | READ_AUTO | Execute automatically, no notification | Search, fetch, read-only |
| 1 | WRITE_NOTIFY | Execute + notify user | File writes, git commits, Redis writes |
| 2 | DESTRUCTIVE_APPROVAL | Require Discord webhook approval, 5-min timeout | Shell commands, DB operations, CDP |
| 3 | FORBIDDEN | Never execute, block at MCP layer | Destructive patterns, SSH, secrets |

### 3.2 Hermes Auth Model (Current Understanding)

```
Hermes: Per-toolset enable/disable per platform
- enable  = tool is available
- disable = tool is unavailable
- No intermediate levels observed
- No approval flow observed
```

**Gap**: Hermes' binary enable/disable does not provide the granularity Guinevere requires for:
- Automatic execution with audit trail (WRITE_NOTIFY)
- User approval gating with timeout (DESTRUCTIVE_APPROVAL)
- Pattern-based blocking (FORBIDDEN)

### 3.3 Auth Preservation Strategy

#### Option A: Hermes Plugin with Auth Layer
```
Hermes Plugin: guinevere-auth-middleware
  - Intercepts all tool invocations
  - Checks auth level from a configurable matrix
  - WRITE_NOTIFY: allows execution, sends Discord notification
  - DESTRUCTIVE_APPROVAL: pauses execution, sends webhook, waits 5 min
  - FORBIDDEN: blocks at plugin level before tool runs
```

#### Option B: Dual Tool System
```
- Hermes native: READ_AUTO tools only (file reads, web search)
- Guinevere MCP: WRITE_NOTIFY + DESTRUCTIVE_APPROVAL tools
- Bridge: Hermes delegates to MCP for gated operations
```

#### Option C: Hermes Custom Tool Wrappers
```
- Each DESTRUCTIVE_APPROVAL tool wrapped as Hermes custom tool
- Custom tool contains auth logic before delegating to actual operation
- Leverages Hermes plugin lifecycle hooks for injection
```

**Recommendation**: Option A (plugin middleware) is cleanest. Option B is safest (no auth regression). Option C is most Hermes-native.

---

## 4. Discord Webhook Approval Flow Preservation

### 4.1 Current Flow

```
1. User issues destructive command via Discord
2. MCP server classifies as DESTRUCTIVE_APPROVAL
3. MCP sends Discord webhook: "Approve? [Yes] [No] -- 5 min timeout"
4. If user clicks Yes within 300s -> execute
5. If timeout or No -> reject with audit log
6. All approvals/rejections logged to evidence trail
```

### 4.2 Preservation in Hermes Context

```
Hermes Custom Plugin: guinevere-approval-gate
  Lifecycle hook: pre_tool_execution
  - Check tool auth level in config
  - If DESTRUCTIVE_APPROVAL:
    - Emit Discord webhook with approve/reject buttons
    - Block tool execution thread
    - Await webhook response or timeout
    - Log decision to audit trail
  - If timeout:
    - Reject tool execution
    - Log timeout event
  - If approved:
    - Allow tool execution
    - Log approval event
```

**Hermes plugin hook points to investigate**:
| Hook | Phase | Use |
|------|-------|-----|
| `before_tool_call` | Pre-execution | Inject auth check + webhook |
| `after_tool_call` | Post-execution | Log results to audit |
| `on_tool_error` | Error | Log failures |

---

## 5. Risk Assessment Per Migration Path

### 5.1 Low-Risk Migrations

| Tool | Migration Path | Risk | Mitigation |
|------|---------------|------|------------|
| `brave_search` -> `web` | Configure Brave API key in Hermes | LOW | Verify search results parity |
| `exa_search` -> `web` | Configure Exa API key in Hermes | LOW | Verify search results parity |
| `websearch` -> `web` | Generic search config | LOW | Test query coverage |
| `fetch` -> `web` (fetch mode) | Built into web toolset | LOW | Test URL fetch parity |

### 5.2 Medium-Risk Migrations

| Tool | Migration Path | Risk | Mitigation |
|------|---------------|------|------------|
| `filesystem` -> `file` | Enable Hermes `file` | MEDIUM | Audit path whitelist; keep Guinevere `filesystem` as safety net |
| `context7` -> `web` | Partial migration | MEDIUM | Context7 SDK has unique API; may need custom wrapper |

### 5.3 High-Risk Migrations

| Tool | Migration Path | Risk | Mitigation |
|------|---------------|------|------------|
| `shell_tool` -> `terminal` | Enable Hermes `terminal` | **HIGH** | Do NOT migrate without command-blocking audit. Keep Guinevere `shell_tool` until Hermes terminal security is verified. |

### 5.4 Blocked Migrations (Must Persist as Custom)

| Tool | Reason | Impact |
|------|--------|--------|
| `postgres_tool` | No Hermes equivalent, critical data layer | CRITICAL |
| `redis_tool` | No Hermes equivalent, critical cache layer | CRITICAL |
| `docker_tool` | No Hermes equivalent | HIGH |
| `git_tool` | No Hermes equivalent | HIGH |
| `github` | No Hermes equivalent | HIGH |
| `grep_app` | No Hermes equivalent | MEDIUM |
| `obscura_cdp` | Hermes `browser` unproven, CDP-specific needs | HIGH |
| `time_tools` | No Hermes equivalent | LOW |

---

## 6. Phased Migration Roadmap

### Phase 1: Foundation (Weeks 1-2)
- Provision API keys for `web` toolset (Brave, Exa)
- Install Chrome/browser-cdp for `browser` toolset
- Audit Hermes `terminal` and `file` security models
- Design auth middleware plugin architecture (Option A/B/C decision)

### Phase 2: Low-Risk Migration (Weeks 3-4)
- Migrate `brave_search`, `exa_search`, `websearch`, `fetch` -> Hermes `web`
- Migrate `filesystem` (read-only) -> Hermes `file`
- Run parallel: Guinevere MCP + Hermes native for migrated tools
- Validate parity for 2 weeks before disabling MCP equivalents

### Phase 3: Auth Layer (Weeks 5-6)
- Implement auth middleware plugin for Hermes
- Port Discord webhook approval flow
- Test with DESTRUCTIVE_APPROVAL tools (shell_tool, postgres_tool)

### Phase 4: Custom Tool Porting (Weeks 7-10)
- Port `docker_tool` as Hermes custom plugin
- Port `git_tool` + `github` as Hermes custom plugins
- Port `grep_app` as Hermes custom plugin
- Port `time_tools` as Hermes skill or plugin
- Evaluate `obscura_cdp` vs Hermes `browser` -- keep better one
- Keep `postgres_tool` and `redis_tool` as custom (no alternative)

### Phase 5: Deprecation (Week 11+)
- Disable migrated MCP tools
- Full switch to Hermes native + custom plugins
- Remove redundant MCP server code
- Update AGENTS.md workflow patterns

---

## 7. Summary: What Survives, What Migrates, What's New

| Category | Count | Tools |
|----------|-------|-------|
| **Migrate to Hermes native** | 5 | brave_search, exa_search, websearch, fetch, filesystem |
| **Partial/Hybrid migration** | 2 | context7, shell_tool (blocked pending audit) |
| **Port as Hermes custom plugin** | 5 | docker_tool, git_tool, github, grep_app, time_tools |
| **Must persist as custom MCP** | 3 | postgres_tool, redis_tool, obscura_cdp |
| **Deprecate (agent-internal)** | 1 | sequential_thinking |

**End state**: Hermes native (7 toolsets) + Custom plugins (5) + Persistent MCP (3) = 15 functional tools. Net reduction from 16 MCP tools to 8 custom (5 plugins + 3 MCP), with 7 becoming Hermes-native.

---

## 8. Evidence and References

- Guinevere MCP source: 16 tools with auth matrix, Discord webhook flow
- `hermes tools list`: 24 toolsets, 12 available
- `hermes doctor`: dependency gaps identified
- `hermes plugins list`: 3 browser plugins, plugin lifecycle hooks
- Cross-reference: Report 09 for tools inventory
- Cross-reference: Report 11 for skills ecosystem
- Cross-reference: Report 12 for SOUL.md integration

---

## 9. Footer

| Field | Value |
|-------|-------|
| Report ID | RR-HERMES-10 |
| Version | 1.0 |
| Date | 2026-06-04 |
| Status | RESEARCH COMPLETE |
| Next | Report 11: SKILLS-SYSTEM.md |
| Author | Guinevere (automated research synthesis) |