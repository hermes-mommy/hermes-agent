# P21 Discord Voice Interface — Research Report

**Project:** Guinevere de Baroque
**Phase:** P21 Voice Interface (research + planning only)
**Author:** Research sub-agent
**Date:** 2026-06-24
**Output path:** `docs/setup-evidence/P21/research/p21-discord-voice-research.md`

---

## 1. Executive Summary

This report collects the official discord.py and Discord developer documentation needed to design a voice turn surface for Guinevere. The key building blocks are:

1. **Connection:** `VoiceChannel.connect()` returns a `VoiceClient`.
2. **Receive:** `discord-ext-voice-recv` extends `VoiceClient` with `.listen(AudioSink)` and a `wants_opus()`/`write()` sink API.
3. **Send:** `VoiceClient.play(AudioSource)` using `FFmpegPCMAudio`/`FFmpegOpusAudio` or a custom `PCMAudio` source.
4. **Safety:** HARD STOP runs on the STT transcript as text, before the transcript reaches Hermes. Always-listening must be gated by consent, a Faiz-only channel, visible indicators, and audit logging.

No runtime code, deployment, or restart is proposed in this document.

---

## 2. discord.py Voice Client (Send & Receive)

### 2.1 Connecting

Per the discord.py migration docs and API reference, connecting to a voice channel is done from the `VoiceChannel` object:

```python
vc = await channel.connect()
# channel is a discord.VoiceChannel instance
```

`channel.connect()` returns a `discord.VoiceClient`.

Sources:

- discord.py migration guide, "Voice Changes in v1.0": `https://github.com/rapptz/discord.py/blob/master/docs/migrating_to_v1.rst`
- discord.py API reference — `VoiceChannel` / `VoiceClient`: `https://discordpy.readthedocs.io/en/latest/api.html`
- Context7 `/rapptz/discord.py` query — *Voice Channel Connection and Playback* (retrieved 2026-06-24)

### 2.2 Sending Audio

Playback uses `VoiceClient.play(AudioSource)`:

```python
vc.play(discord.FFmpegPCMAudio('file.mp3'), after=lambda e: print('done', e))
vc.is_playing()
vc.pause()
vc.resume()
vc.stop()
```

Key source classes:

| Class | Purpose |
|---|---|
| `FFmpegPCMAudio` | Decodes media to PCM; discord.py then encodes to Opus |
| `FFmpegOpusAudio` | Produces Opus packets directly, skipping one encode step |
| `PCMAudio` | Custom source: implement `read()` returning PCM frames |
| `PCMVolumeTransformer` | Runtime volume control |
| `AudioSource` | Base class for custom sources |

Opus loading (required for PCM sources):

```python
import discord
discord.opus.load_opus('/path/to/libopus.so')
# or rely on auto-detection; check with
discord.opus.is_loaded()
```

Sources:

- discord.py docs API reference — `FFmpegPCMAudio`, `FFmpegOpusAudio`, `AudioSource`: `https://discordpy.readthedocs.io/en/latest/api.html`
- Context7 `/rapptz/discord.py` — `discord.opus.load_opus` / `discord.opus.is_loaded` (retrieved 2026-06-24)
- `discord/voice_client.py` source — RTP header/packet creation: `https://github.com/Rapptz/discord.py/blob/master/discord/voice_client.py`

### 2.3 Receiving Audio

discord.py core does **not** expose receive audio directly. The community extension `discord-ext-voice-recv` is the de facto standard. It subclasses `VoiceClient` as `VoiceRecvClient` and provides:

```python
from discord.ext import voice_recv

class MySink(voice_recv.AudioSink):
    def __init__(self):
        super().__init__()

    def wants_opus(self) -> bool:
        return False  # we want decoded PCM

    def write(self, user, data):
        # data.pcm   -> decoded PCM bytes (if wants_opus() == False)
        # data.opus  -> raw Opus packet (if wants_opus() == True)
        # data.user  -> user metadata
        pass

    def cleanup(self):
        pass

# Connect with the extended client
vc = await voice_channel.connect(cls=voice_recv.VoiceRecvClient)
vc.listen(MySink())
```

`AudioSink.write(self, user, data)` receives per-packet data. `data.pcm` is the decoded PCM produced by the extension from Discord's Opus payload.

Sources:

- `discord-ext-voice-recv` README/PyPI: `https://pypi.org/project/discord-ext-voice-recv/`
- GitHub: `https://github.com/imayhaveborkedit/discord-ext-voice-recv`
- RFC discussion on the receive API design: `https://github.com/Rapptz/discord.py/issues/1094`
- Pull request implementing receive: `https://github.com/Rapptz/discord.py/pull/6507`
- Real-world GitHub usage from `search_code` (retrieved 2026-06-24): `voice_client.listen(sink)` and `AudioSink.write(self, user, data)` patterns across multiple repositories.

---

## 3. Discord Voice Gateway & UDP Transport

### 3.1 Protocol Flow (Discord developer docs)

The official Discord documentation describes the following flow:

1. Client sends a Gateway `Voice State Update` (opcode 4) to join a voice channel.
2. Discord replies with `Voice Server Update` (gateway event) containing the voice server endpoint and token.
3. Client opens a WebSocket (the **voice gateway**) to that endpoint and identifies.
4. Voice gateway responds with a `Ready` payload containing SSRC, UDP IP/port, and supported encryption modes.
5. Client opens a **UDP** socket to the provided IP/port; performs IP discovery if needed.
6. Client sends `Select Protocol` (opcode 1) with its public IP/port and chosen encryption mode.
7. Voice gateway replies with `Session Description` (opcode 4) containing the secret key.
8. Voice data is sent/received as RTP packets carrying encrypted Opus audio.

Sources:

- Discord Developer Docs — Voice Connections: `https://docs.discord.com/developers/topics/voice-connections`
- Discord Userdoccers mirror — "Voice Connections": `https://docs.discord.food/topics/voice-connections`

### 3.2 Codec and Frame Format

- **Codec:** Opus (mandatory; the only audio codec Discord supports).
- **Sample rate:** 48 kHz.
- **Channels:** 2 (stereo) for sending; received streams are also 48 kHz stereo by default.
- **Frame size:** 20 ms (960 samples at 48 kHz).
- **Encryption:** Depends on mode selected (e.g., `xsalsa20_poly1305` deprecated; `aead_aes256_gcm`/`aead_xchacha20_poly1305` current). This is handled by the library.
- **Silence sentinel:** When stopping transmission, send 5 frames of silence (`0xF8, 0xFF, 0xFE`) to avoid Opus interpolation artifacts.

Sources:

- Discord Developer Docs — Voice Connections: `https://docs.discord.com/developers/topics/voice-connections`
- Discord Userdoccers — "Opus is the only available codec and should be priority 1000": `https://docs.discord.food/topics/voice-connections`

### 3.3 Gateway Reconnection

- Bots should implement voice gateway resume.
- On connection severed, open a new WebSocket and reconnect.
- Version 8+ of the voice gateway can resend buffered messages after a successful resume.

Source: Discord Developer Docs — Voice Connections: `https://docs.discord.com/developers/topics/voice-connections`

---

## 4. Push-to-Talk (PTT) Design for a Remote VPS Bot

### 4.1 The Core Constraint

Guinevere runs on a remote VPS. She cannot capture a local keyboard keybind on Faiz's machine. Therefore, a true "hold-to-talk" hardware keybind must be implemented **outside** the bot and signaled to the bot via an HTTP/webhook endpoint or a text command.

### 4.2 Candidate PTT Surfaces

| Surface | Mechanism | Pros | Cons |
|---|---|---|---|
| **Slash command `/voice arm` / `/voice disarm`** | User runs `/voice arm` to open the mic; bot listens until Faiz says the HARD STOP phrase or runs `/voice disarm`. | Explicit, auditable, works from any Discord client, aligns with existing slash command UX. | One extra tap vs. a hardware key. |
| **Reaction toggle on a status message** | Bot posts a "Voice armed/disarmed" control embed; Faiz clicks the emoji to arm. | Visible, simple, mobile-friendly. | Less direct than slash command; can drift off-screen. |
| **External trigger (Tasker phone keybind → webhook)** | Phone keybind hits a Guinevere HTTP endpoint `/voice/ptt?state=on`. | Closest to a hardware PTT button. | Requires phone + Tasker + authenticated endpoint; network latency. |
| **Text command** | Faiz types `!ptt` or `/voice` in chat. | Simplest to implement. | Slower than a keybind; not hands-free. |

### 4.3 Recommended PTT Surface

**Primary:** `/voice arm` and `/voice disarm` slash commands.
**Secondary:** Tasker/external webhook for users who want a hardware-like button.
**Tertiary:** Reaction toggle on a persistent voice-status embed for quick visual control.

Rationale:

- Slash commands are already the canonical Guinevere UX (`docs/60-persona/63-DiscordUXSpec_v1.0.md` §2).
- They are authenticated, permission-scoped, and produce an audit trail.
- They do not require exposing a public webhook unless desired.
- The armed state can be shown in the bot's Discord presence/status.

---

## 5. Always-Listening Constraints & Consent Gating

### 5.1 Discord ToS / Privacy Implications

- Discord's Developer Policy and Developer Terms require lawful processing of user data.
- Voice data is sensitive personal data; recording or transcribing without consent may violate Discord ToS and local laws (e.g., all-party consent jurisdictions).
- Discord states it does not record voice/video calls; bots that do so must obtain explicit user consent.

Sources:

- Discord Developer Policy: `https://support-dev.discord.com/hc/en-us/articles/8563934450327-Discord-Developer-Policy`
- Discord Developer Terms of Service: `https://support-dev.discord.com/hc/en-us/articles/8562894815383-Discord-Developer-Terms-of-Service`
- Discord Terms of Service: `https://discord.com/terms`
- Discord Safety — "Are you recording my voice and video calls?": `https://discord.com/safety/important-policy-updates`
- Community discussion on consent/recording: `https://support.discord.com/hc/en-us/community/posts/360071369492-Record-Calls`

### 5.2 Recommended Gating for Guinevere

Because "Guinevere's Domain" is a single-user private server, the risk surface is smaller, but the following gates are still required:

1. **Faiz-only channel:** The bot only arms voice in a designated private voice channel accessible only to Faiz (and the bot).
2. **Explicit consent on first use:** A one-time `/consent voice on` (reuse existing `/consent` command from the UX spec) before the bot is allowed to receive voice.
3. **Visible indicator:** Bot status changes to "Listening 👂" when armed; "Speaking 🎤" when generating TTS; normal status when disarmed.
4. **Armed state is not permanent:** Auto-disarm after a timeout or when Faiz leaves the channel.
5. **HARD STOP stops everything:** A HARD STOP trigger (text or spoken) immediately disarms the mic and returns to safe mode.
6. **Audit logging:** Every arm/disarm/consent event is written to `#audit-log` as required by `docs/60-persona/63-DiscordUXSpec_v1.0.md` §8.3.
7. **No 24/7 always-on capture:** The bot should be in an unarmed idle state by default; capture only occurs during an Faiz-initiated armed session.

---

## 6. Audio Sink → STT Streaming Pattern

### 6.1 PCM Chunk Streaming

A sink that feeds a streaming STT provider should buffer per-user Opus/PCM frames and emit chunks as speech segments are detected.

```python
from collections import defaultdict
from discord.ext import voice_recv

class StreamingSTTSink(voice_recv.AudioSink):
    def __init__(self, on_pcm):
        super().__init__()
        self.on_pcm = on_pcm  # callback(bytes_per_user)
        self.buffers = defaultdict(bytes)

    def wants_opus(self) -> bool:
        return False  # ask for decoded PCM

    def write(self, user, data):
        # data.pcm is the decoded PCM for this 20ms frame
        self.buffers[user] += data.pcm

    def finalize_user(self, user):
        pcm = self.buffers.pop(user, b'')
        self.on_pcm(user, pcm)

    def cleanup(self):
        for user in list(self.buffers):
            self.finalize_user(user)
```

Key points:

- `data.pcm` from `discord-ext-voice-recv` is already decoded from Opus.
- Default output is 48 kHz stereo. Most STT providers need 16 kHz (or 24 kHz) mono.
- Resample 48 kHz → 16 kHz and downmix stereo → mono before sending to STT.
- Frame size is 20 ms; a VAD (voice activity detector) should be used to detect speech start/end and avoid sending silence.

Sources:

- `discord-ext-voice-recv` README/PyPI: `https://pypi.org/project/discord-ext-voice-recv/`
- Real-world GitHub code from `search_code` (retrieved 2026-06-24): `MyAudioSink.write(self, user, data)` writes `data.pcm` to a stream.

### 6.2 Resampling and Downmixing

Tools commonly used:

- **ffmpeg** via `subprocess` or `pydub` for offline chunk conversion.
- **librosa / soundfile / resampy** for programmatic resampling in Python.
- **webrtcvad** or **silero-vad** for voice activity detection.

Example ffmpeg conversion for a PCM chunk:

```bash
ffmpeg -f s16le -ar 48000 -ac 2 -i input.pcm \
       -ar 16000 -ac 1 -f s16le output.pcm
```

---

## 7. Interruption / Barge-In

### 7.1 Stopping Playback

`VoiceClient.stop()` cancels the current `AudioSource` immediately:

```python
if vc.is_playing():
    vc.stop()
```

`VoiceClient.source` can also be swapped at runtime.

### 7.2 Ducking

To lower volume instead of stopping:

```python
vc.source = discord.PCMVolumeTransformer(vc.source)
vc.source.volume = 0.3
```

### 7.3 Barge-In Flow

While TTS is playing:

1. Continue receiving audio via the sink.
2. Run VAD on the incoming stream.
3. If Faiz starts speaking (VAD threshold exceeded):
   - `vc.stop()` or duck volume.
   - Abort the current TTS generation if still streaming.
   - Switch to listening mode.
   - Process the new utterance through the existing Hermes turn pipeline.

Source:

- Context7 `/rapptz/discord.py` — *Modifying Voice Client Audio Source* (retrieved 2026-06-24)

---

## 8. Codec Facts Summary

| Property | Discord Voice |
|---|---|
| Codec | Opus |
| Sample rate | 48 kHz |
| Channels (send) | 2 (stereo) |
| Frame duration | 20 ms |
| Samples per frame | 960 @ 48 kHz |
| Silence sentinel | 5 frames of silence before stopping send |
| Encryption modes | aead_aes256_gcm, aead_xchacha20_poly1305, deprecated xsalsa20_poly1305 |
| STT input typical | 16 kHz mono PCM (or 24 kHz) |
| TTS output typical | 48 kHz stereo PCM (or resampled to 48 kHz) |

---

## 9. Permissions

The bot needs the following voice channel permissions:

- `CONNECT`
- `SPEAK`
- (Optional but recommended) `PRIORITY_SPEAKER` if available
- (Optional) `USE_VOICE_ACTIVATION`

These are granted through the Discord OAuth2 scope `bot` with permissions or through channel permission overrides.

Source:

- discord.py docs — `Permissions`: `https://discordpy.readthedocs.io/en/latest/api.html`
- Discord Developer Docs — permissions: `https://docs.discord.com/developers/topics/permissions`

---

## 10. Voice Channel ID Wiring

Analogous to the existing constant in `src/discord/hermes_conversational.py`:

```python
GUINEVERE_CHAT_CHANNEL_ID: Final[int] = 1_510_914_600_777_023_659
```

A new constant should be added for the voice channel:

```python
GUINEVERE_VOICE_CHANNEL_ID: Final[int] = <VOICE_CHANNEL_ID>
```

This should be wired the same way as `GUINEVERE_CHAT_CHANNEL_ID` — loaded from environment/config if necessary, but a single canonical constant for now.

---

## 11. UX Alignment with Discord UX Spec

### 11.1 Server Structure

Per `docs/60-persona/63-DiscordUXSpec_v1.0.md` §1, the server is private, single-user (Faiz only), and contains the channel categories:

- `👑 MOMMY'S THRONE`
- `📊 SURVEILLANCE ROOM`
- `🔧 PROJECTS`
- `🗡️ ARCHIVE`

A dedicated voice channel should be placed under `👑 MOMMY'S THRONE`, e.g., `#guinevere-voice`.

### 11.2 Presence / Status Indicator

Add two new presence states to the table in `docs/60-persona/63-DiscordUXSpec_v1.0.md` §1.2 / §7.6:

| Condition | Activity Text | Status |
|---|---|---|
| Voice armed / listening | `Listening to Darling 👂` | Online (green) |
| Voice speaking / playing TTS | `Speaking to Darling 🎤` | Online (green) |

### 11.3 Slash Command UX

Proposed new commands (consistent with §2 command style):

| Command | Params | Behavior |
|---|---|---|
| `/voice arm` | — | Joins designated voice channel, arms mic, sets presence to "Listening 👂". |
| `/voice disarm` | — | Disarms mic, optionally disconnects from voice channel, restores default presence. |
| `/voice join` | channel (optional) | Alias/helper for manual connection. |
| `/voice status` | — | Shows armed/disarmed, channel, current STT/TTS state. |

All commands are Faiz-only, consistent with the existing permission model.

---

## 12. Recommended PTT Data-Flow Diagram

```
Faiz speaks in Discord voice channel
         │
         ▼
┌─────────────────────┐
│ Discord Voice Server│
│ (Opus 48 kHz stereo)│
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  VoiceRecvClient    │
│  .listen(MySink)    │
└──────────┬──────────┘
           │ Opus packets
           ▼
┌─────────────────────┐
│  AudioSink.write()  │
│  data.opus / data.pcm│
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Opus decode (if pcm)│
│ Resample 48 kHz → 16│
│ Stereo → mono       │
└──────────┬──────────┘
           │ 16 kHz mono PCM chunks
           ▼
┌─────────────────────┐
│ Streaming STT       │
│ (e.g., Whisper API, │
│  Deepgram, Azure)   │
└──────────┬──────────┘
           │ transcript text
           ▼
┌─────────────────────┐
│ HARD STOP check     │
│ (text, pre-Hermes)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Hermes conversational│
│ turn pipeline       │
│ (existing handler)  │
└──────────┬──────────┘
           │ response text
           ▼
┌─────────────────────┐
│ TTS generation      │
│ (PCM / mp3 / opus)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Resample to 48 kHz  │
│ if needed; mix to   │
│ stereo if needed    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Opus encode / send  │
│ VoiceClient.play()   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Faiz hears Guinevere│
│ in Discord voice    │
└─────────────────────┘
```

---

## 13. Open Questions for Implementation Planning

1. Which STT provider will be used, and what are its exact PCM requirements (sample rate, bit depth, channel count)?
2. Which TTS provider will be used, and does it output PCM or Opus natively?
3. Do we need a local Opus/VAD dependency in the VPS container, or will we use ffmpeg subprocesses?
4. Should the voice module reuse the existing Redis rate limiter (DB0) or a dedicated voice rate limit bucket?
5. What is the target `discord.py` and `discord-ext-voice-recv` version pin to ensure DAVE/E2EE compatibility?

---

## 14. Sources Cited

1. Discord Developer Docs — Voice Connections: `https://docs.discord.com/developers/topics/voice-connections`
2. Discord Userdoccers — Voice Connections: `https://docs.discord.food/topics/voice-connections`
3. discord.py API Reference: `https://discordpy.readthedocs.io/en/latest/api.html`
4. discord.py migration guide (Voice Changes in v1.0): `https://github.com/rapptz/discord.py/blob/master/docs/migrating_to_v1.rst`
5. Context7 `/rapptz/discord.py` docs (retrieved 2026-06-24)
6. `discord-ext-voice-recv` PyPI: `https://pypi.org/project/discord-ext-voice-recv/`
7. `discord-ext-voice-recv` GitHub: `https://github.com/imayhaveborkedit/discord-ext-voice-recv`
8. RFC: Voice Receive API Design/Usage: `https://github.com/Rapptz/discord.py/issues/1094`
9. PR #6507 — Support for receiving audio: `https://github.com/Rapptz/discord.py/pull/6507`
10. Discord Developer Policy: `https://support-dev.discord.com/hc/en-us/articles/8563934450327-Discord-Developer-Policy`
11. Discord Developer Terms of Service: `https://support-dev.discord.com/hc/en-us/articles/8562894815383-Discord-Developer-Terms-of-Service`
12. Discord Terms of Service: `https://discord.com/terms`
13. Discord Safety — Important Policy Updates: `https://discord.com/safety/important-policy-updates`
14. Discord Community — Record Calls: `https://support.discord.com/hc/en-us/community/posts/360071369492-Record-Calls`
15. Guinevere Discord UX Spec v1.0: `docs/60-persona/63-DiscordUXSpec_v1.0.md`
16. Guinevere HARD STOP handler: `src/core/services/hard_stop_handler.py`
17. Guinevere Hermes conversational turn: `src/discord/hermes_conversational.py`
