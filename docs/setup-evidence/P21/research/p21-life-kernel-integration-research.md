# P21 Voice Interface — Life Kernel Integration Research

**Role**: life_kernel integration researcher  
**Date**: 2026-06-24  
**Status**: COMPLETE  

---

## Table of Contents

1. [HARD STOP Flag: Single Source of Truth for Kernel HALT](#1-hard-stop-flag-single-source-of-truth-for-kernel-halt)
2. [Voice as a Sensor: Sensor Adapter Interface](#2-voice-as-a-sensor-sensor-adapter-interface)
3. [Voice Turn as Cognition Input: Observe-Decide-Act-Reflect](#3-voice-turn-as-cognition-input-observe-decide-act-reflect)
4. [Dashboard and Log Channel Voice State](#4-dashboard-and-log-channel-voice-state)
5. [HermesBrain.think() — Proactive Voice Output Seam](#5-hermesbrainthink--proactive-voice-output-seam)
6. [Always-Listening vs. Autonomy Exception](#6-always-listening-vs-autonomy-exception)
7. [Cross-Specialist Intersections](#7-cross-specialist-intersections)
8. [Design Recommendations](#8-design-recommendations)

---

## 1. HARD STOP Flag: Single Source of Truth for Kernel HALT

### Exact mechanism

The heartbeat's `_heartbeat_1s()` method (heartbeat.py:254-357) is the kernel's liveness safety check, executing every **1 second**. The critical Redis key access is at **line 273**:

```python
hard_stop_key = "life_kernel:hard_stop"
try:
    hard_stop_value = await self.redis_client.get(hard_stop_key)
```

When `live_hard_stop = bool(hard_stop_value)` is `True`:
- The Redis value is read at heartbeat.py:275
- The graph's `hard_stop_requested` field is set to `True` via `graph.ainvoke()` (line 299)
- A HARD STOP dashboard update is force-published via `self._discord_publisher.publish_hard_stop(state)` (line 316)
- A lifecycle log `[HARD_STOP] Kernel halted by operator` is written (line 318)
- `await self.stop()` is called (line 322), cancelling all heartbeat loops

The heartbeat also handles **recovery**: if the Redis flag is absent but the graph checkpoint has a stale `hard_stop_requested=True`, it clears the checkpoint state (lines 328-351) — this fixed the P20 stuck-HARD-STOP bug.

### What voice always-listening MUST do

1. **Check `life_kernel:hard_stop` in Redis BEFORE each capture attempt.** If set to any truthy value, the always-listening loop must NOT capture audio. This is a pre-capture gate, not a mid-capture interrupt.

2. **Check the flag BETWEEN capture chunks** (if streaming/buffered). Between STT transcription chunks, re-check the Redis key. If set, discard the pending capture and enter safe mode.

3. **SET `life_kernel:hard_stop` when a spoken safe word is detected in STT output.** The voice pipeline transcribes audio → runs `HardStopHandler.check(transcript)` → if True, the callback (or pipeline logic) does:
   ```python
   await redis_client.set("life_kernel:hard_stop", "voice_safe_word")
   ```
   This single Redis SET triggers the entire kernel halt through the existing 1s heartbeat, without any voice-specific stop logic needed in the kernel.

4. **SET `life_kernel:hard_stop` on RECOVERY_TRIGGERS match.** The `HardStopHandler.check_recovery()` at hard_stop_handler.py:105 detects resume phrases ("resume", "aku sudah okay", etc.). When recovery is detected via voice transcript, the pipeline must DELETE the Redis key:
   ```python
   await redis_client.delete("life_kernel:hard_stop")
   ```
   The next 1s heartbeat detects the absent flag and clears the graph's stale `hard_stop_requested`.

### Summary Table

| Action | Redis Operation | Code Location |
|--------|----------------|---------------|
| Pre-capture gate check | `GET life_kernel:hard_stop` | heartbeat.py:275 |
| Spoken safe word sets HALT | `SET life_kernel:hard_stop "voice"` | Must be added in voice pipeline |
| Spoken recovery clears HALT | `DELETE life_kernel:hard_stop` | Must be added in voice pipeline |
| Kernel reacts (heartbeat) | `GET life_kernel:hard_stop` already runs at heartbeat.py:275 every 1s | heartbeat.py:273-323 |

**The voice pipeline does NOT need its own `_heartbeat_1s()` equivalent.** It reads and writes the same Redis key that the kernel already polls.

---

## 2. Voice as a Sensor: Sensor Adapter Interface

### Existing adapter contract

`BaseSensorAdapter` at `src/life_kernel/sensor_adapters/base.py` defines:

```python
SENSOR_NAME: str
OBSERVATION_TYPE: str
DEFAULT_CONTENT: str

async def sense() -> list[dict[str, Any]]
    # Returns [{
    #   "source": f"sensor:{self.name}",
    #   "type": self.OBSERVATION_TYPE,
    #   "content": self.DEFAULT_CONTENT,
    #   "timestamp": datetime.now().isoformat(),
    #   "additional": {},
    # }]

async def health() -> bool
```

### Existing adapters (all placeholders)

Listed in `sensor_adapters/__init__.py` (line 15-25):
- `DiscordSensorAdapter` — polls messages, mentions
- `GmailSensorAdapter`
- `FinanceSensorAdapter`
- `WearableSensorAdapter`
- `SurveillanceSensorAdapter` — consent-gated
- `VPSSensorAdapter`
- `RepoSensorAdapter`
- `BrowserSensorAdapter`

### Proposed `VoiceSensorAdapter`

A new adapter subclass should:

- **SENSOR_NAME** = `"voice"`
- **OBSERVATION_TYPE** = `"utterance"` or `"voice_activity"`
- **sense()** feed voice-derived signals into the awareness loop every 30s (the existing _heartbeat_30s interval, heartbeat.py:400-419). The voice states to surface:
  - `listening_state`: "idle" | "listening" | "processing" | "speaking" — current voice hardware state
  - `last_utterance_timestamp`: ISO timestamp of most recent STT result
  - `utterance_count`: monotonic counter for dashboard
  - `transcript_summary` or `transcript_snippet`: last N chars of most recent transcript (sanitized — NEVER raw audio)
  - `voice_activity_detected`: bool for awareness

- **health()** returns whether the microphone device is available and the always-listening loop is running

### Registration and wiring

```python
# In the kernel startup (where other adapters are registered):
sensor_registry = SensorRegistry()
voice_adapter = VoiceSensorAdapter(config={})
await sensor_registry.register("voice", voice_adapter)
```

The registry's `sense_all()` (sensors.py:108) calls every registered adapter. The `BackgroundCognition.observer()` loop (cognition.py:296-326) polls `sense_all()` every 10s and writes observations to the graph via `_write_to_graph()`.

**Limitation**: The sense/observer loop runs every 10s (cognition.py:73: `"observer": 10.0`). Voice utterances happen at unpredictable intervals (millisecond granularity for voice activity detection). The adapter can buffer recent utterances and batch them into the next `sense()` call, but for conversational turn handling (STT→response→TTS), the dedicated Hermes conversational pipeline must be used, NOT the sensor poll loop.

### Two-tier design

| Tier | Component | Purpose | Cadence |
|------|-----------|---------|---------|
| **Reactive** | Voice STT → HardStopHandler → Hermes pipeline → TTS | Real-time conversational turns | Per utterance |
| **Reflective** | VoiceSensorAdapter.sense() → observer loop → graph state | Awareness, dashboard, long-term context | Every 10-30s |

The reactive tier handles voice safety and conversation. The reflective tier feeds voice-derived signals into the kernel's world model so the kernel is aware of voice state.

---

## 3. Voice Turn as Cognition Input: Observe-Decide-Act-Reflect

### The existing graph cycle

The life-mind graph at `graph.py:850-995` has:

```
START → observe → decide → (act/idle/reflect) → END
                ↑                              |
                └──────────────────────────────┘
                (cycle repeats per heartbeat)
```

- **observe_node** (graph.py:133-272): reads P16 KG + P18 memory adapters, populates `recalled_concepts`/`recalled_memories`. Currently gets NO sensor observations — the observer loop writes them but the graph doesn't actively read them from `observations` list to influence the decision context.
- **decide_node** (graph.py:275-353): static priority engine, HARD STOP check, routes to act/idle/reflect
- **act_node** (graph.py:356-444): picks highest-priority goal
- **reflect_node** (graph.py:447-569): audit, journal write
- **idle_node** (graph.py:572-692): self-directed task generation

### Where a voice transcript injects

A voice transcript is NOT a synchronous graph injection in the current architecture. The existing conversational path for Discord messages goes through `hermes_conversational.py` (the full `handle_conversation()` pipeline), which calls `HermesBrain.think()` via `HermesSessionAdapter.send_message()` — completely bypassing the life-mind graph.

**For voice, the same pattern applies**: the voice turn is a real-time interaction that should NOT wait for a 60s heartbeat cycle to traverse OBSERVE→DECIDE→ACT. It needs the same dedicated pipeline:

```
STT transcript → HardStopHandler.check() → Hermes conversaton pipeline → TTS
```

The voice transcript enters the **graph indirectly** through:
1. The `VoiceSensorAdapter.sense()` surfaces "had conversation at timestamp" metadata into the observer loop
2. `BackgroundCognition.memory()` (cognition.py:328-339) every 5m could scan recent voice interactions for long-term memory patterns
3. The Hermes pipeline's auto-store memory (P18 memory bridge) saves conversation history to the episodic memory store, which the graph's `observe_node` recalls in future cycles

### The injection point in observe_node

When the graph runs `observe_node` on its 60s heartbeat, the node queries P18 memory. Voice conversations stored in P18 will appear in `recalled_memories` (graph.py:202-208). This is the natural injection point: voice transcripts persist to memory → `observe_node` recalls them → the decision context includes voice-derived signals.

### What must be added

A field `voice_state` or `last_voice_utterance` in `LifeMindState` (state.py) that:
- Is written by the voice pipeline on each utterance (best-effort, non-blocking)
- Is read by `observe_node` for awareness display
- Gets rendered on the dashboard

The existing `observations` list (state.py:109-114, reducer cap at 100) can also receive voice observation entries from the BackgroundCognition observer loop.

---

## 4. Dashboard and Log Channel Voice State

### Dashboard interface

`DashboardWriter.update_dashboard(state)` at `dashboard_writer.py:126` renders the `LifeMindState` as a Discord embed. It calls `self._renderer.render_embed(state)` (dashboard.py:285-386) which produces a 12-field embed.

**Currently displayed fields:**
- Status (HARD STOPPED/ALIVE/INACTIVE)
- Mode (current_phase)
- Current Focus
- Last Decision
- Last Action Result
- Next Planned Action
- Current Agenda (goals)
- HARD STOP status
- Memory status
- Uptime
- Heartbeat timestamp
- Cycles (act/cycle/session counts)

**To add voice state**, extend `LifeMindState` with:

```python
voice_listening_mode: NotRequired[str]  # "off" | "ptt" | "always_listening"
voice_last_utterance: NotRequired[str]  # ISO timestamp or truncated transcript
voice_last_command: NotRequired[str]    # Most recent spoken command intent
```

Then add a `_voice_section()` to `DashboardRenderer` (dashboard.py) and a field in `render_embed()`.

### Log channel for voice

`LogChannel.write(message)` at `log_channel.py:58` is the append-only interface. Voice lifecycle events should be logged:
- `"[VOICE] Always-listening enabled (consent granted)"`
- `"[VOICE] HARD STOP via voice safe word"`
- `"[VOICE] Recovery from HARD STOP via voice"`
- `"[VOICE] Microphone device unavailable — fallback to PTT"`

### HARD STOP bypass for voice dashboard updates

`DashboardWriter.publish_hard_stop()` at `dashboard_writer.py:184` force-publishes the HARD STOP state bypassing the checksum-skip. The voice pipeline must call this same method (or equivalent) when the spoken safe word triggers HALT, via:

```python
# After SET life_kernel:hard_stop in Redis:
await dashboard_writer.publish_hard_stop(state_with_hard_stop=True)
```

The `_heartbeat_1s()` also does this (heartbeat.py:312-318) — so it may happen redundantly, which is acceptable (fail-safe idempotency).

---

## 5. HermesBrain.think() — Proactive Voice Output Seam

### The existing think() interface

`HermesBrain.think()` at `hermes_brain.py:258-343`:
- Takes `user_message: str`, `system_prompt: str`, `conversation_history: list[dict]`
- Calls `AIAgent.run_conversation()` (blocking, offloaded via `asyncio.to_thread`)
- Returns `{final_response, input_tokens, output_tokens, total_tokens, model, estimated_cost_usd}`

`HermesBrain.think_with_tools()` at `hermes_brain.py:372-452`:
- Same as `think()` but passes `tools: list[Any]` for tool-using reasoning

### Proactive TTS output

The kernel should be able to initiate voice output WITHOUT a user utterance (e.g., morning briefing, alarm, notification). The seam is:

1. **Triggers**: The 60s heartbeat (`_heartbeat_60s`, heartbeat.py:421-492) is the natural trigger. On state `"voice_output_pending"` in the graph, the kernel would generate the response text via `HermesBrain.think()` or a lighter invocation.

2. **Generation**: Call `hermes_brain.think()` with a system prompt like "Generate a concise spoken greeting for the operator. It is 08:30 WIB. Keep it under 30 words." The response text goes to TTS.

3. **Gating**: Before any proactive TTS, check:
   - `life_kernel:hard_stop` Redis key — must be CLEAR
   - `voice_listening_mode` — must NOT be "off"
   - `consent_scope` — must include proactive_voice (see §6)
   - `dnd_active` — must resolve first (Discord DND 00:00-07:00 WIB, per DiscordUXSpec)

4. **Queue**: The voice output must be serialized through a single queue so proactive TTS doesn't interrupt an ongoing conversation. The simplest approach: a `asyncio.Queue[str]` that the TTS-consuming coroutine drains, with proactive messages only enqueued when the queue is empty AND the system is not mid-utterance.

### Code location for the gating

In `heartbeat.py`'s `_heartbeat_60s()` or in the graph's `idle_node()`, after determining the kernel is truly idle and the operator is likely present, check the consent flag and enqueue a TTS message. This keeps proactive voice out of the hot path.

---

## 6. Always-Listening vs. Autonomy Exception

### The conflict

The living autonomy kernel is designed to be **autonomy-first** — the heartbeat runs 24/7, the graph creates self-directed tasks when Faiz is silent (idle_node at graph.py:572), and HermesBrain generates autonomous decisions (`_make_brain_decide` at graph.py:715). This autonomy principle (V-003: "silence is not a blocker") is central to the kernel's design.

Voice always-listening (continuous microphone capture) is a **surveillance-class capability** that directly conflicts with this autonomy principle:

| Principle | Always-listening | Conflict |
|-----------|-----------------|----------|
| Autonomous (V-003) | Kernel may start listening unbidden | Must NOT auto-enable |
| Consent-gated (P18) | Surveillance adapter is consent-gated | Voice has the same restriction |
| Hard Stop | Safe word halts everything | Voice must honor HARD STOP |
| Audit trail | All state changes logged | Voice enable/disable must be audited |

### The SurveillanceSensorAdapter precedent

At `sensor_adapters/surveillance_adapter.py:8-22`:

```python
class SurveillanceSensorAdapter(BaseSensorAdapter):
    SENSOR_NAME = "surveillance"
    DEFAULT_CONTENT = (
        "Surveillance data placeholder — access is consent-gated. No raw "
        "surveillance feed is read or stored in v1."
    )
```

The voice always-listening adapter must follow the same pattern: **consent-gated by default, never auto-enabled.**

### Required gating for always-listening activation

1. **Explicit Faiz consent** — must be stored in the consent_ledger (P18 consent schema). A field `voice_always_listening: bool` in `faiz_profile` or `consent_scope_registry`. The voice pipeline checks this before every capture start.

2. **Visible indicator** — the dashboard embed must show `Voice: 🔴 Always Listening` or `Voice: 🟢 PTT` status. The `voice_listening_mode` field in LifeMindState drives this.

3. **HARD STOP overrides everything** — if `life_kernel:hard_stop` is set, always-listening stops immediately, even mid-transcription.

4. **DND (00:00-07:00 WIB)** — the DiscordUXSpec §DND period must also gate proactive voice output (though the operator may still speak and trigger HARD STOP even in DND). During DND, always-listening should be paused.

5. **Audit** — every enable/disable of always-listening must write to the audit trail (audit.audit_trail table with hash chain) AND to the log channel.

### Architectural placement

The always-listening gate should live in a dedicated `voice_gate.py` module (not in the kernel directly), exposing:

```python
class VoiceGate:
    async def can_listen(self) -> bool:
        """Returns True iff always-listening is consent-gated ON, HARD STOP clear, DND resolved."""
    
    async def can_speak_proactive(self) -> bool:
        """Returns True iff proactive voice is consented, HARD STOP clear, DND resolved."""
```

This gate is consulted by both:
- The always-listening capture loop (pre-capture)
- The heartbeat/graph (proactive TTS gating)

### Autonomy exception for HARD STOP

The one exception to "voice must be consent-gated" is the **HARD STOP path**. The safe word must ALWAYS be detected and acted upon, regardless of consent state. This is already how the text-based HardStopHandler works (it runs on RAW input before any other filtering). The STT pipeline must run HARD STOP detection on every transcript, even if the system is in "off" mode for conversation — though in practice, if the mic is off, there's no transcript to check. The solution: when the HARD STOP safe word is spoken, the operator knows to say it clearly, and the system MUST be listening for it (which is itself a form of always-listening). This is a design tension: the mic must be hot enough to hear a safe word but not so hot that it captures everything.

**Recommended approach**: A minimal "safe word wake" mode where the microphone is active but audio is immediately discarded unless (a) the VAD detects speech AND (b) the STT output matches a safe word pattern. This keeps privacy while preserving the safety path.

---

## 7. Cross-Specialist Intersections

- **Prompt injection researcher**: Voice transcript = untrusted text (V-022-class). Must run through existing quarantine/sanitization before reaching Hermes. The HardStopHandler runs on RAW transcript FIRST (existing behavior at hard_stop_handler.py:89-103), then the sanitized/labelled transcript goes to the conversational pipeline.
- **Discord voice APIs researcher**: The life_kernel voice sensor adapter does NOT depend on Discord.py's voice API — it's a general interface. Discord-specific VAD/PTT/connection handling belongs in the Discord voice researcher's domain.
- **Hermes core integration researcher**: `HermesBrain.think()` is the bridge for both conversational turns and proactive TTS. The voice pipeline's conversation handler reuses `HermesBrain.think()` or `HermesSessionAdapter.send_message()`.
- **Audio pipeline researcher**: The life_kernel cares only about the STT output (text) going to HardStopHandler + Hermes conversation, and the TTS input (text) coming from Hermes. Audio capture/codec concerns are the audio pipeline researcher's domain.
- **Data policy researcher**: Voice transcripts are privacy-sensitive data. The VoiceSensorAdapter must NOT log raw transcripts. The sanitized observation fed to the kernel is metadata-only (timestamps, counts).

---

## 8. Design Recommendations

### R1: Single HARD STOP key, no duplication
The voice pipeline reads and writes Redis key `life_kernel:hard_stop` — the same key the 1s heartbeat polls. No new kernel stop path needed.

### R2: VoiceSensorAdapter for kernel awareness
Create `sensor_adapters/voice_adapter.py` with `class VoiceSensorAdapter(BaseSensorAdapter)` that feeds voice state metadata into the observer loop. Register with `SensorRegistry` at kernel startup.

### R3: VoiceGate module for consent gating
Create `src/voice/voice_gate.py` with `VoiceGate.can_listen()` and `VoiceGate.can_speak_proactive()` that check:
- `life_kernel:hard_stop` in Redis (must be absent)
- Consent ledger for `voice_always_listening` (must be True)
- DND window (not during 00:00-07:00 WIB)
- Returns the combined decision

### R4: Dashboard voice fields
Add `voice_listening_mode`, `voice_last_utterance`, `voice_last_command` to `LifeMindState` (state.py). Extend `DashboardRenderer.render_embed()` (dashboard.py) with a "Voice" inline field.

### R5: Proactive TTS queue
In `heartbeat.py`'s `_heartbeat_60s()`, after a successful decision cycle, if the graph indicates the kernel wants to speak (new state field `proactive_tts_message`), and `voice_gate.can_speak_proactive()` returns True, enqueue the message into the TTS queue. The TTS consumer drains this queue in FIFO order, not interrupting ongoing speech.

### R6: Audit every voice state transition
Every microphone/always-listening state change (off→listening→speaking→off) should write to `LogChannel` and optionally to the `audit.audit_trail` table. This is fail-soft (log failures don't break voice) but required for compliance.

### R7: Never auto-enable always-listening
Always-listening defaults to OFF at boot. Only enabled via explicit Faiz consent (stored in P18 consent_ledger). The voice pipeline refuses to capture audio until explicitly enabled. This is enforced in `voice_gate.py`, not in the kernel.

### R8: Two-tier design — real-time + awareness
Voice has two integration tiers into the kernel:
| Tier | Latency | Path | Purpose |
|------|---------|------|---------|
| 1 — Reactive | < 2s (real-time) | STT → HardStopHandler → Hermes pipeline → TTS | Conversational turn |
| 2 — Reflective | 10-30s | VoiceSensorAdapter.sense() → observer loop → graph state | Dashboard display, awareness |

The reactive tier bypasses the kernel graph entirely. The reflective tier feeds metadata into the graph. Do NOT route conversational turns through the 60s heartbeat — that destroys the real-time UX.

---

## Verdict: PASS

All life_kernel integration points for P21 voice are documented:
1. HARD STOP life_kernel:hard_stop Redis key: heartbeat.py:273-322 mapped
2. Sensor adapter interface: sensor_adapters/base.py:57-73 mapped + SensorRegistry at sensors.py:108-148
3. Graph observe→decide→act→reflect cycle: graph.py:850-995, injection via P18 memory recall in observe_node
4. DashboardWriter.update_dashboard: dashboard_writer.py:126-183 + publish_hard_stop: dashboard_writer.py:184-218
5. LogChannel.write: log_channel.py:58-63
6. HermesBrain.think(): hermes_brain.py:258-343, proactive TTS seam at heartbeat.py:421-492
7. VoiceGate consent gating: surveillance_adapter.py precedent, design for voice_gate.py

No autonomous always-listening activation proposed. Eight design recommendations provided.

**File**: `docs/setup-evidence/P21/research/p21-life-kernel-integration-research.md`
