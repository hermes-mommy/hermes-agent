# TimescaleDB Production Patterns for Surveillance Data Pipeline

> **Scope**: Python/FastAPI + asyncpg async worker consuming from Redis buffer → TimescaleDB hypertables
> **Data types**: app_usage, gps_location, notifications, clipboard, health_metrics
> **Retention**: 7-day raw → 90-day aggregated → 1-year summaries
> **Date**: 2026-06-02

---

## 1. Hypertable Schema Design

### 1.1 Official TimescaleDB Pattern — Segment by Query Dimension

**Evidence** ([TimescaleDB official](https://github.com/timescale/timescaledb/blob/ceb5eec5bff5f125954c18b6ce96188cd5043b1c/docs/getting-started/financial-ticks/README.md)):

```sql
CREATE TABLE stock_prices (
  ts                TIMESTAMPTZ         NOT NULL,
  ticker            TEXT                NOT NULL,
  price             DOUBLE PRECISION    NOT NULL,
  change_delta      DOUBLE PRECISION    NOT NULL,
  change_percentage DOUBLE PRECISION    NOT NULL,
  volume            BIGINT NOT NULL CHECK (volume >= 0)
)
WITH (
  timescaledb.hypertable,
  timescaledb.segmentby='ticker'
);
```

### 1.2 Recommended Guinevere Schema

```sql
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

CREATE TABLE surveillance_events (
    time            TIMESTAMPTZ     NOT NULL,
    event_id        UUID            NOT NULL DEFAULT gen_random_uuid(),
    event_type      VARCHAR(30)     NOT NULL,
    subject_id      UUID            NOT NULL,
    device_id       UUID,
    metadata        JSONB,
    latitude        DOUBLE PRECISION,
    longitude       DOUBLE PRECISION,
    altitude        DOUBLE PRECISION,
    accuracy_m      DOUBLE PRECISION,
    app_package     VARCHAR(255),
    app_name        VARCHAR(255),
    screen_time_s   INTEGER,
    notification_title TEXT,
    notification_body  TEXT,
    notification_app   VARCHAR(255),
    heart_rate      SMALLINT,
    steps           INTEGER,
    calories        DOUBLE PRECISION,
    clipboard_text  TEXT,
    ingested_at     TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    batch_id        UUID,
    PRIMARY KEY (time, event_id)
);

SELECT create_hypertable(
    'surveillance_events', 'time',
    chunk_time_interval => INTERVAL '1 day'
);

CREATE INDEX idx_surv_subject_time
    ON surveillance_events (subject_id, time DESC);
CREATE INDEX idx_surv_device_time
    ON surveillance_events (device_id, time DESC);
CREATE INDEX idx_surv_type_time
    ON surveillance_events (event_type, time DESC);
CREATE INDEX idx_surv_metadata_gin
    ON surveillance_events USING GIN (metadata);
```

### 1.3 Chunk Interval Sizing

**Official guidance** ([Timescale docs](https://docs.timescale.com/use-timescale/latest/hypertables/change-chunk-intervals/)):

> Set `chunk_interval` so that the indexes for chunks currently being ingested into fit within **25% of main memory** (`shared_buffers`).

| Daily Data Volume | Chunk Interval | Rationale |
|---|---|---|
| < 1 GB/day | `INTERVAL '7 days'` | Default. Chunks ~7 GB, fits in 32 GB shared_buffers |
| 1–5 GB/day | `INTERVAL '1 day'` | Active chunk ~1-5 GB, fits in 16-32 GB |
| 5–20 GB/day | `INTERVAL '12 hours'` | Keeps active chunk under 10 GB |
| > 20 GB/day | `INTERVAL '1 hour'` | Extreme throughput, requires careful tuning |

**For Guinevere**: ~10k-100k events/day = ~50-500 MB/day uncompressed. **`INTERVAL '1 day'` is optimal** — small enough for fast retention drops, large enough for efficient compression.

---

## 2. Compression Policies

### 2.1 Production Patterns

**Evidence** ([logtide-dev production](https://github.com/logtide-dev/logtide/blob/e4c314c0818cc2d58270d7912cb352516514ba4f/packages/backend/migrations/034_service_health_monitoring.sql#L108-L112)):

```sql
ALTER TABLE monitor_results SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'monitor_id',
  timescaledb.compress_orderby = 'time DESC'
);
SELECT add_compression_policy('monitor_results', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_retention_policy('monitor_results', INTERVAL '30 days', if_not_exists => TRUE);
```

**Evidence** ([TimescaleDB test suite](https://github.com/timescale/timescaledb/blob/ceb5eec5bff5f125954c18b6ce96188cd5043b1c/tsl/test/sql/compression_qualpushdown.sql#L13-L16)):

```sql
ALTER TABLE hyper SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'time',
    timescaledb.compress_segmentby = 'device_id');
```

### 2.2 Guinevere Compression Setup

```sql
ALTER TABLE surveillance_events SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'subject_id, event_type',
    timescaledb.compress_orderby = 'time DESC'
);

SELECT add_compression_policy(
    'surveillance_events', INTERVAL '2 days', if_not_exists => TRUE
);
```

| Setting | Value | Rationale |
|---|---|---|
| `compress_segmentby` | `subject_id, event_type` | Most queries filter by subject and event type |
| `compress_orderby` | `time DESC` | Surveillance queries want most-recent first |
| Compression after | 2 days | Keeps today + yesterday uncompressed for fast writes |

---

## 3. Retention Policy — Tiered Architecture

### 3.1 Three-Tier Retention

```
Tier 1: RAW (7 days)      → surveillance_events hypertable
Tier 2: HOURLY (90 days)  → continuous aggregate materialized view
Tier 3: DAILY (1 year)    → separate hypertable with own retention
```

**Evidence** ([TimescaleDB tests](https://github.com/timescale/timescaledb/blob/ceb5eec5bff5f125954c18b6ce96188cd5043b1c/tsl/test/sql/bgw_policy.sql)):

```sql
SELECT add_retention_policy('test_strict', interval '2 days', schedule_interval => NULL);
SELECT add_compression_policy('test_strict', INTERVAL '2 weeks', schedule_interval => NULL);
```

**Evidence** ([FreePeak production](https://github.com/FreePeak/db-mcp-server/blob/2215835a29f8a75bbba9bdd4de19c03a1f0e4916/init-scripts/timescaledb/03-continuous-aggregates.sql#L95-L102)):

```sql
SELECT add_compression_policy('test_data.sensor_readings', INTERVAL '7 days');
SELECT add_compression_policy('test_data.weather_observations', INTERVAL '30 days');
SELECT add_compression_policy('test_data.device_metrics', INTERVAL '3 days');
SELECT add_retention_policy('test_data.sensor_readings', INTERVAL '90 days');
SELECT add_retention_policy('test_data.device_metrics', INTERVAL '30 days');
```

### 3.2 Guinevere Retention Policies

```sql
-- TIER 1: Raw events — 7 day retention
SELECT add_retention_policy(
    'surveillance_events', INTERVAL '7 days', if_not_exists => TRUE
);

-- TIER 2: Hourly aggregates table with 90 day retention
CREATE TABLE surveillance_hourly (
    bucket          TIMESTAMPTZ     NOT NULL,
    subject_id      UUID            NOT NULL,
    event_type      VARCHAR(30)     NOT NULL,
    event_count     BIGINT          NOT NULL,
    avg_latitude    DOUBLE PRECISION,
    avg_longitude   DOUBLE PRECISION,
    total_distance_m DOUBLE PRECISION,
    total_screen_time_s BIGINT,
    unique_apps     INTEGER,
    avg_heart_rate  DOUBLE PRECISION,
    max_heart_rate  SMALLINT,
    total_steps     INTEGER,
    total_calories  DOUBLE PRECISION,
    notification_count INTEGER,
    first_seen      TIMESTAMPTZ,
    last_seen       TIMESTAMPTZ,
    PRIMARY KEY (bucket, subject_id, event_type)
);

SELECT create_hypertable(
    'surveillance_hourly', 'bucket',
    chunk_time_interval => INTERVAL '7 days'
);

ALTER TABLE surveillance_hourly SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'subject_id, event_type',
    timescaledb.compress_orderby = 'bucket DESC'
);

SELECT add_compression_policy('surveillance_hourly', INTERVAL '14 days', if_not_exists => TRUE);
SELECT add_retention_policy('surveillance_hourly', INTERVAL '90 days', if_not_exists => TRUE);

-- TIER 3: Daily summaries with 1 year retention
CREATE TABLE surveillance_daily (
    bucket          TIMESTAMPTZ     NOT NULL,
    subject_id      UUID            NOT NULL,
    event_type      VARCHAR(30)     NOT NULL,
    event_count     BIGINT          NOT NULL,
    total_distance_m DOUBLE PRECISION,
    home_latitude   DOUBLE PRECISION,
    home_longitude  DOUBLE PRECISION,
    unique_locations INTEGER,
    total_screen_time_s BIGINT,
    top_apps        JSONB,
    avg_heart_rate  DOUBLE PRECISION,
    resting_heart_rate SMALLINT,
    total_steps     INTEGER,
    total_calories  DOUBLE PRECISION,
    sleep_hours     DOUBLE PRECISION,
    notification_count INTEGER,
    active_hours    INTEGER,
    PRIMARY KEY (bucket, subject_id, event_type)
);

SELECT create_hypertable(
    'surveillance_daily', 'bucket',
    chunk_time_interval => INTERVAL '30 days'
);

ALTER TABLE surveillance_daily SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'subject_id, event_type',
    timescaledb.compress_orderby = 'bucket DESC'
);

SELECT add_compression_policy('surveillance_daily', INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_retention_policy('surveillance_daily', INTERVAL '365 days', if_not_exists => TRUE);
```

---

## 4. Continuous Aggregates for Downsampling

### 4.1 Official Pattern

**Evidence** ([TimescaleDB events tutorial](https://github.com/timescale/timescaledb/blob/ceb5eec5bff5f125954c18b6ce96188cd5043b1c/docs/getting-started/events-uuidv7/README.md)):

```sql
CREATE MATERIALIZED VIEW app_events_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', uuid_timestamp(event_id)) AS hour,
    event_type,
    COUNT(*) as event_count,
    COUNT(DISTINCT user_id) as unique_users,
    SUM(revenue_cents) / 100.0 as total_revenue
FROM app_events
GROUP BY hour, event_type;

SELECT add_continuous_aggregate_policy('app_events_hourly',
    start_offset => INTERVAL '2 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');
```

**Evidence** ([logtide-dev production](https://github.com/logtide-dev/logtide/blob/e4c314c0818cc2d58270d7912cb352516514ba4f/packages/backend/migrations/034_service_health_monitoring.sql#L118-L140)):

```sql
CREATE MATERIALIZED VIEW IF NOT EXISTS monitor_uptime_daily
WITH (timescaledb.continuous, timescaledb.materialized_only = false) AS
SELECT
  time_bucket('1 day', time) AS bucket,
  monitor_id, organization_id, project_id,
  COUNT(*) AS total_checks,
  COUNT(*) FILTER (WHERE status = 'up') AS successful_checks,
  ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'up') / NULLIF(COUNT(*), 0), 2) AS uptime_pct
FROM monitor_results
GROUP BY bucket, monitor_id, organization_id, project_id
WITH NO DATA;
```

### 4.2 Guinevere Continuous Aggregates

```sql
-- HOURLY AGGREGATE: Raw → Hourly (feeds Tier 2)
CREATE MATERIALIZED VIEW surveillance_hourly_agg
WITH (timescaledb.continuous, timescaledb.materialized_only = false) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    subject_id, event_type,
    COUNT(*)::BIGINT AS event_count,
    AVG(latitude) AS avg_latitude,
    AVG(longitude) AS avg_longitude,
    SUM(COALESCE(screen_time_s, 0))::BIGINT AS total_screen_time_s,
    COUNT(DISTINCT app_package)::INTEGER AS unique_apps,
    AVG(heart_rate)::DOUBLE PRECISION AS avg_heart_rate,
    MAX(heart_rate)::SMALLINT AS max_heart_rate,
    SUM(COALESCE(steps, 0))::INTEGER AS total_steps,
    SUM(COALESCE(calories, 0))::DOUBLE PRECISION AS total_calories,
    COUNT(*) FILTER (WHERE event_type = 'notification')::INTEGER AS notification_count,
    MIN(time) AS first_seen,
    MAX(time) AS last_seen
FROM surveillance_events
GROUP BY bucket, subject_id, event_type
WITH NO DATA;

SELECT add_continuous_aggregate_policy('surveillance_hourly_agg',
    start_offset    => INTERVAL '4 hours',
    end_offset      => INTERVAL '5 minutes',
    schedule_interval => INTERVAL '15 minutes',
    if_not_exists   => TRUE
);

ALTER MATERIALIZED VIEW surveillance_hourly_agg SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'subject_id, event_type',
    timescaledb.compress_orderby = 'bucket DESC'
);

SELECT add_compression_policy('surveillance_hourly_agg', INTERVAL '14 days', if_not_exists => TRUE);

-- DAILY AGGREGATE: Hourly → Daily (feeds Tier 3)
CREATE MATERIALIZED VIEW surveillance_daily_agg
WITH (timescaledb.continuous, timescaledb.materialized_only = false) AS
SELECT
    time_bucket('1 day', time) AS bucket,
    subject_id, event_type,
    COUNT(*)::BIGINT AS event_count,
    SUM(COALESCE(screen_time_s, 0))::BIGINT AS total_screen_time_s,
    AVG(heart_rate)::DOUBLE PRECISION AS avg_heart_rate,
    MIN(heart_rate)::SMALLINT AS resting_heart_rate,
    SUM(COALESCE(steps, 0))::INTEGER AS total_steps,
    SUM(COALESCE(calories, 0))::DOUBLE PRECISION AS total_calories,
    COUNT(*) FILTER (WHERE event_type = 'notification')::INTEGER AS notification_count,
    COUNT(DISTINCT time_bucket('1 hour', time))::INTEGER AS active_hours
FROM surveillance_events
GROUP BY bucket, subject_id, event_type
WITH NO DATA;

SELECT add_continuous_aggregate_policy('surveillance_daily_agg',
    start_offset    => INTERVAL '3 days',
    end_offset      => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 day',
    if_not_exists   => TRUE
);

ALTER MATERIALIZED VIEW surveillance_daily_agg SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'subject_id, event_type',
    timescaledb.compress_orderby = 'bucket DESC'
);

SELECT add_compression_policy('surveillance_daily_agg', INTERVAL '30 days', if_not_exists => TRUE);
```

### 4.3 Continuous Aggregate Policy Tuning

| Parameter | Hourly | Daily | Rationale |
|---|---|---|---|
| `start_offset` | 4 hours | 3 days | Buffer for late-arriving events from Redis |
| `end_offset` | 5 minutes | 1 hour | Avoid refreshing incomplete windows |
| `schedule_interval` | 15 minutes | 1 day | 4x/hr near-realtime; daily once/day |
| `materialized_only` | false | false | Real-time queries include unmaterialized recent data |

---

## 5. Python Async Ingestion — Redis Buffer → TimescaleDB

### 5.1 High-Performance COPY Protocol (Recommended)

**Evidence** ([asyncpg source](https://github.com/MagicStack/asyncpg/blob/db8ecc2a38e16fb0c090aef6f5506547c2831c24/asyncpg/connection.py#L1023-L1065)):

```python
# asyncpg native COPY — fastest possible insert path
# Uses PostgreSQL binary COPY protocol, bypasses query parser
await con.copy_records_to_table(
    'mytable', records=[
        (1, 'foo', 'bar'),
        (2, 'ham', 'spam')
    ]
)
```

**Evidence** ([vectorize-io/hindsight production](https://github.com/vectorize-io/hindsight/blob/main/hindsight-api-slim/hindsight_api/engine/db/postgresql.py#L49-L58)):

```python
async def copy_records_to_table(
    self, table_name: str, *,
    records: list[tuple[Any, ...]],
    columns: list[str],
    timeout: float | None = None,
) -> None:
    """Use asyncpg's native COPY for fast bulk loading."""
    await self._conn.copy_records_to_table(
        table_name, records=records, columns=columns, timeout=timeout
    )
```

**Evidence** ([ActorCloud production](https://github.com/actorcloud/ActorCloud/blob/master/server/actor_libs/database/async_db/base.py#L82-L105)):

```python
# Production pattern: bounded deque + batch COPY
deque_length = deque_length if deque_length <= 5000 else 5000
records = (deque.popleft() for _ in range(0, deque_length))
await self.copy_records_to_table(
    table_name, records=records, columns=columns
)
```

### 5.2 Complete Async Worker Implementation

```python
"""
surveillance_worker.py — Redis buffer → TimescaleDB async ingestion worker
Architecture:
  API writes events to Redis list (LPUSH)
  Worker polls Redis (RPOPLPUSH to processing list for reliability)
  Batches events and bulk-inserts via asyncpg COPY protocol
"""
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any
import asyncpg
import orjson
import redis.asyncio as redis

logger = logging.getLogger(__name__)

REDIS_KEY = "surveillance:events:pending"
REDIS_PROCESSING_KEY = "surveillance:events:processing"
BATCH_SIZE = 1000
BATCH_TIMEOUT_S = 2.0
POLL_INTERVAL_S = 0.1
MAX_RETRIES = 3
DLQ_KEY = "surveillance:events:dead_letter"

COLUMNS = [
    "time", "event_id", "event_type", "subject_id", "device_id",
    "metadata", "latitude", "longitude", "altitude", "accuracy_m",
    "app_package", "app_name", "screen_time_s",
    "notification_title", "notification_body", "notification_app",
    "heart_rate", "steps", "calories",
    "clipboard_text", "ingested_at", "batch_id",
]


class SurveillanceIngestor:
    """High-throughput async worker: Redis → TimescaleDB via COPY protocol."""

    def __init__(self, redis_url: str, pg_dsn: str,
                 batch_size: int = BATCH_SIZE,
                 batch_timeout: float = BATCH_TIMEOUT_S):
        self.redis_url = redis_url
        self.pg_dsn = pg_dsn
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self._running = False
        self._stats = {"ingested": 0, "failed": 0, "batches": 0}

    async def start(self) -> None:
        self._running = True
        self._redis = redis.from_url(self.redis_url, decode_responses=True)
        self._pool = await asyncpg.create_pool(
            self.pg_dsn, min_size=2, max_size=10, command_timeout=60,
            server_settings={"jit": "off"},
        )
        logger.info("SurveillanceIngestor started (batch_size=%d)", self.batch_size)
        try:
            await self._ingestion_loop()
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        self._running = False
        if hasattr(self, "_pool"):
            await self._pool.close()
        if hasattr(self, "_redis"):
            await self._redis.aclose()
        logger.info("SurveillanceIngestor shut down. Stats: %s", self._stats)

    async def _ingestion_loop(self) -> None:
        while self._running:
            batch = await self._collect_batch()
            if batch:
                await self._flush_batch(batch)

    async def _collect_batch(self) -> list[tuple]:
        records: list[tuple] = []
        deadline = asyncio.get_event_loop().time() + self.batch_timeout
        while len(records) < self.batch_size:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                break
            try:
                raw = await self._redis.rpoplpush(REDIS_KEY, REDIS_PROCESSING_KEY)
                if raw is None:
                    await asyncio.sleep(min(POLL_INTERVAL_S, remaining))
                    continue
                record = self._parse_event(raw)
                if record is not None:
                    records.append(record)
            except redis.RedisError as e:
                logger.error("Redis error during batch collection: %s", e)
                await asyncio.sleep(1.0)
                break
        return records

    def _parse_event(self, raw_json: str) -> tuple | None:
        try:
            event = orjson.loads(raw_json)
            return (
                datetime.fromisoformat(event["time"]),
                uuid.UUID(event.get("event_id", str(uuid.uuid4()))),
                event["event_type"],
                uuid.UUID(event["subject_id"]),
                uuid.UUID(event["device_id"]) if event.get("device_id") else None,
                orjson.dumps(event.get("metadata", {})),
                event.get("latitude"), event.get("longitude"),
                event.get("altitude"), event.get("accuracy_m"),
                event.get("app_package"), event.get("app_name"),
                event.get("screen_time_s"),
                event.get("notification_title"),
                event.get("notification_body"),
                event.get("notification_app"),
                event.get("heart_rate"), event.get("steps"),
                event.get("calories"), event.get("clipboard_text"),
                datetime.now(timezone.utc),
                uuid.uuid4(),
            )
        except (KeyError, ValueError, TypeError) as e:
            logger.warning("Failed to parse event: %s", e)
            return None

    async def _flush_batch(self, records: list[tuple]) -> None:
        batch_id = records[0][-1]
        for attempt in range(MAX_RETRIES):
            try:
                async with self._pool.acquire() as conn:
                    async with conn.transaction():
                        await conn.copy_records_to_table(
                            "surveillance_events",
                            records=records, columns=COLUMNS, timeout=30.0,
                        )
                        pipe = self._redis.pipeline()
                        for _ in records:
                            pipe.rpop(REDIS_PROCESSING_KEY)
                        await pipe.execute()
                self._stats["ingested"] += len(records)
                self._stats["batches"] += 1
                logger.debug("Flushed batch %s: %d events", batch_id, len(records))
                return
            except asyncpg.exceptions.UniqueViolationError:
                logger.warning("Duplicate in batch %s, fallback to individual", batch_id)
                await self._flush_individual(records)
                return
            except (asyncpg.PostgresError, asyncio.TimeoutError) as e:
                if attempt < MAX_RETRIES - 1:
                    backoff = 2 ** attempt
                    logger.warning("Batch %s attempt %d failed: %s, retry in %ds",
                                   batch_id, attempt + 1, e, backoff)
                    await asyncio.sleep(backoff)
                else:
                    logger.error("Batch %s failed after %d attempts, DLQ",
                                 batch_id, MAX_RETRIES)
                    await self._send_to_dlq(records, str(e))
                    self._stats["failed"] += len(records)

    async def _flush_individual(self, records: list[tuple]) -> None:
        async with self._pool.acquire() as conn:
            ph = ", ".join(f"${i+1}" for i in range(len(COLUMNS)))
            query = ("INSERT INTO surveillance_events "
                     "({cols}) VALUES ({ph}) "
                     "ON CONFLICT (time, event_id) DO NOTHING").format(
                         cols=", ".join(COLUMNS), ph=ph)
            await conn.executemany(query, records)
        pipe = self._redis.pipeline()
        for _ in records:
            pipe.rpop(REDIS_PROCESSING_KEY)
        await pipe.execute()
        self._stats["ingested"] += len(records)

    async def _send_to_dlq(self, records: list[tuple], error: str) -> None:
        pipe = self._redis.pipeline()
        for record in records:
            dlq_entry = orjson.dumps({
                "error": error,
                "event_id": str(record[1]),
                "event_type": record[2],
                "time": record[0].isoformat(),
            }).decode()
            pipe.lpush(DLQ_KEY, dlq_entry)
        await pipe.execute()
```

### 5.3 Alternative: `executemany` for ON CONFLICT Support

**Evidence** ([SpecterOps/Nemesis production](https://github.com/SpecterOps/Nemesis/blob/main/libs/chromium/chromium/history.py#L84-L97)):

```python
async with asyncpg_pool.acquire() as conn:
    insert_sql = """
        INSERT INTO chromium.history
        (originating_object_id, agent_id, source, project, username, browser,
         url, title, visit_count, last_visit_time)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        ON CONFLICT (source, username, browser, url, title, last_visit_time)
        DO UPDATE SET
            url = EXCLUDED.url,
            title = EXCLUDED.title,
            visit_count = EXCLUDED.visit_count,
            last_visit_time = EXCLUDED.last_visit_time
    """
    await conn.executemany(insert_sql, urls_data)
```

### 5.4 Performance Comparison

| Method | Throughput | ON CONFLICT | Use Case |
|---|---|---|---|
| `copy_records_to_table` | ~500k-1M rows/s | No | Bulk append-only ingestion |
| `executemany` | ~10k-50k rows/s | Yes | Deduplication, upserts |
| `execute` (single INSERT) | ~1k-5k rows/s | Yes | Individual event writes |
| COPY with `enable_direct_compress_copy` | Variable | No | Direct-to-columnstore |

**Recommendation**: Use `copy_records_to_table` as primary path. Fall back to `executemany` with `ON CONFLICT DO NOTHING` only for duplicate handling.

---

## 6. FastAPI Integration — Lifespan Worker Management

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from surveillance_worker import SurveillanceIngestor

ingestor: SurveillanceIngestor | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global ingestor
    ingestor = SurveillanceIngestor(
        redis_url="redis://localhost:6379/0",
        pg_dsn="postgresql://user:pass@localhost:5432/guinevere",
    )
    task = asyncio.create_task(ingestor.start())
    yield
    if ingestor:
        await ingestor.shutdown()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)
```

---

## 7. Monitoring and Observability Queries

```sql
-- Check chunk count and sizes
SELECT * FROM timescaledb_information.chunks
WHERE hypertable_name = 'surveillance_events'
ORDER BY range_start DESC LIMIT 10;

-- Check compression status per chunk
SELECT chunk_name, range_start, range_end, is_compressed,
    pg_size_pretty(pg_total_relation_size(
        (chunk_schema || '.' || chunk_name)::regclass
    )) AS total_size
FROM timescaledb_information.chunks
WHERE hypertable_name = 'surveillance_events'
ORDER BY range_start DESC;

-- Check continuous aggregate refresh status
SELECT * FROM timescaledb_information.continuous_aggregates;
SELECT * FROM timescaledb_information.jobs
WHERE application_name LIKE 'Refresh Continuous%';

-- Check retention policy job status
SELECT * FROM timescaledb_information.jobs WHERE proc_name = 'policy_retention';

-- Capacity planning
SELECT * FROM chunks_detailed_size('surveillance_events')
ORDER BY range_start DESC LIMIT 20;
```

---

## 8. Complete Migration Script

Combine all sections above into a single migration file. Execution order:

1. Create extensions (`timescaledb`, `uuid-ossp`)
2. Create `surveillance_events` hypertable with 1-day chunks
3. Create indexes on `subject_id`, `device_id`, `event_type`, `metadata`
4. Configure compression: segmentby `subject_id, event_type`, orderby `time DESC`
5. Add compression policy (2 days) + retention policy (7 days)
6. Create `surveillance_hourly` table + hypertable + compression + retention (90 days)
7. Create `surveillance_daily` table + hypertable + compression + retention (365 days)
8. Create `surveillance_hourly_agg` continuous aggregate + refresh policy (15 min)
9. Create `surveillance_daily_agg` continuous aggregate + refresh policy (1 day)

---

## Sources

| Source | Type | Permalink |
|---|---|---|
| timescale/timescaledb | Official repo | [commit ceb5eec](https://github.com/timescale/timescaledb/commit/ceb5eec5bff5f125954c18b6ce96188cd5043b1c) |
| MagicStack/asyncpg | asyncpg COPY protocol | [connection.py#L1023](https://github.com/MagicStack/asyncpg/blob/db8ecc2a38e16fb0c090aef6f5506547c2831c24/asyncpg/connection.py#L1023) |
| logtide-dev/logtide | Production migration | [034 migration](https://github.com/logtide-dev/logtide/blob/e4c314c0818cc2d58270d7912cb352516514ba4f/packages/backend/migrations/034_service_health_monitoring.sql) |
| FreePeak/db-mcp-server | Production aggregates | [03-continuous-aggregates](https://github.com/FreePeak/db-mcp-server/blob/2215835a29f8a75bbba9bdd4de19c03a1f0e4916/init-scripts/timescaledb/03-continuous-aggregates.sql) |
| Timescale docs | Chunk sizing | [docs.timescale.com](https://docs.timescale.com/use-timescale/latest/hypertables/change-chunk-intervals/) |
| vectorize-io/hindsight | Production COPY wrapper | [postgresql.py](https://github.com/vectorize-io/hindsight/blob/main/hindsight-api-slim/hindsight_api/engine/db/postgresql.py) |
| actorcloud/ActorCloud | Production batch COPY | [base.py](https://github.com/actorcloud/ActorCloud/blob/master/server/actor_libs/database/async_db/base.py) |
| SpecterOps/Nemesis | Production executemany | [history.py](https://github.com/SpecterOps/Nemesis/blob/main/libs/chromium/chromium/history.py) |
