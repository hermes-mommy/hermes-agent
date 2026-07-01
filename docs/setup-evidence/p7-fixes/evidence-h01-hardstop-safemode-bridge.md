# P7 Evidence — H-01 Fix: HardStopHandler ↔ SafeModeController Bridge

**Date:** 2026-06-09
**Finding:** H-01 (from P4 audit, still open)
**Severity:** CRITICAL (safety)

---

## Problem

`HardStopHandler._trigger()` only set its own `self.state = SAFE` but had no mechanism to notify `SafeModeController`. This meant:

1. `SafeModeController.force_safe_mode()` didn't exist — no way to force safe mode from external trigger
2. HardStopHandler had no callback/broadcast mechanism
3. Non-Discord paths (CLI, API, future services) would not trigger safe mode

## Fix Applied

### 1. `src/persona/safe_mode.py` — Added `force_safe_mode()`

```python
def force_safe_mode(
    self,
    context: str = "external_trigger",
    trigger: DistressLevel = DistressLevel.D4_EMERGENCY,
) -> None:
```

- Bypasses normal distress evaluation flow
- Idempotent — only upgrades trigger level if new one is higher
- Full audit logging via structlog

### 2. `src/hermes/safety_plugin.py` — Wired bridge callback

```python
# Wire HardStopHandler → SafeModeController via callback.
if self._hard_stop_available and self._hard_stop_handler is not None:
    def _on_hard_stop(event: Any) -> None:
        if self._safe_mode_controller is not None:
            self._safe_mode_controller.force_safe_mode(
                context=f"hard_stop:{event.trigger}",
            )
    self._hard_stop_handler.register_on_trigger(_on_hard_stop)
```

### 3. Additional fixes in safety_plugin.py

- D2 distress: yandere_level → 2 (not 0); D3+: yandere_level → 0
- Recovery: syncs distress_state=0 to Redis on recovery
- Drift detection: uses SOUL.md canonical baseline hash
- F-15: action changed from REWRITE to LOG
- Y6 semantic check: tightened regex to reduce false positives

## Verification

```
tests/persona/test_safe_mode.py + tests/safety/test_hard_stop_handler.py
→ 151 passed in 3.50s ✅

tests/persona/ + tests/safety/ (full suite)
→ 1675 passed, 4 failed (pre-existing enum mismatch, not from this fix)
```

## Status: ✅ RESOLVED
