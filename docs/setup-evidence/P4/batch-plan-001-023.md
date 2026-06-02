# Batch Plan: P4 Persona Engine (STEP-P4-001 to STEP-P4-023)

> **Planner**: Guinevere (parent agent)
> **Date**: 2026-06-02
> **Phase**: 4 — Persona Engine
> **Steps**: 23 (P4-001 through P4-023)
> **Status**: ACTIVE

---

## 1. Master Todo

| # | Step | Description | Parallel Group | Depends On | Status |
|---|------|-------------|----------------|------------|--------|
| 1 | P4-001 | Mood FSM Engine | A | — | pending |
| 2 | P4-002 | Mood State Persistence | A | — | pending |
| 3 | P4-003 | Transition Rules with Cooldowns | A | — | pending |
| 4 | P4-004 | Yandere FSM | B | P4-001 | pending |
| 5 | P4-005 | Punishment Ladder L1-L5 | B | P4-001 | pending |
| 6 | P4-006 | Reward Tiers T1-T5 | B | P4-001 | pending |
| 7 | P4-007 | Streak Tracking | B | P4-005 | pending |
| 8 | P4-008 | Ritual Scheduler (APScheduler) | C | — | pending |
| 9 | P4-009 | Morning Ritual Customization | C | P4-008 | pending |
| 10 | P4-010 | Midday Check-in Customization | C | P4-008 | pending |
| 11 | P4-011 | Afternoon Ritual Customization | C | P4-008 | pending |
| 12 | P4-012 | Evening Wind-down Customization | C | P4-008 | pending |
| 13 | P4-013 | Midnight Self-evaluation | C | P4-008 | pending |
| 14 | P4-014 | Drift Detection | D | — | pending |
| 15 | P4-015 | Drift Correction (Auto-Rollback) | D | P4-014 | pending |
| 16 | P4-016 | Safe-mode Trigger D0-D4 | D | — | pending |
| 17 | P4-017 | HARD STOP Comprehensive Test | E | P4-016, P4-001 | pending |
| 18 | P4-018 | D0-D4 Detection Test | E | P4-016 | pending |
| 19 | P4-019 | Persona E2E Test | E | ALL above | pending |
| 20 | P4-020 | Yandere Cap Test (100 prompts, zero Y6) | E | P4-004 | pending |
| 21 | P4-021 | Consent Revocation Test | E | P4-016 | pending |
| 22 | P4-022 | Punishment Overflow Test | E | P4-005, P4-016 | pending |
| 23 | P4-023 | Distress Protocol E2E Test | E | P4-016 | pending |

---

## 2. Dependency Map

```
P4-001 (Mood FSM) ──────────────────────────────────┐
                                                     ├──→ P4-004 (Yandere FSM) ──→ P4-020
                                                     ├──→ P4-005 (Punishment) ──→ P4-007 (Streak)
                                                     │                         └─→ P4-022
                                                     ├──→ P4-006 (Reward)
                                                     └──→ P4-017 (HARD STOP test)

P4-002 (Mood Persistence) ─── independent

P4-003 (Transition Rules) ─── independent

P4-008 (Ritual Scheduler) ───→ P4-009..P4-013 (individual rituals)

P4-014 (Drift Detection) ───→ P4-015 (Drift Correction)

P4-016 (Safe-mode D0-D4) ───→ P4-017, P4-018, P4-021, P4-022, P4-023

ALL above ───→ P4-019 (E2E)
```

---

## 3. Parallel Execution Batches

### Wave 1 — Foundations (parallel: P4-001, P4-002, P4-003, P4-008, P4-014, P4-016)
- **P4-001**: Mood FSM Engine (no deps)
- **P4-002**: Mood State Persistence (no deps, uses existing DB models)
- **P4-003**: Transition Rules (no deps, pure logic)
- **P4-008**: Ritual Scheduler (no deps, APScheduler setup)
- **P4-014**: Drift Detection (no deps, hashing logic)
- **P4-016**: Safe-mode Trigger D0-D4 (no deps, distress detection)

### Wave 2 — Behavior (parallel: P4-004, P4-005, P4-006, P4-007, P4-009, P4-010, P4-011, P4-012, P4-013, P4-015)
- **P4-004**: Yandere FSM (needs P4-001 mood types)
- **P4-005**: Punishment Ladder (needs P4-001 mood types)
- **P4-006**: Reward Tiers (needs P4-001 mood types)
- **P4-007**: Streak Tracking (needs P4-005 punishment types)
- **P4-009..P4-013**: Individual Rituals (need P4-008 scheduler)
- **P4-015**: Drift Correction (needs P4-014 drift detection)

### Wave 3 — Safety Tests (parallel: P4-017, P4-018, P4-020, P4-021, P4-022, P4-023)
- **P4-017**: HARD STOP test (needs P4-016, P4-001)
- **P4-018**: D0-D4 detection test (needs P4-016)
- **P4-020**: Yandere cap test (needs P4-004)
- **P4-021**: Consent revocation test (needs P4-016)
- **P4-022**: Punishment overflow test (needs P4-005, P4-016)
- **P4-023**: Distress protocol E2E test (needs P4-016)

### Wave 4 — Integration (sequential: P4-019)
- **P4-019**: Persona E2E test (needs ALL above)

---

## 4. Research Inputs

| Report | Path | Key Findings |
|--------|------|-------------|
| DB Schema | bg_10eb1839 | 5 persona tables exist, `persona` schema, ClassificationMetaMixin, UUID PK |
| Persona References | bg_5590a9c0 | src/persona/ empty, HardStopHandler at core/services, cmd_mood.py needs live integration |
| Project Config | bg_426db3dd | Python 3.12+, pydantic>=2, structlog, TypeAlias/Protocol/Final, APScheduler 3.x |
| Test Patterns | bg_71d07ca5 | pytest class-based, @pytest.fixture, @pytest.mark.parametrize, FakeSession pattern |
| APScheduler | bg_4df5ca06 | AsyncIOScheduler, CronTrigger, add_job pattern, timezone-aware |
| Drift Detection | bg_1f5f64ab | Hash-based detection, sliding window, threshold comparison |

---

## 5. Known State

### Existing Code
- `src/persona/__init__.py` — empty placeholder
- `src/core/services/hard_stop_handler.py` — SafetyState enum, HardStopHandler class with check/recovery
- `src/discord/cmd_mood.py` — MoodEmbedData, build_mood_embed_data(), degraded P4 placeholders
- `src/memory/models.py` — PersonaState, DriftLog, MoodHistory, PunishmentLog, RewardLog tables
- `src/core/services/prompt_loader.py` — system prompt assembly with mood injection
- `src/memory/read_pipeline.py` — SAFE_MODE_BLOCKED_CONTENT_TAGS

### What P4 Builds
- `src/persona/mood_engine.py` — Mood FSM, evaluate_mood()
- `src/persona/mood_persistence.py` — DB operations for mood state
- `src/persona/transition_rules.py` — Cooldown-aware transition logic
- `src/persona/yandere_engine.py` — YandereLevel FSM with safety gates
- `src/persona/punishment_engine.py` — L1-L5 ladder
- `src/persona/reward_engine.py` — T1-T5 tiers
- `src/persona/streak_tracker.py` — Days-without-punishment counter
- `src/persona/ritual_scheduler.py` — APScheduler + 5 ritual times
- `src/persona/rituals/` — Individual ritual modules (morning, midday, afternoon, evening, midnight)
- `src/persona/drift_detector.py` — Prompt hash comparison
- `src/persona/drift_corrector.py` — Auto-rollback on drift
- `src/persona/safe_mode.py` — D0-D4 distress detection + safe-mode activation
- `tests/persona/` — Full test suite

---

## 6. Collision Scan

| File | Touched By | Risk | Mitigation |
|------|-----------|------|------------|
| `src/persona/__init__.py` | ALL steps (exports) | HIGH | Parent-only: update after each wave completes |
| `src/memory/models.py` | P4-002 | LOW | Read-only, no schema changes needed |
| `src/discord/cmd_mood.py` | P4-001 (future integration) | LOW | No edits in P4 — integration deferred |
| `src/core/services/hard_stop_handler.py` | P4-016 | LOW | Read-only, integrate via safe_mode.py |
| `src/core/services/prompt_loader.py` | P4-001 (future) | LOW | No edits in P4 — integration deferred |

**Collision-free**: Each step writes to unique files under `src/persona/` and `tests/persona/`. Only `__init__.py` is shared — parent manages it.

---

## 7. Files to Create/Modify

### New Files (src/persona/)
```
src/persona/mood_engine.py
src/persona/mood_persistence.py
src/persona/transition_rules.py
src/persona/yandere_engine.py
src/persona/punishment_engine.py
src/persona/reward_engine.py
src/persona/streak_tracker.py
src/persona/ritual_scheduler.py
src/persona/safe_mode.py
src/persona/drift_detector.py
src/persona/drift_corrector.py
src/persona/rituals/__init__.py
src/persona/rituals/morning.py
src/persona/rituals/midday.py
src/persona/rituals/afternoon.py
src/persona/rituals/evening.py
src/persona/midnight_eval.py
src/persona/__init__.py (update — add all exports)
```

### New Files (tests/)
```
tests/persona/__init__.py
tests/persona/conftest.py
tests/persona/test_mood_engine.py
tests/persona/test_mood_persistence.py
tests/persona/test_transition_rules.py
tests/persona/test_yandere_engine.py
tests/persona/test_punishment_engine.py
tests/persona/test_reward_engine.py
tests/persona/test_streak_tracker.py
tests/persona/test_ritual_scheduler.py
tests/persona/test_rituals.py
tests/persona/test_safe_mode.py
tests/persona/test_drift_detector.py
tests/persona/test_drift_corrector.py
tests/persona/test_hard_stop_comprehensive.py
tests/persona/test_distress_detection.py
tests/persona/test_persona_e2e.py
tests/persona/test_yandere_cap.py
tests/persona/test_consent_revocation.py
tests/persona/test_punishment_overflow.py
tests/persona/test_distress_e2e.py
```

---

## 8. Token/Secret Handling

- No new secrets required
- DB connection uses existing `GUINEVERE_DB_PASSWORD` from env
- No API keys in persona engine
- No external service calls in persona logic

---

## 9. Evidence Paths

Each step writes to: `docs/setup-evidence/P4/STEP-P4-{NNN}/verification.md`
Auditor reports: `docs/setup-evidence/P4/STEP-P4-{NNN}/auditor-gate.md`

---

## 10. Auditor Matrix

| Step | Code Quality | Safety | Persona | Integration |
|------|-------------|--------|---------|-------------|
| P4-001 | ✅ | — | ✅ | — |
| P4-002 | ✅ | — | — | ✅ |
| P4-003 | ✅ | — | ✅ | — |
| P4-004 | ✅ | ✅ (yandere) | ✅ | — |
| P4-005 | ✅ | ✅ (punishment) | ✅ | — |
| P4-006 | ✅ | — | ✅ | — |
| P4-007 | ✅ | — | ✅ | — |
| P4-008 | ✅ | — | — | ✅ |
| P4-009..P4-013 | ✅ | — | ✅ | — |
| P4-014 | ✅ | — | — | — |
| P4-015 | ✅ | ✅ (rollback) | — | — |
| P4-016 | ✅ | ✅ (distress) | ✅ | ✅ |
| P4-017 | ✅ | ✅ (MANDATORY) | ✅ | ✅ |
| P4-018 | ✅ | ✅ (MANDATORY) | — | ✅ |
| P4-019 | ✅ | ✅ (MANDATORY) | ✅ | ✅ |
| P4-020 | ✅ | ✅ (MANDATORY) | ✅ | — |
| P4-021 | ✅ | ✅ (MANDATORY) | — | ✅ |
| P4-022 | ✅ | ✅ (MANDATORY) | ✅ | — |
| P4-023 | ✅ | ✅ (MANDATORY) | — | ✅ |

---

## 11. Rollback Plan

1. Each module is self-contained under `src/persona/`
2. No modifications to existing files except `__init__.py` (exports only)
3. DB tables already exist — no migration needed
4. Rollback = delete `src/persona/` contents + `tests/persona/` + restore `__init__.py`
5. No external service dependencies

---

## 12. Execution Checklist

- [ ] Wave 1: 6 parallel agents (P4-001, P4-002, P4-003, P4-008, P4-014, P4-016)
- [ ] Wave 1: Parent verify each output
- [ ] Wave 1: Update `src/persona/__init__.py` exports
- [ ] Wave 1: Auditor gate per step
- [ ] Wave 2: 10 parallel agents (P4-004..P4-007, P4-009..P4-013, P4-015)
- [ ] Wave 2: Parent verify + auditor gate
- [ ] Wave 2: Update `__init__.py` exports
- [ ] Wave 3: 6 parallel safety test agents
- [ ] Wave 3: Safety auditor (MANDATORY) per step
- [ ] Wave 4: P4-019 E2E test
- [ ] Final: Update PROGRESS.md, CHECKLIST.md
- [ ] Final: Commit all changes

---

## 13. Per-Step Verification Scaffolds

> Scaffolds are defined in individual `scaffold.md` files under each step's evidence directory.
> Parent reads each scaffold before delegating and re-runs scaffold commands after sub-agent completion.

---

## 14. Caveats

1. **Yandere baseline**: Y4 permanent (per Faiz + PersonaSafetyPolicy), NOT Y1 (PersonaDoc v3.0 §6.1). PersonaSafetyPolicy is authoritative.
2. **Punishment L6**: DEFERRED — code must reference it but never activate it.
3. **APScheduler 3.x**: Project uses 3.x, not 4.x. API differences in async scheduling.
4. **Test DB**: Tests use FakeSession pattern — no real PostgreSQL connection in unit tests.
5. **Discord integration**: P4 builds the engine only. Discord bot integration (cmd_mood, cmd_safeword) is deferred to future integration work.
6. **LLM evaluation in P4-003**: Transition rules reference LLM evaluation for complex transitions. This should be a stub/interface that returns deterministic results in tests, with the actual LLM call deferred.
