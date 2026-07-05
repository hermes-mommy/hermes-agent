# P21 Voice Interface — Round 2 Architecture Audit Report

| Dimension | Architecture |
|---|---|
| Auditor | Independent architecture auditor (sub-agent) |
| Date | 2026-06-24 |
| Scope | P21 Voice Interface planning phase — verify Round-1 findings A1, A2, A3 are closed in the amended plan; re-verify integration-not-sidecar, DRY safety, two-tier life_kernel, NEW/LOCKED separation, dependency-map parallelism; identify any new gaps introduced by the amendments |
| Source-of-truth | `docs/setup-evidence/P21/plan/p21-voice-interface-enterprise-plan.md`; `docs/setup-evidence/P21/evidence/audits/round-1/architecture.md`; `AGENTS.md`; `src/discord/hermes_conversational.py`; `src/hermes/_session_adapter.py`; `src/hermes/_memory_bridge.py`; `src/core/services/hard_stop_handler.py`; `src/life_kernel/heartbeat.py`; `src/life_kernel/sensors.py`; `src/life_kernel/state.py`; `docs/setup-evidence/P21/research/p21-dependency-collision-research.md` |

## 1. Executive Verdict

**OVERALL: PASS with minor clarification notes.**

The amended plan closes the three architecture-related Round-1 findings (A1, A2, A3) with concrete Wave 3 pre-conditions and acceptance criteria. Integration-not-sidecar, DRY safety reuse, two-tier life_kernel separation, NEW/LOCKED file gating, and dependency-map parallelism are all preserved and better scoped. The remaining observations are documentation-clarity issues (a missing file in the File Structure table and the Redis callback mechanism), not architectural gaps.

---

## 2. Round-1 Finding Closure

| Round-1 Finding | Amendment | Status | Evidence in Amended Plan |
|---|---|---|---|
| A1 — `_process_and_respond` returns `bool` + calls `channel.send` directly; `ProcessedTurn` not in source; refactor seam is design-only | A1: P21-003 pre-condition + scaffold; move all side effects to Discord-text adapter; `source_type="voice"` unit test | **CLOSED** | `p21-voice-interface-enterprise-plan.md` "Audit Round-1 Amendments" table, line 462; Wave P21-003 scaffold (lines 377–385) |
| A2 — p50 <1.5 s depends on streaming-Hermes not in current source | A2: P21-003 acceptance criterion accepts non-streaming MVP p50 ~2 s; streaming-Hermes is a Phase-2 optimization | **CLOSED** | "Audit Round-1 Amendments" line 463; Wave P21-003 scaffold; STT/TTS/Streaming Pipeline section (line 181–183) |
| A3 — `src/voice/turn_core.py` listed under Wave 1 but depends on LOCKED refactor | A3: `turn_core.py` is explicitly Wave 3 (P21-003); Wave 1 parallelism scoped to STT/TTS/provider interfaces + codec + sanitize + cost/metrics only | **CLOSED** | "Audit Round-1 Amendments" line 464; File Structure NEW-file table (line 56); Dependency Map lines 113–118 |

---

## 3. Dimension-by-Dimension Re-Verification

### 3.1 Integration vs. Sidecar

**Verdict: PASS**

- The plan states the architecture principle at the top: "Voice reuses the Hermes turn-core; the only new code is STT/TTS wire, the L6 quarantine wrapper, the Discord voice-channel connection, and the additive sensor/dashboard" (`p21-voice-interface-enterprise-plan.md`, line 25).
- The Hard Rejection Criteria section (line 519) explicitly rejects a sidecar-only design, and the Hermes Core Wiring section (lines 203–220) details the thin adapter pattern: STT → `_process_turn_core()` → TTS.
- Source verification: `_process_and_respond()` (`src/discord/hermes_conversational.py:427–691`) contains the full turn logic; extracting it into a shared `_process_turn_core()` returning `ProcessedTurn` is the design intent, not yet code. This is acceptable for a planning-phase architecture audit because the plan gates the refactor explicitly in P21-003 (LOCKED until P20 pass).

### 3.2 Shared Turn-Core Refactoring Contract

**Verdict: PASS (closed by A1, with one clarifying note)**

- A1 now requires:
  1. Move distress/mood/recall/Hermes/cost/shadow/auto-store into `_process_turn_core()` returning `ProcessedTurn`.
  2. Keep `channel.send` / `_split_response` in the Discord-text adapter only.
  3. Add `source_type: str = "discord"` to memory store and cost calls.
  4. Provide a unit test proving `source_type="voice"` invocation works without importing `discord.TextChannel`.
- This directly addresses Round-1 Finding 2.2.1 and 2.2.2 (`src/discord/hermes_conversational.py:539–541`, `:589–596` still call `channel.send` today).
- **Clarifying note:** The plan says `ProcessedTurn` should live in a shared location importable by both `src/discord/` and `src/voice/` (e.g., `src/voice/types.py` or `src/core/turn_types.py`) (`p21-voice-interface-enterprise-plan.md`, line 462). The File Structure table (line 43) lists `src/voice/types.py` as the home for `ProcessedTurn`. This is sufficient for planning, but the Wave 3 scaffold should commit to a single canonical module before implementation begins.

### 3.3 DRY Safety Hooks

**Verdict: PASS**

- The plan requires voice to reuse `HardStopHandler.check()` on the RAW transcript before sanitization (`p21-voice-interface-enterprise-plan.md`, line 19; line 273).
- `DistressDetector` / `SafeModeController` are reused from the existing path, not duplicated.
- Source verification: `src/core/services/hard_stop_handler.py:89–103` is text-based and reused; `src/life_kernel/heartbeat.py:273` reads the same Redis `life_kernel:hard_stop` key every 1 s.
- **Clarifying note:** The current `HardStopHandler.check()` only mutates internal state and fires callbacks; it does **not** write Redis. The plan implies the voice path will write `life_kernel:hard_stop` either by modifying the locked handler (which the plan correctly avoids) or by registering a Redis-writing callback via `register_on_trigger()`. The plan should explicitly state the callback approach to avoid a hidden dependency on touching `hard_stop_handler.py`.

### 3.4 Latency Budget

**Verdict: PASS (closed by A2)**

- A2 adds an acceptance criterion: if streaming-Hermes is unavailable, accept p50 ~2 s for MVP.
- Source verification: `src/hermes/_session_adapter.py:235–239` confirms `send_message()` runs `agent.run_conversation()` synchronously in a thread, which is non-streaming.
- The plan's E2E p50 target of ~1.5–2.0 s (line 309) is now framed as a target with a documented fallback, matching the source-of-truth.

### 3.5 Two-Tier life_kernel Design

**Verdict: PASS**

- Reactive tier: real-time voice turns bypass the life_kernel graph and use the shared Hermes turn-core.
- Reflective tier: `VoiceSensorAdapter` feeds metadata (not raw audio) into the 30 s awareness loop (`p21-voice-interface-enterprise-plan.md`, lines 228–232).
- Source verification:
  - `src/life_kernel/sensors.py:108–148` defines the `SensorRegistry.sense_all()` loop and the `_SensorAdapter` Protocol.
  - `src/life_kernel/state.py:109–114` defines `add_observations_reducer` capped at 100 entries.
  - `src/life_kernel/heartbeat.py:273` polls the same `life_kernel:hard_stop` Redis key.
- The single-source-of-truth flag is preserved; no new stop path is introduced.

### 3.6 NEW vs. LOCKED File Separation

**Verdict: PASS (with one documentation note)**

- The plan clearly separates NEW files (Wave 1, unblocked) from MODIFIED/LOCKED files (Wave 2+, blocked on P20 pass) in the File Structure table (lines 34–93) and the Global Constraints (line 18).
- `src/discord/hermes_conversational.py:427–691`, `src/core/main.py`, `pyproject.toml`, etc., are correctly marked as LOCKED until P20 production pass.
- **Documentation note:** `src/surveillance/classification.py` is not listed in the File Structure table, but Amendment A7 (line 468) requires adding `voice_raw_audio` event classification to it in P21-004. The File Structure table should be updated to list `src/surveillance/classification.py` as a MODIFIED file in Wave P21-004.

### 3.7 Dependency Map and Parallelism

**Verdict: PASS**

- The Dependency Map (lines 96–118) and parallelism rules are internally consistent and match the LOCKED/NEW gating.
- `turn_core.py` is correctly placed in Wave 3 (P21-003) and depends on the hermes_conversational refactor.
- P21-004 and P21-005 can parallelize after P21-003 because memory writes and consent/HARD-STOP gating are independent surfaces.
- P21-007 (dashboard) can parallelize with P21-004/005/006 because it is additive only.

---

## 4. New Gaps Identified (Round 2)

| ID | Gap | Severity | Recommended Fix |
|---|---|---|---|
| G1 | `safe_word_override.py` is referenced in the P21-005 scaffold but not listed in the File Structure NEW files | LOW | Add `src/voice/safe_word_override.py` to the File Structure table, or clarify that override-detection is folded into `sanitize.py` / `voice_gate.py` |
| G2 | Redis write path for spoken safe-word is implied but not explicit | LOW | Add a sentence in "HARD STOP Behavior for Voice" stating the voice path registers an `HardStopHandler` callback that writes `life_kernel:hard_stop` to the same DB the heartbeat polls (per A4) |
| G3 | `src/surveillance/classification.py` missing from File Structure MODIFIED list | LOW | Add `src/surveillance/classification.py` as MODIFIED in Wave P21-004 per Amendment A7 |

---

## 5. Source-of-Truth Verification Matrix

| Claim in Plan | Source-of-Truth Evidence | Status |
|---|---|---|
| Voice reuses shared Hermes turn-core | `src/discord/hermes_conversational.py:427–691` contains the body to extract | ✅ Confirmed |
| `send_message()` is non-streaming today | `src/hermes/_session_adapter.py:235–239` uses `asyncio.to_thread(agent.run_conversation, ...)` | ✅ Confirmed |
| `life_kernel:hard_stop` polled every 1 s | `src/life_kernel/heartbeat.py:273` reads the Redis key | ✅ Confirmed |
| Sensor Protocol supports new adapters | `src/life_kernel/sensors.py:108–148` `_SensorAdapter` Protocol and `sense_all()` | ✅ Confirmed |
| State reducer caps observations | `src/life_kernel/state.py:109–114` `add_observations_reducer` | ✅ Confirmed |
| `HardStopHandler.check()` is text-based | `src/core/services/hard_stop_handler.py:89–103` | ✅ Confirmed |
| `_process_and_respond` still returns `bool` + sends to `channel` | `src/discord/hermes_conversational.py:491`, `:540–541`, `:589–596`, `hermes_conversational.py:348` | ⚠️ Confirmed current state; A1 covers the required refactor |
| `store_conversation()` currently hardcodes `source="discord_conversation"` | `src/hermes/_memory_bridge.py:274` | ⚠️ Confirmed; A9 covers the `source_type` kwarg |

---

## 6. Risk Register

| ID | Risk | Severity | Status |
|---|---|---|---|
| R1 | Refactor of `_process_and_respond` changes return type and side-effect surface | MEDIUM | Closed by A1 — P21-003 scaffold is explicit |
| R2 | `ProcessedTurn` type not yet in source | LOW | Tracked in Wave 3; `src/voice/types.py` is the planned home |
| R3 | p50 <1.5 s depends on streaming-Hermes | MEDIUM | Closed by A2 — MVP accepts p50 ~2 s |
| R4 | Voice `turn_core.py` depends on LOCKED refactor | LOW | Closed by A3 — Wave 3 dependency is explicit |
| R5 | Redis write for spoken safe-word mechanism not explicit | LOW | New gap G2 — minor clarification needed |

---

## 7. Conditions for Pass

1. Keep A1–A3 amendments verbatim in the plan; no regression that places `turn_core.py` in Wave 1.
2. Address G1–G3 documentation notes before implementation begins (low severity, non-blocking).
3. No runtime code, deploy, or restart occurs in the planning phase (already upheld).

---

## 8. Conclusion

The Round-2 amended P21 Voice Interface plan is architecturally sound. All three Round-1 architecture findings (A1–A3) are **CLOSED** by binding amendments. The plan remains integration-not-sidecar, preserves DRY safety hooks, maintains the two-tier life_kernel design, correctly separates NEW/LOCKED files, and documents parallel/sequential dependencies. The three new gaps (G1–G3) are minor documentation clarifications and do not change the architecture verdict.

**Overall verdict: PASS (with G1–G3 documentation notes).**

---

*Report written to `docs/setup-evidence/P21/evidence/audits/round-2/architecture.md`.*
