# P19 Completion Pass — Execution Plan

**Date:** 2026-06-27 15:05 WIB
**Author:** Guinevere (parent)

---

## 4 Gaps → 4 Implementation Steps

### P19-C01: Audit Journal project_id Propagation

**Root cause:** `graph.py` reflect_node calls `journal_writer.write_entry(state=state, ...)` but does NOT pass `project_id` from state. The `write_entry` class (JournalWriter in `domain_minds/durability.py` or a wrapper) doesn't propagate project_id to `PostgresAuditJournal.record()`.

**Fix:** 
1. `graph.py` reflect_node: extract `project_id` from `state` and pass to `journal_writer.write_entry(project_id=...)`
2. `journal_writer.write_entry` (must accept `project_id` kwarg and forward to `record()`)
3. `PostgresAuditJournal.record()` already accepts `project_id` (P19 change in durability.py) — just needs the caller to pass it.

**Files to touch:** `src/life_kernel/graph.py` (reflect_node), `src/life_kernel/domain_minds/durability.py` (JournalWriter class if separate from PostgresAuditJournal)

**Tests:** `tests/life_kernel/test_durability.py` or new test — verify `record()` receives project_id, verify audit journal row has project_id in entry.

### P19-C02: Memory Principal Project Scoping

**Root cause:** `MemoryRecallAdapter.recall()` scopes principal to `"project:{project_id}"` when context has project_id, but the `observe_node` context dict doesn't include project_id from graph state. The adapter receives `context.get("project_id")` → None → falls back to `"guinevere_core"`.

**Fix:**
1. `graph.py` observe_node: include `project_id` from state in the context dict passed to `memory_adapter.recall(context)`
2. Same for KG adapter: `kg_adapter.recall(context)` should receive project_id from state.

**Files to touch:** `src/life_kernel/graph.py` (observe_node)

**Tests:** `tests/life_kernel/test_p19_recall_project_id.py` (already written — 3 tests pass, now verify integration)

### P19-C03: recall_memories project_id Pipeline

**Root cause:** `recall_memories()` in `src/memory/read_pipeline.py` doesn't accept `project_id`. The callback in `main.py` accepts `project_id` but defers forwarding because the pipeline doesn't accept it.

**Fix:**
1. `recall_memories()` signature: add `project_id: uuid.UUID | None = None`
2. Forward to `ProjectScopedMemoryStore` or a WHERE clause filter when project_id is provided.
3. Remove the "defer" log in main.py callback — now actually forward project_id.

**Files to touch:** `src/memory/read_pipeline.py`, `src/core/main.py` (remove defer log, forward project_id)

**Tests:** `tests/memory/test_recall_project_id.py` or `tests/projects/test_memory_isolation.py`

### P19-C04: Discord /project UX Activation

**Root cause:** `cmd_project.py` exists and imports cleanly but is NOT registered in `_entrypoint.py` setup_hook command tree.

**Fix:**
1. `_entrypoint.py` setup_hook: import `cmd_project` callback and register `/project` command
2. `guinevere-discord.service` restart to load new command registration

**Files to touch:** `src/discord/_entrypoint.py`

**Tests:** `tests/discord/test_cmd_project.py` or equivalent

## Deployment Strategy

1. Implement all 4 fixes locally (one at a time, test each)
2. Run full test suite (life_kernel + memory + discord + projects)
3. scp changed files to VPS
4. Restart guinevere-core (P19-C01/C02/C03) + restart guinevere-discord (P19-C04)
5. Verify live proof for each gap

## Rollback

- File rollback: restore VPS files from backup (must backup before overwrite)
- Service rollback: restart core/discord with backup files
- Flag rollback: DEL feature:projects:enabled (instant, no restart)

## Evidence

All under `docs/setup-evidence/P19/evidence/completion-pass/`: preflight, plan, implementation evidence per gap, runtime proof, audit wave 1/2, final report, auditor gate.

## Hard Rejection

- Project_id in docs but not live: FAIL
- Audit journal new rows lack project_id: FAIL
- Recall accepts project_id but doesn't filter: FAIL
- Discord /project claimed but not registered: FAIL
- P20 dashboard duplicates: FAIL
- Service crash: FAIL
- Secret in evidence: FAIL
- Unrelated service disruption: FAIL