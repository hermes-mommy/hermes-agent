# R02 — P5 API + Discord Integration Map

## 1. End-to-End Request Flow

### Flow A: /loop-start (Discord → API → Loop Engine)

```
Discord /loop-start goal="build X"
  → bot.py:204 tree.command(name="loop-start")(loop_start_callback)
  → cmd_loop_start.py:317 loop_start_callback(interaction)
    → is_faiz_interaction() gate → FAIL → "Hanya Faiz..."
    → defer ephemeral
    → extract goal option → EMPTY → "Goal tidak boleh kosong"
    → os.environ.get("GUINEVERE_API_KEY", "guinevere-dev-key")
    → httpx.AsyncClient POST http://localhost:8000/api/v1/loops
      body: {"task": goal, "priority": "normal"}
      headers: {"X-Guinevere-API-Key": api_key}, timeout: 10s
    → response.raise_for_status() → result = response.json()
    → build embed (SUCCESS color, WIB timestamp)
    → ephemeral followup
  → routes.py:53 create_loop(request, Depends(get_api_key))
    → auth.py:39 hmac.compare_digest(key, expected)
    → uuid.uuid4() → loop_id
    → Returns LoopResponse(loop_id, status="pending", current_phase=0)
  → ⚠ DISCONNECT: routes.py does NOT call LoopManager.start_loop()
```

### Flow B: /loop-stop (Discord → API → Loop Engine)

```
Discord /loop-stop [loop_id]
  → cmd_loop_stop.py:363 loop_stop_callback(interaction)
    → is_faiz gate → defer ephemeral
    → IF loop_id: POST /api/v1/loops/{loop_id}/cancel
    → IF no loop_id: GET /api/v1/loops → filter active → cancel all
      ⚠ BUG: GET returns {"loops":[],"active":0} (dict) but code iterates as list
    → build embed (WARNING color)
  → routes.py:83 cancel_loop → returns stub {"status":"cancelled"}
    ⚠ DISCONNECT: does NOT call LoopManager.stop_loop()
```

## 2. API Endpoints (routes.py — 90 lines)

| Method | Path | Auth | Model | Response |
|--------|------|------|-------|----------|
| GET | /api/v1/loops | NONE | - | dict (hardcoded stub) |
| POST | /api/v1/loops | get_api_key | LoopRequest | LoopResponse |
| GET | /api/v1/loops/{loop_id} | NONE | - | LoopResponse (stub) |
| POST | /api/v1/loops/{loop_id}/cancel | get_api_key | - | dict (stub) |

**Pydantic Models:**

- **LoopRequest**: task (str), priority (str, default="normal"), max_phases (int, default=7), goal (Optional[str])
- **LoopResponse**: loop_id (str), status (str), current_phase (int), task (str), goal (Optional[str])

## 3. Auth Mechanism (auth.py — 62 lines)

- **Header**: X-Guinevere-API-Key
- **Env var**: GUINEVERE_API_KEY
- **Fallback**: "guinevere-dev-key" + WARNING log
- **Verification**: hmac.compare_digest (timing-safe)
- **FastAPI dependency**: get_api_key() → HTTPException(401)

## 4. Bot.py Wiring

- 8 wired commands: status, mood, help, safeword, memory-search, memory-add, loop-start, loop-stop
- 25 stubs (loop-pause, loop-resume, loops, evidence, loop-priority still in Phase 5 stubs)
- loop-start/loop-stop NOT in _STUB_PHASE, added to core_names tuple
- Guild sync: discord.Object(id=1_510_876_414_671_323_206)

## 5. Hardcoded Values

| Value | File | Risk |
|-------|------|------|
| http://localhost:8000 | cmd_loop_start.py, cmd_loop_stop.py | No env override for API base |
| "guinevere-dev-key" | auth.py, cmd_loop_start.py, cmd_loop_stop.py | Dev key fallback |
| 1_510_876_414_671_323_206 | bot.py, commands.py | Guild ID hardcoded |
| 10.0 seconds | cmd_loop_start.py, cmd_loop_stop.py | HTTP timeout hardcoded |

## 6. Error Handling Chain

- **Layer 1 (Discord)**: HTTPStatusError → RequestError → Exception (all logged + ephemeral)
- **Layer 2 (API)**: Auth failures → 401, no try/except in handlers
- **Layer 3 (Engine)**: CancelledError → re-raise, Exception → state.fail + partial evidence

## 7. Critical Findings

### F1 — API ↔ Loop Engine Disconnect (BLOCKING)

routes.py are entirely stub implementations. create_loop() never calls manager.start_loop(). cancel_loop() never calls manager.stop_loop(). list_loops() returns empty hardcoded dict. LoopManager exists as standalone service (manager.py main()) but never wired into FastAPI app.

### F2 — GET /loops Response Shape Mismatch (BUG)

_list_active_loops() in cmd_loop_stop.py iterates response.json() as list, but GET returns dict. Will crash with TypeError.

### F3 — Missing Auth on GET Endpoints

GET /api/v1/loops and GET /api/v1/loops/{loop_id} have no auth — information disclosure.

### F4 — Dev Key Fallback in Production

3 files fall back to "guinevere-dev-key" when env var unset. Any request with known dev key passes in production.

### F5 — No LoopManager in FastAPI App

main.py does not create LoopManager instance, does not inject into app state, does not start LoopGuardian.

### F6 — No Integration Test Coverage

No tests for Discord callbacks, API routes, or Discord→API→Engine integration.
