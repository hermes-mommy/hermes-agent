# Lane C (P4 Persona/Consent Fix) — Consent & Safety Boundaries Audit

**Auditor:** Independent auditor (Round 1)
**Date:** 2026-06-27
**Scope:** 5 files — `src/hermes/plugins/persona_plugin.py`, `src/discord/cmd_consent.py`,
`src/persona/safe_mode.py`, `src/persona/yandere_fsm.py`, `src/hermes/safety_plugin.py`
**Audit Type:** Implementation audit (post-fix verification)

---

## Executive Summary

| Dimension | Verdict | Worst Severity |
|---|---|---|
| Consent enforcement on revocation | POOR — fail-open by design | **CRITICAL** |
| HARD STOP gate | OK at plugin layer, but relies on shared Redis key only | HIGH |
| Y4/Y5/Y6 boundary | Well-implemented at FSM; Y6 impossible by enum absence | LOW |
| Fail-open vs fail-closed | **Fail-open everywhere for persona injection** | CRITICAL |
| Revocation cascade | Partially implemented — pub/sub only, no subscriber | HIGH |
| Safety coordination (SafeModeController + HARD STOP) | Wired correctly via callback bridge | LOW |

**Net verdict:** The structural shell of the consent/safety boundary is sound — Y6 is genuinely
impossible, safe mode is wired into HARD STOP via callback, and forbidden patterns block LLM
output. However, the consent **revocation cascade** is half-built: `cmd_consent.revoke` publishes
to `consent:revoked`, but `PersonaPlugin` reads the **key** `consent:grants` (cross-DB even: DB0 in
plugin vs DB0 in cmd_consent, both same key, fine) and never subscribes to the pub/sub channel —
so a revoked consent is only enforced on the *next* pre-LLM call, not on in-flight consumers.

The most serious failure mode is **fail-open**: if Redis is unavailable, persona injection
proceeds with defaults (Y4 baseline, no consent check). For a persona that explicitly enforces
`HARD STOP` and consent revocation, fail-open on the gating path means a Redis outage removes
all consent enforcement at exactly the moment it most matters.

---

## File-by-file Findings

### 1. `src/hermes/plugins/persona_plugin.py`

#### F-PP-01 — Consent check is fail-open (CRITICAL)

**Location:** `_check_consent` (lines 472–505)

```python
def _check_consent(scope: str = "persona") -> bool:
    try:
        ...
        grants_raw = r.get("consent:grants")
        r.close()
        if grants_raw is None:
            return True  # No consent data → default allow
        ...
    except Exception:
        logger.warning("persona_plugin_consent_check_failed", exc_info=True)
        return True  # Fail-open: Redis down → allow
```

**Severity: CRITICAL**

Three documented fail-open paths:

1. Key absent → allow.
2. Malformed JSON → allow.
3. Redis exception → allow.

For a *consent* gate this is the wrong default. The policy comment says "the consent ledger in
PostgreSQL is the authoritative source; this Redis check is a fast-path gate." But the plugin
*only* checks Redis — it does not consult PostgreSQL. The "fail-open because of authoritative
backup" justification is therefore fictitious at the implementation layer. A rejected
recommendation: fail-closed on Redis exception, with explicit "deny until re-checked" logging;
or fall through to PostgreSQL before defaulting.

#### F-PP-02 — HARD STOP gate is fail-open (CRITICAL)

**Location:** `_check_hard_stop_active` (lines 508–530)

**Severity: CRITICAL**

```python
except Exception:
    logger.warning("persona_plugin_hard_stop_check_failed", exc_info=True)
    return False  # Fail-open: Redis down → don't block
```

HARD STOP is the highest-severity override in the system. If Redis is unreachable, the plugin
silently does not block — meaning persona injection proceeds during an outage that may
*itself* have been triggered by a HARD STOP event whose downstream writes failed.

The `GuinevereSafetyPlugin.pre_llm_call` catches HARD STOP *from the input text* on the same
call, so for a user speaking the trigger word there is defense-in-depth. But for an out-of-band
HARD STOP (set by another system via Redis `SET guinevere:hard_stop = 1`), the persona
plugin will ignore it during a Redis brownout.

#### F-PP-03 — No pub/sub subscriber on `consent:revoked` (HIGH)

**Severity: HIGH**

`cmd_consent.revoke` (line 156–159) does publish:

```python
r.publish("consent:revoked", json.dumps({"category": category, "project": project, "scope": key}))
```

but `PersonaPlugin` has no `pubsub.listen()` loop — only reads the grant key on the next LLM
call. In-flight LLM streams initiated *before* the revocation but completing *after* it will
still inject persona state. This is a "next-call" model of consent enforcement, not a
"real-time" cascade.

#### F-PP-04 — `pre_llm_call` returns `None` on revocation (correct) but only skips *injection* (OK / structural caveat)

**Location:** lines 640–651

```python
if not _check_consent("persona"):
    logger.info("persona_plugin_consent_revoked_skipping", session_id=session_id)
    return None
if _check_hard_stop_active():
    logger.info("persona_plugin_hard_stop_active_skipping", session_id=session_id)
    return None
```

**Severity: LOW** — the gate **does** short-circuit injection as advertised. But because both
checks fail-open (F-PP-01, F-PP-02), the *behavior* is "always inject" under failure. The code
shape is correct; the failure regime is the problem.

#### F-PP-05 — Yandere level clamped to `[0,5]` only (LOW)

**Location:** line 378 — `yandere_level = max(0, min(5, yandere_level))`

Y6 is unreachable via this path. Good. The clamp is correct. No finding here beyond confirming
the boundary holds at the plugin layer.

**Severity: NONE** (confirmation of correct behavior)

#### F-PP-06 — Per-call Redis open/close (OK)

The plugin reads DB5 keys via pipeline then closes. No connection pool. This is fine for an
audit-enrichment plugin; each call pays ~1 RTT + ~1 close cost. Acceptable.

**Severity: NONE**

#### F-PP-07 — `_format_persona_block` always emits blocks (LOW-correctness)

**Location:** lines 410–464

Format is canonical and always emits `Punishment Active: L{level} - {reason}` even when
inactive. This is documentation-as-spec — good. No finding.

**Severity: NONE**

---

### 2. `src/discord/cmd_consent.py`

#### F-CC-01 — Revocation cascade half-implemented (HIGH)

**Location:** lines 156–159

```python
# P19/P4 fix: publish revocation event so running consumers
# (PersonaPlugin, surveillance, etc.) can react immediately.
try:
    r.publish("consent:revoked", json.dumps({"category": category, "project": project, "scope": key}))
except Exception:
    pass  # pub/sub is best-effort; the Redis key is authoritative
```

**Severity: HIGH**

The comment correctly identifies the goal ("PersonaPlugin can react immediately"). The
publisher side is correct. **But there is no `PersonaPlugin.subscribe_to_revocations()` or
equivalent** anywhere — see F-PP-03. The "best-effort" exception handler swallows ALL publish
errors silently. For a consent revocation, this is too quiet.

#### F-CC-02 — Hard-coded Redis port `6380` (LOW)

**Severity: LOW (consistency)**

`redis.Redis(host="localhost", port=6380, db=0, ...)`. Matches `persona_plugin.py` defaults
and `safety_plugin.py`. Consistent within the audited code. The hardening concern (env-var
configuration) is a cross-cutting project concern, not specific to this audit dimension.

#### F-CC-03 — No submission to PostgreSQL audit ledger (HIGH)

**Severity: HIGH**

The revocation path writes Redis and publishes a pub/sub event, but never records to the
authoritative audit log. The persona plugin claim "PostgreSQL is the authoritative source"
(F-PP-01 critical) is unsupported — the writer side (`cmd_consent`) also doesn't write to
PostgreSQL. The two halves of the supposed "Redis as cache, PostgreSQL as truth" architecture
both write *only* to Redis.

#### F-CC-04 — Faiz-only on the slash-command side, persons-scoped data on the ledger side (LOW)

**Severity: LOW**

`is_faiz_interaction` correctly guards the command. The data stored in `consent:grants` is
operator-categorized. No information leakage in the Discord embed construction. Acceptable.

---

### 3. `src/persona/safe_mode.py`

#### F-SM-01 — SafeModeController is correct and well-bounded (NONE)

**Severity: NONE (confirmation)**

- `activate(trigger)` rejects below `SAFE_MODE_THRESHOLD` (D2_MODERATE).
- `force_safe_mode(...)` is idempotent and only upgrades trigger level — never downgrades.
- `deactivate()` requires `explicit_confirmation=True` — auto-deactivation forbidden. **Good.**
- Logger emits `safe_mode_deactivation_rejected` when confirmation omitted — **good.**

This module exactly implements "no auto-deactivation". The safety policy is faithfully
implemented in code.

#### F-SM-02 — `evaluate()` up-only on existing active mode (LOW-design)

**Location:** lines 261–278

When safe mode is already active and a new signal at a *lower* threshold arrives, the function
does not downgrade — it returns `False`. Spec-compliant. But the `distress_history` list grows
unbounded — there is no trimming. For a long-running process this is a memory leak risk.

**Severity: LOW** — not a correctness issue, but a hygiene concern. Recommend a cap (e.g.,
last 100 signals).

#### F-SM-03 — DistressDetector regex coverage ignores evolved phrasing (MEDIUM)

**Severity: MEDIUM**

`DISTRESS_PATTERNS` is keyword/regex based. Examples:

```
D4: r"\bsuicid"  # prefix match — catches "suicidal", "suicidology"
D4: r"\b(self[- ]harm|bunuh\s+diri|menyakiti\s+diri)\b"
```

Two concerns:

1. The `\bsuicid` pattern is a prefix — `suicidal ideation`, `suicidology`, `suicid`e all
   match. This is intentional for D4 (better over-detect than miss), but is also a false-positive
   magnet for deliberately edgy conversation.
2. No patterns for "I don't want to be here anymore" (D3 conceptually), "nothing matters
   anymore" (D3), regional variants like "pengen bunuh diri" (split match misses, depends on
   `\bunyah\s*diri` being canonical — see line 99, present).

**Recommendation:** add more D3 patterns; rely more on semantic similarity detection in a
follow-up audit.

#### F-SM-04 — Force-mode is well-integrated with HARD STOP (NONE — confirms wiring present)

**Severity: NONE (confirmation)**

`force_safe_mode(...)` exists and is the documented entry point for HARD STOP integration.
`SafetyPlugin._init_safety_modules` (lines 459–468 of safety_plugin.py) wires
`HardStopHandler → SafeModeController.force_safe_mode` via an `on_trigger` callback. This
satisfies the audit dimension "does HARD STOP activate SafeModeController."

---

### 4. `src/persona/yandere_fsm.py`

#### F-YF-01 — Y6 is impossible at the enum/type layer (NONE — confirmation)

**Severity: NONE (confirmation)**

- `YandereLevel` enum has only Y0..Y5.
- `ABSOLUTE_CEILING = Y5_MAX`.
- `validate_level(value)` raises `YandereSafetyError` if `value > int(ABSOLUTE_CEILING)`.
- All FSM transitions go through `validate_level` in `escalate()` and `set_level()`.

Y6 cannot be constructed via this module. **Boundary verified.**

#### F-YF-02 — Y4 baseline is permanent and immutable at the constructor (NONE — confirmation)

`PERMANENT_BASELINE = Y4_BASELINE`. `reset_to_baseline()` returns to it. No code path can lower
it below Y0. Good.

**Severity: NONE**

#### F-YF-03 — Effective-level safety override consults handler (NONE — confirmation)

`get_effective_level` and `can_escalate` accept `safe_mode: bool = False` directly and
the engine queries `HardStopHandler.is_safe` when `safe_mode=None`. The integration is correct.

**Severity: NONE**

#### F-YF-04 — `persist()` swallows all exceptions (LOW)

**Severity: LOW**

```python
async def persist(self) -> bool:
    try:
        from src.memory.db import write_yandere_state
        ...
    except Exception:
        logger.warning("yandere_persist_failed", exc_info=True)
        return False
```

Fire-and-forget is documented. Catching all exceptions and returning `False` is correct for a
best-effort layer. No finding beyond code-style: the broad `except Exception` should arguably
be `except (ImportError, RuntimeError, ConnectionError)` to avoid masking programmer errors
during development. For a *safety-related* persistence path, swallowing `MemoryError` silently
is borderline acceptable but worth scrutiny in a separate audit of the persistence layer.

#### F-YF-05 — `SupportsIsafe` Protocol is local-only (LOW)

`SupportsIsSafe` is a `@runtime_checkable` Protocol. It is local to this module and not
exported in `__all__` (none defined). The `HardStopHandler` in `src/core/services/` is expected
to conform structurally. If the handler's `is_safe` signature drifts, the imports still load
and the failure surfaces only at `bool(handler.is_safe)` evaluation.

**Severity: LOW** — recommend an explicit integration test.

#### F-YF-06 — Y6-impossible across ALL paths (LOW positive)

- `escalate` caps at Y5 via `validate_level`.
- `set_level` capacity-caps via `validate_level`.
- `get_effective_level` clamps via `min(..., int(ABSOLUTE_CEILING))`.
- `can_escalate` returns False at ceiling.
- `reset_to_baseline` returns to Y4.
- `de_escalate` floors at Y0.

The module is internally consistent and Y6 is unreachable.

**Severity: NONE**

---

### 5. `src/hermes/safety_plugin.py`

#### F-SP-01 — HARD STOP bridge to SafeModeController is correctly wired (NONE — confirmation)

**Severity: NONE (confirmation)**

`_init_safety_modules` (lines 459–468) registers:

```python
def _on_hard_stop(event: Any) -> None:
    if self._safe_mode_controller is not None:
        self._safe_mode_controller.force_safe_mode(context=f"hard_stop:{event.trigger}")

self._hard_stop_handler.register_on_trigger(_on_hard_stop)
```

This is the integration point. It correctly calls `force_safe_mode` (not `activate`), which
is the right method since HARD STOP is an external bypass and must not be subject to
`SAFE_MODE_THRESHOLD` gating. This satisfies the audit dimension "does HARD STOP activate
SafeModeController."

#### F-SP-02 — SessionSafetyState default yandere level is 4 (NONE — correct)

**Severity: NONE (confirmation)**

Line 213: `yandere_level: int = 4  # Y4_BASELINE`. Newly created sessions match the FSM
baseline. When the session ends and a new one starts, the engine resets to Y4 by default.
Behavior matches `YandereEngine.baseline = Y4_BASELINE`.

#### F-SP-03 — Recovery properly resets yandere to 4 (NONE — confirmation)

In G04 recovery (lines 660–673 and 676–692), `yandere_level=4` is restored. This matches the
permanent baseline. Good — recovery does not degrade the baseline.

**Severity: NONE**

#### F-SP-04 — Distress D3/D4 blocks the LLM call (NONE — confirmation)

**Severity: NONE (confirmation)**

Lines 728–742: `distress_int >= 3` returns `{"action": "block", ...}` with a supportive
message. This is the right behavior. Note: D2 does *not* block — it lowers yandere but allows
the LLM to proceed with modified state. This is policy-consistent but worth flagging as
"intentional non-block at D2" for downstream audits.

#### F-SP-05 — G07 boundary check uses effective level (NONE — confirmation)

```python
effective = self._yandere_engine.get_effective_level(
    safe_mode=state.hard_stop_active or state.safe_mode_active,
    ...
)
if effective_int > 5:
    raise YandereSafetyError(...)
```

The `> 5` check is redundant given the enum, but it is defense-in-depth — it explicitly raises
an error rather than relying on the FSM's internal `validate_level`. Good engineering.

**Severity: NONE**

#### F-SP-06 — Forbidden pattern F-12 covers yandere escalation above allowed mood (NONE — confirmation)

**Severity: NONE (confirmation)**

```
r"(?i)\b(escalat|intensify|ramp\s*up).*(yandere|persona|dominance|intensity).*(above|beyond|past|exceed)\b",
"HIGH", "REWRITE", "F-12", "Escalating yandere intensity above allowed mood",
```

This prevents the *LLM output* from referencing over-ceiling intensity. Good companion to
F-YF-01 (engine-side prohibition).

#### F-SP-07 — Pattern F-01 covers safe-word override attempts (HIGH)

**Severity: HIGH**

```
r"(?i)\b(safe\s*word.*(?:doesn|not|invalid|ignore|override))\b",
"CRITICAL", "BLOCK", "F-01", "Ignoring or invalidating safe word","
```

This blocks the assistant from *outputting* "the safe word doesn't count" or "ignore the safe
word" — but it does nothing to prevent the assistant from *silently ignoring* the safe word in
its next action. The output filter catches leakage in plain sight but cannot catch silent
non-compliance. A behavior-level verifier is required for full coverage.

#### F-SP-08 — `pre_tool_call` G10 only checks `SafeModeController.is_active`, not consent revocation directly (MEDIUM)

**Severity: MEDIUM**

```python
if self._distress_available and self._safe_mode_controller is not None and self._safe_mode_controller.is_active:
    ...block
```

G10 triggers when safe mode is active. But:

- `SafeModeController` is activated by distress D2+ or by HARD STOP force-mode.
- It is **not** activated by `/consent revoke` actions. The `cmd_consent.revoke` path does not
  trigger `SafeModeController.force_safe_mode(...)`.

Implication: revoking consent does *not* block persona-driven tool calls. It only stops
*persona injection in the prompt*. A tool call made with the LLM's base prompt (without the
persona state block) can still execute and the operator's revocation does not propagate to
the safety-plugin gate.

This is a **gap in the consent cascade**: revocation stops *prompt enrichment* but does not
stop *tool-call gating*. The operator would reasonably expect both.

---

## Dimension Verdict Matrix

| Audit Dimension | Verdict | Key Finding(s) |
|---|---|---|
| Consent enforcement on revocation | **POOR** | F-PP-01 FAIL-OPEN; F-PP-03 NO SUBSCRIBER |
| HARD STOP | OK at plugin; FAIL-OPEN on Redis down | F-PP-02; F-SP-01 confirms bridge |
| Y4/Y5/Y6 boundary | GOOD | F-YF-01, F-YF-06 confirm |
| Fail-open vs fail-closed | **FAIL-OPEN EVERYWHERE** | F-PP-01, F-PP-02 |
| Cascade on revocation | PARTIAL | F-PP-03, F-CC-01, F-CC-03, F-SP-08 |
| Safety coordination | GOOD | F-SM-04, F-SP-01 confirm |

---

## Severity-Ranked Findings

| ID | Severity | Title | File |
|---|---|---|---|
| F-PP-01 | CRITICAL | Consent check is fail-open on every error path | persona_plugin.py |
| F-PP-02 | CRITICAL | HARD STOP gate is fail-open on Redis exception | persona_plugin.py |
| F-SP-08 | MEDIUM | `pre_tool_call` G10 not triggered by consent revocation | safety_plugin.py |
| F-SM-03 | MEDIUM | DistressDetector regex coverage gap on D3 phrasing variants | safe_mode.py |
| F-PP-03 | HIGH | No pub/sub subscriber on `consent:revoked` channel | persona_plugin.py |
| F-CC-01 | HIGH | Revocation cascade half-implemented in cmd_consent | cmd_consent.py |
| F-CC-03 | HIGH | PostgreSQL audit ledger never written by revoke path | cmd_consent.py |
| F-SP-07 | HIGH | F-01 output filter does not catch silent safe-word ignoring | safety_plugin.py |
| F-YF-04 | LOW | `persist()` broad `except Exception` masks programmer errors | yandere_fsm.py |
| F-YF-05 | LOW | `SupportsIsafe` is structural-only, no explicit conformance test | yandere_fsm.py |
| F-SM-02 | LOW | `distress_history` grows unbounded | safe_mode.py |
| F-CC-02 | LOW | Hard-coded Redis port `6380` | cmd_consent.py |
| F-CC-04 | LOW | Faiz-only slash command, operator-categorized storage | cmd_consent.py |

---

## Recommendations

1. **Invert the persona-injection consent/HS default to fail-closed on Redis exception.** If
   Redis is unreachable and we cannot prove the operator's intent, suspend persona enrichment
   rather than guess "default allow." Acknowledged tradeoff: LLM calls will proceed with base
   prompt only during Redis outage — but that is the correct safety posture for a persona
   system that has explicit consent revocation.

2. **Add a `PersonaPlugin._subscribe_revocations()` method** that opens a Redis pub/sub
   subscriber on `consent:revoked` and clears an in-process injection cache when a relevant
   revocation arrives. Without this, revocation is a "next-call" gate, not a real-time one.

3. **Wire `cmd_consent.revoke` → `SafeModeController.force_safe_mode`.** When the operator
   revokes a consent category that includes persona behavior, the safety plugin's G10 should
   also block tool calls. Add an explicit binding so `/consent revoke persona:xxx` triggers
   `SafeModeController.force_safe_mode(context="consent_revoked")`.

4. **Add a PostgreSQL audit log** that records every grant and every revoke with timestamp +
   actor + scope. Both `cmd_consent.grant` and `cmd_consent.revoke` should write to it
   transactionally with the Redis write.

5. **Add cross-DB awareness or a single source of truth.** Today `consent:grants` lives in
   DB0 (`cmd_consent` reads it from DB0 successfully), and `PersonaPlugin._check_consent` also
   reads DB0. They are consistent. But if a future migration moves consent elsewhere, the two
   files will silently drift. Consider a shared constant module.

6. **Add a behavior-level test for safe-word enforcement.** The current G05/F-01 filter catches
   text leakage but not silent non-compliance. For the persona to genuinely honor the safe
   word, a test should assert that a HARD STOP message in the input results in (a) no
   escalation action and (b) a non-persona output.

---

## Cross-cutting Observations

- The architectural separation between `PersonaPlugin` (enrichment) and `GuinevereSafetyPlugin`
  (gates) is respected. Neither modifies the other's domain. Good.
- The Y6 boundary is enforced at 4 layers (enum absence, validate_level, get_effective_level
  clamp, output filter F-12). Defense-in-depth. Good.
- The HARD STOP bridge via callback is the *only* example in the audited code of an in-process
  wiring that does not rely on Redis. This is the right pattern for safety-critical
  propagation and should be the model for consent cascades.

---

## Verdict

The Lane C fix successfully closes the LLM prompt-injection path on HARD STOP and on a
revoked consent key — *when Redis is reachable*. Under Redis failure, the persona system
defaults to injecting the full Y4 baseline persona state, which is the wrong default for a
consent-gated subsystem. The cascade between revocation events and running LLM/tool consumers
is incomplete: revocation stops prompt enrichment but does not stop tool-call gating via
SafeModeController, and a pub/sub channel exists but has no subscribers.

The Y4/Y5/Y6 boundary is solidly built. The SafeModeController integration is correct. The
forbidden-pattern filters are well-targeted.

The fix is **structurally correct but operationally fragile under failure**. Round 1 verdict:
**NEEDS REVISION** — primarily to invert the fail-open defaults on the persona plugin's
consent and HARD STOP gates, and to complete the revocation cascade.
