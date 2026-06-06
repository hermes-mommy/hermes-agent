# Grafana & Visualization Gaps — Hermes Runtime Metrics

**Date**: 2026-06-06  
**Scope**: B8 metrics + dashboard gap analysis for Phase 7c  
**Status**: COMPLETE — gaps identified, actionable findings below  
**Files examined**:
- `monitoring/prometheus/prometheus.yml` (scrape configs)
- `monitoring/prometheus/rules/guinevere-alerts.yml` (alert rules)
- `monitoring/prometheus/rules/guinevere-backup-alerts.yml`
- `monitoring/grafana/dashboards/guinevere-hermes.json` (dashboard panels)
- `monitoring/alertmanager/alertmanager.yml` (routing rules)
- `monitoring/promtail/promtail-config.yml` (log shipping)
- `monitoring/loki/loki-config.yml` (log aggregation)
- `monitoring/compose.monitoring.yml` (Docker stack)
- `src/core/services/llm_metrics.py` (metric definitions — the **only** Hermes metrics source)
- `src/core/services/llm_router.py` (metric emission points)
- `src/core/main.py` (metrics server startup)
- `src/hermes/session_adapter.py` (Hermes session manager — **no metrics instrumentation**)
- `src/hermes/safety_plugin.py` (Hermes safety hooks — **no prometheus_client usage**)
- `src/hermes/memory_bridge.py` (Hermes memory — **no prometheus_client usage**)
- `src/hermes/hermes_conversational.py` (main handler — **no prometheus_client usage**)
- `systemd/hermes-gateway.service` (Hermes gateway systemd unit)
- `docs/setup-evidence/hermes-migration/phase-7c/phase-7c-safe-subset-completion-report.md` (B12 status)

---

## 1. Executive Summary

The Hermes monitoring stack has **4 metrics defined and emitting**, serving **5 functional dashboard panels** and **3 functional alert rules**. However, **5 dashboard panels show placeholder values** (`vector(0)`), **2 alert rules reference nonexistent metrics**, and **3 alert rules rely on proxy metrics** because their dedicated metrics were never instrumented.

**B12** (Hermes-native gateway metrics missing) from the Phase 7 blocker register remains **fully open**. The metrics on port 9191 are emitted by the FastAPI bot process (`main.py` lifespan), **not** by the Hermes Agent gateway process (`hermes --config ... gateway`). The actual Hermes gateway process (`hermes-gateway.service`) exposes **zero metrics**.

---

## 2. Actually Instrumented Metrics (Phase 6 — Existing)

Defined in `src/core/services/llm_metrics.py` and emitted by `src/core/services/llm_router.py`:

| Metric | Type | Labels | Emitted From |
|---|---|---|---|
| `hermes_llm_calls_total` | Counter | `model`, `status` | `llm_router.py:observe_call()` |
| `hermes_llm_latency_seconds` | Histogram | `model` | `llm_router.py:observe_latency()` |
| `hermes_llm_cost_usd_total` | Counter | `model` | `llm_router.py:observe_cost()` |
| `hermes_fallback_activations_total` | Counter | `from_model`, `to_model` | `llm_router.py:observe_fallback()` |

**Served on**: `localhost:9191/metrics` via `start_llm_metrics_server(port=9191)` called from `main.py` lifeycle (`src/core/main.py:43-45`).

**Critical observation**: These metrics are emitted by the **FastAPI/Discord bot process** (which imports and uses `LLMRouter`), not by the Hermes Agent gateway process (`hermes-gateway.service`). The systemd `hermes-gateway.service` runs `hermes --config ... gateway` — a completely separate Python process that does not call `start_llm_metrics_server()`.

---

## 3. Prometheus Scrape Target Analysis

From `monitoring/prometheus/prometheus.yml`:

| Job | Target | Port | Path | Instance Label | Status |
|---|---|---|---|---|---|
| `fastapi` | `host.docker.internal:8000` | 8000 | `/metrics` | (default) | ✅ Correct — FastAPI app `guinevere_*` metrics |
| `hermes` | `host.docker.internal:9191` | 9191 | `/metrics` | `hermes-gateway` | ⚠️ **Misleading label** — actually scrapes FastAPI bot process metrics, not Hermes gateway |

**Finding**: The `hermes` job scrapes port 9191, which is started by `main.py` (FastAPI/Discord bot process). The Prometheus dashboard and alert `up{job="hermes"}` actually checks whether the FastAPI process's metrics server is alive, **not** whether the Hermes gateway process is running. The `instance` relabel `hermes-gateway` creates a false semantic association.

**What's missing from scrape config**: No scrape target for the actual Hermes gateway process. The gateway runs on `host.docker.internal:9191` only if the bot process starts the metrics server; the actual Hermes gateway (`hermes --config ... gateway`) does not self-export metrics.

---

## 4. Grafana Dashboard Panel Gaps

From `monitoring/grafana/dashboards/guinevere-hermes.json`:

### 4.1 Functional Panels (Working Correctly)

| Panel | ID | Expression | Status |
|---|---|---|---|
| Gateway Status | 1 | `up{job="hermes"}` | ✅ Works (shows FastAPI metrics server up, not Hermes gateway up) |
| LLM Calls Rate | 2 | `rate(hermes_llm_calls_total[5m])` | ✅ Works |
| LLM Latency (p50/p95/p99) | 3 | `histogram_quantile(0.5/0.95/0.99, rate(hermes_llm_latency_seconds_bucket[5m]))` | ✅ Works |
| Cumulative LLM Cost | 4 | `hermes_llm_cost_usd_total` / `rate(...[1h])` | ✅ Works |
| Fallback Activations | 5 | `rate(hermes_fallback_activations_total[5m])` | ✅ Works |

### 4.2 Placeholder Panels (Never Instrumented — Show `vector(0)`)

| Panel | ID | Expression | Gap | Requires |
|---|---|---|---|---|
| Safety Blocks | 6 | `sum(rate(hermes_safety_blocks_total[5m])) or vector(0)` | ❌ Metric never defined | New Counter `hermes_safety_blocks_total{reason,severity}` |
| HARD STOP Events | 7 | `sum(increase(hermes_hard_stop_events_total[24h])) or vector(0)` | ❌ Metric never defined | New Counter `hermes_hard_stop_events_total{source}` |
| Memory Recall Latency | 8 | `rate(llm_latency_sum)/rate(llm_latency_count) or vector(0)` | ⚠️ Uses LLM proxy, not dedicated metric | New Histogram `hermes_memory_recall_latency_seconds{operation}` |
| Model Call Rate | 9 | `rate(hermes_llm_calls_total[5m])` | ⚠️ Aggregate only, no per-model breakdown | New Counter `hermes_model_calls_total{model,status}` or use existing `hermes_llm_calls_total{model}` with proper breakdown in panel |

### 4.3 Missing Panels (No Coverage)

| Area | Suggested Panel | Why Needed |
|---|---|---|
| Session health | Hermes session error rate | `session_adapter.py` has 5 error log paths with zero metrics |
| Rate limit hits | Rate limit events counter | `conversational_handler.py` has no metric for rate limit absorption |
| Memory bridge health | Memory recall/store success/error rate | `memory_bridge.py` swallows errors silently — no observability |
| Distress detection | Distress detection count | `conversational_handler.py` detects distress but no metric |
| Adapter health | Hermes adapter Redis connectivity | Redis session store failures are logged but unmonitored |
| Safety plugin | Safety gate pass/fail per gate | `safety_plugin.py` logs 6 hooks but emits zero prometheus metrics |
| Provider breakdown | Per-provider latency/cost/error | Current histograms have `model` label but panels don't break down by it |

---

## 5. Alert Rule Gaps

From `monitoring/prometheus/rules/guinevere-alerts.yml`:

### 5.1 Functional Hermes Alerts

| Rule | Severity | Expression | Status |
|---|---|---|---|
| `GuinevereHermesGatewayDown` | SEV1 | `up{job="hermes"} == 0` | ⚠️ Functional but checks wrong process (FastAPI metrics, not Hermes gateway) |
| `GuinevereHermesLatencyHigh` | SEV2 | `histogram_quantile(0.95, rate(hermes_llm_latency_seconds_bucket[5m])) > 5` | ✅ Functional |
| `GuinevereHermesBudgetNearCap` | SEV2 | `hermes_llm_cost_usd_total > 24` | ✅ Functional |

### 5.2 Dead Alert Rules (Reference Nonexistent Metrics — Never Fire)

| Rule | Severity | Expression | Problem |
|---|---|---|---|
| `GuinevereHermesSafetyBlocksSpike` | SEV2 | `rate(hermes_safety_blocks_total[5m]) > 10` | ❌ `hermes_safety_blocks_total` was **never instrumented** — alert will **never fire** |
| `GuinevereHermesMemoryRecallLatency` | SEV3 | `rate(llm_latency_sum)/rate(llm_latency_count) > 10` | ⚠️ Uses aggregate LLM latency as proxy for memory recall — may trigger false positives or miss real memory issues |
| `GuinevereHermesModelCallsAnomaly` | SEV3 | `rate(hermes_llm_calls_total[5m]) > 100` | ⚠️ Aggregate only — without per-model breakdown, a single model spike masked by others. Annotations note "pending Phase 7c" |

### 5.3 Missing Alert Rules

| Alert | Severity | Proposed Expression | Why Needed |
|---|---|---|---|
| Excessive fallbacks | SEV3 | `rate(hermes_fallback_activations_total[5m]) > 5` | Fallback chain indicates provider degradation |
| Hermes session errors | SEV3 | `rate(hermes_session_errors_total[15m]) > 0` | Session load/save failures affect user experience |
| Memory bridge failures | SEV3 | `rate(hermes_memory_bridge_errors_total[15m]) > 0` | Silent memory failures degrade persona quality |
| Rate limit threshold breach | SEV4 | `rate(hermes_rate_limit_events_total[5m]) > 0` | Detects potential abuse or misconfigured limits |

### 5.4 Annotations Confirming Pending Status

From `guinevere-alerts.yml`:

> **GuinevereHermesMemoryRecallLatency**: "Note: Hermes-native hermes_memory_recall_latency_seconds metric pending instrumentation (Phase 7c)."

> **GuinevereHermesModelCallsAnomaly**: "Note: Per-model hermes_model_calls_total metric pending instrumentation (Phase 7c)."

Dashboard descriptions also confirm:
- Panel 6: "Requires hermes_safety_blocks_total metric from Hermes-native instrumentation (Phase 7c). Currently returns 0 if metric is absent."
- Panel 7: "Requires hermes_hard_stop_events_total metric from Hermes-native instrumentation (Phase 7c). Currently returns 0 if metric is absent."

---

## 6. Alertmanager Routing Analysis

From `monitoring/alertmanager/alertmanager.yml`:

### 6.1 Existing Hermes Routes

| Alert | Receiver | Repeat Interval | Correct? |
|---|---|---|---|
| `GuinevereHermesGatewayDown` | discord-critical + gotify-critical | 2m | ✅ Correct for SEV1 |
| `GuinevereHermesLatencyHigh\|SafetyBlocksSpike\|BudgetNearCap` | discord-warning + gotify-warning | 10m | ⚠️ SafetyBlocksSpike will never fire (dead metric) |
| `GuinevereHermesMemoryRecallLatency\|ModelCallsAnomaly` | discord-info | 30m | ⚠️ Both use proxy metrics or aggregate data |

### 6.2 Routing Issues

1. **Hermes-specific routes use `match_re` with a pipe-delimited list** — this works but is fragile. If a new Hermes SEV2 alert is added (e.g., excessive fallbacks), it will fall through to the generic SEV2 route with a 4h repeat interval instead of 10m.

2. **All webhook receivers point to** `http://localhost:8000/internal/alertmanager/webhook` — the Gotify "receivers" named `gotify-critical` and `gotify-warning` also point to the same FastAPI webhook, suggesting Gotify routing is handled inside the FastAPI app logic, not in Alertmanager.

3. **Inhibit rules** suppress SEV2 when SEV0 fires for same alertname, and SEV3 when SEV1 fires — this is correct but may mask SEV3 Hermes alerts if SEV1 gateway fires simultaneously.

---

## 7. Log Shipping & Annotation Analysis

From `monitoring/promtail/promtail-config.yml`:

### 7.1 Systemd Journal Scraping

```
job_name: journal
relabel_configs:
  - source_labels: ["__journal__systemd_unit"]
    regex: "(?:guinevere|hermes)-(.+)\\.service"
    target_label: "service"
```

✅ Correctly matches `hermes-gateway.service` and extracts "gateway" as the service label.

### 7.2 Issues

1. **No structured log parsing for Hermes logs**. The journald job does not apply pipeline stages to parse JSON-structured logs from the Hermes gateway. The Hermes process writes structured JSON via `structlog`, but Promtail is not extracting `level`, `component`, or `event_type` labels from Hermes journal entries.

2. **The `varlogs` pipeline** only applies JSON parsing to `/var/log/guinevere*.log`, not to Hermes-specific log paths.

3. **No Loki log alert rules** reference Hermes log patterns. All Hermes alerting is Prometheus-metric-based. There are no `LogQL` alert rules for Hermes error patterns.

---

## 8. Comprehensive Gap Matrix

| Gap ID | Area | Severity | Current State | Action Required |
|---|---|---|---|---|
| G1 | **Metrics — safety** | HIGH | `hermes_safety_blocks_total` never instrumented; alert + dashboard reference dead metric | Define and instrument Counter in `llm_metrics.py` or `safety_plugin.py` |
| G2 | **Metrics — HARD STOP** | HIGH | `hermes_hard_stop_events_total` never instrumented; dashboard shows `vector(0)` | Define and instrument Counter |
| G3 | **Metrics — memory recall** | MEDIUM | `hermes_memory_recall_latency_seconds` never instrumented; uses LLM latency proxy | Define and instrument Histogram in memory bridge |
| G4 | **Metrics — per-model breakdown** | MEDIUM | Current `hermes_llm_calls_total{model}` has model label but panels show aggregate only | Add panel with `rate(hermes_llm_calls_total[5m]) by (model)` |
| G5 | **Metrics — session errors** | LOW | No session error metric; `session_adapter.py` has 5 error paths with zero metrics | Define and instrument Counter |
| G6 | **Metrics — rate limiting** | LOW | No rate limit metric; all `_is_rate_limited()` calls silently absorbed | Define and instrument Counter |
| G7 | **Metrics — memory bridge** | LOW | No memory bridge health metric; errors logged but unmeasured | Define Counter in `memory_bridge.py` |
| G8 | **Metrics — safety plugin** | LOW | `safety_plugin.py` has 6 hooks but zero prometheus metrics | Consider adding gate pass/fail counters |
| G9 | **Metrics — distress detection** | LOW | Distress detection events logged but not metrified | Consider adding Counter |
| G10 | **Scrape — false label** | MEDIUM | `hermes` job scrapes FastAPI process, labeled as `hermes-gateway` | Add actual Hermes gateway scrape target, or relabel accurately |
| G11 | **Dashboard — missing panels** | MEDIUM | No panels for session health, rate limits, memory bridge, adapter health | Add panels after metrics defined |
| G12 | **Dashboard — placeholder panels** | HIGH | 4 of 9 panels show `vector(0)` or proxy data | Add real metrics, then remove `or vector(0)` fallbacks |
| G13 | **Alerts — dead rules** | HIGH | 1 rule never fires (SafetyBlocksSpike); 2 rules use proxy data | Fix metrics, fix expressions |
| G14 | **Alerts — missing safe-mode fallback** | LOW | No alert for distress detection activation | Consider SEV3 alert |
| G15 | **Promtail — missing Hermes JSON parsing** | LOW | No pipeline stages for Hermes structured logs | Add JSON parsing stages for `hermes-gateway` service |
| G16 | **Metrics server ownership** | HIGH | Metrics on `:9191` come from FastAPI bot, not Hermes gateway process — confusing architecture | Clarify ownership; consider moving metrics to actual Hermes gateway process |

---

## 9. Priority Recommendations for B8 Implementation

### Immediate (Unblocks dashboard + alert fix)

1. **Instrument `hermes_safety_blocks_total{reason,severity}`** — Counter in `llm_metrics.py` or preferably in `safety_plugin.py` where safety gates actually execute. This unblocks Panel 6 and the `GuinevereHermesSafetyBlocksSpike` alert.

2. **Instrument `hermes_hard_stop_events_total{source}`** — Counter. Unblocks Panel 7.

3. **Instrument `hermes_memory_recall_latency_seconds{operation}`** — Histogram. Unblocks Panel 8 and the `GuinevereHermesMemoryRecallLatency` alert.

4. **Add per-model breakdown panel** — Modify Panel 9 or add new panel: `rate(hermes_llm_calls_total[5m]) by (model)`. Unblocks `GuinevereHermesModelCallsAnomaly` alert specificity.

5. **Replace `vector(0)` fallbacks** — Remove `or vector(0)` from dashboard expressions once real metrics exist.

### Short-Term (Phase 7c or B9)

6. **Fix scrape target semantics** — Either add a dedicated `hermes-gateway` job for the actual gateway process, or relabel the existing `fastapi` job accurately and rename `hermes` job to `hermes-metrics-server`.

7. **Add session error metric** — `hermes_session_errors_total{error_type}` in `session_adapter.py`.

8. **Add fallback alert** — `rate(hermes_fallback_activations_total[5m]) > 5` as SEV3.

### Technical Debt

9. **Add memory bridge metrics** — `hermes_memory_bridge_errors_total{operation}` and `hermes_memory_bridge_calls_total{operation,status}`.

10. **Add Promtail JSON parsing stages** for `hermes-gateway` service logs.

11. **Add rate limit metrics** — `hermes_rate_limit_events_total` Counter.

---

## 10. File Path Reference

| File | Purpose |
|---|---|
| `src/core/services/llm_metrics.py` | **Primary**: Define new Hermes metric families here |
| `src/core/services/llm_router.py` | Emission of LLM call/latency/cost/fallback metrics |
| `src/hermes/safety_plugin.py` | **Target**: Add `hermes_safety_blocks_total` counter in Gate 01/02/05 |
| `src/hermes/session_adapter.py` | **Target**: Add `hermes_session_errors_total` counter |
| `src/hermes/memory_bridge.py` | **Target**: Add memory recall latency histogram + error counters |
| `src/hermes/hermes_conversational.py` | **Target**: Add rate limit + distress detection metrics |
| `monitoring/grafana/dashboards/guinevere-hermes.json` | **Target**: Update panel expressions, remove `vector(0)`, add new panels |
| `monitoring/prometheus/rules/guinevere-alerts.yml` | **Target**: Fix dead alert rules, add missing alerts |
| `monitoring/prometheus/prometheus.yml` | **Target**: Fix scrape target semantics |
| `monitoring/promtail/promtail-config.yml` | **Target**: Add Hermes JSON pipeline stages |
| `systemd/hermes-gateway.service` | Reference only — actual Hermes gateway process unit |
| `src/core/main.py` | Metrics server startup (line 43-45) — currently the sole metrics endpoint owner |

---

## 11. Key Architectural Finding

The metrics server on port 9191 (`start_llm_metrics_server(port=9191)`) is started **inside** the FastAPI `main.py` lifespan. This means:

1. The metrics server lives as a daemon thread in the FastAPI/Discord bot process.
2. If the bot process dies, port 9191 dies — `up{job="hermes"}` goes to 0 and triggers `GuinevereHermesGatewayDown`.
3. The actual Hermes Agent gateway (`hermes --config ... gateway` via systemd) can be running healthily while `up{job="hermes"}` = 0, creating a false positive alert.
4. Conversely, the Hermes gateway can be down while port 9191 is up (if the bot is running but the gateway crashed), creating a false negative.

**Recommendation**: For B8, either:
- **(Option A)** Instrument metrics directly in the `hermes-gateway` process so port 9191 reflects actual gateway health, OR
- **(Option B)** Rename the `hermes` job to `fastapi-llm-metrics` and add a dedicated `hermes-gateway` job that scrapes the actual gateway's metric endpoint (once the gateway is instrumented), OR
- **(Option C)** At minimum, update the dashboard and alert descriptions to clarify that `up{job="hermes"}` checks the LLM routing metrics server (bot process), not the Hermes gateway process.

---

## 12. Conclusion

B8 implementation must address **G1-G4** (safety blocks, HARD STOP, memory recall latency, per-model breakdown metrics) to unblock the 4 placeholder dashboard panels and 3 alert rules. Additionally, **G10** (scrape target semantic mismatch) and **G16** (metrics server ownership ambiguity) should be resolved to prevent false positive/negative alerts.

The existing monitoring stack is well-architected for what it covers (LLM routing metrics), but the Hermes-native metrics promised in Phase 7c were **never instrumented**. The infrastructure (Prometheus, Grafana, Alertmanager, Promtail, Loki) is fully ready to consume them — the gap is purely in metric definition and emission from the Hermes source files.

---

## Footer

Generated by Sisyphus for Guinevere ADR-035 Phase 7c B8 gap analysis. All files examined are local repository versions; no VPS runtime was accessed.
