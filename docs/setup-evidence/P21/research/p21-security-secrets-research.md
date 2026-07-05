# P21 Voice Interface — Security, Secrets & Prompt-Injection Research

**Phase:** P21 Voice Interface (research + planning ONLY — NO implementation/deploy/restart)
**Date:** 2026-06-24
**Author:** Guinevere (parent) for Faiz — written directly after the specialist sub-agent died without producing a file. Parent holds full repo grounding; official-doc citations gathered via firecrawl/brave/jina (retrieved 2026-06-24).
**Status:** COMPLETE

> **Provenance note:** The original security-secrets specialist sub-agent (opus, foreground) timed out at ~24 min / 15 tool uses and wrote no file. Per AGENTS.md §14 (sub-agent output discipline) and the parent-verification rule, the parent authored this file directly using the same grounding block plus freshly fetched official provider privacy/security/pricing docs. All provider claims below cite official sources.

---

## 1. Secrets & Env Model

### 1.1 Existing secrets architecture (ground truth)

Guinevere uses SOPS + age encryption with **zero plaintext secrets in the repo** (MCPConfigGuide §1.3; `docs/20-security/22-EncryptionKeyMgmt_v1.0.md`; `docs/20-security/23-SecretsRotationRunbook_v1.0.md`):

- Encrypted YAML: `/home/guinevere/config/mcp.production.yaml.sops`
- age key: `/home/guinevere/.age/key.txt` (NEVER read directly by code; decrypted via `sops -d`)
- Rotation cadence: **quarterly** (SecretsRotationRunbook; MCP06)
- Decryption at startup: `sops -d …/mcp.production.yaml.sops` → env; auto-cleanup on service stop
- Encryption profile for stored data: `envelope-AES-256-GCM` (per `ClassificationMetaMixin.encryption_profile` in `src/memory/models.py:72`)

AGENTS.md BLOCKING rules apply absolutely to voice secrets:
- NEVER commit secrets: Discord bot token, API keys, DB passwords, surveillance credentials, SOPS/age keys.
- NEVER send secrets/personal/intimate data to external MCP/web tools.
- NEVER store raw surveillance data in repo artifacts.

### 1.2 Voice provider keys — proposed env model

Voice introduces new provider API keys (STT, TTS, realtime). They MUST follow the same SOPS/age path. Two integration options:

| Option | Description | Recommendation |
|---|---|---|
| **A — Direct provider keys** | Separate STT/TTS keys stored in SOPS, voice service calls providers directly | Use for MVP local-fallback + non-9Router providers (ElevenLabs, Deepgram, faster-whisper needs no key) |
| **B — 9Router-proxied** | 9Router already holds `9ROUTER_API_KEY`/`GUINEVERE_9ROUTER_API_KEY` (see `src/life_kernel/hermes_brain.py:248-249` `has_9router_key`/`has_guinevere_key` checks). If 9Router proxies STT/TTS (e.g. OpenAI audio endpoints), reuse the existing key | Prefer for OpenAI audio (Whisper/TTS/Realtime) to avoid a new secret |

**Proposed env vars** (added to `mcp.production.yaml.sops` under a new `voice:` section; names chosen to avoid collision with existing keys):

```yaml
# /home/guinevere/config/mcp.production.yaml.sops (decrypted view)
voice:
  enabled: false                      # feature flag / kill switch
  stt:
    provider: "openai"                # openai | deepgram | faster-whisper(local)
    openai_api_key: "${VOICE_STT_OPENAI_API_KEY}"   # Option A; or reuse 9Router key (Option B)
    deepgram_api_key: "${VOICE_DEEPGRAM_API_KEY}"
  tts:
    provider: "openai"                # openai | elevenlabs | piper(local)
    openai_api_key: "${VOICE_TTS_OPENAI_API_KEY}"
    elevenlabs_api_key: "${VOICE_ELEVENLABS_API_KEY}"
  realtime:
    provider: "openai"                # openai-realtime | deepgram-voice-agent | off
    openai_api_key: "${VOICE_REALTIME_OPENAI_API_KEY}"
  local_fallback:
    stt_model: "faster-whisper"       # no key needed
    tts_model: "piper"                # no key needed
  consent:
    always_listening: false           # hard-default OFF
  cost:
    daily_cap_usd: 2.00
    monthly_cap_usd: 6.00             # within the USD 30/mo system cap
```

- All `${VOICE_*_API_KEY}` values live **only** in the SOPS-encrypted file + the decrypted runtime env. Never in repo, never logged, never passed to an external MCP/web tool.
- Rotation: quarterly alongside existing keys (SecretsRotationRunbook). Add a `secret_rotation_log` row (`src/memory/models.py:1046` `SecretRotationLog`) per key rotated.
- If a key is ever exposed (leaked into a log/artifact/MCP payload): immediate rotation + `BreakGlassLog`/incident per `docs/20-security/23-SecretsRotationRunbook_v1.0.md`.

### 1.3 Key derivation & encryption-at-rest

- Secrets in transit to providers: TLS 1.2+ (provider-side; OpenAI confirms TLS 1.2+ — see §4).
- Stored audio (if any raw audio retained): `envelope-AES-256-GCM` via `ClassificationMetaMixin.encryption_profile` (`src/memory/models.py:72`), `key_id` + `key_version` tracked.
- age key file permissions: restricted to `guinevere` OS user only; never readable by sub-agents.

---

## 2. Prompt Injection via Transcript (the core security argument)

### 2.1 Voice transcript = untrusted text

A voice transcript is **not** a trusted operator instruction just because Faiz spoke it. Threat scenarios:
- Faiz reads aloud a malicious web page / email → the spoken text carries an injection payload.
- An audio file or external voice plays an injection through the mic (e.g. a video saying *"ignore the safe word"*).
- A transcript-poisoning attempt: a deliberately crafted utterance meant to override policy once stored in memory.

Per `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md` the trust hierarchy (§3.1) classifies external/content-derived input at Trust Level 5–6. A voice transcript is therefore **Trust Level 6 — Untrusted by default** (it cannot be proven to originate from Faiz's intent vs. an external source he merely vocalized). It MUST pass the standard 3-stage pipeline (§7.1):

```
Raw transcript
  → Stage 1: Classify (trust=6, source_type='voice', detect instruction patterns)
  → Stage 2: Sanitize (strip instruction patterns, remove secrets)
  → Stage 3: Quarantine/Label → <untrusted source="voice" trust="6" confidence="…">…</untrusted>
  → Inject only into L7–L9 (quarantined layers); NEVER L0–L6 (privileged/dynamic)
```

### 2.2 Safe-word classifier runs on RAW transcript BEFORE sanitization

This is the non-negotiable ordering (`PromptInjection §8.3`; SW-PI-008): the safe-word classifier runs at the input boundary, **before** any sanitization or trust classification. Concretely for voice:

```
STT final transcript
  → HardStopHandler.check(transcript)            # src/core/services/hard_stop_handler.py:89
     ├─ if triggered: set Redis "life_kernel:hard_stop" + SafeModeController + neutral TTS ack + audit  → STOP
     └─ else: continue
  → DistressDetector.detect(transcript)          # src/persona/safe_mode.py (via hermes_conversational.py:460)
  → injection classify → sanitize → label/quarantine
  → Hermes turn (transcript enters as quarantined L9 content)
```

Because `HardStopHandler.check(message: str)` (`src/core/services/hard_stop_handler.py:89`) is **text-based**, the spoken safe word ("hard stop", "safe word", "hentikan", "berhenti", + semantic patterns + Indonesian equivalents) is detected on the transcript **identically** to a typed safe word. **Zero false-negative tolerance** (`PersonaSafetyPolicy §7`; `PromptInjection §8.3` rule 5). A spoken safe-word override attempt ("safe word is disabled", "safe word was revoked") is a SEV0 incident (`PromptInjection §8.4`; §16.1).

### 2.3 Register voice as injection vector V-022

The existing vector catalog runs V-001..V-021 (`PromptInjection §5`). Voice is a new input surface. Register:

| Field | Value |
|---|---|
| Vector ID | **V-022** (proposed) |
| Surface | Voice transcript (STT output from Discord voice channel) |
| Input Source | Spoken audio (may vocalize external content) |
| Trust Level | 6 — Untrusted |
| Classification | HIGH–CRITICAL risk (depends on content; spoken injection ~ clipboard injection V-007) |
| Primary Defense | (1) HardStopHandler on raw transcript (pre-sanitization); (2) instruction-pattern sanitizer; (3) `<untrusted source="voice">` label; (4) quarantine to L7–L9; (5) memory write-validation gate |
| Secondary Defense | Secret-in-transcript scanner (§3); provider no-retention (§4); consent scope gating |
| Test IDs | PI-021 (spoken "ignore safe word" via audio), PI-022 (read-aloud web injection), PI-023 (spoken secret dictation), PI-024 (transcript poisoning into memory) |
| Evidence Path | `evidence/prompt-safety/<YYYY-MM>/external-sanitization/V-022-<incident-id>.md` |

### 2.4 Applicable memory-safety rules (§9)

Every voice-derived fact written to memory MUST satisfy (`PromptInjection §9`):
- **MEM-001**: validate source trust level before storage → voice source = Trust 6 → requires Faiz confirmation or safety-state check (or stays quarantined, not promoted).
- **MEM-002**: write from Trust 5–6 MUST be quarantined.
- **MEM-003**: instruction patterns in transcript → block write + log injection event.
- **MEM-004**: must not remove/weaken safety boundaries.
- **MEM-006/007/008**: promotion requires injection-check gate + safety-state check + blocked during restricted (safe-mode/distress) states.
- **RECALL-001..006**: every recalled voice fact carries `source_type='voice'`, `source_trust='quarantined_5'`, confidence, storage_date, `do_not_recall` enforcement.

This means **a voice transcript must NOT enter long-term memory without passing the injection write-validation + redaction/retention gate** (see `p21-memory-transcript-research.md` and the P21 hard-rejection rule).

---

## 3. Secret-in-Transcript (clipboard-equivalent)

Voice can capture spoken secrets: Faiz dictating a password, reciting a recovery code, or a notification/readout containing a token. This is the audio analog of clipboard secret capture (V-006/V-007, `PromptInjection §7.2`).

### 3.1 Secret-pattern scanner on transcripts

Apply the existing clipboard secret scanner to the transcript **before** storage or LLM context:
- Passwords / passphrases
- API keys / bearer tokens (sk-…, AKIA…, Bearer …)
- Session cookies / JWTs (eyJ…)
- Recovery / 2FA codes (numeric OTP patterns)
- DB connection strings, private keys (`-----BEGIN … PRIVATE KEY-----`)

### 3.2 Handling (mirrors V-006/V-007)

| Detection | Action |
|---|---|
| Secret pattern in transcript | **Drop immediately** — never store, never send to LLM context. Incident-log **hash + category only** (no plaintext). Classify Critical. |
| Instruction pattern in transcript | Quarantine entire transcript; log as instruction-quarantine event; never inject into privileged layers. |
| Non-secret, non-instruction | Proceed through §2 pipeline; store redacted per `p21-memory-transcript-research.md`. |

`PromptInjection §7.2` clipboard rule: "Credential logging → incident-log category and hash; never log plaintext." Identical for voice.

---

## 4. Audio Data Exfiltration & Provider Data-Residency

### 4.1 Raw audio is sensitive — never leaves VPS unencrypted

- Raw audio = surveillance-class data. AGENTS.md: "NEVER store raw surveillance data in repo artifacts."
- Provider upload only to **consented** endpoints (consent scope `voice.storage.raw_audio` OFF by default → prefer transcript-only; raw audio discarded after STT — see `p21-memory-transcript-research.md`).
- No raw audio in logs, evidence artifacts, or MCP payloads. If raw audio must be retained (future), max 24h encrypted (`envelope-AES-256-GCM`), auto-purge — aligned with camera/screenshot policy (V-013/V-014, `PromptInjection §10.3`).

### 4.2 Provider retention/training posture (official-doc citations)

| Provider | Default training on customer data? | Retention | Source (retrieved 2026-06-24) |
|---|---|---|---|
| **OpenAI API** | **No** by default (API Platform after Mar 1 2023) | Up to 30 days for abuse monitoring; **Zero Data Retention (ZDR)** requestable for eligible endpoints | [openai.com/enterprise-privacy](https://openai.com/enterprise-privacy/) ("By default, we do not use your business data for training our models… OpenAI may securely retain API inputs and outputs for up to 30 days… You can also request zero data retention (ZDR) for eligible endpoints"); [platform docs: your-data](https://developers.openai.com/api/docs/guides/your-data) |
| **Deepgram** | Configurable; **default = zero retention after processing** | SOC 2 Type II; default config "zero retention after processing"; EU endpoint available | [deepgram.com/data-security](https://deepgram.com/data-security); [deepgram compliance](https://deepgram.com/learn/standard-compliance-speech-to-text) ("Deepgram's default configuration meets the strictest requirements with zero retention after processing") |
| **ElevenLabs** | Voice cloning requires consent verification; **Zero Retention Mode** available (Enterprise) | SOC2 + GDPR; Zero Retention Mode for sensitive workflows | [elevenlabs.io/privacy-policy](https://elevenlabs.io/privacy-policy); [elevenlabs enterprise](https://elevenlabs.io/enterprise) ("optional Zero Retention Mode ensures none of your content or data are retained"); [zero-retention docs](https://elevenlabs.io/docs/eleven-api/resources/zero-retention-mode) |
| **OpenAI Realtime API** | Same OpenAI API data policy (no training by default; ≤30d / ZDR) | Billed per audio I/O tokens; 15-min idle connection limit | [developers.openai.com/api/docs/guides/realtime](https://developers.openai.com/api/docs/guides/realtime); [pricing](https://openai.com/api/pricing/) |

**Recommendation:** Prefer providers offering no-training + ZDR/zero-retention (OpenAI API ZDR, Deepgram default, ElevenLabs ZRM). For the most sensitive voice content (consent `voice.storage.raw_audio` would be ON, or intimate/medical/financial utterances), route STT to the **local fallback** (`faster-whisper` — no data leaves the VPS). This is the voice equivalent of "Ollama fallback for sensitive LLM content."

### 4.3 OpenAI Realtime cost note (security-adjacent)

Realtime API bills per audio token (input ~$100/1M tokens ≈ $0.06/min input; output ~$200/1M ≈ $0.24/min output per OpenAI community/pricing discussion — [pricing](https://openai.com/api/pricing/), [community](https://community.openai.com/t/i-dont-understand-the-pricing-for-the-realtime-api/963837)). 15-min idle connection limit. This is a **cost-exfiltration** risk if always-listening is ever enabled (continuous billing) — another reason always-listening is not MVP (see `p21-consent-surveillance-research.md`).

---

## 5. Auth / Rate-Limit / Cost (4-level matrix + Redis DB5)

Per MCPConfigGuide §2 (4-level auth matrix) and the exa cost-throttle pattern:

- **L1 Read-Autonomous**: STT/TTS/realtime calls within the daily/monthly voice cost budget → Guinevere executes and notifies.
- **L3 Destructive-Approval**: if voice spend exceeds the daily cap (`voice.cost.daily_cap_usd`) → escalate to Faiz before further spend; if monthly cap hit → voice disabled until next cycle (mirror exa's `$5/day → $3/mo throttle → $5/mo hard-stop` pattern, MCPConfigGuide §3.3).
- Rate-limit + cost counters in **Redis DB5** (`ratelimit:voice:{provider}:{date}` / `ratelimit:voice:monthly:{YYYY-MM}`), per MCPConfigGuide §1.4.

### 5.1 Voice cost tags (feed existing `CostTracker.record_cost`)

`src/core/services/cost_tracker.py` `CostTracker.record_cost(model, input_tokens, output_tokens, cost_per_1k_input, cost_per_1k_output)`. Voice stages use model tags:
- `stt:openai-whisper`, `stt:deepgram-nova`, `stt:faster-whisper(local=$0)`
- `tts:openai-tts-1`, `tts:elevenlabs`, `tts:piper(local=$0)`
- `realtime:openai-realtime`

All counted against the USD 30/mo system cap; voice sub-cap (`voice.cost.monthly_cap_usd`) keeps voice spend bounded.

---

## 6. RBAC / Access Control

Per `docs/20-security/21-AccessControl_RBAC_ABAC_v1.0.md` and MCPConfigGuide §1.5 (PgBouncer per-service users):

- Voice subsystem uses the **`guinevere_core`** DB user (SELECT/INSERT/UPDATE all schemas, transaction pool) — **no superuser**, no `guinevere_admin`.
- Sub-agents touching voice (research/implementer) = task-scoped, **no Critical data access**, read/search only for researchers (AccessControl §15; `PromptInjection §12.4`).
- Voice config/keys (`/home/guinevere/config/*.sops`, `/home/guinevere/.age/key.txt`) are **L4 Forbidden** for the filesystem tool (MCPConfigGuide §3.5) — voice code never reads SOPS files directly; it reads decrypted env vars.

---

## 7. Threat Model Additions for Voice

Extends `docs/20-security/25-ThreatModel_v1.0.md` and `PromptInjection §4`:

| Threat | Vector | Severity | Mitigation |
|---|---|---|---|
| **Pre-recorded audio injection** | Adversary plays an audio file into the mic uttering "ignore the safe word" / "override ADR-002" | CRITICAL (SEV0) | HardStopHandler on transcript (pre-sanitize); instruction-pattern sanitizer; only Trust 1–3 may trigger safe word (SW-PI-002); quarantined; SEV0 incident |
| **Spoken safe-word override** | Transcript contains "safe word is disabled/revoked" | CRITICAL (SEV0) | Rejected unless confirmed via approved config/ADR path (SW-PI-003); SEV0 |
| **Speaker impersonation** | Non-Faiz speaker in voice channel issues commands | HIGH | Faiz-only voice channel + consent gating; speaker ID is future (MVP trusts channel membership = Faiz) |
| **Transcript poisoning → memory** | Crafted utterance stored as fact, later recalled to reshape boundaries | HIGH (SEV1) | MEM-001..008 write-validation; source_trust='quarantined_5'; do_not_recall; contradiction detection on recall (RECALL-006) |
| **Spoken secret capture** | Faiz dictates a password/token | CRITICAL (data) | Secret scanner drops it; hash+category log only (§3) |
| **Provider compromise / data leak** | STT/TTS provider leaks audio/transcript | HIGH | Prefer ZDR/no-retention providers; local fallback for sensitive content; rotate keys on compromise |
| **Raw audio exfiltration via logs/MCP** | Raw audio written to a log or sent to an MCP tool | CRITICAL | Never log raw audio; never send to external MCP; AGENTS.md BLOCKING |
| **Always-listening cost runaway** | Realtime API bills continuously while idle | MEDIUM (cost) | Hard-default OFF; daily/monthly caps; kill switch; not MVP |
| **Audio replay (replay attack)** | Same injection audio replayed | HIGH | Same mitigations as pre-recorded injection; rate-limit + dedup of identical transcripts |

---

## 8. Cross-References

- `p21-consent-surveillance-research.md` — consent scopes, always-listening gating, spoken safe-word → Redis flag.
- `p21-memory-transcript-research.md` — transcript storage schema, retention/redaction, do_not_recall, audit hash chain.
- `p21-hermes-core-integration-research.md` — where the transcript enters the Hermes turn (reusing existing safety hooks).
- `p21-runtime-latency-deploy-research.md` — provider cost/latency, local fallback runtime, observability metrics.
- `p21-discord-voice-research.md` — capture surface (Faiz-only channel, consent).

---

## 9. Hard-Rejection Compliance Check (self-audit)

| Criterion | Met? | Evidence |
|---|---|---|
| Secrets/token handling is concrete (not vague) | ✅ | §1 names exact env vars, SOPS path, rotation, encryption profile |
| Provider claims backed by official-doc research | ✅ | §4.2 table cites openai.com/enterprise-privacy, deepgram.com/data-security, elevenlabs.io, openai pricing — all retrieved 2026-06-24 |
| Voice transcript treated as untrusted (injection pipeline) | ✅ | §2 maps full classify→sanitize→quarantine + V-022 registration |
| Safe-word detection first-class in audio path (pre-sanitization) | ✅ | §2.2 — HardStopHandler.check(transcript) before sanitize (SW-PI-008) |
| Secrets in transcript handled (drop/hash, never store) | ✅ | §3 |
| No raw audio in artifacts/logs/MCP | ✅ | §4.1 |
| No runtime code written / no deploy / no restart | ✅ | Planning-only; all proposals framed as design |

---

## 10. Footer

| Field | Value |
|---|---|
| Author | Guinevere (parent) — direct authorship after sub-agent failure |
| Grounding | `docs/20-security/*`, `src/core/services/hard_stop_handler.py`, `src/memory/models.py`, `src/life_kernel/hermes_brain.py`, MCPConfigGuide |
| Official-doc retrieval date | 2026-06-24 |
| Citations | OpenAI enterprise-privacy + pricing + realtime docs; Deepgram data-security; ElevenLabs privacy/enterprise/zero-retention |
| Verdict | PASS |
