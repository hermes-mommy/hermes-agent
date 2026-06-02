# D02 — Integration Wiring Audit (API ↔ Engine ↔ Discord)

| Field | Value |
|---|---|
| **Audit ID** | P5-FINAL-AUDIT / D02 |
| **Domain** | Integration wiring — API routes, Discord commands, LoopManager lifecycle |
| **Auditor** | Independent (automated) |
| **Date** | 2026-06-02 |
| **Verdict** | **NEEDS REVIEW** |

---

## 1. Files Reviewed

| File | Lines | Role |
|---|---|---|
| `src/core/api/routes.py` | 90 | FastAPI route definitions for loop management |
| `src/core/api/auth.py` | 62 | API key authentication (header-based) |
| `src/core/main.py` | 57 | FastAPI app bootstrap and router inclusion |
| `src/discord/cmd_loop_start.py` | 453 | `/loop-start` Discord slash command |
| `src/discord/cmd_loop_stop.py` | 522 | `/loop-stop` Discord slash command |
| `src/discord/bot.py` | 348 | Bot class, command registration, lifecycle |
| `src/loops/manager.py` | 272 | LoopManager — SDLC loop orchestration engine |

---

## 2. Check Results Summary

| # | Check | Verdict | Severity |
|---|---|---|---|
| 1 | API ↔ LoopManager wiring | **FAIL** | CRITICAL |
| 2 | Discord → API HTTP calls | PASS | — |
| 3 | Response shape (`_list_active_loops`) | **FAIL** | CRITICAL |
| 4 | Auth on write endpoints | PASS | — |
| 5 | Error handling completeness | PASS | — |
| 6 | Hardcoded values (env-configurable?) | **NEEDS REVIEW** | MODERATE |
| 7 | bot.py command wiring | PASS | — |
| 8 | LoopManager lifecycle | **FAIL** | CRITICAL |

---

## 3. Detailed Findings

### 3.1 [FAIL] API ↔ LoopManager — Routes Are Stubs

**File:** `src/core/api/routes.py` (all endpoints)

The API routes have **zero references** to `LoopManager`. Every endpoint returns fabricated/hardcoded data:

| Endpoint | Expected Behavior | Actual Behavior |
|---|---|---|
| `GET /api/v1/loops` | Call `manager.list_loops()` | Returns `{"loops": [], "active": 0, "completed": 0}` (hardcoded empty) |
| `POST /api/v1/loops` | Call `manager.start_loop(task, goal, priority)` | Generates random UUID, returns static `LoopResponse(status="pending", current_phase=0)` |
| `GET /api/v1/loops/{loop_id}` | Call `manager.get_loop_status(loop_id)` | Returns `LoopResponse(status="unknown", task="stub")` |
| `POST /api/v1/loops/{loop_id}/cancel` | Call `manager.stop_loop(loop_id)` | Returns `{"status": "cancelled"}` without stopping anything |

**Impact:** The entire three-tier architecture (Discord → API → LoopManager) is broken at the API ↔ LoopManager boundary. Discord commands POST to the API, the API returns fake data, and no loop is ever created or cancelled.

**Root Cause:** `routes.py` does not import or instantiate `LoopManager`. No dependency injection or app-state pattern is used.

---

### 3.2 [PASS] Discord → API HTTP Calls

Both Discord commands correctly call the API:

**`cmd_loop_start.py` (line 345-353):**
- `POST {API_BASE_URL}/api/v1/loops` with `json={"task": goal, "priority": "normal"}`
- Header: `X-Guinevere-API-Key` from env
- Timeout: 10.0s
- `response.raise_for_status()` called

**`cmd_loop_stop.py`:**
- `_cancel_loop()` (line 328-334): `POST {base}/api/v1/loops/{loop_id}/cancel` with auth header
- `_list_active_loops()` (line 347-352): `GET {base}/api/v1/loops` with auth header

HTTP method, endpoint paths, auth headers, and timeouts are all correct.

---

### 3.3 [FAIL] Response Shape Mismatch — `_list_active_loops()`

**File:** `src/discord/cmd_loop_stop.py`, lines 347-357

`_list_active_loops()` expects the GET `/loops` response to be a **list**:

```python
all_loops: list[dict[str, object]] = response.json()  # expects list
return [
    loop for loop in all_loops
    if loop.get("status") in ("running", "queued")
]
```

But `GET /api/v1/loops` in `routes.py` (line 50) returns a **dict**:

```python
return {"loops": [], "active": 0, "completed": 0}
```

**Runtime consequence:** Iterating over a dict yields its keys (strings). Calling `.get("status")` on a string raises `AttributeError`. The `except Exception` block (line 454) would catch this, but the user gets a generic "unexpected error" message instead of a meaningful response.

**Fix required:** Either:
1. Change the API to return `list[dict]` directly, or
2. Change `_list_active_loops()` to extract `response.json()["loops"]`.

---

### 3.4 [PASS] Auth on Write Endpoints

**File:** `src/core/api/auth.py`

- `POST /api/v1/loops` — protected via `Depends(get_api_key)` (routes.py line 56) ✅
- `POST /api/v1/loops/{loop_id}/cancel` — protected via `Depends(get_api_key)` (routes.py line 85) ✅
- `GET /api/v1/loops` — no auth (routes.py line 46-50). Acceptable for internal read-only on localhost.
- `GET /api/v1/loops/{loop_id}` — no auth (routes.py line 70-80). Same rationale.

Auth mechanism uses `hmac.compare_digest` (timing-safe comparison) and reads `GUINEVERE_API_KEY` from env. Dev fallback key exists with logged warning — acceptable.

---

### 3.5 [PASS] Error Handling Completeness

Both Discord commands implement three-layer error handling:

| Layer | Exception | User Message |
|---|---|---|
| HTTP status error | `httpx.HTTPStatusError` | Reports status code |
| Network error | `httpx.RequestError` | "Cannot reach API" |
| Unexpected | `Exception` | "Unexpected error, logged for investigation" |

All three layers log via `logger.exception()` and send ephemeral followup messages. No error path is silently swallowed.

---

### 3.6 [NEEDS REVIEW] Hardcoded Values

| Value | Location | Configurable? | Issue |
|---|---|---|---|
| `API_BASE_URL = "http://localhost:8000"` | `cmd_loop_start.py:48`, `cmd_loop_stop.py:48` | **NO** — `Final` constant | Must be `os.environ.get("GUINEVERE_API_URL", ...)` for VPS deployment |
| `GUILD_ID = 1_510_876_414_671_323_206` | `bot.py:37` | **NO** — integer literal | Must be `int(os.environ.get("DISCORD_GUILD_ID", ...))` for multi-guild/staging |
| `timeout=10.0` | `cmd_loop_start.py:351`, `cmd_loop_stop.py:331` | NO | Low priority, acceptable as default |
| `_DEV_DEFAULT_KEY = "guinevere-dev-key"` | `auth.py:15` | Partially — env override exists | Logged warning on fallback. Acceptable for dev path. |
| `GUINEVERE_API_KEY` fallback | `cmd_loop_start.py:344`, `cmd_loop_stop.py:384` | YES — `os.environ.get()` with dev default | Acceptable |

**Impact:** `API_BASE_URL` hardcoded to `localhost:8000` will fail in any non-local deployment where the API and bot run on separate hosts/ports. `GUILD_ID` hardcoding prevents staging/testing on a different guild.

---

### 3.7 [PASS] bot.py Command Wiring

**File:** `src/discord/bot.py`, lines 159-232

`loop-start` and `loop-stop` are:
1. **Imported** from their dedicated modules (lines 173-174)
2. **Registered** via `self.tree.command()` with correct names and descriptions (lines 204-211)
3. **Excluded from stubs** via `core_names` tuple (lines 214-218) — stub generator skips them

The `_STUB_PHASE` dict still contains `loop-pause`, `loop-resume`, `loops`, `evidence`, `loop-priority` as Phase 5 stubs — these are separate commands and correctly remain as stubs.

---

### 3.8 [FAIL] LoopManager Lifecycle — Not Connected to API

**File:** `src/loops/manager.py` (standalone), `src/core/main.py` (no reference)

`LoopManager` is a fully-implemented service with:
- `start_loop(task, goal, priority)` → returns `loop_id`
- `stop_loop(loop_id)` → returns state dict
- `list_loops()` → returns list of state dicts
- `get_loop_status(loop_id)` → returns state dict or None
- Guardian monitoring, evidence pipeline, phase execution

However:
- `src/core/main.py` does **not** import `LoopManager`
- The FastAPI `lifespan()` function does **not** instantiate or inject a `LoopManager`
- `routes.py` has **no reference** to `LoopManager` — no app-state dependency, no singleton
- `manager.py` has its own standalone `main()` entry point (line 237) for running as an independent asyncio service

**The three-tier architecture is disconnected:**
```
Discord Bot  ──(HTTP)──>  FastAPI API  ──(NOT WIRED)──>  LoopManager
      ✅ working              ❌ stubbed                     ✅ implemented
```

**Required fix:** Instantiate `LoopManager` in FastAPI lifespan or via app-state/dependency injection, and wire route handlers to call `manager.start_loop()`, `manager.stop_loop()`, `manager.list_loops()`.

---

## 4. Additional Observations

### 4.1 Duplicate Protocol Definitions

`cmd_loop_start.py` and `cmd_loop_stop.py` each define identical copies of:
- `DiscordEmbedProtocol`
- `DiscordEmbedFactory`
- `DiscordColourFactory`
- `DiscordEmbedModule`
- `DiscordResponseProtocol`
- `DiscordFollowupProtocol`
- `DiscordInteractionProtocol`
- `_get_option_value()`
- `_send_denied()`
- `_defer_ephemeral()`
- `_followup_send()`
- `_format_wib_timestamp()`

This is ~120 lines of duplication per file. Not a wiring issue, but a maintenance risk.

### 4.2 Duplicate Constants

`API_BASE_URL`, `LOOPS_ENDPOINT`, `FOOTER_TEXT`, `FOOTER_ICON`, `WIB` are duplicated across both command files. A shared constants module would reduce drift risk.

### 4.3 LoopResponse Model Mismatch

The API's `LoopResponse` model (routes.py lines 31-38) has fields: `loop_id`, `status`, `current_phase`, `task`, `goal`. The Discord command's `loop_start_callback` (line 355-357) extracts: `loop_id` (or `id`), `status`, `priority`. The field `priority` does NOT exist on `LoopResponse`, so `result.get("priority", "normal")` always returns the default `"normal"`.

---

## 5. Verdict Summary

| Category | Verdict |
|---|---|
| Discord → API (HTTP layer) | **PASS** |
| API → LoopManager (integration) | **FAIL** |
| Response shape contract | **FAIL** |
| Auth enforcement | **PASS** |
| Error handling | **PASS** |
| Config portability | **NEEDS REVIEW** |
| Command registration | **PASS** |
| LoopManager lifecycle | **FAIL** |

### Overall Verdict: **NEEDS REVIEW**

The Discord-to-API leg is solid (correct HTTP calls, auth headers, error handling, command registration). However, the API-to-LoopManager leg is entirely missing — routes are stubs returning fabricated data, and `LoopManager` is a standalone service with no integration point. Additionally, a response shape mismatch between `GET /loops` and `_list_active_loops()` will cause a runtime `AttributeError` when the API is eventually connected.

---

## 6. Required Fixes (Priority Order)

| # | Fix | Severity | Files Affected |
|---|---|---|---|
| 1 | Wire `LoopManager` into FastAPI via lifespan/app-state and update routes to call manager methods | CRITICAL | `main.py`, `routes.py` |
| 2 | Fix response shape: align `GET /loops` return type with `_list_active_loops()` parser | CRITICAL | `routes.py` OR `cmd_loop_stop.py` |
| 3 | Make `API_BASE_URL` env-configurable (`GUINEVERE_API_URL`) | MODERATE | `cmd_loop_start.py`, `cmd_loop_stop.py` |
| 4 | Make `GUILD_ID` env-configurable (`DISCORD_GUILD_ID`) | MODERATE | `bot.py` |
| 5 | Add `priority` field to `LoopResponse` or remove from Discord parser | LOW | `routes.py`, `cmd_loop_start.py` |

---

## 7. Boundary Compliance

| Boundary | Status |
|---|---|
| No secrets hardcoded | PASS — dev key has env override + warning |
| No type suppression (`as any`, `@ts-ignore`) | PASS |
| No empty catch blocks | PASS — all exceptions logged |
| Consent/safety boundary | N/A — no persona/surveillance code in scope |

---

*Audit complete. Report generated by independent D02 auditor.*
