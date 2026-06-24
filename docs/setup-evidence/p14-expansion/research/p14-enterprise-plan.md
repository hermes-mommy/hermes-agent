# P14 — Wearable Health Pipeline: Enterprise Implementation Plan

**Date:** 2026-06-18
**Status:** Plan Gate — Awaiting Momus Review
**Approach:** Mi Fitness Cloud API (primary) + Systemd Timer + TimescaleDB + Anomaly Detection + GHI + Mood Modifier
**Previous approach (DEPRECATED):** Gadgetbridge WebDAV + Android daemon → superseded by operator decision

---

## 0. Operator Decisions (Binding)

| # | Topic | Decision | Rationale |
|---|---|---|---|
| D1 | Data Source | **Mi Fitness Cloud API** (primary) from VPS | Zero mobile infra, simplest deploy |
| D2 | Transport | HTTPS directly from VPS → Xiaomi Cloud | No phone, no WebDAV, no daemon |
| D3 | Scheduling | **Systemd timer** (matches Guinevere convention) | Consistent with `guinevere-shadow-monitor.timer` |
| D4 | HRV & Body Battery | **C — Runtime detect** (`sqlite_master`/API field check) | Graceful degradation, future-proof |
| D5 | Data Classification | **B — New scope `wearable-health-*`** | Granular consent, independent from surveillance revocation |
| D6 | Persona Integration | **B — Mood modifier** (`mood_engine.py`) | Safe — GHI adjusts mood, does NOT drive yandere FSM |
| D7 | Alert Escalation | **B — Quiet hours + SEV0 bypass** | Balanced responsiveness vs alert fatigue |
| D8 | Mi Fitness Cloud | **Primary source** (Gadgetbridge deferred to v2) | Simplest path, no mobile dependency |
| D9 | Conflict Resolution | Mi Fitness Cloud always wins (single source in v1) | No merge logic needed |
| D10 | Gadgetbridge | **Deferred to v2** as raw data fallback | Reduces v1 scope significantly |

### Decisions that ELIMINATE old gaps:
| Old Gap | Status | Reason |
|---|---|---|
| B1: Fictional Gadgetbridge schema | **ELIMINATED** | Not using Gadgetbridge in v1 |
| B2: No phone→VPS transport | **ELIMINATED** | No phone involved |
| B3: No ingestion scheduler | **ELIMINATED** | Systemd timer + API poll replaces file scheduler |
| B4: No device onboarding | **SIMPLIFIED** | Account linking replaces device pairing |
| B5: No consent UX | **RETAINED** | Still needed |
| B6: No systemd service | **RETAINED** | Still needed (now timer+service pair) |

---

## 1. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        VPS (Guinevere)                       │
│                                                              │
│  ┌──────────────────────┐                                    │
│  │ guinevere-wearable   │                                    │
│  │ .timer (systemd)     │  every 30 min                      │
│  └──────────┬───────────┘                                    │
│             │ triggers                                       │
│             ▼                                                │
│  ┌──────────────────────┐    ┌────────────────────┐         │
│  │ src.wearable.sync    │───▶│ Mi Fitness Cloud   │         │
│  │ (oneshot)            │◀───│ API (Xiaomi)       │         │
│  └──────────┬───────────┘    │ userId + passToken │         │
│             │                 └────────────────────┘         │
│             ▼                                                │
│  ┌──────────────────────┐                                    │
│  │ normalizer.py        │  API JSON → HealthMetricPayload    │
│  └──────────┬───────────┘                                    │
│             ▼                                                │
│  ┌──────────────────────┐    ┌────────────────────┐         │
│  │ Redis DB2 buffer     │───▶│ Consumer pipeline   │         │
│  │ (reuse P7)           │    │ consent gate       │         │
│  └──────────────────────┘    │ classification     │         │
│                              └────────┬───────────┘         │
│                                       ▼                     │
│                              ┌────────────────────┐         │
│                              │ TimescaleDB        │         │
│                              │ health.* schema    │         │
│                              │ 5 hypertables      │         │
│                              │ + 3 aggregate      │         │
│                              └────────┬───────────┘         │
│                                       ▼                     │
│                              ┌────────────────────┐         │
│                              │ Analysis Worker    │         │
│                              │ (systemd timer)    │         │
│                              │ - baseline.py      │         │
│                              │ - anomaly.py       │         │
│                              │ - ghi.py           │         │
│                              └────────┬───────────┘         │
│                                       ▼                     │
│                     ┌─────────────────┼───────────────┐     │
│                     ▼                 ▼               ▼     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ mood_engine  │  │ Alert Router │  │ Prometheus   │      │
│  │ (modifier)   │  │ (SEV-based)  │  │ metrics      │      │
│  └──────────────┘  └──────┬───────┘  └──────────────┘      │
│                           ▼                                  │
│                    ┌──────────────┐                          │
│                    │ Discord DM   │                          │
│                    │ (quiet hrs)  │                          │
│                    └──────────────┘                          │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ Discord Commands (owner-only)                        │    │
│  │ /health-status  /ghi  /wearable-sync  /wearable-cfg  │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ Grafana Dashboard: wearable-health                   │    │
│  └──────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow
1. `systemd/guinevere-wearable-sync.timer` fires every 30 minutes
2. `src.wearable.sync` (oneshot) authenticates → fetches latest metrics → normalizes → pushes to Redis DB2
3. Consumer pipeline (reuse P7): consent gate → classification → TimescaleDB `health.*`
4. `systemd/guinevere-wearable-analysis.timer` fires daily at 04:00 WIB
5. `src.wearable.analysis` (oneshot): baseline → anomaly detection → GHI scoring
6. GHI → `mood_engine.py` modifier (NOT `yandere_fsm.py`)
7. Anomalies → alert router → Discord DM (SEV0 bypasses quiet hours)
8. Prometheus exports pipeline health metrics
9. Grafana visualizes trends

---

## 2. Revised Blocking Gaps (Mi Fitness Cloud Era)

### NB1: Token management & secure storage
**Severity:** BLOCKING
**What:** `userId` + `passToken` are Xiaomi account cookies — credentials. Must be stored in SOPS-encrypted `.env.wearable`, never plaintext. Token refresh must be handled without interactive login (login endpoint is rate-limited, may trigger captcha).
**Fix:** Step P14-002 + P14-003 cover env file + client with token persistence.

### NB2: API metric coverage gaps
**Severity:** BLOCKING
**What:** Mi Fitness Cloud confirms: steps, activity, distance, calories, HR, body measurements. **NOT confirmed: sleep, HRV, body battery, stress.** SDK `mi-fitness` may cover SpO2.
**Fix:** Step P14-003 runtime-detects available metrics. Unsupported metrics marked `data_source_unavailable=true`, excluded from GHI scoring. GHI weights rebalance when metrics missing.

### NB3: API reliability & graceful degradation
**Severity:** BLOCKING
**What:** Unofficial API. Endpoints change, captcha/device-untrusted errors, region-sensitive. Pipeline must not crash on API failure.
**Fix:** Step P14-003 includes exponential backoff, circuit breaker (3 consecutive failures → pause sync, alert SEV3), graceful error types.

### NB4: Wearable consent scope
**Severity:** BLOCKING (same as old B5)
**What:** New scope `wearable-health.*` needed. No UX to grant/revoke. Fail-closed gate blocks all data.
**Fix:** Step P14-013.

---

## 3. Step Plan (20 Steps)

### Phase A — Foundation (Steps 1-3)
Sequential. Everything depends on schema + config.

| Step | Title | Deliverable | Parallel |
|---|---|---|---|
| **P14-001** | Health DB Schema & Alembic Migration | `alembic/versions/p14_add_health_hypertables.sql` — `health.*` schema, 5 hypertables (heart_rate, daily_activity, spo2, stress, sleep_sessions), 3 aggregate tables, continuous aggregates, 365d retention, ingestion cursor table | Sequential |
| **P14-002** | Environment Config & SOPS Secrets | `.env.wearable` template, SOPS-encrypted secret store for Xiaomi credentials, `.env.wearable.example` for repo | Sequential |
| **P14-003** | `src/wearable/` Package Skeleton + Mi Fitness Client | `src/wearable/__init__.py`, `config.py`, `mi_fitness_client.py` (auth, token persist, fetch metrics, exponential backoff, circuit breaker, error types: `AuthError`, `RateLimitError`, `EndpointDriftError`, `CaptchaRequiredError`) | Sequential |

### Phase B — Data Pipeline (Steps 4-6)
Sequential. Pipeline flows linearly.

| Step | Title | Deliverable | Parallel |
|---|---|---|---|
| **P14-004** | Data Normalizer | `src/wearable/normalizer.py` — Mi Fitness API JSON → unified `HealthMetricPayload` (Pydantic), per-metric extractors, runtime metric availability detection, source provenance tagging | Sequential (after P14-003) |
| **P14-005** | Redis Buffer Push + Consumer Extension | Reuse P7 `redis_buffer.py` pattern. `src/wearable/sync.py` — oneshot: auth → fetch → normalize → push Redis DB2. Extend consumer scope map with `wearable-health.*`. Dedup on upsert. | Sequential (after P14-004) |
| **P14-006** | TimescaleDB Writer | `src/wearable/writer.py` — Redis consumer → `INSERT ON CONFLICT` into `health.*` hypertables. Per-metric upsert logic. Ingestion cursor tracking in `health.ingestion_cursor`. Source provenance column. | Sequential (after P14-005) |

### Phase C — Intelligence (Steps 7-9)
Sequential within phase. Can parallel with Phase D.

| Step | Title | Deliverable | Parallel |
|---|---|---|---|
| **P14-007** | Baseline Engine + Warmup State Machine | `src/wearable/baseline.py` — 28-day rolling baseline per metric. Warmup stages: `insufficient` (0-3d) → `provisional` (4-14d) → `stabilizing` (15-28d) → `stable` (28d+) → `rebaseline` (>7d gap). Persisted in `health.baseline_state`. | Parallel with Phase D |
| **P14-008** | Anomaly Detection Engine | `src/wearable/anomaly.py` — Metric-specific thresholds (HR: ±5bpm resting, SpO2: absolute <94/<92/<90, Steps: -40%, Stress: +30%). Persistence requirements (1 reading ≠ anomaly). Confidence scoring. State context awareness. Anomaly event logging to `health.anomaly_events`. | Parallel with Phase D |
| **P14-009** | GHI Scoring | `src/wearable/ghi.py` — Sleep 40% / Cardio 20% / Activity 20% / Recovery 20%. Confidence score (0-1). Suppress GHI when confidence <0.4. Penalty cap -15% per pillar. Exponential decay over 3 days. Dynamic weight rebalance when metrics unavailable. Tiers: Excellent ≥85, Good ≥70, Fair ≥55, Poor ≥40, Critical <40. | Parallel with Phase D |

### Phase D — Integration (Steps 10-11)
Can parallel with Phase C.

| Step | Title | Deliverable | Parallel |
|---|---|---|---|
| **P14-010** | Mood Modifier Integration | `src/wearable/mood_integration.py` — GHI → `mood_engine.py` score modifier. Caring tone when recovery low, energetic when healthy. Does NOT touch `yandere_fsm.py`. Redis key: `wearable:ghi:current`. Health data invisible during argument/distress state. | Parallel with Phase C |
| **P14-011** | Alert Routing (Prometheus + Discord + Quiet Hours) | `src/wearable/alerts.py` + `monitoring/prometheus/rules/wearable-alerts.yml`. SEV mapping: SEV0 (SpO2<90%, HR>130 sustained) → immediate DM bypass quiet hours. SEV1 (SpO2<92%, HR anomaly 3+ days) → DM next active window. SEV2 (GHI<30 2+ days, sleep<4h) → daily summary embed. SEV3 (battery low, sync delay >2h) → log only, `/wearable-status`. Rate limiting: max 5 alerts/hour. | Parallel with Phase C |

### Phase E — UX & Consent (Steps 12-13)
After Phase C+D.

| Step | Title | Deliverable | Parallel |
|---|---|---|---|
| **P14-012** | Consent Integration | Extend `src/surveillance/consent_gate.py`: add `wearable-health.*` to `VALID_SURVEILLANCE_SCOPES`. `src/wearable/consent.py` — grant/revoke logic, consent ledger entries, fail-closed behavior. | Sequential |
| **P14-013** | Discord Commands | `src/wearable/commands.py` — 4 commands: `/health-status` (GHI + today metrics + trend arrows), `/ghi` (detailed GHI breakdown + confidence + warmup state), `/wearable-sync` (manual trigger), `/wearable-cfg` (account link status, metric availability, consent state). Owner-only permission (reuse `_auth_guard.py`). | Sequential (after P14-012) |

### Phase F — Ops (Steps 14-17)
After Phase E. Steps 14-16 can parallel.

| Step | Title | Deliverable | Parallel |
|---|---|---|---|
| **P14-014** | Systemd Timer + Service | `systemd/guinevere-wearable-sync.service` (Type=oneshot), `systemd/guinevere-wearable-sync.timer` (OnUnitActiveSec=30min, Persistent=true), `systemd/guinevere-wearable-analysis.service` + `.timer` (daily 04:00). Follow canonical pattern from `guinevere-shadow-monitor.*`. Install script: `scripts/install_wearable_service.sh`. | Parallel with 15-16 |
| **P14-015** | Prometheus Metrics | `src/wearable/metrics.py` — Expose: `wearable_sync_last_success_timestamp`, `wearable_sync_errors_total`, `wearable_metrics_ingested_total{metric}`, `wearable_ghi_current`, `wearable_ghi_confidence`, `wearable_baseline_state`, `wearable_anomalies_detected_total{severity}`. Prometheus scrape config update. | Parallel with 14,16 |
| **P14-016** | Grafana Dashboard | `monitoring/grafana/dashboards/wearable-health.json` — Panels: GHI trend (30d), metric time-series, anomaly timeline, data freshness gauge, baseline state indicator, sync health. Provisioning config. | Parallel with 14,15 |
| **P14-017** | Encryption at Rest | Health data classification in Data Governance Policy. Access audit logging on health data queries. SOPS for credential rotation (90-day schedule). | Sequential (after 14-16) |

### Phase G — Quality (Steps 18-20)
After Phase F.

| Step | Title | Deliverable | Parallel |
|---|---|---|---|
| **P14-018** | Unit Tests | `tests/wearable/test_client.py`, `test_normalizer.py`, `test_baseline.py`, `test_anomaly.py`, `test_ghi.py`, `test_mood.py`, `test_alerts.py`, `test_consent.py`. Mock Mi Fitness API responses. Test warmup states. Test GHI confidence model. Test alert severity routing. | Sequential |
| **P14-019** | Integration Tests | `tests/wearable/test_e2e_pipeline.py` — Full pipeline: mock API → normalizer → Redis → consumer → TimescaleDB → analysis → GHI → mood. Test data freshness. Test consent gate blocking. Test quiet hours alert routing. | Sequential (after P14-018) |
| **P14-020** | P14 GATE — Final Validation | `docs/setup-evidence/p14-expansion/evidence-p14-expansion.md` update. All 20 AC-WEAR acceptance criteria validated. Cross-reference ADR-021, PersonaSafetyPolicy. Document caveats (API fragility, metric coverage gaps). Rollback plan. | Sequential (after P14-019) |

---

## 4. Dependency Map

```
P14-001 (Schema)
  └──▶ P14-002 (Config)
         └──▶ P14-003 (Client)
                └──▶ P14-004 (Normalizer)
                       └──▶ P14-005 (Redis+Consumer)
                              └──▶ P14-006 (Writer)
                                     ├──▶ P14-007 (Baseline) ──┐
                                     ├──▶ P14-008 (Anomaly)  ──┤
                                     ├──▶ P14-009 (GHI)      ──┤
                                     ├──▶ P14-010 (Mood)     ──┤
                                     └──▶ P14-011 (Alerts)   ──┤
                                                                ├──▶ P14-012 (Consent)
                                                                │      └──▶ P14-013 (Commands)
                                                                │
                                                                ├──▶ P14-014 (Systemd) ──┐
                                                                ├──▶ P14-015 (Prometheus)┤
                                                                └──▶ P14-016 (Grafana) ──┤
                                                                                          └──▶ P14-017 (Encryption)
                                                                                                   └──▶ P14-018 (Unit Tests)
                                                                                                          └──▶ P14-019 (Integration Tests)
                                                                                                                 └──▶ P14-020 (P14 GATE)
```

### Parallel Execution Opportunities
- **Phase C** (P14-007, 008, 009) can execute **in parallel with Phase D** (P14-010, 011) — they read from the same hypertables but write to different outputs
- **Phase F** (P14-014, 015, 016) can execute **in parallel** — independent operational artifacts
- **Phase G** is fully sequential (tests build on each other)

---

## 5. Collision Scan

| Shared File/Resource | Steps Touching It | Owner | Mitigation |
|---|---|---|---|
| `src/surveillance/consent_gate.py` | P14-012 | P14-012 sub-agent | Extend VALID_SURVEILLANCE_SCOPES list only |
| `src/surveillance/consumer.py` | P14-005 | P14-005 sub-agent | Add `wearable-health` to scope map dict |
| `src/discord/_command_registry.py` | P14-013 | P14-013 sub-agent | Register 4 new commands, no modification of existing |
| `src/mood_engine.py` (or wherever mood lives) | P14-010 | P14-010 sub-agent | Add modifier hook, no FSM changes |
| `monitoring/prometheus/rules/` | P14-015 | P14-015 sub-agent | New file `wearable-alerts.yml`, no edit to existing |
| `monitoring/grafana/dashboards/` | P14-016 | P14-016 sub-agent | New file `wearable-health.json`, no edit to existing |
| `monitoring/prometheus/prometheus.yml` | P14-015 | P14-015 sub-agent | Append scrape job for wearable metrics |
| `alembic/versions/` | P14-001 | P14-001 sub-agent | New migration file only |
| `systemd/` | P14-014 | P14-014 sub-agent | New files only |
| `.env.wearable` (new) | P14-002 | P14-002 sub-agent | New file |
| `docs/setup-evidence/p14-expansion/` | P14-020 | Parent-only | Evidence aggregation, parent writes |

**No collisions detected.** Each step touches distinct files or appends to shared files at distinct locations. No two steps write the same file simultaneously.

---

## 6. Database Schema (Revised)

### Hypertables (5)
```sql
CREATE SCHEMA IF NOT EXISTS health;

-- Heart Rate (from Mi Fitness Cloud API)
CREATE TABLE health.heart_rate (
    time        TIMESTAMPTZ NOT NULL,
    device_id   UUID NOT NULL,
    bpm         SMALLINT NOT NULL,
    resting_bpm SMALLINT,
    source      TEXT DEFAULT 'mi_fitness_cloud',
    confidence  FLOAT DEFAULT 1.0,
    owner_id    UUID NOT NULL
);
SELECT create_hypertable('health.heart_rate', 'time');
CREATE UNIQUE INDEX uq_heart_rate ON health.heart_rate (time, device_id, owner_id);

-- Daily Activity
CREATE TABLE health.daily_activity (
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

-- SpO2
CREATE TABLE health.spo2 (
    time        TIMESTAMPTZ NOT NULL,
    device_id   UUID NOT NULL,
    spo2_pct    FLOAT NOT NULL,
    source      TEXT DEFAULT 'mi_fitness_cloud',
    owner_id    UUID NOT NULL
);
SELECT create_hypertable('health.spo2', 'time');

-- Stress
CREATE TABLE health.stress (
    time        TIMESTAMPTZ NOT NULL,
    device_id   UUID NOT NULL,
    score       SMALLINT NOT NULL,  -- 0-100 proprietary Xiaomi score
    source      TEXT DEFAULT 'mi_fitness_cloud',
    owner_id    UUID NOT NULL
);
SELECT create_hypertable('health.stress', 'time');

-- Sleep Sessions (per-night summary)
CREATE TABLE health.sleep_sessions (
    id              BIGSERIAL PRIMARY KEY,
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
    UNIQUE(sleep_date, device_id, owner_id)
);
```

### Aggregate/Analysis Tables (4)
```sql
-- Baseline state per metric
CREATE TABLE health.baseline_state (
    metric      TEXT NOT NULL,
    device_id   UUID NOT NULL,
    stage       TEXT NOT NULL,  -- insufficient/provisional/stabilizing/stable/rebaseline
    baseline_value FLOAT,
    data_points INT NOT NULL DEFAULT 0,
    first_data_at TIMESTAMPTZ,
    last_data_at TIMESTAMPTZ,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    owner_id    UUID NOT NULL,
    PRIMARY KEY (metric, device_id, owner_id)
);

-- GHI daily score
CREATE TABLE health.ghi_daily (
    date        DATE NOT NULL,
    device_id   UUID NOT NULL,
    ghi_score   FLOAT NOT NULL,
    confidence  FLOAT NOT NULL,
    sleep_score FLOAT,
    cardio_score FLOAT,
    activity_score FLOAT,
    recovery_score FLOAT,
    tier        TEXT NOT NULL,  -- excellent/good/fair/poor/critical
    owner_id    UUID NOT NULL,
    PRIMARY KEY (date, device_id, owner_id)
);

-- Anomaly events
CREATE TABLE health.anomaly_events (
    id          BIGSERIAL PRIMARY KEY,
    time        TIMESTAMPTZ NOT NULL,
    device_id   UUID NOT NULL,
    metric      TEXT NOT NULL,
    severity    TEXT NOT NULL,  -- SEV0/SEV1/SEV2/SEV3
    value       FLOAT NOT NULL,
    baseline    FLOAT,
    deviation   FLOAT,
    description TEXT,
    alert_sent  BOOLEAN DEFAULT FALSE,
    owner_id    UUID NOT NULL
);
SELECT create_hypertable('health.anomaly_events', 'time');

-- Ingestion cursor
CREATE TABLE health.ingestion_cursor (
    source          TEXT NOT NULL,
    device_id       UUID NOT NULL,
    last_sync_at    TIMESTAMPTZ,
    last_data_date  DATE,
    metrics_available TEXT[],  -- array of confirmed metrics
    consecutive_failures INT DEFAULT 0,
    circuit_breaker_open BOOLEAN DEFAULT FALSE,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    owner_id        UUID NOT NULL,
    PRIMARY KEY (source, device_id, owner_id)
);
```

### Continuous Aggregates (for Grafana)
```sql
-- Hourly heart rate aggregates
CREATE MATERIALIZED VIEW health.heart_rate_hourly
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 hour', time) AS bucket,
       device_id,
       AVG(bpm)::SMALLINT AS avg_bpm,
       MIN(bpm) AS min_bpm,
       MAX(bpm) AS max_bpm,
       resting_bpm,
       owner_id
FROM health.heart_rate
GROUP BY bucket, device_id, resting_bpm, owner_id;

-- Daily metric summary
CREATE MATERIALIZED VIEW health.daily_summary
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 day', time) AS bucket,
       device_id,
       metric_name,
       AVG(value) AS avg_value,
       MIN(value) AS min_value,
       MAX(value) AS max_value,
       COUNT(*) AS sample_count,
       owner_id
FROM health.all_metrics_flat  -- view that unions all hypertables
GROUP BY bucket, device_id, metric_name, owner_id;
```

### Retention Policy
```sql
SELECT add_retention_policy('health.heart_rate', INTERVAL '365 days');
SELECT add_retention_policy('health.spo2', INTERVAL '365 days');
SELECT add_retention_policy('health.stress', INTERVAL '365 days');
SELECT add_retention_policy('health.anomaly_events', INTERVAL '730 days');  -- keep anomalies longer
-- Aggregates retained indefinitely (small storage footprint)
```

---

## 7. Mi Fitness Client Design (P14-003)

### Library Selection
- **Primary:** `mi-fitness-mcp` — Xiaomi cloud connector, cookie-based auth
- **Enrichment:** `mi-fitness` SDK — broader metric surface (SpO2, blood pressure)
- **Fallback (v2):** `zepp-life-mcp` — for legacy Huami accounts

### Auth Flow
```
.env.wearable (SOPS-encrypted)
  → MI_FITNESS_USER_ID=<id>
  → MI_FITNESS_PASS_TOKEN=<token>
  → MI_FITNESS_REGION=<region>

Client reads credentials → authenticated requests → token persistence in Redis
On TokenExpiredError → attempt refresh → on CaptchaRequiredError → circuit break + SEV3 alert
```

### Metric Fetch Strategy
```python
class MiFitnessClient:
    """Mi Fitness Cloud API client with circuit breaker and graceful degradation."""

    METRIC_ENDPOINTS = {
        'heart_rate': 'confirmed',
        'steps': 'confirmed',
        'activity': 'confirmed',
        'distance': 'confirmed',
        'calories': 'confirmed',
        'body_measurements': 'confirmed',
        'spo2': 'sdk_available',      # via mi-fitness SDK
        'sleep': 'unconfirmed',        # may not be available
        'stress': 'unconfirmed',
        'hrv': 'unconfirmed',
        'body_battery': 'unconfirmed',
    }

    async def fetch_metrics(self, date_range: DateRange) -> FetchResult:
        """Fetch available metrics. Gracefully skip unavailable ones."""
        results = {}
        for metric, status in self.METRIC_ENDPOINTS.items():
            if status == 'unconfirmed' and not self._sdk_probe(metric):
                results[metric] = MetricResult(status='unavailable')
                continue
            try:
                results[metric] = await self._fetch_single(metric, date_range)
            except (AuthError, RateLimitError) as e:
                self._handle_auth_failure(e)
                raise
            except EndpointDriftError:
                results[metric] = MetricResult(status='endpoint_changed')
                logger.warning(f"Endpoint drift for {metric}")
        return FetchResult(metrics=results)
```

### Circuit Breaker
```
State: CLOSED (normal operation)
  → 3 consecutive failures → OPEN (pause sync, SEV3 alert)
  → After 30 minutes → HALF_OPEN (single retry)
  → Success → CLOSED
  → Failure → OPEN (another 30 min wait)
```

---

## 8. GHI Scoring — Dynamic Weight Rebalance

When metrics are unavailable (common with Mi Fitness Cloud), GHI weights auto-rebalance:

| Metric Available | Default Weight | Rebalanced (if sleep missing) | Rebalanced (if recovery missing) |
|---|---|---|---|
| Sleep | 40% | N/A | 40% |
| Cardio | 20% | 33% | 20% |
| Activity | 20% | 33% | 33% |
| Recovery | 20% | 33% | N/A (redistributed) |

**Suppression rule:** If fewer than 2 pillars have data, GHI is suppressed (not computed). Display: "Insufficient data for GHI."

---

## 9. Alert Severity Matrix

| Severity | Trigger | Action | Quiet Hours |
|---|---|---|---|
| **SEV0** | SpO2 < 90%, HR > 130 sustained >30min | Immediate Discord DM + Gotify + health.anomaly_events | **BYPASS** |
| **SEV1** | SpO2 < 92%, HR anomaly 3+ consecutive days, GHI < 40 2+ days | Discord DM at next active window | Respected |
| **SEV2** | GHI < 55 2+ days, sleep < 5h 3+ days, stress elevated 3+ days | Embed in daily morning summary | Respected |
| **SEV3** | Sync delay > 2h, circuit breaker open, API auth failure | Log + surface in `/wearable-status` | Respected |

**Quiet hours:** 23:00 - 07:00 WIB (configurable in `.env.wearable`)
**Rate limit:** Max 5 alerts/hour per severity. Alert storms → batch + summarize.

---

## 10. Consent Model

### New Scopes
```python
WEARABLE_HEALTH_SCOPES = [
    'wearable-health.heart_rate.explicit',
    'wearable-health.sleep.explicit',
    'wearable-health.activity.explicit',
    'wearable-health.spo2.explicit',
    'wearable-health.stress.explicit',
    'wearable-health.ghi.explicit',      # GHI is derived, needs own consent
    'wearable-health.alerts.explicit',    # alert notifications
]
```

### Consent Flow
1. Operator runs `/wearable-cfg consent grant` → all scopes granted atomically
2. Operator can revoke individual scopes: `/wearable-cfg consent revoke wearable-health.alerts`
3. Consent ledger records every grant/revoke with timestamp + reason
4. Consumer checks consent gate before writing to TimescaleDB
5. **Fail-closed:** No consent = no data stored. Sync still runs but data is discarded with log entry.

---

## 11. Persona Safety Boundaries (from requirements spec §4.7)

### ABSOLUTE RULES (Non-negotiable, from PersonaSafetyPolicy)
1. **NEVER** use health data for confrontation, correction, or punishment
2. **NEVER** mention specific health metrics unless operator asks directly
3. Health data is **ONLY for care context** — no behavioral correction
4. During active argument/distress state: health data is **invisible** to persona engine
5. Contravention = safety boundary violation (ADR-001, ADR-002)

### Mood Modifier Implementation
```python
# src/wearable/mood_integration.py
def compute_health_mood_modifier(ghi: GHIResult) -> MoodModifier:
    """Compute mood modifier from GHI. Does NOT affect yandere FSM state."""
    if ghi.tier == 'excellent':
        return MoodModifier(energy=+0.1, caring=+0.05, tone='upbeat')
    elif ghi.tier == 'good':
        return MoodModifier(energy=0, caring=0, tone='normal')
    elif ghi.tier == 'fair':
        return MoodModifier(energy=-0.05, caring=+0.1, tone='gentle')
    elif ghi.tier == 'poor':
        return MoodModifier(energy=-0.15, caring=+0.2, tone='concerned')
    else:  # critical
        return MoodModifier(energy=-0.2, caring=+0.3, tone='tender')
```

**Key constraint:** This modifier is consumed by `mood_engine.py` as an additive adjustment. It does NOT change `yandere_fsm.py` state transitions. Y-level adjustments are done through existing ritual scheduler, not health data.

---

## 12. Systemd Units

### Sync Timer (every 30 min)
```ini
# systemd/guinevere-wearable-sync.timer
[Unit]
Description=Guinevere Wearable Sync Timer

[Timer]
OnBootSec=120
OnUnitActiveSec=1800
AccuracySec=30
Persistent=true

[Install]
WantedBy=timers.target
```

### Sync Service (oneshot)
```ini
# systemd/guinevere-wearable-sync.service
[Unit]
Description=Guinevere Wearable Mi Fitness Cloud Sync
After=network-online.target redis.service postgresql.service
Wants=network-online.target

[Service]
Type=oneshot
User=guinevere
Group=guinevere
Slice=guinevere.slice
WorkingDirectory=/home/guinevere/code/guinevere
Environment=PYTHONPATH=/home/guinevere/code/guinevere
Environment=PYTHONDONTWRITEBYTECODE=1
Environment=VIRTUAL_ENV=/home/guinevere/code/guinevere/.venv
EnvironmentFile=/home/guinevere/code/guinevere/.env.wearable
ExecStart=/home/guinevere/code/guinevere/.venv/bin/python -m src.wearable.sync
StandardOutput=journal
StandardError=journal
SyslogIdentifier=guinevere-wearable-sync
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=true
ReadWritePaths=/home/guinevere/code/guinevere /home/guinevere/data /home/guinevere/logs

[Install]
WantedBy=multi-user.target
```

### Analysis Timer (daily 04:00 WIB / 21:00 UTC)
```ini
# systemd/guinevere-wearable-analysis.timer
[Unit]
Description=Guinevere Wearable Health Analysis Timer

[Timer]
OnCalendar=*-*-* 21:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

### Analysis Service (oneshot)
```ini
# systemd/guinevere-wearable-analysis.service
[Unit]
Description=Guinevere Wearable Health Analysis
After=network-online.target redis.service postgresql.service
Requires=postgresql.service

[Service]
Type=oneshot
User=guinevere
Group=guinevere
Slice=guinevere.slice
WorkingDirectory=/home/guinevere/code/guinevere
Environment=PYTHONPATH=/home/guinevere/code/guinevere
Environment=PYTHONDONTWRITEBYTECODE=1
Environment=VIRTUAL_ENV=/home/guinevere/code/guinevere/.venv
EnvironmentFile=/home/guinevere/code/guinevere/.env.wearable
ExecStart=/home/guinevere/code/guinevere/.venv/bin/python -m src.wearable.analysis
StandardOutput=journal
StandardError=journal
SyslogIdentifier=guinevere-wearable-analysis
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=true
ReadWritePaths=/home/guinevere/code/guinevere /home/guinevere/data /home/guinevere/logs

[Install]
WantedBy=multi-user.target
```

---

## 13. Package Structure

```
src/wearable/
├── __init__.py
├── config.py              # Settings from .env.wearable
├── mi_fitness_client.py   # Mi Fitness Cloud API client
├── normalizer.py          # API JSON → HealthMetricPayload
├── sync.py                # Oneshot: auth → fetch → normalize → Redis push
├── writer.py              # Redis → TimescaleDB writer
├── baseline.py            # 28-day rolling baseline + warmup state machine
├── anomaly.py             # Metric-specific anomaly detection
├── ghi.py                 # GHI scoring with confidence + dynamic weights
├── mood_integration.py    # GHI → mood_engine modifier
├── alerts.py              # Alert routing (SEV-based, quiet hours)
├── consent.py             # Wearable consent management
├── commands.py            # Discord slash commands
├── metrics.py             # Prometheus metric exporters
├── models.py              # Pydantic models (HealthMetricPayload, GHIResult, etc.)
└── errors.py              # Custom exceptions
```

---

## 14. Risk Register

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Xiaomi changes API endpoints | High | High (pipeline breaks) | Circuit breaker + SEV3 alert + manual token re-extraction procedure documented |
| Token expires without refresh | Medium | Medium (sync pauses) | Token persistence + refresh logic + SEV3 alert on auth failure |
| Captcha/device-untrusted triggered | Medium | High (manual intervention needed) | Alert operator with re-auth instructions. No auto-retry on captcha. |
| Sleep/HRv data never available via API | Medium | Medium (GHI less accurate) | Dynamic weight rebalance. GHI still useful with 3 of 4 pillars. |
| Rate limit on data endpoints | Low | Medium | Exponential backoff. 30-min sync interval is conservative. |
| Account banned by Xiaomi | Low | Catastrophic (pipeline dead) | Documented fallback: Gadgetbridge v2. No aggressive polling. |
| GHI false positive → mood modifier too aggressive | Low | Medium (persona too caring when operator is fine) | GHI confidence model + suppression below 0.4 confidence |

---

## 15. Rollback Plan

1. Disable timers: `sudo systemctl disable --now guinevere-wearable-sync.timer guinevere-wearable-analysis.timer`
2. Drop health schema: `DROP SCHEMA health CASCADE;` (destructive, confirm first)
3. Remove `.env.wearable` and SOPS secrets
4. Revert `consent_gate.py` and `consumer.py` scope additions
5. Remove Discord commands from registry
6. Remove Prometheus scrape job and alert rules
7. Remove Grafana dashboard provisioning

---

## 16. Evidence Requirements

| Step | Evidence File | Content |
|---|---|---|
| P14-001 | `evidence/p14/step-001-schema.md` | Migration output, table verification |
| P14-003 | `evidence/p14/step-003-client.md` | Auth test, metric fetch test |
| P14-006 | `evidence/p14/step-006-writer.md` | Insert/upsert verification, cursor tracking |
| P14-009 | `evidence/p14/step-009-ghi.md` | GHI computation test, confidence model |
| P14-011 | `evidence/p14/step-011-alerts.md` | Alert routing test, quiet hours test |
| P14-014 | `evidence/p14/step-014-systemd.md` | Service status, timer verification |
| P14-020 | `evidence/p14/p14-gate.md` | All AC-WEAR criteria, cross-reference, rollback test |

---

## 17. Auditor Matrix

| Auditor | Scope | Steps |
|---|---|---|
| Security auditor | Token handling, SOPS, encryption at rest, credential rotation | P14-002, P14-003, P14-017 |
| Schema auditor | Migration correctness, hypertable config, retention, indexes | P14-001, P14-006 |
| Integration auditor | End-to-end data flow, consent gate, Redis buffer | P14-005, P14-012, P14-019 |
| Ops auditor | Systemd units, Prometheus, Grafana, alert routing | P14-011, P14-014, P14-015, P14-016 |
| Persona safety auditor | Mood modifier boundaries, yandere isolation, confrontation rule | P14-010, P14-013 |

---

## 18. Step Comparison: Old vs New

| Old Plan (Gadgetbridge) | New Plan (Mi Fitness Cloud) | Change |
|---|---|---|
| 27 steps + 10 gap fills = 37 | **20 steps** | **-17 steps (46% reduction)** |
| Phone + WebDAV + daemon + parser | VPS + API client + normalizer | Much simpler |
| Gadgetbridge SQLite schema issues | JSON API (no schema mismatch) | B1 eliminated |
| Android transport engineering | Python HTTP client | B2, B3 eliminated |
| Device pairing UX | Account linking | B4 simplified |
| APScheduler | Systemd timer | Consistent with Guinevere |
| 8 persona FSM states | Mood modifier only | Safer, less code |

---

## 19. Open Items

1. **Xiaomi account region** — Operator needs to confirm their Mi Fitness account region (`ru`, `cn`, `global`). Affects API endpoints.
2. **Device model** — Xiaomi Watch S3 or Band 9? Affects which metrics the watch reports to Mi Fitness Cloud.
3. **`mi-fitness-mcp` vs `mi-fitness` SDK** — Start with `mi-fitness-mcp`, evaluate `mi-fitness` SDK for broader coverage during P14-003 implementation.
4. **Morning brief integration** — Existing morning brief format needs extension. Separate step or fold into P14-013?
5. **Gadgetbridge v2 scope** — Document v2 plan for raw data access as future enhancement.

---

## Appendix A: AC-WEAR Acceptance Criteria (from requirements spec)

| ID | Criterion | Step Coverage |
|---|---|---|
| AC-WEAR-01 | Health data ingested from Mi Fitness Cloud every 30 min | P14-003, P14-005, P14-014 |
| AC-WEAR-02 | 5 health metrics stored in TimescaleDB hypertables | P14-001, P14-006 |
| AC-WEAR-03 | 28-day baseline computed with warmup stages | P14-007 |
| AC-WEAR-04 | Anomaly detection with metric-specific thresholds | P14-008 |
| AC-WEAR-05 | GHI score computed daily with confidence model | P14-009 |
| AC-WEAR-06 | GHI modifies mood but NOT yandere FSM state | P14-010 |
| AC-WEAR-07 | SEV0 health alerts bypass quiet hours | P14-011 |
| AC-WEAR-08 | Consent grant/revoke for wearable-health scopes | P14-012 |
| AC-WEAR-09 | 4 Discord commands (owner-only) operational | P14-013 |
| AC-WEAR-10 | Systemd timer + service running in production | P14-014 |
| AC-WEAR-11 | Prometheus metrics exported for pipeline health | P14-015 |
| AC-WEAR-12 | Grafana dashboard showing health trends | P14-016 |
| AC-WEAR-13 | Health data encrypted/classified per governance | P14-017 |
| AC-WEAR-14 | Unit tests pass for all wearable modules | P14-018 |
| AC-WEAR-15 | Integration test: full pipeline E2E | P14-019 |
| AC-WEAR-16 | API failure → circuit breaker → SEV3 alert | P14-003 |
| AC-WEAR-17 | Health data NEVER used for confrontation/punishment | P14-010 (code), P14-020 (audit) |
| AC-WEAR-18 | Consent fail-closed: no consent = no data stored | P14-012 |
| AC-WEAR-19 | Unavailable metrics excluded from GHI with weight rebalance | P14-009 |
| AC-WEAR-20 | Rollback procedure documented and tested | P14-020 |
