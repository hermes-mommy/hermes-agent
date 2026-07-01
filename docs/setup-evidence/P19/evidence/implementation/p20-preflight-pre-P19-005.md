# P20 Fresh Runtime Incident Preflight — Pre-P19-005 (deep LOCKED-file edits)

**Date:** 2026-06-25 (pre-P19-005)
**Trigger:** P19-005 modifies 9 P20 production files (`heartbeat.py`, `graph.py`, `cognition.py`, `dashboard_writer.py`, `redis_client.py`, `session_graph.py`, `state.py`, `self_improve.py`, `main.py`) — the deepest LOCKED-file wave. Per operator standing instruction, fresh preflight required before any LOCKED-file edit.

## 1. Verdict

**CLEAN — proceed with P19-005 (split 005a/005b/005c, strictly additive + feature-flag-gated).**

## 2. Signals (read-only)

| Signal | Value | Status |
|---|---|---|
| `guinevere-core` | active / running / Result=success / NRestarts=0 | ✅ |
| Memory current / peak | ~1.0 GB / ~1.1 GB (vs 4 GB cap) | ✅ no OOM |
| Journal errors (5 min) | 0 | ✅ |
| `hard_stop_requested` (3 min, 10 samples) | all `False` | ✅ HARD STOP CLEAR |
| think_complete/fallback events (3 min) | 4 (active brain) | ✅ |
| recursion/traceback/oom/killed (30 min) | 0 | ✅ |

## 3. Post-P19-004 health (diff vs pre-004 baseline)

P19-004's additive `project_id` threading through `_memory_bridge`/`p16`/`p18`/KG query files did NOT disturb P20: still 0 restarts, 0 errors, hard_stop clear, memory flat. `test_memory_bridge.py` 17/17 pass confirmed no regression. Baseline maintained.

## 4. Scope of 005 LOCKED edits authorized

- **005a (zero-risk additive):** add `NotRequired[Optional[str]] project_id` to `LifeMindState`/`SessionState` in `state.py`. Checkpoint-replay-safe (fields default absent). P20 regression must pass.
- **005b (feature-flagged thread_id):** `heartbeat.py` thread_id selection conditional on `feature:projects:enabled`. Flag OFF → `thread_id="heartbeat"` (legacy, P20-compatible). Flag ON → `thread_id=f"heartbeat-{project_id}"`. Grep must show 0 unconditional `thread_id="heartbeat"`.
- **005c (full project-aware):** per-project `BackgroundCognition` (bounded N=3), per-project dashboard/log, per-project world-state keys. Only after 005a+005b verified.

**Forbidden (preserved invariants):**
- HARD STOP scoped per project → FAIL (`life_kernel:hard_stop` stays global)
- `thread_id="heartbeat"` hardcoded unconditionally → FAIL (must be flag-conditional)
- P20 semantics altered when flag OFF → FAIL
- `_ADAPTERS` global mutated unsafely across projects → FAIL (per-project instances or context-read project_id)
- 6-interval heartbeat schedule changed → FAIL
- `hermes_brain.py` / `graph.py` topology altered → FAIL (005c may add per-project cognition instances but must not change the 4-node graph topology)

## 5. Footer

| Field | Value |
|---|---|
| Preflight result | CLEAN |
| Decision | Proceed with P19-005a → verify → 005b → verify → 005c |
| Author | Guinevere (parent) |
