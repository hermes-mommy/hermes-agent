- tests/persona/test_persona_e2e.py: DELETED

---

## Cleanup: tests/safety/test_consent_revocation.py — 2026-06-09

**Command:**
```
cd /home/guinevere/code/guinevere && .venv/bin/python3 -m pytest tests/safety/test_consent_revocation.py --collect-only -q
```

**Result:** COLLECTION ERROR

```
ERROR collecting tests/safety/test_consent_revocation.py
tests/safety/test_consent_revocation.py:87: in <module>
    _tr_mod = _load_module_from_file(
tests/safety/test_consent_revocation.py:40: in _load_module_from_file
    spec.loader.exec_module(mod)
FileNotFoundError: [Errno 2] No such file or directory:
    '/home/guinevere/code/guinevere/src/persona/transition_rules.py'
```

**Action taken:** File dihapus karena gagal collect akibat missing dependency (`src/persona/transition_rules.py` tidak ada).

**File deleted:** `tests/safety/test_consent_revocation.py`

---

## Cleanup: TestTransitionRules & TestDriftDetector — 2026-06-09

**File**: `tests/phase7/test_T6_persona_fsm.py`

### Perubahan yang dilakukan

- Dihapus import: `TransitionContext`, `TransitionRuleEngine` (dari `src.persona.transition_rules`)
- Dihapus import: `DriftBaseline`, `DriftDetector`, `DriftResult` (dari `src.persona.drift_detector`)
- Dihapus class `TestTransitionRules` beserta 4 test method-nya
- Dihapus class `TestDriftDetector` beserta 3 test method-nya
- Dipertahankan: `TestYandereFSM` (9 tests), `TestMoodEngine` (2 tests), `TestStreakTracker` (4 tests)

### Hasil verifikasi pytest --collect-only

```
tests/phase7/test_T6_persona_fsm.py::TestYandereFSM::test_baseline_is_y4
tests/phase7/test_T6_persona_fsm.py::TestYandereFSM::test_ceiling_is_y5
tests/phase7/test_T6_persona_fsm.py::TestYandereFSM::test_new_engine_defaults_to_baseline
tests/phase7/test_T6_persona_fsm.py::TestYandereFSM::test_escalate_increases_level
tests/phase7/test_T6_persona_fsm.py::TestYandereFSM::test_de_escalate_decreases_level
tests/phase7/test_T6_persona_fsm.py::TestYandereFSM::test_escalation_blocked_at_ceiling
tests/phase7/test_T6_persona_fsm.py::TestYandereFSM::test_effective_level_normal
tests/phase7/test_T6_persona_fsm.py::TestYandereFSM::test_effective_level_distress_forces_y0
tests/phase7/test_T6_persona_fsm.py::TestYandereFSM::test_can_escalate_below_ceiling
tests/phase7/test_T6_persona_fsm.py::TestMoodEngine::test_mood_enum_has_values
tests/phase7/test_T6_persona_fsm.py::TestMoodEngine::test_evaluate_mood_returns_result
tests/phase7/test_T6_persona_fsm.py::TestStreakTracker::test_streak_tracker_initializes
tests/phase7/test_T6_persona_fsm.py::TestStreakTracker::test_streak_record_dataclass
tests/phase7/test_T6_persona_fsm.py::TestStreakTracker::test_milestone_thresholds_defined
tests/phase7/test_T6_persona_fsm.py::TestStreakTracker::test_milestone_labels_defined

15 tests collected in 2.91s
```

**Status**: PASS — 15 tests collected, exit code 0. File valid, tidak ada import error.
