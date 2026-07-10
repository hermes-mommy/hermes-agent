# Consciousness Loop -- Current Architecture Report

> **Generated**: 2026-07-10 | **Purpose**: P24 replan research input | **Scope**: Full consciousness loop + life_kernel integration

---

## 1. Directory Structure

```
guinevere/consciousness/
├── __init__.py              # Public exports
├── loop.py                  # ConsciousnessLoop class (254 lines)
├── substrates.py            # 7 substrate implementations (381 lines)
├── substrate_registry.py    # Registry binding substrates to loop (60 lines)
├── state.py                 # ConsciousnessState + AffectVector (155 lines)
├── prompts.py               # LLM prompt templates (104 lines)
├── wire.py                  # Wiring into Hermes agent runtime (85 lines)
└── infra/
    ├── __init__.py           # Infra re-exports
    ├── audit_writer.py       # Hash-chained audit trail (199 lines)
    ├── budget.py             # IterationBudget (265 lines)
    ├── reflection.py         # ReflectionExtractor (136 lines)
    └── testing_gate.py       # ADR-029 TestingGate (288 lines)
```

---

## 2. Public Exports (`__init__.py`)

**File**: `guinevere/consciousness/__init__.py` (21 lines)

Exports: `ConsciousnessLoop`, `SUBSTRATE_NAMES`, `AffectVector`, `ConsciousnessState`, `DreamJournalEntry`, `SubstrateStatus`

---

## 3. ConsciousnessLoop Class (`loop.py`)

**File**: `guinevere/consciousness/loop.py` (254 lines)

### 3.1 Module-Level Constants

SUBSTRATE_NAMES = ["heartbeat", "active_cognition", "reflection", "strategic_planning", "dreaming", "metacognition", "emotion_driven"]

### 3.2 Constructor (Lines 63-104)

```python
def __init__(self, llm_router: Any | None = None, settings: Any | None = None) -> None:
```

**State initialized:**
- `self._llm_router` -- Hermes AIAgent (single brain via 9router)
- `self._settings` -- GuinevereConfig (fail-soft if None)
- `self._state` -- ConsciousnessState() instance
- `self._shutdown_event` -- asyncio.Event()
- `self._tasks` -- list[asyncio.Task[None]]()
- `self._session_active` -- False
- `self._prompts` -- reference to guinevere.consciousness.prompts module
- `self._SubstrateStatus` -- SubstrateStatus enum reference
- `self._registry` -- build_registry(self) (dict of name -> bound callable)
- `self._config` -- dict from settings.consciousness (fail-soft)

### 3.3 Properties (Lines 108-122)

| Property | Type | Description |
|---|---|---|
| substrate_names | list[str] | Keys of the registry (always 7) |
| state | ConsciousnessState | Mutable state object |
| is_running | bool | session_active AND NOT shutdown_event.is_set() |

### 3.4 Lifecycle Hooks

**on_session_start(session_id=None)** (Lines 125-142):
- Sets started_at = now UTC
- Generates or accepts session_id
- Sets _session_active = True, clears shutdown event
- Resets all 7 substrate statuses to IDLE

**on_session_end()** (Lines 144-158):
- Sets shutdown event
- Sets _session_active = False
- Logs dream_count and thought_count

### 3.5 run() (Lines 162-227)

```python
async def run(self) -> None:
```

**Flow:**
1. Calls on_session_start() if not already active
2. Spawns one asyncio.Task per substrate via _run_substrate(name, coroutine_fn)
3. Creates a watcher task that asyncio.gather's all substrate tasks
4. Creates a shutdown waiter task on self._shutdown_event.wait()
5. asyncio.wait([shutdown_waiter, watcher], return_when=FIRST_COMPLETED)
6. On cancellation: sets shutdown event, cancels all substrate tasks, gathers them
7. finally: clears task list

### 3.6 _run_substrate() (Lines 231-254)

```python
async def _run_substrate(self, name: str, coroutine_fn: Any) -> None:
```

**Failure isolation pattern:**
- try: await coroutine_fn()
- except CancelledError: raise (propagate for asyncio)
- except Exception: log + set substrate status to FAILED
- finally: log substrate.exited

---

## 4. Substrate Registry (`substrate_registry.py`)

**File**: `guinevere/consciousness/substrate_registry.py` (60 lines)

### 4.1 Registry Map

```python
_SUBSTRATE_FUNCTIONS = {
    "heartbeat": substrate_heartbeat,
    "active_cognition": substrate_active_cognition,
    "reflection": substrate_reflection,
    "strategic_planning": substrate_strategic_planning,
    "dreaming": substrate_dreaming,
    "metacognition": substrate_metacognition,
    "emotion_driven": substrate_emotion_driven,
}
```

### 4.2 build_registry(loop) (Lines 47-60)

Each substrate function is a module-level async function that accepts `(self: ConsciousnessLoop)`. The registry binds the loop instance via `functools.partial` so each entry is a zero-argument awaitable.

---

## 5. Consciousness State (`state.py`)

**File**: `guinevere/consciousness/state.py` (155 lines)

### 5.1 SubstrateStatus Enum

Values: IDLE, RUNNING, COMPLETED, FAILED, DISABLED

### 5.2 AffectVector (Lines 27-63)

```python
@dataclass
class AffectVector:
    valence: float = 0.0      # negative <-> positive
    arousal: float = 0.5      # low <-> high energy
    dominance: float = 0.5    # submissive <-> dominant
    curiosity: float = 0.5    # indifferent <-> exploratory
    confidence: float = 0.5   # uncertain <-> confident
    serenity: float = 0.5     # agitated <-> calm
```

Methods:
- `as_dict()` -> dict[str, float]
- `ewma_update(new_values, lam=0.3)` -- applies `lam * value + (1-lam) * old`

### 5.3 DreamJournalEntry

```python
@dataclass
class DreamJournalEntry:
    timestamp: datetime
    scenario: str
    counterfactual: str
    insight: str
```

### 5.4 ConsciousnessState (Lines 77-155)

```python
@dataclass
class ConsciousnessState:
    affect: AffectVector                    # 6D emotion vector
    self_story: str                         # Default: "I am Guinevere..."
    dream_journal: list[DreamJournalEntry]  # Capped at 50
    substrate_statuses: dict[str, SubstrateStatus]  # 7 entries
    last_thought_at: dict[str, datetime]    # Per-substrate timestamps
    started_at: datetime | None
    session_id: str | None
    _lock: asyncio.Lock                     # Thread-safe mutations
    _thoughts: list[str]                    # Capped at 200
```

Methods:
- record_thought(substrate, thought) -- appends, caps at 200
- recent_thoughts(n=10) -- last N thoughts
- set_substrate_status(name, status)
- add_dream_entry(entry) -- inserts at 0, caps at 50
- snapshot() -- JSON-safe dict

---

## 6. Substrate Implementations (`substrates.py`)

**File**: `guinevere/consciousness/substrates.py` (381 lines)

### 6.1 Shared Helper: _self_prompt() (Lines 46-84)

```python
async def _self_prompt(llm_router, system_msg, user_msg, max_tokens=256) -> str:
```

- Combines system_msg + user_msg into one prompt
- Calls `llm_router.chat(prompt)` -- Hermes AIAgent's chat() method
- Returns str; empty string on failure
- Defensive: handles dict-returning routers (legacy)

### 6.2 All 7 Substrates

| # | Name | Cadence | LLM Calls | What It Does |
|---|---|---|---|---|
| 1 | heartbeat | 1s (10s/30s/60s tiers) | HEARTBEAT_SYSTEM + USER (64 tokens) | Multi-tier liveness, state snapshot, affect check |
| 2 | active_cognition | 5m (300s) | ACTIVE_COGNITION_SYSTEM + USER (128 tokens) | "I am thinking X" reflection pulse |
| 3 | reflection | 1h (3600s) | REFLECTION_SYSTEM + USER (256 tokens) | Memory consolidation from 20 recent thoughts |
| 4 | strategic_planning | 24h (86400s) | PLANNING_SYSTEM + USER (256 tokens) | Aspiration-weighted planning with self_story |
| 5 | dreaming | 4-6h random | DREAMING_SYSTEM + USER (256 tokens) | Counterfactual replay, creates DreamJournalEntry |
| 6 | metacognition | 30s | METACOGNITION_SYSTEM + USER (128 tokens) | Quality assessment of recent 10 thoughts |
| 7 | emotion_driven | 60s | EMOTION_SYSTEM + USER (128 tokens) | EWMA affect vector update (lam=0.3) |

All substrates share the same pattern:
1. Set status to RUNNING
2. Enter while-not-shutdown loop
3. Call _self_prompt() with substrate-specific prompts
4. Record thought via state.record_thought()
5. asyncio.sleep(interval)
6. finally: _safe_finish() resets to IDLE if still RUNNING

---

## 7. Prompt Templates (`prompts.py`)

**File**: `guinevere/consciousness/prompts.py` (104 lines)

7 system/user prompt pairs for the 7 substrates. Each substrate has:
- A SYSTEM prompt defining the role
- A USER prompt with format variables (affect, thoughts, etc.)

---

## 8. Wiring into Agent Runtime (`wire.py`)

**File**: `guinevere/consciousness/wire.py` (85 lines)

Called from agent_init.py Group G (line 1764-1769).

**Flow:**
1. Read agent._guinevere_settings -> no settings? skip
2. Read settings.consciousness -> no config? skip
3. Check consciousness_cfg.enabled -> disabled? skip
4. Get llm_router from agent._llm_router or agent.llm_router
5. Construct ConsciousnessLoop(llm_router=llm_router, settings=settings)
6. Call loop.on_session_start()
7. asyncio.create_task(loop.run(), name="consciousness-loop")
8. Attach to agent: agent._consciousness_loop, agent._consciousness_task
9. Attach shutdown hook: agent._consciousness_stop

---

## 9. HTTP Server Integration (`server.py`)

**File**: `guinevere/http/server.py` (237 lines)

### 9.1 Consciousness Loop in _lifespan() (Lines 117-154)

```python
from guinevere.consciousness import ConsciousnessLoop
from run_agent import AIAgent

_consciousness_brain = AIAgent(
    base_url="http://localhost:20128/v1",
    api_key="sk-noauth",
    provider="custom",
    model="guinevere",
    enabled_toolsets=[],
)
_consciousness_loop = ConsciousnessLoop(
    llm_router=_consciousness_brain,
    settings=settings,
)
_consciousness_loop.on_session_start()
consciousness_task = tg.create_task(_consciousness_loop.run(), name="m3-consciousness")
app.state.consciousness_loop = _consciousness_loop
```

**Key details:**
- Brain = dedicated AIAgent targeting localhost:20128/v1 (9router local proxy)
- provider="custom", model="guinevere", api_key="sk-noauth"
- No toolsets enabled for consciousness brain
- Runs inside asyncio.TaskGroup with M16 surveillance placeholder
- Fail-soft: on failure, falls back to _noop_placeholder()

### 9.2 Shutdown (Lines 175-188)

```python
_shutdown_event.set()
_cl = getattr(app.state, "consciousness_loop", None)
if _cl is not None:
    _cl.on_session_end()
consciousness_task.cancel()
```

---

## 10. Config Model

**File**: `guinevere/config/models.py` (Lines 95-106)

```python
class ConsciousnessConfig(BaseModel):
    enabled: bool = False  # DISABLED by default
    heartbeat_intervals: list[int] = [60, 300, 900]
    dreaming_pct: float = 0.05
    substrates: list[str] = ["short_term", "long_term", "emotional"]
```

**NOTE:** Config model is NOT consumed by the actual implementation. The loop uses hardcoded ADR-063 values. The substrates list in config differs from the actual 7 substrates.

---

## 11. Infrastructure Sub-Package (infra/)

### 11.1 AuditWriter (199 lines)
- Hash-chained audit trail (SHA-256) to PostgreSQL audit.audit_trail
- write_event() -> AuditEvent, verify_chain() -> bool
- P19 multi-project via chain_version=2

### 11.2 IterationBudget (265 lines)
- Thread-safe turn/token/cost limiting
- Parent=90 turns/500K tokens/$5.00; subagent=50/250K/$2.50
- Atomic triple-limit check under asyncio.Lock
- Parent budget cascade

### 11.3 ReflectionExtractor (136 lines)
- LLM-powered lesson extraction from loop artifacts
- Returns ReflectionEntry with outcome + lessons

### 11.4 TestingGate (288 lines)
- ADR-029 compliance gate for self-modification
- Runs pytest in subprocess, parses output
- Returns GateDecision (approved + reason)

**None of these are wired into the consciousness loop itself. They are for M10/W14 self-modification pipeline.**

---

## 12. Life Kernel Integration

### 12.1 HeartbeatService (heartbeat.py, 740 lines)

The Life Kernel has its OWN heartbeat -- separate from consciousness loop.

| Interval | Duration | Purpose |
|---|---|---|
| L1S | 1s | Liveness + HARD STOP detection (Redis) |
| L10S | 10s | Graph health check |
| L30S | 30s | Awareness refresh (sensor poll) |
| L60S | 60s | Decision trigger (graph.ainvoke) + dashboard |
| L5M | 5m | Deep scan |
| L1H | 1h | Reflection + self-improvement |

Constructor takes: graph (LangGraph), redis_client, checkpointer, discord_publisher, hermes_brain, log_channel, project_id.

### 12.2 LangGraph StateGraph (graph.py, 1115 lines)

4-node cyclic graph: observe -> decide -> act/reflect/idle -> END

- observe_node: P16 KG + P18 memory recall
- decide_node: Priority engine (HARD_STOP > KEEP_ALIVE > ... > EXPLORE)
- act_node: Highest-priority goal execution
- reflect_node: Audit + journal writing
- idle_node: Memory-driven self-directed tasks

LLM-enriched variants when hermes_brain provided: _make_brain_decide, _make_brain_act, _make_brain_idle

### 12.3 HermesBrain (hermes_brain.py, 464 lines)

```python
class HermesBrain:
    async def think(user_message, system_prompt, ...) -> dict
    async def think_with_tools(...) -> dict
```

Wraps AIAgent.run_conversation() via asyncio.to_thread(). 30s hard timeout. Fallback response on failure.

---

## 13. Dual Architecture Summary

| Aspect | Consciousness Loop | Life Kernel Heartbeat |
|---|---|---|
| Location | guinevere/consciousness/ | guinevere/life_kernel/heartbeat.py |
| ADR | ADR-063 (7-substrate) | P5+P20 architecture benchmark |
| Brain | AIAgent via chat() | HermesBrain via run_conversation() |
| Graph | None (flat async tasks) | LangGraph StateGraph |
| Persistence | In-memory only | PostgreSQL + Redis checkpoints |
| Safety | No HARD STOP | Redis HARD STOP flag |
| Memory | Thought stream (200 cap) | P16 KG + P18 memory adapters |

---

## 14. Key Observations for P24 Replan

1. **Two parallel autonomous systems** with overlapping concerns (heartbeat, reflection, planning).
2. **Different LLM interfaces**: chat() vs run_conversation().
3. **No persistence** in consciousness loop -- all state lost on restart.
4. **Config model mismatch** -- ConsciousnessConfig not consumed by implementation.
5. **No LangGraph integration** in consciousness loop.
6. **Dual wiring** -- HTTP server and agent_init both wire the loop.
7. **Infra sub-package not wired** into the loop itself.
8. **Good failure isolation** per substrate.
9. **No inter-substrate communication** beyond shared state.
10. **No HARD STOP** in consciousness loop.

---

## 15. File Inventory (Absolute Paths)

| File | Lines |
|---|---|
| C:/Users/faizz/hermes-agent/guinevere/consciousness/__init__.py | 21 |
| C:/Users/faizz/hermes-agent/guinevere/consciousness/loop.py | 254 |
| C:/Users/faizz/hermes-agent/guinevere/consciousness/substrates.py | 381 |
| C:/Users/faizz/hermes-agent/guinevere/consciousness/substrate_registry.py | 60 |
| C:/Users/faizz/hermes-agent/guinevere/consciousness/state.py | 155 |
| C:/Users/faizz/hermes-agent/guinevere/consciousness/prompts.py | 104 |
| C:/Users/faizz/hermes-agent/guinevere/consciousness/wire.py | 85 |
| C:/Users/faizz/hermes-agent/guinevere/consciousness/infra/__init__.py | 37 |
| C:/Users/faizz/hermes-agent/guinevere/consciousness/infra/audit_writer.py | 199 |
| C:/Users/faizz/hermes-agent/guinevere/consciousness/infra/budget.py | 265 |
| C:/Users/faizz/hermes-agent/guinevere/consciousness/infra/reflection.py | 136 |
| C:/Users/faizz/hermes-agent/guinevere/consciousness/infra/testing_gate.py | 288 |
| C:/Users/faizz/hermes-agent/guinevere/http/server.py | 237 |
| C:/Users/faizz/hermes-agent/guinevere/config/models.py | 190 |
| C:/Users/faizz/hermes-agent/guinevere/life_kernel/heartbeat.py | 740 |
| C:/Users/faizz/hermes-agent/guinevere/life_kernel/graph.py | 1115 |
| C:/Users/faizz/hermes-agent/guinevere/life_kernel/hermes_brain.py | 464 |
| C:/Users/faizz/hermes-agent/guinevere/life_kernel/heartbeat_d1_native_unused.py | 414 |
| C:/Users/faizz/hermes-agent/agent/agent_init.py | 1789 |
