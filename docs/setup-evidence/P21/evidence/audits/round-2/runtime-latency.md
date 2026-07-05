# P21 Voice Interface — Round 2 Audit: Runtime / Latency / Deploy

**Auditor:** Independent runtime/latency dimension auditor (round 2)
**Scope:** Amended P21 plan (`p21-voice-interface-enterprise-plan.md`), round-1 runtime-latency audit (`runtime-latency.md`), supporting research files, and repo source-of-truth.
**Date:** 2026-06-24
**Verdict:** PASS with conditions

---

## 1. Executive Summary

The amended P21 plan closes all three runtime/latency round-1 findings (A4–A6) through explicit, binding amendments in the new "Audit Round-1 Amendments" section. The runtime/latency/deploy dimension remains sound: the new `guinevere-voice` service is justified, resource ceiling is consistent with existing per-service limits, Redis/port collision risk is low and now explicitly handled, local fallback is documented, rollback model is concrete, and P20 gating is intact. No new blocking gaps were introduced. Verdict is **PASS with conditions**: the A4–A6 amendments must be treated as binding implementation requirements in P21-008, and their evidence must appear in the wave verification artifacts.

---

## 2. Round-1 Finding Closure

| Round-1 # | Finding | Amendment ID | Wave | Closure Verdict | Evidence / Rationale |
|---|---|---|---|---|---|
| A4 | Voice Redis DB index for `life_kernel:hard_stop` access not specified | A4 | P21-008 | **CLOSED** | Plan now states: "document the exact Redis DB index the voice service uses to read/write `life_kernel:hard_stop` (must match `heartbeat.py:273`'s connection DB); verify the voice Redis client connects to the same DB the kernel polls" (`p21-voice-interface-enterprise-plan.md:466`). |
| A5 | `guinevere-voice.service` `After=`/`Requires=` ordering vs core/mcp not specified | A5 | P21-008 | **CLOSED** | Plan now states: "`After=guinevere-core.service` (voice starts after core); NO `Requires=guinevere-core.service` (so `systemctl stop guinevere-voice` is independent and a core restart doesn't force-pull voice down)" (`p21-voice-interface-enterprise-plan.md:467`). |
| A6 | Prometheus scrape port/registry for voice metrics not specified | A6 | P21-007/008 | **CLOSED** | Plan now states: "voice metrics reuse the existing Prometheus registry; if a separate HTTP server is needed, use a port ≠ 9191 (already used by `llm_metrics` `src/core/main.py:74`) OR push to the shared gateway" (`p21-voice-interface-enterprise-plan.md:468`). |

The amendments are explicitly declared "binding for the future implementation waves" (`p21-voice-interface-enterprise-plan.md:481`).

---

## 3. Re-verification of Runtime / Latency / Deploy Dimensions

### 3.1 `guinevere-voice` service justification — PASS

**Amended plan claim:** new isolated `guinevere-voice` service with independent restart/rollback, scoped `MemoryLimit=512M`/`CPUQuota` (`p21-voice-interface-enterprise-plan.md:329` and research `p21-runtime-latency-deploy-research.md:88-98`).

**Audit:**
- The decision matrix and rationale remain unchanged and consistent with the existing service decomposition (core, mcp, surveillance, gmail, x-poster, discord, loops each have their own unit — `systemd/guinevere-mcp.service:1-33` shows the established pattern: `MemoryHigh=1G`, `MemoryMax=2G`, `CPUQuota=200%`, `Requires=guinevere-core.service`).
- Voice's distinct resource profile (Opus encode/decode, STT/TTS WebSockets, VAD, resampling) justifies a separate unit.
- The new service is additive and does not destabilize `guinevere-core`, which is in P20 production-pass HOLD.

**Verdict:** PASS.

---

### 3.2 Resource ceiling — PASS with caveat

**Amended plan claim:** `MemoryLimit=512M`, `CPUQuota` ~1 CPU, RAM estimate 150–350 MB (`p21-runtime-latency-deploy-research.md:102-103` and `p21-voice-interface-enterprise-plan.md:329`).

**Audit:**
- 512 MB matches the smaller per-service ceilings in the repo (e.g. `guinevere-gmail.service` 512M, `guinevere-x-poster.service` 512M, `guinevere-surveillance.service` 768M — round-1 audit baseline §2.1).
- The 150–350 MB estimate is plausible for single-user PTT (PCM ring buffers, Opus, VAD, STT/TTS client buffers) but assumes the local-fallback Whisper model is not loaded persistently; if it is, 512 MB can be tight (`p21-runtime-latency-deploy-research.md:128`).
- No new benchmark evidence has been added; this remains a directional assumption.

**Verdict:** PASS — assumption reasonable for MVP, implementation must measure RSS under local-fallback load.

---

### 3.3 Redis / port / DB collision — PASS (improved from NEEDS REVIEW)

**Amended plan claim:** voice uses key-prefix `voice:*` in DB3 (session) + DB5 (rate-limit); no new DB; no collision with `life_kernel:hard_stop` (`p21-runtime-latency-deploy-research.md:108-110` and `p21-voice-interface-enterprise-plan.md:329`).

**Audit:**
- No new listen port is required (outbound provider WebSockets + Discord gateway).
- Key-prefix `voice:*` is a safe namespace distinct from `life_kernel:hard_stop` and from `session:{id}` / `ratelimit:{ip}` patterns (`docs/60-persona/62-MCPConfigGuide_v1.0.md:124-129`).
- **A4 amendment now closes the gap:** it requires P21-008 to document the exact Redis DB index the voice service uses to read/write `life_kernel:hard_stop` and to verify the voice Redis client connects to the same DB the kernel polls (`p21-voice-interface-enterprise-plan.md:466`).
- Current repo source-of-truth shows `heartbeat.py:273` uses `self.redis_client` to read `life_kernel:hard_stop`; the kernel's Redis client is configured in `src/life_kernel/redis_client.py:38` (`redis.Redis.from_url(redis_url, db=db, decode_responses=True)`), with DB selection externalized. The amendment's instruction to "match `heartbeat.py:273`'s connection DB" is therefore implementable.

**Verdict:** PASS — collision risk low and the round-1 DB-index documentation gap is now explicitly closed by a binding amendment.

---

### 3.4 Local fallback — PASS with caveat

**Amended plan claim:** faster-whisper + Piper/Kokoro local fallback, CPU feasible for single-user PTT, heavy for always-listening (`p21-runtime-latency-deploy-research.md:115-129` and `p21-voice-interface-enterprise-plan.md:318-322`).

**Audit:**
- The fallback chain (primary cloud → alt cloud → local) is documented and gated by cost/sensitive-content/outage triggers.
- The plan correctly notes that always-listening + faster-whisper CPU is heavy and therefore not MVP.
- No local benchmark evidence has been added; the claim remains directional.

**Verdict:** PASS — acceptable for planning, but P21-001/002 implementation should include CPU/RSS smoke tests before finalizing fallback thresholds.

---

### 3.5 Prometheus metrics — PASS (improved from NEEDS REVIEW)

**Amended plan claim:** `src/voice/metrics.py` follows `src/gmail/metrics.py` pattern (`p21-runtime-latency-deploy-research.md:133-149` and `p21-voice-interface-enterprise-plan.md:58`).

**Audit:**
- Proposed metric families are consistent with existing module-level Prometheus patterns in the repo.
- **A6 amendment now closes the port/registry gap:** it requires voice metrics to either reuse the existing Prometheus registry or, if a separate HTTP server is used, to bind to a port other than 9191 (already used by `llm_metrics` in `src/core/main.py:72-74`).

**Verdict:** PASS — pattern is consistent and the port-collision risk is now explicitly mitigated by a binding amendment.

---

### 3.6 Rollback model — PASS (improved from NEEDS REVIEW)

**Amended plan claim:** feature flag `voice.enabled:false` + `/voice-off` slash command + HARD STOP Redis flag + `systemctl stop guinevere-voice` (`p21-runtime-latency-deploy-research.md:159-169` and `p21-voice-interface-enterprise-plan.md:334-336`).

**Audit:**
- Four concrete levers remain in place.
- Independent service stop leaves core/Discord text/kernel unaffected, consistent with existing service isolation.
- **A5 amendment now closes the ordering gap:** it requires `After=guinevere-core.service` but NO `Requires=guinevere-core.service`, preserving independent voice rollback while ensuring startup order (`p21-voice-interface-enterprise-plan.md:467`).

**Verdict:** PASS — rollback concept remains sound and the systemd ordering dependency gap is now explicitly closed by a binding amendment.

---

### 3.7 Latency budget and provider claims — PASS

**Amended plan claim:** E2E p50 ~1.5–2.0 s, p95 ~2.5–3.5 s; bottleneck = LLM TTFT + non-streaming TTS (`p21-voice-interface-enterprise-plan.md:308-309` and `p21-runtime-latency-deploy-research.md:39`).

**Audit:**
- Budget is internally consistent with the research file.
- Provider latency/cost claims cite official sources (OpenAI pricing, Deepgram pricing, faster-whisper GitHub).
- Non-streaming Hermes is explicitly accepted for MVP; streaming-Hermes is deferred as a Phase-2 optimization.

**Verdict:** PASS.

---

### 3.8 P20 production-pass gate — PASS

**Amended plan claim:** Wave 3+ and P21-008 are BLOCKED until P20 production pass (`p21-voice-interface-enterprise-plan.md:18`, `85-88`, `436`).

**Audit:**
- P21-008 (`guinevere-voice.service`, `src/core/main.py`, `pyproject.toml`) is explicitly BLOCKED on P20 pass.
- The plan remains planning-only with no runtime code edits, deploy, or restart in this phase.
- This aligns with AGENTS.md §2 and hard-rejection criterion 8.

**Verdict:** PASS.

---

## 4. New Gaps / Conditions Introduced by the Amendments

No new FAIL-level or blocking runtime/latency gaps were introduced. Two **conditions** must hold for this dimension to remain PASS when P21-008 executes:

1. **A4 implementation evidence:** P21-008's `verification.md` must show the chosen Redis DB index for `life_kernel:hard_stop` and demonstrate (via unit test or smoke test) that the voice Redis client reads/writes the same DB the heartbeat polls.
2. **A5/A6 implementation evidence:** P21-008 must include the final `guinevere-voice.service` unit with the exact `After=`/`Requires=` relationship documented in A5, and P21-007/008 must include the chosen Prometheus registry/port strategy documented in A6.

The amended plan explicitly makes these amendments binding (`p21-voice-interface-enterprise-plan.md:481`), so the design intent is clear; the only remaining risk is implementation non-compliance.

---

## 5. Cross-Cutting Observations

1. **Port collision:** voice needs no inbound listen port beyond the existing Discord gateway and outbound provider WebSockets. A6 explicitly prevents Prometheus port 9191 collision.
2. **DB collision:** avoided by `voice:*` key-prefix plus the A4 amendment's DB-index verification requirement.
3. **Resource assumption:** the 512 MB ceiling remains an assumption that needs empirical validation when local fallback is exercised.
4. **P20 non-interference:** the additive service model and P20-gating preserve the production-pass soak.

---

## 6. Round-1 Finding Closure Table (Runtime / Latency Dimension)

| Finding | Description | Status | Amendment | Wave | Notes |
|---|---|---|---|---|---|
| A4 | Redis DB index for `life_kernel:hard_stop` not specified | **CLOSED** | A4 | P21-008 | Binding requirement to document and verify DB index match with heartbeat |
| A5 | systemd `After=`/`Requires=` ordering unspecified | **CLOSED** | A5 | P21-008 | Binding requirement: `After=guinevere-core.service`, NO `Requires=` |
| A6 | Prometheus port/registry strategy unspecified | **CLOSED** | A6 | P21-007/008 | Binding requirement: shared registry OR port ≠ 9191 |

---

## 7. Verdict

**Overall: PASS with conditions**

The runtime/latency/deploy dimension of the amended P21 plan is sound. All three round-1 findings for this dimension (A4, A5, A6) are closed via explicit, binding amendments. No new blocking gaps were introduced. The remaining work is to ensure P21-008 implementation satisfies the A4–A6 evidence requirements.
