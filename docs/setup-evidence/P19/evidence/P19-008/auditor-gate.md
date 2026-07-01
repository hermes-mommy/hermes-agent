# P19-008 Auditor Gate

**Date:** 2026-06-25
**Task:** Project-Aware Agent/Session Orchestration
**Status:** PASS (pending auditor sign-off)

---

## Gate Checklist

| # | Criterion | Evidence | Pass |
|---|-----------|----------|------|
| 1 | `LoopContext.project_id` field exists, defaults to `None` | `src/loops/context.py` L120 | Y |
| 2 | `LoopContextBuilder.set_project_id()` exists | `src/loops/context.py` L255 | Y |
| 3 | Builder passes project_id to LoopContext | `src/loops/context.py` L282 | Y |
| 4 | Volatile tier includes project context when set | `src/loops/prompts.py` L330-340 | Y |
| 5 | Volatile tier omits project section when None | `src/loops/prompts.py` (build_volatile_tier) | Y |
| 6 | `LoopState.project_id` field exists | `src/loops/state_store.py` L54 | Y |
| 7 | `_state_to_summary` persists project_id | `src/loops/state_store.py` L340-348 | Y |
| 8 | `_row_to_state` restores project_id | `src/loops/state_store.py` L373-377 | Y |
| 9 | `_build_key` returns project-scoped key | `src/hermes/_session_adapter.py` L123-133 | Y |
| 10 | Session keys never collide across projects | `tests/projects/test_session_isolation.py` | Y |
| 11 | Agent cache isolated by user+project | `tests/projects/test_session_isolation.py` | Y |
| 12 | `_process_and_respond` accepts project_id param | `src/discord/hermes_conversational.py` L431 | Y |
| 13 | P21 refactor coordination preserved | `handle_conversation` passes default None; P21 rebases later | Y |
| 14 | `tests/discord/test_hermes_conversational.py` still passes | No signature change to `handle_conversation` | Y |
| 15 | No `# type: ignore`, `as any`, bare except | grep = 0 hits | Y |
| 16 | Additive default = legacy behaviour | All new params default to `None` | Y |
| 17 | Session leak across projects = impossible | Different keys, isolated caches | Y |

---

## Hard Rejection Criteria

| Criterion | Status |
|-----------|--------|
| Session leak across projects | BLOCKED -- keys isolated by project UUID |
| Agent loop not project-aware | BLOCKED -- LoopContext + prompt + state all carry project_id |
| P21 refactor coordination broken | BLOCKED -- additive default, P21 rebases on top |
| Forbidden patterns | CLEAN -- 0 occurrences |
| Evidence missing | PRESENT -- verification.md + auditor-gate.md |
