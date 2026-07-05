# P21 Voice Interface — Round 2 Audit: Hermes Integration

**Auditor:** Independent Hermes-integration auditor (Round 2)  
**Date:** 2026-06-24  
**Scope:** Verify that round-1 findings (A1, A9) are closed in the amended plan; re-verify send_message reuse, cost tags, shadow pipeline reuse, DRY enforcement; cite file:line for all claims.

---

## Audit Method

1. Read the amended P21 enterprise plan (`docs/setup-evidence/P21/plan/p21-voice-interface-enterprise-plan.md`), especially the "Audit Round-1 Amendments" section (lines 456-481).
2. Read the round-1 hermes-integration audit (`docs/setup-evidence/P21/evidence/audits/round-1/hermes-integration.md`).
3. Verify that round-1 findings A1 and A9 are addressed in wave scaffolds.
4. Re-verify the current source code state against the plan's integration claims.
5. Confirm that the plan's hold on implementation (blocked on P20 pass) is documented.

---

## Round-1 Finding Closure

| Finding | Round-1 Status | Amendment ID | Round-2 Status | Evidence |
|---------|----------------|--------------|----------------|----------|
| **A1**: `ProcessedTurn` not in source; refactor seam design-only; `_process_and_respond()` returns `bool` + calls `channel.send()` directly (architecture, hermes-integration) | CRITICAL GAP | A1 | **CLOSED** | Plan line 462: P21-003 pre-condition mandates `_process_turn_core()` refactor returning `ProcessedTurn`; `ProcessedTurn` defined in shared location (`src/voice/types.py` or `src/core/turn_types.py`); unit test must prove `source_type="voice"` invokes without importing `discord.TextChannel`. Wave 3 scaffold (line 377-385) requires no regression in existing Discord text tests. |
| **A9**: `store_conversation()` hardcodes `source="discord_conversation"`; `source_type` param missing (surveillance-privacy, hermes-integration) | MISSING PROVENANCE | A9 | **CLOSED** | Plan line 470: P21-003 deliverable adds `source_type: str = "discord"` kwarg to `HermesMemoryBridge.store_conversation()` (`src/hermes/_memory_bridge.py:217-313`); dynamic `source`/`tags`; test must prove voice episodes carry `source="voice_conversation"` + `["voice","chat",...]`. |

**Closure verdict:** Both A1 and A9 are **CLOSED** in the amended plan. The wave scaffold for P21-003 (lines 377-385, 462, 470) is binding, specific, and testable. Implementation is gated on P20 production-pass per the hold rule (line 18).

---

## Re-Verification: Current Source Code State vs. Plan Claims

### 1. `_process_turn_core()` Refactor Seam — STILL DESIGN-ONLY (expected)

**Source:** `src/discord/hermes_conversational.py:427-691`

The current `_process_and_respond()` function:
- Lines 427-433: Signature is `async def _process_and_respond(bot: Any, author: Any, channel: Any, content: str, start_time: float) -> bool`
- Lines 552, 572, 577: Calls `await channel.send(FALLBACK_MESSAGE)` directly (Discord-specific)
- Line 498: Derives session factory via `getattr(bot, "get_session_factory", None)`
- Line 589: Derives shadow pipeline via `getattr(bot, "shadow_pipeline", None)`
- Line 654-660: Calls `bridge.store_conversation(user_message=content, assistant_response=response_text, user_id_hash=user_id_hash, safe_mode=safe_mode_activated)` without `source_type`

**Plan claim (line 209-218):**
```python
async def _process_turn_core(
    *, content: str, author_id: str, channel_id: str,
    session_factory: AsyncSessionFactory | None,
    shadow_pipeline: ShadowPipeline | None,
    source_type: str = "discord",
) -> ProcessedTurn:
    """Shared turn core. Runs Steps 7-13: distress → mood → memory recall
    → system prompt → Hermes → cost → auto-store → shadow. Caller delivers response."""
```

**Status:** The refactor seam does **not exist** in source (unchanged from round 1). This is expected because this is the planning phase; Wave P21-003 (blocked on P20 pass) will implement it.

**Round-2 check:** PASS — the plan documents the seam correctly and gates it behind P20 pass (line 79, 378). The amendment A1 (line 462) specifies the exact deliverable.

### 2. `ProcessedTurn` Type Definition — NOT IN SOURCE (expected)

**Source:** `grep -R "ProcessedTurn" C:\Users\faizz\guinevere\src` returned no matches.

**Plan claim (line 44, 462):** `ProcessedTurn` will be defined in `src/voice/types.py` or a shared `src/core/turn_types.py`.

**Status:** The type does **not exist** in source (unchanged from round 1). This is expected; Wave P21-003 will define it.

**Round-2 check:** PASS — A1 (line 462) requires `ProcessedTurn` in a location importable by both `src/discord/` and `src/voice/`. This is binding.

### 3. `store_conversation()` Source Type Provenance — NOT IN SOURCE (expected)

**Source:** `src/hermes/_memory_bridge.py:216-313`

Current implementation:
- Lines 216-223: Signature is `async def store_conversation(self, user_message: str, assistant_response: str, user_id_hash: str, *, safe_mode: bool = False) -> str | None` (no `source_type` param)
- Line 274: Hardcodes `source="discord_conversation"`
- Line 280: Hardcodes `tags=["discord", "chat", f"user:{user_id_hash}"]`

**Plan claim (line 80, 470):** Add `source_type: str = "discord"` kwarg; dynamic `source`/`tags`.

**Status:** The provenance parameter does **not exist** in source (unchanged from round 1). This is expected; Wave P21-003 will add it.

**Round-2 check:** PASS — A9 (line 470) specifies the exact file:line (`src/hermes/_memory_bridge.py:217-313`) and the required change. The test requirement ("voice episodes carry `source="voice_conversation"` + `["voice","chat",...]`") is binding.

### 4. `HermesSessionAdapter.send_message()` Reuse — PASSES

**Source:** `src/hermes/_session_adapter.py:184-312`

Current implementation:
- Lines 184-189: Signature is `async def send_message(self, user_id: str, content: str | list[dict[str, Any]], system_prompt: str) -> str`
- Lines 235-240: LLM call is synchronous, offloaded via `asyncio.to_thread(agent.run_conversation, ...)`
- Lines 252-259: Returns full response string `final_response`

**Characteristics:**
- Non-streaming (returns full text before TTS can start)
- Surface-agnostic (text-in/text-out, no Discord/voice-specific logic)
- No modification required for voice reuse

**Plan claim (line 84, 220):** Voice adapter calls `_process_turn_core(content=transcript, source_type="voice")` → response text → TTS. `HermesSessionAdapter.send_message()` reused as-is (non-streaming MVP).

**Round-2 check:** PASS — the source confirms non-streaming text-in/text-out. The plan correctly identifies this as MVP-acceptable with streaming-Hermes deferred to Phase-2 (A2, line 463).

### 5. STT/TTS Cost Tags (`stt:*`, `tts:*`) — DESIGN SUPPORTED

**Source:** `src/core/services/cost_tracker.py:25-53`

Current implementation:
- Lines 25-26: Signature is `def record_cost(self, model: str, input_tokens: int, output_tokens: int, cost_per_1k_input: float, cost_per_1k_output: float)`
- Line 37: Increments `cost:by_model:{model}` for any arbitrary model string

**Plan claim (line 27, 57, 313-314):** Voice STT/TTS costs feed `CostTracker.record_cost()` with model tags `stt:*`, `tts:*`, `realtime:*`; voice sub-cap within system cap.

**Round-2 check:** PASS — the tracker is model-agnostic and accepts any tag. No code change required. Voice cost recording (Wave P21-001, line 57) will call `record_cost(model='stt:deepgram-nova', ...)` etc.

### 6. Shadow Pipeline Reuse — PASSES

**Source:** `src/discord/shadow_pipeline.py:118-124`

Current signature:
```python
async def shadow_forward(
    self,
    message_content: str,
    bot_response: str,
    user_id: str,
    channel_id: str,
) -> dict[str, Any]:
```

All parameters are strings. A voice turn can pass `message_content=transcript`, `bot_response=response_text`, `user_id=author_id`, `channel_id="voice"`.

**Plan claim (line 56, 220):** Shadow pipeline reused; voice passes transcript/response as strings.

**Round-2 check:** PASS — the interface is surface-agnostic. No modification required.

### 7. DRY / Safety-Hook Duplication — CRITICAL, GATED ON WAVE 3

**Source:** `src/discord/hermes_conversational.py:427-691`

Current state: Steps 7-13 (distress, mood, memory recall, Hermes, shadow, cost, auto-store, logging) are embedded in `_process_and_respond()`, which is Discord-specific.

**Plan claim (line 7, 220):** "Zero new safety code, zero duplication of safety hooks" via shared `_process_turn_core()`.

**Status:** The DRY guarantee depends entirely on the Wave P21-003 refactor. Until that refactor lands, any voice implementation would either duplicate safety hooks (DRY violation) or hack around the Discord-specific function (architectural debt).

**Round-2 check:** PASS (conditions) — the plan correctly identifies this as a Wave 3 blocker (line 79: "BLOCKED on P20 pass") and documents the exact pre-condition in A1 (line 462). The forbidden pattern in P21-003 scaffold (line 381: "duplicated safety hooks in voice path (DRY violation)") is explicit.

---

## Hard-Rejection Criterion Assessment

| Criterion | Status | Evidence |
|-----------|--------|----------|
| 1. Plan is sidecar-only without evaluating Hermes core integration | **Not triggered** | Plan explicitly chooses integration via shared turn-core (line 7, 206-221). |
| 2. Always-listening allowed without gating | **Not triggered** | Outside this dimension's scope. |
| 3. Provider claims not backed by official docs | **Not triggered** | Outside this dimension's scope. |
| 4. Secrets/token handling vague | **Not triggered** | Outside this dimension's scope. |
| 5. Transcripts can enter memory without redaction/retention | **Not triggered** | A9 (line 470) closes the provenance gap; memory write passes MEM-001..008 gate (line 24, 388). |
| 6. Safe-word/HARD STOP not first-class in audio path | **Not triggered** | `HardStopHandler.check()` reusable; plan documents pre-sanitization check (line 19, 56). |
| 7. Sub-agent output inline-only without file | **Not triggered** | This audit is written to file. |
| 8. Edits runtime code, deploys, or restarts production | **Not triggered** | Planning-only phase (line 3, 17). |

---

## Additional Observations

1. **Latency budget realism:** The plan acknowledges E2E p50 ~1.5-2.0s with non-streaming `send_message()` (line 182-184, 309). Streaming-Hermes is deferred to Phase-2 optimization (A2, line 463). This is internally consistent.

2. **HARD STOP pre-sanitization:** `HardStopHandler.check()` at `src/core/services/hard_stop_handler.py:89-103` operates on raw text strings (line 89-96: exact triggers + bounded substring + semantic patterns). The plan correctly states it runs on the raw transcript before sanitization (line 19, 56). This is surface-agnostic and reusable for voice.

3. **Life_kernel interaction:** The plan states voice turns do not route through `life_kernel` heartbeat loops; only metadata flows via `VoiceSensorAdapter` (line 229-230). This avoids coupling voice real-time turns to the 30s/60s autonomy cadence. Architecturally sound.

4. **Wave dependency map:** P21-003 (Hermes turn pipeline refactor) is correctly marked `sequential` after P21-001/002 and **BLOCKED on P20 pass** (line 103, 113, 378). The dependency lock is explicit and traceable.

---

## Overall Verdict

**PASS (conditions)**

The round-1 findings (A1, A9) are **CLOSED** in the amended plan. Both are binding P21-003 deliverables with specific file:line targets, testable acceptance criteria, and explicit forbidden patterns. The plan correctly documents:

- **A1 closure:** `_process_turn_core()` refactor with `ProcessedTurn` return type, `source_type` param, unit test proving no Discord import in voice path (line 462).
- **A9 closure:** `store_conversation()` gains `source_type` kwarg, dynamic provenance, voice-episode test (line 470).

The **architectural design** remains sound:
- Voice as text-in/text-out
- Non-streaming `send_message()` reuse (MVP-acceptable)
- Surface-agnostic `shadow_forward()` reuse
- Model-agnostic `CostTracker.record_cost()` supporting `stt:*`/`tts:*` tags
- Text-based `HardStopHandler.check()` reuse

The **implementation hold** (blocked on P20 production-pass) is explicit and pervasive (lines 17-18, 79, 378, 435). The plan is internally consistent: the refactor seam does not exist today (expected for planning phase), and Wave 3 is gated until the P20 kernel soak completes.

**Conditions:**
1. Wave P21-003 must implement the exact refactor specified in A1 (line 462) and A9 (line 470) without regression.
2. Unit tests must prove no safety hook is skipped for `source_type="voice"` (P21-003 scaffold line 383).
3. The P20 production-pass gate must hold until LK-017 soak completes (line 18).

---

## Recommended Before Wave P21-003 Execution

1. **Define `ProcessedTurn`** in `src/voice/types.py` or `src/core/turn_types.py` with fields: `response_text: str`, `metadata: dict[str, Any]`, `safe_mode_activated: bool`, `distress_signal: DistressSignal`, `cost_metadata: dict[str, Any]`.

2. **Extract `_process_turn_core()`** from `_process_and_respond()` body (lines 453-689):
   - Move distress detection (453-486), mood eval (488-493), memory recall (494-553), Hermes invoke (555-578), shadow forward (586-601), cost tracking (603-638), auto-store (644-674), logging (676-689) into the new function.
   - Pass `session_factory`, `shadow_pipeline`, `source_type` as explicit params (not via `getattr(bot, ...)`).
   - Return `ProcessedTurn` with response text + metadata.
   - Discord-text adapter calls `_process_turn_core()` then `channel.send()`.
   - Voice adapter calls `_process_turn_core()` then TTS.

3. **Add `source_type` to `store_conversation()`** at `src/hermes/_memory_bridge.py:216-313`:
   - Line 216: Add param `source_type: str = "discord"` after `safe_mode`.
   - Line 274: Change to `source=f"{source_type}_conversation"`.
   - Line 280: Change to `tags=[source_type, "chat", f"user:{user_id_hash}"]`.

4. **Unit test coverage:**
   - `tests/discord/test_hermes_conversational.py`: Verify existing text tests still pass (no regression).
   - `tests/voice/test_voice_turn_core.py`: Verify `source_type="voice"` invokes without importing `discord.TextChannel`.
   - `tests/hermes/test_memory_bridge.py`: Verify voice episodes carry `source="voice_conversation"` + `["voice","chat",...]`.

---

## File:Line Citation Index

| Claim | Plan Line(s) | Source File:Line(s) |
|-------|--------------|---------------------|
| A1: `_process_turn_core()` refactor with `ProcessedTurn` | 209-218, 462 | `src/discord/hermes_conversational.py:427-691` (current Discord-specific impl) |
| A9: `store_conversation()` source_type provenance | 80, 470 | `src/hermes/_memory_bridge.py:216-313` (lines 274, 280 hardcode discord) |
| `send_message()` non-streaming reuse | 84, 220 | `src/hermes/_session_adapter.py:184-312` (lines 235-240, 252-259) |
| `CostTracker.record_cost()` model-agnostic | 27, 57, 313-314 | `src/core/services/cost_tracker.py:25-53` (line 37 accepts any model tag) |
| `shadow_forward()` surface-agnostic | 56, 220 | `src/discord/shadow_pipeline.py:118-124` |
| `HardStopHandler.check()` text-based reusable | 19, 56 | `src/core/services/hard_stop_handler.py:89-103` |
| P21-003 blocked on P20 pass | 17-18, 79, 378, 435 | AGENTS.md §6 (P20 soak gate) |
| DRY safety hooks forbidden pattern | 381 | P21-003 scaffold |
| Voice cost tags (`stt:*`/`tts:*`) | 27, 57, 313-314 | `src/voice/cost.py` (Wave P21-001, not yet impl) |
| Voice provenance test | 470 | `tests/voice/test_voice_turn_core.py` (Wave P21-003, not yet impl) |

---

## Final Summary

Round-1 findings **A1** (ProcessedTurn + refactor seam) and **A9** (store_conversation source_type) are **CLOSED** in the amended plan via binding P21-003 deliverables. The hermes-integration design is sound: voice reuses the text turn-core, non-streaming `send_message()`, surface-agnostic shadow/cost/HARD-STOP infrastructure, and DRY safety hooks. The implementation hold (blocked on P20 pass) is explicit. No new gaps introduced. Verdict: **PASS (conditions)**.
