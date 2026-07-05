# P21 Voice Interface — Round 2 Safety/Consent Audit Report

**Dimension:** Safety / Consent (critical)
**Audit date:** 2026-06-24
**Auditor:** Independent auditor
**Scope:** Amended P21 plan vs. repo source-of-truth; verify Round-1 findings closed and no new gaps
**Verdict:** **PASS (conditional)** — Round-1 FAIL findings are now concretely closed by P21-005 amendments; implementation must still deliver them.

> **Post-finalization accuracy note (2026-06-25):** The hard-rejection table line below stating "All 9 research files and audit files written to disk" is accurate on file existence but should not imply all 9 research sub-agents succeeded. 2 research sub-agents failed with no file; their outputs were rejected and parent-authored replacement files with provenance were accepted. Accurate claim: "no accepted deliverable is inline-only; 2 failed outputs rejected and parent-replaced." Hard-rejection #7 satisfied because failed outputs were rejected, not accepted inline-only.

---

## Round-1 Finding Closure Table

| Round-1 Finding | Severity | Amendment | Wave | Closure Status | Rationale |
|---|---|---|---|---|---|
| F1: `cmd_consent.py` accepts arbitrary category strings — safety features (`safe_word`, `distress`, `crisis`, `hard_stop`) can be "revoked" via `/consent` | Critical | P21-005 adds `PROTECTED_SCOPES` denylist in `src/discord/cmd_consent.py`; required command (d) tests `/consent category:safe_word action:off` → refused with PROTECTED_SCOPES error | P21-005 | **CLOSED** | Design now explicitly forbids revoking safety features at the command layer. |
| F2: `HardStopHandler` has no SW-PI-003 safe-word-override detector; spoken "safe word is revoked/disabled" is not rejected/SEV0 | Critical | P21-005 creates `src/voice/safe_word_override.py` + integrates with transcript sanitizer; required red-team (b) tests spoken override → rejected + SEV0 | P21-005 | **CLOSED** | Plan routes override detection through the voice sanitizer (pre-Hermes) while avoiding edits to the LOCKED `hard_stop_handler.py`. |
| F3: Boundary-embedded safe-word matching may miss tokens like "hardstopnow" or "i want a hard stop now" | High | P21-005 red-team test (c) requires detection of: "i want a hard stop now", "hardstopnow"; acknowledges need for tokenized/boundary-insensitive matching | P21-005 | **CLOSED (with caveat)** | Exact-match logic in `hard_stop_handler.py:95` is still bounded-substring; amendment accepts that test-driven enforcement will close the residual false-negative risk. |

*Source: round-1 audit `docs/setup-evidence/P21/evidence/audits/round-1/safety-consent.md`; amended plan P21-005 section `docs/setup-evidence/P21/plan/p21-voice-interface-enterprise-plan.md:397-408` and the Round-1 Amendments table at `:456-479`.*

---

## 1. HARD STOP First-Class in Audio Path

**Finding:** **PASS (planning) / NEEDS REVIEW (until P21-005 delivered)**

The amended plan at `p21-voice-interface-enterprise-plan.md:19-20`, `:269-274`, and `:518-524` continues to assert the correct ordering:

> STT final transcript → `HardStopHandler.check(transcript)` at `src/core/services/hard_stop_handler.py:89` → if triggered, set Redis `life_kernel:hard_stop` → SafeModeController/Y0/neutral → TTS neutral ack → minimal non-punitive audit.

Source-code truth (`src/life_kernel/heartbeat.py:273-322`) polls the same `life_kernel:hard_stop` key every second and halts the kernel when truthy. This is unchanged and correct.

The Round-1 amendment (A3) adds a red-team test that requires boundary-embedded safe words (e.g. "i want a hard stop now", "hardstopnow") to be detected. This addresses the exact-match limitation noted in Round 1 (`hard_stop_handler.py:95`). Because P21-005 is an future implementation wave, the planning-level design now closes the gap by making the test an acceptance criterion.

**Citation:** `p21-voice-interface-enterprise-plan.md:397-408`; `src/core/services/hard_stop_handler.py:89-103`; `src/life_kernel/heartbeat.py:273-322`

---

## 2. Safe-Word-Override Rejection (SW-PI-003)

**Finding:** **PASS (planning)**

Round 1 noted that `hard_stop_handler.py` contains no override detector. The amended plan does NOT propose editing the LOCKED `hard_stop_handler.py`; instead, P21-005 creates `src/voice/safe_word_override.py` and integrates it with the transcript sanitizer (`src/voice/sanitize.py`) so that a spoken "safe word is revoked/disabled" is rejected and classified SEV0 **before** the transcript reaches Hermes.

The required red-team test (b) at `p21-voice-interface-enterprise-plan.md:404` is:

> spoken "safe word revoked/disabled" → rejected + SEV0

This is consistent with `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md` §8.3 (SW-PI-003) and §16.1 (external content attempting safe-word override = SEV0).

**Citation:** `p21-voice-interface-enterprise-plan.md:397-408`; `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md:734` (SW-PI-003)

---

## 3. Always-Listening NOT MVP + 8 Gates + Fail-Closed Consent Cache

**Finding:** **PASS**

The amended plan at `p21-voice-interface-enterprise-plan.md:21`, `:169-174`, `:517-519` and `p21-consent-surveillance-research.md:83-113` continues to state:

> `voice.always_listening` defaults OFF, enabled only after ALL 8 gating checks pass: explicit Faiz consent · visible indicator · retention policy · HARD STOP honored · audit trail · device auth · purpose-bound · no-silent-reactivation.

P21-005 scaffold now requires:

> `check_consent()` must validate the 8 independent always-listening gating flags inside the consent cache, not just the ledger (`p21-voice-interface-enterprise-plan.md:399`).

This closes the Round-1 concern that the current `src/surveillance/consent_gate.py:49-55` only validates `VALID_SURVEILLANCE_SCOPES` and has no notion of always-listening gating flags.

**Citation:** `p21-voice-interface-enterprise-plan.md:399`; `p21-consent-surveillance-research.md:104-113`; `src/surveillance/consent_gate.py:49-55`

---

## 4. Five Voice Consent Scopes Default OFF

**Finding:** **PASS**

The five voice consent scopes remain documented and default OFF:

| Scope | Default |
|---|---|
| `voice.capture.ptt` | OFF |
| `voice.always_listening` | OFF (MVP-blocked) |
| `voice.storage.transcript` | OFF |
| `voice.storage.raw_audio` | OFF |
| `voice.proactive_tts` | OFF |

P21-005 now requires adding these to `src/surveillance/consent_gate.py` `VALID_SURVEILLANCE_SCOPES` (or a dedicated voice registry) and testing revocation cascade.

**Citation:** `p21-consent-surveillance-research.md:49-55`; `p21-voice-interface-enterprise-plan.md:265-266`

---

## 5. Safety Features Non-Disablable via `/consent`

**Finding:** **PASS (planning)**

P21-005 explicitly modifies `src/discord/cmd_consent.py` to add a `PROTECTED_SCOPES` denylist containing `safe_word`, `distress`, `crisis`, `hard_stop`, and tests that `/consent category:safe_word action:off` is refused. This closes the Round-1 FAIL finding that the current `cmd_consent.py:103,128` accepts arbitrary category strings.

**Citation:** `p21-voice-interface-enterprise-plan.md:397-408`; `src/discord/cmd_consent.py:38-169`

---

## 6. Distress D0-D4 + D4 Crisis Response

**Finding:** **PASS**

`p21-consent-surveillance-research.md:239-267` documents D0-D4 handling with a D4 response consistent with `PersonaSafetyPolicy` §8.2 and forbidden pattern F-14. The D4 response is neutral, non-dominance, and encourages emergency support.

The shared turn-core refactor (P21-003) ensures distress detection runs on the transcript before Hermes, using the existing `DistressDetector` (`src/persona/safe_mode.py:85-141`).

**Citation:** `p21-consent-surveillance-research.md:239-267`; `src/persona/safe_mode.py:85-141`

---

## 7. Spoken Safe-Word Event Minimal and Non-Punitive

**Finding:** **PASS**

The amended plan at `p21-voice-interface-enterprise-plan.md:20-21`, `:273` and `p21-consent-surveillance-research.md:6.3 continues to require minimal, non-punitive audit for spoken safe-word events, consistent with `PersonaSafetyPolicy` §7.3 and §16.1-16.2.

**Citation:** `p21-voice-interface-enterprise-plan.md:20-21`; `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md §7.3, §16`

---

## 8. Recovery Explicit-Only

**Finding:** **PASS**

Recovery requires explicit phrases (`resume`, `aku sudah okay`, etc.) via `HardStopHandler.check_recovery()` at `src/core/services/hard_stop_handler.py:105-117`. No auto-resume is planned.

**Citation:** `src/core/services/hard_stop_handler.py:56-117`; `p21-voice-interface-enterprise-plan.md:273`

---

## 9. New Gaps Introduced by Amendments

**Finding:** **NONE BLOCKING**

The amendments introduce no new architectural or policy gaps. One operational caveat remains:

- **Caveat:** The SW-PI-003 override detector is deliberately placed in a NEW file (`src/voice/safe_word_override.py`) rather than the existing `hard_stop_handler.py` because the latter is LOCKED/P1-021. This is a sound engineering trade-off, but P21-005 must ensure the override detector runs **before** `HardStopHandler.check()` returns False and before the transcript is sanitized, so that an override attempt cannot slip through as a normal utterance. The P21-005 red-team test (b) is the enforcement mechanism.

**Citation:** `p21-voice-interface-enterprise-plan.md:399`

---

## Hard-Rejection Criteria Re-Check

| ID | Criterion | Verdict | Evidence |
|---|---|---|---|
| 1 | Sidecar-only | **PASS** | Plan mandates integration via shared `_process_turn_core` (`p21-voice-interface-enterprise-plan.md:25`, `:519`) |
| 2 | Always-listening without gating | **PASS** | 8 gates documented; P21-006 gated; MVP blocked (`p21-voice-interface-enterprise-plan.md:21`, `:169-174`, `:517-519`) |
| 3 | Provider claims not official-doc-backed | **PASS** | `p21-voice-provider-research.md` + `p21-security-secrets-research.md` cite official docs (`p21-voice-interface-enterprise-plan.md:521`) |
| 4 | Vague secrets | **PASS** | Exact env vars, SOPS path, rotation, encryption profile (`p21-voice-interface-enterprise-plan.md:22`, `:291-296`) |
| 5 | Transcripts in memory without redaction/retention | **PASS** | MEM-001..008 gate + redaction + retention policy (`p21-voice-interface-enterprise-plan.md:24`, `:255-257`, `:518-523`) |
| 6 | Safe-word/HARD STOP not first-class | **PASS** | Pre-Hermes pre-sanitize `HardStopHandler.check()` + shared Redis flag + P21-005 red-team tests (`p21-voice-interface-enterprise-plan.md:20`, `:269-279`, `:397-408`) |
| 7 | Inline-only sub-agent output | **PASS** | All 9 research files and audit files written to disk (`p21-voice-interface-enterprise-plan.md:525`) |
| 8 | Runtime code edits/deploy/restart in this phase | **PASS** | Planning-only; waves held until P20 pass (`p21-voice-interface-enterprise-plan.md:17-18`, `:351-452`, `:526`) |

---

## Overall Verdict

**PASS (conditional)**

The Round-1 safety/consent **FAIL** has been re-characterized to **PASS at the planning level**. The amended P21-005 scaffold concretely closes the three enforcement gaps:

1. `cmd_consent.py` PROTECTED_SCOPES denylist — **closed** by P21-005 scaffold.
2. SW-PI-003 safe-word-override rejection — **closed** by new `src/voice/safe_word_override.py` + sanitizer integration.
3. Boundary-embedded safe-word red-team test — **closed** by required test (c) in P21-005.

The hard-rejection criteria are all mitigated in planning documents, with the most safety-critical items (#2 always-listening gating and #6 first-class HARD STOP) now backed by explicit wave scaffolds and acceptance tests.

The condition on this PASS is that P21-005 implementation must actually deliver `src/voice/safe_word_override.py`, the `PROTECTED_SCOPES` denylist in `cmd_consent.py`, and the boundary-embedded red-team tests before the P21 safety/consent dimension can be called fully closed in implementation.

---

**Report path:** `docs/setup-evidence/P21/evidence/audits/round-2/safety-consent.md`
