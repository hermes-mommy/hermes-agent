# R04: Consciousness Loop Implementation Research

**Generated:** 2026-06-29
**Method:** Full file read + grep analysis of ADR-063, all src/loops/ files (37 .py), auxiliary_client.py, run_agent.py session hooks, and consciousness-loop-implementation-guide.md.

---

## 1. ADR-063 Consciousness Loop Architecture Summary

ADR-063 (`docs/setup-evidence/P28-P36-masterplan/adr-drafts/ADR-063-consciousness-loop-architecture.md`) defines **Pattern C composite** for the consciousness loop: Springdrift substrate + P20 6-loop BackgroundCognition + Letta-style 4-tier memory lifecycle + Autogenesis Protocol. It mandates 7 first-class subsystem components:

| # | Component | Cadence | ADR-063 Source |
|---|-----------|---------|----------------|
| 1 | P20 Heartbeat (L1S/L10S/L30S/L60S) | 1s/10s/30s/60s | ADR-063 line 39-49 |
| 2 | 6-loop BackgroundCognition | 10s-60m | ADR-063 line 51-59 |
| 3 | Plan-Generation Cycle | 24h cron + aspiration weighted | ADR-063 line 61-69 |
| 4 | Dream Cycle (counterfactual + generative) | 4-6h | ADR-063 line 71-81 |
| 5 | Identity + Aspiration Layer | pinned + EWMA | ADR-063 line 83-93 |
| 6 | Emotion / Affect Layer (6-8 dim vector) | EWMA lambda ~0.3 | ADR-063 line 95-107 |
| 7 | 24/7 Operating Boundary | continuous | ADR-063 line 109-111 |

---

## 2. src/loops/ 7-Phase State Machine Inventory

The existing `src/loops/` contains **37 .py files** (not 48 as stated in the plan; the discrepancy likely counts `__pycache__` or subdirectories). These implement a **7-phase SDLC state machine**, NOT a consciousness loop. The phases are an autonomous software development lifecycle engine:

### 2.1 Core State Machine (`src/loops/state_machine.py:25-36`)

```python
LoopPhase(IntEnum):
    RESEARCH = 1
    PLAN_AND_DELEGATE = 2
    DELEGATE = 3
    EXECUTE = 4
    VALIDATE_AND_AUDIT = 5
    UPDATE_DOCUMENTS = 6
    SETUP_EVIDENCE = 7
    COMPLETE = 8  # terminal
```

Status lifecycle: INIT -> RUNNING -> (PAUSED|BLOCKED|COMPLETE|FAILED|CANCELLED)

### 2.2 File-by-File Disposition (37 files)

| File | Purpose | P24 Disposition |
|------|---------|-----------------|
| `state_machine.py` | 7-phase SDLC state machine (IntEnum + LoopStateMachine class) | **DELETE** -- consciousness loop has entirely different phase model (7 substrates, not 7 SDLC phases) |
| `manager.py` | LoopManager: creates asyncio.Tasks, drives phases via PHASE_REGISTRY, integrates guardian/cost | **PORT semantics** -- the asyncio.TaskGroup orchestration pattern and guardian integration are valuable; restructure for consciousness substrates |
| `circuit_breaker.py` | 3-layer safety: DependencyCircuitBreaker + StuckDetector + SafetyGate | **PORT** -- all 3 layers directly reusable; the 6 circuit breakers ADR-063 requires map to DependencyCircuitBreaker instances |
| `guardian.py` | LoopGuardian watchdog: heartbeat 30s, progress timeout 300s, resource check 60s | **PORT** -- the heartbeat liveness pattern (HEARTBEAT_INTERVAL * 3 kill) is directly applicable to consciousness substrate monitoring |
| `scheduler.py` | APScheduler AsyncIOScheduler for cron-based loop triggers | **PORT** -- the Dream cycle (4-6h) and Plan cycle (24h) need cron scheduling |
| `reflection.py` | ReflectionExtractor: post-loop lesson extraction via LLM | **PORT** -- maps to Metacognition substrate (C2) |
| `escalation.py` | 4-tier escalation: AUTO/NOTIFY/APPROVE/ESCALATE | **PORT** -- directly reusable for consciousness failure modes |
| `concurrency.py` | ConcurrencyLimiter + TokenBucket + ResourceGate | **PORT** -- resource gate pattern needed for consciousness budget control |
| `safety_integration.py` | LoopSafetyGate: HardStopHandler bridge + Redis pub/sub HMAC-signed broadcast | **PORT** -- HARD STOP mechanism critical for consciousness loop safety |
| `budget.py` | IterationBudget: turn/token/cost limiting with parent-child propagation | **PORT** -- consciousness substrates need budget bounds |
| `cost.py` | LoopCostTracker: Redis DB5 per-loop cost tracking | **PORT** -- cost tracking for LLM-heavy consciousness loop |
| `retry.py` | RetryExecutor with exponential backoff + error taxonomy (transient/deterministic/unknown) | **PORT** -- LLM call retry with circuit breaker integration |
| `recovery.py` | RecoveryManager: SHA-256 hash checkpoints + PostgreSQL persistence + restart recovery | **PORT** -- consciousness loop must survive process restart |
| `state_store.py` | LoopStateStore: PostgreSQL `projects.loop_instances` CRUD | **MODIFY** -- schema changes needed for consciousness-specific fields |
| `phases/base.py` | BasePhaseHandler: abstract base with `_call_llm` helper via constructor-injected LLMRouter | **PORT** -- the `_call_llm` pattern becomes the self-prompting call for each substrate |
| `phases/__init__.py` | PHASE_REGISTRY: maps LoopPhase -> async handler | **REWRITE** -- replace SDLC phase registry with consciousness substrate registry |
| `phases/research.py` | Research phase handler | **DELETE** -- SDLC-specific |
| `phases/plan_delegate.py` | Plan and Delegate phase handler | **DELETE** -- SDLC-specific |
| `phases/delegate.py` | Delegate phase handler | **DELETE** -- SDLC-specific |
| `phases/execute.py` | Execute phase handler | **DELETE** -- SDLC-specific |
| `phases/validate_audit.py` | Validate and Audit phase handler | **DELETE** -- SDLC-specific |
| `phases/update_docs.py` | Update Docs phase handler | **DELETE** -- SDLC-specific |
| `phases/setup_evidence.py` | Setup Evidence phase handler | **DELETE** -- SDLC-specific |
| `environment.py` | EnvironmentMonitor: service health + system resources + 4-level degradation | **PORT** -- consciousness loop needs environment awareness for graceful degradation |
| `verify.py` | OutputVerifier: file existence, markdown structure, forbidden patterns, command execution | **PORT** -- output verification useful for consciousness substrate outputs |
| `hash_anchor.py` | SHA-256 line hashing for edit validation | **PORT** -- integrity checking for consciousness state |
| `sub_agent.py` | SubAgentSpawner: spawns delegated sub-agent tasks | **PORT** -- ActiveCognition substrate may spawn sub-agents |
| `contract.py` | TaskContract: structured task specification | **PORT** -- task contracts for consciousness-initiated work |
| `evidence.py` | EvidencePipeline: phase artifact collection + final report generation | **MODIFY** -- adapt for consciousness substrate evidence |
| `artifacts.py` | evidence_dir, write_artifact, read_artifact, artifact_exists | **PORT** -- artifact persistence for consciousness outputs |
| `enforcer.py` | TodoEnforcer | **REVIEW** -- may be SDLC-specific |
| `backlog.py` | Backlog management | **PORT** -- consciousness loop may maintain task backlog |
| `dedup.py` | Deduplication | **PORT** -- thought deduplication for consciousness stream |
| `curator.py` | Curator | **PORT** -- memory curation for dream cycle |
| `conversation.py` | Conversation management | **PORT** -- conversation state for consciousness |
| `context.py` | Context management | **PORT** -- context for consciousness substrates |
| `prompts.py` | Prompt templates | **REWRITE** -- consciousness-specific prompt templates |
| `metrics.py` | Metrics collection | **PORT** -- observability for consciousness loop |
| `sandbox.py` | Sandbox isolation | **PORT** -- sandboxed execution for consciousness-initiated actions |
| `audit_writer.py` | SHA-256 chained audit trail writer | **PORT** -- audit trail critical for consciousness accountability |
| `testing_gate.py` | Testing gate | **REVIEW** -- may be SDLC-specific |
| `review_fork.py` | Review fork | **REVIEW** -- may be SDLC-specific |
| `discovery.py` | Discovery | **PORT** -- curiosity-driven discovery substrate |
| `tool_registry.py` | Tool registry | **PORT** -- consciousness loop needs tool access |
| `skill_library.py` | Skill library | **PORT** -- self-improvement substrate needs skill tracking |
| `priority.py` | Priority management | **PORT** -- consciousness thought prioritization |
| `hermes_bridge.py` | Hermes bridge | **PORT** -- Hermes Society integration |

**Disposition summary:**
- **DELETE**: 7 files (all SDLC phase handlers + state_machine.py)
- **PORT**: 25 files (directly reusable patterns)
- **MODIFY**: 2 files (state_store.py schema changes, evidence.py adaptation)
- **REWRITE**: 2 files (phases/__init__.py, prompts.py)
- **REVIEW**: 3 files (enforcer.py, testing_gate.py, review_fork.py)

---

## 3. Self-Prompting via auxiliary_client.py

### 3.1 How Self-Prompting Works

The consciousness loop needs to call the LLM autonomously (self-prompting). The mechanism is:

1. **auxiliary_client.py** (`.venv/Lib/site-packages/agent/auxiliary_client.py`) provides a resolution chain for LLM calls with 7-step fallback: Main provider -> OpenRouter -> Nous Portal -> Custom endpoint -> Native Anthropic -> Direct API-key providers -> None.

2. **BasePhaseHandler._call_llm** (`src/loops/phases/base.py:140-189`) provides the protected helper that all phase handlers use. It accepts `messages: list[dict[str, str]]` and `task_type: str`, calls `self._llm_router.chat()`, and returns a dict with `content`, `usage`, and `model`.

3. **For consciousness self-prompting**: Each substrate (Heartbeat, ActiveCognition, Reflection, etc.) would construct a prompt (system + user messages), call `_call_llm()`, and process the response to generate the next thought/action. The prompt templates would live in `prompts.py` (rewritten).

### 3.2 Mock Requirement (D3)

Per operator decision D3, all LLM calls must be mock-only for tests. The existing pattern supports this: `BasePhaseHandler.__init__` accepts `llm_router: Any | None = None`. When `None`, `_call_llm` raises `RuntimeError`. For mock testing, inject a mock LLMRouter that returns canned responses.

For the consciousness loop, each substrate `_call_llm` call should:
- In production: use `auxiliary_client.py` resolution chain
- In tests (D3): inject a `MockLLMRouter` that returns deterministic responses
- Per D2: local runtime only, no VPS, no real LLM

---

## 4. Circuit Breakers: The 6 Guards

ADR-063 references safety boundaries and drift triad integration. The existing `src/loops/circuit_breaker.py` provides a 3-layer architecture that maps to 6 circuit breaker instances for the consciousness loop:

### 4.1 Existing 3-Layer Architecture

| Layer | Class | Purpose | Key Parameters |
|-------|-------|---------|----------------|
| L1 | `DependencyCircuitBreaker` | Per-dependency async circuit breaker (CLOSED/OPEN/HALF_OPEN) | `fail_max=5`, `reset_timeout_s=60.0` |
| L2 | `StuckDetector` | Hard-loop (same fingerprint 3x) + soft-stall (velocity < 20%) | `hard_loop_threshold=3`, `soft_stall_velocity_pct=0.20`, `soft_stall_steps=5` |
| L3 | `SafetyGate` | Orchestrator: HARD STOP check -> circuit breaker -> stuck detector | `hard_stop_checker` callable |

### 4.2 Proposed 6 Circuit Breakers for Consciousness Loop

| # | Breaker Name | Guards | Rationale |
|---|-------------|--------|-----------|
| 1 | `llm_call_breaker` | Every LLM self-prompting call | 5 consecutive failures -> OPEN (cascading LLM provider failure) |
| 2 | `memory_write_breaker` | Memory persistence operations | Prevent infinite memory accumulation on write failures |
| 3 | `dream_cycle_breaker` | Dream cycle execution | ADR-063: "counterfactual replay may amplify bias" -- limit dream frequency on repeated failures |
| 4 | `reflection_breaker` | 1h reflection cycle | Prevent reflection storms if LLM returns invalid JSON |
| 5 | `plan_generation_breaker` | Aspiration/plan generation | Prevent plan generation loops on malformed aspiration state |
| 6 | `affect_update_breaker` | Emotion vector updates | ADR-063: "if affect vector drifts maliciously... decision layer may over-correct" |

### 4.3 Failure Modes

| Failure Mode | Circuit Breaker | Behavior |
|-------------|----------------|----------|
| LLM provider down | `llm_call_breaker` | 5 failures -> OPEN, skip substrate for 60s, retry in HALF_OPEN |
| Same thought repeated 3x | StuckDetector (L2) | `hard_loop` detection -> abort substrate cycle, escalate |
| Thought velocity drops 80% | StuckDetector (L2) | `soft_stall` -> retry with backoff |
| Hard stop triggered | SafetyGate (L3) | Immediate abort of all substrates, HMAC-signed broadcast |
| Budget exhausted | IterationBudget | `BudgetExhaustedError` -> graceful substrate shutdown |
| Environment degraded | EnvironmentMonitor | 4-level degradation (0-3) -> reduce substrate intensity |

---

## 5. 7 Substrate Design for guinevere/consciousness/loop.py

### 5.1 Architecture: asyncio.TaskGroup for 7 Substrates

The consciousness loop should use `asyncio.TaskGroup` (Python 3.11+) to run all 7 substrates concurrently. Each substrate is an `asyncio.Task` with its own cadence and failure isolation.

Design sketch (NOT code, for design understanding only):

```python
class ConsciousnessLoop:
    async def run(self):
        async with asyncio.TaskGroup() as tg:
            tg.create_task(self._heartbeat_substrate())        # 1s/10s/30s/60s
            tg.create_task(self._active_cognition_substrate())  # 5m
            tg.create_task(self._reflection_substrate())        # 1h
            tg.create_task(self._plan_generation_substrate())   # 24h self-triggered
            tg.create_task(self._dreaming_substrate())          # ~5% of time
            tg.create_task(self._metacognition_substrate())     # C2 continuous
            tg.create_task(self._emotion_driven_substrate())    # continuous
```

### 5.2 Substrate Cadences (from ADR-063)

| Substrate | Cadence | Source | Notes |
|-----------|---------|--------|-------|
| Heartbeat | 1s (L1S), 10s (graph health), 30s (awareness refresh), 60s (decision-on-idle) | ADR-063 lines 41-46 | P20 inheritance; Q57 "anything without trigger" |
| ActiveCognition | 5m (LLM-light pulse) | ADR-063 line 47 | "I'm thinking X" pulse; audit-14 section 7.3 |
| Reflection | 1h (reflection + memory consolidation + self-improvement) | ADR-063 line 48 | P20 `_heartbeat_1h` inheritance |
| StrategicPlanning | 24h cron + aspiration-weighted selector | ADR-063 lines 61-69 | Self-triggered via aspiration EWMA pull |
| Dreaming | ~5% of runtime (4-6h staggered) | ADR-063 lines 71-81 | Counterfactual replay + generative dream-journal |
| Metacognition (C2) | Continuous | ADR-063 (consciousness-theory-foundations) | Thinking about thinking; quality assessment of each thought |
| EmotionDriven | Continuous (EWMA lambda ~0.3) | ADR-063 lines 95-107 | 6-8 dim affect vector; co-weights all decisions |

### 5.3 Session Hooks

Per the plan requirement for `on_session_start` / `on_session_end` hooks:

The Hermes installed codebase has session hooks in `run_agent.py:544-586`:
- `on_session_start(session_id, **start_context)` -- called when a new session begins
- `on_session_end(session_id, previous_messages)` -- called when session transitions/ends

The consciousness loop should expose:
- `on_session_start`: Initialize affect vector, load self_story, start all 7 substrate tasks
- `on_session_end`: Flush dream journal, persist affect state, checkpoint consciousness state, graceful substrate shutdown

---

## 6. D2/D3 Implications: Local Mock Only

Per operator decisions:
- **D2**: Local runtime only. No VPS deploy, no Discord live, no real LLM. The consciousness loop runs on the developer's local machine only.
- **D3**: Mock-only LLM for tests. All `_call_llm` calls in test mode use `MockLLMRouter` returning deterministic responses.

This means:
1. The consciousness loop file `guinevere/consciousness/loop.py` must be fully functional with a mock LLM router injected
2. No real LLM calls during tests or local development
3. The `auxiliary_client.py` resolution chain is for reference only in P24; the actual mock must be injected via constructor
4. EnvironmentMonitor service checks (Redis, PG, 9Router) will all report unhealthy in local-only mode -- the consciousness loop must handle this gracefully (degradation level 3 -> reduced substrate intensity, not crash)

---

## 7. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| asyncio.TaskGroup propagates CancelledError from any substrate to all others | HIGH | Wrap each substrate in try/except, use separate asyncio.Task (not TaskGroup) with shield() |
| Dream cycle LLM cost in production (4-6h LLM-light) | MEDIUM | IterationBudget with `max_cost_usd` cap per dream cycle; budget.py already supports this |
| Affect vector drift causing malicious decisions (ADR-063 line 132) | HIGH | drift triad 0.68/0.85/0.72 hysteresis; T4 founder gate; affect_update_breaker |
| Counterfactual replay bias amplification (ADR-063 line 134) | MEDIUM | Novel-association seeding from BDI model; explicit counter-via-founder-vote |
| Identity layer irreversibility (ADR-063 line 133) | HIGH | 24h cool-off; per-aspiration EWMA reset on founder 2/2 |
| 37 -> new architecture: valuable SDLC semantics lost | LOW | SDLC patterns (retry, circuit breaker, guardian, budget, recovery, escalation) are all PORTed; only 7 phase-specific handlers are DELETED |
| D2 local-only: consciousness loop untested against real infrastructure | MEDIUM | Mock-only testing is sufficient for P24; production deployment is a separate wave |
| PostgreSQL state_store.py schema mismatch for consciousness fields | MEDIUM | MODIFY disposition; schema migration needed for consciousness-specific columns |

---

## 8. Verdict

**PASS** with conditions.

The src/loops/ 7-phase SDLC state machine is architecturally incompatible with the ADR-063 consciousness loop (different phase model, different purpose), but the **infrastructure around it** is directly reusable: circuit breaker (3-layer, 6 instances), guardian (heartbeat + progress), scheduler (APScheduler cron), escalation (4-tier), concurrency (resource gate), budget (turn/token/cost), retry (exponential backoff + taxonomy), recovery (checkpoint + restart), safety integration (HARD STOP + HMAC), and audit writer (SHA-256 chain). The disposition is DELETE 7 SDLC-specific files, PORT 25 infrastructure files, MODIFY 2, REWRITE 2, REVIEW 3. Self-prompting works via `BasePhaseHandler._call_llm()` + `auxiliary_client.py` resolution chain, with `MockLLMRouter` per D3. The 6 circuit breakers guard LLM calls, memory writes, dream cycles, reflection, plan generation, and affect updates. `asyncio.TaskGroup` (or shielded individual Tasks) runs 7 substrates concurrently with independent cadences from 1s (heartbeat) to 24h (plan cron).
