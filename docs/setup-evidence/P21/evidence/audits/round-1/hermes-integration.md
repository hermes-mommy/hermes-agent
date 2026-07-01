# P21 Voice Interface — Round 1 Audit: Hermes Integration

**Auditor:** Independent Hermes-integration auditor  
**Date:** 2026-06-24  
**Scope:** Verify that the proposed voice turn reuses the Hermes text turn-core without duplication, that all Steps 7–13 are preserved, and that the planned refactor seam is sound and consistent with the repository source-of-truth.  

---

## Audit Method

1. Read the P21 enterprise plan (`docs/setup-evidence/P21/plan/p21-voice-interface-enterprise-plan.md`).
2. Read the Hermes core integration research (`docs/setup-evidence/P21/research/p21-hermes-core-integration-research.md`).
3. Verify claims against the current repository source-of-truth:
   - `src/discord/hermes_conversational.py`
   - `src/hermes/_session_adapter.py`
   - `src/hermes/_memory_bridge.py`
   - `src/hermes/adapter.py`
   - `src/core/services/cost_tracker.py`
   - `src/discord/shadow_pipeline.py`
   - `src/core/services/hard_stop_handler.py`
4. Compare the proposed architecture with what exists today, not what is promised for a later wave.

---

## Findings

### 1. Refactor seam at `hermes_conversational.py:427-691` — DOES NOT EXIST YET

The current `_process_and_respond()` at `src/discord/hermes_conversational.py:427-691` is Discord-specific. It accepts `bot`, `author`, and `channel` objects, calls `await channel.send(FALLBACK_MESSAGE)` directly on lines 552, 572, and 577, and derives session access via `getattr(bot, "get_session_factory", None)` (line 498) and the shadow pipeline via `getattr(bot, "shadow_pipeline", None)` (line 589).

| Step | Current lines | Surface-agnostic? | Notes |
|------|---------------|---------------------|-------|
| 7 Distress | 453–486 | No | Uses raw `content` string, so could be reused, but the step is embedded inside a Discord-specific function. |
| 8 Mood | 488–493 | No | Embedded. |
| 9 Memory recall | 494–553 | No | Embedded; depends on `bot.get_session_factory()`. |
| 10 Hermes invoke | 555–579 | No | Calls `_invoke_hermes_and_send(author, channel, …)`. |
| 10b Shadow forward | 586–601 | No | Embedded; depends on `bot.shadow_pipeline`. |
| 11 Cost tracking | 603–638 | No | Embedded. |
| 12 Auto-store | 644–674 | No | Calls `bridge.store_conversation(user_message=content, …)` without provenance. |
| 13 Structured logging | 676–689 | No | Embedded. |

**Verdict for this check:** The refactor seam is **not implemented**. The proposed `_process_turn_core()` function is design-only. Because the extraction has not happened, Steps 7–13 are preserved for text **today**, but they are **not yet preserved for voice** in any code path.

### 2. `_process_turn_core` signature — NOT PRESENT IN SOURCE

The plan and the research both specify a shared function, but with a subtle mismatch:

- **Plan** (`p21-voice-interface-enterprise-plan.md:209-218`) proposes:
  ```python
  async def _process_turn_core(
      *, content: str, author_id: str, channel_id: str,
      session_factory: AsyncSessionFactory | None,
      shadow_pipeline: ShadowPipeline | None,
      source_type: str = "discord",
  ) -> ProcessedTurn:
  ```

- **Research** (`p21-hermes-core-integration-research.md:60-76`) proposes the same signature but **omits `source_type`** from the formal signature, only mentioning it later as a needed change for memory provenance.

Neither signature exists in `src/discord/hermes_conversational.py`. A global grep for `ProcessedTurn` in `src/` returned no matches.

**Verdict:** Signature is **unimplemented and internally inconsistent** between plan and research.

### 3. `store_conversation()` source_type provenance — NOT PRESENT IN SOURCE

Current `HermesMemoryBridge.store_conversation()` at `src/hermes/_memory_bridge.py:216-313` has:

- Signature (lines 216–223) lacks `source_type`.
- Line 274 hardcodes `source="discord_conversation"`.
- Line 280 hardcodes `tags=["discord", "chat", f"user:{user_id_hash}"]`.

The research document (lines 225–236) proposes adding `source_type` so that voice turns can write `source="voice_conversation"` and tags `["voice", "chat", …]`. This change is **not in the codebase**.

**Verdict:** Provenance parameter **missing**. Memory writes from any future voice path would incorrectly be tagged as `discord_conversation` unless the call site overrides the source string manually.

### 4. `HermesSessionAdapter.send_message()` reuse — PASSES

`src/hermes/_session_adapter.py:184-312` defines:

- `async def send_message(self, user_id: str, content: str | list[dict[str, Any]], system_prompt: str) -> str` (lines 184–189).
- The LLM call is synchronous, offloaded via `asyncio.to_thread()` at lines 235–240.
- The return is a full string `final_response` at lines 252–259.

This is **non-streaming**, surface-agnostic (text-in/text-out), and can be reused by both text and voice without modification. The research recommendation (Section 2.3) to use the existing non-streaming `send_message()` for the voice MVP is correct and consistent with the source.

**Verdict:** PASS.

### 5. STT/TTS cost tags feeding `CostTracker.record_cost` — DESIGN SUPPORTED, CODE NOT YET PRESENT

`src/core/services/cost_tracker.py:25-53` defines:

- `def record_cost(self, model: str, input_tokens: int, output_tokens: int, cost_per_1k_input: float, cost_per_1k_output: float)` (lines 25–26).
- Line 37 increments `cost:by_model:{model}` for any arbitrary model string.

The infrastructure accepts `stt:*`, `tts:*`, and `realtime:*` tags. No voice code currently calls `record_cost()` with those tags, but the design document (`p21-voice-interface-enterprise-plan.md:313-314`) and the research (Section 5.3) explicitly define the intended usage.

**Verdict:** Design is sound and the tracker is model-agnostic; actual wiring does not yet exist.

### 6. Shadow pipeline reuse for voice — PASSES (interface is surface-agnostic)

`src/discord/shadow_pipeline.py:118-124` exposes:

```python
async def shadow_forward(
    self,
    message_content: str,
    bot_response: str,
    user_id: str,
    channel_id: str,
) -> dict[str, Any]:
```

All parameters are strings. A voice turn can pass `message_content=transcript`, `bot_response=response_text`, `user_id=author_id`, and `channel_id="voice"`.

**Verdict:** PASS — the shadow pipeline can be reused without change.

### 7. DRY / safety-hook duplication risk — CRITICAL GAP

The research document’s central safety argument (Section 4.2) states: “No new safety surface is created by adding voice.” This argument depends entirely on the shared `_process_turn_core()` refactor. Because that refactor does **not** exist, any voice implementation executed today would either:

- Duplicate the safety hooks in a separate voice path (DRY violation), or
- Call the existing Discord-specific `_process_and_respond()` with a fake `author`/`channel` (architectural hack).

Neither is acceptable. The plan correctly identifies this as a Wave 3 task blocked on P20 pass, but the audit must report the current state honestly: the safety-preserving seam is **not yet real**.

### 8. Additional consistency observations

- **Latency budget realism:** The plan estimates E2E p50 ~1.5–2.0 s for a voice turn, with the LLM as the bottleneck. Because `send_message()` is non-streaming and returns a full response before TTS can start, serial latency is STT + LLM + TTS. The plan acknowledges this and defers streaming to a Phase-2 enhancement. This is internally consistent.
- **HARD STOP pre-sanitization:** The plan states that `HardStopHandler.check(transcript)` runs on the raw transcript before sanitization. The existing `HardStopHandler.check()` at `src/core/services/hard_stop_handler.py:89-103` operates on a text string and is surface-agnostic, so it can be reused for voice. This part of the design is sound.
- **Life_kernel interaction:** The plan states that voice turns do not route through `life_kernel` heartbeat loops; only metadata flows via `VoiceSensorAdapter`. This avoids coupling voice real-time turns to the 30 s/60 s autonomy cadence and is architecturally sound.

---

## Cited File:Line References

| Finding | File | Lines |
|---------|------|-------|
| `_process_and_respond()` Discord-specific, no shared seam | `src/discord/hermes_conversational.py` | 427–691 |
| `_process_and_respond()` calls `channel.send()` directly | `src/discord/hermes_conversational.py` | 552, 572, 577 |
| `_process_and_respond()` fetches session factory from `bot` | `src/discord/hermes_conversational.py` | 498–499 |
| `_process_and_respond()` fetches shadow from `bot` | `src/discord/hermes_conversational.py` | 588–589 |
| `ProcessedTurn` does not exist in `src/` | grep result | (none) |
| `store_conversation()` hardcodes `discord_conversation` | `src/hermes/_memory_bridge.py` | 273–274, 279–280 |
| `store_conversation()` signature lacks `source_type` | `src/hermes/_memory_bridge.py` | 216–223 |
| `send_message()` is non-streaming | `src/hermes/_session_adapter.py` | 184–312, esp. 235–240, 252–259 |
| `record_cost()` accepts arbitrary model tag | `src/core/services/cost_tracker.py` | 25–53, esp. 37 |
| `shadow_forward()` is surface-agnostic | `src/discord/shadow_pipeline.py` | 118–124 |
| `HardStopHandler.check()` is text-based and reusable | `src/core/services/hard_stop_handler.py` | 89–103 |

---

## Per-Hard-Rejection-Criterion Assessment

| Hard-rejection criterion (P21 planning) | Status | Rationale |
|------------------------------------------|--------|-----------|
| 1. Plan is sidecar-only without evaluating Hermes core integration | **Not triggered** | Plan explicitly chooses integration via shared turn-core. |
| 2. Always-listening allowed without gating | **Not triggered** | Plan defers always-listening to P21-006 with 8-gate checklist. |
| 3. Provider claims not backed by official docs | **Not triggered** | Provider research is separate file; not within this dimension’s scope. |
| 4. Secrets/token handling vague | **Not triggered** | Secrets model names SOPS path and rotation; outside this dimension. |
| 5. Transcripts can enter memory without redaction/retention | **RISK** | `store_conversation()` currently hardcodes `discord` provenance and has no `source_type`; until the provenance change lands, voice transcripts would be mis-tagged. |
| 6. Safe-word/HARD STOP not first-class in audio path | **Not triggered** | Design is sound; `HardStopHandler.check()` is text-based and reusable. |
| 7. Sub-agent output inline-only without file | **Not triggered** | This audit is written to file. |
| 8. Edits runtime code, deploys, or restarts production | **Not triggered** | No runtime changes made by this audit. |

---

## Overall Verdict

**NEEDS REVIEW**

The **architectural design** is sound: voice as text-in/text-out, reusing the non-streaming `HermesSessionAdapter.send_message()`, surface-agnostic `ShadowPipeline.shadow_forward()`, and a proposed shared `_process_turn_core()` that would preserve Steps 7–13 for both text and voice. The `CostTracker` already supports arbitrary model tags (`stt:*`, `tts:*`).

However, the **actual refactor seam does not exist in source**. `_process_and_respond()` is still Discord-specific, `ProcessedTurn` is undefined, and `HermesMemoryBridge.store_conversation()` has no `source_type` parameter. Until Wave P21-003 lands, the safety-preserving DRY claim is a design assertion, not an implemented guarantee. The plan acknowledges this by blocking Wave 3 on the P20 production pass, so the gap is documented and gated rather than hidden.

---

## Required Before P21 Voice Turn-Core Implementation

1. Extract `_process_and_respond()` body into a surface-agnostic `_process_turn_core()` with the agreed signature, including `source_type`. Ensure error paths return a typed result object rather than calling `channel.send()` internally.
2. Add `source_type: str = "discord"` to `HermesMemoryBridge.store_conversation()` and switch the hardcoded `source`/`tags` to dynamic values.
3. Define `ProcessedTurn` (or equivalent) in a location accessible to both `src/discord/` and `src/voice/`.
4. Add unit tests that exercise `_process_turn_core()` with both `source_type="discord"` and `source_type="voice"` to prove no safety hook is skipped for voice.
