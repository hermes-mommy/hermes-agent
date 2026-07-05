# P21 Voice Interface — Round 1 Architecture Audit Report

| Dimension | Architecture |
|---|---|
| Auditor | Independent architecture auditor (sub-agent) |
| Date | 2026-06-24 |
| Scope | P21 Voice Interface planning phase — architecture, Hermes integration, life_kernel integration, latency, dependency map |
| Source-of-truth | `docs/setup-evidence/P21/plan/p21-voice-interface-enterprise-plan.md`; `docs/setup-evidence/P21/research/p21-hermes-core-integration-research.md`; `docs/setup-evidence/P21/research/p21-life-kernel-integration-research.md`; `docs/setup-evidence/P21/research/p21-dependency-collision-research.md`; `docs/setup-evidence/P21/research/p21-runtime-latency-deploy-research.md`; `AGENTS.md`; `src/discord/hermes_conversational.py`; `src/life_kernel/heartbeat.py`; `src/life_kernel/state.py`; `src/life_kernel/sensors.py`; `src/core/services/hard_stop_handler.py` |

## 1. Executive Verdict

**OVERALL: PASS with conditions.**

P21 is explicitly designed as **integration, not sidecar**. The plan correctly mandates reusing the shared Hermes turn-core via a refactoring seam at `src/discord/hermes_conversational.py:427-691`, and it correctly preserves the single-source-of-truth `life_kernel:hard_stop` Redis key. The DRY safety argument is structurally sound, but the plan does not yet prove the seam is actually achievable without altering the return contract of `_process_and_respond` or the `channel.send` calls embedded in `_invoke_hermes_and_send`. The latency budget is realistic at the architectural level but leans on a streaming-Hermes enhancement that the source-of-truth code does not currently support. The two-tier life_kernel design (reactive real-time vs. reflective sensor) is correct and non-disruptive. NEW/LOCKED separation is well documented, though the dependency map overstates the parallelism of Wave 1 versus Wave 2 given the `src/voice/` package's dependency on `ProcessedTurn` defined in the LOCKED `hermes_conversational.py` refactor.

---

## 2. Dimension-by-Dimension Findings

### 2.1 Integration vs. Sidecar

**Verdict: PASS**

- The plan states the core principle repeatedly: "Voice reuses the Hermes turn-core; the only new code is STT/TTS wire, the L6 quarantine wrapper, the Discord voice-channel connection, and the additive sensor/dashboard" (`p21-voice-interface-enterprise-plan.md`, "Architecture" paragraph).
- The hard-rejection criterion is satisfied: "Plan is sidecar-only without evaluating Hermes core integration" is explicitly mitigated in the plan's Hard Rejection Criteria section and in the Hermes core integration research file.
- The architecture diagram in `p21-hermes-core-integration-research.md` §1.2 shows a thin adapter: STT → `_process_turn_core()` → TTS.

### 2.2 Shared Turn-Core Refactoring (`_process_and_respond` → `_process_turn_core`)

**Verdict: NEEDS REVIEW**

- The plan and research both specify extracting the body of `_process_and_respond` at `src/discord/hermes_conversational.py:427-691` into a shared `_process_turn_core()` (`p21-hermes-core-integration-research.md` §1.2, §7.2; plan §"Hermes Core Wiring").
- **Finding 2.2.1:** `_process_and_respond` currently returns `bool` and contains `await channel.send(...)` calls both directly (error fallback at line 540-541) and indirectly through `_invoke_hermes_and_send` (lines 589-596). The proposed `ProcessedTurn` return type is **not** present in source-of-truth; it is a design artifact. The plan does not document how the voice adapter will avoid importing Discord-specific `channel.send` behavior or how the voice path will receive response text without triggering Discord text-channel side effects. This is a seam correctness gap.
- **Finding 2.2.2:** The research file (§7.2, step 3) says "Replace `await channel.send(FALLBACK_MESSAGE)` with return of an error-typed `ProcessedTurn`." But the current source at `hermes_conversational.py:539-541` sends `FALLBACK_MESSAGE` to `channel` in multiple places. Unless the refactor is performed, the voice adapter cannot safely call the shared core without risking Discord-text delivery. This is a **planning gap**, not an implementation bug, but it must be addressed before Wave P21-003 is delegated.
- **Cited source:** `src/discord/hermes_conversational.py:427-691`, `src/discord/hermes_conversational.py:539-541`, `src/discord/hermes_conversational.py:589-596`.

**Recommended fix:** The planner should amend the plan (or add an P21-003 pre-condition) stating that the refactor must:
1. Move `DistressDetector/SafeModeController`, memory recall, Hermes invocation, cost tracking, shadow forward, and auto-store into a pure function returning `ProcessedTurn`.
2. Keep all `channel.send` and `_split_response` side effects in the Discord-text adapter only.
3. Add `source_type: str = "discord"` to `store_conversation` and cost-tag calls.
4. Provide a unit test proving the shared core can be invoked with `source_type="voice"` without importing `discord.TextChannel`.

### 2.3 DRY Safety Hooks

**Verdict: PASS (conditional)**

- The DRY argument is sound: `HardStopHandler.check()` (`src/core/services/hard_stop_handler.py:89-103`) operates on text and will be reused verbatim. `DistressDetector.detect()` and `SafeModeController.evaluate()` are reused from `src/persona/safe_mode.py`. The plan correctly avoids duplicating these hooks.
- The plan states the injection quarantine runs once in `src/voice/sanitize.py` and labels the transcript with `<untrusted source="voice" trust="6">` before entering the shared turn-core (`p21-voice-interface-enterprise-plan.md` §Global Constraints, §Prompt Injection).
- **Finding 2.3.1:** The plan asserts the transcript is fed into `_process_turn_core` after injection quarantine, but the `HardStopHandler.check()` must run on the **RAW** transcript pre-sanitization. The research file acknowledges this (`p21-hermes-core-integration-research.md` §4.3: "The safe-word classifier runs BEFORE sanitization on RAW input"), but the plan's §Global Constraints says "Every transcript MUST pass: `HardStopHandler.check()` on RAW transcript (pre-sanitization, SW-PI-008) → injection classify/sanitize." This ordering is correct. The architecture is sound; implementation must preserve it.

### 2.4 Latency Budget

**Verdict: PASS (conditional)**

- The plan documents E2E p50 <1.5s and p95 <2.5-3.5s with a per-stage budget (`p21-voice-interface-enterprise-plan.md` §Cost/Latency Model; `p21-runtime-latency-deploy-research.md` §1).
- The bottleneck is correctly identified as LLM TTFT + non-streaming TTS.
- **Finding 2.4.1:** The streaming-vs-fallback tradeoff is documented in `p21-runtime-latency-deploy-research.md` §2.3 and in the plan §"STT / TTS / Streaming Pipeline". The research correctly notes that Hermes `send_message()` is **non-streaming** today (`src/hermes/_session_adapter.py:235-239`, `src/discord/hermes_conversational.py:301`) and that streaming-Hermes is a Phase-2 enhancement.
- **Finding 2.4.2:** The plan's global latency target of p50 <1.5s is only achievable with streaming TTS and overlapping LLM-to-TTS. With the current non-streaming Hermes path, the research estimates p50 ~2s (`p21-runtime-latency-deploy-research.md` §2.3: "MVP decision: accept non-streaming Hermes + streaming TTS — simpler, reuses existing adapter, ~p50 2 s."). The plan's §Cost/Latency Model says "E2E p50 ~1.5-2.0s" which is consistent but stricter than the source. The target is **ambitious but not unrealistic** provided the streaming-Hermes optimization is tracked as a dependency.
- **Recommended fix:** Add an explicit acceptance criterion in P21-003: "If streaming-Hermes is not available, accept p50 ~2s and file a follow-up optimization."

### 2.5 Two-Tier life_kernel Design

**Verdict: PASS**

- The plan correctly distinguishes reactive real-time turns (bypass the graph) from reflective sensor metadata (feeds the 30s awareness loop). This matches the source-of-truth sensor architecture: `src/life_kernel/sensors.py:108-148` `sense_all()` is called by the observer loop, and `src/life_kernel/state.py:109-114` already has a capped `observations` reducer.
- The proposed `VoiceSensorAdapter` (`src/life_kernel/sensor_adapters/voice_sensor_adapter.py`) is additive, implements the existing `_SensorAdapter` Protocol, and does not modify the 1s HARD-STOP heartbeat (`src/life_kernel/heartbeat.py:254-357`).
- The single-source-of-truth `life_kernel:hard_stop` Redis key is preserved (`src/life_kernel/heartbeat.py:273` reads it every 1s; voice path will SET it on spoken safe-word). This is correctly documented in `p21-life-kernel-integration-research.md` §1 and the plan §"life_kernel Wiring".

### 2.6 NEW vs. LOCKED File Separation

**Verdict: PASS (with documentation note)**

- The plan clearly separates NEW files (Wave 1, unblocked) from LOCKED shared-core changes (Wave 3+, blocked on P20 pass). This is documented in the plan §"File Structure" table, §"Global Constraints", and in `p21-dependency-collision-research.md` §5, §10.
- **Finding 2.6.1:** The dependency map in the plan claims P21-001 (STT/TTS provider abstraction) and the NEW-file scaffolding are parallel and independent. However, `src/voice/turn_core.py` is listed as a NEW file in Wave 1/3 but conceptually depends on the `ProcessedTurn` type defined by the LOCKED `hermes_conversational.py` refactor. In practice, `turn_core.py` cannot be implemented until the refactor is complete. The plan partially acknowledges this by listing `src/voice/turn_core.py` under Wave 3 (P21-003) and noting it depends on the `hermes_conversational.py` refactor which is BLOCKED on P20 pass. This is correct but the parallelism claim for Wave 1 should be scoped to "STT/TTS provider interfaces and audio codec" only.
- **Finding 2.6.2:** The collision matrix in `p21-dependency-collision-research.md` §9 rates `src/core/main.py`, `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md`, and `pyproject.toml` as MEDIUM risk because they are shared with P20 or are single-owner doc edits. This is consistent with the plan's gating.

### 2.7 Dependency Map and Parallelism

**Verdict: PASS (with one clarification needed)**

- The plan provides a 9-wave dependency map and parallelism rules (`p21-voice-interface-enterprise-plan.md` §"Dependency Map").
- The sequencing is logical: P21-001 → 002 → 003 → 004/005 → 006 → 007 → 008 → 009.
- **Finding 2.7.1:** The plan states "P21-004, P21-005 can `parallel` after 003". This is correct because memory writes (004) and consent/HARD-STOP gating (005) are independent surfaces. Similarly, P21-007 is additive dashboard work that can parallel 004/005/006.
- **Finding 2.7.2:** The collision research file §10.2 lists Wave 1 (NEW files) as unblocked and Wave 3 (LOCKED-file edits) as blocked on P20 pass. This is the binding sequencing. The plan should make it explicit in the "Dependency Map" that `src/voice/turn_core.py` is NOT part of Wave 1 even though it lives under `src/voice/`.

---

## 3. Source-of-Truth Verification Matrix

| Claim in Plan / Research | Source-of-Truth Evidence | Status |
|---|---|---|
| `_process_and_respond()` is the shared turn core | `src/discord/hermes_conversational.py:427-691` contains distress, memory, Hermes, cost, shadow, auto-store | ✅ Verified |
| `HermesSessionAdapter.send_message()` is non-streaming | `src/hermes/_session_adapter.py:235-239` uses `asyncio.to_thread(agent.run_conversation, ...)`; research §2.1 | ✅ Verified |
| `life_kernel:hard_stop` is checked every 1s | `src/life_kernel/heartbeat.py:273` reads Redis key | ✅ Verified |
| Sensor registry Protocol supports new adapters | `src/life_kernel/sensors.py:108-148` `sense_all()`; `src/life_kernel/state.py:109-114` observations reducer | ✅ Verified |
| `HardStopHandler.check()` is text-based | `src/core/services/hard_stop_handler.py:89-103` | ✅ Verified |
| `_process_and_respond` returns `bool` and sends to Discord channel | `src/discord/hermes_conversational.py:491`, `:540-541`, `:589-596` | ⚠️ Confirmed — needs refactor for shared core |

---

## 4. Risk Register

| ID | Risk | Severity | Mitigation in Plan | Status |
|---|---|---|---|---|
| R1 | Refactor of `_process_and_respond` changes return type and side-effect surface | MEDIUM | P21-003 BLOCKED on P20 pass; explicit seam design | Tracked; needs pre-condition test |
| R2 | `ProcessedTurn` type not yet in source code | LOW | Defined in plan; will be added during P21-003 | Tracked |
| R3 | p50 <1.5s depends on streaming-Hermes not in current source | MEDIUM | Fallback to p50 ~2s documented; streaming-Hermes as Phase-2 optimization | Tracked |
| R4 | Voice `turn_core.py` depends on LOCKED refactor but is in NEW-file package | LOW | Plan correctly places it in Wave 3; collision matrix acknowledges | Tracked |
| R5 | P20 production-pass still in soak; timing uncertainty | MEDIUM | Gating documented; Wave 1 NEW files can proceed after pass | External dependency |

---

## 5. Conditions for Phase PASS

1. **P21-003 pre-condition:** Add a concrete refactor contract to the plan: `channel.send` side effects must remain in the Discord-text adapter; `_process_turn_core` returns `ProcessedTurn`; `source_type` parameter added to memory store and cost calls.
2. **Latency acceptance criterion:** Document that p50 <1.5s is a target requiring streaming-Hermes; if unavailable, accepted MVP p50 is ~2s.
3. **Turn-core location clarification:** Ensure `src/voice/turn_core.py` is not listed as a Wave 1 deliverable; keep it under Wave 3 dependency on the LOCKED refactor.

---

## 6. Conclusion

The P21 Voice Interface architecture is fundamentally sound: it is integration-not-sidecar, it reuses the Hermes text turn-core, it preserves the single `life_kernel:hard_stop` Redis key, and it correctly separates reactive real-time turns from reflective sensor awareness. The main gaps are in the **refactoring contract** for `_process_and_respond` and the **latency target caveat**; both are addressable as planning-phase conditions and do not invalidate the architecture. No runtime code has been edited, deployed, or restarted in this phase.

**Overall verdict: PASS (with the conditions above).**

---

*Report written to `docs/setup-evidence/P21/evidence/audits/round-1/architecture.md`.*
