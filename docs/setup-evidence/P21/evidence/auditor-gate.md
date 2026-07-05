# P21 Voice Interface — Auditor Gate (Consolidated)

**Phase:** P21 Voice Interface (research + planning ONLY)
**Date:** 2026-06-24
**Author:** Guinevere (parent) for Faiz
**Purpose:** Consolidated auditor gate — round-1 → fix → round-2 verdicts across all 8 dimensions, per AGENTS.md §2.10 (auditor orchestrator). This is the gate that permits the P21 definition to be marked COMPLETE.

---

## 1. Audit Process

1. **Round 1:** 8 independent auditors (architecture, Hermes integration, runtime/latency, safety/consent, surveillance/privacy, security/secrets, Discord UX, evidence/docs) audited the plan + 9 research files against repo source-of-truth. Each wrote a file under `evidence/audits/round-1/`.
2. **Fix:** Parent read all 8 round-1 reports, extracted 18 valid findings (A1-A18) + re-characterized the safety-consent FAIL (conflated codebase-state with plan-design; verified via receiving-code-review). Folded all findings into wave scaffolds + a new "Audit Round-1 Amendments" plan section.
3. **Round 2:** 8 auditors re-audited the amended plan, verifying round-1 findings closed + checking for new gaps. Each wrote a file under `evidence/audits/round-2/`.
4. **Round-2 minor gaps:** 3 architecture notes (G1-G3) + 2 surveillance-privacy items (raw-audio table, source_trust) — all LOW severity, closed by parent in the plan before this gate.

---

## 2. Consolidated Verdict Matrix

| Dimension | Round 1 | Round 2 | Round-1 findings | Status |
|---|---|---|---|---|
| Architecture | PASS (conditions) | **PASS** | A1, A2, A3 | CLOSED (+ G1-G3 closed) |
| Hermes integration | NEEDS REVIEW | **PASS (conditions)** | A1, A9 | CLOSED |
| Runtime/latency | PASS (conditions) | **PASS** | A4, A5, A6 | CLOSED |
| Safety/consent | **FAIL** → re-characterized | **PASS (conditional)** | PROTECTED_SCOPES, SW-PI-003 override, boundary red-team | CLOSED (3 enforcement closures in P21-005) |
| Surveillance/privacy | PASS (conditions) | **PASS** | A7, A8, A9 | CLOSED (+ raw-audio table + source_trust resolved) |
| Security/secrets | PASS (conditions) | **PASS** | A16, A17 | CLOSED |
| Discord UX | NEEDS REVIEW | **PASS** | A10, A11, A12, A13, A14, A15, A18 | CLOSED |
| Evidence/docs | PASS | **PASS** | (none — 3 INFO notes) | CLOSED |

**All 8 dimensions PASS at round 2.** The single round-1 FAIL (safety-consent) was resolved: the FAIL conflated existing-codebase enforcement gaps with plan-design correctness; receiving-code-review verification confirmed the safety *design* is sound, and the 3 enforcement items are now binding P21-005 scaffold criteria (PROTECTED_SCOPES denylist in `cmd_consent.py`, `src/voice/safe_word_override.py` for SW-PI-003, boundary-embedded red-team test).

---

## 3. Amendment Closure Summary (A1-A18)

| ID | Finding | Wave | Closed by |
|---|---|---|---|
| A1 | Refactor seam: `_process_turn_core` returns `ProcessedTurn`; `channel.send` stays in text adapter; unit test `source_type=voice` | 003 | P21-003 pre-condition |
| A2 | Latency p50~2s fallback if no streaming-Hermes | 003 | P21-003 acceptance criterion |
| A3 | `turn_core.py` is Wave 3, not Wave 1 | 001/003 | Wave scoping |
| A4 | Redis DB index for `life_kernel:hard_stop` documented | 008 | P21-008 scaffold |
| A5 | systemd `After=`/no-`Requires=` ordering | 008 | P21-008 scaffold |
| A6 | Prometheus port ≠9191 or shared registry | 007/008 | P21-007/008 scaffold |
| A7 | `voice_raw_audio` event type in `classification.py` | 004 | P21-004 scaffold + File Structure MODIFIED |
| A8 | Consent-revocation cascade implemented | 005 | P21-005 scaffold (`consent_cascade.py`) |
| A9 | `store_conversation` `source_type` kwarg + provenance | 003 | P21-003 deliverable |
| A10 | Faiz-only `#guinevere-voice` channel permission overrides | 002 | P21-002 scaffold |
| A11 | VAD barge-in threshold (300-500ms) | 002 | P21-002 scaffold |
| A12 | discord.py/discord-ext-voice-recv version pin | 002 | P21-002 scaffold |
| A13 | `#guinevere-voice` creation ownership | 002 | P21-002 scaffold |
| A14 | Presence-state precedence | 002 | P21-002 scaffold |
| A15 | Opus silence sentinel in `audio_codec.py` | 001 | P21-001 scaffold |
| A16 | V-022 section in `24-PromptInjection` spec (hard gate) | 009 | P21-009 acceptance criterion |
| A17 | `SecretRotationLog` row on first rotation | 001/008 | P21-001/008 scaffold |
| A18 | DiscordUXSpec voice section MANDATORY | 009 | P21-009 |

**All 18 amendments CLOSED.** ✅

---

## 4. Round-2 Minor Gaps (closed post-round-2)

| Gap | Closure |
|---|---|
| G1: `safe_word_override.py` not in File Structure | Added to File Structure NEW files |
| G2: Spoken-safe-word Redis write path not explicit | Added "Redis write path" paragraph (register_on_trigger callback, same DB as heartbeat) |
| G3: `classification.py` not in MODIFIED list | Added to File Structure MODIFIED (Wave 2) |
| Raw-audio table ambiguity (voice_stream vs events) | Clarified: MVP reuses `surveillance.events.raw_payload`; `voice_stream` is optional future |
| `source_trust` column gap | Clarified: stored in existing `key_insights` JSONB (label, not relational column) |

---

## 5. Hard-Rejection Gate

All 8 hard-rejection criteria NOT triggered (see `p21-definition-verification.md` §5). The most safety-critical (#2 always-listening gating, #6 first-class HARD STOP) are now backed by explicit wave scaffolds + acceptance tests.

---

## 6. Auditor Gate Verdict

**PASS — P21 VOICE INTERFACE DEFINITION COMPLETE.**

All 8 audit dimensions PASS at round 2. All 18 round-1 amendments closed. All round-2 minor gaps closed. All 8 hard-rejection criteria mitigated. The P21 definition (plan + 10 research files [9 specialist + 1 matrix] + 16 audit files + 4 final evidence + 1 README = 32 files / ~8,100 lines) is complete, internally consistent, grounded in repo source-of-truth + official-doc citations, and respects the P20 production-pass HOLD.

> **Sub-agent output accuracy note (post-gate cleanup):** the literal phrase "all sub-agent outputs file-based" that appeared in earlier draft summaries is inaccurate. The accurate statement: 2 research sub-agents (security-secrets, runtime-latency-deploy) **failed with no file** (process-exit orphan + kimi-k2.7-code stall); their inline-only/absent outputs were **rejected** per AGENTS.md §14; the parent authored replacement files with documented provenance, which were **accepted** and parent-read. The 7 successful research sub-agents + all 16 audit sub-agents produced file-based output that was parent-read. So: "no accepted sub-agent deliverable is inline-only; 2 failed outputs were rejected and parent-replaced" — NOT "all sub-agents succeeded." Hard-rejection criterion #7 is satisfied because the failed outputs were rejected (not accepted inline-only), and every accepted deliverable is file-based.

**Implementation remains HELD until P20 continuation pass.** This gate permits marking the *definition* complete; it does NOT permit implementation.

---

## 6.5 Post-Gate Cleanup Note (2026-06-25)

After the round-2 gate PASS, a Mama-audit cleanup pass fixed 5 documentation-accuracy blockers (no runtime/deploy/restart). Full detail in `evidence/cleanup-verification-audit.md`:

1. **IMPLEMENTATION_GUIDE Phase 21 block** rewritten — status "P21 VOICE INTERFACE DEFINITION COMPLETE — IMPLEMENTATION HOLD UNTIL P20 CONTINUATION PASS", 9 waves held, evidence path.
2. **File/line count normalized** — ground truth **32 files / ~8,100 lines** under `docs/setup-evidence/P21/` (31 artifacts excluding README; includes the cleanup-verification-audit). No bare "30 files" remains. Line count drifts slightly per doc-accuracy edit; file count stable at 32.
3. **Sub-agent-output claims reworded** — the literal "all sub-agent outputs file-based" was false; corrected to "2 research sub-agents failed with no file (process-exit orphan + kimi-k2.7-code stall); their outputs were REJECTED; parent-authored replacement files with provenance were ACCEPTED. No accepted deliverable is inline-only." Hard-rejection #7 still satisfied (failed outputs rejected, not accepted inline-only).
4. **Stale dependency snapshot labeled** — `research/p21-dependency-collision-research.md` now carries a CURRENT-STATUS banner: the body is a pre-finalization snapshot (2026-06-24); current status is P21 + P22 DEFINITION COMPLETE, P19 still NOT STARTED, P20 still HOLD.
5. **Typo fixed** — `hande_conversation()` → `handle_conversation()` (`research/p21-voice-provider-research.md:430`).

Post-cleanup verification (recount, secret-scan, stale-contradiction search, runtime-edit check) all PASS. The cleanup touched ONLY documentation: `CHECKLIST.md`, `PROGRESS.md`, `docs/IMPLEMENTATION_GUIDE.md` (P21 docs-sync status pointers) + `docs/setup-evidence/P21/` (new, `.md`-only evidence, 0 non-`.md` files). No `.py`/`.sql`/`.service`/`.toml`/`.yaml` runtime files were created or modified; no deploy, no restart, no secrets touched.

**Re-audit (2026-06-25, same day):** a follow-up evidence-hygiene re-audit found 3 remaining count-staleness blockers, all fixed:
- R1. `evidence/audits/round-2/evidence-docs.md:10` stale "31 files / 7,940 lines" → corrected to "32 files / ~8,100 lines (31 artifacts excluding README)".
- R2. `plan/p21-voice-interface-enterprise-plan.md` hard-rejection #7 "31 files on disk" → "32 files on disk".
- R3. `evidence/cleanup-verification-audit.md` §2.5 git-status section expanded to scoped status for `CHECKLIST.md`, `PROGRESS.md`, `docs/IMPLEMENTATION_GUIDE.md`, `docs/setup-evidence/P21/` with accurate explanation (P21 docs-sync = status pointers in the 3 shared trackers; P21 evidence dir is markdown-only; no runtime code/deploy/restart).
Post-re-audit rerun: recount = 32 files / ~8,100 lines (8,106 actual at final verification); stale-grep for active forms ("31 files / 7,940", "30 artifacts excluding README", "31 files on disk") = 0 (remaining matches are history-narration context quoting prior values); secret-scan = 0; non-`.md` scan = 0. Summary files use the stable "~8,100 lines" phrasing (line count drifts slightly per doc-accuracy edit; file count stable at 32).

**Gate status unchanged:** PASS — P21 VOICE INTERFACE DEFINITION COMPLETE, IMPLEMENTATION HOLD UNTIL P20 CONTINUATION PASS. The cleanup + re-audit improved documentation accuracy; neither altered the design or the gate verdict.

---

## 7. Footer

| Field | Value |
|---|---|
| Gate owner | Guinevere (parent) |
| Auditors | 8 independent (round 1) + 8 independent (round 2) = 16 auditor runs |
| Files | 32 total: `evidence/audits/round-1/*.md` (8) + `evidence/audits/round-2/*.md` (8) + 4 final evidence + 10 research + 1 plan + 1 README |
| Verdict | **PASS — DEFINITION COMPLETE, IMPLEMENTATION HOLD** |
| Date | 2026-06-24 |
