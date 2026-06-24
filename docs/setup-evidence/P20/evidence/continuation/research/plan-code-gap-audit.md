# P20 Living Autonomy Kernel — Plan-to-Code Gap Audit

> **Scope:** LK-001 .. LK-017  
> **Plan root:** `docs/setup-evidence/P20/plan/`  
> **Code root:** `src/life_kernel/`  
> **Generated:** 2026-06-24  
> **Tests:** `python -m pytest tests/life_kernel/ -q --disable-warnings --tb=short` -> **420 passed, 7 skipped, 0 failed**

## Executive Verdict

The P20 Living Autonomy Kernel has a **solid skeleton and passes all local tests**, but it is still **partially a facade** for several life-mind capabilities. The runtime (heartbeat, graph, Hermes brain bridge, dashboard, and startup wiring) is real. Most background cognition, daily-life sensors, per-session execution, and real-world side effects remain **architectural placeholders** or **dry-run stubs**. No production 24-hour soak has been completed.

## Per-Step Gap Matrix

| Step | Plan / Acceptance Criteria | What Exists | Status | Real Gap |
|------|---------------------------|-------------|--------|----------|
| **LK-001** | Governance + vision sync; update `AGENTS.md` and `P20/README.md`; mark old plan superseded | `AGENTS.md` includes P20 Autonomy-First Governance Exception; `P20/README.md` updated; old `p5-p20-merged-plan.md` marked superseded | COMPLETE | None |
| **LK-002** | LangGraph dep + graph skeleton; typed `LifeMindState` | `graph.py`, `state.py`, `models.py`; tests pass | COMPLETE | None |
| **LK-003** | World model persistence (PostgreSQL + Redis); durable task queue, concerns, commitments, journal | SQLAlchemy models in `models.py` (`life_mind_state`, `heartbeat_record`, `domain_mind_state`); `redis_client.py` caches state; `journal.py`/`PostgresAuditJournal` persist journal | PARTIAL | No `world_model.py`; no active world-model update engine; heartbeat 30s awareness refresh is a placeholder |
| **LK-004** | Hermes brain bridge; must call `AIAgent.run_conversation()` | `hermes_brain.py` wraps `AIAgent`; `think()` and `think_with_tools()` call `self.agent.run_conversation()`; no `LLMRouter` fallback | COMPLETE | None |
| **LK-005** | Heartbeat service with 1s/10s/30s/60s/5m/1h pulses | `heartbeat.py` implements all six intervals; 1s HARD STOP check, 60s graph invoke, 1h self-improvement are real; 10s/30s/5m are placeholders | MOSTLY COMPLETE | 10s stuck detection, 30s sensor refresh, 5m domain-mind scan are stubbed |
| **LK-006** | Global life-mind graph chooses self-directed tasks | `graph.py` has observe -> decide -> act/reflect/idle; `idle_node` seeds a `goal` from recalled KG/memory or deterministic fallback; `decide_node` has priority engine; brain wrappers are optional | COMPLETE (skeleton) | LLM brain only consulted when available; decision still static/fallback-safe |
| **LK-007** | Background cognition loops run and write only through queues/locks | `cognition.py` has six `asyncio.Task` loops (observer, memory, critic, curiosity, self-improvement, guardian); write queue serializes graph writes | RUNS BUT MOSTLY PLACEHOLDER | Observer uses `SensorRegistry` if given, otherwise placeholder; memory/critic/curiosity/self-improvement/guardian only emit placeholder observations |
| **LK-008** | Per-session autonomy graph with worktree/profile/thread isolation | `session_graph.py` builds a LangGraph SDLC graph; `SessionProfileManager` in-memory; `SessionWorktree`/`DiscordThreadManager` record intent only | PARTIAL | Session SDLC nodes are placeholders; worktree, profile, thread isolation are not real |
| **LK-009** | Discord dashboard (edit-not-spam) + log UX | `dashboard.py`/`dashboard_writer.py` edit a single message; `log_channel.py`/`discord_rest_client.py` post lifecycle logs; `log_writer.py` persists local log; renders living state sections | COMPLETE | None |
| **LK-010** | P16 KG + P18 memory integration into observe/decide context | `p16_adapter.py`, `p18_adapter.py`, `decision_context.py`; `main.py` wires real recall callables into graph; `observe_node` populates `recalled_concepts`/`recalled_memories`; brain decide prompt includes them | COMPLETE | None (fail-soft if DB unavailable) |
| **LK-011** | Unified daily-life sensors (Discord, Gmail, finance, wearable, surveillance, VPS, repo, browser) | `SensorRegistry` + 8 `BaseSensorAdapter` subclasses; all return safe placeholder observations | COMPLETE AS ARCHITECTURE | No real API polling in any adapter |
| **LK-012** | Email autonomy: classify, draft, send low-risk; block sensitive/dangerous | `EmailMind` with deterministic risk classification and LangGraph subgraph; low-risk path returns `queued` (no real API); sensitive/dangerous blocked | COMPLETE (POLICY) | Real Gmail send not implemented; only placeholder send path |
| **LK-013** | Finance record/category/summary/anomaly; no payment/transfer | `FinanceMind` records, classifies, summarizes, detects anomalies; `execute_action` blocks pay/transfer/withdraw/invest/trade; uses `PostgresAuditJournal` in production mode | COMPLETE (LOGIC) | No real banking/finance API integration |
| **LK-014** | Engineering deployment autonomy: backup -> canary -> smoke -> deploy/rollback | `EngineerMind` + `SSHDeployBackend` with dry-run default; policy-gated flow and graph exist | COMPLETE (POLICY/DRY-RUN) | Real SSH/systemd execution disabled by default; production deploy not exercised |
| **LK-015** | Self-improvement reflection + regression gate + candidate tracking | `self_improve.py` has `ReflectionEvaluator`, `ImprovementTracker`, `RegressionGate` (runs `pytest` subprocess), candidate dataclass | COMPLETE (LOGIC) | `ImprovementTracker` is in-memory only; no persistent candidate store or auto-promotion |
| **LK-016** | Replace trigger-first startup wiring | `src/core/main.py` starts `HermesBrain`, `create_life_mind_graph`, `HeartbeatService`; removes `LoopScheduler`/daily rituals | COMPLETE | None |
| **LK-017** | Runtime soak / audit / production rollout | `tests/life_kernel/test_soak.py` with staged soak tests; local suite 420 passed | PARTIAL | No real 24-hour production soak; no actual VPS deployment; auditor verdict = "PRODUCTION ROLLOUT HOLD" |

## Placeholder / Stub / TODO Inventory in `src/life_kernel/`

> Search terms: `placeholder`, `stub`, `TODO`, `FIXME`, `NotImplemented`, `pass #`, `mock`, `fake`, `dummy`

| File | Count | Key Placeholders / Stubs |
|------|-------|---------------------------|
| `cognition.py` | 6 loops | Observer falls back to placeholder observation; memory/critic/curiosity/self-improvement/guardian loops emit only placeholder text and never call `hermes_brain` |
| `heartbeat.py` | 3 intervals | `_heartbeat_10s`, `_heartbeat_30s`, `_heartbeat_5m` are empty placeholders |
| `graph.py` | 1 | "placeholder for P19 heartbeat integration" in observe_node |
| `session_graph.py` | 4 | Execute, audit, document, complete nodes are placeholders; `SessionWorktree`, `SessionProfileManager`, `DiscordThreadManager` are intent-only / in-memory |
| `self_improve.py` | 4 | All candidate generators are "placeholder" per docstring; tracker is in-memory |
| `sensor_adapters/*.py` | 8 adapters | Every adapter returns a placeholder observation; no real API calls |
| `domain_minds/email_mind.py` | 1 | `send_node` is a placeholder send path |
| `domain_minds/engineer_mind.py` | 1 | `_deploy_node` is intent-only when no backend |
| `domain_minds/deploy_backend.py` | 1 | `SSHDeployBackend` defaults to dry-run; real mode raises `NotImplementedError` (intentional) |
| `sensors.py` | - | No stubs in code, but depends on placeholder adapters |

**No literal `TODO`/`FIXME`/`NotImplemented` strings were found** in `src/life_kernel/`.

## Specific Checks Requested

### 1. Is `world_model` real or placeholder?

**Verdict:** Partial / placeholder.

- No `world_model.py` module exists.
- Persistence schema exists (`LifeMindStateModel`, `DomainMindState`, `redis_client.py`).
- `observe_node` derives `world_model_status` from real P16/P18 adapter health.
- However, **there is no active world-model update engine**; heartbeat 30s sensor refresh and deep scans are empty placeholders.
- The world model is therefore a **state schema + recall adapters**, not a living, self-updating model.

### 2. Does the Hermes brain bridge call `AIAgent.run_conversation()` or fall back to raw `LLMRouter`?

**Verdict:** Calls `AIAgent.run_conversation()`.

- `src/life_kernel/hermes_brain.py:294-299` and `:403-409` call `self.agent.run_conversation(...)`.
- No `LLMRouter.chat()` or raw model path exists in the kernel.
- `main.py` no longer starts `LLMRouter`; `HermesBrain` is the only brain.

### 3. Does the idle/decision cycle create self-directed tasks from world state, or just health checks?

**Verdict:** Creates self-directed tasks from world state.

- `graph.py:idle_node` inspects `recalled_memories` and `recalled_concepts` to generate a task; falls back to a deterministic rotation only when recall is empty.
- It appends a `goal` to `state["goals"]` with `Priority.IMPROVE_AUTONOMY`.
- `decide_node` routes to `idle` only when no goals/commitments/concerns exist; otherwise routes to `act`/`reflect`.
- The heartbeat 60s pulse invokes the graph and triggers this behavior.

### 4. Are P16 KG and P18 memory wired into observe/decide context?

**Verdict:** Yes, wired and fail-soft.

- `main.py` builds real recall callables for P18 (`recall_memories`) and P16 (`KGQueryEngine.search_entities`) and injects them into `create_life_mind_graph(..., kg_adapter=..., memory_adapter=...)`.
- `graph.py:observe_node` calls both adapters and stores results in `recalled_concepts` / `recalled_memories`.
- `_make_brain_decide` feeds recalled concepts/memories into the LLM prompt.
- If adapters fail or are unavailable, the kernel degrades gracefully and continues.

### 5. Does the dashboard show living state or raw technical loop state?

**Verdict:** Shows living state.

- `dashboard.py` renders: heartbeat, state, goals, commitments, concerns, sessions, audit, autonomy (last decision, next action, memory status, HARD STOP).
- `render_embed()` produces a Discord embed with status emoji, current focus, agenda, memory recall counts, cycles, etc.
- It redacts secrets and checksums state to avoid spam.

### 6. Are daily-life domain minds real or stubs?

| Domain | Status |
|--------|--------|
| **Email** | Real policy engine (`EmailMind`) with risk classification and LangGraph subgraph; **real send is stubbed** |
| **Finance** | Real record/classify/summary/anomaly engine (`FinanceMind`); **real banking API is absent** |
| **Health / Wearable** | **Stub only**: `WearableSensorAdapter` returns a placeholder; no `HealthMind` domain mind exists |
| **Communication (Discord)** | **Stub only**: `DiscordSensorAdapter` placeholder |
| **Engineering deploy** | Real policy/dry-run engine; real SSH/systemd execution disabled by default |

### 7. Do background cognition loops actually run, or are they only defined?

**Verdict:** They run, but most are placeholders.

- `BackgroundCognition.start()` launches six `asyncio.Task` loops.
- The write queue serializes all graph writes.
- `observer` polls a `SensorRegistry` if supplied; otherwise writes a placeholder.
- `memory`, `critic`, `curiosity`, `self_improvement`, and `guardian` only emit placeholder observations and do **not** call `hermes_brain` or real backends.
- Heartbeat 1h also runs a real `ReflectionEvaluator` / `ImprovementTracker` path.

## Missing Evidence Files

The following per-step evidence directories were **not found** under `docs/setup-evidence/P20/evidence/`:

- `LK-001/` .. `LK-009/` -- no `verification.md` or `auditor-gate.md` present.
- `LK-010/` .. `LK-017/` have evidence files.

This means the early waves (LK-001..009) were implemented but not formally evidenced, which is a documentation/traceability gap.

## Risk / Continuation Heat Map

| Area | Realization | Risk | Next Continuation Work |
|------|-------------|------|------------------------|
| Core runtime (heartbeat, graph, brain bridge) | High | Low | Harden 1s HARD STOP edge cases |
| P16/P18 observe/decide wiring | High | Low | Add recall latency budgets; wire proactive meta-memory |
| Dashboard / log UX | High | Low | Add operator commands; tune update frequency |
| Daily-life sensors | Architecture only | Medium | Implement real Discord/Gmail/finance/wearable/VPS/repo/browser polling |
| Email / finance domain minds | Policy logic only | Medium | Wire real Gmail API (OAuth) and finance ingestion |
| Background cognition | Skeleton only | Medium | Replace placeholder loops with real anomaly detection, curiosity, critic, memory consolidation |
| Per-session autonomy graph | Skeleton only | High | Implement real worktree/profile/thread isolation and SDLC nodes |
| Engineering deploy | Dry-run only | High | Enable `SSHDeployBackend` real mode under explicit approval; run real canary deploy |
| Self-improvement | In-memory only | Medium | Persistent candidate store; auto-promotion under regression gate |
| World model | Schema only | High | Build active world-model update engine; replace heartbeat 30s/5m placeholders |
| Production soak | Not started | High | Real 24-hour VPS soak; production rollout |

## Conclusion

The P20 Living Autonomy Kernel is **locally complete and test-green**, but the **real gaps are all on the "live substrate" boundary**: real sensors, real side-effecting actions (email send, finance ingestion, SSH deploy), real per-session execution, and a real production soak. The brain, graph, and dashboard are wired correctly. The continuation plan should prioritize turning the placeholder adapters and dry-run backends into real, consent-gated, audit-wrapped integrations, starting with the highest-risk surfaces (deploy, email, world-model update engine).

---

*Audit path:* `docs/setup-evidence/P20/evidence/continuation/research/plan-code-gap-audit.md`
