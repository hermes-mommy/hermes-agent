# Research: TimescaleDB 2.x Compression/Columnstore — Why `add_compression_policy` Fails and How to Fix It

**Date:** 2026-06-02
**Scope:** TimescaleDB 2.15–2.27 on PostgreSQL 16, compression/columnstore API, Guinevere P3-002 context
**Sources:** Official TimescaleDB docs (archived `timescale/docs` repo), GitHub source code + issues #8600/#8739/#8749, real-world Alembic migrations, Guinevere workspace scan

---

## Executive Summary

The P3-002 migration error `columnstore not enabled on hypertable "events"` at `SELECT add_compression_policy('surveillance.events', INTERVAL '7 days', if_not_exists => TRUE)` means the hypertable `surveillance.events` was created but **compression/columnstore was never enabled on it**. The `ALTER TABLE ... SET (timescaledb.compress = true)` step is a mandatory prerequisite — skipping it causes the internal C check `TS_HYPERTABLE_HAS_COMPRESSION_ENABLED(ht)` to fail.

Two distinct causes are possible:

| Cause | Scenario | Fix |
|---|---|---|
| **#1 — Missing ALTER step** | The migration never ran `ALTER TABLE surveillance.events SET (timescaledb.compress = true, ...)` before `add_compression_policy()` | Add the missing ALTER step |
| **#2 — PL/pgSQL plan cache bug** (TimescaleDB ≤ 2.21.1) | The ALTER + policy call is wrapped in a PL/pgSQL function; second execution strips the custom TimescaleDB options from cached plan | Upgrade to ≥ 2.22, or avoid wrapping in PL/pgSQL |

For Guinevere P3-002, the root cause is **Cause #1**: the `tmp/patch-migration.py` script injects hypertable DDL (`create_hypertable`) but does **not** include the `ALTER TABLE ... SET (timescaledb.compress = true)` step before the `add_compression_policy()` call. The ALTER step must be added.

Additionally, the currently installed **TimescaleDB 2.27.1 Community Edition** Docker image may need verification that the Apache 2–licensed compression feature is actually available in the running container.

---

## 1. What Raises the "columnstore not enabled" Error?

### Exact Code Path

**File:** `tsl/src/bgw_policy/compression_api.c` (line ~380)
**Function:** `validate_compress_chunks_hypertable()`

```c
if (!TS_HYPERTABLE_HAS_COMPRESSION_ENABLED(ht))
{
    ereport(ERROR,
            (errcode(ERRCODE_FEATURE_NOT_SUPPORTED),
             errmsg("columnstore not enabled on hypertable \"%s\"",
                     get_rel_name(user_htoid)),
             errhint("Enable columnstore before adding a columnstore policy.")));
}
```

Both `add_compression_policy()` (function) and `add_columnstore_policy()` (procedure) resolve to the same C function `ts_policy_compression_add`, which calls `validate_compress_chunks_hypertable()`.

### The Check Macro

**File:** `src/hypertable.h`

```c
#define TS_HYPERTABLE_HAS_COMPRESSION_ENABLED(ht) \
    ((ht)->fd.compression_state == HypertableCompressionEnabled)
```

The error fires when `hypertable->fd.compression_state != 1` — meaning the hypertable was **never flagged as compression-enabled**. This flag is set **only** by running `ALTER TABLE ... SET (timescaledb.compress = true)` (or the alias `timescaledb.enable_columnstore = true`).

### The ALTER TABLE Interception

**File:** `src/with_clause/alter_table_with_clause.c`

TimescaleDB intercepts `ALTER TABLE` via a PostgreSQL utility hook. It parses custom `timescaledb.*` options and removes them before PostgreSQL processes the statement. The parsed option for enabling compression accepts **three alias names**:

```c
.arg_names = {"compress", "columnstore", "enable_columnstore", NULL},
```

All three are equivalent — they all set `compression_state = 1`.

---

## 2. Old API (Compress) vs Newer API (Columnstore) — Differences

TimescaleDB 2.13+ introduced columnar/columnstore access method. The rebranding to "hypercore" happened in 2.18. **Both APIs are aliased to the same underlying implementation.**

| Aspect | Legacy Compression API (≤ 2.16) | Columnstore / Hypercore API (≥ 2.18) |
|---|---|---|
| Enable syntax | `ALTER TABLE t SET (timescaledb.compress, ...)` | `ALTER TABLE t SET (timescaledb.enable_columnstore = true, ...)` |
| Segment-by option | `compress_segmentby` | `segmentby` |
| Order-by option | `compress_orderby` | `orderby` |
| Policy function | `add_compression_policy()` (function) | `add_columnstore_policy()` (procedure, v2.18+) |
| Status | Still supported, no migration needed | Recommended for new deployments |

**Both `compress` and `enable_columnstore` map to the same boolean flag** in the `alter_table_with_clause_def[]` array. Using either one sets `compression_state = 1`. The `add_compression_policy()` function continues to work regardless of which syntax was used to enable compression.

**Recommendation for Guinevere:** Continue using the legacy compression API (`timescaledb.compress`, `add_compression_policy()`) — it is fully supported and avoids confusion. No migration to hypercore is needed.

---

## 3. The PL/pgSQL Plan Caching Bug (TimescaleDB 2.21.1)

**Issue:** [#8600](https://github.com/timescale/timescaledb/issues/8600) — "Second run of PL/pgSQL hypertable setup fails"
**Fix:** PRs [#8739](https://github.com/timescale/timescaledb/pull/8739) + [#8749](https://github.com/timescale/timescaledb/pull/8749) (merged into 2.22)
**Affected:** TimescaleDB 2.21.1

### Root Cause

When ALTER TABLE with TimescaleDB custom options is wrapped inside a PL/pgSQL function, the utility hook strips the custom options and PostgreSQL caches the sanitized plan. On the **second call** to the same function, the cached plan contains a plain `ALTER TABLE t SET ()` — an empty option list — which does NOT set `compression_state = 1`. The subsequent `add_compression_policy()` then fails with:

```
ERROR: columnstore not enabled on hypertable "data_test"
HINT: Enable columnstore before adding a columnstore policy.
```

### Reproduction

```sql
-- TimescaleDB 2.21 — BUG REPRODUCER
CREATE OR REPLACE FUNCTION create_hypertable_test() RETURNS VOID AS $$
BEGIN
  DROP TABLE IF EXISTS data_test CASCADE;
  CREATE TABLE data_test (...);
  PERFORM create_hypertable('data_test', ...);
  ALTER TABLE data_test SET (timescaledb.enable_columnstore = true, ...);  -- stripped on 2nd call
  CALL add_columnstore_policy('data_test', after => INTERVAL '2d');       -- fails on 2nd call
END;
$$ LANGUAGE plpgsql;

SELECT create_hypertable_test();  -- OK
SELECT create_hypertable_test();  -- ERROR: columnstore not enabled
```

### Is Guinevere Affected?

**Unlikely** — Guinevere uses raw `op.execute()` calls in Alembic migrations, not PL/pgSQL functions. The bug only applies when wrapping ALTER TABLE inside a PL/pgSQL function body. Guinevere is on TimescaleDB 2.27.1 (based on P0-016 evidence), which already contains the fix.

**Nevertheless**, the migration code should be structured so the `ALTER TABLE ... SET (timescaledb.compress = true)` call is a **separate, explicit step** in the migration, not combined with the policy call in a way that could trigger caching issues.

---

## 4. Correct SQL Sequence for Enabling Compression

### Canonical Four-Step Sequence

```sql
-- Step 1: Create base table
CREATE TABLE surveillance.events (
    event_id     BIGINT GENERATED ALWAYS AS IDENTITY,
    occurred_at  TIMESTAMPTZ NOT NULL,
    event_type   TEXT NOT NULL,
    device_id    TEXT NOT NULL,
    payload      JSONB,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Step 2: Convert to hypertable
SELECT create_hypertable(
    'surveillance.events',
    by_range('occurred_at', INTERVAL '1 day'),
    if_not_exists => TRUE
);

-- Step 3: Enable compression with segment/order options
ALTER TABLE surveillance.events SET (
    timescaledb.compress = true,
    timescaledb.compress_segmentby = 'event_type, device_id',
    timescaledb.compress_orderby = 'occurred_at DESC, event_id DESC'
);

-- Step 4: Add compression policy (with if_not_exists for idempotency)
SELECT add_compression_policy(
    'surveillance.events',
    INTERVAL '7 days',
    if_not_exists => TRUE
);
```

### Step 3 is the Missing Piece

**This is the root cause of the P3-002 error.** The `tmp/patch-migration.py` script injects `create_hypertable()` calls (Step 2) and policy calls (Step 4) but **omits Step 3** — the `ALTER TABLE ... SET (timescaledb.compress = true)` command. Without Step 3, `hypertable->fd.compression_state` stays at `0`, and `add_compression_policy()` raises the error.

### All Hypertables and Their Compression Settings

Based on the authoritative ERD (`docs/30-data/33-DatabaseERD_MigrationStrategy_v1.0.md`):

| Hypertable | Chunk Interval | Compression | Segment By | Order By | Policy | Retention |
|---|---|---|---|---|---|---|
| `memory.episodes` | 7 days | `compress = true` | `episode_type` | `started_at DESC, importance DESC` | 14 days | 10 years |
| `surveillance.events` | 1 day | `compress = true` | `event_type, device_id` | `occurred_at DESC` | 7 days | 180 days |
| `financial.transactions` | 1 month | **NONE** | — | — | — | 7 years |
| `audit.audit_trail` | 1 month | **NONE** | — | — | — | 1 year |

Only `memory.episodes` and `surveillance.events` need compression. The other two hypertables do not.

### For Continuous Aggregates (if applicable)

```sql
ALTER MATERIALIZED VIEW my_cagg SET (timescaledb.compress = true);
SELECT add_compression_policy('my_cagg', compress_after => INTERVAL '33 days', if_not_exists => TRUE);
```

---

## 5. Best Practice: Policy Deferral in Alembic Migrations

### Rule: Separate Schema DDL from Policy DDL

Compression policies should be created in a **separate migration step** after the schema DDL migration, for these reasons:

1. **Dependency ordering**: The policy requires compression to already be enabled on the hypertable, which itself requires the hypertable to exist
2. **Idempotency**: Schema changes that modify column types may conflict with compressed chunks. The safe pattern is schema → enable compression → policy
3. **Rollback safety**: `remove_compression_policy()` followed by `DROP TABLE` is cleaner than trying to unwind a single combined migration
4. **Observability**: Separate steps make it easier to verify each stage (`SELECT * FROM timescaledb_information.jobs`)

### Recommended Alembic Migration Structure

**Migration 1 — Schema + Hypertable (DDL only):**
```python
def upgrade():
    op.create_table(
        "events",
        sa.Column("event_id", sa.BigInteger(), autoincrement=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("device_id", sa.Text(), nullable=False),
        schema="surveillance",
    )
    op.execute("SELECT create_hypertable('surveillance.events', by_range('occurred_at', INTERVAL '1 day'), if_not_exists => TRUE)")
```

**Migration 2 — Enable Compression + Policy (deferred):**
```python
def upgrade():
    op.execute("""
        ALTER TABLE surveillance.events SET (
            timescaledb.compress = true,
            timescaledb.compress_segmentby = 'event_type, device_id',
            timescaledb.compress_orderby = 'occurred_at DESC'
        )
    """)
    op.execute("SELECT add_compression_policy('surveillance.events', INTERVAL '7 days', if_not_exists => TRUE)")

def downgrade():
    op.execute("SELECT remove_compression_policy('surveillance.events', if_exists => TRUE)")
    op.execute("ALTER TABLE surveillance.events SET (timescaledb.compress = false)")
```

**Alternative — Inline in a single migration (if separation is impractical):**
```python
def upgrade():
    # ... create table, create_hypertable ...

    # ENABLE compression BEFORE policy
    op.execute("""
        ALTER TABLE surveillance.events SET (
            timescaledb.compress = true,
            timescaledb.compress_segmentby = 'event_type, device_id',
            timescaledb.compress_orderby = 'occurred_at DESC'
        )
    """)
    op.execute("SELECT add_compression_policy('surveillance.events', INTERVAL '7 days', if_not_exists => TRUE)")
```

### Idempotency Using `if_not_exists`

All TimescaleDB policy functions support `if_not_exists` (and `if_exists` for removal):
- `add_compression_policy(..., if_not_exists => TRUE)` — warns instead of erroring if policy already exists
- `remove_compression_policy(..., if_exists => TRUE)` — no-op if policy doesn't exist
- `create_hypertable(..., if_not_exists => TRUE)` — no-op if hypertable exists

Always use `if_not_exists => TRUE` in migrations for idempotent re-runs.

---

## 6. Transaction Safety

### `ALTER TABLE ... SET (timescaledb.compress = true)` — Transaction-Safe

The `ALTER TABLE` command that enables compression is **a DDL command that TimescaleDB intercepts as a utility statement**. In standard PostgreSQL, DDL commands cannot be rolled back. However, when run inside an Alembic migration with the `asyncpg` driver:

- The `ALTER TABLE` runs as part of the migration's transaction
- If the migration fails later (e.g., `add_compression_policy` fails), the `ALTER TABLE` effect **may persist** because TimescaleDB's utility hook processes it independently of the transaction

**Mitigation:** Reorder operations so that the policy call comes AFTER the ALTER, and use `if_not_exists` to make the entire sequence safely re-runnable. This way, if the migration fails mid-way, the next run completes without errors.

### `add_compression_policy()` — Transaction-Safe (With Caveat)

`add_compression_policy()` creates a job in the TimescaleDB job scheduler (`timescaledb_information.jobs`). This job creation is transactional within the migration. If the migration is rolled back (e.g., by a later downgrade), the job is removed as well.

### Disable-Change-Reenable Pattern (for schema changes on compressed hypertables)

If you need to modify the schema of an already-compressed hypertable:

```python
def upgrade():
    # Disable
    op.execute("SELECT remove_compression_policy('t', if_exists => TRUE)")
    op.execute("ALTER TABLE t SET (timescaledb.compress = false)")

    # Schema change
    op.add_column("t", sa.Column("new_col", sa.Text()), schema="myschema")

    # Re-enable
    op.execute("""
        ALTER TABLE t SET (
            timescaledb.compress = true,
            timescaledb.compress_segmentby = '...',
            timescaledb.compress_orderby = '...'
        )
    """)
    op.execute("SELECT add_compression_policy('t', INTERVAL '7 days', if_not_exists => TRUE)")
```

---

## 7. Known Bugs and Version-Specific Differences (2.15–2.27)

| Version | Issue | Impact |
|---|---|---|
| **2.15** | First release with columnar access method (early columnstore) | Stable for compression API |
| **2.18** | Hypercore rebranding; `add_columnstore_policy()` introduced | Both APIs work; no migration needed |
| **2.21** | **PL/pgSQL plan caching bug** (#8600) — ALTER TABLE options stripped on cached function execution | Fixed in 2.22 via PRs #8739/#8749 |
| **2.22** | Fix for cached utility statements | Upgrade recommended |
| **2.25** | No compression-related regressions reported | Stable |
| **2.27** | Latest stable in this range; no compression bugs reported | **Guinevere runs 2.27.1** |
| **2.27.1 Community Edition** | Docker image may not include TSL-licensed features | ⚠️ **Verify compression is available** |

### ⚠️ Community Edition Caveat

The P0-016 evidence indicates TimescaleDB 2.27.1 **Community Edition** is installed. The Community Edition Docker image may or may not include compression support depending on which Docker tag was used:

- `timescale/timescaledb:latest-pg16` (full image, includes all features including compression)
- `timescale/timescaledb:latest-pg16-oss` (Apache 2 only, excludes Timescale-licensed features)

Compression is available under the Apache 2 license, so both images should include it. However, this should be **verified** before running the migration:

```sql
-- Verify compression is available in the running instance
SELECT default_version, installed_version
FROM pg_available_extensions
WHERE name = 'timescaledb';

-- Verify compression works (dry-run on an existing hypertable)
SELECT compression_enabled
FROM timescaledb_information.hypertables
WHERE hypertable_name = 'events';
```

---

## 8. Specific Fix for Guinevere P3-002

### Current Problem

The `tmp/patch-migration.py` script injects:

```python
op.execute("SELECT create_hypertable('surveillance.events', by_range('occurred_at', INTERVAL '1 day'), if_not_exists => TRUE)")
# ... later ...
op.execute("SELECT add_compression_policy('surveillance.events', INTERVAL '7 days', if_not_exists => TRUE)")
```

The `add_compression_policy()` call fails because the `ALTER TABLE ... SET (timescaledb.compress = true)` step was **never executed** between hypertable creation and policy creation.

### Required Changes

In the migration file (either the full migration or a separate patch migration), **add the missing ALTER step** between `create_hypertable()` and `add_compression_policy()`:

```python
def upgrade():
    # ... table creation, create_hypertable ...

    # Step 1: Enable compression on surveillance.events
    op.execute("""
        ALTER TABLE surveillance.events SET (
            timescaledb.compress = true,
            timescaledb.compress_segmentby = 'event_type, device_id',
            timescaledb.compress_orderby = 'occurred_at DESC'
        )
    """)

    # Step 2: Add compression policy (7-day schedule)
    op.execute("SELECT add_compression_policy('surveillance.events', INTERVAL '7 days', if_not_exists => TRUE)")

    # Repeat for memory.episodes
    op.execute("""
        ALTER TABLE memory.episodes SET (
            timescaledb.compress = true,
            timescaledb.compress_segmentby = 'episode_type',
            timescaledb.compress_orderby = 'started_at DESC, importance DESC'
        )
    """)
    op.execute("SELECT add_compression_policy('memory.episodes', INTERVAL '14 days', if_not_exists => TRUE)")

def downgrade():
    op.execute("SELECT remove_compression_policy('surveillance.events', if_exists => TRUE)")
    op.execute("ALTER TABLE surveillance.events SET (timescaledb.compress = false)")
    op.execute("SELECT remove_compression_policy('memory.episodes', if_exists => TRUE)")
    op.execute("ALTER TABLE memory.episodes SET (timescaledb.compress = false)")
```

---

## 9. References

1. TimescaleDB Source: [`compression_api.c`](https://github.com/timescale/timescaledb/blob/main/tsl/src/bgw_policy/compression_api.c)
2. TimescaleDB Source: [`hypertable.h`](https://github.com/timescale/timescaledb/blob/main/src/hypertable.h) (compression macro)
3. TimescaleDB Source: [`alter_table_with_clause.c`](https://github.com/timescale/timescaledb/blob/main/src/with_clause/alter_table_with_clause.c)
4. GitHub Issue [#8600](https://github.com/timescale/timescaledb/issues/8600) — Cached PL/pgSQL function bug
5. GitHub PR [#8739](https://github.com/timescale/timescaledb/pull/8739) — Fix for cached utility statements
6. GitHub PR [#8749](https://github.com/timescale/timescaledb/pull/8749) — Additional fix for cached utility statements
7. TimescaleDB Docs: [`about-compression.md`](https://github.com/timescale/docs/blob/latest/use-timescale/compression/about-compression.md)
8. TimescaleDB Docs: [`compression-policy.md`](https://github.com/timescale/docs/blob/latest/use-timescale/compression/compression-policy.md)
9. TimescaleDB Docs: [`add_compression_policy.md`](https://github.com/timescale/docs/blob/latest/api/compression/add_compression_policy.md)
10. Real-world pattern: [APITaxi Alembic migration](https://github.com/openmaraude/APITaxi/blob/master/APITaxi_models2/migrations/versions/20230228_11%3A06%3A53_43685d1824b7_activity_logs.py)
11. Real-world pattern: [Scribe migration (disable → schema → re-enable)](https://github.com/jonathan-gtd/scribe/blob/master/custom_components/scribe/migration.py)
12. Guinevere workspace: ERD v1.0 (`docs/30-data/33-DatabaseERD_MigrationStrategy_v1.0.md`)
13. Guinevere workspace: P0-016 TimescaleDB installation evidence