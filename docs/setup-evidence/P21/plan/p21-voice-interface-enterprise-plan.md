# P21 Voice Interface — Enterprise Implementation Plan

> **For agentic workers:** This plan defines future implementation waves (P21-001..P21-009). Per the P21 phase objective, **NO implementation/deploy/restart is performed in the planning phase.** Waves are held until the **P20 Living Autonomy Kernel production-pass** completes (LK-017 soak). When execution begins, use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement wave-by-wave. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe, deeply-integrated voice interface to Guinevere alongside the existing Discord text channel — STT ingestion (push-to-talk + gated wake-word), TTS replies, realtime interruption handling, consent gating, and surveillance-class retention — by reusing the existing Hermes turn-core, HARD STOP, distress, and injection infrastructure rather than building a sidecar.

**Architecture:** A voice turn is text-in/text-out at its core. STT produces a transcript → the transcript flows through the **same shared turn-core** that Discord text uses (`_process_turn_core`, refactored from `_process_and_respond()`) → TTS renders the response. HARD STOP detection runs on the transcript **before** Hermes (`HardStopHandler.check(transcript)`), identical to the text path, and sets the same Redis `life_kernel:hard_stop` flag the heartbeat polls. Voice is a new additive `src/voice/` package + a `guinevere-voice` systemd service, NOT a sidecar — zero new safety code, zero duplication of safety hooks. Always-listening is NOT MVP (full consent gating required first).

**Tech Stack:** Python/FastAPI, discord.py + `discord-ext-voice-recv` (AudioSink receive), PyNaCl/libopus (Opus 48kHz), streaming STT (Deepgram Nova-3 Multilingual / OpenAI gpt-realtime-whisper), streaming TTS (Cartesia Sonic 3.5 / OpenAI tts-1), local fallback (faster-whisper + Piper), Silero VAD, openWakeWord, PostgreSQL 16 (memory/surveillance/consent/audit schemas), Redis (DB3 session + DB5 rate-limit, key-prefix `voice:*`), SOPS/age secrets, Prometheus + Grafana, systemd.

---

## Global Constraints

(These apply to every wave. Each wave's requirements implicitly include this section.)

- **Planning-only this phase:** NO runtime code, NO deploy, NO restart of production services in P21 planning. Waves execute later, gated on P20 production-pass.
- **Implementation HOLD:** Wave 3+ (LOCKED-file edits: `src/core/main.py`, `src/discord/_entrypoint.py`, `pyproject.toml`, `src/life_kernel/state.py` additive, `src/memory/models.py` additive) are BLOCKED until `docs/setup-evidence/P20/README.md` LK-017 reaches PRODUCTION PASS. NEW files (Wave 1: `src/voice/*`, `src/life_kernel/sensor_adapters/voice_sensor_adapter.py`, `alembic/versions/p21_001_voice_stream.py`, `secrets/voice-secrets.enc.yaml`, `tests/voice/*`) are unblocked and non-conflicting with the P20 soak.
- **Voice transcript = untrusted text (Trust Level 6):** Every transcript MUST pass: `HardStopHandler.check()` on RAW transcript (pre-sanitization, SW-PI-008) → injection classify/sanitize → `<untrusted source="voice" trust="6">` label → quarantine to L7-L9. Register voice as injection vector **V-022**.
- **HARD STOP is first-class in the audio path:** Spoken safe word → `HardStopHandler.check(transcript)` → set Redis `life_kernel:hard_stop` → SafeModeController/Y0/neutral → TTS neutral ack → minimal non-punitive audit. Zero false-negative tolerance.
- **Always-listening is NOT MVP:** `voice.always_listening` consent scope defaults OFF and stays disabled until ALL 8 gating checks pass (explicit consent + visible indicator + retention policy + HARD STOP honored + audit + device auth + purpose-bound + no-silent-reactivation).
- **Secrets:** All voice provider API keys in SOPS-encrypted `secrets/voice-secrets.enc.yaml` (or 9Router-proxied for OpenAI audio), decrypted at startup, never in repo/logs/MCP. Quarterly rotation.
- **No raw audio in artifacts/logs/MCP:** Raw audio discarded after STT by default; if retained (diagnostic), max 24h encrypted (`envelope-AES-256-GCM`) in `surveillance.events.raw_payload`, auto-purge.
- **Transcripts must not enter memory without redaction/retention/injection-gate:** MEM-001..008 write-validation + safe-state check + secret-scanner + instruction-pattern quarantine before any `memory.episodes` insert.
- **Integration, not sidecar:** Voice reuses the Hermes turn-core; the only new code is STT/TTS wire, the L6 quarantine wrapper, the Discord voice-channel connection, and the additive sensor/dashboard.
- **P19 forward-compat:** Voice episodes carry a nullable `project_id` so P19 (multi-project namespaces, not started) can partition later without a backfill.
- **USD 30/mo cap:** Voice STT/TTS costs feed the existing `CostTracker` with model tags `stt:*` / `tts:*` / `realtime:*`; voice sub-cap (`voice.cost.monthly_cap_usd`) within the system cap.
- **RBAC:** Voice subsystem uses `guinevere_core` DB user (no superuser). Sub-agents touching voice = task-scoped, no Critical data.
- **Type safety:** No `# type: ignore`, `as any`, bare `except`, empty catch. Pydantic models + strict checks.
- **Single-user:** Faiz-only voice channel; non-Faiz audio capture disabled by default.

---

## File Structure

(Decomposition locked here. Each file has one clear responsibility. Follows existing repo patterns — `src/gmail/`, `src/channels/whatsapp/`, `src/discord/` for structure; `src/gmail/metrics.py` for Prometheus; `src/memory/models.py` `ClassificationMetaMixin` for storage.)

**NEW files (P21-owned, Wave 1 — unblocked):**
| File | Responsibility |
|---|---|
| `src/voice/__init__.py` | Package marker |
| `src/voice/config.py` | Voice config dataclass (Pydantic); loads `voice:` section from decrypted `mcp.production.yaml.sops` (or `voice-secrets.enc.yaml`); env-var resolution |
| `src/voice/types.py` | Typed models: `VoiceTurn`, `ProcessedTurn`, `VoiceSessionState`, `TranscriptEvent`, enums (`VoiceMode`, `VoiceStage`) |
| `src/voice/exceptions.py` | `VoiceError` hierarchy: `STTError`, `TTSError`, `VoiceConsentError`, `VoiceHardStopError`, `AudioTransportError` |
| `src/voice/sanitize.py` | Transcript quarantine wrapper: classify (Trust 6) → strip instruction patterns → secret-scanner (reuse `src/surveillance/secret_scanner.py`) → label `<untrusted source="voice" trust="6">` → return `SanitizedTranscript` |
| `src/voice/voice_gate.py` | `VoiceGate` class: `can_listen()` / `can_speak_proactive()` — checks Redis `life_kernel:hard_stop` absent + consent ledger + DND window. Fail-closed. |
| `src/voice/safe_word_override.py` | SW-PI-003 safe-word-override rejection (detects "safe word is revoked/disabled" in transcript → reject + SEV0); boundary-insensitive safe-word matching helper for STT robustness. Preferred over editing the locked `hard_stop_handler.py`. |
| `src/voice/stt/base.py` | `STTProvider` Protocol: `async def transcribe(pcm_chunks: AsyncIterator[bytes]) -> TranscriptEvent` (streaming) + `async def health() -> bool` |
| `src/voice/stt/openai_stt.py` | `OpenAISTTProvider(STTProvider)` — gpt-realtime-whisper streaming |
| `src/voice/stt/deepgram_stt.py` | `DeepgramSTTProvider(STTProvider)` — Nova-3 Multilingual streaming |
| `src/voice/stt/faster_whisper_stt.py` | `FasterWhisperSTTProvider(STTProvider)` — local fallback, no network |
| `src/voice/tts/base.py` | `TTSProvider` Protocol: `async def synthesize(text: str) -> AsyncIterator[bytes]` (streaming PCM) + `async def health() -> bool` |
| `src/voice/tts/cartesia_tts.py` | `CartesiaTTSProvider(TTSProvider)` — Sonic 3.5 WebSocket |
| `src/voice/tts/openai_tts.py` | `OpenAITTSProvider(TTSProvider)` — tts-1 streaming |
| `src/voice/tts/piper_tts.py` | `PiperTTSProvider(TTSProvider)` — local fallback, Indonesian id-ID voice |
| `src/voice/audio_codec.py` | Opus decode/encode (libopus via PyNaCl), 48kHz stereo ↔ 16kHz mono PCM resample (soxr/ffmpeg), VAD (Silero) wrapper |
| `src/voice/turn_core.py` | `handle_voice_turn(transcript, user_id, ...) -> ProcessedTurn` — calls shared `_process_turn_core()` (from hermes-core refactor) then hands response to TTS. Also calls `HardStopHandler.check()` pre-Hermes + sets Redis flag. |
| `src/voice/cost.py` | Voice cost recording: wraps `CostTracker.record_cost` with `stt:*`/`tts:*`/`realtime:*` tags; Redis DB5 daily/monthly counters + hard-stop |
| `src/voice/metrics.py` | Prometheus metrics (mirrors `src/gmail/metrics.py` pattern): `voice_turn_latency_seconds`, `voice_stt_cost_usd`, `voice_tts_cost_usd`, `voice_hard_stop_total`, `voice_consent_violation_total`, `voice_injection_detected_total`, `voice_secrets_detected_total`, `voice_bargein_total`, `voice_connected`, `voice_provider_fallback_total` |
| `src/voice/session.py` | Per-session voice state (Redis DB3 `voice:session:{user_id}`), armed/disarmed, mode |
| `src/voice/dashboard_section.py` | `render_voice_section(state) -> EmbedField` — additive dashboard "VOICE" section for `src/life_kernel/dashboard.py` |
| `src/life_kernel/sensor_adapters/voice_sensor_adapter.py` | `VoiceSensorAdapter(BaseSensorAdapter)` — feeds voice metadata into the 30s awareness loop (NOT real-time turns) |
| `src/discord/_voice_client.py` | `VoiceRecvClient` connection + `StreamingSTTSink` + playback + barge-in (`vc.stop()`). PTT arm/disarm via `/voice` slash. |
| `src/discord/cmd_voice.py` | `/voice arm`, `/voice disarm`, `/voice join`, `/voice status`, `/voice-off` (kill switch) slash commands (Faiz-only) |
| `alembic/versions/p21_001_voice_stream.py` | Migration: `surveillance.voice_stream` table (raw audio, 24h TTL) + nullable `project_id` on `memory.episodes`. `down_revision = 'p20_001_life_kernel_schema'` |
| `secrets/voice-secrets.enc.yaml` | SOPS-encrypted voice provider keys (STT/TTS/realtime). Under existing `.sops.yaml` `secrets/.*\.yaml$` rule. |
| `tests/voice/test_voice_sanitize.py` | V-022 injection/secret scanner tests |
| `tests/voice/test_voice_hard_stop.py` | Spoken safe-word → Redis flag → neutral TTS ack (zero false-negative) |
| `tests/voice/test_voice_gate.py` | Fail-closed consent + HARD STOP + DND gating |
| `tests/voice/test_voice_turn_core.py` | Shared turn-core reuse (DRY safety) |
| `tests/voice/test_voice_cost.py` | STT/TTS cost tags + cap hard-stop |
| `tests/voice/test_voice_codec.py` | Opus ↔ PCM resample correctness |
| `tests/voice/test_voice_consent.py` | 5 scopes default OFF, revocation cascade |
| `tests/voice/test_voice_metrics.py` | Prometheus surface |
| `tests/voice/test_voice_sensor_adapter.py` | Sensor adapter Protocol conformance |

**MODIFIED files (P21-owned, additive-only — Wave 2, blocked on P20 pass for LOCKED ones):**
| File | Change | Wave | Risk |
|---|---|---|---|
| `src/discord/hermes_conversational.py:427-691` | Extract `_process_and_respond()` body into shared `_process_turn_core(content, author_id, channel_id, session_factory, shadow_pipeline, source_type="discord") -> ProcessedTurn`; text adapter calls it then `channel.send()`. **BLOCKED on P20 pass** (file is in P20 scope). | 3 (P21-003) | MEDIUM |
| `src/hermes/_memory_bridge.py:217-313` | Add `source_type` kwarg (default `"discord"`) to `store_conversation()`; dynamic `source`/`tags`. Additive. | 3 | LOW |
| `src/life_kernel/state.py` | Add `NotRequired` fields: `voice_listening_mode`, `voice_last_utterance`, `voice_last_command`, `current_project_id`. Additive, default-safe. | 2 | LOW |
| `src/life_kernel/dashboard.py` | Add `_voice_section(state)` rendered additively (after existing sections). | 2 | LOW |
| `src/life_kernel/sensors.py` | Register `VoiceSensorAdapter` at kernel startup (no Protocol change). | 2 | NONE |
| `src/memory/models.py` | Add nullable `project_id: Mapped[Optional[uuid.UUID]]` to `Episodes` (additive migration). | 2 | LOW |
| `src/surveillance/classification.py` | Add `voice_raw_audio` event type classified `CRITICAL` / `retention_class="critical_media"` / `encryption_profile="double_high"` (amendment A7). | 2 | LOW |
| `src/core/main.py` | Add `guinevere-voice` service startup wire AFTER kernel lifespan step. **BLOCKED on P20 pass.** | 4 (P21-008) | MEDIUM |
| `src/discord/_entrypoint.py` | Wire `_voice_client.py` init AFTER existing bot init. | 4 | MEDIUM |
| `src/discord/_command_registry.py` | Register `/voice*` commands. | 4 | LOW |
| `pyproject.toml` | Add deps: `discord-ext-voice-recv`, `PyNaCl`, `deepgram-sdk`, `cartesia`, `faster-whisper`, `piper-tts`, `silero-vad`, `openwakeword`. **BLOCKED on P20 pass** (align with P20 audit gates). | 2 | MEDIUM |
| `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md` | Add V-022 voice transcript vector section (single-owner edit, after plan approval). | 5 (P21-009) | MEDIUM |
| `docs/10-governance/17-ADR_Index_v1.0.md` | Add V-022 / voice ADR pointer (single-owner). | 5 | LOW |
| `docs/60-persona/63-DiscordUXSpec_v1.0.md` | Optional additive §X Voice Channel section (presence states, `/voice` commands). | 5 | LOW |
| `docs/setup-evidence/P21/README.md` | Update status/scope/progress (this phase). | now | NONE |

---

## Dependency Map

```text
P21-001 (STT/TTS provider abstraction) ──┐
P21-002 (Discord push-to-talk MVP) ──────┤ depends on 001 + _voice_client
P21-003 (Hermes voice turn pipeline) ────┤ depends on 001,002 + hermes_conversational refactor (BLOCKED P20)
P21-004 (transcript memory + retention/redaction) ──┤ depends on 003 + models.py additive (BLOCKED P20)
P21-005 (consent + HARD STOP + safe-word enforcement) ──┤ depends on 003,004
P21-006 (VAD/wake-word gated design) ────┤ depends on 005 (always-listening gating)
P21-007 (dashboard/status integration) ──┤ depends on 002,005 + dashboard.py additive
P21-008 (runtime deploy + smoke + rollback) ──┤ depends on ALL + main.py wire (BLOCKED P20)
P21-009 (audit + soak + final evidence) ──┤ depends on 008
```

**Parallelism (per AGENTS.md §2.4):**
- P21-001 and the NEW-file scaffolding (Wave 1) are `parallel` — independent new files, no shared writer.
- P21-002 depends on 001's STT/TTS Protocols → `sequential` after 001.
- P21-003 depends on the `hermes_conversational.py` refactor → `sequential`, and BLOCKED on P20 pass.
- P21-004, P21-005 can `parallel` after 003 (memory path vs consent/HARD-STOP path are independent surfaces).
- P21-006 `sequential` after 005 (needs consent gating).
- P21-007 `parallel` with 004/005/006 (additive dashboard only).
- P21-008 `sequential` after all (deploy).
- P21-009 `sequential` after 008 (soak).

---

## Collision Scan (summary — full matrix in `p21-dependency-collision-research.md` §5/§9)

- **0 HIGH risk.** No file is contested between two active implementers.
- **3 MEDIUM:** `src/core/main.py` (shared P20 lifespan — voice wire AFTER kernel), `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md` (V-022 single-owner edit), `pyproject.toml` (P21 single-owner, align with P20 audit).
- **9 LOW:** additive `NotRequired` state fields, additive dashboard section, additive `project_id` column, additive `source_type` kwarg, `voice-secrets.enc.yaml` new file, ADR index pointer, Discord UX optional section, `uv.lock` regen.
- **39 NONE:** all LOCKED P20 files P21 does NOT touch (heartbeat, hermes_brain, graph, adapter, safety_plugin, hard_stop_handler, safe_mode, etc.) + all NEW P21 files.
- **Rule:** P21 implementation on LOCKED files waits for P20 production-pass; NEW files are unblocked now (but not executed in this planning phase).

---

## Provider Shortlist + Benchmark Criteria

(From `p21-voice-provider-research.md` — official-doc cited, retrieved 2026-06-24.)

**Benchmark criteria (score each provider 0-3):** STT streaming latency p50/p95 · $/hr active listening · Indonesian (id-ID) WER · code-switching quality · TTS TTFA p50 · TTS Indonesian naturalness · TTS $/hr · E2E PTT latency · streaming-interruption latency · local-fallback feasibility · Hermes integration fit (all STT = text → same pipeline, no differentiation).

**Recommended primary (Option A — best-of-breed):**
- STT: **Deepgram Nova-3 Multilingual** ($0.0058/min streaming, sub-300ms, id-ID, Flux EOT ~260ms)
- TTS: **Cartesia Sonic 3.5** (~1 credit/char, 40-188ms TTFA, native id-ID, WebSocket streaming, Python SDK)
- VAD: **Silero VAD** (offline, free, accurate)
- Wake-word: **openWakeWord** (free, offline) — for P21-006 only
- Local fallback: **faster-whisper** + **Piper** (id-ID `news_tts` voice) — $0, no network

**Cost-sensitive alternative (Option B):** Google Chirp 3 STT + Google WaveNet id-ID TTS (60 min/mo + 1M chars/mo free).
**Simplest (Option C):** OpenAI gpt-realtime-whisper ($0.017/min) + OpenAI tts-1 (reuse 9Router key — no new secret).
**Best voice quality (Option D):** ElevenLabs Multilingual v2 + cloned consented Indonesian voice (expensive, voice-cloning consent required).
**Offline-only (Option E):** faster-whisper + Piper ($0).

**Realtime (NOT MVP):** OpenAI Realtime API gpt-realtime-mini (~$0.06-0.10/min) or Deepgram Voice Agent API ($4.50/hr) — for P21-006+ only, gated behind always-listening consent.

**Decision for MVP:** Option A primary + Option E fallback. Final selection at P21-001 execution after a live benchmark against Faiz's id+en code-switching audio.

---

## Push-to-Talk (PTT) Design

(From `p21-discord-voice-research.md` §4.)

Guinevere is a **remote VPS bot** — no local client keybind capture. PTT arming surfaces, ranked:
1. **Primary:** `/voice arm` / `/voice disarm` slash commands (authenticated, auditable, canonical UX).
2. **Secondary:** Tasker phone keybind → authenticated webhook `/voice/ptt` (hardware-like button).
3. **Tertiary:** Reaction toggle on a persistent voice-status embed.

**PTT data-flow:** Faiz speaks → Discord voice (Opus 48kHz stereo) → `VoiceRecvClient.listen(StreamingSTTSink)` → Opus decode → resample 48kHz stereo → 16kHz mono PCM → VAD endpointing → streaming STT → transcript → `HardStopHandler.check()` (pre-Hermes) → shared `_process_turn_core()` → response text → streaming TTS → resample → Opus encode → `VoiceClient.play()` → barge-in via `vc.stop()` on VAD during playback.

---

## Always-Listening Design (gated, NOT MVP)

(From `p21-consent-surveillance-research.md` §3, `p21-life-kernel-integration-research.md` §6.)

`voice.always_listening` defaults OFF. Enabled only after ALL 8 gates pass: explicit Faiz consent · visible indicator (presence "Listening 👂" + dashboard) · retention policy (raw audio ≤24h) · HARD STOP honored · audit trail · device auth · purpose-bound wake-word path · no-silent-reactivation (fail-closed consent cache). Even then, a **minimal "safe-word wake" mode** is recommended: mic active but audio discarded unless (VAD speech detected AND STT matches safe-word) — preserving the safety path while minimizing surveillance surface. P21-006 designs this; P21 does not enable it in MVP.

---

## STT / TTS / Streaming Pipeline

(From `p21-runtime-latency-deploy-research.md` §2, `p21-hermes-core-integration-research.md` §2.)

**Streaming path (target):** chunked PCM → streaming STT (partial transcripts) → VAD end-of-speech → final transcript → `HardStopHandler.check()` → distress + injection sanitize + memory recall → Hermes (non-streaming today; streaming variant is P21-003 Phase-2 optimization) → response text → streaming TTS (first audio chunk before full LLM response) → resample → Opus stream → Discord.

**Fallback (full-text-then-TTS):** if Hermes `send_message` stays non-streaming (it returns a full dict — `_session_adapter.py:235`), TTS starts after full LLM response. p50 ~2s, acceptable for MVP. Streaming-Hermes is a P21-003 enhancement, not an MVP blocker.

**Barge-in:** while TTS plays, VAD on incoming PCM; if Faiz speaks >X ms → `vc.stop()` + abort TTS stream.

---

## Discord Voice UX

(From `p21-discord-voice-research.md` §11, aligns with `63-DiscordUXSpec_v1.0.md`.)

- New voice channel `#guinevere-voice` under `👑 MOMMY'S THRONE`.
- New presence states: `Listening to Darling 👂` (armed), `Speaking to Darling 🎤` (TTS).
- Slash commands (Faiz-only): `/voice arm`, `/voice disarm`, `/voice join`, `/voice status`, `/voice-off` (kill switch).
- Bot permissions: `CONNECT`, `SPEAK` on `#guinevere-voice`.
- Consent: one-time `/consent category:voice action:on` before first arm.
- Audit: every arm/disarm/consent → `#audit-log`.
- Embed palette per DiscordUXSpec §4.1 (purple `#6B21A8` default, green `#16A34A` safe-mode).

---

## Hermes Core Wiring

(From `p21-hermes-core-integration-research.md` — the integration-not-sidecar decision.)

Refactor seam at `src/discord/hermes_conversational.py:427-691`: extract `_process_and_respond()` body into:

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

Text adapter: `_process_turn_core(...)` → `channel.send()`. Voice adapter: `_process_turn_core(content=transcript, source_type="voice")` → TTS. **Zero safety-hook duplication** — DRY. `store_conversation()` gains a `source_type` kwarg for provenance. `HermesSessionAdapter.send_message` reused as-is (non-streaming MVP; streaming variant later).

---

## life_kernel Wiring

(From `p21-life-kernel-integration-research.md`.)

- **HARD STOP flag (single source of truth):** voice checks Redis `life_kernel:hard_stop` pre-capture + between chunks; sets it on spoken safe-word (`HardStopHandler.check(transcript)` → `redis.set("life_kernel:hard_stop", "voice_safe_word")`); deletes it on spoken recovery. The 1s heartbeat (`heartbeat.py:273`) is the canonical detector — voice adds no new stop path.
- **VoiceSensorAdapter** (`src/life_kernel/sensor_adapters/voice_sensor_adapter.py`): implements `BaseSensorAdapter` Protocol; feeds metadata (listening_state, last_utterance_ts, utterance_count, sanitized snippet — NEVER raw audio) into the 30s awareness loop. **Reactive tier** (real-time turns) bypasses the graph; **reflective tier** (awareness) feeds it. Do NOT route turns through the 60s heartbeat.
- **Dashboard:** additive `voice_listening_mode`/`voice_last_utterance`/`voice_last_command` `NotRequired` fields in `LifeMindState`; new `_voice_section()` in `dashboard.py`.
- **Proactive TTS seam:** `HermesBrain.think()` can generate proactive voice (morning briefing) — gated by `VoiceGate.can_speak_proactive()` (HARD STOP clear + consent + DND resolved), serialized through a TTS queue.
- **Autonomy conflict:** always-listening is surveillance-class — MUST NOT auto-enable (unlike the kernel's autonomy-first principle). `VoiceGate` enforces consent-gating; the HARD-STOP path is the one exception (safe-word always detected).

---

## Memory / Transcript Model

(From `p21-memory-transcript-research.md`.)

- **Transcript** → `memory.episodes` (`episode_type='voice_turn'`, `raw_content`=redacted transcript, `source='voice'`, `embedding` via existing `EmbeddingService`, `do_not_recall` for safe-word/intimate/distress, `project_id` nullable for P19). **Provenance labels** (`source_type='voice'`, `source_trust='quarantined_5'`, confidence, storage_date) are stored in the existing `key_insights` JSONB column (no new column needed — `source_trust` is a label, not a relational field; matches how `source`/`tags` are already stored). P21-004 test asserts `key_insights.source_type='voice'` + `key_insights.source_trust='quarantined_5'`.
- **Raw audio** → discarded by default after STT. If retained (diagnostic only, consent `voice.storage.raw_audio` ON): stored in the **existing `surveillance.events.raw_payload`** (`event_type='voice_raw_audio'`, `LargeBinary`, `envelope-AES-256-GCM`, max 24h TTL, auto-purge). The `surveillance.voice_stream` table mentioned in the File Structure/P21-004 migration is an **optional future** dedicated raw-audio table; for MVP, raw audio reuses `surveillance.events` (consistency with V-013/V-014 camera/screenshot 24h policy + the A8 consent-cascade purge target). The P21-004 migration creates `surveillance.voice_stream` only if a dedicated table is chosen at implementation time; otherwise the migration is limited to the `project_id` column + the `voice_raw_audio` classification entry (A7). This resolves the round-2 surveillance-privacy raw-audio-table ambiguity.
- **Provenance labels:** `source_type='voice'`, `source_trust='quarantined_5'`, confidence from STT, storage_date, do_not_recall.
- **Audit:** voice safety events → `audit.audit_trail` (event_hash + previous_hash hash chain), minimal/non-punitive.
- **Consent revocation cascade:** revoke `voice.*` → mark voice episodes `deletion_state='pending_delete'`/`do_not_recall=true` → purge raw audio → record cascade in `consent.revocation_log.cascade_effects`.

**Storage decision table** (full in `p21-memory-transcript-research.md` §9): redacted transcript = Restricted/Long-Term Curated/envelope-AES-256-GCM; safe-word transcript = Critical/DNR/double-AES; raw audio (diagnostic) = Critical/Short Raw/24h/double-AES; safety event = audit_trail/1 year.

---

## Retention / Redaction Policy

(From `p21-memory-transcript-research.md` §3, `p21-consent-surveillance-research.md` §9.)

- Classification: raw audio = Critical; transcript = Restricted (Critical if safe-word/intimate); always-listening buffer = Critical (transient); proactive TTS log = Restricted.
- Retention: raw audio ≤24h (Short Raw, auto-delete unless incident hold); transcript raw ≤7 days then summarize/delete; safe-word/crisis transcript = minimal hash/event only, not full transcript.
- Redaction before memory write: secret-scanner (`src/surveillance/secret_scanner.py`) → drop secrets/hash-only; instruction-pattern quarantine (PromptInjection §7.3) → strip "ignore safe word"/"override ADR"/role-redefinition; intimate content minimization → double-encrypt + do_not_recall.
- Encryption: `envelope-AES-256-GCM` default; double for Critical.

---

## Consent Flow

(From `p21-consent-surveillance-research.md` §2, §4.)

5 voice consent scopes, all default OFF, revocable, auditable, non-transferable: `voice.capture.ptt` · `voice.always_listening` (MVP-blocked) · `voice.storage.transcript` · `voice.storage.raw_audio` · `voice.proactive_tts`. Reuse `/consent` slash command (new `voice` category). Write to `consent.consent_ledger`; invalidate Redis cache; audit to `#audit-log` immediately. Safety features (safe-word, distress, crisis) cannot be disabled via consent. Fail-closed consent cache (`src/surveillance/consent_gate.py` pattern).

---

## HARD STOP Behavior for Voice

(From `p21-consent-surveillance-research.md` §6, `p21-life-kernel-integration-research.md` §1.)

Sequence: STT transcript → `HardStopHandler.check(transcript)` (`src/core/services/hard_stop_handler.py:89`) → if True: `redis.set("life_kernel:hard_stop", "voice_safe_word")` → `SafeModeController`/persona Y0/neutral → `HardStopHandler.get_neutral_response()` → TTS neutral ack → minimal non-punitive audit to `audit_trail` + `#audit-log`. Kernel 1s heartbeat halts on the same flag. Zero false-negative tolerance; spoken safe-word override attempt = SEV0. Recovery: spoken "resume"/"aku sudah okay" → `HardStopHandler.check_recovery()` → `redis.delete("life_kernel:hard_stop")`.

**Redis write path (architecture G2 closure):** the voice service registers a `HardStopHandler.register_on_trigger()` callback (`src/core/services/hard_stop_handler.py:66`) that writes `life_kernel:hard_stop` to the **same Redis DB the heartbeat polls** (`src/life_kernel/heartbeat.py:273`; DB index documented in P21-008 per A4). This keeps `HardStopHandler.state` and the Redis flag synchronized through the handler's existing callback mechanism rather than an ad-hoc direct SET. The spoken-safe-word detection itself runs `HardStopHandler.check(transcript)` (pre-Hermes, pre-sanitization); the callback performs the Redis write + `SafeModeController` switch + audit.

---

## Safe-Word Detection in Audio/Transcript Path

First-class: `HardStopHandler.check()` runs on the **RAW transcript BEFORE sanitization** (SW-PI-008). Exact triggers (`hard stop`, `safe word`, `safeword`, `hentikan`, `berhenti`) + semantic patterns + Indonesian equivalents, all already in the handler. The STT robustness concern (audio crafted to transcribe as a safe-word bypass) is mitigated by the injection sanitizer's source-trust check (only Trust 1-3 may trigger safe word — SW-PI-002) — a spoken "safe word is revoked" is rejected unless via approved config/ADR path.

---

## Prompt-Injection Handling for Transcripts/Audio-Derived Content

(From `p21-security-secrets-research.md` §2.)

Voice transcript = Trust Level 6 (untrusted — could be read-aloud injection or played audio). Pipeline: classify (trust=6, source_type='voice') → sanitize (strip instruction patterns: "ignore safe word", "override ADR", "you are now", role-redefinition) → label `<untrusted source="voice" trust="6" confidence="…">` → quarantine to L7-L9 → NEVER reaches privileged L0-L6. Register V-022. Memory write must pass MEM-001..008. Secret-in-transcript: clipboard-equivalent scanner → drop/hash-only, never store. Audio-replay/pre-recorded injection = SEV0.

---

## Secrets / Env Model

(From `p21-security-secrets-research.md` §1.)

`secrets/voice-secrets.enc.yaml` (SOPS/age, under `.sops.yaml` `secrets/.*\.yaml$` rule): `voice.stt.openai_api_key`, `voice.stt.deepgram_api_key`, `voice.tts.openai_api_key`, `voice.tts.elevenlabs_api_key`, `voice.realtime.openai_api_key` (or reuse 9Router key for OpenAI audio — Option B, no new secret). `voice:` section with `enabled` flag, providers, `cost.daily_cap_usd`/`monthly_cap_usd`, `consent.always_listening:false`. Quarterly rotation + `SecretRotationLog` row. Never in repo/logs/MCP. `envelope-AES-256-GCM` for stored audio.

---

## Audit Trail Model

Voice safety events → `audit.audit_trail` (`event_type` ∈ `voice_safeword_spoken`, `voice_distress_detected`, `voice_injection_blocked`, `voice_secret_dropped`, `voice_consent_changed`, `voice_bargein`, `voice_provider_fallback`), `event_payload` minimal (episode_id, trigger_type, vector_id, content_hash — NO full transcript), `principal='guinevere:voice_pipeline'`, `event_hash` + `previous_hash` (hash chain). Per PersonaSafetyPolicy §16: minimal, non-punitive, encrypted if Critical. Discord `#audit-log` mirror per DiscordUXSpec.

---

## Cost / Latency Model

(From `p21-runtime-latency-deploy-research.md` §1, §9.)

Latency budget (PTT cloud): STT 300-600ms p50 · HARD STOP check <5ms · distress+sanitize+recall ~100-250ms · Hermes LLM 400-800ms (bottleneck) · TTS streaming first-audio 300-600ms · Opus encode+network ~60-170ms. **E2E p50 ~1.5-2.0s, p95 ~2.5-3.5s.** Bottleneck = LLM TTFT + non-streaming TTS.

Cost per turn (Option A): STT ~$0.001 + LLM ~$0.002-0.005 + TTS ~$0.003 = ~$0.006-0.009/turn. ~3,300-5,000 turns/mo within USD 30 cap. Voice sub-cap: daily $2, monthly $6. Always-listening realtime = $0.06-0.30/min continuous (cost-exfiltration risk — another reason not MVP).

`CostTracker.record_cost(model='stt:deepgram-nova'/'tts:cartesia-sonic'/'realtime:openai-realtime', ...)` feeds existing `cost:by_model:*` Redis keys; USD 30/mo cap auto-includes voice.

---

## Local Fallback Model

(From `p21-runtime-latency-deploy-research.md` §4.)

faster-whisper (CPU/GPU, MIT, id-ID) + Piper (CPU, id-ID `news_tts`, MIT) + Silero VAD + openWakeWord — all offline, $0. Triggers: provider outage · cost ceiling hit · sensitive content (consent `voice.storage.raw_audio` ON or intimate/medical/financial utterance → local STT so audio never leaves VPS) · 9Router unavailable (Ollama LLM fallback already exists). Chain: primary cloud → alt cloud → local. CPU cost feasible for single-user PTT bursts; heavy for always-listening (reinforces not-MVP).

---

## Deployment Model

(From `p21-runtime-latency-deploy-research.md` §3.)

**New systemd service `guinevere-voice`** (isolated, independent restart/rollback, scoped `MemoryLimit=512M`/`CPUQuota`). Mirrors `guinevere-mcp.service` pattern. Resource: ~1 CPU core under load, 150-350MB RAM. No new listen port (Discord gateway + outbound provider WS). Redis: key-prefix `voice:*` in DB3 (session) + DB5 (rate-limit) — no new DB, no collision with `life_kernel:hard_stop`. PostgreSQL: existing schemas via `guinevere_core` user. Coexists with `guinevere-core`/`guinevere-mcp`/`guinevere-scheduler`/`guinevere-surveillance` without port/DB collision.

---

## Rollback Model

Feature-flag `voice.enabled:false` in config → service starts but doesn't connect/capture. `/voice-off` kill switch (disconnect + disable + audit). HARD STOP halts voice (spoken/typed safe word → Redis flag). `systemctl stop guinevere-voice` (core unaffected). Config-gated rollout (no blue-green for single-user): flag-on → smoke → soak → flag-stays-on; rollback = flag-off + verify core unaffected.

---

## P20 / P19 / P22 Dependency Maps

(From `p21-dependency-collision-research.md`.)

- **P20:** P21 depends on life_kernel (heartbeat HARD-STOP flag, sensor adapter, dashboard, HermesBrain via adapter). P20 is in PRODUCTION PASS HOLD (soak). **Non-interference contract:** P21 changes to life_kernel are strictly additive (new `VoiceSensorAdapter`, new `NotRequired` state fields, new dashboard section); MUST NOT alter the 1s HARD-STOP loop semantics, the 6-interval schedule, the `life_kernel:hard_stop` key contract, `hermes_brain.py`, `graph.py`, or the Hermes conversational core. P21 implementation on LOCKED files BLOCKED until P20 pass; NEW files unblocked.
- **P19 (NOT STARTED):** voice turns carry nullable `project_id` (forward-compat seam) so P19 can partition memory later without a backfill. P21 code is namespace-agnostic (`project_id=None` default).
- **P22 (TBD):** P21 OWNS voice (not deferred to P22 — voice is internal infrastructure, not a SaaS integration). Future P22 integrations (calendar/notes) could be voice-invoked via Hermes tool-calling, but P21 does not pre-design those hooks.

---

## Implementation Waves (for later — NOT executed this phase)

Each wave below is a future implementation step with its own verification scaffold. **All held until P20 production-pass for LOCKED-file waves; Wave 1 (NEW files) unblocked but still not executed in this planning phase.**

### Wave P21-001: STT/TTS Provider Abstraction

**Files:** Create `src/voice/{__init__,config,types,exceptions,sanitize}.py`, `src/voice/stt/{base,openai_stt,deepgram_stt,faster_whisper_stt}.py`, `src/voice/tts/{base,cartesia_tts,openai_tts,piper_tts}.py`, `src/voice/audio_codec.py`, `src/voice/cost.py`, `src/voice/metrics.py`, `secrets/voice-secrets.enc.yaml`, `tests/voice/test_voice_{sanitize,codec,cost,metrics}.py`.
**Parallel:** parallel (independent new files).
**Scaffold:**
- Expected Files: as above.
- Forbidden Patterns: `# type: ignore`, `as any`, bare `except`, `except Exception:` (empty), hardcoded API keys, raw audio in logs.
- Required Commands: `python -m pytest tests/voice/ -v` → exit 0; `python -m mypy src/voice/` → exit 0 (if configured); `sops -d secrets/voice-secrets.enc.yaml` → decrypts (no plaintext in repo).
- Evidence: `docs/setup-evidence/P21/evidence/P21-001/verification.md`, `auditor-gate.md`.
- Hard Rejection: provider claims not backed by official docs; secrets in plaintext/repo; transcript sanitization skips HardStopHandler pre-check.

### Wave P21-002: Discord Push-to-Talk MVP

**Files:** Create `src/discord/_voice_client.py` (`VoiceRecvClient` + `StreamingSTTSink` + playback + barge-in), `src/discord/cmd_voice.py` (`/voice arm|disarm|join|status|off`), `src/voice/session.py`; modify `src/discord/_command_registry.py` (register), `pyproject.toml` (add `discord-ext-voice-recv`, `PyNaCl`).
**Depends on:** P21-001. **Parallel:** sequential after 001.
**Scaffold:**
- Expected Files: as above.
- Forbidden Patterns: capturing non-Faiz audio without consent gating; `vc.stop()` missing on barge-in; presence indicator not updated on arm/disarm.
- Required Commands: `python -m pytest tests/voice/test_voice_client.py -v` → exit 0; bot joins `#guinevere-voice`, arms, captures, STT, TTS, speaks back, barge-in cancels, `/voice-off` disconnects.
- Evidence: `docs/setup-evidence/P21/evidence/P21-002/verification.md`, `auditor-gate.md`.
- Hard Rejection: PTT without Faiz-only channel + consent; no kill switch.

### Wave P21-003: Hermes Voice Turn Pipeline

**Files:** Modify `src/discord/hermes_conversational.py:427-691` (extract `_process_turn_core`), `src/hermes/_memory_bridge.py:217-313` (`source_type` kwarg); create `src/voice/turn_core.py`.
**Depends on:** P21-001, P21-002. **Parallel:** sequential. **BLOCKED on P20 production-pass** (`hermes_conversational.py` is LOCKED).
**Scaffold:**
- Expected Files: as above.
- Forbidden Patterns: duplicated safety hooks in voice path (DRY violation); voice path bypasses distress/HARD STOP; `store_conversation` loses provenance.
- Required Commands: `python -m pytest tests/discord/test_hermes_conversational.py tests/voice/test_voice_turn_core.py -v` → exit 0 (existing text tests still pass — no regression); replay a checkpoint to confirm no state-shape change.
- Evidence: `docs/setup-evidence/P21/evidence/P21-003/verification.md`, `auditor-gate.md`.
- Hard Rejection: sidecar voice path that doesn't reuse the shared turn-core; any safety hook duplicated.

### Wave P21-004: Transcript Memory + Retention/Redaction

**Files:** Modify `src/memory/models.py` (nullable `project_id` on `Episodes`); create `alembic/versions/p21_001_voice_stream.py` (`surveillance.voice_stream` + `project_id`); `src/voice/memory_writer.py` (MEM-001..008 gate).
**Depends on:** P21-003. **Parallel:** parallel with P21-005. **BLOCKED on P20 pass** (`models.py` additive).
**Scaffold:**
- Expected Files: as above.
- Forbidden Patterns: transcript written without secret-scanner + injection-gate; raw audio stored by default; raw audio >24h; no `do_not_recall` on safe-word transcript; no hash-chain audit.
- Required Commands: `python -m pytest tests/voice/test_voice_memory.py -v` → exit 0; `alembic upgrade head` → exit 0; `alembic downgrade -1` + `alembic upgrade head` → exit 0 (idempotent).
- Evidence: `docs/setup-evidence/P21/evidence/P21-004/verification.md`, `auditor-gate.md`.
- Hard Rejection: transcripts enter memory without redaction/retention/injection-gate (hard-rejection rule).

### Wave P21-005: Consent + HARD STOP + Safe-Word Enforcement

**Files:** Create `src/voice/voice_gate.py`, `src/voice/safe_word_override.py`; modify `src/surveillance/consent_gate.py` (add voice scopes to `VALID_SURVEILLANCE_SCOPES` + always-listening 8-gate flag check inside `check_consent`), `src/discord/cmd_consent.py` (`voice` category + `PROTECTED_SCOPES` denylist), optionally `src/core/services/hard_stop_handler.py` (add `check_override_attempt()` + boundary-insensitive matching) — **NOTE: `hard_stop_handler.py` is LOCKED/P1-021; any edit needs P20-gate awareness + Oracle review per AGENTS.md §6; prefer implementing override-detection in `src/voice/safe_word_override.py` + the transcript sanitizer (SW-PI-002/003) to avoid touching the locked handler.**
**Depends on:** P21-003, P21-004. **Parallel:** parallel with P21-004.
**Scaffold:**
- Expected Files: as above.
- Forbidden Patterns: always-listening enabled without all 8 gates; consent cache not fail-closed; safe-word detected post-sanitization (must be pre); safe-word event punitive; safety features disable-able via consent; `cmd_consent.py` accepting a revoke on `safe_word`/`distress`/`crisis`/`hard_stop`.
- Required Commands: `python -m pytest tests/voice/test_voice_{gate,hard_stop,consent,safe_word_override}.py -v` → exit 0; red-team: (a) spoken safe-word → Redis flag set + neutral TTS + audit (zero false-negative); (b) spoken "safe word revoked/disabled" → rejected + SEV0; (c) boundary-embedded safe-word ("i want a hard stop now", "hardstopnow") → detected; (d) `/consent category:safe_word action:off` → refused with PROTECTED_SCOPES error; (e) always-listening refuses to start without all 8 gates.
- Evidence: `docs/setup-evidence/P21/evidence/P21-005/verification.md`, `auditor-gate.md`.
- Hard Rejection: always-listening without full gating; safe-word/HARD STOP not first-class in audio path; `cmd_consent.py` without PROTECTED_SCOPES denylist; no safe-word-override (SW-PI-003) rejection path.

> **Round-1 audit amendments (safety-consent + surveillance-privacy):** The original round-1 safety-consent audit returned FAIL on three implementation-enforcement gaps. Receiving-code-review verification confirmed: (1) `cmd_consent.py:103,128` accepts arbitrary category strings — VALID, closed by PROTECTED_SCOPES above; (2) `HardStopHandler` has no SW-PI-003 override detector — VALID, closed by `src/voice/safe_word_override.py` + sanitizer (prefer not touching locked handler); (3) exact-match boundary sensitivity — PARTIALLY valid (the `f" {trigger} "` bounded-substring + 5 semantic regex patterns DO catch most embedded phrases, but truly boundary-stuck tokens like "hardstopnow" need tokenized matching) — closed by the boundary-embedded red-team test (c) above. The safety *design* (HARD STOP pre-Hermes pre-sanitization, shared Redis flag, 8-gate always-listening, non-punitive audit, explicit recovery) is sound; these are enforcement items the wave must deliver.

### Wave P21-006: VAD/Wake-Word Gated Design

**Files:** Create `src/voice/vad.py` (Silero), `src/voice/wake_word.py` (openWakeWord); wire into `_voice_client.py` for always-listening path (gated behind `voice.always_listening` consent + all 8 gates).
**Depends on:** P21-005. **Parallel:** sequential.
**Scaffold:**
- Expected Files: as above.
- Forbidden Patterns: always-listening active without consent + visible indicator + retention + HARD STOP + audit; mic hot enough to capture everything (use safe-word-wake minimal mode).
- Required Commands: `python -m pytest tests/voice/test_voice_{vad,wake_word}.py -v` → exit 0; always-listening refuses to start without all gates; safe-word-wake mode discards non-safe-word audio.
- Evidence: `docs/setup-evidence/P21/evidence/P21-006/verification.md`, `auditor-gate.md`.
- Hard Rejection: always-listening enabled in MVP without gating.

### Wave P21-007: Dashboard/Status Integration

**Files:** Create `src/voice/dashboard_section.py`; modify `src/life_kernel/dashboard.py` (add `_voice_section`), `src/life_kernel/state.py` (`NotRequired` voice fields), `src/life_kernel/sensors.py` (register `VoiceSensorAdapter`); create `src/life_kernel/sensor_adapters/voice_sensor_adapter.py`.
**Depends on:** P21-002, P21-005. **Parallel:** parallel with P21-004/005/006 (additive only).
**Scaffold:**
- Expected Files: as above.
- Forbidden Patterns: raw transcript in sensor observation (metadata only); dashboard spammed (edit-not-spam); state fields not `NotRequired` (breaks checkpoint replay).
- Required Commands: `python -m pytest tests/life_kernel/ tests/voice/test_voice_sensor_adapter.py -v` → exit 0 (390 P20 tests still pass — no regression); replay existing checkpoint → new fields default absent.
- Evidence: `docs/setup-evidence/P21/evidence/P21-007/verification.md`, `auditor-gate.md`.
- Hard Rejection: breaks P20 soak (regression in `tests/life_kernel/`).

### Wave P21-008: Runtime Deploy + Smoke + Rollback

**Files:** Create `guinevere-voice.service` systemd unit; modify `src/core/main.py` (voice startup wire AFTER kernel lifespan); `pyproject.toml` deps.
**Depends on:** ALL. **Parallel:** sequential. **BLOCKED on P20 pass** (`main.py`, `pyproject.toml`).
**Scaffold:**
- Expected Files: as above.
- Forbidden Patterns: voice wire before kernel lifespan (startup-order collision); no feature flag; no kill switch; deploy without smoke.
- Required Commands: `systemctl daemon-reload && systemctl start guinevere-voice` → active; smoke (join, arm, capture, STT, Hermes, TTS, speak, barge-in, spoken safe-word → HARD STOP, `/voice-off`); `systemctl stop guinevere-voice` → core unaffected; `uv lock --check` → exit 0.
- Evidence: `docs/setup-evidence/P21/evidence/P21-008/verification.md`, `auditor-gate.md`.
- Hard Rejection: deploy/restart in this planning phase (planning-only); no rollback verification.

### Wave P21-009: Audit + Soak + Final Evidence

**Files:** Modify `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md` (V-022 section), `docs/10-governance/17-ADR_Index_v1.0.md` (pointer), `docs/60-persona/63-DiscordUXSpec_v1.0.md` (optional §X); final evidence.
**Depends on:** P21-008. **Parallel:** sequential.
**Scaffold:**
- Expected Files: doc updates + final evidence.
- Forbidden Patterns: V-022 section without official-doc grounding; ADR index pointer missing; soak <24h.
- Required Commands: 24h soak (mirrors LK-017); latency/cost/hard-stop metrics green; `python -m pytest tests/voice/ tests/life_kernel/ -v` → exit 0; full auditor wave PASS.
- Evidence: `docs/setup-evidence/P21/evidence/P21-009/verification.md`, `auditor-gate.md`, `final-p21-planning-report.md`.
- Hard Rejection: soak shows regression in P20 kernel; any hard-rejection criterion unmet.

---

## Audit Round-1 Amendments (consolidated from 8 round-1 auditors)

Round-1 verdicts: architecture **PASS (conditions)**, hermes-integration **NEEDS REVIEW**, runtime-latency **PASS (conditions)**, safety-consent **FAIL→NEEDS REVIEW** (re-characterized per receiving-code-review; see P21-005 amendment above), surveillance-privacy **PASS (conditions)**, security-secrets **PASS (conditions)**, discord-ux **NEEDS REVIEW**, evidence-docs **PASS**. No hard-rejection criterion is unmitigated after the amendments below. All findings are implementation-enforcement items folded into wave scaffolds; none invalidate the design.

| # | Finding (auditor) | Amendment | Wave |
|---|---|---|---|
| A1 | `_process_and_respond` returns `bool` + calls `channel.send` directly; `ProcessedTurn` not in source; refactor seam is design-only (architecture, hermes-integration) | P21-003 pre-condition: refactor MUST move distress/mood/recall/Hermes/cost/shadow/auto-store into a pure `_process_turn_core()` returning `ProcessedTurn`; `channel.send`/`_split_response` stay in the Discord-text adapter only; unit test proves `source_type="voice"` invokes without importing `discord.TextChannel`. `ProcessedTurn` defined in a location importable by both `src/discord/` and `src/voice/` (e.g. `src/voice/types.py` or a shared `src/core/turn_types.py`). | 003 |
| A2 | p50 <1.5s depends on streaming-Hermes not in current source (architecture) | P21-003 acceptance criterion: if streaming-Hermes unavailable, accept MVP p50 ~2s (non-streaming `send_message` + streaming TTS); file streaming-Hermes as a Phase-2 optimization, not a blocker. | 003 |
| A3 | `src/voice/turn_core.py` listed under Wave 1 but depends on LOCKED refactor (architecture) | `turn_core.py` is a **Wave 3** deliverable (P21-003), NOT Wave 1. Wave 1 parallelism is scoped to STT/TTS provider interfaces + audio codec + sanitize + cost + metrics only. | 001/003 |
| A4 | Voice Redis DB index for `life_kernel:hard_stop` access not specified (runtime-latency) | P21-008 scaffold: document the exact Redis DB index the voice service uses to read/write `life_kernel:hard_stop` (must match `heartbeat.py:273`'s connection DB); verify the voice Redis client connects to the same DB the kernel polls. | 008 |
| A5 | `guinevere-voice.service` `After=`/`Requires=` ordering vs core/mcp not specified (runtime-latency) | P21-008 scaffold: explicit systemd unit ordering — `After=guinevere-core.service` (voice starts after core); NO `Requires=guinevere-core.service` (so `systemctl stop guinevere-voice` is independent and a core restart doesn't force-pull voice down unless desired). | 008 |
| A6 | Prometheus scrape port/registry for voice metrics not specified (runtime-latency) | P21-007/008 scaffold: voice metrics reuse the existing Prometheus registry; if a separate HTTP server is needed, use a port ≠ 9191 (already used by `llm_metrics` `src/core/main.py:74`) OR push to the shared gateway. | 007/008 |
| A7 | `voice_raw_audio` event type missing from `src/surveillance/classification.py:80-167` (surveillance-privacy) | P21-004 scaffold: add `voice_raw_audio` event type classified `CRITICAL` / `retention_class="critical_media"` / `encryption_profile="double_high"` to `src/surveillance/classification.py` before raw-audio retention path executes. | 004 |
| A8 | Consent-revocation cascade documented but not implemented (surveillance-privacy) | P21-005 scaffold: implement concrete cascade function (`src/voice/consent_cascade.py` or in `voice_gate.py`) + test: revoke `voice.*` → mark voice episodes `deletion_state='pending_delete'`/`do_not_recall=true` → purge `surveillance.events` raw audio for `event_type='voice_raw_audio'` → record `consent.revocation_log.cascade_effects`. | 005 |
| A9 | `store_conversation()` hardcodes `source="discord_conversation"`; `source_type` param missing (surveillance-privacy, hermes-integration) | P21-003 deliverable: add `source_type: str = "discord"` kwarg to `HermesMemoryBridge.store_conversation()` (`src/hermes/_memory_bridge.py:217-313`); dynamic `source`/`tags`; test voice episodes carry `source="voice_conversation"` + `["voice","chat",...]`. | 003 |
| A10 | Faiz-only `#guinevere-voice` not enforced at channel-permission level (discord-ux) | P21-002 scaffold: explicit Discord channel permission overrides — deny `VIEW_CHANNEL`/`CONNECT` for `@everyone`; allow `VIEW_CHANNEL`/`CONNECT`/`SPEAK` for Faiz's role + bot role. Document in a setup runbook. | 002 |
| A11 | Barge-in VAD threshold unspecified (discord-ux) | P21-002 scaffold: document VAD barge-in threshold (recommended 300-500ms speech above threshold before `vc.stop()`). | 002 |
| A12 | discord.py / discord-ext-voice-recv version pin TBD (discord-ux) | P21-002 scaffold: pin versions in `pyproject.toml` (DAVE/E2EE compatibility). | 002 |
| A13 | `#guinevere-voice` creation not assigned to a wave (discord-ux) | P21-002 scaffold: clarify channel created manually (setup runbook) OR by bot on first `/voice join`; assign ownership. | 002 |
| A14 | Presence-state precedence undefined when voice + non-voice overlap (discord-ux) | P21-002 scaffold: define precedence (e.g. SEV0 > HARD STOP > voice-armed > loop-active > default). | 002 |
| A15 | Opus silence sentinel on TTS stop not mentioned (discord-ux) | P21-001 scaffold (`audio_codec.py`): send 5 frames of silence (`0xF8 0xFF 0xFE`) before stopping TTS send to avoid Opus interpolation artifacts. | 001 |
| A16 | V-022 section not yet in canonical `24-PromptInjection_ModelSafety_v1.0.md` (security-secrets, evidence-docs) | P21-009 hard acceptance criterion: V-022 section MUST be added (single-owner edit) citing the research file + provider sources; P21-009 not done until committed. | 009 |
| A17 | No live `SecretRotationLog` row yet (security-secrets) | First voice-key rotation (P21-001 or P21-008) MUST create a `SecretRotationLog` row (`src/memory/models.py:1046-1061`) + evidence per SecretsRotationRunbook §7. | 001/008 |
| A18 | DiscordUXSpec §7.6 presence states + §X voice section not yet added (discord-ux) | P21-009: make the DiscordUXSpec voice-section update MANDATORY (was "optional") before implementation completes. | 009 |

These amendments are binding for the future implementation waves. They do NOT change the planning-phase status (no implementation occurs now).

---

## Per-Step Verification Scaffold (summary)

Every wave's `verification.md` must follow the AGENTS.md §11 12-section schema: What Was Done · Files Changed · Validation Results · Evidence Artifacts · Doc-Sync Impact · Boundary Compliance · Rollback/Re-run Safety · Design Decisions/Caveats · Auditor Gate · Security Scan · Acceptance Criteria Mapping · Footer. Scaffold fields (Expected Files / Forbidden Patterns / Required Commands / Evidence Requirements / Hard Rejection Criteria) are per-wave above. Parent re-runs every scaffold command after sub-agent claims done (AGENTS.md §2.5 rule 5).

---

## Evidence Paths

| Wave | Verification | Auditor gate |
|---|---|---|
| P21-001..009 | `docs/setup-evidence/P21/evidence/P21-0XX/verification.md` | `docs/setup-evidence/P21/evidence/P21-0XX/auditor-gate.md` |
| Round-1 audits | `docs/setup-evidence/P21/evidence/audits/round-1/<dimension>.md` | — |
| Round-2 audits | `docs/setup-evidence/P21/evidence/audits/round-2/<dimension>.md` | — |
| Final | `docs/setup-evidence/P21/evidence/{p21-definition-verification,auditor-gate,final-p21-planning-report}.md` | — |

---

## Auditor Matrix (for the audit waves + future per-wave gates)

| Dimension | Scope | Key checks |
|---|---|---|
| Architecture | Integration-not-sidecar, DRY safety hooks, seam correctness, latency budget | Voice reuses `_process_turn_core`; no duplicated distress/HARD STOP; streaming-vs-fallback documented |
| Hermes integration | Turn-core refactor, `source_type` provenance, streaming status, cost tags | `_process_and_respond` extraction non-regressive; `store_conversation` provenance; `stt:*`/`tts:*` cost |
| Runtime/latency | `guinevere-voice` service isolation, resource ceiling, no Redis/port collision, rollback | New service; `MemoryLimit`; no DB collision; feature-flag + kill switch |
| Safety/consent | Spoken safe-word → Redis flag, always-listening gating, distress, F-01..F-15 | HARD STOP pre-sanitization; 8 gates; fail-closed cache; zero false-negative |
| Surveillance/privacy | Transcript classification, retention, raw-audio 24h, do_not_recall, audit hash chain | Critical classification; ≤24h raw; DNR on safe-word; hash-chain audit |
| Security/secrets | SOPS keys, V-022 injection, secret-in-transcript, provider ZDR, RBAC | No plaintext keys; V-022 registered; secret-scanner; no raw audio in MCP |
| Discord UX | Faiz-only channel, presence states, slash commands, embed palette, DND | `#guinevere-voice`; `/voice*`; presence `Listening 👂`/`Speaking 🎤`; DND respected |
| Evidence/docs | File-based outputs, official-doc citations, cross-refs, no inline-only | Every research/audit file exists + parent-read; citations to official docs |

---

## Hard Rejection Criteria (binary FAIL conditions)

1. Plan is sidecar-only without evaluating Hermes core integration → **FAIL**. (Mitigated: §Hermes Core Wiring mandates option (a) thin adapter; `p21-hermes-core-integration-research.md` argues it.)
2. Always-listening allowed without explicit consent + visible indicator + retention policy + HARD STOP + audit → **FAIL**. (Mitigated: §Always-Listening Design 8-gate checklist; P21-006 gated.)
3. Provider claims not backed by official-doc research → **FAIL**. (Mitigated: `p21-voice-provider-research.md` 56 cited sources; `p21-security-secrets-research.md` §4.2 official provider privacy pages; `p21-runtime-latency-deploy-research.md` §9 official pricing.)
4. Secrets/token handling vague → **FAIL**. (Mitigated: §Secrets/Env Model names exact env vars, SOPS path, rotation, encryption profile.)
5. Transcripts can enter memory without redaction/retention policy → **FAIL**. (Mitigated: §Memory/Transcript Model + §Retention/Redaction + P21-004 scaffold MEM-001..008 gate.)
6. Safe-word/HARD STOP not first-class in audio path → **FAIL**. (Mitigated: §HARD STOP Behavior for Voice + §Safe-Word Detection; `HardStopHandler.check()` pre-Hermes pre-sanitization.)
7. Sub-agent output inline-only without file → **FAIL**. (Mitigated: 32 files on disk; 2 research sub-agents (security-secrets, runtime-latency-deploy) failed with no file (process-exit orphan + kimi-k2.7-code stall) and their inline-only/absent outputs were REJECTED; parent-authored replacement files with documented provenance were accepted and parent-read. The 7 successful research sub-agents + 16 audit sub-agents produced file-based output. So no accepted deliverable is inline-only — the failed outputs were rejected, not accepted.)
8. Edits runtime code, deploys, or restarts production in this phase → **FAIL**. (Mitigated: this is planning-only; waves are future, gated on P20 pass.)

---

## Self-Review (writing-plans skill)

- **Spec coverage:** Every P21 objective item maps to a wave — provider shortlist (P21-001), PTT (P21-002), Hermes turn pipeline (P21-003), transcript memory/retention (P21-004), consent+HARD STOP+safe-word (P21-005), VAD/wake-word (P21-006), dashboard (P21-007), deploy+smoke+rollback (P21-008), audit+soak (P21-009). ✅
- **Placeholder scan:** No "TBD"/"implement later"/"add appropriate error handling". Wave scaffolds have concrete Expected Files, Forbidden Patterns (regex/grep), Required Commands, Hard Rejection. (Wave *execution* TDD steps are intentionally deferred to execution time per the planning-only constraint — they are not placeholders, they are out-of-scope-for-this-phase.) ✅
- **Type consistency:** `ProcessedTurn` (defined in hermes-core refactor) used by `turn_core.py`; `STTProvider`/`TTSProvider` Protocols used by all provider impls; `VoiceGate.can_listen()`/`can_speak_proactive()` used by `_voice_client.py` + heartbeat proactive path; `voice:*` Redis key-prefix consistent; `life_kernel:hard_stop` key name consistent across all waves. ✅

---

## Final Allowed Status

**P21 VOICE INTERFACE DEFINITION COMPLETE — IMPLEMENTATION HOLD UNTIL P20 CONTINUATION PASS.**

This plan is the definition. Implementation waves P21-001..009 execute later, gated on the P20 Living Autonomy Kernel production-pass (LK-017 soak → PRODUCTION PASS). Wave 1 (NEW files) is technically unblocked but is NOT executed in this planning phase per the P21 objective.
