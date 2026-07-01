# STEP-P18-002 — FSRS-6 Spaced Repetition + 6h Consolidation Cycle + Active Forgetting — Verification

**Date:** 2026-06-19
**Task:** P18-002
**Status:** PASS
**Operator:** Guinevere (autonomous) for Faiz

---

## 1. What Was Done

Added the **FSRS-6 spaced repetition scheduler** wrapper and **6-hourly decay sweep**
job to the memory consolidation pipeline. The FSRS wrapper is optional: when the
`fsrs>=5.0.0` library is not installed, every public method returns a no-op result
and the caller treats the call as best-effort. The active-forgetting policy is
metadata-only (`deletion_state='archived'`); no episodes are hard-deleted.

### Files Created

| Path | Purpose |
|---|---|
| `src/memory/spaced_repetition.py` | New module: `FSRSScheduler` wrapper, `FSRSReviewResult` dataclass, `GRADE_*` constants, closed-form retrievability fallback. |
| `docs/setup-evidence/P18/evidence/STEP-P18-002/verification.md` | This file. |

### Files Modified

| Path | Change |
|---|---|
| `src/memory/consolidation.py` | (a) Added `DECAY_SWEEP_*` and `ACTIVE_FORGETTING_*` constants after `CONSOLIDATION_MINUTE`. (b) Added `fsrs_enabled: bool = True` parameter to `consolidate_episodes_to_facts()` and a post-loop FSRS review hook. (c) Added `DecaySweepResult`, `decay_sweep_job()`, and `register_decay_job()` at the end of the file. |
| `pyproject.toml` | Added `"fsrs>=5.0.0"` to the `dependencies` list. |
| `src/memory/__init__.py` | Added import block from `src.memory.spaced_repetition` and appended 7 names to `__all__`. |

---

## 2. Files Changed (final layout)

### `src/memory/spaced_repetition.py` (new file, ~500 lines)

- Module docstring documents FSRS-6 rationale and benchmark sources.
- Constants: `GRADE_AGAIN=1`, `GRADE_HARD=2`, `GRADE_GOOD=3`, `GRADE_EASY=4`, `DEFAULT_REQUEST_RETENTION=0.9`, `FSRS_STATE_NEW=0`, `FSRS_STATE_LEARNING=1`, `FSRS_STATE_REVIEW=2`, `FSRS_STATE_RELEARNING=3`.
- `FSRSReviewResult` dataclass: `stability`, `difficulty`, `elapsed_days`, `scheduled_days`, `reps`, `lapses`, `state`, `last_review`, `next_review`. Has `to_dict()` (JSONB-safe) and `no_op()` classmethod.
- `FSRSScheduler` class: lazy-imports `fsrs` on `__init__`. Methods: `schedule_review()`, `predict_retrievability()`, `get_next_review()`, `update_episode_state()`. All methods degrade to no-op when `fsrs` is unavailable.
- Private helpers: `_to_card()`, `_coerce_state()`, `_retrievability_formula()`, `_init_backend()`.

### `src/memory/consolidation.py` — delta

#### New constants (inserted after `CONSOLIDATION_MINUTE = 0`)

```python
DECAY_SWEEP_JOB_ID = "decay_sweep"
DECAY_SWEEP_HOUR = 0
DECAY_SWEEP_MINUTE = 0
DECAY_SWEEP_INTERVAL_HOURS = 6
ACTIVE_FORGETTING_THRESHOLD = 0.1
ACTIVE_FORGETTING_GRACE_DAYS = 90
ACTIVE_FORGETTING_DEFAULT_MODE = "archive"
```

#### `consolidate_episodes_to_facts()` signature change

```python
async def consolidate_episodes_to_facts(
    session: AsyncSessionProtocol,
    *,
    watermark: datetime | None = None,
    now: datetime | None = None,
    kg_ingestion_enabled: bool = True,
    fsrs_enabled: bool = True,          # <-- NEW
) -> ConsolidationResult:
```

#### Post-loop FSRS review hook (inserted before the P16 KG ingestion block)

Mirrors the `kg_ingestion_enabled` pattern: lazy-import `FSRSScheduler`, iterate
`consolidated_episodes`, call `update_episode_state()` with `grade=GRADE_GOOD`,
log metadata only, never fail consolidation.

#### New types and functions (appended at end of file)

- `DecaySweepResult` class: `episodes_reviewed`, `episodes_archived`, `errors`, `to_dict()`.
- `async def decay_sweep_job(session_factory, fsrs_enabled=True) -> DecaySweepResult`:
  queries all non-DNR episodes, runs FSRS review on due episodes, archives episodes
  with `retrievability < 0.1` and `age > 90 days`. Non-breaking: returns empty
  result when `session_factory is None` or `fsrs` is unavailable.
- `async def register_decay_job(scheduler, session_factory) -> None`: registers
  the decay sweep on APScheduler v3 with `trigger='interval'`, `hours=6`,
  `replace_existing=True`, `misfire_grace_time=1800`.

### `pyproject.toml` — delta

Added `"fsrs>=5.0.0"` after `"mcp>=1.0"` in the `dependencies` list.

### `src/memory/__init__.py` — delta

Added import block from `src.memory.spaced_repetition` and appended to `__all__`:
`"FSRSScheduler"`, `"FSRSReviewResult"`, `"GRADE_AGAIN"`, `"GRADE_HARD"`,
`"GRADE_GOOD"`, `"GRADE_EASY"`, `"DEFAULT_REQUEST_RETENTION"`.

---

## 3. Validation Results

### 3.1 Syntax compile

| Check | Command | Result |
|---|---|---|
| spaced_repetition.py | `python -c "import py_compile; py_compile.compile('src/memory/spaced_repetition.py', doraise=True)"` | OK (exit 0) |
| consolidation.py | `python -c "import py_compile; py_compile.compile('src/memory/consolidation.py', doraise=True)"` | OK (exit 0) |
| __init__.py | `python -c "import py_compile; py_compile.compile('src/memory/__init__.py', doraise=True)"` | OK (exit 0) |

### 3.2 Pattern checks

| Check | Pattern | Result |
|---|---|---|
| Type suppression in spaced_repetition.py | `as any\|@ts-ignore\|# type: ignore` | count=0 (expected 0) |
| Bare except in spaced_repetition.py | `^\s*except:\s*$` | 0 (expected 0) |
| Bare except in consolidation.py | `^\s*except:\s*$` | 0 (expected 0) |
| fsrs dependency in pyproject.toml | `fsrs>=5\.0\.0` | PASS |

### 3.3 Runtime smoke tests (without `fsrs` package installed)

| Check | Output |
|---|---|
| FSRSScheduler no-op fallback | `available=False`; `schedule_review(None, GOOD)` returns `stability=0.0, difficulty=0.0, state=0`; `predict_retrievability({S:5,D:2.5}, t=10)` returns `0 < R < 1`; invalid grade `99` raises `ValueError`. |
| Consolidation module imports | `DECAY_SWEEP_JOB_ID='decay_sweep'`, `DECAY_SWEEP_INTERVAL_HOURS=6`, `ACTIVE_FORGETTING_THRESHOLD=0.1`, `ACTIVE_FORGETTING_GRACE_DAYS=90`, `ACTIVE_FORGETTING_DEFAULT_MODE='archive'`; `DecaySweepResult()` defaults to zeros. |
| `src.memory.__init__` exports | All 7 FSRS names present in both `hasattr(mem, name)` and `mem.__all__`. |
| `consolidate_episodes_to_facts` signature | `fsrs_enabled` and `kg_ingestion_enabled` both present as keyword-only parameters. |

---

## 4. Evidence Artifacts

| Artifact | Path |
|---|---|
| Verification report | `docs/setup-evidence/P18/evidence/STEP-P18-002/verification.md` (this file) |
| FSRS wrapper module | `src/memory/spaced_repetition.py` |
| Consolidation delta | `src/memory/consolidation.py` |
| Package dependency | `pyproject.toml` |
| Package exports | `src/memory/__init__.py` |

---

## 5. Doc-Sync Impact

No doc changes required for this step. The Memory Schema doc
(`docs/00-core/04-MemorySchema_v2.0.md`) and the Memory Tier deep-dive doc (if it
exists under `docs/30-data/`) will reference the FSRS scheduler and decay sweep in
a later P18 step. This step is pure code + dependency addition.

---

## 6. Boundary Compliance

- **No secrets committed.** No credentials, tokens, or decrypted values in any changed file.
- **No surveillance data in artifacts.** FSRS wrapper contains only algorithm logic; decay sweep logs metadata (counts, errors) only.
- **No persona/consent/safety boundary changes.** All P18 work is on memory tier storage and recall scheduling, separate from persona state.
- **No destructive ops executed.** No database migrations run; no production deploy.
- **No raw memory content logged.** `spaced_repetition.py` and `consolidation.py` log only metadata: counts, error types, job IDs, interval hours.
- **Active forgetting is non-destructive.** Default mode is `archive` (sets `deletion_state='archived'`), never hard-deletes episodes. Grace period of 90 days prevents premature archival.

---

## 7. Rollback / Re-run Safety

- **`spaced_repetition.py` is fully re-importable.** No module-level side effects beyond class and constant definitions.
- **`consolidation.py` changes are additive.** New constants, new parameter (with default), new functions appended at end. No existing function signatures were modified (only `consolidate_episodes_to_facts` gained an optional keyword argument with a backward-compatible default).
- **`pyproject.toml` change is additive.** Removing `"fsrs>=5.0.0"` from dependencies reverts to pre-P18-002 state.
- **No database connectivity required at import time.** The `FSRSScheduler` lazy-imports `fsrs` on construction; the decay sweep job only queries the DB when a `session_factory` is provided.

---

## 8. Design Decisions / Caveats

1. **FSRS-6 chosen per benchmark.** See `research-reports/p18-fsrs-vs-sm2-benchmark.md`.
   FSRS-6 cuts log-loss ~34% vs Anki SM-2 on the 350M-review benchmark; 99.6%
   pairwise win rate; ~20–30% fewer reviews at matched retention.

2. **6-hour consolidation cycle chosen per benchmark.** See
   `research-reports/p18-consolidation-forgetting-benchmark.md`. 6h matches
   biologically-motivated multi-period architecture (4× ultradian cycles);
   documented in Human-Inspired Memory Architecture implementations. The daily
   03:00 ICT consolidation continues to run unchanged — the decay sweep is
   **additional**.

3. **Active forgetting threshold = 0.1.** Matches the Mem0 default search
   threshold and the Ebbinghaus near-zero retention floor. Combined with a
   90-day grace period to protect recently-distilled facts.

4. **Lazy-import pattern.** `FSRSScheduler` uses `try: import fsrs` on
   `__init__`, falling back to a no-op scheduler if unavailable. This allows
   the module to be imported and tested without `fsrs` installed.

5. **`fsrs_enabled` parameter on `consolidate_episodes_to_facts()`.** Added
   alongside the existing `kg_ingestion_enabled` with the same pattern:
   `try/except ImportError/except Exception`, log metadata, never fail
   consolidation.

6. **Decay sweep uses `interval` trigger, not `cron`.** The task spec allowed
   either; `interval` with `hours=6` is simpler and avoids cron expression
   fragility. The `DECAY_SWEEP_HOUR` and `DECAY_SWEEP_MINUTE` constants are
   retained for documentation and potential future cron migration.

7. **`schedule_review()` raises `ValueError` on invalid grade.** The no-op
   fallback only triggers when `fsrs` is unavailable or the call itself fails;
   programming errors (wrong grade value) are surfaced immediately.

8. **`predict_retrievability()` uses closed-form formula as fallback.**
   `R(t) = (1 + t/(9*S))^(-D)`. When the library is unavailable or
   `get_card_retrievability` raises, the formula is used directly.

---

## 9. Auditor Gate

Auditor gate is deferred to the parent verification wave per AGENTS.md §2.10.
No implementation sub-agent was used for this step — the changes are tightly
scoped (1 new module, 3 modified files) and the parent session read every
changed file plus ran runtime smoke tests.

---

## 10. Acceptance Criteria Mapping

| Criterion | Status | Evidence |
|---|---|---|
| `spaced_repetition.py` exists with `FSRSScheduler` class | PASS | §3.3 smoke test |
| `consolidation.py` has `decay_sweep_job()`, `register_decay_job()`, `fsrs_enabled` param | PASS | §3.3 signature + module imports |
| `pyproject.toml` has `fsrs>=5.0.0` in dependencies | PASS | §3.2 grep check |
| `__init__.py` exports FSRSScheduler, FSRSReviewResult, GRADE_* constants | PASS | §3.3 export check |
| `py_compile` passes on all 3 Python files | PASS | §3.1 |
| No type suppression patterns (`as any`, `@ts-ignore`, `# type: ignore`) | PASS | §3.2 count=0 |
| No bare `except:` blocks | PASS | §3.2 count=0/0 |
| FSRS wrapper degrades gracefully when `fsrs` package not installed | PASS | §3.3 no-op smoke test |
| Active forgetting never hard-deletes (archive mode only) | PASS | §6 + code review of `decay_sweep_job` |

---

## 11. Final Status

**PASS** — Ready for downstream P18 steps (recall pipeline integration,
FSRS parameter tuning, decay-aware scoring). The `fsrs>=5.0.0` dependency has
been added but **not installed** in the current environment. User must run
`pip install fsrs>=5.0.0` (or `uv pip install fsrs>=5.0.0`) as a separate,
explicitly approved step before FSRS scheduling becomes active. The decay sweep
job has not been registered on any running APScheduler instance.