# P21 Voice Interface — Final Planning Report

**Phase:** P21 Voice Interface — RESEARCH + PLANNING ONLY (NO implementation/deploy/restart)
**Date:** 2026-06-24
**Author:** Guinevere (parent) for Faiz
**Status:** **P21 VOICE INTERFACE DEFINITION COMPLETE — IMPLEMENTATION HOLD UNTIL P20 CONTINUATION PASS**

---

## 1. Executive Summary

Phase 21 defined a safe, deeply-integrated voice interface for Guinevere end-to-end — **without writing any runtime code, deploying, or restarting production.** The definition covers STT ingestion (push-to-talk + gated wake-word), TTS replies, realtime interruption/barge-in, consent gating, and surveillance-class retention, all wired into the existing Hermes turn-core, life_kernel, memory, consent, audit, and HARD STOP infrastructure — **not** as a sidecar.

The central architectural insight: **a voice transcript is text.** The existing `HardStopHandler.check()`, `DistressDetector`, `SafeModeController`, injection-sanitizer, memory bridge, and cost tracker all operate on text, so a voice turn = STT(transcript) → the same shared turn-core Discord text uses → TTS(response). This yields safety-by-construction (zero duplicated safety hooks) and satisfies the P21 hard-rejection rule against sidecar-only design.

Implementation waves P21-001..009 are fully defined and scaffolded but **HELD** until the P20 Living Autonomy Kernel production-pass (LK-017 soak) completes, because several waves touch LOCKED P20 files.

---

## 2. What Was Done (this phase)

| Deliverable | Path | Status |
|---|---|---|
| Tool/skill coverage matrix | `research/p21-tool-skill-coverage-matrix.md` | ✅ |
| 9 specialist research files | `research/p21-{voice-provider,discord-voice,hermes-core-integration,life-kernel-integration,memory-transcript,consent-surveillance,security-secrets,runtime-latency-deploy,dependency-collision}-research.md` | ✅ |
| Enterprise plan (planner gate) | `plan/p21-voice-interface-enterprise-plan.md` | ✅ |
| Audit round 1 (8 dimensions) | `evidence/audits/round-1/*.md` | ✅ |
| Plan amendments (18 findings A1-A18) | folded into plan wave scaffolds + "Audit Round-1 Amendments" section | ✅ |
| Audit round 2 (8 dimensions) | `evidence/audits/round-2/*.md` | ✅ (all PASS) |
| Round-2 minor gaps closed | G1-G3 + raw-audio + source_trust | ✅ |
| Definition verification | `evidence/p21-definition-verification.md` | ✅ |
| Auditor gate | `evidence/auditor-gate.md` | ✅ |
| This final report | `evidence/final-p21-planning-report.md` | ✅ |

**Total: 1 plan + 10 research (9 specialist + 1 coverage matrix) + 16 audit (8×2 rounds) + 4 final evidence (incl. cleanup-verification-audit) + 1 README = 32 files / ~8,100 lines under `docs/setup-evidence/P21/` (31 artifacts excluding README).** (Counts as of post-re-audit 2026-06-25; the cleanup-verification-audit is the 4th final-evidence file. Line count drifts slightly per doc edit; file count stable at 32.)

---

## 3. Key Architectural Decisions

1. **Integration, not sidecar.** Voice reuses the Hermes text turn-core via a refactored `_process_turn_core()` (extracted from `_process_and_respond()` at `src/discord/hermes_conversational.py:427-691`). The only new code is STT/TTS wire, the L6 quarantine wrapper, the Discord voice-channel connection, and additive sensor/dashboard. (Hard-rejection #1 mitigated.)
2. **HARD STOP is first-class in the audio path.** `HardStopHandler.check(transcript)` runs on the RAW transcript BEFORE sanitization (SW-PI-008) and BEFORE Hermes; a spoken safe word sets the same Redis `life_kernel:hard_stop` flag the 1s heartbeat polls. Zero false-negative tolerance; SW-PI-003 override rejection via `src/voice/safe_word_override.py` + sanitizer. (Hard-rejection #6 mitigated.)
3. **Always-listening is NOT MVP.** `voice.always_listening` defaults OFF; enabled only after 8 gates (consent + visible indicator + retention + HARD STOP + audit + device auth + purpose-bound + no-silent-reactivation). Fail-closed consent cache. (Hard-rejection #2 mitigated.)
4. **Voice transcript = untrusted text (Trust 6).** Registered as injection vector V-022; runs through classify→sanitize→quarantine→L7-L9; never reaches privileged L0-L6. Secret-in-transcript scanner (clipboard-analog). (Hard-rejection #3, #5 mitigated.)
5. **New `guinevere-voice` systemd service** (isolated, independent restart/rollback, `MemoryLimit=512M`). Feature-flag + `/voice-off` kill switch + HARD STOP + `systemctl stop` rollback.
6. **P19 forward-compat:** voice episodes carry nullable `project_id` so multi-project namespaces can partition later without a backfill.
7. **P20 non-interference:** P21 changes to life_kernel are strictly additive (new `VoiceSensorAdapter`, `NotRequired` state fields, dashboard section); the 1s HARD-STOP loop, 6-interval schedule, `hermes_brain.py`, `graph.py`, and the Hermes core are untouched. LOCKED-file waves blocked until P20 pass.

---

## 4. Provider Shortlist (official-doc cited, retrieved 2026-06-24)

- **STT (primary):** Deepgram Nova-3 Multilingual ($0.0058/min streaming, sub-300ms, id-ID)
- **TTS (primary):** Cartesia Sonic 3.5 (~1 credit/char, 40-188ms TTFA, native id-ID)
- **VAD:** Silero VAD (offline, free) · **Wake-word:** openWakeWord (free, offline)
- **Local fallback:** faster-whisper + Piper (id-ID `news_tts`) — $0, no network
- **Realtime (NOT MVP):** OpenAI Realtime gpt-realtime-mini / Deepgram Voice Agent API

Final selection at P21-001 execution after a live benchmark against Faiz's id+en code-switching audio.

---

## 5. Audit Outcome

- **Round 1:** 8 dimensions → 5 PASS (conditions), 2 NEEDS REVIEW, 1 FAIL (safety-consent).
- **Fix:** 18 findings (A1-A18) folded into wave scaffolds; safety-consent FAIL re-characterized (conflated codebase-state with plan-design; 3 enforcement closures added to P21-005).
- **Round 2:** 8 dimensions → **all PASS.** All 18 amendments CLOSED. 5 round-2 minor gaps closed.

---

## 6. Hard-Rejection Criteria — All Mitigated

| # | Criterion | Mitigated |
|---|---|---|
| 1 | Sidecar-only without Hermes integration | ✅ option (a) thin adapter |
| 2 | Always-listening without gating | ✅ NOT MVP; 8 gates |
| 3 | Provider claims not official-doc-backed | ✅ 58+ citations |
| 4 | Vague secrets | ✅ SOPS/age, exact env vars |
| 5 | Transcripts in memory without redaction/retention | ✅ MEM-001..008 + redaction + 24h raw |
| 6 | Safe-word/HARD STOP not first-class | ✅ pre-Hermes pre-sanitize + Redis flag |
| 7 | Inline-only sub-agent output | ✅ NOT triggered | 32 files on disk (31 artifacts + README). Note: 2 research sub-agents (security-secrets, runtime-latency-deploy) failed/no-file (process-exit orphan + kimi-k2.7-code stall); their inline-only/absent outputs were REJECTED; parent authored replacement files with documented provenance, which were accepted. So "no accepted sub-agent output is inline-only" — not "all sub-agents succeeded". |
| 8 | Runtime edits/deploy/restart in this phase | ✅ planning-only |

---

## 7. Implementation Waves (HELD until P20 pass)

P21-001 STT/TTS abstraction → P21-002 Discord PTT MVP → P21-003 Hermes voice turn pipeline (BLOCKED P20) → P21-004 transcript memory+retention (BLOCKED P20) → P21-005 consent+HARD STOP+safe-word → P21-006 VAD/wake-word gated → P21-007 dashboard → P21-008 deploy+smoke+rollback (BLOCKED P20) → P21-009 audit+soak+final.

Wave 1 (NEW files) is technically unblocked but NOT executed in this planning phase per the P21 objective.

---

## 8. Caveats

1. **Two research files were parent-authored** (`p21-security-secrets-research.md`, `p21-runtime-latency-deploy-research.md`) after their specialist sub-agents failed with no file (process-exit orphan + kimi-k2.7-code stall). Their inline-only/absent outputs were **rejected**; the parent authored replacement files with documented provenance notes, which were **accepted** and parent-read. Official-doc citations were gathered directly by the parent. The other 7 research files are sub-agent-authored and parent-read. This means the literal claim "all sub-agent outputs file-based" is **false** — the accurate claim is "no accepted sub-agent deliverable is inline-only; 2 failed outputs were rejected and parent-replaced."
2. **Implementation is HELD.** This phase produced a definition, not running code. Waves execute later, gated on P20 production-pass.
3. **P20 timing is external.** The HOLD duration depends on the P20 LK-017 24h clean-soak completing.
4. **Provider pricing/latency** are 2026-06-24 snapshots; verify freshness at P21-001 execution.

---

## 9. Boundary Compliance

No persona drift, no consent violation, no surveillance overreach, no Y6, no HARD STOP bypass, no distress-suppression, no secret/intimate data exposure. No runtime code edited, no deploy, no restart, no destructive op. P20 production-pass HOLD respected. Sub-agent output discipline: 2 research sub-agents failed with no file (rejected); parent-authored replacement files with provenance were accepted and parent-read; all 7 successful sub-agent research files + all 16 audit files are file-based and parent-read.

---

## 10. Final Status

**P21 VOICE INTERFACE DEFINITION COMPLETE — IMPLEMENTATION HOLD UNTIL P20 CONTINUATION PASS.**

---

## 11. Footer

| Field | Value |
|---|---|
| Report author | Guinevere (parent) for Faiz |
| Phase | P21 Voice Interface (planning) |
| Artifacts | 32 files / ~8,100 lines (31 artifacts excluding README: 1 plan + 10 research + 16 audit + 4 final evidence) — post-re-audit 2026-06-25 |
| Audit | 2 rounds × 8 dimensions, all round-2 PASS |
| Hard-rejection | 8/8 mitigated |
| Date | 2026-06-24 |
| Verdict | **DEFINITION COMPLETE — IMPLEMENTATION HOLD** |
