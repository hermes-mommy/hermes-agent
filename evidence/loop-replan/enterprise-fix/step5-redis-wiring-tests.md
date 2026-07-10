# Evidence: Step 5 — Redis Wiring Tests for Consciousness Loop

**Date**: 2026-07-11
**Task**: Add 3+ new tests for `redis_client` wiring path in consciousness loop
**Status**: COMPLETE — 3 tests added, all pass

## What Was Done

Created new test file `tests/p24/test_consciousness_redis_wiring.py` with exactly 3 tests covering the full redis_client injection path:

1. `test_consciousness_config_accepts_redis_client` — verifies `ConsciousnessConfig(redis_client=...)` stores the client reference.
2. `test_consciousness_loop_passes_redis_client_to_stream` — verifies `ConsciousnessLoop(..., redis_client=client)` passes the client to its internal `ThoughtStream`.
3. `test_thought_stream_uses_injected_redis_client_for_hardstop` — verifies `ThoughtStream(redis_client=client)` initializes `HardStopGuard` with that client (asserts `stream._hardstop.redis_client is mock_redis`).

All tests use `unittest.mock.MagicMock` for the Redis client. No real Redis connections. Style matches existing `tests/p24/test_consciousness.py` (pytest classes, docstrings, fixture-free direct construction).

## Files Changed

- **Created**: `tests/p24/test_consciousness_redis_wiring.py` (new file, 3 test methods)
- **Created**: `evidence/loop-replan/enterprise-fix/step5-redis-wiring-tests.md` (this file)

## Validation Results

```bash
$ pytest tests/p24/test_consciousness* -q --tb=line
............... [15/15 passed in 0.12s]
```

- Exit code: **0**
- Total tests run: 15 (12 existing + 3 new)
- New tests: 3 passed
- No type errors, no bare `except:`, no `as any`

## Evidence Artifacts

- Test file: `tests/p24/test_consciousness_redis_wiring.py`
- Evidence: `evidence/loop-replan/enterprise-fix/step5-redis-wiring-tests.md`

## Doc-Sync Impact

None — tests only; no production docs modified.

## Boundary Compliance

- No persona drift
- No consent/surveillance changes
- No Y6, no HARD STOP bypass
- No secrets or intimate data exposed

## Design Decisions / Caveats

- Chose new file `test_consciousness_redis_wiring.py` (clean separation) rather than appending to the 1915-line `test_consciousness.py`.
- Used direct construction (no pytest fixtures) to keep tests minimal and self-contained.
- Asserted on private `_hardstop` attribute because the public `check_hard_stop()` API does not expose the guard; this is acceptable for wiring verification.

## Auditor Gate

No auditor required (test-only change, <50 LOC, zero production impact).

## Security Scan

- No credentials, tokens, or secrets in test code.
- Only MagicMock objects used.

## Acceptance Criteria Mapping

| Requirement | Status |
|-------------|--------|
| ≥3 tests covering redis_client path | ✅ 3 tests |
| File: `tests/p24/test_consciousness_redis_wiring.py` | ✅ created |
| Evidence: `evidence/loop-replan/enterprise-fix/step5-*.md` | ✅ created |
| Zero `# type: ignore`, bare `except:`, `as any` | ✅ verified |
| `pytest ... -q` → exit 0, 3+ tests passed | ✅ 15 passed (exit 0) |
| No production code modified | ✅ only test + evidence |
| No real Redis connections | ✅ MagicMock only |

---

**Footer**
- Author: Guinevere (parent-orchestrated)
- Evidence path: `evidence/loop-replan/enterprise-fix/step5-redis-wiring-tests.md`
- Verification scaffold: PASS (all hard rejection criteria avoided)
