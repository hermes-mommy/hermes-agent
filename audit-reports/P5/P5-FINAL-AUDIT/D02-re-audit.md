# D02 — Integration Wiring Re-Audit (P5.5 Remediation)

| Field | Value |
|---|---|
| **Audit ID** | P5-FINAL-AUDIT / D02-re-audit |
| **Domain** | Integration wiring — API routes, LoopManager lifecycle, response shapes |
| **Scope** | FIX 8 (C-07/08/09): LoopManager wired to routes.py + main.py |
| **Prior Report** | `audit-reports/P5/P5-FINAL-AUDIT/D02-integration-wiring.md` |
| **Auditor** | READ-ONLY re-audit (automated) |
| **Date** | 2026-06-02 |
| **Verdict** | **NEEDS REVIEW** |

---

## 1. Per-Finding Status

| # | Original Finding | Severity | Status | Evidence |
|---|---|---|---|---|
| 3.1 | API routes are stubs — no LoopManager reference | CRITICAL | **RESOLVED** | See §2.1 |
| 3.3 | Response shape mismatch — `_list_active_loops()` expects list, gets dict | CRITICAL | **NOT RESOLVED** | See §2.2 |
| 3.8 | LoopManager disconnected from FastAPI | CRITICAL | **RESOLVED** | See §2.3 |
| 3.6 | Hardcoded `API_BASE_URL` and `GUILD_ID` | MODERATE | **NOT RESOLVED** | See §2.4 |

---

## 2. Detailed Evidence

### 2.1 [RESOLVED] API Routes Are Stubs → Real LoopManager Calls

**File:** `src/core/api/routes.py` (118 lines)

**Grep check:** `stub|sample|placeholder|TODO|FIXME` → **0 matches** in `src/core/api/`.

All four endpoints now extract LoopManager via `_get_loop_manager(request)`:

```python
# Line 36-44: Dependency extraction with 503 guard
def _get_loop_manager(request: Request):
    manager = getattr(request.app.state, "loop_manager", None)
    if manager is None:
        raise HTTPException(status_code=503, detail="Loop manager not initialized")
    return manager
```

| Endpoint | Line | LoopManager Call | Verified |
|---|---|---|---|
| `GET /api/v1/loops` | 52 | `await manager.list_loops()` | Yes |
| `POST /api/v1/loops` | 71 | `await manager.start_loop(task=..., goal=..., priority=...)` | Yes |
| `GET /api/v1/loops/{loop_id}` | 94 | `await manager.get_loop_status(loop_id)` | Yes |
| `POST /api/v1/loops/{loop_id}/cancel` | 113 | `await manager.stop_loop(loop_id)` | Yes |

Every endpoint has proper `try/except` with `logger.exception()` and `HTTPException(500)`.

**Verdict: RESOLVED.** No stub returns remain. All endpoints call real LoopManager methods.

---

### 2.2 [NOT RESOLVED] Response Shape Mismatch — `_list_active_loops()`

**Producer (API):** `src/core/api/routes.py` lines 47-59

```python
@router.get("/loops")
async def list_loops(request: Request) -> dict[str, Any]:
    manager = _get_loop_manager(request)
    loops = await manager.list_loops()
    active = sum(1 for l in loops if l.get("status") == "running")
    completed = sum(1 for l in loops if l.get("status") == "complete")
    return {"loops": loops, "active": active, "completed": completed}
```

Return type: `dict` with keys `loops`, `active`, `completed`.

**Consumer (Discord):** `src/discord/cmd_loop_stop.py` lines 353-357

```python
all_loops: list[dict[str, object]] = response.json()
return [
    loop for loop in all_loops
    if loop.get("status") in ("running", "queued")
]
```

Expects: `list[dict]` directly from `response.json()`.

**Runtime consequence:** `response.json()` returns `{"loops": [...], "active": N, "completed": N}` (a dict). Iterating over a dict yields its string keys (`"loops"`, `"active"`, `"completed"`). Calling `.get("status")` on a string raises `AttributeError`. This is caught by the outer `except Exception` handler but produces a generic error message to the user.

**LoopManager `list_loops()` return type (verified):** `src/loops/manager.py` line 142-144:

```python
async def list_loops(self) -> list[dict[str, Any]]:
    return [state.to_dict() for state in self.active_loops.values()]
```

This returns a `list[dict]` correctly. The issue is the API wraps it in an envelope dict, while the consumer expects the raw list.

**Fix required (either):**
1. Change `_list_active_loops()` to extract `response.json()["loops"]`, or
2. Change `GET /api/v1/loops` to return the list directly.

**Verdict: NOT RESOLVED.** The P5.5 fix wired LoopManager but did not address the consumer-side response shape mismatch.

---

### 2.3 [RESOLVED] LoopManager Lifecycle — Properly Connected to FastAPI

**File:** `src/core/main.py` (134 lines)

```python
# Lines 29-53: Lifespan creates LoopManager and starts guardian
@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.loops.manager import LoopManager

    loop_manager = LoopManager()                      # Line 34: instantiation
    app.state.loop_manager = loop_manager             # Line 35: app-state injection

    guardian_task = asyncio.create_task(               # Line 37-41: guardian background
        loop_manager.guardian.monitor(),
        name="guardian-monitor",
    )
    app.state.guardian_task = guardian_task

    logger.info("guinevere_starting", version="0.1.0")
    yield
    logger.info("guinevere_stopping")

    # Lines 48-53: graceful shutdown
    await loop_manager.guardian.stop()
    guardian_task.cancel()
    try:
        await guardian_task
    except asyncio.CancelledError:
        pass
```

```python
# Lines 132-134: Router inclusion
from src.core.api.routes import router
app.include_router(router)
```

**LoopManager API (verified in `src/loops/manager.py`):**

| Method | Signature | Return Type | Line |
|---|---|---|---|
| `start_loop` | `(task: str, goal: str, priority: str = "normal") -> str` | `loop_id` (UUID hex) | 50-89 |
| `stop_loop` | `(loop_id: str) -> dict[str, Any]` | state dict or error dict | 91-126 |
| `get_loop_status` | `(loop_id: str) -> dict[str, Any] \| None` | state dict or None | 128-140 |
| `list_loops` | `() -> list[dict[str, Any]]` | list of state dicts | 142-144 |

**Health check integration (bonus):** Lines 68-121 implement `/health/detailed` that checks `app.state.loop_manager` and `app.state.guardian_task`, providing operational visibility.

**Verdict: RESOLVED.** LoopManager is properly instantiated in lifespan, stored on app.state, guardian is started as background task, and graceful shutdown is implemented.

---

### 2.4 [NOT RESOLVED] Hardcoded Values

**`API_BASE_URL` — still hardcoded:**

| File | Line | Value |
|---|---|---|
| `src/discord/cmd_loop_start.py` | 48 | `API_BASE_URL: Final[str] = "http://localhost:8000"` |
| `src/discord/cmd_loop_stop.py` | 48 | `API_BASE_URL: Final[str] = "http://localhost:8000"` |

**`GUILD_ID` — still hardcoded in multiple files:**

| File | Line | Value |
|---|---|---|
| `src/discord/bot.py` | 37 | `GUILD_ID: int = 1_510_876_414_671_323_206` |
| `src/discord/commands.py` | 15 | `GUILD_ID = 1_510_876_414_671_323_206` |
| `src/discord/guild_setup.py` | 22 | `GUILD_ID = 1510876414671323206` |

**Impact:** Deployment to VPS or staging will fail — `localhost:8000` is unreachable from a separate bot host, and the guild ID prevents multi-guild testing.

**Recommended fix:**
- `API_BASE_URL` → `os.environ.get("GUINEVERE_API_URL", "http://localhost:8000")`
- `GUILD_ID` → `int(os.environ.get("DISCORD_GUILD_ID", "1510876414671323206"))`

**Verdict: NOT RESOLVED.** These were MODERATE findings and may have been intentionally deferred, but they remain open.

---

## 3. New Findings

### 3.1 [LOW] `cancel_loop` Returns 200 for Unknown Loops

**File:** `src/core/api/routes.py` lines 104-118

When `manager.stop_loop(loop_id)` is called with an unknown loop ID, `LoopManager.stop_loop()` (manager.py line 102-103) returns:

```python
return {"error": f"Loop {loop_id} not found."}
```

The route passes this through as a 200 OK response with `{"error": "..."}`. It should return 404 instead. Compare with `get_loop` (line 98-99) which correctly checks for `None` and returns 404.

**Suggested fix:**
```python
if "error" in result:
    raise HTTPException(status_code=404, detail=result["error"])
```

### 3.2 [LOW] `LoopResponse` Still Missing `priority` Field

**File:** `src/core/api/routes.py` lines 26-34

`LoopResponse` model does not include `priority`. The Discord `loop_start_callback` extracts `result.get("priority", "normal")` which always returns the default. This was original finding 4.3 and remains unaddressed.

**Impact:** Informational only — priority is always reported as "normal" in Discord responses.

### 3.3 [INFO] `get_loop` Returns Raw `to_dict()` — Field Count Mismatch with `LoopResponse`

**File:** `src/core/api/routes.py` line 101

```python
return status  # type: dict[str, Any] from LoopStateMachine.to_dict()
```

`to_dict()` returns 10 fields (`loop_id`, `task`, `goal`, `current_phase`, `current_phase_name`, `status`, `artifacts`, `created_at`, `error_count`, `retry_count`), while `LoopResponse` defines only 5 fields. This is acceptable since `get_loop` returns `dict[str, Any]`, but clients expecting a consistent shape across endpoints may be confused.

---

## 4. Summary

### Original Findings Resolution

| # | Finding | Severity | Status |
|---|---|---|---|
| 3.1 | API routes are stubs | CRITICAL | **RESOLVED** |
| 3.3 | Response shape mismatch (`_list_active_loops`) | CRITICAL | **NOT RESOLVED** |
| 3.8 | LoopManager disconnected | CRITICAL | **RESOLVED** |
| 3.6 | Hardcoded URLs/GUILD_ID | MODERATE | **NOT RESOLVED** |

### New Findings

| # | Finding | Severity |
|---|---|---|
| 3.1-new | `cancel_loop` returns 200 for unknown loops | LOW |
| 3.2-new | `LoopResponse` missing `priority` field | LOW |
| 3.3-new | `get_loop` returns richer dict than `LoopResponse` | INFO |

### Verdict: **NEEDS REVIEW**

Two of four original findings are resolved. The two CRITICAL LoopManager wiring fixes (stubs + lifecycle) are fully addressed. However:

1. **CRITICAL: Response shape mismatch** between `GET /api/v1/loops` and `_list_active_loops()` in `cmd_loop_stop.py` will cause a runtime `AttributeError`. This was explicitly called out in the original audit (finding 3.3, fix #2) and remains unaddressed.
2. **MODERATE: Hardcoded values** persist across 5 files. Likely deferred but should be tracked.

**Blocking issue:** Finding 2.2 (response shape mismatch) is a runtime crash that will manifest the first time a user runs `/loop-stop` without a loop_id. This should be fixed before the integration wiring can be considered complete.

---

## 5. Boundary Compliance

| Boundary | Status |
|---|---|
| No secrets hardcoded | PASS |
| No type suppression (`as any`, `@ts-ignore`, `# type: ignore`) | PASS |
| No empty catch blocks | PASS — all exceptions logged with `logger.exception()` |
| No stub/placeholder returns in routes | PASS — grep confirmed 0 matches |
| Consent/safety boundary | N/A |

---

*Re-audit complete. Report generated by READ-ONLY D02 re-auditor.*
