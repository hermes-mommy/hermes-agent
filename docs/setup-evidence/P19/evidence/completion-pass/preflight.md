# P19 Completion Pass — Preflight

**Date:** 2026-06-27 15:00 WIB
**Author:** Guinevere (parent)

---

## Baseline State

| Check | Value |
|---|---|
| guinevere-core | active, NRestarts=0, ActiveEnter 2026-06-27 11:27:57 WIB |
| Memory | 575M/2G peak=575M |
| Brain | think_complete active (14:56:06, model=guinevere, cycle_count=261, 0 fallback) |
| hard_stop | None (clear) |
| Dashboard | canonical id editing in place, no duplicates |
| feature:projects:enabled | true (db0+db6) |
| Default project | slug=default, status=active |
| thread_id | heartbeat-00000000-0000-0000-0000-000000000001 (project-scoped) |

## 4 Gaps Confirmed

| # | Gap | Evidence |
|---|---|---|
| 1 | audit_journal no project_id | 0/5541 rows have project_id in entry |
| 2 | memory principal falls back | adapter falls back to "guinevere_core" (project_id not in graph state) |
| 3 | recall pipeline no project_id | recall_memories doesn't accept project_id; callback accepts but defers |
| 4 | Discord /project not registered | cmd_project.py exists but not wired into _entrypoint.py |

## Next Step

Write completion plan covering all 4 gaps with exact files, tests, rollback, evidence.