# Enterprise Fix — Step 4: wire.py + safety.py Deprecation/Safety Notes Verification

**Date**: 2026-07-10
**Status**: PASS (No Code Change Required)
**Agent**: Sisyphus (direct verification)

---

## Audit Result

**Files Reviewed**:
- `guinevere/consciousness/wire.py` (lines 1-18)
- `guinevere/consciousness/safety.py` (lines 1-25)

**Findings**:

### wire.py
- Module docstring already correctly states: *"DEPRECATED: server.py ``_lifespan()`` is the primary consciousness loop entrypoint."*
- Already documents the `ConsciousnessLoop(llm_router=, settings=)` signature.
- No mention of `redis_client` needed because `wire.py` is the **deprecated path** (Group G agent_init.py). The new `redis_client` injection happens exclusively via `server.py` lifespan (Step 2) → `loop.py` (Step 2) → `thought_stream.py` (Step 3).

**Verdict**: No edit required. Existing deprecation language is sufficient.

### safety.py
- Module docstring correctly describes `HardStopGuard` behavior, fail-open semantics, and the safety contract.
- Line 24 already states: *"Replaces HeartbeatService._heartbeat_1s() HARD STOP detection (A6 deprecation)."*
- No code changes needed; the guard implementation already accepts `redis_client` in its constructor (verified in Step 3).

**Verdict**: No edit required. Safety contract is correctly documented.

---

## Evidence Path

**Output File**: `evidence/loop-replan/enterprise-fix/step4-wire-safety-notes.md` (this file)

**Rationale for "No Change"**:
- Both files already contain accurate, up-to-date deprecation and safety language.
- The `redis_client` wiring is an **implementation detail** handled in the active path (`server.py` → `loop.py` → `thought_stream.py`), not in the deprecated `wire.py` shim.

---

## Auditor Gate (Self-Check)

| Check | Result |
|-------|--------|
| Files reviewed | ✅ wire.py, safety.py |
| Forbidden patterns | ✅ 0 matches (no edits performed) |
| Evidence file written | ✅ This file |
| Correct decision | ✅ No code change needed |
| Scope respected | ✅ Did not touch deprecated wire.py logic |

**Verdict**: **PASS** — Step 4 complete with zero code changes. Ready for Step 5 (tests).

---

**Footer**
- Related Steps: 2 (loop.py), 3 (thought_stream.py)
- Next: Step 5 — Add 3+ tests for redis_client wiring path
