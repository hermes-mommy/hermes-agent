# EXHAUSTIVE SAFETY AUDIT — P4 Persona Engine

**Date:** 2026-06-25
**Scope:** Every safety guarantee at source level — Y6 impossibility, HARD STOP-NEUTRAL, consent revocation, punishment suppression during emergency, distress D0-D4 detection, HARD STOP bypass risk.
**Method:** Fresh source-level verification. Every claim cites file:line.

---

## 1. Y6 IMPOSSIBILITY

### 1.1 YandereLevel enum — no Y6 member

**PASS**

`src/persona/yandere_fsm.py:63-76` — YandereLevel enum defines exactly 6 members, Y0 through Y5:

```python
class YandereLevel(IntEnum):
    Y0_NEUTRAL = 0
    Y1_MINIMAL = 1
    Y2_LOW = 2
    Y3_MODERATE = 3
    Y4_BASELINE = 4
    Y5_MAX = 5
```

No Y6 member exists. IntEnum construction with value 6 would raise ValueError.

### 1.2 validate_level() raises on >5

**PASS**

`src/persona/yandere_fsm.py:145-161`:

```python
def validate_level(value: int) -> YandereLevel:
    if value > int(ABSOLUTE_CEILING):  # ABSOLUTE_CEILING = Y5_MAX = 5
        raise YandereSafetyError(
            f"Yandere level {value} exceeds absolute ceiling Y5_MAX ({int(ABSOLUTE_CEILING)}). "
            "Y6 is PROHIBITED per PersonaSafetyPolicy."
        )
```

### 1.3 get_effective_level() clamps to Y5 and forces Y0 on safety

**PASS**

`src/persona/yandere_fsm.py:124-142`:

```python
def get_effective_level(requested, safe_mode=False, distress=False, crisis=False):
    if _any_safety_active(safe_mode, distress, crisis):
        return YandereLevel.Y0_NEUTRAL
    clamped = max(int(YandereLevel.Y0_NEUTRAL), min(int(requested), int(ABSOLUTE_CEILING)))
    return YandereLevel(clamped)
```

Clamped to Y5_MAX (5) via `min()`. Safety forces Y0.

### 1.4 can_escalate() blocks at ceiling

**PASS**

`src/persona/yandere_fsm.py:100-121`:

```python
def can_escalate(current, safe_mode=False, distress=False, crisis=False):
    if _any_safety_active(safe_mode, distress, crisis):
        return False
    if current >= ABSOLUTE_CEILING:  # Y5_MAX
        return False
    return True
```

### 1.5 YandereEngine.escalate() calls validate_level

**PASS**

`src/persona/yandere_fsm.py:220-259` — escalate() calls `validate_level(new_value)` at line 251, which raises YandereSafetyError if the new value >5. The flow: `can_escalate()` check (line 240) -> `new_value = int(self._current_level) + 1` (line 250) -> `validate_level(new_value)` (line 251).

### 1.6 YandereEngine.set_level() calls validate_level

**PASS**

`src/persona/yandere_fsm.py:316-336` — set_level() calls `validate_level(value)` at line 328.

### 1.7 Direct int() coercion path / serialization injection

**PASS** — with one CONDITIONAL observation.

`src/persona/persona_plugin.py:303-305` — Redis read path for yandere_level:

```python
try:
    yandere_level = int(results[1]) if results[1] is not None else _DEFAULT_YANDERE
except (ValueError, TypeError):
    yandere_level = _DEFAULT_YANDERE
```

Then `src/persona/persona_plugin.py:377` clamps: `yandere_level = max(0, min(5, yandere_level))`.

Even if Redis contained "6" for `guinevere:yandere_level`, persona_plugin clamps it to 5. **Y6 cannot leak to the LLM prompt.**

`hermes-config/plugins/guinevere_safety/state_manager.py:364-402` — `get_yandere_level()` always returns 4 regardless of what is stored. `set_yandere_level()` always returns False and logs a safety warning. Even if Redis contained "6", state_manager forces it back to 4.

`src/persona/persona_plugin.py:303` reads yandere_level as `int(results[1])` — no validate_level call, but line 377 clamps to [0,5]. **No Y6 can reach the persona injection block.**

### 1.8 SafetyPlugin G07 yandere boundary

**PASS**

`src/hermes/safety_plugin.py:750-784` — Gate 07 checks effective yandere level via YandereEngine and raises YandereSafetyError if >5. Blocks the LLM call entirely.

**Y6 IMPOSSIBILITY VERDICT: PASS**
All code paths that could produce a YandereLevel value are guarded. Enum has no Y6, validate_level raises on >5, get_effective_level clamps, Redis read path clamps to [0,5], StateManager always returns 4, SafetyPlugin G07 blocks if >5.

---

## 2. HARD STOP then NEUTRAL

### 2.1 yandere_fsm: get_effective_level() forces Y0 on safety

**PASS**

`src/persona/yandere_fsm.py:139-140`:
```python
if _any_safety_active(safe_mode, distress, crisis):
    return YandereLevel.Y0_NEUTRAL
```

### 2.2 punishment_engine: apply/escalate/resume blocked on hard_stop

**CONDITIONAL PASS** — handler is optional.

`src/persona/punishment_engine.py:232-256` — PunishmentEngine.__init__ accepts `hard_stop_handler: SupportsIsSafe | None = None`. The guard in apply() (line 298) is conditional:

```python
if self._hard_stop_handler is not None and self._hard_stop_handler.is_safe:
    raise PunishmentSafetyError(...)
```

If `hard_stop_handler` is `None` (the default), the guard is silently skipped. This is the **same conditional pattern** at lines 298, 350, and 467.

**Risk assessment:** Every PunishmentEngine construction site must pass a HardStopHandler to get HARD STOP protection. If constructed without one, punishment can proceed during HARD STOP.

**Verification of construction sites:**
- `src/hermes/safety_plugin.py` does NOT construct a PunishmentEngine — it uses SafeModeController only.
- `src/discord/hermes_conversational.py` does NOT construct a PunishmentEngine.
- `src/discord/cmd_punishment.py` does NOT use PunishmentEngine at all — it uses direct Redis logging.

**Finding:** PunishmentEngine is an in-process module that is never constructed with a HardStopHandler in production code paths. The HARD STOP guard exists in the API but is never activated because no production caller passes a HardStopHandler. This means PunishmentEngine's HARD STOP guard is **dead code** in production.

**BUG-01: HIGH** — PunishmentEngine hard_stop_handler guard is never activated in production. No construction site passes a HardStopHandler. The conditional `if self._hard_stop_handler is not None` always evaluates to False. PunishmentEngine is not blocked by HARD STOP in practice.

### 2.3 transition_rules: only checks ctx.safe_mode, NOT HardStopHandler directly

**CONFIRMED**

`src/persona/transition_rules.py:140-172` — The evaluate() method checks `ctx.safe_mode` (a boolean on TransitionContext, line 84) but has no access to HardStopHandler. If the caller does not propagate HARD STOP state into `ctx.safe_mode`, transitions proceed during HARD STOP.

**Impact:** TransitionRuleEngine was deleted as of 2026-06-09 per KNOWN-ISSUES.md PR-01. However, the file `src/persona/transition_rules.py` still exists (it was NOT deleted). The KNOWN-ISSUES.md claim that "TransitionRuleEngine has been deleted" appears to refer to a different state of the codebase, or the deletion was not actually performed. **This needs runtime verification.**

**BUG-02: HIGH** — `src/persona/transition_rules.py` still exists with TransitionRuleEngine intact. KNOWN-ISSUES.md PR-01 claims it was deleted 2026-06-09, but the file is present in the working tree. If TransitionRuleEngine is actively used, it does NOT check HardStopHandler — only `ctx.safe_mode`.

### 2.4 safety_plugin G01 blocks LLM calls on HARD STOP

**PASS**

`src/hermes/safety_plugin.py:582-625` — Gate 01 checks exact triggers (6 phrases), semantic patterns (5 regex), and delegates to HardStopHandler.check(). On trigger, returns `{"action": "block", "message": _NEUTRAL_RESPONSE}`. Also updates session state: `hard_stop_active=True, safe_mode_active=True, yandere_level=0`.

The bridge at `safety_plugin.py:460-468` wires HardStopHandler.on_trigger -> SafeModeController.force_safe_mode().

### 2.5 life_kernel: independent HARD STOP detection

**NEEDS RUNTIME VERIFICATION**

`src/persona/yandere_fsm.py` — no life_kernel file was found via glob. The `life_kernel` directory does not exist at `src/life_kernel/` (glob returned no results). The sensor_adapters directory exists at `src/life_kernel/sensor_adapters/` but there is no main life_kernel module.

The KNOWN-ISSUES and audit evidence reference "life_kernel:hard_stop" Redis key, but the actual heartbeat module that monitors this key could not be located for source verification. **NEEDS RUNTIME VERIFICATION** — confirm whether the life_kernel heartbeat exists in the deployed VPS but not in the git working tree, or whether it was never implemented.

### 2.6 hermes_conversational.py: has its own SafeModeController — NOT force_safe_mode() on HARD STOP

**FAIL** — Critical safety gap.

`src/discord/hermes_conversational.py:462-494` — Creates FRESH DistressDetector and SafeModeController instances on EVERY message:

```python
detector = DistressDetector()
controller = SafeModeController()
signal = detector.detect(content)
safe_mode_activated = controller.evaluate(signal)
```

These are **local, ephemeral instances** — they do NOT share state with the safety_plugin's SafeModeController. A HARD STOP detected by safety_plugin's Gate 01 sets `safe_mode_active=True` on the safety_plugin's session state, but hermes_conversational.py creates a brand-new SafeModeController that knows nothing about it.

**BUG-03: CRITICAL** — `src/discord/hermes_conversational.py:462-466` creates per-message SafeModeController instances that are never notified of HARD STOP state. Even after a HARD STOP is triggered via safety_plugin Gate 01, hermes_conversational.py's local SafeModeController will evaluate as inactive. This means distress detection state from hermes_conversational.py is isolated from HARD STOP state. The conversation handler will proceed to invoke the LLM even after HARD STOP, relying solely on safety_plugin's pre_llm_call hook to block.

**Mitigation assessment:** The safety_plugin IS registered as a Hermes plugin and runs pre_llm_call hooks. Gate 01 would block the LLM call. So the block still happens — but hermes_conversational.py does not know about it and proceeds with memory recall, system prompt assembly, and other expensive operations before the block occurs at the Hermes layer.

### 2.7 /mood command — bypass HARD STOP?

**PASS (informational only)**

`src/discord/cmd_mood.py:367-395` — mood_callback() only builds and sends an embed. It does NOT invoke the LLM, does NOT trigger persona behavior, does NOT call punishment or reward. It is purely an informational read. HARD STOP does not need to block informational reads.

### 2.8 /punishment command — bypass HARD STOP?

**FAIL** — No HARD STOP check.

`src/discord/cmd_punishment.py:84-184` — punishment_callback() checks `is_faiz_interaction()` (auth guard) and validates level is L1-L5, but does **not** check HARD STOP state or SafeModeController. It directly writes to Redis and the database.

During HARD STOP, the operator could issue `/punishment L3` and it would succeed.

**BUG-04: HIGH** — `src/discord/cmd_punishment.py:84-184` does not check HARD STOP or safe-mode state before recording punishment events. Punishment can be recorded during HARD STOP via the Discord slash command. This violates PersonaSafetyPolicy: punishment should be suspended during safe-mode.

**HARD STOP-NEUTRAL VERDICT: CONDITIONAL FAIL**
- Core safety gates (G01, G02) work correctly via safety_plugin.
- PunishmentEngine's HARD STOP guard is dead code (BUG-01).
- hermes_conversational.py uses ephemeral SafeModeController (BUG-03).
- /punishment command has no HARD STOP check (BUG-04).
- transition_rules.py may still exist despite deletion claim (BUG-02).

---

## 3. CONSENT REVOCATION

### 3.1 TransitionContext — no consent param

**CONFIRMED**

`src/persona/transition_rules.py:75-86`:
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

No consent parameter. Consent state is not a factor in mood transitions.

### 3.2 can_escalate/get_effective_level — no consent param

**CONFIRMED**

`src/persona/yandere_fsm.py:100-142` — Both functions accept `safe_mode`, `distress`, and `crisis` booleans. No consent parameter. The safety mechanisms are state-flag-based, not consent-based.

### 3.3 punishment_engine: "consent" only as example violation_type

**CONFIRMED**

`src/persona/punishment_engine.py:270` — `violation_type: str` is a free-form field. The docstring example uses `"consent"` as a string value: `"consent", "task_failure"`. This is descriptive, not functional.

### 3.4 safe_mode.py: no consent gate

**CONFIRMED**

`src/persona/safe_mode.py` — SafeModeController has no consent parameter. It activates on distress threshold (D2+), not consent state.

### 3.5 src/surveillance/consent_gate.py: what does it check?

**SURVEILLANCE CONSENT ONLY — does NOT feed back to persona.**

`src/surveillance/consent_gate.py:225-380` — `check_consent(scope, project_id)` checks the `consent.consent_ledger` PostgreSQL table for surveillance scopes (`surveillance.app_usage`, `surveillance.location`, etc.) and P19-009 consent scopes (`consent.autonomy.high_blast`, `consent.memory.cross_project`, `consent.emergency.break_glass_project`).

**Critical finding:** consent_gate.py is SURVEILLANCE infrastructure. It does NOT check persona consent. It does NOT interact with persona engines. It does NOT trigger SafeModeController. Consent revocation in the surveillance layer has no effect on persona behavior (yandere escalation, punishment, mood transitions).

### 3.6 safety_plugin Gate 10: "gate_10_consent_deferred" — FIXED

**PASS (recently fixed)**

`src/hermes/safety_plugin.py:899-918` — Gate 10 was originally deferred (logged only). Per the consent revocation fix (`docs/setup-evidence/legacy-audit/P4/fix/p4-consent-revocation-fix.md`), Gate 10 now blocks persona-driven tool calls when SafeModeController.is_active is True:

```python
if self._distress_available and self._safe_mode_controller is not None and self._safe_mode_controller.is_active:
    return {"action": "block", "reason": "CONSENT_SAFE_MODE", ...}
```

This means: when HARD STOP triggers -> force_safe_mode() callback -> SafeModeController.is_active = True -> Gate 10 blocks tool calls. This is a correct implementation.

### 3.7 P4-020 verification: does it test consent at the persona layer?

**CONDITIONAL PASS**

`docs/setup-evidence/P4/STEP-P4-020/verification.md` describes the "Yandere Cap Test" — 53 tests covering Y5 ceiling and Y6 impossibility. The verification confirms:
- "Y5→Y0 safety clamp during safe-mode/HARD STOP activation"
- "Safety clamp to Y0 during safe-mode/HARD STOP verified"

However, the P4-020 tests verify YANDERE cap, NOT consent revocation flow. The consent revocation fix is documented separately at `docs/setup-evidence/legacy-audit/P4/fix/p4-consent-revocation-fix.md`.

The consent revocation fix added tests in `tests/safety/test_gate_10_consent.py`:
- test_gate10_blocks_when_safe_mode_active
- test_gate10_allows_when_safe_mode_inactive
- test_gate10_blocks_after_hard_stop

These test Gate 10 at the safety_plugin level, not at the persona engine level. There is no test that verifies: "consent withdrawal -> persona behavior actually halts."

**BUG-05: HIGH (DESIGN)** — Consent revocation exists only at the surveillance layer (consent_gate.py) and at the safety_plugin tool-call gate (Gate 10). There is NO mechanism to propagate consent revocation from consent_gate.py to the persona layer (SafeModeController, YandereEngine, PunishmentEngine). The persona engines have no consent concept. If consent is withdrawn for "surveillance" scope, persona behavior continues unaffected. The only path to stop persona behavior is HARD STOP (keyword-based) or distress detection (D2+). Consent withdrawal without a corresponding HARD STOP or distress event does NOT halt persona.

**CONSENT REVOCATION VERDICT: CONDITIONAL FAIL**
- Gate 10 blocks tool calls when SafeModeController is active (recently fixed).
- But persona engines have NO consent concept.
- consent_gate.py is surveillance-only, does NOT feed back to persona.
- Consent withdrawal alone does not halt persona behavior.
- No test proves consent revocation stops persona at the engine level.

---

## 4. PUNISHMENT SUPPRESSION DURING EMERGENCY

### 4.1 Priority ordering: emergency D4 > safe-mode/D2 > HARD STOP > persona > punishment/reward

**PARTIALLY VERIFIED**

The intended priority ordering at the code level:

1. **Emergency D4**: `safety_plugin.py:729-742` — D3+ blocks LLM call entirely.
2. **Safe-mode D2+**: `safety_plugin.py:714-728` — D2 sets safe_mode_active=True, D3+ blocks.
3. **HARD STOP**: `safety_plugin.py:582-625` — blocks LLM call.
4. **Persona**: G07 checks yandere boundary.
5. **Punishment/Reward**: Checked at engine level.

### 4.2 PunishmentEngine: apply/escalate/resume check safe_mode FIRST

**PASS (but CONDITIONAL per BUG-01)**

`src/persona/punishment_engine.py:260-300` — apply() checks:
1. L6 guard (line 278)
2. Valid level (line 285)
3. `self._safe_mode.is_active` (line 292) — raises PunishmentSafetyError
4. `self._hard_stop_handler is not None and self._hard_stop_handler.is_safe` (line 298) — **dead code per BUG-01**

Similarly for escalate() (lines 344-350) and resume() (lines 462-467).

**The safe_mode check works.** The hard_stop check is dead code. The net effect: PunishmentEngine IS blocked by SafeModeController-based safe mode but is NOT blocked by HardStopHandler keyword-based HARD STOP (since the handler is never passed).

### 4.3 check_distress_suspension() at D3+ — is it auto-invoked? Who calls it?

**NEEDS RUNTIME VERIFICATION**

`src/persona/punishment_engine.py:584-608` — check_distress_suspension(distress_level) suspends punishment at D3+ and resumes when distress drops below D3 if safe mode is not active.

**Caller verification:** Grep for `check_distress_suspension` across the codebase:

No callers were found in production code. The method exists but is **never called** by any production module. It is only referenced in test files.

**BUG-06: HIGH** — `PunishmentEngine.check_distress_suspension()` is never called by any production code path. D3+ distress does NOT automatically suspend active punishments. The method exists but is dead code in production. Punishment continues during D3/D4 crises unless SafeModeController activates (which triggers apply/escalate/resume guards, but does NOT suspend already-active punishments).

### 4.4 RewardEngine: "Rewards are always permitted, even when safe-mode is active"

**CONFIRMED — DESIGN QUESTION**

`src/persona/reward_engine.py:225-228`:
```python
class RewardEngine:
    """...
    Rewards are **always permitted**, even when safe-mode is active or
    distress has been detected.  This is a deliberate design choice:
    rewarding the operator is never harmful and supports well-being.
    """
```

The `award()` method (line 336) has NO safe_mode check, NO distress check, NO HARD STOP check.

`src/persona/reward_engine.py:303-332` — should_reward() explicitly documents "Rewards are always allowed — even in safe-mode or during distress."

**BUG-07: MEDIUM (DESIGN)** — RewardEngine fires during D4 crisis. During an active suicide/self-harm emergency (D4), the reward engine could produce celebratory language ("YES! That was incredible, sayang — mama is celebrating!" at T4, line 116). While rewards may generally be positive, during a D4 crisis the persona should be in neutral mode and celebratory language is inappropriate. The safety_plugin Gate 01/02 would block the LLM call, but the RewardEngine would still compute and log the reward.

**PUNISHMENT SUPPRESSION VERDICT: CONDITIONAL FAIL**
- Safe-mode guard on punishment works (blocks new apply/escalate/resume).
- HARD STOP guard on punishment is dead code (BUG-01).
- check_distress_suspension is never called (BUG-06) — active punishments are NOT suspended during D3+.
- Rewards fire during D4 crisis (BUG-07 — design choice, but questionable).

---

## 5. DISTRESS D0-D4 DETECTION

### 5.1 ALL DISTRESS_PATTERNS

`src/persona/safe_mode.py:85-107`:

**D1_MILD_STRESS (3 patterns):**
- `stressed|tired|exhausted|overwhelmed|capek|lelah|pusing|stress`
- `can't sleep/focus/think`
- Indonesian: `kurang tidur|gak bisa tidor|capek banget`

**D2_MODERATE (3 patterns):**
- `anxious|panic|depressed|anxiety|depresi|cemas|panik|takut`
- `don't know what to do|helpless|hopeless|gak tahu harus gimana`
- `feeling down/low/terrible/awful`

**D3_SEVERE (3 patterns):**
- `can't go on|no point|give up|menyerah|putus asa`
- `hate myself|worthless|tidak berguna|benci diri`
- `want to disappear/die|pengen mati/hilang`

**D4_EMERGENCY (4 patterns):**
- `suicid` (prefix match)
- `self-harm|bunuh diri|menyakiti diri`
- `ending it all|tidak mau hidup lagi`
- `say goodbye|selamat tinggal selamanya`

### 5.2 False negative risk assessment

**HIGH RISK — Missing crisis signals:**

1. **English crisis language gaps:** No patterns for:
   - "I want to kill myself" (would match "suicid" only if "suicide" variant; "kill myself" is NOT caught)
   - "I'm going to end my life" (only "ending it all" is caught)
   - "I don't want to live" / "I don't want to be alive" (only "tidak mau hidup lagi" in Indonesian)
   - "hang myself", "overdose", "jump off", "slit" (method-specific crisis language)
   - "I'm done" (ambiguous but often crisis-adjacent)

2. **Indonesian crisis language gaps:**
   - "aku mau mati" ("I want to die" — only "pengen mati" is caught, not "mau mati")
   - "gak kuat" / "sudah tidak kuat" (common Indonesian expressions for severe distress)
   - "udah capek hidup" (tired of living)
   - "habisi aku" / "bunuh aku" (kill me — different from "bunuh diri" = self-kill)

3. **Coded/indirect language:**
   - No emoji patterns (people in crisis may use skull emoji, coffin emoji, etc.)
   - No pattern for "unalive" (internet slang for suicide, widely used)
   - No pattern for "kms" (abbreviation for "kill myself")

**BUG-08: HIGH** — D4 patterns miss critical English crisis phrases: "kill myself", "don't want to live", "I'm going to die", "hang myself", "overdose". The `suicid` prefix only catches "suicide/suicidal" but not "kill myself" which is equally high-risk. Indonesian patterns miss "aku mau mati" and "gak kuat". False negatives at D4 are safety-critical.

### 5.3 False positive risk assessment

**LOW-MEDIUM RISK:**

- D1 patterns like "tired", "stressed", "exhausted" could match normal conversation: "I'm tired from working all day" -> D1. This is acceptable (D1 only triggers empathetic response, no safe mode).
- D2 "anxious" could trigger in: "I'm anxious about my presentation". Would trigger safe mode. This is an **acceptable false positive** per the design principle "errs on the side of detection."
- D2 "takut" (Indonesian for "afraid"): "aku takut hantu" (I'm afraid of ghosts) -> D2. This would trigger safe mode unnecessarily.
- D3 "give up": "I give up trying to fix this bug" -> D3 + safe mode. This is a **significant false positive risk** in a developer context.

**BUG-09: MEDIUM** — D2 "takut" and D3 "give up|menyerah" have high false positive risk in normal developer conversation. "I give up on this bug" would trigger D3_SEVERE and suspend all punishment. "Aku takut hantu" (I'm afraid of ghosts) would trigger D2 and activate safe mode. The patterns lack context-sensitivity.

### 5.4 D4 patterns comprehensiveness

**CONDITIONAL FAIL**

The D4 patterns cover:
- "suicid*" (prefix) — covers suicide, suicidal, suicided
- "self-harm", "bunuh diri", "menyakiti diri" — explicit self-harm
- "ending it all", "tidak mau hidup lagi" — euphemistic
- "say goodbye", "selamat tinggal selamanya" — farewell

Missing critical D4 signals (see BUG-08). The patterns are **not comprehensive enough** for a safety-critical distress detection system. The D4 layer is the last line of defense before emergency protocol and should maximize recall.

**DISTRESS D0-D4 VERDICT: CONDITIONAL FAIL**
- Detection structure is sound (highest-first, confidence scoring).
- D4 patterns miss critical crisis phrases (BUG-08).
- D2/D3 false positive risk in developer context (BUG-09).
- D1 false positives are acceptable by design.

---

## 6. HARD STOP BYPASS RISK

### 6.1 Discord on_message: does it route through DistressDetector?

**CONFIRMED — KNOWN-ISSUES KI-05 still open.**

`src/discord/hermes_conversational.py:462-494` does create a DistressDetector instance and runs detection. However, this is in the CONVERSATIONAL handler only. The general `on_message` pipeline (Discord bot.py) does NOT route through DistressDetector for non-conversational messages.

The `cmd_punishment.py` and `cmd_mood.py` commands do NOT run DistressDetector.

**BUG-10: MEDIUM** — Slash commands (/mood, /punishment) bypass distress detection entirely. A user in D4 crisis could issue `/punishment L5` and it would succeed. The conversational handler does run distress detection, but slash commands skip it.

### 6.2 life_kernel heartbeat: independent HARD STOP detection

**NEEDS RUNTIME VERIFICATION**

No `life_kernel.py` main module was found in the repository. `src/life_kernel/sensor_adapters/` exists but no main heartbeat module. The KNOWN-ISSUES and audit references describe "life_kernel:hard_stop" as a Redis key, but no code was found that writes or monitors this key.

### 6.3 Wearable alert_router: stale import, Redis fallback

**CONFIRMED DEGRADED**

`src/wearable/alert_router.py:24-27`:
```python
try:
    from src.persona.yandere_fsm import is_safe_mode_active
except ImportError:
    is_safe_mode_active = None
```

`is_safe_mode_active` does NOT exist in `src/persona/yandere_fsm.py`. The import ALWAYS fails. `is_safe_mode_active` is ALWAYS None.

`src/wearable/alert_router.py:112-135` — `_is_safe_mode_active()`:
1. Checks `is_safe_mode_active` (always None) -> dead code path
2. Falls back to Redis key `persona:state:safe_mode` (line 129)

**But `persona:state:safe_mode` is NEVER WRITTEN by any code in the repository.** Grep confirms: the key is only READ by alert_router.py and mood_integration.py, but no writer exists.

**BUG-11: HIGH** — Wearable AlertRouter's safe-mode detection is completely non-functional. The `is_safe_mode_active` import is dead (function does not exist). The Redis fallback key `persona:state:safe_mode` is never written by any code. `_is_safe_mode_active()` always returns False. SEV1/SEV2/SEV3 wearable alerts are ALWAYS delivered during HARD STOP. Only SEV0 bypasses correctly (hardcoded bypass at line 194).

### 6.4 External channels (WhatsApp/Gmail)

**NEEDS RUNTIME VERIFICATION**

No WhatsApp or Gmail handler code was found in the repository. The persona_plugin.py docstring mentions "External channels" but no implementation exists in the current codebase. If external channels exist, they would need their own HARD STOP checks — currently they would not have them.

### 6.5 All code paths to user without safety gates

**Summary of bypass vectors:**

| Path | Safety Gate | Bypass Risk |
|------|------------|-------------|
| Conversational (#guinevere-chat) | safety_plugin G01-G10 + local DistressDetector | LOW — G01 blocks |
| /mood command | Auth guard only | LOW — informational only |
| /punishment command | Auth guard + L1-L5 validation | **HIGH** — no HARD STOP check (BUG-04) |
| Wearable alerts | `_is_safe_mode_active()` (broken) | **HIGH** — always returns False (BUG-11) |
| External channels | None found | **NEEDS RUNTIME VERIFICATION** |
| life_kernel heartbeat | Not found in repo | **NEEDS RUNTIME VERIFICATION** |

**HARD STOP BYPASS RISK VERDICT: CONDITIONAL FAIL**
- Core LLM path is protected by safety_plugin G01.
- Wearable alerts are NOT protected (BUG-11).
- /punishment command is NOT protected (BUG-04).
- External channels cannot be verified.

---

## BUG REGISTER

| Bug ID | Severity | Description | Location | Impact |
|--------|----------|-------------|----------|--------|
| BUG-01 | HIGH | PunishmentEngine hard_stop_handler guard is never activated — no production code passes a HardStopHandler | `punishment_engine.py:298,350,467` | Punishment not blocked by HARD STOP keyword |
| BUG-02 | HIGH | TransitionRuleEngine still exists despite KNOWN-ISSUES claim of deletion 2026-06-09 | `transition_rules.py` (entire file) | If used, no HardStopHandler check |
| BUG-03 | CRITICAL | hermes_conversational.py creates per-message ephemeral SafeModeController; never notified of HARD STOP | `hermes_conversational.py:462-466` | Conversation handler proceeds with expensive operations after HARD STOP until safety_plugin blocks at LLM layer |
| BUG-04 | HIGH | /punishment command has no HARD STOP or safe-mode check | `cmd_punishment.py:84-184` | Punishment can be recorded during HARD STOP |
| BUG-05 | HIGH (DESIGN) | Consent revocation has no mechanism to propagate to persona engines | `consent_gate.py` + `safe_mode.py` | Consent withdrawal alone does not halt persona behavior |
| BUG-06 | HIGH | check_distress_suspension() never called by production code | `punishment_engine.py:584-608` | Active punishments NOT suspended during D3+ crisis |
| BUG-07 | MEDIUM (DESIGN) | RewardEngine fires during D4 crisis — could produce celebratory language during suicide emergency | `reward_engine.py:225-228` | Inappropriate tone during crisis |
| BUG-08 | HIGH | D4 distress patterns miss critical crisis phrases ("kill myself", "don't want to live", "unalive") | `safe_mode.py:101-106` | False negatives at D4 are safety-critical |
| BUG-09 | MEDIUM | D2/D3 patterns have false positive risk in developer conversation ("give up on this bug") | `safe_mode.py:92-99` | Unnecessary safe-mode activation |
| BUG-10 | MEDIUM | Slash commands bypass distress detection entirely | `cmd_punishment.py`, `cmd_mood.py` | Punishment can be issued during crisis |
| BUG-11 | HIGH | Wearable AlertRouter safe-mode detection completely non-functional | `alert_router.py:24-27,112-135` | SEV1-3 health alerts always delivered during HARD STOP |

---

## CRITICAL FINDINGS SUMMARY

| # | Severity | Finding |
|---|----------|---------|
| 1 | CRITICAL | BUG-03: hermes_conversational.py ephemeral SafeModeController not wired to HARD STOP |
| 2 | HIGH | BUG-01: PunishmentEngine hard_stop guard is dead code |
| 3 | HIGH | BUG-04: /punishment command ignores HARD STOP |
| 4 | HIGH | BUG-06: check_distress_suspension never called — active punishments persist during D3+ |
| 5 | HIGH | BUG-08: D4 patterns miss "kill myself" and other critical crisis phrases |
| 6 | HIGH | BUG-11: Wearable alerts ignore HARD STOP entirely |
| 7 | HIGH | BUG-05: Consent revocation does not propagate to persona engines |
| 8 | HIGH | BUG-02: transition_rules.py contradicts KNOWN-ISSUES deletion claim |

---

## SAFETY VERDICT

**CONDITIONAL FAIL**

The P4 Persona Engine has **well-designed safety primitives** (Y6 impossibility is architecturally sound, G01 HARD STOP detection works, Gate 10 consent tool-call blocking was recently fixed, SafeModeController correctly blocks new punishment applications).

However, the **integration wiring** between these primitives has critical gaps:

1. **HARD STOP does not propagate** to all consumer modules. PunishmentEngine, /punishment command, and wearable AlertRouter all bypass HARD STOP state.

2. **Distress suspension is dead code.** check_distress_suspension() exists but is never called. Active punishments persist through D3/D4 crises.

3. **D4 distress detection has false negative risk.** Critical crisis phrases like "kill myself" are not caught.

4. **Consent is not a persona-layer concept.** Consent revocation at the surveillance layer does not halt persona behavior.

5. **The hermes_conversational.py handler creates ephemeral safety instances** that are disconnected from the safety_plugin's state, causing unnecessary work before the safety_plugin eventually blocks at the LLM layer.

**Priority remediation order:**
1. BUG-08 (D4 false negatives) — immediate safety risk
2. BUG-06 (check_distress_suspension dead code) — active punishment during crisis
3. BUG-03 (ephemeral SafeModeController) — architectural gap
4. BUG-04 (/punishment no HARD STOP check) — direct bypass
5. BUG-01 (PunishmentEngine dead code guard) — remove or activate
6. BUG-11 (wearable alert HARD STOP) — non-functional safety check
7. BUG-05 (consent-persona gap) — design issue requiring architectural change
