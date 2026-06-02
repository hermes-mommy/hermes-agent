# Research: TimescaleDB Compression Documentation

> **Source**: TimescaleDB official docs (timescale/docs repo, branch `latest` — archived 2026-04-20)
> **Fetched**: 2026-06-02
> **Purpose**: Extract key information about enabling compression on hypertables

---

## Table of Contents

1. [Page 1: About Compression](#page-1-about-compression)
2. [Page 2: Create a Compression Policy](#page-2-create-a-compression-policy)
3. [Page 3: `add_compression_policy()` API](#page-3-add_compression_policy-api)
4. [Page 4: Manual Compression](#page-4-manual-compression)
5. [Cross-Cutting Findings](#cross-cutting-findings)

---

## Page 1: About Compression

**Original URL**: `https://docs.timescale.com/use-timescale/latest/compression/about-compression/`
**Actual source**: `https://raw.githubusercontent.com/timescale/docs/latest/use-timescale/compression/about-compression.md`

### Deprecation / Version Notes

> **Superseded by hypercore** (since TimescaleDB v2.18.0). However, compression APIs are still supported, you do not need to migrate to the hypercore APIs.

### Is `ALTER TABLE ... SET (timescaledb.compress)` a Required Step?

**YES.** Every compression workflow shown uses `ALTER TABLE ... SET (timescaledb.compress, ...)` as the first step.

### Exact SQL Commands Shown

**1. Basic compression with time ordering only:**
```sql
ALTER TABLE metrics 
SET (timescaledb.compress, timescaledb.compress_orderby='time');
```

**2. Compression with segmentby + orderby (recommended for device-based queries):**
```sql
ALTER TABLE metrics 
SET (
	timescaledb.compress, 
	timescaledb.compress_segmentby='device_id', 
	timescaledb.compress_orderby='time'
);
```

**3. Manual chunk compression (after ALTER TABLE):**
```sql
SELECT compress_chunk(c) FROM show_chunks('metrics') c;
```

The page then demonstrates timing benchmarks showing query speed improvement:
- Without compression: `177,399 ms`
- With compression (segmentby=device_id): `42,139 ms`

### Columnstore Mention

The page says data is "reorganized and stored in **column-order rather than row-order**" when compressed. The term "columnstore" is not used explicitly in this Markdown source, but the rendered page on tigerdata.com references "converting data from the rowstore to the columnstore" in compression algorithm descriptions.

### Compression on Empty Tables

Not explicitly addressed on this page. However, `ALTER TABLE ... SET (timescaledb.compress, ...)` is a metadata/configuration change that sets compression parameters — it does not compress existing data. No actual data is needed to set this.

### Other Key Details

- Segmenting columns should be chosen based on query access patterns (e.g., `device_id`)
- Ordering defaults to `time DESC`; using `time` for ordering improves compression ratios
- Number of rows compressed together in a single batch = **1000** (if chunk doesn't have enough data, compression ratio is reduced)
- Indexes on uncompressed chunks remain; TimescaleDB creates custom indexes for compressed data using `segmentby` and `orderby`

---

## Page 2: Create a Compression Policy

**Original URL**: `https://docs.timescale.com/use-timescale/latest/compression/create-a-compression-policy/`
**Actual source**: `https://raw.githubusercontent.com/timescale/docs/latest/use-timescale/compression/compression-policy.md`
**Note**: The original URL redirects to tigerdata.com and returns 404. The actual file in the docs repo is named `compression-policy.md`.

### Deprecation / Version Notes

> **Superseded by hypercore** (since TimescaleDB v2.18.0). Compression APIs still supported, no migration needed.

### Is `ALTER TABLE ... SET (timescaledb.compress)` a Required Step?

**YES.** Step 1 of the procedure explicitly shows the ALTER TABLE command as a prerequisite before adding the policy.

### Exact SQL Commands Shown

**1. Enable compression on the hypertable (prerequisite):**
```sql
ALTER TABLE example SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'device_id'
);
```

**2. Add automatic compression policy for chunks older than 7 days:**
```sql
SELECT add_compression_policy('example', INTERVAL '7 days');
```

**3. View current compression policies:**
```sql
SELECT * FROM timescaledb_information.jobs
  WHERE proc_name='policy_compression';
```

**4. Pause a compression policy (find job_id first):**
```sql
SELECT * FROM timescaledb_information.jobs where proc_name = 'policy_compression' AND relname = 'example';
SELECT alter_job(<job_id>, scheduled => false);
```

**5. Resume a compression policy:**
```sql
SELECT alter_job(<job_id>, scheduled => true);
```

**6. Remove a compression policy:**
```sql
SELECT remove_compression_policy('example');
```

**7. Disable compression entirely (only if no compressed chunks exist):**
```sql
ALTER TABLE <EXAMPLE> SET (timescaledb.compress=false);
```

### Columnstore Mention

**None** in this page.

### Compression on Empty Tables

Not explicitly addressed. The disable-compression section notes: *"This command works only if you don't currently have any compressed chunks."* If compressed chunks exist, each must be decompressed individually before turning off compression.

---

## Page 3: `add_compression_policy()` API Reference

**Original URL**: `https://docs.timescale.com/api/latest/compression/add_compression_policy/`
**Actual source**: `https://raw.githubusercontent.com/timescale/docs/latest/api/compression/add_compression_policy.md`

### Deprecation / Version Notes

> **Superseded by `add_columnstore_policy()`** (since TimescaleDB v2.18.0). However, compression APIs are still supported, you do not need to migrate to the hypercore APIs.

### Is `ALTER TABLE ... SET (timescaledb.compress)` a Required Step?

**YES — explicitly documented as a prerequisite:**
> "Compression policies can only be created on hypertables or continuous aggregates that **already have compression enabled**. To set `timescaledb.compress` and other configuration parameters for hypertables, use the `ALTER TABLE` command."

### Exact SQL Commands Shown

**1. Basic policy — compress chunks older than 60 days:**
```sql
SELECT add_compression_policy('cpu', compress_after => INTERVAL '60d');
```

**2. Policy using chunk creation time instead of data age:**
```sql
SELECT add_compression_policy('cpu', compress_created_before => INTERVAL '3 months');
```

**3. Policy on hypertable with integer-based time column:**
```sql
SELECT add_compression_policy('table_with_bigint_time', BIGINT '600000');
```

**4. Policy on a continuous aggregate:**
```sql
SELECT add_compression_policy('cpu_weekly', INTERVAL '8 weeks');
```

### Full Function Signature

```sql
add_compression_policy(
  hypertable REGCLASS,
  compress_after INTERVAL or INTEGER,       -- mutually exclusive with compress_created_before
  compress_created_before INTERVAL,          -- mutually exclusive with compress_after; not for continuous aggregates
  schedule_interval INTERVAL,                -- optional; default 12h (if chunk_interval >= 1 day) else chunk_interval/2
  initial_start TIMESTAMPTZ,                 -- optional; default NULL
  timezone TEXT,                              -- optional; default NULL (UTC)
  if_not_exists BOOLEAN                      -- optional; default false (warns instead of errors)
)
```

### Columnstore Mention

The **superseding function** `add_columnstore_policy()` is explicitly named, confirming the hypercore/columnstore rebranding direction.

### Compression on Empty Tables

Not addressed on this page. The policy operates on chunks — if the hypertable has no data/chunks, the policy will run but have nothing to compress.

---

## Page 4: Manual Compression

**Original URL**: `https://docs.timescale.com/use-timescale/latest/compression/manual-compression/`
**Actual source**: `https://raw.githubusercontent.com/timescale/docs/latest/use-timescale/compression/manual-compression.md`

### Deprecation / Version Notes

No explicit deprecation banner in this file (the feature banner is inherited from the parent compression docs).

### Is `ALTER TABLE ... SET (timescaledb.compress)` a Required Step?

**YES — assumed as prerequisite.** The manual compression procedure starts by selecting chunks via `show_chunks()`, then calling `compress_chunk()`. Compression must already be enabled via `ALTER TABLE ... SET (timescaledb.compress, ...)` before these steps.

### Exact SQL Commands Shown

**1. List chunks older than 3 days:**
```sql
SELECT show_chunks('example', older_than => INTERVAL '3 days');
```

**2. Manually compress a specific chunk:**
```sql
SELECT compress_chunk('<chunk_name>');
```

**3. Check compression stats:**
```sql
SELECT *
FROM chunk_compression_stats('example');
```

**4. Compress all chunks between 1 and 3 weeks old in one command:**
```sql
SELECT compress_chunk(i, if_not_compressed => true)
    FROM show_chunks(
        'example',
        now()::timestamp - INTERVAL '1 week',
        now()::timestamp - INTERVAL '3 weeks'
    ) i;
```

**5. Roll up uncompressed chunks (v2.9+):**
```sql
ALTER TABLE example SET (timescaledb.compress_chunk_time_interval = '<time_interval>',
                            timescaledb.compress_orderby = 'time ASC');
SELECT compress_chunk(c, if_not_compressed => true)
    FROM show_chunks(
        'example',
        now()::timestamp - INTERVAL '1 week'
    ) c;
```

### Columnstore Mention

**None** in this page.

### Compression on Empty Tables

Not addressed. The procedure assumes chunks already exist (uses `show_chunks()` to find them). An empty hypertable with no data has no chunks, so `compress_chunk()` would have nothing to operate on.

### Other Key Details

- Chunk rollup (v2.9+): multiple uncompressed chunks can be merged into a single compressed chunk
- Recommended to set `timescaledb.compress_orderby = 'time ASC'` during rollup to avoid performance penalty from repeated re-compression
- The `compress_chunk_time_interval` must be a **multiple** of the uncompressed chunk interval

---

## Cross-Cutting Findings

### 1. Deprecation Status (v2.18.0+)

| Aspect | Status |
|---|---|
| Compression APIs (legacy) | Still supported, no migration required |
| Hypercore (new) | Supersedes compression; uses `add_columnstore_policy()` instead of `add_compression_policy()` |
| Docs repo | Archived 2026-04-20 (read-only) |

### 2. Required Workflow to Enable Compression

```
Step 1: ALTER TABLE ... SET (timescaledb.compress, ...)   -- enable + configure
Step 2a: SELECT add_compression_policy(...)                 -- automatic policy (OR)
Step 2b: SELECT compress_chunk(...)                         -- manual compression
```

**`ALTER TABLE ... SET (timescaledb.compress)` IS a required step** — confirmed across all pages.

### 3. Columnstore Mentions

- The term **"columnstore"** is used in the hypercore documentation (the successor) and in the compression algorithm descriptions (rowstore → columnstore conversion).
- The legacy compression docs describe data as "stored in **column-order rather than row-order**" — functionally equivalent to columnstore.
- The superseding API is explicitly named `add_columnstore_policy()`.

### 4. Compression on Empty Tables

**Not explicitly documented** in any of the four pages. Inferred behavior:
- `ALTER TABLE ... SET (timescaledb.compress, ...)` is a metadata/configuration operation — it should work on empty hypertables.
- `compress_chunk()` requires existing chunks — an empty hypertable has none.
- `add_compression_policy()` schedules a background job — it will run but have nothing to compress on an empty table.

### 5. Compression Algorithms (from about-compression page)

| Data Type | Algorithm(s) |
|---|---|
| Integers, timestamps, booleans | Delta encoding → Delta-of-delta → Simple-8b → Run-length encoding |
| Floating point (non-repeating) | XOR-based compression (Gorilla-derived) |
| All other types (strings, etc.) | Dictionary compression |
| JSONB | Dictionary compression → PostgreSQL TOAST (pglz or lz4) |

### 6. Key Constraints

- Compression can only be enabled on **hypertables** (not regular PostgreSQL tables)
- A chunk needs at least **1000 rows** per batch for good compression ratios
- Disabling compression requires **no compressed chunks** exist (each must be decompressed first)
- Indexes on compressed chunks use custom TimescaleDB indexes based on `segmentby`/`orderby`, not original indexes
- `compress_after` and `compress_created_before` are **mutually exclusive** in `add_compression_policy()`