# P4 Persona Engine: Downstream Impact Mapping (P3, P5, P7, P8, P11-P14, P19-P24)

**Audit Date:** 2026-06-25
**Scope:** Read-only mapping of every downstream phase's integration/dependency on `src/persona/` (mood FSM, yandere FSM, safe-mode, punishment, reward, drift, streak, rituals).
**Method:** grep + file reads of every integration touchpoint. No runtime code was modified.

---

## P3 Memory — Mood Persistence

### Dependency Surface

- `src/persona/mood_persistence.py:83` — `class MoodRepository` depends on `src.memory.models.MoodHistory` (line 24) and `src.memory.models.PersonaState` (line 24) for DB CRUD.
- `src/persona/streak_tracker.py:29` — imports `PersonaState` from `src.memory.models`.
- `src/memory/models.py:455-471` — `class MoodHistory` in schema `persona` (line 457), columns: `mood`, `intensity`, `trigger`, `duration_minutes`, `recorded_at`.
- `src/memory/models.py:413-426` — `class PersonaState` in schema `persona` (line 415), columns: `state_key`, `state_value` (JSONB), `updated_at`, `updated_by`.
- `src/memory/models.py:126-127` — `SessionSummary` has `mood_at_start` / `mood_at_end` (nullable Text).
- `src/memory/models.py:335` — `TaskCompletionEvent` has `mood_self_report` (nullable Text).
- `src/memory/read_pipeline.py:82-85` — read pipeline classifies `mood`, `punishment` as content tags (keyword pass-through for the emotion signal).

### Compatibility Assessment

| Aspect | Assessment |
|---|---|
| Schema ownership | Shared between `src/memory/models.py` (ORM definitions) and `src/persona/mood_persistence.py` (queries). No conflict. |
| MoodRepository instantiation | `MoodRepository(session: AsyncSession)` — requires a DB session; **no singleton**, safe for per-request session injection. |
| Global mood key | `PersonaState.state_key='current_mood'` is a single global key (`mood_persistence.py:31`). No `project_id` column. P19 plans to backfill; P4 is unaffected. |
| Blocker risk | None. P3 already provides the tables; P4 writes into them. |

### Verdict
**No blocker.** P3 provides the storage layer that P4 consumes. Shared `persona.*` schema tables.

---

## P5 Agent Loop — Persona State Consultation

### Dependency Surface

- `src/hermes/plugins/persona_plugin.py:471` — `class PersonaPlugin` injects mood/yandere/punishment state into every LLM call via `pre_llm_call` hook.
- `src/hermes/plugins/persona_plugin.py:533-606` — `pre_llm_call()` reads `mood_variant`, `yandere_level`, `punishment_level` from Redis DB5 and injects a `[PERSONA STATE]` block into the system prompt.
- `src/hermes/plugins/persona_plugin.py:618-704` — `post_llm_call()` runs milestone detection. `pre_tool_call()` reads punishment state to decide if tool calls are blocked/restricted.
- `src/hermes/safety_plugin.py:452-537` — `GuinevereSafetyPlugin` instantiates `SafeModeController`, `YandereEngine`, `DistressDetector` from `src.persona` as safety gates before every LLM call.
- `src/hermes/safety_plugin.py:543-637` — G01 (HARD STOP), G02 (distress), G07 (yandere boundary) — all gate the LLM loop using persona modules.
- `src/discord/hermes_conversational.py:454-489` — Lazy-imports `SafeModeController`, `DistressDetector`, `Mood` from `src.persona` for the conversational handler (user-facing Discord agent loop).
- `src/loops/prompts.py:112-134` — `SystemPromptBuilder` accepts `persona_prompt` string and includes a `## Persona` section. The resolution is a compiled string from `docs/60-persona/61-SystemPromptMaster_v1.1.md`, not a live FSM query.

### Phase 5 Ritual Deprecation Verification

The P4 `__init__.py` (lines 128-149) conditionally imports ritual modules with `DeprecationWarning`, stating: "Scheduled removal: Phase 7" (comment at line 6). **Phase 7 did NOT remove them** — the deprecated imports are still present and the ritual files (`src/persona/rituals/`) remain on disk. The replacement was supposed to be "Hermes cron + PersonaPlugin" (per ritual docstrings, e.g., `rituals/afternoon.py:11`).

**Findings:**
- Rituals were deprecated in the P4 init but **Phase 7 never removed them** — they still work (conditional import under `warnings.catch_warnings()`).
- No evidence of a Hermes cron-based replacement actually running.
- The `ritual_scheduler.py` module and all ritual files are still present on disk.

### Compatibility Assessment

| Aspect | Assessment |
|---|---|
| PersonaPlugin | Works: injects persona state per-LLM-call. State is read from Redis DB5 global keys. **No per-session/session_id scoping** — all sessions see the same mood/yandere/punishment. |
| SafetyPlugin | Works: G01/G02/G07 gate every LLM call using per-session state (`_get_session_state` at safety_plugin.py:561). Session-level state tracking exists for HARD STOP, safe-mode, yandere. |
| Ritual deprecation | **Partially completed.** Deprecated at import level but removal was never done. Hermes cron replacement not found. |
| Blocker risk | **Low.** The agent loop correctly consults P4 state before acting. Yandere/safe/punishment state flows into every tool call + LLM call. |

### Verdict
**Compatible.** The agent loop (Hermes + Discord conversational) properly gates on P4 state. Ritual deprecation is stale but not harmful.

---

## P7 Surveillance — Persona/Safe-Mode/Consent Boundaries

### Dependency Surface

- `src/surveillance/consent_gate.py:1-283` — Independent consent-gate module. **Does NOT import `src.persona`.** It has its own `ConsentStatus` enum (`src/surveillance/consent_gate.py:66`) and `check_consent(scope)` function. Uses Redis DB2 cache + `consent.consent_ledger` table.
- `src/surveillance/__init__.py` — no persona imports found.
- `src/hermes/safety_plugin.py:59-89` — HardStopHandler keyword detection (HARD STOP, "break character", "restore persona") which eventually wires into `SafeModeController.force_safe_mode()` (safety_plugin.py:460-468).
- **P7 surveillance does not directly invoke P4 safe-mode.** The bridge is through `HardStopHandler -> SafeModeController.force_safe_mode()` in `src/hermes/safety_plugin.py`.

### Compatibility Assessment

| Aspect | Assessment |
|---|---|
| Direct P4 dependency | **None.** Surveillance consent gate is standalone. |
| Safe-mode bridge | Indirect: `HardStopHandler` triggers `SafeModeController.force_safe_mode()` via callback in safety_plugin.py. |
| Blocker risk | **None.** Surveillance P7 consent operates at a different layer (surveillance scope consent) from P4 persona safety (distress/safe-mode). |

### Verdict
**Compatible and decoupled.** P7 surveillance consent and P4 safe-mode are separate subsystems bridged only through the safety plugin.

---

## P8 MVP Observability — Persona Metrics/Logs

### Dependency Surface

- `src/observability/sentry_integration.py:42-44` — Drops events matching paths `persona-safety`, `surveillance-raw`, `consent-revocation`, `hard-stop`. **Actively suppresses persona-safety events from Sentry.**
- `src/observability/windows_metrics.py:147-186` — `wire_consent_hook()` connects the `windows_consent` subsystem drop counter to Prometheus. References `WindowsConsentDecision`, not persona.
- No direct Prometheus counters for `mood_variant`, `yandere_level`, `punishment_level` were found in `src/observability/`.

### Compatibility Assessment

| Aspect | Assessment |
|---|---|
| Persona metrics surfaced | **No.** No Prometheus/Grafana counters exist for persona state. Sentry actively drops `persona-safety` tagged events. |
| Persona structlog | Every P4 module uses `structlog` — the logs are written but no observability dashboard consumes them. |
| Blocker risk | **Low.** Observability gap for persona state, but P8 MVP doesn't require it. P19/P23 plans mention observability of persona state (future). |

### Verdict
**Gap identified.** P4 persona state is not surfaced in observability dashboards. Sentry actively drops persona-safety events. Structlog messages exist but are not aggregated.

---

## P11/P12/P13/P14 — External Channels & Persona Behavior

### Dependency Surface

- **P11 WhatsApp:**
  - `src/channels/whatsapp/bridge.py:163` — calls `get_system_prompt_with_context(memories=None, mood="Content")` — **hardcodes mood="Content"**, does not query live P4 mood.
  - `src/channels/whatsapp/consent_manager.py` — WhatsApp-specific consent gate (P11-016), independent of P4.
  - `src/channels/whatsapp/ops_commands.py:90-133` — reads `safe_mode` from `HardStopHandler`, reads `consent_granted` state — uses P4 safe-mode indirectly through the pipeline.
  
- **P12 Gmail:**
  - `src/gmail/bridge.py:39` — `HermesRefusedError` for "safety block, persona constraint".
  - `src/gmail/bridge.py:530,584` — calls `get_system_prompt_with_context(memories=None, mood="Content")` — again **hardcodes mood="Content"**, not live P4 mood.
  - `src/gmail/draft/generator.py:30` — has `PersonaLeakError`, no persona imports found.
  - `src/gmail/consent_manager.py` — email consent (surveillance scope), independent of P4.
  
- **P13/P14 X/Twitter/Finance:**
  - `src/x_poster/` — **No persona imports found.** No P4 dependency.
  - `src/finance/`, `src/financial/` — **No persona imports found.** One comment about "personal finance tracking" in `src/finance/db.py:26`.

### Compatibility Assessment

| Aspect | Assessment |
|---|---|
| Live persona mood in channels | **Not wired.** `bridge.py` in both WhatsApp and Gmail hardcode `mood="Content"`. The live P4 mood FSM state is NOT consulted. |
| Safe-mode in channels | **Partially wired.** WhatsApp `ops_commands.py` reads `HardStopHandler.is_safe` to decide routing. |
| Yandere influence on outbound behavior | **Not found.** No evidence yandere level influences channel response tone. |
| P14 finance | **No dependency.** |
| Blocker risk | **Medium.** Mood/Variant/Persona behavior does not flow into external channels. Users on WhatsApp or email always see "Content" mood, never the actual persona state. This is an integration gap, not a safety violation. |

### Verdict
**Integration gap.** External channels (WhatsApp, Gmail) hardcode `mood="Content"` instead of reading live P4 state. Yandere/safe-mode/punishment do not influence channel behavior. Not a blocker but an incomplete integration.

---

## P19 Multi-Project Context — CRITICAL GLOBAL VS PER-PROJECT PERSONA STATE

### Dependency Surface (What P19 Touches)

- `src/persona/mood_persistence.py:31` — `_CURRENT_MOOD_KEY = "current_mood"` — **single global key** in `persona.persona_state` table.
- `src/persona/mood_persistence.py:256` — `_MOOD_STREAK_KEY = "mood_streak"` — **single global key**.
- `src/persona/yandere_fsm.py:169` — `YandereEngine` — instance stored in `safety_plugin.py:526` as `self._yandere_engine`. **Per-safety-plugin-instance, not per-session.**
- `src/persona/safe_mode.py:234` — `SafeModeController` — instance in `safety_plugin.py:455` as `self._safe_mode_controller`. **Per-safety-plugin-instance.**
- `src/persona/punishment_engine.py:221` — `PunishmentEngine` — not directly instantiated in safety_plugin or persona_plugin; it is a standalone construct.
- `src/hermes/plugins/persona_plugin.py:104-106` — Redis DB5 keys: `guinevere:mood_variant`, `guinevere:yandere_level`, `guinevere:punishment_level`, `guinevere:last_interaction`. **All global keys, no project_id prefix.**

### Instantiation Pattern Analysis

| Component | Instantiation | Per-Project? |
|---|---|---|
| `YandereEngine` | `safety_plugin.py:526` — one instance per `GuinevereSafetyPlugin` instance. Hermes agent creates one plugin instance. **Effectively singleton.** | **No.** All sessions share the same yandere level. |
| `SafeModeController` | `safety_plugin.py:455` — one instance per plugin. Also `discord/hermes_conversational.py:457` creates a second instance. **Two instances, but each is a singleton in its scope.** | **No.** Safe mode is a global shutdown signal. This is **intentional** per P19 design. |
| `MoodRepository` | Not instantiated at module level. Requires `AsyncSession`. Injected per-session. **Stateless repository pattern.** | **Yes, per-DB-session.** But writes to a global `current_mood` key. The key itself is global, not the instance. |
| `PersonaPlugin` | `src/hermes/plugins/persona_plugin.py:766` — `plugin = PersonaPlugin()`. One instance per agent. | **No.** Reads global Redis DB5 keys. |
| `PunishmentEngine` | Not instantiated globally. Would be per-component. | **Depends on owner component.** Not a blocker. |

### P19's Own Design on Persona

Per the P19 enterprise plan (multiple sources):
- "The shared persona (mood/yandere/punishment/safe-mode/HARD-STOP) stays **global**" — P19 plan line 7.
- "Shared persona no cross-project memory leak" — P19 final report line 60, **PASS**.
- "Shared persona stays global (mood/yandere/punishment/safe-mode)" — P19 definition verification line 76.
- "HARD STOP stays GLOBAL" — P19 plan line 19 (hard-rejection criterion).
- P19 explicitly chose to NOT scope persona per project.

### Compatibility Assessment

| Aspect | Assessment |
|---|---|
| Per-project persona state | **Not needed by design.** P19 explicitly keeps persona global. All sessions/projects share mood, yandere level, safe-mode. |
| Cross-project state leak | **Intentional.** Persona mood/yandere from project A IS visible to project B. P19 calls this a "shared persona" feature, not a bug. |
| HARD STOP scope | **Global by design.** P19 hard-rejects scoping HARD STOP. |
| Memory isolation (separate) | Persona **memories** get `project_scope='global'` — visible from all projects. Non-persona memories get `project_scope='project'` — isolated. See P19 plan §P19-011 backfill rules. |
| Blocker risk | **Low.** P4's global singleton state is not a P19 compatibility problem — it is the intended architecture. |

### Verdict
**Compatible by design.** P19 explicitly keeps the persona engine global. The only risk is if P19 implementation accidentally introduces project-scoped persona keys that collide with global ones — but the P19 plan fully documents the design. P4 provides `persona.persona_state` and Redis DB5 keys, both global — P19 does not need them to be otherwise.

---

## P20 Living Autonomy Kernel (CLOSED) — Persona Engine Interaction

### Dependency Surface

- `src/life_kernel/` — **No direct imports from `src.persona` found.** grep for `from.*persona` and `import.*persona` returned zero results across all `.py` files in `src/life_kernel/`.
- `src/life_kernel/cognition.py:405` — references "HARD STOP safety, consent boundaries" in a code comment only.
- `src/life_kernel/sensor_adapters/` — no persona imports.
- `src/life_kernel/heartbeat.py` — no persona imports.
- `src/life_kernel/graph.py:699,826,908` — comments about "personal/episodic" privacy boundaries, but no P4 imports.
- `src/life_kernel/hermes_brain.py:103` — mentions "full persona" in a docstring reference — this is about the system prompt, not the P4 engine.

### Hard Stop / Consent / Y-Ceiling Bypass Check

- `src/life_kernel/cognition.py:405-412` — Has the comment mentioning HARD STOP and "secret leakage" — appears to be awareness, not bypass.
- P20 `sensor_adapters/gmail_adapter.py:12` defers to consent gate.
- P20 `sensor_adapters/surveillance_adapter.py:11-20` explicitly notes "access is consent-gated."
- P20 `sensor_adapters/wearable_adapter.py:12` references operator consent.
- **No evidence of P4 bypass found in P20.** The life kernel defers consent/safety checks to the Hermes agent loop (where P4 is enforced via PersonaPlugin + SafetyPlugin).

### Compatibility Assessment

| Aspect | Assessment |
|---|---|
| Direct P4 imports | **None.** P20 does not directly call YandereEngine, SafeModeController, or MoodRepository. |
| Indirect P4 use | P20 routes through Hermes agent → SafetyPlugin → P4 state. This is the correct architecture. |
| HARD STOP bypass | **Not found.** P20 cognition.py mentions HARD STOP as a boundary to respect. |
| Consent bypass | **Not found.** Sensor adapters are consent-gated. |
| Blocker risk | **Low.** P20 and P4 are architecturally separated: P4 lives in the Hermes agent's safety/plugin layer; P20 owns the autonomous loop (heartbeat/cognition/graph). P4 safety is enforced before P20 actions reach the user. |

### Verdict
**No bypass found.** P20 autonomy routes through Hermes safety (which gates on P4 state). No direct P4 imports or bypasses in life_kernel code.

---

## P21 Voice Interface — Persona Impact

### Dependency Surface

- **No runtime code exists.** `src/voice/` does not exist. P21 is definition-only.
- P21 plan states: "a voice transcript is text, so the existing text-based safety hooks (HARD STOP, distress, injection-sanitization) apply unchanged."
- P21 would reuse the same `PersonaPlugin` for persona state injection into LLM prompts.

### Compatibility Assessment

| Aspect | Assessment |
|---|---|
| Voice uses P4 | **By design — when implemented.** Text-based safety hooks apply to voice transcripts. |
| TTS voice persona | P21 plan mentions "consented persona voice" but no implementation. |
| P4-not-blocker | Correct. P4 does not block P21. |
| Blocker risk | **None.** P21 will reuse existing P4 safety when implemented. |

### Verdict
**No blocker.** P21 definition correctly scopes P4 reuse.

---

## P22 Life Integration Hub — AuthLevel Gating vs Persona

### Dependency Surface

- `src/mcp/auth.py:42` — `class AuthLevel` enum: `READ_AUTO`, `WRITE_NOTIFY`, `DESTRUCTIVE_APPROVAL`, `FORBIDDEN`.
- `src/mcp/auth_matrix.py` — Maps tools/operations to AuthLevel. **This is MCP-level auth, not P4 persona.** P4 does NOT bypass AuthLevel checks.
- **No direct persona imports found in P22 definition docs.** P22 plan says consent boundaries are per-project, not persona-scoped.
- P22 plan explicitly states: "Default permission tier is READ (L1) for all integrations. Write/destructive operations require explicit consent per L2-L4 gates."

### AuthLevel in Persona Context

grep for `AuthLevel` in `src/persona/` returned zero results. P4 does not know about or override AuthLevel. P4 safe-mode / yandere / punishment act at a different layer (persona behavior), not at the MCP tool-auth layer.

### Compatibility Assessment

| Aspect | Assessment |
|---|---|
| Persona bypass of AuthLevel | **Not found.** P4 does not know about AuthLevel. P4 state does not affect MCP tool authorization. |
| Safe-mode vs AuthLevel | **Not wired.** When P4 safe-mode is active, MCP tools do not automatically block at the AuthLevel layer — the block happens at the Hermes agent loop (SafetyPlugin blocks the LLM from calling tools). Not a raw AuthLevel bypass. |
| Yandere bypass | **Not found.** Yandere level does not influence AuthLevel. |
| Blocker risk | **Low.** P4 and P22 operate at different layers (persona behavior vs tool authorization). They do not conflict. |

### Verdict
**Compatible and decoupled.** P4 persona safety and P22 AuthLevel operate at different layers. No bypass found.

---

## P23 Embodied Operations / Action Layer — Persona Safety Boundaries

### Dependency Surface

- **No runtime code exists.** `src/life_kernel/executors/` does not exist. P23 is definition-only.
- P23 plan specifies: `SemanticActionClassifier` will classify actions into L1-L4 risk tiers. AuthLevel is an **INPUT**, not 1:1 (Codex P1-2 fix).
- P23 plan specifies: consent boundary, HARD STOP global cancellation, safe-mode/distress freeze, rollback.
- P4 safe-mode is designed to **suspend all persona behavior** — P23 would respect this.
- P23 plan (P23-005..010) describes executors gated by consent + safe-mode.

### Compatibility Assessment

| Aspect | Assessment |
|---|---|
| Punishment overflow risk | P23 executor limits are defined by `PunishmentEngine` level + `allowed_actions`. P4 `PUNISHMENT_CONFIG` (punishment_engine.py:110-193) defines per-level allowed/blocked actions. P23 should map these to allowed executor domains. **Not yet wired.** |
| Consent bypass | P23 plan requires consent boundary. Not yet implemented. |
| Safe-mode/distress freeze | P23 plan includes this. When safe-mode is active, all P23 actions should be blocked. **Design exists but unimplemented.** |
| Yandere influence on action tier | Not specified in P23 plan. Yandere level may influence tone but should not affect classification. No conflict. |
| Blocker risk | **Low at definition level.** When P23 implements, it must wire to P4 safe-mode/punishment/consent boundaries. The P4 API supports this (`SafeModeController.is_active`, `PunishmentEngine.get_state_snapshot`, `YandereEngine.get_effective_level`). |

### Verdict
**Definition-compatible.** P23 plans correctly reference P4 safety boundaries. When implementation starts, the hook points exist (get_state_snapshot, is_active, etc.). No design conflict.

---

## P24 Hermes Fork Convergence — Persona Engine Surface Map

### Persona Implementation Surface Identification

The persona engine exists in multiple locations:

| Location | File | Role |
|---|---|---|
| **src/persona/** (19 files) | Core engine | Mood FSM, yandere FSM, safe-mode, punishment, reward, drift, streak, rituals (deprecated). **Primary source of truth.** |
| **src/hermes/plugins/persona_plugin.py** | Hermes PersonaPlugin | Reads Redis DB5 global keys, injects `[PERSONA STATE]` block. Thin Redis reader, no duplicate logic. |
| **src/hermes/safety_plugin.py** | GuinevereSafetyPlugin | Imports and instantiates `YandereEngine`, `SafeModeController`, `DistressDetector`. Maintains session-level state for these. |
| **src/hermes_plugins/commands_high/mood.py** | /mood command | Display-only. Reads mood state from (presumably) PersonaPlugin or direct Redis. **Not a source of truth.** |
| **src/hermes_plugins/commands_system/punishment.py** | Punishment command | Displays punishment state. Thin wrapper. |
| **src/hermes_plugins/commands_system/consent.py** | Consent command | Discord consent management. Independent of P4 (consent.consent_ledger). |
| **src/discord/hermes_conversational.py:454-489** | Conversational handler | Lazy-imports SafeModeController, DistressDetector, Mood. Second instance of SafeModeController. |
| **src/discord/cmd_mood.py** | Discord /mood | Purely display. Reads mood from unknown source (placeholder strings: "Content" default). |
| **src/wearable/alert_router.py:25-131** | Wearable alert router | Imports `is_safe_mode_active` (deleted from yandere_fsm — stale import). Falls back to Redis key `persona:state:safe_mode`. |
| **src/wearable/mood_integration.py:33** | Wearable mood modifier | Imports `Mood` from `src.persona.mood_engine`. GHI -> mood modifier. |
| **src/core/services/prompt_loader.py:41** | System prompt loader | `get_system_prompt_with_context(mood="Content")` — hardcoded mood default. Used by Gmail/WhatsApp bridges. |
| **src/loops/prompts.py:112-134** | Loop prompt builder | Accepts `persona_prompt` string. Source: Static SystemPromptMaster doc, not live P4 FSM. |

### Architecture Assessment: Split, Superseded, or Still Owned?

| Claim | Assessment |
|---|---|
| **Solely owned by src/persona/** | **Partially false.** The core FSM logic is in `src/persona/`, but the **runtime instantiation** is split across `src/hermes/plugins/persona_plugin.py` (Redis reader), `src/hermes/safety_plugin.py` (YandereEngine + SafeModeController), and `src/discord/hermes_conversational.py` (second SafeModeController). |
| **Split** | **Yes.** `YandereEngine` is instantiated in `safety_plugin.py:526`. `SafeModeController` is instantiated in both `safety_plugin.py:455` and `discord/hermes_conversational.py:457`. There are **two SafeModeController instances** in different subsystems. `PersonaPlugin` in `persona_plugin.py` is a separate Redis-based reader. |
| **Superseded** | **No.** No newer engine supersedes `src/persona/`. The plugins are consumers, not replacements. |
| **Must adapt for P24** | **Low priority.** P24 convergence research (`p24-memory-kg-persona-safety`) rates persona convergence as "Extension sufficient" — PersonaPlugin + SafetyPlugin hooks already integrate with Hermes. The split is manageable. |

### Key Finding: Stale Import in Wearable

`src/wearable/alert_router.py:25` imports `is_safe_mode_active` from `src.persona.yandere_fsm`, but grep confirms `is_safe_mode_active` does NOT exist in `yandere_fsm.py` (the function `_is_safe_mode` exists as a private method of `YandereEngine`). The import at `alert_router.py:25` is wrapped in a try/except (line 26 handles the ImportError by setting `is_safe_mode_active = None`), so it degrades gracefully to a Redis fallback. But the import is **stale** — the symbol was removed from yandere_fsm.py and only the try/except prevents a crash.

### Verdict
**Split architecture.** Core logic is in `src/persona/`. Runtime ownership is distributed across `src/hermes/plugins/` and `src/discord/`. Not superseded, not consolidated. P24 may want to consolidate the duplicate `SafeModeController` instances and fix the stale wearable import.

---

## P4 OWNERSHIP VERDICT

**The persona engine is NOT solely owned by `src/persona/`.** The architecture is **split**:

1. **Core FSM logic** is in `src/persona/` (19 files) — mood, yandere, safe-mode, punishment, reward, drift, streak. This is the source of truth for **logic**.

2. **Runtime instantiation** is distributed:
   - `src/hermes/safety_plugin.py` owns the `YandereEngine` and `SafeModeController` instances for the Hermes agent loop.
   - `src/hermes/plugins/persona_plugin.py` owns the `PersonaPlugin` (Redis DB5 reader) for state injection.
   - `src/discord/hermes_conversational.py` owns a **second** `SafeModeController` instance for the Discord conversational handler.
   - `src/wearable/alert_router.py` has a stale import that degrades to Redis fallback.

3. **External channels** (WhatsApp, Gmail) hardcode `mood="Content"` instead of reading live P4 state — an integration gap.

4. **P20 life_kernel** has zero direct P4 imports — routing through Hermes safety is the correct architecture.

5. **P19 explicitly keeps persona global** — no per-project scoping needed.

6. **P22/P23/P24 are definition-only** — no runtime conflicts. Design documents reference P4 correctly.

**No supersession has occurred.** No newer component replaces `src/persona/`. The split is between "owning the logic" (src/persona/) and "owning the instances" (plugins/consumers).

### Recommendations from This Audit

1. **Fix stale import** in `src/wearable/alert_router.py:25` — `is_safe_mode_active` was removed from `yandere_fsm.py`.
2. **Consolidate SafeModeController instances** — there are two independent instances (safety_plugin.py + hermes_conversational.py). They cannot share state. Consider a singleton or shared Redis state.
3. **Wire live P4 mood into external channels** — WhatsApp and Gmail bridges hardcode `mood="Content"` and should read the actual mood variant.
4. **Observe **P19 implements memory isolation** — ensure the `persona.persona_state` global keys are NOT accidentally scoped. P19 plan says they stay global, but the backfill must preserve this.
5. **No P20 bypass found** — continue to route autonomy through Hermes safety (which gates on P4 state).
