# P23 Audit Round 1 — Observability / Evidence

> Auditor: independent. Date: 2026-06-25.

## 1. Audit Scope

This audit covers the observability and evidence dimension of P23 "Embodied Operations / Personal OS Action Layer" as defined in `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md`. It evaluates whether the design and current ground-truth files satisfy:

1. Dashboard: additive `_actions_section` with queued/running/done/failed/rolled-back state, checksum-gated edit-not-spam, and `NotRequired` state fields.
2. Log channel: lifecycle events (queued/started/succeeded/failed/rolled-back/cancelled) to `#actions-log`, minimal and redacted.
3. Prometheus metrics: mirror `src/gmail/metrics.py` with `p23_action_*` metrics, executor health, queue depth, cost, and Grafana dashboards.
4. Audit journal vs audit log distinction: `journal.py` reasoning "why" vs `audit.action_log` immutable hash-chain "what/when/who".
5. Artifacts: per-action directory with redacted contents, SHA-256 hashes, ≤24h surveillance-class retention, never external.
6. Alerts: failure rate, queue stuck, executor unhealthy, HARD-STOP active, consent violation, injection, secret-redaction spike, cost caps.
7. Soak: 24h action queue live, HARD-STOP test, no P20 regression, no Aizanta impact.

## 2. Findings

### 2.1 Dashboard — design present, implementation deferred

**Severity: INFO / LOW (planning phase)**

Path: `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:468-470`

The plan specifies an additive `_actions_section` in `DashboardRenderer`, placed after `_autonomy_section`, with `NotRequired` action fields on `LifeMindState`. The section is required to show:
- queue_depth
- running action
- last N done/failed/rolled-back
- HARD-STOP status
- safe-mode status

Ground-truth checks:
- `src/life_kernel/dashboard.py:201-214` lists sections `[heartbeat, state, goals, commitments, concerns, sessions, audit, autonomy]`; no `_actions_section` is present.
- `src/life_kernel/dashboard_writer.py:27-183` implements the existing edit-not-spam, checksum-gated pattern (verified at `dashboard_writer.py:71-143` and `dashboard.py:43-69`).
- `src/life_kernel/state.py:100-263` defines `LifeMindState` with `NotRequired[str]` precedent for P20 fields, but no P23 `NotRequired` action fields exist yet.

**Recommendation:** The design correctly uses the existing edit-not-spam writer and checksum gate; implementation is explicitly held to P23-017. Ensure the new section truncates to last 5 states to stay within Discord embed limits as noted in research §5 risk #1.

### 2.2 Log channel — design present, no implementation

**Severity: INFO / LOW (planning phase)**

Path: `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:471-472`

The plan requires lifecycle events to `#actions-log` (fallback `#system-health`) in a minimal, redacted one-liner format.

Ground-truth checks:
- `src/life_kernel/log_channel.py:1-149` defines the abstract `LogChannel` and `DiscordLogChannel` with fail-soft behavior; it does not yet include action-specific lifecycle event formatting or `#actions-log` routing.
- `src/life_kernel/log_writer.py:1-147` provides the coalesced file log writer, but is not yet wired to action lifecycle events.

**Recommendation:** At P23-017, create an action-specific log publisher that routes to `#actions-log` and applies the same `_sanitize()` and `secret_scanner` redaction used elsewhere.

### 2.3 Prometheus metrics and Grafana — design only, no runtime files

**Severity: MEDIUM (hard-rejection #14 dependency)**

Path: `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:472-474`, `docs/setup-evidence/P23/research/p23-observability-dashboard-audit-research.md:74-98`

The plan and research specify a metrics module mirroring `src/gmail/metrics.py` (`src/life_kernel/action_metrics.py` or `src/observability/p23_metrics.py`) with counters/gauges/histograms for queued, running, duration, succeeded, failed, rolled_back, cancelled, hard_stop_cancellations, consent_violation, injection_blocked, secret_redacted, executor_health, queue_depth, and cost.

Ground-truth checks:
- `src/gmail/metrics.py:1-131` provides the required Prometheus pattern.
- `src/observability/__init__.py:1-5` is a thin package; no P23 metrics exist.
- `Glob` confirms `src/life_kernel/action_metrics.py` does not exist.
- `Grep` for `p23_action_` across `src/` returned no matches.
- `monitoring/grafana/dashboards/` contains 10 dashboards but no `guinevere-p23-embodied-operations.json`.

**Recommendation:** Before claiming runtime-ready, create `src/life_kernel/action_metrics.py` (or `src/observability/p23_metrics.py`) using the `gmail/metrics.py` module-level metric + thin wrapper pattern, and add the Grafana dashboard JSON under `monitoring/grafana/dashboards/`.

### 2.4 Audit journal vs audit log — dual-surface design present, implementation deferred

**Severity: INFO / LOW (planning phase)**

Path: `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:393-435`

The plan defines:
- Reasoning journal via `src/life_kernel/journal.py` — "WHY" Guinevere chose an action; curable; feeds self-improvement.
- `audit.action_log` — immutable, hash-chained, WORM compliance log of "what/when/who".

Ground-truth checks:
- `src/life_kernel/journal.py:1-66` is a reasoning-journal writer that writes reflective entries.
- `audit.action_log` does not yet exist in the repo.
- The P22 `audit.integration_api_log` precedent is cited but not implemented for P23.

**Recommendation:** At P23-016, create the Alembic migration for `audit.action_log` with the exact DDL in the plan, including `CONSTRAINT no_update_or_delete CHECK (false)` and hash-chain fields. Ensure `journal.py` remains distinct from the compliance log.

### 2.5 Artifacts — design complete, no runtime implementation

**Severity: MEDIUM (hard-rejection #8 dependency)**

Path: `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:438-446`, `docs/setup-evidence/P23/research/p23-observability-dashboard-audit-research.md:121-142`

The plan and research specify per-action artifact directories under `docs/setup-evidence/P23/evidence/actions/<action-id>/` containing redacted screenshot, DOM snapshot, HAR, transcript, stdout/stderr, rollback_state, and meta.json with SHA-256 hashes. Surveillance-class captures are ≤24h; artifacts never sent to external MCP/web tools.

Ground-truth checks:
- No `src/life_kernel/executors/artifact_writer.py` or equivalent exists.
- No P23 action evidence directory exists yet.
- `src/life_kernel/dashboard.py:57-69` uses `_sanitize()` for secret redaction, demonstrating the existing redaction pipeline that artifacts should reuse.

**Recommendation:** Implement artifact writer in P23-016 using `secret_scanner` + PII redaction before write. Store per-action SHA-256 hashes in `meta.json` and enforce 24h purge for surveillance-class captures.

### 2.6 Alerts — design present, no implementation

**Severity: MEDIUM (planning phase)**

Path: `docs/setup-evidence/P23/research/p23-observability-dashboard-audit-research.md:145-159`

Alert conditions specified: failure rate >10%/25%, queue stuck >10 min, executor unhealthy >2 min, HARD-STOP active, consent violation, injection blocked, secret-redaction spike, cost >$25/>$30.

Ground-truth checks:
- `docs/40-operations/40-ObservabilityAlertingSpec_v1.0.md` and `41-SLO_SLA_ErrorBudget_v1.0.md` define the existing alert framework and SLO/SLA policy.
- No P23-specific alert rules exist in `monitoring/prometheus/rules/` or the repo.

**Recommendation:** At P23-018, add Prometheus alert rules under `monitoring/prometheus/rules/p23-*.yml` consistent with the existing `guinevere_` naming and routing schema.

### 2.7 Soak — deferred to P23-020

**Severity: INFO**

Path: `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:577-589`, `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:997-1007`

The 24h soak plan exists and mirrors LK-017: action queue live, HARD-STOP test, no P20 regression, no Aizanta impact, metrics green, audit hash-chain verified.

Ground-truth checks:
- (at audit time) P23-020 was explicitly held until P20 production pass and P19 definition pass. **DOC-GATE cleanup 2026-06-25:** current gate is P20 axis satisfied by operator accepted-risk waiver (fresh runtime incident preflight before LOCKED-file edits) + P19 namespace contract readiness (P19 definition complete 2026-06-25).
- No soak evidence exists yet.

## 3. Hard-Rejection Criteria Check (#8, #14)

### #8 — Secrets can enter logs/evidence/artifacts

**Status: DESIGN mitigated; NOT runtime-verified**

The plan and research specify:
- `secret_scanner` + PII redaction before audit write and artifact write (`p23-embodied-operations-enterprise-plan.md:389`, `p23-observability-dashboard-audit-research.md:70`, `p23-observability-dashboard-audit-research.md:138`).
- Dashboard sanitization via `DashboardRenderer._sanitize()` (`dashboard.py:57-69`).
- No raw secrets in artifacts/MCP/Discord (AGENTS.md §12).

However, no runtime artifact writer or audit writer exists yet, so this criterion cannot be verified at runtime. The design correctly addresses it; implementation must enforce it.

### #14 — Discord dashboard does not prove queued/running/done/failed/rollback state

**Status: DESIGN complete; NOT implemented**

The plan explicitly designs an additive `_actions_section` that proves all five required states (`p23-embodied-operations-enterprise-plan.md:468-470`, `p23-observability-dashboard-audit-research.md:38-55`). The existing `dashboard.py` and `dashboard_writer.py` provide the checksum-gated, edit-not-spam mechanism needed to render it. The section itself is not yet present in source, which is acceptable in the planning phase but must be completed before P23-017 acceptance.

## 4. Verdict

**Verdict: NEEDS-REVIEW**

**Summary:**

The P23 observability and evidence design is complete, consistent with the existing `gmail/metrics.py` Prometheus pattern, the `DashboardRenderer`/`DashboardWriter` edit-not-spam mechanism, the `LogChannel` abstraction, and the governance specs in `docs/40-operations/40-ObservabilityAlertingSpec_v1.0.md` and `41-SLO_SLA_ErrorBudget_v1.0.md`. However, no implementation exists yet; this is expected because the project is in the planning phase and P23-016/017/018 are held. The parent-authored research file (`p23-observability-dashboard-audit-research.md`) documents its provenance and contains path:line citations to the source files it references; its content is rigorous and aligned with the plan.

**Blockers before runtime acceptance:**
1. Implement `src/life_kernel/action_metrics.py` (or `src/observability/p23_metrics.py`) with the full metric set.
2. Add `_actions_section` to `src/life_kernel/dashboard.py` and the required `NotRequired` action fields to `LifeMindState`.
3. Wire `#actions-log` lifecycle event publishing in `src/life_kernel/log_channel.py`.
4. Create `audit.action_log` DDL and hash-chain writer in P23-016.
5. Implement per-action redacted artifact writer with SHA-256 hashes in P23-016.
6. Add P23 alert rules and Grafana dashboard JSON in P23-018.
7. (at audit time) Complete the P23-020 24h soak with evidence after P20 pass and P19 definition pass. **DOC-GATE cleanup 2026-06-25:** current gate is P20 axis satisfied by operator accepted-risk waiver (fresh runtime incident preflight before LOCKED-file edits) + P19 namespace contract readiness (P19 definition complete 2026-06-25). (P23-020 own 24h soak remains valid and runs after P23 implementation; the P20 axis is now satisfied by operator accepted-risk waiver.)
