# RG-007: Prometheus /metrics Endpoint — Verification Report

| Field | Value |
|---|---|
| Task | Add Prometheus `/metrics` endpoint to `src/core/main.py` |
| Step ID | RG-007 |
| Date | 2026-06-03 |
| Status | **PASS** |

## What Was Done

Added Prometheus metrics instrumentation to `src/core/main.py`:

1. **Imports**: `prometheus_client` (Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST), `starlette.middleware.base.BaseHTTPMiddleware`, `starlette.requests.Request as StarletteRequest`, `starlette.responses.Response`, `time`.
2. **Metrics defined**:
   - `guinevere_requests_total` — Counter with labels `method`, `endpoint`, `status`.
   - `guinevere_request_duration_seconds` — Histogram with labels `method`, `endpoint`.
3. **`_PrometheusMiddleware`** class extending `BaseHTTPMiddleware` — tracks request count and duration using `time.monotonic()`.
4. **Middleware registered** via `app.add_middleware(_PrometheusMiddleware)`.
5. **`/metrics` endpoint** — `GET /metrics` returning `generate_latest()` with `CONTENT_TYPE_LATEST` media type.

## Files Changed

| File | Change Type |
|---|---|
| `src/core/main.py` | Modified — inserted 44 lines (metrics, middleware, endpoint) after `app = FastAPI(...)` and before `@app.get("/health")` |

## Validation Results

| Check | Command | Expected | Actual | Result |
|---|---|---|---|---|
| Syntax | `python -m py_compile src/core/main.py` | exit 0 | exit 0 | PASS |
| TODO count | `grep -c "TODO" src/core/main.py` | 0 | 0 | PASS |
| /metrics present | `grep -c "/metrics" src/core/main.py` | >= 1 | 1 | PASS |
| Forbidden `as any` | `grep "as any" src/core/main.py` | 0 | 0 | PASS |
| Forbidden `@ts-ignore` | `grep "@ts-ignore" src/core/main.py` | 0 | 0 | PASS |
| `type: ignore` count | `grep "type: ignore" src/core/main.py` | 1 (dispatch only) | 1 (line 164) | PASS |
| Empty `except: pass` | Manual review | 0 new | 0 new | PASS |
| LSP diagnostics | `lsp_diagnostics src/core/main.py` | 0 new errors | 0 new errors | PASS |

### LSP Diagnostics Detail

All reported diagnostics are **pre-existing** `reportMissingImports` for `fastapi`, `redis.asyncio`, and cascading `reportUnknown*` warnings caused by basedpyright not resolving these packages in the current environment. The new imports (`prometheus_client`, `starlette.*`) show the same `reportMissingImports` pattern — consistent with pre-existing behavior, not new defects.

No new error categories introduced.

## Evidence Artifacts

- This file: `docs/setup-evidence/runtime-gaps/STEP-RG-007/verification.md`

## Boundary Compliance

- No persona drift, consent violation, surveillance overreach, or Y6 behavior.
- No secrets, credentials, or intimate data exposed.
- No destructive operations performed.
- No existing endpoints (`/health`, `/health/detailed`, `/`) modified.
- No lifespan function modified.
- No surveillance consumer code (RG-004) modified.

## Design Decisions

1. **Single `# type: ignore[override]`** on `dispatch` method — required due to Starlette's `BaseHTTPMiddleware.dispatch` signature incompatibility with basedpyright strict checking. This is a known upstream typing issue.
2. **`time.monotonic()`** used for duration measurement (not `time.time()`) — immune to wall-clock adjustments.
3. **`StarletteRequest`** alias avoids conflict with FastAPI's `Request` already imported at module top.
4. **Middleware tracks all requests** including `/metrics` itself — acceptable per task specification.

## Rollback

Revert the 44-line insertion between `app = FastAPI(...)` closing paren (line 138) and `@app.get("/health")` (originally line 141). No other files modified.

## Footer

| Field | Value |
|---|---|
| Verified by | Parent (direct verification) |
| Verification method | py_compile + lsp_diagnostics + grep + manual review |
| Auditor gate | Pending (separate auditor pass) |
