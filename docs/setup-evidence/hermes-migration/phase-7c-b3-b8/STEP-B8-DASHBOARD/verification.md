# STEP-B8-DASHBOARD Verification — Process-Correct Hermes Metrics Dashboard

| Field | Value |
|---|---|
| Status | PASS |
| Date | 2026-06-06 |
| Scope | Local Grafana/Prometheus dashboard verification only |
| Final Phase 7 status | BLOCKED |
| ADR-035 status | NOT IMPLEMENTED |

## What Changed

Updated `monitoring/grafana/dashboards/guinevere-hermes.json` to reflect the Phase 7c B8 safe-subset metrics that are actually emitted by the local safety-plugin instrumentation.

Changes applied:

1. Dashboard description now states that `up{job="hermes"}` reflects the Prometheus metrics target, not authoritative Hermes Agent gateway process liveness.
2. Panel 1 renamed from `Gateway Status` to `Metrics Target Status (not gateway process liveness)` and includes an explicit description blocking false `hermes_gateway_up` semantics.
3. Safety Blocks panel now uses live `hermes_safety_blocks_total` instrumentation without `or vector(0)` placeholder masking.
4. HARD STOP panel now derives from `hermes_safety_blocks_total{gate="G01"}` instead of nonexistent `hermes_hard_stop_events_total`.
5. Memory-recall proxy panel was replaced with `Safety Plugin Sessions` using `hermes_session_count`.
6. Model-call proxy panel was replaced with `Message Throughput by Direction` using `hermes_message_count_total{direction}`.

No VPS deployment, service restart, or live Prometheus/Grafana reload was performed in this safe subset.

## Files Changed

| File | Change |
|---|---|
| `monitoring/grafana/dashboards/guinevere-hermes.json` | Updated dashboard text and panels for process-correct B8 metrics |

## Validation Results

| Check | Result | Evidence |
|---|---:|---|
| Dashboard JSON parse | PASS | `python -c "import json; json.load(open(...)); print('dashboard json ok')"` |
| Alert YAML parse | PASS | `python -c "import yaml; yaml.safe_load(open(...)); print('alerts yaml ok')"` |
| Dashboard LSP diagnostics | PASS | 0 diagnostics |
| Alert rules LSP diagnostics | PASS | 0 diagnostics |
| No source definition of `hermes_gateway_up` | PASS | strict grep found no metric definition in `src/` |
| No dashboard query for nonexistent HARD STOP metric | PASS | dashboard uses `hermes_safety_blocks_total{gate="G01"}`; remaining text only states no separate metric is emitted |

## Metrics Represented

| Metric | Dashboard Use | Ownership |
|---|---|---|
| `hermes_safety_blocks_total{gate,reason}` | Safety Blocks Rate; HARD STOP Safety Blocks (`gate="G01"`) | `GuinevereSafetyPlugin` observer wiring |
| `hermes_session_count` | Safety Plugin Sessions | `GuinevereSafetyPlugin.on_session_start` gauge update |
| `hermes_message_count_total{direction}` | Message Throughput by Direction | `GuinevereSafetyPlugin` hook observer wiring |
| `up{job="hermes"}` | Metrics target scrape status only | Prometheus scrape target; not gateway process liveness |

## Boundary Compliance

- No `hermes_gateway_up` metric was added.
- No false Hermes Agent gateway process-liveness claim was added.
- No VPS deployment was performed.
- No service restart was performed.
- No Aizanta resource was touched.
- No deprecated files were archived or deleted.
- No ADR-035 IMPLEMENTED or Phase 7 complete claim was made.

## Remaining Caveats

- The dashboard is updated as local configuration only. It has not been deployed/reloaded on the VPS in this safe subset.
- `up{job="hermes"}` is still only scrape-target health. A true gateway liveness metric remains blocked until it is emitted by the actual Hermes Agent gateway process.
- Final Phase 7 remains blocked by B3 archive readiness and other Phase 7c gates.

## Footer

Generated as Phase 7c B3+B8 safe-subset evidence. This file is not final migration completion evidence.
