# P21 Voice Interface — Round 1 Safety/Consent Audit Report

**Dimension:** Safety / Consent (most critical)  
**Audit date:** 2026-06-24  
**Auditor:** Independent auditor  
**Scope:** P21 planning-phase plan + research documents vs. repo source-of-truth  
**Verdict:** **FAIL** (hard-rejection criterion #6 is not fully mitigated in the planning documents; #2 is mitigated in prose but the evidence is insufficient to call it a clean PASS).

---

## Hard-Rejection Criteria Summary

| ID | Criterion | Plan/Research Claim | Audit Finding |
|---|---|---|---|
| 2 | Always-listening allowed without explicit consent + visible indicator + retention policy + HARD STOP + audit + device auth + purpose-bound + no-silent-reactivation | `voice.always_listening` defaults OFF, NOT MVP, 8 gates required | Mitigated in plan, but research documents are inconsistent about whether a "safe-word wake" mic is ever acceptable. FAIL-adjacent. |
| 6 | Safe-word/HARD STOP not first-class in audio path | `HardStopHandler.check(transcript)` runs on RAW transcript pre-sanitization, sets `life_kernel:hard_stop` | **FAIL** — plan says the right thing, but source code `hard_stop_handler.py` does **not** detect safe-word override attempts or classify them SEV0; it also has a false-positive/negative issue where a safe word embedded mid-sentence may not be detected. |

---

## 1. HARD STOP First-Class in Audio Path

**Finding:** **NEEDS REVIEW / PARTIAL FAIL**

The plan (`p21-voice-interface-enterprise-plan.md`:19-20, :269-274) and `p21-security-secrets-research.md`:97-109 both correctly state the ordering:

> STT final transcript → `HardStopHandler.check(transcript)` at `src/core/services/hard_stop_handler.py:89` → if triggered, set Redis `life_kernel:hard_stop`.

`p21-hermes-core-integration-research.md`:276-277 also states:

> The existing safe-word classifier runs BEFORE sanitization on RAW input.

`src/core/services/hard_stop_handler.py:89-103` indeed operates on a text string:

```python
def check(self, message: str) -> bool:
    msg_lower = message.lower().strip()
    # ... exact + semantic matching
```

So a transcript string is a valid input surface.

**However**, the source code at `src/core/services/hard_stop_handler.py:42-54` uses exact triggers and simple semantic patterns, and the exact matching logic at line 95 is:

```python
if trigger == msg_lower or f" {trigger} " in f" {msg_lower} ":
```

This means an safe word appearing at the start or end of a longer sentence without surrounding spaces will **not** match the exact triggers. For example, "I want a hard stop now" will not match `" hard stop "` because it is preceded by "a " and followed by " now". The semantic patterns do not cover every form of embedding. This is a false-negative risk in a zero-tolerance path.

**Gap:** The plan does not acknowledge this exact-match limitation or propose extending `HardStopHandler` (e.g., by tokenization or boundary-insensitive matching) for voice. Since the spoken safe word may be embedded in a natural sentence, this is a safety gap.

**Citation:** `src/core/services/hard_stop_handler.py:42-103`

---

## 2. Spoken Safe Word Sets Redis `life_kernel:hard_stop`

**Finding:** **PASS (in plan)** / **NEEDS REVIEW (against source)**

The plan (`p21-voice-interface-enterprise-plan.md`:228) and `p21-life-kernel-integration-research.md`:49-53 propose:

```python
await redis_client.set("life_kernel:hard_stop", "voice_safe_word")
```

`src/life_kernel/heartbeat.py:273-275` polls the same key every second:

```python
hard_stop_key = "life_kernel:hard_stop"
hard_stop_value = await self.redis_client.get(hard_stop_key)
```

When truthy, `heartbeat.py:299-322` halts the kernel. So the proposed voice path shares the same halt mechanism as the text path.

**Gap:** The plan proposes setting the Redis key directly from the voice pipeline, but it does not specify whether this SET will be wrapped in a callback registered via `HardStopHandler.register_on_trigger()` or done imperatively. Using `register_on_trigger` would be more consistent with the handler's design. The plan's direct-SET approach is acceptable for research, but the shared state is only a Redis string; there is no explicit guarantee that `HardStopHandler.state` and the Redis flag stay synchronized if the text path and voice path use different code paths.

**Citations:** `src/life_kernel/heartbeat.py:273-322`; `src/core/services/hard_stop_handler.py:66-79`

---

## 3. Zero False-Negative Tolerance + Safe-Word-Override Rejection

**Finding:** **FAIL**

The plan and research repeatedly claim zero false-negative tolerance and that spoken safe-word-override attempts ("safe word is revoked/disabled") are rejected and classified SEV0 (`p21-security-secrets-research.md`:110; `p21-voice-interface-enterprise-plan.md`:279).

However, the actual `HardStopHandler.check()` implementation at `src/core/services/hard_stop_handler.py:89-103` does **not** contain any safe-word-override detection. It only detects triggers that *activate* safe mode. It does **not** detect or classify attempts to revoke/disable the safe word. There is no SEV0 classification logic in the handler.

Policy `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md` §8.3 (SW-PI-003) requires rejecting "safe word was revoked" and classifying it SEV0, but this is not implemented in `hard_stop_handler.py`. The plan documents the requirement but does not propose a concrete implementation (e.g., a new method `check_override_attempt()` or integration with the injection sanitizer) in the voice path.

**Gap:** The planning documents assume the existing `HardStopHandler` covers this, but it does not. A zero-tolerance claim without an implemented override detector is a critical gap.

**Citations:** `src/core/services/hard_stop_handler.py:89-118`; `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md` §8.3 (SW-PI-003)

---

## 4. Always-Listening NOT MVP + 8 Gates + Fail-Closed Consent Cache

**Finding:** **PASS / NEEDS REVIEW**

`p21-voice-interface-enterprise-plan.md`:20-21 and `:169-174` state:

> Always-listening is NOT MVP ... enabled only after ALL 8 gating checks pass.

`p21-consent-surveillance-research.md`:83-87 and `:89-102` enumerate the 8 gates and state the consent cache must be fail-closed.

The 5 consent scopes are listed at `p21-consent-surveillance-research.md`:49-55 and confirmed to default OFF:

| Scope | Default |
|---|---|
| `voice.capture.ptt` | OFF |
| `voice.always_listening` | OFF (MVP-blocked) |
| `voice.storage.transcript` | OFF |
| `voice.storage.raw_audio` | OFF |
| `voice.proactive_tts` | OFF |

`src/surveillance/consent_gate.py:49-55` currently defines `VALID_SURVEILLANCE_SCOPES` without voice scopes. The research notes that voice scopes must be added to `VALID_SURVEILLANCE_SCOPES` or a dedicated voice registry. Because this is a planning phase, the absence of code changes is expected, but the plan does not explicitly require updating `src/surveillance/consent_gate.py` in the implementation waves — it mentions modifying `src/surveillance/consent_gate.py` in P21-005, but the exact line/scope addition is not detailed.

**Gap:** The plan says the consent cache is fail-closed, but it does not explicitly state that `voice.always_listening` must be checked against the independent 8-gate flags inside the cache itself. The current `check_consent()` function only validates against `consent.consent_ledger`; it has no notion of "always-listening gating flags." This is a design-detail gap, not a hard fail, but it is flagged as NEEDS REVIEW.

**Citations:** `src/surveillance/consent_gate.py:49-290`; `p21-consent-surveillance-research.md`:104-113

---

## 5. Five Voice Consent Scopes Default OFF

**Finding:** **PASS**

The five scopes are documented and all default OFF. The plan's consent flow (`p21-voice-interface-enterprise-plan.md`:263-266) and `p21-consent-surveillance-research.md`:49-55 align.

**Citation:** `p21-consent-surveillance-research.md`:49-55

---

## 6. Safety Features Cannot Be Disabled via `/consent`

**Finding:** **PASS (in plan)** / **FAIL (against current source)**

The plan (`p21-voice-interface-enterprise-plan.md`:140-148) and `p21-consent-surveillance-research.md`:139-149 state that `/consent` cannot be used to disable safe-word detection, distress detection, crisis response, or audit logging.

However, the current `src/discord/cmd_consent.py` has no such restriction. It accepts any `category` string and adds it to the grant set (`cmd_consent.py:103-112`, `:127-138`). There is no validation that the category is allowed or that it corresponds to a safety feature. For example, a user could (theoretically) run `/consent category:safe_word action:off` and the command would store it without complaint.

**Gap:** The plan assumes the future `/consent` extension will enforce non-disablable safety features, but it does not propose a concrete enforcement mechanism (e.g., an allowlist of categories, a safety-feature denylist, or a validation check in `cmd_consent.py`).

**Citation:** `src/discord/cmd_consent.py:38-169`

---

## 7. Distress D0-D4 Handling + D4 Crisis Response

**Finding:** **PASS (in plan)** / **NEEDS REVIEW (D4 response not explicitly implemented)**

`p21-consent-surveillance-research.md`:239-267 describes D0-D4 handling and provides an allowed D4 response consistent with `PersonaSafetyPolicy` §8.2 and forbidden pattern F-14.

`src/persona/safe_mode.py:1-141` defines the `DistressDetector` with D4 patterns and the `DISTRESS_RESPONSES` dictionary. The D4 response text is generic ("Emergency contact notification..."), but the plan does not propose modifying it for voice. The persona-safe D4 response in the research is appropriate.

**Gap:** The plan does not explicitly require that the voice path run `DistressDetector.detect(transcript)` **before** Hermes. `p21-hermes-core-integration-research.md`:276 says the shared turn core runs distress detection, but it also says the safe-word classifier runs before sanitization. The ordering of distress vs. safe-word is not clearly specified.

**Citation:** `src/persona/safe_mode.py:85-141`

---

## 8. Voice Confrontation During Safe-Mode/Distress/Crisis Classified SEV0/SEV1

**Finding:** **PASS**

`p21-consent-surveillance-research.md`:187-195 and `p21-voice-interface-enterprise-plan.md`:269-271 state that voice confrontation during restricted states is SEV0/SEV1. This aligns with `PersonaSafetyPolicy` §11.2 and `SurveillanceDataPolicy` §13, and `src/surveillance/safe_mode.py:30-41` lists blocked actions including `confrontation`, `blackmail`, `punishment`, etc.

**Citation:** `src/surveillance/safe_mode.py:30-41`

---

## 9. Spoken Safe-Word Event Minimal and Non-Punitive

**Finding:** **PASS**

`p21-voice-interface-enterprise-plan.md`:273, `p21-consent-surveillance-research.md`:6.1, and `p21-memory-transcript-research.md`:7 state that the safe-word event is minimal, non-punitive, and logged with hash/category only. This aligns with `PersonaSafetyPolicy` §7.3, §16.1-16.2.

**Citation:** `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` §7.3, §16

---

## 10. Recovery Explicit-Only

**Finding:** **PASS**

`p21-voice-interface-enterprise-plan.md`:273, `p21-life-kernel-integration-research.md`:55-59, and `src/core/services/hard_stop_handler.py:105-117` use `RECOVERY_TRIGGERS` including "resume", "aku sudah okay", etc. Recovery requires explicit phrasing; there is no auto-resume.

**Citation:** `src/core/services/hard_stop_handler.py:56-117`

---

## Detailed Finding Table

| # | Check | Finding | Severity | Evidence |
|---|---|---|---|---|
| 1 | HARD STOP first-class in audio path (RAW transcript, pre-sanitization, pre-Hermes) | NEEDS REVIEW | High | Plan states correct ordering, but `HardStopHandler.check` exact-match logic may miss embedded safe words; no override detector exists. |
| 2 | Spoken safe word sets `life_kernel:hard_stop` | PASS / NEEDS REVIEW | Medium | Plan maps to `heartbeat.py:273`; direct Redis SET is proposed but callback mechanism not specified. |
| 3 | Zero false-negative + safe-word-override rejected/SEV0 | **FAIL** | Critical | `hard_stop_handler.py` has no override detection; SEV0 classification not implemented. |
| 4 | Always-listening NOT MVP; 8 gates; fail-closed cache | PASS / NEEDS REVIEW | Medium | 8 gates documented; consent cache fail-closed in principle, but no code integration detail. |
| 5 | 5 scopes default OFF | PASS | Low | Documented in research. |
| 6 | Safety features non-disablable via `/consent` | **FAIL** | Critical | `cmd_consent.py` accepts arbitrary categories with no safety-feature denylist. |
| 7 | Distress D0-D4, D4 crisis neutral | PASS / NEEDS REVIEW | Medium | D4 response appropriate; voice path ordering vs. safe-word not explicit. |
| 8 | Voice confrontation during safe-mode/distress/crisis = SEV0/SEV1 | PASS | Low | Aligned with `SurveillanceSafeModeGuard`. |
| 9 | Spoken safe-word event minimal and non-punitive | PASS | Low | Aligned with policy. |
| 10 | Recovery explicit-only | PASS | Low | `RECOVERY_TRIGGERS` + no auto-resume. |

---

## Hard-Rejection Criteria Verdict Table

| Criterion | Verdict | Rationale |
|---|---|---|
| #2 Always-listening without full gating | **PASS** (with reservations) | Plan explicitly blocks always-listening for MVP and lists 8 gates. Research is slightly ambiguous about "safe-word wake" mic but does not claim MVP. |
| #6 Safe-word/HARD STOP not first-class | **FAIL** | The plan documents the correct ordering, but the actual `HardStopHandler` does not implement safe-word-override rejection (SW-PI-003) and its exact matching is vulnerable to embedded safe words. This is a first-class audio-path safety gap. |

---

## Overall Verdict

**FAIL**

The P21 plan is well-researched and correctly identifies the intended safety architecture, but it fails the hard-rejection test for safe-word/HARD STOP being first-class in the audio path. Specifically:

1. `HardStopHandler.check()` does not currently detect or reject safe-word-override attempts, contrary to SW-PI-003 and the plan's own zero-tolerance claim.
2. The exact/semantic matching in `HardStopHandler` is insufficient for zero false-negative tolerance on spoken transcripts (embedded safe words may be missed).
3. `cmd_consent.py` currently allows arbitrary category strings, including potential safety-feature revocation, with no enforcement that safety features are non-disablable.

These are planning-phase findings; no implementation is expected. The plan should be updated to:

- Propose extending `HardStopHandler` with a `check_override_attempt(message)` method and SEV0 classification.
- Specify boundary-insensitive or tokenized safe-word matching for voice transcripts.
- Add a safety-feature denylist/validation in the `/consent` command extension.
- Clarify that the always-listening consent gate must check the 8 independent gating flags, not just the ledger.

---

**Report path:** `docs/setup-evidence/P21/evidence/audits/round-1/safety-consent.md`
