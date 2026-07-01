# P21 Voice Interface -- Hermes Core Integration Research

**Role:** Hermes core integration researcher
**Date:** 2026-06-24
**Status:** PASS -- architecture recommendation confirmed

---

## Table of Contents

1.  [Executive Summary](#executive-summary)
2.  [Reuse Point: The `handle_conversation()` Turn Core](#1-reuse-point-the-handle_conversation-turn-core)
3.  [HermesSessionAdapter.send_message() -- Streaming Analysis](#2-hermessessionadaptersend_message---streaming-analysis)
4.  [HermesMemoryBridge -- Verbatim Reuse](#3-hermesmemorybridge---verbatim-reuse)
5.  [Safety Plugin Placement -- Core Safety Argument](#4-safety-plugin-placement)
6.  [Cost Tracking -- Voice Cost Channel](#5-cost-tracking)
7.  [Shadow Pipeline](#6-shadow-pipeline)
8.  [Architectural Recommendation: Thin Adapter over Text Turn-Core](#7-architectural-recommendation)
9.  [Appendix: File:Line Reference Map](#appendix-fileline-reference-map)

---

## Executive Summary

A voice turn is **text-in/text-out at its core**. Every safety, memory, mood, cost, and shadow hook that runs for a Discord text message must also run for a voice turn. The existing pipeline at `src/discord/hermes_conversational.py:358` (`handle_conversation()`) implements all of these in a single orchestrated flow. The recommended architecture is:

- **STT** produces a transcript string (the voice input surface, classified V-022-class per the prompt-injection spec).
- **Feed** that transcript into a **refactored shared "turn core"** -- distress detection, safe-mode, mood, memory recall, system prompt assembly, Hermes invocation, cost tracking, auto-store, and shadow forward -- all from `_process_and_respond()`.
- **TTS** the resulting response text.

This is **option (a): a thin adapter over the existing text turn-core**. Option (b), a new Hermes-native audio path, would duplicate every safety hook and is rejected.

---

## 1. Reuse Point: The `handle_conversation()` Turn Core

### 1.1 Current Architecture

`handle_conversation()` at `hermes_conversational.py:358-419` is the entry point. It runs guard checks (channel, bot, slash, Faiz, rate limit) and then delegates to `_process_and_respond()` at line 427.

The `_process_and_respond()` function (lines 427-691) is the true "turn core". Its stages:

| Step | Lines | Component | File Reference |
|------|-------|-----------|----------------|
| 7 | 453-486 | Distress detection (DistressDetector + SafeModeController) | `persona/safe_mode.py:149-212` |
| 8 | 488-493 | Mood evaluation | `persona/mood_engine.py` |
| 9 | 495-553 | Memory recall + system prompt assembly | `hermes/_memory_bridge.py:93-212` |
| 10 | 556-578 | Hermes AIAgent invocation via `_invoke_hermes_and_send()` | `hermes/_session_adapter.py:189-312` |
| 10b | 586-601 | Shadow forward (fire-and-forget) | `discord/shadow_pipeline.py:118-302` |
| 11 | 603-638 | Cost tracking via CostTracker | `core/services/cost_tracker.py:25-53` |
| 12 | 644-674 | Auto-store conversation to memory | `hermes/_memory_bridge.py:217-313` |
| 13 | 677-689 | Structured logging | - |

### 1.2 Proposed Shared Turn-Core

A voice turn skips steps 1-5 (channel check, bot check, slash check, Faiz check, rate limit -- those are Discord-specific) but runs **all of steps 7-13 identically**.

The minimal shared function signature:

```python
async def _process_turn_core(
    *,
    content: str,                    # STT transcript (for voice) or message.content (for text)
    author_id: str,                  # For cost tracking + hashing
    channel_id: str,                 # For logging
    session_factory: AsyncSessionFactory | None,
    shadow_pipeline: ShadowPipeline | None,
    # Output sinks: the turn core produces a response string but does NOT send it.
    # The caller (text adapter -> channel.send() / voice adapter -> TTS) handles delivery.
) -> ProcessedTurn:
    """Shared turn core used by both text and voice paths.
    
    All safety hooks (Steps 7-13) run here.
    The caller is responsible for delivering the response_text to the appropriate surface.
    """
```

Where `ProcessedTurn` is:

```python
@dataclass
class ProcessedTurn:
    response_text: str
    metadata: dict[str, Any]          # model, tokens, cost
    safe_mode_activated: bool
    distress_level: DistressLevel
    user_id_hash: str
    latency_ms: float
```

The **Discord text adapter** would become:

```python
async def handle_conversation(bot, message) -> bool:
    if not _passes_channel_guard(message):  # Steps 1-5
        return False
    result = await _process_turn_core(
        content=message.content,
        author_id=str(message.author.id),
        channel_id=str(message.channel.id),
        session_factory=bot.get_session_factory(),
        shadow_pipeline=bot.shadow_pipeline,
    )
    for chunk in _split_response(result.response_text):
        await message.channel.send(chunk)
    return True
```

The **voice adapter** would become:

```python
async def handle_voice_turn(transcript: str, user_id: str) -> tuple[str, dict]:
    result = await _process_turn_core(
        content=transcript,
        author_id=user_id,
        channel_id="voice",            # Surface-identifying channel
        session_factory=get_session_factory(),
        shadow_pipeline=get_shadow(),
    )
    return result.response_text, result.metadata  # Caller TTSes this
```

### 1.3 DRY Safety Argument

Every safety check in steps 7-13 runs identically. There is **zero** branching on surface type inside these steps. No safety hook needs to know whether the input came from Discord text or a voice transcript. This is the core DRY safety argument: one code path, one audit trail, one surface for vulnerability discovery.

---

## 2. HermesSessionAdapter.send_message() -- Streaming Analysis

### 2.1 Current Implementation

`HermesSessionAdapter.send_message()` at `_session_adapter.py:184-312` has this signature:

```python
async def send_message(
    self,
    user_id: str,
    content: str | list[dict[str, Any]],
    system_prompt: str,
) -> str:
```

It calls `agent.run_conversation()` via `asyncio.to_thread()` (line 235-239) -- a synchronous blocking call offloaded to a thread:

```python
result: dict[str, Any] = await asyncio.to_thread(
    agent.run_conversation,
    user_message=content,
    system_message=system_prompt,
    conversation_history=history,
)
```

The return is a **complete response string** (`result.get("final_response")`). There is no streaming support whatsoever -- the entire LLM response is produced before `send_message()` returns.

### 2.2 Tradeoff for Voice

| Factor | Full-text-then-TTS | Streaming TTS |
|--------|-------------------|---------------|
| End-to-end latency | LLM latency + TTS latency (serial) | Overlapped: TTS begins as soon as first chunk arrives from LLM |
| Barge-in support | Impossible -- user must wait for full response before speaking | Possible -- user can interrupt mid-response |
| Implementation effort | Zero (current code) | Significant: new streaming interface in adapter, streaming TTS integration |
| Complexity | Low | High (stream state management, cancellation, chunking boundaries) |

### 2.3 Recommendation for P21

**Phase 1 (MVP):** Use the existing non-streaming `send_message()`. Voice latency at MVP will be `STT_time + LLM_time + TTS_time`. With typical 9Router LLM latency of 2-5s and TTS of 1-3s for a paragraph, total is 5-10s. Acceptable for first-turn voice interaction where barge-in is not required.

**Phase 2 (enhancement):** Add a streaming variant `send_message_stream()` that yields response chunks as they arrive. This requires:
- Exposing the underlying `AIAgent.run_conversation()` streaming mode (AIAgent likely supports it via `stream=True`, but the adapter currently hardcodes synchronous mode).
- A `StreamingHermesSessionAdapter` subclass or a new async generator method.
- TTS engine that accepts streaming input (most modern TTS APIs support this).

### 2.4 File:Line References

| File | Line | Detail |
|------|------|--------|
| `_session_adapter.py` | 184-189 | `send_message()` signature: returns `str` |
| `_session_adapter.py` | 235-239 | `asyncio.to_thread(agent.run_conversation, ...)` -- sync blocking call |
| `_session_adapter.py` | 252-259 | `final_response` extracted from result dict |

---

## 3. HermesMemoryBridge -- Verbatim Reuse

### 3.1 READ Path: `recall_for_context()`

```python
async def recall_for_context(
    self,
    query: str,
    *,
    safe_mode: bool = False,
    principal: str = "guinevere_core",
    limit: int = 5,
    token_budget: int = 800,
    kg_enabled: bool = True,
) -> list[dict[str, object]]:
```

File: `hermes/_memory_bridge.py:93-212`

This interface is **text-in**. `query` is a natural-language string. A voice transcript is a natural-language string. They are identical. No change needed.

### 3.2 WRITE Path: `store_conversation()`

```python
async def store_conversation(
    self,
    user_message: str,
    assistant_response: str,
    user_id_hash: str,
    *,
    safe_mode: bool = False,
) -> str | None:
```

File: `hermes/_memory_bridge.py:217-313`

The content format is `"Faiz: {user_message}\nGuinevere: {assistant_response}"`. The `source` is hardcoded as `"discord_conversation"` (line 272) and `tags` include `["discord", "chat", ...]` (line 280).

### 3.3 Transcript-Specific Needs

Two small changes recommended for provenance:

1. **Add `source_type='voice'` parameter** to `store_conversation()` so the memory record carries an audio provenance tag. This enables downstream analysis of voice-vs-text interaction patterns.

   Proposed change at `_memory_bridge.py:272`:
   ```python
   source = "voice_conversation" if source_type == "voice" else "discord_conversation"
   tags = ["voice", "chat", ...] if source_type == "voice" else ["discord", "chat", ...]
   ```

2. **The `store_conversation()` call site** in the shared turn-core would accept a `source_type` parameter (default `"discord"`, override `"voice"` when called from voice path).

### 3.4 File:Line References

| File | Line | Detail |
|------|------|--------|
| `_memory_bridge.py` | 93-99 | `recall_for_context()` signature |
| `_memory_bridge.py` | 146-155 | `recall_memories()` invocation -- query is a plain string |
| `_memory_bridge.py` | 217-224 | `store_conversation()` signature |
| `_memory_bridge.py` | 272-281 | Hardcoded `source="discord_conversation"` and tags |

---

## 4. Safety Plugin Placement

### 4.1 Dual Safety Layers

The safety system has **two layers**, both operating on text:

**Layer 1: Conversation handler (hermes_conversational.py)**
- `DistressDetector.detect(content)` at file:line `persona/safe_mode.py:157`
- `SafeModeController.evaluate(signal)` at file:line `persona/safe_mode.py:247`
- These run in `_process_and_respond()` at `hermes_conversational.py:453-486` -- **BEFORE** Hermes is called.

**Layer 2: Hermes plugin hooks (safety_plugin.py)**
- `pre_llm_call` hook: Gates G01 (HARD STOP), G02 (Distress), G04 (Recovery), G07 (Yandere)
- `post_llm_call` hook: Gate G03 (Drift detection)
- `transform_llm_output` hook: Gates G05 (Forbidden), G06 (Secrets), G08 (Yandere semantic)
- `pre_tool_call` hook: Gates G09 (Auth matrix), G10 (Consent)
- Registered at `safety_plugin.py:1210-1249`

These plugins operate on the **string text** of the incoming user message and outgoing assistant response. They do not care about the transport surface.

### 4.2 The Core Safety Argument

A voice transcript is text. The transcript string passes through:

1. `_process_and_respond()` -> `DistressDetector.detect(transcript)` -> `SafeModeController.evaluate()`
2. `_invoke_hermes_and_send()` -> `adapter.send_message(transcript)` -> Hermes plugin hooks
3. `GuinevereSafetyPlugin.pre_llm_call()` -> G01/G02/G04/G07 on the transcript

All safety gates apply identically. **No new safety surface is created by adding voice.** The STT engine is the new attack surface (an attacker could craft audio that STT transcribes as a safe-word bypass attempt), but that is an STT robustness concern, not a pipeline safety concern.

### 4.3 Prompt Injection for Voice Transcripts

Per `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md`, voice transcripts are `V-022-class` -- "untrusted text that must be sanitized / labelled / quarantined before reaching privileged layers L0-L6." The existing safe-word classifier runs BEFORE sanitization on RAW input (the transcript string). The injection-sanitization layer would wrap the transcript in:

```
<untrusted source="voice:stt:whisper-1">
{transcript}
</untrusted>
```

before passing it to the turn core. The turn core itself does not need to change -- the XML delimiters are consumed by the sanitization layer at L7-L9.

### 4.4 File:Line References

| File | Line | Detail |
|------|------|--------|
| `hermes_conversational.py` | 453-486 | Distress + safe-mode detection on `content` (first safety layer) |
| `safety_plugin.py` | 543-791 | `pre_llm_call()` -- G01/G02/G04/G07 on raw text |
| `safety_plugin.py` | 1009-1134 | `transform_llm_output()` -- G05/G06/G08 on response text |
| `safety_plugin.py` | 1210-1249 | Hook registration in `register()` |
| `hard_stop_handler.py` | 89-103 | `check(message: str) -> bool` -- operates on text |

---

## 5. Cost Tracking

### 5.1 Existing CostTracker

File: `core/services/cost_tracker.py:10-78`

```python
def record_cost(self, model: str, input_tokens: int, output_tokens: int,
                cost_per_1k_input: float, cost_per_1k_output: float):
```

Redis keys created:
- `cost:current_month` (float)
- `cost:current_day` (float)
- `cost:by_model:{model}` (float)
- `cost:daily:{today}` (float)
- `cost:monthly:{month}` (float)
- `token:*` counters

The USD 30/mo cap is checked via `check_budget()` (line 55-66).

### 5.2 Voice Adds STT + TTS Cost

A voice turn involves these cost components:

| Component | Model Tag (proposed) | Typical Provider | Rough Cost |
|-----------|---------------------|-----------------|------------|
| STT | `stt:whisper-1` | OpenAI Whisper | $0.006/min |
| LLM (Hermes) | `kiro-free` (9Router) | GPT-5.5 core | Existing tracking |
| TTS | `tts:openai-tts-1` | OpenAI TTS | $0.015/1K chars |
| TTS (alt) | `tts:elevenlabs` | ElevenLabs | $0.0003/char |

### 5.3 Proposed Voice Cost Channel

The existing `record_cost()` models are LLM-only and use `model` as the LLM model name. Voice costs should be tracked **as separate model tags** feeding into the same Redis keys:

```python
# In voice adapter, after STT:
cost_tracker.record_cost(
    model="stt:whisper-1",
    input_tokens=0,
    output_tokens=audio_duration_seconds * 100,  # ~100 tokens/sec equivalent
    cost_per_1k_input=0.0,
    cost_per_1k_output=0.006 / (audio_duration_seconds * 100) * 1000,
)

# After TTS:
cost_tracker.record_cost(
    model="tts:openai-tts-1",
    input_tokens=0,
    output_tokens=len(tts_chars),
    cost_per_1k_input=0.0,
    cost_per_1k_output=0.015,  # $0.015 per 1K chars
)
```

This reuses the existing `cost:by_model:*` Redis keys so the USD 30/mo cap automatically includes STT/TTS spend. No new tracking infrastructure needed.

### 5.4 Usage Threshold for Voice

A typical voice turn:
- 10s audio -> STT: ~$0.001
- LLM: $0.002-0.005 (varies by 9Router model)
- TTS 200 chars response: ~$0.003

Total per voice turn: ~$0.006-0.009. At USD 30/mo cap, this allows ~3,300-5,000 voice turns per month alongside text usage.

### 5.5 File:Line References

| File | Line | Detail |
|------|------|--------|
| `cost_tracker.py` | 25-53 | `record_cost()` -- accepts any model string |
| `cost_tracker.py` | 37 | `pipe.incrbyfloat(f"cost:by_model:{model}", cost)` -- generic model key |
| `cost_tracker.py` | 55-66 | `check_budget()` -- reads `cost:current_month` |
| `hermes_conversational.py` | 603-638 | Cost tracking call site in existing turn core |

---

## 6. Shadow Pipeline

### 6.1 Current Shadow Pipeline

File: `discord/shadow_pipeline.py`

`ShadowPipeline.shadow_forward()` at line 118-302 is a **fire-and-forget** async task invoked via `asyncio.create_task()` at `hermes_conversational.py:591-595`. It invokes a Hermes subprocess (`hermes --no-stream ...`), captures the response, logs comparison metrics, and **never** sends anything to Discord.

### 6.2 Voice Turns Should Shadow-Forward Too

The shadow pipeline is a **safety comparison tool** -- it detects divergence between the production response and a "correct" Hermes response. Voice turns benefit from shadow forwarding for the same reason text turns do: detecting safety-marker mismatches.

However, there are two considerations:

1. **The shadow pipeline currently invokes a `hermes` subprocess** (line 78-79: `["hermes", "--no-stream", ...]`). This is independent of the HermesSessionAdapter path used by the main pipeline. Voice turns would shadow-forward to the *same subprocess* -- no changes needed.

2. **STT/TTS costs are NOT shadowed.** The shadow pipeline only compares the LLM response text. STT and TTS happen before/after the shadow pipeline's scope.

3. **Proposed change:** The shared turn core's shadow-forward step at `_process_turn_core()` should be identical for both surfaces. Pass the same `content` (transcript) and `response_text` to `shadow.shadow_forward()`.

### 6.3 File:Line References

| File | Line | Detail |
|------|------|--------|
| `shadow_pipeline.py` | 118-124 | `shadow_forward()` signature |
| `hermes_conversational.py` | 588-601 | Fire-and-forget shadow invocation |
| `hermes_conversational.py` | 589 | `shadow = getattr(bot, "shadow_pipeline", None)` -- needs refactoring to accept injected shadow |

---

## 7. Architectural Recommendation

### 7.1 Option (a) vs Option (b)

| Criterion | (a) Thin adapter over text turn-core | (b) New Hermes-native audio path |
|-----------|--------------------------------------|----------------------------------|
| Safety hook duplication | Zero -- shared via refactored `_process_turn_core()` | Complete duplication needed -- every safety gate must be re-implemented |
| Maintenance burden | Low -- one turn core to maintain | High -- two parallel implementations drift over time |
| Audit surface | Single code path, single audit trail | Two code paths, must audit both |
| STT error handling | Injected into shared pipeline as a pre-stage | Must implement independently |
| Barge-in complexity | Same for both (requires streaming adapter changes) | Same for both |
| Time to MVP | Low -- extract `_process_and_respond()` body into shared function | High -- build entire new pipeline from scratch |
| Consistency guarantee | Text and voice produce identical behaviour per safety hook | Behavioural divergence is inevitable |

**Decision: Option (a) with refactoring seam.**

### 7.2 The Refactoring Seam

The refactoring from the current architecture to the shared turn core is straightforward:

1. Extract the body of `_process_and_respond()` (`hermes_conversational.py:427-691`) into `_process_turn_core()`.
2. Remove the `author`, `channel` parameters (Discord-specific). Replace with `author_id: str`, `channel_id: str` (abstract).
3. Replace `await channel.send(FALLBACK_MESSAGE)` with return of an error-typed `ProcessedTurn`.
4. Add optional `source_type: str = "discord"` parameter for memory provenance.
5. The Discord adapter calls `_process_turn_core()` then `channel.send()` on the result.
6. The voice adapter calls `_process_turn_core()` then TTS on the result.

### 7.3 Integration (Not Sidecar)

Per the P21 hard-rejection rule: a sidecar voice service would have its own text processing, its own safety hooks, its own memory bridge -- it would diverge within a week. Integration-by-refactoring ensures:

- One DistressDetector instance, one call path.
- One set of forbidden patterns, one transform pipeline.
- One memory store with consistent provenance tags.
- One cost tracker, one budget cap.
- One shadow pipeline.

### 7.4 Integration with life_kernel

The `life_kernel` (src/life_kernel/hermes_brain.py) uses `HermesBrain` which wraps `AIAgent` independently. Voice turns do NOT interact with life_kernel directly -- they are user-initiated turns, not autonomous reasoning. life_kernel heartbeat loops (`heartbeat.py`) continue to run independently. No changes to life_kernel needed for voice.

---

## Appendix: File:Line Reference Map

| File | Lines | Component | Integration Point |
|------|-------|-----------|-------------------|
| `discord/hermes_conversational.py` | 358-419 | `handle_conversation()` | Discord adapter -> shared turn core |
| `discord/hermes_conversational.py` | 427-691 | `_process_and_respond()` | **Seam -- extract into shared `_process_turn_core()`** |
| `discord/hermes_conversational.py` | 453-486 | Distress detection | Runs on transcript text, unchanged |
| `discord/hermes_conversational.py` | 495-553 | Memory recall + system prompt | Runs on transcript as `query`, unchanged |
| `discord/hermes_conversational.py` | 556-578 | Hermes invocation | `_invoke_hermes_and_send()` unchanged |
| `discord/hermes_conversational.py` | 586-601 | Shadow forward | Unchanged, shared |
| `discord/hermes_conversational.py` | 603-638 | Cost tracking | STT/TTS tagged as `stt:*` and `tts:*` models |
| `discord/hermes_conversational.py` | 644-674 | Auto-store memory | Add `source_type="voice"` parameter |
| `hermes/adapter.py` | 32-54 | `get_adapter()` singleton | Shared by both surfaces |
| `hermes/_session_adapter.py` | 184-312 | `send_message()` | Non-streaming; Phase 2 add streaming variant |
| `hermes/_session_adapter.py` | 235-239 | `asyncio.to_thread(agent.run_conversation)` | Synchronous blocking call |
| `hermes/_memory_bridge.py` | 93-212 | `recall_for_context()` | Verbatim reuse -- text-in/text-out |
| `hermes/_memory_bridge.py` | 217-313 | `store_conversation()` | Add `source_type` param for provenance |
| `hermes/_memory_bridge.py` | 272 | Hardcoded `source="discord_conversation"` | Change to dynamic based on source_type |
| `hermes/safety_plugin.py` | 543-791 | `pre_llm_call()` | G01/G02/G04/G07 -- text, unchanged |
| `hermes/safety_plugin.py` | 1009-1134 | `transform_llm_output()` | G05/G06/G08 -- text, unchanged |
| `hermes/safety_plugin.py` | 1210-1249 | Plugin registration | Unchanged |
| `hermes/plugins/persona_plugin.py` | 536-611 | `pre_llm_call()` | Persona state injection -- text, unchanged |
| `discord/shadow_pipeline.py` | 118-302 | `shadow_forward()` | Unchanged fire-and-forget |
| `core/services/cost_tracker.py` | 25-53 | `record_cost()` | Accepts `stt:*` / `tts:*` model tags |
| `core/services/cost_tracker.py` | 55-66 | `check_budget()` | USD 30/mo cap includes STT/TTS |
| `core/services/hard_stop_handler.py` | 89-103 | `check(message)` | Text input, unchanged |
| `persona/safe_mode.py` | 157-212 | `DistressDetector.detect()` | Text input, unchanged |
| `persona/safe_mode.py` | 247-281 | `SafeModeController.evaluate()` | Text input, unchanged |
