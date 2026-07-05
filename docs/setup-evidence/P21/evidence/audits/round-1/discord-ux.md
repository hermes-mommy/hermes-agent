# P21 Voice Interface — Round 1 Audit: Discord UX

**Dimension:** Discord UX Auditor  
**Phase:** P21 Voice Interface — Planning (Round 1)  
**Date:** 2026-06-24  
**Output Path:** `docs/setup-evidence/P21/evidence/audits/round-1/discord-ux.md`  
**Verdict:** NEEDs REVIEW

---

## 1. Scope & Method

Audited the Discord UX design of the P21 voice interface against the enterprise plan, discord.py documentation, and canonical Guinevere source-of-truth documents.

**Artifacts reviewed:**
- `docs/setup-evidence/P21/plan/p21-voice-interface-enterprise-plan.md`
- `docs/setup-evidence/P21/research/p21-discord-voice-research.md`
- `docs/60-persona/63-DiscordUXSpec_v1.0.md`
- `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md`
- `src/core/services/hard_stop_handler.py`
- `src/discord/hermes_conversational.py`

**Hard-rejection criteria (P21):** None triggered.

---

## 2. Findings by Check

### 2.1 Push-to-Talk (PTT) design for remote VPS bot

**Verdict:** PASS

The plan correctly identifies that a remote VPS bot cannot capture local keybinds. The PTT surface is ranked as:
1. Primary: `/voice arm` / `/voice disarm` slash commands.
2. Secondary: Tasker/external webhook `/voice/ptt`.
3. Tertiary: Reaction toggle on a persistent voice-status embed.

This is appropriate and directly supported by the research file (`p21-discord-voice-research.md` §4.1-4.3). Slash commands are authenticated, permission-scoped, and produce an audit trail, aligning with the existing Guinevere command model (`63-DiscordUXSpec_v1.0.md` §2).

**Citations:**
- `docs/setup-evidence/P21/plan/p21-voice-interface-enterprise-plan.md` lines 156-166
- `docs/setup-evidence/P21/research/p21-discord-voice-research.md` lines 164-191

---

### 2.2 Voice channel Faiz-only under `👑 MOMMY'S THRONE`

**Verdict:** NEEDS REVIEW

The plan and research both place `#guinevere-voice` under the `👑 MOMMY'S THRONE` category, consistent with the existing server structure (`63-DiscordUXSpec_v1.0.md` §1.3). However, the **mechanism by which the channel remains Faiz-only is not explicitly documented**. The plan states "Single-user: Faiz-only voice channel" (`p21-voice-interface-enterprise-plan.md` line 30) and "non-Faiz audio capture disabled by default" (line 30), but it does not specify the Discord permission overrides required to enforce this at the channel level.

Required detail missing:
- Deny `VIEW_CHANNEL`/`CONNECT` for `@everyone`.
- Allow `VIEW_CHANNEL`/`CONNECT`/`SPEAK` for Faiz's role.
- Allow `CONNECT`/`SPEAK` for the bot role.

Without these explicit permission rules, a future implementer might rely on the server being "private" (as described in `63-DiscordUXSpec_v1.0.md` §1.1) rather than on explicit channel-level enforcement. The existing DiscordUXSpec §8.2 only lists text channel permissions and does not include `#guinevere-voice`.

**Citations:**
- `docs/setup-evidence/P21/plan/p21-voice-interface-enterprise-plan.md` line 30, 193-194
- `docs/setup-evidence/P21/research/p21-discord-voice-research.md` lines 379-388
- `docs/60-persona/63-DiscordUXSpec_v1.0.md` §1.3, §8.2

---

### 2.3 Presence states `Listening 👂` / `Speaking 🎤`

**Verdict:** PASS with caveat

The plan proposes two new presence states:
- Voice armed / listening: `Listening to Darling 👂`
- Voice speaking / playing TTS: `Speaking to Darling 🎤`

These are consistent with the existing presence framework in `63-DiscordUXSpec_v1.0.md` §1.2 / §7.6. The research file explicitly references adding them to the table in §11.2.

Caveat: The current `DiscordUXSpec_v1.0.md` §7.6 does not yet contain these states. The plan acknowledges this as an optional update in Wave P21-009 (`p21-voice-interface-enterprise-plan.md` line 90). This is acceptable for a planning-phase audit, but the spec update must be mandatory, not optional, before implementation.

**Citations:**
- `docs/setup-evidence/P21/plan/p21-voice-interface-enterprise-plan.md` lines 189-194
- `docs/setup-evidence/P21/research/p21-discord-voice-research.md` lines 391-398
- `docs/60-persona/63-DiscordUXSpec_v1.0.md` §1.2, §7.6

---

### 2.4 Slash commands are Faiz-only

**Verdict:** PASS

The plan lists `/voice arm`, `/voice disarm`, `/voice join`, `/voice status`, `/voice-off` as Faiz-only and places their implementation in `src/discord/cmd_voice.py`. This aligns with the existing permission model where all slash commands are restricted to Faiz (`63-DiscordUXSpec_v1.0.md` §2 header: "Only Faiz can execute commands").

**Citations:**
- `docs/setup-evidence/P21/plan/p21-voice-interface-enterprise-plan.md` lines 195, 422-423
- `docs/setup-evidence/P21/research/p21-discord-voice-research.md` lines 399-410

---

### 2.5 Embed palette consistency

**Verdict:** PASS

The plan explicitly states the embed palette follows `DiscordUXSpec` §4.1:
- Default purple `#6B21A8`
- Safe-mode green `#16A34A`

These match the canonical palette in `63-DiscordUXSpec_v1.0.md` §4.1 exactly.

**Citations:**
- `docs/setup-evidence/P21/plan/p21-voice-interface-enterprise-plan.md` line 199
- `docs/60-persona/63-DiscordUXSpec_v1.0.md` §4.1

---

### 2.6 DND (00:00-07:00 WIB) respected for proactive voice

**Verdict:** PASS

The plan states that proactive TTS is gated by `VoiceGate.can_speak_proactive()`, which checks the DND window. The DND window is defined in `63-DiscordUXSpec_v1.0.md` §6.3 as 00:00-07:00 WIB. This is consistent.

Caveat: The UX of "proactive voice" is only lightly sketched (morning briefing via voice). The actual user-facing behavior — e.g., whether the bot auto-joins the voice channel during DND if already armed — should be clarified before implementation.

**Citations:**
- `docs/setup-evidence/P21/plan/p21-voice-interface-enterprise-plan.md` lines 189, 231-232
- `docs/60-persona/63-DiscordUXSpec_v1.0.md` §6.3

---

### 2.7 `/consent` reused with voice category

**Verdict:** PASS

The plan reuses the existing `/consent` slash command with a new `voice` category, which is consistent with the canonical consent UX in `63-DiscordUXSpec_v1.0.md` §2.6 (`/consent category action`). The plan also lists five voice-specific consent scopes (`voice.capture.ptt`, `voice.always_listening`, `voice.storage.transcript`, `voice.storage.raw_audio`, `voice.proactive_tts`).

**Citations:**
- `docs/setup-evidence/P21/plan/p21-voice-interface-enterprise-plan.md` lines 261-266
- `docs/60-persona/63-DiscordUXSpec_v1.0.md` §2.6

---

### 2.8 Every arm/disarm/consent event audited to `#audit-log`

**Verdict:** PASS

The plan explicitly states: "every arm/disarm/consent event is written to `#audit-log`" (`p21-voice-interface-enterprise-plan.md` line 198). The research file reinforces this, referencing `63-DiscordUXSpec_v1.0.md` §8.3. The plan's Audit Trail Model (lines 299-301) further specifies the event types and hash-chain requirements.

**Citations:**
- `docs/setup-evidence/P21/plan/p21-voice-interface-enterprise-plan.md` lines 197-199, 299-301
- `docs/setup-evidence/P21/research/p21-discord-voice-research.md` line 219
- `docs/60-persona/63-DiscordUXSpec_v1.0.md` §8.3

---

### 2.9 Barge-in via `vc.stop()`

**Verdict:** PASS

The plan and research both use `VoiceClient.stop()` for barge-in, which is the correct discord.py API for cancelling the current `AudioSource`. The flow is: VAD detects Faiz speaking during TTS → `vc.stop()` → abort TTS stream → switch to listening.

**Citations:**
- `docs/setup-evidence/P21/plan/p21-voice-interface-enterprise-plan.md` lines 181-186
- `docs/setup-evidence/P21/research/p21-discord-voice-research.md` §7.1-7.3

---

### 2.10 Bot permissions `CONNECT`, `SPEAK` documented

**Verdict:** PASS

The plan explicitly documents the bot needs `CONNECT` and `SPEAK` permissions on `#guinevere-voice`. The research file §9 lists these and also mentions optional `PRIORITY_SPEAKER` and `USE_VOICE_ACTIVATION`.

**Citations:**
- `docs/setup-evidence/P21/plan/p21-voice-interface-enterprise-plan.md` line 196
- `docs/setup-evidence/P21/research/p21-discord-voice-research.md` §9

---

### 2.11 Opus 48kHz stereo ↔ 16kHz mono PCM resample

**Verdict:** PASS

The plan and research correctly describe the audio pipeline:
- Discord voice is Opus 48 kHz stereo (`p21-discord-voice-research.md` §3.2).
- Most STT providers require 16 kHz mono PCM.
- Resampling and downmixing are required before STT; TTS output is resampled back to 48 kHz stereo for Discord.
- The plan specifies `src/voice/audio_codec.py` to handle Opus decode/encode and resampling (soxr/ffmpeg).

**Citations:**
- `docs/setup-evidence/P21/plan/p21-voice-interface-enterprise-plan.md` lines 55, 165, 422-423
- `docs/setup-evidence/P21/research/p21-discord-voice-research.md` §2.2, §3.2, §6.2

---

### 2.12 `discord-ext-voice-recv` as receive library

**Verdict:** PASS

The research file justifies `discord-ext-voice-recv` as the de facto standard for receiving audio with discord.py, providing `VoiceRecvClient`, `AudioSink`, and `wants_opus()`/`write()` API. The plan adopts this. This is correct; discord.py core does not expose audio receive directly.

**Citations:**
- `docs/setup-evidence/P21/plan/p21-voice-interface-enterprise-plan.md` lines 9, 62, 86-88, 181-186
- `docs/setup-evidence/P21/research/p21-discord-voice-research.md` §2.3, §6.1

---

## 3. Additional Observations (Non-Blocking)

1. **Barge-in VAD threshold is unspecified.** The plan says "if Faiz speaks >X ms" without committing to a value or range. A recommended threshold (e.g., 300-500 ms) should be documented before Wave P21-002 implementation.
2. **discord.py / discord-ext-voice-recv version pin is TBD.** The research file lists this as an remaining open question (line 498). A version pin should be added to `pyproject.toml` before implementation, especially given DAVE/E2EE compatibility concerns.
3. **Voice channel creation / setup is not assigned to a wave.** The plan assumes `#guinevere-voice` exists but does not specify whether it is created manually, via a migration script, or by the bot. This should be clarified.
4. **Presence priority during overlapping states is undefined.** If the bot is simultaneously in a voice armed state and a loop active state, which presence wins? The plan should define precedence rules before implementation.
5. **Opus silence sentinel on stop is not mentioned.** The research file notes that sending 5 frames of silence avoids Opus interpolation artifacts. The plan's `audio_codec.py` should explicitly handle this when stopping TTS playback.

---

## 4. Hard-Rejection Criteria Check

| # | Criterion | Status |
|---|---|---|
| 1 | Sidecar-only without Hermes core integration | PASS (not sidecar; reuses `_process_turn_core`) |
| 2 | Always-listening without consent + indicator + retention + HARD STOP + audit | PASS (always-listening gated to P21-006, 8 gates documented) |
| 3 | Provider claims not backed by official docs | PASS (research cites discord.py docs, Discord dev docs, PyPI) |
| 4 | Secrets/token handling vague | PASS (SOPS/age, quarterly rotation, no plaintext) |
| 5 | Transcripts enter memory without redaction/retention | PASS (MEM-001..008 gate, redaction, ≤24h raw audio) |
| 6 | Safe-word/HARD STOP not first-class in audio path | PASS (`HardStopHandler.check()` pre-Hermes, Redis flag) |
| 7 | Sub-agent output inline-only without file | PASS (all research files written to disk) |
| 8 | Edits runtime code / deploys / restarts production | PASS (planning-only, no implementation) |

---

## 5. Verdict

**Overall: NEEDS REVIEW**

The Discord UX design for P21 is fundamentally sound: PTT via slash commands is the right choice for a remote VPS bot, the channel placement and presence states align with the Discord UX spec, and all safety/consent/audit surfaces are present. No hard-rejection criteria are triggered.

The dimension does not receive a clean PASS because the **Faiz-only enforcement for `#guinevere-voice` is not explicitly specified** at the channel permission level. The design relies on the server being "private" rather than documenting explicit Discord permission overrides. Additionally, a handful of implementation details (VAD threshold, version pinning, channel creation, presence priority) need clarification before Wave P21-002.

---

## 6. Recommendations

1. **Mandatory before P21-002:** Add explicit Discord channel permission rules for `#guinevere-voice` to the plan or a setup runbook.
2. **Mandatory before P21-002:** Document the VAD barge-in threshold or range.
3. **Recommended before P21-002:** Pin `discord.py` and `discord-ext-voice-recv` versions in `pyproject.toml`.
4. **Recommended before P21-002:** Clarify whether `#guinevere-voice` is created manually or by the bot, and which wave owns that setup.
5. **Recommended before P21-002:** Define presence-state precedence when voice and non-voice states overlap.
6. **Recommended during P21-002:** Ensure `audio_codec.py` sends the Opus silence sentinel on TTS stop.

---

*End of report.*
