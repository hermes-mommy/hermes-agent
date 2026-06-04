# D04 Safety Re-Check — P7.5 Remediation Audit

| Field | Value |
|---|---|
| **Audit ID** | D04-safety-recheck |
| **Remediation phase** | P7.5 |
| **Auditor** | Re-auditor (read-only) |
| **Date** | 2026-06-03 |
| **Scope** | 3 findings from original D04 audit: C5, H1, H3 |
| **Overall Verdict** | **PASS** |

---

## Finding C5 (CRITICAL) — SurveillanceSafeModeGuard NOT wired to production output path

**Original finding:** `SurveillanceSafeModeGuard` existed in `src/surveillance/safe_mode.py` but was never instantiated in the Discord bot or any production code path.

### Verification

**File:** `src/discord/bot.py`

| Check | Result | Evidence |
|---|---|---|
| Guard instantiated in `__init__` | ✅ | Lines 122–128: `self._surveillance_guard = SurveillanceSafeModeGuard(safety_state_getter=lambda: _get_handler().state)` |
| HardStopHandler state lambda wired | ✅ | Line 124: `from .cmd_safeword import _get_handler`; Line 127: `lambda: _get_handler().state` |
| `surveillance_guard` property exposed | ✅ | Lines 132–135: `@property def surveillance_guard(self) -> SurveillanceSafeModeGuard` |
| TYPE_CHECKING import present | ✅ | Line 22: `from src.surveillance.safe_mode import SurveillanceSafeModeGuard` (inside `if TYPE_CHECKING`) |
| Runtime import in `__init__` | ✅ | Line 123: `from src.surveillance.safe_mode import SurveillanceSafeModeGuard` |

### Verdict: **PASS** ✅

The guard is now instantiated during bot construction with a live `HardStopHandler.state` lambda, and exposed as a read-only property for downstream consumers.

---

## Finding H1 (HIGH) — `_BLOCKED_ACTIONS` doesn't cover all 7 Section 12.2 prohibited uses

**Original finding:** `_BLOCKED_ACTIONS` had 6 entries; `humiliation` and `public_disclosure` were missing, failing to cover all Section 12.2 prohibited uses.

### Verification

**File:** `src/surveillance/safe_mode.py`, lines 31–40

```python
_BLOCKED_ACTIONS: Final[frozenset[str]] = frozenset({
    "confrontation",            # line 32
    "blackmail",                # line 33
    "punishment",               # line 34
    "jealousy_escalation",      # line 35
    "dependency_manipulation",  # line 36
    "intimate_data_reference",  # line 37
    "humiliation",              # line 38  ← NEW
    "public_disclosure",        # line 39  ← NEW
})
```

| Check | Result | Evidence |
|---|---|---|
| Entry count = 8 | ✅ | Counted 8 entries in frozenset (lines 32–39) |
| `humiliation` present | ✅ | Line 38 |
| `public_disclosure` present | ✅ | Line 39 |
| Docstring says "8" (not "6") | ✅ | Line 8: `"blocks 8 confrontation action types"` |
| `get_blocked_actions` docstring says "8" | ✅ | Line 180: `"all 8 blocked action types"` |

**File:** `tests/surveillance/test_safe_mode.py`

| Check | Result | Evidence |
|---|---|---|
| Test `BLOCKED_ACTIONS` list has 8 entries | ✅ | Lines 38–47: 8 items listed |
| `humiliation` in test list | ✅ | Line 45 |
| `public_disclosure` in test list | ✅ | Line 46 |
| `test_all_eight_in_safe_mode` exists | ✅ | Line 200: `def test_all_eight_in_safe_mode` |
| Asserts `len(result) == 8` | ✅ | Line 204 |

### Verdict: **PASS** ✅

All 8 prohibited uses are now covered in both source and tests. Docstrings updated consistently.

---

## Finding H3 (HIGH) — Unknown SAFE-mode actions default to ALLOWED (fail-open)

**Original finding:** Unknown action types in `check_confrontation()` fell through to a default that returned `allowed=True` (fail-open), violating the fail-closed safety principle.

### Verification

**File:** `src/surveillance/safe_mode.py`, lines 153–163

```python
# Unknown action type -- fail-closed: BLOCK in safe mode.
logger.warning(
    "confrontation_unknown_action_blocked",
    action=action,
    safety_state=state.value,
)
return ConfrontationDecision(
    allowed=False,                                                    # ← FAIL-CLOSED
    reason=f"Unknown action type -- blocked in safe mode (fail-closed)",
    blocked_action=action,
)
```

| Check | Result | Evidence |
|---|---|---|
| Unknown action returns `allowed=False` | ✅ | Line 160: `allowed=False` |
| Comment says "fail-closed" | ✅ | Line 153: `# Unknown action type -- fail-closed: BLOCK in safe mode.` |
| Warning logged | ✅ | Lines 154–158: `logger.warning("confrontation_unknown_action_blocked", ...)` |

**File:** `tests/surveillance/test_safe_mode.py` — Edge case tests

| Check | Result | Evidence |
|---|---|---|
| `test_empty_action_string_blocked_in_safe` | ✅ | Lines 358–364: asserts `decision.allowed is False` and `"Unknown" in decision.reason` |
| `test_unknown_action_blocked_in_safe` | ✅ | Lines 366–372: asserts `decision.allowed is False` and `"Unknown" in decision.reason` |
| `test_unknown_action_allowed_in_normal` | ✅ | Lines 374–379: asserts `decision.allowed is True` (normal mode unchanged) |

### Verdict: **PASS** ✅

Unknown actions in SAFE mode are now fail-closed (blocked) with warning-level logging. NORMAL mode behaviour is preserved.

---

## Summary

| Finding | Severity | Original Verdict | Re-Check Verdict |
|---|---|---|---|
| **C5** — Guard not wired | CRITICAL | NEEDS REVIEW | **PASS** ✅ |
| **H1** — Missing blocked actions | HIGH | NEEDS REVIEW | **PASS** ✅ |
| **H3** — Fail-open unknown | HIGH | NEEDS REVIEW | **PASS** ✅ |

### Overall Verdict: **PASS**

All three D04 safety findings have been correctly remediated:
- C5: `SurveillanceSafeModeGuard` is instantiated in `GuinevereBot.__init__` with a live `HardStopHandler.state` lambda and exposed via property.
- H1: `_BLOCKED_ACTIONS` now contains all 8 entries including `humiliation` and `public_disclosure`; docstrings and tests are consistent.
- H3: Unknown actions in SAFE mode are now fail-closed (`allowed=False`) with `logger.warning`; edge-case tests cover empty string, unknown action, and normal-mode passthrough.

---

*Report generated 2026-06-03. Read-only audit — no source files modified.*
