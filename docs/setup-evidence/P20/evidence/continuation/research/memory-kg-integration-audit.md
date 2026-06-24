---
title: "P20 Memory / Knowledge-Graph Integration Audit"
status: "Completed"
date: "2026-06-24"
owner: "Faiz"
scope: "P20 Living Autonomy Kernel — P16 KG & P18 Memory recall wiring"
---

# P20 Memory / Knowledge-Graph Integration Audit

## Request

Verify whether P16 Knowledge Graph and P18 Memory are actually wired into the life kernel's observe/decide context (AC-LIFE-005), or merely imported but unused.

## Verdict

**Integration is REAL and functional, but shallow in two places:**

1. **Real adapters are built and injected at startup** (`src/core/main.py`).
2. **observe_node calls them every cycle** and stores `recalled_concepts` / `recalled_memories` in `LifeMindState`.
3. **decide / idle / reflect nodes consume the recalled context** for routing, self-directed task generation, and journal gating.
4. **No separate "world model" module exists** — `world_model_status` is derived from adapter health, not from a dedicated world-model substrate.
5. **Background-cognition memory loop is still a placeholder** (`src/life_kernel/cognition.py`); proactive recall only happens inside the graph's observe_node.
6. **`DecisionContextBuilder` is defined but unused** by the graph; `state.py` docstrings incorrectly claim the graph uses it.

## 1. Imports of P16 / P18 inside `src/life_kernel/`

| Source | Import / Reference | Notes |
|---|---|---|
| `src/life_kernel/p16_adapter.py` | None direct; expects injected `kg_client` callable | Adapter normalises `KGQueryEngine.search_entities` output |
| `src/life_kernel/p18_adapter.py` | None direct; expects injected `memory_client` callable | Adapter normalises `recall_memories` output |
| `src/life_kernel/graph.py` | Uses adapters only via module-level `_ADAPTERS` registry | No `src.memory` / `src.knowledge_graph` imports |
| `src/life_kernel/decision_context.py` | Imports `KGRecallAdapter`, `MemoryRecallAdapter` | Exported but **not consumed by graph.py** |
| `src/life_kernel/__init__.py` | Re-exports both adapter classes + `DecisionContextBuilder` | Public surface only |

No `src/memory/*` or `src/knowledge_graph/*` modules are imported directly inside `src/life_kernel/`.  All coupling is through the two adapter classes and the runtime wiring in `src/core/main.py`.

## 2. Memory (`src/memory/`) module inventory

- `__init__.py`
- `models.py`
- `db.py`
- `read_pipeline.py`
- `write_pipeline.py`
- `embeddings.py`
- `tiers.py`
- `consolidation.py`
- `compaction.py`
- `spaced_repetition.py`
- `dnr.py`

The real recall surface is `recall_memories` in `read_pipeline.py`.

## 3. Knowledge Graph (`src/knowledge_graph/`) module inventory

- `__init__.py`, `types.py`, `config.py`, `constants.py`, `errors.py`, `repository.py`
- `ingestion/` — `pipeline.py`, `batch_processor.py`, `backfill.py`, `cron.py`, `backfill_validator.py`
- `query/` — `engine.py`, `context.py`, `token_budget.py`, `rrf_fusion.py`, `ppr.py`
- `extraction/` — `entity_extractor.py`, `relation_extractor.py`, `patterns.py`
- `resolution/` — `resolver.py`, `fuzzy.py`, `canonical.py`
- `consent/` — `rls.py`, `manager.py`, `audit.py`
- `observability/` — `logger.py`, `metrics.py`, `tracer.py`
- `eval/` — `runner.py`, `report.py`, `metrics.py`, `golden_set.py`
- `tests/`

The real recall surface used by the kernel is `KGQueryEngine.search_entities`.

## 4. Where the wiring happens

`src/core/main.py` (lines 204-329):

```python
# Build async SQLAlchemy engine/session factory for the kernel
_lk_engine = _lk_create_async_engine(_lk_db_url, pool_size=2, pool_pre_ping=True)
_lk_session_factory = _lk_async_sessionmaker(_lk_engine, ...)

# P18 memory adapter: wrap recall_memories with a per-call session
async def _life_recall_fn(*, query_text: str, principal: str = "guinevere_core", exclude_dnr: bool = True):
    async with _lk_session_factory() as _lk_session:
        return await _recall_memories(
            _lk_session, query_text, limit=20,
            exclude_dnr=exclude_dnr, principal=principal, safe_mode=False,
        )

memory_adapter = MemoryRecallAdapter(memory_client=_life_recall_fn)

# P16 KG adapter: wrap KGQueryEngine.search_entities
_kg_engine_instance = _KGQueryEngine(session_factory=_lk_session_factory)

async def _life_kg_fn(*, query_text: str):
    rows = await _kg_engine_instance.search_entities(query_text)
    return [
        {
            "name": getattr(r, "display_name", None) or str(getattr(r, "entity_id", "")),
            "relevance": float(getattr(r, "relevance", 0.0)),
            "source": "p16",
        }
        for r in (rows or [])
    ]

kg_adapter = KGRecallAdapter(kg_client=_life_kg_fn)

# Inject into the graph
create_life_mind_graph(
    checkpointer=checkpointer,
    hermes_brain=hermes_brain,
    kg_adapter=kg_adapter,
    memory_adapter=memory_adapter,
    journal_writer=journal_writer,
)
```

**Key point:** the life kernel receives live, DB-backed recall callables at application startup.

## 5. How observe_node uses P16/P18

`src/life_kernel/graph.py::observe_node` (lines 133-275):

1. Reads adapters from the module-level registry `_ADAPTERS`.
2. Seeds recall with `current_focus` (falls back to a generic query).
3. Awaits `kg_adapter.recall(...)` and `memory_adapter.recall(...)` concurrently (fail-soft).
4. Sets `world_model_status` to `active` / `degraded` / `unavailable`.
5. Returns:
   - `recalled_concepts`
   - `recalled_memories`
   - `decision_context`
   - `world_model_status`
   - `memory_status`

This means **every graph cycle triggers real P16 + P18 recall** when adapters are present.

## 6. How decide / idle / reflect consume the recalled context

### decide_node (static) + `_make_brain_decide` (LLM wrapper)

- Static `decide_node` does **not** use recall directly; it routes on `goals`, `commitments`, `concerns`.
- When a brain is available and static routing yields `idle`, `_make_brain_decide` feeds the top 5 recalled concepts and memories into the prompt (lines 744-754).

### idle_node + `_make_brain_idle`

- `idle_node` picks a self-directed task from recalled memories first, then concepts, then a deterministic fallback (lines 613-638).
- `_make_brain_idle` feeds the same recall context to the LLM to generate a brain-grounded agenda (lines 819-834).

### reflect_node

- Uses `recalled_memories` / `recalled_concepts` to decide if the cycle was "meaningful" enough to write a journal entry (lines 519-523).
- Logs the recall counts in the journal `lessons_learned`.

## 7. "World model" reality check

- There is **no dedicated `world_model` module** in `src/life_kernel/`.
- `world_model_status` is a string derived from adapter availability/health (`active`/`degraded`/`unavailable`).
- `world_model_available` is `True` iff status == `active`.
- The kernel therefore does **not** pull from Redis/PostgreSQL raw state for its world model; it relies on the P16/P18 recall adapters, which themselves query PostgreSQL.

## 8. Proactive recall mechanism

- **Reactive recall:** `observe_node` triggers recall on every cycle. ✅
- **Proactive / background recall:** The `memory` loop in `src/life_kernel/cognition.py` is a placeholder that only writes:  
  `"Memory pattern scan placeholder — waiting for P18 memory recall integration."`  
  It does **not** call the real memory adapter. ❌
- No other background proactive recall service exists.

## 9. Inconsistencies / gaps found

| Issue | Location | Impact |
|---|---|---|
| `DecisionContextBuilder` is exported but never used by the graph | `decision_context.py`, `__init__.py` | Dead-ish utility; graph duplicates its logic inline |
| `state.py` docstrings say recall is populated "via DecisionContextBuilder" | `state.py` | Documentation drift; graph populates directly |
| `cognition.py` memory loop placeholder | `cognition.py` | No proactive memory-driven cognition |
| No dedicated world-model substrate | `graph.py` | World model == adapter health + recall results |

## 10. Test coverage

Relevant tests:

- `tests/life_kernel/test_continuation_integration.py` — T6-T10: adapter injection, observe populates recall, idle uses recall, journal writes, memory_status.
- `tests/life_kernel/test_decision_context.py` — `DecisionContextBuilder` unit tests.
- `tests/life_kernel/test_p16_adapter.py` / `test_p18_adapter.py` — adapter normalisation tests.

## Conclusion

**AC-LIFE-005 is implemented:** P16 and P18 are genuinely wired into the life kernel and influence observe/decide/idle/reflection.  
**The integration is shallow in two ways worth fixing:**

1. **Proactive/background recall is missing** — `cognition.py` still holds a placeholder.
2. **DecisionContextBuilder drift** — either wire it into `observe_node` or remove/rename it and fix `state.py` docstrings.

## Recommendations

1. Replace the `memory` loop placeholder in `cognition.py` with a real periodic recall task that pushes observations into the graph when strong memory signals are detected.
2. Decide whether `DecisionContextBuilder` is the canonical context builder; if yes, refactor `observe_node` to use it and delete duplicated logic; if no, deprecate it and correct `state.py` comments.
3. Consider adding a `world_model_status` telemetry metric so dashboard/Grafana can track adapter health over time.

---

*Audit generated by Guinevere code-search sub-agent.*
*Sources: src/core/main.py, src/life_kernel/graph.py, src/life_kernel/state.py, src/life_kernel/cognition.py, src/life_kernel/decision_context.py, src/life_kernel/p16_adapter.py, src/life_kernel/p18_adapter.py, src/memory/read_pipeline.py, src/knowledge_graph/query/engine.py, tests/life_kernel/test_continuation_integration.py.*
