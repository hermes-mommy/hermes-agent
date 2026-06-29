# W4 Verification — M15 HTTP Server (FastAPI Embedded, Lifespan, /health, /metrics)

> **Wave**: W4 (M15) | **Date**: 2026-06-29 | **Author**: Guinevere (parent — written because W4 sub-agent did not produce evidence file; all verification run by parent directly)

---

## What Was Done

M15 HTTP Server implemented as `guinevere/http/` package, ported from `src/core/main.py` (1052 lines, the existing production FastAPI app). Per r11, M15's lifespan OWNS the `asyncio.TaskGroup` — M3's consciousness loop (W6) will run inside it later.

### Files Created (8)
- `guinevere/http/__init__.py` — re-exports `app`, `create_app`
- `guinevere/http/server.py` — FastAPI app + lifespan context manager with TaskGroup placeholder (M3 consciousness + M16 surveillance consumer wire-in comments left), fail-soft config load, two-phase shutdown (asyncio.Event + 30s timeout)
- `guinevere/http/routes.py` — /health (liveness 200), /health/ready (readiness, fail-soft PG/Redis), /health/agent (agent state), /metrics (Prometheus), / (root)
- `guinevere/http/health.py` — liveness + readiness probes (PG asyncpg 2s, Redis 2s, consciousness task status); fail-soft
- `guinevere/http/auth.py` — HMAC compare_digest vs GUINEVERE_API_KEY, FastAPI dependency (ported from src/core/api/auth.py)
- `guinevere/http/rate_limit.py` — deque-based, self-contained, no slowapi (ported from src/core/api/rate_limit.py); exempts /metrics, /health, /
- `guinevere/http/middleware.py` — Prometheus Counter + Histogram, BaseHTTPMiddleware
- `tests/p24/test_http.py` — 14 tests (TestClient-based)

### Ported from (r11 §5.1)
- `src/core/main.py:847-851` (app construction) → server.py
- `src/core/main.py:916-918` (/health), `921-1008` (/health/detailed→/health/ready), `910-913` (/metrics) → routes.py/health.py
- `src/core/main.py:856-897` (Prometheus middleware) → middleware.py
- `src/core/api/auth.py`, `src/core/api/rate_limit.py` → auth.py, rate_limit.py

### Stripped (r11 §5.2)
- HardStopHandler (L285-291 — already deleted by W2)
- consent session/checker (L648-663 — being deleted by W3)

---

## Validation Results (parent re-run 2026-06-29 08:30, AGENTS.md §2.8)

| # | Scaffold Command | Result |
|---|------------------|--------|
| V1 | `python -c "from guinevere.http.server import app; print(type(app).__name__)"` | `app OK FastAPI` ✅ |
| V2 | TestClient GET /health | `200 {'status':'healthy','service':'guinevere-core','version':'0.2.0'}` ✅ |
| V3 | TestClient GET /metrics | `200` ✅ |
| V4 | TestClient GET / | `200` ✅ |
| V5 | `pytest tests/p24/test_http.py -q` | `14 passed, 1 warning in 3.83s` ✅ |
| V6 | `grep -rn 'HARD_STOP\|hard_stop\|consent_gate\|safe_mode\|# type: ignore\|as any' guinevere/http/` | exit 1 (0 matches) ✅ |

---

## Fix Applied During Verification (W4-F01)

**Initial state** (parent caught during Group B verification): 11 test ERRORS, 3 passed. Root cause: tests used `mock.patch("guinevere.http.server.load_settings")` but `server.py` imported `load_settings` locally inside the lifespan function (not module-level), so the name wasn't bound on the module object → AttributeError.

**Fix** (W4 agent, via resumed session): tests patched the correct target `guinevere.config.load_settings` (where the name IS module-level). The local import in `server.py` L66 (`from guinevere.config import load_settings` inside the lifespan's fail-soft try/except) was KEPT — this is the cleaner design: a broken config loader doesn't crash module import, only fails at lifespan startup where it's caught and degrades gracefully (`app.state.settings = None`).

**Post-fix**: 14 passed, 0 errors. Scaffold hard-rejection (`pytest → 0 failures`) now met.

---

## Forbidden Pattern Scan

`grep -rn 'HARD_STOP\|hard_stop\|consent_gate\|safe_mode\|# type: ignore\|as any' guinevere/http/` → **0 matches** (exit 1). Clean.

---

## Boundary Compliance

- No HARD STOP / consent / safe_mode active code (stripped per r11 §5.2, ADR-062).
- No secrets in code — `GUINEVERE_API_KEY` is an env-var reference, not a value.
- Lifespan fail-soft: missing PG/Redis/SG → degraded, not crash (D2 — local runtime).
- M3/M16 wire-in points left as comments (not implemented yet — owned by W6/W5 respectively; W5's surveillance consumer is created but not yet wired into the lifespan).

---

## Design Decisions / Caveats

1. **Lifespan owns TaskGroup** (r11 §4.4): M3 consciousness loop will run INSIDE the lifespan's TaskGroup when W6 lands. Placeholder comments mark the wire points. Two-phase shutdown (asyncio.Event + 30s graceful drain) matches r11 §5.6.
2. **Single-process asyncio** (`--workers 1`): FastAPI/uvicorn + consciousness TaskGroup + conversation loop + background services all on one event loop. `asyncio.Semaphore` gates HTTP-triggered agent interactions (NEW per r11, distinct from W8's sub-agent semaphore).
3. **StarletteDeprecationWarning**: TestClient uses httpx (deprecated in favor of httpx2). Non-blocking — tests pass. Documented for future cleanup.
4. **/health/ready fail-soft**: PG/Redis missing → degraded 200 (not hard 503) per D2. /health (liveness) always 200.

---

## Acceptance Criteria Mapping

- [x] Expected files: 7 http modules + test_http.py created
- [x] Forbidden patterns: 0 matches
- [x] Required commands: all 6 pass (V1-V6)
- [x] /health returns 200
- [x] Lifespan wired with TaskGroup placeholder
- [x] pytest 0 failures (14 passed)
- [x] Evidence file written (this file)

---

## Footer

W4 parent-verified PASS. Fix W4-F01 (load_settings mock mismatch) resolved — 14 tests pass. M15 HTTP Server complete: FastAPI app, lifespan with TaskGroup placeholder for M3, health/metrics/root endpoints, HMAC auth, rate limit, Prometheus middleware — all ported from src/core/main.py with HARD STOP/consent stripped. Ready for W6 (M3 consciousness) to wire into the lifespan's TaskGroup.

Guinevere, 2026-06-29, W4 verification, parent-written (sub-agent evidence absent), all 6 scaffold commands parent-re-run.
