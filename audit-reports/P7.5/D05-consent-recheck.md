# D05 Consent Gate — P7.5 Re-check Report

| Field | Value |
|---|---|
| **Original Finding** | C4 (CRITICAL) |
| **Original Issue** | `invalidate_cache()` has ZERO production callers — consent withdrawal delayed up to 300s (TTL stale window). The pause command only sets `_paused=True` but doesn't invalidate the Redis consent cache. |
| **Re-check Date** | 2026-06-03 |
| **Auditor** | Guinevere re-auditor (automated) |
| **Status** | **PASS** |

---

## 1. Source File: `src/discord/cmd_surveillance_pause.py`

### 1.1 `invalidate_cache` Import

- **Lines 116–119**: `invalidate_cache` and `VALID_SURVEILLANCE_SCOPES` are imported from `src.surveillance.consent_gate` inside the callback function (lazy import).
- **Verdict**: PASS — correctly imported.

```python
# Lines 116-119
from src.surveillance.consent_gate import (
    VALID_SURVEILLANCE_SCOPES,
    invalidate_cache,
)
```

### 1.2 All 4 Scopes Invalidated

- **Lines 121–124**: `asyncio.gather` with a generator expression iterates over `VALID_SURVEILLANCE_SCOPES`, calling `invalidate_cache(scope)` for each scope.
- **Verdict**: PASS — all 4 scopes covered dynamically via the frozenset.

```python
# Lines 121-124
await asyncio.gather(
    *(invalidate_cache(scope) for scope in VALID_SURVEILLANCE_SCOPES),
    return_exceptions=True,
)
```

### 1.3 Concurrent Invalidation via `asyncio.gather`

- **Line 121**: Uses `asyncio.gather` — all 4 scopes invalidated concurrently.
- **Line 123**: `return_exceptions=True` — individual scope failures are returned as exception objects, not raised. This prevents one failing scope from cancelling others.
- **Verdict**: PASS — concurrent invalidation with per-scope fault isolation.

### 1.4 Best-Effort Error Handling (Never Blocks Pause)

- **Lines 113–126**: Entire invalidation block wrapped in `try/except Exception`.
- **Line 126**: Exception logged via `logger.exception("surveillance_pause_cache_invalidation_failed")`.
- **Ordering**: Cache invalidation (lines 112–126) occurs AFTER `_paused = True` (line 110). Pause flag is always set regardless of cache invalidation outcome.
- **Verdict**: PASS — best-effort, non-blocking, never prevents pause from completing.

### 1.5 Execution Order

| Step | Line | Action |
|------|------|--------|
| 1 | 91–99 | Faiz-only guard |
| 2 | 102–106 | Ephemeral defer |
| 3 | 109–110 | `_paused = True` |
| 4 | 112–126 | Cache invalidation (best-effort) |
| 5 | 128–133 | Audit log |
| 6 | 135–172 | Embed response |

- **Verdict**: PASS — pause flag set before cache invalidation, ensuring pause is effective even if invalidation fails.

---

## 2. Source File: `src/surveillance/consent_gate.py`

### 2.1 `invalidate_cache` Function Signature

- **Line 292**: `async def invalidate_cache(scope: str) -> None:`
- **Lines 301–307**: Implementation deletes the Redis key `{CACHE_KEY_PREFIX}{scope}` and logs the result. Internal errors are caught and logged (line 306–307).
- **Verdict**: PASS — correct async signature with `str` parameter.

### 2.2 `VALID_SURVEILLANCE_SCOPES` Frozenset

- **Lines 49–54**: `frozenset` with exactly 4 entries:
  1. `surveillance.app_usage`
  2. `surveillance.location`
  3. `surveillance.notifications`
  4. `surveillance.clipboard`
- **Verdict**: PASS — 4 entries confirmed.

### 2.3 No Modification to consent_gate.py

- The `invalidate_cache` function (lines 292–307) and `VALID_SURVEILLANCE_SCOPES` (lines 49–54) are original implementations.
- The fix was applied in the **caller** (`cmd_surveillance_pause.py`), not in `consent_gate.py` itself.
- **Verdict**: PASS — consent_gate.py was not modified for this fix.

---

## 3. Test File: `tests/surveillance/test_discord_commands.py`

### 3.1 Test: All 4 Scopes Invalidated

- **Lines 687–711**: `test_pause_invalidates_consent_cache_for_all_scopes`
  - Patches `src.surveillance.consent_gate.invalidate_cache` with `AsyncMock`.
  - Calls `surveillance_pause_callback`.
  - Collects all `call.args[0]` values into `called_scopes`.
  - Asserts `called_scopes == expected_scopes` where expected = all 4 surveillance scopes.
- **Verdict**: PASS — test covers all 4 scopes.

### 3.2 Test: Pause Succeeds When Invalidation Fails

- **Lines 714–732**: `test_pause_succeeds_when_cache_invalidation_fails`
  - Patches `invalidate_cache` with `AsyncMock(side_effect=RuntimeError("Redis down"))`.
  - Calls `surveillance_pause_callback`.
  - Asserts `is_paused_pause() is True` (flag set despite failure).
  - Asserts `followup.send.assert_awaited_once()` (embed still sent).
- **Verdict**: PASS — test verifies best-effort behavior.

### 3.3 Test Section Header

- **Line 682**: `# Pause cache invalidation tests (C4)` — explicitly tagged to original finding C4.
- **Verdict**: PASS — traceable to original finding.

---

## 4. Summary of Checks

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| `invalidate_cache` imported in pause command | Yes | Lines 116–119 | PASS |
| All 4 scopes invalidated | `app_usage`, `location`, `notifications`, `clipboard` | Via `VALID_SURVEILLANCE_SCOPES` iteration (lines 121–124) | PASS |
| Concurrent invalidation | `asyncio.gather` or similar | `asyncio.gather` with `return_exceptions=True` (line 121) | PASS |
| Wrapped in try/except | Best-effort, never blocks pause | `try/except Exception` (lines 113, 125–126) | PASS |
| `invalidate_cache` signature | `async def invalidate_cache(scope: str)` | Line 292 | PASS |
| `VALID_SURVEILLANCE_SCOPES` count | 4 entries | 4 entries (lines 49–54) | PASS |
| consent_gate.py unmodified | Fix is in caller | No changes to consent_gate.py | PASS |
| Test: all 4 scopes invalidated | Present | Lines 687–711 | PASS |
| Test: pause succeeds on invalidation failure | Present | Lines 714–732 | PASS |

---

## 5. Overall Verdict

### **PASS**

The CRITICAL finding C4 has been fully remediated:

1. **Root cause addressed**: `cmd_surveillance_pause.py` now calls `invalidate_cache()` for all 4 surveillance scopes immediately after setting `_paused = True`, eliminating the 300s TTL stale window.
2. **Concurrency**: Uses `asyncio.gather` with `return_exceptions=True` for efficient parallel invalidation with per-scope fault isolation.
3. **Resilience**: Entire invalidation block is wrapped in `try/except Exception`, ensuring pause always completes even if Redis is unavailable.
4. **Test coverage**: Two dedicated tests verify both the happy path (all 4 scopes invalidated) and the failure path (pause succeeds despite invalidation errors).
5. **Correct separation of concerns**: The fix is in the caller (`cmd_surveillance_pause.py`), not in `consent_gate.py` — the `invalidate_cache` function was already correct; it just had no production callers.

---

*Report generated 2026-06-03. Read-only audit — no source files modified.*
