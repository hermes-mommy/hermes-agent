# STEP-C5 Verification Report

**Step**: C5 + H1 + H3 -- Wire SurveillanceSafeModeGuard, add missing blocked actions, fail-closed unknowns
**Date**: 2026-06-03
**Status**: PASS

## What Was Done

### H1: Add humiliation + public_disclosure to _BLOCKED_ACTIONS

- **File**: `src/surveillance/safe_mode.py`
- Added `"humiliation"` and `"public_disclosure"` to the `_BLOCKED_ACTIONS` frozenset
- Count increased from 6 to 8 blocked action types
- Updated module docstring (line 8) from "6 confrontation" to "8 confrontation"
- Updated `get_blocked_actions()` docstring from "6 blocked" to "8 blocked"
- PersonaSafetyPolicy alignment: section 12.2 explicitly prohibits humiliation and public disclosure

### H3: Unknown actions fail-closed BLOCKED

- **File**: `src/surveillance/safe_mode.py`
- Replaced the final fallthrough block in `check_confrontation()` (previously lines 151-161)
- Old behavior: unknown actions defaulted to ALLOWED with `logger.info`
- New behavior: unknown actions BLOCKED with `logger.warning` and `allowed=False`
- Rationale: fail-closed security posture -- unknown actions must not bypass safe mode

### C5: Wire SurveillanceSafeModeGuard into production

- **File**: `src/discord/bot.py`
- Added lazy import of `SurveillanceSafeModeGuard` and `_get_handler` inside `__init__()`
- Instantiated `self._surveillance_guard` with `safety_state_getter=lambda: _get_handler().state`
- Added `surveillance_guard` property for external module access
- Added `SurveillanceSafeModeGuard` to `TYPE_CHECKING` import block for type checker support

### Test Updates

- **File**: `tests/surveillance/test_safe_mode.py`
- Added `"humiliation"` and `"public_disclosure"` to `BLOCKED_ACTIONS` test list (now 8 items)
- Renamed `test_all_six_in_safe_mode` to `test_all_eight_in_safe_mode`, assert len == 8
- Changed `test_empty_action_string_allowed_in_safe` to `test_empty_action_string_blocked_in_safe`, assert `allowed is False`
- Changed `test_unknown_action_defaults_allowed_in_safe` to `test_unknown_action_blocked_in_safe`, assert `allowed is False`
- Parametrized tests automatically cover humiliation + public_disclosure via `BLOCKED_ACTIONS` list

## Files Changed

| File | Change Type |
|---|---|
| `src/surveillance/safe_mode.py` | Modified (H1 + H3) |
| `src/discord/bot.py` | Modified (C5 wiring) |
| `tests/surveillance/test_safe_mode.py` | Modified (test updates) |

## Validation Results

### pytest

```
73 passed, 0 failed in 1.82s
```

All 73 tests pass, including:
- 8 blocked actions x normal mode (8 tests)
- 8 blocked actions x safe mode (8 tests)
- 8 blocked actions x is_confrontation_blocked safe (8 tests)
- 8 blocked actions x is_confrontation_blocked normal (8 tests)
- test_all_eight_in_safe_mode
- test_empty_action_string_blocked_in_safe
- test_unknown_action_blocked_in_safe

### grep

| Command | Expected | Actual |
|---|---|---|
| `grep -c "humiliation" src/surveillance/safe_mode.py` | >= 1 | 1 |
| `grep -c "public_disclosure" src/surveillance/safe_mode.py` | >= 1 | 1 |

### LSP Diagnostics

| File | New Errors | Pre-existing Errors |
|---|---|---|
| `src/surveillance/safe_mode.py` | 0 | 0 |
| `src/discord/bot.py` | 0 | 4 (discord import resolution) |
| `tests/surveillance/test_safe_mode.py` | 0 | 3 (frozen dataclass test assignments) |

No new errors introduced.

## Boundary Compliance

- No persona drift: changes enforce stricter safety blocking
- No consent violation: fail-closed is more protective
- No surveillance overreach: guard is wired and active
- No type suppression: no `# type: ignore`, `as any`, or `@ts-ignore` added
- No empty catches: no exception handling changes
- cmd_safeword.py not modified (read-only reference)

## Rollback Safety

All changes are reversible via git revert. No migrations, no state changes, no destructive operations.
