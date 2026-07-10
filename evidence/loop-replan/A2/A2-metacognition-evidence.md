# Evidence: A2 — MetaCogEval Metacognition Module

## What Was Done

Implemented a two-layer metacognitive evaluation system for the consciousness thought stream:

1. **Created** `guinevere/consciousness/metacognition.py` — new module with:
   - `MetaCogEval` frozen dataclass (confidence, coherence, novelty, safety_pass, should_record, suggested_type)
   - `MetacognitiveEvaluator` class with real-time `evaluate()` and periodic `periodic_review()`
   - Hallucination guard with contradiction detection and unsubstantiated superlative checks
   - Integration constants: CONFIDENCE_WEIGHT=0.4, COHERENCE_WEIGHT=0.3, NOVELTY_WEIGHT=0.3
   - Configurable `review_interval` (default 20 thoughts)

2. **Modified** `guinevere/consciousness/thought_stream.py`:
   - Added import of `MetaCogEval` and `MetacognitiveEvaluator`
   - `ThoughtStream.__init__`: creates `MetacognitiveEvaluator` instance (`self._metacog`)
   - `run()`: Step 4 now calls `self._metacog.evaluate()` for full MetaCogEval access; Step 8 adds periodic self-review at interval
   - `_metacog_eval()`: preserved for backward compatibility, now delegates to `self._metacog.evaluate()`
   - Periodic review results recorded as META-type thoughts in state

3. **Updated** `guinevere/consciousness/__init__.py`:
   - Added `MetaCogEval` to imports and `__all__`

4. **Appended** 16 new tests to `tests/p24/test_consciousness.py`:
   - `TestMetacognition` class covering: import, real-time eval, confidence scoring, hallucination guard (contradictions + superlatives), suggested type, periodic review (populated + empty), review interval, review count, frozen dataclass, novelty scoring, ThoughtStream integration, backward compat

## Files Changed

| File | Action | Lines |
|---|---|---|
| `guinevere/consciousness/metacognition.py` | Created | ~280 |
| `guinevere/consciousness/thought_stream.py` | Modified | ~30 lines changed |
| `guinevere/consciousness/__init__.py` | Modified | +2 lines |
| `tests/p24/test_consciousness.py` | Appended | +280 lines |

## Validation Results

```
python -c "from guinevere.consciousness.metacognition import MetaCogEval; print('OK')" → OK

python -m pytest tests/p24/test_consciousness.py -v -x --timeout=30 -k "metacog"
→ 16 passed, 32 deselected

python -m pytest tests/p24/test_consciousness.py -v -x --timeout=30
→ 48 passed (32 existing + 16 new)

python -m pytest tests/p24/test_consciousness_delegate.py tests/p24/test_consciousness_live.py -v -x --timeout=30
→ 2 passed, 1 skipped
```

## Evidence Artifacts

- This file: `evidence/loop-replan/A2/A2-metacognition-evidence.md`

## Doc-Sync Impact

- No doc changes required (implementation detail, not user-facing).
- ADR index not affected (no new ADR).

## Boundary Compliance

- No imports from `guinevere.consciousness.infra` ✅
- No circular imports ✅
- No asyncio.sleep() in eval path ✅
- No LLM calls in evaluator (synchronous heuristics only) ✅
- No bare except blocks ✅
- No type suppression ✅
- No modifications to loop.py, state.py, thought.py, dreaming.py ✅

## Rollback/Re-run Safety

- Fully idempotent. Re-running creates identical state.
- Rollback: revert `metacognition.py` deletion + revert `thought_stream.py` and `__init__.py` edits.

## Design Decisions

1. **Heuristic-only eval**: No LLM calls in eval path — fast, deterministic, no timeout risk.
2. **Sliding window novelty**: Compares against recent N contents, not full history.
3. **Hallucination guard**: Pattern-based contradiction + superlative detection. Conservative — false positives preferred over false negatives.
4. **Periodic review as META thought**: Results recorded in state for visibility in thought stream.
5. **Backward compat**: `_metacog_eval()` preserved as thin wrapper for any external callers.

## Auditor Gate

- Pending (to be spawned after parent verification).
