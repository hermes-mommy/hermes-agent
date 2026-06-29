# W4 Auditor Gate -- M15 HTTP Server (Round 1)

Auditor: independent
Commit: 4714a49
Branch: feat/p24-hermes-fork
Date: 2026-06-29

---

## Check Results

| # | Claim | Verdict | Evidence |
|---|-------|---------|----------|
| 1 | `app` is FastAPI | PASS | `type(app).__name__` = `FastAPI` |
| 2 | `/health` returns 200 | PASS | `status_code=200`, body `{"status":"healthy","service":"guinevere-core","version":"0.2.0"}` |
| 3 | `/metrics` and `/` return 200 | PASS | `metrics 200 root 200` |
| 4 | 14 tests pass | PASS | `14 passed, 1 warning in 3.59s` (StarletteDeprecationWarning only) |
| 5 | Forbidden patterns = 0 | PASS | `grep` exit code 1 (0 matches for HARD_STOP/hard_stop/consent_gate/safe_mode/type: ignore/as any/bare except) |
| 6 | Lifespan structure | PASS (w/ F01) | TaskGroup is real code (`asyncio.TaskGroup()` + `create_task`), config load fail-soft (`try/except` at L64-72), two-phase shutdown (`Event.set()` + task.cancel()). See F01 for 30s timeout gap. |
| 7 | GUINEVERE_API_KEY is env ref | PASS | `auth.py:28`: `os.environ.get("GUINEVERE_API_KEY")` -- not hardcoded. |
| 8 | `/health/ready` fail-soft | PASS | `health.py:97-109`: PG/Redis missing returns `"not_configured"`, connection failure returns `"unavailable"`, overall `"degraded"` -- no hard crash. |
| 9 | Stripped patterns = 0 | PASS | `grep` exit code 1 (0 matches for HardStopHandler/consent_session/consent_checker/P22ConsentChecker) |
| 10 | Cross-package imports | PASS | `import guinevere.http, guinevere.surveillance, guinevere.observability` -- `all import OK` |

---

## Adversarial Analysis

**W4 fix (test patch target):** Confirmed correct. `server.py:65` does `from guinevere.config import load_settings` inside the lifespan `try` block. Test fixture patches `guinevere.config.load_settings` (the module-level attribute), which is the correct target. Verified `guinevere.config.load_settings` resolves to a real function. Tests do NOT trivially assert True -- they exercise real endpoint responses, status codes, body structure, fail-soft degradation, and singleton behavior.

**TaskGroup placeholder:** REAL code, not a comment. `server.py:112` uses `asyncio.TaskGroup()`, L116/L123 use `tg.create_task(_noop_placeholder())`. The `_noop_placeholder` coroutine (L39-49) blocks on `asyncio.Event().wait()` until cancelled -- correct placeholder behavior.

**Bare except / swallowed errors:** Zero `except:` (bare) found. All exception handlers use `except Exception:` with `exc_info=True` logging. Phase 6 cleanup uses `contextlib.suppress(Exception)` for PG/Redis close -- acceptable for best-effort teardown.

**Test quality:** 14 tests across 7 test classes covering: liveness (2), readiness (2), agent state (1), metrics (2), root (1), rate limiter (3), app import (3). Tests use real fixtures with `server_mod._app = None` reset to force fresh app per test. The `client_no_config` fixture correctly verifies fail-soft: `RuntimeError` raised from config load produces degraded readiness (200), not hard crash.

---

## Findings

| ID | Severity | Description | Location | Fix |
|----|----------|-------------|----------|-----|
| F01 | LOW | Docstring promises "30s graceful drain" but implementation cancels tasks immediately after `_shutdown_event.set()` with no wait/timeout. The Event is set but no task awaits it (noop placeholders use their own internal Event). | `server.py:9-10` (docstring) vs `server.py:133-142` (impl) | Add `await asyncio.wait_for(_shutdown_event.wait(), timeout=30)` or replace the cancel-then-wait with a timed drain before cancellation. For now, placeholder tasks exit instantly on cancel so this is cosmetic. |
| F02 | LOW | `build_readiness` return type annotation is `dict[str, Any]` but actually returns `tuple[dict, int]`. Caller (`routes.py:48`) correctly destructures `(body, status_code)`. | `health.py:69` | Change annotation to `-> tuple[dict[str, Any], int]`. |

---

## Verdict

**PASS**

- 10/10 checks pass.
- 2 LOW findings (0 CRITICAL, 0 HIGH, 0 MEDIUM).
- W4 fix (patch target) is correct and tests are meaningful.
- TaskGroup placeholder is real code, not a comment.
- No bare excepts, no swallowed errors.
- All 8 files exist: `guinevere/http/{__init__,server,routes,health,auth,rate_limit,middleware}.py` + `tests/p24/test_http.py`.
- 14 tests pass, 0 errors.
