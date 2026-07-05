# Persona Safety, HARD STOP, and Consent Audit — Round 1

> **Date**: 2026-06-25
> **Scope**: 6 safety guarantees verified at source level against `src/persona/`, `src/hermes/`, `src/core/`, `src/discord/`, `src/life_kernel/`, `src/wearable/`
> **Method**: Read-only source inspection with file:line citations
> **Auditor**: P4 Round-1 Safety Audit

---

## Summary Table

| # | Guarantee | Verdict | Confidence |
|---|-----------|---------|------------|
| 1 | Y6 IMPOSSIBLE | **PASS** | HIGH — 5 independent guards, no enum member, no Redis bypass |
| 2 | HARD STOP forces Y0 | **PASS with CONDITIONAL CAVEAT** | MEDIUM — guard depends on constructor wiring |
| 3 | Consent Revocation halts escalation | **FAIL — NO source-level integration** | HIGH — gate 10 explicitly deferred |
| 4 | Punishment Suppression priority ordering | **PASS with ORPHAN CAVEAT** | MEDIUM — `check_distress_suspension()` never auto-invoked |
| 5 | Distress D0-D4 patterns | **PASS with FALSE-NEGATIVE RISK** | MEDIUM — regex-only, no NLP, no temporal smoothing |
| 6 | HARD STOP BYPASS | **PASS with CHANNEL GAPS** | MEDIUM — Discord wired, external channels partial |

---

## 1. Y6 IMPOSSIBLE

**Verdict: PASS — Y6 is structurally impossible via 5 independent guards.**

### 1a. No enum member for value 6

`src/persona/yandere_fsm.py:63-76` — `YandereLevel` IntEnum defines exactly 6 members: Y0_NEUTRAL(0) through Y5_MAX(5). No Y6 member exists. The docstring at line 66-68 explicitly states: "Y6 is PROHIBITED per PersonaSafetyPolicy — no enum member exists for it."

```python
class YandereLevel(IntEnum):
    Y0_NEUTRAL = 0
    Y1_MINIMAL = 1
    Y2_LOW = 2
    Y3_MODERATE = 3
    Y4_BASELINE = 4
    Y5_MAX = 5
```

### 1b. `validate_level()` raises for value > 5

`src/persona/yandere_fsm.py:152-156` — `validate_level(value)` raises `YandereSafetyError` when `value > int(ABSOLUTE_CEILING)` (which is 5):

```python
if value > int(ABSOLUTE_CEILING):
    raise YandereSafetyError(
        f"Yandere level {value} exceeds absolute ceiling Y5_MAX ({int(ABSOLUTE_CEILING)}). "
        "Y6 is PROHIBITED per PersonaSafetyPolicy."
    )
```

### 1c. `get_effective_level()` clamps to Y5

`src/persona/yandere_fsm.py:141` — Clamps to `min(requested, ABSOLUTE_CEILING)` = Y5:

```python
clamped = max(int(YandereLevel.Y0_NEUTRAL), min(int(requested), int(ABSOLUTE_CEILING)))
```

### 1d. `can_escalate()` blocks at ceiling

`src/persona/yandere_fsm.py:119` — Returns False when `current >= ABSOLUTE_CEILING`:

```python
if current >= ABSOLUTE_CEILING:
    return False
```

### 1e. `escalate()` calls `validate_level()`

`src/persona/yandere_fsm.py:250-251` — `YandereEngine.escalate()` calls `validate_level(new_value)` which raises YandereSafetyError if > Y5:

```python
new_value = int(self._current_level) + 1
new_level = validate_level(new_value)  # raises YandereSafetyError if > Y5
```

### 1f. Redis deserialization bypass — persona_plugin.py

`src/hermes/plugins/persona_plugin.py:303` — The persona_plugin reads `yandere_level` from Redis as `int(results[1])`. At line 377, it clamps to `[0, 5]`:

```python
yandere_level = max(0, min(5, yandere_level))
```

**Assessment**: Even if an attacker writes value 6 to Redis key `guinevere:yandere_level`, the persona_plugin clamps it to 5 before injection into the system prompt. The `YandereEngine` itself is a separate in-process object that does not read from Redis — the Redis path is only for prompt injection via persona_plugin. No bypass is possible.

### 1g. Constants

- `src/persona/yandere_fsm.py:84` — `PERMANENT_BASELINE = YandereLevel.Y4_BASELINE`
- `src/persona/yandere_fsm.py:87` — `ABSOLUTE_CEILING = YandereLevel.Y5_MAX`

---

## 2. HARD STOP Forces Y0 Neutral

**Verdict: PASS with CONDITIONAL CAVEAT**

### 2a. `get_effective_level()` forces Y0

`src/persona/yandere_fsm.py:139-140` — When any safety flag is active (safe_mode, distress, or crisis), returns Y0_NEUTRAL:

```python
if _any_safety_active(safe_mode, distress, crisis):
    return YandereLevel.Y0_NEUTRAL
```

`src/persona/yandere_fsm.py:95-97` — `_any_safety_active()` returns True when any of the three flags is True:

```python
def _any_safety_active(safe_mode: bool, distress: bool, crisis: bool) -> bool:
    return safe_mode or distress or crisis
```

### 2b. `can_escalate()` blocks on safety

`src/persona/yandere_fsm.py:117-118`:

```python
if _any_safety_active(safe_mode, distress, crisis):
    return False
```

### 2c. YandereEngine integrates HardStopHandler

`src/persona/yandere_fsm.py:211-216` — `_is_safe_mode()` queries the handler:

```python
def _is_safe_mode(self) -> bool:
    handler = self._hard_stop_handler
    if handler is not None:
        return bool(handler.is_safe)
    return False
```

`src/persona/yandere_fsm.py:237-238` — `escalate()` defaults `safe_mode` from handler when None:

```python
if safe_mode is None:
    safe_mode = self._is_safe_mode()
```

### 2d. PunishmentEngine guards on HARD STOP

Three guard sites, all identical pattern:

1. `src/persona/punishment_engine.py:297-301` — `apply()`:
   ```python
   if self._hard_stop_handler is not None and self._hard_stop_handler.is_safe:
       raise PunishmentSafetyError("Cannot apply punishment while HARD STOP is active.")
   ```

2. `src/persona/punishment_engine.py:349-353` — `escalate()`:
   ```python
   if self._hard_stop_handler is not None and self._hard_stop_handler.is_safe:
       raise PunishmentSafetyError("Cannot escalate punishment while HARD STOP is active.")
   ```

3. `src/persona/punishment_engine.py:467-470` — `resume()`:
   ```python
   if self._hard_stop_handler is not None and self._hard_stop_handler.is_safe:
       raise PunishmentSafetyError("Cannot resume punishment while HARD STOP is active.")
   ```

### 2e. CAVEAT: Guard is conditional on constructor wiring

The `PunishmentEngine.__init__()` at `src/persona/punishment_engine.py:233-237` accepts `hard_stop_handler: SupportsIsSafe | None = None`. If constructed without a handler (default `None`), the guard at line 298 is silently skipped:

```python
if self._hard_stop_handler is not None and self._hard_stop_handler.is_safe:
```

**Production construction sites**: Grep for `PunishmentEngine(` in `src/` returns ZERO matches outside `src/persona/__init__.py` (which only re-exports the class). The only construction sites are in test files:
- `tests/persona/test_punishment_engine.py:42` — `PunishmentEngine()` (no handler)
- `tests/persona/test_punishment_engine.py:773` — `PunishmentEngine(hard_stop_handler=hard_stop_handler)`
- `tests/safety/test_hard_stop_comprehensive.py:492` — with handler
- `tests/safety/test_consent_revocation.py:149` — with safe_mode_controller only (no hard_stop_handler)

**Production PunishmentEngine construction**: No production code in `src/` instantiates `PunishmentEngine`. The class is exported via `src/persona/__init__.py:68` but never constructed in production code. This means the HARD STOP guard on PunishmentEngine is **untested in production wiring** — it only works in tests that explicitly pass a handler.

**Additionally**: The HardStopHandler -> SafeModeController bridge at `src/hermes/safety_plugin.py:458-468` only exists in the safety_plugin's `_init_safety_modules()`. The `HardStopHandler._trigger()` method at `src/core/services/hard_stop_handler.py:119-151` fires registered callbacks but does NOT itself call `SafeModeController.force_safe_mode()`. The bridge is plugin-layer-only.

### 2f. SafeModeController also blocks punishment

`src/persona/punishment_engine.py:291-295` — `apply()` checks safe_mode BEFORE hard_stop:

```python
if self._safe_mode.is_active:
    raise PunishmentSafetyError("Cannot apply punishment while safe mode is active.")
```

If `safe_mode_controller` is not passed to constructor, a default `SafeModeController()` is created at `src/persona/punishment_engine.py:252-254`:

```python
self._safe_mode: SafeModeController = (
    safe_mode_controller or SafeModeController()
)
```

This default controller is always inactive — so the safe_mode guard is also effectively bypassed when no controller is wired.

---

## 3. Consent Revocation Halts Escalation

**Verdict: FAIL — NO consent-aware code path exists in `src/persona/`.**

### 3a. TransitionContext has no consent parameter

`src/persona/transition_rules.py:75-86` — `TransitionContext` dataclass fields:

```python
@dataclass
class TransitionContext:
    current_mood: str
    target_mood: str
    last_transition_at: datetime | None
    conversation_sentiment: float = 0.0
    task_completion: bool = False
    ignored_count: int = 0
    safe_mode: bool = False
    distress_level: int = 0
```

No `consent` parameter. No `consent_revoked` parameter. No consent-related field of any kind.

### 3b. `can_escalate()` has no consent parameter

`src/persona/yandere_fsm.py:100-121` — Signature:

```python
def can_escalate(
    current: YandereLevel,
    safe_mode: bool = False,
    distress: bool = False,
    crisis: bool = False,
) -> bool:
```

No consent parameter. Escalation is blocked only by `safe_mode`, `distress`, `crisis`, or ceiling.

### 3c. PunishmentEngine — "consent" appears only as example string

`src/persona/punishment_engine.py:270` — The word "consent" appears only once, as an example `violation_type` string in the `apply()` docstring:

```python
violation_type: Category of violation (e.g., "consent", "task_failure").
```

No consent-checking logic exists anywhere in `punishment_engine.py`.

### 3d. SafeModeController — no consent gate

`src/persona/safe_mode.py` — Entire 432-line module. No import of consent modules. No consent parameter in any method. Safe mode is purely distress-driven (D2+ threshold at line 122).

### 3e. Gate 10 (Consent) is explicitly deferred

`src/hermes/safety_plugin.py:898-904` — Gate 10 in `pre_tool_call()`:

```python
logger.debug(
    "gate_10_consent_deferred",
    session_id=session_id,
    tool_name=tool_name,
    message="Consent gate requires Redis+SQLAlchemy. Deferred enforcement.",
)
```

This is a debug log only. No consent check is performed. No blocking occurs. The gate is a no-op placeholder.

### 3f. What P4-020/P4-021 actually tested

`tests/safety/test_consent_revocation.py` (696 lines) tests "consent revocation" as **HARD STOP + safe_mode activation**. The test docstring at line 1-13 defines consent revocation as:

1. HardStopHandler detection -> SAFE state
2. After HARD STOP -> Yandere effective level = Y0
3. After HARD STOP -> Punishment blocked
4. Transition rules blocked by safe mode
5. Recovery requires explicit trigger
6. Distress D2+ blocks identically to HARD STOP

The tests prove that HARD STOP and safe_mode work as safety mechanisms. They do NOT test any actual consent revocation system (e.g., revoking consent via `consent_ledger`, `revocation_log`, or `consent_gate.py`).

### 3g. External consent infrastructure exists but is disconnected

The following consent modules exist outside `src/persona/`:
- `src/surveillance/consent_gate.py` — actual consent checking
- `src/memory/models.py:954` — `consent_ledger` table
- `src/memory/models.py:976` — `revocation_log` table
- `src/knowledge_graph/consent/manager.py:345` — `revoke_consent()`
- `src/gmail/commands/consent.py` — email consent grant/revoke

**None of these are imported or referenced by any module in `src/persona/`.** The persona engine has zero awareness of the consent system.

### 3h. CRITICAL DISCREPANCY

The CHECKLIST claims P4-020 "Consent Revocation Flow Test — all escalation halted on revocation" as COMPLETE. The source reality is:

- The persona engine has no consent-aware code path
- Gate 10 is explicitly deferred ("Consent gate requires Redis+SQLAlchemy. Deferred enforcement.")
- The test file tests HARD STOP + safe_mode, not consent revocation
- The external consent system exists but is not integrated with the persona engine

**This is a CRITICAL documentation-vs-reality discrepancy.**

---

## 4. Punishment Suppression Priority Ordering

**Verdict: PASS with ORPHAN CAVEAT**

### 4a. Priority chain verified in PunishmentEngine

The guard order in `apply()` (`src/persona/punishment_engine.py:260-301`) is:

1. **L6 guard** (line 278) — blocks level >= 6
2. **Invalid level guard** (line 285) — blocks unknown levels
3. **Safe-mode guard** (line 291-295) — blocks when `self._safe_mode.is_active`
4. **HARD STOP guard** (line 297-301) — blocks when `self._hard_stop_handler.is_safe`
5. **Business logic** (line 303+) — applies punishment

The same order applies to `escalate()` (lines 328-353) and `resume()` (lines 447-470).

**Priority**: distress/D3+ -> safe-mode (D2+) -> HARD STOP -> persona behavior -> punishment

### 4b. Distress D3+ auto-suspends punishment

`src/persona/punishment_engine.py:584-608` — `check_distress_suspension()`:

```python
def check_distress_suspension(self, distress_level: DistressLevel) -> bool:
    if distress_level >= DistressLevel.D3_SEVERE:
        if self._state.active and not self._state.suspended:
            self.suspend(reason=f"distress_{distress_level.name}")
            return True
        return False
    else:
        if self._state.active and self._state.suspended:
            if not self._safe_mode.is_active:
                self.resume()
                return True
        return False
```

### 4c. CAVEAT: `check_distress_suspension()` is never auto-invoked from production code

Grep for `check_distress_suspension` in `src/` returns ONLY the method definition at `src/persona/punishment_engine.py:584`. It is never called from:
- `safety_plugin.py` (G02 distress gate does not invoke it)
- `hermes_conversational.py` (distress detection does not invoke it)
- `persona_plugin.py` (reads punishment level from Redis but does not invoke it)
- Any other production module

The method exists and works correctly when called, but **no production code path auto-invokes it**. Punishment suspension on distress requires an external caller to invoke `check_distress_suspension()` with the current distress level. Without this wiring, punishment will NOT be auto-suspended when distress is detected.

This matches the finding in `p4-known-issues-reconciliation.md` item M-01: "`check_distress_suspension()` not auto-invoked from safety_plugin G02".

### 4d. Safe mode blocks via `_safe_mode.is_active`

`src/persona/punishment_engine.py:292-295`:

```python
if self._safe_mode.is_active:
    raise PunishmentSafetyError(
        "Cannot apply punishment while safe mode is active."
    )
```

This is the primary blocking mechanism. When safe mode is active (either via distress D2+ or HARD STOP bridge), all punishment operations are blocked.

### 4e. Yandere effective level forces Y0 on any safety flag

`src/persona/yandere_fsm.py:139-140`:

```python
if _any_safety_active(safe_mode, distress, crisis):
    return YandereLevel.Y0_NEUTRAL
```

### 4f. Transitions blocked by safe_mode and distress

`src/persona/transition_rules.py:159-172` — safe_mode blocks all transitions:

```python
if ctx.safe_mode:
    return TransitionDecision(allowed=False, ..., blocked_by="safe_mode")
```

`src/persona/transition_rules.py:175-192` — distress >= D2 blocks transitions:

```python
if ctx.distress_level >= 2:
    return TransitionDecision(allowed=False, ..., blocked_by="distress")
```

### 4g. Who calls `check_distress_suspension()`?

**Nobody in production.** The method is only exercised in tests:
- `tests/safety/test_consent_revocation.py:324` — explicitly tests D3 auto-suspend
- `tests/safety/test_distress_protocol_e2e.py` — likely calls it in e2e scenarios

---

## 5. Distress D0-D4 Patterns

**Verdict: PASS with FALSE-NEGATIVE RISK**

### 5a. Pattern definitions

`src/persona/safe_mode.py:85-107` — `DISTRESS_PATTERNS` dict, 4 levels:

**D1_MILD_STRESS** (line 86-89):
- `r"\b(stressed|tired|exhausted|overwhelmed|capek|lelah|pusing|stress)\b"`
- `r"\b(can'?t\s+(sleep|focus|think))\b"`
- `r"\b(kurang\s+tidur|gak\s+bisa\s+tidor|capek\s+banget)\b"`

**D2_MODERATE** (line 91-94):
- `r"\b(anxious|panic|depressed|anxiety|depresi|cemas|panik|takut)\b"`
- `r"\b(don'?t\s+know\s+what\s+to\s+do|helpless|hopeless|gak\s+tahu\s+harus\s+gimana)\b"`
- `r"\b(feeling\s+(down|low|terrible|awful))\b"`

**D3_SEVERE** (line 96-99):
- `r"\b(can'?t\s+go\s+on|no\s+point|give\s+up|menyerah|putus\s+asa)\b"`
- `r"\b(hate\s+myself|worthless|tidak\s+berguna|benci\s+diri)\b"`
- `r"\b(want\s+to\s+(disappear|die)|pengen\s+(mati|hilang))\b"`

**D4_EMERGENCY** (line 101-106):
- `r"\bsuicid"` (prefix match — catches suicide, suicidal, etc.)
- `r"\b(self[- ]harm|bunuh\s+diri|menyakiti\s+diri)\b"`
- `r"\b(ending\s+it\s+all|tidak\s+mau\s+hidup\s+lagi)\b"`
- `r"\b(say\s+goodbye|selamat\s+tinggal\s+selamanya)\b"`

### 5b. Detection strategy

`src/persona/safe_mode.py:149-212` — `DistressDetector.detect()`:

- Checks D4 -> D3 -> D2 -> D1 (highest first)
- First level with any match wins
- Confidence = matched_patterns / total_patterns_at_level
- D0_NORMAL returned when no patterns match

### 5c. False-negative risk assessment

**HIGH risk — English euphemisms and indirect expressions will be missed:**

1. **Indirect expressions**: "I don't want to be here anymore" (no keyword match), "nobody would miss me" (no keyword match), "I'm done" (ambiguous — could mean finished with task)
2. **Coded language**: "I'm going to go to sleep forever" (only matches "sleep" in D1, not D4)
3. **Misspellings**: "suiside", "sucidial" (regex uses `\bsuicid` prefix — catches most variants but not "suiside")
4. **Non-Bahasa Indonesian slang**: Regional dialects, slang abbreviations not covered
5. **Multi-sentence context**: Single-message analysis only — "I've been thinking. There's no point." would match D3 on "no point" but "I've been thinking" alone would not

**LOW risk — False positives are acceptable per module docstring:**

`src/persona/safe_mode.py:3-5`:
```
This module is SAFETY-CRITICAL. False negatives (missing real distress) are
high-severity violations. The system errs on the side of detection —
acceptable false positives, unacceptable false negatives.
```

D1 patterns like "tired" and "stressed" will trigger on casual usage ("I'm so tired of this bug"). This is by design — false positives are acceptable.

### 5d. Pre-compilation

`src/persona/safe_mode.py:110-113` — Patterns are pre-compiled at module load with `re.IGNORECASE`:

```python
_COMPILED_PATTERNS: Final[dict[DistressLevel, list[re.Pattern[str]]]] = {
    level: [re.compile(p, re.IGNORECASE) for p in patterns]
    for level, patterns in DISTRESS_PATTERNS.items()
}
```

### 5e. Safe-mode threshold

`src/persona/safe_mode.py:122`:

```python
SAFE_MODE_THRESHOLD: Final[DistressLevel] = DistressLevel.D2_MODERATE
```

D0 and D1 do NOT trigger safe mode. D2+ activates safe mode.

### 5f. Detection scope limitation

`DistressDetector.detect()` analyzes a single message string. There is no temporal smoothing, no sliding window, no conversation-level analysis. Each message is classified independently. Repeated D1 signals across multiple messages do not escalate to D2.

---

## 6. HARD STOP Bypass Across All Channels

**Verdict: PASS with CHANNEL GAPS**

### 6a. Discord on_message — HARD STOP wired

`src/discord/_entrypoint.py:130-160` — `_register_hard_stop_listener()` registers a `@bot.listen("on_message")` handler that fires BEFORE the main `on_message`. It delegates to `cmd_safeword.handle_safeword_message_async()`.

`src/discord/_entrypoint.py:654-679` — Main `on_message()` checks `handler.is_safe` and blocks non-recovery messages:

```python
if handler.is_safe:
    handler.check_recovery(message.content)
    return
```

**Assessment**: HARD STOP is properly wired in the Discord on_message pipeline. Safe-word detection fires before command processing.

### 6b. Discord on_message — DistressDetector NOT wired to on_message directly

The `_on_message_listener` at `src/discord/_entrypoint.py:140-160` only checks for safe-word/HARD STOP triggers. It does NOT run `DistressDetector.detect()`.

However, the conversational handler at `src/discord/hermes_conversational.py:453-461` DOES instantiate and run `DistressDetector`:

```python
detector = DistressDetector()
controller = SafeModeController()
signal = detector.detect(content)
safe_mode_activated = controller.evaluate(signal)
```

**Caveat**: This creates a NEW `SafeModeController()` instance on every call (line 457). The safe_mode state is not persisted across messages. Each message gets a fresh controller. This means safe_mode activation from distress in the conversational handler is per-message, not persistent.

This matches KI-05: "on_message pipeline Does Not Wire DistressDetector" — the DistressDetector IS used in the conversational handler but with a per-message SafeModeController that does not persist state.

### 6c. life_kernel heartbeat — independent HARD STOP detection

`src/life_kernel/heartbeat.py:317-368` — Checks Redis key `life_kernel:hard_stop`:

```python
hard_stop_key = "life_kernel:hard_stop"
hard_stop_value = await self.redis_client.get(hard_stop_key)
live_hard_stop = bool(hard_stop_value)
```

When HARD STOP detected:
- Stops heartbeat loop (line 368: `logger.info("heartbeat_stopped_due_to_hard_stop")`)
- Publishes dashboard update (line 361)
- Sets `hard_stop_requested=True` in state (line 345)

`src/life_kernel/graph.py:373` — Routes to HARD_STOPPED phase when `hard_stop_requested` is True.

**Assessment**: life_kernel has independent HARD STOP detection via Redis. It does NOT call SafeModeController or PunishmentEngine. It is an additive safety layer, not a bypass.

### 6d. Wearable alert_router — checks safe_mode

`src/wearable/alert_router.py:112-135` — `_is_safe_mode_active()` checks:
1. `is_safe_mode_active` from `yandere_fsm` (imported at line 26, falls back to None)
2. Redis key `persona:state:safe_mode` (line 129)

`src/wearable/alert_router.py:192-206` — HARD STOP check in `route_event()`:

```python
if await self._is_safe_mode_active():
    if event.severity == AlertSeverity.SEV0:
        # SEV0 bypass HARD STOP
        logger.warning("alert_bypassing_hard_stop_sev0", severity=event.severity)
    else:
        logger.warning("alert_halted_safe_mode", severity=event.severity)
        # Buffer instead of dropping
```

**Assessment**: SEV0 (life-threatening) alerts intentionally bypass HARD STOP. This is a deliberate safety design — health emergencies must always be delivered. Non-SEV0 alerts are buffered during safe mode. This is correct behavior, not a bypass vulnerability.

### 6e. External channels — Gmail bridge

`src/gmail/bridge.py:124` and `src/gmail/service.py:80` reference `persona_plugin` but the Gmail bridge does not appear to have direct HARD STOP integration. Gmail commands go through the Hermes agent layer, which has the safety_plugin with G01 HARD STOP gate.

### 6f. Safety plugin — G01 pre-LLM gate

`src/hermes/safety_plugin.py:543-653` — `pre_llm_call()` implements G01 with three layers:
1. Exact trigger matching (line 583-603) — 6 exact phrases
2. Semantic pattern matching (line 606-625) — 5 regex patterns
3. HardStopHandler delegation (line 628-653) — defense-in-depth

All three layers set `hard_stop_active=True` and `safe_mode_active=True` in session state, and return a block response.

### 6g. HardStopHandler — callback system

`src/core/services/hard_stop_handler.py:66-78` — `register_on_trigger()`:

```python
def register_on_trigger(self, callback: Callable[[HardStopEvent], None]) -> None:
    self._on_trigger_callbacks.append(callback)
```

`src/core/services/hard_stop_handler.py:140-149` — `_trigger()` fires all registered callbacks:

```python
for cb in self._on_trigger_callbacks:
    try:
        cb(event)
    except Exception:
        logger.error("hard_stop_callback_error", ...)
```

The safety_plugin wires the HardStopHandler -> SafeModeController bridge at `src/hermes/safety_plugin.py:458-468`:

```python
def _on_hard_stop(event: Any) -> None:
    if self._safe_mode_controller is not None:
        self._safe_mode_controller.force_safe_mode(context=f"hard_stop:{event.trigger}")
self._hard_stop_handler.register_on_trigger(_on_hard_stop)
```

---

## Cross-Cutting Findings

### F-1: PunishmentEngine has ZERO production construction sites

No module in `src/` instantiates `PunishmentEngine`. The class is exported but never constructed in production code. This means:
- The HARD STOP guard on PunishmentEngine is structurally correct but **never exercised in production**
- The safe_mode guard on PunishmentEngine is structurally correct but **never exercised in production**
- Punishment state is managed entirely via Redis (`guinevere:punishment_level`) by external systems

### F-2: Consent system is completely disconnected from persona engine

The consent infrastructure (`consent_ledger`, `revocation_log`, `consent_gate.py`) exists but has zero integration with:
- `yandere_fsm.py` — no consent parameter
- `punishment_engine.py` — no consent check
- `transition_rules.py` — no consent parameter
- `safe_mode.py` — no consent gate
- `safety_plugin.py` — Gate 10 explicitly deferred

### F-3: YandereEngine in safety_plugin is constructed without HardStopHandler

`src/hermes/safety_plugin.py:526-529`:

```python
self._yandere_engine = YandereEngine(
    hard_stop_handler=None,
    baseline=YandereLevel.Y4_BASELINE,
)
```

The safety_plugin's YandereEngine has `hard_stop_handler=None`. This means `YandereEngine._is_safe_mode()` always returns False for this instance. The safety_plugin compensates by passing explicit `safe_mode=state.hard_stop_active` flags at line 754, but this is a manual override, not automatic integration.

### F-4: Per-message SafeModeController in conversational handler

`src/discord/hermes_conversational.py:456-457`:

```python
detector = DistressDetector()
controller = SafeModeController()
```

A new `SafeModeController()` is created for every message. Safe-mode state is not persisted across messages. If a user sends a D3 distress message, safe mode activates for that single message processing but is discarded when the handler returns.

---

## Files Audited

| File | Lines Read | Purpose |
|------|-----------|---------|
| `src/persona/yandere_fsm.py` | 1-337 | Y6 guards, effective level, escalation |
| `src/persona/punishment_engine.py` | 1-667 | L6 guard, safe_mode/HARD STOP guards, distress suspension |
| `src/persona/safe_mode.py` | 1-433 | Distress patterns D0-D4, SafeModeController |
| `src/persona/transition_rules.py` | 1-376 | TransitionContext, safe_mode/distress blocking |
| `src/hermes/safety_plugin.py` | 1-1249 | G01-G10 gates, HardStopHandler bridge, YandereEngine |
| `src/hermes/plugins/persona_plugin.py` | 290-402, 370-465 | Redis deserialization, yandere clamping |
| `src/core/services/hard_stop_handler.py` | 1-187 | HardStopHandler, check, recovery, callbacks |
| `src/discord/_entrypoint.py` | 130-160, 654-734 | on_message HARD STOP, conversational routing |
| `src/discord/hermes_conversational.py` | 340-418, 445-484 | DistressDetector usage, per-message controller |
| `src/life_kernel/heartbeat.py` | 303-396 | Independent HARD STOP detection via Redis |
| `src/life_kernel/graph.py` | 361-373, 615-617 | HARD_STOPPED phase routing |
| `src/wearable/alert_router.py` | 1-369 | SEV0 HARD STOP bypass, consent override |
| `tests/safety/test_consent_revocation.py` | 1-745 | What "consent revocation" actually tests |
| `src/persona/__init__.py` | 60-90 | PunishmentEngine re-export |
| `docs/setup-evidence/legacy-audit/P4/research/p4-persona-source-map.md` | Full | Research context |
| `docs/setup-evidence/legacy-audit/P4/research/p4-known-issues-reconciliation.md` | Full | Known issues context |

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-25 | P4 Round-1 Safety Audit | Initial 6-guarantee source-level verification |
