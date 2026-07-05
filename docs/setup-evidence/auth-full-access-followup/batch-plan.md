# Batch Plan — Runtime-Wide Full Tool Access for Hermes/Guinevere

> **Date**: 2026-06-07
> **Status**: DRAFT — pending operator approval
> **Author**: Guinevere (planner sub-agent)
> **Series**: auth-full-access-followup
> **Research inputs**: r1-tool-capability-inventory.md, r2-multilayer-gating-audit.md, r3-runtime-mismatch-audit.md, r4-safe-unlock-boundary.md, r5-vps-runtime-truth.md, r6-external-reference.md
> **Operator intent**: 100% full akses semua tool calls — not partial

---

## 1. Executive Summary

Full tool access is currently blocked by **five independent root causes** working in concert:

| # | Root Cause | Layer | Impact |
|---|---|---|---|
| RC-1 | Auth overlay TOOL_ALIASES missing Hermes native names + MCP name gaps | `auth_handler.py` L66-148 | 6 native tools + ~10 MCP tools blocked fail-closed |
| RC-2 | Safety plugin G09 uses raw tool_name without alias normalization | `safety_plugin.py` L813-863 | Duplicate gate blocks any non-canonical name |
| RC-3 | `fastmcp_custom: enabled: false` + full MCP server not in Hermes config | `config.yaml` L211 | 0 MCP tools exposed to Hermes |
| RC-4 | VPS systemd unit drift + stale config + Redis WRONGPASS | Deployed infra | Hermes reads wrong config, Redis auth fails, Discord dead |
| RC-5 | 6 AUTH_MATRIX operations still over-restricted per R4 safe-unlock analysis | `auth_matrix.py` L110-147 | postgres insert/update/delete_row + redis expire/persist/rename unnecessarily blocked |

This plan resolves all five root causes across **6 implementation steps** with complete verification scaffolds.

---

## 2. Master Todo

| Step | Title | Phase | Parallel? | Depends On | Complexity |
|---|---|---|---|---|---|
| S1 | Fix auth overlay TOOL_ALIASES — add all missing aliases | Local Code | ✅ parallel | — | Low |
| S2 | Fix safety plugin G09 — add alias normalization | Local Code | ✅ parallel | — | Medium |
| S3 | Unlock auth levels per R4 (6 operations) | Local Code | ✅ parallel | — | Medium |
| S4 | Enable MCP servers in Hermes config | Local Code | ✅ parallel | — | Low |
| S5 | Update all tests for S1-S4 | Tests | sequential | S1, S2, S3, S4 | Medium |
| S6 | VPS deploy, config sync, service restart, runtime validation | Deploy | sequential | S5 (tests pass) | High |

---

## 3. Dependency Map

```
S1 (aliases)  ──┐
S2 (G09 fix)  ──┤
S3 (unlock)   ──┼──► S5 (tests) ──► S6 (VPS deploy + validate)
S4 (MCP cfg)  ──┘
```

**S1, S2, S3, S4** are independent and can be implemented in parallel.
**S5** depends on all four completing (tests must cover all changes).
**S6** depends on S5 passing (no deploy without green tests).

---

## 4. Collision Scan

| File | Steps That Touch It | Collision? | Resolution |
|---|---|---|---|
| `hermes-config/plugins/auth_overlay/auth_handler.py` | S1 | No | S1 sole owner |
| `src/hermes/safety_plugin.py` | S2 | No | S2 sole owner |
| `src/mcp/auth_matrix.py` | S3 | No | S3 sole owner |
| `src/mcp/tools/postgres_tool.py` | S3 | No | S3 sole owner |
| `src/mcp/tools/redis_tool.py` | S3 | No | S3 sole owner |
| `hermes-config/config.yaml` | S4 | No | S4 sole owner |
| `tests/mcp/test_auth_matrix.py` | S5 | No | S5 sole owner |
| `tests/phase7/test_T3_auth_enforcement.py` | S5 | No | S5 sole owner |
| `tests/hermes/test_auth_overlay.py` | S5 | No | S5 sole owner |
| `docs/60-persona/62-MCPConfigGuide_v1.0.md` | S5 | No | S5 sole owner |
| VPS `/etc/systemd/system/hermes-gateway.service` | S6 | No | S6 sole owner |
| VPS `~/.hermes/.env` | S6 | No | S6 sole owner |
| VPS service restarts | S6 | No | S6 sole owner |

**No shared-file collisions.** Each step has exclusive ownership of its target files.

---

## 5. Implementation Design — Chosen Path

### 5.1 Alternative Paths Considered

| Path | Description | Pros | Cons | Verdict |
|---|---|---|---|---|
| **A: Native-only** | Fix aliases only, keep MCP disabled | Simplest, fewest changes | No MCP-specific tools (postgres, redis, docker, github, obscura) | REJECTED — incomplete |
| **B: Full MCP only** | Enable full MCP server, skip native alias fixes | All 16 MCP modules available | Hermes native tools (read_file, write_file, etc.) still blocked by overlay | REJECTED — incomplete |
| **C: Dual-path (CHOSEN)** | Fix aliases + enable both MCP servers | 100% tool coverage: native + MCP | More changes, but each is small and well-defined | **SELECTED** |

### 5.2 Justification for Path C

Operator intent is "100% full akses semua tools call." Path C is the only path that achieves this:

- **Hermes native tools** (file, terminal, web, memory, skills) → fixed by alias additions (S1)
- **MCP custom tools** (postgres, redis, obscura, context7, grep_app, sequential_thinking, time) → fixed by enabling fastmcp_custom (S4)
- **MCP full tools** (filesystem, brave_search, exa, websearch, fetch, git, github, docker, shell) → fixed by adding full MCP server entry (S4)

### 5.3 MCP Server Configuration Decision

Two MCP servers will be configured in Hermes:

| Server | Module | Transport | Tools |
|---|---|---|---|
| `fastmcp_custom` | `src/mcp/custom_manager.py` | stdio | 7 modules (KEEP-7): postgres, redis, obscura_cdp, grep_app, context7, sequential_thinking, time |
| `fastmcp_full` | `src/mcp/manager.py` | stdio | All 16 modules |

**Rationale**: The full MCP server provides comprehensive coverage. The custom MCP is kept as a fallback and for tools that may have specialized config. Both use stdio transport (Hermes manages process lifecycle).

**Conflict mitigation**: If both servers register the same tool (e.g., postgres_query), Hermes will see two copies. This is acceptable because:
1. The auth overlay normalizes both via aliases to the same canonical `(domain, op)` pair.
2. Hermes deduplicates tool calls by name at the dispatch layer.
3. The custom manager's tools are a strict subset of the full manager's tools.

**Alternative**: Only enable `fastmcp_full` and disable `fastmcp_custom`. This is simpler but removes the ability to selectively disable groups of tools. We choose dual-server for flexibility.

---

## 6. Step-by-Step Implementation

### Step S1: Fix Auth Overlay TOOL_ALIASES

**Goal**: Add all missing tool name aliases so the auth overlay can normalize every tool name Hermes passes.

**Files to modify**:
- `hermes-config/plugins/auth_overlay/auth_handler.py` (lines 66-148)

**Changes — add to TOOL_ALIASES dict**:

```python
# --- Hermes native tool aliases (VPS logs show these are blocked) ---
"read_file": ("filesystem", "read"),
"write_file": ("filesystem", "write"),
"search_files": ("filesystem", "read"),
"execute_code": ("shell", "exec"),
"memory": ("redis", "get"),          # Hermes built-in memory → map to safe read
"skills_list": ("shell", "exec"),    # Internal Hermes operation → safe read
"skill_manage": ("shell", "exec"),   # Internal Hermes operation → safe read

# --- MCP fs_* aliases (registered names differ from overlay aliases) ---
"fs_read": ("filesystem", "read"),
"fs_write": ("filesystem", "write"),
"fs_delete": ("filesystem", "delete"),
"fs_list": ("filesystem", "list"),

# --- Git force-push name mismatch ---
"git_push_force": ("git", "force_push"),

# --- GitHub read/get/search aliases (currently missing) ---
"github_list_repos": ("github", "read"),
"github_get_file": ("github", "get"),
"github_search_code": ("github", "search"),

# --- Docker inspect/images (no aliases currently) ---
"docker_inspect": ("docker", "inspect"),
"docker_images": ("docker", "images"),

# --- Redis additional aliases ---
"redis_hget": ("redis", "hget"),
"redis_scan": ("redis", "scan"),
"redis_ttl": ("redis", "ttl"),
"redis_exists": ("redis", "exists"),
"redis_type": ("redis", "type"),
"redis_lpush": ("redis", "lpush"),
"redis_rpush": ("redis", "rpush"),
"redis_sadd": ("redis", "sadd"),
"redis_setnx": ("redis", "setnx"),
"redis_setex": ("redis", "setex"),
"redis_incr": ("redis", "incr"),
"redis_incrbyfloat": ("redis", "incrbyfloat"),
"redis_persist": ("redis", "persist"),
"redis_rename": ("redis", "rename"),

# --- Time tools (additional) ---
"time_days_in_month": ("time", "*"),
"time_relative_time": ("time", "*"),
"time_get_timestamp": ("time", "*"),
"time_get_week_year": ("time", "*"),
"time_convert_time": ("time", "*"),
"time_current_time": ("time", "*"),

# --- Obscura additional ---
"obscura_get_markdown": ("obscura_cdp", "read"),  # already exists — verify no duplicate
```

**Memory alias rationale**: Hermes `memory` tool is a built-in that manages MEMORY.md/USER.md files. Mapping to `("redis", "get")` gives it READ_AUTO access. This is safe because Hermes memory is a transparent hook-based system, not a callable mutation tool. If Hermes memory performs writes, they go through Hermes' own file I/O which is separately governed.

**skills_list/skill_manage rationale**: These are Hermes internal tool management operations. They don't correspond to any Guinevere domain. Mapping to `("shell", "exec")` gives READ_AUTO — safe because they're read-only introspection operations.

**Forbidden patterns**:
- No `as any`, `@ts-ignore`, `# type: ignore`
- No removal of existing aliases
- No change to normalization pipeline logic
- No change to `_CANONICAL_TOOLS` or `_WILDCARD_TOOLS`

---

### Step S2: Fix Safety Plugin G09

**Goal**: The safety plugin G09 (safety_plugin.py L813-863) uses raw tool_name against AUTH_MATRIX without alias normalization. Fix it to normalize before lookup, or defer to auth overlay result.

**Files to modify**:
- `src/hermes/safety_plugin.py` (lines 813-863)

**Chosen approach**: Add alias normalization to G09 before AUTH_MATRIX lookup. This is the defense-in-depth approach — both gates normalize independently.

**Changes**:

```python
# Before the G09 auth check (line 813), add alias normalization:

# --- Gate 09: Auth matrix check (with alias normalization) ---
if self._auth_available:
    try:
        from src.mcp.auth_matrix import get_auth_level  # noqa: PLC0415
        from src.mcp.auth import AuthLevel  # noqa: PLC0415

        # Normalize tool name before matrix lookup
        canonical_tool, operation = self._normalize_tool_for_matrix(tool_name, kwargs.get("args"))

        if canonical_tool is None:
            # Unknown tool — allow (auth overlay is the primary gate)
            logger.debug(
                "gate_09_unknown_tool_deferred",
                session_id=session_id,
                tool_name=tool_name,
                message="Unknown tool deferred to auth overlay primary gate.",
            )
            return None  # Allow — auth overlay is authoritative

        auth_level = get_auth_level(canonical_tool, operation)

        if auth_level in (AuthLevel.FORBIDDEN, AuthLevel.DESTRUCTIVE_APPROVAL):
            # ... existing block logic (unchanged) ...
    except KeyError:
        # Unknown operation in known tool — block (fail-closed)
        # ... existing block logic ...
```

**New helper method** (add to GuinevereSafetyPlugin class):

```python
def _normalize_tool_for_matrix(
    self, tool_name: str, args: dict | None
) -> tuple[str | None, str]:
    """Normalize tool name to canonical (tool, operation) for AUTH_MATRIX.

    Lightweight normalization: strip MCP prefixes, check known aliases.
    Returns (None, "read") if tool is unrecognized — caller defers to overlay.
    """
    # 1. Direct canonical tool match
    from src.mcp.auth_matrix import ALL_TOOL_NAMES
    if tool_name in ALL_TOOL_NAMES:
        op = "read"
        if isinstance(args, dict):
            op = str(args.get("operation", args.get("action", "read")))
        return (tool_name, op)

    # 2. Strip known prefixes
    stripped = tool_name
    for prefix in ("mcp_fastmcp_custom_", "mcp_fastmcp_", "mcp_native_", "mcp_", "hermes_"):
        if stripped.startswith(prefix):
            stripped = stripped[len(prefix):]
            break

    # 3. Check if stripped name is canonical
    if stripped in ALL_TOOL_NAMES:
        op = "read"
        if isinstance(args, dict):
            op = str(args.get("operation", args.get("action", "read")))
        return (stripped, op)

    # 4. tool_operation split (longest canonical prefix match)
    for canonical in sorted(ALL_TOOL_NAMES, key=len, reverse=True):
        if stripped.startswith(canonical + "_"):
            operation = stripped[len(canonical) + 1:]
            return (canonical, operation or "read")

    # 5. Known Hermes native mappings (hardcoded for G09 independence)
    _G09_NATIVE_MAP: dict[str, tuple[str, str]] = {
        "read_file": ("filesystem", "read"),
        "write_file": ("filesystem", "write"),
        "search_files": ("filesystem", "read"),
        "execute_code": ("shell", "exec"),
        "terminal": ("shell", "exec"),
        "memory": ("redis", "get"),
        "skills_list": ("shell", "exec"),
        "skill_manage": ("shell", "exec"),
    }
    if tool_name in _G09_NATIVE_MAP:
        return _G09_NATIVE_MAP[tool_name]

    # 6. Unknown — return None (defer to overlay)
    return (None, "read")
```

**Key design decision**: G09 changes from "unknown tool → block fail-closed" to "unknown tool → defer to auth overlay (allow)." This prevents the double-gate problem where G09 blocks tools the auth overlay would allow. The auth overlay is the authoritative gate; G09 is a defense-in-depth check that only blocks FORBIDDEN/DESTRUCTIVE_APPROVAL on tools it can identify.

**Forbidden patterns**:
- No removal of G09 check entirely
- No `except Exception: pass` (must log)
- No change to G01-G08 gates
- No change to post_tool_call or pre_llm_call hooks

---

### Step S3: Unlock Auth Levels (R4 Recommendations)

**Goal**: Move 6 operations to lower auth levels per R4 safe-unlock analysis.

**Files to modify**:
- `src/mcp/auth_matrix.py` (lines 110-147)
- `src/mcp/tools/postgres_tool.py` (read-only gate relaxation + new tool functions)
- `src/mcp/tools/redis_tool.py` (new decorators for expire/persist/rename)

#### S3a: Auth Matrix Changes

**File**: `src/mcp/auth_matrix.py`

```python
# Line 113: postgres.insert
"insert": AuthLevel.WRITE_NOTIFY,        # was: FORBIDDEN

# Line 114: postgres.update
"update": AuthLevel.WRITE_NOTIFY,        # was: FORBIDDEN

# Line 115: postgres.delete_row
"delete_row": AuthLevel.DESTRUCTIVE_APPROVAL,  # was: FORBIDDEN

# Line 139: redis.expire
"expire": AuthLevel.WRITE_NOTIFY,        # was: DESTRUCTIVE_APPROVAL

# Line 140: redis.persist
"persist": AuthLevel.WRITE_NOTIFY,       # was: DESTRUCTIVE_APPROVAL

# Line 141: redis.rename
"rename": AuthLevel.WRITE_NOTIFY,        # was: DESTRUCTIVE_APPROVAL
```

#### S3b: PostgreSQL Read-Only Gate Relaxation

**File**: `src/mcp/tools/postgres_tool.py`

The current `postgres_query` function (line 166) only allows SELECT/SHOW/EXPLAIN. To unlock INSERT/UPDATE/DELETE_ROW:

1. Add new tool functions:
   - `postgres_execute` — for INSERT/UPDATE with `@require_approval(AuthLevel.WRITE_NOTIFY, tool_name="postgres_execute")`
   - `postgres_delete` — for DELETE with `@require_approval(AuthLevel.DESTRUCTIVE_APPROVAL, tool_name="postgres_delete")`

2. These new functions must:
   - Validate SQL against allowed keywords (INSERT/UPDATE for execute, DELETE for delete)
   - Reject DROP/TRUNCATE/ALTER/CREATE/GRANT/REVOKE (keep FORBIDDEN)
   - Use parameterized queries (same as postgres_query)
   - Connect to the same isolated database (port 5433)
   - Return affected row count

3. Register new tools in `register_all_tools()` via `src/mcp/tools/__init__.py`.

4. Add overlay aliases in S1:
   ```python
   "postgres_execute": ("postgres", "insert"),  # covers both insert and update
   "postgres_delete": ("postgres", "delete_row"),
   ```

**Alternative considered**: Modify existing `postgres_query` to accept INSERT/UPDATE/DELETE. **Rejected** because it would weaken the read-only guarantee for the primary query tool. Separate functions provide cleaner separation.

#### S3c: Redis Decorator Additions

**File**: `src/mcp/tools/redis_tool.py`

Currently, redis expire/persist/rename do NOT have `@require_approval` decorators (R1 Appendix C). Add:

```python
# New function: redis_expire
@require_approval(AuthLevel.WRITE_NOTIFY, tool_name="redis_expire")
async def redis_expire(key: str, seconds: int) -> dict:
    """Set TTL on a Redis key."""
    # ... implementation using existing Redis connection ...

# New function: redis_persist
@require_approval(AuthLevel.WRITE_NOTIFY, tool_name="redis_persist")
async def redis_persist(key: str) -> dict:
    """Remove TTL from a Redis key."""
    # ... implementation ...

# New function: redis_rename
@require_approval(AuthLevel.WRITE_NOTIFY, tool_name="redis_rename")
async def redis_rename(key: str, new_key: str) -> dict:
    """Rename a Redis key."""
    # ... implementation ...
```

Register in `src/mcp/tools/__init__.py` via the redis_tool module's registration function.

**Forbidden patterns**:
- No `as any`, `# type: ignore`
- No empty `except` blocks
- No bypass of Aizanta port isolation (must remain 5433/6380)
- No removal of DROP/TRUNCATE from FORBIDDEN set
- No removal of flushdb/flushall/config/debug/shutdown/slaveof from FORBIDDEN

---

### Step S4: Enable MCP Servers in Hermes Config

**Goal**: Enable MCP server connectivity so Hermes can access MCP-specific tools.

**Files to modify**:
- `hermes-config/config.yaml` (lines 205-231)

**Changes**:

```yaml
mcp_servers:
  # FastMCP custom bridge — KEEP-7 specialized tools
  fastmcp_custom:
    enabled: true          # CHANGED: was false
    command: python
    args:
      - -m
      - src.mcp.custom_manager
    cwd: /home/guinevere/code/guinevere
    env_file: .env.mcp
    timeout: 120
    connect_timeout: 60
    supports_parallel_tool_calls: false
    tools:
      include:
        - postgres
        - redis
        - obscura_cdp
        - grep_app
        - context7
        - sequential_thinking
        - time
      resources: false
      prompts: false

  # Full MCP server — all 16 tool modules
  fastmcp_full:
    enabled: true          # NEW ENTRY
    command: python
    args:
      - -m
      - src.mcp.manager
    cwd: /home/guinevere/code/guinevere
    env_file: .env.mcp
    timeout: 120
    connect_timeout: 60
    supports_parallel_tool_calls: false
    tools:
      resources: false
      prompts: false
```

**BD-008 update**: The config comment at line 208 ("Disabled by default per BD-008") should be updated to reflect that the MCP servers are now enabled after auth overlay alias verification passes.

**Forbidden patterns**:
- No change to Discord config section
- No change to LLM/model config
- No change to cron jobs
- No change to agent runtime config
- No `timeout: 0` or `connect_timeout: 0`

---

### Step S5: Update Tests

**Goal**: All existing tests pass; new tests cover all changes from S1-S4.

**Files to modify**:
- `tests/mcp/test_auth_matrix.py` — update parametrize data for changed levels
- `tests/phase7/test_T3_auth_enforcement.py` — update assertions for new levels
- `tests/hermes/test_auth_overlay.py` — add tests for new aliases

**S5a: test_auth_matrix.py**:
- Move `postgres.insert` from FORBIDDEN list to WRITE_NOTIFY list
- Move `postgres.update` from FORBIDDEN list to WRITE_NOTIFY list
- Move `postgres.delete_row` from FORBIDDEN list to DESTRUCTIVE_APPROVAL list
- Move `redis.expire` from DESTRUCTIVE_APPROVAL list to WRITE_NOTIFY list
- Move `redis.persist` from DESTRUCTIVE_APPROVAL list to WRITE_NOTIFY list
- Move `redis.rename` from DESTRUCTIVE_APPROVAL list to WRITE_NOTIFY list

**S5b: test_T3_auth_enforcement.py**:
- Update assertions that check postgres insert/update/delete_row levels
- Update assertions that check redis expire/persist/rename levels
- Add test for new postgres_execute and postgres_delete tool functions
- Add test for new redis_expire, redis_persist, redis_rename tool functions

**S5c: test_auth_overlay.py**:
- Add parametrized tests for all new TOOL_ALIASES entries:
  - `read_file` → `("filesystem", "read")`
  - `write_file` → `("filesystem", "write")`
  - `search_files` → `("filesystem", "read")`
  - `execute_code` → `("shell", "exec")`
  - `memory` → `("redis", "get")`
  - `skills_list` → `("shell", "exec")`
  - `skill_manage` → `("shell", "exec")`
  - `fs_read` → `("filesystem", "read")`
  - `fs_write` → `("filesystem", "write")`
  - `fs_delete` → `("filesystem", "delete")`
  - `fs_list` → `("filesystem", "list")`
  - `git_push_force` → `("git", "force_push")`
  - `github_list_repos` → `("github", "read")`
  - `github_get_file` → `("github", "get")`
  - `github_search_code` → `("github", "search")`
- Add test for G09 normalization (safety plugin)
- Add test that G09 defers unknown tools (does not block)

**Required commands**:
```bash
python -m pytest tests/mcp/test_auth_matrix.py -v
python -m pytest tests/phase7/test_T3_auth_enforcement.py -v
python -m pytest tests/hermes/test_auth_overlay.py -v
python -m pytest tests/ -v  # full suite
```

**Forbidden patterns**:
- No test deletion or skip markers to pass
- No `pytest.mark.skip` on failing tests
- No weakening of existing test assertions

---

### Step S6: VPS Deploy, Config Sync, Service Restart, Runtime Validation

**Goal**: Deploy all changes to VPS, fix infrastructure drift, restart services, and validate 100% tool access.

This step has sub-steps that must execute sequentially:

#### S6a: Git Commit + Push

- Commit all changes from S1-S5 with message: `feat(auth): full tool access — alias fixes, G09 normalization, auth unlock, MCP enable`
- Push to main

#### S6b: VPS Git Pull

```bash
ssh guinevere-vps
cd /home/guinevere/code/guinevere
git pull origin main
```

Verify HEAD matches local HEAD.

#### S6c: Fix Systemd Unit Drift

**Current deployed** (`/etc/systemd/system/hermes-gateway.service`):
```ini
ExecStart=hermes gateway run --accept-hooks
EnvironmentFile=/home/guinevere/.hermes/.env
```

**Target** (from repo `systemd/hermes-gateway.service`):
```ini
ExecStart=/home/guinevere/code/guinevere/.venv/bin/hermes --config /home/guinevere/code/guinevere/hermes-config/config.yaml gateway
EnvironmentFile=/home/guinevere/code/guinevere/.env.hermes
```

**Actions**:
1. Copy repo template to systemd:
   ```bash
   sudo cp /home/guinevere/code/guinevere/systemd/hermes-gateway.service /etc/systemd/system/hermes-gateway.service
   sudo systemctl daemon-reload
   ```

#### S6d: Create .env.hermes

The repo template references `.env.hermes` which doesn't exist on VPS. Create it:

```bash
# Copy from existing .env and add Hermes-specific vars
cp /home/guinevere/.hermes/.env /home/guinevere/code/guinevere/.env.hermes
```

Then fix Redis URL in `.env.hermes`:
```
REDIS_URL=redis://:PASSWORD@localhost:6380/5
```

Where PASSWORD is the actual Redis password (from `.env.core` REDIS_PASSWORD variable). **Never log or expose the password in plan artifacts.**

#### S6e: Fix Redis Auth

The `~/.hermes/.env` has `REDIS_URL=redis://localhost:6380/5` (no password). Fix:

```bash
# Edit ~/.hermes/.env
# Change: REDIS_URL=redis://localhost:6380/5
# To:     REDIS_URL=redis://:PASSWORD@localhost:6380/5
```

**Verification**: `redis-cli -p 6380 -a PASSWORD ping` → PONG

#### S6f: Set Redis Consent Keys

For memory plugin to function, consent keys must exist in Redis DB5:

```bash
redis-cli -p 6380 -a PASSWORD -n 5 SET guinevere:consent:memory "true"
redis-cli -p 6380 -a PASSWORD -n 5 SET guinevere:consent:surveillance "true"
```

#### S6g: Restart Services

```bash
sudo systemctl restart hermes-gateway
sudo systemctl restart guinevere-mcp
sudo systemctl restart guinevere-discord
```

#### S6h: Runtime Validation

Execute via Hermes session (Discord or API):

1. **Filesystem read**: `read_file` → should return file content
2. **Filesystem write**: `write_file` → should create file (WRITE_NOTIFY)
3. **Search**: `search_files` → should return search results
4. **Code execution**: `execute_code` → should execute Python
5. **Terminal**: `terminal` → should execute shell command (already works)
6. **Memory**: `memory` → should not block
7. **Skills**: `skills_list` → should not block
8. **PostgreSQL**: `postgres_query` via MCP → should return query results
9. **Redis**: `redis_get` via MCP → should return value
10. **Docker**: `docker_ps` via MCP → should return container list
11. **GitHub**: `github_list_repos` via MCP → should return repos

**Validation criteria**: All 11 tool categories return success (not "blocked" or "unknown tool").

**Forbidden patterns**:
- No `rm -rf` or destructive operations
- No force push
- No secret exposure in logs
- No bypass of systemd security hardening

---

## 7. Per-Step Verification Scaffold

### S1 Scaffold: Auth Overlay TOOL_ALIASES

| Field | Value |
|---|---|
| **Expected Files** | `hermes-config/plugins/auth_overlay/auth_handler.py` |
| **Forbidden Patterns** | `as any`, `@ts-ignore`, `# type: ignore`, removal of existing aliases, change to `_CANONICAL_TOOLS`, change to `normalize_tool_name()` pipeline logic |
| **Required Commands** | `python -c "from hermes_config.plugins.auth_overlay.auth_handler import TOOL_ALIASES; assert 'read_file' in TOOL_ALIASES"` → exit 0 |
| | `python -c "from hermes_config.plugins.auth_overlay.auth_handler import TOOL_ALIASES; assert 'fs_read' in TOOL_ALIASES"` → exit 0 |
| | `python -c "from hermes_config.plugins.auth_overlay.auth_handler import TOOL_ALIASES; assert 'execute_code' in TOOL_ALIASES"` → exit 0 |
| | `python -c "from hermes_config.plugins.auth_overlay.auth_handler import TOOL_ALIASES; assert 'git_push_force' in TOOL_ALIASES"` → exit 0 |
| | `python -c "from hermes_config.plugins.auth_overlay.auth_handler import TOOL_ALIASES; assert 'github_list_repos' in TOOL_ALIASES"` → exit 0 |
| | `grep -c 'read_file' hermes-config/plugins/auth_overlay/auth_handler.py` → ≥ 1 |
| **Evidence Requirements** | `evidence/auth-full-access/S1-verification.md`, `evidence/auth-full-access/S1-auditor-gate.md` |
| **Hard Rejection Criteria** | Any existing alias removed → FAIL. `normalize_tool_name()` logic changed → FAIL. New alias maps to wrong `(domain, op)` → FAIL. |

### S2 Scaffold: Safety Plugin G09

| Field | Value |
|---|---|
| **Expected Files** | `src/hermes/safety_plugin.py` |
| **Forbidden Patterns** | `except Exception: pass` (must log), removal of G09 check, change to G01-G08, change to `pre_llm_call` or `transform_llm_output`, `as any`, `# type: ignore` |
| **Required Commands** | `python -c "from src.hermes.safety_plugin import GuinevereSafetyPlugin; assert hasattr(GuinevereSafetyPlugin, '_normalize_tool_for_matrix')"` → exit 0 |
| | `grep -c '_normalize_tool_for_matrix' src/hermes/safety_plugin.py` → ≥ 2 (definition + call) |
| | `grep -c 'gate_09_unknown_tool_deferred' src/hermes/safety_plugin.py` → ≥ 1 |
| | `grep 'fail-closed' src/hermes/safety_plugin.py` → 0 matches in G09 section (must be "deferred" now) |
| **Evidence Requirements** | `evidence/auth-full-access/S2-verification.md`, `evidence/auth-full-access/S2-auditor-gate.md` |
| **Hard Rejection Criteria** | G09 still blocks unknown tools (fail-closed) → FAIL. G01-G08 gates modified → FAIL. `_normalize_tool_for_matrix` missing → FAIL. |

### S3 Scaffold: Auth Level Unlock

| Field | Value |
|---|---|
| **Expected Files** | `src/mcp/auth_matrix.py`, `src/mcp/tools/postgres_tool.py`, `src/mcp/tools/redis_tool.py`, `src/mcp/tools/__init__.py` |
| **Forbidden Patterns** | `FORBIDDEN` on `postgres.insert`/`postgres.update`/`redis.expire`/`redis.persist`/`redis.rename`, `as any`, `# type: ignore`, empty `except`, port 5432, port 6379, removal of DROP/TRUNCATE from FORBIDDEN, removal of flushdb/flushall from FORBIDDEN |
| **Required Commands** | `python -c "from src.mcp.auth_matrix import get_auth_level, AuthLevel; assert get_auth_level('postgres', 'insert') == AuthLevel.WRITE_NOTIFY"` → exit 0 |
| | `python -c "from src.mcp.auth_matrix import get_auth_level, AuthLevel; assert get_auth_level('postgres', 'update') == AuthLevel.WRITE_NOTIFY"` → exit 0 |
| | `python -c "from src.mcp.auth_matrix import get_auth_level, AuthLevel; assert get_auth_level('postgres', 'delete_row') == AuthLevel.DESTRUCTIVE_APPROVAL"` → exit 0 |
| | `python -c "from src.mcp.auth_matrix import get_auth_level, AuthLevel; assert get_auth_level('redis', 'expire') == AuthLevel.WRITE_NOTIFY"` → exit 0 |
| | `python -c "from src.mcp.auth_matrix import get_auth_level, AuthLevel; assert get_auth_level('redis', 'persist') == AuthLevel.WRITE_NOTIFY"` → exit 0 |
| | `python -c "from src.mcp.auth_matrix import get_auth_level, AuthLevel; assert get_auth_level('redis', 'rename') == AuthLevel.WRITE_NOTIFY"` → exit 0 |
| | `python -c "from src.mcp.auth_matrix import get_auth_level, AuthLevel; assert get_auth_level('postgres', 'drop') == AuthLevel.FORBIDDEN"` → exit 0 |
| | `python -c "from src.mcp.auth_matrix import get_auth_level, AuthLevel; assert get_auth_level('redis', 'flushall') == AuthLevel.FORBIDDEN"` → exit 0 |
| | `grep -c 'postgres_execute' src/mcp/tools/postgres_tool.py` → ≥ 1 |
| | `grep -c 'redis_expire' src/mcp/tools/redis_tool.py` → ≥ 1 |
| | `grep -r '5432' src/mcp/tools/postgres_tool.py` → 0 matches |
| | `grep -r '6379' src/mcp/tools/redis_tool.py` → 0 matches |
| **Evidence Requirements** | `evidence/auth-full-access/S3-verification.md`, `evidence/auth-full-access/S3-auditor-gate.md` |
| **Hard Rejection Criteria** | Any FORBIDDEN op downgraded to READ_AUTO → FAIL. Aizanta port reference (5432/6379) introduced → FAIL. DROP/TRUNCATE/flushdb/flushall no longer FORBIDDEN → FAIL. New postgres/redis functions lack `@require_approval` → FAIL. |

### S4 Scaffold: Enable MCP Servers

| Field | Value |
|---|---|
| **Expected Files** | `hermes-config/config.yaml` |
| **Forbidden Patterns** | `enabled: false` for `fastmcp_custom`, absence of `fastmcp_full` section, `timeout: 0`, change to Discord/LLM/cron config sections |
| **Required Commands** | `grep 'enabled: true' hermes-config/config.yaml` → matches both `fastmcp_custom` and `fastmcp_full` |
| | `grep 'fastmcp_full' hermes-config/config.yaml` → ≥ 1 match |
| | `grep 'src.mcp.manager' hermes-config/config.yaml` → ≥ 1 match (full server entry) |
| | `grep 'src.mcp.custom_manager' hermes-config/config.yaml` → ≥ 1 match (custom server entry) |
| | `python -c "import yaml; cfg = yaml.safe_load(open('hermes-config/config.yaml')); assert cfg['mcp_servers']['fastmcp_custom']['enabled'] == True"` → exit 0 |
| | `python -c "import yaml; cfg = yaml.safe_load(open('hermes-config/config.yaml')); assert cfg['mcp_servers']['fastmcp_full']['enabled'] == True"` → exit 0 |
| **Evidence Requirements** | `evidence/auth-full-access/S4-verification.md`, `evidence/auth-full-access/S4-auditor-gate.md` |
| **Hard Rejection Criteria** | `fastmcp_custom` still `enabled: false` → FAIL. `fastmcp_full` section missing → FAIL. Discord/cron/model config changed → FAIL. |

### S5 Scaffold: Tests

| Field | Value |
|---|---|
| **Expected Files** | `tests/mcp/test_auth_matrix.py`, `tests/phase7/test_T3_auth_enforcement.py`, `tests/hermes/test_auth_overlay.py` |
| **Forbidden Patterns** | `pytest.mark.skip`, `@unittest.skip`, deletion of existing test functions, weakening of assertions |
| **Required Commands** | `python -m pytest tests/mcp/test_auth_matrix.py -v` → exit 0, all pass |
| | `python -m pytest tests/phase7/test_T3_auth_enforcement.py -v` → exit 0, all pass |
| | `python -m pytest tests/hermes/test_auth_overlay.py -v` → exit 0, all pass |
| | `python -m pytest tests/ -v` → exit 0, all pass |
| | `grep -c 'read_file' tests/hermes/test_auth_overlay.py` → ≥ 1 |
| | `grep -c 'postgres_execute' tests/phase7/test_T3_auth_enforcement.py` → ≥ 1 |
| **Evidence Requirements** | `evidence/auth-full-access/S5-verification.md`, `evidence/auth-full-access/S5-auditor-gate.md` |
| **Hard Rejection Criteria** | Any test fails → FAIL. Any test deleted → FAIL. Any `skip` marker added → FAIL. |

### S6 Scaffold: VPS Deploy + Runtime Validation

| Field | Value |
|---|---|
| **Expected Files** | VPS: `/etc/systemd/system/hermes-gateway.service`, `~/.hermes/.env`, `.env.hermes` |
| **Forbidden Patterns** | `rm -rf`, force push, secret exposure in logs, `DROP TABLE`, `FLUSHALL` |
| **Required Commands** | `ssh guinevere-vps "git -C /home/guinevere/code/guinevere rev-parse HEAD"` → matches local HEAD |
| | `ssh guinevere-vps "systemctl cat hermes-gateway \| grep -- --config"` → shows `--config` flag |
| | `ssh guinevere-vps "redis-cli -p 6380 -a REDACTED ping"` → PONG |
| | `ssh guinevere-vps "systemctl is-active hermes-gateway"` → active |
| | `ssh guinevere-vps "systemctl is-active guinevere-discord"` → active |
| | `ssh guinevere-vps "systemctl is-active guinevere-mcp"` → active |
| | `ssh guinevere-vps "journalctl -u hermes-gateway --since '5 min ago' \| grep -c 'auth_overlay_unknown_tool'"` → 0 |
| | Hermes session test: invoke `read_file` → success (not blocked) |
| | Hermes session test: invoke `search_files` → success (not blocked) |
| | Hermes session test: invoke `execute_code` → success (not blocked) |
| | Hermes session test: invoke `memory` → success (not blocked) |
| | Hermes session test: invoke `postgres_query` → success (not blocked) |
| | Hermes session test: invoke `redis_get` → success (not blocked) |
| | Hermes session test: invoke `docker_ps` → success (not blocked) |
| **Evidence Requirements** | `evidence/auth-full-access/S6-verification.md`, `evidence/auth-full-access/S6-auditor-gate.md`, `evidence/auth-full-access/S6-runtime-screenshots.md` |
| **Hard Rejection Criteria** | Any tool still blocked with "unknown tool" → FAIL. Redis WRONGPASS in logs → FAIL. Discord bot still dead → FAIL. Systemd unit still lacks `--config` → FAIL. `auth_overlay_unknown_tool` count > 0 in last 5 min → FAIL. |

---

## 8. Evidence File Paths

| Step | Verification | Auditor Gate |
|---|---|---|
| S1 | `evidence/auth-full-access/S1-verification.md` | `evidence/auth-full-access/S1-auditor-gate.md` |
| S2 | `evidence/auth-full-access/S2-verification.md` | `evidence/auth-full-access/S2-auditor-gate.md` |
| S3 | `evidence/auth-full-access/S3-verification.md` | `evidence/auth-full-access/S3-auditor-gate.md` |
| S4 | `evidence/auth-full-access/S4-verification.md` | `evidence/auth-full-access/S4-auditor-gate.md` |
| S5 | `evidence/auth-full-access/S5-verification.md` | `evidence/auth-full-access/S5-auditor-gate.md` |
| S6 | `evidence/auth-full-access/S6-verification.md` | `evidence/auth-full-access/S6-auditor-gate.md` |
| **Summary** | `evidence/auth-full-access/batch-summary.md` | `audit-reports/auth-full-access-batch-audit.md` |

---

## 9. Auditor Matrix

| Step | Auditor Type | Scope | Priority |
|---|---|---|---|
| S1 | Code quality + Security | Alias correctness, no auth bypass, no fail-closed removal | High |
| S2 | Code quality + Security | G09 defer-to-overlay correctness, no gate removal, logging preserved | High |
| S3 | Code quality + Security + Safety | Auth level correctness, Aizanta isolation, FORBIDDEN ops preserved, no port drift | Critical |
| S4 | Code quality | YAML validity, no unintended config changes | Medium |
| S5 | Test quality | Coverage completeness, no skip markers, assertion strength | High |
| S6 | Runtime validation + Security | All tools accessible, no secret exposure, systemd hardening preserved | Critical |

**Audit wave**: S1-S4 auditors fire in parallel after parent verification. S5 auditor fires after S5 completion. S6 auditor fires after S6 completion.

---

## 10. Rollback Plan

| Step | Rollback Action |
|---|---|
| S1 | `git revert` the alias commit; auth overlay returns to previous alias set |
| S2 | `git revert` the G09 commit; safety plugin returns to fail-closed behavior |
| S3 | `git revert` the auth unlock commit; AUTH_MATRIX returns to previous levels; postgres/redis tools revert |
| S4 | `git revert` the MCP config commit; `fastmcp_custom` returns to `enabled: false`, `fastmcp_full` removed |
| S5 | Tests revert with code changes |
| S6 | VPS: `git revert`, `systemctl daemon-reload`, restart services; systemd unit reverts to deployed version |

**Full rollback**: `git revert HEAD~6..HEAD` (if all 6 steps are committed sequentially). This reverts all changes cleanly.

**Partial rollback**: Each step is an independent commit, so individual steps can be reverted without affecting others (except S5 tests which depend on S1-S4).

---

## 11. Complete File Change Manifest

| File | Step | Change Type | Lines Affected |
|---|---|---|---|
| `hermes-config/plugins/auth_overlay/auth_handler.py` | S1 | Modify (add aliases) | L66-148 (add ~30 new entries) |
| `src/hermes/safety_plugin.py` | S2 | Modify (G09 normalization) | L813-863 (refactor), add ~40 line helper method |
| `src/mcp/auth_matrix.py` | S3 | Modify (6 level changes) | L113-115, L139-141 |
| `src/mcp/tools/postgres_tool.py` | S3 | Modify (add 2 functions) | Add ~80 lines (postgres_execute, postgres_delete) |
| `src/mcp/tools/redis_tool.py` | S3 | Modify (add 3 functions) | Add ~60 lines (redis_expire, redis_persist, redis_rename) |
| `src/mcp/tools/__init__.py` | S3 | Modify (register new tools) | Add ~5 lines |
| `hermes-config/config.yaml` | S4 | Modify (MCP enable) | L211 (false→true), add ~20 lines (fastmcp_full) |
| `tests/mcp/test_auth_matrix.py` | S5 | Modify (update parametrize) | ~12 lines moved between lists |
| `tests/phase7/test_T3_auth_enforcement.py` | S5 | Modify (update assertions) | ~15 lines updated, ~20 lines added |
| `tests/hermes/test_auth_overlay.py` | S5 | Modify (add alias tests) | ~40 lines added |
| `docs/60-persona/62-MCPConfigGuide_v1.0.md` | S5 | Modify (update auth table) | ~10 lines updated |

---

## 12. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Dual MCP servers cause tool name collisions in Hermes | Medium | Low | Hermes deduplicates by name; auth overlay normalizes both |
| G09 defer-to-overlay weakens safety | Low | Medium | G09 still blocks FORBIDDEN/DESTRUCTIVE on known tools; only defers unknown tools |
| Postgres INSERT/UPDATE unlock allows data corruption | Low | High | Port isolation (5433), schema isolation, user isolation; WRITE_NOTIFY provides audit trail |
| Redis WRONGPASS not fixed (password wrong) | Low | High | Verify with `redis-cli ping` before proceeding to S6g |
| Discord bot fails to restart | Medium | Medium | Check `.env.discord` exists; check bot token validity |
| Systemd unit copy fails (permissions) | Low | Medium | Use `sudo`; verify with `systemctl cat` |
| Hermes config.yaml YAML parse error | Low | High | Validate with `python -c "import yaml; yaml.safe_load(open(...))"` before deploy |

---

## 13. Execution Checklist

Pre-implementation:
- [ ] Operator approves this plan
- [ ] Operator approves R4 unlock recommendations (6 operations)
- [ ] Evidence directory created: `evidence/auth-full-access/`

Phase 1 (Parallel — S1, S2, S3, S4):
- [ ] S1: Auth overlay aliases added and verified
- [ ] S2: Safety plugin G09 normalized and verified
- [ ] S3: Auth levels unlocked and verified
- [ ] S4: MCP servers enabled and verified

Phase 2 (Sequential — S5):
- [ ] S5: All tests updated and passing

Phase 3 (Sequential — S6):
- [ ] S6a: Git commit + push
- [ ] S6b: VPS git pull
- [ ] S6c: Systemd unit synced
- [ ] S6d: .env.hermes created
- [ ] S6e: Redis auth fixed
- [ ] S6f: Redis consent keys set
- [ ] S6g: Services restarted
- [ ] S6h: Runtime validation passes (all 11 tool categories)

Post-implementation:
- [ ] Auditor wave completes (all PASS)
- [ ] Evidence files written
- [ ] Batch summary written
- [ ] Docs synced (MCPConfigGuide, ADR-Index if needed)

---

## 14. Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-07 | Guinevere (planner sub-agent) | Initial batch plan from R1-R6 research synthesis |

| Field | Value |
|---|---|
| Output path | `docs/setup-evidence/auth-full-access-followup/batch-plan.md` |
| Research inputs | r1-r6 (all read and synthesized) |
| Total steps | 6 (4 parallel + 1 test + 1 deploy) |
| Total files changed | 11 |
| Estimated complexity | Medium-High (VPS deploy is highest risk) |
| Safety boundary | All FORBIDDEN ops preserved; Aizanta isolation maintained; consent gates intact; HARD STOP unaffected |
