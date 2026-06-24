# Memory / World-Model Integration Research Report

**Agent:** memory/world-model integration researcher  
**Date:** 2026-06-24  
**Context:** P20 Living Autonomy Kernel CONTINUATION pass — design concrete integration of real Knowledge Graph and Memory recall into the life_kernel observe cycle.

---

## 1. Executive Summary

The life_kernel currently runs with **hardcoded placeholders** for both P16 (Knowledge Graph) and P18 (Memory) recall adapters. `observe_node` sets `world_model_available = False` unconditionally and attempts to build a `DecisionContext` through `state["kg_adapter"]` / `state["memory_adapter"]` that are **never injected** by `core/main.py`. When injection is absent, decision_context degrades to a static no-signal dict. Meanwhile, the real substrates — `RecallContextAssembler` (KG) and `recall_memories()` (Memory) — are fully production-ready with hybrid RRF fusion, classification ceilings, DNR safety, token budgets, and FSRS/consent support. They are already imported and used elsewhere in the codebase but have never been wired into the life_kernel graph.

This report provides a **file-by-file, function-level integration design** that: (1) replaces the p16/p18 placeholders with real adapter implementations, (2) injects adapters into the graph via `core/main.py` using the async session-factory pattern already established for surveillance, (3) propagates recalled concepts and memories into the HermesBrain decision/act/idle prompts so autonomy is memory-driven (AC-LIFE-005), and (4) maintains graceful degradation — failed recall never crashes the kernel. No changes to HARD STOP, no raw `LLMRouter.chat`, no unsafe side-effects.

**Key metrics from the real substrates:**

| Substrate | Module | Ready since | Uses |
|---|---|---|---|
| KG query engine | `src.knowledge_graph.query.engine.KGQueryEngine` | P16-003 | RCTE traversal, entity search, PPR, consent-aware |
| KG RRF fusion | `src.knowledge_graph.query.rrf_fusion.KGRRFFusion` | P16-003 | 4th signal, non-breaking fallback |
| KG context assembler | `src.knowledge_graph.query.context.RecallContextAssembler` | P16-003 | end-to-end pipeline |
| Memory recall | `src.memory.read_pipeline.recall_memories` | P3-010 | hybrid ranking, classification ceiling, DNR, token budget |
| Embedding | `src.memory.embeddings.EmbeddingService.aembed` | P3-005 | 9Router-native, 1536-dim, privacy-guarded |

---

## 2. Current State Evidence

### 2.1 `p16_adapter.py` — full placeholder

File: `C:/Users/faizz/guinevere/src/life_kernel/p16_adapter.py`

Lines 39-99 define `KGRecallAdapter.recall()` which returns deterministic mock concepts regardless of input. Key lines:

```
# Line 61: query = str(context.get("query", context.get("content", ""))).lower()
# Lines 63-74: returns hardcoded ["autonomy_kernel", "decision_context"]
# Line 94-98: return dict includes "_placeholder": True
```

The docstring states (line 4-7): *"Real KG traversal is intentionally stubbed; wiring to src.knowledge_graph is deferred to a later milestone."* That milestone is LK-010.

### 2.2 `p18_adapter.py` — full placeholder

File: `C:/Users/faizz/guinevere/src/life_kernel/p18_adapter.py`

Lines 40-102 define `MemoryRecallAdapter.recall()` returning same two mock memories regardless of input. Key lines:

```
# Line 66-75: hardcoded ["Previous observation contained idle task generation.", "Kernel cycled through observe -> decide -> act -> reflect."]
# Line 97-101: return dict includes "_placeholder": True
```

Docstring says (line 4-7): *"Real memory recall is intentionally stubbed; wiring to src.memory is deferred to a later milestone."*

### 2.3 `decision_context.py` — calls stubs, but call never happens

File: `C:/Users/faizz/guinevere/src/life_kernel/decision_context.py`

Lines 47-99 define `DecisionContextBuilder.build()`. It:

- Reads latest observation from state (line 61-67).
- Calls `self.kg_adapter.recall(seed_context)` and `self.memory_adapter.recall(seed_context)` concurrently (lines 69-70).
- Assembles enriched_context dict with top_concepts + top_memories.

This builder works correctly — but is **only called** inside `observe_node` when BOTH `kg_adapter` and `memory_adapter` are truthy in state (graph.py line 161-162). Since they are never injected, the builder never executes.

### 2.4 `graph.py` — `world_model_available` hardcoded False; adapters never injected

File: `C:/Users/faizz/guinevere/src/life_kernel/graph.py`

**observe_node (lines 97-172):**

Line 129: `world_model_available = False  # Placeholder for P18 integration`

Lines 159-170:
```python
try:
    kg_adapter = state.get("kg_adapter")  # injected via config/context
    memory_adapter = state.get("memory_adapter")
    if kg_adapter and memory_adapter:
        from src.life_kernel.decision_context import DecisionContextBuilder
        builder = DecisionContextBuilder(kg_adapter=kg_adapter, memory_adapter=memory_adapter)
        decision_context = await builder.build(state)
    else:
        decision_context = {"p16_available": False, "p18_available": False, "kg_context": None, "memory_context": None}
except Exception:
    decision_context = {"p16_available": False, "p18_available": False, "kg_context": None, "memory_context": None}
```

Both `kg_adapter` and `memory_adapter` are read from state but **no code in the repo ever sets them**. The `else` branch always executes.

**idle_node (lines 435-504):**

Line 467: `task_options = [...]` with exactly 3 hardcoded strings, chosen via `random.choice`. No memory-driven generation.

**create_life_mind_graph (line 642-761):**

Signature: `def create_life_mind_graph(checkpointer=None, hermes_brain=None)` — no adapter parameters.

### 2.5 `state.py` — NotRequired fields present but never populated

File: `C:/Users/faizz/guinevere/src/life_kernel/state.py`

Lines 207-211:
```python
kg_adapter: NotRequired[Any]
memory_adapter: NotRequired[Any]
```

Lines 214-219 — P20 dashboard fields exist:
```python
last_autonomous_decision: NotRequired[str]
last_action_result: NotRequired[str]
next_planned_action: NotRequired[str]
memory_status: NotRequired[str]
uptime_start: NotRequired[str]
```

`memory_status` is a string placeholder that nothing sets. No fields exist for `recalled_concepts`, `recalled_memories`, or `world_model_status`.

### 2.6 Real substrate: KG Query Engine + RecallContextAssembler

File: `C:/Users/faizz/guinevere/src/knowledge_graph/query/engine.py` — `KGQueryEngine`

- Constructor (line 261): `KGQueryEngine(session_factory: SessionFactory, max_hops=3, max_results=50)`.
- Methods: `traverse(seed_ids, max_hops, consent_token)` — RCTE graph walk (line 298); `search_entities(query, limit)` — ILIKE entity search (line 848); `find_path(src, dst, max_hops)` — BFS path find (line 523).
- All methods return typed frozen dataclasses. Every public method opens its own session via injected `session_factory`.

File: `C:/Users/faizz/guinevere/src/knowledge_graph/query/context.py` — `RecallContextAssembler`

- Constructor (line 170): `RecallContextAssembler(query_engine, ppr, rrf_fusion, token_budget)` — all four required, None refused.
- `.assemble(query_text, existing_recall_results, seed_entity_ids=None, token_budget=1000, traversal_max_hops=3)` (line 195). Returns `RecallContext` with `enhanced_results`, `graph_context`, `seed_entities`, `ppr_scores`, `graph_signal_active`.
- Fails with `KGQueryError` on non-KG exceptions; pure KG errors propagate; the assembler never swallows safety violations.
- Non-breaking: returns `enhanced_results=input` unchanged when KG contributes nothing.

File: `C:/Users/faizz/guinevere/src/knowledge_graph/query/rrf_fusion.py` — `KGRRFFusion`

- Constructor (line 179): `KGRRFFusion(query_engine, ppr)`.
- `compute_graph_scores(query_text, seed_entity_ids=None, top_k=60)` returns `{fact_id: score}` (line 192).
- `fuse_with_existing(existing_results, graph_scores)` adds KG contribution to combined_score (line 377). Non-breaking.

File: `C:/Users/faizz/guinevere/src/knowledge_graph/query/ppr.py` — `PersonalizedPageRank`

- Constructor: `PersonalizedPageRank(query_engine)`. Method: `.compute(seed_ids, top_k=50)`.

File: `C:/Users/faizz/guinevere/src/knowledge_graph/query/token_budget.py` — `KGTokenBudgetManager`

- Constructor: `KGTokenBudgetManager(query_engine)`. Method: `.format_graph_context_sync(traversal_results, ppr_results, max_tokens)`.

### 2.7 Real substrate: Memory recall pipeline

File: `C:/Users/faizz/guinevere/src/memory/read_pipeline.py` — `recall_memories`

Signature (line 755):
```python
async def recall_memories(
    session: RecallSession,
    query_text: str,
    limit: int = 20,
    *,
    exclude_dnr: bool = True,
    safe_mode: bool = False,
    principal: str = "guinevere_core",
    embedding_service: EmbeddingClient | None = None,
    token_budget: int = DEFAULT_TOKEN_BUDGET,
    kg_enabled: bool = True,
    fsrs_enabled: bool = False,
) -> RecallResults:
```

Requires an open `AsyncSession` (sqlalchemy). Returns `list[dict]` with keys: `id`, `safe_content`, `classification`, `importance`, `created_at`, `combined_score`, `is_summarized`.

Safety gates:
- `exclude_dnr=True` filters do-not-recall episodes (SQL WHERE).
- `safe_mode=True` redacts Critical/Restricted/Confidential raw content.
- `principal` determines classification ceiling (`guinevere_core` defaults to Critical).
- `embedding_service` for vector cosine similarity (falls back gracefully to FTS-only).
- `kg_enabled=True` adds 4th KG RRF signal (falls back to 3-signal on KG unavailability).
- `token_budget=4000` trims excess results.

File: `C:/Users/faizz/guinevere/src/memory/embeddings.py` — `EmbeddingService.aembed`

```python
async def aembed(self, text, classification="Restricted", *, sanitized_summary=None) -> list[float]:
```

File: `C:/Users/faizz/guinevere/src/memory/db.py` — `get_async_session`

```python
@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    ...
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### 2.8 Session factory pattern from `core/main.py`

File: `C:/Users/faizz/guinevere/src/core/main.py`

Lines 149-152:
```python
_engine = _create_async_engine(_db_url, pool_size=2, pool_pre_ping=True)
_session_factory = _async_sessionmaker(
    _engine, class_=_AsyncSession, expire_on_commit=False,
)
```

This factory is used by `SurveillanceConsumer` and the KG ingestion cron. The same pattern should be used for the life_kernel adapters. Currently the life_kernel block (line 203+) does **not** create or receive a session factory.

---

## 3. Gap Table

| ID | Severity | Title | Current | Required | Files | Vision Ref |
|---|---|---|---|---|---|---|
| gap-p16-stub | critical | KGRecallAdapter returns mock data | `src/life_kernel/p16_adapter.py:93-99` returns `{"concepts": [mock], "_placeholder": True}` | Integrate with `RecallContextAssembler`; return real KG concepts; report `_degraded` on failure | `p16_adapter.py`, `graph.py` | LK-010, AC-LIFE-005 |
| gap-p18-stub | critical | MemoryRecallAdapter returns mock data | `src/life_kernel/p18_adapter.py:96-102` returns `{"memories": [mock], "_placeholder": True}` | Integrate with `recall_memories()`; return real episodic memories; report `_degraded` on failure | `p18_adapter.py`, `graph.py` | LK-010, AC-LIFE-005 |
| gap-world-model-flag | critical | `world_model_available` hardcoded False | `src/life_kernel/graph.py:129` | Compute from adapter availability + health; set `world_model_status` | `graph.py`, `state.py` | V-003 |
| gap-adapter-injection | critical | kg_adapter/memory_adapter never injected into state | `src/life_kernel/graph.py:160-162` reads `.get("kg_adapter")` — always None | Inject adapters at `create_life_mind_graph()` construction; pass from `core/main.py` | `graph.py`, `core/main.py` | LK-010 |
| gap-session-lifecycle | high | No DB session factory integration in life_kernel | `core/main.py:216-227` does not create or pass a session factory to `create_life_mind_graph` | Build/reuse async session factory; pass to adapter constructors in `core/main.py` lifespan | `core/main.py` | LK-010 |
| gap-brain-feed | high | HermesBrain prompts lack recall context | `graph.py:548-552` `user_msg` only has goals/commitments/concerns/observations | Inject `recalled_concepts` and `recalled_memories` into decide/act/idle brain prompts | `graph.py` `_make_brain_decide`, `_make_brain_act`, `_make_brain_idle` | AC-LIFE-005 |
| gap-idle-random | medium | idle_node picks from 3 hardcoded strings | `src/life_kernel/graph.py:463-468` `random.choice(task_options)` | Let brain propose memory-driven agenda; fall back to static but include recall context | `graph.py` `_make_brain_idle` | V-003, AC-LIFE-005 |
| gap-state-fields | medium | No `recalled_concepts`/`recalled_memories`/`world_model_status` in state | `src/life_kernel/state.py:214-219` only has `last_autonomous_decision`, `action_result`, `memory_status` | Add new NotRequired fields for recall outputs and status | `state.py` | AC-LIFE-005 |
| gap-heartbeat-stubs | low | _heartbeat_10s/_heartbeat_30s/_heartbeat_5m/_heartbeat_1h are if-pass stubs | `heartbeat.py:386-549`: each logs `"heartbeat_XXs_YY"` then `# Placeholder for future` | (Out of scope for this research, listed for awareness; P19 heartbeat integration) | `heartbeat.py` | LK-000 |

---

## 4. Concrete Integration Design

### 4.1 New state fields (`src/life_kernel/state.py`)

Add after line 218 (the existing `memory_status` field):

```python
    # P20 integration: recall outputs for memory-driven autonomy (AC-LIFE-005)
    recalled_concepts: NotRequired[list[dict[str, Any]]]
    """Top KG concepts recalled during the last observe cycle. Each dict has
    keys: ``name``, ``relevance``, ``source``, ``entity_id``."""
    recalled_memories: NotRequired[list[dict[str, Any]]]
    """Top episodic memories recalled during the last observe cycle. Each dict
    has keys: ``content``, ``relevance``, ``id``, ``classification``."""
    world_model_status: NotRequired[str]
    """One of ``"available"``, ``"degraded"``, ``"unavailable"`` reflecting
    the composite health of KG + memory recall adapters."""
```

### 4.2 Rewrite `KGRecallAdapter` (`src/life_kernel/p16_adapter.py`)

Replace the stub with a class wrapping `RecallContextAssembler`:

```python
class KGRecallAdapter:
    """Real P16 KG recall adapter using ``RecallContextAssembler``.

    Creates and owns a lightweight stateless handle to the KG query
    pipeline.  Each call to ``recall()`` opens/closes a DB session
    through the assembler's internal session factory.  Degrades
    gracefully on any failure: returns empty concepts with
    ``_degraded=True``, never raises.
    """

    def __init__(self, assembler: RecallContextAssembler) -> None:
        self._assembler = assembler

    async def recall(self, context: dict[str, Any]) -> dict[str, Any]:
        query = str(context.get("query", context.get("content", ""))).strip()
        if not query:
            return {"concepts": [], "count": 0, "_degraded": False,
                    "_placeholder": False, "_timestamp": datetime.now().isoformat()}
        try:
            kg_ctx = await self._assembler.assemble(
                query_text=query,
                existing_recall_results=[],
                token_budget=1000,
                traversal_max_hops=3,
            )
        except Exception as exc:
            logger.warning("kg_recall_degraded", error_type=type(exc).__name__)
            return {"concepts": [], "count": 0, "_degraded": True,
                    "_timestamp": datetime.now().isoformat(), "error": type(exc).__name__}

        concepts = [
            {
                "name": s.get("display_name", ""),
                "relevance": float(s.get("relevance", 0.0)),
                "entity_id": s.get("entity_id", ""),
                "entity_type": s.get("entity_type", ""),
                "source": "kg",
            }
            for s in (kg_ctx.seed_entities or [])
        ]
        return {
            "concepts": concepts,
            "count": len(concepts),
            "graph_context": kg_ctx.graph_context or "",
            "graph_signal_active": kg_ctx.graph_signal_active,
            "_degraded": False,
            "_placeholder": False,
            "_timestamp": datetime.now().isoformat(),
        }
```

No change to the constructor signature `__init__(self, kg_client=None)` backwards compat? The stub accepts `kg_client` which is unused. We can keep the old signature as deprecated or break it. Since this is the research, we recommend dropping `kg_client` and accepting `assembler`. The caller is `core/main.py` which constructs adapters fresh.

### 4.3 Rewrite `MemoryRecallAdapter` (`src/life_kernel/p18_adapter.py`)

```python
class MemoryRecallAdapter:
    """Real P18 memory recall adapter using ``recall_memories()``.

    Each ``recall()`` opens an async session via the injected
    ``session_factory`` and passes it to the read pipeline.  The
    pipeline handles classification ceilings, DNR filtering, token
    budget, and safe-mode redaction.  Degrades gracefully: returns
    empty memories with ``_degraded=True``, never raises.
    """

    def __init__(
        self,
        session_factory: Callable[[], AsyncContextManager[Any]],
        embedding_service: Any | None = None,
        principal: str = "guinevere_core",
        safe_mode: bool = False,
        token_budget: int = 4000,
    ) -> None:
        self._session_factory = session_factory
        self._embedding_service = embedding_service
        self._principal = principal
        self._safe_mode = safe_mode
        self._token_budget = token_budget

    async def recall(self, context: dict[str, Any]) -> dict[str, Any]:
        query = str(context.get("query", context.get("content", ""))).strip()
        if not query:
            return {"memories": [], "count": 0, "_degraded": False,
                    "_placeholder": False, "_timestamp": datetime.now().isoformat()}
        try:
            async with self._session_factory() as session:
                results = await recall_memories(
                    session=session,
                    query_text=query,
                    limit=10,
                    exclude_dnr=True,
                    safe_mode=self._safe_mode,
                    principal=self._principal,
                    embedding_service=self._embedding_service,
                    kg_enabled=False,  # KG augmentation is handled by the KG adapter separately
                    token_budget=self._token_budget,
                )
        except Exception as exc:
            logger.warning("memory_recall_degraded", error_type=type(exc).__name__)
            return {"memories": [], "count": 0, "_degraded": True,
                    "_timestamp": datetime.now().isoformat(), "error": type(exc).__name__}

        memories = [
            {
                "content": r.get("safe_content", ""),
                "relevance": float(r.get("combined_score", 0.0) or 0.0),
                "id": str(r.get("id", "")),
                "classification": str(r.get("classification", "")),
            }
            for r in (results or [])
        ]
        return {
            "memories": memories,
            "count": len(memories),
            "_degraded": False,
            "_placeholder": False,
            "_timestamp": datetime.now().isoformat(),
        }
```

### 4.4 Modify `create_life_mind_graph` to accept adapters (`src/life_kernel/graph.py`)

Change the function signature (around line 639):

```python
def create_life_mind_graph(
    checkpointer: Any | None = None,
    hermes_brain: Any | None = None,
    kg_adapter: Any | None = None,
    memory_adapter: Any | None = None,
) -> Any:
```

Create a closure that wraps `observe_node` with access to the adapters:

```python
_observe_fn = _make_observe(kg_adapter, memory_adapter)

def _make_observe(kg_adapter, memory_adapter):
    async def observe(state):
        # ... same body as current observe_node but use injected adapters
        ...
    return observe
```

Replace `world_model_available = False` with:
```python
world_model_available = kg_adapter is not None and memory_adapter is not None
```

Replace the adapter-injection block (lines 159-170) with the injected adapters:

```python
# Build decision context from injected adapters (LK-010)
try:
    if kg_adapter and memory_adapter:
        builder = DecisionContextBuilder(kg_adapter=kg_adapter, memory_adapter=memory_adapter)
        decision_context = await builder.build(state)
        recalled_concepts = decision_context.get("kg_concepts", [])
        recalled_memories = decision_context.get("memory_signals", [])
        world_model_status = "available"
    else:
        decision_context = {"p16_available": False, "p18_available": False}
        recalled_concepts = []
        recalled_memories = []
        world_model_status = "unavailable"
except Exception as exc:
    logger.warning("observe_decision_context_failed", error_type=type(exc).__name__)
    decision_context = {"p16_available": False, "p18_available": False}
    recalled_concepts = []
    recalled_memories = []
    world_model_status = "degraded"
```

Return:
```python
return {
    "observations": updated_observations,
    "decision_context": decision_context,
    "recalled_concepts": recalled_concepts,
    "recalled_memories": recalled_memories,
    "world_model_status": world_model_status,
}
```

At the bottom, register the wrapped observe node instead of raw:

```python
builder.add_node("observe", _observe_fn)
```

### 4.5 Update brain prompts with recall context (`src/life_kernel/graph.py`)

Add a helper:
```python
def _format_recalls(concepts, memories, max_items=3):
    """Return string snippets for brain prompts."""
    parts = []
    for c in (concepts or [])[:max_items]:
        parts.append(f"  - concept: {c.get('name', '?')} (relevance {c.get('relevance', 0):.2f})")
    for m in (memories or [])[:max_items]:
        content = m.get("content", "")[:120]
        parts.append(f"  - memory: {content}... (score {m.get('relevance', 0):.2f})")
    return "\n".join(parts) or "  (none)"
```

In `_make_brain_decide`:
```python
recalled_concepts = state.get("recalled_concepts", [])
recalled_memories = state.get("recalled_memories", [])
user_msg = (
    f"Goals: {goals}. Commitments: {commitments}. Concerns: {concerns}.\n"
    f"Recalled context:\n{_format_recalls(recalled_concepts, recalled_memories)}\n"
    f"Observations: {len(state.get('observations', []))}."
    f"Cycle: {state.get('cycle_count', 0)}. "
    "Decide the next phase: act, reflect, idle, or observe."
)
```

In `_make_brain_act`:
```python
user_msg = (
    f"Goal: {top.get('description', '?')} (priority={top.get('priority')}). "
    f"Recalled context:\n{_format_recalls(state.get('recalled_concepts', []), state.get('recalled_memories', []))}\n"
    "Propose ONE concrete next action in a single short sentence."
)
```

In `_make_brain_idle`:
```python
user_msg = (
    "The operator is silent and there is no pending work.\n"
    f"Recalled context:\n{_format_recalls(state.get('recalled_concepts', []), state.get('recalled_memories', []))}\n"
    "Propose ONE self-directed agenda item to stay usefully alive. "
    "Reply with a short label and a one-sentence description."
)
```

### 4.6 Wire adapters in `core/main.py`

Inside the P20 block (around line 203), before `create_life_mind_graph`:

```python
# ---- Build adapters from shared session factory ----
# If _session_factory was not created (surveillance block may have failed),
# create a standalone one for the life kernel.
if "_session_factory" not in dir():
    _db_url = os.environ.get("DATABASE_URL", "postgresql+asyncpg://guinevere_core@localhost:5433/guinevere")
    _life_engine = _create_async_engine(_db_url, pool_size=2, pool_pre_ping=True)
    _session_factory = _async_sessionmaker(
        _life_engine, class_=_AsyncSession, expire_on_commit=False,
    )

# Embedding service (9Router-native, privacy-guarded)
try:
    from src.memory import EmbeddingService
    _embedding_svc = EmbeddingService()
except Exception:
    _embedding_svc = None
    logger.warning("embedding_service_init_failed")

# KG pipeline adapters
try:
    from src.knowledge_graph.query import (
        KGQueryEngine, PersonalizedPageRank, KGRRFFusion,
        KGTokenBudgetManager, RecallContextAssembler,
    )
    _kg_engine = KGQueryEngine(_session_factory, max_hops=3, max_results=50)
    _kg_ppr = PersonalizedPageRank(_kg_engine)
    _kg_rrf = KGRRFFusion(_kg_engine, _kg_ppr)
    _kg_budget = KGTokenBudgetManager(_kg_engine)
    _kg_assembler = RecallContextAssembler(_kg_engine, _kg_ppr, _kg_rrf, _kg_budget)
    kg_adapter = KGRecallAdapter(assembler=_kg_assembler)
    logger.info("kg_adapter_initialized")
except Exception as kg_adapter_err:
    kg_adapter = None
    logger.warning("kg_adapter_init_failed", error=str(kg_adapter_err))

# Memory recall adapter
try:
    memory_adapter = MemoryRecallAdapter(
        session_factory=_session_factory,
        embedding_service=_embedding_svc,
        principal="guinevere_core",
        safe_mode=False,
        token_budget=4000,
    )
    logger.info("memory_adapter_initialized")
except Exception as mem_adapter_err:
    memory_adapter = None
    logger.warning("memory_adapter_init_failed", error=str(mem_adapter_err))

# Create graph with adapters
graph = create_life_mind_graph(
    checkpointer=checkpointer,
    hermes_brain=hermes_brain,
    kg_adapter=kg_adapter,
    memory_adapter=memory_adapter,
)
```

### 4.7 Safety considerations for recall_memories parameters

| Parameter | Value | Rationale |
|---|---|---|
| `principal` | `"guinevere_core"` | System-internal principal — may read up to Critical classification. |
| `exclude_dnr` | `True` | DNR episodes are never surfaced to the autonomy kernel. |
| `safe_mode` | `False` (or `True` for stricter) | `False` allows raw memory content into brain prompts. Since prompts are not sent to Discord (only metadata is), this is acceptable. Recommend enforcing safe_mode redaction if any content path goes to dashboard/logs. Current dashboard only displays `last_autonomous_decision`, `next_planned_action`, `act_count` — no raw memory content. Safe to leave `False`. |
| `kg_enabled` | `False` in memory adapter | KG augmentation is handled separately by the `KGRecallAdapter`. Setting both would double the 4th RRF signal. |
| `embedding_service` | `EmbeddingService` (or `None`) | Vector search improves recall relevance. `None` falls back to FTS-only (keyword). |
| `token_budget` | `4000` | Sufficient for top-10 memory items (~400 chars each) with room to spare. |

---

## 5. Risks

| Risk | Mitigation |
|---|---|
| **Checkpointer serialization failure**: If adapter objects are accidentally stored in checkpointed state (LifeMindState fields), the Postgres checkpointer may fail to serialize the adapter (non-picklable objects like session factories). | Use closure injection (recommended above) — adapters never live in state. The state fields `kg_adapter`/`memory_adapter` can be left as NotRequired and never populated. Alternatively, if state injection is preferred, ensure adapters are lightweight dataclasses with only a callable factory (function references are not JSON-serializable but are pickleable). **Recommended: closure injection, no state storage.** |
| **DB/embedding outage stalls observe_node**: A downed database or embedding API timeout blocks the observe cycle. | Each adapter wraps ALL external I/O in try/except and returns `_degraded=True`. The observe_node wraps the entire adapter+decision block in try/except (current code lines 159-170 already do this). The kernel continues with empty context. |
| **Token bloat from feeding too many concepts/memories**: Large recall results could exceed the brain's context window or incur high cost. | `_format_recalls` caps at `max_items=3` per supply. `recall_memories` enforces a hard token budget (default 4000). `KGTokenBudgetManager` enforces 1000-token ceiling per query. All three layers of truncation prevent overflow. |
| **Sensitive memory content leaked to Discord dashboard/logs**: The lifecycle log currently emits only phase/acts/decision/next_action (heartbeat.py:510-513). If future code includes raw memory context, sensitive content could be written to Discord. | Dashboard: currently metadata-only. Lifecycle log: throttled (1/5 min), only structured metadata. **Hard rule**: never log `safe_content` or `graph_context` to Discord. Add a note in code review checklist. |
| **KG consent token mismatch**: If edges have `consent_token` set but the kernel's KG query passes a different token, the traversal returns empty results. | KG adapters should use `consent_token=None` (system-internal) to bypass consent filtering, matching the behaviour of the existing KG ingestion cron. The KG query engine defaults to no consent filter when `consent_token=None`. |
| **Double-kg contribution**: `recall_memories(kg_enabled=True)` already adds a KG RRF signal. If `KGRecallAdapter` also uses the same RRF fusion, memory results would get a double KG contribution. | Set `kg_enabled=False` in `MemoryRecallAdapter` (as designed). The KG adapter's `RecallContextAssembler` handles KG signal separately. |

---

## 6. Hard-Rejection Flags

**None.** The system as proposed satisfies:
- HARD STOP remains absolute + non-LLM (decide_node's priority hierarchy checks hard_stop_requested first, brain never controls END decision).
- No raw `LLMRouter.chat` in graph path (only `HermesBrain.think`).
- "Heartbeat" terminology preserved.
- No secrets in output.
- Display-only autonomy (no DMs/side-effects).

**However**, shipping the CURRENT code (without this integration) would trigger a hard rejection on AC-LIFE-005 because decisions are not memory-driven (stubs return mock data, brain prompts never contain recall context). This research report provides the implementation path to close that gap.

---

## 7. Concrete Recommendation for the Implementation Phase

### Priority order

1. **Add state fields** (`state.py` lines 207-219) — quick, trivial.
2. **Rewrite p16_adapter.py** with real `RecallContextAssembler` wrapper as specified in 4.2.
3. **Rewrite p18_adapter.py** with real `recall_memories` wrapper as specified in 4.3.
4. **Modify `graph.py`:**
   - Add `kg_adapter`/`memory_adapter` to `create_life_mind_graph` signature.
   - Create `_make_observe` closure in `_make_observe(kg_adapter, memory_adapter):` near line 97.
   - Replace world_model_available logic.
   - Return new state fields.
   - Add `_format_recalls` helper and update `_make_brain_decide`, `_make_brain_act`, `_make_brain_idle` prompts.
   - Register `_observe_fn` instead of raw `observe_node`.
5. **Modify `core/main.py`** to build adapters and pass to `create_life_mind_graph` as designed in 4.6.
6. **Add unit tests** for:
   - Adapter degradation: verify `_degraded=True` returned when assembler/pipeline raises.
   - observe_node with real adapters: verify `recalled_concepts`/`recalled_memories` populated.
   - observe_node with None adapters: verify `world_model_status="unavailable"`, no crash.
   - Brain prompts: verify `_format_recalls` produces expected strings.
7. **Validation audit**: confirm no `LLMRouter.chat`, HARD STOP unchanged, no secrets logged, no side-effects.

### Key function signatures for implementation

```python
# graph.py
def create_life_mind_graph(
    checkpointer: Any | None = None,
    hermes_brain: Any | None = None,
    kg_adapter: Any | None = None,
    memory_adapter: Any | None = None,
) -> Any:
    """...

    ``kg_adapter`` and ``memory_adapter`` are injected by ``core/main.py``.
    When both are provided, ``observe_node`` builds a full decision context
    using ``DecisionContextBuilder`` and populates ``recalled_concepts`` /
    ``recalled_memories`` in the output state.  When either is ``None``, the
    node degrades gracefully without impacting kernel safety.
    """

# p16_adapter.py
class KGRecallAdapter:
    def __init__(self, assembler: RecallContextAssembler | None = None) -> None: ...

# p18_adapter.py
class MemoryRecallAdapter:
    def __init__(
        self,
        session_factory: Callable[[], AsyncContextManager[Any]],
        embedding_service: Any | None = None,
        principal: str = "guinevere_core",
        safe_mode: bool = False,
        token_budget: int = 4000,
    ) -> None: ...

# core/main.py  (inside P20 life_kernel block)
_session_factory = _async_sessionmaker(_engine, class_=_AsyncSession, expire_on_commit=False)
kg_adapter = KGRecallAdapter(assembler=_kg_assembler) if _kg_assembler else None
memory_adapter = MemoryRecallAdapter(session_factory=_session_factory, embedding_service=_embedding_svc) if _embedding_svc else MemoryRecallAdapter(session_factory=_session_factory)
```

### Dependencies

The real substrates are already installed in `.venv` and used elsewhere. No new `pip install` required.

### Files to modify (final list)

| File | Change |
|---|---|
| `src/life_kernel/state.py` | Add 3 new NotRequired fields |
| `src/life_kernel/p16_adapter.py` | Full rewrite of KGRecallAdapter |
| `src/life_kernel/p18_adapter.py` | Full rewrite of MemoryRecallAdapter |
| `src/life_kernel/graph.py` | Add adapter params, _make_observe, world_model flag, brain prompts |
| `src/core/main.py` | Build adapters, pass to create_life_mind_graph |
| `tests/life_kernel/test_p16_adapter.py` | New: real adapter unit tests |
| `tests/life_kernel/test_p18_adapter.py` | New: real adapter unit tests |
| `tests/life_kernel/test_observe_node.py` | New: observe_node integration tests |

---

*End of report.*
