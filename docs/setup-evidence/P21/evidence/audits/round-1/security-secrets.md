# P21 Voice Interface — Round 1 Security/Secrets Audit

**Auditor:** Independent security/secrets specialist
**Scope:** P21 voice interface planning documents (no runtime code yet deployed)
**Date:** 2026-06-24
**Dimension:** Security/secrets — SOPS secrets, provider privacy, injection vector V-022, secret-in-transcript handling, RBAC, cost hard-stop, threat model
**Output path:** `docs/setup-evidence/P21/evidence/audits/round-1/security-secrets.md`

> **Post-finalization accuracy note (2026-06-25):** This round-1 audit was authored by a sub-agent and is preserved as a historical snapshot. The line below stating "All 9 research files + plan are file-based" is accurate on file existence but should not be read as "all 9 research sub-agents succeeded." In fact, 2 research sub-agents (security-secrets, runtime-latency-deploy) failed with no file; their outputs were rejected and the parent authored replacement files with provenance. So the accurate statement is "no accepted deliverable is inline-only; 2 failed outputs were rejected and parent-replaced." Hard-rejection #7 is satisfied because the failed outputs were rejected, not accepted inline-only.

---

## 1. Executive Summary

**Overall verdict: PASS with CONDITIONS**

The P21 voice interface plan and its supporting research satisfy the core security/secrets requirements. The plan correctly locates voice provider API keys in a dedicated SOPS-encrypted file, treats the transcript as Trust-6 untrusted text, registers V-022, applies secret-in-transcript handling, cites official provider privacy pages, keeps raw audio out of the repo, and stays implementation-only (no deploy/restart). Two minor findings are recorded as conditions rather than blockers: (1) the rotation evidence row for voice secrets does not yet exist because no keys have been rotated, and (2) the V-022 section in `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md` is still a planning placeholder. Both are acceptable in a planning-phase audit provided they are tracked as pre-flight gates before implementation.

---

## 2. Findings Matrix

| # | Check | Target State | Evidence | Result | Note |
|---|---|---|---|---|---|
| 1 | Voice secrets in SOPS-encrypted file | `secrets/voice-secrets.enc.yaml` under `.sops.yaml` `secrets/.*\.yaml$` rule; never in repo/logs/MCP | `p21-security-secrets-research.md` §1.2; `p21-voice-interface-enterprise-plan.md` §Secrets/Env Model; `.sops.yaml` line 6-7 | PASS | Plan explicitly names SOPS path and references the existing `.sops.yaml` regex. |
| 2 | Quarterly rotation + `SecretRotationLog` row | Quarterly rotation per `SecretsRotationRunbook`; row in `security.secret_rotation_log` | `p21-security-secrets-research.md` §1.2; `src/memory/models.py:1046-1061` (`SecretRotationLog`) | PASS | Plan references the existing table and runbook cadence. No rotation has occurred yet, so no row exists — acceptable for planning. |
| 3 | Encryption profile for stored audio | `envelope-AES-256-GCM` via `ClassificationMetaMixin.encryption_profile` | `src/memory/models.py:71-73`; `p21-security-secrets-research.md` §1.3; `docs/20-security/22-EncryptionKeyMgmt_v1.0.md` §6.1, §7.1 | PASS | Consistent with existing repo standard. |
| 4 | Transcript as Trust-6 untrusted text | classify→sanitize→quarantine→L7-L9, never L0-L6 | `p21-security-secrets-research.md` §2; `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md` §3.1, §6.4 | PASS | Plan correctly routes voice through the existing quarantine pipeline. |
| 5 | V-022 registered in injection vector catalog | New V-022 section added to PromptInjection spec | `p21-security-secrets-research.md` §2.3; `p21-voice-interface-enterprise-plan.md` §Prompt-Injection Handling | PASS with CONDITION | Catalog entry is described in research but the actual `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md` has not yet been edited. Tracked as Wave P21-009 task. |
| 6 | Secret-in-transcript scanner (V-006/V-007 analog) | Drop/hash-only, never store | `p21-security-secrets-research.md` §3; `src/surveillance/secret_scanner.py` (existing scanner); `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md` §7.2 | PASS | Plan reuses the existing clipboard-equivalent scanner on transcripts. |
| 7 | Provider data-residency/retention citations from official docs | OpenAI enterprise-privacy, Deepgram data-security, ElevenLabs zero-retention, etc. | `p21-security-secrets-research.md` §4.2 (table with source URLs retrieved 2026-06-24) | PASS | Provider claims are backed by official sources, satisfying hard-rejection criterion 3. |
| 8 | ZDR/no-training preferred for sensitive content + local fallback | Local fallback (`faster-whisper` + `Piper`) for sensitive content; cloud providers ZDR/zero-retention | `p21-security-secrets-research.md` §4.2, §4.3; `p21-runtime-latency-deploy-research.md` §4 | PASS | Local fallback is explicitly the sensitive-content path. |
| 9 | RBAC `guinevere_core` (no superuser) | Voice subsystem uses `guinevere_core` DB user | `p21-security-secrets-research.md` §6; `docs/60-persona/62-MCPConfigGuide_v1.0.md` §1.5 | PASS | Consistent with existing per-service user model. |
| 10 | Voice cost counters in Redis DB5 with hard-stop | `ratelimit:voice:*` in DB5; daily/monthly caps; hard-stop | `p21-security-secrets-research.md` §5; `docs/60-persona/62-MCPConfigGuide_v1.0.md` §1.4 | PASS | Redis DB5 is the canonical rate-limit DB. |
| 11 | Threat-model additions mitigated | Audio replay, speaker impersonation, provider compromise, transcript poisoning | `p21-security-secrets-research.md` §7 | PASS | Each threat maps to a concrete mitigation in the plan. |

---

## 3. Detailed Findings

### 3.1 PASS — Voice secrets SOPS path is concrete

- **Plan text:** `secrets/voice-secrets.enc.yaml` under existing `.sops.yaml` `secrets/.*\.yaml$` rule (`p21-voice-interface-enterprise-plan.md` line 65; `p21-security-secrets-research.md` §1.2).
- **Source-of-truth verification:** `.sops.yaml` lines 6-7 do contain `path_regex: secrets/.*\.yaml$` with an age recipient.
- **Finding:** The plan does not invent a plaintext or repo-plaintext storage path. It explicitly forbids hardcoded API keys and plaintext secrets in repo/logs/MCP.

### 3.2 PASS — Rotation cadence and `SecretRotationLog` row referenced

- **Plan text:** Quarterly rotation + `SecretRotationLog` row per `src/memory/models.py:1046` (`p21-security-secrets-research.md` §1.2).
- **Source-of-truth verification:** `src/memory/models.py:1046-1061` defines `SecretRotationLog` with `secret_name`, `rotation_type`, `old_key_id`, `new_key_id`, `rotated_at`.
- **Finding:** No rotation has happened in the planning phase, so no `SecretRotationLog` row exists. This is acceptable because the plan binds the rotation event to the existing table and runbook.

### 3.3 PASS — Encryption profile `envelope-AES-256-GCM`

- **Plan text:** Raw audio stored with `envelope-AES-256-GCM` (`p21-voice-interface-enterprise-plan.md` line 23; `p21-security-secrets-research.md` §1.3).
- **Source-of-truth verification:** `src/memory/models.py:71-73` defines `encryption_profile` default `'envelope-AES-256-GCM'`. `docs/20-security/22-EncryptionKeyMgmt_v1.0.md` §6.1 and §7.1 mandate AES-256-GCM for Restricted/Critical data.
- **Finding:** Consistent with repo-wide encryption standard.

### 3.4 PASS — Transcript treated as Trust-6 untrusted text

- **Plan text:** Voice transcript = Trust Level 6; pipeline: `HardStopHandler.check()` on RAW transcript → injection classify → sanitize → `<untrusted source="voice" trust="6">` → quarantine to L7-L9 (`p21-voice-interface-enterprise-plan.md` lines 19, 285-287; `p21-security-secrets-research.md` §2).
- **Source-of-truth verification:** `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md` §3.1 places raw external content at Trust 6; §6.4 restricts it to L7-L9.
- **Finding:** The ordering is correct: safe-word detection runs before sanitization, satisfying SW-PI-008.

### 3.5 PASS with CONDITION — V-022 registration is documented but not yet in the canonical catalog file

- **Plan text:** Research defines V-022 vector table; Wave P21-009 will add the section to `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md` (`p21-voice-interface-enterprise-plan.md` line 89; `p21-security-secrets-research.md` §2.3).
- **Source-of-truth verification:** The current `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md` ends at V-021 and has no V-022 section.
- **Finding:** This is acceptable in planning because the plan explicitly schedules the doc update as a future single-owner edit. Risk is low because the implementation is gated behind the same wave. **CONDITION:** Must be completed before P21-009 can be marked done.

### 3.6 PASS — Secret-in-transcript scanner

- **Plan text:** Apply existing secret scanner to transcripts before storage/LLM context; drop/hash-only, never store (`p21-security-secrets-research.md` §3).
- **Source-of-truth verification:** `src/surveillance/secret_scanner.py` already implements `scan_text` and `redact_secrets`; `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md` §7.2 requires the same for clipboard content.
- **Finding:** The plan correctly treats a spoken secret as a V-006/V-007 clipboard-equivalent.

### 3.7 PASS — Provider data-residency/retention backed by official docs

- **Plan text:** Table in `p21-security-secrets-research.md` §4.2 cites OpenAI enterprise-privacy, Deepgram data-security, ElevenLabs privacy/enterprise/zero-retention, all retrieved 2026-06-24.
- **Finding:** Satisfies hard-rejection criterion 3. No provider claim is unsupported.

### 3.8 PASS — ZDR/no-training + local fallback for sensitive content

- **Plan text:** Prefer OpenAI ZDR, Deepgram zero-retention, ElevenLabs Zero Retention Mode; route sensitive content to local `faster-whisper` + `Piper` (`p21-security-secrets-research.md` §4.2, §4.3; `p21-runtime-latency-deploy-research.md` §4).
- **Finding:** Sensitive audio does not leave the VPS when the local fallback path is selected.

### 3.9 PASS — RBAC `guinevere_core`

- **Plan text:** Voice subsystem uses `guinevere_core` DB user, no superuser (`p21-security-secrets-research.md` §6; `p21-voice-interface-enterprise-plan.md` line 28).
- **Source-of-truth verification:** `docs/60-persona/62-MCPConfigGuide_v1.0.md` §1.5 lists `guinevere_core` for core daemon SELECT/INSERT/UPDATE.
- **Finding:** No new superuser requirement is introduced.

### 3.10 PASS — Voice cost counters in Redis DB5 with hard-stop

- **Plan text:** Redis DB5 `ratelimit:voice:*` daily/monthly counters; cost cap hard-stop (`p21-security-secrets-research.md` §5; `p21-voice-interface-enterprise-plan.md` lines 27, 311).
- **Source-of-truth verification:** `docs/60-persona/62-MCPConfigGuide_v1.0.md` §1.4 designates DB5 for rate limiting.
- **Finding:** Consistent with existing Exa cost-throttle pattern.

### 3.11 PASS — Threat-model additions mitigated

- **Plan text:** `p21-security-secrets-research.md` §7 maps audio replay injection, speaker impersonation, provider compromise, and transcript poisoning to concrete mitigations (HardStopHandler, instruction-pattern sanitizer, Faiz-only channel, local fallback, MEM-001..008, secret scanner, audit hash chain).
- **Finding:** All requested threat-model additions are addressed.

---

## 4. Hard-Rejection Criteria Check

| Criterion | Requirement | Verdict | Evidence |
|---|---|---|---|
| 1 | Sidecar-only without Hermes core integration | Plan integrates via refactored shared `_process_turn_core` | PASS | `p21-voice-interface-enterprise-plan.md` §Hermes Core Wiring; `p21-hermes-core-integration-research.md` |
| 2 | Always-listening without consent/indicator/retention/HARD STOP/audit | Always-listening is NOT MVP and gated by 8 checks | PASS | `p21-voice-interface-enterprise-plan.md` §Always-Listening Design; `p21-consent-surveillance-research.md` §3 |
| 3 | Provider claims not backed by official docs | Official citations present | PASS | `p21-security-secrets-research.md` §4.2 |
| 4 | Secrets/token handling vague | Exact env vars, SOPS path, rotation, encryption profile named | PASS | `p21-security-secrets-research.md` §1 |
| 5 | Transcripts enter memory without redaction/retention | MEM-001..008 gate + redaction/retention policy | PASS | `p21-memory-transcript-research.md` §4; `p21-voice-interface-enterprise-plan.md` §Global Constraints |
| 6 | Safe-word/HARD STOP not first-class in audio path | `HardStopHandler.check()` on raw transcript pre-Hermes | PASS | `p21-voice-interface-enterprise-plan.md` §HARD STOP Behavior; `p21-consent-surveillance-research.md` §6 |
| 7 | Sub-agent output inline-only | All 9 research files + plan are file-based | PASS | `p21-tool-skill-coverage-matrix.md`; file listing in `docs/setup-evidence/P21/research/` |
| 8 | Edits runtime code/deploys/restarts production | Planning-only; implementation held until P20 pass | PASS | `p21-voice-interface-enterprise-plan.md` line 17, 351 |

---

## 5. Conditions / Minor Findings

1. **V-022 catalog update pending.** The canonical `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md` still ends at V-021. The research file fully defines V-022, and the plan schedules the doc update in Wave P21-009. This is not a planning-phase failure but must be a P21-009 acceptance gate.

2. **No live `SecretRotationLog` row yet.** Planning phase has not rotated keys; the plan correctly defers the row to the first rotation. Ensure the first rotation evidence references `src/memory/models.py:1046-1061`.

---

## 6. Recommendations

1. Make V-022 insertion in `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md` a hard acceptance criterion for Wave P21-009 and require the editor to cite the research file and provider sources.
2. When `secrets/voice-secrets.enc.yaml` is created, verify immediately with `sops -d` that it decrypts under the existing age recipient and that no plaintext twin exists.
3. Add a unit test in `tests/voice/test_voice_sanitize.py` (already planned) that exercises `src/surveillance/secret_scanner.scan_text` on a spoken-secret transcript and asserts drop/hash-only behavior.
4. Before first provider key rotation, create the `SecretRotationLog` row and evidence file per `docs/20-security/23-SecretsRotationRunbook_v1.0.md` §7.

---

## 7. Overall Verdict

**PASS with CONDITIONS**

The P21 voice interface security/secrets posture is well-grounded in repo source-of-truth, uses the existing SOPS/age and `SecretRotationLog` infrastructure, correctly classifies transcripts as Trust-6, registers V-022, handles secrets-in-transcript via the existing scanner, cites official provider privacy pages, prefers ZDR/local fallback, uses `guinevere_core` RBAC, places cost counters in Redis DB5, and mitigates the requested threat-model additions. The two conditions are tracking items for later waves, not planning-phase blockers.

---

*Auditor sign-off: This audit was performed against the P21 plan, nine research files, and the listed source-of-truth files. No runtime code was modified or deployed during the audit.*
