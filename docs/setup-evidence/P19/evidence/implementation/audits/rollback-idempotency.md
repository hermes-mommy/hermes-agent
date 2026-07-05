# P19 Rollback / Idempotency Audit

**Auditor:** rollback-idempotency
**Date:** 2026-06-25
**Scope:** ALL P19 modified source files (50 files) + migration files (p19_001, p19_002) + backfill script.
**Criteria:** Additive (project_id=None default), wave rollback, migration idempotency (IF NOT EXISTS / ON CONFLICT), downgrade path tested, destructive changes.

---

## Verdict: PASS WITH CONDITIONS (2 LOW, 1 INFO)

All P19 changes are additive with safe defaults. Migrations are idempotent and have downgrade paths. The single destructive DDL (domain_mind_state unique constraint swap) is transactional and reversible. Two low-severity gaps: p19_002 downgrade lacks dedicated test coverage; no explicit FK constraints on project_id columns.

---

## 1. Additive Check: project_id=None Default

### Verdict: PASS -- All 50 source files are purely additive.

Every P19-modified source file adds `project_id` as an **optional parameter with `None` default**. Existing callers are unaffected.

**Evidence by category:**

| Category | Files | project_id Signature | Additive? |
|---|---|---|---|
| Memory pipeline | `read_pipeline.py`, `write_pipeline.py`, `models.py` | `project_id: uuid.UUID \| None = None` | YES |
| Project registry | `types.py`, `registry.py`, `memory_store.py`, `exceptions.py`, `secrets_vault.py` | New module (all additive) | YES |
| Life kernel | `cognition.py`, `heartbeat.py`, `state.py`, `graph.py`, `session_graph.py`, `redis_client.py`, `self_improve.py`, `sensors.py`, `dashboard_writer.py`, `log_channel.py`, `metrics.py`, `p16_adapter.py`, `p18_adapter.py`, `domain_minds/durability.py`, `sensor_adapters/base.py` | `project_id: str \| None = None` or `NotRequired[str]` | YES |
| Loops | `context.py`, `state_store.py`, `audit_writer.py`, `prompts.py`, `metrics.py` | `project_id: Optional[uuid.UUID] = None` or `project_id: uuid.UUID \| None = None` | YES |
| Knowledge graph | `query/engine.py`, `query/context.py`, `query/ppr.py`, `query/rrf_fusion.py`, `consent/audit.py` | `project_id: uuid.UUID \| None = None` | YES |
| Discord | `cmd_project.py`, `project_session.py`, `hermes_conversational.py` | New module or `project_id: str \| None = None` | YES |
| Surveillance | `consent_gate.py`, `consumer.py` | `project_id: uuid.UUID \| None = None` | YES |
| Hermes | `_memory_bridge.py`, `_session_adapter.py` | `project_id: ... \| None = None` | YES |
| Finance | `db.py`, `hook.py`, `plugin.py` | `project_id: ... \| None = None` | YES |
| Gmail | `config.py`, `consent_manager.py`, `metrics.py`, `pubsub_client.py`, `router.py` | `project_id: ... \| None = None` | YES |
| Wearable/X-Poster | `wearable/health_consent.py`, `wearable/metrics.py`, `x_poster/config.py`, `x_poster/metrics.py` | `project_id: ... \| None = None` | YES |

**Zero-copy pass-through (memory_store.py, line 53):**
```python
if project_id is None:
    return recall_fn  # zero-copy, no overhead
```

**ORM models (models.py, lines 180-187):**
```python
project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
    UUID(as_uuid=True), nullable=True,
    comment="Project namespace UUID. NULL = global-scope entity visible from all projects.",
)
```

**Conclusion:** When `project_id` is not supplied (current default), all code paths are identical to pre-P19 behavior. No existing call signature is broken.

---

## 2. Wave Rollback: Can Every Wave Be Rolled Back?

### Verdict: PASS -- Every wave has a reversible path.

| Wave | Rollback Mechanism | Data Loss? |
|---|---|---|
| P19-001 (Governance/ADR-052) | Docs-only; no runtime changes | None |
| P19-002 (Project registry/types) | New module; unused until wired | None |
| P19-003 (DB schema/migrations) | `alembic downgrade p20_001` reverses all DDL | project_id partitioning data lost (documented warning) |
| P19-004 (Memory/KG namespace) | `project_id=None` = pass-through; no change | None |
| P19-005a/b/c (Life-kernel context) | `project_id=None` = original behavior | None |
| P19-006a-e (Sensors/actions) | `project_id=None` = original behavior | None |
| P19-007 (Discord commands) | New module; no existing commands modified | None |
| P19-008 (Agent/session orchestration) | `project_id=None` = pass-through | None |
| P19-009 (Consent/surveillance) | Falls back to global when `project_id=None` | None |
| P19-010 (Observability) | Metrics have `project_id="default"` label | None |
| P19-011 (Backfill/NOT NULL) | `alembic downgrade p19_001` drops NOT NULL | NOT NULL constraint removed (documented) |
| P19-012 (Deploy) | Standard deploy rollback | None |

**Key design:** P19's "wave rollback" is achieved through the `project_id=None` default. Disabling the feature flag (`feature:projects:enabled`) causes all code paths to treat `project_id` as None, reverting to legacy global behavior without code changes.

---

## 3. Migration Idempotency

### 3.1 p19_001_project_namespaces -- Verdict: PASS

**Idempotency mechanisms:**

| DDL Statement | Idempotency Guard | Re-run Safe? |
|---|---|---|
| `CREATE TABLE IF NOT EXISTS projects.project_registry` | IF NOT EXISTS | YES |
| `INSERT INTO projects.project_registry ... ON CONFLICT (slug) DO NOTHING` | ON CONFLICT DO NOTHING | YES |
| `ALTER TABLE ... ADD COLUMN IF NOT EXISTS project_id UUID` (x14 tables) | IF NOT EXISTS | YES |
| `ALTER TABLE ... ADD COLUMN IF NOT EXISTS project_scope TEXT ...` (x4 tables) | IF NOT EXISTS | YES |
| `UPDATE ... SET project_id = '...' WHERE project_id IS NULL` (x11 tables) | WHERE NULL guard | YES |
| `CREATE INDEX IF NOT EXISTS ix_*_project_id_*` (x17 indexes) | IF NOT EXISTS | YES |
| `CREATE UNIQUE INDEX IF NOT EXISTS ix_domain_mind_state_project_id_domain` | IF NOT EXISTS | YES |
| `DROP INDEX IF EXISTS ... ix_domain_mind_state_domain` | IF EXISTS | YES |

**Total: 50 DDL/DML statements, all idempotent.**

**Downgrade function (lines 182-243):** Reverses all changes:
- Drops all 17 composite indexes with `DROP INDEX IF EXISTS`
- Drops 4 `project_scope` columns with `DROP COLUMN IF EXISTS`
- Drops 14 `project_id` columns with `DROP COLUMN IF EXISTS`
- Drops `projects.project_registry` with `DROP TABLE IF EXISTS ... CASCADE`
- Restores original `ix_domain_mind_state_domain` unique index

### 3.2 p19_002_project_id_not_null -- Verdict: PASS

**Upgrade pre-check (lines 55-64):**
```python
for table in NOT_NULL_TABLES:
    result = op.get_bind().execute(
        sa.text(f"SELECT count(*) FROM {table} WHERE project_id IS NULL")
    )
    null_count = int(result.scalar() or 0)
    if null_count > 0:
        raise RuntimeError(
            f"PRE-CHECK FAIL: {table} has {null_count} rows with "
            f"NULL project_id. Run scripts/p19_backfill.py first."
        )
```

**NOT NULL application (lines 67-73):** `op.alter_column` with `nullable=False`. Re-running on an already-NOT-NULL column is a no-op in PostgreSQL.

**Downgrade (lines 76-83):** `op.alter_column` with `nullable=True` for all 11 tables. Re-running on an already-nullable column is a no-op.

### 3.3 Backfill Script (scripts/p19_backfill.py) -- Verdict: PASS

- Uses `WHERE project_id IS NULL` guard -- re-running on clean DB is a no-op (line 213-221)
- Batched UPDATE with ctid subselect (lines 98-112) -- no long-held row locks
- Post-backfill verification (lines 239-251) -- fails fast if incomplete
- Scope classification uses `WHERE project_scope = 'project' AND source IN (...)` -- idempotent
- Supports `--dry-run` flag for safety

### 3.4 Initial Schema Migration -- Verdict: N/A (pre-P19)

`e401bb5fd274_initial_schema_47_tables.py` uses `CREATE TABLE` (not `IF NOT EXISTS`) -- this is correct for the initial migration. All TimescaleDB hypertable and pgvector index creation uses `if_not_exists => TRUE` and `CREATE INDEX IF NOT EXISTS`.

---

## 4. Downgrade Path Testing

### Verdict: CONDITIONAL PASS

**p19_001:** Downgrade cycle is tested in `tests/projects/test_migration_p19_001.py` (lines 328-351):
```python
def test_migration_idempotent_cycle():
    """Upgrade -> downgrade p20_001 -> upgrade must succeed."""
    command.downgrade(alembic_cfg, "p20_001_life_kernel_schema")
    command.upgrade(alembic_cfg, "head")
    # Verify default project exists again
```

Additional test coverage:
- `test_registry_table_idempotent()` -- double CREATE TABLE IF NOT EXISTS
- `test_default_seeded()` -- sentinel UUID verification
- `test_default_project_idempotent_seed()` -- ON CONFLICT re-run
- `test_project_id_column_exists()` -- all 14 tables parametrized
- `test_project_scope_column_exists()` -- all 4 memory/KG tables
- `test_project_id_backfilled()` -- zero NULLs after migration
- `test_consent_null_allowed()` -- global tables stay nullable
- `test_project_id_references_valid_default()` -- orphan check
- `test_domain_mind_state_unique_constraint_swapped()` -- composite unique
- `test_composite_index_exists()` -- all 17 indexes parametrized
- `test_migration_idempotent_cycle()` -- full upgrade/downgrade/upgrade

**p19_002:** NO dedicated downgrade test. The downgrade function is trivial (ALTER COLUMN SET NOT NULL -> nullable=True) but is not exercised by any test.

**Condition:** p19_002 downgrade test should be added to `tests/projects/test_migration_p19_001.py` (or a new file) to verify the NOT NULL -> nullable cycle.

---

## 5. Destructive Changes

### Verdict: PASS -- One controlled destructive change, fully mitigated.

**Finding DESTRUCT-01 [LOW]: domain_mind_state unique constraint swap**

Location: `p19_001_project_namespaces.py`, lines 167-179.

```sql
DO $$
BEGIN
    UPDATE life_kernel.domain_mind_state
    SET project_id = '<default_uuid>'
    WHERE project_id IS NULL;

    DROP INDEX IF EXISTS life_kernel.ix_domain_mind_state_domain;

    CREATE UNIQUE INDEX IF NOT EXISTS ix_domain_mind_state_project_id_domain
    ON life_kernel.domain_mind_state (project_id, domain);
END $$;
```

**Risk assessment:**
- DROP INDEX is inside a `DO $$` block (single transaction in PostgreSQL)
- Backfill runs BEFORE the DROP, so the new composite unique is satisfiable
- Downgrade restores the original single-column unique: `CREATE UNIQUE INDEX IF NOT EXISTS ix_domain_mind_state_domain`
- Tested in `test_domain_mind_state_unique_constraint_swapped()`

**Mitigation:** Transactional ordering (backfill -> drop -> create) prevents a window where duplicate domains could be inserted. The constraint swap is the ONLY non-additive DDL in all of P19.

**No other destructive changes found:**
- `src/loops/state_store.py` line 218: `DELETE FROM projects.loop_instances WHERE ...` -- existing pre-P19 functionality (loop cleanup), not added by P19
- `src/loops/dedup.py` line 176: `DELETE FROM agents.task_queue WHERE ...` -- existing dedup logic
- No TRUNCATE, CASCADE DELETE, or data-destroying operations added by P19 source code

---

## 6. Summary of All Findings

| # | Severity | Finding | Status |
|---|---|---|---|
| RID-01 | LOW | p19_002 downgrade path not tested by any test | CONDITIONAL -- add test |
| RID-02 | LOW | No explicit FOREIGN KEY constraints from project_id columns to project_registry.id (orphan project_id values possible at DB level) | ACCEPTED -- logical references in code, FK enforcement deferred |
| RID-03 | INFO | p19_001 migration runs inline backfill UPDATE without batching (separate p19_backfill.py script mitigates for production) | DOCUMENTED |

---

## 7. Detailed Evidence Map

### Migrations
- `alembic/versions/p19_001_project_namespaces.py` -- 50 idempotent DDL/DML statements
- `alembic/versions/p19_002_project_id_not_null.py` -- Pre-check + NOT NULL with downgrade
- `scripts/p19_backfill.py` -- Batched, idempotent, verified backfill script

### Source files (50 files with project_id)
- `src/projects/types.py`, `src/projects/registry.py`, `src/projects/memory_store.py`, `src/projects/exceptions.py`, `src/projects/secrets_vault.py`
- `src/memory/read_pipeline.py`, `src/memory/write_pipeline.py`, `src/memory/models.py`
- `src/life_kernel/cognition.py`, `src/life_kernel/heartbeat.py`, `src/life_kernel/state.py`, `src/life_kernel/graph.py`, `src/life_kernel/session_graph.py`, `src/life_kernel/redis_client.py`, `src/life_kernel/self_improve.py`, `src/life_kernel/sensors.py`, `src/life_kernel/dashboard_writer.py`, `src/life_kernel/log_channel.py`, `src/life_kernel/metrics.py`, `src/life_kernel/p16_adapter.py`, `src/life_kernel/p18_adapter.py`, `src/life_kernel/domain_minds/durability.py`, `src/life_kernel/sensor_adapters/base.py`
- `src/loops/context.py`, `src/loops/state_store.py`, `src/loops/audit_writer.py`, `src/loops/prompts.py`, `src/loops/metrics.py`
- `src/knowledge_graph/query/engine.py`, `src/knowledge_graph/query/context.py`, `src/knowledge_graph/query/ppr.py`, `src/knowledge_graph/query/rrf_fusion.py`, `src/knowledge_graph/consent/audit.py`
- `src/discord/cmd_project.py`, `src/discord/project_session.py`, `src/discord/hermes_conversational.py`
- `src/surveillance/consent_gate.py`, `src/surveillance/consumer.py`
- `src/hermes/_memory_bridge.py`, `src/hermes/_session_adapter.py`
- `src/finance/db.py`, `src/finance/hook.py`, `src/finance/plugin.py`
- `src/gmail/config.py`, `src/gmail/consent_manager.py`, `src/gmail/metrics.py`, `src/gmail/pubsub_client.py`, `src/gmail/router.py`
- `src/wearable/health_consent.py`, `src/wearable/metrics.py`
- `src/x_poster/config.py`, `src/x_poster/metrics.py`

### Tests
- `tests/projects/test_migration_p19_001.py` -- 15 test functions covering idempotency, columns, indexes, FK integrity, downgrade cycle
- `tests/projects/test_agent_loop_project.py`, `test_project_switcher.py`, `test_audit_project_id.py`, `test_finance_project_aware.py`, `test_gmail_project_aware.py`, `test_wearable_xposter_project_aware.py`
- `tests/life_kernel/test_project_context.py`, `test_project_context_state.py`

### Prior audits
- `docs/setup-evidence/P19/evidence/audits/round-1/database-migration.md` -- PASS with conditions (DB-01..04)
- `docs/setup-evidence/P19/evidence/audits/round-2/database-migration.md` -- PASS (all 4 findings resolved)

---

## 8. Hard Rejection Criteria

| Criterion | Status | Evidence |
|---|---|---|
| Any source file breaks existing callers | NOT FOUND | All 50 files use `project_id=None` default |
| Migration is non-idempotent | NOT FOUND | All DDL uses IF NOT EXISTS / ON CONFLICT / WHERE NULL guard |
| Downgrade path missing | NOT FOUND | Both p19_001 and p19_002 have `downgrade()` functions |
| Undocumented destructive DDL | NOT FOUND | Only domain_mind_state constraint swap; transactional, tested |
| Feature cannot be disabled | NOT FOUND | `project_id=None` pass-through reverts to legacy behavior |
| Backfill script data-destroying | NOT FOUND | WHERE NULL guard + post-verification + --dry-run |
