# P20 Continuation Research — Daily-Life Domain Minds

## Output Path

`docs/setup-evidence/P20/evidence/continuation/research/daily-life-domain-minds.md`

## 1. Executive Summary

The P20 Living Autonomy Kernel has a complete set of **domain-mind modules**
(`EngineerMind`, `EmailMind`, `FinanceMind`, `self_improve.ReflectionEvaluator`)
and a `SensorRegistry` with eight placeholder adapters, but the main
`observe→decide→act→reflect→idle` graph never calls any of them. The `act_node`
only increments counters and logs intent; the `idle_node` generates agenda
items with `random.choice()` over three hardcoded strings. No domain dispatch
exists. Real sensor adapters are stubs that return placeholder text and never
query external APIs. The result is a functional heartbeat and dashboard, but a
life-mind that is not yet "living" across daily-life domains.

This report documents the current wiring, identifies the gap, and recommends a
**display-only v1** dispatch path that routes to `EmailMind` and `FinanceMind`
for safe classify/summarize/read-only work, keeps engineering/health/surveillance
escalated, and replaces the random idle task with a memory- and
sensor-context-driven agenda suggestion.

## 2. Current State Evidence (file:line)

### 2.1 Domain minds exist but are not invoked by the graph

- `src/life_kernel/domain_minds/__init__.py:1-27` exports `EmailMind`,
  `FinanceMind`, `EngineerMind`, `DeployPolicy`, etc.
- `src/life_kernel/__init__.py:48-56` re-exports the same classes.
- `src/life_kernel/graph.py` (the life-mind StateGraph) contains **no import of**
  `domain_minds`. A grep for `domain_mind` in `src/life_kernel` only returns the
  package `__init__.py` imports, the model, and the module's own internal imports
  (`src/life_kernel/__init__.py:48`,
  `src/life_kernel/domain_minds/__init__.py:5-13`,
  `src/life_kernel/models.py:91`).
- `src/life_kernel/heartbeat.py` likewise has no domain-mind references.

### 2.2 The act node is purely intent/log only

`src/life_kernel/graph.py:256-344` (`act_node`) picks the highest-priority goal,
logs it, and returns:

```python
# src/life_kernel/graph.py:256-344
async def act_node(state: LifeMindState) -> dict[str, Any]:
    ...
    # If goals exist, identify highest-priority goal
    if goals:
        ...
        logger.info(
            "life_kernel.act",
            phase=state.get("current_phase"),
            goal_id=highest_priority_goal.get("goal_id"),
            priority=highest_priority_goal.get("priority"),
            description=highest_priority_goal.get("description"),
        )
    else:
        ...
```

No domain-specific execution occurs.

### 2.3 The idle node uses random.choice over hardcoded strings

`src/life_kernel/graph.py:435-504` (`idle_node`) includes:

```python
# src/life_kernel/graph.py:463-468
task_options = [
    ("exploration", "Exploration: review life_kernel state for patterns"),
    ("self_improvement", "Self-improvement: evaluate SDLC loop efficiency"),
    ("learning", "Learning: revisit recent observations for insights"),
]
task_type, task_description = random.choice(task_options)
```

### 2.4 Sensor adapters are all placeholder stubs

Every adapter subclasses `BaseSensorAdapter` and returns only the placeholder
content. Examples:

- `src/life_kernel/sensor_adapters/gmail_adapter.py:16-21`
  ```python
  SENSOR_NAME = "gmail"
  OBSERVATION_TYPE = "email"
  DEFAULT_CONTENT = (
      "Gmail inbox polling placeholder — unread count and important emails "
      "are not fetched in v1 (real calls require OAuth/Gmail API)."
  )
  ```
- `src/life_kernel/sensor_adapters/finance_adapter.py:16-21`
  ```python
  SENSOR_NAME = "finance"
  OBSERVATION_TYPE = "balance"
  DEFAULT_CONTENT = (
      "Financial data polling placeholder — account balances and "
      "transactions are not fetched in v1. No payment or transfer is performed."
  )
  ```
- `src/life_kernel/sensor_adapters/vps_adapter.py:16-21`
  ```python
  SENSOR_NAME = "vps"
  OBSERVATION_TYPE = "metric"
  DEFAULT_CONTENT = (
      "VPS metrics polling placeholder — CPU, memory, disk, and services "
      "are not fetched in v1 (requires SSH/monitoring credentials)."
  )
  ```

### 2.5 SensorRegistry is not wired to the running kernel

- `src/life_kernel/sensors.py:45-174` defines `SensorRegistry`, but
  `src/core/main.py:203-284` only creates the graph, heartbeat, and Discord
  publisher — it never instantiates or registers a `SensorRegistry`, nor does it
  pass one to `BackgroundCognition`.
- `src/life_kernel/cognition.py:296-319` shows that `BackgroundCognition.observer`
  will use a `SensorRegistry` if provided, otherwise it falls back to a
  placeholder observation.

### 2.6 Background cognition is not started

`src/core/main.py` starts `HeartbeatService` but does not create
`BackgroundCognition`; the six observer loops (observer, memory, critic,
curiosity, self_improvement, guardian) are not running in production.

### 2.7 Decision context is never built with real adapters

`src/life_kernel/graph.py:158-170` attempts to build `decision_context` only if
`kg_adapter` and `memory_adapter` are present in state:

```python
# src/life_kernel/graph.py:159-168
kg_adapter = state.get("kg_adapter")
memory_adapter = state.get("memory_adapter")
if kg_adapter and memory_adapter:
    ...
    decision_context = await builder.build(state)
else:
    decision_context = {"p16_available": False, "p18_available": False, ...}
```

`LifeMindState` declares `kg_adapter` and `memory_adapter` as `NotRequired[Any]`
(`src/life_kernel/state.py:207-211`), but no startup code populates them, and
`p16_adapter.py`/`p18_adapter.py` are stub adapters returning mock data.

### 2.8 Heartbeat deep-scan/reflection placeholders

- `src/life_kernel/heartbeat.py:530-549` (`_heartbeat_5m`) is labeled
  "Placeholder for future domain mind scanning."
- `src/life_kernel/heartbeat.py:551-571` (`_heartbeat_1h`) is labeled
  "Placeholder for future reflection logic."
- `src/life_kernel/heartbeat.py:373-398` (`_heartbeat_10s`) and `400-419`
  (`_heartbeat_30s`) are also stubs.

## 3. Gap Table

| id | severity | title | current_state | required_state | files | vision-ref |
|---|---|---|---|---|---|---|
| gap-domain-dispatch-missing | critical | Domain minds are not invoked by the life-mind graph | `act_node` only logs intent; no routing to `EmailMind`, `FinanceMind`, `EngineerMind`, etc. | Add a dispatch step (or extend `act_node`) that routes to the correct domain mind based on `current_focus`/goal domain. | `src/life_kernel/graph.py`, `src/life_kernel/domain_minds/*.py` | V-005, AC-LIFE-002 |
| gap-idle-no-sensor-context | high | `idle_node` generates tasks via `random.choice()` | `random.choice` over 3 hardcoded strings with no world context. | `idle_node` (or `brain_idle`) consults recent sensor observations + memory/KG summary to propose a context-driven agenda item. | `src/life_kernel/graph.py:435-504` | V-005, AC-LIFE-002 |
| gap-sensors-not-registered | high | `SensorRegistry` is created but never populated or started | `SensorRegistry` exists, but no startup code registers adapters or passes the registry to `BackgroundCognition`. | Register adapters at startup and inject the registry into `BackgroundCognition`; wire `sense_all()` results into graph observations. | `src/core/main.py`, `src/life_kernel/cognition.py`, `src/life_kernel/sensors.py` | V-002, V-005 |
| gap-sensors-are-stubs | medium | All daily-life sensor adapters are placeholders | Adapters return only a placeholder string; no external API is called. | Incrementally implement real (but read-only / safe) adapters behind feature flags, starting with repo + finance CSV import + Gmail OAuth. | `src/life_kernel/sensor_adapters/*.py` | V-005 |
| kg-memory-stubs | medium | Decision context is built from stub adapters | `p16_adapter.py` and `p18_adapter.py` return mock data; adapters are never injected into state. | Inject real `KGRecallAdapter` and `MemoryRecallAdapter` (or their real backends) into `LifeMindState` so `DecisionContextBuilder` enriches decisions. | `src/life_kernel/p16_adapter.py`, `src/life_kernel/p18_adapter.py`, `src/core/main.py`, `src/life_kernel/decision_context.py` | V-005, AC-LIFE-005 |
| gap-heartbeat-scans-stubs | medium | 10s/30s/5m/1h heartbeat handlers are placeholders | `_heartbeat_10s`, `_heartbeat_30s`, `_heartbeat_5m`, `_heartbeat_1h` only log. | Implement stuck-detection, sensor refresh, domain-mind health scan, and reflection/memory consolidation. | `src/life_kernel/heartbeat.py` | V-005, AC-LIFE-009 |
| gap-current-focus-unused | low | `current_focus` state field is declared but unused | `LifeMindState.current_focus` exists; dashboard renders it as "—". | The brain/dispatch sets `current_focus` to a domain (email/finance/engineering/health/etc.) and the dashboard displays it. | `src/life_kernel/state.py:148-153`, `src/life_kernel/graph.py`, `src/life_kernel/dashboard.py:321-324` | V-005 |

## 4. Risks

| risk | mitigation |
|---|---|
| Wiring domain minds directly into `act_node` could allow unsupervised side effects (email send, deploy, payment). | Implement a **display-only v1** dispatch: domain minds only classify/summarize/record; any outbound action sets `next_planned_action` and `last_action_result` for dashboard/log only. |
| `EngineerMind` / `SSHDeployBackend` have a real backend path that can run `ssh`/`systemctl` when `dry_run=False` and `enabled=True`. | Keep `dry_run=True` as the only production-allowed mode; gate real backend instantiation behind operator approval and explicit env flag; never auto-promote without human review. |
| `FinanceMind` records to `PostgresAuditJournal` in production mode by default, which could write financial data without clear consent boundary. | Keep v1 finance actions read-only (`summarize`, `detect_anomalies`, `record` from operator-supplied observations only); require explicit consent flag to enable production durability. |
| Enabling real sensor adapters (Gmail, finance, wearable, surveillance) risks privacy and secret exposure. | Each adapter must remain opt-in, consent-gated, and redacted by `DashboardRenderer._sanitize()`; no credentials in state or logs. |
| Random idle tasks waste cycles and make the kernel appear alive without real autonomy. | Replace `random.choice` with sensor + memory + KG driven agenda generation, still display-only. |

## 5. Hard-Rejection Flags

None of the existing code violates the hard-rejection rules, but the following
would be hard-rejection material if implemented carelessly:

- Any code path that calls `raw LLMRouter.chat` as the brain path. Current code
  correctly uses `HermesBrain.think()` (`src/life_kernel/graph.py:84`,
  `src/life_kernel/hermes_brain.py:258-343`).
- Any proposal to bypass the non-LLM HARD STOP. Current code preserves this in
  `decide_node` (`src/life_kernel/graph.py:211-213`) and the 1s heartbeat
  (`src/life_kernel/heartbeat.py:254-358`).
- Any use of the term "pulse" instead of "heartbeat". Current code uses
  "heartbeat" consistently.
- No secrets are present in the reviewed source.

## 6. Concrete Recommendation for Implementation Phase

### 6.1 Safe v1 dispatch design

Introduce a `DomainMindDispatcher` (new module under
`src/life_kernel/domain_dispatch.py`) that maps a goal's `domain` field to a
domain-mind instance:

```python
DOMAIN_MINDS = {
    "email": EmailMind,
    "finance": FinanceMind,
    "engineering": EngineerMind,
}
```

In `act_node`, when a goal has a `domain` field, call
`await dispatcher.dispatch(state, goal)`. The dispatcher returns a dict with:

```python
{
    "last_action_result": "display-only summary",
    "next_planned_action": "proposed next step",
    "current_focus": goal["domain"],
}
```

No side effects are executed; results are stored in state for the dashboard and
log channel.

### 6.2 Display-only domain classification

For v1, the only "safe to wire" domain minds are:

- `EmailMind`: classify/summarize; never call the placeholder `send()` without
  operator review.
- `FinanceMind`: `record` (from operator-supplied or CSV-imported observations),
  `summarize`, `detect_anomalies`; block `pay`/`transfer`/`invest`/`trade`.
- `EngineerMind`: keep in dry-run/policy-review mode only; any real backend call
  must be escalated.

Health, wearable, surveillance, browser, and Discord sensors remain **escalated**
until explicit consent and real adapters are implemented.

### 6.3 Sensor-driven idle agenda

Replace the `random.choice` in `idle_node` with a helper that:

1. Reads the most recent 10 observations from `state["observations"]`.
2. Checks for any `sensor:*` observations produced by `SensorRegistry`.
3. Falls back to `DecisionContextBuilder` (`kg_adapter`/`memory_adapter`) to
   enrich context.
4. Builds a prompt for `HermesBrain.think()`:
   "Given these recent observations and memory summary, propose one
   display-only self-directed agenda item."
5. Stores the result in `next_planned_action` and the observation's
   `description`.

Because adapters are still placeholders, the agenda item will reference the
placeholder content; this is acceptable for v1 and proves the wiring.

### 6.4 Startup wiring

In `src/core/main.py`, after creating the `SensorRegistry`, register the
placeholder adapters and pass the registry to `BackgroundCognition`:

```python
from src.life_kernel import SensorRegistry, GmailSensorAdapter, FinanceSensorAdapter, RepoSensorAdapter

sensor_registry = SensorRegistry()
await sensor_registry.register("gmail", GmailSensorAdapter())
await sensor_registry.register("finance", FinanceSensorAdapter())
await sensor_registry.register("repo", RepoSensorAdapter())
# ... etc.
```

Then start `BackgroundCognition` with the registry. This is the minimal next
step to make the kernel actually observe daily-life signals rather than just
heartbeat placeholders.

## 7. Conclusion

The domain-mind building blocks (`EngineerMind`, `EmailMind`, `FinanceMind`,
`SensorRegistry`, placeholder adapters) are implemented and unit-tested, but
life-mind graph integration is missing. The kernel is currently a heartbeat +
dashboard skeleton with isolated domain modules. The recommended continuation is
a **display-only v1 dispatch + sensor-driven idle agenda**, keeping all side
effects (email send, deploy, payments, surveillance) gated or escalated, while
still satisfying V-005's requirement that Guinevere act over daily-life domains
in a visible, auditable way.
