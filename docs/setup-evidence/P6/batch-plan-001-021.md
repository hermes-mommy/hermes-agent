# Batch Plan — P6 MCP Tools (Steps 001–021)

**Phase:** P6 — MCP Tools Integration
**Generated:** 2026-06-02
**Planner:** Guinevere (autonomous planner)
**Status:** READY FOR EXECUTION

---

## (a) Master Todo

| Step | Name | Status | Parallelism | Wave |
|------|------|--------|-------------|------|
| P6-001 | MCP Gateway + systemd service | ⬜ | sequential | 1 |
| P6-002 | brave_search | ⬜ | parallel | 2 |
| P6-003 | context7 | ⬜ | parallel | 2 |
| P6-004 | exa | ⬜ | parallel | 2 |
| P6-005 | fetch | ⬜ | parallel | 2 |
| P6-006 | filesystem | ⬜ | parallel | 2 |
| P6-007 | github | ⬜ | parallel | 2 |
| P6-008 | grep_app | ⬜ | parallel | 2 |
| P6-009 | obscura_cdp (playwright) | ⬜ | parallel | 2 |
| P6-010 | sequential_thinking | ⬜ | parallel | 2 |
| P6-011 | time | ⬜ | parallel | 2 |
| P6-012 | websearch (hybrid) | ⬜ | sequential | 3 |
| P6-013 | git | ⬜ | parallel | 2 |
| P6-014 | postgres | ⬜ | parallel | 2 |
| P6-015 | redis | ⬜ | parallel | 2 |
| P6-016 | shell | ⬜ | parallel | 2 |
| P6-017 | docker | ⬜ | parallel | 2 |
| P6-018 | Auth Matrix Verification | ⬜ | sequential | 4a |
| P6-019 | Tool Selection Decision Matrix | ⬜ | sequential | 4b |
| P6-020 | Cost Tracking Per Tool | ⬜ | sequential | 4c |
| P6-021 | Budget Enforcement Test | ⬜ | sequential | 4d |

---

## (b) Dependency Map

```
P5 (100% complete — prerequisite)
 └─→ P6-001 (MCP Gateway — infrastructure, must be first)
      ├─→ P6-002 (brave_search)      ─┐
      ├─→ P6-003 (context7)           │
      ├─→ P6-004 (exa)        ────────┤
      ├─→ P6-005 (fetch)              │
      ├─→ P6-006 (filesystem)         │
      ├─→ P6-007 (github)             │
      ├─→ P6-008 (grep_app)           │
      ├─→ P6-009 (obscura_cdp)        │
      ├─→ P6-010 (sequential_thinking) │
      ├─→ P6-011 (time)               │
      ├─→ P6-013 (git)                │
      ├─→ P6-014 (postgres)           │
      ├─→ P6-015 (redis)              │
      ├─→ P6-016 (shell)              │
      └─→ P6-017 (docker)             │
                                       │
                  P6-002 + P6-004 ─────┘
                        ↓
                  P6-012 (websearch — needs brave + exa)
                        ↓
                  P6-018 (auth matrix — all tools must exist)
                        ↓
                  P6-019 (tool selection — needs auth matrix)
                        ↓
                  P6-020 (cost tracking — needs auth matrix)
                        ↓
                  P6-021 (budget enforcement — needs exa + websearch + cost tracking)
```

### Explicit Dependencies

| Step | Depends On | Rationale |
|------|-----------|-----------|
| P6-001 | P5 complete | Infrastructure foundation |
| P6-002 | P6-001 | Needs MCP gateway running |
| P6-003 | P6-001 | Needs MCP gateway running |
| P6-004 | P6-001 | Needs MCP gateway running |
| P6-005 | P6-001 | Needs MCP gateway running |
| P6-006 | P6-001 | Needs MCP gateway running |
| P6-007 | P6-001 | Needs MCP gateway running |
| P6-008 | P6-001 | Needs MCP gateway running |
| P6-009 | P6-001 | Needs MCP gateway running |
| P6-010 | P6-001 | Needs MCP gateway running |
| P6-011 | P6-001 | Needs MCP gateway running |
| P6-012 | P6-002, P6-004 | Hybrid needs both Brave and Exa |
| P6-013 | P6-001 | Needs MCP gateway running |
| P6-014 | P6-001 | Needs MCP gateway running |
| P6-015 | P6-001 | Needs MCP gateway running |
| P6-016 | P6-001 | Needs MCP gateway running |
| P6-017 | P6-001 | Needs MCP gateway running |
| P6-018 | P6-002..P6-017 | All 16 tools must exist to verify auth matrix |
| P6-019 | P6-018 | Auth matrix must be verified before decision matrix |
| P6-020 | P6-018 | Auth matrix must be verified before cost tracking |
| P6-021 | P6-004, P6-012, P6-020 | Exa + websearch + cost tracking for budget enforcement |

---

## (c) Parallelism Map

### Wave 1 — Infrastructure (Sequential)

| Step | Description |
|------|-------------|
| P6-001 | MCP Gateway: `src/mcp/manager.py`, `src/mcp/__init__.py`, `src/mcp/tools/__init__.py`, `systemd/guinevere-mcp.service`, pip install deps |

### Wave 2 — Tool Implementation (15 Parallel)

All fire after Wave 1 completes. No inter-step dependencies.

| Step | Tool | File |
|------|------|------|
| P6-002 | brave_search | `src/mcp/tools/brave_search.py` |
| P6-003 | context7 | `src/mcp/tools/context7.py` |
| P6-004 | exa | `src/mcp/tools/exa_search.py` |
| P6-005 | fetch | `src/mcp/tools/fetch.py` |
| P6-006 | filesystem | `src/mcp/tools/filesystem.py` |
| P6-007 | github | `src/mcp/tools/github.py` |
| P6-008 | grep_app | `src/mcp/tools/grep_app.py` |
| P6-009 | obscura_cdp | `src/mcp/tools/obscura_cdp.py` |
| P6-010 | sequential_thinking | `src/mcp/tools/sequential_thinking.py` |
| P6-011 | time | `src/mcp/tools/time_tools.py` |
| P6-013 | git | `src/mcp/tools/git_tool.py` |
| P6-014 | postgres | `src/mcp/tools/postgres_tool.py` |
| P6-015 | redis | `src/mcp/tools/redis_tool.py` |
| P6-016 | shell | `src/mcp/tools/shell_tool.py` |
| P6-017 | docker | `src/mcp/tools/docker_tool.py` |

### Wave 3 — Hybrid Tool (Sequential)

| Step | Description | Depends On |
|------|-------------|-----------|
| P6-012 | websearch (Brave→Exa fallback) | P6-002 + P6-004 |

### Wave 4 — Verification Chain (Sequential)

| Step | Description | Depends On |
|------|-------------|-----------|
| P6-018 | Auth Matrix Verification | P6-002..P6-017 (all tools) |
| P6-019 | Tool Selection Decision Matrix | P6-018 |
| P6-020 | Cost Tracking Per Tool | P6-018 |
| P6-021 | Budget Enforcement Test | P6-004 + P6-012 + P6-020 |

---

## (d) Collision Scan

| Shared File | Writers | Collision Risk | Mitigation |
|------------|---------|----------------|------------|
| `src/mcp/manager.py` | P6-001 only | NONE | Single owner; other steps register via import |
| `src/mcp/__init__.py` | P6-001 only | NONE | Single owner |
| `src/mcp/tools/__init__.py` | P6-001 only | NONE | Single owner; tools imported dynamically |
| `src/mcp/tools/*.py` | One per step | NONE | Each step creates its own unique file |
| `src/mcp/auth.py` | P6-001 creates; P6-018 verifies | LOW | P6-001 creates skeleton; P6-018 verifies all tools use it |
| `src/mcp/cost.py` | P6-020 creates | NONE | Single owner |
| `src/mcp/budget.py` | P6-021 creates | NONE | Single owner |
| `src/mcp/tool_selector.py` | P6-019 creates | NONE | Single owner |
| `tests/mcp/test_*.py` | One per step | NONE | Each step creates its own test file |
| `systemd/guinevere-mcp.service` | P6-001 only | NONE | Single owner |
| `pyproject.toml` | No changes | NONE | Dependencies added via pip in P6-001 |
| `docs/setup-evidence/P6/` | Each step writes own subdir | NONE | Isolated directories |

**Verdict:** No file-level collisions detected. Each tool step writes to its own unique file in `src/mcp/tools/` and its own test file in `tests/mcp/`.

---

## (e) Research Inputs

| Report | Path |
|--------|------|
| P6 Steps Overview | `research-reports/P6/p6-steps-overview.md` |

Additional context files read:

| File | Purpose |
|------|---------|
| `src/mcp/__init__.py` | Current MCP module state (empty stub) |
| `src/core/services/cost_tracker.py` | Existing cost tracking pattern (Redis DB5, INCRBYFLOAT, pipeline) |
| `src/loops/verify.py` | Existing verification pattern (OutputVerifier, file/command/markdown checks) |
| `src/loops/cost.py` | Existing loop cost tracking pattern (LoopCostTracker, Redis DB5) |
| `stepprompts/StepPrompts.md` lines 7048–7357 | P6 section with implementation hints |
| `adr/ADR-033-browser-automation-obscura.md` | Obscura CDP integration decision |
| `pyproject.toml` | Project config, Python 3.12, ruff, mypy strict, pytest |

---

## (f) Known State

- **Phase 5:** 100% complete — Memory + Observability infrastructure operational
- **PostgreSQL:** Running on port 5433, `guinevere_core` user, `guinevere_readonly` reader role
- **Redis:** Running on port 6380, DB0–DB5 allocated (DB5 for cost tracking)
- **9Router:** Running on port 20128 (LLM proxy)
- **Obscura:** Planned for port 9222 (CDP server, per ADR-033)
- **Core API:** Running on port 8000 (FastAPI + uvicorn)
- **systemd:** All services under `guinevere.slice`
- **Secrets:** BRAVE_API_KEY, EXA_API_KEY, GITHUB_PAT encrypted in SOPS from P0
- **Python:** 3.12, ruff linter, mypy strict, pytest
- **Existing patterns:** structlog, frozen dataclass for config, Protocol for interfaces, httpx AsyncClient

---

## (g) Binding Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| MCP SDK | `mcp` package v1.x (`from mcp.server.fastmcp import FastMCP`) | Official Python MCP SDK, stdio transport |
| Python Playwright | `pip install playwright` with `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1` | No separate `playwright-core` PyPI; skip browser download since Obscura provides CDP |
| Obscura CDP | `connect_over_cdp("ws://127.0.0.1:9222")` | Per ADR-033; use `page.content()` or LP.getMarkdown instead of screenshot |
| Auth matrix | `@require_approval` decorator with 4 levels | PraisonAI-style decorator; Read-Auto, Write-Notify, Destructive-Approval, Forbidden |
| Cost tracking | Redis DB5, `tool:cost:{name}:YYYY-MM-DD` keys, INCRBYFLOAT microdollars | Follows existing `cost_tracker.py` and `loops/cost.py` patterns |
| Logging | structlog throughout | Consistent with project convention; no print/stdlib logging |
| Config | frozen dataclass | Immutable configuration objects |
| Interfaces | Protocol classes | Type-safe interfaces for tool implementations |
| Secrets | SOPS only | BRAVE_API_KEY, EXA_API_KEY, GITHUB_PAT already encrypted from P0 |
| Dependencies | `mcp`, `httpx`, `redis`, `asyncpg`, `playwright`, `structlog`, `markdownify` | Added via pip; existing deps in pyproject.toml cover most |
| Discord webhook | Write-Notify and Destructive-Approval send Discord notifications | Per auth matrix spec |

---

## (h) Evidence Paths

| Step | Evidence Path |
|------|---------------|
| P6-001 | `docs/setup-evidence/P6/STEP-P6-001/verification.md` |
| P6-002 | `docs/setup-evidence/P6/STEP-P6-002/verification.md` |
| P6-003 | `docs/setup-evidence/P6/STEP-P6-003/verification.md` |
| P6-004 | `docs/setup-evidence/P6/STEP-P6-004/verification.md` |
| P6-005 | `docs/setup-evidence/P6/STEP-P6-005/verification.md` |
| P6-006 | `docs/setup-evidence/P6/STEP-P6-006/verification.md` |
| P6-007 | `docs/setup-evidence/P6/STEP-P6-007/verification.md` |
| P6-008 | `docs/setup-evidence/P6/STEP-P6-008/verification.md` |
| P6-009 | `docs/setup-evidence/P6/STEP-P6-009/verification.md` |
| P6-010 | `docs/setup-evidence/P6/STEP-P6-010/verification.md` |
| P6-011 | `docs/setup-evidence/P6/STEP-P6-011/verification.md` |
| P6-012 | `docs/setup-evidence/P6/STEP-P6-012/verification.md` |
| P6-013 | `docs/setup-evidence/P6/STEP-P6-013/verification.md` |
| P6-014 | `docs/setup-evidence/P6/STEP-P6-014/verification.md` |
| P6-015 | `docs/setup-evidence/P6/STEP-P6-015/verification.md` |
| P6-016 | `docs/setup-evidence/P6/STEP-P6-016/verification.md` |
| P6-017 | `docs/setup-evidence/P6/STEP-P6-017/verification.md` |
| P6-018 | `docs/setup-evidence/P6/STEP-P6-018/verification.md` |
| P6-019 | `docs/setup-evidence/P6/STEP-P6-019/verification.md` |
| P6-020 | `docs/setup-evidence/P6/STEP-P6-020/verification.md` |
| P6-021 | `docs/setup-evidence/P6/STEP-P6-021/verification.md` |

Each step also requires:
- `docs/setup-evidence/P6/STEP-P6-{NNN}/auditor-gate.md` — auditor verdict

---

## (i) Auditor Matrix

| Step | Security | Auth | Code Quality | Tests | Cost |
|------|----------|------|--------------|-------|------|
| P6-001 | No secrets in service file | N/A (infra) | No type ignore, no empty except | Service starts, responds to ping | N/A |
| P6-002 | BRAVE_API_KEY via SOPS only | Read-Auto enforced | No Any, no cast, structlog | search() returns results | Redis DB5 key created |
| P6-003 | No API key (free tier) | Read-Auto enforced | No Any, no cast, structlog | resolve/query returns docs | N/A (free) |
| P6-004 | EXA_API_KEY via SOPS only | Read-Auto enforced | No Any, no cast, structlog | search() works, cap blocks at $5 | Redis DB5 daily counter |
| P6-005 | No secrets | Read-Auto enforced | No Any, no cast, structlog | fetch() returns markdown | N/A ($0) |
| P6-006 | Path whitelist enforced | Read/Write/Destructive per op | No Any, no cast, structlog | Allowed paths work, /etc blocked | N/A ($0) |
| P6-007 | GITHUB_PAT via SOPS only | Read/Write/Destructive per op | No Any, no cast, structlog | list/create/delete operations | N/A ($0) |
| P6-008 | No secrets | Read-Auto enforced | No Any, no cast, structlog | search returns code snippets | N/A ($0) |
| P6-009 | No secrets | Read/Write/Destructive per op | No Any, no cast, structlog | CDP connect works, no screenshot() | N/A ($0) |
| P6-010 | No secrets | Read-Auto enforced | No Any, no cast, structlog | Chain-of-thought produces output | LLM token tracking |
| P6-011 | No secrets | Read-Auto enforced | No Any, no cast, structlog | WIB conversions correct | N/A ($0) |
| P6-012 | Both API keys via SOPS | Read-Auto enforced | No Any, no cast, structlog | Brave primary, Exa fallback works | Per-query cost tracked |
| P6-013 | No secrets (SSH key) | Read/Write/Destructive/Forbidden | No Any, no cast, structlog | log/diff/status work, force push main blocked | N/A ($0) |
| P6-014 | DSN via env/SOPS | Read-Auto SELECT, Forbidden DROP | No Any, no cast, structlog | SELECT works, DROP blocked | N/A ($0) |
| P6-015 | URL via env/SOPS | Read/Write/Destructive/Forbidden | No Any, no cast, structlog | GET works, FLUSHALL blocked | N/A ($0) |
| P6-016 | No secrets | Destructive-Approval all | No Any, no cast, structlog | Whitelisted cmds work, rm -rf blocked | N/A ($0) |
| P6-017 | No secrets | Read/Write/Destructive/Forbidden | No Any, no cast, structlog | ps/logs work, prune -a blocked | N/A ($0) |
| P6-018 | No secrets in test output | All 4 levels verified | N/A (test step) | 16 tools pass auth check | N/A |
| P6-019 | No secrets | N/A (config step) | No Any, no cast, structlog | Decision matrix routes correctly | N/A |
| P6-020 | No secrets | N/A (infra step) | No Any, no cast, structlog | Redis DB5 keys per tool exist | INCRBYFLOAT per tool verified |
| P6-021 | No secrets | N/A (test step) | N/A (test step) | $5 cap triggers Brave fallback | Exa cap verified, fallback cost |

---

## (j) Rollback Plan

| Step | Rollback Action | Services to Stop |
|------|----------------|-----------------|
| P6-001 | Remove `systemd/guinevere-mcp.service`, uninstall pip deps, restore `src/mcp/__init__.py` | `systemctl stop guinevere-mcp` |
| P6-002 | Delete `src/mcp/tools/brave_search.py` and test | None |
| P6-003 | Delete `src/mcp/tools/context7.py` and test | None |
| P6-004 | Delete `src/mcp/tools/exa_search.py` and test, flush Redis DB5 exa keys | None |
| P6-005 | Delete `src/mcp/tools/fetch.py` and test | None |
| P6-006 | Delete `src/mcp/tools/filesystem.py` and test | None |
| P6-007 | Delete `src/mcp/tools/github.py` and test | None |
| P6-008 | Delete `src/mcp/tools/grep_app.py` and test | None |
| P6-009 | Delete `src/mcp/tools/obscura_cdp.py` and test, stop obscura service | `systemctl stop guinevere-obscura` |
| P6-010 | Delete `src/mcp/tools/sequential_thinking.py` and test | None |
| P6-011 | Delete `src/mcp/tools/time_tools.py` and test | None |
| P6-012 | Delete `src/mcp/tools/websearch.py` and test | None |
| P6-013 | Delete `src/mcp/tools/git_tool.py` and test | None |
| P6-014 | Delete `src/mcp/tools/postgres_tool.py` and test | None |
| P6-015 | Delete `src/mcp/tools/redis_tool.py` and test | None |
| P6-016 | Delete `src/mcp/tools/shell_tool.py` and test | None |
| P6-017 | Delete `src/mcp/tools/docker_tool.py` and test | None |
| P6-018 | Delete `src/mcp/auth.py` verification tests | None |
| P6-019 | Delete `src/mcp/tool_selector.py` and test | None |
| P6-020 | Delete `src/mcp/cost.py` and test, flush Redis DB5 tool cost keys | None |
| P6-021 | Delete `src/mcp/budget.py` and test | None |

**Global rollback:** `systemctl stop guinevere-mcp && systemctl disable guinevere-mcp` — all tools become unreachable.

---

## (k) Caveats

### Known Risks

1. **Obscura pre-1.0 (v0.1.6):** CDP coverage is partial (9/40+ domains). Edge cases may break. Fallback to Playwright + Chromium documented in ADR-033.
2. **Playwright pip package naming:** No separate `playwright-core` PyPI package exists. Use `pip install playwright` with `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1` env var.
3. **Exa daily cap race condition:** Redis INCRBYFLOAT is atomic, but between cap check and API call, a concurrent request could exceed cap by one request. Acceptable for $5 cap.
4. **SOPS secret decryption latency:** Each tool must decrypt secrets at startup. Cold start adds ~200ms. Mitigated by caching decrypted values in process memory.
5. **grep.app API stability:** No official API documentation. Implementation based on reverse-engineered endpoints. May break without notice.
6. **Context7 free tier limits:** 1000 calls/month. Monitor usage; implement caching to stay within limits.
7. **Brave Search free tier:** 2000 requests/month. Monitor usage; websearch hybrid helps distribute load.
8. **Shell command whitelist bypass:** Subshell/pipe injection could bypass whitelist. Defense: parse command AST, reject if `;`, `|`, `&&`, `$()` detected outside whitelist.
9. **PostgreSQL read-only defense-in-depth:** Three layers — `BEGIN READ ONLY`, AST parsing, reader role. Any single layer failure still blocks writes via other layers.
10. **Docker socket access:** `guinevere` user needs docker group membership. Verify with `groups guinevere` before implementation.

### Pre-Existing Issues

- `src/mcp/__init__.py` is a stub (1 line comment). P6-001 replaces it.
- No `tests/mcp/` directory exists yet. P6-001 creates it.
- `pyproject.toml` does not list `mcp` or `markdownify` as dependencies. P6-001 adds them via pip; consider adding to `pyproject.toml` in a follow-up.

### Limitations

- **No live API testing on Windows dev:** Implementation and unit tests run on Windows; live API integration tests require VPS deployment.
- **Auth decorator requires Discord webhook:** Write-Notify and Destructive-Approval levels send Discord notifications. Webhook URL must be configured in environment.
- **Budget enforcement is advisory:** If Redis DB5 is unreachable, tools log warnings but do not block. This is intentional — fail-open for availability, fail-closed for cost.

---

## Execution Checklist

1. [ ] P6-001: MCP Gateway — verify service starts, stdio transport works
2. [ ] Wave 2: Fire 15 parallel sub-agents (P6-002..P6-011, P6-013..P6-017)
3. [ ] Verify each Wave 2 tool independently (parent verification + verifier sub-agent)
4. [ ] P6-012: websearch hybrid — verify Brave primary + Exa fallback
5. [ ] P6-018: Auth matrix — verify all 16 tools enforce correct level
6. [ ] P6-019: Tool selector — verify decision matrix routes correctly
7. [ ] P6-020: Cost tracking — verify Redis DB5 keys per tool
8. [ ] P6-021: Budget enforcement — verify $5 Exa cap triggers Brave fallback
9. [ ] Spawn auditor wave for all completed steps
10. [ ] Fix valid findings, re-audit until PASS
11. [ ] Final report: changed files, verification, evidence, auditor path, caveats

---

*Batch plan generated by Guinevere planner. 2026-06-02.*
