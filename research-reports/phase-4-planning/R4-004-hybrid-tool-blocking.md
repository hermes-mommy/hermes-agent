# Phase 4 Planning: Hybrid Tool Blocking & Safety Patterns

**Date:** 2026-06-05  
**Scope:** Read-only research on existing shell command blocking, docker safety, terminal restriction patterns, destructive approval flows, webhook notifications, timeouts, git/github tools, and subprocess usage.  
**Target:** Inform Phase 4 (MCP + Tools) migration for 4 HYBRID mode tools.

---

## 1. Executive Summary

The codebase implements a robust, multi-layered safety architecture for tool execution, centered around a 4-tier AuthLevel system (READ_AUTO, WRITE_NOTIFY, DESTRUCTIVE_APPROVAL, FORBIDDEN). All subprocess executions strictly use syncio.create_subprocess_exec (never shell=True), with explicit timeout handling and process termination. The DESTRUCTIVE_APPROVAL flow enforces a 5-minute timeout with automatic denial, integrated with Discord webhook notifications and a Hermes /approve command.

---

## 2. Shell Tool (shell_tool) Safety Patterns

**File:** src/mcp/tools/shell_tool.py  
**Auth Level:** DESTRUCTIVE_APPROVAL (all shell operations require explicit operator approval).

### Blocking Logic
1. **Whitelist Enforcement:** Base command must exist in ALLOWED_COMMANDS (exact prefix match).
   - Allowed: ls, cat, grep, ind, wc, head, 	ail, python, pip, git, systemctl status, df, ree, uptime, hostname, whoami, pwd, echo, date, which, ile, stat.
2. **Injection Prevention:** Raw command string is scanned for _INJECTION_CHARS before parsing.
   - Blocked: ;, |, &&, ||, `  `, $(, >, <.
3. **Hard-Block Patterns:** Substring match against BLOCKED_PATTERNS.
   - Blocked: m -rf, mkfs, dd, sudo, chmod 777, wget | sh, curl | sh, :(){ (fork bomb), > /dev/sda, mv / /dev/null, shutdown, eboot, halt, poweroff.
4. **Path Isolation:** Blocks references to Aizanta-isolated paths (/home/aizanta, /etc/aizanta, /var/lib/aizanta, /opt/aizanta).
5. **Service Isolation:** Blocks systemctl commands targeting izanta services.

### Timeout Mechanism
- _DEFAULT_TIMEOUT: 30 seconds.
- _MAX_TIMEOUT: 300 seconds (hard cap).
- Implementation: syncio.wait_for(process.communicate(), timeout=timeout). On timeout, process.kill() is called, followed by wait process.wait().

---

## 3. Docker Tool (docker_tool) Safety Patterns

**File:** src/mcp/tools/docker_tool.py  
**Auth Levels:** READ_AUTO (ps, logs, inspect, images), WRITE_NOTIFY (start, stop, restart), DESTRUCTIVE_APPROVAL (rm, rmi), FORBIDDEN (system_prune, rm_all).

### Blocking Logic
1. **Network Isolation:** Containers MUST be attached to the guinevere-net network. Verified via docker inspect before any state-changing operation.
2. **Name Validation:** Container names must match ^[a-zA-Z0-9][a-zA-Z0-9_.\-]*$ (blocks shell meta-characters).
3. **Image Prefix Check:** docker_rmi only allows removal of images starting with guinevere.
4. **Forbidden Patterns:** Unconditionally blocks: system prune -a, system prune --all, olume prune, 
etwork prune, uilder prune -a.

### Timeout Mechanism
- Default timeout: 30 seconds per _run_docker call.
- Uses syncio.wait_for with process.kill() on timeout.

---

## 4. Git Tool (git_tool) Safety Patterns

**File:** src/mcp/tools/git_tool.py  
**Auth Levels:** READ_AUTO (status, log, diff), WRITE_NOTIFY (commit, push), DESTRUCTIVE_APPROVAL (push_force), FORBIDDEN (force_push to main/master).

### Blocking Logic
1. **Force Push Detection:** _is_forbidden checks for --force, -f, or --force-with-lease flags.
2. **Protected Branches:** Force push to main or master (case-insensitive, handles efs/heads/ prefixes and refspecs like HEAD:refs/heads/main) is strictly FORBIDDEN at runtime, even if DESTRUCTIVE_APPROVAL is granted.
3. **Environment Handling:** Uses GITHUB_PAT from environment for authenticated pushes.

### Subprocess Pattern
- Uses syncio.create_subprocess_exec with cwd and env parameters. No timeout explicitly set in _run_git (relies on default asyncio behavior, which is a potential Phase 4 improvement area).

---

## 5. GitHub Tool (github) Safety Patterns

**File:** src/mcp/tools/github.py  
**Auth Levels:** READ_AUTO (list_repos, get_file, search_code), WRITE_NOTIFY (create_issue, create_pr).

### Blocking & Safety Logic
1. **Authentication:** Requires GITHUB_PAT environment variable; raises ConfigurationError if missing.
2. **Rate Limit Awareness:** Extracts and logs X-RateLimit-Remaining and X-RateLimit-Reset headers.
3. **Error Handling:** 
   - 401 → ConfigurationError (invalid PAT).
   - 403 → Logs rate limit, raises HTTPStatusError.
   - 404 → Returns empty result (graceful degradation).
4. **Retry Logic:** Uses 	enacity with exponential backoff (wait_exponential(multiplier=1, max=10), stop_after_attempt(3)) for 5xx errors and TransportError.
5. **Timeout:** Hardcoded _TIMEOUT_SECONDS = 15.0 for httpx.AsyncClient.

---

## 6. DESTRUCTIVE_APPROVAL & Timeout Mechanisms

**File:** src/mcp/auth.py  
**Core Logic:** The equire_approval decorator orchestrates the approval flow.

1. **Notification:** Fires _send_discord_notification with tool name and "Awaiting operator approval..." message.
2. **Wait Mechanism:** _wait_for_approval creates an syncio.Event and stores it in _pending_approvals dict.
3. **Timeout:** _APPROVAL_TIMEOUT_SECONDS = 300.0 (5 minutes).
   - If syncio.wait_for times out, the event is cleared, and the function returns False.
   - A False return raises ForbiddenOperationError("Operation '{name}' was denied or timed out.").
4. **Resolution:** External callers (e.g., Discord bot) invoke src.mcp.auth.approve(tool_name) or deny(tool_name) to set the event and resolve the wait.

**Hermes Integration:**  
**File:** src/hermes_plugins/commands_system/approve.py  
- Provides /approve <tool_name> command.
- Checks _pending_approvals dict and calls pprove(tool_name) to unblock the waiting coroutine.

---

## 7. Webhook & Notification Systems

### Discord Webhook
**File:** src/mcp/auth.py, src/discord/notifications.py
- DISCORD_WEBHOOK_URL environment variable is read by _get_webhook_url().
- httpx.AsyncClient posts JSON payload with content field.
- Silent failure: HTTP errors are logged but do not block tool execution (fire-and-forget for WRITE_NOTIFY).

### Gotify Fallback
**File:** src/discord/gotify_fallback.py
- Triggered for SEV0 and SEV1 alerts in src/discord/notifications.py.
- Uses GOTIFY_APP_TOKEN and defaults to http://localhost:8081.
- Maps severity to Gotify priority (SEV0=10, SEV1=7, SEV2=5, SEV3=3, SEV4=1).
- 5.0 second timeout on HTTP POST. Fail-soft design (returns False on timeout, connect error, or exception).

---

## 8. Subprocess Execution Patterns

All local execution tools (shell_tool, docker_tool, git_tool) adhere to strict safety patterns:
1. **No Shell=True:** Exclusively use syncio.create_subprocess_exec(*args, ...).
2. **Argument Parsing:** Commands are split via shlex.split *after* injection checks, ensuring arguments are passed as discrete list items to exec.
3. **Timeout Enforcement:** syncio.wait_for(process.communicate(), timeout=...) is standard.
4. **Process Cleanup:** On syncio.TimeoutError, process.kill() is immediately called, followed by wait process.wait() to prevent zombie processes.
5. **Encoding Safety:** stdout/stderr decoded with errors="replace" to prevent UnicodeDecodeError crashes.

---

## 9. Centralized Auth Matrix

**File:** src/mcp/auth_matrix.py  
The AUTH_MATRIX dictionary is the single source of truth for tool operation authorization levels. It is verified at runtime by erify_matrix_completeness() to ensure all 16 registered tools have defined auth levels. The equire_approval decorator cross-checks its declared level against this matrix and logs a warning on mismatch.

---

## 10. Phase 4 Migration Recommendations

1. **Hermes 	erminal Plugin Alignment:** Ensure the Hermes 	erminal plugin respects the existing 5-minute DESTRUCTIVE_APPROVAL timeout and integrates with the _pending_approvals event system.
2. **Blocklist Porting:** The ALLOWED_COMMANDS, BLOCKED_PATTERNS, and _INJECTION_CHARS from shell_tool.py should be ported to the Hermes safety plugin (src/hermes/safety_plugin.py) as a pre_tool_call hook for defense-in-depth.
3. **Git Timeout Addition:** git_tool.py currently lacks an explicit timeout in _run_git. Add syncio.wait_for with a 30s default to match shell_tool and docker_tool patterns.
4. **WRITE_NOTIFY Async Safety:** The current syncio.create_task(_send_discord_notification(...)) is correct for non-blocking execution, but ensure the Hermes migration preserves this fire-and-forget pattern to avoid blocking the agent loop.
5. **Network Isolation Verification:** The guinevere-net check in docker_tool is a strong pattern. Ensure any new container management tools in Phase 4 inherit this _check_guinevere_network guard.

---
*Generated by Guinevere Research Agent — Read-Only Analysis*