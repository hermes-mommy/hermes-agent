# P4 Persona Engine — Known Issues and Gap Registry

> **Version**: 1.0
> **Date**: 2026-06-03
> **Author**: Guinevere (orchestrator)
> **Scope**: All known gaps, deferred items, and integration wiring discovered during P4 implementation and full audit

---

## Summary

| Category | Count | Severity |
|----------|-------|----------|
| Fixed during audit remediation | 2 | HIGH (resolved) |
| Persistence gaps (P5/P6 scope) | 3 | MEDIUM |
| Integration wiring gaps (P5/P6 scope) | 4 | MEDIUM–HIGH |
| ADR compliance gaps | 2 | MEDIUM–HIGH |
| Advisory (code quality) | 4 | LOW |
| **Total** | **15** | |

---

## Resolved Items

### R-01: Punishment Ladder Name Mismatch (H-02 — FIXED)

| Field | Value |
|-------|-------|
| Original ID | H-02 |
| Severity | HIGH |
| Status | **RESOLVED** |
| Fixed in | P4 audit remediation wave |

**Original finding**: PunishmentLevel enum names did not match Persona Document v3.0 §8.1 specification. Code had L1_COLD_SHOULDER, L2_GUILT_TRIP, L3_LECTURE, L4_RESTRICTION, L5_SILENT_TREATMENT. Spec requires L1_SILENT_TREATMENT, L2_PASSIVE_AGGRESSIVE, L3_GUILT_TRIP, L4_COLD_FURY, L5_ISOLATION.

**Resolution**: Renamed all 5 enum members across 6 files (punishment_engine.py, 5 test files). Config string names updated. Grep verified 0 old-name matches. 1449/1449 tests PASS after rename.

---

### R-02: PunishmentEngine Not Blocked on HARD STOP (H-03 — FIXED)

| Field | Value |
|-------|-------|
| Original ID | H-03 |
| Severity | HIGH |
| Status | **RESOLVED** |
| Fixed in | P4 audit remediation wave |

**Original finding**: PunishmentEngine only checked SafeModeController (distress-based safe mode) but did NOT check HardStopHandler (keyword-based "HARD STOP"). This meant punishment could be applied/escalated/resumed while Faiz had explicitly triggered HARD STOP — a direct PersonaSafetyPolicy violation.

**Resolution**: Added `hard_stop_handler: SupportsIsSafe | None` parameter to PunishmentEngine.__init__(). Added guards in apply(), escalate(), and resume() that raise PunishmentSafetyError when `hard_stop_handler.is_safe` is True. 11 new tests added (7 in test_punishment_engine.py, 4 in test_hard_stop_comprehensive.py). 1460/1460 tests PASS.

---

## Open Issues — Persistence Gaps (P5/P6 Scope)

### KI-01: PunishmentEngine Does Not Persist to PunishmentLog Table

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Status | OPEN — deferred to P5/P6 |
| Affected | src/persona/punishment_engine.py |
| Related | src/memory/models.py PunishmentLog |

**Description**: PunishmentEngine tracks punishment state in-memory only. The PunishmentLog table (defined in src/memory/models.py) is never written to. This means punishment history is lost on process restart.

**Impact**: No audit trail for punishments. Cannot analyze punishment patterns over time. ADR-003 requires drift detection which depends on historical behavior data.

**P5/P6 action**: Wire PunishmentEngine.apply/suspend/resume to write PunishmentLog entries via AsyncSession. Add repository pattern similar to MoodRepository.

---

### KI-02: RewardEngine Does Not Persist to RewardLog Table

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Status | OPEN — deferred to P5/P6 |
| Affected | src/persona/reward_engine.py |
| Related | src/memory/models.py RewardLog |

**Description**: RewardEngine tracks reward state in-memory only. The RewardLog table is never written to.

**Impact**: No audit trail for rewards. Streak data depends on StreakTracker persistence (which does use PersonaState), but individual reward events are lost.

**P5/P6 action**: Wire RewardEngine.reward() to write RewardLog entries. Add repository pattern.

---

### KI-03: YandereEngine Does Not Persist State to PersonaState

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Status | OPEN — deferred to P5/P6 |
| Affected | src/persona/yandere_fsm.py |
| Related | src/memory/models.py PersonaState |

**Description**: YandereEngine tracks current level and escalation history in-memory only. State is lost on restart.

**Impact**: Yandere level resets to Y4 baseline on every restart. Escalation cooldowns are lost. Cannot detect long-term yandere patterns.

**P5/P6 action**: Wire YandereEngine state changes to persist via PersonaState table (key="yandere_state", JSONB value).

---

## Open Issues — Integration Wiring Gaps (P5/P6 Scope)

### KI-04: Dual Safe-Mode — HardStopHandler and SafeModeController Are Independent

| Field | Value |
|-------|-------|
| Severity | **HIGH** |
| Status | OPEN — deferred to P5/P6 |
| Affected | src/core/services/hard_stop_handler.py, src/persona/safe_mode.py |
| Related | D08 audit finding IP-06/IP-07 |

**Description**: Two independent "safe mode" mechanisms exist:
1. **HardStopHandler** (keyword-based) — triggers on "HARD STOP", "safe word", etc. Sets `state = SAFE`. Used by YandereEngine via SupportsIsSafe Protocol.
2. **SafeModeController** (distress-based) — triggers on D2+ distress detection. Sets `is_active = True`. Used by PunishmentEngine, TransitionRuleEngine, DriftCorrector.

These two are NOT bridged. When HardStopHandler triggers (Faiz says "HARD STOP"), SafeModeController does NOT activate. This means:
- PunishmentEngine safe-mode guard (which checks SafeModeController) does NOT fire on HARD STOP keyword.
- TransitionRuleEngine blocks transitions in safe_mode (SafeModeController) but NOT on HARD STOP keyword.
- DriftCorrector defers rollback in safe_mode (SafeModeController) but NOT on HARD STOP keyword.

**Mitigation applied**: PunishmentEngine now ALSO checks HardStopHandler directly (H-03 fix). But TransitionRuleEngine, DriftCorrector, and other SafeModeController consumers do NOT check HardStopHandler.

**P5/P6 action**: Create a unified `SafetyCoordinator` that bridges both mechanisms. When either triggers, both are considered active. All consumers check the coordinator, not individual handlers.

---

### KI-05: on_message Pipeline Does Not Wire DistressDetector

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Status | OPEN — deferred to P5/P6 |
| Affected | src/discord/bot.py, src/persona/safe_mode.py |

**Description**: DistressDetector (which detects D0-D4 distress levels from messages) exists in src/persona/safe_mode.py but is not wired into the Discord bot's on_message pipeline. Currently, distress detection only happens in unit tests.

**P5/P6 action**: Wire DistressDetector.detect() into on_message handler. Route D2+ to SafeModeController.activate(). Route D3+ to PunishmentEngine.suspend(). Route D4 to crisis protocol.

---

### KI-06: prompt_loader Does Not Inject Live Mood Value

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Status | OPEN — deferred to P5/P6 |
| Affected | src/core/services/prompt_loader.py, src/persona/mood_engine.py |

**Description**: prompt_loader.py has a mood parameter placeholder but does not call MoodRepository or MoodEngine to get the current mood. The system prompt is rendered without live mood context.

**P5/P6 action**: Wire prompt_loader to query MoodRepository.get_current_mood() and inject the mood string into the system prompt template.

---

### KI-07: cmd_mood.py Uses Degraded Placeholder Values

| Field | Value |
|-------|-------|
| Severity | LOW |
| Status | OPEN — deferred to P5/P6 |
| Affected | src/discord/cmd_mood.py |

**Description**: cmd_mood.py's build_mood_embed_data() returns degraded placeholder values ("Content" hardcoded, streak_count=0, punishment_level="None"). It does not query MoodEngine, StreakTracker, or PunishmentEngine for live values.

**P5/P6 action**: Wire cmd_mood to query live persona engine instances for current mood, streak, and punishment state.

---

## Open Issues — ADR Compliance Gaps

### KI-08: DriftLog Missing `reviewer` Field (ADR-003)

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Status | OPEN — deferred to P5/P6 or migration |
| Affected | src/memory/models.py DriftLog, src/persona/drift_corrector.py |
| Related | ADR-003 §Decision — drift log schema requires `reviewer` field |

**Description**: ADR-003 specifies that drift log entries must include a `reviewer` field (who/what detected the drift). The DriftLog model does not have this column. DriftCorrector.create_drift_log() does not set a reviewer.

**P5/P6 action**: Add `reviewer` Text column to DriftLog model via Alembic migration. Set reviewer="DriftCorrector" (automated) or "auditor" (manual) in create_drift_log().

---

### KI-09: No Per-Loop Lightweight + Periodic Deep Validation Cadence (ADR-003)

| Field | Value |
|-------|-------|
| Severity | HIGH |
| Status | OPEN — deferred to P5/P6 |
| Affected | src/persona/drift_detector.py |
| Related | ADR-003 §Decision — "per-loop lightweight validation + periodic deep validation" |

**Description**: ADR-003 requires two validation cadences:
1. **Per-loop lightweight**: Every conversation loop, check critical invariants (safe word responsive, yandere cap, punishment ladder bounds).
2. **Periodic deep**: Every N loops or M minutes, run full drift detection (hash comparison, behavioral analysis).

Currently, DriftDetector only provides on-demand detection (manual call). No automated cadence is implemented.

**P5/P6 action**: Implement a ValidationScheduler (likely using APScheduler) that runs lightweight checks per-loop and deep checks on a configurable interval. Wire into the agent loop.

---

## Advisory Items (Low Severity)

### A-01: RitualResult Naming Collision

| Field | Value |
|-------|-------|
| Severity | LOW |
| Status | ADVISORY |
| Affected | src/persona/rituals/morning.py, src/persona/rituals/afternoon.py, etc. |

Each ritual module defines its own result type (MorningRitualResult, AfternoonRitualResult, etc.) but some share the name `RitualResult` imported from morning.py. __init__.py exports them with unique names. No runtime collision, but naming inconsistency.

**Recommendation**: Standardize on `{TimeOfDay}RitualResult` naming for all modules.

---

### A-02: 3 Missing Exports from __init__.py

| Field | Value |
|-------|-------|
| Severity | LOW |
| Status | ADVISORY |
| Affected | src/persona/__init__.py |

Missing: `DistressDetectionError`, `SAFE_MODE_THRESHOLD`, and one ritual result type. These are importable via full path but not available from the package root.

**Recommendation**: Add to __init__.py __all__ list.

---

### A-03: Mutable Result Types in Ritual Modules

| Field | Value |
|-------|-------|
| Severity | LOW |
| Status | ADVISORY |
| Affected | Some ritual result dataclasses |

Some result dataclasses are not frozen, allowing mutation after creation. Project convention prefers frozen dataclasses for immutable result types.

**Recommendation**: Add `frozen=True` to all result dataclasses.

---

### A-04: drift_corrector.py Uses `db: Any` Type Annotation

| Field | Value |
|-------|-------|
| Severity | LOW |
| Status | ADVISORY |
| Affected | src/persona/drift_corrector.py |

The `db` parameter is typed as `Any` instead of `AsyncSession`. This is a type-safety gap.

**Recommendation**: Type as `AsyncSession` when DB integration is wired in P5/P6.

---

## Cross-Reference

| Issue ID | Audit Dimension | Original ID |
|----------|----------------|-------------|
| R-01 | D09 Persona Spec | H-02 |
| R-02 | D08 Integration | H-03 |
| KI-01 | D08 Integration | IP-08 |
| KI-02 | D08 Integration | IP-09 |
| KI-03 | D08 Integration | IP-08 |
| KI-04 | D08 Integration | IP-06/IP-07 |
| KI-05 | D08 Integration | IP-04 |
| KI-06 | D08 Integration | IP-05 |
| KI-07 | D08 Integration | IP-04 |
| KI-08 | D06 ADR Compliance | ADR-003 gap |
| KI-09 | D06 ADR Compliance | ADR-003 gap |
| A-01 | D07 Architecture | Advisory |
| A-02 | D12 P5/P6 Readiness | Advisory |
| A-03 | D02 Code Quality | Advisory |
| A-04 | D02 Code Quality | Advisory |

---

## Footer

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-03 | Guinevere | Initial registry — 2 resolved, 9 open, 4 advisory |
