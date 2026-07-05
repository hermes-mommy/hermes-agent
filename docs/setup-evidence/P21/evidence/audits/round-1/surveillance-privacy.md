# P21 Voice Interface — Round 1 Surveillance / Privacy Audit

**Auditor role:** Independent surveillance/privacy auditor
**Date:** 2026-06-24
**Scope:** P21 planning artifacts (research + enterprise plan), no runtime code implemented yet
**Verdict:** PASS with conditions

---

## 1. Executive Summary

Voice is correctly framed as a **first-class surveillance stream** in the planning materials. The design defaults to discarding raw audio, classifies transcripts as `Restricted` (escalating to `Critical` for safe-word/intimate/distress content), applies the existing `do_not_recall` mechanism, and records safety events to a hash-chained `audit.audit_trail`. All hard-rejection criteria relevant to this dimension are met in policy, with two implementation-level gaps that must be closed before P21-004/005 execute.

---

## 2. Dimension Verdicts

| # | Check | Verdict | Evidence / File:Line |
|---|------|--------|----------------------|
| 1 | Voice as first-class surveillance stream | PASS | `p21-consent-surveillance-research.md` §2.1; enterprise plan §Memory/Transcript Model |
| 2 | Transcript classification (`Restricted` default, `Critical` on safe-word/intimate) | PASS | `p21-memory-transcript-research.md` §2.1; `src/memory/models.py:57-76` (`ClassificationMetaMixin` defaults) |
| 3 | Raw audio discarded by default after STT | PASS | `p21-memory-transcript-research.md` §2.2, §3.1, §9 storage table |
| 4 | If retained, raw audio ≤24h encrypted in `surveillance.events.raw_payload`, auto-purge | PASS with condition | `p21-memory-transcript-research.md` §2.2, §9; `src/memory/models.py:528-552`; condition: new `voice_raw_audio` event type must be added to `src/surveillance/classification.py:80-167` before implementation |
| 5 | `do_not_recall` on safe-word/intimate/distress transcripts | PASS | `p21-memory-transcript-research.md` §5; `src/memory/models.py:139-141` |
| 6 | Minimal/non-punitive audit trail with `event_hash` + `previous_hash` | PASS | `p21-memory-transcript-research.md` §7; `src/memory/models.py:1068-1087` |
| 7 | Consent-revocation cascade (mark episodes, purge raw audio, `cascade_effects`) | PASS with condition | `p21-memory-transcript-research.md` §8; `src/memory/models.py:965-984` (`RevocationLog.cascade_effects`); condition: cascade must be implemented in `src/voice/` or `src/surveillance/` code, not only documented |
| 8 | Raw audio NEVER in logs/artifacts/MCP | PASS | `p21-security-secrets-research.md` §4.1; enterprise plan §Global Constraints |
| 9 | Provenance labels (`source_type=voice`, `source_trust=quarantined_5`) on every stored voice fact | PASS with condition | `p21-memory-transcript-research.md` §6; `src/hermes/_memory_bridge.py:217-313` currently hardcodes `source="discord_conversation"`; the plan correctly requires adding `source_type` param |

---

## 3. Detailed Findings

### 3.1 Voice treated as first-class surveillance stream — PASS

`p21-consent-surveillance-research.md` §2.1 explicitly grounds voice in the `Guinevere_SurveillanceDataPolicy_v1.0.md` and `Guinevere_ConsentRevocationPolicy_v1.0.md`, treating voice as analogous to camera/screenshots and wearable health. The enterprise plan §Memory/Transcript Model states: "Voice is treated as a first-class surveillance stream with the same consent, retention, and redaction rules as text."

This is consistent with the source-of-truth policies:
- `docs/30-data/31-SurveillanceDataPolicy_v1.0.md` §3.1 lists "future wearable sources" and §6.3 maps camera, screenshots, wearable health as `Critical` or `Restricted/Critical`.
- `docs/30-data/32-ConsentRevocationPolicy_v1.0.md` §3 requires consent to be revocable, scoped, auditable, purpose-bound, safety-limited, default-deny, fail-closed, and non-silently-reactivating — all applied to voice in the research.

### 3.2 Transcript classification — PASS

`p21-memory-transcript-research.md` §2.1 proposes:
- Default `classification = Restricted`
- Escalate to `Critical` for safe-word, distress, intimate, or crisis content
- `do_not_recall = true` for safe-word/intimate/distress

This aligns with:
- `docs/30-data/30-DataGovernance_ClassificationPolicy_v1.0.md` §4.1 tier 4: Critical includes "intimate, safe-word, crisis, credential, raw high-risk surveillance" and §4.2 "highest classification wins for mixed-category records."
- `src/memory/models.py:57-76` `ClassificationMetaMixin` defaults to `classification = 'Restricted'` and `retention_class = 'Long-Term Curated'`.

### 3.3 Raw audio discarded by default — PASS

The plan repeatedly states raw audio is discarded after STT by default (`p21-memory-transcript-research.md` §2.2, §3.1, §9). This satisfies privacy minimization (`docs/30-data/31-SurveillanceDataPolicy_v1.0.md` §4 "Raw data is toxic by default" and §9.2 retention classes).

### 3.4 Raw audio retention (if ever retained) — PASS with condition

`p21-memory-transcript-research.md` §9 storage table maps diagnostic raw audio to:
- Table: `surveillance.events`
- Class: `Critical`
- Retention class: `Short Raw`
- Retention: `24 hours`
- Encryption: `double-AES-256-GCM`

This matches:
- `src/memory/models.py:528-552` (`SurveillanceEvents` with `raw_payload: LargeBinary`, `ClassificationMetaMixin`)
- `docs/30-data/31-SurveillanceDataPolicy_v1.0.md` §9.2 `Critical Media Short Raw | Max 24 hours | Camera frames, screenshots, raw visual surveillance`

**Condition:** `src/surveillance/classification.py:80-167` currently only maps `app_usage`, `screen_state`, `active_window`, `idle_time`, `notification`, `browser`, `location`, `call_log`, `health`, `clipboard`, `screenshot`, `camera`. A new `voice_raw_audio` event type must be added and classified as `CRITICAL` / `double_high` before P21-004 executes.

### 3.5 `do_not_recall` enforcement — PASS

`p21-memory-transcript-research.md` §5 states safe-word/distress/intimate voice episodes must be marked `do_not_recall = true`. The existing schema supports this:
- `src/memory/models.py:139-141`: `do_not_recall: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))`
- `src/memory/read_pipeline.py`, `src/memory/consolidation.py`, `src/memory/dnr.py` already enforce DNR exclusion in recall paths.

### 3.6 Audit trail minimal/non-punitive with hash chain — PASS

`p21-memory-transcript-research.md` §7 specifies voice safety events write to `audit.audit_trail` with `event_hash` + `previous_hash`. The schema exists:
- `src/memory/models.py:1068-1087`: `AuditTrail` has `event_hash: Mapped[str]` and `previous_hash: Mapped[Optional[str]]`
- `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` §16 requires logs to be minimal, non-punitive, encrypted if Critical, and linked to a hash chain.

### 3.7 Consent-revocation cascade — PASS with condition

`p21-memory-transcript-research.md` §8 describes a complete cascade:
1. Stop voice collection
2. Mark voice-derived `memory.episodes` as `pending_delete` or `do_not_recall`
3. Purge raw audio from `surveillance.events.raw_payload` for `event_type = 'voice_raw_audio'`
4. Record cascade in `consent.revocation_log.cascade_effects`

The schema supports this:
- `src/memory/models.py:965-984`: `RevocationLog.cascade_effects: Mapped[Optional[JsonObject]]`
- `src/memory/models.py:74`: `deletion_state` supports `active`, `pending_delete`, etc.

**Condition:** The cascade is documented but not yet implemented. A concrete implementation plan (function, file, and test) must be added to the P21-005 wave before execution.

### 3.8 Raw audio never in logs/artifacts/MCP — PASS

`p21-security-secrets-research.md` §4.1 and the enterprise plan §Global Constraints explicitly forbid raw audio in logs, evidence artifacts, or MCP payloads. This is reinforced by `AGENTS.md` blocking rules.

### 3.9 Provenance labels — PASS with condition

`p21-memory-transcript-research.md` §6 requires every stored voice fact to carry:
- `source_type = 'voice'`
- `source_trust = 'quarantined_5'`
- confidence, storage_date, `do_not_recall`

The plan correctly identifies that `src/hermes/_memory_bridge.py:274` currently hardcodes `source="discord_conversation"` and proposes adding a `source_type` parameter. The enterprise plan §Hermes Core Wiring confirms this.

**Condition:** The `source_type` parameter change to `_memory_bridge.py:217-313` must be tracked as a P21-003 deliverable and tested.

---

## 4. Hard-Rejection Criteria Relevant to This Dimension

| Criterion | Status | Notes |
|---|--------|------|
| 5. Transcripts can enter memory without redaction/retention policy | NOT MET as risk | The plan correctly requires MEM-001..008 gate + secret scanner + instruction-pattern quarantine + classification before memory write. No gap in policy; implementation must enforce it. |

The hard-rejection criterion is **mitigated in planning** because the policy requires all necessary gates. The risk shifts to P21-004 implementation.

---

## 5. Gaps and Conditions

1. **`src/surveillance/classification.py` must add `voice_raw_audio`**
   - Before P21-004 implementation, add a `voice_raw_audio` event type classified as `CRITICAL` with `retention_class = "critical_media"` and `encryption_profile = "double_high"`.

2. **Consent-revocation cascade must be implemented, not only documented**
   - Add a concrete function (e.g., `src/voice/consent_cascade.py`) and test in P21-005 that marks episodes, purges raw audio, and writes `cascade_effects`.

3. **`source_type` provenance parameter in memory bridge**
   - Track in P21-003; test that voice episodes carry `source="voice_conversation"` and tags include `"voice"`.

---

## 6. Cited Source-of-Truth File:Line References

| File | Lines | What it proves |
|------|-------|----------------|
| `src/memory/models.py` | 57-76 | `ClassificationMetaMixin` defaults and governance columns |
| `src/memory/models.py` | 92-149 | `Episodes` table supports `do_not_recall`, `classification`, `source`, etc. |
| `src/memory/models.py` | 528-552 | `SurveillanceEvents.raw_payload` exists for raw audio retention |
| `src/memory/models.py` | 1068-1087 | `AuditTrail` has `event_hash` + `previous_hash` |
| `src/memory/models.py` | 965-984 | `RevocationLog.cascade_effects` JSONB exists |
| `src/hermes/_memory_bridge.py` | 217-313 | `store_conversation()` currently hardcodes `source="discord_conversation"` |
| `src/surveillance/classification.py` | 80-167 | Existing event-type classification map (no `voice_raw_audio` yet) |
| `docs/30-data/31-SurveillanceDataPolicy_v1.0.md` | 216-250 | Retention classes and raw media 24h rule |
| `docs/30-data/30-DataGovernance_ClassificationPolicy_v1.0.md` | 110-132 | Classification tiers and escalation rules |
| `docs/30-data/32-ConsentRevocationPolicy_v1.0.md` | 56-68, 185-241 | Consent principles and revocation procedure |
| `p21-memory-transcript-research.md` | all | Research document under audit |
| `p21-consent-surveillance-research.md` | §2, §3, §6, §9 | Consent/surveillance framing |
| `p21-voice-interface-enterprise-plan.md` | §Global Constraints, §Memory/Transcript Model, §Hard Rejection Criteria | Plan under audit |

---

## 7. Overall Verdict

**PASS with conditions.**

The surveillance/privacy design for P21 is sound and grounded in existing policies and schema. The two conditions (`voice_raw_audio` classification map entry and concrete revocation-cascade implementation) are implementation details that do not block the planning phase but must be resolved before P21-004/005 execute.
