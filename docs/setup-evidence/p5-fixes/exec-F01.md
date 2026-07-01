# exec-F01.md — Fix F-01: LoopManager Direct Instantiation

**Bug ID:** F-01  
**Status:** FIXED  
**Date:** 2026-06-09  
**Files modified:** 11 (10 callers + 1 routes file)

---

## Deskripsi Bug

10 file memanggil `LoopManager()` secara langsung, membuat instance baru yang terpisah dari shared instance yang di-manage oleh FastAPI app state. Karena `LoopManager.__init__` membuat dict `active_loops` baru setiap kali, semua command Discord dan Hermes yang menggunakan pattern ini tidak bisa melihat loop yang sedang berjalan.

### Pattern bermasalah (sebelum fix):
```python
from src.loops.manager import LoopManager
manager = LoopManager()  # ← instance baru, bukan shared instance
state = manager.active_loops.get(loop_id)  # ← selalu None
```

### Correct pattern (setelah fix, mengikuti cmd_loop_start.py):
```python
import httpx, os
async with httpx.AsyncClient() as client:
    response = await client.post(
        f"http://localhost:8000/api/v1/loops/{loop_id}/pause",
        headers={"X-Guinevere-API-Key": os.environ.get("GUINEVERE_API_KEY", "")},
        timeout=10.0,
    )
    response.raise_for_status()
    result = response.json()
```

---

## API Endpoints yang Ditambahkan ke routes.py

Routes sebelumnya (4 endpoints):
- `GET  /api/v1/loops`
- `POST /api/v1/loops`
- `GET  /api/v1/loops/{loop_id}`
- `POST /api/v1/loops/{loop_id}/cancel`

Routes baru yang ditambahkan (4 endpoints):
- `POST /api/v1/loops/{loop_id}/pause` — pause running loop
- `POST /api/v1/loops/{loop_id}/resume` — resume paused loop (validates PAUSED status, returns 400 if not paused)
- `POST /api/v1/loops/{loop_id}/priority` — update loop priority (validates low/normal/high/critical)
- `GET  /api/v1/loops/{loop_id}/evidence` — fetch evidence artifacts (metadata only, no raw surveillance data)

---

## Files Modified

### src/core/api/routes.py
Added 4 new endpoints + `PriorityUpdateRequest` Pydantic model. All new endpoints use `_get_loop_manager(request)` to access the shared instance from `app.state.loop_manager`.

### src/discord/cmd_loops.py
Replaced `LoopManager().list_loops()` with `GET /api/v1/loops`.

### src/discord/cmd_loop_pause.py
Replaced `LoopManager().active_loops.get(loop_id)` + `state.pause()` with `POST /api/v1/loops/{loop_id}/pause`.

### src/discord/cmd_loop_resume.py
Replaced `LoopManager().active_loops.get(loop_id)` + `state.resume()` + `LoopStatus` check with `POST /api/v1/loops/{loop_id}/resume`. 400 response from API maps to "Loop Not Paused" embed.

### src/discord/cmd_loop_priority.py
Replaced `LoopManager().active_loops.get(loop_id)` + `state.priority = priority` with `POST /api/v1/loops/{loop_id}/priority`.

### src/discord/cmd_evidence.py
Replaced `LoopManager().active_loops.get(loop_id)` + `manager.evidence_pipelines.get(loop_id)` with `GET /api/v1/loops/{loop_id}/evidence`.

### src/hermes_plugins/commands_loop/loops.py
Same as cmd_loops.py — `GET /api/v1/loops`.

### src/hermes_plugins/commands_loop/loop_pause.py
Same as cmd_loop_pause.py — `POST /api/v1/loops/{loop_id}/pause`.

### src/hermes_plugins/commands_loop/loop_resume.py
Same as cmd_loop_resume.py — `POST /api/v1/loops/{loop_id}/resume`.

### src/hermes_plugins/commands_loop/loop_priority.py
Same as cmd_loop_priority.py — `POST /api/v1/loops/{loop_id}/priority`.

### src/hermes_plugins/commands_loop/evidence.py
Same as cmd_evidence.py — `GET /api/v1/loops/{loop_id}/evidence`.

---

## Verification

```
$ python3 -c "from src.discord.cmd_loops import loops_callback; print('OK')"
cmd_loops OK
$ python3 -c "from src.discord.cmd_loop_pause import loop_pause_callback; print('OK')"
cmd_loop_pause OK
$ python3 -c "from src.discord.cmd_loop_resume import loop_resume_callback; print('OK')"
cmd_loop_resume OK
$ python3 -c "from src.discord.cmd_loop_priority import loop_priority_callback; print('OK')"
cmd_loop_priority OK
$ python3 -c "from src.discord.cmd_evidence import evidence_callback; print('OK')"
cmd_evidence OK
$ python3 -c "from src.hermes_plugins.commands_loop.loops import register; print('OK')"
hermes_loops OK
$ python3 -c "from src.hermes_plugins.commands_loop.loop_pause import register; print('OK')"
hermes_loop_pause OK
$ python3 -c "from src.hermes_plugins.commands_loop.loop_resume import register; print('OK')"
hermes_loop_resume OK
$ python3 -c "from src.hermes_plugins.commands_loop.loop_priority import register; print('OK')"
hermes_loop_priority OK
$ python3 -c "from src.hermes_plugins.commands_loop.evidence import register; print('OK')"
hermes_evidence OK
```

Routes confirmed:
```
GET  /api/v1/loops
POST /api/v1/loops
GET  /api/v1/loops/{loop_id}
POST /api/v1/loops/{loop_id}/cancel
POST /api/v1/loops/{loop_id}/pause   ← NEW
POST /api/v1/loops/{loop_id}/resume  ← NEW
POST /api/v1/loops/{loop_id}/priority ← NEW
GET  /api/v1/loops/{loop_id}/evidence ← NEW
```

No remaining `LoopManager()` instantiations in any of the 10 patched files (grep output shows only docstring references).

---

## Error Handling

All converted files now handle three httpx exception classes consistently:
- `httpx.HTTPStatusError` — API returned non-2xx (logged + user-friendly message with status code)
- `httpx.RequestError` — network/connection failure (logged + user-friendly "API unreachable" message)
- `Exception` — unexpected errors (logged + generic unavailable message)

The evidence endpoint GET does not require `GUINEVERE_API_KEY` (same as `GET /api/v1/loops`). The mutation endpoints (pause, resume, priority) require the key via `X-Guinevere-API-Key` header.
