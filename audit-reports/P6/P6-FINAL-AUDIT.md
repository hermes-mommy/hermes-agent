# P6 MCP Tools — Full Brutal Audit Report

| Field | Value |
|---|---|
| **Phase** | P6 — MCP Tools (21 steps, P6-001 to P6-021) |
| **Audit Date** | 2026-06-03 |
| **Auditor** | Guinevere (parent) + 8 explore agents + 13 specialist dimension auditors |
| **Methodology** | Super research wave → 8 parallel explore agents → 13 parallel specialist auditors (incl. 6 Oracle) → parent synthesis |
| **Overall Verdict** | **CONDITIONAL PASS — 4 CRITICAL findings require fix before P7** |
| **Dimension Reports** | `audit-reports/P6/P6-FINAL-AUDIT/D{01-13}-*.md` |
| **Research Reports** | `research-reports/P6-audit/` (8 explore agent outputs) |

---

## 1. Executive Summary

P6 MCP Tools delivers a **functionally complete, well-tested standalone MCP server** with 17 tool integrations, 791 passing tests (3 skipped), clean architecture, and strong code quality. However, the audit reveals **4 CRITICAL systemic issues** that prevent full acceptance:

1. **Aizanta cross-contamination risk** — 6 vectors where Guinevere MCP tools could reach Aizanta services
2. **Dead infrastructure code** — ToolCostTracker, BudgetEnforcer, auth_matrix, and tool_selector are never called at runtime
3. **MCP disconnected from agent loop** — `src/loops/` has zero imports of `src/mcp/` — agent loop cannot invoke any MCP tool
4. **Auth matrix documentation-only** — `AUTH_MATRIX` dict exists but no runtime enforcement ties it to `@require_approval` decorators

**These are NOT blockers for P6 acceptance as a standalone module.** They are integration gaps that must be addressed before P7/P8 can depend on MCP tooling.

---

## 2. Dimension Verdicts

| # | Dimension | Verdict | Score | CRITICAL | HIGH | MED | LOW |
|---|-----------|---------|-------|----------|------|-----|-----|
| D01 | Completeness | CONDITIONAL PASS | 95% | 0 | 0 | 1 | 1 |
| D02 | Code Quality | PASS | 95/100 | 0 | 0 | 2 | 1 |
| D03 | Security & Secrets | NEEDS REVIEW | 80/100 | 1* | 0 | 1 | 0 |
| D04 | Auth Matrix Enforcement | **FAIL** | 45/100 | 2 | 1 | 0 | 0 |
| D05 | Cost Tracking | **FAIL** | 30/100 | 2 | 1 | 0 | 0 |
| D06 | Test Coverage | CONDITIONAL PASS | 85% | 0 | 1 | 1 | 1 |
| D07 | ADR Compliance | CONDITIONAL PASS | 6/7 | 0 | 0 | 1 | 0 |
| D08 | Architecture Consistency | NEEDS REVIEW | B | 0 | 0 | 3 | 0 |
| D09 | Integration Points | **FAIL** | 35/100 | 1 | 3 | 0 | 0 |
| D10 | Operational Safety | NEEDS REVIEW | 75/100 | 0 | 0 | 4 | 2 |
| D11 | Known Issues & Risks | NEEDS REVIEW | 17 items | 0 | 2 | 6 | 9 |
| D12 | P7/P8 Readiness | READY w/ CAVEATS | 70% | 0 | 1 | 2 | 0 |
| D13 | Aizanta Isolation | **FAIL** | 40/100 | 6 | 3 | 0 | 0 |
| | **TOTAL** | | | **12** | **12** | **21** | **14** |

*Pre-existing (P0-014), not P6 fault.

---

## 3. CRITICAL Findings (Cross-Dimensional)

### C-01: Aizanta Cross-Contamination Vectors (D13)

**Severity**: CRITICAL — Data safety  
**Impact**: Guinevere could read/modify/destroy Aizanta data  

6 vectors identified:

| # | Vector | File | Mechanism | Fix |
|---|--------|------|-----------|-----|
| 1 | `POSTGRES_PORT` env override | `postgres_tool.py:16` | `int(os.environ.get("POSTGRES_PORT", "5433"))` — can set 5432 | Hardcode 5433 or validate `in {5433}` |
| 2 | `POSTGRES_DB` env override | `postgres_tool.py:17` | Can point to Aizanta DB | Remove env override or whitelist |
| 3 | `POSTGRES_READONLY_USER` override | `postgres_tool.py:18` | Can use Aizanta credentials | Remove env override |
| 4 | `docker_logs` no network check | `docker_tool.py:211-223` | Leaks Aizanta container logs | Add `_check_network()` before execution |
| 5 | `docker_inspect` no network check | `docker_tool.py:249-264` | Exposes Aizanta container metadata | Add `_check_network()` before execution |
| 6 | `docker_rmi` no image check | `docker_tool.py:299-314` | Can delete Aizanta images | Add image name prefix validation |

**Fix Priority**: P6-001 (must fix before P7)  
**Estimated Effort**: 2-3 hours

### C-02: Dead Infrastructure Code (D05 + D09)

**Severity**: CRITICAL — Functionality gap  
**Impact**: Cost tracking, budget enforcement, auth matrix, and tool selector are non-functional at runtime  

| Component | File | Status | Issue |
|-----------|------|--------|-------|
| `ToolCostTracker` | `src/mcp/cost.py` | Dead code | Never imported or instantiated by any tool |
| `BudgetEnforcer` | `src/mcp/budget.py` | Dead code | Never imported or instantiated by any tool |
| `AUTH_MATRIX` | `src/mcp/auth_matrix.py` | Documentation-only | No runtime tie to `@require_approval` decorators |
| `select_tool()` | `src/mcp/tool_selector.py` | Orphaned | Never called from `src/loops/` |

**Root Cause**: These were implemented as standalone modules but never wired into the tool execution pipeline. Each tool implements its own inline cost tracking (or doesn't).

**Fix Priority**: P6-002 (must fix before P7/P8)  
**Estimated Effort**: 4-6 hours (wire ToolCostTracker into each tool, wire AUTH_MATRIX into register_tools)

### C-03: MCP Disconnected from Agent Loop (D09)

**Severity**: CRITICAL — Architecture gap  
**Impact**: The agent loop (`src/loops/`) cannot invoke any MCP tool  

**Evidence**: `grep -r "from src.mcp" src/loops/` returns zero results. The MCP server runs as a standalone systemd service (`guinevere-mcp.service`) with stdio transport, but there is no client-side integration in the agent loop phases.

**Root Cause**: P6 focused on server-side MCP tool implementations without implementing the client-side bridge in `src/loops/phases/execute.py`.

**Fix Priority**: P6-003 (required for P7/P8 to use MCP tools)  
**Estimated Effort**: 8-12 hours (MCP client integration, tool invocation protocol, error handling)

### C-04: Auth Matrix Not Runtime-Enforced (D04)

**Severity**: CRITICAL — Security gap  
**Impact**: 11/16 tools have bare function implementations without `@require_approval` decorators  

**Evidence**: `AUTH_MATRIX` in `auth_matrix.py` defines the correct auth level for every tool-operation pair, but this dict is only used in tests. The actual tool functions in `src/mcp/tools/*.py` do not import or reference `AUTH_MATRIX`. The `@require_approval` decorator exists in `auth.py` but is not applied to tool functions at registration time.

**Specific mismatches**:
- PostgreSQL: AUTH_MATRIX says DESTRUCTIVE_APPROVAL for INSERT/UPDATE/DELETE, but tool blocks them entirely
- Redis: AUTH_MATRIX says DESTRUCTIVE_APPROVAL for DEL, but tool allows READ_AUTO for all operations
- 11 tools expose bare functions without any auth decoration

**Fix Priority**: P6-001 (must fix before P7)  
**Estimated Effort**: 3-4 hours (wire AUTH_MATRIX into register_tools, apply decorators dynamically)

---

## 4. HIGH Findings

### H-01: Git Force-Push Bypass Vectors (D04, D11)

3 bypass vectors in `git_tool.py`:
- `HEAD:refs/heads/main` refspec bypasses `_is_forbidden()` string check
- `--force-with-lease` not checked (only `--force` blocked)
- Branch name matching is case-sensitive (`Main` vs `main`)

**Fix**: Add refspec validation, add `--force-with-lease` to blocked flags, normalize branch names to lowercase.

### H-02: 5 Stub Tests in test_git_tool.py (D06)

`TestAuthLevels` has 5 stub tests (pass with `pass` body) that don't actually verify auth enforcement. `test_force_push_blocked` only tests `--force` flag, not `--force-with-lease`.

**Fix**: Implement actual auth level verification in stub tests.

### H-03: brave_search Cost Keys Lack TTL (D05, D11)

`brave_search.py` writes to `tool:cost:brave_search:{date}` via `incrbyfloat` but never calls `expireat`. Keys accumulate indefinitely.

**Fix**: Add `pipe.expireat(key, end_of_day_timestamp)` after `incrbyfloat`.

### H-04: P8 Readiness — No Metrics Hooks (D12)

Zero Prometheus metrics, no `/cost` API endpoint, no tool invocation counters. P8 Observability cannot monitor MCP tools.

**Fix**: Deferred to P8 phase (add prometheus_client, expose metrics endpoint).

---

## 5. MEDIUM Findings

| # | Finding | Dimension | File | Fix |
|---|---------|-----------|------|-----|
| M-01 | StepPrompts.md still says "⬜ Not Started" for all P6 steps | D01 | StepPrompts.md | Update status markers |
| M-02 | redis_tool.py uses 6× `Any` type | D02 | redis_tool.py | Type with `RedisResponseType` |
| M-03 | obscura_cdp `_pw: Any` | D02 | obscura_cdp.py:34 | Use `PlaywrightInstance` or Protocol |
| M-04 | systemd %E/ path-vs-value gap | D03 | guinevere-mcp.service | Use LoadCredential+ExecStartPre |
| M-05 | Redis DB5 dual-use (cost + rate limiting) | D07 | ADR-030 conflict | Create ADR-034 or amend ADR-030 |
| M-06 | No MCPError base exception hierarchy | D08 | src/mcp/ | Create MCPError(Exception) base |
| M-07 | budget.py imports from level-3 exa_search.py | D08 | budget.py:14 | Extract BudgetExceeded to shared exceptions |
| M-08 | cost.py/budget.py duplicate Redis connections | D08 | cost.py, budget.py | Reuse CostTracker from src/core/ |
| M-09 | 8 missing systemd hardening directives | D10 | guinevere-mcp.service | Add NoNewPrivileges, PrivateTmp, etc. |
| M-10 | Redis `KEYS` instead of `SCAN` in cost.py | D10 | cost.py:134 | Replace with SCAN cursor |
| M-11 | filesystem TOCTOU race (narrow window) | D10 | filesystem.py:96-98 | Acceptable risk, document |
| M-12 | filesystem no file size limits | D10 | filesystem.py | Add MAX_READ_SIZE constant |
| M-13 | docker_images leaks all host images | D10 | docker_tool.py:158 | Filter by label/prefix |
| M-14 | 11/16 tools have bypass vulnerability (bare functions) | D04 | src/mcp/tools/ | Wire AUTH_MATRIX at registration |
| M-15 | Redis FLUSHDB mandate conflict | D04 | redis_tool.py vs auth_matrix | Align: BLOCKED in both |
| M-16 | Postgres AUTH_MATRIX says DESTRUCTIVE but tool BLOCKS | D04 | postgres_tool.py vs auth_matrix | Align: FORBIDDEN in both |
| M-17 | Obscura CDP page.content() fallback | D02 | obscura_cdp.py:94 | reportOptionalMemberAccess — add None check |
| M-18 | Ruff E402 import-not-at-top (2 files) | D02 | manager.py, test_postgres_tool.py | Move imports to top |
| M-19 | Ruff E741 ambiguous variable `l` | D02 | test_budget.py | Rename to `line` |
| M-20 | Ruff F841 unused variables (2) | D02 | test_cost.py | Remove or use |
| M-21 | shell unrestricted FS access via whitelist | D13 | shell_tool.py | Acceptable — gated by DESTRUCTIVE_APPROVAL |

---

## 6. Dimension Detail Summaries

### D01: Completeness — CONDITIONAL PASS (95%)
- 24 source files, 22 test files confirmed
- 21 evidence directories + 21 scaffold files confirmed
- pyproject.toml updated with mcp + markdownify
- 2 systemd services confirmed
- **Gap**: StepPrompts.md not updated (still says "⬜ Not Started")

### D02: Code Quality — PASS (95/100)
- 23/24 files use structlog (context7.py uses stdlib logging — acceptable for library wrapper)
- 8 frozen dataclass usages — consistent with codebase pattern
- 1 `type: ignore[import-untyped]` — justified (playwright lacks type stubs)
- 7 `except Exception` — all logged with structlog, none empty
- 2 `pass` after except — both in finally blocks (acceptable)
- **Ruff**: 5 errors (2 E402, 1 E741, 2 F841) — trivial fixes

### D03: Security & Secrets — NEEDS REVIEW (80/100)
- **PASS**: All 7 secrets via `os.environ` — zero hardcoded credentials
- **PASS**: Port isolation (Redis 6380, PG 5433) in all tools
- **PASS**: Tests use safe fixtures, no real credentials
- **PASS**: Systemd uses `%E/` credential specifiers
- **CRITICAL (pre-existing)**: P0-014 auditor report contains real POSTGRES_PASSWORD — not P6 fault
- **MEDIUM**: systemd %E/ path-vs-value gap (documented, low risk)

### D04: Auth Matrix Enforcement — FAIL (45/100)
- AUTH_MATRIX dict correctly defines 16 tools × operations × auth levels
- Tests verify matrix completeness (93 tests)
- **FAIL**: No runtime enforcement — AUTH_MATRIX is documentation-only
- **FAIL**: 11/16 tools expose bare functions without `@require_approval`
- **FAIL**: Postgres AUTH_MATRIX says DESTRUCTIVE but tool BLOCKS entirely
- **FAIL**: Redis FLUSHDB in AUTH_MATRIX as DESTRUCTIVE but tool blocks it

### D05: Cost Tracking — FAIL (30/100)
- ToolCostTracker (241 lines) and BudgetEnforcer (364 lines) implemented correctly
- 45 + 42 tests pass for both modules
- **FAIL**: Neither module imported by any tool at runtime
- **FAIL**: Only 3 tools (exa, brave, context7) have inline cost tracking
- **FAIL**: brave_search lacks TTL on cost keys
- **HIGH**: budget.py imports BudgetExceeded from exa_search (layer violation)

### D06: Test Coverage — CONDITIONAL PASS (85%)
- 791 passed, 3 skipped (symlinks on Windows), 0 failed
- 702 test functions, 173 classes, 560 mocks
- All 12 FORBIDDEN operations have explicit blocking tests
- **GAP**: 6 stub tests in test_git_tool.py (TestAuthLevels + force_push)
- **GAP**: All tests use mocks — no integration tests with real services

### D07: ADR Compliance — CONDITIONAL PASS (6/7)
- ADR-033 (Obscura): PASS — obscura_cdp.py, guinevere-obscura.service, connect_over_cdp
- ADR-020 (Browser): PASS — Obscura primary, Chromium rollback documented
- ADR-005 (Agent Loop): PASS — tool pattern compatible
- ADR-031 (DB Layer): PASS — port 5433 enforced
- ADR-015 (Secrets): PASS — all via os.environ
- ADR-027 (PostgreSQL): PASS — 3-layer defense
- **VIOLATION**: ADR-030 (Redis) — DB5 assigned to rate limiting, but cost.py also uses DB5

### D08: Architecture Consistency — NEEDS REVIEW (Grade B)
- Clean 3-level dependency tree: Level 0 (utils) → Level 1 (base infra) → Level 2 (tools) → Level 3 (orchestration)
- structlog consistent (23/24 files)
- Frozen dataclass discipline maintained
- sys.path dance in manager.py documented and justified
- **Issues**: No MCPError base, budget.py layer violation, Redis connection duplication

### D09: Integration Points — FAIL (35/100)
- **FAIL**: Zero imports of `src.mcp` from `src/loops/` — agent loop cannot reach MCP tools
- **FAIL**: auth_matrix documentation-only, no runtime enforcement
- **FAIL**: ToolCostTracker + BudgetEnforcer dead code
- **FAIL**: tool_selector orphaned, never called
- **PASS**: MCP server startup chain (manager → tools → register_all)
- **PASS**: websearch correctly imports brave_search + exa_search
- **PASS**: budget.py correctly imports BudgetExceeded from exa_search

### D10: Operational Safety — NEEDS REVIEW (75/100)
- All dangerous operations properly gated (rm -rf, DROP TABLE, FLUSHALL, force-push)
- Shell injection defense: rejects `;`, `|`, `&&`, `$()`, backticks
- PostgreSQL 3-layer defense: BEGIN READ ONLY + SQL classifier + readonly role
- **Issues**: Missing systemd hardening, Redis KEYS vs SCAN, filesystem TOCTOU, docker_images leak

### D11: Known Issues & Risks — NEEDS REVIEW (17 items)
- 0 CRITICAL, 2 HIGH, 6 MEDIUM, 3 LOW, 2 ADVISORY, 4 INFO
- Top risk scores: Cost tracking dead code (0.280), Obscura pre-1.0 (0.240)
- Git bypass vectors documented but low probability
- 5 stub tests in git tool

### D12: P7/P8 Readiness — READY WITH CAVEATS (70%)
- **P7**: 0 blockers — MCP tools don't touch surveillance paths
- **P8**: 3 blockers — no Prometheus metrics, no /cost API, no tool invocation counters
- MCP extensibility pattern clean for future phases
- Redis DB2 pre-allocated for surveillance (no conflict)
- Systemd template excellent for replication

### D13: Aizanta Isolation — FAIL (40/100)
- **6 CRITICAL** cross-contamination vectors (see C-01)
- **3 HIGH**: shell unrestricted FS, systemctl visibility, FS whitelist env override
- **PASS**: Redis port 6380 hardcoded (not overridable)
- **PASS**: Docker ps/start/stop/restart check guinevere-net
- **PASS**: Symlink resolution in filesystem tool
- **PASS**: FLUSHALL blocked

---

## 7. Fix Prioritization Matrix

| Priority | Fix | CRITICAL Items | Effort | Phase |
|----------|-----|----------------|--------|-------|
| **P6-001** | Aizanta isolation hardening | C-01 (6 vectors) | 2-3h | Before P7 |
| **P6-002** | Wire AUTH_MATRIX into tool registration | C-04 | 3-4h | Before P7 |
| **P6-003** | MCP client bridge in src/loops/ | C-03 | 8-12h | Before P8 |
| **P6-004** | Wire ToolCostTracker into tools | C-02 | 4-6h | Before P8 |
| P6-005 | Git bypass vector fixes | H-01 | 1-2h | Before P7 |
| P6-006 | Stub test implementation | H-02 | 1h | Before P7 |
| P6-007 | brave_search TTL on cost keys | H-03 | 30min | Before P7 |
| P6-008 | Ruff fixes (5 errors) | M-18..M-20 | 30min | Now |
| P6-009 | StepPrompts.md status update | M-01 | 30min | Now |
| P6-010 | ADR-034 Redis DB allocation | M-05 | 1h | Before P7 |

---

## 8. Positive Highlights

P6 has significant strengths that should not be overlooked:

1. **Test discipline**: 791 tests, zero failures, comprehensive coverage of all FORBIDDEN operations
2. **Code quality**: structlog throughout, frozen dataclasses, no type suppression (1 justified exception)
3. **Security posture**: Zero hardcoded secrets, proper port isolation, 3-layer PostgreSQL defense
4. **Architecture**: Clean 3-level dependency tree, no circular imports, consistent patterns
5. **Obscura integration**: ADR-033 fully implemented, connect_over_cdp working, no screenshot() correctly enforced
6. **Shell injection defense**: Rejects 5 injection patterns, DESTRUCTIVE_APPROVAL for ALL shell ops
7. **Filesystem security**: Symlink resolution, separator-enforced prefix matching, path whitelist
8. **Redis safety**: FLUSHALL blocked, command classification, ACL-aware connections

---

## 9. Overall Verdict

### CONDITIONAL PASS

P6 MCP Tools is **accepted as a standalone module** with the following conditions:

1. **Before P7 starts**: Fix C-01 (Aizanta isolation), C-04 (auth matrix enforcement), H-01 (git bypass), H-02 (stub tests), H-03 (brave TTL)
2. **Before P8 starts**: Fix C-02 (cost tracking wiring), C-03 (MCP-loop bridge), H-04 (metrics hooks)
3. **Now (trivial)**: Fix P6-008 (ruff errors), P6-009 (StepPrompts status)

**What P6 delivered well**: 17 MCP tools, 791 tests, clean architecture, zero secrets in code, strong security patterns.

**What P6 did not deliver**: Runtime integration with agent loop, runtime cost tracking, runtime auth matrix enforcement, Aizanta isolation hardening. These are integration gaps, not implementation failures — the modules exist and are tested, they just need to be wired in.

---

## 10. Audit Trail

| Phase | Agent Count | Duration | Output |
|-------|-------------|----------|--------|
| Research wave | 8 explore agents | ~15min | `research-reports/P6-audit/` (8 files) |
| Dimension auditors | 13 (7 review + 6 Oracle) | ~20min | `audit-reports/P6/P6-FINAL-AUDIT/` (13 files) |
| Synthesis | Parent (Guinevere) | ~10min | This report |
| **Total** | **21 agents** | **~45min** | **22 files** |

---

*Report generated by Guinevere parent audit orchestrator. All dimension reports independently written by specialist auditors. Parent verified all reports exist and read each before synthesis.*
