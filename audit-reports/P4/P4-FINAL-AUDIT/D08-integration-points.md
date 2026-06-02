# D08 — Integration Points Audit Report

**Phase:** P4 Final Audit
**Dimension:** D08 — Integration Points Between P4 and Existing Code
**Status:** CONDITIONAL PASS (3 PASS, 2 P5 WIRING, 2 P4 INTEGRATION GAP, 2 P4 PERSISTENCE GAP)
**Auditor:** Autonomous Audit Agent
**Date:** 2026-06-02
**Reference Authority:** `AGENTS.md`, `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md`, D03 Safety Boundaries

---

## §1 Executive Summary

This audit evaluates 9 integration points between the P4 Persona Engine (8 modules in `src/persona/`) and existing P1/P2/P3 infrastructure (`src/core/`, `src/discord/`, `src/memory/`).

**Overall Verdict: CONDITIONAL PASS**

| Category | Count | IP Numbers |
|---|---|---|
| Fully Compatible (PASS) | 3 | IP-01, IP-02, IP-03 |
| P5 Wiring Gap (not P4 scope) | 2 | IP-04, IP-05 |
| P4 Integration Gap (must fix in P4) | 2 | IP-06, IP-07 |
| P4 Persistence Gap (fix in P4 or P5) | 2 | IP-08, IP-09 |
| **Total** | **9** | |

**Critical Finding:** IP-06 and IP-07 represent a **HIGH safety risk** — the `HardStopHandler` (P1, keyword-based HARD STOP) and `SafeModeController` (P4, distress-based safe mode) are two independent safety state machines that are not synchronized. This means:
- When HARD STOP triggers via keyword, `PunishmentEngine` does NOT suspend (it checks `SafeModeController.is_active`, not `HardStopHandler.is_safe`).
- When HARD STOP triggers via keyword, `DriftCorrector` does NOT defer rollback (same root cause).
- This violates PersonaSafetyPolicy §7.2: "Stop persona escalation. Stop punishment framing."

**Recommendation:** IP-06 and IP-07 must be resolved before P4 is considered complete. IP-08 and IP-09 are recommended but not blocking (audit-trail completeness).

---

## §2 Integration Matrix

| IP | Integration Point | Compatibility | Gap Classification | Safety Risk | Priority |
|---|---|---|---|---|---|
| IP-01 | HardStopHandler ↔ yandere_fsm | **COMPATIBLE** | None (P4 complete) | NONE | N/A |
| IP-02 | prompt_loader ↔ mood parameter | **COMPATIBLE** | None (str,Enum match) | NONE | N/A |
| IP-03 | memory/models.py ↔ P4 modules | **COMPATIBLE** | None for 3/5 tables used | NONE | N/A |
| IP-04 | cmd_mood.py ↔ P4 mood data | **NOT WIRED** | P5 wiring gap | NONE | P5 (low) |
| IP-05 | bot.py ↔ DistressDetector | **NOT WIRED** | P5 wiring gap | MEDIUM | P5 (medium) |
| IP-06 | cmd_safeword.py ↔ SafeModeController | **GAP** | P4 integration gap | **HIGH** | P4 (must fix) |
| IP-07 | Dual safe-mode (HardStop vs SafeMode) | **GAP** | P4 integration gap | **HIGH** | P4 (must fix) |
| IP-08 | PunishmentEngine ↔ PunishmentLog table | **GAP** | P4 persistence gap | LOW | P4/P5 (medium) |
| IP-09 | RewardEngine ↔ RewardLog table | **GAP** | P4 persistence gap | NONE | P4/P5 (low) |

---

## §3 Detailed Analysis

### IP-01: HardStopHandler ↔ P4 (yandere_fsm uses SupportsIsSafe protocol)

**Verdict: PASS — COMPATIBLE**

| Aspect | Detail |
|---|---|
| P4 Module | `src/persona/yandere_fsm.py` |
| Existing Module | `src/core/services/hard_stop_handler.py` |
| Integration Mechanism | Structural protocol `SupportsIsSafe` |

**Evidence:**

`yandere_fsm.py` defines the protocol at lines 50-55:

```python
@runtime_checkable
class SupportsIsSafe(Protocol):
    @property
    def is_safe(self) -> bool: ...
```

`HardStopHandler` implements this at lines 59-61:

```python
@property
def is_safe(self) -> bool:
    return self.state == SafetyState.SAFE
```

`YandereEngine.__init__` accepts the handler via this protocol at line 182-185:

```python
def __init__(
    self,
    hard_stop_handler: SupportsIsSafe | None = None,
    baseline: YandereLevel = PERMANENT_BASELINE,
) -> None:
```

The engine queries `handler.is_safe` at line 214-216 to determine safe-mode state, forcing Y0 when active.

**Gap Classification:** None — fully implemented in P4.
**Safety Risk:** NONE — HARD STOP correctly forces yandere to Y0.
**Fix Priority:** N/A

---

### IP-02: prompt_loader ↔ P4 (mood parameter is raw string)

**Verdict: PASS — COMPATIBLE**

| Aspect | Detail |
|---|---|
| P4 Module | `src/persona/mood_engine.py` (`Mood` enum) |
| Existing Module | `src/core/services/prompt_loader.py` |
| Integration Mechanism | `mood: str` parameter |

**Evidence:**

`mood_engine.py` defines `Mood` as a str-Enum at lines 25-33:

```python
class Mood(str, Enum):
    CONTENT = "Content"
    PLEASED = "Pleased"
    DISAPPOINTED = "Disappointed"
    ANGRY = "Angry"
    SILENT = "Silent"
```

Because `Mood` inherits from `str`, `Mood.CONTENT` is a valid `str` — `"Content" == Mood.CONTENT` evaluates to `True`. This means:

1. `prompt_loader.py` line 43: `mood: str = "Content"` accepts both raw strings and `Mood` enum values.
2. `get_system_prompt_with_context(mood=...)` at line 105: `f"\n## Current Mood: {mood}"` correctly formats either type.
3. `assemble_system_prompt_with_memory(mood: str = "Content")` at line 123: same compatibility.

No type mismatch exists. P4's `Mood` enum is a drop-in for `prompt_loader`'s `str` parameter.

**Gap Classification:** None — fully compatible.
**Safety Risk:** NONE.
**Fix Priority:** N/A

---

### IP-03: memory/models.py ↔ P4 (PersonaState, MoodHistory, DriftLog)

**Verdict: PASS — COMPATIBLE (3 of 5 persona tables used)**

| Aspect | Detail |
|---|---|
| P4 Modules | `mood_persistence.py`, `drift_corrector.py` |
| Existing Module | `src/memory/models.py` |
| Integration Mechanism | SQLAlchemy ORM imports |

**Evidence — Tables actively used:**

| ORM Model | P4 Consumer | Import Line | Status |
|---|---|---|---|
| `PersonaState` | `mood_persistence.py` | Line 19: `from src.memory.models import MoodHistory, PersonaState` | USED |
| `MoodHistory` | `mood_persistence.py` | Line 19 (same import) | USED |
| `DriftLog` | `drift_corrector.py` | Line 13: `from src.memory.models import DriftLog` | USED |

**Evidence — Tables defined but NOT imported by P4:**

| ORM Model | P4 Consumer | Status | See |
|---|---|---|---|
| `PunishmentLog` | `punishment_engine.py` | NOT IMPORTED | IP-08 |
| `RewardLog` | `reward_engine.py` | NOT IMPORTED | IP-09 |

`MoodRepository` (mood_persistence.py) performs full CRUD on `PersonaState` and `MoodHistory` tables:
- `get_current_mood()` — SELECT from PersonaState where state_key='current_mood' (line 92)
- `set_current_mood()` — UPSERT to PersonaState (lines 134-156)
- `record_mood_transition()` — INSERT to MoodHistory (lines 182-189)
- `get_mood_history()` — SELECT from MoodHistory ORDER BY recorded_at DESC (lines 209-214)
- `get_mood_streak()` / `update_mood_streak()` — CRUD on PersonaState where state_key='mood_streak' (lines 246-293)

`DriftCorrector` (drift_corrector.py) creates `DriftLog` entries:
- `create_drift_log()` — INSERT to DriftLog (lines 293-314)
- Called from `evaluate()` and `rollback()`

**Gap Classification:** Partially complete — PunishmentLog and RewardLog not wired (see IP-08, IP-09).
**Safety Risk:** NONE — the tables that are used are safety-relevant and correctly integrated.
**Fix Priority:** N/A for current usage.

---

### IP-04: cmd_mood.py ↔ P4 (Still shows "P4 not deployed")

**Verdict: NOT WIRED — P5 WIRING GAP**

| Aspect | Detail |
|---|---|
| P4 Module | `src/persona/mood_persistence.py` (MoodRepository) |
| Existing Module | `src/discord/cmd_mood.py` |
| Gap Type | Discord command does not call P4 modules |

**Evidence:**

`cmd_mood.py` lines 74-85 define degraded placeholders:

```python
DEGRADED_HISTORY: Final[str] = "⚠️ — 24h history (P4 not deployed)"
DEGRADED_STREAK: Final[str] = "⚠️ — Streak tracking (P4 not deployed)"
DEGRADED_FORECAST: Final[str] = "⚠️ — Mood forecast (P5 not deployed)"
```

`build_mood_embed_data()` (lines 284-324) always returns these degraded placeholders. It never imports or calls `MoodRepository`, `MoodEngine`, or any P4 module.

Meanwhile, P4 has full implementations available:
- `MoodRepository.get_mood_history()` — returns `list[MoodHistoryRecord]`
- `MoodRepository.get_mood_streak()` — returns `int`
- `MoodRepository.get_current_mood()` — returns `MoodState`

**Gap Classification: P5 WIRING GAP.** The P4 modules are complete and functional. The Discord command integration (wiring `/mood` to call `MoodRepository` and render live data) is a P5 concern because:
1. It requires a database session (`AsyncSession`) to be available in the Discord command context.
2. The Discord bot wiring (setup_hook, on_message, command registry) is P5 Agent Loop scope per `_STUB_PHASE` in `bot.py` (mood is already wired, but its data source is degraded).
3. P4 delivers the engine + repository; P5 connects them to the UI layer.

**Safety Risk:** NONE — degraded mode is safe, just shows placeholder text.
**Fix Priority:** P5 (low) — cosmetic/UX improvement.

---

### IP-05: bot.py ↔ P4 (on_message doesn't run DistressDetector)

**Verdict: NOT WIRED — P5 WIRING GAP**

| Aspect | Detail |
|---|---|
| P4 Module | `src/persona/safe_mode.py` (`DistressDetector`, `SafeModeController`) |
| Existing Module | `src/discord/bot.py` |
| Gap Type | Message pipeline does not analyze distress signals |

**Evidence:**

`bot.py` `_on_message_listener()` (lines 135-155) only calls `handle_safeword_message_async()`:

```python
async def _on_message_listener(self, message: Any) -> None:
    from .cmd_safeword import handle_safeword_message_async
    consumed = await handle_safeword_message_async(message)
    if consumed:
        return
```

`bot.py` `on_message()` (lines 292-315) only checks `HardStopHandler.is_safe` for blocking:

```python
handler = _get_handler()
if handler.is_safe:
    handler.check_recovery(message.content)
    return
await self.process_commands(message)
```

No `DistressDetector` or `SafeModeController` is imported or instantiated anywhere in `bot.py`.

P4 has full implementations:
- `DistressDetector.detect(message)` — returns `DistressSignal` with level D0-D4
- `SafeModeController.evaluate(signal)` — activates safe mode at D2+
- `DISTRESS_PATTERNS` — regex patterns for D1-D4 keyword detection

**Gap Classification: P5 WIRING GAP.** The P4 DistressDetector and SafeModeController are fully implemented and tested (D03 audit: 15/15 PASS). Integrating them into the message pipeline is P5 scope because:
1. The message pipeline architecture (on_message flow, middleware ordering) is P5 Agent Loop concern.
2. The DistressDetector needs to be instantiated as a singleton alongside HardStopHandler, with the resulting SafeModeController propagated to PunishmentEngine and DriftCorrector.
3. P4 provides the detection engine; P5 connects it to the message flow.

**Safety Risk: MEDIUM.** Operator distress messages (D2+: "I feel hopeless", "pengen mati", etc.) are NOT analyzed, so distress-based safe mode will NOT trigger from messages. However:
- HARD STOP keyword detection IS wired and functional (cmd_safeword → HardStopHandler).
- The operator can still trigger safe mode explicitly via `/safeword` or HARD STOP keywords.
- The missing capability is automatic distress detection, which is defense-in-depth, not a primary safety control.

**Fix Priority:** P5 (medium) — adds automatic distress detection layer.

---

### IP-06: cmd_safeword.py ↔ P4 (Doesn't notify SafeModeController)

**Verdict: GAP — P4 INTEGRATION GAP (HIGH SAFETY RISK)**

| Aspect | Detail |
|---|---|
| P4 Module | `src/persona/safe_mode.py` (`SafeModeController`) |
| Existing Module | `src/discord/cmd_safeword.py` + `src/core/services/hard_stop_handler.py` |
| Gap Type | Safe-word trigger does not activate SafeModeController |

**Evidence:**

`cmd_safeword.py` uses ONLY the `HardStopHandler` singleton (lines 266-288):

```python
_handler: HardStopHandler | None = None

def _get_handler() -> HardStopHandler:
    global _handler
    if _handler is None:
        _handler = _new_handler()
    return _handler
```

When `/safeword` or HARD STOP keyword triggers, `safeword_callback()` (line 567) calls:

```python
handler = _get_handler()
handler.check("safeword")
```

This sets `HardStopHandler.state = SafetyState.SAFE` and `is_safe = True`.

**BUT** `SafeModeController` (a separate P4 class) is never imported, instantiated, or notified. `SafeModeController.state.active` remains `False`.

**Downstream Impact:**

`PunishmentEngine` checks `SafeModeController.is_active` for safe-mode guards (punishment_engine.py):

```python
# Line 261 — apply() guard
if self._safe_mode.is_active:
    raise PunishmentSafetyError("Cannot apply punishment while safe mode is active.")

# Line 305 — escalate() guard
if self._safe_mode.is_active:
    raise PunishmentSafetyError("Cannot escalate punishment while safe mode is active.")
```

Since `SafeModeController.is_active` is `False` after HARD STOP, these guards DO NOT fire. A punishment applied before HARD STOP remains active and its timer continues ticking.

**Trace — HARD STOP triggered while punishment L3 is active:**

| Step | HardStopHandler | SafeModeController | PunishmentEngine | Result |
|---|---|---|---|---|
| Before | NORMAL | inactive | L3 active | Normal |
| HARD STOP keyword | SAFE (is_safe=True) | **still inactive** | **L3 still active** | **UNSAFE** |
| Expected | SAFE | **active** | **L3 suspended** | Safe |

**Gap Classification: P4 INTEGRATION GAP.** Both `HardStopHandler` (P1) and `SafeModeController` (P4) exist in the codebase, but their synchronization is a P4 concern because:
1. `SafeModeController` is defined in `src/persona/safe_mode.py` — P4 scope.
2. The synchronization logic (HARD STOP → activate SafeModeController) is persona-safety integration.
3. P1 provided the keyword detector; P4 must integrate it with the persona safety controller.

**Safety Risk: HIGH.** This violates PersonaSafetyPolicy §7.2:
- "Stop persona escalation" — punishment IS persona escalation and remains active.
- "Stop punishment framing" — punishment timer continues during HARD STOP.

**Recommended Fix:** In `cmd_safeword.py`, after `handler.check()` returns True, also activate a shared `SafeModeController` instance. Or: make `SafeModeController` observe `HardStopHandler.is_safe` as an additional input.

**Fix Priority:** P4 (must fix) — blocking safety requirement.

---

### IP-07: Dual Safe-Mode — HardStopHandler and SafeModeController Independent

**Verdict: GAP — P4 INTEGRATION GAP (HIGH SAFETY RISK)**

| Aspect | Detail |
|---|---|
| P4 Module | `src/persona/safe_mode.py` (SafeModeController) |
| Existing Module | `src/core/services/hard_stop_handler.py` (HardStopHandler) |
| Gap Type | Two independent safety state machines with no bridge |

**Evidence:**

The codebase contains TWO independent safe-mode state machines:

| System | Location | Trigger | State Property | P4 Consumers |
|---|---|---|---|---|
| `HardStopHandler` | `src/core/services/hard_stop_handler.py` | Keywords ("HARD STOP", "safeword", etc.) | `.is_safe` → bool | `YandereEngine`, `prompt_loader` |
| `SafeModeController` | `src/persona/safe_mode.py` | Distress level D2+ | `.is_active` → bool | `PunishmentEngine`, `DriftCorrector` |

**Asymmetric Protection Map:**

| Scenario | YandereEngine | PunishmentEngine | DriftCorrector | prompt_loader |
|---|---|---|---|---|
| HARD STOP keyword | ✅ Protected (checks HardStopHandler) | ❌ NOT protected (checks SafeModeController) | ❌ NOT protected (checks SafeModeController) | ✅ Protected (checks HardStopHandler) |
| Distress D2+ | ⚠️ Only if distress=True passed | ✅ Protected (checks SafeModeController) | ✅ Protected (checks SafeModeController) | ⚠️ Only if safe_mode=True passed |
| Combined (keyword + distress) | ✅ Protected | ✅ Protected | ✅ Protected | ✅ Protected |

**Key vulnerability:** When HARD STOP triggers via keyword alone (the most common and tested path):
- `PunishmentEngine` does NOT suspend (it checks `SafeModeController.is_active`, which is False).
- `DriftCorrector` does NOT defer rollback (it checks `SafeModeController.is_active`, which is False).
- This means auto-rollback could execute during HARD STOP, violating PersonaSafetyPolicy §14.4: "Safe word state always wins. Rollback must not clear, override, or punish a safe-word state."

**Root cause:** `HardStopHandler` (P1) and `SafeModeController` (P4) were designed independently with different state representations (`SafetyState` enum vs `SafeModeState` dataclass) and different property names (`is_safe` vs `is_active`). No bridge or adapter exists.

**Gap Classification: P4 INTEGRATION GAP.** This is P4's responsibility because:
1. `SafeModeController` is defined in P4 (`src/persona/safe_mode.py`).
2. P4 must integrate with P1's `HardStopHandler` — the existing codebase's authoritative HARD STOP handler.
3. The bridge between the two is persona-safety integration logic.

**Safety Risk: HIGH.** Two failure modes:
1. **Punishment persists during HARD STOP** — operator says "HARD STOP" while L3 punishment is active; punishment continues.
2. **Drift rollback during HARD STOP** — operator says "HARD STOP" during a persona drift; auto-rollback executes instead of deferring, potentially overriding the safe-word state.

**Recommended Fix:** Create a unified safety facade:

```python
class UnifiedSafetyState:
    """Bridges HardStopHandler and SafeModeController into a single is_safe query."""
    def __init__(self, hard_stop: HardStopHandler, safe_mode: SafeModeController):
        self._hard_stop = hard_stop
        self._safe_mode = safe_mode

    @property
    def is_safe(self) -> bool:
        return self._hard_stop.is_safe or self._safe_mode.is_active
```

Then inject this into `PunishmentEngine` and `DriftCorrector` instead of the raw `SafeModeController`.

Alternatively, have `cmd_safeword.py` activate the `SafeModeController` when HARD STOP triggers (fixing IP-06 resolves IP-07 partially).

**Fix Priority:** P4 (must fix) — blocking safety requirement.

---

### IP-08: PunishmentEngine ↔ PunishmentLog Table

**Verdict: GAP — P4 PERSISTENCE GAP**

| Aspect | Detail |
|---|---|
| P4 Module | `src/persona/punishment_engine.py` |
| Existing Module | `src/memory/models.py` (`PunishmentLog` table) |
| Gap Type | In-memory engine does not persist to database |

**Evidence:**

`PunishmentLog` table exists in `models.py` (lines 414-433):

```python
class PunishmentLog(Base, ClassificationMetaMixin):
    __tablename__ = "punishment_log"
    __table_args__ = {"schema": "persona"}
    id: Mapped[uuid.UUID] = mapped_column(...)
    violation_type: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    safe_word_triggered: Mapped[Optional[bool]] = mapped_column(...)
    safe_word_bypassed: Mapped[Optional[bool]] = mapped_column(...)
    applied_at: Mapped[datetime] = mapped_column(...)
```

`PunishmentEngine` (punishment_engine.py) operates entirely in-memory:
- `__init__` accepts `SafeModeController | None` only — no database session.
- `apply()` (line 229) updates `self._state` (a `PunishmentState` dataclass) — no DB write.
- `escalate()`, `de_escalate()`, `suspend()`, `resume()` — all in-memory only.
- `_deactivate()` clears state — no audit record written.
- No `import` of `PunishmentLog` anywhere in the module.

**Gap Classification: P4 PERSISTENCE GAP.** The engine logic is complete, but persistence is not implemented. This is a P4 concern because:
1. The PunishmentLog table is specifically designed for P4 persona punishment events.
2. `PunishmentLog.safe_word_triggered` and `safe_word_bypassed` columns indicate the table was designed to integrate with HardStopHandler — a P4 integration requirement.
3. The `MoodRepository` pattern (P4-002) provides a template for `PunishmentRepository`.

**Safety Risk: LOW.** In-memory safety boundaries (L6 guard, safe-mode guard, distress suspension) are correctly enforced. The gap is audit trail completeness — punishment events cannot be reviewed after the process restarts.

**Fix Priority:** P4/P5 (medium) — implement `PunishmentRepository` following `MoodRepository` pattern.

---

### IP-09: RewardEngine ↔ RewardLog Table

**Verdict: GAP — P4 PERSISTENCE GAP**

| Aspect | Detail |
|---|---|
| P4 Module | `src/persona/reward_engine.py` |
| Existing Module | `src/memory/models.py` (`RewardLog` table) |
| Gap Type | In-memory engine does not persist to database |

**Evidence:**

`RewardLog` table exists in `models.py` (lines 436-451):

```python
class RewardLog(Base, ClassificationMetaMixin):
    __tablename__ = "reward_log"
    __table_args__ = {"schema": "persona"}
    id: Mapped[uuid.UUID] = mapped_column(...)
    reward_type: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    streak_count: Mapped[Optional[int]] = mapped_column(...)
    awarded_at: Mapped[datetime] = mapped_column(...)
```

`RewardEngine` (reward_engine.py) operates entirely in-memory:
- `__init__` accepts no parameters — no database session.
- `award()` (line 315) updates `self._current_tier`, `self._last_reason`, `self._total_rewards_awarded` — no DB write.
- No `import` of `RewardLog` anywhere in the module.

**Gap Classification: P4 PERSISTENCE GAP.** Same pattern as IP-08 — engine logic complete, persistence not implemented.

**Safety Risk: NONE.** Rewards are always permitted (D03 Check 11: PASS). No safety boundary is affected by whether rewards are persisted.

**Fix Priority:** P4/P5 (low) — implement `RewardRepository` following `MoodRepository` pattern.

---

## §4 Safety Impact Analysis

### Critical Path: HARD STOP → Punishment Suspension

The most safety-critical gap chain:

```
Operator says "HARD STOP"
  → HardStopHandler.state = SAFE (is_safe = True)        ✅ Works
  → YandereEngine → effective level Y0                    ✅ Works (checks HardStopHandler)
  → prompt_loader → safe_mode = True                      ✅ Works (checks HardStopHandler)
  → SafeModeController.is_active = False                   ❌ NOT NOTIFIED
  → PunishmentEngine → safe_mode guard = False             ❌ PUNISHMENT CONTINUES
  → DriftCorrector → rollback deferred = False             ❌ ROLLBACK MAY EXECUTE
```

### Mitigation: Existing Defenses

Despite the gap, the following defenses exist:

1. **YandereEngine IS protected** — HARD STOP forces Y0 via `SupportsIsSafe` protocol.
2. **prompt_loader IS protected** — memory recall uses safe-mode filtering.
3. **HARD STOP blocks command processing** — `bot.py` `on_message()` returns early when `handler.is_safe` is True, preventing new slash commands from executing.
4. **Distress suspension exists independently** — if operator distress is D3+, `PunishmentEngine.check_distress_suspension()` suspends punishment via its own `SafeModeController`.

### Risk Assessment

| Risk | Severity | Likelihood | Impact |
|---|---|---|---|
| Punishment active during HARD STOP | HIGH | MEDIUM | Operator in distress, punishment tone continues |
| Drift rollback during HARD STOP | MEDIUM | LOW | Rollback could conflict with safe-word state |
| Distress undetected in messages | MEDIUM | HIGH | D2+ distress doesn't auto-trigger safe mode |
| Punishment events not persisted | LOW | HIGH | Audit trail gaps, no safety impact |
| Reward events not persisted | NONE | HIGH | No safety impact |

---

## §5 Scope Classification Summary

### P4 Scope (must fix before P4 complete):

| IP | Gap | Effort | Justification |
|---|---|---|---|
| IP-06 | cmd_safeword.py ↔ SafeModeController | MEDIUM | Safety-critical: HARD STOP must suspend punishment |
| IP-07 | Dual safe-mode bridge | MEDIUM | Architectural: unified safety facade needed |

### P4 Scope (recommended, not blocking):

| IP | Gap | Effort | Justification |
|---|---|---|---|
| IP-08 | PunishmentEngine persistence | LOW | Audit trail: follow MoodRepository pattern |
| IP-09 | RewardEngine persistence | LOW | Audit trail: follow MoodRepository pattern |

### P5 Scope (wiring, not P4 concern):

| IP | Gap | Effort | Justification |
|---|---|---|---|
| IP-04 | cmd_mood.py live data | LOW | UX: wire MoodRepository to /mood command |
| IP-05 | bot.py DistressDetector | MEDIUM | Pipeline: wire DistressDetector into on_message |

---

## §6 Recommendations

### R1: Unified Safety Facade (IP-06 + IP-07) — BLOCKING

Create a bridge that synchronizes `HardStopHandler` and `SafeModeController`:

**Option A — Adapter pattern (minimal change):**
```python
# In cmd_safeword.py or a new safety_bridge.py
from src.persona.safe_mode import SafeModeController, DistressLevel

_safe_mode = SafeModeController()

def on_hard_stop_triggered():
    """Call when HardStopHandler transitions to SAFE."""
    _safe_mode.activate(DistressLevel.D2_MODERATE)  # treat HARD STOP as D2+
```

**Option B — Unified facade (preferred):**
```python
class SafetyFacade:
    @property
    def is_safe(self) -> bool:
        return self._hard_stop.is_safe or self._safe_mode.is_active
```

Inject `SafetyFacade` into `PunishmentEngine` and `DriftCorrector` as their safety authority.

### R2: PunishmentRepository (IP-08) — RECOMMENDED

Follow the `MoodRepository` pattern:
- `PunishmentRepository.__init__(session: AsyncSession)`
- `record_punishment(level, violation_type, description, safe_word_triggered)`
- `get_punishment_history(limit=20)`

Wire into `PunishmentEngine.apply()` and `PunishmentEngine.escalate()` as post-action persistence.

### R3: RewardRepository (IP-09) — OPTIONAL

Same pattern as R2. Lower priority since rewards have no safety implications.

### R4: DistressDetector Wiring (IP-05) — P5 SCOPE

In P5, wire `DistressDetector.detect()` into `bot.py`'s `_on_message_listener()`:
```python
detector = DistressDetector()
controller = _get_safe_mode_controller()
signal = detector.detect(message.content)
controller.evaluate(signal)
```

### R5: cmd_mood.py Live Data (IP-04) — P5 SCOPE

In P5, replace degraded placeholders with `MoodRepository` queries when a DB session is available.

---

## §7 Files Audited

| File | Path | Role |
|---|---|---|
| hard_stop_handler.py | `src/core/services/hard_stop_handler.py` | P1 HARD STOP handler |
| prompt_loader.py | `src/core/services/prompt_loader.py` | P3 prompt assembly |
| models.py | `src/memory/models.py` | P3 database models (47 tables) |
| cmd_mood.py | `src/discord/cmd_mood.py` | P2 /mood command |
| cmd_safeword.py | `src/discord/cmd_safeword.py` | P2 /safeword command |
| bot.py | `src/discord/bot.py` | P2 bot entrypoint |
| yandere_fsm.py | `src/persona/yandere_fsm.py` | P4 yandere FSM |
| mood_engine.py | `src/persona/mood_engine.py` | P4 mood FSM |
| mood_persistence.py | `src/persona/mood_persistence.py` | P4 mood repository |
| drift_detector.py | `src/persona/drift_detector.py` | P4 drift detection |
| drift_corrector.py | `src/persona/drift_corrector.py` | P4 drift correction |
| punishment_engine.py | `src/persona/punishment_engine.py` | P4 punishment ladder |
| reward_engine.py | `src/persona/reward_engine.py` | P4 reward tiers |
| safe_mode.py | `src/persona/safe_mode.py` | P4 distress detection + safe mode |

---

## §8 Cross-References

| Report | Relevance |
|---|---|
| D03 Safety Boundaries | 15/15 PASS — safety boundaries correct within each module |
| D12 P4/P5 Readiness (P3) | 18/19 PASS — P3 APIs ready for P4/P5 consumption |
| D02 Code Quality | P4 code quality baseline |
| D05 Security Secrets | No secrets in P4 modules |

---

## §9 Verdict Summary Table

| IP | Integration Point | Verdict | Gap Class | Safety Risk | Fix Priority |
|---|---|---|---|---|---|
| IP-01 | HardStopHandler ↔ yandere_fsm | **PASS** | None | NONE | N/A |
| IP-02 | prompt_loader ↔ mood | **PASS** | None | NONE | N/A |
| IP-03 | models.py ↔ P4 ORM | **PASS** | None (3/5 used) | NONE | N/A |
| IP-04 | cmd_mood.py ↔ P4 | **P5 WIRING** | P5 | NONE | P5 low |
| IP-05 | bot.py ↔ DistressDetector | **P5 WIRING** | P5 | MEDIUM | P5 medium |
| IP-06 | cmd_safeword ↔ SafeMode | **GAP** | P4 | **HIGH** | P4 must fix |
| IP-07 | Dual safe-mode | **GAP** | P4 | **HIGH** | P4 must fix |
| IP-08 | PunishmentEngine ↔ DB | **GAP** | P4 | LOW | P4/P5 medium |
| IP-09 | RewardEngine ↔ DB | **GAP** | P4 | NONE | P4/P5 low |

---

## §10 Overall Verdict

**CONDITIONAL PASS**

P4 delivers 8 well-implemented persona modules with correct internal safety boundaries (D03: 15/15 PASS). Three integration points are fully compatible (IP-01, IP-02, IP-03). Two gaps are P5 wiring concerns outside P4 scope (IP-04, IP-05).

However, **two HIGH-risk integration gaps (IP-06, IP-07)** indicate that the `HardStopHandler` and `SafeModeController` safety state machines are desynchronized. This creates a scenario where HARD STOP keyword detection does NOT suspend active punishment or defer drift rollback — a direct violation of PersonaSafetyPolicy §7.2 and §14.4.

**Condition for full PASS:** IP-06 and IP-07 must be resolved with a unified safety facade or bridge that ensures HARD STOP activation propagates to `PunishmentEngine` and `DriftCorrector`.

**P4 can proceed** with the understanding that IP-06/IP-07 are tracked as blocking safety fixes and IP-08/IP-09 are recommended improvements.

---

## §11 Footer

| Field | Value |
|---|---|
| Report | D08-integration-points.md |
| Dimension | 8 of N — Integration Points |
| Files Audited | 14 files across `src/persona/`, `src/core/`, `src/discord/`, `src/memory/` |
| Cross-references | D03, D12 (P3), D02, D05 |
| Verdict | **CONDITIONAL PASS** (3 PASS, 2 P5 wiring, 2 P4 integration gap, 2 P4 persistence gap) |
| Blocking Items | IP-06, IP-07 — dual safe-mode desynchronization (HIGH safety risk) |

*Report generated: 2026-06-02*
*Auditor: Autonomous Audit Agent*
*Dimension: D08 — Integration Points*
