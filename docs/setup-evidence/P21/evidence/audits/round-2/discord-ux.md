# P21 Voice Interface — Round 2 Audit: Discord UX

**Dimension:** Discord UX Auditor  
**Phase:** P21 Voice Interface — Planning (Round 2)  
**Date:** 2026-06-24  
**Output Path:** `docs/setup-evidence/P21/evidence/audits/round-2/discord-ux.md`  
**Verdict:** PASS

---

## 1. Scope & Method

Audited the amended P21 voice plan (`p21-voice-interface-enterprise-plan.md`) to verify every Round-1 Discord UX finding (A10-A18) is now closed, and re-checked the Discord UX design against the enterprise plan, `p21-discord-voice-research.md`, and canonical source-of-truth documents.

**Artifacts reviewed:**
- `docs/setup-evidence/P21/plan/p21-voice-interface-enterprise-plan.md`
- `docs/setup-evidence/P21/evidence/audits/round-1/discord-ux.md`
- `docs/setup-evidence/P21/research/p21-discord-voice-research.md`
- `docs/60-persona/63-DiscordUXSpec_v1.0.md`
- `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md`
- `src/core/services/hard_stop_handler.py`
- `src/discord/hermes_conversational.py`

**P21 hard-rejection criteria check:**
| # | Criterion | Status |
|---|---|---|
| 1 | Sidecar-only without Hermes core integration | PASS (uses shared `_process_turn_core`) |
| 2 | Always-listening without consent + indicator + retention + HARD STOP + audit | PASS (always-listening NOT MVP; 8 gates; P21-006) |
| 3 | Provider claims not backed by official docs | PASS (research cites discord.py docs, Discord dev docs, PyPI) |
| 4 | Secrets/token handling vague | PASS (SOPS/age, quarterly rotation, no plaintext) |
| 5 | Transcripts enter memory without redaction/retention | PASS (MEM-001..008 gate, redaction, ≤24h raw audio) |
| 6 | Safe-word/HARD STOP not first-class in audio path | PASS (`HardStopHandler.check()` pre-Hermes, Redis flag) |
| 7 | Sub-agent output inline-only without file | PASS (all deliverables file-based) |
| 8 | Runtime code edits / deploy / restart in this phase | PASS (planning-only, no implementation) |

---

## 2. Round-1 Finding Closure

| Round-1 Finding | Amended Plan Location | Closure | Rationale |
|---|---|---|---|
| **A10** — Faiz-only `#guinevere-voice` channel permission overrides not specified | `p21-voice-interface-enterprise-plan.md` line 471 | **CLOSED** | Amendment now specifies exact overrides: deny `VIEW_CHANNEL`/`CONNECT` for `@everyone`; allow `VIEW_CHANNEL`/`CONNECT`/`SPEAK` for Faiz's role + bot role. Documented in setup runbook. |
| **A11** — VAD barge-in threshold unspecified | `p21-voice-interface-enterprise-plan.md` line 472 | **CLOSED** | Amendment documents recommended 300–500 ms speech above threshold before `vc.stop()`. |
| **A12** — `discord.py` / `discord-ext-voice-recv` version pin TBD | `p21-voice-interface-enterprise-plan.md` line 473 | **CLOSED** | Amendment requires pinning versions in `pyproject.toml`, with explicit DAVE/E2EE compatibility rationale. |
| **A13** — `#guinevere-voice` creation not assigned to a wave | `p21-voice-interface-enterprise-plan.md` line 474 | **CLOSED** | Amendment assigns ownership: created manually via setup runbook OR by bot on first `/voice join`; ownership explicit. |
| **A14** — Presence-state precedence when voice + non-voice overlap undefined | `p21-voice-interface-enterprise-plan.md` line 475 | **CLOSED** | Amendment defines precedence order: `SEV0 > HARD STOP > voice-armed > loop-active > default`. |
| **A15** — Opus silence sentinel on TTS stop not mentioned | `p21-voice-interface-enterprise-plan.md` line 476 | **CLOSED** | Amendment requires sending 5 frames of silence (`0xF8 0xFF 0xFE`) before stopping TTS, implemented in `src/voice/audio_codec.py`. |
| **A18** — DiscordUXSpec §7.6 presence states + §X voice section treated as optional | `p21-voice-interface-enterprise-plan.md` line 479 | **CLOSED** | Amendment makes the DiscordUXSpec voice section update MANDATORY in P21-009 (was "optional"). |

*Note: A16–A17 are outside the Discord UX dimension but were also reviewed for consistency; they are closed in their respective dimensions (V-022 section now mandatory; `SecretRotationLog` required).*

---

## 3. Re-Verification of Discord UX Design

### 3.1 Push-to-Talk (PTT) Design

**Verdict:** PASS

Amended plan maintains the same PTT surface, ranked correctly for a remote VPS bot (`p21-voice-interface-enterprise-plan.md` lines 156-166):
1. Primary: `/voice arm` / `/voice disarm` slash commands.
2. Secondary: Tasker/external webhook `/voice/ptt`.
3. Tertiary: Reaction toggle on a persistent voice-status embed.

Slash commands are authenticated, Faiz-only, and produce an audit trail, consistent with `63-DiscordUXSpec_v1.0.md` §2 command style.

**Citations:**
- `p21-voice-interface-enterprise-plan.md` lines 156-166
- `p21-discord-voice-research.md` lines 164-191

---

### 3.2 Voice Channel Faiz-Only Enforcement

**Verdict:** PASS (with A10 amendment)

The amended plan explicitly documents the Discord permission overrides required to keep `#guinevere-voice` Faiz-only (A10):
- Deny `VIEW_CHANNEL`/`CONNECT` for `@everyone`.
- Allow `VIEW_CHANNEL`/`CONNECT`/`SPEAK` for Faiz's role.
- Allow `CONNECT`/`SPEAK` for the bot role.

This is binding on P21-002 and will be recorded in a setup runbook. It is stronger than the original round-1 design that relied on the server being "private."

**Citations:**
- `p21-voice-interface-enterprise-plan.md` lines 30, 193-194, 471
- `p21-discord-voice-research.md` lines 379-388
- `63-DiscordUXSpec_v1.0.md` §1.3, §8.2

---

### 3.3 Presence States `Listening 👂` / `Speaking 🎤`

**Verdict:** PASS

The plan proposes two new presence states (`p21-voice-interface-enterprise-plan.md` lines 194-195):
- Voice armed / listening: `Listening to Darling 👂`
- Voice speaking / playing TTS: `Speaking to Darling 🎤`

Round-1 correctly noted `DiscordUXSpec_v1.0.md` §7.6 did not yet contain these states. Amendment A18 makes adding them **mandatory** in P21-009, and A14 defines precedence when voice and non-voice states overlap (`SEV0 > HARD STOP > voice-armed > loop-active > default`).

**Citations:**
- `p21-voice-interface-enterprise-plan.md` lines 194-195, 475, 479
- `p21-discord-voice-research.md` lines 391-398
- `63-DiscordUXSpec_v1.0.md` §7.6

---

### 3.4 Slash Commands Are Faiz-Only

**Verdict:** PASS

`/voice arm`, `/voice disarm`, `/voice join`, `/voice status`, `/voice-off` are documented as Faiz-only and placed in `src/discord/cmd_voice.py` (`p21-voice-interface-enterprise-plan.md` lines 195, 422-423). This aligns with `63-DiscordUXSpec_v1.0.md` §2 header: "Only Faiz can execute commands."

**Citations:**
- `p21-voice-interface-enterprise-plan.md` lines 195, 422-423
- `p21-discord-voice-research.md` lines 399-410
- `63-DiscordUXSpec_v1.0.md` §2 header

---

### 3.5 Embed Palette Consistency

**Verdict:** PASS

The plan explicitly follows `DiscordUXSpec` §4.1 (`p21-voice-interface-enterprise-plan.md` line 199):
- Default purple `#6B21A8`
- Safe-mode green `#16A34A`

These match the canonical palette exactly.

**Citations:**
- `p21-voice-interface-enterprise-plan.md` line 199
- `63-DiscordUXSpec_v1.0.md` §4.1

---

### 3.6 DND (00:00-07:00 WIB) Respected for Proactive Voice

**Verdict:** PASS

Proactive TTS is gated by `VoiceGate.can_speak_proactive()`, which checks the DND window. DND window is defined in `63-DiscordUXSpec_v1.0.md` §6.3 as 00:00-07:00 WIB. The plan notes proactive voice (e.g., morning briefing) is gated by this check (`p21-voice-interface-enterprise-plan.md` lines 231-232).

**Citations:**
- `p21-voice-interface-enterprise-plan.md` lines 189, 231-232
- `63-DiscordUXSpec_v1.0.md` §6.3

---

### 3.7 `/consent` Reused with Voice Category

**Verdict:** PASS

The plan reuses the existing `/consent` slash command with a new `voice` category, consistent with `63-DiscordUXSpec_v1.0.md` §2.6. It lists five voice-specific consent scopes (`voice.capture.ptt`, `voice.always_listening`, `voice.storage.transcript`, `voice.storage.raw_audio`, `voice.proactive_tts`), all default OFF and revocable (`p21-voice-interface-enterprise-plan.md` lines 261-266).

**Citations:**
- `p21-voice-interface-enterprise-plan.md` lines 261-266
- `63-DiscordUXSpec_v1.0.md` §2.6

---

### 3.8 Every Arm/Disarm/Consent Event Audited to `#audit-log`

**Verdict:** PASS

The plan states: "every arm/disarm/consent event is written to `#audit-log`" (`p21-voice-interface-enterprise-plan.md` line 198). The Audit Trail Model (lines 299-301) further specifies event types and hash-chain requirements, consistent with `63-DiscordUXSpec_v1.0.md` §8.3.

**Citations:**
- `p21-voice-interface-enterprise-plan.md` lines 197-199, 299-301
- `63-DiscordUXSpec_v1.0.md` §8.3

---

### 3.9 Barge-In via `vc.stop()`

**Verdict:** PASS

The plan uses `VoiceClient.stop()` for barge-in, which is the correct discord.py API for cancelling the current `AudioSource`. Amendment A11 now documents the VAD threshold (300–500 ms). The flow remains: VAD detects Faiz speaking during TTS → `vc.stop()` → abort TTS stream → switch to listening.

**Citations:**
- `p21-voice-interface-enterprise-plan.md` lines 181-186, 472
- `p21-discord-voice-research.md` §7.1-7.3

---

### 3.10 Bot Permissions `CONNECT`, `SPEAK` Documented

**Verdict:** PASS

The plan documents the bot needs `CONNECT` and `SPEAK` permissions on `#guinevere-voice` (`p21-voice-interface-enterprise-plan.md` line 196), with optional `PRIORITY_SPEAKER` and `USE_VOICE_ACTIVATION` noted in research (`p21-discord-voice-research.md` §9).

**Citations:**
- `p21-voice-interface-enterprise-plan.md` line 196
- `p21-discord-voice-research.md` §9

---

### 3.11 Opus 48 kHz Stereo ↔ 16 kHz Mono PCM Resample

**Verdict:** PASS

The plan and research correctly describe the pipeline:
- Discord voice is Opus 48 kHz stereo.
- STT providers typically require 16 kHz mono PCM.
- Resampling/downmixing is required before STT; TTS output is resampled back to 48 kHz stereo for Discord.
- `src/voice/audio_codec.py` is specified to handle Opus decode/encode and resampling (soxr/ffmpeg). (`p21-voice-interface-enterprise-plan.md` lines 55, 165, 422-423)

**Citations:**
- `p21-voice-interface-enterprise-plan.md` lines 55, 165, 422-423
- `p21-discord-voice-research.md` §2.2, §3.2, §6.2

---

### 3.12 `discord-ext-voice-recv` as Receive Library

**Verdict:** PASS

The research file justifies `discord-ext-voice-recv` as the de facto standard for receiving audio with discord.py, providing `VoiceRecvClient`, `AudioSink`, and `wants_opus()`/`write()` API. The plan adopts this and amendment A12 requires version pinning in `pyproject.toml`.

**Citations:**
- `p21-voice-interface-enterprise-plan.md` lines 9, 62, 86-88, 181-186, 473
- `p21-discord-voice-research.md` §2.3, §6.1

---

### 3.13 Opus Silence Sentinel

**Verdict:** PASS (with A15 amendment)

Amendment A15 explicitly requires sending 5 frames of silence (`0xF8 0xFF 0xFE`) before stopping TTS send to avoid Opus interpolation artifacts. The amendment places this in `src/voice/audio_codec.py` (P21-001), which is the correct location for Opus encode utilities. The exact call site within `_voice_client.py` playback will be resolved during implementation.

**Citations:**
- `p21-voice-interface-enterprise-plan.md` line 476
- `p21-discord-voice-research.md` §3.2

---

## 4. New-Gap Check (Introduced or Previously Missed)

| Area | Finding | Severity | Status |
|---|---|---|---|
| Voice channel ID wiring | Research §10 suggests a `GUINEVERE_VOICE_CHANNEL_ID` constant, but the plan does not specify where it lives or how it is populated. | Low | **Non-blocking** — implementation detail for P21-002/P21-008. |
| Redis DB for `life_kernel:hard_stop` | Plan states voice uses DB3/DB5 but does not document which DB holds `life_kernel:hard_stop`; amendment A4 (runtime-latency) covers this in P21-008. | Low | **Non-blocking** — tracked under runtime-latency dimension (A4). |
| DiscordUXSpec §8.2 permission matrix | Current `DiscordUXSpec_v1.0.md` §8.2 does not include `#guinevere-voice`; amendment A18 mandates the spec update in P21-009. | Low | **Non-blocking** — amendment makes it mandatory. |

No blocking new gaps were identified for the Discord UX dimension.

---

## 5. Conclusion

All Round-1 Discord UX findings (A10-A15, A18) are now closed by binding amendments in the enterprise plan. The Discord UX design remains fundamentally sound: PTT via slash commands is the right choice for a remote VPS bot, the channel placement and Faiz-only permission model align with the Discord UX spec, presence states and precedence are now defined, and all safety/consent/audit surfaces are present.

The amended plan satisfies the P21 hard-rejection criteria and introduces no new blocking Discord UX gaps.

**Overall Verdict: PASS**

---

## 6. Round-1 Finding Closure Table (Summary)

| A# | Finding | Wave | Status |
|---|---|---|---|
| A10 | Faiz-only `#guinevere-voice` channel permission overrides not specified | P21-002 | **CLOSED** |
| A11 | VAD barge-in threshold unspecified | P21-002 | **CLOSED** |
| A12 | `discord.py` / `discord-ext-voice-recv` version pin TBD | P21-002 | **CLOSED** |
| A13 | `#guinevere-voice` creation not assigned to a wave | P21-002 | **CLOSED** |
| A14 | Presence-state precedence when voice + non-voice overlap undefined | P21-002 | **CLOSED** |
| A15 | Opus silence sentinel on TTS stop not mentioned | P21-001 | **CLOSED** |
| A18 | DiscordUXSpec voice section treated as optional | P21-009 | **CLOSED** |

---

*End of report.*
