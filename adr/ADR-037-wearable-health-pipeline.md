---
adr: 037
title: "Wearable Health Data Integration Pipeline"
status: "Accepted"
date: "2026-06-18"
deciders:
  - "Faiz (Owner, solo developer Indonesia)"
  - "Guinevere (Executor / autonomous system steward)"
tags:
  - wearable
  - health
  - mi-fitness
  - timescaledb
  - mood-modifier
  - consent
  - privacy
risk_level: "HIGH"
supersedes: "Partially supersedes the post-MVP deferral scope of ADR-021"
related_documents:
  - ADR-001
  - ADR-002
  - ADR-021
  - ADR-022
  - ADR-024
  - ADR-032
  - docs/00-core/02-TechnicalArchitecture_v2.0.md
  - docs/30-data/30-DataGovernance_Classification_v1.0.md
  - docs/30-data/31-SurveillanceDataPolicy_v1.0.md
  - docs/30-data/32-ConsentRevocationPolicy_v1.0.md
  - docs/60-persona/60-PersonaSafetyPolicy_v1.0.md
  - docs/setup-evidence/p14-expansion/evidence-p14-expansion.md
  - research-reports/p14-expansion/p14-enterprise-plan.md
---

# ADR-037: Wearable Health Data Integration Pipeline

> **Numbering note:** The task description referenced this ADR as "ADR-022", but
> `adr/ADR-022-communication-channel-strategy.md` already exists (Accepted with
> notes 2026-06-03). Per the ADR Maintenance Rules — "Add new ADRs with
> monotonically increasing numbers. Do not reuse ADR numbers." — and because
> ADR-021 fully documents the prior decision classifying wearable integration as
> post-MVP, this follow-up implementation ADR is filed as **ADR-037** (next free
> in the current sequence after ADR-036). This ADR documents the *implemented*
> wearable health data pipeline via Mi Fitness Cloud API → VPS, partially
> superseding the post-MVP deferral of ADR-021 for this specific integration
> path.

## Status

Accepted

## Date

2026-06-18

## Deciders

Faiz (Owner, solo developer Indonesia); Guinevere (Executor / autonomous system steward)

## Tags

wearable, health, mi-fitness, timescaledb, mood-modifier, consent, privacy

## Risk Level

HIGH

## Supersedes

Partially supersedes the post-MVP deferral scope of ADR-021 for the Mi Fitness
Cloud → VPS integration path only. ADR-021's graceful-degradation invariant
remains in force for any future non-Xiaomi wearable path and for the "no device
connected" scenario (sync service exits 0 with logged skip when token is absent).

## Related Documents

| Document | Relationship |
|---|---|
| ADR-001 | Persona safety and ethical boundary |
| ADR-002 | User autonomy and safe word enforcement |
| ADR-021 | Wearable integration post-MVP (deferral) |
| ADR-022 | Communication channel strategy |
| ADR-024 | Data governance and classification policy |
| ADR-032 | Backup storage strategy (S3 + R2) |
| Technical Architecture v2.0 | Runtime architecture, VPS topology |
| Data Governance & Classification Policy | CRITICAL classification of health data |
| Surveillance Data Policy | 365-day retention, care-only usage |
| Consent & Revocation Policy | Consent gating for wearable-health.* scopes |
| Persona Safety Policy | Y4 baseline / Y5 ceiling / Y6 prohibition |
| P14 evidence (20 steps) | Per-step implementation evidence |

## Context

Earlier drafts and the original P14-001..P14-027 Gadgetbridge-era plan proposed
a phone-mediated WebDAV path: the Android phone would sync Xiaomi watch data
through Gadgetbridge and forward SQLite files to the VPS over WebDAV. P14
enterprise re-planning (2026-06-12 through 2026-06-18) abandoned that path for
three reasons:

1. **Operational fragility.** WebDAV depends on a phone staying on, paired, and
   network-reachable. Silent failures create stale data and false anomalies.
2. **Consent surface area.** A phone-resident relay splits the consent boundary
   across two devices and one human, weakening revocation guarantees.
3. **Schema mismatch.** Gadgetbridge SQLite tables are an implementation detail,
   not a stable vendor contract. Long-term support requires normalising against
   the Mi Fitness Cloud data model.

Canonical v2.0 decisions inherited by this ADR:

- Health data is CRITICAL classification (per ADR-024 / Data Governance Policy).
- Consent is required for any wearable-health.* scope (per ConsentRevocationPolicy).
- Y4 baseline, Y5 ceiling, Y6 absolute prohibition (per Persona Safety Policy).
- Memory uses PostgreSQL + Redis; no SQLite; TimescaleDB extension for time-series.
- Persona NEVER uses health data for confrontation, correction, or punishment.
- VPS primary hosts PostgreSQL, Redis, Prometheus, Grafana.
- HMAC keys, Mi Fitness credentials, and SOPS/age encryption gate the
  wearable-health secret boundary.

## Decision Drivers

- Health data is among the most privacy-sensitive data the system handles; the
  decision must minimise data duplication, persistent secrets, and external
  attack surface.
- The owner is the sole user; convenience and reliability outrank multi-tenant
  scale considerations.
- Persona safety depends on health data being a *modifier* (soft signal), not a
  *trigger* (hard rule). The architecture must make this technically enforceable.
- The implementation must be auditable through file-based evidence and reversible
  through a one-step rollback (disable systemd units + drop health.* schema).
- Canonical v2.0 documentation must remain internally consistent; this ADR
  supersedes the deferral aspect of ADR-021 only for the Mi Fitness path.

## Considered Options

1. **Gadgetbridge (Android) + WebDAV -> VPS** (original P14 plan).
2. **Mi Fitness Cloud API -> VPS (direct, server-to-server)** -- Chosen.
3. **Phone companion app (custom) -> VPS over Tailscale mesh.**
4. **Defer wearable health data to a later phase (status quo of ADR-021).**

## Decision Outcome

Chosen option: **Mi Fitness Cloud API -> VPS (direct, server-to-server)**.

The VPS is the sole integration point. The wearable pipeline:

- Authenticates to the Mi Fitness Cloud API using a SOPS-stored MI_FITNESS_TOKEN.
- Pulls sleep, heart-rate, steps, and SpO2 telemetry on a 15-minute systemd
  timer (guinevere-wearable-sync.timer) plus an hourly analysis timer
  (guinevere-wearable-analysis.timer).
- Buffers raw responses in Redis DB4 with a 5-minute TTL.
- Normalises the Mi Fitness Cloud response shape into the Guinevere internal
  model (src/wearable/normalizer.py).
- Writes into the TimescaleDB health.* schema (5 hypertables + 2 reference
  tables).
- Computes a 28-day personal baseline (src/wearable/baseline.py).
- Detects +/-20% deviations from baseline (src/wearable/anomaly.py).
- Computes the Guinevere Health Index (GHI) weighted as Sleep 40% / Cardio 20%
  / Activity 20% / Recovery 20% (src/wearable/ghi.py).
- Exposes a GHI-derived mood *modifier* (never a hard rule) to the persona
  state machine via src/wearable/mood_integration.py. The modifier never
  escalates Y-level above Y4 (baseline) or Y5 (ceiling) and never produces
  confrontation, correction, or punishment.
- Routes alerts through a consent-gated, persona-tone-aware router
  (src/wearable/alert_router.py).
- Surfaces a single Discord command (src/discord/cmd_health_report.py).
- Discards raw payloads after parse; only normalised data lands in TimescaleDB.

The phone, Gadgetbridge, and WebDAV are explicitly **out of scope** for this
implementation. ADR-021's graceful-degradation invariant is preserved: if the
Mi Fitness token is missing, the sync service exits 0 with a logged skip, and
all downstream GHI/mood functions return None.

## Consequences

### Positive

- Removes a phone-resident relay and a WebDAV endpoint from the trust boundary.
- Server-to-server Mi Fitness auth is a single SOPS-encrypted secret.
- Health data lives only in one place (TimescaleDB) under one retention policy.
- 15-minute sync interval stays well within Mi Fitness rate limits.
- Mood integration is structurally a modifier (GHI -> persona), not a trigger,
  making the Y4/Y5/Y6 boundary technically enforceable.
- All health data is CRITICAL-classified; encryption at rest is covered by the
  existing PostgreSQL posture plus application-level consent/encryption gates.
- Clear rollback: stop both systemd timers, drop the health.* schema via
  down-migration, remove .env.wearable -- system reverts to pre-P14 state.

### Negative

- Couples the wearable pipeline to the Mi Fitness Cloud API contract; future
  Xiaomi deprecations require a schema re-version.
- 5 hypertables + 2 reference tables add ~1.4M rows/year for a single user.
- 17 source files in src/wearable/ add ~2900 LOC to the codebase (excluding
  tests at ~1400 LOC).
- Systemd timers consume negligible CPU (<0.1% idle), but the hourly analysis
  timer adds ~5 seconds of TimescaleDB compute per run.

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Mi Fitness API deprecation | Low (Xiaomi long tail) | High (pipeline halts) | Modular client interface; swap-in for alternative vendor |
| Token rotation failure | Low (SOPS-managed) | Medium (stale data) | Graceful exit on 401; logged skip |
| Health data persona drift | Low (structural modifier) | Critical (safety) | Mood modifier capped; no confrontation/correction/punishment |
| Consent revocation race | Low | High | Consent gate checked per-sync-cycle, not per-request |

## Implementation Notes

### Schema Design (health.*)

| Hypertable | Metrics | Retention |
|---|---|---|
| health.sleep_sessions | sleep_quality, duration_min, deep_sleep_min, rem_min, latency_min | 365 days |
| health.heart_rate_readings | bpm, resting_bpm | 365 days |
| health.step_records | steps, distance_km, calories_burned | 365 days |
| health.spo2_readings | spo2_percent | 365 days |
| health.daily_summaries | ghi_score, anomaly_count, mood_modifier_value | 365 days |

| Reference Table | Purpose |
|---|---|
| health.baseline | Per-metric 28-day rolling PB/PS scores |
| health.user_consent | Consent status for wearable-health.* scopes |

### Device Support

Supported: Xiaomi Smart Band 9 Pro via Mi Fitness Cloud API (official).
Unsupported (legacy plan): Gadgetbridge WebDAV path (abandoned).
Graceful degradation: No token = no sync, no GHI, mood modifier returns None.

### Persona Safety Gates

1. Y-level modifier is capped at max(Y4 baseline, current - 1) -- this means
   sleep-deprivation/stress can REDUCE Y-level (Guinevere is gentler when
   Faiz is unwell) but NEVER increases it or produces confrontation.
2. No punishment/confrontation text is ever derived from health data.
3. All health-discord output is ephemeral (visible only to Faiz).
4. Consent revocation immediately pauses all wearable sync; health data access
   reverts to None returns.

### Budget Impact

- $0/month marginal cost (Mi Fitness Cloud API is free, no additional LLM calls
  per sync cycle).
- Postgres/Redis disk overhead: estimated ~85 MB/year for a single user.
- Monitoring: Prometheus metrics exposed at guinevere_wearable_*.

## Links

- [`../docs/00-core/02-TechnicalArchitecture_v2.0.md`](../docs/00-core/02-TechnicalArchitecture_v2.0.md)
- [`../docs/30-data/30-DataGovernance_Classification_v1.0.md`](../docs/30-data/30-DataGovernance_Classification_v1.0.md)
- [`../docs/30-data/31-SurveillanceDataPolicy_v1.0.md`](../docs/30-data/31-SurveillanceDataPolicy_v1.0.md)
- [`../docs/30-data/32-ConsentRevocationPolicy_v1.0.md`](../docs/30-data/32-ConsentRevocationPolicy_v1.0.md)
- [`../docs/60-persona/60-PersonaSafetyPolicy_v1.0.md`](../docs/60-persona/60-PersonaSafetyPolicy_v1.0.md)
- [`../docs/setup-evidence/p14-expansion/evidence-p14-expansion.md`](../docs/setup-evidence/p14-expansion/evidence-p14-expansion.md)
- [`ADR-021`](ADR-021-wearable-integration-post-mvp.md)
- [`ADR-001`](ADR-001-persona-safety-ethical-boundary.md)
- [`ADR-002`](ADR-002-user-autonomy-safe-word-enforcement.md)
- [`ADR-032`](ADR-032-backup-storage-strategy.md)