# P18 — Advanced Memory: Index

**Status:** ✅ COMPLETE (MVP)
**Date:** 2026-06-18
**Implementation date:** 2026-06-19
**Phase:** Expansion

## Scope

Phase 18 extends the existing memory schema with advanced retrieval and
consolidation capabilities: hierarchical memory tiers (working / episodic /
semantic / archival), automatic summarization and decay policies, episodic
clustering, and proactive recall triggered by context signals (location,
time, conversation topic). The phase also introduces operator-facing memory
controls for review, edit, and bulk purge.

Deliverables include: memory tier schema and migration, FSRS-based spaced
repetition and consolidation scheduler, proactive recall hook into the agent
loop, memory review/edit Discord commands, and evaluation harness for recall
precision and latency budgets.

## Directory Structure

```
P18/
├── README.md                    ← You are here
├── plan/                        ← Implementation plan
│   └── p18-implementation-plan.md
├── evidence/                    ← Per-step evidence
│   ├── STEP-P18-001/
│   │   └── verification.md
│   ├── STEP-P18-002/
│   │   └── verification.md
│   ├── STEP-P18-004/
│   │   └── verification.md
│   ├── STEP-P18-008/
│   │   └── verification.md
│   └── audit-fixes/
│       └── verification.md
└── research/                    ← Research artifacts
```

## Production Code Location

| Artifact | Path |
|---|---|
| Memory tiers module | `src/memory/tiers.py` |
| FSRS spaced repetition | `src/memory/spaced_repetition.py` |
| Consolidation scheduler | `src/memory/consolidation.py` |
| Discord commands | `src/discord/cmd_memory_stats.py`, `cmd_memory_review.py`, `cmd_memory_schedule.py`, `cmd_memory_decay.py` |
| Read pipeline (reconsolidation) | `src/memory/read_pipeline.py` |
| DB Migration | `alembic/versions/p18_add_memory_tiers_fsrs.py` |

## Progress

| Step | Status | Description |
|---|---|---|
| P18-001 | ✅ COMPLETE | Memory tier schema + FSRS columns + migration |
| P18-002 | ✅ COMPLETE | FSRS-6 spaced repetition + consolidation scheduler |
| P18-003 | ⬜ | Proactive recall hook into agent loop |
| P18-004 | ✅ COMPLETE | Memory Discord commands (stats, review, schedule, decay) |
| P18-005 | ⬜ | Recall precision + latency evaluation |
| P18-006 | ⬜ | Meta-memory layer |
| P18-007 | ⬜ | Context budget integration |
| P18-008 | ✅ COMPLETE | Reconsolidation-on-retrieval + FSRS recall scoring |

> **Note:** MVP complete (2026-06-19). Phase 2 (P18-003 proactive recall, P18-005 eval) deferred. Phase 3 (P18-006 meta-memory, P18-007 context budget) pending evaluation.
