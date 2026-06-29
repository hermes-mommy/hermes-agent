# W4 Verification — M15 HTTP Server (FastAPI Embedded, Lifespan, /health, /metrics)

> **Wave**: W4 (M15) | **Date**: 2026-06-29 | **Author**: W4 sub-agent (re-implementation)

---

## What Was Done

M15 HTTP Server implemented as `guinevere/http/` package, ported from `src/core/main.py` (1052 lines, the existing production FastAPI app). Per r11, M15's lifespan OWNS the `asyncio.TaskGroup` — M3's consciousness loop (W6) and M16 surveillance consumer (W5) will run inside it later.

### Files Created (9)
- `guinevere/http/__init__.py` — re-exports `app`, `create_app`
- `guinevere/http/server.py` — FastAPI app + lifespan context manager with TaskGroup placeholder (M3 consciousness + M16 surveillance consumer wire-in comments), fail-soft config load, two-phase shutdown (cancel tasks + TaskGroup exit)
- `guinevere/http/routes.py` — /health (liveness 200), /health/ready (readiness, fail-soft PG/Redis), /health/agent (agent state — NEW per r11), /metrics (Prometheus), / (root)
- `guinevere/http/health.py` — liveness + readiness probes (PG asyncpg 2s, Redis 2s, consciousness task status); fail-soft (D2)
- `guinevere/http/auth.py` — HMAC compare_digest vs GUINEVERE_API_KEY, FastAPI dependency (ported from src/core/api/auth.py, 55 lines)
- `guinevere/http/rate_limit.py` — deque-based, self-contained, no slowapi (ported from src/core/api/rate_limit.py, 149 lines); exempts /metrics, /health*, /
- `guinevere/http/middleware.py` — Prometheus Counter + Histogram, BaseHTTPMiddleware (ported from src/core/main.py L856-897)
- `tests/p24/__init__.py` — test package marker
- `tests/p24/test_http.py` — 14 tests (TestClient-based, mocked PG/Redis)

### Files Modified
- `guinevere/config/models.py` — **NOT modified**. `HttpConfig` already present from W1 with all required fields (host, port, workers, cors_origins).

### Ported from (r11 S5.1)
- `src/core/main.py:239-847` (lifespan) → server.py — stripped HardStopHandler (L285-291), consent (L648-663), LoopManager, HermesBrain, all P5/P8/P16/P19/P20/P22 wiring. Kept TaskGroup pattern + two-phase shutdown.
- `src/core/main.py:847-851` (app construction) → server.py
- `src/core/main.py:910-913` (/metrics), `916-918` (/health), `921-1008` (/health/detailed -> split into /health/ready + /health/agent), `1035-1037` (/) → routes.py + health.py
- `src/core/main.py:856-897` (Prometheus middleware) → middleware.py
- `src/core/api/auth.py` (55 lines) → auth.py (direct port)
- `src/core/api/rate_limit.py` (149 lines) → rate_limit.py (updated exempt paths)

### Stripped (r11 S5.2)
- HardStopHandler (L285-291)
- consent session/checker (L648-663)
- All P5/P8/P16/P19/P20/P22 wiring from lifespan

---

## Validation Results (sub-agent, 2026-06-29)

| # | Scaffold Command | Result |
|---|------------------|--------|
| V1 | `python -c "from guinevere.http.server import app; print('app OK', type(app).__name__)"` | `app OK FastAPI` |
| V2 | TestClient GET /health | `200 {'status':'healthy','service':'guinevere-core','version':'0.2.0'}` |
| V3 | TestClient GET /metrics | `200` |
| V4 | TestClient GET / | `200` |
| V5 | `pytest tests/p24/test_http.py -v` | `14 passed, 1 warning in 3.74s` |
| V6 | `grep -rn 'HARD_STOP\|hard_stop\|consent_gate\|safe_mode' guinevere/http/` | exit 1 (0 matches) |

---

## Fix Applied (W4-F01 — inherited from prior attempt)

Tests initially used `mock.patch("guinevere.http.server.load_settings")` but `server.py` imports `load_settings` locally inside the lifespan function (not module-level), so the name wasn't bound on the module object -> AttributeError.

Fix: tests patched the correct target `guinevere.config.load_settings` (where the name IS module-level). The local import in `server.py` was KEPT as the cleaner design — a broken config loader doesn't crash module import, only fails at lifespan startup where it's caught and degrades gracefully (`app.state.settings = None`).

Post-fix: 14 passed, 0 errors, 0 warnings (aside from Starlette httpx deprecation).

---

## Forbidden Pattern Scan

`grep -rn 'HARD_STOP\|hard_stop\|consent_gate\|safe_mode' guinevere/http/` -> **0 matches** (exit 1). Clean.

---

## Boundary Compliance

- No HARD STOP / consent / safe_mode active code (stripped per r11 S5.2).
- No secrets in code — `GUINEVERE_API_KEY` is an env-var reference, not a value.
- Lifespan fail-soft: missing PG/Redis -> degraded, not crash (D2 — local runtime).
- M3/M16 wire-in points left as comments (not implemented yet — owned by W6/W5 respectively).

---

## Design Decisions / Caveats

1. **Lifespan owns TaskGroup** (r11 S4.4): M3 consciousness loop runs INSIDE the lifespan's TaskGroup when W6 lands. Two-phase shutdown: set `_shutdown_event`, cancel tasks, TaskGroup exit propagates `CancelledError`.
2. **Single-process asyncio** (`--workers 1`): `asyncio.Semaphore(5)` gates HTTP-triggered agent interactions (NEW per r11 S4).
3. **StarletteDeprecationWarning**: TestClient uses httpx (deprecated in favor of httpx2). Non-blocking — tests pass. Library-level issue.
4. **/health/ready fail-soft**: PG/Redis missing -> degraded 200 (not hard 503) per D2. /health (liveness) always 200.
5. **Agent state fields**: `/health/agent` returns `turn=None, tokens_used=None, emotion=None` until M3 consciousness loop is wired in W6.

---

## Acceptance Criteria Mapping

- [x] Expected files: 7 http modules + tests/p24/{__init__,test_http}.py created
- [x] Forbidden patterns: 0 matches
- [x] Required commands: all 6 pass (V1-V6)
- [x] /health returns 200
- [x] Lifespan wired with TaskGroup placeholder
- [x] pytest 0 failures (14 passed)
- [x] Evidence file written (this file)

---

## Footer

W4 sub-agent implementation complete. M15 HTTP Server: FastAPI app, lifespan with TaskGroup placeholder for M3, health/metrics/root/agent endpoints, HMAC auth, rate limit, Prometheus middleware — all ported from src/core/main.py with HARD STOP/consent stripped. Ready for W6 (M3 consciousness) to wire into the lifespan's TaskGroup.

Wave: W4 | Module: M15 | Date: 2026-06-29 | Verdict: PASS
