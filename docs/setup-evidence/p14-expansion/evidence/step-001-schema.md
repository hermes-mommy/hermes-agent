# P14 Step 001 Evidence: Health schema migration

## File Path Created
- `migrations/p14_add_health_schema.sql`

## Table Count Verification
- Intended base tables in `health` schema: 9
  - 5 hypertables: `heart_rate`, `daily_activity`, `spo2`, `stress`, `sleep_sessions`
  - 4 analysis tables: `baseline_state`, `ghi_daily`, `anomaly_events`, `ingestion_cursor`

## Hypertable Count Verification
- Intended hypertables in `health` schema: 6
  - `heart_rate`
  - `daily_activity`
  - `spo2`
  - `stress`
  - `sleep_sessions`
  - `anomaly_events`

## Index Count
- Created query-pattern indexes: 16
  - `uq_heart_rate`
  - `idx_heart_rate_owner_time`
  - `idx_heart_rate_device_time`
  - `idx_daily_activity_owner_date`
  - `idx_daily_activity_device_date`
  - `idx_spo2_owner_time`
  - `idx_spo2_device_time`
  - `idx_stress_owner_time`
  - `idx_stress_device_time`
  - `idx_sleep_sessions_owner_start_time`
  - `idx_sleep_sessions_device_start_time`
  - `idx_anomaly_events_owner_time`
  - `idx_anomaly_events_device_time`
  - `idx_baseline_state_owner_metric`
  - `idx_ghi_daily_owner_date`
  - `idx_ingestion_cursor_owner_device`

## Retention Policy List
- `health.heart_rate` — 365 days
- `health.daily_activity` — 365 days
- `health.spo2` — 365 days
- `health.stress` — 365 days
- `health.sleep_sessions` — 365 days
- `health.anomaly_events` — 730 days

## Idempotency Check
- All create operations use `IF NOT EXISTS` or `if_not_exists => TRUE`
- Schema creation uses `CREATE SCHEMA IF NOT EXISTS health`
- Tables use `CREATE TABLE IF NOT EXISTS`
- Indexes use `CREATE INDEX IF NOT EXISTS`
- Hypertables use `create_hypertable(..., if_not_exists => TRUE)`
- Retention policies use `if_not_exists => TRUE`
- Continuous aggregates use `CREATE MATERIALIZED VIEW IF NOT EXISTS`
- Rollback instructions use `DROP ... IF EXISTS`

## Notes
- This evidence is based on the authored migration content and has not yet been executed against the database.
