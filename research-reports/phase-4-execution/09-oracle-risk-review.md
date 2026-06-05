---
title: "Phase 4 Hermes MCP Execution — Oracle Risk Review"
status: "Draft"
date: "2026-06-05"
reviewer: "Oracle (Architecture/Security Consultant)"
sources:
  - "docs/setup-evidence/hermes-migration/phase-4-mcp.md"
  - "docs/setup-evidence/hermes-migration/batch-plan-migration.md (§Phase 4)"
  - "adr/ADR-035-hermes-migration.md (§Pillar 4, §Phase 4)"
  - "src/mcp/auth_matrix.py"
  - "src/mcp/auth.py"
  - "src/mcp/budget.py"
  - "src/hermes/safety_plugin.py"
  - "hermes-config/hooks/_hook_utils.py"
  - "AGENTS.md (§7, §9)"
  - "docs/20-security/20-SecurityPolicy_v1.0.md"
  - "docs/20-security/21-AccessControl_RBAC_ABAC_v1.0.md"
---

# Phase 4 Hermes MCP Tool Execution Migration — Oracle Risk Review

## Bottom Line

**CONDITIONAL GO** — Phase 4 is architecturally sound but has 4 must-fix design issues that create real auth enforcement gaps, a dangerous dual-source-of-truth for the auth matrix, and missing startup/fail-closed guarantees. The plan's safety checks (P4-T1 through P4-T5) are necessary but insufficient — they test individual components in isolation, not the **composite auth chain** where gaps emerge. Fix the 4 blocking items before implementation; the remaining 5 are watch-items that can be mitigated during implementation.

**Effort to fix**: Short (~4h total across all must-fix items).

---

## Action Plan

1. **Consolidate auth matrix to ONE source of truth** — Delete the inline `AUTH_MATRIX` dict in `plugins/auth_overlay.py`. Use ONLY `src/mcp/auth_matrix.py` (imported). The YAML file at `config/hermes/auth_matrix.yaml` must be a **generated artifact** (not hand-edited), produced by a script that reads `auth_matrix.py` and dumps YAML. Test: `verify_matrix_completeness()` still returns True after every startup, and the YAML file matches the Python source via checksum.

2. **Fix native MCP auth gap** — The `pre_tool_call` hook fires INSIDE Hermes's pipeline, but Hermes native MCP servers (terminal, filesystem, git, fetch, web) may dispatch tool execution before the hook callback returns. **Mitigation**: Set `tools: []` on all native MCP server configs (disable all tools at the Hermes level), then re-expose them ONLY through the auth overlay plugin as a proxy/relay. This ensures the plugin gates every invocation. If Hermes doesn't support tool-level disable, wrap the native tool endpoint behind a local proxy that the plugin controls.

3. **Add startup gate enforcement** — The plan says "critical: true → Hermes refuses to start without auth_overlay" but this depends on Hermes's plugin loader behavior, which has NOT been verified. **Add an explicit startup check** in the Hermes gateway entrypoint: before `hermes gateway start`, run `python -c "from plugins.auth_overlay import AuthOverlayPlugin; p=AuthOverlayPlugin(); p.on_load({})"` — if it imports or instantiation fails, abort startup with exit code 1. This is a code gate, not a config gate.

4. **Persist destructive approval state to Redis DB5** — The current in-process `_pending_approvals` dict loses state on Hermes restart. Extend `plugins/auth_overlay.py` to store pending approvals in Redis DB5 with a 5-minute TTL (matching the approval timeout). On plugin reload, scan Redis for pending approvals and re-attach the asyncio.Event. This prevents dropped approval requests during gateway restarts.

---

## Why This Approach

- **Single source of truth** eliminates the highest-severity risk: auth matrix divergence between Python code and YAML config. Currently, Phase 4 creates THREE representations (`auth_matrix.py`, `auth_overlay.py` inline dict, `auth_matrix.yaml`) that can silently drift. A single Python source with YAML as a derived artifact is the only way to guarantee consistency.
- **Native tool proxy** is the only reliable fix for the Hermes native MCP auth gap. The `pre_tool_call` hook is advisory in Hermes's architecture for native tools — the actual tool dispatch may race ahead of the hook response. Disabling native tool registration and proxying through the plugin guarantees interception.
- **Explicit startup gate** doesn't rely on Hermes's plugin `critical` flag behavior being correct for all failure modes. A verified Python-side import/instantiation check before gateway start is defense-in-depth.
- **Persistent approval state** is required because Hermes gateway restarts are not zero-risk during Phase 4 operations (config reloads, plugin updates, native MCP server connection drops). Lost approvals would destroy user trust in the destructive approval workflow.

---

## Watch Out For

- **Auth matrix completeness gap**: The plan's Phase 4 `AUTH_MATRIX` in `auth_overlay.py` uses DIFFERENT tool names from the existing `src/mcp/auth_matrix.py`. The existing code uses `["brave_search", "context7", "docker", "exa", "fetch", "filesystem", "git", "github", "grep_app", "obscura_cdp", "postgres", "redis", "sequential_thinking", "shell", "time", "websearch"]`. The plan's overlay uses `["web", "filesystem", "terminal", "git", "fetch", "postgres_tool", "redis_tool", "obscura_cdp", "grep_app", "context7", "sequential_thinking", "time_tools"]` — note `"postgres_tool"` vs `"postgres"`, `"redis_tool"` vs `"redis"`, `"terminal"` vs `"shell"`, etc. These mismatches mean the auth overlay will treat every call to the existing tools as UNKNOWN → FORBIDDEN (fail-closed but BROKEN). **Must reconcile naming before implementation.**
- **Budget enforcement is NOT integrated into the auth overlay**: The plan's Phase 4 Safety Checkpoint P4-T4 says "Budget: 80% alert, 100% block" but the budget check lives in `src/mcp/budget.py` as a separate path (not called by the auth overlay). The auth overlay must call `BudgetEnforcer.check_budget()` on every tool invocation, or destructive operations could proceed past budget caps. The ADR-035 hook #3 (`pre_tool_call` → consent_gate.py) correctly includes budget, but the Phase 4 auth overlay plan doesn't mention budget integration.
- **Rollback risk**: The Phase 4 rollback (`git checkout -- src/mcp/manager.py src/mcp/auth_matrix.py src/mcp/tools/`) could revert Phase 1-3 changes if those phases modified the same files. Create a phase-specific git tag (`phase-4-baseline`) immediately before beginning Phase 4 implementation.

---

## Risk Register — Detailed Findings

| # | Finding | Severity | Status | Details |
|---|---------|----------|--------|---------|
| **F1** | Auth matrix triple-source-of-truth | **CRITICAL** | MUST FIX | Three representations (`auth_matrix.py`, `auth_overlay.py` inline dict, `auth_matrix.yaml`) can diverge silently. Tool names mismatch between sources (e.g., `postgres` vs `postgres_tool`, `shell` vs `terminal`). |
| **F2** | Native MCP tools bypass auth hook | **CRITICAL** | MUST FIX | Hermes native MCP servers (web, filesystem, terminal, git, fetch) may execute tool calls before the `pre_tool_call` hook callback returns. The plan's CAUTION note acknowledges this but relies on timing, not architectural enforcement. |
| **F3** | Startup gate unverifiable | **HIGH** | MUST FIX | The plan relies on Hermes's `critical: true` plugin flag, but this behavior has NOT been tested against v0.15.2. If the plugin fails to load but Hermes starts anyway (graceful degradation), all 16 tools execute WITHOUT auth enforcement. |
| **F4** | Approval state lost on restart | **HIGH** | MUST FIX | `_pending_approvals` is in-process dict. Hermes gateway stop/start during Phase 4 drops all pending destructive approval requests. User must re-initiate the operation from scratch. |
| **F5** | Tool name mismatch in overlay | **HIGH** | MUST FIX | The auth overlay's `AUTH_MATRIX` uses different keys than `src/mcp/auth_matrix.py`: `postgres_tool` vs `postgres`, `redis_tool` vs `redis`, `terminal` vs `shell`, `time_tools` vs `time`. Existing code calling these tools will get FORBIDDEN for everything. |
| **F6** | Budget enforcement missing from auth chain | **HIGH** | MUST FIX | Phase 4 Safety Checkpoint P4-T4 expects budget enforcement, but the auth overlay plugin code in `phase-4-mcp.md` has NO budget check integration. Budget is a separate path in `src/mcp/budget.py` that the overlay never calls. |
| **F7** | FORBIDDEN_COMMANDS list overlap with native terminal | **MEDIUM** | WATCH | The plan's `FORBIDDEN_COMMANDS` list (rm -rf /, dd, mkfs, shutdown, reboot, etc.) overlaps with `terminal.blocked_commands` config. The block must work at both levels (Hermes config + auth overlay) or one becomes a bypass path. |
| **F8** | Pre_tool_call hook order unspecified | **MEDIUM** | WATCH | With consent gate hook + auth overlay plugin + budget check all targeting the same lifecycle point, the execution ORDER determines safety. If consent check happens AFTER tool execution, the model already has tool results. Must document and test hook priority ordering. |
| **F9** | Webhook approval timeout vs UX | **LOW** | WATCH | 5-minute approval timeout is long for a destructive operation. If the Discord webhook message goes unseen, the operation sits pending for 5 minutes, then silently denies. No retry mechanism or escalation path exists in the plan. |
| **F10** | Phase 4 rollback may corrupt Phase 1-3 state | **MEDIUM** | WATCH | Rollback uses `git checkout -- src/mcp/manager.py src/mcp/auth_matrix.py src/mcp/tools/` — these files may have been modified by Phase 1-3. Rollback without a phase-4-baseline git tag could lose legitimate changes. |

---

## Go/No-Go Conditions

### GO Conditions (all must pass)

| Condition | Verification | Phase 4 Gate |
|-----------|-------------|-------------|
| Auth matrix single source of truth | `pytest tests/mcp/test_auth_matrix.py -v` passes AND `verify_matrix_completeness()` returns True AFTER `auth_overlay.py` is loaded. Only `src/mcp/auth_matrix.py` defines tool→level mappings. | P4-T1 superseded |
| Native MCP tools proxied through auth overlay | Test: register 5 native MCP tools, verify that `hermes tool test terminal run "ls"` returns the auth overlay block/notify result, not a direct terminal output. The auth hook fires BEFORE native tool dispatch. | New gate (P4-T6) |
| Startup gate verified | `python -c "from plugins.auth_overlay import AuthOverlayPlugin; p=AuthOverlayPlugin(); assert p.on_load({})"` returns True. Hermes gateway start WITHOUT `auth_overlay.py` importable → exit code 1. | P4-T2 expanded |
| Destructive approval persists across restart | Test: queue destructive operation → kill Hermes gateway → restart → verify pending approval can still be resolved. Redis DB5 shows pending approval with correct TTL. | New gate (P4-T7) |
| Tool names reconciled | All 16 tools in auth overlay match the canonical names in `src/mcp/auth_matrix.ALL_TOOL_NAMES`. Zero FORBIDDEN false positives from name mismatch. | P4-T1 integrated |
| Budget check called by auth overlay | Auth overlay calls `BudgetEnforcer.check_budget()` on every tool invocation. At $31 monthly (above $30 cap), ALL 16 tools return budget error, not just exa/brave. | P4-T4 expanded |

### NO-GO Triggers (ANY → full investigation, do not proceed)

- Auth overlay can be bypassed by calling a native MCP tool directly (bypassing Hermes hook pipeline)
- `config/hermes/auth_matrix.yaml` differs from `src/mcp/auth_matrix.py` in any tool name, operation, or auth level
- `hermes gateway start` succeeds when `plugins/auth_overlay.py` has a syntax error or missing import
- Any tool in `src/mcp/auth_matrix.ALL_TOOL_NAMES` is missing from the auth overlay's enforcement
- Budget enforcement can be bypassed by using a native MCP tool (hermes terminal/git/fetch) instead of a custom tool

---

## Hidden Blockers

1. **Hermes v0.15.2 hook behavior undocumented**: The `pre_tool_call` hook's exact timing relative to native MCP tool dispatch is NOT documented in any research report. The 16 Phase 1 reports never tested this specific scenario. The hook MAY fire AFTER the native tool has already executed. This is the single biggest unknown in Phase 4. **Mitigation**: Verify with a test that registers a native MCP tool then checks whether `pre_tool_call` can block it. If not, implement the proxy approach (Action Plan item #2).

2. **YAML auth_matrix.yaml is never validated at runtime**: The plan creates `config/hermes/auth_matrix.yaml` as a reference but neither the auth overlay nor any test reads it. If someone edits the YAML thinking it's authoritative, the change has ZERO effect — the inline `AUTH_MATRIX` dict in `auth_overlay.py` is what actually executes. This creates a dangerous illusion of configurability.

3. **Discord webhook approval is synchronous blocking on the event loop**: The current `src/mcp/auth.py` implementation (`_wait_for_approval`) blocks the Hermes event loop for up to 5 minutes while waiting for approval. If the Hermes gateway is single-threaded (likely for an async Discord bot), this blocks ALL other message processing for up to 5 minutes. The auth overlay must use a non-blocking pattern that yields control back to the event loop while waiting.

---

## Full Autonomous Execution — Per-Action Approval Requirements

Per AGENTS.md (§7 Operator Protocol) and the "NEVER auto-deploy or run destructive ops without explicit per-action approval" BLOCKING rule, the following Phase 4 steps require **explicit per-action approval from Faiz** even under "full autonomous" instruction:

| Step | Action | Reason |
|------|--------|--------|
| 4.1 | `hermes mcp add ...` (5 native MCP servers) | Registers new tool endpoints that execute system commands. Without verified auth overlay protection, this introduces code execution risk. **Requires approval BEFORE first `hermes mcp add` command.** |
| 4.2 | Create `plugins/auth_overlay.py` | File creation is safe, but the auth matrix contents must be reviewed by Faiz before plugin activation. The tool→auth level mappings directly control what the LLM can do to the system. |
| 4.3 | `sudo systemctl restart guinevere-mcp` | Service restart with potential config changes. |
| 4.4 | `hermes gateway restart` (config reload) | Gateway restart with auth overlay activation. If auth overlay fails, all tools are unprotected during the brief restart window. |
| Rollback | `hermes mcp remove ...`, `git checkout -- ...`, `sudo systemctl restart ...` | Destructive rollback may overwrite Phase 1-3 changes. Requires approval before execution. |
| Destructive approval test | `hermes tool test redis_tool flush "DB5"` | Actual destructive operation on a live Redis database. Must use a test/staging environment or accept data loss risk. |

**Recommended flow**: Faiz reviews and approves the auth matrix mapping (16 tools × operations → auth levels) BEFORE any `hermes mcp add` or `hermes gateway restart` command executes. This gives Faiz explicit visibility into what auth levels the LLM has on each tool before the gateway goes live with native MCP capabilities.

---

## Escalation Triggers

If any of the following are discovered during implementation, escalate to Faiz immediately:

- Hermes v0.15.2 `pre_tool_call` hook cannot block native MCP tool execution (confirms F2)
- `critical: true` plugin flag does NOT prevent Hermes startup when the plugin module is missing or has a syntax error (confirms F3)
- Any tool operation in the existing `src/mcp/auth_matrix.AUTH_MATRIX` is missing a mapping in the auth overlay
- Budget enforcement has been bypassed by a tool call in testing
- Redis connection to DB5 fails during auth overlay startup (deny all tool calls until resolved)

---

## Alternative Sketch (if Hermes hook cannot block native tools)

If the `pre_tool_call` hook cannot stop Hermes native MCP tool execution (confirmed blocker F2):

1. **Don't register native MCP servers at all**. Keep ALL 16 tools on the custom FastMCP server (`guinevere-mcp.service`).
2. Use the auth overlay plugin to **proxy tool calls**: when the LLM requests a native-equivalent tool, the plugin intercepts the request at the Hermes plugin layer, applies the auth matrix, and forwards the approved call to the FastMCP server as a custom tool.
3. This eliminates the native MCP auth gap entirely, at the cost of losing some Hermes-native features (streaming tool output, native error handling). Risk Level: MEDIUM (performance overhead).
4. Revisit native MCP migration in Phase 7 hardening after the auth overlay is proven in production.
