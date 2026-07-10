# A6 LifeKernel Merge + ConsciousnessConfig

**Date:** 2026-07-10
**Status:** DONE
**Scope:** Deprecate P20 LangGraph HeartbeatService, fix server.py entrypoint, add deprecation wire notice.

---

## Summary of Changes

### 1. server.py — ConsciousnessConfig guard + substrate_names fix

**File:** `guinevere/http/server.py`

- **Fixed `substrate_names` reference:** Replaced `_consciousness_loop.substrate_names` (removed with substrates.py) with `THOUGHT_TYPE_NAMES` imported from `guinevere.consciousness`. The log line now reads `thought_types=len(THOUGHT_TYPE_NAMES)`.
- **Added ConsciousnessConfig guard:** Before attempting consciousness loop creation, the code now checks `settings.consciousness.enabled`. If `False`, the loop is skipped and a `_noop_placeholder()` task is created instead with name `"m3-consciousness-disabled"`. The guard handles `settings` being `None` (fail-soft — defaults to enabled).

### 2. wire.py — Deprecation notice in module docstring

**File:** `guinevere/consciousness/wire.py`

- Added deprecation notice to the module docstring:
  > DEPRECATED: server.py `_lifespan()` is the primary consciousness loop entrypoint. This wire is preserved for backward compatibility (agent_init.py Group G) but will be removed in a future release.
- No functional changes to `wire()` function logic.

### 3. heartbeat.py — Module-level deprecation warning

**File:** `guinevere/life_kernel/heartbeat.py`

- Added `import warnings` and `warnings.warn(...)` after the module docstring with `DeprecationWarning` category.
- Warning message: "HeartbeatService is superseded by ThoughtStream (guinevere/consciousness/thought_stream.py). HARD STOP detection → HardStopGuard (guinevere/consciousness/safety.py). Liveness monitoring → HEARTBEAT thought type. This module is preserved for backward compatibility (P20 LangGraph). Will be removed in a future release."
- Added `logger.warning("life_kernel.heartbeat.deprecated", ...)` at module level after logger definition.
- No changes to HeartbeatService class or its logic.

---

## Files Changed

| File | Change Type | Description |
|---|---|---|
| `guinevere/http/server.py` | Modified | ConsciousnessConfig guard + THOUGHT_TYPE_NAMES fix |
| `guinevere/consciousness/wire.py` | Modified | Deprecation notice in module docstring |
| `guinevere/life_kernel/heartbeat.py` | Modified | Module-level DeprecationWarning + logger.warning |

---

## Test Results

### Consciousness tests (primary target)

```
tests/p24/test_consciousness.py — ALL PASSED
tests/p24/test_consciousness_live.py — ALL PASSED
tests/p24/test_consciousness_delegate.py — ALL PASSED

================ 113 passed, 1 skipped, 20 warnings in 21.56s =================
```

### Deprecation warning verification

The `DeprecationWarning` from heartbeat.py fires correctly when the module is imported (confirmed in test output):
```
DeprecationWarning: HeartbeatService is superseded by ThoughtStream (guinevere/consciousness/thought_stream.py). HARD STOP detection → HardStopGuard (guinevere/consciousness/safety.py). Liveness monitoring → HEARTBEAT thought type. This module is preserved for backward compatibility (P20 LangGraph). Will be removed in a future release.
```

The `logger.warning("life_kernel.heartbeat.deprecated", ...)` also fires correctly:
```
2026-07-10 09:23:42 [warning  ] life_kernel.heartbeat.deprecated msg='HeartbeatService superseded by ThoughtStream (guinevere/consciousness/thought_stream.py).'
```

### Pre-existing failures (not caused by A6)

- `test_life_kernel.py`: ImportError for `CalendarSensorAdapter` (pre-existing, unrelated)
- `test_http.py`: TypeError on Loki import (pre-existing, unrelated)

---

## Forbidden Pattern Check

| Pattern | server.py | wire.py | heartbeat.py |
|---|---|---|---|
| `# type: ignore` | NONE | NONE | NONE |
| `except :` (bare) | NONE | NONE | NONE |
| `as any` (Python equivalent) | NONE | NONE | NONE |

All three files are clean of forbidden patterns.

---

## Design Decisions

1. **Guard placement:** The ConsciousnessConfig guard is placed *before* the try block (not inside it) so that disabled config doesn't trigger any import overhead from `run_agent` or `guinevere.consciousness`.

2. **Fail-soft on settings=None:** If `settings` is None (config load failed), `_consciousness_enabled` defaults to `True` — the existing try/except handles construction failures anyway.

3. **heartbeat.py warnings.warn at module level:** The `warnings.warn()` executes on import, which is the correct behavior for a deprecation warning. The `logger.warning()` also fires at module import time (structlog lazy proxy).

4. **wire.py docstring-only change:** No functional changes — the wire() function logic is preserved as-is. Only the module docstring is updated.

---

## Boundary Compliance

- No persona drift
- No consent violation
- No surveillance overreach
- No secret/intimate data exposure
- No HARD STOP bypass
- No new dependencies added

---

## Rollback/Re-run Safety

All changes are idempotent and backward-compatible:
- server.py: guard is additive; THOUGHT_TYPE_NAMES is a direct replacement for the broken `substrate_names`
- wire.py: docstring-only change, no functional impact
- heartbeat.py: warnings.warn + logger.warning only, no logic changes

Rollback: `git checkout -- guinevere/http/server.py guinevere/consciousness/wire.py guinevere/life_kernel/heartbeat.py`
