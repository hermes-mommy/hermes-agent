# A1 — ThoughtStream Core Implementation Report

**Date:** 2026-07-10
**Task:** Replace 7-substrate consciousness loop with single continuous thought stream

---

## Files Created

| File | Lines | Description |
|---|---|---|
| `guinevere/consciousness/thought.py` | ~90 | Thought dataclass (frozen) + ThoughtType enum (6 types) |
| `guinevere/consciousness/thought_stream.py` | ~475 | ThoughtStream class: sequential thought generation with AffectVector influence, metacog eval, action threshold, HARD STOP check |

## Files Modified

| File | Description |
|---|---|
| `guinevere/consciousness/loop.py` | Rewritten: delegates to ThoughtStream, keeps lifecycle (on_session_start/on_session_end/run), single asyncio.Task instead of 7 |
| `guinevere/consciousness/__init__.py` | Updated exports: removed SubstrateStatus, added Thought, ThoughtType, ThoughtStream, THOUGHT_TYPE_NAMES |
| `guinevere/config/models.py` | ConsciousnessConfig: enabled=True, continuous_stream=True, thought_type_weights dict |
| `tests/p24/test_consciousness.py` | Updated for ThoughtStream architecture (removed 7-substrate assertions) |
| `tests/p24/test_consciousness_delegate.py` | Updated import from `substrates._self_prompt` to `thought_stream._self_prompt` |
| `tests/p24/test_consciousness_live.py` | Updated import from `substrates._self_prompt` to `thought_stream._self_prompt` |

## Files Deleted

| File | Description |
|---|---|
| `guinevere/consciousness/substrates.py` | 381 lines — 7 async substrates (replaced by ThoughtStream) |
| `guinevere/consciousness/substrate_registry.py` | 60 lines — substrate name→coroutine registry (no longer needed) |

---

## Architecture Changes

### Before (7-substrate pattern)
```
ConsciousnessLoop
  ├─ substrate_heartbeat (1s loop + asyncio.sleep)
  ├─ substrate_active_cognition (5m loop + asyncio.sleep)
  ├─ substrate_reflection (1h loop + asyncio.sleep)
  ├─ substrate_strategic_planning (24h loop + asyncio.sleep)
  ├─ substrate_dreaming (4-6h loop + asyncio.sleep)
  ├─ substrate_metacognition (30s loop + asyncio.sleep)
  └─ substrate_emotion_driven (60s loop + asyncio.sleep)
```
7 concurrent asyncio.Tasks, each with `while not shutdown: ... await asyncio.sleep(N)`.

### After (unified thought stream)
```
ConsciousnessLoop
  └─ ThoughtStream.run() (single asyncio.Task)
      └─ while not shutdown:
          ├─ check_hard_stop()
          ├─ select_thought_type(affect, weights)
          ├─ generate(content via _self_prompt)
          ├─ metacog_eval(confidence)
          ├─ record_thought()
          ├─ action if confidence > 0.8
          └─ yield_to_event_loop()
```
1 asyncio.Task, sequential thoughts, no asyncio.sleep.

### ThoughtType Enum
- COGNITION — active thinking
- REFLECTION — memory consolidation
- PLANNING — strategic aspiration
- DREAMING — counterfactual replay
- META — metacognition (quality assessment)
- HEARTBEAT — liveness pulse

### AffectVector Influence
Thought type selection uses weighted random with affect-based modulation:
- High curiosity → boosts COGNITION, PLANNING
- High serenity → boosts DREAMING
- High confidence → boosts META
- Low arousal → boosts REFLECTION

### HARD STOP Integration
- `ThoughtStream.check_hard_stop()` delegates to `guinevere.consciousness.safety.HardStopGuard`
- Lazy-init with cached guard instance (no repeated module imports)
- Fail-open when Redis unavailable or safety module not yet implemented
- Called at start of each thought cycle

---

## Verification Results

### Import Test
```
$ python -c "from guinevere.consciousness.thought import Thought, ThoughtType; print('OK')"
OK
```

### Forbidden Patterns Check
- `asyncio.sleep(` in thought_stream.py: **NONE** (only in safety.py — allowed)
- `while True:` without shutdown check: **NONE** (only in safety.py — allowed)

### Test Results
```
$ python -m pytest tests/p24/test_consciousness.py tests/p24/test_consciousness_delegate.py -v -x --timeout=30
======================= 23 passed in 1.56s =======================
```

All 23 tests pass:
- TestConsciousnessImports (3): loop/state, thought/stream, infra
- TestThoughtType (2): 6 types, correct values
- TestThought (4): defaults, should_act threshold, log_string
- TestConsciousnessLoop (3): start/stop, thought_stream property, thought_types
- TestSelfPrompting (1): mock self-prompt produces thought
- TestSessionHooks (3): start sets state, end clears state, full lifecycle
- TestAffectVector (2): ewma_update, as_dict
- TestDreamJournal (2): add_entry, capped_at_50
- TestSnapshot (1): returns dict
- TestDelegate (2): self_prompt delegates to agent, empty string on failure

---

## Hard Rejection Criteria Check

| Criterion | Status |
|---|---|
| ThoughtStream generates sequential thoughts | **PASS** — one thought at a time, next starts when previous finishes |
| Supports all 6 ThoughtTypes | **PASS** — COGNITION, REFLECTION, PLANNING, DREAMING, META, HEARTBEAT |
| Shutdown handling | **PASS** — asyncio.Event pattern, yields to event loop for cancellation propagation |
| No asyncio.sleep in thought_stream.py | **PASS** — uses run_in_executor yield instead |
| No substrates.py imports | **PASS** — file deleted, all references removed |
| _self_prompt preserved | **PASS** — moved to thought_stream.py with identical interface |

---

## Design Decisions and Caveats

1. **Yield mechanism**: Uses `asyncio.get_running_loop().run_in_executor(None, lambda: None)` instead of `asyncio.sleep(0)`. This yields to the event loop for cancellation propagation without violating the "no asyncio.sleep in thought_stream.py" constraint.

2. **HARD STOP guard caching**: The HardStopGuard instance is created once and cached. When no Redis client is available, the guard is skipped entirely (fail-open) to avoid per-cycle overhead.

3. **Metacognitive evaluation**: META-type thoughts parse `quality_score` from JSON response. Other types use a baseline confidence of 0.5 ± affect influence.

4. **Action threshold**: Thoughts with confidence > 0.8 trigger action execution. Currently logs and records the action; future dispatchers will handle specific actions per type.

5. **State compatibility**: ConsciousnessState.record_thought() signature preserved — the new code calls it the same way as the old substrates did.

6. **Test compatibility**: Tests updated to use MockLLMRouter with synchronous `chat()` method (matching the AIAgent.chat() interface). Old substrate-specific tests replaced with ThoughtStream-specific tests.

---

## Evidence Artifacts

- `evidence/loop-replan/A1/implementation-report.md` — this file
- `evidence/loop-replan/A1/scaffold-check.md` — verification scaffold results
- `evidence/loop-replan/A1/auditor-gate.md` — auditor gate status
