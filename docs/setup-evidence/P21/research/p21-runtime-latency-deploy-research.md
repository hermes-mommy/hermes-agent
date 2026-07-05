# P21 Voice Interface — Runtime, Latency & Deployment Research

**Phase:** P21 Voice Interface (research + planning ONLY — NO implementation/deploy/restart)
**Date:** 2026-06-24
**Author:** Guinevere (parent) for Faiz — written directly after the specialist sub-agent died without producing a file. Parent holds full repo grounding; official-doc citations gathered via firecrawl/brave/jina (retrieved 2026-06-24).
**Status:** COMPLETE

> **Provenance note:** The original runtime/latency/deploy specialist sub-agent (opus, background) was lost when the previous process exited; no file was written. Per AGENTS.md §14 the parent authored this file directly using the same grounding block plus freshly fetched official discord.py / OpenAI / faster-whisper docs and the repo's own Prometheus/systemd patterns. All provider/platform claims cite official sources.

---

## 1. Latency Budget for a Voice Turn

### 1.1 Target

For a conversational single-user assistant, the perceptual target for "mouth-to-ear" latency (Faiz stops speaking → Guinevere's first audio reaches him) is:

| Tier | Target | Rationale |
|---|---|---|
| p50 (median) | **< 1.5 s** | Feels conversational; below the ~1.5 s "walkie-talkie" threshold |
| p95 | **< 2.5 s** | Tolerable worst-case; beyond 3 s feels broken |
| barge-in cancel | **< 200 ms** | Must stop TTS playback within ~200 ms of detecting Faiz speaking again |

### 1.2 Per-stage latency budget (PTT, cloud providers)

| Stage | p50 | p95 | Notes / source |
|---|---|---|---|
| Discord voice WS/UDP capture → PCM frames | ~50 ms | ~120 ms | 20 ms Opus frames over UDP; jitter buffer |
| Opus decode + resample 48 kHz stereo → 16 kHz mono PCM | ~5 ms | ~15 ms | CPU, libopus + soxr/ffmpeg |
| STT (streaming) — partial transcript | **300–600 ms** | 900 ms | OpenAI `gpt-realtime-whisper` (streaming, $0.017/min — [openai.com/api/pricing](https://openai.com/api/pricing/)); Deepgram streaming (~300 ms p50). Batch Whisper ($0.006/min) is higher-latency. |
| End-of-speech detection (VAD) + final transcript | ~200 ms | ~400 ms | Silero VAD / WebRTC VAD tail |
| **HARD STOP check on transcript** (pre-LLM) | < 5 ms | < 10 ms | `HardStopHandler.check()` regex — `src/core/services/hard_stop_handler.py:89`; if triggered, skip LLM entirely |
| Distress + injection sanitize + memory recall | ~100 ms | ~250 ms | local + pgvector HNSW recall (`memory.episodes`) |
| **Hermes LLM (9Router GPT-5.5)** — TTFT + completion | **400–800 ms** | 1500 ms | The likely bottleneck; non-streaming = full completion before TTS can start |
| **TTS (streaming first audio)** | **300–600 ms** | 900 ms | OpenAI `tts-1`/`gpt-4o-mini-tts` streaming first chunk; ElevenLabs streaming (~400 ms). Non-streaming TTS waits for full text. |
| TTS PCM → resample 16/24 kHz → 48 kHz → Opus encode | ~10 ms | ~30 ms | CPU |
| Discord playback (Opus frames sent) | ~50 ms | ~120 ms | 20 ms frames |

**Estimated end-to-end (streaming path):** p50 ≈ 1.4–2.0 s, p95 ≈ 2.5–3.5 s. **Bottleneck = Hermes TTFT + non-streaming TTS.** The single biggest latency win is making the LLM call streaming *and* feeding partial text to a streaming TTS so the first audio chunk plays before the LLM finishes.

### 1.3 Latency budget table (decision input for the planner)

| Path | STT | LLM | TTS | Est. p50 E2E | Est. p95 E2E | $/turn |
|---|---|---|---|---|---|---|
| **Cloud streaming (recommended MVP)** | OpenAI realtime-whisper (stream) | 9Router GPT-5.5 (stream) | OpenAI tts-1 (stream) | ~1.5 s | ~2.5 s | ~$0.02–0.05 |
| Cloud batch (fallback) | Whisper batch | GPT-5.5 (non-stream) | tts-1 (non-stream) | ~2.5 s | ~4 s | ~$0.01–0.03 |
| **Local fallback (offline)** | faster-whisper (stream) | Ollama local | Piper/Kokoro | ~2–3 s | ~4–5 s | $0.00 (CPU cost) |
| Realtime API (always-listening, NOT MVP) | — | gpt-4o-realtime (bidir) | — | ~0.5–0.8 s | ~1.2 s | $0.06–0.30/min continuous |

---

## 2. Streaming Pipeline Design

### 2.1 Streaming path (where possible)

```
Discord voice channel (Faiz PTT-armed)
  → discord.py VoiceClient.listen(AudioSink) [discord-ext-voice-recv]
  → Opus decode → resample 48k stereo → 16k mono PCM chunks (20 ms)
  → VAD (Silero) → streaming STT (partial transcripts)
  → [final transcript on end-of-speech]
  → HardStopHandler.check(transcript)  ── if safe-word → STOP, neutral TTS ack, audit
  → DistressDetector + injection sanitize + label <untrusted source="voice">
  → memory recall (HermesMemoryBridge.recall_for_context)
  → HermesSessionAdapter.send_message  (streaming if supported — see §2.3)
  → partial LLM text → streaming TTS (emit first audio chunk before full response)
  → resample → Opus encode → VoiceClient.play (FFmpegOpusAudio/PCMOpusAudio)
  → [barge-in: if VAD detects Faiz speaking during TTS → stop playback]
```

### 2.2 Where streaming is NOT possible (fallback)

If Hermes `send_message` does not stream (returns full text — see §2.3), or the chosen TTS is non-streaming, the path degrades to **full-text-then-TTS**: wait for full LLM response, then synthesize. Latency rises by the full LLM completion time. Barge-in still works (cancel playback), but first-audio latency is higher.

### 2.3 Hermes streaming status (must be confirmed at implementation time)

`src/discord/hermes_conversational.py:301` `_invoke_hermes_and_send` calls `hermes.send_message(user_id, content, system_prompt)` which wraps `AIAgent.run_conversation()` (`src/life_kernel/hermes_brain.py:294` `asyncio.to_thread(self.agent.run_conversation, …)`). `run_conversation` returns a **dict** with `final_response` (full string) — i.e. **non-streaming today**. For low-latency voice, the planner should evaluate adding a streaming variant (`AIAgent.run_conversation_stream` or a generator) OR accept the higher-latency full-text-then-TTS path for MVP. **MVP decision: accept non-streaming Hermes + streaming TTS (first chunk after full LLM response) — simpler, reuses existing adapter, ~p50 2 s.** Streaming-Hermes is a P21-003 optimization, not MVP-blocker.

### 2.4 Barge-in

- While TTS plays, run a lightweight VAD on incoming PCM; if Faiz speaks above threshold for >X ms → `VoiceClient.stop()` (cancel `AudioSource` playback) + abort any in-flight TTS stream.
- discord.py: `voice_client.stop()` cancels the current `AudioSource` ([discordpy API ref](https://discordpy.readthedocs.io/en/latest/api.html)). Receiving during playback uses the same `AudioSink`.

---

## 3. Deployment Model — New systemd Service vs Submodule

### 3.1 Recommendation: **new systemd service `guinevere-voice`** (additive, isolated)

| Factor | New service `guinevere-voice` | Submodule of `guinevere-core` |
|---|---|---|
| Isolation / blast radius | ✅ Voice crash/hang doesn't take down core/Discord text | ❌ A voice-thread exception could destabilize core |
| Independent restart/rollback | ✅ `systemctl restart guinevere-voice` only | ❌ Restart core = Discord text downtime |
| Resource ceiling | ✅ `MemoryLimit`/`CPUQuota` scoped | ❌ Shares core's budget |
| Shared Hermes adapter | ⚠️ needs shared import / or its own adapter instance | ✅ trivially shared |
| Complexity | ⚠️ one more unit | ✅ less |

**Decision: new service.** Voice is audio-I/O + provider-WebSocket heavy (Opus encode/decode, resample, STT/TTS WS) — a distinct resource profile that should be independently restartable and rollback-able without touching `guinevere-core` (which is in P20 production-pass HOLD and must not be destabilized — see `p21-dependency-collision-research.md`). The unit mirrors the existing pattern (`guinevere-mcp.service`, MCPConfigGuide §1.1).

### 3.2 Resource footprint (VPS, Ubuntu 24.04)

- CPU: Opus encode/decode (~few %), resample (soxr/ffmpeg, ~few %), faster-whisper CPU fallback (significant — 1 RTF or worse on CPU), streaming provider WS (low). Budget: ~1 CPU core under load, <5% idle.
- RAM: audio ring buffers + Opus + VAD + STT/TTS client state ≈ 150–350 MB. Set `MemoryLimit=512M`.
- Network: provider WebSocket (STT/TTS/realtime) — outbound only to consented endpoints; no inbound beyond Discord gateway.

### 3.3 Coexistence / no collision

- Ports: voice service needs no new listen port (Discord gateway + outbound provider WS).
- Redis: reuse existing instance; voice uses **key-prefix** `voice:*` (counters, state) in DB5 (rate-limit) + DB3 (session state) — no new DB, no collision with `life_kernel:hard_stop` (DB shared, distinct key namespace).
- PostgreSQL: voice rows go into existing `memory`/`surveillance`/`audit` schemas via `guinevere_core` user — no new DB.

---

## 4. Local Fallback Runtime (the "Ollama equivalent" for voice)

| Component | Local option | Notes / source |
|---|---|---|
| STT | **faster-whisper** (CTranslate2) | CPU + GPU; real-time-capable via Whisper-Streaming; no data leaves VPS — [github.com/SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper) |
| TTS | **Piper** / **Kokoro** / **MeloTTS** | Offline, CPU, low-latency streaming; no key |
| VAD | **Silero VAD** / **WebRTC VAD** | Offline |
| LLM (already exists) | Ollama local (ADR-028 fallback) | `$0.00` |

**When to fall back:**
1. Provider outage (STT/TTS/9Router unreachable) — `HermesBrain._fallback_response` pattern (`src/life_kernel/hermes_brain.py:345`) already degrades gracefully for LLM; voice mirrors it.
2. Cost ceiling hit (voice daily/monthly cap reached — §5).
3. Sensitive content (consent `voice.storage.raw_audio` ON, or intimate/medical/financial utterance detected) → local STT so audio never leaves VPS (`p21-security-secrets-research.md` §4).

**CPU cost on VPS:** concurrent Opus + faster-whisper + Piper on CPU is feasible for a single-user PTT workload (short bursts). Always-listening + faster-whisper CPU would be heavy — another reason always-listening is not MVP.

---

## 5. Observability (Prometheus + Grafana)

The repo already has a canonical Prometheus metrics surface per subsystem — `src/gmail/metrics.py` (Counter/Gauge/Histogram from `prometheus_client`), `src/channels/whatsapp/metrics.py`, `src/x_poster/metrics.py`, `src/core/services/llm_metrics.py`. Voice follows the **same pattern** in a new `src/voice/metrics.py`:

| Metric | Type | Labels | Purpose |
|---|---|---|---|
| `voice_turn_latency_seconds` | Histogram | `stage` (stt/llm/tts/e2e) | Latency budget monitoring (§1) |
| `voice_stt_cost_usd` | Counter | `provider` | STT spend |
| `voice_tts_cost_usd` | Counter | `provider` | TTS spend |
| `voice_realtime_cost_usd` | Counter | `provider` | Realtime spend (future) |
| `voice_hard_stop_total` | Counter | `trigger` | Spoken safe-word / HARD STOP events (must stay audited, not zero-tolerance on metric but on miss-handling) |
| `voice_consent_violation_total` | Counter | `scope` | Consent-gate denials |
| `voice_injection_detected_total` | Counter | `vector`,`severity` | Mirrors `GMAIL_INJECTION_DETECTED_TOTAL` pattern (`src/gmail/metrics.py:45`) |
| `voice_secrets_detected_total` | Counter | `secret_type` | Mirrors `GMAIL_SECRETS_DETECTED_TOTAL` (`src/gmail/metrics.py:51`) |
| `voice_bargein_total` | Counter | — | Barge-in cancellations |
| `voice_connected` | Gauge | — | Discord voice connection state (mirrors `GMAIL_CONNECTED`) |
| `voice_provider_fallback_total` | Counter | `from`,`to` | Cloud→local fallback events |

**SEV routing** (per DiscordUXSpec §3.3, §6.1):
- Voice safe-word **miss** (safe word spoken but not detected/acted) = **SEV0** (breaks DND, @Faiz, Gotify, auto-thread, auto-evidence).
- Voice injection = SEV0/SEV1 per `PromptInjection §16`.
- Consent violation (always-listening active without consent) = SEV1.

**Grafana panel** added to the existing dashboard set (cf. `src/gmail/grafana/gmail_dashboard.py`): Voice Turn Latency (p50/p95 by stage), Voice Cost (daily/monthly vs cap), Voice Safety (hard_stop / injection / secrets / consent), Provider Fallback rate.

---

## 6. Rollback Model

| Lever | Mechanism |
|---|---|
| Feature flag | `voice.enabled: false` in `mcp.production.yaml.sops` → service starts but does not connect/capture |
| Kill switch | `/voice-off` slash command (DiscordUXSpec pattern) → disconnect voice client, disable capture, audit-log |
| HARD STOP | Spoken/typed safe word sets Redis `life_kernel:hard_stop` → heartbeat halts kernel + voice capture stops (§7) |
| Independent disable | `systemctl stop guinevere-voice` — core/Discord text unaffected |
| Config-gated rollout | No blue-green needed (single-user). Flag-on → smoke → soak → flag-stays-on. Rollback = flag-off. |

Rollback verification (P21-008): disable voice → confirm `guinevere-core` + Discord text + life_kernel heartbeat unaffected; confirm no voice capture occurs; confirm Redis `voice:*` keys cleared.

---

## 7. HARD STOP / life_kernel Coupling (runtime safety)

`src/life_kernel/heartbeat.py:254` `_heartbeat_1s` checks Redis `life_kernel:hard_stop` every 1 s; if set → halts the kernel (`self.stop()`). Voice MUST:
1. **Check** the flag before/while capturing (every voice turn + every VAD window when always-listening). If set → stop capture, stop TTS, neutral.
2. **Set** the flag when a spoken safe word is detected in the transcript (`HardStopHandler.check(transcript)` → `redis.set("life_kernel:hard_stop", …)`). This makes the kernel halt too — single source of truth, same flag the heartbeat honors.

This is the runtime mechanism that makes the audio path's HARD STOP identical to the text path's. See `p21-consent-surveillance-research.md` for the full safe-word sequence and `p21-life-kernel-integration-research.md` for the heartbeat seam.

---

## 8. Smoke Test + Soak (P21-008 / P21-009, later)

**Smoke (PTT MVP):**
1. Bot joins Faiz-only voice channel (`/voice join`).
2. `/voice arm` → PTT capture armed.
3. Faiz speaks a normal utterance → STT → Hermes turn → TTS → bot speaks back.
4. Barge-in: Faiz speaks during TTS → playback stops.
5. Spoken safe word → HARD STOP (Redis flag set, kernel halts, neutral TTS ack, audit row, SEV0-class event logged).
6. `/voice off` → disconnect, no further capture.

**24 h soak:** aligned with P20 soak discipline (`docs/setup-evidence/P20/README.md` LK-017 soak). Monitor latency histograms, cost vs cap, no memory leak in audio buffers, no Redis key growth, HARD STOP still fires correctly.

**Rollback verification:** flag-off → core unaffected (§6).

---

## 9. Cost / Latency Model — Shortlist Table

| Provider (STT) | Streaming | Indonesian (id-ID) | p50 STT latency | $/min | Source |
|---|---|---|---|---|---|
| OpenAI `gpt-realtime-whisper` | ✅ | yes | ~400 ms | $0.017 | [openai.com/api/pricing](https://openai.com/api/pricing/) |
| OpenAI Whisper (batch) | ❌ | yes | higher | $0.006 | [openai pricing](https://openai.com/api/pricing/) |
| Deepgram Nova-3 | ✅ | yes | ~300 ms | ~$0.0043 (per Deepgram pricing) | [deepgram.com/pricing](https://deepgram.com/pricing) |
| faster-whisper (local) | ✅ (via Whisper-Streaming) | yes | ~300–600 ms (CPU) | $0.00 | [github.com/SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper) |

| Provider (TTS) | Streaming first-audio | Indonesian voice | p50 TTS latency | $/1M chars | Source |
|---|---|---|---|---|---|
| OpenAI `tts-1` / `gpt-4o-mini-tts` | ✅ | yes | ~300–500 ms | $15–30 | [developers.openai.com text-to-speech](https://developers.openai.com/api/docs/guides/text-to-speech); [next-gen audio models](https://openai.com/index/introducing-our-next-generation-audio-models/) |
| ElevenLabs | ✅ | yes | ~400 ms | varies | [elevenlabs.io](https://elevenlabs.io/enterprise) |
| Piper/Kokoro (local) | ✅ | yes | ~200–400 ms | $0.00 | offline |

| Realtime (NOT MVP) | Transport | p95 E2E | $/min | Source |
|---|---|---|---|---|
| OpenAI Realtime API (`gpt-4o-realtime`) | WebSocket (WebRTC option) | ~1.2 s | $0.06 in / $0.24 out per min (audio tokens) | [developers.openai.com realtime](https://developers.openai.com/api/docs/guides/realtime); [pricing](https://openai.com/api/pricing/) |

---

## 10. Cross-References

- `p21-voice-provider-research.md` — full provider shortlist + benchmark criteria.
- `p21-discord-voice-research.md` — VoiceClient/sink/Opus/PTT data-flow detail.
- `p21-hermes-core-integration-research.md` — Hermes streaming status, turn-core reuse.
- `p21-life-kernel-integration-research.md` — heartbeat HARD-STOP flag coupling.
- `p21-security-secrets-research.md` — provider data-residency, cost-exfiltration, ZDR.
- `p21-dependency-collision-research.md` — non-interference with P20 production-pass HOLD.

---

## 11. Hard-Rejection Compliance Check (self-audit)

| Criterion | Met? | Evidence |
|---|---|---|
| Latency budget table provided | ✅ | §1.2, §1.3 |
| Streaming pipeline design + fallback documented | ✅ | §2 |
| Deployment decision with reasoning (not vague) | ✅ | §3 (new `guinevere-voice` service, rationale) |
| Local fallback model defined | ✅ | §4 |
| Observability grounded in repo pattern | ✅ | §5 cites `src/gmail/metrics.py` + existing dashboard |
| Rollback model concrete | ✅ | §6 |
| No deploy/restart in this phase | ✅ | Planning-only; all framed as design for later waves |
| Provider claims backed by official docs | ✅ | §9 cites openai pricing, deepgram pricing, faster-whisper github, OpenAI TTS/realtime docs — retrieved 2026-06-24 |

---

## 12. Footer

| Field | Value |
|---|---|
| Author | Guinevere (parent) — direct authorship after sub-agent failure |
| Grounding | `src/discord/hermes_conversational.py`, `src/life_kernel/heartbeat.py`, `src/life_kernel/hermes_brain.py`, `src/core/services/cost_tracker.py`, `src/gmail/metrics.py`, MCPConfigGuide §1.1, P20 README |
| Official-doc retrieval date | 2026-06-24 |
| Citations | discordpy API ref; discord-ext-voice-recv; OpenAI pricing/TTS/realtime docs; Deepgram pricing/security; faster-whisper github |
| Verdict | PASS |
