---
adr: 039
title: "Gadgetbridge SQLite Parser for Wearable Health Data"
status: "Accepted"
date: "2026-06-18"
deciders:
  - "Faiz (Owner, solo developer Indonesia)"
  - "Guinevere (Executor / autonomous system steward)"
tags:
  - wearable
  - health
  - gadgetbridge
  - sqlite
  - xiaomi
  - mood-modifier
  - consent
  - privacy
risk_level: "HIGH"
supersedes: "Partially supersedes ADR-037 by widening the implementation path to include Gadgetbridge SQLite export as a first-class data source alongside Mi Fitness Cloud API"
related_documents:
  - ADR-001
  - ADR-002
  - ADR-021
  - ADR-022
  - ADR-024
  - ADR-032
  - ADR-037
  - docs/00-core/02-TechnicalArchitecture_v2.0.md
  - docs/30-data/30-DataGovernance_Classification_v1.0.md
  - docs/30-data/31-SurveillanceDataPolicy_v1.0.md
  - docs/30-data/32-ConsentRevocationPolicy_v1.0.md
  - docs/60-persona/60-PersonaSafetyPolicy_v1.0.md
  - docs/setup-evidence/p14-expansion/evidence-p14-expansion.md
  - docs/setup-evidence/p14-expansion/evidence-p14-gadgetbridge-pivot.md
  - research-reports/p14-expansion/p14-gadgetbridge-enterprise-plan.md
  - research-reports/p14-expansion/p14-gadgetbridge-sqlite-schema.md
  - research-reports/p14-expansion/p14-vps-sync-mechanisms.md
---

# ADR-039: Gadgetbridge SQLite Parser for Wearable Health Data

> **Numbering note.** The previous wearable integration ADR is filed as
> ADR-037 (Mi Fitness Cloud API -> VPS). This ADR documents the second
> accepted implementation path: parsing the Gadgetbridge Android app's
> SQLite export on the VPS. ADR-037 remains Accepted for the Mi Fitness
> Cloud path. ADR-039 adds a config-driven dispatch (`WEARABLE_DATA_SOURCE`)
> so the operator can switch between the two ingestion paths without code
> changes or schema migrations. Both paths land in the same `health.*`
> schema and share the downstream pipeline (baseline, anomaly, GHI, mood
> modifier, alerts, Discord surface).

## Status

Accepted

## Date

2026-06-18

## Deciders

Faiz (Owner, solo developer Indonesia); Guinevere (Executor / autonomous system steward)

## Tags

wearable, health, gadgetbridge, sqlite, xiaomi, mood-modifier, consent, privacy

## Risk Level

HIGH

## Supersedes

Partially supersedes the implicit "Mi Fitness Cloud only" assumption baked
into ADR-037 by introducing a second accepted ingestion path. ADR-037 itself
remains Accepted for the cloud-API route. The shared downstream pipeline
(Redis DB4 buffer, TimescaleDB writer, baseline, anomaly, GHI, mood
modifier, alert router, Discord surface) is unchanged. Operators select
the path with `WEARABLE_DATA_SOURCE=gadgetbridge|mi_fitness` in
`.env.wearable`.

## Related Documents

| Document | Relationship |
|---|---|
| ADR-001 | Persona safety and ethical boundary |
| ADR-002 | User autonomy and safe word enforcement |
| ADR-021 | Wearable integration post-MVP (deferral) |
| ADR-022 | Communication channel strategy |
| ADR-024 | Data governance and classification policy |
| ADR-032 | Backup storage strategy (S3 + R2) |
| ADR-037 | Mi Fitness Cloud path (sibling ADR; both paths coexist) |
| Technical Architecture v2.0 | Runtime architecture, VPS topology |
| Data Governance & Classification Policy | CRITICAL classification of health data |
| Surveillance Data Policy | 365-day retention, care-only usage |
| Consent & Revocation Policy | Consent gating for wearable-health.* scopes |
| Persona Safety Policy | Y4 baseline / Y5 ceiling / Y6 prohibition |
| P14 expansion evidence | Per-step Mi Fitness implementation evidence |
| P14 Gadgetbridge pivot evidence | Per-step Gadgetbridge SQLite parser evidence |
| P14 Gadgetbridge enterprise plan | Research artifact for the pivot |
| P14 Gadgetbridge SQLite schema | Reverse-engineered schema reference |
| P14 VPS sync mechanisms | Manual transfer and automation research |

## Context

ADR-037 originally documented a single ingestion path for Phase 14: Mi
Fitness Cloud API -> VPS, server-to-server, authenticated with a SOPS-stored
`MI_FITNESS_TOKEN`. During deployment planning (2026-06-18) four constraints
made that path unsuitable for the operator's current device setup:

1. **Mi Fitness SDK v0.2.0 only queries relatives.** The open-source SDK
   reverse-engineered by the community (`mifit` on PyPI) requires a
   relative user ID (typically the user's own profile is treated as a
   "relative" of the binding account). Direct self-data queries return
   permission errors.
2. **QR-code token file auth requires manual workstation setup.** The
   official Mi Fitness Cloud auth flow is a one-time QR scan paired with
   the Xiaomi Wear mobile app. Tokens must be exported from a paired phone
   onto a workstation that runs the SDK. The flow is fragile, has no
   documented refresh path, and depends on the operator's mobile device
   being reachable from the same workstation as the VPS-decoding host.
3. **No cloud API supports direct self-data queries.** Xiaomi's vendor
   platform (`api-mifit.huami.com`) returns 403 for self-scoped reads;
   only "family" or "relative" scopes are reachable through the public
   SDKs. The console-style dashboard used on mobile bypasses this
   restriction, but there is no equivalent programmatic endpoint.
4. **Operator hardware is a Xiaomi Watch 2 Pro (Model M2233W1) paired
   with a Gadgetbridge-compatible Android phone.** Gadgetbridge supports
   60+ wearable devices and stores a deterministic SQLite export on the
   phone. This data is available offline, requires no vendor token, and
   has no rate limit.

Canonical v2.0 decisions inherited by this ADR (unchanged from ADR-037):

- Health data is CRITICAL classification (per ADR-024 / Data Governance
  Policy).
- Consent is required for any `wearable-health.*` scope (per
  ConsentRevocationPolicy).
- Y4 baseline, Y5 ceiling, Y6 absolute prohibition (per Persona Safety
  Policy).
- Memory uses PostgreSQL + Redis; no SQLite (memory layer); TimescaleDB
  extension for time-series. The Gadgetbridge SQLite export is a
  transient ingestion artefact, not part of the memory layer.
- Persona NEVER uses health data for confrontation, correction, or
  punishment.
- VPS primary hosts PostgreSQL, Redis, Prometheus, Grafana.
- HMAC keys, Mi Fitness credentials, and SOPS/age encryption gate the
  wearable-health secret boundary.

## Decision Drivers

- Health data is among the most privacy-sensitive data the system
  handles; the decision must minimise persistent secrets, vendor lock-in,
  and external attack surface.
- The owner is the sole user; convenience and reliability outrank
  multi-tenant scale considerations.
- Persona safety depends on health data being a *modifier* (soft signal),
  not a *trigger* (hard rule). The architecture must make this
  technically enforceable on both ingestion paths.
- The implementation must be auditable through file-based evidence and
  reversible through a one-step config switch (`WEARABLE_DATA_SOURCE`)
  with no schema migration required.
- Canonical v2.0 documentation must remain internally consistent; this
  ADR documents an additional accepted path for the same data domain,
  not a replacement of ADR-037.

## Considered Options

1. **Gadgetbridge SQLite export -> VPS (parser + manual transfer)** --
   Chosen.
2. **Mi Fitness Cloud API -> VPS (direct, server-to-server)** -- Chosen
   (ADR-037, kept as sibling option, selected when token + relative
   account are available).
3. **Phone companion app (custom) -> VPS over Tailscale mesh.**
4. **Defer wearable health data to a later phase (status quo of ADR-021
   for any path that fails).**

## Decision Outcome

Chosen option: **Gadgetbridge SQLite parser on VPS, config-driven
dispatch between Gadgetbridge and Mi Fitness Cloud**.

The VPS is the sole integration point for both paths. The Gadgetbridge
pipeline:

- Uses the Gadgetbridge Android app (free, open-source) as the data
  source. The app exports a SQLite database named `Gadgetbridge` (no
  extension) onto the Android phone's local storage.
- Transports the SQLite file from the phone to the VPS via manual file
  transfer (Android -> VPS through SCP, WebDAV, or SFTP). Optional
  automation via Tasker is documented but out of scope for this ADR.
- Parses the export with a sync Python module at
  `src/wearable/gadgetbridge_client.py` (725 LOC). The parser queries
  `sqlite_master` to discover available tables (handling schema
  variations across Gadgetbridge versions), auto-detects timestamp
  scales (samples above 10^12 are treated as milliseconds, otherwise
  seconds), and decodes sleep stages from the activity table's
  `RAW_KIND` codes (112 light start, 120 light, 121 deep, 122 REM, 249
  awake).
- Buffers normalised samples in Redis DB4 with a 5-minute TTL,
  identical to the Mi Fitness Cloud path.
- Writes into the same `health.*` TimescaleDB hypertables (no
  migration required).
- Runs the existing 28-day baseline, +/-20% anomaly, GHI 40/20/20/20
  scoring, mood modifier, and consent-gated alert pipeline without
  changes.
- Tags every Gadgetbridge-originated sample with
  `MetricSource.GADGETBRIDGE` (an existing enum value) so downstream
  queries can distinguish source.
- Exposes the same three Discord commands through Hermes:
  `/health-report`, `/health-trend`, `/health-baseline`.
- Switches between paths by setting `WEARABLE_DATA_SOURCE=gadgetbridge`
  or `WEARABLE_DATA_SOURCE=mi_fitness` in `.env.wearable`. The dispatch
  happens inside `src/wearable/sync.py`; no code changes are required
  for a path switch.

The existing systemd timers (`guinevere-wearable-sync.timer` every 30
minutes, `guinevere-wearable-analysis.timer` daily at 04:00 WIB) drive
both paths. The Mi Fitness client (`mi_fitness_client.py`) is retained
for fallback and can be re-enabled with a single env var.

## Consequences

### Positive

- Removes the relative-account and QR-code auth constraints from the
  primary wearable path.
- Eliminates dependency on the unofficial Mi Fitness SDK v0.2.0, which
  has no published support contract.
- Gives the operator full offline control of the wearable data export
  (no rate limit, no captcha, no vendor lock-in).
- Gadgetbridge supports 60+ wearable devices, not just Xiaomi. The
  operator can switch watches without rewriting the pipeline.
- SQLite export is deterministic and testable, with schema discovery
  via `sqlite_master` reducing version-drift risk.
- 85% of the existing P14 code (consent, Redis buffer, writer, baseline,
  anomaly, GHI, mood, alerts) is reused without modification.
- A future path migration is a single env var change with zero
  downtime.

### Negative

- Manual file transfer required between Android and VPS. The operator
  must run an export in the Gadgetbridge app and move the file. Optional
  Tasker automation reduces friction but is out of scope here.
- No real-time sync. Gadgetbridge exports on demand; the systemd timer
  picks up whichever file is on disk. Stale data windows are bounded by
  the operator's export cadence.
- Gadgetbridge schema is not officially documented. The parser relies
  on reverse-engineered patterns and table-name introspection. Schema
  drift between Gadgetbridge versions may require parser updates.
- HRV and body battery are not available in Gadgetbridge's exported
  tables (no confirmed tables); the GHI's 20% recovery component
  degrades to a partial signal on this path.
- The Mi Fitness Cloud code path remains in the repository even when
  unused, adding maintenance surface area.

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Gadgetbridge schema drift | Medium (frequent releases) | Medium (parser needs update) | Table introspection via `sqlite_master`; sample-level assertions in tests; version-pinned parser tests |
| Manual transfer missed | Low (operator discipline) | Low (stale data) | Stale-data Prometheus metric; system continues with prior buffer |
| Path confusion (operator switches env var accidentally) | Low | Low | Dispatch log line at startup; metric `guinevere_wearable_source` exposes active source |
| SQLite parser bug across devices | Low | Medium | 71 unit tests + 8 integration scenarios covering 6 metric tables; safe defaults on parse error |
| HRV/body-battery unavailable | Low | Low | GHI recovery component handles None; weights redistribute |
| Consent revocation race | Low | High | Consent gate checked per-sync-cycle, not per-request; same gate as Mi Fitness path |

## Implementation Notes

### Module Layout

| File | Purpose |
|---|---|
| `src/wearable/gadgetbridge_client.py` (725 LOC) | SQLite parser: 6 metric tables, timestamp auto-detect, sleep decoding, source tagging |
| `src/wearable/normalizer.py` (+55 LOC) | Gadgetbridge extractors; produces `MetricSource.GADGETBRIDGE` tagged samples |
| `src/wearable/config.py` (+3 fields) | `WEARABLE_DATA_SOURCE`, `GADGETBRIDGE_DB_PATH`, `GADGETBRIDGE_TRANSFER_DIR` |
| `src/wearable/errors.py` (+4 exceptions) | `GadgetbridgeDbMissing`, `GadgetbridgeSchemaError`, `GadgetbridgeEmptyResult`, `GadgetbridgeParseError` |
| `src/wearable/sync.py` (rewrite, 154 LOC) | Config-driven dispatch (`mi_fitness` vs `gadgetbridge`); same downstream contract |
| `src/discord/_command_registry.py` (+3 commands) | Registers `/health-report`, `/health-trend`, `/health-baseline` |
| `src/discord/_entrypoint.py` (+3 registrations) | Wires the three commands into the Hermes dispatch table |

### Table Discovery

The parser begins by querying `sqlite_master` for any table matching
the known names (`ACTIVITY`, `HEART_RATE`, `STEPS`, `SLEEP`, `SPO2`,
`BATTERY`). Missing tables are skipped without raising; an empty result
emits a Prometheus metric (`guinevere_wearable_gadgetbridge_table_present`)
so the operator can verify coverage.

### Timestamp Auto-Detection

Gadgetbridge uses heterogeneous timestamp formats across tables and
versions. The parser treats samples above 10^12 as milliseconds and
otherwise as seconds (Unix epoch). Mixed scales inside a single table
are normalised to milliseconds internally before buffer write.

### Sleep Decoding

Sleep stages are not stored in a dedicated sleep table on every
Gadgetbridge version. The parser reads the `RAW_KIND` column on the
activity table and maps known codes:

| `RAW_KIND` | Stage |
|---|---|
| 112 | light sleep (start) |
| 120 | light sleep |
| 121 | deep sleep |
| 122 | REM |
| 249 | awake |

Unknown codes default to "unspecified" and emit a metric counter so
the operator can detect new schema additions.

### Source Tagging

Every Gadgetbridge-originated sample carries
`MetricSource.GADGETBRIDGE`. Downstream modules (writer, baseline,
anomaly, GHI, mood, alert) are source-agnostic and treat the tag as
metadata only.

### Consent Integration

The existing `health_consent.py` consent gate is reused. Seven
`wearable-health.*` scopes are enforced; revocation pauses both paths
simultaneously. The gate is fail-closed and Redis-cached (300s TTL).

### Discord Surface

Three Hermes commands are wired through `src/discord/_command_registry.py`
and `src/discord/_entrypoint.py`:

- `/health-report` — current GHI, top anomalies, mood modifier delta
- `/health-trend` — last 7 days of GHI + sleep + cardio summary
- `/health-baseline` — 28-day rolling baseline values

All output is ephemeral (visible only to the operator).

### Systemd Timers

The existing `guinevere-wearable-sync.timer` (every 30 minutes) and
`guinevere-wearable-analysis.timer` (daily at 04:00 WIB) drive both
paths. No service restart is required for a config switch.

### Persona Safety Gates

Inherited unchanged from ADR-037:

1. Y-level modifier is capped at max(Y4 baseline, current Y - 1);
   health signals can REDUCE Y-level (Guinevere is gentler when the
   operator is unwell) but NEVER increases it or produces confrontation.
2. No punishment/correction text is ever derived from health data.
3. All health-discord output is ephemeral (visible only to the
   operator).
4. Consent revocation immediately pauses all wearable sync; health
   data access reverts to None returns.
5. The mood integration module does NOT import `yandere_fsm.py`; the
   mood signal is a *modifier*, never a yandere *trigger*.

### Budget Impact

- $0/month marginal cost (Gadgetbridge is free, no vendor API calls,
  no additional LLM calls per sync cycle).
- Postgres/Redis disk overhead unchanged from ADR-037: estimated ~85
  MB/year for a single user.
- Monitoring: same Prometheus metrics; `guinevere_wearable_source`
  exposes the active data source (gadgetbridge vs mi_fitness) as a
  gauge.

## Links

- [`../docs/00-core/02-TechnicalArchitecture_v2.0.md`](../docs/00-core/02-TechnicalArchitecture_v2.0.md)
- [`../docs/30-data/30-DataGovernance_Classification_v1.0.md`](../docs/30-data/30-DataGovernance_Classification_v1.0.md)
- [`../docs/30-data/31-SurveillanceDataPolicy_v1.0.md`](../docs/30-data/31-SurveillanceDataPolicy_v1.0.md)
- [`../docs/30-data/32-ConsentRevocationPolicy_v1.0.md`](../docs/30-data/32-ConsentRevocationPolicy_v1.0.md)
- [`../docs/60-persona/60-PersonaSafetyPolicy_v1.0.md`](../docs/60-persona/60-PersonaSafetyPolicy_v1.0.md)
- [`../docs/setup-evidence/p14-expansion/evidence-p14-expansion.md`](../docs/setup-evidence/p14-expansion/evidence-p14-expansion.md)
- [`../docs/setup-evidence/p14-expansion/evidence-p14-gadgetbridge-pivot.md`](../docs/setup-evidence/p14-expansion/evidence-p14-gadgetbridge-pivot.md)
- [`ADR-021`](ADR-021-wearable-integration-post-mvp.md)
- [`ADR-037`](ADR-037-wearable-health-pipeline.md)
- [`ADR-001`](ADR-001-persona-safety-ethical-boundary.md)
- [`ADR-002`](ADR-002-user-autonomy-safe-word-enforcement.md)
- [`ADR-032`](ADR-032-backup-storage-strategy.md)