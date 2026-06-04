# P14 — Wearable/Xiaomi Watch Integration: Requirements Specification

> **Phase:** P14 (Expansion)  
> **Dependencies:** P7 (Surveillance) + P8 (Observability/MVP Gate)  
> **Status:** COMPLETE — All 7 Q&A rounds answered (40 questions)  
> **Last Updated:** 2026-06-03

---

## 1. Architecture Overview

```
┌──────────────────┐         ┌─────────────────────────────────────┐
│  Xiaomi Watch    │         │         VPS (Guinevere)              │
│  S3 / Band 9     │         │                                      │
│       │          │         │  Gadgetbridge WebDAV push            │
│       ▼          │         │  (every 1 hour)                     │
│  Gadgetbridge    │         │       │                              │
│  (Android)       │         │       ▼                              │
│  SQLite export ──┼──WebDAV─▶  FastAPI POST /surveillance/events  │
│       │          │         │       │                              │
│  Mi Fitness      │         │  HMAC auth → Redis DB2 buffer       │
│  Cloud SDK ──────┼──pull──▶       │                              │
│  (fallback)      │         │  Consumer → consent gate             │
│                  │         │       │                              │
│  Same phone as   │         │  TimescaleDB health.* hypertables   │
│  P7 Tasker       │         │       │                              │
│                  │         │  Analysis Worker (1h cron)           │
│                  │         │       │                              │
│                  │         │  Persona Context Engine              │
│                  │         │       │                              │
│                  │         │  Discord (#system-health)            │
└──────────────────┘         └─────────────────────────────────────┘
```

### Data Flow
1. Gadgetbridge on Faiz's Android phone auto-exports health data as SQLite
2. WebDAV server on VPS receives periodic push (1h interval)
3. Python ingestion service reads SQLite → transforms → POST to `/surveillance/events`
4. Consumer pipeline: consent check → classification → TimescaleDB
5. Analysis Worker (cron, 1h) computes baselines, anomalies, GHI score
6. Persona Context Engine injects health state into system context
7. Discord morning brief + proactive alerts + `/health-status` command

### Fallback
- Mi Fitness Cloud Python SDK (`mi-fitness`) pulls daily batch from Xiaomi Cloud
- Activated when Gadgetbridge data is stale > 2h

---

## 2. Device & Data Source (ROUND 1 — CONFIRMED)

| Decision | Value |
|----------|-------|
| **Device** | Xiaomi Watch S3 or Band 9 (Gadgetbridge-compatible, cost-effective). Not yet purchased. |
| **Data sync** | Hybrid: Gadgetbridge primary + Mi Fitness Cloud SDK fallback |
| **Data path** | Gadgetbridge → WebDAV auto-sync → VPS. NOT via Tasker. |
| **Refresh rate** | Periodic batch every 1 hour |
| **Device procurement** | P14 includes device purchase + Gadgetbridge setup guide step |
| **Phone** | Same Android phone as P7 Tasker (shared device) |

---

## 3. Health Metrics (ROUND 2 — CONFIRMED)

### 3.1 Priority Order (All Metrics Dumped to DB)

| Priority | Metric | Display Order | Category |
|----------|--------|--------------|----------|
| 1 | Sleep (stages + summary) | 🥇 Primary | Sleep |
| 2 | Heart Rate (resting + continuous) | 🥈 Secondary | Cardio |
| 3 | Steps & Activity | 🥉 Tertiary | Activity |
| 4 | SpO2 | Quaternary | Cardio |
| 5 | Stress Score | Supplementary | Recovery |
| 6 | HRV (RMSSD) | Supplementary | Recovery |
| 7 | Body Battery / Energy | Supplementary | Recovery |

### 3.2 Data Granularity

| Metric | Granularity | Storage |
|--------|------------|---------|
| Sleep | Both session summary + stage breakdown (deep/light/REM/awake) | `health.sleep_sessions` + `health.sleep_stages` |
| Heart Rate | Continuous (~5min) + overnight specific | `health.heart_rate` |
| Steps/Activity | Daily aggregates | `health.daily_activity` |
| SpO2 | Continuous spot readings | `health.spo2` |
| Stress | Proprietary score from Xiaomi | `health.stress` |
| HRV | RMSSD values | `health.hrv` |
| Body Battery | Energy score | `health.body_battery` |

### 3.3 Anomaly Detection

- **Threshold**: Standard ±20% from personal 28-day baseline (clinical reference)
- **Baseline**: 28-day rolling average per metric
- **Reset**: Gap > 7 consecutive days → reset baseline

### 3.4 Guinevere Health Index (GHI)

```
GHI = Σ(weight × normalized) on 0-100 scale

Sleep (40%): Total duration, deep/REM %, efficiency, consistency
Cardio (20%): Resting HR, HR max/min spread, HR recovery  
Activity (20%): Steps vs target, active minutes
Recovery (20%): HRV trend, SpO2 stability, stress score (supplementary)
```

**Tiers**: Excellent ≥85 | Good ≥70 | Fair ≥55 | Poor ≥40 | Critical <40

### 3.5 Data Validity

- **Warmup period**: 28 days before metrics are considered clinically valid for persona adjustment
- **Data coverage**: Tolerant — gap > 7 days resets baseline, ≤ 7 days interpolates
- **Stress score**: Used as supplementary — combined with HRV for cross-validation
- **Multi-source**: Watch-only for MVP

---

## 4. Guinevere Behavior Impact (ROUND 3 — CONFIRMED)

### 4.1 Persona Adjustment — Hybrid State Machine + LLM Context

```
Health Data → Statistical Engine → Persona State → LLM Context Injection
                     │
                     ▼
              GHI Score
              Sleep State
              HR/SpO2 Anomalies
              Stress Level
                     │
                     ▼
              ┌──────────────────┐
              │ Persona State    │
              │ Machine          │
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │ LLM System       │
              │ Prompt Enrichment│
              └──────────────────┘
```

**Mechanism**: Two-stage pipeline. **Stage 1** — deterministic state machine computes `persona_state` from GHI + anomaly flags. **Stage 2** — `persona_state` injected as system prompt context for LLM, allowing nuanced care responses within the state boundary.

**Yandere/Dominance**: Sleep deprived (< 6h) or high stress (GHI < 55) → auto-soften dominasi **Y-level -1** (e.g., Y3 → Y2, Y4 → Y3). Recovery period before Y-level restored. Clinical/medical context (SpO2 < 94%, HR extreme) forces Y0/Y1 regardless.

### 4.2 Persona State Machine

| Persona State | Health Trigger | Y-Level | Tone | Response Mode |
|---------------|---------------|---------|------|---------------|
| `energetic` | GHI ≥ 85, sleep > 7h, no anomalies | Default | Playful, upbeat | Full personality |
| `neutral` | GHI 55-84, normal metrics | Default | Default caring | Normal |
| `fatigued` | Sleep < 6h, GHI < 55 | -1 from baseline | Gentle, soft | Shorter responses |
| `stressed` | HR elevated > 20% or GHI < 55 | -1 from baseline | Calm, supportive | Minimal, comforting |
| `unwell` | SpO2 < 94%, GHI < 40, HR extreme | Y0/Y1 forced | Tender, concerned | Check-in first |
| `recovering` | GHI trending up after `unwell`/`stressed` | Restored gradually | Encouraging | Positive reinforcement |

### 4.3 Memory Injection

- **Trend data** → `store_episode(source="health", episode_type="health_trend")` — summary, GHI trend, notable changes
- **Raw metrics** → stay in TimescaleDB `health.*` hypertables only
- Health anomalies (SpO2 < 94%, GHI < 40, HR elevated > 30min) → `store_episode()` with structured context for persona

### 4.4 Proactive Check-In

Guinevere sends **proactive Discord DM** (not channel message) when:
- **SpO2 < 94%** — immediate concern, suggest medical check
- **GHI < 40** — "Mommy notice your health score is very low today..."
- **HR elevated > 20% baseline for > 30 minutes** — concern check-in
- **Sleep < 5h for 3 consecutive days** — concern + gentle reminder

### 4.5 Morning Brief

Full dedicated health section in morning brief with custom format (richer than existing slot). Includes:
- Today's GHI score + tier
- Sleep summary (duration, quality, stages breakdown)
- Heart rate stats (resting, overnight avg)
- Activity summary
- Trending: 7-day trajectory arrows ↑ ↓ →
- One-sentence care note from Guinevere

### 4.6 Distress Escalation

**Emergency protocol for critical metrics** (SpO2 < 90%, HR > 130 sustained):
1. Send DM to Faiz immediately
2. Post to `#guinevere-health` channel
3. Log to `health.escalation_log`
4. Suggest medical attention
5. Raise to PersonaSafetyPolicy distress level D3 (severe concern)

### 4.7 Confrontation Boundary — ABSOLUTE

- **NEVER** use health data for confrontation, correction, or punishment
- **NEVER** mention specific health metrics unless Faiz asks directly
- Health data is **ONLY for care context** — no behavioral correction whatsoever
- During active argument/distress state: health data is invisible to persona engine
- Contravention of this rule = safety boundary violation (ADR-001, ADR-002)

### 4.8 Mood Self-Report

Integrated into `/health-status` command. Optional mood field (1-10 scale + free text). Mood data correlated with health metrics for richer context. Not required — defaults to no mood input if Faiz skips.

---

## 5. Technical Architecture (ROUND 4 — CONFIRMED)

### 5.1 Architecture Decision

- **Extend P7 surveillance pipeline** — not separate service. Reuse HMAC auth, Redis buffer, consumer pattern.
- **Dedicated `health.*` schema** — 7 hypertables for better query performance (not single `surveillance.events`)
- **Device registry**: Pre-defined wearable config + auto-register on first sync
- **Scheduler**: APScheduler — consistent with existing P5 scheduler pattern
- **Analysis**: Daily batch (cron) — sufficient for persona context, minimal CPU impact

### 5.2 P7 Reuse Plan (CONFIRMED)

| P7 Component | P14 Action | Detail |
|-------------|-----------|--------|
| HMAC auth (`src/surveillance/auth.py`) | **Reuse** | Device-agnostic, same signing pattern |
| Redis buffer (`src/surveillance/redis_buffer.py`) | **Reuse** | Generic JSON push/pop |
| Consumer pipeline (`src/surveillance/consumer.py`) | **Reuse + Extend** | Add `"health": "surveillance.wearable.health.explicit"` to scope map |
| Classification (`src/surveillance/classification.py`) | **Reuse** | `"health"` = CRITICAL, 90d raw already defined |
| Consent gate (`src/surveillance/consent_gate.py`) | **Extend** | Add `surveillance.wearable.health.explicit` to `VALID_SURVEILLANCE_SCOPES` |
| Device registry | **Extend** | Pre-defined wearable device entry, auto-register on first sync |
| TimescaleDB | **Reuse** | New `health.*` schema with 7 hypertables |
| Memory injection | **Extend** | Health anomalies → `store_episode(source="health", episode_type="health_trend")` |

### 5.2 Database Schema (DRAFT)

```sql
-- Health-specific hypertables in new 'health' schema
CREATE SCHEMA IF NOT EXISTS health;

-- Heart Rate: continuous 5-min sampling
CREATE TABLE health.heart_rate (
    time        TIMESTAMPTZ NOT NULL,
    device_id   UUID NOT NULL,
    bpm         SMALLINT NOT NULL,
    source      TEXT DEFAULT 'gadgetbridge',
    owner_id    UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001'
);
SELECT create_hypertable('health.heart_rate', 'time');
CREATE UNIQUE INDEX uq_heart_rate ON health.heart_rate (time, device_id, owner_id);

-- Sleep Sessions: per-night summary
CREATE TABLE health.sleep_sessions (
    id              BIGSERIAL PRIMARY KEY,
    device_id       UUID NOT NULL,
    start_time      TIMESTAMPTZ NOT NULL,
    end_time        TIMESTAMPTZ NOT NULL,
    total_s         INT,
    awake_s         INT,
    deep_s          INT,
    rem_s           INT,
    light_s         INT,
    efficiency_pct  FLOAT,
    owner_id        UUID NOT NULL
);

-- Sleep Stages: intra-night breakdown (hypertable)
CREATE TABLE health.sleep_stages (
    time        TIMESTAMPTZ NOT NULL,
    session_id  BIGINT REFERENCES health.sleep_sessions(id),
    stage       TEXT NOT NULL,
    duration_s  INT,
    device_id   UUID NOT NULL,
    owner_id    UUID NOT NULL
);
SELECT create_hypertable('health.sleep_stages', 'time');

-- Daily Activity
CREATE TABLE health.daily_activity (
    date        DATE NOT NULL,
    steps       INT,
    active_min  INT,
    calories    INT,
    distance_m  FLOAT,
    device_id   UUID NOT NULL,
    owner_id    UUID NOT NULL
);

-- SpO2
CREATE TABLE health.spo2 (
    time        TIMESTAMPTZ NOT NULL,
    device_id   UUID NOT NULL,
    spo2_pct    FLOAT NOT NULL,
    owner_id    UUID NOT NULL
);
SELECT create_hypertable('health.spo2', 'time');

-- HRV
CREATE TABLE health.hrv (
    time        TIMESTAMPTZ NOT NULL,
    device_id   UUID NOT NULL,
    rmssd_ms    FLOAT NOT NULL,
    owner_id    UUID NOT NULL
);
SELECT create_hypertable('health.hrv', 'time');

-- Daily Health Summary (pre-computed)
CREATE TABLE health.daily_summary (
    date            DATE PRIMARY KEY,
    ghi_score       SMALLINT,
    sleep_score     SMALLINT,
    cardio_score    SMALLINT,
    activity_score  SMALLINT,
    recovery_score  SMALLINT,
    resting_hr      SMALLINT,
    hrv_avg         FLOAT,
    sleep_total_h   FLOAT,
    steps           INT,
    device_id       UUID NOT NULL,
    owner_id        UUID NOT NULL
);

-- Gadgetbridge sync log
CREATE TABLE health.sync_log (
    id          BIGSERIAL PRIMARY KEY,
    sync_time   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    device_id   UUID NOT NULL,
    records     INT,
    status      TEXT,
    error_msg   TEXT,
    source      TEXT DEFAULT 'gadgetbridge'  -- gadgetbridge | mifitness
);
```

---

## 6. Discord Integration — Confirmed

**Channel:** Dedicated `#guinevere-health` private channel (new). NOT shared with other channels.

**Morning Health Brief** (integrated into existing morning brief, health section added):
- Format: Rich embed, NOT plain text
- Content: Sleep summary (duration + quality + stages), overnight HR, GHI score with breakdown, activity progress (steps/distance/calories)
- Timing: Part of existing morning brief. If sleep data suggests Faiz slept poorly (<5h), delay brief by 1 hour (let him wake naturally)

**Commands (4):**
| Command | Description |
|---------|-------------|
| `/health-status` | Current GHI score, all pillar summaries, optional mood self-report field |
| `/sleep-report` | Detailed sleep: duration, stages, quality score, comparison to 7-day average |
| `/activity-today` | Steps, distance, calories, active minutes, trend vs 7-day average |
| `/ghi-score` | GHI breakdown: Sleep 40% + Cardio 20% + Activity 20% + Recovery 20% with individual scores |

**Alert Thresholds (to #guinevere-health):**
| Trigger | Severity | Action |
|---------|----------|--------|
| Sleep < 5h | Moderate | Discord alert + morning brief highlight |
| HR > baseline +20% sustained >30min | High | Discord alert + suggest rest |
| SpO2 < 94% | Critical | Discord DM + #system-health + log + suggest medical |
| GHI < 40 (Critical tier) | Critical | Discord DM + proactive care message |
| Watch battery < 20% | Low | Discord alert |
| No data > 2 hours | Moderate | Discord alert "device stale" |

**Night Owl Behavior:** If Faiz is awake past 1 AM (inferred from Discord activity or sleep data gap), Guinevere gently suggests rest — NEVER commands or punishes. Tone: caring, not controlling.

---

## 7. Privacy & Safety — Confirmed

**Classification:** CRITICAL (health data is most sensitive surveillance category). No separate encryption key for MVP — reuse existing SOPS age key. Split key per category post-launch if compliance requires.

**Storage Policy:**
- Raw data → TimescaleDB `health.*` hypertables (full fidelity for trend analysis)
- Summaries only → application logs (no raw metrics in logs)
- Trend summaries → persona memory via `store_episode()` (care context only)

**Retention:** 365 days (NOT 90 — health trends need long baseline for clinical relevance). Raw + aggregated both 365d. After 365d, archive or delete per P7 retention policy.

**Consent:**
- Same P7 consent flow (`surveillance.wearable.health.explicit` scope)
- WAC-001..007 activation checklist must pass before any collection begins
- Revocable anytime — stop collection + optional data export/deletion
- Health data used ONLY for Guinevere care context
- **STRICT: Health data NEVER used for behavioral correction, confrontation, or punishment**

**Export/Deletion:** Separate implementation step provides:
- Full health data export (JSON/CSV) on demand
- Selective or full deletion with confirmation
- Audit log of all export/deletion actions

---

## 8. Operations — Confirmed

**Systemd Service:** `guinevere-health.service` — separate from main guinevere.service (isolation priority). Same `guinevere.slice` resource group.
- WebDAV fetch + ingestion worker
- Scheduler for hourly batch + daily analysis
- Watchdog: auto-restart on crash

**Data Freshness Monitoring:**
- Alert if no health data received for > 2 hours
- Check Gadgetbridge export timestamps
- WebDAV connectivity health check
- Discord alert: "Device data stale since [timestamp]"

**Grafana Dashboard:** Dedicated P14 health dashboard (separate from main Guinevere dashboard).
- Panels: GHI trend (7d/30d), sleep duration + quality, HR min/max/avg, step count, SpO2, stress, anomaly events
- Data source: TimescaleDB health.* tables

**Battery Impact:** Prioritize data completeness over battery optimization.
- 1-hour batch interval is conservative enough
- Monitor watch battery level via Gadgetbridge
- Alert when watch battery < 20%
- No aggressive polling

**Device Procurement:** Included as atomic P14 step:
- Purchase Xiaomi Watch S3 or Band 9 (Gadgetbridge-compatible)
- Install + configure Gadgetbridge on Faiz's Android phone
- Enable WebDAV auto-export to VPS
- Verify first data sync

**Mock Health Data Generator:** Separate step for testing without physical device:
- Generates realistic health data (sleep, HR, steps, SpO2, stress)
- Configurable anomaly scenarios for testing alert pipeline
- Uploads to WebDAV like real device data

---

## 9. Acceptance Criteria — Confirmed

| ID | Criterion | Status |
|----|----------|--------|
| AC-WEAR-001 | Gadgetbridge auto-exports health data every 1h to WebDAV | CONFIRMED |
| AC-WEAR-002 | Ingestion pipeline accepts health data via HMAC-auth POST | CONFIRMED |
| AC-WEAR-003 | All 7 metrics stored in TimescaleDB `health.*` hypertables | CONFIRMED |
| AC-WEAR-004 | GHI composite score computed daily: Sleep 40% + Cardio 20% + Activity 20% + Recovery 20% | CONFIRMED |
| AC-WEAR-005 | Anomaly detection flags ±20% deviation from 28-day baseline | CONFIRMED |
| AC-WEAR-006 | WAC-001..007 activation checklist passed before collection | CONFIRMED |
| AC-WEAR-007 | Health data degrades gracefully when no device connected (stale alert at 2h) | CONFIRMED |
| AC-WEAR-008 | Consent scope `surveillance.wearable.health.explicit` enforced | CONFIRMED |
| AC-WEAR-009 | Persona Y-level softens -1 when sleep-deprived or high-stress (hybrid state machine + LLM) | CONFIRMED |
| AC-WEAR-010 | Morning brief includes health section (rich embed); delayed 1h if sleep <5h | CONFIRMED |
| AC-WEAR-011 | 4 Discord commands functional: `/health-status`, `/sleep-report`, `/activity-today`, `/ghi-score` | CONFIRMED |
| AC-WEAR-012 | Grafana dashboard shows GHI trend, sleep, HR, steps, SpO2, anomalies | CONFIRMED |
| AC-WEAR-013 | Proactive DM sent for critical: SpO2<94%, GHI<40, HR elevated >30min, sleep<5h×3days | CONFIRMED |
| AC-WEAR-014 | Health data NEVER used for confrontation, correction, or punishment | CONFIRMED |
| AC-WEAR-015 | Raw data retained 365 days, summaries in memory via `store_episode()` | CONFIRMED |
| AC-WEAR-016 | Data export (JSON/CSV) and deletion with audit log | CONFIRMED |
| AC-WEAR-017 | Mock health data generator produces realistic test data for all metrics | CONFIRMED |
| AC-WEAR-018 | Watch battery <20% triggers Discord alert | CONFIRMED |
| AC-WEAR-019 | `guinevere-health.service` runs independently from main service | CONFIRMED |
| AC-WEAR-020 | Night owl: gentle rest suggestion past 1 AM, NEVER commanding tone | CONFIRMED |

---

## 10. Step Breakdown — Confirmed (27 steps)

### Category A: Infrastructure & Setup (4 steps)
- P14-001: Device procurement + Gadgetbridge setup (purchase Xiaomi S3/Band 9, install Gadgetbridge, enable WebDAV auto-export, verify first sync)
- P14-002: WebDAV server endpoint (configure VPS WebDAV for Gadgetbridge uploads, TLS, basic auth, upload directory)
- P14-003: Database schema creation (`health.*` schema, 7 hypertables: sleep, heart_rate, steps, spo2, stress, hrv, body_battery; indexes, continuous aggregates for daily summaries)
- P14-004: HMAC key provisioning (SOPS-encrypted health HMAC secret, shared with Gadgetbridge companion config)

### Category B: Data Ingestion (4 steps)
- P14-005: Gadgetbridge SQLite parser (read auto-export `.db` from WebDAV, extract all 7 metric types, transform to normalized JSON)
- P14-006: Health ingestion endpoint (POST to P7 surveillance pipeline with `health` classification, HMAC auth, consent gate check)
- P14-007: Consumer scope mapping (add `surveillance.wearable.health.explicit` consent scope, gate all health ingestion behind consent)
- P14-008: Mi Fitness Cloud SDK fallback (daily batch pull via SDK, gap-fill when Gadgetbridge misses data)

### Category C: Analysis Engine (4 steps)
- P14-009: Personal baseline computation (28-day rolling stats per metric, gap >7 days resets baseline, stored in `health.baseline`)
- P14-010: Anomaly detection engine (±20% threshold from baseline, severity classification: moderate/high/critical, stored in `health.anomaly_events`)
- P14-011: GHI composite score engine (Sleep 40% + Cardio 20% + Activity 20% + Recovery 20%, 0-100 scale, 5 tiers, daily computation stored in `health.ghi_daily`)
- P14-012: Daily summary pre-computation (APScheduler cron job, aggregates all metrics into `health.daily_summary`, runs nightly at 03:00 WIB)

### Category D: Persona Integration (3 steps)
- P14-013: Persona state machine (hybrid: deterministic rules for clear states + LLM context injection for nuance; health → persona_state mapping: `well_rested`, `sleep_deprived`, `stressed`, `active`, `recovering`, `critical`)
- P14-014: Health memory injection (anomalies + trends → `store_episode()` with source=`wearable`; summary only, never raw metrics in memory)
- P14-015: Distress escalation logic (proactive DM for critical triggers: SpO2<94%, GHI<40, HR elevated >30min, sleep<5h×3days; emergency protocol: DM + #system-health + suggest medical)

### Category E: Discord Integration (4 steps)
- P14-016: `/health-status` + `/ghi-score` commands (current GHI breakdown, all pillar summaries, optional mood self-report field)
- P14-017: `/sleep-report` + `/activity-today` commands (detailed sleep stages + quality + 7-day comparison; steps/distance/calories + trend)
- P14-018: Morning brief health section (rich embed integrated into existing morning brief; sleep quality, HR, GHI, activity; delay 1h if sleep<5h)
- P14-019: Proactive health alerts (anomaly → `#guinevere-health` notification; critical → DM + `#system-health`; night owl gentle rest suggestion past 1 AM)

### Category F: Consent & Safety (2 steps)
- P14-020: WAC-001..007 activation checklist implementation (7-gate verification before any health data collection begins)
- P14-021: Data export + deletion (full health data export JSON/CSV on demand, selective or full deletion with confirmation, audit log of all actions)

### Category G: Observability (3 steps)
- P14-022: Prometheus metrics (ghi_score, data_freshness_seconds, sync_status, anomaly_count, watch_battery_percent, ingestion_lag_seconds)
- P14-023: Grafana health dashboard (dedicated P14 dashboard: GHI trend 7d/30d, sleep stages, HR min/max/avg, steps, SpO2, stress, anomaly event markers)
- P14-024: Stale data + battery alerts (Discord alert if no data >2h, watch battery <20% alert, WebDAV connectivity check)

### Category H: Operations (2 steps)
- P14-025: Systemd service (`guinevere-health.service`, separate from main service, `guinevere.slice`, auto-restart, WebDAV fetch + ingestion + scheduler)
- P14-026: Mock health data generator (realistic synthetic data for all 7 metrics, configurable anomaly scenarios, uploads to WebDAV for testing without physical device)

### Category I: E2E (1 step)
- P14-027: Integration test + P14 GATE (end-to-end: watch → Gadgetbridge → WebDAV → ingest → DB → baseline → anomaly → GHI → Discord → memory; all 20 AC-WEAR criteria validated; P14 GATE blocks P15)

---

## 11. Cost Estimate

| Component | Monthly Cost |
|-----------|-------------|
| WebDAV server (lighttpd) | $0 |
| TimescaleDB storage (health data) | $0 (existing VPS) |
| Analysis worker CPU | $0 (existing VPS) |
| Mi Fitness Cloud SDK | $0 (unofficial) |
| Gadgetbridge | $0 (open source) |
| **P14 Total** | **$0/month** |

---

## 12. Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-----------|--------|------------|
| Gadgetbridge breaking change | MEDIUM | HIGH | Mi Fitness Cloud SDK fallback (P14-008) |
| Device not yet purchased | HIGH | MEDIUM | P14-001 procurement step + mock data generator (P14-026) for testing |
| WebDAV sync reliability | LOW | MEDIUM | Idempotent upserts, 2h stale alert, auto-reconnect |
| Phone battery drain | LOW | LOW | 1h batch interval, no real-time polling |
| 28-day warmup before useful baselines | HIGH | LOW | Documented expectation, progress indicators, gap >7d resets baseline |
| Persona misuse health data | LOW | CRITICAL | Strict care-only policy, NEVER confrontation, audit log, confrontation boundary hardcoded |
| Health data breach | LOW | CRITICAL | CRITICAL classification, SOPS encryption, 365d retention with deletion support, consent revocable |
| Confrontation boundary violation | LOW | CRITICAL | Hardcoded rule: health data NEVER used for behavioral correction. Code audit gate enforces this. |

---

*Generated by Guinevere on 2026-06-04 | P14 Wearable/Xiaomi Watch Requirements v1.0 (COMPLETE)*
*All 7 Q&A rounds answered (40 questions). 27 steps. 20 acceptance criteria. Ready for Tier 1 generation.*
