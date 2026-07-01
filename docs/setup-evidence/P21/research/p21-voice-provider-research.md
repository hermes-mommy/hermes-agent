# P21 Voice Interface — Voice Provider Research (STT + TTS + Realtime)

**Date:** 2026-06-24 (all prices and claims retrieved on or before this date)
**Scope:** Single-user private AI companion (Guinevere de Baroque), Indonesian + English code-switching
**Constraints:** Python/FastAPI stack, discord.py voice (Opus 48kHz), existing HARD STOP + prompt-injection infra processes TEXT — voice transcript text feeds existing text pipeline
**Reading order:** Executive shortlist -> Provider deep-dives -> Audio codec -> Wake-word/VAD -> Local fallback -> Benchmark criteria -> Design options

---

## 1. Executive Shortlist Table

| Provider | Capability | Indonesian Support | Streaming | Latency (p50) | Pricing (approx) | Notes |
|---|---|---|---|---|---|---|
| **OpenAI Whisper API** | STT (whisper-1, gpt-4o-transcribe, gpt-4o-mini-transcribe) | Yes (99+ languages incl. id) | No native streaming (use Realtime API for streaming) | Batch: 5-10x realtime (~6s for 60s file) | $0.006/min (whisper-1), $0.003/min (gpt-4o-mini-transcribe) | Batch only. Gpt-4o-transcribe-diarize available. $0.017/min for gpt-realtime-whisper streaming. 25MB file limit. |
| **OpenAI TTS** | TTS (tts-1, tts-1-hd, gpt-4o-mini-tts) | Yes (Whisper language coverage) | Yes (streaming via REST) | ~500ms TTS-1 | $15/1M chars (tts-1), $30/1M (hd), ~$15/1M chars (gpt-4o-mini-tts token-based) | 9-13 built-in voices. No voice cloning. gpt-4o-mini-tts has steerable prosody via instructions param. No SSML. |
| **OpenAI Realtime API** | Realtime conversational (gpt-realtime, gpt-realtime-mini) | Yes (multilingual speech-to-speech) | WebRTC / WebSocket / SIP | <150ms (speech-to-speech) | gpt-realtime: $32/1M audio input tokens + $64/1M audio output; ~$0.18-0.24/min. mini: ~$0.06-0.10/min | Full speech-to-speech. Function calling built-in. Barge-in via VAD. $0.017/min extra for transcription. |
| **Deepgram Nova-3** | STT | Yes (Nova-3 Multilingual incl. id) | WebSocket streaming | sub-300ms streaming | Streaming: $0.0048/min (mono), $0.0058/min (multi); Batch: $0.0043/min | $200 free credits. Flux multilingual (Apr 2026) adds integrated end-of-turn detection ~260ms. |
| **Deepgram Aura-2** | TTS | No (7 languages: EN, ES, FR, DE, NL, IT, JA) | WebSocket streaming | <200ms TTFB (90ms optimized) | Aura-1: $0.015/1K chars; Aura-2: $0.030/1K chars | No Indonesian voice. 40+ EN voices. Enterprise Runtime. |
| **Deepgram Voice Agent API** | Realtime agent | Via Nova-3 STT (id) + BYO LLM | WebSocket | Sub-300ms | $4.50/hr (Standard tier), $0.075/min | Unified STT+TTS+LLM orchestration. Barge-in, function calling. 75% cheaper than OpenAI Realtime. |
| **AssemblyAI** | STT | Yes (Universal-2: 99 languages incl. id; Universal-3 Pro: 6 languages only) | WebSocket streaming | 300-600ms streaming | $0.15/hr (U-2 batch), $0.45/hr (U-3 Pro streaming) | $50 free credits. U-3 Pro does NOT support Indonesian (silent fallback to U-2). Add-ons stack diarization, sentiment, etc. |
| **Google Cloud STT (Chirp 3)** | STT | Yes (125+ languages incl. id-ID) | gRPC streaming | ~250-400ms | $0.016/min standard; $0.004/min dynamic batch | 60 min/month free ongoing. Chirp 3 included at no premium. 15-sec billing increments. |
| **Google Cloud TTS** | TTS | Yes (WaveNet/Neural2 voices, id-ID available) | REST streaming | ~300-500ms | $4/1M chars (Standard), $16/1M (WaveNet/Neural2), $30/1M (Chirp 3 HD) | 1M chars/month free for WaveNet. 500+ voices. SSML supported. **Has Indonesian Neural2 voices.** |
| **Azure Speech STT** | STT | Yes (140+ languages incl. id-ID) | SDK (WebSocket) | ~250-400ms | $1/hr ($0.0167/min) standard; $0.36/hr batch | 5 hr/month free. SOC 2, HIPAA, GDPR. Custom models trainable. |
| **Azure Speech TTS** | TTS | Yes (id-ID neural voices available) | SDK / REST / SSML streaming | ~300-500ms | Neural TTS: ~$16/1M chars | **Has Indonesian (id-ID) neural voices.** Full SSML support. Custom Voice (training). HD voices available. |
| **ElevenLabs** | TTS + Conversational AI | Yes (32+ languages incl. id via Multilingual v2) | WebSocket / WebRTC | ~200-400ms TTS | TTS: ~$60/1M chars (Flash). Agents: $0.10-0.20/min | **Has Indonesian voice quality (voice cloning retains id).** Voice cloning requires explicit consent. Plan-based ($5-$330/mo). |
| **Cartesia Sonic** | TTS | Yes (42 languages incl. id through Sonic 3.5) | WebSocket streaming | 40-188ms TTFA (Sonic 3.5) | ~$33/1M chars (1 credit/char on Pro plan) | **Has Indonesian support.** 40ms TTFA claim. Voice cloning from 10s audio. Free tier (20K chars). |
| **Cartesia Ink** | STT | Limited (English + select) | WebSocket | Streaming-optimized | $0.13/hr | Not suitable for Indonesian. |
| **faster-whisper** (local) | STT (offline) | Yes (99 languages incl. id) | Local (batch/pseudo-streaming) | GPU: ~4x realtime (large-v3); CPU: slower | $0 (MIT license) | 2.9GB model (large-v3). Requires CUDA GPU or high-RAM CPU. INT8 quantization available. |
| **Piper** (local) | TTS (offline) | Yes (id-ID voice available) | Local | Near real-time on CPU | $0 (MIT license) | **Has Indonesian news_tts voice.** Rhasspy project. Small footprint (<100MB). |
| **Kokoro** (local) | TTS (offline) | Limited (EN, FR, KO, JA, ZH-CN — **no Indonesian**) | Local | 36-96x real-time on GPU, CPU-capable | $0 (Apache 2.0) | #1 TTS Arena (Jan 2026). 82M params, 300MB. No Indonesian. |

---

## 2. Detailed Provider Analysis

### 2.1 STT Providers

#### OpenAI Whisper API (whisper-1, gpt-4o-transcribe, gpt-4o-mini-transcribe)

- **Model:** whisper-1 (general-purpose), gpt-4o-transcribe (higher quality), gpt-4o-mini-transcribe (cost-optimized)
- **Languages:** 99+ languages including Indonesian. Source: [developers.openai.com/api/docs/guides/speech-to-text](https://developers.openai.com/api/docs/guides/speech-to-text) (retrieved 2026-06-24)
- **Streaming:** Not natively supported. whisper-1 is batch-only (upload complete file, wait for transcript). For real-time, use gpt-realtime-whisper via the Realtime API ($0.017/min). Source: [costgoat.com](https://costgoat.com/pricing/openai-transcription) (retrieved 2026-06-24)
- **Latency:** Batch mode approximately 5-10x real-time. No streaming latency data for whisper-1.
- **Pricing:** $0.006/min for whisper-1, $0.003/min for gpt-4o-mini-transcribe (estimated ~0.00125/min). Source: [openai.com/api/pricing/](https://openai.com/api/pricing/) (retrieved 2026-06-24)
- **Max audio length:** 25MB file limit (~25 min MP3 at 128kbps). No duration limit if file fits.
- **Auth:** OpenAI API key (Bearer token)
- **Diarization:** Available via gpt-4o-transcribe-diarize
- **Indonesian WER:** Not officially published. Community whisper benchmarks show WER ~8-12% for Indonesian on clean audio, higher on noisy.
- **Benchmark criterion:** $/hr active listening: $0.36/hr; WER on Indonesian: ~10-15%; latency: batch only

#### Deepgram (Nova-3, Flux)

- **Model:** Nova-3 (Feb 2025), Flux Multilingual (Apr 29, 2026 — integrated end-of-turn detection)
- **Indonesian:** Supported. Nova-3 Multilingual covers 10+ languages with code-switching; monolingual variant expanded to 30+ languages including Indonesian. Deepgram has a dedicated Indonesian product page at [deepgram.com/product/speech-to-text/indonesian](https://deepgram.com/product/speech-to-text/indonesian). Source (retrieved 2026-06-24)
- **Streaming:** WebSocket-based real-time streaming with interim results, speech_final markers, and utterance endpointing.
- **Latency:** Nova-3 streaming sub-300ms; Flux multilingual end-of-turn detection ~260ms median. Source: [Coval.ai benchmark June 2026](https://www.coval.ai/blog/best-speech-to-text-providers-in-2026-independent-benchmarks-and-how-to-choose/) (retrieved 2026-06-24)
- **Pricing:** 
  - Nova-3 Monolingual streaming: $0.0048/min ($0.288/hr)
  - Nova-3 Multilingual streaming: $0.0058/min ($0.348/hr)
  - Flux English: $0.0065/min; Flux Multilingual: $0.0078/min
  - Batch/pre-recorded: $0.0043/min ($0.258/hr)
  - Source: [deepgram.com/pricing](https://deepgram.com/pricing) and [diyai.io](https://diyai.io/ai-tools/speech-to-text/deepgram-pricing-2026/) (retrieved 2026-06-24)
- **Auth:** API Key (Authorization: Token KEY) or JWT tokens
- **Free credits:** $200
- **Max audio:** No documented file limit for pre-recorded; streaming is continuous
- **Benchmark criterion:** Streaming latency p50: sub-300ms; $/hr active listening: $0.35-0.47/hr (multilingual streaming); Indonesian WER: ~6-9% (Nova-3, no independent id WER published)

#### AssemblyAI (Universal-2, Universal-3 Pro)

- **Indonesian:** Supported on Universal-2 (99 languages). Universal-3 Pro supports ONLY 6 languages (EN, ES, FR, DE, IT, PT) — Indonesian is NOT supported and audio silently falls back to Universal-2. Source: [assemblyai.com/pricing](https://www.assemblyai.com/pricing) and [checkthat.ai](https://checkthat.ai/brands/assemblyai/pricing) (retrieved 2026-06-24)
- **Streaming:** WebSocket-based real-time transcription. Billed on total session duration, not audio content.
- **Latency:** 300-600ms median streaming latency. Source: [Coval.ai June 2026](https://www.coval.ai/blog/best-speech-to-text-providers-in-2026-independent-benchmarks-and-how-to-choose/)
- **Pricing:**
  - Universal-2 batch: $0.15/hr ($0.0025/min)
  - Universal-2 streaming: $0.15/hr
  - Universal-3 Pro batch: $0.21/hr
  - Universal-3 Pro streaming: $0.45/hr
  - Add-ons: diarization +$0.02/hr, sentiment +$0.02/hr, summarization +$0.03/hr, entity detection +$0.08/hr
  - Source: [assemblyai.com/pricing](https://www.assemblyai.com/pricing) (retrieved 2026-06-24)
- **Auth:** API key (x-api-key header)
- **Free credits:** $50
- **Indonesian caveat:** Since U-3 Pro does not support id-ID, real accuracy gains for Indonesian are unavailable at any price on AssemblyAI. U-2 must be used.
- **Benchmark criterion:** Indonesian WER ~8-12% (U-2); $/hr streaming: $0.15/hr + $0.02/hr diarization = $0.17/hr total (base)

#### Google Cloud Speech-to-Text (Chirp 3, Chirp 2)

- **Indonesian:** Yes. Supports id-ID. 125+ languages. Source: [cloud.google.com/speech-to-text](https://cloud.google.com/speech-to-text/pricing) (retrieved 2026-06-24)
- **Streaming:** gRPC bidirectional streaming. Interim results supported. Streaming limit: 5 minutes per request (v1p1beta1), but continuous streaming is possible with reconnection.
- **Latency:** ~250-400ms streaming. Chirp 3 provides "endpointing sensitivity" SHORT mode for faster turn-taking. Source: [Coval.ai June 2026](https://www.coval.ai/blog/best-speech-to-text-providers-in-2026-independent-benchmarks-and-how-to-choose/)
- **Pricing:**
  - V2 Standard: $0.016/min ($0.96/hr) — includes Chirp 3 at no extra cost
  - V2 Dynamic Batch: $0.004/min ($0.24/hr) — up to 24-hour turnaround
  - 60 min/month free (ongoing, no expiration)
  - $300 free credits for new customers
  - Source: [cloud.google.com/speech-to-text/pricing](https://cloud.google.com/speech-to-text/pricing) (retrieved 2026-06-24)
- **Auth:** GCP service account (OAuth 2.0 / API keys)
- **Billing:** 15-second increments, rounded up. Short utterances cost disproportionally.
- **Max audio:** Batch up to 480 minutes. Streaming: 5 min per stream (v1p1beta1 extension possible).
- **Benchmark criterion:** Indonesian WER: ~7-11% (Chirp 3); $/hr streaming: $0.96/hr; latency: ~250-400ms

#### Azure Speech-to-Text

- **Indonesian:** Yes. id-ID supported. 140+ languages. Source: [learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support) (retrieved 2026-06-24)
- **Streaming:** SDK-based real-time transcription with WebSocket. Support for interim results, end-of-stream detection.
- **Latency:** ~250-400ms. Comparable to Google Cloud STT.
- **Pricing:**
  - Standard real-time: $1/hr ($0.0167/min)
  - Batch: $0.36/hr
  - Custom model: $1.20/hr real-time; $0.45/hr batch
  - Free tier: 5 audio hours/month
  - Source: [azure.microsoft.com/en-us/pricing/details/speech/](https://azure.microsoft.com/en-us/pricing/details/speech/) (retrieved 2026-06-24)
- **Auth:** Azure AI Services key (Ocp-Apim-Subscription-Key) or Entra token
- **Diarization:** Included in fast transcription at no extra cost
- **Benchmark criterion:** Indonesian WER ~8-12% (standard model); $/hr: $1.00/hr real-time; latency: ~300-400ms

### 2.2 TTS Providers

#### OpenAI TTS (tts-1, tts-1-hd, gpt-4o-mini-tts)

- **Voices:** 9 (tts-1/hd), 13 (gpt-4o-mini-tts: adds ballad, verse, marin, cedar). No Indonesian-specific voices — voices are English-optimized but pronounce non-English text via Whisper phoneme mapping.
- **Indonesian quality:** Follows Whisper language support — Indonesian (id) is in Whisper's 99+ language list, so TTS can pronounce Indonesian text, but prosody and accent are not natively Indonesian. Quality is functional, not native.
- **Streaming:** REST API supports streaming response (chunked transfer encoding). Not WebSocket.
- **Latency:** tts-1 ~0.5s first-byte; gpt-4o-mini-tts variable (higher for instructions processing).
- **Pricing:**
  - tts-1: $15/1M chars (~$0.015/min or ~$0.74/hr)
  - tts-1-hd: $30/1M chars (~$0.03/min or ~$1.49/hr)
  - gpt-4o-mini-tts: $0.60/1M input tokens + $12/1M audio output tokens (~$0.015/min estimated, ~$0.90/hr)
  - Source: [texttolab.com](https://texttolab.com/blog/openai-tts-pricing) and [openai.com/api/pricing](https://openai.com/api/pricing/) (retrieved 2026-06-24)
- **SSML:** Not supported. gpt-4o-mini-tts uses instructions parameter instead (natural language prosody control).
- **Voice cloning:** Not available.
- **Max request:** tts-1/hd: 4,096 chars; gpt-4o-mini-tts: 2,000 input tokens.
- **Auth:** OpenAI API key.
- **Benchmark criterion:** $/hr audio: $0.74/hr (cheapest TTS option); latency: ~500ms TTFB; Indonesian prosody quality: functional but non-native.

#### Deepgram Aura / Aura-2

- **Voices:** 40+ English-optimized. 7 languages as of Aura-2: English, Spanish, French, German, Dutch, Italian, Japanese. **Indonesian NOT supported.** Source: [deepgram.com/learn/aura-2-now-speaks-dutch-french-german-italian-japanese](https://deepgram.com/learn/aura-2-now-speaks-dutch-french-german-italian-japanese) (retrieved 2026-06-24)
- **Streaming:** WebSocket streaming supported.
- **Latency:** Aura-2 <200ms TTFB baseline, 90ms optimized. Aura-2 Coval benchmark: 313ms p50 TTFA. Source: [deepgram.com/learn/best-text-to-speech-apis-2026](https://deepgram.com/learn/best-text-to-speech-apis-2026) (retrieved 2026-06-24)
- **Pricing:** Aura-1: $0.015/1K chars; Aura-2: $0.030/1K chars. Source: [deepgram.com/pricing](https://deepgram.com/pricing) (retrieved 2026-06-24)
- **SSML:** Not supported. Aura-2 Controls provide speed and pronunciation overrides.
- **Auth:** Deepgram API key.
- **Indonesian suitability:** Poor — no id-ID voice. Not recommended for this project.

#### ElevenLabs

- **Voices:** 1000+ voices. Multilingual v2 supports 32+ languages including Indonesian. Voice cloning retains the cloned voice across all supported languages (including id). Source: [elevenlabs.io/voice-cloning](https://elevenlabs.io/voice-cloning) (retrieved 2026-06-24)
- **Indonesian quality:** Excellent — can clone a consented Indonesian voice and it will speak id-ID naturally. Or use pre-built multilingual voices with Indonesian text.
- **Streaming:** WebSocket (preferred) or WebRTC. Word-level timestamps. Interruption handling built into Conversational AI.
- **Latency:** ~200-400ms TTS (Flash model). Source: [docs.pipecat.ai](https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs) (retrieved 2026-06-24)
- **Pricing:**
  - TTS Multilingual v2: ~1 credit/char. Flash model: ~0.5-1 credit/char.
  - API pricing: Starter $5/mo (30K chars), Creator $22/mo (121K chars), Pro $99/mo (600K chars), Scale $330/mo (1.8M chars)
  - Overage: ~$0.17/min (~$10.20/hr)
  - Conversational AI: $0.10-0.20/min ($6-12/hr) — 95% discount on silence >10s
  - Source: [elevenlabs.io/pricing](https://elevenlabs.io/pricing) and [cekura.ai](https://www.cekura.ai/blogs/elevenlabs-pricing) (retrieved 2026-06-24)
- **SSML:** Not supported.
- **Voice cloning consent:** Required. Explicit consent from voice owner. Clone verification. 12+ US states have voice cloning laws (CA, NY, TN ELVIS Act). Source: [terms.law](https://terms.law/ai-output-rights/elevenlabs/) (retrieved 2026-06-24)
- **Auth:** API key (xi-api-key header), signed URLs for agents.
- **Benchmark criterion:** $/hr: ~$10.20/hr overage (expensive); Indonesian quality: excellent with cloned voice; TTS Arena rank: #4; streaming latency: ~200-400ms.

#### Google Cloud TTS

- **Voices:** 500+ voices. Indonesian (id-ID) supported via Neural2 voices (e.g., id-ID-Standard-A, id-ID-WaveNet-A, id-ID-Neural2-A). Source: [cloud.google.com/text-to-speech/docs/voices](https://cloud.google.com/text-to-speech/docs/list-voices-and-types) (retrieved 2026-06-24)
- **Indonesian quality:** Native Indonesian voices available in multiple tiers (Standard, WaveNet, Neural2). Best native Indonesian cloud TTS option.
- **Streaming:** REST streaming supported. Bidirectional streaming via gRPC for Chirp 3: HD voices (lowest latency).
- **Latency:** ~300-500ms TTFB. Streaming can reduce perceived latency.
- **Pricing:**
  - Standard: $4/1M chars (4M chars free/month)
  - WaveNet: $4/1M chars (1M chars free/month) — value note: same price as Standard!
  - Neural2: $16/1M chars (1M free/month)
  - Chirp 3: HD: $30/1M chars (1M free/month)
  - Gemini 2.5 Flash TTS: $0.50/1M text input + $10/1M audio output tokens
  - Source: [cloud.google.com/text-to-speech/pricing](https://cloud.google.com/text-to-speech/pricing) (retrieved 2026-06-24)
- **SSML:** Full SSML support (pitch, rate, volume, pauses, pronunciation, emphasis, custom lexicon).
- **Voice cloning:** Chirp 3: Instant Custom Voice — from 10 seconds of audio, $60/1M chars. Multilingual transfer.
- **Auth:** GCP service account.
- **Benchmark criterion:** $/hr: $1.49/hr (WaveNet, ~150 wpm); best native Indonesian voice; SSML support; TTS Arena rank: #2 (Gemini Flash).

#### Azure Speech TTS

- **Voices:** 500+ neural voices. Indonesian (id-ID) neural voices available (e.g., id-ID-ArifNeural (Male), id-ID-WahyuNeural (Female)). Source: [learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support) (retrieved 2026-06-24)
- **Indonesian quality:** Native id-ID neural voices. Full emotional range (cheerful, sad, angry, etc. via SSML).
- **Streaming:** SDK streaming (real-time synthesis). REST API supports SSML with streaming.
- **Latency:** ~300-500ms TTFB.
- **Pricing:** 
  - Neural TTS: ~$16/1M chars (prebuilt, non-HD)
  - Neural HD: higher (check pricing page)
  - Custom Neural Voice: $24/1M chars; training: $52/hr; hosting: $4.04/model/hr
  - Free tier: 0.5M chars/month
  - Source: [azure.microsoft.com/en-us/pricing/details/speech/](https://azure.microsoft.com/en-us/pricing/details/speech/) (retrieved 2026-06-24)
- **SSML:** Full support (prosody, emphasis, pronunciation, lexicon, multispeaker, viseme).
- **Voice cloning:** Custom Neural Voice (professional voice talent required) and Personal Voice (short samples).
- **Auth:** Azure AI Services key or Entra token.
- **Benchmark criterion:** $/hr: ~$1.60/hr (Neural, 150 wpm); native id-ID voices; full SSML.

#### Cartesia Sonic 3.5

- **Voices:** 42 languages including Indonesian. Voice library has multilingual voices with native quality. Source: [docs.cartesia.ai](https://docs.cartesia.ai/build-with-cartesia/tts-models/latest) (retrieved 2026-06-24)
- **Indonesian quality:** Yes — "42 languages out of the box — English, Hindi, Spanish, French, German, Japanese, Hebrew, and 35 more, each at native quality." Indonesian is included in the 42 languages.
- **Streaming:** WebSocket streaming with continuations and concurrent contexts. 40ms time-to-first-audio claimed. Source: [cartesia.ai/product/python-text-to-speech-api-tts/](https://www.cartesia.ai/product/python-text-to-speech-api-tts/) (retrieved 2026-06-24)
- **Latency:** Sonic 3.5: 188ms p50 TTFA (Coval benchmark). Sonic-3: 100ms claimed TTFB. Source: [gradium.ai](https://gradium.ai/content/best-text-to-speech-apis-2026) (retrieved 2026-06-24)
- **Pricing:**
  - Free: $0/mo (20K chars)
  - Pro: $4/mo (100K credits)
  - Startup: $39/mo (1.25M credits)
  - Scale: $239/mo (8M credits)
  - TTS: 1 credit/char standard; Pro Voice Cloning: 1.5 credits/char
  - Source: [cartesia.ai/pricing](https://www.cartesia.ai/pricing) and [eesel.ai](https://www.eesel.ai/blog/cartesia-sonic-3-pricing) (retrieved 2026-06-24)
- **SSML:** Not traditional SSML. Pronunciation dictionaries and inline phoneme overrides available.
- **Voice cloning:** Instant (10 seconds audio). Pro Voice Cloning (higher quality).
- **Auth:** API key (Bearer token in header, or short-lived token in query param for WebSocket).
- **Python SDK:** Official `cartesia` package on PyPI with websocket support. Source: [github.com/cartesia-ai/cartesia-python](https://github.com/cartesia-ai/cartesia-python) (retrieved 2026-06-24)
- **Benchmark criterion:** Latency: 40-188ms TTFA (fastest cloud TTS); $/hr: ~$1.50/hr (1M chars/Pro plan); Indonesian quality: native; best for real-time voice agents.

### 2.3 Realtime/Streaming Voice APIs (Bidirectional Audio)

#### OpenAI Realtime API (gpt-realtime, gpt-realtime-mini)

- **Transport:** WebRTC (recommended for browser/mobile), WebSocket (server pipelines), SIP (telephony, beta). Source: [platform.openai.com/docs/guides/realtime-webrtc](https://platform.openai.com/docs/guides/realtime-webrtc) (retrieved 2026-06-24)
- **Models:** gpt-realtime (GA), gpt-realtime-mini (cost-optimized), gpt-realtime-whisper (streaming STT only), gpt-realtime-translate (live translation)
- **Language:** Multilingual speech-to-speech. Follows GPT model language coverage (broad).
- **Interruption/Barge-in:** Built-in VAD with configurable thresholds. Server-side turn detection. Client can also send `input_audio_buffer.clear` to interrupt.
- **Function calling:** Supported. Tools can be defined; the model decides when to call them mid-conversation.
- **Pricing:**
  - gpt-realtime: $32/1M audio input tokens + $64/1M audio output tokens
  - gpt-realtime-mini: substantially lower (specific pricing not broken out separately on public page)
  - Approximately $0.18-0.24/min for gpt-realtime; ~$0.06-0.10/min for mini. Source: [forasoft.com](https://www.forasoft.com/blog/article/openai-realtime-api-webrtc-sip-websockets-integration) (retrieved 2026-06-24)
  - Additional transcription (if enabled): charges for whisper-1 or gpt-4o-transcribe per minute
- **Auth:** API key (server-side). Ephemeral tokens for client-side WebRTC via REST endpoint.
- **Benchmark criterion:** ~$10.80-14.40/hr (gpt-realtime); ~$3.60-6.00/hr (mini); latency: <150ms speech-to-speech; function calling and reasoning built in.

#### Deepgram Voice Agent API

- **Transport:** WebSocket (single connection for STT+TTS+LLM orchestration). Source: [developers.deepgram.com/docs/voice-agent](https://developers.deepgram.com/docs/voice-agent) (retrieved 2026-06-24)
- **Interruption/Barge-in:** Built-in barge-in detection, turn-taking prediction, mid-session control. Source: [deepgram.com/product/voice-agent-api](https://deepgram.com/product/voice-agent-api)
- **Function calling:** Yes — client-side and server-side function execution.
- **Bring-your-own model:** Can use own LLM (e.g., OpenAI, Anthropic via liteLLM) or Deepgram-hosted.
- **Pricing:** $0.075/min ($4.50/hr) for Standard tier. BYO LLM/TTS reduces bill. 24% cheaper than ElevenLabs Conversational AI, 75% cheaper than OpenAI Realtime API. Source: [deepgram.com/learn/voice-agent-api-generally-available](https://deepgram.com/learn/voice-agent-api-generally-available) (retrieved 2026-06-24)
- **Free credits:** $200.
- **Auth:** API key or JWT token.
- **Indonesian STT:** Yes (via Nova-3 Multilingual). **TTS:** No Indonesian voice in Aura. Must BYO TTS.
- **Benchmark criterion:** $4.50/hr (includes STT+TTS+LLM orchestration); VAD + EOT integrated; sub-300ms streaming.

#### ElevenLabs Conversational AI (ElevenAgents)

- **Transport:** WebSocket or WebRTC. Source: [elevenlabs.io/blog/conversational-ai-webrtc](https://elevenlabs.io/blog/conversational-ai-webrtc) (retrieved 2026-06-24)
- **Interruption/Barge-in:** Built-in. Real-time detection of pauses, overlaps, speech intent. Activity ping prevents premature interruption. Agents know when to listen vs. speak.
- **Function calling:** Yes, via MCP (Model Context Protocol) tool calls.
- **Pricing:** $0.10-0.20/min ($6-12/hr). 95% discount on silence >10 seconds. LLM costs passed through separately (external LLM provider billed directly). Source: [elevenlabs.io/pricing/agents](https://elevenlabs.io/pricing/agents) and [elevenlabs.io/blog/we-cut-our-pricing-for-conversational-ai](https://elevenlabs.io/blog/we-cut-our-pricing-for-conversational-ai) (retrieved 2026-06-24)
- **Indonesian STT:** Yes (Scribe v2 supports 90+ languages). **TTS:** Yes, via Multilingual v2 including Indonesian.
- **Auth:** API key (server-side). Signed URLs for client-side. Conversation tokens for WebRTC.
- **Python SDK:** Available. React SDK also available.
- **Benchmark criterion:** $6-12/hr; Indonesian support: strong (native TTS + Scribe STT); latency: ~400-600ms end-to-end.

#### Cartesia Line (Voice Agents)

- **Transport:** WebSocket. Source: [cartesia.ai/agents/](https://www.cartesia.ai/agents/) (retrieved 2026-06-24)
- **Models:** Sonic (TTS), Ink (STT), Line (agent orchestration). Full vertically-owned stack.
- **Interruption:** Supported through Sonic TTS contexts.
- **Pricing:** Credit-based. Free tier available. Startup: $39/mo (1.25M TTS credits + $49 prepaid agent minutes). Source: [cartesia.ai/pricing](https://www.cartesia.ai/pricing) (retrieved 2026-06-24)
- **Indonesian:** TTS: Yes (Sonic 3.5 has id). **STT (Ink):** Limited (primarily English). Not suitable as standalone STT for id.
- **Auth:** API key + short-lived tokens for WebSocket.
- **Benchmark criterion:** 40-188ms TTFA (Sonic 3.5); ~$39/mo base; limited STT language support.

---

## 3. Audio Codec / Format Facts

### Discord Voice Architecture

- **Discord voice uses Opus codec natively at 48kHz.** Source: [discordpy.readthedocs.io](https://discordpy.readthedocs.io/en/latest/api.html) (retrieved 2026-06-24)
- **discord.py** expects either Opus packets (20ms frames) OR PCM 16-bit 48kHz stereo (3,840 bytes per 20ms frame). If `is_opus()` returns True, the audio source must return Opus-encoded data; otherwise PCM.
- **Receiving audio:** Discord transmits Opus packets. Decode to PCM (16-bit signed, little-endian, 48kHz, stereo) for STT processing.
- **Sending audio:** Must be Opus-encoded PCM or raw PCM that discord.py will encode. FFmpegPCMAudio handles conversion from many formats. FFmpegOpusAudio skips re-encoding.
- **FFmpeg required** for format conversion in discord.py voice pipeline.

### Codec/Format Requirements by Provider

| Provider | Input (STT) | Output (TTS) | Transcoding Needed for Discord |
|---|---|---|---|
| OpenAI Whisper API | mp3, wav, mp4, m4a, webm, opus, flac, wma, ogg | mp3, opus, aac, flac, wav, pcm | STT: opus direct; TTS: opus or wav -> discord.py PCM |
| Deepgram | PCM 8/16kHz, mulaw, opus, webm, mp3 | PCM (raw/s16le), opus | STT: decode opus->PCM 16kHz mono; TTS: PCM 48kHz stereo needed |
| AssemblyAI | wav, mp3, m4a, ogg, webm, opus, flac | N/A (STT only) | STT: decode opus->PCM |
| Google Cloud STT | wav, flac, opus, mp3 (v2), webm | N/A | STT: decode opus->PCM 16kHz mono |
| Azure STT | wav, mp3, opus, ogg | N/A | STT: decode opus |
| Google TTS | N/A | mp3, wav, ogg (Opus) | TTS: ogg/Opus direct, or wav->PCM 48kHz |
| Azure TTS | N/A | mp3, wav, ogg, pcm | TTS: PCM format available |
| ElevenLabs TTS | N/A | mp3, wav, pcm, mulaw | TTS: pcm_16000 (WebSocket) -> upsample to 48kHz stereo |
| Cartesia Sonic | N/A | wav, pcm, raw (configurable format/sample rate) | TTS: pcm_s16le at 48kHz (native Discord match) |

**Key insight:** Most STT providers expect 16kHz mono PCM as the optimal input format. Discord audio at 48kHz stereo PCM must be downmixed to mono and resampled to 16kHz. Opus decode -> PCM -> resample/remix -> STT provider.

For TTS to Discord: synthesize at any sample rate, resample to 48kHz stereo PCM, then FFmpegPCMAudio or custom Opus encoding for playback.

---

## 4. Wake-word / VAD Options

| Solution | Type | License | Offline | Latency | Notes |
|---|---|---|---|---|---|
| **WebRTC VAD** | VAD (signal processing) | BSD (open-source) | Yes (no model, just GMM) | <1ms | Google's open-source VAD. Extremely lightweight. Binary speech/silence. Lower accuracy in noise. Built into browsers. |
| **Silero VAD** | VAD (deep learning) | MIT | Yes (ONNX model ~1.7MB) | ~10ms | Higher accuracy than WebRTC VAD, especially in noise. Requires PyTorch or ONNX runtime. Pre-trained for 16kHz/8kHz. |
| **Picovoice Cobra** | VAD (deep learning) | Proprietary | Yes | Low | Picovoice's VAD. Deep learning accuracy with on-device performance. Production-ready. Priced per platform. |
| **openWakeWord** | Wake-word detection | Apache 2.0 | Yes | Low (RPi3 runs 15-20 models) | Open-source wake-word engine. ONNX-based. Custom training pipeline. More accurate than Porcupine on benchmark. Python package available. |
| **Picovoice Porcupine** | Wake-word detection | Proprietary (free tier, enterprise $6K+/yr) | Yes | Sub-100ms | Industry standard. Ready-built wake words ("Hey Google", "Alexa") plus custom training. Python SDK. |
| **Deepgram Flux** | VAD + EOT (built into STT) | Proprietary | No | ~260ms EOT | Integrated end-of-turn detection in Deepgram's Flux model. No separate VAD needed. Saves 200-600ms vs external VAD. |

**Recommendations for Guinevere:**
- **Push-to-talk (PTT) mode:** No VAD needed. User presses a key -> stream starts -> key release -> finalize -> process.
- **Always-listening:** Use Silero VAD (free, offline, accurate) for voice activity detection + openWakeWord for wake-word ("Mommy" or "Guinevere"). Both are free, open-source, and run offline on the VPS.
- **Cloud alternative:** Deepgram Flux (if using Deepgram STT) — integrated EOT eliminates separate VAD and improves latency.

---

## 5. Local/Offline Fallback Chain

### STT Offline: faster-whisper

- **faster-whisper** (MIT license, pip installable) is the recommended local STT engine.
- **Models:** large-v3 (best accuracy, 2.9GB), large-v3-turbo (faster, slightly less accurate), medium, small, tiny.
- **Indonesian:** Supported (99 languages). large-v3 multilingual WER comparable to cloud STT on clean audio (~8-12% id WER).
- **Performance:** On VPS with NVIDIA GPU (RTX 3090): large-v3 ~12.9x realtime (60 min file in ~4min40s). On CPU: slower but feasible with tiny/base model.
- **INT8 quantization** reduces memory footprint by ~50% with minimal accuracy loss.
- **Alternative:** whisper.cpp (C++ port, better for CPU/Apple Silicon, same models).

### TTS Offline: Piper + Kokoro

- **Piper** (MIT license): **Has Indonesian news_tts voice.** Very small footprint (<100MB model). Runs on CPU (Raspberry Pi 4 capable). Near real-time speed. Native Indonesian voice available. GitHub: [github.com/rhasspy/piper](https://github.com/rhasspy/piper) (VOICES.md lists id_ID).
- **Kokoro** (Apache 2.0): 82M params, #1 on TTS Arena (Jan 2026). 300MB file, runs on CPU. **Does NOT support Indonesian** — only EN, FR, KO, JA, ZH-CN. Not suitable as primary offline TTS for id.

### Fallback Chain Strategy

```
Primary (online): 
  STT: Deepgram Nova-3 Multilingual (Indonesian) or Google Chirp 3 (cost-sensitive)
  TTS: Google Neural2 id-ID or Cartesia Sonic 3.5 (lowest latency)
  Realtime: OpenAI gpt-realtime-mini or Deepgram Voice Agent API

Fallback 1 (cost ceiling hit / credit exhaustion):
  STT: Google Chirp 3 ($0.016/min, 60 min free/mo remaining)
  TTS: Google WaveNet id-ID ($4/1M chars, 1M free/mo)

Fallback 2 (API outage):
  STT: Deepgram Nova-3 (different provider from fallback 1)
  TTS: Cartesia Sonic 3.5 (different provider)

Fallback 3 (complete cloud outage / privacy-sensitive):
  STT: faster-whisper large-v3-turbo (local, no network)
  TTS: Piper id-id news_tts voice (local, no network)

Fallback 4 (resource-constrained / VPS under load):
  STT: faster-whisper tiny (lightweight, CPU-only)
  TTS: Piper tiny voice
```

**Trigger conditions for local fallback:**
- VPS network outage (no internet connectivity to API endpoints)
- Cloud provider API returning 5xx errors or rate-limit exhaustion
- Privacy-sensitive content (user explicitly requests local-only processing)
- Cost ceiling reached (monthly budget exhausted for cloud APIs)
- Latency-sensitive operation where local inference is competitive

---

## 6. Benchmark Criteria for Planner Scoring

| Criterion | Description | Provider where best |
|---|---|---|
| **STT streaming latency p50** | Time from speech end to finalized transcript | Deepgram Nova-3: sub-300ms; OpenAI Realtime: sub-150ms |
| **STT streaming latency p95** | Tail latency for worst-case utterances | Deepgram Flux: ~260ms EOT |
| **$/hr active listening** | Cost per hour of streaming transcription | Deepgram Nova-3 Mono: $0.29/hr; Google Dynamic Batch: $0.24/hr |
| **Indonesian WER** | Word Error Rate on id-ID speech | Cloud (all): ~7-12%; Local faster-whisper: ~8-15% |
| **Code-switching quality** | Accuracy on mixed id+en sentences | Deepgram Nova-3 Multilingual; Google Chirp 3 |
| **TTS TTFA p50** | Time to first audio for response | Cartesia Sonic 3.5: 188ms; Deepgram Aura-2: 313ms |
| **TTS Indonesian naturalness** | Blind preference test score for id-ID | Google Neural2 id-ID; Cartesia Sonic 3.5; ElevenLabs (cloned) |
| **TTS $/hr** | Cost per hour of synthesized speech | OpenAI tts-1: $0.74/hr; Google WaveNet: $1.49/hr |
| **E2E latency (PTT)** | PTT press -> response audio in Discord | Deepgram VOIP: ~1s target; Realtime API: sub-1s |
| **Streaming interruption latency** | Time from user interrupt to TTS stop | OpenAI Realtime: native; Deepgram VAPI: built-in |
| **Local fallback feasibility** | Can run fully offline on VPS | faster-whisper + Piper: Yes (no GPU required for Piper) |
| **Existing Hermes integration fit** | How well text goes through Hermes pipeline | All STT produces text -> same pipeline = no differentiation needed |

---

## 7. Design Options for the Planner

### Option A: Best-of-breed cloud (recommended for primary)

- **STT:** Deepgram Nova-3 Multilingual ($0.0058/min streaming) — best Indonesian support, sub-300ms latency, integrated EOT via Flux
- **TTS:** Cartesia Sonic 3.5 (~1 credit/char, 40ms TTFA) — native Indonesian, fastest TTS, Python SDK, WebSocket streaming
- **Realtime:** Deepgram Voice Agent API ($4.50/hr) or OpenAI Realtime Mini for speech-to-speech (if full speech-to-speech wanted)
- **VAD:** Silero VAD (offline, free, accurate) for always-listening; Flux EOT for stream endpointing
- **Wake-word:** openWakeWord (free, offline, more accurate than Porcupine)
- **Total cost estimate:** ~$0.35/hr STT + ~$1.50/hr TTS = ~$1.85/hr for active conversation

### Option B: Google-native (cost-sensitive)

- **STT:** Google Chirp 3 ($0.016/min streaming, 60 min free/mo)
- **TTS:** Google WaveNet id-ID ($4/1M chars, 1M free/mo)
- **VAD:** WebRTC VAD (free, no dependencies)
- **Total cost:** $0.96/hr STT + $0/hr TTS (under 1M chars) = $0.96/hr
- **Downside:** Higher STT latency than Deepgram, higher TTS latency than Cartesia

### Option C: OpenAI-native (simplest integration)

- **STT:** gpt-4o-mini-transcribe ($0.003/min batch) for PTT; gpt-realtime-whisper ($0.017/min streaming) for live
- **TTS:** gpt-4o-mini-tts (~$0.015/min) for steerable prosody
- **Realtime:** gpt-realtime-mini (~$0.06-0.10/min) for full speech-to-speech
- **Total cost:** $0.18/hr STT + $0.90/hr TTS = ~$1.08/hr (or $3.60-6.00/hr realtime)
- **Downside:** No native Indonesian TTS voices; no voice cloning; batch-only STT

### Option D: ElevenLabs (best voice quality)

- **STT:** Scribe v2 (90+ languages incl. id) 
- **TTS:** ElevenLabs Multilingual v2 with cloned consented Indonesian voice
- **Conversational AI:** ElevenAgents ($0.10-0.20/min)
- **Total cost:** ~$10.20/hr overage (expensive for high volume)
- **Upside:** Best Indonesian TTS if voice-cloned; single-provider stack

### Option E: Offline-only (privacy/cost ceiling)

- **STT:** faster-whisper large-v3-turbo (local, $0/run)
- **TTS:** Piper id-id news_tts voice (local, $0/run)
- **VAD:** Silero VAD + openWakeWord (both local, free)
- **Total cost:** $0.00/hr (VPS electricity only)
- **Downside:** Lower TTS quality than cloud; requires GPU for real-time STT

### Key Integration Note

**Voice transcript = text.** The HARD STOP handler, prompt injection sanitizer, distress detector, safe-mode controller, and all safety logic operate on TEXT. This means regardless of which STT provider is chosen, the transcript output feeds directly into the existing `handle_conversation()` pipeline unchanged. No safety logic needs to be reimplemented for voice. The existing `HermesConversational.handle_conversation()` should be the target for STT transcript text; the pipeline already handles rate limiting, distress detection, mood, memory recall, system prompt assembly, LLM calling, and response chunking.

---

## Sources (retrieved 2026-06-24)

1. OpenAI Speech-to-Text API docs: https://developers.openai.com/api/docs/guides/speech-to-text
2. OpenAI API pricing: https://openai.com/api/pricing/
3. OpenAI Whisper model: https://developers.openai.com/api/docs/models/whisper-1
4. OpenAI TTS guide: https://platform.openai.com/docs/guides/text-to-speech
5. OpenAI Realtime API guide: https://platform.openai.com/docs/guides/realtime
6. OpenAI Realtime WebRTC: https://platform.openai.com/docs/guides/realtime-webrtc
7. OpenAI gpt-realtime model: https://developers.openai.com/api/docs/models/gpt-realtime
8. OpenAI GPT-4o mini TTS: https://platform.openai.com/docs/models/gpt-4o-mini-tts
9. OpenAI updates blog: https://developers.openai.com/blog/updates-audio-models
10. Deepgram pricing: https://deepgram.com/pricing
11. Deepgram STT Indonesian: https://deepgram.com/product/speech-to-text/indonesian
12. Deepgram Voice Agent: https://deepgram.com/product/voice-agent-api
13. Deepgram Aura TTS: https://deepgram.com/product/text-to-speech
14. Deepgram Aura-2 languages: https://deepgram.com/learn/aura-2-now-speaks-dutch-french-german-italian-japanese
15. Deepgram STT learning center: https://deepgram.com/learn/best-speech-to-text-apis-2026
16. Deepgram Aura-2 latency: https://deepgram.com/learn/best-text-to-speech-apis-2026
17. Deepgram Voice Agent pricing comparison: https://deepgram.com/learn/voice-agent-api-generally-available
18. Deepgram TTS models docs: https://developers.deepgram.com/docs/tts-models
19. AssemblyAI pricing: https://www.assemblyai.com/pricing
20. AssemblyAI STT product: https://www.assemblyai.com/products/speech-to-text
21. AssemblyAI streaming: https://www.assemblyai.com/products/streaming-speech-to-text
22. Google Cloud STT pricing: https://cloud.google.com/speech-to-text/pricing
23. Google Cloud TTS pricing: https://cloud.google.com/text-to-speech/pricing
24. Google STT overview: https://docs.cloud.google.com/speech-to-text/docs/overview
25. Google STT Chirp 3: https://docs.cloud.google.com/speech-to-text/docs/models/chirp-3
26. Google TTS voices: https://cloud.google.com/text-to-speech/docs/voices
27. Google TTS streaming: https://docs.cloud.google.com/text-to-speech/docs/create-audio-text-streaming
28. Azure Speech pricing: https://azure.microsoft.com/en-us/pricing/details/speech/
29. Azure STT overview: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-to-text
30. Azure TTS overview: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/text-to-speech
31. Azure language support: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support
32. ElevenLabs pricing: https://elevenlabs.io/pricing
33. ElevenLabs Agents pricing: https://elevenlabs.io/pricing/agents
34. ElevenLabs voice cloning: https://elevenlabs.io/voice-cloning
35. ElevenLabs WebSocket: https://elevenlabs.io/docs/eleven-agents/libraries/web-sockets
36. ElevenLabs WebRTC: https://elevenlabs.io/blog/conversational-ai-webrtc
37. ElevenLabs Conversational AI pricing cut: https://elevenlabs.io/blog/we-cut-our-pricing-for-conversational-ai
38. ElevenLabs Terms (consent): https://elevenlabs.io/terms-of-use
39. Cartesia pricing: https://www.cartesia.ai/pricing
40. Cartesia Sonic: https://www.cartesia.ai/sonic/
41. Cartesia Sonic 3.5 docs: https://docs.cartesia.ai/build-with-cartesia/tts-models/latest
42. Cartesia Python SDK: https://github.com/cartesia-ai/cartesia-python
43. Cartesia TTS WebSocket API: https://docs.cartesia.ai/api-reference/tts/websocket
44. faster-whisper guide: https://localaimaster.com/blog/faster-whisper-guide
45. Piper GitHub: https://github.com/rhasspy/piper
46. Piper id-ID voice commit: https://huggingface.co/rhasspy/piper-voices/commit/67265bba2397cfb86ff687cfc7ffe3a0e3c3aa55
47. Kokoro-82M: https://huggingface.co/hexgrad/Kokoro-82M
48. openWakeWord GitHub: https://github.com/dscripka/openWakeWord
49. Picovoice VAD comparison: https://picovoice.ai/blog/best-voice-activity-detection-vad/
50. Silero VAD + WebRTC VAD: https://picovoice.ai/blog/python-speech-recognition/
51. discord.py voice API: https://discordpy.readthedocs.io/en/latest/api.html
52. Discord audio guide: https://v12.discordjs.guide/voice/understanding-voice.html
53. Coval.ai STT benchmarks June 2026: https://www.coval.ai/blog/best-speech-to-text-providers-in-2026-independent-benchmarks-and-how-to-choose/
54. OpenAI Realtime pricing breakdown: https://hackernoon.com/openai-realtime-api-pricing-in-2026-real-world-data-from-4000-measured-sessions
55. OpenAI TTS vs competitors: https://texttolab.com/blog/openai-tts-pricing
56. Deepgram pricing 2026 breakdown: https://diyai.io/ai-tools/speech-to-text/deepgram-pricing-2026/
57. Google STT 2026 review: https://diyai.io/ai-tools/speech-to-text/reviews/google-speech-to-text-review/
58. Azure STT pricing Q&A: https://learn.microsoft.com/en-us/answers/questions/2155625/speech-to-text-costing-1-hr-is-crazy-no-bulk-avail
