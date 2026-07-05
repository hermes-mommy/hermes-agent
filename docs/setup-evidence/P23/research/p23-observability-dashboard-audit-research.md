# P23 Research — Observability / Dashboard / Audit

> Status: RESEARCH (definition phase). Date: 2026-06-25. Author: Guinevere (parent-authored; subagent attempts timed out twice on API errors — provenance documented per AGENTS.md §14, mirroring P21 §2 acceptance of parent-authored replacement files).
> Scope: P23 Embodied Operations / Personal OS Action Layer — observability, Discord dashboard, audit trail, evidence/artifact model, soak strategy.

## 1. Objective

Define how P23 makes autonomous action **provable and debuggable**: a Discord dashboard section that proves action state (queued/running/done/failed/rolled-back), a log channel streaming lifecycle events, Prometheus metrics + Grafana, a hash-chained immutable audit trail distinct from the reasoning journal, an evidence/artifact model that never leaks secrets, SLO alerts, cost tracking, and a 24h soak gate. This research satisfies the P23 hard-rejection criteria: "Discord dashboard must prove queued/running/done/failed/rollback state" and "audit trail stores reasoning, command intent, outcome, artifact path, rollback state."

## 2. Sources Consulted

### Local Files (parent-read)
- `src/life_kernel/dashboard.py:19-216` — `DashboardRenderer` class; `_render_full()` joins sections `[heartbeat, state, goals, commitments, concerns, sessions, audit, autonomy]` (lines 201-214); per-section pattern `_X_section(self, state) -> str` (e.g. `_heartbeat_section:76`, `_audit_section:162`, `_autonomy_section:176`); `_state_checksum`/`_sanitize`/`_fmt_timestamp` helpers; `render(graph_state)` entrypoint (line 216). **P23 adds `_actions_section` additively.**
- `src/life_kernel/dashboard_writer.py` — writes the rendered dashboard markdown to the persistent Discord message (edit-not-spam).
- `src/life_kernel/discord_rest_client.py` — Option-B core-integrated REST publisher (Oracle-confirmed per PROGRESS.md:946); publishes to the dashboard channel without a sidecar bot.
- `src/life_kernel/log_channel.py` + `src/life_kernel/log_writer.py` — streams lifecycle/log events to a Discord log channel.
- `src/life_kernel/journal.py` — the **reasoning journal** ("why Guinevere chose this action"); V-007 audit-for-debugging source.
- `src/gmail/metrics.py:5-121` — Prometheus pattern: `from prometheus_client import Counter, Gauge, Histogram`; module-level metric instances + thin `record_X()`/`set_X()` wrapper functions (e.g. `GMAIL_CONNECTED = Gauge(...)` line 7, `record_email_received(category)` line 83). **P23 metrics mirror this exactly.**
- `src/observability/` — existing observability package (Prometheus registry, metrics export).
- `src/core/services/cost_tracker.py` — `CostTracker` class; `record_cost(...)` feeds Redis DB5 `cost:by_model:*` / `ratelimit:total:*` keys; USD 30/mo cap enforcement (IMPLEMENTATION_GUIDE §5).
- `docs/setup-evidence/P22/plan/p22-life-integration-hub-plan.md` §Audit Trail Model (lines 122-184) — `audit.integration_api_log` hash-chained DDL, `no_update_or_delete` CHECK, WORM cold archive after 1 year. **P23 audit.action_log mirrors this schema.**
- `src/life_kernel/heartbeat.py:254-358` — `_heartbeat_1s()` HARD-STOP detector; P23 dashboard must reflect HARD-STOP state.
- `docs/40-operations/40-ObservabilityAlertingSpec_v1.0.md` — observability + alerting spec.
- `docs/40-operations/41-SLO_SLA_ErrorBudget_v1.0.md` — SLO/SLA + error budget.
- `docs/setup-evidence/P20/README.md` — P20 EARLY PRODUCTION ACCEPTANCE / operator waived 24h soak / PASS WITH ACCEPTED RISK (P23-020 still runs its OWN 24h soak after implementation, which is separate and still valid).

### Sibling Research (cross-ref)
- `p23-policy-gate-risk-classification-research.md` — risk tiers L1-L4, 7-step gate, distress freeze.
- `p23-rollback-idempotency-research.md` — action lifecycle states (queued→scheduled→pre-flight→running→succeeded/failed/rolled-back/cancelled/timed-out), `audit.p23_action_log` DDL.
- `p23-security-secrets-consent-research.md` — redaction pipeline, hash-chain audit.

### External References
- Prometheus client_python docs — https://github.com/prometheus/client_python (retrieved 2026-06-25)
- Grafana dashboarding — https://grafana.com/docs/grafana/latest/dashboards/ (retrieved 2026-06-25)

## 3. Findings

### 3.1 Dashboard Integration (additive "ACTIONS" section)

P23 extends `DashboardRenderer` (`src/life_kernel/dashboard.py:19`) with a new `_actions_section(self, state: LifeMindState) -> str` method, registered into the `_render_full()` section list (line 203-214) AFTER `_autonomy_section`. This mirrors the P21 `_voice_section` additive pattern exactly (P21 plan §File Structure). **Additive only — no existing section modified.**

The section renders a compact action-state summary:

```text
## ⚡ ACTIONS
queue_depth: 3 | running: 1 | hard_stop: CLEAR | safe_mode: D0
▶ running: p23:browser:obscura:nav-042 (L1, 12s) — extracting pricing table
✓ done   : p23:github:repo:pr-019 (L2, 2m ago) — PR #124 created
✗ failed : p23:vps:deploy:deploy-007 (L3, 5m ago) — canary smoke FAILED → rolled-back
↩ rolled : p23:filesystem:write:cfg-003 (L2, 8m ago) — restored from backup
```

**State fields (additive `NotRequired` on `LifeMindState`):** `actions_queue_depth: int`, `actions_running: list[ActionSummary]`, `actions_recent: list[ActionSummary]` (last 5 done/failed/rolled-back), `actions_hard_stop: str` (mirrors `life_kernel:hard_stop` Redis value), `actions_safe_mode: str` (D0-D4). These are `NotRequired` so existing checkpoint replay does not break (P21 precedent: `voice_listening_mode` etc.). Sensitive fields (intent text) are redacted via `DashboardRenderer._sanitize` (line 58) before rendering — **never raw command/secrets in the dashboard**.

**Edit-not-spam:** `dashboard_writer.py` updates the single persistent dashboard message in place (checksum-gated via `_state_checksum` line 44 — only re-publishes if state changed), avoiding Discord rate-limit spam. This is the existing P20 pattern; P23 just adds fields.

### 3.2 Log Channel (action lifecycle streaming)

`log_channel.py` + `log_writer.py` stream P23 action lifecycle events to `#actions-log` (new dedicated channel; fallback `#system-health`). Each event is a minimal, redacted one-liner:

```text
[2026-06-25T14:03:12 WIB] QUEUED    p23:browser:nav-042  L1  namespace=default
[2026-06-25T14:03:13 WIB] STARTED   p23:browser:nav-042  executor=browser
[2026-06-25T14:03:25 WIB] SUCCEEDED p23:browser:nav-042  duration=12s  artifact=evidence/actions/nav-042/
[2026-06-25T14:08:01 WIB] FAILED    p23:vps:deploy-007  stage=canary_smoke  err=health_check_timeout
[2026-06-25T14:08:03 WIB] ROLLED    p23:vps:deploy-007  restored_from=backup_2026-06-25_1408
[2026-06-25T14:10:00 WIB] CANCELLED p23:github:pr-021    reason=HARD_STOP
```

**Event schema:** `{timestamp_wib, action_id, namespace, executor, surface, risk_tier, event(QUEUED|STARTED|SUCCEEDED|FAILED|ROLLED_BACK|CANCELLED|TIMED_OUT), duration_s?, stage?, error_code?, artifact_path?, correlation_id}`. **Redaction:** every field passes `secret_scanner` (src/surveillance/secret_scanner.py) before publish — secrets → `[REDACTED:hash]`, PII minimized. No raw command text in the log channel (only intent summary + artifact path).

### 3.3 Prometheus Metrics (mirror src/gmail/metrics.py)

P23 creates `src/life_kernel/action_metrics.py` (or `src/observability/p23_metrics.py`) following the `src/gmail/metrics.py:5-121` pattern exactly: module-level `Counter`/`Gauge`/`Histogram` instances + thin `record_X()`/`set_X()` wrappers.

| Metric | Type | Labels | Purpose |
|---|---|---|---|
| `P23_ACTION_QUEUED_TOTAL` | Counter | executor, risk_tier, namespace | actions entering the queue |
| `P23_ACTION_RUNNING` | Gauge | executor | currently-executing actions |
| `P23_ACTION_DURATION_SECONDS` | Histogram | executor, risk_tier, outcome | end-to-end action latency |
| `P23_ACTION_SUCCEEDED_TOTAL` | Counter | executor, risk_tier | successful actions |
| `P23_ACTION_FAILED_TOTAL` | Counter | executor, risk_tier, error_code | failed actions |
| `P23_ACTION_ROLLED_BACK_TOTAL` | Counter | executor, risk_tier | rolled-back actions |
| `P23_ACTION_CANCELLED_TOTAL` | Counter | executor, reason | cancelled (HARD_STOP/explicit) |
| `P23_HARD_STOP_CANCELLATIONS_TOTAL` | Counter | (none) | HARD-STOP-driven cancellations |
| `P23_CONSENT_VIOLATION_TOTAL` | Counter | surface, scope | consent-gate blocks |
| `P23_INJECTION_BLOCKED_TOTAL` | Counter | vector(V-023) | injection-sanitizer blocks |
| `P23_SECRET_REDACTED_TOTAL` | Counter | executor | secret-scanner redactions |
| `P23_EXECUTOR_HEALTH` | Gauge | executor, surface | 1=healthy, 0=unhealthy |
| `P23_QUEUE_DEPTH` | Gauge | (none) | durable queue backlog |
| `P23_ACTION_COST_USD` | Counter | executor, cost_kind(planner\|self_debug\|api) | USD spend per action |
| `P23_RETRY_TOTAL` | Counter | executor, attempt | retry attempts |
| `P23_DEAD_LETTER_TOTAL` | Counter | executor, risk_tier | exhausted-retry actions |

**Registry:** reuses the existing Prometheus registry in `src/observability/` (no new port; if a separate HTTP server is needed, use a port ≠ 9191 already used by `llm_metrics` per `src/core/main.py` — P21 A6 precedent). Scraped by the existing Prometheus on 9090.

### 3.4 Grafana Dashboard

New Grafana dashboard "P23 Embodied Operations" (mirrors existing guinevere dashboards). Panels:
1. **Action throughput** — queued vs succeeded vs failed vs rolled-back (time series, stacked).
2. **Queue depth + running** — gauges + time series (detect stuck queue).
3. **Action duration p50/p95** — histogram by executor.
4. **Failure rate by executor** — alert when >10% over 5min.
5. **HARD-STOP cancellations** — counter + alert on any increase.
6. **Consent violations + injection blocks** — security surface.
7. **Executor health** — status panel (green/red per executor).
8. **Cost by executor** — USD accumulation vs $30/mo cap line.
9. **Retry/dead-letter** — reliability surface.

### 3.5 Audit Journal vs Audit Log (critical distinction)

P23 maintains **two separate audit surfaces** with different purposes (AGENTS.md §0.1 V-007: "audit for self-diagnosis and debugging, not as a default approval bottleneck"):

| Surface | Location | Purpose | Mutability | Content |
|---|---|---|---|---|
| **Reasoning Journal** | `src/life_kernel/journal.py` → `journal` table | "WHY Guinevere chose this action" — self-debug, self-improvement (V-006/V-007) | Append, curable (Guinevere may summarize/expire) | HermesBrain reasoning trace, alternatives considered, failure analysis, rollback rationale |
| **Compliance Audit Log** | `audit.action_log` (new table, mirrors P22 `audit.integration_api_log`) | "WHAT/WHEN/WHO" — immutable compliance trail, tamper-evident | **WORM** (no UPDATE/DELETE, hash-chained) | event_id, sequence, actor, executor, surface, action_id, namespace, risk_tier, intent_hash, command_redacted, outcome, artifact_path, rollback_state, previous_hash, event_hash |

Both are required. The journal is for Guinevere to debug herself (V-007); the audit log is for evidence/compliance/tamper-detection. The journal feeds `self_improve.py` (action outcomes → improvement candidates); the audit log feeds the dashboard `_audit_section` + external review.

### 3.6 Evidence / Artifact Model

Each action writes an artifact directory under `docs/setup-evidence/P23/evidence/actions/<action-id>/`:

```text
actions/nav-042/
  ├── screenshot.png          # full-page browser screenshot (browser executor)
  ├── dom_snapshot.html       # DOM at action time
  ├── har.log                 # network capture (browser)
  ├── command_transcript.redacted.md   # redacted command + intent
  ├── stdout.redacted.log     # redacted executor stdout
  ├── stderr.redacted.log     # redacted executor stderr
  ├── rollback_state.json     # rollback snapshot reference
  └── meta.json               # action_id, namespace, executor, risk_tier, correlation_id, artifact_hashes
```

**Rules:**
- Every file passes `secret_scanner` + PII redaction BEFORE write. Secrets → `[REDACTED:sha256:8chars]`. **Never raw secrets/personal/intimate/surveillance data in artifacts** (AGENTS.md BLOCKING).
- `meta.json` stores SHA-256 hashes of each artifact file (tamper-evidence).
- `artifact_path` stored in the `audit.action_log` row.
- Retention: artifacts retained per data-classification (Restricted/Critical → encrypted at rest, `envelope-AES-256-GCM`; mirror P21/P22 retention). Raw surveillance-class captures (browser screenshots, desktop screenshots) ≤24h unless incident hold (mirror P21 raw-audio 24h policy + V-013/V-014 camera/screenshot precedent).
- Artifacts NEVER sent to external MCP/web tools (AGENTS.md §12 consent-safety).

### 3.7 SLO / Alerts (docs/40-operations/40, 41)

| Alert | Condition | Severity | Channel |
|---|---|---|---|
| ActionFailureRate | failed_total/(succeeded+failed) > 10% over 5min | WARNING | #system-health |
| ActionFailureRateCritical | > 25% over 5min | CRITICAL | #system-health + DM Faiz |
| QueueStuck | queue_depth > 0 AND no SUCCEEDED in 10min | WARNING | #system-health |
| QueueBacklog | queue_depth > 50 | WARNING | #system-health |
| ExecutorUnhealthy | P23_EXECUTOR_HEALTH == 0 for any executor > 2min | CRITICAL | #system-health + DM |
| HardStopActive | `life_kernel:hard_stop` set | CRITICAL | #system-health (dashboard) |
| ConsentViolation | P23_CONSENT_VIOLATION_TOTAL increases | WARNING | #audit-log |
| InjectionBlocked | P23_INJECTION_BLOCKED_TOTAL increases | WARNING | #audit-log |
| SecretRedactionSpike | P23_SECRET_REDACTED_TOTAL > baseline 3σ | WARNING | #audit-log + DM |
| CostApproachingCap | monthly spend > $25 | WARNING | #system-health |
| CostHardStop | monthly spend ≥ $30 | CRITICAL | all LLM blocked (CostTracker) |

SLOs (per 41-SLO_SLA): action success rate ≥ 95% (L1/L2); queue drain time p95 < 60s; executor uptime ≥ 99%; HARD-STOP propagation < 1s (heartbeat 1s cadence).

### 3.8 Cost Tracking

Every P23 action incurs: (a) LLM cost — planner `HermesBrain.think()` + self-debug `think()` on failure; (b) executor API cost — external integrations (GitHub $0, browser $0, VPS $0; calendar/tasks/notes $0 per P22). All feed `CostTracker.record_cost(model='p23:<executor>:planner'/'p23:<executor>:self_debug'/'p23:<executor>:api', ...)` (`src/core/services/cost_tracker.py`) → Redis DB5 `cost:by_model:*` / `ratelimit:total:monthly:*`. USD 30/mo cap auto-includes P23 (existing cap, no new budget line). P23 sub-cap: `p23.cost.monthly_cap_usd` within system cap (mirror P21 voice sub-cap pattern). Cost tags surfaced in `P23_ACTION_COST_USD` metric + dashboard.

### 3.9 Soak Strategy (P23-020 final gate)

P23-020 = 24h production soak mirroring LK-017 (P20 README:80-90):
- Action queue live (L1/L2 actions executing autonomously).
- HARD-STOP tested (spoken/typed safe word → `life_kernel:hard_stop` → all queued+running actions CANCELLED → dashboard reflects → recovery clears).
- No P20 regression: `python -m pytest tests/life_kernel/ -q` stays 420 passed / 7 skipped (P20 README:88).
- No Aizanta impact: `systemctl status aizanta-*` + `docker ps --filter name=aizanta` + `redis-cli -n 10 PING` green throughout (IMPLEMENTATION_GUIDE §6 verify).
- Metrics green: failure rate < 10%, no queue stuck, no executor unhealthy.
- Audit hash-chain integrity verified (periodic re-derivation job — no breaks).
- Evidence: 24h soak report + metrics snapshots + HARD-STOP test recording.

## 4. Implications for P23 Design

- **P23-017 (Discord dashboard/log UX)** owns the `_actions_section` + log channel wiring — additive to `dashboard.py`/`log_channel.py`, P20 non-interference respected.
- **P23-018 (Observability/metrics/alerts)** owns `action_metrics.py` + Grafana + alert rules.
- **P23-016 (Audit journal + artifacts + redaction)** owns the dual audit surface (journal + `audit.action_log`) + artifact model + redaction pipeline.
- Metrics + dashboard + audit are ADDITIVE to P20 — never modify `_heartbeat_1s`, the 6-interval schedule, `hermes_brain.py`, or `graph.py`.
- The `LifeMindState` additions are `NotRequired` (checkpoint-replay-safe, P21 precedent).

## 5. Risks / Open Questions

1. **Dashboard message size:** adding ACTIONS section may exceed Discord 2000-char embed limit if queue is deep — mitigate by truncating to last 5 + "queue_depth: N" summary (P21 dashboard truncation precedent).
2. **Artifact storage growth:** screenshots/HAR/DOM can be large — enforce 24h purge for surveillance-class + encrypted-at-rest + periodic cleanup job. Disk budget on 60GB Guinevere slice.
3. **Audit hash-chain verification cadence:** hourly? daily? — recommend hourly (cheap) + daily full re-derivation.
4. **Log channel rate-limit:** high action throughput could spam `#actions-log` — apply slowapi + Redis DB5 bucket (mirror P22 throttle) + batch lifecycle events.
5. **Journal vs audit overlap:** ensure no duplication — journal = narrative reasoning (curable); audit = structured event (immutable). Clear schema separation.
6. **Prometheus port:** if P23 needs a dedicated metrics HTTP server, must not collide with 9191 (`llm_metrics`) — prefer reuse of shared registry/gateway (P21 A6).

## 6. Recommendations to Planner

- P23-017 scaffold: add `_actions_section` to `DashboardRenderer` (after `_autonomy_section`), add `NotRequired` action fields to `LifeMindState`, wire `log_channel.py` for action lifecycle events. Forbidden: modifying existing sections, non-`NotRequired` state fields, raw secrets in dashboard.
- P23-018 scaffold: create `src/life_kernel/action_metrics.py` mirroring `src/gmail/metrics.py`; Grafana dashboard JSON; alert rules in Prometheus/Grafana. Forbidden: new port 9191 collision, metrics without labels.
- P23-016 scaffold: create `audit.action_log` Alembic migration (down_revision `p20_001_life_kernel_schema`), hash-chain helper, redaction pipeline reusing `secret_scanner`, artifact writer. Forbidden: audit rows without hash, artifacts with raw secrets, mutable audit (no UPDATE/DELETE grant).
- Soak gate (P23-020): 24h, HARD-STOP test, no P20 regression, no Aizanta impact — mirror LK-017 exactly.

## 7. Verdict

**PASS** — observability/dashboard/audit design is complete, additive to P20, mirrors proven gmail-metrics + P22-audit + P21-dashboard patterns, and satisfies all P23 hard-rejection criteria for dashboard proof + audit trail + secret-redaction. Parent-authored due to subagent API timeouts (provenance documented); content grounded in parent-read source files with exact path:line citations.
