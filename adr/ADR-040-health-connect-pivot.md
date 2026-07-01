---
adr: 040
title: "Health Connect as Primary Wearable Data Source"
status: "Accepted"
date: "2026-06-19"
deciders:
  - "Faiz (Owner, solo developer Indonesia)"
  - "Guinevere (Executor / autonomous system steward)"
tags:
  - wearable
  - health
  - health-connect
  - android
  - xiaomi
  - mood-modifier
  - consent
  - privacy
risk_level: "HIGH"
supersedes: "Supersedes ADR-039 (Gadgetbridge SQLite path) and ADR-037 (Mi Fitness Cloud path). Both prior paths remain in the repository as fallback for non-Xiaomi devices."
related_documents:
  - ADR-001
  - ADR-002
  - ADR-021
  - ADR-022
  - ADR-024
  - ADR-032
  - ADR-037
  - ADR-039
  - docs/00-core/02-TechnicalArchitecture_v2.0.md
  - docs/30-data/30-DataGovernance_Classification_v1.0.md
  - docs/30-data/31-SurveillanceDataPolicy_v1.0.md
  - docs/30-data/32-ConsentRevocationPolicy_v1.0.md
  - docs/60-persona/60-PersonaSafetyPolicy_v1.0.md
  - docs/setup-evidence/p14-expansion/evidence-p14-expansion.md
  - research-reports/p14-health-connect-enterprise-plan.md
  - research-reports/p14-health-connect-api.md
  - research-reports/p14-health-connect-normalizer-mapping.md
---

# ADR-040: Health Connect as Primary Wearable Data Source

> **Numbering note.** Phase 14 has now seen three pivots in eight days. ADR-037
> (Mi Fitness Cloud API, 2026-06-18) was the first accepted path. ADR-039
> (Gadgetbridge SQLite parser, 2026-06-18) was added as a sibling option
> when the Mi Fitness SDK proved unable to query self-data. ADR-040 documents
> the third and current canonical path: Android Health Connect, which is the
> official health data aggregation layer shipped with Android 14+. The
> Xiaomi Watch 2 Pro (M2233W1) runs HyperOS, which Gadgetbridge cannot pair
> with. The Mi Fitness app on the same phone does write to Health Connect,
> which means the data is available through a vendor-neutral, SDK-stable API.
> ADR-037 and ADR-039 remain Accepted as sibling options for non-Xiaomi and
> non-Health-Connect-capable devices, and as fallback when Health Connect
> exports are not available.

## Status

Accepted

## Date

2026-06-19

## Deciders

Faiz (Owner, solo developer Indonesia); Guinevere (Executor / autonomous system steward)

## Tags

wearable, health, health-connect, android, xiaomi, mood-modifier, consent, privacy

## Risk Level

HIGH

## Supersedes

Supersedes ADR-039 (Gadgetbridge SQLite parser) and ADR-037 (Mi Fitness Cloud API) as the canonical P14 wearable ingestion path. Both ADRs remain Accepted as fallback options. The Xiaomi Watch 2 Pro (M2233W1) with HyperOS is unsupported by Gadgetbridge, and the Mi Fitness Cloud SDK only queries relatives rather than the bound user's own data. Health Connect is the official Android health data aggregation layer, written to by Mi Fitness, and requires no root. The downstream pipeline (Redis DB2 buffer, TimescaleDB writer, baseline, anomaly, GHI, mood modifier, alert router, Discord surface) is unchanged from ADR-037 and ADR-039.

## Related Documents

| Document | Relationship |
|---|---|
| ADR-001 | Persona safety and ethical boundary |
| ADR-002 | User autonomy and safe word enforcement |
| ADR-021 | Wearable integration post-MVP (deferral) |
| ADR-022 | Communication channel strategy |
| ADR-024 | Data governance and classification policy |
| ADR-032 | Backup storage strategy (S3 + R2) |
| ADR-037 | Mi Fitness Cloud path (sibling, fallback for non-Xiaomi) |
| ADR-039 | Gadgetbridge SQLite path (sibling, fallback for non-HyperOS) |
| Technical Architecture v2.0 | Runtime architecture, VPS topology |
| Data Governance & Classification Policy | CRITICAL classification of health data |
| Surveillance Data Policy | 365-day retention, care-only usage |
| Consent & Revocation Policy | Consent gating for wearable-health.* scopes |
| Persona Safety Policy | Y4 baseline / Y5 ceiling / Y6 prohibition |
| P14 expansion evidence | Master evidence file (this update appended) |
| P14 Health Connect enterprise plan | Architecture and reuse analysis |
| P14 Health Connect API | Health Connect SDK reference |
| P14 Health Connect normalizer mapping | Record type to metric mapping |

## Context

Phase 14 began with a Gadgetbridge-on-Android-with-WebDAV plan (P14-001
through P14-027, all archived as legacy). ADR-037 replaced that plan with a
direct Mi Fitness Cloud API to VPS path. ADR-039 added a Gadgetbridge SQLite
parser path as a sibling option when the Mi Fitness Cloud SDK proved unable
to query self-data through the unofficial `mifit` PyPI package. Both paths
landed in the same `health.*` schema and shared the downstream pipeline.

During a live device check on 2026-06-19, two blocking constraints emerged:

1. **Xiaomi Watch 2 Pro (M2233W1) is unsupported by Gadgetbridge.** The
   watch runs HyperOS rather than Mi Fitness firmware, and Gadgetbridge's
   device compatibility list does not include the M2233W1 model. Pairing
   fails silently and the device never appears in the Gadgetbridge app.
2. **Mi Fitness Cloud API only exposes relative data.** The unofficial SDK
   reverse-engineered from `api-mifit.huami.com` queries a relative account
   (typically the bound user's profile), not the user's own records. Direct
   self-data reads return 403. There is no documented programmatic endpoint
   for self-data, and the QR-code token export requires a manual workstation
   step that does not survive VPS-side automation.

The same operator hardware setup does have a working path: the Mi Fitness
app on the Android phone is already configured to write the watch's health
metrics (heart rate, steps, SpO2, sleep, active calories) to Android Health
Connect. Permissions were granted on 2026-06-19 and the Health Connect
database shows 1.5 MB of recent samples. Health Connect is the official
Android health data aggregation layer (added in Android 14, with a Jetpack
SDK for older releases). It exposes a stable, documented API across vendor
boundaries, requires no root, and decouples the phone-side data source from
the downstream pipeline.

Canonical v2.0 decisions inherited by this ADR (unchanged from ADR-037 and
ADR-039):

- Health data is CRITICAL classification (per ADR-024 / Data Governance
  Policy).
- Consent is required for any `wearable-health.*` scope (per
  ConsentRevocationPolicy).
- Y4 baseline, Y5 ceiling, Y6 absolute prohibition (per Persona Safety
  Policy).
- Memory uses PostgreSQL + Redis; no SQLite in the memory layer.
  TimescaleDB extension for time-series.
- Persona NEVER uses health data for confrontation, correction, or
  punishment.
- VPS primary hosts PostgreSQL, Redis, Prometheus, Grafana.
- HMAC keys, SOPS/age encryption, and health-data consent gates apply as
  before.

## Decision Drivers

- Health data is among the most privacy-sensitive data the system
  handles. The decision must minimize persistent secrets, vendor lock-in,
  and external attack surface.
- The owner is the sole user. Convenience and reliability outrank
  multi-tenant scale considerations.
- Persona safety depends on health data being a *modifier* (soft signal),
  not a *trigger* (hard rule). The architecture must make this technically
  enforceable on every ingestion path.
- The implementation must be auditable through file-based evidence and
  reversible through a one-step config switch (`WEARABLE_DATA_SOURCE`) with
  no schema migration required.
- Canonical v2.0 documentation must remain internally consistent. This ADR
  documents a new canonical path; ADR-037 and ADR-039 are preserved as
  fallback options for non-Xiaomi or non-Health-Connect devices.

## Considered Options

1. **Android Health Connect export to JSON, then VPS parse.** Chosen.
2. **Mi Fitness Cloud API to VPS (direct, server-to-server).** Sibling
   option under ADR-037, kept as fallback for cases where the operator
   pairs a non-Xiaomi watch.
3. **Gadgetbridge SQLite parser on VPS.** Sibling option under ADR-039,
   kept as fallback for cases where the watch is Gadgetbridge-compatible.
4. **Custom phone companion app with full polling.** Rejected: duplicates
   what Health Connect already provides, requires root or accessibility
   permissions, and adds maintenance surface area for no accuracy gain.
5. **Defer wearable health data to a later phase (status quo of ADR-021).**
   Rejected: existing P14 implementation is sound; only the ingestion edge
   needed replacing.

## Decision Outcome

Chosen option: **Android Health Connect JSON export, parsed on VPS**.

The data path is:

- A minimal Kotlin app on the Android phone reads five Health Connect
  record types (HeartRate, Steps, OxygenSaturation, SleepSession,
  ActiveCaloriesBurned) and writes them to a single JSON file at
  `/sdcard/Download/health-connect-export/export.json`. The app is launched
  manually by the operator (no background service, no auto-export).
- The operator pulls the JSON via `adb pull`, then SCPs it to the VPS at
  `/var/lib/guinevere/health-connect-export/export.json`.
- `src/wearable/health_connect_client.py` parses the JSON, calls into the
  existing normalizer with `MetricSource.HEALTH_CONNECT`, and feeds the
  downstream pipeline (Redis DB2 buffer, TimescaleDB writer, baseline,
  anomaly, GHI, mood modifier, alert router, Discord surface).
- `WEARABLE_DATA_SOURCE=health_connect` in `.env.wearable` activates the
  path. Switching back to Mi Fitness Cloud or Gadgetbridge is a single env
  var change with zero downtime.

The phone, the Kotlin app, and Health Connect are explicitly in scope for
this implementation. The Kotlin app is the smallest viable surface: one
activity, six supporting files, no background service. Health Connect is the
official API. The SDK is published as part of Jetpack and ships stable
record types across Android versions.

## Consequences

### Positive

- Removes the Gadgetbridge device-compatibility constraint and the Mi
  Fitness Cloud SDK relative-account constraint in one move.
- Uses the official Android health data aggregation API. No root required.
  No QR-code auth dance. No reverse-engineered schema.
- Health Connect record types are vendor-neutral. If the operator swaps
  the Xiaomi watch for another vendor's wearable, the same Health Connect
  path keeps working as long as the vendor app writes to Health Connect.
- 85% of the existing P14 code is reused. Consent gate, Redis buffer,
  writer, baseline, anomaly, GHI, mood modifier, alert router, Discord
  surface all remain source-agnostic.
- A future migration is a single env var change with zero downtime.
- Health Connect is documented by Google. SDK version changes go through
  standard Android deprecation cycles, not silent vendor breakage.

### Negative

- Manual export step. The operator must press a button in the Kotlin app,
  run `adb pull`, and SCP the file. No background sync, no automatic
  schedule.
- Stress metric is not available in Health Connect. The GHI's 20% recovery
  component degrades to a partial signal, same as the Gadgetbridge path.
- Health Connect SDK version changes could require code updates. The
  Kotlin app is small enough that this is a low-effort follow-up.
- The Kotlin app adds a small piece of phone-side code to maintain.
  Mitigation: it is six files, 399 LOC in MainActivity, no background
  service, no daemon.

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Health Connect SDK deprecation | Low (Android standard cycle) | Medium | Bounded Kotlin surface; SDK version pinned in build.gradle |
| Operator forgets to export | Medium | Low | Stale-data Prometheus metric; system continues with prior buffer |
| Health Connect permissions revoked | Low | High | App emits metric on missing permission; sync logs skip; consent gate fail-closed |
| Manual transfer missed or skipped | Medium | Low | Stale-data window bounded; GHI returns None when stale |
| Path confusion (operator switches env var accidentally) | Low | Low | Dispatch log line at startup; metric `guinevere_wearable_source` exposes active source |
| Kotlin app breaks on new Android version | Low | Medium | 6-file surface; pinned SDK; 55 unit tests cover JSON DTOs |
| Stress metric absent from Health Connect | Low | Low | GHI recovery component handles None; weights redistribute |

## Implementation Notes

### Module Layout

| File | Purpose |
|---|---|
| `android/HealthConnectExport/app/src/main/java/com/guinevere/hcexport/MainActivity.kt` (399 LOC) | Reads 5 Health Connect record types, serializes to JSON, writes to `/sdcard/Download/health-connect-export/export.json` |
| `android/HealthConnectExport/app/build.gradle` | Gradle build, Health Connect SDK dependency, Kotlin coroutines |
| `android/HealthConnectExport/app/src/main/AndroidManifest.xml` | Health Connect permissions, activity declaration |
| `android/HealthConnectExport/app/src/main/java/com/guinevere/hcexport/RecordTypes.kt` | DTO classes for 5 record types |
| `android/HealthConnectExport/app/src/main/java/com/guinevere/hcexport/ExportSerializer.kt` | JSON serialization with explicit DTOs |
| `android/HealthConnectExport/app/src/main/java/com/guinevere/hcexport/PermissionHelper.kt` | Health Connect permission request flow |
| `src/wearable/health_connect_client.py` (435 LOC) | JSON parser, `parse_health_connect_json(path)` returns `HealthConnectParseResult` |
| `src/wearable/normalizer.py` (+100 LOC) | `normalize_health_connect_result()`; produces `MetricSource.HEALTH_CONNECT` tagged samples |
| `src/wearable/config.py` (+2 fields) | `health_connect_json_path`, `health_connect_device_name` |
| `src/wearable/models.py` (+1 enum) | `MetricSource.HEALTH_CONNECT` |
| `src/wearable/errors.py` (+4 exceptions) | `HealthConnectJsonMissing`, `HealthConnectJsonMalformed`, `HealthConnectUnknownRecordType`, `HealthConnectEmptyResult` |
| `src/wearable/sync.py` (+92 LOC, `_sync_health_connect()`) | New dispatch branch; same downstream contract as `mi_fitness` and `gadgetbridge` |
| `tests/test_health_connect_client.py` (55 unit tests) | JSON parsing, DTO mapping, edge cases (empty, malformed, missing fields) |
| `tests/test_health_connect_integration.py` (8-10 scenarios) | End-to-end: JSON file -> Redis buffer -> TimescaleDB writer -> GHI |

### Health Connect Record Mapping

| Health Connect Record | HealthMetricType | Extraction | Unit |
|---|---|---|---|
| `HeartRateRecord` (Series) | HEART_RATE | `samples[i].beatsPerMinute` | bpm |
| `StepsRecord` (Interval) | STEPS | `count` (summed per day) | steps |
| `OxygenSaturationRecord` (Instant) | SPO2 | `percentage.value` | percent |
| `SleepSessionRecord` (Interval) | SLEEP | `duration.inMinutes` | minutes |
| `ActiveCaloriesBurnedRecord` (Interval) | ACTIVITY | `energy.inKilocalories` (summed per day) | kcal |

Stress is not natively available in Health Connect and is marked
`MetricStatus.UNAVAILABLE`, identical to the Gadgetbridge path.

### JSON Export Schema (Kotlin app output)

The Kotlin app writes a single JSON file with this shape:

```json
{
  "export_timestamp": "2026-06-19T19:00:00+07:00",
  "device_manufacturer": "Xiaomi",
  "device_model": "M2233W1",
  "sdk_version": "1.1.0",
  "records": {
    "heart_rate": [
      {
        "start_time": "2026-06-19T08:00:00+07:00",
        "end_time": "2026-06-19T08:05:00+07:00",
        "samples": [
          {"time": "2026-06-19T08:00:00+07:00", "bpm": 72}
        ],
        "metadata": {"data_origin": "com.xiaomi.wearable", "recording_method": 2}
      }
    ],
    "steps": [...],
    "oxygen_saturation": [...],
    "sleep_sessions": [...],
    "active_calories": [...]
  }
}
```

The Python parser reads this file, validates the schema with Pydantic v2
strict types, and emits typed errors (`HealthConnectJsonMalformed`) on
shape mismatch.

### Consent Integration

The existing `health_consent.py` consent gate is reused. Seven
`wearable-health.*` scopes are enforced. Revocation pauses all three paths
(Mi Fitness Cloud, Gadgetbridge SQLite, Health Connect) simultaneously. The
gate is fail-closed and Redis-cached with a 300-second TTL.

### Discord Surface

The three Hermes commands registered under ADR-039 (`/health-report`,
`/health-trend`, `/health-baseline`) work unchanged. The active data
source is exposed in the report embed so the operator can confirm which
path is live.

### Systemd Timers

The existing `guinevere-wearable-sync.timer` (every 30 minutes) and
`guinevere-wearable-analysis.timer` (daily at 04:00 WIB) drive all three
paths. No service restart is required for a config switch.

### Persona Safety Gates

Inherited unchanged from ADR-037 and ADR-039:

1. Y-level modifier is capped at max(Y4 baseline, current Y - 1). Health
   signals can REDUCE Y-level (Guinevere is gentler when the operator is
   unwell) but NEVER increase it or produce confrontation.
2. No punishment/correction text is ever derived from health data.
3. All health-discord output is ephemeral (visible only to the operator).
4. Consent revocation immediately pauses all wearable sync. Health data
   access reverts to None returns.
5. The mood integration module does NOT import `yandere_fsm.py`. The mood
   signal is a modifier, never a yandere trigger.

### Budget Impact

- $0/month marginal cost. Health Connect is free, no vendor API calls, no
  additional LLM calls per sync cycle.
- Postgres/Redis disk overhead unchanged from ADR-037: estimated ~85 MB
  per year for a single user.
- Monitoring: same Prometheus metrics. `guinevere_wearable_source`
  exposes the active data source as a gauge (now with three possible
  values: `health_connect`, `gadgetbridge`, `mi_fitness`).

## Links

- [`../docs/00-core/02-TechnicalArchitecture_v2.0.md`](../docs/00-core/02-TechnicalArchitecture_v2.0.md)
- [`../docs/30-data/30-DataGovernance_Classification_v1.0.md`](../docs/30-data/30-DataGovernance_Classification_v1.0.md)
- [`../docs/30-data/31-SurveillanceDataPolicy_v1.0.md`](../docs/30-data/31-SurveillanceDataPolicy_v1.0.md)
- [`../docs/30-data/32-ConsentRevocationPolicy_v1.0.md`](../docs/30-data/32-ConsentRevocationPolicy_v1.0.md)
- [`../docs/60-persona/60-PersonaSafetyPolicy_v1.0.md`](../docs/60-persona/60-PersonaSafetyPolicy_v1.0.md)
- [`../docs/setup-evidence/p14-expansion/evidence-p14-expansion.md`](../docs/setup-evidence/p14-expansion/evidence-p14-expansion.md)
- [`ADR-021`](ADR-021-wearable-integration-post-mvp.md)
- [`ADR-037`](ADR-037-wearable-health-pipeline.md)
- [`ADR-039`](ADR-039-gadgetbridge-sqlite-parser.md)
- [`ADR-001`](ADR-001-persona-safety-ethical-boundary.md)
- [`ADR-002`](ADR-002-user-autonomy-safe-word-enforcement.md)
- [`ADR-032`](ADR-032-backup-storage-strategy.md)
- [`../research-reports/p14-health-connect-enterprise-plan.md`](../research-reports/p14-health-connect-enterprise-plan.md)
- [`../research-reports/p14-health-connect-api.md`](../research-reports/p14-health-connect-api.md)
- [`../research-reports/p14-health-connect-normalizer-mapping.md`](../research-reports/p14-health-connect-normalizer-mapping.md)