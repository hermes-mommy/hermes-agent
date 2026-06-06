# Step 7b.5 — Hermes Monitoring Config Files — Verification

## 1. What Was Done

Implemented local Hermes gateway monitoring configuration files under `monitoring/` per ADR-035 Phase 7b §6.5:

- **Prometheus scrape job**: Replaced `job_name: "hermes-llm-routing"` with canonical `job_name: "hermes"`, target `host.docker.internal:9191`, and relabel `instance` → `hermes-gateway`.
- **Alert rules**: Added `guinevere-hermes` alert group with six `GuinevereHermes*` rules covering gateway down, latency high, safety blocks spike, budget near cap, memory recall latency (pending instrumentation), and model calls anomaly (pending instrumentation). Every rule includes a `runbook` annotation.
- **Grafana dashboard**: Created `guinevere-hermes.json` with panels for gateway status, LLM calls rate, latency p50/p95/p99, cumulative cost, fallback activations, and three pending-instrumentation panels (safety blocks, HARD STOP events, memory recall latency, model call rate).
- **Alertmanager routes**: Added defense-in-depth Hermes alert routing via `alertname` and `alertname` regex matches for Hermes critical/warning/info alerts, preserving all existing routes.
- **Promtail**: Updated journal `__systemd_unit` regex from `guinevere-(.+)\\.service` to `(?:guinevere|hermes)-(.+)\\.service` to match `hermes-gateway.service`.

## 2. Files Changed

| File | Change |
|---|---|
| `monitoring/prometheus/prometheus.yml` | Replaced `hermes-llm-routing` job with canonical `hermes` job + `host.docker.internal:9191` + instance relabel |
| `monitoring/prometheus/rules/guinevere-alerts.yml` | Added `guinevere-hermes` group with 6 rules, each with runbook annotation |
| `monitoring/grafana/dashboards/guinevere-hermes.json` | Created new Hermes dashboard (9 panels, valid JSON) |
| `monitoring/alertmanager/alertmanager.yml` | Added 3 Hermes-specific routes (critical/warning/info via alertname match) |
| `monitoring/promtail/promtail-config.yml` | Updated journal unit regex to match `hermes-*` services |
| `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-5/verification.md` | This file |
| `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-5/auditor-gate.md` | Auditor gate evidence |

## 3. Validation Results

| Check | Result |
|---|---|
| Dashboard JSON parse | PASS (see §3.1) |
| `job_name: "hermes"` in prometheus.yml | PASS (see §3.2) |
| `host.docker.internal:9191` in prometheus.yml | PASS (see §3.3) |
| `GuinevereHermes` alert rules present | PASS (see §3.4) |
| `hermes-gateway.service` in promtail config | PASS (see §3.5) |
| `GuinevereHermesGatewayDown` in alertmanager.yml | PASS (see §3.6) |
| All Hermes alert rules have runbook annotation | PASS (manual review) |
| No `job_name: "hermes-llm-routing"` remains | PASS (grep confirms zero matches) |

### 3.1 Dashboard JSON Parse

```
python -c "import json; json.load(open('monitoring/grafana/dashboards/guinevere-hermes.json', encoding='utf-8'))"
→ Exit code 0 (PASS)
```

### 3.2 Canonical Hermes Job Name

```
grep "job_name: \"hermes\"" monitoring/prometheus/prometheus.yml
→ Exit code 0 (PASS)
```

### 3.3 Target host.docker.internal:9191

```
grep "host.docker.internal:9191" monitoring/prometheus/prometheus.yml
→ Exit code 0 (PASS)
```

### 3.4 GuinevereHermes Alert Rules

```
grep "GuinevereHermes" monitoring/prometheus/rules/guinevere-alerts.yml
→ Exit code 0 (PASS) — 6 rules matched
```

### 3.5 Promtail hermes-gateway Service Matching

```
grep "hermes-gateway" monitoring/promtail/promtail-config.yml
→ Exit code 0 (PASS) — note: regex is `(?:guinevere|hermes)-(.+)\\.service`
```

### 3.6 Alertmanager Hermes Route

```
grep "GuinevereHermesGatewayDown" monitoring/alertmanager/alertmanager.yml
→ Exit code 0 (PASS)
```

### 3.7 No Deprecated Job Name

```
grep "hermes-llm-routing" monitoring/prometheus/prometheus.yml
→ Exit code 1 (PASS — no remaining references)
```

## 4. Evidence Artifacts

- `monitoring/prometheus/prometheus.yml` — updated Hermes scrape job
- `monitoring/prometheus/rules/guinevere-alerts.yml` — Hermes alert rules section
- `monitoring/grafana/dashboards/guinevere-hermes.json` — Hermes Grafana dashboard
- `monitoring/alertmanager/alertmanager.yml` — Hermes alert routes
- `monitoring/promtail/promtail-config.yml` — updated journal regex
- This verification file
- `auditor-gate.md` — pending auditor gate evidence

## 5. Doc-Sync Impact

- ADR-035 Hermes Migration: monitoring configs updated locally; final deployment deferred to Phase 7c.
- `docs/40-operations/40-ObservabilityAlertingSpec_v1.0.md`: Hermes scrape job and alert rules now match the design intent. Dashboard coverage added.
- New runbooks referenced by alert runbook annotations:
  - `docs/40-operations/runbooks/hermes-gateway-down.md` (referenced by `GuinevereHermesGatewayDown`)
  - `docs/40-operations/runbooks/hermes-safety-spike.md` (referenced by `GuinevereHermesSafetyBlocksSpike`)
  - `docs/40-operations/runbooks/hermes-cost-anomaly.md` (referenced by `GuinevereHermesBudgetNearCap`)
  - Note: runbook files are created in Step 7b.8; until then, annotations reference their planned paths.

## 6. Boundary Compliance

- No persona, yandere, or consent surfaces touched.
- No surveillance data exposed.
- No secret values in configs (all webhook URLs are internal `localhost:8000` references).
- HARD STOP, SEV0/SEV1 alert paths remain unchanged.
- No hidden controls or backdoor monitoring added.

## 7. Rollback/Re-run Safety

- **Rollback**: `git checkout -- monitoring/prometheus/prometheus.yml monitoring/prometheus/rules/guinevere-alerts.yml monitoring/alertmanager/alertmanager.yml monitoring/promtail/promtail-config.yml monitoring/grafana/dashboards/guinevere-hermes.json docs/setup-evidence/hermes-migration/phase-7/STEP-7B-5/`
- **Re-run safe**: All edits are idempotent; Prometheus/Grafana/Alertmanager/Promtail are not running locally.
- **Non-destructive**: No Docker containers, services, or VPS state mutated.

## 8. Design Decisions/Caveats

- `hermes_safety_blocks_total` and `hermes_hard_stop_events_total` metrics are **pending Hermes-native instrumentation** (Phase 7c). Alert rules and dashboard panels that reference them use `or vector(0)` to avoid false-positive firing when metrics are absent.
- The Prometheus target uses `host.docker.internal:9191` because Hermes runs on the host (not in Docker), consistent with the existing `fastapi` job pattern.
- Alertmanager routes use `alertname` match rather than only `sev_level` for defense-in-depth; Hermes alerts also match the existing `sev_level`-based routes via `continue: false`.
- The Promtail regex change from `guinevere-(.+)\\.service` to `(?:guinevere|hermes)-(.+)\\.service` preserves backward compatibility for all existing `guinevere-*` services.
- Live monitoring deployment, Prometheus reload, and Grafana import verification are deferred to Phase 7c per Oracle verdict.

## 9. Auditor Gate

Pending — see `auditor-gate.md` in this directory.

## 10. Security Scan

- No secrets, tokens, keys, or passwords introduced.
- No `localhost:9191` target (correctly uses `host.docker.internal:9191`).
- No overly permissive alerting rules.
- No new HTTP endpoints or exposed ports.
- All Hermes alert rules include runbook annotations pointing to `docs/40-operations/runbooks/`.

## 11. Acceptance Criteria Mapping

| Criteria | Status |
|---|---|
| Canonical `job_name: "hermes"` replaces `hermes-llm-routing` | PASS |
| Target `host.docker.internal:9191` with instance `hermes-gateway` | PASS |
| Phase 6 `hermes_llm_*` metric semantics preserved | PASS |
| 6 GuinevereHermes alert rules with runbook annotations | PASS |
| Valid Grafana dashboard JSON with 9 panels | PASS |
| Alertmanager Hermes routes without breaking existing routes | PASS |
| Promtail regex matches `hermes-gateway.service` | PASS |
| Evidence files created | PASS |

## 12. Footer

**Step**: 7b.5 (Hermes Monitoring Config Files)
**Phase**: Phase 7b — Local Hardening (Phase 7c deferred)
**Date**: 2026-06-06
**Verification**: File-based scaffold commands only; no live deployment claim.
**Next Step**: Step 7b.6 (Systemd Hermes Gateway Template)
