# Lane C — P4 Persona/Consent Fix: Ground Truth Report

**Date:** 2026-06-27
**Phase:** 0 — Ground Truth
**Author:** Guinevere (orchestrator)
**Source:** Direct inspection of source code, audit reports, P4 KNOWN-ISSUES.md, persona source

---

## 1. Executive Summary

P4 Persona Engine was implemented and verified (23/23 steps PASS, 1449+ tests). However, the P4 audit + KNOWN-ISSUES.md reveals significant gaps between code existence and runtime activation. Several behavioral engines are verified as "complete" at the unit test level but are NOT wired into the live runtime path. The consent revocation story is particularly weak — consent is stored in Redis and checked at some gates, but revocation does NOT actively stop running persona/surveillance processes.

---

## 2. CRITICAL: Consent Revocation Does Not Stop Persona/Surveillance

### 2.1 Source Confirmation

**Consent storage:** `src/discord/cmd_consent.py` — stores consent grants in Redis key `consent:grants` as a JSON set.

**Consent checks found in:**
- `src/knowledge_graph/consent/manager.py` — KG consent manager
- `src/wearable/health_consent.py` — wearable health consent
- `src/gmail/consent_manager.py` — Gmail consent
- `src/channels/whatsapp/consent_manager.py` — WhatsApp consent
- `src/hermes_plugins/commands_system/consent.py` — Hermes consent command

**Missing: PersonaPlugin consent check.**
- `src/hermes/plugins/persona_plugin.py` — grep for `consent` returns only `_DEFAULT_SAFE_WORD` (line 145). There is NO consent revocation check before persona injection.
- No persona engine checks consent state before injecting mood/persona/ritual state.

### 2.2 Impact

- When Faiz revokes consent via `/consent action:revoke`, the consent flag is updated in Redis.
- **BUT:** The persona engine (PersonaPlugin, mood injection, ritual scheduler) does NOT check this flag.
- **BUT:** Running surveillance doesn't stop — it checks consent at ingestion time, not continuously.
- **BUT:** Personalization/persona injection continues even after revocation.

### 2.3 Fix Required

1. PersonaPlugin MUST check consent state before injecting persona context.
2. Active surveillance/personalization paths MUST poll or be notified of consent revocation.
3. Consent revocation MUST trigger a cascade: stop persona injection → stop surveillance → stop personalization.
4. This should be a runtime-active check, not just a one-time gate.

---

## 3. PersonaPlugin: Consent Check Missing

### 3.1 Source Confirmation

**File:** `src/hermes/plugins/persona_plugin.py`

The plugin loads persona state and injects it into Hermes prompts. However:
- No consent revocation check before injection.
- The `_DEFAULT_SAFE_WORD` is defined but only used for HARD STOP, not consent.
- The plugin assumes it should always inject persona state.

### 3.2 Fix Required

- Add `_check_consent()` method to PersonaPlugin.
- Call it before every prompt injection.
- If consent is revoked, return neutral/empty injection.
- Cache consent state with a short TTL (e.g., 30s Redis TTL) to avoid Redis call on every message.

---

## 4. HARD STOP: Global and Higher Than Persona/Autonomy

### 4.1 Source Confirmation

**File:** `src/persona/safe_mode.py` — `SafeModeController` and `DistressDetector`

**File:** `src/persona/yandere_fsm.py` — `YandereEngine` with `SupportsIsSafe` protocol

**File:** `src/persona/punishment_engine.py` — `PunishmentEngine` checks `HardStopHandler`

### 4.2 Status

HARD STOP is well-implemented:
- `HardStopHandler` is the authoritative source for HARD STOP state.
- `PunishmentEngine` checks `HardStopHandler.is_safe` before apply/escalate/resume (R-02 fix).
- `YandereEngine` has `SupportsIsSafe` protocol integration.
- `SafeModeController` handles distress-based safe mode.

**Gap:** `SafeModeController` is NOT activated when HARD STOP keyword fires (PR-01 in KNOWN-ISSUES.md). This is a known gap, partially resolved.

### 4.3 Fix Required

- Implement `SafetyCoordinator` that bridges `HardStopHandler` and `SafeModeController`.
- HARD STOP keyword MUST activate SafeModeController.
- This is deferred to P5 in KNOWN-ISSUES.md but is in scope for Lane C.

---

## 5. Distress/Safety Override: Not Defeated by Punishment/Persona/Ritual

### 5.1 Source Confirmation

- `PunishmentEngine` checks `HardStopHandler.is_safe` before applying punishment (R-02 fix).
- Distress D0-D4 protocol is implemented in `SafeModeController`.
- D3+ crisis → neutral support; D4 explicit crisis → immediate neutral + resources.

### 5.2 Status

The protection chain is:
1. Distress detected → SafeModeController activated.
2. HARD STOP keyword → HardStopHandler activated.
3. PunishmentEngine checks HardStopHandler before applying punishment.
4. YandereEngine respects SupportsIsSafe protocol.

**Gap:** No guarantee that rituals/mood injection checks distress state before firing. If a ritual is mid-execution during a distress event, it may continue.

### 5.3 Fix Required

- Ritual scheduler must check SafeModeController.is_active before executing rituals.
- Mood injection must check SafeModeController.is_active before injecting mood context.
- PersonaPlugin must check BOTH consent AND safety state.

---

## 6. Six Behavioral Engines: Wired vs Dead Code

### 6.1 Engine Status Matrix

| Engine | File | Unit Tests | Runtime Wired? | Live Pathway? |
|--------|------|-----------|----------------|---------------|
| MoodEngine | `mood_engine.py` | ✅ | ⚠️ PARTIAL | Only via Discord `/mood` command (degraded placeholder) |
| YandereEngine | `yandere_fsm.py` | ✅ | ⚠️ PARTIAL | State is in-memory only, lost on restart (KI-03) |
| PunishmentEngine | `punishment_engine.py` | ✅ | ✅ | Wired via Discord commands + Hermes plugin |
| RewardEngine | `reward_engine.py` | ✅ | ⚠️ PARTIAL | Wired via Discord commands, but PersonaPlugin path unclear |
| StreakTracker | `streak_tracker.py` | ✅ | ❌ | Not wired to any runtime path |
| DriftDetector | `drift_detector.py` | ✅ | ❌ | On-demand only, no automated cadence (D-01) |
| DriftCorrector | `drift_corrector.py` | ✅ | ❌ | Manual trigger only, no DB persistence |
| RitualScheduler | `ritual_scheduler.py` | ✅ | ⚠️ DEPRECATED | Deprecated in Phase 5; Hermes cron handles rituals now |
| MilestoneEngine | `milestone_engine.py` | ? | ❌ | No runtime wiring found |
| TransitionRuleEngine | `transition_rules.py` | ✅ | ❌ | **DELETED** (per KNOWN-ISSUES.md PR-01) |
| SafeModeController | `safe_mode.py` | ✅ | ⚠️ PARTIAL | Distress detection not wired to Discord on_message (KI-05) |

### 6.2 Decision Required

For each engine, the decision is:
- **WIRE:** Wire to runtime (PersonaPlugin, Hermes lifecycle, Discord handlers).
- **DEPRECATE:** Formally deprecate with docs/evidence, remove from active import path.
- **DEFER:** Explicitly defer to a future phase with documented blocker.

### 6.3 Recommendation

| Engine | Recommendation | Reason |
|--------|---------------|--------|
| MoodEngine | WIRE | Core persona feature; prompt_loader doesn't inject live mood (KI-06) |
| YandereEngine | WIRE | Core safety feature; needs DB persistence (KI-03) |
| PunishmentEngine | WIRE | Already wired; verify completeness |
| RewardEngine | WIRE | Already partially wired; complete the wiring |
| StreakTracker | WIRE | Needed for mood/punishment context |
| DriftDetector | DEFER to P5 | Requires ValidationScheduler (architectural change) |
| DriftCorrector | DEFER to P5 | Depends on DriftDetector |
| RitualScheduler | DEPRECATE | Already deprecated in Phase 5; Hermes cron is canonical |
| MilestoneEngine | DEPRECATE | No runtime wiring, no known consumers |
| TransitionRuleEngine | ALREADY DELETED | Confirmed deleted per KNOWN-ISSUES.md |

---

## 7. Rituals Deprecated Mismatch

### 7.1 Source Confirmation

**File:** `src/persona/__init__.py` (lines 128-149)

```python
# Deprecated ritual imports (Phase 5 — kept for backward compatibility)
# These trigger DeprecationWarning; scheduled removal: Phase 7.
```

The ritual modules are imported with `DeprecationWarning` suppression. They still exist in the codebase but the docs say Hermes cron handles rituals now.

**In PROGRESS.md:** P4-008 through P4-013 show rituals as ✅ complete.

### 7.2 Impact

- Docs say rituals are implemented and working.
- Code says rituals are deprecated.
- Hermes cron may or may not be running the same rituals.
- This is a docs-vs-runtime mismatch.

### 7.3 Fix Required

- Audit Hermes cron ritual configuration to confirm it covers all 5 rituals.
- If Hermes cron covers them: mark Python rituals as FORMALLY DEPRECATED with clear docs.
- If Hermes cron does NOT cover them: restore Python rituals or add missing Hermes cron entries.
- Update PROGRESS.md and CHECKLIST.md to reflect actual runtime state.

---

## 8. Persona Injection: Runtime Proof Required

### 8.1 Source Confirmation

**File:** `src/hermes/plugins/persona_plugin.py`

The PersonaPlugin exists and is registered in the Hermes plugin system. However:
- No runtime log evidence of persona injection in production.
- Unit tests exist but don't prove runtime activation.
- The plugin loads from Redis DB5 for persona state.

### 8.2 Fix Required

- Add structured logging to PersonaPlugin to confirm injection at runtime.
- Verify via VPS logs that persona injection is actually happening.
- If not happening, debug and fix the plugin loading/registration.

---

## 9. Y4/Y5/Y6 Boundary: Status

### 9.1 Source Confirmation

**File:** `src/persona/yandere_fsm.py`

```python
ABSOLUTE_CEILING = ...  # Y5
PERMANENT_BASELINE = ... # Y4
```

- Y4 is permanent baseline — confirmed.
- Y5 is absolute ceiling — confirmed.
- Y6 is impossible — confirmed via `validate_level()` and `can_escalate()`.

### 9.2 Status

Y4/Y5/Y6 boundary is **INTACT** in the code. No fix needed.

---

## 10. Test Status

### 10.1 Existing Tests

- P4 test suite: 1288+ tests pass (post-cleanup baseline).
- Consent tests: ✅ exist in `test_consent_boundary.py`.
- Persona tests: ✅ exist across multiple test files.
- Safety tests: ✅ exist in `test_hard_stop_comprehensive.py`.

### 10.2 Tests to Add

- Consent revocation → persona injection stops (NEW).
- Consent revocation → surveillance pauses (NEW).
- PersonaPlugin consent check (NEW).
- Ritual scheduler safety check (NEW).
- Runtime injection proof test (NEW, integration-level).

---

## 11. Summary of Required Fixes

| ID | Severity | Description | Files to Modify |
|----|----------|-------------|-----------------|
| CONSENT-001 | **CRITICAL** | Consent revocation does not stop persona/surveillance | `src/hermes/plugins/persona_plugin.py`, `src/persona/safe_mode.py` |
| CONSENT-002 | **CRITICAL** | PersonaPlugin has no consent check before injection | `src/hermes/plugins/persona_plugin.py` |
| SAFE-001 | HIGH | SafeModeController not activated by HARD STOP keyword | `src/persona/safe_mode.py` (or new coordinator) |
| SAFE-002 | HIGH | Rituals don't check distress/safety state before execution | `src/persona/ritual_scheduler.py` or Hermes cron |
| WIRE-001 | HIGH | MoodEngine not wired to prompt_loader (KI-06) | `src/core/services/prompt_loader.py` |
| WIRE-002 | HIGH | DistressDetector not wired to Discord on_message (KI-05) | `src/discord/bot.py` |
| WIRE-003 | MEDIUM | YandereEngine state lost on restart (KI-03) | `src/persona/yandere_fsm.py` |
| WIRE-004 | MEDIUM | StreakTracker not wired to any runtime path | `src/persona/streak_tracker.py` + consumers |
| RITUAL-001 | MEDIUM | Rituals deprecated but docs say complete | `src/persona/__init__.py`, docs |
| DEAD-001 | MEDIUM | MilestoneEngine has no runtime wiring | Decision: deprecate or wire |
| DEAD-002 | MEDIUM | DriftDetector/DriftCorrector on-demand only | Decision: defer to P5 or wire |
| PROOF-001 | MEDIUM | No runtime proof of persona injection | Production logging |

---

## 12. Evidence Sources

- `src/persona/__init__.py` — full file read (245 lines)
- `src/persona/safe_mode.py` — partial read (80 lines)
- `src/hermes/plugins/persona_plugin.py` — grep for consent/safety
- `src/discord/cmd_consent.py` — partial read (60 lines)
- `docs/setup-evidence/P4/KNOWN-ISSUES.md` — full file read (352 lines)
- `audit-reports/P4/` — 23 files catalogued
- `src/persona/` — 19 files catalogued
- PROGRESS.md — P4 section shows 23/23 complete, P4-008-023 all checked
- CHECKLIST.md — P4 section shows all steps verified