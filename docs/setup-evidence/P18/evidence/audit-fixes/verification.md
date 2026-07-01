# P18 Audit Fixes — Verification Report

**Timestamp:** 2026-06-19 21:24 WIB (14:24 UTC)
**Status:** PASS
**Scope:** 2 surgical fixes — no refactoring, no new features, no test/migration changes

---

## FIX 1: `src/memory/__init__.py` — Missing Re-exports

### Change 1.1: Add FSRS state constants to spaced_repetition import block

- **Location:** Lines 99–105 (after `DEFAULT_REQUEST_RETENTION,`)
- **Old:** Block ended with `DEFAULT_REQUEST_RETENTION,` then `)`
- **New:** Added 6 symbols before closing `)`:
  ```python
  # State constants
  VALID_GRADES,
  FSRS_STATE_NEW,
  FSRS_STATE_LEARNING,
  FSRS_STATE_REVIEW,
  FSRS_STATE_RELEARNING,
  ```

### Change 1.2: Add new consolidation import block

- **Location:** Between spaced_repetition and read_pipeline import blocks
- **Old:** No consolidation import block existed
- **New:** Added:
  ```python
  from src.memory.consolidation import (
      # Decay sweep (P18-002)
      DECAY_SWEEP_JOB_ID,
      ACTIVE_FORGETTING_THRESHOLD,
      ACTIVE_FORGETTING_GRACE_DAYS,
      DecaySweepResult,
      register_decay_job,
  )
  ```

### Change 1.3: Add FSRS_WEIGHT to read_pipeline import block

- **Location:** After `BOTH_SIGNAL_BONUS,` in read_pipeline imports
- **Old:** `BOTH_SIGNAL_BONUS,` followed by `RECENCY_MAX_BOOST,`
- **New:** `BOTH_SIGNAL_BONUS,` then `FSRS_WEIGHT,` then `RECENCY_MAX_BOOST,`

### Change 1.4: Add new symbols to `__all__` list

- **Location:** After `"DEFAULT_REQUEST_RETENTION",` (end of `__all__`)
- **Old:** List ended with `"DEFAULT_REQUEST_RETENTION",` then `]`
- **New:** Added 12 new entries before `]`:
  ```python
  "VALID_GRADES",
  "FSRS_STATE_NEW",
  "FSRS_STATE_LEARNING",
  "FSRS_STATE_REVIEW",
  "FSRS_STATE_RELEARNING",
  # FSRS Read Pipeline
  "FSRS_WEIGHT",
  # Decay Sweep (P18-002)
  "DECAY_SWEEP_JOB_ID",
  "ACTIVE_FORGETTING_THRESHOLD",
  "ACTIVE_FORGETTING_GRACE_DAYS",
  "DecaySweepResult",
  "register_decay_job",
  ```

---

## FIX 2: `src/memory/consolidation.py` — Importance Floor for Active Forgetting

### Change 2.1: Add `ACTIVE_FORGETTING_IMPORTANCE_FLOOR` constant

- **Location:** After `ACTIVE_FORGETTING_GRACE_DAYS` docstring (after original line 78)
- **Old:** No importance floor constant
- **New:**
  ```python
  ACTIVE_FORGETTING_IMPORTANCE_FLOOR = 8
  """Episodes with importance >= this value are protected from active forgetting.
  High-importance memories (importance 8-10) represent critical context for Faiz
  and should never be auto-archived regardless of retrievability."""
  ```

### Change 2.2: Add importance check to active forgetting condition

- **Location:** Active forgetting conditional block (originally lines 1028–1033)
- **Old:**
  ```python
  if (
      isinstance(retrievability, (int, float))
      and retrievability < ACTIVE_FORGETTING_THRESHOLD
      and age_days is not None
      and age_days > ACTIVE_FORGETTING_GRACE_DAYS
  ):
  ```
- **New:**
  ```python
  ep_importance = getattr(ep, "importance", None)
  if (
      isinstance(retrievability, (int, float))
      and retrievability < ACTIVE_FORGETTING_THRESHOLD
      and age_days is not None
      and age_days > ACTIVE_FORGETTING_GRACE_DAYS
      and (ep_importance is None or ep_importance < ACTIVE_FORGETTING_IMPORTANCE_FLOOR)
  ):
  ```

---

## Validation Results

| Check | Command | Result |
|---|---|---|
| py_compile __init__.py | `python -m py_compile src/memory/__init__.py` | **exit 0** |
| py_compile consolidation.py | `python -m py_compile src/memory/consolidation.py` | **exit 0** |

---

## Symbol Existence Verification

All re-exported symbols confirmed present in source modules:

| Symbol | Source File | Line |
|---|---|---|
| `VALID_GRADES` | `src/memory/spaced_repetition.py` | 48 |
| `FSRS_STATE_NEW` | `src/memory/spaced_repetition.py` | 53 |
| `FSRS_STATE_LEARNING` | `src/memory/spaced_repetition.py` | 54 |
| `FSRS_STATE_REVIEW` | `src/memory/spaced_repetition.py` | 55 |
| `FSRS_STATE_RELEARNING` | `src/memory/spaced_repetition.py` | 56 |
| `FSRS_WEIGHT` | `src/memory/read_pipeline.py` | 135 |
| `DECAY_SWEEP_JOB_ID` | `src/memory/consolidation.py` | 56 |
| `ACTIVE_FORGETTING_THRESHOLD` | `src/memory/consolidation.py` | 71 |
| `ACTIVE_FORGETTING_GRACE_DAYS` | `src/memory/consolidation.py` | 76 |
| `DecaySweepResult` | `src/memory/consolidation.py` | 898 |
| `register_decay_job` | `src/memory/consolidation.py` | 1080 |

---

## Boundary Compliance

- No persona drift
- No consent violation
- No surveillance overreach
- No safety boundary change
- No secrets exposed
- No refactoring beyond specified scope
- No new dependencies added
- No function signatures changed
