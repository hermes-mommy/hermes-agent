# P4-020 Consent Revocation Fix — Gate 10 Wiring

**Date:** 2026-06-26
**Files Modified:** `src/hermes/safety_plugin.py`
**Severity:** CRITICAL → FIXED

---

## Problem

P4-020 (Consent Revocation Flow Test) was marked `[x] ✅` in CHECKLIST.md but had NO source-level enforcement. Gate 10 in `safety_plugin.py` was explicitly deferred:

```python
# Gate 10: Consent gate (deferred)
logger.debug("gate_10_consent_deferred", ...)
```

This was a CRITICAL finding in the P4 audit (B-CRIT-01).

---

## Fix

Gate 10 now checks `SafeModeController.is_active`. When safe-mode is active (triggered by HARD STOP callback, distress D2+, or explicit consent revocation), persona-driven tool calls are blocked.

### Changed Code

**Before (safety_plugin.py:898-904):**
```python
# --- Gate 10: Consent gate (deferred) ---
logger.debug(
    "gate_10_consent_deferred",
    session_id=session_id,
    tool_name=tool_name,
    message="Consent gate requires Redis+SQLAlchemy. Deferred enforcement.",
)
```

**After:**
```python
# --- Gate 10: Consent/Safe-mode gate ---
# When safe-mode is active (HARD STOP, distress D2+, or explicit consent
# revocation), block persona-driven tool calls.
if self._distress_available and self._safe_mode_controller is not None and self._safe_mode_controller.is_active:
    logger.warning("gate_10_consent_blocked", ...)
    observe_safety_block("G10", f"CONSENT_SAFE_MODE:{tool_name}")
    return {"action": "block", "reason": "CONSENT_SAFE_MODE", ...}

logger.debug("gate_10_consent_allowed", ...)
```

### Design Decisions

| Decision | Rationale |
|----------|-----------|
| Use SafeModeController, not consent_gate.py | consent_gate.py is async P7 surveillance infrastructure. SafeModeController is already available, in-process, and integrates with HARD STOP callback. This avoids new DB scopes, async coordination, and P7 dependency. |
| Block on is_active | Safe-mode IS the consent revocation mechanism. When HARD STOP triggers (PersonaSafetyPolicy §7), the callback at safety_plugin.py:458-468 calls force_safe_mode(). Gate 10 just checks the resulting state. |
| Graceful degradation | If SafeModeController import failed, `_distress_available=False` and Gate 10 is a no-op (same as previous deferred behavior). |
| Logging | `gate_10_consent_blocked` (warning) for blocks, `gate_10_consent_allowed` (debug) for pass-through. No personal/intimate data logged. |

### Safety Audit

| Rule | Status |
|------|--------|
| Consent revocation blocks behavior | ✅ Safe-mode active → block |
| No consent bypass path | ✅ Only deactivates via `SafeModeController.deactivate(explicit_confirmation=True)` |
| Y6 still impossible | ✅ No change to Y6 guards |
| HARD STOP still halts | ✅ Gate 10 complements G01/G02 |
| No intimate data exposed | ✅ No message content logged |

---

## Tests Added

`tests/safety/test_gate_10_consent.py`:
- `test_gate10_blocks_when_safe_mode_active` — SafeModeController.is_active=True → block
- `test_gate10_allows_when_safe_mode_inactive` — SafeModeController.is_active=False → None
- `test_gate10_degrades_when_controller_unavailable` — _distress_available=False → None
- `test_gate10_blocks_after_hard_stop` — force_safe_mode() → Gate 10 blocks

`tests/safety/test_safety_boundary_regression.py`:
- `test_y6_cannot_activate` — validate_level(6) raises YandereSafetyError
- `test_hard_stop_forces_y0` — get_effective_level(safe_mode=True) → Y0_NEUTRAL
- `test_distress_blocks_punishment` — PunishmentEngine blocked during safe mode
- `test_check_distress_suspension_suspends_punishment` — D3+ suspends
