# R04 — Forbidden Patterns & Code Quality Audit

| Field | Value |
|---|---|
| Audit Target | P5 Agent Loop |
| Scope | src/loops/, src/core/api/, src/discord/cmd_loop_start.py, src/discord/cmd_loop_stop.py |
| Files Scanned | 23 Python source files (excluding __pycache__) |
| Date | 2026-06-02 |
| Auditor | R04 Forbidden Patterns Scanner |
| Verdict | **NEEDS REVIEW** — 18 findings across 8 categories |

---

## Executive Summary

The P5 Agent Loop codebase is **well-structured** with strong patterns: consistent structlog usage (in loops/api), comprehensive docstrings, `from __future__ import annotations` across nearly all files, zero `print()` statements, zero bare excepts, and zero hardcoded secrets. However, **18 findings** require review across security (`shell=True`, `cast()`, hardcoded dev-key fallbacks), type-safety (`Any` usage in 5 files), code quality (4 functions over 50 lines, 2 files over 300 lines), and logging inconsistency (discord files use `logging` instead of `structlog`).

---

## Files Inventory

### src/loops/ (20 source files)

| File | Lines | structlog | future annotations |
|---|---|---|---|
| `__init__.py` | 39 | N/A (no logger) | Missing* |
| `manager.py` | 272 | YES | YES |
| `state_machine.py` | 226 | YES | YES |
| `cost.py` | 194 | YES | YES |
| `evidence.py` | 194 | YES | YES |
| `verify.py` | 183 | YES | YES |
| `scheduler.py` | 175 | YES | YES |
| `guardian.py` | 157 | YES | YES |
| `enforcer.py` | 132 | YES | YES |
| `sub_agent.py` | 128 | YES | YES |
| `contract.py` | 130 | YES | YES |
| `hash_anchor.py` | 145 | YES | YES |
| `artifacts.py` | 100 | YES | YES |
| `phases/__init__.py` | 48 | N/A (no logger) | YES |
| `phases/setup_evidence.py` | 70 | YES | YES |
| `phases/validate_audit.py` | 104 | YES | YES |
| `phases/research.py` | 55 | YES | YES |
| `phases/plan_delegate.py` | 57 | YES | YES |
| `phases/delegate.py` | 57 | YES | YES |
| `phases/execute.py` | 56 | YES | YES |
| `phases/update_docs.py` | 53 | YES | YES |

*Note: `src/loops/__init__.py` has 39 lines, is a re-export module, and does not contain type annotations that require `from __future__ import annotations`.

### src/core/api/ (3 source files)

| File | Lines | structlog | future annotations |
|---|---|---|---|
| `__init__.py` | 1 | N/A | N/A (trivial) |
| `routes.py` | 90 | YES | **MISSING** |
| `auth.py` | 62 | YES | YES |

### src/discord/ (2 target files)

| File | Lines | structlog | future annotations |
|---|---|---|---|
| `cmd_loop_start.py` | 453 | **NO — uses logging.getLogger** | YES |
| `cmd_loop_stop.py` | 522 | **NO — uses logging.getLogger** | YES |

---

## FORBIDDEN PATTERNS — Detailed Findings

### 1. Type Safety Suppression (`as any` / `@ts-ignore` / `# type: ignore` / `@ts-expect-error`)

**Verdict: PASS — 0 findings**

No matches found in any scanned file.

---

### 2. `cast(` — Type Casting

**Verdict: NEEDS REVIEW — 2 findings**

| File | Line | Code | Severity |
|---|---|---|---|
| `src/discord/cmd_loop_start.py` | 109 | `return cast(DiscordEmbedModule, cast(object, mod))` | Medium |
| `src/discord/cmd_loop_stop.py` | 109 | `return cast(DiscordEmbedModule, cast(object, mod))` | Medium |

**Context:** Both files use `importlib.import_module("discord")` to dynamically import the discord package (so the module works even without discord.py installed), then use double-cast to satisfy the type checker. The `cast(object, mod)` intermediate step is unusual and suggests the type checker cannot resolve `types.ModuleType` to the Protocol.

**Risk:** Low functional risk — the runtime_checkable Protocol validates at runtime. However, `cast()` is type-safety suppression per AGENTS.md BLOCKING rules.

**Recommendation:** Replace with explicit attribute extraction or `typing.TYPE_CHECKING` guard with a conditional runtime isinstance check.

---

### 3. Bare `except:` (No Exception Type)

**Verdict: PASS — 0 findings**

No bare except clauses found. All except blocks specify exception types.

---

### 4. `except Exception` with Swallowed Errors (`pass` / Empty Body)

**Verdict: PASS — 0 findings (all have substantive handling)**

All `except Exception` blocks contain substantive error handling:

| File | Line | Handling |
|---|---|---|
| `src/loops/manager.py` | 214 | Logs error, calls `state.fail(reason)`, attempts partial evidence report |
| `src/loops/manager.py` | 227 | Logs nested exception from final report generation |
| `src/loops/scheduler.py` | 81 | Logs warning and re-raises |
| `src/loops/scheduler.py` | 149 | Logs error (does NOT re-raise — see **advisory note** below) |
| `src/discord/cmd_loop_start.py` | 385 | Calls `logger.exception()`, sends user-facing error message |
| `src/discord/cmd_loop_stop.py` | 454 | Calls `logger.exception()`, sends user-facing error message |

**Advisory Note (scheduler.py:149):** The `_trigger_loop` method catches `Exception` and logs but does not re-raise. This is a fire-and-forget scheduler trigger, so silent swallowing is intentional — but consider whether scheduler job failures should propagate to APScheduler's error handler.

---

### 5. `shell=True` in subprocess Calls

**Verdict: NEEDS REVIEW — 1 finding**

| File | Line | Context | Severity |
|---|---|---|---|
| `src/loops/verify.py` | 110 | `subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)` | **HIGH** |

**Context:** `OutputVerifier.verify_command()` accepts an arbitrary shell command string and executes it with `shell=True`. This is used by the scaffold verification system to run user-defined commands.

**Risk:** If `command` can be influenced by untrusted input (LLM output, sub-agent output, external API response), this is a **command injection vulnerability**. Even with a 30-second timeout, an attacker could execute arbitrary commands.

**Mitigating factors:**
- The `command` parameter originates from the planner scaffold, which is generated by the agent loop itself (trusted internal source).
- Timeout is 30 seconds.
- `capture_output=True` prevents stdout/stderr leakage.

**Recommendation:** Add input validation/sanitization on the `command` parameter. Consider using `shlex.split()` + `shell=False` for simple commands, or implement a command allowlist for scaffold verification.

---

### 6. `eval(` / `exec(` — Code Injection Risks

**Verdict: PASS — 0 findings**

No `eval()` or `exec()` calls found in any scanned file.

---

### 7. Hardcoded Passwords, Tokens, or API Keys

**Verdict: NEEDS REVIEW — 3 findings**

| File | Line | Code | Severity |
|---|---|---|---|
| `src/core/api/auth.py` | 15 | `_DEV_DEFAULT_KEY: str = "guinevere-dev-key"` | Medium |
| `src/discord/cmd_loop_start.py` | 344 | `os.environ.get("GUINEVERE_API_KEY", "guinevere-dev-key")` | Medium |
| `src/discord/cmd_loop_stop.py` | 384 | `os.environ.get("GUINEVERE_API_KEY", "guinevere-dev-key")` | Medium |

**Context:** All three instances use `"guinevere-dev-key"` as a fallback when `GUINEVERE_API_KEY` is not set in the environment. In `auth.py`, the fallback triggers a `logger.warning` — good defensive practice.

**Risk:** If deployed to production without `GUINEVERE_API_KEY` set, the system silently falls back to a known, guessable key. The discord commands pass this key directly in HTTP headers.

**Recommendation:**
- In `auth.py`: Consider raising an error (not warning) when `GUINEVERE_API_KEY` is unset in non-dev environments.
- In discord commands: Fail explicitly instead of falling back to a hardcoded key.
- Add an environment detection check (e.g., `GUINEVERE_ENV=production`) that blocks fallback usage.

**Note on cost.py:** `password=os.environ.get("REDIS_PASSWORD", "")` uses an empty string default, which is safe — the connection will simply fail if the password is wrong, not silently succeed.

---

### 8. `os.system(` — Shell Injection

**Verdict: PASS — 0 findings**

No `os.system()` calls found.

---

### 9. `Any` Type Usage in Annotations

**Verdict: NEEDS REVIEW — 14 annotation usages across 5 files**

| File | Lines | Usage | Count |
|---|---|---|---|
| `src/loops/verify.py` | 28, 97, 115, 164, 173 | `dict[str, Any]`, `list[dict[str, Any]]` | 5 |
| `src/loops/sub_agent.py` | 37, 40, 61, 81 | `dict[str, Any]`, `list[dict[str, Any]]` | 4 |
| `src/loops/manager.py` | 91, 128, 142 | `dict[str, Any]`, `list[dict[str, Any]]` | 3 |
| `src/loops/enforcer.py` | 29 | `dict[str, dict[str, Any]]` | 1 |
| `src/loops/guardian.py` | 32 | `dict[str, dict[str, Any]]` | 1 |

**Pattern:** All usages follow the pattern `dict[str, Any]` for heterogeneous dictionaries returned from methods or stored as instance attributes. This is a common Python pattern for loosely-structured data.

**Assessment:** While `Any` is technically forbidden per AGENTS.md, these usages are in structural positions where the dict contents are inherently heterogeneous (verification results, agent records, loop state dicts). Replacing with `dict[str, object]` would require extensive `isinstance` checks or cast-unsafe access patterns.

**Recommendation:** Consider using Pydantic models or TypedDict for these structures. If not feasible, `dict[str, object]` with proper narrowing at access points is the correct alternative.

---

### 10. `pass` Statements Without Docstring Justification

**Verdict: PASS — 0 findings (all are standard CancelledError idiom)**

| File | Line | Context |
|---|---|---|
| `src/loops/guardian.py` | 156 | `except asyncio.CancelledError: pass` |
| `src/loops/manager.py` | 120 | `except asyncio.CancelledError: pass` |
| `src/loops/manager.py` | 261 | `except asyncio.CancelledError: pass` |

All three are the standard Python idiom for acknowledging task cancellation in an `await` block. This is universally accepted and not a code quality concern.

---

## CODE QUALITY — Detailed Findings

### 11. Missing Docstrings on Public Classes/Functions

**Verdict: PASS — 0 findings**

All 11 public classes and all public methods/functions across the scanned files have comprehensive docstrings with Args/Returns/Raises sections.

---

### 12. Functions Over 50 Lines

**Verdict: NEEDS REVIEW — 4 findings**

| File | Function | Lines | Size |
|---|---|---|---|
| `src/loops/manager.py` | `_run_loop()` | 150–234 | **84 lines** |
| `src/loops/evidence.py` | `generate_final_report()` | 74–173 | **99 lines** |
| `src/loops/cost.py` | `record_loop_cost()` | 55–123 | **68 lines** |
| `src/discord/cmd_loop_stop.py` | `loop_stop_callback()` | 363–462 | **99 lines** |

**Details:**

- **`_run_loop`** (manager.py): Orchestrates the 7-phase execution loop with error handling. Could be split into `_execute_phases()` + `_handle_loop_error()`.
- **`generate_final_report`** (evidence.py): Builds the evidence report markdown. The long f-string template (lines 118–158) inflates line count. Could extract template to a separate constant.
- **`record_loop_cost`** (cost.py): Redis pipeline operations + global tracker sync. Could split into `_write_redis_cost()` + `_sync_global_tracker()`.
- **`loop_stop_callback`** (cmd_loop_stop.py): Complex Discord callback with multiple API calls and branching. Could extract the cancellation logic into a helper function.

---

### 13. Files Over 300 Lines

**Verdict: NEEDS REVIEW — 2 findings**

| File | Lines | Over By |
|---|---|---|
| `src/discord/cmd_loop_start.py` | 453 | +153 |
| `src/discord/cmd_loop_stop.py` | 522 | +222 |

**Note:** Both files contain significant code duplication — Protocol definitions, embed builders, helper functions, and callback logic are nearly identical between the two files. Consider extracting shared Discord interaction utilities into a `src/discord/_shared.py` module.

All other files are under 300 lines (largest non-discord file: `manager.py` at 272 lines).

---

### 14. Inconsistent structlog Usage

**Verdict: NEEDS REVIEW — 2 findings**

| File | Line | Logger Type |
|---|---|---|
| `src/discord/cmd_loop_start.py` | 28 | `logging.getLogger(__name__)` |
| `src/discord/cmd_loop_stop.py` | 28 | `logging.getLogger(__name__)` |

**Context:** All 19 files in `src/loops/` and both files in `src/core/api/` consistently use `structlog.get_logger()`. Only the two Discord command files deviate, using stdlib `logging.getLogger()`.

**Impact:** Structured logging metadata (`loop_id=`, `error=`, etc.) is not available from these files' log output. Inconsistency makes log aggregation and searching harder.

**Recommendation:** Migrate to `structlog.get_logger()` for consistency. Note that `logger.exception()` calls (lines 368, 377, 386, 437, 446, 455) work with both stdlib logging and structlog.

---

### 15. `print(` Statements

**Verdict: PASS — 0 findings**

No `print()` statements found. All logging goes through structlog or stdlib logging.

---

### 16. Missing `from __future__ import annotations`

**Verdict: NEEDS REVIEW — 1 finding**

| File | Status |
|---|---|
| `src/core/api/routes.py` | **MISSING** |

**Context:** `routes.py` uses `from typing import Optional` (line 4) instead of the modern `X \| None` syntax. Adding `from __future__ import annotations` would enable PEP 604 union syntax and eliminate the `Optional` import.

All other non-trivial files (22 of 23) include the import.

---

## Additional Observations (Not in Scan Scope but Noted)

### A. Code Duplication Between Discord Files

`cmd_loop_start.py` and `cmd_loop_stop.py` share approximately 200 lines of duplicated code:
- Protocol definitions (`DiscordEmbedModule`, `DiscordEmbedProtocol`, `DiscordResponseProtocol`)
- Dynamic import helper (`_get_discord_embed_module`)
- Interaction helpers (`_send_denied`, `_defer_ephemeral`, `_followup_send`, `_get_option_value`)
- Timezone and formatting utilities

### B. `_trigger_loop` Silent Exception Swallowing (scheduler.py:149)

The `_trigger_loop` method catches `Exception` and only logs — no re-raise. APScheduler may not be aware of the failure. Consider whether this should propagate.

### C. `Optional` vs `X | None` in routes.py

`routes.py` uses `from typing import Optional` — inconsistent with the rest of the codebase which uses `X | None` (enabled by `from __future__ import annotations`).

---

## Summary Scorecard

| # | Check | Verdict | Findings |
|---|---|---|---|
| 1 | Type safety suppression (as any, @ts-ignore, etc.) | **PASS** | 0 |
| 2 | `cast()` type casting | **NEEDS REVIEW** | 2 |
| 3 | Bare `except:` | **PASS** | 0 |
| 4 | Swallowed `except Exception` | **PASS** | 0 (advisory: 1) |
| 5 | `shell=True` | **NEEDS REVIEW** | 1 (HIGH) |
| 6 | `eval()` / `exec()` | **PASS** | 0 |
| 7 | Hardcoded credentials | **NEEDS REVIEW** | 3 |
| 8 | `os.system()` | **PASS** | 0 |
| 9 | `Any` type usage | **NEEDS REVIEW** | 14 usages / 5 files |
| 10 | Unjustified `pass` | **PASS** | 0 |
| 11 | Missing docstrings | **PASS** | 0 |
| 12 | Functions > 50 lines | **NEEDS REVIEW** | 4 |
| 13 | Files > 300 lines | **NEEDS REVIEW** | 2 |
| 14 | Inconsistent structlog | **NEEDS REVIEW** | 2 |
| 15 | `print()` statements | **PASS** | 0 |
| 16 | Missing future annotations | **NEEDS REVIEW** | 1 |

**Overall: NEEDS REVIEW** — 18 findings (1 HIGH security, 5 medium, 12 code quality)

---

## Priority Fix Order

1. **[HIGH] shell=True** in `verify.py` — Add command sanitization or allowlist
2. **[MEDIUM] Hardcoded dev-key fallbacks** — Fail explicitly in production, or add env detection
3. **[MEDIUM] cast() in discord files** — Replace with isinstance + Protocol check
4. **[MEDIUM] Discord files use logging instead of structlog** — Migrate for consistency
5. **[LOW] Any type usage** — Replace with TypedDict or Pydantic models where feasible
6. **[LOW] Functions > 50 lines** — Extract helper methods
7. **[LOW] Files > 300 lines** — Extract shared Discord utilities
8. **[LOW] routes.py missing future annotations** — Add import, replace Optional

---

_Report generated by R04 Forbidden Patterns Scanner for P5 Agent Loop audit._