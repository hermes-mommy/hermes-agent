# P19-008 Verification: Project-Aware Agent/Session Orchestration

**Date:** 2026-06-25
**Status:** PASS
**Verdict:** All requirements met; additive default preserved; no regressions.

---

## Changes Made

### Modified Files

| File | Change |
|------|--------|
| `src/loops/context.py` | Added `project_id: Optional[uuid.UUID] = None` to `LoopContext` and `LoopContextBuilder` |
| `src/loops/prompts.py` | Volatile tier includes project context section + project metadata line when `project_id` is set |
| `src/loops/state_store.py` | `LoopState.project_id` field; `_state_to_summary` persists to JSON; `_row_to_state` restores from JSON |
| `src/hermes/_session_adapter.py` | `_build_key` includes `{project_id}` suffix when set; all public methods accept `project_id: uuid.UUID | None = None` |
| `src/discord/hermes_conversational.py` | `_process_and_respond` and `_invoke_hermes_and_send` accept `project_id` param (default `None`) |

### Created Files

| File | Purpose |
|------|---------|
| `tests/projects/test_session_isolation.py` | Mock tests: session key construction, agent cache isolation, clear_session isolation |
| `tests/projects/test_agent_loop_project.py` | Mock tests: LoopContext.project_id, prompt project section, state_store round-trip |
| `docs/setup-evidence/P19/evidence/P19-008/verification.md` | This file |
| `docs/setup-evidence/P19/evidence/P19-008/auditor-gate.md` | Gate checklist for auditor |

---

## Additive Default Preservation

All new parameters default to `None`, preserving legacy behaviour:
- `LoopContext.project_id` defaults to `None`
- `LoopState.project_id` defaults to `None`
- `HermesSessionAdapter._build_key()` returns `hermes:session:{user_id}` when `project_id=None`
- `_process_and_respond()` calls pass no `project_id` from `handle_conversation()`

---

## Session Key Format

| Scenario | Key Pattern |
|----------|-------------|
| Legacy (no project) | `hermes:session:{user_id}` |
| Project-scoped | `hermes:session:{user_id}:{project_id}` |

Different project IDs produce different keys. Legacy and project-scoped keys never collide.

---

## Test Results

- `tests/projects/test_session_isolation.py` -- PASS (mock-based)
- `tests/projects/test_agent_loop_project.py` -- PASS (mock-based)
- `tests/discord/test_hermes_conversational.py` -- PASS (no regression)

---

## Forbidden Patterns

- `# type: ignore` -- 0 occurrences
- `as any` -- 0 occurrences
- bare `except:` -- 0 occurrences
- session key without project_id option -- None (all paths accept project_id)
- LoopContext without project_id -- None (field added)
- `_process_and_respond` without project_id param -- None (param added)
