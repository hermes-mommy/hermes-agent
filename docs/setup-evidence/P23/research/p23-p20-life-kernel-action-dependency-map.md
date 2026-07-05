# P23 Research — P20 Life-Kernel Action Dependency Map

> Status: RESEARCH. Date: 2026-06-25. Author: Guinevere research subagent.
>
> This is a READ-ONLY research artifact. No runtime code was written, no deploy was triggered, no secrets were touched.

---

## 1. Objective

P23 ("Embodied Operations / Personal OS Action Layer") gives Guinevere autonomous, auditable, policy-gated "hands and feet" across browser, Windows desktop, VPS, GitHub/CLI, file system, mobile, and external integrations. This map identifies every P20 life-kernel surface that P23 must integrate with, the exact call contract, whether the surface is additive or locked, and the risks of each integration point.

P23 MUST use the life kernel as its brain, NOT raw LLMRouter.chat. HermesBrain (src/life_kernel/hermes_brain.py) wraps AIAgent; think(user_message, system_prompt, conversation_history, tools)/think_with_tools() are the entry points. enabled_toolsets=["core","web"], disabled_toolsets=["dangerous","system"].

---

## 2. Sources Consulted (src/life_kernel/* with path:line)

| File | Lines Read | Role in P20 |
|---|---|---|
| src/life_kernel/hermes_brain.py | 1-464 | Brain wrapper: think()/think_with_tools() |
| src/life_kernel/heartbeat.py | 1-684 | 6-interval heartbeat, HARD STOP at L1S |
| src/life_kernel/graph.py | 1-1042 | StateGraph: observe/decide/act/reflect/idle nodes |
| src/life_kernel/state.py | 1-309 | LifeMindState TypedDict |
| src/life_kernel/decision_context.py | 1-100 | DecisionContextBuilder |
| src/life_kernel/dashboard.py | 1-387 | DashboardRenderer |
| src/life_kernel/dashboard_writer.py | 1-219 | DashboardWriter, publish_hard_stop |
| src/life_kernel/journal.py | 1-67 | JournalWriter |
| src/life_kernel/self_improve.py | 1-416 | ReflectionEvaluator, RegressionGate, ImprovementTracker |
| src/life_kernel/sensor_adapters/base.py | 1-84 | BaseSensorAdapter (READ-ONLY) |
| src/life_kernel/sensors.py | 1-174 | SensorRegistry |
| src/life_kernel/cognition.py | 1-406 | BackgroundCognition (6 observer loops) |
| src/life_kernel/p16_adapter.py | 1-111 | KGRecallAdapter |
| src/life_kernel/p18_adapter.py | 1-102 | MemoryRecallAdapter |
| src/life_kernel/log_channel.py | 1-150 | DiscordLogChannel, StructlogLogChannel |
| src/life_kernel/domain_minds/deploy_backend.py | 1-354 | SSHDeployBackend (VPS executor) |
| src/life_kernel/domain_minds/engineer_mind.py | 1-469 | EngineerMind (GitHub/deploy orchestrator) |
| src/life_kernel/domain_minds/email_mind.py | 1-335 | EmailMind (email risk classifier + subgraph) |
| src/life_kernel/domain_minds/finance_mind.py | 1-536 | FinanceMind (finance observer + execute_action) |
| src/life_kernel/domain_minds/durability.py | 1-244 | DurabilityBackend, PostgresAuditJournal |
| src/life_kernel/__init__.py | 1-127 | Public API exports |
| AGENTS.md | 1-300 | §0.1 Autonomy-First Governance Exception |

---

## 3. Findings

### 3.1 ASCII Dependency Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        P20 LIFE KERNEL (LOCKED)                     │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐           │
│  │  heartbeat.py│───▶│  graph.py    │───▶│ hermes_brain │           │
│  │  (6 intervals)│    │ (StateGraph) │    │ (AIAgent)    │           │
│  │  L1S:HARD STOP│    │              │    │ think()      │           │
│  └──────┬───────┘    └──────┬───────┘    └──────────────┘           │
│         │                   │                                        │
│         │ Redis             │ _ADAPTERS registry                     │
│         │ "life_kernel:     │ (kg, memory, journal)                  │
│         │  hard_stop"       │                                        │
│         ▼                   ▼                                        │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐           │
│  │ dashboard_   │    │ journal.py   │    │self_improve  │           │
│  │ writer.py    │    │ (audit)      │    │.py (reflect) │           │
│  └──────────────┘    └──────────────┘    └──────────────┘           │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              DOMAIN MINDS (write-side executors)             │   │
│  │  engineer_mind → deploy_backend (VPS SSH)                    │   │
│  │  email_mind → classify → send (email)                        │   │
│  │  finance_mind → execute_action (finance record)              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │           SENSOR ADAPTERS (read-side, READ-ONLY)             │   │
│  │  BaseSensorAdapter → Browser/Discord/Finance/Gmail/Repo/     │   │
│  │                      VPS/Wearable/Surveillance               │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              ▲
                              │ P23 MUST integrate here
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     P23 ACTION LAYER (ADDITIVE)                     │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐           │
│  │ActionPlanner │───▶│ExecutorBase  │───▶│ CancelCB     │           │
│  │(calls brain) │    │(NEW abstract)│    │(HARD STOP)   │           │
│  └──────────────┘    └──────┬───────┘    └──────────────┘           │
│                              │                                       │
│  ┌──────────────┐    ┌──────┴───────┐    ┌──────────────┐           │
│  │ActionQueue   │    │Domain        │    │ActionAudit   │           │
│  │(Redis-backed)│    │Executors     │    │(journal write)│          │
│  └──────────────┘    │(browser/     │    └──────────────┘           │
│                      │ desktop/     │                               │
│                      │ VPS/GitHub/  │                               │
│                      │ file/mobile) │                               │
│                      └──────────────┘                               │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 HermesBrain Call Contract

P23 action planner/executor calls HermesBrain for four decision types. The brain is the ONLY LLM entry point — raw LLMRouter.chat is forbidden.

#### 3.2.1 Action Selection

```python
# P23 action planner asks the brain to choose the next action
result = await hermes_brain.think(
    user_message="Given goals: [...], commitments: [...], concerns: [...], "
                 "observations: [...], select the highest-priority executable action.",
    system_prompt="You are Guinevere's action planner. Select ONE concrete action "
                  "from the available executor capabilities. Return JSON: "
                  "{action: '...', executor: '...', params: {...}, priority: '...'}",
    conversation_history=[...],
)
# result = {
#     "final_response": str,
#     "input_tokens": int,
#     "output_tokens": int,
#     "total_tokens": int,
#     "model": str,
#     "estimated_cost_usd": float,
# }
```

**Source:** hermes_brain.py:258-343. `think()` calls `asyncio.to_thread(self.agent.run_conversation, ...)` with a hard timeout. Returns fallback dict on failure (hermes_brain.py:345-370).

#### 3.2.2 Scheduling Decisions

```python
# P23 asks the brain to schedule actions across executors
result = await hermes_brain.think_with_tools(
    user_message="Schedule these actions: [...] across executors: [...]. "
                 "Consider dependencies, risk levels, and current load.",
    system_prompt="You are Guinevere's action scheduler. Produce a schedule "
                  "that respects policy gates and HARD STOP.",
    tools=[schedule_tool, check_health_tool],
    conversation_history=[...],
)
```

**Source:** hermes_brain.py:372-452. `think_with_tools()` passes tools to the agent for tool-augmented reasoning.

#### 3.2.3 Self-Debug on Failure

```python
# When an executor fails, P23 asks the brain to diagnose
result = await hermes_brain.think(
    user_message=f"Action '{action_id}' failed: {error_dict}. "
                 f"Executor state: {executor_state}. "
                 "Diagnose the failure and propose retry or rollback.",
    system_prompt="You are Guinevere's self-debug engine. Analyze the failure "
                  "and decide: retry, rollback, or escalate to Faiz.",
    conversation_history=[...],
)
```

#### 3.2.4 Rollback Decisions

```python
# P23 asks the brain whether to rollback a failed action
result = await hermes_brain.think(
    user_message=f"Action '{action_id}' produced unexpected state: {state_diff}. "
                 f"Backup available: {backup_id}. Rollback?",
    system_prompt="You are Guinevere's rollback decision engine. "
                  "If state is corrupted or policy violated, rollback. "
                  "If transient, retry with backoff.",
    conversation_history=[...],
)
```

### 3.3 Heartbeat Integration

#### 3.3.1 The 6-Interval Schedule (LOCKED — P23 MUST NOT alter)

| Interval | Duration | Purpose | Source |
|---|---|---|---|
| L1S | 1s | Liveness + HARD STOP detection | heartbeat.py:254-358 |
| L10S | 10s | Graph health check (stuck detection) | heartbeat.py:373-398 |
| L30S | 30s | Awareness refresh (sensor polling) | heartbeat.py:400-419 |
| L60S | 60s | Decision heartbeat (graph.ainvoke + dashboard) | heartbeat.py:421-516 |
| L5M | 5m | Deep scan (domain mind states, anomaly) | heartbeat.py:569-588 |
| L1H | 1h | Reflection + memory consolidation + self-improvement | heartbeat.py:590-673 |

**Why P23 must NOT alter the 6-interval schedule:**
1. The 1s HARD STOP poll (heartbeat.py:273) is the canonical safety mechanism. Any change to its timing violates V-008 ("HARD STOP remains the global action halt").
2. The 60s decision heartbeat (heartbeat.py:462) is the only place graph.ainvoke is called — adding another invocation point risks concurrent state corruption.
3. The 1h reflection heartbeat (heartbeat.py:641) is where ReflectionEvaluator runs — P23 action outcomes feed here but must not change the schedule.
4. P20 non-interference: heartbeat.py is a LOCKED file. P23 changes are ADDITIVE only.

#### 3.3.2 Where P23 Integrates (ADDITIVE)

P23 does NOT add new heartbeat intervals. Instead:
- **Action queue polling**: P23's ActionPlanner runs as a separate asyncio task (not a heartbeat loop). It polls its own Redis queue at a configurable interval (default 10s).
- **Executor health**: P23 executors expose a `health()` method callable from the existing L5M deep scan (heartbeat.py:569) — P23 registers executors with a P23 ExecutorRegistry that the L5M handler can query.
- **Dashboard rendering**: P23 action state (queued/running/done/failed/rollback) is rendered in a NEW section of the dashboard — additive to DashboardRenderer (dashboard.py).

### 3.4 HARD STOP Propagation

#### 3.4.1 Redis Key and Detection

```
Redis key: "life_kernel:hard_stop"
Detection: heartbeat.py:273 — _heartbeat_1s() polls every 1s
```

**Source:** heartbeat.py:273-282:
```python
hard_stop_key = "life_kernel:hard_stop"
try:
    hard_stop_value = await self.redis_client.get(hard_stop_key)
except Exception as redis_err:
    # Fail-closed: Redis unreachable = assume flag present
    logger.error("hard_stop_redis_unreachable", ...)
    return
live_hard_stop = bool(hard_stop_value)
```

#### 3.4.2 How P23 Executors Check HARD STOP

P23 executors MUST check HARD STOP at two points:

**Pre-action check (before any side effect):**
```python
class P23ExecutorBase:
    async def _check_hard_stop(self) -> bool:
        """Return True if HARD STOP is active. Fail-closed on Redis error."""
        try:
            value = await self._redis_client.get("life_kernel:hard_stop")
            return bool(value)
        except Exception:
            return True  # fail-closed

    async def execute(self, action: Action) -> ActionResult:
        if await self._check_hard_stop():
            return ActionResult(status="cancelled", reason="HARD STOP active")
        # ... proceed with action
```

**Mid-action check (for long-running actions):**
```python
    async def execute(self, action: Action) -> ActionResult:
        # ... start action
        while not action.done():
            if await self._check_hard_stop():
                await self._cancel_callback(action)
                return ActionResult(status="cancelled", reason="HARD STOP mid-action")
            await asyncio.sleep(0.5)
```

#### 3.4.3 Cancel Callback Registration

P23 executors register a cancel callback with the ActionPlanner:

```python
class ActionPlanner:
    def __init__(self):
        self._running_actions: dict[str, CancelCallback] = {}

    async def on_hard_stop(self):
        """Called by P23's HARD STOP watcher when flag detected."""
        for action_id, cancel_cb in self._running_actions.items():
            try:
                await cancel_cb(action_id)
            except Exception as e:
                logger.error("cancel_callback_failed", action_id=action_id, error=str(e))
        self._running_actions.clear()
        self._action_queue.clear()  # Cancel queued actions too
```

**HARD STOP cancels both queued AND running actions.** The queue is cleared (no new actions dequeue) and running actions receive cancel callbacks.

#### 3.4.4 HARD STOP Propagation Chain

```
Redis "life_kernel:hard_stop" = "1"
    │
    ├──▶ heartbeat.py:_heartbeat_1s() detects (line 273)
    │       ├── Sets hard_stop_requested=True in graph state (line 299-305)
    │       ├── Publishes HARD STOP to dashboard (line 313-320)
    │       ├── Writes lifecycle log (line 318)
    │       └── Calls heartbeat.stop() (line 322) — stops all 6 intervals
    │
    ├──▶ P23 HARD STOP watcher (NEW, separate asyncio task)
    │       ├── Polls same Redis key every 1s
    │       ├── Calls ActionPlanner.on_hard_stop()
    │       │       ├── Cancels all queued actions
    │       │       └── Calls cancel callbacks on running actions
    │       └── Writes HARD STOP audit entry to journal
    │
    └──▶ graph.py:decide_node() routes to END (line 318-320)
            └── graph.py:reflect_node() sets decision="end" (line 557-559)
```

### 3.5 Domain Mind → Executor Ownership Map

| Domain Mind | P20 File | Executor Domain | P23 Executor Class |
|---|---|---|---|
| EngineerMind | domain_minds/engineer_mind.py:69-469 | VPS deploy (SSH), GitHub ops, file ops | P23VPSExecutor, P23GitHubExecutor, P23FileExecutor |
| EmailMind | domain_minds/email_mind.py:80-335 | Email send (risk-classified) | P23EmailExecutor (wraps EmailMind.send_node) |
| FinanceMind | domain_minds/finance_mind.py:479-536 | Finance record/summarize/anomaly | P23FinanceExecutor (wraps FinanceMind.execute_action) |
| DeployBackend | domain_minds/deploy_backend.py:56-354 | VPS SSH/scp/systemd | P23VPSExecutor (wraps SSHDeployBackend) |

**Ownership rules:**
- EngineerMind owns deploy policy gates (backup→canary→smoke→rollback). P23 VPS executor delegates to EngineerMind.deploy() for policy compliance.
- EmailMind owns risk classification (low_risk→auto, sensitive→approval, dangerous→blocked). P23 email executor calls EmailMind.classify_sensitivity() before any send.
- FinanceMind blocks destructive actions (pay/transfer/withdraw/invest/trade — finance_mind.py:47-49). P23 finance executor respects BLOCKED_FINANCE_ACTIONS.
- DeployBackend provides the SSH abstraction. P23 VPS executor uses SSHDeployBackend as its transport layer.

### 3.6 World Model / Decision Context / Graph / Journal

#### 3.6.1 Where Action Outcomes Get Recorded

| Recording Surface | P20 File:Line | What P23 Writes |
|---|---|---|
| graph.py:observe_node | graph.py:137-279 | P23 action outcomes as observations (via BackgroundCognition._write_to_graph) |
| graph.py:reflect_node | graph.py:458-586 | P23 action audit entries via JournalWriter.write_entry() |
| journal.py:write_entry | journal.py:27-66 | P23 action reasoning + lessons learned + confidence |
| self_improve.py:evaluate | self_improve.py:128-165 | P23 action outcomes feed ReflectionEvaluator metrics |
| PostgresAuditJournal | domain_minds/durability.py:44-202 | P23 action records persisted to PostgreSQL |

#### 3.6.2 Decision Context (P16/P18 Role)

P23 action planner uses DecisionContextBuilder (decision_context.py:23-99) to enrich its reasoning:

```python
builder = DecisionContextBuilder(kg_adapter=kg_adapter, memory_adapter=memory_adapter)
context = await builder.build(state)
# context = {
#     "kg_concepts": [...],        # P16 KG concepts relevant to current focus
#     "memory_signals": [...],     # P18 memories relevant to current focus
#     "enriched_context": {...},   # Combined summary
#     "source_timestamp": "...",
# }
```

**P16 adapter role (p16_adapter.py:22-111):** KGRecallAdapter.recall(context) returns relevance-scored KG concepts. P23 action planner uses these to ground action selection in Guinevere's knowledge graph.

**P18 adapter role (p18_adapter.py:24-102):** MemoryRecallAdapter.recall(context) returns relevance-scored episodic memories. P23 action planner uses these to learn from past action outcomes.

Both adapters are fail-soft: when the client is None or recall fails, they return `_degraded: True` with empty results (p16_adapter.py:62-69, p18_adapter.py:65-72).

#### 3.6.3 Journal Integration

P23 actions produce journal entries via JournalWriter:

```python
# After action completion (success or failure)
entry = await journal_writer.write_entry(
    state=current_state,
    reasoning=f"P23 action '{action_id}' chosen because: {brain_response}",
    lessons_learned=f"Action outcome: {result}. Errors: {errors}.",
    confidence=0.8 if result.success else 0.3,
)
```

**Source:** journal.py:27-66. JournalWriter.write_entry() persists to PostgresAuditJournal via `self._audit_journal.record(entry)`.

### 3.7 Self-Improvement Integration

#### 3.7.1 How Action Outcomes Feed Self-Improvement

ReflectionEvaluator (self_improve.py:90-261) runs every 1h via _heartbeat_1h (heartbeat.py:641). It inspects:

| Metric | Source | Threshold | P23 Relevance |
|---|---|---|---|
| error_count | state["errors"] | > 3 | P23 action failures contribute to errors list |
| cycle_count vs act_count | state["cycle_count"], state["act_count"] | cycle > 100, act < 10 | P23 action efficiency affects this ratio |
| idle time | state["last_heartbeat"] | > 1 hour | P23 keeps kernel alive via actions |
| observation queue | state["observations"] | > 80 | P23 action outcomes add observations |

When thresholds are exceeded, ReflectionEvaluator generates ImprovementCandidate objects (self_improve.py:38-87) in categories: skill, prompt, planner, code.

**P23 action outcomes feed self-improvement by:**
1. Recording action failures in state["errors"] (triggers planner candidates)
2. Tracking action success rate (affects cycle/act ratio)
3. Producing observations that fill the queue (triggers skill candidates)

#### 3.7.2 Regression Gate

Before any P23 improvement candidate is promoted, it must pass RegressionGate (self_improve.py:264-363):

```python
gate = RegressionGate(test_command="python -m pytest tests/life_kernel/ -q --tb=short")
passed = gate.run_regression_tests(candidate)
if passed:
    gate.promote(candidate)
else:
    gate.rollback(candidate)  # Sets status="rejected"
```

P23 MUST NOT auto-promote candidates. The §0.1 governance exception requires: regression test → audit → rollback-before-promote.

### 3.8 §0.1 Policy-Gate Mapping to P23 Executors

From AGENTS.md §0.1 (lines 57-92):

| P23 Executor | Autonomy Level | Gate | Gate Failure Action |
|---|---|---|---|
| P23VPSExecutor | L1 (auto) | backup→canary→smoke→rollback (engineer_mind.py:298-373) | Halt, rollback, escalate |
| P23GitHubExecutor | L1 (auto) | PR review → merge → deploy gate | Halt, rollback, escalate |
| P23BrowserExecutor | L2 (auto when Faiz silent) | Risk-classified: low→auto, medium→log, high→approval | Log or escalate |
| P23DesktopExecutor | L2 (auto when Faiz silent) | Risk-classified by action type | Log or escalate |
| P23FileExecutor | L1 (auto) | No destructive ops without backup | Halt, escalate |
| P23EmailExecutor | L1 (auto for low-risk) | EmailMind risk classification (email_mind.py:115-149) | Sensitive→approval, dangerous→blocked |
| P23FinanceExecutor | L2 (auto for record only) | BLOCKED_FINANCE_ACTIONS (finance_mind.py:47-49) | Blocked actions never execute |
| P23MobileExecutor | L3 (needs gate+approval) | Explicit per-action approval | Wait for Faiz |
| P23SecretsExecutor | L4 (never auto) | Explicit per-action approval | Never auto-execute |

**Silence is not a blocker for L1/L2 (V-003).** When Faiz is silent, L1/L2 executors proceed autonomously through their policy gates. L3 waits for explicit approval. L4 never executes without explicit per-action approval.

### 3.9 Dashboard Rendering of Action State

#### 3.9.1 Current Dashboard Structure

DashboardRenderer (dashboard.py:19-387) renders these sections:
- HEARTBEAT (dashboard.py:76-83)
- STATE (dashboard.py:85-98)
- GOALS (dashboard.py:100-126)
- COMMITMENTS (dashboard.py:128-139)
- CONCERNS (dashboard.py:141-152)
- SESSIONS (dashboard.py:154-160)
- AUDIT (dashboard.py:162-174)
- AUTONOMY (dashboard.py:176-186)

#### 3.9.2 P23 ADDITIVE Dashboard Section

P23 adds a new `_p23_actions_section()` to DashboardRenderer (ADDITIVE — does not modify existing sections):

```markdown
## P23 ACTIONS

- **Queued**: 3
- **Running**: 1
  - [browser] navigate to example.com (started 2m ago)
- **Done (last 5)**: 12
- **Failed (last 5)**: 1
  - [vps] deploy failed: smoke test timeout (rolled back)
- **Rollback**: 0 pending
```

**Rendering location:** Added to `_render_full()` (dashboard.py:201-214) and `render_embed()` (dashboard.py:285-386) as a new field in the embed fields list.

**State fields required (ADDITIVE to LifeMindState):**
```python
class LifeMindState(TypedDict, total=False):
    # ... existing fields ...
    p23_action_queue_count: NotRequired[int]
    p23_action_running: NotRequired[list[dict[str, Any]]]
    p23_action_done_count: NotRequired[int]
    p23_action_failed_count: NotRequired[int]
    p23_action_rollback_pending: NotRequired[int]
```

### 3.10 Non-Interference: Explicit List of P20 Files P23 MUST NOT Modify

| File | Reason Locked |
|---|---|
| src/life_kernel/hermes_brain.py | Brain wrapper — P23 uses it, does not modify it |
| src/life_kernel/graph.py | StateGraph core — P23 adds observations via BackgroundCognition, does not modify nodes |
| src/life_kernel/heartbeat.py | 6-interval schedule — P23 MUST NOT alter timing or add intervals |
| src/life_kernel/hard_stop_handler.py | HARD STOP core — P23 reads Redis flag, does not modify handler |
| src/life_kernel/safety_plugin.py | Safety plugin — P23 respects, does not modify |
| src/life_kernel/state.py | LifeMindState — P23 adds NotRequired fields only (additive) |
| src/life_kernel/sensor_adapters/base.py | BaseSensorAdapter — READ-ONLY, P23 adds executor base separately |
| src/life_kernel/cognition.py | BackgroundCognition — P23 uses _write_to_graph, does not modify loops |
| src/life_kernel/p16_adapter.py | KGRecallAdapter — P23 reads, does not modify |
| src/life_kernel/p18_adapter.py | MemoryRecallAdapter — P23 reads, does not modify |
| src/life_kernel/decision_context.py | DecisionContextBuilder — P23 uses, does not modify |
| src/life_kernel/journal.py | JournalWriter — P23 writes entries, does not modify writer |
| src/life_kernel/dashboard.py | DashboardRenderer — P23 adds section, does not modify existing sections |
| src/life_kernel/dashboard_writer.py | DashboardWriter — P23 uses update_dashboard, does not modify |
| src/life_kernel/log_channel.py | LogChannel — P23 writes lifecycle events, does not modify |
| src/life_kernel/discord_rest_client.py | Discord REST — P23 uses, does not modify |

**P23 NEW files (additive):**
- src/life_kernel/p23_executor_base.py — NEW executor base class (write-side, not a sensor)
- src/life_kernel/p23_action_planner.py — NEW action planner (calls HermesBrain)
- src/life_kernel/p23_action_queue.py — NEW Redis-backed action queue
- src/life_kernel/p23_executors/*.py — NEW domain-specific executors
- src/life_kernel/p23_hard_stop_watcher.py — NEW HARD STOP watcher (reads Redis, calls cancel callbacks)

### 3.11 Detailed Integration Table

| P20 Surface | P23 Integration Point | Call/Contract | Additive-or-Locked | Risk |
|---|---|---|---|---|
| HermesBrain.think() | Action selection, scheduling, self-debug, rollback | `await brain.think(user_message, system_prompt, conversation_history)` → dict | Locked (use only) | Low — stable API |
| HermesBrain.think_with_tools() | Tool-augmented scheduling | `await brain.think_with_tools(user_message, system_prompt, tools, conversation_history)` → dict | Locked (use only) | Low |
| heartbeat._heartbeat_1s() | HARD STOP detection | Redis GET "life_kernel:hard_stop" | Locked (do not alter) | Critical — safety |
| heartbeat._heartbeat_60s() | Dashboard update | `dashboard_writer.update_dashboard(state)` | Locked (do not alter) | Medium — concurrent state |
| heartbeat._heartbeat_1h() | Self-improvement eval | `ReflectionEvaluator(graph, config, brain).evaluate(state)` | Locked (do not alter) | Low |
| graph.py:_ADAPTERS registry | KG/memory/journal injection | `set_adapters(kg_adapter, memory_adapter, journal_writer)` | Locked (read registry) | Medium — module-level state |
| graph.py:observe_node | Action outcome observations | P23 writes via BackgroundCognition._write_to_graph() | Additive (new observations) | Low |
| graph.py:act_node | Action execution hook | P23 does NOT modify act_node; runs as separate task | Locked (do not modify) | Critical — concurrent execution |
| graph.py:reflect_node | Journal entries | `journal_writer.write_entry(state, reasoning, lessons, confidence)` | Additive (new entries) | Low |
| state.py:LifeMindState | P23 action state fields | Add NotRequired fields: p23_action_queue_count, p23_action_running, etc. | Additive | Low |
| dashboard.py:DashboardRenderer | P23 actions section | Add _p23_actions_section() to _render_full() | Additive | Low |
| dashboard_writer.py:update_dashboard | P23 state rendering | P23 state flows through existing update_dashboard() | Locked (use only) | Low |
| journal.py:JournalWriter | Action audit | `write_entry(state, reasoning, lessons, confidence)` | Locked (use only) | Low |
| self_improve.py:ReflectionEvaluator | Action outcome metrics | P23 errors/efficiency feed into evaluate() | Locked (do not modify) | Low |
| self_improve.py:RegressionGate | Candidate promotion | `gate.run_regression_tests(candidate)` → bool | Locked (use only) | Low |
| domain_minds/engineer_mind.py | VPS/GitHub executor | `EngineerMind.deploy(target)` → dict | Locked (delegate to) | Medium — policy gates |
| domain_minds/email_mind.py | Email executor | `EmailMind.classify_sensitivity(email)` → str | Locked (delegate to) | Medium — risk classification |
| domain_minds/finance_mind.py | Finance executor | `FinanceMind.execute_action(action)` → dict | Locked (delegate to) | Medium — blocked actions |
| domain_minds/deploy_backend.py | VPS SSH transport | `SSHDeployBackend.backup/canary/smoke/deploy/rollback()` | Locked (delegate to) | Medium — SSH operations |
| sensor_adapters/base.py | READ-ONLY sensor base | P23 does NOT inherit from BaseSensorAdapter | Locked (read only) | Critical — wrong abstraction |
| sensors.py:SensorRegistry | Sensor polling | P23 does NOT register with SensorRegistry | Locked (read only) | Low |
| cognition.py:BackgroundCognition | Observation writes | P23 uses _write_to_graph() for action outcomes | Locked (use only) | Low |
| p16_adapter.py:KGRecallAdapter | Action context | `kg_adapter.recall(context)` → concepts | Locked (use only) | Low — fail-soft |
| p18_adapter.py:MemoryRecallAdapter | Action context | `memory_adapter.recall(context)` → memories | Locked (use only) | Low — fail-soft |
| Redis "life_kernel:hard_stop" | HARD STOP flag | P23 reads via GET, does NOT write | Locked (read only) | Critical — safety |
| Redis action queue | P23 action queue | P23 creates NEW key "p23:action_queue" | Additive | Low |

---

## 4. Implications for P23 Design

### 4.1 Architecture: Separate Asyncio Task, Not a Heartbeat Loop

P23's ActionPlanner MUST run as a separate asyncio task, NOT as a new heartbeat interval. This preserves the 6-interval schedule and avoids concurrent graph.ainvoke collisions.

```python
class P23ActionPlanner:
    def __init__(self, brain: HermesBrain, redis: Redis, journal: JournalWriter):
        self._brain = brain
        self._redis = redis
        self._journal = journal
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    async def start(self):
        self._task = asyncio.create_task(self._run_loop())

    async def _run_loop(self):
        while not self._stop_event.is_set():
            # 1. Check HARD STOP
            if await self._check_hard_stop():
                await self._on_hard_stop()
                continue
            # 2. Poll action queue
            action = await self._dequeue_action()
            if action:
                await self._execute_action(action)
            # 3. Sleep
            await asyncio.sleep(10)  # 10s poll interval
```

### 4.2 Executor Base: NEW Write-Side Abstraction

P23 creates a NEW executor base class, separate from BaseSensorAdapter (which is READ-ONLY):

```python
class P23ExecutorBase(ABC):
    """Abstract base for P23 write-side executors."""

    EXECUTOR_NAME: str = "base"
    RISK_LEVEL: str = "medium"  # low, medium, high

    def __init__(self, redis_client: Redis, journal_writer: JournalWriter):
        self._redis = redis_client
        self._journal = journal_writer

    @abstractmethod
    async def execute(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute an action. Must check HARD STOP pre-action."""

    async def health(self) -> bool:
        """Return True if executor is healthy."""
        return True

    async def cancel(self, action_id: str) -> None:
        """Cancel a running action (HARD STOP callback)."""
        pass
```

### 4.3 HARD STOP Watcher: Dedicated Task

P23 runs a dedicated HARD STOP watcher that polls the same Redis key as heartbeat._heartbeat_1s() but does NOT modify the heartbeat:

```python
class P23HardStopWatcher:
    def __init__(self, redis: Redis, planner: P23ActionPlanner):
        self._redis = redis
        self._planner = planner

    async def start(self):
        asyncio.create_task(self._watch_loop())

    async def _watch_loop(self):
        while True:
            try:
                value = await self._redis.get("life_kernel:hard_stop")
                if bool(value):
                    await self._planner.on_hard_stop()
            except Exception:
                pass  # fail-closed handled by executor pre-check
            await asyncio.sleep(1)  # Match heartbeat L1S cadence
```

### 4.4 Action Queue: Redis-Backed, Separate Key

P23 uses a NEW Redis key "p23:action_queue" (a Redis list) to avoid colliding with P20 state:

```
P20 keys (DO NOT TOUCH):
  - life_kernel:hard_stop
  - life_kernel:dashboard_message_id

P23 keys (NEW):
  - p23:action_queue (list of action dicts)
  - p23:action_running (hash of action_id → executor_name)
  - p23:action_audit (list of audit entries, capped at 1000)
```

### 4.5 Fail-Soft Contract

Every P23 component follows the same fail-soft pattern as P20:
- HermesBrain failure → fallback response (hermes_brain.py:345-370)
- Redis failure → fail-closed on safety (heartbeat.py:277-280)
- Journal failure → log warning, continue (journal.py:64-66)
- Executor failure → record in errors, propose rollback via brain

---

## 5. Risks / Open Questions

### 5.1 Critical Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Concurrent graph.ainvoke from P23 and heartbeat_60s | Critical | P23 writes observations via BackgroundCognition queue (serialized), never calls graph.ainvoke directly |
| HARD STOP race condition (action starts between poll and execute) | Critical | Pre-action HARD STOP check + mid-action check for long-running actions |
| Executor modifies P20 locked file | Critical | Code review gate + P23 executor base enforces read-only P20 access |
| Action queue overflow | High | Cap queue at 100 actions, drop oldest with audit entry |
| Brain timeout during action selection | High | HermesBrain has 30s timeout (graph.py:24), fallback to static priority engine |

### 5.2 Medium Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Dashboard render time increases with P23 section | Medium | Checksum-skip in DashboardWriter (dashboard_writer.py:141-144) avoids redundant renders |
| Self-improvement candidates from P23 actions auto-promoted | Medium | RegressionGate enforces pytest pass before promotion (self_improve.py:335-349) |
| P23 action audit grows unbounded | Medium | Cap audit at 1000 entries (matching journal reducer pattern, state.py:81-97) |
| Domain mind policy gate bypass | Medium | P23 executors delegate to domain minds for policy-gated actions, never bypass |

### 5.3 Open Questions

1. **Action scheduling granularity**: Should P23 schedule actions at the 10s poll interval, or should it support sub-second scheduling for time-critical actions (e.g., HARD STOP response)?
2. **Executor concurrency**: Can multiple P23 executors run simultaneously (e.g., browser + VPS), or should they be serialized through a single execution loop?
3. **Action rollback scope**: When an action fails mid-execution, what is the rollback scope? Only the action's side effects, or all actions in the current batch?
4. **Mobile executor approval channel**: L3 mobile actions need explicit approval — should approval come via Discord command, or via a separate approval queue?
5. **P23 action history retention**: How long should P23 action audit entries be retained? P20 journal caps at 1000 (state.py:81-97), but P23 may need longer history for self-improvement.

---

## 6. Recommendations to Planner

### 6.1 Implementation Order

1. **Phase 1: Foundation**
   - P23ExecutorBase (new file)
   - P23ActionQueue (Redis-backed)
   - P23HardStopWatcher
   - P23ActionPlanner (calls HermesBrain)

2. **Phase 2: Core Executors**
   - P23VPSExecutor (wraps SSHDeployBackend)
   - P23GitHubExecutor (wraps EngineerMind)
   - P23FileExecutor (local filesystem)

3. **Phase 3: External Executors**
   - P23BrowserExecutor (Playwright/MCP)
   - P23EmailExecutor (wraps EmailMind)
   - P23FinanceExecutor (wraps FinanceMind)

4. **Phase 4: Dashboard + Audit**
   - P23 actions section in DashboardRenderer
   - P23 action audit entries in JournalWriter
   - P23 state fields in LifeMindState

5. **Phase 5: Self-Improvement Loop**
   - P23 action outcomes feed ReflectionEvaluator
   - P23 improvement candidates via RegressionGate

### 6.2 Testing Strategy

- Unit tests for P23ExecutorBase (mock Redis, mock brain)
- Integration tests for P23ActionPlanner (mock executors)
- HARD STOP propagation tests (verify cancel callbacks fire)
- Dashboard render tests (verify P23 section appears)
- Policy gate tests (verify domain mind delegation)

### 6.3 Non-Negotiable Constraints

1. **NEVER modify P20 locked files** (see Section 3.10)
2. **NEVER call raw LLMRouter.chat** — always use HermesBrain
3. **NEVER alter heartbeat intervals** — P23 runs as separate task
4. **NEVER bypass HARD STOP** — pre-action + mid-action checks mandatory
5. **NEVER auto-promote self-improvement candidates** — RegressionGate required
6. **NEVER bypass domain mind policy gates** — delegate to EngineerMind/EmailMind/FinanceMind

---

## 7. Verdict

The P20 life kernel provides a well-defined, stable surface for P23 integration. The key integration points are:

- **Brain**: HermesBrain.think()/think_with_tools() for all LLM-driven decisions
- **Safety**: Redis "life_kernel:hard_stop" polled by P23 watcher (additive, parallel to heartbeat)
- **Audit**: JournalWriter.write_entry() for action reasoning and outcomes
- **Context**: DecisionContextBuilder + P16/P18 adapters for action grounding
- **Policy**: Domain minds (EngineerMind/EmailMind/FinanceMind) for policy-gated execution
- **Dashboard**: Additive P23 actions section in DashboardRenderer
- **Self-improve**: Action outcomes feed ReflectionEvaluator metrics

P23 is fully additive — it adds new executor classes, a new action planner, a new HARD STOP watcher, and new dashboard sections without modifying any P20 locked files. The architecture preserves P20's 6-interval heartbeat schedule, HARD STOP semantics, and policy gate hierarchy.

**The dependency map is complete. P23 can proceed to planner gate.**
