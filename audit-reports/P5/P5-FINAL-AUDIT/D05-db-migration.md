# D05: Database Migration & Model Consistency Audit

| Field | Value |
|---|---|
| **Auditor** | Independent DB Auditor (P5-FINAL-AUDIT) |
| **Date** | 2026-06-02 |
| **Scope** | P5 migration + ORM models for LoopInstances, AgentTasks, EvidenceArtifacts, SubagentRegistry, TaskQueue, ExecutionLog |
| **Files Reviewed** | `alembic/versions/p5_extend_loop_instances.py`, `src/memory/models.py` (L54-83, L637-880), `alembic/env.py` |
| **Verdict** | **NEEDS REVIEW** |

---

## 1. Migration-Model Consistency

**Verdict: PASS**

Every column in the P5 migration exists in the ORM model with matching type, nullable, and server default.

| Column | Migration Type | Model Type | Nullable | Server Default | Match |
|---|---|---|---|---|---|
| `task_id` (alter) | `sa.UUID()` | `UUID(as_uuid=True)` | True | -- | OK |
| `goal` | `sa.Text()` | `Text` | True | -- | OK |
| `guardian_heartbeat_at` | `sa.TIMESTAMP(timezone=True)` | `TIMESTAMP(timezone=True)` | True | -- | OK |
| `lqs_score` | `sa.Float()` | `Float` | True | -- | OK |
| `cost_estimate` | `sa.Float()` | `Float` | True | -- | OK |
| `error_count` | `sa.Integer()` | `Integer` | implicit True | `"0"` / `text("0")` | OK |
| `retry_count` | `sa.Integer()` | `Integer` | implicit True | `"0"` / `text("0")` | OK |

**Note on `error_count`/`retry_count` nullable semantics:**
Both columns are `Mapped[Optional[int]]` with `server_default=text("0")`. The column is technically nullable (no `nullable=False`), but server default ensures newly inserted rows always get `0`. This is consistent between migration and model, but the design choice means:
- INSERT without specifying the column -> DB sets it to `0`
- INSERT with explicit `NULL` -> DB stores `NULL`
- If intent is "always non-null counter", consider `nullable=False` in a follow-up.

**Not a blocker** -- design is internally consistent.

---

## 2. Migration Chain Resolution

**Verdict: FAIL**

| Check | Result |
|---|---|
| `down_revision` value | `"e401bb5fd274"` |
| Parent migration file | **NOT FOUND** |
| Total migration files in `alembic/versions/` | **1** (only `p5_extend_loop_instances.py`) |

**Detail:** Grep for `revision.*=.*e401bb5fd274` across `alembic/versions/*.py` returned only the self-reference in the P5 migration (`down_revision = "e401bb5fd274"`). No file declares `revision = "e401bb5fd274"`.

**Impact:** `alembic upgrade head` will fail with `Can't locate revision identified by e401bb5fd274`. The migration cannot be applied until the parent migration file is present or `down_revision` is set to `None` (if this is the first migration).

**Fix options:**
1. Add the missing parent migration file that creates the base `loop_instances` table (and presumably all other base tables).
2. If the base schema is created via `Base.metadata.create_all()` (not through Alembic), set `down_revision = None` and add a comment explaining this is the initial Alembic-tracked migration.

---

## 3. Downgrade Completeness

**Verdict: PASS**

| Upgrade Operation | Downgrade Counterpart |
|---|---|
| `alter_column task_id nullable=True` | `alter_column task_id nullable=False` |
| `add_column goal` | `drop_column goal` |
| `add_column guardian_heartbeat_at` | `drop_column guardian_heartbeat_at` |
| `add_column lqs_score` | `drop_column lqs_score` |
| `add_column cost_estimate` | `drop_column cost_estimate` |
| `add_column error_count` | `drop_column error_count` |
| `add_column retry_count` | `drop_column retry_count` |

Downgrade drops columns in exact reverse order of addition and reverts `task_id` nullable constraint. **Complete reversal.**

**Caveat (standard):** Downgrade will fail if any `loop_instances` rows have `task_id IS NULL` at downgrade time, since it enforces `nullable=False`. This is inherent to nullable-to-non-nullable downgrades and not a defect.

---

## 4. Schema Correctness ("projects" schema)

**Verdict: PASS**

| Location | Schema Used | Correct |
|---|---|---|
| Migration: all `op.add_column` calls | `schema="projects"` | OK |
| Migration: `op.alter_column` | `schema="projects"` | OK |
| Migration: all `op.drop_column` | `schema="projects"` | OK |
| Model `LoopInstances.__table_args__` | `{"schema": "projects"}` | OK |
| Model `Tasks.__table_args__` | `{"schema": "projects"}` | OK |
| Model `AgentTasks.__table_args__` | `{"schema": "projects"}` | OK |
| Model `EvidenceArtifacts.__table_args__` | `{"schema": "projects"}` | OK |
| `alembic/env.py` GUINEVERE_SCHEMAS | includes `"projects"` | OK |

All P5-relevant tables and migration operations consistently use the `projects` schema.

---

## 5. Foreign Key Integrity

**Verdict: PASS**

| FK Column | Points To | Target Table Exists | Target PK Type |
|---|---|---|---|
| `LoopInstances.task_id` | `projects.tasks.id` | Yes (`Tasks`, L637) | `UUID(as_uuid=True)` |
| `AgentTasks.loop_instance_id` | `projects.loop_instances.id` | Yes (`LoopInstances`, L659) | `UUID(as_uuid=True)` |
| `EvidenceArtifacts.task_id` | `projects.tasks.id` | Yes (`Tasks`, L637) | `UUID(as_uuid=True)` |

All FK targets resolve to existing tables with matching PK types within the `projects` schema.

**Additional FKs in reviewed scope:**

| FK Column | Points To | Target Exists |
|---|---|---|
| `TaskQueue.agent_id` | `agents.subagent_registry.id` | Yes (`SubagentRegistry`, L804) |
| `ExecutionLog.task_id` | `agents.task_queue.id` | Yes (`TaskQueue`, L828) |
| `ExecutionLog.agent_id` | `agents.subagent_registry.id` | Yes (`SubagentRegistry`, L804) |

All cross-schema FKs (projects -> agents) are valid.

---

## 6. task_id Nullable Change

**Verdict: PASS**

| Aspect | Assessment |
|---|---|
| Direction | NOT NULL -> nullable (relaxation) |
| Backward-compatible | Yes -- existing rows retain values; new rows may be NULL |
| Documented | Yes -- migration docstring L4: "makes task_id nullable for ad-hoc loops" |
| Model type | `Mapped[Optional[uuid.UUID]]` -- correctly reflects nullable=True |
| Downgrade risk | Standard -- fails if NULL rows exist at downgrade time |

The change supports ad-hoc loops that are not tied to a specific task. Design rationale is sound.

---

## 7. Server Defaults (error_count / retry_count)

**Verdict: PASS**

| Column | Migration Syntax | Model Syntax | DDL Output |
|---|---|---|---|
| `error_count` | `server_default="0"` | `server_default=text("0")` | `DEFAULT 0` |
| `retry_count` | `server_default="0"` | `server_default=text("0")` | `DEFAULT 0` |

Both syntaxes are correct:
- Migration uses Alembic's `server_default` string parameter, which emits raw DDL.
- Model uses SQLAlchemy's `text("0")` wrapper, which also emits `DEFAULT 0`.
- PostgreSQL interprets both as integer literal `0`.

**No issue.**

---

## 8. Index Analysis

**Verdict: NEEDS REVIEW**

`LoopInstances` defines **no explicit indexes** (`__table_args__ = {"schema": "projects"}` -- dict form, no Index objects).

**Columns that would benefit from indexes:**

| Column | Query Pattern | Priority | Rationale |
|---|---|---|---|
| `task_id` | FK joins, `WHERE task_id = ?` | **High** | PostgreSQL does NOT auto-index FK columns. Every join to `tasks` requires a sequential scan on `loop_instances`. |
| `status` | `WHERE status = 'running'` | **High** | Agent loop likely queries by status frequently. |
| `started_at` | Temporal ordering, range queries | Medium | Other models (Episodes, Events) have `started_at DESC` indexes. LoopInstances lacks this. |
| `loop_phase` | `WHERE loop_phase = ?` | Medium | Phase-based filtering in agent loop. |

**Comparison with other models:**
- `Episodes`: has `Index("episodes_started_at_idx", text("started_at DESC"))`
- `Events`: has `Index("events_occurred_at_idx", text("occurred_at DESC"))`
- `LoopInstances`: **no indexes at all**

**Recommendation:** Add at minimum:
```python
# In LoopInstances.__table_args__:
Index("ix_loop_instances_task_id", "task_id"),
Index("ix_loop_instances_status", "status"),
Index("ix_loop_instances_started_at", text("started_at DESC")),
```

And a corresponding `op.create_index` / `op.drop_index` pair in the migration.

**Not a blocker** for P5 correctness, but will cause performance degradation at scale.

---

## 9. SQLite References

**Verdict: PASS**

| File | SQLite References |
|---|---|
| `p5_extend_loop_instances.py` | None |
| `alembic/env.py` | None |
| `src/memory/models.py` | None (uses PostgreSQL-specific types: UUID, JSONB, ARRAY, TSVECTOR, pgvector) |

All code is PostgreSQL-native. No SQLite fallback or conditional dialect logic found.

---

## 10. ClassificationMetaMixin Application

**Verdict: PASS**

| Check | Result |
|---|---|
| `LoopInstances` inherits `ClassificationMetaMixin` | Yes -- `class LoopInstances(Base, ClassificationMetaMixin)` (L659) |
| Mixin definition | L54-83 -- 12 governance columns |
| Other P5-relevant tables using mixin | `AgentTasks` (L695), `TaskQueue` (L828), `ExecutionLog` (L854) |
| Tables without mixin (by design) | `EvidenceArtifacts` (L717), `SubagentRegistry` (L804) |

**Mixin columns provided:**

| Column | Type | Nullable | Default |
|---|---|---|---|
| `classification` | Text | False | `'Restricted'` |
| `purpose` | Text | True | -- |
| `source` | Text | True | -- |
| `retention_class` | Text | False | `'Long-Term Curated'` |
| `retention_until` | TIMESTAMP(tz) | True | -- |
| `access_policy` | Text | False | `'guinevere-core'` |
| `encryption_profile` | Text | False | `'envelope-AES-256-GCM'` |
| `deletion_state` | Text | False | `'active'` |
| `key_id` | Text | True | -- |
| `key_version` | Integer | True | -- |
| `created_at` | TIMESTAMP(tz) | -- | `func.now()` |
| `updated_at` | TIMESTAMP(tz) | False | `func.now()` |

Mixin is correctly applied. Note: the P5 migration does not add mixin columns (those should exist from the base table creation migration -- see Finding #2 regarding missing parent migration).

---

## Summary of Findings

| # | Check | Verdict | Severity |
|---|---|---|---|
| 1 | Migration-model consistency | PASS | -- |
| 2 | Migration chain resolution | **FAIL** | **Critical** |
| 3 | Downgrade completeness | PASS | -- |
| 4 | Schema correctness | PASS | -- |
| 5 | FK integrity | PASS | -- |
| 6 | task_id nullable change | PASS | -- |
| 7 | Server defaults | PASS | -- |
| 8 | Index coverage | **NEEDS REVIEW** | Moderate |
| 9 | No SQLite references | PASS | -- |
| 10 | ClassificationMetaMixin | PASS | -- |

---

## Overall Verdict: NEEDS REVIEW

### Critical Blocker (must fix before merge)

1. **Missing parent migration file** -- `down_revision = "e401bb5fd274"` does not resolve to any file in `alembic/versions/`. Only one migration file exists in the entire directory. Alembic cannot apply this migration. Either add the parent migration or correct `down_revision`.

### Recommended Improvements (non-blocking)

2. **Add indexes** on `task_id` (FK), `status` (frequent filter), and `started_at` (temporal) for `loop_instances`. These are standard operational indexes that prevent sequential scans on hot query paths.

3. **Consider `nullable=False`** for `error_count`/`retry_count` if the intent is "always a non-negative integer". Currently nullable with server_default=0, which allows explicit NULL inserts.

---

## Appendix: Alembic Environment Assessment

| Aspect | Assessment |
|---|---|
| Async engine | `async_engine_from_config` with `NullPool` -- correct for migrations |
| Multi-schema | `GUINEVERE_SCHEMAS` frozenset with 12 schemas including `projects` |
| Version table | Stored in `ops` schema (`version_table_schema="ops"`) |
| Autogenerate support | `compare_type=True`, `compare_server_default=True` |
| Password handling | Via `GUINEVERE_DB_PASSWORD` env var -- no hardcoded secrets |
| Schema filter | `include_name` callback filters to canonical schemas only |
| Target metadata | `Base.metadata` from `src.memory.models` |

**alembic/env.py is correctly configured.** No issues found.

---

*Report generated by independent DB auditor. No source files were modified.*
