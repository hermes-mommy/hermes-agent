# P21 Voice Interface — Round 1 Audit: Runtime / Latency / Deploy

**Auditor:** Independent runtime/latency dimension auditor  
**Scope:** `p21-voice-interface-enterprise-plan.md` (deployment model, latency budget, rollback model, resource ceiling, metrics) + `p21-runtime-latency-deploy-research.md` + repo source-of-truth (systemd units, metrics patterns, Redis routing, P20 status, pyproject.toml, main.py, heartbeat.py).  
**Date:** 2026-06-24  
**Verdict:** PASS with findings (NEEDS REVIEW on two concrete gaps; no FAIL).

---

## 1. Executive Summary

The P21 runtime/latency/deploy planning is sound overall: a new `guinevere-voice` systemd service is justified by isolation and independent-rollback requirements; resource assumptions are in the right ballpark but not stress-tested; Redis/port collision risk is low because the plan uses key-prefixes inside existing DBs; the local fallback is documented but not benchmarked; Prometheus metrics are explicitly modeled on existing subsystem patterns; the rollback model has multiple concrete levers; and the phase is correctly blocked on P20 production pass. Two issues need a follow-up clarification before implementation (NEEDS REVIEW), neither is a phase-blocking FAIL.

---

## 2. Source-of-Truth Baseline

### 2.1 Systemd / deployment patterns

- `vps-mirror/systemd-live/guinevere-core.service`: `MemoryHigh=1G`, `MemoryMax=2G`, `CPUQuota=200%`, `Type=exec`, runs uvicorn on port 8000 (`vps-mirror/systemd-live/guinevere-core.service:22-24`).
- `systemd/guinevere-mcp.service`: `MemoryHigh=1G`, `MemoryMax=2G`, `CPUQuota=200%`, `Requires=guinevere-core.service`, `Type=exec` (`systemd/guinevere-mcp.service:22-24`).
- `systemd/guinevere-surveillance.service`: `MemoryHigh=512M`, `MemoryMax=768M`, `CPUQuota=100%`, `Requires=guinevere-core.service` (`systemd/guinevere-surveillance.service:25-27`).
- `systemd/guinevere-gmail.service`: `MemoryHigh=448M`, `MemoryMax=512M`, `CPUQuota=100%` (`systemd/guinevere-gmail.service:23-25`).
- `systemd/guinevere-x-poster.service`: `MemoryHigh=256M`, `MemoryMax=512M`, `CPUQuota=100%` (`systemd/guinevere-x-poster.service:23-25`).

All live units use `Restart=always`, `StandardOutput/Error=journal`, a `guinevere.slice`, and per-service `EnvironmentFile`.

### 2.2 Redis / DB routing

- `docs/60-persona/62-MCPConfigGuide_v1.0.md:123-130`: DB0 task queue, DB1 LLM cache, DB2 surveillance, DB3 session state (TTL 24h), DB4 pub/sub, DB5 rate limit.
- `src/core/main.py:136-142`: surveillance consumer explicitly connects to Redis `db=2`.
- `src/life_kernel/heartbeat.py:273`: HARD-STOP flag key is `life_kernel:hard_stop`.

### 2.3 Metrics patterns

- `src/gmail/metrics.py`: module-level `Counter`/`Gauge`/`Histogram` from `prometheus_client`, helper functions to set/inc/observe.
- `src/channels/whatsapp/metrics.py`: same pattern, with device labels.
- `src/core/services/llm_metrics.py`: also defines `Counter`/`Gauge`/`Histogram` and starts an Prometheus HTTP server on `localhost:9191`.
- `src/x_poster/metrics.py`: same pattern plus `start_http_server`.

### 2.4 Hermes non-streaming status

- `src/hermes/_session_adapter.py:235-240`: calls `agent.run_conversation(...)` via `asyncio.to_thread` and expects a dict with `final_response` — i.e. non-streaming today.
- `src/discord/hermes_conversational.py:333-337`: calls `hermes.send_message(user_id, content, system_prompt)` and receives a full string.

### 2.5 P20 status

- `docs/setup-evidence/P20/README.md:1-5`: "PRODUCTION STABILIZED — SOAK IN PROGRESS — PRODUCTION PASS HOLD".
- `docs/setup-evidence/P20/README.md:49`: LK-017 in production soak.
- `docs/setup-evidence/P20/README.md:79-85`: 390 life-kernel tests passing.

### 2.6 pyproject.toml

- `pyproject.toml:1-56`: no voice dependencies (`discord-ext-voice-recv`, `PyNaCl`, `deepgram-sdk`, `cartesia`, `faster-whisper`, `piper-tts`, `silero-vad`, `openwakeword`).

---

## 3. Findings

### 3.1 New systemd service `guinevere-voice` vs submodule — PASS

**Plan claim:** New additive service `guinevere-voice` with isolation, independent restart/rollback, `MemoryLimit=512M`, `CPUQuota` ~1 CPU (`p21-runtime-latency-deploy-research.md:88-98`, `p21-voice-interface-enterprise-plan.md:329`).

**Audit:**
- Isolation is consistent with the existing service decomposition: core, mcp, surveillance, gmail, x-poster, discord, loops each have their own unit.
- A separate service is the right call: voice path involves Opus encode/decode, STT/TTS WebSockets, and VAD — a different resource profile from the FastAPI core and from P20's heartbeat.
- Independent restart/rollback is real because the unit can be stopped/started without `Requires=guinevere-core.service` or `Requires=guinevere-mcp.service`.

**Verdict:** PASS.

---n

### 3.2 Resource footprint — PASS with caveat

**Plan claim:** `MemoryLimit=512M`, ~1 CPU; RAM estimate 150–350 MB (`p21-runtime-latency-deploy-research.md:102-103`).

**Audit:**
- 512 MB matches the smaller per-service ceiling in the repo (e.g. `guinevere-gmail.service` 512M, `guinevere-x-poster.service` 512M, `guinevere-surveillance.service` 768M).
- The 150–350 MB estimate is plausible for a single-user PTT path (PCM ring buffers, Opus, VAD state, STT/TTS client buffers, Python runtime) but assumes no local faster-whisper model loaded. If the local fallback loads a Whisper model, 512 MB can be tight on CPU; the plan acknowledges this in `p21-runtime-latency-deploy-research.md:128`.
- The research cites no benchmark numbers for the actual VPS (CPU/RAM not specified in repo).

**Verdict:** PASS — assumption is reasonable for MVP, but implementation should measure RSS under local-fallback load.

---

### 3.3 Redis / port / DB collision — PASS with clarification needed

**Plan claim:** voice uses key-prefix `voice:*` in DB3 (session) + DB5 (rate-limit); no new DB; no collision with `life_kernel:hard_stop` (`p21-runtime-latency-deploy-research.md:109-110`, `p21-voice-interface-enterprise-plan.md:329`).

**Audit:**
- No new listen port is required (outbound provider WebSockets + Discord gateway).
- Key-prefix `voice:*` is a safe namespace distinct from `life_kernel:hard_stop` and from `session:{id}` / `ratelimit:{ip}` patterns (`docs/60-persona/62-MCPConfigGuide_v1.0.md:124-129`).
- **NEEDS REVIEW:** The plan does not state which Redis DB the voice path will use for the HARD-STOP *check* / `life_kernel:hard_stop` read. That key lives on the default Redis DB (DB0 in most existing code) or the same connection that `heartbeat.py:273` uses. The voice service must open a Redis connection compatible with the kernel's DB selection, otherwise it will read/write to the wrong DB and miss the HARD-STOP flag or fail to set it. The implementation wave should document the Redis DB index for the voice connection.

**Verdict:** PASS on collision risk; NEEDS REVIEW on DB index for `life_kernel:hard_stop` access.

---

### 3.4 Local fallback (faster-whisper + Piper) — PASS with caveat

**Plan claim:** faster-whisper + Piper/Kokoro local fallback, CPU feasible for single-user PTT, heavy for always-listening (`p21-runtime-latency-deploy-research.md:115-129`).

**Audit:**
- The fallback chain (primary cloud → alt cloud → local) is sound.
- The plan correctly notes that always-listening + faster-whisper CPU is heavy and therefore not MVP.
- No local benchmark evidence is provided; the claim is directional.

**Verdict:** PASS — acceptable for planning, but P21-001/002 implementation should include a CPU/RSS smoke test before finalizing fallback thresholds.

---

### 3.5 Prometheus metrics mirroring repo pattern — PASS

**Plan claim:** `src/voice/metrics.py` follows `src/gmail/metrics.py` pattern (`p21-runtime-latency-deploy-research.md:133-149`).

**Audit:**
- The proposed metrics (`voice_turn_latency_seconds`, `voice_stt_cost_usd`, `voice_tts_cost_usd`, `voice_hard_stop_total`, `voice_consent_violation_total`, `voice_injection_detected_total`, `voice_secrets_detected_total`, `voice_bargein_total`, `voice_connected`, `voice_provider_fallback_total`) are consistent with module-level metric families + helper functions used across `src/gmail/metrics.py`, `src/channels/whatsapp/metrics.py`, `src/x_poster/metrics.py`, and `src/core/services/llm_metrics.py`.
- Plan references mirroring `GMAIL_INJECTION_DETECTED_TOTAL` (`src/gmail/metrics.py:45`) and `GMAIL_SECRETS_DETECTED_TOTAL` (`src/gmail/metrics.py:51`) — exact line references match.

**Verdict:** PASS.

---

### 3.6 Rollback model — PASS with clarification needed

**Plan claim:** Feature flag `voice.enabled:false` + `/voice-off` slash command + HARD STOP Redis flag + `systemctl stop guinevere-voice` (`p21-runtime-latency-deploy-research.md:159-169`, `p21-voice-interface-enterprise-plan.md:334-336`).

**Audit:**
- Four concrete levers: config flag, Discord kill switch, spoken safe-word → shared HARD STOP, systemd unit stop.
- Independent service stop leaves core/Discord text/kernel unaffected, consistent with existing service isolation.
- **NEEDS REVIEW:** The plan does not state whether `guinevere-voice.service` will declare `Requires=` / `After=` dependencies on `guinevere-core.service` or `guinevere-mcp.service`. If it `Requires=guinevere-core.service`, an independent voice rollback (stop) is still possible, but a core restart would pull voice down. Conversely, if voice has no ordering dependency, core can restart independently. The systemd unit design should be explicit in P21-008.

**Verdict:** PASS on rollback concept; NEEDS REVIEW on systemd unit ordering dependency.

---

### 3.7 Latency budget grounded in official provider docs — PASS

**Plan claim:** Tables cite OpenAI pricing, Deepgram pricing, faster-whisper GitHub, OpenAI TTS/realtime docs (`p21-runtime-latency-deploy-research.md:201-216`, `p21-runtime-latency-deploy-research.md:242`).

**Audit:**
- The research file includes explicit URLs for OpenAI, Deepgram, faster-whisper, and Piper/Kokoro.
- Latency numbers are presented as estimates (e.g. "~300 ms", "~400 ms") rather than guaranteed SLAs, which is appropriate for a planning document.
- The conclusion that the bottleneck is Hermes LLM (non-streaming) + non-streaming TTS is consistent with `src/hermes/_session_adapter.py:235-240` and `src/discord/hermes_conversational.py:333-337`.

**Verdict:** PASS.

---

### 3.8 Deployment blocked on P20 pass — PASS

**Plan claim:** Wave 3+ (main.py, pyproject.toml, hermes_conversational.py, life_kernel/state.py, memory/models.py) are BLOCKED until P20 production pass (`p21-voice-interface-enterprise-plan.md:18`, `p21-voice-interface-enterprise-plan.md:85-88`).

**Audit:**
- P20 README confirms PRODUCTION PASS HOLD.
- pyproject.toml currently lacks voice dependencies, so no accidental voice deps are present.
- No runtime code edits are performed in this planning phase (consistent with AGENTS.md §2 and P21 hard-rejection rule 8).

**Verdict:** PASS.

---

## 4. Cross-Cutting Observations

1. **No port collision** because voice uses outbound WebSockets + Discord gateway.
2. **Redis DB collision is avoided by key-prefix**, but the DB index for `life_kernel:hard_stop` must be confirmed.
3. **Metric port collision:** if `guinevere-voice` also starts a Prometheus HTTP server, it must use a port other than 9191 (already used by `llm_metrics` in `src/core/main.py:74`) or reuse the same registry via push/aggregation. The plan does not detail this.
4. **Cost ceiling integration** mentions `CostTracker.record_cost` but does not show the existing cost tracker code; this is acceptable for planning but should be verified during P21-001.

---

## 5. Required Follow-ups Before Implementation

| # | Gap | Owner | Evidence |
|---|---|---|---|
| 1 | Document exact Redis DB index used by voice service to read/write `life_kernel:hard_stop` | P21-008 implementer | `docs/setup-evidence/P21/evidence/P21-008/verification.md` |
| 2 | Document `guinevere-voice.service` systemd `After=`/`Requires=` ordering vs core/mcp | P21-008 implementer | `docs/setup-evidence/P21/evidence/P21-008/verification.md` |
| 3 | Confirm Prometheus scrape port/registry strategy for voice metrics | P21-007/P21-008 implementer | `src/voice/metrics.py` + verification.md |

---

## 6. Verdict

**Overall:** PASS

The runtime/latency/deploy dimension is well-reasoned, consistent with repo patterns, and respects the P20 production-pass hold. Two NEEDS REVIEW items (Redis DB index for HARD STOP, systemd ordering dependency) are non-blocking for the planning phase but must be closed during P21-008 implementation.
