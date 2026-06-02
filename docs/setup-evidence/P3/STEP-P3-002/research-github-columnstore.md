# Research: TimescaleDB Error "columnstore not enabled on hypertable"

> **Date**: 2026-06-02
> **Scope**: GitHub code search, issue tracker, real-world migration patterns
> **Type**: TYPE D (Comprehensive)

---

## 1. Exact Code Path That Raises the Error

**File**: `tsl/src/bgw_policy/compression_api.c`
**Function**: `validate_compress_chunks_hypertable()`

### Source (lines ~375-420)

The error is raised by the **`add_compression_policy`** / **`add_columnstore_policy`** entry point. Both SQL functions resolve to the same C function `ts_policy_compression_add`, which calls `policy_compression_add_internal`, which calls `validate_compress_chunks_hypertable`.

**Evidence** ([source](https://github.com/timescale/timescaledb/blob/2c8b3237d095ef1b73e3126b800719edbf406773/tsl/src/bgw_policy/compression_api.c#L364-L421)):

```c
static Hypertable *
validate_compress_chunks_hypertable(Cache *hcache, Oid user_htoid, bool *is_cagg)
{
    ContinuousAggHypertableStatus status;
    Hypertable *ht = ts_hypertable_cache_get_entry(hcache, user_htoid, true);
    *is_cagg = false;

    if (ht != NULL)
    {
        if (!TS_HYPERTABLE_HAS_COMPRESSION_ENABLED(ht))
        {
            ereport(ERROR,
                    (errcode(ERRCODE_FEATURE_NOT_SUPPORTED),
                     errmsg("columnstore not enabled on hypertable \"%s\"",
                             get_rel_name(user_htoid)),
                     errhint("Enable columnstore before adding a columnstore policy.")));
        }
        // ... also checks for cagg materialization ...
    }
    // ... also handles continuous aggregates ...
}
```

### The Check Macro

**File**: `src/hypertable.h`
**Evidence** ([source](https://github.com/timescale/timescaledb/blob/2c8b3237d095ef1b73e3126b800719edbf406773/src/hypertable.h#L24-L39)):

```c
enum
{
    HypertableCompressionOff = 0,
    HypertableCompressionEnabled = 1,
    HypertableInternalCompressionTable = 2,
};

#define TS_HYPERTABLE_HAS_COMPRESSION_ENABLED(ht) \
    ((ht)->fd.compression_state == HypertableCompressionEnabled)
```

The error fires when `hypertable->fd.compression_state != 1` — meaning columnstore/compression was **never enabled** on the hypertable via `ALTER TABLE ... SET (timescaledb.compress = true)` or the newer `timescaledb.enable_columnstore = true`.

---

## 2. The ALTER TABLE Interception Mechanism

**File**: `src/with_clause/alter_table_with_clause.c`
**Evidence** ([source](https://github.com/timescale/timescaledb/blob/2c8b3237d095ef1b73e3126b800719edbf406773/src/with_clause/alter_table_with_clause.c#L59-L80)):

```c
static const WithClauseDefinition alter_table_with_clause_def[] = {
        [AlterTableFlagColumnstore] = {
            .arg_names = {"compress", "columnstore", "enable_columnstore", NULL},
            .type_id = BOOLOID,
            .default_val = (Datum)false,
        },
        [AlterTableFlagSegmentBy] = {
            .arg_names = {"compress_segmentby", "segmentby", "segment_by", NULL},
            .type_id = TEXTOID,
        },
        [AlterTableFlagOrderBy] = {
            .arg_names = {"compress_orderby", "orderby", "order_by", NULL},
            .type_id = TEXTOID,
        },
        // ...
};
```

The ALTER TABLE command is intercepted by TimescaleDB's custom utility hook. The custom options (`timescaledb.compress`, `timescaledb.enable_columnstore`, etc.) are parsed and **removed** before the command is passed to PostgreSQL — since PostgreSQL doesn't know these options.

---

## 3. The Bug in Issue #8600 — Cached Function Problem

**Issue**: [#8600 - Second run of PL/pgSQL hypertable setup fails](https://github.com/timescale/timescaledb/issues/8600)
**Status**: Closed (fixed in PR #8739 / #8749)
**Affected Version**: TimescaleDB 2.21.1

### Root Cause (from issue comments)

> The ALTER TABLE command to set compression settings uses custom TimescaleDB storage options that aren't actually supported by PostgreSQL. To make this work, the ALTER command is intercepted and the custom options parsed and removed, before the command is passed to PostgreSQL. However, the function is cached after the options are removed so the second time the function is invoked the alter table command won't have any options.

In PL/pgSQL, cached plans lose the TimescaleDB-specific options on subsequent executions because the utility hook already stripped them during the first execution's plan caching. The second call gets a plain `ALTER TABLE <name> SET ()` (with an empty option list), which doesn't actually set `compression_state = 1` on the hypertable. Then `add_columnstore_policy()` checks `TS_HYPERTABLE_HAS_COMPRESSION_ENABLED` and finds `compression_state == 0`, raising:

```
ERROR: columnstore not enabled on hypertable "..."
HINT: Enable columnstore before adding a columnstore policy.
```

### Fix

PRs [#8739](https://github.com/timescale/timescaledb/pull/8739) and [#8749](https://github.com/timescale/timescaledb/pull/8749) fixed cached utility statements. Fixed in TimescaleDB 2.22+.

### Reproduction (from the issue)

```sql
-- TimescaleDB 2.21 — BUG REPRODUCER
CREATE OR REPLACE FUNCTION create_hypertable_test() RETURNS VOID AS
$$
BEGIN
DROP TABLE IF EXISTS data_test CASCADE;
CREATE TABLE data_test (id INT NOT NULL, date TIMESTAMP WITHOUT TIME ZONE NOT NULL, value INT NULL);
PERFORM create_hypertable('data_test', by_range('date', INTERVAL '1 day'), ...);
ALTER TABLE data_test SET (timescaledb.enable_columnstore = true, timescaledb.orderby = 'date DESC', timescaledb.segmentby = 'id');
CALL add_columnstore_policy('data_test', after => INTERVAL '2d');
END;
$$ LANGUAGE plpgsql;

-- First execution succeeds, second fails
select create_hypertable_test();  -- OK
select create_hypertable_test();  -- ERROR: columnstore not enabled
```

The **workaround** is to avoid wrapping ALTER TABLE + add_columnstore_policy inside a PL/pgSQL function, or upgrade to >= 2.22.

---

## 4. Legacy Compression (<= 2.16) vs Columnstore (>= 2.18)

The issue reporter confirms that **TimescaleDB 2.16.1** does NOT have this problem because it uses the **legacy compression API**:

| Feature | Legacy (<= 2.16.x) | Hypercore / Columnstore (>= 2.18) |
|---|---|---|
| Enable syntax | `ALTER TABLE t SET (timescaledb.compress, ...)` | `ALTER TABLE t SET (timescaledb.enable_columnstore = true, ...)` |
| Policy function | `add_compression_policy()` (function) | `add_columnstore_policy()` (procedure) or `add_compression_policy()` |
| Option names | `compress_segmentby`, `compress_orderby` | `segmentby`, `orderby` (shorter aliases) |

Both syntaxes are **aliased** in the with_clause parser — `"compress"`, `"columnstore"`, and `"enable_columnstore"` all map to the same underlying option ([PR #7981](https://github.com/timescale/timescaledb/pull/7981)).

---

## 5. Real-World Migration Patterns (Alembic & Raw SQL)

### Pattern A: Correct SQL Sequence

**Source**: [openmaraude/APITaxi](https://github.com/openmaraude/APITaxi/blob/master/APITaxi_models2/migrations/versions/20230228_11%3A06%3A53_43685d1824b7_activity_logs.py#L33-L37)

```python
op.execute("""
    ALTER TABLE activity_log SET (
        timescaledb.compress,
        timescaledb.compress_segmentby = 'resource, resource_id',
        timescaledb.compress_orderby = 'id DESC,time DESC'
    )
""")
op.execute("SELECT add_compression_policy('activity_log', INTERVAL '7 days')")
op.execute("SELECT add_retention_policy('activity_log', INTERVAL '2 months')")
```

### Pattern B: Using `if_not_exists` for Idempotency

**Source**: [uselotus/lotus](https://github.com/uselotus/lotus/blob/main/backend/metering_billing/aggregation/common_query_templates.py#L10-L16)

```python
CAGG_COMPRESSION = """
ALTER MATERIALIZED VIEW {{ cagg_name }} set (timescaledb.compress = true);
SELECT add_compression_policy(
    '{{ cagg_name }}',
    compress_after=>'33 days'::interval,
    if_not_exists=>true
);
"""
```

### Pattern C: Disable → Enable Cycle for Schema Migrations

**Source**: [jonathan-gtd/scribe](https://github.com/jonathan-gtd/scribe/blob/master/custom_components/scribe/migration.py#L124-L191)

```python
# Disable compression first
await conn.execute("SELECT remove_compression_policy('states_raw', if_exists => true)")
await conn.execute("ALTER TABLE states_raw SET (timescaledb.compress = false)")

# ... do schema changes ...

# Re-enable compression
await conn.execute("""
    ALTER TABLE states_raw SET (
        timescaledb.compress,
        timescaledb.compress_segmentby = 'metadata_id'
    )
""")
await conn.execute(f"SELECT add_compression_policy('states_raw', INTERVAL '{compress_after}')")
```

### Pattern D: Python Library (timescaledb-python)

**Source**: [jmitchel3/timescaledb-python](https://github.com/jmitchel3/timescaledb-python/blob/main/src/timescaledb/compression/sync.py#L22-L25)

```python
def sync_compression_policies(session, *models):
    for model in model_list:
        compress_enabled = model.__enable_compression__
        if not compress_enabled:
            continue
        enable_table_compression(session, model, commit=False)
        add_compression_policy(session, model, commit=False)
```

---

## 6. Prerequisite Requirements for `add_compression_policy` / `add_columnstore_policy`

### The chain of requirements:

| Step | SQL | Purpose |
|---|---|---|
| 1 | `CREATE TABLE` | Create base table |
| 2 | `SELECT create_hypertable(...)` | Convert to hypertable |
| 3 | `ALTER TABLE t SET (timescaledb.compress = true)` | **Enable compression/columnstore** — sets `compression_state = 1` |
| 4 | `SELECT add_compression_policy(...)` | Add automated policy (this is where the check fires) |

If step **3** is skipped or fails to persist (as in the cached function bug), step **4** raises:

```
ERROR: columnstore not enabled on hypertable "..."
HINT: Enable columnstore before adding a columnstore policy.
```

### Safe SQL Sequence (recommended)

```sql
-- Step 1: Create table
CREATE TABLE conditions (
    time TIMESTAMPTZ NOT NULL,
    device_id INT NOT NULL,
    temperature FLOAT
);

-- Step 2: Create hypertable
SELECT create_hypertable('conditions', 'time');

-- Step 3: Enable columnstore with options
ALTER TABLE conditions SET (
    timescaledb.compress = true,
    timescaledb.compress_orderby = 'time DESC',
    timescaledb.compress_segmentby = 'device_id'
);

-- Step 4: Verify compression is enabled
SELECT compression_enabled FROM timescaledb_information.hypertables
WHERE hypertable_name = 'conditions';

-- Step 5: Add compression policy (with if_not_exists for idempotency)
SELECT add_compression_policy('conditions', INTERVAL '7 days', if_not_exists => true);
```

### For Continuous Aggregates

```sql
ALTER MATERIALIZED VIEW my_cagg SET (timescaledb.compress = true);
SELECT add_compression_policy('my_cagg', compress_after => INTERVAL '33 days', if_not_exists => true);
```

### Disable/Re-enable Cycle (for schema changes)

```sql
-- Pause policy
SELECT remove_compression_policy('conditions', if_exists => true);

-- Disable
ALTER TABLE conditions SET (timescaledb.compress = false);

-- ... schema changes ...

-- Re-enable
ALTER TABLE conditions SET (
    timescaledb.compress = true,
    timescaledb.compress_orderby = 'time DESC',
    timescaledb.compress_segmentby = 'device_id'
);

-- Restart policy
SELECT add_compression_policy('conditions', INTERVAL '7 days', if_not_exists => true);
```

---

## 7. Summary

| Question | Answer |
|---|---|
| **Exact error location** | `tsl/src/bgw_policy/compression_api.c`, function `validate_compress_chunks_hypertable()`, line ~380 |
| **What triggers it?** | `add_compression_policy()` or `add_columnstore_policy()` called on a hypertable where `compression_state != 1` |
| **Version where behavior changed** | Bug introduced in 2.21 with columnstore rename; fixed in 2.22 (PRs #8739, #8749) |
| **Prerequisite ALTER needed** | Yes — `ALTER TABLE <ht> SET (timescaledb.compress = true)` or `timescaledb.enable_columnstore = true` |
| **PL/pgSQL caching bug** | Cached function execution strips TimescaleDB-specific ALTER TABLE options on second call (fixed in >= 2.22) |
| **Columnstore aliases** | `compress` / `columnstore` / `enable_columnstore` — all map to the same boolean option |
| **Columnstore option names** | `segmentby` (alias for `compress_segmentby`), `orderby` (alias for `compress_orderby`) |
| **Real-world pattern** | Always pair the ALTER with the policy call; use `if_not_exists => true`; use `remove_compression_policy` before disabling |

---

## References

1. [TimescaleDB Source: compression_api.c](https://github.com/timescale/timescaledb/blob/main/tsl/src/bgw_policy/compression_api.c)
2. [TimescaleDB Source: hypertable.h (compression macro)](https://github.com/timescale/timescaledb/blob/main/src/hypertable.h)
3. [TimescaleDB Source: alter_table_with_clause.c](https://github.com/timescale/timescaledb/blob/main/src/with_clause/alter_table_with_clause.c)
4. [GitHub Issue #8600: Cached function bug](https://github.com/timescale/timescaledb/issues/8600)
5. [TimescaleDB PR #7981: columnstore aliases](https://github.com/timescale/timescaledb/pull/7981)
6. [TimescaleDB SQL API: policy_api.sql](https://github.com/timescale/timescaledb/blob/main/sql/policy_api.sql)
7. [Real-world migration: APITaxi](https://github.com/openmaraude/APITaxi/blob/master/APITaxi_models2/migrations/versions/20230228_11%3A06%3A53_43685d1824b7_activity_logs.py)
8. [Real-world migration: Scribe](https://github.com/jonathan-gtd/scribe/blob/master/custom_components/scribe/migration.py)
9. [Real-world: timescaledb-python library](https://github.com/jmitchel3/timescaledb-python)
10. [TimescaleDB Docs: Altering with Columnstore](https://github.com/timescale/docs/blob/latest/use-timescale/schema-management/alter.md)