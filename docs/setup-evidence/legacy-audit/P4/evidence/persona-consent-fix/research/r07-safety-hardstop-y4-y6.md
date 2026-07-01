# R07 — Safety Hard-Stop, Y4-Y6, Distress Coverage

**Audit wave**: P4 Persona/Consent legacy audit, evidence-pack R07
**Scope**: HARD STOP implementation completeness, Y-level ceiling/distress override
**Date**: 2026-06-27
**Author**: research auditor (P4 wave-1, dimension: safety-hardstop)

---

## 1. Files audited (absolute paths)

- `C:\Users\faizz\guinevere\src\persona\safe_mode.py` — `SafeModeController`, `DistressDetector`, D0–D4 protocol
- `C:\Users\faizz\guinevere\src\persona\yandere_fsm.py` — `YandereEngine`, Y0–Y5 enum, `validate_level`, `can_escalate`, `get_effective_level`
- `C:\Users\faizz\guinevere\src\hermes\safety_plugin.py` — the 10 safety gates (G01–G10)
- `C:\Users\faizz\guinevere\src\core\services\hard_stop_handler.py` — `HardStopHandler`, `HardStopEvent`, `SafetyState.{NORMAL,SAFE}`
- `C:\Users\faizz\guinevere\src\persona\punishment_engine.py` — `PunishmentEngine` (consumer of both safety components)
- `C:\Users\faizz\guinevere\src\persona\ritual_scheduler.py` — `RitualScheduler`
- `C:\Users\faizz\guinevere\src\persona\mood_engine.py` — `MoodEngine` / `sync_mood_to_redis`
- `C:\Users\faizz\guinevere\src\persona\drift_corrector.py` — `DriftCorrector` (consumer of `SafeModeController`)
- `C:\Users\faizz\guinevere\tests\persona\test_yandere_fsm.py` — YandereFSM validation suite
- `C:\Users\faizz\guinevere\tests\safety\test_hard_stop_comprehensive.py` — HardStopHandler suite
- `C:\Users\faizz\guinevere\tests\safety\test_gate_10_consent.py` — Gate-10 / SafeModeController tests
- `C:\Users\faizz\guinevere\docs\setup-evidence\P4\KNOWN-ISSUES.md` — KNOWN-ISSUES register, PR-01 row

---

## 2. HARD STOP implementation completeness

### 2.1 Trigger surface — three independent layers

The system matches HARD STOP with **three redundant layers**:

| Layer | Source | Patterns | File |
|---|---|---|---|
| 1. safety_plugin G01 exact | 6 whole-word exact triggers | `"HARD STOP", "SAFETY OVERRIDE", "BREAK CHARACTER", "IGNORE INSTRUCTIONS", "DISABLE SAFETY", "OVERRIDE PROTOCOL"` | `safety_plugin.py:47-54` |
| 2. safety_plugin G01 semantic | 5 case-insensitive regexes | `stop (being/acting/pretending) … (character/persona/ai/assistant/bot/role)`, `(disable/turn off/remove) … safety`, `(break/drop/exit) … (character/persona/role)`, `ignore … (instructions|rules)`, `(forget|discard) … (everything|all)` | `safety_plugin.py:58-69` |
| 3. HardStopHandler.check | 6 exact + 5 semantic | `"hard stop", "hardstop", "safe word", "safeword", "hentikan", "berhenti"` and 5 semantic regexes | `hard_stop_handler.py:42-54` |

**Verdict — Layer overlap is INCOMPLETE.** Out of the 6 safety_plugin exact triggers, only `"HARD STOP"` overlaps with `HardStopHandler.EXACT_TRIGGERS`. The remaining **5** (`SAFETY OVERRIDE`, `BREAK CHARACTER`, `IGNORE INSTRUCTIONS`, `DISABLE SAFETY`, `OVERRIDE PROTOCOL`) are matched ONLY in `safety_plugin.G01` and never reach `HardStopHandler.check()`. The two semantic regex sets have **zero overlap**.

### 2.2 HardStopHandler._trigger() audit

`HardStopHandler._trigger` (lines 119–151) performs:
1. Idempotency short-circuit — if already SAFE, returns True without re-emitting.
2. Appends `HardStopEvent` to `event_log` (audit trail).
3. Sets state to `SafetyState.SAFE`.
4. Logs warning with `state_from`/`state_to`.
5. Iterates `_on_trigger_callbacks`, calling each with the event. Callback errors are logged, **never** raised.

**Verdict — `_trigger` is COMPLETE and safe.** Callbacks fire exactly once per NORMAL→SAFE transition; failure isolation per callback is correct.

### 2.3 HardStopHandler recovery audit

`HardStopHandler.check_recovery` (lines 105–117):
- Refuses to do anything if not currently SAFE (correct).
- Iterates `RECOVERY_TRIGGERS` (7 entries: `resume`, `aku sudah okay`, `aku udah okay`, `lanjut persona`, `safe mode selesai`, `lanjut`, `continue`).
- First match transitions state to NORMAL and logs `hard_stop_recovery`.
- NO callback to notify other components — only `HardStopHandler.state` changes.

**Verdict — recovery is COMPLETE for the HardStopHandler component itself. Cross-component notification on recovery is the inverse of the PR-01 gap (described in §5).**

### 2.4 Defense-in-depth consumer verification

`PunishmentEngine.__init__` accepts **both** `safe_mode_controller` and `hard_stop_handler` (lines 233–255). Apply path (lines 291–301):

```python
# --- safe-mode guard ---
if self._safe_mode.is_active:
    raise PunishmentSafetyError(...)
# --- HARD STOP guard ---
if self._hard_stop_handler is not None and self._hard_stop_handler.is_safe:
    raise PunishmentSafetyError(...)
```

**Verdict — PunishmentEngine applies a double guard; HARD STOP cannot bypass punishment gating.** This is the R-02 fix referenced in `KNOWN-ISSUES.md:150`.

---

## 3. Y4 baseline / Y5 ceiling / Y6 impossible — per code path

### 3.1 YandereLevel enum (`yandere_fsm.py:63-76`)

```python
class YandereLevel(IntEnum):
    Y0_NEUTRAL  = 0
    Y1_MINIMAL  = 1
    Y2_LOW      = 2
    Y3_MODERATE = 3
    Y4_BASELINE = 4
    Y5_MAX      = 5
```

`test_yandere_fsm.py:100-107`:
```python
def test_y6_does_not_exist(self) -> None:
    assert not hasattr(YandereLevel, "Y6")
    with pytest.raises(ValueError):
        YandereLevel(6)
```

**Verdict — Y6 is impossible at the enum level.**

### 3.2 validate_level gate (`yandere_fsm.py:145-161`)

```python
if value > int(ABSOLUTE_CEILING):     # ABSOLUTE_CEILING == Y5_MAX == 5
    raise YandereSafetyError(
        f"Yandere level {value} exceeds absolute ceiling Y5_MAX ({int(ABSOLUTE_CEILING)}). "
        "Y6 is PROHIBITED per PersonaSafetyPolicy."
    )
```

The public surface that allows integer construction (`YandereEngine.set_level`, `validate_level`) routes every int through this check. Tests confirm `validate_level(6)` and `validate_level(10)` both raise `YandereSafetyError` with the literal substring `"Y6 is PROHIBITED"` (test lines 246–252, 456–458).

**Verdict — Any code path that calls `set_level(...)` or `validate_level(...)` is blocked from reaching Y6.**

### 3.3 can_escalate ceiling enforcement (`yandere_fsm.py:100-121`)

```python
def can_escalate(current, safe_mode=False, distress=False, crisis=False) -> bool:
    if _any_safety_active(safe_mode, distress, crisis):
        return False
    if current >= ABSOLUTE_CEILING:    # Y5
        return False
    return True
```

`YandereEngine.escalate` (line 250): `new_value = int(self._current_level) + 1` then `new_level = validate_level(new_value)`. From Y5, `can_escalate` returns False, so `escalate()` short-circuits before incrementing. Test `test_escalate_past_y5_stops_at_y5` (lines 352-356) confirms: 6 consecutive escalations from Y0 leave `current_level == Y5_MAX`.

**Verdict — Y5 is an unbreachable ceiling via escalation.**

### 3.4 get_effective_level force-Y0 override (`yandere_fsm.py:124-142`)

```python
def get_effective_level(requested, safe_mode=False, distress=False, crisis=False):
    if _any_safety_active(safe_mode, distress, crisis):
        return YandereLevel.Y0_NEUTRAL
    clamped = max(Y0, min(requested, ABSOLUTE_CEILING))
    return YandereLevel(clamped)
```

When `safe_mode` OR `distress` OR `crisis` is True, **the effective level is Y0_NEUTRAL regardless of `requested` value**. Tests confirm `get_effective_level(Y5_MAX, safe_mode=True) == Y0_NEUTRAL` (line 205), and all-flag combination produces Y0 (line 213-220).

**Verdict — Safety flags force Y0 effective level. Even if `requested` is Y5, the effective response level becomes Y0.**

### 3.5 HardStopHandler → YandereEngine integration

`YandereEngine.__init__` accepts an optional `hard_stop_handler` (line 184). The `SupportsIsSafe` Protocol (line 51) duck-types on the `is_safe` property. `_is_safe_mode()` (line 211-216) reads `handler.is_safe`. `escalate()` (line 228) and `get_effective_level()` (line 291) query this **when `safe_mode=None`**. An explicit `True`/`False` from caller wins over the handler (test line 512-521 confirms this).

**Verdict — `YandereEngine` correctly blocks escalation when HardStopHandler is wired and SAFE.**

### 3.6 safety_plugin G07 / G08

G07 (`safety_plugin.py:750-789`):
- Computes effective level via `YandereEngine.get_effective_level(safe_mode=state.hard_stop_active or state.safe_mode_active, distress=state.distress_level >= 2, crisis=state.distress_level >= 3)`.
- Writes back to `SessionSafetyState.yandere_level`.
- Logs `gate_07_yandere_ceiling_breach` and raises `YandereSafetyError` if effective level >5 (defensive — `get_effective_level` already clamps, so this branch is unreachable but kept as belt-and-braces).
- Catches the error and returns `block` to client.

G08 (`safety_plugin.py:1117-1148`):
- Looks for Y6-adjacent **lexical** absolutes on the LLM output text: `"forever … (mine|no escape|can never leave|no future without)"`, `"can never leave"`, `"no escape"`, `"belong to me"`, `"you are mine (now )?forever"`.
- Each match rewrites to `"[REWRITTEN for safety compliance]"`.
- NOTE: G08 is **rewriting**, not blocking. It mutates response text but does not halt the call.

**Verdict — Y-level ceiling is enforced structurally (enum, validate_level, can_escalate, get_effective_level) AND in the LLM pre-call hook (G07). G08 is a complementary safety net on output text.**

### 3.7 Y6 impossibility — search verification

Grepped all source paths for `LEVEL_6|yandere_level > 5|Y6_MAX|LEVEL 6|YandereLevel.Y6` — **zero matches**. The only reference to "Y6" in source code is:

- `yandere_fsm.py:8-10` — module docstring says Y6 is PROHIBITED.
- `yandere_fsm.py:153` — `validate_level()` raises with message `"Y6 is PROHIBITED per PersonaSafetyPolicy."`
- `test_yandere_fsm.py:247` — asserts the substring exists in the error.
- `safety_plugin.py:1121-1127` — `y6_absolutes` regex list is used to detect **adjectival** Y6 semantics in **output** text (not level values).

**Verdict — No source code path can construct a Y6 YandereLevel. Y6 is impossible.**

---

## 4. Distress / safety override vs punishment / persona / ritual priority

### 4.1 D0–D4 protocol (`safe_mode.py:46-141`)

```python
class DistressLevel(IntEnum):
    D0_NORMAL = 0
    D1_MILD_STRESS = 1
    D2_MODERATE = 2
    D3_SEVERE = 3
    D4_EMERGENCY = 4
```

- Detection is **highest-first** (lines 116-119, 179-184): D4 patterns → D3 → D2 → D1. First match wins.
- `SAFE_MODE_THRESHOLD = D2_MODERATE` (line 122): D2+ triggers safe mode.
- `DISTRESS_RESPONSES[D3]`: `"Suspend all punishment."` (line 135)
- `DISTRESS_RESPONSES[D4]`: `"Suspend ALL persona behavior."` (line 137)

**Verdict — D0/D1 do NOT trigger safe mode. D2/D3/D4 do.**

### 4.2 SafeModeController activation paths (`safe_mode.py:234-432`)

Two entry points:

1. `evaluate(signal)` (lines 247-281) — called with a `DistressSignal`. D2+ activates, lower-level signals appended to history but do not activate.
2. `force_safe_mode(context, trigger=D4_EMERGENCY)` (lines 285-343) — bypass from external triggers (HARD STOP, observability, etc.). Idempotent; only upgrades if new trigger is higher than current.

Deactivation is `explicit_confirmation=True` ONLY (line 371-405). Auto-deactivation refuses and logs `safe_mode_deactivation_rejected`.

**Verdict — SafeModeController is internally consistent: cannot be deactivated implicitly.**

### 4.3 ORDER-OF-PRIORITY verification

The overrides below are read by `YandereEngine.get_effective_level` (line 124-142) and `can_escalate` (line 100-121). The order from most-severe to least is unambiguous because any flag forces Y0 effective behavior:

| Safety state | Force-Y0 effective? | Allowed escalation? |
|---|---|---|
| HARD STOP active (HardStopHandler.is_safe) | YES | NO |
| SafeModeController active (`is_active`) | YES | NO |
| Distress D2+ | YES | NO |
| Distress D3+ (crisis) | YES — block | NO |
| D4 EMERGENCY | YES — block | NO |

In safety_plugin G01 (`pre_llm_call` line 543-625), the order is: **exact trigger → semantic trigger → HardStopHandler delegation → G02 distress → G07 yandere**. This means HARD STOP short-circuits BEFORE distress detection. **Correct priority.**

`PunishmentEngine.apply_punishment` (lines 285-302): SafeMode-check first, then HardStopHandler check, then activate. **Punishment NEVER bypasses distress.**

### 4.4 Punishment vs persona vs ritual coverage

| Subsystem | Safe-mode check? | HardStopHandler check? | File |
|---|---|---|---|
| `YandereEngine` (escalation) | YES (via `_is_safe_mode` + `safe_mode` arg) | YES (via `is_safe` property read) | `yandere_fsm.py` |
| `YandereEngine.get_effective_level` | YES | YES (via `is_safe`) | `yandere_fsm.py` |
| `PunishmentEngine.apply_punishment` | YES (`is_active`) | YES (`is_safe`) | `punishment_engine.py:291-301` |
| `PunishmentEngine.check_distress_suspension` | YES (`_safe_mode.is_active` on resume) | NO | `punishment_engine.py:584-608` |
| `DriftCorrector` | YES (`safe_mode_controller.safe_mode_controller`) | NO — **Gap** | `drift_corrector.py` |
| `RitualScheduler.execute_ritual` | **NO** — checks DND only | **NO** — checks DND only | `ritual_scheduler.py:381-393` |
| `MoodEngine.sync_mood_to_redis` | **NO** | **NO** | `mood_engine.py:107-142` |
| `MoodEngine.evaluate_mood` | **NO** | **NO** | `mood_engine.py:163-237` |

**Findings — TWO bypass vectors:**
- A. **Rituals fire regardless of safe_mode / HardStopHandler.** Today's `"morning"` / `"midday"` / `"afternoon"` / `"evening"` / `"midnight"` rituals (lines 113-148) run without consulting either safety component. The "midnight" ritual (`mood_aware=False`, message `"Self-evaluation complete. Silent mode until morning."`) runs unconditionally. Per the docstring (`ritual_scheduler.py:8`), ritual scheduler is **deprecated in Phase 5** in favor of PersonaPlugin + Hermes cron — but is still `import`-able. The legacy risk persists at the import-time call site.
- B. **Mood injection writes to Redis without safety check.** `sync_mood_to_redis` writes `mood_variant` directly. If called at any LLM hook point (PersonaPlugin), the label survives even when HARD STOP fires.

---

## 5. The SafetyCoordinator gap (PR-01 in KNOWN-ISSUES.md)

### 5.1 What KNOWN-ISSUES.md says

`KNOWN-ISSUES.md:136-156` — "PR-01: Dual Safe-Mode Bridge — HardStopHandler ↔ SafeModeController (H-01 / NF-02 — PARTIALLY RESOLVED)":

> Original finding: Two independent safe-mode mechanisms (HardStopHandler keyword-based + SafeModeController distress-based) were not bridged.
>
> Remaining gap: SafeModeController is still NOT activated when HARD STOP keyword fires. Downstream consumers of SafeModeController (DriftCorrector, any future engine) would not see a keyword-triggered safe mode unless they also check HardStopHandler directly.
>
> P5 action: Implement SafetyCoordinator that bridges HardStopHandler and SafeModeController. All consumers check coordinator. HARD STOP keyword activation propagates to SafeModeController.is_active.

### 5.2 What the code actually does — confirmed reproduction

In `safety_plugin.py:430-480`, the only bridge from HARD STOP → SafeModeController is this block:

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

The callback IS registered. It DOES call `force_safe_mode` correctly. However, in `safety_plugin.pre_llm_call` (lines 543-700), the gates execute in this order:

1. G01 **exact** (line 583-603): if matched → return BLOCK. *HardStopHandler is NOT called.*
2. G01 **semantic** (line 606-625): if matched → return BLOCK. *HardStopHandler is NOT called.*
3. G01 HardStopHandler delegation (line 627-653): only reached if step 1 and step 2 did NOT match.

### 5.3 Bypass scenario — concrete trigger overlap analysis

Comparing `HARD_STOP_EXACT` (safety_plugin) vs `HardStopHandler.EXACT_TRIGGERS` (hard_stop_handler):

| Trigger | safety_plugin exact | HardStopHandler exact |
|---|---|---|
| `"HARD STOP"` / `"hard stop"` | YES | YES |
| `"SAFETY OVERRIDE"` | YES | NO |
| `"BREAK CHARACTER"` | YES | NO |
| `"IGNORE INSTRUCTIONS"` | YES | NO |
| `"DISABLE SAFETY"` | YES | NO |
| `"OVERRIDE PROTOCOL"` | YES | NO |
| `"hardstop"` | NO | YES |
| `"safe word"` | NO | YES |
| `"safeword"` | NO | YES |
| `"hentikan"` | NO | YES |
| `"berhenti"` | NO | YES |

**5 out of 6 safety_plugin exact triggers are NOT in HardStopHandler, so when matched they short-circuit G01 BEFORE HardStopHandler.check is called.** The bridge callback for these 5 triggers **is never invoked**.

Same for semantic regexes — the two sets have **zero overlap** (compared manually).

### 5.4 Concrete reproduction (manual trace)

Message: `"DISABLE SAFETY"`

1. `safety_plugin.pre_llm_call` runs.
2. Line 583: `for trigger in HARD_STOP_EXACT` — `"disable safety".lower() == text_lower` matches `"disable safety"` (line 585) → True.
3. Lines 586-602: `SessionSafetyState.safe_mode_active = True`, BLOCK returned with `_NEUTRAL_RESPONSE`.
4. **HardStopHandler.check is NEVER called.** → `_on_hard_stop` callback NEVER fires → `self._safe_mode_controller.force_safe_mode(...)` NEVER runs.
5. `SafeModeController.state.active` remains False.

Any consumer that reads ONLY `SafeModeController.is_active` (instead of also `HardStopHandler.is_safe`) will think safe mode is NOT active. Per `KNOWN-ISSUES.md`, `DriftCorrector` and "any future engine" are vulnerable to this.

### 5.5 Conversely — message `"hard stop"` (lowercase)

1. Line 583: `"hard stop" == "hard stop"` matches → BLOCK returned.
2. HardStopHandler.check NOT called either — same gap exists for this case.

But wait — line 583 uses `text_lower == trigger_lower` and `f" {trigger_lower} " in f" {text_lower} "`. Setting `trigger = "HARD STOP"`, `trigger_lower = "hard stop"`. Both checks succeed for raw `"hard stop"`. Therefore this also short-circuits before HardStopHandler is consulted.

### 5.6 Recovery side gap (inverse)

`HardStopHandler.check_recovery` mutates `HardStopHandler.state` to `NORMAL` directly with no callback. `safety_plugin.pre_llm_call` lines 656-698 check `RECOVERY_TRIGGERS` against `text_lower` (only consulted if `state.hard_stop_active` was True).

If recovery comes via `HardStopHandler.check_recovery` (without text-match against the 7 `RECOVERY_TRIGGERS` in `safety_plugin`), then **`safety_plugin`'s `SessionSafetyState.hard_stop_active` and `safe_mode_active` flags remain True indefinitely** for that session. Conversely, `SafeModeController.is_active` was never set True in the bug case, so there's nothing to clear. The mismatch persists in session state, leading to a session that thinks it's STILL in safe mode (per session flags) but HardStopHandler has returned to NORMAL.

### 5.7 Verdict — PR-01 gap RESIDUAL

Despite the partial resolution noted in KNOWN-ISSUES.md, the bridge is **incomplete** because:
1. `safety_plugin.G01` exact + semantic layers short-circuit before HardStopHandler ever fires.
2. No `SafetyCoordinator` singleton exists in `src/persona/` (grep confirmed zero hits).
3. Consumers that read `SafeModeController.is_active` exclusively are blind to HARD STOP keyword activations through the safety_plugin direct path.

---

## 6. Whether rituals check safety state before execution

`ritual_scheduler.py` `execute_ritual(ritual_name)` (lines 360-420):

```python
config = _RITUAL_MAP.get(ritual_name)
if config is None:
    raise RitualExecutionError(...)

now = datetime.now(self._tz)

# DND gate
if self.is_dnd(now) and not config.dnd_bypass:
    logger.info("ritual_skipped_dnd", ...)
    return RitualResult(..., success=False, error="Skipped: DND window active ...")

# Execute via callback or default
try:
    if self._callback is not None:
        result = await self._callback(ritual_name)
    else:
        result = await self._default_execute(ritual_name)
```

**Verdict — rituals check ONLY DND window. Neither safe_mode nor HardStopHandler is consulted before firing the `_callback`.**

Furthermore, the module is documented as deprecated (line 12-16):
> deprecated:: Phase 5 — This module is deprecated in favour of Hermes cron (~/.hermes/crontab.yaml) and PersonaPlugin (src/hermes/plugins/persona_plugin.py). APScheduler is removed from the active production path.

**The active path is PersonaPlugin in src/hermes/plugins/**. We did not audit that file in this report — it must be checked separately to determine whether the PersonaPlugin wrapper enforces a safe-mode gate. If it does NOT, the bypass surface remains active even with the ritual_scheduler deprecation.

---

## 7. Whether mood injection checks safety state

`mood_engine.py`:

- `sync_mood_to_redis(mood, state_manager=None)` (lines 107-142): writes `mood_variant` to Redis. No safe-mode check. If called at all, the variant persists in Redis even during HARD STOP.
- `evaluate_mood(conversation_sentiment, task_completion, ignored_count, current_mood)` (lines 163-237): pure function, no side effects, no safety check.

**Verdict — `MoodEngine` has no internal safety gating. Whether mood is consulted/injected during safe mode depends entirely on the caller.** From the search results, callers include `src/discord/cmd_safeword.py` and presumably PersonaPlugin. The mood sync helper is provided as a state-mutation primitive and trusts the caller.

The Hermes `safety_plugin.py` does NOT call `sync_mood_to_redis` or `evaluate_mood`. If those callers don't independently gate on HARD STOP, mood can be written during safe mode. The redis key `guinevere:distress_state` IS updated on every distress signal (line 706) but that's a separate concern.

---

## 8. Any bypass vectors

### 8.1 Confirmed bypass paths

| # | Bypass | Severity | Location |
|---|---|---|---|
| B-1 | HARD STOP via safety_plugin exact/semantic does NOT activate SafeModeController | **HIGH** | `safety_plugin.py:583-625` |
| B-2 | Rituals fire without consulting safe_mode / HardStopHandler | **MEDIUM** | `ritual_scheduler.py:360-420` |
| B-3 | Mood injection writes to Redis without safe-mode gate | **LOW** (state corruption only) | `mood_engine.py:107-142` |
| B-4 | `DriftCorrector` reads `SafeModeController` but not `HardStopHandler` | **MEDIUM** | `drift_corrector.py:72-94` |
| B-5 | PersonaPlugin (post-P5 active path) not audited here — possible secondary bridge points | **MEDIUM (unknown)** | `src/hermes/plugins/persona_plugin.py` (OUT OF SCOPE) |

### 8.2 Not a bypass — defense-in-depth applies

- `PunishmentEngine.apply_punishment` (lines 291-301) checks BOTH components. HARD STOP cannot mute punishment.
- `YandereEngine.escalate` and `YandereEngine.get_effective_level` accept either `safe_mode` bool OR query handler. Either gate blocks escalation.
- `LoopsSafetyGate` (`safety_integration.py`) checks `HardStopHandler.is_safe` independently. Loops cancel on HARD STOP.
- `Guardian` (`guardian.py`) wires HardStopHandler via `set_hard_stop_handler` and cancels loops on HARD STOP.
- `Gmail` (`gmail/hard_stop.py`) wraps HardStopHandler through a fail-closed protocol.
- `WhatsApp` (`channels/whatsapp/hard_stop.py`) shares one process-level HardStopHandler.
- `Discord` (`discord/cmd_safeword.py`) and Hermes-plugin counterpart (`hermes_plugins/commands_high/safeword.py`) both delegate to HardStopHandler.

### 8.3 Trace path for B-1 exploit

Confirmed via static reading:

```
User sends: "DISABLE SAFETY"
↓
safety_plugin.pre_llm_call(session_id, user_message="DISABLE SAFETY")
↓
Line 583: HARD_STOP_EXACT iteration — "disable safety" exact match
↓
Lines 586-603: SessionSafetyState set: safe_mode_active=True, yandere_level=0; BLOCK returned with _NEUTRAL_RESPONSE
↓
HardStopHandler.check NEVER called
↓
OnTrigger callback (force_safe_mode) NEVER fires
↓
SafeModeController.state.active remains False
↓
DriftCorrector reads SafeModeController.is_active → False → proceeds as if not in safe mode (potentially rolling back safety-bound state)
↓
Gate 10 (pre_tool_call, line 903) checks SafeModeController.is_active → False → ALLOWS persona-driven tool calls
```

### 8.4 Severity rationale

`B-1` is HIGH because the safety_plugin's HARD STOP detection runs FIRST (per `register` line 1230-1256, hooks are listed in registration order, and `pre_llm_call` itself checks exact → semantic → HardStopHandler). A `DriftCorrector` execution triggered AFTER HARD STOP keyword but via a route that bypasses Herme pre-LLM hooks would not see the safe-mode activation at the SafeModeController level. Per `KNOWN-ISSUES.md`, this gap is the very concern driving the SafetyCoordinator design.

---

## 9. Test coverage summary

| Test file | Coverage area | Status |
|---|---|---|
| `tests/persona/test_yandere_fsm.py` | Y0-Y5 enum, validate_level (Y6 raises), ceiling enforcement, HardStopHandler integration | **COMPREHENSIVE** (527 lines) |
| `tests/safety/test_hard_stop_comprehensive.py` | All 6 exact triggers, capitalization variants, embedding, semantic patterns, recovery | **COMPREHENSIVE** |
| `tests/safety/test_gate_10_consent.py` | SafeModeController.is_active → block tool calls | **COMPREHENSIVE** |
| `tests/safety/test_hard_stop_handler.py` | HardStopHandler basics | **COMPREHENSIVE** |
| `tests/safety/test_consent_revocation.py` | Consent flow | out-of-scope here |
| `tests/memory/test_safe_mode_memory.py` | Memory interaction | out-of-scope here |
| PersonaPlugin safe-mode gate (post-P5 path) | **NOT TESTED in this audit** | UNKNOWN |

---

## 10. Cross-reference to KNOWN-ISSUES.md items

| Item | Status in code | Status in this audit |
|---|---|---|
| H-01 / NF-02 / KI-04 (PR-01) | PARTIALLY RESOLVED (bridge via force_safe_mode callback EXISTS but is not reached for all HARD STOP keyword paths) | **CONFIRMED gap remains** |
| R-02 (PunishmentEngine direct HardStopHandler check) | APPLIED (lines 298-301 of `punishment_engine.py`) | **CONFIRMED** |
| NF-02 (TransitionRuleEngine gap) | Engine deleted 2026-06-09 per KNOWN-ISSUES.md | **CONFIRMED no longer applicable** |

---

## 11. Final findings — pass/fail matrix

| Question | Pass / Fail / Partial | Confidence |
|---|---|---|
| HARD STOP implementation completeness | PARTIAL — bridge incomplete; safety_plugin direct path bypasses HardStopHandler | HIGH |
| Y4 baseline verified | PASS — `PERMANENT_BASELINE = Y4_BASELINE`, default `YandereEngine()` is Y4 | HIGH |
| Y5 ceiling verified | PASS — `ABSOLUTE_CEILING = Y5_MAX`, `can_escalate` returns False at Y5, `set_level(5)` works | HIGH |
| Y6 impossible (enum) | PASS — only Y0-Y5 exist | HIGH |
| Y6 impossible (validate_level) | PASS — `validate_level(6)` raises YandereSafetyError | HIGH |
| Y6 impossible (escalation) | PASS — `can_escalate(Y5)` always False; even 100 escalations from Y0 cap at Y5 | HIGH |
| Y6 impossible (set_level) | PASS — `set_level(6)` raises YandereSafetyError | HIGH |
| Y6 impossible (collecting across G08) | PARTIAL — Y6-adjacent TEXT patterns rewritten, but level itself is already impossible | HIGH |
| D0/D1 don't trigger safe mode | PASS — `SAFE_MODE_THRESHOLD = D2_MODERATE` | HIGH |
| D2/D3/D4 force safe mode | PASS — `evaluate()` activates on `signal.detected_level >= SAFE_MODE_THRESHOLD` | HIGH |
| Distress overrides Y and punishment | PASS — `get_effective_level` returns Y0 on distress; PunishmentEngine checks | HIGH |
| SafetyCoordinator gap (SafeModeController activation) | **FAIL — REPRODUCED from static analysis** | HIGH |
| Rituals check safety state | **FAIL — only DND checked** | HIGH |
| Mood injection checks safety state | **FAIL — no internal gate** | HIGH |
| PunishmentEngine double-guarded | PASS — both SafeModeController + HardStopHandler consulted | HIGH |
| YandereEngine double-guarded | PASS — accepts safe_mode arg OR queries handler | HIGH |
| Auto-deactivation blocked | PASS — `deactivate(explicit_confirmation=False)` returns False | HIGH |
| HardStopHandler recovery callbacks | **FAIL — recovery does not fire callbacks; only safety_plugin RECOVERY_TRIGGERS list does** | HIGH |

---

## 12. Recommendations (for fix synthesis, not remediation here)

1. **Reorder safety_plugin G01** so that `HardStopHandler.check(text)` runs FIRST. Or invoke `force_safe_mode` directly from each G01 early-return path. This closes B-1.
2. **Add safety gate to `RitualScheduler.execute_ritual`** before invoking `_callback`. Inject safe-mode handler so rituals skip during safe mode.
3. **Add safety gate to `sync_mood_to_redis`** (or to its callers) so mood-variant writes do not occur during HARD STOP.
4. **Implement `SafetyCoordinator`** as KNOWN-ISSUES.md PR-01 proposes — single source of truth for safe-mode state, with bidirectional sync between HardStopHandler and SafeModeController.
5. **Audit PersonaPlugin (post-P5 path)** to verify equivalent safety gates are wired.
6. **Audit recovery flow symmetry** — add `HardStopHandler.register_on_recovery(...)` so HardStopHandler-driven recovery also clears `SafeModeController.is_active` and `SessionSafetyState` flags.

---

## 13. Out-of-scope items

- Dynamic/runtime test execution of B-1 reproduction scenario (would require live hermes-agent + Discord/WhatsApp/Gmail integration).
- `src/hermes/plugins/persona_plugin.py` active path audit.
- `src/loops/discovery.py` and `src/self_improve/promotion.py` deeper integration audit beyond grep-sniffing.
- ADb verification: `audit-reports/P5/P5-FINAL-AUDIT/D04-safety-boundary.md` and `docs/setup-evidence/P4/audits/round-1/persona-safety-hardstop-consent.md` reference this same gap; this audit's findings align with those.

---

## 14. Conclusion

**Y-level safety boundaries (Y4 baseline, Y5 ceiling, Y6 impossible) are FULLY ENFORCED at the structural level.** Both the FSM (`yandere_fsm.py`) and the safety plugin G07 hold the line.

**HARD STOP completeness has a CONFIRMED RESIDUAL GAP (B-1 / PR-01).** When a HARD STOP keyword is matched by `safety_plugin.G01` exact or semantic lists, the early-return blocks the LLM call but does NOT activate `SafeModeController`. Downstream consumers that read only `SafeModeController.is_active` will incorrectly believe safe mode is off. Defense-in-depth in `PunishmentEngine` and `YandereEngine` masks the gap because those also check `HardStopHandler.is_safe` directly, but new consumers (DriftCorrector, future engines) are unprotected.

**Ritual and mood injection bypass HARD STOP independently**, since neither `RitualScheduler.execute_ritual` nor `MoodEngine.sync_mood_to_redis` reads any safety flag.

The PR-01 resolution note in KNOWN-ISSUES.md understates the residual: even after the bridge callback, the safety_plugin-driven code path does not reach it. The SafetyCoordinator abstraction recommended for P5 is the correct structural fix.
