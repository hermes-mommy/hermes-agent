# ADR-035 Phase 4 Execution Planner Gate

| Field | Value |
|---|---|
| Plan | ADR-035 Phase 4 — MCP Tools execution |
| Status | PLANNER GATE FILE — pending parent verification |
| Date | 2026-06-05 |
| Evidence root | `docs/setup-evidence/phase-4/` |
| Research root | `research-reports/phase-4-execution/` |
| Baseline plan | `docs/setup-evidence/phase-4/batch-plan-phase-4.md` v1.1 |
| Authority | Python `src/mcp/auth_matrix.py` is auth source of truth |

## 1. Planner Verdict

Phase 4 may proceed to implementation only after this file is parent-read and scaffold compliance is verified.

Conditional planner verdict: **READY WITH GATES**.

Blocking gates before implementation:

1. Parent must read this planner gate file fully.
2. Parent must verify all per-step scaffolds are concrete and checkable.
3. Parent must sync active todos to the dependency map in this file.
4. Parent must run collision scan before delegating implementation.
5. No VPS deploy, restart, rollback, systemd change, or live destructive approval test may run without explicit per-action approval because project policy blocks stateful/destructive live operations.

## 2. Research Inputs Read

Execution research reports under `research-reports/phase-4-execution/`:

| ID | Path | Planner Use |
|---|---|---|
| 01 | `01-mcp-state.md` | VPS live state, Hermes v0.15.2, config gap, FastMCP `_config` blocker, Aizanta port violation |
| 02 | `02-native-tools.md` | Native Hermes toolset availability, CLI semantics, partial native tool coverage |
| 03 | `03-auth-matrix.md` | Auth matrix completeness, decorator path, dead safety plugin path, active enforcement gaps |
| 04 | `04-fastmcp-bridge.md` | FastMCP stdio feasibility and KEEP-7 custom tools |
| 05 | `05-budget-gap.md` | Budget fail-open gaps and required Redis Lua pre-tool enforcement |
| 06 | `06-planning-synthesis.md` | Prior synthesis, wave order, contradiction resolutions |
| 07 | `07-hermes-external-docs.md` | Official Hermes MCP/plugin/hook behavior, unsupported critical plugin flags |
| 08 | `08-security-budget-patterns.md` | Fail-closed authorization, approval, Redis Lua, shell/path/secret guard patterns |
| 09 | `09-oracle-risk-review.md` | Oracle high-risk findings and go/no-go conditions |

Additional local inputs read:

- `docs/setup-evidence/phase-4/batch-plan-phase-4.md` v1.1.
- `adr/ADR-035-hermes-migration.md`.
- `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md`.
- `research-reports/phase-4-planning/R4-007-hermes-mcp-plugin-docs.md`.
- `docs/setup-evidence/phase-4/AUDIT-security-v1.1.md`.
- `docs/setup-evidence/phase-4/AUDIT-adr035-compliance-v1.1.md`.
- `hermes-config/config.yaml`.
- `src/mcp/auth_matrix.py`.
- `src/mcp/auth.py`.
- `src/mcp/tools/__init__.py`.
- `src/mcp/manager.py`.
- `src/mcp/tools/sequential_thinking.py`.
- `src/mcp/tools/filesystem.py`.
- `src/hermes/safety_plugin.py`.
- `src/hermes/session_adapter.py`.
- `src/mcp/budget.py`.

## 3. Known State

### 3.1 VPS / Runtime

- Hermes Agent Gateway v0.15.2 is active on VPS with `guinevere_safety` plugin.
- Live `~/.hermes/config.yaml` is a default-like template and does not currently register Phase 4 MCP servers.
- `hermes mcp list` on VPS reported no configured MCP servers.
- Legacy `guinevere-mcp.service` is inactive/disabled; it previously registered 16 tools.
- FastMCP manager import/server creation succeeds until tool registration reaches `src/mcp/tools/filesystem.py`, where FastMCP rejects `_config` parameters.
- Required canonical ports remain PG=5433, Redis=6380, 9Router=20128, Obscura=9222/9223.
- VPS currently has standard ports 5432 and 6379 listening. This is an Aizanta isolation violation to report, but remediation is a stateful service action requiring explicit approval.

### 3.2 Auth

- `src/mcp/auth_matrix.py` is complete for all 16 canonical tools and 80 operations.
- Python `get_auth_level(tool_name, operation)` raises `KeyError` fail-closed for unknown tools/operations.
- Existing decorator path in `src/mcp/auth.py` uses in-memory approval and has drift-prone/warn-only matrix validation.
- Existing `src/hermes/safety_plugin.py` has a `pre_tool_call` method, but it fails open on generic auth exceptions and does not map prefixed MCP tool names to canonical auth matrix names.

### 3.3 Hermes Docs Reality

- `mcp_servers` supports stdio/HTTP servers with `command`, `args`, `env`, `enabled`, `timeout`, `connect_timeout`, `supports_parallel_tool_calls`, and `tools.include/exclude`.
- `hermes mcp add` exists, but direct YAML configuration remains preferred for deterministic review.
- `critical:true` and plugin-level `on_failure:block` are not native Hermes plugin flags.
- Shell hooks can use `on_failure:block`; plugin hook errors are caught/logged and gateway continues.
- `pre_tool_call` can block tool dispatch by returning `{"action":"block"}`, but native MCP timing must be proven before live exposure.

### 3.4 Budget

- Existing budget code uses Redis 6380 DB5 but has fail-open Redis error handling and read-then-write patterns.
- Existing tool-level budget is not wired into Hermes `pre_tool_call`.
- Phase 4 must implement Redis Lua atomic budget checking and fail-closed behavior for tool calls.

## 4. Binding Decisions

| ID | Decision | Rationale |
|---|---|---|
| BD-001 | Implement auth overlay as a separate Hermes plugin. | Keeps Hermes integration isolated and testable. |
| BD-002 | Use custom startup gate instead of `critical:true`. | Hermes does not support mandatory plugin manifests. |
| BD-003 | Use Redis Lua for budget checks. | Atomic check/increment and fail-closed behavior required. |
| BD-004 | Retain FastMCP as stdio backend for 7 custom KEEP tools. | Avoid rewriting existing custom MCP tools. |
| BD-005 | Hybrid guard safety comes from config + plugin guards + tests. | Terminal/git/docker behavior differs from old tools. |
| BD-006 | Python `src/mcp/auth_matrix.py` is the only runtime auth source. | User requirement: YAML reference only with zero drift. |
| BD-007 | Budget thresholds are warn at $24 and block at $30 monthly. | ADR/user requirement. |
| BD-008 | Configure native MCP exposure with no direct production tool access until pre-tool blocking proof passes. | Oracle risk F2: native dispatch bypass must be ruled out. |
| BD-009 | Persist destructive approval state to Redis DB5 with 5-minute TTL. | Oracle risk F4: in-memory state is lost on restart. |
| BD-010 | Reconcile all Hermes/MCP tool names to canonical `ALL_TOOL_NAMES`. | Prevent false forbidden/unknown results and bypasses. |
| BD-011 | Include FastMCP `_config` fix in Wave 1/P4-005 scope. | Live FastMCP registration is blocked otherwise. |
| BD-012 | Require all 15 P4-007 checks PASS despite old text saying 14. | Batch plan/checklist inconsistency resolved conservatively. |

## 5. Contradictions Resolved

| Contradiction | Resolution |
|---|---|
| User text wave order vs batch plan v1.1 | Follow batch plan v1.1/planner authority: Wave 1 P4-001+P4-005, Wave 2 P4-002, Wave 3 P4-003+P4-004+P4-006, Wave 4 P4-007, Wave 5 P4-008. |
| YAML auth matrix vs Python source | Python runtime source only. Any YAML remains reference/generated evidence only and cannot drive runtime auth. |
| `critical:true`/plugin `on_failure:block` vs Hermes reality | Do not rely on unsupported plugin flags. Enforce startup gate and internal fail-closed returns. |
| Batch plan read-only `src/mcp/tools/*.py` vs live FastMCP `_config` blocker | Scope change allowed for `src/mcp/tools/filesystem.py` only: rename `_config` to `config` in four tool function defaults or implement KEEP-7-only registration without importing filesystem. Preferred: minimal rename because it fixes a real FastMCP v1 compatibility bug. |
| `sequential_think` vs actual MCP tool name | Use registered MCP name `sequential_thinking`. |
| 14 vs 15 security checks | Require all 15 checks PASS. |
| Direct native MCP exposure vs Oracle bypass risk | Do not expose direct production native tools until a blocking proof test shows `pre_tool_call` blocks before dispatch. |
| Full autonomous deployment request vs project policy | Local implementation may proceed; live deploy/restart/rollback/destructive tests require explicit per-action approval. |

## 6. Dependency Map and Waves

### Wave 1 — parallel after this planner gate

- P4-001: Hermes MCP config baseline and safe native server registration strategy.
- P4-005: FastMCP custom bridge and `_config` compatibility fix.

### Wave 2 — after P4-001

- P4-002: Auth overlay plugin, tool-name reconciliation, Redis-backed approval state, fail-closed behavior.

### Wave 3 — after P4-002, parallel if no file collisions

- P4-003: Redis Lua budget hook.
- P4-004: Hybrid guards.
- P4-006: Startup gate.

### Wave 4 — after P4-003, P4-004, P4-005, P4-006 parent-verified

- P4-007: Security audit suite, all 15 checks PASS.

### Wave 5 — after P4-007 PASS

- P4-008: E2E test suite, expected 20/20 PASS or documented pre-existing/runtime-blocked failures.

### Post-implementation gates

- Parallel verification wave.
- Auditor wave with independent reports.
- Evidence and PROGRESS update.
- Git commit/push only after all gates PASS and git-master workflow runs.
- VPS deployment/restart only after explicit per-action approval.

## 7. Master Todo

| Step | Wave | Dependency | Status |
|---|---:|---|---|
| P4-001 | 1 | Planner gate | Pending |
| P4-005 | 1 | Planner gate | Pending |
| P4-002 | 2 | P4-001 | Pending |
| P4-003 | 3 | P4-002 | Pending |
| P4-004 | 3 | P4-002 | Pending |
| P4-006 | 3 | P4-002 | Pending |
| P4-007 | 4 | P4-003, P4-004, P4-005, P4-006 | Pending |
| P4-008 | 5 | P4-007 | Pending |
| Deploy/restart/runtime proof | Post | P4-008 + explicit approval | Blocked pending approval |
| Evidence/auditors/git | Post | Verification/auditors PASS | Pending |

## 8. Collision Scan

| Surface | Owners | Collision Risk | Mitigation |
|---|---|---|---|
| `hermes-config/config.yaml` | P4-001 primary; P4-003/P4-004 may need hook slots | High | P4-001 owns config structure and reserves hook/plugin slots. Later steps should edit only reserved sections or be sequenced. |
| `src/mcp/tools/filesystem.py` | P4-005 | Medium | P4-005 sole owner; only rename `_config` parameters to `config`, no behavior refactor. |
| `hermes-config/plugins/auth_overlay/` | P4-002 | Low | P4-002 sole owner. |
| `hermes-config/hooks/budget_check.py`, `budget_lua.py`, `budget_lua_extended.py` | P4-003 | Low | P4-003 sole owner. |
| `hermes-config/hooks/hybrid_guards.py` | P4-004 | Low | P4-004 sole owner. |
| `scripts/startup_gate.py`, `scripts/startup_gate_test.py` | P4-006 | Low | P4-006 sole owner. |
| `tests/hermes/*` | Multiple | Medium | Each P4 step owns its direct test file. P4-007 and P4-008 own audit/E2E tests. Avoid shared fixture edits unless one owner is assigned. |
| `docs/setup-evidence/phase-4/*.md` | Parent | High | Parent owns evidence aggregation. Implementers may write per-step verification only if scaffold explicitly permits. |
| VPS systemd/live config | Deployment | Critical | No writes/restarts without explicit approval. |

## 9. Files to Create or Modify

### P4-001

Expected modify:

- `hermes-config/config.yaml`
- `tests/hermes/test_mcp_config.py`
- `docs/setup-evidence/phase-4/P4-001-verification.md`

Expected create if needed:

- `tests/hermes/__init__.py`

### P4-005

Expected modify:

- `hermes-config/config.yaml`
- `src/mcp/tools/filesystem.py`
- `tests/hermes/test_fastmcp_bridge.py`
- `docs/setup-evidence/phase-4/P4-005-verification.md`

Expected create if needed:

- `src/mcp/custom_manager.py` or `src/mcp/manager_custom.py` only if KEEP-7-only registration is chosen instead of minimal filesystem fix.

### P4-002

Expected create:

- `hermes-config/plugins/auth_overlay/__init__.py`
- `hermes-config/plugins/auth_overlay/plugin.yaml`
- `hermes-config/plugins/auth_overlay/auth_handler.py`
- `hermes-config/plugins/auth_overlay/approval_handler.py`
- `hermes-config/plugins/auth_overlay/notify_handler.py`
- `hermes-config/plugins/auth_overlay/forbidden_handler.py`
- `tests/hermes/test_auth_overlay.py`
- `docs/setup-evidence/phase-4/P4-002-verification.md`

Expected modify only if required by loading path:

- `hermes-config/config.yaml`

### P4-003

Expected create:

- `hermes-config/hooks/budget_check.py`
- `hermes-config/hooks/budget_lua.py`
- `hermes-config/hooks/budget_lua_extended.py`
- `tests/hermes/test_budget_hook.py`
- `docs/setup-evidence/phase-4/P4-003-verification.md`

Expected modify only in reserved config section:

- `hermes-config/config.yaml`

### P4-004

Expected create:

- `hermes-config/hooks/hybrid_guards.py`
- `tests/hermes/test_hybrid_guards.py`
- `docs/setup-evidence/phase-4/P4-004-verification.md`

Expected modify only in reserved config section:

- `hermes-config/config.yaml`

### P4-006

Expected create:

- `scripts/startup_gate.py`
- `scripts/startup_gate_test.py`
- `tests/hermes/test_startup_gate.py` if needed
- `docs/setup-evidence/phase-4/P4-006-verification.md`

### P4-007

Expected create:

- `tests/hermes/test_security_audit.py`
- `docs/setup-evidence/phase-4/P4-007-verification.md`

Expected modify:

- `docs/setup-evidence/phase-4/verification.md`
- `docs/setup-evidence/phase-4/auditor-gate.md`

### P4-008

Expected create:

- `tests/hermes/test_integration_e2e.py`
- `docs/setup-evidence/phase-4/P4-008-verification.md`

Expected modify:

- `docs/setup-evidence/phase-4/verification.md`

## 10. Implementation Design

### 10.1 P4-001 MCP config baseline

- Convert/verify `hermes-config/config.yaml` MCP sections against Hermes documented `mcp_servers` shape.
- Do not assume old native-like keys register MCP servers.
- Configure servers conservatively and include comments/evidence for native exposure gate.
- Native MCP production exposure must not bypass auth overlay. Until proof exists, direct native tool exposure should be empty/disabled or gated in test-only context.
- Keep ports to 5433/6380/20128 only.

### 10.2 P4-005 FastMCP custom bridge

- FastMCP custom server must expose KEEP-7 custom tools: `postgres`, `redis`, `obscura_cdp`, `grep_app`, `context7`, `sequential_thinking`, `time`.
- Fix the FastMCP `_config` registration blocker minimally or create a custom KEEP-7 registration path that never imports/registers filesystem/native modules.
- Registered name for sequential tool is `sequential_thinking`.
- Use stdio MCP config with project cwd and environment, no secret literals.

### 10.3 P4-002 Auth overlay

- Import Python `src/mcp/auth_matrix.py` directly. No hand-maintained runtime YAML.
- Normalize Hermes names such as `mcp_fastmcp_custom_redis_get`, native `fetch_url`, terminal/git aliases, and custom tool names into canonical tool + operation.
- Unknown canonical mapping must block fail-closed.
- READ_AUTO allow, WRITE_NOTIFY notify and allow, DESTRUCTIVE_APPROVAL create Redis-persisted approval request and wait/poll with TTL, FORBIDDEN block and audit.
- Plugin code must catch its own exceptions and return block, not allow.
- Approval state must use Redis DB5, 5-minute TTL, and no secret exposure.

### 10.4 P4-003 Budget hook

- Use Redis 6380 DB5 and Lua atomic check/update.
- Warn at $24, block at $30 monthly. Include per-tool daily/global daily checks if specified.
- Redis errors, Lua errors, parse errors, and missing env must fail closed.
- Budget should run before expensive/destructive execution and compose with auth overlay.

### 10.5 P4-004 Hybrid guards

- Block shell injection patterns: `;`, `|`, `&&`, backticks, `$()` where applicable.
- Block unsafe Docker operations per 5-layer guard.
- Block force-push to main/master.
- Enforce Aizanta path isolation and canonical port isolation.

### 10.6 P4-006 Startup gate

- Validate plugin directories/manifests/import/register for `auth_overlay` and `guinevere_safety`.
- Validate hook files compile/import.
- Validate auth matrix import and completeness.
- Refuse startup with non-zero exit if critical plugins or hooks are broken.
- No `os.system()`; use `subprocess.run` with list args if needed and `os.execvp` only after successful validation.

### 10.7 P4-007 Audit

- Implement deterministic security audit with 15 checks.
- All checks must pass before P4-008.
- Include Aizanta isolation, Python source auth matrix, forbidden operation blocks, budget fail-closed, native dispatch proof status, FastMCP, startup gate, secrets, and latency checks.

### 10.8 P4-008 E2E

- E2E tests cover native/hybrid/custom/cross-cutting and latency.
- Tests must avoid live destructive operations unless explicit approval is granted; use dry-run/mocks where approval boundary blocks live actions.
- Runtime deployment proof remains separate and approval-gated.

## 11. Token, Secret, and Safety Handling

- Never commit or print Discord tokens, API keys, DB passwords, SOPS/age keys, surveillance credentials, or decrypted env values.
- Use env names only: `REDIS_URL`, `DATABASE_URL`, `DISCORD_APPROVAL_WEBHOOK`, `GOTIFY_TOKEN`, `GITHUB_PAT`.
- Use default docs values only with canonical ports: Redis 6380 DB5, Postgres 5433, 9Router 20128.
- Redact webhook URLs and approval payload secrets in logs/evidence.
- Do not store raw surveillance data in evidence.
- Preserve HARD STOP, consent revocation, no Y6, no distress suppression, no hidden coercion.

## 12. Rollback Plan

Rollback commands are documented in the batch plan but are stateful/destructive. They require explicit per-action approval before execution.

Permitted before approval:

- Local code changes.
- Local tests.
- Read-only VPS inspections.
- Dry-run/config validation that does not mutate live service state.

Not permitted without explicit approval:

- `sudo systemctl stop/start/restart/reload hermes-gateway`.
- `systemctl daemon-reload`.
- Writing `~/.hermes/config.yaml` on VPS.
- `hermes mcp add/remove` on VPS if it persists config.
- Stopping/disabling Postgres/Redis on 5432/6379.
- Live destructive approval tests against real Redis/service state.

## 13. Evidence and Auditor Matrix

| Step | Verification Path | Auditor Surface |
|---|---|---|
| P4-001 | `docs/setup-evidence/phase-4/P4-001-verification.md` | ADR compliance + config correctness |
| P4-002 | `docs/setup-evidence/phase-4/P4-002-verification.md` | Security/auth fail-closed |
| P4-003 | `docs/setup-evidence/phase-4/P4-003-verification.md` | Security + FinOps |
| P4-004 | `docs/setup-evidence/phase-4/P4-004-verification.md` | Security/hybrid guard |
| P4-005 | `docs/setup-evidence/phase-4/P4-005-verification.md` | Technical accuracy/FastMCP |
| P4-006 | `docs/setup-evidence/phase-4/P4-006-verification.md` | Security/startup gate |
| P4-007 | `docs/setup-evidence/phase-4/P4-007-verification.md` | Security + ADR + technical accuracy |
| P4-008 | `docs/setup-evidence/phase-4/P4-008-verification.md` | E2E/runtime behavior |
| Master | `docs/setup-evidence/phase-4/verification.md` | Cross-step evidence |
| Auditor | `docs/setup-evidence/phase-4/auditor-gate.md` | Final auditor gate |

Auditors must be independent and file-based. PASS is required before marking the task complete.

## 14. Per-Step Verification Scaffolds

### P4-001 Scaffold — Hermes MCP Config Baseline

| Field | Contract |
|---|---|
| Expected Files | `hermes-config/config.yaml`; `tests/hermes/test_mcp_config.py`; `docs/setup-evidence/phase-4/P4-001-verification.md` |
| Forbidden Patterns | `redis://localhost:6379`; `localhost:5432`; `critical:\s*true`; `on_failure:\s*block` inside plugin manifests; plaintext token-like values `(sk-[A-Za-z0-9_-]+|ghp_[A-Za-z0-9_]+|discord(app)?\.com/api/webhooks/[^\s]+)` |
| Required Commands | `python -m pytest tests/hermes/test_mcp_config.py -v` → exit 0; `python -m compileall hermes-config` → exit 0 |
| Evidence Requirements | `P4-001-verification.md` includes config diff summary, canonical ports proof, native exposure proof/limitation, auth source statement |
| Hard Rejection Criteria | Missing/invalid `mcp_servers`; direct native exposure without auth-block proof; YAML auth matrix treated as runtime source; any 5432/6379 reference in created config; secrets in config |

### P4-005 Scaffold — FastMCP Custom Bridge

| Field | Contract |
|---|---|
| Expected Files | `hermes-config/config.yaml`; `src/mcp/tools/filesystem.py` or custom KEEP-7 manager file; `tests/hermes/test_fastmcp_bridge.py`; `docs/setup-evidence/phase-4/P4-005-verification.md` |
| Forbidden Patterns | `def .*\(_config`; `#\s*type:\s*ignore`; `\bAny\b` newly introduced; hardcoded secrets; registering all 16 tools when only KEEP-7 is expected |
| Required Commands | `python -m pytest tests/hermes/test_fastmcp_bridge.py -v` → exit 0; `python -m compileall src/mcp hermes-config` → exit 0 |
| Evidence Requirements | `P4-005-verification.md` lists exposed KEEP-7 tools and proves `sequential_thinking` naming; documents `_config` fix or KEEP-7-only manager decision |
| Hard Rejection Criteria | FastMCP registration still fails; filesystem/native tools exposed through custom bridge unintentionally; auth matrix completeness bypassed; Aizanta blocked paths weakened |

### P4-002 Scaffold — Auth Overlay

| Field | Contract |
|---|---|
| Expected Files | `hermes-config/plugins/auth_overlay/__init__.py`; `plugin.yaml`; `auth_handler.py`; `approval_handler.py`; `notify_handler.py`; `forbidden_handler.py`; `tests/hermes/test_auth_overlay.py`; `docs/setup-evidence/phase-4/P4-002-verification.md` |
| Forbidden Patterns | `except\s+Exception\s*:\s*(pass|return\s+None|return\s+\{\s*['\"]action['\"]\s*:\s*['\"]allow)`; `#\s*type:\s*ignore`; `\bAny\b`; hand-maintained runtime `auth_matrix.yaml`; plaintext webhook/API tokens; `shell=True`; `print\(` |
| Required Commands | `python -m pytest tests/hermes/test_auth_overlay.py -v` → exit 0; `python -m compileall hermes-config/plugins/auth_overlay` → exit 0 |
| Evidence Requirements | `P4-002-verification.md` maps all 16 canonical tools, all four auth levels, unknown fail-closed, Redis approval TTL, webhook redaction, native/MCP prefix normalization |
| Hard Rejection Criteria | Unknown tool allowed; FORBIDDEN allowed; DESTRUCTIVE_APPROVAL not persisted to Redis DB5; plugin exception allows execution; Python auth matrix not used directly |

### P4-003 Scaffold — Budget Hook

| Field | Contract |
|---|---|
| Expected Files | `hermes-config/hooks/budget_check.py`; `hermes-config/hooks/budget_lua.py`; `hermes-config/hooks/budget_lua_extended.py`; `tests/hermes/test_budget_hook.py`; `docs/setup-evidence/phase-4/P4-003-verification.md`; optional reserved edit to `hermes-config/config.yaml` |
| Forbidden Patterns | `redis://localhost:6379`; `localhost:5432`; non-atomic read-then-increment pattern `(get\(|incrbyfloat\()` outside Lua wrapper; `except\s+.*:\s*pass`; `return\s+\{\s*['\"]action['\"]\s*:\s*['\"]allow` on Redis/Lua error; `#\s*type:\s*ignore`; `\bAny\b` newly introduced |
| Required Commands | `python -m pytest tests/hermes/test_budget_hook.py -v` → exit 0; `python -m compileall hermes-config/hooks` → exit 0 |
| Evidence Requirements | `P4-003-verification.md` shows warn $24/block $30, Redis 6380 DB5, Lua atomicity, fail-closed Redis error, per-tool/global cap behavior |
| Hard Rejection Criteria | Redis failure allows tool; budget check not wired into pre-tool path; monthly >$30 allowed; check-then-increment race remains |

### P4-004 Scaffold — Hybrid Guards

| Field | Contract |
|---|---|
| Expected Files | `hermes-config/hooks/hybrid_guards.py`; `tests/hermes/test_hybrid_guards.py`; `docs/setup-evidence/phase-4/P4-004-verification.md`; optional reserved edit to `hermes-config/config.yaml` |
| Forbidden Patterns | `shell=True`; allowlist bypass for `;`, `|`, `&&`, backticks, `$()`; hardcoded container names; `/home/aizanta` allowed; `--force` to main/master allowed; `except\s+.*:\s*pass`; `#\s*type:\s*ignore`; `\bAny\b` newly introduced |
| Required Commands | `python -m pytest tests/hermes/test_hybrid_guards.py -v` → exit 0; `python -m compileall hermes-config/hooks` → exit 0 |
| Evidence Requirements | `P4-004-verification.md` includes shell, Docker, git, Aizanta path, port isolation, and safe allow examples |
| Hard Rejection Criteria | Injection pattern allowed; Docker destructive operation allowed without approval; force-push main/master allowed; Aizanta path/port violation allowed |

### P4-006 Scaffold — Startup Gate

| Field | Contract |
|---|---|
| Expected Files | `scripts/startup_gate.py`; `scripts/startup_gate_test.py` or `tests/hermes/test_startup_gate.py`; `docs/setup-evidence/phase-4/P4-006-verification.md` |
| Forbidden Patterns | `os\.system\(`; silent continuation after failed plugin import/register; `except\s+.*:\s*pass`; `return\s+0` on critical validation failure; `#\s*type:\s*ignore`; `\bAny\b` newly introduced |
| Required Commands | `python -m pytest scripts/startup_gate_test.py -v` or `python -m pytest tests/hermes/test_startup_gate.py -v` → exit 0; `python -m compileall scripts hermes-config/plugins` → exit 0 |
| Evidence Requirements | `P4-006-verification.md` proves broken auth_overlay blocks startup, broken guinevere_safety blocks startup, valid config exec path is list-arg safe, unsupported `critical:true` not relied upon |
| Hard Rejection Criteria | Gateway can start with missing/broken auth_overlay; startup gate depends on unsupported plugin flags; failure swallowed; shell execution unsafe |

### P4-007 Scaffold — Security Audit Suite

| Field | Contract |
|---|---|
| Expected Files | `tests/hermes/test_security_audit.py`; `docs/setup-evidence/phase-4/P4-007-verification.md`; `docs/setup-evidence/phase-4/verification.md`; `docs/setup-evidence/phase-4/auditor-gate.md` |
| Forbidden Patterns | Audit count hardcoded to 14; skipped security tests; `pytest.mark.skip` without documented accepted blocker; secrets in evidence; raw surveillance data; `#\s*type:\s*ignore`; `\bAny\b` newly introduced |
| Required Commands | `python -m pytest tests/hermes/test_security_audit.py -v` → exit 0; targeted grep checks for forbidden patterns in changed files → zero new violations |
| Evidence Requirements | `P4-007-verification.md` lists all 15 checks with PASS/FAIL and maps to ADR/security requirements; master verification and auditor gate updated |
| Hard Rejection Criteria | Any of 15 checks FAIL; auth matrix source drift; native bypass unresolved but marked PASS; Aizanta isolation ignored; budget fail-open accepted |

### P4-008 Scaffold — E2E Integration Suite

| Field | Contract |
|---|---|
| Expected Files | `tests/hermes/test_integration_e2e.py`; `docs/setup-evidence/phase-4/P4-008-verification.md`; `docs/setup-evidence/phase-4/verification.md` |
| Forbidden Patterns | `time\.sleep\((?:[6-9]|[1-9][0-9])`; hardcoded API keys/webhooks; live destructive action without approval; skipped E2E tests without documented blocker; `#\s*type:\s*ignore`; `\bAny\b` newly introduced |
| Required Commands | `python -m pytest tests/hermes/test_integration_e2e.py -v --timeout=300` → exit 0 or explicit approval-blocked/pre-existing split; `python -m compileall tests/hermes` → exit 0 |
| Evidence Requirements | `P4-008-verification.md` includes native/hybrid/custom/cross-cutting/latency categories, 20 expected cases, live-vs-mocked distinction, approval blockers |
| Hard Rejection Criteria | E2E claims live runtime proof without deployment approval; destructive test runs unapproved; <20 cases without documented reason; failures caused by Phase 4 left unresolved |

## 15. Verification Commands Before Completion

At minimum before reporting Phase 4 complete:

```powershell
python -m pytest tests/hermes/test_mcp_config.py -v
python -m pytest tests/hermes/test_fastmcp_bridge.py -v
python -m pytest tests/hermes/test_auth_overlay.py -v
python -m pytest tests/hermes/test_budget_hook.py -v
python -m pytest tests/hermes/test_hybrid_guards.py -v
python -m pytest scripts/startup_gate_test.py -v
python -m pytest tests/hermes/test_security_audit.py -v
python -m pytest tests/hermes/test_integration_e2e.py -v --timeout=300
python -m compileall hermes-config src/mcp scripts tests/hermes
```

Also run `lsp_diagnostics` on changed Python/config directories where supported.

## 16. Tracker Sync Plan

After parent verification of this file:

1. Mark planner gate todo completed.
2. Mark planner verification/collision scan todo in progress.
3. Replace previous wave todos with planner-authoritative wave order:
   - Wave 1: P4-001 + P4-005.
   - Wave 2: P4-002.
   - Wave 3: P4-003 + P4-004 + P4-006.
   - Wave 4: P4-007.
   - Wave 5: P4-008.
4. Keep deployment todo but mark blocked pending explicit per-action approval.

## 17. Caveats and Blockers

- Deployment/restart remains approval-blocked.
- Live native MCP pre-tool blocking proof may require approved runtime mutation; until then, direct production native exposure is blocked.
- Existing files contain pre-existing `Any`/`type: ignore` violations; touched files must not introduce new ones and should remove touched violations where feasible.
- Standard ports 5432/6379 listening on VPS violate Aizanta isolation but remediation is a live service action requiring approval.
- FastMCP bridge has a live `_config` blocker requiring minimal code fix or alternate KEEP-7 manager.
- LLM cost tracking remains Phase 6 deferred unless directly needed for P4 tests.

## 18. Execution Checklist

- [ ] Parent read this planner gate fully.
- [ ] Parent verified every scaffold field is concrete.
- [ ] Todos synced to planner wave order.
- [ ] Collision scan confirmed before implementation.
- [ ] One implementation sub-agent per P4 step.
- [ ] Each delegation includes the relevant scaffold verbatim.
- [ ] Parent verifies claimed files and reruns scaffold commands.
- [ ] Per-step verification files created only after implementation passes.
- [ ] Independent auditor wave run after parent verification.
- [ ] All valid auditor findings fixed and re-audited.
- [ ] Deployment/restart performed only after explicit per-action approval.
- [ ] Git commit/push performed only after all verification and git-master workflow.

## 19. Footer

This planner gate resolves execution research into a machine-checkable implementation contract. It does not itself authorize live VPS mutation, restart, rollback, destructive tests, or deployment.
