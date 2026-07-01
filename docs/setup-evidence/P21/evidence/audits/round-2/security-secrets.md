# P21 Voice Interface — Round 2 Security/Secrets Audit

**Auditor:** Independent security/secrets specialist (Round 2)
**Scope:** P21 voice interface planning documents (no runtime code yet deployed)
**Date:** 2026-06-24
**Dimension:** Security/secrets — SOPS secrets, provider privacy, injection vector V-022, secret-in-transcript handling, RBAC, cost hard-stop, threat model
**Output path:** `docs/setup-evidence/P21/evidence/audits/round-2/security-secrets.md`

---

## 1. Executive Summary

**Overall verdict: PASS**

The amended P21 voice interface plan now closes both Round-1 security/secrets conditions (A16 V-022 catalog entry, A17 first-rotation `SecretRotationLog` row) by binding them to concrete wave scaffolds. All other security/secrets controls (SOPS path, Trust-6 transcript handling, secret-in-transcript scanner, provider ZDR citations, RBAC, Redis DB5 cost hard-stop, threat-model mitigations) remain sound and traceable to repo source-of-truth. No new gaps that fall within the security/secrets dimension were introduced by the amendments. The plan remains planning-only, with no runtime edits/deploys/restarts in this phase.

---

## 2. Round-1 Finding Closure Table

| Round-1 Finding | Condition / Amendment | Round-2 Status | Evidence |
|---|---|---|---|
| A16 — V-022 section in `24-PromptInjection_ModelSafety_v1.0.md` not yet added | P21-009 hard acceptance criterion: V-022 section MUST be added (single-owner edit) citing the research file + provider sources; P21-009 not done until committed. | **CLOSED** by amendment | `p21-voice-interface-enterprise-plan.md` §Audit Round-1 Amendments line 477; `p21-security-secrets-research.md` §2.3 defines full V-022 vector table to be inserted |
| A17 — No live `SecretRotationLog` row yet | First voice-key rotation (P21-001 or P21-008) MUST create a `SecretRotationLog` row (`src/memory/models.py:1046-1061`) + evidence per `SecretsRotationRunbook_v1.0.md` §7. | **CLOSED** by amendment | `p21-voice-interface-enterprise-plan.md` §Audit Round-1 Amendments line 478; plan §Secrets/Env Model references `SecretRotationLog` |
| SOPS voice secrets path | `secrets/voice-secrets.enc.yaml` under `.sops.yaml` `secrets/.*\.yaml$` rule | CLOSED | `.sops.yaml:6-7`; plan §Secrets/Env Model; research §1.2 |
| Trust-6 transcript pipeline | classify → sanitize → quarantine L7-L9 | CLOSED | `24-PromptInjection_ModelSafety_v1.0.md` §3.1, §6.4; plan §Global Constraints line 19 |
| Secret-in-transcript scanner | Reuse `src/surveillance/secret_scanner.py` drop/hash-only | CLOSED | `src/surveillance/secret_scanner.py:225-318`; research §3; plan §Retention/Redaction line 256 |
| Provider ZDR/no-training citations | OpenAI, Deepgram, ElevenLabs official docs cited | CLOSED | research §4.2 table with URLs retrieved 2026-06-24 |
| RBAC `guinevere_core` | Voice uses `guinevere_core` DB user | CLOSED | `62-MCPConfigGuide_v1.0.md` §1.5; plan §Global Constraints line 28 |
| Redis DB5 cost hard-stop | `ratelimit:voice:*` in DB5 with daily/monthly caps | CLOSED | `62-MCPConfigGuide_v1.0.md` §1.4; research §5; plan §Cost/Latency Model lines 27, 311 |
| Threat-model mitigations | Audio replay, impersonation, provider compromise, transcript poisoning mapped | CLOSED | research §7; plan §Prompt-Injection Handling, §HARD STOP Behavior |

---

## 3. Detailed Findings

### 3.1 CLOSED — A16 V-022 now bound to P21-009 hard acceptance

- **Original finding (Round 1):** V-022 was fully defined in `p21-security-secrets-research.md` §2.3 but not yet inserted into the canonical `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md`, which ends at V-021 (`24-PromptInjection_ModelSafety_v1.0.md:504`).
- **Amendment:** `p21-voice-interface-enterprise-plan.md` §Audit Round-1 Amendments line 477 makes V-022 insertion a **hard acceptance criterion** for Wave P21-009, with the requirement to cite the research file and provider sources, and states "P21-009 not done until committed."
- **Verification:** The amended plan no longer treats V-022 as an open planning condition; it is now an explicit pre-soak gate. This satisfies the Round-1 condition without requiring the canonical doc edit during the planning phase.
- **No new gap:** The amendment correctly preserves the single-owner edit model and avoids premature edits to the locked PromptInjection spec before P20 pass.

### 3.2 CLOSED — A17 first `SecretRotationLog` row bound to first rotation

- **Original finding (Round 1):** No `SecretRotationLog` row existed because no voice keys had been rotated in the planning phase.
- **Amendment:** `p21-voice-interface-enterprise-plan.md` §Audit Round-1 Amendments line 478 requires the first voice-key rotation (Wave P21-001 or P21-008) to create a `SecretRotationLog` row per `src/memory/models.py:1046-1061` and evidence per `docs/20-security/23-SecretsRotationRunbook_v1.0.md` §7.
- **Verification:** `src/memory/models.py:1046-1061` defines `SecretRotationLog` with `secret_name`, `rotation_type`, `old_key_id`, `new_key_id`, and `rotated_at`. The runbook §7 standardizes rotation evidence artifacts. The plan defers the row to the first rotation, which is the correct planning-phase behavior.

### 3.3 PASS — SOPS secrets path remains concrete

- `secrets/voice-secrets.enc.yaml` is explicitly named in the plan (line 65, §Secrets/Env Model) and research (§1.2).
- `.sops.yaml:6-7` already covers `secrets/.*\.yaml$` with the age recipient.
- The plan forbids hardcoded API keys, plaintext secrets in repo/logs/MCP, and requires never reading SOPS files directly from code (research §1.2).

### 3.4 PASS — Trust-6 transcript pipeline unchanged and correct

- Plan §Global Constraints line 19 and §Prompt-Injection Handling line 287 require: `HardStopHandler.check()` on RAW transcript → injection classify → sanitize → `<untrusted source="voice" trust="6">` → quarantine to L7-L9.
- `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md` §3.1 places raw external content at Trust 6; §6.4 restricts it to L7-L9.
- Safe-word detection ordering satisfies SW-PI-008 (safe-word classifier runs before sanitization).

### 3.5 PASS — Secret-in-transcript scanner reused

- Plan §Retention/Redaction line 256 and research §3 require applying `src/surveillance/secret_scanner.py` to transcripts before storage/LLM context.
- `src/surveillance/secret_scanner.py:225-318` implements `scan_text` and `redact_secrets` with drop/redact behavior and hash-only logging.
- This mirrors the V-006/V-007 clipboard handling in `24-PromptInjection_ModelSafety_v1.0.md` §7.2 and §10.2.

### 3.6 PASS — Provider ZDR/no-training claims backed by official docs

- Research §4.2 provides a table citing `openai.com/enterprise-privacy`, `deepgram.com/data-security`, `elevenlabs.io/privacy-policy`, `elevenlabs.io/enterprise`, `elevenlabs.io/docs/eleven-api/resources/zero-retention-mode`, `developers.openai.com/api/docs/guides/realtime`, and `openai.com/api/pricing/`, all retrieved 2026-06-24.
- Hard-rejection criterion 3 (provider claims not official-doc-backed) remains satisfied.

### 3.7 PASS — Local fallback for sensitive content retained

- Research §4.2 and plan §Local Fallback Model line 321 route sensitive audio to local `faster-whisper` + `Piper`, ensuring audio does not leave the VPS.
- Cloud providers selected (OpenAI ZDR, Deepgram zero-retention, ElevenLabs Zero Retention Mode) are the least-retentive options.

### 3.8 PASS — RBAC `guinevere_core` and no superuser

- Plan §Global Constraints line 28 and research §6 state voice subsystem uses `guinevere_core` DB user.
- `docs/60-persona/62-MCPConfigGuide_v1.0.md` §1.5 lists `guinevere_core` for core daemon SELECT/INSERT/UPDATE.
- No new superuser or privileged DB user is introduced.

### 3.9 PASS — Redis DB5 cost hard-stop retained

- Research §5 and plan §Cost/Latency Model lines 27, 311 place voice cost counters in Redis DB5 (`ratelimit:voice:*`) with daily/monthly caps.
- `docs/60-persona/62-MCPConfigGuide_v1.0.md` §1.4 designates DB5 for rate limiting.
- The existing `CostTracker.record_cost` pattern is reused with `stt:*`, `tts:*`, and `realtime:*` tags.

### 3.10 PASS — Threat-model mitigations remain complete

- Research §7 maps pre-recorded audio injection, spoken safe-word override, speaker impersonation, transcript poisoning, spoken secret capture, provider compromise, raw audio exfiltration, always-listening cost runaway, and audio replay to concrete mitigations.
- Plan §HARD STOP Behavior, §Safe-Word Detection, §Prompt-Injection Handling, §Local Fallback Model, and §Cost/Latency Model operationalize these mitigations.

---

## 4. New-Gap Scan

| Check | Result | Evidence |
|---|---|---|
| A16 amendment introduces premature edit to `24-PromptInjection_ModelSafety_v1.0.md` | NO — P21-009 is explicitly held until P20 pass and implementation; no planning-phase edit required | plan line 477 |
| A17 amendment weakens rotation evidence requirement | NO — it binds the first rotation to `SecretRotationLog` + runbook evidence | plan line 478 |
| New plaintext secrets surface introduced by amendments | NO — no new secret paths or plaintext handling in amendments |
| New provider claim without official citation | NO — no new providers or claims in amendments |
| New bypass of secret-in-transcript scanner | NO — amendments strengthen enforcement (P21-005) rather than weaken |
| New RBAC/superuser risk | NO — amendments do not touch RBAC |
| New cost/rate-limit gap | NO — DB5 caps remain unchanged |

No new security/secrets gaps were introduced by the Round-1 amendments.

---

## 5. Hard-Rejection Criteria Check

| Criterion | Requirement | Verdict | Evidence |
|---|---|---|---|
| 1 | Sidecar-only without Hermes core integration | PASS | plan §Hermes Core Wiring; research `p21-hermes-core-integration-research.md` |
| 2 | Always-listening without gating | PASS | plan §Always-Listening Design; 8-gate checklist |
| 3 | Provider claims not backed by official docs | PASS | research §4.2 official citations |
| 4 | Secrets/token handling vague | PASS | exact env vars, SOPS path, rotation, encryption profile named |
| 5 | Transcripts enter memory without redaction/retention | PASS | MEM-001..008 gate + redaction/retention policy |
| 6 | Safe-word/HARD STOP not first-class in audio path | PASS | `HardStopHandler.check()` pre-Hermes pre-sanitize |
| 7 | Sub-agent output inline-only | PASS | all research/audit files file-based |
| 8 | Edits runtime code/deploys/restarts production | PASS | planning-only; waves held until P20 pass |

---

## 6. Conditions Remaining

None. Both Round-1 security/secrets conditions (A16, A17) are now closed by binding amendments. All other security/secrets checks remain PASS.

---

## 7. Recommendations

1. During P21-009 execution, verify the V-022 section in `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md` includes the exact vector table from `p21-security-secrets-research.md` §2.3 and cites the official provider sources.
2. During the first voice-key rotation (P21-001 or P21-008), create the `SecretRotationLog` row and the runbook §7 evidence artifact before revoking the old key.
3. When `secrets/voice-secrets.enc.yaml` is created, run `sops -d` to confirm it decrypts under the existing age recipient and scan the repo for any plaintext twin.
4. Add a unit test in `tests/voice/test_voice_sanitize.py` that feeds a spoken-secret transcript to `src/surveillance/secret_scanner.scan_text` and asserts drop/hash-only behavior.

---

## 8. Overall Verdict

**PASS**

The amended P21 voice interface security/secrets dimension satisfies all Round-1 conditions. A16 is closed by making V-022 insertion a hard P21-009 acceptance criterion; A17 is closed by binding the first voice-key rotation to a `SecretRotationLog` row and runbook evidence. No new security/secrets gaps were introduced. The plan remains planning-only with no runtime edits, deployments, or restarts.

---

*Auditor sign-off: This Round-2 audit was performed against the amended P21 plan, Round-1 security/secrets audit, research files, and listed source-of-truth files. No runtime code was modified or deployed during the audit.*
