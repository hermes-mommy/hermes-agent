# R08: Sub-Agent System — delegate_tool.py Patch, Iteration Budget, Recursive Spawning

**Generated**: 2026-06-29
**Method**: Direct file reads and grep searches against `.venv/Lib/site-packages/tools/delegate_tool.py` (2801 lines), `.venv/Lib/site-packages/agent/iteration_budget.py` (62 lines), `src/loops/phases/delegate.py` (82 lines), and `docs/setup-evidence/P28-P36-masterplan/adr-drafts/ADR-065-sub-agent-recursive-spawning.md`.

---

## 1. Verified Constants in delegate_tool.py

All claimed constants exist at the stated lines. Confirmed via direct grep/read:

| Constant | File:Line | Current Value | Purpose |
|---|---|---|---|
| `_DEFAULT_MAX_CONCURRENT_CHILDREN` | `delegate_tool.py:132` | `3` | Default cap on simultaneous child agents per delegate_task call |
| `MAX_DEPTH` | `delegate_tool.py:133` | `1` | Default flat: parent(0) -> child(1); grandchildren rejected by default |
| `_MIN_SPAWN_DEPTH` | `delegate_tool.py:136` | `1` | Minimum allowed value for `delegation.max_spawn_depth` config |
| `_MAX_SPAWN_DEPTH_CAP` | `delegate_tool.py:137` | `3` | Hard upper clamp for `delegation.max_spawn_depth` config |
| `DELEGATE_BLOCKED_TOOLS` | `delegate_tool.py:45-53` | `frozenset({"delegate_task", "clarify", "memory", "send_message", "execute_code"})` | Tools children must never have access to |
| `_SUBAGENT_TOOLSETS` | `delegate_tool.py:123-129` | Derived dynamically from `TOOLSETS` minus excluded toolsets minus fully-blocked ones | Available toolset names for subagents |

**MaxDepthReached**: Does NOT exist as a class or exception in the current codebase. The depth limit is enforced at `delegate_tool.py:1962-1972` via a JSON error string return, not an exception:
```python
if depth >= max_spawn:
    return json.dumps({
        "error": (
            f"Delegation depth limit reached (depth={depth}, "
            f"max_spawn_depth={max_spawn}). ..."
        )
    })
```
ADR-065 references `MaxDepthReached` exception, but this is a design spec, not yet implemented.

**`_get_max_spawn_depth()`** at `delegate_tool.py:394-429`: Reads `delegation.max_spawn_depth` from config, clamped to `[_MIN_SPAWN_DEPTH, _MAX_SPAWN_DEPTH_CAP]` = `[1, 3]`. Falls back to `MAX_DEPTH` (1).

---

## 2. Plan Claims vs Reality

### 2.1 delegate_tool.py Constants Patch (Plan M5.5)

Plan states: patch lines 132-137 to change `max_concurrent: 3->10`, `max_depth: 1->5`, `spawn_cap: 3->5`.

**Reality check**:
- `_DEFAULT_MAX_CONCURRENT_CHILDREN = 3` at line 132 -- confirmed. Changing to 10 is a code constant change + config.yaml `delegation.max_concurrent_children: 10`.
- `MAX_DEPTH = 1` at line 133 -- confirmed. Changing default to 5 means changing this constant. But the code clamps to `_MAX_SPAWN_DEPTH_CAP` at line 137.
- `_MAX_SPAWN_DEPTH_CAP = 3` at line 137 -- confirmed. Must change to 5 to allow config values up to 5.
- `_get_max_spawn_depth()` docstring at line 395 says "clamped to [1, 3]" -- docstring must also be updated.

**Disposition**: MODIFY-CREATE. All changes are to constants + docstring in `delegate_tool.py`. Straightforward.

### 2.2 Remove delegate_task from DELEGATE_BLOCKED_TOOLS

Plan states: "Remove `delegate_task` from `DELEGATE_BLOCKED_TOOLS` frozenset".

**Reality**: `delegate_task` is listed at `delegate_tool.py:47` inside the frozenset. Removing it enables sub-agents to call `delegate_task` themselves (recursive spawning). However, there is ALREADY a role-based mechanism: `role='orchestrator'` re-adds the `delegation` toolset at `delegate_tool.py:967`:
```python
if effective_role == "orchestrator" and "delegation" not in child_toolsets:
    child_toolsets.append("delegation")
```

This means the `DELEGATE_BLOCKED_TOOLS` set only blocks `delegate_task` for **leaf** subagents. Orchestrator-role children already get delegation capability via the role path. Removing `delegate_task` from `DELEGATE_BLOCKED_TOOLS` would make ALL sub-agents (including leaf) able to delegate, which contradicts the leaf/orchestrator design.

**Risk**: HIGH. Removing `delegate_task` from `DELEGATE_BLOCKED_TOOLS` breaks the leaf/orchestrator distinction. The correct approach is to keep the frozenset as-is and use `role='orchestrator'` for recursive spawning. The plan's instruction to "remove delegate_task from DELEGATE_BLOCKED_TOOLS" is **incorrect** per the existing code design.

**Disposition**: BLOCKED on plan correction. The existing mechanism (role-based) already supports recursive spawning. The plan should instead raise `_MAX_SPAWN_DEPTH_CAP` to 5 and ensure `role='orchestrator'` propagates correctly at all depth levels.

### 2.3 New file: guinevere/iteration_budget.py

Plan states: "CREATE NEW file `guinevere/iteration_budget.py` with global `asyncio.Semaphore(10)` to prevent 10x5x90=4500 concurrent calls."

**Reality**: Hermes v0.15.2 already has `agent/iteration_budget.py` (62 lines) containing `IterationBudget` class:
- Thread-safe `threading.Lock`-based consume/refund counter (`agent/iteration_budget.py:32-62`)
- Each agent (parent or subagent) gets its own instance
- Parent cap = `max_iterations` (default 90), subagent cap = `delegation.max_iterations` (default 50)
- Used at `delegate_tool.py:1136`: `iteration_budget=None` (fresh budget per subagent)

The plan's proposed `asyncio.Semaphore(10)` is a DIFFERENT concept from Hermes's existing `IterationBudget`:
- **Existing**: per-agent iteration counter (how many LLM turns per agent)
- **Plan's proposal**: global concurrency limiter (how many subagents run simultaneously)

The plan wants to create a GLOBAL semaphore to cap total concurrent sub-agent API calls across the entire process. This is distinct from the per-agent iteration budget.

**Key design questions for the new file**:
- The existing `ThreadPoolExecutor(max_workers=max_children)` at `delegate_tool.py:2101` already limits parallelism per `delegate_task` call to `max_children` (currently 3, proposed 10).
- But recursive nested spawns could create 10x5=50 concurrent children across the tree. The plan's global `asyncio.Semaphore(10)` would cap this.
- However, `delegate_tool.py` uses `ThreadPoolExecutor` (threading), NOT asyncio. A threading `Semaphore` would be more appropriate than `asyncio.Semaphore` for direct integration.
- The plan mentions `MaxDepthReached` exception for cap breach -- this does not exist and must be created.

**Disposition**: MODIFY-CREATE. Create `guinevere/iteration_budget.py` with a `threading.Semaphore(10)` (not asyncio.Semaphore, since delegate_tool.py uses ThreadPoolExecutor). Add `MaxDepthReached` exception. Integrate into `_run_single_child` to acquire semaphore before child execution and release on completion.

### 2.4 MaxDepthReached Exception

ADR-065 specifies `MaxDepthReached` exception for cap breach. The current code returns a JSON error string instead.

**Disposition**: MODIFY-CREATE. Create `MaxDepthReached(Exception)` class. Can live in `guinevere/iteration_budget.py` or as a standalone exception module. Replace JSON error returns at `delegate_tool.py:1963-1971` with `raise MaxDepthReached(...)`.

### 2.5 Consciousness State Interaction (M3)

Plan states: "W8 depends on W6 (sub-agent runner needs consciousness loop state for delegation context)."

**Reality**: There are ZERO references to consciousness, M3, awareness, or self-aware in `delegate_tool.py`. The word "consciousness" does not appear anywhere in the 2801-line file. The current delegation system is completely stateless with respect to consciousness.

The plan's intended interaction model (from `p24-hermes-native-fork-enterprise-plan.md:1079`):
- Sub-agent runner needs consciousness loop state for delegation context
- W8 (M5 Sub-agents) depends on W6 (M3 Consciousness)

This means M5 must be implemented AFTER M3, and the sub-agent spawn path must inject consciousness state (affect, substrate, thought history) into the child agent's context or system prompt.

**Current gap**: No mechanism exists in `delegate_tool.py` to pass consciousness state to children. The `_build_child_system_prompt()` function at line 971 builds the child prompt with goal/context/workspace/role, but has no consciousness-aware parameters.

**Disposition**: MODIFY-CREATE. Add consciousness state injection points in `_build_child_agent()` (around line 971-978). Wire consciousness state from parent agent attributes into child's system prompt or context. This requires M3 (ConsciousnessLoop) to be implemented first, exposing state via parent agent attributes (e.g., `parent_agent._consciousness_state`).

---

## 3. ADR-065 Compliance Gap Analysis

ADR-065 specifies (from `ADR-065-sub-agent-recursive-spawning.md`):

| ADR-065 Requirement | Current Status | Gap |
|---|---|---|
| Recursive sub-agent spawning | PARTIAL: role='orchestrator' enables it, but `_MAX_SPAWN_DEPTH_CAP=3` limits to 3 levels | Cap must be raised to 5+ (plan) or 10 (ADR) |
| Hard cap = 10 active per Hermes | NOT IMPLEMENTED: no global active-count semaphore | Need global semaphore in `_run_single_child` |
| `MaxDepthReached` exception | NOT IMPLEMENTED: JSON error string returned | Need exception class |
| Audit trail with signature chain | NOT IMPLEMENTED: no hash-chained spawn audit rows | Need audit chain in `_register_subagent` |
| Distributed shaker signal at 8+ active | NOT IMPLEMENTED | Out of P24 scope (requires cross-instance) |
| Per-Hermes memory/quota split | NOT IMPLEMENTED: subagent gets `iteration_budget=None` (fresh) | Need quota allocation from parent |
| Emergency cap override (Tier 4) | NOT IMPLEMENTED | Out of P24 scope (requires DAO/Tier 4) |
| Spawn rate limit (30/hour) | NOT IMPLEMENTED | Need rate limiter in new iteration_budget.py |

---

## 4. Sub-agent Identity and Lineage Chain

The current code ALREADY tracks parent-child identity (`delegate_tool.py:910-922, 1140-1148`):

```python
child_depth = getattr(parent_agent, "_delegate_depth", 0) + 1  # :910
subagent_id = f"sa-{task_index}-{_uuid.uuid4().hex[:8]}"       # :920
parent_subagent_id = getattr(parent_agent, "_subagent_id", None)  # :921

child._delegate_depth = child_depth       # :1140
child._delegate_role = effective_role     # :1143
child._subagent_id = subagent_id         # :1146
child._parent_subagent_id = parent_subagent_id  # :1147
```

The module-level registry at `delegate_tool.py:155` tracks active subagents:
```python
_active_subagents: Dict[str, Dict[str, Any]] = {}
```

Registration includes `subagent_id`, `parent_id`, `depth`, `goal`, `model`, `started_at` (line 1450-1465). This provides the BASE for an audit chain but lacks:
- Hash chaining (ADR-065 signature_chain_hash)
- Resource budget tracking (tokens_allocated, memory_quota_bytes)
- Scope boundary tracking (namespace_writes, tools_allowed)

**Disposition**: MODIFY-CREATE. Extend `_register_subagent()` record to include hash chain (hash of parent's last audit row), resource budget, and scope boundary fields.

---

## 5. Concurrency Architecture

Current concurrency model (`delegate_tool.py:2091-2101`):
- Single child: runs directly on main thread (no pool)
- Multiple children: `ThreadPoolExecutor(max_workers=max_children)` 
- `max_children` = `_get_max_concurrent_children()` which reads `delegation.max_concurrent_children` from config, default 3

The plan proposes `max_children=10` per call. With recursive spawning at depth 5:
- Worst case: 10 children x 5 levels = 50 concurrent API calls
- Plan's global `asyncio.Semaphore(10)` caps total concurrent across entire tree

**Implementation path**: 
1. Change `_DEFAULT_MAX_CONCURRENT_CHILDREN` from 3 to 10
2. Change `_MAX_SPAWN_DEPTH_CAP` from 3 to 5
3. Add global `threading.Semaphore(10)` in `guinevere/iteration_budget.py`
4. Acquire semaphore in `_run_single_child()` before `child.run()`, release in `finally`
5. Raise `MaxDepthReached` if semaphore cannot be acquired within timeout

---

## 6. Disposition Summary

| Component | Disposition | Rationale |
|---|---|---|
| `_DEFAULT_MAX_CONCURRENT_CHILDREN` constant (line 132) | MODIFY: 3 -> 10 | Per ADR-065 / plan |
| `MAX_DEPTH` constant (line 133) | MODIFY: 1 -> 5 | Per plan M5.5 |
| `_MAX_SPAWN_DEPTH_CAP` constant (line 137) | MODIFY: 3 -> 5 | Per plan M5.5 |
| `DELEGATE_BLOCKED_TOOLS` frozenset (line 45) | KEEP AS-IS | Plan's instruction to remove `delegate_task` is INCORRECT; role-based orchestrator mechanism already handles this |
| `_get_max_spawn_depth()` docstring (line 395) | MODIFY: update clamp range to [1, 5] | Align with new cap |
| `guinevere/iteration_budget.py` | CREATE | New file with global semaphore + MaxDepthReached + spawn rate limiter |
| `MaxDepthReached` exception | CREATE | In iteration_budget.py; replace JSON error at delegate_tool.py:1963 |
| Consciousness state injection | CREATE | Wire M3 state into child agent via _build_child_agent; depends on M3 existing |
| Audit chain extension | MODIFY | Extend _register_subagent with hash chain, budget, scope fields |
| `src/loops/phases/delegate.py` | DELETE | Placeholder stub (82 lines); replaced by M5 implementation |

---

## 7. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Plan incorrectly says to remove `delegate_task` from `DELEGATE_BLOCKED_TOOLS` | HIGH | Do NOT remove; use role='orchestrator' path instead. Correct plan. |
| `asyncio.Semaphore` vs `threading.Semaphore` mismatch | MEDIUM | delegate_tool.py uses ThreadPoolExecutor, not asyncio. Use `threading.Semaphore` unless M3 forces asyncio migration. |
| 10 concurrent children x 5 depth = 50 API calls | HIGH | Global semaphore(10) caps this. But 10x90 iterations = 900 total API turns per delegate_task call is still expensive. |
| Consciousness state not yet implemented (M3) | MEDIUM | M5 W8 explicitly depends on W6 (M3). Implement M5 without consciousness hooks first, add hooks when M3 lands. |
| Hash-chained audit requires cryptographic dependency | LOW | Python `hashlib` is stdlib. SHA-256 chain is sufficient for audit trail. |
| `MaxDepthReached` exception changes error contract | MEDIUM | Existing callers expect JSON error string. Exception must be caught and serialized at delegate_task entry point. |

---

## 8. Verdict

**BLOCKED** on one plan correction: the instruction to "Remove `delegate_task` from `DELEGATE_BLOCKED_TOOLS`" is architecturally incorrect. The existing role-based mechanism (`role='orchestrator'` re-adds the delegation toolset) already supports recursive spawning without modifying the frozenset. Removing the entry would break the leaf/orchestrator distinction and allow ALL sub-agents (including leaf) to delegate, violating the design contract at `delegate_tool.py:967`.

All other components (constant patches, new iteration_budget.py, MaxDepthReached exception, audit chain extension, consciousness state injection points) are feasible and correctly specified in the plan.

**Corrections needed in plan**:
1. Remove instruction to modify `DELEGATE_BLOCKED_TOOLS` -- keep frozenset as-is
2. Clarify `threading.Semaphore` vs `asyncio.Semaphore` -- use threading for direct integration with ThreadPoolExecutor
3. Note that consciousness state injection (M3) is a forward dependency, not blocking M5 core implementation
