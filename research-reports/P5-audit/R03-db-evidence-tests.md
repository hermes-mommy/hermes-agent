# R03 — P5 DB, Migration, Evidence, and Test Coverage

## 1. Migration — p5_extend_loop_instances.py

| Field | Value |
|---|---|
| revision | p5_extend_loops |
| down_revision | e401bb5fd274 |
| Schema | projects |
| Table | loop_instances |

Column additions (6):

| Column | Type | Nullable | Default |
|---|---|---|---|
| goal | Text | nullable | — |
| guardian_heartbeat_at | TIMESTAMP(tz) | nullable | — |
| lqs_score | Float | nullable | — |
| cost_estimate | Float | nullable | — |
| error_count | Integer | — | server_default="0" |
| retry_count | Integer | — | server_default="0" |

Nullable change: task_id altered from NOT NULL to nullable=True.
Downgrade: drops all 6 columns, restores task_id NOT NULL.

### CRITICAL: Broken Migration Chain

down_revision = "e401bb5fd274" references a parent migration that does NOT exist in alembic/versions/. Only ONE migration file exists in the entire directory. `alembic upgrade head` will FAIL on a fresh database. Initial schema was applied via tmp/migration.py (standalone script, not Alembic revision).

## 2. Model-Migration Consistency — LoopInstances (lines 659-692)

VERDICT: CONSISTENT

All 6 migration columns present in ORM with matching types/nullability:

- goal: Mapped[Optional[str]] = Text, nullable=True
- guardian_heartbeat_at: Mapped[Optional[datetime]] = TIMESTAMP(tz), nullable=True
- lqs_score: Mapped[Optional[float]] = Float, nullable=True
- cost_estimate: Mapped[Optional[float]] = Float, nullable=True
- error_count: Mapped[Optional[int]] = Integer, server_default=text("0")
- retry_count: Mapped[Optional[int]] = Integer, server_default=text("0")
- task_id: Mapped[Optional[uuid.UUID]] = nullable=True (matches migration)

Pre-existing columns (id, loop_phase, status, started_at, completed_at, result_summary) intact. Uses ClassificationMetaMixin. Schema = projects.

## 3. Related Tables — Still Intact

| Table | Class | Schema | FK to loop_instances | Status |
|---|---|---|---|---|
| agent_tasks | AgentTasks | projects | loop_instance_id FK | INTACT |
| evidence_artifacts | EvidenceArtifacts | projects | task_id FK | INTACT |
| subagent_registry | SubagentRegistry | agents | — | INTACT |
| task_queue | TaskQueue | agents | agent_id FK | INTACT |
| execution_log | ExecutionLog | agents | task_id+agent_id FKs | INTACT |

## 4. Evidence Trail — evidence/phase-5/

STEP folders present (8 of 23 claimed):

| Folder | File | Size |
|---|---|---|
| STEP-P5-001 | verification.md | 4513B |
| STEP-P5-002 | verification.md | 4388B |
| STEP-P5-003 | verification.md | 4381B |
| STEP-P5-004 | verification.md | 3570B |
| STEP-P5-011 | verification.md | 5327B |
| STEP-P5-017 | verification.md | 3760B |
| STEP-P5-020 | verification.md | 5019B |
| STEP-P5-022 | verification.md | 4901B |

MISSING STEP folders (15): 005, 006, 007, 008, 009, 010, 012, 013, 014, 015, 016, 018, 019, 021, 023

Auditor gates (5, all PASS): code-quality, db-migration, discord-integration, safety-boundary, security

Batch-level files: P5-batch-plan.md (12514B), P5-batch-final-report.md (6632B — claims 23/23 but only 8 evidence folders)

**EVIDENCE GAP:** batch-final-report claims 23/23 complete but only 8/23 STEP folders have verification.md.

## 5. Systemd Units

### guinevere-loops.service

| Directive | Value |
|---|---|
| After | guinevere-core.service |
| Requires | guinevere-core.service |
| ExecStart | .venv/bin/python -m src.loops.manager |
| User | guinevere |
| Restart | always, RestartSec=10 |
| Slice | guinevere.slice |

### guinevere-scheduler.service

| Directive | Value |
|---|---|
| After | guinevere-loops.service |
| Requires | guinevere-loops.service |
| ExecStart | .venv/bin/python -m src.loops.scheduler |
| User | guinevere |
| Restart | always, RestartSec=10 |
| Slice | guinevere.slice |

Dependency chain: scheduler → loops → core.
Missing: No EnvironmentFile, no MemoryMax/CPUQuota, no StandardOutput/StandardError journal.

## 6. Test Coverage — tests/test_e2e_loop.py

Single test function: test_full_loop_cycle() (async)

17 assertions covered:

1. start_loop returns loop_id (string)
2. Loop reaches terminal within 30s
3. Final status is 'complete'
4. Phase = 8 (COMPLETE)
5. Phase name 'Complete'
6-12. Artifacts exist for 7 phases
13. evidence-final.md exists
14. error_count = 0
15. artifacts dict = 7 entries
16. Task preserved
17. Goal preserved

NOT covered: Guardian, Enforcer, Hash anchor, Sub-agent, Contract, Cost tracking, Scheduler, Discord commands, API endpoints, Error count/retry, LQS calculation, State machine transitions, Migration rollback, Auth middleware, OutputVerifier, Phase handler unit tests.

Test infrastructure: Custom async runner (not pytest), asyncio.run(), manual sys.path, no fixtures/mocking.

## 7. alembic/env.py

No P5-specific references. Standard async multi-schema config. GUINEVERE_SCHEMAS includes "projects". version_table_schema="ops".
