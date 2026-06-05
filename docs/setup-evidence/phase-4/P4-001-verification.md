# P4-001 Verification — Hermes MCP Config Baseline

| Field | Value |
|---|---|
| P4 Step | P4-001 — Hermes MCP config baseline |
| Status | VERIFIED |
| Date | 2026-06-05 |
| Evidence Root | `docs/setup-evidence/phase-4/` |
| Planner Gate | `docs/setup-evidence/phase-4/planner-gate-phase-4-execution.md` |
| Authority | Python `src/mcp/auth_matrix.py` (BD-006) |

---

## 1. Config Diff Summary

### 1.1 `mcp_servers` Section — Full Replacement

**Before (non-standard legacy format):**

```yaml
mcp_servers:
  web:
    enabled: true
    tools:
      - brave_search
      - exa_search
      - fetch_url
      - websearch
  filesystem:
    enabled: true
    root_path: /home/guinevere/code/guinevere
    allowed_paths:
      - /home/guinevere/code/guinevere
    blocked_paths:
      - /etc
      - /root
      - /home/guinevere/.ssh
  terminal:
    enabled: true
    allowed_commands:
      - "ls,cat,head,tail,grep,find,wc,sort,uniq"
      # ... non-standard keys
  git:
    enabled: true
    allowed_operations:
      - status, diff, log, branch, checkout, add, commit, push, pull
    # ... non-standard keys
  fetch:
    enabled: true
    timeout_seconds: 30
    max_response_size_mb: 10
```

The old config used native Hermes toolset configuration keys (`root_path`, `allowed_paths`, `blocked_paths`, `allowed_commands`, `blocked_commands`, `allowed_operations`, `blocked_operations`, `timeout_seconds`, `max_response_size_mb`) inside `mcp_servers`. These are **not valid Hermes MCP server definitions** — they are native toolset configs that Hermes handles separately as built-in capabilities.

**After (documented Hermes mcp_servers shape):**

```yaml
mcp_servers:
  fastmcp_custom:
    enabled: false
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
```

Changes:
- Removed 5 native tool entries (`web`, `filesystem`, `terminal`, `git`, `fetch`) from `mcp_servers` — they are built-in Hermes capabilities, not MCP servers
- Added `fastmcp_custom` stdio MCP server with documented Hermes shape (`command`/`args`/`cwd`/`env_file`, `timeout`, `connect_timeout`, `supports_parallel_tool_calls`, `tools.include`/`resources`/`prompts`)
- Server is `enabled: false` per BD-008 native exposure gate
- Added comprehensive header comments documenting: Hermes documented shape, native exposure gate (BD-008), auth source (BD-006), canonical ports

### 1.2 `auth_matrix` Section — Reference-Only Annotation

Added header warning:
```
# WARNING: This YAML auth_matrix is REFERENCE ONLY and does NOT drive runtime
# auth decisions. Python src/mcp/auth_matrix.py is the sole runtime auth
# source (BD-006). Any divergence between this reference and the Python source
# must be resolved by updating the Python source, NOT this YAML.
```

No runtime values changed.

### 1.3 Other Sections

No changes to: `discord`, `model`, `providers`, `budget`, `agent`, `memory`, `hooks`, `cron`, `observability`, `approval`, `audit`.

---

## 2. Canonical Ports Proof

| Port | Service | How Referenced | Present? |
|------|---------|----------------|----------|
| 6380 | Redis (Aizanta) | Comment in `mcp_servers` header + existing `model.providers` section | ✅ |
| 5433 | Postgres (Aizanta) | Comment in `mcp_servers` header | ✅ |
| 20128 | 9Router | Used in `model.base_url` and `providers.ninerouter.base_url` | ✅ |

No references to forbidden ports 5432 or 6379 anywhere in the config.

---

## 3. Native Exposure Proof / Limitation

### Gate Status: ENABLED (blocking)

| Check | Status | Detail |
|-------|--------|--------|
| Direct native production tools exposed in `mcp_servers` | ❌ NONE | All native tool entries removed from `mcp_servers` |
| Any MCP server enabled | ❌ NO | `fastmcp_custom.enabled: false` |
| Tools with native production capability accessible | ❌ NO | Native tools (filesystem, shell, terminal, git, web, fetch, docker, github) not included in any MCP server's `tools.include` |
| Native exposure gate comment present | ✅ YES | `NATIVE EXPOSURE GATE (BD-008 / P4-001)` section in mcp_servers header |
| Pre-tool_call blocking proof | ❌ NOT YET | Deferred to P4-002 (auth overlay) — this is a Wave 2 dependency |

**Rationale per BD-008 / Oracle Risk F2:** Direct native production tool exposure via MCP servers remains disabled until `pre_tool_call` blocking proof passes. The auth overlay plugin (P4-002) will implement this proof. Until then, the only MCP server defined is disabled, and native Hermes built-in toolsets remain available but are not routed through `mcp_servers`.

**Limitation:** Native Hermes built-in toolsets (web, filesystem, terminal, git, fetch, etc.) are still available as built-in Hermes capabilities — this is Hermes platform behavior, not MCP server configuration. The auth overlay (P4-002) will gate these at the `pre_tool_call` hook level.

---

## 4. Auth Source Statement

| Check | Status | Detail |
|-------|--------|--------|
| Python `src/mcp/auth_matrix.py` exists | ✅ YES | 16 tools, 80 operations, `get_auth_level()` raises `KeyError` on unknown (fail-closed) |
| Python `verify_matrix_completeness()` exists | ✅ YES | Asserts all 16 tools registered |
| YAML `auth_matrix` section present | ✅ YES | Retained for reference only |
| YAML `auth_matrix` declared reference-only | ✅ YES | Header comment: "REFERENCE ONLY" + "Python src/mcp/auth_matrix.py is the sole runtime auth source" |
| Runtime auth driven by YAML | ❌ NO | Only Python `auth_matrix.py` is imported at runtime |

**Authority:** Python `src/mcp/auth_matrix.py` is the sole runtime auth source (BD-006). The YAML `auth_matrix` is retained as documentation/reference but must not be used for runtime auth decisions.

---

## 5. Scaffold Compliance

### Expected Files

| File | Status |
|------|--------|
| `hermes-config/config.yaml` | ✅ Modified — `mcp_servers` replaced, `auth_matrix` annotated |
| `tests/hermes/test_mcp_config.py` | ✅ Created — 25 tests |
| `docs/setup-evidence/phase-4/P4-001-verification.md` | ✅ Created — this file |

### Forbidden Patterns Check

| Pattern | Search Result | Status |
|---------|---------------|--------|
| `redis://localhost:6379` | 0 matches | ✅ PASS |
| `localhost:5432` | 0 matches | ✅ PASS |
| `critical:\s*true` (in config.yaml) | 0 matches | ✅ PASS |
| Plaintext secrets regex | 0 matches | ✅ PASS |

### Required Commands

| Command | Exit Code | Result |
|---------|-----------|--------|
| `python -m pytest tests/hermes/test_mcp_config.py -v` | 0 | 25/25 PASS |
| `python -m compileall hermes-config` | 0 | All files compiled |

### Hard Rejection Criteria

| Criterion | Status |
|-----------|--------|
| Missing/invalid `mcp_servers` | ✅ `mcp_servers` present with valid shape |
| Direct native exposure without auth-block proof | ✅ All servers disabled; no native production tools in any include list |
| YAML auth matrix treated as runtime source | ✅ Declared reference-only with clear warning |
| Any 5432/6379 reference | ✅ None found |
| Secrets in config | ✅ None found |

---

## 6. Files Changed

| File | Change Type | Summary |
|------|-------------|---------|
| `hermes-config/config.yaml` | Modify | Replaced `mcp_servers` with documented shape; added reference-only annotation to `auth_matrix` |
| `tests/hermes/test_mcp_config.py` | Create | 25 tests across 7 test classes validating shape, forbidden patterns, ports, exposure gate, auth source, YAML validity |
| `docs/setup-evidence/phase-4/P4-001-verification.md` | Create | This evidence file |

---

## 7. Design Decisions and Caveats

1. **Native Hermes toolsets remain built-in available.** This config only controls MCP server definitions. Native Hermes capabilities (web search, filesystem access, terminal, git, fetch) are platform built-ins and are NOT gated by `mcp_servers` configuration. True gating requires the auth overlay plugin (P4-002) and `pre_tool_call` hook interception.

2. **FastMCP custom bridge is placeholder-only.** The `fastmcp_custom` server definition uses `command: python -m src.mcp.custom_manager` which does not yet exist as a runnable module. P4-005 will create the actual bridge and enable the server after FastMCP `_config` compatibility fix.

3. **No runtime deployment.** This is a local config baseline only. Live VPS deployment requires explicit approval per project policy.

4. **Typed YAML parsing.** Test file uses recursive `ConfigValue`/`ConfigMap` aliases plus `typing.cast` for YAML-loaded data; no `Any` or type-suppression comments are introduced.

---

## 8. Boundary Compliance

- No persona drift: config change is technical, not behavioral
- No consent violation: no surveillance, approval, or consent changes
- No Y6 or HARD STOP bypass
- No secret/intimate data exposure
- No hidden coercion or control removal

---

## 9. Footer

| Field | Value |
|---|---|
| Evidence Path | `docs/setup-evidence/phase-4/P4-001-verification.md` |
| Prepared By | P4-001 Implementation |
| Next Steps | Wave 2: P4-002 (auth overlay) — requires `pre_tool_call` blocking proof |
| Rollback | Restore `hermes-config/config.yaml` from git; delete test file |
