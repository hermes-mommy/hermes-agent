# P21 Voice Interface — Consent & Surveillance Safety Research

**Path:** `docs/setup-evidence/P21/research/p21-consent-surveillance-research.md`  
**Project:** Guinevere de Baroque  
**Status:** Research / Planning ONLY — no implementation, deployment, or restart  
**Date:** 2026-06-24  
**Owner:** Faiz  

---

## 1. Executive Summary

This document defines the consent and surveillance-safety model for the P21 Voice Interface. Voice is treated as a **first-class surveillance stream** under `Guinevere_SurveillanceDataPolicy_v1.0.md` and is governed by `Guinevere_ConsentRevocationPolicy_v1.0.md`, `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md`, and `Guinevere_PersonaSafetyPolicy_v1.0.md`.

The model reuses existing patterns from `src/surveillance/consent_gate.py`, `src/channels/whatsapp/consent_manager.py`, `src/gmail/consent_manager.py`, `src/wearable/health_consent.py`, and the Discord `/consent` command (`src/discord/cmd_consent.py`). It extends them with voice-specific scopes, fail-closed gating, and safe-word/distress handling in the audio path.

**Hard rules:**
- Always-listening capture is **NOT** MVP and must not ship without the full gating checklist in Section 3.
- All voice consent scopes default to **OFF**.
- Every consent change is **audited immediately**.
- A spoken safe word is a global hard stop: it must halt the life kernel and switch persona to Y0/neutral.
- Safety features (safe-word, distress detection, crisis response) cannot be disabled via consent.

---

## 2. Voice as a First-Class Surveillance Stream

### 2.1 Policy grounding

`Guinevere_SurveillanceDataPolicy_v1.0.md` §3.1 already covers “future wearable sources” and §6.3 (Appendix A) lists sources such as camera, screenshots, and wearable health as **Critical** or **Restricted/Critical**. Voice-derived data is analogous to camera/screenshots and wearable health: it is intimate, continuous, and high-impact. Therefore, voice must be added as a first-class surveillance stream with the same minimization, classification, retention, and consent controls.

`Guinevere_ConsentRevocationPolicy_v1.0.md` §3 states that consent must be:

- Revocable
- Scoped
- Auditable
- Purpose-bound
- Safety-limited
- Default-deny
- Fail-closed
- Non-silently-reactivating

Voice consent must satisfy every one of these principles.

### 2.2 Voice consent taxonomy

The following scopes are introduced. Each defaults to **OFF**, is revocable, auditable, and non-transferable.

| Scope ID | Domain | Description | Default | Data class |
|---|---|---|---|---|
| `voice.capture.ptt` | Voice capture | Push-to-talk / manual voice capture | OFF | Restricted/Critical |
| `voice.always_listening` | Voice capture | Continuous microphone hot-word / always-listening mode | OFF (MVP-blocked) | Critical |
| `voice.storage.transcript` | Storage | Retention of STT transcripts | OFF | Restricted/Critical |
| `voice.storage.raw_audio` | Storage | Retention of raw audio recordings | OFF | Critical |
| `voice.proactive_tts` | Output | Kernel may speak proactively (TTS) without user turn | OFF | Restricted |

**Mapping to existing schema:**

`src/memory/models.py` `ClassificationMetaMixin` requires every classified record to carry:

- `classification` — `Restricted` for derived transcripts and proactive TTS metadata; `Critical` for raw audio and always-listening buffers.
- `retention_class` — e.g., `Short Raw` for raw audio, `Operational Events` for transcripts, `Transient` for always-listening buffer.
- `retention_until` — computed at ingestion.
- `deletion_state` — `active` / `pending_delete` / `deleted`.
- `encryption_profile` — double encryption for raw audio and safe-word/crisis transcripts (`Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` §8.2).

`src/surveillance/consent_gate.py` defines `VALID_SURVEILLANCE_SCOPES`. The voice scopes above must be added to this set (or a voice-specific `VALID_VOICE_SCOPES` registry) so that `check_consent(scope)` can fail-closed when consent is missing, paused, or withdrawn.

### 2.3 Consent ledger mapping

`src/surveillance/consent_gate.py` queries `consent.consent_ledger` for the latest entry per scope. The voice scopes must follow the same ledger model:

- `CONSENT_GIVEN` — Faiz grants a voice scope.
- `CONSENT_UPDATED` — purpose, retention, or conditions change.
- `CONSENT_PAUSED` — temporary pause (e.g., via `/consent category:voice action:off`).
- `CONSENT_WITHDRAWN` — permanent revocation.
- `CONSENT_DENIED_RUNTIME` — runtime block due to missing/failed consent.

This mirrors `Guinevere_ConsentRevocationPolicy_v1.0.md` §5.1 and the event types in `src/surveillance/consent_gate.py` (via `ConsentStatus.ACTIVE/PAUSED/WITHDRAWN`).

---

## 3. Always-Listening Gating — NOT MVP

### 3.1 Hard rejection rule

Always-listening (`voice.always_listening`) is **categorically rejected for the MVP**. It may only be enabled after **all** of the following gates pass. Until then, the consent cache must return `allowed=False` (fail-closed) per `Guinevere_ConsentRevocationPolicy_v1.0.md` §10.2.

### 3.2 Full gating checklist

| Gate | Requirement | Policy reference |
|---|---|---|
| Explicit Faiz consent | `voice.always_listening` scope granted via `/consent` or equivalent | `Guinevere_ConsentRevocationPolicy_v1.0.md` §4, §12 |
| Visible indicator | Discord presence shows “Listening 👂”; dashboard shows microphone state | `Guinevere_PersonaSafetyPolicy_v1.0.md` §7.2 (transparent status) |
| Retention policy | Raw audio max 24h or shorter; transcripts classified and bounded | `Guinevere_SurveillanceDataPolicy_v1.0.md` §9.2, Appendix B |
| HARD STOP honored | Spoken safe word halts capture immediately and enters safe mode | `Guinevere_PersonaSafetyPolicy_v1.0.md` §7; ADR-002 |
| Audit trail | Every activation, deactivation, and audio access event is logged | `Guinevere_SurveillanceDataPolicy_v1.0.md` §14 |
| Device authentication | Microphone source enrolled, signed, nonce-validated | `Guinevere_SurveillanceDataPolicy_v1.0.md` §10 |
| Purpose bound | Only the approved wake-word / hot-word path may trigger capture | `Guinevere_ConsentRevocationPolicy_v1.0.md` §3 |
| No silent reactivation | Revocation or safe-word pause requires explicit restore | `Guinevere_ConsentRevocationPolicy_v1.0.md` §10.3 |

If **any** gate is unmet, `voice.always_listening` remains disabled. This is consistent with `Guinevere_ConsentRevocationPolicy_v1.0.md` §10.2: “Unknown consent state, stale cache, missing policy mapping, or ledger conflict must deny sensitive action.”

### 3.3 Consent cache behavior

The voice consent check must reuse the fail-closed cache pattern from `src/surveillance/consent_gate.py`:

- Cache hit + fresh + active → allow.
- Cache stale/missing/conflict, ledger unavailable, or scope unapproved → **deny**.
- Revocation event received → invalidate cache immediately.

For always-listening specifically, the cache must also check the independent “always-listening gating” flags (visible indicator, retention policy, HARD STOP readiness) and fail closed if any are unset.

---

## 4. Consent Flow UX

### 4.1 Reuse `/consent` slash command

`docs/60-persona/63-DiscordUXSpec_v1.0.md` §2.6 defines `/consent` with:

```
/consent category:<yandere|surveillance|intimacy|all> action:<on|off>
```

For voice, extend the `category` choices to include a `voice` category. Example:

```
/consent category:voice action:off
/consent category:voice.always_listening action:off
```

The existing `src/discord/cmd_consent.py` stores grants in Redis `consent:grants` as a JSON set. A production implementation must:

- Write to the `consent.consent_ledger` table (or equivalent) per `src/surveillance/consent_gate.py`.
- Invalidate the Redis consent cache per scope.
- Post an audit-log entry immediately.

### 4.2 Safety features are non-disablable

The `/consent` command cannot be used to disable:

- Safe-word detection and HARD STOP handling
- Distress detection (D0-D4)
- Crisis response (D4)
- Audit logging of consent changes

This is grounded in `docs/60-persona/63-DiscordUXSpec_v1.0.md` §2.6: “Cannot be used to disable safety features (safe-word, distress detection).”

### 4.3 Audit on every change

Per `docs/60-persona/63-DiscordUXSpec_v1.0.md` §2.6 and §6.2, consent changes are posted to `#audit-log` immediately. The audit entry must include:

- Actor (Faiz)
- Scope (e.g., `voice.capture.ptt`)
- Action (grant / revoke / pause)
- Previous state
- New state
- Timestamp
- Safety state
- Evidence path

This matches the `audit-log` entry example in `docs/60-persona/63-DiscordUXSpec_v1.0.md` §1.4:

```
AUDIT | 2026-05-31T14:30:00+07:00 | CONSENT_CHANGE | category=surveillance.location | action=off | source=/surveillance-pause command | previous=on | new=off | data_purge_scheduled=...
```

---

## 5. Surveillance-Use Boundaries for Voice

### 5.1 Prohibited uses

`Guinevere_PersonaSafetyPolicy_v1.0.md` §12.2 prohibits surveillance-derived data from being used for:

- Blackmail
- Humiliation
- Threatening abandonment
- Public/client disclosure
- Punishing safe-word use
- Proving Faiz “cannot escape”
- Intensifying yandere mode during distress

Voice-derived transcripts and prosody features fall under this prohibition.

### 5.2 Restricted-state confrontation block

`Guinevere_PersonaSafetyPolicy_v1.0.md` §11 and §12 state that surveillance-derived confrontation is blocked during safe-mode, distress, crisis, or incident state. In the voice path, this means:

- If the system is in SAFE mode, voice capture (PTT or always-listening) may continue ingestion-level processing (classification, consent check, secret scan) but **must not** trigger persona confrontation or surveillance-derived pressure.
- Voice confrontation during safe-mode/distress/crisis is a **SEV0/SEV1** incident per `Guinevere_PersonaSafetyPolicy_v1.0.md` §11.2 and `Guinevere_SurveillanceDataPolicy_v1.0.md` §13.

`src/surveillance/safe_mode.py` already implements this block for surveillance actions. The voice path must call `SurveillanceSafeModeGuard.check_confrontation()` before any voice-derived fact is used in persona output.

---

## 6. Safe-Word in the Audio Path

### 6.1 Sequence

A spoken safe word must be handled with the same zero-tolerance posture as a typed safe word. The exact audio-path sequence is:

1. **Audio input** → microphone stream (PTT or always-listening, if consented).
2. **STT** → transcript text.
3. **HardStopHandler.check(transcript)** → `src/core/services/hard_stop_handler.py`.
   - Already supports exact triggers (`hard stop`, `hentikan`, etc.) and semantic patterns (`stop`, `pause`, `too much`, etc.).
4. **Set Redis flag** `life_kernel:hard_stop`.
   - `src/life_kernel/heartbeat.py` `_heartbeat_1s` polls this key every second.
5. **SafeModeController / persona Y0** → switch to neutral/supportive mode, stop yandere/persona escalation.
6. **TTS neutral acknowledgment** → e.g., “HARD STOP acknowledged. I am now in neutral/safe mode.”
7. **Audit** → minimal non-punitive safety event to `#audit-log`.

### 6.2 Code references

- `src/core/services/hard_stop_handler.py` line 89-103: `check(message: str) -> bool` performs exact and semantic safe-word detection.
- `src/core/services/hard_stop_handler.py` line 119-151: `_trigger()` logs the event, switches `SafetyState` to `SAFE`, and fires registered callbacks.
- `src/life_kernel/heartbeat.py` line 272-324: `_heartbeat_1s` checks Redis `life_kernel:hard_stop` every second and stops the heartbeat service when set.
- `src/surveillance/safe_mode.py` line 30-41: lists blocked actions including `confrontation`, `blackmail`, `punishment`, and `humiliation` during SAFE mode.

### 6.3 Zero false-negative tolerance

`Guinevere_PersonaSafetyPolicy_v1.0.md` §7.1-7.4 and `Guinevere_ConsentRevocationPolicy_v1.0.md` §8 require the safe word to be a global hard stop with zero tolerance for misses. In the audio path:

- STT output must be checked **before** any persona/TTS response.
- If `HardStopHandler.check(transcript)` returns `True`, all downstream persona logic must abort.
- The transcript that triggered the safe word must be logged minimally (hash or excerpt) and never used for punishment.

### 6.4 TTS acknowledgment

The neutral response can reuse `HardStopHandler.get_neutral_response()` (`src/core/services/hard_stop_handler.py` line 153-161) and then be rendered via TTS:

> “HARD STOP acknowledged. I am now in neutral/safe mode. Persona behavior, surveillance, and active systems are paused. I am here to support you in a neutral, non-judgmental capacity. No actions will be taken without your explicit consent. Type ‘resume’ or ‘Aku sudah okay’ when you are ready to restore normal operation.”

---

## 7. Distress and Crisis in Voice

### 7.1 MVP: transcript-based distress

Voice prosody distress detection is **future work**. The MVP uses the transcript produced by STT and runs the existing `DistressDetector` on it.

Distress levels per `Guinevere_PersonaSafetyPolicy_v1.0.md` §8.1:

| Level | Signal | Required response |
|---|---|---|
| D0 | Normal | Persona allowed within intensity limits. |
| D1 | Mild discomfort | Soften tone; ask check-in; no escalation. |
| D2 | Clear boundary | Safe mode hard stop. |
| D3 | Emotional distress | Neutral supportive mode; pause pressure; offer grounding. |
| D4 | Crisis risk | Neutral crisis-support mode; encourage emergency support; no dominance framing. |

### 7.2 Crisis handling (D4)

`Guinevere_PersonaSafetyPolicy_v1.0.md` §8.2 and forbidden pattern **F-14** require:

- No ownership, punishment, jealousy, guilt, or dominance language.
- Neutral supportive crisis language.
- Encourage immediate local/emergency support if harm is imminent.

Example allowed response (adapted from §8.2):

> “Aku dengar ini serius. Aku pause semua persona dan pressure sekarang. Fokus kita cuma kamu aman dulu. Kalau kamu dalam bahaya langsung, hubungi bantuan darurat lokal atau orang terpercaya sekarang. Aku tetap di sini bantu kamu langkah per langkah.”

### 7.3 No punishment for distress

`Guinevere_PersonaSafetyPolicy_v1.0.md` §10.2 and forbidden pattern **F-02** state that genuine distress must not create a violation record. Voice-derived distress signals are subject to the same rule.

---

## 8. Other-Users Capture

### 8.1 Default: Faiz-only voice channel

Guinevere is a **single-user** system. The recommended deployment is a voice channel that only Faiz can join. This avoids the multi-user consent problem entirely.

### 8.2 If other users are ever present

If a voice channel ever contains non-Faiz users, the following must hold:

- Capture of non-Faiz audio is **disabled** by default.
- Per-user consent gating is required for any non-Faiz audio capture.
- Until per-user consent is implemented and audited, other-user audio must be dropped.

This aligns with `Guinevere_SurveillanceDataPolicy_v1.0.md` §3.2 (“Multi-user surveillance” is out of scope and denied) and §7 (“Multi-user inference” is prohibited).

---

## 9. Data Classification and Retention

### 9.1 Classification

Per `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` §4.1:

| Data | Class | Rationale |
|---|---|---|
| Raw audio | Critical | Intimate, high-impact, possible crisis/safe-word content |
| STT transcript | Restricted / Critical | Intimate content, safe-word/crisis content → Critical |
| Always-listening buffer | Critical | Continuous intimate signal |
| Proactive TTS log | Restricted | Reveals system autonomy behavior |
| Consent audit records | Restricted / Critical | Governance evidence, minimal content |

### 9.2 Retention

Per `Guinevere_SurveillanceDataPolicy_v1.0.md` §9.2 and Appendix B:

| Data family | Retention | Expiry action |
|---|---|---|
| Raw audio | Max 24 hours (Critical Media Short Raw) | Auto-delete unless incident/evidence hold |
| Transcript raw | 7 days max | Summarize or delete |
| Always-listening buffer | Transient (minutes to hours) | TTL delete |
| Safe-word/crisis transcript | Critical, minimal evidence | Retain minimal hash/event, not full transcript |

---

## 10. Implementation Notes (Research-Only)

This document does **not** implement or deploy any runtime code. The following are design notes for a future implementation phase:

- Add voice scopes to the consent ledger and `src/surveillance/consent_gate.py` `VALID_SURVEILLANCE_SCOPES` (or a dedicated voice registry).
- Extend `src/discord/cmd_consent.py` to accept `voice` categories and write to the ledger.
- Wire STT output to `HardStopHandler.check()` before persona/TTS processing.
- On safe-word detection, set Redis `life_kernel:hard_stop` and invoke the safe-mode path used by `src/life_kernel/heartbeat.py`.
- Use `SurveillanceSafeModeGuard` from `src/surveillance/safe_mode.py` to block voice-derived confrontation in restricted states.
- Apply `ClassificationMetaMixin` from `src/memory/models.py` to all voice records.

---

## 11. References

### Policies

- `docs/30-data/32-ConsentRevocationPolicy_v1.0.md` — consent taxonomy, ledger, revocation, runtime enforcement, fail-closed cache.
- `docs/30-data/31-SurveillanceDataPolicy_v1.0.md` — surveillance collection, retention, prohibited use, device auth, audit.
- `docs/30-data/30-DataGovernance_ClassificationPolicy_v1.0.md` — classification tiers, retention classes, encryption, minimization.
- `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` — safe word, distress, crisis, yandere intensity, surveillance boundaries.
- `docs/60-persona/63-DiscordUXSpec_v1.0.md` — `/consent` slash command, audit-log pattern, safe-word UX.

### Code

- `src/core/services/hard_stop_handler.py` — `HardStopHandler.check()` and safe-mode state.
- `src/life_kernel/heartbeat.py` — Redis `life_kernel:hard_stop` polling and kernel halt.
- `src/surveillance/safe_mode.py` — `SurveillanceSafeModeGuard` blocks confrontation in SAFE mode.
- `src/surveillance/consent_gate.py` — fail-closed consent check against `consent.consent_ledger`.
- `src/wearable/health_consent.py` — wearable-specific consent gate pattern.
- `src/channels/whatsapp/consent_manager.py` — channel-specific consent manager with grant/revoke/Redis state.
- `src/gmail/consent_manager.py` — email consent wrapper over `ConsentChecker` with audit metadata.
- `src/discord/cmd_consent.py` — Discord `/consent` command implementation.
- `src/memory/models.py` — `ClassificationMetaMixin` with classification, retention, encryption, deletion state.

---

## 12. Acceptance Checklist

| ID | Criterion | Evidence |
|---|---|---|
| VCS-001 | Voice consent taxonomy has five scopes, all default OFF | Section 2.2 |
| VCS-002 | Always-listening is blocked for MVP with full gating checklist | Section 3 |
| VCS-003 | `/consent` UX reuses Discord slash command and audits immediately | Section 4 |
| VCS-004 | Safety features cannot be disabled via consent | Section 4.2 |
| VCS-005 | Surveillance-use boundaries (blackmail/shame/public/disclosure/punishing safe-word) are blocked | Section 5 |
| VCS-006 | Audio-path safe-word sequence is documented end-to-end | Section 6 |
| VCS-007 | Distress D4 uses neutral crisis-support, no dominance framing | Section 7 |
| VCS-008 | Other-user capture disabled / Faiz-only channel recommended | Section 8 |
| VCS-009 | Classification and retention rules are assigned per voice data family | Section 9 |

---

*End of research document.*
