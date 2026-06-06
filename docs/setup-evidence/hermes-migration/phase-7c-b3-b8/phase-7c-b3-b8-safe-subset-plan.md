# Phase 7c B3+B8 Safe-Subset Plan

Status: PLANNED — safe subset only  
Date: 2026-06-06  
Scope: B3 deprecated archive readiness + B8 local runtime metrics instrumentation  
Final Phase 7 status: BLOCKED  
ADR-035 status: NOT IMPLEMENTED

## 1. Executive Gate

Research and Oracle both reject a full B3+B8 completion claim in this session.

Oracle verdict: **PROCEED SAFE SUBSET**.

- B3 archive is blocked. Do not `git mv` any deprecated file until a per-file scan proves zero live production imports and zero test dependencies, then tests pass before and after each archive step.
- B8 local instrumentation is allowed only when each metric is emitted from the process or hook that owns the event. Do not emit `hermes_gateway_up` from the core/FastAPI 9191 metrics server because that would falsely represent the Hermes Agent gateway.
- VPS deploy/restart is blocked for this safe subset. Local config/dashboard/test evidence is allowed.

## 2. Research Inputs

| Path | Key conclusion |
|---|---|
| `research-reports/phase-7c-b3-b8/01-remaining-imports.md` | Archive remains blocked by active production imports and test dependencies. |
| `research-reports/phase-7c-b3-b8/02-test-deprecated-imports.md` | Five test files still depend on deprecated files; one stale command-count test is already wrong. |
| `research-reports/phase-7c-b3-b8/03-metrics-gaps.md` | Safety plugin has no Prometheus metrics; requested B8 metrics are not emitted. |
| `research-reports/phase-7c-b3-b8/04-grafana-gaps.md` | Existing dashboard has placeholders; 9191 scrape semantics are not actual gateway semantics. |
| Oracle `bg_9491aa24` | Proceed safe subset; B3 full archive blocked; B8 local instrumentation only. |

## 3. Binding Decisions

1. **No deprecated archive in this batch** unless a later step proves a micro-subset has no live imports and no tests. Current safe subset treats archive as blocked and creates readiness evidence.
2. **No Phase 7 completion claim.** ADR-035 stays NOT IMPLEMENTED.
3. **No VPS deployment/restart in this batch.** B8 instrumentation is local-only and dashboard/config-only.
4. **No `hermes_gateway_up` emitted from core/FastAPI metrics.** The metric remains blocked until the real Hermes Agent gateway exposes a scrape target or equivalent process-owned signal.
5. **Metrics added now must be process-correct:** safety block counters live in `src/hermes/safety_plugin.py` through shared metric observers; session/message counters can be observed by Hermes hooks only when those hooks run in the Hermes gateway process.
6. **No `Any`, type suppressions, or empty catches introduced.** Existing debt in untouched files is not in scope, but touched code must not add forbidden patterns.

## 4. Master Todo and Dependency Map

| Step | Description | Parallelism | Depends on |
|---|---|---|---|
| B3-R | Create per-file archive readiness evidence and keep archive blocked honestly | Parallel | Planner |
| B8-M | Add local process-correct metrics definitions and safety plugin wiring | Parallel | Planner |
| B8-D | Update dashboard/rules to use real local metrics and mark blocked gateway metric honestly | Sequential | B8-M |
| VERIFY | Parent verification for B3/B8 safe subset | Sequential | B3-R, B8-M, B8-D |
| AUDIT | Three auditors: Archive Integrity, Metrics Completeness, Integration | Parallel | VERIFY |
| REPORT | Final report and optional commit decision | Sequential | AUDIT |

## 5. Collision Scan

| File or surface | Owner | Collision mitigation |
|---|---|---|
| `src/core/services/llm_metrics.py` | B8-M | Single writer for metric definitions and observer helpers. |
| `src/hermes/safety_plugin.py` | B8-M | Single writer for safety block/session/message observer calls. |
| `tests/hermes/test_llm_metrics.py` | B8-M | Add tests for new metric families/observers. |
| `tests/hermes/test_safety_plugin.py` | B8-M | Add tests proving safety block/session/message observers are called. |
| `monitoring/prometheus/rules/guinevere-alerts.yml` | B8-D | Single writer for alert expression cleanup if needed. |
| `monitoring/grafana/dashboards/guinevere-hermes.json` | B8-D | Single writer for panel updates. |
| `docs/setup-evidence/hermes-migration/phase-7c-b3-b8/` | Parent | Parent owns plan, verification, completion, and audit outputs. |
| `src/_deprecated/` | No owner | No archive/move in safe subset unless planner is amended after proof. |
| VPS services | No owner | No deploy/restart in safe subset. |

## 6. Step B3-R Scaffold — Archive Readiness Evidence

### Task

Create file-based evidence that the deprecated archive remains blocked and list exact preconditions for future archive.

### Expected Files

- `docs/setup-evidence/hermes-migration/phase-7c-b3-b8/STEP-B3-READINESS/verification.md`
- Optional supporting scan output under the same directory.

### Must Do

- Summarize all 10 deprecated target files.
- Mark each file as one of: blocked by production imports, blocked by tests, blocked by inter-deprecated dependency, or candidate only if proven clean.
- Explicitly state that no `git mv` archive was performed.
- Include the current blockers from `01-remaining-imports.md` and `02-test-deprecated-imports.md`.
- Include future acceptance criteria for archive: zero production imports, zero test imports or migrated tests, tests pass before and after, archive via `git mv`, README added.

### Must Not Do

- Do not move/archive/delete deprecated files.
- Do not claim B3 complete.
- Do not claim Phase 7 complete or ADR-035 implemented.

### Forbidden Patterns

- `B3 complete`
- `deprecated archive complete`
- `ADR-035 IMPLEMENTED`
- `Phase 7 complete`

These are allowed only in explicit negated/blocker context.

### Required Commands

- `grep -R "src.hermes.memory_bridge\|src.hermes.session_adapter\|from \.commands\|from \. _embed_helpers" src tests` adapted as needed for Windows/direct tools or equivalent reports.
- `python -m pytest tests/phase7/ -q --tb=short` → exit 0.
- `python -m pytest tests/discord/test_cmd_mood.py -q --tb=short` → exit 0.

### Evidence Requirements

- `STEP-B3-READINESS/verification.md` includes command outputs, blocker table, and future archive gates.

### Hard Rejection Criteria

- Any deprecated file is archived in this step.
- Evidence hides active imports or test dependencies.
- Evidence claims B3/Phase 7 is complete.

## 7. Step B8-M Scaffold — Process-Correct Metrics

### Task

Add local Prometheus metrics definitions and observer helpers, then wire safety/session/message observations through Hermes safety plugin hooks without falsely claiming real gateway process liveness.

### Expected Files

- `src/core/services/llm_metrics.py`
- `src/hermes/safety_plugin.py`
- `tests/hermes/test_llm_metrics.py`
- `tests/hermes/test_safety_plugin.py`
- `docs/setup-evidence/hermes-migration/phase-7c-b3-b8/STEP-B8-METRICS/verification.md`

### Metrics Allowed Now

- `hermes_safety_blocks_total{gate, reason}`
- `hermes_session_count` or equivalent gauge set from `on_session_start`
- `hermes_message_count_total{direction}` observed from hook activity

### Metrics Blocked Now

- `hermes_gateway_up` must not be emitted from the core/FastAPI 9191 process. It can appear in evidence as blocked until the real Hermes gateway exposes metrics.

### Must Do

- Add metric definitions with low-cardinality labels only.
- Add observer helpers for safety block, session count, and message count.
- Call observers at actual safety block points: hard_stop exact/semantic/handler, D3+ distress block, yandere safety violation, auth forbidden/destructive/unknown, forbidden critical output block.
- Count user/assistant/tool hook activity as message events only if semantically defensible.
- Add tests proving metric families exist and observer calls increment.
- Add tests proving safety plugin invokes observers for at least hard_stop, forbidden critical, and auth block.

### Must Not Do

- Do not emit `hermes_gateway_up` from `llm_metrics.py` or core/FastAPI.
- Do not introduce `Any`, type suppressions, or empty catches in touched code.
- Do not restart or deploy services.
- Do not change Aizanta.

### Forbidden Patterns in Touched Code

- `# type: ignore`
- `@ts-ignore`
- `@ts-expect-error`
- `as any`
- `except:`
- `except Exception` newly introduced
- `\bAny\b` newly introduced
- `hermes_gateway_up` definition in `src/core/services/llm_metrics.py`

### Required Commands

- `lsp_diagnostics` on changed Python files → no new errors.
- `python -m pytest tests/hermes/test_llm_metrics.py -q --tb=short` → exit 0.
- `python -m pytest tests/hermes/test_safety_plugin.py -q --tb=short` → exit 0.
- `python -m pytest tests/phase7/ -q --tb=short` → exit 0.
- Strict grep on touched files for forbidden patterns → no new matches.

### Evidence Requirements

- `STEP-B8-METRICS/verification.md` includes metric names, ownership rationale, command outputs, and explicit `hermes_gateway_up` blocked note.

### Hard Rejection Criteria

- `hermes_gateway_up` is emitted from the wrong process.
- Metrics use high-cardinality labels such as raw session id.
- Safety plugin tests fail.
- Any new type-safety suppression or empty catch is introduced.

## 8. Step B8-D Scaffold — Dashboard and Alert Cleanup

### Task

Update local Grafana/Prometheus config to use real local metrics where available and mark blocked gateway liveness semantics honestly.

### Expected Files

- `monitoring/grafana/dashboards/guinevere-hermes.json`
- `monitoring/prometheus/rules/guinevere-alerts.yml`
- `docs/setup-evidence/hermes-migration/phase-7c-b3-b8/STEP-B8-METRICS/verification.md` updated with config checks.

### Must Do

- Update safety blocks panel to use `hermes_safety_blocks_total` without hiding it as permanently pending.
- Add or update session/message panels for `hermes_session_count` and `hermes_message_count_total` if metrics are implemented.
- Keep gateway liveness panel honest: either continue using `up{job="hermes"}` with a note that it is metrics endpoint liveness, or mark real `hermes_gateway_up` blocked.
- Validate dashboard JSON parses.
- Validate alert YAML parses.

### Must Not Do

- Do not deploy/restart Prometheus, Grafana, or Hermes gateway.
- Do not claim live scrape verification unless performed safely and documented.

### Required Commands

- `python -c "import json; json.load(open('monitoring/grafana/dashboards/guinevere-hermes.json'))"` → exit 0.
- YAML parse for `monitoring/prometheus/rules/guinevere-alerts.yml` → exit 0.
- Grep checks for `hermes_safety_blocks_total`, `hermes_session_count`, `hermes_message_count_total` in dashboard/rules as appropriate.

## 9. Auditor Matrix

| Auditor | Report path | Scope | PASS Criteria |
|---|---|---|---|
| Archive Integrity | `docs/setup-evidence/hermes-migration/phase-7c-b3-b8/AUDIT-archive-integrity.md` | B3 readiness and no archive | No files moved, blockers honest, future gates explicit. |
| Metrics Completeness | `docs/setup-evidence/hermes-migration/phase-7c-b3-b8/AUDIT-metrics-completeness.md` | Metric definitions, tests, dashboard | Metrics implemented where safe; `gateway_up` not falsely emitted; tests pass. |
| Integration | `docs/setup-evidence/hermes-migration/phase-7c-b3-b8/AUDIT-integration.md` | Combined B3+B8 boundary and evidence | No false Phase 7 completion, no service disruption, evidence complete. |

## 10. Rollback Plan

- For local code/config changes: revert edited files from git if verification fails.
- For metrics definitions: remove new metric definitions and observer calls together to avoid orphan references.
- For dashboard/rules: restore previous dashboard/rules from git.
- No VPS changes should occur in this safe subset, so no service rollback is expected.

## 11. Execution Checklist

- [ ] B3 readiness evidence created and parent-read.
- [ ] B8 metrics implemented only where process-correct.
- [ ] `hermes_gateway_up` not emitted from core/FastAPI.
- [ ] Dashboard/rules parse cleanly.
- [ ] Python diagnostics have no new errors.
- [ ] Targeted tests pass.
- [ ] Phase 7 tests pass.
- [ ] Three auditors PASS.
- [ ] Final report says Phase 7 complete: NO unless all Phase 7 gates actually pass.

## 12. Footer

This plan intentionally narrows the user-requested B3+B8 work to the subset allowed by research and Oracle. Full deprecated archive, VPS deploy/restart, and final ADR-035 implementation remain blocked until their gates are independently satisfied.
