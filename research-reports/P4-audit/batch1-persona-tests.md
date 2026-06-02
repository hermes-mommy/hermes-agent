# Batch 1 — Persona Test Suite Inventory

> **Audit Date:** 2026-06-02
> **Scope:** `tests/persona/` — 6 test files (P4-001, P4-002, P4-003, P4-015, drift_detector, yandere_fsm)
> **Methodology:** Full file read, line-by-line extraction of classes, methods, decorators, assertions, and fixtures.

---

## Executive Summary

| Metric | Count |
|---|---|
| Test files analyzed | 6 |
| Total test classes | 59 |
| Total test methods | 265 |
| Total `@pytest.mark.parametrize` decorators | 15 |
| Total `assert` statements | 417 |
| Total fixtures defined | 21 |
| Async test methods (`@pytest.mark.asyncio`) | 56 |


---

## File 1: `test_mood_engine.py`

**Path:** `C:\Users\faizz\guinevere\tests\persona\test_mood_engine.py`
**Lines:** 495
**Docstring:** P4-001: Mood FSM Engine Deterministic Unit Tests
**Imports from:** `src.persona.mood_engine`

### Summary

| Metric | Count |
|---|---|
| Test classes | 7 |
| Test methods | 49 |
| `@pytest.mark.parametrize` | 2 |
| `assert` statements | 70 |
| Fixtures defined | 1 |

### Fixtures Defined

| Fixture | Line | Description |
|---|---|---|
| `all_moods` | 30 | Returns all five Mood enum members |

### Parametrize Decorators

| # | Method | Parameters | Test Cases |
|---|---|---|---|
| 1 | `test_valid_transitions` | `current, target` (2 params) | 9 cases (all valid transitions) |
| 2 | `test_invalid_transitions` | `current, target` (2 params) | 16 cases (self-transitions + cross-level jumps) |

### Classes and Methods

#### Class: `TestMoodEnum` (line 40)
*Verify all 5 mood states exist with correct string values.*

| # | Method | Line |
|---|---|---|
| 1 | `test_content_value` | 43 |
| 2 | `test_pleased_value` | 47 |
| 3 | `test_disappointed_value` | 50 |
| 4 | `test_angry_value` | 53 |
| 5 | `test_silent_value` | 56 |
| 6 | `test_all_five_moods_exist` | 59 |
| 7 | `test_mood_is_str_enum` | 63 |
| 8 | `test_mood_string_interop` | 68 |

#### Class: `TestTransitions` (line 83)
*Verify the TRANSITIONS dict covers all moods and valid edges.*

| # | Method | Line |
|---|---|---|
| 1 | `test_all_moods_have_entries` | 86 |
| 2 | `test_content_transitions` | 91 |
| 3 | `test_pleased_transitions` | 94 |
| 4 | `test_disappointed_transitions` | 97 |
| 5 | `test_angry_transitions` | 100 |
| 6 | `test_silent_transitions` | 103 |
| 7 | `test_total_valid_edges` | 106 |
| 8 | `test_transitions_is_final` | 114 |

#### Class: `TestCanTransition` (line 124)
*Boolean transition checker against the TRANSITIONS map.*

| # | Method | Line | Decorators |
|---|---|---|---|
| 1 | `test_valid_transitions` | 143 | `@pytest.mark.parametrize` (9 cases) |
| 2 | `test_invalid_transitions` | 171 | `@pytest.mark.parametrize` (16 cases) |

#### Class: `TestEvaluateMood` (line 180)
*Heuristic mood evaluator — signal-based transition proposals.*

| # | Method | Line |
|---|---|---|
| 1 | `test_positive_sentiment_with_task_completion` | 185 |
| 2 | `test_positive_sentiment_without_task_completion` | 197 |
| 3 | `test_task_completion_without_positive_sentiment` | 207 |
| 4 | `test_ignored_count_2_disappointed` | 219 |
| 5 | `test_ignored_count_3_disappointed` | 229 |
| 6 | `test_ignored_count_4_angry` | 242 |
| 7 | `test_ignored_count_10_angry` | 253 |
| 8 | `test_neutral_inputs_no_transition` | 266 |
| 9 | `test_boundary_sentiment_no_transition` | 275 |
| 10 | `test_zero_sentiment_no_transition` | 285 |
| 11 | `test_ignored_from_pleased_skips_to_none` | 296 |
| 12 | `test_positive_from_silent_no_transition` | 311 |

#### Class: `TestMoodTransition` (line 327)
*MoodTransition dataclass — default values and mutability.*

| # | Method | Line |
|---|---|---|
| 1 | `test_default_cooldown` | 330 |
| 2 | `test_custom_cooldown` | 338 |
| 3 | `test_mutable_state` | 347 |
| 4 | `test_from_mood_and_to_mood_preserved` | 359 |

#### Class: `TestErrorHierarchy` (line 375)
*Custom exception classes follow proper inheritance.*

| # | Method | Line |
|---|---|---|
| 1 | `test_mood_engine_error_is_exception` | 378 |
| 2 | `test_invalid_transition_is_mood_engine_error` | 381 |
| 3 | `test_evaluation_error_is_mood_engine_error` | 384 |
| 4 | `test_raise_invalid_transition` | 387 |
| 5 | `test_raise_evaluation_error` | 391 |
| 6 | `test_catch_as_base_error` | 395 |

#### Class: `TestEdgeCases` (line 408)
*Boundary conditions and FSM invariants.*

| # | Method | Line |
|---|---|---|
| 1 | `test_silent_can_only_go_to_content` | 411 |
| 2 | `test_angry_can_only_go_to_disappointed_or_silent` | 417 |
| 3 | `test_no_self_transitions` | 423 |
| 4 | `test_fsm_is_connected` | 428 |
| 5 | `test_evaluate_ignored_priority_over_sentiment` | 444 |
| 6 | `test_evaluate_ignored_4_priority_over_sentiment` | 455 |
| 7 | `test_ignored_1_no_transition` | 466 |
| 8 | `test_negative_sentiment_no_transition` | 476 |
| 9 | `test_evaluate_from_all_moods_neutral` | 486 |

---

## File 2: `test_mood_persistence.py`

**Path:** `C:\Users\faizz\guinevere\tests\persona\test_mood_persistence.py`
**Lines:** 555
**Docstring:** P4-002: Mood State Persistence Layer — deterministic unit tests
**Imports from:** `src.persona.mood_persistence`

### Summary

| Metric | Count |
|---|---|
| Test classes | 7 |
| Test methods | 26 |
| `@pytest.mark.parametrize` | 0 |
| `assert` statements | 68 |
| Fixtures defined | 4 |
| Async methods (`@pytest.mark.asyncio`) | 26 |

### Fixtures Defined

| Fixture | Line | Description |
|---|---|---|
| `repo_empty` | 150 | Repository with no existing rows |
| `repo_with_mood` | 157 | Repository with an existing current_mood row |
| `repo_with_history` | 170 | Repository with multiple mood history entries |
| `repo_with_streak` | 198 | Repository with an existing mood_streak row |

### Fake DB Infrastructure (non-test helpers)

| Class | Line | Purpose |
|---|---|---|
| `FakePersonaState` | 41 | Mimics PersonaState ORM model |
| `FakeMoodHistory` | 51 | Mimics MoodHistory ORM model |
| `FakeScalars` | 63 | Wraps list to provide `.all()` |
| `FakeResult` | 73 | Mimics SQLAlchemy Result |
| `FakeAsyncSession` | 86 | Deterministic fake AsyncSession |
| `FailingAsyncSession` | 118 | Fake session that raises on execute/commit |

### Parametrize Decorators

None.

### Classes and Methods

#### Class: `TestGetCurrentMood` (line 215)

| # | Method | Line | Async |
|---|---|---|---|
| 1 | `test_returns_none_when_no_row` | 217 | Yes |
| 2 | `test_returns_mood_state` | 222 | Yes |
| 3 | `test_returns_frozen_dataclass` | 232 | Yes |

#### Class: `TestSetCurrentMood` (line 244)

| # | Method | Line | Async |
|---|---|---|---|
| 1 | `test_insert_when_no_existing_row` | 246 | Yes |
| 2 | `test_update_when_existing_row` | 261 | Yes |
| 3 | `test_default_intensity_and_updated_by` | 281 | Yes |

#### Class: `TestRecordMoodTransition` (line 297)

| # | Method | Line | Async |
|---|---|---|---|
| 1 | `test_inserts_history_entry` | 299 | Yes |
| 2 | `test_default_intensity` | 320 | Yes |

#### Class: `TestGetMoodHistory` (line 339)

| # | Method | Line | Async |
|---|---|---|---|
| 1 | `test_returns_history_records` | 341 | Yes |
| 2 | `test_returns_empty_when_no_history` | 361 | Yes |
| 3 | `test_frozen_dataclass` | 369 | Yes |

#### Class: `TestMoodStreak` (line 381)

| # | Method | Line | Async |
|---|---|---|---|
| 1 | `test_get_streak_returns_zero_when_no_row` | 383 | Yes |
| 2 | `test_get_streak_returns_value` | 391 | Yes |
| 3 | `test_update_streak_insert_when_no_row` | 398 | Yes |
| 4 | `test_update_streak_modifies_existing` | 412 | Yes |

#### Class: `TestErrorHandling` (line 434)

| # | Method | Line | Async |
|---|---|---|---|
| 1 | `test_get_current_mood_wraps_db_error` | 436 | Yes |
| 2 | `test_set_current_mood_wraps_db_error` | 447 | Yes |
| 3 | `test_set_current_mood_wraps_commit_error` | 458 | Yes |
| 4 | `test_record_mood_transition_wraps_error` | 470 | Yes |
| 5 | `test_get_mood_history_wraps_db_error` | 480 | Yes |
| 6 | `test_get_mood_streak_wraps_db_error` | 488 | Yes |
| 7 | `test_update_mood_streak_wraps_db_error` | 496 | Yes |
| 8 | `test_error_hierarchy` | 504 | Yes |

#### Class: `TestReturnTypeContracts` (line 516)

| # | Method | Line | Async |
|---|---|---|---|
| 1 | `test_mood_state_fields` | 518 | Yes |
| 2 | `test_mood_history_record_fields` | 531 | Yes |
| 3 | `test_mood_history_record_nullable_fields` | 546 | Yes |

---

## File 3: `test_yandere_fsm.py`

**Path:** `C:\Users\faizz\guinevere\tests\persona\test_yandere_fsm.py`
**Lines:** 526
**Docstring:** Comprehensive tests for Yandere Intensity FSM
**Imports from:** `persona.yandere_fsm`

### Summary

| Metric | Count |
|---|---|
| Test classes | 13 |
| Test methods | 71 |
| `@pytest.mark.parametrize` | 2 |
| `assert` statements | 78 |
| Fixtures defined | 4 |

### Fixtures Defined

| Fixture | Line | Description |
|---|---|---|
| `engine` | 45 | Fresh YandereEngine with default baseline (Y4) |
| `engine_with_handler` | 51 | YandereEngine wired to a FakeHardStopHandler |
| `engine_at_y0` | 59 | YandereEngine set to Y0_NEUTRAL |
| `engine_at_y5` | 67 | YandereEngine set to Y5_MAX |

### Fake Infrastructure

| Class | Line | Purpose |
|---|---|---|
| `FakeHardStopHandler` | 34 | Minimal stub mimicking HardStopHandler.is_safe |

### Parametrize Decorators

| # | Method | Parameters | Test Cases |
|---|---|---|---|
| 1 | `test_can_escalate_below_ceiling` | `level` (1 param) | 5 cases (Y0-Y4) |
| 2 | `test_valid_levels` | `value` (1 param) | 6 cases (0-5) |

### Classes and Methods

#### Class: `TestYandereLevelEnum` (line 79)
*Verify enum structure and constraints.*

| # | Method | Line |
|---|---|---|
| 1 | `test_y0_neutral_value` | 82 |
| 2 | `test_y1_minimal_value` | 85 |
| 3 | `test_y2_low_value` | 88 |
| 4 | `test_y3_moderate_value` | 91 |
| 5 | `test_y4_baseline_value` | 94 |
| 6 | `test_y5_max_value` | 97 |
| 7 | `test_y6_does_not_exist` | 100 |
| 8 | `test_enum_has_exactly_six_members` | 106 |
| 9 | `test_ordering` | 109 |
| 10 | `test_is_int_enum` | 119 |

#### Class: `TestConstants` (line 129)

| # | Method | Line |
|---|---|---|
| 1 | `test_permanent_baseline_is_y4` | 132 |
| 2 | `test_absolute_ceiling_is_y5` | 135 |

#### Class: `TestCanEscalate` (line 144)

| # | Method | Line | Decorators |
|---|---|---|---|
| 1 | `test_can_escalate_below_ceiling` | 157 | `@pytest.mark.parametrize` (5 cases) |
| 2 | `test_cannot_escalate_at_y5` | 160 | |
| 3 | `test_safe_mode_blocks_escalation` | 163 | |
| 4 | `test_distress_blocks_escalation` | 166 | |
| 5 | `test_crisis_blocks_escalation` | 169 | |
| 6 | `test_all_flags_block_escalation` | 172 | |
| 7 | `test_safe_mode_blocks_even_below_ceiling` | 183 | |
| 8 | `test_no_flags_allows_escalation` | 186 | |

#### Class: `TestGetEffectiveLevel` (line 195)

| # | Method | Line |
|---|---|---|
| 1 | `test_normal_returns_requested` | 198 |
| 2 | `test_normal_returns_y0` | 201 |
| 3 | `test_safe_mode_forces_y0` | 204 |
| 4 | `test_distress_forces_y0` | 207 |
| 5 | `test_crisis_forces_y0` | 210 |
| 6 | `test_all_flags_force_y0` | 213 |
| 7 | `test_y0_with_no_flags` | 222 |
| 8 | `test_y4_with_no_flags` | 225 |
| 9 | `test_y5_with_no_flags` | 228 |

#### Class: `TestValidateLevel` (line 237)

| # | Method | Line | Decorators |
|---|---|---|---|
| 1 | `test_valid_levels` | 241 | `@pytest.mark.parametrize` (6 cases) |
| 2 | `test_y6_raises_safety_error` | 246 | |
| 3 | `test_high_than_y6_raises_safety_error` | 250 | |
| 4 | `test_negative_raises_transition_error` | 254 | |
| 5 | `test_large_negative_raises_transition_error` | 258 | |

#### Class: `TestExceptionHierarchy` (line 268)

| # | Method | Line |
|---|---|---|
| 1 | `test_safety_error_is_yandere_error` | 271 |
| 2 | `test_transition_error_is_yandere_error` | 274 |
| 3 | `test_yandere_error_is_exception` | 277 |

#### Class: `TestYandereEngineInit` (line 286)

| # | Method | Line |
|---|---|---|
| 1 | `test_default_baseline_is_y4` | 289 |
| 2 | `test_default_current_level_is_baseline` | 292 |
| 3 | `test_custom_baseline` | 295 |

#### Class: `TestYandereEngineEscalate` (line 306)

| # | Method | Line |
|---|---|---|
| 1 | `test_escalate_from_y0_to_y1` | 309 |
| 2 | `test_escalate_from_y4_to_y5` | 314 |
| 3 | `test_escalate_from_y5_blocked` | 319 |
| 4 | `test_escalate_with_safe_mode_blocked` | 324 |
| 5 | `test_escalate_with_distress_blocked` | 330 |
| 6 | `test_escalate_with_crisis_blocked` | 335 |
| 7 | `test_sequential_escalations` | 340 |
| 8 | `test_escalate_past_y5_stops_at_y5` | 352 |

#### Class: `TestYandereEngineDeEscalate` (line 364)

| # | Method | Line |
|---|---|---|
| 1 | `test_de_escalate_from_y4_to_y3` | 367 |
| 2 | `test_de_escalate_from_y0_stays_y0` | 372 |
| 3 | `test_de_escalate_from_y5_to_y4` | 377 |
| 4 | `test_sequential_de_escalations` | 381 |

#### Class: `TestYandereEngineEffectiveLevel` (line 399)

| # | Method | Line |
|---|---|---|
| 1 | `test_effective_level_normal` | 402 |
| 2 | `test_effective_level_safe_mode` | 405 |
| 3 | `test_effective_level_distress` | 408 |
| 4 | `test_effective_level_crisis` | 411 |

#### Class: `TestYandereEngineReset` (line 420)

| # | Method | Line |
|---|---|---|
| 1 | `test_reset_from_y0` | 423 |
| 2 | `test_reset_from_y5` | 428 |
| 3 | `test_reset_already_at_baseline` | 433 |

#### Class: `TestYandereEngineSetLevel` (line 444)

| # | Method | Line |
|---|---|---|
| 1 | `test_set_valid_level` | 447 |
| 2 | `test_set_level_from_int` | 452 |
| 3 | `test_set_level_y6_raises` | 456 |
| 4 | `test_set_level_negative_raises` | 460 |
| 5 | `test_set_level_y5` | 464 |
| 6 | `test_set_level_y0` | 468 |

#### Class: `TestYandereEngineHardStopIntegration` (line 478)

| # | Method | Line |
|---|---|---|
| 1 | `test_handler_safe_mode_blocks_escalation` | 481 |
| 2 | `test_handler_normal_allows_escalation` | 490 |
| 3 | `test_handler_safe_forces_effective_y0` | 498 |
| 4 | `test_handler_normal_returns_real_effective` | 505 |
| 5 | `test_explicit_safe_mode_overrides_handler` | 512 |
| 6 | `test_no_handler_defaults_to_not_safe` | 522 |

---

## File 4: `test_transition_rules.py`

**Path:** `C:\Users\faizz\guinevere\tests\persona\test_transition_rules.py`
**Lines:** 610
**Docstring:** P4-003: Mood Transition Rules with Cooldowns — Comprehensive Tests
**Imports from:** `persona.transition_rules`

### Summary

| Metric | Count |
|---|---|
| Test classes | 12 |
| Test methods | 42 |
| `@pytest.mark.parametrize` | 8 |
| `assert` statements | 68 |
| Fixtures defined | 2 |

### Fixtures Defined

| Fixture | Line | Description |
|---|---|---|
| `engine` | 38 | Default TransitionRuleEngine with 300s cooldown |
| `custom_engine` | 44 | Engine with custom 60s cooldown |

### Helper Functions (non-test)

| Function | Line | Purpose |
|---|---|---|
| `_ctx()` | 49 | Helper to build TransitionContext with defaults |

### Parametrize Decorators

| # | Method | Params | Cases | Coverage |
|---|---|---|---|---|
| 1 | `test_valid_transition_allowed` | current, target | 9 | All VALID_TRANSITIONS |
| 2 | `test_invalid_transition_blocked` | current, target | 12 | Invalid pairs + self-transitions |
| 3 | `test_forced_bypasses_cooldown` | current, target | 2 | Angry->Silent, Content->Pleased |
| 4 | `test_safe_mode_blocks_all` | current, target | 9 | All valid transitions |
| 5 | `test_distress_blocks` | level | 3 | [2, 3, 4] |
| 6 | `test_distress_below_d2_allows` | level | 2 | [0, 1] |
| 7 | `test_ambiguous_sentiment_triggers_llm` | sentiment | 5 | [-0.3, -0.15, 0.0, 0.15, 0.3] |
| 8 | `test_clear_sentiment_no_llm_without_extra_signals` | sentiment | 6 | [-1.0, -0.5, -0.31, 0.31, 0.5, 1.0] |

### Classes and Methods

#### Class: `TestValidTransitions` (line 74)

| # | Method | Line | Decorators |
|---|---|---|---|
| 1 | `test_valid_transition_allowed` | 82 | `@parametrize` (9 cases) |
| 2 | `test_all_moods_covered` | 95 | |

#### Class: `TestInvalidTransitions` (line 121)

| # | Method | Line | Decorators |
|---|---|---|---|
| 1 | `test_invalid_transition_blocked` | 129 | `@parametrize` (12 cases) |
| 2 | `test_unknown_source_mood` | 140 | |

#### Class: `TestCooldown` (line 153)

| # | Method | Line |
|---|---|---|
| 1 | `test_cooldown_blocks_within_window` | 156 |
| 2 | `test_cooldown_blocks_at_299s` | 165 |
| 3 | `test_cooldown_allows_at_boundary` | 174 |
| 4 | `test_cooldown_allows_after_window` | 182 |
| 5 | `test_no_previous_transition` | 189 |
| 6 | `test_custom_cooldown` | 195 |

#### Class: `TestForcedTransitions` (line 214)

| # | Method | Line | Decorators |
|---|---|---|---|
| 1 | `test_forced_bypasses_cooldown` | 225 | `@parametrize` (2 cases) |
| 2 | `test_forced_still_blocked_by_safe_mode` | 238 | |
| 3 | `test_forced_still_blocked_by_distress` | 251 | |

#### Class: `TestSafeMode` (line 270)

| # | Method | Line | Decorators |
|---|---|---|---|
| 1 | `test_safe_mode_blocks_all` | 278 | `@parametrize` (9 cases) |
| 2 | `test_safe_mode_overrides_distress` | 294 | |

#### Class: `TestDistressLevel` (line 313)

| # | Method | Line | Decorators |
|---|---|---|---|
| 1 | `test_distress_blocks` | 317 | `@parametrize` (3 cases) |
| 2 | `test_distress_below_d2_allows` | 334 | `@parametrize` (2 cases) |

#### Class: `TestRemainingCooldown` (line 354)

| # | Method | Line |
|---|---|---|
| 1 | `test_no_previous_transition` | 357 |
| 2 | `test_just_transitioned` | 360 |
| 3 | `test_halfway` | 364 |
| 4 | `test_exactly_at_cooldown` | 368 |
| 5 | `test_past_cooldown` | 372 |
| 6 | `test_custom_cooldown_value` | 376 |
| 7 | `test_default_now_uses_utc` | 380 |

#### Class: `TestShouldUseLlmEvaluation` (line 397)

| # | Method | Line | Decorators |
|---|---|---|---|
| 1 | `test_ambiguous_sentiment_triggers_llm` | 404 | `@parametrize` (5 cases) |
| 2 | `test_clear_sentiment_no_llm_without_extra_signals` | 418 | `@parametrize` (6 cases) |
| 3 | `test_multiple_signals_task_and_sentiment` | 432 | |
| 4 | `test_multiple_signals_ignored_and_sentiment` | 443 | |
| 5 | `test_multiple_signals_task_and_ignored` | 454 | |
| 6 | `test_single_signal_no_llm` | 466 | |
| 7 | `test_zero_everything_no_llm` | 478 | |

#### Class: `TestEvaluateWithLlm` (line 495)

| # | Method | Line |
|---|---|---|
| 1 | `test_stub_returns_same_as_evaluate_allowed` | 498 |
| 2 | `test_stub_returns_same_as_evaluate_blocked` | 508 |
| 3 | `test_stub_respects_safe_mode` | 518 |

#### Class: `TestExceptionHierarchy` (line 536)

| # | Method | Line |
|---|---|---|
| 1 | `test_cooldown_active_is_transition_rules_error` | 539 |
| 2 | `test_invalid_transition_is_transition_rules_error` | 542 |
| 3 | `test_transition_rules_is_exception` | 545 |

#### Class: `TestDecisionDefaults` (line 554)

| # | Method | Line |
|---|---|---|
| 1 | `test_default_cooldown_zero` | 557 |
| 2 | `test_default_blocked_by_none` | 563 |

#### Class: `TestCheckOrder` (line 575)

| # | Method | Line |
|---|---|---|
| 1 | `test_safe_mode_before_distress` | 578 |
| 2 | `test_distress_before_invalid` | 590 |
| 3 | `test_invalid_before_cooldown` | 601 |

---

## File 5: `test_drift_detector.py`

**Path:** `C:\Users\faizz\guinevere\tests\persona\test_drift_detector.py`
**Lines:** 412
**Docstring:** Comprehensive tests for persona drift detection module
**Imports from:** `persona.drift_detector`

### Summary

| Metric | Count |
|---|---|
| Test classes | 9 |
| Test methods | 34 |
| `@pytest.mark.parametrize` | 2 |
| `assert` statements | 44 |
| Fixtures defined | 3 |

### Fixtures Defined

| Fixture | Line | Description |
|---|---|---|
| `baseline` | 47 | Standard test DriftBaseline |
| `detector` | 58 | DriftDetector with default threshold |
| `low_threshold_detector` | 64 | DriftDetector with threshold=0.05 |

### Parametrize Decorators

| # | Method | Parameters | Test Cases |
|---|---|---|---|
| 1 | `test_known_scores` | `current_hash, expected_score` (2 params) | 4 cases (exact, alert-range, rollback-range, minor-drift) |
| 2 | `test_action_spectrum` | `current_hash, expected_action, expected_drift` (3 params) | 5 cases |

### Classes and Methods

#### Class: `TestComputePromptHash` (line 74)

| # | Method | Line |
|---|---|---|
| 1 | `test_produces_valid_sha256_hex` | 77 |
| 2 | `test_deterministic` | 83 |
| 3 | `test_known_value` | 91 |
| 4 | `test_empty_text_raises` | 99 |

#### Class: `TestComputeDriftScore` (line 109)

| # | Method | Line | Decorators |
|---|---|---|---|
| 1 | `test_exact_match_returns_zero` | 112 | |
| 2 | `test_different_hash_returns_positive` | 115 | |
| 3 | `test_different_length_returns_one` | 119 | |
| 4 | `test_known_scores` | 132 | `@parametrize` (4 cases) |
| 5 | `test_empty_current_hash_raises` | 142 | |

#### Class: `TestDetect` (line 152)

| # | Method | Line |
|---|---|---|
| 1 | `test_none_when_exact_match` | 155 |
| 2 | `test_none_when_minor_drift` | 161 |
| 3 | `test_alert_for_moderate_drift` | 167 |
| 4 | `test_rollback_for_severe_drift` | 173 |
| 5 | `test_detect_populates_result_fields` | 179 |
| 6 | `test_detect_uses_utc_now_when_no_timestamp` | 188 |

#### Class: `TestThresholdConfiguration` (line 202)

| # | Method | Line |
|---|---|---|
| 1 | `test_default_threshold` | 205 |
| 2 | `test_custom_threshold` | 208 |
| 3 | `test_low_threshold_changes_action` | 212 |
| 4 | `test_low_threshold_alert_boundary` | 219 |
| 5 | `test_invalid_threshold_zero_raises` | 226 |
| 6 | `test_invalid_threshold_negative_raises` | 230 |
| 7 | `test_invalid_threshold_above_one_raises` | 236 |
| 8 | `test_threshold_one_is_valid` | 242 |

#### Class: `TestUpdateBaseline` (line 252)

| # | Method | Line |
|---|---|---|
| 1 | `test_update_changes_reference` | 255 |
| 2 | `test_update_affects_subsequent_detection` | 267 |
| 3 | `test_update_empty_hash_raises` | 283 |

#### Class: `TestCheckCountAndLastResult` (line 298)

| # | Method | Line |
|---|---|---|
| 1 | `test_initial_check_count_zero` | 301 |
| 2 | `test_initial_last_result_none` | 304 |
| 3 | `test_check_count_increments` | 307 |
| 4 | `test_last_result_updates` | 315 |

#### Class: `TestFrozenDataclasses` (line 334)

| # | Method | Line |
|---|---|---|
| 1 | `test_drift_baseline_is_frozen` | 337 |
| 2 | `test_drift_result_is_frozen` | 346 |

#### Class: `TestConstructorValidation` (line 365)

| # | Method | Line |
|---|---|---|
| 1 | `test_empty_baseline_hash_raises` | 368 |

#### Class: `TestEndToEndScenarios` (line 383)

| # | Method | Line | Decorators |
|---|---|---|---|
| 1 | `test_action_spectrum` | 403 | `@parametrize` (5 cases) |

---

## File 6: `test_drift_corrector.py`

**Path:** `C:\Users\faizz\guinevere\tests\persona\test_drift_corrector.py`
**Lines:** 818
**Docstring:** P4-015: Drift Correction Auto-Rollback — deterministic unit tests
**Imports from:** `persona.drift_corrector`, `persona.drift_detector`, `persona.safe_mode`

### Summary

| Metric | Count |
|---|---|
| Test classes | 11 |
| Test methods | 43 |
| `@pytest.mark.parametrize` | 1 |
| `assert` statements | 89 |
| Fixtures defined | 7 |
| Async methods (`@pytest.mark.asyncio`) | 30 |

### Fixtures Defined

| Fixture | Line | Description |
|---|---|---|
| `baseline` | 129 | Standard test DriftBaseline |
| `detector` | 140 | DriftDetector with default threshold (0.10) |
| `corrector` | 146 | DriftCorrector without safe_mode controller |
| `safe_controller` | 152 | SafeModeController in non-active state |
| `corrector_with_safe_mode` | 158 | DriftCorrector with safe_mode controller (inactive) |
| `active_safe_mode_controller` | 167 | SafeModeController with safe_mode already active |
| `corrector_active_safe_mode` | 184 | DriftCorrector with safe_mode already active |

### Fake DB Infrastructure (non-test helpers)

| Class | Line | Purpose |
|---|---|---|
| `FakeResult` | 39 | Mimics SQLAlchemy Result |
| `FakeAsyncSession` | 52 | Deterministic fake AsyncSession |
| `FailingAsyncSession` | 79 | Session that raises on commit AND rollback (double failure) |

### Parametrize Decorators

| # | Method | Parameters | Test Cases |
|---|---|---|---|
| 1 | `test_action_spectrum` | `current_hash, expected_action, expected_drift, expected_rollback` (4 params) | 5 cases |

### Classes and Methods

#### Class: `TestDriftCorrectionResult` (line 200)
*Tests for DriftCorrectionResult frozen dataclass.*

| # | Method | Line |
|---|---|---|
| 1 | `test_construction` | 203 |
| 2 | `test_frozen_enforcement` | 218 |
| 3 | `test_action_none` | 230 |
| 4 | `test_action_alert` | 240 |

#### Class: `TestRollbackResult` (line 256)
*Tests for RollbackResult frozen dataclass.*

| # | Method | Line |
|---|---|---|
| 1 | `test_construction` | 259 |
| 2 | `test_frozen_enforcement` | 271 |

#### Class: `TestErrorHierarchy` (line 287)

| # | Method | Line |
|---|---|---|
| 1 | `test_drift_correction_error_is_exception` | 290 |
| 2 | `test_rollback_error_is_drift_correction_error` | 293 |
| 3 | `test_rollback_error_catchable_as_base` | 296 |

#### Class: `TestEvaluateNoDrift` (line 306)

| # | Method | Line | Async |
|---|---|---|---|
| 1 | `test_exact_match` | 310 | Yes |
| 2 | `test_minor_drift_within_threshold` | 320 | Yes |
| 3 | `test_no_drift_reason_message` | 332 | Yes |
| 4 | `test_no_drift_creates_drift_log` | 341 | Yes |
| 5 | `test_no_drift_increments_detector_count` | 351 | Yes |

#### Class: `TestEvaluateDriftDetected` (line 366)

| # | Method | Line | Async |
|---|---|---|---|
| 1 | `test_alert_range_triggers_auto_rollback` | 370 | Yes |
| 2 | `test_severe_drift_triggers_auto_rollback` | 382 | Yes |
| 3 | `test_length_mismatch_triggers_auto_rollback` | 393 | Yes |
| 4 | `test_drift_reason_contains_score` | 405 | Yes |
| 5 | `test_drift_creates_rollback_and_evaluation_logs` | 415 | Yes |

#### Class: `TestEvaluateSafeModeDefer` (line 431)

| # | Method | Line | Async |
|---|---|---|---|
| 1 | `test_safe_mode_active_defers_rollback` | 435 | Yes |
| 2 | `test_safe_mode_defer_reason_mentions_safe_mode` | 452 | Yes |
| 3 | `test_safe_mode_inactive_allows_rollback` | 467 | Yes |
| 4 | `test_safe_mode_no_drift_still_returns_none` | 478 | Yes |
| 5 | `test_safe_mode_defer_creates_evaluation_log_only` | 488 | Yes |

#### Class: `TestRollback` (line 510)

| # | Method | Line | Async |
|---|---|---|---|
| 1 | `test_rollback_success` | 514 | Yes |
| 2 | `test_rollback_restored_hash_is_baseline` | 527 | Yes |
| 3 | `test_rollback_previous_hash_from_last_result` | 537 | Yes |
| 4 | `test_rollback_no_previous_detection` | 547 | Yes |
| 5 | `test_rollback_creates_drift_log` | 557 | Yes |
| 6 | `test_rollback_with_safe_mode_defers` | 568 | Yes |
| 7 | `test_rollback_commit_failure_raises_rollback_error` | 585 | Yes |
| 8 | `test_rollback_timestamp_is_utc` | 597 | Yes |
| 9 | `test_rollback_double_failure_raises` | 607 | Yes |

#### Class: `TestCreateDriftLog` (line 622)

| # | Method | Line | Async |
|---|---|---|---|
| 1 | `test_creates_drift_log_entry` | 626 | Yes |
| 2 | `test_drift_log_fields_populated` | 648 | Yes |
| 3 | `test_drift_log_rollback_available_false_for_none` | 676 | Yes |
| 4 | `test_drift_log_commit_failure_raises` | 696 | Yes |
| 5 | `test_drift_log_double_failure_still_raises` | 718 | Yes |

#### Class: `TestDriftCorrectorConstruction` (line 743)

| # | Method | Line |
|---|---|---|
| 1 | `test_constructor_without_safe_mode` | 746 |
| 2 | `test_constructor_with_safe_mode` | 751 |

#### Class: `TestDriftThresholdConstant` (line 769)

| # | Method | Line |
|---|---|---|
| 1 | `test_threshold_value` | 772 |
| 2 | `test_threshold_matches_detector_default` | 775 |

#### Class: `TestEndToEndScenarios` (line 785)

| # | Method | Line | Decorators |
|---|---|---|---|
| 1 | `test_action_spectrum` | 806 | `@parametrize` (5 cases) + `@pytest.mark.asyncio` |

---

## Cross-File Summary Table

| File | Classes | Methods | Parametrize | Asserts | Fixtures | Async |
|---|---|---|---|---|---|---|
| `test_mood_engine.py` | 7 | 49 | 2 | 70 | 1 | 0 |
| `test_mood_persistence.py` | 7 | 26 | 0 | 68 | 4 | 26 |
| `test_yandere_fsm.py` | 13 | 71 | 2 | 78 | 4 | 0 |
| `test_transition_rules.py` | 12 | 42 | 8 | 68 | 2 | 0 |
| `test_drift_detector.py` | 9 | 34 | 2 | 44 | 3 | 0 |
| `test_drift_corrector.py` | 11 | 43 | 1 | 89 | 7 | 30 |
| **TOTAL** | **59** | **265** | **15** | **417** | **21** | **56** |

---

## Assertion Counting Methodology

1. **Explicit `assert` statements only.** `pytest.raises()` context managers are NOT counted as assertions — they are exception-expectation decorators.
2. **Method counting:** Each `def test_*` method is counted once regardless of parametrize expansion. Parametrized methods generate multiple test cases at runtime.
3. **Effective test case count:** With parametrize expansion, the actual number of test cases at runtime is significantly higher than 265. Estimated effective count: ~340+ test cases (265 base methods + ~75 additional parametrized cases).
4. **Import paths vary:** `test_mood_engine.py` and `test_mood_persistence.py` import from `src.persona.*` while the other four files import from `persona.*` directly. This may indicate inconsistent package configuration or dual-path imports.
5. **No `@pytest.mark.skip` or `@pytest.mark.xfail` decorators** were found in any of the 6 files.
6. **All 6 files are 100% deterministic** — no network calls, no LLM invocations, no real DB connections. Time-dependent tests use injected `now` parameters or fixed constants.
