# P20 Daily-Life Domain Minds — Capability Audit

**Output path:** `docs/setup-evidence/P20/evidence/continuation/research/daily-life-domains-audit.md`

**Audit scope:** `src/life_kernel/`, `src/gmail/`, `src/finance/`

**Date:** 2026-06-24

**Verdict:** Three daily-life domain minds exist as real, unit-tested modules (`EmailMind`, `FinanceMind`, `EngineerMind` + `self_improve.ReflectionEvaluator`), but none are wired into the life-mind graph, sensor adapters are all placeholders, and no health/routine domain mind exists. The kernel remains a heartbeat/dashboard skeleton with isolated domain modules.

## 1. Domain Mind Inventory

| Domain | File | Status | Capability Level |
|---|---|---|---|
| Email | `src/life_kernel/domain_minds/email_mind.py` | Real, policy-gated | Classifies outgoing email as `low_risk` / `sensitive` / `dangerous`; builds a LangGraph subgraph; `send()` is a placeholder that never calls a real email API. |
| Finance | `src/life_kernel/domain_minds/finance_mind.py` | Real, read-only/record-only | Records transactions, classifies by keyword, summarizes, detects anomalies; blocks `pay`/`transfer`/`invest`/`trade`. |
| Engineering / Deploy | `src/life_kernel/domain_minds/engineer_mind.py` + `deploy_backend.py` | Real, policy-gated | Implements `backup` -> `canary` -> `smoke_test` -> `deploy`/`rollback`; intent-only/dry-run unless a real `DeployBackend` is injected. |
| Self-Improvement | `src/life_kernel/self_improve.py` | Real, heuristic-based | `ReflectionEvaluator` produces `ImprovementCandidate`s across 4 categories; `RegressionGate` can run `pytest` before promotion. |
| Health / Routine | **Missing** | Stub only (`wearable_adapter.py`) | No `HealthMind`; only a placeholder sensor adapter that returns text about heart rate/steps/sleep. |
| Learning / Research | **Missing** | No dedicated module | Only generic idle tasks (`exploration`, `learning`) and placeholder curiosity loop in `cognition.py`. |
| Communication | Partial (`email_mind`) | Same as email | No separate comms mind; Discord adapter is a placeholder sensor. |

## 2. Email Autonomy

- `src/life_kernel/domain_minds/email_mind.py` is a real module with:
  - Deterministic sensitivity classification (`low_risk`, `sensitive`, `dangerous`).
  - Dangerous-pattern blocking for secrets, tokens, CVV, payment confirmations.
  - LangGraph subgraph (`build_graph`) with `classify_node` -> `approve_node`/`send_node`.
  - Placeholder `send()` that logs intent but never calls an email provider.

- `src/gmail/` is a fully separate Gmail/Hermes integration (bridge, client, service, sync engine, classifier, draft generator). It does **not** import `src.life_kernel` and is not used by the life kernel.

- `src/life_kernel/sensor_adapters/gmail_adapter.py` is a 21-line placeholder that returns:  
  `Gmail inbox polling placeholder -- unread count and important emails are not fetched in v1...`

**Conclusion:** Email domain mind is real but isolated. The life kernel does not observe Gmail or dispatch to `EmailMind`.

## 3. Finance Autonomy

- `src/life_kernel/domain_minds/finance_mind.py` is a real module with:
  - `record_transaction`, `classify_transaction`, `summarize`, `detect_anomalies`.
  - `execute_action` dispatcher that blocks destructive actions.
  - Durability backend (`PostgresAuditJournal` / `InMemoryJournal`).

- `src/finance/hook.py` is a separate Hermes hook that listens on Discord `#finance` channel, parses messages with `FinanceParser`, and writes to its own PostgreSQL DB. It does **not** import `src.life_kernel`.

- `src/life_kernel/sensor_adapters/finance_adapter.py` is a 21-line placeholder that returns:  
  `Financial data polling placeholder -- account balances and transactions are not fetched in v1...`

**Conclusion:** Finance domain mind is real but isolated. The life kernel does not read real finance data or dispatch to `FinanceMind`.

## 4. Health / Routine Influence

- No `HealthMind` or `RoutineMind` exists in `src/life_kernel/domain_minds/`.
- The only health-related code is:
  - `src/life_kernel/sensor_adapters/wearable_adapter.py` -- placeholder returning text about heart rate/steps/sleep.
  - `expense:health` category inside `FinanceMind.CATEGORY_KEYWORDS`.
  - Health endpoints used in `EngineerMind` smoke tests (`/health`, `/health/detailed`).

**Conclusion:** Health/routine has no domain mind and therefore cannot influence life-kernel decisions.

## 5. Self-Improvement Loop (LK-015)

`src/life_kernel/self_improve.py` implements:

- `ImprovementCandidate` dataclass with lifecycle status (`proposed` -> `regression_testing` -> `promoted`/`rejected`).
- `ReflectionEvaluator.evaluate(state)` produces candidates heuristically:
  - `> 3 errors` -> planner candidate
  - high cycle count + low act count -> planner/efficiency candidate
  - idle `> 1 hour` -> skill candidate
  - observation queue near cap (`> 80`) -> skill candidate
  - fallback -> prompt candidate
- `RegressionGate` runs a configurable `pytest` command and calls `promote()` or `rollback()`.
- `ImprovementTracker` holds candidates in memory.

**Conclusion:** LK-015 does produce real candidates and has a regression gate, but it is not wired into the graph/heartbeat; descriptions are placeholders.

## 6. Engineering Deployment Autonomy (LK-014)

`src/life_kernel/domain_minds/engineer_mind.py` + `deploy_backend.py` implement:

- `DeployPolicy`: `backup_required`, `canary_required`, `smoke_required`, `rollback_enabled`, `canary_duration_s`, `health_endpoints`, `auto_deploy`.
- `EngineerMind.deploy(target)` flow:
  1. `backup(target)`
  2. `canary(target)`
  3. `smoke_test(target)`
  4. `deploy(target)` if smoke passes, else `rollback(target, backup_id)`.
- `SSHDeployBackend` provides real SSH/command paths but is **dry-run by default**; no destructive command runs unless explicitly configured.
- LangGraph subgraph in `EngineerMind.build_graph()` mirrors the same flow.

**Conclusion:** LK-014 has full backup/canary/smoke/rollback scaffolding, gated and dry-run by default.

## 7. Idle Agenda Analysis

`src/life_kernel/graph.py` `idle_node` (lines 581-701) generates self-directed tasks from:

1. Recalled P18 memory -> `memory_driven`
2. Recalled KG concept -> `concept_driven`
3. Deterministic fallback rotating by `cycle_count % 3`:
   - `self_improvement`: "review recent autonomous decisions for improvement candidates"
   - `exploration`: "survey current world-state for emerging concerns"
   - `learning`: "consolidate a learning from the last reflection cycle"

**Conclusion:** Idle agenda is generic and does **not** include daily-life tasks (email triage, finance review, health check, routine reminders). It is also not informed by real sensor data.

## 8. Brain Outputs Are Richer Than observe/reflect/idle

The valid routing decisions are `{act, reflect, idle, observe, end}` (`graph.py:25`).

Dashboard/state outputs include:

- `decision`
- `last_autonomous_decision`
- `next_planned_action`
- `current_focus`
- `last_action_result`
- `memory_status`
- `recalled_concepts` / `recalled_memories`
- `journal_entries`
- `world_model_status`

**Conclusion:** The brain/decision surface is already richer than only `observe`/`reflect`/`idle`; the gap is that domain minds are not dispatched from these decisions.

## 9. Gap Summary

| # | Gap | Severity | Notes |
|---|---|---|---|
| 1 | Domain minds are not wired into `act_node` | Critical | `act_node` only logs intent and increments counters. |
| 2 | No health/routine domain mind | High | Only wearable sensor placeholder exists. |
| 3 | Sensor adapters are all stubs | High | Gmail, finance, VPS, wearable, surveillance, browser, Discord, repo adapters return placeholder strings. |
| 4 | `src/gmail` and `src/finance` are isolated silos | Medium | They run independently and do not feed the life kernel. |
| 5 | Idle agenda is generic | Medium | No daily-life context (email/finance/health) in idle tasks. |
| 6 | Background cognition not started | Medium | `BackgroundCognition` exists but is not instantiated/started in `src/core/main.py`. |
| 7 | Self-improvement candidates are heuristic placeholders | Low | Real candidates exist, but descriptions are generic and not yet driven by Hermes. |

## 10. Recommendations for Strengthening

1. **Wire a display-only domain dispatcher** in `act_node` that routes goals with a `domain` field to `EmailMind`, `FinanceMind`, or `EngineerMind`, storing results in `last_action_result`/`next_planned_action` without side effects.
2. **Create a `HealthMind`** (even if minimal) that ingests wearable/self-reported data and sets concerns/goals for routine/health items.
3. **Implement real (but consent-gated) sensor adapters** for Gmail, finance CSV/import, and wearable data; keep them opt-in.
4. **Feed sensor observations into `idle_node`** so agenda items reference actual email/finance/health state instead of generic strings.
5. **Start `BackgroundCognition`** in `src/core/main.py` with a populated `SensorRegistry`.
6. **Connect `ReflectionEvaluator`** to the reflect/heartbeat cycle so LK-015 candidates are produced from real loop metrics.

---

*Audit completed by Guinevere -- P20 Living Autonomy Kernel continuation research.*