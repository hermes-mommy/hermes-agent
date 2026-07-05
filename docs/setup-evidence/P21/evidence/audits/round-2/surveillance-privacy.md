# P21 Voice Interface — Round 2 Surveillance / Privacy Audit

**Auditor role:** Independent surveillance/privacy auditor
**Date:** 2026-06-24
**Scope:** Amended P21 enterprise plan + source-of-truth files; planning phase only (NO runtime code implemented)
**Verdict:** PASS (with two planning inconsistencies that must be resolved before P21-004/P21-005 execute)

---

## 1. Executive Summary

The amended enterprise plan folds the three surveillance/privacy round-1 findings (A7, A8, A9) into concrete wave scaffolds. All hard-rejection criteria relevant to this dimension remain mitigated in policy. However, two new planning inconsistencies were introduced by the amendments: (1) an ambiguity between using the existing `surveillance.events.raw_payload` table versus creating a new `surveillance.voice_stream` table for retained raw audio, and (2) an ambiguity in provenance labels (`source='voice'` vs `source="voice_conversation"`; no explicit mapping for `source_trust`). These do not invalidate the design but must be reconciled before implementation waves P21-003/P21-004/P21-005 execute.

---

## 2. Round-1 Finding Closure Table

| Round-1 Finding | Description | Amendment in amended plan | Status | Evidence |
|---|---|---|---|---|
| **A7** | `voice_raw_audio` event type missing from `src/surveillance/classification.py:80-167` | **A7**: P21-004 scaffold must add `voice_raw_audio` classified `CRITICAL` / `retention_class="critical_media"` / `encryption_profile="double_high"` | **CLOSED** | `docs/setup-evidence/P21/plan/p21-voice-interface-enterprise-plan.md:468`; `p21-memory-transcript-research.md` §2.2, §9 |
| **A8** | Consent-revocation cascade documented but not implemented | **A8**: P21-005 scaffold must implement concrete cascade function (`src/voice/consent_cascade.py` or in `voice_gate.py`) + test; revoke `voice.*` → mark voice episodes `deletion_state='pending_delete'` / `do_not_recall=true` → purge `surveillance.events` raw audio for `event_type='voice_raw_audio'` → record `consent.revocation_log.cascade_effects` | **CLOSED** | `docs/setup-evidence/P21/plan/p21-voice-interface-enterprise-plan.md:469`; `p21-memory-transcript-research.md` §8 |
| **A9** | `store_conversation()` hardcodes `source="discord_conversation"`; `source_type` param missing | **A9**: P21-003 deliverable must add `source_type: str = "discord"` kwarg to `HermesMemoryBridge.store_conversation()` (`src/hermes/_memory_bridge.py:217-313`); dynamic `source`/`tags`; test voice episodes carry `source="voice_conversation"` + `["voice","chat",...]` | **CLOSED** | `docs/setup-evidence/P21/plan/p21-voice-interface-enterprise-plan.md:470`; `src/hermes/_memory_bridge.py:274` still hardcodes `source="discord_conversation"` |

---

## 3. Re-Verification of Surveillance/Privacy Controls

### 3.1 Voice as first-class surveillance stream — PASS

The amended plan and research explicitly ground voice in the same policy framework as camera, screenshots, and wearable health.

- `p21-consent-surveillance-research.md` §2.1: "Voice-derived data is analogous to camera/screenshots and wearable health ... voice must be added as a first-class surveillance stream with the same minimization, classification, retention, and consent controls."
- `p21-voice-interface-enterprise-plan.md` §Memory/Transcript Model: "Voice is treated as a first-class surveillance stream with the same consent, retention, and redaction rules as text."
- Source-of-truth: `docs/30-data/31-SurveillanceDataPolicy_v1.0.md` §3.1, §6.3, §9.2.

### 3.2 Transcript classification — PASS

- Default `Restricted`; escalates to `Critical` for safe-word, distress, intimate, or crisis content.
- `p21-memory-transcript-research.md` §2.1, §3.1.
- Schema support: `src/memory/models.py:57-76` (`ClassificationMetaMixin` defaults).

### 3.3 Raw audio discarded by default — PASS

- `p21-voice-interface-enterprise-plan.md` §Global Constraints: "No raw audio in artifacts/logs/MCP: Raw audio discarded after STT by default."
- `p21-memory-transcript-research.md` §2.2: "Privacy-by-default recommendation: discard raw audio immediately after STT."

### 3.4 Raw audio retention (if retained) — PASS with condition

- If retained, raw audio is encrypted (`envelope-AES-256-GCM`, double for Critical), stored ≤24h, and auto-purged.
- Amendment A7 correctly maps `voice_raw_audio` to `CRITICAL` / `retention_class="critical_media"` / `encryption_profile="double_high"`, matching `docs/30-data/31-SurveillanceDataPolicy_v1.0.md` §9.2 "Critical Media Short Raw | Max 24 hours."
- **Condition**: A7 is planned for P21-004; the classification.py edit has not happened yet. `src/surveillance/classification.py:80-167` still has no `voice_raw_audio` entry.

### 3.5 `do_not_recall` on safe-word/intimate/distress — PASS

- `p21-voice-interface-enterprise-plan.md` §Retention/Redaction Policy and `p21-memory-transcript-research.md` §5 require `do_not_recall=true` for safe-word/intimate/distress transcripts.
- Schema support: `src/memory/models.py:139-141`.

### 3.6 Audit hash chain — PASS

- Voice safety events go to `audit.audit_trail` with `event_hash` + `previous_hash`.
- Schema support: `src/memory/models.py:1068-1087`.
- `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` §16 requires minimal, non-punitive, encrypted, hash-chained logs.

### 3.7 Raw audio never in logs/artifacts/MCP — PASS

- Explicitly forbidden in `p21-voice-interface-enterprise-plan.md` §Global Constraints and `p21-security-secrets-research.md` §1.
- Consistent with `AGENTS.md` blocking rules.

### 3.8 Provenance labels — PARTIAL

- The amended plan requires `source_type='voice'` and source/tags provenance (A9), which addresses the round-1 gap.
- However, the research (`p21-memory-transcript-research.md` §6) also requires `source_trust='quarantined_5'` / `'untrusted_6'`, and the current `src/memory/models.py` `Episodes` table has no `source_trust` column. The amended plan does not reconcile how `source_trust` will be stored (column vs. tags/metadata). This is a new gap.

---

## 4. NEW Gaps Introduced by the Amendments

### 4.1 Raw-audio table ambiguity

**Issue:** The amended plan is internally inconsistent about where retained raw audio lives:

- `p21-voice-interface-enterprise-plan.md` §File Structure (line 64) / P21-004 scaffold: create new `surveillance.voice_stream` table for raw audio, 24h TTL.
- `p21-voice-interface-enterprise-plan.md` §Memory/Transcript Model: retained raw audio goes to existing `surveillance.events.raw_payload` with `event_type='voice_raw_audio'`.
- Amendment A8's consent-revocation cascade explicitly purges `surveillance.events` raw audio for `event_type='voice_raw_audio'`.

**Impact:** P21-004 cannot both create a dedicated `voice_stream` table and store diagnostic raw audio in `surveillance.events` without clarification. The cascade in P21-005 also needs a single target table.

**Recommendation before implementation:** Pick one model and update the other locations:
- Option A: Retained raw audio lives in `surveillance.events` (amend A7 / P21-004 to remove `voice_stream` table and use `event_type='voice_raw_audio'`).
- Option B: Retained raw audio lives in `surveillance.voice_stream` (update Memory/Transcript Model and A8 cascade to reference the new table, and ensure `classification.py` classification still applies).

### 4.2 Provenance label inconsistency

**Issue:** The amended plan uses conflicting values for the source provenance label:

- `p21-memory-transcript-research.md` §2.1: `source = 'voice'`
- Amendment A9 test criterion: `source="voice_conversation"`

**Recommendation before implementation:** Choose a single value (suggested: `voice_conversation` to mirror `discord_conversation`, with tag `voice`) and update both research and wave scaffold acceptance criteria.

### 4.3 `source_trust` not reconciled to schema

**Issue:** `p21-memory-transcript-research.md` §6 requires `source_trust='quarantined_5'` or `'untrusted_6'`. The amended plan only addresses `source_type`/source/tags. The `Episodes` schema has no `source_trust` column.

**Recommendation before implementation:** Either add `source_trust` to the P21-004 `memory.episodes` additive migration, or explicitly map it into `tags`/`metadata` and document the mapping in P21-003/P21-004.

---

## 5. Source-of-Truth File:Line References

| File | Lines | What it proves |
|------|-------|----------------|
| `src/surveillance/classification.py` | 80-167 | Existing event-type classification map; `voice_raw_audio` still absent at planning time |
| `src/memory/models.py` | 57-76 | `ClassificationMetaMixin` defaults and governance columns |
| `src/memory/models.py` | 92-149 | `Episodes` supports `do_not_recall`, `classification`, `source`, etc. |
| `src/memory/models.py` | 528-552 | `SurveillanceEvents.raw_payload` exists for raw audio retention |
| `src/memory/models.py` | 965-984 | `RevocationLog.cascade_effects` JSONB exists |
| `src/memory/models.py` | 1068-1087 | `AuditTrail` has `event_hash` + `previous_hash` |
| `src/hermes/_memory_bridge.py` | 217-313 | `store_conversation()` currently hardcodes `source="discord_conversation"`; A9 plans `source_type` kwarg |
| `docs/30-data/31-SurveillanceDataPolicy_v1.0.md` | 216-250 | Retention classes and raw media 24h rule |
| `docs/30-data/30-DataGovernance_Classification_v1.0.md` | 110-132 | Classification tiers and escalation rules |
| `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` | 484-516 | Safety log minimum, non-punitive, encrypted, hash-chained |
| `docs/setup-evidence/P21/plan/p21-voice-interface-enterprise-plan.md` | 456-479 | Audit Round-1 Amendments table (A7, A8, A9) |
| `docs/setup-evidence/P21/research/p21-consent-surveillance-research.md` | §2, §3, §6, §9 | Consent/surveillance framing |
| `docs/setup-evidence/P21/research/p21-memory-transcript-research.md` | all | Memory/transcript/retention research |

---

## 6. Hard-Rejection Criteria Relevant to This Dimension

| # | Criterion | Status | Notes |
|---|---|---|---|
| 1 | Sidecar-only | NOT MET as risk | Plan explicitly integrates voice into Hermes turn-core; not a sidecar. |
| 2 | Always-listening without gating | NOT MET as risk | `voice.always_listening` is MVP-blocked with 8-gate checklist. |
| 3 | Provider claims not official-doc-backed | NOT MET as risk | Provider research cites official docs/pricing. |
| 4 | Vague secrets | NOT MET as risk | Exact SOPS path, env vars, rotation, and encryption profile specified. |
| 5 | Transcripts in memory without redaction/retention | NOT MET as risk | MEM-001..008 gate, secret scanner, instruction-pattern quarantine, and classification are required before memory write. |
| 6 | Safe-word/HARD STOP not first-class | NOT MET as risk | HardStopHandler runs pre-sanitization; Redis `life_kernel:hard_stop` is single source of truth. |
| 7 | Inline-only sub-agent output | NOT MET as risk | All research/audit outputs are file-based. |
| 8 | Runtime code edits/deploy/restart in this phase | NOT MET as risk | Plan is explicitly planning-only; waves are held. |

---

## 7. Overall Verdict

**PASS.**

All three surveillance/privacy round-1 findings (A7, A8, A9) are explicitly closed in the amended plan through binding wave scaffolds. The design continues to satisfy every surveillance/privacy hard-rejection criterion in policy. Two new planning inconsistencies (raw-audio table target and provenance label reconciliation) need resolution before P21-003/P21-004/P21-005 execute, but they do not invalidate the overall surveillance/privacy design.
