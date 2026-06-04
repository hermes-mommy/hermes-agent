# P7-022: Surveillance Data Retention Policies

| Field | Value |
|---|---|
| Step | P7-022 |
| Date | 2026-06-03 |
| Author | Guinevere (Sisyphus-Junior) |
| Status | Active |

---

## 1. Overview

Guinevere's surveillance data retention follows a **3-tier architecture** aligned with
ADR-010 and SurveillanceDataPolicy Section 5 and Section 9:

| Tier | Retention Period | Data Scope | Storage |
|---|---|---|---|
| **Raw** | 7 days | Raw surveillance events | `surveillance.events` hypertable |
| **Aggregated** | 90 days | Continuous aggregates, materialized views | TimescaleDB continuous aggregates |
| **Summary** | 365 days | Curated long-term summaries | PostgreSQL memory tables |

Each tier is enforced through TimescaleDB automated policies: `drop_chunks` for deletion
and `add_compression_policy` for storage optimization.

---

## 2. Raw Events (7 days)

### 2.1 Scope

Raw events are stored in the `surveillance.events` TimescaleDB hypertable. This includes
all ingested surveillance event types: app_usage, screen_state, active_window, idle_time,
notification, browser, location, call_log, health, clipboard, screenshot, and camera.

### 2.2 Retention Enforcement

```sql
SELECT add_retention_policy('surveillance.events',
    INTERVAL '7 days',
    if_not_exists => TRUE
);
```

TimescaleDB's `drop_chunks` background job automatically removes chunks older than
7 days based on the `occurred_at` timestamp column.

### 2.3 Compression

```sql
SELECT add_compression_policy('surveillance.events',
    INTERVAL '7 days',
    if_not_exists => TRUE
);
```

Chunks older than 7 days are compressed before expiry. Only 1 chunk (1 day) is typically
eligible for compression at any given time, since raw retention is also 7 days.

---

## 3. Aggregated Data (90 days)

### 3.1 Scope

Continuous aggregates and materialized views derived from raw surveillance events:

- Hourly event counts by type and classification
- Daily usage patterns (app, screen, idle summaries)
- Location geofence summaries
- Notification category summaries
- Browser domain category summaries

### 3.2 Retention Enforcement

```sql
SELECT add_retention_policy('surveillance.events_hourly',
    INTERVAL '90 days',
    if_not_exists => TRUE
);
```

### 3.3 Refresh Policy

Continuous aggregates are refreshed on a scheduled cadence (default: after every chunk
interval) to incorporate new raw data before the raw chunks are dropped.

---

## 4. Summary Data (365 days)

### 4.1 Scope

Curated long-term summaries promoted to PostgreSQL memory tables:

- Productivity weekly/monthly summaries
- Health trend summaries (post-MVP activation)
- Routine pattern summaries
- Safety/incident evidence summaries (redacted)

### 4.2 Retention Enforcement

Summary data is managed at the application layer through promotion workflows with
explicit `retention_until` timestamps. TimescaleDB drop_chunks is not used for
summary data since it resides in standard PostgreSQL tables.

### 4.3 Do-Not-Recall Compatibility

All promoted summary data must support correction, deletion, do-not-recall marking,
and export as required by SurveillanceDataPolicy Section 12.

---

## 5. Compression Policy

### 5.1 Configuration

| Parameter | Value | Description |
|---|---|---|
| `compress_after` | 7 days | Chunks older than this are compressed |
| `compress_orderby` | `occurred_at DESC` | Optimal ordering for time-series queries |
| `compress_segmentby` | `event_type` | Group compression by event type for efficient filtering |

### 5.2 Implementation

```sql
ALTER TABLE surveillance.events SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'occurred_at DESC',
    timescaledb.compress_segmentby = 'event_type'
);

SELECT add_compression_policy('surveillance.events',
    INTERVAL '7 days',
    if_not_exists => TRUE
);
```

### 5.3 Space Savings

TimescaleDB compression typically achieves 90%+ storage reduction for surveillance
event data due to high columnar redundancy in time-series workloads.

---

## 6. Chunk Configuration

### 6.1 Parameters

| Parameter | Value | Rationale |
|---|---|---|
| `chunk_time_interval` | 1 day | Fine-grained chunking for precise retention slicing |
| `space_partitioning` | None (default) | Single-node deployment; multi-node not required |

### 6.2 Implementation

```sql
SELECT create_hypertable('surveillance.events', 'occurred_at',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);
```

### 6.3 Chunk Lifecycle

```
Day 0         Day 7              Day 8
  |              |                  |
  [chunk created] [compression auto] [drop_chunks auto]
  |              |                  |
  uncompressed   compressed         deleted
```

With 1-day chunks:
- 7 uncompressed chunks exist at any time (days 0-6)
- 1 compressed chunk (day 7) eligible for compression
- Chunks older than 7 days are automatically dropped

---

## 7. Retention Enforcement

### 7.1 Automated Jobs

TimescaleDB runs two automated background jobs per hypertable:

| Job | Function | Schedule | Effect |
|---|---|---|---|
| Retention | `drop_chunks()` | Hourly (default) | Deletes chunks older than retention interval |
| Compression | Internal compression worker | After chunk age > `compress_after` | Compresses eligible chunks |

### 7.2 Verification Queries

Check retention policies in TimescaleDB catalog:

```sql
-- List all retention policies
SELECT hypertable_name, retention_interval, job_id
FROM timescaledb_information.jobs
WHERE proc_name = 'policy_retention';

-- List compression policies
SELECT hypertable_name, compress_after, job_id
FROM timescaledb_information.compression_settings;

-- Check chunk expiration
SELECT chunk_name, range_start, range_end,
       range_end + INTERVAL '7 days' AS expires_at
FROM timescaledb_information.chunks
WHERE hypertable_name = 'events'
ORDER BY range_start DESC
LIMIT 10;
```

### 7.3 Manual Retention Enforcement

```sql
-- Emergency: manually drop raw events older than 7 days
SELECT drop_chunks('surveillance.events',
    older_than => INTERVAL '7 days'
);

-- Manually drop aggregated data older than 90 days
SELECT drop_chunks('surveillance.events_hourly',
    older_than => INTERVAL '90 days'
);
```

---

## 8. Data Classification Impact

The 3-tier retention architecture aligns with Guinevere's data classification levels
(SurveillanceDataPolicy Appendix A and B):

| Classification | Retention Tier | Duration | Example Event Types |
|---|---|---|---|
| Internal | Raw (7d) | Events deleted after 7 days | app_usage, screen_state, active_window, idle_time |
| Confidential | Aggregated (90d) | Summaries retained for 90 days | notification, browser, location, call_log, health |
| Restricted | Summary (365d) | Curated summaries for 365 days | clipboard (secrets dropped), screenshot, camera |

### 8.1 Minute-Need Retention Alignment

The classification module's `get_retention_days(retention_class)` maps:
- `short_raw` and `critical_media` -> 1-7 days (raw tier)
- `medium_operational` -> 90 days (aggregated tier)
- `long_term_curated`, `regulated_audit` -> 365 days (summary tier)
- `formal_hold` -> 730 days (policy-defined hold, not automated)

---

## 9. Compliance References

| Document | Section | Relevance |
|---|---|---|
| ADR-010 | Full | Surveillance data retention policy -- class-based retention, minimization, summarization |
| SurveillanceDataPolicy | Section 5 | Consent boundary and retention interaction |
| SurveillanceDataPolicy | Section 9 | Storage and retention rules, retention classes, enforcement |
| SurveillanceDataPolicy | Appendix B | Retention matrix with raw, summary, and deletion rules |
| DataGovernance Classification | Full | Parent policy for classification, minimization, retention |
| ConsentRevocationPolicy | Full | Revocation interaction with retention and deletion workflows |

---

## 10. Verification Queries

### 10.1 Policy Existence

```sql
SELECT * FROM timescaledb_information.jobs
WHERE application_name LIKE '%Retention%'
   OR application_name LIKE '%Compression%';
```

### 10.2 Chunk Age Distribution

```sql
SELECT
    hypertable_name,
    COUNT(*) AS chunk_count,
    MIN(range_start) AS oldest_chunk_start,
    MAX(range_end) AS newest_chunk_end,
    NOW() - MIN(range_start) AS oldest_chunk_age
FROM timescaledb_information.chunks
WHERE hypertable_name = 'events'
GROUP BY hypertable_name;
```

### 10.3 Compression Status

```sql
SELECT
    hypertable_name,
    compression_enabled,
    total_chunks,
    number_compressed_chunks,
    ROUND(
        CASE WHEN number_compressed_chunks > 0
        THEN 100.0 * number_compressed_chunks / total_chunks
        ELSE 0 END, 1
    ) AS pct_compressed
FROM timescaledb_information.compressed_hypertable_stats
WHERE hypertable_name = 'events';
```

---

## 11. Footer

| Field | Value |
|---|---|
| Version | 1.0 |
| Date | 2026-06-03 |
| Author | Guinevere (Sisyphus-Junior) |
| Review Status | Pending auditor gate |
| Next Review | After TimescaleDB deployment verification |