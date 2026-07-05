# P19 Research: Observability, Audit & Evidence Per-Project

**Status:** ✅ COMPLETE
**Date:** 2026-06-25
**Author:** Guinevere (parent-authored from scout reports + direct reads)
**Scope:** How observability, audit, and evidence become project-aware.

---

## 1. Executive Summary

Observability and audit are **global today**: Prometheus metrics have label dimensions (event_type, category, metric_type) but no `project_id`; three audit sinks (`audit.audit_trail`, `life_kernel.audit_journal`, `memory.kg_consent_audit`) have no `project_id`. P19 adds `project_id` as a Prometheus label on relevant metrics and a `project_id` column on all audit tables (nullable for global safety events). Evidence roots stay phase-based for Guinevere-core, with per-project runtime evidence under `evidence/projects/{project_id}/`.

---

## 2. Current Prometheus Metrics

- Core: `guinevere_requests_total`, `guinevere_request_duration_seconds` (`src/core/main.py`).
- Windows: `guinevere_windows_events_received_total{event_type}` etc. (`src/observability/windows_metrics.py:50-77`).
- Wearable: `guinevere_wearable_metrics_ingested_total{metric_type}` etc. (`src/wearable/metrics.py:38-127`).
- Gmail: `gmail_emails_received_total{category, tier}` etc. (`src/gmail/metrics.py:7-76`).
- X Poster: `x_poster_posts_total{status}` etc. (`src/x_poster/metrics.py:11-101`).
- Metrics server at port 9191 (`src/core/main.py:74`).

---

## 3. Current Grafana Dashboards

`monitoring/grafana/dashboards/`: guinevere-agent-loop, guinevere-database-memory, guinevere-finops, guinevere-hermes, guinevere-infrastructure, guinevere-llm-cost-latency, guinevere-persona-safety, guinevere-x-poster, x-poster-enterprise.

Stack: Prometheus + Grafana + Loki + Promtail + Alertmanager (`monitoring/compose.monitoring.yml`, `systemd/guinevere-monitoring.service`).

---

## 4. Per-Project Metrics

Add `project_id` as a Prometheus label on metrics where relevant:
- `guinevere_memory_recall_total{project_id="work"}` 42
- `guinevere_agent_loop_total{project_id, status}`
- `guinevere_audit_events_total{project_id, event_type}`
- `guinevere_llm_cost_usd{project_id, model}`
- `guinevere_surveillance_events_total{project_id, event_type}`

Metrics that stay global (no project label):
- `guinevere_hard_stop_total` (global safety)
- `guinevere_persona_state` (global persona)
- Infrastructure metrics (node, postgres, redis — not project-scoped)

**Label cardinality:** bounded by number of active projects (small), so safe.

---

## 5. Current Audit Journal

Three sinks, all without `project_id`:
1. `src/loops/audit_writer.py:32-97` → `audit.audit_trail` (id, event_type, event_payload JSONB, principal, event_hash, previous_hash, occurred_at).
2. `src/life_kernel/domain_minds/durability.py:44-142` → `life_kernel.audit_journal` (id, source, entry JSONB, recorded_at).
3. `src/knowledge_graph/consent/audit.py:92-183` → `memory.kg_consent_audit` (id, consent_token, action, affected_entity_id, affected_edge_id, principal, occurred_at, details).

Recent commit `c29a461` fixed `PostgresAuditJournal` (multi-statement DDL split, JSON serialization, truthful logging).

---

## 6. Per-Project Audit

Every audit row includes `project_id`:
- Nullable for global events (HARD STOP, safe-word, persona safety, global consent changes).
- NOT NULL for project events (project memory write, project deploy, project consent change, project switch).

`write_event()` / `record()` signatures gain `project_id` param (default None = global).

---

## 7. Evidence Root Per-Project

- Current: `docs/setup-evidence/{P1..P22}/` (phase-based, project = guinevere core).
- Proposed: keep phase-based for Guinevere-core (phases ARE the core project's work).
- Runtime projects (work, personal, etc.) get `evidence/projects/{project_id}/` for their runtime evidence (deploy logs, audit exports, incident reports).

---

## 8. Project-Local vs Guinevere-Core Evidence

| Type | Path | Owner |
|---|---|---|
| Guinevere-core phase evidence | `docs/setup-evidence/P{N}/` | Guinevere (core project) |
| Runtime project evidence | `evidence/projects/{project_id}/` | The runtime project |
| P19 definition evidence | `docs/setup-evidence/P19/evidence/` | Guinevere (this phase) |

---

## 9. Log Channel Per-Project

(Covered in Discord UX research §9.) Top-3 projects get dedicated log channels; rest use shared `#guinevere-log` with `[project:slug]` prefix.

---

## 10. Audit Queries

- Dashboard/API: "show all audit events for project X in last 24h" → `SELECT * FROM audit.audit_trail WHERE project_id = :project_id AND occurred_at > now() - interval '24 hours'`.
- Global query: `WHERE project_id IS NULL` (safety events).

---

## 11. Hash Chain Per-Project vs Global

- **Option A: single global hash chain** (RECOMMENDED) — simpler, project_id is just a column.
- **Option B: per-project hash chain** — stronger isolation but complex (N chains to verify).
- Decision: Option A. The hash chain verifies integrity across all events; `project_id` is a filter dimension, not a chain dimension.

---

## 12. Retention Per-Project

- Different projects can have different retention policies (stored in `projects.project_registry.metadata.retention`).
- Project A: 30 days raw surveillance; Project B: 180 days.
- Retention jobs read per-project policy.

---

## 13. Alert Per-Project

- Alertmanager rules filter by `project_id` label: `alert: HighProjectErrorRate` with `expr: rate(guinevere_agent_loop_errors_total{project_id="work"}[5m]) > 0.1`.
- Global alerts (HARD STOP, persona safety) have no project filter.

---

## 14. Soak Metrics Per-Project

When P19 itself soaks (P19-012), track:
- `p19_projects_active` gauge
- `p19_memory_isolation_test_pass_total` counter
- `p19_project_switch_total` counter
- Per-project recall latency, audit write latency.

---

## 15. P20 Continuation Interaction

- P20 life_kernel metrics become project-labeled after P19 lands (P19-005/010).
- During P19 soak, P20's existing global metrics must NOT regress (additive labels only).

---

## 16. Hard Rejection: Audit Without Project ID

- Every project audit row (except global safety events) must have `project_id`.
- Test: `test_audit_project_id` — project event audit row has `project_id` set; HARD STOP audit row has `project_id IS NULL`.

---

## 17. Evidence Integrity Per-Project

- Hash-chain verification includes `project_id` in the canonical payload (so a row's project cannot be silently changed without breaking the chain).
- `event_hash = SHA256(canonical_payload_including_project_id + previous_hash)`.

---

## 18. Conclusion

P19 adds `project_id` as a Prometheus label on relevant metrics (bounded cardinality), a `project_id` column on all three audit sinks (nullable for global safety events), per-project log channels, per-project retention policies, and per-project Alertmanager rules. Evidence roots stay phase-based for Guinevere-core with per-project runtime evidence under `evidence/projects/{project_id}/`. The hash chain stays global (single chain, project_id is a column in the canonical payload).
