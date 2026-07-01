# P4 Persona Engine: Downstream Compatibility Report (P19-P24)

**Audit Date:** 2026-06-25
**Scope:** Read-only verification of P4 persona engine compatibility with P19-P24 roadmap phases.
**Method:** Source code grep, P19/P24 planning doc review, runtime surface inventory.
**Attestation:** Every claim below cites a real file:line. No fabrication.

---

## 1. P19 (Multi-Project Context) — ACTIVE BOTTLENECK

### Claim: "Shared persona stays global" is explicit

**Verdict: CONFIRMED.**

- P19 plan (`p19-multi-project-context-enterprise-plan.md:6`): "The shared persona (mood/yandere/punishment/safe-mode/HARD-STOP) stays **global**."
- P19 plan (`p19-multi-project-context-enterprise-plan.md:18`): "HARD STOP stays GLOBAL. P19 MUST NOT scope HARD STOP. This is a hard-rejection criterion."
- P19 plan architecture diagram (`p19-multi-project-context-enterprise-plan.md:93-127`): Shared persona explicitly drawn as a GLOBAL layer above all projects.

### Claim: `src/persona/` has no `project_id` references

**Verdict: CONFIRMED.**

- Grep of `src/persona/` for `project_id` returns **0 matches** across all modules.
- `src/persona/safe_mode.py:234-433` (SafeModeController), `src/persona/yandere_fsm.py:169-337` (YandereEngine) — no `project_id` in any constructor, method signature, or state.

### Claim: `session_id` references in src/persona/ are metadata-only, not scoping

**Verdict: CONFIRMED.**

- The only `session_id` references are in `src/persona/milestone_engine.py` (lines 129, 141, 253, 266, 279, 310, 486, 495, 502, 542, 597, 605). These are metadata labels for milestone recording, NOT scoping/namespace identifiers.
- Core state machines (yandere_fsm, mood_engine, punishment_engine, safe_mode, drift_detector) have zero `session_id` parameters.

### Claim: `persona.persona_state` table has no `project_id` column

**Verdict: CONFIRMED.**

- Source: `models.py:384-397`. The `PersonaState` model has columns: `id`, `state_key`, `state_value`, `updated_at`, `updated_by`. No `project_id`.
- Migration `e401bb5fd274` (lines 612-631): `op.create_table('persona_state', ...)` confirms no `project_id` column.
- Other persona schema tables (`drift_log`, `mood_history`, `punishment_log`, `reward_log`) also lack `project_id`. This is intentional — persona is global.

### Claim: Redis DB5 keys have no project-scoping

**Verdict: CONFIRMED.**

- `src/hermes/plugins/persona_plugin.py:105-120`: All 14 Redis DB5 keys use `guinevere:` prefix without project qualifier (e.g., `guinevere:mood_variant`, `guinevere:yandere_level`, `guinevere:punishment_level`).
- `src/wearable/alert_router.py:29`: `persona:state:safe_mode` is a global key.
- `src/wearable/mood_integration.py:43-44`: `persona:state:active` and `persona:state:safe_mode` are global keys.

### Assessment: Is P4 ready for P19 multi-project context?

**Verdict: READY BY DESIGN — No changes needed.**

The P19 architecture explicitly keeps persona global. P4 has zero `project_id` awareness, which is the **correct design** per the P19 constraint. No P4 changes are required for P19.

---

## 2. P20 (Living Autonomy — CLOSED)

### Claim: life_kernel has no direct imports from src.persona

**Verdict: CONFIRMED.**

- Grep of `src/life_kernel/` for `from src.persona|import src.persona` returns **0 matches**.
- `src/life_kernel/heartbeat.py:28` imports only `from src.life_kernel.state import LifeMindPhase`.
- `src/life_kernel/graph.py:15` imports only `from src.life_kernel.state import ...`.
- `src/life_kernel/cognition.py:18` imports only `from src.life_kernel.state import Priority`.

### Claim: P20 routes through Hermes agent to SafetyPlugin to P4 state

**Verdict: CONFIRMED.**

- `src/hermes/safety_plugin.py:452`: `GuinevereSafetyPlugin` lazily imports `DistressDetector` and `SafeModeController` from `src.persona.safe_mode`.
- `src/hermes/safety_plugin.py:460-468`: `HardStopHandler` is wired to `SafeModeController.force_safe_mode()` via callback.
- `src/hermes/plugins/persona_plugin.py:536-611`: `PersonaPlugin.pre_llm_call` reads P4 state from Redis DB5 and injects into Hermes prompt context.
- `src/discord/hermes_conversational.py:462-470`: Discord conversational layer imports `DistressDetector` and `SafeModeController` from `src.persona.safe_mode` for per-message distress detection.

### Claim: P20 does NOT bypass HARD STOP, consent, or Y-ceiling

**Verdict: CONFIRMED.**

- The heartbeat (`heartbeat.py:323-339`) reads `life_kernel:hard_stop` and stops on detection. This is its own safety path, independent of persona.
- `src/life_kernel/cognition.py`, `heartbeat.py`, `graph.py` — none import from `src.persona`. P20 cannot bypass persona safety controls.
- The Hermes conversational path creates `DistressDetector` + `SafeModeController` for per-message analysis.
- `src/hermes/safety_plugin.py:524`: Yandere boundary check (G07) is active.

### Claim: Heartbeat's `life_kernel:hard_stop` does not conflict/duplicate persona HARD STOP

**Verdict: TWO INDEPENDENT MECHANISMS — NO CONFLICT, BUT NO REVERSE BRIDGE.**

**Mechanism A: HardStopHandler (in-process)**
- `src/core/services/hard_stop_handler.py:34-187` — In-process state machine with `SafetyState.NORMAL`/`SafetyState.SAFE`
- Keyword detection: "hard stop", "safe word", semantic patterns (lines 42-54)
- Has `register_on_trigger()` callback system (line 66-78)

**Mechanism B: `life_kernel:hard_stop` Redis key**
- Set by HardStopHandler callback or external trigger
- Read by `heartbeat.py:323` — canonical detector for P20
- Used by `src/discord/cmd_project.py:44` to block project switching

**Bridge exists:** `safety_plugin.py:460-468` wires `HardStopHandler` → `SafeModeController.force_safe_mode()` via callback.

**No reverse bridge:** If `SafeModeController.force_safe_mode()` is called directly (e.g., by distress detection at `hermes_conversational.py:469-470`), the `life_kernel:hard_stop` Redis key is NOT set. The heartbeat would not know about persona-triggered safe-mode.

**SEVERITY:** LOW — The primary trigger path (HardStopHandler → both mechanisms) works. The edge case (direct SafeModeController activation without HardStopHandler) is unlikely in practice.

---

## 3. P21 (Voice Interface)

### Claim: No runtime code exists

**Verdict: CONFIRMED.**

- `src/voice/` does not exist (Glob returns zero files). P21 is definition/planning only.

### Claim: Text-based safety hooks apply to voice transcripts

**Verdict: PLANNING CONFIRMATION ONLY.** No runtime code to verify.

- Per P23 plan references: "HARD STOP first-class: spoken safe word to `HardStopHandler.check(transcript)` (pre-Hermes, pre-sanitize, P21 SW-PI-008) to set `life_kernel:hard_stop`."
- This confirms P21 voice transcripts will flow through the same `HardStopHandler` detection used by the text-based system.

---

## 4. P22 (Life Integration Hub)

### Claim: `AuthLevel` enum exists

**Verdict: CONFIRMED.**

- `src/mcp/auth.py:42-48`: `class AuthLevel(enum.Enum)` with 4 levels: `READ_AUTO`, `WRITE_NOTIFY`, `DESTRUCTIVE_APPROVAL`, `FORBIDDEN`.

### Claim: No persona imports in MCP auth layer

**Verdict: CONFIRMED.**

- Grep of `src/mcp/` for `from src.persona|import src.persona` returns **0 matches**.
- `src/mcp/auth.py:1-252` and `src/mcp/auth_matrix.py:1-278` contain no references to persona modules.
- `auth_matrix.py:22`: Only imports `AuthLevel` from `src.mcp.auth`.

### Claim: Safe-mode blocks MCP tool calls at Hermes agent loop

**Verdict: CONFIRMED.**

- `src/hermes/safety_plugin.py:903`: `if self._safe_mode_controller is not None and self._safe_mode_controller.is_active:` — checks safe-mode before tool execution.
- When safe mode is active, returns `{"action": "block", "reason": "CONSENT_SAFE_MODE", ...}` (lines 911-918) which vetoes the tool call.
- This runs in `pre_tool_call` hook, BEFORE the MCP `require_approval` decorator executes.
- The MCP auth layer (`src/mcp/auth.py`) never sees the call when safe mode is active.

**Is this sufficient?** YES for the current architecture. The Hermes agent loop is the single point where tool calls are dispatched. The safety plugin's `pre_tool_call` hook is called for every tool invocation.

### Claim: P22 forbids AuthLevel-only gating for L2/L3/L4

**Verdict: IMPLEMENTATION REQUIREMENT — NOT A CURRENT CODE ISSUE.**

- P22 has no runtime code. The `SemanticActionClassifier` (referenced in P23 plan) uses AuthLevel as INPUT, not as 1:1 mapping. This is a P22/P23 implementation requirement.

### Claim: P4 does NOT provide alternate action paths through MCP

**Verdict: CONFIRMED.**

- When safe mode is active, P4's `SafeModeController` provides a complete halt — no persona behavior proceeds. There is no "alternate path" that bypasses safe-mode for MCP tools.
- This is correct per PersonaSafetyPolicy.

---

## 5. P23 (Embodied Operations)

### Claim: No runtime code exists

**Verdict: CONFIRMED.**

- P23 is definition-only. No `src/actions/` or equivalent exists.

### Claim: P4 hook points exist and are public

**Verdict: CONFIRMED for three hooks.**

1. **SafeModeController.is_active** — `src/persona/safe_mode.py:422-424`:
   ```python
   @property
   def is_active(self) -> bool:
       """Whether safe mode is currently active."""
       return self.state.active
   ```
   CONFIRMED: public property, read-only.

2. **PunishmentEngine.get_state_snapshot()** — `src/persona/punishment_engine.py:500-517`:
   ```python
   def get_state_snapshot(self) -> dict[str, object]:
       """Return a serialisable snapshot of current punishment state."""
   ```
   CONFIRMED: public method, returns dict with `active`, `level`, `level_name`, `violation_type`, `started_at`, `duration_seconds`, `suspended`, `suspension_reason`.

3. **YandereEngine.get_effective_level()** — `src/persona/yandere_fsm.py:283-298`:
   ```python
   def get_effective_level(
       self,
       safe_mode: bool | None = None,
       distress: bool = False,
       crisis: bool = False,
   ) -> YandereLevel:
   ```
   CONFIRMED: public method, accepts optional safety flags, queries HardStopHandler when `safe_mode=None`.

### Flag: P23 IMPLEMENTATION DEPENDENCY

**Severity: WARNING**

P23 embodied operations need to check persona state before executing any physical action. The hook points exist, but P23 implementors must:
1. Instantiate or receive `SafeModeController`, `PunishmentEngine`, `YandereEngine` references
2. Call `is_active` / `get_state_snapshot()` / `get_effective_level()` before each action
3. Halt if safe mode is active, punishment is L4+, or yandere is at Y5 with safety override

The P23 plan references `life_kernel:hard_stop` as the canonical stop mechanism. P23 executors should check BOTH `life_kernel:hard_stop` (Redis) AND `SafeModeController.is_active` (in-memory). The `SafeModeController` is instantiated per-process in the safety plugin (`safety_plugin.py:455`), so P23 executors in the same process can query it. But executors in a different process would need the Redis fallback.

**SEVERITY:** MEDIUM — P23 implementation must wire persona state checks explicitly. The hook points are public and well-documented, but no ready-made "check before action" utility exists.

---

## 6. P24 (Hermes Fork Convergence)

### Full persona implementation surface map

| Surface | File | Role | P24 Action |
|---|---|---|---|
| P4 Persona Engine | `src/persona/` (12+ modules) | FSM core: mood, yandere, punishment, reward, drift, safe-mode, streak, milestones | Keep as-is (backend state machines) |
| PersonaPlugin | `src/hermes/plugins/persona_plugin.py` (785 lines) | Redis DB5 injection into `pre_llm_call` hook | Keep as Hermes plugin or migrate into fork internal extension |
| SafetyPlugin | `src/hermes/safety_plugin.py` (~960 lines) | 10 safety gates, bridges HardStopHandler -> SafeModeController | Keep as Hermes plugin |
| Discord conversational | `src/discord/hermes_conversational.py:462-697` | DistressDetector + SafeModeController usage | **Fix: Consolidate SafeModeController instances** |
| Wearable alert_router | `src/wearable/alert_router.py:24-29` | Stale `is_safe_mode_active` import + Redis fallback | **BUG-01: Fix stale import** |
| Wearable mood_integration | `src/wearable/mood_integration.py:44,99` | Reads Redis `persona:state:safe_mode` | **BUG-02: Dead Redis key** |
| Prompt loader | `src/core/services/prompt_loader.py:213-254` | `safe_mode` param + `hard_stop_handler.is_safe` | Keep; already uses HardStopHandler |
| Loops prompts | `src/loops/prompts.py` | `SystemPromptBuilder` with persona prompt | Keep; no persona imports |
| StateManager | `hermes-config/plugins/guinevere_safety/state_manager.py` | Redis DB5 state management (`set_punishment`, `set_mood`, etc.) | Keep in owned fork |

### Claim: Persona convergence is "extension sufficient" (no fork needed for persona)

**Verdict: CONFIRMED.**

Per P24 research (`p24-memory-kg-persona-safety-convergence-research.md:162-163`):
> "Persona is already native Hermes plugin. The FSM engines (yandere, reward, punishment, mood) are backend state machines that write to Redis DB5; the plugin reads and injects."

Per P24 research (`p24-memory-kg-persona-safety-convergence-research.md:172`):
> "Fork Required? NO. Extension sufficient. Persona is already a native Hermes plugin via the standard hook system."

The full owned fork stance (P24 plan) is justified by the P20 lifecycle requirement (heartbeat persistence), NOT by persona/safety convergence gaps.

### P24 convergence actions for persona surface

1. **Duplicate SafeModeController instances**: Two independent `SafeModeController()` instances are created:
   - `safety_plugin.py:455`: `self._safe_mode_controller = SafeModeController()` — wired to HardStopHandler callback, lives for plugin lifetime
   - `hermes_conversational.py:465`: `controller = SafeModeController()` — local to distress detection flow
   
   These have SEPARATE `SafeModeState` objects. The safety plugin's instance is activated via HardStopHandler callback; the Discord instance is not. **BUG-03: state not shared.**

2. **Fix stale wearable import**: See section 7 (BUG-01).

3. **Wire live mood into external channels**: `src/wearable/mood_integration.py:99` reads `persona:state:safe_mode` but this key is never written. See section 7 (BUG-02).

4. **PersonaPlugin registration**: `persona_plugin.py:751-784` registers via `register(ctx)` function. Already a Hermes-native plugin. P24 can keep it as external plugin or migrate into fork internal extension. **Recommendation: keep external** — no functional benefit to internalizing a stateless Redis reader.

5. **`src/persona/` as-is**: The P24 plan does not call for migrating P4 engine code into the Hermes fork. The FSM engines are backend state machines that write to Redis DB5 via `StateManager` (`hermes-config/plugins/guinevere_safety/state_manager.py`); the plugins just read. This architecture is sound.

---

## 7. Bug Register

### BUG-01: Stale wearable import — `is_safe_mode_active` does not exist in yandere_fsm.py

**File:** `src/wearable/alert_router.py:25-27`
**Severity:** MEDIUM
**Status:** CONFIRMED BUG

```python
try:
    from src.persona.yandere_fsm import is_safe_mode_active
except ImportError:
    is_safe_mode_active = None  # type: ignore[assignment]
```

The function `is_safe_mode_active` does NOT exist in `src/persona/yandere_fsm.py`. Grep of `yandere_fsm.py` for `is_safe_mode_active` and `def is_safe_mode` returns zero matches. The file has only `_is_safe_mode` as a private instance method on `YandereEngine` (line 211-216), not a module-level function.

The `try/except ImportError` catches this and sets `is_safe_mode_active = None`.

**Fallback behavior:** When `is_safe_mode_active is None`, the `_is_safe_mode_active()` method (lines 112-135) falls back to Redis key `persona:state:safe_mode`. But this key is NEVER WRITTEN by any code in the codebase (see BUG-02).

**Impact:** `AlertRouter._is_safe_mode_active()` always returns `False`. During safe-mode, non-SEV0 health alerts are NOT buffered — they are delivered normally to Discord. SEV0 alerts are correctly delivered (they bypass HARD STOP anyway at line 194-196). The safety regression is: non-SEV0 alerts will be sent during active safe-mode.

### BUG-02: Redis key `persona:state:safe_mode` is never written

**Files:** `src/wearable/alert_router.py:29`, `src/wearable/mood_integration.py:44`
**Severity:** MEDIUM
**Status:** CONFIRMED BUG

Both `alert_router.py` and `mood_integration.py` define and READ from Redis key `persona:state:safe_mode`:
- `alert_router.py:29`: `REDIS_PERSONA_SAFE_MODE_KEY = "persona:state:safe_mode"` — read at line 129
- `mood_integration.py:44`: `REDIS_PERSONA_SAFE_MODE_KEY = "persona:state:safe_mode"` — read at line 99

Grep of the entire `src/` directory for writes to this key (`.set(.*persona:state:safe_mode`) returns **zero matches**. The `StateManager` in `hermes-config/plugins/guinevere_safety/state_manager.py` writes other keys (`guinevere:mood_variant`, `guinevere:punishment_level`, etc.) but NOT `persona:state:safe_mode`.

The `SafeModeController` (`src/persona/safe_mode.py:234-433`) manages `active` as an **in-memory bool** — it does NOT write to Redis.

Tests (`tests/test_wearable.py:1589-1729`) explicitly mock `persona:state:safe_mode` as `None`, confirming the test writers expect this key to be absent by default.

**Impact:**
- `alert_router.py`: `_is_safe_mode_active()` always returns `False`. Non-SEV0 health alerts delivered during safe-mode.
- `mood_integration.py:99-101`: `is_safe_to_apply()` safe-mode check is dead code. The function still has other safety gates (consent check at line 104, persona state check at line 108), so it is not completely unprotected.

**Root cause:** The original implementation assumed someone would write `persona:state:safe_mode = "true"` to Redis when safe-mode activates. No code was ever written to do this. The `life_kernel:hard_stop` Redis key is the ONLY Redis-based safety signal, but it uses a different key name.

**Fix options:**
1. (Recommended) Modify `SafeModeController.activate()` (`safe_mode.py:345-369`) to also write `persona:state:safe_mode = "true"` to Redis, and `deactivate()` to `DEL` the key.
2. (Alternative) Change wearable modules to read `life_kernel:hard_stop` instead of `persona:state:safe_mode`.
3. (Minimal) Remove stale import, document that wearable safe-mode detection is not functional.

### BUG-03: Separate SafeModeController instances — state not shared

**Files:** `src/hermes/safety_plugin.py:455`, `src/discord/hermes_conversational.py:465`
**Severity:** LOW
**Status:** DESIGN ISSUE

Two separate `SafeModeController()` instances are created:
- `safety_plugin.py:455`: `self._safe_mode_controller = SafeModeController()` — wired to HardStopHandler callback, lives for plugin lifetime
- `hermes_conversational.py:465`: `controller = SafeModeController()` — local to distress detection flow, created per-message

These instances have separate `SafeModeState` objects. If the safety plugin's instance is activated via HardStopHandler callback, the Discord conversational layer's instance will NOT know. The converse is also true.

**Impact:** The Discord conversational layer's local `SafeModeController` is used only for distress-triggered safe-mode in the conversational flow. The safety plugin's instance is used for Hermes agent-level blocking. In practice, both should activate on the same distress detection, but the state is not synchronized.

---

## 8. DOWNSTREAM COMPATIBILITY VERDICT

### PASS (no changes needed)

| Phase | Status | Verdict | Evidence |
|---|---|---|---|
| **P19** Multi-Project Context | ACTIVE BOTTLENECK | **PASS** | Persona stays global by explicit P19 design. Zero `project_id` in `src/persona/`. `persona.persona_state` table has no `project_id` column. Redis DB5 keys are global `guinevere:` prefix. |
| **P20** Living Autonomy | CLOSED | **PASS** | life_kernel has zero imports from `src/persona/`. Decoupled via Redis (`life_kernel:hard_stop`) + Hermes agent loop. |
| **P21** Voice Interface | Definition only | **PASS** | No runtime code. P21 plan correctly references `HardStopHandler.check(transcript)`. |
| **P22** Life Integration Hub | Definition only | **PASS** | No persona imports in MCP auth layer. Safe-mode blocks at Hermes `pre_tool_call` hook (safety_plugin.py:903-918), upstream of MCP `require_approval`. |
| **P23** Embodied Operations | Definition only | **PASS with flag** | Three hook points verified public and well-documented. P23 must wire checks explicitly. No ready-made "check before action" utility. |
| **P24** Hermes Fork Convergence | Definition only | **PASS** | PersonaPlugin already native Hermes plugin. P24 research confirms "extension sufficient." Three bugs are P24 remediation targets but do not block convergence. |

### MUST FIX BEFORE P24 IMPLEMENTATION

1. **BUG-01 + BUG-02** (stale wearable import + missing Redis writer): The wearable safe-mode detection is silently broken. `is_safe_mode_active` does not exist in `yandere_fsm.py`; the Redis fallback key `persona:state:safe_mode` is never written. Fix `SafeModeController` to write to Redis, or fix the stale import and document the contract.

2. **BUG-03** (duplicate SafeModeController instances): Not critical for current operation, but will cause confusion during P24 convergence when multiple controllers have inconsistent in-memory state.

### NEEDS RUNTIME VERIFICATION

- Whether `persona:state:safe_mode` is maintained by any process outside this repository (e.g., VPS runtime scripts, external cron jobs).
- Full HARD STOP propagation path: heartbeat → checkpointer → graph → Hermes agent → SafetyPlugin → tool execution.

### Overall Verdict

**P4 PERSONA ENGINE IS COMPATIBLE WITH THE P19-P24 ROADMAP.**

The persona engine is correctly decoupled from all downstream phases. Its Hermes integration via `PersonaPlugin` is already native. Its safety integration via `GuinevereSafetyPlugin` is already native. The P19 plan explicitly keeps persona global. P20 does not touch persona. P23 hook points are public and well-documented. P24 convergence requires no migration of persona code — only bug fixes in the wearable integration layer.

---

*Audit conducted via read-only verification of source code and planning documents. All claims cite file:line references. No runtime code was modified.*
