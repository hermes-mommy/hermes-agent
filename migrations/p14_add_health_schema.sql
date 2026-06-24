-- =============================================================================
-- P14-001: Health schema and hypertables migration
-- =============================================================================
-- Purpose: Create health schema, hypertables, analysis tables, continuous
--          aggregates, indexes, and retention policies for health telemetry.
--
-- Execution:
--   docker exec -i guinevere-postgres psql -U guinevere -d guinevere \
--     < migrations/p14_add_health_schema.sql
--
-- Idempotent: YES (all operations use IF NOT EXISTS or if_not_exists => TRUE)
--
-- Author: Guinevere (P14-001 Migration)
-- Date: 2026-06-18
-- Chunk interval: 1 day
-- Retention: 365 days for health data; 730 days for anomaly_events
-- =============================================================================

BEGIN;

-- =============================================================================
-- §1: Create schema
-- =============================================================================
CREATE SCHEMA IF NOT EXISTS health;

-- =============================================================================
-- §2: Create hypertables
-- =============================================================================
-- health.heart_rate
CREATE TABLE IF NOT EXISTS health.heart_rate (
    time        TIMESTAMPTZ NOT NULL,
    device_id   UUID NOT NULL,
    bpm         SMALLINT NOT NULL,
    resting_bpm SMALLINT,
    source      TEXT DEFAULT 'mi_fitness_cloud',
    confidence  FLOAT DEFAULT 1.0,
    owner_id    UUID NOT NULL
);
SELECT create_hypertable('health.heart_rate', 'time', if_not_exists => TRUE);
CREATE UNIQUE INDEX IF NOT EXISTS uq_heart_rate ON health.heart_rate (time, device_id, owner_id);

-- health.daily_activity
CREATE TABLE IF NOT EXISTS health.daily_activity (
    date        DATE NOT NULL,
    steps       INT,
    active_min  INT,
    calories    INT,
    distance_m  FLOAT,
    source      TEXT DEFAULT 'mi_fitness_cloud',
    device_id   UUID NOT NULL,
    owner_id    UUID NOT NULL,
    PRIMARY KEY (date, device_id, owner_id)
);
SELECT create_hypertable('health.daily_activity', 'date', if_not_exists => TRUE);

-- health.spo2
CREATE TABLE IF NOT EXISTS health.spo2 (
    time        TIMESTAMPTZ NOT NULL,
    device_id   UUID NOT NULL,
    spo2_pct    FLOAT NOT NULL,
    source      TEXT DEFAULT 'mi_fitness_cloud',
    owner_id    UUID NOT NULL
);
SELECT create_hypertable('health.spo2', 'time', if_not_exists => TRUE);

-- health.stress
CREATE TABLE IF NOT EXISTS health.stress (
    time        TIMESTAMPTZ NOT NULL,
    device_id   UUID NOT NULL,
    score       SMALLINT NOT NULL,
    source      TEXT DEFAULT 'mi_fitness_cloud',
    owner_id    UUID NOT NULL
);
SELECT create_hypertable('health.stress', 'time', if_not_exists => TRUE);

-- health.sleep_sessions
CREATE TABLE IF NOT EXISTS health.sleep_sessions (
    id              BIGSERIAL,
    device_id       UUID NOT NULL,
    sleep_date      DATE NOT NULL,
    start_time      TIMESTAMPTZ NOT NULL,
    end_time        TIMESTAMPTZ NOT NULL,
    total_s         INT,
    deep_s          INT,
    rem_s           INT,
    light_s         INT,
    awake_s         INT,
    efficiency_pct  FLOAT,
    source          TEXT DEFAULT 'mi_fitness_cloud',
    owner_id        UUID NOT NULL,
    UNIQUE(start_time, sleep_date, device_id, owner_id)
);
SELECT create_hypertable('health.sleep_sessions', 'start_time', if_not_exists => TRUE);

-- =============================================================================
-- §3: Create analysis tables
-- =============================================================================
-- health.baseline_state (regular table, not hypertable)
CREATE TABLE IF NOT EXISTS health.baseline_state (
    metric      TEXT NOT NULL,
    device_id   UUID NOT NULL,
    stage       TEXT NOT NULL CHECK (stage IN ('insufficient','provisional','stabilizing','stable','rebaseline')),
    baseline_value FLOAT,
    data_points INT NOT NULL DEFAULT 0,
    first_data_at TIMESTAMPTZ,
    last_data_at TIMESTAMPTZ,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    owner_id    UUID NOT NULL,
    PRIMARY KEY (metric, device_id, owner_id)
);

-- health.ghi_daily (regular table)
CREATE TABLE IF NOT EXISTS health.ghi_daily (
    date        DATE NOT NULL,
    device_id   UUID NOT NULL,
    ghi_score   FLOAT NOT NULL,
    confidence  FLOAT NOT NULL,
    sleep_score FLOAT,
    cardio_score FLOAT,
    activity_score FLOAT,
    recovery_score FLOAT,
    tier        TEXT NOT NULL CHECK (tier IN ('excellent','good','fair','poor','critical')),
    owner_id    UUID NOT NULL,
    PRIMARY KEY (date, device_id, owner_id)
);

-- health.anomaly_events (hypertable)
CREATE TABLE IF NOT EXISTS health.anomaly_events (
    id          BIGINT GENERATED ALWAYS AS IDENTITY,
    time        TIMESTAMPTZ NOT NULL,
    device_id   UUID NOT NULL,
    metric      TEXT NOT NULL,
    severity    TEXT NOT NULL CHECK (severity IN ('SEV0','SEV1','SEV2','SEV3')),
    value       FLOAT NOT NULL,
    baseline    FLOAT,
    deviation   FLOAT,
    description TEXT,
    alert_sent  BOOLEAN DEFAULT FALSE,
    owner_id    UUID NOT NULL,
    CONSTRAINT pk_anomaly_events PRIMARY KEY (id, time)
);
SELECT create_hypertable('health.anomaly_events', 'time', if_not_exists => TRUE);

-- health.ingestion_cursor (regular table)
CREATE TABLE IF NOT EXISTS health.ingestion_cursor (
    source          TEXT NOT NULL,
    device_id       UUID NOT NULL,
    last_sync_at    TIMESTAMPTZ,
    last_data_date  DATE,
    metrics_available TEXT[],
    consecutive_failures INT DEFAULT 0,
    circuit_breaker_open BOOLEAN DEFAULT FALSE,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    owner_id        UUID NOT NULL,
    PRIMARY KEY (source, device_id, owner_id)
);

-- =============================================================================
-- §4: Indexes
-- =============================================================================
-- Common query pattern: owner + time range
CREATE INDEX IF NOT EXISTS idx_heart_rate_owner_time
    ON health.heart_rate (owner_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_heart_rate_device_time
    ON health.heart_rate (device_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_daily_activity_owner_date
    ON health.daily_activity (owner_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_daily_activity_device_date
    ON health.daily_activity (device_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_spo2_owner_time
    ON health.spo2 (owner_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_spo2_device_time
    ON health.spo2 (device_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_stress_owner_time
    ON health.stress (owner_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_stress_device_time
    ON health.stress (device_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_sleep_sessions_owner_start_time
    ON health.sleep_sessions (owner_id, start_time DESC);
CREATE INDEX IF NOT EXISTS idx_sleep_sessions_device_start_time
    ON health.sleep_sessions (device_id, start_time DESC);
CREATE INDEX IF NOT EXISTS idx_anomaly_events_owner_time
    ON health.anomaly_events (owner_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_anomaly_events_device_time
    ON health.anomaly_events (device_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_baseline_state_owner_metric
    ON health.baseline_state (owner_id, metric);
CREATE INDEX IF NOT EXISTS idx_ghi_daily_owner_date
    ON health.ghi_daily (owner_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_ingestion_cursor_owner_device
    ON health.ingestion_cursor (owner_id, device_id);

-- =============================================================================
-- §5: Continuous aggregates
-- =============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS health.heart_rate_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket(INTERVAL '1 hour', time) AS bucket,
    device_id,
    owner_id,
    AVG(bpm)::FLOAT AS avg_bpm,
    MIN(bpm)::SMALLINT AS min_bpm,
    MAX(bpm)::SMALLINT AS max_bpm,
    COUNT(*)::BIGINT AS sample_count
FROM health.heart_rate
GROUP BY 1, 2, 3
WITH NO DATA;

CREATE MATERIALIZED VIEW IF NOT EXISTS health.daily_summary
WITH (timescaledb.continuous) AS
SELECT
    time_bucket(INTERVAL '1 day', time) AS day,
    owner_id,
    device_id,
    AVG(bpm)::FLOAT AS avg_bpm,
    MIN(bpm)::SMALLINT AS min_bpm,
    MAX(bpm)::SMALLINT AS max_bpm,
    COUNT(*)::BIGINT AS sample_count
FROM health.heart_rate
GROUP BY 1, 2, 3
WITH NO DATA;

-- =============================================================================
-- §6: Retention policies
-- =============================================================================
SELECT add_retention_policy('health.heart_rate', INTERVAL '365 days', if_not_exists => TRUE);
SELECT add_retention_policy('health.daily_activity', INTERVAL '365 days', if_not_exists => TRUE);
SELECT add_retention_policy('health.spo2', INTERVAL '365 days', if_not_exists => TRUE);
SELECT add_retention_policy('health.stress', INTERVAL '365 days', if_not_exists => TRUE);
SELECT add_retention_policy('health.sleep_sessions', INTERVAL '365 days', if_not_exists => TRUE);
SELECT add_retention_policy('health.anomaly_events', INTERVAL '730 days', if_not_exists => TRUE);

-- =============================================================================
-- §7: Continuous aggregate refresh policies
-- =============================================================================
SELECT add_continuous_aggregate_policy('health.heart_rate_hourly',
    start_offset => INTERVAL '2 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);
SELECT add_continuous_aggregate_policy('health.daily_summary',
    start_offset => INTERVAL '14 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

COMMIT;

-- =============================================================================
-- §8: Verification Queries (run after migration)
-- =============================================================================
-- V-1: Confirm schema exists
--   SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'health';
--   Expected: 1 row

-- V-2: Confirm table count
--   SELECT COUNT(*) FROM information_schema.tables
--   WHERE table_schema = 'health' AND table_type = 'BASE TABLE';
--   Expected: 9 base tables (5 hypertables + 4 analysis tables)

-- V-3: Confirm hypertable count
--   SELECT COUNT(*) FROM timescaledb_information.hypertables
--   WHERE hypertable_schema = 'health';
--   Expected: 6 hypertables (heart_rate, daily_activity, spo2, stress, sleep_sessions, anomaly_events)

-- V-4: Confirm indexes
--   SELECT indexname FROM pg_indexes
--   WHERE schemaname = 'health'
--   ORDER BY indexname;
--   Expected: primary keys and query-pattern indexes listed above

-- V-5: Confirm retention policies
--   SELECT hypertable_schema, hypertable_name, config
--   FROM timescaledb_information.jobs
--   WHERE proc_name = 'policy_retention' AND hypertable_schema = 'health'
--   ORDER BY hypertable_name;
--   Expected: 6 rows with 365d for data tables and 730d for anomaly_events

-- V-6: Confirm continuous aggregates
--   SELECT view_schema, view_name
--   FROM timescaledb_information.continuous_aggregates
--   WHERE view_schema = 'health'
--   ORDER BY view_name;
--   Expected: heart_rate_hourly, daily_summary

-- V-7: Confirm hypertable chunk interval
--   SELECT hypertable_name, chunk_time_interval
--   FROM timescaledb_information.hypertables
--   WHERE hypertable_schema = 'health'
--   ORDER BY hypertable_name;
--   Expected: 1 day for all hypertables

-- =============================================================================
-- §9: Rollback Instructions
-- =============================================================================
-- To rollback this migration:
--   SELECT remove_continuous_aggregate_policy('health.heart_rate_hourly', if_exists => TRUE);
--   SELECT remove_continuous_aggregate_policy('health.daily_summary', if_exists => TRUE);
--   SELECT remove_retention_policy('health.heart_rate', if_exists => TRUE);
--   SELECT remove_retention_policy('health.daily_activity', if_exists => TRUE);
--   SELECT remove_retention_policy('health.spo2', if_exists => TRUE);
--   SELECT remove_retention_policy('health.stress', if_exists => TRUE);
--   SELECT remove_retention_policy('health.sleep_sessions', if_exists => TRUE);
--   SELECT remove_retention_policy('health.anomaly_events', if_exists => TRUE);
--   DROP MATERIALIZED VIEW IF EXISTS health.daily_summary CASCADE;
--   DROP MATERIALIZED VIEW IF EXISTS health.heart_rate_hourly CASCADE;
--   DROP TABLE IF EXISTS health.ingestion_cursor CASCADE;
--   DROP TABLE IF EXISTS health.ghi_daily CASCADE;
--   DROP TABLE IF EXISTS health.baseline_state CASCADE;
--   DROP TABLE IF EXISTS health.anomaly_events CASCADE;
--   DROP TABLE IF EXISTS health.sleep_sessions CASCADE;
--   DROP TABLE IF EXISTS health.stress CASCADE;
--   DROP TABLE IF EXISTS health.spo2 CASCADE;
--   DROP TABLE IF EXISTS health.daily_activity CASCADE;
--   DROP TABLE IF EXISTS health.heart_rate CASCADE;
--   DROP SCHEMA IF EXISTS health CASCADE;
-- Note: This is destructive and removes all health telemetry and derived aggregates.

-- =============================================================================
-- §10: Footer
-- =============================================================================
-- | Field | Value |
-- |---|---|
-- | Migration ID | P14-001 |
-- | Date | 2026-06-18 |
-- | Author | Guinevere |
-- | PostgreSQL | 16.14 in Docker guinevere-postgres:5433 |
-- | TimescaleDB | v2.27.1 |
-- | Database | guinevere |
-- | Schema | health |
-- | Chunk Interval | 1 day |
-- | Data Retention | 365 days |
-- | Anomaly Retention | 730 days |
-- | Idempotent | YES (all IF NOT EXISTS / if_not_exists) |
