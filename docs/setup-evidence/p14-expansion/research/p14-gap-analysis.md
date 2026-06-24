# P14 Wearable/Xiaomi Watch — E2E Gap Analysis

**Date:** 2026-06-18
**Status:** Research synthesis
**Scope:** Identify missing steps, wrong assumptions, and underspecified designs that could break P14 end-to-end functionality.

---

## Executive Summary

P14 has 27 defined steps (P14-001 through P14-027) across 9 categories. After cross-referencing the step prompts against the real codebase structure, actual Gadgetbridge schema, production anomaly detection patterns, and P7/P8 integration surfaces, I found **6 BLOCKING gaps**, **8 HIGH-RISK gaps**, and **7 MEDIUM-RISK underspecifications**.

The core risk: **P14-005 (Gadgetbridge parser) targets a fictional schema**, and **no step covers the actual data transport from phone to VPS**. These two issues alone could invalidate the entire pipeline.

---

## 🔴 BLOCKING Gaps (Must fix before implementation)

### B1: Gadgetbridge parser targets wrong schema (P14-005)

**Severity:** BLOCKING
**Step:** P14-005

**What P14-005 assumes:**
- Tables: `HEART_RATE_SAMPLE`, `SLEEP_SAMPLE`, `ACTIVITY_SAMPLE`, `SPO2_SAMPLE`, `STRESS_SAMPLE`, `HRV_SAMPLE`, `BODY_ENERGY_SAMPLE`
- Uniform millisecond timestamps
- Direct column reads like `SELECT TIMESTAMP, HEART_RATE FROM HEART_RATE_SAMPLE`

**Reality (from Gadgetbridge docs + downstream parsers):**
- Real tables: `MI_BAND_ACTIVITY_SAMPLE`, `HUAMI_HEART_RATE_MANUAL_SAMPLE`, `HUAMI_HEART_RATE_MAX_SAMPLE`, `HUAMI_HEART_RATE_RESTING_SAMPLE`, `HUAMI_SPO2_SAMPLE`, `HUAMI_STRESS_SAMPLE`, `HUAMI_EXTENDED_ACTIVITY_SAMPLE`, `HUAMI_PAI_SAMPLE`, `HUAMI_SLEEP_RESPIRATORY_RATE_SAMPLE`
- Timestamps are **seconds** in older Mi Band tables, **milliseconds** in newer Huami tables
- `HRV_SAMPLE` is **NOT a confirmed Gadgetbridge table** — HRV may not be directly exported
- `BODY_ENERGY_SAMPLE` is **NOT a confirmed Gadgetbridge table** — body battery is a derived concept
- Sleep stages are encoded as `RAW_KIND` codes (112=waking, 120=light, 121=deep, 122=REM) inside `MI_BAND_ACTIVITY_SAMPLE`, NOT in a standalone `SLEEP_SAMPLE` table
- Heart rate value `255` means missing/invalid in older exports
- `DEVICE` table uses `_id` as integer FK, not string UUIDs

**Impact:** The parser will query non-existent tables and silently return zero data. The entire ingestion pipeline downstream of P14-005 will be starved.

**Fix required:**
1. Rewrite P14-005 to target real Gadgetbridge table names
2. Add `sqlite_master` introspection to detect available tables per device/firmware
3. Implement per-table timestamp normalization (seconds vs milliseconds)
4. Derive HRV and body-energy from raw data or mark as unsupported
5. Map `RAW_KIND` codes to sleep stages
6. Read `DEVICE` table for real device identity instead of hardcoded `DEFAULT_DEVICE_ID = "watch_s3_01"`

---

### B2: No data transport mechanism from phone to VPS

**Severity:** BLOCKING
**Step:** Gap between P14-002 (WebDAV server) and P14-006 (ingestion endpoint)

**What's missing:** Gadgetbridge auto-exports a local SQLite file to the phone's storage. P14-002 sets up a WebDAV server on the VPS. But **nothing connects them**.

No step covers:
- Android-side sync app configuration (FolderSync, RCX, or similar WebDAV sync client)
- Sync schedule (how often the SQLite file gets pushed)
- Conflict resolution when the file is being written while being synced
- Integrity verification (how does the VPS know the sync completed?)
- Handling the fact that Gadgetbridge locks its DB during export

**Impact:** Even with a perfect WebDAV server and perfect parser, **no data arrives**. The pipeline is dry.

**Fix required:** New step P14-002b: "Android → VPS sync pipeline" covering:
- FolderSync/RCX configuration profile
- Sync interval (recommended: every 30 min during waking hours)
- File locking strategy (sync to `.tmp`, atomic rename)
- Integrity check (SHA256 sidecar file or file size validation)
- Monitoring: sync lag alert if last sync > 2 hours

---

### B3: No fetch/scheduler from WebDAV to ingestion pipeline

**Severity:** BLOCKING
**Step:** Gap between P14-002 (WebDAV server) and P14-006 (ingestion endpoint)

**What's missing:** Even after the SQLite file arrives on the VPS via WebDAV, nothing fetches it and feeds it to the parser.

No step covers:
- Scheduled download/polling of the WebDAV-synced file
- File watcher vs cron approach
- Incremental parsing (only parse new rows since last ingestion cursor)
- Deduplication of overlapping sync windows
- Backpressure when multiple exports accumulate

**Impact:** Data sits on the VPS filesystem but never reaches TimescaleDB.

**Fix required:** New step P14-004b: "Wearable ingestion scheduler" covering:
- APScheduler job or systemd timer for periodic fetch
- File cursor tracking (last-ingested rowid/timestamp per device)
- Incremental extraction → normalized payload → Redis buffer push
- Dead letter queue for corrupted exports
- Metrics: `wearable_last_ingestion_timestamp`, `wearable_ingestion_rows_total`

---

### B4: No device onboarding/pairing flow

**Severity:** BLOCKING
**Step:** Missing entirely

**What's missing:** P14-001 covers procurement and Gadgetbridge setup. P14-003 creates a `device_registry` table. But no step covers the **actual pairing UX** where the operator tells Guinevere about their new watch.

No step covers:
- Discord command to register a new wearable device (e.g., `/wearable pair`)
- Collecting device name, model, MAC address, Gadgetbridge device ID
- Creating the `device_registry` entry with `device_type="wearable"`
- Associating the device with the operator's user ID
- Generating WebDAV credentials scoped to that device

**Impact:** Without device registration, foreign keys fail, consent has no scope anchor, and status commands show nothing.

**Fix required:** New step P14-001b: "Device onboarding flow" covering:
- `/wearable pair` Discord command with model selection
- Device registry insert with UUID generation
- WebDAV credential generation + SOPS encryption
- Welcome DM with sync setup instructions
- Consent scope initialization for the new device

---

### B5: No wearable consent UX

**Severity:** BLOCKING
**Step:** P14-007 maps consent scopes, but no UX exists

**What P14-007 covers:** Internal consent gate extension, WAC gates, `health_consent.py` module.

**What's missing:** The operator has **no way to grant or revoke** wearable health data consent. P14-007 builds the backend but exposes no UI.

No step covers:
- Discord command to grant health consent (`/consent grant wearable-health`)
- Discord command to revoke (`/consent revoke wearable-health`)
- Consent status display in `/surveillance-status` or `/wearable status`
- Consent ledger entries for the new wearable scopes
- Fail-closed behavior when consent is not yet granted

**Impact:** Fail-closed consent gate blocks ALL wearable data. The pipeline processes nothing until consent is manually inserted into the DB.

**Fix required:** Extend P14-007 or add P14-007b: "Wearable consent UX" covering:
- `/consent grant wearable-health` command
- `/consent revoke wearable-health` with confirmation
- Consent scope registration during device pairing (P14-001b)
- Surface consent state in `/wearable status`

---

### B6: No systemd service for wearable pipeline

**Severity:** BLOCKING
**Step:** Missing entirely

**What's missing:** Every other daemon in Guinevere has a systemd service:
- `guinevere-surveillance.service`
- `guinevere-discord.service`
- `guinevere-loops.service`
- `guinevere-scheduler.service`

P14 has **no step** to create `guinevere-wearable.service` or equivalent.

No step covers:
- Systemd unit file for the wearable ingestion daemon
- Environment file (`.env.wearable`)
- Auto-restart policy
- Dependency ordering (must start after Redis + PostgreSQL)
- VPS deployment mirror in `vps-mirror/systemd-live/`

**Impact:** Even if all code exists, it doesn't run in production. Manual `python -m src.wearable.consumer` is not a deployment strategy.

**Fix required:** New step P14-026b: "Wearable service deployment" covering:
- `systemd/guinevere-wearable.service`
- `.env.wearable` template
- VPS mirror deployment
- Prometheus scrape target registration
- Log rotation config

---

## 🟠 HIGH-RISK Gaps (Could cause data loss, false alerts, or silent failures)

### H1: Anomaly detection uses universal ±20% threshold (P14-010)

**Severity:** HIGH
**Risk:** False alert fatigue or missed real anomalies

A flat ±20% threshold is too coarse:
- **Resting HR:** Normal variation is 3-5 bpm. A 20% threshold on 60 bpm = 12 bpm, which would miss clinically significant sustained 8 bpm rises.
- **SpO2:** Normal is 95-100%. A 20% drop from 98% = 78.4%, which is DEAD before the alert triggers.
- **Steps:** Day-to-day variation is often 30-50%. A 20% threshold would alert on normal lazy days.
- **HRV:** Highly variable by nature. 20% may be within normal circadian range.

**Fix required:**
- Replace universal threshold with metric-specific rules:
  - HR: ±5 bpm resting (2-3 night persistence), ±15% active
  - SpO2: Absolute thresholds (<94% caution, <92% high concern, <90% urgent)
  - Steps: -40% from baseline (weekend-adjusted)
  - HRV: -30% from 7-day rolling baseline
- Add persistence requirements (1 reading ≠ anomaly)
- Add state context (resting vs active vs sleep)

---

### H2: GHI scoring lacks confidence model and penalty saturation (P14-011)

**Severity:** HIGH
**Risk:** Misleading scores when data quality is poor

Missing from P14-011:
- **Confidence score:** No mechanism to express "this GHI is based on 60% of expected data"
- **Score suppression:** No rule to withhold GHI when data is too sparse
- **Penalty saturation:** Multiple anomalies could compound to produce negative or zero scores
- **Penalty decay:** No mechanism for scores to recover after bad days
- **Pillar overlap:** Sleep quality and recovery physiology may double-count the same signal

**Fix required:**
- Add confidence as first-class output: `ghi_confidence: float [0,1]`
- Suppress GHI when confidence < 0.4
- Cap individual anomaly penalties at -15% per pillar
- Implement exponential penalty decay over 3 days
- Document pillar independence rules

---

### H3: No baseline warmup state machine

**Severity:** HIGH
**Risk:** Garbage anomalies during first 28 days

P14-009 computes a 28-day baseline. But during days 1-27:
- Is anomaly detection active?
- Is GHI computed?
- Does the user see "learning" state?
- What happens on day 7 with only 7 data points?

No step covers the provisional/learning state that all production wearables implement (Oura: 2 weeks, Google: 7 nights, Garmin: several weeks).

**Fix required:** New step or extend P14-009:
- Stage 0 (0-3 days): `insufficient_data` — no GHI, no anomalies
- Stage 1 (4-14 days): `provisional` — GHI with degraded confidence, anomaly alerts suppressed
- Stage 2 (15-28 days): `stabilizing` — GHI with rising confidence, anomaly alerts active but conservative
- Stage 3 (28+ days): `stable` — full functionality
- Stage 4 (after >7 day gap): `rebaseline` — reset to Stage 1

---

### H4: No alert routing for wearable anomalies

**Severity:** HIGH
**Risk:** Anomalies detected but nobody is notified

P14-010 detects anomalies. P14-012 through P14-019 adjust persona behavior. But **no step routes critical health alerts to the operator** outside the persona system.

Missing:
- Prometheus alert rules for wearable anomalies (SEV0/1/2/3 mapping)
- Alertmanager routing for health alerts → Discord/Gotify
- Discord embed format for health anomaly notifications
- Rate limiting for alert storms (e.g., device malfunction causing 100 alerts/hour)
- Quiet hours for non-critical health alerts

**Fix required:** New step P14-010b: "Wearable alert routing" covering:
- `monitoring/prometheus/rules/wearable-alerts.yml`
- Alertmanager receiver configuration
- Discord notification embed template
- Rate limits and quiet hours
- SEV mapping (SpO2 <90% = SEV0, HR anomaly = SEV2, low battery = SEV3)

---

### H5: No encryption for health data at rest

**Severity:** HIGH
**Risk:** Privacy breach, violates data governance

Health data is among the most sensitive personal data. P14-003 creates TimescaleDB tables with plaintext health metrics. P14-002 uses basic auth over TLS (transport encryption only).

Missing:
- Encryption of health metric columns in TimescaleDB (or at-rest encryption via pgcrypto)
- Encryption of the synced SQLite file on the VPS filesystem
- Access logging for health data queries
- Data classification tag in the data governance policy

**Fix required:**
- Extend P14-003 with at-rest encryption strategy
- Add health data to Data Governance & Classification Policy
- Add access audit logging to P14-006 ingestion writer

---

### H6: No Grafana dashboards for wearable health

**Severity:** HIGH
**Risk:** Zero observability into the wearable pipeline health

P14 creates an entire data pipeline but no step covers visualization. The monitoring stack exists (`monitoring/grafana/`), but no wearable-specific dashboards are provisioned.

Missing:
- Wearable data freshness dashboard (last sync, last ingestion, data gaps)
- Health metrics trend dashboard (7d/30d views for all 7 metrics)
- GHI score history dashboard
- Anomaly event timeline
- Device battery / connectivity status

**Fix required:** New step P14-024b: "Wearable Grafana dashboards" covering:
- `monitoring/grafana/dashboards/wearable-health.json`
- `monitoring/grafana/provisioning/dashboards/wearable.yml`
- Data source wiring to TimescaleDB

---

### H7: Dual-source conflict resolution undefined (P14-005 vs P14-008)

**Severity:** HIGH
**Risk:** Duplicate or contradictory data

P14-005 ingests from Gadgetbridge SQLite. P14-008 provides Mi Fitness Cloud SDK fallback. Both could provide overlapping data for the same time window.

Missing:
- Source priority rules (which wins on conflict?)
- Deduplication key strategy (device_id + timestamp + metric_type?)
- Merge logic for partial overlaps
- Source provenance tagging in stored records

**Fix required:** Extend P14-008 or add P14-008b:
- Define source priority: Gadgetbridge > Mi Fitness Cloud (or vice versa)
- Implement upsert with `ON CONFLICT (device_id, metric_type, occurred_at) DO UPDATE` only if source priority is higher
- Tag every row with `source: gadgetbridge | mi_fitness_cloud`

---

### H8: No test fixtures with real Gadgetbridge schema

**Severity:** HIGH
**Risk:** P14-027 integration tests pass against mock data but fail in production

P14-027 defines 10 test scenarios and 20 AC validations. But no step creates test fixtures that match the **real** Gadgetbridge SQLite schema.

Missing:
- Sample Gadgetbridge SQLite database with known data patterns
- Fixture for `MI_BAND_ACTIVITY_SAMPLE` with realistic RAW_KIND codes
- Fixture for `HUAMI_*` tables with correct timestamp units
- Fixture with intentional corruption (missing data, future timestamps, 255 HR values)
- Fixture for multi-day data to test baseline computation

**Fix required:** New step P14-026c: "Test fixtures and mock data" covering:
- `tests/wearable/fixtures/gadgetbridge_sample.db`
- `tests/wearable/fixtures/expected_parsed_output.json`
- `tests/wearable/fixtures/corrupted_export.db`
- Schema validation test that runs against real export format

---

## 🟡 MEDIUM-RISK Underspecifications

### M1: WebDAV credential rotation (P14-002)
P14-002 creates basic auth credentials encrypted with SOPS. No rotation schedule. If credentials leak, the attacker has permanent access to the health data sync endpoint.
**Recommendation:** Add 90-day rotation schedule to P14-002.

### M2: Wearable data retention policy
P14-003 sets 365-day retention on hypertables. Health data may need longer retention for longitudinal analysis, or shorter for privacy compliance. No discussion of tradeoffs.
**Recommendation:** Clarify retention policy with operator. Consider 730-day for aggregates, 365-day for raw samples.

### M3: Persona integration mechanics (P14-012 through P14-019)
These steps describe persona behavior adjustments based on GHI states, but don't specify the exact code integration points:
- Which function in `yandere_fsm.py` reads GHI?
- How does `mood_engine.py` consume health anomalies?
- Does `punishment_engine.py` suppress punishment when recovery is low?
- What's the Redis key pattern for GHI state?
**Recommendation:** Each persona step needs explicit file + function + Redis key references.

### M4: Discord command scope and permissions (P14-021 through P14-024)
Four Discord commands are defined (`/health`, `/health-trend`, `/ghi`, `/wearable-status`) but no permission model. Can anyone see Faiz's health data? Is it owner-only?
**Recommendation:** Add owner-only permission check consistent with existing `_auth_guard.py` pattern.

### M5: Incremental parsing cursor storage
The ingestion scheduler (proposed P14-004b) needs to track where it left off. No step specifies cursor storage.
**Recommendation:** Store cursor in `wearable.ingestion_cursor` table: `(device_id, last_timestamp, last_rowid, updated_at)`.

### M6: Wearable battery/connection monitoring
No step covers monitoring the watch's battery level or connection status to Gadgetbridge. A dead watch = no data = stale baselines.
**Recommendation:** Add battery level ingestion to P14-005 and surface in `/wearable-status`.

### M7: Mi Fitness Cloud SDK fragility (P14-008)
Mi Fitness Cloud OAuth2 is unofficial and may break at any time. P14-008 should have a clear deprecation/kill switch.
**Recommendation:** Add health check and automatic disable when auth fails > 3 consecutive times.

---

## Revised Step Count Estimate

| Category | Original Steps | New Steps Needed | Total |
|---|---|---|---|
| Device & Setup | P14-001 | + P14-001b (onboarding) | 2 |
| Transport | P14-002 | + P14-002b (phone→VPS sync) | 2 |
| Database | P14-003 | — | 1 |
| Ingestion | P14-004, P14-005, P14-006 | + P14-004b (scheduler) | 4 |
| Consent | P14-007 | + P14-007b (UX) | 2 |
| Fallback | P14-008 | + P14-008b (conflict resolution) | 2 |
| Analytics | P14-009, P14-010, P14-011 | + P14-010b (alert routing) | 4 |
| Persona | P14-012 through P14-019 | — (needs detail refinement) | 8 |
| WAC | P14-020 | — | 1 |
| Discord | P14-021 through P14-024 | — (needs permission model) | 4 |
| Testing | P14-027 | + P14-026c (fixtures) | 2 |
| Deployment | (missing) | + P14-026b (systemd service) | 1 |
| Observability | (missing) | + P14-024b (Grafana dashboards) | 1 |
| Security | (missing) | + P14-003b (encryption at rest) | 1 |
| **Total** | **27** | **+10** | **37** |

---

## Clarifying Questions for Operator

Before implementation, I need your decisions on these:

### 1. Transport Architecture
**Option A:** Gadgetbridge auto-export → FolderSync (Android app) → WebDAV → VPS filesystem → scheduled fetch → Redis buffer → TimescaleDB
**Option B:** Gadgetbridge auto-export → custom Android daemon → HTTPS POST → VPS API → Redis buffer → TimescaleDB (bypasses WebDAV entirely)
**Option C:** Keep WebDAV but add a custom Android companion app that reads Gadgetbridge DB directly and pushes to Guinevere API

Which transport model do you prefer? Option A is lowest effort but fragile. Option B is most robust but requires Android development.

### 2. HRV and Body Battery
Real Gadgetbridge exports for Xiaomi devices do **not** have confirmed `HRV_SAMPLE` or `BODY_ENERGY_SAMPLE` tables.
**Option A:** Derive HRV proxy from heart rate variability within `MI_BAND_ACTIVITY_SAMPLE` (possible but approximate)
**Option B:** Drop HRV and body battery as tracked metrics for v1
**Option C:** Only support them for devices that explicitly export them (check `sqlite_master` at runtime)

### 3. Data Classification
Health data from wearables is sensitive. Should it be:
**Option A:** Classified as `surveillance` scope (reuses existing consent infrastructure)
**Option B:** New consent scope family `wearable-health-*` (cleaner separation, more work)
**Option C:** New data classification tier above surveillance (most protective, most work)

### 4. Persona Integration Depth
P14-012 through P14-019 describe 8 persona states based on GHI. Implementation options:
**Option A:** Full state machine integration with `yandere_fsm.py` — GHI directly affects persona transitions
**Option B:** Lightweight mood modifier — GHI adjusts `mood_engine.py` scores but doesn't change FSM states
**Option C:** Advisory only — GHI is available to persona engine but requires explicit operator opt-in per behavior

### 5. Alert Escalation
When a critical health anomaly is detected (e.g., SpO2 <90%):
**Option A:** Alert via Discord DM immediately, regardless of quiet hours
**Option B:** Alert via Discord + Gotify, respect quiet hours unless SEV0
**Option C:** Alert via persona behavior change only (no direct notification)

### 6. Mi Fitness Cloud Priority
Given that Mi Fitness Cloud SDK is unofficial and fragile:
**Option A:** Primary data source, Gadgetbridge as fallback
**Option B:** Gadgetbridge as primary, Mi Fitness as gap-fill only
**Option C:** Implement both as equal sources with merge logic

---

## Evidence

| Source | Path/URL |
|---|---|
| Project structure report | `research-reports/p14-existing-project-structure.md` |
| P7/P8 integration report | `research-reports/p14-p7-p8-integration-points.md` |
| Gadgetbridge schema report | `research-reports/p14-gadgetbridge-schema.md` |
| Anomaly detection report | `research-reports/p14-anomaly-detection.md` |
| Requirements spec | `research-reports/p14-expansion/requirements-p14-wearable.md` |
| Step prompts | `stepprompts/StepPrompts.md` (line 38624+) |
| Evidence file | `docs/setup-evidence/p14-expansion/evidence-p14-expansion.md` |
