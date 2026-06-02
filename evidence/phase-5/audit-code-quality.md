# Code Quality Audit — P5 Agent Loop

## Summary
- **Verdict: NEEDS REVIEW**
- Files audited: 28 (25 new, 3 modified)
- Findings: 9 (0 critical, 3 major, 6 minor)

No blocking critical issues. The codebase is clean, well-documented, and follows consistent patterns. Three major findings require attention before production readiness: `shell=True` subprocess usage, synchronous Redis in an async-capable module, and broad exception catching in the scheduler. Six minor findings relate to style consistency.

---

## Critical Findings (blocks completion)

_None._

---

## Major Findings (should fix)

### M1 — `subprocess.run(shell=True)` in verify.py

- **File:** `src/loops/verify.py`, line 110
- **Severity:** Major (security)
- **Description:** `verify_command()` passes the command string directly to `subprocess.run(command, shell=True, ...)`. If any untrusted input reaches this method, it enables shell injection attacks.
- **Recommendation:** Use `shlex.split(command)` with `shell=False`, or enforce that callers pass pre-split argument lists. At minimum, add a docstring warning that callers must sanitize input.

### M2 — Synchronous Redis in cost.py

- **File:** `src/loops/cost.py`, lines 32-39
- **Severity:** Major (async correctness)
- **Description:** `LoopCostTracker` uses `redis.Redis` (synchronous client). If any method is called from an async context (e.g., `LoopManager._run_loop`), it will block the event loop. Currently not wired into the main loop execution path, but the module is exported from `src/loops/__init__.py` suggesting future async integration.
- **Recommendation:** Use `redis.asyncio.Redis` and make methods `async def`, or document that all methods must be called via `asyncio.to_thread()`.

### M3 — Broad `except Exception` in scheduler.py trigger

- **File:** `src/loops/scheduler.py`, lines 149-154
- **Severity:** Major (error handling)
- **Description:** `_trigger_loop()` catches `Exception` and logs the error without re-raising. Scheduled cron jobs that fail silently may leave operators unaware of recurring failures. Unlike `manager.py` line 214 (which is a top-level loop runner that also logs + fails the state machine), this silently drops the failure.
- **Recommendation:** Add a failure counter or notification mechanism. At minimum, log at `error` level with the task name for alerting integration. Consider using `except (RuntimeError, ConnectionError, OSError)` to narrow the catch.

---

## Minor Findings (nice to have)

### m1 — `from __future__ import annotations` missing in routes.py and loops/\_\_init\_\_.py

- **Files:** `src/core/api/routes.py`, `src/loops/__init__.py`
- **Description:** 20 of 22 loops-source files use `from __future__ import annotations`. These two files are exceptions. Not a bug, but breaks the pattern.
- **Recommendation:** Add `from __future__ import annotations` for consistency.

### m2 — `Optional[str]` vs `str | None` inconsistency in routes.py

- **File:** `src/core/api/routes.py`, lines 4, 28
- **Description:** Uses `from typing import Optional` and `Optional[str]` while `auth.py` uses PEP 604 syntax `str | None`. The rest of the P5 codebase uses PEP 604.
- **Recommendation:** Replace `Optional[str]` with `str | None` and remove the `from typing import Optional` import.

### m3 — Import order in routes.py

- **File:** `src/core/api/routes.py`, lines 3-10
- **Description:** Imports are not alphabetically sorted. `uuid` and `typing` are stdlib, `structlog`/`fastapi` are third-party, `src.core.api.auth` is local, `pydantic` is third-party — the third-party imports are interleaved with local imports.
- **Recommendation:** Group: stdlib → third-party → local, alphabetically within each group.

### m4 — Logging style inconsistency in guardian.py and enforcer.py

- **Files:** `src/loops/guardian.py`, `src/loops/enforcer.py`
- **Description:** Most phase handlers use dot-notation log events (`phase.research.start`), while guardian/enforcer use underscore-notation (`loop_registered`, `heartbeat_received`). Both styles appear in `manager.py` (`loop_manager.loop_started` with dots).
- **Recommendation:** Standardize on dot-notation for all loop system events (e.g., `guardian.loop_registered`, `enforcer.agent_tracked`).

### m5 — `Any` usage in 5 files for heterogeneous dicts

- **Files:** `guardian.py`, `enforcer.py`, `sub_agent.py`, `verify.py`, `manager.py`
- **Description:** All use `dict[str, Any]` for records containing mixed types (str, datetime, bool, None). This is functionally correct but loses type information.
- **Recommendation:** Replace with `TypedDict` or Pydantic `BaseModel` for stronger typing. Acceptable as-is for P5 placeholder code.

### m6 — Private attribute access in manager.py main()

- **File:** `src/loops/manager.py`, line 264
- **Description:** Module-level `main()` function accesses `manager._tasks` (private attribute). While it is in the same file, accessing private attributes from outside the class is a style concern.
- **Recommendation:** Add a public method like `get_active_tasks()` or `cancel_all()` on `LoopManager`.

---

## Per-File Results

| File | Status | Notes |
|------|--------|-------|
| `src/core/api/routes.py` | PASS (minor) | Missing `__future__`, `Optional` vs `| None`, import order |
| `src/core/api/auth.py` | PASS | Clean. HMAC compare, proper HTTPException, good docstrings |
| `src/loops/__init__.py` | PASS (minor) | Missing `__future__` import; otherwise clean re-exports |
| `src/loops/state_machine.py` | PASS | Clean. IntEnum, frozenset terminal statuses, good serialisation |
| `src/loops/artifacts.py` | PASS | Clean. Path-based I/O, proper encoding, logged operations |
| `src/loops/phases/__init__.py` | PASS | Clean registry, proper KeyError on missing handler |
| `src/loops/phases/research.py` | PASS | Clean placeholder template, async, docstrings |
| `src/loops/phases/plan_delegate.py` | PASS | Clean placeholder template, async, docstrings |
| `src/loops/phases/delegate.py` | PASS | Clean placeholder template, async, docstrings |
| `src/loops/phases/execute.py` | PASS | Clean placeholder template, async, docstrings |
| `src/loops/phases/validate_audit.py` | PASS | Clean placeholder template, async, docstrings |
| `src/loops/phases/update_docs.py` | PASS | Clean placeholder template, async, docstrings |
| `src/loops/phases/setup_evidence.py` | PASS | Clean placeholder template, async, docstrings |
| `src/loops/guardian.py` | PASS (minor) | `Any` for dict values, log style inconsistency; otherwise solid watchdog |
| `src/loops/enforcer.py` | PASS (minor) | `Any` for dict values, log style inconsistency; otherwise solid enforcement |
| `src/loops/hash_anchor.py` | PASS | Clean. SHA-256 validation, proper IndexError/OSError handling |
| `src/loops/sub_agent.py` | PASS (minor) | `Any` usage for agent records; linear search acceptable for P5 |
| `src/loops/contract.py` | PASS | Clean. Pydantic model, proper prompt generation |
| `src/loops/verify.py` | PASS (major) | `shell=True` subprocess (M1); `Any` for result dicts; sync subprocess in non-async method |
| `src/loops/evidence.py` | PASS | Clean. Proper phase slug mapping, LQS placeholder, artifact I/O |
| `src/loops/manager.py` | PASS (minor) | `Any` for return dicts; private attribute access in `main()`; broad `except Exception` is justified (logged + state machine fail) |
| `src/loops/scheduler.py` | PASS (major) | Silent `except Exception` in trigger (M3); otherwise clean APScheduler integration |
| `src/loops/cost.py` | PASS (major) | Synchronous Redis (M2); otherwise clean pipeline-based cost recording |
| `tests/test_e2e_loop.py` | PASS | Clean. Comprehensive 10-check verification, proper cleanup, timeout handling |
| `alembic/versions/p5_extend_loop_instances.py` | PASS | Clean migration. Proper upgrade/downgrade symmetry, schema-qualified |
| `src/core/main.py` (modified) | PASS | Clean. Router inclusion at module level is acceptable for FastAPI |
| `src/memory/models.py` (modified, lines 659-693) | PASS | Clean. New columns match migration, proper `Mapped[]` types, server defaults |
| `src/discord/bot.py` (modified) | PASS | Pre-existing `# type: ignore[assignment]` at line 31 accepted per audit scope |

---

## Anti-Pattern Scan

| Pattern | Count | Locations |
|---------|-------|-----------|
| `# type: ignore` | 1 | `src/discord/bot.py:31` (pre-existing, accepted) |
| `@ts-ignore` / `@ts-expect-error` | 0 | — |
| `as any` | 0 | — |
| Bare `except:` | 0 | — |
| Empty `except:` (no body/log) | 0 | — |
| `except Exception` (broad) | 4 | `manager.py:214,227` (justified), `scheduler.py:81,149` (81 re-raises; 149 swallows — see M3) |
| `from typing import Any` | 5 | `guardian.py`, `enforcer.py`, `sub_agent.py`, `verify.py`, `manager.py` (all for `dict[str, Any]`) |
| `shell=True` | 1 | `verify.py:110` (see M1) |
| `import logging` (in loops/) | 0 | — (all use structlog) |
| Missing `structlog` import | 0 | All 19 loops files + 2 API files use `structlog.get_logger()` consistently |
| `from __future__` missing | 2 | `routes.py`, `loops/__init__.py` (see m1) |
| Commented-out code | 0 | — |
| Dead/unreachable code | 0 | — |
| Unused imports | 0 | — |

---

## Positive Observations

1. **Consistent structlog usage** — All 21 new/modified source files use `logger = structlog.get_logger()` with structured key-value logging. No stdlib `logging` leakage in the loop system.
2. **Comprehensive docstrings** — Every public class and method has a docstring with Args/Returns/Raises sections.
3. **`from __future__ import annotations`** — Used in 20 of 22 files, enabling PEP 604 union syntax and deferred evaluation.
4. **No type suppression** — Zero `# type: ignore` in new code. The one instance in `bot.py:31` is pre-existing and accepted.
5. **Proper async patterns** — All phase handlers are `async def`, `LoopManager._run_loop` properly awaits all calls, `Guardian.monitor` uses `asyncio.sleep`.
6. **Proper CancelledError handling** — All `asyncio.CancelledError` catches re-raise or are in cancel/await patterns with `pass`.
7. **HMAC timing-safe comparison** — `auth.py` uses `hmac.compare_digest` for API key verification.
8. **Clean migration** — Alembic migration has proper upgrade/downgrade symmetry with schema qualification.
9. **E2E test coverage** — `test_e2e_loop.py` has 10 verification checks, proper cleanup, and timeout handling.
10. **Phase registry pattern** — Clean `PHASE_REGISTRY` mapping with `KeyError` on missing handlers.

---

## Verdict Justification

**NEEDS REVIEW** — No critical/blocking findings. The code is production-quality for a Phase 5 scaffold with placeholder phase handlers. Three major findings (shell injection risk, sync Redis in async-capable module, silent scheduler error swallowing) should be addressed before the loop system is wired to real LLM execution in a later wave. Six minor findings are style/consistency improvements that can be batched.

---

_Audit performed by: Code Quality Auditor (independent)_
_Date: 2026-06-02_
_Scope: P5 Agent Loop batch — 23 steps, 28 files_
