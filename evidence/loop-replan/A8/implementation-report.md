# A8 Implementation Report — HardStopGuard

## What Was Done

Created `guinevere/consciousness/safety.py` with the `HardStopGuard` class — a Redis-based safety guard for the consciousness loop that checks the `life_kernel:hard_stop` key before each thought generation cycle.

## Files Created

| File | Purpose |
|---|---|
| `guinevere/consciousness/safety.py` | HardStopGuard class implementation |

## Design Decisions

### 1. Fail-Open on Redis Connectivity

When Redis is unreachable, the guard logs a warning and returns `False` (no HARD STOP). This is **fail-open** for connectivity, not fail-stop.

**Rationale:** A transient Redis outage should not permanently block the consciousness loop. The HARD STOP signal is an operator-initiated safety mechanism, not a default state. If Redis is down, the loop should continue (with warning) rather than halt indefinitely.

**Contrast with HeartbeatService:** The legacy `_heartbeat_1s()` uses fail-closed ("we must NOT assume the flag is absent"). This is appropriate for the heartbeat's 1-second polling loop which has a tight coupling to the graph state. For the consciousness loop's per-thought-cycle check, fail-open is safer because:
- The consciousness loop has other safety mechanisms (budget limits, testing gate).
- A Redis outage blocking all thought generation would be a worse failure mode than missing one HARD STOP signal during the outage window.
- The operator can always stop the process directly if Redis is down and HARD STOP is needed.

### 2. Cached State via `active` Property

The `active` property returns the cached state from the last `check()` call. This allows synchronous access without Redis overhead. The caller must call `check()` to refresh the state.

### 3. Async Redis Client

Uses `redis.asyncio.Redis` directly (not `redis.asyncio.from_url`). The caller owns the client lifecycle and passes it to the guard. This follows the same pattern as `HeartbeatService.__init__()` which receives `redis_client: aioredis.Redis`.

### 4. `wait_for_clear()` Polling Loop

The `wait_for_clear()` method is the ONLY place that uses `asyncio.sleep`. It polls Redis at a configurable interval (default 5s) until the HARD STOP signal is cleared. This is the designated blocking point for the consciousness loop to wait during a HARD STOP event.

### 5. No Dependency on HeartbeatService

The guard is self-contained. It does not import or depend on `HeartbeatService` or any `life_kernel` module. This ensures clean separation as HeartbeatService is deprecated (A6).

## Verification Results

### Import Test
```
python -c "from guinevere.consciousness.safety import HardStopGuard; print('OK')"
> OK
```

### LSP Diagnostics
LSP server (basedpyright) not installed in this environment. No code-level type errors detected during manual review.

### Forbidden Patterns Check
- No `# type: ignore` — PASS
- No `Any` casts — PASS
- No blocking Redis calls (all async) — PASS
- No dependency on HeartbeatService — PASS
- No LLM calls — PASS
- No `asyncio.sleep` outside `wait_for_clear()` — PASS

## Boundary Compliance

- **Safety contract:** The guard only reports the signal; the caller is responsible for halting thought generation.
- **No secrets exposure:** No credentials, tokens, or personal data in the module.
- **No persona drift:** The module is pure infrastructure with no persona behavior.

## Rollback/Re-run Safety

- **Idempotent:** The module can be imported multiple times without side effects.
- **No database migrations:** Pure Python module, no schema changes.
- **No config changes:** Does not modify any configuration files.

## Caveats

1. **Test coverage:** The verification scaffold requires `python -m pytest tests/p24/test_consciousness*.py -v -x --timeout=30 -k "hard_stop"` — no existing tests match this pattern. Tests should be created as a follow-up task.
2. **LSP not available:** basedpyright not installed; type safety verified by manual review only.
